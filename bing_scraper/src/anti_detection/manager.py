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
    created_at: float = 0.0
    last_used: float = 0.0
    request_count: int = 0
    browser_type: str = "chrome"
    fingerprint_data: Dict[str, Any] = None
    session_history: List[str] = None
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.last_used == 0.0:
            self.last_used = time.time()
        if self.fingerprint_data is None:
            self.fingerprint_data = {}
        if self.session_history is None:
            self.session_history = []

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
        """Create a new browser profile with sophisticated randomized characteristics."""
        
        # Choose browser type first (affects other choices)
        browser_types = ['chrome', 'firefox', 'safari', 'edge']
        browser_weights = [0.65, 0.15, 0.12, 0.08]  # Chrome dominance
        browser_type = random.choices(browser_types, weights=browser_weights)[0]
        
        # Get appropriate user agent for browser
        user_agent = self.user_agent_rotator.get_user_agent_by_browser(browser_type)
        
        # Viewport sizes based on real-world usage statistics
        common_viewports = [
            (1920, 1080),  # 22% usage
            (1366, 768),   # 12% usage
            (1536, 864),   # 8% usage
            (1440, 900),   # 7% usage
            (1280, 720),   # 6% usage
            (1600, 900),   # 5% usage
            (1280, 1024),  # 4% usage
            (1024, 768),   # 3% usage
            (1680, 1050),  # 2% usage
            (1280, 800),   # 2% usage
        ]
        
        viewport_weights = [22, 12, 8, 7, 6, 5, 4, 3, 2, 2]
        viewport_size = random.choices(common_viewports, weights=viewport_weights)[0]
        
        # Timezone/language combinations that make sense geographically
        geo_profiles = [
            # North America
            ("America/New_York", "en-US", 35),
            ("America/Los_Angeles", "en-US", 20),
            ("America/Chicago", "en-US", 15),
            ("America/Toronto", "en-CA", 5),
            
            # Europe
            ("Europe/London", "en-GB", 8),
            ("Europe/Berlin", "de-DE", 3),
            ("Europe/Paris", "fr-FR", 2),
            ("Europe/Madrid", "es-ES", 2),
            ("Europe/Rome", "it-IT", 1),
            
            # Asia Pacific
            ("Asia/Tokyo", "ja-JP", 2),
            ("Australia/Sydney", "en-AU", 3),
            ("Asia/Singapore", "en-SG", 1),
            
            # Other English-speaking
            ("Pacific/Auckland", "en-NZ", 1),
            ("Africa/Johannesburg", "en-ZA", 1),
            ("Asia/Kolkata", "en-IN", 1),
        ]
        
        # Select timezone/language combination
        selected_geo = random.choices(
            geo_profiles, 
            weights=[weight for _, _, weight in geo_profiles]
        )[0]
        timezone, language, _ = selected_geo
        
        # Create sophisticated fingerprint data
        fingerprint_data = self._generate_browser_fingerprint(browser_type, viewport_size)
        
        profile = BrowserProfile(
            profile_id=profile_id,
            user_agent=user_agent,
            viewport_size=viewport_size,
            timezone=timezone,
            language=language,
            browser_type=browser_type,
            fingerprint_data=fingerprint_data
        )
        
        # Add proxy if enabled (based on geographic profile)
        if self.settings.proxy_enabled:
            # Try to match proxy location to timezone when possible
            profile.proxy_config = self.proxy_manager.get_proxy(region=timezone.split('/')[0])
        
        logger.info(f"Created sophisticated profile {profile_id}: {browser_type} {viewport_size} {timezone}")
        return profile
    
    def _generate_browser_fingerprint(self, browser_type: str, viewport_size: tuple) -> Dict[str, Any]:
        """Generate realistic browser fingerprint data."""
        
        # Screen resolution (usually larger than viewport)
        width, height = viewport_size
        screen_width = width if random.random() < 0.3 else random.choice([
            width + 0,   # Fullscreen
            width + 280, # With sidebar
            width + 400, # Dual monitor setup
        ])
        screen_height = height if random.random() < 0.3 else random.choice([
            height + 0,   # Fullscreen  
            height + 80,  # With taskbar
            height + 120, # With top/bottom bars
        ])
        
        # Hardware concurrency (CPU cores)
        cpu_cores = random.choices([2, 4, 6, 8, 12, 16], weights=[5, 35, 25, 20, 10, 5])[0]
        
        # Memory (device memory API)
        memory_gb = random.choices([4, 8, 16, 32], weights=[15, 50, 30, 5])[0]
        
        # WebGL renderer strings (realistic GPU models)
        gpu_models = [
            "ANGLE (Intel, Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "AMD Radeon Pro 560X OpenGL Engine",
            "Intel Iris Pro OpenGL Engine",
            "NVIDIA GeForce GTX 1050 Ti/PCIe/SSE2",
        ]
        
        # Platform strings
        if browser_type == 'safari':
            platform = random.choice(["MacIntel", "iPhone", "iPad"])
        elif browser_type == 'edge':
            platform = "Win32"
        else:
            platform = random.choice(["Win32", "MacIntel", "Linux x86_64"])
        
        fingerprint = {
            # Screen properties
            'screen_width': screen_width,
            'screen_height': screen_height,
            'viewport_width': width,
            'viewport_height': height,
            'color_depth': random.choice([24, 32]),
            'pixel_ratio': random.choice([1, 1.25, 1.5, 2]),
            
            # Hardware properties
            'hardware_concurrency': cpu_cores,
            'device_memory': memory_gb,
            'platform': platform,
            'webgl_renderer': random.choice(gpu_models),
            
            # Browser-specific features
            'do_not_track': random.choice([True, False, None]),
            'cookie_enabled': True,
            'java_enabled': False,
            'language_count': random.randint(1, 3),
            
            # Canvas fingerprint seed (used to generate consistent canvas data)
            'canvas_seed': random.randint(1000000, 9999999),
            
            # Audio fingerprint seed
            'audio_seed': random.randint(1000000, 9999999),
            
            # WebRTC properties
            'webrtc_enabled': random.choice([True, False]),
            
            # Plugins (browser-specific)
            'plugin_count': self._get_realistic_plugin_count(browser_type),
            
            # Timezone offset (minutes from UTC)
            'timezone_offset': random.choice([-480, -420, -360, -300, -240, -180, 0, 60, 120, 180, 240, 300, 480, 540]),
        }
        
        return fingerprint
    
    def _get_realistic_plugin_count(self, browser_type: str) -> int:
        """Get realistic plugin count based on browser type."""
        if browser_type == 'chrome':
            return random.choice([3, 4, 5])  # PDF Viewer, Chrome PDF Plugin, etc.
        elif browser_type == 'firefox':
            return random.choice([0, 1, 2])  # Modern Firefox has fewer plugins
        elif browser_type == 'safari':
            return 0  # Safari doesn't expose plugins
        elif browser_type == 'edge':
            return random.choice([2, 3, 4])  # Similar to Chrome
        else:
            return random.choice([0, 1, 2, 3])
    
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
    
    def rotate_session(self, session_id: str, full_rotation: bool = False) -> bool:
        """
        Rotate session characteristics for enhanced stealth.
        
        Args:
            session_id: Session to rotate
            full_rotation: Whether to do complete profile regeneration
            
        Returns:
            True if rotation was successful
        """
        if session_id not in self.active_profiles:
            logger.warning(f"Cannot rotate non-existent session: {session_id}")
            return False
        
        profile = self.active_profiles[session_id]
        
        if full_rotation:
            # Complete profile regeneration
            logger.info(f"Performing full rotation for session {session_id}")
            
            # Keep session history but regenerate everything else
            old_history = profile.session_history.copy()
            
            # Create completely new profile
            new_profile = self._create_browser_profile(session_id)
            new_profile.session_history = old_history
            new_profile.session_history.append(f"full_rotation_{int(time.time())}")
            
            self.active_profiles[session_id] = new_profile
            
        else:
            # Partial rotation (less suspicious)
            logger.debug(f"Performing partial rotation for session {session_id}")
            
            # Update user agent (keep same browser type for consistency)
            profile.user_agent = self.user_agent_rotator.get_user_agent_by_browser(profile.browser_type)
            
            # Rotate proxy if enabled
            if self.settings.proxy_enabled:
                profile.proxy_config = self.proxy_manager.get_proxy()
            
            # Minor viewport adjustments (simulate window resize)
            if random.random() < 0.3:
                width, height = profile.viewport_size
                width_delta = random.randint(-100, 100)
                height_delta = random.randint(-50, 50)
                new_width = max(800, min(2560, width + width_delta))
                new_height = max(600, min(1440, height + height_delta))
                profile.viewport_size = (new_width, new_height)
                logger.debug(f"Adjusted viewport to {profile.viewport_size}")
            
            # Update timestamps
            profile.last_used = time.time()
            profile.session_history.append(f"partial_rotation_{int(time.time())}")
        
        logger.info(f"Session rotated: {session_id} (full={full_rotation})")
        return True
    
    def should_rotate_session(self, session_id: str) -> bool:
        """
        Determine if a session should be rotated based on usage patterns.
        
        Args:
            session_id: Session to check
            
        Returns:
            True if session should be rotated
        """
        if session_id not in self.active_profiles:
            return False
        
        profile = self.active_profiles[session_id]
        current_time = time.time()
        
        # Age-based rotation (rotate sessions older than 2 hours)
        session_age = current_time - profile.created_at
        if session_age > 7200:  # 2 hours
            logger.debug(f"Session {session_id} needs rotation due to age: {session_age:.0f}s")
            return True
        
        # Request count-based rotation (rotate after 50 requests)
        if profile.request_count > 50:
            logger.debug(f"Session {session_id} needs rotation due to request count: {profile.request_count}")
            return True
        
        # Inactivity-based rotation (rotate if unused for 30 minutes)
        inactivity = current_time - profile.last_used
        if inactivity > 1800:  # 30 minutes
            logger.debug(f"Session {session_id} needs rotation due to inactivity: {inactivity:.0f}s")
            return True
        
        return False
    
    def update_session_usage(self, session_id: str, activity: str = "request") -> None:
        """
        Update session usage statistics.
        
        Args:
            session_id: Session to update
            activity: Type of activity performed
        """
        if session_id in self.active_profiles:
            profile = self.active_profiles[session_id]
            profile.last_used = time.time()
            profile.request_count += 1
            profile.session_history.append(f"{activity}_{int(time.time())}")
            
            # Trim history to keep only last 20 entries
            if len(profile.session_history) > 20:
                profile.session_history = profile.session_history[-20:]
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up session profile."""
        if session_id in self.active_profiles:
            profile = self.active_profiles[session_id]
            logger.info(f"Cleaning up session {session_id}: {profile.request_count} requests, "
                       f"age: {time.time() - profile.created_at:.0f}s")
            del self.active_profiles[session_id]
    
    def cleanup_stale_sessions(self, max_age_hours: int = 6) -> int:
        """
        Clean up stale sessions that are too old.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        stale_sessions = []
        
        for session_id, profile in self.active_profiles.items():
            if current_time - profile.created_at > max_age_seconds:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            self.cleanup_session(session_id)
        
        if stale_sessions:
            logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")
        
        return len(stale_sessions)
    
    def get_session_health_score(self, session_id: str) -> float:
        """
        Calculate a health score for a session (0.0 = needs immediate rotation, 1.0 = perfect).
        
        Args:
            session_id: Session to evaluate
            
        Returns:
            Health score between 0.0 and 1.0
        """
        if session_id not in self.active_profiles:
            return 0.0
        
        profile = self.active_profiles[session_id]
        current_time = time.time()
        
        # Age score (newer is better)
        session_age = current_time - profile.created_at
        age_score = max(0.0, 1.0 - (session_age / 7200))  # Linear decline over 2 hours
        
        # Request count score (fewer requests is better)
        request_score = max(0.0, 1.0 - (profile.request_count / 50))  # Linear decline over 50 requests
        
        # Inactivity score (recent activity is better)
        inactivity = current_time - profile.last_used
        inactivity_score = max(0.0, 1.0 - (inactivity / 1800))  # Linear decline over 30 minutes
        
        # Weighted average
        health_score = (age_score * 0.4 + request_score * 0.4 + inactivity_score * 0.2)
        
        return health_score
    
    def get_best_session(self, exclude_sessions: List[str] = None) -> Optional[str]:
        """
        Get the session ID with the best health score.
        
        Args:
            exclude_sessions: Sessions to exclude from selection
            
        Returns:
            Session ID with best health score, or None if no good sessions
        """
        if exclude_sessions is None:
            exclude_sessions = []
        
        best_session = None
        best_score = 0.0
        
        for session_id in self.active_profiles:
            if session_id in exclude_sessions:
                continue
            
            score = self.get_session_health_score(session_id)
            if score > best_score:
                best_score = score
                best_session = session_id
        
        # Only return session if it has a decent health score
        if best_score > 0.3:
            return best_session
        
        return None
    
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