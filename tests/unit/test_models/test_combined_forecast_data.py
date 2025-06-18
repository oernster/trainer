"""
Comprehensive tests for combined forecast data models to achieve 100% test coverage.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
import logging

from src.models.combined_forecast_data import (
    CombinedForecastData,
    DailyForecastData,
    CombinedDataStatus,
    ForecastDataQuality,
    CombinedForecastValidator,
    create_weather_only_forecast,
    create_astronomy_only_forecast,
    create_complete_forecast,
)
from src.models.weather_data import WeatherData, WeatherForecastData
from src.models.weather_data import Location as WeatherLocation
from src.models.astronomy_data import (
    AstronomyData,
    AstronomyForecastData,
    AstronomyEvent,
    AstronomyEventType,
    AstronomyEventPriority,
)
from src.models.astronomy_data import Location as AstronomyLocation


class TestDailyForecastData:
    """Comprehensive tests for DailyForecastData class."""

    def test_daily_forecast_validation_weather_date_mismatch(self):
        """Test validation with weather data date mismatch."""
        test_date = date.today()
        wrong_date = test_date + timedelta(days=1)

        weather_data = WeatherData(
            timestamp=datetime.combine(wrong_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        with pytest.raises(
            ValueError, match="Weather data date must match forecast date"
        ):
            DailyForecastData(date=test_date, weather_data=weather_data)

    def test_daily_forecast_validation_astronomy_date_mismatch(self):
        """Test validation with astronomy data date mismatch."""
        test_date = date.today()
        wrong_date = test_date + timedelta(days=1)

        astronomy_data = AstronomyData(date=wrong_date, events=[])

        with pytest.raises(
            ValueError, match="Astronomy data date must match forecast date"
        ):
            DailyForecastData(date=test_date, astronomy_data=astronomy_data)

    def test_primary_astronomy_event_without_data(self):
        """Test primary_astronomy_event property without astronomy data."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        assert daily_forecast.primary_astronomy_event is None

    def test_astronomy_event_count_without_data(self):
        """Test astronomy_event_count property without astronomy data."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        assert daily_forecast.astronomy_event_count == 0

    def test_has_high_priority_astronomy_without_data(self):
        """Test has_high_priority_astronomy property without astronomy data."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        assert not daily_forecast.has_high_priority_astronomy

    def test_weather_description_without_data(self):
        """Test weather_description property without weather data."""
        test_date = date.today()

        astronomy_data = AstronomyData(date=test_date, events=[])

        daily_forecast = DailyForecastData(
            date=test_date, astronomy_data=astronomy_data
        )

        assert daily_forecast.weather_description == "No weather data"

    def test_temperature_display_without_data(self):
        """Test temperature_display property without weather data."""
        test_date = date.today()

        astronomy_data = AstronomyData(date=test_date, events=[])

        daily_forecast = DailyForecastData(
            date=test_date, astronomy_data=astronomy_data
        )

        assert daily_forecast.temperature_display == "N/A"

    def test_is_precipitation_day_without_data(self):
        """Test is_precipitation_day property without weather data."""
        test_date = date.today()

        astronomy_data = AstronomyData(date=test_date, events=[])

        daily_forecast = DailyForecastData(
            date=test_date, astronomy_data=astronomy_data
        )

        assert not daily_forecast.is_precipitation_day

    def test_moon_phase_icon_without_data(self):
        """Test moon_phase_icon property without astronomy data."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        assert daily_forecast.moon_phase_icon == "🌑"

    def test_get_astronomy_events_by_type_without_data(self):
        """Test get_astronomy_events_by_type method without astronomy data."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        events = daily_forecast.get_astronomy_events_by_type(AstronomyEventType.APOD)
        assert events == []

    def test_get_display_summary_no_data(self):
        """Test get_display_summary method with no meaningful data."""
        test_date = date.today()

        astronomy_data = AstronomyData(date=test_date, events=[])  # No events

        daily_forecast = DailyForecastData(
            date=test_date, astronomy_data=astronomy_data
        )

        summary = daily_forecast.get_display_summary()
        assert summary == "No data available"


