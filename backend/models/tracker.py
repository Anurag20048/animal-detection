from dataclasses import dataclass
from threading import RLock
from typing import Dict, Optional, Set, Tuple

@dataclass
class TrackState:
    tracking_id: int
    animal_id: str
    last_frame: int
    last_center: Tuple[float, float]
    movement_distance: float = 0.0

class TrackBiometricMapper:
    """Maps ByteTrack IDs to persistent biometric animal IDs."""
    def __init__(self, max_inactive_frames: int = 90) -> None:
        self.max_inactive_frames = max_inactive_frames
        self.track_to_animal: Dict[int, str] = {}
        self.animal_to_tracks: Dict[str, Set[int]] = {}
        self.track_states: Dict[int, TrackState] = {}
        self._lock = RLock()

    def get_animal_id(self, tracking_id: int) -> Optional[str]:
        if tracking_id < 0: return None
        with self._lock: return self.track_to_animal.get(tracking_id)

    def assign(self, tracking_id: int, animal_id: str, frame_index: int, center: Tuple[float, float]) -> bool:
        if tracking_id < 0: return False
        with self._lock:
            existing_animal = self.track_to_animal.get(tracking_id)
            if existing_animal and existing_animal != animal_id:
                self.animal_to_tracks.get(existing_animal, set()).discard(tracking_id)
            self.track_to_animal[tracking_id] = animal_id
            self.animal_to_tracks.setdefault(animal_id, set()).add(tracking_id)
            duplicate = self._has_active_duplicate(animal_id, tracking_id, frame_index)
            self.update_position(tracking_id, animal_id, frame_index, center)
            return duplicate

    def update_position(self, tracking_id: int, animal_id: str, frame_index: int, center: Tuple[float, float]) -> None:
        if tracking_id < 0: return
        state = self.track_states.get(tracking_id)
        if state is None:
            self.track_states[tracking_id] = TrackState(tracking_id, animal_id, frame_index, center)
            return
        dx, dy = center[0] - state.last_center[0], center[1] - state.last_center[1]
        state.movement_distance += (dx * dx + dy * dy) ** 0.5
        state.last_center, state.last_frame, state.animal_id = center, frame_index, animal_id

    def movement_score(self, animal_id: str) -> float:
        with self._lock:
            distance = sum(s.movement_distance for s in self.track_states.values() if s.animal_id == animal_id)
        return float(max(0.0, min(100.0, distance / 12.0)))

    def _has_active_duplicate(self, animal_id: str, current_tracking_id: int, frame_index: int) -> bool:
        for tracking_id in self.animal_to_tracks.get(animal_id, set()):
            if tracking_id == current_tracking_id: continue
            state = self.track_states.get(tracking_id)
            if state and frame_index - state.last_frame <= self.max_inactive_frames: return True
        return False
