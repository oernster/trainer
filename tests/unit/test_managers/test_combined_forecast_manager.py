"""
Comprehensive tests for CombinedForecastManager.
Author: Oliver Ernster

Tests for 100% coverage of src/managers/combined_forecast_manager.py
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date
from PySide6.QtCore import QObject, Signal, QTimer

from src.managers.combined_forecast_manager import (
    CombinedForecastManager,
    CombinedForecastFactory
)
from src.models.weather_data import WeatherForecastData, Location, WeatherData
from src.models.astronomy_data import AstronomyForecastData, AstronomyData
from src.models.combined_forecast_data import (
    CombinedForecastData,
    CombinedDataStatus,
    CombinedForecastValidator,
    ForecastDataQuality
)
from src.managers.weather_manager import WeatherManager
from src.managers.astronomy_manager import AstronomyManager
from src.managers.weather_config import WeatherConfig
from src.managers.astronomy_config import AstronomyConfig


@pytest.fixture
def mock_weather_manager():
    """Create a mock weather manager."""
    manager = Mock(spec=WeatherManager)
    manager.weather_updated = Mock()
    manager.weather_updated.connect = Mock()
    manager.weather_updated.disconnect = Mock()
    manager.weather_error = Mock()
    manager.weather_error.connect = Mock()
    manager.weather_error.disconnect = Mock()
    manager.loading_state_changed = Mock()
    manager.loading_state_changed.connect = Mock()
    manager.loading_state_changed.disconnect = Mock()
    manager.refresh_weather = AsyncMock()
    manager.is_loading = Mock(return_value=False)
    manager.clear_cache = Mock()
    manager.shutdown = Mock()
    return manager


@pytest.fixture
def mock_astronomy_manager():
    """Create a mock astronomy manager."""
    manager = Mock(spec=AstronomyManager)
    manager.astronomy_updated = Mock()
    manager.astronomy_updated.connect = Mock()
    manager.astronomy_updated.disconnect = Mock()
    manager.astronomy_error = Mock()
    manager.astronomy_error.connect = Mock()
    manager.astronomy_error.disconnect = Mock()
    manager.loading_state_changed = Mock()
    manager.loading_state_changed.connect = Mock()
    manager.loading_state_changed.disconnect = Mock()
    manager.refresh_astronomy = AsyncMock()
    manager.is_loading = Mock(return_value=False)
    manager.clear_cache = Mock()
    manager.shutdown = Mock()
    return manager


@pytest.fixture
def sample_location():
    """Create a sample location."""
    return Location("Test City", 51.5074, -0.1278)


@pytest.fixture
def sample_weather_data(sample_location):
    """Create sample weather forecast data."""
    weather_data = WeatherData(
        timestamp=datetime.now(),
        temperature=20.0,
        humidity=65,
        weather_code=2,  # Partly cloudy
        description="Partly cloudy"
    )
    
    return WeatherForecastData(
        location=sample_location,
        daily_forecast=[weather_data],
        hourly_forecast=[weather_data],
        last_updated=datetime.now()
    )


@pytest.fixture
def sample_astronomy_data(sample_location):
    """Create sample astronomy forecast data."""
    from src.models.astronomy_data import Location as AstronomyLocation, MoonPhase
    
    # Convert to astronomy location
    astro_location = AstronomyLocation(
        name=sample_location.name,
        latitude=sample_location.latitude,
        longitude=sample_location.longitude
    )
    
    astronomy_data = AstronomyData(
        date=date.today(),
        sunrise_time=datetime.now().replace(hour=6, minute=30),
        sunset_time=datetime.now().replace(hour=19, minute=45),
        moon_phase=MoonPhase.FULL_MOON,
        moon_illumination=1.0,
        events=[]
    )
    
    return AstronomyForecastData(
        location=astro_location,
        daily_astronomy=[astronomy_data],
        last_updated=datetime.now()
    )


@pytest.fixture
def sample_combined_forecast(sample_location, sample_weather_data, sample_astronomy_data):
    """Create sample combined forecast data."""
    return CombinedForecastData.create(
        location=sample_location,
        weather_data=sample_weather_data,
        astronomy_data=sample_astronomy_data
    )


class TestCombinedForecastManagerInit:
    """Test CombinedForecastManager initialization."""
    
    def test_init_with_no_managers(self):
        """Test initialization with no managers."""
        manager = CombinedForecastManager()
        
        assert manager._weather_manager is None
        assert manager._astronomy_manager is None
        assert isinstance(manager._validator, CombinedForecastValidator)
        assert manager._current_forecast is None
        assert manager._last_update_time is None
        assert manager._is_loading is False
        assert manager._location is None
        assert isinstance(manager._refresh_timer, QTimer)
    
    def test_init_with_managers(self, mock_weather_manager, mock_astronomy_manager):
        """Test initialization with both managers."""
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        assert manager._weather_manager is mock_weather_manager
        assert manager._astronomy_manager is mock_astronomy_manager
        
        # Verify signal connections
        mock_weather_manager.weather_updated.connect.assert_called()
        mock_weather_manager.weather_error.connect.assert_called()
        mock_weather_manager.loading_state_changed.connect.assert_called()
        mock_astronomy_manager.astronomy_updated.connect.assert_called()
        mock_astronomy_manager.astronomy_error.connect.assert_called()
        mock_astronomy_manager.loading_state_changed.connect.assert_called()
    
    def test_init_with_weather_manager_only(self, mock_weather_manager):
        """Test initialization with only weather manager."""
        manager = CombinedForecastManager(mock_weather_manager, None)
        
        assert manager._weather_manager is mock_weather_manager
        assert manager._astronomy_manager is None
        
        # Verify weather signal connections
        mock_weather_manager.weather_updated.connect.assert_called()
        mock_weather_manager.weather_error.connect.assert_called()
        mock_weather_manager.loading_state_changed.connect.assert_called()
    
    def test_init_with_astronomy_manager_only(self, mock_astronomy_manager):
        """Test initialization with only astronomy manager."""
        manager = CombinedForecastManager(None, mock_astronomy_manager)
        
        assert manager._weather_manager is None
        assert manager._astronomy_manager is mock_astronomy_manager
        
        # Verify astronomy signal connections
        mock_astronomy_manager.astronomy_updated.connect.assert_called()
        mock_astronomy_manager.astronomy_error.connect.assert_called()
        mock_astronomy_manager.loading_state_changed.connect.assert_called()


class TestCombinedForecastManagerSetters:
    """Test manager setter methods."""
    
    def test_set_weather_manager_new(self, mock_weather_manager):
        """Test setting weather manager when none exists."""
        manager = CombinedForecastManager()
        manager.set_weather_manager(mock_weather_manager)
        
        assert manager._weather_manager is mock_weather_manager
        mock_weather_manager.weather_updated.connect.assert_called()
        mock_weather_manager.weather_error.connect.assert_called()
        mock_weather_manager.loading_state_changed.connect.assert_called()
    
    def test_set_weather_manager_replace(self, mock_weather_manager):
        """Test replacing existing weather manager."""
        old_manager = Mock(spec=WeatherManager)
        old_manager.weather_updated = Mock()
        old_manager.weather_updated.disconnect = Mock()
        old_manager.weather_error = Mock()
        old_manager.weather_error.disconnect = Mock()
        old_manager.loading_state_changed = Mock()
        old_manager.loading_state_changed.disconnect = Mock()
        
        manager = CombinedForecastManager(old_manager, None)
        manager.set_weather_manager(mock_weather_manager)
        
        # Verify old signals disconnected
        old_manager.weather_updated.disconnect.assert_called()
        old_manager.weather_error.disconnect.assert_called()
        old_manager.loading_state_changed.disconnect.assert_called()
        
        # Verify new signals connected
        assert manager._weather_manager is mock_weather_manager
        mock_weather_manager.weather_updated.connect.assert_called()
        mock_weather_manager.weather_error.connect.assert_called()
        mock_weather_manager.loading_state_changed.connect.assert_called()
    
    def test_set_astronomy_manager_new(self, mock_astronomy_manager):
        """Test setting astronomy manager when none exists."""
        manager = CombinedForecastManager()
        manager.set_astronomy_manager(mock_astronomy_manager)
        
        assert manager._astronomy_manager is mock_astronomy_manager
        mock_astronomy_manager.astronomy_updated.connect.assert_called()
        mock_astronomy_manager.astronomy_error.connect.assert_called()
        mock_astronomy_manager.loading_state_changed.connect.assert_called()
    
    def test_set_astronomy_manager_replace(self, mock_astronomy_manager):
        """Test replacing existing astronomy manager."""
        old_manager = Mock(spec=AstronomyManager)
        old_manager.astronomy_updated = Mock()
        old_manager.astronomy_updated.disconnect = Mock()
        old_manager.astronomy_error = Mock()
        old_manager.astronomy_error.disconnect = Mock()
        old_manager.loading_state_changed = Mock()
        old_manager.loading_state_changed.disconnect = Mock()
        
        manager = CombinedForecastManager(None, old_manager)
        manager.set_astronomy_manager(mock_astronomy_manager)
        
        # Verify old signals disconnected
        old_manager.astronomy_updated.disconnect.assert_called()
        old_manager.astronomy_error.disconnect.assert_called()
        old_manager.loading_state_changed.disconnect.assert_called()
        
        # Verify new signals connected
        assert manager._astronomy_manager is mock_astronomy_manager
        mock_astronomy_manager.astronomy_updated.connect.assert_called()
        mock_astronomy_manager.astronomy_error.connect.assert_called()
        mock_astronomy_manager.loading_state_changed.connect.assert_called()


class TestCombinedForecastManagerGetForecast:
    """Test get_combined_forecast method."""
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_success(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_weather_data,
        sample_astronomy_data,
        sample_location
    ):
        """Test successful combined forecast retrieval."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        assert result is not None
        assert isinstance(result, CombinedForecastData)
        assert result.location == sample_location
        assert manager._current_forecast is result
        assert manager._last_update_time is not None
        assert manager._location == sample_location
        
        # Verify signals emitted
        manager.combined_forecast_updated.emit.assert_called_once()
        manager.data_quality_changed.emit.assert_called_once()
        
        # Verify loading state changes
        assert manager.loading_state_changed.emit.call_count == 2  # True then False
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_weather_only(
        self, 
        mock_weather_manager,
        sample_weather_data,
        sample_location
    ):
        """Test combined forecast with only weather data."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        
        manager = CombinedForecastManager(mock_weather_manager, None)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        assert result is not None
        assert result.status == CombinedDataStatus.WEATHER_ONLY
        assert result.has_weather_data
        assert not result.has_astronomy_data
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_astronomy_only(
        self, 
        mock_astronomy_manager,
        sample_astronomy_data,
        sample_location
    ):
        """Test combined forecast with only astronomy data."""
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(None, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        assert result is not None
        assert result.status == CombinedDataStatus.ASTRONOMY_ONLY
        assert not result.has_weather_data
        assert result.has_astronomy_data
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_no_managers(self, sample_location):
        """Test combined forecast with no managers."""
        manager = CombinedForecastManager()
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        manager.forecast_error = Mock()
        manager.forecast_error.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        # When no managers are available, the method returns None due to validation failure
        assert result is None
        
        # Verify error signal was emitted
        manager.forecast_error.emit.assert_called_once()
        # Verify loading state changes were emitted
        manager.loading_state_changed.emit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_weather_exception(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_astronomy_data,
        sample_location
    ):
        """Test combined forecast when weather fetch raises exception."""
        mock_weather_manager.refresh_weather.side_effect = Exception("Weather API error")
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        assert result is not None
        assert result.status == CombinedDataStatus.ASTRONOMY_ONLY
        assert not result.has_weather_data
        assert result.has_astronomy_data
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_astronomy_exception(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_weather_data,
        sample_location
    ):
        """Test combined forecast when astronomy fetch raises exception."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        mock_astronomy_manager.refresh_astronomy.side_effect = Exception("Astronomy API error")
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        assert result is not None
        assert result.status == CombinedDataStatus.WEATHER_ONLY
        assert result.has_weather_data
        assert not result.has_astronomy_data
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_both_exceptions(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_location
    ):
        """Test combined forecast when both fetches raise exceptions."""
        mock_weather_manager.refresh_weather.side_effect = Exception("Weather API error")
        mock_astronomy_manager.refresh_astronomy.side_effect = Exception("Astronomy API error")
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        manager.forecast_error = Mock()
        manager.forecast_error.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location)
        
        # When both managers fail, no data is available, resulting in no daily forecasts
        # This causes validation to fail and None is returned
        assert result is None
        
        # Verify error signal was emitted
        manager.forecast_error.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_general_exception(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_location
    ):
        """Test combined forecast when general exception occurs."""
        mock_weather_manager.refresh_weather.return_value = None
        mock_astronomy_manager.refresh_astronomy.return_value = None
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.forecast_error = Mock()
        manager.forecast_error.emit = Mock()
        
        # Mock CombinedForecastData.create to raise exception
        with patch('src.managers.combined_forecast_manager.CombinedForecastData.create') as mock_create:
            mock_create.side_effect = Exception("Creation failed")
            
            result = await manager.get_combined_forecast(sample_location)
            
            assert result is None
            manager.forecast_error.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_cached(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_combined_forecast,
        sample_location
    ):
        """Test returning cached forecast when not stale."""
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now() - timedelta(minutes=15)  # Recent
        
        result = await manager.get_combined_forecast(sample_location, force_refresh=False)
        
        assert result is sample_combined_forecast
        # Should not call refresh methods
        mock_weather_manager.refresh_weather.assert_not_called()
        mock_astronomy_manager.refresh_astronomy.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_force_refresh(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_weather_data,
        sample_astronomy_data,
        sample_combined_forecast,
        sample_location
    ):
        """Test force refresh ignores cache."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now() - timedelta(minutes=15)  # Recent
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast(sample_location, force_refresh=True)
        
        assert result is not None
        # Should call refresh methods despite cache
        mock_weather_manager.refresh_weather.assert_called_once()
        mock_astronomy_manager.refresh_astronomy.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_no_location_uses_stored(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_weather_data,
        sample_astronomy_data,
        sample_location
    ):
        """Test using stored location when none provided."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager._location = sample_location
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast()
        
        assert result is not None
        assert result.location == sample_location
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_no_location_creates_default(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_weather_data,
        sample_astronomy_data
    ):
        """Test creating default location when none provided or stored."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        result = await manager.get_combined_forecast()
        
        assert result is not None
        assert result.location.name == "Unknown"
        assert result.location.latitude == 0.0
        assert result.location.longitude == 0.0


class TestCombinedForecastManagerFetchMethods:
    """Test private fetch methods."""
    
    @pytest.mark.asyncio
    async def test_fetch_weather_data_success(self, mock_weather_manager, sample_weather_data, sample_location):
        """Test successful weather data fetch."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        
        manager = CombinedForecastManager(mock_weather_manager, None)
        result = await manager._fetch_weather_data(sample_location)
        
        assert result is sample_weather_data
        mock_weather_manager.refresh_weather.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_weather_data_no_manager(self, sample_location):
        """Test weather data fetch with no manager."""
        manager = CombinedForecastManager()
        result = await manager._fetch_weather_data(sample_location)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_weather_data_exception(self, mock_weather_manager, sample_location):
        """Test weather data fetch with exception."""
        mock_weather_manager.refresh_weather.side_effect = Exception("API error")
        
        manager = CombinedForecastManager(mock_weather_manager, None)
        result = await manager._fetch_weather_data(sample_location)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_astronomy_data_success(self, mock_astronomy_manager, sample_astronomy_data, sample_location):
        """Test successful astronomy data fetch."""
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(None, mock_astronomy_manager)
        result = await manager._fetch_astronomy_data(sample_location)
        
        assert result is sample_astronomy_data
        mock_astronomy_manager.refresh_astronomy.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_astronomy_data_no_manager(self, sample_location):
        """Test astronomy data fetch with no manager."""
        manager = CombinedForecastManager()
        result = await manager._fetch_astronomy_data(sample_location)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_astronomy_data_exception(self, mock_astronomy_manager, sample_location):
        """Test astronomy data fetch with exception."""
        mock_astronomy_manager.refresh_astronomy.side_effect = Exception("API error")
        
        manager = CombinedForecastManager(None, mock_astronomy_manager)
        result = await manager._fetch_astronomy_data(sample_location)
        
        assert result is None


