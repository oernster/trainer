"""
NASA API manager for fetching astronomy data from NASA APIs.
Author: Oliver Ernster

This module handles all communication with NASA APIs,
following solid Object-Oriented design principles with proper
abstraction, error handling, caching, and rate limiting.
"""

import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from urllib.parse import urljoin
import json

from version import __version__
from ..models.astronomy_data import (
    AstronomyData,
    AstronomyForecastData,
    AstronomyEvent,
    AstronomyEventType,
    AstronomyEventPriority,
    MoonPhase,
    Location,
    AstronomyDataValidator,
)
from ..managers.astronomy_config import AstronomyConfig

logger = logging.getLogger(__name__)


class AstronomyAPIException(Exception):
    """Base exception for astronomy API-related errors."""

    pass


class AstronomyNetworkException(AstronomyAPIException):
    """Exception for network-related errors."""

    pass


class AstronomyDataException(AstronomyAPIException):
    """Exception for astronomy data processing errors."""

    pass


class AstronomyRateLimitException(AstronomyAPIException):
    """Exception for rate limit exceeded errors."""

    pass


class AstronomyAuthenticationException(AstronomyAPIException):
    """Exception for API authentication errors."""

    pass


@dataclass
class AstronomyAPIResponse:
    """Container for raw astronomy API response data."""

    status_code: int
    data: Union[Dict[str, Any], List[Any]]
    timestamp: datetime
    source: str
    url: str


class HTTPClient(ABC):
    """Abstract HTTP client interface for dependency injection."""

    @abstractmethod
    async def get(self, url: str, params: Dict[str, Any]) -> AstronomyAPIResponse:
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

    def __init__(self, timeout_seconds: int = 15):
        """Initialize HTTP client with timeout."""
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is created."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout, headers={"User-Agent": f"Trainer/{__version__}"}
            )
        return self._session

    async def get(self, url: str, params: Dict[str, Any]) -> AstronomyAPIResponse:
        """Make HTTP GET request."""
        session = await self._ensure_session()

        try:
            async with session.get(url, params=params) as response:
                data = await response.json()
                return AstronomyAPIResponse(
                    status_code=response.status,
                    data=data,
                    timestamp=datetime.now(),
                    source="NASA",
                    url=str(response.url),
                )
        except aiohttp.ClientError as e:
            raise AstronomyNetworkException(f"Network error: {e}")
        except json.JSONDecodeError as e:
            raise AstronomyDataException(f"Invalid JSON response: {e}")
        except Exception as e:
            raise AstronomyAPIException(f"HTTP request failed: {e}")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._session and not self._session.closed:
            await self._session.close()

    def close_sync(self) -> None:
        """Close HTTP client synchronously."""
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


class AstronomyDataSource(ABC):
    """
    Abstract base class for astronomy data sources.

    Follows Open/Closed Principle - open for extension, closed for modification.
    """

    @abstractmethod
    async def fetch_astronomy_data(
        self, location: Location, days: int
    ) -> AstronomyForecastData:
        """Fetch astronomy data from source."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of the astronomy data source."""
        pass

    @abstractmethod
    def get_source_url(self) -> str:
        """Get the base URL of the astronomy data source."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the astronomy data source and cleanup resources."""
        pass

    @abstractmethod
    def shutdown_sync(self) -> None:
        """Shutdown the astronomy data source synchronously."""
        pass


class AstronomyService(ABC):
    """Abstract base class for individual NASA API services."""

    def __init__(self, http_client: HTTPClient, config: AstronomyConfig):
        self._http_client = http_client
        self._config = config

    @abstractmethod
    async def fetch_events(
        self, location: Location, start_date: date, end_date: date
    ) -> List[AstronomyEvent]:
        """Fetch astronomy events for date range."""
        pass

    @abstractmethod
    def get_service_name(self) -> str:
        """Get service name."""
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """Get service base URL."""
        pass


