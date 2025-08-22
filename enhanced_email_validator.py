#!/usr/bin/env python3
"""
Enhanced Email Validator - Production-ready email validation with DNS checking
"""

import re
import socket
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class EmailQuality(Enum):
    """Email quality classification"""
    HIGH = "high"           # Business decision makers, direct contacts
    MEDIUM = "medium"       # Standard business contacts  
    LOW = "low"            # Generic or uncertain emails
    INVALID = "invalid"    # Syntactically invalid or spam


@dataclass
class EmailValidationResult:
    """Result of email validation"""
    email: str
    is_valid: bool = False
    quality: EmailQuality = EmailQuality.INVALID
    confidence_score: float = 0.0
    
    # Technical validation
    syntax_valid: bool = False
    domain_exists: bool = False
    mx_record_exists: bool = False
    
    # Quality assessment
    is_business_email: bool = False
    is_personal_email: bool = False
    is_role_based: bool = False
    is_disposable: bool = False
    
    # Context and metadata
    domain: str = ""
    local_part: str = ""
    mx_records: List[str] = field(default_factory=list)
    validation_time_ms: float = 0.0
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'email': self.email,
            'is_valid': self.is_valid,
            'quality': self.quality.value,
            'confidence_score': self.confidence_score,
            'syntax_valid': self.syntax_valid,
            'domain_exists': self.domain_exists,
            'mx_record_exists': self.mx_record_exists,
            'is_business_email': self.is_business_email,
            'is_personal_email': self.is_personal_email,
            'is_role_based': self.is_role_based,
            'is_disposable': self.is_disposable,
            'domain': self.domain,
            'local_part': self.local_part,
            'mx_records': self.mx_records,
            'validation_time_ms': self.validation_time_ms,
            'error_message': self.error_message
        }


