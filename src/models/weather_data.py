"""
Weather data models for the Trainer application.
Author: Oliver Ernster

This module contains immutable data classes for weather information,
following solid Object-Oriented design principles with proper encapsulation
and single responsibility.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Optional, Protocol, Tuple

from version import __weather_version__, __weather_api_provider__

logger = logging.getLogger(__name__)


class WeatherCode(Enum):
    """WMO Weather interpretation codes."""
    CLEAR_SKY = 0
    MAINLY_CLEAR = 1
    PARTLY_CLOUDY = 2
    OVERCAST = 3
    FOG = 45
    DEPOSITING_RIME_FOG = 48
    DRIZZLE_LIGHT = 51
    DRIZZLE_MODERATE = 53
    DRIZZLE_DENSE = 55
    FREEZING_DRIZZLE_LIGHT = 56
    FREEZING_DRIZZLE_DENSE = 57
    RAIN_SLIGHT = 61
    RAIN_MODERATE = 63
    RAIN_HEAVY = 65
    FREEZING_RAIN_LIGHT = 66
    FREEZING_RAIN_HEAVY = 67
    SNOW_SLIGHT = 71
    SNOW_MODERATE = 73
    SNOW_HEAVY = 75
    SNOW_GRAINS = 77
    RAIN_SHOWERS_SLIGHT = 80
    RAIN_SHOWERS_MODERATE = 81
    RAIN_SHOWERS_VIOLENT = 82
    SNOW_SHOWERS_SLIGHT = 85
    SNOW_SHOWERS_HEAVY = 86
    THUNDERSTORM = 95
    THUNDERSTORM_SLIGHT_HAIL = 96
    THUNDERSTORM_HEAVY_HAIL = 99


class TemperatureUnit(Enum):
    """Temperature unit enumeration."""
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


class WeatherDataReader(Protocol):
    """Protocol for reading weather data."""
    
    def get_temperature(self) -> float:
        """Get temperature value."""
        ...
    
    def get_humidity(self) -> int:
        """Get humidity percentage."""
        ...
    
    def get_weather_code(self) -> int:
        """Get WMO weather code."""
        ...
    
    def get_timestamp(self) -> datetime:
        """Get data timestamp."""
        ...


class WeatherIconProvider(Protocol):
    """Protocol for providing weather icons."""
    
    def get_weather_icon(self, weather_code: int) -> str:
        """Get weather icon for given code."""
        ...


@dataclass(frozen=True)
class Location:
    """Immutable location data."""
    name: str
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """Validate location data."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")
        if not self.name.strip():
            raise ValueError("Location name cannot be empty")


@dataclass(frozen=True)
class WeatherData:
    """
    Immutable weather data for a specific time.
    
    Follows Single Responsibility Principle - only responsible for
    weather data representation and basic calculations.
    """
    timestamp: datetime
    temperature: float  # Celsius
    humidity: int  # Percentage (0-100)
    weather_code: int  # WMO weather code
    description: str = ""
    data_source: str = field(default=__weather_api_provider__)
    
    def __post_init__(self):
        """Validate weather data on creation."""
        if not (0 <= self.humidity <= 100):
            raise ValueError(f"Invalid humidity: {self.humidity}")
        if self.weather_code < 0:
            raise ValueError(f"Invalid weather code: {self.weather_code}")
    
    @property
    def temperature_display(self) -> str:
        """Get formatted temperature display."""
        return f"{self.temperature:.1f}°C"
    
    @property
    def humidity_display(self) -> str:
        """Get formatted humidity display."""
        return f"{self.humidity}%"
    
    @property
    def weather_code_enum(self) -> Optional[WeatherCode]:
        """Get weather code as enum if valid."""
        try:
            return WeatherCode(self.weather_code)
        except ValueError:
            return None
    
    def get_temperature_in_unit(self, unit: TemperatureUnit) -> float:
        """Get temperature in specified unit."""
        if unit == TemperatureUnit.FAHRENHEIT:
            return (self.temperature * 9/5) + 32
        return self.temperature
    
    def get_temperature_display_in_unit(self, unit: TemperatureUnit) -> str:
        """Get formatted temperature in specified unit."""
        temp = self.get_temperature_in_unit(unit)
        unit_symbol = "°F" if unit == TemperatureUnit.FAHRENHEIT else "°C"
        return f"{temp:.1f}{unit_symbol}"
    
    def is_precipitation(self) -> bool:
        """Check if weather involves precipitation."""
        precipitation_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 
                             71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}
        return self.weather_code in precipitation_codes
    
    def is_severe_weather(self) -> bool:
        """Check if weather is severe."""
        severe_codes = {65, 67, 75, 82, 86, 95, 96, 99}  # Heavy rain/snow, thunderstorms
        return self.weather_code in severe_codes


