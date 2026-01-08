"""
Face detection and recognition using facenet-pytorch.
Supports MPS (Apple Silicon), CUDA, and CPU backends with automatic fallback.
"""

import os
from pathlib import Path
from typing import Optional, Literal
import hashlib

import torch
import numpy as np
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1

from services.raw_handler import RawHandler


DeviceType = Literal["auto", "mps", "cuda", "cpu"]

# MPS-safe image sizes (divisible by common pooling factors)
MPS_SAFE_SIZE = 1024  # Resize large images to this for MPS compatibility


def get_best_device(preferred: DeviceType = "auto") -> torch.device:
    """
    Get the best available device for computation.

    Args:
        preferred: Preferred device ('auto', 'mps', 'cuda', 'cpu')

    Returns:
        torch.device for computation
    """
    if preferred == "auto":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        elif torch.cuda.is_available():
            return torch.device("cuda")
        else:
            return torch.device("cpu")
    elif preferred == "mps":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        print("Warning: MPS not available, falling back to CPU")
        return torch.device("cpu")
    elif preferred == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        print("Warning: CUDA not available, falling back to CPU")
        return torch.device("cpu")
    else:
        return torch.device("cpu")


def get_available_devices() -> list[str]:
    """Get list of available compute devices."""
    devices = ["auto", "cpu"]
    if torch.backends.mps.is_available():
        devices.insert(1, "mps")
    if torch.cuda.is_available():
        devices.insert(1, "cuda")
    return devices


