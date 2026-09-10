from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import numpy as np

BBox = Tuple[int, int, int, int]

@dataclass
class Detection:
    bbox: BBox
    confidence: float
    class_id: int
    class_name: str
    animal_type: str
    tracking_id: int

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (float(x1 + x2) / 2.0, float(y1 + y2) / 2.0)

class YOLOAnimalDetector:
    COCO_OTHER_ANIMALS = {"bird", "cat", "dog", "horse", "elephant", "bear", "zebra", "giraffe"}

    def __init__(self, model_path: str, tracker_config: str = "bytetrack.yaml") -> None:
        try:
            from ultralytics import YOLO
        except Exception as exc:
            raise RuntimeError("Ultralytics is required for detection. Install requirements.txt first.") from exc
        self.model_path = model_path
        self.tracker_config = tracker_config
        self.model = YOLO(model_path)
        self.names = self.model.names

    def track_frame(self, frame: np.ndarray, confidence_threshold: float) -> List[Detection]:
        results = self.model.track(source=frame, persist=True, conf=confidence_threshold, tracker=self.tracker_config, verbose=False)
        return self._parse_results(results, confidence_threshold)

    def predict_frame(self, frame: np.ndarray, confidence_threshold: float) -> List[Detection]:
        results = self.model.predict(source=frame, conf=confidence_threshold, verbose=False)
        return self._parse_results(results, confidence_threshold)

    def _parse_results(self, results: List[Any], confidence_threshold: float) -> List[Detection]:
        if not results:
            return []
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)
        track_ids = boxes.id.cpu().numpy().astype(int) if getattr(boxes, "id", None) is not None else np.full(len(class_ids), -1, dtype=int)
        detections: List[Detection] = []
        for index, bbox_array in enumerate(xyxy):
            confidence = float(confidences[index])
            if confidence < confidence_threshold:
                continue
            class_id = int(class_ids[index])
            class_name = self._class_name(class_id)
            animal_type = self._map_animal_type(class_name)
            if animal_type is None:
                continue
            x1, y1, x2, y2 = bbox_array.astype(int).tolist()
            detections.append(Detection(bbox=(x1, y1, x2, y2), confidence=confidence, class_id=class_id, class_name=class_name, animal_type=animal_type, tracking_id=int(track_ids[index])))
        return detections

    def _class_name(self, class_id: int) -> str:
        if isinstance(self.names, dict):
            return str(self.names.get(class_id, class_id))
        if 0 <= class_id < len(self.names):
            return str(self.names[class_id])
        return str(class_id)

    def _map_animal_type(self, class_name: str) -> Optional[str]:
        normalized = class_name.strip().lower().replace("_", " ")
        if normalized in {"cow", "cattle", "calf", "bull", "ox"}: return "Cow"
        if normalized in {"buffalo", "water buffalo", "bison"}: return "Buffalo"
        if normalized in {"sheep", "lamb", "ram", "ewe"}: return "Sheep"
        if normalized in self.COCO_OTHER_ANIMALS or "animal" in normalized: return "Other Animals"
        return None
