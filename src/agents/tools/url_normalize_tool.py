"""
URL Normalize Tool for Agency Swarm

Tool for normalizing and cleaning URLs extracted from SERPs,
including redirect unwrapping and tracking parameter removal.
"""

import logging
import re
import base64
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote, urlunparse, urljoin
from dataclasses import dataclass, asdict

from agency_swarm.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


@dataclass
class NormalizedUrl:
    """Represents a normalized URL with metadata"""
    original_url: str
    normalized_url: str
    domain: str
    is_valid: bool
    changes_made: List[str]
    redirect_unwrapped: bool = False
    tracking_removed: bool = False
    protocol_upgraded: bool = False
    www_normalized: bool = False
    path_normalized: bool = False
    error_message: Optional[str] = None
    
    def __post_init__(self):
        # Extract domain from normalized URL
        if self.normalized_url and not self.domain:
            try:
                parsed = urlparse(self.normalized_url)
                self.domain = parsed.netloc.lower()
                if self.domain.startswith('www.'):
                    self.domain = self.domain[4:]
            except Exception:
                self.domain = "unknown"


class UrlNormalizeTool(BaseTool):
    """
    Tool for normalizing and cleaning URLs extracted from search results.
    
    This tool handles:
    - Unwrapping Bing redirect URLs to get final destinations
    - Protocol normalization (http→https)
    - Domain standardization (www vs non-www)
    - Path normalization and encoding fixes
    - Tracking parameter removal (utm_, fbclid, gclid, etc.)
    - Fragment and session ID removal
    - URL validation and malformed URL recovery
    - IDN domain handling
    """
    
    urls: List[str] = Field(
        ...,
        description="List of URLs to normalize and clean"
    )
    
    remove_tracking: bool = Field(
        default=True,
        description="Whether to remove tracking parameters"
    )
    
    unwrap_redirects: bool = Field(
        default=True,
        description="Whether to unwrap search engine redirect URLs"
    )
    
    normalize_protocol: bool = Field(
        default=True,
        description="Whether to normalize protocols (http→https)"
    )
    
    normalize_www: bool = Field(
        default=True,
        description="Whether to normalize www subdomains"
    )
    
    normalize_path: bool = Field(
        default=True,
        description="Whether to normalize URL paths"
    )
    
    validate_urls: bool = Field(
        default=True,
        description="Whether to validate URL format"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _get_tracking_params(self) -> set:
        """Get set of tracking parameters to remove"""
        return {
            # Google Analytics
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'utm_name', 'utm_cid', 'utm_reader', 'utm_viz_id', 'utm_pubreferrer',
            
            # Facebook
            'fbclid', 'fb_action_ids', 'fb_action_types', 'fb_ref', 'fb_source',
            
            # Google Ads
            'gclid', 'gclsrc', 'dclid', 'wbraid', 'gbraid',
            
            # Microsoft/Bing
            'msclkid', 'microsoft_clientid',
            
            # Generic tracking
            'ref', 'referrer', 'source', 'campaign', 'medium',
            'mc_cid', 'mc_eid',  # MailChimp
            'pk_campaign', 'pk_kwd', 'pk_content',  # Piwik
            '_ga', '_gid', '_gat',  # Google Analytics cookies in URL
            
            # Social media
            'igshid',  # Instagram
            'tt_medium', 'tt_content',  # TikTok
            
            # E-commerce
            'aff_id', 'affiliate_id', 'partner_id',
            'promo_code', 'discount_code',
            
            # Session/tracking IDs
            'session_id', 'sessionid', 'sid', 'PHPSESSID', 'jsessionid',
            '_hsenc', '_hsmi',  # HubSpot
            
            # Email tracking
            'email_id', 'email_campaign', 'email_source'
        }
    
    def _get_bing_redirect_patterns(self) -> List:
        """Get Bing redirect patterns"""
        return [
            re.compile(r'https?://www\.bing\.com/ck/a\?.+?&u=([^&]+)'),
            re.compile(r'https?://www\.bing\.com/aclick\?.+?url=([^&]+)'),
            re.compile(r'https?://www\.bing\.com/acjk\?.+?&u=([^&]+)'),
            re.compile(r'https?://cc\.bingj\.com/cache\.aspx\?.+?&u=([^&]+)')
        ]
    
    def run(self) -> Dict[str, Any]:
        """
        Normalize and clean the provided URLs.
        
        Returns:
            Dictionary containing normalized URLs and processing statistics
        """
        start_time = time.time()
        
        # Initialize patterns and parameters
        self.tracking_params = self._get_tracking_params()
        self.bing_redirect_patterns = self._get_bing_redirect_patterns()
        
        logger.info(f"Starting URL normalization for {len(self.urls)} URLs")
        
        normalized_results = []
        stats = {
            "total_urls": len(self.urls),
            "successfully_normalized": 0,
            "redirects_unwrapped": 0,
            "tracking_removed": 0,
            "protocols_upgraded": 0,
            "www_normalized": 0,
            "paths_normalized": 0,
            "validation_failures": 0
        }
        
        for original_url in self.urls:
            try:
                result = self._normalize_single_url(original_url)
                normalized_results.append(result)
                
                # Update statistics
                if result.is_valid:
                    stats["successfully_normalized"] += 1
                else:
                    stats["validation_failures"] += 1
                
                if result.redirect_unwrapped:
                    stats["redirects_unwrapped"] += 1
                if result.tracking_removed:
                    stats["tracking_removed"] += 1
                if result.protocol_upgraded:
                    stats["protocols_upgraded"] += 1
                if result.www_normalized:
                    stats["www_normalized"] += 1
                if result.path_normalized:
                    stats["paths_normalized"] += 1
                    
            except Exception as e:
                logger.error(f"Error normalizing URL '{original_url}': {e}")
                error_result = NormalizedUrl(
                    original_url=original_url,
                    normalized_url=original_url,
                    domain="unknown",
                    is_valid=False,
                    changes_made=[],
                    error_message=str(e)
                )
                normalized_results.append(error_result)
                stats["validation_failures"] += 1
        
        processing_time = time.time() - start_time
        
        logger.info(f"URL normalization completed: {stats['successfully_normalized']}/{stats['total_urls']} "
                   f"successful in {processing_time:.2f}s")
        
        return {
            "success": True,
            "total_urls": stats["total_urls"],
            "processing_time_seconds": processing_time,
            "statistics": stats,
            "normalized_urls": [asdict(result) for result in normalized_results],
            "valid_urls": [result.normalized_url for result in normalized_results if result.is_valid],
            "invalid_urls": [(result.original_url, result.error_message) 
                           for result in normalized_results if not result.is_valid]
        }
    
    def _normalize_single_url(self, url: str) -> NormalizedUrl:
        """Normalize a single URL with comprehensive processing"""
        changes_made = []
        current_url = url.strip()
        
        # Initialize result object
        result = NormalizedUrl(
            original_url=url,
            normalized_url=current_url,
            domain="",
            is_valid=True,
            changes_made=changes_made
        )
        
        try:
            # Step 1: Unwrap redirects
            if self.unwrap_redirects:
                unwrapped_url = self._unwrap_redirect_url(current_url)
                if unwrapped_url != current_url:
                    current_url = unwrapped_url
                    result.redirect_unwrapped = True
                    changes_made.append("redirect_unwrapped")
            
            # Step 2: Basic URL validation and parsing
            if not self._is_valid_url_format(current_url):
                result.is_valid = False
                result.error_message = "Invalid URL format"
                result.normalized_url = current_url
                return result
            
            # Parse URL components
            parsed = urlparse(current_url)
            if not parsed.netloc:
                result.is_valid = False
                result.error_message = "Missing domain"
                result.normalized_url = current_url
                return result
            
            # Step 3: Protocol normalization
            scheme = parsed.scheme.lower()
            if self.normalize_protocol and scheme == 'http':
                scheme = 'https'
                result.protocol_upgraded = True
                changes_made.append("protocol_upgraded")
            
            # Step 4: Domain normalization
            netloc = parsed.netloc.lower()
            if self.normalize_www:
                if netloc.startswith('www.') and len(netloc) > 4:
                    # Remove www. prefix
                    netloc_no_www = netloc[4:]
                    # Keep www only if it's essential (some sites require it)
                    if not self._requires_www(netloc_no_www):
                        netloc = netloc_no_www
                        result.www_normalized = True
                        changes_made.append("www_removed")
            
            # Step 5: Path normalization
            path = parsed.path
            if self.normalize_path:
                normalized_path = self._normalize_path(path)
                if normalized_path != path:
                    path = normalized_path
                    result.path_normalized = True
                    changes_made.append("path_normalized")
            
            # Step 6: Query parameter cleaning
            query = parsed.query
            if self.remove_tracking and query:
                cleaned_query = self._remove_tracking_parameters(query)
                if cleaned_query != query:
                    query = cleaned_query
                    result.tracking_removed = True
                    changes_made.append("tracking_removed")
            
            # Step 7: Fragment removal (typically not needed for business URLs)
            fragment = ""  # Remove fragments by default
            if parsed.fragment:
                changes_made.append("fragment_removed")
            
            # Step 8: Reconstruct URL
            normalized_components = (scheme, netloc, path, parsed.params, query, fragment)
            result.normalized_url = urlunparse(normalized_components)
            
            # Step 9: Final validation
            if self.validate_urls:
                if not self._validate_final_url(result.normalized_url):
                    result.is_valid = False
                    result.error_message = "Final URL validation failed"
            
            # Extract domain for result
            result.domain = netloc
            if result.domain.startswith('www.'):
                result.domain = result.domain[4:]
            
        except Exception as e:
            result.is_valid = False
            result.error_message = f"Normalization error: {str(e)}"
            result.normalized_url = url
        
        return result
    
    def _unwrap_redirect_url(self, url: str) -> str:
        """Unwrap search engine redirect URLs"""
        try:
            # Try Bing redirect patterns
            for pattern in self.bing_redirect_patterns:
                match = pattern.search(url)
                if match:
                    encoded_url = match.group(1)
                    
                    # Try base64 decoding (common in Bing)
                    try:
                        decoded_bytes = base64.b64decode(encoded_url + '==')  # Add padding
                        decoded_url = decoded_bytes.decode('utf-8')
                        if decoded_url.startswith('http'):
                            return decoded_url
                    except Exception:
                        pass
                    
                    # Try URL decoding
                    try:
                        decoded_url = unquote(encoded_url)
                        if decoded_url.startswith('http'):
                            return decoded_url
                    except Exception:
                        pass
            
            # Try extracting from common redirect parameters
            parsed = urlparse(url)
            if parsed.query:
                params = parse_qs(parsed.query)
                
                # Common redirect parameter names
                redirect_params = ['url', 'u', 'link', 'target', 'destination', 'redirect']
                
                for param in redirect_params:
                    if param in params and params[param]:
                        candidate_url = params[param][0]
                        
                        # Try decoding
                        try:
                            candidate_url = unquote(candidate_url)
                            if candidate_url.startswith('http'):
                                return candidate_url
                        except Exception:
                            pass
                        
                        # Try base64 decoding
                        try:
                            decoded_bytes = base64.b64decode(candidate_url + '==')
                            decoded_url = decoded_bytes.decode('utf-8')
                            if decoded_url.startswith('http'):
                                return decoded_url
                        except Exception:
                            pass
            
        except Exception as e:
            logger.debug(f"Error unwrapping redirect URL: {e}")
        
        return url
    
    def _is_valid_url_format(self, url: str) -> bool:
        """Check if URL has valid format"""
        if not url or len(url) < 7:  # Minimum: http://a
            return False
        
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc)
        except Exception:
            return False
    
    def _requires_www(self, domain: str) -> bool:
        """Check if domain requires www subdomain"""
        # Some domains only work with www
        www_required_patterns = [
            # Banking/Financial sites often require www
            r'.*bank.*\.com$',
            r'.*credit.*\.com$',
            
            # Some legacy sites
            r'.*\.gov\..*$',
            r'.*\.edu\..*$'
        ]
        
        for pattern in www_required_patterns:
            if re.match(pattern, domain, re.IGNORECASE):
                return True
        
        return False
    
    def _normalize_path(self, path: str) -> str:
        """Normalize URL path"""
        if not path:
            return "/"
        
        # Remove double slashes
        path = re.sub(r'/+', '/', path)
        
        # Remove trailing slash for non-root paths
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # URL decode path components
        try:
            path = unquote(path)
        except Exception:
            pass
        
        return path
    
    def _remove_tracking_parameters(self, query: str) -> str:
        """Remove tracking parameters from query string"""
        if not query:
            return ""
        
        try:
            params = parse_qs(query, keep_blank_values=True)
            cleaned_params = {}
            
            for key, values in params.items():
                # Skip tracking parameters
                if key.lower() not in self.tracking_params:
                    # Also check for pattern matches
                    is_tracking = False
                    for tracking_param in self.tracking_params:
                        if tracking_param in key.lower():
                            is_tracking = True
                            break
                    
                    if not is_tracking:
                        cleaned_params[key] = values
            
            # Reconstruct query string
            if cleaned_params:
                from urllib.parse import urlencode
                return urlencode(cleaned_params, doseq=True)
            else:
                return ""
                
        except Exception as e:
            logger.debug(f"Error cleaning query parameters: {e}")
            return query
    
    def _validate_final_url(self, url: str) -> bool:
        """Validate the final normalized URL"""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check netloc
            if not parsed.netloc or '.' not in parsed.netloc:
                return False
            
            # Check for obviously invalid domains
            invalid_patterns = [
                r'localhost',
                r'127\.0\.0\.1',
                r'\.local$',
                r'\.invalid$',
                r'\.test$'
            ]
            
            for pattern in invalid_patterns:
                if re.search(pattern, parsed.netloc, re.IGNORECASE):
                    return False
            
            return True
            
        except Exception:
            return False