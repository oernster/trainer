"""
Comprehensive tests for WeatherConfig to achieve 100% test coverage.
Author: Oliver Ernster

This module provides complete test coverage for the weather configuration,
including all classes, methods, validators, and edge cases.
"""

import pytest
from unittest.mock import patch, Mock
from pydantic import ValidationError

from src.managers.weather_config import (
    WeatherConfig,
    WeatherConfigValidator,
    WeatherConfigFactory,
    WeatherConfigMigrator,
    default_weather_config
)


class TestWeatherConfig:
    """Test cases for WeatherConfig class."""

    def test_default_initialization(self):
        """Test default weather config initialization."""
        config = WeatherConfig()
        
        assert config.enabled is True
        assert config.location_latitude == 51.5074
        assert config.location_longitude == -0.1278
        assert config.location_name == "London"
        assert config.refresh_interval_minutes == 30
        assert config.show_humidity is True
        assert config.temperature_unit == "celsius"
        assert config.cache_duration_minutes == 30
        assert config.max_retries == 3
        assert config.timeout_seconds == 10

    def test_custom_initialization(self):
        """Test custom weather config initialization."""
        config = WeatherConfig(
            enabled=False,
            location_name="New York",
            location_latitude=40.7128,
            location_longitude=-74.0060,
            temperature_unit="fahrenheit",
            refresh_interval_minutes=60
        )
        
        assert config.enabled is False
        assert config.location_name == "New York"
        assert config.location_latitude == 40.7128
        assert config.location_longitude == -74.0060
        assert config.temperature_unit == "fahrenheit"
        assert config.refresh_interval_minutes == 60

    def test_temperature_unit_validation_valid(self):
        """Test valid temperature unit validation."""
        config_celsius = WeatherConfig(temperature_unit="celsius")
        config_fahrenheit = WeatherConfig(temperature_unit="fahrenheit")
        
        assert config_celsius.temperature_unit == "celsius"
        assert config_fahrenheit.temperature_unit == "fahrenheit"

    def test_temperature_unit_validation_invalid(self):
        """Test invalid temperature unit validation."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(temperature_unit="kelvin")
        
        assert "Temperature unit must be celsius or fahrenheit" in str(exc_info.value)

    def test_latitude_validation_valid(self):
        """Test valid latitude validation."""
        config_min = WeatherConfig(location_latitude=-90.0)
        config_max = WeatherConfig(location_latitude=90.0)
        config_zero = WeatherConfig(location_latitude=0.0)
        
        assert config_min.location_latitude == -90.0
        assert config_max.location_latitude == 90.0
        assert config_zero.location_latitude == 0.0

    def test_latitude_validation_invalid(self):
        """Test invalid latitude validation."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(location_latitude=-91.0)
        
        assert "Latitude must be between -90 and 90" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(location_latitude=91.0)
        
        assert "Latitude must be between -90 and 90" in str(exc_info.value)

    def test_longitude_validation_valid(self):
        """Test valid longitude validation."""
        config_min = WeatherConfig(location_longitude=-180.0)
        config_max = WeatherConfig(location_longitude=180.0)
        config_zero = WeatherConfig(location_longitude=0.0)
        
        assert config_min.location_longitude == -180.0
        assert config_max.location_longitude == 180.0
        assert config_zero.location_longitude == 0.0

    def test_longitude_validation_invalid(self):
        """Test invalid longitude validation."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(location_longitude=-181.0)
        
        assert "Longitude must be between -180 and 180" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(location_longitude=181.0)
        
        assert "Longitude must be between -180 and 180" in str(exc_info.value)

    def test_location_name_validation_valid(self):
        """Test valid location name validation."""
        config = WeatherConfig(location_name="  London  ")
        assert config.location_name == "London"  # Should be stripped

    def test_location_name_validation_invalid(self):
        """Test invalid location name validation."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(location_name="")
        
        assert "Location name cannot be empty" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            WeatherConfig(location_name="   ")
        
        assert "Location name cannot be empty" in str(exc_info.value)

    def test_field_constraints(self):
        """Test field constraints validation."""
        # Test refresh interval constraints
        with pytest.raises(ValidationError):
            WeatherConfig(refresh_interval_minutes=14)  # Below minimum
        
        with pytest.raises(ValidationError):
            WeatherConfig(refresh_interval_minutes=121)  # Above maximum
        
        # Test cache duration constraints
        with pytest.raises(ValidationError):
            WeatherConfig(cache_duration_minutes=4)  # Below minimum
        
        with pytest.raises(ValidationError):
            WeatherConfig(cache_duration_minutes=61)  # Above maximum
        
        # Test max retries constraints
        with pytest.raises(ValidationError):
            WeatherConfig(max_retries=0)  # Below minimum
        
        with pytest.raises(ValidationError):
            WeatherConfig(max_retries=11)  # Above maximum
        
        # Test timeout constraints
        with pytest.raises(ValidationError):
            WeatherConfig(timeout_seconds=4)  # Below minimum
        
        with pytest.raises(ValidationError):
            WeatherConfig(timeout_seconds=31)  # Above maximum

    def test_get_coordinates(self):
        """Test get_coordinates method."""
        config = WeatherConfig(
            location_latitude=40.7128,
            location_longitude=-74.0060
        )
        
        coordinates = config.get_coordinates()
        assert coordinates == (40.7128, -74.0060)

    def test_is_metric_units(self):
        """Test is_metric_units method."""
        config_celsius = WeatherConfig(temperature_unit="celsius")
        config_fahrenheit = WeatherConfig(temperature_unit="fahrenheit")
        
        assert config_celsius.is_metric_units() is True
        assert config_fahrenheit.is_metric_units() is False

    def test_get_cache_duration_seconds(self):
        """Test get_cache_duration_seconds method."""
        config = WeatherConfig(cache_duration_minutes=45)
        
        assert config.get_cache_duration_seconds() == 2700  # 45 * 60

    def test_get_refresh_interval_seconds(self):
        """Test get_refresh_interval_seconds method."""
        config = WeatherConfig(refresh_interval_minutes=30)
        
        assert config.get_refresh_interval_seconds() == 1800  # 30 * 60

    def test_to_summary_dict(self):
        """Test to_summary_dict method."""
        config = WeatherConfig(
            enabled=True,
            location_name="Test City",
            location_latitude=12.3456,
            location_longitude=-65.4321,
            refresh_interval_minutes=45,
            temperature_unit="fahrenheit",
            show_humidity=False
        )
        
        summary = config.to_summary_dict()
        
        assert summary["enabled"] is True
        assert summary["location"] == "Test City"
        assert summary["coordinates"] == "12.3456, -65.4321"
        assert summary["refresh_interval"] == "45 minutes"
        assert summary["temperature_unit"] == "fahrenheit"
        assert summary["show_humidity"] is False
        assert "api_provider" in summary
        assert "config_version" in summary


