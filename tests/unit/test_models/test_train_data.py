"""
Unit tests for TrainData model and related enums.

Tests the core data structures for representing train information,
including departure times, status, delays, and service details.
"""

import pytest
from datetime import datetime, timedelta
from src.models.train_data import TrainData, TrainStatus, ServiceType, CallingPoint


class TestTrainStatus:
    """Test TrainStatus enum."""

    def test_train_status_values(self):
        """Test TrainStatus enum values."""
        assert TrainStatus.ON_TIME.value == "on_time"
        assert TrainStatus.DELAYED.value == "delayed"
        assert TrainStatus.CANCELLED.value == "cancelled"
        assert TrainStatus.UNKNOWN.value == "unknown"

    def test_train_status_comparison(self):
        """Test TrainStatus enum comparison."""
        assert TrainStatus.ON_TIME == TrainStatus.ON_TIME
        assert TrainStatus.DELAYED != TrainStatus.ON_TIME


class TestServiceType:
    """Test ServiceType enum."""

    def test_service_type_values(self):
        """Test ServiceType enum values."""
        assert ServiceType.FAST.value == "fast"
        assert ServiceType.STOPPING.value == "stopping"
        assert ServiceType.EXPRESS.value == "express"
        assert ServiceType.SLEEPER.value == "sleeper"

    def test_service_type_comparison(self):
        """Test ServiceType enum comparison."""
        assert ServiceType.FAST == ServiceType.FAST
        assert ServiceType.EXPRESS != ServiceType.FAST


class TestCallingPoint:
    """Test CallingPoint model."""

    def test_calling_point_creation(self):
        """Test creating CallingPoint with valid data."""
        arrival_time = datetime(2023, 6, 14, 20, 45)
        departure_time = datetime(2023, 6, 14, 20, 47)

        calling_point = CallingPoint(
            station_name="Woking",
            station_code="WOK",
            scheduled_arrival=arrival_time,
            scheduled_departure=departure_time,
            expected_arrival=arrival_time,
            expected_departure=departure_time,
            platform="3",
            is_origin=False,
            is_destination=False,
        )

        assert calling_point.station_name == "Woking"
        assert calling_point.station_code == "WOK"
        assert calling_point.scheduled_arrival == arrival_time
        assert calling_point.scheduled_departure == departure_time
        assert calling_point.platform == "3"
        assert not calling_point.is_origin
        assert not calling_point.is_destination

    def test_calling_point_time_formatting(self):
        """Test time formatting methods."""
        arrival_time = datetime(2023, 6, 14, 20, 45)
        departure_time = datetime(2023, 6, 14, 20, 47)

        calling_point = CallingPoint(
            station_name="Woking",
            station_code="WOK",
            scheduled_arrival=arrival_time,
            scheduled_departure=departure_time,
            expected_arrival=None,
            expected_departure=None,
            platform="3",
        )

        assert calling_point.format_arrival_time() == "20:45"
        assert calling_point.format_departure_time() == "20:47"

    def test_calling_point_display_time(self):
        """Test get_display_time method for different station types."""
        arrival_time = datetime(2023, 6, 14, 20, 45)
        departure_time = datetime(2023, 6, 14, 20, 47)

        # Origin station
        origin = CallingPoint(
            station_name="Fleet",
            station_code="FLT",
            scheduled_arrival=None,
            scheduled_departure=departure_time,
            expected_arrival=None,
            expected_departure=None,
            platform="1",
            is_origin=True,
        )
        assert origin.get_display_time() == "20:47"

        # Destination station
        destination = CallingPoint(
            station_name="London Waterloo",
            station_code="WAT",
            scheduled_arrival=arrival_time,
            scheduled_departure=None,
            expected_arrival=None,
            expected_departure=None,
            platform="12",
            is_destination=True,
        )
        assert destination.get_display_time() == "20:45"

        # Intermediate station
        intermediate = CallingPoint(
            station_name="Woking",
            station_code="WOK",
            scheduled_arrival=arrival_time,
            scheduled_departure=departure_time,
            expected_arrival=None,
            expected_departure=None,
            platform="3",
        )
        assert intermediate.get_display_time() == "20:45"


