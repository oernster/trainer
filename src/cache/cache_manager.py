"""
Cache manager for coordinating multi-level caching.

This module provides a unified interface for managing memory and disk caches
with intelligent cache warming and eviction strategies.
"""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
import logging
import time

from .memory_cache import MemoryCache


class DiskCache:
    """Simple disk-based cache for persistent storage."""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        """
        Initialize disk cache.
        
        Args:
            cache_dir: Directory for cache files
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.logger = logging.getLogger(__name__)
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from disk cache."""
        try:
            cache_file = self.cache_dir / f"{self._hash_key(key)}.cache"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    
                # Check expiry
                if time.time() < data['expiry']:
                    return data['value']
                else:
                    # Remove expired file
                    cache_file.unlink()
                    
        except Exception as e:
            self.logger.warning(f"Disk cache read error for key {key}: {e}")
            
        return None
        
    def put(self, key: str, value: Any, ttl: int = 3600):
        """Put item in disk cache."""
        try:
            # Check cache size and cleanup if needed
            self._cleanup_if_needed()
            
            cache_file = self.cache_dir / f"{self._hash_key(key)}.cache"
            data = {
                'value': value,
                'expiry': time.time() + ttl,
                'created': time.time()
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
                
        except Exception as e:
            self.logger.warning(f"Disk cache write error for key {key}: {e}")
            
    def delete(self, key: str) -> bool:
        """Delete item from disk cache."""
        try:
            cache_file = self.cache_dir / f"{self._hash_key(key)}.cache"
            if cache_file.exists():
                cache_file.unlink()
                return True
        except Exception as e:
            self.logger.warning(f"Disk cache delete error for key {key}: {e}")
            
        return False
        
    def clear(self):
        """Clear all items from disk cache."""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            self.logger.error(f"Disk cache clear error: {e}")
            
    def _hash_key(self, key: str) -> str:
        """Generate hash for cache key."""
        return hashlib.md5(key.encode()).hexdigest()
        
    def _cleanup_if_needed(self):
        """Cleanup cache if it exceeds size limit."""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
            
            if total_size > self.max_size_bytes:
                # Remove oldest files first
                cache_files = list(self.cache_dir.glob("*.cache"))
                cache_files.sort(key=lambda f: f.stat().st_mtime)
                
                # Remove files until under limit
                for cache_file in cache_files:
                    cache_file.unlink()
                    total_size -= cache_file.stat().st_size
                    if total_size <= self.max_size_bytes * 0.8:  # Leave some headroom
                        break
                        
        except Exception as e:
            self.logger.error(f"Disk cache cleanup error: {e}")


class CacheManager:
    """Multi-level cache manager with intelligent strategies."""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for disk cache
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache levels
        self.l1_cache = MemoryCache(max_size=1000, default_ttl=1800)  # 30 minutes
        self.l2_cache = MemoryCache(max_size=5000, default_ttl=3600)  # 1 hour
        self.l3_cache = DiskCache(cache_dir, max_size_mb=100)
        
        # Cache statistics
        self._stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        
        # Cache warming data
        self._warm_cache_data()
        
    def get(self, key: str, operation_type: str = "default") -> Optional[Any]:
        """
        Get item from multi-level cache.
        
        Args:
            key: Cache key
            operation_type: Type of operation for cache strategy
            
        Returns:
            Cached value or None if not found
        """
        self._stats['total_requests'] += 1
        
        # Try L1 cache first (fastest)
        value = self.l1_cache.get(key)
        if value is not None:
            self._stats['l1_hits'] += 1
            return value
            
        # Try L2 cache
        value = self.l2_cache.get(key)
        if value is not None:
            self._stats['l2_hits'] += 1
            # Promote to L1 for frequently accessed items
            self.l1_cache.put(key, value, ttl=1800)
            return value
            
        # Try L3 cache (disk)
        value = self.l3_cache.get(key)
        if value is not None:
            self._stats['l3_hits'] += 1
            # Promote to L2 and L1
            self.l2_cache.put(key, value, ttl=3600)
            self.l1_cache.put(key, value, ttl=1800)
            return value
            
        # Cache miss
        self._stats['misses'] += 1
        return None
        
    def put(self, key: str, value: Any, operation_type: str = "default", ttl: Optional[int] = None):
        """
        Put item in appropriate cache levels.
        
        Args:
            key: Cache key
            value: Value to cache
            operation_type: Type of operation for cache strategy
            ttl: Time-to-live override
        """
        # Determine cache strategy based on operation type
        strategy = self._get_cache_strategy(operation_type)
        
        # Store in appropriate cache levels
        if strategy['l1']:
            l1_ttl = ttl or strategy['l1_ttl']
            self.l1_cache.put(key, value, ttl=l1_ttl)
            
        if strategy['l2']:
            l2_ttl = ttl or strategy['l2_ttl']
            self.l2_cache.put(key, value, ttl=l2_ttl)
            
        if strategy['l3']:
            l3_ttl = ttl or strategy['l3_ttl']
            self.l3_cache.put(key, value, ttl=l3_ttl)
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set item in cache (alias for put).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        self.put(key, value, ttl=ttl)
        
    def delete(self, key: str):
        """Delete item from all cache levels."""
        self.l1_cache.delete(key)
        self.l2_cache.delete(key)
        self.l3_cache.delete(key)
        
    def clear_all(self):
        """Clear all cache levels."""
        self.l1_cache.clear()
        self.l2_cache.clear()
        self.l3_cache.clear()
        
        # Reset statistics
        self._stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_hits = self._stats['l1_hits'] + self._stats['l2_hits'] + self._stats['l3_hits']
        total_requests = self._stats['total_requests']
        
        return {
            'hit_rate': total_hits / max(total_requests, 1),
            'l1_hit_rate': self._stats['l1_hits'] / max(total_requests, 1),
            'l2_hit_rate': self._stats['l2_hits'] / max(total_requests, 1),
            'l3_hit_rate': self._stats['l3_hits'] / max(total_requests, 1),
            'miss_rate': self._stats['misses'] / max(total_requests, 1),
            'total_requests': total_requests,
            'cache_sizes': {
                'l1': self.l1_cache.get_stats()['size'],
                'l2': self.l2_cache.get_stats()['size']
            },
            'cache_utilization': {
                'l1': self.l1_cache.get_stats()['utilization'],
                'l2': self.l2_cache.get_stats()['utilization']
            }
        }
        
    def cleanup_expired(self):
        """Clean up expired entries from all cache levels."""
        l1_cleaned = self.l1_cache.cleanup_expired()
        l2_cleaned = self.l2_cache.cleanup_expired()
        
        total_cleaned = l1_cleaned + l2_cleaned
        if total_cleaned > 0:
            self.logger.debug(f"Cleaned up {total_cleaned} expired cache entries")
            
        return total_cleaned
        
    def warm_cache(self, warm_data: Dict[str, Any]):
        """Warm cache with frequently accessed data."""
        try:
            for key, data in warm_data.items():
                value = data['value']
                operation_type = data.get('type', 'default')
                ttl = data.get('ttl')
                
                self.put(key, value, operation_type, ttl)
                
            self.logger.info(f"Cache warmed with {len(warm_data)} items")
            
        except Exception as e:
            self.logger.error(f"Cache warming error: {e}")
            
    def _get_cache_strategy(self, operation_type: str) -> Dict[str, Any]:
        """Get caching strategy based on operation type."""
        strategies = {
            'search': {
                'l1': True, 'l1_ttl': 1800,   # 30 minutes
                'l2': True, 'l2_ttl': 3600,   # 1 hour
                'l3': True, 'l3_ttl': 7200    # 2 hours
            },
            'route': {
                'l1': True, 'l1_ttl': 1800,   # 30 minutes
                'l2': True, 'l2_ttl': 3600,   # 1 hour
                'l3': True, 'l3_ttl': 86400   # 24 hours
            },
            'station_data': {
                'l1': True, 'l1_ttl': 3600,   # 1 hour
                'l2': True, 'l2_ttl': 7200,   # 2 hours
                'l3': True, 'l3_ttl': 86400   # 24 hours
            },
            'validation': {
                'l1': True, 'l1_ttl': 1800,   # 30 minutes
                'l2': True, 'l2_ttl': 3600,   # 1 hour
                'l3': False, 'l3_ttl': 0      # Don't persist validations
            },
            'default': {
                'l1': True, 'l1_ttl': 1800,   # 30 minutes
                'l2': True, 'l2_ttl': 3600,   # 1 hour
                'l3': False, 'l3_ttl': 0      # Don't persist by default
            }
        }
        
        return strategies.get(operation_type, strategies['default'])
        
    def _warm_cache_data(self):
        """Pre-populate cache with essential data."""
        # This would be called during initialization to warm up
        # frequently accessed data like common station searches
        pass
        
    def get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate consistent cache key for operations."""
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        key_parts = [operation] + [f"{k}:{v}" for k, v in sorted_kwargs]
        return ":".join(str(part).lower() for part in key_parts)
        
    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching a pattern."""
        try:
            # Invalidate from memory caches
            l1_deleted = self.l1_cache.delete_by_prefix(pattern)
            l2_deleted = self.l2_cache.delete_by_prefix(pattern)
            
            total_deleted = l1_deleted + l2_deleted
            if total_deleted > 0:
                self.logger.debug(f"Invalidated {total_deleted} cache entries matching pattern: {pattern}")
                
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0