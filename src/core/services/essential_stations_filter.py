"""
Essential stations filter for reducing UI complexity and preventing crashes.

This module filters train calling points to show only essential stations:
- FROM station (origin)
- TO station (destination)
- Platform/train changes (interchanges)
- Underground segments (🚇 Underground)
- Walk segments
- Major London terminals

This reduces UI complexity from 20+ stations to 3-5 stations per train,
preventing Qt rendering crashes while preserving important information.
"""

import logging
from typing import List, Set, Optional
from ...models.train_data import CallingPoint

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
        
        Args:
            calling_points: Full list of calling points
            route_segments: Route segments for detecting service pattern changes
            
        Returns:
            Filtered list containing only essential stations
        """
        if not calling_points:
            return []
            
        if len(calling_points) <= 3:
            # Already minimal, no filtering needed
            return calling_points
            
        logger.info(f"Filtering {len(calling_points)} calling points to essential stations only")
        
        essential_stations = []
        
        # Always include FROM station (first)
        essential_stations.append(calling_points[0])
        logger.debug(f"Added FROM station: {calling_points[0].station_name}")
        
        # Process intermediate stations
        for i in range(1, len(calling_points) - 1):
            current = calling_points[i]
            
            if cls._is_essential_station(current, calling_points, i, route_segments):
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
                            index: int, route_segments: Optional[List] = None) -> bool:
        """
        Determine if a station is essential and should be shown.
        
        Args:
            current: Current calling point to evaluate
            all_points: All calling points for context
            index: Index of current point in the list
            route_segments: Route segments for service pattern detection
            
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
        
        # Show stations where service pattern changes (train changes/interchanges)
        if cls._is_service_change_station(current, all_points, index, route_segments):
            logger.debug(f"Essential: Service change - {station_name}")
            return True
        
        # Show stations that are likely interchange points based on name patterns
        if cls._is_likely_interchange(station_name):
            logger.debug(f"Essential: Likely interchange - {station_name}")
            return True
        
        # Skip regular intermediate stations
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
    
    @classmethod
    def _is_service_change_station(cls, current: CallingPoint, all_points: List[CallingPoint],
                                 index: int, route_segments: Optional[List] = None) -> bool:
        """
        Check if this station represents a service change (train change/interchange).
        
        This is detected by:
        1. Service pattern changes in route segments
        2. Operator changes (if available)
        3. Significant time gaps suggesting train changes
        """
        if not route_segments or index == 0:
            return False
            
        try:
            # Look for service pattern changes in route segments
            # Find segments that correspond to this station
            for i, segment in enumerate(route_segments):
                if not hasattr(segment, 'to_station') or not hasattr(segment, 'service_pattern'):
                    continue
                    
                if segment.to_station == current.station_name:
                    # Check if next segment has different service pattern
                    if i < len(route_segments) - 1:
                        next_segment = route_segments[i + 1]
                        if (hasattr(next_segment, 'service_pattern') and
                            segment.service_pattern != next_segment.service_pattern):
                            logger.debug(f"Service pattern change at {current.station_name}: "
                                       f"{segment.service_pattern} → {next_segment.service_pattern}")
                            return True
            
            # Check for significant time gaps (>15 minutes) suggesting train changes
            if index > 0 and index < len(all_points) - 1:
                prev_point = all_points[index - 1]
                next_point = all_points[index + 1]
                
                if (current.scheduled_departure and prev_point.scheduled_arrival and
                    current.scheduled_departure and next_point.scheduled_arrival):
                    
                    # Time spent at this station
                    if current.scheduled_departure and current.scheduled_arrival:
                        stop_duration = (current.scheduled_departure - current.scheduled_arrival).total_seconds() / 60
                        if stop_duration > 15:  # More than 15 minutes suggests train change
                            logger.debug(f"Long stop at {current.station_name}: {stop_duration:.0f} minutes")
                            return True
            
        except Exception as e:
            logger.warning(f"Error checking service change for {current.station_name}: {e}")
        
        return False
    
    @classmethod
    def _is_likely_interchange(cls, station_name: str) -> bool:
        """
        Check if station name suggests it's likely an interchange.
        
        Interchange stations often have these characteristics:
        - "Junction" in the name
        - "Central" in the name (major stations)
        - "Parkway" (major interchange stations)
        - Airport stations
        """
        name_lower = station_name.lower()
        
        interchange_indicators = [
            "junction", "central", "parkway", "airport", "international",
            "interchange", "cross", "bridge"
        ]
        
        for indicator in interchange_indicators:
            if indicator in name_lower:
                return True
        
        return False


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