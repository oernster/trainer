"""
Combined forecast manager for the Trainer application.
Author: Oliver Ernster

This module provides business logic for managing combined weather and astronomy
forecasts, following solid Object-Oriented design principles with proper
abstraction, error handling, and integration coordination.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from PySide6.QtCore import QObject, Signal, QTimer

from ..models.weather_data import WeatherForecastData, Location
from ..models.astronomy_data import AstronomyForecastData
from ..models.combined_forecast_data import (
    CombinedForecastData,
    CombinedDataStatus,
    CombinedForecastValidator
)
from ..managers.weather_manager import WeatherManager
from ..managers.astronomy_manager import AstronomyManager
from ..managers.weather_config import WeatherConfig
from ..managers.astronomy_config import AstronomyConfig

logger = logging.getLogger(__name__)


class CombinedForecastManager(QObject):
    """
    Manager for combined weather and astronomy forecasts.
    
    Follows Facade pattern - provides simplified interface to complex
    weather and astronomy subsystems. Implements Observer pattern
    through Qt signals for UI updates.
    """
    
    # Qt Signals for observer pattern
    combined_forecast_updated = Signal(CombinedForecastData)
    forecast_error = Signal(str)
    loading_state_changed = Signal(bool)
    data_quality_changed = Signal(dict)
    
    def __init__(
        self,
        weather_manager: Optional[WeatherManager] = None,
        astronomy_manager: Optional[AstronomyManager] = None
    ):
        """
        Initialize combined forecast manager.
        
        Args:
            weather_manager: Weather data manager (optional)
            astronomy_manager: Astronomy data manager (optional)
        """
        super().__init__()
        self._weather_manager = weather_manager
        self._astronomy_manager = astronomy_manager
        self._validator = CombinedForecastValidator()
        
        # State tracking
        self._current_forecast: Optional[CombinedForecastData] = None
        self._last_update_time: Optional[datetime] = None
        self._is_loading = False
        self._location: Optional[Location] = None
        
        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)
        
        # Connect manager signals
        self._connect_manager_signals()
        
        logger.info("CombinedForecastManager initialized")
    
    def _connect_manager_signals(self) -> None:
        """Connect signals from weather and astronomy managers."""
        if self._weather_manager:
            self._weather_manager.weather_updated.connect(self._on_weather_updated)
            self._weather_manager.weather_error.connect(self._on_weather_error)
            self._weather_manager.loading_state_changed.connect(self._on_weather_loading_changed)
        
        if self._astronomy_manager:
            self._astronomy_manager.astronomy_updated.connect(self._on_astronomy_updated)
            self._astronomy_manager.astronomy_error.connect(self._on_astronomy_error)
            self._astronomy_manager.loading_state_changed.connect(self._on_astronomy_loading_changed)
    
    def set_weather_manager(self, weather_manager: WeatherManager) -> None:
        """Set or update the weather manager."""
        if self._weather_manager:
            # Disconnect old signals
            self._weather_manager.weather_updated.disconnect(self._on_weather_updated)
            self._weather_manager.weather_error.disconnect(self._on_weather_error)
            self._weather_manager.loading_state_changed.disconnect(self._on_weather_loading_changed)
        
        self._weather_manager = weather_manager
        
        # Connect new signals
        self._weather_manager.weather_updated.connect(self._on_weather_updated)
        self._weather_manager.weather_error.connect(self._on_weather_error)
        self._weather_manager.loading_state_changed.connect(self._on_weather_loading_changed)
        
        logger.info("Weather manager updated in combined forecast manager")
    
    def set_astronomy_manager(self, astronomy_manager: AstronomyManager) -> None:
        """Set or update the astronomy manager."""
        if self._astronomy_manager:
            # Disconnect old signals
            self._astronomy_manager.astronomy_updated.disconnect(self._on_astronomy_updated)
            self._astronomy_manager.astronomy_error.disconnect(self._on_astronomy_error)
            self._astronomy_manager.loading_state_changed.disconnect(self._on_astronomy_loading_changed)
        
        self._astronomy_manager = astronomy_manager
        
        # Connect new signals
        self._astronomy_manager.astronomy_updated.connect(self._on_astronomy_updated)
        self._astronomy_manager.astronomy_error.connect(self._on_astronomy_error)
        self._astronomy_manager.loading_state_changed.connect(self._on_astronomy_loading_changed)
        
        logger.info("Astronomy manager updated in combined forecast manager")
    
    async def get_combined_forecast(
        self,
        location: Optional[Location] = None,
        force_refresh: bool = False
    ) -> Optional[CombinedForecastData]:
        """
        Get combined weather and astronomy forecast.
        
        Args:
            location: Location for forecast (uses manager defaults if None)
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            CombinedForecastData: Combined forecast or None on error
        """
        if location:
            self._location = location
        
        # Check if we should skip refresh
        if not force_refresh and self._should_skip_refresh():
            logger.info("Returning cached combined forecast")
            return self._current_forecast
        
        self._set_loading_state(True)
        
        try:
            # Fetch data from both managers concurrently
            weather_task = self._fetch_weather_data(location)
            astronomy_task = self._fetch_astronomy_data(location)
            
            # Wait for both to complete
            weather_data, astronomy_data = await asyncio.gather(
                weather_task, astronomy_task, return_exceptions=True
            )
            
            # Handle exceptions and ensure proper types
            final_weather_data: Optional[WeatherForecastData] = None
            final_astronomy_data: Optional[AstronomyForecastData] = None
            
            if isinstance(weather_data, Exception):
                logger.error(f"Weather data fetch failed: {weather_data}")
            elif isinstance(weather_data, WeatherForecastData):
                final_weather_data = weather_data
            
            if isinstance(astronomy_data, Exception):
                logger.error(f"Astronomy data fetch failed: {astronomy_data}")
            elif isinstance(astronomy_data, AstronomyForecastData):
                final_astronomy_data = astronomy_data
            
            # Create combined forecast
            if location is None and self._location:
                location = self._location
            elif location is None:
                # Create default location
                from ..models.weather_data import Location as WeatherLocation
                location = WeatherLocation("Unknown", 0.0, 0.0)
            
            combined_forecast = CombinedForecastData.create(
                location=location,
                weather_data=final_weather_data,
                astronomy_data=final_astronomy_data
            )
            
            # Validate combined forecast
            if not self._validator.validate_combined_forecast(combined_forecast):
                logger.warning("Combined forecast validation failed")
            
            # Update state
            self._current_forecast = combined_forecast
            self._last_update_time = datetime.now()
            
            # Emit signals
            self.combined_forecast_updated.emit(combined_forecast)
            self._emit_data_quality_info(combined_forecast)
            
            logger.info(f"Combined forecast updated: {combined_forecast.get_status_summary()}")
            return combined_forecast
            
        except Exception as e:
            error_msg = f"Failed to get combined forecast: {e}"
            logger.error(error_msg)
            self.forecast_error.emit(error_msg)
            return None
            
        finally:
            self._set_loading_state(False)
    
    async def _fetch_weather_data(self, location: Optional[Location]) -> Optional[WeatherForecastData]:
        """Fetch weather data from weather manager."""
        if not self._weather_manager:
            logger.debug("No weather manager available")
            return None
        
        try:
            return await self._weather_manager.refresh_weather()
        except Exception as e:
            logger.error(f"Weather data fetch failed: {e}")
            return None
    
    async def _fetch_astronomy_data(self, location: Optional[Location]) -> Optional[AstronomyForecastData]:
        """Fetch astronomy data from astronomy manager."""
        if not self._astronomy_manager:
            logger.debug("No astronomy manager available")
            return None
        
        try:
            return await self._astronomy_manager.refresh_astronomy()
        except Exception as e:
            logger.error(f"Astronomy data fetch failed: {e}")
            return None
    
    def _should_skip_refresh(self) -> bool:
        """Check if refresh should be skipped based on cache age."""
        if not self._last_update_time or not self._current_forecast:
            return False
        
        # Use shorter cache duration for combined forecasts (30 minutes)
        cache_age = datetime.now() - self._last_update_time
        cache_duration = timedelta(minutes=30)
        
        return cache_age < cache_duration
    
    def _set_loading_state(self, is_loading: bool) -> None:
        """Update loading state and emit signal."""
        if self._is_loading != is_loading:
            self._is_loading = is_loading
            self.loading_state_changed.emit(is_loading)
            logger.debug(f"Combined forecast loading state changed: {is_loading}")
    
    def _emit_data_quality_info(self, forecast: CombinedForecastData) -> None:
        """Emit data quality information."""
        quality_info = {
            "status": forecast.status.value,
            "forecast_days": forecast.forecast_days,
            "has_weather": forecast.has_weather_data,
            "has_astronomy": forecast.has_astronomy_data,
            "total_astronomy_events": forecast.total_astronomy_events,
            "data_quality_summary": forecast.data_quality_summary,
            "error_messages": forecast.error_messages
        }
        self.data_quality_changed.emit(quality_info)
    
    def _auto_refresh(self) -> None:
        """Handle automatic refresh timer."""
        logger.info("Auto-refresh triggered for combined forecast")
        
        # Run async refresh
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.get_combined_forecast())
        else:
            asyncio.run(self.get_combined_forecast())
    
    def _on_weather_updated(self, weather_data: WeatherForecastData) -> None:
        """Handle weather data updates."""
        logger.debug("Weather data updated in combined manager")
        # Trigger combined forecast update
        asyncio.create_task(self._update_combined_forecast_from_weather(weather_data))
    
    def _on_astronomy_updated(self, astronomy_data: AstronomyForecastData) -> None:
        """Handle astronomy data updates."""
        logger.debug("Astronomy data updated in combined manager")
        # Trigger combined forecast update
        asyncio.create_task(self._update_combined_forecast_from_astronomy(astronomy_data))
    
    async def _update_combined_forecast_from_weather(self, weather_data: WeatherForecastData) -> None:
        """Update combined forecast when weather data changes."""
        if not self._current_forecast:
            # No existing forecast, create new one
            await self.get_combined_forecast(force_refresh=True)
            return
        
        # Update existing forecast with new weather data
        try:
            astronomy_data = self._current_forecast.astronomy_forecast
            
            new_forecast = CombinedForecastData.create(
                location=weather_data.location,
                weather_data=weather_data,
                astronomy_data=astronomy_data
            )
            
            self._current_forecast = new_forecast
            self._last_update_time = datetime.now()
            
            self.combined_forecast_updated.emit(new_forecast)
            self._emit_data_quality_info(new_forecast)
            
            logger.debug("Combined forecast updated from weather data")
            
        except Exception as e:
            logger.error(f"Failed to update combined forecast from weather: {e}")
    
    async def _update_combined_forecast_from_astronomy(self, astronomy_data: AstronomyForecastData) -> None:
        """Update combined forecast when astronomy data changes."""
        if not self._current_forecast:
            # No existing forecast, create new one
            await self.get_combined_forecast(force_refresh=True)
            return
        
        # Update existing forecast with new astronomy data
        try:
            weather_data = self._current_forecast.weather_forecast
            
            # Convert astronomy location to weather location for compatibility
            from ..models.weather_data import Location as WeatherLocation
            weather_location = WeatherLocation(
                name=astronomy_data.location.name,
                latitude=astronomy_data.location.latitude,
                longitude=astronomy_data.location.longitude
            )
            
            new_forecast = CombinedForecastData.create(
                location=weather_location,
                weather_data=weather_data,
                astronomy_data=astronomy_data
            )
            
            self._current_forecast = new_forecast
            self._last_update_time = datetime.now()
            
            self.combined_forecast_updated.emit(new_forecast)
            self._emit_data_quality_info(new_forecast)
            
            logger.debug("Combined forecast updated from astronomy data")
            
        except Exception as e:
            logger.error(f"Failed to update combined forecast from astronomy: {e}")
    
    def _on_weather_error(self, error_message: str) -> None:
        """Handle weather errors."""
        logger.warning(f"Weather error in combined manager: {error_message}")
        # Could emit combined error or handle gracefully
    
    def _on_astronomy_error(self, error_message: str) -> None:
        """Handle astronomy errors."""
        logger.warning(f"Astronomy error in combined manager: {error_message}")
        # Could emit combined error or handle gracefully
    
    def _on_weather_loading_changed(self, is_loading: bool) -> None:
        """Handle weather loading state changes."""
        self._update_combined_loading_state()
    
    def _on_astronomy_loading_changed(self, is_loading: bool) -> None:
        """Handle astronomy loading state changes."""
        self._update_combined_loading_state()
    
    def _update_combined_loading_state(self) -> None:
        """Update combined loading state based on individual managers."""
        weather_loading = False
        astronomy_loading = False
        
        if self._weather_manager:
            weather_loading = getattr(self._weather_manager, 'is_loading', lambda: False)()
        
        if self._astronomy_manager:
            astronomy_loading = getattr(self._astronomy_manager, 'is_loading', lambda: False)()
        
        combined_loading = weather_loading or astronomy_loading
        self._set_loading_state(combined_loading)
    
    def start_auto_refresh(self, interval_minutes: int = 30) -> None:
        """Start automatic refresh timer."""
        interval_ms = interval_minutes * 60 * 1000
        self._refresh_timer.start(interval_ms)
        logger.info(f"Combined forecast auto-refresh started (interval: {interval_minutes}m)")
    
    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh timer."""
        self._refresh_timer.stop()
        logger.info("Combined forecast auto-refresh stopped")
    
    def is_auto_refresh_active(self) -> bool:
        """Check if auto-refresh is currently active."""
        return self._refresh_timer.isActive()
    
    def get_current_forecast(self) -> Optional[CombinedForecastData]:
        """Get the current combined forecast."""
        return self._current_forecast
    
    def get_last_update_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful update."""
        return self._last_update_time
    
    def is_loading(self) -> bool:
        """Check if combined forecast is currently being loaded."""
        return self._is_loading
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        if self._is_loading:
            return "Loading combined forecast..."
        
        if not self._current_forecast:
            return "No combined forecast available"
        
        return self._current_forecast.get_status_summary()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information."""
        info = {
            "has_current_forecast": self._current_forecast is not None,
            "last_update_time": self._last_update_time,
            "is_loading": self._is_loading,
            "auto_refresh_active": self.is_auto_refresh_active(),
            "has_weather_manager": self._weather_manager is not None,
            "has_astronomy_manager": self._astronomy_manager is not None
        }
        
        if self._current_forecast:
            info.update({
                "forecast_status": self._current_forecast.status.value,
                "forecast_days": self._current_forecast.forecast_days,
                "total_astronomy_events": self._current_forecast.total_astronomy_events
            })
        
        return info
    
    def clear_cache(self) -> None:
        """Clear all cached combined forecast data."""
        self._current_forecast = None
        self._last_update_time = None
        
        # Also clear individual manager caches if they support it
        if self._weather_manager:
            clear_cache_method = getattr(self._weather_manager, 'clear_cache', None)
            if clear_cache_method:
                clear_cache_method()
        
        if self._astronomy_manager:
            clear_cache_method = getattr(self._astronomy_manager, 'clear_cache', None)
            if clear_cache_method:
                clear_cache_method()
        
        logger.info("Combined forecast cache cleared")
    
    def shutdown(self) -> None:
        """Shutdown combined forecast manager and cleanup resources."""
        logger.info("Shutting down combined forecast manager...")
        
        # Stop auto-refresh
        self.stop_auto_refresh()
        
        # Shutdown individual managers
        if self._weather_manager:
            self._weather_manager.shutdown()
        
        if self._astronomy_manager:
            self._astronomy_manager.shutdown()
        
        # Clear data
        self._current_forecast = None
        self._last_update_time = None
        
        logger.info("Combined forecast manager shutdown complete")


