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
