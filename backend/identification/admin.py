from django.contrib import admin

from .models import IdentificationJob, IdentificationResult


class IdentificationResultInline(admin.TabularInline):
    model = IdentificationResult
    extra = 0
    readonly_fields = ("detection_timestamp",)


@admin.register(IdentificationJob)
class IdentificationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "requested_by", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("requested_by__username", "requested_by__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [IdentificationResultInline]


@admin.register(IdentificationResult)
class IdentificationResultAdmin(admin.ModelAdmin):
    list_display = ("job", "identified_animal", "detected_species", "confidence_score", "match_percentage", "detection_timestamp")
    list_filter = ("detected_species", "detection_timestamp")
    search_fields = ("identified_animal__unique_animal_id", "detected_species")

