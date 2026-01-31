from django.urls import path
from .views import WeatherForecastView

urlpatterns = [
    path("forecast/", WeatherForecastView.as_view()),
]