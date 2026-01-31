import requests
from datetime import datetime
from django.conf import settings
from collections import OrderedDict

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/forecast"

def fetch_weather_and_forecast(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }

    response = requests.get(OPENWEATHER_URL, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    forecast_list = data["list"]

    # -----------------------
    # CURRENT WEATHER
    # -----------------------
    current = forecast_list[0]

    current_weather = {
        "temperature": round(current["main"]["temp"]),
        "humidity": current["main"]["humidity"],
        "wind_speed": current["wind"]["speed"],
        "rainfall": current.get("rain", {}).get("3h", 0),
        "condition": current["weather"][0]["main"],
    }

    # -----------------------
    # 5-DAY FORECAST (1 per day)
    # -----------------------
    daily_forecast = OrderedDict()

    for item in forecast_list:
        date_obj = datetime.fromtimestamp(item["dt"])
        date_key = date_obj.date()

        if date_key not in daily_forecast:
            daily_forecast[date_key] = {
                "date": date_obj.strftime("%Y-%m-%d"),
                "day": date_obj.strftime("%A"),   # Monday, Tuesday
                "temp": round(item["main"]["temp"]),
                "condition": item["weather"][0]["main"],
                "rain": item.get("rain", {}).get("3h", 0),
            }

        if len(daily_forecast) == 5:
            break

    return {
        "current": current_weather,
        "forecast": list(daily_forecast.values())
    }
