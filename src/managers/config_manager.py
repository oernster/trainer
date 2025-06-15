"""
Configuration management for the Train Times application.
Author: Oliver Ernster

This module handles loading, saving, and validating application configuration
using Pydantic models for type safety and validation.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """Configuration for Transport API access."""

    app_id: str = Field(..., description="Transport API app ID")
    app_key: str = Field(..., description="Transport API app key")
    base_url: str = "https://transportapi.com/v3/uk"
    timeout_seconds: int = 10
    max_retries: int = 3
    rate_limit_per_minute: int = 30


class StationConfig(BaseModel):
    """Configuration for station codes and names."""

    from_code: str = "FLE"
    from_name: str = "Fleet"
    to_code: str = "WAT"
    to_name: str = "London Waterloo"


class RefreshConfig(BaseModel):
    """Configuration for data refresh settings."""

    auto_enabled: bool = True
    interval_minutes: int = 2
    manual_enabled: bool = True


class DisplayConfig(BaseModel):
    """Configuration for display settings."""

    max_trains: int = 50
    time_window_hours: int = 10
    show_cancelled: bool = True
    theme: str = "dark"  # Default to dark theme - "dark" or "light"


class ConfigData(BaseModel):
    """Main configuration data model."""

    api: APIConfig
    stations: StationConfig
    refresh: RefreshConfig
    display: DisplayConfig


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
        logger.info(f"ConfigManager initialized with path: {self.config_path}")

    @staticmethod
    def get_default_config_path() -> Path:
        """
        Get the default configuration file path.
        
        On Windows, uses AppData/Roaming/Trainer/config.json
        On other systems, uses current directory/config.json
        
        For executable builds, always prefer AppData on Windows to ensure writability.
        
        Returns:
            Path: Default configuration file path
        """
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA')
            if appdata:
                config_dir = Path(appdata) / "Trainer"
                config_dir.mkdir(parents=True, exist_ok=True)
                return config_dir / "config.json"
        
        # For non-Windows or if APPDATA not available, check if we're in an executable
        # If so, try to use a writable location
        import sys
        if getattr(sys, 'frozen', False):  # Running as executable
            # Try to use user's home directory
            home_dir = Path.home()
            config_dir = home_dir / ".trainer"
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
            if os.name != 'nt':  # Not Windows
                return False
                
            appdata = os.environ.get('APPDATA')
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
                    api=APIConfig(app_id="YOUR_APP_ID_HERE", app_key="YOUR_APP_KEY_HERE"),
                    stations=StationConfig(),
                    refresh=RefreshConfig(),
                    display=DisplayConfig(),
                )
                
                with open(appdata_config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config.model_dump(), f, indent=2, ensure_ascii=False)
                
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
        logger.info(f"Loading config from: {self.config_path}")
        
        if not self.config_path.exists():
            logger.info(f"Config file doesn't exist, creating default at: {self.config_path}")
            self.create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.config = ConfigData(**data)
            logger.info(f"Successfully loaded config from: {self.config_path}")
            return self.config
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {e}")

    def save_config(self, config: ConfigData) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration data to save

        Raises:
            ConfigurationError: If saving fails
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Saving config to: {self.config_path}")
        
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Config directory ensured: {self.config_path.parent}")

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
            self.config = config
            logger.info(f"Successfully saved config to: {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise ConfigurationError(f"Failed to save config: {e}")

    def create_default_config(self) -> None:
        """Create a default configuration file."""
        default_config = ConfigData(
            api=APIConfig(app_id="YOUR_APP_ID_HERE", app_key="YOUR_APP_KEY_HERE"),
            stations=StationConfig(),
            refresh=RefreshConfig(),
            display=DisplayConfig(),
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

        return {
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
