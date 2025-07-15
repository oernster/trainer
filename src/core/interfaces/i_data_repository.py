"""
Data Repository Interface

Interface for data access and persistence operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Set
from ..models.station import Station
from ..models.railway_line import RailwayLine


class IDataRepository(ABC):
    """Interface for data repository operations."""
    
    @abstractmethod
    def load_stations(self) -> List[Station]:
        """
        Load all stations from the data source.
        
        Returns:
            List of Station objects
        """
        pass
    
    @abstractmethod
    def load_railway_lines(self) -> List[RailwayLine]:
        """
        Load all railway lines from the data source.
        
        Returns:
            List of RailwayLine objects
        """
        pass
    
    @abstractmethod
    def get_station_by_name(self, name: str) -> Optional[Station]:
        """
        Get a station by its name.
        
        Args:
            name: Station name to search for
            
        Returns:
            Station object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_railway_line_by_name(self, name: str) -> Optional[RailwayLine]:
        """
        Get a railway line by its name.
        
        Args:
            name: Railway line name to search for
            
        Returns:
            RailwayLine object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_stations_on_line(self, line_name: str) -> List[Station]:
        """
        Get all stations on a specific railway line.
        
        Args:
            line_name: Name of the railway line
            
        Returns:
            List of Station objects on the line
        """
        pass
    
    @abstractmethod
    def get_lines_serving_station(self, station_name: str) -> List[RailwayLine]:
        """
        Get all railway lines serving a specific station.
        
        Args:
            station_name: Name of the station
            
        Returns:
            List of RailwayLine objects serving the station
        """
        pass
    
    @abstractmethod
    def get_journey_time(self, from_station: str, to_station: str, 
                        line_name: str) -> Optional[int]:
        """
        Get journey time between two stations on a specific line.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            line_name: Railway line name
            
        Returns:
            Journey time in minutes if available, None otherwise
        """
        pass
    
    @abstractmethod
    def get_distance(self, from_station: str, to_station: str,
                    line_name: str) -> Optional[float]:
        """
        Get distance between two stations on a specific line.
        
        Args:
            from_station: Starting station name
            to_station: Destination station name
            line_name: Railway line name
            
        Returns:
            Distance in kilometers if available, None otherwise
        """
        pass
    
    @abstractmethod
    def get_all_station_names(self) -> Set[str]:
        """
        Get all unique station names in the system.
        
        Returns:
            Set of all station names
        """
        pass
    
    @abstractmethod
    def get_all_line_names(self) -> Set[str]:
        """
        Get all railway line names in the system.
        
        Returns:
            Set of all railway line names
        """
        pass
    
    @abstractmethod
    def get_interchange_stations(self) -> List[Station]:
        """
        Get all stations that are interchanges (served by multiple lines).
        
        Returns:
            List of interchange Station objects
        """
        pass
    
    @abstractmethod
    def get_terminus_stations(self) -> List[Station]:
        """
        Get all stations that are terminus points.
        
        Returns:
            List of terminus Station objects
        """
        pass
    
    @abstractmethod
    def get_major_stations(self) -> List[Station]:
        """
        Get all major stations in the system.
        
        Returns:
            List of major Station objects
        """
        pass
    
    @abstractmethod
    def get_london_stations(self) -> List[Station]:
        """
        Get all stations in London.
        
        Returns:
            List of London Station objects
        """
        pass
    
    @abstractmethod
    def search_stations_by_name(self, query: str, limit: int = 10) -> List[Station]:
        """
        Search for stations by name using fuzzy matching.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching Station objects
        """
        pass
    
    @abstractmethod
    def search_lines_by_name(self, query: str, limit: int = 10) -> List[RailwayLine]:
        """
        Search for railway lines by name using fuzzy matching.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching RailwayLine objects
        """
        pass
    
    @abstractmethod
    def get_stations_near_location(self, latitude: float, longitude: float,
                                  radius_km: float = 10.0) -> List[Station]:
        """
        Get stations near a geographic location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_km: Search radius in kilometers
            
        Returns:
            List of nearby Station objects
        """
        pass
    
    @abstractmethod
    def get_common_lines(self, station1: str, station2: str) -> List[RailwayLine]:
        """
        Get railway lines that serve both stations.
        
        Args:
            station1: First station name
            station2: Second station name
            
        Returns:
            List of common RailwayLine objects
        """
        pass
    
    @abstractmethod
    def validate_station_exists(self, station_name: str) -> bool:
        """
        Check if a station exists in the system.
        
        Args:
            station_name: Station name to validate
            
        Returns:
            True if station exists, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_line_exists(self, line_name: str) -> bool:
        """
        Check if a railway line exists in the system.
        
        Args:
            line_name: Railway line name to validate
            
        Returns:
            True if line exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_service_patterns(self, line_name: str) -> List[str]:
        """
        Get service patterns for a railway line.
        
        Args:
            line_name: Railway line name
            
        Returns:
            List of service pattern identifiers
        """
        pass
    
    @abstractmethod
    def get_line_statistics(self, line_name: str) -> Dict[str, Any]:
        """
        Get statistics for a railway line.
        
        Args:
            line_name: Railway line name
            
        Returns:
            Dictionary containing line statistics
        """
        pass
    
    @abstractmethod
    def get_network_statistics(self) -> Dict[str, Any]:
        """
        Get overall network statistics.
        
        Returns:
            Dictionary containing network statistics
        """
        pass
    
    @abstractmethod
    def refresh_data(self) -> bool:
        """
        Refresh data from the source.
        
        Returns:
            True if refresh successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_data_version(self) -> str:
        """
        Get the version of the loaded data.
        
        Returns:
            Data version string
        """
        pass
    
    @abstractmethod
    def get_last_updated(self) -> Optional[str]:
        """
        Get the last updated timestamp of the data.
        
        Returns:
            Last updated timestamp string if available, None otherwise
        """
        pass
    
    @abstractmethod
    def backup_data(self, backup_path: str) -> bool:
        """
        Create a backup of the current data.
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            True if backup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def restore_data(self, backup_path: str) -> bool:
        """
        Restore data from a backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful, False otherwise
        """
        pass