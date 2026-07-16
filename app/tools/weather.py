"""
Weather information tool using OpenWeatherMap API.
Graceful degradation: failure returns a placeholder, not a crash (non-fatal by design).
"""
from __future__ import annotations

import logging
from datetime import date, datetime

import httpx
from langchain_core.tools import tool

from app.core.config import get_settings

logger = logging.getLogger("app.tools.weather")


def _kelvin_to_celsius(k: float) -> float:
    return round(k - 273.15, 1)


def _kelvin_to_fahrenheit(k: float) -> float:
    return round((k - 273.15) * 9 / 5 + 32, 1)


def _fetch_current_weather(destination: str) -> dict:
    """Fetch current weather from OpenWeatherMap."""
    settings = get_settings()
    params = {
        "q": destination,
        "appid": settings.WEATHER_API_KEY.get_secret_value(),
        "units": "metric",
    }
    url = f"{settings.WEATHER_BASE_URL}/weather"

    try:
        with httpx.Client(timeout=settings.WEATHER_TIMEOUT_SECONDS) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        temp_c = data["main"]["temp"]
        return {
            "avg_temp_celsius": temp_c,
            "avg_temp_fahrenheit": round(temp_c * 9 / 5 + 32, 1),
            "conditions": data["weather"][0]["description"].title(),
            "humidity_percent": data["main"]["humidity"],
            "precipitation_chance_percent": 0.0,  # not in current weather endpoint
            "warnings": [],
            "data_available": True,
        }
    except httpx.TimeoutException:
        logger.warning(f"Weather API timeout for destination='{destination}'")
        return _unavailable_weather()
    except httpx.HTTPStatusError as exc:
        logger.warning(f"Weather API HTTP {exc.response.status_code} for '{destination}'")
        return _unavailable_weather()
    except (KeyError, ValueError) as exc:
        logger.warning(f"Weather API parse error for '{destination}': {exc}")
        return _unavailable_weather()
    except Exception as exc:
        logger.error(f"Weather API unexpected error: {exc}")
        return _unavailable_weather()


def _unavailable_weather() -> dict:
    """Return a safe placeholder when weather data cannot be fetched."""
    return {
        "avg_temp_celsius": 0.0,
        "avg_temp_fahrenheit": 32.0,
        "conditions": "Weather data unavailable — please check local forecasts",
        "humidity_percent": 0.0,
        "precipitation_chance_percent": 0.0,
        "warnings": ["Weather data could not be retrieved. Check a local weather service."],
        "data_available": False,
    }


@tool
def weather_tool(destination: str, start_date: str, end_date: str) -> str:
    """
    Retrieve weather information for a destination and date range.

    Args:
        destination: City or region name (e.g., 'Kyoto, Japan').
        start_date: Travel start date in ISO format (YYYY-MM-DD).
        end_date: Travel end date in ISO format (YYYY-MM-DD).

    Returns:
        Formatted weather summary string. Never raises — degrades gracefully.
    """
    logger.info(f"weather_tool | destination='{destination}' | {start_date} to {end_date}")
    weather = _fetch_current_weather(destination)

    lines = [
        f"Weather information for: {destination}",
        f"Travel dates: {start_date} to {end_date}",
        f"",
        f"Temperature: {weather['avg_temp_celsius']}°C / {weather['avg_temp_fahrenheit']}°F",
        f"Conditions: {weather['conditions']}",
        f"Humidity: {weather['humidity_percent']}%",
        f"Precipitation chance: {weather['precipitation_chance_percent']}%",
    ]

    if weather["warnings"]:
        lines.append("\nWeather Warnings:")
        for w in weather["warnings"]:
            lines.append(f"  • {w}")

    if not weather["data_available"]:
        lines.append("\nNote: Live weather data was unavailable. Seasonal estimates may be used.")

    return "\n".join(lines)


def get_weather_data(destination: str) -> dict:
    """
    Direct (non-tool) function for use in research node when structured data is needed.
    Returns the raw dict (not formatted string).
    """
    return _fetch_current_weather(destination)
