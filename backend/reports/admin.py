from django.contrib import admin

from .models import ReportRequest


@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    list_display = ("report_type", "output_format", "status", "requested_by", "created_at", "generated_at")
    list_filter = ("report_type", "output_format", "status", "created_at")
    search_fields = ("requested_by__username", "animal__unique_animal_id")

