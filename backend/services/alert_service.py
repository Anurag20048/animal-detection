import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.csv_logger import CSVLogger
from database.mongodb import MongoDBClient


class AlertService:
    def __init__(self, csv_logger: CSVLogger, mongodb: MongoDBClient) -> None:
        self.csv_logger = csv_logger
        self.mongodb = mongodb

    def create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "metadata": json.dumps(metadata or {}, ensure_ascii=True),
        }
        self.csv_logger.log_alert(record)
        self.mongodb.insert_one("alerts", record)
        return record

    def log_system(
        self,
        message: str,
        level: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "level": level,
            "message": message,
            "metadata": json.dumps(metadata or {}, ensure_ascii=True),
        }
        self.csv_logger.log_system(record)
        self.mongodb.insert_one("system_logs", record)

    def log_camera(
        self,
        event: str,
        source: str,
        status: str,
        camera_id: str = "default",
        fps: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "camera_id": camera_id,
            "source": source,
            "event": event,
            "status": status,
            "fps": round(float(fps), 2),
            "metadata": json.dumps(metadata or {}, ensure_ascii=True),
        }
        self.csv_logger.log_camera(record)

    def list_alerts(self, limit: int = 200) -> List[Dict[str, Any]]:
        rows = self.csv_logger.read_rows("alerts", limit=limit)
        return list(reversed(rows))