class APODService(AstronomyService):
    """
    Astronomy Picture of the Day service.

    Follows Single Responsibility Principle - only responsible for APOD API.
    """

    BASE_URL = "https://api.nasa.gov/planetary/apod"

    def get_service_name(self) -> str:
        return "APOD"

    def get_base_url(self) -> str:
        return self.BASE_URL

    async def fetch_events(
        self, location: Location, start_date: date, end_date: date
    ) -> List[AstronomyEvent]:
        """Fetch APOD events for date range using batch API call."""
        try:
            # Use the more efficient batch API call with start_date and end_date
            apod_data_list = await self._fetch_apod_batch(start_date, end_date)
            events = []

            for apod_data in apod_data_list:
                if apod_data and isinstance(apod_data, dict):
                    # Parse the date from the API response
                    date_str = apod_data.get("date")
                    if date_str:
                        try:
                            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            event = self._parse_apod_response(apod_data, event_date)
                            if event:
                                events.append(event)
                        except ValueError as e:
                            logger.warning(
                                f"Invalid date format in APOD response: {date_str}"
                            )

            logger.info(
                f"APOD service fetched {len(events)} events for date range {start_date} to {end_date}"
            )
            return events

        except Exception as e:
            logger.error(f"Failed to fetch APOD batch data: {e}")
            return []

    async def _fetch_apod_batch(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch APOD data for date range using batch API."""
        # Limit the date range to avoid too many requests and ensure we have data
        # APOD started June 16, 1995, and may not have data for every day
        earliest_date = date(1995, 6, 16)  # APOD start date
        today = date.today()

        # Adjust dates to valid range
        actual_start = max(start_date, earliest_date)
        actual_end = min(end_date, today)

        # If the date range is invalid, return empty list
        if actual_start > actual_end:
            logger.info(
                f"No APOD data available for date range {start_date} to {end_date}"
            )
            return []

        # Limit to maximum 7 days to avoid overwhelming the API
        if (actual_end - actual_start).days > 6:
            actual_end = actual_start + timedelta(days=6)

        params = {
            "api_key": self._config.nasa_api_key,
            "start_date": actual_start.strftime("%Y-%m-%d"),
            "end_date": actual_end.strftime("%Y-%m-%d"),
            "hd": "true",
        }

        try:
            response = await self._http_client.get(self.BASE_URL, params)

            if response.status_code == 200:
                if isinstance(response.data, list):
                    logger.debug(f"APOD batch API returned {len(response.data)} items")
                    return response.data
                elif isinstance(response.data, dict):
                    # Single item response
                    return [response.data]
                else:
                    logger.warning(
                        f"APOD API returned unexpected data type: {type(response.data)}"
                    )
                    return []
            elif response.status_code == 403:
                raise AstronomyAuthenticationException("Invalid NASA API key")
            elif response.status_code == 429:
                raise AstronomyRateLimitException("NASA API rate limit exceeded")
            elif response.status_code == 400:
                logger.warning(
                    f"APOD API returned 400 for date range {actual_start} to {actual_end} - likely no data available"
                )
                return []
            else:
                logger.warning(f"APOD API returned status {response.status_code}")
                return []

        except AstronomyAPIException:
            raise
        except Exception as e:
            logger.error(f"Error fetching APOD batch: {e}")
            return []

    def _parse_apod_response(
        self, data: Dict[str, Any], target_date: date
    ) -> AstronomyEvent:
        """Parse APOD API response into AstronomyEvent."""
        title = data.get("title", "Astronomy Picture of the Day")
        explanation = data.get("explanation", "No description available")
        image_url = data.get("hdurl") or data.get("url")

        # Create event for noon of the target date
        event_time = datetime.combine(target_date, datetime.min.time().replace(hour=12))

        return AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title=title,
            description=explanation,
            start_time=event_time,
            end_time=None,
            visibility_info=None,
            nasa_url=f"https://apod.nasa.gov/apod/ap{target_date.strftime('%y%m%d')}.html",
            image_url=image_url,
            priority=AstronomyEventPriority.MEDIUM,
            metadata={
                "media_type": data.get("media_type", "image"),
                "copyright": data.get("copyright"),
                "date": data.get("date"),
            },
        )


class ISSService(AstronomyService):
    """
    International Space Station tracking service.

    Uses Open Notify API for ISS pass predictions.
    """

    BASE_URL = "http://api.open-notify.org/iss-pass.json"

    def get_service_name(self) -> str:
        return "ISS"

    def get_base_url(self) -> str:
        return self.BASE_URL

    async def fetch_events(
        self, location: Location, start_date: date, end_date: date
    ) -> List[AstronomyEvent]:
        """Fetch ISS pass events for date range."""
        try:
            passes = await self._fetch_iss_passes(location)
            events = []

            if not passes:
                logger.info(
                    "No ISS pass data available - service may be temporarily unavailable"
                )
                return []

            for pass_data in passes:
                try:
                    pass_time = datetime.fromtimestamp(pass_data["risetime"])
                    pass_date = pass_time.date()

                    # Only include passes within our date range
                    if start_date <= pass_date <= end_date:
                        event = self._create_iss_event(pass_data, location)
                        events.append(event)
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Invalid ISS pass data: {e}")
                    continue

            logger.info(
                f"ISS service fetched {len(events)} events for date range {start_date} to {end_date}"
            )
            return events

        except Exception as e:
            logger.error(f"Error fetching ISS passes: {e}")
            return []

    async def _fetch_iss_passes(self, location: Location) -> List[Dict[str, Any]]:
        """Fetch ISS pass predictions."""
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "n": 10,  # Number of passes to fetch
        }

        try:
            response = await self._http_client.get(self.BASE_URL, params)

            if response.status_code == 200:
                if isinstance(response.data, dict):
                    return response.data.get("response", [])
                else:
                    logger.warning(
                        f"ISS API returned unexpected data type: {type(response.data)}"
                    )
                    return []
            elif response.status_code == 404:
                logger.warning(
                    "ISS API endpoint not found (404) - service may be temporarily unavailable"
                )
                return []
            else:
                logger.warning(f"ISS API returned status {response.status_code}")
                return []
        except AstronomyNetworkException as e:
            # Handle network errors gracefully
            if "404" in str(e) or "text/html" in str(e):
                logger.warning(
                    "ISS API service appears to be unavailable - skipping ISS data"
                )
                return []
            else:
                logger.error(f"Network error fetching ISS data: {e}")
                return []
        except Exception as e:
            logger.error(f"Unexpected error fetching ISS data: {e}")
            return []

    def _create_iss_event(
        self, pass_data: Dict[str, Any], location: Location
    ) -> AstronomyEvent:
        """Create ISS pass event from API data."""
        rise_time = datetime.fromtimestamp(pass_data["risetime"])
        duration = pass_data["duration"]
        end_time = rise_time + timedelta(seconds=duration)

        # Determine visibility
        visibility = (
            "Visible pass" if duration > 300 else "Brief pass"
        )  # 5+ minutes = good visibility

        return AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="International Space Station Pass",
            description=f"The ISS will pass over {location.name} for {duration} seconds",
            start_time=rise_time,
            end_time=end_time,
            visibility_info=visibility,
            nasa_url="https://spotthestation.nasa.gov/",
            image_url=None,
            priority=(
                AstronomyEventPriority.HIGH
                if duration > 300
                else AstronomyEventPriority.MEDIUM
            ),
            metadata={"duration_seconds": duration, "location": location.name},
        )


class NeoWsService(AstronomyService):
    """
    Near Earth Object Web Service.

    Provides data on asteroids and comets approaching Earth.
    """

    BASE_URL = "https://api.nasa.gov/neo/rest/v1/feed"

    def get_service_name(self) -> str:
        return "NeoWs"

    def get_base_url(self) -> str:
        return self.BASE_URL

    async def fetch_events(
        self, location: Location, start_date: date, end_date: date
    ) -> List[AstronomyEvent]:
        """Fetch Near Earth Object events for date range."""
        try:
            # NeoWs API has a 7-day limit per request, so respect that
            actual_end = min(end_date, start_date + timedelta(days=6))

            neo_data = await self._fetch_neo_data(start_date, actual_end)
            events = []

            for date_str, objects in neo_data.items():
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    # Filter for potentially hazardous or interesting objects
                    interesting_objects = [
                        obj
                        for obj in objects
                        if obj.get("is_potentially_hazardous_asteroid", False)
                        or self._get_max_diameter(obj) > 100
                    ]

                    if interesting_objects:
                        event = self._create_neo_event(interesting_objects, event_date)
                        events.append(event)

                except ValueError as e:
                    logger.warning(f"Invalid date format in NeoWs response: {date_str}")
                    continue

            logger.info(
                f"NeoWs service fetched {len(events)} events for date range {start_date} to {actual_end}"
            )
            return events

        except Exception as e:
            logger.error(f"Error fetching NEO data: {e}")
            return []

    def _get_max_diameter(self, obj: Dict[str, Any]) -> float:
        """Safely extract maximum diameter from NEO object."""
        try:
            return float(
                obj.get("estimated_diameter", {})
                .get("meters", {})
                .get("estimated_diameter_max", 0)
            )
        except (ValueError, TypeError):
            return 0.0

    async def _fetch_neo_data(
        self, start_date: date, end_date: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch Near Earth Object data for date range."""
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "api_key": self._config.nasa_api_key,
        }

        response = await self._http_client.get(self.BASE_URL, params)

        if response.status_code == 200:
            if isinstance(response.data, dict):
                return response.data.get("near_earth_objects", {})
            else:
                logger.warning(
                    f"NeoWs API returned unexpected data type: {type(response.data)}"
                )
                return {}
        elif response.status_code == 403:
            raise AstronomyAuthenticationException("Invalid NASA API key")
        elif response.status_code == 429:
            raise AstronomyRateLimitException("NASA API rate limit exceeded")
        else:
            raise AstronomyAPIException(
                f"NeoWs API returned status {response.status_code}"
            )

    def _create_neo_event(
        self, objects: List[Dict[str, Any]], event_date: date
    ) -> AstronomyEvent:
        """Create Near Earth Object event from API data."""
        object_count = len(objects)
        hazardous_count = sum(
            1 for obj in objects if obj.get("is_potentially_hazardous_asteroid", False)
        )

        if hazardous_count > 0:
            title = f"{hazardous_count} Potentially Hazardous Asteroid{'s' if hazardous_count != 1 else ''}"
            priority = AstronomyEventPriority.HIGH
        else:
            title = (
                f"{object_count} Near Earth Object{'s' if object_count != 1 else ''}"
            )
            priority = AstronomyEventPriority.LOW

        # Get the largest object for description
        largest_object = max(objects, key=lambda obj: self._get_max_diameter(obj))

        largest_name = largest_object.get("name", "Unknown")
        largest_size = self._get_max_diameter(largest_object)

        description = f"{object_count} near-Earth object{'s' if object_count != 1 else ''} approaching Earth. "
        description += f"Largest: {largest_name} (≤{largest_size:.0f}m diameter)"

        event_time = datetime.combine(event_date, datetime.min.time().replace(hour=12))

        return AstronomyEvent(
            event_type=AstronomyEventType.NEAR_EARTH_OBJECT,
            title=title,
            description=description,
            start_time=event_time,
            end_time=None,
            visibility_info="Not visible to naked eye",
            nasa_url="https://cneos.jpl.nasa.gov/",
            image_url=None,
            priority=priority,
            metadata={
                "object_count": object_count,
                "hazardous_count": hazardous_count,
                "largest_object": largest_name,
                "largest_size_meters": largest_size,
            },
        )


