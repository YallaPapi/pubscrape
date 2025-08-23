"""
Query Generation and Management System

This module provides comprehensive query generation, management, and tracking
capabilities for web scraping operations.

Components:
- QueryGenerator: Template-based query generation
- LocationManager: Geographic location management
- BusinessCategoryManager: Business type and category management
- QueryQueue: Priority-based query queue with rate limiting
- QueryTracker: Query execution tracking and analytics
"""

from .query_generator import (
    QueryGenerator,
    QueryTemplate,
    GeneratedQuery,
    SearchEngine,
    create_business_query,
    create_site_search
)

from .location_manager import (
    LocationManager,
    Location,
    Region,
    create_us_cities_manager
)

from .business_categories import (
    BusinessCategoryManager,
    BusinessCategory,
    BusinessType,
    BusinessTier,
    create_default_manager
)

from .query_queue import (
    QueryQueue,
    QueuedQuery,
    QueryStatus,
    QueuePriority,
    RateLimitRule,
    create_search_queue
)

from .query_tracker import (
    QueryTracker,
    QueryResult,
    QueryAnalytics,
    create_tracker
)

__all__ = [
    # Query generation
    'QueryGenerator',
    'QueryTemplate', 
    'GeneratedQuery',
    'SearchEngine',
    'create_business_query',
    'create_site_search',
    
    # Location management
    'LocationManager',
    'Location',
    'Region',
    'create_us_cities_manager',
    
    # Business categories
    'BusinessCategoryManager',
    'BusinessCategory',
    'BusinessType',
    'BusinessTier',
    'create_default_manager',
    
    # Query queue
    'QueryQueue',
    'QueuedQuery',
    'QueryStatus',
    'QueuePriority',
    'RateLimitRule',
    'create_search_queue',
    
    # Query tracking
    'QueryTracker',
    'QueryResult',
    'QueryAnalytics',
    'create_tracker'
]