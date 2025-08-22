"""
Business Website Scoring Tool for Agency Swarm

Tool for analyzing and scoring websites based on business indicators.
Scores domains for business legitimacy, contact potential, and site quality.
"""

import logging
import time
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    from agency_swarm.tools import BaseTool
    from pydantic import Field
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class Field:
        def __init__(self, *args, **kwargs):
            pass

# Import the domain classifier components
try:
    from agents.domain_classifier_agent import WebsiteType, PlatformType, DomainMetadata
except ImportError:
    # Fallback if import fails
    class WebsiteType(Enum):
        BUSINESS = "business"
        PERSONAL = "personal"
        BLOG = "blog"
        ECOMMERCE = "ecommerce"
        PORTFOLIO = "portfolio"
        NEWS_MEDIA = "news_media"
        SOCIAL_MEDIA = "social_media"
        DIRECTORY = "directory"
        GOVERNMENT = "government"
        EDUCATIONAL = "educational"
        NONPROFIT = "nonprofit"
        PLATFORM = "platform"
        UNKNOWN = "unknown"
    
    class PlatformType(Enum):
        WORDPRESS = "wordpress"
        SHOPIFY = "shopify"
        WIX = "wix"
        SQUARESPACE = "squarespace"
        CUSTOM = "custom"
        UNKNOWN = "unknown"

logger = logging.getLogger(__name__)


@dataclass
class BusinessIndicator:
    """Definition of a business scoring indicator"""
    name: str
    description: str
    weight: float  # 0.0 to 1.0
    positive_score: float  # Score to add if indicator is found
    negative_score: float = 0.0  # Score to subtract if indicator is found
    
    # Detection patterns
    url_patterns: List[str] = field(default_factory=list)
    content_patterns: List[str] = field(default_factory=list)
    meta_patterns: List[str] = field(default_factory=list)
    title_patterns: List[str] = field(default_factory=list)
    
    # Contextual rules
    domain_extensions: List[str] = field(default_factory=list)
    platform_boost: Dict[str, float] = field(default_factory=dict)  # Platform-specific score multipliers
    required_matches: int = 1  # Minimum matches needed to trigger
    
    def calculate_score(self, matches: int, platform: str = "unknown") -> float:
        """Calculate the score contribution of this indicator"""
        if matches < self.required_matches:
            return 0.0
        
        base_score = self.positive_score - self.negative_score
        
        # Apply platform boost if applicable
        platform_multiplier = self.platform_boost.get(platform, 1.0)
        
        # Weight by number of matches (diminishing returns)
        match_multiplier = min(2.0, 1.0 + (matches - 1) * 0.1)
        
        return base_score * self.weight * platform_multiplier * match_multiplier


@dataclass
class ScoringResult:
    """Result of business scoring for a domain"""
    domain: str
    business_score: float
    confidence: float
    website_type: WebsiteType
    
    # Scoring breakdown
    total_indicators: int = 0
    positive_indicators: List[str] = field(default_factory=list)
    negative_indicators: List[str] = field(default_factory=list)
    scoring_details: Dict[str, float] = field(default_factory=dict)
    
    # Content analysis results
    has_contact_info: bool = False
    has_business_keywords: bool = False
    has_services_keywords: bool = False
    has_pricing_info: bool = False
    has_address_info: bool = False
    
    # Quality indicators
    content_quality_score: float = 0.0
    site_completeness_score: float = 0.0
    professionalism_score: float = 0.0
    
    # Technical indicators
    platform_type: str = "unknown"
    response_time_ms: float = 0.0
    status_code: Optional[int] = None
    error: Optional[str] = None
    
    def calculate_confidence(self) -> float:
        """Calculate confidence score based on number and quality of indicators"""
        if self.total_indicators == 0:
            return 0.0
        
        # Base confidence from indicator count
        indicator_confidence = min(1.0, self.total_indicators / 10.0)
        
        # Boost confidence for specific high-value indicators
        high_value_boost = 0.0
        if self.has_contact_info:
            high_value_boost += 0.2
        if self.has_address_info:
            high_value_boost += 0.15
        if self.has_pricing_info:
            high_value_boost += 0.1
        
        # Quality score boost
        quality_boost = (self.content_quality_score + self.professionalism_score) / 2.0 * 0.3
        
        return min(1.0, indicator_confidence + high_value_boost + quality_boost)


