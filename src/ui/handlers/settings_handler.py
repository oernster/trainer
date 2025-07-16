"""
Settings Handler for the Train Settings Dialog.

This module handles loading and saving of dialog settings,
including station selections, preferences, and route configurations.
"""

import logging
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class SettingsHandler(QObject):
    """Handles loading and saving of dialog settings."""
    
    # Signals
    settings_loaded = Signal(dict)
    settings_saved = Signal()
    settings_error = Signal(str)
    
    def __init__(self, parent_dialog, config_manager, station_service=None, route_service=None):
        """
        Initialize the settings handler.
        
        Args:
            parent_dialog: The parent settings dialog
            config_manager: Configuration manager
            station_service: Station service for validation
            route_service: Route service for validation
        """
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.config_manager = config_manager
        self.station_service = station_service
        self.route_service = route_service
        
        logger.debug("SettingsHandler initialized")
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from configuration.
        
        Returns:
            Dictionary containing loaded settings
        """
        try:
            if not self.config_manager:
                logger.warning("No config manager available")
                return {}
            
            config = self.config_manager.load_config()
            settings = {}
            
            # Load station settings - try new format first, then old format
            from_station = None
            to_station = None
            
            # Try new format first
            if hasattr(config, 'stations') and config.stations:
                if hasattr(config.stations, 'from_name') and config.stations.from_name:
                    from_station = config.stations.from_name
                if hasattr(config.stations, 'to_name') and config.stations.to_name:
                    to_station = config.stations.to_name
            
            # Fallback to old format
            if not from_station and hasattr(config, 'default_from_station') and config.default_from_station:
                from_station = config.default_from_station
            if not to_station and hasattr(config, 'default_to_station') and config.default_to_station:
                to_station = config.default_to_station
            
            settings['from_station'] = from_station or ""
            settings['to_station'] = to_station or ""
            
            # Load preferences
            preferences = {}
            if hasattr(config, 'show_intermediate_stations'):
                preferences['show_intermediate_stations'] = config.show_intermediate_stations
            if hasattr(config, 'avoid_walking'):
                preferences['avoid_walking'] = config.avoid_walking
            if hasattr(config, 'train_lookahead_hours'):
                preferences['train_lookahead_hours'] = config.train_lookahead_hours
            if hasattr(config, 'max_walking_distance_km'):
                preferences['max_walking_distance_km'] = config.max_walking_distance_km
            
            settings['preferences'] = preferences
            
            # Load departure time if available
            if hasattr(config, 'departure_time'):
                settings['departure_time'] = config.departure_time
            else:
                settings['departure_time'] = "08:00"
                
            # Load route path if available
            if hasattr(config, 'stations') and hasattr(config.stations, 'route_path'):
                route_path = config.stations.route_path
                if route_path and len(route_path) >= 2:
                    # Create minimal route data with the path
                    route_data = {
                        'full_path': route_path,
                        'journey_time': 0,  # Placeholder, will be recalculated
                        'distance': 0,      # Placeholder, will be recalculated
                        'changes': 0        # Placeholder, will be recalculated
                    }
                    settings['route_data'] = route_data
                    logger.info(f"Loaded route path with {len(route_path)} stations")
            
            logger.info(f"Settings loaded successfully: {list(settings.keys())}")
            self.settings_loaded.emit(settings)
            return settings
            
        except Exception as e:
            error_msg = f"Error loading settings: {e}"
            logger.error(error_msg)
            self.settings_error.emit(error_msg)
            return {}
    
    def save_settings(self, from_station: str, to_station: str, preferences: Dict[str, Any],
                     departure_time: str = "08:00", route_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save settings to configuration.
        
        Args:
            from_station: From station name
            to_station: To station name
            preferences: Preferences dictionary
            departure_time: Departure time string
            route_data: Optional route data for validation and route path persistence
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Validate settings before saving
            validation_result = self._validate_settings(from_station, to_station, route_data)
            if not validation_result['valid']:
                QMessageBox.warning(
                    self.parent_dialog,
                    "Invalid Settings",
                    validation_result['message']
                )
                return False
            
            if not self.config_manager:
                logger.error("No config manager available for saving")
                return False
            
            # Get current configuration
            config = self.config_manager.load_config()
            
            # Update station settings (with safe attribute setting)
            if hasattr(config, 'stations'):
                if hasattr(config.stations, 'from_name'):
                    config.stations.from_name = from_station
                if hasattr(config.stations, 'to_name'):
                    config.stations.to_name = to_station
            
            # Also update the old format for backward compatibility
            if hasattr(config, 'default_from_station'):
                config.default_from_station = from_station
            if hasattr(config, 'default_to_station'):
                config.default_to_station = to_station
            
            # Update preferences (with safe attribute setting)
            for key, value in preferences.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    logger.debug(f"Updated preference {key}: {value}")
            
            # Update departure time
            if hasattr(config, 'departure_time'):
                config.departure_time = departure_time
                
            # Save route path if available
            if route_data and 'full_path' in route_data and hasattr(config, 'stations'):
                if hasattr(config.stations, 'route_path'):
                    # Extract the full path from route data
                    route_path = route_data.get('full_path', [])
                    
                    # Validate route path
                    if route_path and len(route_path) >= 2:
                        # Ensure first and last stations match from/to
                        if route_path[0] != from_station or route_path[-1] != to_station:
                            logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                                          f"don't match from/to stations ({from_station}, {to_station})")
                            # Fix the route path to match from/to stations
                            if route_path[0] != from_station:
                                route_path[0] = from_station
                            if route_path[-1] != to_station:
                                route_path[-1] = to_station
                        
                        config.stations.route_path = route_path
                        logger.info(f"Saved route path with {len(route_path)} stations: {' → '.join(route_path)}")
                    else:
                        logger.warning("Invalid route path, not saving")
            
            # Save configuration with force_flush to ensure persistence
            if hasattr(self.config_manager, 'save_config') and 'force_flush' in self.config_manager.save_config.__code__.co_varnames:
                # Use force_flush if available
                self.config_manager.save_config(config, force_flush=True)
                logger.debug("Saved configuration with force_flush=True")
            else:
                # Fallback to regular save
                self.config_manager.save_config(config)
                logger.debug("Saved configuration (force_flush not available)")
            
            logger.info(f"Settings saved successfully: {from_station} → {to_station}")
            self.settings_saved.emit()
            return True
            
        except Exception as e:
            error_msg = f"Error saving settings: {e}"
            logger.error(error_msg)
            self.settings_error.emit(error_msg)
            QMessageBox.critical(self.parent_dialog, "Settings Error", f"Failed to save settings: {e}")
            return False
    
    def _validate_settings(self, from_station: str, to_station: str,
                          route_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate settings before saving.
        
        Args:
            from_station: From station name
            to_station: To station name
            route_data: Optional route data
            
        Returns:
            Dictionary with 'valid' boolean and 'message' string
        """
        try:
            # Basic validation
            if not from_station or not to_station:
                return {
                    'valid': False,
                    'message': 'Please select both From and To stations.'
                }
            
            if from_station == to_station:
                return {
                    'valid': False,
                    'message': 'From and To stations must be different.'
                }
            
            # Validate that route has been calculated if stations are selected
            if from_station and to_station:
                if not route_data or not route_data.get('journey_time'):
                    return {
                        'valid': False,
                        'message': 'Please click "Find Route" to calculate the route before saving settings.'
                    }
                
                # Validate route path if available
                if route_data and 'full_path' in route_data:
                    route_path = route_data.get('full_path', [])
                    
                    # Check if route path is valid
                    if not route_path or len(route_path) < 2:
                        logger.warning("Route path is empty or too short")
                        return {
                            'valid': False,
                            'message': 'Route path is invalid. Please recalculate the route.'
                        }
                    
                    # Check if route path matches from/to stations
                    if route_path[0] != from_station or route_path[-1] != to_station:
                        logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                                      f"don't match from/to stations ({from_station}, {to_station})")
                        return {
                            'valid': False,
                            'message': 'Route path does not match selected stations. Please recalculate the route.'
                        }
            
            # Validate stations exist (if station service is available)
            if self.station_service:
                try:
                    all_stations = self.station_service.get_all_stations()
                    station_names = [station.name for station in all_stations]
                    
                    if from_station not in station_names:
                        return {
                            'valid': False,
                            'message': f'From station "{from_station}" is not valid.'
                        }
                    
                    if to_station not in station_names:
                        return {
                            'valid': False,
                            'message': f'To station "{to_station}" is not valid.'
                        }
                        
                except Exception as e:
                    logger.warning(f"Could not validate stations: {e}")
            
            return {'valid': True, 'message': ''}
            
        except Exception as e:
            logger.error(f"Error validating settings: {e}")
            return {
                'valid': False,
                'message': f'Validation error: {e}'
            }
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings.
        
        Returns:
            Dictionary containing default settings
        """
        return {
            'from_station': '',
            'to_station': '',
            'departure_time': '08:00',
            'preferences': {
                'optimize_for_speed': True,
                'show_intermediate_stations': True,
                'avoid_london': False,
                'prefer_direct': False,
                'avoid_walking': False,
                'max_changes': 3,
                'max_journey_time': 8,
                'train_lookahead_hours': 16,
                'max_walking_distance_km': 1.0
            }
        }
    
    def reset_to_defaults(self):
        """Reset settings to defaults and save."""
        try:
            defaults = self.get_default_settings()
            success = self.save_settings(
                defaults['from_station'],
                defaults['to_station'],
                defaults['preferences'],
                defaults['departure_time']
            )
            
            if success:
                logger.info("Settings reset to defaults")
                self.settings_loaded.emit(defaults)
            
            return success
            
        except Exception as e:
            error_msg = f"Error resetting settings: {e}"
            logger.error(error_msg)
            self.settings_error.emit(error_msg)
            return False