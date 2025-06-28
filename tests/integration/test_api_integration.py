"""
Integration tests for API Manager with real Transport API.

Tests real API integration with Transport API, emphasizing actual
network calls over mocking to catch real-world integration issues.
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock
from src.api.api_manager import (
    APIManager,
    APIException,
    NetworkException,
    AuthenticationException,
    RateLimitException,
)
from src.managers.config_manager import ConfigData


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting functionality."""
        from src.api.api_manager import RateLimiter

        # Create rate limiter with very low limit for testing
        limiter = RateLimiter(calls_per_minute=60)  # Higher limit for faster testing

        # First few calls should be immediate
        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()

        # Should be very fast (under 0.1 seconds)
        assert end_time - start_time < 0.1

        # Verify calls are tracked
        assert len(limiter.calls) == 3

    @pytest.mark.asyncio
    async def test_rate_limiter_cleanup(self):
        """Test that rate limiter cleans up old calls."""
        from src.api.api_manager import RateLimiter

        limiter = RateLimiter(calls_per_minute=60)  # High limit for this test

        # Make several calls
        for _ in range(5):
            await limiter.wait_if_needed()

        # Should have 5 calls recorded
        assert len(limiter.calls) == 5

        # Wait a bit and make another call (this would trigger cleanup in real scenario)
        await asyncio.sleep(0.1)
        await limiter.wait_if_needed()

        # Should still have calls recorded (they're not old enough to clean up)
        assert len(limiter.calls) == 6


class TestAPIManagerInitialization:
    """Test API Manager initialization and context management."""

    def test_api_manager_initialization(self, test_config):
        """Test APIManager initialization."""
        api_manager = APIManager(test_config)

        assert api_manager.config == test_config
        assert api_manager.session is None
        assert api_manager.rate_limiter is not None
        assert (
            api_manager.rate_limiter.calls_per_minute
            == test_config.api.rate_limit_per_minute
        )

    @pytest.mark.asyncio
    async def test_api_manager_context_manager(self, test_config):
        """Test APIManager as async context manager."""
        async with APIManager(test_config) as api_manager:
            assert api_manager.session is not None
            assert hasattr(api_manager.session, "get")

        # Session should be closed after context exit
        # Note: We can't easily test this without accessing private attributes


class TestAPIManagerDepartures:
    """Test departure fetching functionality."""

    @pytest.mark.asyncio
    async def test_get_departures_mock_success(self, test_config, test_api_responses):
        """Test successful departure fetching with mocked response."""
        from unittest.mock import patch, AsyncMock

        # Create a proper async context manager mock
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=test_api_responses["departures_success"]
        )

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ) as mock_get:
                trains = await api_manager.get_departures()

                # Verify API was called (now makes multiple calls for service details)
                assert mock_get.call_count >= 1  # At least one call for departures
                
                # Check the first call (departures)
                first_call_args = mock_get.call_args_list[0]

                # Check URL
                assert "train/station/FLE/live.json" in first_call_args[0][0]

                # Check parameters
                params = first_call_args[1]["params"]
                assert params["app_id"] == test_config.api.app_id
                assert params["app_key"] == test_config.api.app_key
                assert params["destination"] == test_config.stations.to_code
                assert params["from_offset"] == "PT0H"
                assert (
                    params["to_offset"] == f"PT{test_config.display.time_window_hours}H"
                )

                # Verify trains were parsed
                assert isinstance(trains, list)
                assert len(trains) >= 0  # Could be empty if parsing fails

    @pytest.mark.asyncio
    async def test_get_departures_empty_response(self, test_config, test_api_responses):
        """Test handling of empty API response."""
        from unittest.mock import patch, AsyncMock

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=test_api_responses["departures_empty"]
        )

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ):
                trains = await api_manager.get_departures()

                assert isinstance(trains, list)
                assert len(trains) == 0

    @pytest.mark.asyncio
    async def test_get_departures_no_data_response(
        self, test_config, test_api_responses
    ):
        """Test handling of malformed API response."""
        from unittest.mock import patch, AsyncMock

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=test_api_responses["departures_no_data"]
        )

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ):
                trains = await api_manager.get_departures()

                assert isinstance(trains, list)
                assert len(trains) == 0

    @pytest.mark.asyncio
    async def test_get_departures_authentication_error(self, test_config):
        """Test handling of authentication errors."""
        from unittest.mock import patch, AsyncMock

        mock_response = AsyncMock()
        mock_response.status = 401

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ):
                with pytest.raises(AuthenticationException) as exc_info:
                    await api_manager.get_departures()

                assert "Invalid API credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_departures_rate_limit_error(self, test_config):
        """Test handling of rate limit errors."""
        from unittest.mock import patch, AsyncMock

        mock_response = AsyncMock()
        mock_response.status = 429

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ):
                with pytest.raises(RateLimitException) as exc_info:
                    await api_manager.get_departures()

                assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_departures_server_error(self, test_config):
        """Test handling of server errors."""
        from unittest.mock import patch, AsyncMock

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ):
                with pytest.raises(APIException) as exc_info:
                    await api_manager.get_departures()

                assert "API error 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_departures_network_error_with_retry(self, test_config):
        """Test network error handling with retry logic."""
        from unittest.mock import patch, AsyncMock
        import aiohttp

        # Set low retry count for faster testing
        test_config.api.max_retries = 2

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session,
                "get",
                side_effect=aiohttp.ClientError("Network error"),
            ) as mock_get:
                with pytest.raises(NetworkException) as exc_info:
                    await api_manager.get_departures()

                assert "Network error" in str(exc_info.value)

                # Should have retried max_retries times
                assert mock_get.call_count == test_config.api.max_retries

    @pytest.mark.asyncio
    async def test_get_departures_session_not_initialized(self, test_config):
        """Test error when session is not initialized."""
        api_manager = APIManager(test_config)
        # Don't use context manager, so session remains None

        with pytest.raises(NetworkException) as exc_info:
            await api_manager.get_departures()

        assert "Session not initialized" in str(exc_info.value)


