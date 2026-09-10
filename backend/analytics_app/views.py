from django.db.models import Count
from django.http import JsonResponse

from animals.models import Animal
from identification.models import IdentificationResult


def analytics_view(request):
    species_distribution = dict(
        Animal.objects.values_list("species").annotate(count=Count("id"))
    )
    return JsonResponse(
        {
            "total_registered_animals": Animal.objects.count(),
            "total_identifications": IdentificationResult.objects.count(),
            "species_distribution": species_distribution,
        }
    )

