from typing import Dict, Mapping, Tuple
import numpy as np

DEFAULT_REGION_WEIGHTS = {"full": 0.40, "nose": 0.30, "eyes": 0.20, "forehead": 0.10}

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12: return vector
    return vector / norm

def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float:
    first_norm, second_norm = normalize_embedding(first), normalize_embedding(second)
    if first_norm.size == 0 or second_norm.size == 0: return 0.0
    denominator = float(np.linalg.norm(first_norm) * np.linalg.norm(second_norm))
    if denominator <= 1e-12: return 0.0
    return float(np.dot(first_norm, second_norm) / denominator)

def weighted_similarity(candidate: Mapping[str, np.ndarray], reference: Mapping[str, np.ndarray], weights: Mapping[str, float] | None = None) -> Tuple[float, Dict[str, float]]:
    active_weights = weights or DEFAULT_REGION_WEIGHTS
    weighted_total, used_weight = 0.0, 0.0
    region_scores: Dict[str, float] = {}
    for region, weight in active_weights.items():
        if region not in candidate or region not in reference: continue
        score = cosine_similarity(candidate[region], reference[region])
        region_scores[region] = score
        weighted_total += score * weight
        used_weight += weight
    if used_weight <= 1e-12: return 0.0, region_scores
    return float(weighted_total / used_weight), region_scores