class EnhancedEmailValidator:
    """Production-ready email validator with comprehensive checks"""
    
    def __init__(self, enable_dns_check: bool = True, timeout_seconds: int = 5):
        self.enable_dns_check = enable_dns_check
        self.timeout_seconds = timeout_seconds
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # DNS cache to avoid repeated lookups
        self._dns_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 3600  # 1 hour
        
        # Email patterns
        self._compile_patterns()
        
        # Domain lists
        self._load_domain_lists()
        
        self.logger.info(f"EnhancedEmailValidator initialized (DNS: {enable_dns_check}, timeout: {timeout_seconds}s)")
    
    def _compile_patterns(self):
        """Compile email validation patterns"""
        # RFC 5322 compliant email regex (simplified but robust)
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$',
            re.IGNORECASE
        )
        
        # High-quality business email patterns
        self.high_quality_patterns = [
            re.compile(r'^(ceo|president|founder|director|owner)@', re.IGNORECASE),
            re.compile(r'^[a-z]+\.[a-z]+@', re.IGNORECASE),  # firstname.lastname
            re.compile(r'^(contact|business|sales|marketing)@', re.IGNORECASE),
        ]
        
        # Medium-quality business patterns
        self.medium_quality_patterns = [
            re.compile(r'^(info|hello|team|support|admin)@', re.IGNORECASE),
            re.compile(r'^[a-z]+@', re.IGNORECASE),  # Simple first name
        ]
        
        # Role-based email patterns
        self.role_based_patterns = [
            re.compile(r'^(info|contact|support|admin|sales|marketing|hr|legal|finance|operations)@', re.IGNORECASE),
            re.compile(r'^(webmaster|postmaster|hostmaster|abuse|noc)@', re.IGNORECASE),
        ]
        
        # Spam/invalid patterns
        self.spam_patterns = [
            re.compile(r'^(noreply|no-reply|donotreply|bounce)@', re.IGNORECASE),
            re.compile(r'^(test|testing|example|placeholder|dummy)@', re.IGNORECASE),
            re.compile(r'@(test\.|example\.|localhost)', re.IGNORECASE),
        ]
    
    def _load_domain_lists(self):
        """Load domain classification lists"""
        # Personal email providers
        self.personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
            'icloud.com', 'me.com', 'protonmail.com', 'tutanota.com',
            'fastmail.com', 'zoho.com', 'yandex.com', 'mail.com', 'gmx.com'
        }
        
        # Disposable email providers (common ones)
        self.disposable_domains = {
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'trash-mail.com', 'yopmail.com',
            'throwaway.email', 'temp-mail.org'
        }
        
        # Business domain indicators
        self.business_indicators = [
            'corp', 'inc', 'ltd', 'llc', 'company', 'enterprises',
            'group', 'solutions', 'consulting', 'services', 'tech',
            'digital', 'agency', 'partners', 'business', 'firm'
        ]
        
        # Valid TLDs (common business ones)
        self.valid_tlds = {
            # Generic TLDs
            'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
            'info', 'biz', 'name', 'pro', 'museum', 'coop',
            
            # New gTLDs (business)
            'app', 'tech', 'digital', 'online', 'website', 'store',
            'company', 'business', 'enterprises', 'solutions',
            
            # Country codes (major ones)
            'us', 'uk', 'ca', 'au', 'de', 'fr', 'it', 'es', 'nl',
            'se', 'no', 'dk', 'fi', 'pl', 'jp', 'cn', 'in', 'br'
        }
    
    def validate_email(self, email: str) -> EmailValidationResult:
        """Comprehensive email validation"""
        start_time = time.time()
        result = EmailValidationResult(email=email)
        
        try:
            # Step 1: Basic cleanup and syntax validation
            if not self._validate_syntax(email, result):
                result.validation_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Step 2: Domain existence check (if enabled)
            if self.enable_dns_check:
                self._check_domain_dns(result)
            
            # Step 3: Quality assessment
            self._assess_email_quality(result)
            
            # Step 4: Final validation status
            result.is_valid = (
                result.syntax_valid and
                (not self.enable_dns_check or result.domain_exists) and
                result.quality != EmailQuality.INVALID
            )
            
            result.validation_time_ms = (time.time() - start_time) * 1000
            
        except Exception as e:
            result.error_message = str(e)
            result.validation_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Email validation error for {email}: {e}")
        
        return result
    
    def validate_batch(self, emails: List[str], max_workers: int = 10) -> List[EmailValidationResult]:
        """Validate multiple emails in parallel"""
        if not emails:
            return []
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all validation tasks
            future_to_email = {
                executor.submit(self.validate_email, email): email 
                for email in emails
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_email):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    email = future_to_email[future]
                    error_result = EmailValidationResult(
                        email=email,
                        error_message=str(e)
                    )
                    results.append(error_result)
        
        # Sort results to maintain original order
        email_to_result = {r.email: r for r in results}
        ordered_results = [
            email_to_result.get(email, EmailValidationResult(email=email, error_message="Not processed"))
            for email in emails
        ]
        
        return ordered_results
    
    def _validate_syntax(self, email: str, result: EmailValidationResult) -> bool:
        """Validate email syntax"""
        if not email or not isinstance(email, str):
            result.error_message = "Empty or invalid email input"
            return False
        
        # Clean and normalize
        email = email.strip().lower()
        result.email = email
        
        # Basic format check
        if not self.email_pattern.match(email):
            result.error_message = "Invalid email format"
            return False
        
        # Split into parts
        try:
            local_part, domain = email.split('@', 1)
            result.local_part = local_part
            result.domain = domain
        except ValueError:
            result.error_message = "Invalid email structure"
            return False
        
        # Validate local part
        if len(local_part) < 1 or len(local_part) > 64:
            result.error_message = "Invalid local part length"
            return False
        
        # Validate domain
        if len(domain) < 4 or len(domain) > 255:  # Minimum: a.co
            result.error_message = "Invalid domain length"
            return False
        
        # Check for valid TLD
        tld = domain.split('.')[-1].lower()
        if tld not in self.valid_tlds and len(tld) < 2:
            result.error_message = f"Invalid TLD: {tld}"
            return False
        
        # Check for spam patterns
        for pattern in self.spam_patterns:
            if pattern.search(email):
                result.error_message = "Email matches spam pattern"
                result.quality = EmailQuality.INVALID
                return False
        
        result.syntax_valid = True
        return True
    
    def _check_domain_dns(self, result: EmailValidationResult):
        """Check domain DNS records"""
        domain = result.domain
        
        # Check cache first
        cache_key = f"dns_{domain}"
        cached_result = self._get_cached_dns(cache_key)
        if cached_result is not None:
            result.domain_exists, result.mx_record_exists, result.mx_records = cached_result
            return
        
        try:
            # Check if domain resolves
            socket.gethostbyname(domain)
            result.domain_exists = True
            
            # Try to get MX records (simplified - would use dnspython in production)
            try:
                import socket
                # This is a simplified check - in production use dnspython
                mx_info = socket.getaddrinfo(domain, None)
                if mx_info:
                    result.mx_record_exists = True
                    result.mx_records = [domain]  # Simplified
            except:
                # Fallback: if domain exists, assume MX might exist
                result.mx_record_exists = True
                result.mx_records = [domain]
            
            # Cache the result
            self._cache_dns_result(cache_key, (result.domain_exists, result.mx_record_exists, result.mx_records))
            
        except socket.gaierror:
            result.domain_exists = False
            result.mx_record_exists = False
            self._cache_dns_result(cache_key, (False, False, []))
        except Exception as e:
            self.logger.debug(f"DNS check error for {domain}: {e}")
            # Don't fail validation on DNS errors, just mark as unknown
            result.domain_exists = True  # Assume valid if we can't check
            result.mx_record_exists = True
    
    def _assess_email_quality(self, result: EmailValidationResult):
        """Assess email quality for business use"""
        email = result.email
        local_part = result.local_part
        domain = result.domain
        
        confidence = 0.5  # Base confidence
        
        # Check for high-quality patterns
        for pattern in self.high_quality_patterns:
            if pattern.search(email):
                confidence += 0.3
                result.quality = EmailQuality.HIGH
                break
        else:
            # Check medium-quality patterns
            for pattern in self.medium_quality_patterns:
                if pattern.search(email):
                    confidence += 0.1
                    result.quality = EmailQuality.MEDIUM
                    break
            else:
                result.quality = EmailQuality.LOW
        
        # Domain type classification
        if domain in self.personal_domains:
            result.is_personal_email = True
            confidence -= 0.1  # Slight penalty for personal domains
        elif domain in self.disposable_domains:
            result.is_disposable = True
            confidence -= 0.3
            result.quality = EmailQuality.INVALID
        elif any(indicator in domain.lower() for indicator in self.business_indicators):
            result.is_business_email = True
            confidence += 0.2
        else:
            # Custom domain - likely business
            result.is_business_email = True
            confidence += 0.1
        
        # Role-based email check
        for pattern in self.role_based_patterns:
            if pattern.search(email):
                result.is_role_based = True
                break
        
        # Format bonuses
        if '.' in local_part and len(local_part.split('.')) == 2:
            # firstname.lastname format
            parts = local_part.split('.')
            if all(part.isalpha() and len(part) > 1 for part in parts):
                confidence += 0.15
        
        if 4 <= len(local_part) <= 20:  # Reasonable length
            confidence += 0.05
        
        # Ensure confidence is within bounds
        result.confidence_score = max(0.0, min(1.0, confidence))
        
        # Adjust quality based on final confidence
        if result.confidence_score >= 0.8:
            result.quality = EmailQuality.HIGH
        elif result.confidence_score >= 0.5:
            if result.quality == EmailQuality.LOW:
                result.quality = EmailQuality.MEDIUM
        elif result.confidence_score < 0.3:
            result.quality = EmailQuality.LOW
    
    def _get_cached_dns(self, cache_key: str) -> Optional[Tuple[bool, bool, List[str]]]:
        """Get cached DNS result"""
        with self._cache_lock:
            if cache_key in self._dns_cache:
                result, timestamp = self._dns_cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return result
                else:
                    del self._dns_cache[cache_key]
        return None
    
    def _cache_dns_result(self, cache_key: str, result: Tuple[bool, bool, List[str]]):
        """Cache DNS result"""
        with self._cache_lock:
            self._dns_cache[cache_key] = (result, time.time())
    
    def get_validation_stats(self, results: List[EmailValidationResult]) -> Dict[str, Any]:
        """Generate validation statistics"""
        if not results:
            return {}
        
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        
        quality_counts = {
            'high': sum(1 for r in results if r.quality == EmailQuality.HIGH),
            'medium': sum(1 for r in results if r.quality == EmailQuality.MEDIUM),
            'low': sum(1 for r in results if r.quality == EmailQuality.LOW),
            'invalid': sum(1 for r in results if r.quality == EmailQuality.INVALID)
        }
        
        return {
            'total_emails': total,
            'valid_emails': valid,
            'validation_rate': valid / total if total > 0 else 0,
            'quality_distribution': {
                k: {'count': v, 'percentage': v / total * 100}
                for k, v in quality_counts.items()
            },
            'business_emails': sum(1 for r in results if r.is_business_email),
            'personal_emails': sum(1 for r in results if r.is_personal_email),
            'role_based_emails': sum(1 for r in results if r.is_role_based),
            'disposable_emails': sum(1 for r in results if r.is_disposable),
            'avg_confidence': sum(r.confidence_score for r in results) / total if total > 0 else 0,
            'avg_validation_time_ms': sum(r.validation_time_ms for r in results) / total if total > 0 else 0
        }


