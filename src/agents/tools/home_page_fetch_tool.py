"""
Home Page Fetch Tool

Tool for fetching home pages and discovering initial links for site crawling.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import asdict

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field

# Import the core crawler components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from site_crawler_agent import SiteCrawler, PageType, CrawlResult
except ImportError:
    # Fallback for when running without the full agent
    SiteCrawler = None
    PageType = None
    CrawlResult = None


class HomePageFetchTool(BaseTool):
    """
    Tool for fetching home pages and discovering initial navigation links.
    
    This tool handles the first phase of website crawling by fetching the
    home page and identifying key navigation links for further crawling.
    """
    
    domain: str = Field(
        ...,
        description="Domain to fetch home page from (e.g., 'example.com')"
    )
    
    start_url: Optional[str] = Field(
        None,
        description="Optional specific URL to start from instead of domain root"
    )
    
    timeout: Optional[float] = Field(
        30.0,
        description="Request timeout in seconds"
    )
    
    discover_links: bool = Field(
        True,
        description="Whether to discover and classify links on the home page"
    )
    
    max_links: Optional[int] = Field(
        50,
        description="Maximum number of links to discover and classify"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crawler = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.HomePageFetchTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_crawler(self) -> bool:
        """Initialize the site crawler if not already done"""
        if self.crawler is None:
            if SiteCrawler is None:
                self.logger.error("SiteCrawler not available")
                return False
            
            try:
                config = {
                    "timeout": self.timeout,
                    "link_discovery": {
                        "max_links_per_page": self.max_links,
                        "min_confidence_threshold": 0.2
                    }
                }
                self.crawler = SiteCrawler(config)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize crawler: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the home page fetch operation.
        
        Returns:
            Dictionary containing fetch results and discovered links
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting home page fetch for domain: {self.domain}")
            
            # Initialize crawler
            if not self._initialize_crawler():
                return {
                    "success": False,
                    "error": "Failed to initialize crawler",
                    "domain": self.domain
                }
            
            # Fetch the home page
            if self.start_url:
                result = self.crawler.fetch_page(self.start_url, self.timeout)
            else:
                result = self.crawler.crawl_home_page(self.domain, self.start_url)
            
            # Process results
            response_data = {
                "success": result.success,
                "domain": self.domain,
                "url_fetched": result.url,
                "status_code": result.status_code,
                "response_time_ms": result.response_time_ms,
                "content_length": result.content_length,
                "content_type": result.content_type,
                "redirect_url": result.redirect_url,
                "error": result.error,
                "crawl_timestamp": result.crawl_timestamp,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
            # Add link discovery results if requested
            if self.discover_links and result.success:
                discovered_links = []
                link_summary = {}
                
                for link in result.discovered_links:
                    link_data = {
                        "url": link.url,
                        "page_type": link.page_type.value if hasattr(link.page_type, 'value') else str(link.page_type),
                        "link_text": link.link_text,
                        "confidence_score": link.confidence_score,
                        "discovered_on_page": link.discovered_on_page
                    }
                    discovered_links.append(link_data)
                    
                    # Count by page type
                    page_type = link_data["page_type"]
                    link_summary[page_type] = link_summary.get(page_type, 0) + 1
                
                response_data.update({
                    "links_discovered": len(discovered_links),
                    "discovered_links": discovered_links,
                    "link_summary_by_type": link_summary,
                    "priority_links": self._get_priority_links(discovered_links)
                })
                
                self.logger.info(f"Home page fetch completed for {self.domain}: "
                               f"{len(discovered_links)} links discovered")
            else:
                response_data["links_discovered"] = 0
                response_data["discovered_links"] = []
                
                if not result.success:
                    self.logger.warning(f"Home page fetch failed for {self.domain}: {result.error}")
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Error during home page fetch for {self.domain}: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_priority_links(self, discovered_links: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract priority links organized by type"""
        priority_types = ["contact", "about", "team", "services"]
        priority_links = {}
        
        for link in discovered_links:
            page_type = link["page_type"]
            if page_type in priority_types:
                if page_type not in priority_links:
                    priority_links[page_type] = []
                priority_links[page_type].append({
                    "url": link["url"],
                    "link_text": link["link_text"],
                    "confidence_score": link["confidence_score"]
                })
        
        # Sort each type by confidence
        for page_type in priority_links:
            priority_links[page_type].sort(
                key=lambda x: x["confidence_score"], 
                reverse=True
            )
            # Keep only top 3 of each type
            priority_links[page_type] = priority_links[page_type][:3]
        
        return priority_links