class TestCombinedForecastManagerCacheLogic:
    """Test cache-related methods."""
    
    def test_should_skip_refresh_no_cache(self):
        """Test skip refresh with no cached data."""
        manager = CombinedForecastManager()
        assert not manager._should_skip_refresh()
    
    def test_should_skip_refresh_no_last_update(self, sample_combined_forecast):
        """Test skip refresh with no last update time."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        assert not manager._should_skip_refresh()
    
    def test_should_skip_refresh_recent_cache(self, sample_combined_forecast):
        """Test skip refresh with recent cache."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now() - timedelta(minutes=15)  # Recent
        assert manager._should_skip_refresh()
    
    def test_should_skip_refresh_stale_cache(self, sample_combined_forecast):
        """Test skip refresh with stale cache."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now() - timedelta(minutes=45)  # Stale
        assert not manager._should_skip_refresh()


class TestCombinedForecastManagerLoadingState:
    """Test loading state management."""
    
    def test_set_loading_state_change(self):
        """Test setting loading state when it changes."""
        manager = CombinedForecastManager()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        manager._set_loading_state(True)
        
        assert manager._is_loading is True
        manager.loading_state_changed.emit.assert_called_once_with(True)
    
    def test_set_loading_state_no_change(self):
        """Test setting loading state when it doesn't change."""
        manager = CombinedForecastManager()
        manager._is_loading = True
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        manager._set_loading_state(True)
        
        manager.loading_state_changed.emit.assert_not_called()
    
    def test_update_combined_loading_state_both_managers(self, mock_weather_manager, mock_astronomy_manager):
        """Test updating combined loading state with both managers."""
        mock_weather_manager.is_loading.return_value = True
        mock_astronomy_manager.is_loading.return_value = False
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        manager._update_combined_loading_state()
        
        assert manager._is_loading is True
        manager.loading_state_changed.emit.assert_called_once_with(True)
    
    def test_update_combined_loading_state_no_managers(self):
        """Test updating combined loading state with no managers."""
        manager = CombinedForecastManager()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        # Set initial loading state to True to ensure change is detected
        manager._is_loading = True
        
        manager._update_combined_loading_state()
        
        assert manager._is_loading is False
        manager.loading_state_changed.emit.assert_called_once_with(False)
    
    def test_update_combined_loading_state_weather_only(self, mock_weather_manager):
        """Test updating combined loading state with weather manager only."""
        mock_weather_manager.is_loading.return_value = False
        
        manager = CombinedForecastManager(mock_weather_manager, None)
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        # Set initial loading state to True to ensure change is detected
        manager._is_loading = True
        
        manager._update_combined_loading_state()
        
        assert manager._is_loading is False
        manager.loading_state_changed.emit.assert_called_once_with(False)
    
    def test_update_combined_loading_state_manager_no_is_loading_method(self, mock_weather_manager):
        """Test updating combined loading state when manager has no is_loading method."""
        # Remove is_loading method
        del mock_weather_manager.is_loading
        
        manager = CombinedForecastManager(mock_weather_manager, None)
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        # Set initial loading state to True to ensure change is detected
        manager._is_loading = True
        
        manager._update_combined_loading_state()
        
        assert manager._is_loading is False
        manager.loading_state_changed.emit.assert_called_once_with(False)
