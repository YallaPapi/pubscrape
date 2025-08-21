"""
Error Handling Tool

Tool for handling HTTP errors, blocks, challenge pages, and implementing
robust retry logic for site crawling operations.
"""

import logging
import time
import re
import random
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from bs4 import BeautifulSoup

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field


class ErrorType(Enum):
    """Types of errors that can occur during crawling"""
    CONNECTION_ERROR = "connection_error"
    TIMEOUT_ERROR = "timeout_error"
    HTTP_CLIENT_ERROR = "http_client_error"  # 4xx
    HTTP_SERVER_ERROR = "http_server_error"  # 5xx
    BLOCKED_ERROR = "blocked_error"
    CHALLENGE_ERROR = "challenge_error"
    CAPTCHA_ERROR = "captcha_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    REDIRECT_ERROR = "redirect_error"
    CONTENT_ERROR = "content_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryStrategy(Enum):
    """Retry strategies for different error types"""
    NO_RETRY = "no_retry"
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CHALLENGE_RETRY = "challenge_retry"


@dataclass
class ErrorDetails:
    """Detailed information about an error"""
    error_type: ErrorType
    status_code: Optional[int] = None
    error_message: str = ""
    response_content: Optional[str] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_retries: int = 3
    base_delay: float = 1.0
    detected_patterns: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_retryable(self) -> bool:
        """Check if this error type is retryable"""
        return self.retry_strategy != RetryStrategy.NO_RETRY
    
    @property
    def is_temporary(self) -> bool:
        """Check if this is likely a temporary error"""
        return self.error_type in [
            ErrorType.TIMEOUT_ERROR,
            ErrorType.CONNECTION_ERROR,
            ErrorType.HTTP_SERVER_ERROR,
            ErrorType.RATE_LIMIT_ERROR
        ]


