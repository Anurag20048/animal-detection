# =========================================================
# OpenMP FIX (Windows + Anaconda)
# =========================================================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# =========================================================
# Imports
# =========================================================
import cv2
import csv
import time
import torch
import torch.nn as nn
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from torchvision import models, transforms
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image

# =========================================================
# CONFIG
# =========================================================
YOLO_MODEL = "yolov8s.pt"
VIDEO_SOURCE = 0
SIM_THRESHOLD = 0.75

BASE_DIR = r"D:\sheep_biometrics"
FACE_DIR = os.path.join(BASE_DIR, "face_crops")
CSV_PATH = os.path.join(BASE_DIR, "biometric_log.csv")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

os.makedirs(FACE_DIR, exist_ok=True)

# =========================================================
# CNN EMBEDDING MODEL
# =========================================================
cnn = models.resnet18(pretrained=True)
cnn.fc = nn.Identity()
cnn = cnn.to(DEVICE)
cnn.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def extract_embedding(img_array):
    img = Image.fromarray(img_array).convert("RGB")
    img = transform(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        emb = cnn(img)
    return emb.cpu().numpy().flatten()

# =========================================================
# BUILD BIOMETRIC DATABASE
# =========================================================
def build_database():
    db = {}
    for img in os.listdir(FACE_DIR):
        if not img.endswith(".jpg"):
            continue
        sheep_id = img.split("_")[1]
        img_path = os.path.join(FACE_DIR, img)
        image = cv2.imread(img_path)
        emb = extract_embedding(image)
        db.setdefault(sheep_id, []).append(emb)

    for sid in db:
        db[sid] = np.mean(db[sid], axis=0)

    return db

DATABASE = build_database()
print(f"✔ Loaded biometric database with {len(DATABASE)} sheep")

# =========================================================
# CSV SETUP
# =========================================================
csv_exists = os.path.isfile(CSV_PATH)
csv_file = open(CSV_PATH, "a", newline="")
csv_writer = csv.writer(csv_file)

if not csv_exists:
    csv_writer.writerow([
        "tracking_id",
        "sheep_id",
        "similarity_score",
        "timestamp"
    ])

# =========================================================
# YOLO + TRACKING
# =========================================================
yolo = YOLO(YOLO_MODEL)
cap = cv2.VideoCapture(VIDEO_SOURCE)

track_identity_map = {}   # tracking_id -> sheep_id
prev_time = 0

# =========================================================
# LIVE LOOP
# =========================================================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
    prev_time = curr_time

    results = yolo.track(
        frame,
        conf=0.4,
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False
    )

    for r in results:
        if r.boxes.id is None:
            continue

        for box, tid in zip(r.boxes, r.boxes.id):
            cls = int(box.cls[0])
            label = yolo.names[cls]

            if label != "sheep":
                continue

            track_id = int(tid)
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # If this tracking ID already has a biometric ID
            if track_id in track_identity_map:
                sheep_id = track_identity_map[track_id]
                score = 1.0
            else:
                # Face-only crop (upper 45%)
                h = y2 - y1
                face_y2 = y1 + int(0.45 * h)
                face_crop = frame[y1:face_y2, x1:x2]

                if face_crop.size == 0:
                    continue

                query_emb = extract_embedding(face_crop)

                best_id = "Unknown"
                best_score = -1

                for sid, db_emb in DATABASE.items():
                    s = cosine_similarity(
                        [query_emb], [db_emb]
                    )[0][0]
                    if s > best_score:
                        best_score = s
                        best_id = sid

                if best_score >= SIM_THRESHOLD:
                    sheep_id = best_id
                    track_identity_map[track_id] = sheep_id

                    # Save face crop
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_name = f"sheep_{sheep_id}_{track_id}_{ts}.jpg"
                    cv2.imwrite(os.path.join(FACE_DIR, img_name), face_crop)

                    # Log CSV
                    csv_writer.writerow([
                        track_id,
                        sheep_id,
                        round(best_score, 3),
                        ts
                    ])
                    csv_file.flush()
                else:
                    sheep_id = "Unknown"
                    best_score = 0.0

                score = best_score

            # Draw
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                          (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"TID:{track_id} ID:{sheep_id} ({score:.2f})",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    cv2.putText(frame, f"FPS: {fps:.2f}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Sheep Biometric Identification", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
csv_file.close()
cv2.destroyAllWindows()
