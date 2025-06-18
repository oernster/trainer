"""
Unit tests for Weather API Manager with focus on 100% code coverage.

Tests all functionality of the weather API manager including HTTP client,
weather data source, API manager, factory, error handling, and edge cases
to achieve complete coverage.
"""

import pytest
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, List

from src.api.weather_api_manager import (
    WeatherAPIException,
    WeatherNetworkException,
    WeatherDataException,
    WeatherRateLimitException,
    WeatherAPIResponse,
    WeatherDataSource,
    HTTPClient,
    AioHttpClient,
    OpenMeteoWeatherSource,
    WeatherAPIManager,
    WeatherAPIFactory,
)
from src.models.weather_data import (
    WeatherData,
    WeatherForecastData,
    Location,
    WeatherDataValidator,
)
from src.managers.weather_config import WeatherConfig


def create_test_weather_forecast_data(location: Location) -> WeatherForecastData:
    """Helper function to create valid WeatherForecastData for testing."""
    dummy_hourly_weather = WeatherData(
        timestamp=datetime.now(),
        temperature=20.0,
        humidity=80,
        weather_code=1,
        description="Test",
    )
    dummy_daily_weather = WeatherData(
        timestamp=datetime.now(),
        temperature=15.0,
        humidity=75,
        weather_code=2,
        description="Daily Test",
    )
    return WeatherForecastData(
        location=location,
        hourly_forecast=[dummy_hourly_weather],
        daily_forecast=[dummy_daily_weather],
    )


