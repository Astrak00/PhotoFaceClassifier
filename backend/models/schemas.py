"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Photo schemas
class PhotoBase(BaseModel):
    filepath: str
    filename: str
    directory: str


class PhotoResponse(PhotoBase):
    id: int
    exif_date: Optional[datetime] = None
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Face schemas
class FaceBase(BaseModel):
    box: list[float] = Field(..., min_length=4, max_length=4)
    confidence: float


class FaceResponse(FaceBase):
    id: int
    photo_id: int
    person_id: Optional[int] = None
    thumbnail_path: Optional[str] = None

    class Config:
        from_attributes = True


class FaceWithPhoto(FaceResponse):
    photo: PhotoResponse


# Person schemas
class PersonBase(BaseModel):
    name: Optional[str] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    is_ignored: Optional[bool] = None


class PersonResponse(PersonBase):
    id: int
    cluster_id: int
    is_ignored: bool
    photo_count: int
    representative_face_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PersonWithFaces(PersonResponse):
    faces: list[FaceWithPhoto] = []


class PersonSummary(BaseModel):
    """Lightweight person info for lists."""
    id: int
    name: Optional[str] = None
    photo_count: int
    thumbnail_path: Optional[str] = None
    sample_thumbnails: list[str] = []


# Merge schemas
class MergePersonsRequest(BaseModel):
    keep_person_id: int
    merge_person_ids: list[int]


# Scan schemas
class ScanRequest(BaseModel):
    directory: str
    recursive: bool = True
    use_thumbnails: bool = True


class ScanProgress(BaseModel):
    scan_id: int
    status: str
    total_photos: int
    processed_photos: int
    total_faces: int
    total_persons: int
    current_file: Optional[str] = None
    error_message: Optional[str] = None


class ScanResponse(BaseModel):
    scan_id: int
    status: str
    message: str


# Export folder schemas
class FolderSpec(BaseModel):
    name: str
    person_ids: list[int]
    logic: str = Field(default='any', pattern='^(any|all)$')


class CreateFoldersRequest(BaseModel):
    output_directory: str
    folders: list[FolderSpec]
    overwrite: bool = False


class FolderResult(BaseModel):
    folder_name: str
    folder_path: str
    created_count: int
    error_count: int
    errors: list[dict] = []


class CreateFoldersResponse(BaseModel):
    success: bool
    results: list[FolderResult]


# Stats schemas
class SystemStats(BaseModel):
    total_photos: int
    processed_photos: int
    total_faces: int
    total_persons: int
    device: str  # 'mps', 'cuda', or 'cpu'


# Directory browsing
class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class DirectoryListResponse(BaseModel):
    current_path: str
    parent_path: Optional[str]
    entries: list[DirectoryEntry]
