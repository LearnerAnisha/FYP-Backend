# disease/urls.py
from django.urls import path
from .views import DiseaseDetectionAPIView, RecentScansAPIView

urlpatterns = [
    path("detect/", DiseaseDetectionAPIView.as_view()),
    path("recent-scans/", RecentScansAPIView.as_view()),
]
