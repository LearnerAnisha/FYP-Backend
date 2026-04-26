# disease/urls.py
from django.urls import path
from .views import DiseaseDetectionAPIView, RecentScansAPIView, ScanDetailAPIView

urlpatterns = [
    path("detect/", DiseaseDetectionAPIView.as_view()),
    path("recent-scans/", RecentScansAPIView.as_view()),
    path("scans/<int:pk>/", ScanDetailAPIView.as_view()),
]
