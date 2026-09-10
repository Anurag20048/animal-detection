from django.db import models


class AnalyticsSnapshot(models.Model):
    snapshot_date = models.DateField(db_index=True)
    total_registered_animals = models.PositiveIntegerField(default=0)
    total_identifications = models.PositiveIntegerField(default=0)
    average_confidence = models.FloatField(default=0.0)
    species_distribution = models.JSONField(default=dict, blank=True)
    daily_detections = models.JSONField(default=dict, blank=True)
    monthly_detections = models.JSONField(default=dict, blank=True)
    top_animals = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-snapshot_date"]
        indexes = [
            models.Index(fields=["snapshot_date"]),
        ]

    def __str__(self) -> str:
        return f"Analytics snapshot {self.snapshot_date}"

