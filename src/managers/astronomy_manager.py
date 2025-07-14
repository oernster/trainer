"""
Astronomy manager for the Trainer application.
Author: Oliver Ernster

This module provides business logic for astronomy data management,
following solid Object-Oriented design principles with proper
abstraction, error handling, and integration with the UI layer.

Now API-free - generates static astronomy events without requiring NASA API.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal, QTimer

from ..models.astronomy_data import (
    AstronomyForecastData,
    AstronomyEvent,
    AstronomyEventType,
    AstronomyData,
    Location,
    AstronomyDataValidator,
)
from ..managers.astronomy_config import AstronomyConfig
from ..models.astronomy_data import MoonPhase

logger = logging.getLogger(__name__)


class AstronomyManager(QObject):
    """
    Business logic manager for astronomy data.

    Follows Single Responsibility Principle - only responsible for
    astronomy data management and coordination with the UI layer.
    Implements Observer pattern through Qt signals for UI updates.
    
    Now API-free - generates static astronomy events without requiring NASA API.
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
        self._validator = AstronomyDataValidator()
        self._last_update_time: Optional[datetime] = None
        self._current_forecast: Optional[AstronomyForecastData] = None
        self._is_loading = False

        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)

        logger.debug(f"AstronomyManager initialized (enabled: {config.enabled}, API-free mode)")

    def _generate_static_astronomy_events(self) -> List[AstronomyEvent]:
        """Generate static astronomy events for demonstration."""
        now = datetime.now()
        events = []
        
        # Generate events for the next 7 days
        for day_offset in range(7):
            event_date = now + timedelta(days=day_offset)
            
            # Generate 2-4 events per day with variety
            daily_events = [
                AstronomyEvent(
                    event_type=AstronomyEventType.PLANETARY_EVENT,
                    title="Jupiter Visible",
                    description="Jupiter is visible in the evening sky, reaching its highest point around midnight.",
                    start_time=event_date.replace(hour=20, minute=30, second=0, microsecond=0),
                    visibility_info="Eastern Sky, magnitude -2.1",
                    related_links=["https://in-the-sky.org/jupiter.php"],
                    suggested_categories=["Observatory", "Tonight's Sky"]
                ),
                AstronomyEvent(
                    event_type=AstronomyEventType.MOON_PHASE,
                    title="Moon Phase",
                    description=f"The Moon is in {'Waxing Crescent' if day_offset < 3 else 'First Quarter' if day_offset < 5 else 'Waxing Gibbous'} phase.",
                    start_time=event_date.replace(hour=22, minute=0, second=0, microsecond=0),
                    visibility_info="Night Sky, magnitude -12.7",
                    related_links=["https://timeanddate.com/astronomy/moon/"],
                    suggested_categories=["Moon Info", "Tonight's Sky"]
                ),
                AstronomyEvent(
                    event_type=AstronomyEventType.ISS_PASS,
                    title="ISS Pass",
                    description="International Space Station visible pass overhead.",
                    start_time=event_date.replace(hour=6, minute=15, second=0, microsecond=0),
                    visibility_info="Southwest to Northeast, magnitude -3.5",
                    related_links=["https://spotthestation.nasa.gov/"],
                    suggested_categories=["Space Agencies", "Live Data"]
                ),
                AstronomyEvent(
                    event_type=AstronomyEventType.NEAR_EARTH_OBJECT,
                    title="Orion Nebula",
                    description="The Orion Nebula (M42) is well-positioned for observation.",
                    start_time=event_date.replace(hour=23, minute=45, second=0, microsecond=0),
                    visibility_info="Constellation Orion, magnitude 4.0",
                    related_links=["https://messier.seds.org/m/m042.html"],
                    suggested_categories=["Observatory", "Educational"]
                )
            ]
            
            # Add some variety - not all events every day
            if day_offset % 2 == 0:
                events.extend(daily_events[:3])  # 3 events on even days
            else:
                events.extend(daily_events[:2])  # 2 events on odd days
                
        return events

    async def refresh_astronomy(
        self, force_refresh: bool = False
    ) -> Optional[AstronomyForecastData]:
        """
        Refresh astronomy data (now generates static events).

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            AstronomyForecastData: Updated astronomy forecast or None on error
        """
        if not self._config.enabled:
            logger.warning("Astronomy refresh requested but astronomy is disabled")
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

            # Generate static astronomy events
            events = self._generate_static_astronomy_events()

            # Create daily astronomy data from events
            daily_astronomy = []
            events_by_date = {}
            
            # Group events by date
            for event in events:
                event_date = event.start_time.date()
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)
            
            # Create AstronomyData for each date with proper moon phases
            for event_date, date_events in sorted(events_by_date.items()):
                # Calculate moon phase for this date
                moon_phase = self._calculate_moon_phase_for_date(event_date)
                moon_illumination = self._calculate_moon_illumination(moon_phase)
                
                daily_data = AstronomyData(
                    date=event_date,
                    events=date_events,
                    primary_event=date_events[0] if date_events else None,
                    moon_phase=moon_phase,
                    moon_illumination=moon_illumination
                )
                daily_astronomy.append(daily_data)

            # Create forecast data
            forecast_data = AstronomyForecastData(
                location=location,
                daily_astronomy=daily_astronomy,
                last_updated=datetime.now(),
                data_source="Static Generator"
            )

            # Validate data
            if not self._validator.validate_astronomy_forecast(forecast_data):
                raise ValueError("Invalid astronomy data generated")

            # Update internal state
            self._current_forecast = forecast_data
            self._last_update_time = datetime.now()

            # Emit signals
            self.astronomy_updated.emit(forecast_data)
            self._emit_cache_status()

            logger.info(
                f"Astronomy data generated successfully: {forecast_data.total_events} events"
            )
            return forecast_data

        except Exception as e:
            error_msg = f"Unexpected error generating astronomy data: {e}"
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
        # API-free mode - emit basic cache info
        cache_info = {
            "manager_last_update": self._last_update_time,
            "has_current_forecast": self._current_forecast is not None,
            "cache_type": "static_generator"
        }
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

        # Use a default 1-hour interval for API-free mode
        interval_ms = 3600 * 1000  # 1 hour
        self._refresh_timer.start(interval_ms)
        logger.info(
            f"Astronomy auto-refresh started (interval: {interval_ms/1000:.0f}s)"
        )

    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh timer."""
        self._refresh_timer.stop()
        logger.debug("Astronomy auto-refresh stopped")

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
            "has_api_manager": False,  # API-free mode
            "has_current_forecast": self._current_forecast is not None,
            "last_update_time": self._last_update_time,
            "is_loading": self._is_loading,
            "auto_refresh_active": self.is_auto_refresh_active(),
            "data_stale": self.is_data_stale(),
            "cache_type": "static_generator"
        }

        return info

    def clear_cache(self) -> None:
        """Clear all cached astronomy data."""
        # API-free mode - just clear local data
        self._current_forecast = None
        self._last_update_time = None

        self._emit_cache_status()
        logger.debug("Astronomy cache cleared")

    def update_config(self, new_config: AstronomyConfig) -> None:
        """
        Update astronomy configuration.

        Args:
            new_config: New astronomy configuration
        """
        old_enabled = self._config.enabled
        self._config = new_config

        # Handle enable/disable state changes
        if not old_enabled and new_config.enabled:
            # Astronomy was enabled
            logger.info("Astronomy enabled (API-free mode)")

        elif old_enabled and not new_config.enabled:
            # Astronomy was disabled
            self.stop_auto_refresh()
            self.clear_cache()
            logger.info("Astronomy disabled")

        # Update auto-refresh if needed
        if new_config.enabled and self.is_auto_refresh_active():
            self.stop_auto_refresh()
            self.start_auto_refresh()

        logger.info("Astronomy configuration updated")

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        if not self._config.enabled:
            return "Astronomy disabled"

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
        # Return default services for API-free mode
        return ["Static Generator", "Astronomy Links"]

    def shutdown(self) -> None:
        """Shutdown astronomy manager and cleanup resources."""
        logger.debug("Shutting down astronomy manager...")

        # Stop auto-refresh
        self.stop_auto_refresh()

        # Clear data (API-free mode - no API manager to shutdown)
        self._current_forecast = None
        self._last_update_time = None

        logger.debug("Astronomy manager shutdown complete")

    def _calculate_moon_phase_for_date(self, target_date) -> MoonPhase:
        """Calculate moon phase for a given date using a simplified lunar cycle."""
        from datetime import date
        
        # Use a known new moon date as reference (January 1, 2024 was approximately new moon)
        reference_date = date(2024, 1, 1)
        days_since_reference = (target_date - reference_date).days
        
        # Lunar cycle is approximately 29.53 days
        lunar_cycle_days = 29.53
        cycle_position = (days_since_reference % lunar_cycle_days) / lunar_cycle_days
        
        # Map cycle position to moon phases
        if cycle_position < 0.0625:  # 0-1.8 days
            return MoonPhase.NEW_MOON
        elif cycle_position < 0.1875:  # 1.8-5.5 days
            return MoonPhase.WAXING_CRESCENT
        elif cycle_position < 0.3125:  # 5.5-9.2 days
            return MoonPhase.FIRST_QUARTER
        elif cycle_position < 0.4375:  # 9.2-12.9 days
            return MoonPhase.WAXING_GIBBOUS
        elif cycle_position < 0.5625:  # 12.9-16.6 days
            return MoonPhase.FULL_MOON
        elif cycle_position < 0.6875:  # 16.6-20.3 days
            return MoonPhase.WANING_GIBBOUS
        elif cycle_position < 0.8125:  # 20.3-24.0 days
            return MoonPhase.LAST_QUARTER
        else:  # 24.0-29.5 days
            return MoonPhase.WANING_CRESCENT

    def _calculate_moon_illumination(self, moon_phase: MoonPhase) -> float:
        """Calculate approximate moon illumination percentage based on phase."""
        illumination_map = {
            MoonPhase.NEW_MOON: 0.0,
            MoonPhase.WAXING_CRESCENT: 0.25,
            MoonPhase.FIRST_QUARTER: 0.5,
            MoonPhase.WAXING_GIBBOUS: 0.75,
            MoonPhase.FULL_MOON: 1.0,
            MoonPhase.WANING_GIBBOUS: 0.75,
            MoonPhase.LAST_QUARTER: 0.5,
            MoonPhase.WANING_CRESCENT: 0.25,
        }
        return illumination_map.get(moon_phase, 0.5)


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
            location_name="Test Location",
            location_latitude=51.5074,
            location_longitude=-0.1278,
        )
        return AstronomyManager(config)


