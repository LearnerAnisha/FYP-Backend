import requests
from django.conf import settings


class WeatherServiceError(Exception):
    """Custom exception for weather service failures."""
    pass


# -----------------------------
# Reverse Geocoding
# -----------------------------
def reverse_geocode(lat, lon):
    try:
        url = (
            "https://api.openweathermap.org/geo/1.0/reverse"
            f"?lat={lat}&lon={lon}&limit=1&appid={settings.OPENWEATHER_API_KEY}"
        )

        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        return data[0]["name"] if data else None

    except Exception:
        return None


# -----------------------------
# Fetch Weather by City
# -----------------------------
def fetch_weather_by_city(city):
    try:
        url = (
            "https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city}&units=metric&appid={settings.OPENWEATHER_API_KEY}"
        )

        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()

    except Exception:
        raise WeatherServiceError("Failed to fetch weather data")


# -----------------------------
# Build Final Weather Response
# -----------------------------
def build_weather_response(lat=None, lon=None):
    # 1️⃣ Determine city
    city = None

    if lat and lon:
        city = reverse_geocode(lat, lon)

    if not city:
        city = "Kathmandu"

    # 2️⃣ Fetch weather
    raw_data = fetch_weather_by_city(city)

    try:
        current = raw_data["list"][0]

        forecast = []
        for item in raw_data["list"][::8][:5]:
            forecast.append({
                "day": item["dt_txt"].split(" ")[0],
                "temperature": item["main"]["temp"],
                "condition": item["weather"][0]["main"],
                "rain_probability": item.get("pop", 0) * 100,
            })

        return {
            "city": city,
            "current": {
                "temperature": current["main"]["temp"],
                "humidity": current["main"]["humidity"],
                "wind_speed": current["wind"]["speed"],
                "rainfall": current.get("rain", {}).get("3h", 0),
                "condition": current["weather"][0]["main"],
            },
            "forecast": forecast,
        }

    except Exception:
        raise WeatherServiceError("Malformed weather data received")