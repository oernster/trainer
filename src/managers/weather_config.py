"""
Weather configuration management for the Trainer application.
Author: Oliver Ernster

This module extends the configuration system with weather-specific settings,
following solid Object-Oriented design principles.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from version import (
    __weather_version__, 
    __weather_api_provider__, 
    __weather_api_url__,
    get_weather_info
)

logger = logging.getLogger(__name__)


class WeatherConfig(BaseModel):
    """
    Configuration for weather data integration.
    
    Follows Single Responsibility Principle - only responsible for
    weather configuration data and validation.
    """
    
    # Core weather settings
    enabled: bool = Field(default=True, description="Enable weather integration")
    
    # Location settings (London Waterloo coordinates)
    location_latitude: float = Field(default=51.5074, description="Location latitude")
    location_longitude: float = Field(default=-0.1278, description="Location longitude") 
    location_name: str = Field(default="London", description="Location display name")
    
    # Refresh and display settings
    refresh_interval_minutes: int = Field(
        default=30, 
        ge=15, 
        le=120, 
        description="Weather refresh interval in minutes"
    )
    show_humidity: bool = Field(default=True, description="Show humidity information")
    temperature_unit: str = Field(
        default="celsius", 
        description="Temperature unit (celsius or fahrenheit)"
    )
    
    # Advanced settings
    cache_duration_minutes: int = Field(
        default=30,
        ge=5,
        le=60,
        description="Weather data cache duration"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum API retry attempts"
    )
    timeout_seconds: int = Field(
        default=10,
        ge=5,
        le=30,
        description="API request timeout"
    )
    
    # Metadata
    api_provider: str = Field(
        default=__weather_api_provider__,
        description="Weather API provider name"
    )
    api_url: str = Field(
        default=__weather_api_url__,
        description="Weather API base URL"
    )
    config_version: str = Field(
        default=__weather_version__,
        description="Weather configuration version"
    )
    
    @field_validator('temperature_unit')
    @classmethod
    def validate_temperature_unit(cls, v):
        """Validate temperature unit."""
        if v not in ['celsius', 'fahrenheit']:
            raise ValueError('Temperature unit must be celsius or fahrenheit')
        return v
    
    @field_validator('location_latitude')
    @classmethod
    def validate_latitude(cls, v):
        """Validate latitude range."""
        if not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @field_validator('location_longitude')
    @classmethod
    def validate_longitude(cls, v):
        """Validate longitude range."""
        if not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v
    
    @field_validator('location_name')
    @classmethod
    def validate_location_name(cls, v):
        """Validate location name is not empty."""
        if not v.strip():
            raise ValueError('Location name cannot be empty')
        return v.strip()
    
    def get_coordinates(self) -> tuple[float, float]:
        """Get location coordinates as tuple."""
        return (self.location_latitude, self.location_longitude)
    
    def is_metric_units(self) -> bool:
        """Check if using metric temperature units."""
        return self.temperature_unit == "celsius"
    
    def get_cache_duration_seconds(self) -> int:
        """Get cache duration in seconds."""
        return self.cache_duration_minutes * 60
    
    def get_refresh_interval_seconds(self) -> int:
        """Get refresh interval in seconds."""
        return self.refresh_interval_minutes * 60
    
    def to_summary_dict(self) -> dict:
        """Get configuration summary for display."""
        return {
            "enabled": self.enabled,
            "location": self.location_name,
            "coordinates": f"{self.location_latitude:.4f}, {self.location_longitude:.4f}",
            "refresh_interval": f"{self.refresh_interval_minutes} minutes",
            "temperature_unit": self.temperature_unit,
            "show_humidity": self.show_humidity,
            "api_provider": self.api_provider,
            "config_version": self.config_version
        }


class WeatherConfigValidator:
    """
    Validator for weather configuration.
    
    Follows Single Responsibility Principle - only responsible for validation logic.
    """
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """Validate coordinate pair."""
        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)
    
    @staticmethod
    def validate_refresh_interval(minutes: int) -> bool:
        """Validate refresh interval is reasonable."""
        return 15 <= minutes <= 120
    
    @staticmethod
    def validate_cache_duration(minutes: int) -> bool:
        """Validate cache duration is reasonable."""
        return 5 <= minutes <= 60
    
    @staticmethod
    def validate_timeout(seconds: int) -> bool:
        """Validate timeout is reasonable."""
        return 5 <= seconds <= 30
    
    @classmethod
    def validate_config(cls, config: WeatherConfig) -> tuple[bool, list[str]]:
        """
        Validate complete weather configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate coordinates
        if not cls.validate_coordinates(config.location_latitude, config.location_longitude):
            errors.append("Invalid coordinates")
        
        # Validate intervals
        if not cls.validate_refresh_interval(config.refresh_interval_minutes):
            errors.append("Refresh interval must be between 15 and 120 minutes")
        
        if not cls.validate_cache_duration(config.cache_duration_minutes):
            errors.append("Cache duration must be between 5 and 60 minutes")
        
        if not cls.validate_timeout(config.timeout_seconds):
            errors.append("Timeout must be between 5 and 30 seconds")
        
        # Validate location name
        if not config.location_name.strip():
            errors.append("Location name cannot be empty")
        
        # Validate temperature unit
        if config.temperature_unit not in ['celsius', 'fahrenheit']:
            errors.append("Temperature unit must be celsius or fahrenheit")
        
        return len(errors) == 0, errors


