"""
Route Service Interface

Interface for route calculation and management services.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from ..models.route import Route, RouteSegment
from ..models.railway_line import RailwayLine


class IRouteService(ABC):
    """Interface for route calculation and management services."""
    
    @abstractmethod
    def calculate_route(self, from_station: str, to_station: str,
                       max_changes: int = 3, preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """
        Calculate the best route between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            max_changes: Maximum number of changes allowed
            preferences: Optional dictionary of routing preferences
            
        Returns:
            Route object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def calculate_multiple_routes(self, from_station: str, to_station: str,
                                max_routes: int = 5, max_changes: int = 3,
                                preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """
        Calculate multiple alternative routes between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            max_routes: Maximum number of routes to return
            max_changes: Maximum number of changes allowed
            preferences: Optional dictionary of routing preferences
            
        Returns:
            List of Route objects sorted by preference
        """
        pass
    
    @abstractmethod
    def find_direct_routes(self, from_station: str, to_station: str) -> List[Route]:
        """
        Find all direct routes (no changes) between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            List of direct Route objects
        """
        pass
    
    @abstractmethod
    def find_interchange_routes(self, from_station: str, to_station: str) -> List[Route]:
        """
        Find routes with exactly one interchange between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            List of Route objects with one change
        """
        pass
    
    @abstractmethod
    def get_fastest_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Get the fastest route between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            Fastest Route object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_shortest_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Get the shortest distance route between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            Shortest Route object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_fewest_changes_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Get the route with fewest changes between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            Route with fewest changes if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_routes_via_station(self, from_station: str, to_station: str,
                               via_station: str) -> List[Route]:
        """
        Find routes that pass through a specific intermediate station.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            via_station: Intermediate station to pass through
            
        Returns:
            List of Route objects passing through via_station
        """
        pass
    
    @abstractmethod
    def find_routes_avoiding_station(self, from_station: str, to_station: str,
                                   avoid_station: str) -> List[Route]:
        """
        Find routes that avoid a specific station.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            avoid_station: Station to avoid
            
        Returns:
            List of Route objects avoiding the specified station
        """
        pass
    
    @abstractmethod
    def find_routes_on_line(self, from_station: str, to_station: str,
                           line_name: str) -> List[Route]:
        """
        Find routes that use a specific railway line.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            line_name: Railway line to use
            
        Returns:
            List of Route objects using the specified line
        """
        pass
    
    @abstractmethod
    def get_possible_destinations(self, from_station: str, 
                                max_changes: int = 3) -> List[str]:
        """
        Get all possible destinations from a given station.
        
        Args:
            from_station: Starting station name
            max_changes: Maximum number of changes allowed
            
        Returns:
            List of reachable station names
        """
        pass
    
    @abstractmethod
    def get_journey_time(self, from_station: str, to_station: str) -> Optional[int]:
        """
        Get estimated journey time between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            Journey time in minutes if calculable, None otherwise
        """
        pass
    
    @abstractmethod
    def get_distance(self, from_station: str, to_station: str) -> Optional[float]:
        """
        Get distance between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            Distance in kilometers if calculable, None otherwise
        """
        pass
    
    @abstractmethod
    def validate_route(self, route: Route) -> Tuple[bool, List[str]]:
        """
        Validate that a route is feasible and correct.
        
        Args:
            route: Route object to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        pass
    
    @abstractmethod
    def get_route_alternatives(self, route: Route, max_alternatives: int = 3,
                              preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """
        Get alternative routes similar to the given route.
        
        Args:
            route: Original route
            max_alternatives: Maximum number of alternatives
            preferences: Optional dictionary of routing preferences
            
        Returns:
            List of alternative Route objects
        """
        pass
    
    @abstractmethod
    def calculate_route_cost(self, route: Route) -> Optional[float]:
        """
        Calculate estimated cost for a route.
        
        Args:
            route: Route to calculate cost for
            
        Returns:
            Estimated cost if calculable, None otherwise
        """
        pass
    
    @abstractmethod
    def get_interchange_stations(self, from_station: str, to_station: str) -> List[str]:
        """
        Get all possible interchange stations between two stations.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            
        Returns:
            List of station names that can be used as interchanges
        """
        pass
    
    @abstractmethod
    def find_circular_routes(self, station: str, max_distance: float = 50.0) -> List[Route]:
        """
        Find circular routes starting and ending at the same station.
        
        Args:
            station: Starting/ending station name
            max_distance: Maximum distance for circular route
            
        Returns:
            List of circular Route objects
        """
        pass
    
    @abstractmethod
    def get_route_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the route network.
        
        Returns:
            Dictionary containing network statistics
        """
        pass
    
    @abstractmethod
    def clear_route_cache(self) -> None:
        """Clear any cached route calculations."""
        pass
    
    @abstractmethod
    def precompute_common_routes(self, station_pairs: List[Tuple[str, str]]) -> None:
        """
        Precompute routes for common station pairs.
        
        Args:
            station_pairs: List of (from_station, to_station) tuples
        """
        pass