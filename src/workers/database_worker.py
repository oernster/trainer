"""
Database worker for asynchronous station database operations.

This module provides a worker thread that handles station searches, database loading,
and caching operations without blocking the UI thread.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import hashlib

from PySide6.QtCore import Signal
from .base_worker import BaseWorker
from ..cache.memory_cache import MemoryCache, CacheKey


@dataclass
class SearchRequest:
    """Search request data structure."""
    query: str
    limit: int = 10
    request_id: str = ""
    timestamp: float = 0.0


@dataclass
class SearchResult:
    """Search result data structure."""
    stations: List[str]
    request_id: str
    computation_time: float
    cache_hit: bool
    total_matches: int = 0


class DatabaseWorker(BaseWorker):
    """Worker thread for database operations."""
    
    # Database-specific signals
    search_completed = Signal(SearchResult)
    database_loaded = Signal(bool, str)  # success, message
    cache_updated = Signal(str, int)     # cache_type, item_count
    stations_loaded = Signal(list)       # all station names
    
    def __init__(self, station_db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = station_db_manager
        
        # Initialize caches
        self.search_cache = MemoryCache(max_size=1000, default_ttl=1800)  # 30 minutes
        self.station_cache = MemoryCache(max_size=5000, default_ttl=3600)  # 1 hour
        
        # Connect slot methods
        self.search_requested.connect(self.perform_search)
        self.load_database_requested.connect(self.load_database)
        self.warm_cache_requested.connect(self.warm_cache)
        self.get_all_stations_requested.connect(self.get_all_stations)
        
        # Performance tracking
        self._search_count = 0
        self._cache_hits = 0
        
    # Request signals (emitted by UI thread)
    search_requested = Signal(SearchRequest)
    load_database_requested = Signal()
    warm_cache_requested = Signal()
    get_all_stations_requested = Signal(str)  # request_id
    
    def on_thread_started(self):
        """Initialize worker thread."""
        self.logger.info("Database worker thread started")
        self.started.emit()
        
        # Start database loading immediately
        self.load_database_requested.emit()
        
    def on_thread_finished(self):
        """Cleanup worker thread."""
        self.logger.info("Database worker thread finished")
        
        # Log performance stats
        stats = self.get_performance_stats()
        if stats:
            self.logger.info(f"Database worker performance: {stats}")
            
        self.finished.emit()
        
    def perform_search(self, request: SearchRequest):
        """Perform station search operation."""
        if self.is_cancelled():
            return
            
        self.reset_cancellation()
        start_time = time.time()
        
        try:
            with self.measure_operation("station_search"):
                # Check cache first
                cache_key = CacheKey.search_key(request.query, request.limit)
                cached_result = self.search_cache.get(cache_key)
                
                if cached_result is not None:
                    self._cache_hits += 1
                    result = SearchResult(
                        stations=cached_result,
                        request_id=request.request_id,
                        computation_time=time.time() - start_time,
                        cache_hit=True,
                        total_matches=len(cached_result)
                    )
                    self.search_completed.emit(result)
                    return
                    
                # Check for cancellation
                if self.is_cancelled():
                    return
                    
                self.emit_progress(25, "Searching stations...")
                
                # Perform actual search
                stations = self.db_manager.search_stations(request.query, request.limit)
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(75, "Processing results...")
                
                # Cache the result
                self.search_cache.put(cache_key, stations, ttl=1800)  # 30 minutes
                
                self.emit_progress(100, "Search completed")
                
                # Update counters
                self._search_count += 1
                
                # Emit result
                result = SearchResult(
                    stations=stations,
                    request_id=request.request_id,
                    computation_time=time.time() - start_time,
                    cache_hit=False,
                    total_matches=len(stations)
                )
                self.search_completed.emit(result)
                
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            self.error.emit(f"Search failed: {str(e)}")
            
    def load_database(self):
        """Load station database in background."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("database_load"):
                self.emit_progress(0, "Loading railway lines index...")
                
                if self.is_cancelled():
                    return
                    
                # Load database
                success = self.db_manager.load_database()
                
                if self.is_cancelled():
                    return
                    
                if success:
                    self.emit_progress(50, "Building search indices...")
                    
                    # Pre-populate station cache
                    self._populate_station_cache()
                    
                    if self.is_cancelled():
                        return
                        
                    self.emit_progress(100, "Database loaded successfully")
                    self.database_loaded.emit(True, "Database loaded successfully")
                    
                    # Start cache warming
                    self.warm_cache_requested.emit()
                else:
                    self.database_loaded.emit(False, "Failed to load database")
                    
        except Exception as e:
            self.logger.error(f"Database loading error: {e}")
            self.error.emit(f"Database loading failed: {str(e)}")
            
    def warm_cache(self):
        """Pre-populate cache with common searches."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("cache_warming"):
                common_searches = [
                    "London", "Manchester", "Birmingham", "Bristol", "Leeds",
                    "Liverpool", "Newcastle", "Sheffield", "Nottingham", "Cardiff",
                    "Edinburgh", "Glasgow", "Aberdeen", "Dundee", "Stirling",
                    "Oxford", "Cambridge", "Bath", "York", "Chester"
                ]
                
                total_searches = len(common_searches)
                for i, search_term in enumerate(common_searches):
                    if self.is_cancelled():
                        return
                        
                    self.emit_progress(
                        int((i / total_searches) * 100),
                        f"Warming cache: {search_term}"
                    )
                    
                    # Perform search to populate cache
                    try:
                        stations = self.db_manager.search_stations(search_term, 20)
                        cache_key = CacheKey.search_key(search_term, 20)
                        self.search_cache.put(cache_key, stations, ttl=3600)  # 1 hour for common searches
                    except Exception as search_error:
                        self.logger.warning(f"Failed to warm cache for '{search_term}': {search_error}")
                        
                self.emit_progress(100, "Cache warming completed")
                cache_stats = self.search_cache.get_stats()
                self.cache_updated.emit("search", cache_stats['size'])
                
        except Exception as e:
            self.logger.error(f"Cache warming error: {e}")
            self.error.emit(f"Cache warming failed: {str(e)}")
            
    def get_all_stations(self, request_id: str):
        """Get all station names with context."""
        if self.is_cancelled():
            return
            
        try:
            with self.measure_operation("get_all_stations"):
                # Check cache first
                cache_key = "all_stations_with_context"
                cached_stations = self.station_cache.get(cache_key)
                
                if cached_stations is not None:
                    self.stations_loaded.emit(cached_stations)
                    return
                    
                self.emit_progress(25, "Loading all stations...")
                
                # Get all stations with context
                stations = self.db_manager.get_all_stations_with_context()
                
                if self.is_cancelled():
                    return
                    
                self.emit_progress(75, "Caching station list...")
                
                # Cache the result
                self.station_cache.put(cache_key, stations, ttl=7200)  # 2 hours
                
                self.emit_progress(100, "Station list loaded")
                self.stations_loaded.emit(stations)
                
        except Exception as e:
            self.logger.error(f"Get all stations error: {e}")
            self.error.emit(f"Failed to load station list: {str(e)}")
            
            
    def _populate_station_cache(self):
        """Pre-populate station cache with frequently accessed data."""
        try:
            # Cache all station names
            all_stations = self.db_manager.get_all_station_names()
            if all_stations:
                self.station_cache.put("all_station_names", all_stations, ttl=7200)
                
                    
        except Exception as e:
            self.logger.warning(f"Failed to populate station cache: {e}")
            
    def get_cache_stats(self) -> Dict[str, Dict]:
        """Get comprehensive cache statistics."""
        return {
            'search_cache': self.search_cache.get_stats(),
            'station_cache': self.station_cache.get_stats(),
            'performance': {
                'total_searches': self._search_count,
                'cache_hits': self._cache_hits,
                'cache_hit_rate': self._cache_hits / max(self._search_count, 1)
            }
        }
        
    def cleanup_caches(self):
        """Clean up expired cache entries."""
        try:
            search_cleaned = self.search_cache.cleanup_expired()
            station_cleaned = self.station_cache.cleanup_expired()
            
            total_cleaned = search_cleaned + station_cleaned
            if total_cleaned > 0:
                self.logger.info(f"Cleaned up {total_cleaned} expired cache entries")
                
        except Exception as e:
            self.logger.error(f"Cache cleanup error: {e}")