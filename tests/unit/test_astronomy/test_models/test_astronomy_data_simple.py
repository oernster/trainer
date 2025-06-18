"""
Simple working tests for astronomy data models.
"""

import pytest
from datetime import datetime, date, timedelta

from src.models.astronomy_data import (
    AstronomyEvent,
    AstronomyData,
    AstronomyForecastData,
    AstronomyEventType,
    AstronomyEventPriority,
    MoonPhase,
    Location,
    AstronomyDataValidator,
    EmojiAstronomyIconStrategy,
    AstronomyIconProviderImpl,
    default_astronomy_icon_provider,
)


class TestAstronomyEventBasic:
    """Basic test cases for AstronomyEvent model."""

    def test_astronomy_event_creation_minimal(self):
        """Test minimal astronomy event creation."""
        start_time = datetime.now()

        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=start_time,
        )

        assert event.event_type == AstronomyEventType.APOD
        assert event.title == "Test Event"
        assert event.description == "Test Description"
        assert event.start_time == start_time

    def test_astronomy_event_validation_empty_title(self):
        """Test astronomy event validation with empty title."""
        with pytest.raises(ValueError, match="Event title cannot be empty"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="",
                description="Test Description",
                start_time=datetime.now(),
            )

    def test_astronomy_event_icon_property(self):
        """Test astronomy event icon property."""
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(),
        )

        assert event.event_icon == "📸"


class TestAstronomyDataBasic:
    """Basic test cases for AstronomyData model."""

    def test_astronomy_data_creation_minimal(self):
        """Test minimal astronomy data creation."""
        test_date = date.today()

        astronomy_data = AstronomyData(date=test_date, events=[])

        assert astronomy_data.date == test_date
        assert astronomy_data.events == []

    def test_astronomy_data_with_events(self):
        """Test astronomy data with events."""
        test_date = date.today()
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.combine(test_date, datetime.min.time()),
        )

        astronomy_data = AstronomyData(date=test_date, events=[event])

        assert astronomy_data.has_events
        assert astronomy_data.event_count == 1


class TestLocationBasic:
    """Basic test cases for Location model."""

    def test_location_creation_minimal(self):
        """Test minimal location creation."""
        location = Location(name="Test Location", latitude=51.5074, longitude=-0.1278)

        assert location.name == "Test Location"
        assert location.latitude == 51.5074
        assert location.longitude == -0.1278

    def test_location_validation_invalid_latitude(self):
        """Test location validation with invalid latitude."""
        with pytest.raises(ValueError, match="Invalid latitude"):
            Location(name="Test", latitude=91.0, longitude=0.0)


class TestAstronomyDataValidatorBasic:
    """Basic test cases for AstronomyDataValidator."""

    def test_validate_event_type(self):
        """Test event type validation."""
        validator = AstronomyDataValidator()

        assert validator.validate_event_type(AstronomyEventType.APOD)
        assert not validator.validate_event_type("invalid")  # type: ignore

    def test_validate_location(self):
        """Test location validation."""
        validator = AstronomyDataValidator()

        valid_location = Location("Test", 0.0, 0.0)
        assert validator.validate_location(valid_location)


class TestEmojiAstronomyIconStrategyBasic:
    """Basic test cases for EmojiAstronomyIconStrategy."""

    def test_get_icon(self):
        """Test getting icons for different event types."""
        strategy = EmojiAstronomyIconStrategy()

        assert strategy.get_icon(AstronomyEventType.APOD) == "📸"
        assert strategy.get_icon(AstronomyEventType.ISS_PASS) == "🛰️"
        assert strategy.get_icon(AstronomyEventType.UNKNOWN) == "❓"

    def test_get_strategy_name(self):
        """Test getting strategy name."""
        strategy = EmojiAstronomyIconStrategy()
        assert strategy.get_strategy_name() == "emoji"


def test_default_astronomy_icon_provider():
    """Test default astronomy icon provider instance."""
    assert default_astronomy_icon_provider is not None
    assert isinstance(default_astronomy_icon_provider, AstronomyIconProviderImpl)
    assert default_astronomy_icon_provider.get_current_strategy_name() == "emoji"
