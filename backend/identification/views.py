from django.http import JsonResponse

from .models import IdentificationResult


def identification_history_view(request):
    items = IdentificationResult.objects.select_related("identified_animal").values(
        "id",
        "identified_animal__unique_animal_id",
        "detected_species",
        "confidence_score",
        "match_percentage",
        "detection_timestamp",
    )[:100]
    return JsonResponse({"items": list(items)})

