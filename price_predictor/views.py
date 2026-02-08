import requests
from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from krishiSathi import settings
from .models import MasterProduct, DailyPriceHistory
from .serializers import MasterProductSerializer, DailyPriceHistorySerializer
from .filters import MasterProductFilter
from rest_framework.permissions import AllowAny
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class FetchMarketPriceAPIView(APIView):
    """
    Fetches latest market prices from Kalimati API and updates:

    1. MasterProduct:
        - If commodity appears today → update normally
        - If commodity missing → set today's fields NULL, keep last_price unchanged
    2. DailyPriceHistory:
        - Insert only for commodities that appear in todays API
    """

    permission_classes = [AllowAny]

    def get(self, request):
        
        api_url = "https://kalimatimarket.gov.np/api/daily-prices/en"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        try:
            response = requests.get(api_url,headers=headers,timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if "date" not in data or "prices" not in data:
                return Response(
            {
                "error": "Invalid API response",
                "received_keys": list(data.keys()),
                "raw_response": data
            },
            status=500
        )
        except Exception as e:
            return Response({"error": f"API fetch failed: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        api_date = datetime.strptime(data["date"], "%Y-%m-%d").date()

        # Track which items appear today
        products_seen_today = set()

        # Process all items from API
        for item in data["prices"]:
            name = item["commodityname"]
            unit = item.get("commodityunit", "")
            min_p = float(item["minprice"])
            max_p = float(item["maxprice"])
            avg_p = float(item["avgprice"])

            products_seen_today.add(name)

            product, created = MasterProduct.objects.update_or_create(
                commodityname=name,
                defaults={
                    "commodityunit": unit,
                    "min_price": min_p,
                    "max_price": max_p,
                    "avg_price": avg_p,
                    "last_price": avg_p,   # always updated when new data exists
                }
            )

            DailyPriceHistory.objects.update_or_create(
                product=product,
                date=api_date,
                defaults={
                    "min_price": min_p,
                    "max_price": max_p,
                    "avg_price": avg_p,
                }
            )

        #For items missing today → set today's fields NULL
        all_products = MasterProduct.objects.all()

        for product in all_products:
            if product.commodityname not in products_seen_today:
                product.min_price = None
                product.max_price = None
                product.avg_price = None
                # last_price remains unchanged (previous known price)
                product.save(update_fields=["min_price", "max_price", "avg_price"])

        return Response(
            {"message": "Market prices updated (missing items set to NULL)", "date": str(api_date)},
            status=status.HTTP_201_CREATED
        )

class LatestPricesAPIView(ListAPIView):
    """
    Latest market prices with:
    - search by commodity name
    - filter by price range
    - sort ascending / descending
    """

    queryset = MasterProduct.objects.all()
    serializer_class = MasterProductSerializer
    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    # Search
    search_fields = ["commodityname"]

    # Filter (from filters.py)
    filterset_class = MasterProductFilter

    # ↕ Sorting
    ordering_fields = [
        "commodityname",
        "min_price",
        "max_price",
        "avg_price",
        "last_price",
    ]

    ordering = ["commodityname"]  # default

class DailyPriceHistoryAPIView(APIView):
    """Returns complete historical data."""

    permission_classes = [AllowAny]

    def get(self, request):
        data = DailyPriceHistory.objects.all()
        serializer = DailyPriceHistorySerializer(data, many=True)
        return Response(serializer.data)
class MarketPriceAnalysisAPIView(APIView):
    """
    Compares today's vs yesterday’s average price for all commodities.
    Missing data does NOT affect historical analysis.
    """

    permission_classes = [AllowAny]
    
    def get(self, request):
        dates = list(
            DailyPriceHistory.objects.values_list("date", flat=True)
            .distinct()
            .order_by("date")
        )

        if len(dates) < 2:
            return Response({"error": "Not enough historical data"}, status=400)

        yesterday = dates[-2]
        today = dates[-1]

        today_rows = DailyPriceHistory.objects.filter(date=today)
        yesterday_rows = DailyPriceHistory.objects.filter(date=yesterday)

        # Fast lookup map
        yesterday_map = {row.product.id: row.avg_price for row in yesterday_rows}

        results = []
        ups = downs = 0

        for row in today_rows:
            pid = row.product.id
            today_avg = row.avg_price
            y_avg = yesterday_map.get(pid)

            if y_avg:
                change_pct = ((today_avg - y_avg) / y_avg) * 100
            else:
                change_pct = 0

            trend = (
                "up" if change_pct > 0 else
                "down" if change_pct < 0 else
                "same"
            )

            if trend == "up": ups += 1
            if trend == "down": downs += 1

            results.append({
                "commodity": row.product.commodityname,
                "today": today_avg,
                "yesterday": y_avg,
                "change_percentage": round(change_pct, 2),
                "trend": trend,
            })

        market_trend = (
            "Bullish" if ups > downs else
            "Bearish" if downs > ups else
            "Neutral"
        )

        return Response({
            "today": str(today),
            "yesterday": str(yesterday),
            "market_trend": market_trend,
            "changes": results
        })
        
class PriceStatsAPIView(APIView):
    """
    Price Predictor dashboard statistics (app-level logic).
    """

    def get(self, request):
        today = timezone.now().date()

        total_products = MasterProduct.objects.count()

        updated_today = MasterProduct.objects.filter(
            dailypricehistory__date=today
        ).distinct().count()

        missing_today = total_products - updated_today

        total_price_records = DailyPriceHistory.objects.count()

        return Response({
            "total_products": total_products,
            "updated_today": updated_today,
            "missing_today": missing_today,
            "total_price_records": total_price_records,
        })