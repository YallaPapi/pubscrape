"""
Browser Manager with Botasaurus AntiDetectDriver Integration

Handles browser session creation, configuration, and anti-detection features.
Supports both headless and headful modes based on configuration.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import random

from botasaurus.browser import browser, Driver
from selenium.webdriver.chrome.options import Options as ChromeOptions


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


class BrowserManager:
    """
    Manages browser sessions with anti-detection capabilities using Botasaurus
    """
    
    def __init__(self, config: BrowserConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, Driver] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
    def get_browser_session(self, 
                          session_id: str, 
                          domain: Optional[str] = None) -> Driver:
        """
        Get or create a browser session with anti-detection features
        
        Args:
            session_id: Unique identifier for the session
            domain: Optional domain for domain-specific overrides
            
        Returns:
            Configured Driver instance with anti-detection enabled
        """
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
            
        # Apply domain-specific overrides
        session_config = self._get_session_config(domain)
        
        # Create browser with anti-detection using Botasaurus decorator pattern
        browser_instance = self._create_browser_session(session_id, session_config, domain)
        
        # Store session
        self.active_sessions[session_id] = browser_instance
        self.session_metadata[session_id] = {
            "domain": domain,
            "config": session_config,
            "created_at": self._get_timestamp(),
            "requests_count": 0
        }
        
        self.logger.info(f"Created browser session {session_id} for domain {domain}")
        
        return browser_instance
    
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
    
    def _create_browser_session(self, session_id: str, config: BrowserConfig, domain: Optional[str] = None) -> Driver:
        """
        Create a browser session using Botasaurus
        
        Args:
            session_id: Session identifier
            config: Browser configuration
            domain: Optional domain for domain-specific settings
            
        Returns:
            Configured Driver instance
        """
        # Prepare Botasaurus configuration
        botasaurus_config = {
            'headless': config.mode == BrowserMode.HEADLESS,
            'block_images': len(config.block_resources) > 0,
            'user_agent': config.user_agent,
            'window_size': f"{config.window_size[0]},{config.window_size[1]}"
        }
        
        # Add proxy if configured
        if config.proxy:
            botasaurus_config['proxy'] = config.proxy
        
        @browser(**botasaurus_config)
        def create_session(driver, data):
            """Create and configure browser session"""
            # Set timeouts
            driver.run_js(f"setTimeout(function() {{ console.log('Session {session_id} initialized'); }}, 100);")
            return driver
        
        # Create the browser session
        result = create_session({'session_id': session_id, 'domain': domain})
        
        self.logger.info(f"Created browser session {session_id} with config: mode={config.mode.value}, "
                        f"proxy={bool(config.proxy)}, block_resources={bool(config.block_resources)}")
        
        return result
    
    def close_session(self, session_id: str):
        """Close a browser session and clean up resources"""
        if session_id in self.active_sessions:
            try:
                self.active_sessions[session_id].quit()
                del self.active_sessions[session_id]
                
                if session_id in self.session_metadata:
                    del self.session_metadata[session_id]
                    
                self.logger.info(f"Closed browser session {session_id}")
            except Exception as e:
                self.logger.error(f"Error closing session {session_id}: {e}")
    
    def close_all_sessions(self):
        """Close all active browser sessions"""
        session_ids = list(self.active_sessions.keys())
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
def create_browser_manager(
    mode: str = "headless",
    block_resources: bool = True,
    domain_overrides: Optional[Dict[str, Dict[str, Any]]] = None
) -> BrowserManager:
    """
    Factory function to create a BrowserManager with common configurations
    
    Args:
        mode: Browser mode ("headless", "headful", "auto")
        block_resources: Whether to block images, CSS, etc.
        domain_overrides: Domain-specific configuration overrides
        
    Returns:
        Configured BrowserManager instance
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
    
    return BrowserManager(config)