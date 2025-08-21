"""
Main Query Builder System

Orchestrates the complete query building process including template expansion,
regional variations, validation, and output generation.
"""

import logging
import time
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json

from .template_manager import TemplateManager, QueryTemplate, VerticalType, SearchIntent
from .regional_expander import RegionalExpander, GeographicLocation
from .query_validator import QueryValidator, ValidationResult
from .campaign_parser import CampaignParser, CampaignConfig

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    """Represents a complete query execution plan."""
    
    campaign_name: str
    total_queries: int
    queries: List[str]
    query_metadata: List[Dict[str, Any]]
    validation_summary: Dict[str, Any]
    geographic_distribution: Dict[str, Any]
    generation_time: float
    plan_hash: str
    
    def save_to_file(self, file_path: Path):
        """Save query plan to file."""
        plan_data = {
            'campaign_name': self.campaign_name,
            'total_queries': self.total_queries,
            'queries': self.queries,
            'query_metadata': self.query_metadata,
            'validation_summary': self.validation_summary,
            'geographic_distribution': self.geographic_distribution,
            'generation_time': self.generation_time,
            'plan_hash': self.plan_hash,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)
    
    def save_queries_to_file(self, file_path: Path):
        """Save just the queries to a text file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            for query in self.queries:
                f.write(f"{query}\n")
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> 'QueryPlan':
        """Load query plan from file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            campaign_name=data['campaign_name'],
            total_queries=data['total_queries'],
            queries=data['queries'],
            query_metadata=data['query_metadata'],
            validation_summary=data['validation_summary'],
            geographic_distribution=data['geographic_distribution'],
            generation_time=data['generation_time'],
            plan_hash=data['plan_hash']
        )


