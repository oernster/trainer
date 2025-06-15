"""
Unit tests for utility helper functions.

Tests the utility functions used throughout the application
for formatting, grouping, and calculating statistics.
"""

import pytest
from datetime import datetime, timedelta
from src.utils.helpers import (
    format_time,
    format_duration,
    get_time_group,
    group_trains_by_time,
    calculate_journey_stats,
    filter_trains_by_status,
    sort_trains_by_departure,
    get_next_departure,
    format_relative_time,
    validate_time_window,
    validate_refresh_interval,
    get_status_summary,
)
from src.models.train_data import TrainData, TrainStatus, ServiceType


class TestTimeFormatting:
    """Test time formatting utilities."""

    def test_format_time_basic(self):
        """Test basic time formatting."""
        test_time = datetime(2023, 6, 14, 20, 45, 30)
        assert format_time(test_time) == "20:45"

    def test_format_time_midnight(self):
        """Test formatting midnight."""
        test_time = datetime(2023, 6, 14, 0, 0, 0)
        assert format_time(test_time) == "00:00"

    def test_format_time_noon(self):
        """Test formatting noon."""
        test_time = datetime(2023, 6, 14, 12, 0, 0)
        assert format_time(test_time) == "12:00"

    def test_format_time_single_digits(self):
        """Test formatting with single digit hours/minutes."""
        test_time = datetime(2023, 6, 14, 9, 5, 0)
        assert format_time(test_time) == "09:05"


class TestDurationFormatting:
    """Test duration formatting utilities."""

    def test_format_duration_minutes_only(self):
        """Test formatting duration with minutes only."""
        duration = timedelta(minutes=30)
        assert format_duration(duration) == "30m"

    def test_format_duration_hours_and_minutes(self):
        """Test formatting duration with hours and minutes."""
        duration = timedelta(hours=1, minutes=30)
        assert format_duration(duration) == "1h 30m"

    def test_format_duration_hours_only(self):
        """Test formatting duration with hours only."""
        duration = timedelta(hours=2)
        assert format_duration(duration) == "2h 0m"

    def test_format_duration_zero(self):
        """Test formatting zero duration."""
        duration = timedelta(0)
        assert format_duration(duration) == "0m"

    def test_format_duration_with_seconds(self):
        """Test formatting duration with seconds (should be ignored)."""
        duration = timedelta(hours=1, minutes=30, seconds=45)
        assert format_duration(duration) == "1h 30m"

    def test_format_duration_large(self):
        """Test formatting large duration."""
        duration = timedelta(hours=10, minutes=15)
        assert format_duration(duration) == "10h 15m"


class TestTimeGrouping:
    """Test time grouping utilities."""

    def test_get_time_group_next_hour(self):
        """Test time group for trains departing within next hour."""
        now = datetime(2023, 6, 14, 20, 0)

        # Create train departing in 30 minutes
        train = TrainData(
            departure_time=now + timedelta(minutes=30),
            scheduled_departure=now + timedelta(minutes=30),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        )

        assert get_time_group(train, now) == "Next Hour"

    def test_get_time_group_next_3_hours(self):
        """Test time group for trains departing within next 3 hours."""
        now = datetime(2023, 6, 14, 20, 0)

        # Create train departing in 2 hours
        train = TrainData(
            departure_time=now + timedelta(hours=2),
            scheduled_departure=now + timedelta(hours=2),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        )

        assert get_time_group(train, now) == "Next 3 Hours"

    def test_get_time_group_later_today(self):
        """Test time group for trains departing later today."""
        now = datetime(2023, 6, 14, 10, 0)

        # Create train departing in 6 hours (same day)
        train = TrainData(
            departure_time=now + timedelta(hours=6),
            scheduled_departure=now + timedelta(hours=6),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        )

        assert get_time_group(train, now) == "Later Today"

    def test_get_time_group_tomorrow(self):
        """Test time group for trains departing tomorrow."""
        now = datetime(2023, 6, 14, 20, 0)

        # Create train departing tomorrow
        train = TrainData(
            departure_time=now + timedelta(days=1),
            scheduled_departure=now + timedelta(days=1),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        )

        assert get_time_group(train, now) == "Tomorrow"

    def test_get_time_group_default_now(self):
        """Test time group with default now parameter (datetime.now())."""
        # Create train departing in 30 minutes from actual current time
        future_time = datetime.now() + timedelta(minutes=30)
        train = TrainData(
            departure_time=future_time,
            scheduled_departure=future_time,
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        )

        # Call without now parameter to test default datetime.now()
        result = get_time_group(train)
        # Should be "Next Hour" since we created it 30 minutes in the future
        assert result == "Next Hour"


