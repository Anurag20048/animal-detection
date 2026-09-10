from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def profile_view(request):
    profile = getattr(request.user, "profile", None)
    return JsonResponse(
        {
            "username": request.user.get_username(),
            "email": request.user.email,
            "role": getattr(profile, "role", "user"),
        }
    )

