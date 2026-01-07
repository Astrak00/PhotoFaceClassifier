"""
FastAPI backend for Photo Face Classifier.
Provides REST API endpoints for scanning photos, managing persons, and exporting folders.
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import numpy as np

from models.database import Database, Photo, Person, Face
from models.schemas import (
    ScanRequest, ScanResponse, ScanProgress,
    PersonResponse, PersonUpdate, PersonSummary, PersonWithFaces,
    MergePersonsRequest,
    CreateFoldersRequest, CreateFoldersResponse, FolderResult,
    SystemStats, DirectoryListResponse, DirectoryEntry,
    FaceResponse, FaceWithPhoto, PhotoResponse,
)
from services.raw_handler import RawHandler
from services.face_processor import FaceProcessor, get_available_devices
from services.clustering import cluster_faces, FaceClusterer
from services.folder_manager import FolderManager


# Global state
DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "faces.db"
CACHE_DIR = DATA_DIR / "cache"
CONFIG_PATH = DATA_DIR / "config.json"

# Initialize on startup
db: Optional[Database] = None
face_processor: Optional[FaceProcessor] = None
scan_progress: dict = {}

# Default configuration
app_config: dict = {
    'min_faces_per_person': 3,
    'device': 'auto',
}


def load_config():
    """Load configuration from file."""
    global app_config
    if CONFIG_PATH.exists():
        try:
            import json
            with open(CONFIG_PATH, 'r') as f:
                saved = json.load(f)
                app_config.update(saved)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")


def save_config():
    """Save configuration to file."""
    try:
        import json
        with open(CONFIG_PATH, 'w') as f:
            json.dump(app_config, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save config: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global db, face_processor
    
    # Create directories
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load configuration
    load_config()
    
    # Initialize database
    db = Database(DB_PATH)
    
    # Initialize face processor (loads models)
    print("Loading face detection models...")
    face_processor = FaceProcessor(cache_dir=CACHE_DIR)
    
    # Apply configured device
    if app_config['device'] != 'auto':
        face_processor.set_device(app_config['device'])
    
    print(f"Models loaded successfully! Using device: {face_processor.get_device_info()['device_name']}")
    
    yield
    
    # Cleanup
    print("Shutting down...")


app = FastAPI(
    title="Photo Face Classifier",
    description="Classify and organize photos by detected faces",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve face thumbnails
app.mount("/thumbnails", StaticFiles(directory=str(CACHE_DIR)), name="thumbnails")


# ============== Health & Stats ==============

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """Get system statistics."""
    session = db.get_session()
    try:
        total_photos = session.query(Photo).count()
        processed_photos = session.query(Photo).filter_by(processed=True).count()
        total_faces = session.query(Face).count()
        total_persons = session.query(Person).filter_by(is_ignored=False).count()
        
        device = str(face_processor.device) if face_processor else "unknown"
        
        return SystemStats(
            total_photos=total_photos,
            processed_photos=processed_photos,
            total_faces=total_faces,
            total_persons=total_persons,
            device=device,
        )
    finally:
        session.close()


# ============== Directory Browsing ==============

@app.get("/api/browse", response_model=DirectoryListResponse)
async def browse_directory(path: Optional[str] = None):
    """Browse directory structure for folder selection."""
    if path is None:
        path = str(Path.home())
    
    current = Path(path)
    if not current.exists() or not current.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")
    
    entries = []
    try:
        for item in sorted(current.iterdir()):
            # Skip hidden files and system directories
            if item.name.startswith('.'):
                continue
            if item.name in ('node_modules', '__pycache__', '.git'):
                continue
            
            entries.append(DirectoryEntry(
                name=item.name,
                path=str(item.absolute()),
                is_dir=item.is_dir(),
            ))
    except PermissionError:
        pass
    
    parent = str(current.parent.absolute()) if current.parent != current else None
    
    return DirectoryListResponse(
        current_path=str(current.absolute()),
        parent_path=parent,
        entries=entries,
    )


# ============== Scanning ==============

def run_scan(scan_id: int, directory: str, recursive: bool, use_thumbnails: bool):
    """Background task to scan directory for faces."""
    global scan_progress
    
    try:
        # Update status
        scan_progress[scan_id] = {
            'status': 'running',
            'total_photos': 0,
            'processed_photos': 0,
            'total_faces': 0,
            'total_persons': 0,
            'current_file': None,
            'error_message': None,
        }
        db.update_scan_session(scan_id, status='running', started_at=datetime.utcnow())
        
        # Scan directory for images
        image_files = RawHandler.scan_directory(directory, recursive=recursive)
        scan_progress[scan_id]['total_photos'] = len(image_files)
        db.update_scan_session(scan_id, total_photos=len(image_files))
        
        if not image_files:
            scan_progress[scan_id]['status'] = 'completed'
            scan_progress[scan_id]['error_message'] = 'No image files found'
            db.update_scan_session(scan_id, status='completed', completed_at=datetime.utcnow())
            return
        
        # Process each image
        all_face_ids = []
        all_embeddings = []
        
        for i, filepath in enumerate(image_files):
            scan_progress[scan_id]['current_file'] = str(filepath.name)
            
            # Check if already processed
            existing = db.get_photo(str(filepath))
            if existing and existing['processed']:
                scan_progress[scan_id]['processed_photos'] = i + 1
                continue
            
            # Add photo to database
            exif_date = RawHandler.get_exif_date(filepath)
            photo = db.add_photo(str(filepath), exif_date=exif_date)
            
            # Detect faces
            faces = face_processor.process_image(filepath, use_thumbnail=use_thumbnails)
            
            for face_data in faces:
                face = db.add_face(
                    photo_id=photo['id'],
                    box=face_data['box'],
                    confidence=face_data['confidence'],
                    embedding=face_data['embedding'],
                    thumbnail_path=face_data['thumbnail_path'],
                )
                all_face_ids.append(face['id'])
                all_embeddings.append(face_data['embedding'])
            
            # Mark photo as processed
            db.mark_photo_processed(photo['id'])
            
            # Update progress
            scan_progress[scan_id]['processed_photos'] = i + 1
            scan_progress[scan_id]['total_faces'] = len(all_face_ids)
        
        # Cluster faces into persons
        if all_embeddings:
            embeddings_array = np.array(all_embeddings)
            labels, cluster_info = cluster_faces(embeddings_array, min_photos_per_person=app_config['min_faces_per_person'])
            
            # Create person records
            session = db.get_session()
            try:
                # Clear existing persons (for re-scan)
                # session.query(Person).delete()
                
                unique_labels = set(labels)
                person_map = {}  # cluster_id -> person_id
                
                for cluster_id in unique_labels:
                    if cluster_id == -1:
                        continue  # Skip noise (rare appearances)
                    
                    # Check if person with this cluster already exists
                    existing_person = session.query(Person).filter_by(cluster_id=int(cluster_id)).first()
                    if existing_person:
                        person_map[cluster_id] = existing_person.id
                    else:
                        person = Person(cluster_id=int(cluster_id))
                        session.add(person)
                        session.flush()
                        person_map[cluster_id] = person.id
                
                session.commit()
                
                # Assign faces to persons
                for face_id, label in zip(all_face_ids, labels):
                    if label >= 0 and label in person_map:
                        db.update_face_person(face_id, person_map[label])
                
                # Update person photo counts and set representative faces
                for cluster_id, person_id in person_map.items():
                    db.update_person_photo_count(person_id)
                    
                    # Set representative face (highest confidence)
                    faces = session.query(Face).filter_by(person_id=person_id).order_by(Face.confidence.desc()).all()
                    if faces:
                        db.set_representative_face(person_id, faces[0].id)
                
                scan_progress[scan_id]['total_persons'] = len(person_map)
                
            finally:
                session.close()
        
        # Complete
        scan_progress[scan_id]['status'] = 'completed'
        scan_progress[scan_id]['current_file'] = None
        db.update_scan_session(
            scan_id,
            status='completed',
            completed_at=datetime.utcnow(),
            total_faces=len(all_face_ids),
            total_persons=scan_progress[scan_id]['total_persons'],
        )
        
    except Exception as e:
        scan_progress[scan_id]['status'] = 'failed'
        scan_progress[scan_id]['error_message'] = str(e)
        db.update_scan_session(scan_id, status='failed', error_message=str(e))
        raise


@app.post("/api/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start scanning a directory for faces."""
    directory = Path(request.directory)
    
    if not directory.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not directory.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    # Create scan session
    scan_session = db.create_scan_session(str(directory.absolute()))
    
    # Start background task
    background_tasks.add_task(
        run_scan,
        scan_session['id'],
        str(directory.absolute()),
        request.recursive,
        request.use_thumbnails,
    )
    
    return ScanResponse(
        scan_id=scan_session['id'],
        status='started',
        message=f'Scanning {directory}...',
    )