@dataclass(frozen=True)
class WeatherForecastData:
    """
    Complete weather forecast data container.
    
    Follows Single Responsibility Principle - only responsible for
    organizing and providing access to forecast data.
    """
    location: Location
    hourly_forecast: List[WeatherData] = field(default_factory=list)
    daily_forecast: List[WeatherData] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    data_version: str = field(default=__weather_version__)
    
    def __post_init__(self):
        """Validate forecast data."""
        if not self.hourly_forecast and not self.daily_forecast:
            raise ValueError("Forecast must contain either hourly or daily data")
    
    @property
    def current_day_hourly(self) -> List[WeatherData]:
        """Get 3-hourly forecast for current day only."""
        today = datetime.now().date()
        return [w for w in self.hourly_forecast if w.timestamp.date() == today]
    
    @property
    def is_stale(self) -> bool:
        """Check if forecast data is stale (older than 30 minutes)."""
        return (datetime.now() - self.last_updated) > timedelta(minutes=30)
    
    def get_current_weather(self) -> Optional[WeatherData]:
        """Get current weather data (closest to now)."""
        if not self.hourly_forecast:
            return None
        
        now = datetime.now()
        return min(self.hourly_forecast, 
                  key=lambda w: abs((w.timestamp - now).total_seconds()))
    
    def get_hourly_for_date(self, date: date) -> List[WeatherData]:
        """Get hourly forecast for specific date."""
        return [w for w in self.hourly_forecast if w.timestamp.date() == date]
    
    def get_daily_summary_for_date(self, date: date) -> Optional[WeatherData]:
        """Get daily summary for specific date."""
        for weather in self.daily_forecast:
            if weather.timestamp.date() == date:
                return weather
        return None
    
    def has_severe_weather_today(self) -> bool:
        """Check if there's severe weather in today's forecast."""
        today_hourly = self.current_day_hourly
        return any(w.is_severe_weather() for w in today_hourly)
    
    def get_temperature_range_today(self) -> Tuple[float, float]:
        """Get temperature range for today (min, max)."""
        today_hourly = self.current_day_hourly
        if not today_hourly:
            return (0.0, 0.0)
        
        temperatures = [w.temperature for w in today_hourly]
        return (min(temperatures), max(temperatures))


class WeatherIconStrategy(ABC):
    """Abstract strategy for weather icon display."""
    
    @abstractmethod
    def get_icon(self, weather_code: int) -> str:
        """Get icon for weather code."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get name of the icon strategy."""
        pass


