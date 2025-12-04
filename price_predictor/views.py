from django.shortcuts import render

# Create your views here.
import requests
from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import MarketPrice
from rest_framework.generics import ListAPIView
from .serializers import MarketPriceSerializer

class FetchMarketPriceAPIView(APIView):
    """
    Fetches daily market price data from Kalimati External API and stores it in DB.
    If records of the same item already exist for today's date, they are updated instead of duplicated.
    """

    def get(self, request):
        external_api_url = "https://kalimatimarket.gov.np/api/daily-prices/en"

        try:
            # Send GET request to external API
            response = requests.get(external_api_url)
            response.raise_for_status()   # Raise error if API returns 4xx or 5xx
            data = response.json()
        except Exception as e:
            return Response({"error": f"Failed to fetch data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract date from API response
        api_date = datetime.strptime(data["date"], "%Y-%m-%d").date()

        # Loop through all price items returned by API
        for item in data["prices"]:
            MarketPrice.objects.update_or_create(
                commodity_name=item["commodityname"],
                date=api_date,  # Ensure one record per day per commodity
                defaults={
                    "commodity_unit": item.get("commodityunit", ""),
                    "min_price": float(item["minprice"]),
                    "max_price": float(item["maxprice"]),
                    "avg_price": float(item["avgprice"]),
                }
            )

        return Response({"message": "Market prices fetched and stored successfully", "date": str(api_date)},
                        status=status.HTTP_201_CREATED)
    
class MarketPriceListAPIView(ListAPIView):
    """
    Returns stored price data to frontend (React or mobile app).
    """
    queryset = MarketPrice.objects.all()
    serializer_class = MarketPriceSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg
from .models import MarketPrice
from rest_framework import status

class MarketPriceAnalysisAPIView(APIView):
    """
    Returns:
    - today's date
    - previous available date
    - price change (%) per commodity
    - overall market trend
    """

    def get(self, request):
        qs = MarketPrice.objects.all()

        if not qs.exists():
            return Response({"error": "No data available"}, status=404)

        # Get distinct dates sorted (oldest first)
        dates = list(qs.values_list("date", flat=True).distinct().order_by("date"))

        if len(dates) < 2:
            return Response({"error": "Need at least 2 days of data to compute trends"}, status=400)

        prev_date = dates[-2]   # second latest
        today_date = dates[-1]  # latest

        today_items = qs.filter(date=today_date)
        prev_items = qs.filter(date=prev_date)

        # Build a dict for previous day prices
        prev_price_map = {
            item.commodity_name: item.avg_price
            for item in prev_items
        }

        commodity_changes = []
        ups = 0
        downs = 0

        for item in today_items:
            name = item.commodity_name
            today_price = item.avg_price
            prev_price = prev_price_map.get(name)

            if prev_price:
                change_pct = ((today_price - prev_price) / prev_price) * 100
                trend = "up" if change_pct > 0 else "down" if change_pct < 0 else "same"

                if change_pct > 0:
                    ups += 1
                elif change_pct < 0:
                    downs += 1
            else:
                change_pct = 0
                trend = "unknown"

            commodity_changes.append({
                "commodity": name,
                "today": today_price,
                "yesterday": prev_price,
                "change_percentage": round(change_pct, 2),
                "trend": trend
            })

        # Determine global trend
        if ups > downs:
            market_trend = "Bullish"
        elif downs > ups:
            market_trend = "Bearish"
        else:
            market_trend = "Neutral"

        return Response({
            "today": str(today_date),
            "yesterday": str(prev_date),
            "market_trend": market_trend,
            "commodity_changes": commodity_changes
        })