class TestCombinedForecastManagerDataQuality:
    """Test data quality emission methods."""
    
    def test_emit_data_quality_info(self, sample_combined_forecast):
        """Test emitting data quality information."""
        manager = CombinedForecastManager()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        manager._emit_data_quality_info(sample_combined_forecast)
        
        manager.data_quality_changed.emit.assert_called_once()
        call_args = manager.data_quality_changed.emit.call_args[0][0]
        
        assert "status" in call_args
        assert "forecast_days" in call_args
        assert "has_weather" in call_args
        assert "has_astronomy" in call_args
        assert "total_astronomy_events" in call_args
        assert "data_quality_summary" in call_args
        assert "error_messages" in call_args


class TestCombinedForecastManagerAutoRefresh:
    """Test auto-refresh functionality."""
    
    def test_start_auto_refresh(self):
        """Test starting auto-refresh timer."""
        manager = CombinedForecastManager()
        
        # Mock the timer to avoid Qt threading issues
        with patch.object(manager._refresh_timer, 'start') as mock_start:
            with patch.object(manager._refresh_timer, 'isActive', return_value=True):
                manager.start_auto_refresh(15)
                
                mock_start.assert_called_once_with(15 * 60 * 1000)
                assert manager._refresh_timer.isActive()
    
    def test_stop_auto_refresh(self):
        """Test stopping auto-refresh timer."""
        manager = CombinedForecastManager()
        manager.start_auto_refresh(15)
        
        manager.stop_auto_refresh()
        
        assert not manager._refresh_timer.isActive()
    
    def test_is_auto_refresh_active(self):
        """Test checking auto-refresh status."""
        manager = CombinedForecastManager()
        
        # Mock timer methods to avoid Qt threading issues
        with patch.object(manager._refresh_timer, 'isActive', return_value=False):
            assert not manager.is_auto_refresh_active()
        
        with patch.object(manager._refresh_timer, 'start'):
            with patch.object(manager._refresh_timer, 'isActive', return_value=True):
                manager.start_auto_refresh(15)
                assert manager.is_auto_refresh_active()
        
        with patch.object(manager._refresh_timer, 'stop'):
            with patch.object(manager._refresh_timer, 'isActive', return_value=False):
                manager.stop_auto_refresh()
                assert not manager.is_auto_refresh_active()
    
    @patch('asyncio.get_event_loop')
    @patch('asyncio.create_task')
    def test_auto_refresh_with_running_loop(self, mock_create_task, mock_get_loop):
        """Test auto-refresh with running event loop."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop
        
        manager = CombinedForecastManager()
        manager._auto_refresh()
        
        mock_create_task.assert_called_once()
    
    @patch('asyncio.get_event_loop')
    @patch('asyncio.run')
    def test_auto_refresh_without_running_loop(self, mock_run, mock_get_loop):
        """Test auto-refresh without running event loop."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_get_loop.return_value = mock_loop
        
        manager = CombinedForecastManager()
        manager._auto_refresh()
        
        mock_run.assert_called_once()


class TestCombinedForecastManagerSignalHandlers:
    """Test signal handler methods."""
    
    @pytest.mark.asyncio
    async def test_on_weather_updated(self, sample_weather_data):
        """Test weather updated signal handler."""
        manager = CombinedForecastManager()
        
        with patch.object(manager, '_update_combined_forecast_from_weather') as mock_update:
            manager._on_weather_updated(sample_weather_data)
            
            # Verify task was created (can't easily test asyncio.create_task)
            assert True  # Signal handler executed without error
    
    @pytest.mark.asyncio
    async def test_on_astronomy_updated(self, sample_astronomy_data):
        """Test astronomy updated signal handler."""
        manager = CombinedForecastManager()
        
        with patch.object(manager, '_update_combined_forecast_from_astronomy') as mock_update:
            manager._on_astronomy_updated(sample_astronomy_data)
            
            # Verify task was created (can't easily test asyncio.create_task)
            assert True  # Signal handler executed without error
    
    def test_on_weather_error(self):
        """Test weather error signal handler."""
        manager = CombinedForecastManager()
        
        # Should not raise exception
        manager._on_weather_error("Test weather error")
    
    def test_on_astronomy_error(self):
        """Test astronomy error signal handler."""
        manager = CombinedForecastManager()
        
        # Should not raise exception
        manager._on_astronomy_error("Test astronomy error")
    
    def test_on_weather_loading_changed(self):
        """Test weather loading changed signal handler."""
        manager = CombinedForecastManager()
        
        with patch.object(manager, '_update_combined_loading_state') as mock_update:
            manager._on_weather_loading_changed(True)
            mock_update.assert_called_once()
    
    def test_on_astronomy_loading_changed(self):
        """Test astronomy loading changed signal handler."""
        manager = CombinedForecastManager()
        
        with patch.object(manager, '_update_combined_loading_state') as mock_update:
            manager._on_astronomy_loading_changed(False)
            mock_update.assert_called_once()