class BusinessScorer:
    """
    Core business scoring engine that analyzes website characteristics
    to determine business legitimacy and contact potential
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Scoring configuration
        self.business_threshold = self.config.get("business_threshold", 0.6)
        self.high_confidence_threshold = self.config.get("high_confidence_threshold", 0.8)
        self.content_analysis_enabled = self.config.get("content_analysis_enabled", True)
        self.max_content_length = self.config.get("max_content_length", 100000)  # 100KB max
        
        # HTTP configuration
        self.timeout = self.config.get("timeout", 15)
        self.user_agent = self.config.get("user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Initialize business indicators
        self.indicators = self._initialize_business_indicators()
        
        # Statistics
        self.stats = {
            "total_scored": 0,
            "business_sites": 0,
            "personal_sites": 0,
            "average_score": 0.0,
            "high_confidence_predictions": 0
        }
        
        if not REQUESTS_AVAILABLE:
            self.logger.warning("Requests library not available - using mock mode")
        
        self.logger.info(f"BusinessScorer initialized with {len(self.indicators)} indicators")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the business scorer"""
        logger = logging.getLogger(f"{__name__}.BusinessScorer")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_business_indicators(self) -> List[BusinessIndicator]:
        """Initialize business scoring indicators"""
        indicators = []
        
        # Contact Information Indicators (high weight)
        indicators.append(BusinessIndicator(
            name="contact_forms",
            description="Contact forms and contact pages",
            weight=1.0,
            positive_score=15.0,
            content_patterns=[
                r"<form[^>]*contact[^>]*>",
                r"contact[_\s-]*form",
                r"get[_\s-]*in[_\s-]*touch",
                r"contact[_\s-]*us",
                r"reach[_\s-]*out",
                r"send[_\s-]*message"
            ],
            title_patterns=[
                r"contact\s+us",
                r"get\s+in\s+touch",
                r"contact\s+form"
            ],
            url_patterns=[
                r"/contact",
                r"/contact-us",
                r"/get-in-touch",
                r"/contact-form"
            ]
        ))
        
        indicators.append(BusinessIndicator(
            name="phone_numbers",
            description="Phone numbers and contact information",
            weight=0.9,
            positive_score=12.0,
            content_patterns=[
                r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}",  # (555) 123-4567
                r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}",   # 555-123-4567
                r"\+\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}",  # International
                r"tel:",
                r"phone:",
                r"call\s+us"
            ]
        ))
        
        indicators.append(BusinessIndicator(
            name="business_address",
            description="Physical business addresses",
            weight=0.9,
            positive_score=10.0,
            content_patterns=[
                r"\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)",
                r"address:",
                r"location:",
                r"visit\s+us",
                r"office\s+location",
                r"\d{5}[-\s]?\d{4}?"  # ZIP codes
            ]
        ))
        
        # Business Services Indicators
        indicators.append(BusinessIndicator(
            name="services_pages",
            description="Services and offerings pages",
            weight=0.8,
            positive_score=8.0,
            url_patterns=[
                r"/services",
                r"/what-we-do",
                r"/offerings",
                r"/solutions",
                r"/expertise"
            ],
            content_patterns=[
                r"our\s+services",
                r"what\s+we\s+do",
                r"services\s+offered",
                r"our\s+expertise",
                r"solutions\s+we\s+provide"
            ],
            title_patterns=[
                r"services",
                r"what\s+we\s+do",
                r"our\s+offerings"
            ]
        ))
        
        indicators.append(BusinessIndicator(
            name="pricing_information",
            description="Pricing and cost information",
            weight=0.7,
            positive_score=8.0,
            url_patterns=[
                r"/pricing",
                r"/rates",
                r"/cost",
                r"/packages",
                r"/plans"
            ],
            content_patterns=[
                r"pricing",
                r"rates",
                r"cost",
                r"\$\d+",
                r"price",
                r"packages",
                r"plans"
            ]
        ))
        
        # Professional Website Indicators
        indicators.append(BusinessIndicator(
            name="about_company",
            description="About us and company information",
            weight=0.6,
            positive_score=6.0,
            url_patterns=[
                r"/about",
                r"/about-us",
                r"/company",
                r"/who-we-are"
            ],
            content_patterns=[
                r"about\s+us",
                r"our\s+company",
                r"who\s+we\s+are",
                r"our\s+story",
                r"company\s+history"
            ]
        ))
        
        indicators.append(BusinessIndicator(
            name="team_pages",
            description="Team and staff pages",
            weight=0.5,
            positive_score=5.0,
            url_patterns=[
                r"/team",
                r"/staff",
                r"/people",
                r"/our-team"
            ],
            content_patterns=[
                r"our\s+team",
                r"meet\s+the\s+team",
                r"staff\s+members",
                r"team\s+members"
            ]
        ))
        
        # E-commerce Indicators
        indicators.append(BusinessIndicator(
            name="ecommerce_features",
            description="E-commerce and shopping features",
            weight=0.9,
            positive_score=12.0,
            content_patterns=[
                r"add\s+to\s+cart",
                r"shopping\s+cart",
                r"checkout",
                r"buy\s+now",
                r"purchase",
                r"shop\s+online",
                r"product\s+catalog"
            ],
            url_patterns=[
                r"/shop",
                r"/store",
                r"/products",
                r"/cart",
                r"/checkout"
            ],
            platform_boost={
                "shopify": 1.5,
                "woocommerce": 1.3,
                "magento": 1.4
            }
        ))
        
        # Professional Platform Indicators
        indicators.append(BusinessIndicator(
            name="wordpress_business_themes",
            description="WordPress business themes and plugins",
            weight=0.6,
            positive_score=6.0,
            content_patterns=[
                r"wp-content/themes/[^/]*business[^/]*",
                r"wp-content/themes/[^/]*corporate[^/]*",
                r"wp-content/themes/[^/]*professional[^/]*",
                r"wp-content/plugins/[^/]*business[^/]*",
                r"wp-content/plugins/[^/]*contact[^/]*"
            ],
            platform_boost={
                "wordpress": 1.2
            }
        ))
        
        # Business Keywords in Domain
        indicators.append(BusinessIndicator(
            name="business_domain_keywords",
            description="Business-related keywords in domain name",
            weight=0.4,
            positive_score=4.0,
            url_patterns=[
                r"(consulting|services|solutions|group|corp|company|llc|inc|ltd|professional|business|agency|firm)",
            ]
        ))
        
        # Negative Indicators (personal sites)
        indicators.append(BusinessIndicator(
            name="personal_indicators",
            description="Personal website indicators",
            weight=0.8,
            positive_score=0.0,
            negative_score=8.0,
            content_patterns=[
                r"my\s+blog",
                r"personal\s+blog",
                r"about\s+me",
                r"my\s+life",
                r"my\s+thoughts",
                r"personal\s+website"
            ],
            url_patterns=[
                r"/blog",
                r"/diary",
                r"/personal"
            ]
        ))
        
        indicators.append(BusinessIndicator(
            name="social_media_focus",
            description="Heavy social media focus indicating personal use",
            weight=0.6,
            positive_score=0.0,
            negative_score=5.0,
            content_patterns=[
                r"follow\s+me\s+on",
                r"my\s+instagram",
                r"my\s+twitter",
                r"personal\s+photos",
                r"vacation\s+photos"
            ]
        ))
        
        return indicators
    
    def score_domain(self, domain: str, platform_type: str = "unknown", 
                    existing_metadata: Optional[DomainMetadata] = None) -> ScoringResult:
        """
        Score a domain for business indicators
        
        Args:
            domain: Domain to score
            platform_type: Detected platform type
            existing_metadata: Existing domain metadata if available
            
        Returns:
            ScoringResult with business scoring information
        """
        start_time = time.time()
        
        result = ScoringResult(
            domain=domain,
            business_score=0.0,
            confidence=0.0,
            website_type=WebsiteType.UNKNOWN,
            platform_type=platform_type
        )
        
        if not REQUESTS_AVAILABLE:
            # Mock scoring for testing
            result.business_score = 0.5
            result.confidence = 0.5
            result.website_type = WebsiteType.BUSINESS
            result.error = "Requests library not available - mock result"
            return result
        
        try:
            self.logger.info(f"Starting business scoring for {domain}")
            
            # Get website content for analysis
            content = self._get_website_content(domain, result)
            
            if content and not result.error:
                # Analyze content for business indicators
                self._analyze_business_indicators(content, result)
                
                # Analyze domain name for business keywords
                self._analyze_domain_name(domain, result)
                
                # Calculate final scores
                self._calculate_final_scores(result)
                
                # Determine website type
                self._classify_website_type(result)
                
            response_time = (time.time() - start_time) * 1000
            result.response_time_ms = response_time
            
            # Update statistics
            self._update_statistics(result)
            
            self.logger.info(f"Business scoring completed for {domain}: "
                           f"score={result.business_score:.2f}, type={result.website_type.value}")
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Error scoring domain {domain}: {e}")
        
        return result
    
    def _get_website_content(self, domain: str, result: ScoringResult) -> Optional[str]:
        """Get website content for analysis"""
        try:
            # Prepare session
            session = requests.Session()
            session.headers.update({
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            })
            
            # Try HTTPS first, then HTTP
            urls_to_try = [f"https://{domain}", f"http://{domain}"]
            
            for url in urls_to_try:
                try:
                    response = session.get(url, timeout=self.timeout, allow_redirects=True)
                    result.status_code = response.status_code
                    
                    if response.status_code == 200:
                        content = response.text[:self.max_content_length]
                        return content
                        
                except Exception as e:
                    self.logger.debug(f"Failed to get content from {url}: {e}")
                    continue
            
            result.error = "Failed to retrieve website content"
            return None
            
        except Exception as e:
            result.error = f"Error retrieving content: {e}"
            return None
    
    def _analyze_business_indicators(self, content: str, result: ScoringResult):
        """Analyze website content for business indicators"""
        content_lower = content.lower()
        
        for indicator in self.indicators:
            matches = 0
            
            # Check content patterns
            for pattern in indicator.content_patterns:
                try:
                    if re.search(pattern, content_lower, re.IGNORECASE):
                        matches += 1
                except re.error:
                    self.logger.warning(f"Invalid regex pattern: {pattern}")
                    continue
            
            # Check title patterns
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).lower()
                for pattern in indicator.title_patterns:
                    try:
                        if re.search(pattern, title, re.IGNORECASE):
                            matches += 1
                    except re.error:
                        continue
            
            # Check meta patterns
            for pattern in indicator.meta_patterns:
                try:
                    if re.search(pattern, content, re.IGNORECASE):
                        matches += 1
                except re.error:
                    continue
            
            # Calculate score contribution
            if matches > 0:
                score_contribution = indicator.calculate_score(matches, result.platform_type)
                result.business_score += score_contribution
                result.scoring_details[indicator.name] = score_contribution
                result.total_indicators += 1
                
                if indicator.negative_score > 0:
                    result.negative_indicators.append(indicator.name)
                else:
                    result.positive_indicators.append(indicator.name)
                
                # Set specific flags
                if "contact" in indicator.name:
                    result.has_contact_info = True
                elif "address" in indicator.name:
                    result.has_address_info = True
                elif "pricing" in indicator.name:
                    result.has_pricing_info = True
                elif "services" in indicator.name:
                    result.has_services_keywords = True
        
        # Analyze content quality
        self._analyze_content_quality(content, result)
    
    def _analyze_domain_name(self, domain: str, result: ScoringResult):
        """Analyze domain name for business keywords"""
        domain_lower = domain.lower()
        
        for indicator in self.indicators:
            if not indicator.url_patterns:
                continue
            
            matches = 0
            for pattern in indicator.url_patterns:
                try:
                    if re.search(pattern, domain_lower, re.IGNORECASE):
                        matches += 1
                except re.error:
                    continue
            
            if matches > 0:
                score_contribution = indicator.calculate_score(matches, result.platform_type)
                result.business_score += score_contribution
                result.scoring_details[f"{indicator.name}_domain"] = score_contribution
                result.total_indicators += 1
                
                if indicator.negative_score > 0:
                    result.negative_indicators.append(f"{indicator.name}_domain")
                else:
                    result.positive_indicators.append(f"{indicator.name}_domain")
    
    def _analyze_content_quality(self, content: str, result: ScoringResult):
        """Analyze content quality indicators"""
        # Content length (reasonable amount of content)
        content_length = len(content.strip())
        if 1000 <= content_length <= 50000:
            result.content_quality_score += 0.3
        elif content_length > 50000:
            result.content_quality_score += 0.2
        
        # Check for structured content
        structured_elements = [
            r'<header[^>]*>',
            r'<nav[^>]*>',
            r'<footer[^>]*>',
            r'<article[^>]*>',
            r'<section[^>]*>'
        ]
        
        structure_score = 0
        for element in structured_elements:
            if re.search(element, content, re.IGNORECASE):
                structure_score += 0.1
        
        result.content_quality_score += min(0.3, structure_score)
        
        # Check for professional language indicators
        professional_indicators = [
            r'privacy\s+policy',
            r'terms\s+of\s+service',
            r'copyright',
            r'all\s+rights\s+reserved',
            r'professional',
            r'experienced',
            r'certified'
        ]
        
        prof_score = 0
        for indicator in professional_indicators:
            if re.search(indicator, content, re.IGNORECASE):
                prof_score += 0.05
        
        result.professionalism_score = min(1.0, prof_score)
        
        # Site completeness (multiple pages/sections)
        completeness_indicators = [
            r'<a\s+href="[^"]*about[^"]*"',
            r'<a\s+href="[^"]*contact[^"]*"',
            r'<a\s+href="[^"]*services[^"]*"',
            r'<a\s+href="[^"]*products[^"]*"'
        ]
        
        completeness_score = 0
        for indicator in completeness_indicators:
            if re.search(indicator, content, re.IGNORECASE):
                completeness_score += 0.2
        
        result.site_completeness_score = min(1.0, completeness_score)
    
    def _calculate_final_scores(self, result: ScoringResult):
        """Calculate final business score and confidence"""
        # Normalize business score (cap at reasonable maximum)
        max_possible_score = 100.0
        result.business_score = min(1.0, max(0.0, result.business_score / max_possible_score))
        
        # Add quality bonuses
        quality_bonus = (result.content_quality_score + result.professionalism_score + 
                        result.site_completeness_score) / 3.0 * 0.2
        
        result.business_score = min(1.0, result.business_score + quality_bonus)
        
        # Calculate confidence
        result.confidence = result.calculate_confidence()
    
    def _classify_website_type(self, result: ScoringResult):
        """Classify website type based on scoring results"""
        # E-commerce sites
        if "ecommerce_features" in result.positive_indicators:
            result.website_type = WebsiteType.ECOMMERCE
        # High business score
        elif result.business_score >= self.business_threshold:
            result.website_type = WebsiteType.BUSINESS
        # Personal site indicators
        elif any("personal" in indicator for indicator in result.negative_indicators):
            result.website_type = WebsiteType.PERSONAL
        # Blog indicators
        elif result.has_services_keywords and not result.has_contact_info:
            result.website_type = WebsiteType.BLOG
        # Low business score
        elif result.business_score < 0.3:
            result.website_type = WebsiteType.PERSONAL
        else:
            result.website_type = WebsiteType.UNKNOWN
    
    def _update_statistics(self, result: ScoringResult):
        """Update scoring statistics"""
        self.stats["total_scored"] += 1
        
        if result.website_type == WebsiteType.BUSINESS:
            self.stats["business_sites"] += 1
        elif result.website_type == WebsiteType.PERSONAL:
            self.stats["personal_sites"] += 1
        
        # Update running average
        total = self.stats["total_scored"]
        current_avg = self.stats["average_score"]
        self.stats["average_score"] = (current_avg * (total - 1) + result.business_score) / total
        
        if result.confidence >= self.high_confidence_threshold:
            self.stats["high_confidence_predictions"] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scoring statistics"""
        return self.stats.copy()
    
    def score_multiple_domains(self, domains: List[str], 
                              platform_types: Optional[Dict[str, str]] = None) -> List[ScoringResult]:
        """
        Score multiple domains for business indicators
        
        Args:
            domains: List of domains to score
            platform_types: Optional mapping of domain to platform type
            
        Returns:
            List of ScoringResult objects
        """
        results = []
        platform_types = platform_types or {}
        
        self.logger.info(f"Starting batch business scoring for {len(domains)} domains")
        
        for domain in domains:
            try:
                platform_type = platform_types.get(domain, "unknown")
                result = self.score_domain(domain, platform_type)
                results.append(result)
                
                # Add delay between requests to be polite
                time.sleep(0.5)
                
            except Exception as e:
                error_result = ScoringResult(
                    domain=domain,
                    business_score=0.0,
                    confidence=0.0,
                    website_type=WebsiteType.UNKNOWN,
                    error=str(e)
                )
                results.append(error_result)
        
        self.logger.info(f"Batch business scoring completed: {len(results)} results")
        
        return results


class BusinessScoringTool(BaseTool):
    """
    Agency Swarm tool for business website scoring
    """
    
    domains: List[str] = Field(
        ...,
        description="List of domains to analyze for business scoring"
    )
    
    platform_types: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional mapping of domain to platform type for enhanced scoring"
    )
    
    business_threshold: float = Field(
        default=0.6,
        description="Threshold score for classifying sites as business (0.0-1.0)"
    )
    
    timeout: int = Field(
        default=15,
        description="Timeout in seconds for HTTP requests"
    )
    
    content_analysis_enabled: bool = Field(
        default=True,
        description="Whether to perform deep content analysis"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Run business scoring on the provided domains
        
        Returns:
            Dictionary containing scoring results and statistics
        """
        start_time = time.time()
        
        # Initialize business scorer
        config = {
            "business_threshold": self.business_threshold,
            "timeout": self.timeout,
            "content_analysis_enabled": self.content_analysis_enabled,
            "log_level": logging.INFO
        }
        
        scorer = BusinessScorer(config)
        
        logger.info(f"Starting business scoring for {len(self.domains)} domains")
        
        try:
            # Run scoring
            results = scorer.score_multiple_domains(self.domains, self.platform_types)
            
            # Process results
            type_summary = {}
            business_count = 0
            total_score = 0.0
            high_confidence_count = 0
            
            for result in results:
                type_name = result.website_type.value
                type_summary[type_name] = type_summary.get(type_name, 0) + 1
                
                if result.website_type == WebsiteType.BUSINESS:
                    business_count += 1
                
                if not result.error:
                    total_score += result.business_score
                    if result.confidence >= 0.8:
                        high_confidence_count += 1
            
            # Calculate summary statistics
            processing_time = time.time() - start_time
            successful_scorings = len([r for r in results if not r.error])
            average_score = total_score / successful_scorings if successful_scorings > 0 else 0.0
            business_rate = business_count / len(self.domains) if self.domains else 0.0
            
            logger.info(f"Business scoring completed: {successful_scorings}/{len(self.domains)} successful "
                       f"({business_count} business sites) in {processing_time:.2f}s")
            
            return {
                "success": True,
                "processing_summary": {
                    "total_domains": len(self.domains),
                    "successful_scorings": successful_scorings,
                    "failed_scorings": len(self.domains) - successful_scorings,
                    "business_sites_found": business_count,
                    "business_site_rate": business_rate,
                    "average_business_score": average_score,
                    "high_confidence_predictions": high_confidence_count,
                    "processing_time_seconds": processing_time
                },
                "type_distribution": type_summary,
                "scoring_results": [asdict(result) for result in results],
                "scorer_statistics": scorer.get_statistics(),
                "configuration": config
            }
            
        except Exception as e:
            logger.error(f"Error during business scoring: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time,
                "partial_results": None
            }


