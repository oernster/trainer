"""
Comprehensive tests for AstronomyManager to achieve 100% test coverage.
Author: Oliver Ernster

This module provides complete test coverage for the astronomy manager,
including all methods, error conditions, and edge cases.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any

from src.managers.astronomy_manager import AstronomyManager, AstronomyManagerFactory
from src.managers.astronomy_config import AstronomyConfig, AstronomyServiceConfig
from src.models.astronomy_data import (
    AstronomyForecastData,
    AstronomyData,
    AstronomyEvent,
    AstronomyEventType,
    AstronomyEventPriority,
    Location,
    AstronomyDataValidator,
)
from src.api.nasa_api_manager import (
    AstronomyAPIManager,
    AstronomyAPIException,
    AstronomyNetworkException,
    AstronomyRateLimitException,
    AstronomyAuthenticationException,
)


class TestAstronomyManager:
    """Test cases for AstronomyManager class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock astronomy configuration."""
        config = AstronomyConfig(
            enabled=True,
            nasa_api_key="test_api_key",
            location_name="Test Location",
            location_latitude=51.5074,
            location_longitude=-0.1278,
            timezone="Europe/London",
            update_interval_minutes=360,
            timeout_seconds=15,
            max_retries=3,
            retry_delay_seconds=2,
        )
        return config

    @pytest.fixture
    def disabled_config(self):
        """Create a disabled astronomy configuration."""
        return AstronomyConfig(enabled=False)

    @pytest.fixture
    def config_no_api_key(self):
        """Create a config without API key."""
        return AstronomyConfig(
            enabled=True,
            nasa_api_key="",
            location_name="Test Location",
            location_latitude=51.5074,
            location_longitude=-0.1278,
        )

    @pytest.fixture
    def mock_api_manager(self):
        """Create a mock API manager."""
        api_manager = Mock(spec=AstronomyAPIManager)
        api_manager.get_astronomy_forecast = AsyncMock()
        api_manager.get_cache_info = Mock(
            return_value={
                "has_cached_data": True,
                "last_fetch_time": datetime.now(),
                "cache_valid": True,
            }
        )
        api_manager.clear_cache = Mock()
        api_manager.shutdown = AsyncMock()
        api_manager.shutdown_sync = Mock()
        return api_manager

    @pytest.fixture
    def sample_forecast_data(self):
        """Create sample forecast data."""
        location = Location(
            name="Test Location",
            latitude=51.5074,
            longitude=-0.1278,
            timezone="Europe/London",
        )

        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(),
            priority=AstronomyEventPriority.MEDIUM,
        )

        astronomy_data = AstronomyData(
            date=date.today(), events=[event], primary_event=event
        )

        return AstronomyForecastData(
            location=location, daily_astronomy=[astronomy_data], forecast_days=7
        )

    def test_init_enabled_with_valid_api_key(self, mock_config):
        """Test initialization with enabled config and valid API key."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = Mock()

            manager = AstronomyManager(mock_config)

            assert manager._config == mock_config
            assert manager._api_manager is not None
            assert manager._validator is not None
            assert manager._last_update_time is None
            assert manager._current_forecast is None
            assert manager._is_loading is False
            mock_factory.assert_called_once_with(mock_config)

    def test_init_disabled(self, disabled_config):
        """Test initialization with disabled config."""
        manager = AstronomyManager(disabled_config)

        assert manager._config == disabled_config
        assert manager._api_manager is None
        assert not manager._config.enabled

    def test_init_enabled_no_api_key(self, config_no_api_key):
        """Test initialization with enabled config but no API key."""
        manager = AstronomyManager(config_no_api_key)

        assert manager._config == config_no_api_key
        assert manager._api_manager is None

    def test_initialize_api_manager_success(self, mock_config):
        """Test successful API manager initialization."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_api_manager = Mock()
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            assert manager._api_manager == mock_api_manager

    def test_initialize_api_manager_failure(self, mock_config):
        """Test API manager initialization failure."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.side_effect = Exception("API initialization failed")

            manager = AstronomyManager(mock_config)

            # Should emit error signal but not crash
            assert manager._api_manager is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_disabled(self, disabled_config):
        """Test refresh when astronomy is disabled."""
        manager = AstronomyManager(disabled_config)

        result = await manager.refresh_astronomy()

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_no_api_manager(self, mock_config):
        """Test refresh when API manager is not initialized."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = None

            manager = AstronomyManager(mock_config)
            manager._api_manager = None

            result = await manager.refresh_astronomy()

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_skip_refresh(
        self, mock_config, sample_forecast_data
    ):
        """Test refresh skipped when recent data is available."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data
            manager._last_update_time = datetime.now()

            result = await manager.refresh_astronomy(force_refresh=False)

            assert result == sample_forecast_data

    @pytest.mark.asyncio
    async def test_refresh_astronomy_success(
        self, mock_config, mock_api_manager, sample_forecast_data
    ):
        """Test successful astronomy data refresh."""
        mock_api_manager.get_astronomy_forecast.return_value = sample_forecast_data

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            # Mock validator to return True
            with patch.object(
                manager._validator, "validate_astronomy_forecast", return_value=True
            ):
                result = await manager.refresh_astronomy()

            assert result == sample_forecast_data
            assert manager._current_forecast == sample_forecast_data
            assert manager._last_update_time is not None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_validation_failure(
        self, mock_config, mock_api_manager, sample_forecast_data
    ):
        """Test refresh with validation failure."""
        mock_api_manager.get_astronomy_forecast.return_value = sample_forecast_data

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            # Mock validator to return False
            with patch.object(
                manager._validator, "validate_astronomy_forecast", return_value=False
            ):
                result = await manager.refresh_astronomy()

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_authentication_exception(
        self, mock_config, mock_api_manager
    ):
        """Test refresh with authentication exception."""
        mock_api_manager.get_astronomy_forecast.side_effect = (
            AstronomyAuthenticationException("Auth failed")
        )

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = await manager.refresh_astronomy()

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_rate_limit_exception(
        self, mock_config, mock_api_manager
    ):
        """Test refresh with rate limit exception."""
        mock_api_manager.get_astronomy_forecast.side_effect = (
            AstronomyRateLimitException("Rate limit exceeded")
        )

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = await manager.refresh_astronomy()

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_network_exception(
        self, mock_config, mock_api_manager
    ):
        """Test refresh with network exception."""
        mock_api_manager.get_astronomy_forecast.side_effect = AstronomyNetworkException(
            "Network error"
        )

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = await manager.refresh_astronomy()

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_api_exception(self, mock_config, mock_api_manager):
        """Test refresh with API exception."""
        mock_api_manager.get_astronomy_forecast.side_effect = AstronomyAPIException(
            "API error"
        )

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = await manager.refresh_astronomy()

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_astronomy_generic_exception(
        self, mock_config, mock_api_manager
    ):
        """Test refresh with generic exception."""
        mock_api_manager.get_astronomy_forecast.side_effect = Exception("Generic error")

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = await manager.refresh_astronomy()

            assert result is None

    def test_should_skip_refresh_no_data(self, mock_config):
        """Test should_skip_refresh with no existing data."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            assert not manager._should_skip_refresh()

    def test_should_skip_refresh_recent_data(self, mock_config, sample_forecast_data):
        """Test should_skip_refresh with recent data."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data
            manager._last_update_time = datetime.now()

            assert manager._should_skip_refresh()

    def test_should_skip_refresh_stale_data(self, mock_config, sample_forecast_data):
        """Test should_skip_refresh with stale data."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data
            manager._last_update_time = datetime.now() - timedelta(hours=24)

            assert not manager._should_skip_refresh()

    def test_set_loading_state_change(self, mock_config):
        """Test loading state change."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            # Mock signal emission
            manager.loading_state_changed = Mock()

            manager._set_loading_state(True)

            assert manager._is_loading is True
            manager.loading_state_changed.emit.assert_called_once_with(True)

    def test_set_loading_state_no_change(self, mock_config):
        """Test loading state with no change."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager._is_loading = True

            # Mock signal emission
            manager.loading_state_changed = Mock()

            manager._set_loading_state(True)

            # Signal should not be emitted if state doesn't change
            manager.loading_state_changed.emit.assert_not_called()

    def test_emit_cache_status_with_api_manager(self, mock_config, mock_api_manager):
        """Test cache status emission with API manager."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)
            manager.cache_status_changed = Mock()

            manager._emit_cache_status()

            manager.cache_status_changed.emit.assert_called_once()

    def test_emit_cache_status_no_api_manager(self, disabled_config):
        """Test cache status emission without API manager."""
        manager = AstronomyManager(disabled_config)
        manager.cache_status_changed = Mock()

        manager._emit_cache_status()

        # Should not emit if no API manager
        manager.cache_status_changed.emit.assert_not_called()

    @patch("asyncio.get_event_loop")
    def test_auto_refresh_running_loop(self, mock_get_loop, mock_config):
        """Test auto refresh with running event loop."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            with patch("asyncio.create_task") as mock_create_task:
                manager._auto_refresh()

                mock_create_task.assert_called_once()

    @patch("asyncio.get_event_loop")
    @patch("asyncio.run")
    def test_auto_refresh_not_running_loop(self, mock_run, mock_get_loop, mock_config):
        """Test auto refresh with non-running event loop."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_get_loop.return_value = mock_loop

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            manager._auto_refresh()

            mock_run.assert_called_once()

    def test_start_auto_refresh_disabled(self, disabled_config):
        """Test start auto refresh when disabled."""
        manager = AstronomyManager(disabled_config)

        manager.start_auto_refresh()

        assert not manager._refresh_timer.isActive()

    def test_start_auto_refresh_enabled(self, mock_config):
        """Test start auto refresh when enabled."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            # Mock the timer to avoid Qt threading issues
            with patch.object(manager._refresh_timer, "start") as mock_start:
                with patch.object(
                    manager._refresh_timer, "isActive", return_value=True
                ):
                    manager.start_auto_refresh()

                    mock_start.assert_called_once()
                    assert manager.is_auto_refresh_active()

    def test_stop_auto_refresh(self, mock_config):
        """Test stop auto refresh."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager.start_auto_refresh()

            manager.stop_auto_refresh()

            assert not manager._refresh_timer.isActive()

    def test_is_auto_refresh_active(self, mock_config):
        """Test is auto refresh active."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            assert not manager.is_auto_refresh_active()

            # Mock the timer to avoid Qt threading issues
            with patch.object(manager._refresh_timer, "start"):
                with patch.object(
                    manager._refresh_timer, "isActive", return_value=True
                ):
                    manager.start_auto_refresh()
                    assert manager.is_auto_refresh_active()

    def test_get_current_forecast(self, mock_config, sample_forecast_data):
        """Test get current forecast."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data

            result = manager.get_current_forecast()

            assert result == sample_forecast_data

    def test_get_last_update_time(self, mock_config):
        """Test get last update time."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            test_time = datetime.now()
            manager._last_update_time = test_time

            result = manager.get_last_update_time()

            assert result == test_time

    def test_is_loading(self, mock_config):
        """Test is loading."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            assert not manager.is_loading()

            manager._is_loading = True
            assert manager.is_loading()

    def test_is_data_stale_no_forecast(self, mock_config):
        """Test is data stale with no forecast."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            assert manager.is_data_stale()

    def test_is_data_stale_with_forecast(self, mock_config, sample_forecast_data):
        """Test is data stale with forecast."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data

            # Mock the is_stale property using property mock
            with patch.object(
                type(sample_forecast_data),
                "is_stale",
                new_callable=lambda: property(lambda self: False),
            ):
                assert not manager.is_data_stale()

    def test_get_cache_info_with_api_manager(self, mock_config, mock_api_manager):
        """Test get cache info with API manager."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = manager.get_cache_info()

            assert isinstance(result, dict)
            assert "enabled" in result
            assert "has_api_manager" in result
            assert result["enabled"] is True
            assert result["has_api_manager"] is True

    def test_get_cache_info_no_api_manager(self, disabled_config):
        """Test get cache info without API manager."""
        manager = AstronomyManager(disabled_config)

        result = manager.get_cache_info()

        assert isinstance(result, dict)
        assert result["enabled"] is False
        assert result["has_api_manager"] is False

    def test_clear_cache_with_api_manager(
        self, mock_config, mock_api_manager, sample_forecast_data
    ):
        """Test clear cache with API manager."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data
            manager._last_update_time = datetime.now()
            manager.cache_status_changed = Mock()

            manager.clear_cache()

            assert manager._current_forecast is None
            assert manager._last_update_time is None
            mock_api_manager.clear_cache.assert_called_once()

    def test_clear_cache_no_api_manager(self, disabled_config, sample_forecast_data):
        """Test clear cache without API manager."""
        manager = AstronomyManager(disabled_config)
        manager._current_forecast = sample_forecast_data
        manager._last_update_time = datetime.now()
        manager.cache_status_changed = Mock()

        manager.clear_cache()

        assert manager._current_forecast is None
        assert manager._last_update_time is None

    def test_update_config_enable_astronomy(self, disabled_config, mock_config):
        """Test update config enabling astronomy."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = Mock()

            manager = AstronomyManager(disabled_config)

            manager.update_config(mock_config)

            assert manager._config == mock_config
            mock_factory.assert_called_once_with(mock_config)

    def test_update_config_enable_astronomy_no_api_key(self, disabled_config):
        """Test update config enabling astronomy without API key."""
        new_config = AstronomyConfig(enabled=True, nasa_api_key="")

        manager = AstronomyManager(disabled_config)

        manager.update_config(new_config)

        assert manager._config == new_config

    def test_update_config_disable_astronomy(self, mock_config, disabled_config):
        """Test update config disabling astronomy."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)
            manager.start_auto_refresh()

            manager.update_config(disabled_config)

            assert manager._config == disabled_config
            assert not manager.is_auto_refresh_active()

    @patch("asyncio.create_task")
    def test_update_config_api_key_change(
        self, mock_create_task, mock_config, mock_api_manager
    ):
        """Test update config with API key change."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            # Create new config with different API key
            new_config = AstronomyConfig(
                enabled=True,
                nasa_api_key="new_api_key",
                location_name="Test Location",
                location_latitude=51.5074,
                location_longitude=-0.1278,
            )

            manager.update_config(new_config)

            assert manager._config == new_config
            mock_create_task.assert_called_once()

    def test_update_config_restart_auto_refresh(self, mock_config):
        """Test update config restarting auto refresh."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            # Mock timer methods to avoid Qt threading issues
            with patch.object(manager._refresh_timer, "start"):
                with patch.object(manager._refresh_timer, "stop"):
                    with patch.object(
                        manager._refresh_timer, "isActive", return_value=True
                    ):
                        manager.start_auto_refresh()

                        # Create new config with different interval
                        new_config = AstronomyConfig(
                            enabled=True,
                            nasa_api_key="test_api_key",
                            location_name="Test Location",
                            location_latitude=51.5074,
                            location_longitude=-0.1278,
                            update_interval_minutes=720,  # Different interval
                        )

                        manager.update_config(new_config)

                        assert manager._config == new_config
                        assert manager.is_auto_refresh_active()

    def test_get_status_summary_disabled(self, disabled_config):
        """Test get status summary when disabled."""
        manager = AstronomyManager(disabled_config)

        result = manager.get_status_summary()

        assert result == "Astronomy disabled"

    def test_get_status_summary_no_api_manager(self, mock_config):
        """Test get status summary without API manager."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = None

            manager = AstronomyManager(mock_config)
            manager._api_manager = None

            result = manager.get_status_summary()

            assert result == "Astronomy API not initialized"

    def test_get_status_summary_loading(self, mock_config, mock_api_manager):
        """Test get status summary while loading."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)
            manager._is_loading = True

            result = manager.get_status_summary()

            assert result == "Loading astronomy data..."

    def test_get_status_summary_no_data(self, mock_config, mock_api_manager):
        """Test get status summary with no data."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            result = manager.get_status_summary()

            assert result == "No astronomy data available"

    def test_get_status_summary_stale_data(
        self, mock_config, mock_api_manager, sample_forecast_data
    ):
        """Test get status summary with stale data."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data

            with patch.object(manager, "is_data_stale", return_value=True):
                result = manager.get_status_summary()

                assert "stale" in result
                assert str(sample_forecast_data.total_events) in result

    def test_get_status_summary_current_data(
        self, mock_config, mock_api_manager, sample_forecast_data
    ):
        """Test get status summary with current data."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)
            manager._current_forecast = sample_forecast_data

            with patch.object(manager, "is_data_stale", return_value=False):
                result = manager.get_status_summary()

                assert "current" in result
                assert str(sample_forecast_data.total_events) in result

    def test_get_enabled_services(self, mock_config):
        """Test get enabled services."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(mock_config)

            result = manager.get_enabled_services()

            assert isinstance(result, list)

    @patch("asyncio.get_event_loop")
    @patch("asyncio.run")
    def test_shutdown_sync_shutdown_success(
        self, mock_run, mock_get_loop, mock_config, mock_api_manager
    ):
        """Test shutdown with successful sync shutdown."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_get_loop.return_value = mock_loop

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)
            manager.start_auto_refresh()

            manager.shutdown()

            assert not manager.is_auto_refresh_active()
            assert manager._current_forecast is None
            assert manager._last_update_time is None
            assert manager._api_manager is None
            mock_api_manager.shutdown_sync.assert_called_once()

    @patch("asyncio.get_event_loop")
    @patch("asyncio.create_task")
    def test_shutdown_sync_shutdown_failure_async_fallback(
        self, mock_create_task, mock_get_loop, mock_config, mock_api_manager
    ):
        """Test shutdown with sync failure falling back to async."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        # Make sync shutdown fail
        mock_api_manager.shutdown_sync.side_effect = Exception("Sync shutdown failed")

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            manager.shutdown()

            mock_create_task.assert_called_once()

    @patch("asyncio.get_event_loop")
    @patch("asyncio.run")
    def test_shutdown_sync_shutdown_failure_async_fallback_not_running(
        self, mock_config, mock_api_manager
    ):
        """Test shutdown with sync failure falling back to async (not running loop)."""
        # Make sync shutdown fail
        mock_api_manager.shutdown_sync.side_effect = Exception("Sync shutdown failed")

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(mock_config)

            # Mock the asyncio operations to simulate the exact flow
            with patch("asyncio.get_event_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_loop.is_running.return_value = False
                mock_get_loop.return_value = mock_loop

                with patch("asyncio.run") as mock_run:
                    manager.shutdown()

                    # Should attempt async fallback with asyncio.run
                    mock_run.assert_called_once()
                    # Verify cleanup still happens
                    assert manager._api_manager is None

    @patch("asyncio.get_event_loop")
    def test_shutdown_both_failures(self, mock_get_loop, mock_config, mock_api_manager):
        """Test shutdown with both sync and async failures."""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        # Make both sync and async shutdown fail
        mock_api_manager.shutdown_sync.side_effect = Exception("Sync shutdown failed")

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            with patch("asyncio.create_task") as mock_create_task:
                mock_create_task.side_effect = Exception("Async shutdown failed")

                manager = AstronomyManager(mock_config)

                # Should not raise exception even if both fail
                manager.shutdown()

                assert manager._api_manager is None

    def test_shutdown_no_api_manager(self, disabled_config):
        """Test shutdown without API manager."""
        manager = AstronomyManager(disabled_config)
        manager.start_auto_refresh()  # This won't actually start due to disabled config

        # Should not raise exception
        manager.shutdown()

        assert manager._current_forecast is None
        assert manager._last_update_time is None


class TestAstronomyManagerFactory:
    """Test cases for AstronomyManagerFactory class."""

    def test_create_manager(self):
        """Test create manager."""
        config = AstronomyConfig(enabled=True, nasa_api_key="test_key")

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManagerFactory.create_manager(config)

            assert isinstance(manager, AstronomyManager)
            assert manager._config == config

    def test_create_disabled_manager(self):
        """Test create disabled manager."""
        manager = AstronomyManagerFactory.create_disabled_manager()

        assert isinstance(manager, AstronomyManager)
        assert not manager._config.enabled

    def test_create_test_manager(self):
        """Test create test manager."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManagerFactory.create_test_manager("test_api_key")

            assert isinstance(manager, AstronomyManager)
            assert manager._config.enabled
            assert manager._config.nasa_api_key == "test_api_key"
            assert manager._config.location_name == "Test Location"

    def test_create_test_manager_default_key(self):
        """Test create test manager with default key."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManagerFactory.create_test_manager()

            assert isinstance(manager, AstronomyManager)
            assert manager._config.nasa_api_key == "test_key"


class TestAstronomyManagerIntegration:
    """Integration tests for AstronomyManager with real components."""

    @pytest.fixture
    def real_config(self):
        """Create a real configuration for integration tests."""
        return AstronomyConfig(
            enabled=True,
            nasa_api_key="DEMO_KEY",  # NASA provides a demo key
            location_name="London",
            location_latitude=51.5074,
            location_longitude=-0.1278,
            timeout_seconds=5,  # Short timeout for tests
            max_retries=1,
        )

    def test_manager_lifecycle(self, real_config):
        """Test complete manager lifecycle."""
        # This test uses mocks to avoid actual API calls
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_api_manager = Mock()
            mock_api_manager.get_cache_info.return_value = {"test": "data"}
            mock_factory.return_value = mock_api_manager

            # Create manager
            manager = AstronomyManager(real_config)

            # Test basic operations
            assert not manager.is_loading()
            assert manager.get_current_forecast() is None
            assert not manager.is_auto_refresh_active()

            # Start auto refresh (mock timer to avoid Qt issues)
            with patch.object(manager._refresh_timer, "start"):
                with patch.object(
                    manager._refresh_timer, "isActive", return_value=True
                ):
                    manager.start_auto_refresh()
                    assert manager.is_auto_refresh_active()

            # Get cache info
            cache_info = manager.get_cache_info()
            assert isinstance(cache_info, dict)

            # Clear cache
            manager.clear_cache()

            # Stop auto refresh
            manager.stop_auto_refresh()
            assert not manager.is_auto_refresh_active()

            # Shutdown
            manager.shutdown()

    def test_signal_emissions(self, real_config):
        """Test that signals are properly emitted."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ):
            manager = AstronomyManager(real_config)

            # Mock signal connections
            astronomy_updated_calls = []
            astronomy_error_calls = []
            loading_state_calls = []
            cache_status_calls = []

            manager.astronomy_updated.connect(
                lambda data: astronomy_updated_calls.append(data)
            )
            manager.astronomy_error.connect(
                lambda error: astronomy_error_calls.append(error)
            )
            manager.loading_state_changed.connect(
                lambda state: loading_state_calls.append(state)
            )
            manager.cache_status_changed.connect(
                lambda status: cache_status_calls.append(status)
            )

            # Test loading state change
            manager._set_loading_state(True)
            assert len(loading_state_calls) == 1
            assert loading_state_calls[0] is True

            # Test cache status emission
            manager._api_manager = Mock()
            manager._api_manager.get_cache_info.return_value = {"test": "cache"}
            manager._emit_cache_status()
            assert len(cache_status_calls) == 1

    @pytest.mark.asyncio
    async def test_refresh_with_mocked_dependencies(self, real_config):
        """Test refresh with all dependencies mocked."""
        mock_forecast = Mock()
        mock_forecast.total_events = 5

        mock_api_manager = Mock()
        mock_api_manager.get_astronomy_forecast = AsyncMock(return_value=mock_forecast)
        mock_api_manager.get_cache_info.return_value = {"test": "cache"}

        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(real_config)

            # Mock validator
            with patch.object(
                manager._validator, "validate_astronomy_forecast", return_value=True
            ):
                result = await manager.refresh_astronomy()

                assert result == mock_forecast
                assert manager._current_forecast == mock_forecast
                assert manager._last_update_time is not None

    def test_config_update_scenarios(self, real_config):
        """Test various configuration update scenarios."""
        with patch(
            "src.managers.astronomy_manager.AstronomyAPIFactory.create_manager_from_config"
        ) as mock_factory:
            mock_api_manager = Mock()
            mock_factory.return_value = mock_api_manager

            manager = AstronomyManager(real_config)

            # Test disabling
            disabled_config = AstronomyConfig(enabled=False)
            manager.update_config(disabled_config)
            assert not manager._config.enabled

            # Test re-enabling
            manager.update_config(real_config)
            assert manager._config.enabled

            # Test API key change
            new_config = AstronomyConfig(
                enabled=True,
                nasa_api_key="NEW_KEY",
                location_name="London",
                location_latitude=51.5074,
                location_longitude=-0.1278,
            )

            with patch("asyncio.create_task"):
                manager.update_config(new_config)
                assert manager._config.nasa_api_key == "NEW_KEY"


class TestAstronomyManagerEdgeCases:
    """Test edge cases to achieve 100% coverage."""


@pytest.fixture
def mock_config(self):
    """Create a mock astronomy configuration."""
    return AstronomyConfig(
        enabled=True,
        nasa_api_key="test_api_key",
        location_name="Test Location",
        location_latitude=51.5074,
        location_longitude=-0.1278,
    )
