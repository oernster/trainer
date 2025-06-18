"""
Simple working tests for combined forecast data models.
"""

import pytest
from datetime import datetime, date, timedelta

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
from src.models.weather_data import Location, WeatherData, WeatherForecastData
from src.models.astronomy_data import (
    AstronomyData,
    AstronomyForecastData,
    AstronomyEvent,
    AstronomyEventType,
)


class TestDailyForecastDataBasic:
    """Basic test cases for DailyForecastData model."""

    def test_daily_forecast_creation_minimal(self):
        """Test minimal daily forecast creation."""
        test_date = date.today()

        # Create minimal weather data
        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        assert daily_forecast.date == test_date
        assert daily_forecast.weather_data == weather_data
        assert daily_forecast.has_weather_data
        assert not daily_forecast.has_astronomy_data

    def test_daily_forecast_with_astronomy(self):
        """Test daily forecast with astronomy data."""
        test_date = date.today()

        # Create astronomy data
        astronomy_data = AstronomyData(date=test_date, events=[])

        daily_forecast = DailyForecastData(
            date=test_date, astronomy_data=astronomy_data
        )

        assert daily_forecast.has_astronomy_data
        assert not daily_forecast.has_weather_data

    def test_daily_forecast_validation_no_data(self):
        """Test daily forecast validation with no data."""
        test_date = date.today()

        with pytest.raises(
            ValueError,
            match="Daily forecast must contain either weather or astronomy data",
        ):
            DailyForecastData(date=test_date)


class TestCombinedForecastDataBasic:
    """Basic test cases for CombinedForecastData model."""

    def test_combined_forecast_creation_minimal(self):
        """Test minimal combined forecast creation."""
        location = Location("Test Location", 51.5074, -0.1278)
        test_date = date.today()

        # Create minimal daily forecast
        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )

        assert combined_forecast.location == location
        assert len(combined_forecast.daily_forecasts) == 1
        assert combined_forecast.forecast_days == 1

    def test_combined_forecast_factory_weather_only(self):
        """Test creating weather-only forecast."""
        location = Location("Test Location", 51.5074, -0.1278)

        # Create minimal weather forecast with some data
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

        combined_forecast = create_weather_only_forecast(location, weather_forecast)

        assert combined_forecast.location == location
        assert combined_forecast.weather_forecast == weather_forecast
        assert combined_forecast.astronomy_forecast is None

    def test_combined_forecast_validation_empty_forecasts(self):
        """Test combined forecast validation with empty forecasts."""
        location = Location("Test Location", 51.5074, -0.1278)

        with pytest.raises(
            ValueError,
            match="Combined forecast must contain at least one daily forecast",
        ):
            CombinedForecastData(location=location, daily_forecasts=[])


class TestCombinedDataStatusBasic:
    """Basic test cases for CombinedDataStatus enum."""

    def test_combined_data_status_values(self):
        """Test combined data status enum values."""
        assert CombinedDataStatus.COMPLETE.value == "complete"
        assert CombinedDataStatus.WEATHER_ONLY.value == "weather_only"
        assert CombinedDataStatus.ASTRONOMY_ONLY.value == "astronomy_only"
        assert CombinedDataStatus.PARTIAL_FAILURE.value == "partial_failure"
        assert CombinedDataStatus.COMPLETE_FAILURE.value == "complete_failure"


class TestForecastDataQualityBasic:
    """Basic test cases for ForecastDataQuality enum."""

    def test_forecast_data_quality_values(self):
        """Test forecast data quality enum values."""
        assert ForecastDataQuality.EXCELLENT.value == "excellent"
        assert ForecastDataQuality.GOOD.value == "good"
        assert ForecastDataQuality.PARTIAL.value == "partial"
        assert ForecastDataQuality.POOR.value == "poor"


class TestCombinedForecastValidatorBasic:
    """Basic test cases for CombinedForecastValidator."""

    def test_validate_daily_forecast(self):
        """Test daily forecast validation."""
        validator = CombinedForecastValidator()
        test_date = date.today()

        # Valid daily forecast
        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        assert validator.validate_daily_forecast(daily_forecast)

    def test_validate_combined_forecast(self):
        """Test combined forecast validation."""
        validator = CombinedForecastValidator()
        location = Location("Test Location", 51.5074, -0.1278)
        test_date = date.today()

        # Create valid combined forecast
        weather_data = WeatherData(
            timestamp=datetime.combine(test_date, datetime.min.time()),
            temperature=20.0,
            humidity=50,
            weather_code=1,
            description="Clear",
        )

        daily_forecast = DailyForecastData(date=test_date, weather_data=weather_data)

        combined_forecast = CombinedForecastData(
            location=location, daily_forecasts=[daily_forecast]
        )

        assert validator.validate_combined_forecast(combined_forecast)
