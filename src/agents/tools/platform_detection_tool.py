"""
Platform Detection Tool for Agency Swarm

Tool for detecting website platforms through HTTP probing and response analysis.
Supports WordPress, Shopify, and other popular platforms.
"""

import logging
import time
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
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
    from agents.domain_classifier_agent import PlatformType, DomainMetadata
except ImportError:
    # Fallback if import fails
    class PlatformType(Enum):
        WORDPRESS = "wordpress"
        SHOPIFY = "shopify"
        WIX = "wix"
        SQUARESPACE = "squarespace"
        CUSTOM = "custom"
        UNKNOWN = "unknown"

logger = logging.getLogger(__name__)


@dataclass
class PlatformSignature:
    """Definition of a platform detection signature"""
    platform: PlatformType
    name: str
    confidence: float  # 0.0 to 1.0
    
    # Detection methods
    url_patterns: List[str] = field(default_factory=list)
    header_patterns: Dict[str, str] = field(default_factory=dict)
    content_patterns: List[str] = field(default_factory=list)
    meta_patterns: List[str] = field(default_factory=list)
    endpoint_checks: List[str] = field(default_factory=list)
    
    # Additional metadata
    description: str = ""
    common_indicators: List[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    """Result of platform detection for a domain"""
    domain: str
    platform: PlatformType
    confidence: float
    detected_signatures: List[str] = field(default_factory=list)
    response_time_ms: float = 0.0
    status_code: Optional[int] = None
    error: Optional[str] = None
    
    # Additional detection data
    detected_version: Optional[str] = None
    detected_theme: Optional[str] = None
    detected_plugins: List[str] = field(default_factory=list)
    detected_technologies: List[str] = field(default_factory=list)
    
    # Probing details
    probed_urls: List[str] = field(default_factory=list)
    successful_probes: int = 0
    failed_probes: int = 0
    
    def add_signature(self, signature_name: str, confidence: float):
        """Add a detected signature and update confidence"""
        self.detected_signatures.append(signature_name)
        # Update confidence using weighted average
        current_weight = len(self.detected_signatures) - 1
        self.confidence = (self.confidence * current_weight + confidence) / len(self.detected_signatures)
        self.confidence = min(1.0, self.confidence)


class PlatformDetector:
    """
    Core platform detection engine using HTTP probing and response analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # HTTP configuration
        self.timeout = self.config.get("timeout", 10)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
        self.user_agent = self.config.get("user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Detection configuration
        self.max_content_length = self.config.get("max_content_length", 50000)  # 50KB max
        self.enable_content_analysis = self.config.get("enable_content_analysis", True)
        self.enable_meta_analysis = self.config.get("enable_meta_analysis", True)
        
        # Initialize platform signatures
        self.signatures = self._initialize_signatures()
        
        # Statistics
        self.stats = {
            "total_detections": 0,
            "successful_detections": 0,
            "failed_detections": 0,
            "platform_counts": {},
            "average_confidence": 0.0,
            "average_response_time": 0.0
        }
        
        if not REQUESTS_AVAILABLE:
            self.logger.warning("Requests library not available - using mock mode")
        
        self.logger.info(f"PlatformDetector initialized with {len(self.signatures)} signatures")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the platform detector"""
        logger = logging.getLogger(f"{__name__}.PlatformDetector")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_signatures(self) -> List[PlatformSignature]:
        """Initialize platform detection signatures"""
        signatures = []
        
        # WordPress signatures
        signatures.append(PlatformSignature(
            platform=PlatformType.WORDPRESS,
            name="wordpress_wp_json",
            confidence=0.95,
            endpoint_checks=["/wp-json/", "/wp-json/wp/v2/"],
            description="WordPress REST API endpoint"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.WORDPRESS,
            name="wordpress_wp_content",
            confidence=0.90,
            content_patterns=[
                r"/wp-content/themes/",
                r"/wp-content/plugins/",
                r"/wp-includes/",
                r"wp-emoji-release"
            ],
            description="WordPress content directories"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.WORDPRESS,
            name="wordpress_generator",
            confidence=0.85,
            meta_patterns=[
                r'<meta name="generator" content="WordPress[^"]*"',
                r'content="WordPress[^"]*"'
            ],
            description="WordPress generator meta tag"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.WORDPRESS,
            name="wordpress_headers",
            confidence=0.80,
            header_patterns={
                "x-pingback": r"xmlrpc\.php",
                "link": r"wp-json"
            },
            description="WordPress HTTP headers"
        ))
        
        # Shopify signatures
        signatures.append(PlatformSignature(
            platform=PlatformType.SHOPIFY,
            name="shopify_powered_by",
            confidence=0.95,
            header_patterns={
                "x-shopify-stage": r".*",
                "x-shopify-shop-api-call-limit": r".*",
                "server": r"cloudflare"
            },
            description="Shopify-specific headers"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.SHOPIFY,
            name="shopify_cdn",
            confidence=0.90,
            content_patterns=[
                r"cdn\.shopify\.com",
                r"shopify-analytics",
                r"Shopify\.theme",
                r"shop_money_format"
            ],
            description="Shopify CDN and JavaScript"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.SHOPIFY,
            name="shopify_myshopify",
            confidence=0.85,
            url_patterns=[r"\.myshopify\.com"],
            description="Shopify subdomain"
        ))
        
        # Wix signatures
        signatures.append(PlatformSignature(
            platform=PlatformType.WIX,
            name="wix_static",
            confidence=0.90,
            content_patterns=[
                r"static\.wixstatic\.com",
                r"wix\.com",
                r"wixstatic\.com"
            ],
            description="Wix static content"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.WIX,
            name="wix_generator",
            confidence=0.85,
            meta_patterns=[
                r'<meta name="generator" content="Wix[^"]*"'
            ],
            description="Wix generator meta tag"
        ))
        
        # Squarespace signatures
        signatures.append(PlatformSignature(
            platform=PlatformType.SQUARESPACE,
            name="squarespace_static",
            confidence=0.90,
            content_patterns=[
                r"static1\.squarespace\.com",
                r"squarespace\.com",
                r"Squarespace\.EXTENSIONS"
            ],
            description="Squarespace static content"
        ))
        
        signatures.append(PlatformSignature(
            platform=PlatformType.SQUARESPACE,
            name="squarespace_generator",
            confidence=0.85,
            meta_patterns=[
                r'<meta name="generator" content="Squarespace[^"]*"'
            ],
            description="Squarespace generator meta tag"
        ))
        
        return signatures
    
    def detect_platform(self, domain: str) -> DetectionResult:
        """
        Detect the platform for a given domain
        
        Args:
            domain: Domain to probe for platform detection
            
        Returns:
            DetectionResult with platform information
        """
        start_time = time.time()
        
        result = DetectionResult(
            domain=domain,
            platform=PlatformType.UNKNOWN,
            confidence=0.0
        )
        
        if not REQUESTS_AVAILABLE:
            # Mock detection for testing
            result.platform = PlatformType.CUSTOM
            result.confidence = 0.5
            result.error = "Requests library not available - mock result"
            return result
        
        try:
            self.logger.info(f"Starting platform detection for {domain}")
            
            # Prepare session
            session = requests.Session()
            session.headers.update({
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Prepare URLs to check
            base_url = f"https://{domain}"
            if not domain.startswith(('http://', 'https://')):
                urls_to_check = [f"https://{domain}", f"http://{domain}"]
            else:
                urls_to_check = [domain]
            
            # Main detection process
            for base_url in urls_to_check:
                try:
                    # Get main page
                    main_result = self._probe_url(session, base_url, result)
                    if main_result:
                        break
                except Exception as e:
                    self.logger.debug(f"Failed to probe {base_url}: {e}")
                    continue
            
            # Additional endpoint checks
            if result.platform == PlatformType.UNKNOWN:
                self._check_additional_endpoints(session, base_url, result)
            
            # Finalize result
            response_time = (time.time() - start_time) * 1000
            result.response_time_ms = response_time
            
            # Update statistics
            self._update_statistics(result)
            
            self.logger.info(f"Platform detection completed for {domain}: "
                           f"{result.platform.value} (confidence: {result.confidence:.2f})")
            
        except Exception as e:
            result.error = str(e)
            result.platform = PlatformType.UNKNOWN
            self.logger.error(f"Error detecting platform for {domain}: {e}")
        
        return result
    
    def _probe_url(self, session: requests.Session, url: str, result: DetectionResult) -> bool:
        """
        Probe a single URL for platform indicators
        
        Returns:
            True if successful probe, False otherwise
        """
        try:
            result.probed_urls.append(url)
            
            # Make HEAD request first for headers
            head_response = session.head(url, timeout=self.timeout, allow_redirects=True)
            result.status_code = head_response.status_code
            
            if head_response.status_code == 200:
                # Check headers
                self._analyze_headers(head_response.headers, result)
                
                # If we have enough confidence from headers, skip content analysis
                if result.confidence >= 0.8:
                    result.successful_probes += 1
                    return True
                
                # Get content for deeper analysis
                if self.enable_content_analysis:
                    get_response = session.get(url, timeout=self.timeout, allow_redirects=True)
                    content = get_response.text[:self.max_content_length]
                    
                    # Analyze content
                    self._analyze_content(content, result)
                    
                    # Analyze meta tags
                    if self.enable_meta_analysis:
                        self._analyze_meta_tags(content, result)
                
                result.successful_probes += 1
                return True
            else:
                result.failed_probes += 1
                return False
                
        except Exception as e:
            result.failed_probes += 1
            self.logger.debug(f"Failed to probe {url}: {e}")
            return False
    
    def _analyze_headers(self, headers: Dict[str, str], result: DetectionResult):
        """Analyze HTTP headers for platform signatures"""
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        
        for signature in self.signatures:
            if not signature.header_patterns:
                continue
            
            matches = 0
            total_patterns = len(signature.header_patterns)
            
            for header_name, pattern in signature.header_patterns.items():
                header_value = headers_lower.get(header_name.lower(), "")
                if re.search(pattern, header_value, re.IGNORECASE):
                    matches += 1
            
            # Calculate confidence based on match ratio
            if matches > 0:
                match_confidence = (matches / total_patterns) * signature.confidence
                if match_confidence > result.confidence:
                    result.platform = signature.platform
                    result.add_signature(signature.name, match_confidence)
    
    def _analyze_content(self, content: str, result: DetectionResult):
        """Analyze page content for platform signatures"""
        for signature in self.signatures:
            if not signature.content_patterns:
                continue
            
            matches = 0
            for pattern in signature.content_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                # Weight confidence by number of matches
                match_confidence = min(1.0, (matches / len(signature.content_patterns)) * signature.confidence)
                if match_confidence > result.confidence:
                    result.platform = signature.platform
                    result.add_signature(signature.name, match_confidence)
    
    def _analyze_meta_tags(self, content: str, result: DetectionResult):
        """Analyze meta tags for platform signatures"""
        for signature in self.signatures:
            if not signature.meta_patterns:
                continue
            
            for pattern in signature.meta_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    if signature.confidence > result.confidence:
                        result.platform = signature.platform
                        result.add_signature(signature.name, signature.confidence)
    
    def _check_additional_endpoints(self, session: requests.Session, base_url: str, result: DetectionResult):
        """Check additional endpoints for platform detection"""
        for signature in self.signatures:
            if not signature.endpoint_checks:
                continue
            
            for endpoint in signature.endpoint_checks:
                try:
                    check_url = urljoin(base_url, endpoint)
                    response = session.head(check_url, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        if signature.confidence > result.confidence:
                            result.platform = signature.platform
                            result.add_signature(signature.name, signature.confidence)
                        break
                
                except Exception:
                    continue
    
    def _update_statistics(self, result: DetectionResult):
        """Update detection statistics"""
        self.stats["total_detections"] += 1
        
        if result.error:
            self.stats["failed_detections"] += 1
        else:
            self.stats["successful_detections"] += 1
            
            # Update platform counts
            platform_name = result.platform.value
            self.stats["platform_counts"][platform_name] = self.stats["platform_counts"].get(platform_name, 0) + 1
            
            # Update averages
            total_successful = self.stats["successful_detections"]
            current_avg_conf = self.stats["average_confidence"]
            current_avg_time = self.stats["average_response_time"]
            
            self.stats["average_confidence"] = (current_avg_conf * (total_successful - 1) + result.confidence) / total_successful
            self.stats["average_response_time"] = (current_avg_time * (total_successful - 1) + result.response_time_ms) / total_successful
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics"""
        return self.stats.copy()
    
    def detect_multiple_platforms(self, domains: List[str]) -> List[DetectionResult]:
        """
        Detect platforms for multiple domains
        
        Args:
            domains: List of domains to analyze
            
        Returns:
            List of DetectionResult objects
        """
        results = []
        
        self.logger.info(f"Starting batch platform detection for {len(domains)} domains")
        
        for domain in domains:
            try:
                result = self.detect_platform(domain)
                results.append(result)
                
                # Add small delay between requests to be polite
                time.sleep(0.1)
                
            except Exception as e:
                error_result = DetectionResult(
                    domain=domain,
                    platform=PlatformType.UNKNOWN,
                    confidence=0.0,
                    error=str(e)
                )
                results.append(error_result)
        
        self.logger.info(f"Batch platform detection completed: {len(results)} results")
        
        return results


class PlatformDetectionTool(BaseTool):
    """
    Agency Swarm tool for platform detection
    """
    
    domains: List[str] = Field(
        ...,
        description="List of domains to analyze for platform detection"
    )
    
    timeout: int = Field(
        default=10,
        description="Timeout in seconds for HTTP requests"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    
    enable_content_analysis: bool = Field(
        default=True,
        description="Whether to analyze page content for platform detection"
    )
    
    enable_meta_analysis: bool = Field(
        default=True,
        description="Whether to analyze meta tags for platform detection"
    )
    
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="User agent string for HTTP requests"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Run platform detection on the provided domains
        
        Returns:
            Dictionary containing detection results and statistics
        """
        start_time = time.time()
        
        # Initialize platform detector
        config = {
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "enable_content_analysis": self.enable_content_analysis,
            "enable_meta_analysis": self.enable_meta_analysis,
            "user_agent": self.user_agent,
            "log_level": logging.INFO
        }
        
        detector = PlatformDetector(config)
        
        logger.info(f"Starting platform detection for {len(self.domains)} domains")
        
        try:
            # Run detection
            results = detector.detect_multiple_platforms(self.domains)
            
            # Process results
            platform_summary = {}
            successful_detections = 0
            total_confidence = 0.0
            
            for result in results:
                platform_name = result.platform.value
                platform_summary[platform_name] = platform_summary.get(platform_name, 0) + 1
                
                if not result.error:
                    successful_detections += 1
                    total_confidence += result.confidence
            
            # Calculate summary statistics
            processing_time = time.time() - start_time
            average_confidence = total_confidence / successful_detections if successful_detections > 0 else 0.0
            success_rate = successful_detections / len(self.domains) if self.domains else 0.0
            
            logger.info(f"Platform detection completed: {successful_detections}/{len(self.domains)} successful "
                       f"(success rate: {success_rate:.2%}) in {processing_time:.2f}s")
            
            return {
                "success": True,
                "processing_summary": {
                    "total_domains": len(self.domains),
                    "successful_detections": successful_detections,
                    "failed_detections": len(self.domains) - successful_detections,
                    "success_rate": success_rate,
                    "average_confidence": average_confidence,
                    "processing_time_seconds": processing_time
                },
                "platform_summary": platform_summary,
                "detection_results": [asdict(result) for result in results],
                "detector_statistics": detector.get_statistics(),
                "configuration": config
            }
            
        except Exception as e:
            logger.error(f"Error during platform detection: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time,
                "partial_results": None
            }