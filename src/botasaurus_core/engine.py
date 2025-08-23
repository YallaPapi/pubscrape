"""
Botasaurus Core Engine Implementation
TASK-F001: Core Botasaurus integration with anti-detection and session management

This module provides the foundation for all Botasaurus-based scraping operations
with enterprise-grade anti-detection, session isolation, and browser management.
"""

import os
import json
import random
import time
import weakref
import gc
from typing import Dict, Optional, List, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from botasaurus import *
from botasaurus.browser import Driver, Wait
from botasaurus.request import AntiDetectDriver

# Import secure configuration system
try:
    from ..security.secure_config import (
        get_browser_config, 
        get_security_config,
        InputValidator
    )
except ImportError:
    # Fallback imports for standalone usage
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'security'))
    from secure_config import (
        get_browser_config, 
        get_security_config,
        InputValidator
    )

# SECURITY FIX: Remove hardcoded environment variables
# Configuration now comes from secure_config.py instead of environment variables


@dataclass
class SessionConfig:
    """Configuration for browser session isolation and management"""
    session_id: str
    profile_name: str
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    viewport_size: tuple = (1920, 1080)
    user_agent: Optional[str] = None
    timezone: str = "America/New_York"
    locale: str = "en-US"
    stealth_level: int = 3  # 1=basic, 2=moderate, 3=maximum
    max_memory_mb: int = 2048
    enable_cache: bool = True
    block_images: bool = False
    block_media: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'profile_name': self.profile_name,
            'use_proxy': self.use_proxy,
            'proxy_url': self.proxy_url,
            'viewport_size': self.viewport_size,
            'user_agent': self.user_agent,
            'timezone': self.timezone,
            'locale': self.locale,
            'stealth_level': self.stealth_level,
            'max_memory_mb': self.max_memory_mb,
            'enable_cache': self.enable_cache,
            'block_images': self.block_images,
            'block_media': self.block_media
        }


