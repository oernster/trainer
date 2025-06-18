"""
Astronomy data models for the Trainer application.
Author: Oliver Ernster

This module contains immutable data classes for astronomy information,
following solid Object-Oriented design principles with proper encapsulation,
single responsibility, and comprehensive validation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import List, Optional, Protocol, Dict, Any, Union
from urllib.parse import urlparse

from version import __version__

logger = logging.getLogger(__name__)


class AstronomyEventType(Enum):
    """Enumeration of astronomy event types."""
    APOD = "apod"
    ISS_PASS = "iss_pass"
    NEAR_EARTH_OBJECT = "near_earth_object"
    MOON_PHASE = "moon_phase"
    PLANETARY_EVENT = "planetary_event"
    METEOR_SHOWER = "meteor_shower"
    SOLAR_EVENT = "solar_event"
    SATELLITE_IMAGE = "satellite_image"
    UNKNOWN = "unknown"


class MoonPhase(Enum):
    """Moon phase enumeration."""
    NEW_MOON = "new_moon"
    WAXING_CRESCENT = "waxing_crescent"
    FIRST_QUARTER = "first_quarter"
    WAXING_GIBBOUS = "waxing_gibbous"
    FULL_MOON = "full_moon"
    WANING_GIBBOUS = "waning_gibbous"
    LAST_QUARTER = "last_quarter"
    WANING_CRESCENT = "waning_crescent"


class AstronomyEventPriority(Enum):
    """Priority levels for astronomy events."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AstronomyDataReader(Protocol):
    """Protocol for reading astronomy data."""
    
    def get_event_type(self) -> AstronomyEventType:
        """Get event type."""
        ...
    
    def get_title(self) -> str:
        """Get event title."""
        ...
    
    def get_start_time(self) -> datetime:
        """Get event start time."""
        ...
    
    def has_visibility_info(self) -> bool:
        """Check if event has visibility information."""
        ...


class AstronomyIconProvider(Protocol):
    """Protocol for providing astronomy icons."""
    
    def get_astronomy_icon(self, event_type: AstronomyEventType) -> str:
        """Get astronomy icon for given event type."""
        ...


