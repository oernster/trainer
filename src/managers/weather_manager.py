"""
Weather manager for the Trainer application.
Author: Oliver Ernster

This module provides business logic for weather data management,
following solid Object-Oriented design principles with Observer pattern
implementation and proper error handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from PySide6.QtCore import QObject, QTimer, Signal

from version import __weather_version__, __weather_api_provider__
from ..models.weather_data import WeatherForecastData, Location, WeatherData
from ..managers.weather_config import WeatherConfig
from ..api.weather_api_manager import (
    WeatherAPIManager,
    WeatherAPIFactory,
    WeatherAPIException,
    WeatherNetworkException,
    WeatherDataException,
)

logger = logging.getLogger(__name__)


class WeatherObserver(ABC):
    """
    Abstract observer for weather updates.

    Follows Observer pattern for loose coupling between weather manager
    and UI components.
    """

    @abstractmethod
    def on_weather_updated(self, weather_data: WeatherForecastData) -> None:
        """Called when weather data is updated."""
        pass

    @abstractmethod
    def on_weather_error(self, error: Exception) -> None:
        """Called when weather update fails."""
        pass

    @abstractmethod
    def on_weather_loading(self, is_loading: bool) -> None:
        """Called when weather loading state changes."""
        pass


class WeatherSubject:
    """
    Subject that notifies observers of weather changes.

    Implements Observer pattern subject interface.
    """

    def __init__(self):
        """Initialize subject with empty observer list."""
        self._observers: List[WeatherObserver] = []
        self._loading_state = False

    def attach(self, observer: WeatherObserver) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)
            logger.info(f"Weather observer attached: {type(observer).__name__}")

    def detach(self, observer: WeatherObserver) -> None:
        """Detach an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            logger.info(f"Weather observer detached: {type(observer).__name__}")

    def notify_weather_updated(self, weather_data: WeatherForecastData) -> None:
        """Notify all observers of weather update."""
        logger.info(f"Notifying {len(self._observers)} observers of weather update")
        for observer in self._observers:
            try:
                observer.on_weather_updated(weather_data)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    def notify_weather_error(self, error: Exception) -> None:
        """Notify all observers of weather error."""
        logger.warning(f"Notifying {len(self._observers)} observers of weather error")
        for observer in self._observers:
            try:
                observer.on_weather_error(error)
            except Exception as e:
                logger.error(f"Observer error notification failed: {e}")

    def notify_loading_state(self, is_loading: bool) -> None:
        """Notify all observers of loading state change."""
        if self._loading_state != is_loading:
            self._loading_state = is_loading
            for observer in self._observers:
                try:
                    observer.on_weather_loading(is_loading)
                except Exception as e:
                    logger.error(f"Observer loading notification failed: {e}")

    def get_observer_count(self) -> int:
        """Get number of attached observers."""
        return len(self._observers)


class WeatherCommand(ABC):
    """
    Abstract command for weather operations.

    Implements Command pattern for undoable operations.
    """

    @abstractmethod
    async def execute(self) -> None:
        """Execute the command."""
        pass

    @abstractmethod
    async def undo(self) -> None:
        """Undo the command."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get command description."""
        pass


class RefreshWeatherCommand(WeatherCommand):
    """Command to refresh weather data."""

    def __init__(
        self, weather_manager: "WeatherManager", location: Optional[Location] = None
    ):
        """Initialize refresh command."""
        self._weather_manager = weather_manager
        self._location = location
        self._previous_data: Optional[WeatherForecastData] = None

    async def execute(self) -> None:
        """Execute weather refresh."""
        self._previous_data = self._weather_manager.get_current_data()
        await self._weather_manager._fetch_weather_internal(self._location)

    async def undo(self) -> None:
        """Restore previous weather data."""
        if self._previous_data:
            self._weather_manager._set_weather_data(self._previous_data)

    def get_description(self) -> str:
        """Get command description."""
        location_name = self._location.name if self._location else "default location"
        return f"Refresh weather for {location_name}"


