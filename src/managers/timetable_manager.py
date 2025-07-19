"""
Timetable Manager for offline train schedule data.
Author: Oliver Ernster

This module provides functionality to generate realistic train times and schedules
from local JSON files, eliminating the need for API calls.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import random

from ..utils.data_path_resolver import get_data_directory, get_lines_directory, get_data_file_path

logger = logging.getLogger(__name__)

@dataclass
class TrainService:
    """Represents a train service."""
    departure_time: str
    arrival_time: str
    duration_minutes: int
    operator: str
    service_type: str  # "Fast", "Stopping", "Express"
    platform: Optional[str] = None
    status: str = "On time"

@dataclass
class JourneyInfo:
    """Represents journey information between two stations."""
    from_station: str
    to_station: str
    typical_duration: int
    services: List[TrainService]

class TimetableManager:
    """Manages offline train timetable data."""
    
    def __init__(self):
        """Initialize the timetable manager."""
        try:
            self.data_dir = get_data_directory()
            self.lines_dir = get_lines_directory()
        except FileNotFoundError as e:
            logger.error(f"Failed to find data directory: {e}")
            # Fallback to old method
            self.data_dir = Path(__file__).parent.parent / "data"
            self.lines_dir = self.data_dir / "lines"
        
        self.railway_data: Dict[str, Dict] = {}
        self.journey_times: Dict[str, int] = {}  # "FROM-TO" -> minutes
        self.loaded = False
    
    def load_timetable_data(self) -> bool:
        """Load timetable data from JSON files."""
        try:
            # Load the railway lines index
            index_file = self.data_dir / "railway_lines_index.json"
            if not index_file.exists():
                logger.error(f"Railway lines index not found: {index_file}")
                return False
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Load each railway line's timetable data
            for line_info in index_data['lines']:
                line_file = self.lines_dir / line_info['file']
                if not line_file.exists():
                    logger.warning(f"Railway line file not found: {line_file}")
                    continue
                
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                self.railway_data[line_info['name']] = line_data
                
                # Extract journey times if available
                if 'typical_journey_times' in line_data:
                    self.journey_times.update(line_data['typical_journey_times'])
            
            self.loaded = True
            logger.debug(f"Loaded timetable data for {len(self.railway_data)} railway lines")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load timetable data: {e}")
            return False
    
    
    def generate_train_services(self, from_station: str, to_station: str,
                              departure_time: datetime,
                              num_services: int = 10) -> List[TrainService]:
        """Generate realistic train services for a route using station names."""
        if not self.loaded:
            if not self.load_timetable_data():
                return []
        
        services = []
        # Get journey time and operator directly from station names
        journey_time = self.get_journey_time_by_name(from_station, to_station) or 45
        operator = self._get_operator_for_route_by_name(from_station, to_station)
        
        current_time = departure_time
        
        for i in range(num_services):
            # Vary service types
            if i % 4 == 0:
                service_type = "Express"
                duration = max(15, journey_time - random.randint(5, 15))
            elif i % 3 == 0:
                service_type = "Fast"
                duration = journey_time + random.randint(-5, 5)
            else:
                service_type = "Stopping"
                duration = journey_time + random.randint(5, 20)
            
            arrival_time = current_time + timedelta(minutes=duration)
            
            service = TrainService(
                departure_time=current_time.strftime("%H:%M"),
                arrival_time=arrival_time.strftime("%H:%M"),
                duration_minutes=duration,
                operator=operator,
                service_type=service_type,
                platform=self._generate_platform(),
                status="On time"
            )
            
            services.append(service)
            
            # Next service time (vary frequency based on time of day)
            if 7 <= current_time.hour <= 9 or 17 <= current_time.hour <= 19:
                # Peak hours - more frequent
                next_service_gap = random.randint(10, 20)
            elif 22 <= current_time.hour or current_time.hour <= 5:
                # Late night/early morning - less frequent
                next_service_gap = random.randint(45, 90)
            else:
                # Off-peak
                next_service_gap = random.randint(20, 40)
            
            current_time += timedelta(minutes=next_service_gap)
        
        return services
    
    
    def _generate_platform(self) -> str:
        """Generate a realistic platform number."""
        # Most UK stations have platforms 1-20
        return str(random.randint(1, 12))
    
    def get_next_departures(self, from_station: str, to_station: str,
                           count: int = 5) -> List[TrainService]:
        """Get next departures from current time."""
        now = datetime.now()
        return self.generate_train_services(from_station, to_station, now, count)
    
    def get_departures_at_time(self, from_station: str, to_station: str,
                              departure_time: str, count: int = 10) -> List[TrainService]:
        """Get departures from a specific time (HH:MM format)."""
        try:
            hour, minute = map(int, departure_time.split(':'))
            today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            return self.generate_train_services(from_station, to_station, today, count)
        except ValueError:
            # Invalid time format, use current time
            return self.get_next_departures(from_station, to_station, count)
    
    def get_service_frequency(self, from_station: str, to_station: str) -> Dict[str, str]:
        """Get typical service frequency information for a route."""
        # Find the railway line for this route
        for line_name, line_data in self.railway_data.items():
            if 'typical_services' in line_data:
                # Check if both stations are on this line
                station_names = [station.get('name', '') for station in line_data.get('stations', [])]
                if from_station in station_names and to_station in station_names:
                    return line_data['typical_services']
        
        # Default frequency information
        return {
            "peak_frequency": "Every 30 minutes",
            "off_peak_frequency": "Every 60 minutes",
            "evening_frequency": "Every 120 minutes",
            "weekend_frequency": "Every 60 minutes",
            "first_train": "06:00",
            "last_train": "23:00"
        }
    
    def get_journey_time_by_name(self, from_station: str, to_station: str) -> Optional[int]:
        """Get typical journey time between two stations using station names."""
        if not from_station or not to_station:
            return None
            
        # Search through railway data for journey times using station names
        for line_name, line_data in self.railway_data.items():
            stations = line_data.get('stations', [])
            station_names = [s.get('name', '') for s in stations]
            
            # Check if both stations are on this line
            if from_station in station_names and to_station in station_names:
                # Try to find journey time data
                journey_times = line_data.get('typical_journey_times', {})
                
                # Look for journey time using station names as keys
                for key, time in journey_times.items():
                    if (from_station.lower() in key.lower() and to_station.lower() in key.lower()) or \
                       (to_station.lower() in key.lower() and from_station.lower() in key.lower()):
                        return time
                
                # If no specific journey time found, estimate based on station positions
                try:
                    from_idx = station_names.index(from_station)
                    to_idx = station_names.index(to_station)
                    station_distance = abs(to_idx - from_idx)
                    # Estimate 3-5 minutes per station
                    return max(15, station_distance * 4)
                except ValueError:
                    continue
        
        # Fallback estimates for common routes
        return self._estimate_journey_time_by_name(from_station, to_station)
    
    def _estimate_journey_time_by_name(self, from_station: str, to_station: str) -> int:
        """Estimate journey time based on station names and typical routes."""
        # Common route estimates
        route_estimates = {
            ("farnborough", "london waterloo"): 47,
            ("london waterloo", "farnborough"): 47,
            ("woking", "london waterloo"): 35,
            ("london waterloo", "woking"): 35,
            ("clapham junction", "london waterloo"): 12,
            ("london waterloo", "clapham junction"): 12,
            ("surbiton", "london waterloo"): 25,
            ("london waterloo", "surbiton"): 25,
        }
        
        from_lower = from_station.lower()
        to_lower = to_station.lower()
        
        # Check for exact matches
        for (from_key, to_key), time in route_estimates.items():
            if from_key in from_lower and to_key in to_lower:
                return time
        
        # Default estimate
        return 45
    
    def _get_operator_for_route_by_name(self, from_station: str, to_station: str) -> str:
        """Get the typical operator for a route using station names."""
        # Map station names to typical operators
        from_lower = from_station.lower()
        to_lower = to_station.lower()
        
        # London Waterloo routes
        if "waterloo" in from_lower or "waterloo" in to_lower:
            return "South Western Railway"
        
        # London Victoria routes
        if "victoria" in from_lower or "victoria" in to_lower:
            return "Southern"
        
        # London Paddington routes
        if "paddington" in from_lower or "paddington" in to_lower:
            return "Great Western Railway"
        
        # London King's Cross routes
        if "king" in from_lower or "king" in to_lower:
            return "LNER"
        
        # London Euston routes
        if "euston" in from_lower or "euston" in to_lower:
            return "Avanti West Coast"
        
        # Default
        return "National Rail"