class TestTrainGrouping:
    """Test train grouping utilities."""

    def create_test_train(self, departure_time, status=TrainStatus.ON_TIME, delay=0):
        """Helper to create test train data."""
        return TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time - timedelta(minutes=delay),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=status,
            delay_minutes=delay,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid=f"W{hash(departure_time) % 10000}",
            service_id=f"S{hash(departure_time) % 10000}",
        )

    def test_group_trains_by_time_empty(self):
        """Test grouping empty train list."""
        groups = group_trains_by_time([])
        assert groups == {}

    def test_group_trains_by_time_single_group(self):
        """Test grouping trains in single time group."""
        # Use current time and create trains all within next hour
        now = datetime.now()
        trains = [
            self.create_test_train(now + timedelta(minutes=15)),
            self.create_test_train(now + timedelta(minutes=30)),
            self.create_test_train(now + timedelta(minutes=45)),
        ]

        groups = group_trains_by_time(trains)

        # Should have exactly one group for trains within next hour
        assert len(groups) == 1
        assert "Next Hour" in groups
        assert len(groups["Next Hour"]) == 3

    def test_group_trains_by_time_multiple_groups(self):
        """Test grouping trains across multiple time groups."""
        # Use current time and create trains relative to it
        now = datetime.now()
        trains = [
            self.create_test_train(now + timedelta(minutes=30)),  # Next Hour
            self.create_test_train(now + timedelta(hours=2)),  # Next 3 Hours
            self.create_test_train(now + timedelta(hours=5)),  # Later Today
            self.create_test_train(now + timedelta(days=1)),  # Tomorrow
        ]

        groups = group_trains_by_time(trains)

        # Should have at least 2 groups (exact number depends on timing)
        assert len(groups) >= 2
        assert len(groups) <= 4

        # Verify all trains are grouped
        total_trains = sum(len(group_trains) for group_trains in groups.values())
        assert total_trains == 4

        # Verify group names are valid
        valid_groups = {"Next Hour", "Next 3 Hours", "Later Today", "Tomorrow"}
        for group_name in groups.keys():
            assert group_name in valid_groups

    def test_group_trains_by_time_preserves_order(self):
        """Test that trains preserve their input order within groups."""
        # Use current time and create trains all within next hour
        now = datetime.now()
        trains = [
            self.create_test_train(now + timedelta(minutes=45)),  # Later in next hour
            self.create_test_train(now + timedelta(minutes=15)),  # Earlier in next hour
            self.create_test_train(now + timedelta(minutes=30)),  # Middle of next hour
        ]

        groups = group_trains_by_time(trains)
        next_hour_trains = groups["Next Hour"]

        # Should preserve input order (function doesn't sort)
        assert len(next_hour_trains) == 3
        assert next_hour_trains[0].departure_time == now + timedelta(minutes=45)
        assert next_hour_trains[1].departure_time == now + timedelta(minutes=15)
        assert next_hour_trains[2].departure_time == now + timedelta(minutes=30)


