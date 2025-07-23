"""
Station Name Normalizer

Handles station name normalization for case-insensitive comparison and London station variants.
"""

import logging
from typing import List, Optional, Dict, Any

from ..interfaces.i_data_repository import IDataRepository


class StationNameNormalizer:
    """Handles station name normalization and variant matching."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the station name normalizer.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
    
    def normalize_station_name(self, station_name: str, network_graph: Optional[Dict] = None) -> str:
        """
        Normalize station name for case-insensitive comparison and handle London station variants.
        Returns the actual station name (with correct case) if found, or the original name if not found.
        
        Args:
            station_name: The station name to normalize
            network_graph: Optional network graph for priority matching
            
        Returns:
            The normalized station name
        """
        # Check if we can find the station in case-insensitive manner
        all_stations = self.data_repository.get_all_station_names()
        
        # Try direct match first (most efficient)
        if station_name in all_stations:
            return station_name
        
        # 1. Case-insensitive search
        for existing_station in all_stations:
            if existing_station.lower() == station_name.lower():
                self.logger.info(f"Station name normalized (case): '{station_name}' → '{existing_station}'")
                return existing_station
        
        # 2. Get network graph stations if available
        network_stations = []
        if network_graph:
            network_stations = list(network_graph.keys())
        
        # 3. Handle "London X" vs "X" variants (with network graph priority)
        normalized_input = station_name.lower()
        
        # Check if input starts with "London "
        if normalized_input.startswith("london "):
            # Remove "London " prefix
            base_name = normalized_input[7:]
            
            # Check if base name exists in network graph first
            for ns in network_stations:
                if ns.lower() == base_name:
                    self.logger.info(f"Station name normalized (removed London, network): '{station_name}' → '{ns}'")
                    return ns
            
            # If not in network, check all stations
            for existing_station in all_stations:
                if existing_station.lower() == base_name:
                    self.logger.info(f"Station name normalized (removed London): '{station_name}' → '{existing_station}'")
                    return existing_station
        # Input doesn't have "London " prefix
        else:
            # Check for "London X" in network graph first
            london_name = "london " + normalized_input
            for ns in network_stations:
                if ns.lower() == london_name:
                    self.logger.info(f"Station name normalized (added London, network): '{station_name}' → '{ns}'")
                    return ns
                    
            # Try special case for exact names in network graph first
            for ns in network_stations:
                # Check if the non-London version exists with exact case in network
                if ns.lower() == normalized_input:
                    self.logger.info(f"Station name normalized (network exact match): '{station_name}' → '{ns}'")
                    return ns
            
            # Also check for any version with "London " prefix in all stations
            for existing_station in all_stations:
                if existing_station.lower() == london_name:
                    self.logger.info(f"Station name normalized (added London): '{station_name}' → '{existing_station}'")
                    return existing_station
        
        # 4. Advanced normalization - smart handling for London stations
        if not normalized_input.startswith("london "):
            # Try to find any station in the network graph that contains this name with London prefix
            for ns in network_stations:
                ns_lower = ns.lower()
                if ns_lower.startswith("london ") and normalized_input in ns_lower.replace("london ", ""):
                    self.logger.info(f"Station name smart-normalized: '{station_name}' → '{ns}'")
                    return ns
                    
            # Special case for Liverpool Street - explicitly handle this common case
            if normalized_input == "liverpool street":
                for ns in network_stations:
                    if ns.lower() == "london liverpool street":
                        self.logger.info(f"Station name normalized (Liverpool Street special case): '{station_name}' → '{ns}'")
                        return ns
        
        # 5. Additional normalization for parenthetical suffixes
        # Remove common suffixes like "(Main)" for matching
        normalized_input = normalized_input.replace(" (main)", "")
        for existing_station in all_stations:
            normalized_existing = existing_station.lower().replace(" (main)", "")
            if normalized_existing == normalized_input:
                self.logger.info(f"Station name normalized (suffix): '{station_name}' → '{existing_station}'")
                return existing_station
                
        # If no match found, return the original
        self.logger.warning(f"Station name not found in normalization: '{station_name}'")
        return station_name
    
    def normalize_station_list(self, station_names: List[str], network_graph: Optional[Dict] = None) -> List[str]:
        """
        Normalize a list of station names.
        
        Args:
            station_names: List of station names to normalize
            network_graph: Optional network graph for priority matching
            
        Returns:
            List of normalized station names
        """
        normalized_stations = []
        for station_name in station_names:
            normalized_station = self.normalize_station_name(station_name, network_graph)
            normalized_stations.append(normalized_station)
        
        return normalized_stations
    
    def find_station_variants(self, station_name: str) -> List[str]:
        """
        Find all possible variants of a station name.
        
        Args:
            station_name: The station name to find variants for
            
        Returns:
            List of station name variants
        """
        variants = [station_name]
        normalized_input = station_name.lower()
        
        # Add London prefix variant
        if not normalized_input.startswith("london "):
            london_variant = f"London {station_name}"
            variants.append(london_variant)
        else:
            # Remove London prefix variant
            base_name = station_name[7:]  # Remove "London "
            variants.append(base_name)
        
        # Add variants with different suffixes
        suffixes_to_try = [" (Main)", " Central", " Parkway", " International"]
        for suffix in suffixes_to_try:
            if not station_name.endswith(suffix):
                variants.append(station_name + suffix)
            else:
                # Remove suffix variant
                base_name = station_name[:-len(suffix)]
                variants.append(base_name)
        
        # Add case variants
        variants.extend([
            station_name.upper(),
            station_name.lower(),
            station_name.title()
        ])
        
        # Remove duplicates while preserving order
        unique_variants = []
        seen = set()
        for variant in variants:
            if variant not in seen:
                unique_variants.append(variant)
                seen.add(variant)
        
        return unique_variants
    
    def are_stations_equivalent(self, station1: str, station2: str) -> bool:
        """
        Check if two station names refer to the same station.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            True if the stations are equivalent, False otherwise
        """
        # Normalize station names for comparison
        def normalize_for_comparison(name):
            return name.lower().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        norm1 = normalize_for_comparison(station1)
        norm2 = normalize_for_comparison(station2)
        
        # Exact match
        if norm1 == norm2:
            return True
        
        # Handle London prefix variants
        if norm1.startswith("london"):
            base1 = norm1[6:]  # Remove "london"
            if base1 == norm2:
                return True
        
        if norm2.startswith("london"):
            base2 = norm2[6:]  # Remove "london"
            if base2 == norm1:
                return True
        
        # Common variations
        variations = [
            ("central", ""),
            ("main", ""),
            ("parkway", ""),
            ("international", ""),
        ]
        
        for var1, var2 in variations:
            if norm1.replace(var1, var2) == norm2 or norm1 == norm2.replace(var1, var2):
                return True
        
        return False
    
    def get_canonical_station_name(self, station_name: str, network_graph: Optional[Dict] = None) -> str:
        """
        Get the canonical (preferred) name for a station.
        
        Args:
            station_name: The station name to get canonical form for
            network_graph: Optional network graph for priority matching
            
        Returns:
            The canonical station name
        """
        # First try to normalize the station name
        normalized = self.normalize_station_name(station_name, network_graph)
        
        # If we have a network graph, prefer names that exist in the graph
        if network_graph and normalized in network_graph:
            return normalized
        
        # Otherwise, prefer the normalized name from the data repository
        all_stations = self.data_repository.get_all_station_names()
        if normalized in all_stations:
            return normalized
        
        # If all else fails, return the original name
        return station_name
    
    def validate_station_name(self, station_name: str, network_graph: Optional[Dict] = None) -> bool:
        """
        Validate that a station name exists in the system.
        
        Args:
            station_name: The station name to validate
            network_graph: Optional network graph for validation
            
        Returns:
            True if the station exists, False otherwise
        """
        # Try to normalize the station name
        normalized = self.normalize_station_name(station_name, network_graph)
        
        # Check if it exists in the data repository
        if self.data_repository.validate_station_exists(normalized):
            return True
        
        # Check if it exists in the network graph
        if network_graph and normalized in network_graph:
            return True
        
        return False
    
    def get_station_search_suggestions(self, partial_name: str, max_suggestions: int = 10) -> List[str]:
        """
        Get station name suggestions based on partial input.
        
        Args:
            partial_name: Partial station name to search for
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of suggested station names
        """
        all_stations = self.data_repository.get_all_station_names()
        partial_lower = partial_name.lower()
        
        suggestions = []
        
        # First, find stations that start with the partial name
        for station in all_stations:
            if station.lower().startswith(partial_lower):
                suggestions.append(station)
                if len(suggestions) >= max_suggestions:
                    break
        
        # If we don't have enough suggestions, find stations that contain the partial name
        if len(suggestions) < max_suggestions:
            for station in all_stations:
                if (partial_lower in station.lower() and 
                    station not in suggestions):
                    suggestions.append(station)
                    if len(suggestions) >= max_suggestions:
                        break
        
        return suggestions[:max_suggestions]
    
    def clean_station_name(self, station_name: str) -> str:
        """
        Clean a station name by removing extra whitespace and normalizing format.
        
        Args:
            station_name: The station name to clean
            
        Returns:
            The cleaned station name
        """
        # Remove extra whitespace
        cleaned = " ".join(station_name.split())
        
        # Normalize common abbreviations
        abbreviations = {
            " St ": " Street ",
            " Rd ": " Road ",
            " Ave ": " Avenue ",
            " Jct ": " Junction ",
            " Intl ": " International ",
        }
        
        for abbrev, full in abbreviations.items():
            cleaned = cleaned.replace(abbrev, full)
        
        # Ensure proper capitalization for common words
        words = cleaned.split()
        capitalized_words = []
        
        for word in words:
            # Keep certain words lowercase unless they're the first word
            lowercase_words = {"and", "of", "the", "in", "on", "at", "to", "for"}
            if word.lower() in lowercase_words and len(capitalized_words) > 0:
                capitalized_words.append(word.lower())
            else:
                capitalized_words.append(word.capitalize())
        
        return " ".join(capitalized_words)