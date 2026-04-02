from django.urls import path
from .views import (
    FetchMarketPriceAPIView,
    LatestPricesAPIView,
    DailyPriceHistoryAPIView,
    MarketPriceAnalysisAPIView,
    PriceStatsAPIView,
    LastMonthHistoryView
)

urlpatterns = [
    path("fetch-market-prices/", FetchMarketPriceAPIView.as_view(), name="fetch"),
    path("latest/", LatestPricesAPIView.as_view(), name="latest-prices"),
    path("history/", DailyPriceHistoryAPIView.as_view(), name="history"),
    path("analysis/", MarketPriceAnalysisAPIView.as_view(), name="analysis"),
    path("stats/", PriceStatsAPIView.as_view(), name="price-stats"),
    path("history-last-month/<str:commodity>/", LastMonthHistoryView.as_view(), name="history-last-month"),
]
