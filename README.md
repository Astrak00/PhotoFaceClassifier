# Photo Face Classifier

A local, GPU-accelerated photo organization tool that automatically detects and groups faces in your photos. Perfect for photographers who need to sort through large collections of images by the people in them.

## Features

- **Face Detection & Recognition**: Uses MTCNN for face detection and FaceNet (InceptionResnetV1) for face embeddings
- **GPU Acceleration**: Optimized for Apple Silicon M-series chips using MPS (Metal Performance Shaders)
- **RAW Support**: Native support for Sony ARW files and other RAW formats (CR2, CR3, NEF, DNG, ORF, RW2)
- **Fast Scanning**: Uses embedded JPEG thumbnails from RAW files for quick initial scanning
- **Automatic Clustering**: HDBSCAN groups similar faces into person clusters automatically
- **Manual Refinement**: Name people, merge duplicates, and correct mistakes through the web UI
- **Flexible Export**: Create custom folders with symlinks based on people combinations
  - **ANY** mode: Photos with at least one of the selected people
  - **ALL** mode: Photos with all of the selected people (group shots)
- **Non-Destructive**: Original files are never modified; uses symbolic links

## Tech Stack

| Component | Technology |
|-----------|------------|
| Face Detection | facenet-pytorch (MTCNN) |
| Face Recognition | facenet-pytorch (InceptionResnetV1/FaceNet) |
| RAW Processing | rawpy |
| Clustering | HDBSCAN |
| Backend | FastAPI (Python) |
| Database | SQLite |
| Frontend | React + TypeScript + Tailwind CSS |
| Build Tools | uv (Python), Bun (JavaScript) |

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4) for GPU acceleration
- Python 3.11 or 3.12
- Bun (JavaScript runtime)
- ~500MB disk space for models (downloaded on first run)

## Installation

### 1. Install uv (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Bun (JavaScript runtime)

```bash
curl -fsSL https://bun.sh/install | bash
```

### 3. Install Backend Dependencies

```bash
cd backend
uv sync
```

### 4. Install Frontend Dependencies

```bash
cd frontend
bun install
```

## Running the Application

You need to run both the backend and frontend in separate terminals.

### Terminal 1: Start Backend

```bash
./start-backend.sh
# Or manually:
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start on http://localhost:8000. On first run, it will download the face recognition models (~100MB).

### Terminal 2: Start Frontend

```bash
./start-frontend.sh
# Or manually:
cd frontend
bun run dev
```

The frontend will start on http://localhost:5173.

## Usage

### 1. Scan Photos

1. Open http://localhost:5173 in your browser
2. Navigate to the **Scan** tab
3. Browse to select your photos directory
4. Configure options:
   - **Include subdirectories**: Scan nested folders
   - **Use embedded thumbnails**: Faster scanning (recommended)
5. Click **Start Scan**

The scanner will:
- Find all supported image files
- Extract faces from each image
- Generate face embeddings
- Automatically cluster similar faces into "persons"

### 2. Review People

1. Go to the **People** tab
2. You'll see detected persons as cards with sample face thumbnails
3. Click on a person's name to rename them
4. Select multiple persons and click **Merge Selected** to combine duplicates

### 3. Export Folders

1. Go to the **Export** tab
2. Select an output directory
3. Click **Add Folder** to create export folder configurations
4. For each folder:
   - Enter a folder name (e.g., "Family Photos")
   - Select which people to include
   - Choose logic:
     - **ANY**: Include photos with at least one selected person
     - **ALL**: Include photos with all selected people
5. Click **Create Folders**

The tool creates symbolic links to your original photos, so no disk space is wasted.

## API Endpoints

The backend provides a REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/stats` | GET | System statistics |
| `/api/browse` | GET | Browse directories |
| `/api/scan` | POST | Start scanning |
| `/api/scan/{id}/progress` | GET | Get scan progress |
| `/api/persons` | GET | List all persons |
| `/api/persons/{id}` | GET/PATCH | Get/update person |
| `/api/persons/merge` | POST | Merge persons |
| `/api/export` | POST | Create export folders |
| `/api/export/preview` | GET | Preview export |

Full API docs available at http://localhost:8000/docs when the backend is running.

## Performance

Estimated processing times on Apple Silicon M4:

| Operation | Time |
|-----------|------|
| Thumbnail extraction | ~50ms per image |
| Face detection | ~100ms per image |
| Face embedding | ~20ms per face |
| Clustering (10k faces) | ~2 seconds |

For 10,000 images with ~2 faces each:
- **With thumbnails**: ~15-20 minutes
- **Full RAW processing**: ~8-10 hours

## Project Structure

```
img_classifier/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models/
│   │   ├── database.py      # SQLite models
│   │   └── schemas.py       # Pydantic schemas
│   ├── services/
│   │   ├── raw_handler.py   # RAW/image processing
│   │   ├── face_processor.py # Face detection/recognition
│   │   ├── clustering.py    # HDBSCAN clustering
│   │   └── folder_manager.py # Symlink folder creation
│   └── data/
│       ├── faces.db         # SQLite database
│       └── cache/           # Face thumbnails
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application
│   │   ├── api.ts           # API client
│   │   └── pages/
│   │       ├── ScanPage.tsx
│   │       ├── PeoplePage.tsx
│   │       └── ExportPage.tsx
│   └── package.json
├── start-backend.sh
└── start-frontend.sh
```

## Troubleshooting

### Models not loading
The face recognition models are downloaded automatically on first run. If this fails, check your internet connection.

### MPS not available
If you see "Using CPU for face processing", ensure you have:
- PyTorch 2.0+ installed
- macOS 12.3+
- Apple Silicon Mac

### Scan is slow
- Enable "Use embedded thumbnails" option
- Ensure MPS is being used (check terminal output)
- Close other GPU-intensive applications

### Faces not clustering correctly
- Increase `min_cluster_size` in `clustering.py` for fewer, larger clusters
- Decrease it for more granular grouping
- Use the merge feature to manually combine similar persons

## License

MIT License
