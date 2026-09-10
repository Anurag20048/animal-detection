from django.contrib import admin

from .models import Animal, AnimalImage, BiometricEmbedding


class AnimalImageInline(admin.TabularInline):
    model = AnimalImage
    extra = 0


class BiometricEmbeddingInline(admin.TabularInline):
    model = BiometricEmbedding
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ("unique_animal_id", "name", "species", "breed", "gender", "registration_date", "is_active")
    list_filter = ("species", "breed", "gender", "is_active", "registration_date")
    search_fields = ("unique_animal_id", "name", "species", "breed")
    readonly_fields = ("registration_date", "created_at", "updated_at")
    inlines = [AnimalImageInline, BiometricEmbeddingInline]


@admin.register(AnimalImage)
class AnimalImageAdmin(admin.ModelAdmin):
    list_display = ("animal", "image_type", "is_reference", "upload_date")
    list_filter = ("image_type", "is_reference", "upload_date")
    search_fields = ("animal__unique_animal_id", "animal__name")


@admin.register(BiometricEmbedding)
class BiometricEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("animal", "region", "model_name", "vector_dimension", "created_at")
    list_filter = ("region", "model_name", "created_at")
    search_fields = ("animal__unique_animal_id",)

