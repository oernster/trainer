"""
Network Graph Builder Integration

This module demonstrates how to integrate the WalkingConnectionService with the NetworkGraphBuilder
to ensure walking connections are only added between stations that meet all criteria:
1. Close enough for walking
2. On different lines
3. Not served by the same physical train that continues on a line
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from ..interfaces.i_data_repository import IDataRepository
from .walking_connection_service import WalkingConnectionService
from .network_graph_builder import NetworkGraphBuilder

logger = logging.getLogger(__name__)


class EnhancedNetworkGraphBuilder(NetworkGraphBuilder):
    """
    Enhanced network graph builder that uses the WalkingConnectionService
    to determine valid walking connections.
    """
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the enhanced network graph builder.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        super().__init__(data_repository)
        self.walking_connection_service = WalkingConnectionService(data_repository)
        self.logger = logging.getLogger(__name__)
        
    def _add_automatic_walking_connections(self, graph: Dict, station_coordinates: Dict[str, Dict]) -> None:
        """
        Add automatic walking connections between nearby stations that are on different lines
        and not served by the same physical train.
        
        This method overrides the base implementation to use the WalkingConnectionService.
        
        Args:
            graph: The network graph to add connections to
            station_coordinates: Dictionary mapping station names to their coordinates
        """
        try:
            station_names = list(graph.keys())
            connections_added = 0
            
            for i, station1 in enumerate(station_names):
                for station2 in station_names[i+1:]:
                    # Skip if already connected or same station
                    if station2 in graph[station1] or station1 == station2:
                        continue
                    
                    # Use the walking connection service to determine if walking is allowed
                    if self.walking_connection_service.is_walking_connection_allowed(station1, station2):
                        # Calculate distance for the walking connection
                        distance = self._calculate_haversine_distance_between_stations(
                            station1, station2, station_coordinates
                        )
                        
                        if distance:
                            # Calculate walking time based on distance
                            walking_speed_mps = 1.4  # meters per second
                            walking_time = max(2, int((distance * 1000) / (walking_speed_mps * 60)))  # Convert to minutes
                            
                            # Create walking connection with explicit walking_distance_m field
                            walking_distance_m = int(distance * 1000)
                            connection = {
                                'line': 'WALKING',
                                'time': walking_time,
                                'distance': distance,
                                'to_station': station2,
                                'description': f'Walk {walking_distance_m}m between stations',
                                'walking_distance_m': walking_distance_m,
                                'is_walking_connection': True  # Explicit flag for walking connections
                            }
                            
                            reverse_connection = {
                                'line': 'WALKING',
                                'time': walking_time,
                                'distance': distance,
                                'to_station': station1,
                                'description': f'Walk {walking_distance_m}m between stations',
                                'walking_distance_m': walking_distance_m,
                                'is_walking_connection': True  # Explicit flag for walking connections
                            }
                            
                            graph[station1][station2].append(connection)
                            graph[station2][station1].append(reverse_connection)
                            connections_added += 1
                            
                            self.logger.debug(f"Added walking connection: {station1} ↔ {station2} ({walking_time}min, {walking_distance_m}m)")
            
            if connections_added > 0:
                self.logger.info(f"Added {connections_added} automatic walking connections")
                
        except Exception as e:
            self.logger.error(f"Failed to add automatic walking connections: {e}")


# Example usage
def create_enhanced_network_graph_builder(data_repository: IDataRepository) -> EnhancedNetworkGraphBuilder:
    """
    Create an instance of the enhanced network graph builder.
    
    Args:
        data_repository: Data repository for accessing railway data
        
    Returns:
        EnhancedNetworkGraphBuilder: An instance of the enhanced network graph builder
    """
    return EnhancedNetworkGraphBuilder(data_repository)


# Integration guide
"""
To integrate the EnhancedNetworkGraphBuilder into your application:

1. Import the EnhancedNetworkGraphBuilder:
   from core.services.network_graph_builder_integration import EnhancedNetworkGraphBuilder

2. Create an instance of the EnhancedNetworkGraphBuilder with your data repository:
   graph_builder = EnhancedNetworkGraphBuilder(data_repository)

3. Use the graph builder to build your network graph:
   network_graph = graph_builder.build_network_graph()

4. The network graph will now include walking connections that meet all criteria:
   - Close enough for walking
   - On different lines
   - Not served by the same physical train that continues on a line

This ensures that walking connections are only suggested when appropriate,
such as between Farnborough (Main) and Farnborough North, but not between
stations on the same line like Brookwood and Farnborough (Main), or between
stations served by the same physical train like Clapham Junction and London Waterloo.
"""