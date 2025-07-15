"""
Async Handler for the Train Times application.

This module handles all asynchronous operations and worker thread management
for the settings dialog, extracted for better separation of concerns.
"""

import logging
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class AsyncHandler(QObject):
    """Handles asynchronous operations and worker thread management."""
    
    def __init__(self, parent_dialog, worker_manager, station_database):
        """
        Initialize the async handler.
        
        Args:
            parent_dialog: The parent settings dialog
            worker_manager: Worker manager for async operations
            station_database: Station database manager
        """
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.worker_manager = worker_manager
        self.station_database = station_database
        self.pending_operations: Dict[str, Dict[str, Any]] = {}
        
        self._setup_worker_connections()
    
    def _setup_worker_connections(self):
        """Setup connections to worker threads for async operations."""
        try:
            # Connect worker manager signals only if worker_manager exists
            if self.worker_manager and hasattr(self.worker_manager, 'operation_completed'):
                self.worker_manager.operation_completed.connect(self._on_operation_completed)
                self.worker_manager.operation_failed.connect(self._on_operation_failed)
                self.worker_manager.progress_updated.connect(self._on_progress_updated)
                logger.debug("Worker connections established")
            else:
                logger.warning("Worker manager not available - skipping connections")
        except Exception as e:
            logger.warning(f"Worker connections setup failed: {e}")
    
    def _on_operation_completed(self, operation_type: str, request_id: str, result: dict):
        """Handle completed async operations."""
        if request_id not in self.pending_operations:
            return
            
        operation_info = self.pending_operations[request_id]
        
        if operation_type == "search":
            self._handle_search_completed(operation_info, result)
        elif operation_type == "auto_fix":
            self._handle_auto_fix_completed(operation_info, result)
        elif operation_type == "suggest_via":
            self._handle_via_suggestions_completed(operation_info, result)
        elif operation_type == "fastest_route":
            self._handle_fastest_route_completed(operation_info, result)
            
        # Remove from pending operations
        del self.pending_operations[request_id]
    
    def _on_operation_failed(self, operation_type: str, request_id: str, error_message: str):
        """Handle failed async operations."""
        if request_id in self.pending_operations:
            operation_info = self.pending_operations[request_id]
            
            # Show error message
            QMessageBox.critical(
                self.parent_dialog, 
                "Operation Failed", 
                f"{operation_type.title()} failed: {error_message}"
            )
            
            # Hide any progress indicators
            self._hide_progress_indicators(operation_info)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
    
    def _on_progress_updated(self, request_id: str, percentage: int, message: str):
        """Handle progress updates for async operations."""
        if request_id in self.pending_operations:
            operation_info = self.pending_operations[request_id]
            self._update_progress_indicator(operation_info, percentage, message)
    
    def _cancel_pending_operation(self, operation_type: str):
        """Cancel any pending operations of the specified type."""
        try:
            operations_to_cancel = []
            for request_id, operation_info in self.pending_operations.items():
                if operation_info.get('type') == operation_type:
                    operations_to_cancel.append(request_id)
            
            for request_id in operations_to_cancel:
                # Cancel the operation in worker manager if available
                if self.worker_manager and hasattr(self.worker_manager, 'cancel_operation'):
                    try:
                        self.worker_manager.cancel_operation(request_id)
                    except Exception as cancel_error:
                        logger.warning(f"Failed to cancel operation {request_id}: {cancel_error}")
                
                # Remove from pending operations
                if request_id in self.pending_operations:
                    del self.pending_operations[request_id]
                
        except Exception as e:
            logger.error(f"Error canceling pending operation {operation_type}: {e}")
    
    def _show_operation_progress(self, operation_type: str, message: str):
        """Show progress indicator for an operation."""
        try:
            # Update the route info label to show progress
            if hasattr(self.parent_dialog, 'route_info_label'):
                if operation_type == "auto_fix":
                    self.parent_dialog.route_info_label.setText(f"🔧 {message}")
                    self.parent_dialog.route_info_label.setStyleSheet("color: #ff9800; font-style: italic; font-weight: bold;")
                    # Disable the auto-fix button during operation
                    if hasattr(self.parent_dialog, 'auto_fix_route_button'):
                        self.parent_dialog.auto_fix_route_button.setEnabled(False)
                        self.parent_dialog.auto_fix_route_button.setText("Auto-Fixing...")
                elif operation_type == "suggest_via":
                    self.parent_dialog.route_info_label.setText(f"🔍 {message}")
                    self.parent_dialog.route_info_label.setStyleSheet("color: #1976d2; font-style: italic; font-weight: bold;")
                    # Disable the suggest button during operation
                    if hasattr(self.parent_dialog, 'suggest_route_button'):
                        self.parent_dialog.suggest_route_button.setEnabled(False)
                        self.parent_dialog.suggest_route_button.setText("Suggesting...")
                elif operation_type == "fastest_route":
                    self.parent_dialog.route_info_label.setText(f"⚡ {message}")
                    self.parent_dialog.route_info_label.setStyleSheet("color: #1976d2; font-style: italic; font-weight: bold;")
                    # Disable the fastest route button during operation
                    if hasattr(self.parent_dialog, 'fastest_route_button'):
                        self.parent_dialog.fastest_route_button.setEnabled(False)
                        self.parent_dialog.fastest_route_button.setText("Finding...")
                elif operation_type == "search":
                    # Could add search progress indicators here
                    pass
        except Exception as e:
            logger.error(f"Error showing operation progress: {e}")
    
    def _hide_progress_indicators(self, operation_info: dict):
        """Hide progress indicators for an operation."""
        try:
            operation_type = operation_info.get('type', '')
            if operation_type == "auto_fix":
                # Re-enable the auto-fix button
                if hasattr(self.parent_dialog, 'auto_fix_route_button'):
                    self.parent_dialog.auto_fix_route_button.setEnabled(True)
                    self.parent_dialog.auto_fix_route_button.setText("Auto-Fix Route")
                # Reset route info label
                if hasattr(self.parent_dialog, 'update_route_info'):
                    self.parent_dialog.update_route_info()
            elif operation_type == "suggest_via":
                # Re-enable the suggest button
                if hasattr(self.parent_dialog, 'suggest_route_button'):
                    self.parent_dialog.suggest_route_button.setEnabled(True)
                    self.parent_dialog.suggest_route_button.setText("Suggest Route")
                # Reset route info label
                if hasattr(self.parent_dialog, 'update_route_info'):
                    self.parent_dialog.update_route_info()
            elif operation_type == "fastest_route":
                # Re-enable the fastest route button
                if hasattr(self.parent_dialog, 'fastest_route_button'):
                    self.parent_dialog.fastest_route_button.setEnabled(True)
                    self.parent_dialog.fastest_route_button.setText("Fastest Route")
                # Reset route info label
                if hasattr(self.parent_dialog, 'update_route_info'):
                    self.parent_dialog.update_route_info()
        except Exception as e:
            logger.error(f"Error hiding progress indicators: {e}")
    
    def _update_progress_indicator(self, operation_info: dict, percentage: int, message: str):
        """Update progress indicator with percentage and message."""
        try:
            operation_type = operation_info.get('type', '')
            if hasattr(self.parent_dialog, 'route_info_label'):
                if operation_type == "auto_fix":
                    self.parent_dialog.route_info_label.setText(f"🔧 {message} ({percentage}%)")
                elif operation_type == "suggest_via":
                    self.parent_dialog.route_info_label.setText(f"🔍 {message} ({percentage}%)")
                elif operation_type == "fastest_route":
                    self.parent_dialog.route_info_label.setText(f"⚡ {message} ({percentage}%)")
        except Exception as e:
            logger.error(f"Error updating progress indicator: {e}")
    
    def _handle_search_completed(self, operation_info: dict, result: dict):
        """Handle completed search operations."""
        try:
            stations = result.get('stations', [])
            query = operation_info.get('query', '')
            
            # Update the appropriate completer based on the search type
            if 'from' in operation_info.get('type', ''):
                if hasattr(self.parent_dialog, 'from_name_completer'):
                    from PySide6.QtCore import QStringListModel
                    model = QStringListModel(stations)
                    self.parent_dialog.from_name_completer.setModel(model)
            else:
                if hasattr(self.parent_dialog, 'to_name_completer'):
                    from PySide6.QtCore import QStringListModel
                    model = QStringListModel(stations)
                    self.parent_dialog.to_name_completer.setModel(model)
                    
        except Exception as e:
            logger.error(f"Error handling search completion: {e}")
    
    def _handle_auto_fix_completed(self, operation_info: dict, result: dict):
        """Handle completed auto-fix operations."""
        try:
            # Hide progress indicators first
            self._hide_progress_indicators(operation_info)
            
            success = result.get('success', False)
            message = result.get('message', '')
            route = result.get('route', [])  # This is actually the via stations from auto-fix
            
            logger.debug(f"Auto-fix completed: success={success}, route={route}, message={message}")
            
            if success:
                # The route from auto-fix is actually the via stations (train changes)
                # No need to extract - use directly
                if hasattr(self.parent_dialog, 'via_stations'):
                    self.parent_dialog.via_stations.clear()
                    if route:  # If there are via stations
                        self.parent_dialog.via_stations.extend(route)
                
                # Mark route as auto-fixed
                if hasattr(self.parent_dialog, 'route_auto_fixed'):
                    self.parent_dialog.route_auto_fixed = True
                
                # Update UI
                if hasattr(self.parent_dialog, 'update_via_buttons'):
                    self.parent_dialog.update_via_buttons()
                if hasattr(self.parent_dialog, 'update_route_info'):
                    self.parent_dialog.update_route_info()
                
                # Show success message
                if route:  # If there are via stations
                    # Build full route for display
                    from_station = operation_info.get('from_station', '')
                    to_station = operation_info.get('to_station', '')
                    full_route = [from_station] + route + [to_station]
                    
                    QMessageBox.information(
                        self.parent_dialog,
                        "Route Fixed",
                        f"Route has been automatically fixed with {len(route)} train changes:\n"
                        f"{' → '.join(full_route)}"
                    )
                else:
                    QMessageBox.information(
                        self.parent_dialog,
                        "Route Fixed",
                        "Route has been fixed - direct connection is optimal."
                    )
            else:
                QMessageBox.warning(
                    self.parent_dialog,
                    "Cannot Fix Route",
                    message or "Unable to find a valid route between the selected stations."
                )
                
        except Exception as e:
            logger.error(f"Error handling auto-fix completion: {e}")
            # Ensure progress indicators are hidden even on error
            self._hide_progress_indicators(operation_info)
            QMessageBox.critical(self.parent_dialog, "Error", f"Failed to process auto-fix result: {e}")
    
    def _handle_via_suggestions_completed(self, operation_info: dict, result: dict):
        """Handle completed via suggestion operations."""
        try:
            suggestions = result.get('suggestions', [])
            from_station = operation_info.get('from_station', '')
            to_station = operation_info.get('to_station', '')
            
            if suggestions and hasattr(self.parent_dialog, 'show_route_suggestion_dialog'):
                self.parent_dialog.show_route_suggestion_dialog(from_station, to_station, suggestions)
            else:
                QMessageBox.information(
                    self.parent_dialog,
                    "No Route Found",
                    f"No intermediate stations found for route from {from_station} to {to_station}."
                )
                
        except Exception as e:
            logger.error(f"Error handling via suggestions completion: {e}")
    
    def _handle_fastest_route_completed(self, operation_info: dict, result: dict):
        """Handle completed fastest route operations."""
        try:
            success = result.get('success', False)
            route = result.get('route', [])
            message = result.get('message', '')
            
            if success and route:
                # Extract via stations from the route (exclude first and last)
                via_stations = []
                if len(route) > 2:
                    via_stations = route[1:-1]
                    if hasattr(self.parent_dialog, 'via_stations'):
                        self.parent_dialog.via_stations.clear()
                        self.parent_dialog.via_stations.extend(via_stations)
                else:
                    if hasattr(self.parent_dialog, 'via_stations'):
                        self.parent_dialog.via_stations.clear()
                
                # Mark route as auto-fixed
                if hasattr(self.parent_dialog, 'route_auto_fixed'):
                    self.parent_dialog.route_auto_fixed = True
                
                # Update UI
                if hasattr(self.parent_dialog, 'update_via_buttons'):
                    self.parent_dialog.update_via_buttons()
                if hasattr(self.parent_dialog, 'update_route_info'):
                    self.parent_dialog.update_route_info()
                
                # Show result message
                if via_stations:
                    QMessageBox.information(
                        self.parent_dialog,
                        "Fastest Route Found",
                        f"Optimal route with {len(via_stations)} train change(s):\n{' → '.join(route)}"
                    )
                else:
                    # Direct route means no train changes required, regardless of number of stations
                    QMessageBox.information(
                        self.parent_dialog,
                        "Direct Route",
                        f"Direct route is optimal:\n{' → '.join(route)}"
                    )
            else:
                QMessageBox.information(
                    self.parent_dialog,
                    "No Route Found",
                    message or "No optimal route could be found between the selected stations."
                )
                
        except Exception as e:
            logger.error(f"Error handling fastest route completion: {e}")
    
    def cleanup_worker_threads(self):
        """Clean up worker threads to prevent QThread destruction errors."""
        try:
            logger.debug("Cleaning up worker threads...")
            
            # Cancel all pending operations
            try:
                if self.pending_operations:
                    logger.debug(f"Canceling {len(self.pending_operations)} pending operations...")
                    for request_id in list(self.pending_operations.keys()):
                        try:
                            if (self.worker_manager and
                                hasattr(self.worker_manager, 'cancel_operation')):
                                self.worker_manager.cancel_operation(request_id)
                        except Exception as cancel_error:
                            logger.warning(f"Failed to cancel operation {request_id}: {cancel_error}")
                    
                    self.pending_operations.clear()
                    logger.debug("Pending operations cleared")
            except Exception as pending_error:
                logger.warning(f"Error clearing pending operations: {pending_error}")
            
            # Try to stop worker manager using various methods
            try:
                if self.worker_manager:
                    logger.debug("Attempting to stop worker manager...")
                    
                    # Try different stop methods
                    stop_methods = ['stop', 'quit', 'terminate', 'shutdown']
                    for method_name in stop_methods:
                        if hasattr(self.worker_manager, method_name):
                            try:
                                method = getattr(self.worker_manager, method_name)
                                method()
                                logger.debug(f"Worker manager stopped using {method_name}()")
                                break
                            except Exception as method_error:
                                logger.warning(f"{method_name}() failed: {method_error}")
                                continue
                    else:
                        logger.warning("No stop method found on worker manager")
                        
            except Exception as stop_error:
                logger.warning(f"Error stopping worker manager: {stop_error}")
            
            # Disconnect signals
            try:
                if self.worker_manager:
                    logger.debug("Disconnecting worker signals...")
                    
                    if hasattr(self.worker_manager, 'operation_completed'):
                        try:
                            self.worker_manager.operation_completed.disconnect()
                        except:
                            pass
                    
                    if hasattr(self.worker_manager, 'operation_failed'):
                        try:
                            self.worker_manager.operation_failed.disconnect()
                        except:
                            pass
                    
                    if hasattr(self.worker_manager, 'progress_updated'):
                        try:
                            self.worker_manager.progress_updated.disconnect()
                        except:
                            pass
                    
                    logger.debug("Worker signals disconnected")
            except Exception as disconnect_error:
                logger.warning(f"Error disconnecting worker signals: {disconnect_error}")
            
            # Set worker manager to None
            try:
                self.worker_manager = None
                logger.debug("Worker manager reference cleared")
            except Exception as clear_error:
                logger.warning(f"Error clearing worker manager reference: {clear_error}")
            
            logger.debug("Worker thread cleanup completed")
            
        except Exception as cleanup_error:
            logger.error(f"Worker thread cleanup failed: {cleanup_error}")
            # Continue anyway - don't let cleanup failure prevent dialog close