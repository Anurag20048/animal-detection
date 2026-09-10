# Animal Detection & Re-Identification System

Camera-based animal detection, tracking, and visual re-identification using YOLO, ByteTrack, and deep visual embeddings.

> **Project status:** Phase 1 — repository cleanup and architecture preparation.
>
> The repository is being reconstructed from the available project source archives. Production deployment and animal-specific biometric accuracy have not yet been validated.

## Project Goal

The target workflow is:

```text
Camera
  ↓
YOLO Animal Detection
  ↓
ByteTrack Tracking
  ↓
Visual Feature Embedding
  ↓
Similarity Matching
  ├── Match → existing animal ID
  └── No match → create new animal ID
  ↓
Detection Event
  ├── Animal ID
  ├── Timestamp
  ├── Camera ID
  ├── Location
  ├── Detection Confidence
  └── Similarity Score
  ↓
Database / History
  ↓
Dashboard
```

## Current Capabilities

The reconstructed backend already contains:

- YOLOv8-based animal detection
- ByteTrack-based object tracking
- ResNet50 visual embeddings
- Cosine/weighted similarity recognition
- Automatic animal profile creation
- SQLite and CSV persistence
- Optional MongoDB persistence
- JWT-style authentication
- Image and video analysis APIs
- Live webcam/video detection
- Analytics and detection history
- CSV/PDF report endpoints
- Bootstrap 5 + Chart.js dashboard

## Technology Stack

| Layer | Technology |
|---|---|
| Detection | YOLOv8 / Ultralytics |
| Tracking | ByteTrack |
| Feature extraction | ResNet50 / PyTorch |
| Computer vision | OpenCV |
| ML runtime | PyTorch |
| API | FastAPI |
| Web/admin layer | Django |
| Database | SQLite / SQLAlchemy; MongoDB optional |
| Frontend | HTML, CSS, Bootstrap 5, JavaScript, Chart.js |
| Authentication | JWT-style bearer authentication |

## Repository Structure

```text
animal-detection/
├── backend/
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── database/
│   ├── utils/
│   ├── accounts/
│   ├── animals/
│   ├── identification/
│   ├── analytics_app/
│   ├── reports/
│   ├── dashboard/
│   ├── backend_site/
│   ├── app.py
│   ├── config.py
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
├── tests/
├── docs/
├── .gitignore
└── README.md
```

## Development Roadmap

- [x] Phase 1 — Clean repository structure and development configuration
- [ ] Phase 2 — Validate and harden animal detection
- [ ] Phase 3 — Improve animal re-identification and persistent IDs
- [ ] Phase 4 — Add camera identity, timestamps, and location history
- [ ] Phase 5 — Complete dashboard, animal profiles, analytics, and history
- [ ] Phase 6 — Testing, CI, and production hardening
- [ ] Phase 7 — Professional GitHub documentation and demo assets
- [ ] Phase 8 — Deployment and live/demo environment

See [`docs/PHASE-1.md`](docs/PHASE-1.md) for the Phase 1 scope.

## Local Setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
uvicorn app:app --reload
```

The development API is expected at `http://127.0.0.1:8000`.

### Frontend

The existing frontend can be served as a static application. Its API base URL should point to the running backend during local development.

## API Areas

The current backend exposes routes for authentication, animals, detections, history, analytics, reports, image/video analysis, and live detection. The API surface will be stabilized and tested in later phases.

## Data & Privacy

Local databases, uploaded media, generated crops, runtime logs, and credentials are intentionally excluded from Git. Use `.env.example` as the configuration template and keep real secrets in `.env`.

## Limitations

The current recognition pipeline uses generic deep visual embeddings and similarity matching. Region crops are an early implementation rather than specialized animal biometric models. Therefore, this project should be described as **animal re-identification using visual embeddings**, not as a clinically or scientifically validated biometric identification system.

Standard pretrained object-detection classes may not cover every livestock species equally; model/class coverage will be validated in Phase 2.

## License

See `LICENSE`.