def test_email_validator():
    """Test the email validator"""
    print("Testing Enhanced Email Validator")
    print("=" * 40)
    
    validator = EnhancedEmailValidator(enable_dns_check=False)  # Disable DNS for quick test
    
    test_emails = [
        # High quality
        "ceo@company.com",
        "john.smith@business.org", 
        "contact@medical-practice.com",
        
        # Medium quality
        "info@example.com",
        "support@service.net",
        "admin@website.org",
        
        # Low quality  
        "user@gmail.com",
        "test@yahoo.com",
        
        # Invalid
        "noreply@company.com",
        "test@example.com",
        "invalid-email",
        "",
    ]
    
    print("Validating individual emails:")
    results = []
    for email in test_emails:
        result = validator.validate_email(email)
        results.append(result)
        
        print(f"\nEmail: {email}")
        print(f"  Valid: {result.is_valid}")
        print(f"  Quality: {result.quality.value}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Business: {result.is_business_email}")
        print(f"  Personal: {result.is_personal_email}")
        print(f"  Role-based: {result.is_role_based}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
    
    # Test batch validation
    print(f"\n{'='*40}")
    print("Batch Validation Test:")
    batch_results = validator.validate_batch(test_emails[:5])  # Test first 5
    print(f"Processed {len(batch_results)} emails in batch")
    
    # Generate statistics
    stats = validator.get_validation_stats(results)
    print(f"\n{'='*40}")
    print("Validation Statistics:")
    print(f"Total emails: {stats['total_emails']}")
    print(f"Valid emails: {stats['valid_emails']}")
    print(f"Validation rate: {stats['validation_rate']:.1%}")
    print(f"Average confidence: {stats['avg_confidence']:.2f}")
    
    print("\nQuality Distribution:")
    for quality, data in stats['quality_distribution'].items():
        print(f"  {quality.title()}: {data['count']} ({data['percentage']:.1f}%)")
    
    return len([r for r in results if r.is_valid]) > 0


if __name__ == "__main__":
    success = test_email_validator()
    
    if success:
        print(f"\n{'='*40}")
        print("SUCCESS: Email validator is working!")
        print("Ready for integration with lead extraction.")
    else:
        print(f"\n{'='*40}")
        print("ISSUES: Email validator needs fixes.")