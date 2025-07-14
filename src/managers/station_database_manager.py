"""
Station Database Manager for offline railway station data with Service Pattern Support.
Author: Oliver Ernster

This module provides functionality to load and search UK railway station data
from local JSON files, with support for service patterns (express, fast, stopping).
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
    code: str
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
        self.all_stations: Dict[str, Station] = {}  # name -> Station (changed from code -> Station)
        self.station_name_to_code: Dict[str, str] = {}  # name -> code (kept for compatibility)
        self.loaded = False
    
    def _generate_station_code(self, station_name: str) -> str:
        """Generate a simple station code from the station name for backward compatibility."""
        # Remove common words and create a simple code
        name = station_name.upper()
        name = name.replace("(MAIN)", "").replace("(", "").replace(")", "")
        name = name.replace(" CENTRAL", "").replace(" JUNCTION", " JCT")
        name = name.replace(" STREET", " ST").replace(" ROAD", " RD")
        
        # Split into words and take first letters
        words = name.split()
        if len(words) == 1:
            # Single word - take first 3 characters
            return words[0][:3]
        elif len(words) == 2:
            # Two words - take first 2 chars of first, first char of second
            return words[0][:2] + words[1][:1]
        else:
            # Multiple words - take first char of each up to 3
            return ''.join(word[:1] for word in words[:3])
    
    def load_database(self) -> bool:
        """Load the railway station database from JSON files."""
        logger.info("Loading railway station database...")
        
        # Force clear all existing data
        self.railway_lines.clear()
        self.all_stations.clear()
        self.station_name_to_code.clear()
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
                        # Generate a simple code from the name for backward compatibility
                        station_code = self._generate_station_code(station_name)
                        
                        station = Station(
                            name=station_name,
                            code=station_code,
                            coordinates=station_data.get('coordinates', {}),
                            zone=station_data.get('zone'),
                            interchange=station_data.get('interchange')
                        )
                        stations.append(station)
                        
                        # Use station name as primary key now
                        self.all_stations[station_name] = station
                        self.station_name_to_code[station_name] = station_code
                            
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
            
            # Verify key stations are loaded (debug level)
            key_stations = ["Farnborough (Main)", "London Waterloo", "Fleet", "Woking"]
            missing_stations = []
            for station_name in key_stations:
                code = self.station_name_to_code.get(station_name)
                if not code:
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
    
    def find_best_service_pattern(self, from_code: str, to_code: str, line_name: str, 
                                departure_time: Optional[str] = None) -> Optional[ServicePattern]:
        """Find the best service pattern (prefer fast over semi-fast over stopping)."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return None
        
        # Get all station codes for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return None
        
        all_station_codes = [station.code for station in railway_line.stations]
        
        # Find the best pattern that serves both stations
        return service_patterns.get_best_pattern_for_stations(from_code, to_code, all_station_codes)
    
    def get_stations_for_service_pattern(self, line_name: str, pattern_name: str) -> List[str]:
        """Get station codes for a specific service pattern."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return []
        
        pattern = service_patterns.get_pattern(pattern_name)
        if not pattern:
            return []
        
        # Get all station codes for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return []
        
        all_station_codes = [station.code for station in railway_line.stations]
        
        if pattern.stations == "all":
            return all_station_codes
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
        for station_code, station in self.all_stations.items():
            network[station_code] = {
                'station': station,
                'coordinates': station.coordinates,
                'connections': [],  # List of (connected_station_code, distance, time, line_name, service_pattern, priority)
                'interchange_lines': station.interchange or [],
                'is_major_interchange': len(station.interchange or []) >= 2,
                'lines': self.get_railway_lines_for_station(station_code)
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
                    current_code = pattern_stations[i]
                    next_code = pattern_stations[i + 1]
                    
                    current_station = self.get_station_by_code(current_code)
                    next_station = self.get_station_by_code(next_code)
                    
                    if current_station and next_station:
                        # Calculate distance and time
                        distance = self.calculate_haversine_distance(
                            current_station.coordinates, next_station.coordinates
                        )
                        
                        journey_time = self.get_journey_time_between_stations(current_code, next_code)
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
                        network[current_code]['connections'].append(
                            (next_code, distance, journey_time, line_name, pattern_code, pattern.service_type.priority)
                        )
                        network[next_code]['connections'].append(
                            (current_code, distance, journey_time, line_name, pattern_code, pattern.service_type.priority)
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
                current_station.code, next_station.code
            )
            if not journey_time:
                journey_time = max(2, int(distance * 1.5))
            
            # Add bidirectional connections (legacy format)
            network[current_station.code]['connections'].append(
                (next_station.code, distance, journey_time, line_name, "legacy", 3)  # Default priority
            )
            network[next_station.code]['connections'].append(
                (current_station.code, distance, journey_time, line_name, "legacy", 3)
            )

    def dijkstra_shortest_path_with_service_patterns(self, start_code: str, end_code: str,
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
        if start_code not in network or end_code not in network:
            return []
        
        # Check if both stations are on the same line for direct route optimization
        start_lines = set(network[start_code]['lines'])
        end_lines = set(network[end_code]['lines'])
        common_lines = start_lines.intersection(end_lines)
        
        if common_lines:
            # Try to find direct route on same line first
            direct_route = self._find_direct_route_on_line(start_code, end_code, list(common_lines)[0])
            if direct_route:
                return [(direct_route, 1.0)]  # Low cost for direct route
        
        # Priority queue: (total_cost, current_station, path, num_changes, current_line, current_pattern)
        pq = [(0.0, start_code, [start_code], 0, None, None)]
        
        # Track visited states: (station_code, num_changes, pattern) -> best_cost
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
            if current_station == end_code:
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
    
    def _find_direct_route_on_line(self, start_code: str, end_code: str, line_name: str) -> Optional[List[str]]:
        """Find direct route between two stations on the same railway line."""
        try:
            railway_line = self.railway_lines.get(line_name)
            if not railway_line:
                return None
            
            # Get station positions on the line
            station_codes = [station.code for station in railway_line.stations]
            
            try:
                start_idx = station_codes.index(start_code)
                end_idx = station_codes.index(end_code)
            except ValueError:
                return None
            
            # Build direct route
            if start_idx < end_idx:
                # Forward direction
                route_codes = station_codes[start_idx:end_idx + 1]
            else:
                # Reverse direction
                route_codes = station_codes[end_idx:start_idx + 1]
                route_codes.reverse()
            
            # Convert codes to names
            route_names = []
            for code in route_codes:
                station = self.get_station_by_code(code)
                if station:
                    route_names.append(station.name)
            
            return route_names if len(route_names) >= 2 else None
            
        except Exception as e:
            logger.warning(f"Error finding direct route: {e}")
            return None

    # Include essential methods from original file
    def get_station_code(self, station_name: str) -> Optional[str]:
        """Get station code for a station name."""
        if not self.loaded:
            logger.debug("Database not loaded, loading now...")
            if not self.load_database():
                logger.error("Database loading failed")
                return None
        
        station_name_clean = station_name.strip()
        logger.debug(f"Looking up station: '{station_name_clean}'")
        
        # Check for exact match
        code = self.station_name_to_code.get(station_name_clean)
        if code:
            result_code = code.upper() if code else None
            logger.debug(f"Found exact match: '{station_name_clean}' -> '{result_code}'")
            return result_code
        
        # Check for case-insensitive matches
        case_insensitive_matches = []
        for name, stored_code in self.station_name_to_code.items():
            if name.lower() == station_name_clean.lower():
                case_insensitive_matches.append((name, stored_code))
        
        if case_insensitive_matches:
            _, code = case_insensitive_matches[0]
            result_code = code.upper() if code else None
            logger.debug(f"Using case-insensitive match: '{station_name_clean}' -> '{result_code}'")
            return result_code
        
        # Check for partial matches (for debugging)
        partial_matches = []
        for name in self.station_name_to_code.keys():
            if station_name_clean.lower() in name.lower() or name.lower() in station_name_clean.lower():
                partial_matches.append(name)
        
        if partial_matches:
            logger.debug(f"Partial matches found for '{station_name_clean}': {partial_matches[:3]}")
        
        logger.warning(f"Station '{station_name_clean}' not found in database")
        return None
    
    def get_station_by_code(self, station_code: str) -> Optional[Station]:
        """Get station object by code (now searches by name)."""
        if not self.loaded:
            if not self.load_database():
                return None
        # Since we now use names as keys, find station by matching generated code
        for station_name, station in self.all_stations.items():
            if station.code == station_code.upper():
                return station
        return None
    
    
    def get_railway_lines_for_station(self, station_code: str) -> List[str]:
        """Get all railway lines that serve a given station."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        lines = []
        for line_name, railway_line in self.railway_lines.items():
            line_station_codes = [s.code for s in railway_line.stations]
            if station_code in line_station_codes:
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
    
    def get_journey_time_between_stations(self, from_code: str, to_code: str) -> Optional[int]:
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
                
                # Try direct journey time
                journey_key = f"{from_code}-{to_code}"
                if journey_key in journey_times:
                    return journey_times[journey_key]
                
                # Try reverse direction
                reverse_key = f"{to_code}-{from_code}"
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
        for station_name, station_code in self.station_name_to_code.items():
            station_name_lower = station_name.lower()
            
            # Check for matches (case insensitive)
            if query_lower in station_name_lower:
                # Add line context for disambiguation if station appears on multiple lines
                lines = self.get_railway_lines_for_station(station_code)
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
        for station_name, station_code in self.station_name_to_code.items():
            lines = self.get_railway_lines_for_station(station_code)
            if len(lines) > 1:
                # Add primary line context for disambiguation
                primary_line = lines[0]
                disambiguated_name = f"{station_name} ({primary_line})"
                stations_with_context.append(disambiguated_name)
            else:
                stations_with_context.append(station_name)
        
        return sorted(stations_with_context)
    
    def get_station_by_name(self, station_name: str) -> Optional[Station]:
        """Get station object by name."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        parsed_name = self.parse_station_name(station_name)
        return self.all_stations.get(parsed_name)
    
    def suggest_via_stations(self, from_station: str, to_station: str, limit: int = 10) -> List[str]:
        """Suggest via stations for a route."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        # Parse station names
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Get station codes
        from_code = self.get_station_code(from_parsed)
        to_code = self.get_station_code(to_parsed)
        
        if not from_code or not to_code:
            return []
        
        # Find routes and extract intermediate stations
        routes = self.dijkstra_shortest_path_with_service_patterns(
            from_code, to_code, max_routes=3, max_changes=2
        )
        
        via_stations = set()
        for route_codes, _ in routes:
            # Extract intermediate stations (exclude first and last)
            if len(route_codes) > 2:
                for station_code in route_codes[1:-1]:
                    station = self.get_station_by_code(station_code)
                    if station:
                        via_stations.add(station.name)
        
        return sorted(list(via_stations))[:limit]
    
    def find_route_between_stations(self, from_station: str, to_station: str,
                                  max_changes: int = 3, departure_time: Optional[str] = None) -> List[List[str]]:
        """Find routes between stations (UI compatibility method)."""
        print(f"🔍 find_route_between_stations called with: from='{from_station}', to='{to_station}', time='{departure_time}'")
        result = self.find_route_between_stations_with_service_patterns(
            from_station, to_station, max_changes, departure_time
        )
        print(f"🔍 find_route_between_stations returning {len(result) if result else 0} routes")
        return result
    
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
            
            # Get station codes
            current_code = self.get_station_code(current_parsed)
            next_code = self.get_station_code(next_parsed)
            
            if not current_code or not next_code:
                continue
            
            # Find common lines between current and next station
            current_lines = set(self.get_railway_lines_for_station(current_code))
            next_lines = set(self.get_railway_lines_for_station(next_code))
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
        
        # Get station codes
        from_code = self.get_station_code(from_station)
        to_code = self.get_station_code(to_station)
        
        if not from_code or not to_code:
            return None
        
        # Find common lines
        from_lines = set(self.get_railway_lines_for_station(from_code))
        to_lines = set(self.get_railway_lines_for_station(to_code))
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
        print(f"🔍 find_route_between_stations_with_service_patterns called with: from='{from_station}', to='{to_station}'")
        
        if not self.loaded:
            print("🔍 Database not loaded, loading now...")
            if not self.load_database():
                print("❌ Database loading failed")
                return []
        
        # Parse station names to remove line context
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        print(f"🔍 Parsed names: from='{from_parsed}', to='{to_parsed}'")
        
        # Check if stations exist in the database (using names as primary key now)
        from_station_obj = self.all_stations.get(from_parsed)
        to_station_obj = self.all_stations.get(to_parsed)
        
        print(f"🔍 Station objects: from_obj={from_station_obj is not None}, to_obj={to_station_obj is not None}")
        
        if not from_station_obj or not to_station_obj:
            print(f"❌ Station objects not found: from='{from_parsed}' -> {from_station_obj is not None}, to='{to_parsed}' -> {to_station_obj is not None}")
            return []
        
        # Get station codes for backward compatibility with existing methods
        from_code = from_station_obj.code
        to_code = to_station_obj.code
        print(f"🔍 Station codes: from_code='{from_code}', to_code='{to_code}'")
        
        # First try simple direct route check
        direct_route = self._find_simple_direct_route(from_code, to_code)
        if direct_route:
            return [direct_route]
        
        # Try service pattern aware Dijkstra with timeout protection
        try:
            route_results = self.dijkstra_shortest_path_with_service_patterns(
                from_code, to_code, max_routes=5, max_changes=max_changes, departure_time=departure_time
            )
            
            # Convert station codes back to names
            named_routes = []
            for route_codes, cost in route_results:
                named_route = []
                for station_code in route_codes:
                    station = self.get_station_by_code(station_code)
                    if station:
                        named_route.append(station.name)
                if named_route:
                    named_routes.append(named_route)
                    logger.info(f"Service-aware route: {' -> '.join(named_route)} (Cost: {cost:.2f})")
            
            if named_routes:
                return named_routes
                
        except Exception as e:
            logger.warning(f"Service pattern routing failed: {e}")
        
        # Fallback to simple routing if service pattern routing fails
        logger.info("Falling back to simple routing")
        return self._find_simple_routes(from_code, to_code, max_changes)
    
    def _find_simple_direct_route(self, from_code: str, to_code: str) -> Optional[List[str]]:
        """Find a simple direct route between two stations on the same line."""
        try:
            # Check if both stations are on the same line
            from_lines = set(self.get_railway_lines_for_station(from_code))
            to_lines = set(self.get_railway_lines_for_station(to_code))
            common_lines = from_lines.intersection(to_lines)
            
            if common_lines:
                # Use the first common line
                line_name = list(common_lines)[0]
                return self._find_direct_route_on_line(from_code, to_code, line_name)
            
            return None
        except Exception as e:
            logger.warning(f"Error in simple direct route: {e}")
            return None
    
    def _find_simple_routes(self, from_code: str, to_code: str, max_changes: int = 3) -> List[List[str]]:
        """Simple fallback routing without service patterns."""
        try:
            routes = []
            
            # Try direct route first
            direct_route = self._find_simple_direct_route(from_code, to_code)
            if direct_route:
                routes.append(direct_route)
                return routes
            
            # Try cross-network routing for complex journeys
            cross_network_routes = self._find_cross_network_routes(from_code, to_code, max_changes)
            if cross_network_routes:
                routes.extend(cross_network_routes)
                return routes
            
            # Try one-change routes through major interchange stations
            major_interchanges = ['WAT', 'VIC', 'LBG', 'PAD', 'KGX', 'EUS', 'LST', 'CLJ', 'BHM', 'MAN']
            
            from_lines = set(self.get_railway_lines_for_station(from_code))
            to_lines = set(self.get_railway_lines_for_station(to_code))
            
            for interchange_code in major_interchanges:
                if interchange_code == from_code or interchange_code == to_code:
                    continue
                
                interchange_lines = set(self.get_railway_lines_for_station(interchange_code))
                
                # Check if interchange connects both origin and destination lines
                if (from_lines.intersection(interchange_lines) and
                    to_lines.intersection(interchange_lines)):
                    
                    # Build route through interchange
                    first_leg = self._find_simple_direct_route(from_code, interchange_code)
                    second_leg = self._find_simple_direct_route(interchange_code, to_code)
                    
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
    
    def _find_cross_network_routes(self, from_code: str, to_code: str, max_changes: int = 3) -> List[List[str]]:
        """Find routes across different railway networks using dynamic interchange discovery."""
        try:
            routes = []
            
            # Dynamically identify interchange stations based on connectivity
            interchange_stations = self._identify_interchange_stations()
            
            # Score and rank interchange stations by importance
            ranked_interchanges = self._rank_interchange_stations(interchange_stations, from_code, to_code)
            
            logger.info(f"Attempting generalized cross-network routing from {from_code} to {to_code}")
            logger.info(f"Found {len(ranked_interchanges)} potential interchange stations")
            
            # Try single-interchange routes (2 legs)
            for interchange_code, score in ranked_interchanges[:20]:  # Top 20 interchanges
                if interchange_code == from_code or interchange_code == to_code:
                    continue
                
                # Try route: from -> interchange -> to
                first_leg = self._find_simple_direct_route(from_code, interchange_code)
                second_leg = self._find_simple_direct_route(interchange_code, to_code)
                
                if first_leg and second_leg:
                    # Combine legs, removing duplicate interchange station
                    combined_route = first_leg + second_leg[1:]
                    routes.append(combined_route)
                    logger.info(f"Found single-interchange route via {interchange_code} (score: {score:.2f}): {len(combined_route)} stations")
                    
                    if len(routes) >= 3:  # Limit single-interchange routes
                        break
            
            # If no single-interchange routes found and max_changes allows, try double-interchange routes
            if not routes and max_changes >= 2:
                logger.info("Trying double-interchange cross-network routing")
                routes.extend(self._find_multi_interchange_routes(from_code, to_code, ranked_interchanges, 2))
            
            # If still no routes and max_changes allows, try triple-interchange routes
            if not routes and max_changes >= 3:
                logger.info("Trying triple-interchange cross-network routing")
                routes.extend(self._find_multi_interchange_routes(from_code, to_code, ranked_interchanges, 3))
            
            return routes
            
        except Exception as e:
            logger.error(f"Error in generalized cross-network routing: {e}")
            return []
    
    def _find_regional_connection_routes(self, from_code: str, to_code: str) -> List[List[str]]:
        """Find routes using regional connections and operator transfers."""
        try:
            routes = []
            
            # Define regional connection patterns for common cross-network journeys
            regional_patterns = {
                # South to North patterns
                ('south', 'north'): [
                    ['WAT', 'CLJ', 'EUS'],  # Waterloo -> Clapham Junction -> Euston
                    ['WAT', 'CLJ', 'VIC', 'EUS'],  # Via Victoria
                    ['SOU', 'BSK', 'RDG', 'PAD'],  # Southampton -> Basingstoke -> Reading -> Paddington
                ],
                # South to Midlands patterns
                ('south', 'midlands'): [
                    ['WAT', 'CLJ', 'RDG', 'BHM'],  # Via Reading
                    ['SOU', 'BSK', 'RDG', 'BHM'],  # Southampton route
                ],
                # London to Manchester patterns
                ('london', 'manchester'): [
                    ['WAT', 'CLJ', 'EUS', 'MAN'],  # Waterloo -> Euston -> Manchester
                    ['PAD', 'RDG', 'BHM', 'MAN'],  # Paddington -> Reading -> Birmingham -> Manchester
                ],
            }
            
            # Determine journey type based on station locations
            from_region = self._classify_station_region(from_code)
            to_region = self._classify_station_region(to_code)
            
            logger.info(f"Regional routing: {from_region} to {to_region}")
            
            # Try patterns based on journey type
            journey_key = (from_region, to_region)
            if journey_key in regional_patterns:
                for pattern in regional_patterns[journey_key]:
                    route = self._build_route_through_pattern(from_code, to_code, pattern)
                    if route:
                        routes.append(route)
                        logger.info(f"Found regional pattern route: {len(route)} stations")
            
            # Try reverse patterns
            reverse_key = (to_region, from_region)
            if reverse_key in regional_patterns:
                for pattern in regional_patterns[reverse_key]:
                    # Reverse the pattern
                    reversed_pattern = list(reversed(pattern))
                    route = self._build_route_through_pattern(from_code, to_code, reversed_pattern)
                    if route:
                        routes.append(route)
                        logger.info(f"Found reverse regional pattern route: {len(route)} stations")
            
            return routes
            
        except Exception as e:
            logger.error(f"Error in regional connection routing: {e}")
            return []
    
    def _classify_station_region(self, station_code: str) -> str:
        """Classify a station into a regional category."""
        try:
            # Get lines serving this station
            lines = self.get_railway_lines_for_station(station_code)
            
            # London terminals and major London stations
            london_stations = ['WAT', 'VIC', 'LBG', 'PAD', 'KGX', 'EUS', 'LST', 'CLJ', 'OLD', 'MOG']
            if station_code in london_stations:
                return 'london'
            
            # Northern England
            northern_lines = ['Northern Rail', 'TransPennine Express', 'East Coast Main Line']
            northern_stations = ['MAN', 'LIV', 'LDS', 'SHF', 'NCL', 'YRK', 'HUL']
            if station_code in northern_stations or any(line in northern_lines for line in lines):
                return 'north'
            
            # Midlands
            midlands_stations = ['BHM', 'CCV', 'NUN', 'LTV', 'WVH']
            midlands_lines = ['West Midlands Railway', 'Cross Country']
            if station_code in midlands_stations or any(line in midlands_lines for line in lines):
                return 'midlands'
            
            # South/South West
            south_lines = ['South Western Main Line', 'Southern Network', 'Great Western Main Line']
            south_stations = ['SOU', 'WIN', 'BSK', 'WOK', 'FNB', 'FLE', 'BRI', 'RDG']
            if station_code in south_stations or any(line in south_lines for line in lines):
                return 'south'
            
            # Scotland
            scottish_lines = ['ScotRail Network', 'Caledonian Sleeper']
            scottish_stations = ['GLC', 'EDB', 'ABE', 'INV', 'STG']
            if station_code in scottish_stations or any(line in scottish_lines for line in lines):
                return 'scotland'
            
            # Wales
            welsh_lines = ['Transport for Wales', 'Heart of Wales Line']
            if any(line in welsh_lines for line in lines):
                return 'wales'
            
            # Default to south for unknown stations
            return 'south'
            
        except Exception as e:
            logger.warning(f"Error classifying station region for {station_code}: {e}")
            return 'unknown'
    
    def _build_route_through_pattern(self, from_code: str, to_code: str, pattern: List[str]) -> Optional[List[str]]:
        """Build a route through a specific pattern of interchange stations."""
        try:
            # Find the best entry and exit points in the pattern
            best_route = None
            min_total_length = float('inf')
            
            for entry_idx, entry_station in enumerate(pattern):
                for exit_idx, exit_station in enumerate(pattern):
                    if exit_idx <= entry_idx:
                        continue
                    
                    # Try to build route: from -> entry -> (pattern) -> exit -> to
                    first_leg = self._find_simple_direct_route(from_code, entry_station)
                    if not first_leg:
                        continue
                    
                    # Build middle section through pattern
                    middle_section = []
                    for i in range(entry_idx, exit_idx + 1):
                        if i == entry_idx:
                            middle_section.extend([entry_station])
                        else:
                            leg = self._find_simple_direct_route(pattern[i-1], pattern[i])
                            if leg:
                                middle_section.extend(leg[1:])  # Skip duplicate station
                            else:
                                middle_section = None
                                break
                    
                    if not middle_section:
                        continue
                    
                    final_leg = self._find_simple_direct_route(exit_station, to_code)
                    if not final_leg:
                        continue
                    
                    # Combine all legs
                    complete_route = first_leg + middle_section[1:] + final_leg[1:]
                    
                    if len(complete_route) < min_total_length:
                        min_total_length = len(complete_route)
                        best_route = complete_route
            
            return best_route
            
        except Exception as e:
            logger.warning(f"Error building route through pattern: {e}")
            return None
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

    
    def _identify_interchange_stations(self) -> Dict[str, Dict]:
        """Dynamically identify interchange stations based on line connectivity."""
        try:
            interchange_stations = {}
            
            # Analyze each station to determine its interchange potential
            for station_code, station in self.all_stations.items():
                lines_served = self.get_railway_lines_for_station(station_code)
                
                if len(lines_served) >= 2:  # Station serves multiple lines
                    # Calculate interchange score based on various factors
                    score = self._calculate_interchange_score(station_code, lines_served)
                    
                    interchange_stations[station_code] = {
                        'station': station,
                        'lines_served': lines_served,
                        'line_count': len(lines_served),
                        'interchange_score': score,
                        'is_terminal': self._is_terminal_station(station_code, lines_served),
                        'network_diversity': self._calculate_network_diversity(lines_served)
                    }
            
            logger.info(f"Identified {len(interchange_stations)} potential interchange stations")
            return interchange_stations
            
        except Exception as e:
            logger.error(f"Error identifying interchange stations: {e}")
            return {}
    
    def _calculate_interchange_score(self, station_code: str, lines_served: List[str]) -> float:
        """Calculate a score for how good an interchange station is."""
        try:
            score = 0.0
            
            # Base score from number of lines
            score += len(lines_served) * 10
            
            # Bonus for serving different types of networks
            network_types = set()
            for line_name in lines_served:
                network_type = self._classify_network_type(line_name)
                network_types.add(network_type)
            
            # Higher score for connecting different network types
            score += len(network_types) * 15
            
            # Bonus for major operators
            major_operators = {'National Rail', 'London Underground', 'London Overground', 'DLR'}
            for line_name in lines_served:
                railway_line = self.railway_lines.get(line_name)
                if railway_line and any(op in railway_line.operator for op in major_operators):
                    score += 5
            
            # Bonus for stations with "interchange" in their explicit interchange list
            station = self.all_stations.get(station_code)
            if station and station.interchange:
                score += len(station.interchange) * 3
            
            # Bonus for terminal stations (often major interchanges)
            if self._is_terminal_station(station_code, lines_served):
                score += 20
            
            return score
            
        except Exception as e:
            logger.warning(f"Error calculating interchange score for {station_code}: {e}")
            return 0.0
    
    def _classify_network_type(self, line_name: str) -> str:
        """Classify a railway line into a network type."""
        line_lower = line_name.lower()
        
        if any(keyword in line_lower for keyword in ['underground', 'tube', 'metro']):
            return 'underground'
        elif any(keyword in line_lower for keyword in ['overground', 'dlr']):
            return 'london_rail'
        elif any(keyword in line_lower for keyword in ['main line', 'express', 'sleeper']):
            return 'intercity'
        elif any(keyword in line_lower for keyword in ['railway', 'rail', 'network']):
            return 'regional'
        else:
            return 'suburban'
    
    def _is_terminal_station(self, station_code: str, lines_served: List[str]) -> bool:
        """Check if a station is a terminal station on any of its lines."""
        try:
            for line_name in lines_served:
                railway_line = self.railway_lines.get(line_name)
                if railway_line and railway_line.stations:
                    # Check if station is first or last on the line
                    station_codes = [s.code for s in railway_line.stations]
                    if station_code in [station_codes[0], station_codes[-1]]:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking terminal status for {station_code}: {e}")
            return False
    
    def _calculate_network_diversity(self, lines_served: List[str]) -> float:
        """Calculate how diverse the networks served by this station are."""
        try:
            network_types = set()
            operators = set()
            
            for line_name in lines_served:
                network_types.add(self._classify_network_type(line_name))
                railway_line = self.railway_lines.get(line_name)
                if railway_line:
                    operators.add(railway_line.operator)
            
            # Diversity score based on variety of network types and operators
            return len(network_types) * 2 + len(operators)
            
        except Exception as e:
            logger.warning(f"Error calculating network diversity: {e}")
            return 0.0
    
    def _rank_interchange_stations(self, interchange_stations: Dict[str, Dict], 
                                 from_code: str, to_code: str) -> List[Tuple[str, float]]:
        """Rank interchange stations by their suitability for this specific journey."""
        try:
            ranked = []
            
            from_lines = set(self.get_railway_lines_for_station(from_code))
            to_lines = set(self.get_railway_lines_for_station(to_code))
            
            for station_code, info in interchange_stations.items():
                station_lines = set(info['lines_served'])
                
                # Base score from interchange quality
                score = info['interchange_score']
                
                # Bonus if station connects to origin lines
                if from_lines.intersection(station_lines):
                    score += 30
                
                # Bonus if station connects to destination lines
                if to_lines.intersection(station_lines):
                    score += 30
                
                # Bonus if station connects both origin and destination networks
                if (from_lines.intersection(station_lines) and 
                    to_lines.intersection(station_lines)):
                    score += 50
                
                # Distance penalty (rough geographic scoring)
                distance_penalty = self._calculate_geographic_penalty(station_code, from_code, to_code)
                score -= distance_penalty
                
                ranked.append((station_code, score))
            
            # Sort by score (highest first)
            ranked.sort(key=lambda x: x[1], reverse=True)
            
            return ranked
            
        except Exception as e:
            logger.error(f"Error ranking interchange stations: {e}")
            return []
    
    def _calculate_geographic_penalty(self, interchange_code: str, from_code: str, to_code: str) -> float:
        """Calculate a penalty based on geographic detour."""
        try:
            interchange_station = self.all_stations.get(interchange_code)
            from_station = self.all_stations.get(from_code)
            to_station = self.all_stations.get(to_code)
            
            if not interchange_station or not from_station or not to_station:
                return 0.0
            
            # Calculate direct distance from origin to destination
            direct_distance = self.calculate_haversine_distance(
                from_station.coordinates, to_station.coordinates
            )
            
            # Calculate distance via interchange
            via_distance = (
                self.calculate_haversine_distance(from_station.coordinates, interchange_station.coordinates) +
                self.calculate_haversine_distance(interchange_station.coordinates, to_station.coordinates)
            )
            
            # Penalty based on detour ratio
            if direct_distance > 0:
                detour_ratio = via_distance / direct_distance
                return max(0, (detour_ratio - 1.0) * 20)  # Penalty for detours
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating geographic penalty: {e}")
            return 0.0
    
    def _find_multi_interchange_routes(self, from_code: str, to_code: str, 
                                     ranked_interchanges: List[Tuple[str, float]], 
                                     num_interchanges: int) -> List[List[str]]:
        """Find routes using multiple interchange stations."""
        try:
            routes = []
            
            if num_interchanges == 2:
                # Try combinations of top interchange stations
                top_interchanges = [code for code, score in ranked_interchanges[:15]]
                
                for i, interchange1 in enumerate(top_interchanges):
                    for interchange2 in top_interchanges[i+1:]:
                        if interchange1 == interchange2:
                            continue
                        
                        # Try route: from -> interchange1 -> interchange2 -> to
                        route = self._build_multi_leg_route(from_code, [interchange1, interchange2], to_code)
                        if route:
                            routes.append(route)
                            logger.info(f"Found double-interchange route via {interchange1} and {interchange2}: {len(route)} stations")
                            
                            if len(routes) >= 2:  # Limit routes
                                break
                    
                    if len(routes) >= 2:
                        break
            
            elif num_interchanges == 3:
                # Try combinations of top interchange stations for 3-interchange routes
                top_interchanges = [code for code, score in ranked_interchanges[:10]]
                
                for i, interchange1 in enumerate(top_interchanges):
                    for j, interchange2 in enumerate(top_interchanges):
                        if j <= i:
                            continue
                        for k, interchange3 in enumerate(top_interchanges):
                            if k <= j:
                                continue
                            
                            # Try route: from -> interchange1 -> interchange2 -> interchange3 -> to
                            route = self._build_multi_leg_route(from_code, [interchange1, interchange2, interchange3], to_code)
                            if route:
                                routes.append(route)
                                logger.info(f"Found triple-interchange route: {len(route)} stations")
                                
                                if len(routes) >= 1:  # Limit to 1 triple-interchange route
                                    return routes
            
            return routes
            
        except Exception as e:
            logger.error(f"Error finding multi-interchange routes: {e}")
            return []
    
    def _build_multi_leg_route(self, from_code: str, interchange_codes: List[str], to_code: str) -> Optional[List[str]]:
        """Build a route through multiple interchange stations."""
        try:
            # Build the complete route by connecting all segments
            all_stations = [from_code] + interchange_codes + [to_code]
            complete_route = []
            
            for i in range(len(all_stations) - 1):
                current_station = all_stations[i]
                next_station = all_stations[i + 1]
                
                # Find route segment between current and next station
                segment = self._find_simple_direct_route(current_station, next_station)
                if not segment:
                    return None  # Cannot complete this route
                
                # Add segment to complete route (avoid duplicating stations)
                if i == 0:
                    complete_route.extend(segment)
                else:
                    complete_route.extend(segment[1:])  # Skip first station (duplicate)
            
            return complete_route if len(complete_route) >= 2 else None
            
        except Exception as e:
            logger.warning(f"Error building multi-leg route: {e}")
            return None
