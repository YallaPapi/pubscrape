"""
Domain Classifier Agent

Agency Swarm agent for classifying and prioritizing business websites.
Handles domain deduplication, platform detection, business scoring, 
and crawl budget assignment with comprehensive metrics tracking.
"""

import logging
import time
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, asdict, field
from enum import Enum

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
from pydantic import Field


class WebsiteType(Enum):
    """Enumeration of website types"""
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
    """Enumeration of detected platforms"""
    WORDPRESS = "wordpress"
    SHOPIFY = "shopify"
    WIX = "wix"
    SQUARESPACE = "squarespace"
    WEEBLY = "weebly"
    DRUPAL = "drupal"
    JOOMLA = "joomla"
    MAGENTO = "magento"
    PRESTASHOP = "prestashop"
    BIGCOMMERCE = "bigcommerce"
    WEBFLOW = "webflow"
    GHOST = "ghost"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class PriorityLevel(Enum):
    """Priority levels for crawling"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"


@dataclass
class DomainMetadata:
    """Comprehensive metadata for a classified domain"""
    domain: str
    normalized_domain: str
    original_url: str
    website_type: WebsiteType = WebsiteType.UNKNOWN
    platform_type: PlatformType = PlatformType.UNKNOWN
    business_score: float = 0.0
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    crawl_budget: int = 5
    
    # Classification details
    business_indicators: List[str] = field(default_factory=list)
    platform_indicators: List[str] = field(default_factory=list)
    industry_hints: List[str] = field(default_factory=list)
    exclusion_reasons: List[str] = field(default_factory=list)
    
    # Technical details
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    detected_technologies: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    last_probed: Optional[float] = None
    
    # Flags
    is_accessible: bool = True
    requires_javascript: bool = False
    has_robots_txt: bool = False
    is_redirect: bool = False
    redirect_target: Optional[str] = None
    
    def update_timestamp(self):
        """Update the last_updated timestamp"""
        self.last_updated = time.time()
    
    def mark_probed(self):
        """Mark the domain as recently probed"""
        self.last_probed = time.time()
        self.update_timestamp()


@dataclass
class ClassificationStats:
    """Statistics for the classification process"""
    total_domains: int = 0
    unique_domains: int = 0
    duplicates_removed: int = 0
    successfully_classified: int = 0
    failed_classifications: int = 0
    
    # Website type counts
    business_websites: int = 0
    ecommerce_websites: int = 0
    personal_websites: int = 0
    blog_websites: int = 0
    
    # Platform counts
    wordpress_sites: int = 0
    shopify_sites: int = 0
    custom_sites: int = 0
    
    # Priority distribution
    critical_priority: int = 0
    high_priority: int = 0
    medium_priority: int = 0
    low_priority: int = 0
    skip_priority: int = 0
    
    # Performance metrics
    processing_time_seconds: float = 0.0
    average_classification_time_ms: float = 0.0
    domains_per_second: float = 0.0
    
    # Quality metrics
    average_business_score: float = 0.0
    average_crawl_budget: float = 0.0
    accessibility_rate: float = 0.0


class DomainClassifier:
    """
    Core domain classifier for deduplication, normalization, and metadata tracking.
    
    This class handles the foundational operations for domain classification including:
    - Domain normalization and deduplication
    - Metadata tracking and management
    - Statistics collection
    - Batch processing coordination
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Core data structures
        self.domains: Dict[str, DomainMetadata] = {}
        self.domain_to_normalized: Dict[str, str] = {}  # Maps original to normalized
        self.url_to_domain: Dict[str, str] = {}  # Maps URLs to normalized domains
        
        # Processing statistics
        self.stats = ClassificationStats()
        
        # Configuration
        self.max_domain_length = self.config.get("max_domain_length", 253)
        self.strip_www = self.config.get("strip_www", True)
        self.preserve_subdomain = self.config.get("preserve_subdomain", True)
        self.case_sensitive = self.config.get("case_sensitive", False)
        
        self.logger.info("DomainClassifier initialized with config options")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the domain classifier"""
        logger = logging.getLogger(f"{__name__}.DomainClassifier")
        
        # Configure structured logging if needed
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def add_domains(self, domains: List[str]) -> Dict[str, Any]:
        """
        Add a list of domains/URLs for classification.
        
        Args:
            domains: List of domain names or URLs to add
            
        Returns:
            Dictionary with processing results and statistics
        """
        start_time = time.time()
        
        added_domains = []
        duplicate_domains = []
        invalid_domains = []
        
        self.logger.info(f"Adding {len(domains)} domains for classification")
        
        for domain_url in domains:
            try:
                # Normalize the domain
                normalized = self._normalize_domain(domain_url)
                
                if not normalized:
                    invalid_domains.append(domain_url)
                    continue
                
                # Check for duplicates
                if normalized in self.domains:
                    duplicate_domains.append(domain_url)
                    self.logger.debug(f"Duplicate domain skipped: {domain_url} -> {normalized}")
                    continue
                
                # Create domain metadata
                metadata = DomainMetadata(
                    domain=normalized,
                    normalized_domain=normalized,
                    original_url=domain_url
                )
                
                # Store the domain
                self.domains[normalized] = metadata
                self.domain_to_normalized[domain_url] = normalized
                self.url_to_domain[domain_url] = normalized
                
                added_domains.append(normalized)
                
                self.logger.debug(f"Added domain: {domain_url} -> {normalized}")
                
            except Exception as e:
                self.logger.error(f"Error processing domain '{domain_url}': {e}")
                invalid_domains.append(domain_url)
        
        # Update statistics
        self.stats.total_domains += len(domains)
        self.stats.unique_domains = len(self.domains)
        self.stats.duplicates_removed += len(duplicate_domains)
        
        processing_time = time.time() - start_time
        self.stats.processing_time_seconds += processing_time
        
        result = {
            "success": True,
            "added_domains": len(added_domains),
            "duplicate_domains": len(duplicate_domains),
            "invalid_domains": len(invalid_domains),
            "total_unique_domains": len(self.domains),
            "processing_time_seconds": processing_time,
            "added_domain_list": added_domains,
            "duplicate_domain_list": duplicate_domains,
            "invalid_domain_list": invalid_domains
        }
        
        self.logger.info(f"Domain addition completed: {len(added_domains)} added, "
                        f"{len(duplicate_domains)} duplicates, {len(invalid_domains)} invalid")
        
        return result
    
    def _normalize_domain(self, domain_url: str) -> Optional[str]:
        """
        Normalize a domain or URL to a consistent format.
        
        Args:
            domain_url: Domain name or URL to normalize
            
        Returns:
            Normalized domain string or None if invalid
        """
        if not domain_url or not isinstance(domain_url, str):
            return None
        
        domain_url = domain_url.strip()
        
        # Handle URLs vs plain domains
        if '://' in domain_url:
            try:
                parsed = urlparse(domain_url)
                domain = parsed.netloc
            except Exception:
                return None
        else:
            domain = domain_url
        
        if not domain:
            return None
        
        # Remove port numbers
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Normalize case
        if not self.case_sensitive:
            domain = domain.lower()
        
        # Strip www prefix if configured
        if self.strip_www and domain.startswith('www.'):
            domain = domain[4:]
        
        # Validate domain format
        if not self._is_valid_domain(domain):
            return None
        
        # Check length
        if len(domain) > self.max_domain_length:
            return None
        
        return domain
    
    def _is_valid_domain(self, domain: str) -> bool:
        """
        Validate that a domain string is properly formatted.
        
        Args:
            domain: Domain string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not domain:
            return False
        
        # Basic format validation
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        if not domain_pattern.match(domain):
            return False
        
        # Must contain at least one dot (TLD required)
        if '.' not in domain:
            return False
        
        # No consecutive dots
        if '..' in domain:
            return False
        
        # No leading/trailing dots or hyphens
        if domain.startswith('.') or domain.endswith('.'):
            return False
        if domain.startswith('-') or domain.endswith('-'):
            return False
        
        return True
    
    def get_domain_metadata(self, domain: str) -> Optional[DomainMetadata]:
        """
        Get metadata for a specific domain.
        
        Args:
            domain: Domain to get metadata for (can be original URL or normalized)
            
        Returns:
            DomainMetadata object or None if not found
        """
        # Try direct lookup first
        if domain in self.domains:
            return self.domains[domain]
        
        # Try lookup via normalization mapping
        if domain in self.domain_to_normalized:
            normalized = self.domain_to_normalized[domain]
            return self.domains.get(normalized)
        
        # Try normalizing and lookup
        normalized = self._normalize_domain(domain)
        if normalized and normalized in self.domains:
            return self.domains[normalized]
        
        return None
    
    def update_domain_metadata(self, domain: str, updates: Dict[str, Any]) -> bool:
        """
        Update metadata for a specific domain.
        
        Args:
            domain: Domain to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False if domain not found
        """
        metadata = self.get_domain_metadata(domain)
        if not metadata:
            return False
        
        # Update fields
        for field_name, value in updates.items():
            if hasattr(metadata, field_name):
                setattr(metadata, field_name, value)
                self.logger.debug(f"Updated {domain}.{field_name} = {value}")
        
        # Update timestamp
        metadata.update_timestamp()
        
        return True
    
    def get_domains_by_type(self, website_type: WebsiteType) -> List[DomainMetadata]:
        """
        Get all domains of a specific website type.
        
        Args:
            website_type: Type of website to filter by
            
        Returns:
            List of DomainMetadata objects matching the type
        """
        return [metadata for metadata in self.domains.values() 
                if metadata.website_type == website_type]
    
    def get_domains_by_platform(self, platform_type: PlatformType) -> List[DomainMetadata]:
        """
        Get all domains of a specific platform type.
        
        Args:
            platform_type: Type of platform to filter by
            
        Returns:
            List of DomainMetadata objects matching the platform
        """
        return [metadata for metadata in self.domains.values() 
                if metadata.platform_type == platform_type]
    
    def get_domains_by_priority(self, priority_level: PriorityLevel) -> List[DomainMetadata]:
        """
        Get all domains of a specific priority level.
        
        Args:
            priority_level: Priority level to filter by
            
        Returns:
            List of DomainMetadata objects matching the priority
        """
        return [metadata for metadata in self.domains.values() 
                if metadata.priority_level == priority_level]
    
    def get_all_domains(self) -> List[DomainMetadata]:
        """
        Get all domain metadata objects.
        
        Returns:
            List of all DomainMetadata objects
        """
        return list(self.domains.values())
    
    def probe_domain_platforms(self, domains: Optional[List[str]] = None, 
                              batch_size: int = 10) -> Dict[str, Any]:
        """
        Probe domains for platform detection using HTTP requests.
        
        Args:
            domains: Optional list of specific domains to probe. If None, probes all domains.
            batch_size: Number of domains to process in each batch
            
        Returns:
            Dictionary containing probing results and updated metadata
        """
        if domains is None:
            domains_to_probe = list(self.domains.keys())
        else:
            # Normalize provided domains
            domains_to_probe = []
            for domain in domains:
                normalized = self._normalize_domain(domain)
                if normalized and normalized in self.domains:
                    domains_to_probe.append(normalized)
        
        self.logger.info(f"Starting platform probing for {len(domains_to_probe)} domains")
        
        # Import platform detector here to avoid circular imports
        try:
            from .tools.platform_detection_tool import PlatformDetector, PlatformType as DetectorPlatformType
            
            # Map our PlatformType to detector PlatformType
            platform_map = {
                DetectorPlatformType.WORDPRESS: PlatformType.WORDPRESS,
                DetectorPlatformType.SHOPIFY: PlatformType.SHOPIFY,
                DetectorPlatformType.WIX: PlatformType.WIX,
                DetectorPlatformType.SQUARESPACE: PlatformType.SQUARESPACE,
                DetectorPlatformType.CUSTOM: PlatformType.CUSTOM,
                DetectorPlatformType.UNKNOWN: PlatformType.UNKNOWN
            }
            
        except ImportError:
            self.logger.error("Platform detection tool not available")
            return {"success": False, "error": "Platform detection tool not available"}
        
        # Initialize detector
        detector_config = {
            "timeout": 10,
            "max_retries": 2,
            "enable_content_analysis": True,
            "enable_meta_analysis": True,
            "log_level": self.logger.level
        }
        
        detector = PlatformDetector(detector_config)
        
        # Process domains in batches
        total_probed = 0
        total_updated = 0
        platform_counts = {}
        
        for i in range(0, len(domains_to_probe), batch_size):
            batch = domains_to_probe[i:i + batch_size]
            
            try:
                # Detect platforms for this batch
                results = detector.detect_multiple_platforms(batch)
                
                # Update domain metadata
                for result in results:
                    domain = result.domain
                    if domain in self.domains:
                        metadata = self.domains[domain]
                        
                        # Map platform type
                        if hasattr(result, 'platform') and result.platform in platform_map:
                            metadata.platform_type = platform_map[result.platform]
                        else:
                            metadata.platform_type = PlatformType.UNKNOWN
                        
                        # Update metadata with detection results
                        if hasattr(result, 'confidence'):
                            metadata.platform_indicators = [f"confidence: {result.confidence:.2f}"]
                        
                        if hasattr(result, 'detected_signatures'):
                            metadata.platform_indicators.extend(result.detected_signatures)
                        
                        if hasattr(result, 'response_time_ms'):
                            metadata.response_time_ms = result.response_time_ms
                        
                        if hasattr(result, 'status_code'):
                            metadata.status_code = result.status_code
                        
                        if hasattr(result, 'error') and result.error:
                            metadata.is_accessible = False
                            metadata.exclusion_reasons.append(f"probe_error: {result.error}")
                        else:
                            metadata.is_accessible = True
                        
                        # Mark as probed
                        metadata.mark_probed()
                        
                        total_updated += 1
                        
                        # Count platforms
                        platform_name = metadata.platform_type.value
                        platform_counts[platform_name] = platform_counts.get(platform_name, 0) + 1
                
                total_probed += len(results)
                
                # Small delay between batches to be polite
                if i + batch_size < len(domains_to_probe):
                    import time
                    time.sleep(1.0)
                
                self.logger.info(f"Processed batch {i//batch_size + 1}: {len(results)} domains probed")
                
            except Exception as e:
                self.logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                continue
        
        # Update overall statistics
        self.stats.successfully_classified += total_updated
        
        self.logger.info(f"Platform probing completed: {total_probed} domains probed, "
                        f"{total_updated} metadata updated")
        
        return {
            "success": True,
            "probing_summary": {
                "domains_requested": len(domains_to_probe),
                "domains_probed": total_probed,
                "metadata_updated": total_updated,
                "platform_distribution": platform_counts
            },
            "detector_statistics": detector.get_statistics()
        }

    def score_business_domains(self, domains: Optional[List[str]] = None, 
                              batch_size: int = 5) -> Dict[str, Any]:
        """
        Score domains for business indicators and classify website types.
        
        Args:
            domains: Optional list of specific domains to score. If None, scores all domains.
            batch_size: Number of domains to process in each batch
            
        Returns:
            Dictionary containing scoring results and updated metadata
        """
        if domains is None:
            domains_to_score = list(self.domains.keys())
        else:
            # Normalize provided domains
            domains_to_score = []
            for domain in domains:
                normalized = self._normalize_domain(domain)
                if normalized and normalized in self.domains:
                    domains_to_score.append(normalized)
        
        self.logger.info(f"Starting business scoring for {len(domains_to_score)} domains")
        
        # Import business scorer here to avoid circular imports
        try:
            from .tools.business_scoring_tool import BusinessScorer, WebsiteType as ScorerWebsiteType
            
            # Map our WebsiteType to scorer WebsiteType
            website_type_map = {
                ScorerWebsiteType.BUSINESS: WebsiteType.BUSINESS,
                ScorerWebsiteType.PERSONAL: WebsiteType.PERSONAL,
                ScorerWebsiteType.BLOG: WebsiteType.BLOG,
                ScorerWebsiteType.ECOMMERCE: WebsiteType.ECOMMERCE,
                ScorerWebsiteType.PORTFOLIO: WebsiteType.PORTFOLIO,
                ScorerWebsiteType.NEWS_MEDIA: WebsiteType.NEWS_MEDIA,
                ScorerWebsiteType.SOCIAL_MEDIA: WebsiteType.SOCIAL_MEDIA,
                ScorerWebsiteType.DIRECTORY: WebsiteType.DIRECTORY,
                ScorerWebsiteType.GOVERNMENT: WebsiteType.GOVERNMENT,
                ScorerWebsiteType.EDUCATIONAL: WebsiteType.EDUCATIONAL,
                ScorerWebsiteType.NONPROFIT: WebsiteType.NONPROFIT,
                ScorerWebsiteType.PLATFORM: WebsiteType.PLATFORM,
                ScorerWebsiteType.UNKNOWN: WebsiteType.UNKNOWN
            }
            
        except ImportError:
            self.logger.error("Business scoring tool not available")
            return {"success": False, "error": "Business scoring tool not available"}
        
        # Initialize scorer
        scorer_config = {
            "timeout": 15,
            "business_threshold": 0.6,
            "content_analysis_enabled": True,
            "log_level": self.logger.level
        }
        
        scorer = BusinessScorer(scorer_config)
        
        # Prepare platform types for enhanced scoring
        platform_types = {}
        for domain in domains_to_score:
            if domain in self.domains:
                platform_types[domain] = self.domains[domain].platform_type.value
        
        # Process domains in batches
        total_scored = 0
        total_updated = 0
        scoring_summary = {}
        
        for i in range(0, len(domains_to_score), batch_size):
            batch = domains_to_score[i:i + batch_size]
            
            try:
                # Score this batch
                batch_platform_types = {domain: platform_types.get(domain, "unknown") for domain in batch}
                results = scorer.score_multiple_domains(batch, batch_platform_types)
                
                # Update domain metadata
                for result in results:
                    domain = result.domain
                    if domain in self.domains:
                        metadata = self.domains[domain]
                        
                        # Update business score and website type
                        metadata.business_score = result.business_score
                        
                        # Map website type
                        if hasattr(result, 'website_type') and result.website_type in website_type_map:
                            metadata.website_type = website_type_map[result.website_type]
                        else:
                            metadata.website_type = WebsiteType.UNKNOWN
                        
                        # Update business indicators
                        if hasattr(result, 'positive_indicators'):
                            metadata.business_indicators = result.positive_indicators
                        
                        if hasattr(result, 'industry_hints'):
                            metadata.industry_hints = result.industry_hints
                        
                        # Update technical details
                        if hasattr(result, 'response_time_ms') and result.response_time_ms:
                            metadata.response_time_ms = result.response_time_ms
                        
                        if hasattr(result, 'status_code') and result.status_code:
                            metadata.status_code = result.status_code
                        
                        if hasattr(result, 'error') and result.error:
                            metadata.is_accessible = False
                            metadata.exclusion_reasons.append(f"scoring_error: {result.error}")
                        else:
                            metadata.is_accessible = True
                        
                        # Update flags based on scoring results
                        if hasattr(result, 'has_contact_info'):
                            if result.has_contact_info:
                                metadata.business_indicators.append("contact_info_found")
                        
                        if hasattr(result, 'has_business_keywords'):
                            if result.has_business_keywords:
                                metadata.business_indicators.append("business_keywords_found")
                        
                        # Update timestamp
                        metadata.update_timestamp()
                        
                        total_updated += 1
                        
                        # Count website types
                        website_type_name = metadata.website_type.value
                        scoring_summary[website_type_name] = scoring_summary.get(website_type_name, 0) + 1
                
                total_scored += len(results)
                
                # Small delay between batches to be polite
                if i + batch_size < len(domains_to_score):
                    import time
                    time.sleep(2.0)
                
                self.logger.info(f"Processed scoring batch {i//batch_size + 1}: {len(results)} domains scored")
                
            except Exception as e:
                self.logger.error(f"Error processing scoring batch {i//batch_size + 1}: {e}")
                continue
        
        # Update overall statistics
        self.stats.successfully_classified += total_updated
        
        self.logger.info(f"Business scoring completed: {total_scored} domains scored, "
                        f"{total_updated} metadata updated")
        
        return {
            "success": True,
            "scoring_summary": {
                "domains_requested": len(domains_to_score),
                "domains_scored": total_scored,
                "metadata_updated": total_updated,
                "website_type_distribution": scoring_summary
            },
            "scorer_statistics": scorer.get_statistics()
        }

    def prioritize_domains(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prioritize domains based on business scores and assign crawl budgets.
        
        Args:
            config: Optional configuration for prioritization rules
            
        Returns:
            Dictionary containing prioritization results
        """
        prioritization_config = config or {}
        
        # Prioritization weights and thresholds
        business_score_weight = prioritization_config.get("business_score_weight", 0.7)
        platform_weight = prioritization_config.get("platform_weight", 0.2)
        accessibility_weight = prioritization_config.get("accessibility_weight", 0.1)
        
        # Platform multipliers (bonus scores for certain platforms)
        platform_multipliers = prioritization_config.get("platform_multipliers", {
            "shopify": 1.3,
            "wordpress": 1.1,
            "custom": 1.2,
            "wix": 1.0,
            "squarespace": 1.0,
            "unknown": 0.8
        })
        
        # Crawl budget assignments based on priority
        budget_assignments = prioritization_config.get("budget_assignments", {
            "critical": 20,
            "high": 15,
            "medium": 10,
            "low": 5,
            "skip": 0
        })
        
        self.logger.info(f"Starting domain prioritization for {len(self.domains)} domains")
        
        # Calculate priority scores for all domains
        domain_priorities = []
        
        for domain, metadata in self.domains.items():
            try:
                # Calculate composite priority score
                priority_score = self._calculate_priority_score(
                    metadata, 
                    business_score_weight, 
                    platform_weight, 
                    accessibility_weight, 
                    platform_multipliers
                )
                
                # Determine priority level
                priority_level = self._determine_priority_level(priority_score, metadata)
                
                # Assign crawl budget
                crawl_budget = budget_assignments.get(priority_level.value, 5)
                
                # Update metadata
                metadata.priority_level = priority_level
                metadata.crawl_budget = crawl_budget
                metadata.update_timestamp()
                
                domain_priorities.append({
                    "domain": domain,
                    "priority_score": priority_score,
                    "priority_level": priority_level.value,
                    "crawl_budget": crawl_budget,
                    "business_score": metadata.business_score,
                    "website_type": metadata.website_type.value,
                    "platform_type": metadata.platform_type.value,
                    "is_accessible": metadata.is_accessible
                })
                
            except Exception as e:
                self.logger.error(f"Error calculating priority for {domain}: {e}")
                # Set default values for failed prioritization
                metadata.priority_level = PriorityLevel.LOW
                metadata.crawl_budget = 5
                metadata.update_timestamp()
        
        # Sort domains by priority score (highest first)
        domain_priorities.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Generate priority distribution
        priority_distribution = {}
        for entry in domain_priorities:
            level = entry["priority_level"]
            priority_distribution[level] = priority_distribution.get(level, 0) + 1
        
        self.logger.info(f"Domain prioritization completed: {len(domain_priorities)} domains prioritized")
        
        return {
            "success": True,
            "prioritization_summary": {
                "total_domains": len(domain_priorities),
                "priority_distribution": priority_distribution,
                "average_priority_score": sum(p["priority_score"] for p in domain_priorities) / len(domain_priorities) if domain_priorities else 0.0,
                "total_crawl_budget": sum(p["crawl_budget"] for p in domain_priorities)
            },
            "prioritized_domains": domain_priorities,
            "configuration": {
                "business_score_weight": business_score_weight,
                "platform_weight": platform_weight,
                "accessibility_weight": accessibility_weight,
                "platform_multipliers": platform_multipliers,
                "budget_assignments": budget_assignments
            }
        }
    
    def _calculate_priority_score(self, metadata: DomainMetadata, business_weight: float, 
                                 platform_weight: float, accessibility_weight: float,
                                 platform_multipliers: Dict[str, float]) -> float:
        """Calculate composite priority score for a domain"""
        
        # Base business score (0.0 to 1.0)
        business_component = metadata.business_score * business_weight
        
        # Platform bonus (based on platform type)
        platform_multiplier = platform_multipliers.get(metadata.platform_type.value, 1.0)
        platform_component = (platform_multiplier - 1.0) * platform_weight
        
        # Accessibility bonus
        accessibility_component = (1.0 if metadata.is_accessible else 0.0) * accessibility_weight
        
        # Additional bonuses
        bonus_score = 0.0
        
        # Contact information bonus
        if metadata.has_contact_info or "contact_info_found" in metadata.business_indicators:
            bonus_score += 0.1
        
        # Address information bonus
        if "address" in " ".join(metadata.business_indicators).lower():
            bonus_score += 0.05
        
        # E-commerce site bonus
        if metadata.website_type == WebsiteType.ECOMMERCE:
            bonus_score += 0.15
        
        # Quality indicators bonus
        if len(metadata.business_indicators) >= 3:
            bonus_score += 0.05
        
        # Penalty for errors or inaccessibility
        penalty = 0.0
        if not metadata.is_accessible:
            penalty += 0.2
        
        if metadata.exclusion_reasons:
            penalty += len(metadata.exclusion_reasons) * 0.05
        
        # Calculate final score
        final_score = business_component + platform_component + accessibility_component + bonus_score - penalty
        
        return max(0.0, min(1.0, final_score))
    
    def _determine_priority_level(self, priority_score: float, metadata: DomainMetadata) -> PriorityLevel:
        """Determine priority level based on priority score and metadata"""
        
        # Critical priority for high-value e-commerce sites
        if (metadata.website_type == WebsiteType.ECOMMERCE and 
            priority_score >= 0.8 and metadata.is_accessible):
            return PriorityLevel.CRITICAL
        
        # High priority thresholds
        if priority_score >= 0.7:
            return PriorityLevel.HIGH
        elif priority_score >= 0.5:
            return PriorityLevel.MEDIUM
        elif priority_score >= 0.3:
            return PriorityLevel.LOW
        else:
            # Skip sites with very low scores or accessibility issues
            if not metadata.is_accessible or priority_score < 0.2:
                return PriorityLevel.SKIP
            else:
                return PriorityLevel.LOW
    
    def create_crawl_queue(self, priority_filters: Optional[List[str]] = None,
                          max_domains: Optional[int] = None) -> Dict[str, Any]:
        """
        Create an ordered crawl queue based on domain prioritization.
        
        Args:
            priority_filters: Optional list of priority levels to include (e.g., ["critical", "high"])
            max_domains: Optional maximum number of domains to include in queue
            
        Returns:
            Dictionary containing the crawl queue and metadata
        """
        
        # Get all domains sorted by priority
        prioritized = self.prioritize_domains()
        if not prioritized["success"]:
            return {"success": False, "error": "Failed to prioritize domains"}
        
        all_domains = prioritized["prioritized_domains"]
        
        # Apply priority filters if specified
        if priority_filters:
            filtered_domains = [d for d in all_domains if d["priority_level"] in priority_filters]
        else:
            # Exclude 'skip' priority by default
            filtered_domains = [d for d in all_domains if d["priority_level"] != "skip"]
        
        # Apply max domains limit
        if max_domains:
            filtered_domains = filtered_domains[:max_domains]
        
        # Create crawl queue entries
        crawl_queue = []
        total_budget = 0
        
        for i, domain_info in enumerate(filtered_domains):
            domain = domain_info["domain"]
            metadata = self.domains[domain]
            
            crawl_entry = {
                "queue_position": i + 1,
                "domain": domain,
                "normalized_domain": metadata.normalized_domain,
                "original_url": metadata.original_url,
                "priority_level": domain_info["priority_level"],
                "priority_score": domain_info["priority_score"],
                "crawl_budget": domain_info["crawl_budget"],
                "website_type": domain_info["website_type"],
                "platform_type": domain_info["platform_type"],
                "business_score": domain_info["business_score"],
                "is_accessible": domain_info["is_accessible"],
                "business_indicators": metadata.business_indicators,
                "platform_indicators": metadata.platform_indicators,
                "exclusion_reasons": metadata.exclusion_reasons,
                "estimated_pages": domain_info["crawl_budget"],  # For SiteCrawler compatibility
                "created_at": metadata.created_at
            }
            
            crawl_queue.append(crawl_entry)
            total_budget += domain_info["crawl_budget"]
        
        # Generate queue statistics
        queue_stats = {
            "total_domains": len(crawl_queue),
            "total_crawl_budget": total_budget,
            "average_priority_score": sum(d["priority_score"] for d in crawl_queue) / len(crawl_queue) if crawl_queue else 0.0,
            "priority_distribution": {}
        }
        
        # Count by priority level
        for entry in crawl_queue:
            level = entry["priority_level"]
            queue_stats["priority_distribution"][level] = queue_stats["priority_distribution"].get(level, 0) + 1
        
        # Count by website type
        type_distribution = {}
        for entry in crawl_queue:
            website_type = entry["website_type"]
            type_distribution[website_type] = type_distribution.get(website_type, 0) + 1
        
        queue_stats["type_distribution"] = type_distribution
        
        self.logger.info(f"Crawl queue created: {len(crawl_queue)} domains, "
                        f"total budget: {total_budget} pages")
        
        return {
            "success": True,
            "queue_metadata": {
                "created_at": time.time(),
                "filters_applied": priority_filters or ["all except skip"],
                "max_domains_limit": max_domains,
                "queue_statistics": queue_stats
            },
            "crawl_queue": crawl_queue
        }
    
    def export_crawl_queue(self, output_format: str = "json", 
                          priority_filters: Optional[List[str]] = None,
                          max_domains: Optional[int] = None) -> Dict[str, Any]:
        """
        Export the crawl queue in various formats for downstream processing.
        
        Args:
            output_format: Format for export ("json", "csv_data", "sitecrawler_format")
            priority_filters: Optional priority level filters
            max_domains: Optional maximum number of domains
            
        Returns:
            Dictionary containing exported queue data
        """
        
        # Create the crawl queue
        queue_result = self.create_crawl_queue(priority_filters, max_domains)
        if not queue_result["success"]:
            return queue_result
        
        crawl_queue = queue_result["crawl_queue"]
        metadata = queue_result["queue_metadata"]
        
        if output_format == "json":
            return {
                "success": True,
                "format": "json",
                "metadata": metadata,
                "crawl_queue": crawl_queue
            }
        
        elif output_format == "csv_data":
            # Convert to CSV-friendly format
            csv_rows = []
            for entry in crawl_queue:
                csv_rows.append({
                    "queue_position": entry["queue_position"],
                    "domain": entry["domain"],
                    "original_url": entry["original_url"],
                    "priority_level": entry["priority_level"],
                    "priority_score": round(entry["priority_score"], 3),
                    "crawl_budget": entry["crawl_budget"],
                    "website_type": entry["website_type"],
                    "platform_type": entry["platform_type"],
                    "business_score": round(entry["business_score"], 3),
                    "is_accessible": entry["is_accessible"],
                    "business_indicators_count": len(entry["business_indicators"]),
                    "platform_indicators_count": len(entry["platform_indicators"]),
                    "exclusion_reasons_count": len(entry["exclusion_reasons"])
                })
            
            return {
                "success": True,
                "format": "csv_data",
                "metadata": metadata,
                "csv_headers": list(csv_rows[0].keys()) if csv_rows else [],
                "csv_rows": csv_rows
            }
        
        elif output_format == "sitecrawler_format":
            # Format specifically for SiteCrawler agent consumption
            sitecrawler_domains = []
            for entry in crawl_queue:
                sitecrawler_domains.append({
                    "domain": entry["domain"],
                    "url": entry["original_url"],
                    "max_pages": entry["crawl_budget"],
                    "priority": entry["priority_level"],
                    "website_type": entry["website_type"],
                    "platform": entry["platform_type"],
                    "business_score": entry["business_score"],
                    "metadata": {
                        "business_indicators": entry["business_indicators"],
                        "platform_indicators": entry["platform_indicators"],
                        "queue_position": entry["queue_position"],
                        "priority_score": entry["priority_score"]
                    }
                })
            
            return {
                "success": True,
                "format": "sitecrawler_format",
                "metadata": metadata,
                "domains_for_crawling": sitecrawler_domains
            }
        
        else:
            return {
                "success": False,
                "error": f"Unsupported export format: {output_format}"
            }

    def generate_comprehensive_report(self, export_format: str = "json", 
                                    export_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive classification and metrics report.
        
        Args:
            export_format: Format for export ("json", "csv")
            export_path: Optional path for export (defaults to timestamp-based filename)
            
        Returns:
            Dictionary containing comprehensive report and export information
        """
        
        # Import metrics tools here to avoid circular imports
        try:
            from .tools.metrics_reporting_tool import MetricsCollector, ComprehensiveReport
        except ImportError:
            self.logger.error("Metrics reporting tool not available")
            return {"success": False, "error": "Metrics reporting tool not available"}
        
        self.logger.info(f"Generating comprehensive report for {len(self.domains)} domains")
        
        # Initialize metrics collector
        collector_config = {
            "enable_detailed_logging": True,
            "enable_performance_tracking": True,
            "enable_export": True,
            "output_directory": export_path or "classification_reports",
            "log_level": self.logger.level
        }
        
        collector = MetricsCollector(collector_config)
        
        try:
            # Generate comprehensive report
            report = collector.generate_comprehensive_report(self.domains)
            
            # Export the report
            export_result = collector.export_report(report, export_format)
            
            # Prepare return data
            result = {
                "success": True,
                "report_summary": {
                    "report_id": report.report_id,
                    "generated_at": report.generated_at,
                    "total_domains": report.total_domains,
                    "processing_duration_seconds": report.processing_duration_seconds
                },
                "key_metrics": {
                    "business_sites_found": report.classification_metrics.website_type_counts.get("business", 0),
                    "ecommerce_sites_found": report.classification_metrics.website_type_counts.get("ecommerce", 0),
                    "average_business_score": report.classification_metrics.average_business_score,
                    "platform_detection_rate": report.processing_metrics.platform_detection_rate,
                    "accessibility_rate": (report.classification_metrics.accessible_sites_count / report.total_domains) * 100 if report.total_domains > 0 else 0,
                    "contact_info_rate": (report.classification_metrics.contact_info_found_count / report.total_domains) * 100 if report.total_domains > 0 else 0
                },
                "distribution_summary": {
                    "website_types": report.classification_metrics.website_type_percentages,
                    "platform_types": report.classification_metrics.platform_type_percentages,
                    "priority_levels": report.classification_metrics.priority_level_percentages
                },
                "top_performers": {
                    "business_domains": report.top_business_domains[:5],  # Top 5 for summary
                    "ecommerce_domains": report.top_ecommerce_domains
                },
                "insights": report.insights,
                "recommendations": report.recommendations,
                "export_result": export_result
            }
            
            self.logger.info(f"Comprehensive report generated successfully: {export_result.get('output_file', 'N/A')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_platform_hit_rates(self) -> Dict[str, Any]:
        """
        Get detailed platform detection hit rates and statistics.
        
        Returns:
            Dictionary containing platform detection statistics
        """
        if not self.domains:
            return {"success": False, "error": "No domains available for analysis"}
        
        platform_stats = {}
        total_domains = len(self.domains)
        detected_platforms = 0
        platform_confidence_sum = {}
        platform_response_times = {}
        
        for domain, metadata in self.domains.items():
            platform_name = metadata.platform_type.value
            
            # Count platform occurrences
            if platform_name not in platform_stats:
                platform_stats[platform_name] = {
                    "count": 0,
                    "percentage": 0.0,
                    "avg_confidence": 0.0,
                    "avg_response_time_ms": 0.0,
                    "successful_detections": 0
                }
            
            platform_stats[platform_name]["count"] += 1
            
            # Track successful detections (non-unknown platforms with indicators)
            if platform_name != "unknown" and metadata.platform_indicators:
                platform_stats[platform_name]["successful_detections"] += 1
                detected_platforms += 1
                
                # Collect confidence data (if available in indicators)
                confidence_indicators = [ind for ind in metadata.platform_indicators if "confidence:" in ind]
                if confidence_indicators:
                    try:
                        confidence_str = confidence_indicators[0].split("confidence: ")[1]
                        confidence = float(confidence_str)
                        if platform_name not in platform_confidence_sum:
                            platform_confidence_sum[platform_name] = []
                        platform_confidence_sum[platform_name].append(confidence)
                    except (ValueError, IndexError):
                        pass
            
            # Collect response time data
            if metadata.response_time_ms:
                if platform_name not in platform_response_times:
                    platform_response_times[platform_name] = []
                platform_response_times[platform_name].append(metadata.response_time_ms)
        
        # Calculate percentages and averages
        for platform_name, stats in platform_stats.items():
            stats["percentage"] = (stats["count"] / total_domains) * 100
            
            # Calculate average confidence
            if platform_name in platform_confidence_sum:
                confidences = platform_confidence_sum[platform_name]
                stats["avg_confidence"] = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Calculate average response time
            if platform_name in platform_response_times:
                times = platform_response_times[platform_name]
                stats["avg_response_time_ms"] = sum(times) / len(times) if times else 0.0
        
        # Calculate overall hit rates
        overall_detection_rate = (detected_platforms / total_domains) * 100 if total_domains > 0 else 0
        
        # Identify most/least detected platforms
        sorted_platforms = sorted(platform_stats.items(), key=lambda x: x[1]["successful_detections"], reverse=True)
        most_detected = sorted_platforms[0] if sorted_platforms else None
        least_detected = sorted_platforms[-1] if sorted_platforms else None
        
        return {
            "success": True,
            "overall_statistics": {
                "total_domains": total_domains,
                "platforms_detected": detected_platforms,
                "overall_detection_rate_percent": overall_detection_rate,
                "unique_platforms_found": len([p for p, s in platform_stats.items() if s["successful_detections"] > 0])
            },
            "platform_statistics": platform_stats,
            "top_platforms": {
                "most_detected": most_detected[0] if most_detected else None,
                "most_detected_count": most_detected[1]["successful_detections"] if most_detected else 0,
                "least_detected": least_detected[0] if least_detected and least_detected[1]["successful_detections"] > 0 else None
            },
            "performance_insights": self._generate_platform_performance_insights(platform_stats, overall_detection_rate)
        }
    
    def _generate_platform_performance_insights(self, platform_stats: Dict[str, Any], 
                                              overall_rate: float) -> List[str]:
        """Generate insights about platform detection performance"""
        insights = []
        
        # Detection rate insights
        if overall_rate > 70:
            insights.append(f"Excellent platform detection rate: {overall_rate:.1f}%")
        elif overall_rate > 50:
            insights.append(f"Good platform detection rate: {overall_rate:.1f}%")
        else:
            insights.append(f"Platform detection rate needs improvement: {overall_rate:.1f}%")
        
        # Platform-specific insights
        wordpress_stats = platform_stats.get("wordpress", {})
        if wordpress_stats.get("successful_detections", 0) > 0:
            wp_percentage = wordpress_stats.get("percentage", 0)
            insights.append(f"WordPress represents {wp_percentage:.1f}% of detected platforms")
        
        shopify_stats = platform_stats.get("shopify", {})
        if shopify_stats.get("successful_detections", 0) > 0:
            shopify_percentage = shopify_stats.get("percentage", 0)
            insights.append(f"Shopify e-commerce sites: {shopify_percentage:.1f}% of platforms")
        
        # Unknown platform analysis
        unknown_stats = platform_stats.get("unknown", {})
        unknown_percentage = unknown_stats.get("percentage", 0)
        if unknown_percentage > 40:
            insights.append(f"High percentage of unidentified platforms: {unknown_percentage:.1f}% - consider expanding detection signatures")
        
        return insights
    
    def get_exclusion_analysis(self) -> Dict[str, Any]:
        """
        Analyze domain exclusions and filtering decisions.
        
        Returns:
            Dictionary containing exclusion analysis
        """
        if not self.domains:
            return {"success": False, "error": "No domains available for analysis"}
        
        exclusion_stats = {}
        total_domains = len(self.domains)
        total_exclusions = 0
        inaccessible_count = 0
        
        # Collect exclusion data
        for domain, metadata in self.domains.items():
            # Count inaccessible domains
            if not metadata.is_accessible:
                inaccessible_count += 1
            
            # Analyze exclusion reasons
            for reason in metadata.exclusion_reasons:
                total_exclusions += 1
                
                # Categorize exclusion reasons
                category = self._categorize_exclusion_reason(reason)
                
                if category not in exclusion_stats:
                    exclusion_stats[category] = {
                        "count": 0,
                        "percentage": 0.0,
                        "specific_reasons": {}
                    }
                
                exclusion_stats[category]["count"] += 1
                
                # Track specific reasons within categories
                if reason not in exclusion_stats[category]["specific_reasons"]:
                    exclusion_stats[category]["specific_reasons"][reason] = 0
                exclusion_stats[category]["specific_reasons"][reason] += 1
        
        # Calculate percentages
        for category, stats in exclusion_stats.items():
            stats["percentage"] = (stats["count"] / total_exclusions) * 100 if total_exclusions > 0 else 0
        
        # Calculate accessibility rate
        accessibility_rate = ((total_domains - inaccessible_count) / total_domains) * 100 if total_domains > 0 else 0
        
        # Generate exclusion insights
        exclusion_insights = self._generate_exclusion_insights(exclusion_stats, accessibility_rate, total_domains)
        
        return {
            "success": True,
            "summary": {
                "total_domains": total_domains,
                "total_exclusions": total_exclusions,
                "inaccessible_domains": inaccessible_count,
                "accessibility_rate_percent": accessibility_rate,
                "exclusion_rate_percent": (total_exclusions / total_domains) * 100 if total_domains > 0 else 0
            },
            "exclusion_categories": exclusion_stats,
            "insights": exclusion_insights
        }
    
    def _categorize_exclusion_reason(self, reason: str) -> str:
        """Categorize exclusion reasons into broader categories"""
        reason_lower = reason.lower()
        
        if any(keyword in reason_lower for keyword in ["timeout", "connection", "network"]):
            return "connectivity_issues"
        elif any(keyword in reason_lower for keyword in ["http", "404", "500", "error"]):
            return "http_errors"
        elif any(keyword in reason_lower for keyword in ["scoring", "business", "low_score"]):
            return "quality_filtering"
        elif any(keyword in reason_lower for keyword in ["platform", "detection"]):
            return "platform_detection_issues"
        elif any(keyword in reason_lower for keyword in ["personal", "blog", "spam"]):
            return "content_filtering"
        else:
            return "other"
    
    def _generate_exclusion_insights(self, exclusion_stats: Dict[str, Any], 
                                   accessibility_rate: float, total_domains: int) -> List[str]:
        """Generate insights about exclusion patterns"""
        insights = []
        
        # Accessibility insights
        if accessibility_rate > 90:
            insights.append(f"Excellent accessibility: {accessibility_rate:.1f}% of domains reachable")
        elif accessibility_rate > 70:
            insights.append(f"Good accessibility: {accessibility_rate:.1f}% of domains reachable")
        else:
            insights.append(f"Accessibility concerns: Only {accessibility_rate:.1f}% of domains reachable")
        
        # Top exclusion categories
        if exclusion_stats:
            top_category = max(exclusion_stats.items(), key=lambda x: x[1]["count"])
            insights.append(f"Primary exclusion category: {top_category[0]} ({top_category[1]['percentage']:.1f}%)")
        
        # Connectivity insights
        connectivity_stats = exclusion_stats.get("connectivity_issues", {})
        if connectivity_stats.get("count", 0) > total_domains * 0.1:
            insights.append("High number of connectivity issues - consider adjusting timeout settings")
        
        # Quality filtering insights
        quality_stats = exclusion_stats.get("quality_filtering", {})
        if quality_stats.get("count", 0) > total_domains * 0.2:
            insights.append("Aggressive quality filtering detected - review scoring thresholds")
        
        return insights

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the classification process.
        
        Returns:
            Dictionary containing detailed statistics
        """
        # Update statistics
        self._update_statistics()
        
        return {
            "total_statistics": asdict(self.stats),
            "current_state": {
                "total_domains": len(self.domains),
                "domain_mappings": len(self.domain_to_normalized),
                "url_mappings": len(self.url_to_domain)
            },
            "type_distribution": self._get_type_distribution(),
            "platform_distribution": self._get_platform_distribution(),
            "priority_distribution": self._get_priority_distribution()
        }
    
    def _update_statistics(self):
        """Update the current statistics based on domain data"""
        if not self.domains:
            return
        
        # Count by website type
        type_counts = {}
        for metadata in self.domains.values():
            type_name = metadata.website_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        self.stats.business_websites = type_counts.get("business", 0)
        self.stats.ecommerce_websites = type_counts.get("ecommerce", 0)
        self.stats.personal_websites = type_counts.get("personal", 0)
        self.stats.blog_websites = type_counts.get("blog", 0)
        
        # Count by platform
        platform_counts = {}
        for metadata in self.domains.values():
            platform_name = metadata.platform_type.value
            platform_counts[platform_name] = platform_counts.get(platform_name, 0) + 1
        
        self.stats.wordpress_sites = platform_counts.get("wordpress", 0)
        self.stats.shopify_sites = platform_counts.get("shopify", 0)
        self.stats.custom_sites = platform_counts.get("custom", 0)
        
        # Count by priority
        priority_counts = {}
        for metadata in self.domains.values():
            priority_name = metadata.priority_level.value
            priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1
        
        self.stats.critical_priority = priority_counts.get("critical", 0)
        self.stats.high_priority = priority_counts.get("high", 0)
        self.stats.medium_priority = priority_counts.get("medium", 0)
        self.stats.low_priority = priority_counts.get("low", 0)
        self.stats.skip_priority = priority_counts.get("skip", 0)
        
        # Calculate averages
        business_scores = [m.business_score for m in self.domains.values() if m.business_score > 0]
        self.stats.average_business_score = sum(business_scores) / len(business_scores) if business_scores else 0.0
        
        crawl_budgets = [m.crawl_budget for m in self.domains.values()]
        self.stats.average_crawl_budget = sum(crawl_budgets) / len(crawl_budgets) if crawl_budgets else 0.0
        
        accessible_count = sum(1 for m in self.domains.values() if m.is_accessible)
        self.stats.accessibility_rate = accessible_count / len(self.domains) if self.domains else 0.0
        
        # Performance metrics
        if self.stats.processing_time_seconds > 0 and len(self.domains) > 0:
            self.stats.domains_per_second = len(self.domains) / self.stats.processing_time_seconds
    
    def _get_type_distribution(self) -> Dict[str, int]:
        """Get distribution of website types"""
        distribution = {}
        for metadata in self.domains.values():
            type_name = metadata.website_type.value
            distribution[type_name] = distribution.get(type_name, 0) + 1
        return distribution
    
    def _get_platform_distribution(self) -> Dict[str, int]:
        """Get distribution of platform types"""
        distribution = {}
        for metadata in self.domains.values():
            platform_name = metadata.platform_type.value
            distribution[platform_name] = distribution.get(platform_name, 0) + 1
        return distribution
    
    def _get_priority_distribution(self) -> Dict[str, int]:
        """Get distribution of priority levels"""
        distribution = {}
        for metadata in self.domains.values():
            priority_name = metadata.priority_level.value
            distribution[priority_name] = distribution.get(priority_name, 0) + 1
        return distribution
    
    def export_domains(self, format_type: str = "json") -> Dict[str, Any]:
        """
        Export domains in various formats.
        
        Args:
            format_type: Export format ("json", "csv_data", "list")
            
        Returns:
            Dictionary containing exported data
        """
        if format_type == "json":
            return {
                "domains": [asdict(metadata) for metadata in self.domains.values()],
                "statistics": self.get_statistics(),
                "export_timestamp": time.time()
            }
        elif format_type == "csv_data":
            # Return data suitable for CSV export
            rows = []
            for metadata in self.domains.values():
                rows.append({
                    "domain": metadata.domain,
                    "original_url": metadata.original_url,
                    "website_type": metadata.website_type.value,
                    "platform_type": metadata.platform_type.value,
                    "business_score": metadata.business_score,
                    "priority_level": metadata.priority_level.value,
                    "crawl_budget": metadata.crawl_budget,
                    "is_accessible": metadata.is_accessible,
                    "created_at": metadata.created_at
                })
            return {"rows": rows, "headers": list(rows[0].keys()) if rows else []}
        elif format_type == "list":
            return {"domains": list(self.domains.keys())}
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


class DomainClassifierAgent(Agent):
    """
    Agency Swarm agent for domain classification and prioritization.
    
    This agent coordinates the domain classification process using the
    DomainClassifier core class and provides tools for batch processing.
    """
    
    def __init__(self):
        super().__init__(
            name="DomainClassifier",
            description="Classifies and prioritizes business websites for crawling with comprehensive platform detection and scoring",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.1,
            max_prompt_tokens=25000,
        )
        
        # Initialize the domain classifier
        self.classifier = DomainClassifier()
        
        self.logger = logging.getLogger(f"{__name__}.DomainClassifierAgent")
        self.logger.info("DomainClassifierAgent initialized")