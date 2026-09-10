import threading
from typing import Any, Dict, List, Optional, Union

import cv2
import numpy as np

from config import Settings
from models.detector import YOLOAnimalDetector
from models.embedding_model import ResNet50EmbeddingModel
from services.alert_service import AlertService
from services.animal_service import AnimalService
from utils.camera_utils import open_video_capture
from utils.fps import FPSCounter
from utils.image_utils import draw_detection, draw_hud, enhance_frame, save_region_crops


class DetectionService:
    def __init__(
        self,
        settings: Settings,
        animal_service: AnimalService,
        alert_service: AlertService,
    ) -> None:
        self.settings = settings
        self.animal_service = animal_service
        self.alert_service = alert_service
        self.detector: Optional[YOLOAnimalDetector] = None
        self.embedding_model: Optional[ResNet50EmbeddingModel] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.source: Union[str, int, None] = None
        self.last_fps = 0.0
        self.processed_frames = 0
        self.last_error: Optional[str] = None
        self._lock = threading.RLock()

    def start(
        self,
        source: Union[str, int, None] = None,
        show_window: bool = False,
    ) -> Dict[str, Any]:
        parsed_source = self.settings.parse_source(
            source if source is not None else self.settings.default_camera_source
        )
        with self._lock:
            if self.running:
                return {
                    "started": False,
                    "message": "Detection is already running.",
                    "source": self.source,
                }

            self.source = parsed_source
            self.last_error = None
            self.stop_event.clear()
            self.thread = threading.Thread(
                target=self.run,
                kwargs={"source": parsed_source, "show_window": show_window},
                daemon=True,
            )
            self.thread.start()
            return {
                "started": True,
                "message": "Detection started.",
                "source": parsed_source,
                "status": "starting",
            }

    def stop(self) -> Dict[str, Any]:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        with self._lock:
            self.running = False
        return {"stopped": True, "message": "Detection stopped."}

    def run(
        self,
        source: Union[str, int, None] = None,
        show_window: bool = True,
    ) -> None:
        parsed_source = self.settings.parse_source(
            source if source is not None else self.settings.default_camera_source
        )
        self.source = parsed_source

        try:
            self._ensure_models()
        except Exception as exc:
            self.last_error = str(exc)
            self.alert_service.create_alert(
                "Detection loop error",
                self.last_error,
                severity="critical",
                metadata={"source": str(parsed_source)},
            )
            return

        capture = open_video_capture(parsed_source)
        if not capture.isOpened():
            self.last_error = (
                f"Unable to open camera/video source: {parsed_source}. "
                "Tried native OpenCV capture backends."
            )
            self.alert_service.log_camera(
                event="open_failed",
                source=str(parsed_source),
                status="error",
                metadata={"error": self.last_error},
            )
            self.alert_service.create_alert(
                "Camera disconnected",
                self.last_error,
                severity="critical",
                metadata={"source": str(parsed_source)},
            )
            return

        fps_counter = FPSCounter()
        window_name = "Smart Livestock Monitoring"
        with self._lock:
            self.running = True
            self.last_error = None

        self.alert_service.log_system(
            "Detection loop started.",
            metadata={"source": str(parsed_source), "show_window": show_window},
        )
        self.alert_service.log_camera(
            event="started",
            source=str(parsed_source),
            status="running",
            metadata={"show_window": show_window},
        )

        try:
            while not self.stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    self.last_error = "Camera disconnected or video stream ended."
                    self.alert_service.log_camera(
                        event="disconnected",
                        source=str(parsed_source),
                        status="error",
                        fps=self.last_fps,
                        metadata={"frame": self.processed_frames},
                    )
                    self.alert_service.create_alert(
                        "Camera disconnected",
                        self.last_error,
                        severity="critical",
                        metadata={"source": str(parsed_source)},
                    )
                    break

                self.processed_frames += 1
                frame = enhance_frame(frame)
                detections = self.detector.track_frame(
                    frame,
                    confidence_threshold=self.settings.confidence_threshold,
                )
                self.last_fps = fps_counter.update()

                for detection in detections:
                    if detection.confidence < self.settings.low_confidence_alert_threshold:
                        self.alert_service.create_alert(
                            "Low confidence detection",
                            f"{detection.animal_type} detected with confidence {detection.confidence:.2f}.",
                            metadata={
                                "tracking_id": detection.tracking_id,
                                "animal_type": detection.animal_type,
                            },
                        )

                    crops = save_region_crops(
                        frame=frame,
                        bbox=detection.bbox,
                        crop_root=self.settings.crop_dir,
                        full_image_root=self.settings.full_image_dir,
                        animal_type=detection.animal_type,
                        tracking_id=detection.tracking_id,
                    )
                    embeddings = self.embedding_model.embed_regions(crops.images)
                    result = self.animal_service.process_detection(
                        tracking_id=detection.tracking_id,
                        animal_type=detection.animal_type,
                        confidence=detection.confidence,
                        embeddings=embeddings,
                        crop_paths=crops.paths,
                        frame_index=self.processed_frames,
                        center=detection.center,
                    )

                    label = (
                        f"{result['animal_id']} {detection.animal_type} "
                        f"{detection.confidence:.2f} sim:{result['similarity']:.2f}"
                    )
                    draw_detection(frame, detection.bbox, label)

                draw_hud(frame, self.last_fps, str(parsed_source))
                if show_window:
                    cv2.imshow(window_name, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        self.stop_event.set()

        except Exception as exc:
            self.last_error = str(exc)
            self.alert_service.create_alert(
                "Detection loop error",
                self.last_error,
                severity="critical",
                metadata={"source": str(parsed_source)},
            )
        finally:
            capture.release()
            if show_window:
                try:
                    cv2.destroyWindow(window_name)
                except Exception:
                    cv2.destroyAllWindows()
            with self._lock:
                self.running = False
            self.alert_service.log_system(
                "Detection loop stopped.",
                metadata={"source": str(parsed_source), "last_error": self.last_error},
            )
            self.alert_service.log_camera(
                event="stopped",
                source=str(parsed_source),
                status="stopped",
                fps=self.last_fps,
                metadata={"last_error": self.last_error},
            )

    def stats(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "starting": self.thread is not None and self.thread.is_alive() and not self.running,
            "source": self.source,
            "last_fps": round(float(self.last_fps), 2),
            "processed_frames": self.processed_frames,
            "last_error": self.last_error,
        }

    def predict_image(
        self,
        frame: np.ndarray,
        confidence_threshold: Optional[float] = None,
    ) -> List[Any]:
        self._ensure_models()
        frame = enhance_frame(frame)
        threshold = confidence_threshold if confidence_threshold is not None else self.settings.confidence_threshold
        return self.detector.predict_frame(frame, confidence_threshold=threshold)

    def _ensure_models(self) -> None:
        if self.detector is None:
            self.detector = YOLOAnimalDetector(
                model_path=self.settings.yolo_model_path,
                tracker_config=self.settings.yolo_tracker_config,
            )
        if self.embedding_model is None:
            self.embedding_model = ResNet50EmbeddingModel(
                use_pretrained=self.settings.resnet_pretrained
            )