class TestJourneyStats:
    """Test journey statistics calculation."""

    def create_test_train(
        self, status=TrainStatus.ON_TIME, delay=0, service_type=ServiceType.FAST
    ):
        """Helper to create test train data."""
        departure_time = datetime.now()
        return TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time - timedelta(minutes=delay),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=service_type,
            status=status,
            delay_minutes=delay,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid=f"W{hash(departure_time) % 10000}",
            service_id=f"S{hash(departure_time) % 10000}",
        )

    def test_calculate_journey_stats_empty(self):
        """Test calculating stats for empty train list."""
        stats = calculate_journey_stats([])

        expected_stats = {
            "total_trains": 0,
            "on_time": 0,
            "delayed": 0,
            "cancelled": 0,
            "average_delay": 0,
            "max_delay": 0,
        }

        assert stats == expected_stats

    def test_calculate_journey_stats_all_on_time(self):
        """Test calculating stats for all on-time trains."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME, 0),
            self.create_test_train(TrainStatus.ON_TIME, 0),
            self.create_test_train(TrainStatus.ON_TIME, 0),
        ]

        stats = calculate_journey_stats(trains)

        assert stats["total_trains"] == 3
        assert stats["on_time"] == 3
        assert stats["delayed"] == 0
        assert stats["cancelled"] == 0
        assert stats["average_delay"] == 0
        assert stats["max_delay"] == 0

    def test_calculate_journey_stats_mixed_status(self):
        """Test calculating stats for mixed train statuses."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME, 0),
            self.create_test_train(TrainStatus.DELAYED, 5),
            self.create_test_train(TrainStatus.DELAYED, 10),
            self.create_test_train(TrainStatus.CANCELLED, 0),
        ]

        stats = calculate_journey_stats(trains)

        assert stats["total_trains"] == 4
        assert stats["on_time"] == 1
        assert stats["delayed"] == 2
        assert stats["cancelled"] == 1
        assert stats["average_delay"] == 7.5  # (5 + 10) / 2 = 7.5
        assert stats["max_delay"] == 10

    def test_calculate_journey_stats_delay_calculations(self):
        """Test delay calculations in stats."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME, 0),
            self.create_test_train(TrainStatus.DELAYED, 2),
            self.create_test_train(TrainStatus.DELAYED, 8),
            self.create_test_train(TrainStatus.DELAYED, 15),
        ]

        stats = calculate_journey_stats(trains)

        # Average delay: only delayed trains count (2 + 8 + 15) / 3 = 8.3
        assert stats["average_delay"] == 8.3
        assert stats["max_delay"] == 15

    def test_calculate_journey_stats_zero_division_safety(self):
        """Test that stats calculation handles edge cases safely."""
        # Test with only cancelled trains (no delays to average)
        trains = [
            self.create_test_train(TrainStatus.CANCELLED, 0),
            self.create_test_train(TrainStatus.CANCELLED, 0),
        ]

        stats = calculate_journey_stats(trains)

        assert stats["total_trains"] == 2
        assert stats["cancelled"] == 2
        assert stats["average_delay"] == 0  # Should not cause division by zero
        assert stats["max_delay"] == 0

    def test_calculate_journey_stats_only_delayed_trains(self):
        """Test stats calculation with only delayed trains."""
        trains = [
            self.create_test_train(TrainStatus.DELAYED, 3),
            self.create_test_train(TrainStatus.DELAYED, 7),
            self.create_test_train(TrainStatus.DELAYED, 12),
        ]

        stats = calculate_journey_stats(trains)

        assert stats["total_trains"] == 3
        assert stats["on_time"] == 0
        assert stats["delayed"] == 3
        assert stats["cancelled"] == 0
        assert stats["average_delay"] == 7.3  # (3 + 7 + 12) / 3 = 7.33, rounded to 7.3
        assert stats["max_delay"] == 12


class TestTrainFiltering:
    """Test train filtering utilities."""

    def create_test_train(self, status=TrainStatus.ON_TIME, delay=0):
        """Helper to create test train data."""
        departure_time = datetime.now()
        return TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time - timedelta(minutes=delay),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=status,
            delay_minutes=delay,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid=f"W{hash(departure_time) % 10000}",
            service_id=f"S{hash(departure_time) % 10000}",
        )

    def test_filter_trains_by_status_include_cancelled_true(self):
        """Test filtering trains with include_cancelled=True (default)."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.DELAYED),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        filtered = filter_trains_by_status(trains, include_cancelled=True)
        assert len(filtered) == 3
        assert filtered == trains  # Should return all trains

    def test_filter_trains_by_status_include_cancelled_default(self):
        """Test filtering trains with default include_cancelled parameter."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.DELAYED),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        filtered = filter_trains_by_status(trains)
        assert len(filtered) == 3
        assert filtered == trains  # Should return all trains by default

    def test_filter_trains_by_status_exclude_cancelled(self):
        """Test filtering trains with include_cancelled=False."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.DELAYED),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        filtered = filter_trains_by_status(trains, include_cancelled=False)
        assert len(filtered) == 2

        # Should only contain non-cancelled trains
        for train in filtered:
            assert not train.is_cancelled

    def test_filter_trains_by_status_empty_list(self):
        """Test filtering empty train list."""
        filtered = filter_trains_by_status([], include_cancelled=False)
        assert filtered == []

    def test_filter_trains_by_status_all_cancelled(self):
        """Test filtering when all trains are cancelled."""
        trains = [
            self.create_test_train(TrainStatus.CANCELLED),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        filtered = filter_trains_by_status(trains, include_cancelled=False)
        assert filtered == []


class TestTrainSorting:
    """Test train sorting utilities."""

    def create_test_train(self, departure_time, status=TrainStatus.ON_TIME):
        """Helper to create test train data."""
        return TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time,
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=status,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid=f"W{hash(departure_time) % 10000}",
            service_id=f"S{hash(departure_time) % 10000}",
        )

    def test_sort_trains_by_departure_empty(self):
        """Test sorting empty train list."""
        sorted_trains = sort_trains_by_departure([])
        assert sorted_trains == []

    def test_sort_trains_by_departure_single_train(self):
        """Test sorting single train."""
        now = datetime.now()
        train = self.create_test_train(now)

        sorted_trains = sort_trains_by_departure([train])
        assert len(sorted_trains) == 1
        assert sorted_trains[0] == train

    def test_sort_trains_by_departure_already_sorted(self):
        """Test sorting already sorted trains."""
        now = datetime.now()
        trains = [
            self.create_test_train(now + timedelta(minutes=10)),
            self.create_test_train(now + timedelta(minutes=20)),
            self.create_test_train(now + timedelta(minutes=30)),
        ]

        sorted_trains = sort_trains_by_departure(trains)
        assert len(sorted_trains) == 3

        # Should maintain order
        for i in range(len(sorted_trains) - 1):
            assert (
                sorted_trains[i].departure_time <= sorted_trains[i + 1].departure_time
            )

    def test_sort_trains_by_departure_reverse_order(self):
        """Test sorting trains in reverse order."""
        now = datetime.now()
        trains = [
            self.create_test_train(now + timedelta(minutes=30)),
            self.create_test_train(now + timedelta(minutes=20)),
            self.create_test_train(now + timedelta(minutes=10)),
        ]

        sorted_trains = sort_trains_by_departure(trains)
        assert len(sorted_trains) == 3

        # Should be sorted by departure time
        expected_times = [
            now + timedelta(minutes=10),
            now + timedelta(minutes=20),
            now + timedelta(minutes=30),
        ]

        for i, train in enumerate(sorted_trains):
            assert train.departure_time == expected_times[i]

    def test_sort_trains_by_departure_mixed_order(self):
        """Test sorting trains in mixed order."""
        now = datetime.now()
        trains = [
            self.create_test_train(now + timedelta(minutes=25)),
            self.create_test_train(now + timedelta(minutes=5)),
            self.create_test_train(now + timedelta(minutes=15)),
            self.create_test_train(now + timedelta(minutes=35)),
        ]

        sorted_trains = sort_trains_by_departure(trains)
        assert len(sorted_trains) == 4

        # Verify sorted order
        for i in range(len(sorted_trains) - 1):
            assert (
                sorted_trains[i].departure_time <= sorted_trains[i + 1].departure_time
            )

    def test_sort_trains_by_departure_same_time(self):
        """Test sorting trains with same departure time."""
        now = datetime.now()
        trains = [
            self.create_test_train(now),
            self.create_test_train(now),
            self.create_test_train(now + timedelta(minutes=10)),
        ]

        sorted_trains = sort_trains_by_departure(trains)
        assert len(sorted_trains) == 3

        # First two should have same time, third should be later
        assert sorted_trains[0].departure_time == sorted_trains[1].departure_time
        assert sorted_trains[2].departure_time > sorted_trains[0].departure_time


