"""
CAPTCHA Detection and Handling for Bing Scraper
Detects various types of CAPTCHA challenges and implements handling strategies.
"""

import time
import random
import logging
from typing import Optional, Dict, Any, List, Tuple
import re

logger = logging.getLogger(__name__)

class CaptchaHandler:
    """Handles CAPTCHA detection and response strategies."""
    
    def __init__(self, settings):
        """Initialize CAPTCHA handler with settings."""
        self.settings = settings
        self.captcha_indicators = self._load_captcha_indicators()
        self.handling_strategies = self._load_handling_strategies()
        
        logger.info("CaptchaHandler initialized")
    
    def _load_captcha_indicators(self) -> Dict[str, List[str]]:
        """Load CAPTCHA detection patterns."""
        return {
            'text_indicators': [
                'captcha',
                'verify you are human',
                'prove you are not a robot',
                'i\'m not a robot',
                'recaptcha',
                'hcaptcha',
                'cloudflare',
                'bot detection',
                'suspicious activity',
                'automated traffic',
                'verify your identity',
                'security check',
                'access denied',
                'blocked',
                'rate limit',
                'too many requests',
                'unusual traffic',
                'solve the puzzle',
                'complete the challenge',
                'verify to continue',
            ],
            
            'url_indicators': [
                'captcha',
                'challenge',
                'verify',
                'blocked',
                'security',
                'robot',
                'bot-check',
                'cloudflare.com',
                'recaptcha',
                'hcaptcha',
            ],
            
            'element_selectors': [
                # reCAPTCHA
                '.g-recaptcha',
                '#g-recaptcha',
                'iframe[src*="recaptcha"]',
                '[data-sitekey]',
                
                # hCAPTCHA
                '.h-captcha',
                '#h-captcha',
                'iframe[src*="hcaptcha"]',
                
                # Cloudflare
                '.cf-challenge',
                '#cf-challenge',
                '.cf-browser-verification',
                
                # Generic CAPTCHA elements
                'input[name*="captcha"]',
                'img[alt*="captcha"]',
                'img[src*="captcha"]',
                '.captcha',
                '#captcha',
                
                # Bot detection messages
                '.bot-detection',
                '.security-check',
                '.verify-human',
                
                # Bing-specific
                '.b_captcha',
                '#b_captcha',
                '[data-module="captcha"]',
            ],
            
            'title_indicators': [
                'captcha',
                'verification',
                'access denied',
                'blocked',
                'security check',
                'bot detection',
                'cloudflare',
                'please verify',
                'prove you are human',
            ]
        }
    
    def _load_handling_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load CAPTCHA handling strategies."""
        return {
            'cloudflare_challenge': {
                'wait_time_range': (5, 15),
                'retry_attempts': 3,
                'indicators': ['cloudflare', 'checking your browser', 'ddos protection'],
                'auto_solvable': True,
            },
            
            'recaptcha_v2': {
                'wait_time_range': (30, 120),
                'retry_attempts': 1,
                'indicators': ['recaptcha', 'i\'m not a robot'],
                'auto_solvable': False,
            },
            
            'recaptcha_v3': {
                'wait_time_range': (3, 8),
                'retry_attempts': 2,
                'indicators': ['recaptcha', 'score'],
                'auto_solvable': True,
            },
            
            'hcaptcha': {
                'wait_time_range': (30, 120),
                'retry_attempts': 1,
                'indicators': ['hcaptcha', 'solve the puzzle'],
                'auto_solvable': False,
            },
            
            'simple_challenge': {
                'wait_time_range': (2, 8),
                'retry_attempts': 3,
                'indicators': ['verify', 'security check', 'bot'],
                'auto_solvable': True,
            },
            
            'rate_limit': {
                'wait_time_range': (60, 300),
                'retry_attempts': 2,
                'indicators': ['rate limit', 'too many requests', 'slow down'],
                'auto_solvable': True,
            }
        }
    
    def detect_captcha(self, driver, page_source: str = None, current_url: str = None) -> Optional[Dict[str, Any]]:
        """
        Detect if page contains CAPTCHA or blocking challenge.
        
        Args:
            driver: Botasaurus driver instance
            page_source: Page HTML source (optional)
            current_url: Current page URL (optional)
            
        Returns:
            CAPTCHA detection result or None if no CAPTCHA detected
        """
        try:
            if page_source is None:
                page_source = driver.page_html
            
            if current_url is None:
                current_url = driver.current_url
            
            # Get page title
            try:
                page_title = driver.title.lower() if driver.title else ""
            except:
                page_title = ""
            
            detection_result = {
                'detected': False,
                'type': None,
                'confidence': 0.0,
                'indicators': [],
                'elements_found': [],
                'suggested_action': None,
            }
            
            # Check text indicators
            page_lower = page_source.lower()
            text_matches = []
            for indicator in self.captcha_indicators['text_indicators']:
                if indicator in page_lower:
                    text_matches.append(indicator)
            
            # Check URL indicators
            url_matches = []
            if current_url:
                url_lower = current_url.lower()
                for indicator in self.captcha_indicators['url_indicators']:
                    if indicator in url_lower:
                        url_matches.append(indicator)
            
            # Check title indicators
            title_matches = []
            for indicator in self.captcha_indicators['title_indicators']:
                if indicator in page_title:
                    title_matches.append(indicator)
            
            # Check for CAPTCHA elements
            element_matches = []
            for selector in self.captcha_indicators['element_selectors']:
                try:
                    elements = driver.select_all(selector)
                    if elements:
                        element_matches.append(selector)
                except:
                    pass
            
            # Calculate confidence and determine type
            total_indicators = len(text_matches) + len(url_matches) + len(title_matches) + len(element_matches)
            
            if total_indicators > 0:
                detection_result['detected'] = True
                detection_result['indicators'] = text_matches + url_matches + title_matches
                detection_result['elements_found'] = element_matches
                
                # Determine CAPTCHA type and confidence
                captcha_type, confidence = self._classify_captcha_type(
                    text_matches, url_matches, title_matches, element_matches, page_source
                )
                
                detection_result['type'] = captcha_type
                detection_result['confidence'] = confidence
                detection_result['suggested_action'] = self._get_suggested_action(captcha_type)
                
                logger.warning(f"CAPTCHA detected: {captcha_type} (confidence: {confidence:.2f})")
                logger.debug(f"Indicators: {detection_result['indicators']}")
                
            return detection_result if detection_result['detected'] else None
            
        except Exception as e:
            logger.error(f"Error during CAPTCHA detection: {e}")
            return None
    
    def _classify_captcha_type(self, text_matches: List[str], url_matches: List[str], 
                              title_matches: List[str], element_matches: List[str], 
                              page_source: str) -> Tuple[str, float]:
        """Classify the type of CAPTCHA based on indicators."""
        
        all_indicators = text_matches + url_matches + title_matches
        all_text = ' '.join(all_indicators).lower()
        
        # Cloudflare Detection
        if any('cloudflare' in indicator for indicator in all_indicators) or \
           any('cf-' in element for element in element_matches):
            confidence = 0.9 if 'checking your browser' in page_source.lower() else 0.7
            return 'cloudflare_challenge', confidence
        
        # reCAPTCHA Detection
        if any('recaptcha' in indicator for indicator in all_indicators) or \
           any('recaptcha' in element for element in element_matches):
            if 'i\'m not a robot' in all_text:
                return 'recaptcha_v2', 0.9
            else:
                return 'recaptcha_v3', 0.7
        
        # hCAPTCHA Detection
        if any('hcaptcha' in indicator for indicator in all_indicators) or \
           any('hcaptcha' in element for element in element_matches):
            return 'hcaptcha', 0.9
        
        # Rate Limiting
        if any(term in all_text for term in ['rate limit', 'too many requests', 'slow down']):
            return 'rate_limit', 0.8
        
        # Generic bot detection
        if any(term in all_text for term in ['bot', 'robot', 'automated']):
            return 'simple_challenge', 0.6
        
        # Blocking/Access Denied
        if any(term in all_text for term in ['blocked', 'access denied', 'suspicious']):
            return 'simple_challenge', 0.7
        
        # Default to simple challenge
        return 'simple_challenge', 0.5
    
    def _get_suggested_action(self, captcha_type: str) -> str:
        """Get suggested action for CAPTCHA type."""
        strategy = self.handling_strategies.get(captcha_type, {})
        
        if strategy.get('auto_solvable', False):
            return 'wait_and_retry'
        else:
            return 'rotate_session'
    
    def handle_captcha(self, driver, captcha_info: Dict[str, Any]) -> bool:
        """
        Handle detected CAPTCHA challenge.
        
        Args:
            driver: Botasaurus driver instance
            captcha_info: CAPTCHA detection information
            
        Returns:
            True if handling was successful, False otherwise
        """
        captcha_type = captcha_info.get('type', 'simple_challenge')
        strategy = self.handling_strategies.get(captcha_type, self.handling_strategies['simple_challenge'])
        
        logger.info(f"Handling CAPTCHA: {captcha_type}")
        
        try:
            if strategy.get('auto_solvable', False):
                return self._handle_auto_solvable_captcha(driver, captcha_type, strategy)
            else:
                return self._handle_manual_captcha(driver, captcha_type, strategy)
                
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return False
    
    def _handle_auto_solvable_captcha(self, driver, captcha_type: str, strategy: Dict[str, Any]) -> bool:
        """Handle CAPTCHAs that can be automatically solved."""
        
        if captcha_type == 'cloudflare_challenge':
            return self._handle_cloudflare_challenge(driver, strategy)
        elif captcha_type == 'recaptcha_v3':
            return self._handle_recaptcha_v3(driver, strategy)
        elif captcha_type == 'rate_limit':
            return self._handle_rate_limit(driver, strategy)
        else:
            return self._handle_generic_wait(driver, strategy)
    
    def _handle_manual_captcha(self, driver, captcha_type: str, strategy: Dict[str, Any]) -> bool:
        """Handle CAPTCHAs that require manual intervention."""
        logger.warning(f"Manual CAPTCHA detected: {captcha_type}")
        
        # For manual CAPTCHAs, we can't solve them automatically
        # Best strategy is to wait a bit and then rotate session
        wait_time = random.uniform(*strategy['wait_time_range'])
        logger.info(f"Waiting {wait_time:.1f}s before session rotation")
        time.sleep(wait_time)
        
        return False  # Indicates need for session rotation
    
    def _handle_cloudflare_challenge(self, driver, strategy: Dict[str, Any]) -> bool:
        """Handle Cloudflare challenge (usually auto-solves)."""
        logger.info("Handling Cloudflare challenge")
        
        # Cloudflare challenges usually solve themselves
        # We just need to wait for the redirect
        max_wait = strategy['wait_time_range'][1]
        check_interval = 2
        
        for i in range(0, max_wait, check_interval):
            time.sleep(check_interval)
            
            try:
                # Check if we're still on challenge page
                current_url = driver.current_url
                page_source = driver.page_html.lower()
                
                # Check for signs that challenge is complete
                if 'cloudflare' not in current_url.lower() and \
                   'checking your browser' not in page_source:
                    logger.info("Cloudflare challenge appears to be resolved")
                    return True
                    
            except Exception as e:
                logger.debug(f"Error checking Cloudflare status: {e}")
        
        logger.warning("Cloudflare challenge did not resolve automatically")
        return False
    
    def _handle_recaptcha_v3(self, driver, strategy: Dict[str, Any]) -> bool:
        """Handle reCAPTCHA v3 (invisible, usually auto-solves)."""
        logger.info("Handling reCAPTCHA v3")
        
        # reCAPTCHA v3 runs in background and usually resolves automatically
        wait_time = random.uniform(*strategy['wait_time_range'])
        logger.info(f"Waiting {wait_time:.1f}s for reCAPTCHA v3 to process")
        time.sleep(wait_time)
        
        # Check if page has changed/progressed
        try:
            page_source = driver.page_html.lower()
            if 'recaptcha' not in page_source or 'captcha' not in page_source:
                logger.info("reCAPTCHA v3 appears to be resolved")
                return True
        except Exception as e:
            logger.debug(f"Error checking reCAPTCHA v3 status: {e}")
        
        return False
    
    def _handle_rate_limit(self, driver, strategy: Dict[str, Any]) -> bool:
        """Handle rate limiting."""
        logger.info("Handling rate limit")
        
        # For rate limits, we need to wait longer
        wait_time = random.uniform(*strategy['wait_time_range'])
        logger.info(f"Rate limited - waiting {wait_time:.1f}s")
        time.sleep(wait_time)
        
        # Try refreshing the page
        try:
            driver.refresh()
            time.sleep(3)
            
            # Check if rate limit is gone
            page_source = driver.page_html.lower()
            if not any(indicator in page_source for indicator in ['rate limit', 'too many requests']):
                logger.info("Rate limit appears to be resolved")
                return True
                
        except Exception as e:
            logger.debug(f"Error refreshing page after rate limit: {e}")
        
        return False
    
    def _handle_generic_wait(self, driver, strategy: Dict[str, Any]) -> bool:
        """Handle generic challenges with wait strategy."""
        logger.info("Handling generic challenge")
        
        wait_time = random.uniform(*strategy['wait_time_range'])
        logger.info(f"Waiting {wait_time:.1f}s for challenge to resolve")
        time.sleep(wait_time)
        
        # Try simple page interactions
        try:
            # Scroll a bit
            driver.run_js("window.scrollBy(0, 100);")
            time.sleep(1)
            
            # Move mouse
            driver.run_js("""
                var event = new MouseEvent('mousemove', {
                    clientX: 500,
                    clientY: 300,
                    bubbles: true
                });
                document.dispatchEvent(event);
            """)
            time.sleep(1)
            
            # Check if challenge is resolved
            captcha_detection = self.detect_captcha(driver)
            if not captcha_detection:
                logger.info("Generic challenge appears to be resolved")
                return True
                
        except Exception as e:
            logger.debug(f"Error during generic challenge handling: {e}")
        
        return False
    
    def is_captcha_page(self, driver) -> bool:
        """Quick check if current page is a CAPTCHA page."""
        try:
            captcha_info = self.detect_captcha(driver)
            return captcha_info is not None
        except:
            return False
    
    def get_captcha_statistics(self) -> Dict[str, Any]:
        """Get statistics about CAPTCHA handling."""
        return {
            'total_indicators': sum(len(indicators) for indicators in self.captcha_indicators.values()),
            'supported_types': list(self.handling_strategies.keys()),
            'auto_solvable_types': [
                captcha_type for captcha_type, strategy in self.handling_strategies.items()
                if strategy.get('auto_solvable', False)
            ]
        }