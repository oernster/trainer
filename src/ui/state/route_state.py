"""
Route State Management for the Train Times application.

This module manages all route-related state including via stations,
route validation, and auto-fix status.
"""

import logging
from typing import List, Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class RouteState(QObject):
    """Manages route-related state for the settings dialog."""
    
    # Signals
    via_stations_changed = Signal(list)  # Emitted when via stations list changes
    route_auto_fixed_changed = Signal(bool)  # Emitted when auto-fix status changes
    route_validation_changed = Signal(bool, str)  # Emitted when validation status changes
    
    def __init__(self, parent=None):
        """Initialize route state."""
        super().__init__(parent)
        
        # Via stations state
        self._via_stations: List[str] = []
        self._route_auto_fixed: bool = False
        
        # Route validation state
        self._is_route_valid: bool = True
        self._validation_message: str = ""
        
        # Current from/to stations for validation
        self._from_station: str = ""
        self._to_station: str = ""
        self._departure_time: str = ""
    
    @property
    def via_stations(self) -> List[str]:
        """Get the current via stations list."""
        return self._via_stations.copy()
    
    @via_stations.setter
    def via_stations(self, stations: List[str]):
        """Set the via stations list."""
        if stations != self._via_stations:
            self._via_stations = stations.copy() if stations else []
            self.via_stations_changed.emit(self._via_stations.copy())
            logger.debug(f"Via stations updated: {self._via_stations}")
    
    @property
    def route_auto_fixed(self) -> bool:
        """Get the route auto-fixed status."""
        return self._route_auto_fixed
    
    @route_auto_fixed.setter
    def route_auto_fixed(self, auto_fixed: bool):
        """Set the route auto-fixed status."""
        if auto_fixed != self._route_auto_fixed:
            self._route_auto_fixed = auto_fixed
            self.route_auto_fixed_changed.emit(auto_fixed)
            logger.debug(f"Route auto-fixed status updated: {auto_fixed}")
    
    @property
    def is_route_valid(self) -> bool:
        """Get the route validation status."""
        return self._is_route_valid
    
    @property
    def validation_message(self) -> str:
        """Get the route validation message."""
        return self._validation_message
    
    @property
    def from_station(self) -> str:
        """Get the current from station."""
        return self._from_station
    
    @from_station.setter
    def from_station(self, station: str):
        """Set the from station."""
        if station != self._from_station:
            self._from_station = station
            logger.debug(f"From station updated: {station}")
    
    @property
    def to_station(self) -> str:
        """Get the current to station."""
        return self._to_station
    
    @to_station.setter
    def to_station(self, station: str):
        """Set the to station."""
        if station != self._to_station:
            self._to_station = station
            logger.debug(f"To station updated: {station}")
    
    @property
    def departure_time(self) -> str:
        """Get the current departure time."""
        return self._departure_time
    
    @departure_time.setter
    def departure_time(self, time_str: str):
        """Set the departure time."""
        if time_str != self._departure_time:
            self._departure_time = time_str
            logger.debug(f"Departure time updated: {time_str}")
    
    def add_via_station(self, station: str) -> bool:
        """
        Add a via station to the route.
        
        Args:
            station: Station name to add
            
        Returns:
            True if station was added, False if it already exists
        """
        if station and station not in self._via_stations:
            self._via_stations.append(station)
            self.via_stations_changed.emit(self._via_stations.copy())
            logger.debug(f"Via station added: {station}")
            return True
        return False
    
    def remove_via_station(self, station: str) -> bool:
        """
        Remove a via station from the route.
        
        Args:
            station: Station name to remove
            
        Returns:
            True if station was removed, False if it wasn't found
        """
        if station in self._via_stations:
            self._via_stations.remove(station)
            self.via_stations_changed.emit(self._via_stations.copy())
            logger.debug(f"Via station removed: {station}")
            
            # Reset auto-fixed flag only when ALL via stations are removed
            if len(self._via_stations) == 0:
                self.route_auto_fixed = False
            
            return True
        return False
    
    def clear_via_stations(self):
        """Clear all via stations."""
        if self._via_stations:
            self._via_stations.clear()
            self.via_stations_changed.emit([])
            self.route_auto_fixed = False
            logger.debug("All via stations cleared")
    
    def set_via_stations(self, stations: List[str]):
        """
        Set the complete via stations list.
        
        Args:
            stations: List of station names
        """
        self.via_stations = stations
    
    def get_complete_route(self) -> List[str]:
        """
        Get the complete route including from, via, and to stations.
        
        Returns:
            Complete route as a list of station names
        """
        route = []
        if self._from_station:
            route.append(self._from_station)
        route.extend(self._via_stations)
        if self._to_station:
            route.append(self._to_station)
        return route
    
    def is_direct_route(self) -> bool:
        """Check if this is a direct route (no via stations)."""
        return len(self._via_stations) == 0
    
    def has_valid_endpoints(self) -> bool:
        """Check if both from and to stations are set."""
        return bool(self._from_station and self._to_station and self._from_station != self._to_station)
    
    def update_validation_status(self, is_valid: bool, message: str = ""):
        """
        Update the route validation status.
        
        Args:
            is_valid: Whether the route is valid
            message: Validation message (if invalid)
        """
        if is_valid != self._is_route_valid or message != self._validation_message:
            self._is_route_valid = is_valid
            self._validation_message = message
            self.route_validation_changed.emit(is_valid, message)
            logger.debug(f"Route validation updated: valid={is_valid}, message='{message}'")
    
    def reset_state(self):
        """Reset all route state to defaults."""
        self.clear_via_stations()
        self._from_station = ""
        self._to_station = ""
        self._departure_time = ""
        self.update_validation_status(True, "")
        logger.debug("Route state reset to defaults")
    
    def get_state_summary(self) -> dict:
        """
        Get a summary of the current route state.
        
        Returns:
            Dictionary containing current state information
        """
        return {
            'from_station': self._from_station,
            'to_station': self._to_station,
            'departure_time': self._departure_time,
            'via_stations': self._via_stations.copy(),
            'route_auto_fixed': self._route_auto_fixed,
            'is_route_valid': self._is_route_valid,
            'validation_message': self._validation_message,
            'is_direct_route': self.is_direct_route(),
            'has_valid_endpoints': self.has_valid_endpoints(),
            'complete_route': self.get_complete_route()
        }