class TestTrainData:
    """Test TrainData model with real data scenarios."""

    def create_sample_calling_points(self):
        """Create sample calling points for testing."""
        return [
            CallingPoint(
                station_name="Fleet",
                station_code="FLT",
                scheduled_arrival=None,
                scheduled_departure=datetime(2023, 6, 14, 20, 45),
                expected_arrival=None,
                expected_departure=datetime(2023, 6, 14, 20, 45),
                platform="1",
                is_origin=True,
            ),
            CallingPoint(
                station_name="Woking",
                station_code="WOK",
                scheduled_arrival=datetime(2023, 6, 14, 21, 0),
                scheduled_departure=datetime(2023, 6, 14, 21, 2),
                expected_arrival=datetime(2023, 6, 14, 21, 0),
                expected_departure=datetime(2023, 6, 14, 21, 2),
                platform="3",
            ),
            CallingPoint(
                station_name="London Waterloo",
                station_code="WAT",
                scheduled_arrival=datetime(2023, 6, 14, 21, 32),
                scheduled_departure=None,
                expected_arrival=datetime(2023, 6, 14, 21, 32),
                expected_departure=None,
                platform="12",
                is_destination=True,
            ),
        ]

    def test_train_data_creation_valid(self):
        """Test creating TrainData with valid data."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        scheduled_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=scheduled_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=datetime(2023, 6, 14, 21, 32),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        assert train.departure_time == departure_time
        assert train.scheduled_departure == scheduled_time
        assert train.destination == "London Waterloo"
        assert train.platform == "2"
        assert train.operator == "South Western Railway"
        assert train.service_type == ServiceType.FAST
        assert train.status == TrainStatus.ON_TIME
        assert train.delay_minutes == 0
        assert train.current_location == "Fleet"
        assert train.train_uid == "W12345"
        assert train.service_id == "24673004"
        assert len(train.calling_points) == 3

    def test_train_data_immutable(self):
        """Test that TrainData is immutable (frozen dataclass)."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            train.departure_time = datetime.now()

        with pytest.raises(AttributeError):
            train.delay_minutes = 5

    def test_train_data_on_time_scenario(self):
        """Test TrainData with on-time scenario."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        scheduled_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=scheduled_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=datetime(2023, 6, 14, 21, 32),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        assert train.is_delayed == False
        assert train.is_cancelled == False
        assert train.status_color == "#4caf50"  # Green for on-time
        assert train.format_departure_time() == "20:45"
        assert train.format_delay() == "On Time"
        assert train.get_status_icon() == "✅"

    def test_train_data_delayed_scenario(self):
        """Test TrainData with delay scenario."""
        departure_time = datetime(2023, 6, 14, 20, 47)
        scheduled_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=scheduled_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.DELAYED,
            delay_minutes=2,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        assert train.is_delayed == True
        assert train.is_cancelled == False
        assert train.delay_minutes == 2
        assert train.status_color == "#ff9800"  # Orange for delayed
        assert train.format_delay() == "2m Late"
        assert train.get_status_icon() == "⚠️"

    def test_train_data_cancelled_scenario(self):
        """Test TrainData with cancellation scenario."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.CANCELLED,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location=None,
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        assert train.is_cancelled == True
        assert train.is_delayed == False  # Cancelled trains are not considered delayed
        assert train.status_color == "#f44336"  # Red for cancelled
        assert train.get_status_icon() == "❌"

    def test_service_type_variations(self):
        """Test different service types."""
        calling_points = self.create_sample_calling_points()
        base_data = {
            "departure_time": datetime.now(),
            "scheduled_departure": datetime.now(),
            "destination": "London Waterloo",
            "platform": "1",
            "operator": "South Western Railway",
            "status": TrainStatus.ON_TIME,
            "delay_minutes": 0,
            "estimated_arrival": None,
            "journey_duration": None,
            "current_location": "Fleet",
            "train_uid": "W12345",
            "service_id": "24673004",
            "calling_points": calling_points,
        }

        # Test all service types
        for service_type in ServiceType:
            train = TrainData(service_type=service_type, **base_data)
            assert train.service_type == service_type
            assert train.get_service_icon() in ["⚡", "🚄", "🚌", "🛏️", "🚂"]

    def test_theme_color_variations(self):
        """Test status colors for different themes."""
        departure_time = datetime.now()
        calling_points = self.create_sample_calling_points()

        # Test each status with both themes
        status_tests = [
            (TrainStatus.ON_TIME, "#4caf50", "#388e3c"),
            (TrainStatus.DELAYED, "#ff9800", "#f57c00"),
            (TrainStatus.CANCELLED, "#f44336", "#d32f2f"),
            (TrainStatus.UNKNOWN, "#666666", "#9e9e9e"),
        ]

        for status, dark_color, light_color in status_tests:
            train = TrainData(
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
                train_uid="W12345",
                service_id="24673004",
                calling_points=calling_points,
            )

            assert train.get_status_color("dark") == dark_color
            assert train.get_status_color("light") == light_color
            assert train.status_color == dark_color  # Default is dark
            assert train.status_color_light == light_color

    def test_time_formatting(self):
        """Test time formatting methods."""
        departure_time = datetime(2023, 6, 14, 20, 45, 30)  # Include seconds
        scheduled_time = datetime(2023, 6, 14, 20, 43, 15)
        arrival_time = datetime(2023, 6, 14, 21, 32, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=scheduled_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.DELAYED,
            delay_minutes=2,
            estimated_arrival=arrival_time,
            journey_duration=timedelta(minutes=47, seconds=30),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        assert train.format_departure_time() == "20:45"
        assert train.format_scheduled_time() == "20:43"
        assert train.format_arrival_time() == "21:32"
        assert train.format_journey_duration() == "47m"

    def test_journey_duration_formatting(self):
        """Test journey duration formatting with various durations."""
        calling_points = self.create_sample_calling_points()
        base_data = {
            "departure_time": datetime.now(),
            "scheduled_departure": datetime.now(),
            "destination": "London Waterloo",
            "platform": "1",
            "operator": "South Western Railway",
            "service_type": ServiceType.FAST,
            "status": TrainStatus.ON_TIME,
            "delay_minutes": 0,
            "estimated_arrival": None,
            "current_location": "Fleet",
            "train_uid": "W12345",
            "service_id": "24673004",
            "calling_points": calling_points,
        }

        # Test various durations
        duration_tests = [
            (timedelta(minutes=30), "30m"),
            (timedelta(minutes=47), "47m"),
            (timedelta(hours=1, minutes=15), "1h 15m"),
            (timedelta(hours=2, minutes=0), "2h 0m"),
            (timedelta(hours=1, minutes=0), "1h 0m"),
            (None, "Unknown"),
        ]

        for duration, expected in duration_tests:
            train = TrainData(journey_duration=duration, **base_data)
            assert train.format_journey_duration() == expected

    def test_delay_formatting(self):
        """Test delay formatting with various delay scenarios."""
        calling_points = self.create_sample_calling_points()
        base_data = {
            "departure_time": datetime.now(),
            "scheduled_departure": datetime.now(),
            "destination": "London Waterloo",
            "platform": "1",
            "operator": "South Western Railway",
            "service_type": ServiceType.FAST,
            "status": TrainStatus.ON_TIME,
            "estimated_arrival": None,
            "journey_duration": None,
            "current_location": "Fleet",
            "train_uid": "W12345",
            "service_id": "24673004",
            "calling_points": calling_points,
        }

        # Test various delay scenarios
        delay_tests = [
            (0, "On Time"),
            (1, "1m Late"),
            (5, "5m Late"),
            (15, "15m Late"),
            (-2, "Early"),  # Early departure
        ]

        for delay_minutes, expected in delay_tests:
            train = TrainData(delay_minutes=delay_minutes, **base_data)
            assert train.format_delay() == expected

    def test_calling_points_methods(self):
        """Test calling points related methods."""
        calling_points = self.create_sample_calling_points()
        train = TrainData(
            departure_time=datetime.now(),
            scheduled_departure=datetime.now(),
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
            calling_points=calling_points,
        )

        # Test intermediate stations
        intermediate = train.get_intermediate_stations()
        assert len(intermediate) == 1
        assert intermediate[0].station_name == "Woking"

        # Test calling points formatting
        calling_points_str = train.format_calling_points()
        assert "Calling at: Woking" in calling_points_str

        # Test calling points summary
        summary = train.get_calling_points_summary()
        assert summary == "Via Woking"

    def test_calling_points_direct_service(self):
        """Test calling points for direct service."""
        # Create direct service with only origin and destination
        direct_calling_points = [
            CallingPoint(
                station_name="Fleet",
                station_code="FLT",
                scheduled_arrival=None,
                scheduled_departure=datetime(2023, 6, 14, 20, 45),
                expected_arrival=None,
                expected_departure=datetime(2023, 6, 14, 20, 45),
                platform="1",
                is_origin=True,
            ),
            CallingPoint(
                station_name="London Waterloo",
                station_code="WAT",
                scheduled_arrival=datetime(2023, 6, 14, 21, 32),
                scheduled_departure=None,
                expected_arrival=datetime(2023, 6, 14, 21, 32),
                expected_departure=None,
                platform="12",
                is_destination=True,
            ),
        ]

        train = TrainData(
            departure_time=datetime.now(),
            scheduled_departure=datetime.now(),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.EXPRESS,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=direct_calling_points,
        )

        # Test direct service
        intermediate = train.get_intermediate_stations()
        assert len(intermediate) == 0

        calling_points_str = train.format_calling_points()
        assert calling_points_str == "Direct service"

        summary = train.get_calling_points_summary()
        assert summary == "Direct"

    def test_to_display_dict(self):
        """Test conversion to display dictionary."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        scheduled_time = datetime(2023, 6, 14, 20, 43)
        arrival_time = datetime(2023, 6, 14, 21, 32)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=scheduled_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.DELAYED,
            delay_minutes=2,
            estimated_arrival=arrival_time,
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        display_dict = train.to_display_dict()

        # Verify all expected keys are present
        expected_keys = {
            "departure_time",
            "scheduled_time",
            "destination",
            "platform",
            "operator",
            "service_type",
            "service_icon",
            "status",
            "status_icon",
            "status_color",
            "delay",
            "delay_minutes",
            "journey_duration",
            "arrival_time",
            "current_location",
            "is_delayed",
            "is_cancelled",
            "calling_points",
            "calling_points_summary",
        }

        assert set(display_dict.keys()) == expected_keys

        # Verify specific values
        assert display_dict["departure_time"] == "20:45"
        assert display_dict["scheduled_time"] == "20:43"
        assert display_dict["destination"] == "London Waterloo"
        assert display_dict["platform"] == "2"
        assert display_dict["operator"] == "South Western Railway"
        assert display_dict["service_type"] == "Fast"
        assert display_dict["service_icon"] == "⚡"
        assert display_dict["status"] == "Delayed"
        assert display_dict["status_icon"] == "⚠️"
        assert display_dict["status_color"] == "#ff9800"
        assert display_dict["delay"] == "2m Late"
        assert display_dict["delay_minutes"] == 2
        assert display_dict["journey_duration"] == "47m"
        assert display_dict["arrival_time"] == "21:32"
        assert display_dict["current_location"] == "Fleet"
        assert display_dict["is_delayed"] == True
        assert display_dict["is_cancelled"] == False
        assert "Calling at: Woking" in display_dict["calling_points"]
        assert display_dict["calling_points_summary"] == "Via Woking"

    def test_to_display_dict_with_none_values(self):
        """Test display dictionary with None values."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time,
            destination="London Waterloo",
            platform=None,  # No platform assigned
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=None,  # No arrival estimate
            journey_duration=None,  # No duration info
            current_location=None,  # No location info
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        display_dict = train.to_display_dict()

        # Verify None values are handled properly
        assert display_dict["platform"] == "TBA"
        assert display_dict["arrival_time"] == "Unknown"
        assert display_dict["journey_duration"] == "Unknown"
        assert display_dict["current_location"] == "Unknown"

    def test_to_display_dict_theme_variations(self):
        """Test display dictionary with different themes."""
        departure_time = datetime(2023, 6, 14, 20, 45)
        calling_points = self.create_sample_calling_points()

        train = TrainData(
            departure_time=departure_time,
            scheduled_departure=departure_time,
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.DELAYED,
            delay_minutes=5,
            estimated_arrival=None,
            journey_duration=None,
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
            calling_points=calling_points,
        )

        # Test dark theme (default)
        dark_dict = train.to_display_dict("dark")
        assert dark_dict["status_color"] == "#ff9800"

        # Test light theme
        light_dict = train.to_display_dict("light")
        assert light_dict["status_color"] == "#f57c00"

        # Test invalid theme (should default to dark)
        invalid_dict = train.to_display_dict("invalid")
        assert invalid_dict["status_color"] == "#ff9800"
