from django.conf import settings
from django.db import models

from animals.models import Animal


class ReportRequest(models.Model):
    class ReportType(models.TextChoices):
        IDENTIFICATION_SUMMARY = "identification_summary", "Identification Summary"
        ANIMAL_PROFILE = "animal_profile", "Animal Profile"
        ANALYTICS = "analytics", "Analytics"

    class Format(models.TextChoices):
        PDF = "pdf", "PDF"
        CSV = "csv", "CSV"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATED = "generated", "Generated"
        FAILED = "failed", "Failed"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_requests",
    )
    animal = models.ForeignKey(
        Animal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_requests",
    )
    report_type = models.CharField(max_length=64, choices=ReportType.choices)
    output_format = models.CharField(max_length=16, choices=Format.choices, default=Format.PDF)
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING, db_index=True)
    file = models.FileField(upload_to="reports/generated/%Y/%m/%d/", blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["report_type", "created_at"]),
            models.Index(fields=["requested_by", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.report_type} {self.output_format} ({self.status})"

