"""
Refactored Route Service Implementation

Service implementation for route calculation and pathfinding using modular components.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from collections import deque

from ..interfaces.i_route_service import IRouteService
from ..interfaces.i_data_repository import IDataRepository
from ..models.route import Route, RouteSegment
from .network_graph_builder import NetworkGraphBuilder
from .pathfinding_algorithm import PathfindingAlgorithm
from .route_converter import RouteConverter
from .station_name_normalizer import StationNameNormalizer
from .underground_routing_handler import UndergroundRoutingHandler


class RouteServiceRefactored(IRouteService):
    """Refactored service implementation for route calculation and pathfinding."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the route service with modular components.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        
        # Initialize modular components
        self.network_builder = NetworkGraphBuilder(data_repository)
        self.pathfinder = PathfindingAlgorithm(data_repository)
        self.route_converter = RouteConverter(data_repository)
        self.station_normalizer = StationNameNormalizer(data_repository)
        self.underground_handler = UndergroundRoutingHandler(data_repository)
        
        # Cache for route calculations
        # Cache key is (from_station, to_station, preferences_key)
        self._route_cache: Dict[Tuple, List[Route]] = {}
        
        self.logger.info("Initialized RefactoredRouteService with modular components")
    
    def calculate_route(self, from_station: str, to_station: str,
                       max_changes: Optional[int] = None,
                       preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Calculate the best route between two stations."""
        # Normalize station names for case-insensitive matching
        normalized_from = self.station_normalizer.normalize_station_name(from_station)
        normalized_to = self.station_normalizer.normalize_station_name(to_station)
        
        if not self.data_repository.validate_station_exists(normalized_from):
            self.logger.warning(f"From station does not exist: {from_station}")
            return None
        
        if not self.data_repository.validate_station_exists(normalized_to):
            self.logger.warning(f"To station does not exist: {to_station}")
            return None
        
        if from_station == to_station:
            return None
        
        # Get cache key that includes preferences
        cache_key = self._get_cache_key(normalized_from, normalized_to, preferences)
        
        # Check cache first
        if cache_key in self._route_cache:
            routes = self._route_cache[cache_key]
            if routes:
                self.logger.debug(f"Using cached route for {normalized_from} → {normalized_to} with preferences")
                return routes[0]  # Return best route
        
        # Check if we should use black box Underground routing
        black_box_route = self.underground_handler.create_black_box_route(normalized_from, normalized_to)
        if black_box_route:
            # Cache and return the black box route
            self._route_cache[cache_key] = [black_box_route]
            return black_box_route
        
        # Build network graph
        graph = self.network_builder.build_network_graph()
        
        # Calculate route using Dijkstra's algorithm
        self.logger.info(f"Attempting to find route from '{normalized_from}' to '{normalized_to}' with preferences: {preferences}")
        path_node = self.pathfinder.dijkstra_shortest_path(
            normalized_from, normalized_to, graph, 'time', preferences
        )
        
        if path_node is None:
            self.logger.warning(f"No route found from '{normalized_from}' to '{normalized_to}'")
            self.logger.info(f"Original station names: '{from_station}' to '{to_station}'")
            
            # Check stations exist in network graph
            if normalized_from not in graph:
                self.logger.warning(f"Station '{normalized_from}' not found in network graph")
            if normalized_to not in graph:
                self.logger.warning(f"Station '{normalized_to}' not found in network graph")
                
            return None
        
        # Only check max_changes if explicitly provided
        if max_changes is not None and path_node.changes > max_changes:
            self.logger.warning(f"Route requires {path_node.changes} changes, max allowed: {max_changes}")
            return None
        
        try:
            route = self.route_converter.path_to_route(path_node, graph)
            
            # Enhance route with black box Underground segments if needed
            enhanced_route = self.underground_handler.enhance_route_with_black_box(route)
            
            # Cache the result with preference-aware key
            self._route_cache[cache_key] = [enhanced_route]
            self.logger.debug(f"Cached route for {normalized_from} → {normalized_to} with preferences")
            
            return enhanced_route
            
        except Exception as e:
            self.logger.error(f"Failed to convert path to route: {e}")
            return None
    
    def calculate_multiple_routes(self, from_station: str, to_station: str,
                                max_routes: int = 5, max_changes: Optional[int] = None,
                                preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Calculate multiple alternative routes between two stations."""
        # Normalize station names for case-insensitive matching
        normalized_from = self.station_normalizer.normalize_station_name(from_station)
        normalized_to = self.station_normalizer.normalize_station_name(to_station)
        
        routes = []
        
        # Get cache key that includes preferences
        cache_key = self._get_cache_key(normalized_from, normalized_to, preferences)
        
        # Check cache first
        if cache_key in self._route_cache and len(self._route_cache[cache_key]) >= max_routes:
            self.logger.debug(f"Using cached multiple routes for {normalized_from} → {normalized_to} with preferences")
            return self._route_cache[cache_key][:max_routes]
        
        # Check if we should use black box Underground routing
        black_box_route = self.underground_handler.create_black_box_route(normalized_from, normalized_to)
        if black_box_route:
            routes.append(black_box_route)
            self._route_cache[cache_key] = routes
            return routes
        
        # Build network graph
        graph = self.network_builder.build_network_graph()
        
        # Try different optimization strategies
        strategies = ['time', 'changes', 'distance']
        
        for strategy in strategies:
            if len(routes) >= max_routes:
                break
            
            path_node = self.pathfinder.dijkstra_shortest_path(
                normalized_from, normalized_to, graph, strategy, preferences
            )
            
            if path_node:
                # Only check max_changes if explicitly provided
                if max_changes is not None and path_node.changes > max_changes:
                    continue
                    
                try:
                    route = self.route_converter.path_to_route(path_node, graph)
                    
                    # Enhance route with black box Underground segments if needed
                    enhanced_route = self.underground_handler.enhance_route_with_black_box(route)
                    
                    # Check if this route is significantly different from existing ones
                    is_unique = True
                    for existing_route in routes:
                        if self._routes_similar(enhanced_route, existing_route):
                            is_unique = False
                            break
                    
                    if is_unique:
                        routes.append(enhanced_route)
                        
                except Exception as e:
                    self.logger.error(f"Failed to create route with strategy {strategy}: {e}")
                    continue
        
        # Sort routes by preference (time, then changes, then distance)
        routes.sort(key=lambda r: (
            r.total_journey_time_minutes or 999,
            r.changes_required,
            r.total_distance_km or 999
        ))
        
        # Cache the results with preference-aware key
        self._route_cache[cache_key] = routes
        self.logger.debug(f"Cached {len(routes)} routes for {normalized_from} → {normalized_to} with preferences")
        
        return routes[:max_routes]
    
    def find_direct_routes(self, from_station: str, to_station: str) -> List[Route]:
        """Find all direct routes (no changes) between two stations."""
        common_lines = self.data_repository.get_common_lines(from_station, to_station)
        
        direct_routes = []
        
        for line in common_lines:
            # Check if stations are on the same line in correct order
            line_stations = line.stations
            
            try:
                from_idx = line_stations.index(from_station)
                to_idx = line_stations.index(to_station)
                
                if from_idx != to_idx:  # Different stations
                    # Calculate journey time and distance
                    journey_time = line.get_journey_time(from_station, to_station) or 0
                    distance = line.get_distance(from_station, to_station) or 0.0
                    
                    route = self.route_converter.create_direct_route(
                        from_station, to_station, line.name, journey_time, distance
                    )
                    
                    direct_routes.append(route)
                    
            except ValueError:
                # Stations not on this line
                continue
        
        return direct_routes
    
    def find_interchange_routes(self, from_station: str, to_station: str) -> List[Route]:
        """Find routes with exactly one interchange between two stations."""
        interchange_routes = []
        
        # Get all interchange stations
        interchange_stations = self.data_repository.get_interchange_stations()
        
        for interchange in interchange_stations:
            if interchange.name == from_station or interchange.name == to_station:
                continue
            
            # Try route via this interchange
            first_leg = self.find_direct_routes(from_station, interchange.name)
            second_leg = self.find_direct_routes(interchange.name, to_station)
            
            # Combine legs if both exist
            for leg1 in first_leg:
                for leg2 in second_leg:
                    # Check if we can change lines at the interchange
                    leg1_lines = set(seg.line_name for seg in leg1.segments)
                    leg2_lines = set(seg.line_name for seg in leg2.segments)
                    
                    if leg1_lines.intersection(leg2_lines):
                        continue  # Same line, not really an interchange
                    
                    # Create combined route
                    route = self.route_converter.create_interchange_route(
                        from_station, to_station, leg1, leg2, interchange.name
                    )
                    
                    interchange_routes.append(route)
        
        # Sort by journey time
        interchange_routes.sort(key=lambda r: r.total_journey_time_minutes or 999)
        
        return interchange_routes
    
    def get_fastest_route(self, from_station: str, to_station: str,
                         preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Get the fastest route between two stations."""
        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(from_station, to_station, graph, 'time', preferences)
        
        if path_node:
            try:
                route = self.route_converter.path_to_route(path_node, graph)
                return self.underground_handler.enhance_route_with_black_box(route)
            except Exception as e:
                self.logger.error(f"Failed to create fastest route: {e}")
        
        return None
    
    def get_shortest_route(self, from_station: str, to_station: str,
                          preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Get the shortest distance route between two stations."""
        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(from_station, to_station, graph, 'distance', preferences)
        
        if path_node:
            try:
                route = self.route_converter.path_to_route(path_node, graph)
                return self.underground_handler.enhance_route_with_black_box(route)
            except Exception as e:
                self.logger.error(f"Failed to create shortest route: {e}")
        
        return None
    
    def get_fewest_changes_route(self, from_station: str, to_station: str,
                                preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Get the route with fewest changes between two stations."""
        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(from_station, to_station, graph, 'changes', preferences)
        
        if path_node:
            try:
                route = self.route_converter.path_to_route(path_node, graph)
                return self.underground_handler.enhance_route_with_black_box(route)
            except Exception as e:
                self.logger.error(f"Failed to create fewest changes route: {e}")
        
        return None
    
    def find_routes_via_station(self, from_station: str, to_station: str,
                               via_station: str,
                               preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Find routes that pass through a specific intermediate station."""
        routes = []
        
        # Calculate route from start to via station
        first_leg = self.calculate_route(from_station, via_station, preferences=preferences)
        if not first_leg:
            return routes
        
        # Calculate route from via station to destination
        second_leg = self.calculate_route(via_station, to_station, preferences=preferences)
        if not second_leg:
            return routes
        
        # Combine the routes
        route = self.route_converter.create_via_station_route(
            from_station, to_station, first_leg, second_leg, via_station
        )
        
        routes.append(route)
        return routes
    
    def find_routes_avoiding_station(self, from_station: str, to_station: str,
                                   avoid_station: str,
                                   preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Find routes that avoid a specific station."""
        routes = self.calculate_multiple_routes(from_station, to_station, preferences=preferences)
        
        filtered_routes = []
        for route in routes:
            if avoid_station not in route.intermediate_stations:
                filtered_routes.append(route)
        
        return filtered_routes
    
    def find_routes_on_line(self, from_station: str, to_station: str,
                           line_name: str,
                           preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Find routes that use a specific railway line."""
        # Check if both stations are on the specified line
        line = self.data_repository.get_railway_line_by_name(line_name)
        if not line:
            return []
        
        if from_station not in line.stations or to_station not in line.stations:
            return []
        
        # Try to find direct route on this line
        direct_routes = self.find_direct_routes(from_station, to_station)
        
        routes_on_line = []
        for route in direct_routes:
            if any(seg.line_name == line_name for seg in route.segments):
                routes_on_line.append(route)
        
        return routes_on_line
    
    def get_possible_destinations(self, from_station: str, 
                                max_changes: int = 3) -> List[str]:
        """Get all possible destinations from a given station."""
        graph = self.network_builder.build_network_graph()
        
        if from_station not in graph:
            return []
        
        destinations = set()
        
        # BFS to find all reachable stations within max_changes
        queue = deque([(from_station, 0, set())])  # (station, changes, lines_used)
        visited = set()
        
        while queue:
            current_station, changes, lines_used = queue.popleft()
            
            if (current_station, changes) in visited:
                continue
            
            visited.add((current_station, changes))
            
            if current_station != from_station:
                destinations.add(current_station)
            
            if changes >= max_changes:
                continue
            
            # Explore neighbors
            for next_station, connections in graph[current_station].items():
                for connection in connections:
                    line = connection['line']
                    new_changes = changes
                    
                    # Check if we need to change lines
                    if lines_used and line not in lines_used:
                        new_changes += 1
                    
                    if new_changes <= max_changes:
                        new_lines_used = lines_used | {line}
                        queue.append((next_station, new_changes, new_lines_used))
        
        return sorted(list(destinations))
    
    def get_journey_time(self, from_station: str, to_station: str,
                        preferences: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Get estimated journey time between two stations."""
        route = self.get_fastest_route(from_station, to_station, preferences)
        return route.total_journey_time_minutes if route else None
    
    def get_distance(self, from_station: str, to_station: str,
                    preferences: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """Get distance between two stations."""
        route = self.get_shortest_route(from_station, to_station, preferences)
        return route.total_distance_km if route else None
    
    def validate_route(self, route: Route) -> Tuple[bool, List[str]]:
        """Validate that a route is feasible and correct."""
        errors = []
        
        # Check if all stations exist
        if not self.data_repository.validate_station_exists(route.from_station):
            errors.append(f"From station does not exist: {route.from_station}")
        
        if not self.data_repository.validate_station_exists(route.to_station):
            errors.append(f"To station does not exist: {route.to_station}")
        
        # Check segments
        for i, segment in enumerate(route.segments):
            # Skip validation for Underground black box segments
            if segment.service_pattern == "UNDERGROUND":
                continue
                
            # Check if line exists
            if not self.data_repository.validate_line_exists(segment.line_name):
                errors.append(f"Segment {i}: Line does not exist: {segment.line_name}")
                continue
            
            # Check if stations are on the line
            line = self.data_repository.get_railway_line_by_name(segment.line_name)
            if line:
                if segment.from_station not in line.stations:
                    errors.append(f"Segment {i}: Station {segment.from_station} not on line {segment.line_name}")
                
                if segment.to_station not in line.stations:
                    errors.append(f"Segment {i}: Station {segment.to_station} not on line {segment.line_name}")
        
        # Check segment continuity
        for i in range(len(route.segments) - 1):
            current_segment = route.segments[i]
            next_segment = route.segments[i + 1]
            
            if current_segment.to_station != next_segment.from_station:
                errors.append(f"Segments {i} and {i+1}: Not continuous - {current_segment.to_station} != {next_segment.from_station}")
        
        return len(errors) == 0, errors
    
    def get_route_alternatives(self, route: Route, max_alternatives: int = 3,
                              preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Get alternative routes similar to the given route."""
        return self.calculate_multiple_routes(
            route.from_station,
            route.to_station,
            max_alternatives + 1,  # +1 because original might be included
            preferences=preferences
        )[:max_alternatives]
    
    def calculate_route_cost(self, route: Route) -> Optional[float]:
        """Calculate estimated cost for a route."""
        # Simple cost calculation based on distance and changes
        if route.total_distance_km is None:
            return None
        
        base_cost = route.total_distance_km * 0.20  # £0.20 per km
        change_cost = route.changes_required * 2.0  # £2.00 per change
        
        return base_cost + change_cost
    
    def get_interchange_stations(self, from_station: str, to_station: str) -> List[str]:
        """Get all possible interchange stations between two stations."""
        interchange_stations = []
        
        # Get lines serving each station
        from_lines = self.data_repository.get_lines_serving_station(from_station)
        to_lines = self.data_repository.get_lines_serving_station(to_station)
        
        # Find stations that are on lines serving both origin and destination
        all_interchanges = self.data_repository.get_interchange_stations()
        
        for interchange in all_interchanges:
            interchange_lines = self.data_repository.get_lines_serving_station(interchange.name)
            
            # Check if this interchange connects the origin and destination networks
            connects_from = any(line in from_lines for line in interchange_lines)
            connects_to = any(line in to_lines for line in interchange_lines)
            
            if connects_from and connects_to and interchange.name not in [from_station, to_station]:
                interchange_stations.append(interchange.name)
        
        return interchange_stations
    
    def find_circular_routes(self, station: str, max_distance: float = 50.0) -> List[Route]:
        """Find circular routes starting and ending at the same station."""
        circular_routes = []
        graph = self.network_builder.build_network_graph()
        
        if station not in graph:
            return circular_routes
        
        # BFS to find stations within distance limit
        queue = deque([(station, 0.0, [station], [])])  # (current, distance, path, lines)
        
        while queue:
            current, distance, path, lines = queue.popleft()
            
            if distance > max_distance:
                continue
            
            if len(path) > 1 and current == station:
                # Found a circular route
                try:
                    route = self.route_converter.create_circular_route(
                        station, path, lines, distance
                    )
                    circular_routes.append(route)
                except Exception as e:
                    self.logger.error(f"Failed to create circular route: {e}")
                
                continue
            
            # Explore neighbors
            for next_station, connections in graph[current].items():
                if len(path) > 1 and next_station in path[:-1]:  # Avoid loops except back to start
                    continue
                
                for connection in connections:
                    new_distance = distance + connection['distance']
                    new_path = path + [next_station]
                    new_lines = lines + [connection['line']]
                    
                    queue.append((next_station, new_distance, new_path, new_lines))
        
        return circular_routes[:5]  # Return top 5 circular routes
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """Get statistics about the route network."""
        graph = self.network_builder.build_network_graph()
        
        total_stations = len(graph)
        total_connections = sum(len(neighbors) for neighbors in graph.values())
        
        # Calculate network statistics
        lines = self.data_repository.load_railway_lines()
        total_lines = len(lines)
        
        # Get Underground statistics
        underground_stats = self.underground_handler.get_underground_statistics()
        
        return {
            "total_stations": total_stations,
            "total_connections": total_connections // 2,  # Bidirectional connections
            "total_lines": total_lines,
            "cache_size": len(self._route_cache),
            "average_connections_per_station": total_connections / total_stations if total_stations > 0 else 0,
            "underground_stats": underground_stats
        }
    
    def clear_route_cache(self) -> None:
        """Clear any cached route calculations."""
        self._route_cache.clear()
        self.network_builder.clear_cache()
        self.underground_handler.clear_cache()
        self.logger.info("All caches cleared")
    
    def precompute_common_routes(self, station_pairs: List[Tuple[str, str]]) -> None:
        """Precompute routes for common station pairs."""
        self.logger.info(f"Precomputing routes for {len(station_pairs)} station pairs...")
        
        for from_station, to_station in station_pairs:
            try:
                route = self.calculate_route(from_station, to_station)
                if route:
                    self.logger.debug(f"Precomputed route: {from_station} -> {to_station}")
            except Exception as e:
                self.logger.error(f"Failed to precompute route {from_station} -> {to_station}: {e}")
        
        self.logger.info(f"Precomputation complete. Cache size: {len(self._route_cache)}")
    
    def _get_cache_key(self, from_station: str, to_station: str, preferences: Optional[Dict[str, Any]] = None) -> Tuple:
        """Create a cache key that includes relevant preferences."""
        pref_key = None
        if preferences:
            # Only include preferences that affect routing
            routing_prefs = {
                'avoid_walking': preferences.get('avoid_walking', False),
                'prefer_direct': preferences.get('prefer_direct', False),
                'avoid_london': preferences.get('avoid_london', False),
                'max_walking_distance_km': preferences.get('max_walking_distance_km', 0.1)
            }
            if any(routing_prefs.values()):
                pref_key = frozenset(routing_prefs.items())
        
        return (from_station, to_station, pref_key)
    
    def _routes_similar(self, route1: Route, route2: Route, threshold: float = 0.8) -> bool:
        """Check if two routes are similar."""
        # Compare intermediate stations
        stations1 = set(route1.intermediate_stations)
        stations2 = set(route2.intermediate_stations)
        
        if not stations1 and not stations2:
            return True  # Both are direct routes
        
        if not stations1 or not stations2:
            return False  # One is direct, other is not
        
        # Calculate Jaccard similarity
        intersection = len(stations1.intersection(stations2))
        union = len(stations1.union(stations2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold