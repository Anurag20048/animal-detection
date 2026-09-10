import numpy as np
from backend.models.recognizer import BiometricRecognizer


def test_same_embedding_matches_registered_animal():
    recognizer = BiometricRecognizer(0.80, {"full": 1.0})
    vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    recognizer.register("C00001", "Cow", {"full": vector})
    match = recognizer.find_best_match("Cow", {"full": vector})
    assert match.animal_id == "C00001"
    assert match.similarity > 0.99
    assert match.is_new is False


def test_different_embedding_can_create_new_identity():
    recognizer = BiometricRecognizer(0.80, {"full": 1.0})
    reference = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    candidate = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    recognizer.register("C00001", "Cow", {"full": reference})
    match = recognizer.find_best_match("Cow", {"full": candidate})
    assert match.is_new is True
