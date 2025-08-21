"""Anti-detection module for Bing Scraper."""

from .manager import AntiDetectionManager
from .user_agents import UserAgentRotator
from .delays import HumanLikeDelays
from .proxy_manager import ProxyManager

__all__ = [
    'AntiDetectionManager',
    'UserAgentRotator', 
    'HumanLikeDelays',
    'ProxyManager'
]