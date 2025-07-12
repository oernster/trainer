"""
Disk-based cache implementation for persistent storage.

This module provides a disk-based cache for storing computed results
that should persist across application restarts.
"""

import json
import pickle
import hashlib
import time
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
import logging
import threading


class DiskCache:
    """Thread-safe disk-based cache with size management."""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        """
        Initialize disk cache.
        
        Args:
            cache_dir: Directory for cache files
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Cache metadata file
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from disk cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file(key)
                if not cache_file.exists():
                    return None
                    
                # Check metadata for expiry
                if key in self.metadata:
                    if time.time() > self.metadata[key]['expiry']:
                        self._remove_cache_file(key)
                        return None
                        
                # Load data
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    
                # Update access time in metadata
                if key in self.metadata:
                    self.metadata[key]['last_access'] = time.time()
                    self._save_metadata()
                    
                return data
                
            except Exception as e:
                self.logger.warning(f"Disk cache read error for key {key}: {e}")
                # Clean up corrupted file
                self._remove_cache_file(key)
                return None
                
    def put(self, key: str, value: Any, ttl: int = 3600):
        """
        Put item in disk cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        with self._lock:
            try:
                # Check cache size and cleanup if needed
                self._cleanup_if_needed()
                
                cache_file = self._get_cache_file(key)
                
                # Save data
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
                    
                # Update metadata
                file_size = cache_file.stat().st_size
                self.metadata[key] = {
                    'expiry': time.time() + ttl,
                    'created': time.time(),
                    'last_access': time.time(),
                    'size': file_size,
                    'filename': cache_file.name
                }
                
                self._save_metadata()
                
            except Exception as e:
                self.logger.warning(f"Disk cache write error for key {key}: {e}")
                
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set item in disk cache (alias for put).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        self.put(key, value, ttl)
        
    def delete(self, key: str) -> bool:
        """
        Delete item from disk cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            return self._remove_cache_file(key)
            
    def clear(self):
        """Clear all items from disk cache."""
        with self._lock:
            try:
                # Remove all cache files
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                    
                # Clear metadata
                self.metadata.clear()
                self._save_metadata()
                
                self.logger.info("Disk cache cleared")
                
            except Exception as e:
                self.logger.error(f"Disk cache clear error: {e}")
                
    def cleanup_expired(self) -> int:
        """
        Remove expired items from cache.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, meta in self.metadata.items():
                if current_time > meta['expiry']:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                self._remove_cache_file(key)
                
            if expired_keys:
                self.logger.debug(f"Cleaned up {len(expired_keys)} expired disk cache entries")
                
            return len(expired_keys)
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_size = sum(meta['size'] for meta in self.metadata.values())
            
            return {
                'size': len(self.metadata),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'utilization': total_size / self.max_size_bytes if self.max_size_bytes > 0 else 0,
                'cache_dir': str(self.cache_dir)
            }
            
    def get_keys_by_prefix(self, prefix: str) -> List[str]:
        """
        Get all cache keys that start with the given prefix.
        
        Args:
            prefix: Key prefix to search for
            
        Returns:
            List of matching keys
        """
        with self._lock:
            return [key for key in self.metadata.keys() if key.startswith(prefix)]
            
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
                self._remove_cache_file(key)
            return len(keys_to_delete)
            
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a key."""
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed_key}.cache"
        
    def _remove_cache_file(self, key: str) -> bool:
        """Remove cache file and metadata for a key."""
        try:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
                
            if key in self.metadata:
                del self.metadata[key]
                self._save_metadata()
                
            return True
            
        except Exception as e:
            self.logger.warning(f"Error removing cache file for key {key}: {e}")
            return False
            
    def _cleanup_if_needed(self):
        """Cleanup cache if it exceeds size limit."""
        try:
            total_size = sum(meta['size'] for meta in self.metadata.values())
            
            if total_size > self.max_size_bytes:
                # Sort by last access time (LRU)
                sorted_items = sorted(
                    self.metadata.items(),
                    key=lambda x: x[1]['last_access']
                )
                
                # Remove oldest files until under limit
                for key, meta in sorted_items:
                    self._remove_cache_file(key)
                    total_size -= meta['size']
                    
                    # Stop when we're under 80% of limit (leave headroom)
                    if total_size <= self.max_size_bytes * 0.8:
                        break
                        
                self.logger.info(f"Disk cache cleanup completed, size reduced to {total_size / (1024*1024):.1f}MB")
                
        except Exception as e:
            self.logger.error(f"Disk cache cleanup error: {e}")
            
    def _load_metadata(self) -> Dict[str, Dict]:
        """Load cache metadata from disk."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    
                # Validate metadata against actual files
                validated_metadata = {}
                for key, meta in metadata.items():
                    cache_file = self._get_cache_file(key)
                    if cache_file.exists():
                        # Update size if file exists
                        meta['size'] = cache_file.stat().st_size
                        validated_metadata[key] = meta
                        
                return validated_metadata
                
        except Exception as e:
            self.logger.warning(f"Error loading cache metadata: {e}")
            
        return {}
        
    def _save_metadata(self):
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving cache metadata: {e}")
            
    def optimize(self):
        """Optimize cache by removing expired items and defragmenting."""
        with self._lock:
            try:
                # Remove expired items
                expired_count = self.cleanup_expired()
                
                # Validate all cache files
                invalid_keys = []
                for key in list(self.metadata.keys()):
                    cache_file = self._get_cache_file(key)
                    if not cache_file.exists():
                        invalid_keys.append(key)
                        
                # Remove invalid entries
                for key in invalid_keys:
                    del self.metadata[key]
                    
                if invalid_keys:
                    self._save_metadata()
                    
                total_cleaned = expired_count + len(invalid_keys)
                if total_cleaned > 0:
                    self.logger.info(f"Cache optimization completed: removed {total_cleaned} invalid entries")
                    
                return total_cleaned
                
            except Exception as e:
                self.logger.error(f"Cache optimization error: {e}")
                return 0


