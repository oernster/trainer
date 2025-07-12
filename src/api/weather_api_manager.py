"""
Weather API manager for fetching weather data from Open-Meteo API.
Author: Oliver Ernster

This module handles all communication with the Open-Meteo API,
following solid Object-Oriented design principles with proper
abstraction, error handling, and caching.
"""

import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from version import (
    __weather_version__,
    __weather_api_provider__,
    __weather_api_url__,
    get_weather_info,
)
from ..models.weather_data import (
    WeatherData,
    WeatherForecastData,
    Location,
    WeatherDataValidator,
)
from ..managers.weather_config import WeatherConfig

logger = logging.getLogger(__name__)


class WeatherAPIException(Exception):
    """Base exception for weather API-related errors."""

    pass


class WeatherNetworkException(WeatherAPIException):
    """Exception for network-related errors."""

    pass


class WeatherDataException(WeatherAPIException):
    """Exception for weather data processing errors."""

    pass


class WeatherRateLimitException(WeatherAPIException):
    """Exception for rate limit exceeded errors."""

    pass


@dataclass
class WeatherAPIResponse:
    """Container for raw weather API response data."""

    status_code: int
    data: Dict
    timestamp: datetime
    source: str


class WeatherDataSource(ABC):
    """
    Abstract base class for weather data sources.

    Follows Open/Closed Principle - open for extension, closed for modification.
    """

    @abstractmethod
    async def fetch_weather_data(self, location: Location) -> WeatherForecastData:
        """Fetch weather data from source."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of the weather data source."""
        pass

    @abstractmethod
    def get_source_url(self) -> str:
        """Get the base URL of the weather data source."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the weather data source and cleanup resources."""
        pass

    @abstractmethod
    def shutdown_sync(self) -> None:
        """Shutdown the weather data source synchronously."""
        pass


class HTTPClient(ABC):
    """Abstract HTTP client interface for dependency injection."""

    @abstractmethod
    async def get(self, url: str, params: Dict) -> WeatherAPIResponse:
        """Make HTTP GET request."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close HTTP client."""
        pass

    @abstractmethod
    def close_sync(self) -> None:
        """Close HTTP client synchronously."""
        pass


class AioHttpClient(HTTPClient):
    """
    Concrete HTTP client implementation using aiohttp.

    Follows Dependency Inversion Principle - implements abstraction.
    """

    def __init__(self, timeout_seconds: int = 10):
        """Initialize HTTP client with timeout."""
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is created."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"User-Agent": f"Trainer/{__weather_version__}"},
            )
        return self._session

    async def get(self, url: str, params: Dict) -> WeatherAPIResponse:
        """Make HTTP GET request."""
        session = await self._ensure_session()

        try:
            async with session.get(url, params=params) as response:
                data = await response.json()
                return WeatherAPIResponse(
                    status_code=response.status,
                    data=data,
                    timestamp=datetime.now(),
                    source=__weather_api_provider__,
                )
        except aiohttp.ClientError as e:
            raise WeatherNetworkException(f"Network error: {e}")
        except Exception as e:
            raise WeatherAPIException(f"HTTP request failed: {e}")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._session and not self._session.closed:
            await self._session.close()

    def close_sync(self) -> None:
        """Close HTTP client synchronously (for shutdown)."""
        if self._session and not self._session.closed:
            try:
                # Create a new event loop to properly close the session
                import asyncio

                try:
                    # Try to get the current event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, schedule the close for later
                        loop.create_task(self._session.close())
                    else:
                        # If loop is not running, run the close operation
                        loop.run_until_complete(self._session.close())
                except RuntimeError:
                    # No event loop available, create a new one
                    asyncio.run(self._session.close())

                self._session = None
                logger.debug("HTTP client session closed properly")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
                # Fallback: just detach the session
                self._session = None


