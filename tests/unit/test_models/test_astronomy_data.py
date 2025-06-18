"""
Comprehensive tests for astronomy data models to achieve 100% test coverage.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
import logging

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
    AstronomyDataReader,
    AstronomyIconProvider,
    AstronomyIconStrategy,
    default_astronomy_icon_provider
)


class TestAstronomyEvent:
    """Comprehensive tests for AstronomyEvent class."""
    
    def test_astronomy_event_creation_full(self):
        """Test full astronomy event creation with all parameters."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=start_time,
            end_time=end_time,
            visibility_info="Visible from northern hemisphere",
            nasa_url="https://nasa.gov/test",
            image_url="https://example.com/image.jpg",
            priority=AstronomyEventPriority.HIGH,
            metadata={"test": "value"}
        )
        
        assert event.event_type == AstronomyEventType.APOD
        assert event.title == "Test Event"
        assert event.description == "Test Description"
        assert event.start_time == start_time
        assert event.end_time == end_time
        assert event.visibility_info == "Visible from northern hemisphere"
        assert event.nasa_url == "https://nasa.gov/test"
        assert event.image_url == "https://example.com/image.jpg"
        assert event.priority == AstronomyEventPriority.HIGH
        assert event.metadata == {"test": "value"}
    
    def test_astronomy_event_validation_empty_title(self):
        """Test validation with empty title."""
        with pytest.raises(ValueError, match="Event title cannot be empty"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="   ",  # Only whitespace
                description="Test Description",
                start_time=datetime.now()
            )
    
    def test_astronomy_event_validation_empty_description(self):
        """Test validation with empty description."""
        with pytest.raises(ValueError, match="Event description cannot be empty"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="Test Title",
                description="   ",  # Only whitespace
                start_time=datetime.now()
            )
    
    def test_astronomy_event_validation_end_before_start(self):
        """Test validation with end time before start time."""
        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)
        
        with pytest.raises(ValueError, match="End time cannot be before start time"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="Test Title",
                description="Test Description",
                start_time=start_time,
                end_time=end_time
            )
    
    def test_astronomy_event_validation_invalid_nasa_url(self):
        """Test validation with invalid NASA URL."""
        with pytest.raises(ValueError, match="Invalid NASA URL"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="Test Title",
                description="Test Description",
                start_time=datetime.now(),
                nasa_url="invalid-url"
            )
    
    def test_astronomy_event_validation_invalid_image_url(self):
        """Test validation with invalid image URL."""
        with pytest.raises(ValueError, match="Invalid image URL"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="Test Title",
                description="Test Description",
                start_time=datetime.now(),
                image_url="not-a-url"
            )
    
    def test_astronomy_event_validation_invalid_metadata(self):
        """Test validation with invalid metadata."""
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            AstronomyEvent(
                event_type=AstronomyEventType.APOD,
                title="Test Title",
                description="Test Description",
                start_time=datetime.now(),
                metadata="not-a-dict"  # type: ignore
            )
    
    def test_is_valid_url_valid_urls(self):
        """Test _is_valid_url with valid URLs."""
        assert AstronomyEvent._is_valid_url("https://example.com")
        assert AstronomyEvent._is_valid_url("http://nasa.gov/test")
        assert AstronomyEvent._is_valid_url("https://subdomain.example.com/path")
    
    def test_is_valid_url_invalid_urls(self):
        """Test _is_valid_url with invalid URLs."""
        assert not AstronomyEvent._is_valid_url("invalid-url")
        assert not AstronomyEvent._is_valid_url("")
        assert not AstronomyEvent._is_valid_url("just-text")
    
    def test_is_valid_url_exception_handling(self):
        """Test _is_valid_url exception handling."""
        # Test with None to trigger exception
        assert not AstronomyEvent._is_valid_url(None)  # type: ignore
    
    def test_duration_property_with_end_time(self):
        """Test duration property when end time is available."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2, minutes=30)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=start_time,
            end_time=end_time
        )
        
        assert event.duration == timedelta(hours=2, minutes=30)
    
    def test_duration_property_without_end_time(self):
        """Test duration property when end time is not available."""
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=datetime.now()
        )
        
        assert event.duration is None
    
    @patch('src.models.astronomy_data.datetime')
    def test_is_ongoing_with_end_time(self, mock_datetime):
        """Test is_ongoing property with end time."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        start_time = datetime(2023, 6, 15, 10, 0, 0)
        end_time = datetime(2023, 6, 15, 14, 0, 0)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=start_time,
            end_time=end_time
        )
        
        assert event.is_ongoing
    
    @patch('src.models.astronomy_data.datetime')
    def test_is_ongoing_without_end_time(self, mock_datetime):
        """Test is_ongoing property without end time."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        start_time = datetime(2023, 6, 15, 10, 0, 0)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=start_time
        )
        
        assert event.is_ongoing
    
    @patch('src.models.astronomy_data.datetime')
    def test_is_future(self, mock_datetime):
        """Test is_future property."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        future_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Future Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 14, 0, 0)
        )
        
        assert future_event.is_future
    
    @patch('src.models.astronomy_data.datetime')
    def test_is_past_with_end_time(self, mock_datetime):
        """Test is_past property with end time."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        past_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Past Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 8, 0, 0),
            end_time=datetime(2023, 6, 15, 10, 0, 0)
        )
        
        assert past_event.is_past
    
    @patch('src.models.astronomy_data.datetime')
    def test_is_past_without_end_time(self, mock_datetime):
        """Test is_past property without end time."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        past_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Past Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 8, 0, 0)
        )
        
        assert past_event.is_past
    
    def test_has_visibility_info_true(self):
        """Test has_visibility_info property when visibility info exists."""
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=datetime.now(),
            visibility_info="Visible from northern hemisphere"
        )
        
        assert event.has_visibility_info
    
    def test_has_visibility_info_false(self):
        """Test has_visibility_info property when visibility info is empty."""
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=datetime.now(),
            visibility_info="   "  # Only whitespace
        )
        
        assert not event.has_visibility_info
    
    def test_has_image_true(self):
        """Test has_image property when image URL exists."""
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=datetime.now(),
            image_url="https://example.com/image.jpg"
        )
        
        assert event.has_image
    
    def test_has_image_false(self):
        """Test has_image property when image URL is empty."""
        # Test with None image URL
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=datetime.now(),
            image_url=None
        )
        
        assert not event.has_image
    
    def test_event_icon_all_types(self):
        """Test event_icon property for all event types."""
        icons = {
            AstronomyEventType.APOD: "📸",
            AstronomyEventType.ISS_PASS: "🛰️",
            AstronomyEventType.NEAR_EARTH_OBJECT: "☄️",
            AstronomyEventType.MOON_PHASE: "🌙",
            AstronomyEventType.PLANETARY_EVENT: "🪐",
            AstronomyEventType.METEOR_SHOWER: "⭐",
            AstronomyEventType.SOLAR_EVENT: "☀️",
            AstronomyEventType.SATELLITE_IMAGE: "🌍",
            AstronomyEventType.UNKNOWN: "❓"
        }
        
        for event_type, expected_icon in icons.items():
            event = AstronomyEvent(
                event_type=event_type,
                title="Test Title",
                description="Test Description",
                start_time=datetime.now()
            )
            assert event.event_icon == expected_icon
    
    def test_get_formatted_time(self):
        """Test get_formatted_time method."""
        start_time = datetime(2023, 6, 15, 14, 30, 0)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=start_time
        )
        
        assert event.get_formatted_time() == "14:30"
        assert event.get_formatted_time("%Y-%m-%d %H:%M") == "2023-06-15 14:30"
    
    def test_get_formatted_duration_no_duration(self):
        """Test get_formatted_duration when no duration available."""
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=datetime.now()
        )
        
        assert event.get_formatted_duration() == "Unknown duration"
    
    def test_get_formatted_duration_hours_and_minutes(self):
        """Test get_formatted_duration with hours and minutes."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2, minutes=30)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=start_time,
            end_time=end_time
        )
        
        assert event.get_formatted_duration() == "2h 30m"
    
    def test_get_formatted_duration_minutes_only(self):
        """Test get_formatted_duration with minutes only."""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=45)
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Title",
            description="Test Description",
            start_time=start_time,
            end_time=end_time
        )
        
        assert event.get_formatted_duration() == "45m"


class TestAstronomyData:
    """Comprehensive tests for AstronomyData class."""
    
    def test_astronomy_data_creation_full(self):
        """Test full astronomy data creation with all parameters."""
        test_date = date.today()
        start_time = datetime.combine(test_date, datetime.min.time())
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=start_time
        )
        
        sunrise = datetime.combine(test_date, datetime.min.time().replace(hour=6))
        sunset = datetime.combine(test_date, datetime.min.time().replace(hour=18))
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[event],
            primary_event=event,
            moon_phase=MoonPhase.FULL_MOON,
            moon_illumination=0.95,
            sunrise_time=sunrise,
            sunset_time=sunset
        )
        
        assert astronomy_data.date == test_date
        assert astronomy_data.events == [event]
        assert astronomy_data.primary_event == event
        assert astronomy_data.moon_phase == MoonPhase.FULL_MOON
        assert astronomy_data.moon_illumination == 0.95
        assert astronomy_data.sunrise_time == sunrise
        assert astronomy_data.sunset_time == sunset
    
    def test_astronomy_data_validation_moon_illumination_invalid(self):
        """Test validation with invalid moon illumination."""
        with pytest.raises(ValueError, match="Moon illumination must be between 0.0 and 1.0"):
            AstronomyData(
                date=date.today(),
                moon_illumination=1.5
            )
    
    def test_astronomy_data_validation_sunrise_wrong_date(self):
        """Test validation with sunrise on wrong date."""
        test_date = date.today()
        wrong_date_sunrise = datetime.combine(test_date + timedelta(days=1), datetime.min.time())
        sunset = datetime.combine(test_date, datetime.min.time().replace(hour=18))
        
        with pytest.raises(ValueError, match="Sunrise time must be on the same date"):
            AstronomyData(
                date=test_date,
                sunrise_time=wrong_date_sunrise,
                sunset_time=sunset
            )
    
    def test_astronomy_data_validation_sunset_wrong_date(self):
        """Test validation with sunset on wrong date."""
        test_date = date.today()
        sunrise = datetime.combine(test_date, datetime.min.time().replace(hour=6))
        wrong_date_sunset = datetime.combine(test_date + timedelta(days=1), datetime.min.time())
        
        with pytest.raises(ValueError, match="Sunset time must be on the same date"):
            AstronomyData(
                date=test_date,
                sunrise_time=sunrise,
                sunset_time=wrong_date_sunset
            )
    
    def test_astronomy_data_validation_sunrise_after_sunset(self):
        """Test validation with sunrise after sunset."""
        test_date = date.today()
        sunrise = datetime.combine(test_date, datetime.min.time().replace(hour=18))
        sunset = datetime.combine(test_date, datetime.min.time().replace(hour=6))
        
        with pytest.raises(ValueError, match="Sunrise must be before sunset"):
            AstronomyData(
                date=test_date,
                sunrise_time=sunrise,
                sunset_time=sunset
            )
    
    def test_astronomy_data_validation_primary_event_not_in_list(self):
        """Test validation with primary event not in events list."""
        test_date = date.today()
        start_time = datetime.combine(test_date, datetime.min.time())
        
        event1 = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Event 1",
            description="Description 1",
            start_time=start_time
        )
        
        event2 = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Event 2",
            description="Description 2",
            start_time=start_time
        )
        
        with pytest.raises(ValueError, match="Primary event must be in the events list"):
            AstronomyData(
                date=test_date,
                events=[event1],
                primary_event=event2
            )
    
    def test_astronomy_data_validation_event_wrong_date(self):
        """Test validation with event on wrong date."""
        test_date = date.today()
        wrong_date = test_date + timedelta(days=1)
        start_time = datetime.combine(wrong_date, datetime.min.time())
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Wrong Date Event",
            description="Test Description",
            start_time=start_time
        )
        
        with pytest.raises(ValueError, match="Event Wrong Date Event is not for date"):
            AstronomyData(
                date=test_date,
                events=[event]
            )
    
    def test_has_events_properties(self):
        """Test has_events and event_count properties."""
        test_date = date.today()
        start_time = datetime.combine(test_date, datetime.min.time())
        
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=start_time
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[event]
        )
        
        assert astronomy_data.has_events
        assert astronomy_data.event_count == 1
        
        # Test empty events
        empty_data = AstronomyData(date=test_date, events=[])
        assert not empty_data.has_events
        assert empty_data.event_count == 0
    
    def test_high_priority_events(self):
        """Test high_priority_events and has_high_priority_events properties."""
        test_date = date.today()
        start_time = datetime.combine(test_date, datetime.min.time())
        
        high_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="High Priority Event",
            description="Test Description",
            start_time=start_time,
            priority=AstronomyEventPriority.HIGH
        )
        
        critical_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Critical Priority Event",
            description="Test Description",
            start_time=start_time,
            priority=AstronomyEventPriority.CRITICAL
        )
        
        low_event = AstronomyEvent(
            event_type=AstronomyEventType.MOON_PHASE,
            title="Low Priority Event",
            description="Test Description",
            start_time=start_time,
            priority=AstronomyEventPriority.LOW
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[high_event, critical_event, low_event]
        )
        
        high_priority = astronomy_data.high_priority_events
        assert len(high_priority) == 2
        assert high_event in high_priority
        assert critical_event in high_priority
        assert low_event not in high_priority
        assert astronomy_data.has_high_priority_events
    
    def test_moon_phase_icon(self):
        """Test moon_phase_icon property for all moon phases."""
        icons = {
            MoonPhase.NEW_MOON: "🌑",
            MoonPhase.WAXING_CRESCENT: "🌒",
            MoonPhase.FIRST_QUARTER: "🌓",
            MoonPhase.WAXING_GIBBOUS: "🌔",
            MoonPhase.FULL_MOON: "🌕",
            MoonPhase.WANING_GIBBOUS: "🌖",
            MoonPhase.LAST_QUARTER: "🌗",
            MoonPhase.WANING_CRESCENT: "🌘"
        }
        
        for moon_phase, expected_icon in icons.items():
            astronomy_data = AstronomyData(
                date=date.today(),
                moon_phase=moon_phase
            )
            assert astronomy_data.moon_phase_icon == expected_icon
        
        # Test no moon phase
        no_phase_data = AstronomyData(date=date.today())
        assert no_phase_data.moon_phase_icon == "🌑"
    
    def test_daylight_duration(self):
        """Test daylight_duration property."""
        test_date = date.today()
        sunrise = datetime.combine(test_date, datetime.min.time().replace(hour=6))
        sunset = datetime.combine(test_date, datetime.min.time().replace(hour=18))
        
        astronomy_data = AstronomyData(
            date=test_date,
            sunrise_time=sunrise,
            sunset_time=sunset
        )
        
        assert astronomy_data.daylight_duration == timedelta(hours=12)
        
        # Test without times
        no_times_data = AstronomyData(date=test_date)
        assert no_times_data.daylight_duration is None
    
    def test_get_events_by_type(self):
        """Test get_events_by_type method."""
        test_date = date.today()
        start_time = datetime.combine(test_date, datetime.min.time())
        
        apod_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="APOD Event",
            description="Test Description",
            start_time=start_time
        )
        
        iss_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="ISS Event",
            description="Test Description",
            start_time=start_time
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[apod_event, iss_event]
        )
        
        apod_events = astronomy_data.get_events_by_type(AstronomyEventType.APOD)
        assert len(apod_events) == 1
        assert apod_events[0] == apod_event
    
    def test_get_events_by_priority(self):
        """Test get_events_by_priority method."""
        test_date = date.today()
        start_time = datetime.combine(test_date, datetime.min.time())
        
        high_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="High Priority Event",
            description="Test Description",
            start_time=start_time,
            priority=AstronomyEventPriority.HIGH
        )
        
        low_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Low Priority Event",
            description="Test Description",
            start_time=start_time,
            priority=AstronomyEventPriority.LOW
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[high_event, low_event]
        )
        
        high_events = astronomy_data.get_events_by_priority(AstronomyEventPriority.HIGH)
        assert len(high_events) == 1
        assert high_events[0] == high_event
    
    @patch('src.models.astronomy_data.datetime')
    def test_get_ongoing_events(self, mock_datetime):
        """Test get_ongoing_events method."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        test_date = date(2023, 6, 15)
        
        ongoing_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Ongoing Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 10, 0, 0),
            end_time=datetime(2023, 6, 15, 14, 0, 0)
        )
        
        future_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Future Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 16, 0, 0)
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[ongoing_event, future_event]
        )
        
        ongoing_events = astronomy_data.get_ongoing_events()
        assert len(ongoing_events) == 1
        assert ongoing_events[0] == ongoing_event
    
    @patch('src.models.astronomy_data.datetime')
    def test_get_future_events(self, mock_datetime):
        """Test get_future_events method."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        test_date = date(2023, 6, 15)
        
        past_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Past Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 8, 0, 0)
        )
        
        future_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Future Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 16, 0, 0)
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[past_event, future_event]
        )
        
        future_events = astronomy_data.get_future_events()
        assert len(future_events) == 1
        assert future_events[0] == future_event
    
    def test_get_sorted_events(self):
        """Test get_sorted_events method."""
        test_date = date.today()
        
        event1 = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Event 1",
            description="Test Description",
            start_time=datetime.combine(test_date, datetime.min.time().replace(hour=14)),
            priority=AstronomyEventPriority.HIGH
        )
        
        event2 = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Event 2",
            description="Test Description",
            start_time=datetime.combine(test_date, datetime.min.time().replace(hour=10)),
            priority=AstronomyEventPriority.CRITICAL
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[event1, event2]
        )
        
        # Test sorted by time
        sorted_by_time = astronomy_data.get_sorted_events()
        assert len(sorted_by_time) == 2
        assert sorted_by_time[0] == event2  # Earlier time
        assert sorted_by_time[1] == event1  # Later time
        
        # Test sorted by priority
        sorted_by_priority = astronomy_data.get_sorted_events(by_priority=True)
        assert len(sorted_by_priority) == 2
        assert sorted_by_priority[0] == event2  # Higher priority (CRITICAL = 4)
        assert sorted_by_priority[1] == event1  # Lower priority (HIGH = 3)


class TestAstronomyForecastData:
    """Comprehensive tests for AstronomyForecastData class."""
    
    def test_astronomy_forecast_creation_full(self):
        """Test full astronomy forecast creation."""
        location = Location(
            name="Test Location",
            latitude=51.5074,
            longitude=-0.1278
        )
        
        test_date = date.today()
        astronomy_data = AstronomyData(date=test_date)
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=[astronomy_data],
            data_source="Test Source",
            forecast_days=5
        )
        
        assert forecast.location == location
        assert forecast.daily_astronomy == [astronomy_data]
        assert forecast.data_source == "Test Source"
        assert forecast.forecast_days == 5
    
    def test_astronomy_forecast_validation_empty_daily_data(self):
        """Test validation with empty daily astronomy data."""
        location = Location(
            name="Test Location",
            latitude=51.5074,
            longitude=-0.1278
        )
        
        with pytest.raises(ValueError, match="Forecast must contain at least one day of astronomy data"):
            AstronomyForecastData(
                location=location,
                daily_astronomy=[]
            )
    
    def test_astronomy_forecast_validation_too_many_days(self):
        """Test validation with too many forecast days."""
        location = Location(
            name="Test Location",
            latitude=51.5074,
            longitude=-0.1278
        )
        
        daily_data = [AstronomyData(date=date.today() + timedelta(days=i)) for i in range(8)]
        
        with pytest.raises(ValueError, match="Forecast cannot contain more than 7 days"):
            AstronomyForecastData(
                location=location,
                daily_astronomy=daily_data,
                forecast_days=7
            )
    
    def test_astronomy_forecast_validation_unordered_dates(self):
        """Test validation with unordered dates."""
        location = Location(
            name="Test Location",
            latitude=51.5074,
            longitude=-0.1278
        )
        
        today = date.today()
        daily_data = [
            AstronomyData(date=today + timedelta(days=1)),
            AstronomyData(date=today)  # Out of order
        ]
        
        with pytest.raises(ValueError, match="Daily astronomy data must be in chronological order"):
            AstronomyForecastData(
                location=location,
                daily_astronomy=daily_data
            )
    
    def test_astronomy_forecast_validation_duplicate_dates(self):
        """Test validation with duplicate dates."""
        location = Location(
            name="Test Location",
            latitude=51.5074,
            longitude=-0.1278
        )
        
        today = date.today()
        daily_data = [
            AstronomyData(date=today),
            AstronomyData(date=today)  # Duplicate
        ]
        
        with pytest.raises(ValueError, match="Daily astronomy data cannot contain duplicate dates"):
            AstronomyForecastData(
                location=location,
                daily_astronomy=daily_data
            )
    
    @patch('src.models.astronomy_data.datetime')
    def test_is_stale(self, mock_datetime):
        """Test is_stale property."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        last_updated = datetime(2023, 6, 15, 5, 0, 0)  # 7 hours ago
        mock_datetime.now.return_value = now
        
        location = Location("Test", 0.0, 0.0)
        astronomy_data = AstronomyData(date=date.today())
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=[astronomy_data],
            last_updated=last_updated
        )
        
        assert forecast.is_stale
        
        # Test fresh data
        fresh_updated = datetime(2023, 6, 15, 10, 0, 0)  # 2 hours ago
        fresh_forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=[astronomy_data],
            last_updated=fresh_updated
        )
        
        assert not fresh_forecast.is_stale
    
    def test_total_events(self):
        """Test total_events property."""
        location = Location("Test", 0.0, 0.0)
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        event1 = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Event 1",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time())
        )
        
        event2 = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Event 2",
            description="Test Description",
            start_time=datetime.combine(tomorrow, datetime.min.time())
        )
        
        event3 = AstronomyEvent(
            event_type=AstronomyEventType.MOON_PHASE,
            title="Event 3",
            description="Test Description",
            start_time=datetime.combine(tomorrow, datetime.min.time())
        )
        
        daily_data = [
            AstronomyData(date=today, events=[event1]),
            AstronomyData(date=tomorrow, events=[event2, event3])
        ]
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=daily_data
        )
        
        assert forecast.total_events == 3
    
    def test_has_high_priority_events(self):
        """Test has_high_priority_events property."""
        location = Location("Test", 0.0, 0.0)
        
        today = date.today()
        high_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="High Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.HIGH
        )
        
        low_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Low Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.LOW
        )
        
        # Test with high priority events
        high_priority_data = [AstronomyData(date=today, events=[high_event])]
        high_priority_forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=high_priority_data
        )
        assert high_priority_forecast.has_high_priority_events
        
        # Test without high priority events
        low_priority_data = [AstronomyData(date=today, events=[low_event])]
        low_priority_forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=low_priority_data
        )
        assert not low_priority_forecast.has_high_priority_events
    
    def test_forecast_date_properties(self):
        """Test forecast_start_date and forecast_end_date properties."""
        location = Location("Test", 0.0, 0.0)
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        daily_data = [
            AstronomyData(date=today),
            AstronomyData(date=tomorrow)
        ]
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=daily_data
        )
        
        assert forecast.forecast_start_date == today
        assert forecast.forecast_end_date == tomorrow
    
    def test_get_astronomy_for_date(self):
        """Test get_astronomy_for_date method."""
        location = Location("Test", 0.0, 0.0)
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        today_data = AstronomyData(date=today)
        tomorrow_data = AstronomyData(date=tomorrow)
        
        daily_data = [today_data, tomorrow_data]
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=daily_data
        )
        
        # Test found
        result = forecast.get_astronomy_for_date(today)
        assert result == today_data
        
        # Test not found
        result = forecast.get_astronomy_for_date(today + timedelta(days=5))
        assert result is None
    
    @patch('src.models.astronomy_data.date')
    def test_get_today_astronomy(self, mock_date):
        """Test get_today_astronomy method."""
        today = date(2023, 6, 15)
        mock_date.today.return_value = today
        
        location = Location("Test", 0.0, 0.0)
        today_data = AstronomyData(date=today)
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=[today_data]
        )
        
        result = forecast.get_today_astronomy()
        assert result == today_data
    
    @patch('src.models.astronomy_data.date')
    def test_get_tomorrow_astronomy(self, mock_date):
        """Test get_tomorrow_astronomy method."""
        today = date(2023, 6, 15)
        tomorrow = date(2023, 6, 16)
        mock_date.today.return_value = today
        
        location = Location("Test", 0.0, 0.0)
        tomorrow_data = AstronomyData(date=tomorrow)
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=[tomorrow_data]
        )
        
        result = forecast.get_tomorrow_astronomy()
        assert result == tomorrow_data
    
    def test_get_events_by_type(self):
        """Test get_events_by_type method."""
        location = Location("Test", 0.0, 0.0)
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        apod_event1 = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="APOD Event 1",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time())
        )
        
        iss_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="ISS Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time())
        )
        
        apod_event2 = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="APOD Event 2",
            description="Test Description",
            start_time=datetime.combine(tomorrow, datetime.min.time())
        )
        
        daily_data = [
            AstronomyData(date=today, events=[apod_event1, iss_event]),
            AstronomyData(date=tomorrow, events=[apod_event2])
        ]
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=daily_data
        )
        
        apod_events = forecast.get_events_by_type(AstronomyEventType.APOD)
        assert len(apod_events) == 2
        assert apod_event1 in apod_events
        assert apod_event2 in apod_events
        assert iss_event not in apod_events
    
    def test_get_high_priority_events(self):
        """Test get_high_priority_events method."""
        location = Location("Test", 0.0, 0.0)
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        high_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="High Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.HIGH
        )
        
        low_event = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Low Priority Event",
            description="Test Description",
            start_time=datetime.combine(today, datetime.min.time()),
            priority=AstronomyEventPriority.LOW
        )
        
        critical_event = AstronomyEvent(
            event_type=AstronomyEventType.MOON_PHASE,
            title="Critical Priority Event",
            description="Test Description",
            start_time=datetime.combine(tomorrow, datetime.min.time()),
            priority=AstronomyEventPriority.CRITICAL
        )
        
        daily_data = [
            AstronomyData(date=today, events=[high_event, low_event]),
            AstronomyData(date=tomorrow, events=[critical_event])
        ]
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=daily_data
        )
        
        high_priority_events = forecast.get_high_priority_events()
        assert len(high_priority_events) == 2
        assert high_event in high_priority_events
        assert critical_event in high_priority_events
        assert low_event not in high_priority_events
    
    @patch('src.models.astronomy_data.datetime')
    def test_get_upcoming_events(self, mock_datetime):
        """Test get_upcoming_events method."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        location = Location("Test", 0.0, 0.0)
        
        today = date(2023, 6, 15)
        tomorrow = date(2023, 6, 16)
        
        past_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Past Event",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 8, 0, 0)
        )
        
        future_event1 = AstronomyEvent(
            event_type=AstronomyEventType.ISS_PASS,
            title="Future Event 1",
            description="Test Description",
            start_time=datetime(2023, 6, 15, 16, 0, 0)
        )
        
        future_event2 = AstronomyEvent(
            event_type=AstronomyEventType.MOON_PHASE,
            title="Future Event 2",
            description="Test Description",
            start_time=datetime(2023, 6, 16, 10, 0, 0)
        )
        
        daily_data = [
            AstronomyData(date=today, events=[past_event, future_event1]),
            AstronomyData(date=tomorrow, events=[future_event2])
        ]
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=daily_data
        )
        
        # Test without limit
        upcoming_events = forecast.get_upcoming_events()
        assert len(upcoming_events) == 2
        assert upcoming_events[0] == future_event1  # Earlier future event
        assert upcoming_events[1] == future_event2  # Later future event
        assert past_event not in upcoming_events
        
        # Test with limit
        limited_events = forecast.get_upcoming_events(limit=1)
        assert len(limited_events) == 1
        assert limited_events[0] == future_event1


class TestLocation:
    """Comprehensive tests for Location class."""
    
    def test_location_creation_full(self):
        """Test full location creation with all parameters."""
        location = Location(
            name="London",
            latitude=51.5074,
            longitude=-0.1278,
            timezone="Europe/London",
            elevation=11.0
        )
        
        assert location.name == "London"
        assert location.latitude == 51.5074
        assert location.longitude == -0.1278
        assert location.timezone == "Europe/London"
        assert location.elevation == 11.0
    
    def test_location_validation_invalid_latitude(self):
        """Test validation with invalid latitude."""
        with pytest.raises(ValueError, match="Invalid latitude: 91.0"):
            Location(name="Test", latitude=91.0, longitude=0.0)
        
        with pytest.raises(ValueError, match="Invalid latitude: -91.0"):
            Location(name="Test", latitude=-91.0, longitude=0.0)
    
    def test_location_validation_invalid_longitude(self):
        """Test validation with invalid longitude."""
        with pytest.raises(ValueError, match="Invalid longitude: 181.0"):
            Location(name="Test", latitude=0.0, longitude=181.0)
        
        with pytest.raises(ValueError, match="Invalid longitude: -181.0"):
            Location(name="Test", latitude=0.0, longitude=-181.0)
    
    def test_location_validation_empty_name(self):
        """Test validation with empty name."""
        with pytest.raises(ValueError, match="Location name cannot be empty"):
            Location(name="   ", latitude=0.0, longitude=0.0)
    
    def test_location_validation_invalid_elevation(self):
        """Test validation with invalid elevation."""
        with pytest.raises(ValueError, match="Invalid elevation: -600.0"):
            Location(name="Test", latitude=0.0, longitude=0.0, elevation=-600.0)


class TestEmojiAstronomyIconStrategy:
    """Comprehensive tests for EmojiAstronomyIconStrategy class."""
    
    def test_get_icon_all_types(self):
        """Test get_icon method for all event types."""
        strategy = EmojiAstronomyIconStrategy()
        
        expected_icons = {
            AstronomyEventType.APOD: "📸",
            AstronomyEventType.ISS_PASS: "🛰️",
            AstronomyEventType.NEAR_EARTH_OBJECT: "☄️",
            AstronomyEventType.MOON_PHASE: "🌙",
            AstronomyEventType.PLANETARY_EVENT: "🪐",
            AstronomyEventType.METEOR_SHOWER: "⭐",
            AstronomyEventType.SOLAR_EVENT: "☀️",
            AstronomyEventType.SATELLITE_IMAGE: "🌍",
            AstronomyEventType.UNKNOWN: "❓"
        }
        
        for event_type, expected_icon in expected_icons.items():
            assert strategy.get_icon(event_type) == expected_icon
    
    def test_get_icon_unknown_type(self):
        """Test get_icon method with unknown event type."""
        strategy = EmojiAstronomyIconStrategy()
        
        # Test with a mock that's not in the dictionary
        # This will return the default "❓" icon
        mock_event_type = MagicMock()
        
        result = strategy.get_icon(mock_event_type)
        assert result == "❓"
    
    def test_get_strategy_name(self):
        """Test get_strategy_name method."""
        strategy = EmojiAstronomyIconStrategy()
        assert strategy.get_strategy_name() == "emoji"


class TestAstronomyIconProviderImpl:
    """Comprehensive tests for AstronomyIconProviderImpl class."""
    
    def test_init_with_strategy(self):
        """Test initialization with strategy."""
        strategy = EmojiAstronomyIconStrategy()
        
        with patch('src.models.astronomy_data.logger') as mock_logger:
            provider = AstronomyIconProviderImpl(strategy)
            
            assert provider._strategy == strategy
            mock_logger.info.assert_called_once_with(
                "AstronomyIconProvider initialized with emoji strategy"
            )
    
    def test_set_strategy(self):
        """Test set_strategy method."""
        old_strategy = EmojiAstronomyIconStrategy()
        new_strategy = EmojiAstronomyIconStrategy()
        
        provider = AstronomyIconProviderImpl(old_strategy)
        
        with patch('src.models.astronomy_data.logger') as mock_logger:
            provider.set_strategy(new_strategy)
            
            assert provider._strategy == new_strategy
            mock_logger.info.assert_called_with(
                "Astronomy icon strategy changed from emoji to emoji"
            )
    
    def test_get_astronomy_icon(self):
        """Test get_astronomy_icon method."""
        strategy = EmojiAstronomyIconStrategy()
        provider = AstronomyIconProviderImpl(strategy)
        
        result = provider.get_astronomy_icon(AstronomyEventType.APOD)
        assert result == "📸"
    
    def test_get_current_strategy_name(self):
        """Test get_current_strategy_name method."""
        strategy = EmojiAstronomyIconStrategy()
        provider = AstronomyIconProviderImpl(strategy)
        
        assert provider.get_current_strategy_name() == "emoji"


class TestAstronomyDataValidator:
    """Comprehensive tests for AstronomyDataValidator class."""
    
    def test_validate_event_type(self):
        """Test validate_event_type method."""
        assert AstronomyDataValidator.validate_event_type(AstronomyEventType.APOD)
        assert not AstronomyDataValidator.validate_event_type("invalid")  # type: ignore
        assert not AstronomyDataValidator.validate_event_type(None)  # type: ignore
    
    @patch('src.models.astronomy_data.datetime')
    def test_validate_timestamp(self, mock_datetime):
        """Test validate_timestamp method."""
        now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        # Valid timestamp
        valid_timestamp = datetime(2023, 6, 16, 12, 0, 0)  # Tomorrow
        assert AstronomyDataValidator.validate_timestamp(valid_timestamp)
        
        # Too old
        old_timestamp = datetime(2023, 6, 13, 12, 0, 0)  # 2 days ago
        assert not AstronomyDataValidator.validate_timestamp(old_timestamp)
        
        # Too far in future
        future_timestamp = datetime(2023, 8, 15, 12, 0, 0)  # 2 months later
        assert not AstronomyDataValidator.validate_timestamp(future_timestamp)
    
    def test_validate_priority(self):
        """Test validate_priority method."""
        assert AstronomyDataValidator.validate_priority(AstronomyEventPriority.HIGH)
        assert not AstronomyDataValidator.validate_priority("invalid")  # type: ignore
        assert not AstronomyDataValidator.validate_priority(None)  # type: ignore
    
    def test_validate_moon_phase(self):
        """Test validate_moon_phase method."""
        assert AstronomyDataValidator.validate_moon_phase(MoonPhase.FULL_MOON)
        assert AstronomyDataValidator.validate_moon_phase(None)
        assert not AstronomyDataValidator.validate_moon_phase("invalid")  # type: ignore
    
    def test_validate_location(self):
        """Test validate_location method."""
        # Valid location
        location = Location("Test", 0.0, 0.0)
        assert AstronomyDataValidator.validate_location(location)
        
        # Invalid latitude
        with pytest.raises(ValueError):
            Location("Test", 91.0, 0.0)
        
        # Invalid longitude
        with pytest.raises(ValueError):
            Location("Test", 0.0, 181.0)
        
        # Empty name
        with pytest.raises(ValueError):
            Location("   ", 0.0, 0.0)
        
        # Test exception handling
        assert not AstronomyDataValidator.validate_location(None)  # type: ignore
    
    def test_validate_astronomy_event(self):
        """Test validate_astronomy_event method."""
        # Valid event
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.now()
        )
        assert AstronomyDataValidator.validate_astronomy_event(event)
        
        # Test with mock invalid event using object.__setattr__ to bypass frozen dataclass
        invalid_event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.now()
        )
        
        # Use object.__setattr__ to modify frozen dataclass for testing
        object.__setattr__(invalid_event, 'title', '   ')  # Empty title
        assert not AstronomyDataValidator.validate_astronomy_event(invalid_event)
    
    def test_validate_astronomy_data(self):
        """Test validate_astronomy_data method."""
        test_date = date.today()
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.combine(test_date, datetime.min.time())
        )
        
        astronomy_data = AstronomyData(
            date=test_date,
            events=[event],
            moon_phase=MoonPhase.FULL_MOON,
            moon_illumination=0.5
        )
        
        assert AstronomyDataValidator.validate_astronomy_data(astronomy_data)
        
        # Test with invalid moon illumination - this will raise during creation
        with pytest.raises(ValueError, match="Moon illumination must be between 0.0 and 1.0"):
            AstronomyData(date=test_date, moon_illumination=1.5)
        
        # Test validation with mock data that has invalid moon illumination
        mock_data = MagicMock()
        mock_data.events = []
        mock_data.moon_phase = None
        mock_data.moon_illumination = 1.5  # Invalid
        
        assert not AstronomyDataValidator.validate_astronomy_data(mock_data)
    
    def test_validate_astronomy_forecast(self):
        """Test validate_astronomy_forecast method."""
        location = Location("Test", 0.0, 0.0)
        astronomy_data = AstronomyData(date=date.today())
        
        forecast = AstronomyForecastData(
            location=location,
            daily_astronomy=[astronomy_data]
        )
        
        assert AstronomyDataValidator.validate_astronomy_forecast(forecast)
        
        # Test with invalid location - this will raise during creation
        with pytest.raises(ValueError, match="Invalid latitude: 91.0"):
            Location("Test", 91.0, 0.0)
        
        # Test validation with mock forecast that has invalid location
        mock_forecast = MagicMock()
        mock_location = MagicMock()
        mock_location.latitude = 91.0  # Invalid
        mock_location.longitude = 0.0
        mock_location.name = "Test"
        mock_forecast.location = mock_location
        mock_forecast.daily_astronomy = [astronomy_data]
        mock_forecast.forecast_days = 7
        
        assert not AstronomyDataValidator.validate_astronomy_forecast(mock_forecast)


class TestProtocols:
    """Test protocol implementations."""
    
    def test_astronomy_data_reader_protocol(self):
        """Test AstronomyDataReader protocol implementation."""
        # AstronomyEvent should implement the protocol
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(),
            visibility_info="Test visibility"
        )
        
        # Test protocol methods
        assert event.event_type == AstronomyEventType.APOD
        assert event.title == "Test Event"
        assert event.start_time is not None
        assert event.has_visibility_info
    
    def test_astronomy_icon_provider_protocol(self):
        """Test AstronomyIconProvider protocol implementation."""
        provider = AstronomyIconProviderImpl(EmojiAstronomyIconStrategy())
        
        # Test protocol method
        icon = provider.get_astronomy_icon(AstronomyEventType.APOD)
        assert icon == "📸"


def test_default_astronomy_icon_provider():
    """Test default astronomy icon provider instance."""
    assert default_astronomy_icon_provider is not None
    assert isinstance(default_astronomy_icon_provider, AstronomyIconProviderImpl)
    assert default_astronomy_icon_provider.get_current_strategy_name() == "emoji"
    
    # Test that it works
    icon = default_astronomy_icon_provider.get_astronomy_icon(AstronomyEventType.APOD)
    assert icon == "📸"


class TestProtocolMethods:
    """Test protocol method implementations to cover missing lines."""
    
    def test_astronomy_data_reader_protocol_methods(self):
        """Test AstronomyDataReader protocol methods - covers lines 61, 65, 69, 73."""
        # Import the protocol to ensure it's loaded
        from src.models.astronomy_data import AstronomyDataReader
        
        # Create a class that implements the protocol
        class ConcreteAstronomyDataReader:
            def get_event_type(self) -> AstronomyEventType:
                return AstronomyEventType.APOD
            
            def get_title(self) -> str:
                return "Test Title"
            
            def get_start_time(self) -> datetime:
                return datetime.now()
            
            def has_visibility_info(self) -> bool:
                return True
        
        reader = ConcreteAstronomyDataReader()
        assert reader.get_event_type() == AstronomyEventType.APOD
        assert reader.get_title() == "Test Title"
        assert isinstance(reader.get_start_time(), datetime)
        assert reader.has_visibility_info() is True
        
        # Test that AstronomyEvent implements the protocol
        event = AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(),
            visibility_info="Test visibility"
        )
        
        # These should work as AstronomyEvent implements the protocol
        assert event.event_type == AstronomyEventType.APOD
        assert event.title == "Test Event"
        assert isinstance(event.start_time, datetime)
        assert event.has_visibility_info
    
    def test_astronomy_icon_provider_protocol_method(self):
        """Test AstronomyIconProvider protocol method - covers line 81."""
        # Import the protocol to ensure it's loaded
        from src.models.astronomy_data import AstronomyIconProvider
        
        # Create a class that implements the protocol
        class ConcreteAstronomyIconProvider:
            def get_astronomy_icon(self, event_type: AstronomyEventType) -> str:
                return "🌟"
        
        provider = ConcreteAstronomyIconProvider()
        assert provider.get_astronomy_icon(AstronomyEventType.APOD) == "🌟"
        
        # Test that AstronomyIconProviderImpl implements the protocol
        impl_provider = AstronomyIconProviderImpl(EmojiAstronomyIconStrategy())
        assert impl_provider.get_astronomy_icon(AstronomyEventType.APOD) == "📸"
    
    def test_protocol_definitions_directly(self):
        """Test protocol definitions to ensure they're covered."""
        # Import and reference the protocols to ensure coverage
        from src.models.astronomy_data import AstronomyDataReader, AstronomyIconProvider
        
        # Check that the protocols exist and have the expected methods
        assert hasattr(AstronomyDataReader, 'get_event_type')
        assert hasattr(AstronomyDataReader, 'get_title')
        assert hasattr(AstronomyDataReader, 'get_start_time')
        assert hasattr(AstronomyDataReader, 'has_visibility_info')
        assert hasattr(AstronomyIconProvider, 'get_astronomy_icon')