class PersistentCache:
    """High-level persistent cache with automatic management."""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        """
        Initialize persistent cache.
        
        Args:
            cache_dir: Directory for cache files
            max_size_mb: Maximum cache size in megabytes
        """
        self.disk_cache = DiskCache(cache_dir, max_size_mb)
        self.logger = logging.getLogger(__name__)
        
    def cache_route_calculation(self, from_station: str, to_station: str, 
                              max_changes: int, routes: List[List[str]]):
        """Cache route calculation results."""
        key = f"route:{from_station.lower()}:{to_station.lower()}:{max_changes}"
        self.disk_cache.put(key, routes, ttl=86400)  # 24 hours
        
    def get_cached_route(self, from_station: str, to_station: str, 
                        max_changes: int) -> Optional[List[List[str]]]:
        """Get cached route calculation results."""
        key = f"route:{from_station.lower()}:{to_station.lower()}:{max_changes}"
        return self.disk_cache.get(key)
        
    def cache_station_search(self, query: str, limit: int, results: List[str]):
        """Cache station search results."""
        key = f"search:{query.lower()}:{limit}"
        self.disk_cache.put(key, results, ttl=7200)  # 2 hours
        
    def get_cached_search(self, query: str, limit: int) -> Optional[List[str]]:
        """Get cached station search results."""
        key = f"search:{query.lower()}:{limit}"
        return self.disk_cache.get(key)
        
    def cache_via_stations(self, from_station: str, to_station: str, via_stations: List[str]):
        """Cache via station suggestions."""
        key = f"via:{from_station.lower()}:{to_station.lower()}"
        self.disk_cache.put(key, via_stations, ttl=86400)  # 24 hours
        
    def get_cached_via_stations(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Get cached via station suggestions."""
        key = f"via:{from_station.lower()}:{to_station.lower()}"
        return self.disk_cache.get(key)
        
    def invalidate_route_cache(self, from_station: Optional[str] = None, to_station: Optional[str] = None):
        """Invalidate route cache entries."""
        if from_station and to_station:
            # Invalidate specific route
            prefix = f"route:{from_station.lower()}:{to_station.lower()}"
        elif from_station:
            # Invalidate all routes from station
            prefix = f"route:{from_station.lower()}"
        else:
            # Invalidate all routes
            prefix = "route:"
            
        deleted = self.disk_cache.delete_by_prefix(prefix)
        if deleted > 0:
            self.logger.info(f"Invalidated {deleted} route cache entries")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.disk_cache.get_stats()
        
    def cleanup(self):
        """Perform cache cleanup and optimization."""
        return self.disk_cache.optimize()