class LinkDiscoveryTool(BaseTool):
    """
    Tool for discovering and classifying links from HTML content.
    
    This tool can be used to analyze HTML content and extract
    classified links without fetching pages.
    """
    
    html_content: str = Field(
        ...,
        description="HTML content to analyze for links"
    )
    
    base_url: str = Field(
        ...,
        description="Base URL for resolving relative links"
    )
    
    current_url: Optional[str] = Field(
        None,
        description="URL of the current page being analyzed"
    )
    
    max_links: Optional[int] = Field(
        100,
        description="Maximum number of links to discover"
    )
    
    min_confidence: Optional[float] = Field(
        0.2,
        description="Minimum confidence threshold for link classification"
    )
    
    priority_types_only: bool = Field(
        False,
        description="Whether to return only high-priority page types (contact, about, team)"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.link_discovery = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.LinkDiscoveryTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_discovery(self) -> bool:
        """Initialize the link discovery system"""
        if self.link_discovery is None:
            try:
                from site_crawler_agent import LinkDiscovery
                
                config = {
                    "max_links_per_page": self.max_links,
                    "min_confidence_threshold": self.min_confidence
                }
                self.link_discovery = LinkDiscovery(config)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize link discovery: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute link discovery on the provided HTML content.
        
        Returns:
            Dictionary containing discovered and classified links
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting link discovery for URL: {self.current_url or self.base_url}")
            
            # Initialize link discovery
            if not self._initialize_discovery():
                return {
                    "success": False,
                    "error": "Failed to initialize link discovery system"
                }
            
            # Discover links
            discovered_links = self.link_discovery.discover_links(
                self.html_content,
                self.base_url,
                self.current_url or self.base_url
            )
            
            # Filter by priority if requested
            if self.priority_types_only:
                priority_types = {"contact", "about", "team", "services"}
                discovered_links = [
                    link for link in discovered_links
                    if hasattr(link.page_type, 'value') and link.page_type.value in priority_types
                ]
            
            # Convert to serializable format
            links_data = []
            link_summary = {}
            
            for link in discovered_links:
                link_data = {
                    "url": link.url,
                    "page_type": link.page_type.value if hasattr(link.page_type, 'value') else str(link.page_type),
                    "link_text": link.link_text,
                    "confidence_score": link.confidence_score,
                    "discovered_on_page": link.discovered_on_page,
                    "context": link.context
                }
                links_data.append(link_data)
                
                # Count by page type
                page_type = link_data["page_type"]
                link_summary[page_type] = link_summary.get(page_type, 0) + 1
            
            # Sort by confidence
            links_data.sort(key=lambda x: x["confidence_score"], reverse=True)
            
            processing_time = (time.time() - start_time) * 1000
            
            self.logger.info(f"Link discovery completed: {len(links_data)} links found")
            
            return {
                "success": True,
                "base_url": self.base_url,
                "current_url": self.current_url,
                "total_links_discovered": len(links_data),
                "discovered_links": links_data,
                "link_summary_by_type": link_summary,
                "high_confidence_links": [
                    link for link in links_data 
                    if link["confidence_score"] >= 0.6
                ],
                "processing_time_ms": processing_time,
                "discovery_statistics": self.link_discovery.get_statistics() if self.link_discovery else {}
            }
            
        except Exception as e:
            self.logger.error(f"Error during link discovery: {e}")
            return {
                "success": False,
                "error": str(e),
                "base_url": self.base_url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the tools
    print("Testing HomePageFetchTool...")
    
    # Test home page fetch
    tool = HomePageFetchTool(
        domain="example.com",
        discover_links=True,
        max_links=20
    )
    
    result = tool.run()
    print(f"Result: {result}")