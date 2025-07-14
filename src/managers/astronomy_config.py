"""
Astronomy configuration management for the Trainer application.
Author: Oliver Ernster

This module handles astronomy-specific configuration with proper validation,
defaults, and Object-Oriented design principles.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class AstronomyDisplayConfig:
    """Configuration for astronomy display preferences."""

    show_in_forecast: bool = True
    default_expanded: bool = False
    max_events_per_day: int = 3
    icon_size: str = "medium"  # small, medium, large
    show_event_times: bool = True
    show_visibility_info: bool = True
    compact_mode: bool = False
    animation_enabled: bool = True

    def __post_init__(self):
        """Validate display configuration."""
        if self.max_events_per_day < 1 or self.max_events_per_day > 10:
            raise ValueError("max_events_per_day must be between 1 and 10")

        if self.icon_size not in ["small", "medium", "large"]:
            raise ValueError("icon_size must be 'small', 'medium', or 'large'")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AstronomyDisplayConfig":
        """Create display config from dictionary."""
        return cls(
            show_in_forecast=data.get("show_in_forecast", True),
            default_expanded=data.get("default_expanded", False),
            max_events_per_day=data.get("max_events_per_day", 3),
            icon_size=data.get("icon_size", "medium"),
            show_event_times=data.get("show_event_times", True),
            show_visibility_info=data.get("show_visibility_info", True),
            compact_mode=data.get("compact_mode", False),
            animation_enabled=data.get("animation_enabled", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert display config to dictionary."""
        return {
            "show_in_forecast": self.show_in_forecast,
            "default_expanded": self.default_expanded,
            "max_events_per_day": self.max_events_per_day,
            "icon_size": self.icon_size,
            "show_event_times": self.show_event_times,
            "show_visibility_info": self.show_visibility_info,
            "compact_mode": self.compact_mode,
            "animation_enabled": self.animation_enabled,
        }


