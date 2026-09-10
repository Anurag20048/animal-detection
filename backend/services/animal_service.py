import json
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np

from config import Settings
from database.csv_logger import CSVLogger
from database.mongodb import MongoDBClient
from database.sqlite_storage import SQLiteStorage
from models.recognizer import BiometricRecognizer
from models.tracker import TrackBiometricMapper
from services.alert_service import AlertService
from services.health_service import HealthService
from utils.id_generator import AnimalIDGenerator


class AnimalService:
    def __init__(
        self,
        settings: Settings,
        csv_logger: CSVLogger,
        mongodb: MongoDBClient,
        sqlite_storage: Optional[SQLiteStorage],
        alert_service: AlertService,
        health_service: HealthService,
    ) -> None:
        self.settings = settings
        self.csv_logger = csv_logger
        self.mongodb = mongodb
        self.sqlite_storage = sqlite_storage
        self.alert_service = alert_service
        self.health_service = health_service
        self.id_generator = AnimalIDGenerator(settings.animal_prefixes)
        self.tracker = TrackBiometricMapper()
        self.recognizer = BiometricRecognizer(
            similarity_threshold=settings.recognition_threshold,
            region_weights=settings.region_weights,
            embedding_momentum=settings.embedding_momentum,
        )
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.embedding_store_path = settings.embedding_dir / "embeddings.json"
        self._lock = RLock()

        self._load_profiles()
        self._load_embeddings()

    def process_detection(
        self,
        tracking_id: int,
        animal_type: str,
        confidence: float,
        embeddings: Mapping[str, np.ndarray],
        crop_paths: Mapping[str, str],
        frame_index: int,
        center: Tuple[float, float],
    ) -> Dict[str, Any]:
        timestamp = datetime.now().isoformat(timespec="seconds")

        with self._lock:
            known_animal_id = self.tracker.get_animal_id(tracking_id)
            if known_animal_id:
                animal_id = known_animal_id
                match = self.recognizer.compare_to_animal(animal_id, embeddings)
                similarity = match.similarity
                is_new = False
            else:
                match = self.recognizer.find_best_match(animal_type, embeddings)
                if match.animal_id and not match.is_new:
                    animal_id = match.animal_id
                    similarity = match.similarity
                    is_new = False
                else:
                    animal_id = self.id_generator.next_id(animal_type)
                    similarity = 0.0
                    is_new = True
                    self.recognizer.register(animal_id, animal_type, embeddings)
                    self.alert_service.create_alert(
                        "Unknown animal detected",
                        f"Registered new {animal_type} profile as {animal_id}.",
                        metadata={"animal_id": animal_id, "tracking_id": tracking_id},
                    )

            has_reference_embedding = bool(self.recognizer.embeddings.get(animal_id))
            if embeddings and not has_reference_embedding:
                self.recognizer.register(animal_id, animal_type, embeddings)
            elif embeddings and (is_new or similarity >= self.settings.recognition_threshold):
                self.recognizer.update(animal_id, embeddings)

            duplicate = self.tracker.assign(
                tracking_id=tracking_id,
                animal_id=animal_id,
                frame_index=frame_index,
                center=center,
            )
            if duplicate:
                self.alert_service.create_alert(
                    "Duplicate animal warning",
                    f"Animal {animal_id} is associated with multiple active tracking IDs.",
                    metadata={"animal_id": animal_id, "tracking_id": tracking_id},
                )

            profile = self._update_profile(
                animal_id=animal_id,
                animal_type=animal_type,
                timestamp=timestamp,
                similarity=similarity,
                crop_paths=crop_paths,
            )

            detection_record = {
                "detection_id": str(uuid.uuid4()),
                "tracking_id": tracking_id,
                "animal_id": animal_id,
                "animal_type": animal_type,
                "timestamp": timestamp,
                "confidence": round(float(confidence), 4),
                "similarity_score": round(float(similarity), 4),
                "full_image_path": crop_paths.get("full", ""),
                "forehead_image_path": crop_paths.get("forehead", ""),
                "eyes_image_path": crop_paths.get("eyes", ""),
                "nose_image_path": crop_paths.get("nose", ""),
            }
            self.csv_logger.log_detection(detection_record)
            self.mongodb.insert_one("detections", detection_record)
            if self.sqlite_storage is not None:
                self.sqlite_storage.save_detection(detection_record)

            embedding_document = self.recognizer.serialize_record(animal_id)
            self.mongodb.upsert_one(
                "embeddings",
                {"animal_id": animal_id},
                embedding_document,
            )
            if self.sqlite_storage is not None:
                self.sqlite_storage.save_animal_profile(profile)
            self._save_embeddings()

            return {
                "animal_id": animal_id,
                "profile": profile,
                "detection": detection_record,
                "similarity": similarity,
                "is_new": is_new,
                "duplicate": duplicate,
            }

    def register_manual_profile(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.now().isoformat(timespec="seconds")
        animal_type = (
            str(payload.get("species") or payload.get("animal_type") or "Other Animals")
            .strip()
            or "Other Animals"
        )
        animal_id = str(
            payload.get("unique_animal_id") or payload.get("animal_id") or ""
        ).strip()
        if not animal_id:
            animal_id = self.id_generator.next_id(animal_type)

        profile = {
            "animal_id": animal_id,
            "unique_animal_id": animal_id,
            "name": str(payload.get("name", "")).strip(),
            "animal_type": animal_type,
            "species": animal_type,
            "breed": str(payload.get("breed", "")).strip(),
            "gender": str(payload.get("gender", "")).strip(),
            "age": str(payload.get("age", "")).strip(),
            "description": str(payload.get("description", "")).strip(),
            "registration_date": str(payload.get("registration_date") or timestamp),
            "created_by": str(payload.get("created_by", "")).strip(),
            "first_seen_time": str(payload.get("first_seen_time") or timestamp),
            "last_seen_time": str(payload.get("last_seen_time") or timestamp),
            "total_sightings": int(payload.get("total_sightings", 0) or 0),
            "best_image_path": str(payload.get("best_image_path", "")).strip(),
            "average_similarity_score": float(payload.get("average_similarity_score", 0.0) or 0.0),
            "movement_score": float(payload.get("movement_score", 0.0) or 0.0),
            "feeding_score": float(payload.get("feeding_score", 0.0) or 0.0),
            "activity_score": float(payload.get("activity_score", 0.0) or 0.0),
            "overall_health_score": float(payload.get("overall_health_score", 0.0) or 0.0),
            "health_score": float(payload.get("health_score", 0.0) or 0.0),
            "status": str(payload.get("status", "Registered")).strip() or "Registered",
        }
        metadata = {
            "name": profile["name"],
            "breed": profile["breed"],
            "gender": profile["gender"],
            "age": profile["age"],
            "description": profile["description"],
            "registration_date": profile["registration_date"],
            "created_by": profile["created_by"],
        }
        profile["metadata"] = json.dumps(metadata, ensure_ascii=True)

        with self._lock:
            self.profiles[animal_id] = profile
            self.id_generator.observe(animal_id)
            self.csv_logger.upsert_animal(profile)
            self.mongodb.upsert_one("animals", {"animal_id": animal_id}, profile)
            if self.sqlite_storage is not None:
                self.sqlite_storage.save_animal_profile(profile)
        return profile

    def list_animals(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.profiles.values())

    def get_animal(self, animal_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.profiles.get(animal_id)

    def list_detections(self, limit: int = 200) -> List[Dict[str, Any]]:
        if self.sqlite_storage is not None:
            return self.sqlite_storage.list_detections(limit=limit)
        rows = self.csv_logger.read_rows("detections", limit=limit)
        return list(reversed(rows))

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            by_type: Dict[str, int] = {}
            for profile in self.profiles.values():
                by_type[profile["animal_type"]] = by_type.get(profile["animal_type"], 0) + 1

        total_detections = len(self.csv_logger.read_rows("detections"))
        if self.sqlite_storage is not None:
            total_detections = len(self.sqlite_storage.list_detections(limit=10000))

        return {
            "total_animals": len(self.profiles),
            "animals_by_type": by_type,
            "total_detections": total_detections,
            "total_alerts": len(self.csv_logger.read_rows("alerts")),
        }

    def _update_profile(
        self,
        animal_id: str,
        animal_type: str,
        timestamp: str,
        similarity: float,
        crop_paths: Mapping[str, str],
    ) -> Dict[str, Any]:
        profile = self.profiles.get(animal_id)
        if profile is None:
            profile = {
                "animal_id": animal_id,
                "animal_type": animal_type,
                "first_seen_time": timestamp,
                "last_seen_time": timestamp,
                "total_sightings": 0,
                "best_image_path": crop_paths.get("full", ""),
                "average_similarity_score": 0.0,
                "movement_score": 0.0,
                "feeding_score": 0.0,
                "activity_score": 0.0,
                "health_score": 0.0,
                "status": "Normal",
            }

        sightings = int(float(profile.get("total_sightings", 0))) + 1
        previous_average = float(profile.get("average_similarity_score", 0.0) or 0.0)
        average_similarity = (
            similarity if sightings == 1 else ((previous_average * (sightings - 1)) + similarity) / sightings
        )

        health = self.health_service.calculate(
            movement_score=self.tracker.movement_score(animal_id),
            total_sightings=sightings,
        )

        profile.update(
            {
                "animal_type": animal_type,
                "last_seen_time": timestamp,
                "total_sightings": sightings,
                "average_similarity_score": round(float(average_similarity), 4),
                "best_image_path": profile.get("best_image_path") or crop_paths.get("full", ""),
                **health,
            }
        )
        self.profiles[animal_id] = profile
        self.id_generator.observe(animal_id)
        self.csv_logger.upsert_animal(profile)
        self.csv_logger.log_health(
            {
                "timestamp": timestamp,
                "animal_id": animal_id,
                "movement_score": profile.get("movement_score", 0.0),
                "feeding_score": profile.get("feeding_score", 0.0),
                "activity_score": profile.get("activity_score", 0.0),
                "overall_health_score": profile.get("overall_health_score", profile.get("health_score", 0.0)),
                "health_score": profile.get("health_score", 0.0),
                "status": profile.get("status", "Normal"),
                "metadata": {"total_sightings": sightings},
            }
        )
        self.mongodb.upsert_one("animals", {"animal_id": animal_id}, profile)
        return profile

    def _load_profiles(self) -> None:
        records: List[Dict[str, Any]] = []
        records.extend(self.csv_logger.read_rows("animals"))
        records.extend(self.mongodb.find_many("animals", limit=10000))
        if self.sqlite_storage is not None:
            records.extend(self.sqlite_storage.list_animals())

        for record in records:
            animal_id = str(record.get("animal_id", "")).strip()
            if not animal_id:
                continue
            self.profiles[animal_id] = dict(record)
            self.id_generator.observe(animal_id)

    def _load_embeddings(self) -> None:
        for record in self._read_local_embedding_records():
            self.recognizer.load_record(record)
        for record in self.mongodb.find_many("embeddings", limit=10000):
            self.recognizer.load_record(record)

    def _read_local_embedding_records(self) -> List[Dict[str, Any]]:
        path = Path(self.embedding_store_path)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    def _save_embeddings(self) -> None:
        records = [
            self.recognizer.serialize_record(animal_id)
            for animal_id in sorted(self.recognizer.embeddings)
        ]
        self.embedding_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_store_path.write_text(
            json.dumps(records, ensure_ascii=True),
            encoding="utf-8",
        )
