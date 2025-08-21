"""
Campaign Parser System

Parses campaign YAML files to extract templates, service terms, cities,
and other campaign configuration data for query generation.
"""

import logging
import yaml
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from .template_manager import QueryTemplate, VerticalType, SearchIntent
from .regional_expander import GeographicLocation, RegionType

logger = logging.getLogger(__name__)


@dataclass
class CampaignConfig:
    """Configuration for a marketing campaign."""
    
    name: str
    description: str = ""
    vertical: Optional[VerticalType] = None
    target_regions: List[str] = field(default_factory=list)
    service_terms: List[str] = field(default_factory=list)
    cities: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    query_templates: List[str] = field(default_factory=list)
    custom_templates: List[QueryTemplate] = field(default_factory=list)
    max_queries_per_template: Optional[int] = None
    priority_filter: Optional[int] = None
    intent_filters: List[SearchIntent] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign config to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'vertical': self.vertical.value if self.vertical else None,
            'target_regions': self.target_regions,
            'service_terms': self.service_terms,
            'cities': self.cities,
            'states': self.states,
            'query_templates': self.query_templates,
            'custom_templates': [t.to_dict() for t in self.custom_templates],
            'max_queries_per_template': self.max_queries_per_template,
            'priority_filter': self.priority_filter,
            'intent_filters': [i.value for i in self.intent_filters],
            'exclusions': self.exclusions,
            'metadata': self.metadata
        }


