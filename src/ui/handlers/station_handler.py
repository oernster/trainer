"""
Station Handler for the Train Times application.

This module handles all station-related logic including autocomplete,
validation, and station selection for the settings dialog.
"""

import logging
from typing import Optional, List
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject, Signal, QTimer, QStringListModel

logger = logging.getLogger(__name__)


class StationHandler(QObject):
    """Handles station selection, autocomplete, and validation logic."""
    
    # Signals
    from_station_changed = Signal(str)  # Emitted when from station changes
    to_station_changed = Signal(str)    # Emitted when to station changes
    stations_validated = Signal(bool)   # Emitted when station validation changes
    
    def __init__(self, parent_dialog, station_database):
        """
        Initialize the station handler.
        
        Args:
            parent_dialog: The parent settings dialog
            station_database: Station database manager
        """
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.station_database = station_database
        
        # Current station state
        self._from_station = ""
        self._to_station = ""
        self._stations_valid = False
        
        logger.debug("StationHandler initialized")
    
    @property
    def from_station(self) -> str:
        """Get the current from station."""
        return self._from_station
    
    @property
    def to_station(self) -> str:
        """Get the current to station."""
        return self._to_station
    
    @property
    def stations_valid(self) -> bool:
        """Check if both stations are valid and different."""
        return self._stations_valid
    
    def api_search_stations(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for stations using the internal database with disambiguation.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching station names
        """
        try:
            # Use internal database for station search with line context for duplicates
            stations = self.station_database.search_stations(query, limit)
            logger.debug(f"Found {len(stations)} stations matching '{query}' in internal database")
            return stations
            
        except Exception as e:
            logger.error(f"Error in database station search: {e}")
            return []
    
    def api_get_station_name(self, station_name: str, strict_mode: bool = False) -> Optional[str]:
        """
        Get validated station name using the internal database with smart matching.
        
        Args:
            station_name: The station name to look up
            strict_mode: If True, only allow exact matches (for validating autocomplete selections)
            
        Returns:
            Validated station name or None if not found
        """
        try:
            station_name_clean = station_name.strip()
            logger.debug(f"api_get_station_name called with: '{station_name_clean}', strict_mode={strict_mode}")
            
            # First try exact match with original name (don't parse yet)
            # Station names are used directly now - no codes needed
            station_obj = self.station_database.get_station_by_name(station_name_clean)
            if station_obj:
                logger.debug(f"Found exact station '{station_obj.name}' for '{station_name_clean}' in internal database")
                return station_obj.name
            
            # If that fails, try with parsed name (remove parentheses)
            parsed_name = self.station_database.parse_station_name(station_name_clean)
            logger.debug(f"Trying parsed name: '{parsed_name}'")
            
            if parsed_name != station_name_clean:
                parsed_station_obj = self.station_database.get_station_by_name(parsed_name)
                if parsed_station_obj:
                    logger.debug(f"Found station '{parsed_station_obj.name}' for parsed name '{parsed_name}' in internal database")
                    return parsed_station_obj.name
            
            # In strict mode, don't use fallback search - require exact matches
            if strict_mode:
                logger.debug(f"Strict mode: No exact match found for '{station_name_clean}'")
                return None
            
            # If exact matches fail, try to find the best match from search results
            logger.debug(f"No exact match found, trying search for '{station_name_clean}'...")
            search_results = self.station_database.search_stations(station_name_clean, limit=5)
            
            if search_results:
                logger.debug(f"Search results: {search_results}")
                # Use the first (best) match from search results
                best_match = search_results[0]
                
                # Try the best match directly first (without parsing)
                best_match_obj = self.station_database.get_station_by_name(best_match)
                if best_match_obj:
                    logger.debug(f"Found best match station '{best_match_obj.name}' for '{best_match}' (from search)")
                    return best_match_obj.name
                
                # If that fails, try parsing the best match
                best_match_parsed = self.station_database.parse_station_name(best_match)
                if best_match_parsed != best_match:
                    best_match_parsed_obj = self.station_database.get_station_by_name(best_match_parsed)
                    if best_match_parsed_obj:
                        logger.debug(f"Found best match station '{best_match_parsed_obj.name}' for parsed '{best_match_parsed}' (from search)")
                        return best_match_parsed_obj.name
                
                logger.debug(f"Best match '{best_match}' found but no station available")
            else:
                logger.debug(f"No search results found for '{station_name_clean}'")
            
            return None
            
        except Exception as e:
            logger.error(f"Error in database station name lookup: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def on_from_name_changed(self, text: str):
        """Handle from station name text change with immediate lookup."""
        try:
            if not text.strip():
                # Clear to station when from station is cleared
                self.clear_to_station()
                return
            
            # Immediate lookup for better responsiveness
            self.lookup_from_stations()
            
        except Exception as e:
            logger.error(f"Error in on_from_name_changed: {e}")
    
    def on_from_name_completed(self, text: str):
        """Handle from station name autocomplete selection."""
        try:
            self.set_from_station_by_name(text)
        except Exception as e:
            logger.error(f"Error in on_from_name_completed: {e}")
    
    def on_to_name_changed(self, text: str):
        """Handle to station name text change with immediate filtering."""
        try:
            if not hasattr(self.parent_dialog, 'to_name_edit') or not self.parent_dialog.to_name_edit.isEnabled():
                return
            
            # If text is empty, reset completer
            if not text.strip():
                self._update_stations_validation()
                return
            
            # Update completer prefix for immediate filtering
            if len(text) >= 1 and hasattr(self.parent_dialog, 'to_name_completer'):
                self.parent_dialog.to_name_completer.setCompletionPrefix(text)
                # Force completer to show popup if there are matches
                if self.parent_dialog.to_name_completer.completionCount() > 0:
                    self.parent_dialog.to_name_completer.complete()
            
            # Update stations validation
            self._update_stations_validation()
            
        except Exception as e:
            logger.error(f"Error in on_to_name_changed: {e}")
    
    def on_to_name_completed(self, text: str):
        """Handle to station name autocomplete selection."""
        try:
            self.set_to_station_by_name(text)
        except Exception as e:
            logger.error(f"Error in on_to_name_completed: {e}")
    
    def lookup_from_stations(self):
        """Perform lookup for from stations."""
        try:
            if not hasattr(self.parent_dialog, 'from_name_edit'):
                return
                
            query = self.parent_dialog.from_name_edit.text().strip()
            if not query or len(query) < 1:
                return
            
            # Make API call to search for stations
            matches = self.api_search_stations(query)
            
            # Update completer
            if hasattr(self.parent_dialog, 'from_name_completer'):
                model = QStringListModel(matches)
                self.parent_dialog.from_name_completer.setModel(model)
                
        except Exception as e:
            logger.error(f"Error in lookup_from_stations: {e}")
    
    def set_from_station_by_name(self, name: str):
        """Set from station by name and enable to station."""
        try:
            if not name or not name.strip():
                # Clear via stations when from station is cleared
                self._from_station = ""
                self.from_station_changed.emit("")
                self.clear_to_station()
                return
                
            validated_name = self.api_get_station_name(name.strip())
            if validated_name:
                self._from_station = validated_name
                self.from_station_changed.emit(validated_name)
                
                # Enable to station field
                if hasattr(self.parent_dialog, 'to_name_edit'):
                    self.parent_dialog.to_name_edit.setEnabled(True)
                    self.parent_dialog.to_name_edit.setPlaceholderText("Start typing destination station...")
                
                # Pre-populate to station dropdown with reachable destinations
                self.populate_to_stations_completer(validated_name)
                
                # Update stations validation
                self._update_stations_validation()
            else:
                # No valid station found
                self._from_station = ""
                self.from_station_changed.emit("")
                self.clear_to_station()
                    
        except Exception as e:
            logger.error(f"Error in set_from_station_by_name: {e}")
            self._from_station = ""
            self.from_station_changed.emit("")
            self.clear_to_station()
    
    def set_to_station_by_name(self, name: str):
        """Set to station by name."""
        try:
            if not name or not name.strip():
                self._to_station = ""
                self.to_station_changed.emit("")
                self._update_stations_validation()
                return
            
            validated_name = self.api_get_station_name(name.strip())
            if validated_name:
                self._to_station = validated_name
                self.to_station_changed.emit(validated_name)
                
                # Update to station text field
                if hasattr(self.parent_dialog, 'to_name_edit'):
                    # Temporarily disconnect signals to prevent recursive calls
                    try:
                        self.parent_dialog.to_name_edit.textChanged.disconnect()
                        self.parent_dialog.to_name_edit.setText(validated_name)
                        self.parent_dialog.to_name_edit.textChanged.connect(self.on_to_name_changed)
                    except (TypeError, RuntimeError):
                        # Handle case where signal is not connected
                        self.parent_dialog.to_name_edit.setText(validated_name)
                        self.parent_dialog.to_name_edit.textChanged.connect(self.on_to_name_changed)
            else:
                self._to_station = ""
                self.to_station_changed.emit("")
            
            # Update stations validation
            self._update_stations_validation()
                    
        except Exception as e:
            logger.error(f"Error in set_to_station_by_name: {e}")
            self._to_station = ""
            self.to_station_changed.emit("")
            self._update_stations_validation()
    
    def populate_to_stations_completer(self, from_station_name: str):
        """Populate to station completer with all available stations."""
        try:
            if not hasattr(self.parent_dialog, 'to_name_edit') or not hasattr(self.parent_dialog, 'to_name_completer'):
                return
                
            # Set loading state
            self.parent_dialog.to_name_edit.setPlaceholderText("Loading destinations...")
            
            # Get all stations with disambiguation context
            all_stations = self.station_database.get_all_stations_with_context()
            
            if all_stations:
                # Sort stations alphabetically for better UX
                all_stations.sort()
                
                # Update completer with all stations
                model = QStringListModel(all_stations)
                self.parent_dialog.to_name_completer.setModel(model)
                
                # Configure completer for better performance
                self.parent_dialog.to_name_completer.setCompletionPrefix("")
                self.parent_dialog.to_name_completer.setCurrentRow(0)
                
                # Set success placeholder text
                self.parent_dialog.to_name_edit.setPlaceholderText(f"Type to search {len(all_stations)} stations...")
                
                logger.debug(f"Loaded {len(all_stations)} stations with disambiguation from database")
            else:
                # No stations found - set error message
                logger.error("No stations found in database")
                self.parent_dialog.to_name_edit.setPlaceholderText("No stations available")
            
        except Exception as e:
            logger.error(f"Error in populate_to_stations_completer: {e}")
            if hasattr(self.parent_dialog, 'to_name_edit'):
                self.parent_dialog.to_name_edit.setPlaceholderText("Error loading stations")
    
    def clear_to_station(self):
        """Clear to station selection and disable field."""
        try:
            self._to_station = ""
            self.to_station_changed.emit("")
            
            if hasattr(self.parent_dialog, 'to_name_edit'):
                self.parent_dialog.to_name_edit.clear()
                self.parent_dialog.to_name_edit.setEnabled(False)
                self.parent_dialog.to_name_edit.setPlaceholderText("Select a From station first...")
            
            self._update_stations_validation()
            
        except Exception as e:
            logger.error(f"Error clearing to station: {e}")
    
    def _update_stations_validation(self):
        """Update the stations validation status."""
        try:
            # Check if we have both stations and they're different
            old_valid = self._stations_valid
            self._stations_valid = bool(
                self._from_station and 
                self._to_station and 
                self._from_station != self._to_station
            )
            
            # Emit signal if validation status changed
            if old_valid != self._stations_valid:
                self.stations_validated.emit(self._stations_valid)
                logger.debug(f"Stations validation updated: {self._stations_valid}")
            
        except Exception as e:
            logger.error(f"Error updating stations validation: {e}")
    
    def reset_stations(self):
        """Reset both stations to empty state."""
        try:
            self._from_station = ""
            self._to_station = ""
            self._stations_valid = False
            
            # Clear UI elements
            if hasattr(self.parent_dialog, 'from_name_edit'):
                self.parent_dialog.from_name_edit.clear()
            
            self.clear_to_station()
            
            # Emit signals
            self.from_station_changed.emit("")
            self.to_station_changed.emit("")
            self.stations_validated.emit(False)
            
            logger.debug("Stations reset to empty state")
            
        except Exception as e:
            logger.error(f"Error resetting stations: {e}")
    
    def get_stations_summary(self) -> dict:
        """
        Get a summary of the current station state.
        
        Returns:
            Dictionary containing current station information
        """
        return {
            'from_station': self._from_station,
            'to_station': self._to_station,
            'stations_valid': self._stations_valid,
            'has_from_station': bool(self._from_station),
            'has_to_station': bool(self._to_station),
            'stations_different': self._from_station != self._to_station if self._from_station and self._to_station else False
        }