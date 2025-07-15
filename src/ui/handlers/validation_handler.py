"""
Validation Handler for the Train Times application.

This module handles route validation logic including geographical validation,
connectivity checks, and route optimization validation for the settings dialog.
"""

import logging
from typing import List, Tuple, Optional
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class ValidationHandler(QObject):
    """Handles route validation and connectivity checks."""
    
    # Signals
    validation_completed = Signal(bool, str)  # is_valid, message
    route_validated = Signal(bool, str, list)  # is_valid, message, complete_route
    
    def __init__(self, parent_dialog, station_database, route_state):
        """
        Initialize the validation handler.
        
        Args:
            parent_dialog: The parent settings dialog
            station_database: Station database manager
            route_state: Route state manager
        """
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.station_database = station_database
        self.route_state = route_state
        
        logger.debug("ValidationHandler initialized")
    
    def validate_route(self, from_station: str, via_stations: List[str], to_station: str) -> Tuple[bool, str]:
        """
        Validate if the route forms a valid geographical path.
        Uses different validation rules for user-created vs auto-fixed routes.
        
        Args:
            from_station: Origin station name
            via_stations: List of via station names
            to_station: Destination station name
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            if not via_stations:
                # Direct routes are always valid
                result = (True, "")
                self.validation_completed.emit(True, "")
                return result
            
            # Build complete route
            complete_route = [from_station] + via_stations + [to_station]
            
            # Apply different validation rules based on whether route was auto-fixed
            if self.route_state.route_auto_fixed:
                # Lenient validation for auto-fixed routes
                result = self._validate_auto_fixed_route(complete_route)
            else:
                # Strict validation for user-created routes
                result = self._validate_user_created_route(complete_route)
            
            # Emit signals
            self.validation_completed.emit(result[0], result[1])
            self.route_validated.emit(result[0], result[1], complete_route)
            
            return result
            
        except Exception as e:
            error_msg = f"Error validating route: {e}"
            logger.error(error_msg)
            self.validation_completed.emit(False, error_msg)
            return (False, error_msg)
    
    def _validate_user_created_route(self, complete_route: List[str]) -> Tuple[bool, str]:
        """Strict validation for user-created routes."""
        try:
            # Check each segment for direct operator connections and reasonable distances
            for i in range(len(complete_route) - 1):
                current_station = complete_route[i]
                next_station = complete_route[i + 1]
                
                # Get station objects for distance calculation (parse names to remove disambiguation)
                current_station_parsed = self.station_database.parse_station_name(current_station)
                next_station_parsed = self.station_database.parse_station_name(next_station)
                current_station_obj = self.station_database.get_station_by_name(current_station_parsed)
                next_station_obj = self.station_database.get_station_by_name(next_station_parsed)
                
                if not current_station_obj or not next_station_obj:
                    return (False, f"Could not find station data for {current_station} or {next_station}.")
                
                # Calculate distance between stations
                distance = self.station_database.calculate_haversine_distance(
                    current_station_obj.coordinates,
                    next_station_obj.coordinates
                )
                
                # Strict validation: 50km limit for user-created routes
                if distance > 50:
                    # Check if there's a direct operator connection
                    operator = self.station_database.get_operator_for_segment(current_station_parsed, next_station_parsed)
                    
                    if not operator:
                        # No direct operator and too far apart
                        return (False, f"Stations {current_station} and {next_station} are {distance:.1f}km apart with no direct railway connection. Use 'Auto-Fix Route' to add intermediate stations.")
                    else:
                        # Has direct operator but still quite far - check if it's a reasonable main line connection
                        if distance > 150:  # Even with direct operator, 150km+ is suspicious for via stations
                            return (False, f"Stations {current_station} and {next_station} are {distance:.1f}km apart. While there is a direct railway connection, this distance suggests missing intermediate stations. Use 'Auto-Fix Route' to optimize the route.")
                
                # For short distances, verify there's some kind of railway connection
                if distance <= 50:
                    operator = self.station_database.get_operator_for_segment(current_station_parsed, next_station_parsed)
                    if not operator:
                        # Try to find any route with reasonable number of changes
                        routes = self.station_database.find_route_between_stations(current_station_parsed, next_station_parsed, max_changes=2)
                        if not routes:
                            return (False, f"No railway connection found between {current_station} and {next_station}, even though they are only {distance:.1f}km apart.")
                        
                        # Check if the route is too complex
                        shortest_route = min(routes, key=len)
                        if len(shortest_route) > 5:  # More than 5 stations total suggests complexity
                            return (False, f"Route between {current_station} and {next_station} requires {len(shortest_route)} stations total, which is too complex for a via connection. Use 'Auto-Fix Route' to optimize.")
            
            return (True, "")
            
        except Exception as e:
            logger.error(f"Error in user-created route validation: {e}")
            return (False, f"Validation error: {e}")
    
    def _validate_auto_fixed_route(self, complete_route: List[str]) -> Tuple[bool, str]:
        """Lenient validation for auto-fixed routes - just check basic connectivity."""
        try:
            # For auto-fixed routes, we trust the auto-fix algorithm and just do basic checks
            for i in range(len(complete_route) - 1):
                current_station = complete_route[i]
                next_station = complete_route[i + 1]
                
                # Get station objects (parse names to remove disambiguation)
                current_station_parsed = self.station_database.parse_station_name(current_station)
                next_station_parsed = self.station_database.parse_station_name(next_station)
                current_station_obj = self.station_database.get_station_by_name(current_station_parsed)
                next_station_obj = self.station_database.get_station_by_name(next_station_parsed)
                
                if not current_station_obj or not next_station_obj:
                    return (False, f"Could not find station data for {current_station} or {next_station}.")
                
                # Calculate distance
                distance = self.station_database.calculate_haversine_distance(
                    current_station_obj.coordinates,
                    next_station_obj.coordinates
                )
                
                # Very lenient check - only reject if distance is extremely unreasonable (>500km)
                if distance > 500:
                    return (False, f"Stations {current_station} and {next_station} are {distance:.1f}km apart, which seems unreasonable even for an auto-fixed route.")
                
                # Check for basic railway connectivity (allow up to 3 changes for auto-fixed routes)
                operator = self.station_database.get_operator_for_segment(current_station_parsed, next_station_parsed)
                if not operator:
                    routes = self.station_database.find_route_between_stations(current_station_parsed, next_station_parsed, max_changes=3)
                    if not routes:
                        return (False, f"No railway connection found between {current_station} and {next_station} in auto-fixed route.")
            
            return (True, "")
            
        except Exception as e:
            logger.error(f"Error in auto-fixed route validation: {e}")
            return (False, f"Validation error: {e}")
    
    def validate_station_connectivity(self, from_station: str, to_station: str) -> Tuple[bool, str]:
        """
        Validate that two stations are connected by railway.
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            
        Returns:
            Tuple[bool, str]: (is_connected, message)
        """
        try:
            if not from_station or not to_station:
                return (False, "Both stations must be specified")
            
            if from_station == to_station:
                return (False, "From and To stations must be different")
            
            # Parse station names
            from_parsed = self.station_database.parse_station_name(from_station)
            to_parsed = self.station_database.parse_station_name(to_station)
            
            # Check if stations exist
            from_obj = self.station_database.get_station_by_name(from_parsed)
            to_obj = self.station_database.get_station_by_name(to_parsed)
            
            if not from_obj:
                return (False, f"Station '{from_station}' not found in database")
            if not to_obj:
                return (False, f"Station '{to_station}' not found in database")
            
            # Check for direct connection
            operator = self.station_database.get_operator_for_segment(from_parsed, to_parsed)
            if operator:
                return (True, f"Direct connection available via {operator}")
            
            # Check for indirect connection
            routes = self.station_database.find_route_between_stations(from_parsed, to_parsed, max_changes=3)
            if routes:
                shortest_route = min(routes, key=len)
                changes = len(shortest_route) - 2  # Subtract origin and destination
                if changes == 0:
                    return (True, "Direct route available")
                else:
                    return (True, f"Route available with {changes} train change(s)")
            
            # Calculate distance to provide helpful feedback
            distance = self.station_database.calculate_haversine_distance(
                from_obj.coordinates,
                to_obj.coordinates
            )
            
            return (False, f"No railway connection found between stations (distance: {distance:.1f}km)")
            
        except Exception as e:
            logger.error(f"Error validating station connectivity: {e}")
            return (False, f"Connectivity check failed: {e}")
    
    def validate_via_station_addition(self, via_station: str, current_route: List[str]) -> Tuple[bool, str]:
        """
        Validate adding a via station to the current route.
        
        Args:
            via_station: Station to add as via station
            current_route: Current complete route [from, via1, via2, ..., to]
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            if not via_station:
                return (False, "Via station cannot be empty")
            
            if len(current_route) < 2:
                return (False, "Need both from and to stations before adding via stations")
            
            # Check if station already exists in route
            if via_station in current_route:
                return (False, f"Station '{via_station}' is already in the route")
            
            # Check if via station exists in database
            via_parsed = self.station_database.parse_station_name(via_station)
            via_obj = self.station_database.get_station_by_name(via_parsed)
            if not via_obj:
                return (False, f"Station '{via_station}' not found in database")
            
            # Create new route with via station added at the end (before destination)
            new_route = current_route[:-1] + [via_station] + [current_route[-1]]
            
            # Validate the new route would be reasonable
            validation_result = self._validate_user_created_route(new_route)
            if not validation_result[0]:
                return (False, f"Adding '{via_station}' would create an invalid route: {validation_result[1]}")
            
            return (True, f"Via station '{via_station}' can be added to route")
            
        except Exception as e:
            logger.error(f"Error validating via station addition: {e}")
            return (False, f"Via station validation failed: {e}")
    
    def validate_departure_time(self, departure_time: str, from_station: str) -> Tuple[bool, str]:
        """
        Validate departure time for a given station.
        
        Args:
            departure_time: Time in HH:MM format
            from_station: Origin station name
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            if not departure_time:
                return (True, "No departure time specified")
            
            # Validate time format
            try:
                hours, minutes = map(int, departure_time.split(':'))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    return (False, "Invalid time format. Use HH:MM (24-hour format)")
            except (ValueError, IndexError):
                return (False, "Invalid time format. Use HH:MM (24-hour format)")
            
            if not from_station:
                return (True, "Departure time format is valid")
            
            # Check if departure time is available for this station
            from_parsed = self.station_database.parse_station_name(from_station)
            valid_times = self._get_valid_departure_times(from_parsed)
            
            if valid_times:
                if departure_time in valid_times:
                    return (True, f"Departure time {departure_time} is available")
                else:
                    # Find nearest available time
                    nearest_time = self._find_nearest_valid_time(departure_time, valid_times)
                    if nearest_time:
                        return (False, f"Departure time {departure_time} not available. Nearest available: {nearest_time}")
                    else:
                        return (False, f"Departure time {departure_time} not available for this station")
            else:
                # No timetable data available - assume time is valid
                return (True, f"Departure time {departure_time} format is valid (no timetable data available)")
            
        except Exception as e:
            logger.error(f"Error validating departure time: {e}")
            return (False, f"Departure time validation failed: {e}")
    
    def _get_valid_departure_times(self, from_station: str) -> List[str]:
        """Get valid departure times for a station from the railway line data."""
        try:
            valid_times = []
            
            # Find which railway line contains this station
            lines = self.station_database.get_railway_lines_for_station(from_station)
            if not lines:
                return []
            
            # Use the first line to get timing data
            line_name = lines[0]
            railway_line = self.station_database.railway_lines.get(line_name)
            if not railway_line:
                return []
            
            # Load the JSON file to get timing data
            line_file = self.station_database.lines_dir / railway_line.file
            if not line_file.exists():
                return []
            
            try:
                import json
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                # Find the station in the JSON data
                for station_data in line_data.get('stations', []):
                    if station_data.get('name') == from_station:
                        times_data = station_data.get('times', {})
                        # Collect all times from all periods
                        for period, times in times_data.items():
                            if isinstance(times, list):
                                valid_times.extend(times)
                        break
                
            except Exception as json_error:
                logger.error(f"Error reading JSON file: {json_error}")
                return []
            
            # Sort times chronologically and remove duplicates
            valid_times = sorted(list(set(valid_times)))
            return valid_times
            
        except Exception as e:
            logger.error(f"Error getting valid departure times: {e}")
            return []
    
    def _find_nearest_valid_time(self, target_time: str, valid_times: List[str]) -> Optional[str]:
        """Find the nearest valid time to the target time."""
        try:
            if not valid_times:
                return None
            
            # Convert times to minutes for comparison
            def time_to_minutes(time_str):
                try:
                    hours, minutes = map(int, time_str.split(':'))
                    return hours * 60 + minutes
                except:
                    return 0
            
            target_minutes = time_to_minutes(target_time)
            
            # Find the closest time
            closest_time = None
            min_diff = float('inf')
            
            for valid_time in valid_times:
                valid_minutes = time_to_minutes(valid_time)
                diff = abs(target_minutes - valid_minutes)
                
                if diff < min_diff:
                    min_diff = diff
                    closest_time = valid_time
            
            return closest_time
            
        except Exception as e:
            logger.error(f"Error finding nearest valid time: {e}")
            return None
    
    def show_validation_warning(self, message: str, title: str = "Route Validation Warning"):
        """
        Show a validation warning dialog to the user.
        
        Args:
            message: Warning message
            title: Dialog title
        """
        try:
            QMessageBox.warning(self.parent_dialog, title, message)
        except Exception as e:
            logger.error(f"Error showing validation warning: {e}")
    
    def show_validation_error(self, message: str, title: str = "Route Validation Error"):
        """
        Show a validation error dialog to the user.
        
        Args:
            message: Error message
            title: Dialog title
        """
        try:
            QMessageBox.critical(self.parent_dialog, title, message)
        except Exception as e:
            logger.error(f"Error showing validation error: {e}")
    
    def get_validation_summary(self) -> dict:
        """
        Get a summary of the current validation state.
        
        Returns:
            Dictionary containing validation information
        """
        try:
            complete_route = self.route_state.get_complete_route()
            
            if len(complete_route) < 2:
                return {
                    'route_valid': False,
                    'message': 'Incomplete route - need both from and to stations',
                    'complete_route': complete_route,
                    'connectivity_valid': False,
                    'departure_time_valid': True
                }
            
            # Validate complete route
            route_validation = self.validate_route(
                complete_route[0], 
                complete_route[1:-1], 
                complete_route[-1]
            )
            
            # Validate connectivity
            connectivity_validation = self.validate_station_connectivity(
                complete_route[0], 
                complete_route[-1]
            )
            
            # Validate departure time
            departure_time_validation = self.validate_departure_time(
                self.route_state.departure_time,
                complete_route[0]
            )
            
            return {
                'route_valid': route_validation[0],
                'route_message': route_validation[1],
                'complete_route': complete_route,
                'connectivity_valid': connectivity_validation[0],
                'connectivity_message': connectivity_validation[1],
                'departure_time_valid': departure_time_validation[0],
                'departure_time_message': departure_time_validation[1],
                'overall_valid': route_validation[0] and connectivity_validation[0] and departure_time_validation[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            return {
                'route_valid': False,
                'message': f'Validation error: {e}',
                'complete_route': [],
                'connectivity_valid': False,
                'departure_time_valid': False,
                'overall_valid': False
            }