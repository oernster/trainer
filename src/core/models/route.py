"""
Route Model

Data model for representing train routes using station names only.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from .station import Station


@dataclass(frozen=True)
class RouteSegment:
    """Represents a segment of a route between two stations."""
    
    from_station: str
    to_station: str
    line_name: str
    distance_km: Optional[float] = None
    journey_time_minutes: Optional[int] = None
    service_pattern: Optional[str] = None
    
    def __post_init__(self):
        """Validate route segment data."""
        if not self.from_station or not self.to_station:
            raise ValueError("From and to stations cannot be empty")
        if not self.line_name:
            raise ValueError("Line name cannot be empty")


@dataclass(frozen=True)
class Route:
    """
    Represents a complete route between two stations.
    
    Uses station names only - no station codes.
    """
    
    from_station: str
    to_station: str
    segments: List[RouteSegment]
    total_distance_km: Optional[float] = None
    total_journey_time_minutes: Optional[int] = None
    changes_required: int = 0
    route_type: str = "direct"  # direct, interchange, complex
    service_patterns: Optional[List[str]] = None
    full_path: Optional[List[str]] = None  # Complete path including all intermediate stations
    
    def __post_init__(self):
        """Validate and calculate route data."""
        if not self.from_station or not self.to_station:
            raise ValueError("From and to stations cannot be empty")
        
        if not self.segments:
            raise ValueError("Route must have at least one segment")
        
        # Calculate changes required
        if len(self.segments) > 1:
            object.__setattr__(self, 'changes_required', len(self.segments) - 1)
        
        # Determine route type
        if len(self.segments) == 1:
            route_type = "direct"
        elif len(self.segments) == 2:
            route_type = "interchange"
        else:
            route_type = "complex"
        object.__setattr__(self, 'route_type', route_type)
        
        # Calculate totals if not provided
        if self.total_distance_km is None:
            total_distance = sum(seg.distance_km for seg in self.segments 
                               if seg.distance_km is not None)
            if total_distance > 0:
                object.__setattr__(self, 'total_distance_km', total_distance)
        
        if self.total_journey_time_minutes is None:
            total_time = sum(seg.journey_time_minutes for seg in self.segments 
                           if seg.journey_time_minutes is not None)
            if total_time > 0:
                # Add interchange time for changes
                interchange_time = self.changes_required * 5  # 5 minutes per change
                object.__setattr__(self, 'total_journey_time_minutes', 
                                 total_time + interchange_time)
    
    @property
    def is_direct(self) -> bool:
        """Check if this is a direct route (no changes)."""
        return len(self.segments) == 1
    
    @property
    def requires_changes(self) -> bool:
        """Check if this route requires changes."""
        return self.changes_required > 0
    
    @property
    def intermediate_stations(self) -> List[str]:
        """Get list of intermediate stations on this route."""
        # If we have the full path, use it (more accurate)
        if self.full_path and len(self.full_path) > 2:
            return self.full_path[1:-1]  # Exclude origin and destination
        
        # Fallback to segment-based calculation
        stations = []
        for segment in self.segments:
            if segment.from_station not in stations:
                stations.append(segment.from_station)
        
        # Add the final destination
        if self.segments:
            stations.append(self.segments[-1].to_station)
        
        # Remove first and last stations (origin and destination)
        if len(stations) > 2:
            return stations[1:-1]
        return []
    
    @property
    def lines_used(self) -> List[str]:
        """Get list of railway lines used in this route."""
        return list(set(segment.line_name for segment in self.segments))
    
    @property
    def interchange_stations(self) -> List[str]:
        """Get list of stations where changes are required."""
        if len(self.segments) <= 1:
            return []
        
        interchanges = []
        for i in range(len(self.segments) - 1):
            current_segment = self.segments[i]
            next_segment = self.segments[i + 1]
            
            # The interchange station is where current segment ends
            # and next segment begins
            if current_segment.to_station == next_segment.from_station:
                interchanges.append(current_segment.to_station)
        
        return interchanges
    
    def get_journey_time_display(self) -> str:
        """Get formatted journey time for display."""
        if self.total_journey_time_minutes is None:
            return "Unknown"
        
        hours = self.total_journey_time_minutes // 60
        minutes = self.total_journey_time_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def get_distance_display(self) -> str:
        """Get formatted distance for display."""
        if self.total_distance_km is None:
            return "Unknown"
        
        if self.total_distance_km < 1:
            return f"{int(self.total_distance_km * 1000)}m"
        else:
            return f"{self.total_distance_km:.1f}km"
    
    def get_route_description(self) -> str:
        """Get a human-readable description of the route."""
        if self.is_direct:
            line = self.segments[0].line_name
            return f"Direct service on {line}"
        
        lines = self.lines_used
        changes = self.changes_required
        
        if changes == 1:
            return f"Change once - via {lines[0]} then {lines[1]}"
        else:
            return f"{changes} changes required via {', '.join(lines)}"
    
    def get_detailed_description(self) -> List[str]:
        """Get detailed step-by-step route description."""
        steps = []
        
        for i, segment in enumerate(self.segments):
            if i == 0:
                steps.append(f"Board {segment.line_name} at {segment.from_station}")
            else:
                steps.append(f"Change to {segment.line_name} at {segment.from_station}")
            
            if segment.journey_time_minutes:
                time_str = f" ({segment.journey_time_minutes}m)"
            else:
                time_str = ""
            
            steps.append(f"Travel to {segment.to_station}{time_str}")
        
        return steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert route to dictionary representation."""
        return {
            "from_station": self.from_station,
            "to_station": self.to_station,
            "segments": [
                {
                    "from_station": seg.from_station,
                    "to_station": seg.to_station,
                    "line_name": seg.line_name,
                    "distance_km": seg.distance_km,
                    "journey_time_minutes": seg.journey_time_minutes,
                    "service_pattern": seg.service_pattern
                }
                for seg in self.segments
            ],
            "total_distance_km": self.total_distance_km,
            "total_journey_time_minutes": self.total_journey_time_minutes,
            "changes_required": self.changes_required,
            "route_type": self.route_type,
            "service_patterns": self.service_patterns,
            "is_direct": self.is_direct,
            "requires_changes": self.requires_changes,
            "intermediate_stations": self.intermediate_stations,
            "lines_used": self.lines_used,
            "interchange_stations": self.interchange_stations,
            "journey_time_display": self.get_journey_time_display(),
            "distance_display": self.get_distance_display(),
            "route_description": self.get_route_description(),
            "detailed_description": self.get_detailed_description()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Route':
        """Create Route from dictionary representation."""
        segments = [
            RouteSegment(
                from_station=seg["from_station"],
                to_station=seg["to_station"],
                line_name=seg["line_name"],
                distance_km=seg.get("distance_km"),
                journey_time_minutes=seg.get("journey_time_minutes"),
                service_pattern=seg.get("service_pattern")
            )
            for seg in data["segments"]
        ]
        
        return cls(
            from_station=data["from_station"],
            to_station=data["to_station"],
            segments=segments,
            total_distance_km=data.get("total_distance_km"),
            total_journey_time_minutes=data.get("total_journey_time_minutes"),
            changes_required=data.get("changes_required", 0),
            route_type=data.get("route_type", "direct"),
            service_patterns=data.get("service_patterns")
        )
    
    def __str__(self) -> str:
        """String representation of the route."""
        return f"{self.from_station} → {self.to_station} ({self.get_route_description()})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Route(from_station='{self.from_station}', "
                f"to_station='{self.to_station}', "
                f"segments={len(self.segments)}, "
                f"changes={self.changes_required})")