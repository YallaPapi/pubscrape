"""
Browser Manager with Proper Botasaurus Integration

Fixed to work with the actual Botasaurus API patterns.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import random

from botasaurus.browser import browser, Driver


class BrowserMode(Enum):
    HEADLESS = "headless"
    HEADFUL = "headful"
    AUTO = "auto"  # Determined by config or domain-specific rules


@dataclass
class BrowserConfig:
    """Configuration for browser sessions"""
    mode: BrowserMode = BrowserMode.HEADLESS
    user_agent: Optional[str] = None
    profile_path: Optional[str] = None
    proxy: Optional[str] = None
    block_resources: List[str] = None
    window_size: tuple = (1920, 1080)
    timeout: int = 30
    max_retries: int = 3
    domain_overrides: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        if self.block_resources is None:
            self.block_resources = [
                "image", "stylesheet", "font", "media",
                "*.png", "*.jpg", "*.jpeg", "*.gif", "*.css",
                "*.woff", "*.woff2", "*.ttf", "*.mp4", "*.mp3"
            ]
        if self.domain_overrides is None:
            self.domain_overrides = {}


class BotasaurusBrowserManager:
    """
    Browser Manager that works with actual Botasaurus patterns
    Creates browser functions dynamically based on configuration
    """
    
    def __init__(self, config: BrowserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_browser_functions: Dict[str, Any] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("BotasaurusBrowserManager initialized")
        
    def create_browser_function(self, session_id: str, domain: Optional[str] = None):
        """
        Create a browser function for a specific session using Botasaurus patterns
        
        Args:
            session_id: Unique identifier for the session
            domain: Optional domain for domain-specific overrides
            
        Returns:
            Browser function that can be called with data
        """
        # Apply domain-specific overrides
        session_config = self._get_session_config(domain)
        
        # Prepare Botasaurus decorator arguments
        decorator_args = {
            'headless': session_config.mode == BrowserMode.HEADLESS,
            'block_images': len(session_config.block_resources) > 0,
        }
        
        if session_config.user_agent:
            decorator_args['user_agent'] = session_config.user_agent
        
        if session_config.proxy:
            decorator_args['proxy'] = session_config.proxy
        
        # Create the browser function with the decorator
        @browser(**decorator_args)
        def browser_session(driver, data):
            """Browser session created with Botasaurus"""
            try:
                # Store session metadata in driver for later access
                session_data = {
                    'session_id': session_id,
                    'domain': domain,
                    'config': session_config,
                    'created_at': self._get_timestamp(),
                    'requests_count': 0
                }
                
                # Execute the actual browser task based on data
                if 'action' in data:
                    if data['action'] == 'navigate':
                        driver.get(data['url'])
                        driver.sleep(2)
                        return {
                            'success': True,
                            'title': driver.title,
                            'url': driver.current_url,
                            'session_id': session_id
                        }
                    elif data['action'] == 'search':
                        # Use google_get for more reliable searching
                        driver.google_get(data['query'])
                        driver.sleep(2)
                        return {
                            'success': True,
                            'title': driver.title,
                            'url': driver.current_url,
                            'query': data['query'],
                            'page_html_length': len(driver.page_html()),
                            'session_id': session_id
                        }
                
                # Default action - just return driver status
                return {
                    'success': True,
                    'session_id': session_id,
                    'driver_ready': True,
                    'user_agent': driver.user_agent
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'session_id': session_id
                }
        
        # Store the browser function
        self.active_browser_functions[session_id] = browser_session
        self.session_metadata[session_id] = {
            "domain": domain,
            "config": session_config,
            "created_at": self._get_timestamp(),
            "requests_count": 0
        }
        
        self.logger.info(f"Created browser function for session {session_id}, domain {domain}")
        
        return browser_session
    
    def execute_browser_action(self, session_id: str, action_data: Dict[str, Any]):
        """
        Execute a browser action using the session's browser function
        
        Args:
            session_id: Session identifier
            action_data: Data describing the action to execute
            
        Returns:
            Result of the browser action
        """
        if session_id not in self.active_browser_functions:
            # Create browser function if it doesn't exist
            domain = action_data.get('domain')
            self.create_browser_function(session_id, domain)
        
        browser_func = self.active_browser_functions[session_id]
        
        try:
            result = browser_func(action_data)
            
            # Update session stats
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["requests_count"] += 1
                self.session_metadata[session_id]["last_activity"] = self._get_timestamp()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Browser action failed for session {session_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
    
    def navigate_to_url(self, session_id: str, url: str, domain: Optional[str] = None):
        """Convenience method for navigation"""
        return self.execute_browser_action(session_id, {
            'action': 'navigate',
            'url': url,
            'domain': domain
        })
    
    def search_query(self, session_id: str, query: str, domain: Optional[str] = None):
        """Convenience method for searching"""
        return self.execute_browser_action(session_id, {
            'action': 'search',
            'query': query,
            'domain': domain
        })
    
    def _get_session_config(self, domain: Optional[str] = None) -> BrowserConfig:
        """Apply domain-specific configuration overrides"""
        config = self.config
        
        if domain and domain in self.config.domain_overrides:
            overrides = self.config.domain_overrides[domain]
            
            # Create a copy of config with overrides
            config_dict = {
                "mode": BrowserMode(overrides.get("mode", config.mode.value)),
                "user_agent": overrides.get("user_agent", config.user_agent),
                "profile_path": overrides.get("profile_path", config.profile_path),
                "proxy": overrides.get("proxy", config.proxy),
                "block_resources": overrides.get("block_resources", config.block_resources),
                "window_size": overrides.get("window_size", config.window_size),
                "timeout": overrides.get("timeout", config.timeout),
                "max_retries": overrides.get("max_retries", config.max_retries),
                "domain_overrides": config.domain_overrides
            }
            
            config = BrowserConfig(**config_dict)
            
        return config
    
    def close_session(self, session_id: str):
        """Close a browser session and clean up resources"""
        if session_id in self.active_browser_functions:
            try:
                # Remove the browser function
                del self.active_browser_functions[session_id]
                
                if session_id in self.session_metadata:
                    del self.session_metadata[session_id]
                    
                self.logger.info(f"Closed browser session {session_id}")
            except Exception as e:
                self.logger.error(f"Error closing session {session_id}: {e}")
    
    def close_all_sessions(self):
        """Close all active browser sessions"""
        session_ids = list(self.active_browser_functions.keys())
        for session_id in session_ids:
            self.close_session(session_id)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a browser session"""
        return self.session_metadata.get(session_id)
    
    def update_session_stats(self, session_id: str, requests_count: int = 1):
        """Update session statistics"""
        if session_id in self.session_metadata:
            self.session_metadata[session_id]["requests_count"] += requests_count
            self.session_metadata[session_id]["last_activity"] = self._get_timestamp()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all_sessions()


# Factory function for easy browser creation
def create_botasaurus_browser_manager(
    mode: str = "headless",
    block_resources: bool = True,
    domain_overrides: Optional[Dict[str, Dict[str, Any]]] = None
) -> BotasaurusBrowserManager:
    """
    Factory function to create a BotasaurusBrowserManager with common configurations
    
    Args:
        mode: Browser mode ("headless", "headful", "auto")
        block_resources: Whether to block images, CSS, etc.
        domain_overrides: Domain-specific configuration overrides
        
    Returns:
        Configured BotasaurusBrowserManager instance
    """
    config = BrowserConfig(
        mode=BrowserMode(mode),
        block_resources=[
            "image", "stylesheet", "font", "media",
            "*.png", "*.jpg", "*.jpeg", "*.gif", "*.css",
            "*.woff", "*.woff2", "*.ttf", "*.mp4", "*.mp3"
        ] if block_resources else [],
        domain_overrides=domain_overrides or {}
    )
    
    return BotasaurusBrowserManager(config)