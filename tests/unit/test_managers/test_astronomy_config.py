"""
Comprehensive tests for astronomy_config.py module.
Author: Oliver Ernster

This module provides 100% test coverage for all astronomy configuration classes.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.managers.astronomy_config import (
    AstronomyDisplayConfig,
    AstronomyCacheConfig,
    AstronomyServiceConfig,
    AstronomyConfig,
    AstronomyConfigManager,
)


class TestAstronomyDisplayConfig:
    """Test AstronomyDisplayConfig class."""

    def test_default_initialization(self):
        """Test default initialization of AstronomyDisplayConfig."""
        config = AstronomyDisplayConfig()

        assert config.show_in_forecast is True
        assert config.default_expanded is False
        assert config.max_events_per_day == 3
        assert config.icon_size == "medium"
        assert config.show_event_times is True
        assert config.show_visibility_info is True
        assert config.compact_mode is False
        assert config.animation_enabled is True

    def test_custom_initialization(self):
        """Test custom initialization of AstronomyDisplayConfig."""
        config = AstronomyDisplayConfig(
            show_in_forecast=False,
            default_expanded=True,
            max_events_per_day=5,
            icon_size="large",
            show_event_times=False,
            show_visibility_info=False,
            compact_mode=True,
            animation_enabled=False,
        )

        assert config.show_in_forecast is False
        assert config.default_expanded is True
        assert config.max_events_per_day == 5
        assert config.icon_size == "large"
        assert config.show_event_times is False
        assert config.show_visibility_info is False
        assert config.compact_mode is True
        assert config.animation_enabled is False

    def test_post_init_validation_max_events_too_low(self):
        """Test validation error when max_events_per_day is too low."""
        with pytest.raises(
            ValueError, match="max_events_per_day must be between 1 and 10"
        ):
            AstronomyDisplayConfig(max_events_per_day=0)

    def test_post_init_validation_max_events_too_high(self):
        """Test validation error when max_events_per_day is too high."""
        with pytest.raises(
            ValueError, match="max_events_per_day must be between 1 and 10"
        ):
            AstronomyDisplayConfig(max_events_per_day=11)

    def test_post_init_validation_invalid_icon_size(self):
        """Test validation error when icon_size is invalid."""
        with pytest.raises(
            ValueError, match="icon_size must be 'small', 'medium', or 'large'"
        ):
            AstronomyDisplayConfig(icon_size="invalid")

    def test_from_dict_with_all_values(self):
        """Test creating AstronomyDisplayConfig from dictionary with all values."""
        data = {
            "show_in_forecast": False,
            "default_expanded": True,
            "max_events_per_day": 7,
            "icon_size": "small",
            "show_event_times": False,
            "show_visibility_info": False,
            "compact_mode": True,
            "animation_enabled": False,
        }

        config = AstronomyDisplayConfig.from_dict(data)

        assert config.show_in_forecast is False
        assert config.default_expanded is True
        assert config.max_events_per_day == 7
        assert config.icon_size == "small"
        assert config.show_event_times is False
        assert config.show_visibility_info is False
        assert config.compact_mode is True
        assert config.animation_enabled is False

    def test_from_dict_with_partial_values(self):
        """Test creating AstronomyDisplayConfig from dictionary with partial values."""
        data = {"max_events_per_day": 5, "icon_size": "large"}

        config = AstronomyDisplayConfig.from_dict(data)

        # Should use defaults for missing values
        assert config.show_in_forecast is True
        assert config.default_expanded is False
        assert config.max_events_per_day == 5
        assert config.icon_size == "large"
        assert config.show_event_times is True
        assert config.show_visibility_info is True
        assert config.compact_mode is False
        assert config.animation_enabled is True

    def test_from_dict_empty(self):
        """Test creating AstronomyDisplayConfig from empty dictionary."""
        config = AstronomyDisplayConfig.from_dict({})

        # Should use all defaults
        assert config.show_in_forecast is True
        assert config.default_expanded is False
        assert config.max_events_per_day == 3
        assert config.icon_size == "medium"
        assert config.show_event_times is True
        assert config.show_visibility_info is True
        assert config.compact_mode is False
        assert config.animation_enabled is True

    def test_to_dict(self):
        """Test converting AstronomyDisplayConfig to dictionary."""
        config = AstronomyDisplayConfig(
            show_in_forecast=False,
            default_expanded=True,
            max_events_per_day=8,
            icon_size="large",
            show_event_times=False,
            show_visibility_info=False,
            compact_mode=True,
            animation_enabled=False,
        )

        result = config.to_dict()

        expected = {
            "show_in_forecast": False,
            "default_expanded": True,
            "max_events_per_day": 8,
            "icon_size": "large",
            "show_event_times": False,
            "show_visibility_info": False,
            "compact_mode": True,
            "animation_enabled": False,
        }

        assert result == expected


class TestAstronomyCacheConfig:
    """Test AstronomyCacheConfig class."""

    def test_default_initialization(self):
        """Test default initialization of AstronomyCacheConfig."""
        config = AstronomyCacheConfig()

        assert config.duration_hours == 6
        assert config.max_entries == 100
        assert config.cleanup_interval_hours == 24
        assert config.persist_to_disk is True
        assert config.cache_directory is None

    def test_custom_initialization(self):
        """Test custom initialization of AstronomyCacheConfig."""
        config = AstronomyCacheConfig(
            duration_hours=12,
            max_entries=200,
            cleanup_interval_hours=48,
            persist_to_disk=False,
            cache_directory="/tmp/cache",
        )

        assert config.duration_hours == 12
        assert config.max_entries == 200
        assert config.cleanup_interval_hours == 48
        assert config.persist_to_disk is False
        assert config.cache_directory == "/tmp/cache"

    def test_post_init_validation_duration_too_low(self):
        """Test validation error when duration_hours is too low."""
        with pytest.raises(
            ValueError, match="duration_hours must be between 1 and 168"
        ):
            AstronomyCacheConfig(duration_hours=0)

    def test_post_init_validation_duration_too_high(self):
        """Test validation error when duration_hours is too high."""
        with pytest.raises(
            ValueError, match="duration_hours must be between 1 and 168"
        ):
            AstronomyCacheConfig(duration_hours=169)

    def test_post_init_validation_max_entries_too_low(self):
        """Test validation error when max_entries is too low."""
        with pytest.raises(ValueError, match="max_entries must be between 10 and 1000"):
            AstronomyCacheConfig(max_entries=9)

    def test_post_init_validation_max_entries_too_high(self):
        """Test validation error when max_entries is too high."""
        with pytest.raises(ValueError, match="max_entries must be between 10 and 1000"):
            AstronomyCacheConfig(max_entries=1001)

    def test_post_init_validation_cleanup_interval_too_low(self):
        """Test validation error when cleanup_interval_hours is too low."""
        with pytest.raises(
            ValueError, match="cleanup_interval_hours must be between 1 and 168"
        ):
            AstronomyCacheConfig(cleanup_interval_hours=0)

    def test_post_init_validation_cleanup_interval_too_high(self):
        """Test validation error when cleanup_interval_hours is too high."""
        with pytest.raises(
            ValueError, match="cleanup_interval_hours must be between 1 and 168"
        ):
            AstronomyCacheConfig(cleanup_interval_hours=169)

    def test_from_dict_with_all_values(self):
        """Test creating AstronomyCacheConfig from dictionary with all values."""
        data = {
            "duration_hours": 24,
            "max_entries": 500,
            "cleanup_interval_hours": 72,
            "persist_to_disk": False,
            "cache_directory": "/custom/cache",
        }

        config = AstronomyCacheConfig.from_dict(data)

        assert config.duration_hours == 24
        assert config.max_entries == 500
        assert config.cleanup_interval_hours == 72
        assert config.persist_to_disk is False
        assert config.cache_directory == "/custom/cache"

    def test_from_dict_with_partial_values(self):
        """Test creating AstronomyCacheConfig from dictionary with partial values."""
        data = {"duration_hours": 12, "persist_to_disk": False}

        config = AstronomyCacheConfig.from_dict(data)

        # Should use defaults for missing values
        assert config.duration_hours == 12
        assert config.max_entries == 100
        assert config.cleanup_interval_hours == 24
        assert config.persist_to_disk is False
        assert config.cache_directory is None

    def test_from_dict_empty(self):
        """Test creating AstronomyCacheConfig from empty dictionary."""
        config = AstronomyCacheConfig.from_dict({})

        # Should use all defaults
        assert config.duration_hours == 6
        assert config.max_entries == 100
        assert config.cleanup_interval_hours == 24
        assert config.persist_to_disk is True
        assert config.cache_directory is None

    def test_to_dict(self):
        """Test converting AstronomyCacheConfig to dictionary."""
        config = AstronomyCacheConfig(
            duration_hours=18,
            max_entries=300,
            cleanup_interval_hours=36,
            persist_to_disk=False,
            cache_directory="/test/cache",
        )

        result = config.to_dict()

        expected = {
            "duration_hours": 18,
            "max_entries": 300,
            "cleanup_interval_hours": 36,
            "persist_to_disk": False,
            "cache_directory": "/test/cache",
        }

        assert result == expected

    def test_get_cache_duration_seconds(self):
        """Test getting cache duration in seconds."""
        config = AstronomyCacheConfig(duration_hours=2)
        assert config.get_cache_duration_seconds() == 7200  # 2 * 3600


class TestAstronomyServiceConfig:
    """Test AstronomyServiceConfig class."""

    def test_default_initialization(self):
        """Test default initialization of AstronomyServiceConfig."""
        config = AstronomyServiceConfig()

        assert config.apod is True
        assert config.neows is True
        assert config.iss is True
        assert config.epic is False
        assert config.mars_weather is False
        assert config.exoplanets is False

    def test_custom_initialization(self):
        """Test custom initialization of AstronomyServiceConfig."""
        config = AstronomyServiceConfig(
            apod=False,
            neows=False,
            iss=False,
            epic=True,
            mars_weather=True,
            exoplanets=True,
        )

        assert config.apod is False
        assert config.neows is False
        assert config.iss is False
        assert config.epic is True
        assert config.mars_weather is True
        assert config.exoplanets is True

    def test_from_dict_with_all_values(self):
        """Test creating AstronomyServiceConfig from dictionary with all values."""
        data = {
            "apod": False,
            "neows": False,
            "iss": False,
            "epic": True,
            "mars_weather": True,
            "exoplanets": True,
        }

        config = AstronomyServiceConfig.from_dict(data)

        assert config.apod is False
        assert config.neows is False
        assert config.iss is False
        assert config.epic is True
        assert config.mars_weather is True
        assert config.exoplanets is True

    def test_from_dict_with_partial_values(self):
        """Test creating AstronomyServiceConfig from dictionary with partial values."""
        data = {"epic": True, "mars_weather": True}

        config = AstronomyServiceConfig.from_dict(data)

        # Should use defaults for missing values
        assert config.apod is True
        assert config.neows is True
        assert config.iss is True
        assert config.epic is True
        assert config.mars_weather is True
        assert config.exoplanets is False

    def test_from_dict_empty(self):
        """Test creating AstronomyServiceConfig from empty dictionary."""
        config = AstronomyServiceConfig.from_dict({})

        # Should use all defaults
        assert config.apod is True
        assert config.neows is True
        assert config.iss is True
        assert config.epic is False
        assert config.mars_weather is False
        assert config.exoplanets is False

    def test_to_dict(self):
        """Test converting AstronomyServiceConfig to dictionary."""
        config = AstronomyServiceConfig(
            apod=False,
            neows=True,
            iss=False,
            epic=True,
            mars_weather=False,
            exoplanets=True,
        )

        result = config.to_dict()

        expected = {
            "apod": False,
            "neows": True,
            "iss": False,
            "epic": True,
            "mars_weather": False,
            "exoplanets": True,
        }

        assert result == expected

    def test_get_enabled_services_all_enabled(self):
        """Test getting enabled services when all are enabled."""
        config = AstronomyServiceConfig(
            apod=True,
            neows=True,
            iss=True,
            epic=True,
            mars_weather=True,
            exoplanets=True,
        )

        enabled = config.get_enabled_services()
        expected = ["apod", "neows", "iss", "epic", "mars_weather", "exoplanets"]

        assert enabled == expected

    def test_get_enabled_services_partial_enabled(self):
        """Test getting enabled services when some are enabled."""
        config = AstronomyServiceConfig(
            apod=True,
            neows=False,
            iss=True,
            epic=False,
            mars_weather=True,
            exoplanets=False,
        )

        enabled = config.get_enabled_services()
        expected = ["apod", "iss", "mars_weather"]

        assert enabled == expected

    def test_get_enabled_services_none_enabled(self):
        """Test getting enabled services when none are enabled."""
        config = AstronomyServiceConfig(
            apod=False,
            neows=False,
            iss=False,
            epic=False,
            mars_weather=False,
            exoplanets=False,
        )

        enabled = config.get_enabled_services()

        assert enabled == []

    def test_is_service_enabled_valid_services(self):
        """Test checking if specific services are enabled."""
        config = AstronomyServiceConfig(
            apod=True,
            neows=False,
            iss=True,
            epic=False,
            mars_weather=True,
            exoplanets=False,
        )

        assert config.is_service_enabled("apod") is True
        assert config.is_service_enabled("neows") is False
        assert config.is_service_enabled("iss") is True
        assert config.is_service_enabled("epic") is False
        assert config.is_service_enabled("mars_weather") is True
        assert config.is_service_enabled("exoplanets") is False

    def test_is_service_enabled_invalid_service(self):
        """Test checking if invalid service is enabled."""
        config = AstronomyServiceConfig()

        assert config.is_service_enabled("invalid_service") is False


class TestAstronomyConfig:
    """Test AstronomyConfig class."""

    def test_default_initialization(self):
        """Test default initialization of AstronomyConfig."""
        config = AstronomyConfig()

        assert config.enabled is True
        assert config.nasa_api_key == ""
        assert config.location_name == "London"
        assert config.location_latitude == 51.5074
        assert config.location_longitude == -0.1278
        assert config.timezone == "Europe/London"
        assert config.update_interval_minutes == 360
        assert config.timeout_seconds == 15
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 2
        assert isinstance(config.services, AstronomyServiceConfig)
        assert isinstance(config.display, AstronomyDisplayConfig)
        assert isinstance(config.cache, AstronomyCacheConfig)

    def test_custom_initialization(self):
        """Test custom initialization of AstronomyConfig."""
        services = AstronomyServiceConfig(apod=False, neows=True)
        display = AstronomyDisplayConfig(show_in_forecast=False)
        cache = AstronomyCacheConfig(duration_hours=12)

        config = AstronomyConfig(
            enabled=False,
            nasa_api_key="test_key",
            location_name="Paris",
            location_latitude=48.8566,
            location_longitude=2.3522,
            timezone="Europe/Paris",
            update_interval_minutes=720,
            timeout_seconds=30,
            max_retries=5,
            retry_delay_seconds=5,
            services=services,
            display=display,
            cache=cache,
        )

        assert config.enabled is False
        assert config.nasa_api_key == "test_key"
        assert config.location_name == "Paris"
        assert config.location_latitude == 48.8566
        assert config.location_longitude == 2.3522
        assert config.timezone == "Europe/Paris"
        assert config.update_interval_minutes == 720
        assert config.timeout_seconds == 30
        assert config.max_retries == 5
        assert config.retry_delay_seconds == 5
        assert config.services == services
        assert config.display == display
        assert config.cache == cache

    def test_post_init_validation_invalid_latitude_low(self):
        """Test validation error when latitude is too low."""
        with pytest.raises(ValueError, match="Invalid latitude: -91.0"):
            AstronomyConfig(location_latitude=-91.0)

    def test_post_init_validation_invalid_latitude_high(self):
        """Test validation error when latitude is too high."""
        with pytest.raises(ValueError, match="Invalid latitude: 91.0"):
            AstronomyConfig(location_latitude=91.0)

    def test_post_init_validation_invalid_longitude_low(self):
        """Test validation error when longitude is too low."""
        with pytest.raises(ValueError, match="Invalid longitude: -181.0"):
            AstronomyConfig(location_longitude=-181.0)

    def test_post_init_validation_invalid_longitude_high(self):
        """Test validation error when longitude is too high."""
        with pytest.raises(ValueError, match="Invalid longitude: 181.0"):
            AstronomyConfig(location_longitude=181.0)

    def test_post_init_validation_empty_location_name(self):
        """Test validation error when location name is empty."""
        with pytest.raises(ValueError, match="Location name cannot be empty"):
            AstronomyConfig(location_name="")

    def test_post_init_validation_whitespace_location_name(self):
        """Test validation error when location name is only whitespace."""
        with pytest.raises(ValueError, match="Location name cannot be empty"):
            AstronomyConfig(location_name="   ")

    @patch("src.managers.astronomy_config.logger")
    def test_post_init_validation_empty_api_key_warning(self, mock_logger):
        """Test warning when API key is empty but astronomy is enabled."""
        AstronomyConfig(enabled=True, nasa_api_key="")
        mock_logger.warning.assert_called_once_with(
            "Astronomy is enabled but NASA API key is empty"
        )

    @patch("src.managers.astronomy_config.logger")
    def test_post_init_validation_whitespace_api_key_warning(self, mock_logger):
        """Test warning when API key is only whitespace but astronomy is enabled."""
        AstronomyConfig(enabled=True, nasa_api_key="   ")
        mock_logger.warning.assert_called_once_with(
            "Astronomy is enabled but NASA API key is empty"
        )

    def test_post_init_validation_update_interval_too_low(self):
        """Test validation error when update_interval_minutes is too low."""
        with pytest.raises(
            ValueError, match="update_interval_minutes must be at least 60"
        ):
            AstronomyConfig(update_interval_minutes=59)

    def test_post_init_validation_timeout_too_low(self):
        """Test validation error when timeout_seconds is too low."""
        with pytest.raises(
            ValueError, match="timeout_seconds must be between 5 and 60"
        ):
            AstronomyConfig(timeout_seconds=4)

    def test_post_init_validation_timeout_too_high(self):
        """Test validation error when timeout_seconds is too high."""
        with pytest.raises(
            ValueError, match="timeout_seconds must be between 5 and 60"
        ):
            AstronomyConfig(timeout_seconds=61)

    def test_post_init_validation_max_retries_too_low(self):
        """Test validation error when max_retries is too low."""
        with pytest.raises(ValueError, match="max_retries must be between 0 and 5"):
            AstronomyConfig(max_retries=-1)

    def test_post_init_validation_max_retries_too_high(self):
        """Test validation error when max_retries is too high."""
        with pytest.raises(ValueError, match="max_retries must be between 0 and 5"):
            AstronomyConfig(max_retries=6)

    def test_post_init_validation_retry_delay_too_low(self):
        """Test validation error when retry_delay_seconds is too low."""
        with pytest.raises(
            ValueError, match="retry_delay_seconds must be between 1 and 10"
        ):
            AstronomyConfig(retry_delay_seconds=0)

    def test_post_init_validation_retry_delay_too_high(self):
        """Test validation error when retry_delay_seconds is too high."""
        with pytest.raises(
            ValueError, match="retry_delay_seconds must be between 1 and 10"
        ):
            AstronomyConfig(retry_delay_seconds=11)

    def test_from_dict_with_all_values(self):
        """Test creating AstronomyConfig from dictionary with all values."""
        data = {
            "enabled": False,
            "nasa_api_key": "test_key_123",
            "location_name": "Tokyo",
            "location_latitude": 35.6762,
            "location_longitude": 139.6503,
            "timezone": "Asia/Tokyo",
            "update_interval_minutes": 480,
            "timeout_seconds": 25,
            "max_retries": 4,
            "retry_delay_seconds": 3,
            "services": {
                "apod": False,
                "neows": True,
                "iss": False,
                "epic": True,
                "mars_weather": False,
                "exoplanets": True,
            },
            "display": {
                "show_in_forecast": False,
                "max_events_per_day": 5,
                "icon_size": "large",
            },
            "cache": {
                "duration_hours": 12,
                "max_entries": 200,
                "persist_to_disk": False,
            },
        }

        config = AstronomyConfig.from_dict(data)

        assert config.enabled is False
        assert config.nasa_api_key == "test_key_123"
        assert config.location_name == "Tokyo"
        assert config.location_latitude == 35.6762
        assert config.location_longitude == 139.6503
        assert config.timezone == "Asia/Tokyo"
        assert config.update_interval_minutes == 480
        assert config.timeout_seconds == 25
        assert config.max_retries == 4
        assert config.retry_delay_seconds == 3

        # Check nested configs
        assert config.services.apod is False
        assert config.services.neows is True
        assert config.services.epic is True
        assert config.display.show_in_forecast is False
        assert config.display.max_events_per_day == 5
        assert config.display.icon_size == "large"
        assert config.cache.duration_hours == 12
        assert config.cache.max_entries == 200
        assert config.cache.persist_to_disk is False

    def test_from_dict_with_partial_values(self):
        """Test creating AstronomyConfig from dictionary with partial values."""
        data = {
            "nasa_api_key": "partial_key",
            "location_name": "Berlin",
            "services": {"apod": False},
        }

        config = AstronomyConfig.from_dict(data)

        # Should use defaults for missing values
        assert config.enabled is True
        assert config.nasa_api_key == "partial_key"
        assert config.location_name == "Berlin"
        assert config.location_latitude == 51.5074  # default
        assert config.services.apod is False
        assert config.services.neows is True  # default

    def test_from_dict_empty(self):
        """Test creating AstronomyConfig from empty dictionary."""
        config = AstronomyConfig.from_dict({})

        # Should use all defaults
        assert config.enabled is True
        assert config.nasa_api_key == ""
        assert config.location_name == "London"
        assert config.location_latitude == 51.5074
        assert config.services.apod is True
        assert config.display.show_in_forecast is True
        assert config.cache.duration_hours == 6

    def test_to_dict(self):
        """Test converting AstronomyConfig to dictionary."""
        services = AstronomyServiceConfig(apod=False, epic=True)
        display = AstronomyDisplayConfig(show_in_forecast=False, max_events_per_day=7)
        cache = AstronomyCacheConfig(duration_hours=18, persist_to_disk=False)

        config = AstronomyConfig(
            enabled=False,
            nasa_api_key="test_key",
            location_name="Sydney",
            location_latitude=-33.8688,
            location_longitude=151.2093,
            timezone="Australia/Sydney",
            update_interval_minutes=600,
            timeout_seconds=20,
            max_retries=2,
            retry_delay_seconds=4,
            services=services,
            display=display,
            cache=cache,
        )

        result = config.to_dict()

        assert result["enabled"] is False
        assert result["nasa_api_key"] == "test_key"
        assert result["location_name"] == "Sydney"
        assert result["location_latitude"] == -33.8688
        assert result["location_longitude"] == 151.2093
        assert result["timezone"] == "Australia/Sydney"
        assert result["update_interval_minutes"] == 600
        assert result["timeout_seconds"] == 20
        assert result["max_retries"] == 2
        assert result["retry_delay_seconds"] == 4

        # Check nested dictionaries
        assert result["services"]["apod"] is False
        assert result["services"]["epic"] is True
        assert result["display"]["show_in_forecast"] is False
        assert result["display"]["max_events_per_day"] == 7
        assert result["cache"]["duration_hours"] == 18
        assert result["cache"]["persist_to_disk"] is False

    def test_create_default(self):
        """Test creating default AstronomyConfig."""
        config = AstronomyConfig.create_default()

        assert config.enabled is True
        assert config.nasa_api_key == ""
        assert config.location_name == "London"
        assert config.location_latitude == 51.5074
        assert config.location_longitude == -0.1278
        assert isinstance(config.services, AstronomyServiceConfig)
        assert isinstance(config.display, AstronomyDisplayConfig)
        assert isinstance(config.cache, AstronomyCacheConfig)

    @patch("src.managers.astronomy_config.logger")
    def test_from_file_success(self, mock_logger):
        """Test loading AstronomyConfig from file successfully."""
        test_data = {
            "astronomy": {
                "enabled": True,
                "nasa_api_key": "file_key",
                "location_name": "Madrid",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            config = AstronomyConfig.from_file(temp_path)

            assert config.enabled is True
            assert config.nasa_api_key == "file_key"
            assert config.location_name == "Madrid"
        finally:
            temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    def test_from_file_not_found(self, mock_logger):
        """Test loading AstronomyConfig from non-existent file."""
        non_existent_path = Path("non_existent_config.json")

        config = AstronomyConfig.from_file(non_existent_path)

        # Should return default config
        assert config.enabled is True
        assert config.nasa_api_key == ""
        assert config.location_name == "London"

        # Should have been called twice: once for file not found, once for empty API key
        assert mock_logger.warning.call_count == 2
        mock_logger.warning.assert_any_call(
            f"Astronomy config file not found: {non_existent_path}"
        )
        mock_logger.warning.assert_any_call(
            "Astronomy is enabled but NASA API key is empty"
        )

    @patch("src.managers.astronomy_config.logger")
    def test_from_file_invalid_json(self, mock_logger):
        """Test loading AstronomyConfig from file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = Path(f.name)

        try:
            with pytest.raises(
                ValueError, match="Invalid astronomy configuration file"
            ):
                AstronomyConfig.from_file(temp_path)
        finally:
            temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_from_file_permission_error(self, mock_open, mock_logger):
        """Test loading AstronomyConfig from file with permission error."""
        test_path = Path("test_config.json")

        with pytest.raises(PermissionError):
            AstronomyConfig.from_file(test_path)

    @patch("src.managers.astronomy_config.logger")
    def test_save_to_file_new_file(self, mock_logger):
        """Test saving AstronomyConfig to new file."""
        config = AstronomyConfig(
            nasa_api_key="save_test_key", location_name="Barcelona"
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # Remove the file so we can test creating a new one
        temp_path.unlink()

        try:
            config.save_to_file(temp_path)

            # Verify file was created and contains correct data
            with open(temp_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)

            assert "astronomy" in saved_data
            assert saved_data["astronomy"]["nasa_api_key"] == "save_test_key"
            assert saved_data["astronomy"]["location_name"] == "Barcelona"

            mock_logger.info.assert_called_once_with(
                f"Astronomy configuration saved to {temp_path}"
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    def test_save_to_file_existing_file(self, mock_logger):
        """Test saving AstronomyConfig to existing file."""
        # Create existing file with other data
        existing_data = {
            "other_config": {"key": "value"},
            "astronomy": {"old_key": "old_value"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(existing_data, f)
            temp_path = Path(f.name)

        config = AstronomyConfig(nasa_api_key="updated_key", location_name="Valencia")

        try:
            config.save_to_file(temp_path)

            # Verify file was updated correctly
            with open(temp_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)

            # Other config should be preserved
            assert saved_data["other_config"]["key"] == "value"
            # Astronomy config should be updated
            assert saved_data["astronomy"]["nasa_api_key"] == "updated_key"
            assert saved_data["astronomy"]["location_name"] == "Valencia"

            mock_logger.info.assert_called_once_with(
                f"Astronomy configuration saved to {temp_path}"
            )
        finally:
            temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_save_to_file_permission_error(self, mock_open, mock_logger):
        """Test saving AstronomyConfig with permission error."""
        config = AstronomyConfig()
        test_path = Path("test_config.json")

        with pytest.raises(PermissionError):
            config.save_to_file(test_path)

    def test_validate_enabled_with_api_key(self):
        """Test validation when enabled with valid API key."""
        config = AstronomyConfig(enabled=True, nasa_api_key="valid_key")

        issues = config.validate()
        assert len(issues) == 0

    def test_validate_enabled_without_api_key(self):
        """Test validation when enabled without API key."""
        config = AstronomyConfig(enabled=True, nasa_api_key="")

        issues = config.validate()
        assert "NASA API key is required when astronomy is enabled" in issues

    def test_validate_disabled_without_api_key(self):
        """Test validation when disabled without API key."""
        config = AstronomyConfig(enabled=False, nasa_api_key="")

        issues = config.validate()
        # Should not complain about missing API key when disabled
        assert "NASA API key is required when astronomy is enabled" not in issues

    def test_validate_empty_location_name(self):
        """Test validation with empty location name."""
        # Create config with valid name first, then modify to test validate() method
        config = AstronomyConfig(location_name="Valid")
        config.location_name = ""

        issues = config.validate()
        assert "Location name cannot be empty" in issues

    def test_validate_whitespace_location_name(self):
        """Test validation with whitespace-only location name."""
        # Create config with valid name first, then modify to test validate() method
        config = AstronomyConfig(location_name="Valid")
        config.location_name = "   "  # Only whitespace

        issues = config.validate()
        assert "Location name cannot be empty" in issues

    def test_validate_invalid_coordinates(self):
        """Test validation with invalid coordinates."""
        config = AstronomyConfig(location_latitude=50.0, location_longitude=0.0)

        # Modify to invalid values after creation
        config.location_latitude = -100.0
        config.location_longitude = 200.0

        issues = config.validate()
        assert "Invalid latitude: -100.0" in issues
        assert "Invalid longitude: 200.0" in issues

    def test_validate_no_services_enabled(self):
        """Test validation when no services are enabled."""
        services = AstronomyServiceConfig(
            apod=False,
            neows=False,
            iss=False,
            epic=False,
            mars_weather=False,
            exoplanets=False,
        )

        config = AstronomyConfig(
            enabled=True, nasa_api_key="valid_key", services=services
        )

        issues = config.validate()
        assert "At least one astronomy service must be enabled" in issues

    def test_validate_disabled_no_services_check(self):
        """Test validation when disabled - should not check services."""
        services = AstronomyServiceConfig(
            apod=False,
            neows=False,
            iss=False,
            epic=False,
            mars_weather=False,
            exoplanets=False,
        )

        config = AstronomyConfig(enabled=False, services=services)

        issues = config.validate()
        assert "At least one astronomy service must be enabled" not in issues

    def test_is_valid_true(self):
        """Test is_valid returns True for valid config."""
        config = AstronomyConfig(enabled=True, nasa_api_key="valid_key")

        assert config.is_valid() is True

    def test_is_valid_false(self):
        """Test is_valid returns False for invalid config."""
        config = AstronomyConfig(enabled=True, nasa_api_key="")  # Missing API key

        assert config.is_valid() is False

    def test_get_location_tuple(self):
        """Test getting location as tuple."""
        config = AstronomyConfig(location_latitude=40.7128, location_longitude=-74.0060)

        location = config.get_location_tuple()
        assert location == (40.7128, -74.0060)

    def test_get_cache_duration_seconds(self):
        """Test getting cache duration in seconds."""
        cache = AstronomyCacheConfig(duration_hours=3)
        config = AstronomyConfig(cache=cache)

        duration = config.get_cache_duration_seconds()
        assert duration == 10800  # 3 * 3600

    def test_get_update_interval_seconds(self):
        """Test getting update interval in seconds."""
        config = AstronomyConfig(update_interval_minutes=120)

        interval = config.get_update_interval_seconds()
        assert interval == 7200  # 120 * 60

    def test_has_valid_api_key_true(self):
        """Test has_valid_api_key returns True for valid key."""
        config = AstronomyConfig(nasa_api_key="valid_key_123")

        assert config.has_valid_api_key() is True

    def test_has_valid_api_key_false_empty(self):
        """Test has_valid_api_key returns False for empty key."""
        config = AstronomyConfig(nasa_api_key="")

        assert config.has_valid_api_key() is False

    def test_has_valid_api_key_false_whitespace(self):
        """Test has_valid_api_key returns False for whitespace key."""
        config = AstronomyConfig(nasa_api_key="   ")

        assert config.has_valid_api_key() is False

    def test_get_enabled_services_count(self):
        """Test getting count of enabled services."""
        services = AstronomyServiceConfig(
            apod=True,
            neows=False,
            iss=True,
            epic=True,
            mars_weather=False,
            exoplanets=False,
        )

        config = AstronomyConfig(services=services)

        count = config.get_enabled_services_count()
        assert count == 3  # apod, iss, epic

    def test_str_representation_enabled(self):
        """Test string representation when enabled."""
        services = AstronomyServiceConfig(apod=True, neows=True, iss=False)
        config = AstronomyConfig(
            enabled=True, location_name="TestCity", services=services
        )

        str_repr = str(config)
        assert "AstronomyConfig(enabled, 2 services, TestCity)" == str_repr

    def test_str_representation_disabled(self):
        """Test string representation when disabled."""
        config = AstronomyConfig(enabled=False, location_name="TestCity")

        str_repr = str(config)
        assert "AstronomyConfig(disabled, 3 services, TestCity)" == str_repr


class TestAstronomyConfigManager:
    """Test AstronomyConfigManager class."""

    @patch("src.managers.astronomy_config.logger")
    def test_init_default_path(self, mock_logger):
        """Test initialization with default path."""
        manager = AstronomyConfigManager()

        assert manager.config_path == Path("config.json")
        assert manager._config is None
        mock_logger.info.assert_called_once_with(
            "AstronomyConfigManager initialized with path: config.json"
        )

    @patch("src.managers.astronomy_config.logger")
    def test_init_custom_path(self, mock_logger):
        """Test initialization with custom path."""
        custom_path = Path("custom_config.json")
        manager = AstronomyConfigManager(custom_path)

        assert manager.config_path == custom_path
        assert manager._config is None
        mock_logger.info.assert_called_once_with(
            f"AstronomyConfigManager initialized with path: {custom_path}"
        )

    @patch("src.managers.astronomy_config.logger")
    def test_load_config_success(self, mock_logger):
        """Test loading config successfully."""
        test_data = {
            "astronomy": {
                "enabled": True,
                "nasa_api_key": "test_key",
                "location_name": "TestLocation",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            manager = AstronomyConfigManager(temp_path)
            config = manager.load_config()

            assert config.enabled is True
            assert config.nasa_api_key == "test_key"
            assert config.location_name == "TestLocation"
            assert manager._config == config

            mock_logger.info.assert_any_call(
                "Astronomy configuration loaded successfully"
            )
        finally:
            temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    def test_load_config_file_not_found(self, mock_logger):
        """Test loading config when file not found."""
        non_existent_path = Path("non_existent.json")
        manager = AstronomyConfigManager(non_existent_path)

        config = manager.load_config()

        # Should return default config
        assert config.enabled is True
        assert config.nasa_api_key == ""
        assert config.location_name == "London"
        assert manager._config == config

    @patch("src.managers.astronomy_config.logger")
    def test_load_config_exception(self, mock_logger):
        """Test loading config with exception."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = Path(f.name)

        try:
            manager = AstronomyConfigManager(temp_path)
            config = manager.load_config()

            # Should return default config on error
            assert config.enabled is True
            assert config.nasa_api_key == ""
            assert config.location_name == "London"
            assert manager._config == config

            mock_logger.error.assert_called()
        finally:
            temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    def test_save_config_success(self, mock_logger):
        """Test saving config successfully."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # Remove the file so we can test creating a new one
        temp_path.unlink()

        try:
            manager = AstronomyConfigManager(temp_path)
            config = AstronomyConfig(nasa_api_key="save_test", location_name="SaveTest")

            manager.save_config(config)

            assert manager._config == config
            mock_logger.info.assert_called_with(
                "Astronomy configuration saved successfully"
            )

            # Verify file was created
            assert temp_path.exists()
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    @patch.object(
        AstronomyConfig,
        "save_to_file",
        side_effect=PermissionError("Permission denied"),
    )
    def test_save_config_exception(self, mock_save, mock_logger):
        """Test saving config with exception."""
        manager = AstronomyConfigManager()
        config = AstronomyConfig()

        with pytest.raises(PermissionError):
            manager.save_config(config)

        mock_logger.error.assert_called_with(
            "Failed to save astronomy configuration: Permission denied"
        )

    def test_get_config_cached(self):
        """Test getting config when already cached."""
        manager = AstronomyConfigManager()
        cached_config = AstronomyConfig(nasa_api_key="cached")
        manager._config = cached_config

        config = manager.get_config()

        assert config == cached_config

    @patch("src.managers.astronomy_config.logger")
    def test_get_config_not_cached(self, mock_logger):
        """Test getting config when not cached."""
        test_data = {"astronomy": {"nasa_api_key": "loaded_key"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            manager = AstronomyConfigManager(temp_path)
            config = manager.get_config()

            assert config.nasa_api_key == "loaded_key"
            assert manager._config == config
        finally:
            temp_path.unlink()

    def test_validate_config(self):
        """Test validating current config."""
        manager = AstronomyConfigManager()
        config = AstronomyConfig(
            enabled=True, nasa_api_key=""  # Invalid - missing API key
        )
        manager._config = config

        issues = manager.validate_config()

        assert len(issues) > 0
        assert "NASA API key is required when astronomy is enabled" in issues

    def test_is_config_valid_true(self):
        """Test checking if config is valid - true case."""
        manager = AstronomyConfigManager()
        config = AstronomyConfig(enabled=True, nasa_api_key="valid_key")
        manager._config = config

        assert manager.is_config_valid() is True

    def test_is_config_valid_false(self):
        """Test checking if config is valid - false case."""
        manager = AstronomyConfigManager()
        config = AstronomyConfig(enabled=True, nasa_api_key="")  # Invalid
        manager._config = config

        assert manager.is_config_valid() is False

    def test_reset_to_default(self):
        """Test resetting config to default."""
        manager = AstronomyConfigManager()
        manager._config = AstronomyConfig(nasa_api_key="custom")

        default_config = manager.reset_to_default()

        assert default_config.nasa_api_key == ""
        assert default_config.location_name == "London"
        assert manager._config == default_config

    @patch("src.managers.astronomy_config.logger")
    def test_update_api_key(self, mock_logger):
        """Test updating API key."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # Remove the file so we can test creating a new one
        temp_path.unlink()

        try:
            manager = AstronomyConfigManager(temp_path)
            # Load initial config
            original_config = manager.get_config()
            original_location = original_config.location_name

            manager.update_api_key("new_api_key")

            # Verify config was updated and saved
            updated_config = manager._config
            assert updated_config is not None
            assert updated_config.nasa_api_key == "new_api_key"
            assert (
                updated_config.location_name == original_location
            )  # Should preserve other values

            mock_logger.info.assert_called_with(
                "Astronomy configuration saved successfully"
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    def test_update_location(self, mock_logger):
        """Test updating location."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # Remove the file so we can test creating a new one
        temp_path.unlink()

        try:
            manager = AstronomyConfigManager(temp_path)
            # Load initial config
            original_config = manager.get_config()
            original_api_key = original_config.nasa_api_key

            manager.update_location("New York", 40.7128, -74.0060)

            # Verify config was updated and saved
            updated_config = manager._config
            assert updated_config is not None
            assert updated_config.location_name == "New York"
            assert updated_config.location_latitude == 40.7128
            assert updated_config.location_longitude == -74.0060
            assert (
                updated_config.nasa_api_key == original_api_key
            )  # Should preserve other values

            mock_logger.info.assert_called_with(
                "Astronomy configuration saved successfully"
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @patch("src.managers.astronomy_config.logger")
    def test_toggle_service_valid_service(self, mock_logger):
        """Test toggling a valid service."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # Remove the file so we can test creating a new one
        temp_path.unlink()

        try:
            manager = AstronomyConfigManager(temp_path)
            # Load initial config
            original_config = manager.get_config()
            original_apod_state = original_config.services.apod

            manager.toggle_service("apod", not original_apod_state)

            # Verify service was toggled
            updated_config = manager._config
            assert updated_config is not None
            assert updated_config.services.apod == (not original_apod_state)

            mock_logger.info.assert_called_with(
                "Astronomy configuration saved successfully"
            )
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_toggle_service_invalid_service(self):
        """Test toggling an invalid service."""
        manager = AstronomyConfigManager()

        with pytest.raises(
            ValueError, match="Unknown astronomy service: invalid_service"
        ):
            manager.toggle_service("invalid_service", True)
