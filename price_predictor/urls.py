from django.urls import path
from .views import FetchMarketPriceAPIView,MarketPriceListAPIView

urlpatterns = [
    path("fetch-market-prices/", FetchMarketPriceAPIView.as_view(), name="fetch-market-prices"),
    path("prices/", MarketPriceListAPIView.as_view(), name="prices-list"),
]