class EnhancedBusinessScoringTool(BaseTool):
    """
    Enhanced Agency Swarm tool for business website scoring with email validation integration.
    
    This tool combines traditional business scoring with Mailtester Ninja API validation results
    to provide comprehensive lead quality assessment and prioritization.
    """
    
    contact_data: List[Dict[str, Any]] = Field(
        ...,
        description="List of contact data dictionaries containing domain and email validation information"
    )
    
    business_threshold: float = Field(
        default=0.6,
        description="Threshold score for classifying sites as business (0.0-1.0)"
    )
    
    email_quality_weight: float = Field(
        default=0.4,
        description="Weight of email validation quality in final scoring (0.0-1.0)"
    )
    
    prioritize_verified_emails: bool = Field(
        default=True,
        description="Whether to boost scores for SMTP-verified emails"
    )
    
    penalty_for_disposable: float = Field(
        default=0.3,
        description="Score penalty for disposable email addresses"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Run enhanced business scoring with email validation integration.
        
        Returns:
            Dictionary containing enhanced scoring results and lead prioritization
        """
        start_time = time.time()
        
        logger.info(f"Starting enhanced business scoring for {len(self.contact_data)} contacts")
        
        try:
            enhanced_results = []
            
            for contact in self.contact_data:
                enhanced_score = self._calculate_enhanced_score(contact)
                enhanced_results.append(enhanced_score)
            
            # Sort by priority score (highest first)
            enhanced_results.sort(key=lambda x: x.get('final_priority_score', 0), reverse=True)
            
            # Categorize results by lead quality
            lead_categories = self._categorize_leads(enhanced_results)
            
            # Calculate summary statistics
            processing_time = time.time() - start_time
            
            logger.info(f"Enhanced business scoring completed in {processing_time:.2f}s")
            
            return {
                "success": True,
                "processing_summary": {
                    "total_contacts": len(self.contact_data),
                    "high_priority_leads": lead_categories['high_priority_count'],
                    "medium_priority_leads": lead_categories['medium_priority_count'],
                    "low_priority_leads": lead_categories['low_priority_count'],
                    "verified_email_count": lead_categories['verified_email_count'],
                    "disposable_email_count": lead_categories['disposable_email_count'],
                    "processing_time_seconds": processing_time
                },
                "lead_prioritization": {
                    "high_priority_leads": lead_categories['high_priority'],
                    "medium_priority_leads": lead_categories['medium_priority'],
                    "low_priority_leads": lead_categories['low_priority']
                },
                "enhanced_scoring_results": enhanced_results,
                "configuration": {
                    "business_threshold": self.business_threshold,
                    "email_quality_weight": self.email_quality_weight,
                    "prioritize_verified_emails": self.prioritize_verified_emails,
                    "penalty_for_disposable": self.penalty_for_disposable
                }
            }
            
        except Exception as e:
            logger.error(f"Error during enhanced business scoring: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time
            }
    
    def _calculate_enhanced_score(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced business score incorporating email validation data"""
        
        # Extract key contact information
        email = contact.get('host_email', contact.get('email', ''))
        domain = contact.get('domain', email.split('@')[1] if '@' in email else '')
        
        # Base business scoring factors
        base_business_score = self._calculate_base_business_score(contact, domain)
        
        # Email validation scoring
        email_quality_score = self._calculate_email_quality_score(contact)
        
        # Combine scores with weighting
        website_weight = 1.0 - self.email_quality_weight
        final_score = (base_business_score * website_weight) + (email_quality_score * self.email_quality_weight)
        
        # Apply special bonuses and penalties
        final_score = self._apply_scoring_adjustments(contact, final_score)
        
        # Ensure score is within bounds
        final_score = max(0.0, min(1.0, final_score))
        
        # Calculate confidence level
        confidence = self._calculate_confidence(contact, base_business_score, email_quality_score)
        
        # Determine lead priority category
        priority_category = self._determine_priority_category(final_score, confidence, contact)
        
        return {
            **contact,  # Preserve original contact data
            'base_business_score': base_business_score,
            'email_quality_score': email_quality_score,
            'final_priority_score': final_score,
            'confidence_level': confidence,
            'priority_category': priority_category,
            'scoring_breakdown': {
                'website_component': base_business_score * website_weight,
                'email_component': email_quality_score * self.email_quality_weight,
                'is_verified_email': contact.get('smtp_verified', False),
                'is_disposable': contact.get('is_disposable_email', False),
                'is_role_account': contact.get('is_role_account', False),
                'mailtester_score': contact.get('mailtester_score', 0.0)
            }
        }
    
    def _calculate_base_business_score(self, contact: Dict[str, Any], domain: str) -> float:
        """Calculate base business score from contact and domain information"""
        
        score = 0.5  # Base score
        
        # Domain type indicators
        if self._is_business_domain(domain):
            score += 0.2
        elif self._is_personal_domain(domain):
            score -= 0.1
        
        # Title/role indicators
        title = contact.get('title', '').lower()
        executive_titles = ['ceo', 'founder', 'president', 'director', 'vp', 'vice president', 'chief', 'head', 'owner']
        if any(exec_title in title for exec_title in executive_titles):
            score += 0.25
        
        # Company information
        company = contact.get('company', '')
        if company and len(company) > 3:
            score += 0.15
        
        # Website quality indicators
        website = contact.get('website', contact.get('podcast_website', ''))
        if website and website.startswith('http'):
            score += 0.1
        
        # Contact page availability
        if contact.get('contact_page_url', '') or contact.get('contact_forms_available', False):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_email_quality_score(self, contact: Dict[str, Any]) -> float:
        """Calculate email quality score from Mailtester validation data"""
        
        # Start with Mailtester score if available
        base_score = contact.get('mailtester_score', 0.5)
        
        # Apply validation-based adjustments
        if contact.get('smtp_verified', False):
            base_score += 0.2  # Verified emails are highly valuable
        
        if contact.get('is_role_account', False) and not contact.get('is_disposable_email', False):
            base_score += 0.15  # Business role accounts are valuable
        
        if contact.get('is_disposable_email', False):
            base_score -= self.penalty_for_disposable  # Heavily penalize disposable emails
        
        if contact.get('is_catch_all_domain', False):
            base_score -= 0.1  # Catch-all domains are less reliable
        
        # Domain existence and MX records
        if contact.get('has_mx_records', False) and contact.get('domain_exists', False):
            base_score += 0.1
        
        # SMTP connectivity
        if contact.get('smtp_can_connect', False):
            base_score += 0.05
        
        # Validation method bonus (API validation is preferred)
        if contact.get('email_validation_method') == 'Mailtester Ninja API':
            base_score += 0.05
        
        return max(0.0, min(1.0, base_score))
    
    def _apply_scoring_adjustments(self, contact: Dict[str, Any], score: float) -> float:
        """Apply final scoring adjustments based on special conditions"""
        
        # Bonus for SMTP-verified business contacts
        if (self.prioritize_verified_emails and 
            contact.get('smtp_verified', False) and 
            contact.get('is_role_account', False) and 
            not contact.get('is_disposable_email', False)):
            score += 0.1
        
        # Penalty for multiple risk factors
        risk_factors = sum([
            contact.get('is_disposable_email', False),
            contact.get('is_catch_all_domain', False),
            not contact.get('has_mx_records', True),
            not contact.get('domain_exists', True)
        ])
        
        if risk_factors >= 2:
            score -= 0.15  # Multiple risk factors compound
        
        # Bonus for high-confidence Mailtester results
        if contact.get('mailtester_confidence_level') == 'high':
            score += 0.05
        
        return score
    
    def _calculate_confidence(self, contact: Dict[str, Any], business_score: float, email_score: float) -> float:
        """Calculate overall confidence in the lead quality assessment"""
        
        confidence = 0.5  # Base confidence
        
        # Email validation confidence
        if contact.get('email_validation_method') == 'Mailtester Ninja API':
            confidence += 0.2
        
        if contact.get('smtp_verified', False):
            confidence += 0.2
        
        # Business information completeness
        info_completeness = sum([
            bool(contact.get('company')),
            bool(contact.get('title')),
            bool(contact.get('website', contact.get('podcast_website', ''))),
            bool(contact.get('contact_page_url'))
        ]) / 4.0
        
        confidence += info_completeness * 0.3
        
        # Score consistency
        score_difference = abs(business_score - email_score)
        if score_difference < 0.2:  # Scores are consistent
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _determine_priority_category(self, score: float, confidence: float, contact: Dict[str, Any]) -> str:
        """Determine lead priority category"""
        
        # High priority: High score with high confidence OR verified business email
        if ((score >= 0.75 and confidence >= 0.7) or 
            (contact.get('smtp_verified', False) and 
             contact.get('is_role_account', False) and 
             not contact.get('is_disposable_email', False) and
             score >= 0.6)):
            return 'high'
        
        # Medium priority: Good score OR verified email
        elif (score >= 0.5 and confidence >= 0.5) or contact.get('smtp_verified', False):
            return 'medium'
        
        # Low priority: Everything else
        else:
            return 'low'
    
    def _categorize_leads(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize leads by priority and calculate statistics"""
        
        categories = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': [],
            'high_priority_count': 0,
            'medium_priority_count': 0,
            'low_priority_count': 0,
            'verified_email_count': 0,
            'disposable_email_count': 0
        }
        
        for result in results:
            priority = result.get('priority_category', 'low')
            
            categories[f'{priority}_priority'].append(result)
            categories[f'{priority}_priority_count'] += 1
            
            if result.get('smtp_verified', False):
                categories['verified_email_count'] += 1
            
            if result.get('is_disposable_email', False):
                categories['disposable_email_count'] += 1
        
        return categories
    
    def _is_business_domain(self, domain: str) -> bool:
        """Check if domain appears to be business-oriented"""
        business_indicators = [
            'corp', 'inc', 'ltd', 'llc', 'company', 'enterprises',
            'group', 'solutions', 'consulting', 'services', 'tech',
            'digital', 'agency', 'partners', 'business'
        ]
        
        domain_lower = domain.lower()
        return any(indicator in domain_lower for indicator in business_indicators)
    
    def _is_personal_domain(self, domain: str) -> bool:
        """Check if domain is a personal email provider"""
        personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'me.com', 'protonmail.com',
            'tutanota.com', 'fastmail.com', 'zoho.com', 'yandex.com',
            'mail.com', 'gmx.com', 'web.de', 'live.com', 'msn.com'
        }
        return domain.lower() in personal_domains