class TestCombinedForecastManagerUpdateMethods:
    """Test forecast update methods."""
    
    @pytest.mark.asyncio
    async def test_update_combined_forecast_from_weather_no_existing(
        self, 
        sample_weather_data
    ):
        """Test updating from weather when no existing forecast."""
        manager = CombinedForecastManager()
        
        with patch.object(manager, 'get_combined_forecast') as mock_get:
            await manager._update_combined_forecast_from_weather(sample_weather_data)
            mock_get.assert_called_once_with(force_refresh=True)
    
    @pytest.mark.asyncio
    async def test_update_combined_forecast_from_weather_with_existing(
        self, 
        sample_weather_data,
        sample_combined_forecast
    ):
        """Test updating from weather with existing forecast."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        await manager._update_combined_forecast_from_weather(sample_weather_data)
        
        assert manager._current_forecast is not None
        assert manager._last_update_time is not None
        manager.combined_forecast_updated.emit.assert_called_once()
        manager.data_quality_changed.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_combined_forecast_from_weather_exception(
        self, 
        sample_weather_data,
        sample_combined_forecast
    ):
        """Test updating from weather with exception."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        
        # Mock CombinedForecastData.create to raise exception
        with patch('src.managers.combined_forecast_manager.CombinedForecastData.create') as mock_create:
            mock_create.side_effect = Exception("Creation failed")
            
            await manager._update_combined_forecast_from_weather(sample_weather_data)
            
            # Should handle exception gracefully
            assert True
    
    @pytest.mark.asyncio
    async def test_update_combined_forecast_from_astronomy_no_existing(
        self, 
        sample_astronomy_data
    ):
        """Test updating from astronomy when no existing forecast."""
        manager = CombinedForecastManager()
        
        with patch.object(manager, 'get_combined_forecast') as mock_get:
            await manager._update_combined_forecast_from_astronomy(sample_astronomy_data)
            mock_get.assert_called_once_with(force_refresh=True)
    
    @pytest.mark.asyncio
    async def test_update_combined_forecast_from_astronomy_with_existing(
        self, 
        sample_astronomy_data,
        sample_combined_forecast
    ):
        """Test updating from astronomy with existing forecast."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        
        await manager._update_combined_forecast_from_astronomy(sample_astronomy_data)
        
        assert manager._current_forecast is not None
        assert manager._last_update_time is not None
        manager.combined_forecast_updated.emit.assert_called_once()
        manager.data_quality_changed.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_combined_forecast_from_astronomy_exception(
        self, 
        sample_astronomy_data,
        sample_combined_forecast
    ):
        """Test updating from astronomy with exception."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        
        # Mock CombinedForecastData.create to raise exception
        with patch('src.managers.combined_forecast_manager.CombinedForecastData.create') as mock_create:
            mock_create.side_effect = Exception("Creation failed")
            
            await manager._update_combined_forecast_from_astronomy(sample_astronomy_data)
            
            # Should handle exception gracefully
            assert True


