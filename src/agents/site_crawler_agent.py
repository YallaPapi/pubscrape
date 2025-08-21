"""
Site Crawler Agent

Agency Swarm agent for crawling business websites to discover contact pages
and other relevant content. Integrates with Botasaurus for anti-detection
and follows respectful crawling practices.
"""

import logging
import time
import re
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse, urljoin
from dataclasses import dataclass, asdict, field
from enum import Enum
import requests
from bs4 import BeautifulSoup

try:
    from agency_swarm import Agent
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    # Create mock classes for testing
    class Agent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

# Optional Botasaurus integration
try:
    from botasaurus import bt
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    bt = None

from pydantic import Field


class PageType(Enum):
    """Types of pages that can be discovered"""
    HOME = "home"
    CONTACT = "contact"
    ABOUT = "about"
    TEAM = "team"
    STAFF = "staff"
    FOOTER = "footer"
    PRIVACY = "privacy"
    LEGAL = "legal"
    TERMS = "terms"
    SITEMAP = "sitemap"
    SERVICES = "services"
    CAREERS = "careers"
    NEWS = "news"
    BLOG = "blog"
    FAQ = "faq"
    UNKNOWN = "unknown"


class CrawlStatus(Enum):
    """Status of crawl operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class DiscoveredLink:
    """Represents a discovered link during crawling"""
    url: str
    page_type: PageType
    link_text: str
    confidence_score: float = 0.0
    discovered_on_page: str = ""
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Normalize the URL after initialization"""
        self.url = self._normalize_url(self.url)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistency"""
        if not url:
            return ""
        
        # Remove fragments
        if '#' in url:
            url = url.split('#')[0]
        
        # Strip trailing slashes except for root
        if url.endswith('/') and len(url) > 1:
            url = url.rstrip('/')
        
        return url


@dataclass
class CrawlResult:
    """Result of crawling a page"""
    url: str
    status_code: Optional[int] = None
    content: Optional[str] = None
    discovered_links: List[DiscoveredLink] = field(default_factory=list)
    error: Optional[str] = None
    response_time_ms: Optional[float] = None
    content_length: Optional[int] = None
    content_type: Optional[str] = None
    redirect_url: Optional[str] = None
    crawl_timestamp: float = field(default_factory=time.time)
    
    @property
    def success(self) -> bool:
        """Whether the crawl was successful"""
        return self.status_code is not None and 200 <= self.status_code < 300


@dataclass
class SiteCrawlSession:
    """Represents a crawl session for a domain"""
    domain: str
    start_url: str
    max_pages: int
    discovered_links: Dict[str, DiscoveredLink] = field(default_factory=dict)
    crawled_pages: Dict[str, CrawlResult] = field(default_factory=dict)
    pending_urls: Set[str] = field(default_factory=set)
    failed_urls: Set[str] = field(default_factory=set)
    blocked_urls: Set[str] = field(default_factory=set)
    session_id: str = ""
    status: CrawlStatus = CrawlStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_pages_crawled: int = 0
    total_links_discovered: int = 0
    robots_txt_content: Optional[str] = None
    
    def __post_init__(self):
        """Initialize session with start URL"""
        if not self.session_id:
            self.session_id = f"{self.domain}_{int(time.time())}"
        
        # Add start URL to pending
        self.pending_urls.add(self.start_url)


class LinkDiscovery:
    """
    Core link discovery system for identifying relevant pages on websites.
    
    This class handles the parsing of HTML content to find and classify links
    based on URL patterns, link text, and contextual clues.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Link classification patterns
        self.page_patterns = self._initialize_page_patterns()
        
        # Configuration
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.3)
        self.max_links_per_page = self.config.get("max_links_per_page", 200)
        self.ignore_extensions = self.config.get("ignore_extensions", [
            '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.svg',
            '.css', '.js', '.ico', '.xml', '.zip', '.rar', '.exe'
        ])
        
        self.logger.info("LinkDiscovery initialized with pattern-based classification")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the link discovery system"""
        logger = logging.getLogger(f"{__name__}.LinkDiscovery")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_page_patterns(self) -> Dict[PageType, Dict[str, List[str]]]:
        """Initialize patterns for page type classification"""
        return {
            PageType.CONTACT: {
                "url_patterns": [
                    r"/contact", r"/contact-us", r"/contact_us", r"/get-in-touch",
                    r"/reach-us", r"/contact-info", r"/contactus", r"/contact\.html",
                    r"/contact\.php", r"/kontakt", r"/contacto"
                ],
                "text_patterns": [
                    r"contact\s*us", r"get\s*in\s*touch", r"reach\s*us", r"contact\s*info",
                    r"contact\s*form", r"contact\s*page", r"get\s*in\s*contact"
                ],
                "context_selectors": [
                    "footer a", "nav a", ".contact", "#contact", ".footer-contact"
                ]
            },
            PageType.ABOUT: {
                "url_patterns": [
                    r"/about", r"/about-us", r"/about_us", r"/aboutus", r"/our-story",
                    r"/who-we-are", r"/company", r"/about\.html", r"/about\.php"
                ],
                "text_patterns": [
                    r"about\s*us", r"about\s*our", r"our\s*story", r"who\s*we\s*are",
                    r"our\s*company", r"about\s*page", r"learn\s*more"
                ],
                "context_selectors": [
                    "nav a", "header a", ".about", "#about"
                ]
            },
            PageType.TEAM: {
                "url_patterns": [
                    r"/team", r"/our-team", r"/our_team", r"/staff", r"/people",
                    r"/leadership", r"/management", r"/team\.html"
                ],
                "text_patterns": [
                    r"our\s*team", r"meet\s*the\s*team", r"team\s*members", r"staff",
                    r"leadership", r"our\s*people", r"management"
                ],
                "context_selectors": [
                    "nav a", ".team", "#team", ".staff"
                ]
            },
            PageType.SERVICES: {
                "url_patterns": [
                    r"/services", r"/our-services", r"/what-we-do", r"/solutions",
                    r"/products", r"/offerings"
                ],
                "text_patterns": [
                    r"our\s*services", r"what\s*we\s*do", r"solutions", r"products",
                    r"offerings", r"services"
                ],
                "context_selectors": [
                    "nav a", ".services", "#services"
                ]
            },
            PageType.PRIVACY: {
                "url_patterns": [
                    r"/privacy", r"/privacy-policy", r"/privacy_policy", r"/privacypolicy"
                ],
                "text_patterns": [
                    r"privacy\s*policy", r"privacy\s*statement", r"data\s*protection"
                ],
                "context_selectors": [
                    "footer a", ".legal", ".privacy"
                ]
            },
            PageType.LEGAL: {
                "url_patterns": [
                    r"/legal", r"/terms", r"/terms-of-service", r"/terms_of_service",
                    r"/conditions", r"/disclaimer"
                ],
                "text_patterns": [
                    r"terms\s*of\s*service", r"legal\s*notice", r"disclaimer",
                    r"terms\s*and\s*conditions"
                ],
                "context_selectors": [
                    "footer a", ".legal", ".terms"
                ]
            },
            PageType.SITEMAP: {
                "url_patterns": [
                    r"/sitemap", r"/site-map", r"/sitemap\.xml", r"/sitemap\.html"
                ],
                "text_patterns": [
                    r"site\s*map", r"sitemap"
                ],
                "context_selectors": [
                    "footer a", ".sitemap"
                ]
            },
            PageType.CAREERS: {
                "url_patterns": [
                    r"/careers", r"/jobs", r"/employment", r"/work-with-us", r"/join-us"
                ],
                "text_patterns": [
                    r"careers", r"jobs", r"employment", r"work\s*with\s*us", r"join\s*us"
                ],
                "context_selectors": [
                    "nav a", "footer a", ".careers"
                ]
            }
        }
    
    def discover_links(self, html_content: str, base_url: str, 
                      current_url: str = "") -> List[DiscoveredLink]:
        """
        Discover and classify links from HTML content.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative links
            current_url: URL of the current page being parsed
            
        Returns:
            List of discovered and classified links
        """
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            discovered_links = []
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            if len(links) > self.max_links_per_page:
                self.logger.warning(f"Found {len(links)} links, limiting to {self.max_links_per_page}")
                links = links[:self.max_links_per_page]
            
            for link in links:
                try:
                    href = link.get('href', '').strip()
                    if not href or href.startswith('#'):
                        continue
                    
                    # Resolve relative URLs
                    absolute_url = urljoin(base_url, href)
                    
                    # Skip if same domain check fails
                    if not self._is_same_domain(absolute_url, base_url):
                        continue
                    
                    # Skip unwanted file extensions
                    if self._has_ignored_extension(absolute_url):
                        continue
                    
                    # Get link text and context
                    link_text = link.get_text(strip=True)
                    
                    # Classify the link
                    page_type, confidence = self._classify_link(
                        absolute_url, link_text, link, soup
                    )
                    
                    # Skip low confidence links unless they're high-priority types
                    if confidence < self.min_confidence_threshold:
                        if page_type not in [PageType.CONTACT, PageType.ABOUT, PageType.TEAM]:
                            continue
                    
                    # Create discovered link
                    discovered_link = DiscoveredLink(
                        url=absolute_url,
                        page_type=page_type,
                        link_text=link_text,
                        confidence_score=confidence,
                        discovered_on_page=current_url or base_url,
                        context={
                            "tag_attributes": dict(link.attrs),
                            "parent_tag": link.parent.name if link.parent else None,
                            "position_in_page": len(discovered_links)
                        }
                    )
                    
                    discovered_links.append(discovered_link)
                    
                except Exception as e:
                    self.logger.debug(f"Error processing link {href}: {e}")
                    continue
            
            # Sort by confidence score
            discovered_links.sort(key=lambda x: x.confidence_score, reverse=True)
            
            self.logger.info(f"Discovered {len(discovered_links)} classified links from {current_url or base_url}")
            
            return discovered_links
            
        except Exception as e:
            self.logger.error(f"Error discovering links from HTML: {e}")
            return []
    
    def _is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL belongs to the same domain as base URL"""
        try:
            url_domain = urlparse(url).netloc.lower()
            base_domain = urlparse(base_url).netloc.lower()
            
            # Remove www prefix for comparison
            url_domain = url_domain.replace('www.', '')
            base_domain = base_domain.replace('www.', '')
            
            return url_domain == base_domain
        except Exception:
            return False
    
    def _has_ignored_extension(self, url: str) -> bool:
        """Check if URL has an extension that should be ignored"""
        try:
            path = urlparse(url).path.lower()
            return any(path.endswith(ext) for ext in self.ignore_extensions)
        except Exception:
            return False
    
    def _classify_link(self, url: str, link_text: str, 
                      link_element, soup) -> Tuple[PageType, float]:
        """
        Classify a link based on URL patterns, text, and context.
        
        Args:
            url: Absolute URL of the link
            link_text: Text content of the link
            link_element: BeautifulSoup link element
            soup: BeautifulSoup object of the entire page
            
        Returns:
            Tuple of (PageType, confidence_score)
        """
        best_type = PageType.UNKNOWN
        best_confidence = 0.0
        
        url_lower = url.lower()
        text_lower = link_text.lower()
        
        for page_type, patterns in self.page_patterns.items():
            confidence = 0.0
            
            # Check URL patterns
            for pattern in patterns.get("url_patterns", []):
                if re.search(pattern, url_lower):
                    confidence += 0.6
                    break
            
            # Check text patterns
            for pattern in patterns.get("text_patterns", []):
                if re.search(pattern, text_lower):
                    confidence += 0.4
                    break
            
            # Check context (location in page)
            context_boost = self._get_context_boost(link_element, patterns)
            confidence += context_boost
            
            # Special handling for contact pages
            if page_type == PageType.CONTACT:
                if any(word in text_lower for word in ['email', 'phone', 'address']):
                    confidence += 0.2
            
            # Update best match
            if confidence > best_confidence:
                best_confidence = confidence
                best_type = page_type
        
        # Normalize confidence to 0-1 range
        best_confidence = min(1.0, max(0.0, best_confidence))
        
        return best_type, best_confidence
    
    def _get_context_boost(self, link_element, patterns: Dict[str, List[str]]) -> float:
        """Get confidence boost based on link context/location"""
        boost = 0.0
        
        # Check if link is in navigation
        parent = link_element.parent
        while parent and parent.name:
            tag_name = parent.name.lower()
            class_names = ' '.join(parent.get('class', [])).lower()
            id_name = parent.get('id', '').lower()
            
            # Navigation context
            if tag_name in ['nav', 'header'] or 'nav' in class_names:
                boost += 0.1
                break
            
            # Footer context
            if tag_name == 'footer' or 'footer' in class_names:
                boost += 0.15
                break
            
            # Sidebar context
            if 'sidebar' in class_names or 'aside' in tag_name:
                boost += 0.05
                break
            
            parent = parent.parent
        
        # Check specific selectors from patterns
        context_selectors = patterns.get("context_selectors", [])
        for selector in context_selectors:
            try:
                # This is a simplified check - in practice, you'd want to
                # check if the link matches the CSS selector
                if any(part in str(link_element.parent) for part in selector.split()):
                    boost += 0.1
                    break
            except Exception:
                continue
        
        return min(0.3, boost)  # Cap context boost
    
    def get_page_type_priority(self, page_type: PageType) -> int:
        """Get crawling priority for a page type (higher = more important)"""
        priorities = {
            PageType.CONTACT: 10,
            PageType.ABOUT: 8,
            PageType.TEAM: 7,
            PageType.SERVICES: 6,
            PageType.CAREERS: 5,
            PageType.PRIVACY: 3,
            PageType.LEGAL: 3,
            PageType.SITEMAP: 4,
            PageType.HOME: 9,
            PageType.UNKNOWN: 1
        }
        return priorities.get(page_type, 1)
    
    def filter_by_priority(self, links: List[DiscoveredLink], 
                          max_count: Optional[int] = None) -> List[DiscoveredLink]:
        """Filter and sort links by priority and confidence"""
        # Sort by priority and confidence
        sorted_links = sorted(
            links,
            key=lambda x: (
                self.get_page_type_priority(x.page_type),
                x.confidence_score
            ),
            reverse=True
        )
        
        if max_count:
            sorted_links = sorted_links[:max_count]
        
        return sorted_links
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        return {
            "patterns_loaded": len(self.page_patterns),
            "min_confidence_threshold": self.min_confidence_threshold,
            "max_links_per_page": self.max_links_per_page,
            "ignored_extensions": len(self.ignore_extensions)
        }