class TestNextDeparture:
    """Test next departure utilities."""

    def create_test_train(self, departure_time, status=TrainStatus.ON_TIME):
        """Helper to create test train data."""
        return TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time,
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=status,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid=f"W{hash(departure_time) % 10000}",
            service_id=f"S{hash(departure_time) % 10000}",
        )

    def test_get_next_departure_empty_list(self):
        """Test getting next departure from empty list."""
        with pytest.raises(ValueError, match="No trains provided"):
            get_next_departure([])

    def test_get_next_departure_no_future_trains(self):
        """Test getting next departure when no future trains exist."""
        now = datetime.now()
        trains = [
            self.create_test_train(now - timedelta(minutes=30)),
            self.create_test_train(now - timedelta(minutes=10)),
        ]

        with pytest.raises(ValueError, match="No future departures found"):
            get_next_departure(trains)

    def test_get_next_departure_single_future_train(self):
        """Test getting next departure with single future train."""
        now = datetime.now()
        future_train = self.create_test_train(now + timedelta(minutes=15))
        trains = [self.create_test_train(now - timedelta(minutes=10)), future_train]

        next_train = get_next_departure(trains)
        assert next_train == future_train

    def test_get_next_departure_multiple_future_trains(self):
        """Test getting next departure with multiple future trains."""
        now = datetime.now()
        earliest_train = self.create_test_train(now + timedelta(minutes=5))
        trains = [
            self.create_test_train(now - timedelta(minutes=10)),
            self.create_test_train(now + timedelta(minutes=30)),
            earliest_train,
            self.create_test_train(now + timedelta(minutes=15)),
        ]

        next_train = get_next_departure(trains)
        assert next_train == earliest_train

    def test_get_next_departure_mixed_past_and_future(self):
        """Test getting next departure with mixed past and future trains."""
        now = datetime.now()
        next_train = self.create_test_train(now + timedelta(minutes=10))
        trains = [
            self.create_test_train(now - timedelta(hours=1)),
            self.create_test_train(now - timedelta(minutes=30)),
            next_train,
            self.create_test_train(now + timedelta(minutes=20)),
            self.create_test_train(now + timedelta(hours=1)),
        ]

        result = get_next_departure(trains)
        assert result == next_train

    def test_get_next_departure_exactly_now(self):
        """Test getting next departure when train departs exactly now."""
        now = datetime.now()
        # Train departing exactly now should not be considered "future"
        trains = [
            self.create_test_train(now),
            self.create_test_train(now + timedelta(minutes=10)),
        ]

        next_train = get_next_departure(trains)
        # Should get the train 10 minutes from now, not the one departing exactly now
        assert next_train.departure_time == now + timedelta(minutes=10)