@dataclass
class RetryContext:
    """Context for retry operations"""
    url: str
    attempt_number: int = 0
    max_attempts: int = 3
    last_error: Optional[ErrorDetails] = None
    total_delay: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def can_retry(self) -> bool:
        """Check if more retries are possible"""
        return self.attempt_number < self.max_attempts
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since first attempt"""
        return time.time() - self.start_time


class ErrorDetector:
    """
    Detector for various types of web crawling errors and challenges.
    
    This class analyzes HTTP responses to identify different types of
    errors, blocks, and challenge pages that require special handling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Detection patterns
        self.challenge_patterns = self._initialize_challenge_patterns()
        self.block_patterns = self._initialize_block_patterns()
        self.captcha_patterns = self._initialize_captcha_patterns()
        
        # Configuration
        self.content_analysis_enabled = self.config.get("content_analysis_enabled", True)
        self.max_content_analysis_size = self.config.get("max_content_analysis_size", 50000)
        
        self.logger.info("ErrorDetector initialized with pattern-based detection")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the detector"""
        logger = logging.getLogger(f"{__name__}.ErrorDetector")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_challenge_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for challenge page detection"""
        return {
            "cloudflare": [
                r"cloudflare",
                r"cf-ray",
                r"checking your browser",
                r"browser check",
                r"ddos protection",
                r"ray id"
            ],
            "ddos_guard": [
                r"ddos-guard",
                r"ddosguard",
                r"protection by ddos-guard"
            ],
            "incapsula": [
                r"incapsula",
                r"incap_ses",
                r"powered by incapsula"
            ],
            "sucuri": [
                r"sucuri",
                r"sucuri website firewall",
                r"access denied.*sucuri"
            ],
            "akamai": [
                r"akamai",
                r"reference.*akamai",
                r"akamai ghost"
            ]
        }
    
    def _initialize_block_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for block detection"""
        return {
            "access_denied": [
                r"access denied",
                r"access forbidden",
                r"you don't have permission",
                r"unauthorized access",
                r"forbidden.*access"
            ],
            "ip_blocked": [
                r"ip.*blocked",
                r"your ip.*blocked",
                r"blocked.*ip address",
                r"ip address.*denied"
            ],
            "rate_limit": [
                r"rate limit",
                r"too many requests",
                r"request limit",
                r"quota exceeded",
                r"api limit"
            ],
            "bot_detection": [
                r"bot.*detected",
                r"automated.*traffic",
                r"suspicious.*activity",
                r"not a human",
                r"robot.*detected"
            ]
        }
    
    def _initialize_captcha_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for CAPTCHA detection"""
        return {
            "recaptcha": [
                r"recaptcha",
                r"google.*captcha",
                r"grecaptcha",
                r"recaptcha.*site.*key"
            ],
            "hcaptcha": [
                r"hcaptcha",
                r"h-captcha"
            ],
            "generic_captcha": [
                r"captcha",
                r"verify.*human",
                r"prove.*not.*robot",
                r"security.*check",
                r"human.*verification"
            ]
        }
    
    def detect_error_type(self, response: Optional[requests.Response] = None,
                         exception: Optional[Exception] = None,
                         url: str = "") -> ErrorDetails:
        """
        Detect the type of error from response or exception.
        
        Args:
            response: HTTP response object (if available)
            exception: Exception that occurred (if any)
            url: URL that was being requested
            
        Returns:
            ErrorDetails with classified error information
        """
        try:
            # Handle exceptions first
            if exception:
                return self._classify_exception(exception, url)
            
            # Handle HTTP responses
            if response:
                return self._classify_response(response, url)
            
            # No response or exception - unknown error
            return ErrorDetails(
                error_type=ErrorType.UNKNOWN_ERROR,
                error_message="No response or exception provided",
                retry_strategy=RetryStrategy.NO_RETRY
            )
            
        except Exception as e:
            self.logger.error(f"Error during error detection: {e}")
            return ErrorDetails(
                error_type=ErrorType.UNKNOWN_ERROR,
                error_message=f"Detection failed: {str(e)}",
                retry_strategy=RetryStrategy.NO_RETRY
            )
    
    def _classify_exception(self, exception: Exception, url: str) -> ErrorDetails:
        """Classify an exception into an error type"""
        exception_type = type(exception).__name__
        exception_str = str(exception).lower()
        
        # Connection errors
        if "connectionerror" in exception_type.lower() or "connection" in exception_str:
            return ErrorDetails(
                error_type=ErrorType.CONNECTION_ERROR,
                error_message=str(exception),
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=3,
                base_delay=2.0
            )
        
        # Timeout errors
        if "timeout" in exception_type.lower() or "timeout" in exception_str:
            return ErrorDetails(
                error_type=ErrorType.TIMEOUT_ERROR,
                error_message=str(exception),
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=2,
                base_delay=5.0
            )
        
        # SSL/TLS errors
        if any(term in exception_str for term in ["ssl", "tls", "certificate"]):
            return ErrorDetails(
                error_type=ErrorType.CONNECTION_ERROR,
                error_message=str(exception),
                retry_strategy=RetryStrategy.NO_RETRY  # SSL errors usually aren't retryable
            )
        
        # Generic exception
        return ErrorDetails(
            error_type=ErrorType.UNKNOWN_ERROR,
            error_message=str(exception),
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_retries=1,
            base_delay=3.0
        )
    
    def _classify_response(self, response: requests.Response, url: str) -> ErrorDetails:
        """Classify an HTTP response into an error type"""
        status_code = response.status_code
        content = ""
        
        # Get response content for analysis
        if self.content_analysis_enabled:
            try:
                content = response.text[:self.max_content_analysis_size].lower()
            except Exception as e:
                self.logger.warning(f"Could not read response content: {e}")
        
        headers = {k.lower(): v for k, v in response.headers.items()}
        
        # Handle different status codes
        if 200 <= status_code < 300:
            # Success but might contain challenge content
            return self._check_success_content(response, content, headers, url)
        
        elif 400 <= status_code < 500:
            return self._classify_client_error(status_code, content, headers, url)
        
        elif 500 <= status_code < 600:
            return self._classify_server_error(status_code, content, headers, url)
        
        else:
            return ErrorDetails(
                error_type=ErrorType.UNKNOWN_ERROR,
                status_code=status_code,
                error_message=f"Unexpected status code: {status_code}",
                response_content=content[:1000] if content else None,
                response_headers=headers,
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=1
            )
    
    def _check_success_content(self, response: requests.Response, content: str,
                              headers: Dict[str, str], url: str) -> ErrorDetails:
        """Check if successful response contains challenge content"""
        detected_patterns = []
        
        # Check for challenge patterns
        for challenge_type, patterns in self.challenge_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_patterns.append(f"challenge_{challenge_type}:{pattern}")
        
        # Check for CAPTCHA patterns
        for captcha_type, patterns in self.captcha_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_patterns.append(f"captcha_{captcha_type}:{pattern}")
        
        # Check for block patterns
        for block_type, patterns in self.block_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_patterns.append(f"block_{block_type}:{pattern}")
        
        # Determine error type
        if detected_patterns:
            if any("captcha" in pattern for pattern in detected_patterns):
                return ErrorDetails(
                    error_type=ErrorType.CAPTCHA_ERROR,
                    status_code=response.status_code,
                    error_message="CAPTCHA detected in response content",
                    response_content=content[:1000],
                    response_headers=headers,
                    detected_patterns=detected_patterns,
                    retry_strategy=RetryStrategy.CHALLENGE_RETRY,
                    max_retries=1,
                    base_delay=30.0
                )
            
            elif any("challenge" in pattern for pattern in detected_patterns):
                return ErrorDetails(
                    error_type=ErrorType.CHALLENGE_ERROR,
                    status_code=response.status_code,
                    error_message="Challenge page detected",
                    response_content=content[:1000],
                    response_headers=headers,
                    detected_patterns=detected_patterns,
                    retry_strategy=RetryStrategy.CHALLENGE_RETRY,
                    max_retries=1,
                    base_delay=15.0
                )
            
            elif any("block" in pattern for pattern in detected_patterns):
                return ErrorDetails(
                    error_type=ErrorType.BLOCKED_ERROR,
                    status_code=response.status_code,
                    error_message="Access blocked",
                    response_content=content[:1000],
                    response_headers=headers,
                    detected_patterns=detected_patterns,
                    retry_strategy=RetryStrategy.NO_RETRY
                )
        
        # If no issues detected but we're here, might be empty content
        if not content.strip() or len(content) < 100:
            return ErrorDetails(
                error_type=ErrorType.CONTENT_ERROR,
                status_code=response.status_code,
                error_message="Response content appears empty or invalid",
                response_content=content,
                response_headers=headers,
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=2,
                base_delay=2.0
            )
        
        # Success with valid content
        return ErrorDetails(
            error_type=ErrorType.UNKNOWN_ERROR,  # Not really an error
            status_code=response.status_code,
            error_message="Success",
            response_content=content[:1000],
            response_headers=headers,
            retry_strategy=RetryStrategy.NO_RETRY
        )
    
    def _classify_client_error(self, status_code: int, content: str,
                              headers: Dict[str, str], url: str) -> ErrorDetails:
        """Classify 4xx client errors"""
        if status_code == 403:
            return ErrorDetails(
                error_type=ErrorType.BLOCKED_ERROR,
                status_code=status_code,
                error_message="Access forbidden (403)",
                response_content=content[:1000],
                response_headers=headers,
                retry_strategy=RetryStrategy.NO_RETRY
            )
        
        elif status_code == 404:
            return ErrorDetails(
                error_type=ErrorType.HTTP_CLIENT_ERROR,
                status_code=status_code,
                error_message="Page not found (404)",
                response_content=content[:1000],
                response_headers=headers,
                retry_strategy=RetryStrategy.NO_RETRY
            )
        
        elif status_code == 429:
            # Extract retry-after header if available
            retry_after = headers.get("retry-after", "60")
            try:
                delay = float(retry_after)
            except ValueError:
                delay = 60.0
            
            return ErrorDetails(
                error_type=ErrorType.RATE_LIMIT_ERROR,
                status_code=status_code,
                error_message=f"Rate limited (429), retry after {delay}s",
                response_content=content[:1000],
                response_headers=headers,
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                max_retries=2,
                base_delay=delay
            )
        
        else:
            return ErrorDetails(
                error_type=ErrorType.HTTP_CLIENT_ERROR,
                status_code=status_code,
                error_message=f"Client error ({status_code})",
                response_content=content[:1000],
                response_headers=headers,
                retry_strategy=RetryStrategy.NO_RETRY
            )
    
    def _classify_server_error(self, status_code: int, content: str,
                              headers: Dict[str, str], url: str) -> ErrorDetails:
        """Classify 5xx server errors"""
        if status_code in [502, 503, 504]:
            # Temporary server errors
            return ErrorDetails(
                error_type=ErrorType.HTTP_SERVER_ERROR,
                status_code=status_code,
                error_message=f"Temporary server error ({status_code})",
                response_content=content[:1000],
                response_headers=headers,
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=3,
                base_delay=5.0
            )
        
        else:
            return ErrorDetails(
                error_type=ErrorType.HTTP_SERVER_ERROR,
                status_code=status_code,
                error_message=f"Server error ({status_code})",
                response_content=content[:1000],
                response_headers=headers,
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_retries=2,
                base_delay=3.0
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics"""
        return {
            "content_analysis_enabled": self.content_analysis_enabled,
            "max_content_analysis_size": self.max_content_analysis_size,
            "challenge_pattern_count": sum(len(patterns) for patterns in self.challenge_patterns.values()),
            "block_pattern_count": sum(len(patterns) for patterns in self.block_patterns.values()),
            "captcha_pattern_count": sum(len(patterns) for patterns in self.captcha_patterns.values())
        }


class RetryManager:
    """
    Manager for implementing retry logic with various strategies.
    
    This class handles the execution of retry strategies including
    exponential backoff, linear delays, and challenge-specific retries.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Configuration
        self.max_global_retries = self.config.get("max_global_retries", 5)
        self.max_retry_delay = self.config.get("max_retry_delay", 300.0)  # 5 minutes
        self.jitter_factor = self.config.get("jitter_factor", 0.1)
        
        self.logger.info("RetryManager initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the manager"""
        logger = logging.getLogger(f"{__name__}.RetryManager")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def calculate_delay(self, retry_context: RetryContext, 
                       error_details: ErrorDetails) -> float:
        """
        Calculate the delay before next retry attempt.
        
        Args:
            retry_context: Current retry context
            error_details: Details of the error that occurred
            
        Returns:
            Delay in seconds before next retry
        """
        strategy = error_details.retry_strategy
        attempt = retry_context.attempt_number
        base_delay = error_details.base_delay
        
        if strategy == RetryStrategy.NO_RETRY:
            return 0.0
        
        elif strategy == RetryStrategy.IMMEDIATE_RETRY:
            delay = 0.0
        
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * attempt
        
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (2 ** (attempt - 1))
        
        elif strategy == RetryStrategy.CHALLENGE_RETRY:
            # Special handling for challenges
            delay = base_delay + (attempt * 10.0)
        
        else:
            delay = base_delay
        
        # Add jitter to avoid thundering herd
        if delay > 0:
            jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * delay
            delay = max(0.1, delay + jitter)
        
        # Cap at maximum delay
        delay = min(delay, self.max_retry_delay)
        
        self.logger.debug(f"Calculated retry delay: {delay:.2f}s for {strategy.value}")
        
        return delay
    
    def should_retry(self, retry_context: RetryContext, 
                    error_details: ErrorDetails) -> Tuple[bool, str]:
        """
        Determine if a retry should be attempted.
        
        Args:
            retry_context: Current retry context
            error_details: Details of the error that occurred
            
        Returns:
            Tuple of (should_retry, reason)
        """
        # Check if retries are enabled for this error type
        if not error_details.is_retryable:
            return False, f"Error type {error_details.error_type.value} is not retryable"
        
        # Check attempt limits
        if not retry_context.can_retry:
            return False, f"Max attempts reached ({retry_context.max_attempts})"
        
        if retry_context.attempt_number >= self.max_global_retries:
            return False, f"Global retry limit reached ({self.max_global_retries})"
        
        if retry_context.attempt_number >= error_details.max_retries:
            return False, f"Error-specific retry limit reached ({error_details.max_retries})"
        
        # Check elapsed time
        elapsed = retry_context.elapsed_time
        if elapsed > 3600:  # 1 hour total timeout
            return False, f"Total retry timeout exceeded ({elapsed:.0f}s)"
        
        # Special handling for certain error types
        if error_details.error_type == ErrorType.BLOCKED_ERROR:
            return False, "Access blocked - retry unlikely to succeed"
        
        if error_details.error_type == ErrorType.HTTP_CLIENT_ERROR:
            # Most 4xx errors shouldn't be retried
            if error_details.status_code in [400, 401, 403, 404, 410]:
                return False, f"HTTP {error_details.status_code} - client error not retryable"
        
        return True, "Retry conditions met"
    
    def execute_retry_delay(self, delay: float) -> float:
        """
        Execute the retry delay.
        
        Args:
            delay: Delay in seconds
            
        Returns:
            Actual delay time applied
        """
        if delay <= 0:
            return 0.0
        
        self.logger.info(f"Applying retry delay: {delay:.2f}s")
        start_time = time.time()
        time.sleep(delay)
        actual_delay = time.time() - start_time
        
        return actual_delay
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retry manager statistics"""
        return {
            "max_global_retries": self.max_global_retries,
            "max_retry_delay": self.max_retry_delay,
            "jitter_factor": self.jitter_factor
        }


class ErrorHandlingTool(BaseTool):
    """
    Tool for comprehensive error handling and retry logic.
    
    This tool integrates error detection and retry management to provide
    robust error handling for web crawling operations.
    """
    
    operation: str = Field(
        ...,
        description="Operation to perform: 'detect_error', 'plan_retry', 'execute_retry'"
    )
    
    url: Optional[str] = Field(
        None,
        description="URL being processed (for context)"
    )
    
    status_code: Optional[int] = Field(
        None,
        description="HTTP status code received"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message or exception text"
    )
    
    response_content: Optional[str] = Field(
        None,
        description="Response content for analysis"
    )
    
    response_headers: Optional[Dict[str, str]] = Field(
        None,
        description="Response headers"
    )
    
    attempt_number: int = Field(
        1,
        description="Current attempt number (1-based)"
    )
    
    max_attempts: int = Field(
        3,
        description="Maximum number of attempts allowed"
    )
    
    previous_error_type: Optional[str] = Field(
        None,
        description="Type of previous error (for retry planning)"
    )
    
    enable_content_analysis: bool = Field(
        True,
        description="Whether to analyze response content for challenge detection"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_detector = None
        self.retry_manager = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.ErrorHandlingTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_components(self) -> bool:
        """Initialize error detector and retry manager"""
        if self.error_detector is None or self.retry_manager is None:
            try:
                detector_config = {
                    "content_analysis_enabled": self.enable_content_analysis,
                    "max_content_analysis_size": 50000
                }
                self.error_detector = ErrorDetector(detector_config)
                
                retry_config = {
                    "max_global_retries": 5,
                    "max_retry_delay": 300.0,
                    "jitter_factor": 0.1
                }
                self.retry_manager = RetryManager(retry_config)
                
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize error handling components: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the error handling operation.
        
        Returns:
            Dictionary containing operation results
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting error handling operation: {self.operation}")
            
            # Initialize components
            if not self._initialize_components():
                return {
                    "success": False,
                    "error": "Failed to initialize error handling components",
                    "operation": self.operation
                }
            
            if self.operation == "detect_error":
                return self._detect_error_operation(start_time)
            
            elif self.operation == "plan_retry":
                return self._plan_retry_operation(start_time)
            
            elif self.operation == "execute_retry":
                return self._execute_retry_operation(start_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {self.operation}",
                    "operation": self.operation,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            self.logger.error(f"Error during error handling operation: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": self.operation,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _detect_error_operation(self, start_time: float) -> Dict[str, Any]:
        """Detect and classify error type"""
        try:
            # Create mock response if we have status code and content
            mock_response = None
            if self.status_code and self.response_content is not None:
                mock_response = type('MockResponse', (), {
                    'status_code': self.status_code,
                    'text': self.response_content,
                    'headers': self.response_headers or {}
                })()
            
            # Create mock exception if we have error message
            mock_exception = None
            if self.error_message and not mock_response:
                mock_exception = Exception(self.error_message)
            
            # Detect error type
            error_details = self.error_detector.detect_error_type(
                response=mock_response,
                exception=mock_exception,
                url=self.url or ""
            )
            
            return {
                "success": True,
                "operation": "detect_error",
                "url": self.url,
                "error_classification": {
                    "error_type": error_details.error_type.value,
                    "status_code": error_details.status_code,
                    "error_message": error_details.error_message,
                    "is_retryable": error_details.is_retryable,
                    "is_temporary": error_details.is_temporary,
                    "retry_strategy": error_details.retry_strategy.value,
                    "max_retries": error_details.max_retries,
                    "base_delay": error_details.base_delay,
                    "detected_patterns": error_details.detected_patterns
                },
                "detector_statistics": self.error_detector.get_statistics(),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "detect_error",
                "url": self.url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _plan_retry_operation(self, start_time: float) -> Dict[str, Any]:
        """Plan retry strategy for an error"""
        try:
            # Create retry context
            retry_context = RetryContext(
                url=self.url or "",
                attempt_number=self.attempt_number,
                max_attempts=self.max_attempts
            )
            
            # Create error details (simplified)
            error_type = ErrorType.UNKNOWN_ERROR
            if self.previous_error_type:
                try:
                    error_type = ErrorType(self.previous_error_type)
                except ValueError:
                    pass
            
            error_details = ErrorDetails(
                error_type=error_type,
                status_code=self.status_code,
                error_message=self.error_message or "Unknown error"
            )
            
            # Check if retry should be attempted
            should_retry, retry_reason = self.retry_manager.should_retry(
                retry_context, error_details
            )
            
            retry_delay = 0.0
            if should_retry:
                retry_delay = self.retry_manager.calculate_delay(
                    retry_context, error_details
                )
            
            return {
                "success": True,
                "operation": "plan_retry",
                "url": self.url,
                "retry_plan": {
                    "should_retry": should_retry,
                    "retry_reason": retry_reason,
                    "retry_delay_seconds": retry_delay,
                    "attempt_number": self.attempt_number,
                    "max_attempts": self.max_attempts,
                    "retry_strategy": error_details.retry_strategy.value,
                    "error_type": error_details.error_type.value
                },
                "retry_manager_statistics": self.retry_manager.get_statistics(),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "plan_retry",
                "url": self.url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _execute_retry_operation(self, start_time: float) -> Dict[str, Any]:
        """Execute retry delay"""
        try:
            # This operation just executes the delay
            # The actual retry request would be handled by the calling code
            
            # Create simplified error details for delay calculation
            error_type = ErrorType.UNKNOWN_ERROR
            if self.previous_error_type:
                try:
                    error_type = ErrorType(self.previous_error_type)
                except ValueError:
                    pass
            
            error_details = ErrorDetails(
                error_type=error_type,
                status_code=self.status_code,
                error_message=self.error_message or "Unknown error"
            )
            
            retry_context = RetryContext(
                url=self.url or "",
                attempt_number=self.attempt_number,
                max_attempts=self.max_attempts
            )
            
            # Calculate and execute delay
            delay = self.retry_manager.calculate_delay(retry_context, error_details)
            actual_delay = self.retry_manager.execute_retry_delay(delay)
            
            return {
                "success": True,
                "operation": "execute_retry",
                "url": self.url,
                "retry_execution": {
                    "planned_delay_seconds": delay,
                    "actual_delay_seconds": actual_delay,
                    "attempt_number": self.attempt_number,
                    "retry_completed": True
                },
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "execute_retry",
                "url": self.url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the error handling tool
    print("Testing ErrorHandlingTool...")
    
    # Test error detection
    tool = ErrorHandlingTool(
        operation="detect_error",
        url="https://example.com/blocked",
        status_code=403,
        response_content="<html><body>Access Denied - Your IP has been blocked</body></html>",
        enable_content_analysis=True
    )
    
    result = tool.run()
    print(f"Error detection result: {result.get('success', False)}")
    
    if result.get("success"):
        error_class = result.get("error_classification", {})
        print(f"Error type: {error_class.get('error_type')}")
        print(f"Is retryable: {error_class.get('is_retryable')}")
        print(f"Detected patterns: {error_class.get('detected_patterns')}")
    
    # Test retry planning
    tool = ErrorHandlingTool(
        operation="plan_retry",
        url="https://example.com/timeout",
        previous_error_type="timeout_error",
        attempt_number=2,
        max_attempts=3
    )
    
    result = tool.run()
    print(f"\nRetry planning result: {result.get('success', False)}")
    
    if result.get("success"):
        retry_plan = result.get("retry_plan", {})
        print(f"Should retry: {retry_plan.get('should_retry')}")
        print(f"Delay: {retry_plan.get('retry_delay_seconds'):.2f}s")