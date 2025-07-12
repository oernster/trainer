"""
Worker manager for coordinating all worker threads.

This module provides a centralized manager for all worker threads,
handling their lifecycle and coordinating operations between them.
"""

from typing import Dict, Optional, Any
import time
import logging

from PySide6.QtCore import QObject, Signal, QTimer
from .database_worker import DatabaseWorker, SearchRequest
from .route_worker import RouteWorker, RouteRequest


class WorkerManager(QObject):
    """Manages all worker threads and coordinates operations."""
    
    # Consolidated signals for UI
    operation_started = Signal(str, str)  # operation_type, request_id
    operation_completed = Signal(str, str, dict)  # operation_type, request_id, result
    operation_failed = Signal(str, str, str)  # operation_type, request_id, error_message
    progress_updated = Signal(str, int, str)  # request_id, percentage, message
    
    def __init__(self, station_db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = station_db_manager
        self.logger = logging.getLogger(__name__)
        
        # Create worker instances
        self.database_worker = DatabaseWorker(station_db_manager, self)
        self.route_worker = RouteWorker(station_db_manager, self)
        
        # Track pending operations
        self.pending_operations: Dict[str, Dict[str, Any]] = {}
        
        # Setup signal connections
        self._setup_signal_connections()
        
        # Start worker threads
        self.database_worker.start_thread()
        self.route_worker.start_thread()
        
        # Setup periodic cache cleanup
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_caches)
        self.cleanup_timer.start(300000)  # 5 minutes
        
        self.logger.info("WorkerManager initialized with all worker threads")
        
    def _setup_signal_connections(self):
        """Setup signal connections between workers and manager."""
        # Database worker signals
        self.database_worker.search_completed.connect(self._on_search_completed)
        self.database_worker.database_loaded.connect(self._on_database_loaded)
        self.database_worker.stations_loaded.connect(self._on_stations_loaded)
        self.database_worker.progress.connect(self._on_database_progress)
        self.database_worker.error.connect(self._on_database_error)
        
        # Route worker signals
        self.route_worker.route_calculated.connect(self._on_route_calculated)
        self.route_worker.route_fixed.connect(self._on_route_fixed)
        self.route_worker.via_stations_suggested.connect(self._on_via_suggested)
        self.route_worker.route_validated.connect(self._on_route_validated)
        self.route_worker.progress.connect(self._on_route_progress)
        self.route_worker.error.connect(self._on_route_error)
        
    def search_stations_async(self, query: str, limit: int = 10) -> str:
        """Request asynchronous station search."""
        request_id = f"search_{int(time.time() * 1000)}"
        
        request = SearchRequest(
            query=query,
            limit=limit,
            request_id=request_id,
            timestamp=time.time()
        )
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'search',
            'start_time': time.time(),
            'query': query,
            'limit': limit
        }
        
        # Emit operation started signal
        self.operation_started.emit('search', request_id)
        
        # Send request to worker
        self.database_worker.search_requested.emit(request)
        
        self.logger.debug(f"Search request queued: {query} (ID: {request_id})")
        return request_id
        
    def calculate_route_async(self, from_station: str, to_station: str, max_changes: int = 3) -> str:
        """Request asynchronous route calculation."""
        request_id = f"route_{int(time.time() * 1000)}"
        
        request = RouteRequest(
            from_station=from_station,
            to_station=to_station,
            max_changes=max_changes,
            request_id=request_id,
            operation_type="find_route"
        )
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'route_calculation',
            'start_time': time.time(),
            'from_station': from_station,
            'to_station': to_station,
            'max_changes': max_changes
        }
        
        # Emit operation started signal
        self.operation_started.emit('route_calculation', request_id)
        
        # Send request to worker
        self.route_worker.route_requested.emit(request)
        
        self.logger.debug(f"Route calculation request queued: {from_station} -> {to_station} (ID: {request_id})")
        return request_id
        
    def auto_fix_route_async(self, from_station: str, to_station: str) -> str:
        """Request asynchronous route auto-fix."""
        request_id = f"autofix_{int(time.time() * 1000)}"
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'auto_fix',
            'start_time': time.time(),
            'from_station': from_station,
            'to_station': to_station
        }
        
        # Emit operation started signal
        self.operation_started.emit('auto_fix', request_id)
        
        # Send request to worker
        self.route_worker.auto_fix_requested.emit(from_station, to_station, request_id)
        
        self.logger.debug(f"Auto-fix request queued: {from_station} -> {to_station} (ID: {request_id})")
        return request_id
        
    def suggest_via_stations_async(self, from_station: str, to_station: str) -> str:
        """Request asynchronous via station suggestions."""
        request_id = f"suggest_{int(time.time() * 1000)}"
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'suggest_via',
            'start_time': time.time(),
            'from_station': from_station,
            'to_station': to_station
        }
        
        # Emit operation started signal
        self.operation_started.emit('suggest_via', request_id)
        
        # Send request to worker
        self.route_worker.suggest_via_requested.emit(from_station, to_station, request_id)
        
        self.logger.debug(f"Via suggestion request queued: {from_station} -> {to_station} (ID: {request_id})")
        return request_id
        
    def find_fastest_route_async(self, from_station: str, to_station: str) -> str:
        """Request asynchronous fastest route calculation."""
        request_id = f"fastest_{int(time.time() * 1000)}"
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'fastest_route',
            'start_time': time.time(),
            'from_station': from_station,
            'to_station': to_station
        }
        
        # Emit operation started signal
        self.operation_started.emit('fastest_route', request_id)
        
        # Send request to worker
        self.route_worker.fastest_route_requested.emit(from_station, to_station, request_id)
        
        self.logger.debug(f"Fastest route request queued: {from_station} -> {to_station} (ID: {request_id})")
        return request_id
        
    def validate_route_async(self, route: list, from_station: str, to_station: str) -> str:
        """Request asynchronous route validation."""
        request_id = f"validate_{int(time.time() * 1000)}"
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'route_validation',
            'start_time': time.time(),
            'route': route,
            'from_station': from_station,
            'to_station': to_station
        }
        
        # Emit operation started signal
        self.operation_started.emit('route_validation', request_id)
        
        # Send request to worker
        self.route_worker.validate_route_requested.emit(route, from_station, to_station, request_id)
        
        self.logger.debug(f"Route validation request queued (ID: {request_id})")
        return request_id
        
    def get_all_stations_async(self) -> str:
        """Request all stations with context."""
        request_id = f"all_stations_{int(time.time() * 1000)}"
        
        # Track the operation
        self.pending_operations[request_id] = {
            'type': 'get_all_stations',
            'start_time': time.time()
        }
        
        # Emit operation started signal
        self.operation_started.emit('get_all_stations', request_id)
        
        # Send request to worker
        self.database_worker.get_all_stations_requested.emit(request_id)
        
        self.logger.debug(f"Get all stations request queued (ID: {request_id})")
        return request_id
        
    def cancel_operation(self, request_id: str) -> bool:
        """Cancel a pending operation."""
        if request_id in self.pending_operations:
            operation = self.pending_operations[request_id]
            operation_type = operation['type']
            
            # Request cancellation from appropriate worker
            if operation_type in ['search', 'get_all_stations']:
                self.database_worker.request_cancellation()
            elif operation_type in ['route_calculation', 'auto_fix', 'suggest_via', 'fastest_route', 'route_validation']:
                self.route_worker.request_cancellation()
                
            # Remove from pending operations
            del self.pending_operations[request_id]
            
            self.logger.info(f"Cancelled operation: {operation_type} (ID: {request_id})")
            return True
            
        return False
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            'database_worker': self.database_worker.get_cache_stats(),
            'route_worker': self.route_worker.get_cache_stats(),
            'pending_operations': len(self.pending_operations),
            'worker_performance': {
                'database': self.database_worker.get_performance_stats(),
                'route': self.route_worker.get_performance_stats()
            }
        }
        
    def shutdown(self):
        """Shutdown all worker threads gracefully."""
        self.logger.info("Shutting down WorkerManager...")
        
        # Stop cleanup timer
        self.cleanup_timer.stop()
        
        # Cancel all pending operations
        for request_id in list(self.pending_operations.keys()):
            self.cancel_operation(request_id)
            
        # Stop worker threads
        self.database_worker.stop_thread()
        self.route_worker.stop_thread()
        
        self.logger.info("WorkerManager shutdown complete")
        
    # Signal handlers for worker responses
    def _on_search_completed(self, result):
        """Handle search completion."""
        request_id = result.request_id
        if request_id in self.pending_operations:
            operation = self.pending_operations[request_id]
            
            # Calculate total time
            total_time = time.time() - operation['start_time']
            
            # Prepare result data
            result_data = {
                'stations': result.stations,
                'computation_time': result.computation_time,
                'total_time': total_time,
                'cache_hit': result.cache_hit,
                'total_matches': result.total_matches
            }
            
            # Emit completion signal
            self.operation_completed.emit('search', request_id, result_data)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
            
            self.logger.debug(f"Search completed: {len(result.stations)} results in {total_time:.3f}s (ID: {request_id})")
            
    def _on_route_calculated(self, result):
        """Handle route calculation completion."""
        request_id = result.request_id
        if request_id in self.pending_operations:
            operation = self.pending_operations[request_id]
            
            # Calculate total time
            total_time = time.time() - operation['start_time']
            
            # Prepare result data
            result_data = {
                'routes': result.routes,
                'computation_time': result.computation_time,
                'total_time': total_time,
                'cache_hit': result.cache_hit,
                'metadata': result.metadata or {}
            }
            
            # Emit completion signal
            self.operation_completed.emit('route_calculation', request_id, result_data)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
            
            self.logger.debug(f"Route calculation completed: {len(result.routes)} routes in {total_time:.3f}s (ID: {request_id})")
            
    def _on_route_fixed(self, route, success, message, request_id):
        """Handle route auto-fix completion."""
        if request_id in self.pending_operations:
            operation = self.pending_operations[request_id]
            
            # Calculate total time
            total_time = time.time() - operation['start_time']
            
            # Prepare result data
            result_data = {
                'route': route,  # This is the via stations from auto-fix
                'success': success,
                'message': message,
                'total_time': total_time
            }
            
            # Emit completion signal
            self.operation_completed.emit(operation['type'], request_id, result_data)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
            
            self.logger.debug(f"Route fix completed: {success} in {total_time:.3f}s (ID: {request_id})")
        else:
            self.logger.warning(f"Received route_fixed signal for unknown request_id: {request_id}")
                
    def _on_via_suggested(self, stations, request_id):
        """Handle via station suggestions completion."""
        if request_id in self.pending_operations:
            operation = self.pending_operations[request_id]
            
            # Calculate total time
            total_time = time.time() - operation['start_time']
            
            # Prepare result data
            result_data = {
                'via_stations': stations,
                'total_time': total_time
            }
            
            # Emit completion signal
            self.operation_completed.emit('suggest_via', request_id, result_data)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
            
            self.logger.debug(f"Via suggestions completed: {len(stations)} suggestions in {total_time:.3f}s (ID: {request_id})")
            
    def _on_route_validated(self, is_valid, message, request_id):
        """Handle route validation completion."""
        if request_id in self.pending_operations:
            operation = self.pending_operations[request_id]
            
            # Calculate total time
            total_time = time.time() - operation['start_time']
            
            # Prepare result data
            result_data = {
                'is_valid': is_valid,
                'message': message,
                'total_time': total_time
            }
            
            # Emit completion signal
            self.operation_completed.emit('route_validation', request_id, result_data)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
            
            self.logger.debug(f"Route validation completed: {is_valid} in {total_time:.3f}s (ID: {request_id})")
            
    def _on_stations_loaded(self, stations):
        """Handle all stations loading completion."""
        # Find the corresponding request ID
        for request_id, operation in self.pending_operations.items():
            if operation['type'] == 'get_all_stations':
                # Calculate total time
                total_time = time.time() - operation['start_time']
                
                # Prepare result data
                result_data = {
                    'stations': stations,
                    'total_time': total_time
                }
                
                # Emit completion signal
                self.operation_completed.emit('get_all_stations', request_id, result_data)
                
                # Remove from pending operations
                del self.pending_operations[request_id]
                
                self.logger.debug(f"All stations loaded: {len(stations)} stations in {total_time:.3f}s (ID: {request_id})")
                break
                
    def _on_database_loaded(self, success, message):
        """Handle database loading completion."""
        if success:
            self.logger.info("Database loaded successfully in worker thread")
        else:
            self.logger.error(f"Database loading failed: {message}")
            
    def _on_database_progress(self, percentage):
        """Handle database worker progress updates."""
        # Find active database operations and emit progress
        for request_id, operation in self.pending_operations.items():
            if operation['type'] in ['search', 'get_all_stations']:
                self.progress_updated.emit(request_id, percentage, "")
                break
                
    def _on_route_progress(self, percentage):
        """Handle route worker progress updates."""
        # Find active route operations and emit progress
        for request_id, operation in self.pending_operations.items():
            if operation['type'] in ['route_calculation', 'auto_fix', 'suggest_via', 'fastest_route', 'route_validation']:
                self.progress_updated.emit(request_id, percentage, "")
                break
                
    def _on_database_error(self, error_message):
        """Handle database worker errors."""
        # Find active database operations and emit error
        for request_id, operation in list(self.pending_operations.items()):
            if operation['type'] in ['search', 'get_all_stations']:
                self.operation_failed.emit(operation['type'], request_id, error_message)
                del self.pending_operations[request_id]
                break
                
    def _on_route_error(self, error_message):
        """Handle route worker errors."""
        # Find active route operations and emit error
        for request_id, operation in list(self.pending_operations.items()):
            if operation['type'] in ['route_calculation', 'auto_fix', 'suggest_via', 'fastest_route', 'route_validation']:
                self.operation_failed.emit(operation['type'], request_id, error_message)
                del self.pending_operations[request_id]
                break
                
    def _cleanup_caches(self):
        """Periodic cache cleanup."""
        try:
            self.database_worker.cleanup_caches()
            self.route_worker.cleanup_caches()
            self.logger.debug("Periodic cache cleanup completed")
        except Exception as e:
            self.logger.error(f"Cache cleanup error: {e}")