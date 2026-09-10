from django.http import JsonResponse

from .models import ReportRequest


def reports_view(request):
    return JsonResponse(
        {
            "count": ReportRequest.objects.count(),
            "items": list(
                ReportRequest.objects.values(
                    "id",
                    "report_type",
                    "output_format",
                    "status",
                    "created_at",
                    "generated_at",
                )[:50]
            ),
        }
    )

