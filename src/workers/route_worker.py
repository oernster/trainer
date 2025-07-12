"""
Route worker for asynchronous route calculation operations.

This module provides a worker thread that handles route calculations, pathfinding,
auto-fix operations, and via station suggestions without blocking the UI thread.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import hashlib

from PySide6.QtCore import Signal
from .base_worker import BaseWorker
from ..cache.memory_cache import MemoryCache, CacheKey


@dataclass
class RouteRequest:
    """Route calculation request."""
    from_station: str
    to_station: str
    max_changes: int = 3
    request_id: str = ""
    operation_type: str = "find_route"  # find_route, auto_fix, suggest_via


@dataclass
class RouteResult:
    """Route calculation result."""
    routes: List[List[str]]
    computation_time: float
    request_id: str
    operation_type: str
    cache_hit: bool = False
    metadata: Optional[Dict] = None


class RouteWorker(BaseWorker):
    """Worker thread for route calculations."""
    
    # Route-specific signals
    route_calculated = Signal(RouteResult)
    route_fixed = Signal(list, bool, str, str)  # route, success, message, request_id
    via_stations_suggested = Signal(list, str)  # stations, request_id
    route_validated = Signal(bool, str, str)  # is_valid, message, request_id
    
    def __init__(self, station_db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = station_db_manager
        
        # Initialize caches
        self.route_cache = MemoryCache(max_size=500, default_ttl=1800)  # 30 minutes
        self.via_cache = MemoryCache(max_size=300, default_ttl=3600)    # 1 hour
        self.validation_cache = MemoryCache(max_size=200, default_ttl=1800)  # 30 minutes
        
        # Connect slot methods
        self.route_requested.connect(self.calculate_route)
        self.auto_fix_requested.connect(self.auto_fix_route)
        self.suggest_via_requested.connect(self.suggest_via_stations)
        self.fastest_route_requested.connect(self.find_fastest_route_async)
        self.validate_route_requested.connect(self.validate_route)
        
        # Performance tracking
        self._route_calculations = 0
        self._cache_hits = 0
        
    # Request signals
    route_requested = Signal(RouteRequest)
    auto_fix_requested = Signal(str, str, str)  # from, to, request_id
    suggest_via_requested = Signal(str, str, str)  # from, to, request_id
    fastest_route_requested = Signal(str, str, str)  # from, to, request_id
    validate_route_requested = Signal(list, str, str, str)  # route, from, to, request_id
    
    def on_thread_started(self):
        """Initialize route worker thread."""
        self.logger.info("Route worker thread started")
        self.started.emit()
        
    def on_thread_finished(self):
        """Cleanup route worker thread."""
        self.logger.info("Route worker thread finished")
        
        # Log performance stats
        stats = self.get_performance_stats()
        if stats:
            self.logger.info(f"Route worker performance: {stats}")
            
        self.finished.emit()
        
    def calculate_route(self, request: RouteRequest):
        """Calculate route between stations."""
        if self.is_cancelled():
            return
            
        self.reset_cancellation()
        start_time = time.time()
        
        try:
            with self.measure_operation("route_calculation"):
                # Check cache
                cache_key = CacheKey.route_key(request.from_station, request.to_station, request.max_changes)
                cached_routes = self.route_cache.get(cache_key)
                
                if cached_routes is not None:
                    self._cache_hits += 1
                    result = RouteResult(
                        routes=cached_routes,
                        computation_time=time.time() - start_time,
                        request_id=request.request_id,
                        operation_type=request.operation_type,
                        cache_hit=True,
                        metadata={"cache_hit": True}
                    )
                    self.route_calculated.emit(result)
                    return
                    
                self.emit_progress(10, "Initializing route calculation...")
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(30, "Building network graph...")
                
                # Perform route calculation
                routes = self.db_manager.find_route_between_stations(
                    request.from_station,
                    request.to_station,
                    request.max_changes
                )
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(80, "Optimizing routes...")
                
                # Cache the result
                self.route_cache.put(cache_key, routes, ttl=1800)  # 30 minutes
                
                self.emit_progress(100, "Route calculation completed")
                
                # Update counters
                self._route_calculations += 1
                
                # Emit result
                result = RouteResult(
                    routes=routes,
                    computation_time=time.time() - start_time,
                    request_id=request.request_id,
                    operation_type=request.operation_type,
                    cache_hit=False,
                    metadata={"cache_hit": False, "route_count": len(routes)}
                )
                self.route_calculated.emit(result)
                
        except Exception as e:
            self.logger.error(f"Route calculation error: {e}")
            self.error.emit(f"Route calculation failed: {str(e)}")
            
    def auto_fix_route(self, from_station: str, to_station: str, request_id: str):
        """Auto-fix route between stations."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("auto_fix_route"):
                self.emit_progress(0, "Analyzing current route...")
                
                if self.is_cancelled():
                    return
                    
                # Check cache for auto-fix results
                cache_key = f"autofix:{from_station.lower()}:{to_station.lower()}"
                cached_result = self.route_cache.get(cache_key)
                
                if cached_result is not None:
                    train_changes, success, message = cached_result
                    self.route_fixed.emit(train_changes, success, f"{message} (cached)", request_id)
                    return
                    
                self.emit_progress(25, "Finding optimal path...")
                
                # Find routes with different strategies
                routes = self.db_manager.find_route_between_stations(from_station, to_station, max_changes=3)
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(60, "Validating route geography...")
                
                if routes:
                    # Use the best route (first one is typically best)
                    best_route = routes[0]
                    
                    self.emit_progress(80, "Identifying train changes...")
                    
                    # Identify actual train change points
                    train_changes = self.db_manager.identify_train_changes(best_route)
                    
                    self.emit_progress(100, "Route optimization completed")
                    
                    success = True
                    message = f"Route optimized with {len(train_changes)} train changes"
                    
                    # Cache the result
                    self.route_cache.put(cache_key, (train_changes, success, message), ttl=1800)
                    
                    self.route_fixed.emit(train_changes, success, message, request_id)
                else:
                    success = False
                    message = "No valid route found"
                    
                    # Cache negative result for shorter time
                    self.route_cache.put(cache_key, ([], success, message), ttl=300)
                    
                    self.route_fixed.emit([], success, message, request_id)
                    
        except Exception as e:
            self.logger.error(f"Auto-fix error: {e}")
            self.error.emit(f"Auto-fix failed: {str(e)}")
            
    def suggest_via_stations(self, from_station: str, to_station: str, request_id: str):
        """Suggest via stations for route."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("suggest_via_stations"):
                # Check cache first
                cache_key = CacheKey.via_stations_key(from_station, to_station)
                cached_suggestions = self.via_cache.get(cache_key)
                
                if cached_suggestions is not None:
                    self.via_stations_suggested.emit(cached_suggestions, request_id)
                    return
                    
                self.emit_progress(0, "Analyzing route options...")
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(50, "Finding interchange stations...")
                
                # Get via station suggestions
                via_stations = self.db_manager.suggest_via_stations(from_station, to_station)
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(100, "Via station suggestions completed")
                
                # Cache the result
                self.via_cache.put(cache_key, via_stations, ttl=3600)  # 1 hour
                
                self.via_stations_suggested.emit(via_stations, request_id)
                
        except Exception as e:
            self.logger.error(f"Via station suggestion error: {e}")
            self.error.emit(f"Via station suggestion failed: {str(e)}")
            
    def validate_route(self, route: List[str], from_station: str, to_station: str, request_id: str):
        """Validate route geography and connectivity."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("route_validation"):
                # Create cache key from route hash
                route_str = "->".join(route)
                route_hash = hashlib.md5(route_str.encode()).hexdigest()
                cache_key = CacheKey.validation_key(route_hash)
                
                # Check cache first
                cached_result = self.validation_cache.get(cache_key)
                if cached_result is not None:
                    is_valid, message = cached_result
                    self.route_validated.emit(is_valid, f"{message} (cached)", request_id)
                    return
                    
                self.emit_progress(25, "Validating route geography...")
                
                if self.is_cancelled():
                    return
                    
                # Perform validation
                is_valid = self.db_manager.validate_route_geography(route, from_station, to_station)
                
                self.emit_progress(75, "Checking connectivity...")
                
                if is_valid:
                    message = "Route is geographically valid and well-connected"
                else:
                    message = "Route has geographical inefficiencies or connectivity issues"
                    
                self.emit_progress(100, "Validation completed")
                
                # Cache the result
                self.validation_cache.put(cache_key, (is_valid, message), ttl=1800)
                
                self.route_validated.emit(is_valid, message, request_id)
                
        except Exception as e:
            self.logger.error(f"Route validation error: {e}")
            self.error.emit(f"Route validation failed: {str(e)}")
            
    def find_fastest_route_async(self, from_station: str, to_station: str, request_id: str):
        """Find fastest route between stations (optimized version)."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("fastest_route"):
                self.emit_progress(0, "Initializing fastest route search...")
                
                # Check cache for fastest route
                cache_key = f"fastest:{from_station.lower()}:{to_station.lower()}"
                cached_result = self.route_cache.get(cache_key)
                
                if cached_result is not None:
                    self.route_fixed.emit(cached_result[0], True, f"{cached_result[2]} (cached)", request_id)
                    return
                    
                self.emit_progress(20, "Analyzing route options...")
                
                if self.is_cancelled():
                    return
                    
                # Try different numbers of changes to find optimal route
                best_route = None
                best_changes = float('inf')
                
                for max_changes in range(0, 6):  # Try 0-5 changes
                    if self.is_cancelled():
                        return
                        
                    self.emit_progress(20 + (max_changes * 10), f"Trying routes with {max_changes} changes...")
                    
                    routes = self.db_manager.find_route_between_stations(from_station, to_station, max_changes=max_changes)
                    
                    if routes:
                        shortest_route = min(routes, key=len)
                        route_changes = len(shortest_route) - 2  # Exclude start/end
                        
                        if route_changes < best_changes:
                            best_route = shortest_route
                            best_changes = route_changes
                            break  # Found a good route, use it
                            
                if self.is_cancelled():
                    return
                    
                self.emit_progress(80, "Identifying train changes...")
                
                if best_route:
                    # Identify actual train change points
                    train_change_stations = self.db_manager.identify_train_changes(best_route)
                    
                    self.emit_progress(100, "Fastest route found")
                    
                    success = True
                    message = f"Optimal route found with {len(train_change_stations)} train changes"
                    
                    # Cache the result
                    self.route_cache.put(cache_key, (train_change_stations, success, message), ttl=1800)
                    
                    self.route_fixed.emit(train_change_stations, success, message, request_id)
                else:
                    success = False
                    message = "No optimal route found"
                    
                    # Cache negative result
                    self.route_cache.put(cache_key, ([], success, message), ttl=300)
                    
                    self.route_fixed.emit([], success, message, request_id)
                    
        except Exception as e:
            self.logger.error(f"Fastest route error: {e}")
            self.error.emit(f"Fastest route calculation failed: {str(e)}")
            
    def get_cache_stats(self) -> Dict[str, Dict]:
        """Get comprehensive cache statistics."""
        return {
            'route_cache': self.route_cache.get_stats(),
            'via_cache': self.via_cache.get_stats(),
            'validation_cache': self.validation_cache.get_stats(),
            'performance': {
                'total_calculations': self._route_calculations,
                'cache_hits': self._cache_hits,
                'cache_hit_rate': self._cache_hits / max(self._route_calculations, 1)
            }
        }
        
    def cleanup_caches(self):
        """Clean up expired cache entries."""
        try:
            route_cleaned = self.route_cache.cleanup_expired()
            via_cleaned = self.via_cache.cleanup_expired()
            validation_cleaned = self.validation_cache.cleanup_expired()
            
            total_cleaned = route_cleaned + via_cleaned + validation_cleaned
            if total_cleaned > 0:
                self.logger.info(f"Cleaned up {total_cleaned} expired route cache entries")
                
        except Exception as e:
            self.logger.error(f"Route cache cleanup error: {e}")