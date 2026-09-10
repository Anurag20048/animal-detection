from django.http import JsonResponse

from .models import Animal


def animal_index_view(request):
    return JsonResponse(
        {
            "count": Animal.objects.count(),
            "items": list(
                Animal.objects.values(
                    "unique_animal_id",
                    "name",
                    "species",
                    "breed",
                    "gender",
                    "registration_date",
                )[:50]
            ),
        }
    )

