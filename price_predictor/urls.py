from django.urls import path
from .views import (
    FetchMarketPriceAPIView,
    LatestPricesAPIView,
    DailyPriceHistoryAPIView,
    MarketPriceAnalysisAPIView,
)

urlpatterns = [
    path("fetch-market-prices/", FetchMarketPriceAPIView.as_view(), name="fetch"),
    path("latest/", LatestPricesAPIView.as_view(), name="latest-prices"),
    path("history/", DailyPriceHistoryAPIView.as_view(), name="history"),
    path("analysis/", MarketPriceAnalysisAPIView.as_view(), name="analysis"),
]
