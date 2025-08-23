"""
Query Generator - Template engine for generating search queries

Supports multiple search engines and query patterns:
- Business searches: "[business_type] near [location]"
- Site-specific searches: "site:example.com [keywords]"
- Location-based searches with radius
- Multiple search engine formats
"""
import re
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class SearchEngine(Enum):
    """Supported search engines with their specific formats"""
    BING_MAPS = "bing_maps"
    GOOGLE_MAPS = "google_maps"
    BING_WEB = "bing_web"
    GOOGLE_WEB = "google_web"
    DUCKDUCKGO = "duckduckgo"


@dataclass
class QueryTemplate:
    """Template for generating queries"""
    name: str
    template: str
    variables: Set[str]
    engine: SearchEngine
    description: str = ""
    priority: int = 1
    
    def __post_init__(self):
        """Extract variables from template"""
        self.variables = set(re.findall(r'\{(\w+)\}', self.template))


@dataclass
class GeneratedQuery:
    """Generated query with metadata"""
    query: str
    template_name: str
    engine: SearchEngine
    variables: Dict[str, str]
    priority: int = 1
    estimated_results: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class QueryGenerator:
    """
    Advanced query generator with template engine and search engine support
    """
    
    def __init__(self):
        self.templates: Dict[str, QueryTemplate] = {}
        self.engine_formats = self._init_engine_formats()
        self._load_default_templates()
    
    def _init_engine_formats(self) -> Dict[SearchEngine, Dict]:
        """Initialize search engine specific formats and constraints"""
        return {
            SearchEngine.BING_MAPS: {
                'max_query_length': 500,
                'supports_radius': True,
                'location_format': 'near {location}',
                'special_operators': ['site:', 'filetype:', 'intitle:']
            },
            SearchEngine.GOOGLE_MAPS: {
                'max_query_length': 2048,
                'supports_radius': True,
                'location_format': 'near {location}',
                'special_operators': ['site:', 'filetype:', 'intitle:', 'inurl:']
            },
            SearchEngine.BING_WEB: {
                'max_query_length': 500,
                'supports_radius': False,
                'location_format': '{location}',
                'special_operators': ['site:', 'filetype:', 'intitle:', 'inurl:', 'contains:']
            },
            SearchEngine.GOOGLE_WEB: {
                'max_query_length': 2048,
                'supports_radius': False,
                'location_format': '{location}',
                'special_operators': ['site:', 'filetype:', 'intitle:', 'inurl:', 'related:', 'cache:']
            },
            SearchEngine.DUCKDUCKGO: {
                'max_query_length': 500,
                'supports_radius': False,
                'location_format': '{location}',
                'special_operators': ['site:', 'filetype:', 'intitle:']
            }
        }
    
    def _load_default_templates(self):
        """Load default query templates"""
        default_templates = [
            # Business location searches
            QueryTemplate(
                name="business_near_location",
                template="{business_type} near {location}",
                variables={"business_type", "location"},
                engine=SearchEngine.BING_MAPS,
                description="Find businesses near a specific location",
                priority=3
            ),
            QueryTemplate(
                name="business_in_city",
                template="{business_type} in {city}, {state}",
                variables={"business_type", "city", "state"},
                engine=SearchEngine.GOOGLE_MAPS,
                description="Find businesses in a specific city",
                priority=3
            ),
            # Site-specific searches
            QueryTemplate(
                name="site_specific_business",
                template="site:{domain} {business_type} {location}",
                variables={"domain", "business_type", "location"},
                engine=SearchEngine.GOOGLE_WEB,
                description="Search for businesses on specific website",
                priority=2
            ),
            QueryTemplate(
                name="site_directory_search",
                template="site:{domain} directory {business_type}",
                variables={"domain", "business_type"},
                engine=SearchEngine.BING_WEB,
                description="Find business directories on specific sites",
                priority=2
            ),
            # Advanced location searches
            QueryTemplate(
                name="business_with_phone",
                template='"{business_type}" "{location}" phone number',
                variables={"business_type", "location"},
                engine=SearchEngine.GOOGLE_WEB,
                description="Find businesses with phone numbers",
                priority=4
            ),
            QueryTemplate(
                name="business_reviews",
                template="{business_type} reviews {location}",
                variables={"business_type", "location"},
                engine=SearchEngine.GOOGLE_WEB,
                description="Find business reviews and ratings",
                priority=1
            ),
            # Social media searches
            QueryTemplate(
                name="social_business_search",
                template="site:{social_platform} {business_type} {location}",
                variables={"social_platform", "business_type", "location"},
                engine=SearchEngine.GOOGLE_WEB,
                description="Find businesses on social media platforms",
                priority=1
            )
        ]
        
        for template in default_templates:
            self.add_template(template)
    
    def add_template(self, template: QueryTemplate):
        """Add a query template"""
        self.templates[template.name] = template
        logger.debug(f"Added template: {template.name}")
    
    def remove_template(self, template_name: str):
        """Remove a query template"""
        if template_name in self.templates:
            del self.templates[template_name]
            logger.debug(f"Removed template: {template_name}")
    
    def get_template(self, template_name: str) -> Optional[QueryTemplate]:
        """Get a specific template"""
        return self.templates.get(template_name)
    
    def list_templates(self, engine: Optional[SearchEngine] = None) -> List[QueryTemplate]:
        """List all templates, optionally filtered by engine"""
        templates = list(self.templates.values())
        if engine:
            templates = [t for t in templates if t.engine == engine]
        return sorted(templates, key=lambda x: x.priority, reverse=True)
    
    def generate_query(self, template_name: str, variables: Dict[str, str], 
                      engine: Optional[SearchEngine] = None) -> GeneratedQuery:
        """
        Generate a query from a template with provided variables
        
        Args:
            template_name: Name of the template to use
            variables: Dictionary of variables to substitute
            engine: Override the template's default engine
            
        Returns:
            GeneratedQuery object
            
        Raises:
            ValueError: If template not found or required variables missing
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        target_engine = engine or template.engine
        
        # Check required variables
        missing_vars = template.variables - set(variables.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Generate query
        try:
            query = template.template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Variable substitution failed: {e}")
        
        # Apply engine-specific formatting
        query = self._format_for_engine(query, target_engine, variables)
        
        # Validate query length
        max_length = self.engine_formats[target_engine]['max_query_length']
        if len(query) > max_length:
            logger.warning(f"Query length ({len(query)}) exceeds {target_engine.value} limit ({max_length})")
        
        return GeneratedQuery(
            query=query,
            template_name=template_name,
            engine=target_engine,
            variables=variables.copy(),
            priority=template.priority,
            tags=[target_engine.value, template_name]
        )
    
    def _format_for_engine(self, query: str, engine: SearchEngine, variables: Dict[str, str]) -> str:
        """Apply engine-specific formatting"""
        engine_config = self.engine_formats[engine]
        
        # Apply location formatting if needed
        if 'location' in variables and '{location}' not in query:
            location_format = engine_config['location_format']
            if location_format != '{location}':
                # Replace location references with engine-specific format
                query = query.replace(variables['location'], 
                                    location_format.format(location=variables['location']))
        
        return query.strip()
    
    def generate_batch(self, template_name: str, variable_sets: List[Dict[str, str]], 
                      engine: Optional[SearchEngine] = None) -> List[GeneratedQuery]:
        """
        Generate multiple queries from a template with different variable sets
        
        Args:
            template_name: Name of the template to use
            variable_sets: List of variable dictionaries
            engine: Override the template's default engine
            
        Returns:
            List of GeneratedQuery objects
        """
        queries = []
        for i, variables in enumerate(variable_sets):
            try:
                query = self.generate_query(template_name, variables, engine)
                queries.append(query)
            except ValueError as e:
                logger.error(f"Failed to generate query {i+1}: {e}")
                continue
        
        logger.info(f"Generated {len(queries)} queries from {len(variable_sets)} variable sets")
        return queries
    
    def generate_variations(self, template_name: str, base_variables: Dict[str, str],
                           variations: Dict[str, List[str]]) -> List[GeneratedQuery]:
        """
        Generate query variations by combining base variables with variations
        
        Args:
            template_name: Template to use
            base_variables: Base variables that don't change
            variations: Variables with multiple values to combine
            
        Returns:
            List of GeneratedQuery objects
        """
        import itertools
        
        # Create all combinations of variations
        variation_keys = list(variations.keys())
        variation_values = [variations[key] for key in variation_keys]
        
        queries = []
        for combination in itertools.product(*variation_values):
            variables = base_variables.copy()
            variables.update(dict(zip(variation_keys, combination)))
            
            try:
                query = self.generate_query(template_name, variables)
                queries.append(query)
            except ValueError as e:
                logger.error(f"Failed to generate variation: {e}")
                continue
        
        logger.info(f"Generated {len(queries)} query variations")
        return queries
    
    def validate_query(self, query: str, engine: SearchEngine) -> Dict[str, Union[bool, str, List[str]]]:
        """
        Validate a query for a specific search engine
        
        Returns:
            Dictionary with validation results
        """
        engine_config = self.engine_formats[engine]
        results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check length
        if len(query) > engine_config['max_query_length']:
            results['errors'].append(f"Query too long: {len(query)} > {engine_config['max_query_length']}")
            results['valid'] = False
        
        # Check for unsupported operators
        used_operators = re.findall(r'(\w+:)', query)
        supported_operators = engine_config['special_operators']
        
        for operator in used_operators:
            if operator not in supported_operators:
                results['warnings'].append(f"Operator '{operator}' may not be supported by {engine.value}")
        
        # Check for empty query
        if not query.strip():
            results['errors'].append("Empty query")
            results['valid'] = False
        
        return results
    
    def export_templates(self, file_path: str):
        """Export templates to JSON file"""
        template_data = []
        for template in self.templates.values():
            template_data.append({
                'name': template.name,
                'template': template.template,
                'engine': template.engine.value,
                'description': template.description,
                'priority': template.priority
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(template_data)} templates to {file_path}")
    
    def import_templates(self, file_path: str):
        """Import templates from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        imported_count = 0
        for data in template_data:
            try:
                template = QueryTemplate(
                    name=data['name'],
                    template=data['template'],
                    variables=set(),  # Will be computed in __post_init__
                    engine=SearchEngine(data['engine']),
                    description=data.get('description', ''),
                    priority=data.get('priority', 1)
                )
                self.add_template(template)
                imported_count += 1
            except Exception as e:
                logger.error(f"Failed to import template {data.get('name', 'unknown')}: {e}")
        
        logger.info(f"Imported {imported_count} templates from {file_path}")
    
    def get_statistics(self) -> Dict[str, Union[int, Dict]]:
        """Get statistics about loaded templates"""
        stats = {
            'total_templates': len(self.templates),
            'by_engine': {},
            'by_priority': {},
            'average_variables': 0
        }
        
        # Count by engine
        for template in self.templates.values():
            engine = template.engine.value
            stats['by_engine'][engine] = stats['by_engine'].get(engine, 0) + 1
        
        # Count by priority
        for template in self.templates.values():
            priority = template.priority
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
        
        # Average variables per template
        if self.templates:
            total_vars = sum(len(t.variables) for t in self.templates.values())
            stats['average_variables'] = round(total_vars / len(self.templates), 2)
        
        return stats


