from agency_swarm.tools import BaseTool
from pydantic import Field
import requests
import time
import hashlib
import json
from pathlib import Path

class SerpFetchTool(BaseTool):
    """
    Fetches Bing SERP pages via requests (fallback when Botasaurus has issues).
    
    This tool provides a working alternative to Botasaurus for basic search functionality.
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
        description="Enable basic stealth mode with realistic user agent."
    )

    def run(self) -> dict:
        """
        Execute the Bing search with requests library.
        Returns HTML content and metadata including timing and status.
        """
        try:
            # Create session ID for tracking
            session_id = f"serp_{hashlib.md5(self.query.encode()).hexdigest()[:8]}"
            
            # Create session with headers
            session = requests.Session()
            
            if self.use_stealth:
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
            
            start_time = time.time()
            
            # Build Bing URL
            if self.page == 1:
                bing_url = f"https://www.bing.com/search?q={self.query.replace(' ', '+')}"
            else:
                start = (self.page - 1) * 10 + 1
                bing_url = f"https://www.bing.com/search?q={self.query.replace(' ', '+')}&first={start}"
            
            # Make request
            response = session.get(bing_url, timeout=self.timeout_s)
            response.raise_for_status()
            
            # Get response data
            page_html = response.text
            response_time = time.time() - start_time
            
            # Check for blocking/success
            blocked_indicators = ['blocked', 'captcha', 'access denied', 'unusual traffic']
            is_blocked = any(indicator in response.text.lower() for indicator in blocked_indicators)
            
            success_indicators = ['search', 'results', self.query.split()[0].lower()]
            has_results = any(indicator in page_html.lower() for indicator in success_indicators)
            
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
                    f.write(page_html)
                html_saved = True
                file_size = len(page_html.encode('utf-8', errors='ignore'))
            except Exception as e:
                html_saved = False
                html_filepath = None
                file_size = 0
            
            # Return compact response with file reference instead of HTML content
            if response.status_code == 200 and len(page_html) > 1000:
                return {
                    "status": "success", 
                    "html_file": str(html_filepath) if html_saved else None,
                    "html_preview": page_html[:1000] + "..." if len(page_html) > 1000 else page_html,
                    "meta": {
                        "query": self.query,
                        "page": self.page,
                        "timestamp": time.time(),
                        "response_time_ms": int(response_time * 1000),
                        "content_length": len(page_html),
                        "file_size": file_size,
                        "html_saved": html_saved,
                        "stealth_enabled": self.use_stealth,
                        "method": "requests",
                        "session_id": session_id,
                        "title": "Bing Search Results",
                        "url": bing_url,
                        "is_blocked": is_blocked,
                        "status_code": response.status_code
                    }
                }
            else:
                return {
                    "status": "error",
                    "error_type": "search_error",
                    "error_message": f"Search failed: status {response.status_code}, content length {len(page_html)}",
                    "meta": {
                        "query": self.query,
                        "page": self.page,
                        "timeout_used": self.timeout_s,
                        "stealth_enabled": self.use_stealth,
                        "session_id": session_id,
                        "status_code": response.status_code
                    }
                }
            
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error_type": "request_error", 
                "error_message": f"Request failed: {str(e)}",
                "meta": {
                    "query": self.query, 
                    "page": self.page,
                    "timeout_used": self.timeout_s
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