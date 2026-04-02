from django.urls import path
from .views import (
    ForecastView,
    CommoditiesView,
    MetricsView,
    UploadCSVView,
    RetrainView,
    HistoryView,
    MarketAnalysisView,  
)

urlpatterns = [
    # Core forecast
    path("forecast/",ForecastView.as_view(), name="forecast"),

    # Market data (live prices + yesterday comparison)
    path("market-analysis/",  MarketAnalysisView.as_view(), name="market-analysis"),

    # Data management
    path("upload/", UploadCSVView.as_view(), name="upload"),
    path("retrain/", RetrainView.as_view(), name="retrain"),

    # Info endpoints
    path("commodities/", CommoditiesView.as_view(), name="commodities"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    path("history/<str:commodity>/", HistoryView.as_view(), name="history"),
]