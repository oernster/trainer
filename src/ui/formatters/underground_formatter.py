"""
Underground Formatter

Handles formatting and display of black box Underground routing segments.
"""

import logging
from typing import List, Optional, Dict, Any

from ...core.models.route import Route, RouteSegment


class UndergroundFormatter:
    """Formats Underground black box routing segments for UI display."""
    
    def __init__(self):
        """Initialize the Underground formatter."""
        self.logger = logging.getLogger(__name__)
        
        # Define colors for Underground display (as hex strings)
        self.underground_color = "#DC241F"  # TfL red
        self.underground_text_color = "#FFFFFF"  # White text
        self.underground_background = "#DC241F32"  # Semi-transparent red
        self.regular_color = "#333333"
        self.regular_background = "#F5F5F5"
    
    def is_underground_segment(self, segment: RouteSegment) -> bool:
        """
        Check if a route segment is an Underground black box segment.
        
        Args:
            segment: The route segment to check
            
        Returns:
            True if this is an Underground segment, False otherwise
        """
        return (segment.service_pattern == "UNDERGROUND" or 
                segment.line_name == "London Underground")
    
    def format_underground_segment_text(self, segment: RouteSegment) -> str:
        """
        Format the text display for an Underground segment.
        
        Args:
            segment: The Underground segment to format
            
        Returns:
            Formatted text string for display
        """
        if not self.is_underground_segment(segment):
            return f"{segment.from_station} → {segment.to_station}"
        
        # Format as black box Underground segment with time range
        return f"🚇 Use London Underground (10-40min)"
    
    def format_underground_segment_detailed(self, segment: RouteSegment) -> Dict[str, str]:
        """
        Format detailed information for an Underground segment.
        
        Args:
            segment: The Underground segment to format
            
        Returns:
            Dictionary with formatted details
        """
        if not self.is_underground_segment(segment):
            return {
                "line": segment.line_name,
                "from": segment.from_station,
                "to": segment.to_station,
                "type": "regular"
            }
        
        return {
            "line": "London Underground",
            "from": segment.from_station,
            "to": segment.to_station,
            "type": "underground",
            "display_text": "Use London Underground",
            "icon": "🚇",
            "time": "(10-40min)",
            "distance": f"{segment.distance_km:.1f}km" if segment.distance_km else "~5km"
        }
    
    def get_underground_segment_style(self, segment: RouteSegment) -> Dict[str, str]:
        """
        Get styling information for an Underground segment.
        
        Args:
            segment: The segment to style
            
        Returns:
            Dictionary with style properties
        """
        if self.is_underground_segment(segment):
            return {
                "background_color": self.underground_background,
                "border_color": self.underground_color,
                "text_color": self.underground_color,
                "border_width": "2px",
                "border_radius": "6px",
                "padding": "8px",
                "margin": "4px 0",
                "font_weight": "bold",
                "css_class": "underground-segment"
            }
        else:
            return {
                "background_color": self.regular_background,
                "border_color": "#CCCCCC",
                "text_color": self.regular_color,
                "border_width": "1px",
                "border_radius": "4px",
                "padding": "6px",
                "margin": "2px 0",
                "font_weight": "normal",
                "css_class": "regular-segment"
            }
    
    def format_route_with_underground(self, route: Route) -> List[Dict[str, Any]]:
        """
        Format a complete route with Underground segments highlighted.
        
        Args:
            route: The route to format
            
        Returns:
            List of formatted segment information
        """
        formatted_segments = []
        
        for i, segment in enumerate(route.segments):
            is_underground = self.is_underground_segment(segment)
            style = self.get_underground_segment_style(segment)
            
            segment_info = {
                "index": i,
                "from_station": segment.from_station,
                "to_station": segment.to_station,
                "line_name": segment.line_name,
                "is_underground": is_underground,
                "journey_time": segment.journey_time_minutes,
                "distance": segment.distance_km,
                "style": style
            }
            
            if is_underground:
                segment_info.update({
                    "display_text": "🚇 Use London Underground",
                    "icon": "🚇",
                    "description": f"Travel from {segment.from_station} to {segment.to_station} using London Underground",
                    "instructions": self.format_underground_instructions(segment)
                })
            else:
                segment_info.update({
                    "display_text": f"🚂 {segment.from_station} → {segment.to_station}",
                    "icon": "🚂",
                    "description": f"Travel from {segment.from_station} to {segment.to_station} via {segment.line_name}",
                    "instructions": [f"Board {segment.line_name} service to {segment.to_station}"]
                })
            
            formatted_segments.append(segment_info)
        
        return formatted_segments
    
    def get_underground_route_summary(self, route: Route) -> Dict[str, Any]:
        """
        Get a summary of Underground usage in a route.
        
        Args:
            route: The route to analyze
            
        Returns:
            Dictionary with Underground usage summary
        """
        underground_segments = [seg for seg in route.segments if self.is_underground_segment(seg)]
        regular_segments = [seg for seg in route.segments if not self.is_underground_segment(seg)]
        
        underground_time = sum(seg.journey_time_minutes or 0 for seg in underground_segments)
        regular_time = sum(seg.journey_time_minutes or 0 for seg in regular_segments)
        
        underground_distance = sum(seg.distance_km or 0 for seg in underground_segments)
        regular_distance = sum(seg.distance_km or 0 for seg in regular_segments)
        
        total_time = underground_time + regular_time
        total_distance = underground_distance + regular_distance
        
        return {
            "has_underground": len(underground_segments) > 0,
            "underground_segments_count": len(underground_segments),
            "regular_segments_count": len(regular_segments),
            "underground_time_minutes": underground_time,
            "regular_time_minutes": regular_time,
            "underground_distance_km": underground_distance,
            "regular_distance_km": regular_distance,
            "underground_percentage_time": (underground_time / total_time * 100) if total_time > 0 else 0,
            "underground_percentage_distance": (underground_distance / total_distance * 100) if total_distance > 0 else 0,
            "summary_text": self._generate_route_summary_text(underground_segments, regular_segments)
        }
    
    def format_underground_instructions(self, segment: RouteSegment) -> List[str]:
        """
        Generate user-friendly instructions for Underground segments.
        
        Args:
            segment: The Underground segment
            
        Returns:
            List of instruction strings
        """
        if not self.is_underground_segment(segment):
            return [f"Travel from {segment.from_station} to {segment.to_station} via {segment.line_name}"]
        
        instructions = [
            f"Use London Underground to travel from {segment.from_station} to {segment.to_station}",
            "Follow Underground signs and maps",
            "Check TfL website or app for live service updates",
            "Allow extra time for potential delays"
        ]
        
        instructions.append("Estimated journey time: 10-40 minutes")
        
        return instructions
    
    def get_underground_css_styles(self) -> str:
        """
        Get CSS styles for Underground segment display.
        
        Returns:
            CSS string for styling Underground elements
        """
        return f"""
        .underground-segment {{
            background-color: {self.underground_background};
            border: 2px solid {self.underground_color};
            border-radius: 6px;
            padding: 8px;
            margin: 4px 0;
            color: {self.underground_color};
            font-weight: bold;
        }}
        
        .underground-icon {{
            color: {self.underground_color};
            font-size: 18px;
            margin-right: 8px;
        }}
        
        .underground-text {{
            color: {self.underground_color};
            font-weight: bold;
        }}
        
        .underground-time {{
            color: {self.underground_color};
            font-style: italic;
            margin-left: 8px;
        }}
        
        .regular-segment {{
            background-color: {self.regular_background};
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 6px;
            margin: 2px 0;
            color: {self.regular_color};
        }}
        
        .route-legend {{
            background-color: #f9f9f9;
            border: 1px solid #dddddd;
            border-radius: 4px;
            padding: 8px;
            margin: 4px 0;
            font-size: 12px;
        }}
        """
    
    def format_route_display_text(self, route: Route) -> str:
        """
        Format a route for simple text display.
        
        Args:
            route: The route to format
            
        Returns:
            Formatted text representation of the route
        """
        if not route.segments:
            return f"{route.from_station} → {route.to_station}"
        
        parts = []
        for segment in route.segments:
            if self.is_underground_segment(segment):
                parts.append(f"🚇 Underground")
            else:
                parts.append(f"🚂 {segment.line_name}")
        
        return f"{route.from_station} → {route.to_station} via {' → '.join(parts)}"
    
    def get_underground_legend_info(self) -> Dict[str, str]:
        """
        Get legend information for Underground display.
        
        Returns:
            Dictionary with legend information
        """
        return {
            "underground_icon": "🚇",
            "underground_text": "London Underground (black box routing)",
            "underground_description": "Simplified routing through London Underground network",
            "regular_icon": "🚂",
            "regular_text": "National Rail",
            "regular_description": "Direct National Rail services"
        }
    
    def _generate_route_summary_text(self, underground_segments: List[RouteSegment], 
                                   regular_segments: List[RouteSegment]) -> str:
        """
        Generate a summary text for the route.
        
        Args:
            underground_segments: List of Underground segments
            regular_segments: List of regular segments
            
        Returns:
            Summary text string
        """
        if not underground_segments:
            return "National Rail only"
        elif not regular_segments:
            return "London Underground only"
        else:
            return f"Mixed journey: {len(regular_segments)} National Rail + {len(underground_segments)} Underground segment(s)"
    
    def should_highlight_underground(self, route: Route) -> bool:
        """
        Determine if Underground segments should be highlighted in this route.
        
        Args:
            route: The route to check
            
        Returns:
            True if Underground segments should be highlighted
        """
        return any(self.is_underground_segment(seg) for seg in route.segments)
    
    def get_underground_warning_text(self) -> str:
        """
        Get warning text for Underground routing.
        
        Returns:
            Warning text string
        """
        return ("Underground routing is simplified. Check TfL website or app for detailed "
                "Underground journey planning, live service updates, and accessibility information.")