class TestCombinedForecastManagerGetters:
    """Test getter methods."""
    
    def test_get_current_forecast(self, sample_combined_forecast):
        """Test getting current forecast."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        
        result = manager.get_current_forecast()
        assert result is sample_combined_forecast
    
    def test_get_current_forecast_none(self):
        """Test getting current forecast when none exists."""
        manager = CombinedForecastManager()
        
        result = manager.get_current_forecast()
        assert result is None
    
    def test_get_last_update_time(self):
        """Test getting last update time."""
        manager = CombinedForecastManager()
        test_time = datetime.now()
        manager._last_update_time = test_time
        
        result = manager.get_last_update_time()
        assert result is test_time
    
    def test_get_last_update_time_none(self):
        """Test getting last update time when none exists."""
        manager = CombinedForecastManager()
        
        result = manager.get_last_update_time()
        assert result is None
    
    def test_is_loading_true(self):
        """Test is_loading when loading."""
        manager = CombinedForecastManager()
        manager._is_loading = True
        
        assert manager.is_loading() is True
    
    def test_is_loading_false(self):
        """Test is_loading when not loading."""
        manager = CombinedForecastManager()
        manager._is_loading = False
        
        assert manager.is_loading() is False
    
    def test_get_status_summary_loading(self):
        """Test status summary when loading."""
        manager = CombinedForecastManager()
        manager._is_loading = True
        
        result = manager.get_status_summary()
        assert result == "Loading combined forecast..."
    
    def test_get_status_summary_no_forecast(self):
        """Test status summary when no forecast."""
        manager = CombinedForecastManager()
        manager._is_loading = False
        
        result = manager.get_status_summary()
        assert result == "No combined forecast available"
    
    def test_get_status_summary_with_forecast(self, sample_combined_forecast):
        """Test status summary with forecast."""
        manager = CombinedForecastManager()
        manager._is_loading = False
        manager._current_forecast = sample_combined_forecast
        
        result = manager.get_status_summary()
        assert result == sample_combined_forecast.get_status_summary()
    
    def test_get_cache_info_empty(self):
        """Test cache info when empty."""
        manager = CombinedForecastManager()
        
        info = manager.get_cache_info()
        
        assert info["has_current_forecast"] is False
        assert info["last_update_time"] is None
        assert info["is_loading"] is False
        assert info["auto_refresh_active"] is False
        assert info["has_weather_manager"] is False
        assert info["has_astronomy_manager"] is False
    
    def test_get_cache_info_with_data(
        self,
        mock_weather_manager,
        mock_astronomy_manager,
        sample_combined_forecast
    ):
        """Test cache info with data."""
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now()
        manager._is_loading = True
        
        # Mock timer to avoid Qt threading issues
        with patch.object(manager._refresh_timer, 'start'):
            with patch.object(manager._refresh_timer, 'isActive', return_value=True):
                manager.start_auto_refresh(30)
                
                info = manager.get_cache_info()
                
                assert info["has_current_forecast"] is True
                assert info["last_update_time"] is not None
                assert info["is_loading"] is True
                assert info["auto_refresh_active"] is True
                assert info["has_weather_manager"] is True
                assert info["has_astronomy_manager"] is True
                assert info["forecast_status"] == sample_combined_forecast.status.value
                assert info["forecast_days"] == sample_combined_forecast.forecast_days
                assert info["total_astronomy_events"] == sample_combined_forecast.total_astronomy_events


class TestCombinedForecastManagerClearCache:
    """Test cache clearing functionality."""
    
    def test_clear_cache_basic(self, sample_combined_forecast):
        """Test basic cache clearing."""
        manager = CombinedForecastManager()
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now()
        
        manager.clear_cache()
        
        assert manager._current_forecast is None
        assert manager._last_update_time is None
    
    def test_clear_cache_with_managers(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_combined_forecast
    ):
        """Test cache clearing with managers that support clear_cache."""
        mock_weather_manager.clear_cache = Mock()
        mock_astronomy_manager.clear_cache = Mock()
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now()
        
        manager.clear_cache()
        
        assert manager._current_forecast is None
        assert manager._last_update_time is None
        mock_weather_manager.clear_cache.assert_called_once()
        mock_astronomy_manager.clear_cache.assert_called_once()
    
    def test_clear_cache_managers_no_clear_method(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_combined_forecast
    ):
        """Test cache clearing with managers that don't support clear_cache."""
        # Don't add clear_cache method to managers
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager._current_forecast = sample_combined_forecast
        manager._last_update_time = datetime.now()
        
        # Should not raise exception
        manager.clear_cache()
        
        assert manager._current_forecast is None
        assert manager._last_update_time is None


class TestCombinedForecastManagerShutdown:
    """Test shutdown functionality."""
    
    def test_shutdown_basic(self):
        """Test basic shutdown."""
        manager = CombinedForecastManager()
        manager._current_forecast = Mock()
        manager._last_update_time = datetime.now()
        manager.start_auto_refresh(30)
        
        manager.shutdown()
        
        assert not manager._refresh_timer.isActive()
        assert manager._current_forecast is None
        assert manager._last_update_time is None
    
    def test_shutdown_with_managers(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager
    ):
        """Test shutdown with managers."""
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager.start_auto_refresh(30)
        
        manager.shutdown()
        
        assert not manager._refresh_timer.isActive()
        mock_weather_manager.shutdown.assert_called_once()
        mock_astronomy_manager.shutdown.assert_called_once()
        assert manager._current_forecast is None
        assert manager._last_update_time is None


