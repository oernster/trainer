"""
Service Pattern Models for Railway Lines

This module defines the data structures and logic for handling different
service patterns (express, fast, semi-fast, stopping) across all UK railway lines.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Enumeration of service types with priority ordering."""
    EXPRESS = ("express", 1, "Express service - major cities/terminals only")
    FAST = ("fast", 2, "Fast service - major stations and key interchanges")
    SEMI_FAST = ("semi_fast", 3, "Semi-fast service - market towns and regional stations")
    STOPPING = ("stopping", 4, "Stopping service - all stations")
    PEAK = ("peak", 2, "Peak service - high frequency, all stations")
    OFF_PEAK = ("off_peak", 3, "Off-peak service - standard frequency")
    NIGHT = ("night", 4, "Night service - limited stations, reduced frequency")
    
    def __init__(self, code: str, priority: int, description: str):
        self.code = code
        self.priority = priority
        self.description = description
    
    @classmethod
    def from_code(cls, code: str) -> Optional['ServiceType']:
        """Get ServiceType from code string."""
        for service_type in cls:
            if service_type.code == code:
                return service_type
        return None


@dataclass
class ServicePattern:
    """Represents a service pattern for a railway line."""
    service_type: ServiceType
    description: str
    typical_journey_time: int  # minutes
    frequency: str  # e.g., "Every 30 minutes"
    stations: Union[List[str], str]  # List of station codes or "all"
    peak_frequency: Optional[str] = None
    off_peak_frequency: Optional[str] = None
    weekend_frequency: Optional[str] = None
    first_service: Optional[str] = None  # HH:MM format
    last_service: Optional[str] = None   # HH:MM format
    operates_on: Optional[List[str]] = None  # ["weekdays", "weekends", "daily"]
    
    def __post_init__(self):
        """Validate service pattern data."""
        if isinstance(self.stations, str) and self.stations != "all":
            raise ValueError("stations must be a list of station codes or 'all'")
    
    def serves_station(self, station_code: str, all_stations: List[str]) -> bool:
        """Check if this service pattern serves a specific station."""
        if self.stations == "all":
            return station_code in all_stations
        elif isinstance(self.stations, list):
            return station_code in self.stations
        return False
    
    def get_station_count(self, all_stations: List[str]) -> int:
        """Get the number of stations served by this pattern."""
        if self.stations == "all":
            return len(all_stations)
        elif isinstance(self.stations, list):
            return len(self.stations)
        return 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_type": self.service_type.code,
            "description": self.description,
            "typical_journey_time": self.typical_journey_time,
            "frequency": self.frequency,
            "stations": self.stations,
            "peak_frequency": self.peak_frequency,
            "off_peak_frequency": self.off_peak_frequency,
            "weekend_frequency": self.weekend_frequency,
            "first_service": self.first_service,
            "last_service": self.last_service,
            "operates_on": self.operates_on
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServicePattern':
        """Create ServicePattern from dictionary."""
        service_type = ServiceType.from_code(data["service_type"])
        if not service_type:
            raise ValueError(f"Unknown service type: {data['service_type']}")
        
        return cls(
            service_type=service_type,
            description=data["description"],
            typical_journey_time=data["typical_journey_time"],
            frequency=data["frequency"],
            stations=data["stations"],
            peak_frequency=data.get("peak_frequency"),
            off_peak_frequency=data.get("off_peak_frequency"),
            weekend_frequency=data.get("weekend_frequency"),
            first_service=data.get("first_service"),
            last_service=data.get("last_service"),
            operates_on=data.get("operates_on")
        )


class LineType(Enum):
    """Classification of railway line types for service pattern templates."""
    MAIN_LINE = "main_line"
    UNDERGROUND = "underground"
    SUBURBAN = "suburban"
    EXPRESS_AIRPORT = "express_airport"
    CROSS_COUNTRY = "cross_country"
    REGIONAL = "regional"
    METRO = "metro"
    SLEEPER = "sleeper"