@dataclass
class AstronomyCacheConfig:
    """Configuration for astronomy data caching."""

    duration_hours: int = 6
    max_entries: int = 100
    cleanup_interval_hours: int = 24
    persist_to_disk: bool = True
    cache_directory: Optional[str] = None

    def __post_init__(self):
        """Validate cache configuration."""
        if self.duration_hours < 1 or self.duration_hours > 168:  # 1 hour to 1 week
            raise ValueError("duration_hours must be between 1 and 168")

        if self.max_entries < 10 or self.max_entries > 1000:
            raise ValueError("max_entries must be between 10 and 1000")

        if self.cleanup_interval_hours < 1 or self.cleanup_interval_hours > 168:
            raise ValueError("cleanup_interval_hours must be between 1 and 168")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AstronomyCacheConfig":
        """Create cache config from dictionary."""
        return cls(
            duration_hours=data.get("duration_hours", 6),
            max_entries=data.get("max_entries", 100),
            cleanup_interval_hours=data.get("cleanup_interval_hours", 24),
            persist_to_disk=data.get("persist_to_disk", True),
            cache_directory=data.get("cache_directory"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert cache config to dictionary."""
        return {
            "duration_hours": self.duration_hours,
            "max_entries": self.max_entries,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "persist_to_disk": self.persist_to_disk,
            "cache_directory": self.cache_directory,
        }

    def get_cache_duration_seconds(self) -> int:
        """Get cache duration in seconds."""
        return self.duration_hours * 3600


@dataclass
class AstronomyServiceConfig:
    """Configuration for individual NASA API services."""

    apod: bool = True  # Astronomy Picture of the Day
    neows: bool = True  # Near Earth Object Web Service
    iss: bool = True  # International Space Station
    epic: bool = False  # Earth Polychromatic Imaging Camera
    mars_weather: bool = False  # Mars Weather Service
    exoplanets: bool = False  # Exoplanet Archive

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AstronomyServiceConfig":
        """Create service config from dictionary."""
        return cls(
            apod=data.get("apod", True),
            neows=data.get("neows", True),
            iss=data.get("iss", True),
            epic=data.get("epic", False),
            mars_weather=data.get("mars_weather", False),
            exoplanets=data.get("exoplanets", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert service config to dictionary."""
        return {
            "apod": self.apod,
            "neows": self.neows,
            "iss": self.iss,
            "epic": self.epic,
            "mars_weather": self.mars_weather,
            "exoplanets": self.exoplanets,
        }

    def get_enabled_services(self) -> List[str]:
        """Get list of enabled service names."""
        enabled = []
        if self.apod:
            enabled.append("apod")
        if self.neows:
            enabled.append("neows")
        if self.iss:
            enabled.append("iss")
        if self.epic:
            enabled.append("epic")
        if self.mars_weather:
            enabled.append("mars_weather")
        if self.exoplanets:
            enabled.append("exoplanets")
        return enabled

    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a specific service is enabled."""
        service_map = {
            "apod": self.apod,
            "neows": self.neows,
            "iss": self.iss,
            "epic": self.epic,
            "mars_weather": self.mars_weather,
            "exoplanets": self.exoplanets,
        }
        return service_map.get(service_name, False)


@dataclass
class AstronomyConfig:
    """
    Complete astronomy configuration.

    Follows Single Responsibility Principle - only responsible for
    astronomy configuration management and validation.
    """

    enabled: bool = True  # Default to enabled since no API required
    location_name: str = "London"
    location_latitude: float = 51.5074
    location_longitude: float = -0.1278
    timezone: str = "Europe/London"
    # Removed API-related fields: nasa_api_key, timeout_seconds, max_retries, retry_delay_seconds
    # Removed update_interval_minutes since we're using static content
    display: AstronomyDisplayConfig = field(default_factory=AstronomyDisplayConfig)
    cache: AstronomyCacheConfig = field(default_factory=AstronomyCacheConfig)
    # New field for link preferences
    enabled_link_categories: List[str] = field(default_factory=lambda: [
        "observatory", "space_agency", "tonight_sky"
    ])

    def __post_init__(self):
        """Validate astronomy configuration."""
        # Validate location coordinates
        if not (-90 <= self.location_latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.location_latitude}")
        if not (-180 <= self.location_longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.location_longitude}")

        # Validate location name
        if not self.location_name.strip():
            raise ValueError("Location name cannot be empty")

        # Validate enabled link categories
        if self.enabled and not self.enabled_link_categories:
            logger.warning("Astronomy is enabled but no link categories are enabled")

        # Validate link categories are valid
        valid_categories = [
            "observatory", "space_agency", "astronomy_tool", "educational",
            "live_data", "community", "tonight_sky", "moon_info"
        ]
        for category in self.enabled_link_categories:
            if category not in valid_categories:
                logger.warning(f"Unknown link category: {category}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AstronomyConfig":
        """Create astronomy config from dictionary."""
        display_data = data.get("display", {})
        cache_data = data.get("cache", {})

        return cls(
            enabled=data.get("enabled", True),  # Default to enabled for API-free approach
            location_name=data.get("location_name", "London"),
            location_latitude=data.get("location_latitude", 51.5074),
            location_longitude=data.get("location_longitude", -0.1278),
            timezone=data.get("timezone", "Europe/London"),
            display=AstronomyDisplayConfig.from_dict(display_data),
            cache=AstronomyCacheConfig.from_dict(cache_data),
            enabled_link_categories=data.get("enabled_link_categories", [
                "observatory", "space_agency", "tonight_sky"
            ]),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert astronomy config to dictionary."""
        return {
            "enabled": self.enabled,
            "location_name": self.location_name,
            "location_latitude": self.location_latitude,
            "location_longitude": self.location_longitude,
            "timezone": self.timezone,
            "display": self.display.to_dict(),
            "cache": self.cache.to_dict(),
            "enabled_link_categories": self.enabled_link_categories,
        }

    @classmethod
    def create_default(cls) -> "AstronomyConfig":
        """Create default astronomy configuration."""
        return cls()

    @classmethod
    def from_file(cls, config_path: Path) -> "AstronomyConfig":
        """Load astronomy configuration from JSON file."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract astronomy section
            astronomy_data = data.get("astronomy", {})
            return cls.from_dict(astronomy_data)

        except FileNotFoundError:
            logger.warning(f"Astronomy config file not found: {config_path}")
            return cls.create_default()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in astronomy config: {e}")
            raise ValueError(f"Invalid astronomy configuration file: {e}")
        except Exception as e:
            logger.error(f"Error loading astronomy config: {e}")
            raise

    def save_to_file(self, config_path: Path) -> None:
        """Save astronomy configuration to JSON file."""
        try:
            # Load existing config if it exists
            existing_data = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)

            # Update astronomy section
            existing_data["astronomy"] = self.to_dict()

            # Save updated config
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Astronomy configuration saved to {config_path}")

        except Exception as e:
            logger.error(f"Error saving astronomy config: {e}")
            raise

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Check location
        if not self.location_name.strip():
            issues.append("Location name cannot be empty")

        # Check coordinates
        if not (-90 <= self.location_latitude <= 90):
            issues.append(f"Invalid latitude: {self.location_latitude}")
        if not (-180 <= self.location_longitude <= 180):
            issues.append(f"Invalid longitude: {self.location_longitude}")

        # Check if at least one link category is enabled
        if self.enabled and not self.enabled_link_categories:
            issues.append("At least one link category must be enabled when astronomy is enabled")

        # Validate link categories
        valid_categories = [
            "observatory", "space_agency", "astronomy_tool", "educational",
            "live_data", "community", "tonight_sky", "moon_info"
        ]
        for category in self.enabled_link_categories:
            if category not in valid_categories:
                issues.append(f"Unknown link category: {category}")

        return issues

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0

    def get_location_tuple(self) -> tuple[float, float]:
        """Get location as (latitude, longitude) tuple."""
        return (self.location_latitude, self.location_longitude)

    def get_cache_duration_seconds(self) -> int:
        """Get cache duration in seconds."""
        return self.cache.get_cache_duration_seconds()

    def get_enabled_link_categories_count(self) -> int:
        """Get number of enabled link categories."""
        return len(self.enabled_link_categories)

    def is_link_category_enabled(self, category: str) -> bool:
        """Check if a specific link category is enabled."""
        return category in self.enabled_link_categories

    def add_link_category(self, category: str) -> None:
        """Add a link category to enabled list."""
        if category not in self.enabled_link_categories:
            self.enabled_link_categories.append(category)

    def remove_link_category(self, category: str) -> None:
        """Remove a link category from enabled list."""
        if category in self.enabled_link_categories:
            self.enabled_link_categories.remove(category)

    def __str__(self) -> str:
        """String representation of astronomy config."""
        status = "enabled" if self.enabled else "disabled"
        categories_count = self.get_enabled_link_categories_count()
        return f"AstronomyConfig({status}, {categories_count} link categories, {self.location_name})"


class AstronomyConfigManager:
    """
    Manager for astronomy configuration operations.

    Follows Single Responsibility Principle - only responsible for
    configuration file management and validation.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize astronomy config manager."""
        self.config_path = config_path or Path("config.json")
        self._config: Optional[AstronomyConfig] = None
        logger.debug(f"AstronomyConfigManager initialized with path: {self.config_path}")

    def load_config(self) -> AstronomyConfig:
        """Load astronomy configuration from file."""
        try:
            self._config = AstronomyConfig.from_file(self.config_path)
            logger.info("Astronomy configuration loaded successfully")
            return self._config
        except Exception as e:
            logger.error(f"Failed to load astronomy configuration: {e}")
            # Return default config on error
            self._config = AstronomyConfig.create_default()
            return self._config

    def save_config(self, config: AstronomyConfig) -> None:
        """Save astronomy configuration to file."""
        try:
            config.save_to_file(self.config_path)
            self._config = config
            logger.info("Astronomy configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save astronomy configuration: {e}")
            raise

    def get_config(self) -> AstronomyConfig:
        """Get current astronomy configuration."""
        if self._config is None:
            return self.load_config()
        return self._config

    def validate_config(self) -> List[str]:
        """Validate current configuration."""
        config = self.get_config()
        return config.validate()

    def is_config_valid(self) -> bool:
        """Check if current configuration is valid."""
        return len(self.validate_config()) == 0

    def reset_to_default(self) -> AstronomyConfig:
        """Reset configuration to default values."""
        self._config = AstronomyConfig.create_default()
        return self._config

    def update_api_key(self, api_key: str) -> None:
        """Update NASA API key."""
        config = self.get_config()
        # Create new config with updated API key (immutable pattern)
        updated_config = AstronomyConfig(
            enabled=config.enabled,
            nasa_api_key=api_key,
            location_name=config.location_name,
            location_latitude=config.location_latitude,
            location_longitude=config.location_longitude,
            timezone=config.timezone,
            update_interval_minutes=config.update_interval_minutes,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            retry_delay_seconds=config.retry_delay_seconds,
            services=config.services,
            display=config.display,
            cache=config.cache,
        )
        self.save_config(updated_config)

    def update_location(self, name: str, latitude: float, longitude: float) -> None:
        """Update location settings."""
        config = self.get_config()
        # Create new config with updated location (immutable pattern)
        updated_config = AstronomyConfig(
            enabled=config.enabled,
            nasa_api_key=config.nasa_api_key,
            location_name=name,
            location_latitude=latitude,
            location_longitude=longitude,
            timezone=config.timezone,
            update_interval_minutes=config.update_interval_minutes,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            retry_delay_seconds=config.retry_delay_seconds,
            services=config.services,
            display=config.display,
            cache=config.cache,
        )
        self.save_config(updated_config)

    def toggle_service(self, service_name: str, enabled: bool) -> None:
        """Toggle a specific astronomy service."""
        config = self.get_config()

        # Update service configuration
        services_dict = config.services.to_dict()
        if service_name in services_dict:
            services_dict[service_name] = enabled
            new_services = AstronomyServiceConfig.from_dict(services_dict)

            # Create new config with updated services
            updated_config = AstronomyConfig(
                enabled=config.enabled,
                nasa_api_key=config.nasa_api_key,
                location_name=config.location_name,
                location_latitude=config.location_latitude,
                location_longitude=config.location_longitude,
                timezone=config.timezone,
                update_interval_minutes=config.update_interval_minutes,
                timeout_seconds=config.timeout_seconds,
                max_retries=config.max_retries,
                retry_delay_seconds=config.retry_delay_seconds,
                services=new_services,
                display=config.display,
                cache=config.cache,
            )
            self.save_config(updated_config)
        else:
            raise ValueError(f"Unknown astronomy service: {service_name}")
