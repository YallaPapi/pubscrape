"""
Search Query Builder System

This module provides comprehensive query building capabilities for the Bing scraper,
including template expansion, regional variations, and query validation.
"""

from .query_builder import QueryBuilder
from .template_manager import TemplateManager, QueryTemplate, VerticalType, SearchIntent
from .regional_expander import RegionalExpander
from .query_validator import QueryValidator
from .campaign_parser import CampaignParser, CampaignConfig

__all__ = [
    'QueryBuilder',
    'TemplateManager', 
    'QueryTemplate',
    'VerticalType',
    'SearchIntent',
    'RegionalExpander',
    'QueryValidator',
    'CampaignParser',
    'CampaignConfig'
]