class QueryBuilder:
    """
    Main query builder that orchestrates the complete query generation process.
    
    Integrates template management, regional expansion, validation, and output
    generation into a unified system.
    """
    
    def __init__(self,
                 template_file: Optional[Path] = None,
                 geographic_data_file: Optional[Path] = None):
        """
        Initialize query builder with optional configuration files.
        
        Args:
            template_file: Optional custom template file
            geographic_data_file: Optional custom geographic data file
        """
        self.template_manager = TemplateManager(template_file)
        self.regional_expander = RegionalExpander(geographic_data_file)
        self.query_validator = QueryValidator()
        self.campaign_parser = CampaignParser()
        
        logger.info("QueryBuilder initialized")
    
    def build_queries_from_campaign(self, 
                                  campaign: CampaignConfig,
                                  deduplicate: bool = True,
                                  validate_queries: bool = True) -> QueryPlan:
        """
        Build complete query plan from campaign configuration.
        
        Args:
            campaign: Campaign configuration
            deduplicate: Remove duplicate queries
            validate_queries: Validate generated queries
            
        Returns:
            Complete query plan with metadata
        """
        start_time = time.time()
        logger.info(f"Building queries for campaign: {campaign.name}")
        
        # Generate base queries from templates and service terms
        base_queries = self._generate_base_queries(campaign)
        logger.info(f"Generated {len(base_queries)} base queries")
        
        # Expand queries regionally
        expanded_queries = self._expand_queries_regionally(base_queries, campaign)
        logger.info(f"Expanded to {len(expanded_queries)} regional queries")
        
        # Apply campaign filters
        filtered_queries = self._apply_campaign_filters(expanded_queries, campaign)
        logger.info(f"Filtered to {len(filtered_queries)} queries")
        
        # Deduplicate if requested
        if deduplicate:
            filtered_queries = self._deduplicate_queries(filtered_queries)
            logger.info(f"Deduplicated to {len(filtered_queries)} unique queries")
        
        # Validate queries if requested
        validation_results = []
        if validate_queries:
            validation_results = self._validate_query_batch(filtered_queries)
            # Filter out invalid queries
            valid_queries = [(q, meta) for (q, meta), result in zip(filtered_queries, validation_results) if result.is_valid]
            filtered_queries = valid_queries
            logger.info(f"Validated to {len(filtered_queries)} valid queries")
        
        # Extract queries and metadata
        final_queries = [query for query, _ in filtered_queries]
        query_metadata = [metadata for _, metadata in filtered_queries]
        
        # Generate statistics
        validation_summary = self._generate_validation_summary(validation_results) if validation_results else {}
        geographic_distribution = self._generate_geographic_summary(query_metadata)
        
        # Create plan hash for deduplication
        plan_hash = self._generate_plan_hash(campaign, final_queries)
        
        generation_time = time.time() - start_time
        
        query_plan = QueryPlan(
            campaign_name=campaign.name,
            total_queries=len(final_queries),
            queries=final_queries,
            query_metadata=query_metadata,
            validation_summary=validation_summary,
            geographic_distribution=geographic_distribution,
            generation_time=generation_time,
            plan_hash=plan_hash
        )
        
        logger.info(f"Query plan generated in {generation_time:.2f}s: {len(final_queries)} queries")
        return query_plan
    
    def build_queries_from_yaml(self, 
                               yaml_file: Path,
                               output_file: Optional[Path] = None) -> List[QueryPlan]:
        """
        Build query plans from YAML campaign file.
        
        Args:
            yaml_file: Path to campaign YAML file
            output_file: Optional output file for queries
            
        Returns:
            List of query plans for each campaign
        """
        # Parse campaigns from YAML
        campaigns = self.campaign_parser.parse_campaign_file(yaml_file)
        logger.info(f"Parsed {len(campaigns)} campaigns from {yaml_file}")
        
        query_plans = []
        all_queries = []
        
        for campaign in campaigns:
            plan = self.build_queries_from_campaign(campaign)
            query_plans.append(plan)
            all_queries.extend(plan.queries)
        
        # Save all queries to output file if specified
        if output_file:
            self._save_queries_to_file(all_queries, Path(output_file))
            logger.info(f"Saved {len(all_queries)} queries to {output_file}")
        
        return query_plans
    
    def _generate_base_queries(self, campaign: CampaignConfig) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate base queries from campaign templates and service terms."""
        base_queries = []
        
        # Get templates for the campaign
        templates = self._get_campaign_templates(campaign)
        
        # Generate queries from templates
        for template in templates:
            # Create variable combinations
            variable_combinations = self._create_variable_combinations(campaign, template)
            
            for variables in variable_combinations:
                try:
                    query = template.format(**variables)
                    metadata = {
                        'template': template.template,
                        'vertical': template.vertical.value,
                        'intent': template.intent.value,
                        'priority': template.priority,
                        'variables': variables,
                        'source': 'template'
                    }
                    base_queries.append((query, metadata))
                    
                except Exception as e:
                    logger.warning(f"Error formatting template {template.template}: {e}")
                    continue
        
        return base_queries
    
    def _get_campaign_templates(self, campaign: CampaignConfig) -> List[QueryTemplate]:
        """Get all relevant templates for the campaign."""
        templates = []
        
        # Add custom templates from campaign
        templates.extend(campaign.custom_templates)
        
        # Add templates from template manager based on campaign criteria
        if campaign.vertical:
            vertical_templates = self.template_manager.get_templates_by_vertical(campaign.vertical)
            
            # Filter by intent if specified
            if campaign.intent_filters:
                vertical_templates = [t for t in vertical_templates if t.intent in campaign.intent_filters]
            
            # Filter by priority if specified
            if campaign.priority_filter:
                vertical_templates = [t for t in vertical_templates if t.priority == campaign.priority_filter]
            
            templates.extend(vertical_templates)
        
        # Add templates from query_templates strings
        for template_str in campaign.query_templates:
            template = QueryTemplate(
                template=template_str,
                vertical=campaign.vertical or VerticalType.PROFESSIONAL_SERVICES,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description=f"Campaign template: {template_str}"
            )
            templates.append(template)
        
        return templates
    
    def _create_variable_combinations(self, campaign: CampaignConfig, template: QueryTemplate) -> List[Dict[str, str]]:
        """Create variable combinations for template expansion."""
        combinations = []
        
        # Get required variables for template
        required_vars = template.variables
        
        # Create base variable set
        variables = {}
        
        # Add service terms if needed
        if any(var in required_vars for var in ['service_type', 'service', 'business_type']):
            service_terms = campaign.service_terms or ['business']
        else:
            service_terms = ['']
        
        # Generate combinations
        for service_term in service_terms:
            var_combo = variables.copy()
            
            # Map service variables
            if 'service_type' in required_vars:
                var_combo['service_type'] = service_term
            if 'service' in required_vars:
                var_combo['service'] = service_term
            if 'business_type' in required_vars:
                var_combo['business_type'] = service_term
            
            # Add other common variables
            if 'specialization' in required_vars:
                var_combo['specialization'] = service_term
            if 'practice_area' in required_vars:
                var_combo['practice_area'] = service_term
            if 'tech_focus' in required_vars:
                var_combo['tech_focus'] = service_term
            if 'restaurant_type' in required_vars:
                var_combo['restaurant_type'] = service_term
            if 'specialty' in required_vars:
                var_combo['specialty'] = service_term
            
            combinations.append(var_combo)
        
        return combinations if combinations else [{}]
    
    def _expand_queries_regionally(self, 
                                 base_queries: List[Tuple[str, Dict[str, Any]]], 
                                 campaign: CampaignConfig) -> List[Tuple[str, Dict[str, Any]]]:
        """Expand base queries with regional variations."""
        expanded_queries = []
        
        for query, metadata in base_queries:
            # Check if query has geographic variables
            if '{city}' in query or '{state}' in query:
                # Get locations for expansion
                locations = self._get_campaign_locations(campaign)
                
                # Expand with each location
                for location in locations:
                    try:
                        # Format query with location
                        expanded_query = query.format(
                            city=location.name,
                            state=location.state_code
                        )
                        
                        # Update metadata
                        expanded_metadata = metadata.copy()
                        expanded_metadata.update({
                            'location': location.name,
                            'state': location.state_code,
                            'state_name': location.state,
                            'region_type': location.region_type.value,
                            'population': location.population,
                            'metro_area': location.metro_area,
                            'priority': location.priority
                        })
                        
                        expanded_queries.append((expanded_query, expanded_metadata))
                        
                    except Exception as e:
                        logger.warning(f"Error expanding query {query} with location {location.name}: {e}")
                        continue
            else:
                # No geographic expansion needed
                expanded_queries.append((query, metadata))
        
        return expanded_queries
    
    def _get_campaign_locations(self, campaign: CampaignConfig) -> List[GeographicLocation]:
        """Get locations for campaign expansion."""
        locations = []
        
        # Add specific cities from campaign
        for city_name in campaign.cities:
            city_key = city_name.lower()
            if city_key in self.regional_expander.locations:
                locations.append(self.regional_expander.locations[city_key])
            else:
                logger.warning(f"City not found in geographic data: {city_name}")
        
        # Add cities from specified states
        for state_code in campaign.states:
            state_locations = self.regional_expander.get_locations_by_state(state_code)
            locations.extend(state_locations)
        
        # If no specific locations, use default set based on priority
        if not locations:
            if campaign.priority_filter:
                locations = self.regional_expander.get_locations_by_priority(campaign.priority_filter)
            else:
                locations = self.regional_expander.get_top_cities(20)  # Top 20 cities
        
        # Apply max queries per template if specified
        if campaign.max_queries_per_template and len(locations) > campaign.max_queries_per_template:
            # Sort by priority and population, then take top N
            locations.sort(key=lambda x: (x.priority, -(x.population or 0)))
            locations = locations[:campaign.max_queries_per_template]
        
        return locations
    
    def _apply_campaign_filters(self, 
                              queries: List[Tuple[str, Dict[str, Any]]], 
                              campaign: CampaignConfig) -> List[Tuple[str, Dict[str, Any]]]:
        """Apply campaign-specific filters to queries."""
        filtered_queries = []
        
        for query, metadata in queries:
            # Apply exclusions
            if campaign.exclusions:
                exclude_query = False
                query_lower = query.lower()
                for exclusion in campaign.exclusions:
                    if exclusion.lower() in query_lower:
                        exclude_query = True
                        break
                
                if exclude_query:
                    continue
            
            # Apply priority filter
            if campaign.priority_filter and metadata.get('priority') != campaign.priority_filter:
                continue
            
            # Apply intent filter
            if campaign.intent_filters:
                query_intent = metadata.get('intent')
                if query_intent and SearchIntent(query_intent) not in campaign.intent_filters:
                    continue
            
            filtered_queries.append((query, metadata))
        
        return filtered_queries
    
    def _deduplicate_queries(self, queries: List[Tuple[str, Dict[str, Any]]]) -> List[Tuple[str, Dict[str, Any]]]:
        """Remove duplicate queries while preserving metadata."""
        seen_queries = set()
        deduplicated = []
        
        for query, metadata in queries:
            query_normalized = query.lower().strip()
            if query_normalized not in seen_queries:
                seen_queries.add(query_normalized)
                deduplicated.append((query, metadata))
        
        return deduplicated
    
    def _validate_query_batch(self, queries: List[Tuple[str, Dict[str, Any]]]) -> List[ValidationResult]:
        """Validate batch of queries."""
        query_strings = [query for query, _ in queries]
        return self.query_validator.validate_query_batch(query_strings)
    
    def _generate_validation_summary(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate validation summary from results."""
        return self.query_validator.get_validation_summary(validation_results)
    
    def _generate_geographic_summary(self, metadata_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate geographic distribution summary."""
        state_counts = {}
        location_counts = {}
        priority_counts = {}
        
        for metadata in metadata_list:
            # Count by state
            state = metadata.get('state')
            if state:
                state_counts[state] = state_counts.get(state, 0) + 1
            
            # Count by location
            location = metadata.get('location')
            if location:
                location_counts[location] = location_counts.get(location, 0) + 1
            
            # Count by priority
            priority = metadata.get('priority')
            if priority:
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            'total_locations': len(location_counts),
            'unique_states': len(state_counts),
            'state_distribution': state_counts,
            'location_distribution': location_counts,
            'priority_distribution': priority_counts,
            'top_states': sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'top_locations': sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        }
    
    def _generate_plan_hash(self, campaign: CampaignConfig, queries: List[str]) -> str:
        """Generate hash for query plan deduplication."""
        plan_data = {
            'campaign_name': campaign.name,
            'total_queries': len(queries),
            'query_sample': queries[:10] if queries else []  # First 10 queries for hash
        }
        
        plan_str = json.dumps(plan_data, sort_keys=True)
        return hashlib.md5(plan_str.encode()).hexdigest()
    
    def _save_queries_to_file(self, queries: List[str], file_path: Path):
        """Save queries to text file."""
        # Ensure output directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for query in queries:
                f.write(f"{query}\n")
    
    def create_sample_campaign(self, vertical: VerticalType, cities: List[str]) -> CampaignConfig:
        """Create a sample campaign for testing."""
        return self.campaign_parser.create_campaign_from_parameters(
            name=f"Sample {vertical.value.replace('_', ' ').title()} Campaign",
            vertical=vertical,
            cities=cities,
            service_terms=['business', 'service', 'company']
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the query builder."""
        return {
            'template_manager': self.template_manager.get_statistics(),
            'regional_expander': self.regional_expander.get_statistics(),
            'validation_rules': self.query_validator.export_validation_rules()
        }
    
    def export_templates(self, file_path: Path):
        """Export all templates to file."""
        self.template_manager.save_templates(file_path)
    
    def export_geographic_data(self, file_path: Path):
        """Export geographic data to file."""
        self.regional_expander.save_geographic_data(file_path)
    
    # Context manager support for resource cleanup
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass