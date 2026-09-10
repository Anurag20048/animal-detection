from __future__ import annotations

import sys
from typing import Any, Iterable, Union

import cv2


def open_video_capture(source: Union[str, int, None]) -> cv2.VideoCapture:
    capture_source = source if source is not None else 0
    capture = cv2.VideoCapture(capture_source)
    if _is_capture_working(capture):
        return capture

    if sys.platform.startswith("win") and isinstance(capture_source, (int, str)) and str(capture_source).isdigit():
        for backend in _windows_camera_backends():
            try:
                capture = cv2.VideoCapture(capture_source, backend)
            except Exception:
                continue
            if _is_capture_working(capture):
                return capture

    return capture


def _is_capture_working(capture: cv2.VideoCapture) -> bool:
    if not capture or not capture.isOpened():
        return False
    ok, frame = capture.read()
    if not ok or frame is None:
        try:
            capture.release()
        except Exception:
            pass
        return False
    return True


def _windows_camera_backends() -> Iterable[int | Any]:
    backends = []
    for name in ("CAP_DSHOW", "CAP_MSMF", "CAP_VFW", "CAP_ANY"):
        backend = getattr(cv2, name, None)
        if backend is not None:
            backends.append(backend)
    return backends
