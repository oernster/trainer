"""
Station Database Manager for offline railway station data.
Author: Oliver Ernster

This module provides functionality to load and search UK railway station data
from local JSON files, eliminating the need for API calls.
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
    """Manages the offline railway station database."""
    
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
        try:
            # Load the railway lines index
            index_file = self.data_dir / "railway_lines_index.json"
            if not index_file.exists():
                logger.error(f"Railway lines index not found: {index_file}")
                return False
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Load each railway line
            for line_info in index_data['lines']:
                line_file = self.lines_dir / line_info['file']
                if not line_file.exists():
                    logger.warning(f"Railway line file not found: {line_file}")
                    continue
                
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                # Create Station objects
                stations = []
                for station_data in line_data['stations']:
                    station = Station(
                        name=station_data['name'],
                        code=station_data['code'],
                        coordinates=station_data['coordinates'],
                        zone=station_data.get('zone'),
                        interchange=station_data.get('interchange')
                    )
                    stations.append(station)
                    
                    # Add to global station mappings
                    self.all_stations[station.code] = station
                    self.station_name_to_code[station.name] = station.code
                
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
            logger.info(f"Loaded {len(self.railway_lines)} railway lines with {len(self.all_stations)} stations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load station database: {e}")
            return False
    
    def search_stations(self, query: str, limit: int = 10) -> List[str]:
        """Search for stations by name (case-insensitive) with railway line context for duplicates."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        
        # First collect all matching stations
        matching_stations = []
        for station_name in self.station_name_to_code.keys():
            if query_lower in station_name.lower():
                matching_stations.append(station_name)
        
        # Group stations by name to identify duplicates
        station_groups = {}
        for station_name in matching_stations:
            if station_name not in station_groups:
                station_groups[station_name] = []
            
            # Get the station code and find which lines it's on
            station_code = self.station_name_to_code[station_name]
            lines = self.get_railway_lines_for_station(station_code)
            station_groups[station_name].extend(lines)
        
        # Format results with line context for duplicates
        formatted_matches = []
        for station_name, lines in station_groups.items():
            unique_lines = list(set(lines))  # Remove duplicates
            if len(unique_lines) > 1:
                # Multiple lines serve this station - add line context
                for line in unique_lines:
                    formatted_name = f"{station_name} ({line})"
                    formatted_matches.append(formatted_name)
            else:
                # Single line or no duplicates - use station name as is
                formatted_matches.append(station_name)
            
            if len(formatted_matches) >= limit:
                break
        
        return sorted(formatted_matches)
    
    def get_station_code(self, station_name: str) -> Optional[str]:
        """Get station code for a station name."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        return self.station_name_to_code.get(station_name.strip())
    
    def get_station_by_code(self, station_code: str) -> Optional[Station]:
        """Get station object by code."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        return self.all_stations.get(station_code.upper())
    
    def get_station_by_name(self, station_name: str) -> Optional[Station]:
        """Get station object by name."""
        code = self.get_station_code(station_name)
        if code:
            return self.get_station_by_code(code)
        return None
    
    def get_stations_on_same_line(self, station_code: str) -> List[str]:
        """Get all stations on the same railway line(s) as the given station."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        station = self.get_station_by_code(station_code)
        if not station:
            return []
        
        same_line_stations = set()
        
        # Find all lines that contain this station
        for line_name, railway_line in self.railway_lines.items():
            line_station_codes = [s.code for s in railway_line.stations]
            if station_code in line_station_codes:
                # Add all stations from this line except the origin station
                for line_station in railway_line.stations:
                    if line_station.code != station_code:
                        same_line_stations.add(line_station.name)
        
        return sorted(list(same_line_stations))
    
    def get_all_station_names(self) -> List[str]:
        """Get all station names in the database."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        return sorted(list(self.station_name_to_code.keys()))
    
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
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the loaded database."""
        if not self.loaded:
            if not self.load_database():
                return {}
        
        return {
            "total_lines": len(self.railway_lines),
            "total_stations": len(self.all_stations),
            "stations_per_line": {
                line_name: len(railway_line.stations)
                for line_name, railway_line in self.railway_lines.items()
            }
        }
    
    def parse_station_name(self, formatted_name: str) -> str:
        """
        Parse a formatted station name to extract the original station name.
        
        Args:
            formatted_name: Station name that might include line context like "Station (Line)"
            
        Returns:
            Original station name without line context
        """
        # Check if the name has line context in parentheses
        if ' (' in formatted_name and formatted_name.endswith(')'):
            # Extract the station name before the parentheses
            return formatted_name.split(' (')[0]
        return formatted_name
    
    def get_all_stations_with_context(self) -> List[str]:
        """Get all station names with railway line context for duplicates."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        # Group all stations by name to identify duplicates
        station_groups = {}
        for station_name, station_code in self.station_name_to_code.items():
            if station_name not in station_groups:
                station_groups[station_name] = []
            
            # Get the lines for this station
            lines = self.get_railway_lines_for_station(station_code)
            station_groups[station_name].extend(lines)
        
        # Format results with line context for duplicates
        formatted_stations = []
        for station_name, lines in station_groups.items():
            unique_lines = list(set(lines))  # Remove duplicates
            if len(unique_lines) > 1:
                # Multiple lines serve this station - add line context
                for line in unique_lines:
                    formatted_name = f"{station_name} ({line})"
                    formatted_stations.append(formatted_name)
            else:
                # Single line - use station name as is
                formatted_stations.append(station_name)
        
        return sorted(formatted_stations)
    
    def calculate_haversine_distance(self, coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
        """
        Calculate the great circle distance between two points on Earth using the Haversine formula.
        
        Args:
            coord1: Dictionary with 'lat' and 'lng' keys for first coordinate
            coord2: Dictionary with 'lat' and 'lng' keys for second coordinate
            
        Returns:
            Distance in kilometers
        """
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
        """
        Get journey time between two stations from JSON data.
        
        Args:
            from_code: Origin station code
            to_code: Destination station code
            
        Returns:
            Journey time in minutes, or None if not found
        """
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
    
    def calculate_connection_cost(self, from_code: str, to_code: str, current_line: str,
                                next_line: str, num_changes: int) -> float:
        """
        Calculate the cost of traveling between two stations.
        
        Args:
            from_code: Origin station code
            to_code: Destination station code
            current_line: Current railway line
            next_line: Next railway line (for line change detection)
            num_changes: Current number of line changes
            
        Returns:
            Total cost (lower is better)
        """
        cost = 0.0
        
        # Get station objects
        from_station = self.get_station_by_code(from_code)
        to_station = self.get_station_by_code(to_code)
        
        if not from_station or not to_station:
            return float('inf')
        
        # Factor 1: Geographical distance (40% weight)
        distance_km = self.calculate_haversine_distance(
            from_station.coordinates, to_station.coordinates
        )
        cost += distance_km * 0.4
        
        # Factor 2: Journey time from JSON data (40% weight)
        journey_time = self.get_journey_time_between_stations(from_code, to_code)
        if journey_time:
            cost += journey_time * 0.4
        else:
            # Estimate based on distance if no journey time available
            estimated_time = distance_km * 1.5  # Rough estimate: 1.5 minutes per km
            cost += estimated_time * 0.4
        
        # Factor 3: Line changes (15% weight)
        if current_line != next_line:
            cost += 15 * 0.15  # 15-minute penalty for line changes
        
        # Factor 4: Major interchange bonus (5% weight)
        if to_station.interchange and len(to_station.interchange) >= 2:
            cost -= 5 * 0.05  # 5-minute bonus for major interchanges
        
        return cost
    
    def build_geographical_network(self) -> Dict[str, Dict]:
        """
        Build station network with geographical distances and journey times.
        
        Returns:
            Dictionary mapping station codes to their network information
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
                'connections': [],  # List of (connected_station_code, distance, time, line_name)
                'interchange_lines': station.interchange or [],
                'is_major_interchange': len(station.interchange or []) >= 2,
                'lines': self.get_railway_lines_for_station(station_code)
            }
        
        # Build connections based on railway lines
        for line_name, railway_line in self.railway_lines.items():
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
                    # Estimate based on distance
                    journey_time = max(2, int(distance * 1.5))  # Minimum 2 minutes
                
                # Add bidirectional connections
                network[current_station.code]['connections'].append(
                    (next_station.code, distance, journey_time, line_name)
                )
                network[next_station.code]['connections'].append(
                    (current_station.code, distance, journey_time, line_name)
                )
        
        logger.debug(f"Built geographical network with {len(network)} stations")
        return network
    
    def dijkstra_shortest_path(self, start_code: str, end_code: str, network: Dict, max_routes: int = 5, max_changes: int = 3, departure_time: Optional[str] = None) -> List[Tuple[List[str], float]]:
        """
        Find shortest paths using Dijkstra's algorithm with multiple criteria and time constraints.
        
        Args:
            start_code: Starting station code
            end_code: Destination station code
            network: Station network from build_geographical_network()
            max_routes: Maximum number of routes to return
            max_changes: Maximum number of line changes allowed
            departure_time: Departure time in HH:MM format (e.g., "14:30")
            
        Returns:
            List of tuples (route_as_station_codes, total_cost)
        """
        if start_code not in network or end_code not in network:
            return []
        
        # Priority queue: (total_cost, current_station, path, num_changes, current_line)
        pq = [(0.0, start_code, [start_code], 0, None)]
        
        # Track visited states: (station_code, num_changes) -> best_cost
        visited = {}
        
        # Store found routes
        routes = []
        
        while pq and len(routes) < max_routes:
            current_cost, current_station, path, num_changes, current_line = heapq.heappop(pq)
            
            # Create state key
            state_key = (current_station, num_changes)
            
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
            
            # Explore connections
            for next_station, distance, time, line_name in network[current_station]['connections']:
                if next_station in path:  # Avoid cycles
                    continue
                
                # Check if this connection is available at the requested time
                if departure_time and not self.is_station_served_at_time(next_station, departure_time):
                    continue
                
                # Calculate cost for this connection
                connection_cost = self.calculate_connection_cost(
                    current_station, next_station, current_line or line_name, line_name, num_changes
                )
                
                new_cost = current_cost + connection_cost
                new_path = path + [next_station]
                new_changes = num_changes + (1 if current_line and current_line != line_name else 0)
                
                heapq.heappush(pq, (new_cost, next_station, new_path, new_changes, line_name))
        
        return routes
    
    def score_route(self, route: List[str]) -> Dict[str, float]:
        """
        Score a route based on multiple criteria.
        
        Args:
            route: List of station codes representing the route
            
        Returns:
            Dictionary with scoring metrics
        """
        if len(route) < 2:
            return {'total_distance': 0, 'total_time': 0, 'num_changes': 0, 'geographical_efficiency': 0, 'overall_score': 0}
        
        total_distance = 0
        total_time = 0
        num_changes = 0
        current_line = None
        
        # Calculate metrics
        for i in range(len(route) - 1):
            from_code = route[i]
            to_code = route[i + 1]
            
            from_station = self.get_station_by_code(from_code)
            to_station = self.get_station_by_code(to_code)
            
            if from_station and to_station:
                # Distance
                distance = self.calculate_haversine_distance(
                    from_station.coordinates, to_station.coordinates
                )
                total_distance += distance
                
                # Time
                journey_time = self.get_journey_time_between_stations(from_code, to_code)
                if journey_time:
                    total_time += journey_time
                else:
                    total_time += distance * 1.5  # Estimate
                
                # Line changes
                from_lines = self.get_railway_lines_for_station(from_code)
                to_lines = self.get_railway_lines_for_station(to_code)
                common_lines = set(from_lines) & set(to_lines)
                
                if current_line and current_line not in common_lines:
                    num_changes += 1
                
                if common_lines:
                    current_line = list(common_lines)[0]
        
        # Calculate geographical efficiency
        if len(route) >= 2:
            start_station = self.get_station_by_code(route[0])
            end_station = self.get_station_by_code(route[-1])
            if start_station and end_station:
                direct_distance = self.calculate_haversine_distance(
                    start_station.coordinates, end_station.coordinates
                )
                geographical_efficiency = direct_distance / total_distance if total_distance > 0 else 0
            else:
                geographical_efficiency = 0
        else:
            geographical_efficiency = 0
        
        # Overall score (lower is better)
        overall_score = total_time + (num_changes * 15) + (total_distance * 0.5) - (geographical_efficiency * 20)
        
        return {
            'total_distance': total_distance,
            'total_time': total_time,
            'num_changes': num_changes,
            'geographical_efficiency': geographical_efficiency,
            'overall_score': overall_score
        }
    
    def validate_route_geography(self, route: List[str], from_station: str, to_station: str) -> bool:
        """
        Validate that route doesn't make illogical geographical detours.
        
        Args:
            route: List of station codes
            from_station: Origin station name
            to_station: Destination station name
            
        Returns:
            True if route is geographically reasonable
        """
        if len(route) < 2:
            return True
        
        # Get coordinates for start and end
        start_station = self.get_station_by_code(route[0])
        end_station = self.get_station_by_code(route[-1])
        
        if not start_station or not end_station:
            return False
        
        start_coords = start_station.coordinates
        end_coords = end_station.coordinates
        
        # Calculate direct distance
        direct_distance = self.calculate_haversine_distance(start_coords, end_coords)
        
        # Calculate total route distance
        total_distance = 0
        for i in range(len(route) - 1):
            from_code = route[i]
            to_code = route[i + 1]
            
            from_st = self.get_station_by_code(from_code)
            to_st = self.get_station_by_code(to_code)
            
            if from_st and to_st:
                distance = self.calculate_haversine_distance(
                    from_st.coordinates, to_st.coordinates
                )
                total_distance += distance
        
        # Route is valid if it's not more than 50% longer than direct route
        efficiency = direct_distance / total_distance if total_distance > 0 else 0
        
        # Also check for major detours (going significantly in wrong direction)
        if len(route) > 2:
            # Check if any intermediate station is too far from the direct path
            for i in range(1, len(route) - 1):
                intermediate_station = self.get_station_by_code(route[i])
                if intermediate_station:
                    # Distance from start to intermediate
                    start_to_intermediate = self.calculate_haversine_distance(
                        start_coords, intermediate_station.coordinates
                    )
                    # Distance from intermediate to end
                    intermediate_to_end = self.calculate_haversine_distance(
                        intermediate_station.coordinates, end_coords
                    )
                    
                    # If intermediate station makes the journey more than 80% longer, it's a detour
                    if (start_to_intermediate + intermediate_to_end) > (direct_distance * 1.8):
                        logger.warning(f"Route validation failed: major detour detected via {intermediate_station.name}")
                        return False
        
        is_valid = efficiency > 0.6  # Route must be at least 60% efficient
        if not is_valid:
            logger.warning(f"Route validation failed: efficiency {efficiency:.2f} < 0.6")
        
        return is_valid
    
    def find_route_between_stations(self, from_station: str, to_station: str, max_changes: int = 3, departure_time: Optional[str] = None) -> List[List[str]]:
        """
        Find possible routes between two stations, including via stations, with time constraints.
        
        Args:
            from_station: Starting station name (may include line context)
            to_station: Destination station name (may include line context)
            max_changes: Maximum number of line changes allowed
            departure_time: Departure time in HH:MM format (e.g., "14:30")
            
        Returns:
            List of routes, where each route is a list of station names
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
        
        # Build geographical network
        network = self.build_geographical_network()
        if not network:
            logger.warning("Failed to build geographical network, falling back to BFS")
            routes = self._find_routes_bfs(from_code, to_code, max_changes, departure_time)
        else:
            # Use optimized Dijkstra's algorithm
            time_info = f" at {departure_time}" if departure_time else ""
            logger.debug(f"Finding optimal routes from {from_parsed} to {to_parsed}{time_info} using Dijkstra's algorithm")
            route_results = self.dijkstra_shortest_path(from_code, to_code, network, max_routes=5, max_changes=max_changes, departure_time=departure_time)
            
            # Extract routes and validate them
            routes = []
            for route_codes, cost in route_results:
                # Validate route geography
                if self.validate_route_geography(route_codes, from_parsed, to_parsed):
                    routes.append(route_codes)
                    logger.debug(f"Valid route found with cost {cost:.2f}: {len(route_codes)} stations")
                else:
                    logger.warning(f"Route rejected due to geographical inefficiency: {len(route_codes)} stations")
            
            # If no valid routes found with Dijkstra, fall back to BFS
            if not routes:
                logger.warning("No valid routes found with Dijkstra, falling back to BFS")
                routes = self._find_routes_bfs(from_code, to_code, max_changes, departure_time)
        
        # Convert station codes back to names
        named_routes = []
        for route in routes:
            named_route = []
            for station_code in route:
                station = self.get_station_by_code(station_code)
                if station:
                    named_route.append(station.name)
            if named_route:
                # Score the route for logging
                score = self.score_route(route)
                logger.info(f"Route: {' -> '.join(named_route[:3])}{'...' if len(named_route) > 3 else ''} "
                          f"(Distance: {score['total_distance']:.1f}km, Time: {score['total_time']:.0f}min, "
                          f"Changes: {score['num_changes']}, Efficiency: {score['geographical_efficiency']:.2f})")
                named_routes.append(named_route)
        
        return named_routes
    
    def _find_routes_bfs(self, from_code: str, to_code: str, max_changes: int, departure_time: Optional[str] = None) -> List[List[str]]:
        """
        Use breadth-first search to find routes between stations with geographical awareness and time constraints.
        
        Args:
            from_code: Starting station code
            to_code: Destination station code
            max_changes: Maximum number of line changes
            departure_time: Departure time in HH:MM format (e.g., "14:30")
            
        Returns:
            List of routes as station code lists
        """
        from collections import deque
        
        # Queue contains: (current_station, route_so_far, changes_used, current_line)
        queue = deque()
        
        # Start with each line that serves the origin station
        for line_name in self.get_railway_lines_for_station(from_code):
            queue.append((from_code, [from_code], 0, line_name))
        
        visited = set()
        routes = []
        
        while queue and len(routes) < 3:  # Limit to 3 routes for performance
            current_station, route, changes, current_line = queue.popleft()
            
            # Skip if we've been here with the same or fewer changes
            state = (current_station, changes, current_line)
            if state in visited:
                continue
            visited.add(state)
            
            # Found destination
            if current_station == to_code:
                routes.append(route)
                continue
            
            # Don't exceed max changes
            if changes >= max_changes:
                continue
            
            # Get the railway line
            if current_line not in self.railway_lines:
                continue
                
            railway_line = self.railway_lines[current_line]
            
            # Find current station's position on this line
            current_position = None
            for i, station in enumerate(railway_line.stations):
                if station.code == current_station:
                    current_position = i
                    break
            
            if current_position is None:
                continue
            
            # Explore stations in both directions on this line, but prioritize geographical direction
            stations_to_explore = []
            
            # Add adjacent stations first (more likely to be geographically correct)
            if current_position > 0:  # Previous station
                stations_to_explore.append((current_position - 1, railway_line.stations[current_position - 1]))
            if current_position < len(railway_line.stations) - 1:  # Next station
                stations_to_explore.append((current_position + 1, railway_line.stations[current_position + 1]))
            
            # Then add other stations on the line, but with distance penalty
            for i, station in enumerate(railway_line.stations):
                if i != current_position and station.code not in route:
                    distance = abs(i - current_position)
                    if distance <= 5:  # Only consider stations within 5 positions
                        stations_to_explore.append((i, station))
            
            # Sort by distance from current position (geographical order)
            stations_to_explore.sort(key=lambda x: abs(x[0] - current_position))
            
            # Explore the stations
            for pos, station in stations_to_explore[:10]:  # Limit to 10 nearest stations
                if station.code not in route:
                    # Check if this station is served at the requested time
                    if departure_time and not self.is_station_served_at_time(station.code, departure_time):
                        continue
                    
                    new_route = route + [station.code]
                    
                    # Continue on same line
                    queue.append((station.code, new_route, changes, current_line))
                    
                    # Check for line changes at interchange stations
                    if changes < max_changes:
                        station_lines = self.get_railway_lines_for_station(station.code)
                        for other_line in station_lines:
                            if other_line != current_line:
                                queue.append((station.code, new_route, changes + 1, other_line))
        
        return routes
    
    def get_interchange_stations(self) -> List[str]:
        """Get all stations that serve multiple railway lines (interchange stations)."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        interchange_stations = []
        for station_name, station_code in self.station_name_to_code.items():
            lines = self.get_railway_lines_for_station(station_code)
            if len(lines) > 1:
                interchange_stations.append(station_name)
        
        return sorted(interchange_stations)
    
    def suggest_via_stations(self, from_station: str, to_station: str) -> List[str]:
        """
        Suggest intermediate interchange stations for a journey with intelligent routing.
        Only returns stations that serve multiple railway lines (interchange stations).
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            List of suggested via interchange stations only
        """
        # Parse station names
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Handle common London routing patterns first
        london_routing = self._get_london_routing_suggestions(from_parsed, to_parsed)
        if london_routing:
            # Filter London routing suggestions to only include interchange stations
            interchange_stations = set(self.get_interchange_stations())
            filtered_london = [station for station in london_routing if station in interchange_stations]
            return filtered_london
        
        # Find routes and extract intermediate stations
        routes = self.find_route_between_stations(from_station, to_station, max_changes=2)
        
        # Get all interchange stations for filtering
        interchange_stations = set(self.get_interchange_stations())
        
        via_suggestions = set()
        for route in routes:
            # Add intermediate stations (excluding start and end), but only if they are interchanges
            if len(route) > 2:
                for station in route[1:-1]:
                    if station in interchange_stations:
                        via_suggestions.add(station)
        
        # If no good interchange routes found, add logical interchange stations
        if not via_suggestions:
            logical_interchanges = self._get_logical_interchanges(from_parsed, to_parsed)
            # Filter logical interchanges to only include actual interchange stations
            for station in logical_interchanges:
                if station in interchange_stations:
                    via_suggestions.add(station)
        
        return sorted(list(via_suggestions))
    
    def _get_london_routing_suggestions(self, from_station: str, to_station: str) -> List[str]:
        """Get routing suggestions for journeys involving London terminals."""
        # Define London terminal groups and their typical interchange stations
        london_terminals = {
            "London Waterloo": "south_western",
            "London Victoria": "southern",
            "London Bridge": "southern",
            "London Paddington": "great_western",
            "London Kings Cross": "east_coast",
            "London St Pancras": "midland",
            "London Euston": "west_coast",
            "London Liverpool Street": "great_eastern"
        }
        
        # Check if destination is a London terminal
        if to_station in london_terminals:
            # Get the origin station's line
            from_code = self.get_station_code(from_station)
            if from_code:
                from_lines = self.get_railway_lines_for_station(from_code)
                
                # Fleet to London terminals routing
                if from_station == "Fleet":
                    if to_station in ["London St Pancras", "London Kings Cross", "London Euston"]:
                        # Fleet is on South Western Main Line, need to interchange
                        return ["Clapham Junction"]
                    elif to_station == "London Waterloo":
                        # Direct route on South Western Main Line
                        return []
                
                # Other South Western Main Line stations to London terminals
                if "South Western Main Line" in from_lines:
                    if to_station in ["London St Pancras", "London Kings Cross", "London Euston", "London Liverpool Street"]:
                        return ["Clapham Junction"]
        
        # Check if origin is a London terminal
        if from_station in london_terminals:
            to_code = self.get_station_code(to_station)
            if to_code:
                to_lines = self.get_railway_lines_for_station(to_code)
                
                # London terminals to South Western Main Line stations
                if "South Western Main Line" in to_lines:
                    if from_station in ["London St Pancras", "London Kings Cross", "London Euston", "London Liverpool Street"]:
                        return ["Clapham Junction"]
        
        return []
    
    def _get_logical_interchanges(self, from_station: str, to_station: str) -> List[str]:
        """Get logical interchange stations based on geographical knowledge."""
        logical_routes = {
            # Fleet routing patterns
            ("Fleet", "Manchester"): ["Reading", "Birmingham New Street"],
            ("Fleet", "Birmingham"): ["Reading"],
            ("Fleet", "Bristol"): ["Reading"],
            ("Fleet", "Leeds"): ["Reading", "Birmingham New Street"],
            ("Fleet", "York"): ["Reading", "Birmingham New Street"],
            
            # London to major cities
            ("London Waterloo", "Manchester"): ["Birmingham New Street"],
            ("London Paddington", "Manchester"): ["Birmingham New Street"],
            ("London St Pancras", "Manchester"): ["Birmingham New Street"],
            
            # Cross-country patterns
            ("Birmingham", "Brighton"): ["Clapham Junction"],
            ("Manchester", "Brighton"): ["Birmingham New Street", "Clapham Junction"],
        }
        
        # Try exact match
        route_key = (from_station, to_station)
        if route_key in logical_routes:
            return logical_routes[route_key]
        
        # Try reverse direction
        reverse_key = (to_station, from_station)
        if reverse_key in logical_routes:
            return logical_routes[reverse_key]
        
        # Default major interchanges
        return ["Clapham Junction", "Birmingham New Street", "Reading"]
    
    def get_operator_for_segment(self, from_station: str, to_station: str) -> Optional[str]:
        """
        Get the railway operator for a segment between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            Railway operator name, or None if no direct connection found
        """
        if not self.loaded:
            if not self.load_database():
                return None
        
        # Parse station names to remove line context
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Get station codes
        from_code = self.get_station_code(from_parsed)
        to_code = self.get_station_code(to_parsed)
        
        if not from_code or not to_code:
            return None
        
        # Find a railway line that contains both stations
        for line_name, railway_line in self.railway_lines.items():
            line_station_codes = [s.code for s in railway_line.stations]
            if from_code in line_station_codes and to_code in line_station_codes:
                return railway_line.operator
        
        return None
    
    def identify_train_changes(self, route_path: List[str]) -> List[str]:
        """
        Identify stations where train operator changes occur (actual train change points).
        
        Args:
            route_path: List of station names representing the complete route
            
        Returns:
            List of station names where train changes occur (via stations)
        """
        if not self.loaded:
            if not self.load_database():
                return []
        
        if len(route_path) < 3:  # Need at least 3 stations to have a via station
            return []
        
        via_stations = []
        
        for i in range(1, len(route_path) - 1):  # Exclude start/end stations
            current_station = route_path[i]
            prev_station = route_path[i-1]
            next_station = route_path[i+1]
            
            # Get operators for the segments before and after this station
            prev_operator = self.get_operator_for_segment(prev_station, current_station)
            next_operator = self.get_operator_for_segment(current_station, next_station)
            
            # If operators are different, this is a train change point
            if prev_operator and next_operator and prev_operator != next_operator:
                via_stations.append(current_station)
                logger.debug(f"Train change detected at {current_station}: {prev_operator} -> {next_operator}")
        
        return via_stations
    
    def get_route_with_operators(self, route_path: List[str]) -> List[Dict[str, str]]:
        """
        Get route information with operator details for each segment.
        
        Args:
            route_path: List of station names representing the route
            
        Returns:
            List of dictionaries with segment information including operators
        """
        if not self.loaded:
            if not self.load_database():
                return []
        
        if len(route_path) < 2:
            return []
        
        route_segments = []
        
        for i in range(len(route_path) - 1):
            from_station = route_path[i]
            to_station = route_path[i + 1]
            operator = self.get_operator_for_segment(from_station, to_station)
            
            route_segments.append({
                'from_station': from_station,
                'to_station': to_station,
                'operator': operator or 'Unknown',
                'segment_index': i
            })
        
        return route_segments
    
    def get_time_period(self, time_str: str) -> str:
        """
        Determine the time period (morning, afternoon, evening, night) for a given time.
        
        Args:
            time_str: Time in HH:MM format (e.g., "14:30")
            
        Returns:
            Time period string: "morning", "afternoon", "evening", or "night"
        """
        try:
            hour = int(time_str.split(':')[0])
            
            if 5 <= hour < 12:
                return "morning"
            elif 12 <= hour < 17:
                return "afternoon"
            elif 17 <= hour <= 23:
                return "evening"
            else:
                return "night"
        except (ValueError, IndexError):
            logger.warning(f"Invalid time format: {time_str}, defaulting to morning")
            return "morning"

    def is_station_served_at_time(self, station_code: str, departure_time: str) -> bool:
        """
        Check if a station is served at a specific time.
        
        Args:
            station_code: Station code to check
            departure_time: Time in HH:MM format (e.g., "14:30")
            
        Returns:
            True if station is served at that time, False otherwise
        """
        if not departure_time:
            return True  # If no time specified, assume all stations are available
        
        time_period = self.get_time_period(departure_time)
        
        # Find the station in the JSON data by loading each line file
        for line_name, railway_line in self.railway_lines.items():
            line_file = self.lines_dir / railway_line.file
            if not line_file.exists():
                continue
                
            try:
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                if 'stations' in line_data:
                    for station in line_data['stations']:
                        if station.get('code') == station_code:
                            # Check if station has service times defined
                            if 'times' in station:
                                times_for_period = station['times'].get(time_period, [])
                                # If the list is empty, no service during this period
                                return len(times_for_period) > 0
                            else:
                                # If no times defined, assume always available
                                return True
            except Exception as e:
                logger.warning(f"Error reading line data from {line_file}: {e}")
                continue
        
        # If station not found in any line data, assume available
        logger.warning(f"Station {station_code} not found in line data, assuming available")
        return True

    def get_next_departure_time(self, station_code: str, departure_time: str) -> Optional[str]:
        """
        Get the next available departure time for a station after the given time.
        
        Args:
            station_code: Station code
            departure_time: Current time in HH:MM format
            
        Returns:
            Next departure time as string, or None if no service
        """
        if not departure_time:
            return None
        
        time_period = self.get_time_period(departure_time)
        
        # Find the station in the JSON data by loading each line file
        for line_name, railway_line in self.railway_lines.items():
            line_file = self.lines_dir / railway_line.file
            if not line_file.exists():
                continue
                
            try:
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                if 'stations' in line_data:
                    for station in line_data['stations']:
                        if station.get('code') == station_code:
                            if 'times' in station:
                                times_for_period = station['times'].get(time_period, [])
                                if times_for_period:
                                    # Find the next departure after the given time
                                    departure_hour, departure_minute = map(int, departure_time.split(':'))
                                    departure_minutes = departure_hour * 60 + departure_minute
                                    
                                    for time_str in times_for_period:
                                        time_hour, time_minute = map(int, time_str.split(':'))
                                        time_minutes = time_hour * 60 + time_minute
                                        
                                        if time_minutes >= departure_minutes:
                                            return time_str
                                    
                                    # If no time found in current period, return first time of next period
                                    next_periods = {
                                        "morning": "afternoon",
                                        "afternoon": "evening",
                                        "evening": "night",
                                        "night": "morning"
                                    }
                                    next_period = next_periods.get(time_period)
                                    if next_period and next_period in station['times']:
                                        next_times = station['times'][next_period]
                                        if next_times:
                                            return next_times[0]
                            break
            except Exception as e:
                logger.warning(f"Error reading line data from {line_file}: {e}")
                continue
        
        return None

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
    
    def is_direct_service_available(self, from_code: str, to_code: str, 
                                  pattern_name: str, line_name: str) -> bool:
        """Check if a direct service exists between two stations for a given pattern."""
        if not self.loaded:
            if not self.load_database():
                return False
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return False
        
        pattern = service_patterns.get_pattern(pattern_name)
        if not pattern:
            return False
        
        # Get all station codes for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return False
        
        all_station_codes = [station.code for station in railway_line.stations]
        
        return (pattern.serves_station(from_code, all_station_codes) and 
                pattern.serves_station(to_code, all_station_codes))
    
    def get_available_service_patterns_for_stations(self, from_code: str, to_code: str, 
                                                  line_name: str) -> List[ServicePattern]:
        """Get all service patterns that serve both stations, sorted by priority (fastest first)."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return []
        
        # Get all station codes for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return []
        
        all_station_codes = [station.code for station in railway_line.stations]
        
        return service_patterns.get_available_patterns_for_stations(from_code, to_code, all_station_codes)
    
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
                'connections': [],  # List of (connected_station_code, distance, time, line_name, service_pattern)
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
                all_station_codes = [s.code for s in railway_line.stations]
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
                                        if time_minutes >= departure_minutes:
                                            return time_str
                                    
                                    # If no time found in current period, return first time of next period
                                    next_periods = {
                                        "morning": "afternoon",
                                        "afternoon": "evening",
                                        "evening": "night",
                                        "night": "morning"
                                    }
                                    next_period = next_periods.get(time_period)
                                    if next_period and next_period in station['times']:
                                        next_times = station['times'][next_period]
                                        if next_times:
                                            return next_times[0]
                            break
            except Exception as e:
                logger.warning(f"Error reading line data from {line_file}: {e}")
                continue
        
        return None