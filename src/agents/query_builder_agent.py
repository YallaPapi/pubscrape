"""
Query Builder Agent for Agency Swarm

An intelligent agent that specializes in building comprehensive search query
campaigns for contact discovery and lead generation across multiple verticals.
"""

import logging
from typing import List, Optional

from agency_swarm import Agent
from .tools.build_queries_tool import BuildQueriesTool
from .tools.geo_expand_tool import GeoExpandTool

logger = logging.getLogger(__name__)


class QueryBuilderAgent(Agent):
    """
    Specialized agent for search query building and campaign management.
    
    This agent excels at:
    - Building comprehensive search query campaigns
    - Expanding templates with geographic variations
    - Validating and optimizing search queries
    - Managing complex multi-vertical campaigns
    - Generating detailed reporting and analytics
    
    The agent uses advanced template systems, geographic expansion capabilities,
    and intelligent validation to create high-quality search query campaigns
    for contact discovery and lead generation.
    """
    
    def __init__(self,
                 name: str = "QueryBuilder",
                 description: str = None,
                 instructions: str = None,
                 tools: Optional[List] = None,
                 **kwargs):
        
        # Default agent description
        if description is None:
            description = (
                "Expert search query builder specializing in contact discovery campaigns. "
                "I create comprehensive query campaigns by expanding templates with "
                "geographic variations, validating quality, and optimizing for maximum effectiveness."
            )
        
        # Default agent instructions
        if instructions is None:
            instructions = """
# Query Builder Agent Instructions

You are an expert at building comprehensive search query campaigns for contact discovery and lead generation. Your role is to help users create effective, validated, and geographically-targeted search queries.

## Core Capabilities

1. **Campaign Building**: Create complete query campaigns from YAML configurations
2. **Geographic Expansion**: Expand templates with city/state variations 
3. **Query Validation**: Ensure queries meet quality and format standards
4. **Multi-Vertical Support**: Handle different business verticals (law firms, restaurants, etc.)
5. **Optimization**: Deduplicate and optimize queries for maximum effectiveness

## Key Tools

### BuildQueriesTool
Use this tool to build complete query campaigns from YAML configurations. It handles:
- Template expansion with service terms
- Regional variations across cities and states
- Query validation and optimization
- Deduplication and quality control
- Comprehensive reporting

### GeoExpandTool  
Use this tool for focused geographic expansion of templates. It provides:
- City/state placeholder expansion
- Regional targeting and filtering
- Population and priority-based selection
- Location variation handling
- Geographic distribution analysis

## Best Practices

1. **Understand Requirements**: Ask clarifying questions about target verticals, regions, and campaign goals
2. **Validate Inputs**: Ensure YAML configurations are properly formatted and complete
3. **Geographic Targeting**: Help users select appropriate geographic scope for their campaigns
4. **Quality Focus**: Always validate queries and provide quality metrics
5. **Clear Communication**: Provide detailed summaries of results and recommendations

## YAML Configuration Format

When helping users create campaigns, use this structure:

```yaml
name: "Campaign Name"
description: "Campaign description"
vertical: "restaurants"  # or law_firms, real_estate, etc.
service_terms:
  - "restaurant"
  - "cafe" 
  - "bistro"
query_templates:
  - "{service_type} {city} contact"
  - "{service_type} {city} owner email"
cities:
  - "New York"
  - "Los Angeles"
  - "Chicago"
states:
  - "CA"
  - "NY"
  - "TX"
max_queries_per_template: 50
priority_filter: 1
intent_filters:
  - "contact_discovery"
  - "email_finding"
exclusions:
  - "spam"
  - "scam"
```

## Response Guidelines

1. **Be Helpful**: Guide users through the query building process step by step
2. **Provide Context**: Explain why certain approaches or settings are recommended
3. **Show Results**: Present clear summaries of generated queries and coverage
4. **Suggest Improvements**: Recommend optimizations based on campaign goals
5. **Handle Errors**: Gracefully handle configuration errors and provide solutions

## Quality Standards

- Ensure all generated queries are valid and well-formed
- Maintain geographic diversity in expansions
- Balance query volume with quality
- Provide validation metrics and quality assessments
- Follow search engine best practices

Remember: Your goal is to create effective, targeted search query campaigns that help users find relevant contacts and leads efficiently.
"""
        
        # Default tools if none provided
        if tools is None:
            tools = [BuildQueriesTool, GeoExpandTool]
        
        # Initialize the agent
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            tools=tools,
            **kwargs
        )
        
        logger.info(f"QueryBuilderAgent '{name}' initialized with {len(tools)} tools")
    
    def create_sample_campaign_yaml(self, vertical: str = "restaurants") -> str:
        """
        Generate a sample campaign YAML for demonstration purposes.
        
        Args:
            vertical: Business vertical for the sample campaign
            
        Returns:
            Sample YAML configuration string
        """
        vertical_configs = {
            "restaurants": {
                "service_terms": ["restaurant", "cafe", "bistro", "diner"],
                "templates": [
                    "{service_type} {city} contact",
                    "{service_type} {city} owner email",
                    "restaurant manager {city} {state}"
                ]
            },
            "law_firms": {
                "service_terms": ["lawyer", "attorney", "law firm", "legal services"],
                "templates": [
                    "{service_type} {city} contact", 
                    "attorney {specialization} {city}",
                    "law firm {city} partner email"
                ]
            },
            "real_estate": {
                "service_terms": ["real estate agent", "realtor", "property management"],
                "templates": [
                    "{service_type} {city} contact",
                    "realtor {city} {state} email",
                    "property manager {city} phone"
                ]
            }
        }
        
        config = vertical_configs.get(vertical, vertical_configs["restaurants"])
        
        sample_yaml = f"""name: "Sample {vertical.replace('_', ' ').title()} Campaign"
description: "Contact discovery campaign for {vertical.replace('_', ' ')}"
vertical: "{vertical}"
service_terms:
{chr(10).join(f'  - "{term}"' for term in config['service_terms'])}
query_templates:
{chr(10).join(f'  - "{template}"' for template in config['templates'])}
cities:
  - "New York"
  - "Los Angeles" 
  - "Chicago"
  - "Houston"
  - "Phoenix"
states:
  - "CA"
  - "NY"
  - "TX"
  - "FL"
  - "IL"
max_queries_per_template: 50
priority_filter: 1
intent_filters:
  - "contact_discovery"
  - "email_finding"
exclusions:
  - "spam"
  - "scam"
metadata:
  created_by: "query_builder_agent"
  version: "1.0"
"""
        
        return sample_yaml
    
    def validate_campaign_yaml(self, yaml_content: str) -> tuple:
        """
        Validate YAML campaign configuration.
        
        Args:
            yaml_content: YAML content to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            from query_builder.campaign_parser import CampaignParser
            
            parser = CampaignParser()
            is_valid, errors = parser.validate_yaml_schema(yaml_content)
            
            return is_valid, errors
            
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def get_supported_verticals(self) -> List[str]:
        """Get list of supported business verticals."""
        from query_builder.template_manager import VerticalType
        
        return [vertical.value for vertical in VerticalType]
    
    def get_available_intents(self) -> List[str]:
        """Get list of available search intents."""
        from query_builder.template_manager import SearchIntent
        
        return [intent.value for intent in SearchIntent]