"""
Route Calculation Handler for the Train Settings Dialog.

This module handles route calculation operations using the core services,
providing a clean interface between the UI and the route calculation logic.
"""

import logging
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class RouteCalculationHandler(QObject):
    """Handles route calculation operations."""
    
    # Signals
    route_calculated = Signal(dict)  # Emitted when route is successfully calculated
    route_calculation_failed = Signal(str)  # Emitted when route calculation fails
    calculation_started = Signal()  # Emitted when calculation starts
    calculation_finished = Signal()  # Emitted when calculation finishes (success or failure)
    
    def __init__(self, parent_dialog, station_service=None, route_service=None):
        """
        Initialize the route calculation handler.
        
        Args:
            parent_dialog: The parent settings dialog
            station_service: Station service for station operations
            route_service: Route service for route calculations
        """
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.station_service = station_service
        self.route_service = route_service
        
        logger.debug("RouteCalculationHandler initialized")
    
    def calculate_route(self, from_station: str, to_station: str, via_stations: Optional[list] = None,
                       max_changes: int = 10, preferences: Optional[Dict[str, Any]] = None) -> bool:
        """
        Calculate route between stations.
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            via_stations: Optional list of via stations
            max_changes: Maximum number of changes allowed
            
        Returns:
            True if calculation started successfully, False otherwise
        """
        try:
            # Validate inputs
            if not from_station or not to_station:
                self.route_calculation_failed.emit("Please select both from and to stations.")
                return False
            
            if from_station == to_station:
                self.route_calculation_failed.emit("From and to stations must be different.")
                return False
            
            # Check if services are available
            if not self.route_service or not self.station_service:
                self.route_calculation_failed.emit("Route calculation services are not available.")
                return False
            
            logger.info(f"Starting route calculation: {from_station} → {to_station}")
            self.calculation_started.emit()
            
            # Get preferences from parent dialog if available
            if preferences is None and hasattr(self.parent_dialog, 'dialog_state'):
                preferences = self.parent_dialog.dialog_state.get_preferences()
            
            # Use real route service to calculate the route
            route_result = self.route_service.calculate_route(
                from_station,
                to_station,
                max_changes=max_changes,
                preferences=preferences
            )
            
            if route_result:
                # Convert route result to our expected format
                route_data = self._convert_route_result(route_result, from_station, to_station, via_stations)
                
                logger.info(f"Route calculated successfully: {from_station} → {to_station}, "
                           f"{route_result.total_journey_time_minutes or 0}min, "
                           f"{route_result.total_distance_km or 0:.1f}km, "
                           f"{route_result.changes_required} changes")
                
                self.route_calculated.emit(route_data)
                self.calculation_finished.emit()
                return True
            else:
                error_msg = f"No route could be found between {from_station} and {to_station}."
                logger.warning(error_msg)
                self.route_calculation_failed.emit(error_msg)
                self.calculation_finished.emit()
                return False
            
        except Exception as e:
            error_msg = f"Error calculating route: {e}"
            logger.error(error_msg)
            self.route_calculation_failed.emit(error_msg)
            self.calculation_finished.emit()
            return False
    
    def _convert_route_result(self, route_result, from_station: str, to_station: str,
                             via_stations: Optional[list] = None) -> Dict[str, Any]:
        """
        Convert route service result to dialog format.
        
        Args:
            route_result: Route result from route service
            from_station: Origin station name
            to_station: Destination station name
            via_stations: Optional list of via stations
            
        Returns:
            Dictionary containing route data in dialog format
        """
        try:
            # Extract interchange stations from the route result
            interchange_stations = []
            if hasattr(route_result, 'interchange_stations') and route_result.interchange_stations:
                interchange_stations = route_result.interchange_stations
            elif hasattr(route_result, 'segments') and route_result.segments:
                # Extract interchange stations from segments
                for i, segment in enumerate(route_result.segments[:-1]):  # Exclude last segment
                    if hasattr(segment, 'to_station'):
                        interchange_stations.append(segment.to_station)
            
            # Extract full path from route result if available
            full_path = []
            if hasattr(route_result, 'full_path') and route_result.full_path:
                full_path = route_result.full_path
            
            route_data = {
                'from_station': from_station,
                'to_station': to_station,
                'via_stations': via_stations or [],
                'journey_time': route_result.total_journey_time_minutes or 0,
                'distance': route_result.total_distance_km or 0.0,
                'changes': route_result.changes_required or 0,
                'operators': route_result.lines_used or [],
                'segments': route_result.segments or [],
                'route_type': route_result.route_type or 'calculated',
                'is_direct': route_result.is_direct or False,
                'interchange_stations': interchange_stations,
                'full_path': full_path  # Include full path for persistence
            }
            
            return route_data
            
        except Exception as e:
            logger.error(f"Error converting route result: {e}")
            return {
                'from_station': from_station,
                'to_station': to_station,
                'via_stations': via_stations or [],
                'journey_time': 0,
                'distance': 0.0,
                'changes': 0,
                'operators': [],
                'segments': [],
                'route_type': 'error',
                'is_direct': False,
                'interchange_stations': [],
                'full_path': []  # Include empty full path for consistency
            }
    
    def auto_fix_route(self, from_station: str, to_station: str) -> bool:
        """
        Auto-fix route issues by finding the best available route.
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            
        Returns:
            True if auto-fix started successfully, False otherwise
        """
        try:
            logger.info(f"Starting route auto-fix: {from_station} → {to_station}")
            
            # Use a higher max_changes for auto-fix to find any possible route
            # Get preferences from parent dialog if available
            preferences = None
            if hasattr(self.parent_dialog, 'dialog_state'):
                preferences = self.parent_dialog.dialog_state.get_preferences()
                
            return self.calculate_route(from_station, to_station, max_changes=15, preferences=preferences)
            
        except Exception as e:
            error_msg = f"Error auto-fixing route: {e}"
            logger.error(error_msg)
            self.route_calculation_failed.emit(error_msg)
            return False
    
    def validate_stations(self, from_station: str, to_station: str) -> Dict[str, Any]:
        """
        Validate that stations exist and are different.
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            
        Returns:
            Dictionary with validation result
        """
        try:
            if not from_station or not to_station:
                return {
                    'valid': False,
                    'message': 'Please select both from and to stations.'
                }
            
            if from_station == to_station:
                return {
                    'valid': False,
                    'message': 'From and to stations must be different.'
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
            logger.error(f"Error validating stations: {e}")
            return {
                'valid': False,
                'message': f'Validation error: {e}'
            }
    
    def get_station_suggestions(self, partial_name: str, limit: int = 10) -> list:
        """
        Get station name suggestions based on partial input.
        
        Args:
            partial_name: Partial station name
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested station names
        """
        try:
            if not self.station_service or not partial_name:
                return []
            
            all_stations = self.station_service.get_all_stations()
            station_names = [station.name for station in all_stations]
            
            # Filter stations that contain the partial name (case-insensitive)
            suggestions = [
                name for name in station_names 
                if partial_name.lower() in name.lower()
            ]
            
            # Sort by relevance (exact matches first, then starts with, then contains)
            def sort_key(name):
                lower_name = name.lower()
                lower_partial = partial_name.lower()
                
                if lower_name == lower_partial:
                    return (0, name)  # Exact match
                elif lower_name.startswith(lower_partial):
                    return (1, name)  # Starts with
                else:
                    return (2, name)  # Contains
            
            suggestions.sort(key=sort_key)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting station suggestions: {e}")
            return []
    
    def is_services_available(self) -> bool:
        """Check if route calculation services are available."""
        return self.station_service is not None and self.route_service is not None
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get the status of available services."""
        return {
            'station_service': self.station_service is not None,
            'route_service': self.route_service is not None,
            'calculation_available': self.is_services_available()
        }