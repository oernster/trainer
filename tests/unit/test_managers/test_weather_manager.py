"""
Comprehensive tests for weather manager to achieve 100% test coverage.
Author: Oliver Ernster

This module provides complete test coverage for all classes and methods
in the weather_manager.py module.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Optional
from PySide6.QtCore import QTimer, QObject

from src.managers.weather_manager import (
    WeatherObserver,
    WeatherSubject,
    WeatherCommand,
    RefreshWeatherCommand,
    WeatherErrorHandler,
    WeatherManager
)
from src.managers.weather_config import WeatherConfig
from src.models.weather_data import WeatherForecastData, Location, WeatherData
from src.api.weather_api_manager import (
    WeatherAPIException,
    WeatherNetworkException,
    WeatherDataException
)


class TestWeatherObserver:
    """Test WeatherObserver abstract base class."""
    
    def test_weather_observer_is_abstract(self):
        """Test that WeatherObserver cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WeatherObserver()


class MockWeatherObserver(WeatherObserver):
    """Mock implementation of WeatherObserver for testing."""
    
    def __init__(self):
        self.weather_updated_calls = []
        self.weather_error_calls = []
        self.weather_loading_calls = []
    
    def on_weather_updated(self, weather_data: WeatherForecastData) -> None:
        self.weather_updated_calls.append(weather_data)
    
    def on_weather_error(self, error: Exception) -> None:
        self.weather_error_calls.append(error)
    
    def on_weather_loading(self, is_loading: bool) -> None:
        self.weather_loading_calls.append(is_loading)


class TestWeatherSubject:
    """Test WeatherSubject implementation."""
    
    @pytest.fixture
    def weather_subject(self):
        """Create WeatherSubject instance."""
        return WeatherSubject()
    
    @pytest.fixture
    def mock_observer(self):
        """Create mock observer."""
        return MockWeatherObserver()
    
    def test_init(self, weather_subject):
        """Test WeatherSubject initialization."""
        assert weather_subject._observers == []
        assert weather_subject._loading_state is False
        assert weather_subject.get_observer_count() == 0
    
    def test_attach_observer(self, weather_subject, mock_observer):
        """Test attaching an observer."""
        weather_subject.attach(mock_observer)
        
        assert mock_observer in weather_subject._observers
        assert weather_subject.get_observer_count() == 1
    
    def test_attach_duplicate_observer(self, weather_subject, mock_observer):
        """Test attaching the same observer twice."""
        weather_subject.attach(mock_observer)
        weather_subject.attach(mock_observer)  # Should not add duplicate
        
        assert weather_subject.get_observer_count() == 1
    
    def test_detach_observer(self, weather_subject, mock_observer):
        """Test detaching an observer."""
        weather_subject.attach(mock_observer)
        weather_subject.detach(mock_observer)
        
        assert mock_observer not in weather_subject._observers
        assert weather_subject.get_observer_count() == 0
    
    def test_detach_nonexistent_observer(self, weather_subject, mock_observer):
        """Test detaching an observer that wasn't attached."""
        # Should not raise an exception
        weather_subject.detach(mock_observer)
        assert weather_subject.get_observer_count() == 0
    
    def test_notify_weather_updated(self, weather_subject, mock_observer):
        """Test notifying observers of weather update."""
        weather_subject.attach(mock_observer)
        
        mock_weather_data = Mock(spec=WeatherForecastData)
        weather_subject.notify_weather_updated(mock_weather_data)
        
        assert len(mock_observer.weather_updated_calls) == 1
        assert mock_observer.weather_updated_calls[0] == mock_weather_data
    
    def test_notify_weather_updated_observer_exception(self, weather_subject):
        """Test weather update notification with observer exception."""
        failing_observer = Mock(spec=WeatherObserver)
        failing_observer.on_weather_updated.side_effect = Exception("Observer failed")
        
        weather_subject.attach(failing_observer)
        
        mock_weather_data = Mock(spec=WeatherForecastData)
        # Should not raise exception, just log error
        weather_subject.notify_weather_updated(mock_weather_data)
        
        failing_observer.on_weather_updated.assert_called_once_with(mock_weather_data)
    
    def test_notify_weather_error(self, weather_subject, mock_observer):
        """Test notifying observers of weather error."""
        weather_subject.attach(mock_observer)
        
        test_error = Exception("Test error")
        weather_subject.notify_weather_error(test_error)
        
        assert len(mock_observer.weather_error_calls) == 1
        assert mock_observer.weather_error_calls[0] == test_error
    
    def test_notify_weather_error_observer_exception(self, weather_subject):
        """Test weather error notification with observer exception."""
        failing_observer = Mock(spec=WeatherObserver)
        failing_observer.on_weather_error.side_effect = Exception("Observer failed")
        
        weather_subject.attach(failing_observer)
        
        test_error = Exception("Test error")
        # Should not raise exception, just log error
        weather_subject.notify_weather_error(test_error)
        
        failing_observer.on_weather_error.assert_called_once_with(test_error)
    
    def test_notify_loading_state(self, weather_subject, mock_observer):
        """Test notifying observers of loading state change."""
        weather_subject.attach(mock_observer)
        
        weather_subject.notify_loading_state(True)
        
        assert len(mock_observer.weather_loading_calls) == 1
        assert mock_observer.weather_loading_calls[0] is True
        assert weather_subject._loading_state is True
    
    def test_notify_loading_state_no_change(self, weather_subject, mock_observer):
        """Test loading state notification when state doesn't change."""
        weather_subject.attach(mock_observer)
        weather_subject._loading_state = True
        
        weather_subject.notify_loading_state(True)  # Same state
        
        assert len(mock_observer.weather_loading_calls) == 0
    
    def test_notify_loading_state_observer_exception(self, weather_subject):
        """Test loading state notification with observer exception."""
        failing_observer = Mock(spec=WeatherObserver)
        failing_observer.on_weather_loading.side_effect = Exception("Observer failed")
        
        weather_subject.attach(failing_observer)
        
        # Should not raise exception, just log error
        weather_subject.notify_loading_state(True)
        
        failing_observer.on_weather_loading.assert_called_once_with(True)


