from django.urls import path
from .views import FetchMarketPriceAPIView,MarketPriceListAPIView,MarketPriceAnalysisAPIView

urlpatterns = [
    path("fetch-market-prices/", FetchMarketPriceAPIView.as_view(), name="fetch-market-prices"),
    path("prices/", MarketPriceListAPIView.as_view(), name="prices-list"),
    path("analysis/", MarketPriceAnalysisAPIView.as_view()),
]