class TestCombinedForecastData:
    """Comprehensive tests for CombinedForecastData class."""

    def test_create_factory_method_no_data(self):
        """Test create factory method with no data."""
        location = WeatherLocation("Test Location", 51.5074, -0.1278)

        # This should create a forecast with COMPLETE_FAILURE status but still have empty daily_forecasts
        # which violates the validation. Let's test this by bypassing the validation
        try:
            combined_forecast = CombinedForecastData.create(location)
            # If it doesn't raise an error, check the status
            assert combined_forecast.status == CombinedDataStatus.COMPLETE_FAILURE
        except ValueError as e:
            # Expected behavior - no daily forecasts means validation fails
            assert "Combined forecast must contain at least one daily forecast" in str(
                e
            )

    def test_get_weather_for_date_not_found(self):
        """Test _get_weather_for_date method when no data found."""
        location = WeatherLocation("Test Location", 51.5074, -0.1278)
        target_date = date.today()
        different_date = target_date + timedelta(days=5)

        weather_data = WeatherData(
            timestamp=datetime.combine(different_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        result = CombinedForecastData._get_weather_for_date(
            weather_forecast, target_date
        )
        assert result is None

    def test_get_weather_for_date_hourly_noon(self):
        """Test _get_weather_for_date method with hourly forecast at noon."""
        location = WeatherLocation("Test Location", 51.5074, -0.1278)
        target_date = date.today()

        noon_weather = WeatherData(
            timestamp=datetime.combine(
                target_date, datetime.min.time().replace(hour=12)
            ),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        other_weather = WeatherData(
            timestamp=datetime.combine(
                target_date, datetime.min.time().replace(hour=8)
            ),
            temperature=18.0,
            humidity=55,
            weather_code=1,
            description="Clear",
        )

        weather_forecast = WeatherForecastData(
            location=location,
            daily_forecast=[],
            hourly_forecast=[other_weather, noon_weather],
        )

        result = CombinedForecastData._get_weather_for_date(
            weather_forecast, target_date
        )
        assert result == noon_weather

    def test_get_weather_for_date_hourly_any(self):
        """Test _get_weather_for_date method with any hourly forecast data."""
        location = WeatherLocation("Test Location", 51.5074, -0.1278)
        target_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(
                target_date, datetime.min.time().replace(hour=8)
            ),
            temperature=18.0,
            humidity=55,
            weather_code=1,
            description="Clear",
        )

        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[], hourly_forecast=[weather_data]
        )

        result = CombinedForecastData._get_weather_for_date(
            weather_forecast, target_date
        )
        assert result == weather_data

    def test_determine_data_quality_excellent(self):
        """Test _determine_data_quality method for excellent quality."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.combine(test_date, datetime.min.time()),
        )

        astronomy_data = AstronomyData(date=test_date, events=[event])

        quality = CombinedForecastData._determine_data_quality(
            weather_data, astronomy_data
        )
        assert quality == ForecastDataQuality.EXCELLENT

    def test_determine_data_quality_good(self):
        """Test _determine_data_quality method for good quality."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        astronomy_data = AstronomyData(date=test_date, events=[])  # No events

        quality = CombinedForecastData._determine_data_quality(
            weather_data, astronomy_data
        )
        assert quality == ForecastDataQuality.GOOD

    def test_determine_data_quality_partial(self):
        """Test _determine_data_quality method for partial quality."""
        test_date = date.today()

        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        quality = CombinedForecastData._determine_data_quality(weather_data, None)
        assert quality == ForecastDataQuality.PARTIAL

        quality = CombinedForecastData._determine_data_quality(
            None, AstronomyData(date=test_date, events=[])
        )
        assert quality == ForecastDataQuality.PARTIAL

    def test_determine_data_quality_poor(self):
        """Test _determine_data_quality method for poor quality."""
        quality = CombinedForecastData._determine_data_quality(None, None)
        assert quality == ForecastDataQuality.POOR

    def test_determine_status_complete(self):
        """Test _determine_status method for complete status."""
        location = WeatherLocation("Test", 0.0, 0.0)

        # Create valid weather forecast with data
        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        # Create valid astronomy forecast with data
        astronomy_location = AstronomyLocation("Test", 0.0, 0.0)
        astronomy_data = AstronomyData(date=date.today(), events=[])
        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        status = CombinedForecastData._determine_status(
            weather_forecast, astronomy_forecast, []
        )
        assert status == CombinedDataStatus.COMPLETE

    def test_determine_status_weather_only(self):
        """Test _determine_status method for weather only status."""
        location = WeatherLocation("Test", 0.0, 0.0)

        # Create valid weather forecast with data
        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        status = CombinedForecastData._determine_status(weather_forecast, None, [])
        assert status == CombinedDataStatus.WEATHER_ONLY

    def test_determine_status_astronomy_only(self):
        """Test _determine_status method for astronomy only status."""
        astronomy_location = AstronomyLocation("Test", 0.0, 0.0)

        # Create valid astronomy forecast with data
        astronomy_data = AstronomyData(date=date.today(), events=[])
        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        status = CombinedForecastData._determine_status(None, astronomy_forecast, [])
        assert status == CombinedDataStatus.ASTRONOMY_ONLY

    def test_determine_status_partial_failure(self):
        """Test _determine_status method for partial failure status."""
        # Create a real daily forecast for testing
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )
        daily_forecasts = [daily_forecast]  # Some daily forecasts exist

        status = CombinedForecastData._determine_status(None, None, daily_forecasts)
        assert status == CombinedDataStatus.PARTIAL_FAILURE

    def test_determine_status_complete_failure(self):
        """Test _determine_status method for complete failure status."""
        status = CombinedForecastData._determine_status(None, None, [])
        assert status == CombinedDataStatus.COMPLETE_FAILURE

    @patch("src.models.combined_forecast_data.datetime")
    def test_is_stale_true(self, mock_datetime):
        """Test is_stale property when data is stale."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        last_updated = datetime(2023, 6, 15, 10, 0, 0)  # 2 hours ago
        mock_datetime.now.return_value = now

        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            last_updated=last_updated,
        )

        assert combined_forecast.is_stale

    def test_has_complete_data_property(self):
        """Test has_complete_data property."""
        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        # Test complete status
        complete_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            status=CombinedDataStatus.COMPLETE,
        )
        assert complete_forecast.has_complete_data

        # Test incomplete status
        incomplete_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            status=CombinedDataStatus.WEATHER_ONLY,
        )
        assert not incomplete_forecast.has_complete_data

    def test_has_weather_data_property(self):
        """Test has_weather_data property."""
        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        # Test with weather forecast
        with_weather = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            weather_forecast=weather_forecast,
        )
        assert with_weather.has_weather_data

        # Test without weather forecast
        without_weather = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )
        assert not without_weather.has_weather_data

    def test_has_astronomy_data_property(self):
        """Test has_astronomy_data property."""
        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        astronomy_location = AstronomyLocation("Test", 0.0, 0.0)
        astronomy_data = AstronomyData(date=date.today(), events=[])
        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        # Test with astronomy forecast
        with_astronomy = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            astronomy_forecast=astronomy_forecast,
        )
        assert with_astronomy.has_astronomy_data

        # Test without astronomy forecast
        without_astronomy = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )
        assert not without_astronomy.has_astronomy_data

    def test_has_high_priority_astronomy_property(self):
        """Test has_high_priority_astronomy property."""
        location = WeatherLocation("Test", 0.0, 0.0)

        today = date.today()

        high_priority_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="High Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.HIGH,
        )

        low_priority_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Low Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.LOW,
        )

        # Test with high priority events
        astronomy_data_high = AstronomyData(date=today, events=[high_priority_event])
        daily_forecast_high = DailyForecastData(
            date=today, astronomy_data=astronomy_data_high
        )

        forecast_with_high = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast_high]
        )
        assert forecast_with_high.has_high_priority_astronomy

        # Test without high priority events
        astronomy_data_low = AstronomyData(date=today, events=[low_priority_event])
        daily_forecast_low = DailyForecastData(
            date=today, astronomy_data=astronomy_data_low
        )

        forecast_without_high = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast_low]
        )
        assert not forecast_without_high.has_high_priority_astronomy

    @patch("src.models.combined_forecast_data.date")
    def test_get_today_forecast(self, mock_date):
        """Test get_today_forecast method."""
        today = date(2023, 6, 15)
        mock_date.today.return_value = today

        location = WeatherLocation("Test", 0.0, 0.0)
        weather_data = WeatherData(
            timestamp=datetime.combine(today, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=today, weather_data=weather_data)

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )

        result = combined_forecast.get_today_forecast()
        assert result == daily_forecast

    @patch("src.models.combined_forecast_data.date")
    def test_get_tomorrow_forecast(self, mock_date):
        """Test get_tomorrow_forecast method."""
        today = date(2023, 6, 15)
        tomorrow = date(2023, 6, 16)
        mock_date.today.return_value = today

        location = WeatherLocation("Test", 0.0, 0.0)
        weather_data = WeatherData(
            timestamp=datetime.combine(tomorrow, datetime.min.time()),
            temperature=22.0,
            humidity=55,
            weather_code=2,
            description="Cloudy",
        )

        daily_forecast = DailyForecastData(date=tomorrow, weather_data=weather_data)

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )

        result = combined_forecast.get_tomorrow_forecast()
        assert result == daily_forecast

    def test_get_forecasts_with_astronomy(self):
        """Test get_forecasts_with_astronomy method."""
        location = WeatherLocation("Test", 0.0, 0.0)

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Forecast with astronomy data
        astronomy_data = AstronomyData(date=today, events=[])
        forecast_with_astronomy = DailyForecastData(
            date=today, astronomy_data=astronomy_data
        )

        # Forecast without astronomy data
        weather_data = WeatherData(
            timestamp=datetime.combine(tomorrow, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        forecast_without_astronomy = DailyForecastData(
            date=tomorrow, weather_data=weather_data
        )

        combined_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[forecast_with_astronomy, forecast_without_astronomy],
        )

        result = combined_forecast.get_forecasts_with_astronomy()
        assert len(result) == 1
        assert result[0] == forecast_with_astronomy

    def test_get_forecasts_with_weather(self):
        """Test get_forecasts_with_weather method."""
        location = WeatherLocation("Test", 0.0, 0.0)

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Forecast with weather data
        weather_data = WeatherData(
            timestamp=datetime.combine(today, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        forecast_with_weather = DailyForecastData(date=today, weather_data=weather_data)

        # Forecast without weather data
        astronomy_data = AstronomyData(date=tomorrow, events=[])
        forecast_without_weather = DailyForecastData(
            date=tomorrow, astronomy_data=astronomy_data
        )

        combined_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[forecast_with_weather, forecast_without_weather],
        )

        result = combined_forecast.get_forecasts_with_weather()
        assert len(result) == 1
        assert result[0] == forecast_with_weather

    def test_get_high_priority_astronomy_days(self):
        """Test get_high_priority_astronomy_days method."""
        location = WeatherLocation("Test", 0.0, 0.0)

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # High priority event
        high_priority_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="High Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.HIGH,
        )

        # Low priority event
        low_priority_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Low Priority Event",
            description="Test Description",
            start_time=datetime.combine(tomorrow, datetime.min.time()),
            priority=AstronomyEventPriority.LOW,
        )

        astronomy_data_high = AstronomyData(date=today, events=[high_priority_event])
        astronomy_data_low = AstronomyData(date=tomorrow, events=[low_priority_event])

        forecast_high = DailyForecastData(
            date=today, astronomy_data=astronomy_data_high
        )
        forecast_low = DailyForecastData(
            date=tomorrow, astronomy_data=astronomy_data_low
        )

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[forecast_high, forecast_low]
        )

        result = combined_forecast.get_high_priority_astronomy_days()
        assert len(result) == 1
        assert result[0] == forecast_high

    def test_get_precipitation_days(self):
        """Test get_precipitation_days method."""
        location = WeatherLocation("Test", 0.0, 0.0)

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Weather with precipitation
        rain_weather = WeatherData(
            timestamp=datetime.combine(today, datetime.min.time()),
            temperature=15.0,
            humidity=80,
            weather_code=61,  # Rain
            description="Rain",
        )

        # Weather without precipitation
        clear_weather = WeatherData(
            timestamp=datetime.combine(tomorrow, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,  # Clear
            description="Clear",
        )

        forecast_rain = DailyForecastData(date=today, weather_data=rain_weather)
        forecast_clear = DailyForecastData(date=tomorrow, weather_data=clear_weather)

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[forecast_rain, forecast_clear]
        )

        result = combined_forecast.get_precipitation_days()
        assert len(result) == 1
        assert result[0] == forecast_rain

    def test_get_status_summary(self):
        """Test get_status_summary method."""
        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        # Test all status types
        status_tests = [
            (
                CombinedDataStatus.COMPLETE,
                "Complete weather and astronomy data available",
            ),
            (
                CombinedDataStatus.WEATHER_ONLY,
                "Weather data available, astronomy data unavailable",
            ),
            (
                CombinedDataStatus.ASTRONOMY_ONLY,
                "Astronomy data available, weather data unavailable",
            ),
            (
                CombinedDataStatus.PARTIAL_FAILURE,
                "Partial data available with some failures",
            ),
            (CombinedDataStatus.COMPLETE_FAILURE, "No forecast data available"),
        ]

        for status, expected_message in status_tests:
            combined_forecast = CombinedForecastData(
                location=location, daily_forecasts=[daily_forecast], status=status
            )
            assert combined_forecast.get_status_summary() == expected_message

    def test_get_error_summary_no_errors(self):
        """Test get_error_summary method with no errors."""
        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast], error_messages=[]
        )

        assert combined_forecast.get_error_summary() == "No errors"

    def test_get_error_summary_with_errors(self):
        """Test get_error_summary method with errors."""
        location = WeatherLocation("Test", 0.0, 0.0)
        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            error_messages=["Weather API error", "Astronomy API timeout"],
        )

        assert (
            combined_forecast.get_error_summary()
            == "Weather API error; Astronomy API timeout"
        )


class TestCombinedForecastValidator:
    """Comprehensive tests for CombinedForecastValidator class."""

    def test_validate_daily_forecast_no_data(self):
        """Test validate_daily_forecast with no weather or astronomy data."""
        # Create a mock daily forecast with no data
        mock_forecast = MagicMock()
        mock_forecast.has_weather_data = False
        mock_forecast.has_astronomy_data = False

        assert not CombinedForecastValidator.validate_daily_forecast(mock_forecast)

    def test_validate_daily_forecast_weather_date_mismatch(self):
        """Test validate_daily_forecast with weather date mismatch."""
        test_date = date.today()
        wrong_date = test_date + timedelta(days=1)

        # Create a mock daily forecast with date mismatch
        mock_forecast = MagicMock()
        mock_forecast.has_weather_data = True
        mock_forecast.has_astronomy_data = False
        mock_forecast.date = test_date
        mock_forecast.weather_data.timestamp.date.return_value = wrong_date
        mock_forecast.astronomy_data = None

        assert not CombinedForecastValidator.validate_daily_forecast(mock_forecast)

    def test_validate_daily_forecast_astronomy_date_mismatch(self):
        """Test validate_daily_forecast with astronomy date mismatch."""
        test_date = date.today()
        wrong_date = test_date + timedelta(days=1)

        # Create a mock daily forecast with date mismatch
        mock_forecast = MagicMock()
        mock_forecast.has_weather_data = False
        mock_forecast.has_astronomy_data = True
        mock_forecast.date = test_date
        mock_forecast.weather_data = None
        mock_forecast.astronomy_data.date = wrong_date

        assert not CombinedForecastValidator.validate_daily_forecast(mock_forecast)

    def test_validate_daily_forecast_exception(self):
        """Test validate_daily_forecast with exception."""
        # Create a mock that raises an exception
        mock_forecast = MagicMock()
        mock_forecast.has_weather_data = True
        mock_forecast.weather_data.timestamp.date.side_effect = AttributeError(
            "Test error"
        )

        assert not CombinedForecastValidator.validate_daily_forecast(mock_forecast)

    def test_validate_location_consistency_valid(self):
        """Test validate_location_consistency with consistent locations."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        astronomy_location = AstronomyLocation("Test", 51.5074, -0.1278)
        astronomy_data = AstronomyData(date=date.today(), events=[])
        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=location,
            daily_forecasts=[daily_forecast],
            weather_forecast=weather_forecast,
            astronomy_forecast=astronomy_forecast,
        )

        assert CombinedForecastValidator.validate_location_consistency(
            combined_forecast
        )

    def test_validate_location_consistency_weather_mismatch(self):
        """Test validate_location_consistency with weather location mismatch."""
        base_location = WeatherLocation("Test", 51.5074, -0.1278)
        weather_location = WeatherLocation("Different", 52.0, -1.0)

        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        weather_forecast = WeatherForecastData(
            location=weather_location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=base_location,
            daily_forecasts=[daily_forecast],
            weather_forecast=weather_forecast,
        )

        assert not CombinedForecastValidator.validate_location_consistency(
            combined_forecast
        )

    def test_validate_location_consistency_astronomy_mismatch(self):
        """Test validate_location_consistency with astronomy location mismatch."""
        base_location = WeatherLocation("Test", 51.5074, -0.1278)
        astronomy_location = AstronomyLocation("Different", 52.0, -1.0)

        astronomy_data = AstronomyData(date=date.today(), events=[])
        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=base_location,
            daily_forecasts=[daily_forecast],
            astronomy_forecast=astronomy_forecast,
        )

        assert not CombinedForecastValidator.validate_location_consistency(
            combined_forecast
        )

    def test_validate_combined_forecast_valid(self):
        """Test validate_combined_forecast with valid data."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        daily_forecast = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )

        assert CombinedForecastValidator.validate_combined_forecast(combined_forecast)

    def test_validate_combined_forecast_empty_forecasts(self):
        """Test validate_combined_forecast with empty daily forecasts."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        # Create a mock with empty daily forecasts
        mock_forecast = MagicMock()
        mock_forecast.daily_forecasts = []

        assert not CombinedForecastValidator.validate_combined_forecast(mock_forecast)

    def test_validate_combined_forecast_invalid_daily(self):
        """Test validate_combined_forecast with invalid daily forecast."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        # Create a mock with invalid daily forecast
        mock_forecast = MagicMock()
        mock_daily = MagicMock()
        mock_daily.has_weather_data = False
        mock_daily.has_astronomy_data = False
        mock_forecast.daily_forecasts = [mock_daily]

        with patch.object(
            CombinedForecastValidator,
            "validate_location_consistency",
            return_value=True,
        ):
            assert not CombinedForecastValidator.validate_combined_forecast(
                mock_forecast
            )

    def test_validate_combined_forecast_unordered_dates(self):
        """Test validate_combined_forecast with unordered dates."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Create mock with unordered dates
        mock_forecast = MagicMock()
        mock_forecast.daily_forecasts = [MagicMock(), MagicMock()]
        mock_forecast.daily_forecasts[0].date = tomorrow
        mock_forecast.daily_forecasts[1].date = today  # Out of order

        with patch.object(
            CombinedForecastValidator,
            "validate_location_consistency",
            return_value=True,
        ):
            with patch.object(
                CombinedForecastValidator, "validate_daily_forecast", return_value=True
            ):
                assert not CombinedForecastValidator.validate_combined_forecast(
                    mock_forecast
                )

    def test_validate_combined_forecast_duplicate_dates(self):
        """Test validate_combined_forecast with duplicate dates."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        today = date.today()

        # Create mock with duplicate dates
        mock_forecast = MagicMock()
        mock_forecast.daily_forecasts = [MagicMock(), MagicMock()]
        mock_forecast.daily_forecasts[0].date = today
        mock_forecast.daily_forecasts[1].date = today  # Duplicate

        with patch.object(
            CombinedForecastValidator,
            "validate_location_consistency",
            return_value=True,
        ):
            with patch.object(
                CombinedForecastValidator, "validate_daily_forecast", return_value=True
            ):
                assert not CombinedForecastValidator.validate_combined_forecast(
                    mock_forecast
                )

    def test_validate_combined_forecast_exception(self):
        """Test validate_combined_forecast with exception."""
        # Create a mock that raises an exception
        mock_forecast = MagicMock()
        mock_forecast.daily_forecasts = None  # Will cause AttributeError

        assert not CombinedForecastValidator.validate_combined_forecast(mock_forecast)

    def test_additional_coverage_scenarios(self):
        """Test additional scenarios to improve coverage."""
        # Test DailyForecastData with no data (should raise ValueError)
        with pytest.raises(
            ValueError,
            match="Daily forecast must contain either weather or astronomy data",
        ):
            DailyForecastData(date=date.today())

        # Test properties when data exists
        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=25.0,
            humidity=60,
            weather_code=2,
            description="Partly cloudy",
        )

        astronomy_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test astronomy event",
            start_time=datetime.now(),
        )

        astronomy_data = AstronomyData(
            date=date.today(),
            events=[astronomy_event],
            primary_event=astronomy_event,  # Set primary event to cover that property
        )

        daily_forecast_with_data = DailyForecastData(
            date=date.today(), weather_data=weather_data, astronomy_data=astronomy_data
        )

        # Test properties that access data
        assert daily_forecast_with_data.has_complete_data
        assert daily_forecast_with_data.primary_astronomy_event is not None
        assert daily_forecast_with_data.astronomy_event_count > 0
        assert daily_forecast_with_data.weather_description == "Partly cloudy"
        assert daily_forecast_with_data.temperature_display == "25.0°C"
        assert (
            daily_forecast_with_data.moon_phase_icon == "🌑"
        )  # Default from astronomy_data

        # Test get_astronomy_events_by_type with data
        events = daily_forecast_with_data.get_astronomy_events_by_type(
            AstronomyEventType.APOD
        )
        assert len(events) == 1

        # Test get_display_summary with data
        summary = daily_forecast_with_data.get_display_summary()
        assert "25.0°C" in summary
        assert "Partly cloudy" in summary
        assert "astronomy event" in summary

    def test_combined_forecast_validation_errors(self):
        """Test CombinedForecastData validation errors."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        # Test chronological order validation
        daily_forecast1 = DailyForecastData(
            date=date.today() + timedelta(days=1),
            weather_data=WeatherData(
                timestamp=datetime.now() + timedelta(days=1),
                temperature=20.0,
                humidity=50,
                weather_code=1,
                description="Clear",
            ),
        )
        daily_forecast2 = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=22.0,
                humidity=55,
                weather_code=1,
                description="Clear",
            ),
        )

        with pytest.raises(
            ValueError, match="Daily forecasts must be in chronological order"
        ):
            CombinedForecastData(
                location=location,
                daily_forecasts=[daily_forecast1, daily_forecast2],  # Wrong order
            )

        # Test duplicate dates validation
        daily_forecast_dup = DailyForecastData(
            date=date.today(),
            weather_data=WeatherData(
                timestamp=datetime.now(),
                temperature=25.0,
                humidity=60,
                weather_code=2,
                description="Cloudy",
            ),
        )

        with pytest.raises(
            ValueError, match="Daily forecasts cannot contain duplicate dates"
        ):
            CombinedForecastData(
                location=location,
                daily_forecasts=[daily_forecast2, daily_forecast_dup],  # Same date
            )

        # Test forecast length validation (more than 14 days)
        long_forecasts = []
        for i in range(15):  # 15 days
            forecast_date = date.today() + timedelta(days=i)
            daily_forecast = DailyForecastData(
                date=forecast_date,
                weather_data=WeatherData(
                    timestamp=datetime.now() + timedelta(days=i),
                    temperature=20.0,
                    humidity=50,
                    weather_code=1,
                    description="Clear",
                ),
            )
            long_forecasts.append(daily_forecast)

        with pytest.raises(ValueError, match="Combined forecast cannot exceed 14 days"):
            CombinedForecastData(location=location, daily_forecasts=long_forecasts)

    def test_combined_forecast_properties(self):
        """Test CombinedForecastData properties for coverage."""
        location = WeatherLocation("Test", 51.5074, -0.1278)

        # Create forecast with astronomy events
        astronomy_data = AstronomyData(
            date=date.today(),
            events=[
                AstronomyEvent(
                    event_type=AstronomyEventType.APOD,
                    title="Test Event 1",
                    description="Test astronomy event 1",
                    start_time=datetime.now(),
                ),
                AstronomyEvent(
                    event_type=AstronomyEventType.ISS_PASS,
                    title="Test Event 2",
                    description="Test astronomy event 2",
                    start_time=datetime.now(),
                ),
            ],
        )

        daily_forecast = DailyForecastData(
            date=date.today(),
            astronomy_data=astronomy_data,
            data_quality=ForecastDataQuality.EXCELLENT,
        )

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )

        # Test forecast_days property
        assert combined_forecast.forecast_days == 1

        # Test total_astronomy_events property
        assert combined_forecast.total_astronomy_events == 2

        # Test data_quality_summary property
        quality_summary = combined_forecast.data_quality_summary
        assert quality_summary[ForecastDataQuality.EXCELLENT] == 1
        assert quality_summary[ForecastDataQuality.GOOD] == 0
        assert quality_summary[ForecastDataQuality.PARTIAL] == 0
        assert quality_summary[ForecastDataQuality.POOR] == 0

    def test_validator_location_consistency_failure(self):
        """Test validator location consistency failure."""
        base_location = WeatherLocation("Test", 51.5074, -0.1278)
        different_location = WeatherLocation("Different", 52.0, -1.0)

        # Create valid data for the forecasts
        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )
        weather_forecast = WeatherForecastData(
            location=different_location,  # Different location
            daily_forecast=[weather_data],
            hourly_forecast=[],
        )

        daily_forecast = DailyForecastData(date=date.today(), weather_data=weather_data)

        combined_forecast = CombinedForecastData(
            location=base_location,
            daily_forecasts=[daily_forecast],
            weather_forecast=weather_forecast,
        )

        # This should return False due to location mismatch
        assert not CombinedForecastValidator.validate_location_consistency(
            combined_forecast
        )

    def test_validator_location_consistency_astronomy_failure(self):
        """Test validator location consistency failure with astronomy data."""
        base_location = WeatherLocation("Test", 51.5074, -0.1278)
        different_astronomy_location = AstronomyLocation("Different", 52.0, -1.0)

        # Create valid astronomy data
        astronomy_data = AstronomyData(date=date.today(), events=[])
        astronomy_forecast = AstronomyForecastData(
            location=different_astronomy_location,  # Different location
            daily_astronomy=[astronomy_data],
        )

        daily_forecast = DailyForecastData(
            date=date.today(), astronomy_data=astronomy_data
        )

        combined_forecast = CombinedForecastData(
            location=base_location,
            daily_forecasts=[daily_forecast],
            astronomy_forecast=astronomy_forecast,
        )

        # This should return False due to astronomy location mismatch (line 479)
        assert not CombinedForecastValidator.validate_location_consistency(
            combined_forecast
        )

    def test_validator_exception_handling(self):
        """Test validator exception handling."""
        # Test with invalid object that will cause AttributeError
        invalid_forecast = (
            None  # This will cause AttributeError when accessing attributes
        )

        # This should return False due to exception handling
        assert not CombinedForecastValidator.validate_combined_forecast(invalid_forecast)  # type: ignore


