"""
Pytest configuration and fixtures for the Trainer train times application.

This module provides shared fixtures and configuration for all tests,
emphasizing real integration testing over mocking.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Try to import PySide6 components, but make them optional for basic tests
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    HAS_QT = True
except ImportError:
    HAS_QT = False

from src.managers.config_manager import ConfigManager, ConfigData, APIConfig, StationConfig, RefreshConfig, DisplayConfig
from src.models.train_data import TrainData, TrainStatus, ServiceType


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for UI tests."""
    if not HAS_QT:
        pytest.skip("PySide6 not available")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def test_config():
    """Provide test configuration with real API credentials."""
    return ConfigData(
        api=APIConfig(
            app_id=os.getenv("TEST_TRANSPORT_API_ID", "test_id"),
            app_key=os.getenv("TEST_TRANSPORT_API_KEY", "test_key"),
            base_url="https://transportapi.com/v3/uk",
            timeout_seconds=30,  # Longer timeout for real API calls
            max_retries=2,
            rate_limit_per_minute=10  # Conservative for testing
        ),
        stations=StationConfig(
            from_code="FLE",
            from_name="Fleet",
            to_code="WAT",
            to_name="London Waterloo"
        ),
        refresh=RefreshConfig(
            auto_enabled=False,  # Disable auto-refresh in tests
            interval_minutes=5,
            manual_enabled=True
        ),
        display=DisplayConfig(
            max_trains=50,
            time_window_hours=10,
            show_cancelled=True,
            theme="dark"
        )
    )


@pytest.fixture
def temp_config_file(test_config):
    """Create temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_config.model_dump(), f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def config_manager(temp_config_file):
    """Provide ConfigManager with temporary config file."""
    return ConfigManager(temp_config_file)


@pytest.fixture
def main_window(qapp, config_manager):
    """Create MainWindow instance for UI testing."""
    if not HAS_QT:
        pytest.skip("PySide6 not available")
    
    from src.ui.main_window import MainWindow
    
    window = MainWindow()
    window.config_manager = config_manager
    window.config = config_manager.load_config()
    yield window
    window.close()


@pytest.fixture
def sample_train_data():
    """Provide sample train data for testing."""
    base_time = datetime.now().replace(second=0, microsecond=0)
    
    return [
        TrainData(
            departure_time=base_time + timedelta(minutes=15),
            scheduled_departure=base_time + timedelta(minutes=15),
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=base_time + timedelta(minutes=62),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004"
        ),
        TrainData(
            departure_time=base_time + timedelta(minutes=22),
            scheduled_departure=base_time + timedelta(minutes=20),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.STOPPING,
            status=TrainStatus.DELAYED,
            delay_minutes=2,
            estimated_arrival=base_time + timedelta(minutes=74),
            journey_duration=timedelta(minutes=52),
            current_location="Fleet",
            train_uid="W12346",
            service_id="24673005"
        ),
        TrainData(
            departure_time=base_time + timedelta(minutes=35),
            scheduled_departure=base_time + timedelta(minutes=35),
            destination="London Waterloo",
            platform="3",
            operator="South Western Railway",
            service_type=ServiceType.EXPRESS,
            status=TrainStatus.CANCELLED,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location=None,
            train_uid="W12347",
            service_id="24673006"
        )
    ]


@pytest.fixture
def large_train_dataset():
    """Generate large dataset of train data for performance testing."""
    trains = []
    base_time = datetime.now().replace(second=0, microsecond=0)
    
    for i in range(100):
        train = TrainData(
            departure_time=base_time + timedelta(minutes=i*10),
            scheduled_departure=base_time + timedelta(minutes=i*10),
            destination="London Waterloo",
            platform=str((i % 10) + 1),
            operator="South Western Railway",
            service_type=ServiceType.FAST if i % 2 == 0 else ServiceType.STOPPING,
            status=TrainStatus.ON_TIME if i % 3 == 0 else TrainStatus.DELAYED,
            delay_minutes=i % 5,
            estimated_arrival=base_time + timedelta(minutes=i*10 + 47),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid=f"W{12345 + i}",
            service_id=f"2467300{i}"
        )
        trains.append(train)
    
    return trains


@pytest.fixture
def test_api_responses():
    """Provide sample API response data for testing."""
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
                    },
                    {
                        "aimed_departure_time": "21:15",
                        "expected_departure_time": "21:15",
                        "destination_name": "London Waterloo",
                        "platform": "1",
                        "operator_name": "South Western Railway",
                        "category": "XX",
                        "status": "ON TIME",
                        "train_uid": "W12346",
                        "service": "24673005",
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
        "departures_no_data": {}
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow)"
    )
    config.addinivalue_line(
        "markers", "ui: marks tests as UI tests (requires PySide6)"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require real API access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "ui" in str(item.fspath):
            item.add_marker(pytest.mark.ui)
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        if "api" in item.name.lower():
            item.add_marker(pytest.mark.api)