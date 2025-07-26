"""
Walking Connection Service

Centralized service for determining walking connections between stations.
This service implements the core logic:
1. Only allow walking connections between stations that are close enough for walking
2. AND on different lines
3. AND not served by the same physical train that continues on a line
"""

import logging
import math
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

class WalkingConnectionService:
    """
    Centralized service for determining walking connections between stations.
    
    This service implements the core logic:
    1. Only allow walking connections between stations that are close enough for walking
    2. AND on different lines
    3. AND not served by the same physical train that continues on a line
    """
    
    def __init__(self, data_repository):
        """
        Initialize the walking connection service.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        
        # Caches for performance
        self._station_to_lines_cache = None
        self._station_coordinates_cache = None
        self._walking_connections_cache = None
        self._interchange_data_cache = None
        self._line_interchanges_cache = None
        
    def is_walking_connection_allowed(self, station1: str, station2: str) -> bool:
        """
        Determine if a walking connection is allowed between two stations.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            bool: True if walking connection is allowed, False otherwise
        """
        # Skip London non-terminal stations
        if not self._are_valid_london_stations(station1, station2):
            return False
            
        # Core logic:
        # 1. Check if stations are close enough for walking
        if not self._are_stations_close_enough(station1, station2):
            return False
            
        # 2. Check if stations are on different lines
        if self._are_stations_on_same_line(station1, station2):
            return False
            
        # 3. Check if there's a direct train connection
        if self._have_direct_train_connection(station1, station2):
            return False
            
        # 4. Check if there's a through service
        if self._have_through_service(station1, station2):
            return False
            
        # 5. Check if stations are served by the same physical train
        if self._are_served_by_same_physical_train(station1, station2):
            return False
            
        # If all checks pass, walking connection is allowed
        return True
    
    def _are_valid_london_stations(self, station1: str, station2: str) -> bool:
        """
        Check if stations are valid for walking connections with respect to London stations.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Define London terminals
        london_terminals = {
            "London Waterloo", "London Victoria", "London Paddington", "London Kings Cross",
            "London St Pancras", "London Euston", "London Liverpool Street", "London Bridge",
            "London Charing Cross", "London Cannon Street", "London Fenchurch Street",
            "London Marylebone", "Clapham Junction"
        }
        
        # Check if stations are in London but not terminals
        station1_in_london = "London" in station1
        station2_in_london = "London" in station2
        
        station1_is_terminal = station1 in london_terminals
        station2_is_terminal = station2 in london_terminals
        
        # Skip if either station is in London but not a terminal
        if (station1_in_london and not station1_is_terminal) or (station2_in_london and not station2_is_terminal):
            self.logger.info(f"Skipping walking connection involving non-terminal London station: {station1} ↔ {station2}")
            return False
            
        # Skip walking connections between London terminals
        if station1_in_london and station2_in_london and station1_is_terminal and station2_is_terminal:
            self.logger.info(f"Skipping walking connection between London terminals: {station1} ↔ {station2}")
            return False
            
        return True
    
    def _are_stations_close_enough(self, station1: str, station2: str, max_distance_m: int = 1000) -> bool:
        """
        Check if stations are close enough for walking based on haversine distance.
        
        Args:
            station1: First station name
            station2: Second station name
            max_distance_m: Maximum walking distance in meters
            
        Returns:
            bool: True if stations are close enough, False otherwise
        """
        # Get station coordinates
        coordinates = self._get_station_coordinates()
        
        if station1 not in coordinates or station2 not in coordinates:
            self.logger.debug(f"Missing coordinates for station: {station1} or {station2}")
            return False
            
        # Calculate haversine distance
        distance_km = self._calculate_haversine_distance(
            coordinates[station1], coordinates[station2]
        )
        
        # Convert to meters and check against max distance
        distance_m = distance_km * 1000
        is_close_enough = distance_m <= max_distance_m
        
        if is_close_enough:
            self.logger.debug(f"Stations are close enough for walking: {station1} ↔ {station2} ({distance_m:.1f}m)")
        else:
            self.logger.debug(f"Stations are too far for walking: {station1} ↔ {station2} ({distance_m:.1f}m)")
            
        return is_close_enough
    
    def _are_stations_on_same_line(self, station1: str, station2: str) -> bool:
        """
        Check if stations are on the same line.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            bool: True if stations are on the same line, False otherwise
        """
        # Get station-to-lines mapping
        station_to_lines = self._get_station_to_lines_mapping()
        
        if station1 not in station_to_lines or station2 not in station_to_lines:
            self.logger.debug(f"Missing line information for station: {station1} or {station2}")
            return False
            
        # Get lines for each station
        lines1 = station_to_lines[station1]
        lines2 = station_to_lines[station2]
        
        # Check if there's any overlap in the lines
        common_lines = set(lines1) & set(lines2)
        
        if common_lines:
            self.logger.info(f"Stations are on the same line(s) {common_lines}: {station1} ↔ {station2}")
            return True
        else:
            self.logger.debug(f"Stations are on different lines: {station1} ↔ {station2}")
            return False
    
    def _have_direct_train_connection(self, station1: str, station2: str) -> bool:
        """
        Check if stations have a direct train connection.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            bool: True if stations have a direct train connection, False otherwise
        """
        # Load interchange data
        interchange_data = self._get_interchange_data()
        
        # Check direct connections
        for direct_conn in interchange_data.get('direct_connections', []):
            direct_from = direct_conn.get('from_station', '')
            direct_to = direct_conn.get('to_station', '')
            walking_distance = direct_conn.get('walking_distance_m', -1)
            
            # If there's a direct train connection with no walking
            if walking_distance == 0 and (
                (direct_from == station1 and direct_to == station2) or
                (direct_from == station2 and direct_to == station1)
            ):
                self.logger.info(f"Direct train connection exists: {station1} ↔ {station2}")
                return True
                
        return False
    
    def _have_through_service(self, station1: str, station2: str) -> bool:
        """
        Check if stations have a through service (same train continues).
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            bool: True if stations have a through service, False otherwise
        """
        # Get station-to-lines mapping
        station_to_lines = self._get_station_to_lines_mapping()
        
        if station1 not in station_to_lines or station2 not in station_to_lines:
            return False
            
        # Get lines for each station
        lines1 = station_to_lines[station1]
        lines2 = station_to_lines[station2]
        
        # Get line interchanges
        line_interchanges = self._get_line_interchanges()
        
        # Check if any pair of lines from the two stations has a through service
        for line1 in lines1:
            for line2 in lines2:
                # Skip if same line (already checked by _are_stations_on_same_line)
                if line1 == line2:
                    continue
                    
                # Check all stations for through services between these lines
                for station, connections in line_interchanges.items():
                    for connection in connections:
                        connection_from_line = connection.get("from_line", "")
                        connection_to_line = connection.get("to_line", "")
                        requires_change = connection.get("requires_change", True)
                        
                        if not requires_change and (
                            (connection_from_line == line1 and connection_to_line == line2) or
                            (connection_from_line == line2 and connection_to_line == line1)
                        ):
                            self.logger.info(f"Through service exists between {line1} and {line2} at {station}")
                            return True
        
        return False
    
    def _are_served_by_same_physical_train(self, station1: str, station2: str) -> bool:
        """
        Check if stations are served by the same physical train that continues on a line.
        This is a more specific check than _have_through_service as it checks for specific
        station pairs that are known to be served by the same physical train.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            bool: True if stations are served by the same physical train, False otherwise
        """
        # Special case for Clapham Junction to London Waterloo
        if (station1 == "Clapham Junction" and station2 == "London Waterloo") or \
           (station1 == "London Waterloo" and station2 == "Clapham Junction"):
            self.logger.info(f"Same physical train serves: {station1} ↔ {station2}")
            return True
            
        # Check other known same-train connections
        same_train_connections = [
            ("Woking", "London Waterloo"),
            ("Guildford", "London Waterloo"),
            ("Basingstoke", "London Waterloo"),
            ("Reading", "London Paddington"),
            ("Oxford", "London Paddington")
        ]
        
        for conn in same_train_connections:
            if (station1 == conn[0] and station2 == conn[1]) or \
               (station1 == conn[1] and station2 == conn[0]):
                self.logger.info(f"Same physical train serves: {station1} ↔ {station2}")
                return True
                
        return False
    
    def _get_station_to_lines_mapping(self) -> Dict[str, List[str]]:
        """
        Get a mapping of stations to the lines they are on.
        
        Returns:
            Dict[str, List[str]]: Mapping of station names to lists of line names
        """
        if self._station_to_lines_cache is not None:
            return self._station_to_lines_cache
            
        station_to_lines = {}
        for line in self.data_repository.load_railway_lines():
            for station in line.stations:
                if station not in station_to_lines:
                    station_to_lines[station] = []
                station_to_lines[station].append(line.name)
                
        self._station_to_lines_cache = station_to_lines
        self.logger.debug(f"Built station-to-lines mapping with {len(station_to_lines)} stations")
        
        return station_to_lines
    
    def _get_station_coordinates(self) -> Dict[str, Dict[str, float]]:
        """
        Get a mapping of stations to their coordinates.
        
        Returns:
            Dict[str, Dict[str, float]]: Mapping of station names to coordinate dictionaries
        """
        if self._station_coordinates_cache is not None:
            return self._station_coordinates_cache
            
        station_coordinates = {}
        
        # Try to use data path resolver
        try:
            from ...utils.data_path_resolver import get_lines_directory
            lines_dir = get_lines_directory()
        except (ImportError, FileNotFoundError):
            # Fallback to old method
            lines_dir = Path("src/data/lines")
            
        if not lines_dir.exists():
            self.logger.error(f"Lines directory not found: {lines_dir}")
            return {}
            
        try:
            for json_file in lines_dir.glob("*.json"):
                if json_file.name.endswith('.backup'):
                    continue
                    
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    stations = data.get('stations', [])
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        coordinates = station.get('coordinates', {})
                        
                        if station_name and coordinates and 'lat' in coordinates and 'lng' in coordinates:
                            station_coordinates[station_name] = coordinates
            
            self._station_coordinates_cache = station_coordinates
            self.logger.debug(f"Built station coordinates mapping with {len(station_coordinates)} stations")
            
            return station_coordinates
            
        except Exception as e:
            self.logger.error(f"Failed to build station coordinates mapping: {e}")
            return {}
    
    def _get_interchange_data(self) -> Dict[str, Any]:
        """
        Get interchange data from the interchange_connections.json file.
        
        Returns:
            Dict[str, Any]: Interchange data
        """
        if self._interchange_data_cache is not None:
            return self._interchange_data_cache
            
        try:
            # Try to use data path resolver
            try:
                from ...utils.data_path_resolver import get_data_file_path
                interchange_file = get_data_file_path("interchange_connections.json")
            except (ImportError, FileNotFoundError):
                # Fallback to old method
                interchange_file = Path("src/data/interchange_connections.json")
                
            if not interchange_file.exists():
                self.logger.error(f"Interchange connections file not found: {interchange_file}")
                return {}
                
            with open(interchange_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self._interchange_data_cache = data
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load interchange data: {e}")
            return {}
    
    def _get_line_interchanges(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get line interchanges data from the interchange_connections.json file.
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Mapping of station names to lists of line connections
        """
        if self._line_interchanges_cache is not None:
            return self._line_interchanges_cache
            
        try:
            interchange_data = self._get_interchange_data()
            line_interchanges_data = interchange_data.get('line_interchanges', [])
            
            # Convert to dictionary for faster lookup
            line_interchanges = {}
            for item in line_interchanges_data:
                station = item.get('station', '')
                connections = item.get('connections', [])
                if station:
                    line_interchanges[station] = connections
            
            self._line_interchanges_cache = line_interchanges
            self.logger.debug(f"Loaded line interchanges for {len(line_interchanges)} stations")
            
            return line_interchanges
            
        except Exception as e:
            self.logger.error(f"Error loading line interchanges data: {e}")
            return {}
    
    def _calculate_haversine_distance(self, coord1: Dict, coord2: Dict) -> float:
        """
        Calculate the Haversine distance between two coordinates in kilometers.
        
        Args:
            coord1: Dictionary with 'lat' and 'lng' keys
            coord2: Dictionary with 'lat' and 'lng' keys
            
        Returns:
            float: Distance in kilometers
        """
        # Extract coordinates (using 'lat' and 'lng' keys from JSON data)
        lat1 = math.radians(coord1['lat'])
        lon1 = math.radians(coord1['lng'])
        lat2 = math.radians(coord2['lat'])
        lon2 = math.radians(coord2['lng'])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        earth_radius_km = 6371.0
        
        return earth_radius_km * c
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._station_to_lines_cache = None
        self._station_coordinates_cache = None
        self._walking_connections_cache = None
        self._interchange_data_cache = None
        self._line_interchanges_cache = None
        
        self.logger.info("Walking connection service cache cleared")