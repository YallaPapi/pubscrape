"""
Query Template Management System

Manages query templates for different verticals (restaurants, law firms, etc.)
with support for template variables, intent types, and customization.
"""

import logging
import re
from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SearchIntent(Enum):
    """Different types of search intent for queries."""
    CONTACT_DISCOVERY = "contact_discovery"
    EMAIL_FINDING = "email_finding"
    SOCIAL_MEDIA = "social_media"
    BUSINESS_INFO = "business_info"
    DIRECTORY_LISTING = "directory_listing"
    REVIEWS_RATINGS = "reviews_ratings"
    COMPETITORS = "competitors"
    INDUSTRY_RESEARCH = "industry_research"


class VerticalType(Enum):
    """Supported business verticals."""
    RESTAURANTS = "restaurants"
    LAW_FIRMS = "law_firms"
    REAL_ESTATE = "real_estate"
    MEDICAL_DENTAL = "medical_dental"
    AUTOMOTIVE = "automotive"
    RETAIL_ECOMMERCE = "retail_ecommerce"
    TECHNOLOGY = "technology"
    PROFESSIONAL_SERVICES = "professional_services"
    FITNESS_WELLNESS = "fitness_wellness"
    EDUCATION = "education"
    NON_PROFIT = "non_profit"
    MANUFACTURING = "manufacturing"


