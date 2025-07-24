"""
Refactored train data management for the Train Times application.

This module coordinates train data fetching, processing, and updates using
a service-oriented architecture for better maintainability and testability.

The original monolithic TrainManager (3,120 lines) has been refactored into:
- RouteCalculationService: Route finding and validation
- TrainDataService: Train data generation and processing  
- ConfigurationService: Configuration management
- TimetableService: Timetable data handling
"""

import asyncio
import logging
import signal
import sys
import threading
from collections import deque
from datetime import datetime
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, Signal, QTimer

from ..models.train_data import TrainData
from ..managers.config_manager import ConfigData
from ..core.services.service_factory import ServiceFactory
from ..core.interfaces.i_route_service import IRouteService
from ..core.interfaces.i_station_service import IStationService
from ..utils.helpers import calculate_journey_stats

from .services.route_calculation_service import RouteCalculationService
from .services.train_data_service import TrainDataService
from .services.configuration_service import ConfigurationService
from .services.timetable_service import TimetableService

logger = logging.getLogger(__name__)


class TrainManager(QObject):
    """
    Refactored train manager using service-oriented architecture.

    Coordinates between services and UI components to provide
    real-time train information with automatic refresh capabilities.
    
    This replaces the original 3,120-line monolithic class with a focused
    coordinator that delegates responsibilities to specialized services.
    """

    # Signals (maintained for backward compatibility)
    trains_updated = Signal(list)  # List[TrainData]
    error_occurred = Signal(str)  # Error message
    status_changed = Signal(str)  # Status message
    connection_changed = Signal(bool, str)  # Connected, message
    last_update_changed = Signal(str)  # Last update timestamp

    def __init__(self, config: ConfigData):
        """
        Initialize refactored train manager.

        Args:
            config: Application configuration
        """
        super().__init__()
        
        # Core state
        self.current_trains: List[TrainData] = []
        self.last_update: Optional[datetime] = None
        self.is_fetching = False
        
        # Thread synchronization and queue management
        self._fetch_lock = threading.Lock()
        self._fetch_queue: deque = deque(maxlen=1)  # Only keep the most recent request
        self._queue_lock = threading.Lock()
        
        # Route state
        self.from_station: Optional[str] = None
        self.to_station: Optional[str] = None
        # Note: route_path removed - UI should get route data directly from RouteService
        
        # Initialize services
        self._initialize_services(config)
        
        # Note: No longer loading route_path from config - UI gets route data from RouteService
        
        logger.info("Refactored TrainManager initialized with service-oriented architecture")

    def _initialize_services(self, config: ConfigData) -> None:
        """Initialize all services."""
        # Initialize core services
        try:
            service_factory = ServiceFactory()
            station_service: Optional[IStationService] = service_factory.get_station_service()
            route_service: Optional[IRouteService] = service_factory.get_route_service()
            logger.info("Core services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            station_service = None
            route_service = None

        # Initialize service layer
        self.route_calculation_service = RouteCalculationService(route_service, station_service)
        self.train_data_service = TrainDataService(config)
        self.configuration_service = ConfigurationService(config, self.__class__.config_manager)
        self.timetable_service = TimetableService()

    # Note: _load_route_from_config removed - UI gets route data directly from RouteService

    # Reference to config_manager for direct access (maintained for compatibility)
    config_manager = None

    def update_config(self, config: ConfigData) -> None:
        """Update configuration across all services."""
        self.configuration_service.update_config(config)
        self.train_data_service.config = config

    def set_route(self, from_station: str, to_station: str, route_path: Optional[List[str]] = None) -> None:
        """Set the current route and trigger refresh."""
        old_from = self.from_station
        old_to = self.to_station
        
        self.from_station = from_station
        self.to_station = to_station
        
        # Note: No longer storing route_path - UI gets route data directly from RouteService
        # Just persist the from/to stations for configuration
        self.configuration_service.set_route_path(from_station, to_station, None)
        
        # Don't trigger automatic refresh here - let the UI handle refresh timing
        # This prevents multiple concurrent fetches during rapid route switching
        if old_from != from_station or old_to != to_station:
            logger.debug("Route changed, but NOT triggering automatic fetch to prevent overload")

    # API initialization method removed - now using static data generation

    def fetch_trains(self) -> None:
        """Fetch train data asynchronously using queue mechanism."""
        try:
            # Add fetch request to queue (only keeps most recent due to maxlen=1)
            with self._queue_lock:
                fetch_request = (self.from_station, self.to_station, datetime.now())
                self._fetch_queue.append(fetch_request)

            # Start processing if not already running
            if not self.is_fetching:
                # ULTIMATE CRASH FIX: Eliminate QTimer.singleShot entirely - call directly
                # The QTimer.singleShot was causing delayed execution that could happen after widget destruction
                try:
                    # Check if manager is still valid before calling _process_fetch_queue
                    if hasattr(self, '_fetch_queue') and hasattr(self, 'is_fetching'):
                        try:
                            # Test object validity
                            _ = self.objectName()
                            self._process_fetch_queue()
                        except RuntimeError as e:
                            logger.error(f"TrainManager destroyed before queue processing: {e}")
                        except Exception as e:
                            logger.error(f"Error in queue processing: {e}")
                    else:
                        logger.error("TrainManager attributes missing, skipping queue processing")
                except Exception as e:
                    logger.error(f"Exception in direct queue processing: {e}")
            
        except Exception as e:
            logger.error(f"Exception in fetch_trains: {e}", exc_info=True)
            raise

    def _process_fetch_queue(self) -> None:
        """Process the fetch queue and execute the most recent request."""
        with self._queue_lock:
            if not self._fetch_queue:
                logger.debug("Queue is empty, nothing to process")
                return
            
            # Get the most recent request (queue only keeps 1 item due to maxlen=1)
            fetch_request = self._fetch_queue.popleft()
            from_station, to_station, timestamp = fetch_request
            
        logger.debug(f"Processing queued fetch: {from_station} -> {to_station}")
        
        # Update current route if it changed
        if self.from_station != from_station or self.to_station != to_station:
            self.from_station = from_station
            self.to_station = to_station
            logger.debug(f"Updated route to: {self.from_station} -> {self.to_station}")
        
        # Start the actual fetch
        self._start_async_fetch()

    def _start_async_fetch(self) -> None:
        """Start async fetch in a way compatible with Qt."""
        def run_async():
            # Use threading lock to prevent concurrent fetches
            if not self._fetch_lock.acquire(blocking=False):
                logger.warning("Another fetch is already in progress, skipping")
                return
                
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
            finally:
                # Always release the lock
                self._fetch_lock.release()

        # Run in separate thread
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    async def _fetch_trains_async(self) -> None:
        """Async method to fetch train data."""
        if self.is_fetching:
            return

        self.is_fetching = True
        logger.debug(f"Starting train fetch for {self.from_station} -> {self.to_station}")
        self.status_changed.emit("Loading train data...")

        try:
            logger.debug("About to check station configuration")
            # Check if we have valid station configuration
            if not self.configuration_service.has_valid_station_config():
                logger.debug("No valid station configuration - showing empty train list")
                self._emit_empty_results()
                return

            logger.debug("Station configuration valid, about to fetch trains from services")
            # Fetch trains using services
            trains = await self._fetch_trains_from_services()
            
            logger.debug(f"Fetched {len(trains) if trains else 0} trains from services")
            if trains:
                logger.debug("Successfully fetched trains using services")
            else:
                logger.debug("No trains returned from services")

            logger.debug("About to process train data")
            # Process the data
            processed_trains = self.train_data_service.process_train_data(trains)
            logger.debug(f"Processed {len(processed_trains)} trains")

            logger.debug("About to update state and emit signals")
            # Update state and emit signals
            self._update_state_and_emit(processed_trains)
            logger.debug("Successfully completed train fetch")

        except Exception as e:
            error_msg = f"Error loading train data: {e}"
            logger.error(f"Exception in train fetch: {e}", exc_info=True)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "Error")

        finally:
            logger.debug("Setting is_fetching to False")
            self.is_fetching = False

    async def _fetch_trains_from_services(self) -> List[TrainData]:
        """Fetch train data using service layer."""
        if not self.from_station or not self.to_station:
            logger.debug(f"No route configured - from_station: {self.from_station}, to_station: {self.to_station}")
            return []

        logger.debug(f"Fetching trains from {self.from_station} to {self.to_station}")

        # Try timetable service first
        logger.debug("Checking timetable service availability")
        if self.timetable_service.is_available():
            logger.debug("Timetable service available, fetching from timetable")
            trains = self.timetable_service.fetch_trains_from_timetable(
                self.from_station, self.to_station
            )
            if trains:
                logger.debug(f"Got {len(trains)} trains from timetable service")
                return trains
            else:
                logger.debug("No trains from timetable service")

        # Generate trains from route calculation
        logger.debug("About to generate trains from route calculation")
        return await self._generate_trains_from_route()

    async def _generate_trains_from_route(self) -> List[TrainData]:
        """Generate trains from route calculation."""
        logger.debug("Starting _generate_trains_from_route")
        if not self.from_station or not self.to_station:
            logger.debug("No from/to station, returning empty list")
            return []
            
        logger.debug("Getting route preferences")
        # Get route preferences
        preferences = self.configuration_service.get_route_preferences()
        logger.debug(f"Got preferences: {preferences}")
        
        logger.debug("About to calculate route")
        # Calculate route
        route_result = self.route_calculation_service.calculate_route(
            self.from_station, self.to_station, preferences
        )
        logger.debug("Route calculation completed")
        
        if not route_result:
            logger.debug(f"No route found from {self.from_station} to {self.to_station}")
            return []

        logger.debug("Route found, about to generate trains")

        # Generate trains from route
        departure_time = datetime.now()
        max_trains = self.configuration_service.get_max_trains_limit()
        logger.debug(f"About to generate {max_trains} trains from route")
        
        trains = self.train_data_service.generate_trains_from_route(
            route_result, self.from_station, self.to_station, departure_time, max_trains
        )
        logger.debug(f"Generated {len(trains)} trains from route calculation")

        return trains

    def _emit_empty_results(self) -> None:
        """Emit empty results."""
        self.current_trains = []
        self.last_update = datetime.now()
        self.trains_updated.emit([])
        self.connection_changed.emit(True, "Connected (No Data)")
        self.last_update_changed.emit(self.last_update.strftime("%H:%M:%S"))
        self.status_changed.emit("No station configuration")

    def _update_state_and_emit(self, processed_trains: List[TrainData]) -> None:
        """Update state and emit signals."""
        logger.debug("*** ENTERING _update_state_and_emit - SIGNAL EMISSION POINT ***")
        logger.debug(f"About to update state with {len(processed_trains)} trains")
        
        self.current_trains = processed_trains
        self.last_update = datetime.now()
        logger.debug(f"State updated with {len(processed_trains)} trains")

        # Emit signals with crash detection
        try:
            # CRASH DETECTION: Check if we're in a valid state to emit signals
            from PySide6.QtCore import QCoreApplication
            app = QCoreApplication.instance()
            if app is None:
                logger.error("CRITICAL - No QApplication instance during signal emission!")
                return
            
            logger.debug("About to emit trains_updated signal")
            self.trains_updated.emit(processed_trains)
            logger.debug("trains_updated signal emitted successfully")
            
            logger.debug("About to emit connection_changed signal")
            self.connection_changed.emit(True, "Connected (Offline)")
            logger.debug("connection_changed signal emitted successfully")
            
            logger.debug("About to emit last_update_changed signal")
            self.last_update_changed.emit(self.last_update.strftime("%H:%M:%S"))
            logger.debug("last_update_changed signal emitted successfully")

            # Generate status message
            logger.debug("About to calculate journey stats")
            stats = calculate_journey_stats(processed_trains)
            status_msg = f"Updated: {len(processed_trains)} trains loaded"
            if stats["delayed"] > 0:
                status_msg += f", {stats['delayed']} delayed"
            if stats["cancelled"] > 0:
                status_msg += f", {stats['cancelled']} cancelled"
            logger.debug(f"Generated status message: {status_msg}")

            logger.debug("About to emit status_changed signal")
            self.status_changed.emit(status_msg)
            logger.debug("status_changed signal emitted successfully")
            
            logger.debug(f"*** SUCCESSFULLY COMPLETED _update_state_and_emit with {len(processed_trains)} trains ***")
        except Exception as e:
            logger.error(f"*** EXCEPTION during signal emission: {e} ***", exc_info=True)
            raise

    # Public API methods (maintained for backward compatibility)
    
    def get_current_trains(self) -> List[TrainData]:
        """Get currently loaded train data."""
        return self.current_trains.copy()

    def get_last_update_time(self) -> Optional[datetime]:
        """Get timestamp of last successful update."""
        return self.last_update

    def get_train_count(self) -> int:
        """Get number of currently loaded trains."""
        return len(self.current_trains)

    def get_stats(self) -> dict:
        """Get statistics about current train data."""
        return calculate_journey_stats(self.current_trains)

    def find_train_by_uid(self, train_uid: str) -> Optional[TrainData]:
        """Find train by UID."""
        for train in self.current_trains:
            if train.train_uid == train_uid:
                return train
        return None

    def find_train_by_service_id(self, service_id: str) -> Optional[TrainData]:
        """Find train by service ID."""
        for train in self.current_trains:
            if train.service_id == service_id:
                return train
        return None

    def clear_data(self) -> None:
        """Clear all train data."""
        self.current_trains.clear()
        self.last_update = None
        self.trains_updated.emit([])
        logger.info("Train data cleared")