class TestRelativeTimeFormatting:
    """Test relative time formatting utilities."""

    def test_format_relative_time_seconds_future(self):
        """Test formatting future time in seconds."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(seconds=30)

        result = format_relative_time(future_time, now)
        assert result == "30 seconds from now"

    def test_format_relative_time_seconds_past(self):
        """Test formatting past time in seconds."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        past_time = now - timedelta(seconds=45)

        result = format_relative_time(past_time, now)
        assert result == "45 seconds ago"

    def test_format_relative_time_minutes_future_singular(self):
        """Test formatting future time in minutes (singular)."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(minutes=1)

        result = format_relative_time(future_time, now)
        assert result == "1 minute from now"

    def test_format_relative_time_minutes_future_plural(self):
        """Test formatting future time in minutes (plural)."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(minutes=15)

        result = format_relative_time(future_time, now)
        assert result == "15 minutes from now"

    def test_format_relative_time_minutes_past(self):
        """Test formatting past time in minutes."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        past_time = now - timedelta(minutes=25)

        result = format_relative_time(past_time, now)
        assert result == "25 minutes ago"

    def test_format_relative_time_hours_future_singular(self):
        """Test formatting future time in hours (singular)."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(hours=1)

        result = format_relative_time(future_time, now)
        assert result == "1 hour from now"

    def test_format_relative_time_hours_future_plural(self):
        """Test formatting future time in hours (plural)."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(hours=3)

        result = format_relative_time(future_time, now)
        assert result == "3 hours from now"

    def test_format_relative_time_hours_past(self):
        """Test formatting past time in hours."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        past_time = now - timedelta(hours=2)

        result = format_relative_time(past_time, now)
        assert result == "2 hours ago"

    def test_format_relative_time_days_future_singular(self):
        """Test formatting future time in days (singular)."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(days=1)

        result = format_relative_time(future_time, now)
        assert result == "1 day from now"

    def test_format_relative_time_days_future_plural(self):
        """Test formatting future time in days (plural)."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        future_time = now + timedelta(days=5)

        result = format_relative_time(future_time, now)
        assert result == "5 days from now"

    def test_format_relative_time_days_past(self):
        """Test formatting past time in days."""
        now = datetime(2023, 6, 14, 12, 0, 0)
        past_time = now - timedelta(days=3)

        result = format_relative_time(past_time, now)
        assert result == "3 days ago"

    def test_format_relative_time_default_now(self):
        """Test formatting relative time with default now parameter."""
        # This test uses actual datetime.now(), so we can't predict exact result
        # but we can verify it returns a string in expected format
        future_time = datetime.now() + timedelta(minutes=10)
        result = format_relative_time(future_time)

        assert isinstance(result, str)
        assert "from now" in result or "ago" in result

    def test_format_relative_time_edge_cases(self):
        """Test formatting relative time edge cases."""
        now = datetime(2023, 6, 14, 12, 0, 0)

        # Exactly 1 minute
        future_time = now + timedelta(minutes=1)
        result = format_relative_time(future_time, now)
        assert result == "1 minute from now"

        # Exactly 1 hour
        future_time = now + timedelta(hours=1)
        result = format_relative_time(future_time, now)
        assert result == "1 hour from now"

        # Exactly 1 day
        future_time = now + timedelta(days=1)
        result = format_relative_time(future_time, now)
        assert result == "1 day from now"