# Convenience functions for common operations
def create_business_query(business_type: str, location: str, 
                         engine: SearchEngine = SearchEngine.BING_MAPS) -> GeneratedQuery:
    """Quick function to create a business search query"""
    generator = QueryGenerator()
    return generator.generate_query(
        "business_near_location",
        {"business_type": business_type, "location": location},
        engine
    )


def create_site_search(domain: str, keywords: str, 
                      engine: SearchEngine = SearchEngine.GOOGLE_WEB) -> GeneratedQuery:
    """Quick function to create a site-specific search query"""
    generator = QueryGenerator()
    
    # Create a simple site search template if not exists
    site_template = QueryTemplate(
        name="simple_site_search",
        template="site:{domain} {keywords}",
        variables={"domain", "keywords"},
        engine=engine,
        description="Simple site-specific search"
    )
    
    generator.add_template(site_template)
    return generator.generate_query(
        "simple_site_search",
        {"domain": domain, "keywords": keywords},
        engine
    )


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    generator = QueryGenerator()
    
    # Generate a business search
    query = generator.generate_query(
        "business_near_location",
        {"business_type": "restaurants", "location": "Seattle, WA"}
    )
    print(f"Generated query: {query.query}")
    
    # Generate batch queries
    variable_sets = [
        {"business_type": "restaurants", "location": "Seattle, WA"},
        {"business_type": "cafes", "location": "Portland, OR"},
        {"business_type": "bars", "location": "San Francisco, CA"}
    ]
    
    queries = generator.generate_batch("business_near_location", variable_sets)
    print(f"\nGenerated {len(queries)} batch queries")
    
    # Show statistics
    stats = generator.get_statistics()
    print(f"\nTemplate statistics: {stats}")