class EPICService(AstronomyService):
    """
    Earth Polychromatic Imaging Camera service.

    Provides Earth imagery from the DSCOVR satellite.
    """

    BASE_URL = "https://api.nasa.gov/EPIC/api/natural/images"

    def get_service_name(self) -> str:
        return "EPIC"

    def get_base_url(self) -> str:
        return self.BASE_URL

    async def fetch_events(
        self, location: Location, start_date: date, end_date: date
    ) -> List[AstronomyEvent]:
        """Fetch EPIC Earth imagery events for date range."""
        try:
            # EPIC has limited recent data availability, so we'll be more conservative
            events = []
            today = date.today()

            # EPIC data is typically available with a delay, so check recent dates
            # Start from a few days ago to increase chances of finding data
            check_start = max(start_date, today - timedelta(days=7))
            check_end = min(end_date, today - timedelta(days=1))  # Yesterday at most

            if check_start > check_end:
                logger.debug("No recent EPIC data available for requested date range")
                return []

            # Limit to 2 attempts to avoid excessive API calls
            attempts = 0
            current_date = check_end  # Start from most recent date

            while current_date >= check_start and len(events) < 2 and attempts < 3:
                epic_event = await self._fetch_epic_for_date(current_date)
                if epic_event:
                    events.append(epic_event)
                current_date -= timedelta(days=1)
                attempts += 1

            logger.info(
                f"EPIC service fetched {len(events)} events from {attempts} attempts"
            )
            return events

        except Exception as e:
            logger.error(f"Error fetching EPIC data: {e}")
            return []

    async def _fetch_epic_for_date(self, target_date: date) -> Optional[AstronomyEvent]:
        """Fetch EPIC image for a specific date."""
        params = {"api_key": self._config.nasa_api_key}

        # EPIC API uses date in URL path
        url = f"{self.BASE_URL}/{target_date.strftime('%Y-%m-%d')}"

        try:
            response = await self._http_client.get(url, params)

            if response.status_code == 200 and response.data:
                # Handle list response from EPIC API
                if isinstance(response.data, list) and len(response.data) > 0:
                    first_image = response.data[0]
                    if isinstance(first_image, dict):
                        return self._create_epic_event(first_image, target_date)
            return None

        except Exception as e:
            logger.warning(f"Failed to fetch EPIC for {target_date}: {e}")
            return None

    def _create_epic_event(
        self, image_data: Dict[str, Any], target_date: date
    ) -> AstronomyEvent:
        """Create EPIC event from API data."""
        image_name = image_data.get("image", "")
        caption = image_data.get("caption", "Earth from space")

        # Construct image URL
        date_str = target_date.strftime("%Y/%m/%d")
        image_url = (
            f"https://api.nasa.gov/EPIC/archive/natural/{date_str}/png/{image_name}.png"
        )

        event_time = datetime.combine(target_date, datetime.min.time().replace(hour=12))

        return AstronomyEvent(
            event_type=AstronomyEventType.SATELLITE_IMAGE,
            title="Earth from DSCOVR Satellite",
            description=f"Daily Earth imagery from the DSCOVR satellite. {caption}",
            start_time=event_time,
            end_time=None,
            visibility_info=None,
            nasa_url="https://epic.gsfc.nasa.gov/",
            image_url=image_url,
            priority=AstronomyEventPriority.LOW,
            metadata={
                "image_name": image_name,
                "caption": caption,
                "satellite": "DSCOVR",
            },
        )


