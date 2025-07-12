"""
Train data management for the Train Times application.

This module coordinates fetching train data from the internal database,
processing it, and managing updates. Now uses offline timetable data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from PySide6.QtCore import QObject, Signal, QTimer
from ..models.train_data import TrainData, TrainStatus, ServiceType
from ..api.api_manager import APIManager, APIException, NetworkException
from ..managers.config_manager import ConfigData
from ..managers.timetable_manager import TimetableManager
from ..utils.helpers import (
    sort_trains_by_departure,
    filter_trains_by_status,
    calculate_journey_stats,
)

logger = logging.getLogger(__name__)


class TrainManager(QObject):
    """
    Manages train data fetching, processing, and updates.

    Coordinates between the API manager and UI components to provide
    real-time train information with automatic refresh capabilities.
    """

    # Signals
    trains_updated = Signal(list)  # List[TrainData]
    error_occurred = Signal(str)  # Error message
    status_changed = Signal(str)  # Status message
    connection_changed = Signal(bool, str)  # Connected, message
    last_update_changed = Signal(str)  # Last update timestamp

    def __init__(self, config: ConfigData):
        """
        Initialize train manager.

        Args:
            config: Application configuration
        """
        super().__init__()
        self.config = config
        self.api_manager: Optional[APIManager] = None
        self.timetable_manager: Optional[TimetableManager] = None
        self.current_trains: List[TrainData] = []
        self.last_update: Optional[datetime] = None
        self.is_fetching = False
        
        # Store current route for timetable generation
        self.from_station: Optional[str] = None
        self.to_station: Optional[str] = None

        # Auto-refresh removed as obsolete

        # Initialize timetable manager
        try:
            self.timetable_manager = TimetableManager()
            logger.debug("TimetableManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TimetableManager: {e}")
            self.timetable_manager = None

        logger.debug("TrainManager initialized")

    def update_config(self, config: ConfigData):
        """Update the configuration and refresh if needed."""
        old_time_window = self.config.display.time_window_hours if self.config else None
        self.config = config
        
        # If time window changed, log it
        if old_time_window != config.display.time_window_hours:
            logger.info(f"Time window updated from {old_time_window} to {config.display.time_window_hours} hours")

    def set_route(self, from_station: str, to_station: str):
        """Set the current route for timetable generation."""
        # Convert station codes to names if needed
        station_mapping = self._create_station_mapping()
        
        # Check if we received codes or names
        if from_station in station_mapping:
            # It's a code, convert to name
            self.from_station = station_mapping[from_station]
            logger.debug(f"Converted from station code {from_station} to name {self.from_station}")
        else:
            # It's already a name
            self.from_station = from_station
            
        if to_station in station_mapping:
            # It's a code, convert to name
            self.to_station = station_mapping[to_station]
            logger.debug(f"Converted to station code {to_station} to name {self.to_station}")
        else:
            # It's already a name
            self.to_station = to_station
            
        logger.debug(f"Route set: {self.from_station} -> {self.to_station}")

    # Auto-refresh functionality removed as obsolete

    async def initialize_api(self):
        """Initialize API manager."""
        try:
            self.api_manager = APIManager(self.config)
            logger.info("API manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize API manager: {e}")
            self.error_occurred.emit(f"API initialization failed: {e}")

    def fetch_trains(self):
        """Fetch train data asynchronously."""
        if self.is_fetching:
            logger.warning("Fetch already in progress, skipping")
            return

        # Run async fetch using QTimer to integrate with Qt event loop
        QTimer.singleShot(0, self._start_async_fetch)

    def _start_async_fetch(self):
        """Start async fetch in a way compatible with Qt."""
        import threading

        def run_async():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._fetch_trains_async())
                loop.close()
            except Exception as e:
                logger.error(f"Error in async fetch thread: {e}")
                self.error_occurred.emit(f"Fetch error: {e}")
                self.is_fetching = False

        # Run in separate thread
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    async def _fetch_trains_async(self):
        """Async method to fetch train data from internal database."""
        if self.is_fetching:
            return

        self.is_fetching = True
        self.status_changed.emit("Loading train data...")

        try:
            # Always use offline timetable instead of API
            if self.timetable_manager is not None:
                trains = await self._fetch_trains_from_timetable()
                logger.debug("Successfully fetched trains from offline timetable")
            else:
                logger.error("Timetable manager not available")
                raise Exception("Timetable manager not available")

            # Process the data
            processed_trains = self._process_train_data(trains)

            # Update state
            self.current_trains = processed_trains
            self.last_update = datetime.now()

            # Emit signals
            self.trains_updated.emit(processed_trains)
            self.connection_changed.emit(True, "Connected (Offline)")
            self.last_update_changed.emit(self.last_update.strftime("%H:%M:%S"))

            stats = calculate_journey_stats(processed_trains)
            status_msg = f"Updated: {len(processed_trains)} trains loaded"
            if stats["delayed"] > 0:
                status_msg += f", {stats['delayed']} delayed"
            if stats["cancelled"] > 0:
                status_msg += f", {stats['cancelled']} cancelled"

            self.status_changed.emit(status_msg)

            logger.debug(f"Successfully loaded {len(processed_trains)} trains")

        except Exception as e:
            error_msg = f"Error loading train data: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "Error")

        finally:
            self.is_fetching = False

    async def _fetch_trains_from_timetable(self) -> List[TrainData]:
        """Fetch train data from internal timetable database."""
        # Check if timetable manager is available
        if self.timetable_manager is None:
            logger.error("Timetable manager not available")
            return []
        
        # Get current route
        if not self.from_station or not self.to_station:
            # If no route configured, return empty list
            logger.warning("No route configured for timetable lookup")
            return []

        # Generate train services using timetable manager
        departure_time = datetime.now()
        
        # Calculate time window end based on configuration
        time_window_hours = self.config.display.time_window_hours
        time_window_end = departure_time + timedelta(hours=time_window_hours)
        
        # Generate more services than needed to ensure we have enough within the time window
        # Generate services for the full time window plus some buffer
        estimated_services_needed = max(self.config.display.max_trains * 2, 20)
        train_services = self.timetable_manager.generate_train_services(
            self.from_station, self.to_station, departure_time,
            num_services=estimated_services_needed
        )

        # Convert train services to TrainData objects and filter by time window
        trains = []
        for i, service in enumerate(train_services):
            # Parse departure and arrival times
            dep_time = datetime.strptime(service.departure_time, "%H:%M").replace(
                year=departure_time.year, month=departure_time.month, day=departure_time.day
            )
            arr_time = datetime.strptime(service.arrival_time, "%H:%M").replace(
                year=departure_time.year, month=departure_time.month, day=departure_time.day
            )
            
            # Handle next day arrivals
            if arr_time < dep_time:
                arr_time += timedelta(days=1)
            
            # Handle next day departures (if departure time has wrapped to next day)
            if dep_time < departure_time:
                dep_time += timedelta(days=1)
                arr_time += timedelta(days=1)
            
            # Filter by time window - only include trains departing within the configured window
            if dep_time > time_window_end:
                continue
            
            # All trains are on time since we removed delay simulation
            delay_minutes = 0
            train_status = TrainStatus.ON_TIME
            
            # Map service type
            service_type_map = {
                "Express": ServiceType.EXPRESS,
                "Fast": ServiceType.FAST,
                "Stopping": ServiceType.STOPPING
            }
            service_type = service_type_map.get(service.service_type, ServiceType.STOPPING)
            
            # Generate unique IDs
            service_id = f"SVC{i+1:03d}{dep_time.strftime('%H%M')}"
            train_uid = f"T{i+1:05d}"
            
            # Generate calling points for this service
            calling_points = self._generate_calling_points(service, dep_time, arr_time, service_type)
            
            train_data = TrainData(
                departure_time=dep_time,
                scheduled_departure=dep_time,
                destination=self.to_station,
                platform=service.platform,
                operator=service.operator,
                service_type=service_type,
                status=train_status,
                delay_minutes=delay_minutes,
                estimated_arrival=arr_time,
                journey_duration=timedelta(minutes=service.duration_minutes),
                current_location=None,
                train_uid=train_uid,
                service_id=service_id,
                calling_points=calling_points
            )
            trains.append(train_data)
            
            # Stop if we have enough trains within the time window
            if len(trains) >= self.config.display.max_trains:
                break

        logger.debug(f"Generated {len(trains)} trains within {time_window_hours} hour time window")
        return trains

    def _generate_calling_points(self, service, departure_time: datetime, arrival_time: datetime, service_type_enum):
        """Generate calling points for a train service."""
        from ..models.train_data import CallingPoint
        
        calling_points = []
        
        # Ensure we have valid station names
        if not self.from_station or not self.to_station:
            return calling_points
        
        # Add origin station
        origin_point = CallingPoint(
            station_name=self.from_station,
            station_code=self.from_station[:3].upper(),  # Simple code generation
            scheduled_arrival=None,
            scheduled_departure=departure_time,
            expected_arrival=None,
            expected_departure=departure_time,
            platform=service.platform,
            is_origin=True,
            is_destination=False
        )
        calling_points.append(origin_point)
        
        # Add intermediate stations based on the route and service type
        # Convert ServiceType enum to string for route lookup
        service_type_str = service_type_enum.value.title() if service_type_enum else "Stopping"
            
        intermediate_stations = self._get_intermediate_stations_for_route(
            self.from_station, self.to_station, service_type_str
        )
        
        # Calculate intermediate times using realistic travel times between stations
        current_time = departure_time
        
        for i, station_name in enumerate(intermediate_stations):
            # Calculate realistic travel time to this station
            travel_time = self._calculate_realistic_travel_time(
                intermediate_stations[i-1] if i > 0 else self.from_station,
                station_name,
                service_type_str
            )
            
            current_time += timedelta(minutes=travel_time)
            
            # Add stop time (1-3 minutes depending on station importance)
            stop_time = self._get_station_stop_time(station_name)
            
            intermediate_point = CallingPoint(
                station_name=station_name,
                station_code=station_name[:3].upper(),
                scheduled_arrival=current_time,
                scheduled_departure=current_time + timedelta(minutes=stop_time),
                expected_arrival=current_time,
                expected_departure=current_time + timedelta(minutes=stop_time),
                platform=None,
                is_origin=False,
                is_destination=False
            )
            calling_points.append(intermediate_point)
            
            # Update current time to departure time from this station
            current_time += timedelta(minutes=stop_time)
        
        # Add destination station
        destination_point = CallingPoint(
            station_name=self.to_station,
            station_code=self.to_station[:3].upper(),
            scheduled_arrival=arrival_time,
            scheduled_departure=None,
            expected_arrival=arrival_time,
            expected_departure=None,
            platform=None,
            is_origin=False,
            is_destination=True
        )
        calling_points.append(destination_point)
        
        return calling_points

    def _get_intermediate_stations_for_route(self, from_station: str, to_station: str, service_type: str = "Stopping") -> List[str]:
        """Get intermediate stations for a specific route based on service type."""
        logger.debug(f"Getting intermediate stations for route: {from_station} -> {to_station}, service type: {service_type}")
        
        # Get configured via stations
        configured_via_stations = []
        if hasattr(self, 'config') and self.config and hasattr(self.config, 'stations'):
            configured_via_stations = getattr(self.config.stations, 'via_stations', [])
        
        logger.debug(f"Configured via stations: {configured_via_stations}")
        
        # Use dynamic routing from JSON data instead of hardcoded patterns
        route_pattern_stations = []
        
        # Create a journey showing key interchange stations (CHANGES) with stops between them
        all_stations = self._create_detailed_interchange_journey(
            from_station, to_station, configured_via_stations, service_type
        )
        
        logger.debug(f"Route pattern stations found: {route_pattern_stations}")
        logger.debug(f"Final intermediate stations list: {all_stations} (total: {len(all_stations)})")
        return all_stations

    def _merge_stations_in_journey_order(self, from_station: str, to_station: str,
                                       route_pattern_stations: List[str],
                                       configured_via_stations: List[str]) -> List[str]:
        """
        Merge route pattern stations with configured via stations in logical journey order.
        
        This method attempts to create a realistic journey by placing configured via stations
        in geographically/logically correct positions within the route pattern.
        """
        logger.debug(f"Merging stations for {from_station} -> {to_station}")
        logger.debug(f"Route pattern: {route_pattern_stations}")
        logger.info(f"Configured via: {configured_via_stations}")
        
        # Use JSON data to determine station relationships dynamically
        station_relationships = self._build_station_relationships_from_json()
        
        # Start with route pattern as base
        merged_stations = route_pattern_stations[:]
        
        # Insert configured via stations in logical positions
        for via_station in configured_via_stations:
            if via_station not in merged_stations:
                # Find the best position to insert this via station
                insert_position = self._find_best_insert_position(
                    via_station, merged_stations, from_station, to_station, station_relationships
                )
                merged_stations.insert(insert_position, via_station)
                logger.debug(f"Inserted {via_station} at position {insert_position}")
        
        logger.debug(f"Final merged stations: {merged_stations}")
        return merged_stations
    
    def _find_best_insert_position(self, via_station: str, current_stations: List[str],
                                 from_station: str, to_station: str,
                                 station_relationships: dict) -> int:
        """
        Find the best position to insert a via station in the journey order.
        """
        # Get station info
        via_info = station_relationships.get(via_station, {"region": "unknown", "priority": 5})
        
        # Special case handling for known problematic combinations
        if from_station == "Fleet" and to_station == "Manchester":
            # For Fleet -> Manchester, the CORRECT geographical order should be:
            # Fleet -> Farnborough -> Clapham Junction -> (London route) -> Bristol -> Birmingham -> Manchester
            
            if via_station == "Clapham Junction":
                # Clapham Junction should be VERY early - right after local Fleet stations
                # It's the first major London interchange from Fleet
                for i, station in enumerate(current_stations):
                    if station in ["Farnborough"]:
                        return i + 1  # Insert right after Farnborough
                return 0  # Insert at beginning if no Farnborough
            
            elif "Bristol Temple Meads" in via_station:
                # Bristol should be after London area but before Birmingham/Midlands
                # Look for a good position after London area stations
                for i, station in enumerate(current_stations):
                    if station in ["Birmingham New Street", "Coventry", "Wolverhampton", "Stafford"]:
                        return i  # Insert before Midlands stations
                # If no Midlands stations found, insert after London/South stations
                for i, station in enumerate(current_stations):
                    if station in ["Reading", "Oxford", "Clapham Junction"]:
                        return i + 1  # Insert after London area stations
                return len(current_stations) // 2  # Fallback to middle
        
        # Default: insert in middle if no specific logic applies
        return max(1, len(current_stations) // 2)
    
    def _limit_stations_by_service_type(self, stations: List[str], service_type: str) -> List[str]:
        """
        Limit the number of stations shown based on service type.
        Express services should show fewer stops, stopping services can show more.
        """
        if not stations:
            return stations
            
        # Define limits based on service type
        limits = {
            "Express": 4,      # Express: only major stations
            "Fast": 8,         # Fast: moderate number of stations
            "Stopping": 12     # Stopping: more stations but still reasonable
        }
        
        max_stations = limits.get(service_type, 8)  # Default to Fast limit
        
        if len(stations) <= max_stations:
            return stations
        
        # If we need to limit, prioritize keeping configured via stations
        # and major interchange stations
        major_stations = {
            "Clapham Junction", "Birmingham New Street", "Reading", "Oxford",
            "Bristol Temple Meads", "Manchester", "London Waterloo", "London Paddington"
        }
        
        # Always keep major stations and configured via stations
        priority_stations = []
        other_stations = []
        
        for station in stations:
            station_clean = station.replace(" (Cross Country Line)", "")
            if (station in major_stations or
                station_clean in major_stations or
                "Bristol Temple Meads" in station or
                "Clapham Junction" in station):
                priority_stations.append(station)
            else:
                other_stations.append(station)
        
        # Combine priority stations with some other stations up to the limit
        remaining_slots = max_stations - len(priority_stations)
        if remaining_slots > 0:
            result = priority_stations + other_stations[:remaining_slots]
        else:
            result = priority_stations[:max_stations]
        
        logger.debug(f"Limited {len(stations)} stations to {len(result)} for {service_type} service")
        return result
    
    def _create_interchange_journey(self, from_station: str, to_station: str,
                                  configured_via_stations: List[str], service_type: str) -> List[str]:
        """
        Create a journey showing key interchange stations (CHANGES) rather than all stops.
        This focuses on where passengers would change trains/lines.
        """
        logger.debug(f"Creating interchange journey: {from_station} -> {to_station}")
        logger.debug(f"Configured via stations: {configured_via_stations}")
        
        # Define major interchange stations and their typical connections
        major_interchanges = {
            "Clapham Junction": {
                "lines": ["South Western", "Southern", "London Overground"],
                "connections": ["London terminals", "South Coast", "Cross Country"]
            },
            "Birmingham New Street": {
                "lines": ["West Coast Main Line", "Cross Country", "Chiltern"],
                "connections": ["London", "Manchester", "Scotland", "South West"]
            },
            "Reading": {
                "lines": ["Great Western", "Cross Country", "Elizabeth Line"],
                "connections": ["London Paddington", "South West", "Midlands"]
            },
            "Bristol Temple Meads": {
                "lines": ["Great Western", "Cross Country"],
                "connections": ["London", "South Wales", "Midlands", "North"]
            },
            "Manchester Piccadilly": {
                "lines": ["West Coast Main Line", "Trans-Pennine", "Northern"],
                "connections": ["London", "Scotland", "Yorkshire", "North West"]
            },
            "Oxford": {
                "lines": ["Great Western", "Chiltern"],
                "connections": ["London", "Birmingham", "Worcester"]
            }
        }
        
        # Create journey segments based on configured via stations
        journey_segments = []
        
        if not configured_via_stations:
            # Direct service - check if it's really direct or has key interchanges
            if service_type == "Express":
                # Express might have 1-2 key interchanges
                key_interchange = self._find_key_interchange(from_station, to_station)
                if key_interchange:
                    journey_segments = [key_interchange]
            # For other service types without configured via stations, show as direct
            return journey_segments
        
        # Build journey with configured via stations as key interchanges
        current_origin = from_station
        
        for via_station in configured_via_stations:
            # Clean station name for lookup
            clean_via = via_station.replace(" (Cross Country Line)", "").strip()
            
            # Add intermediate key stations if the segment is very long
            intermediate = self._find_intermediate_interchange(current_origin, clean_via)
            if intermediate:
                journey_segments.append(intermediate)
            
            # Add the via station as a key interchange
            journey_segments.append(clean_via)
            current_origin = clean_via
        
        # Add final segment interchange if needed
        final_intermediate = self._find_intermediate_interchange(current_origin, to_station)
        if final_intermediate:
            journey_segments.append(final_intermediate)
        
        logger.info(f"Created interchange journey: {journey_segments}")
        return journey_segments
    
    def _find_key_interchange(self, from_station: str, to_station: str) -> Optional[str]:
        """Find a key interchange station for direct services."""
        # Common interchanges for major routes
        route_interchanges = {
            ("Fleet", "Manchester"): "Birmingham New Street",
            ("Fleet", "Bristol"): "Reading",
            ("London Waterloo", "Manchester"): "Birmingham New Street",
            ("London Paddington", "Manchester"): "Birmingham New Street",
        }
        
        route_key = (from_station, to_station)
        return route_interchanges.get(route_key)
    
    def _find_intermediate_interchange(self, from_station: str, to_station: str) -> Optional[str]:
        """Find intermediate interchange for long segments."""
        # Only add intermediate interchanges for very long segments
        long_distance_routes = {
            ("Fleet", "Bristol Temple Meads"): "Reading",
            ("Fleet", "Birmingham New Street"): "Reading",
            ("Clapham Junction", "Manchester"): "Birmingham New Street",
            ("Bristol Temple Meads", "Manchester"): "Birmingham New Street",
        }
        
        route_key = (from_station, to_station)
        return long_distance_routes.get(route_key)
    
    def _create_detailed_interchange_journey(self, from_station: str, to_station: str,
                                           configured_via_stations: List[str], service_type: str) -> List[str]:
        """
        Create a detailed journey showing ALL stops in geographical order.
        Uses JSON line data to build proper railway network routing with configured via stations.
        """
        logger.debug(f"Creating detailed interchange journey: {from_station} -> {to_station}")
        logger.debug(f"Configured via stations: {configured_via_stations}")
        logger.debug(f"Service type: {service_type}")
        
        # Create station code to name mapping
        station_mapping = self._create_station_mapping()
        
        # Convert station codes to full names
        from_name = station_mapping.get(from_station, from_station)
        to_name = station_mapping.get(to_station, to_station)
        
        logger.debug(f"Mapped stations: {from_station} -> {from_name}, {to_station} -> {to_name}")
        
        # Load all line data
        line_data = self._load_all_line_data()
        if not line_data:
            logger.warning("No line data available for dynamic routing")
            return [from_name, to_name]
        
        # Build station network from JSON data
        station_network = self._build_station_network(line_data)
        
        # If we have configured via stations, build route through them
        if configured_via_stations:
            logger.debug(f"Building route through configured via stations: {configured_via_stations}")
            route = self._build_route_via_configured_stations(
                from_name, to_name, configured_via_stations, station_network, service_type
            )
        else:
            # No via stations configured, find direct route
            logger.info("No via stations configured, finding direct route")
            route = self._find_geographical_route(from_name, to_name, station_network, service_type)
        
        if not route or len(route) < 2:
            logger.warning("Dynamic routing failed, using JSON-only fallback")
            # Use JSON-only routing as fallback
            route = self._get_route_from_json_data(from_name, to_name, service_type)
        
        logger.debug(f"Generated route with {len(route)} stations: {' -> '.join(route[:5])}{'...' if len(route) > 5 else ''}")
        return route

    def _build_route_via_configured_stations(self, from_station: str, to_station: str,
                                           configured_via_stations: List[str],
                                           station_network: Dict[str, Dict], service_type: str) -> List[str]:
        """Build a route that goes through all configured via stations in order."""
        logger.debug(f"Building route: {from_station} -> {' -> '.join(configured_via_stations)} -> {to_station}")
        
        # For configured via stations, create a more direct route
        # This respects the user's intention for a specific routing
        complete_route = [from_station]
        
        # Add each via station as a direct waypoint
        for via_station in configured_via_stations:
            logger.debug(f"Adding configured via station: {via_station}")
            
            # For Express services, add minimal intermediate stations
            if service_type == "Express":
                # Add only major interchange stations between current and via station
                intermediate_stations = self._get_major_interchanges_between(
                    complete_route[-1], via_station, station_network
                )
                complete_route.extend(intermediate_stations)
            elif service_type == "Fast":
                # Add some key stations but not all
                intermediate_stations = self._get_key_stations_between(
                    complete_route[-1], via_station, station_network
                )
                complete_route.extend(intermediate_stations)
            # For Stopping services, we can add more stations but still keep it reasonable
            
            # Add the via station itself
            if via_station not in complete_route:
                complete_route.append(via_station)
        
        # Add final segment to destination
        if service_type == "Express":
            # Add only major interchange stations to destination
            intermediate_stations = self._get_major_interchanges_between(
                complete_route[-1], to_station, station_network
            )
            complete_route.extend(intermediate_stations)
        elif service_type == "Fast":
            # Add some key stations to destination
            intermediate_stations = self._get_key_stations_between(
                complete_route[-1], to_station, station_network
            )
            complete_route.extend(intermediate_stations)
        
        # Add destination
        if to_station not in complete_route:
            complete_route.append(to_station)
        
        logger.debug(f"Complete route built with {len(complete_route)} stations: {' -> '.join(complete_route[:5])}{'...' if len(complete_route) > 5 else ''}")
        return complete_route

    def _get_major_interchanges_between(self, from_station: str, to_station: str,
                                      station_network: Dict[str, Dict]) -> List[str]:
        """Get only major interchange stations between two stations."""
        # For Express services, only include major interchanges
        major_interchanges = {
            "Reading", "Oxford", "Birmingham New Street", "Coventry",
            "Wolverhampton", "Stafford", "Crewe", "Preston", "Lancaster"
        }
        
        # Find a simple route and filter for major interchanges only
        route = self._find_geographical_route(from_station, to_station, station_network, "Stopping")
        if not route or len(route) <= 2:
            return []
        
        # Filter to only major interchanges
        filtered = []
        for station in route[1:-1]:  # Exclude origin and destination
            if station in major_interchanges:
                filtered.append(station)
        
        return filtered

    def _get_key_stations_between(self, from_station: str, to_station: str,
                                station_network: Dict[str, Dict]) -> List[str]:
        """Get key stations between two stations for Fast services."""
        # For Fast services, include major interchanges and some regional stations
        route = self._find_geographical_route(from_station, to_station, station_network, "Stopping")
        if not route or len(route) <= 2:
            return []
        
        # Take every 3rd station plus major interchanges
        major_interchanges = {
            "Reading", "Oxford", "Birmingham New Street", "Coventry",
            "Wolverhampton", "Stafford", "Crewe", "Preston", "Lancaster",
            "Basingstoke", "Woking", "Clapham Junction"
        }
        
        filtered = []
        for i, station in enumerate(route[1:-1], 1):  # Exclude origin and destination
            if station in major_interchanges or i % 3 == 0:
                filtered.append(station)
        
        return filtered
    
    # Cache for railway line data to prevent repeated loading
    _line_data_cache = None
    
    def _load_all_line_data(self) -> Dict[str, Dict]:
        """Load all railway line JSON data files."""
        # Return cached data if available
        if self.__class__._line_data_cache is not None:
            return self.__class__._line_data_cache
            
        import json
        from pathlib import Path
        
        line_data = {}
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    line_name = data.get('metadata', {}).get('line_name', json_file.stem)
                    line_data[line_name] = data
                    logger.debug(f"Loaded line data: {line_name}")
            
            logger.debug(f"Loaded {len(line_data)} railway line data files")
            # Cache the data for future use
            self.__class__._line_data_cache = line_data
            return line_data
            
        except Exception as e:
            logger.error(f"Failed to load line data: {e}")
            return {}
    
    def _build_station_network(self, line_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Build a network of stations with their connections and coordinates."""
        station_network = {}
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            
            for i, station in enumerate(stations):
                station_name = station['name']
                
                if station_name not in station_network:
                    station_network[station_name] = {
                        'coordinates': station.get('coordinates', {}),
                        'lines': [],
                        'connections': [],
                        'interchange': station.get('interchange', [])
                    }
                
                # Add this line to the station
                station_network[station_name]['lines'].append(line_name)
                
                # Add connections to adjacent stations on this line
                if i > 0:  # Previous station
                    prev_station = stations[i-1]['name']
                    if prev_station not in station_network[station_name]['connections']:
                        station_network[station_name]['connections'].append(prev_station)
                
                if i < len(stations) - 1:  # Next station
                    next_station = stations[i+1]['name']
                    if next_station not in station_network[station_name]['connections']:
                        station_network[station_name]['connections'].append(next_station)
        
        logger.debug(f"Built station network with {len(station_network)} stations")
        return station_network
    
    def _build_weighted_graph(self, line_data: Dict[str, Dict]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict]]]:
        """
        Build a weighted graph representation of the railway network.
        Returns:
            - graph: Dictionary where keys are station names, values are dictionaries mapping connected stations to edge weights
            - station_timetables: Dictionary containing timetable data for stations
        """
        graph = {}
        station_coordinates = {}
        station_timetables = {}
        
        # First pass: collect all stations and their coordinates
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                station_name = station['name']
                if station_name not in station_coordinates and 'coordinates' in station:
                    station_coordinates[station_name] = station['coordinates']
                
                # Collect timetable data if available
                if 'timetable' in station:
                    if station_name not in station_timetables:
                        station_timetables[station_name] = {}
                    station_timetables[station_name][line_name] = station['timetable']
        
        # Second pass: build the graph with weighted edges
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            line_frequency = data.get('metadata', {}).get('frequency_minutes', 30)
            line_speed = data.get('metadata', {}).get('average_speed_mph', 60)
            
            for i, station in enumerate(stations):
                station_name = station['name']
                
                if station_name not in graph:
                    graph[station_name] = {}
                
                # Add connections to adjacent stations on this line
                if i > 0:  # Previous station
                    prev_station = stations[i-1]['name']
                    if prev_station not in graph:
                        graph[prev_station] = {}
                    
                    # Calculate weight based on distance and line properties
                    weight = self._calculate_edge_weight(
                        station_name, prev_station,
                        station_coordinates,
                        line_frequency, line_speed,
                        line_name
                    )
                    
                    # Add bidirectional connection
                    graph[station_name][prev_station] = weight
                    graph[prev_station][station_name] = weight
                
                # Add interchange connections
                interchanges = station.get('interchange', [])
                for interchange in interchanges:
                    # Handle both string and object formats for interchange data
                    if isinstance(interchange, str):
                        interchange_station = interchange
                        interchange_time = 5  # Default time
                    elif isinstance(interchange, dict):
                        interchange_station = interchange.get('station')
                        interchange_time = interchange.get('time_minutes', 5)
                    else:
                        continue
                    
                    if interchange_station and interchange_station != station_name:
                        if interchange_station not in graph:
                            graph[interchange_station] = {}
                        
                        # Interchange penalty is higher than direct connection
                        interchange_weight = interchange_time * 2  # Penalty for changing trains
                        
                        graph[station_name][interchange_station] = interchange_weight
                        graph[interchange_station][station_name] = interchange_weight
        
        logger.debug(f"Built weighted graph with {len(graph)} stations")
        return graph, station_timetables
    
    def _calculate_edge_weight(self, station1: str, station2: str,
                             coordinates: Dict[str, Dict],
                             frequency: int, speed: float,
                             line_name: str) -> float:
        """
        Calculate edge weight between two stations based on multiple factors.
        Lower weight = better connection.
        """
        # 1. Calculate geographical distance if coordinates available
        distance = 0
        if station1 in coordinates and station2 in coordinates:
            distance = self._calculate_haversine_distance(
                coordinates[station1], coordinates[station2]
            )
        
        # 2. Calculate time component based on distance and speed
        time_component = 5  # Minimum time between stations (minutes)
        if distance > 0 and speed > 0:
            time_component = max(5, (distance / speed) * 60)  # Convert to minutes
        
        # 3. Add frequency penalty (less frequent = higher weight)
        frequency_penalty = frequency / 10  # Scale down the effect
        
        # 4. Line type bonus/penalty based on JSON data
        line_type_factor = 1.0
        
        # Check if this is a main line based on name patterns
        main_line_indicators = [
            "Main Line", "Express", "High Speed", "Inter-City"
        ]
        metro_indicators = [
            "Underground", "Metro", "Light Railway", "Subway", "Tram"
        ]
        
        line_lower = line_name.lower()
        
        if any(indicator.lower() in line_lower for indicator in main_line_indicators):
            line_type_factor = 0.7  # Significant bonus for main lines
        elif any(indicator.lower() in line_lower for indicator in metro_indicators):
            line_type_factor = 2.0  # Significant penalty for metro/underground
        
        # 5. Special case for London Underground when main line exists
        if ("london" in station1.lower() and "london" in station2.lower() and
            any(indicator.lower() in line_lower for indicator in metro_indicators)):
            # Extra penalty to avoid Underground for inter-London journeys when main line exists
            line_type_factor = 3.0
        
        # Combine all factors into final weight
        weight = (time_component + frequency_penalty) * line_type_factor
        
        return weight
    
    def _calculate_haversine_distance(self, coord1: Dict, coord2: Dict) -> float:
        """
        Calculate the great-circle distance between two points on Earth using Haversine formula.
        Returns distance in miles.
        """
        import math
        
        # Extract coordinates
        lat1 = coord1.get('lat', 0)
        lon1 = coord1.get('lng', 0)
        lat2 = coord2.get('lat', 0)
        lon2 = coord2.get('lng', 0)
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in miles
        r = 3959
        return c * r
    
    def _find_route_dijkstra(self, from_station: str, to_station: str,
                            graph: Dict[str, Dict[str, float]],
                            station_timetables: Dict[str, Dict[str, Dict]],
                            service_type: str,
                            current_time: Optional[datetime] = None) -> List[str]:
        """
        Find the optimal route using Dijkstra's algorithm.
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            graph: Weighted graph of the railway network
            station_timetables: Timetable data for stations
            service_type: Type of service (Express, Fast, Stopping)
            current_time: Current time for timetable-based routing (optional)
            
        Returns:
            List of station names representing the optimal route
        """
        import heapq
        
        # Adjust weights based on service type
        service_factor = {
            "Express": 0.8,  # Express services prioritize speed
            "Fast": 1.0,     # Fast is the baseline
            "Stopping": 1.2  # Stopping services can use more complex routes
        }.get(service_type, 1.0)
        
        # Check if stations exist in graph
        if from_station not in graph:
            logger.warning(f"Origin station not found in graph: {from_station}")
            return [from_station, to_station]
        
        if to_station not in graph:
            logger.warning(f"Destination station not found in graph: {to_station}")
            return [from_station, to_station]
        
        # Initialize data structures
        distances = {station: float('infinity') for station in graph}
        distances[from_station] = 0
        priority_queue = [(0.0, from_station, 0)]  # (distance, station, interchanges)
        previous: Dict[str, Optional[str]] = {station: None for station in graph}
        interchanges = {station: 0 for station in graph}  # Track number of interchanges
        
        # Dijkstra's algorithm
        while priority_queue:
            current_distance, current_station, current_interchanges = heapq.heappop(priority_queue)
            
            # If we reached the destination, we're done
            if current_station == to_station:
                break
            
            # If we've found a worse path, skip
            if current_distance > distances[current_station]:
                continue
            
            # Check all neighbors
            for neighbor, weight in graph[current_station].items():
                # Apply service type factor to weight
                adjusted_weight = weight * service_factor
                
                # Apply timetable-based adjustments if available
                if current_time and current_station in station_timetables and neighbor in station_timetables:
                    timetable_adjustment = self._calculate_timetable_adjustment(
                        current_station, neighbor, current_time, station_timetables
                    )
                    adjusted_weight = adjusted_weight * timetable_adjustment
                
                # Calculate if this is an interchange
                is_interchange = self._is_interchange_dijkstra(current_station, neighbor)
                new_interchanges = current_interchanges + (1 if is_interchange else 0)
                
                # Apply interchange limit based on service type
                interchange_limits = {"Express": 2, "Fast": 3, "Stopping": 4}
                interchange_limit = interchange_limits.get(service_type, 3)
                
                if new_interchanges > interchange_limit:
                    # Too many interchanges for this service type
                    continue
                
                # Calculate distance through current node
                distance = current_distance + adjusted_weight
                
                # If we found a better path, update
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_station
                    interchanges[neighbor] = new_interchanges
                    heapq.heappush(priority_queue, (float(distance), neighbor, new_interchanges))
        
        # Reconstruct path
        if previous[to_station] is None:
            logger.warning(f"No path found from {from_station} to {to_station}")
            return [from_station, to_station]
        
        path = []
        current = to_station
        while current:
            path.append(current)
            current = previous[current]
        
        # Reverse to get path from origin to destination
        path.reverse()
        
        logger.debug(f"Found route with {len(path)} stations and {interchanges[to_station]} interchanges using Dijkstra's algorithm")
        return path
    
    def _calculate_timetable_adjustment(self, station1: str, station2: str,
                                      current_time: datetime,
                                      station_timetables: Dict[str, Dict[str, Dict]]) -> float:
        """
        Calculate weight adjustment based on timetables.
        Returns a multiplier to apply to the edge weight.
        """
        # Default: no adjustment
        adjustment = 1.0
        
        # Get timetable data for both stations
        station1_timetable = station_timetables.get(station1, {})
        station2_timetable = station_timetables.get(station2, {})
        
        # Find common lines between stations
        common_lines = set(station1_timetable.keys()) & set(station2_timetable.keys())
        
        if not common_lines:
            return adjustment
        
        # Get current hour and minute
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Check each common line for next departure
        min_wait_time = float('infinity')
        
        for line in common_lines:
            # Get departures for this line from station1
            departures = station1_timetable[line].get('departures', [])
            
            for departure in departures:
                try:
                    dep_hour = int(departure.split(':')[0])
                    dep_minute = int(departure.split(':')[1])
                    
                    # Calculate wait time in minutes
                    if dep_hour < current_hour or (dep_hour == current_hour and dep_minute < current_minute):
                        # Departure is earlier today, assume it's for tomorrow
                        wait_time = (24 - current_hour + dep_hour) * 60 + (dep_minute - current_minute)
                    else:
                        # Departure is later today
                        wait_time = (dep_hour - current_hour) * 60 + (dep_minute - current_minute)
                    
                    min_wait_time = min(min_wait_time, wait_time)
                except (ValueError, IndexError):
                    # Skip invalid time formats
                    continue
        
        # Adjust weight based on wait time
        if min_wait_time < float('infinity'):
            # Shorter wait time = better connection
            if min_wait_time <= 5:
                adjustment = 0.8  # Significant bonus for immediate departure
            elif min_wait_time <= 15:
                adjustment = 0.9  # Moderate bonus for short wait
            elif min_wait_time >= 30:
                adjustment = 1.2  # Penalty for long wait
            elif min_wait_time >= 60:
                adjustment = 1.5  # Significant penalty for very long wait
        
        return adjustment
    
    def _is_interchange_dijkstra(self, station1: str, station2: str) -> bool:
        """
        Determine if moving from station1 to station2 constitutes an interchange.
        """
        # Load line data if needed
        line_data = self._load_all_line_data()
        
        # Find which lines each station is on
        station1_lines = set()
        station2_lines = set()
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            station_names = [s.get('name', '') for s in stations]
            
            if station1 in station_names:
                station1_lines.add(line_name)
            
            if station2 in station_names:
                station2_lines.add(line_name)
        
        # Check if stations share any lines
        common_lines = station1_lines & station2_lines
        
        # If stations are on the same line, check if they're adjacent
        if common_lines:
            for line_name in common_lines:
                stations = [s.get('name', '') for s in line_data[line_name].get('stations', [])]
                
                try:
                    idx1 = stations.index(station1)
                    idx2 = stations.index(station2)
                    
                    # If stations are adjacent on this line, it's not an interchange
                    if abs(idx1 - idx2) == 1:
                        return False
                except ValueError:
                    continue
        
        # If stations don't share lines or aren't adjacent on any common line,
        # it's an interchange
        return True
    
    def _filter_stations_by_service_type_improved(self, stations: List[str], service_type: str) -> List[str]:
        """Filter stations based on service type with improved logic."""
        if len(stations) <= 2:  # Always keep origin and destination
            return stations
        
        logger.debug(f"Filtering {len(stations)} stations for {service_type} service: {' -> '.join(stations[:5])}{'...' if len(stations) > 5 else ''}")
        
        # Define filtering rules based on service type
        if service_type == "Express":
            # Express: Keep origin, destination, and major stations only
            # Aim for 5-8 stations total
            if len(stations) <= 8:
                logger.info(f"Express service: keeping all {len(stations)} stations")
                return stations
                
            # Get major stations from JSON data
            major_stations = self._get_major_stations_from_json()
            
            # Always keep origin and destination
            filtered = [stations[0]]
            
            # Keep only major stations in between
            for station in stations[1:-1]:
                if station in major_stations:
                    filtered.append(station)
            
            # If we have too few stations, add some important ones back
            if len(filtered) + 1 < 6:  # +1 for destination, aim for at least 6 stations
                # Add some stations at regular intervals
                remaining = [s for s in stations[1:-1] if s not in filtered]
                step = max(1, len(remaining) // (6 - len(filtered) - 1))
                
                for i in range(0, len(remaining), step):
                    if len(filtered) + 1 < 8:  # +1 for destination, max 8 stations
                        filtered.append(remaining[i])
                    else:
                        break
            
            # Add destination
            filtered.append(stations[-1])
            logger.info(f"Express service: filtered to {len(filtered)} stations")
            return filtered
            
        elif service_type == "Fast":
            # Fast: Keep more stations but still filter
            # Aim for 8-15 stations total
            if len(stations) <= 15:
                logger.info(f"Fast service: keeping all {len(stations)} stations")
                return stations
                
            # Keep origin, destination, and evenly spaced stations
            filtered = [stations[0]]  # Origin
            
            # Keep stations at regular intervals
            step = max(1, (len(stations) - 2) // 12)  # -2 for origin/destination, aim for ~12 intermediate
            
            for i in range(1, len(stations) - 1, step):
                filtered.append(stations[i])
                
            # Add destination
            filtered.append(stations[-1])
            logger.info(f"Fast service: filtered to {len(filtered)} stations")
            return filtered
            
        else:  # Stopping
            # Stopping: Keep most stations but still limit to a reasonable number
            # Aim for 15-25 stations maximum
            if len(stations) <= 25:
                logger.debug(f"Stopping service: keeping all {len(stations)} stations")
                return stations
                
            # Keep origin, destination, and evenly spaced stations
            filtered = [stations[0]]  # Origin
            
            # Keep stations at regular intervals
            step = max(1, (len(stations) - 2) // 20)  # -2 for origin/destination, aim for ~20 intermediate
            
            for i in range(1, len(stations) - 1, step):
                filtered.append(stations[i])
                
            # Add destination
            filtered.append(stations[-1])
            logger.info(f"Stopping service: filtered to {len(filtered)} stations")
            return filtered
    
    def _get_major_stations_from_json(self) -> set:
        """Get major stations from JSON data without hardcoding."""
        major_stations = set()
        line_data = self._load_all_line_data()
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                # Consider a station major if:
                # 1. It has interchanges with other lines
                # 2. It's explicitly marked as major in the JSON
                # 3. It's a terminus station (first or last on a line)
                if (station.get('interchange') or
                    station.get('is_major', False) or
                    station.get('is_terminus', False)):
                    major_stations.add(station.get('name', ''))
        
        # Find stations that appear on multiple lines (junctions/interchanges)
        station_line_count = {}
        for line_name, data in line_data.items():
            for station in data.get('stations', []):
                station_name = station.get('name', '')
                if station_name:
                    station_line_count[station_name] = station_line_count.get(station_name, 0) + 1
        
        # Add stations that appear on multiple lines
        for station_name, count in station_line_count.items():
            if count >= 2:  # Station appears on at least 2 lines
                major_stations.add(station_name)
        
        return major_stations
    
    def _find_geographical_route(self, from_station: str, to_station: str,
                               station_network: Dict[str, Dict], service_type: str) -> List[str]:
        """Find route using Dijkstra's algorithm with weighted edges."""
        
        logger.debug(f"Looking for route from {from_station} to {to_station}")
        
        # Try to find alternative station names if not found
        if from_station not in station_network:
            from_alt = self._find_alternative_station_name(from_station, station_network)
            if from_alt:
                from_station = from_alt
                logger.info(f"Using alternative origin: {from_station}")
            else:
                logger.warning(f"Origin station not found: {from_station}")
                return [from_station, to_station]
                
        if to_station not in station_network:
            to_alt = self._find_alternative_station_name(to_station, station_network)
            if to_alt:
                to_station = to_alt
                logger.info(f"Using alternative destination: {to_station}")
            else:
                logger.warning(f"Destination station not found: {to_station}")
                return [from_station, to_station]
        
        # Build weighted graph for Dijkstra's algorithm
        line_data = self._load_all_line_data()
        weighted_graph, station_timetables = self._build_weighted_graph(line_data)
        
        # Get current time for timetable-based routing
        current_time = datetime.now()
        
        # Find route using Dijkstra's algorithm
        route = self._find_route_dijkstra(
            from_station, to_station, weighted_graph,
            station_timetables, service_type, current_time
        )
        
        if route and len(route) >= 2:
            logger.debug(f"Found route with {len(route)} stations: {' -> '.join(route[:5])}{'...' if len(route) > 5 else ''}")
            return self._filter_stations_by_service_type_improved(route, service_type)
        
        logger.warning(f"No route found, returning direct connection")
        return [from_station, to_station]

    def _follow_railway_lines(self, from_station: str, to_station: str) -> List[str]:
        """Follow railway lines from origin to destination via interchanges."""
        line_data = self._load_all_line_data()
        
        # Build a map of which lines each station is on
        station_to_lines = {}
        line_to_stations = {}
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            line_to_stations[line_name] = [s.get('name', '') for s in stations]
            
            for station in stations:
                station_name = station.get('name', '')
                if station_name not in station_to_lines:
                    station_to_lines[station_name] = []
                station_to_lines[station_name].append(line_name)
        
        # Find which lines the origin and destination are on
        origin_lines = station_to_lines.get(from_station, [])
        dest_lines = station_to_lines.get(to_station, [])
        
        if not origin_lines or not dest_lines:
            logger.warning(f"Could not find lines for {from_station} or {to_station}")
            return [from_station, to_station]
        
        # Try to find a route through the railway network
        route = self._find_route_via_interchanges(
            from_station, to_station, origin_lines, dest_lines,
            station_to_lines, line_to_stations
        )
        
        return route if route else [from_station, to_station]

    def _find_route_via_interchanges(self, from_station: str, to_station: str,
                                   origin_lines: List[str], dest_lines: List[str],
                                   station_to_lines: Dict[str, List[str]],
                                   line_to_stations: Dict[str, List[str]]) -> List[str]:
        """Find route by following lines and switching at interchanges."""
        
        # Check if both stations are on the same line
        common_lines = set(origin_lines) & set(dest_lines)
        if common_lines:
            # Direct route on same line
            line_name = list(common_lines)[0]
            return self._get_stations_between_on_line(from_station, to_station, line_name, line_to_stations)
        
        # Need to find route via interchanges
        # Use BFS to find the shortest interchange route
        from collections import deque
        
        queue = deque([(from_station, [from_station], origin_lines)])
        visited_stations = {from_station}
        
        while queue:
            current_station, path, current_lines = queue.popleft()
            
            # Check if we can reach destination from current station
            for line_name in current_lines:
                if to_station in line_to_stations.get(line_name, []):
                    # Found a line that connects to destination
                    final_segment = self._get_stations_between_on_line(
                        current_station, to_station, line_name, line_to_stations
                    )
                    if final_segment:
                        # Combine path with final segment (avoiding duplicate current station)
                        complete_route = path + final_segment[1:]
                        logger.info(f"Found route via {len(complete_route)} stations")
                        return complete_route
            
            # Look for interchange stations on current lines
            for line_name in current_lines:
                stations_on_line = line_to_stations.get(line_name, [])
                
                for station_name in stations_on_line:
                    if station_name in visited_stations:
                        continue
                        
                    # Check if this station is an interchange (on multiple lines)
                    station_lines = station_to_lines.get(station_name, [])
                    if len(station_lines) > 1:
                        # This is an interchange - add to queue
                        new_path = self._get_stations_between_on_line(
                            current_station, station_name, line_name, line_to_stations
                        )
                        if new_path:
                            complete_path = path + new_path[1:]  # Avoid duplicate current station
                            queue.append((station_name, complete_path, station_lines))
                            visited_stations.add(station_name)
        
        logger.warning(f"No interchange route found from {from_station} to {to_station}")
        return []

    def _get_stations_between_on_line(self, from_station: str, to_station: str,
                                    line_name: str, line_to_stations: Dict[str, List[str]]) -> List[str]:
        """Get all stations between two stations on a specific line."""
        stations_on_line = line_to_stations.get(line_name, [])
        
        try:
            from_idx = stations_on_line.index(from_station)
            to_idx = stations_on_line.index(to_station)
        except ValueError:
            return []
        
        # Get stations in the correct direction
        if from_idx < to_idx:
            return stations_on_line[from_idx:to_idx + 1]
        else:
            return stations_on_line[to_idx:from_idx + 1][::-1]
    
    def _filter_stations_by_service_type(self, stations: List[str], service_type: str) -> List[str]:
        """Filter stations based on service type but ensure we don't skip important intermediate stations."""
        if len(stations) <= 2:  # Always keep origin and destination
            return stations
        
        # Get interchange stations from JSON data to ensure we keep important connections
        interchange_stations = self._get_interchange_stations_from_json()
            
        if service_type == "Express":
            # Express: Keep major interchange stations and some intermediate stations
            filtered = [stations[0]]  # Keep origin
            for station in stations[1:-1]:
                if station in interchange_stations or self._is_major_station_from_json(station):
                    filtered.append(station)
            filtered.append(stations[-1])  # Keep destination
            return filtered
            
        elif service_type == "Fast":
            # Fast: Keep most stations but skip some minor ones
            filtered = [stations[0]]  # Keep origin
            for i in range(1, len(stations) - 1):
                station = stations[i]
                # Always keep interchange stations, skip every 3rd non-interchange station
                if station in interchange_stations or i % 3 != 0:
                    filtered.append(station)
            filtered.append(stations[-1])  # Keep destination
            return filtered
            
        else:  # Stopping
            # Stopping: Keep all stations - this is the most realistic
            return stations

    def _get_interchange_stations_from_json(self) -> set:
        """Get all stations that have interchange connections from JSON data."""
        interchange_stations = set()
        line_data = self._load_all_line_data()
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                if station.get('interchange'):
                    interchange_stations.add(station.get('name', ''))
        
        return interchange_stations

    def _is_major_station_from_json(self, station_name: str) -> bool:
        """Check if a station is major based on JSON data (multiple lines or large interchange)."""
        line_data = self._load_all_line_data()
        lines_count = 0
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                if station.get('name', '') == station_name:
                    lines_count += 1
                    # If station has many interchange connections, it's major
                    if len(station.get('interchange', [])) >= 3:
                        return True
        
        # Station appears on multiple lines = major station
        return lines_count >= 2
    

    def _create_station_mapping(self) -> Dict[str, str]:
        """Create mapping from station codes to full station names using JSON data."""
        mapping = {}
        
        # Load all line data to build comprehensive station mapping
        line_data = self._load_all_line_data()
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                code = station.get('code', '')
                name = station.get('name', '')
                if code and name:
                    mapping[code] = name
        
        logger.debug(f"Built dynamic station mapping with {len(mapping)} stations from JSON data")
        return mapping

    def _calculate_realistic_travel_time(self, from_station: str, to_station: str, service_type: str) -> int:
        """Calculate realistic travel time between two stations using JSON data."""
        # Load all line data to find journey times
        line_data = self._load_all_line_data()
        
        # Look for journey times in the JSON data
        for line_name, data in line_data.items():
            journey_times = data.get('typical_journey_times', {})
            
            # Try to find station codes for the given station names
            from_code = self._find_station_code(from_station, data)
            to_code = self._find_station_code(to_station, data)
            
            if from_code and to_code:
                # Try direct journey time
                journey_key = f"{from_code}-{to_code}"
                if journey_key in journey_times:
                    base_time = journey_times[journey_key]
                    return self._adjust_time_for_service_type(base_time, service_type)
                
                # Try reverse direction
                reverse_key = f"{to_code}-{from_code}"
                if reverse_key in journey_times:
                    base_time = journey_times[reverse_key]
                    return self._adjust_time_for_service_type(base_time, service_type)
        
        # Fallback: estimate based on geographical distance if coordinates available
        distance = self._calculate_station_distance(from_station, to_station)
        if distance > 0:
            # Rough estimate: 1 mile per minute for stopping, faster for express
            speed_multiplier = {"Express": 1.5, "Fast": 1.2, "Stopping": 1.0}
            return max(5, int(distance * speed_multiplier.get(service_type, 1.0)))
        
        # Final fallback based on service type
        default_times = {"Express": 15, "Fast": 20, "Stopping": 25}
        return default_times.get(service_type, 20)

    def _find_station_code(self, station_name: str, line_data: Dict) -> Optional[str]:
        """Find station code for a given station name in line data."""
        stations = line_data.get('stations', [])
        for station in stations:
            if station.get('name', '').lower() == station_name.lower():
                return station.get('code', '')
        return None

    def _adjust_time_for_service_type(self, base_time: int, service_type: str) -> int:
        """Adjust base journey time based on service type."""
        multipliers = {"Express": 0.8, "Fast": 0.9, "Stopping": 1.1}
        return max(1, int(base_time * multipliers.get(service_type, 1.0)))

    def _calculate_station_distance(self, from_station: str, to_station: str) -> float:
        """Calculate approximate distance between stations using coordinates."""
        import math
        
        line_data = self._load_all_line_data()
        from_coords = None
        to_coords = None
        
        # Find coordinates for both stations
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                if station.get('name', '').lower() == from_station.lower():
                    from_coords = station.get('coordinates', {})
                elif station.get('name', '').lower() == to_station.lower():
                    to_coords = station.get('coordinates', {})
        
        if not from_coords or not to_coords:
            return 0
        
        # Calculate distance using Haversine formula (approximate)
        lat1, lng1 = from_coords.get('lat', 0), from_coords.get('lng', 0)
        lat2, lng2 = to_coords.get('lat', 0), to_coords.get('lng', 0)
        
        if not all([lat1, lng1, lat2, lng2]):
            return 0
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in miles (approximately)
        r = 3959
        return c * r

    def _get_station_stop_time(self, station_name: str) -> int:
        """Get realistic stop time for a station based on JSON interchange data."""
        line_data = self._load_all_line_data()
        
        # Check if station has interchange connections in JSON data
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                if station.get('name', '').lower() == station_name.lower():
                    interchange_lines = station.get('interchange', [])
                    if interchange_lines:
                        # Interchange stations get longer stops
                        return 2 if len(interchange_lines) >= 2 else 1
        
        # Default stop time for non-interchange stations
        return 1

    def _find_alternative_station_name(self, station_name: str, station_network: Dict[str, Dict]) -> Optional[str]:
        """Find alternative station name in the network using fuzzy matching."""
        station_lower = station_name.lower()
        
        # Try exact partial matches first
        for network_station in station_network.keys():
            if station_lower in network_station.lower() or network_station.lower() in station_lower:
                return network_station
        
        # Try common variations
        variations = {
            'manchester': 'Manchester Piccadilly',
            'birmingham': 'Birmingham New Street',
            'bristol': 'Bristol Temple Meads',
            'london waterloo': 'London Waterloo',
            'london paddington': 'London Paddington',
            'farnborough': 'Farnborough (Main)'
        }
        
        for variation, full_name in variations.items():
            if variation in station_lower and full_name in station_network:
                return full_name
        
        return None

    def _get_route_from_json_data(self, from_station: str, to_station: str, service_type: str) -> List[str]:
        """Get route using only JSON data - no hardcoded fallbacks."""
        # Load all line data
        line_data = self._load_all_line_data()
        if not line_data:
            return [from_station, to_station]
        
        # Build station network
        station_network = self._build_station_network(line_data)
        
        # Find route using breadth-first search
        route = self._find_geographical_route(from_station, to_station, station_network, service_type)
        
        if route and len(route) >= 2:
            return route
        
        # If no route found, return just origin and destination
        logger.warning(f"No route found in JSON data from {from_station} to {to_station}")
        return [from_station, to_station]

    async def _fetch_trains_from_api(self) -> List[TrainData]:
        """Fallback method to fetch train data from API."""
        # Initialize API manager if needed
        if self.api_manager is None:
            await self.initialize_api()

        if self.api_manager is None:
            raise Exception("API manager not available")

        # Fetch data using context manager
        async with self.api_manager as api:
            trains = await api.get_departures()
            return trains

    def _process_train_data(self, trains: List[TrainData]) -> List[TrainData]:
        """
        Process raw train data.

        Args:
            trains: Raw train data from API

        Returns:
            List[TrainData]: Processed and filtered train data
        """
        # Filter by status - never show cancelled trains
        filtered_trains = filter_trains_by_status(
            trains, include_cancelled=False
        )

        # Sort by departure time
        sorted_trains = sort_trains_by_departure(filtered_trains)

        # Limit to max trains
        limited_trains = sorted_trains[: self.config.display.max_trains]

        logger.debug(f"Processed {len(trains)} -> {len(limited_trains)} trains")
        return limited_trains

    def get_current_trains(self) -> List[TrainData]:
        """
        Get currently loaded train data.

        Returns:
            List[TrainData]: Current train data
        """
        return self.current_trains.copy()

    def get_last_update_time(self) -> Optional[datetime]:
        """
        Get timestamp of last successful update.

        Returns:
            Optional[datetime]: Last update time or None
        """
        return self.last_update

    def get_train_count(self) -> int:
        """
        Get number of currently loaded trains.

        Returns:
            int: Number of trains
        """
        return len(self.current_trains)

    def get_stats(self) -> dict:
        """
        Get statistics about current train data.

        Returns:
            dict: Train statistics
        """
        return calculate_journey_stats(self.current_trains)

    def find_train_by_uid(self, train_uid: str) -> Optional[TrainData]:
        """
        Find train by UID.

        Args:
            train_uid: Train UID to search for

        Returns:
            Optional[TrainData]: Found train or None
        """
        for train in self.current_trains:
            if train.train_uid == train_uid:
                return train
        return None

    def find_train_by_service_id(self, service_id: str) -> Optional[TrainData]:
        """
        Find train by service ID.

        Args:
            service_id: Service ID to search for

        Returns:
            Optional[TrainData]: Found train or None
        """
        for train in self.current_trains:
            if train.service_id == service_id:
                return train
        return None

    def clear_data(self):
        """Clear all train data."""
        self.current_trains.clear()
        self.last_update = None
        self.trains_updated.emit([])
        logger.info("Train data cleared")

    def _build_station_relationships_from_json(self) -> Dict[str, Dict]:
        """Build station relationships dynamically from JSON data."""
        relationships = {}
        line_data = self._load_all_line_data()
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                station_name = station.get('name', '')
                coordinates = station.get('coordinates', {})
                interchange = station.get('interchange', [])
                
                if station_name:
                    # Determine region based on coordinates (rough approximation)
                    lat = coordinates.get('lat', 0)
                    region = "unknown"
                    if lat > 53:
                        region = "north"
                    elif lat > 52:
                        region = "midlands"
                    elif lat > 51.5:
                        region = "central"
                    else:
                        region = "south"
                    
                    # Priority based on number of interchange lines
                    priority = len(interchange) if interchange else 1
                    
                    relationships[station_name] = {
                        "region": region,
                        "priority": min(priority, 5)  # Cap at 5
                    }
        
        return relationships

    # Auto-refresh methods removed as obsolete
