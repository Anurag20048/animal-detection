from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), unique=True, index=True, nullable=False)
    username = Column(String(128), nullable=False)
    full_name = Column(String(256), nullable=True)
    hashed_password = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnimalProfile(Base):
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(String(64), unique=True, index=True, nullable=False)
    animal_type = Column(String(64), nullable=False)
    first_seen_time = Column(DateTime, nullable=False)
    last_seen_time = Column(DateTime, nullable=False)
    total_sightings = Column(Integer, nullable=False, default=0)
    best_image_path = Column(String(512), default="")
    average_similarity_score = Column(Float, default=0.0)
    movement_score = Column(Float, default=0.0)
    feeding_score = Column(Float, default=0.0)
    activity_score = Column(Float, default=0.0)
    overall_health_score = Column(Float, default=0.0)
    health_score = Column(Float, default=0.0)
    status = Column(String(64), default="Normal")
    metadata_json = Column("metadata", Text, default="{}")


class DetectionRecord(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(String(64), unique=True, index=True, nullable=False)
    tracking_id = Column(Integer, nullable=True)
    animal_id = Column(String(64), index=True, nullable=True)
    animal_type = Column(String(64), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    confidence = Column(Float, default=0.0)
    similarity_score = Column(Float, default=0.0)
    full_image_path = Column(String(512), default="")
    forehead_image_path = Column(String(512), default="")
    eyes_image_path = Column(String(512), default="")
    nose_image_path = Column(String(512), default="")
    camera_id = Column(String(128), default="")
    metadata_json = Column("metadata", Text, default="{}")


class SQLiteStorage:
    def __init__(self) -> None:
        self.database_path = Path(settings.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(self.engine)

    def session(self):
        return self.SessionLocal()

    def create_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        session = self.session()
        try:
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except SQLAlchemyError:
            session.rollback()
            return None
        finally:
            session.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        session = self.session()
        try:
            return session.query(User).filter(User.email == email.lower().strip()).first()
        finally:
            session.close()

    def list_users(self) -> List[Dict[str, Any]]:
        session = self.session()
        try:
            return [
                {
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                }
                for user in session.query(User).order_by(User.created_at.desc()).all()
            ]
        finally:
            session.close()

    def get_user_count(self) -> int:
        session = self.session()
        try:
            return session.query(User).count()
        finally:
            session.close()

    def save_animal_profile(self, profile: Dict[str, Any]) -> bool:
        session = self.session()
        try:
            animal_id = str(profile.get("animal_id", "")).strip()
            if not animal_id:
                return False
            existing = session.query(AnimalProfile).filter(AnimalProfile.animal_id == animal_id).first()
            values = {
                "animal_id": animal_id,
                "animal_type": profile.get("animal_type", ""),
                "first_seen_time": self._parse_timestamp(profile.get("first_seen_time")),
                "last_seen_time": self._parse_timestamp(profile.get("last_seen_time")),
                "total_sightings": int(profile.get("total_sightings", 0) or 0),
                "best_image_path": profile.get("best_image_path", ""),
                "average_similarity_score": float(profile.get("average_similarity_score", 0.0) or 0.0),
                "movement_score": float(profile.get("movement_score", 0.0) or 0.0),
                "feeding_score": float(profile.get("feeding_score", 0.0) or 0.0),
                "activity_score": float(profile.get("activity_score", 0.0) or 0.0),
                "overall_health_score": float(profile.get("overall_health_score", profile.get("health_score", 0.0)) or 0.0),
                "health_score": float(profile.get("health_score", 0.0) or 0.0),
                "status": profile.get("status", "Normal"),
                "metadata_json": str(profile.get("metadata", "{}")),
            }
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
                session.commit()
            else:
                doc = AnimalProfile(**values)
                session.add(doc)
                session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def save_detection(self, record: Dict[str, Any]) -> bool:
        session = self.session()
        try:
            detection_id = str(record.get("detection_id", "")).strip() or str(record.get("timestamp", ""))
            if not detection_id:
                return False
            existing = session.query(DetectionRecord).filter(DetectionRecord.detection_id == detection_id).first()
            values = {
                "detection_id": detection_id,
                "tracking_id": int(record.get("tracking_id", -1) or -1),
                "animal_id": record.get("animal_id", ""),
                "animal_type": record.get("animal_type", ""),
                "timestamp": self._parse_timestamp(record.get("timestamp")),
                "confidence": float(record.get("confidence", 0.0) or 0.0),
                "similarity_score": float(record.get("similarity_score", 0.0) or 0.0),
                "full_image_path": record.get("full_image_path", ""),
                "forehead_image_path": record.get("forehead_image_path", ""),
                "eyes_image_path": record.get("eyes_image_path", ""),
                "nose_image_path": record.get("nose_image_path", ""),
                "camera_id": record.get("camera_id", ""),
                "metadata_json": str(record.get("metadata", "{}")),
            }
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
                session.commit()
            else:
                doc = DetectionRecord(**values)
                session.add(doc)
                session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()

    def list_detections(
        self,
        animal_type: Optional[str] = None,
        animal_id: Optional[str] = None,
        limit: int = 200,
        confidence_min: float = 0.0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        session = self.session()
        try:
            query = session.query(DetectionRecord)
            if animal_type:
                query = query.filter(DetectionRecord.animal_type == animal_type)
            if animal_id:
                query = query.filter(DetectionRecord.animal_id == animal_id)
            if confidence_min > 0.0:
                query = query.filter(DetectionRecord.confidence >= confidence_min)
            start_dt = self._parse_filter_date(start_date)
            end_dt = self._parse_filter_date(end_date, end_of_day=True)
            if start_dt:
                query = query.filter(DetectionRecord.timestamp >= start_dt)
            if end_dt:
                query = query.filter(DetectionRecord.timestamp <= end_dt)
            rows = (
                query.order_by(DetectionRecord.timestamp.desc())
                .offset(max(0, int(offset or 0)))
                .limit(limit)
                .all()
            )
            return [self._record_to_dict(row) for row in rows]
        finally:
            session.close()

    def list_animals(self) -> List[Dict[str, Any]]:
        session = self.session()
        try:
            rows = session.query(AnimalProfile).order_by(AnimalProfile.last_seen_time.desc()).all()
            return [self._profile_to_dict(row) for row in rows]
        finally:
            session.close()

    def analytics_summary(self) -> Dict[str, Any]:
        detections = self.list_detections(limit=1000)
        animal_counts: Dict[str, int] = {}
        by_animal: Dict[str, int] = {}
        daily_counts: Dict[str, int] = {}
        monthly_counts: Dict[str, int] = {}
        for record in detections:
            animal_type = record.get("animal_type", "Unknown")
            animal_counts[animal_type] = animal_counts.get(animal_type, 0) + 1
            key = f"{record.get('animal_id','Unknown')}"
            by_animal[key] = by_animal.get(key, 0) + 1
            ts = record.get("timestamp")
            try:
                date_key = datetime.fromisoformat(ts).date().isoformat() if isinstance(ts, str) else ts.date().isoformat()
            except Exception:
                date_key = "unknown"
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
            if date_key != "unknown":
                monthly_key = date_key[:7]
                monthly_counts[monthly_key] = monthly_counts.get(monthly_key, 0) + 1
        sorted_top = sorted(by_animal.items(), key=lambda x: -x[1])[:8]
        return {
            "total_detections": len(detections),
            "by_type": animal_counts,
            "daily_counts": daily_counts,
            "monthly_counts": monthly_counts,
            "top_animals": [{"animal_id": animal_id, "count": count} for animal_id, count in sorted_top],
        }

    def _record_to_dict(self, row: DetectionRecord) -> Dict[str, Any]:
        return {
            "detection_id": row.detection_id,
            "tracking_id": row.tracking_id,
            "animal_id": row.animal_id,
            "animal_type": row.animal_type,
            "timestamp": row.timestamp.isoformat() if row.timestamp else "",
            "confidence": row.confidence,
            "similarity_score": row.similarity_score,
            "full_image_path": row.full_image_path,
            "forehead_image_path": row.forehead_image_path,
            "eyes_image_path": row.eyes_image_path,
            "nose_image_path": row.nose_image_path,
            "camera_id": row.camera_id,
            "metadata": row.metadata_json,
        }

    def _profile_to_dict(self, row: AnimalProfile) -> Dict[str, Any]:
        metadata = self._parse_metadata(row.metadata_json)
        return {
            "animal_id": row.animal_id,
            "unique_animal_id": row.animal_id,
            "name": metadata.get("name", ""),
            "animal_type": row.animal_type,
            "species": row.animal_type,
            "breed": metadata.get("breed", ""),
            "gender": metadata.get("gender", ""),
            "age": metadata.get("age", ""),
            "description": metadata.get("description", ""),
            "registration_date": metadata.get("registration_date", row.first_seen_time.isoformat() if row.first_seen_time else ""),
            "created_by": metadata.get("created_by", ""),
            "first_seen_time": row.first_seen_time.isoformat() if row.first_seen_time else "",
            "last_seen_time": row.last_seen_time.isoformat() if row.last_seen_time else "",
            "total_sightings": row.total_sightings,
            "best_image_path": row.best_image_path,
            "average_similarity_score": row.average_similarity_score,
            "movement_score": row.movement_score,
            "feeding_score": row.feeding_score,
            "activity_score": row.activity_score,
            "overall_health_score": row.overall_health_score,
            "health_score": row.health_score,
            "status": row.status,
            "metadata": row.metadata_json,
        }

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.utcnow()
        return datetime.utcnow()

    def _parse_filter_date(
        self,
        value: Optional[str],
        end_of_day: bool = False,
    ) -> Optional[datetime]:
        if not value:
            return None
        try:
            text = str(value).strip()
            if len(text) == 10:
                suffix = "T23:59:59" if end_of_day else "T00:00:00"
                text = f"{text}{suffix}"
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def _parse_metadata(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            parsed = json.loads(str(value).replace("'", '"'))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
