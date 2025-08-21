"""
SERP Parse Tool for Agency Swarm

Tool for parsing Bing SERP HTML and extracting organic search results
with robust selector strategies and comprehensive metadata tracking.
"""

import logging
import re
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs, unquote

from agency_swarm.tools import BaseTool
from pydantic import Field

# Import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup, Tag
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None
    Tag = None

# Import lxml for robust parsing
try:
    import lxml
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ExtractedResult:
    """Represents a single extracted search result"""
    url: str
    title: str
    snippet: str
    position: int
    domain: str
    original_url: Optional[str] = None
    selector_used: Optional[str] = None
    result_type: str = "organic"
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Extract domain if not provided
        if not self.domain and self.url:
            try:
                parsed = urlparse(self.url)
                self.domain = parsed.netloc.lower()
                # Remove www. prefix for normalization
                if self.domain.startswith('www.'):
                    self.domain = self.domain[4:]
            except Exception:
                self.domain = "unknown"


@dataclass
class SelectorPerformance:
    """Tracks performance of different selectors"""
    selector_name: str
    success_count: int = 0
    total_attempts: int = 0
    last_used: Optional[float] = None
    average_results: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts


class SerpParseTool(BaseTool):
    """
    Tool for parsing Bing SERP HTML and extracting organic search results.
    
    This tool handles:
    - Robust HTML parsing with fallback strategies
    - Multiple selector types (CSS, XPath) with hot-swapping
    - Extraction of URLs, titles, snippets, and positions
    - Detection of different result types (organic, ads, featured snippets)
    - Comprehensive error handling for malformed HTML
    - Performance tracking and selector optimization
    """
    
    html_content: str = Field(
        ...,
        description="Raw HTML content from Bing SERP page"
    )
    
    html_file_path: Optional[str] = Field(
        default=None,
        description="Optional path to HTML file (alternative to html_content)"
    )
    
    query: Optional[str] = Field(
        default=None,
        description="Original search query for context"
    )
    
    page_number: int = Field(
        default=1,
        description="Page number of results (for position calculation)"
    )
    
    selector_mode: str = Field(
        default="adaptive",
        description="Selector strategy: 'primary', 'fallback', 'xpath', or 'adaptive'"
    )
    
    extract_metadata: bool = Field(
        default=True,
        description="Whether to extract additional metadata"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _get_primary_selectors(self) -> Dict[str, str]:
        """Get primary CSS selectors for current Bing layout"""
        return {
            "results_container": "#b_results",
            "organic_result": ".b_algo",
            "result_link": "h2 a[href]",
            "result_title": "h2",
            "result_snippet": ".b_caption p, .b_caption .b_snippetText",
            "ads_container": "#b_pole, .b_ad",
            "knowledge_panel": ".b_ans, .b_entityTP",
            "pagination": ".sb_pagN, #ns a"
        }
    
    def _get_fallback_selectors(self) -> Dict[str, str]:
        """Get fallback CSS selectors for alternative layouts"""
        return {
            "results_container": ".b_results, #results, .search-results",
            "organic_result": ".result, .search-result, .b_algo, .algo",
            "result_link": "a[href], .result-title a, .result-link",
            "result_title": "h2, h3, .result-title, .title",
            "result_snippet": "p, .result-snippet, .result-description, .snippet, .b_caption",
            "ads_container": ".ad, .ads, .sponsored",
            "knowledge_panel": ".knowledge, .entity, .infobox",
            "pagination": "a[aria-label*='Next'], .next, .pagination a"
        }
    
    def _get_xpath_selectors(self) -> Dict[str, str]:
        """Get XPath selectors as final fallback"""
        return {
            "result_links": "//div[@id='b_results']//h2/a[@href] | //div[contains(@class,'b_algo')]//h2/a[@href]",
            "all_links": "//div[contains(@class,'b_algo')]//a[starts-with(@href,'http')] | //div[contains(@class,'result')]//a[starts-with(@href,'http')]",
            "titles": "//div[@class='b_algo']//h2 | //div[contains(@class,'result')]//h2 | //div[contains(@class,'result')]//h3",
            "snippets": "//div[@class='b_algo']//div[@class='b_caption']//p | //div[contains(@class,'result')]//p[contains(@class,'snippet')]"
        }
    
    def _initialize_performance_tracking(self):
        """Initialize performance tracking for all selectors"""
        all_selectors = {
            **{"primary_" + k: v for k, v in self._primary_selectors.items()},
            **{"fallback_" + k: v for k, v in self.fallback_selectors.items()},
            **{"xpath_" + k: v for k, v in self.xpath_selectors.items()}
        }
        
        for selector_name in all_selectors:
            self.selector_performance[selector_name] = SelectorPerformance(
                selector_name=selector_name
            )
    
    def run(self) -> Dict[str, Any]:
        """
        Parse SERP HTML and extract organic search results.
        
        Returns:
            Dictionary containing extracted results and metadata
        """
        start_time = time.time()
        
        # Initialize selector configurations
        self._primary_selectors = self._get_primary_selectors()
        self.fallback_selectors = self._get_fallback_selectors() 
        self.xpath_selectors = self._get_xpath_selectors()
        
        # Performance tracking
        self.selector_performance: Dict[str, SelectorPerformance] = {}
        self._initialize_performance_tracking()
        
        logger.info(f"Starting SERP parsing for query: '{self.query}' (page {self.page_number})")
        
        try:
            # Get HTML content
            html_content = self._get_html_content()
            if not html_content:
                return self._create_error_result("No HTML content provided")
            
            # Parse HTML with BeautifulSoup
            soup = self._parse_html(html_content)
            if not soup:
                return self._create_error_result("Failed to parse HTML content")
            
            # Analyze SERP structure
            serp_analysis = self._analyze_serp_structure(soup)
            
            # Extract results using adaptive strategy
            if self.selector_mode == "adaptive":
                results = self._extract_results_adaptive(soup)
            elif self.selector_mode == "primary":
                results = self._extract_results_primary(soup)
            elif self.selector_mode == "fallback":
                results = self._extract_results_fallback(soup)
            elif self.selector_mode == "xpath":
                results = self._extract_results_xpath(soup)
            else:
                results = self._extract_results_adaptive(soup)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Generate performance statistics
            performance_stats = self._generate_performance_stats()
            
            logger.info(f"SERP parsing completed: {len(results)} results extracted in {processing_time:.2f}s")
            
            return {
                "success": True,
                "query": self.query,
                "page_number": self.page_number,
                "results_count": len(results),
                "processing_time_seconds": processing_time,
                "results": [asdict(result) for result in results],
                "serp_analysis": serp_analysis,
                "performance_stats": performance_stats,
                "metadata": {
                    "html_length": len(html_content),
                    "selector_mode": self.selector_mode,
                    "extract_metadata": self.extract_metadata,
                    "timestamp": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"SERP parsing failed: {str(e)}")
            return self._create_error_result(str(e))
    
    def _get_html_content(self) -> Optional[str]:
        """Get HTML content from parameter or file"""
        if self.html_content:
            return self.html_content
        
        if self.html_file_path:
            try:
                file_path = Path(self.html_file_path)
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    logger.error(f"HTML file not found: {self.html_file_path}")
            except Exception as e:
                logger.error(f"Failed to read HTML file: {e}")
        
        return None
    
    def _parse_html(self, html_content: str) -> Optional[BeautifulSoup]:
        """Parse HTML content with error recovery"""
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup4 not available for HTML parsing")
            return None
        
        try:
            # Try with lxml parser first (fastest and most robust)
            if LXML_AVAILABLE:
                soup = BeautifulSoup(html_content, 'lxml')
                logger.debug("Parsed HTML with lxml parser")
                return soup
        except Exception as e:
            logger.warning(f"lxml parsing failed: {e}")
        
        try:
            # Fall back to html.parser (built-in)
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.debug("Parsed HTML with html.parser")
            return soup
        except Exception as e:
            logger.error(f"HTML parsing failed with html.parser: {e}")
        
        return None
    
    def _analyze_serp_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze SERP structure and layout"""
        analysis = {
            "has_results": False,
            "has_ads": False,
            "has_knowledge_panel": False,
            "has_pagination": False,
            "result_count_estimate": 0,
            "layout_type": "unknown"
        }
        
        try:
            # Check for main results container
            results_container = soup.select_one(self._primary_selectors["results_container"])
            if not results_container:
                results_container = soup.select_one(self.fallback_selectors["results_container"])
            
            analysis["has_results"] = results_container is not None
            
            if results_container:
                # Estimate result count
                organic_results = results_container.select(self._primary_selectors["organic_result"])
                if not organic_results:
                    organic_results = results_container.select(self.fallback_selectors["organic_result"])
                
                analysis["result_count_estimate"] = len(organic_results)
                
                # Determine layout type
                if len(organic_results) > 0:
                    analysis["layout_type"] = "standard"
                elif soup.select_one(".b_no"):
                    analysis["layout_type"] = "no_results"
                else:
                    analysis["layout_type"] = "unknown"
            
            # Check for ads
            ads_container = soup.select_one(self._primary_selectors["ads_container"])
            if not ads_container:
                ads_container = soup.select_one(self.fallback_selectors["ads_container"])
            analysis["has_ads"] = ads_container is not None
            
            # Check for knowledge panel
            knowledge_panel = soup.select_one(self._primary_selectors["knowledge_panel"])
            if not knowledge_panel:
                knowledge_panel = soup.select_one(self.fallback_selectors["knowledge_panel"])
            analysis["has_knowledge_panel"] = knowledge_panel is not None
            
            # Check for pagination
            pagination = soup.select_one(self._primary_selectors["pagination"])
            if not pagination:
                pagination = soup.select_one(self.fallback_selectors["pagination"])
            analysis["has_pagination"] = pagination is not None
            
        except Exception as e:
            logger.warning(f"SERP structure analysis failed: {e}")
        
        return analysis
    
    def _extract_results_adaptive(self, soup: BeautifulSoup) -> List[ExtractedResult]:
        """Extract results using adaptive selector strategy"""
        # Try primary selectors first
        results = self._extract_results_primary(soup)
        
        # If insufficient results, try fallback selectors
        if len(results) < 3:
            logger.info("Primary selectors yielded few results, trying fallback selectors")
            fallback_results = self._extract_results_fallback(soup)
            
            # Use fallback results if they're significantly better
            if len(fallback_results) > len(results) * 1.5:
                results = fallback_results
        
        # If still insufficient, try XPath selectors
        if len(results) < 2:
            logger.info("Fallback selectors insufficient, trying XPath selectors")
            xpath_results = self._extract_results_xpath(soup)
            
            if len(xpath_results) > len(results):
                results = xpath_results
        
        return results
    
    def _extract_results_primary(self, soup: BeautifulSoup) -> List[ExtractedResult]:
        """Extract results using primary selectors"""
        return self._extract_results_with_selectors(soup, self._primary_selectors, "primary")
    
    def _extract_results_fallback(self, soup: BeautifulSoup) -> List[ExtractedResult]:
        """Extract results using fallback selectors"""
        return self._extract_results_with_selectors(soup, self.fallback_selectors, "fallback")
    
    def _extract_results_xpath(self, soup: BeautifulSoup) -> List[ExtractedResult]:
        """Extract results using XPath selectors"""
        results = []
        
        try:
            # Get all result links using XPath
            links = soup.select("a[href]")  # Simplified for BeautifulSoup
            
            position = (self.page_number - 1) * 10 + 1
            
            for link in links:
                try:
                    # Skip non-result links
                    href = link.get('href', '')
                    if not self._is_organic_result_url(href):
                        continue
                    
                    # Extract title
                    title = self._extract_element_text(link)
                    if not title:
                        # Try parent elements for title
                        parent = link.parent
                        while parent and not title:
                            if parent.name in ['h2', 'h3']:
                                title = self._extract_element_text(parent)
                                break
                            parent = parent.parent
                    
                    # Extract snippet from nearby elements
                    snippet = self._extract_snippet_for_link(link)
                    
                    # Create result
                    result = ExtractedResult(
                        url=href,
                        title=title or "No title",
                        snippet=snippet or "No snippet",
                        position=position,
                        domain="",  # Will be set in __post_init__
                        original_url=href,
                        selector_used="xpath",
                        metadata={
                            "extraction_method": "xpath_fallback"
                        }
                    )
                    
                    results.append(result)
                    position += 1
                    
                    # Limit results per page
                    if len(results) >= 20:
                        break
                        
                except Exception as e:
                    logger.debug(f"Error extracting XPath result: {e}")
                    continue
            
            # Update performance tracking
            perf = self.selector_performance.get("xpath_result_links")
            if perf:
                perf.total_attempts += 1
                if results:
                    perf.success_count += 1
                    perf.average_results = ((perf.average_results or 0) * (perf.success_count - 1) + len(results)) / perf.success_count
                perf.last_used = time.time()
            
        except Exception as e:
            logger.error(f"XPath extraction failed: {e}")
        
        return results
    
    def _extract_results_with_selectors(self, soup: BeautifulSoup, selectors: Dict[str, str], selector_type: str) -> List[ExtractedResult]:
        """Extract results using specified selector set"""
        results = []
        
        try:
            # Find results container
            container = soup.select_one(selectors["results_container"])
            if not container:
                logger.debug(f"No results container found with {selector_type} selectors")
                return results
            
            # Find organic results
            organic_results = container.select(selectors["organic_result"])
            if not organic_results:
                logger.debug(f"No organic results found with {selector_type} selectors")
                return results
            
            logger.debug(f"Found {len(organic_results)} organic results with {selector_type} selectors")
            
            # Extract data from each result
            position = (self.page_number - 1) * 10 + 1
            
            for result_element in organic_results:
                try:
                    result = self._extract_single_result(result_element, selectors, position, selector_type)
                    if result:
                        results.append(result)
                        position += 1
                except Exception as e:
                    logger.debug(f"Error extracting single result: {e}")
                    continue
            
            # Update performance tracking
            perf_key = f"{selector_type}_organic_result"
            perf = self.selector_performance.get(perf_key)
            if perf:
                perf.total_attempts += 1
                if results:
                    perf.success_count += 1
                    perf.average_results = ((perf.average_results or 0) * (perf.success_count - 1) + len(results)) / perf.success_count
                perf.last_used = time.time()
            
        except Exception as e:
            logger.error(f"Result extraction failed with {selector_type} selectors: {e}")
        
        return results
    
    def _extract_single_result(self, element: Tag, selectors: Dict[str, str], position: int, selector_type: str) -> Optional[ExtractedResult]:
        """Extract data from a single result element"""
        try:
            # Extract URL
            link_element = element.select_one(selectors["result_link"])
            if not link_element:
                return None
            
            url = link_element.get('href', '')
            if not url or not self._is_organic_result_url(url):
                return None
            
            # Extract title
            title_element = element.select_one(selectors["result_title"])
            title = self._extract_element_text(title_element) if title_element else "No title"
            
            # Extract snippet
            snippet_element = element.select_one(selectors["result_snippet"])
            snippet = self._extract_element_text(snippet_element) if snippet_element else "No snippet"
            
            # Additional metadata if requested
            metadata = {}
            if self.extract_metadata:
                metadata.update({
                    "has_thumbnail": bool(element.select_one("img")),
                    "has_sitelinks": bool(element.select(".b_deep, .sitelink")),
                    "element_classes": element.get('class', [])
                })
            
            return ExtractedResult(
                url=url,
                title=title,
                snippet=snippet,
                position=position,
                domain="",  # Will be set in __post_init__
                original_url=url,
                selector_used=selector_type,
                metadata=metadata
            )
            
        except Exception as e:
            logger.debug(f"Error extracting single result: {e}")
            return None
    
    def _is_organic_result_url(self, url: str) -> bool:
        """Check if URL is a valid organic result URL"""
        if not url:
            return False
        
        # Skip internal Bing URLs and ads
        if any(pattern in url.lower() for pattern in [
            'bing.com/search',
            'bing.com/aclick',
            'bing.com/acjk',
            'msn.com',
            'microsoft.com',
            'javascript:',
            '#',
            'mailto:'
        ]):
            return False
        
        # Must start with http or be a Bing redirect
        if not (url.startswith('http') or url.startswith('//')):
            return False
        
        return True
    
    def _extract_element_text(self, element: Optional[Tag]) -> str:
        """Extract clean text from an element"""
        if not element:
            return ""
        
        try:
            # Get text and clean it
            text = element.get_text(strip=True)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove common prefixes/suffixes
            text = re.sub(r'^(Ad\s*)?·?\s*', '', text)
            text = re.sub(r'\s*·?\s*$', '', text)
            
            return text.strip()
            
        except Exception:
            return ""
    
    def _extract_snippet_for_link(self, link: Tag) -> str:
        """Extract snippet text for a given link element"""
        try:
            # Look for snippet in parent/sibling elements
            current = link.parent
            for _ in range(3):  # Search up to 3 levels
                if not current:
                    break
                
                # Look for snippet-like elements
                snippet_candidates = current.select("p, .snippet, .description, .b_caption")
                for candidate in snippet_candidates:
                    text = self._extract_element_text(candidate)
                    if len(text) > 20:  # Reasonable snippet length
                        return text
                
                current = current.parent
            
            return ""
            
        except Exception:
            return ""
    
    def _generate_performance_stats(self) -> Dict[str, Any]:
        """Generate performance statistics for selectors"""
        stats = {
            "selector_performance": {},
            "overall_stats": {
                "total_selectors": len(self.selector_performance),
                "successful_selectors": 0,
                "average_success_rate": 0.0
            }
        }
        
        total_success_rate = 0.0
        successful_count = 0
        
        for selector_name, perf in self.selector_performance.items():
            selector_stats = {
                "success_rate": perf.success_rate,
                "total_attempts": perf.total_attempts,
                "success_count": perf.success_count,
                "average_results": perf.average_results,
                "last_used": perf.last_used
            }
            
            stats["selector_performance"][selector_name] = selector_stats
            
            if perf.success_rate > 0:
                total_success_rate += perf.success_rate
                successful_count += 1
        
        if successful_count > 0:
            stats["overall_stats"]["successful_selectors"] = successful_count
            stats["overall_stats"]["average_success_rate"] = total_success_rate / successful_count
        
        return stats
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            "success": False,
            "query": self.query,
            "page_number": self.page_number,
            "results_count": 0,
            "processing_time_seconds": 0,
            "error": error_message,
            "results": [],
            "serp_analysis": {},
            "performance_stats": {},
            "metadata": {
                "html_length": 0,
                "selector_mode": self.selector_mode,
                "timestamp": time.time()
            }
        }