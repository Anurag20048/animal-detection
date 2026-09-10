import base64
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from config import settings
from frame_processing import FrameProcessor
from runtime import create_access_token_for_user, get_current_user, get_runtime
from utils.image_utils import draw_detection
from utils.security import hash_password, verify_password
from fpdf import FPDF


def json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


def parse_json_body(request) -> Optional[Dict[str, Any]]:
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None


def require_auth(request, admin_only: bool = False) -> Dict[str, Any]:
    try:
        current_user = get_current_user(request)
    except ValueError as exc:
        raise
    if admin_only and not current_user.get("is_admin"):
        raise PermissionError("Admin access required.")
    return current_user


def health_view(request):
    runtime = get_runtime()
    return JsonResponse(
        {
            "status": "ok",
            "mongodb": runtime.mongodb.status(),
            "csv": runtime.csv_logger.status(),
            "detection": runtime.detection_stats(),
            "database": {
                "path": str(settings.database_path),
                "url": settings.database_url,
            },
        }
    )


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = parse_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload.")

    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        return json_error("Email and password are required.")

    runtime = get_runtime()
    user = runtime.sqlite_storage.get_user_by_email(email)
    if user is None or not verify_password(password, user.hashed_password):
        return json_error("Invalid email or password.", status=401)

    access_token = create_access_token_for_user(user.email)
    return JsonResponse({"access_token": access_token, "token_type": "bearer"})


@csrf_exempt
def register_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        require_auth(request, admin_only=True)
    except PermissionError as exc:
        return json_error(str(exc), status=403)
    except ValueError as exc:
        return json_error(str(exc), status=401)

    payload = parse_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload.")

    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        return json_error("Email and password are required.")

    runtime = get_runtime()
    if runtime.sqlite_storage.get_user_by_email(email):
        return json_error("User already exists.", status=400)

    created = runtime.sqlite_storage.create_user(
        {
            "email": email.lower().strip(),
            "username": payload.get("username") or email.split("@")[0],
            "full_name": payload.get("full_name") or payload.get("username") or email,
            "hashed_password": hash_password(password),
            "is_admin": bool(payload.get("is_admin", False)),
            "created_at": datetime.utcnow(),
        }
    )
    if created is None:
        return json_error("Unable to create user.", status=500)
    return JsonResponse({"message": "User registered successfully."})


def auth_me_view(request):
    try:
        current_user = require_auth(request)
    except ValueError as exc:
        return json_error(str(exc), status=401)
    return JsonResponse(current_user)


def users_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    try:
        require_auth(request, admin_only=True)
    except PermissionError as exc:
        return json_error(str(exc), status=403)
    except ValueError as exc:
        return json_error(str(exc), status=401)
    runtime = get_runtime()
    return JsonResponse({"items": runtime.sqlite_storage.list_users()})


def animals_view(request):
    if request.method == "POST":
        try:
            current_user = require_auth(request)
        except ValueError as exc:
            return json_error(str(exc), status=401)
        payload = parse_json_body(request)
        if payload is None:
            return json_error("Invalid JSON payload.")
        payload.setdefault("created_by", current_user.get("email", ""))
        profile = get_runtime().animal_service.register_manual_profile(payload)
        return JsonResponse(profile, status=201)

    if request.method != "GET":
        return HttpResponse(status=405)
    runtime = get_runtime()
    return JsonResponse({"items": runtime.animal_service.list_animals()})


def animal_detail_view(request, animal_id: str):
    if request.method != "GET":
        return HttpResponse(status=405)
    runtime = get_runtime()
    profile = runtime.animal_service.get_animal(animal_id)
    if profile is None:
        return JsonResponse({"detail": "Animal not found."}, status=404)
    return JsonResponse(profile)


def detections_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    limit = int(request.GET.get("limit", 200))
    runtime = get_runtime()
    return JsonResponse({"items": runtime.animal_service.list_detections(limit=limit)})


def alerts_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    limit = int(request.GET.get("limit", 200))
    runtime = get_runtime()
    return JsonResponse({"items": runtime.alert_service.list_alerts(limit=limit)})


