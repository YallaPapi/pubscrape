"""
Location Manager - Handle cities, regions, and geographic data for query generation

Features:
- Load cities from CSV files
- Geographic radius calculations
- State/country grouping
- Location validation and normalization
- Coordinate support for radius searches
"""
import csv
import json
import logging
from typing import Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from pathlib import Path
import re
import time

# Optional geopy imports
try:
    from geopy.distance import geodesic
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    geodesic = None
    Nominatim = None

logger = logging.getLogger(__name__)


@dataclass
class Location:
    """Represents a geographic location"""
    name: str
    city: str = ""
    state: str = ""
    country: str = "US"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    population: Optional[int] = None
    timezone: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Normalize location data"""
        if not self.city and self.name:
            # Try to extract city from name
            parts = self.name.split(',')
            if len(parts) >= 1:
                self.city = parts[0].strip()
            if len(parts) >= 2:
                self.state = parts[1].strip()
    
    @property
    def full_name(self) -> str:
        """Full location name"""
        parts = [self.city or self.name]
        if self.state:
            parts.append(self.state)
        if self.country != "US":
            parts.append(self.country)
        return ", ".join(parts)
    
    @property
    def coordinates(self) -> Optional[Tuple[float, float]]:
        """Get coordinates as tuple"""
        if self.latitude is not None and self.longitude is not None:
            return (self.latitude, self.longitude)
        return None
    
    def distance_to(self, other: 'Location') -> Optional[float]:
        """Calculate distance to another location in kilometers"""
        if not GEOPY_AVAILABLE:
            return None
        if self.coordinates and other.coordinates:
            return geodesic(self.coordinates, other.coordinates).kilometers
        return None


@dataclass
class Region:
    """Represents a geographic region (state, province, etc.)"""
    name: str
    code: str
    country: str = "US"
    locations: List[Location] = field(default_factory=list)
    
    def add_location(self, location: Location):
        """Add a location to this region"""
        self.locations.append(location)
    
    @property
    def location_count(self) -> int:
        """Number of locations in this region"""
        return len(self.locations)


class LocationManager:
    """
    Manage geographic locations for query generation
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.locations: Dict[str, Location] = {}
        self.regions: Dict[str, Region] = {}
        self.geocoder = None
        self._location_index: Dict[str, Set[str]] = {}
        
        # Initialize geocoder with delay to avoid rate limits
        if GEOPY_AVAILABLE:
            try:
                self.geocoder = Nominatim(user_agent="pubscrape-query-generator", timeout=10)
            except Exception as e:
                logger.warning(f"Could not initialize geocoder: {e}")
        else:
            logger.warning("Geopy not available - geocoding features disabled")
    
    def load_from_csv(self, csv_file: str, encoding: str = 'utf-8'):
        """
        Load locations from CSV file
        
        Expected CSV format:
        city,state,country,latitude,longitude,population,timezone
        """
        csv_path = self.data_dir / csv_file
        if not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return
        
        loaded_count = 0
        try:
            with open(csv_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        location = self._create_location_from_row(row)
                        self.add_location(location)
                        loaded_count += 1
                    except Exception as e:
                        logger.error(f"Error processing row {loaded_count + 1}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading CSV file {csv_path}: {e}")
            return
        
        logger.info(f"Loaded {loaded_count} locations from {csv_file}")
        self._build_index()
    
    def _create_location_from_row(self, row: Dict[str, str]) -> Location:
        """Create Location object from CSV row"""
        # Handle different column name variations
        city = row.get('city') or row.get('City') or row.get('name') or row.get('Name')
        state = row.get('state') or row.get('State') or row.get('region') or row.get('Region')
        country = row.get('country') or row.get('Country') or 'US'
        
        # Parse coordinates
        latitude = None
        longitude = None
        try:
            if row.get('latitude') or row.get('lat'):
                latitude = float(row.get('latitude') or row.get('lat'))
            if row.get('longitude') or row.get('lng') or row.get('lon'):
                longitude = float(row.get('longitude') or row.get('lng') or row.get('lon'))
        except (ValueError, TypeError):
            pass
        
        # Parse population
        population = None
        try:
            if row.get('population'):
                population = int(float(row.get('population')))
        except (ValueError, TypeError):
            pass
        
        return Location(
            name=city or "Unknown",
            city=city or "",
            state=state or "",
            country=country,
            latitude=latitude,
            longitude=longitude,
            population=population,
            timezone=row.get('timezone')
        )
    
    def add_location(self, location: Location):
        """Add a location to the manager"""
        # Use full name as key for uniqueness
        key = self._normalize_key(location.full_name)
        self.locations[key] = location
        
        # Add to region
        if location.state:
            region_key = f"{location.state}, {location.country}"
            if region_key not in self.regions:
                self.regions[region_key] = Region(
                    name=location.state,
                    code=location.state,
                    country=location.country
                )
            self.regions[region_key].add_location(location)
    
    def _normalize_key(self, name: str) -> str:
        """Normalize location name for indexing"""
        return re.sub(r'[^\w\s]', '', name.lower().strip())
    
    def _build_index(self):
        """Build search index for fast lookups"""
        self._location_index.clear()
        
        for key, location in self.locations.items():
            # Index by various name parts
            search_terms = [
                location.name.lower(),
                location.city.lower(),
                location.full_name.lower()
            ]
            
            # Add aliases
            for alias in location.aliases:
                search_terms.append(alias.lower())
            
            # Add state abbreviations and full names
            if location.state:
                search_terms.extend([
                    location.state.lower(),
                    self._get_state_abbreviation(location.state)
                ])
            
            # Index each term
            for term in search_terms:
                if term:
                    normalized_term = self._normalize_key(term)
                    if normalized_term not in self._location_index:
                        self._location_index[normalized_term] = set()
                    self._location_index[normalized_term].add(key)
    
    def _get_state_abbreviation(self, state_name: str) -> str:
        """Get state abbreviation"""
        # Common US state abbreviations
        state_abbrevs = {
            'alabama': 'al', 'alaska': 'ak', 'arizona': 'az', 'arkansas': 'ar',
            'california': 'ca', 'colorado': 'co', 'connecticut': 'ct', 'delaware': 'de',
            'florida': 'fl', 'georgia': 'ga', 'hawaii': 'hi', 'idaho': 'id',
            'illinois': 'il', 'indiana': 'in', 'iowa': 'ia', 'kansas': 'ks',
            'kentucky': 'ky', 'louisiana': 'la', 'maine': 'me', 'maryland': 'md',
            'massachusetts': 'ma', 'michigan': 'mi', 'minnesota': 'mn', 'mississippi': 'ms',
            'missouri': 'mo', 'montana': 'mt', 'nebraska': 'ne', 'nevada': 'nv',
            'new hampshire': 'nh', 'new jersey': 'nj', 'new mexico': 'nm', 'new york': 'ny',
            'north carolina': 'nc', 'north dakota': 'nd', 'ohio': 'oh', 'oklahoma': 'ok',
            'oregon': 'or', 'pennsylvania': 'pa', 'rhode island': 'ri', 'south carolina': 'sc',
            'south dakota': 'sd', 'tennessee': 'tn', 'texas': 'tx', 'utah': 'ut',
            'vermont': 'vt', 'virginia': 'va', 'washington': 'wa', 'west virginia': 'wv',
            'wisconsin': 'wi', 'wyoming': 'wy'
        }
        return state_abbrevs.get(state_name.lower(), state_name.lower()[:2])
    
    def find_location(self, name: str) -> Optional[Location]:
        """Find a location by name"""
        normalized_name = self._normalize_key(name)
        
        # Direct lookup
        if normalized_name in self.locations:
            return self.locations[normalized_name]
        
        # Search index
        if normalized_name in self._location_index:
            location_keys = self._location_index[normalized_name]
            if location_keys:
                return self.locations[list(location_keys)[0]]
        
        # Partial match
        for term, location_keys in self._location_index.items():
            if normalized_name in term or term in normalized_name:
                if location_keys:
                    return self.locations[list(location_keys)[0]]
        
        return None
    
    def search_locations(self, query: str, limit: int = 10) -> List[Location]:
        """Search for locations matching a query"""
        normalized_query = self._normalize_key(query)
        results = []
        
        # Collect all matching location keys
        matching_keys = set()
        for term, location_keys in self._location_index.items():
            if normalized_query in term or term in normalized_query:
                matching_keys.update(location_keys)
        
        # Convert to Location objects and sort by relevance
        for key in matching_keys:
            if key in self.locations:
                results.append(self.locations[key])
        
        # Sort by population (larger cities first) or name
        results.sort(key=lambda x: (x.population or 0, x.name), reverse=True)
        
        return results[:limit]
    
    def get_locations_by_state(self, state: str) -> List[Location]:
        """Get all locations in a state"""
        state_normalized = state.lower().strip()
        results = []
        
        for location in self.locations.values():
            if (location.state.lower() == state_normalized or 
                self._get_state_abbreviation(location.state) == state_normalized):
                results.append(location)
        
        return sorted(results, key=lambda x: x.population or 0, reverse=True)
    
    def get_locations_near(self, center: Location, radius_km: float) -> List[Tuple[Location, float]]:
        """Get locations within radius of center location"""
        if not center.coordinates:
            return []
        
        results = []
        for location in self.locations.values():
            if location.coordinates and location != center:
                distance = center.distance_to(location)
                if distance and distance <= radius_km:
                    results.append((location, distance))
        
        # Sort by distance
        results.sort(key=lambda x: x[1])
        return results
    
    def get_major_cities(self, min_population: int = 50000, limit: int = 50) -> List[Location]:
        """Get major cities by population"""
        cities = [loc for loc in self.locations.values() 
                 if loc.population and loc.population >= min_population]
        cities.sort(key=lambda x: x.population, reverse=True)
        return cities[:limit]
    
    def geocode_location(self, location: Location) -> bool:
        """
        Add coordinates to a location using geocoding
        
        Returns:
            True if geocoding successful, False otherwise
        """
        if not GEOPY_AVAILABLE or not self.geocoder or location.coordinates:
            return False
        
        try:
            # Rate limiting
            time.sleep(1)
            
            geo_result = self.geocoder.geocode(location.full_name)
            if geo_result:
                location.latitude = geo_result.latitude
                location.longitude = geo_result.longitude
                logger.debug(f"Geocoded {location.full_name}: {location.coordinates}")
                return True
        
        except Exception as e:
            logger.error(f"Geocoding failed for {location.full_name}: {e}")
        
        return False
    
    def geocode_batch(self, locations: List[Location], max_requests: int = 100) -> int:
        """
        Batch geocode multiple locations
        
        Returns:
            Number of successfully geocoded locations
        """
        if not GEOPY_AVAILABLE or not self.geocoder:
            logger.warning("Geocoder not available for batch geocoding")
            return 0
        
        success_count = 0
        processed = 0
        
        for location in locations:
            if processed >= max_requests:
                break
            
            if not location.coordinates:
                if self.geocode_location(location):
                    success_count += 1
                processed += 1
        
        logger.info(f"Batch geocoded {success_count}/{processed} locations")
        return success_count
    
    def export_to_csv(self, filename: str):
        """Export locations to CSV file"""
        output_path = self.data_dir / filename
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['city', 'state', 'country', 'latitude', 'longitude', 
                           'population', 'timezone', 'full_name'])
            
            # Write locations
            for location in sorted(self.locations.values(), key=lambda x: x.full_name):
                writer.writerow([
                    location.city,
                    location.state,
                    location.country,
                    location.latitude or '',
                    location.longitude or '',
                    location.population or '',
                    location.timezone or '',
                    location.full_name
                ])
        
        logger.info(f"Exported {len(self.locations)} locations to {output_path}")
    
    def get_location_statistics(self) -> Dict[str, Union[int, Dict, List]]:
        """Get statistics about loaded locations"""
        stats = {
            'total_locations': len(self.locations),
            'total_regions': len(self.regions),
            'by_country': {},
            'by_state': {},
            'with_coordinates': 0,
            'with_population': 0,
            'top_cities': []
        }
        
        # Count by country and state
        for location in self.locations.values():
            country = location.country
            stats['by_country'][country] = stats['by_country'].get(country, 0) + 1
            
            if location.state:
                state_key = f"{location.state}, {country}"
                stats['by_state'][state_key] = stats['by_state'].get(state_key, 0) + 1
            
            if location.coordinates:
                stats['with_coordinates'] += 1
            
            if location.population:
                stats['with_population'] += 1
        
        # Top cities by population
        top_cities = sorted(
            [loc for loc in self.locations.values() if loc.population],
            key=lambda x: x.population,
            reverse=True
        )[:10]
        
        stats['top_cities'] = [(city.full_name, city.population) for city in top_cities]
        
        return stats
    
    def create_location_variations(self, location: Location) -> List[str]:
        """
        Create different string variations of a location for query generation
        
        Returns:
            List of location string variations
        """
        variations = []
        
        # Basic variations
        if location.city:
            variations.append(location.city)
        
        if location.city and location.state:
            variations.extend([
                f"{location.city}, {location.state}",
                f"{location.city} {location.state}",
                f"{location.city}, {self._get_state_abbreviation(location.state).upper()}"
            ])
        
        # Full name
        variations.append(location.full_name)
        
        # Add aliases
        variations.extend(location.aliases)
        
        # Remove duplicates and empty strings
        variations = list(set(var for var in variations if var.strip()))
        
        return variations


# Convenience functions
def create_us_cities_manager(data_dir: str = "data") -> LocationManager:
    """Create a LocationManager and load US cities"""
    manager = LocationManager(data_dir)
    try:
        manager.load_from_csv("cities.csv")
    except Exception as e:
        logger.warning(f"Could not load cities.csv: {e}")
    return manager


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    manager = LocationManager("data")
    
    # Add some sample locations
    sample_locations = [
        Location("Seattle", "Seattle", "Washington", "US", 47.6062, -122.3321, 737015),
        Location("Portland", "Portland", "Oregon", "US", 45.5152, -122.6784, 647805),
        Location("San Francisco", "San Francisco", "California", "US", 37.7749, -122.4194, 873965)
    ]
    
    for loc in sample_locations:
        manager.add_location(loc)
    
    # Test searching
    results = manager.search_locations("seattle")
    print(f"Found {len(results)} locations for 'seattle'")
    
    # Test distance calculation
    seattle = manager.find_location("Seattle")
    portland = manager.find_location("Portland")
    if seattle and portland:
        distance = seattle.distance_to(portland)
        print(f"Distance from Seattle to Portland: {distance:.1f} km")
    
    # Show statistics
    stats = manager.get_location_statistics()
    print(f"Location statistics: {stats}")