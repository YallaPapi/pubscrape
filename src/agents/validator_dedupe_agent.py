"""
Validator Dedupe Agent

Agency Swarm agent for validating email addresses and removing duplicates from
extracted contact data. Provides comprehensive email validation, deduplication,
blacklist filtering, and quality scoring for contact datasets.
"""

import logging
import re
import time
import dns.resolver
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from urllib.parse import urlparse
from collections import defaultdict, Counter
import concurrent.futures
import threading
from email_validator import validate_email, EmailNotValidError

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

from pydantic import Field, BaseModel


class ValidationStatus(Enum):
    """Email validation status"""
    VALID = "valid"
    INVALID_SYNTAX = "invalid_syntax"
    INVALID_DOMAIN = "invalid_domain"
    BLACKLISTED = "blacklisted"
    DUPLICATE = "duplicate"
    NO_MX_RECORD = "no_mx_record"
    DNS_ERROR = "dns_error"
    UNKNOWN_ERROR = "unknown_error"


class EmailQuality(Enum):
    """Email quality levels"""
    HIGH = "high"        # Business emails, decision makers
    MEDIUM = "medium"    # Standard business contacts
    LOW = "low"          # Generic or uncertain emails
    SPAM = "spam"        # Unwanted or invalid emails


@dataclass
class ValidationResult:
    """Result of email validation"""
    email: str
    status: ValidationStatus
    is_valid: bool = False
    quality: EmailQuality = EmailQuality.LOW
    confidence_score: float = 0.0
    reason: str = ""
    normalized_email: str = ""
    domain: str = ""
    mx_records: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0
    
    # Additional metadata
    tld: str = ""
    is_business_domain: bool = False
    is_personal_domain: bool = False
    blacklist_match: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['status'] = self.status.value
        result['quality'] = self.quality.value
        return result


@dataclass
class ContactRecord:
    """Unified contact record for deduplication"""
    primary_email: str
    all_emails: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    companies: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    social_profiles: List[str] = field(default_factory=list)
    
    # Source tracking
    source_urls: List[str] = field(default_factory=list)
    discovery_methods: List[str] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    
    # Aggregated metrics
    best_confidence: float = 0.0
    total_occurrences: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.primary_email not in self.all_emails:
            self.all_emails.insert(0, self.primary_email)
        
        # Extract domain from primary email
        if '@' in self.primary_email:
            domain = self.primary_email.split('@')[1].lower()
            if domain not in self.domains:
                self.domains.append(domain)
    
    def merge_with(self, other: 'ContactRecord'):
        """Merge another contact record into this one"""
        # Merge email addresses
        for email in other.all_emails:
            if email not in self.all_emails:
                self.all_emails.append(email)
        
        # Merge other fields
        for name in other.names:
            if name not in self.names:
                self.names.append(name)
        
        for title in other.titles:
            if title not in self.titles:
                self.titles.append(title)
        
        for company in other.companies:
            if company not in self.companies:
                self.companies.append(company)
        
        for domain in other.domains:
            if domain not in self.domains:
                self.domains.append(domain)
        
        for phone in other.phone_numbers:
            if phone not in self.phone_numbers:
                self.phone_numbers.append(phone)
        
        for profile in other.social_profiles:
            if profile not in self.social_profiles:
                self.social_profiles.append(profile)
        
        # Merge source tracking
        self.source_urls.extend(other.source_urls)
        self.discovery_methods.extend(other.discovery_methods)
        self.confidence_scores.extend(other.confidence_scores)
        
        # Update aggregated metrics
        self.best_confidence = max(self.best_confidence, other.best_confidence)
        self.total_occurrences += other.total_occurrences
        self.first_seen = min(self.first_seen, other.first_seen)
        self.last_seen = max(self.last_seen, other.last_seen)


