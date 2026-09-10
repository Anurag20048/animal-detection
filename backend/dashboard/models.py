from django.conf import settings
from django.db import models


class DashboardPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_preference",
    )
    dark_mode = models.BooleanField(default=True)
    default_page = models.CharField(max_length=64, default="Dashboard")
    widgets = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Dashboard preferences for {self.user}"

