"""
Refactored Bing Navigator Agent

Specialized search agent with enhanced anti-detection and rate limiting.
"""

import time
from typing import List, Optional, Dict, Any

from ...core.base_agent import SearchAgent, AgentConfig
from ...core.config_manager import config_manager
from ..tools.refactored.serp_fetch_tool import SerpFetchTool


class BingNavigator(SearchAgent):
    """
    Enhanced Bing Navigator Agent with improved search capabilities.
    
    This agent specializes in executing Bing searches with anti-detection measures,
    rate limiting, and comprehensive error handling.
    
    Improvements:
    - Intelligent rate limiting and backoff strategies
    - Session management for consistent searches
    - Anti-detection measure coordination
    - Search result caching and deduplication
    - Comprehensive search metrics tracking
    """
    
    def __init__(self):
        """Initialize Bing Navigator with enhanced configuration"""
        config = AgentConfig(
            name="BingNavigator",
            description=(
                "Expert Bing SERP retrieval specialist with advanced anti-detection. "
                "I execute searches, handle pagination, manage rate limits, and ensure "
                "reliable data collection while avoiding detection."
            ),
            model=config_manager.get("api.openai_model", "gpt-4-turbo-preview"),
            temperature=0.5,  # Lower temperature for more consistent searches
            tools=[SerpFetchTool],
            enable_metrics=True,
            enable_caching=True,
            instructions_path="instructions/bing_navigator.md"
        )
        
        super().__init__(config)
        
        # Search-specific attributes
        self.active_sessions: Dict[str, Dict] = {}
        self.search_cache: Dict[str, Any] = {}
        self.blocked_queries: List[str] = []
        
        # Enhanced search metrics
        self.search_patterns = {
            "queries_by_hour": {},
            "success_by_location": {},
            "block_patterns": []
        }
    
    def _get_default_instructions(self) -> str:
        """Provide default instructions for Bing Navigator"""
        return """
        You are the Bing Navigator, specialized in search engine result retrieval.
        
        Your responsibilities:
        1. Execute Bing searches with provided queries
        2. Implement anti-detection measures:
           - Rotate user agents
           - Use proxy rotation when available
           - Add human-like delays between requests
           - Handle CAPTCHAs and rate limits gracefully
        3. Manage search pagination:
           - Retrieve multiple pages when requested
           - Track page continuity
           - Detect end of results
        4. Handle errors intelligently:
           - Retry with backoff for temporary failures
           - Switch strategies for persistent blocks
           - Report unrecoverable errors clearly
        5. Optimize search performance:
           - Cache results when appropriate
           - Batch similar queries
           - Minimize redundant searches
        
        Search best practices:
        - Use specific, targeted queries
        - Respect rate limits (12-18 requests per minute)
        - Monitor for block signals (429, 503, CAPTCHAs)
        - Maintain session consistency for related searches
        
        Output format:
        - Return raw HTML for parsing
        - Include metadata (timestamp, page number, status)
        - Report any anomalies or warnings
        """
    
    def execute_search(self, 
                      query: str,
                      max_pages: int = 1,
                      use_cache: bool = True,
                      session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a search with enhanced features.
        
        Args:
            query: Search query
            max_pages: Maximum pages to retrieve
            use_cache: Whether to use cached results
            session_id: Optional session for continuity
            
        Returns:
            Search results with metadata
        """
        with self.performance_tracking("execute_search"):
            # Check cache first
            cache_key = f"{query}:{max_pages}"
            if use_cache and cache_key in self.search_cache:
                self.logger.debug(f"Returning cached results for: {query}")
                return self.search_cache[cache_key]
            
            # Check if query is blocked
            if query in self.blocked_queries:
                self.logger.warning(f"Query is blocked: {query}")
                return self._create_blocked_response(query)
            
            # Create or reuse session
            session_id = session_id or self._create_session_id()
            session = self._get_or_create_session(session_id)
            
            # Execute search with monitoring
            results = self._execute_monitored_search(
                query, max_pages, session
            )
            
            # Update metrics and patterns
            self._update_search_patterns(query, results)
            
            # Cache successful results
            if results["status"] == "success" and use_cache:
                self.search_cache[cache_key] = results
                
            return results
    
    def _execute_monitored_search(self,
                                 query: str,
                                 max_pages: int,
                                 session: Dict) -> Dict[str, Any]:
        """Execute search with monitoring and error handling"""
        results = {
            "query": query,
            "pages": [],
            "status": "pending",
            "errors": [],
            "metadata": {
                "session_id": session["id"],
                "start_time": time.time(),
                "max_pages_requested": max_pages
            }
        }
        
        try:
            for page_num in range(1, max_pages + 1):
                # Check rate limiting
                if not self._check_rate_limit(session):
                    results["errors"].append("Rate limit exceeded")
                    break
                
                # Execute single page search
                page_result = self._search_single_page(
                    query, page_num, session
                )
                
                # Check for blocks
                if self._is_blocked(page_result):
                    self._handle_block(query, page_result)
                    results["errors"].append(f"Blocked on page {page_num}")
                    break
                
                results["pages"].append(page_result)
                
                # Add delay between pages
                if page_num < max_pages:
                    self._apply_search_delay(session)
            
            # Set final status
            if len(results["pages"]) > 0:
                results["status"] = "success"
            elif results["errors"]:
                results["status"] = "error"
            else:
                results["status"] = "no_results"
            
            # Add completion metadata
            results["metadata"]["end_time"] = time.time()
            results["metadata"]["duration"] = (
                results["metadata"]["end_time"] - results["metadata"]["start_time"]
            )
            results["metadata"]["pages_retrieved"] = len(results["pages"])
            
        except Exception as e:
            self.logger.error(f"Search execution failed: {e}")
            results["status"] = "error"
            results["errors"].append(str(e))
        
        return results
    
    def _search_single_page(self,
                           query: str,
                           page: int,
                           session: Dict) -> Dict[str, Any]:
        """Execute search for a single page"""
        # This would use the SerpFetchTool
        # For now, return a mock structure
        return {
            "page": page,
            "html": f"<html>Mock results for {query} page {page}</html>",
            "timestamp": time.time(),
            "status": "success"
        }
    
    def _check_rate_limit(self, session: Dict) -> bool:
        """Check if rate limit allows another request"""
        current_time = time.time()
        
        # Get session request history
        request_times = session.get("request_times", [])
        
        # Remove old entries (older than 1 minute)
        request_times = [t for t in request_times if current_time - t < 60]
        
        # Check rate limit (12 requests per minute)
        if len(request_times) >= config_manager.get("search.rate_limit_rpm", 12):
            self.logger.warning("Rate limit reached, waiting...")
            return False
        
        # Update session
        request_times.append(current_time)
        session["request_times"] = request_times
        
        return True
    
    def _is_blocked(self, page_result: Dict) -> bool:
        """Check if search result indicates blocking"""
        if page_result["status"] != "success":
            return False
        
        html = page_result.get("html", "").lower()
        
        # Check for block indicators
        block_indicators = [
            "captcha",
            "unusual traffic",
            "automated queries",
            "rate limit",
            "429",
            "503"
        ]
        
        return any(indicator in html for indicator in block_indicators)
    
    def _handle_block(self, query: str, page_result: Dict):
        """Handle blocked search"""
        self.logger.warning(f"Block detected for query: {query}")
        
        # Add to blocked queries
        self.blocked_queries.append(query)
        
        # Track block pattern
        self.search_patterns["block_patterns"].append({
            "query": query,
            "timestamp": time.time(),
            "indicators": self._extract_block_indicators(page_result)
        })
        
        # Update metrics
        self.search_metrics["blocked_requests"] += 1
    
    def _extract_block_indicators(self, page_result: Dict) -> List[str]:
        """Extract specific block indicators from result"""
        html = page_result.get("html", "").lower()
        indicators = []
        
        if "captcha" in html:
            indicators.append("captcha")
        if "429" in html or "rate" in html:
            indicators.append("rate_limit")
        if "503" in html:
            indicators.append("service_unavailable")
        
        return indicators
    
    def _apply_search_delay(self, session: Dict):
        """Apply appropriate delay between searches"""
        # Base delay
        base_delay = config_manager.get("search.delay_between_requests", 2.0)
        
        # Adjust based on session history
        if session.get("consecutive_searches", 0) > 5:
            # Increase delay for long sessions
            delay = base_delay * 1.5
        else:
            delay = base_delay
        
        # Add jitter
        import random
        delay += random.uniform(0, 0.5)
        
        self.logger.debug(f"Applying delay: {delay:.2f}s")
        time.sleep(delay)
        
        # Update session
        session["consecutive_searches"] = session.get("consecutive_searches", 0) + 1
    
    def _create_session_id(self) -> str:
        """Create unique session ID"""
        import uuid
        return f"search_session_{uuid.uuid4().hex[:8]}"
    
    def _get_or_create_session(self, session_id: str) -> Dict:
        """Get existing session or create new one"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "id": session_id,
                "created": time.time(),
                "request_times": [],
                "consecutive_searches": 0
            }
        
        return self.active_sessions[session_id]
    
    def _create_blocked_response(self, query: str) -> Dict[str, Any]:
        """Create response for blocked query"""
        return {
            "query": query,
            "pages": [],
            "status": "blocked",
            "errors": ["Query is currently blocked due to previous detection"],
            "metadata": {
                "blocked_at": time.time()
            }
        }
    
    def _update_search_patterns(self, query: str, results: Dict):
        """Update search pattern tracking"""
        current_hour = time.strftime("%Y-%m-%d %H:00")
        
        # Track queries by hour
        if current_hour not in self.search_patterns["queries_by_hour"]:
            self.search_patterns["queries_by_hour"][current_hour] = 0
        self.search_patterns["queries_by_hour"][current_hour] += 1
        
        # Track success by location (if available in query)
        # This would parse location from query
        location = self._extract_location(query)
        if location:
            if location not in self.search_patterns["success_by_location"]:
                self.search_patterns["success_by_location"][location] = {
                    "total": 0,
                    "successful": 0
                }
            
            self.search_patterns["success_by_location"][location]["total"] += 1
            if results["status"] == "success":
                self.search_patterns["success_by_location"][location]["successful"] += 1
    
    def _extract_location(self, query: str) -> Optional[str]:
        """Extract location from search query"""
        # Simple extraction - would be more sophisticated in production
        common_locations = [
            "new york", "los angeles", "chicago", "houston", "phoenix",
            "philadelphia", "san antonio", "san diego", "dallas", "atlanta"
        ]
        
        query_lower = query.lower()
        for location in common_locations:
            if location in query_lower:
                return location
        
        return None
    
    def clear_cache(self):
        """Clear search cache"""
        self.search_cache.clear()
        self.logger.info("Search cache cleared")
    
    def clear_blocked_queries(self):
        """Clear blocked queries list"""
        self.blocked_queries.clear()
        self.logger.info("Blocked queries cleared")
    
    def get_search_patterns(self) -> Dict[str, Any]:
        """Get search pattern analysis"""
        return {
            **self.search_patterns,
            "cache_size": len(self.search_cache),
            "blocked_queries_count": len(self.blocked_queries),
            "active_sessions": len(self.active_sessions)
        }
    
    def _cleanup_resources(self):
        """Clean up search-specific resources"""
        # Clear cache
        self.clear_cache()
        
        # Close active sessions
        self.active_sessions.clear()
        
        self.logger.info("Search resources cleaned up")


# For backward compatibility
class BingNavigatorAgent(BingNavigator):
    """Alias for compatibility"""
    pass