class EmailSyntaxValidator:
    """
    Advanced email syntax validation with TLD whitelist support.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Load TLD whitelist
        self.tld_whitelist = self._load_tld_whitelist()
        
        # Performance settings
        self.use_strict_validation = self.config.get("strict_validation", True)
        self.check_deliverability = self.config.get("check_deliverability", False)
        
        self.logger.info(f"EmailSyntaxValidator initialized with {len(self.tld_whitelist)} whitelisted TLDs")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailSyntaxValidator")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _load_tld_whitelist(self) -> Set[str]:
        """Load TLD whitelist from configuration or use defaults"""
        # Default common business TLDs
        default_tlds = {
            # Generic TLDs
            'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
            'info', 'biz', 'name', 'pro', 'museum', 'coop', 'aero',
            
            # New generic TLDs (popular business ones)
            'app', 'tech', 'digital', 'online', 'website', 'store',
            'company', 'business', 'enterprises', 'solutions',
            'consulting', 'agency', 'group', 'partners', 'services',
            
            # Country code TLDs (major ones)
            'us', 'uk', 'ca', 'au', 'de', 'fr', 'it', 'es', 'nl',
            'se', 'no', 'dk', 'fi', 'pl', 'ru', 'cn', 'jp', 'kr',
            'in', 'br', 'mx', 'ar', 'cl', 'za', 'il', 'ae', 'sg',
            'hk', 'tw', 'th', 'my', 'id', 'ph', 'vn', 'nz', 'ie',
            
            # Country code second-level domains
            'co.uk', 'com.au', 'co.in', 'co.za', 'com.br', 'com.mx',
            'co.jp', 'co.kr', 'com.cn', 'com.sg', 'com.hk', 'com.tw'
        }
        
        # Load custom TLDs from config if provided
        custom_tlds = self.config.get("tld_whitelist", [])
        if custom_tlds:
            return set(custom_tlds)
        
        return default_tlds
    
    def validate_syntax(self, email: str) -> ValidationResult:
        """
        Validate email syntax and TLD.
        
        Args:
            email: Email address to validate
            
        Returns:
            ValidationResult with validation details
        """
        start_time = time.time()
        
        if not email or not isinstance(email, str):
            return ValidationResult(
                email=email or "",
                status=ValidationStatus.INVALID_SYNTAX,
                reason="Empty or invalid email input",
                validation_time_ms=(time.time() - start_time) * 1000
            )
        
        # Normalize email
        normalized_email = email.strip().lower()
        
        try:
            # Use email-validator for comprehensive validation
            validated = validate_email(
                normalized_email,
                check_deliverability=self.check_deliverability
            )
            
            normalized_email = validated.email
            domain = normalized_email.split('@')[1]
            
            # Extract TLD
            tld = self._extract_tld(domain)
            
            # Check against TLD whitelist
            if tld not in self.tld_whitelist:
                return ValidationResult(
                    email=email,
                    status=ValidationStatus.INVALID_DOMAIN,
                    normalized_email=normalized_email,
                    domain=domain,
                    tld=tld,
                    reason=f"TLD '{tld}' not in whitelist",
                    validation_time_ms=(time.time() - start_time) * 1000
                )
            
            # Determine domain type
            is_business_domain = self._is_business_domain(domain)
            is_personal_domain = self._is_personal_domain(domain)
            
            # Calculate quality score (no Mailtester data available in syntax-only validation)
            quality, confidence = self._assess_email_quality(normalized_email, domain, mailtester_data=None)
            
            validation_time = (time.time() - start_time) * 1000
            
            return ValidationResult(
                email=email,
                status=ValidationStatus.VALID,
                is_valid=True,
                quality=quality,
                confidence_score=confidence,
                normalized_email=normalized_email,
                domain=domain,
                tld=tld,
                is_business_domain=is_business_domain,
                is_personal_domain=is_personal_domain,
                reason="Valid email syntax and TLD",
                validation_time_ms=validation_time
            )
            
        except EmailNotValidError as e:
            validation_time = (time.time() - start_time) * 1000
            
            return ValidationResult(
                email=email,
                status=ValidationStatus.INVALID_SYNTAX,
                normalized_email=normalized_email,
                reason=f"Syntax validation failed: {str(e)}",
                validation_time_ms=validation_time
            )
        
        except Exception as e:
            validation_time = (time.time() - start_time) * 1000
            self.logger.error(f"Unexpected validation error for {email}: {e}")
            
            return ValidationResult(
                email=email,
                status=ValidationStatus.UNKNOWN_ERROR,
                reason=f"Validation error: {str(e)}",
                validation_time_ms=validation_time
            )
    
    def _extract_tld(self, domain: str) -> str:
        """Extract TLD from domain"""
        # Handle multi-part TLDs like co.uk
        parts = domain.split('.')
        
        # Check for known multi-part TLDs first
        if len(parts) >= 3:
            two_part_tld = '.'.join(parts[-2:])
            if two_part_tld in self.tld_whitelist:
                return two_part_tld
        
        # Return single-part TLD
        return parts[-1] if parts else domain
    
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
            'mail.com', 'gmx.com', 'web.de'
        }
        
        return domain.lower() in personal_domains
    
    def _assess_email_quality(self, email: str, domain: str, mailtester_data: Optional[Dict[str, Any]] = None) -> Tuple[EmailQuality, float]:
        """
        Assess email quality and confidence, incorporating Mailtester API results when available.
        
        Args:
            email: Email address to assess
            domain: Domain part of the email
            mailtester_data: Optional Mailtester validation results
            
        Returns:
            Tuple of (EmailQuality, confidence_score)
        """
        email_lower = email.lower()
        local_part = email_lower.split('@')[0]
        
        # Start with Mailtester score if available, otherwise use base confidence
        if mailtester_data and 'mailtester_score' in mailtester_data:
            confidence = mailtester_data['mailtester_score']
            
            # Apply Mailtester-specific adjustments
            if mailtester_data.get('is_disposable', False):
                confidence = max(0.0, confidence - 0.4)
            
            if mailtester_data.get('is_role_account', False) and not mailtester_data.get('is_disposable', False):
                confidence = min(1.0, confidence + 0.15)  # Business role accounts are valuable
            
            if mailtester_data.get('smtp_verified', False):
                confidence = min(1.0, confidence + 0.2)  # SMTP verification is highly valuable
            
            if mailtester_data.get('is_catch_all', False):
                confidence = max(0.0, confidence - 0.1)  # Catch-all domains are less reliable
                
            # Additional bonus for domain existence and MX records
            if mailtester_data.get('has_mx_records', False) and mailtester_data.get('domain_exists', False):
                confidence = min(1.0, confidence + 0.1)
        else:
            # Fallback to traditional pattern-based scoring
            confidence = 0.5  # Base confidence
            
            # High-quality indicators
            high_quality_patterns = [
                r'^(ceo|founder|president|director|manager|lead|head|chief|owner)@',
                r'^(contact|business|sales|marketing|pr|press|media)@',
                r'^[a-z]+\.[a-z]+@',  # firstname.lastname format
            ]
            
            for pattern in high_quality_patterns:
                if re.match(pattern, email_lower):
                    confidence += 0.3
                    break
            
            # Medium-quality patterns
            medium_quality_patterns = [
                r'^(info|hello|team|support|admin|hr)@',
                r'^[a-z]+@',  # Simple name
            ]
            
            for pattern in medium_quality_patterns:
                if re.match(pattern, email_lower):
                    confidence += 0.1
                    break
            
            # Low-quality/spam patterns (penalties)
            spam_patterns = [
                r'^(noreply|no-reply|donotreply|test|testing|example)@',
                r'^(webmaster|postmaster|administrator|root)@',
            ]
            
            for pattern in spam_patterns:
                if re.match(pattern, email_lower):
                    confidence -= 0.4
                    break
            
            # Domain type adjustments
            if self._is_business_domain(domain):
                confidence += 0.2
            elif self._is_personal_domain(domain):
                confidence -= 0.1
            
            # Format bonuses
            if '.' in local_part:
                confidence += 0.1  # firstname.lastname format
            
            if len(local_part) >= 4:  # Not too short
                confidence += 0.05
        
        # Universal pattern bonuses (apply regardless of validation method)
        # Executive/decision maker patterns
        executive_patterns = [
            r'(ceo|founder|president|director|vp|vice.?president)',
            r'(chief|head|lead|manager|owner)',
            r'(partner|principal|senior|sr\.?)'
        ]
        
        for pattern in executive_patterns:
            if re.search(pattern, local_part, re.IGNORECASE):
                confidence = min(1.0, confidence + 0.1)
                break
        
        # Professional format bonuses
        if re.match(r'^[a-z]+\.[a-z]+$', local_part):  # firstname.lastname
            confidence = min(1.0, confidence + 0.05)
        elif re.match(r'^[a-z][a-z]+$', local_part) and len(local_part) >= 4:  # reasonable name length
            confidence = min(1.0, confidence + 0.02)
        
        # Ensure confidence is within bounds
        confidence = max(0.0, min(1.0, confidence))
        
        # Determine quality level with enhanced thresholds for API-validated emails
        if mailtester_data:
            # Use enhanced thresholds when we have API validation
            if confidence >= 0.75:
                quality = EmailQuality.HIGH
            elif confidence >= 0.45:
                quality = EmailQuality.MEDIUM
            elif confidence >= 0.15:
                quality = EmailQuality.LOW
            else:
                quality = EmailQuality.SPAM
        else:
            # Use traditional thresholds for fallback validation
            if confidence >= 0.7:
                quality = EmailQuality.HIGH
            elif confidence >= 0.4:
                quality = EmailQuality.MEDIUM
            elif confidence >= 0.1:
                quality = EmailQuality.LOW
            else:
                quality = EmailQuality.SPAM
        
        return quality, confidence


class DNSValidator:
    """
    DNS-based email validation with MX record checking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # DNS settings
        self.dns_timeout = self.config.get("dns_timeout", 5.0)
        self.enable_mx_check = self.config.get("enable_mx_check", False)
        self.enable_caching = self.config.get("enable_caching", True)
        
        # DNS cache
        self._dns_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour
        
        self.logger.info(f"DNSValidator initialized (MX check: {self.enable_mx_check})")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.DNSValidator")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def validate_domain(self, domain: str, result: ValidationResult) -> ValidationResult:
        """
        Validate domain DNS records.
        
        Args:
            domain: Domain to validate
            result: Existing validation result to update
            
        Returns:
            Updated ValidationResult
        """
        if not self.enable_mx_check:
            return result
        
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"mx_{domain}"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result is not None:
                result.mx_records = cached_result
                result.validation_time_ms += (time.time() - start_time) * 1000
                return result
            
            # Perform MX lookup
            mx_records = self._lookup_mx_records(domain)
            
            if mx_records:
                result.mx_records = mx_records
                
                # Cache the result
                self._cache_result(cache_key, mx_records)
                
            else:
                result.status = ValidationStatus.NO_MX_RECORD
                result.is_valid = False
                result.reason = f"No MX records found for domain {domain}"
                
            result.validation_time_ms += (time.time() - start_time) * 1000
            
        except Exception as e:
            result.status = ValidationStatus.DNS_ERROR
            result.is_valid = False
            result.reason = f"DNS lookup error: {str(e)}"
            result.validation_time_ms += (time.time() - start_time) * 1000
            
            self.logger.debug(f"DNS validation error for {domain}: {e}")
        
        return result
    
    def _lookup_mx_records(self, domain: str) -> List[str]:
        """Lookup MX records for domain"""
        try:
            # Configure resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.dns_timeout
            resolver.lifetime = self.dns_timeout
            
            # Query MX records
            mx_records = []
            answers = resolver.resolve(domain, 'MX')
            
            for answer in answers:
                mx_records.append(str(answer.exchange).rstrip('.'))
            
            return sorted(mx_records)
            
        except dns.resolver.NXDOMAIN:
            return []
        except dns.resolver.NoAnswer:
            return []
        except Exception as e:
            self.logger.debug(f"MX lookup failed for {domain}: {e}")
            raise
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[str]]:
        """Get cached DNS result"""
        if not self.enable_caching:
            return None
        
        with self._cache_lock:
            if cache_key in self._dns_cache:
                result, timestamp = self._dns_cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return result
                else:
                    # Remove expired entry
                    del self._dns_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: List[str]):
        """Cache DNS result"""
        if not self.enable_caching:
            return
        
        with self._cache_lock:
            self._dns_cache[cache_key] = (result, time.time())


