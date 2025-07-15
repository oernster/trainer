"""
Train data management for the Train Times application.

This module coordinates fetching train data from the internal database,
processing it, and managing updates. Now uses offline timetable data and new core services.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from PySide6.QtCore import QObject, Signal, QTimer
from ..models.train_data import TrainData, TrainStatus, ServiceType
from ..api.api_manager import APIManager, APIException, NetworkException
from ..managers.config_manager import ConfigData
from ..managers.timetable_manager import TimetableManager
from ..core.services.service_factory import ServiceFactory
from ..core.interfaces.i_route_service import IRouteService
from ..core.interfaces.i_station_service import IStationService
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
        self.route_path: Optional[List[str]] = None
        
        # Load route path from config if available
        if (config and hasattr(config, 'stations') and
            hasattr(config.stations, 'route_path') and
            config.stations.route_path):
            self.route_path = config.stations.route_path
            logger.info(f"Loaded route path from config with {len(self.route_path)} stations")
        # Route path already initialized above

        # Initialize new core services
        try:
            service_factory = ServiceFactory()
            self.station_service: Optional[IStationService] = service_factory.get_station_service()
            self.route_service: Optional[IRouteService] = service_factory.get_route_service()
            logger.info("Core services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            self.station_service = None
            self.route_service = None

        # Initialize timetable manager
        try:
            self.timetable_manager = TimetableManager()
            logger.info("TimetableManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TimetableManager: {e}")
            self.timetable_manager = None

        logger.info("TrainManager initialized")

    def update_config(self, config: ConfigData):
        """Update the configuration and refresh if needed."""
        # Get old time window from configurable preference, fallback to display config
        old_time_window = None
        if self.config:
            old_time_window = getattr(self.config, 'train_lookahead_hours', None)
            if old_time_window is None:
                old_time_window = self.config.display.time_window_hours
        
        self.config = config
        
        # Get new time window from configurable preference, fallback to display config
        new_time_window = getattr(config, 'train_lookahead_hours', None)
        if new_time_window is None:
            new_time_window = config.display.time_window_hours
        
        # If time window changed, log it
        if old_time_window != new_time_window:
            logger.info(f"Time window updated from {old_time_window} to {new_time_window} hours")

    # Reference to config_manager for direct access
    config_manager = None
    
    def set_route(self, from_station: str, to_station: str, route_path: Optional[List[str]] = None):
        """Set the current route for timetable generation and trigger refresh."""
        # Station names are used directly now - no conversion needed
        old_from = self.from_station
        old_to = self.to_station
        old_path = self.route_path
        
        self.from_station = from_station
        self.to_station = to_station
        
        # Store route_path for persistence with enhanced validation
        if route_path is not None:
            # Ensure route_path is a list
            if not isinstance(route_path, list):
                logger.warning(f"Route path is not a list, converting: {route_path}")
                try:
                    # Try to convert to list if it's a string or other type
                    if isinstance(route_path, str):
                        route_path = [s.strip() for s in route_path.split(',')]
                    else:
                        route_path = list(route_path)
                except Exception as e:
                    logger.error(f"Failed to convert route_path to list: {e}")
                    route_path = [from_station, to_station]
            
            # Ensure route_path has at least from and to stations
            if len(route_path) < 2:
                logger.warning(f"Route path too short ({len(route_path)}), fixing")
                if len(route_path) == 1:
                    # Add missing station
                    if route_path[0] == from_station:
                        route_path.append(to_station)
                    else:
                        route_path.insert(0, from_station)
                else:
                    # Empty path, create minimal path
                    route_path = [from_station, to_station]
            
            # Validate route path matches from/to stations
            if route_path[0] != from_station or route_path[-1] != to_station:
                logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                              f"don't match from/to stations ({from_station}, {to_station}) - adjusting")
                # Fix the path to match from/to stations
                if route_path[0] != from_station:
                    route_path[0] = from_station
                if route_path[-1] != to_station:
                    route_path[-1] = to_station
            
            self.route_path = route_path
            logger.info(f"Route path set with {len(route_path)} stations: {' → '.join(route_path)}")
            
            # Update config with the new route path and save it
            if self.config and hasattr(self.config, 'stations'):
                # Ensure route_path is properly serializable
                serializable_path = [str(station) for station in route_path]
                self.config.stations.route_path = serializable_path
                logger.info(f"Updated config with new route path: {len(serializable_path)} stations")
                
                # Save the config to disk using the provided config manager
                try:
                    # Try to use the class-level config_manager if available
                    if self.__class__.config_manager:
                        # Check if force_flush is available
                        if hasattr(self.__class__.config_manager, 'save_config') and 'force_flush' in self.__class__.config_manager.save_config.__code__.co_varnames:
                            self.__class__.config_manager.save_config(self.config, force_flush=True)
                            logger.info("Saved config with new route path to disk using shared config manager (force_flush=True)")
                        else:
                            self.__class__.config_manager.save_config(self.config)
                            logger.info("Saved config with new route path to disk using shared config manager")
                        
                        # Verify the route path was saved correctly
                        try:
                            saved_config = self.__class__.config_manager.load_config()
                            if (hasattr(saved_config, 'stations') and
                                hasattr(saved_config.stations, 'route_path') and
                                saved_config.stations.route_path):
                                saved_path = saved_config.stations.route_path
                                logger.info(f"Verified saved route path: {len(saved_path)} stations")
                            else:
                                logger.warning("Route path not found in saved config")
                        except Exception as e:
                            logger.warning(f"Could not verify saved route path: {e}")
                    else:
                        # Fall back to creating a new config manager
                        from .config_manager import ConfigManager
                        config_manager = ConfigManager()
                        config_manager.save_config(self.config, force_flush=True)
                        logger.info("Saved config with new route path to disk using new config manager")
                except Exception as e:
                    logger.error(f"Failed to save config with new route path: {e}")
        else:
            # Clear route path if invalid
            self.route_path = None
            
            # Also clear in config if available
            if self.config and hasattr(self.config, 'stations'):
                self.config.stations.route_path = []
                logger.info("Cleared route path in config")
        
        logger.info(f"Route set: {self.from_station} -> {self.to_station}")
        
        # If route actually changed, trigger a refresh
        if old_from != from_station or old_to != to_station or old_path != self.route_path:
            logger.info(f"Route changed, triggering refresh")
            self.fetch_trains()

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
                logger.info("Successfully fetched trains from offline timetable")
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

            logger.info(f"Successfully loaded {len(processed_trains)} trains")

        except Exception as e:
            error_msg = f"Error loading train data: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "Error")

        finally:
            self.is_fetching = False

    async def _fetch_trains_from_timetable(self) -> List[TrainData]:
        """Fetch train data using core services - NO FALLBACKS."""
        # Get current route
        if not self.from_station or not self.to_station:
            logger.warning(f"No route configured - from_station: {self.from_station}, to_station: {self.to_station}")
            return []
        
        logger.info(f"Fetching trains from {self.from_station} to {self.to_station}")
        
        # Check if config has proper station data
        if (not self.config or
            not hasattr(self.config, 'stations') or
            not self.config.stations or
            not getattr(self.config.stations, 'from_name', None) or
            not getattr(self.config.stations, 'to_name', None)):
            logger.info("No valid station configuration - showing empty train list")
            return []

        # Use core services only - no fallbacks
        if not self.route_service:
            logger.error("Route service not available - cannot generate trains")
            return []

        # Get preferences from config
        # Note: These preferences are dynamically added to the config object
        # by the SettingsHandler.save_settings method, so we need to check
        # if they exist before accessing them
        preferences = {}
        if hasattr(self.config, 'avoid_walking'):
            # For when avoid_walking is enabled, make it a hard constraint
            # This will fully exclude walking connections from route calculation
            preferences['avoid_walking'] = self.config.avoid_walking
            # Don't use a weight - let the algorithm actually find a non-walking route
            if self.config.avoid_walking:
                preferences['exclude_walking'] = True
            else:
                # When avoid_walking is disabled, just use a weight to prefer non-walking routes
                preferences['walking_weight'] = 10.0  # High weight to prefer non-walking connections
        
        if hasattr(self.config, 'prefer_direct'):
            preferences['prefer_direct'] = self.config.prefer_direct
            
        # Check for current location - safely with getattr
        # Try to look for location data in various potential attributes
        try:
            # Dynamically check for any location-related properties
            for location_attr in ['current_location', 'user_location', 'location']:
                if hasattr(self.config, location_attr):
                    location_value = getattr(self.config, location_attr)
                    if location_value:
                        preferences['near_location'] = location_value
                        logger.info(f"Using user location from config.{location_attr}")
                        break
            
            # If we have location settings in station config
            if hasattr(self.config, 'stations'):
                stations_config = self.config.stations
                # Look for location in stations config
                for location_attr in ['current_location', 'user_location', 'location']:
                    if hasattr(stations_config, location_attr):
                        location_value = getattr(stations_config, location_attr)
                        if location_value:
                            preferences['near_location'] = location_value
                            logger.info(f"Using user location from config.stations.{location_attr}")
                            break
        except Exception as e:
            # Don't let location errors affect the main functionality
            logger.warning(f"Error processing location data: {e}")
            
        # Calculate route using core services with preferences
        route_result = self.route_service.calculate_route(
            self.from_station,
            self.to_station,
            preferences=preferences
        )
        
        # GENERAL FIX: Validate and correct routes for disconnected lines
        # This ensures that when origin and destination are on different unconnected lines,
        # the route includes all necessary interchange stations
        logger.debug(f"Starting route validation for {self.from_station} -> {self.to_station}")
        
        # CRITICAL FIX: The validation method modifies the route_result in-place
        # We need to ensure we're using the same object that was modified
        self._ensure_valid_interchange_route(route_result)
        
        # route_result has been modified in-place, so we continue using it
        logger.debug("Route validation completed")
        
        # If we got a route result with a full path, store it for future use
        if route_result and hasattr(route_result, 'full_path') and route_result.full_path:
            # Get the route path from the route result and ensure it's a list
            try:
                # First, try to get the route path as a list
                if isinstance(route_result.full_path, list):
                    route_path = route_result.full_path
                else:
                    # If it's not a list, create a minimal path
                    logger.warning(f"Route path is not a list: {type(route_result.full_path)}")
                    route_path = [self.from_station, self.to_station]
                
                # Ensure route_path has at least from and to stations
                if len(route_path) < 2:
                    logger.warning(f"Route path too short ({len(route_path)}), fixing")
                    route_path = [self.from_station, self.to_station]
                
                # Validate route path matches from/to stations
                if route_path[0] != self.from_station or route_path[-1] != self.to_station:
                    logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                                  f"don't match from/to stations ({self.from_station}, {self.to_station}) - adjusting")
                    # Fix the path to match from/to stations
                    route_path[0] = self.from_station
                    route_path[-1] = self.to_station
                
                # Store the validated route path (but don't override the validated route_result)
                self.route_path = route_path
                logger.debug(f"Stored validated route path with {len(self.route_path)} stations")
                
                # Update config with the new route path and save it
                if (self.config and hasattr(self.config, 'stations')):
                    # Ensure route_path is properly serializable
                    serializable_path = [str(station) for station in route_path]
                    self.config.stations.route_path = serializable_path
                    logger.info(f"Updated config with new route path: {len(serializable_path)} stations")
                    
                    # Save the config to disk using the class-level config_manager if available
                    try:
                        if self.__class__.config_manager:
                            # Use force_flush if available
                            if hasattr(self.__class__.config_manager, 'save_config') and 'force_flush' in self.__class__.config_manager.save_config.__code__.co_varnames:
                                self.__class__.config_manager.save_config(self.config, force_flush=True)
                                logger.info("Saved config with new route path to disk using shared config manager (force_flush=True)")
                            else:
                                self.__class__.config_manager.save_config(self.config)
                                logger.info("Saved config with new route path to disk using shared config manager")
                        else:
                            # Fall back to creating a new config manager
                            from .config_manager import ConfigManager
                            config_manager = ConfigManager()
                            config_manager.save_config(self.config, force_flush=True)
                            logger.info("Saved config with new route path to disk using new config manager (force_flush=True)")
                    except Exception as e:
                        logger.error(f"Failed to save config with new route path: {e}")
            except Exception as e:
                logger.error(f"Error processing route path: {e}")
        
        if not route_result:
            logger.warning(f"No route found from {self.from_station} to {self.to_station} using core services")
            
            # Check if we're trying to avoid walking
            avoid_walking = False
            if hasattr(self.config, 'avoid_walking'):
                avoid_walking = self.config.avoid_walking
            
            # Load walking connections dynamically from interchange_connections.json
            walking_connections = self._load_walking_connections()
            
            logger.info(f"Avoid walking preference is set to: {avoid_walking}")
            
            # Use SimpleRouteFinder as a fallback with appropriate settings
            from ..managers.simple_route_finder import simple_finder
            
            # Make sure SimpleRouteFinder is loaded
            if not simple_finder.loaded:
                simple_finder.load_data()
            
            # Implementation that focuses on finding routes ONLY through rail connections in the JSON data
            logger.info(f"Finding route with avoid_walking={avoid_walking}")
            
            # Verify the simple_finder is loaded
            if not simple_finder.loaded:
                simple_finder.load_data()
                if not simple_finder.loaded:
                    logger.error("Could not load data for SimpleRouteFinder - cannot find routes")
                    route_path = [self.from_station, self.to_station]
                else:
                    logger.info("Successfully loaded SimpleRouteFinder data")
            
            # Method to verify if two stations are connected by rail according to JSON data
            def is_rail_connected(station1, station2):
                # Get all lines for both stations
                station1_lines = simple_finder.get_lines_for_station(station1)
                station2_lines = simple_finder.get_lines_for_station(station2)
                
                # Find common lines
                common_lines = set(station1_lines) & set(station2_lines)
                
                for line in common_lines:
                    stations_on_line = simple_finder.get_stations_on_line(line)
                    
                    try:
                        idx1 = stations_on_line.index(station1)
                        idx2 = stations_on_line.index(station2)
                        
                        # Check if stations are adjacent on this line
                        if abs(idx1 - idx2) == 1:
                            return True
                    except ValueError:
                        continue
                
                return False
            
            # Method to verify if a route only uses rail connections
            def is_valid_rail_route(route):
                if not route or len(route) < 2:
                    return False
                    
                for i in range(len(route) - 1):
                    # Check if this segment is a walking connection
                    station_pair = (route[i], route[i+1])
                    reverse_pair = (route[i+1], route[i])
                    
                    # If it's a known walking connection, the route is invalid
                    if station_pair in walking_connections or reverse_pair in walking_connections:
                        logger.debug(f"Found walking segment: {route[i]} → {route[i+1]}")
                        return False
                    
                    # Verify stations are directly connected by rail
                    if avoid_walking and not is_rail_connected(route[i], route[i+1]):
                        logger.debug(f"Segment not directly connected by rail: {route[i]} → {route[i+1]}")
                        return False
                
                return True
            
            # Analyze route complexity based on distance and network
            def estimate_min_changes(from_station, to_station):
                """Estimate minimum changes needed based on network analysis"""
                # Check if stations are on the same line
                from_lines = simple_finder.get_lines_for_station(from_station)
                to_lines = simple_finder.get_lines_for_station(to_station)
                
                # If they share a line, likely 0-1 changes
                if set(from_lines) & set(to_lines):
                    return 0
                
                # Known hubs that often require changes
                hubs = ["London", "Birmingham", "Manchester", "Edinburgh", "Glasgow", "Leeds", "Bristol"]
                
                # If one station is a hub and the other isn't, likely at least 1 change
                is_from_hub = any(hub in from_station for hub in hubs)
                is_to_hub = any(hub in to_station for hub in hubs)
                
                if is_from_hub != is_to_hub:
                    return 1
                
                # Get all interchange stations
                interchanges = simple_finder.find_interchange_stations()
                
                # If both stations are interchanges but not on same line, likely 1-2 changes
                if from_station in interchanges and to_station in interchanges:
                    return 1
                
                # Otherwise assume 2+ changes for disconnected stations
                return 2
            
            # Analyze if a candidate route is realistic given the UK rail network
            def is_realistic_route(route, min_expected_changes):
                if not route or len(route) < 2:
                    return False
                
                # For routes that should have multiple changes, reject suspiciously short routes
                actual_changes = len(route) - 2  # Number of intermediate stations
                
                if min_expected_changes > 0 and actual_changes < min_expected_changes:
                    logger.warning(f"Route with {actual_changes} changes rejected - expected at least {min_expected_changes}")
                    return False
                
                return True
            
            # Search for a valid route using SimpleRouteFinder with increasing change limits
            route_path = None
            best_route = None
            
            # Estimate minimum changes needed
            min_expected_changes = estimate_min_changes(self.from_station, self.to_station)
            logger.info(f"Estimated minimum changes needed: {min_expected_changes}")
            
            # Try finding routes with various numbers of changes
            # Start with min_expected_changes and go up to 9
            for max_changes in range(max(1, min_expected_changes), 10):
                logger.debug(f"Trying SimpleRouteFinder with max_changes={max_changes}")
                
                # Get a candidate route
                candidate_route = simple_finder.find_route_with_changes(
                    self.from_station, self.to_station, max_changes=max_changes
                )
                
                # Skip invalid routes
                if not candidate_route or len(candidate_route) < 2:
                    continue
                
                # Verify the route doesn't contain walking segments when avoid_walking is enabled
                valid_route = True
                if avoid_walking:
                    valid_route = is_valid_rail_route(candidate_route)
                
                # Store as best route if valid (even if we continue searching)
                if valid_route and (not best_route or len(candidate_route) < len(best_route)):
                    best_route = candidate_route
                    logger.debug(f"Updated best route: {len(best_route)} stations with {max_changes} max changes")
                
                # Check if route is realistic based on network analysis
                if valid_route and is_realistic_route(candidate_route, min_expected_changes):
                    route_path = candidate_route
                    logger.info(f"Found valid {'rail-only ' if avoid_walking else ''}route with {len(route_path)} stations and {max_changes} max changes")
                    break
                    
                # If we've found a valid route but it wasn't realistic, keep searching
                # but only up to a reasonable limit
                if max_changes >= min_expected_changes + 3:
                    # We've tried enough additional changes, use the best route found so far
                    if best_route:
                        route_path = best_route
                        logger.info(f"Using best route found after trying {max_changes} max changes")
                        break
            
            # If we couldn't find a route, use the best route found or create a minimal direct path
            if not route_path:
                if best_route:
                    route_path = best_route
                    logger.info(f"Using best route found: {len(route_path)} stations")
                else:
                    logger.warning(f"Could not find a valid {'rail-only' if avoid_walking else ''} route - using direct path")
                    route_path = [self.from_station, self.to_station]
            
            logger.info(f"Final route: {' → '.join(route_path)}")
            
            # Create a minimal route object with the essential properties needed
            from ..core.models.route import Route, RouteSegment
            
            # Use a dataclass-like approach to create a route object
            class MinimalRoute:
                def __init__(self, path, avoid_walking=False):
                    self.full_path = path
                    self.from_station = path[0]
                    self.to_station = path[-1]
                    self.total_journey_time_minutes = 0
                    self.total_distance_km = 0
                    self.changes_required = 0
                    self.segments = []
                    self._is_valid = True
                    
                    # Create segments between each pair of stations
                    for i in range(len(path) - 1):
                        from_stn = path[i]
                        to_stn = path[i+1]
                        
                        # Check if this is a walking connection
                        station_pair = (from_stn, to_stn)
                        is_walking = False
                        distance_km = 10  # Default distance
                        time_minutes = 15  # Default time
                        
                        if station_pair in walking_connections:
                            is_walking = True
                            conn_info = walking_connections[station_pair]
                            distance_km = conn_info.get("distance_km", distance_km)
                            time_minutes = conn_info.get("time_minutes", time_minutes)
                        
                        # If avoid_walking is enabled and this is a walking connection, mark route as invalid
                        if avoid_walking and is_walking:
                            # Mark as invalid but still create the segment for display
                            self._is_valid = False
                        
                        # Create segment
                        segment = MinimalSegment(
                            from_station=from_stn,
                            to_station=to_stn,
                            is_walking=is_walking,
                            distance_km=distance_km,
                            time_minutes=time_minutes
                        )
                        
                        self.segments.append(segment)
                        self.total_journey_time_minutes += time_minutes
                        self.total_distance_km += distance_km
                        
                        # Count changes (each walking segment is a change)
                        if i > 0 and is_walking:
                            self.changes_required += 1
                
                @property
                def intermediate_stations(self):
                    # Return all stations except first and last
                    return self.full_path[1:-1] if len(self.full_path) > 2 else []
                    
                @property
                def is_valid(self):
                    return self._is_valid
            
            # Helper class for segments
            class MinimalSegment:
                def __init__(self, from_station, to_station, is_walking=False, distance_km=10, time_minutes=15):
                    self.from_station = from_station
                    self.to_station = to_station
                    self.line_name = "WALKING" if is_walking else "National Rail"
                    self.journey_time_minutes = time_minutes
                    self.distance_km = distance_km
                    self.is_walking_connection = is_walking
            
            # Check if avoid_walking is enabled
            avoid_walking = False
            if hasattr(self.config, 'avoid_walking'):
                avoid_walking = self.config.avoid_walking
            
            # If avoid_walking is enabled and we found a route that might contain walking segments,
            # try to find an alternative route that doesn't require any walking
            if avoid_walking and any(pair in walking_connections for i in range(len(route_path) - 1)
                                   for pair in [(route_path[i], route_path[i+1])]):
                logger.info("Route contains potential walking segments with avoid_walking enabled, searching for alternative...")
                
                # Implement Dijkstra's algorithm to find a route that avoids walking connections
                # Build a weighted graph with high penalties for walking segments
                graph = {}
                
                # Make sure SimpleRouteFinder is loaded to get the network
                if not simple_finder.loaded:
                    simple_finder.load_data()
                
                # Build a graph based on potential routes with various change counts
                # First, get several potential routes with different numbers of changes
                all_routes = []
                for max_changes in range(2, 7):  # Try with up to 6 changes for maximum coverage
                    potential_route = simple_finder.find_route_with_changes(
                        self.from_station, self.to_station, max_changes=max_changes
                    )
                    if potential_route and len(potential_route) >= 2:
                        all_routes.append(potential_route)
                        logger.debug(f"Found potential route with {len(potential_route)} stations and {max_changes} max changes")
                
                # Extract all station pairs from these routes
                for route in all_routes:
                    for i in range(len(route) - 1):
                        from_stn = route[i]
                        to_stn = route[i+1]
                        
                        # Initialize if not already in graph
                        if from_stn not in graph:
                            graph[from_stn] = {}
                        if to_stn not in graph:
                            graph[to_stn] = {}
                        
                        # Check if this is a walking connection
                        is_walking = (from_stn, to_stn) in walking_connections or (to_stn, from_stn) in walking_connections
                        
                        # If avoid_walking is true, completely exclude walking connections from the graph
                        if avoid_walking and is_walking:
                            logger.debug(f"Excluding walking connection {from_stn} → {to_stn} from routing graph")
                            continue
                        
                        # For non-walking connections or if avoid_walking is false, add to graph
                        weight = 1 # All connections now have the same weight since walking is excluded
                        
                        # Add to graph (bidirectional)
                        graph[from_stn][to_stn] = weight
                        graph[to_stn][from_stn] = weight
                
                # Run Dijkstra's algorithm to find path with lowest weight (avoiding walking)
                import heapq
                
                def dijkstra(graph, start, end):
                    # Initialize
                    distances = {node: float('infinity') for node in graph}
                    distances[start] = 0
                    priority_queue = [(0, start)]
                    previous = {node: None for node in graph}
                    
                    while priority_queue:
                        current_distance, current_node = heapq.heappop(priority_queue)
                        
                        # If we reached the end, we're done
                        if current_node == end:
                            break
                            
                        # If we've found a better path to the current node, skip
                        if current_distance > distances[current_node]:
                            continue
                            
                        # Check all neighbors
                        for neighbor, weight in graph[current_node].items():
                            distance = current_distance + weight
                            
                            # If this path is better, update distance and previous
                            if distance < distances[neighbor]:
                                distances[neighbor] = distance
                                previous[neighbor] = current_node
                                heapq.heappush(priority_queue, (distance, neighbor))
                    
                    # Reconstruct path
                    if distances[end] == float('infinity'):
                        return None  # No path found
                    
                    path = []
                    current = end
                    while current:
                        path.append(current)
                        current = previous[current]
                    
                    # Reverse to get start->end
                    path.reverse()
                    return path
                
                # Find a path using the graph (which now excludes walking connections if avoid_walking=true)
                alternative_path = dijkstra(graph, self.from_station, self.to_station)
                
                if alternative_path and len(alternative_path) >= 2:
                    # Double-check that this alternative path contains no walking segments
                    contains_walking = False
                    for i in range(len(alternative_path) - 1):
                        station_pair = (alternative_path[i], alternative_path[i+1])
                        reverse_pair = (alternative_path[i+1], alternative_path[i])
                        if station_pair in walking_connections or reverse_pair in walking_connections:
                            contains_walking = True
                            logger.warning(f"Walking segment detected: {station_pair[0]} → {station_pair[1]}")
                            break
                    
                    if not contains_walking:
                        # We found a valid route without walking!
                        route_path = alternative_path
                        logger.info(f"Found alternative non-walking route with {len(route_path)} stations using Dijkstra's algorithm")
                        
                        # Log the complete route for debugging
                        logger.info(f"Non-walking route: {' → '.join(route_path)}")
                    else:
                        logger.warning("Alternative route still contains walking connections - this should not happen!")
                else:
                    logger.warning("Could not find alternative route without walking connections")
            
            # Create the route, respecting avoid_walking preference
            route_result = MinimalRoute(route_path, avoid_walking)
            logger.info(f"Created minimal route with {len(route_path)} stations (valid: {route_result.is_valid})")
            
            # If route is invalid with avoid_walking enabled, but user insisted on this preference,
            # we'll still return the route but it will be marked as invalid for UI display

        # Generate realistic train services based on the calculated route
        departure_time = datetime.now()
        
        # Use configurable look-ahead time from preferences, fallback to display config
        time_window_hours = getattr(self.config, 'train_lookahead_hours', None)
        if time_window_hours is None:
            time_window_hours = self.config.display.time_window_hours
        
        # Use a reasonable default that allows for comprehensive coverage
        max_trains = 100  # Allow enough trains for all railway lines
        
        trains = []
        
        # CRITICAL FIX: Store the validated route_result to reuse for all trains
        # This prevents each train from getting a fresh (unvalidated) route result
        validated_route = route_result
        logger.debug(f"Using validated route with full_path: {getattr(validated_route, 'full_path', 'NO FULL_PATH')}")
        
        # Generate trains at realistic intervals (every 8-15 minutes for more trains)
        current_time = departure_time
        train_count = 0
        
        # Increase train frequency to generate more trains (every 8-15 minutes)
        while train_count < max_trains and current_time < departure_time + timedelta(hours=time_window_hours):
            # Create realistic train service based on VALIDATED route (not fresh route)
            train_data = self._create_train_from_route(validated_route, current_time, train_count)
            if train_data:
                trains.append(train_data)
                train_count += 1
            
            # Next train at standard intervals
            interval_minutes = random.randint(10, 20)  # Standard frequency
            current_time += timedelta(minutes=interval_minutes)

        logger.info(f"Generated {len(trains)} realistic trains using core services")
        return trains

    def _create_train_from_route(self, route_result, departure_time: datetime, train_index: int) -> Optional[TrainData]:
        """Create a realistic TrainData object from a route calculation - NO FALLBACKS."""
        try:
            
            # Calculate arrival time based on route total journey time - NO FALLBACKS
            if not route_result.total_journey_time_minutes:
                logger.error(f"Route result has no journey time - cannot create train")
                return None
            
            arrival_time = departure_time + timedelta(minutes=route_result.total_journey_time_minutes)
            
            # Determine service type based on route complexity
            if route_result.changes_required == 0:
                service_type = ServiceType.EXPRESS if route_result.total_distance_km and route_result.total_distance_km > 50 else ServiceType.FAST
            elif route_result.changes_required <= 2:
                service_type = ServiceType.FAST
            else:
                service_type = ServiceType.STOPPING
            
            # Generate realistic operator based on route
            operators = ["Great Western Railway", "South Western Railway", "Southern", "CrossCountry", "Chiltern Railways"]
            operator = operators[train_index % len(operators)]
            
            # Generate unique IDs
            service_id = f"SVC{train_index+1:03d}{departure_time.strftime('%H%M')}"
            train_uid = f"T{train_index+1:05d}"
            
            # Generate platform (1-12)
            platform = str((train_index % 12) + 1)
            
            # All trains are on time
            train_status = TrainStatus.ON_TIME
            delay_minutes = 0
            
            # Calculate journey duration
            journey_duration = arrival_time - departure_time
            
            # Generate calling points from route
            calling_points = self._generate_calling_points_from_route(route_result, departure_time, arrival_time)
            
            train_data = TrainData(
                departure_time=departure_time,
                scheduled_departure=departure_time,
                destination=self.to_station or "Unknown",
                platform=platform,
                operator=operator,
                service_type=service_type,
                status=train_status,
                delay_minutes=delay_minutes,
                estimated_arrival=arrival_time,
                journey_duration=journey_duration,
                current_location=None,
                train_uid=train_uid,
                service_id=service_id,
                calling_points=calling_points,
                route_segments=getattr(route_result, 'segments', [])
            )
            
            # Debug: Log the route segments that are being attached to the train
            if train_data.route_segments:
                logger.debug(f"Attached {len(train_data.route_segments)} route segments to train {service_id}")
                for i, segment in enumerate(train_data.route_segments):
                    segment_from = getattr(segment, 'from_station', 'UNKNOWN')
                    segment_to = getattr(segment, 'to_station', 'UNKNOWN')
                    line_name = getattr(segment, 'line_name', 'UNKNOWN')
                    service_pattern = getattr(segment, 'service_pattern', 'NONE')
                    logger.debug(f"  Segment {i}: {segment_from} -> {segment_to} (line: {line_name}, service_pattern: {service_pattern})")
                    
                    # Additional debug: Check the actual segment object type and attributes
                    logger.debug(f"    Segment type: {type(segment)}")
                    logger.debug(f"    Segment attributes: {dir(segment)}")
                    if hasattr(segment, '__dict__'):
                        logger.debug(f"    Segment dict: {segment.__dict__}")
            else:
                logger.debug(f"No route segments attached to train {service_id}")
            
            return train_data
            
        except Exception as e:
            logger.error(f"Error creating train from route: {e}")
            return None

    def _generate_calling_points_from_route(self, route_result, departure_time: datetime, arrival_time: datetime) -> List:
        """Generate calling points from route calculation - NO FALLBACKS."""
        from ..models.train_data import CallingPoint
        
        calling_points = []
        
        # Add origin
        origin_point = CallingPoint(
            station_name=self.from_station or "Unknown",
            scheduled_arrival=None,
            scheduled_departure=departure_time,
            expected_arrival=None,
            expected_departure=departure_time,
            platform=None,
            is_origin=True,
            is_destination=False
        )
        calling_points.append(origin_point)
        
        # CRITICAL FIX: Always use full_path as the primary source of truth
        # The route validation system updates full_path, so we should extract intermediate stations from it
        intermediate_stations = []
        if route_result and hasattr(route_result, 'full_path') and route_result.full_path:
            full_path = route_result.full_path
            
            # Extract intermediate stations from full_path (this is the corrected route)
            if len(full_path) > 2:
                intermediate_stations = full_path[1:-1]  # Exclude origin and destination
        else:
            # Fallback: try to get from intermediate_stations property
            if route_result and hasattr(route_result, 'intermediate_stations'):
                intermediate_stations = route_result.intermediate_stations or []
        
        # CRITICAL FIX: Also include transfer stations from route segments
        # These are stations where passengers change trains but aren't included in intermediate_stations
        if route_result and hasattr(route_result, 'segments'):
            segments = route_result.segments or []
            transfer_stations = []
            
            # Look for stations that appear as connection points between different train services
            for i, segment in enumerate(segments):
                if hasattr(segment, 'to_station'):
                    station_name = segment.to_station
                    
                    # Check if this station is a transfer point (not already in intermediate_stations)
                    if station_name not in intermediate_stations and station_name != self.from_station and station_name != self.to_station:
                        # Check if this is where passenger changes between different services
                        if i < len(segments) - 1:  # Not the last segment
                            next_segment = segments[i + 1]
                            current_line = getattr(segment, 'line_name', '')
                            next_line = getattr(next_segment, 'line_name', '')
                            
                            # If line changes and it's not a walking connection, this is a transfer station
                            if current_line != next_line and current_line != 'WALKING' and next_line != 'WALKING':
                                transfer_stations.append(station_name)
                                logger.info(f"Found transfer station: {station_name} (change from {current_line} to {next_line})")
            
            # Add transfer stations to intermediate stations in the correct order
            if transfer_stations:
                # Insert transfer stations in the correct position based on route segments
                for transfer_station in transfer_stations:
                    if transfer_station not in intermediate_stations:
                        # Find the correct position to insert this transfer station
                        insert_position = len(intermediate_stations)  # Default to end
                        
                        # Try to find the correct position based on route segments order
                        for i, segment in enumerate(segments):
                            if hasattr(segment, 'to_station') and segment.to_station == transfer_station:
                                # Insert based on segment position
                                insert_position = min(i, len(intermediate_stations))
                                break
                        
                        intermediate_stations.insert(insert_position, transfer_station)
                        logger.info(f"Added transfer station {transfer_station} at position {insert_position}")
            
            logger.info(f"Final intermediate stations including transfers: {intermediate_stations}")
        
        # Add all intermediate stations as calling points
        if intermediate_stations:
            total_journey_time = (arrival_time - departure_time).total_seconds() / 60  # minutes
            
            # Get segments to check for walking connections
            segments = route_result.segments if hasattr(route_result, 'segments') else []
            
            for i, station_name in enumerate(intermediate_stations):
                # Calculate proportional time for this station
                progress = (i + 1) / (len(intermediate_stations) + 1)
                station_time = departure_time + timedelta(minutes=int(total_journey_time * progress))
                
                # Add 2-minute stop
                stop_duration = timedelta(minutes=2)
                
                # Check if this is a walking connection
                is_walking = False
                walking_distance = None
                walking_time = None
                
                # Look for walking segments to/from this station
                for segment in segments:
                    if hasattr(segment, 'line_name') and segment.line_name == 'WALKING':
                        if hasattr(segment, 'from_station') and hasattr(segment, 'to_station'):
                            if segment.from_station == station_name or segment.to_station == station_name:
                                is_walking = True
                                walking_distance = segment.distance_km if hasattr(segment, 'distance_km') else None
                                walking_time = segment.journey_time_minutes if hasattr(segment, 'journey_time_minutes') else None
                                
                                # Calculate walking time based on 4mph if not provided
                                if not walking_time and walking_distance:
                                    # 4mph = 6.44km/h = 0.107km/min
                                    walking_time = int(walking_distance / 0.107)
                                
                                break
                
                # Also check for connections marked with service_pattern="WALKING"
                if not is_walking:
                    for segment in segments:
                        if hasattr(segment, 'service_pattern') and segment.service_pattern == 'WALKING':
                            if hasattr(segment, 'from_station') and hasattr(segment, 'to_station'):
                                if segment.from_station == station_name or segment.to_station == station_name:
                                    is_walking = True
                                    walking_distance = segment.distance_km if hasattr(segment, 'distance_km') else None
                                    walking_time = segment.journey_time_minutes if hasattr(segment, 'journey_time_minutes') else None
                                    
                                    # Calculate walking time based on 4mph if not provided
                                    if not walking_time and walking_distance:
                                        # 4mph = 6.44km/h = 0.107km/min
                                        walking_time = int(walking_distance / 0.107)
                                    
                                    break
                
                # Keep original station name
                display_name = station_name
                
                # Check if avoid_walking preference is enabled
                avoid_walking = False
                if hasattr(self.config, 'avoid_walking'):
                    avoid_walking = self.config.avoid_walking
                
                # If this is a walking connection and avoid_walking is disabled, add walking info
                if is_walking and not avoid_walking:
                    # Find previous station to connect with walking
                    prev_station = None
                    if len(calling_points) > 0:
                        prev_station = calling_points[-1].station_name
                    
                    # Create walking info text
                    walking_text = ""
                    if walking_distance and walking_time:
                        walking_text = f"<font color='#f44336'>Walk {walking_distance:.1f}km ({walking_time}min)</font>"
                    elif walking_distance:
                        walking_text = f"<font color='#f44336'>Walk {walking_distance:.1f}km</font>"
                    else:
                        walking_text = f"<font color='#f44336'>Walking connection</font>"
                    
                    # Insert a special "walking info" calling point between stations
                    if prev_station:
                        # Calculate time for the walking segment
                        walk_time = station_time - timedelta(minutes=int(walking_time or 10))
                        
                        walking_point = CallingPoint(
                            station_name=walking_text,
                            scheduled_arrival=walk_time,
                            scheduled_departure=walk_time,
                            expected_arrival=walk_time,
                            expected_departure=walk_time,
                            platform=None,
                            is_origin=False,
                            is_destination=False
                        )
                        calling_points.append(walking_point)
                        logger.info(f"Added walking text between {prev_station} and {station_name}")
                elif is_walking and avoid_walking:
                    logger.info(f"Skipping walking connection display for {station_name} due to avoid_walking preference")
                
                intermediate_point = CallingPoint(
                    station_name=display_name,
                    scheduled_arrival=station_time,
                    scheduled_departure=station_time + stop_duration,
                    expected_arrival=station_time,
                    expected_departure=station_time + stop_duration,
                    platform=None,
                    is_origin=False,
                    is_destination=False
                )
                calling_points.append(intermediate_point)
        
        # Add destination
        destination_point = CallingPoint(
            station_name=self.to_station or "Unknown",
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
        # Remove hardcoded long distance routes - let core services handle routing
        # The route service should determine intermediate stations based on actual railway data
        return None
    
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

            logger.info(f"Loaded {len(line_data)} railway line data files")
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
                logger.debug(f"Express service: keeping all {len(stations)} stations")
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
                logger.debug(f"Fast service: keeping all {len(stations)} stations")
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
        """Find route using new core services instead of old station database."""
        
        logger.debug(f"Looking for route from {from_station} to {to_station}")
        
        # Use new core services for route finding
        if self.route_service:
            try:
                # Get preferences from config
                # Note: These preferences are dynamically added to the config object
                # by the SettingsHandler.save_settings method, so we need to check
                # if they exist before accessing them
                preferences = {}
                if hasattr(self.config, 'avoid_walking'):
                    preferences['avoid_walking'] = self.config.avoid_walking
                if hasattr(self.config, 'prefer_direct'):
                    preferences['prefer_direct'] = self.config.prefer_direct
                
                # Calculate route using the new route service with preferences
                route_result = self.route_service.calculate_route(from_station, to_station, preferences=preferences)
                
                if route_result and route_result.segments:
                    # Extract station names from route - use the route's intermediate_stations property
                    route = [from_station]  # Start with origin
                    
                    # Add intermediate stations from the route
                    if route_result.intermediate_stations:
                        route.extend(route_result.intermediate_stations)
                    
                    # Add the final destination
                    route.append(to_station)
                    
                    logger.debug(f"Found route with {len(route)} stations: {' -> '.join(route[:5])}{'...' if len(route) > 5 else ''}")
                    return self._filter_stations_by_service_type_improved(route, service_type)
                else:
                    logger.warning(f"No route found via core services")
                    return [from_station, to_station]
                    
            except Exception as e:
                logger.error(f"Error finding route via core services: {e}")
                return [from_station, to_station]
        else:
            logger.error("Route service not available for route finding")
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
        """Create mapping from station codes to full station names using new station service."""
        mapping = {}
        
        # Use the new station service
        if self.station_service:
            try:
                # Get all stations from the station service
                all_stations = self.station_service.get_all_stations()
                
                # Since we removed station codes, just create a simple identity mapping
                # This allows the code to work with station names directly
                for station in all_stations:
                    if station.name:
                        mapping[station.name] = station.name
                
                logger.debug(f"Built station mapping with {len(mapping)} stations from station service")
            except Exception as e:
                logger.error(f"Error building station mapping: {e}")
        else:
            logger.warning("Station service not available, using empty mapping")
        
        return mapping

    def _calculate_realistic_travel_time(self, from_station: str, to_station: str, service_type: str) -> int:
        """Calculate realistic travel time between two stations using JSON data."""
        # Load all line data to find journey times
        line_data = self._load_all_line_data()
        
        # Look for journey times in the JSON data
        for line_name, data in line_data.items():
            journey_times = data.get('typical_journey_times', {})
            
            # Use station names directly
            from_name = from_station
            to_name = to_station
            
            if from_name and to_name:
                # Try direct journey time using station names
                journey_key = f"{from_name}-{to_name}"
                if journey_key in journey_times:
                    base_time = journey_times[journey_key]
                    return self._adjust_time_for_service_type(base_time, service_type)
                
                # Try reverse direction
                reverse_key = f"{to_name}-{from_name}"
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

    def _find_station_name(self, station_name: str, line_data: Dict) -> Optional[str]:
        """Find and validate station name in line data."""
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

    # Removed _find_alternative_station_name method - fuzzy matching should only be used
    # for autocomplete, not for looking up already-configured stations

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

        # Limit to max trains - use same override as generation
        max_trains_limit = 100  # Override cached config
        limited_trains = sorted_trains[: max_trains_limit]

        logger.info(f"Processed {len(trains)} -> {len(limited_trains)} trains")
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

    def _generate_key_interchange_stations(self, from_station: str, to_station: str) -> List[str]:
        """Generate key interchange stations for a route when route service doesn't provide them."""
        # Define major interchange stations and their typical connections
        major_interchanges = {
            "Clapham Junction": {"region": "london", "priority": 1},
            "Birmingham New Street": {"region": "midlands", "priority": 1},
            "Reading": {"region": "south", "priority": 2},
            "Bristol Temple Meads": {"region": "southwest", "priority": 2},
            "Manchester Piccadilly": {"region": "north", "priority": 1},
            "Oxford": {"region": "central", "priority": 3},
            "Crewe": {"region": "northwest", "priority": 2},
            "Preston": {"region": "northwest", "priority": 3},
            "Coventry": {"region": "midlands", "priority": 3},
            "Wolverhampton": {"region": "midlands", "priority": 3},
            "Stafford": {"region": "midlands", "priority": 3},
        }
        
        # Common route patterns with key interchange stations
        route_patterns = {
            ("Fleet", "Manchester Airport"): ["Reading", "Birmingham New Street"],
            ("Fleet", "Manchester"): ["Reading", "Birmingham New Street"],
            ("Fleet", "Birmingham"): ["Reading"],
            ("Fleet", "Bristol"): ["Reading"],
            ("London", "Manchester"): ["Birmingham New Street"],
            ("London", "Birmingham"): ["Reading"],
            ("Birmingham", "Manchester"): ["Stafford"],
            ("Bristol", "Manchester"): ["Birmingham New Street"],
            ("Reading", "Manchester"): ["Birmingham New Street"],
        }
        
        # Try to find a direct pattern match
        route_key = (from_station, to_station)
        if route_key in route_patterns:
            return route_patterns[route_key]
        
        # Try reverse direction
        reverse_key = (to_station, from_station)
        if reverse_key in route_patterns:
            return list(reversed(route_patterns[reverse_key]))
        
        # Try partial matches (e.g., "Manchester Airport" matches "Manchester")
        for (pattern_from, pattern_to), stations in route_patterns.items():
            if (pattern_from in from_station or from_station in pattern_from) and \
               (pattern_to in to_station or to_station in pattern_to):
                return stations
        
        # Fallback: generate based on geographical logic
        interchange_stations = []
        
        # If going from south to north, add key midlands interchange
        if any(south in from_station.lower() for south in ["fleet", "london", "reading", "bristol"]) and \
           any(north in to_station.lower() for north in ["manchester", "birmingham", "coventry"]):
            if "birmingham" not in from_station.lower():
                interchange_stations.append("Birmingham New Street")
        
        # If going through London area, add Clapham Junction
        if "fleet" in from_station.lower() and "manchester" in to_station.lower():
            if "Clapham Junction" not in interchange_stations:
                interchange_stations.insert(0, "Clapham Junction")
        
        return interchange_stations

    def _ensure_valid_interchange_route(self, route_result):
        """
        Ensure that routes between disconnected lines include all necessary interchange stations.
        This is a general solution that analyzes JSON data to detect when stations are on
        different unconnected lines and dynamically finds required interchange stations.
        """
        if not route_result or not self.from_station or not self.to_station:
            return route_result
        
        try:
            # Load line data to analyze station connectivity
            line_data = self._load_all_line_data()
            if not line_data:
                return route_result
            
            # Build station-to-lines mapping
            station_to_lines = {}
            for line_name, data in line_data.items():
                stations = data.get('stations', [])
                for station in stations:
                    station_name = station.get('name', '')
                    if station_name:
                        if station_name not in station_to_lines:
                            station_to_lines[station_name] = []
                        station_to_lines[station_name].append(line_name)
            
            # Get lines for origin and destination
            origin_lines = station_to_lines.get(self.from_station, [])
            dest_lines = station_to_lines.get(self.to_station, [])
            
            # Check if stations share any common lines (direct connection possible)
            common_lines = set(origin_lines) & set(dest_lines)
            
            if common_lines:
                return route_result  # Direct connection is valid
            
            # Stations are on disconnected lines - need to find interchange stations
            logger.debug(f"Disconnected lines detected: {self.from_station} -> {self.to_station}")
            
            # Find stations that can connect the origin and destination lines
            required_interchanges = self._find_required_interchanges(
                origin_lines, dest_lines, station_to_lines
            )
            
            if not required_interchanges:
                return route_result
            
            logger.debug(f"Required interchanges: {required_interchanges}")
            
            # Check if the current route includes the required interchanges
            current_path = []
            if hasattr(route_result, 'full_path') and route_result.full_path:
                current_path = route_result.full_path
            elif hasattr(route_result, 'intermediate_stations') and route_result.intermediate_stations:
                current_path = [self.from_station] + route_result.intermediate_stations + [self.to_station]
            
            # Check if all required interchanges are present
            missing_interchanges = []
            for interchange in required_interchanges:
                if interchange not in current_path:
                    missing_interchanges.append(interchange)
            
            if missing_interchanges:
                logger.debug(f"Missing interchanges: {missing_interchanges}")
                
                # Build a corrected route that includes the missing interchanges
                corrected_path = self._build_corrected_route(
                    self.from_station, self.to_station, required_interchanges,
                    station_to_lines, line_data
                )
                
                if corrected_path and len(corrected_path) >= 2:
                    logger.debug(f"Corrected route: {' -> '.join(corrected_path)}")
                    
                    # Update the route result with the corrected path and segments
                    if route_result:
                        object.__setattr__(route_result, 'full_path', corrected_path)
                        # Use the route service to create proper segments instead of our local method
                        # This ensures that walking segments are properly marked with service_pattern="WALKING"
                        if self.route_service:
                            try:
                                # Calculate a new route with the corrected path to get proper segments
                                preferences = {}
                                if hasattr(self.config, 'avoid_walking'):
                                    preferences['avoid_walking'] = self.config.avoid_walking
                                if hasattr(self.config, 'prefer_direct'):
                                    preferences['prefer_direct'] = self.config.prefer_direct
                                
                                # Get a fresh route calculation with proper segments
                                fresh_route = self.route_service.calculate_route(
                                    corrected_path[0], corrected_path[-1], preferences=preferences
                                )
                                
                                if fresh_route and fresh_route.segments:
                                    object.__setattr__(route_result, 'segments', fresh_route.segments)
                                    logger.debug(f"Updated route with {len(fresh_route.segments)} fresh route service segments")
                                else:
                                    # Fallback to creating segments manually
                                    corrected_segments = self._create_route_segments_from_path(corrected_path, line_data)
                                    object.__setattr__(route_result, 'segments', corrected_segments)
                            except Exception as e:
                                logger.error(f"Error getting fresh route segments: {e}")
                                # Fallback to creating segments manually
                                corrected_segments = self._create_route_segments_from_path(corrected_path, line_data)
                                object.__setattr__(route_result, 'segments', corrected_segments)
                        else:
                            # Fallback to creating segments manually
                            corrected_segments = self._create_route_segments_from_path(corrected_path, line_data)
                            object.__setattr__(route_result, 'segments', corrected_segments)
                        logger.debug(f"Updated route with {len(corrected_path)} stations")
                        logger.debug(f"Updated route segments for corrected path")
                    else:
                        # Create a minimal route object if none exists
                        class CorrectedRoute:
                            def __init__(self, path, segments):
                                self.full_path = path
                                self.from_station = path[0]
                                self.to_station = path[-1]
                                self.intermediate_stations = path[1:-1] if len(path) > 2 else []
                                self.total_journey_time_minutes = len(path) * 10  # Rough estimate
                                self.total_distance_km = len(path) * 15  # Rough estimate
                                self.changes_required = len([s for s in path if s in required_interchanges])
                                self.segments = segments
                        
                        # Create proper route segments with line change information
                        corrected_segments = self._create_route_segments_from_path(corrected_path, line_data)
                        route_result = CorrectedRoute(corrected_path, corrected_segments)
                        logger.critical(f"CREATED NEW ROUTE: {corrected_path}")
            
            return route_result
            
        except Exception as e:
            logger.critical(f"ROUTE VALIDATION ERROR: {e}")
            return route_result
    
    def _find_required_interchanges(self, origin_lines, dest_lines, station_to_lines):
        """Find stations that can serve as interchanges between origin and destination lines."""
        interchange_candidates = []
        
        # Find stations that appear on both origin lines and destination lines
        for station_name, station_lines in station_to_lines.items():
            station_line_set = set(station_lines)
            
            # Check if this station connects origin and destination line networks
            connects_origin = bool(station_line_set & set(origin_lines))
            connects_dest = bool(station_line_set & set(dest_lines))
            
            if connects_origin and connects_dest:
                # This station directly connects origin and destination lines
                interchange_candidates.append((station_name, 1))  # Priority 1 (direct)
            else:
                # Check if this station can serve as an intermediate interchange
                # (connects to origin lines and has connections to destination network)
                if connects_origin:
                    # Check if any of this station's lines connect to destination network
                    for line in station_lines:
                        if self._line_connects_to_network(line, dest_lines, station_to_lines):
                            interchange_candidates.append((station_name, 2))  # Priority 2 (indirect)
                            break
                elif connects_dest:
                    # Check if any of this station's lines connect to origin network
                    for line in station_lines:
                        if self._line_connects_to_network(line, origin_lines, station_to_lines):
                            interchange_candidates.append((station_name, 2))  # Priority 2 (indirect)
                            break
        
        # Sort by priority (lower number = higher priority)
        interchange_candidates.sort(key=lambda x: x[1])
        
        # Return the station names, prioritizing direct connections
        required_interchanges = [station for station, priority in interchange_candidates[:3]]  # Limit to top 3
        
        logger.info(f"Found interchange candidates: {interchange_candidates}")
        logger.info(f"Required interchanges: {required_interchanges}")
        
        return required_interchanges
    
    def _line_connects_to_network(self, line_name, target_lines, station_to_lines):
        """Check if a line connects to any station that serves the target line network."""
        # This is a simplified check - in a full implementation, you might want to
        # build a more sophisticated network graph
        for station_name, station_lines in station_to_lines.items():
            if line_name in station_lines:
                # Check if this station also serves any target lines
                if any(target_line in station_lines for target_line in target_lines):
                    return True
        return False
    
    def _build_corrected_route(self, from_station, to_station, required_interchanges,
                             station_to_lines, line_data):
        """Build a corrected route that includes all required interchange stations."""
        try:
            # Start with origin
            route = [from_station]
            
            # Add intermediate stations from origin to first interchange
            if required_interchanges:
                first_interchange = required_interchanges[0]
                
                # Find path from origin to first interchange
                intermediate_to_first = self._find_path_between_stations(
                    from_station, first_interchange, station_to_lines, line_data
                )
                if intermediate_to_first:
                    route.extend(intermediate_to_first[1:-1])  # Exclude origin and interchange
                
                # Add the interchange station
                route.append(first_interchange)
                
                # Add path from interchange to destination
                intermediate_to_dest = self._find_path_between_stations(
                    first_interchange, to_station, station_to_lines, line_data
                )
                if intermediate_to_dest:
                    route.extend(intermediate_to_dest[1:])  # Exclude interchange, include destination
                else:
                    route.append(to_station)  # Fallback: direct to destination
            else:
                # No interchanges found, direct route
                route.append(to_station)
            
            return route
            
        except Exception as e:
            logger.error(f"Error building corrected route: {e}")
            return [from_station, to_station]
    
    def _create_route_segments_from_path(self, path: List[str], line_data: Dict[str, Dict]) -> List:
        """Create route segments with line change information from a station path.
        Only creates segments at actual line changes, not at every station."""
        if not path or len(path) < 2:
            return []
        
        segments = []
        
        # Define RouteSegment class once at the top
        class RouteSegment:
            def __init__(self, from_station, to_station, line_name, station_count=1, service_pattern=None):
                self.from_station = from_station
                self.to_station = to_station
                self.line_name = line_name
                self.distance_km = 15 * station_count  # Rough estimate
                self.journey_time_minutes = 10 * station_count  # Rough estimate
                self.service_pattern = service_pattern  # Add service_pattern support
        
        # Load station to lines mapping
        station_to_lines = {}
        try:
            for line_name, data in line_data.items():
                stations = data.get('stations', [])
                for station in stations:
                    station_name = station.get('name', '')
                    if station_name:
                        if station_name not in station_to_lines:
                            station_to_lines[station_name] = []
                        station_to_lines[station_name].append(line_name)
        except Exception as e:
            logger.error(f"Error building station to lines mapping: {e}")
            return []
        
        # Find actual line change points in the path
        segment_start = 0
        current_line = None
        
        for i in range(len(path)):
            station = path[i]
            station_lines = set(station_to_lines.get(station, []))
            
            if i == 0:
                # First station - determine the starting line
                if station_lines:
                    current_line = list(station_lines)[0]  # Use first available line
                else:
                    current_line = "Unknown Line"
                logger.debug(f"Starting segment at {station}")
                continue
            
            # Check if this station is still on the current line
            if current_line in station_lines:
                # Still on same line, continue
                continue
            else:
                # Line change detected! Create segment from segment_start to previous station
                segment_end = i - 1
                if segment_end > segment_start:
                    from_station = path[segment_start]
                    to_station = path[segment_end]
                    station_count = segment_end - segment_start
                    
                    # Create segment for the previous line
                    # Check if this is a walking segment
                    service_pattern = "WALKING" if current_line == 'WALKING' else None
                    segment = RouteSegment(from_station, to_station, current_line, station_count, service_pattern)
                    segments.append(segment)
                    logger.debug(f"Created segment: {from_station} → {to_station} (service_pattern: {service_pattern})")
                
                # Start new segment from previous station (the interchange point)
                segment_start = i - 1
                prev_station = path[i - 1]
                
                # Find the new line for this station
                if station_lines:
                    # Find a line that connects the previous station to this station
                    prev_lines = set(station_to_lines.get(prev_station, []))
                    
                    # Look for a line that both stations share
                    common_lines = prev_lines & station_lines
                    if common_lines:
                        current_line = list(common_lines)[0]
                    else:
                        # No common line - this is a true interchange
                        current_line = list(station_lines)[0]
                else:
                    current_line = "Unknown Line"
                
                logger.debug(f"Line change detected at {prev_station}")
        
        # Create final segment to destination
        if segment_start < len(path) - 1:
            from_station = path[segment_start]
            to_station = path[-1]
            station_count = len(path) - 1 - segment_start
            
            # Check if this is a walking segment
            service_pattern = "WALKING" if current_line == 'WALKING' else None
            segment = RouteSegment(from_station, to_station, current_line, station_count, service_pattern)
            segments.append(segment)
            logger.debug(f"Final segment: {from_station} → {to_station} (service_pattern: {service_pattern})")

        logger.debug(f"Created {len(segments)} route segments")
        return segments

    def _find_path_between_stations(self, start_station, end_station, station_to_lines, line_data):
        """Find a path between two stations using the line data."""
        # Find common lines between the stations
        start_lines = station_to_lines.get(start_station, [])
        end_lines = station_to_lines.get(end_station, [])
        
        common_lines = set(start_lines) & set(end_lines)
        
        if common_lines:
            # Stations are on the same line - find the path
            line_name = list(common_lines)[0]  # Use first common line
            line_stations = []
            
            # Get stations from this line
            if line_name in line_data:
                stations = line_data[line_name].get('stations', [])
                line_stations = [s.get('name', '') for s in stations]
            
            # Find path between stations on this line
            try:
                start_idx = line_stations.index(start_station)
                end_idx = line_stations.index(end_station)
                
                if start_idx < end_idx:
                    return line_stations[start_idx:end_idx + 1]
                else:
                    return line_stations[end_idx:start_idx + 1][::-1]
            except ValueError:
                pass
        
        # Fallback: direct connection
        return [start_station, end_station]
    
    def _load_walking_connections(self) -> dict:
        """Load walking connections dynamically from interchange_connections.json."""
        try:
            import json
            from pathlib import Path
            
            # Load interchange connections file
            connections_file = Path(__file__).parent.parent / "data" / "interchange_connections.json"
            
            if not connections_file.exists():
                logger.warning(f"Interchange connections file not found: {connections_file}")
                return {}
            
            with open(connections_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            walking_connections = {}
            
            # Extract walking connections from the JSON data
            for connection in data.get('connections', []):
                if connection.get('connection_type') == 'WALKING':
                    from_station = connection.get('from_station')
                    to_station = connection.get('to_station')
                    # Convert walking_distance_m to distance_km
                    walking_distance_m = connection.get('walking_distance_m', 1000)
                    distance_km = walking_distance_m / 1000.0  # Convert meters to kilometers
                    time_minutes = connection.get('time_minutes', 10)
                    
                    if from_station and to_station:
                        # Add both directions
                        walking_connections[(from_station, to_station)] = {
                            "distance_km": distance_km,
                            "time_minutes": time_minutes
                        }
                        walking_connections[(to_station, from_station)] = {
                            "distance_km": distance_km,
                            "time_minutes": time_minutes
                        }
            
            logger.info(f"Loaded {len(walking_connections)} walking connections from interchange_connections.json")
            return walking_connections
            
        except Exception as e:
            logger.error(f"Error loading walking connections: {e}")
            return {}
    
    # Auto-refresh methods removed as obsolete
