"""
Mailtester Ninja API Client

A robust client for integrating with the Mailtester Ninja email validation API.
Provides comprehensive email validation with proper error handling and rate limiting.
"""

import os
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class ValidationLevel(Enum):
    """Validation levels available in Mailtester Ninja API"""
    BASIC = "basic"
    FULL = "full"


class EmailStatus(Enum):
    """Email validation status results"""
    VALID = "valid"
    INVALID = "invalid" 
    RISKY = "risky"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"


@dataclass
class MailtesterResult:
    """
    Mailtester Ninja API validation result
    """
    email: str
    is_valid_format: bool = False
    domain_exists: bool = False
    has_mx_records: bool = False
    is_disposable: bool = False
    is_role_account: bool = False
    smtp_check: Optional[Dict[str, Any]] = None
    score: float = 0.0
    suggestion: Optional[str] = None
    status: EmailStatus = EmailStatus.UNKNOWN
    api_response_time_ms: float = 0.0
    validation_level: ValidationLevel = ValidationLevel.BASIC
    
    # Additional metadata
    provider_info: Optional[str] = None
    blacklisted: bool = False
    confidence_level: str = "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['status'] = self.status.value
        result['validation_level'] = self.validation_level.value
        return result
    
    def is_deliverable(self) -> bool:
        """Check if email is considered deliverable"""
        return (
            self.is_valid_format and 
            self.domain_exists and 
            self.has_mx_records and 
            not self.is_disposable and
            self.score >= 0.5
        )
    
    def get_quality_score(self) -> float:
        """Get normalized quality score (0-1)"""
        base_score = self.score
        
        # Apply penalties and bonuses
        if self.is_disposable:
            base_score -= 0.3
        if self.is_role_account:
            base_score += 0.1  # Role accounts can be valuable for business contacts
        if self.smtp_check and self.smtp_check.get('mailbox_exists'):
            base_score += 0.2
        if self.smtp_check and self.smtp_check.get('is_catch_all'):
            base_score -= 0.1  # Catch-all domains are less reliable
            
        return max(0.0, min(1.0, base_score))


