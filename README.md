# Animal Detection & Re-Identification System

A Python computer-vision project for detecting livestock, tracking animals across video frames, and assigning persistent visual re-identification IDs using **YOLO, ByteTrack, ResNet50 embeddings, and similarity matching**.

> **Project status:** Core implementation integrated and CI enabled. The project is suitable as a portfolio/demo system, while production deployment and animal-specific biometric accuracy remain unvalidated.

## What the system does

```text
Camera / Image / Video
        ↓
YOLO Detection
        ↓
ByteTrack Tracking
        ↓
ResNet50 Visual Embedding
        ↓
Similarity Matching
   ┌────┴─────┐
 MATCH      NO MATCH
   ↓            ↓
Existing ID   New Animal ID
   └────┬─────┘
        ↓
Detection Event
  • Animal ID
  • Species
  • Timestamp
  • Camera ID
  • Camera Location
  • Detection Confidence
  • Similarity Score
        ↓
SQLite / CSV / optional MongoDB
        ↓
History / Analytics / Reports
```

## Current capabilities

- YOLOv8/Ultralytics object detection
- ByteTrack object tracking
- Persistent animal IDs such as `C00017`, `S00004`, and `O00002`
- ResNet50 visual feature embeddings
- Weighted cosine-similarity matching
- Region-based crops for visual matching
- Camera registry with camera ID and location
- Normalized identity events with timestamp and confidence metadata
- Automatic animal profile creation
- SQLite and CSV persistence
- Optional MongoDB persistence
- FastAPI endpoints for authentication, animals, identification, history, analytics, and reports
- Django models/admin modules and migrations
- Image/video analysis and live webcam/video processing
- CSV/PDF reporting support
- Regression tests and GitHub Actions CI

## Technology stack

| Layer | Technology |
|---|---|
| Detection | YOLOv8 / Ultralytics |
| Tracking | ByteTrack |
| Feature extraction | ResNet50 / PyTorch / TorchVision |
| Computer vision | OpenCV |
| API | FastAPI |
| Web/admin layer | Django |
| Storage | SQLite / SQLAlchemy / CSV; MongoDB optional |
| Frontend | HTML, CSS, Bootstrap 5, JavaScript, Chart.js |
| Authentication | JWT-style bearer authentication |
| Testing / CI | Pytest / GitHub Actions |

## Repository structure

```text
animal-detection/
├── backend/
│   ├── api/                 # API routes and views
│   ├── models/              # Detector, tracker, embedding, recognizer
│   ├── services/            # Detection, animal, alert, health services
│   ├── database/            # SQLite, CSV, MongoDB adapters
│   ├── utils/               # Camera, image, similarity and security helpers
│   ├── accounts/            # Django authentication app
│   ├── animals/             # Animal profiles and images
│   ├── identification/      # Identification jobs/results
│   ├── analytics_app/       # Analytics models and views
│   ├── reports/             # Report endpoints
│   ├── dashboard/           # Django dashboard modules
│   ├── backend_site/        # Django project configuration
│   ├── app.py               # FastAPI entry point
│   ├── config.py            # Environment/configuration
│   ├── manage.py             # Django management entry point
│   └── requirements.txt
├── frontend/                 # Static dashboard assets
├── tests/                    # Regression tests
├── scripts/                  # Development/restore helpers
├── docs/                     # Phase and project documentation
├── .github/workflows/        # Continuous integration
├── .gitignore
├── LICENSE
└── README.md
```

## Quick start

### 1. Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

### 2. Start the FastAPI service

```powershell
uvicorn app:app --reload
```

The development API is expected at `http://127.0.0.1:8000`.

### 3. Run tests from the repository root

```powershell
pytest -q
```

GitHub Actions runs the same regression suite against the backend dependency set.

### 4. Frontend

The static frontend is located under `frontend/`. Serve it with a local static server and configure its API base URL for the running backend.

## Configuration

Copy `backend/.env.example` to `backend/.env` and configure values such as:

- `YOLO_MODEL_PATH` — detector weights
- `CAMERA_ID` — logical camera identifier
- `CAMERA_LOCATION` — camera location label
- camera source / camera configuration values
- database and optional MongoDB settings

Keep real credentials and local runtime data out of Git.

## API areas

The backend includes routes for:

- Authentication and current-user information
- Animal registration and animal profiles
- Image/video identification
- Detection history with filters and pagination
- Analytics
- CSV/PDF reports
- Live detection/video processing

The exact route definitions are maintained in the backend API and application URL modules.

## Recognition approach

The current re-identification pipeline is a **visual similarity system**:

1. Detect an animal with YOLO.
2. Track the detection with ByteTrack.
3. Generate a normalized ResNet50 embedding from the animal crop.
4. Compare the embedding with stored embeddings for the relevant species.
5. Reuse an existing animal ID when the similarity exceeds the configured threshold; otherwise create a new ID.
6. Update the stored representation using the configured embedding momentum.

This is useful for demonstrating an end-to-end re-identification architecture, but it should not be presented as a scientifically validated biometric system.

## Important limitations

- Generic pretrained ResNet50 embeddings are used; the model is not specifically trained for livestock identity recognition.
- Region crops are an early visual-feature strategy, not specialized nose/ear/stripe/fur biometric models.
- Similarity thresholds are configurable and have not been validated as production-grade accuracy metrics.
- Standard COCO detector weights do not provide validated coverage for every livestock species. Buffalo recognition requires appropriate custom detector weights if buffalo detection is required.
- Camera location is configuration metadata; the application does not automatically determine physical geolocation.
- Production deployment, large-scale performance, security hardening, and real-world accuracy still require environment-specific validation.

## Testing and CI

The repository includes regression tests covering core detector mapping, camera configuration, recognition behavior, and identity-event metadata. GitHub Actions installs `backend/requirements.txt` and runs `pytest -q` with the repository root on `PYTHONPATH`.

## Development roadmap

- [x] Repository cleanup and project documentation
- [x] YOLO detection and ByteTrack tracking architecture
- [x] Visual embedding and similarity recognition architecture
- [x] Persistent animal ID generation
- [x] Camera ID/location identity events
- [x] Complete backend source integration
- [x] Regression test suite and CI workflow
- [ ] Full environment-based runtime validation with real camera/video data
- [ ] Animal-specific embedding training/evaluation
- [ ] Production deployment and monitoring
- [ ] Demo dataset, screenshots, and performance benchmarks

## License

See [`LICENSE`](LICENSE).