@dataclass
class QueryTemplate:
    """Represents a search query template with variables and metadata."""
    
    template: str
    vertical: VerticalType
    intent: SearchIntent
    priority: int = 1  # 1=high, 2=medium, 3=low
    variables: Set[str] = field(default_factory=set)
    description: str = ""
    expected_results: int = 10
    search_operators: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Extract variables from template after initialization."""
        if not self.variables:
            self.variables = self._extract_variables()
    
    def _extract_variables(self) -> Set[str]:
        """Extract variable placeholders from template string."""
        # Find all {variable} patterns
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, self.template)
        return set(matches)
    
    def format(self, **kwargs) -> str:
        """Format template with provided variables."""
        try:
            # Ensure all required variables are provided
            missing_vars = self.variables - set(kwargs.keys())
            if missing_vars:
                logger.warning(f"Missing variables for template: {missing_vars}")
                # Use placeholder values for missing variables
                for var in missing_vars:
                    kwargs[var] = f"[{var}]"
            
            formatted = self.template.format(**kwargs)
            
            # Apply search operators if specified
            if self.search_operators:
                for operator in self.search_operators:
                    formatted = f"{operator} {formatted}"
            
            # Add exclusions if specified
            if self.exclusions:
                exclusions_str = " ".join(f"-{exc}" for exc in self.exclusions)
                formatted = f"{formatted} {exclusions_str}"
            
            return formatted.strip()
            
        except KeyError as e:
            logger.error(f"Template formatting error: {e}")
            return self.template
    
    def validate_variables(self, variables: Dict[str, str]) -> bool:
        """Validate that all required variables are provided."""
        return self.variables.issubset(set(variables.keys()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary representation."""
        return {
            'template': self.template,
            'vertical': self.vertical.value,
            'intent': self.intent.value,
            'priority': self.priority,
            'variables': list(self.variables),
            'description': self.description,
            'expected_results': self.expected_results,
            'search_operators': self.search_operators,
            'exclusions': self.exclusions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryTemplate':
        """Create template from dictionary representation."""
        return cls(
            template=data['template'],
            vertical=VerticalType(data['vertical']),
            intent=SearchIntent(data['intent']),
            priority=data.get('priority', 1),
            variables=set(data.get('variables', [])),
            description=data.get('description', ''),
            expected_results=data.get('expected_results', 10),
            search_operators=data.get('search_operators', []),
            exclusions=data.get('exclusions', [])
        )


class TemplateManager:
    """
    Manages query templates for different business verticals and search intents.
    
    Provides template storage, retrieval, validation, and customization capabilities.
    """
    
    def __init__(self, template_file: Optional[Path] = None):
        """
        Initialize template manager.
        
        Args:
            template_file: Optional path to custom template file
        """
        self.templates: Dict[str, QueryTemplate] = {}
        self.template_file = template_file
        self._load_default_templates()
        
        if template_file and template_file.exists():
            self._load_templates_from_file(template_file)
        
        logger.info(f"TemplateManager initialized with {len(self.templates)} templates")
    
    def _load_default_templates(self):
        """Load comprehensive default templates for all verticals."""
        
        # Restaurant templates
        restaurant_templates = [
            QueryTemplate(
                template="{service_type} {city} contact",
                vertical=VerticalType.RESTAURANTS,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description="Basic restaurant contact search"
            ),
            QueryTemplate(
                template='"{service_type}" "{city}" email OR contact',
                vertical=VerticalType.RESTAURANTS,
                intent=SearchIntent.EMAIL_FINDING,
                priority=1,
                description="Restaurant email discovery with operators"
            ),
            QueryTemplate(
                template="restaurant {city} owner manager contact information",
                vertical=VerticalType.RESTAURANTS,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=2,
                description="Restaurant management contacts"
            ),
            QueryTemplate(
                template="site:facebook.com {restaurant_type} {city}",
                vertical=VerticalType.RESTAURANTS,
                intent=SearchIntent.SOCIAL_MEDIA,
                priority=2,
                search_operators=["site:facebook.com"],
                description="Restaurant Facebook pages"
            )
        ]
        
        # Law firm templates
        law_firm_templates = [
            QueryTemplate(
                template="{practice_area} lawyer {city} contact",
                vertical=VerticalType.LAW_FIRMS,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description="Lawyer contact by practice area"
            ),
            QueryTemplate(
                template='law firm "{city}" partner attorney email',
                vertical=VerticalType.LAW_FIRMS,
                intent=SearchIntent.EMAIL_FINDING,
                priority=1,
                description="Law firm partner email discovery"
            ),
            QueryTemplate(
                template="attorney {specialization} {city} {state}",
                vertical=VerticalType.LAW_FIRMS,
                intent=SearchIntent.DIRECTORY_LISTING,
                priority=2,
                description="Attorney directory search"
            ),
            QueryTemplate(
                template="site:linkedin.com lawyer {practice_area} {city}",
                vertical=VerticalType.LAW_FIRMS,
                intent=SearchIntent.SOCIAL_MEDIA,
                priority=2,
                search_operators=["site:linkedin.com"],
                description="Lawyer LinkedIn profiles"
            )
        ]
        
        # Real estate templates
        real_estate_templates = [
            QueryTemplate(
                template="real estate agent {city} {state} contact",
                vertical=VerticalType.REAL_ESTATE,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description="Real estate agent contacts"
            ),
            QueryTemplate(
                template="realtor {city} email OR phone broker",
                vertical=VerticalType.REAL_ESTATE,
                intent=SearchIntent.EMAIL_FINDING,
                priority=1,
                description="Realtor contact information"
            ),
            QueryTemplate(
                template="property management {city} contact information",
                vertical=VerticalType.REAL_ESTATE,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=2,
                description="Property management contacts"
            )
        ]
        
        # Medical/Dental templates  
        medical_templates = [
            QueryTemplate(
                template="{specialty} doctor {city} contact office",
                vertical=VerticalType.MEDICAL_DENTAL,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description="Medical specialist contacts"
            ),
            QueryTemplate(
                template="dentist {city} {state} practice email",
                vertical=VerticalType.MEDICAL_DENTAL,
                intent=SearchIntent.EMAIL_FINDING,
                priority=1,
                description="Dental practice email discovery"
            ),
            QueryTemplate(
                template="medical clinic {city} physicians contact",
                vertical=VerticalType.MEDICAL_DENTAL,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=2,
                description="Medical clinic physician contacts"
            )
        ]
        
        # Professional services templates
        professional_templates = [
            QueryTemplate(
                template="{service_type} {city} consultant contact",
                vertical=VerticalType.PROFESSIONAL_SERVICES,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description="Professional service consultant contacts"
            ),
            QueryTemplate(
                template="accounting firm {city} CPA contact email",
                vertical=VerticalType.PROFESSIONAL_SERVICES,
                intent=SearchIntent.EMAIL_FINDING,
                priority=1,
                description="Accounting firm contact discovery"
            ),
            QueryTemplate(
                template="consulting {specialization} {city} principal partner",
                vertical=VerticalType.PROFESSIONAL_SERVICES,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=2,
                description="Consulting firm leadership contacts"
            )
        ]
        
        # Technology templates
        tech_templates = [
            QueryTemplate(
                template="software company {city} founder CEO contact",
                vertical=VerticalType.TECHNOLOGY,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=1,
                description="Tech company leadership contacts"
            ),
            QueryTemplate(
                template='"{tech_focus}" startup {city} contact email',
                vertical=VerticalType.TECHNOLOGY,
                intent=SearchIntent.EMAIL_FINDING,
                priority=1,
                description="Tech startup contact discovery"
            ),
            QueryTemplate(
                template="IT services {city} contact support",
                vertical=VerticalType.TECHNOLOGY,
                intent=SearchIntent.CONTACT_DISCOVERY,
                priority=2,
                description="IT services company contacts"
            )
        ]
        
        # Combine all templates
        all_templates = (
            restaurant_templates + law_firm_templates + real_estate_templates +
            medical_templates + professional_templates + tech_templates
        )
        
        # Store templates with unique IDs
        for i, template in enumerate(all_templates):
            template_id = f"{template.vertical.value}_{template.intent.value}_{i}"
            self.templates[template_id] = template
    
    def get_templates_by_vertical(self, vertical: VerticalType) -> List[QueryTemplate]:
        """Get all templates for a specific vertical."""
        return [t for t in self.templates.values() if t.vertical == vertical]
    
    def get_templates_by_intent(self, intent: SearchIntent) -> List[QueryTemplate]:
        """Get all templates for a specific search intent."""
        return [t for t in self.templates.values() if t.intent == intent]
    
    def get_templates_by_priority(self, priority: int) -> List[QueryTemplate]:
        """Get all templates with specific priority level."""
        return [t for t in self.templates.values() if t.priority == priority]
    
    def get_template(self, template_id: str) -> Optional[QueryTemplate]:
        """Get specific template by ID."""
        return self.templates.get(template_id)
    
    def add_template(self, template_id: str, template: QueryTemplate):
        """Add new template to manager."""
        self.templates[template_id] = template
        logger.info(f"Added template: {template_id}")
    
    def remove_template(self, template_id: str) -> bool:
        """Remove template from manager."""
        if template_id in self.templates:
            del self.templates[template_id]
            logger.info(f"Removed template: {template_id}")
            return True
        return False
    
    def filter_templates(self, 
                        vertical: Optional[VerticalType] = None,
                        intent: Optional[SearchIntent] = None,
                        priority: Optional[int] = None,
                        required_variables: Optional[Set[str]] = None) -> List[QueryTemplate]:
        """Filter templates by multiple criteria."""
        
        filtered = list(self.templates.values())
        
        if vertical:
            filtered = [t for t in filtered if t.vertical == vertical]
        
        if intent:
            filtered = [t for t in filtered if t.intent == intent]
        
        if priority:
            filtered = [t for t in filtered if t.priority == priority]
        
        if required_variables:
            filtered = [t for t in filtered if required_variables.issubset(t.variables)]
        
        return filtered
    
    def get_variable_requirements(self, templates: List[QueryTemplate]) -> Set[str]:
        """Get all variables required by a list of templates."""
        all_variables = set()
        for template in templates:
            all_variables.update(template.variables)
        return all_variables
    
    def validate_templates(self, variables: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Validate all templates against provided variables.
        
        Returns:
            Dict mapping template_id to list of missing variables
        """
        validation_results = {}
        
        for template_id, template in self.templates.items():
            missing_vars = template.variables - set(variables.keys())
            if missing_vars:
                validation_results[template_id] = list(missing_vars)
        
        return validation_results
    
    def get_templates_for_vertical_and_variables(self, 
                                               vertical: VerticalType,
                                               available_variables: Set[str]) -> List[QueryTemplate]:
        """Get templates for a vertical that can be satisfied by available variables."""
        vertical_templates = self.get_templates_by_vertical(vertical)
        return [t for t in vertical_templates if t.variables.issubset(available_variables)]
    
    def save_templates(self, file_path: Path):
        """Save templates to JSON file."""
        template_data = {
            template_id: template.to_dict() 
            for template_id, template in self.templates.items()
        }
        
        with open(file_path, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        logger.info(f"Saved {len(self.templates)} templates to {file_path}")
    
    def _load_templates_from_file(self, file_path: Path):
        """Load templates from JSON file."""
        try:
            with open(file_path, 'r') as f:
                template_data = json.load(f)
            
            for template_id, data in template_data.items():
                template = QueryTemplate.from_dict(data)
                self.templates[template_id] = template
            
            logger.info(f"Loaded {len(template_data)} templates from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading templates from {file_path}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get template manager statistics."""
        vertical_counts = {}
        intent_counts = {}
        priority_counts = {}
        
        for template in self.templates.values():
            # Count by vertical
            vertical = template.vertical.value
            vertical_counts[vertical] = vertical_counts.get(vertical, 0) + 1
            
            # Count by intent
            intent = template.intent.value
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            # Count by priority
            priority = template.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            'total_templates': len(self.templates),
            'verticals': vertical_counts,
            'intents': intent_counts,
            'priorities': priority_counts,
            'unique_variables': len(self.get_variable_requirements(list(self.templates.values())))
        }