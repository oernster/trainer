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
            'optimize_for_speed': True,
            'show_intermediate_stations': True,
            'avoid_london': False,
            'prefer_direct': False,
            'max_changes': 3,
            'max_journey_time': 8
        }
        
        logger.debug("DialogState initialized")
    
    def set_route_data(self, route_data: Dict[str, Any]):
        """Set the route data and emit signal."""
        self.route_data = route_data.copy() if route_data else {}
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