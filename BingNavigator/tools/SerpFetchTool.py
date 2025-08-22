from agency_swarm.tools import BaseTool
from pydantic import Field
import sys
import os
import time
import hashlib
import json
from pathlib import Path

# Import proper Botasaurus integration
from botasaurus.browser import browser


class SerpFetchTool(BaseTool):
    """
    Fetches Bing SERP pages via Botasaurus with proper anti-detection measures.
    
    This tool uses the corrected Botasaurus API to handle search query execution
    with anti-detection features like user agent rotation and human-like behavior.
    Returns actual HTML content from Bing search results.
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
        description="Enable anti-detection stealth mode with user agent rotation and human-like behavior."
    )

    def run(self) -> dict:
        """
        Execute the Bing search with proper Botasaurus integration.
        Returns HTML content and metadata including timing and status.
        """
        try:
            # Create session ID for tracking
            session_id = f"serp_{hashlib.md5(self.query.encode()).hexdigest()[:8]}"
            
            # Prepare Botasaurus configuration
            botasaurus_config = {
                'headless': True,
                'block_images': True,
            }
            
            if self.use_stealth:
                botasaurus_config.update({
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
            
            # Create the browser function with proper Botasaurus decorator
            @browser(**botasaurus_config)
            def execute_bing_search(driver, search_data):
                """Execute Bing search with proper Botasaurus API"""
                try:
                    query = search_data['query']
                    page_num = search_data['page']
                    start_time = time.time()
                    
                    # Build Bing URL
                    if page_num == 1:
                        bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
                    else:
                        start = (page_num - 1) * 10 + 1
                        bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&first={start}"
                    
                    # Navigate to Bing
                    driver.get(bing_url)
                    driver.sleep(3)
                    
                    # Get page content using CORRECT API (properties not methods)
                    title = driver.title
                    current_url = driver.current_url
                    page_html = driver.page_html  # Property, not method!
                    user_agent_used = driver.user_agent  # Property, not method!
                    
                    # Check for blocking/success (more specific indicators)
                    blocked_indicators = ['captcha', 'access denied', 'unusual traffic', 'verify you are human', 'too many requests']
                    is_blocked = any(indicator in title.lower() for indicator in blocked_indicators)
                    
                    success_indicators = ['search', 'results', query.split()[0].lower()]
                    has_results = any(indicator in page_html.lower() for indicator in success_indicators)
                    
                    # Try fallback if blocked or no results
                    method_used = 'direct_bing'
                    if is_blocked or not has_results or len(page_html) < 5000:
                        # Use proper fallback URL instead of google_get
                        fallback_url = f"https://www.bing.com/search?q={query.replace(' ', '%20')}&setlang=en"
                        driver.get(fallback_url)
                        driver.sleep(2)
                        
                        title = driver.title
                        current_url = driver.current_url
                        page_html = driver.page_html
                        has_results = len(page_html) > 1000
                        method_used = 'bing_fallback'
                    
                    response_time = time.time() - start_time
                    
                    return {
                        'success': has_results and len(page_html) > 1000,
                        'html': page_html,
                        'title': title,
                        'url': current_url,
                        'query': query,
                        'page': page_num,
                        'response_time_ms': int(response_time * 1000),
                        'is_blocked': is_blocked,
                        'content_length': len(page_html),
                        'method': method_used,
                        'user_agent': user_agent_used,
                        'session_id': search_data.get('session_id', 'unknown')
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'query': query,
                        'page': page_num,
                        'session_id': search_data.get('session_id', 'unknown')
                    }
            
            # Execute the search
            search_data = {
                'query': self.query,
                'page': self.page,
                'session_id': session_id
            }
            
            result = execute_bing_search(search_data)
            
            # Format response according to expected interface
            if result.get('success'):
                # FIXED: Save HTML to file instead of including in JSON payload
                # This prevents the 512KB OpenAI tool_outputs limit from being exceeded
                html_content = result.get('html', '')
                
                # Create output directory
                output_dir = Path("output/html_cache")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create unique filename
                timestamp = int(time.time())
                html_filename = f"bing_{session_id}_{timestamp}.html"
                html_filepath = output_dir / html_filename
                
                # Save HTML content to file
                try:
                    with open(html_filepath, 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(html_content)
                    html_saved = True
                    file_size = len(html_content.encode('utf-8', errors='ignore'))
                except Exception as e:
                    html_saved = False
                    html_filepath = None
                    file_size = 0
                
                # Return compact response with file reference instead of HTML content
                return {
                    "status": "success", 
                    "html_file": str(html_filepath) if html_saved else None,
                    "html_preview": html_content[:1000] + "..." if len(html_content) > 1000 else html_content,  # Small preview only
                    "meta": {
                        "query": self.query,
                        "page": self.page,
                        "timestamp": time.time(),
                        "response_time_ms": result.get('response_time_ms', 0),
                        "content_length": result.get('content_length', 0),
                        "file_size": file_size,
                        "html_saved": html_saved,
                        "stealth_enabled": self.use_stealth,
                        "method": result.get('method', 'direct'),
                        "session_id": session_id,
                        "title": result.get('title', '')[:200] + "..." if len(result.get('title', '')) > 200 else result.get('title', ''),  # Truncate title
                        "url": result.get('url', ''),
                        "is_blocked": result.get('is_blocked', False)
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
                        "session_id": session_id
                    }
                }
            
        except ImportError as e:
            return {
                "status": "error",
                "error_type": "import_error", 
                "error_message": f"Botasaurus not available: {str(e)}",
                "meta": {
                    "query": self.query, 
                    "page": self.page,
                    "recommendation": "Ensure Botasaurus is installed: pip install botasaurus"
                }
            }
        except Exception as e:
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