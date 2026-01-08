# Photo Face Classifier

A local, GPU-accelerated photo organization tool that automatically detects and groups faces in your photos. Perfect for photographers who need to sort through large collections of images by the people in them.

- [Features](#features)
- [Download](#download)
- [Tech Stack](#tech-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Usage](#usage)
  - [Scan Photos](#1-scan-photos)
  - [Review People](#2-review-people)
  - [Export Folders](#3-export-folders)
- [API Endpoints](#api-endpoints)
- [License](#license)

## Features

- **Face Detection & Recognition**: Uses MTCNN for face detection and FaceNet (InceptionResnetV1) for face embeddings
- **GPU Acceleration**: Optimized for Apple Silicon M-series chips using MPS (Metal Performance Shaders) and CUDA.
- **RAW Support**: Native support for Sony ARW files and other RAW formats (CR2, CR3, NEF, DNG, ORF, RW2)
- **Fast Scanning**: Uses embedded JPEG thumbnails from RAW files for quick initial scanning
- **Automatic Clustering**: HDBSCAN groups similar faces into person clusters automatically
- **Manual Refinement**: Name people, merge duplicates, and correct mistakes through the web UI
- **Flexible Export**: Create custom folders with symlinks based on people combinations
  - **ANY** mode: Photos with at least one of the selected people
  - **ALL** mode: Photos with all of the selected people (group shots)
- **Non-Destructive**: Original files are never modified; uses symbolic links

## Download 
To get the latest version, go to the [Releases](https://github.com/Astrak00/face_recognition_organizer/releases/latest) page and download the appropriate package for your system.

> [!NOTE]
> If the latest release is not available for your platform, you can build and run the application from source by following the instructions below. [link](#installation)

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
- Optional: NVIDIA GPU with CUDA for non-Apple systems
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

### 3. Build the application

```bash
./build.sh
```

## Running the Application

The result of building the application is one single executable, containing all the necessary files.

## Usage

### 1. Scan Photos

1. Open the appplication
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


## License

MIT License
