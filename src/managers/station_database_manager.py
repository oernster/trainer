"""
Station Database Manager for offline railway station data with Service Pattern Support.
Author: Oliver Ernster

This module provides functionality to load and search UK railway station data
from local JSON files, with support for service patterns (express, fast, stopping).
UPDATED: Now uses station names exclusively - no more station codes.
"""

import json
import logging
import math
import heapq
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, time
import sys

# Add models to path for service patterns import
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.service_patterns import ServicePatternSet, ServicePattern, ServiceType

logger = logging.getLogger(__name__)

@dataclass
class Station:
    """Represents a railway station."""
    name: str
    coordinates: Dict[str, float]
    zone: Optional[int] = None
    interchange: Optional[List[str]] = None

@dataclass
class RailwayLine:
    """Represents a railway line with its stations."""
    name: str
    file: str
    operator: str
    terminus_stations: List[str]
    major_stations: List[str]
    stations: List[Station]
    service_patterns: Optional[ServicePatternSet] = None

class StationDatabaseManager:
    """Manages the offline railway station database with service pattern support."""
    
    def __init__(self):
        """Initialize the station database manager."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.lines_dir = self.data_dir / "lines"
        self.railway_lines: Dict[str, RailwayLine] = {}
        self.all_stations: Dict[str, Station] = {}  # name -> Station
        self.loaded = False
    
    def load_database(self) -> bool:
        """Load the railway station database from JSON files."""
        logger.info("Loading railway station database...")
        
        # Force clear all existing data
        self.railway_lines.clear()
        self.all_stations.clear()
        self.loaded = False
        
        try:
            # Load the railway lines index
            index_file = self.data_dir / "railway_lines_index.json"
            if not index_file.exists():
                logger.error(f"Railway lines index not found: {index_file}")
                return False
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Load each railway line with minimal logging
            logger.info(f"Loading {len(index_data['lines'])} railway lines...")
            for i, line_info in enumerate(index_data['lines']):
                line_name = line_info.get('name', 'Unknown')
                line_file_name = line_info.get('file', 'unknown.json')
                line_file = self.lines_dir / line_file_name
                
                if not line_file.exists():
                    logger.warning(f"Railway line file not found: {line_file}")
                    continue
                
                try:
                    with open(line_file, 'r', encoding='utf-8') as f:
                        line_data = json.load(f)
                except Exception as json_error:
                    logger.error(f"JSON loading failed for {line_name}: {json_error}")
                    continue
                
                # Create Station objects
                stations = []
                stations_data = line_data.get('stations', [])
                
                for j, station_data in enumerate(stations_data):
                    try:
                        station_name = station_data.get('name', 'Unknown')
                        
                        station = Station(
                            name=station_name,
                            coordinates=station_data.get('coordinates', {}),
                            zone=station_data.get('zone'),
                            interchange=station_data.get('interchange')
                        )
                        stations.append(station)
                        
                        # Use station name as primary key
                        self.all_stations[station_name] = station
                            
                    except Exception as station_error:
                        logger.error(f"Error loading station {j+1} in {line_name}: {station_error}")
                        continue
                
                # Load service patterns if they exist
                service_patterns = None
                if 'service_patterns' in line_data:
                    try:
                        service_patterns = ServicePatternSet.from_dict({
                            "line_name": line_info['name'],
                            "line_type": "suburban",  # Default, will be classified properly
                            "patterns": line_data['service_patterns'],
                            "default_pattern": "fast"  # Default
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load service patterns for {line_info['name']}: {e}")
                
                # Create RailwayLine object
                railway_line = RailwayLine(
                    name=line_info['name'],
                    file=line_info['file'],
                    operator=line_info['operator'],
                    terminus_stations=line_info['terminus_stations'],
                    major_stations=line_info['major_stations'],
                    stations=stations,
                    service_patterns=service_patterns
                )
                
                self.railway_lines[line_info['name']] = railway_line
            
            self.loaded = True
            logger.info(f"Database loading complete: {len(self.railway_lines)} railway lines, {len(self.all_stations)} stations")
            
            # Verify key stations are loaded
            key_stations = ["Farnborough (Main)", "London Waterloo", "Fleet", "Woking"]
            missing_stations = []
            for station_name in key_stations:
                if station_name not in self.all_stations:
                    missing_stations.append(station_name)
            
            if missing_stations:
                logger.warning(f"Missing key stations: {missing_stations}")
            else:
                logger.debug("All key stations loaded successfully")
            
            # Final verification test
            logger.debug("Running database integrity test...")
            test_result = self._test_database_integrity()
            if not test_result:
                logger.error("Database integrity test failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load station database: {e}")
            return False

    def get_service_patterns_for_line(self, line_name: str) -> Optional[ServicePatternSet]:
        """Get service patterns for a railway line."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        railway_line = self.railway_lines.get(line_name)
        if railway_line:
            return railway_line.service_patterns
        return None
    
    def find_best_service_pattern(self, from_station: str, to_station: str, line_name: str, 
                                departure_time: Optional[str] = None) -> Optional[ServicePattern]:
        """Find the best service pattern (prefer fast over semi-fast over stopping)."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return None
        
        # Get all station names for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return None
        
        all_station_names = [station.name for station in railway_line.stations]
        
        # Find the best pattern that serves both stations
        return service_patterns.get_best_pattern_for_stations(from_station, to_station, all_station_names)
    
    def get_stations_for_service_pattern(self, line_name: str, pattern_name: str) -> List[str]:
        """Get station names for a specific service pattern."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return []
        
        pattern = service_patterns.get_pattern(pattern_name)
        if not pattern:
            return []
        
        # Get all station names for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return []
        
        all_station_names = [station.name for station in railway_line.stations]
        
        if pattern.stations == "all":
            return all_station_names
        elif isinstance(pattern.stations, list):
            return pattern.stations
        return []
    
    def build_service_aware_network(self) -> Dict[str, Dict]:
        """
        Build network considering service patterns.
        Creates connections only between stations served by the same pattern,
        with weights based on service speed (fast < semi-fast < stopping).
        """
        if not self.loaded:
            if not self.load_database():
                return {}
        
        network = {}
        
        # Initialize all stations in the network
        for station_name, station in self.all_stations.items():
            network[station_name] = {
                'station': station,
                'coordinates': station.coordinates,
                'connections': [],  # List of (connected_station_name, distance, time, line_name, service_pattern, priority)
                'interchange_lines': station.interchange or [],
                'is_major_interchange': len(station.interchange or []) >= 2,
                'lines': self.get_railway_lines_for_station(station_name)
            }
        
        # Build connections based on service patterns
        for line_name, railway_line in self.railway_lines.items():
            if not railway_line.service_patterns:
                # Fallback to old method if no service patterns
                self._add_legacy_connections(network, railway_line, line_name)
                continue
            
            # For each service pattern, create connections
            for pattern_code, pattern in railway_line.service_patterns.patterns.items():
                pattern_stations = self.get_stations_for_service_pattern(line_name, pattern_code)
                
                # Create connections between consecutive stations in this service pattern
                for i in range(len(pattern_stations) - 1):
                    current_name = pattern_stations[i]
                    next_name = pattern_stations[i + 1]
                    
                    current_station = self.get_station_by_name(current_name)
                    next_station = self.get_station_by_name(next_name)
                    
                    if current_station and next_station:
                        # Calculate distance and time
                        distance = self.calculate_haversine_distance(
                            current_station.coordinates, next_station.coordinates
                        )
                        
                        journey_time = self.get_journey_time_between_stations(current_name, next_name)
                        if not journey_time:
                            # Estimate based on service pattern speed
                            speed_multiplier = {
                                ServiceType.EXPRESS: 0.8,
                                ServiceType.FAST: 1.0,
                                ServiceType.SEMI_FAST: 1.3,
                                ServiceType.STOPPING: 1.5,
                                ServiceType.PEAK: 1.0,
                                ServiceType.OFF_PEAK: 1.1,
                                ServiceType.NIGHT: 1.4
                            }.get(pattern.service_type, 1.2)
                            
                            journey_time = max(2, int(distance * 1.5 * speed_multiplier))
                        
                        # Add bidirectional connections with service pattern info
                        network[current_name]['connections'].append(
                            (next_name, distance, journey_time, line_name, pattern_code, pattern.service_type.priority)
                        )
                        network[next_name]['connections'].append(
                            (current_name, distance, journey_time, line_name, pattern_code, pattern.service_type.priority)
                        )
        
        logger.debug(f"Built service-aware network with {len(network)} stations")
        return network
    
    def _add_legacy_connections(self, network: Dict, railway_line, line_name: str):
        """Add connections for lines without service patterns (legacy method)."""
        stations = railway_line.stations
        
        # Connect adjacent stations on the same line
        for i in range(len(stations) - 1):
            current_station = stations[i]
            next_station = stations[i + 1]
            
            # Calculate distance and time
            distance = self.calculate_haversine_distance(
                current_station.coordinates, next_station.coordinates
            )
            
            journey_time = self.get_journey_time_between_stations(
                current_station.name, next_station.name
            )
            if not journey_time:
                journey_time = max(2, int(distance * 1.5))
            
            # Add bidirectional connections (legacy format)
            network[current_station.name]['connections'].append(
                (next_station.name, distance, journey_time, line_name, "legacy", 3)  # Default priority
            )
            network[next_station.name]['connections'].append(
                (current_station.name, distance, journey_time, line_name, "legacy", 3)
            )

    def dijkstra_shortest_path_with_service_patterns(self, start_name: str, end_name: str,
                                                   max_routes: int = 5, max_changes: int = 3,
                                                   departure_time: Optional[str] = None) -> List[Tuple[List[str], float]]:
        """
        Enhanced Dijkstra with service pattern awareness.
        Prioritizes faster service patterns when building routes.
        """
        import time
        start_time = time.time()
        timeout = 10.0  # 10 second timeout
        
        network = self.build_service_aware_network()
        if start_name not in network or end_name not in network:
            return []
        
        # Check if both stations are on the same line for direct route optimization
        start_lines = set(network[start_name]['lines'])
        end_lines = set(network[end_name]['lines'])
        common_lines = start_lines.intersection(end_lines)
        
        if common_lines:
            # Try to find direct route on same line first
            direct_route = self._find_direct_route_on_line(start_name, end_name, list(common_lines)[0])
            if direct_route:
                return [(direct_route, 1.0)]  # Low cost for direct route
        
        # Priority queue: (total_cost, current_station, path, num_changes, current_line, current_pattern)
        pq = [(0.0, start_name, [start_name], 0, None, None)]
        
        # Track visited states: (station_name, num_changes, pattern) -> best_cost
        visited = {}
        
        # Store found routes
        routes = []
        iterations = 0
        max_iterations = 10000  # Prevent infinite loops
        
        while pq and len(routes) < max_routes and iterations < max_iterations:
            iterations += 1
            
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Route finding timed out after {timeout} seconds")
                break
            
            current_cost, current_station, path, num_changes, current_line, current_pattern = heapq.heappop(pq)
            
            # Create state key
            state_key = (current_station, num_changes, current_pattern)
            
            # Skip if we've found a better path to this state
            if state_key in visited and visited[state_key] <= current_cost:
                continue
            visited[state_key] = current_cost
            
            # Found destination
            if current_station == end_name:
                routes.append((path, current_cost))
                continue
            
            # Don't exceed max changes
            if num_changes >= max_changes:
                continue
            
            # Limit path length to prevent excessive routes
            if len(path) > 20:
                continue
            
            # Explore connections (now includes service pattern info)
            for next_station, distance, time, line_name, pattern_code, priority in network[current_station]['connections']:
                if next_station in path:  # Avoid cycles
                    continue
                
                # Calculate cost for this connection with service pattern priority
                base_cost = time + (distance * 0.1)  # Base cost from time and distance
                pattern_bonus = (4 - priority) * 2  # Faster services get lower cost (priority 1 = 6 bonus, priority 4 = 0 bonus)
                connection_cost = base_cost - pattern_bonus
                
                # Line change penalty
                if current_line and current_line != line_name:
                    connection_cost += 15  # 15-minute penalty for line changes
                
                new_cost = current_cost + connection_cost
                new_path = path + [next_station]
                new_changes = num_changes + (1 if current_line and current_line != line_name else 0)
                
                heapq.heappush(pq, (new_cost, next_station, new_path, new_changes, line_name, pattern_code))
        
        if iterations >= max_iterations:
            logger.warning(f"Route finding stopped after {max_iterations} iterations")
        
        return routes
    
    def _find_direct_route_on_line(self, start_name: str, end_name: str, line_name: str) -> Optional[List[str]]:
        """Find direct route between two stations on the same railway line."""
        try:
            railway_line = self.railway_lines.get(line_name)
            if not railway_line:
                return None
            
            # Get station positions on the line
            station_names = [station.name for station in railway_line.stations]
            
            try:
                start_idx = station_names.index(start_name)
                end_idx = station_names.index(end_name)
            except ValueError:
                return None
            
            # Build direct route
            if start_idx < end_idx:
                # Forward direction
                route_names = station_names[start_idx:end_idx + 1]
            else:
                # Reverse direction
                route_names = station_names[end_idx:start_idx + 1]
                route_names.reverse()
            
            return route_names if len(route_names) >= 2 else None
            
        except Exception as e:
            logger.warning(f"Error finding direct route: {e}")
            return None

    def get_station_by_name(self, station_name: str) -> Optional[Station]:
        """Get station object by name."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        parsed_name = self.parse_station_name(station_name)
        return self.all_stations.get(parsed_name)
    
    def get_railway_lines_for_station(self, station_name: str) -> List[str]:
        """Get all railway lines that serve a given station."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        lines = []
        for line_name, railway_line in self.railway_lines.items():
            line_station_names = [s.name for s in railway_line.stations]
            if station_name in line_station_names:
                lines.append(line_name)
        return lines
    
    def calculate_haversine_distance(self, coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
        """Calculate the great circle distance between two points on Earth using the Haversine formula."""
        if not coord1 or not coord2:
            return float('inf')
        
        lat1, lng1 = coord1.get('lat', 0), coord1.get('lng', 0)
        lat2, lng2 = coord2.get('lat', 0), coord2.get('lng', 0)
        
        if not all([lat1, lng1, lat2, lng2]):
            return float('inf')
        
        # Convert latitude and longitude from degrees to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        earth_radius_km = 6371
        return c * earth_radius_km
    
    def get_journey_time_between_stations(self, from_station: str, to_station: str) -> Optional[int]:
        """Get journey time between two stations from JSON data."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        # Load all line data to find journey times
        for line_name, railway_line in self.railway_lines.items():
            # Load the JSON file for this line to get journey times
            line_file = self.lines_dir / railway_line.file
            if not line_file.exists():
                continue
                
            try:
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                journey_times = line_data.get('typical_journey_times', {})
                
                # Try direct journey time using station names
                journey_key = f"{from_station}-{to_station}"
                if journey_key in journey_times:
                    return journey_times[journey_key]
                
                # Try reverse direction
                reverse_key = f"{to_station}-{from_station}"
                if reverse_key in journey_times:
                    return journey_times[reverse_key]
                    
            except Exception as e:
                logger.warning(f"Error reading journey times from {line_file}: {e}")
                continue
        
        return None

    # UI Compatibility Methods - Required by stations_settings_dialog.py
    
    def search_stations(self, query: str, limit: int = 10) -> List[str]:
        """Search for stations matching the query with disambiguation context and improved case insensitive matching."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        
        matches = []
        for station_name in self.all_stations.keys():
            station_name_lower = station_name.lower()
            
            # Check for matches (case insensitive)
            if query_lower in station_name_lower:
                # Add line context for disambiguation if station appears on multiple lines
                lines = self.get_railway_lines_for_station(station_name)
                if len(lines) > 1:
                    # Add primary line context for disambiguation
                    primary_line = lines[0]  # Use first line as primary
                    disambiguated_name = f"{station_name} ({primary_line})"
                    matches.append(disambiguated_name)
                else:
                    matches.append(station_name)
        
        # Sort by relevance with improved scoring
        def relevance_score(station_name):
            name_lower = station_name.lower()
            # Remove disambiguation context for scoring
            if ' (' in name_lower:
                name_lower = name_lower.split(' (')[0]
            
            # Exact match gets highest priority
            if name_lower == query_lower:
                return (0, station_name.lower())
            # Starts with query gets second priority
            elif name_lower.startswith(query_lower):
                return (1, station_name.lower())
            # Contains query gets third priority
            else:
                return (2, station_name.lower())
        
        matches.sort(key=relevance_score)
        return matches[:limit]
    
    def parse_station_name(self, station_name: str) -> str:
        """Parse station name to remove disambiguation context."""
        if not station_name:
            return ""
        
        # Remove line context in parentheses - but NOT station name parentheses like (Main)
        if ' (' in station_name:
            # Check if this looks like a line disambiguation (contains line-related words)
            paren_content = station_name.split(' (')[1].split(')')[0] if ')' in station_name else ""
            line_indicators = ['Line', 'Railway', 'Network', 'Express', 'Main Line', 'Coast']
            
            # Only remove if it contains line indicators, keep station name parentheses
            if any(indicator in paren_content for indicator in line_indicators):
                return station_name.split(' (')[0].strip()
        
        return station_name.strip()
    
    def get_all_stations_with_context(self) -> List[str]:
        """Get all stations with disambiguation context where needed."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        stations_with_context = []
        for station_name in self.all_stations.keys():
            lines = self.get_railway_lines_for_station(station_name)
            if len(lines) > 1:
                # Add primary line context for disambiguation
                primary_line = lines[0]
                disambiguated_name = f"{station_name} ({primary_line})"
                stations_with_context.append(disambiguated_name)
            else:
                stations_with_context.append(station_name)
        
        return sorted(stations_with_context)
    
    def suggest_via_stations(self, from_station: str, to_station: str, limit: int = 10) -> List[str]:
        """Suggest via stations for a route."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        # Parse station names
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Find routes and extract intermediate stations
        routes = self.dijkstra_shortest_path_with_service_patterns(
            from_parsed, to_parsed, max_routes=3, max_changes=2
        )
        
        via_stations = set()
        for route_names, _ in routes:
            # Extract intermediate stations (exclude first and last)
            if len(route_names) > 2:
                for station_name in route_names[1:-1]:
                    via_stations.add(station_name)
        
        return sorted(list(via_stations))[:limit]
    
    def find_route_between_stations(self, from_station: str, to_station: str,
                                  max_changes: int = 3, departure_time: Optional[str] = None) -> List[List[str]]:
        """Find routes between stations (UI compatibility method)."""
        return self.find_route_between_stations_with_service_patterns(
            from_station, to_station, max_changes, departure_time
        )
    
    def identify_train_changes(self, route: List[str]) -> List[str]:
        """Identify stations where train changes are required."""
        if not self.loaded or len(route) < 3:
            return []
        
        train_changes = []
        current_line = None
        
        for i in range(len(route) - 1):
            current_station = route[i]
            next_station = route[i + 1]
            
            # Parse station names
            current_parsed = self.parse_station_name(current_station)
            next_parsed = self.parse_station_name(next_station)
            
            # Find common lines between current and next station
            current_lines = set(self.get_railway_lines_for_station(current_parsed))
            next_lines = set(self.get_railway_lines_for_station(next_parsed))
            common_lines = current_lines.intersection(next_lines)
            
            if not common_lines:
                # No common line - train change required at current station
                if i > 0:  # Don't add first station as change point
                    train_changes.append(current_station)
            else:
                # Check if we need to change lines
                if current_line and current_line not in common_lines:
                    if i > 0:
                        train_changes.append(current_station)
                
                # Update current line to one of the common lines
                current_line = list(common_lines)[0]
        
        return train_changes
    
    def get_operator_for_segment(self, from_station: str, to_station: str) -> Optional[str]:
        """Get operator for a segment between two stations."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        # Parse station names
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Find common lines
        from_lines = set(self.get_railway_lines_for_station(from_parsed))
        to_lines = set(self.get_railway_lines_for_station(to_parsed))
        common_lines = from_lines.intersection(to_lines)
        
        if common_lines:
            # Return operator of first common line
            line_name = list(common_lines)[0]
            railway_line = self.railway_lines.get(line_name)
            if railway_line:
                return railway_line.operator
        
        return None
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        if not self.loaded:
            if not self.load_database():
                return {}
        
        return {
            'total_stations': len(self.all_stations),
            'total_lines': len(self.railway_lines),
            'lines_with_service_patterns': sum(1 for line in self.railway_lines.values() if line.service_patterns)
        }

    def find_route_between_stations_with_service_patterns(self, from_station: str, to_station: str,
                                                        max_changes: int = 3,
                                                        departure_time: Optional[str] = None) -> List[List[str]]:
        """
        Find routes between stations using service pattern optimization.
        This is the new main routing method that prioritizes faster services.
        """
        if not self.loaded:
            if not self.load_database():
                logger.error("Database loading failed")
                return []
        
        # Parse station names to remove line context
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Check if stations exist in the database
        from_station_obj = self.all_stations.get(from_parsed)
        to_station_obj = self.all_stations.get(to_parsed)
        
        if not from_station_obj or not to_station_obj:
            logger.error(f"Station objects not found: from='{from_parsed}' -> {from_station_obj is not None}, to='{to_parsed}' -> {to_station_obj is not None}")
            return []
        
        # First try simple direct route check
        direct_route = self._find_simple_direct_route(from_parsed, to_parsed)
        if direct_route:
            return [direct_route]
        
        # Try service pattern aware Dijkstra with timeout protection
        try:
            route_results = self.dijkstra_shortest_path_with_service_patterns(
                from_parsed, to_parsed, max_routes=5, max_changes=max_changes, departure_time=departure_time
            )
            
            # Routes are already in station names
            named_routes = []
            for route_names, cost in route_results:
                if route_names:
                    named_routes.append(route_names)
                    logger.info(f"Service-aware route: {' -> '.join(route_names)} (Cost: {cost:.2f})")
            
            if named_routes:
                return named_routes
                
        except Exception as e:
            logger.debug(f"Service pattern routing failed: {e}")
        
        # Fallback to simple routing if service pattern routing fails
        logger.info("Falling back to simple routing")
        return self._find_simple_routes(from_parsed, to_parsed, max_changes)
    
    def _find_simple_direct_route(self, from_name: str, to_name: str) -> Optional[List[str]]:
        """Find a simple direct route between two stations on the same line."""
        try:
            # Check if both stations are on the same line
            from_lines = set(self.get_railway_lines_for_station(from_name))
            to_lines = set(self.get_railway_lines_for_station(to_name))
            common_lines = from_lines.intersection(to_lines)
            
            if common_lines:
                # Use the first common line
                line_name = list(common_lines)[0]
                return self._find_direct_route_on_line(from_name, to_name, line_name)
            
            return None
        except Exception as e:
            logger.warning(f"Error in simple direct route: {e}")
            return None
    
    def _find_simple_routes(self, from_name: str, to_name: str, max_changes: int = 3) -> List[List[str]]:
        """Simple fallback routing without service patterns."""
        try:
            routes = []
            
            # Try direct route first
            direct_route = self._find_simple_direct_route(from_name, to_name)
            if direct_route:
                routes.append(direct_route)
                return routes
            
            # Try one-change routes through major interchange stations
            major_interchanges = ['London Waterloo', 'Victoria', 'London Bridge', 'Paddington',
                                'King\'s Cross', 'Euston', 'Liverpool Street', 'Clapham Junction',
                                'Birmingham New Street', 'Manchester Piccadilly']
            
            from_lines = set(self.get_railway_lines_for_station(from_name))
            to_lines = set(self.get_railway_lines_for_station(to_name))
            
            for interchange_name in major_interchanges:
                if interchange_name == from_name or interchange_name == to_name:
                    continue
                
                interchange_lines = set(self.get_railway_lines_for_station(interchange_name))
                
                # Check if interchange connects both origin and destination lines
                if (from_lines.intersection(interchange_lines) and
                    to_lines.intersection(interchange_lines)):
                    
                    # Build route through interchange
                    first_leg = self._find_simple_direct_route(from_name, interchange_name)
                    second_leg = self._find_simple_direct_route(interchange_name, to_name)
                    
                    if first_leg and second_leg:
                        # Combine legs, removing duplicate interchange station
                        combined_route = first_leg + second_leg[1:]
                        routes.append(combined_route)
                        
                        if len(routes) >= 3:  # Limit to 3 routes
                            break
            
            return routes
            
        except Exception as e:
            logger.error(f"Error in simple routing: {e}")
            return []

    def _test_database_integrity(self) -> bool:
        """Test database integrity by checking key stations exist by name."""
        try:
            # Test key stations that should definitely exist (by name only now)
            test_stations = [
                "Farnborough (Main)",
                "London Waterloo",
                "Fleet",
                "Woking",
                "Clapham Junction"
            ]
            
            all_passed = True
            failed_tests = []
            
            for station_name in test_stations:
                # Test that station exists in all_stations (now keyed by name)
                if station_name not in self.all_stations:
                    failed_tests.append(f"'{station_name}' -> Station not found in database")
                    all_passed = False
                    continue
                
                # Test that we can get the station object
                station_obj = self.all_stations.get(station_name)
                if not station_obj or station_obj.name != station_name:
                    failed_tests.append(f"'{station_name}' -> Station object lookup failed")
                    all_passed = False
            
            if all_passed:
                logger.debug("All database integrity tests passed")
            else:
                logger.error(f"Database integrity test failures: {failed_tests}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Database integrity test error: {e}")
            return False