def history_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    animal_type = request.GET.get("animal_type")
    species = request.GET.get("species")
    animal_id = request.GET.get("animal_id")
    min_confidence = float(request.GET.get("min_confidence", 0.0))
    limit = int(request.GET.get("limit", 200))
    offset = int(request.GET.get("offset", 0))
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    resolved_type = animal_type or species
    runtime = get_runtime()

    if runtime.sqlite_storage is not None:
        items = runtime.sqlite_storage.list_detections(
            animal_type=resolved_type,
            animal_id=animal_id,
            confidence_min=min_confidence,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
        )
    else:
        items = runtime.animal_service.list_detections(limit=limit)
        if resolved_type:
            items = [item for item in items if item.get("animal_type") == resolved_type]
        if animal_id:
            items = [item for item in items if item.get("animal_id") == animal_id]
        if min_confidence > 0.0:
            items = [
                item for item in items
                if float(item.get("confidence", 0.0) or 0.0) >= min_confidence
            ]
    return JsonResponse({"items": items})


def get_analytics_summary(runtime):
    if runtime.sqlite_storage is not None:
        return runtime.sqlite_storage.analytics_summary()

    items = runtime.animal_service.list_detections(limit=1000)
    by_type: Dict[str, int] = {}
    daily_counts: Dict[str, int] = {}
    monthly_counts: Dict[str, int] = {}
    top_animals: Dict[str, int] = {}

    for row in items:
        animal_type = row.get("animal_type", "Unknown")
        by_type[animal_type] = by_type.get(animal_type, 0) + 1
        animal_id = row.get("animal_id", "Unknown")
        top_animals[animal_id] = top_animals.get(animal_id, 0) + 1
        ts = row.get("timestamp")
        date_key = str(ts)[:10] if ts else "unknown"
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        if date_key != "unknown":
            monthly_counts[date_key[:7]] = monthly_counts.get(date_key[:7], 0) + 1

    return {
        "total_detections": len(items),
        "by_type": by_type,
        "daily_counts": daily_counts,
        "monthly_counts": monthly_counts,
        "top_animals": [
            {"animal_id": animal_id, "count": count}
            for animal_id, count in sorted(top_animals.items(), key=lambda x: -x[1])[:8]
        ],
    }


def analytics_summary_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    runtime = get_runtime()
    return JsonResponse(get_analytics_summary(runtime))


