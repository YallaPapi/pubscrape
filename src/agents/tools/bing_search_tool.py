"""
Bing Search Tool for Agency Swarm

Tool for executing individual search queries on Bing with comprehensive
anti-detection, rate limiting, and error handling capabilities.
"""

import logging
import time
import uuid
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

from agency_swarm.tools import BaseTool
from pydantic import Field

# Optional import for Botasaurus - will work in mock mode if not available
try:
    from botasaurus.browser import browser
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    browser = None

# Import project infrastructure
try:
    from infra.rate_limiter import RateLimiter, RateLimitStatus
    from infra.anti_detection_supervisor import AntiDetectionSupervisor
    from infra.delay_manager import ActionType
except ImportError as e:
    logging.warning(f"Could not import infrastructure components: {e}")
    # Fallback imports for development
    RateLimiter = None
    AntiDetectionSupervisor = None
    ActionType = None

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result of a Bing search operation"""
    query: str
    url: str
    page_number: int
    success: bool
    html_file_path: Optional[str] = None
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: float = None
    session_id: Optional[str] = None
    proxy_used: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BingSearchTool(BaseTool):
    """
    Tool for executing Bing search queries with anti-detection and rate limiting.
    
    This tool handles:
    - Botasaurus browser session management
    - Human-like interaction patterns
    - Rate limiting integration
    - Block signal detection and handling
    - Raw HTML storage
    - Comprehensive error handling and logging
    """
    
    query: str = Field(
        ...,
        description="Search query to execute on Bing"
    )
    
    max_pages: int = Field(
        default=1,
        description="Maximum number of pages to retrieve (1-10)",
        ge=1,
        le=10
    )
    
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for session reuse"
    )
    
    proxy_preference: Optional[str] = Field(
        default=None,
        description="Optional proxy preference (residential, datacenter, none)"
    )
    
    store_html: bool = Field(
        default=True,
        description="Whether to store raw HTML responses"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize components as private attributes
        self._rate_limiter = None
        self._anti_detection = None
        self._output_dir = Path("out/html_cache")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize infrastructure if available
        self._initialize_infrastructure()
    
    def _initialize_infrastructure(self):
        """Initialize rate limiting and anti-detection components"""
        try:
            if RateLimiter:
                self._rate_limiter = RateLimiter()
                logger.info("Rate limiter initialized")
            
            if AntiDetectionSupervisor:
                self._anti_detection = AntiDetectionSupervisor()
                logger.info("Anti-detection supervisor initialized")
                
        except Exception as e:
            logger.warning(f"Could not initialize infrastructure: {e}")
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the Bing search with comprehensive error handling.
        
        Returns:
            Dictionary containing search results and metadata
        """
        start_time = time.time()
        results = []
        session_id = self.session_id or f"bing_search_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Starting Bing search for query: '{self.query}' "
                   f"(max_pages: {self.max_pages}, session: {session_id})")
        
        try:
            # Check rate limits before starting
            if self._rate_limiter:
                status, delay = self._rate_limiter.check_rate_limit("bing.com", session_id)
                if status != RateLimitStatus.ALLOWED:
                    return self._create_error_result(
                        f"Rate limited: {status.value}, delay: {delay}s",
                        session_id
                    )
            
            # Execute search with Botasaurus
            search_results = self._execute_search_with_botasaurus(session_id)
            results.extend(search_results)
            
            # Calculate statistics
            successful_pages = len([r for r in results if r.success])
            total_time = time.time() - start_time
            
            # Record results with rate limiter
            if self._rate_limiter:
                for result in results:
                    self._rate_limiter.record_request(
                        domain="bing.com",
                        success=result.success,
                        response_time_ms=result.response_time_ms,
                        status_code=result.status_code,
                        error_type=result.error_message if not result.success else None
                    )
            
            logger.info(f"Bing search completed: {successful_pages}/{len(results)} pages successful "
                       f"in {total_time:.2f}s")
            
            return {
                "success": successful_pages > 0,
                "query": self.query,
                "session_id": session_id,
                "pages_retrieved": successful_pages,
                "total_pages_attempted": len(results),
                "total_time_seconds": total_time,
                "results": [asdict(r) for r in results],
                "html_files": [r.html_file_path for r in results if r.html_file_path],
                "summary": {
                    "success_rate": successful_pages / len(results) if results else 0,
                    "avg_response_time_ms": sum(r.response_time_ms for r in results 
                                               if r.response_time_ms) / successful_pages if successful_pages > 0 else None,
                    "errors_encountered": [r.error_message for r in results if not r.success]
                }
            }
            
        except Exception as e:
            logger.error(f"Bing search failed for query '{self.query}': {str(e)}")
            return self._create_error_result(str(e), session_id)
    
    def _execute_search_with_botasaurus(self, session_id: str) -> List[SearchResult]:
        """Execute search using Botasaurus browser automation"""
        results = []
        
        # Check if Botasaurus is available
        if not BOTASAURUS_AVAILABLE:
            logger.warning("Botasaurus not available, using mock implementation")
            return self._execute_mock_search(session_id)
        
        try:
            # Configure Botasaurus browser options
            browser_options = self._get_botasaurus_options(session_id)
            
            @browser(**browser_options)
            def search_bing(driver, data):
                """Botasaurus function to search Bing"""
                page_results = []
                query = data['query']
                max_pages = data['max_pages']
                session_id = data['session_id']
                
                try:
                    # Enhanced navigation with human behavior simulation
                    
                    # First, visit Bing homepage to establish session
                    logger.debug("Establishing session on Bing homepage")
                    driver.get("https://www.bing.com")
                    
                    # Simulate human session start behavior
                    try:
                        from bing_scraper.src.anti_detection.delays import HumanLikeDelays
                        from bing_scraper.src.anti_detection.captcha_handler import CaptchaHandler
                        
                        delays = HumanLikeDelays(type('Settings', (), {
                            'base_delay_seconds': 3.0
                        })())
                        
                        captcha_handler = CaptchaHandler(type('Settings', (), {})())
                        
                        # Simulate human session start
                        delays.simulate_human_session_start(driver)
                        
                        # Check for CAPTCHA on homepage
                        captcha_info = captcha_handler.detect_captcha(driver)
                        if captcha_info:
                            logger.warning(f"CAPTCHA detected on homepage: {captcha_info['type']}")
                            if not captcha_handler.handle_captcha(driver, captcha_info):
                                # CAPTCHA couldn't be handled, need session rotation
                                raise Exception("CAPTCHA challenge could not be resolved")
                        
                        # Navigate to search with query (more human-like)
                        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
                        logger.debug(f"Navigating to search URL: {search_url}")
                        
                        # Simulate search behavior
                        delays.simulate_search_behavior(driver, query)
                        
                        # Navigate to search results
                        driver.get(search_url)
                        
                        # Execute stealth JavaScript to mask automation
                        self._execute_stealth_scripts(driver)
                        
                        # Wait with human-like delays
                        delays.page_load_delay()
                        
                        # Check for CAPTCHA on search results
                        captcha_info = captcha_handler.detect_captcha(driver)
                        if captcha_info:
                            logger.warning(f"CAPTCHA detected on search results: {captcha_info['type']}")
                            if not captcha_handler.handle_captcha(driver, captcha_info):
                                raise Exception("Search blocked by CAPTCHA")
                        
                    except ImportError:
                        # Fallback if anti-detection modules not available
                        logger.warning("Anti-detection modules not available, using basic delays")
                        driver.sleep(5)
                    
                    # Process each page
                    for page_num in range(1, max_pages + 1):
                        page_result = self._process_search_page(
                            driver, query, page_num, session_id
                        )
                        page_results.append(page_result)
                        
                        # Check for blocking signals
                        if not page_result.success:
                            if self._is_blocking_signal(page_result):
                                logger.warning(f"Blocking signal detected on page {page_num}, stopping")
                                break
                        
                        # Navigate to next page if not the last
                        if page_num < max_pages:
                            if not self._navigate_to_next_page(driver):
                                logger.info(f"No more pages available after page {page_num}")
                                break
                            
                            # Human-like delay between page navigations
                            self._human_delay(driver, "pagination")
                
                except Exception as e:
                    logger.error(f"Error during Bing search: {str(e)}")
                    # Create error result for current attempt
                    error_result = SearchResult(
                        query=query,
                        url=driver.current_url if 'driver' in locals() else "unknown",
                        page_number=1,
                        success=False,
                        error_message=str(e),
                        session_id=session_id
                    )
                    page_results.append(error_result)
                
                return [asdict(result) for result in page_results]
            
            # Execute the search
            search_data = {
                'query': self.query,
                'max_pages': self.max_pages,
                'session_id': session_id
            }
            
            result_dicts = search_bing(data=search_data)
            
            # Convert back to SearchResult objects
            results = []
            for result_dict in result_dicts:
                results.append(SearchResult(**result_dict))
            
        except Exception as e:
            logger.error(f"Botasaurus execution failed: {str(e)}")
            error_result = SearchResult(
                query=self.query,
                url="unknown",
                page_number=1,
                success=False,
                error_message=f"Botasaurus execution failed: {str(e)}",
                session_id=session_id
            )
            results = [error_result]
        
        return results
    
    def _execute_mock_search(self, session_id: str) -> List[SearchResult]:
        """Mock search implementation when Botasaurus is not available"""
        results = []
        
        for page_num in range(1, self.max_pages + 1):
            start_time = time.time()
            
            # Simulate network delay
            time.sleep(0.5)
            
            # Create mock result
            result = SearchResult(
                query=self.query,
                url=f"https://www.bing.com/search?q={self.query.replace(' ', '+')}&first={page_num*10-9}",
                page_number=page_num,
                success=True,
                response_time_ms=(time.time() - start_time) * 1000,
                session_id=session_id
            )
            
            # Mock HTML storage
            if self.store_html:
                result.html_file_path = self._store_mock_html(self.query, page_num, session_id)
            
            results.append(result)
        
        return results
    
    def _store_mock_html(self, query: str, page_num: int, session_id: str) -> str:
        """Store mock HTML content"""
        try:
            timestamp = int(time.time())
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_query = safe_query.replace(' ', '_')[:50]
            
            filename = f"bing_{safe_query}_p{page_num}_{session_id}_{timestamp}.html"
            file_path = self._output_dir / filename
            
            mock_html = f"""<!DOCTYPE html>
<html>
<head><title>Mock Bing Search Results for: {query}</title></head>
<body>
<h1>Mock Search Results for: {query}</h1>
<p>Page {page_num}</p>
<p>Session: {session_id}</p>
<p>Generated at: {time.ctime()}</p>
<div id="b_results">
    <div class="b_algo">
        <h2><a href="https://example.com/result1">Mock Result 1</a></h2>
        <p>This is a mock search result for testing purposes.</p>
    </div>
    <div class="b_algo">
        <h2><a href="https://example.com/result2">Mock Result 2</a></h2>
        <p>Another mock search result for testing.</p>
    </div>
</div>
</body>
</html>"""
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(mock_html)
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to store mock HTML: {e}")
            return None
    
    def _get_botasaurus_options(self, session_id: str) -> Dict[str, Any]:
        """Get advanced Botasaurus browser configuration with enhanced stealth."""
        
        # Simplified anti-detection options for Botasaurus
        options = {
            # Core browser settings
            'headless': False,  # Visible browser appears more human
            'profile': f"bing_session_{session_id}",
            'wait_for_complete_page_load': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        # Add proxy configuration if available and preferred
        if self.proxy_preference != "none" and self._anti_detection:
            try:
                # Enhanced anti-detection with session management
                from bing_scraper.src.anti_detection.manager import AntiDetectionManager
                anti_detection = AntiDetectionManager(type('Settings', (), {
                    'headless_mode': False,
                    'user_agent_rotation': True,
                    'proxy_enabled': True,
                    'block_images': False,
                    'block_css': False,
                    'block_js': False,
                    'base_delay_seconds': 3.0
                })())
                
                config = anti_detection.get_browser_config(session_id)
                
                # Update options with anti-detection config
                if config.get('user_agent'):
                    options['user_agent'] = config['user_agent']
                if config.get('window_size'):
                    options['window_size'] = config['window_size']
                if config.get('proxy'):
                    options['proxy'] = config['proxy']
                    
                logger.debug(f"Applied enhanced anti-detection config")
                
            except Exception as e:
                logger.warning(f"Could not apply enhanced anti-detection: {e}")
        
        logger.debug(f"Enhanced Botasaurus options configured for session {session_id}")
        return options
    
    def _execute_stealth_scripts(self, driver):
        """Execute JavaScript to enhance stealth and mask automation."""
        try:
            # Remove webdriver traces
            driver.run_js("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # Override automation detection
            driver.run_js("""
                window.chrome = {
                    runtime: {}
                };
            """)
            
            # Override permissions API
            driver.run_js("""
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Override plugins
            driver.run_js("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            # Override languages
            driver.run_js("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            # Set realistic screen properties
            driver.run_js("""
                Object.defineProperty(screen, 'width', {
                    get: () => 1920,
                });
                Object.defineProperty(screen, 'height', {
                    get: () => 1080,
                });
                Object.defineProperty(screen, 'colorDepth', {
                    get: () => 24,
                });
            """)
            
            logger.debug("Stealth scripts executed successfully")
            
        except Exception as e:
            logger.warning(f"Failed to execute stealth scripts: {e}")
    
    def _process_search_page(self, driver, query: str, page_num: int, session_id: str) -> SearchResult:
        """Process a single search results page with enhanced human behavior"""
        start_time = time.time()
        
        try:
            # Wait for search results to load with human-like behavior
            self._wait_for_search_results(driver)
            
            # Simulate human reading behavior on search results
            try:
                from bing_scraper.src.anti_detection.delays import HumanLikeDelays
                from bing_scraper.src.anti_detection.captcha_handler import CaptchaHandler
                
                delays = HumanLikeDelays(type('Settings', (), {
                    'base_delay_seconds': 3.0
                })())
                
                captcha_handler = CaptchaHandler(type('Settings', (), {})())
                
                # Simulate reading search results
                delays.simulate_reading_behavior(driver, 'search_results')
                
                # Random mouse movements and scrolling
                if random.random() < 0.7:  # 70% chance
                    delays.simulate_mouse_movements(driver, random.randint(2, 4))
                
                if random.random() < 0.5:  # 50% chance  
                    delays.simulate_scrolling(driver, 'scanning')
                
            except ImportError:
                # Fallback without anti-detection
                time.sleep(random.uniform(2.0, 5.0))
            
            # Get current URL and response details
            current_url = driver.current_url
            page_source = driver.page_html
            
            # Enhanced blocking signal detection
            blocking_detected = False
            
            # Check for CAPTCHA first
            try:
                from bing_scraper.src.anti_detection.captcha_handler import CaptchaHandler
                captcha_handler = CaptchaHandler(type('Settings', (), {})())
                captcha_info = captcha_handler.detect_captcha(driver, page_source, current_url)
                
                if captcha_info:
                    logger.warning(f"CAPTCHA detected during page processing: {captcha_info['type']}")
                    blocking_detected = True
                    error_message = f"CAPTCHA challenge detected: {captcha_info['type']}"
                    
                    # Try to handle CAPTCHA
                    if captcha_handler.handle_captcha(driver, captcha_info):
                        logger.info("CAPTCHA resolved, continuing...")
                        blocking_detected = False
                        # Re-get page content after CAPTCHA resolution
                        page_source = driver.page_html
                        current_url = driver.current_url
                    else:
                        error_message = f"CAPTCHA challenge could not be resolved: {captcha_info['type']}"
                        
            except ImportError:
                # Fallback to basic blocking detection
                if self._detect_blocking_signals(page_source, current_url):
                    blocking_detected = True
                    error_message = "Blocking signal detected in page content"
            
            if blocking_detected:
                return SearchResult(
                    query=query,
                    url=current_url,
                    page_number=page_num,
                    success=False,
                    error_message=error_message,
                    response_time_ms=(time.time() - start_time) * 1000,
                    session_id=session_id
                )
            
            # Store HTML if requested
            html_file_path = None
            if self.store_html:
                html_file_path = self._store_html(page_source, query, page_num, session_id)
            
            response_time = (time.time() - start_time) * 1000
            
            result = SearchResult(
                query=query,
                url=current_url,
                page_number=page_num,
                success=True,
                html_file_path=html_file_path,
                response_time_ms=response_time,
                status_code=200,  # Assume success if we got page source
                session_id=session_id
            )
            
            logger.debug(f"Successfully processed page {page_num} in {response_time:.1f}ms")
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Error processing page {page_num}: {str(e)}")
            
            return SearchResult(
                query=query,
                url=driver.current_url if hasattr(driver, 'current_url') else "unknown",
                page_number=page_num,
                success=False,
                error_message=str(e),
                response_time_ms=response_time,
                session_id=session_id
            )
    
    def _wait_for_search_results(self, driver, timeout: int = 10):
        """Wait for search results to load"""
        try:
            # Wait for main search results container using correct API
            driver.wait_for_element("#b_results", timeout)
            
            # Additional human-like delay
            self._human_delay(driver, "extraction")
            
        except Exception as e:
            logger.warning(f"Timeout waiting for search results: {e}")
            # Continue anyway - page might have loaded differently
    
    def _navigate_to_next_page(self, driver) -> bool:
        """Navigate to the next page of results"""
        try:
            # Look for "Next" button/link
            next_selectors = [
                "a[aria-label*='Next']",
                "a[title*='Next']", 
                ".sb_pagN",
                "#ns a[aria-label*='page']"
            ]
            
            next_link_found = False
            for selector in next_selectors:
                try:
                    if driver.is_element_present(selector):
                        # Human-like delay before clicking
                        self._human_delay(driver, "navigation")
                        
                        # Click next page
                        driver.click(selector)
                        next_link_found = True
                        break
                except:
                    continue
            
            if not next_link_found:
                return False
            
            # Wait for new page to load
            self._wait_for_search_results(driver)
            
            return True
            
        except Exception as e:
            logger.debug(f"Could not navigate to next page: {e}")
            return False
    
    def _detect_blocking_signals(self, page_source: str, url: str) -> bool:
        """Detect if page contains blocking signals"""
        blocking_indicators = [
            "captcha",
            "blocked",
            "too many requests",
            "rate limit",
            "access denied",
            "suspicious activity",
            "verify you are human",
            "robot",
            "automation"
        ]
        
        page_source_lower = page_source.lower()
        url_lower = url.lower()
        
        # Check page content
        for indicator in blocking_indicators:
            if indicator in page_source_lower:
                logger.warning(f"Blocking signal detected: '{indicator}' in page content")
                return True
        
        # Check URL for blocking patterns
        blocking_url_patterns = [
            "captcha",
            "blocked",
            "error",
            "denied"
        ]
        
        for pattern in blocking_url_patterns:
            if pattern in url_lower:
                logger.warning(f"Blocking signal detected: '{pattern}' in URL")
                return True
        
        return False
    
    def _is_blocking_signal(self, result: SearchResult) -> bool:
        """Check if a search result indicates blocking"""
        if not result.success:
            blocking_errors = [
                "captcha",
                "blocked",
                "403",
                "429",
                "rate limit",
                "too many requests"
            ]
            
            error_msg = (result.error_message or "").lower()
            for error in blocking_errors:
                if error in error_msg:
                    return True
        
        return False
    
    def _store_html(self, html_content: str, query: str, page_num: int, session_id: str) -> str:
        """Store HTML content to file"""
        try:
            # Create filename with timestamp and metadata
            timestamp = int(time.time())
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_query = safe_query.replace(' ', '_')[:50]  # Limit length
            
            filename = f"bing_{safe_query}_p{page_num}_{session_id}_{timestamp}.html"
            file_path = self._output_dir / filename
            
            # Write HTML content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.debug(f"Stored HTML to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to store HTML: {e}")
            return None
    
    def _human_delay(self, driver, action_type: str):
        """Apply human-like delay"""
        if self._anti_detection and ActionType:
            try:
                action_enum = getattr(ActionType, action_type.upper(), ActionType.NAVIGATION)
                self._anti_detection.delay_for_action("dummy_session", action_enum)
            except:
                # Fallback to simple delay
                time.sleep(1.0 + (time.time() % 1.0))  # 1-2 seconds
        else:
            # Simple fallback delay
            import random
            time.sleep(random.uniform(1.0, 3.0))
    
    def _human_type(self, driver, selector: str, text: str):
        """Type text with human-like timing"""
        import random
        
        for char in text:
            driver.type(selector, char)
            # Random short delay between keystrokes
            time.sleep(random.uniform(0.05, 0.15))
    
    def _create_error_result(self, error_message: str, session_id: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            "success": False,
            "query": self.query,
            "session_id": session_id,
            "pages_retrieved": 0,
            "total_pages_attempted": 0,
            "total_time_seconds": 0,
            "error": error_message,
            "results": [],
            "html_files": [],
            "summary": {
                "success_rate": 0,
                "avg_response_time_ms": None,
                "errors_encountered": [error_message]
            }
        }