"""
Site Crawl Tool

Tool for executing complete site crawling sessions with configurable
page limits and link discovery.
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
    from site_crawler_agent import SiteCrawler, SiteCrawlSession, PageType, CrawlStatus
except ImportError:
    # Fallback for when running without the full agent
    SiteCrawler = None
    SiteCrawlSession = None
    PageType = None
    CrawlStatus = None


class SiteCrawlTool(BaseTool):
    """
    Tool for executing complete site crawling sessions.
    
    This tool orchestrates the crawling of multiple pages within a domain,
    respecting page limits and prioritizing important page types.
    """
    
    domain: str = Field(
        ...,
        description="Domain to crawl (e.g., 'example.com')"
    )
    
    max_pages: int = Field(
        10,
        description="Maximum number of pages to crawl for this domain"
    )
    
    start_url: Optional[str] = Field(
        None,
        description="Optional specific URL to start crawling from"
    )
    
    priority_types: List[str] = Field(
        default=["contact", "about", "team", "services"],
        description="Page types to prioritize during crawling"
    )
    
    timeout_per_page: float = Field(
        30.0,
        description="Timeout in seconds for each page request"
    )
    
    delay_between_pages: float = Field(
        1.0,
        description="Delay in seconds between page requests"
    )
    
    enable_discovery: bool = Field(
        True,
        description="Whether to discover and follow links"
    )
    
    crawl_session_id: Optional[str] = Field(
        None,
        description="Optional custom session ID for tracking"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crawler = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.SiteCrawlTool")
        
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
                    "timeout": self.timeout_per_page,
                    "link_discovery": {
                        "max_links_per_page": 100,
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
        Execute the complete site crawling session.
        
        Returns:
            Dictionary containing crawl session results and discovered content
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting site crawl for domain: {self.domain} "
                           f"(max {self.max_pages} pages)")
            
            # Initialize crawler
            if not self._initialize_crawler():
                return {
                    "success": False,
                    "error": "Failed to initialize crawler",
                    "domain": self.domain
                }
            
            # Create crawl session
            session = self.crawler.create_crawl_session(
                domain=self.domain,
                max_pages=self.max_pages,
                start_url=self.start_url
            )
            
            if self.crawl_session_id:
                session.session_id = self.crawl_session_id
            
            # Execute the crawl session with custom logic for priority handling
            session = self._execute_prioritized_crawl(session)
            
            # Process and return results
            return self._format_crawl_results(session, start_time)
            
        except Exception as e:
            self.logger.error(f"Error during site crawl for {self.domain}: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _execute_prioritized_crawl(self, session: SiteCrawlSession) -> SiteCrawlSession:
        """Execute crawl session with priority-based page selection"""
        session.status = CrawlStatus.IN_PROGRESS
        
        try:
            self.logger.info(f"Executing crawl session {session.session_id}")
            
            # Convert priority types to enum values if needed
            priority_type_enums = []
            if PageType:
                for ptype in self.priority_types:
                    try:
                        priority_type_enums.append(getattr(PageType, ptype.upper()))
                    except AttributeError:
                        # Try lowercase
                        for page_type in PageType:
                            if page_type.value.lower() == ptype.lower():
                                priority_type_enums.append(page_type)
                                break
            
            urls_to_crawl = list(session.pending_urls)
            pages_crawled = 0
            
            # Priority queue: high-priority URLs first
            high_priority_urls = []
            normal_priority_urls = []
            
            while (urls_to_crawl or high_priority_urls or normal_priority_urls) and pages_crawled < session.max_pages:
                # Select next URL
                if high_priority_urls:
                    current_url = high_priority_urls.pop(0)
                elif normal_priority_urls:
                    current_url = normal_priority_urls.pop(0)
                elif urls_to_crawl:
                    current_url = urls_to_crawl.pop(0)
                else:
                    break
                
                # Skip if already processed
                if (current_url in session.crawled_pages or 
                    current_url in session.failed_urls or 
                    current_url in session.blocked_urls):
                    continue
                
                self.logger.debug(f"Crawling page {pages_crawled + 1}/{session.max_pages}: {current_url}")
                
                # Add delay between requests
                if pages_crawled > 0:
                    time.sleep(self.delay_between_pages)
                
                # Crawl the page
                result = self.crawler.fetch_page(current_url, self.timeout_per_page)
                session.crawled_pages[current_url] = result
                pages_crawled += 1
                
                if result.success and result.discovered_links and self.enable_discovery:
                    # Process discovered links
                    for link in result.discovered_links:
                        if link.url not in session.discovered_links:
                            session.discovered_links[link.url] = link
                            
                            # Check if this is a high-priority link
                            is_high_priority = False
                            if priority_type_enums:
                                is_high_priority = link.page_type in priority_type_enums
                            else:
                                # Fallback to string comparison
                                is_high_priority = any(
                                    ptype.lower() in link.page_type.value.lower() 
                                    if hasattr(link.page_type, 'value') else False
                                    for ptype in self.priority_types
                                )
                            
                            # Add to crawl queue if not already processed
                            if (link.url not in session.crawled_pages and
                                link.url not in session.failed_urls and
                                link.url not in high_priority_urls and
                                link.url not in normal_priority_urls and
                                link.url not in urls_to_crawl):
                                
                                if is_high_priority:
                                    high_priority_urls.append(link.url)
                                    self.logger.debug(f"Added high-priority URL: {link.url} ({link.page_type})")
                                else:
                                    normal_priority_urls.append(link.url)
                
                elif not result.success:
                    session.failed_urls.add(current_url)
                    self.logger.warning(f"Failed to crawl {current_url}: {result.error}")
                
                # Remove from pending
                session.pending_urls.discard(current_url)
            
            session.total_pages_crawled = pages_crawled
            session.total_links_discovered = len(session.discovered_links)
            session.status = CrawlStatus.COMPLETED
            session.end_time = time.time()
            
            duration = session.end_time - session.start_time
            self.logger.info(f"Crawl session completed: {session.session_id}, "
                           f"{pages_crawled} pages crawled, "
                           f"{len(session.discovered_links)} links discovered, "
                           f"duration: {duration:.1f}s")
            
        except Exception as e:
            session.status = CrawlStatus.FAILED
            session.end_time = time.time()
            self.logger.error(f"Crawl session failed: {session.session_id}, error: {e}")
        
        return session
    
    def _format_crawl_results(self, session: SiteCrawlSession, start_time: float) -> Dict[str, Any]:
        """Format crawl session results for return"""
        
        # Convert crawled pages to serializable format
        crawled_pages = {}
        for url, result in session.crawled_pages.items():
            crawled_pages[url] = {
                "url": result.url,
                "status_code": result.status_code,
                "success": result.success,
                "error": result.error,
                "response_time_ms": result.response_time_ms,
                "content_length": result.content_length,
                "content_type": result.content_type,
                "redirect_url": result.redirect_url,
                "links_discovered": len(result.discovered_links) if result.discovered_links else 0,
                "crawl_timestamp": result.crawl_timestamp
            }
        
        # Convert discovered links to serializable format
        discovered_links = {}
        links_by_type = {}
        priority_links = {}
        
        for url, link in session.discovered_links.items():
            page_type = link.page_type.value if hasattr(link.page_type, 'value') else str(link.page_type)
            
            link_data = {
                "url": link.url,
                "page_type": page_type,
                "link_text": link.link_text,
                "confidence_score": link.confidence_score,
                "discovered_on_page": link.discovered_on_page,
                "context": link.context
            }
            
            discovered_links[url] = link_data
            
            # Group by type
            if page_type not in links_by_type:
                links_by_type[page_type] = []
            links_by_type[page_type].append(link_data)
            
            # Track priority links
            if page_type.lower() in [p.lower() for p in self.priority_types]:
                if page_type not in priority_links:
                    priority_links[page_type] = []
                priority_links[page_type].append(link_data)
        
        # Sort priority links by confidence
        for page_type in priority_links:
            priority_links[page_type].sort(
                key=lambda x: x["confidence_score"], 
                reverse=True
            )
        
        # Calculate session statistics
        session_duration = (session.end_time or time.time()) - session.start_time
        processing_time = (time.time() - start_time) * 1000
        
        success_rate = (
            len([p for p in session.crawled_pages.values() if p.success]) 
            / len(session.crawled_pages)
        ) * 100 if session.crawled_pages else 0
        
        return {
            "success": session.status == CrawlStatus.COMPLETED,
            "session_id": session.session_id,
            "domain": session.domain,
            "start_url": session.start_url,
            "status": session.status.value if hasattr(session.status, 'value') else str(session.status),
            "pages_crawled": session.total_pages_crawled,
            "links_discovered": session.total_links_discovered,
            "max_pages_limit": session.max_pages,
            "session_duration_seconds": session_duration,
            "processing_time_ms": processing_time,
            "success_rate_percent": success_rate,
            "crawled_pages": crawled_pages,
            "discovered_links": discovered_links,
            "links_by_type": links_by_type,
            "priority_links": priority_links,
            "failed_urls": list(session.failed_urls),
            "blocked_urls": list(session.blocked_urls),
            "statistics": {
                "total_pages_requested": len(session.crawled_pages),
                "successful_pages": len([p for p in session.crawled_pages.values() if p.success]),
                "failed_pages": len(session.failed_urls),
                "blocked_pages": len(session.blocked_urls),
                "unique_links_found": len(session.discovered_links),
                "avg_response_time_ms": (
                    sum(p.response_time_ms for p in session.crawled_pages.values() 
                        if p.response_time_ms) / len(session.crawled_pages)
                ) if session.crawled_pages else 0
            }
        }


class DomainCrawlBatchTool(BaseTool):
    """
    Tool for crawling multiple domains in batch with shared configuration.
    
    This tool allows crawling multiple domains using consistent settings
    and provides aggregated results across all domains.
    """
    
    domains: List[str] = Field(
        ...,
        description="List of domains to crawl"
    )
    
    max_pages_per_domain: int = Field(
        5,
        description="Maximum pages to crawl per domain"
    )
    
    timeout_per_page: float = Field(
        30.0,
        description="Timeout in seconds for each page request"
    )
    
    delay_between_domains: float = Field(
        5.0,
        description="Delay in seconds between domain crawls"
    )
    
    delay_between_pages: float = Field(
        1.0,
        description="Delay in seconds between page requests within a domain"
    )
    
    priority_types: List[str] = Field(
        default=["contact", "about", "team"],
        description="Page types to prioritize during crawling"
    )
    
    continue_on_error: bool = Field(
        True,
        description="Whether to continue batch if individual domain fails"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.DomainCrawlBatchTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run(self) -> Dict[str, Any]:
        """
        Execute batch crawling across multiple domains.
        
        Returns:
            Dictionary containing aggregated results from all domain crawls
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting batch crawl for {len(self.domains)} domains")
            
            batch_results = {
                "success": True,
                "total_domains": len(self.domains),
                "domains_crawled": 0,
                "domains_failed": 0,
                "total_pages_crawled": 0,
                "total_links_discovered": 0,
                "domain_results": {},
                "aggregated_statistics": {},
                "processing_time_ms": 0
            }
            
            successful_domains = 0
            failed_domains = 0
            all_priority_links = {}
            
            for i, domain in enumerate(self.domains):
                try:
                    self.logger.info(f"Crawling domain {i + 1}/{len(self.domains)}: {domain}")
                    
                    # Create site crawl tool for this domain
                    crawl_tool = SiteCrawlTool(
                        domain=domain,
                        max_pages=self.max_pages_per_domain,
                        priority_types=self.priority_types,
                        timeout_per_page=self.timeout_per_page,
                        delay_between_pages=self.delay_between_pages,
                        enable_discovery=True,
                        crawl_session_id=f"batch_{int(time.time())}_{i}"
                    )
                    
                    # Execute crawl for this domain
                    domain_result = crawl_tool.run()
                    
                    if domain_result.get("success", False):
                        successful_domains += 1
                        batch_results["total_pages_crawled"] += domain_result.get("pages_crawled", 0)
                        batch_results["total_links_discovered"] += domain_result.get("links_discovered", 0)
                        
                        # Aggregate priority links
                        priority_links = domain_result.get("priority_links", {})
                        for page_type, links in priority_links.items():
                            if page_type not in all_priority_links:
                                all_priority_links[page_type] = []
                            all_priority_links[page_type].extend([
                                {**link, "domain": domain} for link in links
                            ])
                    else:
                        failed_domains += 1
                        self.logger.warning(f"Failed to crawl domain {domain}: "
                                          f"{domain_result.get('error', 'Unknown error')}")
                    
                    batch_results["domain_results"][domain] = domain_result
                    
                except Exception as e:
                    failed_domains += 1
                    error_result = {
                        "success": False,
                        "domain": domain,
                        "error": str(e),
                        "pages_crawled": 0,
                        "links_discovered": 0
                    }
                    batch_results["domain_results"][domain] = error_result
                    
                    self.logger.error(f"Error crawling domain {domain}: {e}")
                    
                    if not self.continue_on_error:
                        break
                
                # Delay between domains (except for the last one)
                if i < len(self.domains) - 1:
                    time.sleep(self.delay_between_domains)
            
            # Update batch statistics
            batch_results["domains_crawled"] = successful_domains
            batch_results["domains_failed"] = failed_domains
            batch_results["success"] = successful_domains > 0
            batch_results["processing_time_ms"] = (time.time() - start_time) * 1000
            
            # Sort priority links by confidence
            for page_type in all_priority_links:
                all_priority_links[page_type].sort(
                    key=lambda x: x.get("confidence_score", 0),
                    reverse=True
                )
            
            batch_results["aggregated_priority_links"] = all_priority_links
            
            # Calculate aggregated statistics
            batch_results["aggregated_statistics"] = {
                "success_rate_percent": (successful_domains / len(self.domains)) * 100,
                "avg_pages_per_domain": batch_results["total_pages_crawled"] / successful_domains if successful_domains > 0 else 0,
                "avg_links_per_domain": batch_results["total_links_discovered"] / successful_domains if successful_domains > 0 else 0,
                "total_unique_page_types": len(all_priority_links),
                "domains_with_contact_info": len([
                    d for d, r in batch_results["domain_results"].items()
                    if r.get("success") and "contact" in r.get("priority_links", {})
                ])
            }
            
            self.logger.info(f"Batch crawl completed: {successful_domains}/{len(self.domains)} domains successful, "
                           f"{batch_results['total_pages_crawled']} total pages crawled")
            
            return batch_results
            
        except Exception as e:
            self.logger.error(f"Error during batch crawl: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_domains": len(self.domains),
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the tools
    print("Testing SiteCrawlTool...")
    
    # Test site crawl
    tool = SiteCrawlTool(
        domain="example.com",
        max_pages=3,
        priority_types=["contact", "about"],
        enable_discovery=True
    )
    
    result = tool.run()
    print(f"Crawl result: {result.get('success', False)}")
    print(f"Pages crawled: {result.get('pages_crawled', 0)}")
    print(f"Links discovered: {result.get('links_discovered', 0)}")