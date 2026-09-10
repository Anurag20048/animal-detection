import base64
import io
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

import cv2
import numpy as np
from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fpdf import FPDF

from config import settings
from database.csv_logger import CSVLogger
from database.mongodb import MongoDBClient
from database.sqlite_storage import SQLiteStorage
from schemas import (
    LoginRequest,
    RegisterRequest,
    SettingsRequest,
    StartDetectionRequest,
)
from services.alert_service import AlertService
from services.animal_service import AnimalService
from services.detection_service import DetectionService
from services.health_service import HealthService
from utils.image_utils import draw_detection
from utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from video_stream import VideoStreamer
from frame_processing import FrameProcessor

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Smart Livestock Monitoring and Biometric Identification API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "file://",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


class Runtime:
    def __init__(self) -> None:
        self.settings = settings
        self.csv_logger = CSVLogger(settings.csv_dir)
        self.sqlite_storage = SQLiteStorage()
        self.mongodb = MongoDBClient(settings)
        self.alert_service = AlertService(self.csv_logger, self.mongodb)
        self.health_service = HealthService()
        self.animal_service = AnimalService(
            settings=self.settings,
            csv_logger=self.csv_logger,
            mongodb=self.mongodb,
            sqlite_storage=self.sqlite_storage,
            alert_service=self.alert_service,
            health_service=self.health_service,
        )
        self._detection_service: Optional[DetectionService] = None

        if self.mongodb.enabled and not self.mongodb.available:
            self.alert_service.create_alert(
                "MongoDB connection failed",
                "MongoDB is unavailable. Continuing with CSV and image storage.",
                severity="warning",
                metadata={"error": self.mongodb.error},
            )

        self._ensure_default_admin()

    def _ensure_default_admin(self) -> None:
        if self.sqlite_storage.get_user_count() == 0:
            self.sqlite_storage.create_user(
                {
                    "email": self.settings.admin_email.lower().strip(),
                    "username": "admin",
                    "full_name": "Administrator",
                    "hashed_password": hash_password(self.settings.admin_password),
                    "is_admin": True,
                    "created_at": datetime.utcnow(),
                }
            )
            logger.info("Created default admin user for backend access.")

    @property
    def detection_service(self) -> DetectionService:
        if self._detection_service is None:
            self._detection_service = DetectionService(
                settings=self.settings,
                animal_service=self.animal_service,
                alert_service=self.alert_service,
            )
        return self._detection_service

    def detection_stats(self) -> Dict[str, Any]:
        if self._detection_service is None:
            return {
                "running": False,
                "source": None,
                "last_fps": 0.0,
                "processed_frames": 0,
                "last_error": None,
            }
        return self._detection_service.stats()


_runtime: Optional[Runtime] = None
_video_streamer: VideoStreamer = VideoStreamer()


def get_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication payload.",
        )

    user = get_runtime().sqlite_storage.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return {
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
    }


@app.get("/health")
@app.get("/api/health/")
def health() -> Dict[str, Any]:
    runtime = get_runtime()
    return {
        "status": "ok",
        "mongodb": runtime.mongodb.status(),
        "csv": runtime.csv_logger.status(),
        "detection": runtime.detection_stats(),
        "database": {
            "path": str(settings.database_path),
            "url": settings.database_url,
        },
    }


@app.post("/auth/login")
@app.post("/api/auth/login/")
def login(payload: LoginRequest) -> Dict[str, Any]:
    runtime = get_runtime()
    user = runtime.sqlite_storage.get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/register")