class TestWeatherConfigValidator:
    """Test cases for WeatherConfigValidator class."""

    def test_validate_coordinates_valid(self):
        """Test valid coordinate validation."""
        assert WeatherConfigValidator.validate_coordinates(0, 0) is True
        assert WeatherConfigValidator.validate_coordinates(-90, -180) is True
        assert WeatherConfigValidator.validate_coordinates(90, 180) is True
        assert WeatherConfigValidator.validate_coordinates(51.5074, -0.1278) is True

    def test_validate_coordinates_invalid(self):
        """Test invalid coordinate validation."""
        assert WeatherConfigValidator.validate_coordinates(-91, 0) is False
        assert WeatherConfigValidator.validate_coordinates(91, 0) is False
        assert WeatherConfigValidator.validate_coordinates(0, -181) is False
        assert WeatherConfigValidator.validate_coordinates(0, 181) is False

    def test_validate_refresh_interval_valid(self):
        """Test valid refresh interval validation."""
        assert WeatherConfigValidator.validate_refresh_interval(15) is True
        assert WeatherConfigValidator.validate_refresh_interval(30) is True
        assert WeatherConfigValidator.validate_refresh_interval(120) is True

    def test_validate_refresh_interval_invalid(self):
        """Test invalid refresh interval validation."""
        assert WeatherConfigValidator.validate_refresh_interval(14) is False
        assert WeatherConfigValidator.validate_refresh_interval(121) is False

    def test_validate_cache_duration_valid(self):
        """Test valid cache duration validation."""
        assert WeatherConfigValidator.validate_cache_duration(5) is True
        assert WeatherConfigValidator.validate_cache_duration(30) is True
        assert WeatherConfigValidator.validate_cache_duration(60) is True

    def test_validate_cache_duration_invalid(self):
        """Test invalid cache duration validation."""
        assert WeatherConfigValidator.validate_cache_duration(4) is False
        assert WeatherConfigValidator.validate_cache_duration(61) is False

    def test_validate_timeout_valid(self):
        """Test valid timeout validation."""
        assert WeatherConfigValidator.validate_timeout(5) is True
        assert WeatherConfigValidator.validate_timeout(15) is True
        assert WeatherConfigValidator.validate_timeout(30) is True

    def test_validate_timeout_invalid(self):
        """Test invalid timeout validation."""
        assert WeatherConfigValidator.validate_timeout(4) is False
        assert WeatherConfigValidator.validate_timeout(31) is False

    def test_validate_config_valid(self):
        """Test valid complete config validation."""
        config = WeatherConfig()
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        
        assert is_valid is True
        assert errors == []

    def test_validate_config_invalid_coordinates(self):
        """Test config validation with invalid coordinates."""
        # Create a valid config first, then modify it to bypass pydantic validation
        config = WeatherConfig()
        config.location_latitude = 91.0  # Bypass pydantic validation for testing
        
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        
        assert is_valid is False
        assert "Invalid coordinates" in errors

    def test_validate_config_invalid_refresh_interval(self):
        """Test config validation with invalid refresh interval."""
        # Create a valid config first, then modify it to bypass pydantic validation
        config = WeatherConfig()
        config.refresh_interval_minutes = 14  # Bypass pydantic validation for testing
        
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Refresh interval must be between 15 and 120 minutes" in errors

    def test_validate_config_invalid_cache_duration(self):
        """Test config validation with invalid cache duration."""
        is_valid = WeatherConfigValidator.validate_cache_duration(4)
        assert is_valid is False

    def test_validate_config_invalid_timeout(self):
        """Test config validation with invalid timeout."""
        is_valid = WeatherConfigValidator.validate_timeout(4)
        assert is_valid is False

    def test_validate_config_empty_location_name(self):
        """Test config validation with empty location name."""
        # Create a config with valid pydantic fields but test validator logic
        config = WeatherConfig(location_name="Test")
        config.location_name = ""  # Bypass pydantic validation for testing
        
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Location name cannot be empty" in errors

    def test_validate_config_invalid_temperature_unit(self):
        """Test config validation with invalid temperature unit."""
        config = WeatherConfig()
        config.temperature_unit = "kelvin"  # Bypass pydantic validation for testing
        
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Temperature unit must be celsius or fahrenheit" in errors

    def test_validate_config_multiple_errors(self):
        """Test config validation with multiple errors."""
        config = WeatherConfig()
        # Bypass pydantic validation to test validator logic
        config.location_name = ""
        config.temperature_unit = "kelvin"
        
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert len(errors) >= 2

    def test_validate_config_all_error_conditions(self):
        """Test config validation covering all error conditions (lines 187, 191, 194, 197)."""
        config = WeatherConfig()
        
        # Test invalid coordinates (line 187)
        config.location_latitude = 91.0
        config.location_longitude = 181.0
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Invalid coordinates" in errors
        
        # Reset coordinates and test refresh interval (line 191)
        config.location_latitude = 45.0
        config.location_longitude = -75.0
        config.refresh_interval_minutes = 14
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Refresh interval must be between 15 and 120 minutes" in errors
        
        # Reset refresh interval and test cache duration (line 194)
        config.refresh_interval_minutes = 30
        config.cache_duration_minutes = 4
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Cache duration must be between 5 and 60 minutes" in errors
        
        # Reset cache duration and test timeout (line 197)
        config.cache_duration_minutes = 30
        config.timeout_seconds = 4
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is False
        assert "Timeout must be between 5 and 30 seconds" in errors


