from django.http import JsonResponse

from animals.models import Animal
from identification.models import IdentificationResult
from reports.models import ReportRequest


def dashboard_summary_view(request):
    return JsonResponse(
        {
            "total_animals": Animal.objects.count(),
            "total_identifications": IdentificationResult.objects.count(),
            "total_reports": ReportRequest.objects.count(),
        }
    )

