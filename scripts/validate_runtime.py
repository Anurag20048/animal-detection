"""Validate the local runtime environment without requiring a camera.

Usage from repository root:
    python scripts/validate_runtime.py

The script always validates Python dependencies first. If YOLO_MODEL_PATH (or
backend/yolov8n.pt) exists, it also loads the detector and runs one inference
on a synthetic image. Missing model weights are reported as NOT RUN rather
than being treated as a successful model validation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _add_import_paths() -> None:
    for path in (ROOT, BACKEND):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def main() -> int:
    _add_import_paths()

    required = ("fastapi", "cv2", "numpy", "torch", "torchvision", "ultralytics")
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    print("Runtime dependency check")
    if missing:
        print("STATUS: FAIL")
        print("Missing packages:", ", ".join(missing))
        return 1
    print("STATUS: PASS - core ML/API dependencies are importable")

    model_path = os.getenv("YOLO_MODEL_PATH", "").strip()
    if not model_path:
        candidate = BACKEND / "yolov8n.pt"
        if candidate.exists():
            model_path = str(candidate)

    if not model_path:
        print("Model inference: NOT RUN")
        print("Reason: no YOLO_MODEL_PATH or backend/yolov8n.pt was found.")
        return 0

    model = Path(model_path)
    if not model.is_absolute():
        model = ROOT / model
    if not model.exists():
        print("Model inference: NOT RUN")
        print(f"Reason: configured model does not exist: {model}")
        return 0

    try:
        import numpy as np
        from backend.models.detector import YOLOAnimalDetector

        detector = YOLOAnimalDetector(model_path=str(model))
        frame = np.zeros((320, 320, 3), dtype=np.uint8)
        detections = detector.detect(frame)
        print("Model inference: PASS")
        print(f"Model: {model}")
        print(f"Detections returned on synthetic blank frame: {len(detections)}")
        return 0
    except Exception as exc:  # pragma: no cover - environment-specific validation
        print("Model inference: FAIL")
        print(f"Reason: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
