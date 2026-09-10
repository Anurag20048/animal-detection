import csv
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except Exception:
    pd = None


class CSVLogger:
    """CSV persistence for the livestock system.

    All CSV files are created in one explicit directory:
    animal detection/animal_data/csv/
    """

    SCHEMAS: Dict[str, List[str]] = {
        "animals": [
            "animal_id",
            "animal_type",
            "first_seen_time",
            "last_seen_time",
            "total_sightings",
            "best_image_path",
            "average_similarity_score",
            "movement_score",
            "feeding_score",
            "activity_score",
            "overall_health_score",
            "health_score",
            "status",
        ],
        "detections": [
            "detection_id",
            "tracking_id",
            "animal_id",
            "animal_type",
            "timestamp",
            "confidence",
            "similarity_score",
            "full_image_path",
            "forehead_image_path",
            "eyes_image_path",
            "nose_image_path",
            "camera_id",
        ],
        "alerts": [
            "alert_id",
            "timestamp",
            "alert_type",
            "severity",
            "message",
            "metadata",
        ],
        "system_logs": [
            "timestamp",
            "level",
            "message",
            "metadata",
        ],
        "health_records": [
            "health_record_id",
            "timestamp",
            "animal_id",
            "movement_score",
            "feeding_score",
            "activity_score",
            "overall_health_score",
            "health_score",
            "status",
            "metadata",
        ],
        "camera_logs": [
            "camera_log_id",
            "timestamp",
            "camera_id",
            "source",
            "event",
            "status",
            "fps",
            "metadata",
        ],
    }

    FILE_NAMES = {
        "animals": "animals.csv",
        "detections": "detections.csv",
        "alerts": "alerts.csv",
        "system_logs": "system_logs.csv",
        "health_records": "health_records.csv",
        "camera_logs": "camera_logs.csv",
    }

    def __init__(self, csv_dir: Path) -> None:
        self.csv_dir = Path(csv_dir).resolve()
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.paths = {
            name: self.csv_dir / file_name for name, file_name in self.FILE_NAMES.items()
        }
        self.ensure_files()

    def ensure_files(self) -> None:
        for name in self.SCHEMAS:
            self._ensure_file(name)

    def path_for(self, name: str) -> Path:
        try:
            return self.paths[name]
        except KeyError as exc:
            raise KeyError(f"Unknown CSV table: {name}") from exc

    def log_detection(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault("detection_id", str(uuid.uuid4()))
        self._append("detections", payload)

    def log_alert(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault("alert_id", str(uuid.uuid4()))
        payload.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        self._append("alerts", payload)

    def log_system(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        payload.setdefault("level", "info")
        self._append("system_logs", payload)

    def log_health(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault("health_record_id", str(uuid.uuid4()))
        payload.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        self._append("health_records", payload)

    def log_camera(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault("camera_log_id", str(uuid.uuid4()))
        payload.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        self._append("camera_logs", payload)

    def upsert_animal(self, profile: Dict[str, Any]) -> None:
        animal_id = str(profile.get("animal_id", "")).strip()
        if not animal_id:
            return

        with self._lock:
            rows = self.read_rows("animals")
            updated_row = self._filter_row("animals", profile)
            for index, row in enumerate(rows):
                if str(row.get("animal_id", "")).strip() == animal_id:
                    rows[index] = updated_row
                    break
            else:
                rows.append(updated_row)
            self._write_rows("animals", rows)

    def read_rows(self, name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        path = self.path_for(name)
        self._ensure_file(name)
        if path.stat().st_size == 0:
            return []

        if pd is not None:
            try:
                frame = pd.read_csv(path, dtype=str).fillna("")
                if limit is not None and limit > 0:
                    frame = frame.tail(limit)
                return frame.to_dict(orient="records")
            except Exception:
                pass

        with self._lock:
            with path.open("r", newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        if limit is not None and limit > 0:
            return rows[-limit:]
        return rows

    def status(self) -> Dict[str, Any]:
        return {
            "csv_dir": str(self.csv_dir),
            "files": {name: str(path) for name, path in self.paths.items()},
        }

    def _append(self, name: str, record: Dict[str, Any]) -> None:
        with self._lock:
            self._ensure_file(name)
            with self.path_for(name).open("a", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.SCHEMAS[name])
                writer.writerow(self._filter_row(name, record))

    def _write_rows(self, name: str, rows: List[Dict[str, Any]]) -> None:
        with self.path_for(name).open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.SCHEMAS[name])
            writer.writeheader()
            for row in rows:
                writer.writerow(self._filter_row(name, row))

    def _ensure_file(self, name: str) -> None:
        path = self.path_for(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 0:
            return
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.SCHEMAS[name])
            writer.writeheader()

    def _filter_row(self, name: str, record: Dict[str, Any]) -> Dict[str, str]:
        return {
            field: self._to_csv_value(record.get(field, ""))
            for field in self.SCHEMAS[name]
        }

    def _to_csv_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=True, default=str)
        return str(value)