class OpenMeteoWeatherSource(WeatherDataSource):
    """
    Open-Meteo API weather data source implementation.

    Follows Single Responsibility Principle - only responsible for
    Open-Meteo API communication and data parsing.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, http_client: HTTPClient, config: WeatherConfig):
        """Initialize with HTTP client and configuration."""
        self._http_client = http_client
        self._config = config
        self._validator = WeatherDataValidator()
        logger.debug(f"OpenMeteoWeatherSource initialized for {config.location_name}")

    def get_source_name(self) -> str:
        """Get source name."""
        return __weather_api_provider__

    def get_source_url(self) -> str:
        """Get source URL."""
        return __weather_api_url__

    async def fetch_weather_data(self, location: Location) -> WeatherForecastData:
        """
        Fetch weather data from Open-Meteo API.

        Args:
            location: Location to fetch weather for

        Returns:
            WeatherForecastData: Complete weather forecast

        Raises:
            WeatherAPIException: For API-related errors
        """
        params = self._build_api_params(location)

        try:
            response = await self._http_client.get(self.BASE_URL, params)

            if response.status_code != 200:
                raise WeatherAPIException(f"API returned status {response.status_code}")

            return self._parse_api_response(response.data, location)

        except WeatherAPIException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            raise WeatherAPIException(f"Weather data fetch failed: {e}")

    def _build_api_params(self, location: Location) -> Dict:
        """Build API request parameters."""
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "hourly": "temperature_2m,relative_humidity_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": "Europe/London",
            "forecast_days": 7,
        }

    def _parse_api_response(
        self, data: Dict, location: Location
    ) -> WeatherForecastData:
        """
        Parse Open-Meteo API response into WeatherForecastData.

        Args:
            data: Raw API response data
            location: Location for the forecast

        Returns:
            WeatherForecastData: Parsed weather forecast
        """
        try:
            hourly_data = self._parse_hourly_data(data.get("hourly", {}))
            daily_data = self._parse_daily_data(data.get("daily", {}))

            # Filter hourly data to 3-hourly intervals
            filtered_hourly = self._filter_to_3hourly(hourly_data)

            forecast = WeatherForecastData(
                location=location,
                hourly_forecast=filtered_hourly,
                daily_forecast=daily_data,
                last_updated=datetime.now(),
                data_version=__weather_version__,
            )

            # Validate the forecast data
            if not self._validator.validate_forecast_data(forecast):
                raise WeatherDataException("Invalid weather data received")

            logger.info(
                f"Parsed weather data: {len(filtered_hourly)} hourly, "
                f"{len(daily_data)} daily forecasts"
            )

            return forecast

        except Exception as e:
            logger.error(f"Failed to parse weather data: {e}")
            raise WeatherDataException(f"Weather data parsing failed: {e}")

    def _parse_hourly_data(self, hourly_data: Dict) -> List[WeatherData]:
        """Parse hourly weather data."""
        if not hourly_data:
            return []

        times = hourly_data.get("time", [])
        temperatures = hourly_data.get("temperature_2m", [])
        humidities = hourly_data.get("relative_humidity_2m", [])
        weather_codes = hourly_data.get("weather_code", [])

        weather_list = []

        for i, time_str in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

                # Skip if we don't have all required data
                if (
                    i >= len(temperatures)
                    or i >= len(humidities)
                    or i >= len(weather_codes)
                ):
                    continue

                weather = WeatherData(
                    timestamp=timestamp,
                    temperature=float(temperatures[i]),
                    humidity=int(humidities[i]),
                    weather_code=int(weather_codes[i]),
                    description=self._get_weather_description(weather_codes[i]),
                )

                if self._validator.validate_weather_data(weather):
                    weather_list.append(weather)

            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid hourly data point {i}: {e}")
                continue

        return weather_list

    def _parse_daily_data(self, daily_data: Dict) -> List[WeatherData]:
        """Parse daily weather data."""
        if not daily_data:
            return []

        times = daily_data.get("time", [])
        max_temps = daily_data.get("temperature_2m_max", [])
        min_temps = daily_data.get("temperature_2m_min", [])
        weather_codes = daily_data.get("weather_code", [])

        weather_list = []

        for i, time_str in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(time_str)

                # Skip if we don't have all required data
                if (
                    i >= len(max_temps)
                    or i >= len(min_temps)
                    or i >= len(weather_codes)
                ):
                    continue

                # Use average of min/max for daily temperature
                avg_temp = (float(max_temps[i]) + float(min_temps[i])) / 2

                weather = WeatherData(
                    timestamp=timestamp,
                    temperature=avg_temp,
                    humidity=50,  # Default humidity for daily data
                    weather_code=int(weather_codes[i]),
                    description=self._get_weather_description(weather_codes[i]),
                )

                if self._validator.validate_weather_data(weather):
                    weather_list.append(weather)

            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid daily data point {i}: {e}")
                continue

        return weather_list

    def _filter_to_3hourly(self, hourly_data: List[WeatherData]) -> List[WeatherData]:
        """Filter hourly data to 3-hourly intervals."""
        if not hourly_data:
            return []

        # Take every 3rd hour starting from the first
        return [weather for i, weather in enumerate(hourly_data) if i % 3 == 0]

    def _get_weather_description(self, weather_code: int) -> str:
        """Get human-readable weather description."""
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail",
        }
        return descriptions.get(weather_code, "Unknown")

    async def shutdown(self) -> None:
        """Shutdown the weather data source and cleanup resources."""
        await self._http_client.close()
        logger.info("OpenMeteoWeatherSource shutdown complete")

    def shutdown_sync(self) -> None:
        """Shutdown the weather data source synchronously."""
        if hasattr(self._http_client, "close_sync"):
            self._http_client.close_sync()
        logger.debug("OpenMeteoWeatherSource synchronous shutdown complete")


class WeatherAPIManager:
    """
    High-level weather API manager.

    Follows Dependency Inversion Principle - depends on abstractions,
    not concrete implementations.
    """

    def __init__(self, weather_source: WeatherDataSource, config: WeatherConfig):
        """
        Initialize weather API manager.

        Args:
            weather_source: Weather data source implementation
            config: Weather configuration
        """
        self._weather_source = weather_source
        self._config = config
        self._last_fetch_time: Optional[datetime] = None
        self._cached_data: Optional[WeatherForecastData] = None
        logger.info(
            f"WeatherAPIManager initialized with {weather_source.get_source_name()}"
        )

    async def get_weather_forecast(
        self, location: Optional[Location] = None
    ) -> WeatherForecastData:
        """
        Get weather forecast for location.

        Args:
            location: Location to get forecast for (uses config location if None)

        Returns:
            WeatherForecastData: Weather forecast data
        """
        if location is None:
            location = Location(
                name=self._config.location_name,
                latitude=self._config.location_latitude,
                longitude=self._config.location_longitude,
            )

        # Check cache first
        if self._is_cache_valid() and self._cached_data is not None:
            logger.info("Returning cached weather data")
            return self._cached_data

        # Fetch fresh data
        try:
            forecast_data = await self._weather_source.fetch_weather_data(location)

            # Update cache
            self._cached_data = forecast_data
            self._last_fetch_time = datetime.now()

            logger.debug(f"Fetched fresh weather data for {location.name}")
            return forecast_data

        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")

            # Return cached data if available, even if stale
            if self._cached_data is not None:
                logger.warning("Returning stale cached data due to fetch failure")
                return self._cached_data

            # No cached data available, re-raise the exception
            raise

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self._cached_data or not self._last_fetch_time:
            return False

        cache_age = datetime.now() - self._last_fetch_time
        cache_duration = timedelta(seconds=self._config.get_cache_duration_seconds())

        return cache_age < cache_duration

    def clear_cache(self) -> None:
        """Clear cached weather data."""
        self._cached_data = None
        self._last_fetch_time = None
        logger.debug("Weather cache cleared")

    def get_cache_info(self) -> Dict:
        """Get information about current cache state."""
        return {
            "has_cached_data": self._cached_data is not None,
            "last_fetch_time": self._last_fetch_time,
            "cache_valid": self._is_cache_valid(),
            "cache_duration_seconds": self._config.get_cache_duration_seconds(),
        }

    async def shutdown(self) -> None:
        """Shutdown the weather API manager and cleanup resources."""
        # Shutdown the weather source
        await self._weather_source.shutdown()

        # Clear cache
        self.clear_cache()
        logger.info("WeatherAPIManager shutdown complete")

    def shutdown_sync(self) -> None:
        """Shutdown the weather API manager synchronously."""
        # Shutdown the weather source synchronously
        if hasattr(self._weather_source, "shutdown_sync"):
            self._weather_source.shutdown_sync()

        # Clear cache
        self.clear_cache()
        logger.debug("WeatherAPIManager synchronous shutdown complete")


class WeatherAPIFactory:
    """
    Factory for creating weather API managers.

    Implements Factory pattern for easy instantiation.
    """

    @staticmethod
    def create_openmeteo_manager(config: WeatherConfig) -> WeatherAPIManager:
        """Create weather manager using Open-Meteo API."""
        http_client = AioHttpClient(timeout_seconds=config.timeout_seconds)
        weather_source = OpenMeteoWeatherSource(http_client, config)
        return WeatherAPIManager(weather_source, config)

    @staticmethod
    def create_manager_from_config(config: WeatherConfig) -> WeatherAPIManager:
        """Create weather manager based on configuration."""
        # For now, only Open-Meteo is supported
        # This can be extended to support multiple providers
        return WeatherAPIFactory.create_openmeteo_manager(config)
