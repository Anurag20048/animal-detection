from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import cv2
import numpy as np


BBox = Tuple[int, int, int, int]


@dataclass
class CropResult:
    images: Dict[str, np.ndarray]
    paths: Dict[str, str]


def clip_bbox(bbox: BBox, width: int, height: int) -> BBox:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(int(x1), width - 1))
    y1 = max(0, min(int(y1), height - 1))
    x2 = max(0, min(int(x2), width))
    y2 = max(0, min(int(y2), height))
    if x2 <= x1:
        x2 = min(width, x1 + 1)
    if y2 <= y1:
        y2 = min(height, y1 + 1)
    return x1, y1, x2, y2


def crop_image(frame: np.ndarray, bbox: BBox) -> np.ndarray:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = clip_bbox(bbox, width, height)
    return frame[y1:y2, x1:x2].copy()


def _relative_crop(image: np.ndarray, box: Tuple[float, float, float, float]) -> np.ndarray:
    height, width = image.shape[:2]
    x1 = int(width * box[0])
    y1 = int(height * box[1])
    x2 = int(width * box[2])
    y2 = int(height * box[3])
    return crop_image(image, (x1, y1, x2, y2))


def extract_region_crops(frame: np.ndarray, bbox: BBox) -> Dict[str, np.ndarray]:
    full = crop_image(frame, bbox)
    if full.size == 0:
        return {}

    return {
        "full": full,
        "forehead": _relative_crop(full, (0.25, 0.00, 0.75, 0.30)),
        "eyes": _relative_crop(full, (0.15, 0.22, 0.85, 0.52)),
        "nose": _relative_crop(full, (0.25, 0.58, 0.75, 1.00)),
    }


def save_region_crops(
    frame: np.ndarray,
    bbox: BBox,
    crop_root: Path,
    full_image_root: Path,
    animal_type: str,
    tracking_id: int | None,
) -> CropResult:
    images = extract_region_crops(frame, bbox)
    safe_type = animal_type.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    track_label = "untracked" if tracking_id is None or tracking_id < 0 else str(tracking_id)
    date_label = datetime.now().strftime("%Y-%m-%d")
    crop_dir = crop_root / date_label / safe_type / track_label
    full_dir = full_image_root / date_label / safe_type / track_label
    crop_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, str] = {}
    for region, image in images.items():
        path = (
            full_dir / f"{timestamp}_full.jpg"
            if region == "full"
            else crop_dir / f"{timestamp}_{region}.jpg"
        )
        if image.size > 0:
            cv2.imwrite(str(path), image)
            paths[region] = str(path)
        else:
            paths[region] = ""
    return CropResult(images=images, paths=paths)


def draw_detection(
    frame: np.ndarray,
    bbox: BBox,
    label: str,
    color: Tuple[int, int, int] = (40, 190, 40),
) -> None:
    x1, y1, x2, y2 = clip_bbox(bbox, frame.shape[1], frame.shape[0])
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    text_y = max(20, y1 - 8)
    cv2.putText(
        frame,
        label,
        (x1, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def draw_hud(frame: np.ndarray, fps: float, running_source: str) -> None:
    label = f"FPS: {fps:.1f} | Source: {running_source}"
    cv2.putText(
        frame,
        label,
        (12, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.70,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    try:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge((l_enhanced, a, b))
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        enhanced = cv2.detailEnhance(enhanced, sigma_s=10, sigma_r=0.15)
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        return cv2.addWeighted(enhanced, 1.2, blurred, -0.2, 0)
    except Exception:
        return frame
