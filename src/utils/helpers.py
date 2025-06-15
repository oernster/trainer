"""
Helper utility functions for the Train Times application.

This module contains various utility functions for formatting time,
duration, and organizing train data.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..models.train_data import TrainData


def format_time(dt: datetime) -> str:
    """
    Format datetime to HH:MM string.

    Args:
        dt: Datetime object to format

    Returns:
        str: Formatted time string
    """
    return dt.strftime("%H:%M")


def format_duration(td: timedelta) -> str:
    """
    Format timedelta to human-readable duration.

    Args:
        td: Timedelta object to format

    Returns:
        str: Formatted duration string (e.g., "1h 30m", "45m")
    """
    total_minutes = int(td.total_seconds() / 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def get_time_group(train: TrainData, now: Optional[datetime] = None) -> str:
    """
    Get time group for a train based on departure time.

    Args:
        train: Train data object
        now: Current time (defaults to datetime.now())

    Returns:
        str: Time group name
    """
    if now is None:
        now = datetime.now()

    time_diff = train.departure_time - now
    hours_ahead = time_diff.total_seconds() / 3600

    if hours_ahead <= 1:
        return "Next Hour"
    elif hours_ahead <= 3:
        return "Next 3 Hours"
    elif train.departure_time.date() == now.date():
        return "Later Today"
    else:
        return "Tomorrow"


def group_trains_by_time(trains: List[TrainData]) -> Dict[str, List[TrainData]]:
    """
    Group trains by time periods for better organization.

    Args:
        trains: List of train data objects

    Returns:
        dict: Dictionary with time groups as keys and train lists as values
    """
    now = datetime.now()
    groups = {"Next Hour": [], "Next 3 Hours": [], "Later Today": [], "Tomorrow": []}

    for train in trains:
        group = get_time_group(train, now)
        if group in groups:
            groups[group].append(train)

    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


def filter_trains_by_status(
    trains: List[TrainData], include_cancelled: bool = True
) -> List[TrainData]:
    """
    Filter trains by status.

    Args:
        trains: List of train data objects
        include_cancelled: Whether to include cancelled trains

    Returns:
        List[TrainData]: Filtered train list
    """
    if include_cancelled:
        return trains

    return [train for train in trains if not train.is_cancelled]


def sort_trains_by_departure(trains: List[TrainData]) -> List[TrainData]:
    """
    Sort trains by departure time.

    Args:
        trains: List of train data objects

    Returns:
        List[TrainData]: Sorted train list
    """
    return sorted(trains, key=lambda t: t.departure_time)


def get_next_departure(trains: List[TrainData]) -> TrainData:
    """
    Get the next departing train.

    Args:
        trains: List of train data objects

    Returns:
        TrainData: Next departing train or None if no trains

    Raises:
        ValueError: If no trains are provided
    """
    if not trains:
        raise ValueError("No trains provided")

    now = datetime.now()
    future_trains = [train for train in trains if train.departure_time > now]

    if not future_trains:
        raise ValueError("No future departures found")

    return min(future_trains, key=lambda t: t.departure_time)


def calculate_journey_stats(trains: List[TrainData]) -> Dict[str, float]:
    """
    Calculate statistics about the journey data.

    Args:
        trains: List of train data objects

    Returns:
        dict: Statistics including counts, delays, etc.
    """
    if not trains:
        return {
            "total_trains": 0,
            "on_time": 0,
            "delayed": 0,
            "cancelled": 0,
            "average_delay": 0,
            "max_delay": 0,
        }

    on_time = sum(1 for train in trains if train.status.value == "on_time")
    delayed = sum(1 for train in trains if train.status.value == "delayed")
    cancelled = sum(1 for train in trains if train.status.value == "cancelled")

    delays = [train.delay_minutes for train in trains if train.delay_minutes > 0]
    average_delay = sum(delays) / len(delays) if delays else 0
    max_delay = max(delays) if delays else 0

    return {
        "total_trains": len(trains),
        "on_time": on_time,
        "delayed": delayed,
        "cancelled": cancelled,
        "average_delay": round(average_delay, 1),
        "max_delay": max_delay,
    }


def format_relative_time(dt: datetime, now: Optional[datetime] = None) -> str:
    """
    Format datetime as relative time (e.g., "in 15 minutes", "2 hours ago").

    Args:
        dt: Target datetime
        now: Current time (defaults to datetime.now())

    Returns:
        str: Relative time string
    """
    if now is None:
        now = datetime.now()

    diff = dt - now
    total_seconds = diff.total_seconds()

    if total_seconds < 0:
        # Past time
        total_seconds = abs(total_seconds)
        suffix = "ago"
    else:
        # Future time
        suffix = "from now"

    if total_seconds < 60:
        return f"{int(total_seconds)} seconds {suffix}"
    elif total_seconds < 3600:
        minutes = int(total_seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} {suffix}"
    elif total_seconds < 86400:
        hours = int(total_seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} {suffix}"
    else:
        days = int(total_seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} {suffix}"


def validate_time_window(hours: int) -> bool:
    """
    Validate time window setting.

    Args:
        hours: Time window in hours

    Returns:
        bool: True if valid, False otherwise
    """
    return 1 <= hours <= 24


def validate_refresh_interval(minutes: int) -> bool:
    """
    Validate refresh interval setting.

    Args:
        minutes: Refresh interval in minutes

    Returns:
        bool: True if valid, False otherwise
    """
    return 1 <= minutes <= 60


def get_status_summary(trains: List[TrainData]) -> str:
    """
    Get a summary string of train statuses.

    Args:
        trains: List of train data objects

    Returns:
        str: Status summary string
    """
    if not trains:
        return "No trains"

    stats = calculate_journey_stats(trains)

    parts = []
    if stats["on_time"] > 0:
        parts.append(f"{stats['on_time']} on time")
    if stats["delayed"] > 0:
        parts.append(f"{stats['delayed']} delayed")
    if stats["cancelled"] > 0:
        parts.append(f"{stats['cancelled']} cancelled")

    if not parts:
        return f"{stats['total_trains']} trains"

    return ", ".join(parts)