class MailtesterNinjaClient:
    """
    Client for Mailtester Ninja email validation API with rate limiting,
    caching, and comprehensive error handling.
    """
    
    BASE_URL = "https://api.mailtester.ninja/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        rate_limit_delay: float = 0.1,
        max_retries: int = 3,
        enable_caching: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize Mailtester Ninja API client.
        
        Args:
            api_key: API key (if not provided, will read from MAILTESTER_NINJA_API_KEY env var)
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests to respect rate limits
            max_retries: Maximum number of retry attempts
            enable_caching: Enable response caching
            cache_ttl: Cache TTL in seconds
        """
        self.api_key = api_key or os.getenv('MAILTESTER_NINJA_API_KEY')
        if not self.api_key or self.api_key == 'YOUR_MAILTESTER_NINJA_API_KEY_HERE':
            raise ValueError("Mailtester Ninja API key not found. Please set MAILTESTER_NINJA_API_KEY environment variable.")
        
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        
        # Initialize session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'YTScrape-EmailValidator/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self._last_request_time = 0.0
        self._rate_lock = threading.Lock()
        
        # Caching
        self._cache = {}
        self._cache_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'api_errors': 0,
            'rate_limited': 0,
            'total_validation_time_ms': 0.0
        }
        
        self.logger = self._setup_logging()
        self.logger.info(f"MailtesterNinjaClient initialized (caching: {enable_caching})")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.MailtesterNinjaClient")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _apply_rate_limit(self):
        """Apply rate limiting to requests"""
        with self._rate_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                time.sleep(sleep_time)
                self.stats['rate_limited'] += 1
            
            self._last_request_time = time.time()
    
    def _get_cached_result(self, cache_key: str) -> Optional[MailtesterResult]:
        """Get cached validation result"""
        if not self.enable_caching:
            return None
        
        with self._cache_lock:
            if cache_key in self._cache:
                result, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    self.stats['cache_hits'] += 1
                    return result
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: MailtesterResult):
        """Cache validation result"""
        if not self.enable_caching:
            return
        
        with self._cache_lock:
            self._cache[cache_key] = (result, time.time())
    
    def _generate_cache_key(self, email: str, validation_level: ValidationLevel) -> str:
        """Generate cache key for email validation"""
        return f"{email.lower()}:{validation_level.value}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout))
    )
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            self.stats['requests_made'] += 1
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                raise requests.exceptions.RequestException("Rate limited")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            self.stats['api_errors'] += 1
            self.logger.error(f"API request failed: {e}")
            raise
    
    def validate_email(
        self, 
        email: str, 
        validation_level: ValidationLevel = ValidationLevel.BASIC,
        smtp_timeout: int = 10
    ) -> MailtesterResult:
        """
        Validate a single email address.
        
        Args:
            email: Email address to validate
            validation_level: Level of validation (basic or full)
            smtp_timeout: SMTP connection timeout for full validation
            
        Returns:
            MailtesterResult with validation details
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(email, validation_level)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Prepare request parameters
            params = {
                'email': email,
                'api_key': self.api_key
            }
            
            if validation_level == ValidationLevel.FULL:
                params['timeout'] = smtp_timeout
                endpoint = 'validate/full'
            else:
                endpoint = 'validate/basic'
            
            # Make API request
            response = self._make_request('GET', endpoint, params=params)
            api_data = response.json()
            
            # Parse response into MailtesterResult
            result = self._parse_api_response(email, api_data, validation_level)
            result.api_response_time_ms = (time.time() - start_time) * 1000
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.stats['total_validation_time_ms'] += result.api_response_time_ms
            
            return result
            
        except Exception as e:
            self.logger.error(f"Email validation failed for {email}: {e}")
            
            # Return error result
            error_result = MailtesterResult(
                email=email,
                status=EmailStatus.UNKNOWN,
                validation_level=validation_level,
                api_response_time_ms=(time.time() - start_time) * 1000
            )
            
            return error_result
    
    def validate_batch(
        self, 
        emails: List[str], 
        validation_level: ValidationLevel = ValidationLevel.BASIC,
        batch_size: int = 100
    ) -> List[MailtesterResult]:
        """
        Validate multiple email addresses in batches.
        
        Args:
            emails: List of email addresses to validate
            validation_level: Level of validation (basic or full)
            batch_size: Number of emails per batch request
            
        Returns:
            List of MailtesterResult objects
        """
        results = []
        
        # Process emails in batches
        for i in range(0, len(emails), batch_size):
            batch_emails = emails[i:i + batch_size]
            batch_results = self._validate_email_batch(batch_emails, validation_level)
            results.extend(batch_results)
        
        return results
    
    def _validate_email_batch(
        self, 
        emails: List[str], 
        validation_level: ValidationLevel
    ) -> List[MailtesterResult]:
        """Validate a single batch of emails"""
        start_time = time.time()
        
        try:
            # Prepare request body
            request_data = {
                'api_key': self.api_key,
                'emails': emails,
                'validation_level': validation_level.value
            }
            
            # Make batch API request
            response = self._make_request(
                'POST', 
                'validate/batch', 
                json=request_data
            )
            api_data = response.json()
            
            # Parse batch response
            results = []
            batch_time_ms = (time.time() - start_time) * 1000
            
            for email_result in api_data.get('results', []):
                result = self._parse_api_response(
                    email_result.get('email', ''),
                    email_result,
                    validation_level
                )
                result.api_response_time_ms = batch_time_ms / len(emails)  # Distribute time across emails
                results.append(result)
            
            self.stats['total_validation_time_ms'] += batch_time_ms
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch validation failed: {e}")
            
            # Return error results for all emails
            error_time_ms = (time.time() - start_time) * 1000
            return [
                MailtesterResult(
                    email=email,
                    status=EmailStatus.UNKNOWN,
                    validation_level=validation_level,
                    api_response_time_ms=error_time_ms / len(emails)
                )
                for email in emails
            ]
    
    def _parse_api_response(
        self, 
        email: str, 
        api_data: Dict[str, Any], 
        validation_level: ValidationLevel
    ) -> MailtesterResult:
        """Parse Mailtester Ninja API response into MailtesterResult"""
        
        # Determine status based on validation results
        status = EmailStatus.UNKNOWN
        if api_data.get('is_valid_format') and api_data.get('domain_exists'):
            if api_data.get('has_mx_records'):
                smtp_data = api_data.get('smtp_check', {})
                if smtp_data.get('is_catch_all'):
                    status = EmailStatus.CATCH_ALL
                elif smtp_data.get('mailbox_exists'):
                    status = EmailStatus.VALID
                else:
                    status = EmailStatus.RISKY
            else:
                status = EmailStatus.INVALID
        else:
            status = EmailStatus.INVALID
        
        # Determine confidence level based on score
        score = api_data.get('score', 0.0)
        if score >= 0.8:
            confidence_level = "high"
        elif score >= 0.5:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        return MailtesterResult(
            email=email,
            is_valid_format=api_data.get('is_valid_format', False),
            domain_exists=api_data.get('domain_exists', False),
            has_mx_records=api_data.get('has_mx_records', False),
            is_disposable=api_data.get('is_disposable', False),
            is_role_account=api_data.get('is_role_account', False),
            smtp_check=api_data.get('smtp_check'),
            score=score,
            suggestion=api_data.get('suggestion'),
            status=status,
            validation_level=validation_level,
            confidence_level=confidence_level
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        total_requests = self.stats['requests_made']
        avg_response_time = (
            self.stats['total_validation_time_ms'] / max(1, total_requests)
        )
        
        return {
            'total_requests': total_requests,
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': self.stats['cache_hits'] / max(1, total_requests + self.stats['cache_hits']),
            'api_errors': self.stats['api_errors'],
            'error_rate': self.stats['api_errors'] / max(1, total_requests),
            'rate_limited_requests': self.stats['rate_limited'],
            'average_response_time_ms': avg_response_time
        }
    
    def clear_cache(self):
        """Clear the validation cache"""
        with self._cache_lock:
            self._cache.clear()
        self.logger.info("Validation cache cleared")
    
    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
        self.logger.info("MailtesterNinjaClient closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Factory function for easy client creation
def create_mailtester_client(
    api_key: Optional[str] = None,
    enable_caching: bool = True,
    rate_limit_delay: float = 0.1
) -> MailtesterNinjaClient:
    """
    Factory function to create a configured Mailtester Ninja client.
    
    Args:
        api_key: API key (optional, will read from environment if not provided)
        enable_caching: Enable response caching
        rate_limit_delay: Delay between requests
        
    Returns:
        Configured MailtesterNinjaClient instance
    """
    return MailtesterNinjaClient(
        api_key=api_key,
        enable_caching=enable_caching,
        rate_limit_delay=rate_limit_delay
    )