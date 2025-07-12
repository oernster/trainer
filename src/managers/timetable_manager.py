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
    
    def get_journey_time(self, from_code: str, to_code: str) -> Optional[int]:
        """Get typical journey time between two stations in minutes."""
        if not self.loaded:
            if not self.load_timetable_data():
                return None
        
        # Try direct lookup
        key = f"{from_code}-{to_code}"
        if key in self.journey_times:
            return self.journey_times[key]
        
        # Try reverse lookup
        reverse_key = f"{to_code}-{from_code}"
        if reverse_key in self.journey_times:
            return self.journey_times[reverse_key]
        
        # Estimate based on distance (fallback)
        return self._estimate_journey_time(from_code, to_code)
    
    def _estimate_journey_time(self, from_code: str, to_code: str) -> int:
        """Estimate journey time based on typical speeds and station types."""
        # Basic estimation based on station codes and typical speeds
        estimates = {
            # London terminals to major cities
            ("WAT", "SOU"): 79, ("WAT", "BSK"): 47, ("WAT", "WIN"): 63,
            ("PAD", "RDG"): 25, ("PAD", "BRI"): 105, ("PAD", "CDF"): 120,
            ("KGX", "YRK"): 120, ("KGX", "EDB"): 270, ("KGX", "LDS"): 135,
            ("EUS", "BHM"): 85, ("EUS", "MAN"): 125, ("EUS", "GLC"): 270,
            ("VIC", "BTN"): 52, ("VIC", "GTW"): 30,
            ("LST", "NRW"): 115, ("LST", "IPS"): 68,
        }
        
        # Check both directions
        key = (from_code, to_code)
        reverse_key = (to_code, from_code)
        
        if key in estimates:
            return estimates[key]
        elif reverse_key in estimates:
            return estimates[reverse_key]
        
        # Default estimate: 45 minutes for unknown routes
        return 45
    
    def generate_train_services(self, from_code: str, to_code: str, 
                              departure_time: datetime, 
                              num_services: int = 10) -> List[TrainService]:
        """Generate realistic train services for a route."""
        if not self.loaded:
            if not self.load_timetable_data():
                return []
        
        services = []
        journey_time = self.get_journey_time(from_code, to_code) or 45
        
        # Get operator and service info from railway data
        operator = self._get_operator_for_route(from_code, to_code)
        
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
    
    def _get_operator_for_route(self, from_code: str, to_code: str) -> str:
        """Get the typical operator for a route."""
        # Map station codes to typical operators
        operator_mappings = {
            "WAT": "South Western Railway",
            "VIC": "Southern",
            "PAD": "Great Western Railway", 
            "KGX": "LNER",
            "EUS": "Avanti West Coast",
            "LST": "Greater Anglia",
            "STP": "East Midlands Railway",
            "MYB": "Chiltern Railways"
        }
        
        return operator_mappings.get(from_code, "National Rail")
    
    def _generate_platform(self) -> str:
        """Generate a realistic platform number."""
        # Most UK stations have platforms 1-20
        return str(random.randint(1, 12))
    
    def get_next_departures(self, from_code: str, to_code: str, 
                           count: int = 5) -> List[TrainService]:
        """Get next departures from current time."""
        now = datetime.now()
        return self.generate_train_services(from_code, to_code, now, count)
    
    def get_departures_at_time(self, from_code: str, to_code: str, 
                              departure_time: str, count: int = 10) -> List[TrainService]:
        """Get departures from a specific time (HH:MM format)."""
        try:
            hour, minute = map(int, departure_time.split(':'))
            today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            return self.generate_train_services(from_code, to_code, today, count)
        except ValueError:
            # Invalid time format, use current time
            return self.get_next_departures(from_code, to_code, count)
    
    def get_service_frequency(self, from_code: str, to_code: str) -> Dict[str, str]:
        """Get typical service frequency information for a route."""
        # Find the railway line for this route
        for line_name, line_data in self.railway_data.items():
            if 'typical_services' in line_data:
                # Check if both stations are on this line
                station_codes = [station.get('code', '') for station in line_data.get('stations', [])]
                if from_code in station_codes and to_code in station_codes:
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