class NASAAstronomySource(AstronomyDataSource):
    """
    NASA API astronomy data source implementation.

    Follows Single Responsibility Principle - only responsible for
    NASA API communication and data aggregation.
    """

    def __init__(self, http_client: HTTPClient, config: AstronomyConfig):
        """Initialize with HTTP client and configuration."""
        self._http_client = http_client
        self._config = config
        self._validator = AstronomyDataValidator()

        # Initialize services based on configuration
        self._services: Dict[str, AstronomyService] = {}
        if config.services.apod:
            self._services["apod"] = APODService(http_client, config)
        if config.services.iss:
            self._services["iss"] = ISSService(http_client, config)
        if config.services.neows:
            self._services["neows"] = NeoWsService(http_client, config)
        if config.services.epic:
            self._services["epic"] = EPICService(http_client, config)

        logger.info(
            f"NASAAstronomySource initialized with {len(self._services)} services"
        )

    def get_source_name(self) -> str:
        """Get source name."""
        return "NASA"

    def get_source_url(self) -> str:
        """Get source URL."""
        return "https://api.nasa.gov/"

    async def fetch_astronomy_data(
        self, location: Location, days: int
    ) -> AstronomyForecastData:
        """
        Fetch astronomy data from NASA APIs.

        Args:
            location: Location to fetch astronomy for
            days: Number of days to forecast

        Returns:
            AstronomyForecastData: Complete astronomy forecast

        Raises:
            AstronomyAPIException: For API-related errors
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=days - 1)

        try:
            # Fetch data from all enabled services concurrently
            tasks = []
            for service_name, service in self._services.items():
                task = self._fetch_service_data(service, location, start_date, end_date)
                tasks.append((service_name, task))

            # Wait for all services to complete
            service_results = {}
            for service_name, task in tasks:
                try:
                    events = await task
                    service_results[service_name] = events
                    logger.info(f"{service_name} service returned {len(events)} events")
                except Exception as e:
                    logger.error(f"Error fetching {service_name} data: {e}")
                    service_results[service_name] = []

            # Combine results into daily astronomy data
            daily_astronomy = self._combine_service_results(
                service_results, start_date, end_date
            )

            forecast = AstronomyForecastData(
                location=location,
                daily_astronomy=daily_astronomy,
                last_updated=datetime.now(),
                data_source="NASA",
                forecast_days=days,
            )

            # Validate the forecast data
            if not self._validator.validate_astronomy_forecast(forecast):
                raise AstronomyDataException("Invalid astronomy data received")

            logger.info(
                f"Parsed astronomy data: {len(daily_astronomy)} days, "
                f"{sum(data.event_count for data in daily_astronomy)} total events"
            )

            return forecast

        except Exception as e:
            logger.error(f"Failed to fetch astronomy data: {e}")
            raise AstronomyAPIException(f"Astronomy data fetch failed: {e}")

    async def _fetch_service_data(
        self,
        service: AstronomyService,
        location: Location,
        start_date: date,
        end_date: date,
    ) -> List[AstronomyEvent]:
        """Fetch data from a single service with error handling."""
        try:
            return await service.fetch_events(location, start_date, end_date)
        except Exception as e:
            logger.error(f"Error in {service.get_service_name()} service: {e}")
            return []

    def _combine_service_results(
        self,
        service_results: Dict[str, List[AstronomyEvent]],
        start_date: date,
        end_date: date,
    ) -> List[AstronomyData]:
        """Combine results from all services into daily astronomy data."""
        daily_astronomy = []
        current_date = start_date

        while current_date <= end_date:
            # Collect all events for this date
            daily_events = []
            for service_name, events in service_results.items():
                for event in events:
                    if event.start_time.date() == current_date:
                        daily_events.append(event)

            # Sort events by priority and time
            daily_events.sort(
                key=lambda e: (e.priority.value, e.start_time), reverse=True
            )

            # Determine primary event (highest priority, earliest time)
            primary_event = daily_events[0] if daily_events else None

            # Create daily astronomy data
            astronomy_data = AstronomyData(
                date=current_date,
                events=daily_events,
                primary_event=primary_event,
                moon_phase=self._calculate_moon_phase(
                    current_date
                ),  # Simplified calculation
                moon_illumination=self._calculate_moon_illumination(
                    current_date
                ),  # Simplified calculation
            )

            daily_astronomy.append(astronomy_data)
            current_date += timedelta(days=1)

        return daily_astronomy

    def _calculate_moon_phase(self, target_date: date) -> MoonPhase:
        """Calculate moon phase for a given date (simplified calculation)."""
        # This is a simplified calculation - in a real implementation,
        # you would use a proper astronomical library like ephem or skyfield

        # Use a known new moon date and calculate days since
        known_new_moon = date(2024, 1, 11)  # Known new moon date
        days_since = (target_date - known_new_moon).days
        lunar_cycle = 29.53  # Average lunar cycle length

        phase_position = (days_since % lunar_cycle) / lunar_cycle

        if phase_position < 0.0625:
            return MoonPhase.NEW_MOON
        elif phase_position < 0.1875:
            return MoonPhase.WAXING_CRESCENT
        elif phase_position < 0.3125:
            return MoonPhase.FIRST_QUARTER
        elif phase_position < 0.4375:
            return MoonPhase.WAXING_GIBBOUS
        elif phase_position < 0.5625:
            return MoonPhase.FULL_MOON
        elif phase_position < 0.6875:
            return MoonPhase.WANING_GIBBOUS
        elif phase_position < 0.8125:
            return MoonPhase.LAST_QUARTER
        else:
            return MoonPhase.WANING_CRESCENT

    def _calculate_moon_illumination(self, target_date: date) -> float:
        """Calculate moon illumination percentage (simplified calculation)."""
        # Simplified calculation based on moon phase
        known_new_moon = date(2024, 1, 11)
        days_since = (target_date - known_new_moon).days
        lunar_cycle = 29.53

        phase_position = (days_since % lunar_cycle) / lunar_cycle

        # Calculate illumination based on phase position
        if phase_position <= 0.5:
            # Waxing: 0% to 100%
            return phase_position * 2
        else:
            # Waning: 100% to 0%
            return 2 * (1 - phase_position)

    async def shutdown(self) -> None:
        """Shutdown the astronomy data source and cleanup resources."""
        await self._http_client.close()
        logger.info("NASAAstronomySource shutdown complete")

    def shutdown_sync(self) -> None:
        """Shutdown the astronomy data source synchronously."""
        if hasattr(self._http_client, "close_sync"):
            self._http_client.close_sync()
        logger.debug("NASAAstronomySource synchronous shutdown complete")


class AstronomyAPIManager:
    """
    High-level astronomy API manager.

    Follows Dependency Inversion Principle - depends on abstractions,
    not concrete implementations.
    """

    def __init__(self, astronomy_source: AstronomyDataSource, config: AstronomyConfig):
        """
        Initialize astronomy API manager.

        Args:
            astronomy_source: Astronomy data source implementation
            config: Astronomy configuration
        """
        self._astronomy_source = astronomy_source
        self._config = config
        self._last_fetch_time: Optional[datetime] = None
        self._cached_data: Optional[AstronomyForecastData] = None
        logger.info(
            f"AstronomyAPIManager initialized with {astronomy_source.get_source_name()}"
        )

    async def get_astronomy_forecast(
        self, location: Optional[Location] = None, days: int = 7
    ) -> AstronomyForecastData:
        """
        Get astronomy forecast for location.

        Args:
            location: Location to get forecast for (uses config location if None)
            days: Number of days to forecast

        Returns:
            AstronomyForecastData: Astronomy forecast data
        """
        if location is None:
            location = Location(
                name=self._config.location_name,
                latitude=self._config.location_latitude,
                longitude=self._config.location_longitude,
                timezone=self._config.timezone,
            )

        # Check cache first
        if self._is_cache_valid() and self._cached_data is not None:
            logger.info("Returning cached astronomy data")
            return self._cached_data

        # Fetch fresh data
        try:
            forecast_data = await self._astronomy_source.fetch_astronomy_data(
                location, days
            )

            # Update cache
            self._cached_data = forecast_data
            self._last_fetch_time = datetime.now()

            logger.debug(f"Fetched fresh astronomy data for {location.name}")
            return forecast_data

        except Exception as e:
            logger.error(f"Failed to fetch astronomy data: {e}")

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
        """Clear cached astronomy data."""
        self._cached_data = None
        self._last_fetch_time = None
        logger.debug("Astronomy cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache state."""
        return {
            "has_cached_data": self._cached_data is not None,
            "last_fetch_time": self._last_fetch_time,
            "cache_valid": self._is_cache_valid(),
            "cache_duration_seconds": self._config.get_cache_duration_seconds(),
        }

    async def shutdown(self) -> None:
        """Shutdown the astronomy API manager and cleanup resources."""
        # Shutdown the astronomy source
        await self._astronomy_source.shutdown()

        # Clear cache
        self.clear_cache()
        logger.info("AstronomyAPIManager shutdown complete")

    def shutdown_sync(self) -> None:
        """Shutdown the astronomy API manager synchronously."""
        # Shutdown the astronomy source synchronously
        if hasattr(self._astronomy_source, "shutdown_sync"):
            self._astronomy_source.shutdown_sync()

        # Clear cache
        self.clear_cache()
        logger.debug("AstronomyAPIManager synchronous shutdown complete")


