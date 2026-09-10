# Smart Livestock Monitoring Backend

Backend AI pipeline for real-time livestock detection, ByteTrack tracking, ResNet-50 biometric embeddings, weighted cosine recognition, CSV logging, optional MongoDB storage, health placeholders, alerts, and FastAPI endpoints.

## Animal Classes

- Cow: `C00001`, `C00002`, ...
- Buffalo: `B00001`, `B00002`, ...
- Sheep: `S00001`, `S00002`, ...
- Other Animals: `O00001`, `O00002`, ...

YOLO COCO models can detect cow and sheep directly. Buffalo support is included for custom YOLO models that expose a `buffalo`, `water buffalo`, or `bison` class. Other COCO animal classes are mapped to `Other Animals`.

## Setup

Run these commands from PowerShell:

```powershell
cd "D:\animal detection\backend"
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

MongoDB is optional. If MongoDB is not installed, not running, or `pymongo` cannot connect, the system logs a `MongoDB connection failed` alert and continues with CSV logs and saved images.

## Run Detection From Webcam

```powershell
cd "D:\animal detection\backend"
.\.venv\Scripts\activate
python app.py
```

Press `q` in the OpenCV video window to stop.

## Run FastAPI

```powershell
cd "D:\animal detection\backend"
.\.venv\Scripts\activate
uvicorn app:app --reload
```

API docs are available at:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

- `GET /health`
- `GET /animals`
- `GET /animals/{animal_id}`
- `GET /detections`
- `GET /alerts`
- `POST /start-detection`
- `POST /stop-detection`
- `GET /stats`
- `GET /cameras`
- `POST /settings`

Example start request:

```json
{
  "source": 0,
  "confidence_threshold": 0.35,
  "show_window": false
}
```

`source` can be a webcam index, a video file path, or an IP camera URL.

## Environment Settings

```powershell
$env:YOLO_MODEL_PATH="yolov8n.pt"
$env:CAMERA_SOURCE="0"
$env:CONFIDENCE_THRESHOLD="0.35"
$env:RECOGNITION_THRESHOLD="0.78"
$env:ENABLE_MONGODB="true"
$env:MONGODB_URI="mongodb://localhost:27017"
$env:MONGODB_DATABASE="livestock_monitoring"
```

## Data Outputs

- CSV files: `D:\animal detection\animal_data\csv\`
- Region crops: `D:\animal detection\animal_data\crops\YYYY-MM-DD\<animal_type>\<tracking_id>\`
- Full animal images: `D:\animal detection\animal_data\full_images\YYYY-MM-DD\<animal_type>\<tracking_id>\`
- Local embedding fallback: `D:\animal detection\animal_data\embeddings\embeddings.json`

Required CSV files created on startup:

- `animals.csv`
- `detections.csv`
- `alerts.csv`
- `system_logs.csv`
- `health_records.csv`
- `camera_logs.csv`

Detection CSV columns:

```text
tracking_id, animal_id, animal_type, timestamp, confidence, similarity_score, full_image_path, forehead_image_path, eyes_image_path, nose_image_path
```

## MongoDB Collections

- `animals`
- `detections`
- `embeddings`
- `alerts`
- `system_logs`

## Notes

- Region crops are approximate first-version crops based on the detected animal bounding box:
  - full crop: full bounding box
  - forehead: upper center
  - eyes: upper-middle band
  - nose/muzzle: lower center
- Weighted similarity:
  - full crop: 40%
  - nose/muzzle: 30%
  - eyes: 20%
  - forehead: 10%
- Health scores are placeholders based on movement and sightings only. They are not medical diagnosis.
- On first run, Ultralytics may download `yolov8n.pt`, and torchvision may download ResNet-50 weights if they are not already cached.
