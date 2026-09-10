from pathlib import Path
from types import SimpleNamespace
import threading

import numpy as np

from backend.services.animal_service import AnimalService


class FakeMatch:
    def __init__(self, animal_id=None, similarity=0.0, is_new=True):
        self.animal_id = animal_id
        self.similarity = similarity
        self.is_new = is_new


class FakeRecognizer:
    def __init__(self):
        self.embeddings = {}
        self.calls = []

    def find_best_match(self, animal_type, embeddings):
        self.calls.append(("find", animal_type))
        return FakeMatch()

    def compare_to_animal(self, animal_id, embeddings):
        self.calls.append(("compare", animal_id))
        return FakeMatch(animal_id, 0.93, False)

    def register(self, animal_id, animal_type, embeddings):
        self.embeddings[animal_id] = dict(embeddings)
        self.calls.append(("register", animal_id))

    def update(self, animal_id, embeddings):
        self.embeddings[animal_id] = dict(embeddings)

    def serialize_record(self, animal_id):
        return {"animal_id": animal_id, "regions": list(self.embeddings[animal_id])}


class FakeTracker:
    def __init__(self):
        self.mapping = {}

    def get_animal_id(self, tracking_id):
        return self.mapping.get(tracking_id)

    def assign(self, tracking_id, animal_id, frame_index, center):
        self.mapping[tracking_id] = animal_id
        return False

    def movement_score(self, animal_id):
        return 0.5


class FakeLogger:
    def __init__(self):
        self.detections = []
        self.animals = []
        self.health = []

    def log_detection(self, record):
        self.detections.append(record)

    def upsert_animal(self, profile):
        self.animals.append(profile)

    def log_health(self, record):
        self.health.append(record)

    def read_rows(self, name, limit=None):
        if name == "detections":
            return self.detections
        if name == "animals":
            return self.animals
        return []


class FakeMongo:
    def __init__(self):
        self.inserts = []
        self.upserts = []

    def insert_one(self, collection, document):
        self.inserts.append((collection, document))

    def upsert_one(self, collection, query, document):
        self.upserts.append((collection, query, document))


class FakeAlerts:
    def create_alert(self, title, message, metadata=None):
        pass


class FakeHealth:
    def calculate(self, movement_score, total_sightings):
        return {
            "movement_score": movement_score,
            "feeding_score": 0.0,
            "activity_score": 0.5,
            "overall_health_score": 0.5,
            "health_score": 0.5,
            "status": "Normal",
        }


class FakeSQLite:
    def __init__(self):
        self.detections = []
        self.profiles = []

    def save_detection(self, record):
        self.detections.append(record)

    def save_animal_profile(self, profile):
        self.profiles.append(profile)


def build_service(tmp_path):
    service = AnimalService.__new__(AnimalService)
    service.settings = SimpleNamespace(
        recognition_threshold=0.80,
        embedding_dir=Path(tmp_path),
        animal_prefixes={"Cow": "C", "Buffalo": "B", "Sheep": "S", "Other Animals": "O"},
    )
    service.csv_logger = FakeLogger()
    service.mongodb = FakeMongo()
    service.sqlite_storage = FakeSQLite()
    service.alert_service = FakeAlerts()
    service.health_service = FakeHealth()
    service.id_generator = SimpleNamespace(next_id=lambda _: "C00001", observe=lambda _: None)
    service.tracker = FakeTracker()
    service.recognizer = FakeRecognizer()
    service.profiles = {}
    service._lock = threading.RLock()
    service.embedding_store_path = Path(tmp_path) / "embeddings.json"
    service._save_embeddings = lambda: None
    return service


def test_new_detection_creates_identity_and_persists_event(tmp_path):
    service = build_service(tmp_path)
    result = service.process_detection(
        7,
        "Cow",
        0.91,
        {"full": np.ones(4, dtype=np.float32)},
        {"full": "crops/cow.jpg"},
        12,
        (50.0, 80.0),
    )

    assert result["animal_id"] == "C00001"
    assert result["is_new"] is True
    assert result["detection"]["animal_id"] == "C00001"
    assert 0 <= result["detection"]["confidence"] <= 1
    assert len(service.csv_logger.detections) == 1
    assert len(service.mongodb.inserts) == 1
    assert len(service.sqlite_storage.detections) == 1


def test_same_tracking_id_reuses_identity_and_compares_embedding(tmp_path):
    service = build_service(tmp_path)
    embedding = {"full": np.ones(4, dtype=np.float32)}

    first = service.process_detection(7, "Cow", 0.91, embedding, {}, 1, (10.0, 10.0))
    second = service.process_detection(7, "Cow", 0.94, embedding, {}, 2, (20.0, 20.0))

    assert first["animal_id"] == second["animal_id"] == "C00001"
    assert second["is_new"] is False
    assert second["similarity"] == 0.93
    assert ("compare", "C00001") in service.recognizer.calls
    assert len(service.sqlite_storage.detections) == 2
