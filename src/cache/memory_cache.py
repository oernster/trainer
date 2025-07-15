"""
In-memory LRU cache implementation.

This module provides a high-performance in-memory cache with LRU eviction
for frequently accessed data like search results and route calculations.
"""

from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
import time
import threading
import logging


class MemoryCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of items to store
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self.logger = logging.getLogger(__name__)
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
                
            value, expiry_time = self._cache[key]
            
            # Check if expired
            if time.time() > expiry_time:
                del self._cache[key]
                self._misses += 1
                return None
                
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value
            
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Put item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
                
            expiry_time = time.time() + ttl
            
            # Update existing or add new
            self._cache[key] = (value, expiry_time)
            self._cache.move_to_end(key)
            
            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self.logger.debug(f"Evicted cache key: {oldest_key}")
                
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set item in cache (alias for put).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        self.put(key, value, ttl)
        
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
            
    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            
    def cleanup_expired(self) -> int:
        """
        Remove expired items from cache.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, (_, expiry_time) in self._cache.items():
                if current_time > expiry_time:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                del self._cache[key]
                
            if expired_keys:
                self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            return len(expired_keys)
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'utilization': len(self._cache) / self.max_size
            }
            
    def get_keys_by_prefix(self, prefix: str) -> list[str]:
        """
        Get all cache keys that start with the given prefix.
        
        Args:
            prefix: Key prefix to search for
            
        Returns:
            List of matching keys
        """
        with self._lock:
            return [key for key in self._cache.keys() if key.startswith(prefix)]
            
    def delete_by_prefix(self, prefix: str) -> int:
        """
        Delete all cache entries with keys starting with the given prefix.
        
        Args:
            prefix: Key prefix to delete
            
        Returns:
            Number of items deleted
        """
        with self._lock:
            keys_to_delete = self.get_keys_by_prefix(prefix)
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)


class CacheKey:
    """Helper class for generating consistent cache keys."""
    
    @staticmethod
    def search_key(query: str, limit: int) -> str:
        """Generate cache key for search operations."""
        return f"search:{query.lower()}:{limit}"
        
    @staticmethod
    def route_key(from_station: str, to_station: str, max_changes: int) -> str:
        """Generate cache key for route calculations."""
        return f"route:{from_station.lower()}:{to_station.lower()}:{max_changes}"
        
    @staticmethod
    def via_stations_key(from_station: str, to_station: str) -> str:
        """Generate cache key for via station suggestions."""
        return f"via:{from_station.lower()}:{to_station.lower()}"
        
    @staticmethod
    def validation_key(route_hash: str) -> str:
        """Generate cache key for route validation results."""
        return f"validation:{route_hash}"