@dataclass
class ServicePatternSet:
    """Collection of service patterns for a railway line."""
    line_name: str
    line_type: LineType
    patterns: Dict[str, ServicePattern]  # service_type.code -> ServicePattern
    default_pattern: str  # Default service pattern code
    
    def get_pattern(self, service_type_code: str) -> Optional[ServicePattern]:
        """Get a specific service pattern."""
        return self.patterns.get(service_type_code)
    
    def get_best_pattern_for_stations(self, from_code: str, to_code: str, 
                                    all_stations: List[str]) -> Optional[ServicePattern]:
        """
        Find the best (fastest) service pattern that serves both stations.
        Returns patterns in priority order: express -> fast -> semi_fast -> stopping
        """
        # Sort patterns by priority (lower number = higher priority)
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.service_type.priority
        )
        
        for pattern in sorted_patterns:
            if (pattern.serves_station(from_code, all_stations) and 
                pattern.serves_station(to_code, all_stations)):
                return pattern
        
        return None
    
    def get_available_patterns_for_stations(self, from_code: str, to_code: str,
                                          all_stations: List[str]) -> List[ServicePattern]:
        """Get all service patterns that serve both stations, sorted by priority."""
        available_patterns = []
        
        for pattern in self.patterns.values():
            if (pattern.serves_station(from_code, all_stations) and 
                pattern.serves_station(to_code, all_stations)):
                available_patterns.append(pattern)
        
        # Sort by priority (fastest first)
        return sorted(available_patterns, key=lambda p: p.service_type.priority)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "line_name": self.line_name,
            "line_type": self.line_type.value,
            "patterns": {code: pattern.to_dict() for code, pattern in self.patterns.items()},
            "default_pattern": self.default_pattern
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServicePatternSet':
        """Create ServicePatternSet from dictionary."""
        line_type = LineType(data["line_type"])
        patterns = {
            code: ServicePattern.from_dict(pattern_data)
            for code, pattern_data in data["patterns"].items()
        }
        
        return cls(
            line_name=data["line_name"],
            line_type=line_type,
            patterns=patterns,
            default_pattern=data["default_pattern"]
        )


class ServicePatternTemplates:
    """Templates for creating service patterns for different line types."""
    
    @staticmethod
    def create_main_line_patterns(line_name: str, terminus_stations: List[str], 
                                major_stations: List[str], all_stations: List[str]) -> ServicePatternSet:
        """Create service patterns for main line services."""
        patterns = {}
        
        # Express service - major cities only
        if len(major_stations) >= 4:
            express_stations = [all_stations[0]] + major_stations[1:-1] + [all_stations[-1]]
            patterns["express"] = ServicePattern(
                service_type=ServiceType.EXPRESS,
                description="Express service - major cities only",
                typical_journey_time=int(len(all_stations) * 0.8),  # Faster than all stations
                frequency="Every 60 minutes",
                stations=express_stations,
                peak_frequency="Every 30 minutes",
                off_peak_frequency="Every 60 minutes",
                weekend_frequency="Every 90 minutes",
                operates_on=["daily"]
            )
        
        # Fast service - major stations and key interchanges
        fast_stations = [all_stations[0]] + major_stations + [all_stations[-1]]
        patterns["fast"] = ServicePattern(
            service_type=ServiceType.FAST,
            description="Fast service - major stations and key interchanges",
            typical_journey_time=int(len(all_stations) * 1.2),
            frequency="Every 30 minutes",
            stations=list(set(fast_stations)),  # Remove duplicates
            peak_frequency="Every 20 minutes",
            off_peak_frequency="Every 30 minutes",
            weekend_frequency="Every 45 minutes",
            operates_on=["daily"]
        )
        
        # Semi-fast service - more stations
        semi_fast_stations = all_stations[::2] if len(all_stations) > 10 else all_stations
        patterns["semi_fast"] = ServicePattern(
            service_type=ServiceType.SEMI_FAST,
            description="Semi-fast service - regional stations",
            typical_journey_time=int(len(all_stations) * 1.5),
            frequency="Every 60 minutes",
            stations=semi_fast_stations,
            operates_on=["daily"]
        )
        
        # Stopping service - all stations
        patterns["stopping"] = ServicePattern(
            service_type=ServiceType.STOPPING,
            description="Stopping service - all stations",
            typical_journey_time=len(all_stations) * 2,
            frequency="Every 2 hours",
            stations="all",
            operates_on=["daily"]
        )
        
        return ServicePatternSet(
            line_name=line_name,
            line_type=LineType.MAIN_LINE,
            patterns=patterns,
            default_pattern="fast"
        )
    
    @staticmethod
    def create_underground_patterns(line_name: str, all_stations: List[str]) -> ServicePatternSet:
        """Create service patterns for London Underground lines."""
        patterns = {}
        
        # Peak service
        patterns["peak"] = ServicePattern(
            service_type=ServiceType.PEAK,
            description="Peak service - all stations, high frequency",
            typical_journey_time=len(all_stations) * 2,
            frequency="Every 2-3 minutes",
            stations="all",
            operates_on=["weekdays"],
            first_service="05:00",
            last_service="00:30"
        )
        
        # Off-peak service
        patterns["off_peak"] = ServicePattern(
            service_type=ServiceType.OFF_PEAK,
            description="Off-peak service - all stations",
            typical_journey_time=int(len(all_stations) * 2.5),
            frequency="Every 5-7 minutes",
            stations="all",
            operates_on=["daily"],
            first_service="05:00",
            last_service="00:30"
        )
        
        # Night service (if applicable)
        if "Night" in line_name or len(all_stations) > 20:
            patterns["night"] = ServicePattern(
                service_type=ServiceType.NIGHT,
                description="Night service - limited stations",
                typical_journey_time=len(all_stations) * 3,
                frequency="Every 10-15 minutes",
                stations=all_stations[::3],  # Every 3rd station
                operates_on=["weekends"],
                first_service="00:30",
                last_service="05:00"
            )
        
        return ServicePatternSet(
            line_name=line_name,
            line_type=LineType.UNDERGROUND,
            patterns=patterns,
            default_pattern="off_peak"
        )
    
    @staticmethod
    def create_express_airport_patterns(line_name: str, all_stations: List[str]) -> ServicePatternSet:
        """Create service patterns for express airport services."""
        patterns = {}
        
        # Express service - direct or very limited stops
        if len(all_stations) <= 3:
            # Direct service
            patterns["express"] = ServicePattern(
                service_type=ServiceType.EXPRESS,
                description="Non-stop express service",
                typical_journey_time=15,
                frequency="Every 15 minutes",
                stations=[all_stations[0], all_stations[-1]],
                operates_on=["daily"],
                first_service="05:00",
                last_service="23:30"
            )
        else:
            # Limited stops
            patterns["express"] = ServicePattern(
                service_type=ServiceType.EXPRESS,
                description="Express service - limited stops",
                typical_journey_time=len(all_stations) * 3,
                frequency="Every 15 minutes",
                stations=all_stations,
                operates_on=["daily"],
                first_service="05:00",
                last_service="23:30"
            )
        
        return ServicePatternSet(
            line_name=line_name,
            line_type=LineType.EXPRESS_AIRPORT,
            patterns=patterns,
            default_pattern="express"
        )
    
    @staticmethod
    def create_suburban_patterns(line_name: str, major_stations: List[str], 
                               all_stations: List[str]) -> ServicePatternSet:
        """Create service patterns for suburban lines."""
        patterns = {}
        
        # Fast service
        patterns["fast"] = ServicePattern(
            service_type=ServiceType.FAST,
            description="Fast service - major towns and interchanges",
            typical_journey_time=int(len(all_stations) * 1.5),
            frequency="Every 30 minutes",
            stations=major_stations,
            peak_frequency="Every 20 minutes",
            off_peak_frequency="Every 30 minutes",
            operates_on=["daily"]
        )
        
        # Semi-fast service
        patterns["semi_fast"] = ServicePattern(
            service_type=ServiceType.SEMI_FAST,
            description="Semi-fast service - market towns",
            typical_journey_time=int(len(all_stations) * 1.8),
            frequency="Every 60 minutes",
            stations=all_stations[::2] if len(all_stations) > 8 else all_stations,
            operates_on=["daily"]
        )
        
        # Stopping service
        patterns["stopping"] = ServicePattern(
            service_type=ServiceType.STOPPING,
            description="Stopping service - all stations",
            typical_journey_time=len(all_stations) * 2,
            frequency="Every 2 hours",
            stations="all",
            operates_on=["daily"]
        )
        
        return ServicePatternSet(
            line_name=line_name,
            line_type=LineType.SUBURBAN,
            patterns=patterns,
            default_pattern="fast"
        )
    
    @staticmethod
    def _create_pattern_from_dict(pattern_dict: Dict) -> ServicePattern:
        """Helper method to create ServicePattern from dictionary."""
        return ServicePattern.from_dict(pattern_dict)


