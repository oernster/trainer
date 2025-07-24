"""
Pathfinding Algorithm

Handles Dijkstra's shortest path algorithm and route finding logic.
"""

import logging
import heapq
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path
import json

from ..interfaces.i_data_repository import IDataRepository


@dataclass
class PathNode:
    """Node for pathfinding algorithms."""
    station: str
    distance: float
    time: int
    changes: int
    path: List[str]
    lines_used: List[str]
    
    def __lt__(self, other):
        # For priority queue - prioritize by time, then changes, then distance
        if self.time != other.time:
            return self.time < other.time
        if self.changes != other.changes:
            return self.changes < other.changes
        return self.distance < other.distance


class PathfindingAlgorithm:
    """Handles pathfinding algorithms for route calculation."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the pathfinding algorithm.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
    
    def find_station_in_graph(self, station_name: str, graph: Dict) -> Optional[str]:
        """
        Find a station in the graph, handling London variants.
        Returns the actual graph key if found, or None if not found.
        """
        # Direct lookup first (most efficient)
        if station_name in graph:
            return station_name
            
        # Try with different case
        for graph_station in graph:
            if graph_station.lower() == station_name.lower():
                self.logger.info(f"Graph lookup (case): '{station_name}' → '{graph_station}'")
                return graph_station
                
        # Handle London prefix variants
        station_lower = station_name.lower()
        if station_lower.startswith("london "):
            # Try without London prefix
            base_name = station_lower[7:]  # Remove "london "
            for graph_station in graph:
                if graph_station.lower() == base_name:
                    self.logger.info(f"Graph lookup (removed London): '{station_name}' → '{graph_station}'")
                    return graph_station
        else:
            # Try with London prefix
            london_name = "london " + station_lower
            for graph_station in graph:
                if graph_station.lower() == london_name:
                    self.logger.info(f"Graph lookup (added London): '{station_name}' → '{graph_station}'")
                    return graph_station
        
        # Not found
        return None
    
    def dijkstra_shortest_path(self, start: str, end: str, graph: Dict,
                              weight_func: str = 'time',
                              preferences: Optional[Dict[str, Any]] = None) -> Optional[PathNode]:
        """
        Find shortest path using Dijkstra's algorithm with enhanced pathfinding.
        
        Args:
            start: Starting station name
            end: Destination station name
            graph: Network graph
            weight_func: Weight function ('time', 'distance', 'changes')
            preferences: User preferences for routing
        """
        # Handle London station variants in graph lookup
        graph_start = self.find_station_in_graph(start, graph)
        if not graph_start:
            self.logger.warning(f"Start station '{start}' not found in network graph")
            return None
            
        graph_end = self.find_station_in_graph(end, graph)
        if not graph_end:
            self.logger.warning(f"End station '{end}' not found in network graph")
            return None
            
        # Use the resolved graph station names for the rest of the function
        start = graph_start
        end = graph_end
        
        # Get preferences or use empty dict
        if preferences is None:
            preferences = {}
            
        avoid_walking = preferences.get('avoid_walking', False)
        prefer_direct = preferences.get('prefer_direct', False)
        max_walking_distance_km = preferences.get('max_walking_distance_km', 0.1)
        
        # Check if both stations are on the same line
        common_lines = set()
        for line in self.data_repository.load_railway_lines():
            if start in line.stations and end in line.stations:
                common_lines.add(line.name)
        
        self.logger.debug(f"Starting Dijkstra pathfinding from '{start}' to '{end}' using {weight_func} optimization")
        self.logger.debug(f"Preferences: avoid_walking={avoid_walking}, prefer_direct={prefer_direct}, max_walking_distance_km={max_walking_distance_km}")
        self.logger.debug(f"Common lines between {start} and {end}: {common_lines}")
        
        # Priority queue: (weight, node)
        pq = [PathNode(start, 0.0, 0, 0, [start], [])]
        visited = set()
        distances = {start: 0.0}
        
        # Special priority for stations on main routes
        main_route_stations = {
            "London Waterloo": 2000,
            "London Paddington": 2000,
            "London Kings Cross": 2000,
            "London Euston": 2000,
            "London Liverpool Street": 2000,
            "London Victoria": 1000,
            "London Bridge": 1000
        }
        
        # Determine if we should prioritize a specific London terminal
        southwest_stations = ["Farnborough", "Farnborough North", "Farnborough (Main)", "Basingstoke", "Southampton", "Woking", "Guildford", "Clapham Junction"]
        eastern_stations = ["Colchester", "Chelmsford", "Ipswich", "Norwich"]
        western_stations = ["Reading", "Swindon", "Bristol", "Oxford"]
        
        # Check if we should prioritize a specific terminal based on route
        prioritize_terminal = None
        
        # Regional prioritization for Southwest England
        if "Farnborough" in start or any(station in start for station in southwest_stations):
            prioritize_terminal = "London Waterloo"
            main_route_stations["London Waterloo"] = 3000
            main_route_stations["London Victoria"] = 500
            self.logger.info(f"Prioritizing London Waterloo for Southwest England route")
        elif any(station in start for station in southwest_stations):
            prioritize_terminal = "London Waterloo"
            main_route_stations["London Waterloo"] = 5000
        elif any(station in start for station in eastern_stations):
            prioritize_terminal = "London Liverpool Street"
            main_route_stations["London Liverpool Street"] = 5000
        elif any(station in start for station in western_stations):
            prioritize_terminal = "London Paddington"
            main_route_stations["London Paddington"] = 5000
            
        self.logger.info(f"Prioritizing terminal for route: {prioritize_terminal}")
        
        nodes_explored = 0
        
        while pq:
            current = heapq.heappop(pq)
            nodes_explored += 1
            
            if current.station in visited:
                continue
            
            visited.add(current.station)
            
            if current.station == end:
                self.logger.info(f"Found path from '{start}' to '{end}' after exploring {nodes_explored} nodes")
                self.logger.info(f"Path: {' -> '.join(current.path)}")
                self.logger.info(f"Total distance: {current.distance:.1f}km, time: {current.time}min, changes: {current.changes}")
                return current
            
            # Explore neighbors
            neighbors = graph.get(current.station, {})
            self.logger.debug(f"Exploring {len(neighbors)} neighbors from '{current.station}'")
            
            for next_station, connections in neighbors.items():
                if next_station in visited:
                    continue
                
                # Allow Underground routing for cross-London journeys
                is_london_station = "London" in next_station
                london_terminals = ["London Waterloo", "London Liverpool Street", "London Victoria", "London Paddington",
                                  "London Kings Cross", "London St Pancras", "London Euston", "London Bridge"]
                is_london_terminal = next_station in london_terminals
                
                # Calculate if this is a cross-London journey that might benefit from Underground
                from_is_london = "London" in start
                to_is_london = "London" in end
                
                # Allow Underground routing if:
                # 1. It's a London terminal (always allow)
                # 2. It's a cross-London journey where Underground might be beneficial
                # 3. The journey is longer than 50km (likely cross-London)
                journey_distance = current.distance
                is_cross_london_journey = (not from_is_london and not to_is_london and journey_distance > 30)
                
                # Skip non-terminal London stations ONLY if it's not a beneficial cross-London journey
                if is_london_station and not is_london_terminal and not is_cross_london_journey:
                    self.logger.debug(f"Skipping non-terminal London station: {next_station} (not cross-London journey)")
                    continue
                elif is_london_station and not is_london_terminal and is_cross_london_journey:
                    self.logger.info(f"Allowing Underground routing for cross-London journey: {next_station}")
                
                # If both start and end are on common lines, ONLY allow connections on those lines
                if common_lines:
                    common_line_connections = [c for c in connections if c['line'] in common_lines]
                    if common_line_connections:
                        connections = common_line_connections
                        self.logger.debug(f"RESTRICTING to common line connections only: {[c['line'] for c in connections]}")
                    else:
                        self.logger.debug(f"Skipping {next_station} - no common line connections available")
                        continue
                
                # Check for South Western Main Line connections from Farnborough
                sw_main_line_connections = []
                if "Farnborough" in start or start == "Clapham Junction":
                    sw_main_line_connections = [c for c in connections
                                              if c.get('line') == "South Western Main Line"
                                              and "Waterloo" in c.get('to_station', "")]
                    if sw_main_line_connections:
                        self.logger.debug(f"Found South Western Main Line connection to Waterloo: {current.station} -> {next_station}")
                        
                direct_connections = [c for c in connections if c.get('is_direct', False)]
                
                # Prioritize connections in this order:
                if sw_main_line_connections:
                    connections_to_check = sw_main_line_connections
                    self.logger.debug(f"Using SW Main Line connection from {current.station} to {next_station}")
                elif direct_connections:
                    connections_to_check = direct_connections
                    self.logger.debug(f"Found direct connection from {current.station} to {next_station}")
                else:
                    connections_to_check = connections
                
                # Handle walking connections if avoid_walking is enabled
                if avoid_walking:
                    walking_connections = []
                    non_walking_connections = []
                    
                    for conn in connections_to_check:
                        from_station = current.station
                        to_station = conn['to_station']
                        
                        # Check if these stations are on the same line
                        same_line = False
                        for line in self.data_repository.load_railway_lines():
                            if from_station in line.stations and to_station in line.stations:
                                same_line = True
                                self.logger.info(f"NOT marking as walking - stations are on same line: {from_station} → {to_station} (line: {line.name})")
                                break
                        
                        # Only consider underground connections if not on same line
                        if not same_line:
                            # Check if either station is in London but not a terminal
                            from_is_london = "London" in from_station
                            to_is_london = "London" in to_station
                            london_terminals = ["London Waterloo", "London Liverpool Street", "London Victoria", "London Paddington"]
                            
                            from_is_terminal = from_station in london_terminals
                            to_is_terminal = to_station in london_terminals
                            
                            # Mark as walking if both stations are in London but not both are terminals
                            if from_is_london and to_is_london and not (from_is_terminal and to_is_terminal):
                                walking_connections.append(conn)
                                conn['is_walking_connection'] = True
                                self.logger.info(f"Marking as walking due to both stations being in London: {from_station} → {to_station}")
                                continue
                            elif (from_is_london and not from_is_terminal) or (to_is_london and not to_is_terminal):
                                walking_connections.append(conn)
                                conn['is_walking_connection'] = True
                                self.logger.info(f"Marking as walking due to one non-terminal London station: {from_station} → {to_station}")
                                continue
                            
                        # Check if this is a walking connection between London terminals
                        london_terminals = ["London Waterloo", "London Victoria", "London Paddington",
                                           "London Kings Cross", "London St Pancras", "London Euston",
                                           "London Liverpool Street", "London Bridge", "London Charing Cross"]
                        directly_connected_terminals = [
                            ("London Kings Cross", "London St Pancras"),
                            ("London Waterloo", "London Waterloo East")
                        ]
                        
                        from_is_london_terminal = from_station in london_terminals
                        to_is_london_terminal = to_station in london_terminals
                        
                        # Check if they're London terminals
                        if from_is_london_terminal and to_is_london_terminal:
                            # Check if they're directly connected terminals
                            directly_connected = False
                            for term1, term2 in directly_connected_terminals:
                                if (from_station == term1 and to_station == term2) or (from_station == term2 and to_station == term1):
                                    directly_connected = True
                                    break
                                    
                            if not directly_connected:
                                walking_connections.append(conn)
                                conn['is_walking_connection'] = True
                                self.logger.info(f"Marking as walking due to London terminals: {from_station} → {to_station}")
                                continue
                            
                        # Check if they're on the same line
                        same_line = False
                        for line in self.data_repository.load_railway_lines():
                            if from_station in line.stations and to_station in line.stations:
                                same_line = True
                                break
                        
                        # If stations are on the same line, prefer train connection, not walking
                        if same_line:
                            non_walking_connections.append(conn)
                            self.logger.debug(f"Using train connection for stations on same line: {from_station} → {to_station}")
                            continue
                            
                        # Calculate haversine distance if we have coordinates
                        distance_km = 0
                        if 'distance' in conn:
                            distance_km = conn['distance']
                        
                        # Check explicit walking markers
                        is_walking = (
                            conn.get('line') == 'WALKING' or
                            conn.get('is_walking_connection', False) or
                            ('walking' in conn.get('line', '').lower())
                        )
                        
                        # Apply combined logic to determine if this is a walking connection
                        if is_walking or (not same_line and distance_km > max_walking_distance_km):
                            walking_connections.append(conn)
                            conn['is_walking_connection'] = True
                        else:
                            non_walking_connections.append(conn)
                    
                    # If avoid_walking is true, strictly avoid all walking connections
                    if non_walking_connections:
                        connections_to_check = non_walking_connections
                        self.logger.info(f"Using only {len(non_walking_connections)} non-walking connections from {current.station} to {next_station}")
                        walking_connections = []
                    else:
                        self.logger.warning(f"No non-walking alternatives found from {current.station} to {next_station}")
                        self.logger.warning(f"Network may be disconnected if walking is strictly avoided")
                
                # Find best connection based on weight function with same-line prioritization
                best_connection = self._get_best_connection(
                    connections_to_check, current, start, end, weight_func
                )
                
                if not best_connection:
                    continue
                
                # Calculate new weights using Haversine distance if coordinates available
                new_distance = current.distance + best_connection['distance']
                new_time = current.time + best_connection['time']
                
                # Calculate changes (if switching lines)
                new_changes = current.changes
                if current.lines_used and current.lines_used[-1] != best_connection['line']:
                    # Don't count as a change if it's a direct connection
                    if not best_connection.get('is_direct', False):
                        new_changes += 1
                        new_time += 5  # Add 5 minutes for interchange
                
                new_path = current.path + [next_station]
                new_lines = current.lines_used + [best_connection['line']]
                
                # Choose weight based on function
                weight = self._calculate_weight(
                    weight_func, new_time, new_distance, new_changes, best_connection
                )
                
                # Apply Underground routing bonus for cross-London journeys
                weight = self._apply_underground_routing_bonus(
                    weight, best_connection, current, start, end
                )
                
                # Apply penalties for walking connections
                weight = self._apply_walking_penalties(
                    weight, best_connection, current.station, avoid_walking, max_walking_distance_km
                )
                
                # Only add to queue if we found a better path
                if next_station not in distances or weight < distances[next_station]:
                    distances[next_station] = weight
                    
                    next_node = PathNode(
                        station=next_station,
                        distance=new_distance,
                        time=new_time,
                        changes=new_changes,
                        path=new_path,
                        lines_used=new_lines
                    )
                    
                    heapq.heappush(pq, next_node)
        
        self.logger.warning(f"No path found from '{start}' to '{end}' after exploring {nodes_explored} nodes")
        return None
    
    def _get_best_connection(self, connections: List[Dict], current: PathNode, 
                           start: str, end: str, weight_func: str) -> Optional[Dict]:
        """Get the best connection based on weight function and priorities."""
        if not connections:
            return None
        
        def get_connection_priority(conn):
            """Calculate connection priority - lower is better"""
            base_weight = conn['time'] if weight_func == 'time' else conn.get('distance', conn['time'])
            
            # Special case for Farnborough routes
            if "Farnborough" in start:
                if conn['line'] == "South Western Main Line" and "Waterloo" in conn.get('to_station', ""):
                    self.logger.debug(f"Priority: South Western Main Line to Waterloo")
                    return base_weight - 100000
            
            # Walking connection between Farnborough North and Farnborough (Main)
            if ("Farnborough North" in current.station and "Farnborough (Main)" in conn['to_station']) or \
               ("Farnborough (Main)" in current.station and "Farnborough North" in conn['to_station']):
                self.logger.debug(f"Prioritizing Farnborough walking connection")
                return base_weight - 10000
            
            # Check if both start and end stations are on the same line
            start_lines = set()
            end_lines = set()
            
            for line in self.data_repository.load_railway_lines():
                if start in line.stations:
                    start_lines.add(line.name)
                if end in line.stations:
                    end_lines.add(line.name)
            
            common_lines = start_lines.intersection(end_lines)
            
            # If this connection uses a line that serves both start and end stations,
            # give it massive priority to prevent line switching
            if conn['line'] in common_lines:
                return base_weight - 10000
            
            # Strong preference for staying on the same line as the current path
            if current.lines_used:
                current_line = current.lines_used[-1]
                if conn['line'] == current_line:
                    return base_weight - 1000
            
            # Secondary preference for direct connections
            if conn.get('is_direct', False):
                return base_weight - 100
            
            return base_weight
        
        if weight_func == 'changes':
            def changes_priority(conn):
                start_lines = set()
                end_lines = set()
                
                for line in self.data_repository.load_railway_lines():
                    if start in line.stations:
                        start_lines.add(line.name)
                    if end in line.stations:
                        end_lines.add(line.name)
                
                common_lines = start_lines.intersection(end_lines)
                
                if conn['line'] in common_lines:
                    return (0, conn['time'] - 20000)
                
                if current.lines_used and conn['line'] == current.lines_used[-1]:
                    return (0, conn['time'] - 2000)
                elif conn.get('is_direct', False):
                    return (0, conn['time'] - 1000)
                else:
                    return (1, conn['time'])
            
            return min(connections, key=changes_priority)
        else:
            return min(connections, key=get_connection_priority)
    
    def _calculate_weight(self, weight_func: str, new_time: int, new_distance: float, 
                         new_changes: int, best_connection: Dict) -> float:
        """Calculate the weight for pathfinding based on the weight function."""
        if weight_func == 'time':
            return new_time
        elif weight_func == 'distance':
            return new_distance
        elif weight_func == 'changes':
            # Heavily penalize changes, but give direct connections a big advantage
            direct_bonus = 0 if best_connection.get('is_direct', False) else 1000
            return (new_changes * 1000) + direct_bonus + new_time
        else:
            return new_time
    
    def _apply_walking_penalties(self, weight: float, connection: Dict, current_station: str,
                               avoid_walking: bool, max_walking_distance_km: float) -> float:
        """Apply penalties for walking connections based on preferences."""
        # Check if this is a walking connection
        is_walking = False
        
        from_station = current_station
        to_station = connection['to_station']
        
        # Check if this is explicitly defined as a walking connection
        interchange_connections = self._load_interchange_connections()
        for ic in interchange_connections.get('connections', []):
            if ((ic.get('from_station') == from_station and ic.get('to_station') == to_station) or
                (ic.get('from_station') == to_station and ic.get('to_station') == from_station)):
                if ic.get('connection_type') == 'WALKING':
                    is_walking = True
                    self.logger.debug(f"Walking connection detected: {from_station} -> {to_station} (from interchange_connections.json)")
                    break
        
        if not is_walking:
            # Use Haversine distance calculation to determine if this is a walking connection
            from_coords = None
            to_coords = None
            
            for ic in interchange_connections.get('connections', []):
                if ((ic.get('from_station') == from_station and ic.get('to_station') == to_station) or
                    (ic.get('from_station') == to_station and ic.get('to_station') == from_station)):
                    coords = ic.get('coordinates', {})
                    if coords:
                        if ic.get('from_station') == from_station:
                            from_coords = coords.get('from')
                            to_coords = coords.get('to')
                        else:
                            from_coords = coords.get('to')
                            to_coords = coords.get('from')
                        break
            
            # If we have coordinates, use Haversine distance to determine walking connection
            if from_coords and to_coords:
                haversine_distance_km = self._calculate_haversine_distance(from_coords, to_coords)
                self.logger.debug(f"Haversine distance: {from_station} -> {to_station} = {haversine_distance_km:.3f}km")
                
                if haversine_distance_km > max_walking_distance_km:
                    is_walking = True
                    self.logger.debug(f"Walking connection by distance: {from_station} -> {to_station} ({haversine_distance_km:.3f}km > {max_walking_distance_km}km)")
            else:
                # Fallback: Check if they're on the same line
                same_line = False
                for line in self.data_repository.load_railway_lines():
                    line_stations = [s.replace(" (Main)", "").replace(" (Cross Country Line)", "")
                                   for s in line.stations]
                    clean_from = from_station.replace(" (Main)", "").replace(" (Cross Country Line)", "")
                    clean_to = to_station.replace(" (Main)", "").replace(" (Cross Country Line)", "")
                    
                    if clean_from in line_stations and clean_to in line_stations:
                        same_line = True
                        break
                
                distance_km = connection.get('distance', 0)
                
                if not same_line and distance_km > max_walking_distance_km:
                    is_walking = True
                    self.logger.debug(f"Walking connection by fallback: {from_station} -> {to_station} (not same line, distance: {distance_km:.3f}km)")
        
        # Also check the explicit flags
        if is_walking or connection.get('line') == 'WALKING' or connection.get('is_walking_connection', False):
            if avoid_walking:
                # This should have been filtered out earlier, but just in case
                self.logger.debug(f"Avoid walking: Skipping walking connection: {current_station} -> {to_station}")
                return float('inf')  # Make it impossible to select
            else:
                # Allow walking connections but mark them properly
                connection['is_walking_connection'] = True
                connection['line'] = 'WALKING'
                
                # Use a small penalty to prioritize non-walking connections but allow walking
                penalty_multiplier = connection.get('walking_penalty', 2)
                
                original_weight = weight
                weight = weight * penalty_multiplier
                self.logger.debug(f"Walking connection allowed: {current_station} -> {to_station} (penalty applied: {original_weight} -> {weight})")
        
        return weight
    
    def _calculate_haversine_distance(self, coord1: Dict, coord2: Dict) -> float:
        """Calculate the Haversine distance between two coordinates in kilometers."""
        import math
        
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
    
    def _load_interchange_connections(self) -> dict:
        """Load interchange connections from JSON file."""
        try:
            # Try to use data path resolver
            try:
                from ...utils.data_path_resolver import get_data_file_path
                interchange_file = get_data_file_path("interchange_connections.json")
            except (ImportError, FileNotFoundError):
                # Fallback to old method
                interchange_file = Path("src/data/interchange_connections.json")
                
            if not interchange_file.exists():
                self.logger.warning("Interchange connections file not found")
                return {}
            
            with open(interchange_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            self.logger.error(f"Failed to load interchange connections: {e}")
            return {}
    
    def _apply_underground_routing_bonus(self, weight: float, connection: Dict, current: 'PathNode',
                                       start: str, end: str) -> float:
        """Apply bonus for Underground routing when it's beneficial for cross-London journeys."""
        # Check if this connection involves Underground routing
        if connection.get('line') != 'London Underground':
            return weight
        
        # Calculate journey characteristics
        from_is_london = "London" in start
        to_is_london = "London" in end
        journey_distance = current.distance
        to_station = connection.get('to_station', '')
        
        # Major London terminals that are well-connected via Underground
        major_terminals = [
            "London Waterloo", "London Liverpool Street", "London Victoria", "London Paddington",
            "London Kings Cross", "London St Pancras", "London Euston", "London Bridge"
        ]
        
        # Check if this Underground connection goes to a major terminal
        connects_to_major_terminal = to_station in major_terminals
        
        # Apply different bonuses based on journey type
        bonus_factor = 1.0  # Default: no bonus
        original_weight = weight
        
        # 1. Cross-London journeys (National Rail -> Underground -> National Rail)
        is_cross_london_journey = (not from_is_london and not to_is_london and journey_distance > 20)
        
        # 2. Routes to major terminals (faster than complex National Rail routing)
        if connects_to_major_terminal:
            if is_cross_london_journey:
                # Major bonus for cross-London routes via major terminals
                # Underground crossing London typically takes 25-30 minutes vs 2+ hours via National Rail
                bonus_factor = 0.4  # 60% weight reduction - makes Underground very attractive
                self.logger.info(f"Major Underground bonus (cross-London via terminal): {current.station} -> {to_station}")
            elif journey_distance > 15:
                # Medium bonus for routes to terminals from moderate distances
                bonus_factor = 0.6  # 40% weight reduction
                self.logger.info(f"Medium Underground bonus (to terminal): {current.station} -> {to_station}")
            else:
                # Small bonus for short routes to terminals
                bonus_factor = 0.8  # 20% weight reduction
                self.logger.info(f"Small Underground bonus (short to terminal): {current.station} -> {to_station}")
        elif is_cross_london_journey:
            # Standard bonus for cross-London journeys not via major terminals
            bonus_factor = 0.7  # 30% weight reduction
            self.logger.info(f"Standard Underground bonus (cross-London): {current.station} -> {to_station}")
        
        # Apply the bonus
        if bonus_factor < 1.0:
            weight = weight * bonus_factor
            self.logger.info(f"Underground routing bonus applied: {current.station} -> {to_station} "
                           f"(weight: {original_weight:.1f} -> {weight:.1f}, factor: {bonus_factor})")
        
        return weight