class TestWeatherConfigFactory:
    """Test cases for WeatherConfigFactory class."""

    @patch('src.managers.weather_config.logger')
    def test_create_default_config(self, mock_logger):
        """Test creating default config."""
        config = WeatherConfigFactory.create_default_config()
        
        assert isinstance(config, WeatherConfig)
        assert config.location_name == "London"
        assert config.enabled is True
        mock_logger.info.assert_called_once_with("Creating default weather configuration")

    def test_create_london_config(self):
        """Test creating London config."""
        config = WeatherConfigFactory.create_london_config()
        
        assert isinstance(config, WeatherConfig)
        assert config.location_name == "London"
        assert config.location_latitude == 51.5074
        assert config.location_longitude == -0.1278

    def test_create_waterloo_config(self):
        """Test creating Waterloo config."""
        config = WeatherConfigFactory.create_waterloo_config()
        
        assert isinstance(config, WeatherConfig)
        assert config.location_name == "London Waterloo"
        assert config.location_latitude == 51.5045
        assert config.location_longitude == -0.1097

    @patch('src.managers.weather_config.logger')
    def test_create_custom_config_valid(self, mock_logger):
        """Test creating valid custom config."""
        config = WeatherConfigFactory.create_custom_config(
            name="New York",
            latitude=40.7128,
            longitude=-74.0060,
            temperature_unit="fahrenheit"
        )
        
        assert isinstance(config, WeatherConfig)
        assert config.location_name == "New York"
        assert config.location_latitude == 40.7128
        assert config.location_longitude == -74.0060
        assert config.temperature_unit == "fahrenheit"
        mock_logger.info.assert_called_once_with("Creating custom weather configuration for New York")

    def test_create_custom_config_invalid_coordinates(self):
        """Test creating custom config with invalid coordinates."""
        with pytest.raises(ValueError) as exc_info:
            WeatherConfigFactory.create_custom_config(
                name="Invalid Location",
                latitude=91.0,
                longitude=0.0
            )
        
        assert "Invalid coordinates: 91.0, 0.0" in str(exc_info.value)

    @patch('src.managers.weather_config.logger')
    def test_create_from_dict_valid(self, mock_logger):
        """Test creating config from valid dictionary."""
        config_dict = {
            "location_name": "Test City",
            "location_latitude": 40.0,
            "location_longitude": -74.0,
            "temperature_unit": "celsius"
        }
        
        config = WeatherConfigFactory.create_from_dict(config_dict)
        
        assert isinstance(config, WeatherConfig)
        assert config.location_name == "Test City"
        mock_logger.info.assert_called_once_with("Weather configuration created from dictionary")

    @patch('src.managers.weather_config.logger')
    def test_create_from_dict_invalid(self, mock_logger):
        """Test creating config from invalid dictionary."""
        config_dict = {
            "location_name": "Test City",
            "location_latitude": 91.0,  # Invalid latitude
            "location_longitude": -74.0
        }
        
        with pytest.raises(ValidationError):
            WeatherConfigFactory.create_from_dict(config_dict)
        
        mock_logger.error.assert_called_once()

    @patch('src.managers.weather_config.logger')
    def test_create_from_dict_exception(self, mock_logger):
        """Test creating config from dictionary with exception."""
        config_dict = {
            "temperature_unit": "invalid_unit"
        }
        
        with pytest.raises(ValidationError):
            WeatherConfigFactory.create_from_dict(config_dict)
        
        mock_logger.error.assert_called_once()

    @patch('src.managers.weather_config.logger')
    def test_create_from_dict_validation_error(self, mock_logger):
        """Test creating config from dictionary that passes pydantic but fails custom validation (line 271)."""
        # Create a config dict that will pass pydantic validation but fail custom validation
        config_dict = {
            "location_name": "Test City",
            "location_latitude": 45.0,
            "location_longitude": -75.0,
            "refresh_interval_minutes": 30,
            "cache_duration_minutes": 30,
            "timeout_seconds": 10,
            "temperature_unit": "celsius"
        }
        
        # Mock the validator to return invalid
        with patch.object(WeatherConfigValidator, 'validate_config', return_value=(False, ["Test error"])):
            with pytest.raises(ValueError) as exc_info:
                WeatherConfigFactory.create_from_dict(config_dict)
            
            assert "Invalid configuration: Test error" in str(exc_info.value)
            mock_logger.error.assert_called_once()


