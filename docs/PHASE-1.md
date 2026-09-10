# Phase 1 — Project Cleanup & Repository Structure

## Goal
Prepare the Animal Detection project for maintainable development and later deployment without committing local environments, databases, generated runtime data, or secrets.

## Source of truth
The Phase 1 reconstruction is based on the supplied project archives. The backend archive contains the FastAPI runtime, Django wrapper/apps, detection models, recognition services, database adapters, and utilities. The frontend archive contains the existing dashboard assets.

## Keep
- Python application source
- Django app source and migrations
- FastAPI API/runtime code
- Frontend source
- Dependency manifests
- Configuration templates
- Documentation
- Tests and CI configuration when added
- Intentionally versioned model files only when repository size/licensing permits

## Exclude
- `.venv/` and other virtual environments
- `__pycache__/` and `*.pyc`
- Local SQLite/database files
- Uploaded videos and generated detection crops
- Temporary logs and test files
- `.env` and real credentials
- Generated model artifacts such as ONNX/TensorRT files

## Target architecture

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
├── LICENSE
└── README.md
```

## Current implementation boundary
The existing system already contains YOLOv8 detection, ByteTrack tracking, ResNet50 visual embeddings, similarity recognition, animal profiles, detection history, authentication, analytics, reports, image/video upload, and live webcam/video processing.

Phase 1 does not claim that production deployment or animal-specific biometric accuracy has been validated. Those items belong to later phases.

## Next phase
Phase 2 will validate and harden the YOLO detection pipeline on webcam, image, and video inputs before extending identity matching.
