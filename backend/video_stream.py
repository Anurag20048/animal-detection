from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2

from utils.camera_utils import open_video_capture


@dataclass
class LatestFrame:
    mjpg: Optional[bytes] = None
    jpeg: Optional[bytes] = None
    timestamp: float = 0.0


class VideoStreamer:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._camera_source: Optional[object] = None
        self._latest = LatestFrame()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self, camera_source: object, frame_fn) -> None:
        """Start single capture/detection loop if not already running."""
        with self._lock:
            if self._running:
                return
            self._camera_source = camera_source
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop,
                kwargs={"frame_fn": frame_fn},
                daemon=True,
            )
            self._running = True
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._stop.set()
            t = self._thread
        if t and t.is_alive():
            t.join(timeout=5)
        with self._lock:
            self._running = False

    def _loop(self, frame_fn) -> None:
        # Use a local helper to allow VideoCapture open retry
        cap = None
        try:
            source = self._camera_source if self._camera_source is not None else 0
            # open capture
            cap = open_video_capture(source)
            retry = 0
            while not cap.isOpened() and retry < 10 and not self._stop.is_set():
                retry += 1
                time.sleep(0.2)
                if hasattr(cap, "open"):
                    cap.open(source)

            if cap is None or not cap.isOpened():
                return

            # Backoff parameters for when cap.read() keeps failing (common with disconnected/blocked camera)
            consecutive_failures = 0
            max_consecutive_failures = 50
            backoff_seconds = 0.1
            backoff_max_seconds = 2.0

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    consecutive_failures += 1

                    # If camera is persistently failing, pause and attempt a reopen.
                    if consecutive_failures >= max_consecutive_failures:
                        try:
                            cap.release()
                        except Exception:
                            pass

                        # Exponential backoff before reopening
                        time.sleep(backoff_seconds)
                        backoff_seconds = min(backoff_max_seconds, backoff_seconds * 2)

                        cap = cv2.VideoCapture(source)
                        open_retry = 0
                        while not cap.isOpened() and open_retry < 10 and not self._stop.is_set():
                            open_retry += 1
                            time.sleep(0.2)
                            cap.open(source)

                        consecutive_failures = 0
                        continue

                    # Soft backoff for transient failures
                    time.sleep(0.01)
                    continue

                # Successful frame read: reset failure counters/backoff
                consecutive_failures = 0
                backoff_seconds = 0.1

                annotated, latest_paths = frame_fn(frame)

                # Encode as JPEG for latest endpoint; and MJPEG part for feed
                ok2, jpg = cv2.imencode(".jpg", annotated)
                if not ok2:
                    continue
                ts = time.time()
                with self._lock:
                    self._latest.jpeg = jpg.tobytes()
                    self._latest.timestamp = ts
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            with self._lock:
                self._running = False

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest.jpeg

    def get_latest_timestamp(self) -> float:
        with self._lock:
            return self._latest.timestamp