class TestWeatherCommand:
    """Test WeatherCommand abstract base class."""
    
    def test_weather_command_is_abstract(self):
        """Test that WeatherCommand cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WeatherCommand()


class TestRefreshWeatherCommand:
    """Test RefreshWeatherCommand implementation."""
    
    @pytest.fixture
    def mock_weather_manager(self):
        """Create mock weather manager."""
        manager = Mock()
        manager.get_current_data.return_value = None
        manager._fetch_weather_internal = AsyncMock()
        manager._set_weather_data = Mock()
        return manager
    
    @pytest.fixture
    def mock_location(self):
        """Create mock location."""
        return Location("London", 51.5074, -0.1278)
    
    def test_init_with_location(self, mock_weather_manager, mock_location):
        """Test RefreshWeatherCommand initialization with location."""
        command = RefreshWeatherCommand(mock_weather_manager, mock_location)
        
        assert command._weather_manager == mock_weather_manager
        assert command._location == mock_location
        assert command._previous_data is None
    
    def test_init_without_location(self, mock_weather_manager):
        """Test RefreshWeatherCommand initialization without location."""
        command = RefreshWeatherCommand(mock_weather_manager)
        
        assert command._weather_manager == mock_weather_manager
        assert command._location is None
        assert command._previous_data is None
    
    @pytest.mark.asyncio
    async def test_execute(self, mock_weather_manager, mock_location):
        """Test command execution."""
        mock_previous_data = Mock(spec=WeatherForecastData)
        mock_weather_manager.get_current_data.return_value = mock_previous_data
        
        command = RefreshWeatherCommand(mock_weather_manager, mock_location)
        await command.execute()
        
        assert command._previous_data == mock_previous_data
        mock_weather_manager._fetch_weather_internal.assert_called_once_with(mock_location)
    
    @pytest.mark.asyncio
    async def test_undo_with_previous_data(self, mock_weather_manager, mock_location):
        """Test command undo with previous data."""
        mock_previous_data = Mock(spec=WeatherForecastData)
        
        command = RefreshWeatherCommand(mock_weather_manager, mock_location)
        command._previous_data = mock_previous_data
        
        await command.undo()
        
        mock_weather_manager._set_weather_data.assert_called_once_with(mock_previous_data)
    
    @pytest.mark.asyncio
    async def test_undo_without_previous_data(self, mock_weather_manager, mock_location):
        """Test command undo without previous data."""
        command = RefreshWeatherCommand(mock_weather_manager, mock_location)
        command._previous_data = None
        
        await command.undo()
        
        mock_weather_manager._set_weather_data.assert_not_called()
    
    def test_get_description_with_location(self, mock_weather_manager, mock_location):
        """Test get_description with location."""
        command = RefreshWeatherCommand(mock_weather_manager, mock_location)
        description = command.get_description()
        
        assert "London" in description
        assert "Refresh weather" in description
    
    def test_get_description_without_location(self, mock_weather_manager):
        """Test get_description without location."""
        command = RefreshWeatherCommand(mock_weather_manager)
        description = command.get_description()
        
        assert "default location" in description
        assert "Refresh weather" in description


class TestWeatherErrorHandler:
    """Test WeatherErrorHandler implementation."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock()
    
    @pytest.fixture
    def error_handler(self, mock_logger):
        """Create WeatherErrorHandler instance."""
        return WeatherErrorHandler(mock_logger)
    
    def test_init(self, mock_logger):
        """Test WeatherErrorHandler initialization."""
        handler = WeatherErrorHandler(mock_logger)
        
        assert handler._logger == mock_logger
        assert len(handler._error_strategies) == 4
    
    def test_handle_api_error(self, error_handler, mock_logger):
        """Test handling WeatherAPIException."""
        error = WeatherAPIException("API error")
        message = error_handler.handle_error(error)
        
        assert "Unable to fetch weather data" in message
        mock_logger.error.assert_called_once()
    
    def test_handle_network_error(self, error_handler, mock_logger):
        """Test handling WeatherNetworkException."""
        error = WeatherNetworkException("Network error")
        message = error_handler.handle_error(error)
        
        # The error handler uses isinstance check, so WeatherNetworkException
        # inherits from WeatherAPIException and gets handled by the API error handler
        assert "Unable to fetch weather data" in message
        mock_logger.error.assert_called_once()
    
    def test_handle_data_error(self, error_handler, mock_logger):
        """Test handling WeatherDataException."""
        error = WeatherDataException("Data error")
        message = error_handler.handle_error(error)
        
        # Same issue - WeatherDataException inherits from WeatherAPIException
        assert "Unable to fetch weather data" in message
        mock_logger.error.assert_called_once()
    
    def test_handle_generic_error(self, error_handler, mock_logger):
        """Test handling generic Exception."""
        error = ValueError("Generic error")
        message = error_handler.handle_error(error)
        
        assert "An unexpected error occurred" in message
        mock_logger.error.assert_called_once()
    
    def test_handle_error_inheritance(self, error_handler, mock_logger):
        """Test error handling with inheritance (WeatherAPIException subclass)."""
        # WeatherNetworkException inherits from WeatherAPIException
        error = WeatherNetworkException("Network error")
        message = error_handler.handle_error(error)
        
        # Due to isinstance check order, it uses the first matching handler (WeatherAPIException)
        assert "Unable to fetch weather data" in message


