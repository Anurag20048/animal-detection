"""Camera identity and location configuration.

Camera metadata is configuration, not inferred from the video stream. This keeps
location data explicit and makes the same animal ID traceable across cameras.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple, Union


@dataclass(frozen=True)
class CameraInfo:
    camera_id: str
    source: Union[str, int]
    location: str


class CameraRegistry:
    def __init__(self, cameras: List[CameraInfo]) -> None:
        self.cameras = cameras

    @classmethod
    def from_settings(cls, settings: Any) -> "CameraRegistry":
        raw = getattr(settings, "camera_configs", None)
        if raw:
            return cls(cls._parse_configs(raw))

        camera_id = getattr(settings, "default_camera_id", "CAM-001")
        location = getattr(settings, "default_camera_location", "Unknown")
        source = settings.parse_source(getattr(settings, "default_camera_source", "0"))
        return cls([CameraInfo(str(camera_id), source, str(location))])

    @staticmethod
    def _parse_configs(raw: Any) -> List[CameraInfo]:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
        if not isinstance(raw, list):
            return []

        cameras: List[CameraInfo] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            source = item.get("source")
            camera_id = str(item.get("camera_id", "")).strip()
            location = str(item.get("location", "Unknown")).strip() or "Unknown"
            if source is None or not camera_id:
                continue
            if isinstance(source, str) and source.strip().isdigit():
                source = int(source.strip())
            cameras.append(CameraInfo(camera_id, source, location))
        return cameras

    def resolve(self, source: Union[str, int, None]) -> Tuple[str, str]:
        normalized = str(source).strip() if source is not None else "0"
        for camera in self.cameras:
            if str(camera.source).strip() == normalized:
                return camera.camera_id, camera.location
        return "CAM-UNKNOWN", "Unknown"

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        return {
            camera.camera_id: {
                "source": camera.source,
                "location": camera.location,
            }
            for camera in self.cameras
        }
