"""
Astronomy manager for the Trainer application.
Author: Oliver Ernster

This module provides business logic for astronomy data management,
following solid Object-Oriented design principles with proper
abstraction, error handling, and integration with the UI layer.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, QTimer

from ..models.astronomy_data import (
    AstronomyForecastData,
    Location,
    AstronomyDataValidator,
)
from ..api.nasa_api_manager import (
    AstronomyAPIManager,
    AstronomyAPIFactory,
    AstronomyAPIException,
    AstronomyNetworkException,
    AstronomyRateLimitException,
    AstronomyAuthenticationException,
)
from ..managers.astronomy_config import AstronomyConfig

logger = logging.getLogger(__name__)


class AstronomyManager(QObject):
    """
    Business logic manager for astronomy data.

    Follows Single Responsibility Principle - only responsible for
    astronomy data management and coordination between API and UI layers.
    Implements Observer pattern through Qt signals for UI updates.
    """

    # Qt Signals for observer pattern
    astronomy_updated = Signal(AstronomyForecastData)
    astronomy_error = Signal(str)
    loading_state_changed = Signal(bool)
    cache_status_changed = Signal(dict)

    def __init__(self, config: AstronomyConfig):
        """
        Initialize astronomy manager.

        Args:
            config: Astronomy configuration
        """
        super().__init__()
        self._config = config
        self._api_manager: Optional[AstronomyAPIManager] = None
        self._validator = AstronomyDataValidator()
        self._last_update_time: Optional[datetime] = None
        self._current_forecast: Optional[AstronomyForecastData] = None
        self._is_loading = False

        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)

        # Initialize API manager if enabled
        if config.enabled and config.has_valid_api_key():
            self._initialize_api_manager()

        logger.info(f"AstronomyManager initialized (enabled: {config.enabled})")

    def _initialize_api_manager(self) -> None:
        """Initialize the astronomy API manager."""
        try:
            self._api_manager = AstronomyAPIFactory.create_manager_from_config(
                self._config
            )
            logger.info("Astronomy API manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize astronomy API manager: {e}")
            self.astronomy_error.emit(f"Failed to initialize astronomy system: {e}")

    async def refresh_astronomy(
        self, force_refresh: bool = False
    ) -> Optional[AstronomyForecastData]:
        """
        Refresh astronomy data from API.

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            AstronomyForecastData: Updated astronomy forecast or None on error
        """
        if not self._config.enabled:
            logger.warning("Astronomy refresh requested but astronomy is disabled")
            return None

        if not self._api_manager:
            error_msg = "Astronomy API manager not initialized"
            logger.error(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        # Check if we should skip refresh (unless forced)
        if not force_refresh and self._should_skip_refresh():
            logger.info("Skipping astronomy refresh - recent data available")
            return self._current_forecast

        self._set_loading_state(True)

        try:
            # Create location from config
            location = Location(
                name=self._config.location_name,
                latitude=self._config.location_latitude,
                longitude=self._config.location_longitude,
                timezone=self._config.timezone,
            )

            # Fetch astronomy data
            forecast_data = await self._api_manager.get_astronomy_forecast(
                location, days=7
            )

            # Validate data
            if not self._validator.validate_astronomy_forecast(forecast_data):
                raise ValueError("Invalid astronomy data received from API")

            # Update internal state
            self._current_forecast = forecast_data
            self._last_update_time = datetime.now()

            # Emit signals
            self.astronomy_updated.emit(forecast_data)
            self._emit_cache_status()

            logger.info(
                f"Astronomy data refreshed successfully: {forecast_data.total_events} events"
            )
            return forecast_data

        except AstronomyAuthenticationException as e:
            error_msg = f"NASA API authentication failed: {e}"
            logger.error(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        except AstronomyRateLimitException as e:
            error_msg = f"NASA API rate limit exceeded: {e}"
            logger.warning(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        except AstronomyNetworkException as e:
            error_msg = f"Network error fetching astronomy data: {e}"
            logger.warning(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        except AstronomyAPIException as e:
            error_msg = f"Astronomy API error: {e}"
            logger.error(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        except Exception as e:
            error_msg = f"Unexpected error refreshing astronomy data: {e}"
            logger.error(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        finally:
            self._set_loading_state(False)

    def _should_skip_refresh(self) -> bool:
        """Check if refresh should be skipped based on cache age."""
        if not self._last_update_time or not self._current_forecast:
            return False

        cache_age = datetime.now() - self._last_update_time
        cache_duration = timedelta(seconds=self._config.get_cache_duration_seconds())

        return cache_age < cache_duration

    def _set_loading_state(self, is_loading: bool) -> None:
        """Update loading state and emit signal."""
        if self._is_loading != is_loading:
            self._is_loading = is_loading
            self.loading_state_changed.emit(is_loading)
            logger.debug(f"Astronomy loading state changed: {is_loading}")

    def _emit_cache_status(self) -> None:
        """Emit cache status information."""
        if self._api_manager:
            cache_info = self._api_manager.get_cache_info()
            cache_info.update(
                {
                    "manager_last_update": self._last_update_time,
                    "has_current_forecast": self._current_forecast is not None,
                }
            )
            self.cache_status_changed.emit(cache_info)

    def _auto_refresh(self) -> None:
        """Handle automatic refresh timer."""
        logger.info("Auto-refresh triggered for astronomy data")

        # Run async refresh in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.refresh_astronomy())
        else:
            asyncio.run(self.refresh_astronomy())

    def start_auto_refresh(self) -> None:
        """Start automatic refresh timer."""
        if not self._config.enabled:
            logger.warning("Cannot start auto-refresh: astronomy is disabled")
            return

        interval_ms = self._config.get_update_interval_seconds() * 1000
        self._refresh_timer.start(interval_ms)
        logger.info(
            f"Astronomy auto-refresh started (interval: {interval_ms/1000:.0f}s)"
        )

    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh timer."""
        self._refresh_timer.stop()
        logger.info("Astronomy auto-refresh stopped")

    def is_auto_refresh_active(self) -> bool:
        """Check if auto-refresh is currently active."""
        return self._refresh_timer.isActive()

    def get_current_forecast(self) -> Optional[AstronomyForecastData]:
        """Get the current astronomy forecast."""
        return self._current_forecast

    def get_last_update_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful update."""
        return self._last_update_time

    def is_loading(self) -> bool:
        """Check if astronomy data is currently being loaded."""
        return self._is_loading

    def is_data_stale(self) -> bool:
        """Check if current data is considered stale."""
        if not self._current_forecast:
            return True
        return self._current_forecast.is_stale

    def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information."""
        info = {
            "enabled": self._config.enabled,
            "has_api_manager": self._api_manager is not None,
            "has_current_forecast": self._current_forecast is not None,
            "last_update_time": self._last_update_time,
            "is_loading": self._is_loading,
            "auto_refresh_active": self.is_auto_refresh_active(),
            "data_stale": self.is_data_stale(),
        }

        if self._api_manager:
            api_cache_info = self._api_manager.get_cache_info()
            info.update(api_cache_info)

        return info

    def clear_cache(self) -> None:
        """Clear all cached astronomy data."""
        if self._api_manager:
            self._api_manager.clear_cache()

        self._current_forecast = None
        self._last_update_time = None

        self._emit_cache_status()
        logger.info("Astronomy cache cleared")

    def update_config(self, new_config: AstronomyConfig) -> None:
        """
        Update astronomy configuration.

        Args:
            new_config: New astronomy configuration
        """
        old_enabled = self._config.enabled
        old_api_key = self._config.nasa_api_key

        self._config = new_config

        # Handle enable/disable state changes
        if not old_enabled and new_config.enabled:
            # Astronomy was enabled
            if new_config.has_valid_api_key():
                self._initialize_api_manager()
                logger.info("Astronomy enabled and API manager initialized")
            else:
                logger.warning("Astronomy enabled but no valid API key provided")

        elif old_enabled and not new_config.enabled:
            # Astronomy was disabled
            self.stop_auto_refresh()
            self.clear_cache()
            logger.info("Astronomy disabled")

        elif new_config.enabled:
            # Astronomy remains enabled, check for API key changes
            if old_api_key != new_config.nasa_api_key:
                # API key changed, reinitialize
                if self._api_manager:
                    asyncio.create_task(self._api_manager.shutdown())
                self._initialize_api_manager()
                self.clear_cache()  # Clear cache with old API key
                logger.info("NASA API key updated, manager reinitialized")

        # Update auto-refresh if needed
        if new_config.enabled and self.is_auto_refresh_active():
            self.stop_auto_refresh()
            self.start_auto_refresh()

        logger.info("Astronomy configuration updated")

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        if not self._config.enabled:
            return "Astronomy disabled"

        if not self._api_manager:
            return "Astronomy API not initialized"

        if self._is_loading:
            return "Loading astronomy data..."

        if not self._current_forecast:
            return "No astronomy data available"

        if self.is_data_stale():
            return (
                f"Astronomy data stale ({self._current_forecast.total_events} events)"
            )

        return f"Astronomy data current ({self._current_forecast.total_events} events)"

    def get_enabled_services(self) -> list[str]:
        """Get list of enabled astronomy services."""
        return self._config.services.get_enabled_services()

    def shutdown(self) -> None:
        """Shutdown astronomy manager and cleanup resources."""
        logger.info("Shutting down astronomy manager...")

        # Stop auto-refresh
        self.stop_auto_refresh()

        # Shutdown API manager asynchronously
        if self._api_manager:
            try:
                # Try synchronous shutdown first
                self._api_manager.shutdown_sync()
            except Exception as e:
                logger.warning(f"Error during synchronous shutdown: {e}")
                # Fall back to async shutdown
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._api_manager.shutdown())
                    else:
                        asyncio.run(self._api_manager.shutdown())
                except Exception as e2:
                    logger.error(f"Error during async shutdown: {e2}")

        # Clear data
        self._current_forecast = None
        self._last_update_time = None
        self._api_manager = None

        logger.info("Astronomy manager shutdown complete")


class AstronomyManagerFactory:
    """
    Factory for creating astronomy managers.

    Implements Factory pattern for easy instantiation and testing.
    """

    @staticmethod
    def create_manager(config: AstronomyConfig) -> AstronomyManager:
        """Create astronomy manager with given configuration."""
        return AstronomyManager(config)

    @staticmethod
    def create_disabled_manager() -> AstronomyManager:
        """Create a disabled astronomy manager for testing."""
        config = AstronomyConfig(enabled=False)
        return AstronomyManager(config)

    @staticmethod
    def create_test_manager(api_key: str = "test_key") -> AstronomyManager:
        """Create astronomy manager for testing."""
        config = AstronomyConfig(
            enabled=True,
            nasa_api_key=api_key,
            location_name="Test Location",
            location_latitude=51.5074,
            location_longitude=-0.1278,
        )
        return AstronomyManager(config)
