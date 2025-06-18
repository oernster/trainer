"""
Global pytest configuration and fixtures.
"""

import warnings
import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from src.managers.config_manager import ConfigData, APIConfig, StationConfig, RefreshConfig, DisplayConfig
from src.managers.weather_config import WeatherConfigFactory
from src.models.train_data import TrainData, TrainStatus, ServiceType

# Suppress RuntimeWarnings globally at the Python level
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="coroutine 'AsyncMockMixin._execute_mock_call' was never awaited")

# Configure pytest to ignore RuntimeWarnings
def pytest_configure(config):
    """Configure pytest to suppress RuntimeWarnings."""
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", message=".*AsyncMockMixin.*was never awaited.*")

@pytest.fixture(autouse=True)
def suppress_runtime_warnings():
    """Automatically suppress RuntimeWarnings for all tests."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        yield

@pytest.fixture
def test_config():
    """Provide a test configuration for API manager tests."""
    return ConfigData(
        api=APIConfig(
            app_id="test_id",
            app_key="test_key",
            base_url="https://transportapi.com/v3/uk",
            timeout_seconds=10,
            max_retries=3,
            rate_limit_per_minute=30
        ),
        stations=StationConfig(
            from_code="FLE",
            from_name="Fleet",
            to_code="WAT",
            to_name="London Waterloo"
        ),
        refresh=RefreshConfig(
            auto_enabled=True,
            interval_minutes=2,
            manual_enabled=True
        ),
        display=DisplayConfig(
            max_trains=50,
            time_window_hours=10,
            show_cancelled=True,
            theme="dark"
        ),
        weather=WeatherConfigFactory.create_waterloo_config()
    )

@pytest.fixture
def test_api_responses():
    """Provide test API response data."""
    return {
        "departures_success": {
            "departures": {
                "all": [
                    {
                        "aimed_departure_time": "20:45",
                        "expected_departure_time": "20:47",
                        "destination_name": "London Waterloo",
                        "platform": "2",
                        "operator_name": "South Western Railway",
                        "category": "OO",
                        "status": "LATE",
                        "train_uid": "W12345",
                        "service": "24673004",
                        "origin_name": "Fleet"
                    }
                ]
            }
        },
        "departures_empty": {
            "departures": {
                "all": []
            }
        },
        "departures_no_data": {
            "some_other_key": "value"
        }
    }

@pytest.fixture
def temp_config_file():
    """Provide a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "api": {
                "app_id": "test_id",
                "app_key": "test_key",
                "base_url": "https://transportapi.com/v3/uk",
                "timeout_seconds": 10,
                "max_retries": 3,
                "rate_limit_per_minute": 30
            },
            "stations": {
                "from_code": "FLE",
                "from_name": "Fleet",
                "to_code": "WAT",
                "to_name": "London Waterloo"
            },
            "refresh": {
                "auto_enabled": True,
                "interval_minutes": 2,
                "manual_enabled": True
            },
            "display": {
                "max_trains": 50,
                "time_window_hours": 10,
                "show_cancelled": True,
                "theme": "dark"
            },
            "weather": WeatherConfigFactory.create_waterloo_config().model_dump()
        }
        json.dump(config_data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)

@pytest.fixture
def sample_train_data():
    """Provide sample train data for UI tests."""
    return [
        TrainData(
            departure_time=datetime.now() + timedelta(minutes=5),
            scheduled_departure=datetime.now() + timedelta(minutes=5),
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.STOPPING,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=datetime.now() + timedelta(minutes=52),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004"
        ),
        TrainData(
            departure_time=datetime.now() + timedelta(minutes=15),
            scheduled_departure=datetime.now() + timedelta(minutes=12),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.EXPRESS,
            status=TrainStatus.DELAYED,
            delay_minutes=3,
            estimated_arrival=datetime.now() + timedelta(minutes=59),
            journey_duration=timedelta(minutes=44),
            current_location="Fleet",
            train_uid="W12346",
            service_id="24673005"
        ),
        TrainData(
            departure_time=datetime.now() + timedelta(minutes=25),
            scheduled_departure=datetime.now() + timedelta(minutes=25),
            destination="London Waterloo",
            platform="3",
            operator="South Western Railway",
            service_type=ServiceType.STOPPING,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=datetime.now() + timedelta(minutes=72),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12347",
            service_id="24673006"
        )
    ]

@pytest.fixture
def large_train_dataset():
    """Provide a large dataset of train data for performance tests."""
    trains = []
    for i in range(100):
        trains.append(
            TrainData(
                departure_time=datetime.now() + timedelta(minutes=i*2),
                scheduled_departure=datetime.now() + timedelta(minutes=i*2),
                destination="London Waterloo",
                platform=str((i % 4) + 1),
                operator="South Western Railway",
                service_type=ServiceType.STOPPING if i % 2 == 0 else ServiceType.EXPRESS,
                status=TrainStatus.ON_TIME if i % 3 == 0 else TrainStatus.DELAYED,
                delay_minutes=i % 10,
                estimated_arrival=datetime.now() + timedelta(minutes=i*2 + 47),
                journey_duration=timedelta(minutes=47),
                current_location="Fleet",
                train_uid=f"W{12345 + i}",
                service_id=f"2467300{i % 10}"
            )
        )
    return trains
