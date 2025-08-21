"""
Business Filter Tool for Agency Swarm

Tool for filtering URLs to identify legitimate business websites
and exclude social media, directories, and non-business domains.
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, asdict

from agency_swarm.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


@dataclass
class FilteredUrl:
    """Represents a URL with filtering metadata"""
    url: str
    domain: str
    is_business: bool
    confidence_score: float
    filter_reasons: List[str]
    business_indicators: List[str]
    website_type: Optional[str] = None
    industry_hints: List[str] = None
    
    def __post_init__(self):
        if self.industry_hints is None:
            self.industry_hints = []


@dataclass
class FilteringStats:
    """Statistics about the filtering process"""
    total_urls: int = 0
    business_urls: int = 0
    filtered_urls: int = 0
    social_media_filtered: int = 0
    directory_filtered: int = 0
    news_media_filtered: int = 0
    government_filtered: int = 0
    platform_filtered: int = 0
    duplicate_domains: int = 0
    average_confidence: float = 0.0


class BusinessFilterTool(BaseTool):
    """
    Tool for filtering URLs to identify legitimate business websites.
    
    This tool handles:
    - Social media platform detection and exclusion
    - Directory site filtering (Yelp, Yellow Pages, etc.)
    - News and media site identification
    - Government and educational domain filtering
    - Generic platform detection (WordPress.com, Wix, etc.)
    - Business keyword analysis and scoring
    - Domain deduplication with ranking preservation
    - Confidence scoring for business likelihood
    """
    
    urls: List[str] = Field(
        ...,
        description="List of URLs to filter for business relevance"
    )
    
    exclude_social_media: bool = Field(
        default=True,
        description="Whether to exclude social media platforms"
    )
    
    exclude_directories: bool = Field(
        default=True,
        description="Whether to exclude directory sites"
    )
    
    exclude_news_media: bool = Field(
        default=True,
        description="Whether to exclude news and media sites"
    )
    
    exclude_government: bool = Field(
        default=True,
        description="Whether to exclude government and educational sites"
    )
    
    exclude_platforms: bool = Field(
        default=True,
        description="Whether to exclude generic platforms"
    )
    
    minimum_confidence: float = Field(
        default=0.3,
        description="Minimum confidence score to include URL (0.0-1.0)"
    )
    
    deduplicate_domains: bool = Field(
        default=True,
        description="Whether to deduplicate by domain"
    )
    
    preserve_ranking: bool = Field(
        default=True,
        description="Whether to preserve original ranking when deduplicating"
    )
    
    custom_exclude_domains: Optional[List[str]] = Field(
        default=None,
        description="Additional domains to exclude"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _initialize_filter_rules(self):
        """Initialize all filtering rules and patterns"""
        
        # Social media platforms
        self.social_media_domains = {
            'facebook.com', 'linkedin.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'tiktok.com', 'snapchat.com', 'pinterest.com',
            'reddit.com', 'tumblr.com', 'flickr.com', 'vimeo.com',
            'medium.com', 'quora.com', 'discord.com', 'telegram.org',
            'whatsapp.com', 'wechat.com', 'line.me', 'skype.com'
        }
        
        # Directory and review sites
        self.directory_domains = {
            'yelp.com', 'yellowpages.com', 'bbb.org', 'foursquare.com',
            'tripadvisor.com', 'glassdoor.com', 'indeed.com', 'zomato.com',
            'opentable.com', 'booking.com', 'expedia.com', 'hotels.com',
            'airbnb.com', 'vrbo.com', 'homeaway.com', 'angie.com',
            'thumbtack.com', 'houzz.com', 'citysearch.com', 'superpages.com',
            'whitepages.com', 'spokeo.com', 'trulia.com', 'zillow.com'
        }
        
        # News and media sites
        self.news_media_domains = {
            'cnn.com', 'bbc.com', 'reuters.com', 'ap.org', 'nytimes.com',
            'washingtonpost.com', 'wsj.com', 'ft.com', 'bloomberg.com',
            'forbes.com', 'time.com', 'newsweek.com', 'npr.org',
            'cbsnews.com', 'abcnews.go.com', 'nbcnews.com', 'foxnews.com',
            'usatoday.com', 'latimes.com', 'chicagotribune.com', 'nypost.com',
            'theguardian.com', 'independent.co.uk', 'dailymail.co.uk'
        }
        
        # Generic platforms
        self.platform_domains = {
            'wordpress.com', 'blogspot.com', 'wix.com', 'squarespace.com',
            'weebly.com', 'jimdo.com', 'site123.com', 'webnode.com',
            'strikingly.com', 'carrd.co', 'tilda.cc', 'webflow.com',
            'ghost.org', 'substack.com', 'notion.so', 'airtable.com'
        }
        
        # Government and educational TLD patterns
        self.gov_edu_patterns = [
            re.compile(r'\.gov$', re.IGNORECASE),
            re.compile(r'\.edu$', re.IGNORECASE),
            re.compile(r'\.mil$', re.IGNORECASE),
            re.compile(r'\.ac\.[a-z]{2}$', re.IGNORECASE),
            re.compile(r'\.gov\.[a-z]{2}$', re.IGNORECASE),
            re.compile(r'\.edu\.[a-z]{2}$', re.IGNORECASE)
        ]
        
        # News/media patterns in domain or path
        self.news_patterns = [
            re.compile(r'\b(news|media|press|journal|magazine|newspaper|blog|post)\b', re.IGNORECASE),
            re.compile(r'\b(article|story|report|coverage|breaking)\b', re.IGNORECASE)
        ]
        
        # Directory patterns
        self.directory_patterns = [
            re.compile(r'\b(directory|listing|review|rating|map|local|find)\b', re.IGNORECASE),
            re.compile(r'\b(search|browse|discover|explore)\b', re.IGNORECASE)
        ]
        
        # Business keywords (positive indicators)
        self.business_keywords = {
            'company', 'business', 'services', 'solutions', 'professional',
            'commercial', 'enterprise', 'corporation', 'firm', 'agency',
            'consulting', 'contractor', 'supplier', 'manufacturer', 'provider',
            'office', 'headquarters', 'contact', 'about', 'team', 'staff'
        }
        
        # Industry-specific keywords
        self.industry_keywords = {
            'technology': ['tech', 'software', 'development', 'programming', 'IT', 'digital'],
            'healthcare': ['medical', 'health', 'doctor', 'clinic', 'hospital', 'dental'],
            'legal': ['law', 'attorney', 'lawyer', 'legal', 'firm', 'counsel'],
            'finance': ['financial', 'accounting', 'investment', 'banking', 'insurance'],
            'real_estate': ['property', 'real estate', 'realtor', 'homes', 'commercial'],
            'construction': ['construction', 'building', 'contractor', 'renovation'],
            'automotive': ['auto', 'car', 'vehicle', 'automotive', 'repair', 'service'],
            'retail': ['store', 'shop', 'retail', 'merchandise', 'products'],
            'restaurant': ['restaurant', 'cafe', 'food', 'dining', 'catering'],
            'education': ['training', 'course', 'education', 'learning', 'academy']
        }
        
        # Commercial TLDs (positive indicators)
        self.commercial_tlds = {
            '.com', '.net', '.biz', '.co', '.io', '.ai', '.tech', '.pro',
            '.store', '.shop', '.business', '.company', '.services'
        }
    
    def run(self) -> Dict[str, Any]:
        """
        Filter URLs for business relevance and generate filtering statistics.
        
        Returns:
            Dictionary containing filtered URLs and comprehensive statistics
        """
        start_time = time.time()
        
        # Initialize filtering rules
        self._initialize_filter_rules()
        
        logger.info(f"Starting business filtering for {len(self.urls)} URLs")
        
        # Initialize statistics
        stats = FilteringStats(total_urls=len(self.urls))
        
        # Process each URL
        filtered_results = []
        domain_seen = set()
        
        for i, url in enumerate(self.urls):
            try:
                # Parse URL and extract domain
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Check for domain deduplication
                if self.deduplicate_domains and domain in domain_seen:
                    stats.duplicate_domains += 1
                    logger.debug(f"Skipping duplicate domain: {domain}")
                    continue
                
                # Filter the URL
                filtered_url = self._filter_single_url(url, domain, i + 1)
                
                # Apply confidence threshold
                if filtered_url.confidence_score >= self.minimum_confidence:
                    filtered_results.append(filtered_url)
                    domain_seen.add(domain)
                    
                    if filtered_url.is_business:
                        stats.business_urls += 1
                    else:
                        stats.filtered_urls += 1
                        self._update_filter_stats(stats, filtered_url.filter_reasons)
                else:
                    stats.filtered_urls += 1
                    logger.debug(f"URL filtered due to low confidence: {url} (score: {filtered_url.confidence_score:.2f})")
                
            except Exception as e:
                logger.error(f"Error filtering URL '{url}': {e}")
                # Create error result
                error_result = FilteredUrl(
                    url=url,
                    domain="unknown",
                    is_business=False,
                    confidence_score=0.0,
                    filter_reasons=[f"processing_error: {str(e)}"],
                    business_indicators=[]
                )
                filtered_results.append(error_result)
                stats.filtered_urls += 1
        
        # Calculate final statistics
        if stats.business_urls > 0:
            stats.average_confidence = sum(
                result.confidence_score for result in filtered_results 
                if result.is_business
            ) / stats.business_urls
        
        processing_time = time.time() - start_time
        
        logger.info(f"Business filtering completed: {stats.business_urls} business URLs identified "
                   f"from {stats.total_urls} total URLs in {processing_time:.2f}s")
        
        return {
            "success": True,
            "total_urls": stats.total_urls,
            "business_urls": stats.business_urls,
            "filtered_urls": stats.filtered_urls,
            "processing_time_seconds": processing_time,
            "statistics": asdict(stats),
            "filtered_results": [asdict(result) for result in filtered_results],
            "business_urls_only": [result.url for result in filtered_results if result.is_business],
            "filter_summary": {
                "business_rate": stats.business_urls / stats.total_urls if stats.total_urls > 0 else 0,
                "filter_rate": stats.filtered_urls / stats.total_urls if stats.total_urls > 0 else 0,
                "average_confidence": stats.average_confidence
            }
        }
    
    def _filter_single_url(self, url: str, domain: str, position: int) -> FilteredUrl:
        """Filter a single URL and determine business relevance"""
        filter_reasons = []
        business_indicators = []
        confidence_score = 0.5  # Start with neutral confidence
        website_type = None
        industry_hints = []
        
        # Check exclusion rules
        is_excluded = False
        
        # 1. Social media check
        if self.exclude_social_media and self._is_social_media(domain, url):
            is_excluded = True
            filter_reasons.append("social_media")
            website_type = "social_media"
            confidence_score = 0.0
        
        # 2. Directory check
        elif self.exclude_directories and self._is_directory_site(domain, url):
            is_excluded = True
            filter_reasons.append("directory_site")
            website_type = "directory"
            confidence_score = 0.1
        
        # 3. News/media check
        elif self.exclude_news_media and self._is_news_media(domain, url):
            is_excluded = True
            filter_reasons.append("news_media")
            website_type = "news_media"
            confidence_score = 0.2
        
        # 4. Government/education check
        elif self.exclude_government and self._is_government_edu(domain):
            is_excluded = True
            filter_reasons.append("government_edu")
            website_type = "government_edu"
            confidence_score = 0.1
        
        # 5. Platform check
        elif self.exclude_platforms and self._is_generic_platform(domain):
            is_excluded = True
            filter_reasons.append("generic_platform")
            website_type = "platform"
            confidence_score = 0.3
        
        # 6. Custom exclude domains
        elif self.custom_exclude_domains and domain in self.custom_exclude_domains:
            is_excluded = True
            filter_reasons.append("custom_excluded")
            confidence_score = 0.0
        
        # If not excluded, analyze for business indicators
        if not is_excluded:
            confidence_score, business_indicators, industry_hints = self._analyze_business_indicators(url, domain)
            website_type = "business" if confidence_score >= self.minimum_confidence else "unknown"
        
        return FilteredUrl(
            url=url,
            domain=domain,
            is_business=not is_excluded and confidence_score >= self.minimum_confidence,
            confidence_score=confidence_score,
            filter_reasons=filter_reasons,
            business_indicators=business_indicators,
            website_type=website_type,
            industry_hints=industry_hints
        )
    
    def _is_social_media(self, domain: str, url: str) -> bool:
        """Check if domain is a social media platform"""
        return domain in self.social_media_domains
    
    def _is_directory_site(self, domain: str, url: str) -> bool:
        """Check if domain is a directory or review site"""
        if domain in self.directory_domains:
            return True
        
        # Check for directory patterns in URL
        for pattern in self.directory_patterns:
            if pattern.search(url):
                return True
        
        return False
    
    def _is_news_media(self, domain: str, url: str) -> bool:
        """Check if domain is a news or media site"""
        if domain in self.news_media_domains:
            return True
        
        # Check for news patterns in domain or URL
        for pattern in self.news_patterns:
            if pattern.search(url):
                return True
        
        return False
    
    def _is_government_edu(self, domain: str) -> bool:
        """Check if domain is government or educational"""
        for pattern in self.gov_edu_patterns:
            if pattern.search(domain):
                return True
        
        return False
    
    def _is_generic_platform(self, domain: str) -> bool:
        """Check if domain is a generic platform"""
        return domain in self.platform_domains
    
    def _analyze_business_indicators(self, url: str, domain: str) -> Tuple[float, List[str], List[str]]:
        """Analyze URL for business indicators and calculate confidence score"""
        indicators = []
        industry_hints = []
        score = 0.5  # Start with neutral
        
        url_lower = url.lower()
        domain_lower = domain.lower()
        
        # Check for business keywords in URL
        business_keyword_count = 0
        for keyword in self.business_keywords:
            if keyword in url_lower:
                indicators.append(f"business_keyword: {keyword}")
                business_keyword_count += 1
        
        # Score based on business keywords
        if business_keyword_count > 0:
            score += min(business_keyword_count * 0.1, 0.3)
        
        # Check for industry keywords and hints
        for industry, keywords in self.industry_keywords.items():
            industry_match_count = 0
            for keyword in keywords:
                if keyword in url_lower:
                    industry_match_count += 1
            
            if industry_match_count > 0:
                industry_hints.append(industry)
                indicators.append(f"industry_hint: {industry}")
                score += min(industry_match_count * 0.05, 0.15)
        
        # Check TLD (commercial TLDs are positive indicators)
        for tld in self.commercial_tlds:
            if domain_lower.endswith(tld):
                indicators.append(f"commercial_tld: {tld}")
                score += 0.1
                break
        
        # Check for contact/about pages (strong business indicators)
        contact_indicators = ['contact', 'about', 'team', 'staff', 'office']
        for indicator in contact_indicators:
            if indicator in url_lower:
                indicators.append(f"contact_page: {indicator}")
                score += 0.15
        
        # Check for services/products pages
        commercial_indicators = ['services', 'products', 'solutions', 'pricing', 'shop', 'store']
        for indicator in commercial_indicators:
            if indicator in url_lower:
                indicators.append(f"commercial_page: {indicator}")
                score += 0.1
        
        # Domain length heuristic (very short domains often corporate)
        if len(domain_lower.split('.')[0]) < 8 and not any(char.isdigit() for char in domain_lower):
            indicators.append("short_domain")
            score += 0.05
        
        # Penalize certain patterns
        penalty_patterns = ['blog', 'personal', 'portfolio', 'resume', 'cv']
        for pattern in penalty_patterns:
            if pattern in url_lower:
                indicators.append(f"penalty: {pattern}")
                score -= 0.1
        
        # Ensure score stays within bounds
        score = max(0.0, min(1.0, score))
        
        return score, indicators, industry_hints
    
    def _update_filter_stats(self, stats: FilteringStats, filter_reasons: List[str]):
        """Update filtering statistics based on filter reasons"""
        for reason in filter_reasons:
            if reason == "social_media":
                stats.social_media_filtered += 1
            elif reason == "directory_site":
                stats.directory_filtered += 1
            elif reason == "news_media":
                stats.news_media_filtered += 1
            elif reason == "government_edu":
                stats.government_filtered += 1
            elif reason == "generic_platform":
                stats.platform_filtered += 1