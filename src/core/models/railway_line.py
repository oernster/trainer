"""
Railway Line Model

Data model for representing railway lines using station names only.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from enum import Enum


class LineType(Enum):
    """Types of railway lines."""
    MAINLINE = "mainline"
    BRANCH = "branch"
    SUBURBAN = "suburban"
    METRO = "metro"
    HERITAGE = "heritage"
    FREIGHT = "freight"


class LineStatus(Enum):
    """Operating status of railway lines."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    SEASONAL = "seasonal"


@dataclass(frozen=True)
class RailwayLine:
    """
    Represents a railway line with its stations and properties.
    
    Uses station names only - no station codes.
    """
    
    name: str
    stations: List[str]
    line_type: LineType = LineType.MAINLINE
    status: LineStatus = LineStatus.ACTIVE
    operator: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    journey_times: Optional[Dict[str, int]] = None
    distances: Optional[Dict[str, Dict[str, float]]] = None
    service_patterns: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate railway line data."""
        if not self.name:
            raise ValueError("Line name cannot be empty")
        
        if not self.stations or len(self.stations) < 2:
            raise ValueError("Line must have at least 2 stations")
        
        # Check for duplicate stations
        if len(set(self.stations)) != len(self.stations):
            raise ValueError("Line cannot have duplicate stations")
        
        # Validate journey times if provided
        if self.journey_times:
            station_set = set(self.stations)
            for journey_key, time_value in self.journey_times.items():
                # Skip metadata entries
                if journey_key == "metadata" or not isinstance(time_value, (int, float)):
                    continue
                
                # Parse journey time key (e.g., "London Waterloo-Clapham Junction")
                if "-" in journey_key:
                    parts = journey_key.split("-", 1)  # Split on first dash only
                    if len(parts) == 2:
                        from_station = parts[0].strip()
                        to_station = parts[1].strip()
                        
                        # Only validate if both stations exist in the line
                        if from_station not in station_set:
                            raise ValueError(f"Journey time from_station '{from_station}' not in line stations")
                        if to_station not in station_set:
                            raise ValueError(f"Journey time to_station '{to_station}' not in line stations")
        
        # Validate distances if provided
        if self.distances:
            for from_station, dists in self.distances.items():
                if from_station not in self.stations:
                    raise ValueError(f"Distance from_station '{from_station}' not in line stations")
                for to_station in dists.keys():
                    if to_station not in self.stations:
                        raise ValueError(f"Distance to_station '{to_station}' not in line stations")
    
    @property
    def station_count(self) -> int:
        """Get the number of stations on this line."""
        return len(self.stations)
    
    @property
    def is_active(self) -> bool:
        """Check if this line is currently active."""
        return self.status == LineStatus.ACTIVE
    
    @property
    def is_branch_line(self) -> bool:
        """Check if this is a branch line."""
        return self.line_type == LineType.BRANCH
    
    @property
    def is_mainline(self) -> bool:
        """Check if this is a mainline."""
        return self.line_type == LineType.MAINLINE
    
    @property
    def terminus_stations(self) -> List[str]:
        """Get the terminus stations (first and last)."""
        if len(self.stations) >= 2:
            return [self.stations[0], self.stations[-1]]
        return self.stations.copy()
    
    @property
    def intermediate_stations(self) -> List[str]:
        """Get all stations except the termini."""
        if len(self.stations) > 2:
            return self.stations[1:-1]
        return []
    
    def has_station(self, station_name: str) -> bool:
        """Check if this line serves the given station."""
        return station_name in self.stations
    
    def get_station_index(self, station_name: str) -> Optional[int]:
        """Get the index of a station on this line."""
        try:
            return self.stations.index(station_name)
        except ValueError:
            return None
    
    def get_adjacent_stations(self, station_name: str) -> List[str]:
        """Get stations adjacent to the given station on this line."""
        index = self.get_station_index(station_name)
        if index is None:
            return []
        
        adjacent = []
        if index > 0:
            adjacent.append(self.stations[index - 1])
        if index < len(self.stations) - 1:
            adjacent.append(self.stations[index + 1])
        
        return adjacent
    
    def get_stations_between(self, from_station: str, to_station: str) -> List[str]:
        """Get all stations between two stations on this line."""
        from_index = self.get_station_index(from_station)
        to_index = self.get_station_index(to_station)
        
        if from_index is None or to_index is None:
            return []
        
        # Ensure from_index is less than to_index
        if from_index > to_index:
            from_index, to_index = to_index, from_index
        
        # Return stations between (exclusive of endpoints)
        return self.stations[from_index + 1:to_index]
    
    def get_journey_time(self, from_station: str, to_station: str) -> Optional[int]:
        """Get journey time between two stations on this line."""
        if not self.journey_times:
            return None
        
        # Try both directions for the journey time key
        journey_key1 = f"{from_station}-{to_station}"
        journey_key2 = f"{to_station}-{from_station}"
        
        return self.journey_times.get(journey_key1) or self.journey_times.get(journey_key2)
    
    def get_distance(self, from_station: str, to_station: str) -> Optional[float]:
        """Get distance between two stations on this line."""
        if not self.distances:
            return None
        
        return self.distances.get(from_station, {}).get(to_station)
    
    def is_direct_connection(self, from_station: str, to_station: str) -> bool:
        """Check if there's a direct connection between two stations."""
        from_index = self.get_station_index(from_station)
        to_index = self.get_station_index(to_station)
        
        if from_index is None or to_index is None:
            return False
        
        # Direct connection exists if both stations are on this line
        return True
    
    def get_direction(self, from_station: str, to_station: str) -> Optional[str]:
        """Get the direction of travel between two stations."""
        from_index = self.get_station_index(from_station)
        to_index = self.get_station_index(to_station)
        
        if from_index is None or to_index is None:
            return None
        
        if from_index < to_index:
            return f"towards {self.stations[-1]}"
        elif from_index > to_index:
            return f"towards {self.stations[0]}"
        else:
            return None  # Same station
    
    def get_stations_in_direction(self, from_station: str, direction: str) -> List[str]:
        """Get all stations in a given direction from a station."""
        from_index = self.get_station_index(from_station)
        if from_index is None:
            return []
        
        if direction.lower() in ["up", "forward", "towards_end"]:
            return self.stations[from_index + 1:]
        elif direction.lower() in ["down", "backward", "towards_start"]:
            return self.stations[:from_index]
        else:
            return []
    
    def find_interchange_stations(self, other_lines: List['RailwayLine']) -> List[str]:
        """Find stations that are interchanges with other lines."""
        interchanges = []
        
        for station in self.stations:
            for other_line in other_lines:
                if other_line.name != self.name and other_line.has_station(station):
                    if station not in interchanges:
                        interchanges.append(station)
        
        return interchanges
    
    def get_line_summary(self) -> Dict[str, Any]:
        """Get a summary of line information."""
        return {
            "name": self.name,
            "type": self.line_type.value,
            "status": self.status.value,
            "operator": self.operator,
            "station_count": self.station_count,
            "terminus_stations": self.terminus_stations,
            "is_active": self.is_active,
            "is_branch_line": self.is_branch_line,
            "is_mainline": self.is_mainline
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert railway line to dictionary representation."""
        return {
            "name": self.name,
            "stations": self.stations.copy(),
            "line_type": self.line_type.value,
            "status": self.status.value,
            "operator": self.operator,
            "color": self.color,
            "description": self.description,
            "journey_times": self.journey_times.copy() if self.journey_times else None,
            "distances": self.distances.copy() if self.distances else None,
            "service_patterns": self.service_patterns.copy() if self.service_patterns else None,
            "station_count": self.station_count,
            "terminus_stations": self.terminus_stations,
            "intermediate_stations": self.intermediate_stations,
            "is_active": self.is_active,
            "is_branch_line": self.is_branch_line,
            "is_mainline": self.is_mainline
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RailwayLine':
        """Create RailwayLine from dictionary representation."""
        line_type = LineType(data.get("line_type", "mainline"))
        status = LineStatus(data.get("status", "active"))
        
        return cls(
            name=data["name"],
            stations=data["stations"],
            line_type=line_type,
            status=status,
            operator=data.get("operator"),
            color=data.get("color"),
            description=data.get("description"),
            journey_times=data.get("journey_times"),
            distances=data.get("distances"),
            service_patterns=data.get("service_patterns")
        )
    
    def __str__(self) -> str:
        """String representation of the railway line."""
        return f"{self.name} ({self.station_count} stations)"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"RailwayLine(name='{self.name}', "
                f"stations={self.station_count}, "
                f"type={self.line_type.value}, "
                f"status={self.status.value})")
    
    def __contains__(self, station_name: str) -> bool:
        """Support 'in' operator for checking if station is on line."""
        return self.has_station(station_name)
    
    def __len__(self) -> int:
        """Support len() function to get station count."""
        return self.station_count
    
    def __iter__(self):
        """Support iteration over stations."""
        return iter(self.stations)