class AstronomyAPIFactory:
    """
    Factory for creating astronomy API managers.

    Implements Factory pattern for easy instantiation.
    """

    @staticmethod
    def create_nasa_manager(config: AstronomyConfig) -> AstronomyAPIManager:
        """Create astronomy manager using NASA APIs."""
        http_client = AioHttpClient(timeout_seconds=config.timeout_seconds)
        astronomy_source = NASAAstronomySource(http_client, config)
        return AstronomyAPIManager(astronomy_source, config)

    @staticmethod
    def create_manager_from_config(config: AstronomyConfig) -> AstronomyAPIManager:
        """Create astronomy manager based on configuration."""
        # For now, only NASA is supported
        # This can be extended to support multiple providers
        return AstronomyAPIFactory.create_nasa_manager(config)


# Rate limiting decorator
class RateLimitedAstronomySource:
    """
    Decorator adding rate limiting to astronomy data sources.

    Implements Decorator pattern for cross-cutting concerns.
    """

    def __init__(self, source: AstronomyDataSource, requests_per_hour: int = 1000):
        self._source = source
        self._requests_per_hour = requests_per_hour
        self._request_times: List[datetime] = []

    async def fetch_astronomy_data(
        self, location: Location, days: int
    ) -> AstronomyForecastData:
        """Fetch astronomy data with rate limiting."""
        await self._check_rate_limit()
        return await self._source.fetch_astronomy_data(location, days)

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        now = datetime.now()

        # Remove requests older than 1 hour
        cutoff_time = now - timedelta(hours=1)
        self._request_times = [t for t in self._request_times if t > cutoff_time]

        # Check if we're at the limit
        if len(self._request_times) >= self._requests_per_hour:
            oldest_request = min(self._request_times)
            wait_time = (oldest_request + timedelta(hours=1) - now).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)

        # Record this request
        self._request_times.append(now)

    def get_source_name(self) -> str:
        return f"RateLimited({self._source.get_source_name()})"

    def get_source_url(self) -> str:
        return self._source.get_source_url()

    async def shutdown(self) -> None:
        await self._source.shutdown()

    def shutdown_sync(self) -> None:
        self._source.shutdown_sync()