class CombinedForecastFactory:
    """
    Factory for creating combined forecast managers.
    
    Implements Factory pattern for easy instantiation and testing.
    """
    
    @staticmethod
    def create_manager(
        weather_config: Optional[WeatherConfig] = None,
        astronomy_config: Optional[AstronomyConfig] = None
    ) -> CombinedForecastManager:
        """Create combined forecast manager with given configurations."""
        weather_manager = None
        astronomy_manager = None
        
        if weather_config and weather_config.enabled:
            from ..managers.weather_manager import WeatherManager
            weather_manager = WeatherManager(weather_config)
        
        if astronomy_config and astronomy_config.enabled:
            from ..managers.astronomy_manager import AstronomyManager
            astronomy_manager = AstronomyManager(astronomy_config)
        
        return CombinedForecastManager(weather_manager, astronomy_manager)
    
    @staticmethod
    def create_weather_only_manager(weather_config: WeatherConfig) -> CombinedForecastManager:
        """Create combined manager with only weather data."""
        from ..managers.weather_manager import WeatherManager
        weather_manager = WeatherManager(weather_config)
        return CombinedForecastManager(weather_manager, None)
    
    @staticmethod
    def create_astronomy_only_manager(astronomy_config: AstronomyConfig) -> CombinedForecastManager:
        """Create combined manager with only astronomy data."""
        from ..managers.astronomy_manager import AstronomyManager
        astronomy_manager = AstronomyManager(astronomy_config)
        return CombinedForecastManager(None, astronomy_manager)
    
    @staticmethod
    def create_test_manager() -> CombinedForecastManager:
        """Create combined manager for testing."""
        return CombinedForecastManager(None, None)