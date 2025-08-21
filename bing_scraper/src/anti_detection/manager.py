"""
Anti-Detection Manager for Bing Scraper
Manages all anti-detection features using Botasaurus capabilities.
"""

import random
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .user_agents import UserAgentRotator
from .delays import HumanLikeDelays
from .proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

@dataclass
class BrowserProfile:
    """Browser profile for session isolation."""
    profile_id: str
    user_agent: str
    proxy_config: Optional[Dict[str, str]] = None
    viewport_size: tuple = (1920, 1080)
    timezone: str = "America/New_York"
    language: str = "en-US"

class AntiDetectionManager:
    """
    Comprehensive anti-detection management for web scraping.
    Integrates with Botasaurus for maximum stealth capabilities.
    """
    
    def __init__(self, settings):
        """Initialize anti-detection manager with settings."""
        self.settings = settings
        self.user_agent_rotator = UserAgentRotator()
        self.delays = HumanLikeDelays(settings)
        self.proxy_manager = ProxyManager(settings)
        
        # Session management
        self.active_profiles: Dict[str, BrowserProfile] = {}
        self.session_counter = 0
        
        logger.info("AntiDetectionManager initialized")
    
    def get_browser_config(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get optimized browser configuration for Botasaurus.
        
        Args:
            session_id: Optional session identifier
            
        Returns:
            Browser configuration dictionary
        """
        profile = self._get_or_create_profile(session_id)
        
        config = {
            # Core anti-detection features
            'headless': self.settings.headless_mode,
            'user_agent_rotation': self.settings.user_agent_rotation,
            'block_images': self.settings.block_images,
            'block_css': self.settings.block_css,
            'block_js': self.settings.block_js,
            
            # Browser fingerprinting protection
            'window_size': profile.viewport_size,
            'user_agent': profile.user_agent if not self.settings.user_agent_rotation else None,
            
            # Performance optimizations
            'page_load_strategy': 'eager',
            'disable_dev_shm': True,
            'disable_gpu': True,
            
            # Additional stealth options
            'stealth': True,
            'do_not_track': True,
            'locale': profile.language,
            'timezone': profile.timezone,
        }
        
        # Add proxy configuration if enabled
        if self.settings.proxy_enabled and profile.proxy_config:
            config.update(self._get_proxy_config(profile.proxy_config))
        
        logger.debug(f"Browser config generated for session {session_id}")
        return config
    
    def _get_or_create_profile(self, session_id: Optional[str]) -> BrowserProfile:
        """Get existing profile or create new one."""
        if session_id is None:
            session_id = f"session_{self.session_counter}"
            self.session_counter += 1
        
        if session_id not in self.active_profiles:
            profile = self._create_browser_profile(session_id)
            self.active_profiles[session_id] = profile
            logger.info(f"Created new browser profile: {session_id}")
        
        return self.active_profiles[session_id]
    
    def _create_browser_profile(self, profile_id: str) -> BrowserProfile:
        """Create a new browser profile with randomized characteristics."""
        
        # Random viewport sizes (common resolutions)
        viewports = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (1024, 768)
        ]
        
        # Random timezones
        timezones = [
            "America/New_York", "America/Los_Angeles", "America/Chicago",
            "Europe/London", "Europe/Berlin", "Asia/Tokyo"
        ]
        
        # Random languages
        languages = ["en-US", "en-GB", "en-CA", "en-AU"]
        
        profile = BrowserProfile(
            profile_id=profile_id,
            user_agent=self.user_agent_rotator.get_random_user_agent(),
            viewport_size=random.choice(viewports),
            timezone=random.choice(timezones),
            language=random.choice(languages)
        )
        
        # Add proxy if enabled
        if self.settings.proxy_enabled:
            profile.proxy_config = self.proxy_manager.get_proxy()
        
        return profile
    
    def _get_proxy_config(self, proxy_config: Dict[str, str]) -> Dict[str, Any]:
        """Convert proxy configuration for Botasaurus."""
        if not proxy_config:
            return {}
        
        return {
            'proxy': proxy_config,
            'proxy_authentication': {
                'username': proxy_config.get('username'),
                'password': proxy_config.get('password')
            } if proxy_config.get('username') else None
        }
    
    def apply_human_behavior(self, driver) -> None:
        """Apply human-like behavior patterns to browser session."""
        try:
            # Random delay before action
            self.delays.random_delay()
            
            # Simulate human-like mouse movements (if not headless)
            if not self.settings.headless_mode:
                self._simulate_mouse_movements(driver)
            
            # Random scrolling behavior
            if random.random() < 0.3:  # 30% chance to scroll
                self._simulate_scrolling(driver)
            
            # Random page interaction delay
            time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            logger.warning(f"Error applying human behavior: {e}")
    
    def _simulate_mouse_movements(self, driver) -> None:
        """Simulate natural mouse movements."""
        try:
            # Get page dimensions
            page_width = driver.run_js("return window.innerWidth;")
            page_height = driver.run_js("return window.innerHeight;")
            
            # Generate random mouse movements
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, min(page_width, 1920))
                y = random.randint(0, min(page_height, 1080))
                
                driver.run_js(f"""
                    var event = new MouseEvent('mousemove', {{
                        clientX: {x},
                        clientY: {y},
                        bubbles: true
                    }});
                    document.dispatchEvent(event);
                """)
                
                time.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            logger.debug(f"Mouse simulation error: {e}")
    
    def _simulate_scrolling(self, driver) -> None:
        """Simulate natural scrolling behavior."""
        try:
            # Random scroll amount and direction
            scroll_amount = random.randint(100, 500)
            if random.random() < 0.1:  # 10% chance to scroll up
                scroll_amount = -scroll_amount
            
            driver.run_js(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logger.debug(f"Scrolling simulation error: {e}")
    
    def rotate_session(self, session_id: str) -> None:
        """Rotate session characteristics for enhanced stealth."""
        if session_id in self.active_profiles:
            # Update user agent
            self.active_profiles[session_id].user_agent = \
                self.user_agent_rotator.get_random_user_agent()
            
            # Rotate proxy if enabled
            if self.settings.proxy_enabled:
                self.active_profiles[session_id].proxy_config = \
                    self.proxy_manager.get_proxy()
            
            logger.info(f"Session rotated: {session_id}")
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up session profile."""
        if session_id in self.active_profiles:
            del self.active_profiles[session_id]
            logger.info(f"Session cleaned up: {session_id}")
    
    def get_resource_blocking_rules(self) -> List[str]:
        """Get resource blocking patterns for Botasaurus."""
        blocking_patterns = []
        
        if self.settings.block_images:
            blocking_patterns.extend([
                "*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp", "*.bmp",
                "*.svg", "*.ico", "*.tiff"
            ])
        
        if self.settings.block_css:
            blocking_patterns.extend(["*.css", "*/css/*"])
        
        if self.settings.block_js:
            blocking_patterns.extend([
                "*.js", "*/js/*", "*/javascript/*",
                "*analytics*", "*tracking*", "*ads*"
            ])
        
        # Always block common tracking and ad domains
        blocking_patterns.extend([
            "*google-analytics*", "*googletagmanager*", "*facebook.com/tr*",
            "*doubleclick*", "*googlesyndication*", "*amazon-adsystem*"
        ])
        
        return blocking_patterns
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return {
            'active_sessions': len(self.active_profiles),
            'total_sessions_created': self.session_counter,
            'proxy_enabled': self.settings.proxy_enabled,
            'user_agent_rotation': self.settings.user_agent_rotation,
            'resource_blocking': {
                'images': self.settings.block_images,
                'css': self.settings.block_css,
                'js': self.settings.block_js
            }
        }