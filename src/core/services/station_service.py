"""
Station Service Implementation

Service implementation for station-related operations using names only.
"""

import logging
from typing import List, Optional, Set, Dict, Any
from difflib import SequenceMatcher
import re

from ..interfaces.i_station_service import IStationService
from ..interfaces.i_data_repository import IDataRepository
from ..models.station import Station


class StationService(IStationService):
    """Service implementation for station operations."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the station service.
        
        Args:
            data_repository: Data repository for accessing station data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        
        # Cache for frequently accessed data
        self._station_names_cache: Optional[Set[str]] = None
        self._stations_cache: Optional[List[Station]] = None
        
        self.logger.info("Initialized StationService")
    
    def _ensure_cache_loaded(self) -> None:
        """Ensure station data is cached for performance."""
        if self._station_names_cache is None:
            self._station_names_cache = self.data_repository.get_all_station_names()
        
        if self._stations_cache is None:
            self._stations_cache = self.data_repository.load_stations()
    
    def resolve_station_name(self, input_name: str, strict: bool = False) -> Optional[str]:
        """Resolve a station name from user input."""
        if not input_name or not input_name.strip():
            return None
        
        input_name = input_name.strip()
        self._ensure_cache_loaded()
        
        if not self._station_names_cache:
            return None
        
        # First try exact match (case insensitive)
        for station_name in self._station_names_cache:
            if station_name.lower() == input_name.lower():
                return station_name
        
        # If strict mode, only return exact matches
        if strict:
            return None
        
        # Try prefix match
        matches = []
        input_lower = input_name.lower()
        
        for station_name in self._station_names_cache:
            station_lower = station_name.lower()
            
            # Exact prefix match gets highest priority
            if station_lower.startswith(input_lower):
                matches.append((station_name, 100))
            # Word boundary prefix match gets high priority
            elif any(word.startswith(input_lower) for word in station_lower.split()):
                matches.append((station_name, 90))
            # Contains match gets medium priority
            elif input_lower in station_lower:
                matches.append((station_name, 70))
        
        # If no matches, try fuzzy matching
        if not matches:
            for station_name in self._station_names_cache:
                similarity = SequenceMatcher(None, input_lower, station_name.lower()).ratio()
                if similarity > 0.6:  # 60% similarity threshold
                    matches.append((station_name, int(similarity * 100)))
        
        # Return the best match
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return None
    
    def get_station_suggestions(self, partial: str, limit: int = 10) -> List[str]:
        """Get station name suggestions based on partial input."""
        if not partial or not partial.strip():
            return []
        
        partial = partial.strip()
        self._ensure_cache_loaded()
        
        if not self._station_names_cache:
            return []
        
        suggestions = []
        partial_lower = partial.lower()
        
        for station_name in self._station_names_cache:
            station_lower = station_name.lower()
            score = 0
            
            # Exact match gets highest score
            if station_lower == partial_lower:
                score = 1000
            # Starts with gets high score
            elif station_lower.startswith(partial_lower):
                score = 900
            # Word starts with gets good score
            elif any(word.startswith(partial_lower) for word in station_lower.split()):
                score = 800
            # Contains gets medium score
            elif partial_lower in station_lower:
                score = 600
            # Fuzzy match gets lower score
            else:
                similarity = SequenceMatcher(None, partial_lower, station_lower).ratio()
                if similarity > 0.5:
                    score = int(similarity * 500)
            
            if score > 0:
                suggestions.append((station_name, score))
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [suggestion[0] for suggestion in suggestions[:limit]]
    
    def validate_station_exists(self, name: str) -> bool:
        """Validate that a station exists."""
        if not name or not name.strip():
            return False
        
        return self.data_repository.validate_station_exists(name.strip())
    
    def validate_station_name(self, station_name: str) -> bool:
        """Validate that a station name exists in the system."""
        return self.validate_station_exists(station_name)
    
    def get_station_by_name(self, name: str) -> Optional[Station]:
        """Get station object by name."""
        if not self.validate_station_exists(name):
            return None
        
        return self.data_repository.get_station_by_name(name.strip())
    
    def get_station_details(self, station_name: str) -> Optional[Station]:
        """Get detailed information about a station."""
        return self.get_station_by_name(station_name)
    
    def get_all_stations(self) -> List[Station]:
        """Get all stations."""
        return self.data_repository.load_stations()
    
    def get_all_station_names(self) -> List[str]:
        """Get all station names."""
        stations = self.get_all_stations()
        return [station.name for station in stations]
    
    def get_all_station_names_with_underground(self) -> List[str]:
        """Get all station names including all UK underground stations for autocomplete."""
        # Get National Rail stations
        national_rail_stations = set(self.get_all_station_names())
        
        # Get all UK underground stations
        underground_stations = set()
        try:
            from .underground_routing_handler import UndergroundRoutingHandler
            underground_handler = UndergroundRoutingHandler(self.data_repository)
            
            # Load all underground systems and combine their stations
            systems = underground_handler.load_underground_systems()
            for system_key, system_data in systems.items():
                system_stations = set(system_data.get('stations', []))
                underground_stations.update(system_stations)
                
            self.logger.info(f"Loaded {len(underground_stations)} underground stations from {len(systems)} systems")
        except Exception as e:
            self.logger.warning(f"Could not load underground stations: {e}")
        
        # Combine both sets and return sorted list
        all_stations = national_rail_stations.union(underground_stations)
        return sorted(list(all_stations))
    
    def get_railway_lines_for_station(self, station_name: str) -> List[str]:
        """Get all railway lines that serve a station."""
        lines = self.data_repository.get_lines_serving_station(station_name)
        return [line.name for line in lines]
    
    def get_stations_with_context(self) -> List[Dict[str, Any]]:
        """Get all stations with additional context information."""
        stations = self.get_all_stations()
        return [station.to_dict() for station in stations]
    
    def find_stations_by_pattern(self, pattern: str) -> List[str]:
        """Find stations matching a regex pattern."""
        if not pattern:
            return []
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            self._ensure_cache_loaded()
            
            if not self._station_names_cache:
                return []
            
            matches = []
            for station_name in self._station_names_cache:
                if regex.search(station_name):
                    matches.append(station_name)
            
            return sorted(matches)
            
        except re.error as e:
            self.logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return []
    
    def get_stations_on_line(self, line_name: str) -> List[Station]:
        """Get all stations on a specific railway line."""
        return self.data_repository.get_stations_on_line(line_name)
    
    def find_common_lines(self, from_name: str, to_name: str) -> List[str]:
        """Find railway lines that serve both stations."""
        if not self.validate_station_name(from_name) or not self.validate_station_name(to_name):
            return []
        
        lines = self.data_repository.get_common_lines(from_name, to_name)
        return [line.name for line in lines]
    
    def get_interchange_stations(self) -> List[str]:
        """Get all interchange station names."""
        stations = self.data_repository.get_interchange_stations()
        return [station.name for station in stations]
    
    def get_major_stations(self) -> List[str]:
        """Get all major station names."""
        stations = self.data_repository.get_major_stations()
        return [station.name for station in stations]
    
    def get_london_stations(self) -> List[str]:
        """Get all London station names."""
        stations = self.data_repository.get_london_stations()
        return [station.name for station in stations]
    
    def get_terminus_stations(self) -> List[str]:
        """Get all terminus station names."""
        stations = self.data_repository.get_terminus_stations()
        return [station.name for station in stations]
    
    def search_stations(self, query: str, limit: int = 20) -> List[str]:
        """Search for stations matching a query."""
        if not query or not query.strip():
            return []
        
        # Get search results from repository
        stations = self.data_repository.search_stations_by_name(query.strip(), limit)
        return [station.name for station in stations]
    
    def get_station_statistics(self) -> Dict[str, Any]:
        """Get statistics about stations in the system."""
        stats = self.data_repository.get_network_statistics()
        
        return {
            "total_stations": stats.get("total_stations", 0),
            "interchange_stations": stats.get("interchange_stations", 0),
            "terminus_stations": stats.get("terminus_stations", 0),
            "major_stations": stats.get("major_stations", 0),
            "london_stations": stats.get("london_stations", 0),
            "data_version": stats.get("data_version", "unknown"),
            "last_updated": stats.get("last_loaded")
        }
    
    def normalize_station_name(self, station_name: str) -> str:
        """Normalize a station name to standard format."""
        if not station_name:
            return ""
        
        # Basic normalization
        normalized = station_name.strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Standardize common abbreviations
        replacements = {
            r'\bSt\b': 'Saint',
            r'\bSt\.': 'Saint',
            r'\bRd\b': 'Road',
            r'\bRd\.': 'Road',
            r'\bAve\b': 'Avenue',
            r'\bAve\.': 'Avenue',
            r'\bJct\b': 'Junction',
            r'\bJct\.': 'Junction',
            r'\bIntl\b': 'International',
            r'\bIntl\.': 'International',
            r'\bPkwy\b': 'Parkway',
            r'\bPkwy\.': 'Parkway'
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def get_similar_station_names(self, station_name: str, threshold: float = 0.7,
                                 limit: int = 5) -> List[str]:
        """Find stations with similar names."""
        if not station_name or not self.validate_station_name(station_name):
            return []
        
        self._ensure_cache_loaded()
        if not self._station_names_cache:
            return []
            
        station_lower = station_name.lower()
        similar_stations = []
        
        for other_station in self._station_names_cache:
            if other_station.lower() == station_lower:
                continue  # Skip the same station
            
            similarity = SequenceMatcher(None, station_lower, other_station.lower()).ratio()
            if similarity >= threshold:
                similar_stations.append((other_station, similarity))
        
        # Sort by similarity and return top results
        similar_stations.sort(key=lambda x: x[1], reverse=True)
        return [station[0] for station in similar_stations[:limit]]
    
    def clear_cache(self) -> None:
        """Clear internal caches."""
        self._station_names_cache = None
        self._stations_cache = None
        self.logger.info("Station service cache cleared")
    
    def refresh_data(self) -> bool:
        """Refresh station data from the repository."""
        try:
            success = self.data_repository.refresh_data()
            if success:
                self.clear_cache()
                self.logger.info("Station service data refreshed successfully")
            return success
        except Exception as e:
            self.logger.error(f"Failed to refresh station data: {e}")
            return False
    
    def get_station_name_variants(self, station_name: str) -> List[str]:
        """Get common variants of a station name."""
        if not station_name:
            return []
        
        variants = [station_name]
        
        # Add normalized version
        normalized = self.normalize_station_name(station_name)
        if normalized != station_name:
            variants.append(normalized)
        
        # Add common variations
        name_lower = station_name.lower()
        
        # London prefix variations
        if name_lower.startswith("london "):
            variants.append(station_name[7:])  # Remove "London " prefix
        elif not name_lower.startswith("london "):
            variants.append(f"London {station_name}")
        
        # Central/Centre variations
        if "central" in name_lower:
            variants.append(station_name.replace("Central", "Centre").replace("central", "centre"))
        if "centre" in name_lower:
            variants.append(station_name.replace("Centre", "Central").replace("centre", "central"))
        
        # Remove duplicates while preserving order
        unique_variants = []
        seen = set()
        for variant in variants:
            if variant not in seen:
                unique_variants.append(variant)
                seen.add(variant)
        
        return unique_variants