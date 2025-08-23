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
            'PermissionError': (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
            'Unauthorized': (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
            
            # Validation
            'ValidationError': (ErrorCategory.VALIDATION, ErrorSeverity.LOW, False),
            'ValueError': (ErrorCategory.VALIDATION, ErrorSeverity.LOW, False),
            'KeyError': (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, False),
            
            # Parsing
            'ParseError': (ErrorCategory.PARSING, ErrorSeverity.MEDIUM, True),
            'JSONDecodeError': (ErrorCategory.PARSING, ErrorSeverity.MEDIUM, True),
            
            # System errors\n            'FileNotFoundError': (ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM, False),\n            'PermissionError': (ErrorCategory.SYSTEM, ErrorSeverity.HIGH, False),\n            'OSError': (ErrorCategory.SYSTEM, ErrorSeverity.HIGH, False),\n            'MemoryError': (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, False),\n        }\n    \n    def classify_error(self, error: Exception) -> ErrorInfo:\n        \"\"\"\n        Classify an error and create ErrorInfo object\n        \n        Args:\n            error: Exception to classify\n            \n        Returns:\n            ErrorInfo object with classification details\n        \"\"\"\n        error_type = type(error).__name__\n        \n        # Get classification from rules\n        if error_type in self.error_rules:\n            category, severity, recoverable = self.error_rules[error_type]\n        else:\n            category = ErrorCategory.UNKNOWN\n            severity = ErrorSeverity.MEDIUM\n            recoverable = True\n        \n        # Check for specific error patterns\n        message = str(error).lower()\n        if 'rate limit' in message or 'too many requests' in message:\n            category = ErrorCategory.RATE_LIMIT\n            recoverable = True\n        elif 'timeout' in message:\n            category = ErrorCategory.NETWORK\n            recoverable = True\n        elif 'unauthorized' in message or 'forbidden' in message:\n            category = ErrorCategory.AUTHENTICATION\n            recoverable = False\n        \n        # Get suggested action\n        suggested_action = self._get_suggested_action(category, error_type)\n        \n        return ErrorInfo(\n            error_type=error_type,\n            message=str(error),\n            category=category,\n            severity=severity,\n            timestamp=datetime.now(),\n            traceback=traceback.format_exc(),\n            recoverable=recoverable,\n            suggested_action=suggested_action\n        )\n    \n    def _get_suggested_action(self, category: ErrorCategory, error_type: str) -> str:\n        \"\"\"Get suggested action for error recovery\"\"\"\n        suggestions = {\n            ErrorCategory.NETWORK: \"Check network connection and retry\",\n            ErrorCategory.RATE_LIMIT: \"Wait and retry with exponential backoff\",\n            ErrorCategory.AUTHENTICATION: \"Check API keys and credentials\",\n            ErrorCategory.VALIDATION: \"Validate input data and parameters\",\n            ErrorCategory.PARSING: \"Check data format and parsing logic\",\n            ErrorCategory.SYSTEM: \"Check system resources and permissions\",\n            ErrorCategory.CONFIGURATION: \"Review configuration settings\",\n            ErrorCategory.EXTERNAL_API: \"Check external API status and documentation\"\n        }\n        \n        return suggestions.get(category, \"Review error details and logs\")\n    \n    async def execute_with_retry(\n        self, \n        func: Callable,\n        *args,\n        max_retries: Optional[int] = None,\n        retry_delay: Optional[float] = None,\n        backoff_multiplier: Optional[float] = None,\n        operation_name: str = \"operation\",\n        circuit_breaker_key: Optional[str] = None,\n        **kwargs\n    ) -> Any:\n        \"\"\"\n        Execute function with retry logic and error handling\n        \n        Args:\n            func: Function to execute\n            *args: Function arguments\n            max_retries: Maximum retry attempts\n            retry_delay: Initial retry delay\n            backoff_multiplier: Backoff multiplier for delays\n            operation_name: Name for logging\n            circuit_breaker_key: Key for circuit breaker\n            **kwargs: Function keyword arguments\n            \n        Returns:\n            Function result\n            \n        Raises:\n            Exception: If all retries exhausted or non-retryable error\n        \"\"\"\n        max_retries = max_retries or self.max_retries\n        retry_delay = retry_delay or self.retry_delay\n        backoff_multiplier = backoff_multiplier or self.backoff_multiplier\n        \n        # Get or create circuit breaker\n        circuit_breaker = None\n        if circuit_breaker_key:\n            if circuit_breaker_key not in self.circuit_breakers:\n                self.circuit_breakers[circuit_breaker_key] = CircuitBreaker()\n            circuit_breaker = self.circuit_breakers[circuit_breaker_key]\n        \n        last_error = None\n        current_delay = retry_delay\n        \n        for attempt in range(max_retries + 1):\n            try:\n                # Execute with circuit breaker if available\n                if circuit_breaker:\n                    result = circuit_breaker.call(func, *args, **kwargs)\n                else:\n                    # Handle async functions\n                    if asyncio.iscoroutinefunction(func):\n                        result = await func(*args, **kwargs)\n                    else:\n                        result = func(*args, **kwargs)\n                \n                # Success - log and return\n                if attempt > 0:\n                    self.logger.info(f\"{operation_name} succeeded after {attempt} retries\")\n                \n                return result\n                \n            except Exception as e:\n                last_error = e\n                error_info = self.classify_error(e)\n                error_info.retry_count = attempt\n                error_info.max_retries = max_retries\n                \n                # Log error\n                self._log_error(error_info, operation_name, attempt, max_retries)\n                \n                # Update statistics\n                self._update_error_stats(error_info)\n                \n                # Check if error is retryable\n                if not error_info.recoverable or isinstance(e, NonRetryableError):\n                    self.logger.error(f\"{operation_name} failed with non-retryable error: {e}\")\n                    raise e\n                \n                # Check if we've exhausted retries\n                if attempt >= max_retries:\n                    self.logger.error(f\"{operation_name} failed after {max_retries} retries\")\n                    break\n                \n                # Wait before retry\n                if current_delay > 0:\n                    self.logger.info(f\"Retrying {operation_name} in {current_delay:.1f} seconds...\")\n                    await asyncio.sleep(current_delay)\n                \n                # Increase delay for next attempt\n                current_delay = min(current_delay * backoff_multiplier, self.max_delay)\n        \n        # All retries exhausted\n        if last_error:\n            raise last_error\n    \n    def _log_error(self, error_info: ErrorInfo, operation_name: str, \n                   attempt: int, max_retries: int):\n        \"\"\"Log error with appropriate level\"\"\"\n        log_data = {\n            'operation': operation_name,\n            'attempt': attempt + 1,\n            'max_retries': max_retries + 1,\n            'error_type': error_info.error_type,\n            'error_category': error_info.category.value,\n            'error_severity': error_info.severity.value,\n            'recoverable': error_info.recoverable,\n            'suggested_action': error_info.suggested_action\n        }\n        \n        if error_info.severity == ErrorSeverity.CRITICAL:\n            self.logger.critical(f\"{operation_name} critical error: {error_info.message}\", \n                               extra=log_data, exc_info=True)\n        elif error_info.severity == ErrorSeverity.HIGH:\n            self.logger.error(f\"{operation_name} error: {error_info.message}\", \n                            extra=log_data, exc_info=True)\n        elif attempt < max_retries and error_info.recoverable:\n            self.logger.warning(f\"{operation_name} attempt {attempt + 1} failed: {error_info.message}\", \n                              extra=log_data)\n        else:\n            self.logger.error(f\"{operation_name} failed: {error_info.message}\", \n                            extra=log_data, exc_info=True)\n        \n        # Save to error log file if specified\n        if self.error_log_file:\n            self._save_error_to_file(error_info, operation_name)\n    \n    def _save_error_to_file(self, error_info: ErrorInfo, operation_name: str):\n        \"\"\"Save error to log file\"\"\"\n        try:\n            error_data = {\n                'timestamp': error_info.timestamp.isoformat(),\n                'operation': operation_name,\n                'error_type': error_info.error_type,\n                'message': error_info.message,\n                'category': error_info.category.value,\n                'severity': error_info.severity.value,\n                'recoverable': error_info.recoverable,\n                'retry_count': error_info.retry_count,\n                'traceback': error_info.traceback,\n                'context': error_info.context,\n                'suggested_action': error_info.suggested_action\n            }\n            \n            # Ensure log directory exists\n            log_path = Path(self.error_log_file)\n            log_path.parent.mkdir(parents=True, exist_ok=True)\n            \n            # Append to error log file\n            with open(log_path, 'a', encoding='utf-8') as f:\n                f.write(json.dumps(error_data) + '\\n')\n                \n        except Exception as e:\n            self.logger.error(f\"Failed to save error to file: {e}\")\n    \n    def _update_error_stats(self, error_info: ErrorInfo):\n        \"\"\"Update error statistics\"\"\"\n        # Update counters\n        self.error_stats[error_info.error_type] = self.error_stats.get(error_info.error_type, 0) + 1\n        \n        # Add to history (keep last 1000 errors)\n        self.error_history.append(error_info)\n        if len(self.error_history) > 1000:\n            self.error_history = self.error_history[-1000:]\n    \n    def get_error_summary(self) -> Dict[str, Any]:\n        \"\"\"Get summary of error statistics\"\"\"\n        total_errors = sum(self.error_stats.values())\n        \n        if not self.error_history:\n            return {'total_errors': 0, 'error_types': {}}\n        \n        # Calculate error rates by category\n        category_stats = {}\n        severity_stats = {}\n        \n        for error in self.error_history:\n            category = error.category.value\n            severity = error.severity.value\n            \n            category_stats[category] = category_stats.get(category, 0) + 1\n            severity_stats[severity] = severity_stats.get(severity, 0) + 1\n        \n        # Recent errors (last hour)\n        recent_cutoff = datetime.now() - timedelta(hours=1)\n        recent_errors = [e for e in self.error_history if e.timestamp > recent_cutoff]\n        \n        return {\n            'total_errors': total_errors,\n            'error_types': self.error_stats,\n            'category_distribution': category_stats,\n            'severity_distribution': severity_stats,\n            'recent_errors_count': len(recent_errors),\n            'error_rate_last_hour': len(recent_errors),\n            'most_common_errors': sorted(self.error_stats.items(), \n                                       key=lambda x: x[1], reverse=True)[:5]\n        }\n    \n    def reset_stats(self):\n        \"\"\"Reset error statistics\"\"\"\n        self.error_stats.clear()\n        self.error_history.clear()\n        self.circuit_breakers.clear()\n        self.logger.info(\"Error statistics reset\")\n\n\ndef retry_on_failure(\n    max_retries: int = 3,\n    retry_delay: float = 1.0,\n    backoff_multiplier: float = 2.0,\n    exceptions: tuple = (Exception,),\n    operation_name: Optional[str] = None\n):\n    \"\"\"\n    Decorator for automatic retry on function failure\n    \n    Args:\n        max_retries: Maximum retry attempts\n        retry_delay: Initial retry delay\n        backoff_multiplier: Backoff multiplier\n        exceptions: Tuple of exceptions to retry on\n        operation_name: Name for logging\n        \n    Returns:\n        Decorated function\n    \"\"\"\n    def decorator(func):\n        @wraps(func)\n        async def async_wrapper(*args, **kwargs):\n            error_handler = ErrorHandler(\n                max_retries=max_retries,\n                retry_delay=retry_delay,\n                backoff_multiplier=backoff_multiplier\n            )\n            \n            return await error_handler.execute_with_retry(\n                func, *args, **kwargs,\n                operation_name=operation_name or func.__name__\n            )\n        \n        @wraps(func)\n        def sync_wrapper(*args, **kwargs):\n            error_handler = ErrorHandler(\n                max_retries=max_retries,\n                retry_delay=retry_delay,\n                backoff_multiplier=backoff_multiplier\n            )\n            \n            return asyncio.run(error_handler.execute_with_retry(\n                func, *args, **kwargs,\n                operation_name=operation_name or func.__name__\n            ))\n        \n        if asyncio.iscoroutinefunction(func):\n            return async_wrapper\n        else:\n            return sync_wrapper\n    \n    return decorator\n\n\ndef handle_errors(category: ErrorCategory = ErrorCategory.UNKNOWN, \n                 severity: ErrorSeverity = ErrorSeverity.MEDIUM):\n    \"\"\"\n    Decorator to automatically handle and classify errors\n    \n    Args:\n        category: Error category\n        severity: Error severity\n        \n    Returns:\n        Decorated function\n    \"\"\"\n    def decorator(func):\n        @wraps(func)\n        def wrapper(*args, **kwargs):\n            try:\n                return func(*args, **kwargs)\n            except Exception as e:\n                # Create custom exception with classification\n                if hasattr(e, 'category'):\n                    raise e  # Already classified\n                \n                # Add classification to exception\n                e.category = category\n                e.severity = severity\n                raise e\n        \n        return wrapper\n    return decorator"