class TestValidation:
    """Test validation utilities."""

    def test_validate_time_window_valid_values(self):
        """Test time window validation with valid values."""
        assert validate_time_window(1) is True
        assert validate_time_window(12) is True
        assert validate_time_window(24) is True

    def test_validate_time_window_invalid_values(self):
        """Test time window validation with invalid values."""
        assert validate_time_window(0) is False
        assert validate_time_window(-1) is False
        assert validate_time_window(25) is False
        assert validate_time_window(100) is False

    def test_validate_time_window_boundary_values(self):
        """Test time window validation with boundary values."""
        assert validate_time_window(1) is True  # Lower boundary
        assert validate_time_window(24) is True  # Upper boundary
        assert validate_time_window(0) is False  # Below lower boundary
        assert validate_time_window(25) is False  # Above upper boundary

    def test_validate_refresh_interval_valid_values(self):
        """Test refresh interval validation with valid values."""
        assert validate_refresh_interval(1) is True
        assert validate_refresh_interval(30) is True
        assert validate_refresh_interval(60) is True

    def test_validate_refresh_interval_invalid_values(self):
        """Test refresh interval validation with invalid values."""
        assert validate_refresh_interval(0) is False
        assert validate_refresh_interval(-5) is False
        assert validate_refresh_interval(61) is False
        assert validate_refresh_interval(120) is False

    def test_validate_refresh_interval_boundary_values(self):
        """Test refresh interval validation with boundary values."""
        assert validate_refresh_interval(1) is True  # Lower boundary
        assert validate_refresh_interval(60) is True  # Upper boundary
        assert validate_refresh_interval(0) is False  # Below lower boundary
        assert validate_refresh_interval(61) is False  # Above upper boundary