@app.get("/api/scan/{scan_id}/progress", response_model=ScanProgress)
async def get_scan_progress(scan_id: int):
    """Get progress of a scan."""
    if scan_id in scan_progress:
        progress = scan_progress[scan_id]
        return ScanProgress(
            scan_id=scan_id,
            **progress,
        )
    
    # Check database
    session = db.get_session()
    try:
        scan = session.query(db.Session).get(scan_id)
        if scan:
            return ScanProgress(
                scan_id=scan_id,
                status=scan.status,
                total_photos=scan.total_photos,
                processed_photos=scan.processed_photos,
                total_faces=scan.total_faces,
                total_persons=scan.total_persons,
                current_file=None,
                error_message=scan.error_message,
            )
    finally:
        session.close()
    
    raise HTTPException(status_code=404, detail="Scan not found")


@app.get("/api/scan/latest", response_model=ScanProgress)
async def get_latest_scan():
    """Get the latest scan session progress."""
    scan = db.get_latest_scan_session()
    if not scan:
        raise HTTPException(status_code=404, detail="No scans found")
    
    # Check in-memory progress first
    if scan['id'] in scan_progress:
        progress = scan_progress[scan['id']]
        return ScanProgress(scan_id=scan['id'], **progress)
    
    return ScanProgress(
        scan_id=scan['id'],
        status=scan['status'],
        total_photos=scan['total_photos'],
        processed_photos=scan['processed_photos'],
        total_faces=scan['total_faces'],
        total_persons=scan['total_persons'],
        current_file=None,
        error_message=scan['error_message'],
    )


