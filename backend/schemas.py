from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class StartDetectionRequest(BaseModel):
    source: Optional[Union[str, int]] = Field(
        default=None,
        description="Webcam index, video file path, or IP camera URL.",
    )
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    show_window: bool = False


class SettingsRequest(BaseModel):
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    low_confidence_alert_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recognition_threshold: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    default_camera_source: Optional[str] = None
    yolo_model_path: Optional[str] = None
    enable_mongodb: Optional[bool] = None


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.lower().strip()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("Valid email is required.")
        return email


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.lower().strip()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("Valid email is required.")
        return email


class UploadResponse(BaseModel):
    success: bool
    message: str
    path: Optional[str] = None


class DetectionFilterParams(BaseModel):
    animal_type: Optional[str] = None
    animal_id: Optional[str] = None
    min_confidence: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    limit: Optional[int] = Field(default=200, ge=1, le=2000)


class AnalyticsSummary(BaseModel):
    total_detections: int
    by_type: Dict[str, int]
    daily_counts: Dict[str, int]
    monthly_counts: Dict[str, int]
    top_animals: List[Dict[str, Any]]
