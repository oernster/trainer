"""
Train data management for the Train Times application.

This module coordinates fetching train data from the API,
processing it, and managing updates.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from ..models.train_data import TrainData
from ..api.api_manager import APIManager, APIException, NetworkException
from ..managers.config_manager import ConfigData
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
        self.current_trains: List[TrainData] = []
        self.last_update: Optional[datetime] = None
        self.is_fetching = False

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.fetch_trains)

        logger.info("TrainManager initialized")

    def start_auto_refresh(self):
        """Start automatic refresh timer."""
        if self.config.refresh.auto_enabled:
            interval_ms = self.config.refresh.interval_minutes * 60 * 1000
            self.refresh_timer.start(interval_ms)
            logger.info(
                f"Auto-refresh started with {self.config.refresh.interval_minutes}m interval"
            )
        else:
            logger.info("Auto-refresh disabled in configuration")

    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off."""
        if self.refresh_timer.isActive():
            self.stop_auto_refresh()
            self.config.refresh.auto_enabled = False
        else:
            self.config.refresh.auto_enabled = True
            self.start_auto_refresh()

        logger.info(
            f"Auto-refresh {'enabled' if self.config.refresh.auto_enabled else 'disabled'}"
        )

    def stop_auto_refresh(self):
        """Stop automatic refresh timer."""
        self.refresh_timer.stop()
        logger.info("Auto-refresh stopped")

    def update_refresh_interval(self, minutes: int):
        """
        Update refresh interval.

        Args:
            minutes: New refresh interval in minutes
        """
        self.config.refresh.interval_minutes = minutes
        if self.refresh_timer.isActive():
            self.stop_auto_refresh()
            self.start_auto_refresh()
        logger.info(f"Refresh interval updated to {minutes} minutes")

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
        """Async method to fetch train data."""
        if self.is_fetching:
            return

        self.is_fetching = True
        self.status_changed.emit("Fetching train data...")

        try:
            # Initialize API manager if needed
            if self.api_manager is None:
                await self.initialize_api()

            if self.api_manager is None:
                raise Exception("API manager not available")

            # Fetch data using context manager
            async with self.api_manager as api:
                trains = await api.get_departures()

                # Process the data
                processed_trains = self._process_train_data(trains)

                # Update state
                self.current_trains = processed_trains
                self.last_update = datetime.now()

                # Emit signals
                self.trains_updated.emit(processed_trains)
                self.connection_changed.emit(True, "Connected")
                self.last_update_changed.emit(self.last_update.strftime("%H:%M:%S"))

                stats = calculate_journey_stats(processed_trains)
                status_msg = f"Updated: {len(processed_trains)} trains loaded"
                if stats["delayed"] > 0:
                    status_msg += f", {stats['delayed']} delayed"
                if stats["cancelled"] > 0:
                    status_msg += f", {stats['cancelled']} cancelled"

                self.status_changed.emit(status_msg)

                logger.info(f"Successfully fetched {len(processed_trains)} trains")

        except NetworkException as e:
            error_msg = f"Network Error: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "Network Error")

        except APIException as e:
            error_msg = f"API Error: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "API Error")

        except Exception as e:
            error_msg = f"Unexpected Error: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.connection_changed.emit(False, "Error")

        finally:
            self.is_fetching = False

    def _process_train_data(self, trains: List[TrainData]) -> List[TrainData]:
        """
        Process raw train data.

        Args:
            trains: Raw train data from API

        Returns:
            List[TrainData]: Processed and filtered train data
        """
        # Filter by status if needed
        filtered_trains = filter_trains_by_status(
            trains, self.config.display.show_cancelled
        )

        # Sort by departure time
        sorted_trains = sort_trains_by_departure(filtered_trains)

        # Limit to max trains
        limited_trains = sorted_trains[: self.config.display.max_trains]

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

    def is_auto_refresh_active(self) -> bool:
        """
        Check if auto-refresh is currently active.

        Returns:
            bool: True if auto-refresh is running
        """
        return self.refresh_timer.isActive()

    def get_next_refresh_seconds(self) -> int:
        """
        Get seconds until next refresh.

        Returns:
            int: Seconds until next refresh, 0 if not active
        """
        if not self.refresh_timer.isActive():
            return 0

        interval_ms = self.config.refresh.interval_minutes * 60 * 1000
        remaining_ms = interval_ms - (self.refresh_timer.timerId() % interval_ms)
        return max(0, remaining_ms // 1000)
