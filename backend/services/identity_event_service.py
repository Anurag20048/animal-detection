"""Identity event persistence contract for camera-based re-identification.

This module keeps camera metadata explicit and separates identity assignment from
where/when an observation happened. Storage adapters can persist the returned
record to SQLite, MongoDB, CSV, or an API without changing the identity logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional


class IdentityEventService:
    """Build normalized detection events for persistent animal history."""

    def create_event(
        self,
        *,
        animal_id: str,
        animal_type: str,
        tracking_id: int,
        confidence: float,
        similarity: float,
        camera_id: str,
        camera_location: str,
        timestamp: Optional[str] = None,
        crop_paths: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        if not animal_id.strip():
            raise ValueError("animal_id is required")
        if not camera_id.strip():
            raise ValueError("camera_id is required")
        if not camera_location.strip():
            raise ValueError("camera_location is required")

        event_time = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
        paths = dict(crop_paths or {})
        return {
            "detection_id": str(uuid.uuid4()),
            "animal_id": animal_id,
            "animal_type": animal_type,
            "tracking_id": int(tracking_id),
            "timestamp": event_time,
            "camera_id": camera_id,
            "camera_location": camera_location,
            "confidence": round(float(confidence), 4),
            "similarity_score": round(float(similarity), 4),
            "full_image_path": paths.get("full", ""),
            "forehead_image_path": paths.get("forehead", ""),
            "eyes_image_path": paths.get("eyes", ""),
            "nose_image_path": paths.get("nose", ""),
        }
