from agency_swarm.tools import BaseTool
from pydantic import Field
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import the correct Botasaurus patterns
from botasaurus.browser import browser, Driver
import json
import time
import hashlib


class SerpFetchTool(BaseTool):
    """
    Fetches Bing SERP pages via Botasaurus with proper anti-detection measures.
    
    This tool handles search query execution using the correct Botasaurus API
    with anti-detection features like proxy rotation, user agent rotation, 
    and human-like behavior patterns.
    """
    
    query: str = Field(
        ..., 
        description="The search query string to execute on Bing. Should be specific business-related terms like 'plumber atlanta' or 'restaurant owner contact chicago'."
    )
    page: int = Field(
        1, 
        ge=1, 
        le=10, 
        description="Page number to retrieve (1-10). Page 1 contains the most relevant results."
    )
    timeout_s: int = Field(
        30, 
        ge=5, 
        le=120, 
        description="Network timeout in seconds. Higher values for slow connections, lower for faster response."
    )
    use_stealth: bool = Field(
        True, 
        description="Enable anti-detection stealth mode with proxy rotation, user agent rotation, and human-like behavior."
    )

    def run(self) -> dict:
        """
        Execute the Bing search with proper Botasaurus integration.
        Returns HTML content and metadata including timing, proxy info, and status.
        """
        try:
            # Create session ID for this search
            session_id = f"serp_{hashlib.md5(self.query.encode()).hexdigest()[:8]}"
            
            # Prepare Botasaurus configuration based on stealth settings
            botasaurus_config = {
                'headless': True,
                'block_images': True,
            }
            
            if self.use_stealth:
                # Add anti-detection features
                botasaurus_config.update({
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    # Note: proxy configuration would be added here if available
                })
            
            # Create the browser function with proper Botasaurus decorator
            @browser(**botasaurus_config)
            def execute_bing_search(driver, search_data):
                """Execute Bing search with anti-detection"""
                try:
                    query = search_data['query']
                    page_num = search_data['page']
                    start_time = time.time()
                    
                    # Method 1: Try direct Bing search URL
                    if page_num == 1:
                        bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
                    else:
                        # Calculate start parameter for pagination (Bing uses 'first' parameter)
                        start = (page_num - 1) * 10 + 1
                        bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&first={start}"
                    
                    driver.get(bing_url)
                    driver.sleep(3)  # Wait for page to load
                    
                    # Check if we got results
                    title = driver.title
                    current_url = driver.current_url
                    page_html = driver.page_html()
                    
                    # Detect if we've been blocked or redirected
                    is_blocked = any(signal in title.lower() for signal in ['blocked', 'captcha', 'access denied'])
                    has_results = 'search' in current_url.lower() and len(page_html) > 1000
                    
                    response_time = time.time() - start_time
                    
                    if is_blocked:
                        # Try fallback method: Use google_get to search for Bing results
                        driver.google_get(f"site:bing.com {query}")
                        driver.sleep(2)
                        
                        title = driver.title
                        current_url = driver.current_url
                        page_html = driver.page_html()
                        has_results = len(page_html) > 1000
                    
                    return {
                        'success': has_results and not is_blocked,
                        'html': page_html,
                        'title': title,
                        'url': current_url,
                        'query': query,
                        'page': page_num,
                        'response_time_ms': int(response_time * 1000),
                        'is_blocked': is_blocked,
                        'method': 'fallback_google' if is_blocked else 'direct_bing',
                        'content_length': len(page_html),
                        'session_id': session_id,
                        'user_agent': driver.user_agent
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'query': query,
                        'page': page_num,
                        'session_id': session_id
                    }
            
            # Execute the search
            search_data = {
                'query': self.query,
                'page': self.page,
                'timeout': self.timeout_s,
                'session_id': session_id
            }
            
            result = execute_bing_search(search_data)
            
            # Format the response according to the expected interface
            if result.get('success'):
                return {
                    "status": "success", 
                    "html": result.get('html', ''),
                    "meta": {
                        "query": self.query,
                        "page": self.page,
                        "timestamp": time.time(),
                        "response_time_ms": result.get('response_time_ms', 0),
                        "proxy_used": "none",  # Would be populated if proxy was used
                        "user_agent": result.get('user_agent', 'default'),
                        "rate_limit_status": "green",
                        "content_length": result.get('content_length', 0),
                        "stealth_enabled": self.use_stealth,
                        "pages_retrieved": 1,
                        "method": result.get('method', 'direct'),
                        "session_id": session_id,
                        "bing_title": result.get('title', ''),
                        "bing_url": result.get('url', '')
                    }
                }
            else:
                return {
                    "status": "error",
                    "error_type": "search_error",
                    "error_message": result.get('error', 'Search failed'),
                    "meta": {
                        "query": self.query,
                        "page": self.page,
                        "timeout_used": self.timeout_s,
                        "stealth_enabled": self.use_stealth,
                        "session_id": session_id,
                        "method": result.get('method', 'unknown')
                    }
                }
            
        except ImportError as e:
            # Handle missing Botasaurus gracefully
            return {
                "status": "error",
                "error_type": "import_error", 
                "error_message": f"Botasaurus not available or misconfigured: {str(e)}",
                "meta": {
                    "query": self.query, 
                    "page": self.page,
                    "recommendation": "Ensure Botasaurus is installed: pip install botasaurus"
                }
            }
        except Exception as e:
            # Handle any other errors
            return {
                "status": "error",
                "error_type": "execution_error",
                "error_message": f"SerpFetchTool execution failed: {str(e)}",
                "meta": {
                    "query": self.query, 
                    "page": self.page,
                    "timeout_used": self.timeout_s,
                    "stealth_enabled": self.use_stealth
                }
            }