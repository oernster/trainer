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
        
        # Check exact match first
        if station_name in underground_stations:
            return True
        
        # Try normalized variations for London terminals
        # Handle "London Liverpool Street" -> "Liverpool Street" etc.
        normalized_name = station_name
        if normalized_name.startswith("London "):
            normalized_name = normalized_name[7:]  # Remove "London " prefix
            if normalized_name in underground_stations:
                return True
        
        # Handle common station name variations
        # King's Cross St. Pancras variations
        if "king" in station_name.lower() and ("cross" in station_name.lower() or "pancras" in station_name.lower()):
            # Try "Kings Cross St Pancras" (the version in our JSON)
            if "Kings Cross St Pancras" in underground_stations:
                return True
        
        # Handle apostrophe and period variations
        # Remove apostrophes and periods for comparison
        clean_name = station_name.replace("'", "").replace(".", "")
        if clean_name in underground_stations:
            return True
        
        # Try adding/removing common punctuation
        for station in underground_stations:
            clean_station = station.replace("'", "").replace(".", "")
            if clean_name == clean_station:
                return True
        
        return False
    
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
        from_is_underground = self.is_london_underground_station(from_station)
        to_is_underground = self.is_london_underground_station(to_station)
        
        # If destination is a London terminal that serves National Rail, prefer National Rail
        if self.is_london_terminal(to_station):
            # Check if there's a direct National Rail connection
            if self.data_repository.validate_station_exists(from_station) and self.data_repository.validate_station_exists(to_station):
                # Both stations exist in National Rail network, prefer National Rail routing
                self.logger.info(f"Preferring National Rail routing: {to_station} is a London terminal with National Rail services")
                return False
        
        # Use black box routing if:
        # 1. Both stations are Underground stations (underground-to-underground routes)
        # 2. The destination is Underground-only (not a mixed terminal)
        if to_is_underground:
            if from_is_underground:
                self.logger.info(f"Using black box routing: both {from_station} and {to_station} are Underground stations")
                return True
            elif self.is_underground_only_station(to_station):
                self.logger.info(f"Using black box routing: destination {to_station} is Underground-only station")
                return True
            else:
                self.logger.info(f"Preferring National Rail routing: destination {to_station} serves both Underground and National Rail")
                return False
        
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
            service_pattern="UNDERGROUND",
            train_service_id="LONDON_UNDERGROUND_SERVICE"
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
                    service_pattern="UNDERGROUND",
                    train_service_id="LONDON_UNDERGROUND_SERVICE"
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
        # More realistic distance estimation based on London geography
        
        # Central London stations (Zone 1)
        central_london_indicators = [
            "Central", "City", "Covent Garden", "Oxford", "Piccadilly", "Leicester",
            "Charing Cross", "Westminster", "Victoria", "Liverpool Street", "Kings Cross",
            "Euston", "Paddington", "Waterloo", "London Bridge", "Bank", "Monument"
        ]
        
        # Inner London stations (Zones 2-3)
        inner_london_indicators = [
            "Clapham", "Camden", "Islington", "Hammersmith", "Kensington", "Chelsea",
            "Canary Wharf", "Greenwich", "Wimbledon"
        ]
        
        # Outer London stations (Zones 4-6)
        outer_london_indicators = [
            "Heathrow", "Stanmore", "Epping", "Upminster", "Croydon", "Richmond"
        ]
        
        def get_zone(station_name):
            if any(indicator in station_name for indicator in central_london_indicators):
                return 1  # Central London
            elif any(indicator in station_name for indicator in inner_london_indicators):
                return 2  # Inner London
            elif any(indicator in station_name for indicator in outer_london_indicators):
                return 3  # Outer London
            else:
                return 2  # Default to inner London
        
        from_zone = get_zone(from_station)
        to_zone = get_zone(to_station)
        
        # Distance estimation based on zones
        if from_zone == 1 and to_zone == 1:
            return 2.5  # Central to central: 2-3km
        elif (from_zone == 1 and to_zone == 2) or (from_zone == 2 and to_zone == 1):
            return 5.0  # Central to inner: 4-6km
        elif from_zone == 2 and to_zone == 2:
            return 7.0  # Inner to inner: 6-8km
        elif (from_zone <= 2 and to_zone == 3) or (from_zone == 3 and to_zone <= 2):
            return 12.0  # Inner/central to outer: 10-15km
        else:
            return 15.0  # Outer to outer: 12-18km
    
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
        
        # Realistic Underground time estimates (10-40 minutes):
        # - Short journeys: 10-15 minutes
        # - Medium journeys: 15-25 minutes
        # - Long journeys: 25-40 minutes
        
        estimated_time = max(10, min(40, int(base_time)))  # Between 10-40 minutes
        return estimated_time
    
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