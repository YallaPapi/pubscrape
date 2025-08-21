"""Configuration module for Bing Scraper."""

from .settings import Settings, get_settings
from .search_queries import SearchQueryManager
from .proxy_config import ProxyConfig

__all__ = [
    'Settings',
    'get_settings', 
    'SearchQueryManager',
    'ProxyConfig'
]