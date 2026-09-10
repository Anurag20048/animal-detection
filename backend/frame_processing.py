from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from models.detector import YOLOAnimalDetector
from utils.image_utils import draw_detection, enhance_frame, save_region_crops


@dataclass
class DetectionImagePaths:
    full_image_path: str
    crop_path: str
    crops: Dict[str, str]


class FrameProcessor:
    def __init__(self, settings, animal_service, alert_service, detector: Optional[YOLOAnimalDetector] = None) -> None:
        self.settings = settings
        self.animal_service = animal_service
        self.alert_service = alert_service
        self.detector: Optional[YOLOAnimalDetector] = detector
        self._lock = threading.RLock()

        # Embedding model + biometric processing handled by AnimalService during
        # normal /start-detection loop. For video-feed we only need bounding boxes.

    def _ensure_detector(self) -> YOLOAnimalDetector:
        if self.detector is None:
            self.detector = YOLOAnimalDetector(
                model_path=self.settings.yolo_model_path,
                tracker_config=self.settings.yolo_tracker_config,
            )
        return self.detector

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, str]]:
        """Run YOLO and draw boxes. Also save crops + full frame if detections exist."""
        det = self._ensure_detector()
        annotated = frame.copy()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        date_label = datetime.now().strftime("%Y-%m-%d")

        latest_paths: Dict[str, str] = {}
        processed = enhance_frame(frame)
        detections = det.track_frame(
            processed,
            confidence_threshold=self.settings.confidence_threshold,
        )

        # Draw each detection; save full boxed frame only if at least one animal detected
        any_detected = False
        for detection in detections:
            if detection.confidence < self.settings.low_confidence_alert_threshold:
                continue
            any_detected = True

            label = f"{detection.animal_type} {int(detection.confidence * 100)}%"
            draw_detection(annotated, detection.bbox, label)

            # Save crops using existing utility; also include full image saving
            crops = save_region_crops(
                frame=frame,
                bbox=detection.bbox,
                crop_root=self.settings.crop_dir,
                full_image_root=self.settings.full_image_dir,
                animal_type=detection.animal_type,
                tracking_id=detection.tracking_id,
            )
            # we only need a representative crop path for CSV requirement
            # full path is stored in crops.paths['full']? utility uses full_dir with _full.jpg
            latest_paths["full"] = crops.paths.get("full", "")
            latest_paths["forehead"] = crops.paths.get("forehead", "")
            latest_paths["eyes"] = crops.paths.get("eyes", "")
            latest_paths["nose"] = crops.paths.get("nose", "")

        # If any detected, overwrite a single full frame-with-boxes file as well
        if any_detected:
            out_dir = self.settings.full_image_dir / date_label
            out_dir.mkdir(parents=True, exist_ok=True)
            full_box_path = out_dir / f"boxed_{timestamp}.jpg"
            cv2.imwrite(str(full_box_path), annotated)
            latest_paths["full_box"] = str(full_box_path)

        return annotated, latest_paths