class TestWeatherAPIExceptions:
    """Test custom exception classes."""

    def test_weather_api_exception(self):
        """Test WeatherAPIException base class."""
        exc = WeatherAPIException("Test message")
        assert isinstance(exc, Exception)
        assert str(exc) == "Test message"

    def test_weather_network_exception(self):
        """Test WeatherNetworkException inherits from WeatherAPIException."""
        exc = WeatherNetworkException("Network error")
        assert isinstance(exc, WeatherAPIException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Network error"

    def test_weather_data_exception(self):
        """Test WeatherDataException inherits from WeatherAPIException."""
        exc = WeatherDataException("Data error")
        assert isinstance(exc, WeatherAPIException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Data error"

    def test_weather_rate_limit_exception(self):
        """Test WeatherRateLimitException inherits from WeatherAPIException."""
        exc = WeatherRateLimitException("Rate limit error")
        assert isinstance(exc, WeatherAPIException)
        assert isinstance(exc, Exception)
        assert str(exc) == "Rate limit error"


class TestWeatherAPIResponse:
    """Test WeatherAPIResponse dataclass."""

    def test_weather_api_response_creation(self):
        """Test WeatherAPIResponse creation."""
        timestamp = datetime.now()
        response = WeatherAPIResponse(
            status_code=200,
            data={"test": "data"},
            timestamp=timestamp,
            source="Open-Meteo",
        )

        assert response.status_code == 200
        assert response.data == {"test": "data"}
        assert response.timestamp == timestamp
        assert response.source == "Open-Meteo"


class TestAioHttpClient:
    """Test AioHttpClient implementation."""

    def test_aiohttpclient_init(self):
        """Test AioHttpClient initialization."""
        client = AioHttpClient(timeout_seconds=15)
        assert client._timeout.total == 15
        assert client._session is None

    def test_aiohttpclient_init_default_timeout(self):
        """Test AioHttpClient initialization with default timeout."""
        client = AioHttpClient()
        assert client._timeout.total == 10

    @pytest.mark.asyncio
    async def test_ensure_session_creates_new_session(self):
        """Test _ensure_session creates new session - covers lines 130-135."""
        client = AioHttpClient()

        # Mock aiohttp.ClientSession
        with patch(
            "src.api.weather_api_manager.aiohttp.ClientSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session.closed = False
            mock_session_class.return_value = mock_session

            session = await client._ensure_session()

            assert session == mock_session
            mock_session_class.assert_called_once()
            # Verify session was created with correct parameters
            call_args = mock_session_class.call_args
            assert call_args[1]["timeout"] == client._timeout
            assert "User-Agent" in call_args[1]["headers"]

    @pytest.mark.asyncio
    async def test_ensure_session_reuses_existing_session(self):
        """Test _ensure_session reuses existing session."""
        client = AioHttpClient()

        # Create a mock session that's not closed
        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        session = await client._ensure_session()

        assert session == mock_session

    @pytest.mark.asyncio
    async def test_ensure_session_recreates_closed_session(self):
        """Test _ensure_session recreates closed session - covers line 130."""
        client = AioHttpClient()

        # Create a mock closed session
        old_session = AsyncMock()
        old_session.closed = True
        client._session = old_session

        with patch(
            "src.api.weather_api_manager.aiohttp.ClientSession"
        ) as mock_session_class:
            new_session = AsyncMock()
            new_session.closed = False
            mock_session_class.return_value = new_session

            session = await client._ensure_session()

            assert session == new_session
            assert session != old_session

    @pytest.mark.asyncio
    async def test_get_success(self):
        """Test successful HTTP GET request - covers lines 139-153."""
        client = AioHttpClient()

        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"test": "data"})

        # Create proper async context manager mock
        class MockAsyncContextManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Mock the session to return our context manager
        mock_session = MagicMock()
        mock_session.get.return_value = MockAsyncContextManager()

        # Mock _ensure_session to return the mock session directly (not as coroutine)
        async def mock_ensure_session():
            return mock_session

        with patch.object(client, "_ensure_session", side_effect=mock_ensure_session):
            with patch("src.api.weather_api_manager.datetime") as mock_datetime:
                now = datetime.now()
                mock_datetime.now.return_value = now

                response = await client.get("http://test.com", {"param": "value"})

                assert isinstance(response, WeatherAPIResponse)
                assert response.status_code == 200
                assert response.data == {"test": "data"}
                assert response.timestamp == now
                assert response.source == "Open-Meteo"

    @pytest.mark.asyncio
    async def test_get_client_error(self):
        """Test HTTP GET with ClientError - covers lines 150-151."""
        client = AioHttpClient()

        # Create a proper async context manager mock that raises ClientError
        class MockAsyncContextManager:
            async def __aenter__(self):
                raise aiohttp.ClientError("Connection failed")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Mock the session to return our context manager
        mock_session = MagicMock()
        mock_session.get.return_value = MockAsyncContextManager()

        # Mock _ensure_session to return the mock session directly (not as coroutine)
        async def mock_ensure_session():
            return mock_session

        with patch.object(client, "_ensure_session", side_effect=mock_ensure_session):
            with pytest.raises(WeatherNetworkException) as exc_info:
                await client.get("http://test.com", {})

            assert "Network error: Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_generic_exception(self):
        """Test HTTP GET with generic exception - covers lines 152-153."""
        client = AioHttpClient()

        # Create a proper async context manager mock that raises generic exception
        class MockAsyncContextManager:
            async def __aenter__(self):
                raise Exception("Generic error")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Mock the session to return our context manager
        mock_session = MagicMock()
        mock_session.get.return_value = MockAsyncContextManager()

        # Mock _ensure_session to return the mock session directly (not as coroutine)
        async def mock_ensure_session():
            return mock_session

        with patch.object(client, "_ensure_session", side_effect=mock_ensure_session):
            with pytest.raises(WeatherAPIException) as exc_info:
                await client.get("http://test.com", {})

            assert "HTTP request failed: Generic error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_with_session(self):
        """Test close with active session - covers lines 157-158."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        await client.close()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_session(self):
        """Test close without session."""
        client = AioHttpClient()
        # No session set

        # Should not raise an exception
        await client.close()

    @pytest.mark.asyncio
    async def test_close_with_closed_session(self):
        """Test close with already closed session."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = True
        client._session = mock_session

        await client.close()

        # Should not call close on already closed session
        mock_session.close.assert_not_called()

    def test_close_sync_with_running_loop(self):
        """Test synchronous close with running event loop - covers lines 163-184."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        # Mock asyncio functions
        with patch(
            "src.api.weather_api_manager.asyncio.get_event_loop"
        ) as mock_get_loop:
            mock_loop = Mock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop

            client.close_sync()

            # Should create task for close
            mock_loop.create_task.assert_called_once()

    def test_close_sync_with_non_running_loop(self):
        """Test synchronous close with non-running event loop - covers lines 173-174."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        with patch(
            "src.api.weather_api_manager.asyncio.get_event_loop"
        ) as mock_get_loop:
            mock_loop = Mock()
            mock_loop.is_running.return_value = False
            mock_get_loop.return_value = mock_loop

            client.close_sync()

            # Should run until complete
            mock_loop.run_until_complete.assert_called_once()

    def test_close_sync_no_event_loop(self):
        """Test synchronous close with no event loop - covers lines 175-177."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        with patch(
            "src.api.weather_api_manager.asyncio.get_event_loop"
        ) as mock_get_loop, patch(
            "src.api.weather_api_manager.asyncio.run"
        ) as mock_run:
            mock_get_loop.side_effect = RuntimeError("No event loop")

            client.close_sync()

            # Should use asyncio.run
            mock_run.assert_called_once()

    def test_close_sync_with_exception(self):
        """Test synchronous close with exception - covers lines 181-184."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session

        with patch("src.api.weather_api_manager.asyncio") as mock_asyncio:
            # Make get_event_loop raise an exception that gets caught in the outer try-except
            mock_asyncio.get_event_loop.side_effect = Exception("Unexpected error")

            # Should not raise exception, just log warning and set session to None
            client.close_sync()

            # Session should be set to None as fallback
            assert client._session is None

    def test_close_sync_without_session(self):
        """Test synchronous close without session."""
        client = AioHttpClient()
        # No session set

        # Should not raise an exception
        client.close_sync()

    def test_close_sync_with_closed_session(self):
        """Test synchronous close with already closed session."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = True
        client._session = mock_session

        # Should not attempt to close
        client.close_sync()

    def test_close_sync_with_session_close_exception(self):
        """Test synchronous close with session close exception - covers lines 181-184."""
        client = AioHttpClient()

        mock_session = AsyncMock()
        mock_session.closed = False
        # Make the close method raise an exception
        mock_session.close.side_effect = Exception("Session close failed")
        client._session = mock_session

        with patch(
            "src.api.weather_api_manager.asyncio.get_event_loop"
        ) as mock_get_loop:
            mock_loop = Mock()
            mock_loop.is_running.return_value = False
            mock_loop.run_until_complete.side_effect = Exception(
                "Close operation failed"
            )
            mock_get_loop.return_value = mock_loop

            # Should not raise exception, just log warning and set session to None
            client.close_sync()

            # Session should be set to None as fallback
            assert client._session is None


class TestOpenMeteoWeatherSource:
    """Test OpenMeteoWeatherSource implementation."""

    @pytest.fixture
    def mock_config(self):
        """Create mock weather config."""
        return WeatherConfig(
            location_name="Test Location",
            location_latitude=51.5,
            location_longitude=-0.1,
            timeout_seconds=10,
        )

    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        return AsyncMock(spec=HTTPClient)

    @pytest.fixture
    def weather_source(self, mock_http_client, mock_config):
        """Create OpenMeteoWeatherSource instance."""
        return OpenMeteoWeatherSource(mock_http_client, mock_config)

    def test_init(self, mock_http_client, mock_config):
        """Test OpenMeteoWeatherSource initialization."""
        source = OpenMeteoWeatherSource(mock_http_client, mock_config)

        assert source._http_client == mock_http_client
        assert source._config == mock_config
        assert isinstance(source._validator, WeatherDataValidator)

    def test_get_source_name(self, weather_source):
        """Test get_source_name method."""
        assert weather_source.get_source_name() == "Open-Meteo"

    def test_get_source_url(self, weather_source):
        """Test get_source_url method."""
        assert weather_source.get_source_url() == "https://open-meteo.com/"

    @pytest.mark.asyncio
    async def test_fetch_weather_data_success(self, weather_source):
        """Test successful weather data fetch - covers lines 225-241."""
        location = Location("Test", 51.5, -0.1)

        # Mock API response with data that will create valid forecast entries
        api_data = {
            "hourly": {
                "time": [
                    "2023-01-01T00:00:00",
                    "2023-01-01T03:00:00",
                    "2023-01-01T06:00:00",
                ],
                "temperature_2m": [10.0, 12.0, 15.0],
                "relative_humidity_2m": [80, 75, 70],
                "weather_code": [1, 2, 3],
            },
            "daily": {
                "time": ["2023-01-01"],
                "temperature_2m_max": [15.0],
                "temperature_2m_min": [5.0],
                "weather_code": [1],
            },
        }

        mock_response = WeatherAPIResponse(
            status_code=200,
            data=api_data,
            timestamp=datetime.now(),
            source="Open-Meteo",
        )

        weather_source._http_client.get.return_value = mock_response

        # Mock the parsing methods to return valid data
        with patch.object(
            weather_source, "_parse_hourly_data"
        ) as mock_hourly, patch.object(
            weather_source, "_parse_daily_data"
        ) as mock_daily, patch.object(
            weather_source, "_filter_to_3hourly"
        ) as mock_filter, patch.object(
            weather_source._validator, "validate_forecast_data", return_value=True
        ):

            # Create valid test data
            test_forecast = create_test_weather_forecast_data(location)
            mock_hourly.return_value = test_forecast.hourly_forecast
            mock_daily.return_value = test_forecast.daily_forecast
            mock_filter.return_value = test_forecast.hourly_forecast

            result = await weather_source.fetch_weather_data(location)

            assert isinstance(result, WeatherForecastData)
            assert result.location == location
            assert len(result.hourly_forecast) > 0
            assert len(result.daily_forecast) > 0

    @pytest.mark.asyncio
    async def test_fetch_weather_data_api_error(self, weather_source):
        """Test weather data fetch with API error - covers lines 230-233."""
        location = Location("Test", 51.5, -0.1)

        mock_response = WeatherAPIResponse(
            status_code=500, data={}, timestamp=datetime.now(), source="Open-Meteo"
        )

        weather_source._http_client.get.return_value = mock_response

        with pytest.raises(WeatherAPIException) as exc_info:
            await weather_source.fetch_weather_data(location)

        assert "API returned status 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_weather_data_weather_api_exception_passthrough(
        self, weather_source
    ):
        """Test weather data fetch with WeatherAPIException passthrough - covers lines 237-238."""
        location = Location("Test", 51.5, -0.1)

        weather_source._http_client.get.side_effect = WeatherAPIException("API error")

        with pytest.raises(WeatherAPIException) as exc_info:
            await weather_source.fetch_weather_data(location)

        assert "API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_weather_data_generic_exception(self, weather_source):
        """Test weather data fetch with generic exception - covers lines 239-241."""
        location = Location("Test", 51.5, -0.1)

        weather_source._http_client.get.side_effect = Exception("Generic error")

        with pytest.raises(WeatherAPIException) as exc_info:
            await weather_source.fetch_weather_data(location)

        assert "Weather data fetch failed: Generic error" in str(exc_info.value)

    def test_build_api_params(self, weather_source):
        """Test _build_api_params method - covers line 245."""
        location = Location("Test", 51.5, -0.1)

        params = weather_source._build_api_params(location)

        expected_params = {
            "latitude": 51.5,
            "longitude": -0.1,
            "hourly": "temperature_2m,relative_humidity_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": "Europe/London",
            "forecast_days": 7,
        }

        assert params == expected_params

    def test_parse_api_response_success(self, weather_source):
        """Test successful API response parsing - covers lines 269-297."""
        location = Location("Test", 51.5, -0.1)

        data = {
            "hourly": {
                "time": ["2023-01-01T00:00:00"],
                "temperature_2m": [10.0],
                "relative_humidity_2m": [80],
                "weather_code": [1],
            },
            "daily": {
                "time": ["2023-01-01"],
                "temperature_2m_max": [15.0],
                "temperature_2m_min": [5.0],
                "weather_code": [1],
            },
        }

        # Mock the parsing methods to return valid data
        with patch.object(
            weather_source, "_parse_hourly_data"
        ) as mock_hourly, patch.object(
            weather_source, "_parse_daily_data"
        ) as mock_daily, patch.object(
            weather_source, "_filter_to_3hourly"
        ) as mock_filter, patch.object(
            weather_source._validator, "validate_forecast_data", return_value=True
        ):

            # Create valid test data
            test_forecast = create_test_weather_forecast_data(location)
            mock_hourly.return_value = test_forecast.hourly_forecast
            mock_daily.return_value = test_forecast.daily_forecast
            mock_filter.return_value = test_forecast.hourly_forecast

            result = weather_source._parse_api_response(data, location)

            assert isinstance(result, WeatherForecastData)
            assert result.location == location
            assert len(result.hourly_forecast) > 0
            assert len(result.daily_forecast) > 0

    def test_parse_api_response_validation_failure(self, weather_source):
        """Test API response parsing with validation failure - covers lines 285-286."""
        location = Location("Test", 51.5, -0.1)

        data = {
            "hourly": {
                "time": ["2023-01-01T00:00:00"],
                "temperature_2m": [10.0],
                "relative_humidity_2m": [80],
                "weather_code": [1],
            },
            "daily": {
                "time": ["2023-01-01"],
                "temperature_2m_max": [15.0],
                "temperature_2m_min": [5.0],
                "weather_code": [1],
            },
        }

        # Mock the parsing methods to return valid data so we can test validation failure
        with patch.object(
            weather_source, "_parse_hourly_data"
        ) as mock_hourly, patch.object(
            weather_source, "_parse_daily_data"
        ) as mock_daily, patch.object(
            weather_source, "_filter_to_3hourly"
        ) as mock_filter, patch.object(
            weather_source._validator, "validate_forecast_data", return_value=False
        ):

            # Create valid test data
            test_forecast = create_test_weather_forecast_data(location)
            mock_hourly.return_value = test_forecast.hourly_forecast
            mock_daily.return_value = test_forecast.daily_forecast
            mock_filter.return_value = test_forecast.hourly_forecast

            with pytest.raises(WeatherDataException) as exc_info:
                weather_source._parse_api_response(data, location)

            assert "Invalid weather data received" in str(exc_info.value)

    def test_parse_api_response_exception(self, weather_source):
        """Test API response parsing with exception - covers lines 295-297."""
        location = Location("Test", 51.5, -0.1)

        # Invalid data that will cause parsing error
        data = {"invalid": "data"}

        with pytest.raises(WeatherDataException) as exc_info:
            weather_source._parse_api_response(data, location)

        assert "Weather data parsing failed" in str(exc_info.value)

    def test_parse_hourly_data_empty(self, weather_source):
        """Test parsing empty hourly data - covers lines 301-302."""
        result = weather_source._parse_hourly_data({})
        assert result == []

    def test_parse_hourly_data_success(self, weather_source):
        """Test successful hourly data parsing - covers lines 304-335."""
        hourly_data = {
            "time": [
                "2023-01-01T00:00:00",
                "2023-01-01T03:00:00",
            ],  # Remove Z to avoid timezone issues
            "temperature_2m": [10.0, 12.0],
            "relative_humidity_2m": [80, 75],
            "weather_code": [1, 2],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=True
        ):
            result = weather_source._parse_hourly_data(hourly_data)

            assert len(result) == 2
            assert all(isinstance(w, WeatherData) for w in result)

    def test_parse_hourly_data_missing_data(self, weather_source):
        """Test hourly data parsing with missing data - covers lines 316-318."""
        hourly_data = {
            "time": ["2023-01-01T00:00:00", "2023-01-01T03:00:00"],
            "temperature_2m": [10.0],  # Missing second temperature
            "relative_humidity_2m": [80, 75],
            "weather_code": [1, 2],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=True
        ):
            result = weather_source._parse_hourly_data(hourly_data)

            # Should only process first entry
            assert len(result) == 1

    def test_parse_hourly_data_invalid_entry(self, weather_source):
        """Test hourly data parsing with invalid entry - covers lines 331-333."""
        hourly_data = {
            "time": ["invalid-time", "2023-01-01T03:00:00"],
            "temperature_2m": [10.0, 12.0],
            "relative_humidity_2m": [80, 75],
            "weather_code": [1, 2],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=True
        ):
            result = weather_source._parse_hourly_data(hourly_data)

            # Should skip invalid entry and process valid one
            assert len(result) == 1

    def test_parse_hourly_data_validation_failure(self, weather_source):
        """Test hourly data parsing with validation failure."""
        hourly_data = {
            "time": ["2023-01-01T00:00:00"],
            "temperature_2m": [10.0],
            "relative_humidity_2m": [80],
            "weather_code": [1],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=False
        ):
            result = weather_source._parse_hourly_data(hourly_data)

            # Should skip invalid data
            assert len(result) == 0

    def test_parse_daily_data_empty(self, weather_source):
        """Test parsing empty daily data - covers lines 339-340."""
        result = weather_source._parse_daily_data({})
        assert result == []

    def test_parse_daily_data_success(self, weather_source):
        """Test successful daily data parsing - covers lines 342-376."""
        daily_data = {
            "time": ["2023-01-01", "2023-01-02"],
            "temperature_2m_max": [15.0, 18.0],
            "temperature_2m_min": [5.0, 8.0],
            "weather_code": [1, 2],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=True
        ):
            result = weather_source._parse_daily_data(daily_data)

            assert len(result) == 2
            assert all(isinstance(w, WeatherData) for w in result)
            # Check temperature averaging
            assert result[0].temperature == 10.0  # (15 + 5) / 2
            assert result[1].temperature == 13.0  # (18 + 8) / 2

    def test_parse_daily_data_missing_data(self, weather_source):
        """Test daily data parsing with missing data - covers lines 354-356."""
        daily_data = {
            "time": ["2023-01-01", "2023-01-02"],
            "temperature_2m_max": [15.0],  # Missing second max temp
            "temperature_2m_min": [5.0, 8.0],
            "weather_code": [1, 2],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=True
        ):
            result = weather_source._parse_daily_data(daily_data)

            # Should only process first entry
            assert len(result) == 1

    def test_parse_daily_data_invalid_entry(self, weather_source):
        """Test daily data parsing with invalid entry - covers lines 372-374."""
        daily_data = {
            "time": ["invalid-date", "2023-01-02"],
            "temperature_2m_max": [15.0, 18.0],
            "temperature_2m_min": [5.0, 8.0],
            "weather_code": [1, 2],
        }

        with patch.object(
            weather_source._validator, "validate_weather_data", return_value=True
        ):
            result = weather_source._parse_daily_data(daily_data)

            # Should skip invalid entry and process valid one
            assert len(result) == 1

    def test_filter_to_3hourly_empty(self, weather_source):
        """Test filtering empty hourly data - covers lines 380-381."""
        result = weather_source._filter_to_3hourly([])
        assert result == []

    def test_filter_to_3hourly_success(self, weather_source):
        """Test successful 3-hourly filtering - covers line 384."""
        # Create 6 weather data points
        weather_data = []
        for i in range(6):
            weather_data.append(
                WeatherData(
                    timestamp=datetime.now() + timedelta(hours=i),
                    temperature=10.0 + i,
                    humidity=80,
                    weather_code=1,
                    description="Test",
                )
            )

        result = weather_source._filter_to_3hourly(weather_data)

        # Should return every 3rd item (indices 0, 3)
        assert len(result) == 2
        assert result[0] == weather_data[0]
        assert result[1] == weather_data[3]

    def test_get_weather_description_known_codes(self, weather_source):
        """Test weather description for known codes - covers lines 388-411."""
        # Test a few known codes
        assert weather_source._get_weather_description(0) == "Clear sky"
        assert weather_source._get_weather_description(1) == "Mainly clear"
        assert weather_source._get_weather_description(95) == "Thunderstorm"
        assert (
            weather_source._get_weather_description(99)
            == "Thunderstorm with heavy hail"
        )

    def test_get_weather_description_unknown_code(self, weather_source):
        """Test weather description for unknown code - covers line 411."""
        assert weather_source._get_weather_description(999) == "Unknown"

    @pytest.mark.asyncio
    async def test_shutdown(self, weather_source):
        """Test shutdown method - covers lines 415-416."""
        await weather_source.shutdown()
        weather_source._http_client.close.assert_called_once()

    def test_shutdown_sync_with_close_sync(self, weather_source):
        """Test synchronous shutdown with close_sync method."""
        # Mock http client with close_sync method
        weather_source._http_client.close_sync = Mock()

        weather_source.shutdown_sync()

        weather_source._http_client.close_sync.assert_called_once()

    def test_shutdown_sync_without_close_sync(self, weather_source):
        """Test synchronous shutdown without close_sync method."""
        # Remove close_sync method if it exists
        if hasattr(weather_source._http_client, "close_sync"):
            delattr(weather_source._http_client, "close_sync")

        # Should not raise an exception
        weather_source.shutdown_sync()


class TestWeatherAPIManager:
    """Test WeatherAPIManager implementation."""

    @pytest.fixture
    def mock_config(self):
        """Create mock weather config."""
        return WeatherConfig(
            location_name="Test Location",
            location_latitude=51.5,
            location_longitude=-0.1,
            cache_duration_minutes=30,
        )

    @pytest.fixture
    def mock_weather_source(self):
        """Create mock weather data source."""
        return AsyncMock(spec=WeatherDataSource)

    @pytest.fixture
    def weather_manager(self, mock_weather_source, mock_config):
        """Create WeatherAPIManager instance."""
        return WeatherAPIManager(mock_weather_source, mock_config)

    def test_init(self, mock_weather_source, mock_config):
        """Test WeatherAPIManager initialization."""
        manager = WeatherAPIManager(mock_weather_source, mock_config)

        assert manager._weather_source == mock_weather_source
        assert manager._config == mock_config
        assert manager._last_fetch_time is None
        assert manager._cached_data is None

    @pytest.mark.asyncio
    async def test_get_weather_forecast_with_location(self, weather_manager):
        """Test get_weather_forecast with provided location."""
        location = Location("Custom", 52.0, -1.0)

        # Mock forecast data
        forecast_data = create_test_weather_forecast_data(location)

        weather_manager._weather_source.fetch_weather_data.return_value = forecast_data

        result = await weather_manager.get_weather_forecast(location)

        assert result == forecast_data
        weather_manager._weather_source.fetch_weather_data.assert_called_once_with(
            location
        )

    @pytest.mark.asyncio
    async def test_get_weather_forecast_without_location(self, weather_manager):
        """Test get_weather_forecast without location (uses config) - covers lines 464-469."""
        # Mock forecast data
        forecast_data = create_test_weather_forecast_data(
            Location("Test Location", 51.5, -0.1)
        )

        weather_manager._weather_source.fetch_weather_data.return_value = forecast_data

        result = await weather_manager.get_weather_forecast()

        assert result == forecast_data
        # Verify location was created from config
        call_args = weather_manager._weather_source.fetch_weather_data.call_args[0][0]
        assert call_args.name == "Test Location"
        assert call_args.latitude == 51.5
        assert call_args.longitude == -0.1

    @pytest.mark.asyncio
    async def test_get_weather_forecast_with_cache_valid(self, weather_manager):
        """Test get_weather_forecast with valid cache - covers lines 472-474."""
        location = Location("Test", 51.5, -0.1)

        # Set up cached data
        cached_forecast = create_test_weather_forecast_data(location)
        weather_manager._cached_data = cached_forecast
        weather_manager._last_fetch_time = datetime.now() - timedelta(
            minutes=10
        )  # Recent

        result = await weather_manager.get_weather_forecast(location)

        assert result == cached_forecast
        # Should not call fetch_weather_data
        weather_manager._weather_source.fetch_weather_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_weather_forecast_fetch_and_cache(self, weather_manager):
        """Test get_weather_forecast fetch and cache update - covers lines 477-485."""
        location = Location("Test", 51.5, -0.1)

        # Mock forecast data
        forecast_data = create_test_weather_forecast_data(location)

        weather_manager._weather_source.fetch_weather_data.return_value = forecast_data

        with patch("src.api.weather_api_manager.datetime") as mock_datetime:
            now = datetime.now()
            mock_datetime.now.return_value = now

            result = await weather_manager.get_weather_forecast(location)

            assert result == forecast_data
            assert weather_manager._cached_data == forecast_data
            assert weather_manager._last_fetch_time == now

    @pytest.mark.asyncio
    async def test_get_weather_forecast_fetch_error_with_cache(self, weather_manager):
        """Test get_weather_forecast with fetch error but cached data available - covers lines 487-496."""
        location = Location("Test", 51.5, -0.1)

        # Set up stale cached data
        cached_forecast = create_test_weather_forecast_data(location)
        weather_manager._cached_data = cached_forecast
        weather_manager._last_fetch_time = datetime.now() - timedelta(hours=2)  # Stale

        # Mock fetch to raise exception
        weather_manager._weather_source.fetch_weather_data.side_effect = Exception(
            "Fetch failed"
        )

        result = await weather_manager.get_weather_forecast(location)

        # Should return stale cached data
        assert result == cached_forecast

    @pytest.mark.asyncio
    async def test_get_weather_forecast_fetch_error_no_cache(self, weather_manager):
        """Test get_weather_forecast with fetch error and no cached data - covers line 496."""
        location = Location("Test", 51.5, -0.1)

        # No cached data
        weather_manager._cached_data = None

        # Mock fetch to raise exception
        weather_manager._weather_source.fetch_weather_data.side_effect = Exception(
            "Fetch failed"
        )

        with pytest.raises(Exception) as exc_info:
            await weather_manager.get_weather_forecast(location)

        assert "Fetch failed" in str(exc_info.value)

    def test_is_cache_valid_no_data(self, weather_manager):
        """Test _is_cache_valid with no cached data."""
        assert not weather_manager._is_cache_valid()

    def test_is_cache_valid_no_fetch_time(self, weather_manager):
        """Test _is_cache_valid with no fetch time."""
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )
        weather_manager._last_fetch_time = None

        assert not weather_manager._is_cache_valid()

    def test_is_cache_valid_fresh_data(self, weather_manager):
        """Test _is_cache_valid with fresh data."""
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )
        weather_manager._last_fetch_time = datetime.now() - timedelta(minutes=10)

        assert weather_manager._is_cache_valid()

    def test_is_cache_valid_stale_data(self, weather_manager):
        """Test _is_cache_valid with stale data."""
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )
        weather_manager._last_fetch_time = datetime.now() - timedelta(hours=2)

        assert not weather_manager._is_cache_valid()

    def test_clear_cache(self, weather_manager):
        """Test clear_cache method."""
        # Set up cache
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )
        weather_manager._last_fetch_time = datetime.now()

        weather_manager.clear_cache()

        assert weather_manager._cached_data is None
        assert weather_manager._last_fetch_time is None

    def test_get_cache_info(self, weather_manager):
        """Test get_cache_info method - covers line 516."""
        # Set up cache
        cached_data = create_test_weather_forecast_data(Location("Test", 51.5, -0.1))
        fetch_time = datetime.now() - timedelta(minutes=10)
        weather_manager._cached_data = cached_data
        weather_manager._last_fetch_time = fetch_time

        info = weather_manager.get_cache_info()

        assert info["has_cached_data"] is True
        assert info["last_fetch_time"] == fetch_time
        assert info["cache_valid"] is True
        assert info["cache_duration_seconds"] == 1800  # 30 minutes * 60

    @pytest.mark.asyncio
    async def test_shutdown(self, weather_manager):
        """Test shutdown method - covers lines 526-530."""
        # Set up cache
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )
        weather_manager._last_fetch_time = datetime.now()

        await weather_manager.shutdown()

        # Should shutdown weather source
        weather_manager._weather_source.shutdown.assert_called_once()

        # Should clear cache
        assert weather_manager._cached_data is None
        assert weather_manager._last_fetch_time is None

    def test_shutdown_sync_with_shutdown_sync_method(self, weather_manager):
        """Test synchronous shutdown with shutdown_sync method."""
        # Mock weather source with shutdown_sync method
        weather_manager._weather_source.shutdown_sync = Mock()

        # Set up cache
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )
        weather_manager._last_fetch_time = datetime.now()

        weather_manager.shutdown_sync()

        # Should call shutdown_sync on weather source
        weather_manager._weather_source.shutdown_sync.assert_called_once()

        # Should clear cache
        assert weather_manager._cached_data is None
        assert weather_manager._last_fetch_time is None

    def test_shutdown_sync_without_shutdown_sync_method(self, weather_manager):
        """Test synchronous shutdown without shutdown_sync method."""
        # Remove shutdown_sync method if it exists
        if hasattr(weather_manager._weather_source, "shutdown_sync"):
            delattr(weather_manager._weather_source, "shutdown_sync")

        # Set up cache
        weather_manager._cached_data = create_test_weather_forecast_data(
            Location("Test", 51.5, -0.1)
        )

        # Should not raise an exception
        weather_manager.shutdown_sync()

        # Should still clear cache
        assert weather_manager._cached_data is None


class TestWeatherAPIFactory:
    """Test WeatherAPIFactory implementation."""

    def test_create_openmeteo_manager(self):
        """Test create_openmeteo_manager factory method."""
        config = WeatherConfig(timeout_seconds=15)

        manager = WeatherAPIFactory.create_openmeteo_manager(config)

        assert isinstance(manager, WeatherAPIManager)
        assert manager._config == config
        assert isinstance(manager._weather_source, OpenMeteoWeatherSource)

    def test_create_manager_from_config(self):
        """Test create_manager_from_config factory method."""
        config = WeatherConfig(timeout_seconds=20)

        manager = WeatherAPIFactory.create_manager_from_config(config)

        assert isinstance(manager, WeatherAPIManager)
        assert manager._config == config


class TestWeatherDataSourceAbstractMethods:
    """Test abstract methods of WeatherDataSource."""

    def test_weather_data_source_abstract_methods(self):
        """Test that WeatherDataSource cannot be instantiated."""
        with pytest.raises(TypeError):
            WeatherDataSource()  # type: ignore


class TestHTTPClientAbstractMethods:
    """Test abstract methods of HTTPClient."""

    def test_http_client_abstract_methods(self):
        """Test that HTTPClient cannot be instantiated."""
        with pytest.raises(TypeError):
            HTTPClient()  # type: ignore


# Integration tests for edge cases and error conditions
class TestIntegrationAndEdgeCases:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_full_integration_flow(self):
        """Test full integration flow from factory to data fetch."""
        config = WeatherConfig(
            location_name="Integration Test",
            location_latitude=51.5,
            location_longitude=-0.1,
            timeout_seconds=5,
        )

        # Create manager using factory
        manager = WeatherAPIFactory.create_openmeteo_manager(config)

        # Create test forecast data directly
        location = Location("Integration Test", 51.5, -0.1)
        test_forecast = create_test_weather_forecast_data(location)

        # Mock the weather source's fetch method instead
        with patch.object(
            manager._weather_source, "fetch_weather_data", return_value=test_forecast
        ) as mock_fetch:
            # Test the full flow
            result = await manager.get_weather_forecast()

            assert isinstance(result, WeatherForecastData)
            assert result.location.name == "Integration Test"

            # Test cache functionality
            cached_result = await manager.get_weather_forecast()
            assert cached_result == result

            # Verify fetch was only called once (second call used cache)
            assert mock_fetch.call_count == 1

        # Clean up
        await manager.shutdown()

    def test_weather_api_response_with_various_data_types(self):
        """Test WeatherAPIResponse with various data types."""
        timestamp = datetime.now()

        # Test with different data types
        response1 = WeatherAPIResponse(200, {"key": "value"}, timestamp, "source")
        response2 = WeatherAPIResponse(404, {}, timestamp, "source")
        response3 = WeatherAPIResponse(500, {}, timestamp, "source")

        assert response1.data == {"key": "value"}
        assert response2.data == {}
        assert response3.data == {}

    @pytest.mark.asyncio
    async def test_concurrent_weather_requests(self):
        """Test concurrent weather data requests."""
        config = WeatherConfig()
        http_client = AsyncMock(spec=HTTPClient)
        weather_source = OpenMeteoWeatherSource(http_client, config)
        manager = WeatherAPIManager(weather_source, config)

        location = Location("Test", 51.5, -0.1)

        # Mock successful response
        forecast_data = create_test_weather_forecast_data(location)
        weather_source.fetch_weather_data = AsyncMock(return_value=forecast_data)

        # Make concurrent requests
        tasks = [manager.get_weather_forecast(location) for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # All should return the same cached result
        assert all(result == forecast_data for result in results)

    def test_location_validation_in_weather_context(self):
        """Test location validation in weather context."""
        # Valid locations
        valid_locations = [
            Location("London", 51.5074, -0.1278),
            Location("New York", 40.7128, -74.0060),
            Location("Tokyo", 35.6762, 139.6503),
            Location("Sydney", -33.8688, 151.2093),
        ]

        for location in valid_locations:
            assert location.name
            assert -90 <= location.latitude <= 90
            assert -180 <= location.longitude <= 180

        # Invalid locations should raise ValueError
        with pytest.raises(ValueError):
            Location("Invalid", 91.0, 0.0)  # Invalid latitude

        with pytest.raises(ValueError):
            Location("Invalid", 0.0, 181.0)  # Invalid longitude

        with pytest.raises(ValueError):
            Location("", 0.0, 0.0)  # Empty name

    def test_weather_config_integration_with_api_manager(self):
        """Test weather config integration with API manager."""
        # Test various config scenarios
        configs = [
            WeatherConfig(cache_duration_minutes=5),
            WeatherConfig(cache_duration_minutes=60),
            WeatherConfig(timeout_seconds=5),
            WeatherConfig(timeout_seconds=30),
        ]

        for config in configs:
            manager = WeatherAPIFactory.create_openmeteo_manager(config)
            assert manager._config == config

            # Test cache duration conversion
            cache_info = manager.get_cache_info()
            expected_seconds = config.cache_duration_minutes * 60
            assert cache_info["cache_duration_seconds"] == expected_seconds
