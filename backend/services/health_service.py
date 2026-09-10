from typing import Dict


class HealthService:
    """Placeholder scoring only. This is not medical diagnosis."""

    def calculate(self, movement_score: float, total_sightings: int) -> Dict[str, float | str]:
        movement = max(0.0, min(100.0, float(movement_score)))
        feeding = max(30.0, min(100.0, 55.0 + min(total_sightings, 20) * 2.0))
        activity = max(20.0, min(100.0, (movement * 0.65) + (feeding * 0.35)))
        overall = (movement * 0.45) + (feeding * 0.25) + (activity * 0.30)

        if overall >= 60.0:
            status = "Normal"
        elif overall >= 40.0:
            status = "Warning"
        else:
            status = "Critical"

        return {
            "movement_score": round(movement, 2),
            "feeding_score": round(feeding, 2),
            "activity_score": round(activity, 2),
            "overall_health_score": round(overall, 2),
            "health_score": round(overall, 2),
            "status": status,
        }
