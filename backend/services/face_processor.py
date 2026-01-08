"""
Face detection and recognition using InsightFace.
Uses SCRFD for detection (better at rotated faces) and ArcFace for recognition.
Supports CUDA, CPU, and optimized for consumer hardware.
"""

import os
from pathlib import Path
from typing import Optional, Literal
import hashlib

import cv2
import numpy as np
from PIL import Image
import insightface
from insightface.app import FaceAnalysis

from services.raw_handler import RawHandler


DeviceType = Literal["auto", "cuda", "cpu"]

# MPS-safe image sizes (divisible by common pooling factors)
MPS_SAFE_SIZE = 1024  # Resize large images to this for MPS compatibility


def get_best_device(preferred: DeviceType = "auto") -> str:
    """
    Get the best available device for computation.

    Args:
        preferred: Preferred device ('auto', 'cuda', 'cpu')

    Returns:
        Device string for insightface
    """
    if preferred == "auto":
        try:
            import onnxruntime as ort

            if ort.get_device() == "GPU":
                return "cuda"
        except:
            pass
        return "cpu"
    elif preferred == "cuda":
        return "cuda"
    else:
        return "cpu"


def get_available_devices() -> list[str]:
    """Get list of available compute devices."""
    devices = ["auto", "cpu"]
    try:
        import onnxruntime as ort

        if ort.get_device() == "GPU":
            devices.insert(1, "cuda")
    except:
        pass
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
    Face detection and embedding extraction using InsightFace.
    Uses SCRFD for detection (excellent at detecting rotated faces)
    and ArcFace for recognition (state-of-the-art embeddings).
    Optimized for consumer hardware with ONNX runtime.
    """

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        device: DeviceType = "auto",
        lazy_load: bool = True,
    ):
        """
        Initialize face processor with models.

        Args:
            cache_dir: Directory to cache face thumbnails
            device: Compute device ('auto', 'cuda', 'cpu')
            lazy_load: If True, defer model loading until first use (faster startup)
        """
        self.requested_device = device
        self._models_loaded = False
        self._loading_models = False

        # These will be set when models are loaded
        self.device: Optional[str] = None
        self.face_analysis: Optional["FaceAnalysis"] = None

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
            print(
                "Loading face detection and recognition models (this may take a moment)..."
            )

            # Get the best device
            device_str = get_best_device(self.requested_device)
            providers = (
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if device_str == "cuda"
                else ["CPUExecutionProvider"]
            )

            print(f"Using {device_str.upper()} for face processing")

            # Initialize InsightFace with SCRFD detector and ArcFace recognizer
            # det_size: 640x640 for detection (balanced accuracy/speed)
            # Using SCRFD-2.5GF detector (better than MTCNN for rotated faces)
            # Using ArcFace ResNet100 (state-of-the-art recognition)
            self.face_analysis = FaceAnalysis(
                name="buffalo_l",  # Uses SCRFD-2.5GF + ArcFace ResNet100
                providers=providers,
                det_size=(640, 640),
            )
            self.face_analysis.prepare(ctx_id=0 if device_str == "cuda" else -1)

            self.device = device_str
            self._models_loaded = True
            print(
                f"Models loaded successfully! Using device: {self.get_device_info()['device_name']}"
            )
        except Exception as e:
            print(f"Error loading models: {e}")
            # Try fallback to CPU only model
            try:
                print("Attempting fallback to lightweight models...")
                self.face_analysis = FaceAnalysis(
                    name="buffalo_m",  # Lightweight version: SCRFD-500MF + ArcFace MobileFaceNet
                    providers=["CPUExecutionProvider"],
                    det_size=(640, 640),
                )
                self.face_analysis.prepare(ctx_id=-1)
                self.device = "cpu"
                self._models_loaded = True
                print("Lightweight models loaded successfully on CPU")
            except Exception as fallback_error:
                print(f"Failed to load models even with fallback: {fallback_error}")
                self._loading_models = False
                raise
        finally:
            self._loading_models = False

    def set_device(self, device: DeviceType):
        """
        Change the compute device. Note: This requires reinitializing models.

        Args:
            device: New device ('auto', 'cuda', 'cpu')
        """
        if not self._models_loaded or self.device != str(device):
            self._models_loaded = False
            self._loading_models = False
            self.requested_device = device
            self.face_analysis = None
            self._ensure_models_loaded()

    def get_device_info(self) -> dict:
        """Get information about current device configuration."""
        # Return placeholder info if models not loaded yet
        if not self._models_loaded:
            return {
                "device": "pending",
                "device_name": "Not loaded yet",
                "detector": "SCRFD-2.5GF",
                "recognizer": "ArcFace ResNet100",
                "requested_device": self.requested_device,
                "available_devices": get_available_devices(),
            }
        device_names = {
            "cuda": "NVIDIA GPU (CUDA via ONNX)",
            "cpu": "CPU (ONNX Runtime)",
        }
        device_upper = str(self.device).upper() if self.device else "UNKNOWN"
        return {
            "device": self.device,
            "device_name": device_names.get(self.device, device_upper),
            "detector": "SCRFD-2.5GF",
            "recognizer": "ArcFace ResNet100",
            "requested_device": self.requested_device,
            "available_devices": get_available_devices(),
        }
        device_names = {
            "cuda": "NVIDIA GPU (CUDA via ONNX)",
            "cpu": "CPU (ONNX Runtime)",
        }
        return {
            "device": self.device,
            "device_name": device_names.get(self.device, self.device.upper()),
            "detector": "SCRFD-2.5GF"
            if self.face_analysis.models.get("detention")
            else "SCRFD",
            "recognizer": "ArcFace ResNet100"
            if self.face_analysis.models.get("recognition")
            else "ArcFace",
            "requested_device": self.requested_device,
            "available_devices": get_available_devices(),
        }

    def _get_image_hash(self, filepath: str | Path) -> str:
        """Generate a hash for the image file path and modification time."""
        filepath = Path(filepath)
        stat = filepath.stat()
        content = f"{filepath.absolute()}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(content.encode()).hexdigest()

    def _pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format (BGR)."""
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        cv_image = np.array(pil_image)
        return cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)

    def detect_faces(
        self, image: Image.Image
    ) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float]:
        """
        Detect faces in an image using SCRFD.

        Args:
            image: PIL Image object

        Returns:
            Tuple of (face_tensors, boxes, probabilities, scale_factor)
        """
        self._ensure_models_loaded()
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Convert to OpenCV format
            cv_image = self._pil_to_cv2(image)

            # Detect faces with SCRFD
            assert self.face_analysis is not None, "FaceAnalysis not initialized"
            faces = self.face_analysis.get(cv_image)

            if not faces:
                return np.empty((0, 512)), None, None, 1.0

            # Extract boxes and probabilities
            boxes = np.array([face.bbox for face in faces])
            probs = np.array([face.det_score for face in faces])

            # Extract face tensors (already aligned by SCRFD)
            # SCRFD automatically handles rotation during detection
            face_tensors = []
            for face in faces:
                # Get aligned face embedding
                embedding = face.embedding
                face_tensors.append(embedding)

            if face_tensors:
                face_tensors = np.array(face_tensors)
            else:
                face_tensors = np.empty((0, 512))

            return face_tensors, boxes, probs, 1.0

        except Exception as e:
            print(f"Face detection error: {e}")
            return np.empty((0, 512)), None, None, 1.0

    def get_embeddings(self, face_tensors: np.ndarray) -> np.ndarray:
        """
        Get normalized face embeddings.
        Note: SCRFD + ArcFace already provides normalized embeddings.

        Args:
            face_tensors: Array of face embeddings [N, 512]

        Returns:
            Array of 512-dimensional normalized embeddings [N, 512]
        """
        self._ensure_models_loaded()
        # ArcFace embeddings are already normalized, but ensure it
        embeddings = face_tensors / np.linalg.norm(face_tensors, axis=1, keepdims=True)
        return embeddings

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
        if len(faces) == 0 or boxes is None or probs is None:
            return []

        # Get embeddings (already normalized from ArcFace)
        embeddings = faces  # SCRFD already gives us the ArcFace embeddings

        results = []
        for i, (embedding, box, prob) in enumerate(zip(embeddings, boxes, probs)):
            face_data = {
                "embedding": embedding,
                "box": box.tolist(),
                "confidence": float(prob),
                "thumbnail_path": None,
            }

            if self.cache_dir and box is not None:
                try:
                    img_hash = self._get_image_hash(filepath)
                    thumb_filename = f"{img_hash}_{i}.jpg"
                    thumb_path = self.cache_dir / thumb_filename

                    x1, y1, x2, y2 = map(int, box[:4])
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
        self, embedding1: np.ndarray, embedding2: np.ndarray, threshold: float = 0.5
    ) -> bool:
        """
        Determine if two face embeddings belong to the same person.
        ArcFace embeddings typically use a lower threshold (0.5) compared to
        traditional FaceNet (0.6) due to better angular separation.
        """
        return self.compute_similarity(embedding1, embedding2) > threshold
