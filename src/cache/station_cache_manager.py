"""
Station Cache Manager

Manages persistent caching of station data to improve performance across
application sessions. Provides file-based caching with validation and refresh.
"""

import json
import logging
import os
import time
import gzip
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class StationCacheManager:
    """
    Manager for persistent station data caching.
    
    Provides file-based caching with compression, validation, and automatic
    refresh capabilities to optimize station data loading performance.
    """
    
    def __init__(self, cache_directory: Optional[str] = None):
        """
        Initialize the station cache manager.
        
        Args:
            cache_directory: Directory for cache files, defaults to src/cache
        """
        self.logger = logging.getLogger(__name__)
        
        # Set cache directory
        if cache_directory is None:
            # Default to cache directory relative to this file
            self.cache_directory = Path(__file__).parent
        else:
            self.cache_directory = Path(cache_directory)
        
        # Ensure cache directory exists
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        
        # Cache file paths
        self.station_cache_file = self.cache_directory / "station_data.cache"
        self.metadata_file = self.cache_directory / "cache_metadata.json"
        
        # Cache settings
        self.cache_version = "1.0.0"
        self.max_cache_age_hours = 24  # Cache expires after 24 hours
        self.compression_enabled = True
        
        self.logger.info(f"StationCacheManager initialized with cache directory: {self.cache_directory}")
    
    def _get_data_source_hash(self, data_directory: Path) -> str:
        """
        Generate a hash of the data source files to detect changes.
        
        Args:
            data_directory: Path to the data directory
            
        Returns:
            Hash string representing the current state of data files
        """
        try:
            hash_md5 = hashlib.md5()
            
            # Hash the railway lines index file if it exists
            index_file = data_directory / "railway_lines_index_comprehensive.json"
            if index_file.exists():
                with open(index_file, 'rb') as f:
                    hash_md5.update(f.read())
            
            # Hash the underground stations file if it exists
            underground_file = data_directory / "uk_underground_stations.json"
            if underground_file.exists():
                with open(underground_file, 'rb') as f:
                    hash_md5.update(f.read())
            
            # Hash modification times of JSON files in lines directory
            lines_dir = data_directory / "lines"
            if lines_dir.exists():
                json_files = sorted(lines_dir.glob("*.json"))
                # Filter out backup files
                json_files = [f for f in json_files if not f.name.endswith('.backup')]
                
                for json_file in json_files:
                    # Include file name and modification time
                    hash_md5.update(json_file.name.encode())
                    hash_md5.update(str(json_file.stat().st_mtime).encode())
            
            return hash_md5.hexdigest()
            
        except Exception as e:
            self.logger.warning(f"Failed to generate data source hash: {e}")
            return "unknown"
    
    def _load_cache_metadata(self) -> Dict[str, Any]:
        """
        Load cache metadata from file.
        
        Returns:
            Dictionary containing cache metadata
        """
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load cache metadata: {e}")
        
        return {}
    
    def _save_cache_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Save cache metadata to file.
        
        Args:
            metadata: Metadata dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save cache metadata: {e}")
            return False
    
    def is_cache_valid(self, data_directory: Optional[Path] = None) -> bool:
        """
        Check if the current cache is valid and up-to-date.
        
        Args:
            data_directory: Path to data directory for validation
            
        Returns:
            True if cache is valid, False otherwise
        """
        try:
            # Check if cache files exist
            if not self.station_cache_file.exists():
                self.logger.debug("Cache file does not exist")
                return False
            
            # Load metadata
            metadata = self._load_cache_metadata()
            if not metadata:
                self.logger.debug("Cache metadata missing or invalid")
                return False
            
            # Check cache version
            if metadata.get('cache_version') != self.cache_version:
                self.logger.debug("Cache version mismatch")
                return False
            
            # Check cache age
            created_time = metadata.get('created_timestamp')
            if created_time:
                created_dt = datetime.fromisoformat(created_time)
                age = datetime.now() - created_dt
                if age > timedelta(hours=self.max_cache_age_hours):
                    self.logger.debug(f"Cache expired (age: {age})")
                    return False
            
            # Check data source hash if data directory provided
            if data_directory:
                current_hash = self._get_data_source_hash(data_directory)
                cached_hash = metadata.get('data_source_hash')
                if current_hash != cached_hash:
                    self.logger.debug("Data source has changed")
                    return False
            
            self.logger.debug("Cache is valid")
            return True
            
        except Exception as e:
            self.logger.warning(f"Cache validation failed: {e}")
            return False
    
    def load_cached_stations(self) -> Optional[List[str]]:
        """
        Load station data from cache.
        
        Returns:
            List of station names if successful, None otherwise
        """
        try:
            if not self.station_cache_file.exists():
                return None
            
            start_time = time.time()
            
            # Load data (with or without compression)
            if self.compression_enabled:
                with gzip.open(self.station_cache_file, 'rt', encoding='utf-8') as f:
                    cache_data = json.load(f)
            else:
                with open(self.station_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            
            # Extract station list
            stations = cache_data.get('stations', [])
            
            load_time = time.time() - start_time
            self.logger.info(f"Loaded {len(stations)} stations from cache in {load_time:.3f}s")
            
            return stations
            
        except Exception as e:
            self.logger.error(f"Failed to load cached stations: {e}")
            return None
    
    def save_stations_to_cache(self, stations: List[str], 
                              data_directory: Optional[Path] = None) -> bool:
        """
        Save station data to cache.
        
        Args:
            stations: List of station names to cache
            data_directory: Path to data directory for hash generation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            start_time = time.time()
            
            # Prepare cache data
            cache_data = {
                'stations': sorted(stations),
                'station_count': len(stations),
                'created_timestamp': datetime.now().isoformat(),
                'cache_version': self.cache_version
            }
            
            # Save station data (with or without compression)
            if self.compression_enabled:
                with gzip.open(self.station_cache_file, 'wt', encoding='utf-8') as f:
                    json.dump(cache_data, f, separators=(',', ':'))
            else:
                with open(self.station_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2)
            
            # Prepare and save metadata
            metadata = {
                'cache_version': self.cache_version,
                'created_timestamp': datetime.now().isoformat(),
                'station_count': len(stations),
                'compression_enabled': self.compression_enabled,
                'data_source_hash': self._get_data_source_hash(data_directory) if data_directory else None
            }
            
            self._save_cache_metadata(metadata)
            
            save_time = time.time() - start_time
            self.logger.info(f"Saved {len(stations)} stations to cache in {save_time:.3f}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save stations to cache: {e}")
            return False
    
    def clear_cache(self) -> bool:
        """
        Clear all cache files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            files_removed = 0
            
            if self.station_cache_file.exists():
                self.station_cache_file.unlink()
                files_removed += 1
            
            if self.metadata_file.exists():
                self.metadata_file.unlink()
                files_removed += 1
            
            self.logger.info(f"Cache cleared ({files_removed} files removed)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary containing cache information
        """
        info = {
            'cache_directory': str(self.cache_directory),
            'cache_file_exists': self.station_cache_file.exists(),
            'metadata_file_exists': self.metadata_file.exists(),
            'cache_version': self.cache_version,
            'compression_enabled': self.compression_enabled,
            'max_cache_age_hours': self.max_cache_age_hours
        }
        
        # Add file sizes if files exist
        try:
            if self.station_cache_file.exists():
                info['cache_file_size_bytes'] = self.station_cache_file.stat().st_size
            
            if self.metadata_file.exists():
                info['metadata_file_size_bytes'] = self.metadata_file.stat().st_size
        except Exception as e:
            self.logger.warning(f"Failed to get file sizes: {e}")
        
        # Add metadata if available
        metadata = self._load_cache_metadata()
        if metadata:
            info.update({
                'cached_station_count': metadata.get('station_count'),
                'cache_created': metadata.get('created_timestamp'),
                'data_source_hash': metadata.get('data_source_hash')
            })
        
        return info
    
    def optimize_cache(self) -> bool:
        """
        Optimize the cache by recompressing or reorganizing data.
        
        Returns:
            True if optimization was successful, False otherwise
        """
        try:
            # Load current data
            stations = self.load_cached_stations()
            if not stations:
                self.logger.warning("No cached data to optimize")
                return False
            
            # Get current metadata
            metadata = self._load_cache_metadata()
            data_directory = None
            
            # Re-save with current settings (this will recompress if needed)
            success = self.save_stations_to_cache(stations, data_directory)
            
            if success:
                self.logger.info("Cache optimization completed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Cache optimization failed: {e}")
            return False


# Global cache manager instance
_cache_manager: Optional[StationCacheManager] = None


def get_station_cache_manager(cache_directory: Optional[str] = None) -> StationCacheManager:
    """
    Get the global station cache manager instance.
    
    Args:
        cache_directory: Cache directory path (only used on first call)
        
    Returns:
        The singleton StationCacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = StationCacheManager(cache_directory)
    return _cache_manager