@dataclass(frozen=True)
class AstronomyEvent:
    """
    Immutable astronomy event data.
    
    Follows Single Responsibility Principle - only responsible for
    astronomy event representation and basic validation.
    """
    event_type: AstronomyEventType
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    visibility_info: Optional[str] = None
    nasa_url: Optional[str] = None
    image_url: Optional[str] = None
    priority: AstronomyEventPriority = AstronomyEventPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate astronomy event data on creation."""
        # Validate title
        if not self.title.strip():
            raise ValueError("Event title cannot be empty")
        
        # Validate description
        if not self.description.strip():
            raise ValueError("Event description cannot be empty")
        
        # Validate time constraints
        if self.end_time and self.end_time < self.start_time:
            raise ValueError("End time cannot be before start time")
        
        # Validate URLs if provided
        if self.nasa_url and not self._is_valid_url(self.nasa_url):
            raise ValueError(f"Invalid NASA URL: {self.nasa_url}")
        
        if self.image_url and not self._is_valid_url(self.image_url):
            raise ValueError(f"Invalid image URL: {self.image_url}")
        
        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get event duration if end time is available."""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_ongoing(self) -> bool:
        """Check if event is currently ongoing."""
        now = datetime.now()
        if self.end_time:
            return self.start_time <= now <= self.end_time
        return self.start_time <= now <= (self.start_time + timedelta(hours=24))
    
    @property
    def is_future(self) -> bool:
        """Check if event is in the future."""
        return self.start_time > datetime.now()
    
    @property
    def is_past(self) -> bool:
        """Check if event is in the past."""
        if self.end_time:
            return self.end_time < datetime.now()
        return self.start_time < datetime.now()
    
    @property
    def has_visibility_info(self) -> bool:
        """Check if event has visibility information."""
        return self.visibility_info is not None and self.visibility_info.strip() != ""
    
    @property
    def has_image(self) -> bool:
        """Check if event has an associated image."""
        return self.image_url is not None and self.image_url.strip() != ""
    
    @property
    def event_icon(self) -> str:
        """Get emoji icon for event type."""
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
        return icons.get(self.event_type, "❓")
    
    def get_formatted_time(self, format_str: str = "%H:%M") -> str:
        """Get formatted start time."""
        return self.start_time.strftime(format_str)
    
    def get_formatted_duration(self) -> str:
        """Get formatted duration string."""
        if not self.duration:
            return "Unknown duration"
        
        total_seconds = int(self.duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


@dataclass(frozen=True)
class AstronomyData:
    """
    Immutable daily astronomy data container.
    
    Follows Single Responsibility Principle - only responsible for
    organizing and providing access to daily astronomy events.
    """
    date: date
    events: List[AstronomyEvent] = field(default_factory=list)
    primary_event: Optional[AstronomyEvent] = None
    moon_phase: Optional[MoonPhase] = None
    moon_illumination: Optional[float] = None  # 0.0 to 1.0
    sunrise_time: Optional[datetime] = None
    sunset_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate astronomy data on creation."""
        # Validate moon illumination
        if self.moon_illumination is not None:
            if not (0.0 <= self.moon_illumination <= 1.0):
                raise ValueError("Moon illumination must be between 0.0 and 1.0")
        
        # Validate sunrise/sunset times
        if self.sunrise_time and self.sunset_time:
            if self.sunrise_time.date() != self.date:
                raise ValueError("Sunrise time must be on the same date")
            if self.sunset_time.date() != self.date:
                raise ValueError("Sunset time must be on the same date")
            if self.sunrise_time >= self.sunset_time:
                raise ValueError("Sunrise must be before sunset")
        
        # Validate primary event is in events list
        if self.primary_event and self.primary_event not in self.events:
            raise ValueError("Primary event must be in the events list")
        
        # Validate all events are for the same date
        for event in self.events:
            if event.start_time.date() != self.date:
                raise ValueError(f"Event {event.title} is not for date {self.date}")
    
    @property
    def has_events(self) -> bool:
        """Check if there are any events for this date."""
        return len(self.events) > 0
    
    @property
    def event_count(self) -> int:
        """Get total number of events."""
        return len(self.events)
    
    @property
    def high_priority_events(self) -> List[AstronomyEvent]:
        """Get high priority events."""
        return [e for e in self.events if e.priority in [AstronomyEventPriority.HIGH, AstronomyEventPriority.CRITICAL]]
    
    @property
    def has_high_priority_events(self) -> bool:
        """Check if there are high priority events."""
        return len(self.high_priority_events) > 0
    
    @property
    def moon_phase_icon(self) -> str:
        """Get moon phase icon."""
        if not self.moon_phase:
            return "🌑"
        
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
        return icons.get(self.moon_phase, "🌑")
    
    @property
    def daylight_duration(self) -> Optional[timedelta]:
        """Get daylight duration if sunrise/sunset times are available."""
        if self.sunrise_time and self.sunset_time:
            return self.sunset_time - self.sunrise_time
        return None
    
    def get_events_by_type(self, event_type: AstronomyEventType) -> List[AstronomyEvent]:
        """Get events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_events_by_priority(self, priority: AstronomyEventPriority) -> List[AstronomyEvent]:
        """Get events of a specific priority."""
        return [e for e in self.events if e.priority == priority]
    
    def get_ongoing_events(self) -> List[AstronomyEvent]:
        """Get events that are currently ongoing."""
        return [e for e in self.events if e.is_ongoing]
    
    def get_future_events(self) -> List[AstronomyEvent]:
        """Get future events for this date."""
        return [e for e in self.events if e.is_future]
    
    def get_sorted_events(self, by_priority: bool = False) -> List[AstronomyEvent]:
        """Get events sorted by time or priority."""
        if by_priority:
            return sorted(self.events, key=lambda e: (e.priority.value, e.start_time), reverse=True)
        return sorted(self.events, key=lambda e: e.start_time)


@dataclass(frozen=True)
class AstronomyForecastData:
    """
    Complete astronomy forecast data container.
    
    Follows Single Responsibility Principle - only responsible for
    organizing and providing access to multi-day astronomy forecasts.
    """
    location: 'Location'  # Forward reference to avoid circular import
    daily_astronomy: List[AstronomyData] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    data_source: str = "NASA"
    data_version: str = field(default=__version__)
    forecast_days: int = 7
    
    def __post_init__(self):
        """Validate forecast data on creation."""
        if not self.daily_astronomy:
            raise ValueError("Forecast must contain at least one day of astronomy data")
        
        if len(self.daily_astronomy) > self.forecast_days:
            raise ValueError(f"Forecast cannot contain more than {self.forecast_days} days")
        
        # Validate dates are in chronological order
        dates = [data.date for data in self.daily_astronomy]
        if dates != sorted(dates):
            raise ValueError("Daily astronomy data must be in chronological order")
        
        # Validate no duplicate dates
        if len(dates) != len(set(dates)):
            raise ValueError("Daily astronomy data cannot contain duplicate dates")
    
    @property
    def is_stale(self) -> bool:
        """Check if forecast data is stale (older than 6 hours)."""
        return (datetime.now() - self.last_updated) > timedelta(hours=6)
    
    @property
    def total_events(self) -> int:
        """Get total number of events across all days."""
        return sum(data.event_count for data in self.daily_astronomy)
    
    @property
    def has_high_priority_events(self) -> bool:
        """Check if forecast contains any high priority events."""
        return any(data.has_high_priority_events for data in self.daily_astronomy)
    
    @property
    def forecast_start_date(self) -> Optional[date]:
        """Get the start date of the forecast."""
        if self.daily_astronomy:
            return self.daily_astronomy[0].date
        return None
    
    @property
    def forecast_end_date(self) -> Optional[date]:
        """Get the end date of the forecast."""
        if self.daily_astronomy:
            return self.daily_astronomy[-1].date
        return None
    
    def get_astronomy_for_date(self, target_date: date) -> Optional[AstronomyData]:
        """Get astronomy data for a specific date."""
        return next((data for data in self.daily_astronomy if data.date == target_date), None)
    
    def get_today_astronomy(self) -> Optional[AstronomyData]:
        """Get astronomy data for today."""
        return self.get_astronomy_for_date(date.today())
    
    def get_tomorrow_astronomy(self) -> Optional[AstronomyData]:
        """Get astronomy data for tomorrow."""
        tomorrow = date.today() + timedelta(days=1)
        return self.get_astronomy_for_date(tomorrow)
    
    def get_events_by_type(self, event_type: AstronomyEventType) -> List[AstronomyEvent]:
        """Get all events of a specific type across all days."""
        events = []
        for daily_data in self.daily_astronomy:
            events.extend(daily_data.get_events_by_type(event_type))
        return events
    
    def get_high_priority_events(self) -> List[AstronomyEvent]:
        """Get all high priority events across all days."""
        events = []
        for daily_data in self.daily_astronomy:
            events.extend(daily_data.high_priority_events)
        return events
    
    def get_upcoming_events(self, limit: Optional[int] = None) -> List[AstronomyEvent]:
        """Get upcoming events across all days."""
        events = []
        for daily_data in self.daily_astronomy:
            events.extend(daily_data.get_future_events())
        
        # Sort by start time
        events.sort(key=lambda e: e.start_time)
        
        if limit:
            return events[:limit]
        return events


# Location class for astronomy data (avoiding circular import)
@dataclass(frozen=True)
class Location:
    """Immutable location data for astronomy calculations."""
    name: str
    latitude: float
    longitude: float
    timezone: Optional[str] = None
    elevation: Optional[float] = None  # meters above sea level
    
    def __post_init__(self):
        """Validate location data."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")
        if not self.name.strip():
            raise ValueError("Location name cannot be empty")
        if self.elevation is not None and self.elevation < -500:  # Dead Sea is ~-430m
            raise ValueError(f"Invalid elevation: {self.elevation}")


class AstronomyIconStrategy(ABC):
    """Abstract strategy for astronomy icon display."""
    
    @abstractmethod
    def get_icon(self, event_type: AstronomyEventType) -> str:
        """Get icon for astronomy event type."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get name of the icon strategy."""
        pass


class EmojiAstronomyIconStrategy(AstronomyIconStrategy):
    """Strategy using emoji icons for astronomy event display."""
    
    ASTRONOMY_ICONS = {
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
    
    def get_icon(self, event_type: AstronomyEventType) -> str:
        """Get emoji icon for astronomy event type."""
        return self.ASTRONOMY_ICONS.get(event_type, "❓")
    
    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "emoji"


class AstronomyIconProviderImpl:
    """
    Context class for astronomy icon strategies.
    
    Implements Strategy pattern for flexible icon display.
    """
    
    def __init__(self, strategy: AstronomyIconStrategy):
        """Initialize with icon strategy."""
        self._strategy = strategy
        logger.info(f"AstronomyIconProvider initialized with {strategy.get_strategy_name()} strategy")
    
    def set_strategy(self, strategy: AstronomyIconStrategy) -> None:
        """Change icon strategy at runtime."""
        old_strategy = self._strategy.get_strategy_name()
        self._strategy = strategy
        logger.info(f"Astronomy icon strategy changed from {old_strategy} to {strategy.get_strategy_name()}")
    
    def get_astronomy_icon(self, event_type: AstronomyEventType) -> str:
        """Get astronomy icon using current strategy."""
        return self._strategy.get_icon(event_type)
    
    def get_current_strategy_name(self) -> str:
        """Get name of current strategy."""
        return self._strategy.get_strategy_name()


class AstronomyDataValidator:
    """
    Validator for astronomy data integrity.
    
    Follows Single Responsibility Principle - only responsible for validation.
    """
    
    @staticmethod
    def validate_event_type(event_type: AstronomyEventType) -> bool:
        """Validate astronomy event type."""
        return isinstance(event_type, AstronomyEventType)
    
    @staticmethod
    def validate_timestamp(timestamp: datetime) -> bool:
        """Validate timestamp is reasonable for astronomy events."""
        now = datetime.now()
        # Allow data from 1 day ago to 30 days in future
        return (now - timedelta(days=1)) <= timestamp <= (now + timedelta(days=30))
    
    @staticmethod
    def validate_priority(priority: AstronomyEventPriority) -> bool:
        """Validate astronomy event priority."""
        return isinstance(priority, AstronomyEventPriority)
    
    @staticmethod
    def validate_moon_phase(moon_phase: Optional[MoonPhase]) -> bool:
        """Validate moon phase."""
        return moon_phase is None or isinstance(moon_phase, MoonPhase)
    
    @staticmethod
    def validate_location(location: Location) -> bool:
        """Validate location data."""
        try:
            return (
                -90 <= location.latitude <= 90 and
                -180 <= location.longitude <= 180 and
                location.name.strip() != ""
            )
        except (AttributeError, TypeError):
            return False
    
    @classmethod
    def validate_astronomy_event(cls, event: AstronomyEvent) -> bool:
        """Validate complete astronomy event object."""
        return (
            cls.validate_event_type(event.event_type) and
            cls.validate_timestamp(event.start_time) and
            cls.validate_priority(event.priority) and
            event.title.strip() != "" and
            event.description.strip() != "" and
            (event.end_time is None or event.end_time >= event.start_time)
        )
    
    @classmethod
    def validate_astronomy_data(cls, astronomy_data: AstronomyData) -> bool:
        """Validate complete daily astronomy data."""
        # Validate all events
        for event in astronomy_data.events:
            if not cls.validate_astronomy_event(event):
                return False
        
        # Validate moon phase
        if not cls.validate_moon_phase(astronomy_data.moon_phase):
            return False
        
        # Validate moon illumination
        if astronomy_data.moon_illumination is not None:
            if not (0.0 <= astronomy_data.moon_illumination <= 1.0):
                return False
        
        return True
    
    @classmethod
    def validate_astronomy_forecast(cls, forecast: AstronomyForecastData) -> bool:
        """Validate complete astronomy forecast data."""
        # Validate location
        if not cls.validate_location(forecast.location):
            return False
        
        # Validate all daily data
        for daily_data in forecast.daily_astronomy:
            if not cls.validate_astronomy_data(daily_data):
                return False
        
        # Validate forecast constraints
        if len(forecast.daily_astronomy) > forecast.forecast_days:
            return False
        
        return True


# Default astronomy icon provider instance
default_astronomy_icon_provider = AstronomyIconProviderImpl(EmojiAstronomyIconStrategy())