def make_mps_safe_size(
    width: int, height: int, max_size: int = MPS_SAFE_SIZE
) -> tuple[int, int]:
    """
    Calculate new dimensions that are safe for MPS (divisible by 32).
    Maintains aspect ratio and caps at max_size.
    """
    # Scale down if needed
    scale = min(max_size / width, max_size / height, 1.0)
    new_width = int(width * scale)
    new_height = int(height * scale)

    # Make divisible by 32 for MPS compatibility
    new_width = (new_width // 32) * 32
    new_height = (new_height // 32) * 32

    # Ensure minimum size
    new_width = max(new_width, 160)
    new_height = max(new_height, 160)

    return new_width, new_height


class FaceProcessor:
    """
    Face detection and embedding extraction using MTCNN and InceptionResnetV1.
    Supports MPS (Apple Silicon), CUDA, and CPU with automatic fallback.
    Uses lazy loading for faster startup.
    """

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        device: DeviceType = "auto",
        use_mps_for_detection: bool = True,  # Try MPS for detection
        lazy_load: bool = True,  # Defer model loading until first use
    ):
        """
        Initialize face processor with models.

        Args:
            cache_dir: Directory to cache face thumbnails
            device: Compute device ('auto', 'mps', 'cuda', 'cpu')
            use_mps_for_detection: Whether to try MPS for face detection
            lazy_load: If True, defer model loading until first use (faster startup)
        """
        self.requested_device = device
        self.use_mps_for_detection = use_mps_for_detection
        self._models_loaded = False
        self._loading_models = False

        # These will be set when models are loaded
        self.device = None
        self.detection_device = None
        self.mtcnn = None
        self.resnet = None

        # Track if we need to fall back to CPU for detection
        self._detection_fallback_to_cpu = False

        # Setup cache directory
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load models immediately if not lazy loading
        if not lazy_load:
            self._ensure_models_loaded()

    def _ensure_models_loaded(self):
        """Ensure models are loaded. Called lazily on first use."""
        if self._models_loaded:
            return

        if self._loading_models:
            # Already loading in another call, wait
            import time

            while self._loading_models:
                time.sleep(0.1)
            return

        self._loading_models = True
        try:
            print("Loading face detection models (this may take a moment)...")

            # Get the best device for embeddings (compute-intensive)
            self.device = get_best_device(self.requested_device)
            print(f"Using {self.device.type.upper()} for face embeddings")

            # For detection, try to use same device but with fallback
            if self.use_mps_for_detection and self.device.type == "mps":
                self.detection_device = self.device
                print(f"Using MPS for face detection (with image size normalization)")
            else:
                self.detection_device = torch.device("cpu")
                print(f"Using CPU for face detection")

            self._init_models()
            self._models_loaded = True
            print(
                f"Models loaded successfully! Using device: {self.get_device_info()['device_name']}"
            )
        finally:
            self._loading_models = False

    def _init_models(self):
        """Initialize or reinitialize the ML models."""
        # Initialize MTCNN for face detection
        self.mtcnn = MTCNN(
            image_size=160,
            margin=20,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            device=self.detection_device,
            keep_all=True,
        )

        # Initialize InceptionResnetV1 for face embeddings on preferred device
        self.resnet = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)

    def _reinit_mtcnn_on_cpu(self):
        """Reinitialize MTCNN on CPU as fallback."""
        if not self._detection_fallback_to_cpu:
            print("Falling back to CPU for face detection due to MPS error")
            self._detection_fallback_to_cpu = True
            self.detection_device = torch.device("cpu")
            self.mtcnn = MTCNN(
                image_size=160,
                margin=20,
                min_face_size=40,
                thresholds=[0.6, 0.7, 0.7],
                factor=0.709,
                post_process=True,
                device=self.detection_device,
                keep_all=True,
            )

    def set_device(self, device: DeviceType):
        """
        Change the compute device for embeddings.

        Args:
            device: New device ('auto', 'mps', 'cuda', 'cpu')
        """
        self._ensure_models_loaded()
        new_device = get_best_device(device)
        if new_device != self.device:
            self.requested_device = device
            self.device = new_device
            # Move model to new device
            self.resnet = self.resnet.to(self.device)
            print(f"Switched to {self.device.type.upper()} for face embeddings")

            # Also try to use new device for detection if MPS
            if (
                self.use_mps_for_detection
                and self.device.type == "mps"
                and not self._detection_fallback_to_cpu
            ):
                self.detection_device = self.device
                self._init_models()

    def get_device_info(self) -> dict:
        """Get information about current device configuration."""
        # Return placeholder info if models not loaded yet
        if not self._models_loaded:
            return {
                "device": "pending",
                "device_name": "Not loaded yet",
                "embedding_device": "pending",
                "detection_device": "pending",
                "requested_device": self.requested_device,
                "available_devices": get_available_devices(),
            }
        device_names = {
            "mps": "Apple Silicon GPU (MPS)",
            "cuda": "NVIDIA GPU (CUDA)",
            "cpu": "CPU",
        }
        return {
            "device": self.device.type,
            "device_name": device_names.get(self.device.type, self.device.type.upper()),
            "embedding_device": self.device.type,
            "detection_device": self.detection_device.type,
            "requested_device": self.requested_device,
            "available_devices": get_available_devices(),
        }

    def _get_image_hash(self, filepath: str | Path) -> str:
        """Generate a hash for the image file path and modification time."""
        filepath = Path(filepath)
        stat = filepath.stat()
        content = f"{filepath.absolute()}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(content.encode()).hexdigest()

    def _prepare_image_for_detection(
        self, image: Image.Image
    ) -> tuple[Image.Image, float]:
        """
        Prepare image for face detection, resizing if needed for MPS compatibility.

        Returns:
            Tuple of (prepared_image, scale_factor)
        """
        if self.detection_device.type != "mps":
            return image, 1.0

        # For MPS, resize to safe dimensions
        orig_width, orig_height = image.size
        new_width, new_height = make_mps_safe_size(orig_width, orig_height)

        if new_width != orig_width or new_height != orig_height:
            scale_x = orig_width / new_width
            scale_y = orig_height / new_height
            scale = (scale_x + scale_y) / 2  # Average scale for box adjustment

            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS  # type: ignore

            resized = image.resize((new_width, new_height), resample)
            return resized, scale

        return image, 1.0

    def detect_faces(
        self, image: Image.Image
    ) -> tuple[
        Optional[torch.Tensor], Optional[np.ndarray], Optional[np.ndarray], float
    ]:
        """
        Detect faces in an image.

        Args:
            image: PIL Image object

        Returns:
            Tuple of (face_tensors, boxes, probabilities, scale_factor)
        """
        self._ensure_models_loaded()
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Prepare image for detection (resize for MPS if needed)
            prepared_image, scale = self._prepare_image_for_detection(image)

            try:
                detection_result = self.mtcnn.detect(prepared_image)
                boxes = detection_result[0]
                probs = detection_result[1]
            except RuntimeError as e:
                if "divisible" in str(e) or "MPS" in str(e):
                    # MPS error, fall back to CPU
                    self._reinit_mtcnn_on_cpu()
                    detection_result = self.mtcnn.detect(image)
                    boxes = detection_result[0]
                    probs = detection_result[1]
                    scale = 1.0
                else:
                    raise

            if boxes is None:
                return None, None, None, 1.0

            # Scale boxes back to original image size
            if scale != 1.0:
                boxes = boxes * scale

            # Extract face tensors from original image (full resolution)
            faces = self.mtcnn.extract(image, boxes, save_path=None)

            if faces is None:
                return None, None, None, 1.0

            if faces.dim() == 3:
                faces = faces.unsqueeze(0)

            return faces, boxes, probs, scale

        except Exception as e:
            print(f"Face detection error: {e}")
            # Try CPU fallback
            if self.detection_device.type != "cpu":
                self._reinit_mtcnn_on_cpu()
                return self.detect_faces(image)
            return None, None, None, 1.0

    def get_embeddings(self, face_tensors: torch.Tensor) -> np.ndarray:
        """
        Generate face embeddings from cropped face tensors.
        Uses GPU acceleration when available with CPU fallback.

        Args:
            face_tensors: Tensor of face images [N, 3, 160, 160]

        Returns:
            Array of 512-dimensional embeddings [N, 512]
        """
        self._ensure_models_loaded()
        try:
            with torch.no_grad():
                face_tensors = face_tensors.to(self.device)
                embeddings = self.resnet(face_tensors)
                embeddings = embeddings / embeddings.norm(dim=1, keepdim=True)
                return embeddings.cpu().numpy()
        except Exception as e:
            # Fallback to CPU if GPU fails
            if self.device.type != "cpu":
                print(f"GPU embedding failed ({e}), falling back to CPU")
                with torch.no_grad():
                    face_tensors = face_tensors.to("cpu")
                    self.resnet = self.resnet.to("cpu")
                    embeddings = self.resnet(face_tensors)
                    embeddings = embeddings / embeddings.norm(dim=1, keepdim=True)
                    # Restore to original device
                    self.resnet = self.resnet.to(self.device)
                    return embeddings.numpy()
            raise

    def process_image(
        self, filepath: str | Path, use_thumbnail: bool = True
    ) -> list[dict]:
        """
        Process an image file to detect faces and extract embeddings.

        Args:
            filepath: Path to image file
            use_thumbnail: Use embedded thumbnail for RAW files (faster)

        Returns:
            List of face dictionaries with embedding, box, confidence, thumbnail_path
        """
        filepath = Path(filepath)

        image = RawHandler.get_image(filepath, use_thumbnail=use_thumbnail)
        if image is None:
            return []

        # Store original image for thumbnail extraction
        original_image = image

        faces, boxes, probs, scale = self.detect_faces(image)
        if faces is None:
            return []

        embeddings = self.get_embeddings(faces)

        results = []
        for i, (embedding, box, prob) in enumerate(zip(embeddings, boxes, probs)):  # type: ignore
            face_data = {
                "embedding": embedding,
                "box": box.tolist(),
                "confidence": float(prob),
                "thumbnail_path": None,
            }

            if self.cache_dir:
                try:
                    img_hash = self._get_image_hash(filepath)
                    thumb_filename = f"{img_hash}_{i}.jpg"
                    thumb_path = self.cache_dir / thumb_filename

                    x1, y1, x2, y2 = map(int, box)
                    margin = int((x2 - x1) * 0.1)
                    x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
                    x2, y2 = (
                        min(original_image.width, x2 + margin),
                        min(original_image.height, y2 + margin),
                    )

                    face_crop = original_image.crop((x1, y1, x2, y2))
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.LANCZOS  # type: ignore
                    face_crop = face_crop.resize((150, 150), resample)
                    face_crop.save(thumb_path, "JPEG", quality=85)

                    face_data["thumbnail_path"] = str(thumb_path)
                except Exception as e:
                    print(f"Failed to save face thumbnail: {e}")

            results.append(face_data)

        return results

    def process_batch(
        self, filepaths: list[str | Path], use_thumbnail: bool = True
    ) -> dict[str, list[dict]]:
        """Process multiple images for faces."""
        results = {}
        for filepath in filepaths:
            results[str(filepath)] = self.process_image(filepath, use_thumbnail)
        return results

    def compute_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """Compute cosine similarity between two face embeddings."""
        return float(np.dot(embedding1, embedding2))

    def are_same_person(
        self, embedding1: np.ndarray, embedding2: np.ndarray, threshold: float = 0.6
    ) -> bool:
        """Determine if two face embeddings belong to the same person."""
        return self.compute_similarity(embedding1, embedding2) > threshold
