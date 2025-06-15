"""
Train data models and enums.

This module defines the core data structures for representing train information,
including departure times, status, delays, and service details.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum


class TrainStatus(Enum):
    """Enumeration of possible train statuses."""

    ON_TIME = "on_time"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    """Enumeration of train service types."""

    FAST = "fast"
    STOPPING = "stopping"
    EXPRESS = "express"
    SLEEPER = "sleeper"


@dataclass(frozen=True)
class TrainData:
    """
    Immutable data class representing a single train service.

    This class contains all the information about a train departure,
    including timing, status, platform, and service details.
    """

    departure_time: datetime
    scheduled_departure: datetime
    destination: str
    platform: Optional[str]
    operator: str
    service_type: ServiceType
    status: TrainStatus
    delay_minutes: int
    estimated_arrival: Optional[datetime]
    journey_duration: Optional[timedelta]
    current_location: Optional[str]
    train_uid: str
    service_id: str

    @property
    def is_delayed(self) -> bool:
        """Check if the train is delayed."""
        return self.delay_minutes > 0

    @property
    def is_cancelled(self) -> bool:
        """Check if the train is cancelled."""
        return self.status == TrainStatus.CANCELLED

    @property
    def status_color(self) -> str:
        """Get color code for status display based on current theme."""
        # Dark theme colors
        dark_color_map = {
            TrainStatus.ON_TIME: "#4caf50",  # Green
            TrainStatus.DELAYED: "#ff9800",  # Orange
            TrainStatus.CANCELLED: "#f44336",  # Red
            TrainStatus.UNKNOWN: "#666666",  # Gray
        }
        return dark_color_map[self.status]

    @property
    def status_color_light(self) -> str:
        """Get color code for status display in light theme."""
        light_color_map = {
            TrainStatus.ON_TIME: "#388e3c",  # Darker green
            TrainStatus.DELAYED: "#f57c00",  # Darker orange
            TrainStatus.CANCELLED: "#d32f2f",  # Darker red
            TrainStatus.UNKNOWN: "#9e9e9e",  # Darker gray
        }
        return light_color_map[self.status]

    def get_status_color(self, theme: str = "dark") -> str:
        """Get status color for the specified theme."""
        if theme == "light":
            return self.status_color_light
        return self.status_color

    def format_departure_time(self) -> str:
        """Format departure time for display (HH:MM)."""
        return self.departure_time.strftime("%H:%M")

    def format_scheduled_time(self) -> str:
        """Format scheduled departure time for display (HH:MM)."""
        return self.scheduled_departure.strftime("%H:%M")

    def format_delay(self) -> str:
        """Format delay information for display."""
        if self.delay_minutes == 0:
            return "On Time"
        elif self.delay_minutes > 0:
            return f"{self.delay_minutes}m Late"
        else:
            return "Early"

    def format_journey_duration(self) -> str:
        """Format journey duration for display."""
        if self.journey_duration is None:
            return "Unknown"

        total_minutes = int(self.journey_duration.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def format_arrival_time(self) -> str:
        """Format estimated arrival time for display."""
        if self.estimated_arrival is None:
            return "Unknown"
        return self.estimated_arrival.strftime("%H:%M")

    def get_service_icon(self) -> str:
        """Get Unicode icon for service type."""
        service_icons = {
            ServiceType.FAST: "⚡",
            ServiceType.EXPRESS: "🚄",
            ServiceType.STOPPING: "🚌",
            ServiceType.SLEEPER: "🛏️",
        }
        return service_icons.get(self.service_type, "🚂")

    def get_status_icon(self) -> str:
        """Get Unicode icon for train status."""
        status_icons = {
            TrainStatus.ON_TIME: "✅",
            TrainStatus.DELAYED: "⚠️",
            TrainStatus.CANCELLED: "❌",
            TrainStatus.UNKNOWN: "❓",
        }
        return status_icons.get(self.status, "❓")

    def to_display_dict(self, theme: str = "dark") -> dict:
        """Convert train data to dictionary for display purposes."""
        return {
            "departure_time": self.format_departure_time(),
            "scheduled_time": self.format_scheduled_time(),
            "destination": self.destination,
            "platform": self.platform or "TBA",
            "operator": self.operator,
            "service_type": self.service_type.value.title(),
            "service_icon": self.get_service_icon(),
            "status": self.status.value.replace("_", " ").title(),
            "status_icon": self.get_status_icon(),
            "status_color": self.get_status_color(theme),
            "delay": self.format_delay(),
            "delay_minutes": self.delay_minutes,
            "journey_duration": self.format_journey_duration(),
            "arrival_time": self.format_arrival_time(),
            "current_location": self.current_location or "Unknown",
            "is_delayed": self.is_delayed,
            "is_cancelled": self.is_cancelled,
        }
