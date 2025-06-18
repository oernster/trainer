"""
Integration tests for weather functionality.
Author: Oliver Ernster

This module tests the integration between weather components
following solid Object-Oriented design principles.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.models.weather_data import (
    WeatherData, 
    WeatherForecastData, 
    Location,
    WeatherDataValidator,
    EmojiWeatherIconStrategy,
    WeatherIconProviderImpl
)
from src.managers.weather_config import WeatherConfig, WeatherConfigFactory
from src.managers.weather_manager import WeatherManager, WeatherObserver
from src.api.weather_api_manager import (
    WeatherAPIManager,
    OpenMeteoWeatherSource,
    AioHttpClient
)
from version import __weather_version__, __weather_api_provider__


class MockWeatherObserver(WeatherObserver):
    """Mock observer for testing weather updates."""
    
    def __init__(self):
        self.weather_data = None
        self.error = None
        self.loading_state = False
        self.update_count = 0
        self.error_count = 0
    
    def on_weather_updated(self, weather_data):
        self.weather_data = weather_data
        self.update_count += 1
    
    def on_weather_error(self, error):
        self.error = error
        self.error_count += 1
    
    def on_weather_loading(self, is_loading):
        self.loading_state = is_loading


class TestWeatherDataModels:
    """Test weather data models and validation."""
    
    def test_weather_data_creation(self):
        """Test WeatherData creation and validation."""
        weather = WeatherData(
            timestamp=datetime.now(),
            temperature=20.5,
            humidity=65,
            weather_code=1,
            description="Mainly clear"
        )
        
        assert weather.temperature == 20.5
        assert weather.humidity == 65
        assert weather.temperature_display == "20.5°C"
        assert weather.humidity_display == "65%"
        assert not weather.is_precipitation()
        assert not weather.is_severe_weather()
    
    def test_weather_data_validation(self):
        """Test weather data validation."""
        validator = WeatherDataValidator()
        
        # Valid data
        valid_weather = WeatherData(
            timestamp=datetime.now(),
            temperature=15.0,
            humidity=50,
            weather_code=0
        )
        assert validator.validate_weather_data(valid_weather)
        
        # Invalid humidity
        with pytest.raises(ValueError):
            WeatherData(
                timestamp=datetime.now(),
                temperature=15.0,
                humidity=150,  # Invalid
                weather_code=0
            )
    
    def test_location_validation(self):
        """Test location validation."""
        # Valid location
        location = Location("London", 51.5074, -0.1278)
        assert location.name == "London"
        assert location.latitude == 51.5074
        
        # Invalid latitude
        with pytest.raises(ValueError):
            Location("Invalid", 91.0, 0.0)  # Latitude > 90
    
    def test_weather_forecast_data(self):
        """Test WeatherForecastData functionality."""
        location = Location("London", 51.5074, -0.1278)
        
        # Create test weather data
        now = datetime.now()
        hourly_data = [
            WeatherData(now + timedelta(hours=i), 20.0 + i, 50, 0)
            for i in range(8)
        ]
        daily_data = [
            WeatherData(now + timedelta(days=i), 18.0 + i, 55, 1)
            for i in range(7)
        ]
        
        forecast = WeatherForecastData(
            location=location,
            hourly_forecast=hourly_data,
            daily_forecast=daily_data
        )
        
        assert len(forecast.hourly_forecast) == 8
        assert len(forecast.daily_forecast) == 7
        assert forecast.location.name == "London"
        assert not forecast.is_stale  # Just created
        
        # Test current day hourly
        today_hourly = forecast.current_day_hourly
        assert len(today_hourly) <= 8  # May be filtered by date


class TestWeatherIconStrategy:
    """Test weather icon strategy pattern."""
    
    def test_emoji_icon_strategy(self):
        """Test emoji weather icon strategy."""
        strategy = EmojiWeatherIconStrategy()
        
        assert strategy.get_icon(0) == "☀️"  # Clear sky
        assert strategy.get_icon(95) == "⛈️"  # Thunderstorm
        assert strategy.get_icon(999) == "❓"  # Unknown code
        assert strategy.get_strategy_name() == "emoji"
    
    def test_weather_icon_provider(self):
        """Test weather icon provider context."""
        strategy = EmojiWeatherIconStrategy()
        provider = WeatherIconProviderImpl(strategy)
        
        assert provider.get_weather_icon(0) == "☀️"
        assert provider.get_current_strategy_name() == "emoji"
        
        # Test strategy switching
        new_strategy = EmojiWeatherIconStrategy()
        provider.set_strategy(new_strategy)
        assert provider.get_current_strategy_name() == "emoji"


class TestWeatherConfiguration:
    """Test weather configuration management."""
    
    def test_weather_config_creation(self):
        """Test weather configuration creation."""
        config = WeatherConfig()
        
        assert config.enabled is True
        assert config.location_name == "London"
        assert config.api_provider == __weather_api_provider__
        assert config.config_version == __weather_version__
    
    def test_weather_config_factory(self):
        """Test weather configuration factory."""
        # Default config
        default_config = WeatherConfigFactory.create_default_config()
        assert default_config.location_name == "London"
        
        # London config
        london_config = WeatherConfigFactory.create_london_config()
        assert london_config.location_latitude == 51.5074
        
        # Waterloo config
        waterloo_config = WeatherConfigFactory.create_waterloo_config()
        assert waterloo_config.location_name == "London Waterloo"
        
        # Custom config
        custom_config = WeatherConfigFactory.create_custom_config(
            "Test Location", 50.0, 1.0
        )
        assert custom_config.location_name == "Test Location"
        assert custom_config.location_latitude == 50.0
    
    def test_weather_config_validation(self):
        """Test weather configuration validation."""
        config = WeatherConfig()
        
        # Test coordinate validation
        assert config.get_coordinates() == (51.5074, -0.1278)
        assert config.is_metric_units() is True
        
        # Test invalid coordinates
        with pytest.raises(ValueError):
            WeatherConfig(location_latitude=91.0)  # Invalid latitude


class TestWeatherManager:
    """Test weather manager business logic."""
    
    @pytest.fixture
    def weather_config(self):
        """Create test weather configuration."""
        return WeatherConfigFactory.create_default_config()
    
    @pytest.fixture
    def mock_observer(self):
        """Create mock weather observer."""
        return MockWeatherObserver()
    
    def test_weather_manager_initialization(self, weather_config):
        """Test weather manager initialization."""
        manager = WeatherManager(weather_config)
        
        assert manager._config == weather_config
        assert manager._fetch_count == 0
        assert manager._error_count == 0
        assert manager.get_observer_count() == 0
    
    def test_weather_observer_pattern(self, weather_config, mock_observer):
        """Test observer pattern implementation."""
        manager = WeatherManager(weather_config)
        
        # Attach observer
        manager.attach(mock_observer)
        assert manager.get_observer_count() == 1
        
        # Detach observer
        manager.detach(mock_observer)
        assert manager.get_observer_count() == 0
    
    def test_weather_manager_statistics(self, weather_config):
        """Test weather manager statistics."""
        manager = WeatherManager(weather_config)
        stats = manager.get_statistics()
        
        assert stats["fetch_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["config_version"] == __weather_version__
        assert stats["api_provider"] == __weather_api_provider__
    
    def test_auto_refresh_control(self, weather_config):
        """Test auto-refresh functionality."""
        # Disable auto-start for testing
        weather_config.enabled = False
        manager = WeatherManager(weather_config)
        
        # Should not start automatically when disabled
        assert not manager.is_auto_refresh_active()
        
        # Test manual control
        manager.stop_auto_refresh()
        assert not manager.is_auto_refresh_active()
        
        # Note: Can't test start_auto_refresh without QApplication
        # This would require a Qt test environment


class TestWeatherAPIIntegration:
    """Test weather API integration."""
    
    @pytest.fixture
    def weather_config(self):
        """Create test weather configuration."""
        return WeatherConfigFactory.create_default_config()
    
    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return Mock(spec=AioHttpClient)
    
    def test_openmeteo_weather_source(self, weather_config, mock_http_client):
        """Test Open-Meteo weather source."""
        source = OpenMeteoWeatherSource(mock_http_client, weather_config)
        
        assert source.get_source_name() == __weather_api_provider__
        assert "open-meteo.com" in source.get_source_url()
    
    @pytest.mark.asyncio
    async def test_weather_api_manager_caching(self, weather_config):
        """Test weather API manager caching."""
        # Mock weather source
        mock_source = Mock()
        mock_source.fetch_weather_data = AsyncMock()
        
        # Create test forecast data
        location = Location("London", 51.5074, -0.1278)
        test_weather = WeatherData(datetime.now(), 20.0, 50, 0)
        test_forecast = WeatherForecastData(
            location=location,
            hourly_forecast=[test_weather],
            daily_forecast=[]
        )
        mock_source.fetch_weather_data.return_value = test_forecast
        
        manager = WeatherAPIManager(mock_source, weather_config)
        
        # First call should fetch from source
        result1 = await manager.get_weather_forecast()
        assert mock_source.fetch_weather_data.call_count == 1
        assert result1 == test_forecast
        
        # Second call should use cache
        result2 = await manager.get_weather_forecast()
        assert mock_source.fetch_weather_data.call_count == 1  # No additional call
        assert result2 == test_forecast
        
        # Clear cache and verify fresh fetch
        manager.clear_cache()
        result3 = await manager.get_weather_forecast()
        assert mock_source.fetch_weather_data.call_count == 2  # New call made


class TestWeatherIntegrationEnd2End:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_weather_flow(self):
        """Test complete weather integration flow."""
        # Create configuration
        config = WeatherConfigFactory.create_default_config()
        
        # Create weather manager
        manager = WeatherManager(config)
        
        # Create mock observer
        observer = MockWeatherObserver()
        manager.attach(observer)
        
        # Mock the API response
        with patch.object(manager._api_manager, 'get_weather_forecast') as mock_fetch:
            # Create test data
            location = Location("London", 51.5074, -0.1278)
            test_forecast = WeatherForecastData(
                location=location,
                hourly_forecast=[
                    WeatherData(datetime.now(), 20.0, 50, 0)
                ],
                daily_forecast=[
                    WeatherData(datetime.now(), 18.0, 55, 1)
                ]
            )
            mock_fetch.return_value = test_forecast
            
            # Trigger refresh
            await manager.refresh_weather()
            
            # Verify observer was notified
            assert observer.update_count == 1
            assert observer.weather_data == test_forecast
            assert observer.error_count == 0
            
            # Verify manager state
            assert manager.get_current_data() == test_forecast
            assert not manager.is_data_stale()
            
            # Verify statistics
            stats = manager.get_statistics()
            assert stats["fetch_count"] == 1
            assert stats["error_count"] == 0
            assert stats["success_rate"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__])