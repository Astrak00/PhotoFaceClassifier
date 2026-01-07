"""
RAW image handler for processing Sony ARW files.
Extracts embedded JPEG thumbnails for fast face detection.
"""

import os
import io
from pathlib import Path
from typing import Optional
from datetime import datetime

import rawpy  # type: ignore
from PIL import Image
from PIL.ExifTags import TAGS


class RawHandler:
    """Handles RAW image files, particularly Sony ARW format."""
    
    SUPPORTED_EXTENSIONS = {'.arw', '.raw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.rw2'}
    
    @classmethod
    def is_supported(cls, filepath: str | Path) -> bool:
        """Check if a file is a supported RAW format."""
        return Path(filepath).suffix.lower() in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def extract_thumbnail(cls, filepath: str | Path) -> Optional[Image.Image]:
        """
        Extract embedded JPEG thumbnail from RAW file.
        This is much faster than full RAW processing (~50ms vs ~3s).
        
        Args:
            filepath: Path to the RAW file
            
        Returns:
            PIL Image object or None if extraction fails
        """
        try:
            with rawpy.imread(str(filepath)) as raw:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    return Image.open(io.BytesIO(thumb.data))
                elif thumb.format == rawpy.ThumbFormat.BITMAP:
                    # Some cameras store uncompressed thumbnails
                    return Image.fromarray(thumb.data)
        except Exception as e:
            print(f"Failed to extract thumbnail from {filepath}: {e}")
            return None
        return None
    
    @classmethod
    def process_full_raw(cls, filepath: str | Path) -> Optional[Image.Image]:
        """
        Process full RAW file for maximum quality.
        Use this for re-processing uncertain faces.
        
        Args:
            filepath: Path to the RAW file
            
        Returns:
            PIL Image object or None if processing fails
        """
        try:
            with rawpy.imread(str(filepath)) as raw:
                # Use auto white balance and standard demosaicing
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=False,  # Full resolution
                    no_auto_bright=False,
                    output_bps=8  # 8-bit for face detection
                )
                return Image.fromarray(rgb)
        except Exception as e:
            print(f"Failed to process RAW {filepath}: {e}")
            return None
    
    @classmethod
    def get_image(cls, filepath: str | Path, use_thumbnail: bool = True) -> Optional[Image.Image]:
        """
        Get image from file - handles both RAW and regular image formats.
        
        Args:
            filepath: Path to the image file
            use_thumbnail: For RAW files, use embedded thumbnail if True
            
        Returns:
            PIL Image object or None if loading fails
        """
        filepath = Path(filepath)
        
        if cls.is_supported(filepath):
            if use_thumbnail:
                img = cls.extract_thumbnail(filepath)
                if img is not None:
                    return img
                # Fall back to full processing if thumbnail extraction fails
            return cls.process_full_raw(filepath)
        else:
            # Regular image file (JPEG, PNG, etc.)
            try:
                return Image.open(filepath)
            except Exception as e:
                print(f"Failed to open image {filepath}: {e}")
                return None
    
    @classmethod
    def get_exif_date(cls, filepath: str | Path) -> Optional[datetime]:
        """
        Extract EXIF date from image file.
        
        Args:
            filepath: Path to the image file
            
        Returns:
            datetime object or None if not found
        """
        try:
            img = cls.get_image(filepath, use_thumbnail=True)
            if img is None:
                return None
                
            exif = getattr(img, '_getexif', lambda: None)()
            if exif is None:
                return None
                
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                elif tag == 'DateTime':
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            print(f"Failed to get EXIF date from {filepath}: {e}")
        
        # Fall back to file modification time
        try:
            mtime = os.path.getmtime(filepath)
            return datetime.fromtimestamp(mtime)
        except Exception:
            return None
    
    @classmethod
    def scan_directory(cls, directory: str | Path, recursive: bool = True) -> list[Path]:
        """
        Scan directory for supported image files.
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of paths to supported image files
        """
        directory = Path(directory)
        all_extensions = cls.SUPPORTED_EXTENSIONS | {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        
        image_files = []
        
        if recursive:
            for ext in all_extensions:
                image_files.extend(directory.rglob(f'*{ext}'))
                image_files.extend(directory.rglob(f'*{ext.upper()}'))
        else:
            for ext in all_extensions:
                image_files.extend(directory.glob(f'*{ext}'))
                image_files.extend(directory.glob(f'*{ext.upper()}'))
        
        # Remove duplicates and sort
        return sorted(set(image_files))
