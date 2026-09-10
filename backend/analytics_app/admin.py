from django.contrib import admin

from .models import AnalyticsSnapshot


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_date", "total_registered_animals", "total_identifications", "average_confidence", "created_at")
    list_filter = ("snapshot_date",)

