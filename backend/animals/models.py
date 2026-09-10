from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


class Animal(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNKNOWN = "unknown", "Unknown"

    unique_animal_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    species = models.CharField(max_length=100, db_index=True)
    breed = models.CharField(max_length=100, blank=True)
    gender = models.CharField(
        max_length=16,
        choices=Gender.choices,
        default=Gender.UNKNOWN,
        db_index=True,
    )
    age = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)
    registration_date = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_animals",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-registration_date"]
        indexes = [
            models.Index(fields=["species", "breed"]),
            models.Index(fields=["created_by", "registration_date"]),
        ]

    def __str__(self) -> str:
        label = self.name or self.unique_animal_id
        return f"{label} ({self.species})"


class AnimalImage(models.Model):
    class ImageType(models.TextChoices):
        FULL = "full", "Full Body"
        FACE = "face", "Face"
        NOSE = "nose", "Nose"
        EARS = "ears", "Ears"
        PATTERN = "pattern", "Pattern"
        OTHER = "other", "Other"

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to="animals/images/%Y/%m/%d/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "bmp"])],
    )
    upload_date = models.DateTimeField(auto_now_add=True, db_index=True)
    image_type = models.CharField(max_length=32, choices=ImageType.choices, default=ImageType.FULL)
    is_reference = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-upload_date"]
        indexes = [
            models.Index(fields=["animal", "image_type"]),
            models.Index(fields=["upload_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.animal.unique_animal_id} {self.image_type}"


class BiometricEmbedding(models.Model):
    class Region(models.TextChoices):
        FULL = "full", "Full"
        FOREHEAD = "forehead", "Forehead"
        EYES = "eyes", "Eyes"
        NOSE = "nose", "Nose"
        EARS = "ears", "Ears"
        PATTERN = "pattern", "Pattern"

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="embeddings")
    source_image = models.ForeignKey(
        AnimalImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="embeddings",
    )
    region = models.CharField(max_length=32, choices=Region.choices, default=Region.FULL)
    embedding_vector = models.JSONField()
    model_name = models.CharField(max_length=128, default="resnet50")
    vector_dimension = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["animal", "region"]),
            models.Index(fields=["model_name", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.animal.unique_animal_id} {self.region} embedding"

