"""Search query management for Bing Scraper."""

from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class SearchQuery:
    """Search query configuration."""
    query: str
    vertical: str
    max_pages: int = 5
    priority: str = "medium"

class SearchQueryManager:
    """Manages search queries for different verticals."""
    
    def __init__(self):
        """Initialize with default query templates."""
        self.queries = []
        self._load_default_queries()
    
    def _load_default_queries(self):
        """Load default search query templates."""
        # Real Estate queries
        self.queries.extend([
            SearchQuery("real estate agent {city}", "real_estate", 3, "high"),
            SearchQuery("realtor contact {city}", "real_estate", 3, "high"),
            SearchQuery("mortgage broker {city}", "real_estate", 2, "medium"),
        ])
        
        # Local Services queries  
        self.queries.extend([
            SearchQuery("plumber {city}", "local_services", 3, "medium"),
            SearchQuery("electrician {city}", "local_services", 3, "medium"),
            SearchQuery("dentist {city}", "local_services", 2, "medium"),
        ])
        
        # E-commerce queries
        self.queries.extend([
            SearchQuery("site:shopify.com {niche}", "ecommerce", 5, "high"),
            SearchQuery("powered by shopify {product}", "ecommerce", 4, "high"),
        ])
    
    def get_queries_by_vertical(self, vertical: str) -> List[SearchQuery]:
        """Get queries for a specific vertical."""
        return [q for q in self.queries if q.vertical == vertical]
    
    def format_query(self, query_template: str, **kwargs) -> str:
        """Format query template with provided parameters."""
        return query_template.format(**kwargs)
    
    def add_query(self, query: SearchQuery):
        """Add a new search query."""
        self.queries.append(query)