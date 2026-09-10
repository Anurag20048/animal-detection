import os
from pathlib import Path
from typing import Any, Dict, List, Union

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class Settings:
    """Runtime settings, including explicit camera identity/location metadata."""

    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.project_root = self.base_dir.parent
        self.animal_data_dir = self.project_root / "animal_data"
        self.csv_dir = self.animal_data_dir / "csv"
        self.crop_dir = self.animal_data_dir / "crops"
        self.full_image_dir = self.animal_data_dir / "full_images"
        self.embedding_dir = self.animal_data_dir / "embeddings"

        self.yolo_model_path = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        self.yolo_tracker_config = os.getenv("YOLO_TRACKER_CONFIG", "bytetrack.yaml")
        self.confidence_threshold = _float_env("CONFIDENCE_THRESHOLD", 0.35)
        self.low_confidence_alert_threshold = _float_env("LOW_CONFIDENCE_ALERT_THRESHOLD", 0.50)
        self.recognition_threshold = _float_env("RECOGNITION_THRESHOLD", 0.80)
        self.embedding_momentum = _float_env("EMBEDDING_MOMENTUM", 0.90)
        self.resnet_pretrained = _bool_env("RESNET_PRETRAINED", True)

        self.enable_mongodb = _bool_env("ENABLE_MONGODB", True)
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.mongodb_database = os.getenv("MONGODB_DATABASE", "livestock_monitoring")
        self.mongodb_timeout_ms = int(os.getenv("MONGODB_TIMEOUT_MS", "1500"))

        self.default_camera_source = os.getenv("CAMERA_SOURCE", "0")
        self.camera_sources = self._parse_camera_sources(os.getenv("CAMERA_SOURCES", "0"))
        self.default_camera_id = os.getenv("CAMERA_ID", "CAM-001")
        self.default_camera_location = os.getenv("CAMERA_LOCATION", "Unknown")
        self.camera_configs = os.getenv("CAMERA_CONFIGS", "")

        self.database_path = self.project_root / "backend" / "data" / "app.db"
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{self.database_path.as_posix()}")
        self.upload_dir = self.project_root / "backend" / "data" / "uploads"
        self.reports_dir = self.project_root / "backend" / "data" / "reports"
        self.secret_key = os.getenv("SECRET_KEY", "replace-this-with-a-secure-secret")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@demo.com")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "Demo@123")

        self.region_weights = {"full": 0.40, "nose": 0.30, "eyes": 0.20, "forehead": 0.10}
        self.animal_prefixes = {"Cow": "C", "Buffalo": "B", "Sheep": "S", "Other Animals": "O"}
        self.ensure_directories()

    def ensure_directories(self) -> None:
        for path in [self.animal_data_dir, self.csv_dir, self.crop_dir, self.full_image_dir,
                     self.embedding_dir, self.project_root / "backend" / "data",
                     self.upload_dir, self.reports_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def update(self, values: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {"confidence_threshold", "low_confidence_alert_threshold", "recognition_threshold",
                   "default_camera_source", "default_camera_id", "default_camera_location",
                   "camera_configs", "yolo_model_path", "enable_mongodb"}
        applied: Dict[str, Any] = {}
        for key, value in values.items():
            if key in allowed and value is not None:
                setattr(self, key, value)
                applied[key] = value
        return applied

    @staticmethod
    def parse_source(source: Union[str, int, None]) -> Union[str, int]:
        if source is None:
            return 0
        if isinstance(source, int):
            return source
        source_text = str(source).strip()
        return int(source_text) if source_text.isdigit() else source_text

    @staticmethod
    def _parse_camera_sources(value: str) -> List[str]:
        sources = [item.strip() for item in value.split(",") if item.strip()]
        return sources or ["0"]


settings = Settings()
