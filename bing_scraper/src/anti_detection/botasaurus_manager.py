"""
Botasaurus-based Anti-Detection Manager
Implementation based on research findings for Bing scraper.
"""

import random
import time
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from botasaurus.browser import browser
from botasaurus import UserAgent, WindowSize

logger = logging.getLogger(__name__)

@dataclass
class BingSessionConfig:
    """Configuration for Bing scraping session."""
    profile_name: str
    proxy_url: Optional[str] = None
    user_agent_rotation: bool = True
    consistent_fingerprint: bool = False
    block_resources: bool = True
    max_requests_per_minute: int = 15
    base_delay_seconds: float = 3.0

class BotasaurusAntiDetectionManager:
    """
    Anti-detection manager using Botasaurus native features.
    Based on research findings for optimal Bing scraping.
    """
    
    def __init__(self, settings):
        """Initialize with settings from config."""
        self.settings = settings
        self.active_sessions: Dict[str, BingSessionConfig] = {}
        self.proxy_pool: List[str] = []
        self.failed_proxies: set = set()
        self.session_counter = 0
        
        # Load proxy pool from environment
        self._load_proxy_pool()
        
        logger.info("BotasaurusAntiDetectionManager initialized")
    
    def _load_proxy_pool(self) -> None:
        """Load proxy pool from environment variables."""
        proxy_configs = []
        
        # Main proxy from settings
        if self.settings.proxy_enabled and self.settings.proxy_host:
            if self.settings.proxy_username and self.settings.proxy_password:
                proxy_url = f"http://{self.settings.proxy_username}:{self.settings.proxy_password}@{self.settings.proxy_host}:{self.settings.proxy_port}"
            else:
                proxy_url = f"http://{self.settings.proxy_host}:{self.settings.proxy_port}"
            proxy_configs.append(proxy_url)
        
        # Residential proxy endpoint
        if self.settings.residential_proxy_endpoint:
            if self.settings.residential_proxy_username:
                auth = f"{self.settings.residential_proxy_username}:{self.settings.residential_proxy_password}@"
            else:
                auth = ""
            proxy_url = f"http://{auth}{self.settings.residential_proxy_endpoint}"
            proxy_configs.append(proxy_url)
        
        # Additional proxies from environment (PROXY_1, PROXY_2, etc.)
        i = 1
        while True:
            proxy_env = os.getenv(f'PROXY_{i}')
            if not proxy_env:
                break
            proxy_configs.append(proxy_env)
            i += 1
        
        self.proxy_pool = proxy_configs
        logger.info(f"Loaded {len(self.proxy_pool)} proxies")
    
    def get_session_config(self, campaign_name: str) -> BingSessionConfig:
        """Get or create session configuration for campaign."""
        if campaign_name not in self.active_sessions:
            config = BingSessionConfig(
                profile_name=f"{campaign_name}_{self.session_counter}",
                proxy_url=self._get_next_proxy(),
                user_agent_rotation=self.settings.user_agent_rotation,
                block_resources=self.settings.block_images or self.settings.block_css,
                max_requests_per_minute=self.settings.max_requests_per_minute,
                base_delay_seconds=self.settings.base_delay_seconds
            )
            self.active_sessions[campaign_name] = config
            self.session_counter += 1
            logger.info(f"Created session config for campaign: {campaign_name}")
        
        return self.active_sessions[campaign_name]
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next available proxy from pool."""
        if not self.proxy_pool:
            return None
        
        # Filter out failed proxies
        available_proxies = [p for p in self.proxy_pool if p not in self.failed_proxies]
        
        if not available_proxies:
            logger.warning("All proxies marked as failed, resetting pool")
            self.failed_proxies.clear()
            available_proxies = self.proxy_pool
        
        return random.choice(available_proxies)
    
    def get_browser_decorator_args(self, campaign_name: str) -> Dict[str, Any]:
        """
        Get arguments for @browser decorator based on research findings.
        
        Args:
            campaign_name: Name of the scraping campaign
            
        Returns:
            Dictionary of arguments for @browser decorator
        """
        config = self.get_session_config(campaign_name)
        
        # Base Botasaurus configuration from research
        browser_args = {
            # Anti-detection features
            'user_agent_rotation': config.user_agent_rotation,
            'headless': self.settings.headless_mode,
            
            # Resource blocking for stealth and speed
            'block_images': self.settings.block_images,
            'block_css': self.settings.block_css,
            
            # Session isolation
            'profile': config.profile_name,
            
            # Performance and stealth
            'page_load_strategy': 'eager',
            'stealth': True,
        }
        
        # Add proxy if available
        if config.proxy_url:
            browser_args['proxy'] = config.proxy_url
        
        # Consistent fingerprinting if requested
        if config.consistent_fingerprint:
            browser_args['user_agent'] = UserAgent.HASHED
            browser_args['window_size'] = WindowSize.HASHED
        
        logger.debug(f"Browser args for {campaign_name}: {browser_args}")
        return browser_args
    
    def human_like_delay(self, action_type: str = "navigation") -> float:
        """
        Generate human-like jittered delays based on research.
        
        Args:
            action_type: Type of action for context-appropriate delays
            
        Returns:
            Delay duration in seconds
        """
        # Research-based delay ranges
        delay_ranges = {
            'search': (3.0, 6.0),  # Bing search queries
            'navigation': (2.0, 4.0),  # Page navigation
            'extraction': (1.0, 2.5),  # Data extraction
            'pagination': (3.5, 5.5),  # Next page clicks
        }
        
        min_delay, max_delay = delay_ranges.get(action_type, (2.0, 4.0))
        
        # Apply base delay multiplier from settings
        base_multiplier = self.settings.base_delay_seconds / 3.0
        min_delay *= base_multiplier
        max_delay *= base_multiplier
        
        # Generate jittered delay
        delay = random.uniform(min_delay, max_delay)
        
        logger.debug(f"Generated {action_type} delay: {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def exponential_backoff(self, attempt: int, error_type: str = "rate_limit") -> float:
        """
        Implement exponential backoff based on research findings.
        
        Args:
            attempt: Current retry attempt (1-based)
            error_type: Type of error triggering backoff
            
        Returns:
            Backoff delay in seconds
        """
        # Research-based backoff: 5s, 10s, 20s, up to 2 minutes
        base_delays = {
            'rate_limit': 5.0,  # HTTP 429
            'forbidden': 8.0,   # HTTP 403
            'general': 3.0      # Other errors
        }
        
        base_delay = base_delays.get(error_type, 3.0)
        
        # Exponential growth: 5s, 10s, 20s, 40s, 80s, capped at 120s
        delay = min(base_delay * (2 ** (attempt - 1)), 120.0)
        
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.8, 1.2)
        final_delay = delay * jitter
        
        logger.warning(f"Exponential backoff (attempt {attempt}, {error_type}): {final_delay:.2f}s")
        time.sleep(final_delay)
        return final_delay
    
    def handle_rate_limit_response(self, response, proxy_url: Optional[str] = None) -> bool:
        """
        Handle rate limit responses based on research.
        
        Args:
            response: HTTP response object
            proxy_url: Proxy URL if used
            
        Returns:
            True if backoff was applied, False otherwise
        """
        if not hasattr(response, 'status_code'):
            return False
        
        if response.status_code == 429:  # Too Many Requests
            # Check for Retry-After header (research requirement)
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    wait_time = int(retry_after)
                    logger.info(f"Respecting Retry-After header: {wait_time}s")
                    time.sleep(wait_time)
                    return True
                except ValueError:
                    pass
            
            # Fallback to exponential backoff
            self.exponential_backoff(1, 'rate_limit')
            return True
        
        elif response.status_code == 403:  # Forbidden
            logger.warning("Received 403 Forbidden - possible blocking")
            
            # Mark proxy as unhealthy if used
            if proxy_url:
                self.mark_proxy_unhealthy(proxy_url)
            
            self.exponential_backoff(1, 'forbidden')
            return True
        
        return False
    
    def mark_proxy_unhealthy(self, proxy_url: str) -> None:
        """Mark proxy as unhealthy based on research."""
        self.failed_proxies.add(proxy_url)
        logger.warning(f"Marked proxy as unhealthy: {proxy_url}")
    
    def rotate_session(self, campaign_name: str) -> None:
        """Rotate session configuration for enhanced stealth."""
        if campaign_name in self.active_sessions:
            old_config = self.active_sessions[campaign_name]
            
            # Create new session config with rotated proxy
            new_config = BingSessionConfig(
                profile_name=f"{campaign_name}_{self.session_counter}",
                proxy_url=self._get_next_proxy(),
                user_agent_rotation=old_config.user_agent_rotation,
                block_resources=old_config.block_resources,
                max_requests_per_minute=old_config.max_requests_per_minute,
                base_delay_seconds=old_config.base_delay_seconds
            )
            
            self.active_sessions[campaign_name] = new_config
            self.session_counter += 1
            logger.info(f"Rotated session for campaign: {campaign_name}")
    
    def cleanup_session(self, campaign_name: str) -> None:
        """Clean up session configuration."""
        if campaign_name in self.active_sessions:
            del self.active_sessions[campaign_name]
            logger.info(f"Cleaned up session: {campaign_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get anti-detection statistics."""
        return {
            'active_sessions': len(self.active_sessions),
            'total_proxies': len(self.proxy_pool),
            'failed_proxies': len(self.failed_proxies),
            'settings': {
                'user_agent_rotation': self.settings.user_agent_rotation,
                'headless_mode': self.settings.headless_mode,
                'block_images': self.settings.block_images,
                'block_css': self.settings.block_css,
                'max_requests_per_minute': self.settings.max_requests_per_minute,
                'base_delay_seconds': self.settings.base_delay_seconds
            }
        }