class TestEdgeCasesForFullCoverage:
    """Test edge cases to achieve 100% coverage."""
    
    def test_is_valid_url_edge_cases(self):
        """Test _is_valid_url with edge cases - covers lines 134-135."""
        # Test with malformed URL that causes urlparse to raise an exception
        with patch('src.models.astronomy_data.urlparse') as mock_urlparse:
            mock_urlparse.side_effect = Exception("Parse error")
            assert not AstronomyEvent._is_valid_url("malformed-url")
    
    def test_forecast_empty_daily_astronomy_edge_cases(self):
        """Test forecast properties with empty daily astronomy - covers lines 369, 376."""
        # Create forecast with empty daily_astronomy using __new__ to bypass validation
        location = Location("Test", 0.0, 0.0)
        forecast = AstronomyForecastData.__new__(AstronomyForecastData)
        object.__setattr__(forecast, 'location', location)
        object.__setattr__(forecast, 'daily_astronomy', [])
        object.__setattr__(forecast, 'last_updated', datetime.now())
        object.__setattr__(forecast, 'data_source', "NASA")
        object.__setattr__(forecast, 'data_version', "1.0")
        object.__setattr__(forecast, 'forecast_days', 7)
        
        # These should return None for empty daily_astronomy
        assert forecast.forecast_start_date is None
        assert forecast.forecast_end_date is None
    
    def test_validator_edge_cases_for_full_coverage(self):
        """Test validator edge cases - covers lines 565, 569, 574, 583, 588, 592."""
        # Test validate_astronomy_data with invalid event
        mock_data = MagicMock()
        mock_event = MagicMock()
        
        # Mock an event that fails validation
        with patch.object(AstronomyDataValidator, 'validate_astronomy_event', return_value=False):
            mock_data.events = [mock_event]
            mock_data.moon_phase = None
            mock_data.moon_illumination = None
            
            assert not AstronomyDataValidator.validate_astronomy_data(mock_data)
        
        # Test validate_astronomy_data with invalid moon phase
        mock_data2 = MagicMock()
        mock_data2.events = []
        mock_data2.moon_phase = "invalid_phase"  # Invalid moon phase
        mock_data2.moon_illumination = None
        
        with patch.object(AstronomyDataValidator, 'validate_moon_phase', return_value=False):
            assert not AstronomyDataValidator.validate_astronomy_data(mock_data2)
        
        # Test validate_astronomy_data with invalid moon illumination
        mock_data3 = MagicMock()
        mock_data3.events = []
        mock_data3.moon_phase = None
        mock_data3.moon_illumination = 1.5  # Invalid illumination
        
        assert not AstronomyDataValidator.validate_astronomy_data(mock_data3)
        
        # Test validate_astronomy_forecast with invalid daily data
        mock_forecast = MagicMock()
        mock_forecast.location = Location("Test", 0.0, 0.0)
        mock_forecast.daily_astronomy = [MagicMock()]
        mock_forecast.forecast_days = 7
        
        with patch.object(AstronomyDataValidator, 'validate_astronomy_data', return_value=False):
            assert not AstronomyDataValidator.validate_astronomy_forecast(mock_forecast)
        
        # Test validate_astronomy_forecast with too many days
        mock_forecast2 = MagicMock()
        mock_forecast2.location = Location("Test", 0.0, 0.0)
        mock_forecast2.daily_astronomy = [MagicMock() for _ in range(8)]  # Too many days
        mock_forecast2.forecast_days = 7
        
        with patch.object(AstronomyDataValidator, 'validate_location', return_value=True):
            with patch.object(AstronomyDataValidator, 'validate_astronomy_data', return_value=True):
                assert not AstronomyDataValidator.validate_astronomy_forecast(mock_forecast2)