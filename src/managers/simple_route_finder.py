"""
Simple Route Finder - Emergency fallback for route finding
Author: Oliver Ernster

This is a simple, reliable route finder that bypasses complex service patterns
and provides basic route finding functionality using station names only.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

# Import data path resolver
try:
    from ..utils.data_path_resolver import get_data_directory, get_lines_directory
except ImportError:
    # Fallback if relative import fails
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.data_path_resolver import get_data_directory, get_lines_directory

class SimpleRouteFinder:
    """Simple route finder without complex algorithms, using station names only."""
    
    def __init__(self):
        try:
            self.data_dir = get_data_directory()
            self.lines_dir = get_lines_directory()
        except FileNotFoundError:
            # Fallback to old method
            self.data_dir = Path(__file__).parent.parent / "data"
            self.lines_dir = self.data_dir / "lines"
            
        self.station_lines = {}  # station_name -> [line_names]
        self.line_stations = {}  # line_name -> [station_names_in_order]
        self.loaded = False
    
    def load_data(self) -> bool:
        """Load basic station and line data using station names only."""
        try:
            # Load railway lines index
            index_file = self.data_dir / "railway_lines_index.json"
            if not index_file.exists():
                return False
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Load each line's stations
            for line_info in index_data['lines']:
                line_file = self.lines_dir / line_info['file']
                if not line_file.exists():
                    continue
                
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                line_name = line_info['name']
                station_names = []
                
                for station_data in line_data['stations']:
                    name = station_data['name']
                    
                    # Store station -> lines mapping
                    if name not in self.station_lines:
                        self.station_lines[name] = []
                    self.station_lines[name].append(line_name)
                    
                    station_names.append(name)
                
                # Store line -> stations mapping
                self.line_stations[line_name] = station_names
            
            self.loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading simple route data: {e}")
            return False
    
    def find_direct_route(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Find direct route between two stations using station names."""
        if not self.loaded:
            if not self.load_data():
                return None
        
        # Check if stations exist
        if from_station not in self.station_lines or to_station not in self.station_lines:
            return None
        
        # Find common lines
        from_lines = set(self.station_lines.get(from_station, []))
        to_lines = set(self.station_lines.get(to_station, []))
        common_lines = from_lines.intersection(to_lines)
        
        if not common_lines:
            return None
        
        # Use first common line
        line_name = list(common_lines)[0]
        line_stations = self.line_stations.get(line_name, [])
        
        try:
            from_idx = line_stations.index(from_station)
            to_idx = line_stations.index(to_station)
        except ValueError:
            return None
        
        # Build route
        if from_idx < to_idx:
            route_names = line_stations[from_idx:to_idx + 1]
        else:
            route_names = line_stations[to_idx:from_idx + 1]
            route_names.reverse()
        
        return route_names if len(route_names) >= 2 else None
    
    def get_all_stations(self) -> List[str]:
        """Get list of all station names."""
        if not self.loaded:
            if not self.load_data():
                return []
        
        return list(self.station_lines.keys())
    
    def get_lines_for_station(self, station_name: str) -> List[str]:
        """Get list of lines that serve a station."""
        if not self.loaded:
            if not self.load_data():
                return []
        
        return self.station_lines.get(station_name, [])
    
    def get_stations_on_line(self, line_name: str) -> List[str]:
        """Get list of stations on a line in order."""
        if not self.loaded:
            if not self.load_data():
                return []
        
        return self.line_stations.get(line_name, [])
    
    def find_interchange_stations(self) -> List[str]:
        """Find stations that serve multiple lines (interchange stations)."""
        if not self.loaded:
            if not self.load_data():
                return []
        
        interchange_stations = []
        for station_name, lines in self.station_lines.items():
            if len(lines) > 1:
                interchange_stations.append(station_name)
        
        return interchange_stations
    
    def find_route_with_changes(self, from_station: str, to_station: str, max_changes: int = 2) -> Optional[List[str]]:
        """Find route between stations allowing for changes at interchange stations."""
        if not self.loaded:
            if not self.load_data():
                return None
        
        # Try direct route first
        direct_route = self.find_direct_route(from_station, to_station)
        if direct_route:
            return direct_route
        
        if max_changes < 1:
            return None
        
        # Try one change via interchange stations
        interchange_stations = self.find_interchange_stations()
        
        for interchange in interchange_stations:
            # Check if we can get from origin to interchange
            route_to_interchange = self.find_direct_route(from_station, interchange)
            if not route_to_interchange:
                continue
            
            # Check if we can get from interchange to destination
            route_from_interchange = self.find_direct_route(interchange, to_station)
            if not route_from_interchange:
                continue
            
            # Combine routes, avoiding duplicate interchange station
            combined_route = route_to_interchange + route_from_interchange[1:]
            return combined_route
        
        return None

# Global instance
simple_finder = SimpleRouteFinder()