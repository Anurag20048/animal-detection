from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

from animals.models import Animal


class IdentificationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    uploaded_image = models.ImageField(
        upload_to="identification/uploads/%Y/%m/%d/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "bmp"])],
    )
    uploaded_video = models.FileField(
        upload_to="identification/videos/%Y/%m/%d/",
        validators=[FileExtensionValidator(["mp4", "mov", "avi", "mkv", "webm"])],
        blank=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="identification_jobs",
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING, db_index=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requested_by", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Identification job {self.pk} ({self.status})"


class IdentificationResult(models.Model):
    job = models.ForeignKey(IdentificationJob, on_delete=models.CASCADE, related_name="results")
    identified_animal = models.ForeignKey(
        Animal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="identification_results",
    )
    detected_species = models.CharField(max_length=100, blank=True, db_index=True)
    bbox = models.JSONField(default=dict, blank=True)
    confidence_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    match_percentage = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    similarity_score = models.FloatField(default=0.0, validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)])
    top_k_matches = models.JSONField(default=list, blank=True)
    feature_scores = models.JSONField(default=dict, blank=True)
    detection_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-detection_timestamp"]
        indexes = [
            models.Index(fields=["identified_animal", "detection_timestamp"]),
            models.Index(fields=["detected_species", "detection_timestamp"]),
            models.Index(fields=["confidence_score"]),
        ]

    def __str__(self) -> str:
        animal = self.identified_animal.unique_animal_id if self.identified_animal else "Unknown"
        return f"{animal} {self.match_percentage:.1f}%"

