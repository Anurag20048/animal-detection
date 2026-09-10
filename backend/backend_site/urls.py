from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/health/", permanent=False)),
    path("accounts/", include("accounts.urls")),
    path("animal-records/", include("animals.urls")),
    path("identification-records/", include("identification.urls")),
    path("analytics-app/", include("analytics_app.urls")),
    path("report-requests/", include("reports.urls")),
    path("dashboard-app/", include("dashboard.urls")),
    path("", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