@app.post("/api/auth/register/")
def register(
    payload: RegisterRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    runtime = get_runtime()
    if runtime.sqlite_storage.get_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")

    created = runtime.sqlite_storage.create_user(
        {
            "email": payload.email.lower().strip(),
            "username": payload.username or payload.email.split("@")[0],
            "full_name": payload.full_name or payload.username or payload.email,
            "hashed_password": hash_password(payload.password),
            "is_admin": payload.is_admin,
            "created_at": datetime.utcnow(),
        }
    )
    if created is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create user.")
    return {"message": "User registered successfully."}


@app.get("/auth/me")
@app.get("/api/auth/me/")
def auth_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return current_user


@app.get("/users")
def users(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    runtime = get_runtime()
    return {"items": runtime.sqlite_storage.list_users()}


@app.get("/animals")
@app.get("/api/animals/")
def animals() -> Dict[str, Any]:
    runtime = get_runtime()
    return {"items": runtime.animal_service.list_animals()}


@app.post("/animals")
@app.post("/api/animals/")
def create_animal(
    payload: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    runtime = get_runtime()
    payload = dict(payload)
    payload.setdefault("created_by", current_user.get("email", ""))
    return runtime.animal_service.register_manual_profile(payload)


@app.get("/animals/{animal_id}")
@app.get("/api/animals/{animal_id}/")
def animal_detail(animal_id: str) -> Dict[str, Any]:
    runtime = get_runtime()
    profile = runtime.animal_service.get_animal(animal_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Animal not found.")
    return profile


@app.get("/detections")
@app.get("/api/detections/")
def detections(limit: int = Query(default=200, ge=1, le=5000)) -> Dict[str, Any]:
    runtime = get_runtime()
    return {"items": runtime.animal_service.list_detections(limit=limit)}


@app.get("/alerts")
def alerts(limit: int = Query(default=200, ge=1, le=5000)) -> Dict[str, Any]:
    runtime = get_runtime()
    return {"items": runtime.alert_service.list_alerts(limit=limit)}


@app.get("/history")
@app.get("/api/history/")
def history(
    animal_type: Optional[str] = Query(default=None),
    species: Optional[str] = Query(default=None),
    animal_id: Optional[str] = Query(default=None),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    runtime = get_runtime()
    resolved_type = animal_type or species
    if runtime.sqlite_storage is not None:
        items = runtime.sqlite_storage.list_detections(
            animal_type=resolved_type,
            animal_id=animal_id,
            confidence_min=min_confidence,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
        )
    else:
        items = runtime.animal_service.list_detections(limit=limit)
        if resolved_type:
            items = [item for item in items if item.get("animal_type") == resolved_type]
        if animal_id:
            items = [item for item in items if item.get("animal_id") == animal_id]
        if min_confidence > 0.0:
            items = [
                item for item in items
                if float(item.get("confidence", 0.0) or 0.0) >= min_confidence
            ]
    return {"items": items}


@app.get("/analytics/summary")
@app.get("/api/analytics/")
@app.get("/api/analytics/summary/")
def analytics_summary() -> Dict[str, Any]:
    runtime = get_runtime()
    if runtime.sqlite_storage is not None:
        return runtime.sqlite_storage.analytics_summary()
    items = runtime.animal_service.list_detections(limit=1000)
    by_type: Dict[str, int] = {}
    daily_counts: Dict[str, int] = {}
    monthly_counts: Dict[str, int] = {}
    top_animals: Dict[str, int] = {}
    for row in items:
        animal_type = row.get("animal_type", "Unknown")
        by_type[animal_type] = by_type.get(animal_type, 0) + 1
        animal_id = row.get("animal_id", "Unknown")
        top_animals[animal_id] = top_animals.get(animal_id, 0) + 1
        ts = row.get("timestamp")
        date_key = str(ts)[:10] if ts else "unknown"
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        if date_key != "unknown":
            monthly_counts[date_key[:7]] = monthly_counts.get(date_key[:7], 0) + 1
    return {
        "total_detections": len(items),
        "by_type": by_type,
        "daily_counts": daily_counts,
        "monthly_counts": monthly_counts,
        "top_animals": [
            {"animal_id": animal_id, "count": count}
            for animal_id, count in sorted(top_animals.items(), key=lambda x: -x[1])[:8]
        ],
    }


@app.post("/detect/image")
@app.post("/api/identify/")
@app.post("/api/detect/image/")
def detect_image(
    file: UploadFile = File(...),
    confidence_threshold: float = Query(default=settings.confidence_threshold, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    filename = file.filename or "image"
    ext = Path(filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp"}:
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")

    contents = file.file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Unable to decode image file.")

    detections = get_runtime().detection_service.predict_image(
        frame, confidence_threshold=confidence_threshold
    )
    annotated = frame.copy()
    items = []
    for detection in detections:
        label = f"{detection.animal_type} {int(detection.confidence * 100)}%"
        draw_detection(annotated, detection.bbox, label)
        items.append(
            {
                "animal_type": detection.animal_type,
                "confidence": detection.confidence,
                "bbox": detection.bbox,
                "tracking_id": detection.tracking_id,
            }
        )

    _, encoded = cv2.imencode(".jpg", annotated)
    annotation_b64 = base64.b64encode(encoded.tobytes()).decode("utf-8")
    return {
        "items": items,
        "annotated_image": f"data:image/jpeg;base64,{annotation_b64}",
    }


@app.post("/upload/video")
@app.post("/api/upload/video/")
def upload_video(file: UploadFile = File(...)) -> Dict[str, Any]:
    filename = file.filename or f"upload_{uuid.uuid4().hex}.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        raise HTTPException(status_code=400, detail="Only video uploads are supported.")

    runtime = get_runtime()
    target = runtime.settings.upload_dir / f"{uuid.uuid4().hex}{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as buffer:
        buffer.write(file.file.read())

    return {
        "success": True,
        "message": "Video uploaded successfully.",
        "path": str(target),
    }


@app.post("/start-detection")
def start_detection(payload: StartDetectionRequest) -> Dict[str, Any]:
    runtime = get_runtime()
    if payload.confidence_threshold is not None:
        runtime.settings.confidence_threshold = payload.confidence_threshold

    res = runtime.detection_service.start(
        source=payload.source,
        show_window=payload.show_window,
    )

    camera_source = runtime.settings.parse_source(
        payload.source if payload.source is not None else runtime.settings.default_camera_source
    )
    if not _video_streamer.is_running():
        processor = FrameProcessor(
            settings=runtime.settings,
            animal_service=runtime.animal_service,
            alert_service=runtime.alert_service,
        )
        _video_streamer.start(camera_source=camera_source, frame_fn=processor.process_frame)

    return res


@app.post("/stop-detection")
def stop_detection() -> Dict[str, Any]:
    runtime = get_runtime()
    try:
        _video_streamer.stop()
    except Exception:
        pass
    return runtime.detection_service.stop()


@app.get("/stats")
def stats() -> Dict[str, Any]:
    runtime = get_runtime()
    analytics = analytics_summary()
    return {
        **runtime.animal_service.stats(),
        "detection": runtime.detection_stats(),
        "mongodb": runtime.mongodb.status(),
        "analytics": analytics,
    }


@app.get("/cameras")
def cameras() -> Dict[str, Any]:
    runtime = get_runtime()
    detection = runtime.detection_stats()
    return {
        "configured_sources": runtime.settings.camera_sources,
        "default_source": runtime.settings.default_camera_source,
        "active_source": detection.get("source"),
        "running": detection.get("running", False),
    }


@app.post("/settings")
def update_settings(payload: SettingsRequest) -> Dict[str, Any]:
    runtime = get_runtime()
    applied = runtime.settings.update(payload.dict(exclude_unset=True))
    return {
        "updated": applied,
        "current": {
            "confidence_threshold": runtime.settings.confidence_threshold,
            "low_confidence_alert_threshold": runtime.settings.low_confidence_alert_threshold,
            "recognition_threshold": runtime.settings.recognition_threshold,
            "default_camera_source": runtime.settings.default_camera_source,
            "yolo_model_path": runtime.settings.yolo_model_path,
            "enable_mongodb": runtime.settings.enable_mongodb,
        },
    }


@app.get("/reports/detections.csv")
@app.get("/api/reports/detections.csv")
def report_detections_csv() -> FileResponse:
    runtime = get_runtime()
    csv_path = runtime.csv_logger.path_for("detections")
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="detections.csv",
    )


def create_detection_report_pdf(rows: list[Dict[str, Any]]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Detection Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(4)

    for row in rows[:100]:
        timestamp = row.get("timestamp", "")
        animal_id = row.get("animal_id", "-")
        animal_type = row.get("animal_type", "-")
        confidence = float(row.get("confidence", 0.0) or 0.0)
        pdf.multi_cell(
            0,
            6,
            f"{timestamp} | {animal_id} | {animal_type} | Confidence: {confidence:.2f}",
        )
        pdf.ln(1)

    return pdf.output(dest="S").encode("latin-1")


@app.get("/reports/detections.pdf")
@app.get("/api/reports/detections.pdf")
def report_detections_pdf() -> Response:
    runtime = get_runtime()
    rows = runtime.sqlite_storage.list_detections(limit=200) if runtime.sqlite_storage else runtime.animal_service.list_detections(limit=200)
    pdf_content = create_detection_report_pdf(rows)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=detections_report.pdf"},
    )


@app.get("/video-feed")
def video_feed() -> object:
    def iter_frames():
        last_ts = 0.0
        while True:
            if not _video_streamer.is_running():
                import time
                time.sleep(0.1)
                continue
            jpg = _video_streamer.get_latest_jpeg()
            ts = _video_streamer.get_latest_timestamp()
            if jpg is None or ts == last_ts:
                import time
                time.sleep(0.02)
                continue
            last_ts = ts
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            )

    return StreamingResponse(
        iter_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/latest-detection-image")
def latest_detection_image() -> Response:
    jpg = _video_streamer.get_latest_jpeg()
    if jpg is None:
        return Response(status_code=204)
    return Response(content=jpg, media_type="image/jpeg")


def main() -> None:
    runtime = get_runtime()
    logger.info("Starting Smart Livestock Monitoring from webcam/video source.")
    logger.info(f"Source: {runtime.settings.default_camera_source}")
    runtime.detection_service.run(
        source=runtime.settings.default_camera_source,
        show_window=True,
    )


if __name__ == "__main__":
    main()
