"""
Station Service Interface

Defines the contract for station-related operations using names only.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models.station import Station


class IStationService(ABC):
    """Interface for station-related operations."""
    
    @abstractmethod
    def resolve_station_name(self, input_name: str, strict: bool = False) -> Optional[str]:
        """
        Resolve a station name from user input.
        
        Args:
            input_name: User input station name
            strict: If True, only exact matches are returned
            
        Returns:
            Resolved station name or None if not found
        """
        pass
    
    @abstractmethod
    def validate_station_exists(self, name: str) -> bool:
        """
        Validate that a station exists.
        
        Args:
            name: Station name to validate
            
        Returns:
            True if station exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_station_suggestions(self, partial: str, limit: int = 10) -> List[str]:
        """
        Get station name suggestions based on partial input.
        
        Args:
            partial: Partial station name
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested station names
        """
        pass
    
    @abstractmethod
    def find_common_lines(self, from_name: str, to_name: str) -> List[str]:
        """
        Find railway lines that serve both stations.
        
        Args:
            from_name: Origin station name
            to_name: Destination station name
            
        Returns:
            List of common railway line names
        """
        pass
    
    @abstractmethod
    def get_station_by_name(self, name: str) -> Optional[Station]:
        """
        Get station object by name.
        
        Args:
            name: Station name
            
        Returns:
            Station object or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_stations(self) -> List[Station]:
        """
        Get all stations.
        
        Returns:
            List of all station objects
        """
        pass
    
    @abstractmethod
    def get_all_station_names(self) -> List[str]:
        """
        Get all station names.
        
        Returns:
            List of all station names
        """
        pass
    
    @abstractmethod
    def get_all_station_names_with_underground(self) -> List[str]:
        """
        Get all station names including Underground stations for autocomplete.
        
        Returns:
            List of all station names including Underground-only stations
        """
        pass
    
    @abstractmethod
    def get_stations_on_line(self, line_name: str) -> List[Station]:
        """
        Get all stations on a specific railway line.
        
        Args:
            line_name: Railway line name
            
        Returns:
            List of stations on the line
        """
        pass
    
    @abstractmethod
    def get_railway_lines_for_station(self, station_name: str) -> List[str]:
        """
        Get all railway lines that serve a station.
        
        Args:
            station_name: Station name
            
        Returns:
            List of railway line names
        """
        pass
    
    @abstractmethod
    def search_stations(self, query: str, limit: int = 20) -> List[str]:
        """
        Search for stations matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching station names
        """
        pass
    
    @abstractmethod
    def get_stations_with_context(self) -> List[Dict[str, Any]]:
        """
        Get all stations with additional context information.
        
        Returns:
            List of station dictionaries with context
        """
        pass