from django.contrib import admin

from .models import DashboardPreference


@admin.register(DashboardPreference)
class DashboardPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "dark_mode", "default_page", "updated_at")
    search_fields = ("user__username", "user__email")

