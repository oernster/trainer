"""
Simple Route Finder - Emergency fallback for route finding
Author: Oliver Ernster

This is a simple, reliable route finder that bypasses complex service patterns
and provides basic route finding functionality.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

class SimpleRouteFinder:
    """Simple route finder without complex algorithms."""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.lines_dir = self.data_dir / "lines"
        self.stations = {}  # name -> code
        self.station_lines = {}  # code -> [line_names]
        self.line_stations = {}  # line_name -> [station_codes_in_order]
        self.loaded = False
    
    def load_data(self) -> bool:
        """Load basic station and line data."""
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
                station_codes = []
                
                for station_data in line_data['stations']:
                    name = station_data['name']
                    code = station_data['code']
                    
                    # Store station name -> code mapping
                    self.stations[name] = code
                    
                    # Store station -> lines mapping
                    if code not in self.station_lines:
                        self.station_lines[code] = []
                    self.station_lines[code].append(line_name)
                    
                    station_codes.append(code)
                
                # Store line -> stations mapping
                self.line_stations[line_name] = station_codes
            
            self.loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading simple route data: {e}")
            return False
    
    def find_direct_route(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Find direct route between two stations."""
        if not self.loaded:
            if not self.load_data():
                return None
        
        # Get station codes
        from_code = self.stations.get(from_station)
        to_code = self.stations.get(to_station)
        
        if not from_code or not to_code:
            return None
        
        # Find common lines
        from_lines = set(self.station_lines.get(from_code, []))
        to_lines = set(self.station_lines.get(to_code, []))
        common_lines = from_lines.intersection(to_lines)
        
        if not common_lines:
            return None
        
        # Use first common line
        line_name = list(common_lines)[0]
        line_stations = self.line_stations.get(line_name, [])
        
        try:
            from_idx = line_stations.index(from_code)
            to_idx = line_stations.index(to_code)
        except ValueError:
            return None
        
        # Build route
        if from_idx < to_idx:
            route_codes = line_stations[from_idx:to_idx + 1]
        else:
            route_codes = line_stations[to_idx:from_idx + 1]
            route_codes.reverse()
        
        # Convert codes back to names
        route_names = []
        code_to_name = {code: name for name, code in self.stations.items()}
        
        for code in route_codes:
            name = code_to_name.get(code)
            if name:
                route_names.append(name)
        
        return route_names if len(route_names) >= 2 else None

# Global instance
simple_finder = SimpleRouteFinder()