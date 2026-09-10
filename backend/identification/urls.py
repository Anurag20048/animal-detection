from django.urls import path

from . import views


app_name = "identification"

urlpatterns = [
    path("history/", views.identification_history_view, name="history"),
]

