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
from ..models.train_data import TrainData, TrainStatus, ServiceType, CallingPoint
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
            "destination": self.config.stations.to_name,
            "train_status": "passenger",
            "darwin": "true",  # Include real-time data
            "calling_at": self.config.stations.to_name,
            "from_offset": "PT0H",  # Start from now
            "to_offset": f"PT{self.config.display.time_window_hours}H",  # End at specified hours ahead
        }

        url = f"{self.config.api.base_url}/train/station/{self.config.stations.from_name}/live.json"

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
                        
                        # Try to enhance trains with calling points data
                        enhanced_trains = []
                        for train in trains:
                            if train.service_id:
                                # Try to get detailed service information
                                enhanced_train = await self.get_service_details(train.service_id)
                                if enhanced_train:
                                    enhanced_trains.append(enhanced_train)
                                else:
                                    enhanced_trains.append(train)
                            else:
                                enhanced_trains.append(train)
                        
                        logger.info(f"Successfully fetched {len(enhanced_trains)} trains")
                        return enhanced_trains
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

            # Parse calling points if available
            calling_points = self._parse_calling_points(departure)

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
                calling_points=calling_points,
            )

        except Exception as e:
            logger.error(f"Error creating TrainData: {e}")
            return None

    def _parse_service_response(self, data: Dict) -> Optional[TrainData]:
        """
        Parse service details response to get enhanced train data with calling points.

        Args:
            data: Service details API response

        Returns:
            Optional[TrainData]: Enhanced train data with calling points
        """
        try:
            if "departures" not in data or "all" not in data["departures"]:
                logger.warning("No departures data in service response")
                return None
            
            # Get the first departure (should be our service)
            departures = data["departures"]["all"]
            if not departures:
                return None
                
            departure = departures[0]
            
            # Parse basic train data
            train_data = self._create_train_data_from_departure(departure)
            if not train_data:
                return None
            
            # Try to enhance with more detailed calling points if available
            if "calling_at" in departure and isinstance(departure["calling_at"], list):
                enhanced_calling_points = []
                
                for i, stop in enumerate(departure["calling_at"]):
                    try:
                        # Parse times
                        scheduled_arrival = self._parse_time(stop.get("aimed_arrival_time"))
                        scheduled_departure = self._parse_time(stop.get("aimed_departure_time"))
                        expected_arrival = self._parse_time(stop.get("expected_arrival_time"))
                        expected_departure = self._parse_time(stop.get("expected_departure_time"))
                        
                        # Determine if this is origin or destination
                        is_origin = i == 0
                        is_destination = i == len(departure["calling_at"]) - 1
                        
                        calling_point = CallingPoint(
                            station_name=stop.get("station_name", "Unknown"),
                            station_code=stop.get("station_name", "Unknown"),  # Use station name instead of code
                            scheduled_arrival=scheduled_arrival,
                            scheduled_departure=scheduled_departure,
                            expected_arrival=expected_arrival,
                            expected_departure=expected_departure,
                            platform=stop.get("platform"),
                            is_origin=is_origin,
                            is_destination=is_destination,
                        )
                        
                        enhanced_calling_points.append(calling_point)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse enhanced calling point: {e}")
                        continue
                
                if enhanced_calling_points:
                    # Create new TrainData with enhanced calling points
                    return TrainData(
                        departure_time=train_data.departure_time,
                        scheduled_departure=train_data.scheduled_departure,
                        destination=train_data.destination,
                        platform=train_data.platform,
                        operator=train_data.operator,
                        service_type=train_data.service_type,
                        status=train_data.status,
                        delay_minutes=train_data.delay_minutes,
                        estimated_arrival=train_data.estimated_arrival,
                        journey_duration=train_data.journey_duration,
                        current_location=train_data.current_location,
                        train_uid=train_data.train_uid,
                        service_id=train_data.service_id,
                        calling_points=enhanced_calling_points,
                    )
            
            return train_data
            
        except Exception as e:
            logger.error(f"Error parsing service response: {e}")
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
            "XX": ServiceType.FAST,     # Express Passenger (treat as fast, not direct)
            "XZ": ServiceType.SLEEPER,  # Sleeper
            "BR": ServiceType.STOPPING,  # Bus replacement (treat as stopping)
        }
        return category_map.get(category, ServiceType.FAST)  # Default to FAST instead of STOPPING

    def _parse_calling_points(self, departure: Dict) -> List[CallingPoint]:
        """
        Parse calling points from departure data.
        
        Args:
            departure: Departure data from API
            
        Returns:
            List[CallingPoint]: List of calling points for this service
        """
        calling_points = []
        
        # Check if calling points data is available in the departure
        if "calling_at" in departure and isinstance(departure["calling_at"], list):
            for i, stop in enumerate(departure["calling_at"]):
                try:
                    # Parse times
                    scheduled_arrival = self._parse_time(stop.get("aimed_arrival_time"))
                    scheduled_departure = self._parse_time(stop.get("aimed_departure_time"))
                    expected_arrival = self._parse_time(stop.get("expected_arrival_time"))
                    expected_departure = self._parse_time(stop.get("expected_departure_time"))
                    
                    # Determine if this is origin or destination
                    is_origin = i == 0
                    is_destination = i == len(departure["calling_at"]) - 1
                    
                    calling_point = CallingPoint(
                        station_name=stop.get("station_name", "Unknown"),
                        station_code=stop.get("station_name", "Unknown"),  # Use station name instead of code
                        scheduled_arrival=scheduled_arrival,
                        scheduled_departure=scheduled_departure,
                        expected_arrival=expected_arrival,
                        expected_departure=expected_departure,
                        platform=stop.get("platform"),
                        is_origin=is_origin,
                        is_destination=is_destination,
                    )
                    
                    calling_points.append(calling_point)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse calling point: {e}")
                    continue
        
        # If no calling points data available, create realistic calling points for Fleet to Waterloo route
        if not calling_points:
            # Create origin calling point
            origin_name = departure.get("origin_name", "Fleet")
            origin_code = self.config.stations.from_name
            
            scheduled_dep = self._parse_time(departure.get("aimed_departure_time"))
            expected_dep = self._parse_time(departure.get("expected_departure_time"))
            
            origin_point = CallingPoint(
                station_name=origin_name,
                station_code=origin_name,  # Use station name instead of code
                scheduled_arrival=None,
                scheduled_departure=scheduled_dep,
                expected_arrival=None,
                expected_departure=expected_dep,
                platform=departure.get("platform"),
                is_origin=True,
                is_destination=False,
            )
            calling_points.append(origin_point)
            
            # Add realistic intermediate stations based on service type
            service_type = self._determine_service_type(departure.get("category", ""))
            departure_time = expected_dep or scheduled_dep
            
            if departure_time and service_type == ServiceType.STOPPING:
                # Add intermediate stations for stopping services
                intermediate_stations = [
                    ("Farnborough (Main)", 8),  # 8 minutes from Fleet
                    ("Brookwood", 15),          # 15 minutes from Fleet
                    ("Woking", 20),             # 20 minutes from Fleet
                    ("West Byfleet", 25),       # 25 minutes from Fleet
                    ("Weybridge", 30),          # 30 minutes from Fleet
                    ("Walton-on-Thames", 35),   # 35 minutes from Fleet
                    ("Surbiton", 40),           # 40 minutes from Fleet
                ]
                
                for station_name, minutes_offset in intermediate_stations:
                    arrival_time = departure_time + timedelta(minutes=minutes_offset)
                    departure_time_station = arrival_time + timedelta(minutes=1)  # 1 minute stop
                    
                    intermediate_point = CallingPoint(
                        station_name=station_name,
                        station_code=station_name,  # Use station name instead of code
                        scheduled_arrival=arrival_time,
                        scheduled_departure=departure_time_station,
                        expected_arrival=arrival_time,
                        expected_departure=departure_time_station,
                        platform=None,  # Platform info usually not available for intermediate stations
                        is_origin=False,
                        is_destination=False,
                    )
                    calling_points.append(intermediate_point)
            
            elif departure_time and service_type == ServiceType.FAST:
                # Add fewer stations for fast services
                intermediate_stations = [
                    ("Woking", 20),             # 20 minutes from Fleet
                    ("Surbiton", 35),           # 35 minutes from Fleet
                ]
                
                for station_name, minutes_offset in intermediate_stations:
                    arrival_time = departure_time + timedelta(minutes=minutes_offset)
                    departure_time_station = arrival_time + timedelta(minutes=1)  # 1 minute stop
                    
                    intermediate_point = CallingPoint(
                        station_name=station_name,
                        station_code=station_name,  # Use station name instead of code
                        scheduled_arrival=arrival_time,
                        scheduled_departure=departure_time_station,
                        expected_arrival=arrival_time,
                        expected_departure=departure_time_station,
                        platform=None,
                        is_origin=False,
                        is_destination=False,
                    )
                    calling_points.append(intermediate_point)
            
            # Create destination calling point
            dest_name = departure.get("destination_name", "London Waterloo")
            dest_code = self.config.stations.to_name
            
            # Estimate arrival time based on service type
            estimated_arrival = None
            if departure_time:
                if service_type == ServiceType.EXPRESS:
                    # Express service - 35 minutes
                    estimated_arrival = departure_time + timedelta(minutes=35)
                elif service_type == ServiceType.FAST:
                    # Fast service - 42 minutes
                    estimated_arrival = departure_time + timedelta(minutes=42)
                else:
                    # Stopping service - 50 minutes
                    estimated_arrival = departure_time + timedelta(minutes=50)
            
            dest_point = CallingPoint(
                station_name=dest_name,
                station_code=dest_name,  # Use station name instead of code
                scheduled_arrival=estimated_arrival,
                scheduled_departure=None,
                expected_arrival=estimated_arrival,
                expected_departure=None,
                platform=None,  # Destination platform usually not known
                is_origin=False,
                is_destination=True,
            )
            calling_points.append(dest_point)
        
        return calling_points
