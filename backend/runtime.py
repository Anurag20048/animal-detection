import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

from database.csv_logger import CSVLogger
from database.mongodb import MongoDBClient
from database.sqlite_storage import SQLiteStorage
from frame_processing import FrameProcessor
from services.alert_service import AlertService
from services.animal_service import AnimalService
from services.detection_service import DetectionService
from services.health_service import HealthService
from utils.security import create_access_token, decode_access_token, hash_password, verify_password
from video_stream import VideoStreamer
from config import settings

logger = logging.getLogger("django")

_video_streamer: VideoStreamer = VideoStreamer()
_runtime: Optional["Runtime"] = None


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
                "starting": False,
                "source": None,
                "last_fps": 0.0,
                "processed_frames": 0,
                "last_error": None,
            }
        return self._detection_service.stats()

    @property
    def video_streamer(self) -> VideoStreamer:
        return _video_streamer


def get_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime


def get_current_user(request) -> Dict[str, Any]:
    authorization = request.META.get("HTTP_AUTHORIZATION", "")
    if not authorization.lower().startswith("bearer "):
        raise ValueError("Authentication credentials were not provided.")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise ValueError("Invalid or expired authentication token.") from exc

    email = payload.get("sub")
    if not email:
        raise ValueError("Invalid authentication payload.")

    user = get_runtime().sqlite_storage.get_user_by_email(email)
    if user is None:
        raise ValueError("User not found.")

    return {
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
    }


def create_access_token_for_user(user_email: str) -> str:
    return create_access_token(
        data={"sub": user_email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
