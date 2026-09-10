from dataclasses import dataclass
from typing import Dict, Mapping, Optional

import numpy as np

try:
    from backend.utils.similarity import normalize_embedding, weighted_similarity
except ModuleNotFoundError:
    from utils.similarity import normalize_embedding, weighted_similarity

@dataclass
class RecognitionMatch:
    animal_id: Optional[str]
    similarity: float
    region_scores: Dict[str, float]
    is_new: bool = False

class BiometricRecognizer:
    def __init__(self, similarity_threshold: float, region_weights: Mapping[str, float], embedding_momentum: float = 0.90) -> None:
        self.similarity_threshold = similarity_threshold
        self.region_weights = dict(region_weights)
        self.embedding_momentum = embedding_momentum
        self.embeddings: Dict[str, Dict[str, np.ndarray]] = {}
        self.animal_types: Dict[str, str] = {}

    def register(self, animal_id: str, animal_type: str, embeddings: Mapping[str, np.ndarray]) -> None:
        self.animal_types[animal_id] = animal_type
        self.embeddings[animal_id] = {region: normalize_embedding(vector) for region, vector in embeddings.items()}

    def compare_to_animal(self, animal_id: str, embeddings: Mapping[str, np.ndarray]) -> RecognitionMatch:
        reference = self.embeddings.get(animal_id)
        if not reference: return RecognitionMatch(animal_id=animal_id, similarity=0.0, region_scores={})
        score, region_scores = weighted_similarity(embeddings, reference, weights=self.region_weights)
        return RecognitionMatch(animal_id=animal_id, similarity=score, region_scores=region_scores)

    def find_best_match(self, animal_type: str, embeddings: Mapping[str, np.ndarray]) -> RecognitionMatch:
        best_match = RecognitionMatch(animal_id=None, similarity=0.0, region_scores={})
        for animal_id, reference in self.embeddings.items():
            if self.animal_types.get(animal_id) != animal_type: continue
            score, region_scores = weighted_similarity(embeddings, reference, weights=self.region_weights)
            if score > best_match.similarity:
                best_match = RecognitionMatch(animal_id=animal_id, similarity=score, region_scores=region_scores)
        best_match.is_new = best_match.similarity < self.similarity_threshold
        return best_match

    def update(self, animal_id: str, embeddings: Mapping[str, np.ndarray]) -> None:
        existing = self.embeddings.get(animal_id)
        if not existing: return
        for region, vector in embeddings.items():
            vector = normalize_embedding(vector)
            if region not in existing:
                existing[region] = vector
                continue
            blended = existing[region] * self.embedding_momentum + vector * (1.0 - self.embedding_momentum)
            existing[region] = normalize_embedding(blended)

    def serialize_record(self, animal_id: str) -> Dict[str, object]:
        return {"animal_id": animal_id, "animal_type": self.animal_types.get(animal_id, "Other Animals"), "embeddings": {region: vector.astype(float).tolist() for region, vector in self.embeddings.get(animal_id, {}).items()}}

    def load_record(self, record: Mapping[str, object]) -> None:
        animal_id = str(record.get("animal_id", "")).strip()
        animal_type = str(record.get("animal_type", "Other Animals")).strip()
        raw_embeddings = record.get("embeddings", {})
        if not animal_id or not isinstance(raw_embeddings, dict): return
        embeddings: Dict[str, np.ndarray] = {}
        for region, vector in raw_embeddings.items():
            try: embeddings[str(region)] = normalize_embedding(np.asarray(vector, dtype=np.float32))
            except Exception: continue
        if embeddings: self.register(animal_id, animal_type, embeddings)