class SiteCrawler:
    """
    Core site crawler for fetching web pages and discovering links.
    
    This class handles the actual crawling operations including HTTP requests,
    session management, and integration with the LinkDiscovery system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Initialize components
        self.link_discovery = LinkDiscovery(self.config.get("link_discovery", {}))
        
        # HTTP session
        self.session = requests.Session()
        self._configure_session()
        
        # Configuration
        self.default_timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2.0)
        self.user_agent = self.config.get("user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        self.logger.info("SiteCrawler initialized with HTTP session")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the site crawler"""
        logger = logging.getLogger(f"{__name__}.SiteCrawler")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _configure_session(self):
        """Configure the HTTP session with headers and settings"""
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def fetch_page(self, url: str, timeout: Optional[float] = None) -> CrawlResult:
        """
        Fetch a single page and return crawl result.
        
        Args:
            url: URL to fetch
            timeout: Optional timeout override
            
        Returns:
            CrawlResult with page content and metadata
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        try:
            self.logger.debug(f"Fetching page: {url}")
            
            response = self.session.get(url, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            # Create crawl result
            result = CrawlResult(
                url=url,
                status_code=response.status_code,
                response_time_ms=response_time,
                content_length=len(response.content) if response.content else 0,
                content_type=response.headers.get('content-type', ''),
                crawl_timestamp=time.time()
            )
            
            # Handle redirects
            if response.url != url:
                result.redirect_url = response.url
            
            # Check if successful
            if response.status_code == 200:
                result.content = response.text
                
                # Discover links
                discovered_links = self.link_discovery.discover_links(
                    response.text, url, url
                )
                result.discovered_links = discovered_links
                
                self.logger.info(f"Successfully fetched {url}: {len(discovered_links)} links discovered")
            else:
                result.error = f"HTTP {response.status_code}"
                self.logger.warning(f"Non-200 response for {url}: {response.status_code}")
            
            return result
            
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            self.logger.warning(f"Timeout fetching {url} after {response_time:.0f}ms")
            return CrawlResult(
                url=url,
                error="Timeout",
                response_time_ms=response_time,
                crawl_timestamp=time.time()
            )
            
        except requests.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.warning(f"Connection error fetching {url}: {e}")
            return CrawlResult(
                url=url,
                error=f"Connection error: {str(e)}",
                response_time_ms=response_time,
                crawl_timestamp=time.time()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Unexpected error fetching {url}: {e}")
            return CrawlResult(
                url=url,
                error=f"Unexpected error: {str(e)}",
                response_time_ms=response_time,
                crawl_timestamp=time.time()
            )
    
    def crawl_home_page(self, domain: str, start_url: Optional[str] = None) -> CrawlResult:
        """
        Crawl the home page of a domain and discover initial links.
        
        Args:
            domain: Domain to crawl
            start_url: Optional specific URL to start from
            
        Returns:
            CrawlResult for the home page
        """
        if not start_url:
            # Try HTTPS first, then HTTP
            for protocol in ['https', 'http']:
                test_url = f"{protocol}://{domain}"
                result = self.fetch_page(test_url)
                if result.success:
                    return result
                elif result.status_code and result.status_code < 500:
                    # Client error but reachable, keep this result
                    return result
            
            # If both failed, return the HTTPS attempt
            return self.fetch_page(f"https://{domain}")
        else:
            return self.fetch_page(start_url)
    
    def create_crawl_session(self, domain: str, max_pages: int = 10, 
                           start_url: Optional[str] = None) -> SiteCrawlSession:
        """
        Create a new crawl session for a domain.
        
        Args:
            domain: Domain to crawl
            max_pages: Maximum pages to crawl
            start_url: Optional specific starting URL
            
        Returns:
            New SiteCrawlSession
        """
        if not start_url:
            start_url = f"https://{domain}"
        
        session = SiteCrawlSession(
            domain=domain,
            start_url=start_url,
            max_pages=max_pages
        )
        
        self.logger.info(f"Created crawl session: {session.session_id} for {domain}")
        return session
    
    def execute_crawl_session(self, session: SiteCrawlSession) -> SiteCrawlSession:
        """
        Execute a complete crawl session.
        
        Args:
            session: SiteCrawlSession to execute
            
        Returns:
            Updated SiteCrawlSession with results
        """
        session.status = CrawlStatus.IN_PROGRESS
        
        try:
            self.logger.info(f"Starting crawl session {session.session_id} for {session.domain}")
            
            urls_to_crawl = list(session.pending_urls)
            pages_crawled = 0
            
            while urls_to_crawl and pages_crawled < session.max_pages:
                current_url = urls_to_crawl.pop(0)
                
                # Skip if already crawled or failed
                if current_url in session.crawled_pages or current_url in session.failed_urls:
                    continue
                
                # Crawl the page
                result = self.fetch_page(current_url)
                session.crawled_pages[current_url] = result
                pages_crawled += 1
                
                if result.success and result.discovered_links:
                    # Add discovered links to session
                    for link in result.discovered_links:
                        if link.url not in session.discovered_links:
                            session.discovered_links[link.url] = link
                            
                            # Add high-priority links to crawl queue
                            if (link.page_type in [PageType.CONTACT, PageType.ABOUT, PageType.TEAM] 
                                and link.url not in session.crawled_pages
                                and link.url not in urls_to_crawl):
                                urls_to_crawl.append(link.url)
                
                elif not result.success:
                    session.failed_urls.add(current_url)
                
                # Remove from pending
                session.pending_urls.discard(current_url)
                
                # Small delay between requests
                time.sleep(1.0)
            
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get crawler statistics"""
        return {
            "configuration": {
                "default_timeout": self.default_timeout,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay,
                "user_agent": self.user_agent[:50] + "..." if len(self.user_agent) > 50 else self.user_agent
            },
            "link_discovery_stats": self.link_discovery.get_statistics()
        }


class SiteCrawlerAgent(Agent):
    """
    Agency Swarm agent for website crawling and page discovery.
    
    This agent coordinates the crawling process using the SiteCrawler
    core class and provides tools for domain crawling operations.
    """
    
    def __init__(self):
        super().__init__(
            name="SiteCrawler",
            description="Crawls business websites to discover contact pages and relevant content using anti-detection measures",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.1,
            max_prompt_tokens=25000,
        )
        
        # Initialize the site crawler
        self.crawler = SiteCrawler()
        
        self.logger = logging.getLogger(f"{__name__}.SiteCrawlerAgent")
        self.logger.info("SiteCrawlerAgent initialized")