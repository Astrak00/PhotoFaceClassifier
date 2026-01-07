"""
SQLite database models for face classification data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, make_transient

Base = declarative_base()


class Photo(Base):
    """Represents a photo file."""
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True)
    filepath = Column(String, unique=True, nullable=False, index=True)
    filename = Column(String, nullable=False)
    directory = Column(String, nullable=False)
    file_hash = Column(String, index=True)  # For detecting duplicates
    exif_date = Column(DateTime)
    width = Column(Integer)
    height = Column(Integer)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    faces = relationship('Face', back_populates='photo', cascade='all, delete-orphan')


class Person(Base):
    """Represents a person (cluster of faces)."""
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)  # User-assigned name
    cluster_id = Column(Integer, index=True)  # Original cluster ID from HDBSCAN
    is_ignored = Column(Boolean, default=False)  # User can mark to ignore
    photo_count = Column(Integer, default=0)
    representative_face_id = Column(Integer, ForeignKey('faces.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    faces = relationship('Face', back_populates='person', foreign_keys='Face.person_id')


class Face(Base):
    """Represents a detected face in a photo."""
    __tablename__ = 'faces'
    
    id = Column(Integer, primary_key=True)
    photo_id = Column(Integer, ForeignKey('photos.id'), nullable=False)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=True)
    
    # Bounding box (x1, y1, x2, y2)
    box_x1 = Column(Float, nullable=False)
    box_y1 = Column(Float, nullable=False)
    box_x2 = Column(Float, nullable=False)
    box_y2 = Column(Float, nullable=False)
    
    # Detection confidence
    confidence = Column(Float, nullable=False)
    
    # Face embedding (stored as binary for efficiency)
    embedding = Column(LargeBinary, nullable=False)
    
    # Thumbnail path
    thumbnail_path = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    photo = relationship('Photo', back_populates='faces')
    person = relationship('Person', back_populates='faces', foreign_keys=[person_id])
    
    @property
    def box(self) -> list[float]:
        return [self.box_x1, self.box_y1, self.box_x2, self.box_y2]
    
    @staticmethod
    def embedding_to_bytes(embedding: np.ndarray) -> bytes:
        """Convert numpy embedding to bytes for storage."""
        return embedding.astype(np.float32).tobytes()
    
    @staticmethod
    def bytes_to_embedding(data: bytes) -> np.ndarray:
        """Convert bytes back to numpy embedding."""
        return np.frombuffer(data, dtype=np.float32)


class ExportFolder(Base):
    """Represents a created export folder."""
    __tablename__ = 'export_folders'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    logic = Column(String, default='any')  # 'any' or 'all'
    person_ids = Column(Text)  # JSON array of person IDs
    photo_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def get_person_ids(self) -> list[int]:
        if self.person_ids:
            return json.loads(self.person_ids)
        return []
    
    def set_person_ids(self, ids: list[int]):
        self.person_ids = json.dumps(ids)


class ScanSession(Base):
    """Represents a scanning session."""
    __tablename__ = 'scan_sessions'
    
    id = Column(Integer, primary_key=True)
    source_directory = Column(String, nullable=False)
    status = Column(String, default='pending')  # pending, running, completed, failed
    total_photos = Column(Integer, default=0)
    processed_photos = Column(Integer, default=0)
    total_faces = Column(Integer, default=0)
    total_persons = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Database:
    """Database manager for face classification."""
    
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Synchronous engine for regular operations
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        # expire_on_commit=False allows objects to be used after session closes
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a database session."""
        return self.Session()
    
    def _detach(self, obj):
        """Detach an object from its session so it can be used independently."""
        if obj is not None:
            make_transient(obj)
        return obj
    
    # Photo operations
    def add_photo(self, filepath: str, exif_date: Optional[datetime] = None) -> dict:
        """Add or get a photo record. Returns dict with photo data."""
        filepath = str(Path(filepath).absolute())
        session = self.get_session()
        try:
            photo = session.query(Photo).filter_by(filepath=filepath).first()
            if photo is None:
                photo = Photo(
                    filepath=filepath,
                    filename=Path(filepath).name,
                    directory=str(Path(filepath).parent),
                    exif_date=exif_date
                )
                session.add(photo)
                session.commit()
            
            # Return a dict with the data we need
            return {
                'id': photo.id,
                'filepath': photo.filepath,
                'filename': photo.filename,
                'directory': photo.directory,
                'exif_date': photo.exif_date,
                'processed': photo.processed,
            }
        finally:
            session.close()
    
    def get_photo(self, filepath: str) -> Optional[dict]:
        """Get a photo by filepath. Returns dict or None."""
        filepath = str(Path(filepath).absolute())
        session = self.get_session()
        try:
            photo = session.query(Photo).filter_by(filepath=filepath).first()
            if photo is None:
                return None
            return {
                'id': photo.id,
                'filepath': photo.filepath,
                'filename': photo.filename,
                'directory': photo.directory,
                'exif_date': photo.exif_date,
                'processed': photo.processed,
            }
        finally:
            session.close()
    
    def get_all_photos(self) -> list[dict]:
        """Get all photos as dicts."""
        session = self.get_session()
        try:
            photos = session.query(Photo).all()
            return [{
                'id': p.id,
                'filepath': p.filepath,
                'filename': p.filename,
                'directory': p.directory,
                'exif_date': p.exif_date,
                'processed': p.processed,
            } for p in photos]
        finally:
            session.close()
    
    def mark_photo_processed(self, photo_id: int):
        """Mark a photo as processed."""
        session = self.get_session()
        try:
            photo = session.query(Photo).get(photo_id)
            if photo:
                photo.processed = True
                session.commit()
        finally:
            session.close()
    
    # Face operations
    def add_face(
        self,
        photo_id: int,
        box: list[float],
        confidence: float,
        embedding: np.ndarray,
        thumbnail_path: Optional[str] = None
    ) -> dict:
        """Add a face record. Returns dict with face data."""
        session = self.get_session()
        try:
            face = Face(
                photo_id=photo_id,
                box_x1=box[0],
                box_y1=box[1],
                box_x2=box[2],
                box_y2=box[3],
                confidence=confidence,
                embedding=Face.embedding_to_bytes(embedding),
                thumbnail_path=thumbnail_path
            )
            session.add(face)
            session.commit()
            
            return {
                'id': face.id,
                'photo_id': face.photo_id,
                'person_id': face.person_id,
                'confidence': face.confidence,
                'thumbnail_path': face.thumbnail_path,
            }
        finally:
            session.close()
    
    def get_all_faces(self) -> list[dict]:
        """Get all faces as dicts."""
        session = self.get_session()
        try:
            faces = session.query(Face).all()
            return [{
                'id': f.id,
                'photo_id': f.photo_id,
                'person_id': f.person_id,
                'box': [f.box_x1, f.box_y1, f.box_x2, f.box_y2],
                'confidence': f.confidence,
                'thumbnail_path': f.thumbnail_path,
            } for f in faces]
        finally:
            session.close()
    
    def get_all_embeddings(self) -> tuple[list[int], np.ndarray]:
        """Get all face embeddings."""
        session = self.get_session()
        try:
            faces = session.query(Face).all()
            if not faces:
                return [], np.array([])
            
            face_ids = [f.id for f in faces]
            embeddings = np.array([Face.bytes_to_embedding(f.embedding) for f in faces])
            return face_ids, embeddings
        finally:
            session.close()
    
    def update_face_person(self, face_id: int, person_id: int):
        """Assign a face to a person."""
        session = self.get_session()
        try:
            face = session.query(Face).get(face_id)
            if face:
                face.person_id = person_id
                session.commit()
        finally:
            session.close()
    
    # Person operations
    def add_person(self, cluster_id: int, name: Optional[str] = None) -> dict:
        """Add a person record. Returns dict with person data."""
        session = self.get_session()
        try:
            person = Person(cluster_id=cluster_id, name=name)
            session.add(person)
            session.commit()
            
            return {
                'id': person.id,
                'cluster_id': person.cluster_id,
                'name': person.name,
                'photo_count': person.photo_count,
            }
        finally:
            session.close()
    
    def get_person(self, person_id: int) -> Optional[dict]:
        """Get a person by ID. Returns dict or None."""
        session = self.get_session()
        try:
            person = session.query(Person).get(person_id)
            if person is None:
                return None
            return {
                'id': person.id,
                'cluster_id': person.cluster_id,
                'name': person.name,
                'is_ignored': person.is_ignored,
                'photo_count': person.photo_count,
                'representative_face_id': person.representative_face_id,
                'created_at': person.created_at,
            }
        finally:
            session.close()
    
    def get_all_persons(self) -> list[dict]:
        """Get all persons as dicts."""
        session = self.get_session()
        try:
            persons = session.query(Person).filter_by(is_ignored=False).all()
            return [{
                'id': p.id,
                'cluster_id': p.cluster_id,
                'name': p.name,
                'is_ignored': p.is_ignored,
                'photo_count': p.photo_count,
                'representative_face_id': p.representative_face_id,
                'created_at': p.created_at,
            } for p in persons]
        finally:
            session.close()
    
    def update_person_name(self, person_id: int, name: str):
        """Update a person's name."""
        session = self.get_session()
        try:
            person = session.query(Person).get(person_id)
            if person:
                person.name = name
                session.commit()
        finally:
            session.close()
    
    def merge_persons(self, keep_id: int, merge_id: int):
        """Merge two persons (move all faces from merge_id to keep_id)."""
        session = self.get_session()
        try:
            # Update all faces
            session.query(Face).filter_by(person_id=merge_id).update(
                {Face.person_id: keep_id}
            )
            
            # Update photo count
            keep_person = session.query(Person).get(keep_id)
            merge_person = session.query(Person).get(merge_id)
            
            if keep_person and merge_person:
                keep_person.photo_count += merge_person.photo_count
                session.delete(merge_person)
            
            session.commit()
        finally:
            session.close()
    
    def update_person_photo_count(self, person_id: int):
        """Update the photo count for a person."""
        session = self.get_session()
        try:
            person = session.query(Person).get(person_id)
            if person:
                # Count unique photos
                face_count = session.query(Face).filter_by(person_id=person_id).count()
                person.photo_count = face_count
                session.commit()
        finally:
            session.close()
    
    def set_representative_face(self, person_id: int, face_id: int):
        """Set the representative face for a person."""
        session = self.get_session()
        try:
            person = session.query(Person).get(person_id)
            if person:
                person.representative_face_id = face_id
                session.commit()
        finally:
            session.close()
    
    def get_or_create_person_by_cluster(self, cluster_id: int) -> dict:
        """Get or create a person by cluster ID. Returns dict."""
        session = self.get_session()
        try:
            person = session.query(Person).filter_by(cluster_id=cluster_id).first()
            if person is None:
                person = Person(cluster_id=cluster_id)
                session.add(person)
                session.commit()
            
            return {
                'id': person.id,
                'cluster_id': person.cluster_id,
                'name': person.name,
                'photo_count': person.photo_count,
            }
        finally:
            session.close()
    
    # Scan session operations
    def create_scan_session(self, source_directory: str) -> dict:
        """Create a new scan session. Returns dict."""
        session = self.get_session()
        try:
            scan = ScanSession(source_directory=source_directory)
            session.add(scan)
            session.commit()
            
            return {
                'id': scan.id,
                'source_directory': scan.source_directory,
                'status': scan.status,
                'total_photos': scan.total_photos,
                'processed_photos': scan.processed_photos,
            }
        finally:
            session.close()
    
    def update_scan_session(self, scan_id: int, **kwargs):
        """Update scan session fields."""
        session = self.get_session()
        try:
            scan = session.query(ScanSession).get(scan_id)
            if scan:
                for key, value in kwargs.items():
                    setattr(scan, key, value)
                session.commit()
        finally:
            session.close()
    
    def get_latest_scan_session(self) -> Optional[dict]:
        """Get the most recent scan session. Returns dict or None."""
        session = self.get_session()
        try:
            scan = session.query(ScanSession).order_by(
                ScanSession.created_at.desc()
            ).first()
            if scan is None:
                return None
            return {
                'id': scan.id,
                'source_directory': scan.source_directory,
                'status': scan.status,
                'total_photos': scan.total_photos,
                'processed_photos': scan.processed_photos,
                'total_faces': scan.total_faces,
                'total_persons': scan.total_persons,
                'error_message': scan.error_message,
            }
        finally:
            session.close()
    
    # Query operations for export
    def get_photos_for_persons(self, person_ids: list[int], logic: str = 'any') -> list[dict]:
        """
        Get photos containing specified persons.
        
        Args:
            person_ids: List of person IDs
            logic: 'any' (photos with any of the persons) or 
                   'all' (photos with all of the persons)
        
        Returns:
            List of photo dicts
        """
        session = self.get_session()
        try:
            if logic == 'any':
                # Photos with at least one of the specified persons
                faces = session.query(Face).filter(
                    Face.person_id.in_(person_ids)
                ).all()
                photo_ids = set(f.photo_id for f in faces)
            else:  # 'all'
                # Photos that contain ALL specified persons
                photo_ids = None
                for person_id in person_ids:
                    faces = session.query(Face).filter_by(person_id=person_id).all()
                    current_photo_ids = set(f.photo_id for f in faces)
                    if photo_ids is None:
                        photo_ids = current_photo_ids
                    else:
                        photo_ids &= current_photo_ids
                
                if photo_ids is None:
                    photo_ids = set()
            
            photos = session.query(Photo).filter(Photo.id.in_(photo_ids)).all()
            return [{
                'id': p.id,
                'filepath': p.filepath,
                'filename': p.filename,
                'directory': p.directory,
                'exif_date': p.exif_date,
                'processed': p.processed,
            } for p in photos]
        finally:
            session.close()
    
    def clear_all(self):
        """Clear all data (for testing or reset)."""
        session = self.get_session()
        try:
            session.query(Face).delete()
            session.query(Person).delete()
            session.query(Photo).delete()
            session.query(ScanSession).delete()
            session.query(ExportFolder).delete()
            session.commit()
        finally:
            session.close()
