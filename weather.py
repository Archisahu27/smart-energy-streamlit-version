import requests
import os
from datetime import datetime

OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')

def get_current_weather(city="Nagpur"):
    """
    OpenWeatherMap ka 5-day/3-hour FORECAST endpoint use karta hai,
    taaki genuine "today's min/max temperature" mile — na ki sirf
    ek pal ka snapshot (jaisa 'current weather' endpoint deta tha).
    """
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if response.status_code == 200:
            today_str = datetime.now().strftime('%Y-%m-%d')

            today_entries = [
                entry for entry in data['list']
                if entry['dt_txt'].startswith(today_str)
            ]

            if not today_entries:
                today_entries = data['list'][:8]

            print(f"DEBUG WEATHER - Number of forecast entries used: {len(today_entries)}")
            print(f"DEBUG WEATHER - Entries: {[e['dt_txt'] for e in today_entries]}")

            temps = [entry['main']['temp'] for entry in today_entries]
            temp_max = max(entry['main']['temp_max'] for entry in today_entries)
            temp_min = min(entry['main']['temp_min'] for entry in today_entries)
            avg_temp = sum(temps) / len(temps)

            avg_wind = sum(entry['wind']['speed'] for entry in today_entries) / len(today_entries)
            total_rain = sum(entry.get('rain', {}).get('3h', 0.0) for entry in today_entries)

            weather_data = {
                'T2M': round(avg_temp, 2),
                'T2M_MAX': round(temp_max, 2),
                'T2M_MIN': round(temp_min, 2),
                'PRECTOTCORR': round(total_rain, 2),
                'WS2M': round(avg_wind, 2),
                'source': 'live_api_forecast'
            }
            return weather_data
        else:
            return get_fallback_weather()

    except Exception as e:
        print(f"Weather API error: {e}")
        return get_fallback_weather()

def get_fallback_weather():
    return {
        'T2M': 28.0,
        'T2M_MAX': 32.0,
        'T2M_MIN': 24.0,
        'PRECTOTCORR': 0.0,
        'WS2M': 3.0,
        'source': 'fallback_default'
    }

