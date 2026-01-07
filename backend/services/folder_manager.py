"""
Folder manager for creating symlink-based organization folders.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import shutil


class FolderManager:
    """
    Manages creation of output folders with symlinks to original photos.
    Handles naming conflicts using EXIF date.
    """
    
    def __init__(self, output_base: str | Path):
        """
        Initialize folder manager.
        
        Args:
            output_base: Base directory for output folders
        """
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)
    
    def _resolve_name_conflict(
        self,
        target_dir: Path,
        filename: str,
        exif_date: Optional[datetime]
    ) -> str:
        """
        Resolve filename conflicts using EXIF date or incrementing suffix.
        
        Args:
            target_dir: Directory where file will be linked
            filename: Original filename
            exif_date: EXIF date from the photo (if available)
            
        Returns:
            Resolved filename that doesn't conflict
        """
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        
        # Check if original name is available
        if not (target_dir / filename).exists():
            return filename
        
        # Try with date prefix
        if exif_date:
            date_prefix = exif_date.strftime('%Y-%m-%d')
            dated_name = f"{date_prefix}_{filename}"
            if not (target_dir / dated_name).exists():
                return dated_name
        
        # Fall back to incrementing suffix
        counter = 1
        while True:
            if exif_date:
                date_prefix = exif_date.strftime('%Y-%m-%d')
                new_name = f"{date_prefix}_{stem}_{counter}{suffix}"
            else:
                new_name = f"{stem}_{counter}{suffix}"
            
            if not (target_dir / new_name).exists():
                return new_name
            counter += 1
            
            # Safety limit
            if counter > 10000:
                raise RuntimeError(f"Too many filename conflicts for {filename}")
    
    def create_folder(
        self,
        folder_name: str,
        photos: list[dict],
        overwrite: bool = False
    ) -> dict:
        """
        Create a folder with symlinks to photos.
        
        Args:
            folder_name: Name of the folder to create
            photos: List of photo dicts with 'filepath' and optional 'exif_date' keys
            overwrite: If True, remove existing folder first
            
        Returns:
            Dictionary with creation results
        """
        # Sanitize folder name
        safe_name = "".join(c for c in folder_name if c.isalnum() or c in ' -_').strip()
        if not safe_name:
            safe_name = "Untitled"
        
        folder_path = self.output_base / safe_name
        
        # Handle existing folder
        if folder_path.exists():
            if overwrite:
                shutil.rmtree(folder_path)
            else:
                # Find unique name
                counter = 1
                while folder_path.exists():
                    folder_path = self.output_base / f"{safe_name} ({counter})"
                    counter += 1
        
        folder_path.mkdir(parents=True, exist_ok=True)
        
        created = []
        errors = []
        
        for photo in photos:
            filepath = Path(photo['filepath'])
            exif_date = photo.get('exif_date')
            
            if not filepath.exists():
                errors.append({
                    'filepath': str(filepath),
                    'error': 'File not found'
                })
                continue
            
            # Resolve filename conflicts
            link_name = self._resolve_name_conflict(
                folder_path,
                filepath.name,
                exif_date
            )
            
            link_path = folder_path / link_name
            
            try:
                # Create symlink
                os.symlink(filepath.absolute(), link_path)
                created.append({
                    'original': str(filepath),
                    'link': str(link_path),
                    'link_name': link_name
                })
            except OSError as e:
                errors.append({
                    'filepath': str(filepath),
                    'error': str(e)
                })
        
        return {
            'folder_path': str(folder_path),
            'folder_name': folder_path.name,
            'created_count': len(created),
            'error_count': len(errors),
            'created': created,
            'errors': errors
        }
    
    def create_folders_batch(
        self,
        folder_specs: list[dict],
        overwrite: bool = False
    ) -> list[dict]:
        """
        Create multiple folders at once.
        
        Args:
            folder_specs: List of folder specifications:
                - name: Folder name
                - photos: List of photo dicts
            overwrite: If True, overwrite existing folders
            
        Returns:
            List of creation results
        """
        results = []
        for spec in folder_specs:
            result = self.create_folder(
                spec['name'],
                spec['photos'],
                overwrite=overwrite
            )
            results.append(result)
        return results
    
    def delete_folder(self, folder_name: str) -> bool:
        """
        Delete an output folder and all its symlinks.
        
        Args:
            folder_name: Name of the folder to delete
            
        Returns:
            True if deleted, False if not found
        """
        folder_path = self.output_base / folder_name
        if folder_path.exists() and folder_path.is_dir():
            shutil.rmtree(folder_path)
            return True
        return False
    
    def list_folders(self) -> list[dict]:
        """
        List all output folders.
        
        Returns:
            List of folder info dicts
        """
        folders = []
        for path in self.output_base.iterdir():
            if path.is_dir():
                # Count symlinks
                links = list(path.glob('*'))
                folders.append({
                    'name': path.name,
                    'path': str(path),
                    'link_count': len(links)
                })
        return folders
    
    def get_folder_contents(self, folder_name: str) -> list[dict]:
        """
        Get contents of a folder.
        
        Args:
            folder_name: Name of the folder
            
        Returns:
            List of link info dicts
        """
        folder_path = self.output_base / folder_name
        if not folder_path.exists():
            return []
        
        contents = []
        for link in folder_path.iterdir():
            if link.is_symlink():
                target = link.resolve()
                contents.append({
                    'link_name': link.name,
                    'link_path': str(link),
                    'target': str(target),
                    'exists': target.exists()
                })
        return contents
