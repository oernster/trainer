"""
Transport API manager for fetching train data.

This module handles all communication with the Transport API,
including rate limiting, error handling, and data parsing.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..models.train_data import TrainData, TrainStatus, ServiceType
from ..managers.config_manager import ConfigData

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception for API-related errors."""

    pass


class NetworkException(APIException):
    """Exception for network-related errors."""

    pass


class RateLimitException(APIException):
    """Exception for rate limit exceeded errors."""

    pass


class AuthenticationException(APIException):
    """Exception for authentication failures."""

    pass


class RateLimiter:
    """Rate limiter for API calls to respect Transport API limits."""

    def __init__(self, calls_per_minute: int):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute
        """
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        async with self.lock:
            now = datetime.now()
            # Remove calls older than 1 minute
            self.calls = [
                call_time
                for call_time in self.calls
                if now - call_time < timedelta(minutes=1)
            ]

            if len(self.calls) >= self.calls_per_minute:
                # Wait until oldest call is more than 1 minute old
                oldest_call = min(self.calls)
                wait_time = 60 - (now - oldest_call).total_seconds()
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)

            self.calls.append(now)


class APIManager:
    """
    Handles Transport API communications with rate limiting and error handling.

    Provides methods to fetch train departures and service details from the
    Transport API while respecting rate limits and handling errors gracefully.
    """

    def __init__(self, config: ConfigData):
        """
        Initialize API manager.

        Args:
            config: Application configuration containing API credentials
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(config.api.rate_limit_per_minute)

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=self.config.api.timeout_seconds)
        self.session = aiohttp.ClientSession(
            timeout=timeout, headers={"User-Agent": "FleetTrainTimes/1.0"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_departures(self) -> List[TrainData]:
        """
        Fetch departure information from Fleet to London Waterloo.

        Returns:
            List[TrainData]: List of train departure information

        Raises:
            APIException: For API-related errors
            NetworkException: For network-related errors
        """
        await self.rate_limiter.wait_if_needed()

        params = {
            "app_id": self.config.api.app_id,
            "app_key": self.config.api.app_key,
            "destination": self.config.stations.to_code,
            "train_status": "passenger",
            "darwin": "true",  # Include real-time data
            "calling_at": self.config.stations.to_code,
            "from_offset": "PT0H",  # Start from now
            "to_offset": f"PT{self.config.display.time_window_hours}H",  # End at specified hours ahead
        }

        url = f"{self.config.api.base_url}/train/station/{self.config.stations.from_code}/live.json"

        for attempt in range(self.config.api.max_retries):
            try:
                if not self.session:
                    raise NetworkException("Session not initialized")

                logger.info(
                    f"Fetching departures (attempt {attempt + 1}/{self.config.api.max_retries})"
                )

                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        trains = self._parse_departures_response(data)
                        logger.info(f"Successfully fetched {len(trains)} trains")
                        return trains
                    elif response.status == 401:
                        raise AuthenticationException("Invalid API credentials")
                    elif response.status == 429:
                        raise RateLimitException("Rate limit exceeded")
                    else:
                        error_text = await response.text()
                        raise APIException(f"API error {response.status}: {error_text}")

            except aiohttp.ClientError as e:
                if attempt == self.config.api.max_retries - 1:
                    raise NetworkException(f"Network error: {str(e)}")

                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"Network error on attempt {attempt + 1}, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

        return []  # Should not reach here

    async def get_service_details(self, service_id: str) -> Optional[TrainData]:
        """
        Get detailed information about a specific train service.

        Args:
            service_id: Service identifier from departures response

        Returns:
            Optional[TrainData]: Enhanced train data with current location if available
        """
        await self.rate_limiter.wait_if_needed()

        params = {"app_id": self.config.api.app_id, "app_key": self.config.api.app_key}

        url = f"{self.config.api.base_url}/train/service/{service_id}/live.json"

        try:
            if not self.session:
                return None

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_service_response(data)
                else:
                    logger.warning(
                        f"Failed to get service details for {service_id}: {response.status}"
                    )
                    return None

        except aiohttp.ClientError as e:
            logger.warning(f"Network error getting service details: {e}")
            return None

    def _parse_departures_response(self, data: Dict) -> List[TrainData]:
        """
        Parse API departures response into TrainData objects.

        Args:
            data: Raw API response data

        Returns:
            List[TrainData]: Parsed train data objects
        """
        trains = []

        if "departures" not in data or "all" not in data["departures"]:
            logger.warning("No departures data in API response")
            return trains

        for departure in data["departures"]["all"]:
            try:
                train_data = self._create_train_data_from_departure(departure)
                if train_data:
                    trains.append(train_data)
            except Exception as e:
                logger.warning(f"Failed to parse departure: {e}")
                continue

        # Sort by departure time and limit to max_trains
        sorted_trains = sorted(trains, key=lambda t: t.departure_time)
        return sorted_trains[: self.config.display.max_trains]

    def _create_train_data_from_departure(self, departure: Dict) -> Optional[TrainData]:
        """
        Create TrainData object from single departure entry.

        Args:
            departure: Single departure data from API

        Returns:
            Optional[TrainData]: Parsed train data or None if parsing fails
        """
        try:
            # Parse times
            scheduled_time = self._parse_time(departure.get("aimed_departure_time"))
            expected_time = self._parse_time(
                departure.get("expected_departure_time")
                or departure.get("best_departure_estimate")
            )

            if not scheduled_time:
                return None

            # Use expected time if available, otherwise scheduled time
            departure_time = expected_time or scheduled_time

            # Calculate delay
            delay_minutes = 0
            if expected_time and scheduled_time:
                delay_minutes = int(
                    (expected_time - scheduled_time).total_seconds() / 60
                )

            # Determine status and service type
            status = self._determine_train_status(
                departure.get("status", ""), delay_minutes
            )
            service_type = self._determine_service_type(departure.get("category", ""))

            # Calculate estimated arrival if we have journey duration info
            estimated_arrival = None
            journey_duration = None

            # Try to get journey duration from timetable if available
            if "service_timetable" in departure:
                # This would require another API call, so we'll estimate based on typical journey time
                journey_duration = timedelta(
                    minutes=47
                )  # Typical Fleet to Waterloo time
                estimated_arrival = departure_time + journey_duration

            return TrainData(
                departure_time=departure_time,
                scheduled_departure=scheduled_time,
                destination=departure.get("destination_name", "London Waterloo"),
                platform=departure.get("platform"),
                operator=departure.get("operator_name", "Unknown"),
                service_type=service_type,
                status=status,
                delay_minutes=max(0, delay_minutes),
                estimated_arrival=estimated_arrival,
                journey_duration=journey_duration,
                current_location=departure.get(
                    "origin_name", "Fleet"
                ),  # Use origin as fallback
                train_uid=departure.get("train_uid", ""),
                service_id=departure.get("service", ""),
            )

        except Exception as e:
            logger.error(f"Error creating TrainData: {e}")
            return None

    def _parse_service_response(self, data: Dict) -> Optional[TrainData]:
        """
        Parse service details response to get current location.

        Args:
            data: Service details API response

        Returns:
            Optional[TrainData]: Enhanced train data with current location
        """
        # This would be used to get real-time location data
        # Implementation depends on the specific API response format
        return None

    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime]:
        """
        Parse time string to datetime object.

        Args:
            time_str: Time string from API (HH:MM format)

        Returns:
            Optional[datetime]: Parsed datetime or None if parsing fails
        """
        if not time_str:
            return None

        try:
            # Handle different time formats
            if ":" in time_str:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                today = datetime.now().date()
                result = datetime.combine(today, time_obj)

                # If the time is before current time, assume it's tomorrow
                if result < datetime.now():
                    result += timedelta(days=1)

                return result
        except ValueError as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")

        return None

    def _determine_train_status(
        self, status_str: str, delay_minutes: int
    ) -> TrainStatus:
        """
        Determine train status from API response.

        Args:
            status_str: Status string from API
            delay_minutes: Calculated delay in minutes

        Returns:
            TrainStatus: Parsed train status
        """
        status_upper = status_str.upper()

        if "CANCEL" in status_upper:
            return TrainStatus.CANCELLED
        elif delay_minutes > 0 or "LATE" in status_upper or "DELAY" in status_upper:
            return TrainStatus.DELAYED
        elif "ON TIME" in status_upper or delay_minutes == 0:
            return TrainStatus.ON_TIME
        else:
            return TrainStatus.UNKNOWN

    def _determine_service_type(self, category: str) -> ServiceType:
        """
        Determine service type from category code.

        Args:
            category: Category code from API

        Returns:
            ServiceType: Parsed service type
        """
        category_map = {
            "OO": ServiceType.STOPPING,  # Ordinary Passenger
            "XX": ServiceType.EXPRESS,  # Express Passenger
            "XZ": ServiceType.SLEEPER,  # Sleeper
            "BR": ServiceType.STOPPING,  # Bus replacement (treat as stopping)
        }
        return category_map.get(category, ServiceType.STOPPING)
