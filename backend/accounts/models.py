from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        RESEARCHER = "researcher", "Researcher"
        USER = "user", "User"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.USER)
    organization = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} ({self.role})"

