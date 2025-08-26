"""
Advanced Error Handling System for VRSEN Agency Swarm

Provides comprehensive error handling with retry logic, circuit breakers,
and intelligent error classification and recovery strategies.
"""

import asyncio
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category classification"""
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    PARSING = "parsing"
    SYSTEM = "system"
    CONFIGURATION = "configuration"
    EXTERNAL_API = "external_api"
    USER_INPUT = "user_input"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Detailed error information"""
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    recoverable: bool = True
    suggested_action: Optional[str] = None


class RetryableError(Exception):
    """Exception that indicates the operation should be retried"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class NonRetryableError(Exception):
    """Exception that indicates the operation should not be retried"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.HIGH):
        super().__init__(message)
        self.category = category
        self.severity = severity


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, 
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half-open'
            else:
                raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.timeout)
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = 'closed'
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'


class ErrorHandler:
    """
    Comprehensive error handling system with retry logic and classification
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, 
                 backoff_multiplier: float = 2.0, max_delay: float = 60.0,
                 logger: Optional[logging.Logger] = None,
                 error_log_file: Optional[str] = None):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay
        self.logger = logger or logging.getLogger(__name__)
        self.error_log_file = error_log_file
        
        # Error statistics
        self.error_stats: Dict[str, int] = {}
        self.error_history: List[ErrorInfo] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Error classification rules
        self._setup_error_classification()
    
    def _setup_error_classification(self):
        """Setup error classification rules"""
        self.error_rules = {
            # Network errors
            'ConnectionError': (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
            'TimeoutError': (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
            'HTTPError': (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
            'RequestException': (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
            
            # Rate limiting
            'RateLimitError': (ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM, True),
            'TooManyRequests': (ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM, True),
            
            # Authentication
            'AuthenticationError': (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
            'Unauthorized': (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
            
            # Validation
            'ValidationError': (ErrorCategory.VALIDATION, ErrorSeverity.LOW, False),
            'ValueError': (ErrorCategory.VALIDATION, ErrorSeverity.LOW, False),
            'KeyError': (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, False),
            
            # Parsing
            'ParseError': (ErrorCategory.PARSING, ErrorSeverity.MEDIUM, True),
            'JSONDecodeError': (ErrorCategory.PARSING, ErrorSeverity.MEDIUM, True),
            
            # System errors
            'FileNotFoundError': (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM, False),
            'OSError': (ErrorCategory.SYSTEM, ErrorSeverity.HIGH, False),
            'MemoryError': (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, False),
        }
    
    def classify_error(self, error: Exception) -> ErrorInfo:
        """
        Classify an error and create ErrorInfo object
        
        Args:
            error: Exception to classify
            
        Returns:
            ErrorInfo object with classification details
        """
        error_type = type(error).__name__
        
        # Get classification from rules
        if error_type in self.error_rules:
            category, severity, recoverable = self.error_rules[error_type]
        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.MEDIUM
            recoverable = True
        
        # Check for specific error patterns
        message = str(error).lower()
        if 'rate limit' in message or 'too many requests' in message:
            category = ErrorCategory.RATE_LIMIT
            recoverable = True
        elif 'timeout' in message:
            category = ErrorCategory.NETWORK
            recoverable = True
        elif 'unauthorized' in message or 'forbidden' in message:
            category = ErrorCategory.AUTHENTICATION
            recoverable = False
        
        # Get suggested action
        suggested_action = self._get_suggested_action(category, error_type)
        
        return ErrorInfo(
            error_type=error_type,
            message=str(error),
            category=category,
            severity=severity,
            timestamp=datetime.now(),
            traceback=traceback.format_exc(),
            recoverable=recoverable,
            suggested_action=suggested_action
        )
    
    def _get_suggested_action(self, category: ErrorCategory, error_type: str) -> str:
        """Get suggested action for error recovery"""
        suggestions = {
            ErrorCategory.NETWORK: "Check network connection and retry",
            ErrorCategory.RATE_LIMIT: "Wait and retry with exponential backoff",
            ErrorCategory.AUTHENTICATION: "Check API keys and credentials",
            ErrorCategory.VALIDATION: "Validate input data and parameters",
            ErrorCategory.PARSING: "Check data format and parsing logic",
            ErrorCategory.SYSTEM: "Check system resources and permissions",
            ErrorCategory.CONFIGURATION: "Review configuration settings",
            ErrorCategory.EXTERNAL_API: "Check external API status and documentation"
        }
        
        return suggestions.get(category, "Review error details and logs")
    
    async def execute_with_retry(
        self, 
        func: Callable,
        *args,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        backoff_multiplier: Optional[float] = None,
        operation_name: str = "operation",
        circuit_breaker_key: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic and error handling
        
        Args:
            func: Function to execute
            *args: Function arguments
            max_retries: Maximum retry attempts
            retry_delay: Initial retry delay
            backoff_multiplier: Backoff multiplier for delays
            operation_name: Name for logging
            circuit_breaker_key: Key for circuit breaker
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        max_retries = max_retries or self.max_retries
        retry_delay = retry_delay or self.retry_delay
        backoff_multiplier = backoff_multiplier or self.backoff_multiplier
        
        # Get or create circuit breaker
        circuit_breaker = None
        if circuit_breaker_key:
            if circuit_breaker_key not in self.circuit_breakers:
                self.circuit_breakers[circuit_breaker_key] = CircuitBreaker()
            circuit_breaker = self.circuit_breakers[circuit_breaker_key]
        
        last_error = None
        current_delay = retry_delay
        
        for attempt in range(max_retries + 1):
            try:
                # Execute with circuit breaker if available
                if circuit_breaker:
                    result = circuit_breaker.call(func, *args, **kwargs)
                else:
                    # Handle async functions
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                
                # Success - log and return
                if attempt > 0:
                    self.logger.info(f"{operation_name} succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_error = e
                error_info = self.classify_error(e)
                error_info.retry_count = attempt
                error_info.max_retries = max_retries
                
                # Log error
                self._log_error(error_info, operation_name, attempt, max_retries)
                
                # Update statistics
                self._update_error_stats(error_info)
                
                # Check if error is retryable
                if not error_info.recoverable or isinstance(e, NonRetryableError):
                    self.logger.error(f"{operation_name} failed with non-retryable error: {e}")
                    raise e
                
                # Check if we've exhausted retries
                if attempt >= max_retries:
                    self.logger.error(f"{operation_name} failed after {max_retries} retries")
                    break
                
                # Wait before retry
                if current_delay > 0:
                    self.logger.info(f"Retrying {operation_name} in {current_delay:.1f} seconds...")
                    await asyncio.sleep(current_delay)
                
                # Increase delay for next attempt
                current_delay = min(current_delay * backoff_multiplier, self.max_delay)
        
        # All retries exhausted
        if last_error:
            raise last_error
    
    def _log_error(self, error_info: ErrorInfo, operation_name: str, 
                   attempt: int, max_retries: int):
        """Log error with appropriate level"""
        log_data = {
            'operation': operation_name,
            'attempt': attempt + 1,
            'max_retries': max_retries + 1,
            'error_type': error_info.error_type,
            'error_category': error_info.category.value,
            'error_severity': error_info.severity.value,
            'recoverable': error_info.recoverable,
            'suggested_action': error_info.suggested_action
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"{operation_name} critical error: {error_info.message}", 
                               extra=log_data, exc_info=True)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(f"{operation_name} error: {error_info.message}", 
                            extra=log_data, exc_info=True)
        elif attempt < max_retries and error_info.recoverable:
            self.logger.warning(f"{operation_name} attempt {attempt + 1} failed: {error_info.message}", 
                              extra=log_data)
        else:
            self.logger.error(f"{operation_name} failed: {error_info.message}", 
                            extra=log_data, exc_info=True)
        
        # Save to error log file if specified
        if self.error_log_file:
            self._save_error_to_file(error_info, operation_name)
    
    def _save_error_to_file(self, error_info: ErrorInfo, operation_name: str):
        """Save error to log file"""
        try:
            error_data = {
                'timestamp': error_info.timestamp.isoformat(),
                'operation': operation_name,
                'error_type': error_info.error_type,
                'message': error_info.message,
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'recoverable': error_info.recoverable,
                'retry_count': error_info.retry_count,
                'traceback': error_info.traceback,
                'context': error_info.context,
                'suggested_action': error_info.suggested_action
            }
            
            # Ensure log directory exists
            log_path = Path(self.error_log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to error log file
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to save error to file: {e}")
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """Update error statistics"""
        # Update counters
        self.error_stats[error_info.error_type] = self.error_stats.get(error_info.error_type, 0) + 1
        
        # Add to history (keep last 1000 errors)
        self.error_history.append(error_info)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error statistics"""
        total_errors = sum(self.error_stats.values())
        
        if not self.error_history:
            return {'total_errors': 0, 'error_types': {}}
        
        # Calculate error rates by category
        category_stats = {}
        severity_stats = {}
        
        for error in self.error_history:
            category = error.category.value
            severity = error.severity.value
            
            category_stats[category] = category_stats.get(category, 0) + 1
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
        
        # Recent errors (last hour)
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_errors = [e for e in self.error_history if e.timestamp > recent_cutoff]
        
        return {
            'total_errors': total_errors,
            'error_types': self.error_stats,
            'category_distribution': category_stats,
            'severity_distribution': severity_stats,
            'recent_errors_count': len(recent_errors),
            'error_rate_last_hour': len(recent_errors),
            'most_common_errors': sorted(self.error_stats.items(), 
                                       key=lambda x: x[1], reverse=True)[:5]
        }
    
    def reset_stats(self):
        """Reset error statistics"""
        self.error_stats.clear()
        self.error_history.clear()
        self.circuit_breakers.clear()
        self.logger.info("Error statistics reset")


def retry_on_failure(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
    operation_name: Optional[str] = None
):
    """
    Decorator for automatic retry on function failure
    
    Args:
        max_retries: Maximum retry attempts
        retry_delay: Initial retry delay
        backoff_multiplier: Backoff multiplier
        exceptions: Tuple of exceptions to retry on
        operation_name: Name for logging
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = ErrorHandler(
                max_retries=max_retries,
                retry_delay=retry_delay,
                backoff_multiplier=backoff_multiplier
            )
            
            return await error_handler.execute_with_retry(
                func, *args, **kwargs,
                operation_name=operation_name or func.__name__
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            error_handler = ErrorHandler(
                max_retries=max_retries,
                retry_delay=retry_delay,
                backoff_multiplier=backoff_multiplier
            )
            
            return asyncio.run(error_handler.execute_with_retry(
                func, *args, **kwargs,
                operation_name=operation_name or func.__name__
            ))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def handle_errors(category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """
    Decorator to automatically handle and classify errors
    
    Args:
        category: Error category
        severity: Error severity
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create custom exception with classification
                if hasattr(e, 'category'):
                    raise e  # Already classified
                
                # Add classification to exception
                e.category = category
                e.severity = severity
                raise e
        return wrapper
    return decorator