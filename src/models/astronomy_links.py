"""
Astronomy links management for the Trainer application.
Author: Oliver Ernster

This module provides comprehensive astronomy link categories and management,
supporting the API-free astronomy widget system with curated links to
observatories, space agencies, and astronomy tools.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class LinkCategory(Enum):
    """Categories for astronomy links."""
    
    OBSERVATORY = "observatory"        # Telescopes and observatories
    SPACE_AGENCY = "space_agency"      # Space agencies and missions
    ASTRONOMY_TOOL = "astronomy_tool"  # Apps and software
    EDUCATIONAL = "educational"        # Learning resources
    LIVE_DATA = "live_data"           # Real-time feeds
    COMMUNITY = "community"           # Forums and social
    TONIGHT_SKY = "tonight_sky"       # What's visible tonight
    MOON_INFO = "moon_info"           # Moon phase and info


@dataclass(frozen=True)
class AstronomyLink:
    """Immutable astronomy link data."""
    
    name: str
    url: str
    category: LinkCategory
    emoji: str
    description: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate link data."""
        if not self.name.strip():
            raise ValueError("Link name cannot be empty")
        if not self.url.strip():
            raise ValueError("Link URL cannot be empty")
        if not self._is_valid_url(self.url):
            raise ValueError(f"Invalid URL: {self.url}")
        if not self.description.strip():
            raise ValueError("Link description cannot be empty")
        if not (1 <= self.priority <= 3):
            raise ValueError("Priority must be between 1 and 3")
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class AstronomyLinksDatabase:
    """
    Comprehensive database of astronomy links.
    
    Provides curated links to observatories, space agencies, tools,
    and educational resources for the API-free astronomy system.
    """
    
    def __init__(self):
        """Initialize the astronomy links database."""
        self._links: Dict[str, AstronomyLink] = {}
        self._initialize_links()
    
    def _initialize_links(self) -> None:
        """Initialize the comprehensive astronomy links database."""
        
        # Major Observatories
        observatory_links = [
            AstronomyLink(
                name="Hubble Space Telescope",
                url="https://hubblesite.org/",
                category=LinkCategory.OBSERVATORY,
                emoji="🔭",
                description="Latest images and discoveries from Hubble",
                priority=1,
                tags=["space", "telescope", "images", "nasa"]
            ),
            AstronomyLink(
                name="James Webb Space Telescope",
                url="https://webb.nasa.gov/",
                category=LinkCategory.OBSERVATORY,
                emoji="🔭",
                description="Cutting-edge infrared astronomy",
                priority=1,
                tags=["space", "telescope", "infrared", "nasa"]
            ),
            AstronomyLink(
                name="European Southern Observatory",
                url="https://www.eso.org/",
                category=LinkCategory.OBSERVATORY,
                emoji="🔭",
                description="Ground-based astronomy from Chile",
                priority=1,
                tags=["ground", "telescope", "chile", "eso"]
            ),
            AstronomyLink(
                name="Chandra X-ray Observatory",
                url="https://chandra.harvard.edu/",
                category=LinkCategory.OBSERVATORY,
                emoji="🔭",
                description="X-ray astronomy and high-energy phenomena",
                priority=2,
                tags=["xray", "space", "telescope", "nasa"]
            ),
            AstronomyLink(
                name="Spitzer Space Telescope Archive",
                url="https://www.spitzer.caltech.edu/",
                category=LinkCategory.OBSERVATORY,
                emoji="🔭",
                description="Infrared space telescope archive",
                priority=2,
                tags=["infrared", "space", "telescope", "archive"]
            ),
        ]
        
        # Space Agencies
        space_agency_links = [
            AstronomyLink(
                name="NASA",
                url="https://www.nasa.gov/",
                category=LinkCategory.SPACE_AGENCY,
                emoji="🚀",
                description="National Aeronautics and Space Administration",
                priority=1,
                tags=["nasa", "missions", "space", "usa"]
            ),
            AstronomyLink(
                name="European Space Agency",
                url="https://www.esa.int/",
                category=LinkCategory.SPACE_AGENCY,
                emoji="🚀",
                description="European space missions and research",
                priority=1,
                tags=["esa", "missions", "space", "europe"]
            ),
            AstronomyLink(
                name="SpaceX",
                url="https://www.spacex.com/",
                category=LinkCategory.SPACE_AGENCY,
                emoji="🚀",
                description="Commercial spaceflight and missions",
                priority=1,
                tags=["spacex", "commercial", "rockets", "mars"]
            ),
            AstronomyLink(
                name="JAXA (Japan)",
                url="https://global.jaxa.jp/",
                category=LinkCategory.SPACE_AGENCY,
                emoji="🚀",
                description="Japanese space exploration",
                priority=2,
                tags=["jaxa", "japan", "missions", "space"]
            ),
            AstronomyLink(
                name="NASA Missions",
                url="https://www.nasa.gov/missions/",
                category=LinkCategory.SPACE_AGENCY,
                emoji="🚀",
                description="Current and upcoming NASA missions",
                priority=1,
                tags=["nasa", "missions", "current", "upcoming"]
            ),
        ]
        
        # Astronomy Tools
        astronomy_tool_links = [
            AstronomyLink(
                name="SkySafari",
                url="https://skysafariastronomy.com/",
                category=LinkCategory.ASTRONOMY_TOOL,
                emoji="📱",
                description="Mobile planetarium and telescope control",
                priority=1,
                tags=["mobile", "app", "planetarium", "telescope"]
            ),
            AstronomyLink(
                name="Stellarium",
                url="https://stellarium.org/",
                category=LinkCategory.ASTRONOMY_TOOL,
                emoji="📱",
                description="Free open-source planetarium software",
                priority=1,
                tags=["free", "software", "planetarium", "desktop"]
            ),
            AstronomyLink(
                name="Heavens Above",
                url="https://www.heavens-above.com/",
                category=LinkCategory.ASTRONOMY_TOOL,
                emoji="📱",
                description="Satellite tracking and predictions",
                priority=1,
                tags=["satellites", "tracking", "iss", "predictions"]
            ),
            AstronomyLink(
                name="TimeAndDate Astronomy",
                url="https://www.timeanddate.com/astronomy/",
                category=LinkCategory.ASTRONOMY_TOOL,
                emoji="📱",
                description="Astronomical calculations and calendars",
                priority=2,
                tags=["calculations", "calendar", "sunrise", "sunset"]
            ),
            AstronomyLink(
                name="In-The-Sky.org",
                url="https://in-the-sky.org/",
                category=LinkCategory.ASTRONOMY_TOOL,
                emoji="📱",
                description="Sky maps and astronomical events",
                priority=1,
                tags=["sky", "maps", "events", "calendar"]
            ),
        ]
        
        # Tonight's Sky Resources
        tonight_sky_links = [
            AstronomyLink(
                name="EarthSky Tonight",
                url="https://earthsky.org/tonight/",
                category=LinkCategory.TONIGHT_SKY,
                emoji="🌌",
                description="What's visible in tonight's sky",
                priority=1,
                tags=["tonight", "visible", "current", "sky"]
            ),
            AstronomyLink(
                name="Sky & Telescope This Week",
                url="https://skyandtelescope.org/observing/this-weeks-sky-at-a-glance/",
                category=LinkCategory.TONIGHT_SKY,
                emoji="🌌",
                description="Weekly sky highlights and events",
                priority=1,
                tags=["weekly", "highlights", "observing", "events"]
            ),
            AstronomyLink(
                name="Astronomy Magazine Sky This Month",
                url="https://astronomy.com/observing/sky-this-month",
                category=LinkCategory.TONIGHT_SKY,
                emoji="🌌",
                description="Monthly sky guide and observing tips",
                priority=2,
                tags=["monthly", "guide", "observing", "tips"]
            ),
        ]
        
        # Moon Information
        moon_info_links = [
            AstronomyLink(
                name="Moon Phase Calendar",
                url="https://www.timeanddate.com/moon/phases/",
                category=LinkCategory.MOON_INFO,
                emoji="🌕",
                description="Current moon phase and lunar calendar",
                priority=1,
                tags=["moon", "phases", "calendar", "lunar"]
            ),
            AstronomyLink(
                name="NASA Moon Information",
                url="https://moon.nasa.gov/",
                category=LinkCategory.MOON_INFO,
                emoji="🌕",
                description="Comprehensive moon facts and data",
                priority=1,
                tags=["nasa", "moon", "facts", "data"]
            ),
            AstronomyLink(
                name="Lunar Reconnaissance Orbiter",
                url="https://www.nasa.gov/mission_pages/LRO/main/index.html",
                category=LinkCategory.MOON_INFO,
                emoji="🌕",
                description="Latest lunar exploration and images",
                priority=2,
                tags=["lunar", "exploration", "images", "orbiter"]
            ),
        ]
        
        # Educational Resources
        educational_links = [
            AstronomyLink(
                name="NASA Education",
                url="https://www.nasa.gov/audience/foreducators/",
                category=LinkCategory.EDUCATIONAL,
                emoji="📚",
                description="Educational resources and activities",
                priority=1,
                tags=["education", "learning", "activities", "nasa"]
            ),
            AstronomyLink(
                name="Coursera Astronomy Courses",
                url="https://www.coursera.org/browse/physical-science-and-engineering/physics-and-astronomy",
                category=LinkCategory.EDUCATIONAL,
                emoji="📚",
                description="Online astronomy courses and lectures",
                priority=2,
                tags=["courses", "online", "learning", "university"]
            ),
            AstronomyLink(
                name="Khan Academy Cosmology",
                url="https://www.khanacademy.org/science/cosmology-and-astronomy",
                category=LinkCategory.EDUCATIONAL,
                emoji="📚",
                description="Free astronomy and cosmology lessons",
                priority=1,
                tags=["free", "lessons", "cosmology", "basics"]
            ),
        ]
        
        # Live Data Sources
        live_data_links = [
            AstronomyLink(
                name="Space Weather",
                url="https://www.spaceweather.com/",
                category=LinkCategory.LIVE_DATA,
                emoji="📡",
                description="Real-time space weather and solar activity",
                priority=1,
                tags=["space", "weather", "solar", "realtime"]
            ),
            AstronomyLink(
                name="NASA Solar Dynamics Observatory",
                url="https://sdo.gsfc.nasa.gov/",
                category=LinkCategory.LIVE_DATA,
                emoji="📡",
                description="Live solar observations and data",
                priority=2,
                tags=["solar", "live", "observations", "sun"]
            ),
            AstronomyLink(
                name="International Space Station Tracker",
                url="https://spotthestation.nasa.gov/",
                category=LinkCategory.LIVE_DATA,
                emoji="📡",
                description="Track the ISS in real-time",
                priority=1,
                tags=["iss", "tracking", "realtime", "station"]
            ),
        ]
        
        # Community Resources
        community_links = [
            AstronomyLink(
                name="Reddit Astronomy",
                url="https://www.reddit.com/r/astronomy/",
                category=LinkCategory.COMMUNITY,
                emoji="👥",
                description="Astronomy community discussions",
                priority=2,
                tags=["community", "discussions", "reddit", "social"]
            ),
            AstronomyLink(
                name="CloudyNights",
                url="https://www.cloudynights.com/",
                category=LinkCategory.COMMUNITY,
                emoji="👥",
                description="Telescope and observing community",
                priority=2,
                tags=["telescopes", "observing", "community", "forum"]
            ),
            AstronomyLink(
                name="Astronomy Stack Exchange",
                url="https://astronomy.stackexchange.com/",
                category=LinkCategory.COMMUNITY,
                emoji="👥",
                description="Q&A for astronomy enthusiasts",
                priority=2,
                tags=["questions", "answers", "community", "help"]
            ),
        ]
        
        # Add all links to the database
        all_links = (
            observatory_links + space_agency_links + astronomy_tool_links +
            tonight_sky_links + moon_info_links + educational_links +
            live_data_links + community_links
        )
        
        for link in all_links:
            self._links[link.name.lower().replace(" ", "_")] = link
        
        logger.info(f"Initialized astronomy links database with {len(self._links)} links")
    
    def get_all_links(self) -> List[AstronomyLink]:
        """Get all astronomy links."""
        return list(self._links.values())
    
    def get_links_by_category(self, category: LinkCategory) -> List[AstronomyLink]:
        """Get links by category."""
        return [link for link in self._links.values() if link.category == category]
    
    def get_links_by_priority(self, priority: int) -> List[AstronomyLink]:
        """Get links by priority level."""
        return [link for link in self._links.values() if link.priority == priority]
    
    def get_high_priority_links(self) -> List[AstronomyLink]:
        """Get high priority links (priority 1)."""
        return self.get_links_by_priority(1)
    
    def search_links(self, query: str) -> List[AstronomyLink]:
        """Search links by name, description, or tags."""
        query = query.lower()
        results = []
        
        for link in self._links.values():
            if (query in link.name.lower() or 
                query in link.description.lower() or
                any(query in tag.lower() for tag in link.tags)):
                results.append(link)
        
        return results
    
    def get_category_emoji(self, category: LinkCategory) -> str:
        """Get emoji for link category."""
        category_emojis = {
            LinkCategory.OBSERVATORY: "🔭",
            LinkCategory.SPACE_AGENCY: "🚀",
            LinkCategory.ASTRONOMY_TOOL: "📱",
            LinkCategory.EDUCATIONAL: "📚",
            LinkCategory.LIVE_DATA: "📡",
            LinkCategory.COMMUNITY: "👥",
            LinkCategory.TONIGHT_SKY: "🌌",
            LinkCategory.MOON_INFO: "🌕",
        }
        return category_emojis.get(category, "🔗")
    
    def get_suggested_links_for_event_type(self, event_type: str) -> List[AstronomyLink]:
        """Get suggested links based on astronomy event type."""
        suggestions = []
        
        # Map event types to specific preferred links for better differentiation
        event_specific_map = {
            "apod": ["Hubble Space Telescope", "James Webb Space Telescope"],
            "iss_pass": ["International Space Station Tracker", "Heavens Above"],
            "near_earth_object": ["European Southern Observatory", "Space Weather"],
            "moon_phase": ["Moon Phase Calendar", "NASA Moon Information"],
            "planetary_event": ["EarthSky Tonight", "In-The-Sky.org"],
            "meteor_shower": ["Sky & Telescope This Week", "Stellarium"],
            "solar_event": ["NASA Solar Dynamics Observatory", "Space Weather"],
            "satellite_image": ["NASA", "European Space Agency"],
        }
        
        # Get specific preferred links for this event type
        preferred_names = event_specific_map.get(event_type.lower(), [])
        
        # Find the actual link objects for preferred names
        for name in preferred_names:
            name_key = name.lower().replace(" ", "_")
            if name_key in self._links:
                suggestions.append(self._links[name_key])
        
        # If we don't have enough suggestions, fall back to category-based approach
        if len(suggestions) < 2:
            event_category_map = {
                "apod": [LinkCategory.OBSERVATORY, LinkCategory.SPACE_AGENCY],
                "iss_pass": [LinkCategory.LIVE_DATA, LinkCategory.ASTRONOMY_TOOL],
                "near_earth_object": [LinkCategory.OBSERVATORY, LinkCategory.LIVE_DATA],
                "moon_phase": [LinkCategory.MOON_INFO, LinkCategory.TONIGHT_SKY],
                "planetary_event": [LinkCategory.TONIGHT_SKY, LinkCategory.ASTRONOMY_TOOL],
                "meteor_shower": [LinkCategory.TONIGHT_SKY, LinkCategory.ASTRONOMY_TOOL],
                "solar_event": [LinkCategory.LIVE_DATA, LinkCategory.OBSERVATORY],
                "satellite_image": [LinkCategory.SPACE_AGENCY, LinkCategory.LIVE_DATA],
            }
            
            relevant_categories = event_category_map.get(event_type.lower(), [LinkCategory.TONIGHT_SKY])
            
            for category in relevant_categories:
                category_links = self.get_links_by_category(category)
                # Get links not already in suggestions
                new_links = [link for link in category_links if link not in suggestions]
                sorted_links = sorted(new_links, key=lambda x: x.priority)
                suggestions.extend(sorted_links[:2])
                if len(suggestions) >= 4:
                    break
        
        return suggestions[:4]  # Limit to 4 suggestions


# Global instance of the astronomy links database
astronomy_links_db = AstronomyLinksDatabase()