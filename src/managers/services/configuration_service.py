"""
Configuration service for managing train manager settings and preferences.

This service handles configuration updates, route persistence, and preference management
for the train manager system.
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Service for managing configuration and preferences."""

    def __init__(self, config=None, config_manager=None):
        """
        Initialize configuration service.

        Args:
            config: Current configuration data
            config_manager: Configuration manager for persistence
        """
        self.config = config
        self.config_manager = config_manager

    def update_config(self, new_config) -> None:
        """
        Update configuration and log changes.

        Args:
            new_config: New configuration data
        """
        # Get old time window for comparison
        old_time_window = self._get_time_window_hours(self.config)
        
        self.config = new_config
        
        # Get new time window and log changes
        new_time_window = self._get_time_window_hours(new_config)
        
        if old_time_window != new_time_window:
            logger.info(f"Time window updated from {old_time_window} to {new_time_window} hours")

    def set_route_path(self, from_station: str, to_station: str, 
                      route_path: Optional[List[str]] = None) -> bool:
        """
        Set and persist route path configuration.

        Args:
            from_station: Origin station name
            to_station: Destination station name
            route_path: Optional route path to persist

        Returns:
            True if route was successfully saved, False otherwise
        """
        if not self.config or not hasattr(self.config, 'stations'):
            logger.warning("No valid configuration available for route persistence")
            return False

        if route_path is not None:
            # Validate and clean route path
            validated_path = self._validate_route_path(route_path, from_station, to_station)
            
            if validated_path:
                # Update config with validated path
                serializable_path = [str(station) for station in validated_path]
                self.config.stations.route_path = serializable_path
                logger.info(f"Updated config with route path: {len(serializable_path)} stations")
                
                # Persist to disk
                return self._save_config_to_disk()
            else:
                logger.error("Route path validation failed")
                return False
        else:
            # Clear route path
            self.config.stations.route_path = []
            logger.info("Cleared route path in config")
            return self._save_config_to_disk()

    def get_route_preferences(self) -> Dict[str, Any]:
        """
        Get route calculation preferences from configuration.

        Returns:
            Dictionary of route preferences
        """
        preferences = {}
        
        if not self.config:
            return preferences

        # Check for avoid_walking preference
        if hasattr(self.config, 'avoid_walking'):
            preferences['avoid_walking'] = self.config.avoid_walking
            if self.config.avoid_walking:
                preferences['exclude_walking'] = True
            else:
                preferences['walking_weight'] = 10.0  # High weight to prefer non-walking

        # Check for prefer_direct preference
        if hasattr(self.config, 'prefer_direct'):
            preferences['prefer_direct'] = self.config.prefer_direct

        # Check for location preferences
        location_value = self._get_location_preference()
        if location_value:
            preferences['near_location'] = location_value

        return preferences

    def get_time_window_hours(self) -> int:
        """
        Get time window hours from configuration.

        Returns:
            Time window in hours
        """
        return self._get_time_window_hours(self.config)

    def get_max_trains_limit(self) -> int:
        """
        Get maximum trains limit from configuration.

        Returns:
            Maximum number of trains to display
        """
        # For now, use a fixed limit - could be made configurable later
        return 100

    def _validate_route_path(self, route_path: List[str], from_station: str, 
                           to_station: str) -> Optional[List[str]]:
        """
        Validate and fix route path.

        Args:
            route_path: Route path to validate
            from_station: Expected origin station
            to_station: Expected destination station

        Returns:
            Validated route path or None if invalid
        """
        if not isinstance(route_path, list):
            logger.warning(f"Route path is not a list, converting: {route_path}")
            try:
                if isinstance(route_path, str):
                    route_path = [s.strip() for s in route_path.split(',')]
                else:
                    route_path = list(route_path)
            except Exception as e:
                logger.error(f"Failed to convert route_path to list: {e}")
                return [from_station, to_station]

        # Ensure minimum length
        if len(route_path) < 2:
            logger.warning(f"Route path too short ({len(route_path)}), fixing")
            if len(route_path) == 1:
                if route_path[0] == from_station:
                    route_path.append(to_station)
                else:
                    route_path.insert(0, from_station)
            else:
                route_path = [from_station, to_station]

        # Validate endpoints
        if route_path[0] != from_station or route_path[-1] != to_station:
            logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                          f"don't match stations ({from_station}, {to_station}) - adjusting")
            route_path[0] = from_station
            route_path[-1] = to_station

        return route_path

    def _save_config_to_disk(self) -> bool:
        """
        Save configuration to disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.config_manager:
                # Check if force_flush parameter is available
                if (hasattr(self.config_manager, 'save_config') and 
                    'force_flush' in self.config_manager.save_config.__code__.co_varnames):
                    self.config_manager.save_config(self.config, force_flush=True)
                    logger.info("Saved config to disk using config manager (force_flush=True)")
                else:
                    self.config_manager.save_config(self.config)
                    logger.info("Saved config to disk using config manager")
                
                # Verify save was successful
                return self._verify_config_save()
            else:
                # Fallback to creating new config manager
                from ..config_manager import ConfigManager
                config_manager = ConfigManager()
                config_manager.save_config(self.config, force_flush=True)
                logger.info("Saved config to disk using new config manager")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save config to disk: {e}")
            return False

    def _verify_config_save(self) -> bool:
        """
        Verify that configuration was saved correctly.

        Returns:
            True if verification successful, False otherwise
        """
        try:
            if not self.config_manager:
                return True  # Skip verification if no config manager
                
            saved_config = self.config_manager.load_config()
            if (hasattr(saved_config, 'stations') and
                hasattr(saved_config.stations, 'route_path') and
                saved_config.stations.route_path):
                saved_path = saved_config.stations.route_path
                logger.info(f"Verified saved route path: {len(saved_path)} stations")
                return True
            else:
                logger.warning("Route path not found in saved config")
                return False
                
        except Exception as e:
            logger.warning(f"Could not verify saved route path: {e}")
            return False

    def _get_time_window_hours(self, config) -> int:
        """
        Get time window hours from configuration with fallbacks.

        Args:
            config: Configuration object

        Returns:
            Time window in hours
        """
        if not config:
            return 8  # Default fallback

        # Try configurable preference first
        time_window = getattr(config, 'train_lookahead_hours', None)
        if time_window is not None:
            return time_window

        # Fallback to display config
        if hasattr(config, 'display') and hasattr(config.display, 'time_window_hours'):
            return config.display.time_window_hours

        return 8  # Final fallback

    def _get_location_preference(self) -> Optional[str]:
        """
        Get location preference from configuration.

        Returns:
            Location string or None if not found
        """
        if not self.config:
            return None

        try:
            # Check various location attributes
            for location_attr in ['current_location', 'user_location', 'location']:
                if hasattr(self.config, location_attr):
                    location_value = getattr(self.config, location_attr)
                    if location_value:
                        logger.info(f"Using user location from config.{location_attr}")
                        return location_value

            # Check in stations config
            if hasattr(self.config, 'stations'):
                stations_config = self.config.stations
                for location_attr in ['current_location', 'user_location', 'location']:
                    if hasattr(stations_config, location_attr):
                        location_value = getattr(stations_config, location_attr)
                        if location_value:
                            logger.info(f"Using user location from config.stations.{location_attr}")
                            return location_value

        except Exception as e:
            logger.warning(f"Error processing location data: {e}")

        return None

    def has_valid_station_config(self) -> bool:
        """
        Check if configuration has valid station data.

        Returns:
            True if valid station configuration exists
        """
        return (self.config and
                hasattr(self.config, 'stations') and
                self.config.stations and
                getattr(self.config.stations, 'from_name', None) and
                getattr(self.config.stations, 'to_name', None))

    def get_configured_via_stations(self) -> List[str]:
        """
        Get configured via stations from configuration.

        Returns:
            List of via station names
        """
        if (self.config and 
            hasattr(self.config, 'stations') and
            hasattr(self.config.stations, 'via_stations')):
            return getattr(self.config.stations, 'via_stations', [])
        
        return []

    def get_route_path_from_config(self) -> Optional[List[str]]:
        """
        Get stored route path from configuration.

        Returns:
            Route path list or None if not available
        """
        if (self.config and
            hasattr(self.config, 'stations') and
            hasattr(self.config.stations, 'route_path') and
            self.config.stations.route_path):
            return self.config.stations.route_path
        
        return None