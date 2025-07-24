"""
Essential stations filter for reducing UI complexity and preventing crashes.

This module filters train calling points to show only essential stations:
- FROM station (origin)
- TO station (destination)
- Actual user journey interchanges (where user must change trains)
- Underground segments (🚇 Underground)
- Walk segments
- Major London terminals

This reduces UI complexity from 20+ stations to 3-5 stations per train,
preventing Qt rendering crashes while preserving important information.

For direct journeys with no changes, only origin and destination are shown.
"""

import logging
from typing import List, Set, Optional
from ...models.train_data import CallingPoint
from .interchange_detection_service import InterchangeDetectionService

logger = logging.getLogger(__name__)


class EssentialStationsFilter:
    """Filter calling points to show only essential stations for UI display."""
    
    # Major London terminals that should always be shown
    LONDON_TERMINALS = {
        "London Waterloo", "London Liverpool Street", "London Victoria",
        "London Paddington", "London Kings Cross", "London St Pancras",
        "London Euston", "London Bridge", "London Charing Cross",
        "London Cannon Street", "London Fenchurch Street", "London Marylebone"
    }
    
    # Underground indicators that should always be preserved
    UNDERGROUND_INDICATORS = {
        "🚇 Underground (10-40min)",
        "<font color='#DC241F'>🚇 Underground (10-40min)</font>"
    }
    
    @classmethod
    def filter_to_essential_stations(cls, calling_points: List[CallingPoint],
                                   route_segments: Optional[List] = None) -> List[CallingPoint]:
        """
        Filter calling points to show only essential stations.
        
        For direct journeys with no train changes, only origin and destination are shown.
        For journeys with changes, actual interchange stations are included.
        
        Args:
            calling_points: Full list of calling points
            route_segments: Route segments for detecting actual user journey changes
            
        Returns:
            Filtered list containing only essential stations
        """
        if not calling_points:
            return []
            
        if len(calling_points) <= 2:
            # Only origin and destination, no filtering needed
            return calling_points
            
        logger.info(f"Filtering {len(calling_points)} calling points to essential stations only")
        
        essential_stations = []
        
        # Always include FROM station (first)
        essential_stations.append(calling_points[0])
        logger.debug(f"Added FROM station: {calling_points[0].station_name}")
        
        # Get actual user journey interchanges using InterchangeDetectionService
        actual_interchanges = set()
        if route_segments:
            try:
                interchange_service = InterchangeDetectionService()
                interchange_points = interchange_service.detect_user_journey_interchanges(route_segments)
                
                # Extract station names where user actually needs to change trains
                for interchange in interchange_points:
                    if interchange.is_user_journey_change:
                        actual_interchanges.add(interchange.station_name)
                        logger.debug(f"Detected actual interchange: {interchange.station_name}")
                
                logger.info(f"Found {len(actual_interchanges)} actual user journey interchanges")
            except Exception as e:
                logger.warning(f"Error detecting interchanges: {e}")
        
        # Process intermediate stations
        for i in range(1, len(calling_points) - 1):
            current = calling_points[i]
            
            if cls._is_essential_station(current, calling_points, i, route_segments, actual_interchanges):
                essential_stations.append(current)
                logger.debug(f"Added essential station: {current.station_name}")
            else:
                logger.debug(f"Skipped intermediate station: {current.station_name}")
        
        # Always include TO station (last)
        if len(calling_points) > 1:
            essential_stations.append(calling_points[-1])
            logger.debug(f"Added TO station: {calling_points[-1].station_name}")
        
        reduction_percent = int((1 - len(essential_stations) / len(calling_points)) * 100)
        logger.info(f"Filtered {len(calling_points)} → {len(essential_stations)} stations "
                   f"({reduction_percent}% reduction)")
        
        return essential_stations
    
    @classmethod
    def _is_essential_station(cls, current: CallingPoint, all_points: List[CallingPoint],
                            index: int, route_segments: Optional[List] = None,
                            actual_interchanges: Optional[Set[str]] = None) -> bool:
        """
        Determine if a station is essential and should be shown.
        
        Args:
            current: Current calling point to evaluate
            all_points: All calling points for context
            index: Index of current point in the list
            route_segments: Route segments for service pattern detection
            actual_interchanges: Set of station names where user actually changes trains
            
        Returns:
            True if station is essential, False if it can be hidden
        """
        station_name = current.station_name
        
        # Always show Underground indicators
        if cls._is_underground_indicator(station_name):
            logger.debug(f"Essential: Underground indicator - {station_name}")
            return True
        
        # Always show walk indicators
        if cls._is_walk_indicator(station_name):
            logger.debug(f"Essential: Walk indicator - {station_name}")
            return True
        
        # Always show major London terminals
        if station_name in cls.LONDON_TERMINALS:
            logger.debug(f"Essential: London terminal - {station_name}")
            return True
        
        # Show stations where user actually needs to change trains
        if actual_interchanges and station_name in actual_interchanges:
            logger.debug(f"Essential: Actual user journey interchange - {station_name}")
            return True
        
        # Skip regular intermediate stations (no longer using heuristic-based detection)
        logger.debug(f"Skipping intermediate station (no actual interchange required): {station_name}")
        return False
    
    @classmethod
    def _is_underground_indicator(cls, station_name: str) -> bool:
        """Check if this is an Underground segment indicator."""
        return (station_name in cls.UNDERGROUND_INDICATORS or
                "Underground" in station_name and "🚇" in station_name)
    
    @classmethod
    def _is_walk_indicator(cls, station_name: str) -> bool:
        """Check if this is a walking segment indicator."""
        return ("Walk" in station_name or 
                "walking" in station_name.lower() or
                "🚶" in station_name)
    


class EssentialStationsConfig:
    """Configuration for essential stations filtering."""
    
    def __init__(self, max_stations: int = 5, preserve_underground: bool = True,
                 preserve_walks: bool = True, preserve_terminals: bool = True):
        """
        Initialize configuration.
        
        Args:
            max_stations: Maximum number of stations to show (including FROM/TO)
            preserve_underground: Always show Underground segments
            preserve_walks: Always show walking segments
            preserve_terminals: Always show major London terminals
        """
        self.max_stations = max_stations
        self.preserve_underground = preserve_underground
        self.preserve_walks = preserve_walks
        self.preserve_terminals = preserve_terminals