# Caching decorator
class CachedAstronomySource:
    """
    Decorator adding caching to astronomy data sources.

    Implements Decorator pattern for cross-cutting concerns.
    """

    def __init__(self, source: AstronomyDataSource, cache_duration_hours: int = 6):
        self._source = source
        self._cache_duration = timedelta(hours=cache_duration_hours)
        self._cache: Dict[str, tuple[AstronomyForecastData, datetime]] = {}

    async def fetch_astronomy_data(
        self, location: Location, days: int
    ) -> AstronomyForecastData:
        """Fetch astronomy data with caching."""
        cache_key = f"{location.latitude}_{location.longitude}_{days}"

        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_duration:
                logger.info(f"Returning cached astronomy data for {cache_key}")
                return cached_data

        # Fetch fresh data
        data = await self._source.fetch_astronomy_data(location, days)

        # Update cache
        self._cache[cache_key] = (data, datetime.now())

        # Clean old cache entries
        self._cleanup_cache()

        return data

    def _cleanup_cache(self) -> None:
        """Remove expired cache entries."""
        now = datetime.now()
        expired_keys = [
            key
            for key, (_, cached_time) in self._cache.items()
            if now - cached_time >= self._cache_duration
        ]
        for key in expired_keys:
            del self._cache[key]

    def get_source_name(self) -> str:
        return f"Cached({self._source.get_source_name()})"

    def get_source_url(self) -> str:
        return self._source.get_source_url()

    async def shutdown(self) -> None:
        self._cache.clear()
        await self._source.shutdown()

    def shutdown_sync(self) -> None:
        self._cache.clear()
        self._source.shutdown_sync()
