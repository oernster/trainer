"""
Essential Station Cache Service

Provides instant access to essential UK railway stations for immediate UI responsiveness.
This service contains a curated list of the most commonly used stations to enable
instant population of station selection widgets without waiting for full data loading.
"""

import logging
from typing import List, Set, Dict, Any, Optional
from pathlib import Path
import json
import time

logger = logging.getLogger(__name__)


class EssentialStationCache:
    """
    Fast-access cache for essential UK railway stations.
    
    This service provides immediate access to commonly used stations without
    requiring heavy JSON file processing, enabling instant UI responsiveness.
    """
    
    def __init__(self):
        """Initialize the essential station cache."""
        self.logger = logging.getLogger(__name__)
        self._essential_stations: List[str] = []
        self._underground_stations: List[str] = []
        self._all_stations_cache: List[str] = []
        self._load_time: float = 0.0
        
        # Load essential stations immediately
        self._load_essential_stations()
        
        self.logger.info(f"EssentialStationCache initialized with {len(self._all_stations_cache)} stations in {self._load_time:.3f}s")
    
    def _load_essential_stations(self) -> None:
        """Load essential stations from predefined lists."""
        start_time = time.time()
        
        # Essential National Rail stations (most commonly used)
        self._essential_stations = [
            # London Terminals
            "London Waterloo", "London Victoria", "London Bridge", "London King's Cross",
            "London Paddington", "London Liverpool Street", "London Euston", "London St Pancras International",
            "London Marylebone", "London Cannon Street", "London Blackfriars", "London Charing Cross",
            "London Fenchurch Street",
            
            # Major Interchanges
            "Clapham Junction", "Reading", "Birmingham New Street", "Manchester Piccadilly",
            "Leeds", "Newcastle", "Edinburgh Waverley", "Glasgow Central", "Cardiff Central",
            "Bristol Temple Meads", "Liverpool Lime Street", "Sheffield", "Nottingham",
            "Leicester", "Derby", "York", "Preston", "Crewe", "Stafford", "Coventry",
            
            # South East
            "Brighton", "Gatwick Airport", "East Croydon", "Woking", "Guildford",
            "Portsmouth Harbour", "Southampton Central", "Winchester", "Basingstoke",
            "Farnborough", "Fleet", "Haslemere", "Petersfield", "Horsham", "Crawley",
            "Redhill", "Dorking", "Epsom", "Kingston", "Wimbledon", "Raynes Park",
            "New Malden", "Surbiton", "Thames Ditton", "Esher", "Oxshott", "Cobham & Stoke d'Abernon",
            
            # South West
            "Exeter St Davids", "Plymouth", "Truro", "Penzance", "Bath Spa", "Swindon",
            "Gloucester", "Cheltenham Spa", "Worcester Foregate Street", "Hereford",
            "Newport (South Wales)", "Swansea", "Carmarthen", "Aberystwyth", "Bangor (Gwynedd)",
            
            # Midlands
            "Oxford", "Banbury", "Leamington Spa", "Warwick", "Stratford-upon-Avon",
            "Worcester Shrub Hill", "Kidderminster", "Stourbridge Junction", "Wolverhampton",
            "Walsall", "Tamworth", "Burton-on-Trent", "Loughborough", "Market Harborough",
            
            # East
            "Cambridge", "Peterborough", "Norwich", "Ipswich", "Colchester", "Chelmsford",
            "Southend Victoria", "Southend Central", "Clacton-on-Sea", "Harwich International",
            "King's Lynn", "Great Yarmouth", "Lowestoft", "Bury St Edmunds", "Newmarket",
            
            # North
            "Manchester Oxford Road", "Manchester Airport", "Stockport", "Macclesfield",
            "Chester", "Liverpool Central", "Liverpool South Parkway", "Warrington Central",
            "Wigan North Western", "Bolton", "Blackpool North", "Lancaster", "Carlisle",
            "Penrith", "Oxenholme Lake District", "Windermere", "Barrow-in-Furness",
            
            # Scotland
            "Glasgow Queen Street", "Stirling", "Perth", "Dundee", "Aberdeen", "Inverness",
            "Fort William", "Mallaig", "Kyle of Lochalsh", "Thurso", "Wick", "Stranraer",
            "Dumfries", "Ayr", "Kilmarnock", "Paisley Gilmour Street", "Motherwell",
            "Hamilton Central", "East Kilbride", "Lanark", "Balloch", "Helensburgh Central",
            
            # Wales
            "Wrexham General", "Rhyl", "Llandudno", "Holyhead", "Pwllheli", "Machynlleth",
            "Shrewsbury", "Welshpool", "Newtown (Powys)", "Llandrindod", "Builth Road",
            "Llanwrtyd", "Sugar Loaf", "Llandovery", "Llandeilo", "Ferryside", "Kidwelly",
            "Pembrey & Burry Port", "Llanelli", "Gowerton", "Port Talbot Parkway",
            "Bridgend", "Pontypridd", "Merthyr Tydfil", "Aberdare", "Treherbert",
            "Rhondda", "Tonypandy", "Porth", "Ferndale", "Tylorstown", "Pentre",
            "Ystrad Rhondda", "Llwynypia", "Tonyrefail", "Penygraig", "Dinas Rhondda",
            
            # Northern Ireland (if applicable)
            "Belfast Central", "Belfast Great Victoria Street", "Lisburn", "Portadown",
            "Bangor (Northern Ireland)", "Larne Harbour", "Coleraine", "Londonderry"
        ]
        
        # Essential Underground stations (major stations and interchanges)
        self._underground_stations = [
            # London Underground - Major stations and interchanges
            "Baker Street", "Bond Street", "Oxford Circus", "Piccadilly Circus", "Leicester Square",
            "Covent Garden", "Holborn", "Russell Square", "Tottenham Court Road", "Goodge Street",
            "Warren Street", "Euston Square", "Great Portland Street", "Regent's Park",
            "Marble Arch", "Hyde Park Corner", "Green Park", "Victoria", "St James's Park",
            "Westminster", "Embankment", "Temple", "Blackfriars", "Mansion House",
            "Cannon Street", "Monument", "Bank", "Liverpool Street", "Moorgate",
            "Barbican", "Farringdon", "King's Cross St Pancras", "Angel", "Old Street",
            "Shoreditch High Street", "Whitechapel", "Aldgate", "Aldgate East", "Tower Hill",
            "Tower Gateway", "London Bridge", "Borough", "Elephant & Castle", "Kennington",
            "Oval", "Stockwell", "Vauxhall", "Pimlico", "Sloane Square", "South Kensington",
            "Gloucester Road", "Earl's Court", "High Street Kensington", "Notting Hill Gate",
            "Bayswater", "Paddington", "Edgware Road", "Marylebone", "Baker Street",
            "Finchley Road", "Swiss Cottage", "St John's Wood", "Maida Vale", "Warwick Avenue",
            "Royal Oak", "Westbourne Park", "Ladbroke Grove", "Latimer Road", "Wood Lane",
            "White City", "East Acton", "North Acton", "West Acton", "Ealing Broadway",
            "Ealing Common", "Acton Town", "Hammersmith", "Ravenscourt Park", "Stamford Brook",
            "Turnham Green", "Chiswick Park", "Gunnersbury", "Kew Gardens", "Richmond",
            
            # Glasgow Subway
            "Buchanan Street", "St Enoch", "Bridge Street", "West Street", "Shields Road",
            "Kinning Park", "Cessnock", "Ibrox", "Govan", "Partick", "Kelvinhall",
            "Hillhead", "Kelvinbridge", "St George's Cross", "Cowcaddens",
            
            # Newcastle Metro
            "Central Station", "Monument", "Haymarket", "Jesmond", "West Jesmond",
            "Ilford Road", "Wansbeck Road", "Fawdon", "Kingston Park", "Airport",
            "Callerton Parkway", "Regent Centre", "Four Lane Ends", "Benton", "Longbenton",
            "Palmersville", "Shiremoor", "Monkseaton", "West Monkseaton", "Whitley Bay",
            "Tynemouth", "North Shields", "Meadow Well", "Percy Main", "Howdon",
            "Wallsend", "Walkergate", "Chillingham Road", "Byker", "Manors",
            "Gateshead", "Gateshead Stadium", "Felling", "Heworth", "Pelaw",
            "Hebburn", "Jarrow", "Bede", "Chichester", "South Shields",
            "Tyne Dock", "East Boldon", "Brockley Whins", "Northumberland Park",
            "Meadowell", "South Gosforth", "Wansbeck Road", "Bank Foot"
        ]
        
        # Combine all stations and sort
        all_stations_set = set(self._essential_stations + self._underground_stations)
        self._all_stations_cache = sorted(list(all_stations_set))
        
        self._load_time = time.time() - start_time
        
        self.logger.debug(f"Loaded {len(self._essential_stations)} essential National Rail stations")
        self.logger.debug(f"Loaded {len(self._underground_stations)} essential Underground stations")
        self.logger.debug(f"Total unique stations: {len(self._all_stations_cache)}")
    
    def get_essential_stations(self) -> List[str]:
        """
        Get the list of essential National Rail stations.
        
        Returns:
            List of essential station names for immediate UI population
        """
        return self._essential_stations.copy()
    
    def get_underground_stations(self) -> List[str]:
        """
        Get the list of essential Underground stations.
        
        Returns:
            List of essential Underground station names
        """
        return self._underground_stations.copy()
    
    def get_all_essential_stations(self) -> List[str]:
        """
        Get all essential stations (National Rail + Underground).
        
        Returns:
            Combined sorted list of all essential stations
        """
        return self._all_stations_cache.copy()
    
    def is_essential_station(self, station_name: str) -> bool:
        """
        Check if a station is in the essential stations list.
        
        Args:
            station_name: Name of the station to check
            
        Returns:
            True if the station is in the essential list
        """
        return station_name in self._all_stations_cache
    
    def get_station_suggestions(self, partial: str, limit: int = 10) -> List[str]:
        """
        Get station suggestions from essential stations only.
        
        Args:
            partial: Partial station name to match
            limit: Maximum number of suggestions to return
            
        Returns:
            List of matching station names from essential stations
        """
        if not partial or not partial.strip():
            return []
        
        partial_lower = partial.strip().lower()
        suggestions = []
        
        for station in self._all_stations_cache:
            station_lower = station.lower()
            score = 0
            
            # Exact match gets highest score
            if station_lower == partial_lower:
                score = 1000
            # Starts with gets high score
            elif station_lower.startswith(partial_lower):
                score = 900
            # Word starts with gets good score
            elif any(word.startswith(partial_lower) for word in station_lower.split()):
                score = 800
            # Contains gets medium score
            elif partial_lower in station_lower:
                score = 600
            
            if score > 0:
                suggestions.append((station, score))
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [suggestion[0] for suggestion in suggestions[:limit]]
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the essential station cache.
        
        Returns:
            Dictionary containing cache statistics
        """
        return {
            "essential_national_rail_stations": len(self._essential_stations),
            "essential_underground_stations": len(self._underground_stations),
            "total_unique_stations": len(self._all_stations_cache),
            "load_time_seconds": self._load_time,
            "cache_type": "in_memory_predefined"
        }


# Global instance for singleton access
_essential_cache: Optional[EssentialStationCache] = None


def get_essential_station_cache() -> EssentialStationCache:
    """
    Get the global essential station cache instance.
    
    Returns:
        The singleton EssentialStationCache instance
    """
    global _essential_cache
    if _essential_cache is None:
        _essential_cache = EssentialStationCache()
    return _essential_cache


def get_essential_stations() -> List[str]:
    """
    Quick access function to get all essential stations.
    
    Returns:
        List of all essential station names
    """
    return get_essential_station_cache().get_all_essential_stations()


def get_essential_station_suggestions(partial: str, limit: int = 10) -> List[str]:
    """
    Quick access function to get station suggestions from essential stations.
    
    Args:
        partial: Partial station name to match
        limit: Maximum number of suggestions to return
        
    Returns:
        List of matching station names
    """
    return get_essential_station_cache().get_station_suggestions(partial, limit)