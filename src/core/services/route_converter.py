"""
Route Converter

Handles converting PathNode objects to Route objects and managing intermediate stations.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from ..interfaces.i_data_repository import IDataRepository
from ..models.route import Route, RouteSegment
from .pathfinding_algorithm import PathNode


class RouteConverter:
    """Converts PathNode objects to Route objects with enhanced intermediate stations."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the route converter.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
    
    def path_to_route(self, path_node: PathNode, graph: Dict) -> Route:
        """Convert a PathNode to a Route object."""
        if len(path_node.path) < 2:
            raise ValueError("Path must have at least 2 stations")
        
        segments = []
        current_line = None
        segment_start_idx = 0
        
        # Group consecutive stations on the same line into segments
        for i in range(len(path_node.lines_used)):
            line = path_node.lines_used[i]
            
            if current_line != line:
                # Start new segment
                if current_line is not None:
                    # Finish previous segment - include all stations in between
                    segment_from = path_node.path[segment_start_idx]
                    segment_to = path_node.path[i]
                    
                    # Calculate segment distance and time from the full path
                    segment_distance = 0.0
                    segment_time = 0
                    is_walking_segment = (current_line == 'WALKING')
                    
                    # Sum up distances and times for all hops in this segment
                    for j in range(segment_start_idx, i):
                        hop_from = path_node.path[j]
                        hop_to = path_node.path[j + 1]
                        
                        # Get distance from network graph
                        if hop_from in graph and hop_to in graph[hop_from]:
                            connections = graph[hop_from][hop_to]
                            if connections:
                                # Find connection for this line
                                line_connection = next((c for c in connections if c['line'] == current_line), connections[0])
                                # Use the actual time for the segment (not the penalized time)
                                segment_time += line_connection.get('time', 0)
                                segment_distance += line_connection.get('distance', 0)
                                
                                # Check if this connection is marked as walking
                                if (line_connection.get('is_walking_connection', False) or
                                    line_connection.get('line') == 'WALKING' or
                                    current_line == 'WALKING'):
                                    is_walking_segment = True
                                    self.logger.debug(f"Marking segment as walking: {hop_from} -> {hop_to} (line: {current_line})")
                    
                    segment = RouteSegment(
                        from_station=segment_from,
                        to_station=segment_to,
                        line_name=current_line,
                        distance_km=segment_distance,
                        journey_time_minutes=segment_time,
                        service_pattern="WALKING" if is_walking_segment else None
                    )
                    
                    segments.append(segment)
                
                current_line = line
                segment_start_idx = i
        
        # Add final segment
        if current_line is not None:
            segment_from = path_node.path[segment_start_idx]
            segment_to = path_node.path[-1]
            
            # Calculate distance and time for final segment
            segment_distance = 0.0
            segment_time = 0
            is_walking_segment = (current_line == 'WALKING')
            
            # Sum up distances and times for all hops in this final segment
            for j in range(segment_start_idx, len(path_node.path) - 1):
                hop_from = path_node.path[j]
                hop_to = path_node.path[j + 1]
                
                # Get distance from network graph
                if hop_from in graph and hop_to in graph[hop_from]:
                    connections = graph[hop_from][hop_to]
                    if connections:
                        # Find connection for this line
                        line_connection = next((c for c in connections if c['line'] == current_line), connections[0])
                        # Use the actual time for the segment (not the penalized time)
                        segment_time += line_connection.get('time', 0)
                        segment_distance += line_connection.get('distance', 0)
                        
                        # Check if this connection is marked as walking
                        if (line_connection.get('is_walking_connection', False) or
                            line_connection.get('line') == 'WALKING' or
                            current_line == 'WALKING'):
                            is_walking_segment = True
                            self.logger.debug(f"Marking final segment as walking: {hop_from} -> {hop_to} (line: {current_line})")
            
            segment = RouteSegment(
                from_station=segment_from,
                to_station=segment_to,
                line_name=current_line,
                distance_km=segment_distance,
                journey_time_minutes=segment_time,
                service_pattern="WALKING" if is_walking_segment else None
            )
            
            segments.append(segment)
        
        # Enhance segments with intermediate stations from railway line data
        enhanced_segments = []
        for segment in segments:
            enhanced_segment = self.enhance_segment_with_intermediate_stations(segment)
            enhanced_segments.append(enhanced_segment)
        
        # Create enhanced full path with all intermediate stations
        enhanced_full_path = self.create_enhanced_full_path(enhanced_segments)
        
        # Create route with enhanced intermediate stations calculation
        route = Route(
            from_station=path_node.path[0],
            to_station=path_node.path[-1],
            segments=enhanced_segments,
            total_distance_km=path_node.distance,
            total_journey_time_minutes=path_node.time,
            changes_required=path_node.changes,
            full_path=enhanced_full_path  # Use enhanced path with all intermediate stations
        )
        
        return route
    
    def enhance_segment_with_intermediate_stations(self, segment: RouteSegment) -> RouteSegment:
        """Enhance a route segment by adding intermediate stations from railway line data."""
        # Skip walking segments - they don't have intermediate stations
        if segment.service_pattern == "WALKING" or segment.line_name == "WALKING":
            return segment
        
        # Skip if from and to stations are the same
        if segment.from_station == segment.to_station:
            return segment
        
        # Try to find the railway line data for this segment
        intermediate_stations = self.get_intermediate_stations_from_line_data(
            segment.from_station, segment.to_station, segment.line_name
        )
        
        if intermediate_stations:
            self.logger.debug(f"Found {len(intermediate_stations)} intermediate stations for {segment.from_station} -> {segment.to_station} on {segment.line_name}")
            # Create a new segment - we'll store intermediate stations in the full_path instead
            # since RouteSegment doesn't have intermediate_stations parameter
            return segment
        else:
            self.logger.debug(f"No intermediate stations found for {segment.from_station} -> {segment.to_station} on {segment.line_name}")
            return segment
    
    def get_intermediate_stations_from_line_data(self, from_station: str, to_station: str, line_name: str) -> List[str]:
        """Get intermediate stations between two stations on a specific line from JSON data."""
        self.logger.debug(f"Looking for intermediate stations between {from_station} -> {to_station} on {line_name}")
        try:
            # Get line data with coordinates
            line_data = self._get_line_data_with_coordinates(line_name)
            if not line_data:
                self.logger.debug(f"No line data found for {line_name}")
                return []
            
            stations_data = line_data.get('stations', [])
            if not stations_data:
                self.logger.debug(f"No stations data found in line {line_name}")
                return []
            
            # Extract station names in order
            station_names = []
            for station_data in stations_data:
                if isinstance(station_data, dict):
                    station_name = station_data.get('name', '')
                    if station_name:
                        station_names.append(station_name)
            
            self.logger.debug(f"Found {len(station_names)} stations on {line_name}")
            
            # Find indices of from and to stations
            from_idx = None
            to_idx = None
            
            for i, station_name in enumerate(station_names):
                if station_name == from_station:
                    from_idx = i
                elif station_name == to_station:
                    to_idx = i
            
            self.logger.debug(f"Station indices - {from_station}: {from_idx}, {to_station}: {to_idx}")
            
            # If we found both stations, extract intermediate stations
            if from_idx is not None and to_idx is not None:
                # Ensure we go in the right direction
                start_idx = min(from_idx, to_idx)
                end_idx = max(from_idx, to_idx)
                
                # Get intermediate stations (excluding start and end)
                intermediate_stations = station_names[start_idx + 1:end_idx]
                
                # If we were going in reverse direction, reverse the intermediate stations
                if from_idx > to_idx:
                    intermediate_stations.reverse()
                
                self.logger.debug(f"Extracted {len(intermediate_stations)} intermediate stations for {from_station} -> {to_station} on {line_name}")
                return intermediate_stations
            else:
                self.logger.debug(f"Could not find both stations on line {line_name}")
                return []
                
        except Exception as e:
            self.logger.debug(f"Failed to get intermediate stations for {from_station} -> {to_station} on {line_name}: {e}")
            return []
    
    def create_enhanced_full_path(self, segments: List[RouteSegment]) -> List[str]:
        """Create a full path including all intermediate stations from enhanced segments."""
        self.logger.debug(f"Creating enhanced full path for {len(segments)} segments")
        if not segments:
            return []
        
        full_path = [segments[0].from_station]
        self.logger.debug(f"Starting with: {full_path}")
        
        for i, segment in enumerate(segments):
            self.logger.debug(f"Processing segment {i}: {segment.from_station} -> {segment.to_station} on {segment.line_name}")
            
            # Get intermediate stations for this segment
            intermediate_stations = self.get_intermediate_stations_from_line_data(
                segment.from_station, segment.to_station, segment.line_name
            )
            
            # Add intermediate stations if they exist
            if intermediate_stations:
                self.logger.debug(f"Adding {len(intermediate_stations)} intermediate stations")
                full_path.extend(intermediate_stations)
            else:
                self.logger.debug(f"No intermediate stations found for segment {i}")
            
            # Add the destination station
            full_path.append(segment.to_station)
            self.logger.debug(f"Path after segment {i}: {full_path}")
        
        self.logger.debug(f"Final enhanced path: {full_path}")
        return full_path
    
    def create_direct_route(self, from_station: str, to_station: str, line_name: str,
                          journey_time: int, distance: float) -> Route:
        """Create a direct route between two stations on the same line."""
        segment = RouteSegment(
            from_station=from_station,
            to_station=to_station,
            line_name=line_name,
            journey_time_minutes=journey_time,
            distance_km=distance
        )
        
        # Create full path for direct route
        full_path = [from_station, to_station]
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=[segment],
            total_journey_time_minutes=journey_time,
            total_distance_km=distance,
            changes_required=0,
            full_path=full_path
        )
        
        return route
    
    def create_interchange_route(self, from_station: str, to_station: str,
                               first_leg: Route, second_leg: Route,
                               interchange_station: str) -> Route:
        """Create a route with exactly one interchange between two stations."""
        # Combine the routes
        combined_segments = first_leg.segments + second_leg.segments
        total_time = (first_leg.total_journey_time_minutes or 0) + (second_leg.total_journey_time_minutes or 0) + 5  # 5 min interchange
        total_distance = (first_leg.total_distance_km or 0) + (second_leg.total_distance_km or 0)
        
        # Create full path for interchange route
        full_path = []
        if hasattr(first_leg, 'full_path') and first_leg.full_path:
            full_path.extend(first_leg.full_path[:-1])  # Exclude last station (interchange)
        else:
            full_path.append(from_station)
            
        if hasattr(second_leg, 'full_path') and second_leg.full_path:
            full_path.extend(second_leg.full_path)  # Include all stations from second leg
        else:
            full_path.append(interchange_station)
            full_path.append(to_station)
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=combined_segments,
            total_journey_time_minutes=total_time,
            total_distance_km=total_distance,
            changes_required=1,
            full_path=full_path
        )
        
        return route
    
    def create_via_station_route(self, from_station: str, to_station: str,
                               first_leg: Route, second_leg: Route,
                               via_station: str) -> Route:
        """Create a route that passes through a specific intermediate station."""
        # Combine the routes
        combined_segments = first_leg.segments + second_leg.segments
        total_time = (first_leg.total_journey_time_minutes or 0) + (second_leg.total_journey_time_minutes or 0)
        total_distance = (first_leg.total_distance_km or 0) + (second_leg.total_distance_km or 0)
        total_changes = first_leg.changes_required + second_leg.changes_required
        
        # Add interchange time if changing lines at via station
        if first_leg.segments and second_leg.segments:
            last_line = first_leg.segments[-1].line_name
            next_line = second_leg.segments[0].line_name
            if last_line != next_line:
                total_time += 5  # 5 minutes interchange time
                total_changes += 1
        
        # Create full path for via station route
        full_path = []
        if hasattr(first_leg, 'full_path') and first_leg.full_path:
            full_path.extend(first_leg.full_path[:-1])  # Exclude last station (via station)
        else:
            full_path.append(from_station)
            
        if hasattr(second_leg, 'full_path') and second_leg.full_path:
            full_path.extend(second_leg.full_path)  # Include all stations from second leg
        else:
            full_path.append(via_station)
            full_path.append(to_station)
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=combined_segments,
            total_journey_time_minutes=total_time,
            total_distance_km=total_distance,
            changes_required=total_changes,
            full_path=full_path
        )
        
        return route
    
    def create_circular_route(self, station: str, path: List[str], lines: List[str],
                            total_distance: float) -> Route:
        """Create a circular route starting and ending at the same station."""
        # Create route segments
        segments = []
        for i in range(len(path) - 1):
            segment = RouteSegment(
                from_station=path[i],
                to_station=path[i + 1],
                line_name=lines[i] if i < len(lines) else lines[-1]
            )
            segments.append(segment)
        
        route = Route(
            from_station=station,
            to_station=station,
            segments=segments,
            total_distance_km=total_distance,
            full_path=path  # Include the complete path
        )
        
        return route
    
    def _get_line_data_with_coordinates(self, line_name: str) -> Optional[Dict[str, Any]]:
        """Get line data with station coordinates from JSON files."""
        try:
            # Try to use data path resolver
            try:
                from ...utils.data_path_resolver import get_lines_directory
                lines_dir = get_lines_directory()
            except (ImportError, FileNotFoundError):
                # Fallback to old method
                lines_dir = Path("src/data/lines")
            
            # Convert line name to potential file name
            # Remove common suffixes and normalize
            normalized_name = line_name.lower()
            normalized_name = normalized_name.replace(" line", "").replace(" main", "").replace(" railway", "")
            normalized_name = normalized_name.replace(" ", "_").replace("-", "_")
            
            # Try different file name variations
            potential_files = [
                f"{normalized_name}.json",
                f"{normalized_name}_line.json",
                f"{normalized_name}_main_line.json",
                f"{normalized_name}_railway.json"
            ]
            
            # Also try exact match with underscores
            exact_match = line_name.lower().replace(" ", "_").replace("-", "_")
            potential_files.insert(0, f"{exact_match}.json")
            
            # Search through all JSON files if no direct match
            if not any((lines_dir / f).exists() for f in potential_files):
                for json_file in lines_dir.glob("*.json"):
                    if json_file.name.endswith('.backup'):
                        continue
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            metadata = data.get('metadata', {})
                            if metadata.get('line_name') == line_name:
                                return data
                    except Exception:
                        continue
                
                self.logger.debug(f"No file found for line: {line_name}")
                return None
            
            # Try each potential file name
            for file_name in potential_files:
                line_file = lines_dir / file_name
                if line_file.exists():
                    with open(line_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            return None
                
        except Exception as e:
            self.logger.error(f"Failed to load line data for {line_name}: {e}")
            return None