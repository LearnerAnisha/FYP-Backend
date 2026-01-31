from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import WeatherRequestSerializer
from .weather_services import fetch_weather_and_forecast

class WeatherForecastView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = WeatherRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data["lat"]
        lon = serializer.validated_data["lon"]

        data = fetch_weather_and_forecast(lat, lon)

        return Response(data, status=status.HTTP_200_OK)
