from django.urls import path
from .views import CurrentWeatherAPIView

urlpatterns = [
    path("current/", CurrentWeatherAPIView.as_view(), name="current-weather"),
]