class CampaignParser:
    """
    Parses campaign YAML files and converts them to structured campaign configurations.
    
    Supports flexible YAML formats and provides validation and normalization.
    """
    
    def __init__(self):
        """Initialize campaign parser."""
        logger.info("CampaignParser initialized")
    
    def parse_campaign_file(self, file_path: Path) -> List[CampaignConfig]:
        """
        Parse campaign YAML file and return campaign configurations.
        
        Args:
            file_path: Path to campaign YAML file
            
        Returns:
            List of parsed campaign configurations
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Campaign file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ValueError("Campaign file is empty or invalid")
            
            campaigns = self._parse_campaign_data(data)
            logger.info(f"Parsed {len(campaigns)} campaigns from {file_path}")
            return campaigns
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing campaign file: {e}")
    
    def parse_campaign_string(self, yaml_content: str) -> List[CampaignConfig]:
        """
        Parse campaign YAML from string content.
        
        Args:
            yaml_content: YAML content as string
            
        Returns:
            List of parsed campaign configurations
        """
        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                raise ValueError("Campaign content is empty or invalid")
            
            return self._parse_campaign_data(data)
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing campaign content: {e}")
    
    def _parse_campaign_data(self, data: Dict[str, Any]) -> List[CampaignConfig]:
        """Parse campaign data from loaded YAML."""
        campaigns = []
        
        # Handle single campaign or multiple campaigns
        if 'campaigns' in data:
            # Multiple campaigns format
            for campaign_data in data['campaigns']:
                campaign = self._parse_single_campaign(campaign_data)
                campaigns.append(campaign)
        elif 'name' in data or 'vertical' in data:
            # Single campaign format
            campaign = self._parse_single_campaign(data)
            campaigns.append(campaign)
        else:
            raise ValueError("Invalid campaign format: missing 'campaigns' or campaign fields")
        
        return campaigns
    
    def _parse_single_campaign(self, data: Dict[str, Any]) -> CampaignConfig:
        """Parse a single campaign from data dictionary."""
        # Required field validation
        if not data.get('name'):
            raise ValueError("Campaign must have a name")
        
        campaign = CampaignConfig(
            name=data['name'],
            description=data.get('description', ''),
        )
        
        # Parse vertical
        if 'vertical' in data:
            try:
                campaign.vertical = VerticalType(data['vertical'].lower())
            except ValueError:
                logger.warning(f"Unknown vertical type: {data['vertical']}")
        
        # Parse geographic data
        campaign.target_regions = self._parse_list_field(data, 'target_regions')
        campaign.cities = self._parse_list_field(data, 'cities')
        campaign.states = self._parse_list_field(data, 'states')
        
        # Parse service terms
        campaign.service_terms = self._parse_list_field(data, 'service_terms')
        
        # Parse query templates
        campaign.query_templates = self._parse_list_field(data, 'query_templates')
        
        # Parse custom templates
        if 'custom_templates' in data:
            campaign.custom_templates = self._parse_custom_templates(data['custom_templates'])
        
        # Parse filters and limits
        campaign.max_queries_per_template = data.get('max_queries_per_template')
        campaign.priority_filter = data.get('priority_filter')
        
        # Parse intent filters
        if 'intent_filters' in data:
            campaign.intent_filters = self._parse_intent_filters(data['intent_filters'])
        
        # Parse exclusions
        campaign.exclusions = self._parse_list_field(data, 'exclusions')
        
        # Parse metadata
        campaign.metadata = data.get('metadata', {})
        
        # Validate campaign
        self._validate_campaign(campaign)
        
        return campaign
    
    def _parse_list_field(self, data: Dict[str, Any], field_name: str) -> List[str]:
        """Parse a field that can be a string or list of strings."""
        value = data.get(field_name, [])
        
        if isinstance(value, str):
            # Handle comma-separated strings
            return [item.strip() for item in value.split(',') if item.strip()]
        elif isinstance(value, list):
            # Handle list of strings
            return [str(item).strip() for item in value if str(item).strip()]
        else:
            logger.warning(f"Invalid format for {field_name}: {type(value)}")
            return []
    
    def _parse_custom_templates(self, templates_data: List[Dict[str, Any]]) -> List[QueryTemplate]:
        """Parse custom template definitions."""
        templates = []
        
        for template_data in templates_data:
            try:
                # Required fields
                template_str = template_data.get('template')
                if not template_str:
                    logger.warning("Custom template missing 'template' field")
                    continue
                
                # Optional fields with defaults
                vertical = VerticalType.PROFESSIONAL_SERVICES  # Default
                if 'vertical' in template_data:
                    try:
                        vertical = VerticalType(template_data['vertical'].lower())
                    except ValueError:
                        logger.warning(f"Unknown vertical in custom template: {template_data['vertical']}")
                
                intent = SearchIntent.CONTACT_DISCOVERY  # Default
                if 'intent' in template_data:
                    try:
                        intent = SearchIntent(template_data['intent'].lower())
                    except ValueError:
                        logger.warning(f"Unknown intent in custom template: {template_data['intent']}")
                
                template = QueryTemplate(
                    template=template_str,
                    vertical=vertical,
                    intent=intent,
                    priority=template_data.get('priority', 1),
                    description=template_data.get('description', ''),
                    expected_results=template_data.get('expected_results', 10),
                    search_operators=template_data.get('search_operators', []),
                    exclusions=template_data.get('exclusions', [])
                )
                
                templates.append(template)
                
            except Exception as e:
                logger.error(f"Error parsing custom template: {e}")
                continue
        
        return templates
    
    def _parse_intent_filters(self, intent_data: Union[str, List[str]]) -> List[SearchIntent]:
        """Parse search intent filters."""
        intents = []
        
        if isinstance(intent_data, str):
            intent_list = [intent_data]
        else:
            intent_list = intent_data
        
        for intent_str in intent_list:
            try:
                intent = SearchIntent(intent_str.lower())
                intents.append(intent)
            except ValueError:
                logger.warning(f"Unknown search intent: {intent_str}")
        
        return intents
    
    def _validate_campaign(self, campaign: CampaignConfig):
        """Validate campaign configuration."""
        issues = []
        
        # Check for required data
        if not campaign.name:
            issues.append("Campaign name is required")
        
        # Check for templates or service terms
        if not campaign.query_templates and not campaign.custom_templates and not campaign.service_terms:
            issues.append("Campaign must have query templates, custom templates, or service terms")
        
        # Check for geographic data
        if not campaign.cities and not campaign.states and not campaign.target_regions:
            issues.append("Campaign must specify cities, states, or target regions")
        
        # Validate template formats
        for template in campaign.query_templates:
            if '{' not in template or '}' not in template:
                logger.warning(f"Template may be missing variables: {template}")
        
        if issues:
            raise ValueError(f"Campaign validation failed: {'; '.join(issues)}")
    
    def generate_sample_campaign(self, vertical: VerticalType) -> str:
        """Generate sample campaign YAML for a vertical."""
        
        vertical_configs = {
            VerticalType.RESTAURANTS: {
                'service_terms': ['restaurant', 'cafe', 'bistro', 'diner'],
                'templates': [
                    '{service_type} {city} contact',
                    '{service_type} {city} owner email',
                    'restaurant manager {city} {state}'
                ]
            },
            VerticalType.LAW_FIRMS: {
                'service_terms': ['lawyer', 'attorney', 'law firm', 'legal services'],
                'templates': [
                    '{service_type} {city} contact',
                    'attorney {specialization} {city}',
                    'law firm {city} partner email'
                ]
            },
            VerticalType.REAL_ESTATE: {
                'service_terms': ['real estate agent', 'realtor', 'property management'],
                'templates': [
                    '{service_type} {city} contact',
                    'realtor {city} {state} email',
                    'property manager {city} phone'
                ]
            }
        }
        
        config = vertical_configs.get(vertical, {
            'service_terms': ['business', 'service', 'company'],
            'templates': ['{service_type} {city} contact']
        })
        
        sample = {
            'name': f'{vertical.value.replace("_", " ").title()} Campaign',
            'description': f'Contact discovery campaign for {vertical.value.replace("_", " ")}',
            'vertical': vertical.value,
            'service_terms': config['service_terms'],
            'query_templates': config['templates'],
            'cities': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
            'states': ['CA', 'NY', 'TX', 'FL', 'IL'],
            'max_queries_per_template': 50,
            'priority_filter': 1,
            'intent_filters': ['contact_discovery', 'email_finding'],
            'exclusions': ['spam', 'scam'],
            'metadata': {
                'created_by': 'campaign_generator',
                'version': '1.0'
            }
        }
        
        return yaml.dump(sample, default_flow_style=False, indent=2)
    
    def create_campaign_from_parameters(self,
                                      name: str,
                                      vertical: VerticalType,
                                      cities: List[str],
                                      service_terms: List[str],
                                      templates: Optional[List[str]] = None) -> CampaignConfig:
        """Create campaign configuration from basic parameters."""
        
        campaign = CampaignConfig(
            name=name,
            vertical=vertical,
            cities=cities,
            service_terms=service_terms,
            query_templates=templates or [
                '{service_type} {city} contact',
                '{service_type} {city} email'
            ]
        )
        
        return campaign
    
    def export_campaign_to_yaml(self, campaign: CampaignConfig) -> str:
        """Export campaign configuration to YAML string."""
        return yaml.dump(campaign.to_dict(), default_flow_style=False, indent=2)
    
    def save_campaign_to_file(self, campaign: CampaignConfig, file_path: Path):
        """Save campaign configuration to YAML file."""
        yaml_content = self.export_campaign_to_yaml(campaign)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        logger.info(f"Saved campaign '{campaign.name}' to {file_path}")
    
    def merge_campaigns(self, campaigns: List[CampaignConfig]) -> CampaignConfig:
        """Merge multiple campaigns into a single configuration."""
        if not campaigns:
            raise ValueError("No campaigns to merge")
        
        if len(campaigns) == 1:
            return campaigns[0]
        
        # Use first campaign as base
        merged = campaigns[0]
        merged.name = f"Merged: {' + '.join(c.name for c in campaigns)}"
        merged.description = f"Merged campaign from {len(campaigns)} sources"
        
        # Merge lists from all campaigns
        for campaign in campaigns[1:]:
            merged.target_regions.extend(campaign.target_regions)
            merged.service_terms.extend(campaign.service_terms)
            merged.cities.extend(campaign.cities)
            merged.states.extend(campaign.states)
            merged.query_templates.extend(campaign.query_templates)
            merged.custom_templates.extend(campaign.custom_templates)
            merged.exclusions.extend(campaign.exclusions)
            merged.intent_filters.extend(campaign.intent_filters)
            
            # Merge metadata
            merged.metadata.update(campaign.metadata)
        
        # Remove duplicates
        merged.target_regions = list(set(merged.target_regions))
        merged.service_terms = list(set(merged.service_terms))
        merged.cities = list(set(merged.cities))
        merged.states = list(set(merged.states))
        merged.query_templates = list(set(merged.query_templates))
        merged.exclusions = list(set(merged.exclusions))
        merged.intent_filters = list(set(merged.intent_filters))
        
        return merged
    
    def validate_yaml_schema(self, yaml_content: str) -> Tuple[bool, List[str]]:
        """Validate YAML content against expected schema."""
        errors = []
        
        try:
            data = yaml.safe_load(yaml_content)
            
            if not data:
                errors.append("YAML content is empty")
                return False, errors
            
            # Check for required top-level structure
            if not isinstance(data, dict):
                errors.append("YAML must contain a dictionary at the top level")
                return False, errors
            
            # Validate campaign structure
            campaigns_data = data.get('campaigns', [data] if 'name' in data else [])
            
            for i, campaign_data in enumerate(campaigns_data):
                prefix = f"Campaign {i+1}: " if len(campaigns_data) > 1 else ""
                
                if not isinstance(campaign_data, dict):
                    errors.append(f"{prefix}Campaign must be a dictionary")
                    continue
                
                # Check required fields
                if not campaign_data.get('name'):
                    errors.append(f"{prefix}Missing required field 'name'")
                
                # Check field types
                list_fields = ['service_terms', 'cities', 'states', 'query_templates', 'exclusions']
                for field in list_fields:
                    if field in campaign_data:
                        value = campaign_data[field]
                        if not isinstance(value, (list, str)):
                            errors.append(f"{prefix}Field '{field}' must be a list or string")
                
                # Check vertical if specified
                if 'vertical' in campaign_data:
                    try:
                        VerticalType(campaign_data['vertical'].lower())
                    except ValueError:
                        errors.append(f"{prefix}Invalid vertical: {campaign_data['vertical']}")
            
            return len(errors) == 0, errors
            
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors