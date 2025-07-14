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
        self.all_stations: Dict[str, Station] = {}  # code -> Station
        self.station_name_to_code: Dict[str, str] = {}  # name -> code
        self.loaded = False
    
    def load_database(self) -> bool:
        """Load the railway station database from JSON files."""
        print("🔄 FORCE RELOADING DATABASE - Clearing all existing data...")
        
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
            
            # Load each railway line
            print(f"🔍 Loading {len(index_data['lines'])} railway lines...")
            for i, line_info in enumerate(index_data['lines']):
                line_name = line_info.get('name', 'Unknown')
                line_file_name = line_info.get('file', 'unknown.json')
                line_file = self.lines_dir / line_file_name
                
                print(f"🔍 [{i+1}/{len(index_data['lines'])}] Loading line: {line_name}")
                print(f"    File: {line_file}")
                print(f"    File exists: {line_file.exists()}")
                
                if not line_file.exists():
                    print(f"❌ Railway line file not found: {line_file}")
                    logger.warning(f"Railway line file not found: {line_file}")
                    continue
                
                try:
                    with open(line_file, 'r', encoding='utf-8') as f:
                        line_data = json.load(f)
                    print(f"✅ JSON loaded successfully")
                except Exception as json_error:
                    print(f"❌ JSON loading failed: {json_error}")
                    continue
                
                # Create Station objects
                stations = []
                stations_data = line_data.get('stations', [])
                print(f"    Processing {len(stations_data)} stations...")
                
                for j, station_data in enumerate(stations_data):
                    try:
                        station_name = station_data.get('name', 'Unknown')
                        station_code = station_data.get('code', 'UNK')
                        
                        station = Station(
                            name=station_name,
                            code=station_code,
                            coordinates=station_data.get('coordinates', {}),
                            zone=station_data.get('zone'),
                            interchange=station_data.get('interchange')
                        )
                        stations.append(station)
                        
                        # Add to global station mappings (ensure consistent uppercase for codes)
                        station_code_upper = station.code.upper()
                        self.all_stations[station_code_upper] = station
                        self.station_name_to_code[station.name] = station_code_upper
                        
                        # Debug: Log station loading for key stations
                        if ('farnborough' in station.name.lower() or
                            'waterloo' in station.name.lower() or
                            j < 3 or  # First 3 stations
                            j >= len(stations_data) - 3):  # Last 3 stations
                            print(f"      [{j+1}] '{station.name}' -> '{station_code_upper}'")
                            
                    except Exception as station_error:
                        print(f"❌ Error loading station {j+1}: {station_error}")
                        continue
                
                print(f"    ✅ Loaded {len(stations)} stations for {line_name}")
                
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
            print(f"🎉 DATABASE LOADING COMPLETE:")
            print(f"    ✅ Loaded {len(self.railway_lines)} railway lines")
            print(f"    ✅ Loaded {len(self.all_stations)} total stations")
            print(f"    ✅ Created {len(self.station_name_to_code)} name-to-code mappings")
            
            # Debug: Check if our key stations are loaded
            key_stations = ["Farnborough (Main)", "London Waterloo", "Fleet", "Woking"]
            print(f"🔍 Checking key stations:")
            for station_name in key_stations:
                code = self.station_name_to_code.get(station_name)
                if code:
                    print(f"    ✅ '{station_name}' -> '{code}'")
                else:
                    print(f"    ❌ '{station_name}' -> NOT FOUND")
            
            # Debug: Show some sample station names
            sample_names = list(self.station_name_to_code.keys())[:10]
            print(f"🔍 Sample station names: {sample_names}")
            
            logger.info(f"Loaded {len(self.railway_lines)} railway lines with {len(self.all_stations)} stations")
            
            # Final verification test
            print(f"🧪 FINAL VERIFICATION TEST:")
            test_result = self._test_database_integrity()
            if not test_result:
                print(f"❌ Database integrity test FAILED")
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
            print(f"🔍 Database not loaded, loading now...")
            if not self.load_database():
                print(f"❌ Database loading failed")
                return None
            print(f"✅ Database loaded successfully")
        
        station_name_clean = station_name.strip()
        print(f"🔍 Looking up station: '{station_name_clean}'")
        print(f"🔍 Total stations in name mapping: {len(self.station_name_to_code)}")
        
        # Debug: Show some sample station names for comparison
        sample_names = list(self.station_name_to_code.keys())[:10]
        print(f"🔍 Sample station names: {sample_names}")
        
        # Check for exact match
        code = self.station_name_to_code.get(station_name_clean)
        if code:
            result_code = code.upper() if code else None
            print(f"✅ Found exact match: '{station_name_clean}' -> '{result_code}'")
            return result_code
        
        # Debug: Check for case-insensitive matches
        print(f"❌ No exact match found for '{station_name_clean}'")
        case_insensitive_matches = []
        for name, stored_code in self.station_name_to_code.items():
            if name.lower() == station_name_clean.lower():
                case_insensitive_matches.append((name, stored_code))
        
        if case_insensitive_matches:
            print(f"🔍 Case-insensitive matches found: {case_insensitive_matches}")
            # Use the first case-insensitive match
            _, code = case_insensitive_matches[0]
            result_code = code.upper() if code else None
            print(f"✅ Using case-insensitive match: '{station_name_clean}' -> '{result_code}'")
            return result_code
        
        # Debug: Check for partial matches
        partial_matches = []
        for name in self.station_name_to_code.keys():
            if station_name_clean.lower() in name.lower() or name.lower() in station_name_clean.lower():
                partial_matches.append(name)
        
        if partial_matches:
            print(f"🔍 Partial matches found: {partial_matches[:5]}")  # Show first 5
        else:
            print(f"❌ No partial matches found")
        
        print(f"❌ Station '{station_name_clean}' not found in database")
        return None
    
    def get_station_by_code(self, station_code: str) -> Optional[Station]:
        """Get station object by code."""
        if not self.loaded:
            if not self.load_database():
                return None
        return self.all_stations.get(station_code.upper())
    
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
        
        # Remove line context in parentheses
        if ' (' in station_name:
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
        station_code = self.get_station_code(parsed_name)
        if station_code:
            return self.get_station_by_code(station_code)
        return None
    
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
        if not self.loaded:
            if not self.load_database():
                return []
        
        # Parse station names to remove line context
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Get station codes
        from_code = self.get_station_code(from_parsed)
        to_code = self.get_station_code(to_parsed)
        
        if not from_code or not to_code:
            return []
        
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
    def _test_database_integrity(self) -> bool:
        """Test database integrity by checking key stations."""
        try:
            print("    Testing key station lookups...")
            
            # Test key stations that should definitely exist
            test_stations = [
                ("Farnborough (Main)", "FNB"),
                ("London Waterloo", "WAT"),
                ("Fleet", "FLE"),
                ("Woking", "WOK"),
                ("Clapham Junction", "CLJ")
            ]
            
            all_passed = True
            for station_name, expected_code in test_stations:
                # Test name-to-code lookup
                found_code = self.station_name_to_code.get(station_name)
                if found_code == expected_code:
                    print(f"    ✅ '{station_name}' -> '{found_code}'")
                else:
                    print(f"    ❌ '{station_name}' -> Expected '{expected_code}', got '{found_code}'")
                    all_passed = False
                
                # Test code-to-station lookup
                if found_code:
                    station_obj = self.all_stations.get(found_code)
                    if station_obj and station_obj.name == station_name:
                        print(f"    ✅ Code '{found_code}' -> Station object OK")
                    else:
                        print(f"    ❌ Code '{found_code}' -> Station object FAILED")
                        all_passed = False
            
            if all_passed:
                print("    ✅ All database integrity tests PASSED")
            else:
                print("    ❌ Some database integrity tests FAILED")
            
            return all_passed
            
        except Exception as e:
            print(f"    ❌ Database integrity test error: {e}")
            return False
