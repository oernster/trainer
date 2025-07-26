"""
Station Model

Pure data model for railway stations using names only (no codes).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any


@dataclass(frozen=True)
class Station:
    """
    Immutable data class representing a railway station.
    
    This model uses station names only - no station codes anywhere.
    """
    
    name: str
    coordinates: Optional[Tuple[float, float]] = None  # (latitude, longitude)
    interchange: Optional[List[str]] = None  # List of railway lines
    operator: Optional[str] = None
    zone: Optional[str] = None  # For London stations
    accessibility: Optional[Dict[str, bool]] = None
    facilities: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate station data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Station name cannot be empty")
        
        # Ensure interchange is a list if provided
        if self.interchange is not None and not isinstance(self.interchange, list):
            object.__setattr__(self, 'interchange', list(self.interchange))
        
        # Ensure facilities is a list if provided
        if self.facilities is not None and not isinstance(self.facilities, list):
            object.__setattr__(self, 'facilities', list(self.facilities))
    
    @property
    def is_interchange(self) -> bool:
        """Check if this station is an interchange."""
        return self.interchange is not None and len(self.interchange) > 1
    
    @property
    def is_london_station(self) -> bool:
        """Check if this is a London station."""
        return (self.name.startswith("London ") or
                self.zone is not None or
                (self.interchange is not None and any("Underground" in line or "Overground" in line
                                        for line in self.interchange)))
    
    @property
    def is_major_station(self) -> bool:
        """Check if this is a major station (terminus or major interchange)."""
        major_indicators = [
            "London " in self.name,
            "Central" in self.name,
            "Piccadilly" in self.name,
            "Victoria" in self.name,
            "Waterloo" in self.name,
            "Paddington" in self.name,
            "Kings Cross" in self.name,
            "St Pancras" in self.name,
            "Euston" in self.name,
            "Liverpool Street" in self.name,
            "Bridge" in self.name and "London" in self.name,
            self.is_interchange and self.interchange is not None and len(self.interchange) >= 3
        ]
        return any(major_indicators)
    
    def get_display_name(self) -> str:
        """Get the display name for the station."""
        return self.name
    
    def get_short_name(self) -> str:
        """Get a shortened version of the station name for display."""
        # Remove common prefixes/suffixes for shorter display
        name = self.name
        if name.startswith("London "):
            name = name[7:]  # Remove "London " prefix
        
        # Common abbreviations for display
        abbreviations = {
            " Central": " Cen",
            " International": " Intl",
            " Parkway": " Pkwy",
            " Junction": " Jct",
            " & ": " & ",
            "-on-": "-on-",
            "-upon-": "-upon-"
        }
        
        for full, abbrev in abbreviations.items():
            name = name.replace(full, abbrev)
        
        return name
    
    def has_facility(self, facility: str) -> bool:
        """Check if the station has a specific facility."""
        return self.facilities is not None and facility in self.facilities
    
    
    def get_lines(self) -> List[str]:
        """Get the list of railway lines serving this station."""
        return self.interchange or []
    
    def serves_line(self, line_name: str) -> bool:
        """Check if this station serves a specific railway line."""
        return self.interchange is not None and line_name in self.interchange
    
    def is_underground_station(self) -> bool:
        """Check if this is a pure underground station."""
        from ...managers.services.train_data_service import TrainDataService
        data_service = TrainDataService()
        
        # Initialize data repository if needed
        if data_service._data_repo_cache is None:
            from ..services.json_data_repository import JsonDataRepository
            data_service._data_repo_cache = JsonDataRepository()
        
        # Use the cached underground handler from TrainDataService
        if data_service._underground_handler_cache is None:
            from ..services.underground_routing_handler import UndergroundRoutingHandler
            data_service._underground_handler_cache = UndergroundRoutingHandler(data_service._data_repo_cache)
        
        return data_service._underground_handler_cache.is_underground_station(self.name)
    
    def get_underground_system(self) -> Optional[str]:
        """Get the underground system this station belongs to."""
        from ...managers.services.train_data_service import TrainDataService
        data_service = TrainDataService()
        
        # Initialize data repository if needed
        if data_service._data_repo_cache is None:
            from ..services.json_data_repository import JsonDataRepository
            data_service._data_repo_cache = JsonDataRepository()
        
        # Use the cached underground handler from TrainDataService
        if data_service._underground_handler_cache is None:
            from ..services.underground_routing_handler import UndergroundRoutingHandler
            data_service._underground_handler_cache = UndergroundRoutingHandler(data_service._data_repo_cache)
        
        system_info = data_service._underground_handler_cache.get_underground_system(self.name)
        if system_info:
            return system_info[1]  # Return the system name (second element in tuple)
        return None
    
    def is_mixed_station(self) -> bool:
        """Check if this station has both underground and mainline connections."""
        from ...managers.services.train_data_service import TrainDataService
        data_service = TrainDataService()
        
        # Initialize data repository if needed
        if data_service._data_repo_cache is None:
            from ..services.json_data_repository import JsonDataRepository
            data_service._data_repo_cache = JsonDataRepository()
        
        # Use the cached underground handler from TrainDataService
        if data_service._underground_handler_cache is None:
            from ..services.underground_routing_handler import UndergroundRoutingHandler
            data_service._underground_handler_cache = UndergroundRoutingHandler(data_service._data_repo_cache)
        
        return data_service._underground_handler_cache.is_mixed_station(self.name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert station to dictionary representation."""
        return {
            "name": self.name,
            "coordinates": self.coordinates,
            "interchange": self.interchange,
            "operator": self.operator,
            "zone": self.zone,
            "accessibility": self.accessibility,
            "facilities": self.facilities,
            "is_interchange": self.is_interchange,
            "is_london_station": self.is_london_station,
            "is_major_station": self.is_major_station,
            "display_name": self.get_display_name(),
            "short_name": self.get_short_name()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Station':
        """Create Station from dictionary representation."""
        return cls(
            name=data["name"],
            coordinates=data.get("coordinates"),
            interchange=data.get("interchange"),
            operator=data.get("operator"),
            zone=data.get("zone"),
            accessibility=data.get("accessibility"),
            facilities=data.get("facilities")
        )
    
    def __str__(self) -> str:
        """String representation of the station."""
        return self.name
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"Station(name='{self.name}', interchange={self.interchange})"