class TestWeatherManager:
    """Test WeatherManager implementation."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock weather config."""
        config = Mock(spec=WeatherConfig)
        config.enabled = True
        config.refresh_interval_minutes = 30
        config.get_refresh_interval_seconds.return_value = 1800
        config.api_provider = "test_provider"
        return config
    
    @pytest.fixture
    def mock_api_manager(self):
        """Create mock API manager."""
        manager = AsyncMock()
        manager.get_weather_forecast = AsyncMock()
        manager.clear_cache = Mock()
        manager.shutdown_sync = Mock()
        return manager
    
    @pytest.fixture
    def mock_weather_data(self):
        """Create mock weather forecast data."""
        data = Mock(spec=WeatherForecastData)
        data.get_current_weather.return_value = Mock(spec=WeatherData)
        data.current_day_hourly = [Mock(spec=WeatherData)]
        data.daily_forecast = [Mock(spec=WeatherData)]
        data.is_stale = False
        return data
    
    @pytest.fixture
    def weather_manager(self, mock_config):
        """Create WeatherManager instance with mocked dependencies."""
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            mock_api_manager = AsyncMock()
            mock_factory.create_manager_from_config.return_value = mock_api_manager
            
            with patch('src.managers.weather_manager.QTimer') as mock_timer_class:
                mock_timer = Mock()
                mock_timer_class.return_value = mock_timer
                
                manager = WeatherManager(mock_config)
                manager._api_manager = mock_api_manager
                manager._refresh_timer = mock_timer
                
                return manager
    
    def test_init(self, mock_config):
        """Test WeatherManager initialization."""
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            mock_api_manager = AsyncMock()
            mock_factory.create_manager_from_config.return_value = mock_api_manager
            
            with patch('src.managers.weather_manager.QTimer'):
                manager = WeatherManager(mock_config)
                
                assert manager._config == mock_config
                assert manager._current_forecast is None
                assert manager._fetch_count == 0
                assert manager._error_count == 0
                assert manager._last_successful_fetch is None
                assert len(manager._command_history) == 0
                assert manager._max_history_size == 10
    
    def test_start_auto_refresh_enabled(self, weather_manager, mock_config):
        """Test starting auto-refresh when enabled."""
        mock_config.enabled = True
        weather_manager._config = mock_config
        
        # Reset the mock since constructor already called start
        weather_manager._refresh_timer.start.reset_mock()
        
        weather_manager.start_auto_refresh()
        
        weather_manager._refresh_timer.start.assert_called_once_with(1800000)  # 30 min * 60 sec * 1000 ms
    
    def test_start_auto_refresh_disabled(self, weather_manager, mock_config):
        """Test starting auto-refresh when disabled."""
        mock_config.enabled = False
        weather_manager._config = mock_config
        
        # Reset the mock since constructor already called start
        weather_manager._refresh_timer.start.reset_mock()
        
        weather_manager.start_auto_refresh()
        
        weather_manager._refresh_timer.start.assert_not_called()
    
    def test_stop_auto_refresh(self, weather_manager):
        """Test stopping auto-refresh."""
        weather_manager.stop_auto_refresh()
        
        weather_manager._refresh_timer.stop.assert_called_once()
    
    def test_is_auto_refresh_active(self, weather_manager):
        """Test checking auto-refresh status."""
        weather_manager._refresh_timer.isActive.return_value = True
        
        assert weather_manager.is_auto_refresh_active() is True
        weather_manager._refresh_timer.isActive.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_weather_with_location(self, weather_manager):
        """Test manual weather refresh with location."""
        mock_location = Location("London", 51.5074, -0.1278)
        
        with patch.object(weather_manager, '_execute_command') as mock_execute:
            await weather_manager.refresh_weather(mock_location)
            
            mock_execute.assert_called_once()
            command = mock_execute.call_args[0][0]
            assert isinstance(command, RefreshWeatherCommand)
            assert command._location == mock_location
    
    @pytest.mark.asyncio
    async def test_refresh_weather_without_location(self, weather_manager):
        """Test manual weather refresh without location."""
        with patch.object(weather_manager, '_execute_command') as mock_execute:
            await weather_manager.refresh_weather()
            
            mock_execute.assert_called_once()
            command = mock_execute.call_args[0][0]
            assert isinstance(command, RefreshWeatherCommand)
            assert command._location is None
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, weather_manager):
        """Test successful command execution."""
        mock_command = AsyncMock(spec=WeatherCommand)
        mock_command.get_description.return_value = "Test command"
        
        await weather_manager._execute_command(mock_command)
        
        mock_command.execute.assert_called_once()
        assert mock_command in weather_manager._command_history
    
    @pytest.mark.asyncio
    async def test_execute_command_failure(self, weather_manager):
        """Test command execution failure."""
        mock_command = AsyncMock(spec=WeatherCommand)
        mock_command.execute.side_effect = Exception("Command failed")
        
        with pytest.raises(Exception, match="Command failed"):
            await weather_manager._execute_command(mock_command)
        
        assert mock_command not in weather_manager._command_history
    
    @pytest.mark.asyncio
    async def test_execute_command_history_limit(self, weather_manager):
        """Test command history size limit."""
        weather_manager._max_history_size = 2
        
        # Add commands up to limit
        for i in range(3):
            mock_command = AsyncMock(spec=WeatherCommand)
            mock_command.get_description.return_value = f"Command {i}"
            await weather_manager._execute_command(mock_command)
        
        # Should only keep the last 2 commands
        assert len(weather_manager._command_history) == 2
    
    @pytest.mark.asyncio
    async def test_undo_last_command_success(self, weather_manager):
        """Test successful command undo."""
        mock_command = AsyncMock(spec=WeatherCommand)
        mock_command.get_description.return_value = "Test command"
        weather_manager._command_history.append(mock_command)
        
        await weather_manager.undo_last_command()
        
        mock_command.undo.assert_called_once()
        assert mock_command not in weather_manager._command_history
    
    @pytest.mark.asyncio
    async def test_undo_last_command_failure(self, weather_manager):
        """Test command undo failure."""
        mock_command = AsyncMock(spec=WeatherCommand)
        mock_command.undo.side_effect = Exception("Undo failed")
        mock_command.get_description.return_value = "Test command"
        weather_manager._command_history.append(mock_command)
        
        with pytest.raises(Exception, match="Undo failed"):
            await weather_manager.undo_last_command()
    
    @pytest.mark.asyncio
    async def test_undo_last_command_empty_history(self, weather_manager):
        """Test undo with empty command history."""
        # Should not raise exception
        await weather_manager.undo_last_command()
    
    @pytest.mark.asyncio
    async def test_fetch_weather_internal_success(self, weather_manager, mock_weather_data):
        """Test successful internal weather fetch."""
        weather_manager._api_manager.get_weather_forecast.return_value = mock_weather_data
        
        with patch.object(weather_manager, 'notify_loading_state') as mock_notify_loading:
            with patch.object(weather_manager, 'notify_weather_updated') as mock_notify_updated:
                await weather_manager._fetch_weather_internal()
        
        assert weather_manager._current_forecast == mock_weather_data
        assert weather_manager._fetch_count == 1
        assert weather_manager._last_successful_fetch is not None
        
        # Check loading state notifications
        mock_notify_loading.assert_any_call(True)
        mock_notify_loading.assert_any_call(False)
        mock_notify_updated.assert_called_once_with(mock_weather_data)
    
    @pytest.mark.asyncio
    async def test_fetch_weather_internal_failure(self, weather_manager):
        """Test internal weather fetch failure."""
        test_error = WeatherAPIException("API failed")
        weather_manager._api_manager.get_weather_forecast.side_effect = test_error
        
        with patch.object(weather_manager, 'notify_loading_state') as mock_notify_loading:
            with patch.object(weather_manager, 'notify_weather_error') as mock_notify_error:
                with pytest.raises(WeatherAPIException):
                    await weather_manager._fetch_weather_internal()
        
        assert weather_manager._error_count == 1
        
        # Check notifications
        mock_notify_loading.assert_any_call(True)
        mock_notify_loading.assert_any_call(False)
        mock_notify_error.assert_called_once_with(test_error)
    
    def test_on_refresh_timer_enabled(self, weather_manager, mock_config):
        """Test auto-refresh timer when enabled."""
        mock_config.enabled = True
        weather_manager._config = mock_config
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            with patch('asyncio.create_task') as mock_create_task:
                mock_loop = Mock()
                mock_loop.is_running.return_value = True
                mock_get_loop.return_value = mock_loop
                
                weather_manager._on_refresh_timer()
                
                mock_create_task.assert_called_once()
    
    def test_on_refresh_timer_disabled(self, weather_manager, mock_config):
        """Test auto-refresh timer when disabled."""
        mock_config.enabled = False
        weather_manager._config = mock_config
        
        with patch.object(weather_manager, 'stop_auto_refresh') as mock_stop:
            weather_manager._on_refresh_timer()
            
            mock_stop.assert_called_once()
    
    def test_on_refresh_timer_no_running_loop(self, weather_manager, mock_config):
        """Test auto-refresh timer with no running event loop."""
        mock_config.enabled = True
        weather_manager._config = mock_config
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            with patch('asyncio.run') as mock_run:
                mock_loop = Mock()
                mock_loop.is_running.return_value = False
                mock_get_loop.return_value = mock_loop
                
                weather_manager._on_refresh_timer()
                
                mock_run.assert_called_once()
    
    def test_get_current_data(self, weather_manager, mock_weather_data):
        """Test getting current weather data."""
        weather_manager._current_forecast = mock_weather_data
        
        result = weather_manager.get_current_data()
        
        assert result == mock_weather_data
    
    def test_get_current_data_none(self, weather_manager):
        """Test getting current weather data when none exists."""
        result = weather_manager.get_current_data()
        
        assert result is None
    
    def test_set_weather_data(self, weather_manager, mock_weather_data):
        """Test setting weather data."""
        with patch.object(weather_manager, 'notify_weather_updated') as mock_notify:
            weather_manager._set_weather_data(mock_weather_data)
        
        assert weather_manager._current_forecast == mock_weather_data
        mock_notify.assert_called_once_with(mock_weather_data)
    
    def test_get_current_weather(self, weather_manager, mock_weather_data):
        """Test getting current weather conditions."""
        weather_manager._current_forecast = mock_weather_data
        
        result = weather_manager.get_current_weather()
        
        assert result == mock_weather_data.get_current_weather.return_value
    
    def test_get_current_weather_no_forecast(self, weather_manager):
        """Test getting current weather when no forecast exists."""
        result = weather_manager.get_current_weather()
        
        assert result is None
    
    def test_get_today_hourly(self, weather_manager, mock_weather_data):
        """Test getting today's hourly forecast."""
        weather_manager._current_forecast = mock_weather_data
        
        result = weather_manager.get_today_hourly()
        
        assert result == mock_weather_data.current_day_hourly
    
    def test_get_today_hourly_no_forecast(self, weather_manager):
        """Test getting today's hourly forecast when no forecast exists."""
        result = weather_manager.get_today_hourly()
        
        assert result == []
    
    def test_get_daily_forecast(self, weather_manager, mock_weather_data):
        """Test getting daily forecast."""
        weather_manager._current_forecast = mock_weather_data
        
        result = weather_manager.get_daily_forecast()
        
        assert result == mock_weather_data.daily_forecast
    
    def test_get_daily_forecast_no_forecast(self, weather_manager):
        """Test getting daily forecast when no forecast exists."""
        result = weather_manager.get_daily_forecast()
        
        assert result == []
    
    def test_is_data_stale_no_data(self, weather_manager):
        """Test data staleness check when no data exists."""
        result = weather_manager.is_data_stale()
        
        assert result is True
    
    def test_is_data_stale_with_data(self, weather_manager, mock_weather_data):
        """Test data staleness check with data."""
        weather_manager._current_forecast = mock_weather_data
        mock_weather_data.is_stale = False
        
        result = weather_manager.is_data_stale()
        
        assert result is False
    
    def test_get_statistics(self, weather_manager):
        """Test getting weather manager statistics."""
        weather_manager._fetch_count = 10
        weather_manager._error_count = 2
        weather_manager._last_successful_fetch = datetime.now()
        weather_manager._refresh_timer.isActive.return_value = True
        
        stats = weather_manager.get_statistics()
        
        assert stats["fetch_count"] == 10
        assert stats["error_count"] == 2
        assert stats["success_rate"] == 80.0  # (10-2)/10 * 100
        assert stats["auto_refresh_active"] is True
        assert "config_version" in stats
        assert "api_provider" in stats
    
    def test_get_statistics_no_fetches(self, weather_manager):
        """Test getting statistics with no fetches."""
        stats = weather_manager.get_statistics()
        
        assert stats["fetch_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0.0  # No division by zero
    
    def test_update_config_same_interval(self, weather_manager, mock_config):
        """Test updating config with same refresh interval."""
        new_config = Mock(spec=WeatherConfig)
        new_config.refresh_interval_minutes = 30  # Same as original
        new_config.enabled = True
        
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            mock_new_api_manager = AsyncMock()
            mock_factory.create_manager_from_config.return_value = mock_new_api_manager
            
            weather_manager.update_config(new_config)
            
            assert weather_manager._config == new_config
            assert weather_manager._api_manager == mock_new_api_manager
            mock_new_api_manager.clear_cache.assert_called_once()
    
    def test_update_config_different_interval_active_refresh(self, weather_manager, mock_config):
        """Test updating config with different refresh interval while auto-refresh is active."""
        new_config = Mock(spec=WeatherConfig)
        new_config.refresh_interval_minutes = 60  # Different from original
        new_config.enabled = True
        
        weather_manager._refresh_timer.isActive.return_value = True
        
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            with patch.object(weather_manager, 'stop_auto_refresh') as mock_stop:
                with patch.object(weather_manager, 'start_auto_refresh') as mock_start:
                    mock_new_api_manager = AsyncMock()
                    mock_factory.create_manager_from_config.return_value = mock_new_api_manager
                    
                    weather_manager.update_config(new_config)
                    
                    mock_stop.assert_called_once()
                    mock_start.assert_called_once()  # Should start because enabled
    
    def test_clear_data(self, weather_manager, mock_weather_data):
        """Test clearing weather data."""
        weather_manager._current_forecast = mock_weather_data
        weather_manager._command_history.append(Mock())
        
        weather_manager.clear_data()
        
        assert weather_manager._current_forecast is None
        assert len(weather_manager._command_history) == 0
        weather_manager._api_manager.clear_cache.assert_called_once()
    
    def test_shutdown_with_sync_shutdown(self, weather_manager):
        """Test shutdown with API manager that supports sync shutdown."""
        mock_observer = Mock(spec=WeatherObserver)
        weather_manager.attach(mock_observer)
        
        with patch.object(weather_manager, 'stop_auto_refresh') as mock_stop:
            with patch.object(weather_manager, 'clear_data') as mock_clear:
                weather_manager.shutdown()
                
                mock_stop.assert_called_once()
                mock_clear.assert_called_once()
                assert len(weather_manager._observers) == 0
                weather_manager._api_manager.shutdown_sync.assert_called_once()
    
    def test_shutdown_without_sync_shutdown(self, weather_manager):
        """Test shutdown with API manager that doesn't support sync shutdown."""
        # Remove shutdown_sync method
        del weather_manager._api_manager.shutdown_sync
        
        with patch.object(weather_manager, 'stop_auto_refresh') as mock_stop:
            with patch.object(weather_manager, 'clear_data') as mock_clear:
                weather_manager.shutdown()
                
                mock_stop.assert_called_once()
                mock_clear.assert_called_once()
    
    def test_error_handler_no_matching_strategy(self):
        """Test error handler when no strategy matches (edge case)."""
        mock_logger = Mock()
        handler = WeatherErrorHandler(mock_logger)
        
        # Clear all strategies to test fallback
        handler._error_strategies = {}
        
        error = Exception("Generic error")
        message = handler.handle_error(error)
        
        assert "An unexpected error occurred" in message
    
    def test_weather_subject_get_observer_count(self):
        """Test getting observer count."""
        subject = WeatherSubject()
        observer1 = MockWeatherObserver()
        observer2 = MockWeatherObserver()
        
        assert subject.get_observer_count() == 0
        
        subject.attach(observer1)
        assert subject.get_observer_count() == 1
        
        subject.attach(observer2)
        assert subject.get_observer_count() == 2
        
        subject.detach(observer1)
        assert subject.get_observer_count() == 1
    
    def test_weather_error_handler_specific_handlers(self):
        """Test specific error handler methods directly."""
        mock_logger = Mock()
        handler = WeatherErrorHandler(mock_logger)
        
        # Test _handle_network_error directly
        network_error = WeatherNetworkException("Network failed")
        message = handler._handle_network_error(network_error)
        assert "Network connection error" in message
        mock_logger.error.assert_called_with(f"Weather network error: {network_error}")
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test _handle_data_error directly
        data_error = WeatherDataException("Data failed")
        message = handler._handle_data_error(data_error)
        assert "Weather data is temporarily unavailable" in message
        mock_logger.error.assert_called_with(f"Weather data error: {data_error}")
    
    def test_weather_manager_shutdown_hasattr_check(self):
        """Test shutdown when API manager doesn't have shutdown_sync attribute."""
        mock_config = Mock(spec=WeatherConfig)
        mock_config.enabled = True
        mock_config.refresh_interval_minutes = 30
        mock_config.get_refresh_interval_seconds.return_value = 1800
        mock_config.api_provider = "test_provider"
        
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            mock_api_manager = AsyncMock()
            # Don't add shutdown_sync attribute
            mock_factory.create_manager_from_config.return_value = mock_api_manager
            
            with patch('src.managers.weather_manager.QTimer'):
                manager = WeatherManager(mock_config)
                manager._api_manager = mock_api_manager
                
                # This should trigger the hasattr check and warning log
                manager.shutdown()
    
    def test_shutdown_with_exception(self, weather_manager):
        """Test shutdown when API manager shutdown raises exception."""
        weather_manager._api_manager.shutdown_sync.side_effect = Exception("Shutdown failed")
        
        with patch.object(weather_manager, 'stop_auto_refresh') as mock_stop:
            with patch.object(weather_manager, 'clear_data') as mock_clear:
                # Should not raise exception
                weather_manager.shutdown()
                
                mock_stop.assert_called_once()
                mock_clear.assert_called_once()
    
    def test_update_config_different_interval_disabled(self, weather_manager, mock_config):
        """Test updating config with different interval but disabled."""
        new_config = Mock(spec=WeatherConfig)
        new_config.refresh_interval_minutes = 60  # Different from original
        new_config.enabled = False
        
        weather_manager._refresh_timer.isActive.return_value = True
        
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            with patch.object(weather_manager, 'stop_auto_refresh') as mock_stop:
                with patch.object(weather_manager, 'start_auto_refresh') as mock_start:
                    mock_new_api_manager = AsyncMock()
                    mock_factory.create_manager_from_config.return_value = mock_new_api_manager
                    
                    weather_manager.update_config(new_config)
                    
                    mock_stop.assert_called_once()
                    mock_start.assert_not_called()  # Should not start because disabled

    def test_shutdown_api_manager_shutdown_sync_exception(self):
        """Test shutdown when API manager shutdown_sync raises exception."""
        mock_config = Mock(spec=WeatherConfig)
        mock_config.enabled = True
        mock_config.refresh_interval_minutes = 30
        mock_config.get_refresh_interval_seconds.return_value = 1800
        mock_config.api_provider = "test_provider"
        
        with patch('src.managers.weather_manager.WeatherAPIFactory') as mock_factory:
            mock_api_manager = AsyncMock()
            mock_api_manager.shutdown_sync = Mock(side_effect=Exception("Shutdown failed"))
            mock_factory.create_manager_from_config.return_value = mock_api_manager
            
            with patch('src.managers.weather_manager.QTimer'):
                manager = WeatherManager(mock_config)
                manager._api_manager = mock_api_manager
                
                # Should not raise exception (should be caught and logged as warning)
                manager.shutdown()
                
                # Verify cleanup still happened
                assert manager._current_forecast is None
                assert len(manager._command_history) == 0
                assert len(manager._observers) == 0
                mock_api_manager.shutdown_sync.assert_called_once()