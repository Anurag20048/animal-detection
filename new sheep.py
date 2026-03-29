
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


import cv2
import csv
import time
import torch
import torch.nn as nn
import numpy as np
from datetime import datetime
from ultralytics import YOLO
from torchvision import transforms
from torchvision.models import resnet18, ResNet18_Weights
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image


YOLO_MODEL = "yolov8s.pt"
VIDEO_SOURCE = 0
CONF_THRES = 0.4
SIM_THRESHOLD = 0.75

BASE_DIR = r"D:\animal_biometrics"
FACE_DIR = os.path.join(BASE_DIR, "animal_crops")
CSV_PATH = os.path.join(BASE_DIR, "biometric_log.csv")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

os.makedirs(FACE_DIR, exist_ok=True)


cnn = resnet18(weights=ResNet18_Weights.DEFAULT)
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


def build_database():
    db = {}
    for img in os.listdir(FACE_DIR):
        if not img.endswith(".jpg"):
            continue

        parts = img.split("_")
        if len(parts) < 2:
            continue

        animal = parts[0]
        animal_id = "_".join(parts[1:-1])  # Handle IDs with underscores if needed
        key = f"{animal}_{animal_id}"
        
        img_path = os.path.join(FACE_DIR, img)
        image = cv2.imread(img_path)

        if image is None:
            continue

        emb = extract_embedding(image)
        db.setdefault(key, []).append(emb)

    for key in db:
        db[key] = np.mean(db[key], axis=0)

    return db

DATABASE = build_database()
print(f"✔ Loaded biometric database with {len(DATABASE)} animals")


csv_exists = os.path.isfile(CSV_PATH)
csv_file = open(CSV_PATH, "a", newline="")
csv_writer = csv.writer(csv_file)

if not csv_exists:
    csv_writer.writerow([
        "tracking_id",
        "animal_class",
        "animal_id",
        "similarity_score",
        "timestamp"
    ])


yolo = YOLO(YOLO_MODEL)
cap = cv2.VideoCapture(VIDEO_SOURCE)

track_identity_map = {}
prev_time = 0


while True:
    ret, frame = cap.read()
    if not ret:
        break

    # FPS calculation
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
    prev_time = curr_time

    results = yolo.track(
        frame,
        conf=CONF_THRES,
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
            track_id = int(tid)
            x1, y1, x2, y2 = map(int, box.xyxy[0])


            if track_id in track_identity_map:
                animal_id = track_identity_map[track_id]
                score = 1.0
            else:
                # Head crop (upper 45%)
                h = y2 - y1
                head_y2 = y1 + int(0.45 * h)
                head_crop = frame[y1:head_y2, x1:x2]

                if head_crop.size == 0:
                    continue

                query_emb = extract_embedding(head_crop)

                best_id = "Unknown"
                best_score = -1

                for db_key, db_emb in DATABASE.items():
                    s = cosine_similarity([query_emb], [db_emb])[0][0]
                    if s > best_score:
                        best_score = s
                        best_id = db_key

                full_id = f"{label}_{best_id}" if best_id != "Unknown" else "Unknown"
                
                if best_score >= SIM_THRESHOLD and best_id != "Unknown":
                    animal_id = full_id
                    track_identity_map[track_id] = animal_id

                    # Save head crop
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_name = f"{label}_{best_id}_{track_id}_{ts}.jpg"
                    cv2.imwrite(os.path.join(FACE_DIR, img_name), head_crop)

                    csv_writer.writerow([
                        track_id,
                        label,
                        animal_id,
                        round(best_score, 3),
                        ts
                    ])
                    csv_file.flush()
                else:
                    animal_id = "Unknown"
                    best_score = 0.0

                score = best_score

            # Draw bounding box and label
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                          (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{label} TID:{track_id} ID:{animal_id} ({score:.2f})",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    cv2.putText(
        frame,
        f"FPS: {fps:.2f}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )

    cv2.imshow("Animal Biometric Identification", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
csv_file.close()
cv2.destroyAllWindows()