class WeatherErrorHandler:
    """
    Centralized error handling for weather operations.

    Follows Single Responsibility Principle - only handles errors.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize error handler."""
        self._logger = logger
        self._error_strategies = {
            WeatherAPIException: self._handle_api_error,
            WeatherNetworkException: self._handle_network_error,
            WeatherDataException: self._handle_data_error,
            Exception: self._handle_generic_error,
        }

    def handle_error(self, error: Exception) -> str:
        """Handle error and return user-friendly message."""
        error_type = type(error)

        # Find the most specific handler
        handler = None
        for exception_type, error_handler in self._error_strategies.items():
            if isinstance(error, exception_type):
                handler = error_handler
                break

        if handler is None:
            handler = self._handle_generic_error

        return handler(error)

    def _handle_api_error(self, error: WeatherAPIException) -> str:
        """Handle weather API errors."""
        self._logger.error(f"Weather API error: {error}")
        return "Unable to fetch weather data. Please try again later."

    def _handle_network_error(self, error: WeatherNetworkException) -> str:
        """Handle network errors."""
        self._logger.error(f"Weather network error: {error}")
        return "Network connection error. Please check your internet connection."

    def _handle_data_error(self, error: WeatherDataException) -> str:
        """Handle weather data processing errors."""
        self._logger.error(f"Weather data error: {error}")
        return "Weather data is temporarily unavailable."

    def _handle_generic_error(self, error: Exception) -> str:
        """Handle generic errors."""
        self._logger.error(f"Unexpected weather error: {error}")
        return "An unexpected error occurred while fetching weather data."