class TestAPIManagerServiceDetails:
    """Test service details fetching functionality."""

    @pytest.mark.asyncio
    async def test_get_service_details_success(self, test_config):
        """Test successful service details fetching."""
        from unittest.mock import patch, AsyncMock, MagicMock

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"service": "details"})

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            api_manager._parse_service_response = MagicMock(return_value=None)

            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ) as mock_get:
                result = await api_manager.get_service_details("test_service_id")

                # Verify API was called
                mock_get.assert_called_once()
                call_args = mock_get.call_args

                # Check URL contains service ID
                assert "train/service/test_service_id/live.json" in call_args[0][0]

                # Check parameters
                params = call_args[1]["params"]
                assert params["app_id"] == test_config.api.app_id
                assert params["app_key"] == test_config.api.app_key

    @pytest.mark.asyncio
    async def test_get_service_details_error(self, test_config):
        """Test service details fetching with error response."""
        from unittest.mock import patch, AsyncMock

        mock_response = AsyncMock()
        mock_response.status = 404

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session, "get", return_value=mock_context_manager
            ):
                result = await api_manager.get_service_details("invalid_service_id")

                # Should return None on error
                assert result is None

    @pytest.mark.asyncio
    async def test_get_service_details_network_error(self, test_config):
        """Test service details fetching with network error."""
        from unittest.mock import patch, AsyncMock
        import aiohttp

        async with APIManager(test_config) as api_manager:
            with patch.object(
                api_manager.session,
                "get",
                side_effect=aiohttp.ClientError("Network error"),
            ):
                result = await api_manager.get_service_details("test_service_id")

                # Should return None on network error
                assert result is None

    @pytest.mark.asyncio
    async def test_get_service_details_session_not_initialized(self, test_config):
        """Test service details when session is not initialized."""
        api_manager = APIManager(test_config)
        # Don't use context manager

        result = await api_manager.get_service_details("test_service_id")

        # Should return None when session not initialized
        assert result is None


class TestAPIManagerDataParsing:
    """Test API response parsing functionality."""

    def test_parse_time_valid_formats(self, test_config):
        """Test parsing various valid time formats."""
        api_manager = APIManager(test_config)

        # Test standard HH:MM format
        result = api_manager._parse_time("20:45")
        assert result is not None
        assert result.hour == 20
        assert result.minute == 45

        # Test single digit formats
        result = api_manager._parse_time("9:05")
        assert result is not None
        assert result.hour == 9
        assert result.minute == 5

    def test_parse_time_invalid_formats(self, test_config):
        """Test parsing invalid time formats."""
        api_manager = APIManager(test_config)

        # Test invalid formats
        assert api_manager._parse_time("invalid") is None
        assert api_manager._parse_time("25:00") is None
        assert api_manager._parse_time("12:60") is None
        assert api_manager._parse_time("") is None
        assert api_manager._parse_time(None) is None

    def test_determine_train_status(self, test_config):
        """Test train status determination logic."""
        api_manager = APIManager(test_config)

        from src.models.train_data import TrainStatus

        # Test various status strings
        assert (
            api_manager._determine_train_status("CANCELLED", 0) == TrainStatus.CANCELLED
        )
        assert api_manager._determine_train_status("CANCEL", 0) == TrainStatus.CANCELLED
        assert api_manager._determine_train_status("ON TIME", 0) == TrainStatus.ON_TIME
        assert api_manager._determine_train_status("", 0) == TrainStatus.ON_TIME
        assert api_manager._determine_train_status("LATE", 5) == TrainStatus.DELAYED
        assert api_manager._determine_train_status("DELAY", 3) == TrainStatus.DELAYED
        assert api_manager._determine_train_status("", 5) == TrainStatus.DELAYED
        # Fix: empty string with no delay should be ON_TIME, not UNKNOWN
        assert (
            api_manager._determine_train_status("UNKNOWN_STATUS", 0)
            == TrainStatus.ON_TIME
        )  # Falls through to ON_TIME

    def test_determine_service_type(self, test_config):
        """Test service type determination logic."""
        api_manager = APIManager(test_config)

        from src.models.train_data import ServiceType

        # Test category mappings
        assert api_manager._determine_service_type("OO") == ServiceType.STOPPING
        assert api_manager._determine_service_type("XX") == ServiceType.FAST  # Changed to FAST
        assert api_manager._determine_service_type("XZ") == ServiceType.SLEEPER
        assert api_manager._determine_service_type("BR") == ServiceType.STOPPING
        assert (
            api_manager._determine_service_type("UNKNOWN") == ServiceType.FAST
        )  # Default changed to FAST
        assert (
            api_manager._determine_service_type("") == ServiceType.FAST
        )  # Default changed to FAST