class EmojiWeatherIconStrategy(WeatherIconStrategy):
    """Strategy using emoji icons for weather display."""
    
    WEATHER_ICONS = {
        0: "☀️",    # Clear sky
        1: "🌤️",    # Mainly clear
        2: "⛅",    # Partly cloudy
        3: "☁️",    # Overcast
        45: "🌫️",   # Fog
        48: "🌫️",   # Depositing rime fog
        51: "🌦️",   # Light drizzle
        53: "🌦️",   # Moderate drizzle
        55: "🌧️",   # Dense drizzle
        56: "🌧️",   # Freezing drizzle light
        57: "🌧️",   # Freezing drizzle dense
        61: "🌧️",   # Slight rain
        63: "🌧️",   # Moderate rain
        65: "🌧️",   # Heavy rain
        66: "🌧️",   # Freezing rain light
        67: "🌧️",   # Freezing rain heavy
        71: "🌨️",   # Slight snow
        73: "🌨️",   # Moderate snow
        75: "❄️",   # Heavy snow
        77: "🌨️",   # Snow grains
        80: "🌦️",   # Slight rain showers
        81: "🌧️",   # Moderate rain showers
        82: "⛈️",   # Violent rain showers
        85: "🌨️",   # Slight snow showers
        86: "❄️",   # Heavy snow showers
        95: "⛈️",   # Thunderstorm
        96: "⛈️",   # Thunderstorm with slight hail
        99: "⛈️",   # Thunderstorm with heavy hail
    }
    
    def get_icon(self, weather_code: int) -> str:
        """Get emoji icon for weather code."""
        return self.WEATHER_ICONS.get(weather_code, "❓")
    
    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "emoji"


class WeatherIconProviderImpl:
    """
    Context class for weather icon strategies.
    
    Implements Strategy pattern for flexible icon display.
    """
    
    def __init__(self, strategy: WeatherIconStrategy):
        """Initialize with icon strategy."""
        self._strategy = strategy
        logger.info(f"WeatherIconProvider initialized with {strategy.get_strategy_name()} strategy")
    
    def set_strategy(self, strategy: WeatherIconStrategy) -> None:
        """Change icon strategy at runtime."""
        old_strategy = self._strategy.get_strategy_name()
        self._strategy = strategy
        logger.info(f"Icon strategy changed from {old_strategy} to {strategy.get_strategy_name()}")
    
    def get_weather_icon(self, weather_code: int) -> str:
        """Get weather icon using current strategy."""
        return self._strategy.get_icon(weather_code)
    
    def get_current_strategy_name(self) -> str:
        """Get name of current strategy."""
        return self._strategy.get_strategy_name()


class WeatherDataValidator:
    """
    Validator for weather data integrity.
    
    Follows Single Responsibility Principle - only responsible for validation.
    """
    
    @staticmethod
    def validate_temperature(temperature: float) -> bool:
        """Validate temperature is within reasonable range."""
        return -100.0 <= temperature <= 60.0  # Celsius
    
    @staticmethod
    def validate_humidity(humidity: int) -> bool:
        """Validate humidity percentage."""
        return 0 <= humidity <= 100
    
    @staticmethod
    def validate_weather_code(weather_code: int) -> bool:
        """Validate WMO weather code."""
        valid_codes = {code.value for code in WeatherCode}
        return weather_code in valid_codes
    
    @staticmethod
    def validate_timestamp(timestamp: datetime) -> bool:
        """Validate timestamp is reasonable."""
        now = datetime.now()
        # Allow data from 1 day ago to 7 days in future
        return (now - timedelta(days=1)) <= timestamp <= (now + timedelta(days=7))
    
    @classmethod
    def validate_weather_data(cls, weather_data: WeatherData) -> bool:
        """Validate complete weather data object."""
        return (
            cls.validate_temperature(weather_data.temperature) and
            cls.validate_humidity(weather_data.humidity) and
            cls.validate_weather_code(weather_data.weather_code) and
            cls.validate_timestamp(weather_data.timestamp)
        )
    
    @classmethod
    def validate_forecast_data(cls, forecast_data: WeatherForecastData) -> bool:
        """Validate complete forecast data."""
        # Validate all hourly data
        for weather in forecast_data.hourly_forecast:
            if not cls.validate_weather_data(weather):
                return False
        
        # Validate all daily data
        for weather in forecast_data.daily_forecast:
            if not cls.validate_weather_data(weather):
                return False
        
        return True


# Default weather icon provider instance
default_weather_icon_provider = WeatherIconProviderImpl(EmojiWeatherIconStrategy())