def classify_line_type(line_name: str, operator: str) -> LineType:
    """Classify a railway line based on its name and operator."""
    line_lower = line_name.lower()
    operator_lower = operator.lower()
    
    # Underground/Metro systems
    if ("underground" in line_lower or "tube" in line_lower or 
        "transport for london" in operator_lower or "tfl" in operator_lower):
        return LineType.UNDERGROUND
    
    # Express/Airport services
    if ("express" in line_lower or "airport" in line_lower or 
        "heathrow" in line_lower or "gatwick" in line_lower or "stansted" in line_lower):
        return LineType.EXPRESS_AIRPORT
    
    # Sleeper services
    if "sleeper" in line_lower:
        return LineType.SLEEPER
    
    # Cross-country services
    if ("cross country" in line_lower or "transpennine" in line_lower or
        operator_lower in ["crosscountry", "transpennine express"]):
        return LineType.CROSS_COUNTRY
    
    # Main lines
    if ("main line" in line_lower or 
        any(main in line_lower for main in ["west coast", "east coast", "great western", "midland"])):
        return LineType.MAIN_LINE
    
    # Metro systems
    if ("metro" in line_lower or "subway" in line_lower or "merseyrail" in operator_lower):
        return LineType.METRO
    
    # Regional/suburban (default for most other lines)
    return LineType.SUBURBAN