# ============== Persons ==============

@app.get("/api/persons", response_model=list[PersonSummary])
async def list_persons(include_ignored: bool = False):
    """List all detected persons."""
    session = db.get_session()
    try:
        query = session.query(Person)
        if not include_ignored:
            query = query.filter_by(is_ignored=False)
        
        persons = query.order_by(Person.photo_count.desc()).all()
        
        result = []
        for person in persons:
            # Get sample face thumbnails
            faces = session.query(Face).filter_by(person_id=person.id).order_by(Face.confidence.desc()).limit(6).all()
            thumbnails = [f.thumbnail_path for f in faces if f.thumbnail_path]
            
            # Get representative thumbnail
            rep_thumb = None
            if person.representative_face_id:
                rep_face = session.query(Face).get(person.representative_face_id)
                if rep_face:
                    rep_thumb = rep_face.thumbnail_path
            elif thumbnails:
                rep_thumb = thumbnails[0]
            
            result.append(PersonSummary(
                id=person.id,
                name=person.name,
                photo_count=person.photo_count,
                thumbnail_path=rep_thumb,
                sample_thumbnails=thumbnails,
            ))
        
        return result
    finally:
        session.close()


@app.get("/api/persons/{person_id}", response_model=PersonWithFaces)
async def get_person(person_id: int):
    """Get detailed information about a person including all their faces."""
    session = db.get_session()
    try:
        person = session.query(Person).get(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        faces = session.query(Face).filter_by(person_id=person_id).all()
        
        face_list = []
        for face in faces:
            photo = session.query(Photo).get(face.photo_id)
            face_list.append(FaceWithPhoto(
                id=face.id,
                photo_id=face.photo_id,
                person_id=face.person_id,
                box=[face.box_x1, face.box_y1, face.box_x2, face.box_y2],
                confidence=face.confidence,
                thumbnail_path=face.thumbnail_path,
                photo=PhotoResponse(
                    id=photo.id,
                    filepath=photo.filepath,
                    filename=photo.filename,
                    directory=photo.directory,
                    exif_date=photo.exif_date,
                    processed=photo.processed,
                    created_at=photo.created_at,
                ),
            ))
        
        return PersonWithFaces(
            id=person.id,
            name=person.name,
            cluster_id=person.cluster_id,
            is_ignored=person.is_ignored,
            photo_count=person.photo_count,
            representative_face_id=person.representative_face_id,
            created_at=person.created_at,
            faces=face_list,
        )
    finally:
        session.close()


@app.patch("/api/persons/{person_id}", response_model=PersonResponse)
async def update_person(person_id: int, update: PersonUpdate):
    """Update a person's name or ignored status."""
    session = db.get_session()
    try:
        person = session.query(Person).get(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        if update.name is not None:
            person.name = update.name
        if update.is_ignored is not None:
            person.is_ignored = update.is_ignored
        
        session.commit()
        session.refresh(person)
        
        return PersonResponse(
            id=person.id,
            name=person.name,
            cluster_id=person.cluster_id,
            is_ignored=person.is_ignored,
            photo_count=person.photo_count,
            representative_face_id=person.representative_face_id,
            created_at=person.created_at,
        )
    finally:
        session.close()


@app.post("/api/persons/merge")
async def merge_persons(request: MergePersonsRequest):
    """Merge multiple persons into one."""
    if not request.merge_person_ids:
        raise HTTPException(status_code=400, detail="No persons to merge")
    
    session = db.get_session()
    try:
        # Verify all persons exist
        keep = session.query(Person).get(request.keep_person_id)
        if not keep:
            raise HTTPException(status_code=404, detail=f"Person {request.keep_person_id} not found")
        
        for merge_id in request.merge_person_ids:
            merge = session.query(Person).get(merge_id)
            if not merge:
                raise HTTPException(status_code=404, detail=f"Person {merge_id} not found")
            
            # Move all faces
            session.query(Face).filter_by(person_id=merge_id).update(
                {Face.person_id: request.keep_person_id}
            )
            
            # Delete merged person
            session.delete(merge)
        
        session.commit()
        
        # Update photo count
        db.update_person_photo_count(request.keep_person_id)
        
        return {"status": "success", "merged_count": len(request.merge_person_ids)}
    finally:
        session.close()


# ============== Export Folders ==============

@app.post("/api/export", response_model=CreateFoldersResponse)
async def create_export_folders(request: CreateFoldersRequest):
    """Create export folders with symlinks to photos."""
    output_dir = Path(request.output_directory)
    
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot create output directory: {e}")
    
    folder_manager = FolderManager(output_dir)
    results = []
    
    for folder_spec in request.folders:
        # Get photos for the specified persons
        photos = db.get_photos_for_persons(folder_spec.person_ids, logic=folder_spec.logic)
        
        # Prepare photo data with EXIF dates
        photo_data = []
        for photo in photos:
            photo_data.append({
                'filepath': photo['filepath'],
                'exif_date': photo['exif_date'],
            })
        
        # Create folder
        result = folder_manager.create_folder(
            folder_spec.name,
            photo_data,
            overwrite=request.overwrite,
        )
        
        results.append(FolderResult(
            folder_name=result['folder_name'],
            folder_path=result['folder_path'],
            created_count=result['created_count'],
            error_count=result['error_count'],
            errors=result['errors'],
        ))
    
    return CreateFoldersResponse(
        success=all(r.error_count == 0 for r in results),
        results=results,
    )


@app.get("/api/export/preview")
async def preview_export(
    person_ids: str = Query(..., description="Comma-separated person IDs"),
    logic: str = Query("any", pattern="^(any|all)$"),
):
    """Preview which photos would be included in an export."""
    try:
        ids = [int(x.strip()) for x in person_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid person IDs")
    
    photos = db.get_photos_for_persons(ids, logic=logic)
    
    return {
        "photo_count": len(photos),
        "photos": [
            {
                "id": p['id'],
                "filename": p['filename'],
                "filepath": p['filepath'],
                "exif_date": p['exif_date'].isoformat() if p['exif_date'] else None,
            }
            for p in photos[:100]  # Limit preview to 100
        ],
    }


# ============== Thumbnails ==============

@app.get("/api/thumbnail/{filename}")
async def get_thumbnail(filename: str):
    """Get a face thumbnail image."""
    thumb_path = CACHE_DIR / filename
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(thumb_path, media_type="image/jpeg")


# ============== Configuration ==============

@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    load_config()
    available_devices = get_available_devices()
    current_device = face_processor.get_device_info() if face_processor else {'device': 'unknown', 'device_name': 'Unknown'}
    
    return {
        "min_faces_per_person": app_config['min_faces_per_person'],
        "device": app_config['device'],
        "available_devices": available_devices,
        "current_device": current_device,
    }


@app.post("/api/config")
async def update_config(config: dict):
    """Update configuration."""
    global app_config
    
    if 'min_faces_per_person' in config:
        val = config['min_faces_per_person']
        if not isinstance(val, int) or val < 1 or val > 20:
            raise HTTPException(status_code=400, detail="min_faces_per_person must be between 1 and 20")
        app_config['min_faces_per_person'] = val
    
    if 'device' in config:
        device = config['device']
        available = get_available_devices()
        if device not in available:
            raise HTTPException(status_code=400, detail=f"Invalid device. Available: {available}")
        app_config['device'] = device
        
        # Apply device change to face processor
        if face_processor:
            face_processor.set_device(device)
    
    save_config()
    
    return {
        "status": "success",
        "config": {
            "min_faces_per_person": app_config['min_faces_per_person'],
            "device": app_config['device'],
        }
    }


# ============== Reset ==============

@app.post("/api/reset")
async def reset_database():
    """Reset all data (for testing)."""
    db.clear_all()
    
    # Clear cache
    for f in CACHE_DIR.glob("*.jpg"):
        f.unlink()
    
    # Clear progress
    scan_progress.clear()
    
    return {"status": "reset complete"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
