"""
Dialog State Manager for the Train Settings Dialog.

This module manages the state of the train settings dialog,
providing a centralized way to handle route data and preferences.
"""

import logging
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class DialogState(QObject):
    """Manages the state of the train settings dialog."""
    
    # Signals
    route_data_changed = Signal(dict)
    via_stations_changed = Signal(list)
    departure_time_changed = Signal(str)
    preferences_changed = Signal(dict)
    
    def __init__(self, parent=None):
        """Initialize the dialog state."""
        super().__init__(parent)
        
        # Route state
        self.via_stations = []
        self.departure_time = "08:00"
        self.route_data = {}
        
        # Preferences state
        self.preferences = {
            'show_intermediate_stations': True,
            'avoid_walking': False,
            'max_walking_distance_km': 1.0,
            'train_lookahead_hours': 16,
        }
        
        logger.debug("DialogState initialized")
    
    def set_route_data(self, route_data: Dict[str, Any]):
        """Set route data with enhanced validation and logging."""
        if not route_data:
            logger.warning("Attempted to set empty route data")
            self.route_data = {}
            self.route_data_changed.emit(self.route_data)
            return
        
        # Make a copy to avoid modifying the original
        self.route_data = route_data.copy()
        
        # Validate route data has required fields
        required_fields = ['from_station', 'to_station']
        missing_fields = [field for field in required_fields if field not in self.route_data]
        if missing_fields:
            logger.warning(f"Route data missing required fields: {missing_fields}")
        
        # Ensure full_path is present
        if 'full_path' not in self.route_data or not self.route_data['full_path']:
            logger.warning("Route data missing full_path - attempting to reconstruct")
            
            # Try to reconstruct from interchange stations
            if ('interchange_stations' in self.route_data and
                self.route_data.get('from_station') and
                self.route_data.get('to_station')):
                
                self.route_data['full_path'] = [
                    self.route_data['from_station']
                ] + self.route_data['interchange_stations'] + [
                    self.route_data['to_station']
                ]
                logger.info(f"Reconstructed full_path with {len(self.route_data['full_path'])} stations")
        
        # Log the route data details
        if 'full_path' in self.route_data and self.route_data['full_path']:
            path_len = len(self.route_data['full_path'])
            logger.info(f"Route data set with {path_len} stations in path")
            if path_len >= 2:
                from_station = self.route_data['full_path'][0]
                to_station = self.route_data['full_path'][-1]
                logger.info(f"Route path: {from_station} -> ... -> {to_station}")
        
        # Emit signal for UI updates
        self.route_data_changed.emit(self.route_data)
        logger.debug(f"Route data updated: {len(self.route_data)} keys")
    
    def get_route_data(self) -> Dict[str, Any]:
        """Get the current route data."""
        return self.route_data.copy()
    
    def set_via_stations(self, via_stations: List[str]):
        """Set the via stations list and emit signal."""
        self.via_stations = via_stations.copy() if via_stations else []
        self.via_stations_changed.emit(self.via_stations)
        logger.debug(f"Via stations updated: {self.via_stations}")
    
    def add_via_station(self, station: str) -> bool:
        """Add a via station if not already present."""
        if station and station not in self.via_stations:
            self.via_stations.append(station)
            self.via_stations_changed.emit(self.via_stations)
            logger.debug(f"Via station added: {station}")
            return True
        return False
    
    def remove_via_station(self, station: str) -> bool:
        """Remove a via station if present."""
        if station in self.via_stations:
            self.via_stations.remove(station)
            self.via_stations_changed.emit(self.via_stations)
            logger.debug(f"Via station removed: {station}")
            return True
        return False
    
    def clear_via_stations(self):
        """Clear all via stations."""
        self.via_stations = []
        self.via_stations_changed.emit(self.via_stations)
        logger.debug("Via stations cleared")
    
    def set_departure_time(self, time_str: str):
        """Set the departure time and emit signal."""
        self.departure_time = time_str
        self.departure_time_changed.emit(self.departure_time)
        logger.debug(f"Departure time updated: {time_str}")
    
    def get_departure_time(self) -> str:
        """Get the current departure time."""
        return self.departure_time
    
    def set_preferences(self, preferences: Dict[str, Any]):
        """Set preferences and emit signal."""
        self.preferences.update(preferences)
        self.preferences_changed.emit(self.preferences)
        logger.debug(f"Preferences updated: {list(preferences.keys())}")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get current preferences."""
        return self.preferences.copy()
    
    def set_preference(self, key: str, value: Any):
        """Set a single preference."""
        if key in self.preferences:
            self.preferences[key] = value
            self.preferences_changed.emit(self.preferences)
            logger.debug(f"Preference updated: {key} = {value}")
    
    def get_preference(self, key: str, default=None):
        """Get a single preference value."""
        return self.preferences.get(key, default)
    
    def clear_route_data(self):
        """Clear all route data."""
        self.route_data = {}
        self.route_data_changed.emit(self.route_data)
        logger.debug("Route data cleared")
    
    def get_current_route_config(self) -> Dict[str, Any]:
        """Get the complete current route configuration."""
        return {
            'via_stations': self.via_stations.copy(),
            'departure_time': self.departure_time,
            'route_data': self.route_data.copy(),
            'preferences': self.preferences.copy()
        }
    
    def set_route_config(self, config: Dict[str, Any]):
        """Set the complete route configuration."""
        if 'via_stations' in config:
            self.set_via_stations(config['via_stations'])
        if 'departure_time' in config:
            self.set_departure_time(config['departure_time'])
        if 'route_data' in config:
            self.set_route_data(config['route_data'])
        if 'preferences' in config:
            self.set_preferences(config['preferences'])
        
        logger.debug("Route configuration updated")