class TestFactoryFunctions:
    """Test factory functions for creating combined forecasts."""

    def test_create_weather_only_forecast(self):
        """Test create_weather_only_forecast function."""
        location = WeatherLocation("Test", 0.0, 0.0)

        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        result = create_weather_only_forecast(location, weather_forecast)

        assert result.location == location
        assert result.weather_forecast == weather_forecast
        assert result.astronomy_forecast is None

    def test_create_astronomy_only_forecast(self):
        """Test create_astronomy_only_forecast function."""
        location = WeatherLocation("Test", 0.0, 0.0)
        astronomy_location = AstronomyLocation("Test", 0.0, 0.0)

        astronomy_data = AstronomyData(date=date.today(), events=[])

        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        result = create_astronomy_only_forecast(location, astronomy_forecast)

        assert result.location == location
        assert result.weather_forecast is None
        assert result.astronomy_forecast == astronomy_forecast

    def test_create_complete_forecast(self):
        """Test create_complete_forecast function."""
        location = WeatherLocation("Test", 0.0, 0.0)
        astronomy_location = AstronomyLocation("Test", 0.0, 0.0)

        weather_data = WeatherData(
            timestamp=datetime.now(),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        weather_forecast = WeatherForecastData(
            location=location, daily_forecast=[weather_data], hourly_forecast=[]
        )

        astronomy_data = AstronomyData(date=date.today(), events=[])

        astronomy_forecast = AstronomyForecastData(
            location=astronomy_location, daily_astronomy=[astronomy_data]
        )

        result = create_complete_forecast(
            location, weather_forecast, astronomy_forecast
        )

        assert result.location == location
        assert result.weather_forecast == weather_forecast
        assert result.astronomy_forecast == astronomy_forecast