class WeatherManager(QObject, WeatherSubject):
    """
    High-level weather manager with business logic.

    Follows Single Responsibility Principle - only responsible for
    weather business logic and coordination.
    Implements Observer pattern as subject.
    Integrates with Qt signals for UI updates.
    """

    # Qt Signals for integration with existing Qt-based UI
    weather_updated = Signal(object)  # WeatherForecastData
    weather_error = Signal(str)  # Error message
    loading_state_changed = Signal(bool)  # Loading state

    def __init__(self, config: WeatherConfig):
        """
        Initialize weather manager.

        Args:
            config: Weather configuration
        """
        QObject.__init__(self)
        WeatherSubject.__init__(self)

        self._config = config
        self._api_manager = WeatherAPIFactory.create_manager_from_config(config)
        self._current_forecast: Optional[WeatherForecastData] = None
        self._error_handler = WeatherErrorHandler(logger)

        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._on_refresh_timer)

        # Command history for undo functionality
        self._command_history: List[WeatherCommand] = []
        self._max_history_size = 10

        # Statistics
        self._fetch_count = 0
        self._error_count = 0
        self._last_successful_fetch: Optional[datetime] = None

        logger.info(f"WeatherManager initialized with {config.api_provider}")

        # Start auto-refresh if enabled
        if config.enabled:
            self.start_auto_refresh()

    def start_auto_refresh(self) -> None:
        """Start automatic weather refresh."""
        if not self._config.enabled:
            logger.warning("Cannot start auto-refresh: weather integration disabled")
            return

        interval_ms = self._config.get_refresh_interval_seconds() * 1000
        self._refresh_timer.start(interval_ms)
        logger.info(
            f"Auto-refresh started with {self._config.refresh_interval_minutes}min interval"
        )

    def stop_auto_refresh(self) -> None:
        """Stop automatic weather refresh."""
        self._refresh_timer.stop()
        logger.info("Auto-refresh stopped")

    def is_auto_refresh_active(self) -> bool:
        """Check if auto-refresh is active."""
        return self._refresh_timer.isActive()

    async def refresh_weather(self, location: Optional[Location] = None) -> None:
        """
        Refresh weather data manually.

        Args:
            location: Location to refresh weather for (uses config location if None)
        """
        command = RefreshWeatherCommand(self, location)
        await self._execute_command(command)

    async def _execute_command(self, command: WeatherCommand) -> None:
        """Execute command and add to history."""
        try:
            await command.execute()

            # Add to history
            self._command_history.append(command)
            if len(self._command_history) > self._max_history_size:
                self._command_history.pop(0)

            logger.info(f"Executed command: {command.get_description()}")

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise

    async def undo_last_command(self) -> None:
        """Undo the last executed command."""
        if self._command_history:
            command = self._command_history.pop()
            try:
                await command.undo()
                logger.info(f"Undid command: {command.get_description()}")
            except Exception as e:
                logger.error(f"Command undo failed: {e}")
                raise

    async def _fetch_weather_internal(
        self, location: Optional[Location] = None
    ) -> None:
        """Internal method to fetch weather data."""
        self.notify_loading_state(True)
        self.loading_state_changed.emit(True)

        try:
            self._fetch_count += 1
            forecast_data = await self._api_manager.get_weather_forecast(location)

            # Update internal state
            self._current_forecast = forecast_data
            self._last_successful_fetch = datetime.now()

            # Notify observers and emit Qt signals
            self.notify_weather_updated(forecast_data)
            self.weather_updated.emit(forecast_data)

            logger.info(
                f"Weather data refreshed successfully (fetch #{self._fetch_count})"
            )

        except Exception as e:
            self._error_count += 1
            error_message = self._error_handler.handle_error(e)

            # Notify observers and emit Qt signals
            self.notify_weather_error(e)
            self.weather_error.emit(error_message)

            logger.error(f"Weather refresh failed (error #{self._error_count}): {e}")
            raise

        finally:
            self.notify_loading_state(False)
            self.loading_state_changed.emit(False)

    def _on_refresh_timer(self) -> None:
        """Handle auto-refresh timer timeout."""
        if not self._config.enabled:
            self.stop_auto_refresh()
            return

        logger.info("Auto-refresh timer triggered")

        # Run async refresh in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create task for running event loop
            asyncio.create_task(self._fetch_weather_internal())
        else:
            # Run in new event loop
            asyncio.run(self._fetch_weather_internal())

    def get_current_data(self) -> Optional[WeatherForecastData]:
        """Get current weather forecast data."""
        return self._current_forecast

    def _set_weather_data(self, data: WeatherForecastData) -> None:
        """Set weather data (used by undo operations)."""
        self._current_forecast = data
        self.notify_weather_updated(data)
        self.weather_updated.emit(data)

    def get_current_weather(self) -> Optional[WeatherData]:
        """Get current weather conditions."""
        if self._current_forecast:
            return self._current_forecast.get_current_weather()
        return None

    def get_today_hourly(self) -> List[WeatherData]:
        """Get today's hourly forecast."""
        if self._current_forecast:
            return self._current_forecast.current_day_hourly
        return []

    def get_daily_forecast(self) -> List[WeatherData]:
        """Get daily forecast."""
        if self._current_forecast:
            return self._current_forecast.daily_forecast
        return []

    def is_data_stale(self) -> bool:
        """Check if current data is stale."""
        if not self._current_forecast:
            return True
        return self._current_forecast.is_stale

    def get_statistics(self) -> Dict[str, Any]:
        """Get weather manager statistics."""
        return {
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
            "success_rate": (
                (self._fetch_count - self._error_count)
                / max(self._fetch_count, 1)
                * 100
            ),
            "last_successful_fetch": self._last_successful_fetch,
            "auto_refresh_active": self.is_auto_refresh_active(),
            "observer_count": self.get_observer_count(),
            "has_current_data": self._current_forecast is not None,
            "data_stale": self.is_data_stale(),
            "config_version": __weather_version__,
            "api_provider": __weather_api_provider__,
        }

    def update_config(self, new_config: WeatherConfig) -> None:
        """
        Update weather configuration.

        Args:
            new_config: New weather configuration
        """
        old_interval = self._config.refresh_interval_minutes
        self._config = new_config

        # Update API manager
        self._api_manager = WeatherAPIFactory.create_manager_from_config(new_config)

        # Restart auto-refresh if interval changed
        if new_config.refresh_interval_minutes != old_interval:
            if self.is_auto_refresh_active():
                self.stop_auto_refresh()
                if new_config.enabled:
                    self.start_auto_refresh()

        # Clear cache to force fresh data with new config
        self._api_manager.clear_cache()

        logger.info(f"Weather configuration updated")

    def clear_data(self) -> None:
        """Clear all weather data and cache."""
        self._current_forecast = None
        self._api_manager.clear_cache()
        self._command_history.clear()
        logger.info("Weather data cleared")

    def shutdown(self) -> None:
        """Shutdown weather manager and cleanup resources."""
        self.stop_auto_refresh()
        self.clear_data()

        # Detach all observers
        self._observers.clear()

        # Shutdown API manager synchronously
        try:
            if hasattr(self._api_manager, "shutdown_sync"):
                self._api_manager.shutdown_sync()
            else:
                logger.warning("API manager does not support synchronous shutdown")
        except Exception as e:
            logger.warning(f"Failed to shutdown API manager: {e}")

        logger.info("WeatherManager shutdown complete")
