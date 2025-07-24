"""
Station Data Background Worker

Handles asynchronous loading of station data to prevent UI blocking.
This worker loads the full station dataset in the background while keeping
the UI responsive with essential stations.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal, QObject

logger = logging.getLogger(__name__)


class StationDataWorker(QThread):
    """
    Background worker for loading station data asynchronously.
    
    This worker loads the complete station dataset in a background thread
    to prevent blocking the UI during initialization.
    """
    
    # Signals
    data_loading_started = Signal()
    data_loading_progress = Signal(str, int)  # message, percentage
    data_loading_completed = Signal(list)  # complete station list
    data_loading_failed = Signal(str)  # error message
    underground_data_loaded = Signal(list)  # underground stations
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize the station data worker.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._should_stop = False
        self._station_service = None
        self._data_repository = None
        
    def set_services(self, station_service, data_repository):
        """
        Set the services to use for data loading.
        
        Args:
            station_service: Station service instance
            data_repository: Data repository instance
        """
        self._station_service = station_service
        self._data_repository = data_repository
    
    def stop_loading(self):
        """Request the worker to stop loading data."""
        self._should_stop = True
        self.logger.info("Station data worker stop requested")
    
    def run(self):
        """Main worker thread execution."""
        try:
            self.logger.info("Starting background station data loading")
            self.data_loading_started.emit()
            
            start_time = time.time()
            all_stations = []
            
            # Check if we should stop
            if self._should_stop:
                return
            
            # Phase 1: Load National Rail stations
            self.data_loading_progress.emit("Loading National Rail stations...", 10)
            
            if self._station_service:
                try:
                    national_rail_stations = self._station_service.get_all_station_names()
                    all_stations.extend(national_rail_stations)
                    self.logger.info(f"Loaded {len(national_rail_stations)} National Rail stations")
                except Exception as e:
                    self.logger.warning(f"Failed to load National Rail stations: {e}")
            
            if self._should_stop:
                return
            
            # Phase 2: Load Underground stations
            self.data_loading_progress.emit("Loading Underground stations...", 50)
            
            underground_stations = []
            if self._station_service:
                try:
                    # Load underground stations using the existing method
                    all_with_underground = self._station_service.get_all_station_names_with_underground()
                    
                    # Extract just the underground stations by comparing with national rail
                    national_rail_set = set(all_stations)
                    underground_stations = [
                        station for station in all_with_underground 
                        if station not in national_rail_set
                    ]
                    
                    # Add underground stations to the complete list
                    all_stations.extend(underground_stations)
                    
                    self.logger.info(f"Loaded {len(underground_stations)} Underground stations")
                    
                    # Emit underground stations separately for immediate autocomplete enhancement
                    self.underground_data_loaded.emit(underground_stations)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load Underground stations: {e}")
            
            if self._should_stop:
                return
            
            # Phase 3: Remove duplicates and sort
            self.data_loading_progress.emit("Processing station data...", 80)
            
            # Remove duplicates while preserving order preference (National Rail first)
            unique_stations = []
            seen = set()
            for station in all_stations:
                if station and station not in seen:
                    unique_stations.append(station)
                    seen.add(station)
            
            # Sort the final list
            unique_stations.sort()
            
            if self._should_stop:
                return
            
            # Phase 4: Complete
            self.data_loading_progress.emit("Station data loading complete", 100)
            
            load_time = time.time() - start_time
            self.logger.info(f"Background station data loading completed in {load_time:.3f}s")
            self.logger.info(f"Total stations loaded: {len(unique_stations)}")
            
            # Emit the complete station list
            self.data_loading_completed.emit(unique_stations)
            
        except Exception as e:
            self.logger.error(f"Station data worker failed: {e}")
            self.data_loading_failed.emit(str(e))


class FastStationDataWorker(QThread):
    """
    Optimized worker for loading only essential station data quickly.
    
    This worker focuses on loading just the most commonly needed stations
    for immediate UI responsiveness, skipping heavy data processing.
    """
    
    # Signals
    essential_data_loaded = Signal(list)  # essential stations
    loading_failed = Signal(str)  # error message
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize the fast station data worker.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._should_stop = False
    
    def stop_loading(self):
        """Request the worker to stop loading data."""
        self._should_stop = True
    
    def run(self):
        """Main worker thread execution for fast loading."""
        try:
            self.logger.info("Starting fast essential station data loading")
            start_time = time.time()
            
            # Import here to avoid circular imports
            from ...core.services.essential_station_cache import get_essential_stations
            
            if self._should_stop:
                return
            
            # Load essential stations (this should be very fast)
            essential_stations = get_essential_stations()
            
            load_time = time.time() - start_time
            self.logger.info(f"Fast station data loading completed in {load_time:.3f}s")
            self.logger.info(f"Essential stations loaded: {len(essential_stations)}")
            
            # Emit the essential station list
            self.essential_data_loaded.emit(essential_stations)
            
        except Exception as e:
            self.logger.error(f"Fast station data worker failed: {e}")
            self.loading_failed.emit(str(e))


class StationDataManager(QObject):
    """
    Manager for coordinating station data loading operations.
    
    This manager coordinates between fast essential data loading and
    comprehensive background data loading to optimize UI responsiveness.
    """
    
    # Signals
    essential_stations_ready = Signal(list)  # essential stations for immediate use
    full_stations_ready = Signal(list)  # complete station list
    underground_stations_ready = Signal(list)  # underground stations
    loading_progress = Signal(str, int)  # progress updates
    loading_error = Signal(str)  # error messages
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize the station data manager.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Workers
        self._fast_worker: Optional[FastStationDataWorker] = None
        self._full_worker: Optional[StationDataWorker] = None
        
        # Data state
        self._essential_stations: List[str] = []
        self._full_stations: List[str] = []
        self._underground_stations: List[str] = []
        self._is_loading = False
    
    def start_loading(self, station_service=None, data_repository=None):
        """
        Start the coordinated station data loading process.
        
        Args:
            station_service: Station service for full data loading
            data_repository: Data repository for full data loading
        """
        if self._is_loading:
            self.logger.warning("Station data loading already in progress")
            return
        
        self._is_loading = True
        self.logger.info("Starting coordinated station data loading")
        
        # Start fast loading first for immediate UI responsiveness
        self._start_fast_loading()
        
        # Start full loading in parallel for complete data
        if station_service and data_repository:
            self._start_full_loading(station_service, data_repository)
    
    def _start_fast_loading(self):
        """Start fast essential station loading."""
        self._fast_worker = FastStationDataWorker(self)
        self._fast_worker.essential_data_loaded.connect(self._on_essential_data_loaded)
        self._fast_worker.loading_failed.connect(self._on_fast_loading_failed)
        self._fast_worker.start()
    
    def _start_full_loading(self, station_service, data_repository):
        """Start full station data loading."""
        self._full_worker = StationDataWorker(self)
        self._full_worker.set_services(station_service, data_repository)
        
        # Connect signals
        self._full_worker.data_loading_progress.connect(self.loading_progress)
        self._full_worker.data_loading_completed.connect(self._on_full_data_loaded)
        self._full_worker.data_loading_failed.connect(self._on_full_loading_failed)
        self._full_worker.underground_data_loaded.connect(self._on_underground_data_loaded)
        
        self._full_worker.start()
    
    def _on_essential_data_loaded(self, stations: List[str]):
        """Handle essential data loading completion."""
        self._essential_stations = stations
        self.logger.info(f"Essential stations ready: {len(stations)} stations")
        self.essential_stations_ready.emit(stations)
    
    def _on_full_data_loaded(self, stations: List[str]):
        """Handle full data loading completion."""
        self._full_stations = stations
        self._is_loading = False
        self.logger.info(f"Full stations ready: {len(stations)} stations")
        self.full_stations_ready.emit(stations)
    
    def _on_underground_data_loaded(self, stations: List[str]):
        """Handle underground data loading completion."""
        self._underground_stations = stations
        self.logger.info(f"Underground stations ready: {len(stations)} stations")
        self.underground_stations_ready.emit(stations)
    
    def _on_fast_loading_failed(self, error: str):
        """Handle fast loading failure."""
        self.logger.error(f"Fast station loading failed: {error}")
        self.loading_error.emit(f"Fast loading failed: {error}")
    
    def _on_full_loading_failed(self, error: str):
        """Handle full loading failure."""
        self._is_loading = False
        self.logger.error(f"Full station loading failed: {error}")
        self.loading_error.emit(f"Full loading failed: {error}")
    
    def stop_loading(self):
        """Stop all loading operations."""
        if self._fast_worker:
            self._fast_worker.stop_loading()
            self._fast_worker.wait(1000)  # Wait up to 1 second
        
        if self._full_worker:
            self._full_worker.stop_loading()
            self._full_worker.wait(3000)  # Wait up to 3 seconds
        
        self._is_loading = False
        self.logger.info("Station data loading stopped")
    
    def get_current_stations(self) -> List[str]:
        """
        Get the currently available stations.
        
        Returns the full station list if available, otherwise essential stations.
        
        Returns:
            List of currently available station names
        """
        if self._full_stations:
            return self._full_stations
        return self._essential_stations
    
    def is_loading(self) -> bool:
        """Check if data loading is in progress."""
        return self._is_loading
    
    def get_loading_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loading process."""
        return {
            "essential_stations_count": len(self._essential_stations),
            "full_stations_count": len(self._full_stations),
            "underground_stations_count": len(self._underground_stations),
            "is_loading": self._is_loading,
            "has_essential_data": len(self._essential_stations) > 0,
            "has_full_data": len(self._full_stations) > 0
        }