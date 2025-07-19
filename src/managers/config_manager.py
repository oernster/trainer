"""
Configuration management for the Train Times application.
Author: Oliver Ernster

This module handles loading, saving, and validating application configuration
using Pydantic models for type safety and validation.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from version import __version__, __app_display_name__
from .weather_config import WeatherConfig, WeatherConfigFactory, WeatherConfigMigrator
from .astronomy_config import AstronomyConfig

logger = logging.getLogger(__name__)


class APIConfig(BaseModel):
    """Configuration for Transport API access."""

    app_id: str = Field(..., description="Transport API app ID")
    app_key: str = Field(..., description="Transport API app key")
    base_url: str = "https://transportapi.com/v3/uk"
    timeout_seconds: int = 10
    max_retries: int = 3
    rate_limit_per_minute: int = 30


class StationConfig(BaseModel):
    """Configuration for station names (codes removed)."""

    from_code: str = "Fleet"  # Now stores station name, not code
    from_name: str = "Fleet"
    to_code: str = "London Waterloo"  # Now stores station name, not code
    to_name: str = "London Waterloo"
    via_stations: List[str] = []
    route_auto_fixed: bool = False
    departure_time: str = ""  # Optional departure time in HH:MM format
    route_path: List[str] = []  # Store the complete route path for persistence


class RefreshConfig(BaseModel):
    """Configuration for data refresh settings."""

    auto_enabled: bool = True
    interval_minutes: int = 30
    manual_enabled: bool = True


class DisplayConfig(BaseModel):
    """Configuration for display settings."""

    max_trains: int = 100  # Increased to accommodate all railway lines
    time_window_hours: int = 16
    theme: str = "dark"  # Default to dark theme - "dark" or "light"


class UIConfig(BaseModel):
    """Configuration for UI state persistence."""
    
    weather_widget_visible: bool = True
    astronomy_widget_visible: bool = True
    
    # Window sizing per widget state (width, height)
    window_size_both_visible: tuple[int, int] = (1100, 1200)  # Both weather and astronomy visible
    window_size_weather_only: tuple[int, int] = (1100, 800)   # Only weather visible
    window_size_astronomy_only: tuple[int, int] = (1100, 750) # Only astronomy visible
    window_size_trains_only: tuple[int, int] = (1100, 500)    # Only trains visible


class ConfigData(BaseModel):
    """Main configuration data model with weather and astronomy integration."""

    api: APIConfig
    stations: StationConfig
    refresh: RefreshConfig
    display: DisplayConfig
    ui: UIConfig = UIConfig()  # Default UI state
    weather: Optional[WeatherConfig] = None
    astronomy: Optional[AstronomyConfig] = None
    
    # Route preferences
    optimize_for_speed: bool = True
    show_intermediate_stations: bool = True
    avoid_london: bool = False
    prefer_direct: bool = False
    avoid_walking: bool = False
    max_walking_distance_km: float = 1.0  # Default threshold of 1.0km
    max_changes: int = 3
    max_journey_time: int = 8
    train_lookahead_hours: int = 16  # Configurable train look-ahead time in hours

    def __init__(self, **data):
        """Initialize ConfigData with optional weather, astronomy, and UI config."""
        # If weather config is not provided, create default
        if "weather" not in data or data["weather"] is None:
            data["weather"] = WeatherConfigFactory.create_waterloo_config()

        # If astronomy config is not provided, create default
        if "astronomy" not in data or data["astronomy"] is None:
            data["astronomy"] = AstronomyConfig.create_default()
            
        # If UI config is not provided, create default (for backward compatibility)
        if "ui" not in data or data["ui"] is None:
            data["ui"] = UIConfig()

        super().__init__(**data)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class ConfigManager:
    """
    Manages application configuration with file persistence.

    Handles loading configuration from JSON files, creating default
    configurations, and saving changes back to disk.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file. If None, uses AppData on Windows
        """
        if config_path is None:
            self.config_path = self.get_default_config_path()
        else:
            self.config_path = Path(config_path)
        self.config: Optional[ConfigData] = None

        # Log the config path for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"ConfigManager initialized with path: {self.config_path}")

    @staticmethod
    def get_default_config_path() -> Path:
        """
        Get the default configuration file path.

        On Windows, uses AppData/Roaming/Trainer/config.json
        On Linux, uses XDG_CONFIG_HOME/Trainer/config.json or ~/.config/Trainer/config.json
        For Flatpak, uses the appropriate XDG directory

        Returns:
            Path: Default configuration file path
        """
        if os.name == "nt":  # Windows
            appdata = os.environ.get("APPDATA")
            if appdata:
                config_dir = Path(appdata) / "Trainer"
                config_dir.mkdir(parents=True, exist_ok=True)
                return config_dir / "config.json"
        else:  # Linux/Unix
            # Check for XDG_CONFIG_HOME (standard for Linux desktop apps)
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "Trainer"
            else:
                # Fallback to ~/.config/Trainer (Linux standard)
                config_dir = Path.home() / ".config" / "Trainer"
            
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / "config.json"

        # Fallback to current directory for development
        return Path("config.json")

    def install_default_config_to_appdata(self) -> bool:
        """
        Install default configuration to AppData directory on Windows.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.name != "nt":  # Not Windows
                return False

            appdata = os.environ.get("APPDATA")
            if not appdata:
                return False

            # Create Trainer directory in AppData
            config_dir = Path(appdata) / "Trainer"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Create default config in AppData
            appdata_config_path = config_dir / "config.json"

            # Only create if it doesn't exist
            if not appdata_config_path.exists():
                default_config = ConfigData(
                    api=APIConfig(
                        app_id="YOUR_APP_ID_HERE", app_key="YOUR_APP_KEY_HERE"
                    ),
                    stations=StationConfig(),
                    refresh=RefreshConfig(),
                    display=DisplayConfig(),
                    ui=UIConfig(),
                    weather=WeatherConfigFactory.create_waterloo_config(),
                    astronomy=AstronomyConfig.create_default(),
                )

                with open(appdata_config_path, "w", encoding="utf-8") as f:
                    json.dump(
                        default_config.model_dump(), f, indent=2, ensure_ascii=False
                    )

                return True

            return True  # Already exists

        except Exception as e:
            print(f"Failed to install config to AppData: {e}")
            return False

    def load_config(self) -> ConfigData:
        """
        Load configuration from file.

        If the configuration file doesn't exist, creates a default one.

        Returns:
            ConfigData: The loaded configuration

        Raises:
            ConfigurationError: If the configuration file is invalid
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Loading config from: {self.config_path}")

        if not self.config_path.exists():
            logger.info(
                f"Config file doesn't exist, creating default at: {self.config_path}"
            )
            self.create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.config = ConfigData(**data)
            logger.debug(f"Successfully loaded config from: {self.config_path}")
            return self.config
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {e}")

    def save_config(self, config: ConfigData, force_flush: bool = False) -> bool:
        """
        Save configuration to file with optional forced flush.
        
        Args:
            config: Configuration data to save
            force_flush: If True, forces an fsync to ensure data is written to disk
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Saving config to: {self.config_path}")

        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Config directory ensured: {self.config_path.parent}")
            
            # Serialize config to JSON
            config_json = config.model_dump()
            
            # Ensure route_path is properly serialized if present
            if 'stations' in config_json and 'route_path' in config_json['stations']:
                # Ensure it's a list of strings
                route_path = config_json['stations']['route_path']
                if not isinstance(route_path, list):
                    logger.warning(f"Invalid route_path type: {type(route_path)}, converting to list")
                    config_json['stations']['route_path'] = []
                elif route_path and len(route_path) >= 2:
                    logger.info(f"Saving route path with {len(route_path)} stations")

            # Write to file with proper encoding
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_json, f, indent=2, ensure_ascii=False)
                
                # Force flush to disk if requested
                if force_flush:
                    f.flush()
                    os.fsync(f.fileno())
                    logger.info("Forced flush to disk to ensure persistence")
                    
            self.config = config
            logger.info(f"Successfully saved config to: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            return False

    def create_default_config(self) -> None:
        """Create a default configuration file."""
        default_config = ConfigData(
            api=APIConfig(app_id="YOUR_APP_ID_HERE", app_key="YOUR_APP_KEY_HERE"),
            stations=StationConfig(),
            refresh=RefreshConfig(),
            display=DisplayConfig(),
            ui=UIConfig(),
            weather=WeatherConfigFactory.create_waterloo_config(),
            astronomy=AstronomyConfig.create_default(),
        )
        self.save_config(default_config)

    def update_theme(self, theme: str) -> None:
        """
        Update the theme setting and save to file.

        Args:
            theme: Theme name ("dark" or "light")
        """
        if self.config is None:
            self.load_config()

        if self.config and theme in ["dark", "light"]:
            self.config.display.theme = theme
            self.save_config(self.config)

    def update_refresh_interval(self, minutes: int) -> None:
        """
        Update the refresh interval and save to file.

        Args:
            minutes: Refresh interval in minutes
        """
        if self.config is None:
            self.load_config()

        if self.config and minutes > 0:
            self.config.refresh.interval_minutes = minutes
            self.save_config(self.config)

    def update_time_window(self, hours: int) -> None:
        """
        Update the time window setting and save to file.

        Args:
            hours: Time window in hours (1-24)
        """
        if self.config is None:
            self.load_config()

        if self.config and 1 <= hours <= 24:
            self.config.display.time_window_hours = hours
            self.save_config(self.config)

    def validate_api_credentials(self) -> bool:
        """
        Check if API credentials are configured.

        Returns:
            bool: True if credentials are set, False otherwise
        """
        if self.config is None:
            self.load_config()

        if not self.config:
            return False

        return (
            self.config.api.app_id != "YOUR_APP_ID_HERE"
            and self.config.api.app_key != "YOUR_APP_KEY_HERE"
            and bool(self.config.api.app_id)
            and bool(self.config.api.app_key)
        )

    def get_config_summary(self) -> dict:
        """
        Get a summary of current configuration for display.

        Returns:
            dict: Configuration summary
        """
        if self.config is None:
            self.load_config()

        if not self.config:
            return {"error": "Configuration not loaded"}

        summary = {
            "app_version": __version__,
            "theme": self.config.display.theme,
            "refresh_interval": f"{self.config.refresh.interval_minutes} minutes",
            "time_window": f"{self.config.display.time_window_hours} hours",
            "max_trains": self.config.display.max_trains,
            "auto_refresh": (
                "Enabled" if self.config.refresh.auto_enabled else "Disabled"
            ),
            "api_configured": "Yes" if self.validate_api_credentials() else "No",
            "route": f"{self.config.stations.from_name} → {self.config.stations.to_name}",
        }

        # Add weather configuration summary
        if self.config.weather:
            weather_summary = self.config.weather.to_summary_dict()
            summary.update(
                {
                    "weather_enabled": weather_summary["enabled"],
                    "weather_location": weather_summary["location"],
                    "weather_refresh": weather_summary["refresh_interval"],
                    "weather_provider": weather_summary["api_provider"],
                }
            )
        else:
            summary["weather_enabled"] = False

        return summary

    def update_weather_config(self, **kwargs) -> None:
        """
        Update weather configuration settings.

        Args:
            **kwargs: Weather configuration parameters to update
        """
        if self.config is None:
            self.load_config()

        if self.config and self.config.weather:
            # Create updated weather config
            current_weather_dict = self.config.weather.model_dump()
            current_weather_dict.update(kwargs)

            # Validate and create new weather config
            try:
                new_weather_config = WeatherConfig(**current_weather_dict)
                self.config.weather = new_weather_config
                self.save_config(self.config)
                logger.info(f"Weather configuration updated: {kwargs}")
            except Exception as e:
                logger.error(f"Failed to update weather config: {e}")
                raise ConfigurationError(f"Invalid weather configuration: {e}")

    def get_weather_config(self) -> Optional[WeatherConfig]:
        """
        Get current weather configuration.

        Returns:
            WeatherConfig or None if not available
        """
        if self.config is None:
            self.load_config()

        if self.config:
            return self.config.weather
        return None

    def is_weather_enabled(self) -> bool:
        """
        Check if weather integration is enabled.

        Returns:
            bool: True if weather is enabled
        """
        weather_config = self.get_weather_config()
        return weather_config is not None and weather_config.enabled

    def migrate_config_if_needed(self) -> bool:
        """
        Migrate configuration to current version if needed.

        Returns:
            bool: True if migration was performed
        """
        if self.config is None:
            return False

        try:
            config_dict = self.config.model_dump()

            # Check if weather config migration is needed
            if "weather" in config_dict and config_dict["weather"]:
                weather_dict = config_dict["weather"]
                if WeatherConfigMigrator.is_migration_needed(weather_dict):
                    migrated_weather = WeatherConfigMigrator.migrate_to_current_version(
                        weather_dict
                    )
                    config_dict["weather"] = migrated_weather

                    # Recreate config with migrated data
                    self.config = ConfigData(**config_dict)
                    self.save_config(self.config)
                    logger.info("Configuration migrated to current version")
                    return True
            elif "weather" not in config_dict or not config_dict["weather"]:
                # Add weather config if missing or None
                config_dict["weather"] = (
                    WeatherConfigFactory.create_waterloo_config().model_dump()
                )
                self.config = ConfigData(**config_dict)
                self.save_config(self.config)
                logger.info("Added weather configuration to existing config")
                return True

        except Exception as e:
            logger.error(f"Configuration migration failed: {e}")

        return False