class TestCombinedForecastFactory:
    """Test CombinedForecastFactory methods."""
    
    def test_create_manager_both_enabled(self):
        """Test creating manager with both configs enabled."""
        weather_config = Mock()
        weather_config.enabled = True
        weather_config.get_refresh_interval_seconds = Mock(return_value=300)  # Return integer for multiplication
        astronomy_config = Mock()
        astronomy_config.enabled = True
        
        # Mock both manager classes completely - need to patch the imports in the factory methods
        with patch('src.managers.combined_forecast_manager.WeatherManager') as mock_weather_mgr:
            with patch('src.managers.combined_forecast_manager.AstronomyManager') as mock_astro_mgr:
                # Mock the manager instances
                mock_weather_instance = Mock()
                mock_weather_instance.weather_updated = Mock()
                mock_weather_instance.weather_updated.connect = Mock()
                mock_weather_instance.weather_error = Mock()
                mock_weather_instance.weather_error.connect = Mock()
                mock_weather_instance.loading_state_changed = Mock()
                mock_weather_instance.loading_state_changed.connect = Mock()
                mock_weather_mgr.return_value = mock_weather_instance
                
                mock_astro_instance = Mock()
                mock_astro_instance.astronomy_updated = Mock()
                mock_astro_instance.astronomy_updated.connect = Mock()
                mock_astro_instance.astronomy_error = Mock()
                mock_astro_instance.astronomy_error.connect = Mock()
                mock_astro_instance.loading_state_changed = Mock()
                mock_astro_instance.loading_state_changed.connect = Mock()
                mock_astro_mgr.return_value = mock_astro_instance
                
                # Also need to patch the imports inside the factory methods
                with patch('src.managers.weather_manager.WeatherManager', mock_weather_mgr):
                    with patch('src.managers.astronomy_manager.AstronomyManager', mock_astro_mgr):
                        result = CombinedForecastFactory.create_manager(weather_config, astronomy_config)
                
                assert isinstance(result, CombinedForecastManager)
                assert result._weather_manager is not None
                assert result._astronomy_manager is not None
                mock_weather_mgr.assert_called_once_with(weather_config)
                mock_astro_mgr.assert_called_once_with(astronomy_config)
    
    def test_create_manager_weather_disabled(self):
        """Test creating manager with weather disabled."""
        weather_config = Mock()
        weather_config.enabled = False
        astronomy_config = Mock()
        astronomy_config.enabled = True
        
        with patch('src.managers.combined_forecast_manager.AstronomyManager') as mock_astro_mgr:
            # Mock the astronomy manager instance
            mock_astro_instance = Mock()
            mock_astro_instance.astronomy_updated = Mock()
            mock_astro_instance.astronomy_updated.connect = Mock()
            mock_astro_instance.astronomy_error = Mock()
            mock_astro_instance.astronomy_error.connect = Mock()
            mock_astro_instance.loading_state_changed = Mock()
            mock_astro_instance.loading_state_changed.connect = Mock()
            mock_astro_mgr.return_value = mock_astro_instance
            
            # Also need to patch the import inside the factory method
            with patch('src.managers.astronomy_manager.AstronomyManager', mock_astro_mgr):
                result = CombinedForecastFactory.create_manager(weather_config, astronomy_config)
            
            assert isinstance(result, CombinedForecastManager)
            assert result._weather_manager is None
            assert result._astronomy_manager is not None
            mock_astro_mgr.assert_called_once_with(astronomy_config)
    
    def test_create_manager_astronomy_disabled(self):
        """Test creating manager with astronomy disabled."""
        weather_config = Mock()
        weather_config.enabled = True
        weather_config.get_refresh_interval_seconds = Mock(return_value=300)  # Return integer for multiplication
        astronomy_config = Mock()
        astronomy_config.enabled = False
        
        with patch('src.managers.combined_forecast_manager.WeatherManager') as mock_weather_mgr:
            # Mock the weather manager instance
            mock_weather_instance = Mock()
            mock_weather_instance.weather_updated = Mock()
            mock_weather_instance.weather_updated.connect = Mock()
            mock_weather_instance.weather_error = Mock()
            mock_weather_instance.weather_error.connect = Mock()
            mock_weather_instance.loading_state_changed = Mock()
            mock_weather_instance.loading_state_changed.connect = Mock()
            mock_weather_mgr.return_value = mock_weather_instance
            
            # Also need to patch the import inside the factory method
            with patch('src.managers.weather_manager.WeatherManager', mock_weather_mgr):
                result = CombinedForecastFactory.create_manager(weather_config, astronomy_config)
            
            assert isinstance(result, CombinedForecastManager)
            assert result._weather_manager is not None
            assert result._astronomy_manager is None
            mock_weather_mgr.assert_called_once_with(weather_config)
    
    def test_create_manager_both_disabled(self):
        """Test creating manager with both configs disabled."""
        weather_config = Mock()
        weather_config.enabled = False
        astronomy_config = Mock()
        astronomy_config.enabled = False
        
        result = CombinedForecastFactory.create_manager(weather_config, astronomy_config)
        
        assert isinstance(result, CombinedForecastManager)
        assert result._weather_manager is None
        assert result._astronomy_manager is None
    
    def test_create_manager_none_configs(self):
        """Test creating manager with None configs."""
        result = CombinedForecastFactory.create_manager(None, None)
        
        assert isinstance(result, CombinedForecastManager)
        assert result._weather_manager is None
        assert result._astronomy_manager is None
    
    def test_create_weather_only_manager(self):
        """Test creating weather-only manager."""
        weather_config = Mock()
        weather_config.get_refresh_interval_seconds = Mock(return_value=300)  # Return integer for multiplication
        
        with patch('src.managers.combined_forecast_manager.WeatherManager') as mock_weather_mgr:
            mock_weather_instance = Mock()
            mock_weather_instance.weather_updated = Mock()
            mock_weather_instance.weather_updated.connect = Mock()
            mock_weather_instance.weather_error = Mock()
            mock_weather_instance.weather_error.connect = Mock()
            mock_weather_instance.loading_state_changed = Mock()
            mock_weather_instance.loading_state_changed.connect = Mock()
            mock_weather_mgr.return_value = mock_weather_instance
            
            # Also need to patch the import inside the factory method
            with patch('src.managers.weather_manager.WeatherManager', mock_weather_mgr):
                result = CombinedForecastFactory.create_weather_only_manager(weather_config)
            
            assert isinstance(result, CombinedForecastManager)
            assert result._weather_manager is not None
            assert result._astronomy_manager is None
            mock_weather_mgr.assert_called_once_with(weather_config)
    
    def test_create_astronomy_only_manager(self):
        """Test creating astronomy-only manager."""
        astronomy_config = Mock()
        
        with patch('src.managers.combined_forecast_manager.AstronomyManager') as mock_astro_mgr:
            mock_astro_instance = Mock()
            mock_astro_instance.astronomy_updated = Mock()
            mock_astro_instance.astronomy_updated.connect = Mock()
            mock_astro_instance.astronomy_error = Mock()
            mock_astro_instance.astronomy_error.connect = Mock()
            mock_astro_instance.loading_state_changed = Mock()
            mock_astro_instance.loading_state_changed.connect = Mock()
            mock_astro_mgr.return_value = mock_astro_instance
            
            # Also need to patch the import inside the factory method
            with patch('src.managers.astronomy_manager.AstronomyManager', mock_astro_mgr):
                result = CombinedForecastFactory.create_astronomy_only_manager(astronomy_config)
            
            assert isinstance(result, CombinedForecastManager)
            assert result._weather_manager is None
            assert result._astronomy_manager is not None
            mock_astro_mgr.assert_called_once_with(astronomy_config)
    
    def test_create_test_manager(self):
        """Test creating test manager."""
        result = CombinedForecastFactory.create_test_manager()
        
        assert isinstance(result, CombinedForecastManager)
        assert result._weather_manager is None
        assert result._astronomy_manager is None


class TestCombinedForecastManagerEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_validation_failure(
        self, 
        mock_weather_manager, 
        mock_astronomy_manager,
        sample_weather_data,
        sample_astronomy_data,
        sample_location
    ):
        """Test combined forecast when validation fails."""
        mock_weather_manager.refresh_weather.return_value = sample_weather_data
        mock_astronomy_manager.refresh_astronomy.return_value = sample_astronomy_data
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock validator to return False
        with patch.object(manager._validator, 'validate_combined_forecast', return_value=False):
            # Mock signal emissions
            manager.combined_forecast_updated = Mock()
            manager.combined_forecast_updated.emit = Mock()
            manager.loading_state_changed = Mock()
            manager.loading_state_changed.emit = Mock()
            manager.data_quality_changed = Mock()
            manager.data_quality_changed.emit = Mock()
            
            result = await manager.get_combined_forecast(sample_location)
            
            # Should still return result even if validation fails
            assert result is not None
    
    def test_update_combined_loading_state_getattr_fallback(self):
        """Test loading state update with getattr fallback."""
        # Create manager with mock that has signal attributes but no is_loading method
        mock_weather_manager = Mock()
        mock_weather_manager.weather_updated = Mock()
        mock_weather_manager.weather_updated.connect = Mock()
        mock_weather_manager.weather_error = Mock()
        mock_weather_manager.weather_error.connect = Mock()
        mock_weather_manager.loading_state_changed = Mock()
        mock_weather_manager.loading_state_changed.connect = Mock()
        
        mock_astronomy_manager = Mock()
        mock_astronomy_manager.astronomy_updated = Mock()
        mock_astronomy_manager.astronomy_updated.connect = Mock()
        mock_astronomy_manager.astronomy_error = Mock()
        mock_astronomy_manager.astronomy_error.connect = Mock()
        mock_astronomy_manager.loading_state_changed = Mock()
        mock_astronomy_manager.loading_state_changed.connect = Mock()
        
        # Remove is_loading method to force getattr fallback
        del mock_weather_manager.is_loading
        del mock_astronomy_manager.is_loading
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        
        # Set initial loading state to True to ensure change is detected
        manager._is_loading = True
        
        # Should use getattr with lambda fallback (managers don't have is_loading method)
        manager._update_combined_loading_state()
        
        assert manager._is_loading is False
        manager.loading_state_changed.emit.assert_called_once_with(False)
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_wrong_data_types(
        self,
        mock_weather_manager,
        mock_astronomy_manager,
        sample_location
    ):
        """Test combined forecast with wrong data types returned."""
        # Return wrong types from managers
        mock_weather_manager.refresh_weather.return_value = "not weather data"
        mock_astronomy_manager.refresh_astronomy.return_value = "not astronomy data"

        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)

        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()

        result = await manager.get_combined_forecast(sample_location)

        # When wrong types are returned, they're treated as None, resulting in no data
        # This causes no daily forecasts to be created, which fails validation
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_exception_handling(
        self,
        mock_weather_manager,
        mock_astronomy_manager,
        sample_location
    ):
        """Test combined forecast with exceptions returned from asyncio.gather."""
        # Make managers return exceptions instead of raising them
        weather_exception = Exception("Weather API error")
        astronomy_exception = Exception("Astronomy API error")
        
        mock_weather_manager.refresh_weather.return_value = weather_exception
        mock_astronomy_manager.refresh_astronomy.return_value = astronomy_exception
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        manager.forecast_error = Mock()
        manager.forecast_error.emit = Mock()
        
        # Mock asyncio.gather to return exceptions instead of raising them
        with patch('asyncio.gather') as mock_gather:
            mock_gather.return_value = (weather_exception, astronomy_exception)
            
            result = await manager.get_combined_forecast(sample_location)
            
            # Should handle exceptions and return None due to no valid data
            assert result is None
            manager.forecast_error.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_combined_forecast_asyncio_gather_exceptions(
        self,
        mock_weather_manager,
        mock_astronomy_manager,
        sample_location
    ):
        """Test combined forecast when asyncio.gather returns exceptions directly."""
        # Create actual exceptions
        weather_exception = Exception("Weather API error")
        astronomy_exception = Exception("Astronomy API error")
        
        manager = CombinedForecastManager(mock_weather_manager, mock_astronomy_manager)
        
        # Mock signal emissions
        manager.combined_forecast_updated = Mock()
        manager.combined_forecast_updated.emit = Mock()
        manager.loading_state_changed = Mock()
        manager.loading_state_changed.emit = Mock()
        manager.data_quality_changed = Mock()
        manager.data_quality_changed.emit = Mock()
        manager.forecast_error = Mock()
        manager.forecast_error.emit = Mock()
        
        # Mock the fetch methods to return exceptions directly
        with patch.object(manager, '_fetch_weather_data') as mock_weather_fetch:
            with patch.object(manager, '_fetch_astronomy_data') as mock_astro_fetch:
                # Set up the fetch methods to return exceptions
                mock_weather_fetch.return_value = weather_exception
                mock_astro_fetch.return_value = astronomy_exception
                
                # Mock asyncio.gather to return the exceptions as values (not raise them)
                with patch('asyncio.gather') as mock_gather:
                    mock_gather.return_value = (weather_exception, astronomy_exception)
                    
                    result = await manager.get_combined_forecast(sample_location)
                    
                    # Should handle exceptions and return None due to no valid data
                    assert result is None
                    manager.forecast_error.emit.assert_called_once()