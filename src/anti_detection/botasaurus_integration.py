"""
Botasaurus Integration Module

Seamlessly integrates the anti-detection system with Botasaurus for
maximum stealth and compatibility with existing scraping infrastructure.
"""

import logging
import time
import asyncio
import random
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
import json

# Optional Botasaurus imports
try:
    from botasaurus.browser import browser, Driver
    from botasaurus.anti_detect_driver import AntiDetectDriver
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    browser = None
    Driver = None
    AntiDetectDriver = None

from .stealth_manager import StealthManager, StealthConfig, StealthLevel
from .proxy_rotator import ProxyInfo
from .behavior_simulator import BehaviorSimulator, IntensityLevel
from .rate_limiter import AdaptiveRateLimiter, RequestStatus


class BotasaurusStealthWrapper:
    """
    Wrapper class that integrates anti-detection system with Botasaurus
    """
    
    def __init__(self, 
                 stealth_manager: Optional[StealthManager] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize Botasaurus integration
        
        Args:
            stealth_manager: Pre-configured stealth manager
            config: Configuration dictionary
        """
        self.logger = self._setup_logging()
        self.config = config or {}
        
        # Initialize or use provided stealth manager
        if stealth_manager:
            self.stealth_manager = stealth_manager
        else:
            stealth_config = self._create_stealth_config_from_botasaurus_config()
            self.stealth_manager = StealthManager(stealth_config)
        
        # Active sessions tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Integration state
        self.integration_enabled = BOTASAURUS_AVAILABLE
        
        if not self.integration_enabled:
            self.logger.warning("Botasaurus not available - running in compatibility mode")
        else:
            self.logger.info("Botasaurus integration initialized successfully")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for Botasaurus integration"""
        logger = logging.getLogger("botasaurus_integration")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _create_stealth_config_from_botasaurus_config(self) -> StealthConfig:
        """Create stealth configuration based on Botasaurus-style config"""
        # Map common Botasaurus options to stealth configuration
        botasaurus_config = self.config.get('botasaurus', {})
        
        stealth_level = StealthLevel.MODERATE
        if botasaurus_config.get('use_stealth', True):
            if botasaurus_config.get('headless', True):
                stealth_level = StealthLevel.AGGRESSIVE
            else:
                stealth_level = StealthLevel.MAXIMUM
        
        return StealthConfig(
            stealth_level=stealth_level,
            use_proxies=botasaurus_config.get('proxy') is not None,
            simulate_human_behavior=not botasaurus_config.get('headless', True),
            adaptive_rate_limiting=True,
            cloudflare_evasion=botasaurus_config.get('cloudflare_bypass', True),
            recaptcha_detection=True,
            session_rotation_interval=1800  # 30 minutes
        )
    
    def create_enhanced_browser_decorator(self, **kwargs):
        """
        Create an enhanced browser decorator with anti-detection features
        
        Args:
            **kwargs: Standard Botasaurus browser options plus anti-detection options
            
        Returns:
            Enhanced browser decorator function
        """
        if not BOTASAURUS_AVAILABLE:
            raise RuntimeError("Botasaurus is not available for enhanced browser decorator")
        
        # Extract anti-detection specific options
        anti_detect_options = kwargs.pop('anti_detect', {})
        session_id = kwargs.pop('session_id', None)
        domain = kwargs.pop('domain', None)
        
        # Merge with existing stealth configuration
        stealth_config = self._merge_stealth_options(kwargs, anti_detect_options)
        
        def enhanced_browser(func):
            @browser(**stealth_config)
            def wrapper(driver: Driver, data):
                # Initialize session if needed
                if session_id:
                    session_info = self._initialize_session(session_id, domain, driver)
                else:
                    session_info = {}
                
                # Apply pre-request stealth measures
                self._apply_pre_request_stealth(driver, session_info)
                
                try:
                    # Execute the original function
                    result = func(driver, data)
                    
                    # Apply post-request stealth measures
                    self._apply_post_request_stealth(driver, session_info, success=True)
                    
                    return result
                
                except Exception as e:
                    # Handle errors with stealth measures
                    self._apply_post_request_stealth(driver, session_info, success=False)
                    self._handle_scraping_error(driver, session_info, e)
                    raise
                
                finally:
                    # Clean up session if needed
                    if session_id and session_id in self.active_sessions:
                        self._finalize_session(session_id)
            
            return wrapper
        
        return enhanced_browser
    
    def _merge_stealth_options(self, 
                              botasaurus_kwargs: Dict[str, Any], 
                              anti_detect_options: Dict[str, Any]) -> Dict[str, Any]:
        """Merge Botasaurus options with anti-detection settings"""
        
        # Start with base Botasaurus configuration
        merged_config = botasaurus_kwargs.copy()
        
        # Apply anti-detection enhancements
        stealth_level = anti_detect_options.get('stealth_level', 'moderate')
        
        if stealth_level in ['aggressive', 'maximum']:
            merged_config.update({
                'headless': False,
                'block_images': True,
                'reuse_driver': True,
                'window_size': (1920, 1080),
                'use_stealth': True
            })
        
        # User agent configuration
        if hasattr(self.stealth_manager, 'user_agent_manager') and self.stealth_manager.user_agent_manager:
            user_agent = self.stealth_manager.user_agent_manager.get_user_agent()
            merged_config['user_agent'] = user_agent.user_agent
        
        # Proxy configuration
        if hasattr(self.stealth_manager, 'proxy_rotator') and self.stealth_manager.proxy_rotator:
            proxy_info = asyncio.run(self.stealth_manager.proxy_rotator.get_proxy())
            if proxy_info:
                merged_config['proxy'] = proxy_info.proxy_url
        
        # Browser options for maximum stealth
        if 'browser_options' not in merged_config:
            merged_config['browser_options'] = {}
        
        merged_config['browser_options'].update({
            'disable_blink_features': 'AutomationControlled',
            'exclude_switches': ['enable-automation'],
            'add_argument': [
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--no-sandbox',
                '--disable-application-cache',
                '--disable-gpu',
                '--no-default-browser-check',
                '--no-first-run',
                '--disable-default-apps'
            ]
        })
        
        return merged_config
    
    def _initialize_session(self, session_id: str, domain: Optional[str], driver: Driver) -> Dict[str, Any]:
        """Initialize an anti-detection session"""
        session_info = {
            'session_id': session_id,
            'domain': domain,
            'start_time': time.time(),
            'driver': driver,
            'request_count': 0
        }
        
        # Create stealth session
        if domain:
            stealth_session_id = asyncio.run(
                self.stealth_manager.create_stealth_session(domain, session_id)
            )
            session_info['stealth_session_id'] = stealth_session_id
        
        self.active_sessions[session_id] = session_info
        
        self.logger.info(f"Initialized enhanced session: {session_id}")
        return session_info
    
    def _apply_pre_request_stealth(self, driver: Driver, session_info: Dict[str, Any]):
        """Apply stealth measures before making requests"""
        session_id = session_info.get('session_id')
        
        if not session_id:
            return
        
        # Apply behavior simulation
        if (hasattr(self.stealth_manager, 'behavior_simulator') and 
            self.stealth_manager.behavior_simulator):
            
            asyncio.run(
                self.stealth_manager.behavior_simulator.pre_request_behavior(session_id)
            )
        
        # Apply random delays for human-like behavior
        if self.stealth_manager.config.simulate_human_behavior:
            delay = random.uniform(0.5, 2.0)
            time.sleep(delay)
        
        # Random mouse movements (if headless=False)
        if not driver.headless:
            self._simulate_human_activity(driver)
    
    def _apply_post_request_stealth(self, 
                                   driver: Driver, 
                                   session_info: Dict[str, Any], 
                                   success: bool):
        """Apply stealth measures after receiving response"""
        session_id = session_info.get('session_id')
        
        if not session_id:
            return
        
        session_info['request_count'] = session_info.get('request_count', 0) + 1
        
        # Check for detection patterns in page content
        try:
            page_html = driver.page_html
            detection_info = self.stealth_manager._detect_anti_bot_measures(page_html)
            
            if any(detection_info.values()):
                self.logger.warning(f"Detection patterns found: {detection_info}")
                self._handle_detection_event(driver, session_info, detection_info)
        
        except Exception as e:
            self.logger.debug(f"Could not check for detection patterns: {e}")
        
        # Apply behavior simulation
        if (hasattr(self.stealth_manager, 'behavior_simulator') and 
            self.stealth_manager.behavior_simulator):
            
            asyncio.run(
                self.stealth_manager.behavior_simulator.post_request_behavior(
                    session_id, success
                )
            )
        
        # Random post-request delay
        if success and self.stealth_manager.config.simulate_human_behavior:
            delay = random.uniform(1.0, 3.0)
            time.sleep(delay)
    
    def _simulate_human_activity(self, driver: Driver):
        """Simulate human-like browser activity"""
        try:
            # Random scrolling
            if random.random() < 0.3:
                scroll_amount = random.randint(100, 500)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.1, 0.3))
            
            # Random mouse movements (limited simulation)
            if random.random() < 0.2:
                x = random.randint(100, 1000)
                y = random.randint(100, 600)
                driver.execute_script(f"""
                    var event = new MouseEvent('mousemove', {{
                        clientX: {x},
                        clientY: {y}
                    }});
                    document.dispatchEvent(event);
                """)
        
        except Exception as e:
            self.logger.debug(f"Could not simulate human activity: {e}")
    
    def _handle_detection_event(self, 
                               driver: Driver, 
                               session_info: Dict[str, Any], 
                               detection_info: Dict[str, Any]):
        """Handle detection events with appropriate responses"""
        session_id = session_info.get('session_id')
        
        # Cloudflare detection
        if detection_info.get('cloudflare_detected'):
            self.logger.warning("Cloudflare detected - attempting bypass")
            try:
                driver.detect_and_bypass_cloudflare()
                time.sleep(random.uniform(3.0, 8.0))
            except Exception as e:
                self.logger.error(f"Cloudflare bypass failed: {e}")
        
        # reCAPTCHA detection
        if detection_info.get('recaptcha_detected'):
            self.logger.warning("reCAPTCHA detected - applying extended delay")
            time.sleep(random.uniform(10.0, 20.0))
        
        # Rate limiting detection
        if detection_info.get('rate_limiting_detected'):
            self.logger.warning("Rate limiting detected - applying backoff")
            backoff_time = random.uniform(30.0, 120.0)
            time.sleep(backoff_time)
        
        # Update session with detection event
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session['detection_events'] = session.get('detection_events', 0) + 1
    
    def _handle_scraping_error(self, 
                              driver: Driver, 
                              session_info: Dict[str, Any], 
                              error: Exception):
        """Handle scraping errors with anti-detection measures"""
        session_id = session_info.get('session_id')
        error_str = str(error).lower()
        
        # Determine error type and apply appropriate response
        if any(pattern in error_str for pattern in ['timeout', 'connection', 'network']):
            self.logger.warning(f"Network error in session {session_id}: {error}")
            time.sleep(random.uniform(5.0, 15.0))
        
        elif any(pattern in error_str for pattern in ['blocked', 'forbidden', '403']):
            self.logger.warning(f"Access blocked in session {session_id}: {error}")
            time.sleep(random.uniform(30.0, 60.0))
        
        elif '429' in error_str or 'rate limit' in error_str:
            self.logger.warning(f"Rate limited in session {session_id}: {error}")
            time.sleep(random.uniform(60.0, 180.0))
        
        else:
            self.logger.error(f"Unexpected error in session {session_id}: {error}")
    
    def _finalize_session(self, session_id: str):
        """Clean up and finalize a session"""
        if session_id not in self.active_sessions:
            return
        
        session_info = self.active_sessions[session_id]
        duration = time.time() - session_info['start_time']
        request_count = session_info.get('request_count', 0)
        
        self.logger.info(f"Finalizing session {session_id}: "
                        f"duration={duration:.2f}s, requests={request_count}")
        
        # Close stealth session if exists
        stealth_session_id = session_info.get('stealth_session_id')
        if stealth_session_id:
            asyncio.run(self.stealth_manager.close_session(stealth_session_id))
        
        del self.active_sessions[session_id]
    
    def create_stealth_scraper(self, 
                              target_function: Callable,
                              stealth_options: Optional[Dict[str, Any]] = None) -> Callable:
        """
        Create a stealth-enhanced version of a scraping function
        
        Args:
            target_function: Original scraping function
            stealth_options: Anti-detection options
            
        Returns:
            Enhanced scraping function with anti-detection
        """
        stealth_opts = stealth_options or {}
        
        def stealth_enhanced_scraper(data, **kwargs):
            # Generate unique session ID
            session_id = f"stealth_session_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Prepare enhanced browser configuration
            browser_config = {
                'headless': False,
                'reuse_driver': True,
                'block_images': True,
                'use_stealth': True,
                'session_id': session_id,
                **stealth_opts
            }
            
            # Create enhanced browser decorator
            enhanced_browser = self.create_enhanced_browser_decorator(**browser_config)
            
            # Wrap the target function
            @enhanced_browser
            def wrapped_function(driver, data):
                return target_function(driver, data)
            
            # Execute with enhanced stealth
            return wrapped_function(data)
        
        return stealth_enhanced_scraper
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get statistics about the Botasaurus integration"""
        return {
            'integration_enabled': self.integration_enabled,
            'active_sessions': len(self.active_sessions),
            'botasaurus_available': BOTASAURUS_AVAILABLE,
            'stealth_manager_active': self.stealth_manager is not None,
            'components_active': {
                'user_agent_manager': hasattr(self.stealth_manager, 'user_agent_manager'),
                'proxy_rotator': hasattr(self.stealth_manager, 'proxy_rotator'),
                'behavior_simulator': hasattr(self.stealth_manager, 'behavior_simulator'),
                'rate_limiter': hasattr(self.stealth_manager, 'rate_limiter')
            },
            'session_details': {
                session_id: {
                    'duration': time.time() - session_info['start_time'],
                    'request_count': session_info.get('request_count', 0),
                    'detection_events': session_info.get('detection_events', 0)
                }
                for session_id, session_info in self.active_sessions.items()
            }
        }


# Convenience functions for easy integration

def create_stealth_browser(**kwargs):
    """
    Create a Botasaurus browser decorator with integrated anti-detection
    
    Args:
        **kwargs: Browser configuration options
        
    Returns:
        Enhanced browser decorator
    """
    wrapper = BotasaurusStealthWrapper()
    return wrapper.create_enhanced_browser_decorator(**kwargs)


def enhance_existing_scraper(scraper_function: Callable, 
                           stealth_level: str = "moderate") -> Callable:
    """
    Enhance an existing Botasaurus scraper with anti-detection
    
    Args:
        scraper_function: Existing scraper function
        stealth_level: Level of anti-detection (minimal, moderate, aggressive, maximum)
        
    Returns:
        Enhanced scraper function
    """
    stealth_config = StealthConfig(
        stealth_level=StealthLevel(stealth_level),
        simulate_human_behavior=True,
        adaptive_rate_limiting=True
    )
    
    stealth_manager = StealthManager(stealth_config)
    wrapper = BotasaurusStealthWrapper(stealth_manager)
    
    return wrapper.create_stealth_scraper(scraper_function)


def create_anti_detection_config_for_botasaurus(domain: str) -> Dict[str, Any]:
    """
    Create Botasaurus-compatible configuration with anti-detection optimized for specific domain
    
    Args:
        domain: Target domain for scraping
        
    Returns:
        Botasaurus configuration dictionary
    """
    base_config = {
        'headless': False,
        'reuse_driver': True,
        'use_stealth': True,
        'window_size': (1920, 1080),
        'block_images': True
    }
    
    # Domain-specific optimizations
    domain_lower = domain.lower()
    
    if 'bing.com' in domain_lower:
        base_config.update({
            'block_images': False,  # Bing may need images for SERP parsing
            'user_agent': None,     # Let Botasaurus use stealth user agent
            'headless': False,      # Headful for maximum stealth
        })
    
    elif any(se in domain_lower for se in ['google.com', 'duckduckgo.com']):
        base_config.update({
            'headless': True,       # More careful approach
            'block_images': True,
            'reuse_driver': False,  # Fresh sessions
        })
    
    elif any(social in domain_lower for social in ['facebook', 'twitter', 'linkedin']):
        base_config.update({
            'headless': False,      # Social media sites often require headful
            'block_images': False,  # Images may be important
        })
    
    return base_config


# Export for backward compatibility and convenience
BotasaurusAntiDetection = BotasaurusStealthWrapper
stealth_browser = create_stealth_browser