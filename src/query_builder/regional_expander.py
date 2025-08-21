"""
Regional Expansion System

Handles geographic expansion of query templates with city/state variations,
regional grouping, and geographic data management.
"""

import logging
import json
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import random

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Types of geographic regions."""
    CITY = "city"
    STATE = "state"
    COUNTY = "county"
    METRO_AREA = "metro_area"
    ZIP_CODE = "zip_code"
    REGION = "region"


@dataclass(frozen=True)
class GeographicLocation:
    """Represents a geographic location with metadata."""
    
    name: str
    region_type: RegionType
    state: str
    state_code: str
    country: str = "US"
    population: Optional[int] = None
    metro_area: Optional[str] = None
    county: Optional[str] = None
    zip_codes: Tuple[str, ...] = field(default_factory=tuple)
    aliases: Tuple[str, ...] = field(default_factory=tuple)
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def __post_init__(self):
        """Normalize location data after initialization."""
        # Use object.__setattr__ for frozen dataclass
        object.__setattr__(self, 'name', self.name.strip())
        object.__setattr__(self, 'state', self.state.strip())
        object.__setattr__(self, 'state_code', self.state_code.upper().strip())
        
        # Add common aliases if not provided
        if not self.aliases:
            object.__setattr__(self, 'aliases', tuple(self._generate_aliases()))
    
    def _generate_aliases(self) -> Tuple[str, ...]:
        """Generate common aliases for the location."""
        aliases = []
        
        # Add variations of the name
        name_lower = self.name.lower()
        if " " in self.name:
            # Add version without spaces
            aliases.append(self.name.replace(" ", ""))
            # Add version with underscores
            aliases.append(self.name.replace(" ", "_"))
        
        # Add metro area variations
        if self.metro_area and self.metro_area != self.name:
            aliases.append(self.metro_area)
        
        # Add county variations if applicable
        if self.county and "county" not in name_lower:
            aliases.append(f"{self.name} County")
        
        return tuple(aliases)
    
    def get_search_variations(self) -> List[str]:
        """Get all search variations for this location."""
        variations = [self.name]
        variations.extend(list(self.aliases))
        
        # Add state combinations
        variations.extend([
            f"{self.name}, {self.state}",
            f"{self.name}, {self.state_code}",
            f"{self.name} {self.state}",
            f"{self.name} {self.state_code}"
        ])
        
        # Add metro area combinations if available
        if self.metro_area and self.metro_area != self.name:
            variations.extend([
                f"{self.metro_area}, {self.state}",
                f"{self.metro_area} {self.state_code}"
            ])
        
        return list(set(variations))  # Remove duplicates
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert location to dictionary representation."""
        return {
            'name': self.name,
            'region_type': self.region_type.value,
            'state': self.state,
            'state_code': self.state_code,
            'country': self.country,
            'population': self.population,
            'metro_area': self.metro_area,
            'county': self.county,
            'zip_codes': list(self.zip_codes),
            'aliases': list(self.aliases),
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeographicLocation':
        """Create location from dictionary representation."""
        return cls(
            name=data['name'],
            region_type=RegionType(data['region_type']),
            state=data['state'],
            state_code=data['state_code'],
            country=data.get('country', 'US'),
            population=data.get('population'),
            metro_area=data.get('metro_area'),
            county=data.get('county'),
            zip_codes=tuple(data.get('zip_codes', [])),
            aliases=tuple(data.get('aliases', [])),
            priority=data.get('priority', 1)
        )


class RegionalExpander:
    """
    Handles regional expansion of query templates with intelligent
    geographic data management and optimization.
    """
    
    def __init__(self, geographic_data_file: Optional[Path] = None):
        """
        Initialize regional expander.
        
        Args:
            geographic_data_file: Optional path to custom geographic data
        """
        self.locations: Dict[str, GeographicLocation] = {}
        self.states_data: Dict[str, Dict[str, Any]] = {}
        self.metro_areas: Dict[str, List[str]] = {}
        
        self._load_default_locations()
        
        if geographic_data_file and geographic_data_file.exists():
            self._load_geographic_data(geographic_data_file)
        
        logger.info(f"RegionalExpander initialized with {len(self.locations)} locations")
    
    def _load_default_locations(self):
        """Load comprehensive default geographic data."""
        
        # Major US cities with metro areas
        major_cities = [
            # Northeast
            ("New York", "New York", "NY", 8_400_000, "New York-Newark-Jersey City", 1),
            ("Philadelphia", "Pennsylvania", "PA", 1_580_000, "Philadelphia-Camden-Wilmington", 1),
            ("Boston", "Massachusetts", "MA", 685_000, "Boston-Cambridge-Newton", 1),
            ("Washington", "District of Columbia", "DC", 705_000, "Washington-Arlington-Alexandria", 1),
            
            # Southeast
            ("Atlanta", "Georgia", "GA", 498_000, "Atlanta-Sandy Springs-Roswell", 1),
            ("Miami", "Florida", "FL", 470_000, "Miami-Fort Lauderdale-West Palm Beach", 1),
            ("Tampa", "Florida", "FL", 387_000, "Tampa-St. Petersburg-Clearwater", 1),
            ("Orlando", "Florida", "FL", 307_000, "Orlando-Kissimmee-Sanford", 1),
            ("Charlotte", "North Carolina", "NC", 885_000, "Charlotte-Concord-Gastonia", 1),
            ("Jacksonville", "Florida", "FL", 949_000, "Jacksonville", 1),
            
            # Midwest
            ("Chicago", "Illinois", "IL", 2_670_000, "Chicago-Naperville-Elgin", 1),
            ("Detroit", "Michigan", "MI", 672_000, "Detroit-Warren-Dearborn", 1),
            ("Cleveland", "Ohio", "OH", 385_000, "Cleveland-Elyria", 1),
            ("Columbus", "Ohio", "OH", 898_000, "Columbus", 1),
            ("Indianapolis", "Indiana", "IN", 887_000, "Indianapolis-Carmel-Anderson", 1),
            ("Milwaukee", "Wisconsin", "WI", 590_000, "Milwaukee-Waukesha-West Allis", 1),
            
            # West
            ("Los Angeles", "California", "CA", 3_970_000, "Los Angeles-Long Beach-Anaheim", 1),
            ("San Francisco", "California", "CA", 875_000, "San Francisco-Oakland-Hayward", 1),
            ("San Diego", "California", "CA", 1_420_000, "San Diego-Carlsbad", 1),
            ("Phoenix", "Arizona", "AZ", 1_680_000, "Phoenix-Mesa-Scottsdale", 1),
            ("Las Vegas", "Nevada", "NV", 651_000, "Las Vegas-Henderson-Paradise", 1),
            ("Seattle", "Washington", "WA", 753_000, "Seattle-Tacoma-Bellevue", 1),
            ("Portland", "Oregon", "OR", 652_000, "Portland-Vancouver-Hillsboro", 1),
            ("Denver", "Colorado", "CO", 715_000, "Denver-Aurora-Lakewood", 1),
            
            # Southwest
            ("Houston", "Texas", "TX", 2_320_000, "Houston-The Woodlands-Sugar Land", 1),
            ("Dallas", "Texas", "TX", 1_340_000, "Dallas-Fort Worth-Arlington", 1),
            ("San Antonio", "Texas", "TX", 1_530_000, "San Antonio-New Braunfels", 1),
            ("Austin", "Texas", "TX", 965_000, "Austin-Round Rock", 1),
        ]
        
        # Add major cities
        for city_data in major_cities:
            name, state, state_code, population, metro_area, priority = city_data
            location = GeographicLocation(
                name=name,
                region_type=RegionType.CITY,
                state=state,
                state_code=state_code,
                population=population,
                metro_area=metro_area,
                priority=priority
            )
            self.locations[name.lower()] = location
        
        # Secondary cities
        secondary_cities = [
            ("Albuquerque", "New Mexico", "NM", 560_000, 2),
            ("Tucson", "Arizona", "AZ", 548_000, 2),
            ("Fresno", "California", "CA", 542_000, 2),
            ("Sacramento", "California", "CA", 513_000, 2),
            ("Kansas City", "Missouri", "MO", 495_000, 2),
            ("Mesa", "Arizona", "AZ", 518_000, 2),
            ("Virginia Beach", "Virginia", "VA", 459_000, 2),
            ("Omaha", "Nebraska", "NE", 478_000, 2),
            ("Colorado Springs", "Colorado", "CO", 478_000, 2),
            ("Raleigh", "North Carolina", "NC", 474_000, 2),
            ("Long Beach", "California", "CA", 462_000, 2),
            ("Virginia Beach", "Virginia", "VA", 459_000, 2),
            ("Miami", "Florida", "FL", 442_000, 2),
            ("Oakland", "California", "CA", 433_000, 2),
            ("Minneapolis", "Minnesota", "MN", 429_000, 2),
            ("Tulsa", "Oklahoma", "OK", 413_000, 2),
            ("Arlington", "Texas", "TX", 398_000, 2),
            ("New Orleans", "Louisiana", "LA", 390_000, 2),
            ("Wichita", "Kansas", "KS", 389_000, 2),
            ("Cleveland", "Ohio", "OH", 385_000, 2),
        ]
        
        for city_data in secondary_cities:
            name, state, state_code, population, priority = city_data
            location = GeographicLocation(
                name=name,
                region_type=RegionType.CITY,
                state=state,
                state_code=state_code,
                population=population,
                priority=priority
            )
            self.locations[name.lower()] = location
        
        # Load state data
        self._load_state_data()
    
    def _load_state_data(self):
        """Load US state information."""
        states = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
            'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
            'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
            'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
            'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
            'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
            'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
            'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
            'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
        }
        
        for code, name in states.items():
            self.states_data[code] = {
                'name': name,
                'code': code,
                'cities': [loc.name for loc in self.locations.values() 
                          if loc.state_code == code]
            }
    
    def get_locations_by_state(self, state_code: str) -> List[GeographicLocation]:
        """Get all locations in a specific state."""
        state_code = state_code.upper()
        return [loc for loc in self.locations.values() if loc.state_code == state_code]
    
    def get_locations_by_priority(self, priority: int) -> List[GeographicLocation]:
        """Get locations by priority level."""
        return [loc for loc in self.locations.values() if loc.priority == priority]
    
    def get_top_cities(self, limit: int = 50) -> List[GeographicLocation]:
        """Get top cities by population."""
        cities = [loc for loc in self.locations.values() 
                 if loc.region_type == RegionType.CITY and loc.population]
        return sorted(cities, key=lambda x: x.population or 0, reverse=True)[:limit]
    
    def get_metro_areas(self) -> Dict[str, List[str]]:
        """Get metro areas and their constituent cities."""
        metro_areas = {}
        for location in self.locations.values():
            if location.metro_area:
                if location.metro_area not in metro_areas:
                    metro_areas[location.metro_area] = []
                metro_areas[location.metro_area].append(location.name)
        return metro_areas
    
    def expand_template_regionally(self, 
                                 template: str,
                                 variable_name: str = "city",
                                 max_locations: Optional[int] = None,
                                 priority_filter: Optional[int] = None,
                                 state_filter: Optional[List[str]] = None,
                                 include_variations: bool = True) -> List[Tuple[str, GeographicLocation]]:
        """
        Expand a template with regional variations.
        
        Args:
            template: Template string with {variable_name} placeholder
            variable_name: Name of the geographic variable to expand
            max_locations: Maximum number of locations to include
            priority_filter: Only include locations with this priority
            state_filter: Only include locations from these states
            include_variations: Include location name variations
            
        Returns:
            List of (expanded_query, location) tuples
        """
        # Filter locations based on criteria
        locations = list(self.locations.values())
        
        if priority_filter is not None:
            locations = [loc for loc in locations if loc.priority == priority_filter]
        
        if state_filter:
            state_codes = [s.upper() for s in state_filter]
            locations = [loc for loc in locations if loc.state_code in state_codes]
        
        # Limit number of locations if specified
        if max_locations:
            # Sort by priority and population for best results
            locations.sort(key=lambda x: (x.priority, -(x.population or 0)))
            locations = locations[:max_locations]
        
        expanded_queries = []
        
        for location in locations:
            if include_variations:
                # Use all search variations for the location
                variations = location.get_search_variations()
            else:
                # Use just the primary name
                variations = [location.name]
            
            for variation in variations:
                try:
                    expanded_query = template.format(**{variable_name: variation})
                    expanded_queries.append((expanded_query, location))
                except KeyError as e:
                    logger.warning(f"Template variable error: {e}")
                    continue
        
        return expanded_queries
    
    def batch_expand_templates(self,
                             templates: List[str],
                             variable_mapping: Dict[str, str] = None,
                             max_per_template: Optional[int] = None,
                             deduplicate: bool = True) -> List[Tuple[str, Optional[GeographicLocation]]]:
        """
        Expand multiple templates with regional variations.
        
        Args:
            templates: List of template strings
            variable_mapping: Custom variable name mapping
            max_per_template: Max locations per template
            deduplicate: Remove duplicate queries
            
        Returns:
            List of (expanded_query, location) tuples
        """
        all_expanded = []
        default_variable = variable_mapping.get('default', 'city') if variable_mapping else 'city'
        
        for template in templates:
            # Determine variable name for this template
            variable_name = default_variable
            if variable_mapping:
                for var, mapping in variable_mapping.items():
                    if var in template:
                        variable_name = mapping
                        break
            
            expanded = self.expand_template_regionally(
                template=template,
                variable_name=variable_name,
                max_locations=max_per_template
            )
            all_expanded.extend(expanded)
        
        if deduplicate:
            # Remove duplicate queries while preserving location info
            seen_queries = set()
            deduplicated = []
            for query, location in all_expanded:
                if query not in seen_queries:
                    seen_queries.add(query)
                    deduplicated.append((query, location))
            return deduplicated
        
        return all_expanded
    
    def get_regional_distribution(self, 
                                queries: List[Tuple[str, GeographicLocation]]) -> Dict[str, Any]:
        """Get distribution statistics for regional expansion."""
        state_counts = {}
        priority_counts = {}
        metro_counts = {}
        
        for query, location in queries:
            # Count by state
            state = location.state_code
            state_counts[state] = state_counts.get(state, 0) + 1
            
            # Count by priority
            priority = location.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Count by metro area
            if location.metro_area:
                metro = location.metro_area
                metro_counts[metro] = metro_counts.get(metro, 0) + 1
        
        return {
            'total_queries': len(queries),
            'unique_states': len(state_counts),
            'state_distribution': state_counts,
            'priority_distribution': priority_counts,
            'metro_area_distribution': metro_counts,
            'top_states': sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def suggest_locations_for_vertical(self, 
                                     vertical: str,
                                     max_suggestions: int = 20) -> List[GeographicLocation]:
        """
        Suggest optimal locations for a specific business vertical.
        
        Different verticals may perform better in different geographic areas.
        """
        all_locations = list(self.locations.values())
        
        # Simple heuristic: prioritize by population and priority
        # In a full implementation, this could use vertical-specific data
        all_locations.sort(key=lambda x: (x.priority, -(x.population or 0)))
        
        return all_locations[:max_suggestions]
    
    def add_location(self, location: GeographicLocation):
        """Add new location to the expander."""
        key = location.name.lower()
        self.locations[key] = location
        logger.info(f"Added location: {location.name}, {location.state_code}")
    
    def remove_location(self, location_name: str) -> bool:
        """Remove location from the expander."""
        key = location_name.lower()
        if key in self.locations:
            del self.locations[key]
            logger.info(f"Removed location: {location_name}")
            return True
        return False
    
    def save_geographic_data(self, file_path: Path):
        """Save geographic data to JSON file."""
        data = {
            name: location.to_dict()
            for name, location in self.locations.items()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(self.locations)} locations to {file_path}")
    
    def _load_geographic_data(self, file_path: Path):
        """Load geographic data from JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for name, location_data in data.items():
                location = GeographicLocation.from_dict(location_data)
                self.locations[name] = location
            
            logger.info(f"Loaded {len(data)} locations from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading geographic data from {file_path}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get regional expander statistics."""
        locations_by_state = {}
        locations_by_priority = {}
        total_population = 0
        
        for location in self.locations.values():
            # Count by state
            state = location.state_code
            locations_by_state[state] = locations_by_state.get(state, 0) + 1
            
            # Count by priority
            priority = location.priority
            locations_by_priority[priority] = locations_by_priority.get(priority, 0) + 1
            
            # Sum population
            if location.population:
                total_population += location.population
        
        return {
            'total_locations': len(self.locations),
            'locations_by_state': locations_by_state,
            'locations_by_priority': locations_by_priority,
            'total_population_covered': total_population,
            'unique_states': len(locations_by_state),
            'unique_metro_areas': len(self.get_metro_areas())
        }