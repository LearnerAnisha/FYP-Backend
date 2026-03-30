from django.urls import path
from .views import (ForecastView, CommoditiesView, MetricsView, UploadCSVView, RetrainView, HistoryView)

urlpatterns = [
    # Core forecast endpoint
    path('forecast/', ForecastView.as_view(), name='forecast'),

    # Data management
    path('upload/', UploadCSVView.as_view(), name='upload'),
    path('retrain/', RetrainView.as_view(), name='retrain'),

    # Info endpoints
    path('commodities/', CommoditiesView.as_view(), name='commodities'),
    path('metrics/', MetricsView.as_view(), name='metrics'),
    path('history/<str:commodity>/', HistoryView.as_view(), name='history'),
]