class BlacklistFilter:
    """
    Email blacklist filtering system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Initialize blacklist patterns
        self._initialize_blacklist_patterns()
        
        self.logger.info(f"BlacklistFilter initialized with {len(self.blacklist_patterns)} patterns")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.BlacklistFilter")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_blacklist_patterns(self):
        """Initialize blacklist patterns"""
        # Default blacklist patterns
        default_patterns = [
            # No-reply patterns
            (r'^no-?reply@', "noreply email"),
            (r'^donotreply@', "donotreply email"),
            (r'^bounce@', "bounce email"),
            
            # Placeholder/test patterns
            (r'^(test|testing|example|placeholder)@', "test/placeholder email"),
            (r'^(dummy|fake|temp|temporary)@', "dummy/temporary email"),
            (r'@(test\.|example\.|localhost)', "test/example domain"),
            
            # System/admin patterns
            (r'^(admin|administrator|root|system)@', "system/admin email"),
            (r'^(webmaster|postmaster|hostmaster)@', "webmaster email"),
            (r'^(daemon|mailer-daemon|mail-daemon)@', "daemon email"),
            
            # Generic patterns
            (r'^(info|contact)@.*\.(local|test|dev)', "local/test environment"),
            (r'^(support|help)@.*\.(local|test|dev)', "local/test environment"),
            
            # Suspicious patterns
            (r'^[a-z]{1,3}@', "too short local part"),
            (r'^[0-9]+@', "numeric local part"),
            (r'@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$', "IP address domain"),
            
            # Privacy-focused patterns (configurable)
            (r'^(privacy|anonymous|anon)@', "privacy email"),
        ]
        
        # Load custom patterns from config
        custom_patterns = self.config.get("blacklist_patterns", [])
        
        # Combine patterns
        all_patterns = default_patterns + [(pattern, "custom blacklist") for pattern in custom_patterns]
        
        # Compile regex patterns
        self.blacklist_patterns = []
        for pattern, reason in all_patterns:
            try:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                self.blacklist_patterns.append((compiled_pattern, reason))
            except re.error as e:
                self.logger.warning(f"Invalid blacklist pattern '{pattern}': {e}")
    
    def check_blacklist(self, email: str, result: ValidationResult) -> ValidationResult:
        """
        Check email against blacklist patterns.
        
        Args:
            email: Email to check
            result: Existing validation result to update
            
        Returns:
            Updated ValidationResult
        """
        email_lower = email.lower()
        
        for pattern, reason in self.blacklist_patterns:
            if pattern.search(email_lower):
                result.status = ValidationStatus.BLACKLISTED
                result.is_valid = False
                result.blacklist_match = pattern.pattern
                result.reason = f"Blacklisted: {reason}"
                result.quality = EmailQuality.SPAM
                break
        
        return result


class EmailDeduplicator:
    """
    Advanced email deduplication system with contact record merging.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Deduplication settings
        self.strict_mode = self.config.get("strict_deduplication", True)
        self.merge_similar_domains = self.config.get("merge_similar_domains", True)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.8)
        
        # Tracking data structures
        self._seen_emails = set()
        self._contact_records = {}
        self._email_to_record_id = {}
        self._domain_groups = defaultdict(list)
        
        self.logger.info("EmailDeduplicator initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailDeduplicator")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def check_duplicate(self, email: str, result: ValidationResult, 
                       contact_data: Optional[Dict[str, Any]] = None) -> Tuple[ValidationResult, bool]:
        """
        Check if email is duplicate and handle deduplication.
        
        Args:
            email: Email to check
            result: Validation result
            contact_data: Additional contact information
            
        Returns:
            Tuple of (updated_result, is_duplicate)
        """
        normalized_email = result.normalized_email or email.lower()
        
        # Check for exact duplicate
        if normalized_email in self._seen_emails:
            result.status = ValidationStatus.DUPLICATE
            result.is_valid = False
            result.reason = "Duplicate email address"
            return result, True
        
        # Add to seen emails
        self._seen_emails.add(normalized_email)
        
        # Create or update contact record
        self._process_contact_record(normalized_email, result, contact_data)
        
        return result, False
    
    def _process_contact_record(self, email: str, result: ValidationResult, 
                              contact_data: Optional[Dict[str, Any]] = None):
        """Process contact record for deduplication and merging"""
        domain = email.split('@')[1]
        
        # Generate contact record ID
        record_id = self._generate_record_id(email, contact_data)
        
        # Check if we should merge with existing record
        existing_record_id = self._find_mergeable_record(email, domain, contact_data)
        
        if existing_record_id and existing_record_id != record_id:
            # Merge with existing record
            self._merge_contact_records(existing_record_id, record_id, email, result, contact_data)
        else:
            # Create new record
            self._create_contact_record(record_id, email, result, contact_data)
    
    def _generate_record_id(self, email: str, contact_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate unique record ID for contact"""
        # Use email as base
        base = email
        
        # Add additional identifiers if available
        if contact_data:
            name = contact_data.get('name', '')
            company = contact_data.get('company', '')
            if name:
                base += f"_{name}"
            if company:
                base += f"_{company}"
        
        # Generate hash
        return hashlib.md5(base.encode()).hexdigest()[:12]
    
    def _find_mergeable_record(self, email: str, domain: str, 
                             contact_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Find existing record that should be merged with this contact"""
        if not self.merge_similar_domains:
            return None
        
        # Look for records in same domain
        domain_records = self._domain_groups.get(domain, [])
        
        for record_id in domain_records:
            if record_id in self._contact_records:
                record = self._contact_records[record_id]
                
                # Check if records should be merged
                if self._should_merge_records(email, contact_data, record):
                    return record_id
        
        return None
    
    def _should_merge_records(self, email: str, contact_data: Optional[Dict[str, Any]], 
                            existing_record: ContactRecord) -> bool:
        """Determine if records should be merged"""
        if not contact_data:
            return False
        
        # Check name similarity
        new_name = contact_data.get('name', '').lower()
        if new_name:
            for existing_name in existing_record.names:
                if self._calculate_similarity(new_name, existing_name.lower()) > self.similarity_threshold:
                    return True
        
        # Check company similarity
        new_company = contact_data.get('company', '').lower()
        if new_company:
            for existing_company in existing_record.companies:
                if self._calculate_similarity(new_company, existing_company.lower()) > self.similarity_threshold:
                    return True
        
        return False
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity (simple Jaccard similarity)"""
        if not str1 or not str2:
            return 0.0
        
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _merge_contact_records(self, existing_id: str, new_id: str, email: str, 
                             result: ValidationResult, contact_data: Optional[Dict[str, Any]]):
        """Merge new contact data into existing record"""
        existing_record = self._contact_records[existing_id]
        
        # Create temporary new record
        new_record = self._create_temp_contact_record(email, result, contact_data)
        
        # Merge into existing
        existing_record.merge_with(new_record)
        
        # Update email mapping
        self._email_to_record_id[email] = existing_id
    
    def _create_contact_record(self, record_id: str, email: str, result: ValidationResult, 
                             contact_data: Optional[Dict[str, Any]]):
        """Create new contact record"""
        record = self._create_temp_contact_record(email, result, contact_data)
        
        # Store record
        self._contact_records[record_id] = record
        self._email_to_record_id[email] = record_id
        
        # Add to domain group
        domain = email.split('@')[1]
        self._domain_groups[domain].append(record_id)
    
    def _create_temp_contact_record(self, email: str, result: ValidationResult, 
                                  contact_data: Optional[Dict[str, Any]]) -> ContactRecord:
        """Create temporary contact record for merging"""
        record = ContactRecord(
            primary_email=email,
            all_emails=[email],
            confidence_scores=[result.confidence_score],
            total_occurrences=1,
            best_confidence=result.confidence_score
        )
        
        if contact_data:
            # Extract contact information
            name = contact_data.get('name', '')
            if name:
                record.names.append(name)
            
            title = contact_data.get('title', '')
            if title:
                record.titles.append(title)
            
            company = contact_data.get('company', '')
            if company:
                record.companies.append(company)
            
            phone = contact_data.get('phone', '')
            if phone:
                record.phone_numbers.append(phone)
            
            source_url = contact_data.get('source_url', '')
            if source_url:
                record.source_urls.append(source_url)
            
            method = contact_data.get('discovery_method', '')
            if method:
                record.discovery_methods.append(method)
        
        return record
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return {
            'total_emails_processed': len(self._seen_emails),
            'unique_contact_records': len(self._contact_records),
            'domain_groups': len(self._domain_groups),
            'duplicate_rate': 1.0 - (len(self._contact_records) / max(1, len(self._seen_emails)))
        }
    
    def get_final_contacts(self) -> List[ContactRecord]:
        """Get final deduplicated contact records"""
        return list(self._contact_records.values())


class ValidationReporter:
    """
    Validation and deduplication reporting system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'valid_emails': 0,
            'invalid_syntax': 0,
            'invalid_domain': 0,
            'blacklisted': 0,
            'duplicates': 0,
            'no_mx_record': 0,
            'dns_errors': 0,
            'unknown_errors': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'spam_quality': 0,
            'total_validation_time_ms': 0.0
        }
        
        # Detailed rejection reasons
        self.rejection_reasons = Counter()
        self.blacklist_matches = Counter()
        
        self.logger.info("ValidationReporter initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.ValidationReporter")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def record_validation(self, result: ValidationResult):
        """Record validation result for reporting"""
        self.stats['total_processed'] += 1
        self.stats['total_validation_time_ms'] += result.validation_time_ms
        
        # Count by status
        status_mapping = {
            ValidationStatus.VALID: 'valid_emails',
            ValidationStatus.INVALID_SYNTAX: 'invalid_syntax',
            ValidationStatus.INVALID_DOMAIN: 'invalid_domain',
            ValidationStatus.BLACKLISTED: 'blacklisted',
            ValidationStatus.DUPLICATE: 'duplicates',
            ValidationStatus.NO_MX_RECORD: 'no_mx_record',
            ValidationStatus.DNS_ERROR: 'dns_errors',
            ValidationStatus.UNKNOWN_ERROR: 'unknown_errors'
        }
        
        stat_key = status_mapping.get(result.status, 'unknown_errors')
        self.stats[stat_key] += 1
        
        # Count by quality
        quality_mapping = {
            EmailQuality.HIGH: 'high_quality',
            EmailQuality.MEDIUM: 'medium_quality',
            EmailQuality.LOW: 'low_quality',
            EmailQuality.SPAM: 'spam_quality'
        }
        
        quality_key = quality_mapping.get(result.quality, 'spam_quality')
        self.stats[quality_key] += 1
        
        # Record rejection reasons
        if not result.is_valid:
            self.rejection_reasons[result.reason] += 1
            
            if result.blacklist_match:
                self.blacklist_matches[result.blacklist_match] += 1
    
    def get_acceptance_rate(self) -> float:
        """Calculate acceptance rate"""
        if self.stats['total_processed'] == 0:
            return 0.0
        
        return self.stats['valid_emails'] / self.stats['total_processed']
    
    def get_quality_distribution(self) -> Dict[str, float]:
        """Get quality distribution percentages"""
        total = self.stats['total_processed']
        if total == 0:
            return {'high': 0.0, 'medium': 0.0, 'low': 0.0, 'spam': 0.0}
        
        return {
            'high': self.stats['high_quality'] / total,
            'medium': self.stats['medium_quality'] / total,
            'low': self.stats['low_quality'] / total,
            'spam': self.stats['spam_quality'] / total
        }
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics"""
        total = self.stats['total_processed']
        if total == 0:
            return {'avg_validation_time_ms': 0.0, 'emails_per_second': 0.0}
        
        avg_time = self.stats['total_validation_time_ms'] / total
        emails_per_second = 1000.0 / avg_time if avg_time > 0 else 0.0
        
        return {
            'avg_validation_time_ms': avg_time,
            'emails_per_second': emails_per_second
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        total = self.stats['total_processed']
        
        report = {
            'summary': {
                'total_processed': total,
                'acceptance_rate': self.get_acceptance_rate(),
                'rejection_rate': 1.0 - self.get_acceptance_rate(),
                'duplicate_rate': self.stats['duplicates'] / max(1, total)
            },
            'validation_results': {
                'valid': self.stats['valid_emails'],
                'invalid_syntax': self.stats['invalid_syntax'],
                'invalid_domain': self.stats['invalid_domain'],
                'blacklisted': self.stats['blacklisted'],
                'duplicates': self.stats['duplicates'],
                'no_mx_record': self.stats['no_mx_record'],
                'dns_errors': self.stats['dns_errors'],
                'unknown_errors': self.stats['unknown_errors']
            },
            'quality_distribution': self.get_quality_distribution(),
            'performance': self.get_performance_metrics(),
            'top_rejection_reasons': dict(self.rejection_reasons.most_common(10)),
            'top_blacklist_matches': dict(self.blacklist_matches.most_common(10))
        }
        
        return report
    
    def log_summary(self):
        """Log validation summary"""
        acceptance_rate = self.get_acceptance_rate()
        quality_dist = self.get_quality_distribution()
        performance = self.get_performance_metrics()
        
        self.logger.info(
            f"Validation Summary: {self.stats['total_processed']} emails processed, "
            f"{acceptance_rate:.1%} acceptance rate, "
            f"{quality_dist['high']:.1%} high quality, "
            f"{performance['avg_validation_time_ms']:.1f}ms avg time"
        )


class ValidatorDedupeAgent(Agent):
    """
    Agency Swarm agent for email validation and deduplication.
    
    This agent provides comprehensive email validation, blacklist filtering,
    deduplication, and quality assessment for contact datasets.
    """
    
    def __init__(self):
        super().__init__(
            name="ValidatorDedupe",
            description="Validates email addresses, removes duplicates and blacklisted entries, and provides quality scoring for contact datasets",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.1,
            max_prompt_tokens=25000,
        )
        
        # Initialize validation components
        self.syntax_validator = EmailSyntaxValidator()
        self.dns_validator = DNSValidator()
        self.blacklist_filter = BlacklistFilter()
        self.deduplicator = EmailDeduplicator()
        self.reporter = ValidationReporter()
        
        self.logger = logging.getLogger(f"{__name__}.ValidatorDedupeAgent")
        self.logger.info("ValidatorDedupeAgent initialized")
    
    def validate_email_batch(self, emails: List[str], 
                           contact_data: Optional[List[Dict[str, Any]]] = None,
                           max_workers: int = 10) -> List[ValidationResult]:
        """
        Validate a batch of emails with parallel processing.
        
        Args:
            emails: List of email addresses to validate
            contact_data: Optional contact data for each email
            max_workers: Maximum number of parallel workers
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit validation tasks
            future_to_email = {}
            for i, email in enumerate(emails):
                contact_info = contact_data[i] if contact_data and i < len(contact_data) else None
                future = executor.submit(self._validate_single_email, email, contact_info)
                future_to_email[future] = (email, contact_info)
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_email):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    email, _ = future_to_email[future]
                    self.logger.error(f"Validation error for {email}: {e}")
                    
                    # Create error result
                    error_result = ValidationResult(
                        email=email,
                        status=ValidationStatus.UNKNOWN_ERROR,
                        reason=f"Processing error: {str(e)}"
                    )
                    results.append(error_result)
        
        # Sort results to maintain original order
        email_to_result = {r.email: r for r in results}
        ordered_results = [email_to_result.get(email, ValidationResult(email=email, status=ValidationStatus.UNKNOWN_ERROR)) for email in emails]
        
        return ordered_results
    
    def _validate_single_email(self, email: str, contact_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate a single email address, with optional Mailtester API integration"""
        
        # Check if contact_data contains Mailtester validation results
        mailtester_data = None
        if contact_data and any(key.startswith('mailtester_') for key in contact_data.keys()):
            mailtester_data = contact_data
        
        # Step 1: Syntax validation
        result = self.syntax_validator.validate_syntax(email)
        
        # If we have Mailtester data, enhance the result with API insights
        if result.is_valid and mailtester_data:
            result = self._enhance_with_mailtester_data(result, mailtester_data)
        
        if result.is_valid:
            # Step 2: DNS validation (if enabled and no API data available)
            if not mailtester_data:  # Skip DNS check if we have API data
                result = self.dns_validator.validate_domain(result.domain, result)
            
            if result.is_valid:
                # Step 3: Blacklist filtering
                result = self.blacklist_filter.check_blacklist(email, result)
                
                if result.is_valid:
                    # Step 4: Deduplication check
                    result, is_duplicate = self.deduplicator.check_duplicate(
                        email, result, contact_data
                    )
        
        # Record for reporting
        self.reporter.record_validation(result)
        
        return result
    
    def _enhance_with_mailtester_data(self, result: ValidationResult, mailtester_data: Dict[str, Any]) -> ValidationResult:
        """Enhance ValidationResult with Mailtester API data"""
        
        # Re-assess quality using Mailtester data
        quality, confidence = self.syntax_validator._assess_email_quality(
            result.email, result.domain, mailtester_data
        )
        
        # Update the result with enhanced information
        result.quality = quality
        result.confidence_score = confidence
        
        # Update validation status based on Mailtester results
        mailtester_status = mailtester_data.get('mailtester_status', 'unknown')
        if mailtester_status in ['valid', 'risky', 'catch_all']:
            result.is_valid = True
            result.status = ValidationStatus.VALID
        elif mailtester_status == 'invalid':
            result.is_valid = False
            result.status = ValidationStatus.INVALID_DOMAIN
        
        # Enhance reason with API insights
        api_reasons = []
        if mailtester_data.get('is_disposable', False):
            api_reasons.append("disposable email provider")
        if mailtester_data.get('is_catch_all', False):
            api_reasons.append("catch-all domain")
        if not mailtester_data.get('smtp_verified', True):
            api_reasons.append("SMTP unverified")
        if mailtester_data.get('is_role_account', False):
            api_reasons.append("role account")
        
        if api_reasons:
            enhanced_reason = f"{result.reason} (API: {', '.join(api_reasons)})"
        else:
            enhanced_reason = f"{result.reason} (API verified)"
        
        result.reason = enhanced_reason
        
        # Update domain classification based on API data
        if mailtester_data.get('is_role_account', False) and not mailtester_data.get('is_disposable', False):
            result.is_business_domain = True
            result.is_personal_domain = False
        elif mailtester_data.get('is_disposable', False):
            result.is_business_domain = False
            result.is_personal_domain = True
        
        return result
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report"""
        validation_report = self.reporter.generate_report()
        deduplication_stats = self.deduplicator.get_deduplication_stats()
        
        return {
            'validation': validation_report,
            'deduplication': deduplication_stats,
            'final_contacts': len(self.deduplicator.get_final_contacts())
        }
    
    def get_final_contacts(self) -> List[ContactRecord]:
        """Get final deduplicated contact records"""
        return self.deduplicator.get_final_contacts()
    
    def log_summary(self):
        """Log validation and deduplication summary"""
        self.reporter.log_summary()
        
        dedup_stats = self.deduplicator.get_deduplication_stats()
        self.logger.info(
            f"Deduplication Summary: {dedup_stats['total_emails_processed']} emails, "
            f"{dedup_stats['unique_contact_records']} unique contacts, "
            f"{dedup_stats['duplicate_rate']:.1%} duplicate rate"
        )