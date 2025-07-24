"""
Underground Routing Handler

Handles the "black box" approach for all UK underground systems:
- London Underground (including DLR)
- Glasgow Subway
- Tyne and Wear Metro
"""

import logging
from typing import List, Optional, Set, Dict, Tuple
from pathlib import Path
import json

from ..interfaces.i_data_repository import IDataRepository
from ..models.route import Route, RouteSegment


class UndergroundRoutingHandler:
    """Handles black box routing logic for all UK underground systems."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the underground routing handler.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        
        # Cache for underground station data
        self._london_underground_stations: Optional[Set[str]] = None
        self._glasgow_subway_stations: Optional[Set[str]] = None
        self._tyne_wear_metro_stations: Optional[Set[str]] = None
        
        # Cache for system metadata
        self._underground_systems: Optional[Dict[str, Dict]] = None
    
    def load_underground_systems(self) -> Dict[str, Dict]:
        """Load all underground systems data from properly structured JSON file."""
        if self._underground_systems is not None:
            return self._underground_systems
        
        self._underground_systems = {}
        
        # Load all UK underground stations from properly structured file
        uk_underground_data = self._load_system_data("uk_underground_stations.json", "UK Underground Systems")
        if uk_underground_data:
            # Extract each system from the structured JSON
            london_data = uk_underground_data.get("London Underground", {})
            glasgow_data = uk_underground_data.get("Glasgow Subway", {})
            tyne_wear_data = uk_underground_data.get("Tyne and Wear Metro", {})
            
            # Create system data structures using the JSON data
            if london_data:
                london_stations = set(london_data.get("stations", []))
                self._underground_systems["london"] = {
                    "metadata": {
                        "system": london_data.get("system_name", "London Underground"),
                        "operator": london_data.get("operator", "Transport for London")
                    },
                    "stations": list(london_stations),
                    "terminals": london_data.get("terminals", [])
                }
                self._london_underground_stations = london_stations
            
            if glasgow_data:
                glasgow_stations = set(glasgow_data.get("stations", []))
                self._underground_systems["glasgow"] = {
                    "metadata": {
                        "system": glasgow_data.get("system_name", "Glasgow Subway"),
                        "operator": glasgow_data.get("operator", "Strathclyde Partnership for Transport")
                    },
                    "stations": list(glasgow_stations),
                    "terminals": glasgow_data.get("terminals", [])
                }
                self._glasgow_subway_stations = glasgow_stations
            
            if tyne_wear_data:
                tyne_wear_stations = set(tyne_wear_data.get("stations", []))
                self._underground_systems["tyne_wear"] = {
                    "metadata": {
                        "system": tyne_wear_data.get("system_name", "Tyne and Wear Metro"),
                        "operator": tyne_wear_data.get("operator", "Nexus")
                    },
                    "stations": list(tyne_wear_stations),
                    "terminals": tyne_wear_data.get("terminals", [])
                }
                self._tyne_wear_metro_stations = tyne_wear_stations
        
        return self._underground_systems
    
    def _load_system_data(self, filename: str, system_name: str) -> Optional[Dict]:
        """Load data for a specific underground system."""
        try:
            # Try multiple possible paths
            possible_paths = [
                Path(f"data/{filename}"),  # From src directory
                Path(f"src/data/{filename}"),  # From project root
                Path(__file__).parent.parent.parent / "data" / filename,  # Relative to this file
            ]
            
            system_file = None
            for path in possible_paths:
                if path.exists():
                    system_file = path
                    break
            
            if not system_file:
                self.logger.warning(f"{system_name} stations file not found: {filename}")
                return None
            
            with open(system_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stations = data.get('stations', [])
            self.logger.info(f"Loaded {len(stations)} {system_name} stations")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load {system_name} stations: {e}")
            return None
    
    def load_london_underground_stations(self) -> Set[str]:
        """Load the list of London Underground stations from JSON file."""
        if self._london_underground_stations is not None:
            return self._london_underground_stations
        
        self.load_underground_systems()
        return self._london_underground_stations or set()
    
    def load_glasgow_subway_stations(self) -> Set[str]:
        """Load the list of Glasgow Subway stations from JSON file."""
        if self._glasgow_subway_stations is not None:
            return self._glasgow_subway_stations
        
        self.load_underground_systems()
        return self._glasgow_subway_stations or set()
    
    def load_tyne_wear_metro_stations(self) -> Set[str]:
        """Load the list of Tyne and Wear Metro stations from JSON file."""
        if self._tyne_wear_metro_stations is not None:
            return self._tyne_wear_metro_stations
        
        self.load_underground_systems()
        return self._tyne_wear_metro_stations or set()
    
    def get_underground_system(self, station_name: str) -> Optional[Tuple[str, str]]:
        """
        Determine which underground system a station belongs to.
        
        Args:
            station_name: The station name to check
            
        Returns:
            Tuple of (system_key, system_name) if found, None otherwise
        """
        # Check London Underground first (most comprehensive)
        if self.is_london_underground_station(station_name):
            return ("london", "London Underground")
        
        # Check Glasgow Subway
        if self.is_glasgow_subway_station(station_name):
            return ("glasgow", "Glasgow Subway")
        
        # Check Tyne and Wear Metro
        if self.is_tyne_wear_metro_station(station_name):
            return ("tyne_wear", "Tyne and Wear Metro")
        
        return None
    
    def is_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is part of any UK underground system.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is part of any underground system, False otherwise
        """
        return self.get_underground_system(station_name) is not None
    
    def is_london_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is a London Underground station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London Underground station, False otherwise
        """
        underground_stations = self.load_london_underground_stations()
        return self._check_station_match(station_name, underground_stations, "london")
    
    def is_glasgow_subway_station(self, station_name: str) -> bool:
        """
        Check if a station is a Glasgow Subway station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a Glasgow Subway station, False otherwise
        """
        subway_stations = self.load_glasgow_subway_stations()
        return self._check_station_match(station_name, subway_stations, "glasgow")
    
    def is_tyne_wear_metro_station(self, station_name: str) -> bool:
        """
        Check if a station is a Tyne and Wear Metro station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a Tyne and Wear Metro station, False otherwise
        """
        metro_stations = self.load_tyne_wear_metro_stations()
        return self._check_station_match(station_name, metro_stations, "tyne_wear")
    
    def _check_station_match(self, station_name: str, system_stations: Set[str], system_key: str) -> bool:
        """
        Check if a station name matches any station in the given system.
        
        Args:
            station_name: The station name to check
            system_stations: Set of stations in the system
            system_key: Key identifying the system for specific logic
            
        Returns:
            True if the station matches, False otherwise
        """
        # Check exact match first
        if station_name in system_stations:
            return True
        
        # System-specific normalization
        if system_key == "london":
            return self._check_london_variations(station_name, system_stations)
        elif system_key == "glasgow":
            return self._check_glasgow_variations(station_name, system_stations)
        elif system_key == "tyne_wear":
            return self._check_tyne_wear_variations(station_name, system_stations)
        
        # Generic punctuation handling
        return self._check_generic_variations(station_name, system_stations)
    
    def _check_london_variations(self, station_name: str, underground_stations: Set[str]) -> bool:
        """Handle London-specific station name variations."""
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
        
        return self._check_generic_variations(station_name, underground_stations)
    
    def _check_glasgow_variations(self, station_name: str, subway_stations: Set[str]) -> bool:
        """Handle Glasgow-specific station name variations."""
        # Handle "Glasgow Central" -> "St Enoch" interchange mapping
        if "glasgow central" in station_name.lower():
            return "St Enoch" in subway_stations
        elif "glasgow queen street" in station_name.lower():
            return "Buchanan Street" in subway_stations
        
        return self._check_generic_variations(station_name, subway_stations)
    
    def _check_tyne_wear_variations(self, station_name: str, metro_stations: Set[str]) -> bool:
        """Handle Tyne and Wear Metro-specific station name variations."""
        # Handle "Newcastle" -> "Central Station" mapping
        if station_name.lower() in ["newcastle", "newcastle central"]:
            return "Central Station" in metro_stations
        
        return self._check_generic_variations(station_name, metro_stations)
    
    def _check_generic_variations(self, station_name: str, system_stations: Set[str]) -> bool:
        """Handle generic station name variations (punctuation, etc.)."""
        # Handle apostrophe and period variations
        # Remove apostrophes and periods for comparison
        clean_name = station_name.replace("'", "").replace(".", "")
        if clean_name in system_stations:
            return True
        
        # Try adding/removing common punctuation
        for station in system_stations:
            clean_station = station.replace("'", "").replace(".", "")
            if clean_name == clean_station:
                return True
        
        return False
    
    def is_underground_only_station(self, station_name: str) -> bool:
        """
        Check if a station is underground-only (no National Rail services).
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is underground-only, False otherwise
        """
        # Check if it's an underground station in any system
        if not self.is_underground_station(station_name):
            return False
        
        # Check if it also has National Rail services
        # If the station exists in our railway lines data, it has National Rail services
        all_stations = self.data_repository.get_all_station_names()
        return station_name not in all_stations
    
    def is_mixed_station(self, station_name: str) -> bool:
        """
        Check if a station serves both underground and National Rail.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station serves both underground and National Rail, False otherwise
        """
        # Must be both an underground station AND in our railway lines data
        return (self.is_underground_station(station_name) and
                self.data_repository.validate_station_exists(station_name))
    
    def get_system_terminals(self, system_key: str) -> List[str]:
        """
        Get the list of terminal stations for a specific underground system.
        
        Args:
            system_key: The system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            List of terminal station names
        """
        systems = self.load_underground_systems()
        system_data = systems.get(system_key, {})
        
        if system_key == "london":
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
        else:
            return system_data.get('terminals', [])
    
    def get_london_terminals(self) -> List[str]:
        """
        Get the list of major London terminal stations that serve National Rail.
        
        Returns:
            List of London terminal station names
        """
        return self.get_system_terminals("london")
    
    def is_system_terminal(self, station_name: str, system_key: str) -> bool:
        """
        Check if a station is a terminal for a specific underground system.
        
        Args:
            station_name: The station name to check
            system_key: The system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            True if the station is a terminal for the system, False otherwise
        """
        terminals = self.get_system_terminals(system_key)
        return station_name in terminals
    
    def is_london_terminal(self, station_name: str) -> bool:
        """
        Check if a station is a major London terminal.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London terminal, False otherwise
        """
        return self.is_system_terminal(station_name, "london")
    
    def is_terminal_station(self, station_name: str) -> bool:
        """
        Check if a station is a terminal for any underground system.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a terminal, False otherwise
        """
        system_info = self.get_underground_system(station_name)
        if not system_info:
            return False
        
        system_key, _ = system_info
        return self.is_system_terminal(station_name, system_key)
    
    def should_use_black_box_routing(self, from_station: str, to_station: str) -> bool:
        """
        Determine if black box routing should be used for a journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            True if black box routing should be used, False otherwise
        """
        from_system = self.get_underground_system(from_station)
        to_system = self.get_underground_system(to_station)
        
        from_is_underground = from_system is not None
        to_is_underground = to_system is not None
        
        # If destination is a terminal that serves National Rail, prefer National Rail
        if to_is_underground and self.is_terminal_station(to_station):
            # Check if there's a direct National Rail connection
            if self.data_repository.validate_station_exists(from_station) and self.data_repository.validate_station_exists(to_station):
                # Both stations exist in National Rail network, prefer National Rail routing
                system_key, system_name = to_system
                self.logger.info(f"Preferring National Rail routing: {to_station} is a {system_name} terminal with National Rail services")
                return False
        
        # Use black box routing if:
        # 1. Both stations are underground stations (underground-to-underground routes)
        # 2. The destination is underground-only (not a mixed terminal)
        # 3. The origin is underground-only and destination is not underground (underground-to-national-rail routes)
        if to_is_underground:
            if from_is_underground:
                from_system_key, from_system_name = from_system
                to_system_key, to_system_name = to_system
                
                # Only use black box routing if both stations are from the same underground system
                if from_system_key == to_system_key:
                    self.logger.info(f"Using black box routing: {from_station} ({from_system_name}) to {to_station} ({to_system_name})")
                    return True
                else:
                    self.logger.info(f"Cannot use black box routing: {from_station} ({from_system_name}) and {to_station} ({to_system_name}) are from different underground systems")
                    return False
            elif self.is_underground_only_station(to_station):
                to_system_name = to_system[1]
                self.logger.info(f"Using black box routing: destination {to_station} is {to_system_name}-only station")
                return True
            else:
                to_system_name = to_system[1]
                self.logger.info(f"Preferring National Rail routing: destination {to_station} serves both {to_system_name} and National Rail")
                return False
        
        # Handle underground-to-national-rail routes
        if from_is_underground and not to_is_underground:
            # Check if origin is underground-only or if we should route via terminus
            if self.is_underground_only_station(from_station):
                from_system_name = from_system[1]
                self.logger.info(f"Using black box routing: origin {from_station} is {from_system_name}-only, routing via terminus to {to_station}")
                return True
            else:
                # Mixed station origin - check if destination exists in National Rail network
                if self.data_repository.validate_station_exists(to_station):
                    from_system_name = from_system[1]
                    self.logger.info(f"Using black box routing: routing from {from_system_name} station {from_station} via terminus to {to_station}")
                    return True
        
        return False
    
    def create_black_box_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a black box route for underground journeys.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            A Route object with black box underground segment, or None if not applicable
        """
        if not self.should_use_black_box_routing(from_station, to_station):
            return None
        
        # Determine which underground system to use
        from_system = self.get_underground_system(from_station)
        to_system = self.get_underground_system(to_station)
        
        # Use the destination system if available, otherwise use the origin system
        system_info = to_system or from_system
        if not system_info:
            return None
        
        system_key, system_name = system_info
        
        # Create a single segment representing the underground journey
        segment = RouteSegment(
            from_station=from_station,
            to_station=to_station,
            line_name=system_name,
            distance_km=self._estimate_underground_distance(from_station, to_station, system_key),
            journey_time_minutes=self._estimate_underground_time(from_station, to_station, system_key),
            service_pattern="UNDERGROUND",
            train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE"
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
        
        self.logger.info(f"Created black box {system_name} route: {from_station} -> {to_station}")
        return route
    
    def create_multi_system_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a multi-system route connecting different underground systems via National Rail.
        
        Args:
            from_station: Starting station (underground station)
            to_station: Destination station (different underground system)
            
        Returns:
            A Route object with multiple segments, or None if not applicable
        """
        from_system = self.get_underground_system(from_station)
        to_system = self.get_underground_system(to_station)
        
        # Only create multi-system routes if both stations are underground but from different systems
        if not (from_system and to_system and from_system[0] != to_system[0]):
            return None
        
        from_system_key, from_system_name = from_system
        to_system_key, to_system_name = to_system
        
        self.logger.info(f"Creating multi-system route: {from_station} ({from_system_name}) to {to_station} ({to_system_name})")
        
        # Get appropriate terminals for each system
        from_terminals = self.get_nearest_terminals(from_station)
        to_terminals = self.get_nearest_terminals(to_station)
        
        # Find the best terminal pair that exists in National Rail network
        best_from_terminal = None
        best_to_terminal = None
        
        for from_terminal in from_terminals:
            if self.data_repository.validate_station_exists(from_terminal):
                for to_terminal in to_terminals:
                    if self.data_repository.validate_station_exists(to_terminal):
                        best_from_terminal = from_terminal
                        best_to_terminal = to_terminal
                        break
                if best_from_terminal:
                    break
        
        if not (best_from_terminal and best_to_terminal):
            self.logger.warning(f"No suitable terminals found for multi-system route: {from_station} to {to_station}")
            return None
        
        segments = []
        total_distance = 0
        total_time = 0
        
        # Segment 1: Underground from origin to terminal
        if from_station != best_from_terminal:
            underground_segment1 = RouteSegment(
                from_station=from_station,
                to_station=best_from_terminal,
                line_name=from_system_name,
                distance_km=self._estimate_underground_distance(from_station, best_from_terminal, from_system_key),
                journey_time_minutes=self._estimate_underground_time(from_station, best_from_terminal, from_system_key),
                service_pattern="UNDERGROUND",
                train_service_id=f"{from_system_key.upper()}_UNDERGROUND_SERVICE"
            )
            segments.append(underground_segment1)
            total_distance += underground_segment1.distance_km or 0
            total_time += underground_segment1.journey_time_minutes or 0
        
        # Segment 2: National Rail between terminals
        if best_from_terminal != best_to_terminal:
            rail_distance = self._estimate_national_rail_distance(best_from_terminal, best_to_terminal)
            rail_time = self._estimate_national_rail_time(best_from_terminal, best_to_terminal)
            
            rail_segment = RouteSegment(
                from_station=best_from_terminal,
                to_station=best_to_terminal,
                line_name="National Rail",
                distance_km=rail_distance,
                journey_time_minutes=rail_time,
                service_pattern="NATIONAL_RAIL",
                train_service_id="NATIONAL_RAIL_SERVICE"
            )
            segments.append(rail_segment)
            total_distance += rail_segment.distance_km or 0
            total_time += rail_segment.journey_time_minutes or 0
        
        # Segment 3: Underground from terminal to destination
        if best_to_terminal != to_station:
            underground_segment2 = RouteSegment(
                from_station=best_to_terminal,
                to_station=to_station,
                line_name=to_system_name,
                distance_km=self._estimate_underground_distance(best_to_terminal, to_station, to_system_key),
                journey_time_minutes=self._estimate_underground_time(best_to_terminal, to_station, to_system_key),
                service_pattern="UNDERGROUND",
                train_service_id=f"{to_system_key.upper()}_UNDERGROUND_SERVICE"
            )
            segments.append(underground_segment2)
            total_distance += underground_segment2.distance_km or 0
            total_time += underground_segment2.journey_time_minutes or 0
        
        # Add interchange time (5 minutes per change)
        changes_required = len(segments) - 1
        total_time += changes_required * 5
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=segments,
            total_distance_km=total_distance,
            total_journey_time_minutes=total_time,
            changes_required=changes_required,
            full_path=[from_station] + [seg.to_station for seg in segments]
        )
        
        self.logger.info(f"Created multi-system route: {from_station} -> {best_from_terminal} -> {best_to_terminal} -> {to_station}")
        return route
    
    def _estimate_national_rail_distance(self, from_station: str, to_station: str) -> float:
        """Estimate distance for National Rail segment between terminals."""
        # Rough estimates based on major UK city distances
        distance_map = {
            ("London", "Glasgow"): 650,
            ("London", "Newcastle"): 450,
            ("Glasgow", "Newcastle"): 250,
        }
        
        # Determine cities
        from_city = "London" if "London" in from_station else ("Glasgow" if any(term in from_station for term in ["Glasgow", "Buchanan", "St Enoch"]) else "Newcastle")
        to_city = "London" if "London" in to_station else ("Glasgow" if any(term in to_station for term in ["Glasgow", "Buchanan", "St Enoch"]) else "Newcastle")
        
        # Look up distance
        key = (from_city, to_city) if from_city <= to_city else (to_city, from_city)
        return distance_map.get(key, 400)  # Default 400km
    
    def _estimate_national_rail_time(self, from_station: str, to_station: str) -> int:
        """Estimate journey time for National Rail segment between terminals."""
        distance = self._estimate_national_rail_distance(from_station, to_station)
        # Average speed for long-distance rail: 100-120 km/h
        base_time = (distance / 110) * 60  # Convert to minutes
        return int(base_time)
    
    def get_nearest_terminals(self, station_name: str) -> List[str]:
        """
        Get the nearest terminals to a given station based on its underground system.
        
        Args:
            station_name: The station name
            
        Returns:
            List of nearest terminal stations (ordered by preference)
        """
        system_info = self.get_underground_system(station_name)
        
        if not system_info:
            # Not an underground station, return London terminals as default
            return self.get_london_terminals()[:6]  # Top 6 London terminals
        
        system_key, system_name = system_info
        terminals = self.get_system_terminals(system_key)
        
        # For multi-system routing, we need National Rail terminals, not underground terminals
        # So we skip the check for underground terminals and go directly to system-specific logic
        
        if system_key == "london":
            # For London Underground stations
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
            else:
                # For mixed stations, return terminals that are likely to be well-connected
                return [
                    "London Waterloo",
                    "London Liverpool Street",
                    "London Victoria",
                    "London Paddington"
                ]
        elif system_key == "glasgow":
            # For Glasgow Subway, return National Rail interchange terminals
            return ["Glasgow Central", "Glasgow Queen Street", "Partick"]
        elif system_key == "tyne_wear":
            # For Tyne and Wear Metro, return main terminals
            return ["Central Station", "Sunderland", "South Shields", "Airport"]
        else:
            # Fallback to all terminals for the system
            return terminals
    
    def filter_underground_stations_from_path(self, path: List[str]) -> List[str]:
        """
        Filter out underground-only stations from a path, keeping only terminals and mixed stations.
        
        Args:
            path: List of station names in the path
            
        Returns:
            Filtered path with underground-only stations removed
        """
        filtered_path = []
        
        for station in path:
            # Keep the station if it's:
            # 1. Not an underground station at all
            # 2. A terminal station for any underground system
            # 3. A mixed station (serves both underground and National Rail)
            if (not self.is_underground_station(station) or
                self.is_terminal_station(station) or
                self.is_mixed_station(station)):
                filtered_path.append(station)
            else:
                system_info = self.get_underground_system(station)
                system_name = system_info[1] if system_info else "underground"
                self.logger.debug(f"Filtered out {system_name}-only station: {station}")
        
        return filtered_path
    
    def enhance_route_with_black_box(self, route: Route) -> Route:
        """
        Enhance a route by replacing underground segments with black box representation.
        
        Args:
            route: The route to enhance
            
        Returns:
            Enhanced route with black box underground segments
        """
        enhanced_segments = []
        
        for segment in route.segments:
            # Check if this segment involves underground-only stations
            from_underground_only = self.is_underground_only_station(segment.from_station)
            to_underground_only = self.is_underground_only_station(segment.to_station)
            
            if from_underground_only or to_underground_only:
                # Determine which underground system to use
                from_system = self.get_underground_system(segment.from_station)
                to_system = self.get_underground_system(segment.to_station)
                
                # Use the destination system if available, otherwise use the origin system
                system_info = to_system or from_system
                if system_info:
                    system_key, system_name = system_info
                    
                    # Replace with black box segment
                    black_box_segment = RouteSegment(
                        from_station=segment.from_station,
                        to_station=segment.to_station,
                        line_name=system_name,
                        distance_km=segment.distance_km,
                        journey_time_minutes=segment.journey_time_minutes,
                        service_pattern="UNDERGROUND",
                        train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE"
                    )
                    enhanced_segments.append(black_box_segment)
                    self.logger.debug(f"Replaced segment with {system_name} black box: {segment.from_station} -> {segment.to_station}")
                else:
                    # Fallback to original segment if no system found
                    enhanced_segments.append(segment)
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
    
    def _estimate_underground_distance(self, from_station: str, to_station: str, system_key: str = "london") -> float:
        """
        Estimate the distance for an underground journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            system_key: The underground system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            Estimated distance in kilometers
        """
        if system_key == "glasgow":
            # Glasgow Subway is a small circular system
            return 3.0  # Average journey on Glasgow Subway: 2-4km
        elif system_key == "tyne_wear":
            # Tyne and Wear Metro covers a larger area
            return 8.0  # Average journey on Tyne and Wear Metro: 5-12km
        else:
            # London Underground distance estimation based on geography
            
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
    
    def _estimate_underground_time(self, from_station: str, to_station: str, system_key: str = "london") -> int:
        """
        Estimate the journey time for an underground journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            system_key: The underground system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            Estimated journey time in minutes
        """
        # Estimate based on distance
        distance = self._estimate_underground_distance(from_station, to_station, system_key)
        
        if system_key == "glasgow":
            # Glasgow Subway is frequent but smaller network
            # Average speed about 15-20 km/h including stops
            base_time = (distance / 18) * 60  # Convert to minutes
            estimated_time = max(5, min(20, int(base_time)))  # Between 5-20 minutes
        elif system_key == "tyne_wear":
            # Tyne and Wear Metro covers larger distances
            # Average speed about 25-30 km/h including stops
            base_time = (distance / 27) * 60  # Convert to minutes
            # Add time for potential changes
            if distance > 8:
                base_time += 3  # 3 minutes for one change
            estimated_time = max(8, min(35, int(base_time)))  # Between 8-35 minutes
        else:
            # London Underground
            # Average speed is about 20-25 km/h including stops
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
        Get statistics about all UK underground networks.
        
        Returns:
            Dictionary with underground network statistics
        """
        systems = self.load_underground_systems()
        all_stations = set(self.data_repository.get_all_station_names())
        
        stats = {
            "black_box_enabled": True,
            "systems": {}
        }
        
        total_underground_stations = 0
        total_underground_only = 0
        total_mixed_stations = 0
        total_terminals = 0
        
        for system_key, system_data in systems.items():
            system_stations = set(system_data.get('stations', []))
            system_terminals = system_data.get('terminals', [])
            
            # Count different types of stations for this system
            underground_only = 0
            mixed_stations = 0
            terminals = 0
            
            for station in system_stations:
                if station in all_stations:
                    mixed_stations += 1
                    if station in system_terminals:
                        terminals += 1
                else:
                    underground_only += 1
            
            system_name = system_data.get('metadata', {}).get('system', system_key.replace('_', ' ').title())
            
            stats["systems"][system_key] = {
                "name": system_name,
                "total_stations": len(system_stations),
                "underground_only_stations": underground_only,
                "mixed_stations": mixed_stations,
                "terminals": terminals
            }
            
            # Add to totals
            total_underground_stations += len(system_stations)
            total_underground_only += underground_only
            total_mixed_stations += mixed_stations
            total_terminals += terminals
        
        # Add overall totals
        stats.update({
            "total_underground_stations": total_underground_stations,
            "total_underground_only_stations": total_underground_only,
            "total_mixed_stations": total_mixed_stations,
            "total_terminals": total_terminals
        })
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear any cached underground station data for all systems."""
        self._london_underground_stations = None
        self._glasgow_subway_stations = None
        self._tyne_wear_metro_stations = None
        self._underground_systems = None
        self.logger.info("Underground routing handler cache cleared for all systems")