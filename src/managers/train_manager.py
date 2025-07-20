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
import threading
from datetime import datetime
from typing import List, Optional

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
        
        # Route state
        self.from_station: Optional[str] = None
        self.to_station: Optional[str] = None
        self.route_path: Optional[List[str]] = None
        
        # Initialize services
        self._initialize_services(config)
        
        # Load route path from config if available
        self._load_route_from_config()
        
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

    def _load_route_from_config(self) -> None:
        """Load route path from configuration."""
        route_path = self.configuration_service.get_route_path_from_config()
        if route_path:
            self.route_path = route_path
            logger.info(f"Loaded route path from config with {len(route_path)} stations")

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
        old_path = self.route_path
        
        self.from_station = from_station
        self.to_station = to_station
        
        # Update route path and persist
        if route_path is not None:
            self.route_path = route_path
            self.configuration_service.set_route_path(from_station, to_station, route_path)
        else:
            self.route_path = None
            self.configuration_service.set_route_path(from_station, to_station, None)
        
        logger.info(f"Route set: {self.from_station} -> {self.to_station}")
        
        # Trigger refresh if route changed
        if old_from != from_station or old_to != to_station or old_path != self.route_path:
            logger.info("Route changed, triggering refresh")
            self.fetch_trains()

    # API initialization method removed - now using static data generation

    def fetch_trains(self) -> None:
        """Fetch train data asynchronously."""
        if self.is_fetching:
            logger.warning("Fetch already in progress, skipping")
            return

        # Run async fetch using QTimer to integrate with Qt event loop
        QTimer.singleShot(0, self._start_async_fetch)

    def _start_async_fetch(self) -> None:
        """Start async fetch in a way compatible with Qt."""
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

    async def _fetch_trains_async(self) -> None:
        """Async method to fetch train data."""
        if self.is_fetching:
            return

        self.is_fetching = True
        self.status_changed.emit("Loading train data...")

        try:
            # Check if we have valid station configuration
            if not self.configuration_service.has_valid_station_config():
                logger.info("No valid station configuration - showing empty train list")
                self._emit_empty_results()
                return

            # Fetch trains using services
            trains = await self._fetch_trains_from_services()
            
            if trains:
                logger.info("Successfully fetched trains using services")
            else:
                logger.warning("No trains returned from services")

            # Process the data
            processed_trains = self.train_data_service.process_train_data(trains)

            # Update state and emit signals
            self._update_state_and_emit(processed_trains)

        except Exception as e:
            error_msg = f"Error loading train data: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "Error")

        finally:
            self.is_fetching = False

    async def _fetch_trains_from_services(self) -> List[TrainData]:
        """Fetch train data using service layer."""
        if not self.from_station or not self.to_station:
            logger.warning(f"No route configured - from_station: {self.from_station}, to_station: {self.to_station}")
            return []

        logger.info(f"Fetching trains from {self.from_station} to {self.to_station}")

        # Try timetable service first
        if self.timetable_service.is_available():
            trains = self.timetable_service.fetch_trains_from_timetable(
                self.from_station, self.to_station
            )
            if trains:
                return trains

        # Generate trains from route calculation
        return await self._generate_trains_from_route()

    async def _generate_trains_from_route(self) -> List[TrainData]:
        """Generate trains from route calculation."""
        if not self.from_station or not self.to_station:
            return []
            
        # Get route preferences
        preferences = self.configuration_service.get_route_preferences()
        
        # Calculate route
        route_result = self.route_calculation_service.calculate_route(
            self.from_station, self.to_station, preferences
        )
        
        if not route_result:
            logger.warning(f"No route found from {self.from_station} to {self.to_station}")
            return []

        # Store route path for future use
        if hasattr(route_result, 'full_path') and route_result.full_path:
            self.route_path = route_result.full_path
            # Persist to config
            self.configuration_service.set_route_path(
                self.from_station, self.to_station, self.route_path
            )

        # Generate trains from route
        departure_time = datetime.now()
        max_trains = self.configuration_service.get_max_trains_limit()
        
        trains = self.train_data_service.generate_trains_from_route(
            route_result, self.from_station, self.to_station, departure_time, max_trains
        )

        logger.info(f"Generated {len(trains)} trains from route calculation")
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
        self.current_trains = processed_trains
        self.last_update = datetime.now()

        # Emit signals
        self.trains_updated.emit(processed_trains)
        self.connection_changed.emit(True, "Connected (Offline)")
        self.last_update_changed.emit(self.last_update.strftime("%H:%M:%S"))

        # Generate status message
        stats = calculate_journey_stats(processed_trains)
        status_msg = f"Updated: {len(processed_trains)} trains loaded"
        if stats["delayed"] > 0:
            status_msg += f", {stats['delayed']} delayed"
        if stats["cancelled"] > 0:
            status_msg += f", {stats['cancelled']} cancelled"

        self.status_changed.emit(status_msg)
        logger.info(f"Successfully loaded {len(processed_trains)} trains")

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