class TestWeatherConfigMigrator:
    """Test cases for WeatherConfigMigrator class."""

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    def test_migrate_to_current_version_no_migration_needed(self):
        """Test migration when no migration is needed."""
        config_dict = {
            "location_name": "London",
            "config_version": "2.0.0"
        }
        
        result = WeatherConfigMigrator.migrate_to_current_version(config_dict)
        
        assert result == config_dict

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    @patch('src.managers.weather_config.logger')
    def test_migrate_to_current_version_migration_needed(self, mock_logger):
        """Test migration when migration is needed."""
        config_dict = {
            "location_name": "London",
            "config_version": "1.0.0"
        }
        
        with patch.object(WeatherConfig, 'dict') as mock_dict:
            mock_dict.return_value = {
                "location_name": "London",
                "enabled": True,
                "new_field": "default_value",
                "config_version": "2.0.0"
            }
            
            result = WeatherConfigMigrator.migrate_to_current_version(config_dict)
            
            assert result["config_version"] == "2.0.0"
            assert "new_field" in result
            mock_logger.info.assert_any_call("Migrating weather config from 1.0.0 to 2.0.0")

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    @patch('src.managers.weather_config.logger')
    def test_migrate_to_current_version_missing_fields(self, mock_logger):
        """Test migration with missing fields."""
        config_dict = {
            "location_name": "London"
        }
        
        with patch.object(WeatherConfig, 'dict') as mock_dict:
            mock_dict.return_value = {
                "location_name": "London",
                "enabled": True,
                "missing_field": "default_value",
                "config_version": "2.0.0"
            }
            
            result = WeatherConfigMigrator.migrate_to_current_version(config_dict)
            
            assert "missing_field" in result
            assert result["missing_field"] == "default_value"
            mock_logger.info.assert_any_call("Added missing config field: missing_field = default_value")

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    def test_is_migration_needed_true(self):
        """Test is_migration_needed returns True when migration is needed."""
        config_dict = {"config_version": "1.0.0"}
        
        result = WeatherConfigMigrator.is_migration_needed(config_dict)
        
        assert result is True

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    def test_is_migration_needed_false(self):
        """Test is_migration_needed returns False when no migration is needed."""
        config_dict = {"config_version": "2.0.0"}
        
        result = WeatherConfigMigrator.is_migration_needed(config_dict)
        
        assert result is False

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    def test_is_migration_needed_no_version(self):
        """Test is_migration_needed with no version specified."""
        config_dict = {}
        
        result = WeatherConfigMigrator.is_migration_needed(config_dict)
        
        assert result is True  # Should default to '1.0.0' and need migration


class TestDefaultWeatherConfig:
    """Test cases for default weather config instance."""

    def test_default_weather_config_exists(self):
        """Test that default weather config instance exists."""
        assert default_weather_config is not None
        assert isinstance(default_weather_config, WeatherConfig)

    def test_default_weather_config_is_waterloo(self):
        """Test that default config is Waterloo config."""
        assert default_weather_config.location_name == "London Waterloo"
        assert default_weather_config.location_latitude == 51.5045
        assert default_weather_config.location_longitude == -0.1097


class TestWeatherConfigIntegration:
    """Integration tests for weather configuration."""

    def test_full_config_lifecycle(self):
        """Test complete configuration lifecycle."""
        # Create custom config
        config = WeatherConfigFactory.create_custom_config(
            name="Test Location",
            latitude=45.0,
            longitude=-75.0,
            temperature_unit="fahrenheit",
            refresh_interval_minutes=60
        )
        
        # Validate config
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is True
        assert errors == []
        
        # Test methods
        assert config.get_coordinates() == (45.0, -75.0)
        assert config.is_metric_units() is False
        assert config.get_refresh_interval_seconds() == 3600
        
        # Test summary
        summary = config.to_summary_dict()
        assert summary["location"] == "Test Location"
        assert summary["temperature_unit"] == "fahrenheit"

    def test_config_validation_edge_cases(self):
        """Test configuration validation edge cases."""
        # Test boundary values
        config = WeatherConfig(
            location_latitude=90.0,
            location_longitude=180.0,
            refresh_interval_minutes=15,
            cache_duration_minutes=5,
            timeout_seconds=5,
            max_retries=1
        )
        
        is_valid, errors = WeatherConfigValidator.validate_config(config)
        assert is_valid is True

    @patch('src.managers.weather_config.__weather_version__', '2.0.0')
    def test_migration_integration(self):
        """Test migration integration."""
        old_config = {
            "location_name": "Old Location",
            "config_version": "1.0.0"
        }
        
        # Check if migration is needed
        assert WeatherConfigMigrator.is_migration_needed(old_config) is True
        
        # Perform migration
        migrated = WeatherConfigMigrator.migrate_to_current_version(old_config)
        
        # Verify migration
        assert WeatherConfigMigrator.is_migration_needed(migrated) is False
        
        # Create config from migrated data
        config = WeatherConfigFactory.create_from_dict(migrated)
        assert isinstance(config, WeatherConfig)