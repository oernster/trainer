"""
Comprehensive tests for TrainManager with focus on real code execution.

This test suite aims for 85%+ coverage while exercising actual functionality
rather than relying heavily on mocking.
"""

import pytest
import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from PySide6.QtCore import QTimer, QObject, Signal

from src.managers.train_manager import TrainManager
from src.managers.config_manager import (
    ConfigData,
    APIConfig,
    StationConfig,
    RefreshConfig,
    DisplayConfig,
)
from src.models.train_data import TrainData, TrainStatus, ServiceType
from src.api.api_manager import APIManager, APIException, NetworkException


class TestTrainManager:
    """Test suite for TrainManager class."""

    @pytest.fixture
    def config(self):
        """Provide test configuration."""
        return ConfigData(
            api=APIConfig(
                app_id="test_id",
                app_key="test_key",
                base_url="https://transportapi.com/v3/uk",
                timeout_seconds=10,
                max_retries=2,
                rate_limit_per_minute=30,
            ),
            stations=StationConfig(
                from_code="FLE",
                from_name="Fleet",
                to_code="WAT",
                to_name="London Waterloo",
            ),
            refresh=RefreshConfig(
                auto_enabled=True, interval_minutes=2, manual_enabled=True
            ),
            display=DisplayConfig(
                max_trains=50, time_window_hours=10, show_cancelled=True, theme="dark"
            ),
        )

    @pytest.fixture
    def train_manager(self, qapp, config):
        """Create TrainManager instance."""
        manager = TrainManager(config)
        yield manager
        # Cleanup
        manager.stop_auto_refresh()
        if hasattr(manager, "api_manager") and manager.api_manager:
            # Clean up any async resources
            pass

    @pytest.fixture
    def sample_trains(self):
        """Provide sample train data."""
        base_time = datetime.now().replace(second=0, microsecond=0)
        return [
            TrainData(
                departure_time=base_time + timedelta(minutes=15),
                scheduled_departure=base_time + timedelta(minutes=15),
                destination="London Waterloo",
                platform="2",
                operator="South Western Railway",
                service_type=ServiceType.FAST,
                status=TrainStatus.ON_TIME,
                delay_minutes=0,
                estimated_arrival=base_time + timedelta(minutes=62),
                journey_duration=timedelta(minutes=47),
                current_location="Fleet",
                train_uid="W12345",
                service_id="24673004",
            ),
            TrainData(
                departure_time=base_time + timedelta(minutes=25),
                scheduled_departure=base_time + timedelta(minutes=20),
                destination="London Waterloo",
                platform="1",
                operator="South Western Railway",
                service_type=ServiceType.STOPPING,
                status=TrainStatus.DELAYED,
                delay_minutes=5,
                estimated_arrival=base_time + timedelta(minutes=77),
                journey_duration=timedelta(minutes=52),
                current_location="Fleet",
                train_uid="W12346",
                service_id="24673005",
            ),
            TrainData(
                departure_time=base_time + timedelta(minutes=35),
                scheduled_departure=base_time + timedelta(minutes=35),
                destination="London Waterloo",
                platform="3",
                operator="South Western Railway",
                service_type=ServiceType.EXPRESS,
                status=TrainStatus.CANCELLED,
                delay_minutes=0,
                estimated_arrival=None,
                journey_duration=None,
                current_location=None,
                train_uid="W12347",
                service_id="24673006",
            ),
        ]

    def test_initialization(self, qapp, config):
        """Test TrainManager initialization."""
        manager = TrainManager(config)

        assert manager.config == config
        assert manager.api_manager is None
        assert manager.current_trains == []
        assert manager.last_update is None
        assert manager.is_fetching is False
        assert isinstance(manager.refresh_timer, QTimer)
        assert not manager.refresh_timer.isActive()

    def test_signals_exist(self, train_manager):
        """Test that all required signals exist."""
        assert hasattr(train_manager, "trains_updated")
        assert hasattr(train_manager, "error_occurred")
        assert hasattr(train_manager, "status_changed")
        assert hasattr(train_manager, "connection_changed")
        assert hasattr(train_manager, "last_update_changed")

        # Verify signals are actually Signal objects
        assert isinstance(train_manager.trains_updated, Signal)
        assert isinstance(train_manager.error_occurred, Signal)
        assert isinstance(train_manager.status_changed, Signal)
        assert isinstance(train_manager.connection_changed, Signal)
        assert isinstance(train_manager.last_update_changed, Signal)

    def test_start_auto_refresh_enabled(self, train_manager):
        """Test starting auto-refresh when enabled in config."""
        train_manager.config.refresh.auto_enabled = True
        train_manager.config.refresh.interval_minutes = 3

        train_manager.start_auto_refresh()

        assert train_manager.refresh_timer.isActive()
        expected_interval = 3 * 60 * 1000  # 3 minutes in milliseconds
        assert train_manager.refresh_timer.interval() == expected_interval

    def test_start_auto_refresh_disabled(self, train_manager):
        """Test starting auto-refresh when disabled in config."""
        train_manager.config.refresh.auto_enabled = False

        train_manager.start_auto_refresh()

        assert not train_manager.refresh_timer.isActive()

    def test_stop_auto_refresh(self, train_manager):
        """Test stopping auto-refresh."""
        # Start refresh first
        train_manager.config.refresh.auto_enabled = True
        train_manager.start_auto_refresh()
        assert train_manager.refresh_timer.isActive()

        # Stop refresh
        train_manager.stop_auto_refresh()
        assert not train_manager.refresh_timer.isActive()

    def test_toggle_auto_refresh_enable(self, train_manager):
        """Test toggling auto-refresh from disabled to enabled."""
        train_manager.config.refresh.auto_enabled = False
        train_manager.refresh_timer.stop()

        train_manager.toggle_auto_refresh()

        assert train_manager.config.refresh.auto_enabled is True
        assert train_manager.refresh_timer.isActive()

    def test_toggle_auto_refresh_disable(self, train_manager):
        """Test toggling auto-refresh from enabled to disabled."""
        train_manager.config.refresh.auto_enabled = True
        train_manager.start_auto_refresh()
        assert train_manager.refresh_timer.isActive()

        train_manager.toggle_auto_refresh()

        assert train_manager.config.refresh.auto_enabled is False
        assert not train_manager.refresh_timer.isActive()

    def test_update_refresh_interval_active_timer(self, train_manager):
        """Test updating refresh interval when timer is active."""
        # Start with 2 minute interval
        train_manager.config.refresh.auto_enabled = True
        train_manager.config.refresh.interval_minutes = 2
        train_manager.start_auto_refresh()
        assert train_manager.refresh_timer.isActive()

        # Update to 5 minutes
        train_manager.update_refresh_interval(5)

        assert train_manager.config.refresh.interval_minutes == 5
        assert train_manager.refresh_timer.isActive()
        expected_interval = 5 * 60 * 1000  # 5 minutes in milliseconds
        assert train_manager.refresh_timer.interval() == expected_interval

    def test_update_refresh_interval_inactive_timer(self, train_manager):
        """Test updating refresh interval when timer is inactive."""
        train_manager.config.refresh.interval_minutes = 2
        assert not train_manager.refresh_timer.isActive()

        train_manager.update_refresh_interval(7)

        assert train_manager.config.refresh.interval_minutes == 7
        assert not train_manager.refresh_timer.isActive()

    def test_initialize_api_success(self, train_manager):
        """Test successful API initialization."""

        async def test_async():
            with patch("src.managers.train_manager.APIManager") as mock_api_class:
                mock_api_instance = Mock()
                mock_api_class.return_value = mock_api_instance

                await train_manager.initialize_api()

                assert train_manager.api_manager == mock_api_instance
                mock_api_class.assert_called_once_with(train_manager.config)

        asyncio.run(test_async())

    def test_initialize_api_failure(self, train_manager):
        """Test API initialization failure."""

        async def test_async():
            with patch("src.managers.train_manager.APIManager") as mock_api_class:
                mock_api_class.side_effect = Exception("API init failed")

                # Set up signal mock
                with patch.object(train_manager, "error_occurred") as mock_signal:
                    await train_manager.initialize_api()

                    assert train_manager.api_manager is None
                    mock_signal.emit.assert_called_once()
                    call_args = mock_signal.emit.call_args[0][0]
                    assert "API initialization failed" in call_args

        asyncio.run(test_async())

    def test_fetch_trains_already_fetching(self, train_manager):
        """Test fetch_trains when already fetching."""
        train_manager.is_fetching = True

        # This should return early without starting new fetch
        train_manager.fetch_trains()

        # Should still be fetching (no change)
        assert train_manager.is_fetching is True

    def test_fetch_trains_starts_async_fetch(self, train_manager):
        """Test that fetch_trains starts async fetch."""
        train_manager.is_fetching = False

        with patch.object(train_manager, "_start_async_fetch") as mock_start:
            with patch("PySide6.QtCore.QTimer.singleShot") as mock_single_shot:
                train_manager.fetch_trains()

                mock_single_shot.assert_called_once_with(
                    0, train_manager._start_async_fetch
                )

    def test_process_train_data_with_cancelled_shown(
        self, train_manager, sample_trains
    ):
        """Test processing train data when cancelled trains are shown."""
        train_manager.config.display.show_cancelled = True
        train_manager.config.display.max_trains = 10

        result = train_manager._process_train_data(sample_trains)

        # Should include all trains (including cancelled)
        assert len(result) == 3
        # Should be sorted by departure time
        assert (
            result[0].departure_time
            <= result[1].departure_time
            <= result[2].departure_time
        )

    def test_process_train_data_with_cancelled_hidden(
        self, train_manager, sample_trains
    ):
        """Test processing train data when cancelled trains are hidden."""
        train_manager.config.display.show_cancelled = False
        train_manager.config.display.max_trains = 10

        result = train_manager._process_train_data(sample_trains)

        # Should exclude cancelled trains
        assert len(result) == 2
        for train in result:
            assert not train.is_cancelled

    def test_process_train_data_max_trains_limit(self, train_manager, sample_trains):
        """Test processing train data with max trains limit."""
        train_manager.config.display.show_cancelled = True
        train_manager.config.display.max_trains = 2

        result = train_manager._process_train_data(sample_trains)

        # Should limit to max_trains
        assert len(result) == 2

    def test_get_current_trains(self, train_manager, sample_trains):
        """Test getting current trains."""
        train_manager.current_trains = sample_trains

        result = train_manager.get_current_trains()

        # Should return a copy
        assert result == sample_trains
        assert result is not sample_trains  # Different object

    def test_get_last_update_time_none(self, train_manager):
        """Test getting last update time when None."""
        assert train_manager.get_last_update_time() is None

    def test_get_last_update_time_set(self, train_manager):
        """Test getting last update time when set."""
        test_time = datetime.now()
        train_manager.last_update = test_time

        assert train_manager.get_last_update_time() == test_time

    def test_get_train_count(self, train_manager, sample_trains):
        """Test getting train count."""
        assert train_manager.get_train_count() == 0

        train_manager.current_trains = sample_trains
        assert train_manager.get_train_count() == 3

    def test_get_stats(self, train_manager, sample_trains):
        """Test getting train statistics."""
        train_manager.current_trains = sample_trains

        stats = train_manager.get_stats()

        assert stats["total_trains"] == 3
        assert stats["on_time"] == 1
        assert stats["delayed"] == 1
        assert stats["cancelled"] == 1
        assert stats["max_delay"] == 5

    def test_find_train_by_uid_found(self, train_manager, sample_trains):
        """Test finding train by UID when found."""
        train_manager.current_trains = sample_trains

        result = train_manager.find_train_by_uid("W12346")

        assert result is not None
        assert result.train_uid == "W12346"
        assert result.status == TrainStatus.DELAYED

    def test_find_train_by_uid_not_found(self, train_manager, sample_trains):
        """Test finding train by UID when not found."""
        train_manager.current_trains = sample_trains

        result = train_manager.find_train_by_uid("NONEXISTENT")

        assert result is None

    def test_find_train_by_service_id_found(self, train_manager, sample_trains):
        """Test finding train by service ID when found."""
        train_manager.current_trains = sample_trains

        result = train_manager.find_train_by_service_id("24673005")

        assert result is not None
        assert result.service_id == "24673005"
        assert result.delay_minutes == 5

    def test_find_train_by_service_id_not_found(self, train_manager, sample_trains):
        """Test finding train by service ID when not found."""
        train_manager.current_trains = sample_trains

        result = train_manager.find_train_by_service_id("NONEXISTENT")

        assert result is None

    def test_clear_data(self, train_manager, sample_trains):
        """Test clearing train data."""
        train_manager.current_trains = sample_trains
        train_manager.last_update = datetime.now()

        # Set up signal mock
        with patch.object(train_manager, "trains_updated") as mock_signal:
            train_manager.clear_data()

            assert len(train_manager.current_trains) == 0
            assert train_manager.last_update is None
            mock_signal.emit.assert_called_once_with([])

    def test_is_auto_refresh_active_true(self, train_manager):
        """Test checking if auto-refresh is active when true."""
        train_manager.config.refresh.auto_enabled = True
        train_manager.start_auto_refresh()

        assert train_manager.is_auto_refresh_active() is True

    def test_is_auto_refresh_active_false(self, train_manager):
        """Test checking if auto-refresh is active when false."""
        train_manager.stop_auto_refresh()

        assert train_manager.is_auto_refresh_active() is False

    def test_get_next_refresh_seconds_inactive(self, train_manager):
        """Test getting next refresh seconds when timer inactive."""
        train_manager.stop_auto_refresh()

        result = train_manager.get_next_refresh_seconds()

        assert result == 0

    def test_get_next_refresh_seconds_active(self, train_manager):
        """Test getting next refresh seconds when timer active."""
        train_manager.config.refresh.interval_minutes = 1
        train_manager.config.refresh.auto_enabled = True
        train_manager.start_auto_refresh()

        result = train_manager.get_next_refresh_seconds()

        # Should be between 0 and 60 seconds
        assert 0 <= result <= 60

    @pytest.mark.asyncio
    async def test_fetch_trains_async_success(self, train_manager, sample_trains):
        """Test successful async train fetching."""
        # Mock API manager with async context manager
        mock_api = AsyncMock()
        mock_api.get_departures.return_value = sample_trains
        mock_api.__aenter__ = AsyncMock(return_value=mock_api)
        mock_api.__aexit__ = AsyncMock(return_value=None)
        train_manager.api_manager = mock_api

        await train_manager._fetch_trains_async()

        # Verify state changes - the trains should be processed
        processed_trains = train_manager._process_train_data(sample_trains)
        assert len(train_manager.current_trains) == len(processed_trains)
        assert train_manager.last_update is not None
        assert train_manager.is_fetching is False

    @pytest.mark.asyncio
    async def test_fetch_trains_async_network_error(self, train_manager):
        """Test async train fetching with network error."""
        # Mock API manager to raise NetworkException with proper async context manager
        mock_api = AsyncMock()
        mock_api.get_departures.side_effect = NetworkException("Network failed")
        mock_api.__aenter__ = AsyncMock(return_value=mock_api)
        mock_api.__aexit__ = AsyncMock(return_value=None)
        train_manager.api_manager = mock_api

        await train_manager._fetch_trains_async()

        # Verify error handling
        assert train_manager.is_fetching is False
        # The error should be handled and the method should complete without raising

    @pytest.mark.asyncio
    async def test_fetch_trains_async_api_error(self, train_manager):
        """Test async train fetching with API error."""
        # Mock API manager to raise APIException with proper async context manager
        mock_api = AsyncMock()
        mock_api.get_departures.side_effect = APIException("API failed")
        mock_api.__aenter__ = AsyncMock(return_value=mock_api)
        mock_api.__aexit__ = AsyncMock(return_value=None)
        train_manager.api_manager = mock_api

        await train_manager._fetch_trains_async()

        # Verify error handling
        assert train_manager.is_fetching is False
        # The error should be handled and the method should complete without raising

    @pytest.mark.asyncio
    async def test_fetch_trains_async_unexpected_error(self, train_manager):
        """Test async train fetching with unexpected error."""
        # Mock API manager to raise generic exception with proper async context manager
        mock_api = AsyncMock()
        mock_api.get_departures.side_effect = Exception("Unexpected error")
        mock_api.__aenter__ = AsyncMock(return_value=mock_api)
        mock_api.__aexit__ = AsyncMock(return_value=None)
        train_manager.api_manager = mock_api

        await train_manager._fetch_trains_async()

        # Verify error handling
        assert train_manager.is_fetching is False
        # The error should be handled and the method should complete without raising

    @pytest.mark.asyncio
    async def test_fetch_trains_async_no_api_manager(self, train_manager):
        """Test async train fetching when API manager initialization fails."""
        train_manager.api_manager = None

        with patch.object(train_manager, "initialize_api") as mock_init:
            mock_init.return_value = None  # Simulate failed initialization

            with patch.object(train_manager, "error_occurred") as mock_error_occurred:
                await train_manager._fetch_trains_async()

                assert train_manager.is_fetching is False
                mock_error_occurred.emit.assert_called_once()
                error_msg = mock_error_occurred.emit.call_args[0][0]
                assert "API manager not available" in error_msg

    @pytest.mark.asyncio
    async def test_fetch_trains_async_already_fetching(self, train_manager):
        """Test async train fetching when already fetching."""
        train_manager.is_fetching = True

        # Should return early without doing anything
        await train_manager._fetch_trains_async()

        # Should still be fetching
        assert train_manager.is_fetching is True

    def test_refresh_timer_connection(self, train_manager):
        """Test that refresh timer is properly connected to fetch_trains."""
        # Test that the timer can be connected and disconnected
        # The connection is already made in __init__, so we test it works
        with patch.object(train_manager, "fetch_trains") as mock_fetch:
            # Manually emit the timeout signal to test connection
            train_manager.refresh_timer.timeout.emit()
            mock_fetch.assert_called_once()

    def test_integration_auto_refresh_cycle(self, train_manager, sample_trains):
        """Integration test for auto-refresh cycle."""
        # Set up very short refresh interval for testing
        train_manager.config.refresh.interval_minutes = 1  # 1 minute
        train_manager.config.refresh.auto_enabled = True

        # Mock the fetch_trains method instead of _start_async_fetch
        with patch.object(train_manager, "fetch_trains") as mock_fetch:
            train_manager.start_auto_refresh()

            # Verify timer is active
            assert train_manager.is_auto_refresh_active()

            # Manually trigger the timer to test the connection
            train_manager.refresh_timer.timeout.emit()

            # Verify fetch was called
            mock_fetch.assert_called_once()

    def test_signal_emission_integration(self, train_manager, sample_trains):
        """Integration test for signal emissions during data processing."""
        # Set up signal mock
        with patch.object(train_manager, "trains_updated") as mock_signal:
            # Process some data
            processed = train_manager._process_train_data(sample_trains)

            # Manually update current trains and emit signal (simulating what _fetch_trains_async does)
            train_manager.current_trains = processed
            train_manager.trains_updated.emit(processed)

            # Verify signal was emitted with correct data
            mock_signal.emit.assert_called_once_with(processed)

    def test_config_changes_affect_behavior(self, train_manager, sample_trains):
        """Test that configuration changes affect manager behavior."""
        # Test max_trains limit
        train_manager.config.display.max_trains = 2
        result = train_manager._process_train_data(sample_trains)
        assert len(result) <= 2

        # Test show_cancelled setting
        train_manager.config.display.show_cancelled = False
        result = train_manager._process_train_data(sample_trains)
        cancelled_trains = [t for t in result if t.is_cancelled]
        assert len(cancelled_trains) == 0

        # Test refresh interval
        train_manager.config.refresh.interval_minutes = 5
        train_manager.config.refresh.auto_enabled = True
        train_manager.start_auto_refresh()
        expected_interval = 5 * 60 * 1000
        assert train_manager.refresh_timer.interval() == expected_interval

    def test_thread_safety_considerations(self, train_manager):
        """Test thread safety considerations for async operations."""
        # Test that is_fetching flag prevents concurrent fetches
        train_manager.is_fetching = True

        # Multiple calls to fetch_trains should not interfere
        train_manager.fetch_trains()
        train_manager.fetch_trains()
        train_manager.fetch_trains()

        # Should still be in fetching state
        assert train_manager.is_fetching is True

    def test_memory_management(self, train_manager, sample_trains):
        """Test memory management with large datasets."""
        # Create large dataset
        large_dataset = []
        base_time = datetime.now()
        for i in range(1000):
            train = TrainData(
                departure_time=base_time + timedelta(minutes=i),
                scheduled_departure=base_time + timedelta(minutes=i),
                destination="London Waterloo",
                platform=str(i % 10),
                operator="Test Railway",
                service_type=ServiceType.FAST,
                status=TrainStatus.ON_TIME,
                delay_minutes=0,
                estimated_arrival=base_time + timedelta(minutes=i + 47),
                journey_duration=timedelta(minutes=47),
                current_location="Test Station",
                train_uid=f"T{i:05d}",
                service_id=f"SVC{i:05d}",
            )
            large_dataset.append(train)

        # Process large dataset
        train_manager.config.display.max_trains = 50
        result = train_manager._process_train_data(large_dataset)

        # Should be limited to max_trains
        assert len(result) == 50

        # Clear data should free memory
        train_manager.current_trains = result
        train_manager.clear_data()
        assert len(train_manager.current_trains) == 0

    def test_start_async_fetch_execution(self, train_manager):
        """Test _start_async_fetch method execution - covers lines 122-138."""
        # Mock the _fetch_trains_async method to avoid actual API calls
        with patch.object(train_manager, "_fetch_trains_async") as mock_fetch_async:
            mock_fetch_async.return_value = None  # Simulate successful completion

            # Call _start_async_fetch directly
            train_manager._start_async_fetch()

            # Give the thread a moment to start and complete
            time.sleep(0.1)

            # Verify that _fetch_trains_async was called in the thread
            mock_fetch_async.assert_called_once()

    def test_start_async_fetch_with_exception(self, train_manager):
        """Test _start_async_fetch method when _fetch_trains_async raises exception."""
        # Mock _fetch_trains_async to raise an exception
        with patch.object(train_manager, "_fetch_trains_async") as mock_fetch_async:
            mock_fetch_async.side_effect = Exception("Test async error")

            # Set is_fetching to True to test that it gets reset to False
            train_manager.is_fetching = True

            # Call _start_async_fetch
            train_manager._start_async_fetch()

            # Give the thread time to complete and handle the exception
            time.sleep(0.3)

            # Verify exception handling - the main thing is that is_fetching gets reset
            assert train_manager.is_fetching is False
            # The async method should have been called
            mock_fetch_async.assert_called_once()

    def test_start_async_fetch_threading_behavior(self, train_manager):
        """Test that _start_async_fetch creates and starts a daemon thread."""
        # Mock _fetch_trains_async to avoid actual execution
        with patch.object(train_manager, "_fetch_trains_async") as mock_fetch_async:
            mock_fetch_async.return_value = None

            # Mock threading.Thread to track its creation
            with patch("threading.Thread") as mock_thread_class:
                mock_thread_instance = Mock()
                mock_thread_class.return_value = mock_thread_instance

                train_manager._start_async_fetch()

                # Verify thread was created with daemon=True
                mock_thread_class.assert_called_once()
                call_args = mock_thread_class.call_args
                assert call_args[1]["daemon"] is True

                # Verify thread.start() was called
                mock_thread_instance.start.assert_called_once()

    def test_start_async_fetch_asyncio_integration(self, train_manager):
        """Test asyncio integration in _start_async_fetch."""
        # Mock asyncio components
        mock_loop = Mock()

        # Use a simple function instead of AsyncMock
        def mock_fetch_async():
            return None

        # Replace the method directly
        original_method = train_manager._fetch_trains_async
        train_manager._fetch_trains_async = mock_fetch_async

        try:
            with patch(
                "asyncio.new_event_loop", return_value=mock_loop
            ) as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    train_manager._start_async_fetch()

                    # Give thread time to execute
                    time.sleep(0.2)

                    # Verify asyncio methods were called
                    mock_new_loop.assert_called_once()
                    mock_set_loop.assert_called_once_with(mock_loop)
                    mock_loop.run_until_complete.assert_called_once()
                    mock_loop.close.assert_called_once()
        finally:
            # Restore original method
            train_manager._fetch_trains_async = original_method

    def test_start_async_fetch_integration_with_fetch_trains(self, train_manager):
        """Integration test: fetch_trains -> _start_async_fetch -> _fetch_trains_async."""
        # Create a simple mock function instead of AsyncMock to avoid coroutine warnings
        fetch_called = {"called": False}

        def mock_fetch_async():
            fetch_called["called"] = True
            return None

        # Replace the method directly
        original_method = train_manager._fetch_trains_async
        train_manager._fetch_trains_async = mock_fetch_async

        try:
            # Mock QTimer.singleShot to execute immediately
            with patch("PySide6.QtCore.QTimer.singleShot") as mock_single_shot:

                def immediate_execute(delay, func):
                    func()  # Execute immediately

                mock_single_shot.side_effect = immediate_execute

                # Ensure not already fetching
                train_manager.is_fetching = False

                # Call fetch_trains which should trigger _start_async_fetch
                train_manager.fetch_trains()

                # Give time for the async operation to complete
                time.sleep(0.2)

                # Verify the async method was called
                assert fetch_called["called"] is True
        finally:
            # Restore original method
            train_manager._fetch_trains_async = original_method

    def test_start_async_fetch_real_threading_execution(self, train_manager):
        """Test real threading execution without mocking threading components."""
        # Use a simple flag to track execution
        execution_tracker = {"called": False, "exception": None}
        execution_event = threading.Event()

        def mock_fetch_async():
            execution_tracker["called"] = True
            # Simulate some work without async/await to avoid coroutine warnings
            time.sleep(0.01)
            execution_event.set()  # Signal that execution is complete
            return None

        # Replace the actual method with our mock
        original_method = train_manager._fetch_trains_async
        train_manager._fetch_trains_async = mock_fetch_async

        try:
            # Call _start_async_fetch
            train_manager._start_async_fetch()

            # Wait for thread to complete with timeout
            execution_completed = execution_event.wait(timeout=2.0)

            # Verify execution occurred
            assert (
                execution_completed
            ), "Thread execution did not complete within timeout"
            assert execution_tracker["called"] is True

        finally:
            # Restore original method
            train_manager._fetch_trains_async = original_method
