"""
Interchange Detection Service

This service provides intelligent detection of actual user journey interchanges,
distinguishing between stations where users must change trains versus stations
that simply serve multiple lines.
"""

import logging
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import math
import threading

logger = logging.getLogger(__name__)


class InterchangeType(Enum):
    """Types of interchange connections."""
    TRAIN_CHANGE = "train_change"  # User must change trains
    PLATFORM_CHANGE = "platform_change"  # User changes platforms but not trains
    THROUGH_SERVICE = "through_service"  # Same train continues with different line name
    WALKING_CONNECTION = "walking_connection"  # Walking between stations


@dataclass
class InterchangePoint:
    """Represents a point where a user may need to change during their journey."""
    station_name: str
    from_line: str
    to_line: str
    interchange_type: InterchangeType
    walking_time_minutes: int
    is_user_journey_change: bool
    coordinates: Optional[Dict[str, float]] = None
    description: str = ""


class InterchangeDetectionService:
    """Service for detecting actual user journey interchanges."""
    
    _instance: Optional['InterchangeDetectionService'] = None
    _instance_lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern to prevent multiple expensive initializations."""
        if cls._instance is None:
            with cls._instance_lock:
                # Double-check pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the interchange detection service with lazy loading (singleton-safe)."""
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        
        # Cache for performance - all initialized as None for lazy loading
        self._station_coordinates_cache: Optional[Dict[str, Dict[str, float]]] = None
        self._line_to_file_cache: Optional[Dict[str, str]] = None
        self._station_to_files_cache: Optional[Dict[str, List[str]]] = None
        
        # Known through services - lightweight initialization
        self._known_through_services: Optional[Dict[str, List[Dict[str, str]]]] = None
        
        # Thread locks for safe lazy loading
        self._coordinates_lock = threading.Lock()
        self._line_mapping_lock = threading.Lock()
        self._station_mapping_lock = threading.Lock()
        
        # Mark as initialized
        self._initialized = True
        
        self.logger.info("InterchangeDetectionService singleton initialized with lazy loading")
    
    def _get_known_through_services(self) -> Dict[str, List[Dict[str, str]]]:
        """Get known through services where passengers don't change trains (lazy loaded)."""
        if self._known_through_services is None:
            self._known_through_services = {
                "Hook": [
                    {"from_line": "South Western Main Line", "to_line": "Reading to Basingstoke Line"},
                    {"from_line": "Reading to Basingstoke Line", "to_line": "South Western Main Line"}
                ],
                "Fleet": [
                    {"from_line": "South Western Main Line", "to_line": "Reading to Basingstoke Line"},
                    {"from_line": "Reading to Basingstoke Line", "to_line": "South Western Main Line"},
                    {"from_line": "South Western Railway", "to_line": "South Western Railway Main Line"},
                    {"from_line": "South Western Railway Main Line", "to_line": "South Western Railway"}
                ]
            }
        return self._known_through_services
    
    def detect_user_journey_interchanges(self, route_segments: List[Any]) -> List[InterchangePoint]:
        """
        Detect actual user journey interchanges from route segments.
        
        Args:
            route_segments: List of RouteSegment objects representing the user's journey
            
        Returns:
            List of InterchangePoint objects representing actual journey changes
        """
        try:
            if not route_segments or len(route_segments) < 2:
                self.logger.debug("No route segments or insufficient segments for interchange detection")
                return []
            
            interchanges = []
            
            # Analyze consecutive segments for line changes
            for i in range(len(route_segments) - 1):
                try:
                    current_segment = route_segments[i]
                    next_segment = route_segments[i + 1]
                    
                    # Validate segment structure with better error handling
                    if not all(hasattr(current_segment, attr) for attr in ['to_station', 'line_name']):
                        self.logger.warning(f"Current segment {i} missing required attributes")
                        continue
                        
                    if not all(hasattr(next_segment, attr) for attr in ['from_station', 'line_name']):
                        self.logger.warning(f"Next segment {i+1} missing required attributes")
                        continue
                    
                    connection_station = current_segment.to_station
                    from_line = current_segment.line_name
                    to_line = next_segment.line_name
                    
                    # Validate station names and line names
                    if not connection_station or not from_line or not to_line:
                        self.logger.warning(f"Empty station or line names in segments {i}-{i+1}")
                        continue
                    
                    # Only process if there's actually a line change and stations match
                    if (from_line != to_line and
                        connection_station == next_segment.from_station):
                        
                        interchange = self._analyze_interchange(
                            connection_station, from_line, to_line, current_segment, next_segment
                        )
                        
                        if interchange:
                            interchanges.append(interchange)
                            
                except Exception as e:
                    self.logger.error(f"Error processing segment {i}: {e}")
                    continue
            
            self.logger.debug(f"Detected {len(interchanges)} potential interchanges")
            return interchanges
            
        except Exception as e:
            self.logger.error(f"Error in detect_user_journey_interchanges: {e}")
            return []
    
    def _analyze_interchange(self, station_name: str, from_line: str, to_line: str,
                           current_segment: Any, next_segment: Any) -> Optional[InterchangePoint]:
        """
        Analyze a potential interchange to determine if it's a real user journey change.
        
        Args:
            station_name: Name of the station where the change occurs
            from_line: Line name of the incoming segment
            to_line: Line name of the outgoing segment
            current_segment: Current route segment
            next_segment: Next route segment
            
        Returns:
            InterchangePoint if this is a real user journey change, None otherwise
        """
        # Check if this is a known through service
        if self._is_known_through_service(from_line, to_line, station_name):
            self.logger.debug(f"Through service detected at {station_name}: {from_line} -> {to_line}")
            return InterchangePoint(
                station_name=station_name,
                from_line=from_line,
                to_line=to_line,
                interchange_type=InterchangeType.THROUGH_SERVICE,
                walking_time_minutes=0,
                is_user_journey_change=False,
                description="Through service - same train continues"
            )
        
        # Check if this is actually a meaningful line change that requires user action
        if not self._is_meaningful_user_journey_change(from_line, to_line, station_name, current_segment, next_segment):
            self.logger.debug(f"Not a meaningful user journey change at {station_name}: {from_line} -> {to_line}")
            return InterchangePoint(
                station_name=station_name,
                from_line=from_line,
                to_line=to_line,
                interchange_type=InterchangeType.THROUGH_SERVICE,
                walking_time_minutes=0,
                is_user_journey_change=False,
                description="Same train continues with different line designation"
            )
        
        # Validate that this is a legitimate interchange geographically
        if not self._is_valid_interchange_geographically(station_name, from_line, to_line):
            self.logger.debug(f"Invalid geographic interchange at {station_name}: {from_line} -> {to_line}")
            return None
        
        # Calculate walking time for the interchange
        walking_time = self._calculate_interchange_walking_time(station_name, from_line, to_line)
        
        # Determine if this is a walking connection vs train change
        if walking_time > 10:  # More than 10 minutes suggests walking between stations
            interchange_type = InterchangeType.WALKING_CONNECTION
            is_journey_change = True  # Walking connections are highlighted
        else:
            interchange_type = InterchangeType.TRAIN_CHANGE
            is_journey_change = True
        
        self.logger.debug(f"Valid interchange detected at {station_name}: {from_line} -> {to_line}")
        
        return InterchangePoint(
            station_name=station_name,
            from_line=from_line,
            to_line=to_line,
            interchange_type=interchange_type,
            walking_time_minutes=walking_time,
            is_user_journey_change=is_journey_change,
            coordinates=self._get_station_coordinates().get(station_name),
            description=f"Change from {from_line} to {to_line}"
        )
    
    def _is_known_through_service(self, line1: str, line2: str, station_name: str) -> bool:
        """Check if this represents a known through service."""
        known_services = self._get_known_through_services()
        
        if station_name not in known_services:
            return False
        
        for service in known_services[station_name]:
            if ((service["from_line"] == line1 and service["to_line"] == line2) or
                (service["from_line"] == line2 and service["to_line"] == line1)):
                return True
        
        return False
    
    def _is_meaningful_user_journey_change(self, from_line: str, to_line: str, station_name: str,
                                         current_segment: Any, next_segment: Any) -> bool:
        """
        Determine if a line change represents a meaningful user journey change where the passenger
        must actually change trains, rather than just a line name change for the same physical train.
        
        Args:
            from_line: Line name of the incoming segment
            to_line: Line name of the outgoing segment
            station_name: Station where the change occurs
            current_segment: Current route segment
            next_segment: Next route segment
            
        Returns:
            True if this is a meaningful change requiring user action, False otherwise
        """
        self.logger.debug(f"Analyzing {station_name}: {from_line} -> {to_line}")
        
        # First check if this represents a change between different JSON files (different railway networks)
        is_json_change = self._is_json_file_line_change(from_line, to_line)
        self.logger.debug(f"{station_name} JSON file change: {is_json_change}")
        
        if not is_json_change:
            self.logger.debug(f"Same network detected at {station_name}: {from_line} -> {to_line}")
            return False
        
        # Check if this is a continuous service where the same train continues with different line names
        is_continuous = self._is_continuous_train_service(from_line, to_line, station_name)
        self.logger.debug(f"{station_name} continuous service: {is_continuous}")
        
        if is_continuous:
            self.logger.debug(f"Continuous train service at {station_name}: {from_line} -> {to_line}")
            return False
        
        # Check if the station is actually a terminus or origin for one of the lines
        # If the user is just passing through on the same train, it's not a meaningful change
        is_through = self._is_through_station_for_journey(station_name, from_line, to_line, current_segment, next_segment)
        self.logger.debug(f"{station_name} through station: {is_through}")
        
        if is_through:
            self.logger.debug(f"Through station for journey at {station_name}: {from_line} -> {to_line}")
            return False
        
        # If we get here, it's likely a real interchange requiring user action
        self.logger.debug(f"{station_name} marked as REAL INTERCHANGE requiring user action")
        return True
    
    def _is_continuous_train_service(self, from_line: str, to_line: str, station_name: str) -> bool:
        """
        Check if this represents a continuous train service where the same physical train
        continues its journey with different line designations.
        """
        # Known continuous services where the same train continues with different line names
        continuous_services = [
            # South Western Main Line continuing as Reading to Basingstoke Line
            ("South Western Main Line", "Reading to Basingstoke Line"),
            ("Reading to Basingstoke Line", "South Western Main Line"),
            # Add other known continuous services here
        ]
        
        for service_from, service_to in continuous_services:
            if ((from_line == service_from and to_line == service_to) or
                (from_line == service_to and to_line == service_from)):
                return True
        
        return False
    
    def _is_through_station_for_journey(self, station_name: str, from_line: str, to_line: str,
                                      current_segment: Any, next_segment: Any) -> bool:
        """
        Check if this station is just a through station for the user's journey,
        meaning they don't need to change trains here.
        """
        # Check if both segments have the same service pattern or train ID
        # This would indicate it's the same physical train continuing
        current_service = getattr(current_segment, 'service_pattern', None)
        next_service = getattr(next_segment, 'service_pattern', None)
        
        if current_service and next_service and current_service == next_service:
            self.logger.debug(f"Same service pattern detected: {current_service}")
            return True
        
        # Check train IDs if available
        current_train_id = getattr(current_segment, 'train_id', None)
        next_train_id = getattr(next_segment, 'train_id', None)
        
        if current_train_id and next_train_id and current_train_id == next_train_id:
            self.logger.debug(f"Same train ID detected: {current_train_id}")
            return True
        
        # Check if this is a known through station for specific line combinations
        through_stations = {
            "Woking": [
                # Woking is a through station for South Western services
                ("South Western Main Line", "Reading to Basingstoke Line"),
                ("Reading to Basingstoke Line", "South Western Main Line"),
                # Woking is also a through station for Portsmouth Direct Line services
                ("South Western Main Line", "Portsmouth Direct Line"),
                ("Portsmouth Direct Line", "South Western Main Line"),
            ],
            "Hook": [
                ("South Western Main Line", "Reading to Basingstoke Line"),
                ("Reading to Basingstoke Line", "South Western Main Line"),
            ],
            "Fleet": [
                ("South Western Main Line", "Reading to Basingstoke Line"),
                ("Reading to Basingstoke Line", "South Western Main Line"),
            ]
        }
        
        if station_name in through_stations:
            for through_from, through_to in through_stations[station_name]:
                if ((from_line == through_from and to_line == through_to) or
                    (from_line == through_to and to_line == through_from)):
                    return True
        
        return False
    
    def _is_json_file_line_change(self, line1: str, line2: str) -> bool:
        """Check if a line change represents a change between different JSON files."""
        line_to_file = self._get_line_to_json_file_mapping()
        
        file1 = line_to_file.get(line1)
        file2 = line_to_file.get(line2)
        
        # If we can't find the files, assume it's a change
        if not file1 or not file2:
            return True
        
        # Lines are different if they come from different JSON files
        return file1 != file2
    
    def _is_valid_interchange_geographically(self, station_name: str, from_line: str, to_line: str) -> bool:
        """
        Validate that an interchange is geographically legitimate.
        
        Args:
            station_name: Station where the interchange occurs
            from_line: Incoming line
            to_line: Outgoing line
            
        Returns:
            True if this is a valid interchange based on geographic constraints
        """
        try:
            # Get station coordinates
            station_coordinates = self._get_station_coordinates()
            
            if station_name not in station_coordinates:
                self.logger.debug(f"Missing coordinates for station: {station_name}")
                return True  # Conservative: allow if we can't validate
            
            # Get the line-to-file mapping
            line_to_file = self._get_line_to_json_file_mapping()
            
            file1 = line_to_file.get(from_line)
            file2 = line_to_file.get(to_line)
            
            if not file1 or not file2:
                self.logger.debug(f"Could not find JSON files for lines: {from_line} -> {file1}, {to_line} -> {file2}")
                return True  # Conservative: allow if we can't validate
            
            # Check if the station appears in both JSON files
            station_to_files = self._get_station_to_json_files_mapping()
            station_files = station_to_files.get(station_name, [])
            
            if file1 in station_files and file2 in station_files:
                self.logger.debug(f"Valid interchange: {station_name} appears in both {file1} and {file2}")
                return True
            else:
                self.logger.debug(f"Invalid interchange: {station_name} not in both files. Found in: {station_files}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in geographic validation: {e}")
            return True  # Conservative: allow if validation fails
    
    def _calculate_interchange_walking_time(self, station_name: str, from_line: str, to_line: str) -> int:
        """Calculate estimated walking time for an interchange."""
        # Check for specific known interchange times
        known_times = {
            ("Farnborough (Main)", "Farnborough North"): 12,
            ("Farnborough North", "Farnborough (Main)"): 12,
        }
        
        # Check both directions
        for (station1, station2), time in known_times.items():
            if station_name in [station1, station2]:
                return time
        
        # Default interchange times based on line types
        if 'Underground' in from_line or 'Underground' in to_line:
            return 3  # Underground interchanges are typically faster
        elif 'Express' in from_line or 'Express' in to_line:
            return 8  # Express services often use different platforms
        else:
            return 5  # Standard interchange time
    
    def _get_station_coordinates(self) -> Dict[str, Dict[str, float]]:
        """Get station coordinates from JSON files with thread-safe lazy loading."""
        if self._station_coordinates_cache is not None:
            return self._station_coordinates_cache
        
        with self._coordinates_lock:
            # Double-check pattern to prevent race conditions
            if self._station_coordinates_cache is not None:
                return self._station_coordinates_cache
            
            self.logger.debug("Loading station coordinates (lazy loading)")
            self._station_coordinates_cache = self._build_station_coordinates_mapping()
            return self._station_coordinates_cache
    
    def _build_station_coordinates_mapping(self) -> Dict[str, Dict[str, float]]:
        """Build the mapping of station names to their coordinates."""
        station_coordinates = {}
        
        lines_dir = Path(__file__).parent.parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            self.logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                if json_file.name.endswith('.backup'):
                    continue
                    
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    stations = data.get('stations', [])
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        coordinates = station.get('coordinates', {})
                        
                        if station_name and coordinates and 'lat' in coordinates and 'lng' in coordinates:
                            station_coordinates[station_name] = coordinates
            
            self.logger.debug(f"Built station coordinates mapping with {len(station_coordinates)} stations")
            return station_coordinates
            
        except Exception as e:
            self.logger.error(f"Failed to build station coordinates mapping: {e}")
            return {}
    
    def _get_line_to_json_file_mapping(self) -> Dict[str, str]:
        """Create a mapping of line names to their JSON file names with thread-safe lazy loading."""
        if self._line_to_file_cache is not None:
            return self._line_to_file_cache
        
        with self._line_mapping_lock:
            # Double-check pattern to prevent race conditions
            if self._line_to_file_cache is not None:
                return self._line_to_file_cache
            
            self.logger.debug("Loading line-to-file mapping (lazy loading)")
            self._line_to_file_cache = self._build_line_to_file_mapping()
            return self._line_to_file_cache
    
    def _build_line_to_file_mapping(self) -> Dict[str, str]:
        """Build the mapping of line names to JSON file names with performance optimization."""
        line_to_file = {}
        
        lines_dir = Path(__file__).parent.parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            self.logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            json_files = list(lines_dir.glob("*.json"))
            self.logger.debug(f"Processing {len(json_files)} JSON files for line mapping")
            
            for json_file in json_files:
                if json_file.name.endswith('.backup'):
                    continue
                
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # Get line name from metadata with validation
                        metadata = data.get('metadata', {})
                        line_name = metadata.get('line_name', '').strip()
                        operator = metadata.get('operator', '').strip()
                        file_name = json_file.stem
                        
                        if line_name:
                            line_to_file[line_name] = file_name
                        
                        # Add operator name mappings for common cases
                        if operator:
                            line_to_file[operator] = file_name
                        
                        # Add specific mappings for known operator/service variations
                        self._add_service_variations(line_to_file, file_name)
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON in file {json_file}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing file {json_file}: {e}")
                    continue
            
            self.logger.debug(f"Built line-to-file mapping with {len(line_to_file)} lines")
            return line_to_file
            
        except Exception as e:
            self.logger.error(f"Failed to build line-to-file mapping: {e}")
            return {}
    
    def _add_service_variations(self, line_to_file: Dict[str, str], file_name: str):
        """Add service variations to line mapping for better matching."""
        service_variations = {
            'south_western': [
                'South Western Railway',
                'South Western Main Line'
            ],
            'cross_country': [
                'CrossCountry',
                'Cross Country',
                'Cross Country Line'
            ],
            'reading_to_basingstoke': [
                'Reading to Basingstoke Line'
            ],
            'great_western_main_line': [
                'Great Western Railway',
                'Great Western Main Line'
            ]
        }
        
        for pattern, variations in service_variations.items():
            if pattern in file_name:
                for variation in variations:
                    line_to_file[variation] = file_name
    
    def _get_station_to_json_files_mapping(self) -> Dict[str, List[str]]:
        """Create a mapping of station names to the JSON files they appear in with thread-safe lazy loading."""
        if self._station_to_files_cache is not None:
            return self._station_to_files_cache
        
        with self._station_mapping_lock:
            # Double-check pattern to prevent race conditions
            if self._station_to_files_cache is not None:
                return self._station_to_files_cache
            
            self.logger.debug("Loading station-to-files mapping (lazy loading)")
            self._station_to_files_cache = self._build_station_to_files_mapping()
            return self._station_to_files_cache
    
    def _build_station_to_files_mapping(self) -> Dict[str, List[str]]:
        """Build the mapping of stations to JSON files by loading all line data."""
        station_to_files = {}
        
        lines_dir = Path(__file__).parent.parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            self.logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                if json_file.name.endswith('.backup'):
                    continue
                    
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    stations = data.get('stations', [])
                    file_name = json_file.stem
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        if station_name:
                            if station_name not in station_to_files:
                                station_to_files[station_name] = []
                            station_to_files[station_name].append(file_name)
            
            self.logger.debug(f"Built station-to-files mapping with {len(station_to_files)} stations")
            return station_to_files
            
        except Exception as e:
            self.logger.error(f"Failed to build station-to-files mapping: {e}")
            return {}
    
    def validate_interchange_necessity(self, from_line: str, to_line: str, station: str) -> bool:
        """
        Validate if an interchange is necessary for the user's journey.
        
        Args:
            from_line: Line the user is coming from
            to_line: Line the user is going to
            station: Station where the potential interchange occurs
            
        Returns:
            True if the user must actually change trains at this station
        """
        # Same line = no change needed
        if from_line == to_line:
            return False
        
        # Check if it's a through service
        if self._is_known_through_service(from_line, to_line, station):
            return False
        
        # Check if it's the same network (same JSON file)
        if not self._is_json_file_line_change(from_line, to_line):
            return False
        
        # If we get here, it's likely a real interchange
        return True
    
    def get_station_line_mappings(self) -> Dict[str, List[str]]:
        """Get mapping of stations to the lines that serve them."""
        station_to_lines = {}
        line_to_file = self._get_line_to_json_file_mapping()
        
        # Reverse the mapping to get file to lines
        file_to_lines = {}
        for line, file in line_to_file.items():
            if file not in file_to_lines:
                file_to_lines[file] = []
            file_to_lines[file].append(line)
        
        # Get station to files mapping
        station_to_files = self._get_station_to_json_files_mapping()
        
        # Build station to lines mapping
        for station, files in station_to_files.items():
            lines = []
            for file in files:
                if file in file_to_lines:
                    lines.extend(file_to_lines[file])
            station_to_lines[station] = list(set(lines))  # Remove duplicates
        
        return station_to_lines
    
    def clear_cache(self):
        """Clear all cached data to force reload with thread safety."""
        with self._coordinates_lock:
            self._station_coordinates_cache = None
        with self._line_mapping_lock:
            self._line_to_file_cache = None
        with self._station_mapping_lock:
            self._station_to_files_cache = None
        
        # Clear known through services as well
        self._known_through_services = None
        
        self.logger.debug("InterchangeDetectionService cache cleared")
    
    def _calculate_haversine_distance(self, coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
        """
        Calculate the great-circle distance between two points on Earth using Haversine formula.
        Returns distance in kilometers.
        
        Args:
            coord1: Dictionary with 'lat' and 'lng' keys
            coord2: Dictionary with 'lat' and 'lng' keys
            
        Returns:
            Distance in kilometers
        """
        # Extract coordinates
        lat1 = coord1.get('lat', 0)
        lon1 = coord1.get('lng', 0)
        lat2 = coord2.get('lat', 0)
        lon2 = coord2.get('lng', 0)
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        return c * r