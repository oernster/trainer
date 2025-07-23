"""
Underground Routing Handler

Handles the "black box" approach for London Underground routing.
"""

import logging
from typing import List, Optional, Set
from pathlib import Path
import json

from ..interfaces.i_data_repository import IDataRepository
from ..models.route import Route, RouteSegment


class UndergroundRoutingHandler:
    """Handles London Underground black box routing logic."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the underground routing handler.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        self._london_underground_stations: Optional[Set[str]] = None
    
    def load_london_underground_stations(self) -> Set[str]:
        """Load the list of London Underground stations from JSON file."""
        if self._london_underground_stations is not None:
            return self._london_underground_stations
        
        try:
            # Try to use data path resolver
            try:
                from ...utils.data_path_resolver import get_data_file_path
                underground_file = get_data_file_path("london_underground_stations.json")
            except (ImportError, FileNotFoundError):
                # Fallback to old method
                underground_file = Path("src/data/london_underground_stations.json")
            
            if not underground_file.exists():
                self.logger.warning("London Underground stations file not found")
                self._london_underground_stations = set()
                return self._london_underground_stations
            
            with open(underground_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stations = data.get('stations', [])
            self._london_underground_stations = set(stations)
            
            self.logger.info(f"Loaded {len(self._london_underground_stations)} London Underground stations")
            return self._london_underground_stations
            
        except Exception as e:
            self.logger.error(f"Failed to load London Underground stations: {e}")
            self._london_underground_stations = set()
            return self._london_underground_stations
    
    def is_london_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is a London Underground station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London Underground station, False otherwise
        """
        underground_stations = self.load_london_underground_stations()
        return station_name in underground_stations
    
    def is_underground_only_station(self, station_name: str) -> bool:
        """
        Check if a station is Underground-only (no National Rail services).
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is Underground-only, False otherwise
        """
        # Check if it's an Underground station
        if not self.is_london_underground_station(station_name):
            return False
        
        # Check if it also has National Rail services
        # If the station exists in our railway lines data, it has National Rail services
        all_stations = self.data_repository.get_all_station_names()
        return station_name not in all_stations
    
    def is_mixed_station(self, station_name: str) -> bool:
        """
        Check if a station serves both Underground and National Rail.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station serves both Underground and National Rail, False otherwise
        """
        # Must be both an Underground station AND in our railway lines data
        return (self.is_london_underground_station(station_name) and 
                self.data_repository.validate_station_exists(station_name))
    
    def get_london_terminals(self) -> List[str]:
        """
        Get the list of major London terminal stations that serve National Rail.
        
        Returns:
            List of London terminal station names
        """
        return [
            "London Waterloo",
            "London Liverpool Street", 
            "London Victoria",
            "London Paddington",
            "London Kings Cross",
            "London St Pancras",
            "London Euston",
            "London Bridge",
            "London Charing Cross",
            "London Cannon Street",
            "London Fenchurch Street",
            "London Marylebone"
        ]
    
    def is_london_terminal(self, station_name: str) -> bool:
        """
        Check if a station is a major London terminal.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London terminal, False otherwise
        """
        terminals = self.get_london_terminals()
        return station_name in terminals
    
    def should_use_black_box_routing(self, from_station: str, to_station: str) -> bool:
        """
        Determine if black box routing should be used for a journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            True if black box routing should be used, False otherwise
        """
        # Use black box routing if both stations are in London and at least one is Underground-only
        from_is_london = "London" in from_station
        to_is_london = "London" in to_station
        
        # If both stations are in London
        if from_is_london and to_is_london:
            # Check if either is Underground-only
            from_underground_only = self.is_underground_only_station(from_station)
            to_underground_only = self.is_underground_only_station(to_station)
            
            # Use black box if either station is Underground-only
            if from_underground_only or to_underground_only:
                self.logger.info(f"Using black box routing: {from_station} -> {to_station} (Underground-only stations)")
                return True
        
        return False
    
    def create_black_box_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a black box route for Underground journeys.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            A Route object with black box Underground segment, or None if not applicable
        """
        if not self.should_use_black_box_routing(from_station, to_station):
            return None
        
        # Create a single segment representing the Underground journey
        segment = RouteSegment(
            from_station=from_station,
            to_station=to_station,
            line_name="London Underground",
            distance_km=self._estimate_underground_distance(from_station, to_station),
            journey_time_minutes=self._estimate_underground_time(from_station, to_station),
            service_pattern="UNDERGROUND"
        )
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=[segment],
            total_distance_km=segment.distance_km,
            total_journey_time_minutes=segment.journey_time_minutes,
            changes_required=0,
            full_path=[from_station, to_station]
        )
        
        self.logger.info(f"Created black box Underground route: {from_station} -> {to_station}")
        return route
    
    def get_nearest_terminals(self, station_name: str) -> List[str]:
        """
        Get the nearest London terminals to a given station.
        
        Args:
            station_name: The station name
            
        Returns:
            List of nearest terminal stations (ordered by preference)
        """
        terminals = self.get_london_terminals()
        
        # If the station is already a terminal, return it
        if station_name in terminals:
            return [station_name]
        
        # For Underground-only stations, return all terminals as they're all accessible
        if self.is_underground_only_station(station_name):
            # Return terminals in order of general preference
            return [
                "London Waterloo",
                "London Liverpool Street",
                "London Victoria", 
                "London Paddington",
                "London Kings Cross",
                "London Bridge"
            ]
        
        # For mixed stations, return terminals that are likely to be well-connected
        return [
            "London Waterloo",
            "London Liverpool Street",
            "London Victoria",
            "London Paddington"
        ]
    
    def filter_underground_stations_from_path(self, path: List[str]) -> List[str]:
        """
        Filter out Underground-only stations from a path, keeping only terminals and mixed stations.
        
        Args:
            path: List of station names in the path
            
        Returns:
            Filtered path with Underground-only stations removed
        """
        filtered_path = []
        
        for station in path:
            # Keep the station if it's:
            # 1. Not an Underground station at all
            # 2. A London terminal
            # 3. A mixed station (serves both Underground and National Rail)
            if (not self.is_london_underground_station(station) or
                self.is_london_terminal(station) or
                self.is_mixed_station(station)):
                filtered_path.append(station)
            else:
                self.logger.debug(f"Filtered out Underground-only station: {station}")
        
        return filtered_path
    
    def enhance_route_with_black_box(self, route: Route) -> Route:
        """
        Enhance a route by replacing Underground segments with black box representation.
        
        Args:
            route: The route to enhance
            
        Returns:
            Enhanced route with black box Underground segments
        """
        enhanced_segments = []
        
        for segment in route.segments:
            # Check if this segment involves Underground-only stations
            from_underground_only = self.is_underground_only_station(segment.from_station)
            to_underground_only = self.is_underground_only_station(segment.to_station)
            
            if from_underground_only or to_underground_only:
                # Replace with black box segment
                black_box_segment = RouteSegment(
                    from_station=segment.from_station,
                    to_station=segment.to_station,
                    line_name="London Underground",
                    distance_km=segment.distance_km,
                    journey_time_minutes=segment.journey_time_minutes,
                    service_pattern="UNDERGROUND"
                )
                enhanced_segments.append(black_box_segment)
                self.logger.debug(f"Replaced segment with black box: {segment.from_station} -> {segment.to_station}")
            else:
                # Keep the original segment
                enhanced_segments.append(segment)
        
        # Create enhanced route
        enhanced_route = Route(
            from_station=route.from_station,
            to_station=route.to_station,
            segments=enhanced_segments,
            total_distance_km=route.total_distance_km,
            total_journey_time_minutes=route.total_journey_time_minutes,
            changes_required=route.changes_required,
            full_path=self.filter_underground_stations_from_path(route.full_path or [])
        )
        
        return enhanced_route
    
    def _estimate_underground_distance(self, from_station: str, to_station: str) -> float:
        """
        Estimate the distance for an Underground journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            Estimated distance in kilometers
        """
        # Simple estimation based on typical Underground distances
        # This could be enhanced with actual Underground network data
        
        # If both stations are in central London, assume shorter distance
        central_london_indicators = ["Central", "City", "Covent Garden", "Oxford", "Piccadilly"]
        
        from_central = any(indicator in from_station for indicator in central_london_indicators)
        to_central = any(indicator in to_station for indicator in central_london_indicators)
        
        if from_central and to_central:
            return 3.0  # Short central London journey
        elif from_central or to_central:
            return 8.0  # One end in central London
        else:
            return 15.0  # Cross-London journey
    
    def _estimate_underground_time(self, from_station: str, to_station: str) -> int:
        """
        Estimate the journey time for an Underground journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            Estimated journey time in minutes
        """
        # Estimate based on distance
        distance = self._estimate_underground_distance(from_station, to_station)
        
        # Underground average speed is about 20-25 km/h including stops
        base_time = (distance / 22) * 60  # Convert to minutes
        
        # Add time for potential changes (assume 1 change on average for longer journeys)
        if distance > 10:
            base_time += 5  # 5 minutes for one change
        
        return max(10, int(base_time))  # Minimum 10 minutes
    
    def get_underground_statistics(self) -> dict:
        """
        Get statistics about the Underground network.
        
        Returns:
            Dictionary with Underground network statistics
        """
        underground_stations = self.load_london_underground_stations()
        all_stations = set(self.data_repository.get_all_station_names())
        
        # Count different types of stations
        underground_only = 0
        mixed_stations = 0
        terminals = 0
        
        for station in underground_stations:
            if station in all_stations:
                mixed_stations += 1
                if self.is_london_terminal(station):
                    terminals += 1
            else:
                underground_only += 1
        
        return {
            "total_underground_stations": len(underground_stations),
            "underground_only_stations": underground_only,
            "mixed_stations": mixed_stations,
            "london_terminals": terminals,
            "black_box_enabled": True
        }
    
    def clear_cache(self) -> None:
        """Clear any cached Underground station data."""
        self._london_underground_stations = None
        self.logger.info("Underground routing handler cache cleared")