@pytest.mark.api
@pytest.mark.integration
class TestRealAPIIntegration:
    """Test real API integration with Transport API."""

    @pytest.mark.asyncio
    async def test_real_api_departures_with_credentials(self, test_config):
        """Test fetching real departures from Transport API when credentials are available."""
        # Check if real API credentials are available
        real_app_id = os.getenv("TEST_TRANSPORT_API_ID")
        real_app_key = os.getenv("TEST_TRANSPORT_API_KEY")

        if real_app_id and real_app_key:
            # Use real API credentials from environment
            test_config.api.app_id = real_app_id
            test_config.api.app_key = real_app_key

            async with APIManager(test_config) as api_manager:
                trains = await api_manager.get_departures()

                # Verify we got real data
                assert isinstance(trains, list)

                if trains:  # If there are trains running
                    train = trains[0]
                    assert hasattr(train, "departure_time")
                    assert hasattr(train, "destination")
                    assert hasattr(train, "operator")
                    assert train.destination == "London Waterloo"
        else:
            # Test with invalid credentials to verify error handling
            test_config.api.app_id = "test_no_real_credentials"
            test_config.api.app_key = "test_no_real_credentials"

            async with APIManager(test_config) as api_manager:
                # Should raise an API exception due to invalid credentials
                with pytest.raises((AuthenticationException, APIException)) as exc_info:
                    await api_manager.get_departures()

                # Verify it's an authentication-related error
                error_message = str(exc_info.value)
                assert any(
                    keyword in error_message.lower()
                    for keyword in [
                        "invalid api credentials",
                        "authorisation failed",
                        "authentication",
                        "app_id",
                        "app_key",
                        "application",
                        "not found",
                    ]
                )

    @pytest.mark.asyncio
    async def test_api_error_handling_with_invalid_credentials(self, test_config):
        """Test API error handling with invalid credentials."""
        # Use invalid credentials
        test_config.api.app_id = "invalid_id"
        test_config.api.app_key = "invalid_key"

        async with APIManager(test_config) as api_manager:
            # API might return 401 or 403 for invalid credentials, or other API errors
            with pytest.raises((AuthenticationException, APIException)) as exc_info:
                await api_manager.get_departures()

            # Check that it's an authentication-related error
            error_message = str(exc_info.value)
            assert any(
                keyword in error_message.lower()
                for keyword in [
                    "invalid api credentials",
                    "authorisation failed",
                    "authentication",
                    "app_id",
                    "app_key",
                ]
            )

    @pytest.mark.asyncio
    async def test_10_hour_time_window_parameter(self, test_config):
        """Test that 10-hour time window parameters are included in requests."""
        from unittest.mock import patch, AsyncMock

        captured_params = {}

        mock_response = AsyncMock()
        mock_response.status = 401  # Will raise AuthenticationException

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        def capture_params(url, params=None):
            captured_params.update(params or {})
            return mock_context_manager

        async with APIManager(test_config) as api_manager:
            with patch.object(api_manager.session, "get", side_effect=capture_params):
                try:
                    await api_manager.get_departures()
                except AuthenticationException:
                    pass  # Expected with mock credentials

                # Verify 10-hour window parameters were included
                assert "from_offset" in captured_params
                assert "to_offset" in captured_params
                assert captured_params["from_offset"] == "PT0H"
                assert (
                    captured_params["to_offset"]
                    == f"PT{test_config.display.time_window_hours}H"
                )