class BotasaurusEngine:
    """
    Core Botasaurus engine with enterprise-grade anti-detection and session management
    
    Features:
    - Advanced anti-detection with fingerprint randomization
    - Session isolation with profile management
    - Memory-optimized browser management
    - Automatic recovery and error handling
    - Performance monitoring and metrics
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize Botasaurus engine with secure configuration"""
        # Load secure configuration
        self.browser_config = get_browser_config()
        self.security_config = get_security_config()
        self.input_validator = InputValidator()
        
        self.config = config or self._generate_default_config()
        self.driver: Optional[Driver] = None
        self.session_data: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {
            'start_time': datetime.now(),
            'pages_visited': 0,
            'errors_encountered': 0,
            'memory_usage': 0,
            'detection_attempts': 0,
            'memory_cleanup_count': 0
        }
        self.profiles_dir = Path("./browser_profiles")
        self.profiles_dir.mkdir(exist_ok=True, mode=0o750)  # Secure permissions
        
        # Memory management
        self._cleanup_callbacks = []
        self._memory_threshold = self.security_config.max_retries * 512 * 1024 * 1024  # Dynamic threshold
        
        # Resource tracking for proper cleanup
        self._active_resources = weakref.WeakSet()
        self._cleanup_registered = False
        
    def _generate_default_config(self) -> SessionConfig:
        """Generate default session configuration with random values"""
        session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        return SessionConfig(
            session_id=session_id,
            profile_name=f"profile_{session_id}",
            viewport_size=random.choice([
                (1920, 1080), (1366, 768), (1440, 900),
                (1536, 864), (1600, 900), (1280, 720)
            ])
        )
    
    def _apply_stealth_config(self, driver: Driver) -> None:
        """Apply stealth configuration to bypass detection"""
        if self.config.stealth_level >= 1:
            # Basic stealth - hide automation indicators
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
        if self.config.stealth_level >= 2:
            # Moderate stealth - randomize browser properties
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => Math.floor(Math.random() * 8) + 2
                });
            """)
            
        if self.config.stealth_level >= 3:
            # Maximum stealth - advanced fingerprint spoofing
            driver.execute_script("""
                // Canvas fingerprint protection
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    const context = this.getContext('2d');
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = (imageData.data[i] + Math.random() * 2) | 0;
                    }
                    context.putImageData(imageData, 0, 0);
                    return originalToDataURL.apply(this, arguments);
                };
                
                // WebGL fingerprint protection
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
                
                // Audio fingerprint protection
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) {
                    AudioContext.prototype.__proto__.getChannelData = new Proxy(
                        AudioContext.prototype.__proto__.getChannelData,
                        {
                            apply(target, thisArg, args) {
                                const result = target.apply(thisArg, args);
                                for (let i = 0; i < result.length; i += 100) {
                                    result[i] = result[i] + Math.random() * 0.0001;
                                }
                                return result;
                            }
                        }
                    );
                }
            """)
    
    @browser(
        profile=lambda self: self.config.profile_name,
        headless=lambda self: self.browser_config.headless,
        block_images=lambda self: self.config.block_images or self.browser_config.disable_images,
        block_media=lambda self: self.config.block_media,
        window_size=lambda self: (self.browser_config.viewport_width, self.browser_config.viewport_height),
        user_agent=lambda self: self.config.user_agent,
        proxy=lambda self: self.security_config.proxy_url if self.security_config.enable_proxy else None,
        reuse_driver=True,
        max_retry=lambda self: self.security_config.max_retries
    )
    def create_driver(self, driver: Driver) -> Driver:
        """Create and configure Botasaurus driver with anti-detection"""
        self.driver = driver
        
        # Apply stealth configuration
        self._apply_stealth_config(driver)
        
        # Set viewport and window size
        driver.set_window_size(*self.config.viewport_size)
        
        # Configure timezone and locale
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
            'timezoneId': self.config.timezone
        })
        
        driver.execute_cdp_cmd('Emulation.setLocaleOverride', {
            'locale': self.config.locale
        })
        
        # Disable automation features
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        # Initialize performance monitoring
        self._init_performance_monitoring(driver)
        
        self.metrics['pages_visited'] += 1
        return driver
    
    def _init_performance_monitoring(self, driver: Driver) -> None:
        """Initialize performance monitoring for the driver"""
        try:
            # Enable performance metrics
            driver.execute_cdp_cmd('Performance.enable', {})
            
            # Monitor memory usage
            metrics = driver.execute_cdp_cmd('Performance.getMetrics', {})
            if metrics and 'metrics' in metrics:
                for metric in metrics['metrics']:
                    if metric['name'] == 'JSHeapUsedSize':
                        self.metrics['memory_usage'] = metric['value'] / (1024 * 1024)  # Convert to MB
        except Exception as e:
            print(f"Performance monitoring setup failed: {e}")
    
    def navigate_with_stealth(self, url: str, wait_time: int = 3) -> bool:
        """Navigate to URL with stealth behavior and secure validation"""
        # SECURITY FIX: Validate URL input
        if not self.input_validator.validate_url(url):
            raise ValueError(f"Invalid URL provided: {url}")
        
        # Sanitize URL
        clean_url = self.input_validator.sanitize_string(url, max_length=2048, allow_none=False)
        
        if not self.driver:
            self.driver = self.create_driver()
            
        try:
            # Rate limiting based on security config
            delay = self.security_config.rate_limit_delay
            time.sleep(random.uniform(delay * 0.5, delay * 1.5))
            
            # Navigate to URL with timeout
            self.driver.set_page_load_timeout(self.security_config.request_timeout)
            self.driver.get(clean_url)
            
            # Check memory usage and cleanup if needed
            self._check_memory_usage()
            
            # Random mouse movements to simulate human behavior
            self._simulate_human_behavior()
            
            # Wait for page load with security-configured delay
            time.sleep(random.uniform(wait_time, wait_time + 2))
            
            # Check for bot detection
            if self._check_bot_detection():
                self.metrics['detection_attempts'] += 1
                return False
                
            self.metrics['pages_visited'] += 1
            return True
            
        except Exception as e:
            self.metrics['errors_encountered'] += 1
            print(f"Navigation error: {e}")
            return False
    
    def _simulate_human_behavior(self) -> None:
        """Simulate human-like behavior patterns"""
        if not self.driver:
            return
            
        try:
            # Random scroll patterns
            scroll_actions = [
                lambda: self.driver.execute_script("window.scrollBy(0, 300)"),
                lambda: self.driver.execute_script("window.scrollBy(0, -200)"),
                lambda: self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3)"),
                lambda: self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7)")
            ]
            
            # Execute 2-4 random scroll actions
            for _ in range(random.randint(2, 4)):
                action = random.choice(scroll_actions)
                action()
                time.sleep(random.uniform(0.5, 1.5))
                
            # Random mouse movements (if supported)
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                
                # Move mouse to random positions
                for _ in range(random.randint(3, 6)):
                    x = random.randint(100, 800)
                    y = random.randint(100, 600)
                    actions.move_by_offset(x, y)
                    actions.perform()
                    time.sleep(random.uniform(0.1, 0.3))
            except:
                pass  # Mouse movements not critical
                
        except Exception as e:
            print(f"Human behavior simulation error: {e}")
    
    def _check_memory_usage(self) -> None:
        """Monitor memory usage and trigger cleanup if needed"""
        try:
            # Get current memory usage
            if self.driver:
                metrics = self.driver.execute_cdp_cmd('Performance.getMetrics', {})
                if metrics and 'metrics' in metrics:
                    for metric in metrics['metrics']:
                        if metric['name'] == 'JSHeapUsedSize':
                            current_memory = metric['value']
                            self.metrics['memory_usage'] = current_memory / (1024 * 1024)
                            
                            # Check if memory threshold exceeded
                            if current_memory > self._memory_threshold:
                                self._perform_memory_cleanup()
                                break
                
                # Also check for too many open handles/tabs
                if len(self.driver.window_handles) > 10:
                    self._cleanup_extra_windows()
                    
        except Exception as e:
            print(f"Memory usage check error: {e}")
    
    def _perform_memory_cleanup(self) -> None:
        """Perform memory cleanup operations"""
        try:
            if not self.driver:
                return
            
            # Clear browser caches
            self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            
            # Execute JavaScript garbage collection
            self.driver.execute_script("""
                if (window.gc) {
                    window.gc();
                }
                // Clear any large objects from memory
                window.collectedData = null;
                if (window.performance && window.performance.clearMarks) {
                    window.performance.clearMarks();
                    window.performance.clearMeasures();
                }
            """)
            
            # Force Python garbage collection
            gc.collect()
            
            self.metrics['memory_cleanup_count'] += 1
            print(f"Memory cleanup performed. Count: {self.metrics['memory_cleanup_count']}")
            
        except Exception as e:
            print(f"Memory cleanup error: {e}")
    
    def _cleanup_extra_windows(self) -> None:
        """Close extra browser windows to prevent memory leaks"""
        try:
            if not self.driver or len(self.driver.window_handles) <= 1:
                return
            
            main_window = self.driver.current_window_handle
            
            # Close all windows except the main one
            for handle in self.driver.window_handles:
                if handle != main_window:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
            
            # Switch back to main window
            self.driver.switch_to.window(main_window)
            print(f"Closed {len(self.driver.window_handles) - 1} extra windows")
            
        except Exception as e:
            print(f"Window cleanup error: {e}")
    
    def add_cleanup_callback(self, callback) -> None:
        """Register a callback to be executed during cleanup"""
        if callable(callback):
            self._cleanup_callbacks.append(callback)
    
    def _check_bot_detection(self) -> bool:
        """Check if bot detection mechanisms are triggered"""
        if not self.driver:
            return False
            
        try:
            # Check for common bot detection indicators
            indicators = [
                "captcha",
                "robot",
                "bot-detection",
                "access denied",
                "unusual activity",
                "security check",
                "cloudflare"
            ]
            
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            
            for indicator in indicators:
                if indicator in page_source or indicator in page_title:
                    print(f"Bot detection indicator found: {indicator}")
                    return True
                    
            # Check for Cloudflare challenge
            if "checking your browser" in page_source:
                print("Cloudflare challenge detected")
                return True
                
            return False
            
        except Exception as e:
            print(f"Bot detection check error: {e}")
            return False
    
    def extract_data(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from current page using CSS selectors"""
        if not self.driver:
            return {}
            
        extracted_data = {}
        
        for field_name, selector in selectors.items():
            try:
                elements = self.driver.find_elements_by_css_selector(selector)
                if elements:
                    if len(elements) == 1:
                        extracted_data[field_name] = elements[0].text.strip()
                    else:
                        extracted_data[field_name] = [elem.text.strip() for elem in elements]
                else:
                    extracted_data[field_name] = None
            except Exception as e:
                print(f"Error extracting {field_name}: {e}")
                extracted_data[field_name] = None
                
        return extracted_data
    
    def save_session(self) -> None:
        """Save current session data and cookies"""
        if not self.driver:
            return
            
        session_file = self.profiles_dir / f"{self.config.session_id}.json"
        
        try:
            session_data = {
                'config': self.config.to_dict(),
                'cookies': self.driver.get_cookies(),
                'local_storage': self.driver.execute_script("return window.localStorage"),
                'session_storage': self.driver.execute_script("return window.sessionStorage"),
                'metrics': self.metrics,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
                
            print(f"Session saved: {session_file}")
            
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def load_session(self, session_id: str) -> bool:
        """Load a previously saved session"""
        session_file = self.profiles_dir / f"{session_id}.json"
        
        if not session_file.exists():
            print(f"Session file not found: {session_file}")
            return False
            
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                
            # Restore configuration
            config_data = session_data['config']
            self.config = SessionConfig(**config_data)
            
            # Create driver if not exists
            if not self.driver:
                self.driver = self.create_driver()
                
            # Restore cookies
            for cookie in session_data.get('cookies', []):
                self.driver.add_cookie(cookie)
                
            # Restore local storage
            local_storage = session_data.get('local_storage', {})
            for key, value in local_storage.items():
                self.driver.execute_script(f"window.localStorage.setItem('{key}', '{value}')")
                
            # Restore metrics
            self.metrics = session_data.get('metrics', self.metrics)
            
            print(f"Session loaded: {session_id}")
            return True
            
        except Exception as e:
            print(f"Error loading session: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources and close browser with memory management"""
        try:
            # Execute cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"Cleanup callback error: {e}")
            
            if self.driver:
                try:
                    # Save session before closing
                    self.save_session()
                    
                    # Close all windows
                    for handle in self.driver.window_handles:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    
                    # Quit driver
                    self.driver.quit()
                    
                except Exception as e:
                    print(f"Driver cleanup error: {e}")
                finally:
                    self.driver = None
            
            # Clear caches and force garbage collection
            self.session_data.clear()
            self._active_resources.clear()
            gc.collect()
            self.metrics['memory_cleanup_count'] += 1
                
            # Log final metrics
            print(f"Session metrics: {json.dumps(self.metrics, indent=2)}")
            
        except Exception as e:
            print(f"Cleanup error: {e}")
        finally:
            # Ensure driver is None regardless of errors
            self.driver = None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current session metrics"""
        if self.driver:
            try:
                # Update memory usage
                metrics = self.driver.execute_cdp_cmd('Performance.getMetrics', {})
                if metrics and 'metrics' in metrics:
                    for metric in metrics['metrics']:
                        if metric['name'] == 'JSHeapUsedSize':
                            self.metrics['memory_usage'] = metric['value'] / (1024 * 1024)
            except:
                pass
                
        self.metrics['runtime_seconds'] = (datetime.now() - self.metrics['start_time']).total_seconds()
        return self.metrics


# Decorator for easy integration with existing code
def with_botasaurus(stealth_level: int = 3, **kwargs):
    """Decorator to wrap functions with Botasaurus engine"""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            config = SessionConfig(
                session_id=f"wrapped_{func.__name__}_{int(time.time())}",
                profile_name=f"profile_{func.__name__}",
                stealth_level=stealth_level,
                **kwargs
            )
            engine = BotasaurusEngine(config)
            
            try:
                # Pass engine to function
                result = func(engine, *args, **func_kwargs)
                return result
            finally:
                engine.cleanup()
                
        return wrapper
    return decorator


# Example usage function
@with_botasaurus(stealth_level=3, block_images=True)
def example_scraper(engine: BotasaurusEngine, url: str) -> Dict[str, Any]:
    """Example scraper using Botasaurus engine"""
    # Navigate to URL
    if engine.navigate_with_stealth(url):
        # Extract data
        data = engine.extract_data({
            'title': 'h1',
            'description': 'p',
            'links': 'a'
        })
        return data
    return {}


if __name__ == "__main__":
    # Test the engine
    print("Botasaurus Engine v1.0 initialized")
    print("Core integration complete with anti-detection and session management")
    
    # Create test configuration
    test_config = SessionConfig(
        session_id="test_session",
        profile_name="test_profile",
        stealth_level=3
    )
    
    # Initialize engine
    engine = BotasaurusEngine(test_config)
    print(f"Engine created with config: {test_config.to_dict()}")
    
    # Get metrics
    print(f"Initial metrics: {engine.get_metrics()}")
    
    # Cleanup
    engine.cleanup()