class WeatherConfigFactory:
    """
    Factory for creating weather configurations.
    
    Implements Factory pattern for configuration creation.
    """
    
    @staticmethod
    def create_default_config() -> WeatherConfig:
        """Create default weather configuration."""
        logger.info("Creating default weather configuration")
        return WeatherConfig()
    
    @staticmethod
    def create_london_config() -> WeatherConfig:
        """Create configuration for London."""
        return WeatherConfig(
            location_name="London",
            location_latitude=51.5074,
            location_longitude=-0.1278
        )
    
    @staticmethod
    def create_waterloo_config() -> WeatherConfig:
        """Create configuration for London Waterloo area."""
        return WeatherConfig(
            location_name="London Waterloo",
            location_latitude=51.5045,
            location_longitude=-0.1097
        )
    
    @staticmethod
    def create_custom_config(
        name: str,
        latitude: float,
        longitude: float,
        **kwargs
    ) -> WeatherConfig:
        """Create custom weather configuration."""
        config_data = {
            "location_name": name,
            "location_latitude": latitude,
            "location_longitude": longitude,
            **kwargs
        }
        
        # Validate coordinates before creating
        if not WeatherConfigValidator.validate_coordinates(latitude, longitude):
            raise ValueError(f"Invalid coordinates: {latitude}, {longitude}")
        
        logger.info(f"Creating custom weather configuration for {name}")
        return WeatherConfig(**config_data)
    
    @staticmethod
    def create_from_dict(config_dict: dict) -> WeatherConfig:
        """Create configuration from dictionary."""
        try:
            config = WeatherConfig(**config_dict)
            is_valid, errors = WeatherConfigValidator.validate_config(config)
            
            if not is_valid:
                raise ValueError(f"Invalid configuration: {', '.join(errors)}")
            
            logger.info("Weather configuration created from dictionary")
            return config
            
        except Exception as e:
            logger.error(f"Failed to create weather config from dict: {e}")
            raise


class WeatherConfigMigrator:
    """
    Handles migration of weather configuration between versions.
    
    Follows Open/Closed Principle - can be extended for new migrations.
    """
    
    @staticmethod
    def migrate_to_current_version(config_dict: dict) -> dict:
        """Migrate configuration to current version."""
        current_version = __weather_version__
        config_version = config_dict.get('config_version', '1.0.0')
        
        if config_version == current_version:
            return config_dict
        
        logger.info(f"Migrating weather config from {config_version} to {current_version}")
        
        # Add migration logic here as needed
        migrated_config = config_dict.copy()
        migrated_config['config_version'] = current_version
        
        # Ensure all required fields exist with defaults
        defaults = WeatherConfig().dict()
        for key, default_value in defaults.items():
            if key not in migrated_config:
                migrated_config[key] = default_value
                logger.info(f"Added missing config field: {key} = {default_value}")
        
        return migrated_config
    
    @staticmethod
    def is_migration_needed(config_dict: dict) -> bool:
        """Check if configuration needs migration."""
        current_version = __weather_version__
        config_version = config_dict.get('config_version', '1.0.0')
        return config_version != current_version


# Default weather configuration instance
default_weather_config = WeatherConfigFactory.create_waterloo_config()