class TestStatusSummary:
    """Test status summary utilities."""

    def create_test_train(self, status=TrainStatus.ON_TIME, delay=0):
        """Helper to create test train data."""
        departure_time = datetime.now()
        return TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time - timedelta(minutes=delay),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=status,
            delay_minutes=delay,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid=f"W{hash(departure_time) % 10000}",
            service_id=f"S{hash(departure_time) % 10000}",
        )

    def test_get_status_summary_empty_list(self):
        """Test status summary for empty train list."""
        summary = get_status_summary([])
        assert summary == "No trains"

    def test_get_status_summary_all_on_time(self):
        """Test status summary for all on-time trains."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.ON_TIME),
        ]

        summary = get_status_summary(trains)
        assert summary == "3 on time"

    def test_get_status_summary_all_delayed(self):
        """Test status summary for all delayed trains."""
        trains = [
            self.create_test_train(TrainStatus.DELAYED, 5),
            self.create_test_train(TrainStatus.DELAYED, 10),
        ]

        summary = get_status_summary(trains)
        assert summary == "2 delayed"

    def test_get_status_summary_all_cancelled(self):
        """Test status summary for all cancelled trains."""
        trains = [
            self.create_test_train(TrainStatus.CANCELLED),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        summary = get_status_summary(trains)
        assert summary == "2 cancelled"

    def test_get_status_summary_mixed_status(self):
        """Test status summary for mixed train statuses."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.DELAYED, 5),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        summary = get_status_summary(trains)
        assert summary == "2 on time, 1 delayed, 1 cancelled"

    def test_get_status_summary_only_on_time_and_delayed(self):
        """Test status summary with only on-time and delayed trains."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.DELAYED, 3),
            self.create_test_train(TrainStatus.DELAYED, 7),
        ]

        summary = get_status_summary(trains)
        assert summary == "1 on time, 2 delayed"

    def test_get_status_summary_only_delayed_and_cancelled(self):
        """Test status summary with only delayed and cancelled trains."""
        trains = [
            self.create_test_train(TrainStatus.DELAYED, 5),
            self.create_test_train(TrainStatus.CANCELLED),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        summary = get_status_summary(trains)
        assert summary == "1 delayed, 2 cancelled"

    def test_get_status_summary_unknown_status(self):
        """Test status summary with unknown status trains."""
        trains = [
            self.create_test_train(TrainStatus.UNKNOWN),
            self.create_test_train(TrainStatus.UNKNOWN),
        ]

        summary = get_status_summary(trains)
        # Unknown status trains should result in generic count
        assert summary == "2 trains"

    def test_get_status_summary_single_train_each_status(self):
        """Test status summary with single train of each status."""
        trains = [
            self.create_test_train(TrainStatus.ON_TIME),
            self.create_test_train(TrainStatus.DELAYED, 5),
            self.create_test_train(TrainStatus.CANCELLED),
        ]

        summary = get_status_summary(trains)
        assert summary == "1 on time, 1 delayed, 1 cancelled"
