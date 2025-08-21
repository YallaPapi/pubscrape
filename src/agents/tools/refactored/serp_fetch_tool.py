"""
Refactored SERP Fetch Tool

Enhanced tool for fetching Bing SERP pages with improved error handling,
anti-detection, and performance monitoring.
"""

import time
from typing import Dict, Any, Optional
from pydantic import Field

from ....core.base_tool import SearchTool
from ....core.config_manager import config_manager
from ....infra.bing_searcher import BingSearcher, BingSearcherConfig, SearchQuery
from ....infra.anti_detection_supervisor import AntiDetectionSupervisor


class SerpFetchTool(SearchTool):
    """
    Enhanced SERP fetching tool with comprehensive anti-detection and monitoring.
    
    Improvements:
    - Intelligent retry strategies based on error types
    - Session persistence for related searches
    - Comprehensive metrics and performance tracking
    - Adaptive rate limiting based on response patterns
    - HTML validation and quality checks
    """
    
    tool_name: str = "SerpFetchTool"
    tool_version: str = "2.0.0"
    
    # Tool-specific fields
    query: str = Field(
        ...,
        description="Search query to execute on Bing"
    )
    page: int = Field(
        1,
        ge=1,
        le=10,
        description="Page number to retrieve (1-10)"
    )
    timeout_s: int = Field(
        30,
        ge=5,
        le=120,
        description="Request timeout in seconds"
    )
    use_stealth: bool = Field(
        True,
        description="Enable anti-detection stealth mode"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for request continuity"
    )
    cache_results: bool = Field(
        True,
        description="Cache results for deduplication"
    )
    
    def __init__(self, **data):
        """Initialize with enhanced configuration"""
        super().__init__(**data)
        
        # Initialize infrastructure components
        self._searcher: Optional[BingSearcher] = None
        self._anti_detection: Optional[AntiDetectionSupervisor] = None
        self._session_cache: Dict[str, Any] = {}
    
    def _execute(self) -> Dict[str, Any]:
        """
        Execute the SERP fetch with enhanced error handling.
        
        Returns:
            Comprehensive result dictionary with HTML and metadata
        """
        # Initialize infrastructure if needed
        self._ensure_infrastructure()
        
        # Create search query object
        search_query = SearchQuery(
            query=self.query,
            max_pages=self.page,
            context={
                "session_id": self.session_id,
                "use_stealth": self.use_stealth,
                "cache_enabled": self.cache_results
            }
        )
        
        # Check cache first
        if self.cache_results:
            cached = self._check_cache(search_query)
            if cached:
                self.logger.debug(f"Cache hit for query: {self.query}")
                return cached
        
        # Execute search with monitoring
        start_time = time.time()
        
        try:
            # Get anti-detection session if enabled
            session_config = None
            if self.use_stealth and self._anti_detection:
                session_config = self._anti_detection.get_session_config()
            
            # Execute search
            result = self._searcher.search(
                query=search_query,
                session_id=self.session_id
            )
            
            # Process and validate result
            processed_result = self._process_search_result(result)
            
            # Cache if successful
            if self.cache_results and processed_result["status"] == "success":
                self._cache_result(search_query, processed_result)
            
            # Track performance
            execution_time = time.time() - start_time
            self._track_performance(execution_time, processed_result["status"])
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"Search execution failed: {e}")
            
            # Attempt recovery based on error type
            recovery_result = self._attempt_recovery(e, search_query)
            if recovery_result:
                return recovery_result
            
            # Return error response if recovery failed
            return self._create_error_result(e, search_query)
    
    def _ensure_infrastructure(self):
        """Ensure infrastructure components are initialized"""
        if self._searcher is None:
            config = BingSearcherConfig(
                default_query_timeout=self.timeout_s,
                max_pages_per_query=self.page,
                enable_html_storage=True,
                enable_result_caching=self.cache_results
            )
            self._searcher = BingSearcher(config)
        
        if self.use_stealth and self._anti_detection is None:
            try:
                self._anti_detection = AntiDetectionSupervisor()
            except Exception as e:
                self.logger.warning(f"Anti-detection unavailable: {e}")
                self._anti_detection = None
    
    def _process_search_result(self, result) -> Dict[str, Any]:
        """
        Process and validate search result.
        
        Args:
            result: Raw search result from BingSearcher
            
        Returns:
            Processed and validated result
        """
        # Extract HTML from pages
        html_content = ""
        if result.pages:
            # For now, concatenate HTML from all pages
            # In production, would handle separately
            for page in result.pages:
                if isinstance(page, dict) and "html" in page:
                    html_content += page.get("html", "")
        
        # Validate HTML content
        validation = self._validate_html(html_content)
        
        # Build comprehensive response
        response = {
            "status": "success" if result.success else "error",
            "html": html_content,
            "validation": validation,
            "meta": {
                "query": result.query,
                "pages_retrieved": result.total_pages_retrieved,
                "total_time": result.total_time_seconds,
                "timestamp": result.timestamp,
                "session_id": result.session_id,
                "cache_status": "miss",
                "stealth_enabled": self.use_stealth,
                "quality_score": validation["quality_score"]
            }
        }
        
        # Add errors if any
        if result.errors:
            response["errors"] = result.errors
            response["status"] = "partial" if html_content else "error"
        
        return response
    
    def _validate_html(self, html: str) -> Dict[str, Any]:
        """
        Validate HTML content quality.
        
        Args:
            html: HTML content to validate
            
        Returns:
            Validation results
        """
        validation = {
            "is_valid": True,
            "quality_score": 1.0,
            "warnings": [],
            "content_length": len(html)
        }
        
        # Check minimum length
        if len(html) < 1000:
            validation["warnings"].append("HTML content unusually short")
            validation["quality_score"] *= 0.5
        
        # Check for error indicators
        error_indicators = [
            "403 forbidden",
            "404 not found",
            "500 internal server error",
            "captcha",
            "unusual traffic"
        ]
        
        html_lower = html.lower()
        for indicator in error_indicators:
            if indicator in html_lower:
                validation["warnings"].append(f"Error indicator found: {indicator}")
                validation["quality_score"] *= 0.3
                validation["is_valid"] = False
        
        # Check for result indicators
        result_indicators = [
            "search-results",
            "b_results",
            "organic",
            "<h2",
            "<h3",
            "href="
        ]
        
        has_results = any(indicator in html_lower for indicator in result_indicators)
        if not has_results:
            validation["warnings"].append("No search results detected")
            validation["quality_score"] *= 0.7
        
        return validation
    
    def _check_cache(self, query: SearchQuery) -> Optional[Dict[str, Any]]:
        """
        Check if query results are cached.
        
        Args:
            query: Search query to check
            
        Returns:
            Cached result if available, None otherwise
        """
        cache_key = f"{query.query}:p{self.page}"
        
        if cache_key in self._session_cache:
            cached = self._session_cache[cache_key]
            
            # Check if cache is still fresh (5 minutes)
            if time.time() - cached["timestamp"] < 300:
                cached["meta"]["cache_status"] = "hit"
                return cached
        
        return None
    
    def _cache_result(self, query: SearchQuery, result: Dict[str, Any]):
        """
        Cache search result.
        
        Args:
            query: Search query
            result: Result to cache
        """
        cache_key = f"{query.query}:p{self.page}"
        
        # Add timestamp for cache expiry
        result["timestamp"] = time.time()
        
        # Store in cache
        self._session_cache[cache_key] = result
        
        # Limit cache size
        if len(self._session_cache) > 100:
            # Remove oldest entries
            sorted_keys = sorted(
                self._session_cache.keys(),
                key=lambda k: self._session_cache[k].get("timestamp", 0)
            )
            for key in sorted_keys[:20]:
                del self._session_cache[key]
    
    def _attempt_recovery(self, 
                         error: Exception,
                         query: SearchQuery) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover from search error.
        
        Args:
            error: The error that occurred
            query: The search query
            
        Returns:
            Recovery result if successful, None otherwise
        """
        error_msg = str(error).lower()
        
        # Rate limit error - wait and retry
        if "rate" in error_msg or "429" in error_msg:
            self.logger.info("Rate limit detected, waiting 30s...")
            time.sleep(30)
            
            try:
                # Retry with reduced pages
                query.max_pages = 1
                result = self._searcher.search(query)
                return self._process_search_result(result)
            except Exception as e:
                self.logger.error(f"Recovery failed: {e}")
                return None
        
        # Network error - immediate retry
        elif "network" in error_msg or "connection" in error_msg:
            self.logger.info("Network error, retrying immediately...")
            
            try:
                result = self._searcher.search(query)
                return self._process_search_result(result)
            except Exception as e:
                self.logger.error(f"Recovery failed: {e}")
                return None
        
        # Other errors - no automatic recovery
        return None
    
    def _create_error_result(self, 
                           error: Exception,
                           query: SearchQuery) -> Dict[str, Any]:
        """
        Create comprehensive error result.
        
        Args:
            error: The error that occurred
            query: The search query
            
        Returns:
            Error result dictionary
        """
        return {
            "status": "error",
            "html": "",
            "validation": {
                "is_valid": False,
                "quality_score": 0.0,
                "warnings": [str(error)],
                "content_length": 0
            },
            "meta": {
                "query": query.query,
                "pages_retrieved": 0,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": time.time(),
                "session_id": self.session_id,
                "cache_status": "miss",
                "stealth_enabled": self.use_stealth,
                "quality_score": 0.0
            },
            "errors": [str(error)]
        }
    
    def _track_performance(self, execution_time: float, status: str):
        """
        Track tool performance metrics.
        
        Args:
            execution_time: Time taken to execute
            status: Result status
        """
        # Update base metrics (handled by parent class)
        
        # Track search-specific metrics
        if status == "success":
            self.track_search(
                query=self.query,
                results_count=1,  # Simplified - would count actual results
                blocked=False
            )
        elif status == "error" and "block" in str(self.metrics.last_error).lower():
            self.track_search(
                query=self.query,
                results_count=0,
                blocked=True
            )
    
    def clear_cache(self):
        """Clear the session cache"""
        self._session_cache.clear()
        self.logger.info("Session cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self._session_cache),
            "cache_keys": list(self._session_cache.keys()),
            "oldest_entry": min(
                (v.get("timestamp", 0) for v in self._session_cache.values()),
                default=0
            )
        }