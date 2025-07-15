"""
Route Handler for the Train Times application.

This module handles all route-related operations including route finding,
optimization, and via station management for the settings dialog.
"""

import logging
from typing import List, Optional, Dict, Any
from PySide6.QtWidgets import QMessageBox, QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class RouteHandler(QObject):
    """Handles route finding, optimization, and via station management."""
    
    # Signals
    route_found = Signal(list)  # Emitted when a route is found
    route_optimization_completed = Signal(bool, str, list)  # success, message, route
    via_station_added = Signal(str)  # Emitted when via station is added
    via_station_removed = Signal(str)  # Emitted when via station is removed
    
    def __init__(self, parent_dialog, station_database, route_state):
        """
        Initialize the route handler.
        
        Args:
            parent_dialog: The parent settings dialog
            station_database: Station database manager
            route_state: Route state manager
        """
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.station_database = station_database
        self.route_state = route_state
        
        logger.debug("RouteHandler initialized")
    
    def add_via_station(self):
        """Add a via station to the route and automatically optimize."""
        try:
            if not hasattr(self.parent_dialog, 'add_via_combo'):
                return
                
            via_station = self.parent_dialog.add_via_combo.currentText().strip()
            if not via_station:
                return
            
            # Check if station is already in the list
            if via_station in self.route_state.via_stations:
                QMessageBox.information(
                    self.parent_dialog, 
                    "Duplicate Station", 
                    f"'{via_station}' is already in the via stations list."
                )
                return
            
            # Get current from and to stations
            from_station = self.route_state.from_station
            to_station = self.route_state.to_station
            
            if not from_station or not to_station:
                QMessageBox.warning(
                    self.parent_dialog, 
                    "Missing Stations", 
                    "Please select both From and To stations first."
                )
                return
            
            # Add the via station to the route state
            if self.route_state.add_via_station(via_station):
                # Reset auto-fixed flag since user manually added a station
                self.route_state.route_auto_fixed = False
                
                # Clear the combo box
                self.parent_dialog.add_via_combo.setCurrentText("")
                
                # Automatically find the fastest route that includes the new via station
                self.auto_optimize_route_with_via_stations(from_station, to_station)
                
                # Emit signal
                self.via_station_added.emit(via_station)
                
                logger.debug(f"Via station added: {via_station}")
            
        except Exception as e:
            logger.error(f"Error adding via station: {e}")
    
    def remove_via_station_by_name(self, station_name: str):
        """Remove a via station by name."""
        try:
            if self.route_state.remove_via_station(station_name):
                self.via_station_removed.emit(station_name)
                logger.debug(f"Via station removed: {station_name}")
            
        except Exception as e:
            logger.error(f"Error removing via station by name: {e}")
    
    def suggest_route(self):
        """Suggest a route between from and to stations."""
        try:
            from_station = self.route_state.from_station
            to_station = self.route_state.to_station
            
            if not from_station or not to_station:
                QMessageBox.information(
                    self.parent_dialog, 
                    "Missing Stations", 
                    "Please select both From and To stations first."
                )
                return
            
            # Show progress indicator
            if hasattr(self.parent_dialog, 'suggest_route_button'):
                self.parent_dialog.suggest_route_button.setEnabled(False)
                self.parent_dialog.suggest_route_button.setText("Suggesting...")
            
            if hasattr(self.parent_dialog, 'route_info_widget'):
                self.parent_dialog.route_info_widget.set_progress_message("suggest_via", "Finding route suggestions...")
            
            # Force UI update
            QApplication.processEvents()
            
            # Parse station names
            from_parsed = self.station_database.parse_station_name(from_station)
            to_parsed = self.station_database.parse_station_name(to_station)
            
            # Get departure time if specified
            departure_time = None
            if hasattr(self.parent_dialog, 'departure_time_picker') and not self.parent_dialog.departure_time_picker.is_empty():
                departure_time = self.parent_dialog.departure_time_picker.get_time()
            
            # Get via station suggestions
            via_stations = self.station_database.suggest_via_stations(from_parsed, to_parsed)
            
            # Re-enable button
            if hasattr(self.parent_dialog, 'suggest_route_button'):
                self.parent_dialog.suggest_route_button.setEnabled(True)
                self.parent_dialog.suggest_route_button.setText("Suggest Route")
            
            if hasattr(self.parent_dialog, 'route_info_widget'):
                self.parent_dialog.route_info_widget.update_route_info(
                    from_station, to_station, self.route_state.via_stations, self.route_state.route_auto_fixed
                )
            
            if via_stations:
                self.show_route_suggestion_dialog(from_station, to_station, via_stations)
            else:
                QMessageBox.information(
                    self.parent_dialog,
                    "No Route Found",
                    f"No intermediate stations found for route from {from_station} to {to_station}."
                )
                
        except Exception as e:
            logger.error(f"Error suggesting route: {e}")
            # Ensure button is re-enabled
            if hasattr(self.parent_dialog, 'suggest_route_button'):
                self.parent_dialog.suggest_route_button.setEnabled(True)
                self.parent_dialog.suggest_route_button.setText("Suggest Route")
            QMessageBox.critical(self.parent_dialog, "Error", f"Failed to suggest route: {e}")
    
    def find_fastest_route(self):
        """Find the fastest route between from and to stations."""
        try:
            from_station = self.route_state.from_station
            to_station = self.route_state.to_station
            
            if not from_station or not to_station:
                QMessageBox.information(
                    self.parent_dialog, 
                    "Missing Stations", 
                    "Please select both From and To stations first."
                )
                return
            
            # Show progress indicator
            if hasattr(self.parent_dialog, 'fastest_route_button'):
                self.parent_dialog.fastest_route_button.setEnabled(False)
                self.parent_dialog.fastest_route_button.setText("Finding...")
            
            if hasattr(self.parent_dialog, 'route_info_widget'):
                self.parent_dialog.route_info_widget.set_progress_message("fastest_route", "Finding fastest route...")
            
            # Force UI update
            QApplication.processEvents()
            
            # Parse station names
            from_parsed = self.station_database.parse_station_name(from_station)
            to_parsed = self.station_database.parse_station_name(to_station)
            
            # Get departure time if specified
            departure_time = None
            if hasattr(self.parent_dialog, 'departure_time_picker') and not self.parent_dialog.departure_time_picker.is_empty():
                departure_time = self.parent_dialog.departure_time_picker.get_time()
            
            # Find the fastest route
            best_route = None
            try:
                routes = self.station_database.find_route_between_stations(from_parsed, to_parsed, departure_time=departure_time)
                if routes:
                    # Use the shortest route found
                    best_route = min(routes, key=len)
                    logger.debug(f"Found route via database manager: {' → '.join(best_route)}")
            except Exception as route_error:
                logger.error(f"Database route finding failed: {route_error}")
            
            # If database manager fails, try fallback method
            if not best_route:
                best_route = self._find_fastest_direct_route(from_parsed, to_parsed)
                if best_route:
                    logger.debug(f"Found route via fallback: {' → '.join(best_route)}")
            
            # Re-enable button
            if hasattr(self.parent_dialog, 'fastest_route_button'):
                self.parent_dialog.fastest_route_button.setEnabled(True)
                self.parent_dialog.fastest_route_button.setText("Fastest Route")
            
            if best_route:
                # Identify actual train change points
                train_change_stations = []
                try:
                    train_change_stations = self.station_database.identify_train_changes(best_route)
                    logger.debug(f"Train changes identified: {train_change_stations}")
                except Exception as train_change_error:
                    logger.warning(f"Error identifying train changes: {train_change_error}")
                
                # Update route state
                self.route_state.set_via_stations(train_change_stations)
                self.route_state.route_auto_fixed = True
                
                # Update UI
                if hasattr(self.parent_dialog, 'route_info_widget'):
                    self.parent_dialog.route_info_widget.update_route_info(
                        from_station, to_station, train_change_stations, True
                    )
                
                # Show result message
                if train_change_stations:
                    QMessageBox.information(
                        self.parent_dialog,
                        "Fastest Route Found",
                        f"Optimal route with {len(train_change_stations)} train change(s):\n{' → '.join(best_route)}"
                    )
                else:
                    QMessageBox.information(
                        self.parent_dialog,
                        "Direct Route",
                        f"Direct route is optimal:\n{' → '.join(best_route)}"
                    )
                
                # Emit signal
                self.route_found.emit(best_route)
                
            else:
                if hasattr(self.parent_dialog, 'route_info_widget'):
                    self.parent_dialog.route_info_widget.update_route_info(
                        from_station, to_station, self.route_state.via_stations, self.route_state.route_auto_fixed
                    )
                
                QMessageBox.information(
                    self.parent_dialog,
                    "No Route Found",
                    "No optimal route could be found between the selected stations."
                )
                
        except Exception as e:
            logger.error(f"Error finding fastest route: {e}")
            # Ensure button is re-enabled
            if hasattr(self.parent_dialog, 'fastest_route_button'):
                self.parent_dialog.fastest_route_button.setEnabled(True)
                self.parent_dialog.fastest_route_button.setText("Fastest Route")
            QMessageBox.critical(self.parent_dialog, "Error", f"Failed to find fastest route: {e}")
    
    def auto_fix_route_from_button(self):
        """Auto-fix route when button is clicked."""
        try:
            from_station = self.route_state.from_station
            to_station = self.route_state.to_station
            
            if not from_station or not to_station:
                QMessageBox.information(
                    self.parent_dialog, 
                    "Missing Stations", 
                    "Please select both From and To stations first."
                )
                return
            
            # Show progress indicator
            if hasattr(self.parent_dialog, 'auto_fix_route_button'):
                self.parent_dialog.auto_fix_route_button.setEnabled(False)
                self.parent_dialog.auto_fix_route_button.setText("Auto-Fixing...")
            
            if hasattr(self.parent_dialog, 'route_info_widget'):
                self.parent_dialog.route_info_widget.set_progress_message("auto_fix", "Auto-fixing route...")
            
            # Force UI update
            QApplication.processEvents()
            
            # Parse station names to remove disambiguation
            from_parsed = self.station_database.parse_station_name(from_station)
            to_parsed = self.station_database.parse_station_name(to_station)
            
            # Get departure time if specified
            departure_time = None
            if hasattr(self.parent_dialog, 'departure_time_picker') and not self.parent_dialog.departure_time_picker.is_empty():
                departure_time = self.parent_dialog.departure_time_picker.get_time()
            
            # Find a valid route
            best_route = None
            try:
                routes = self.station_database.find_route_between_stations(from_parsed, to_parsed, departure_time=departure_time)
                if routes:
                    # Use the best route (first one is typically best)
                    best_route = routes[0]
                    logger.debug(f"Auto-fix found route via database manager: {' → '.join(best_route)}")
            except Exception as route_error:
                logger.error(f"Database route finding failed: {route_error}")
            
            # If database manager fails, try fallback method
            if not best_route:
                best_route = self._find_simple_direct_route_fallback(from_parsed, to_parsed)
                if best_route:
                    logger.debug(f"Auto-fix found route via fallback: {' → '.join(best_route)}")
            
            # Re-enable button
            if hasattr(self.parent_dialog, 'auto_fix_route_button'):
                self.parent_dialog.auto_fix_route_button.setEnabled(True)
                self.parent_dialog.auto_fix_route_button.setText("Auto-Fix Route")
            
            if best_route:
                # Identify actual train change points
                train_changes = []
                try:
                    train_changes = self.station_database.identify_train_changes(best_route)
                except Exception as train_change_error:
                    logger.warning(f"Error identifying train changes: {train_change_error}")
                
                # Update route state
                self.route_state.set_via_stations(train_changes)
                self.route_state.route_auto_fixed = True
                
                # Update UI
                if hasattr(self.parent_dialog, 'route_info_widget'):
                    self.parent_dialog.route_info_widget.update_route_info(
                        from_station, to_station, train_changes, True
                    )
                
                # Show success message
                if train_changes:
                    QMessageBox.information(
                        self.parent_dialog,
                        "Route Fixed",
                        f"Route has been automatically fixed with {len(train_changes)} train changes:\n"
                        f"{' → '.join(best_route)}"
                    )
                else:
                    QMessageBox.information(
                        self.parent_dialog,
                        "Route Fixed",
                        "Route has been fixed - direct connection is optimal."
                    )
                
                # Emit signal
                self.route_optimization_completed.emit(True, "Route fixed successfully", best_route)
                
            else:
                if hasattr(self.parent_dialog, 'route_info_widget'):
                    self.parent_dialog.route_info_widget.update_route_info(
                        from_station, to_station, self.route_state.via_stations, self.route_state.route_auto_fixed
                    )
                
                QMessageBox.warning(
                    self.parent_dialog,
                    "Cannot Fix Route",
                    "Unable to find a valid route between the selected stations."
                )
                
                # Emit signal
                self.route_optimization_completed.emit(False, "No valid route found", [])
            
        except Exception as e:
            logger.error(f"Error in auto_fix_route_from_button: {e}")
            # Ensure button is re-enabled
            if hasattr(self.parent_dialog, 'auto_fix_route_button'):
                self.parent_dialog.auto_fix_route_button.setEnabled(True)
                self.parent_dialog.auto_fix_route_button.setText("Auto-Fix Route")
            QMessageBox.critical(self.parent_dialog, "Error", f"Failed to auto-fix route: {e}")
    
    def show_route_suggestion_dialog(self, from_station: str, to_station: str, suggested_via: List[str]):
        """Show dialog with route suggestions."""
        try:
            dialog = QDialog(self.parent_dialog)
            dialog.setWindowTitle("Route Suggestions")
            dialog.setModal(True)
            dialog.resize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            # Info label
            info_label = QLabel(f"Suggested via stations for: {from_station} → {to_station}")
            info_label.setStyleSheet("font-weight: bold; color: #1976d2;")
            layout.addWidget(info_label)
            
            # Suggestions list
            suggestions_list = QListWidget()
            suggestions_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            for station in suggested_via[:10]:  # Limit to 10 suggestions
                suggestions_list.addItem(station)
            layout.addWidget(suggestions_list)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            select_all_button = QPushButton("Select All")
            select_all_button.clicked.connect(suggestions_list.selectAll)
            button_layout.addWidget(select_all_button)
            
            clear_button = QPushButton("Clear All")
            clear_button.clicked.connect(suggestions_list.clearSelection)
            button_layout.addWidget(clear_button)
            
            button_layout.addStretch()
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)
            
            ok_button = QPushButton("Add Selected")
            ok_button.clicked.connect(dialog.accept)
            ok_button.setDefault(True)
            button_layout.addWidget(ok_button)
            
            layout.addLayout(button_layout)
            
            # Show dialog and process result
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_items = suggestions_list.selectedItems()
                selected_stations = [item.text() for item in selected_items]
                
                if selected_stations:
                    # Add selected stations to existing via stations (don't clear existing ones)
                    for station in selected_stations:
                        if self.route_state.add_via_station(station):
                            self.via_station_added.emit(station)
                    
                    # Reset auto-fixed flag since user manually added stations
                    self.route_state.route_auto_fixed = False
                    
                    logger.debug(f"Added via stations from suggestions: {selected_stations}")
                    
        except Exception as e:
            logger.error(f"Error showing route suggestion dialog: {e}")
    
    def auto_optimize_route_with_via_stations(self, from_station: str, to_station: str):
        """Automatically optimize route while preserving user-selected via stations."""
        try:
            # Create a route that includes all current via stations
            current_route = [from_station] + self.route_state.via_stations + [to_station]
            
            # Use train change detection to find only essential interchange stations
            train_change_stations = self.station_database.identify_train_changes(current_route)
            
            # Create optimized via stations list with duplicates removed
            optimized_stations = []
            seen_stations = set()
            
            # Add user-selected via stations first (preserving their choices)
            for station in self.route_state.via_stations:
                if station not in seen_stations:
                    optimized_stations.append(station)
                    seen_stations.add(station)
            
            # Add only essential train change stations that aren't already included
            for station in train_change_stations:
                if station not in seen_stations and station != from_station and station != to_station:
                    optimized_stations.append(station)
                    seen_stations.add(station)
            
            # Update route state with the optimized, deduplicated list
            self.route_state.set_via_stations(optimized_stations)
            
            logger.debug(f"Route optimized with via stations: {optimized_stations}")
            
        except Exception as e:
            logger.error(f"Error in auto_optimize_route_with_via_stations: {e}")
    
    def _find_fastest_direct_route(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Find the fastest direct route using actual railway service patterns."""
        try:
            # Check if both stations are on the same line
            from_lines = set(self.station_database.get_railway_lines_for_station(from_station))
            to_lines = set(self.station_database.get_railway_lines_for_station(to_station))
            common_lines = from_lines.intersection(to_lines)
            
            if common_lines:
                line_name = list(common_lines)[0]
                railway_line = self.station_database.railway_lines.get(line_name)
                
                if railway_line:
                    # Try to find the best service pattern that serves both stations
                    best_route = self._find_best_service_pattern_route(railway_line, from_station, to_station)
                    if best_route:
                        return best_route
                    
                    # Fallback: create a realistic route based on actual line geography
                    return self._create_realistic_route(from_station, to_station, railway_line)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in fastest direct route: {e}")
            return None
    
    def _find_simple_direct_route_fallback(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Simple fallback for direct routes on the same line."""
        try:
            # Check if both stations are on the same line
            from_lines = set(self.station_database.get_railway_lines_for_station(from_station))
            to_lines = set(self.station_database.get_railway_lines_for_station(to_station))
            common_lines = from_lines.intersection(to_lines)
            
            if common_lines:
                # Use the first common line
                line_name = list(common_lines)[0]
                railway_line = self.station_database.railway_lines.get(line_name)
                
                if railway_line:
                    # Simple direct route
                    return [from_station, to_station]
            
            return None
            
        except Exception as e:
            logger.error(f"Error in simple direct route fallback: {e}")
            return None
    
    def _find_best_service_pattern_route(self, railway_line, from_station: str, to_station: str) -> Optional[List[str]]:
        """Find the best service pattern route that serves both stations."""
        try:
            if not railway_line.service_patterns:
                return None
            
            all_station_names = [s.name for s in railway_line.stations]
            
            # Try service patterns in order of preference: express, fast, semi_fast, stopping
            for pattern_name in ['express', 'fast', 'semi_fast', 'stopping']:
                pattern = railway_line.service_patterns.get_pattern(pattern_name)
                if not pattern:
                    continue
                
                # Get stations served by this pattern
                if pattern.stations == "all":
                    pattern_stations = all_station_names
                elif isinstance(pattern.stations, list):
                    pattern_stations = pattern.stations
                else:
                    continue
                
                # Check if both stations are served by this pattern
                if from_station in pattern_stations and to_station in pattern_stations:
                    try:
                        from_idx = pattern_stations.index(from_station)
                        to_idx = pattern_stations.index(to_station)
                        
                        # Extract route between stations in correct direction
                        if from_idx < to_idx:
                            route_stations = pattern_stations[from_idx:to_idx + 1]
                        else:
                            route_stations = list(pattern_stations[to_idx:from_idx + 1])
                            route_stations.reverse()
                        
                        if len(route_stations) >= 2:
                            return route_stations
                            
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding best service pattern route: {e}")
            return None
    
    def _create_realistic_route(self, from_station: str, to_station: str, railway_line) -> Optional[List[str]]:
        """Create a realistic route based on actual line geography."""
        try:
            all_stations = railway_line.stations
            station_names = [s.name for s in all_stations]
            
            # Find positions of from and to stations
            try:
                from_idx = station_names.index(from_station)
                to_idx = station_names.index(to_station)
            except ValueError:
                return None
            
            # Get the range of stations between from and to
            if from_idx < to_idx:
                route_stations = all_stations[from_idx:to_idx + 1]
            else:
                route_stations = list(all_stations[to_idx:from_idx + 1])
                route_stations.reverse()
            
            # Create a realistic stopping pattern
            realistic_route = self._filter_to_realistic_stops(route_stations, railway_line)
            
            return [station.name for station in realistic_route] if realistic_route else None
            
        except Exception as e:
            logger.error(f"Error creating realistic route: {e}")
            return None
    
    def _filter_to_realistic_stops(self, route_stations, railway_line) -> List:
        """Filter stations to create a realistic stopping pattern."""
        try:
            if len(route_stations) <= 3:
                # Short routes - include all stations
                return route_stations
            
            realistic_stops = []
            
            # Always include first and last stations
            realistic_stops.append(route_stations[0])
            
            # For intermediate stations, apply realistic filtering rules
            for i, station in enumerate(route_stations[1:-1], 1):
                include_station = False
                
                # Always include major interchange stations
                if hasattr(station, 'interchange') and station.interchange:
                    include_station = True
                
                # Include major stations
                elif station.name in ['Clapham Junction', 'Woking', 'Basingstoke', 'Winchester', 
                                    'Southampton Central', 'London Victoria', 'London Waterloo', 
                                    'London Paddington', 'London Kings Cross', 'London Euston', 
                                    'London Liverpool Street', 'London Bridge']:
                    include_station = True
                
                # For longer routes, include some intermediate stations at regular intervals
                elif len(route_stations) > 8:
                    if i % 2 == 0:
                        include_station = True
                elif len(route_stations) > 5:
                    if i % 2 == 1:
                        include_station = True
                
                if include_station:
                    realistic_stops.append(station)
            
            # Always include the destination
            if route_stations[-1] not in realistic_stops:
                realistic_stops.append(route_stations[-1])
            
            return realistic_stops
            
        except Exception as e:
            logger.error(f"Error filtering to realistic stops: {e}")
            return route_stations  # Return all stations as fallback