@csrf_exempt
def detect_image_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    file = request.FILES.get("file")
    if file is None:
        return json_error("Image file is required.")

    confidence_threshold = float(request.GET.get("confidence_threshold", settings.confidence_threshold))
    filename = file.name or "image"
    ext = Path(filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp"}:
        return json_error("Only image uploads are supported.", status=400)

    contents = file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return json_error("Unable to decode image file.", status=400)

    detections = get_runtime().detection_service.predict_image(
        frame, confidence_threshold=confidence_threshold
    )
    annotated = frame.copy()
    items = []
    for detection in detections:
        label = f"{detection.animal_type} {int(detection.confidence * 100)}%"
        draw_detection(annotated, detection.bbox, label)
        items.append(
            {
                "animal_type": detection.animal_type,
                "confidence": detection.confidence,
                "bbox": detection.bbox,
                "tracking_id": detection.tracking_id,
            }
        )

    _, encoded = cv2.imencode(".jpg", annotated)
    annotation_b64 = base64.b64encode(encoded.tobytes()).decode("utf-8")
    return JsonResponse(
        {
            "items": items,
            "annotated_image": f"data:image/jpeg;base64,{annotation_b64}",
        }
    )


@csrf_exempt
def upload_video_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    file = request.FILES.get("file")
    if file is None:
        return json_error("Video file is required.")

    filename = file.name or f"upload_{uuid.uuid4().hex}.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return json_error("Only video uploads are supported.", status=400)

    runtime = get_runtime()
    target = runtime.settings.upload_dir / f"{uuid.uuid4().hex}{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as buffer:
        buffer.write(file.read())

    return JsonResponse(
        {
            "success": True,
            "message": "Video uploaded successfully.",
            "path": str(target),
        }
    )


@csrf_exempt
def start_detection_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = parse_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload.")

    runtime = get_runtime()
    if payload.get("confidence_threshold") is not None:
        runtime.settings.confidence_threshold = float(payload["confidence_threshold"])

    camera_source = runtime.settings.parse_source(
        payload.get("source", runtime.settings.default_camera_source)
    )
    res = runtime.detection_service.start(
        source=camera_source,
        show_window=bool(payload.get("show_window", False)),
    )
    if not runtime.video_streamer.is_running():
        # Ensure the shared detector is loaded once, then use it for the video preview.
        runtime.detection_service._ensure_models()
        processor = FrameProcessor(
            settings=runtime.settings,
            animal_service=runtime.animal_service,
            alert_service=runtime.alert_service,
            detector=runtime.detection_service.detector,
        )
        runtime.video_streamer.start(camera_source=camera_source, frame_fn=processor.process_frame)

    return JsonResponse(res)


@csrf_exempt
def stop_detection_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    runtime = get_runtime()
    try:
        runtime.video_streamer.stop()
    except Exception:
        pass
    return JsonResponse(runtime.detection_service.stop())


def stats_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    runtime = get_runtime()
    return JsonResponse(
        {
            **runtime.animal_service.stats(),
            "detection": runtime.detection_stats(),
            "mongodb": runtime.mongodb.status(),
            "analytics": get_analytics_summary(runtime),
        }
    )


def cameras_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    runtime = get_runtime()
    detection = runtime.detection_stats()
    return JsonResponse(
        {
            "configured_sources": runtime.settings.camera_sources,
            "default_source": runtime.settings.default_camera_source,
            "active_source": detection.get("source"),
            "running": detection.get("running", False),
        }
    )


@csrf_exempt
def update_settings_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = parse_json_body(request)
    if payload is None:
        return json_error("Invalid JSON payload.")
    runtime = get_runtime()
    applied = runtime.settings.update(payload)
    return JsonResponse(
        {
            "updated": applied,
            "current": {
                "confidence_threshold": runtime.settings.confidence_threshold,
                "low_confidence_alert_threshold": runtime.settings.low_confidence_alert_threshold,
                "recognition_threshold": runtime.settings.recognition_threshold,
                "default_camera_source": runtime.settings.default_camera_source,
                "yolo_model_path": runtime.settings.yolo_model_path,
                "enable_mongodb": runtime.settings.enable_mongodb,
            },
        }
    )


def report_detections_csv_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)
    runtime = get_runtime()
    csv_path = runtime.csv_logger.path_for("detections")
    file_handle = open(csv_path, "rb")
    return FileResponse(
        file_handle,
        content_type="text/csv",
        filename="detections.csv",
    )


def create_detection_report_pdf(rows: list[Dict[str, Any]]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Detection Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(4)

    for row in rows[:100]:
        timestamp = row.get("timestamp", "")
        animal_id = row.get("animal_id", "-")
        animal_type = row.get("animal_type", "-")
        confidence = float(row.get("confidence", 0.0) or 0.0)
        pdf.multi_cell(
            0,
            6,
            f"{timestamp} | {animal_id} | {animal_type} | Confidence: {confidence:.2f}",
        )
        pdf.ln(1)

    return pdf.output(dest="S").encode("latin-1")


def report_detections_pdf_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    runtime = get_runtime()
    rows = runtime.sqlite_storage.list_detections(limit=200) if runtime.sqlite_storage else runtime.animal_service.list_detections(limit=200)
    pdf_content = create_detection_report_pdf(rows)
    response = HttpResponse(content=pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=detections_report.pdf"
    return response


def video_feed_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    runtime = get_runtime()

    def iter_frames():
        last_ts = 0.0
        while True:
            if not runtime.video_streamer.is_running():
                time.sleep(0.1)
                continue
            jpg = runtime.video_streamer.get_latest_jpeg()
            ts = runtime.video_streamer.get_latest_timestamp()
            if jpg is None or ts == last_ts:
                time.sleep(0.02)
                continue
            last_ts = ts
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            )

    return StreamingHttpResponse(
        iter_frames(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )


def latest_detection_image_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    jpg = get_runtime().video_streamer.get_latest_jpeg()
    if jpg is None:
        return HttpResponse(status=204)
    return HttpResponse(content=jpg, content_type="image/jpeg")
