"""
Centralized Error Handling System for VRSEN Agency Swarm

Provides comprehensive error handling, classification, recovery strategies,
and logging for all components in the lead generation pipeline.
"""

import logging
import time
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
from datetime import datetime
from contextlib import contextmanager


class ErrorCategory(Enum):
    """Categories of errors for classification and handling"""
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    PARSING = "parsing"
    BUSINESS_LOGIC = "business_logic"
    INFRASTRUCTURE = "infrastructure"
    EXTERNAL_API = "external_api"
    DATA_QUALITY = "data_quality"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for error prioritization"""
    CRITICAL = "critical"  # System failure, immediate attention needed
    HIGH = "high"          # Major functionality impaired
    MEDIUM = "medium"      # Partial functionality affected
    LOW = "low"            # Minor issue, system continues
    INFO = "info"          # Informational, not an error


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY_IMMEDIATE = "retry_immediate"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_WITH_DIFFERENT_PARAMS = "retry_with_different_params"
    SKIP_AND_CONTINUE = "skip_and_continue"
    FALLBACK_TO_ALTERNATIVE = "fallback_to_alternative"
    MANUAL_INTERVENTION = "manual_intervention"
    ABORT_OPERATION = "abort_operation"
    CACHE_AND_RETRY_LATER = "cache_and_retry_later"


@dataclass
class ErrorContext:
    """Context information for an error occurrence"""
    timestamp: float = field(default_factory=time.time)
    agent_name: Optional[str] = None
    operation: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class ErrorRecord:
    """Complete record of an error for tracking and analysis"""
    error_id: str
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    suggested_strategy: RecoveryStrategy
    occurrence_count: int = 1
    first_occurrence: float = field(default_factory=time.time)
    last_occurrence: float = field(default_factory=time.time)


class ErrorPatternDetector:
    """Detects patterns in errors for intelligent handling"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.error_history: List[ErrorRecord] = []
        self.pattern_rules = self._initialize_pattern_rules()
    
    def _initialize_pattern_rules(self) -> Dict[str, Callable]:
        """Initialize pattern detection rules"""
        return {
            "repeated_rate_limit": self._detect_repeated_rate_limit,
            "cascading_failure": self._detect_cascading_failure,
            "cyclic_error": self._detect_cyclic_error,
            "degrading_performance": self._detect_degrading_performance
        }
    
    def _detect_repeated_rate_limit(self) -> bool:
        """Detect repeated rate limiting errors"""
        if len(self.error_history) < 3:
            return False
        
        recent_errors = self.error_history[-10:]
        rate_limit_count = sum(
            1 for e in recent_errors 
            if e.category == ErrorCategory.RATE_LIMIT
        )
        return rate_limit_count >= 5
    
    def _detect_cascading_failure(self) -> bool:
        """Detect cascading failures across components"""
        if len(self.error_history) < 5:
            return False
        
        recent_errors = self.error_history[-5:]
        unique_agents = set(e.context.agent_name for e in recent_errors if e.context.agent_name)
        return len(unique_agents) >= 3 and all(
            e.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
            for e in recent_errors
        )
    
    def _detect_cyclic_error(self) -> bool:
        """Detect errors occurring in cycles"""
        if len(self.error_history) < 10:
            return False
        
        # Look for repeating error patterns
        recent_types = [e.error_type for e in self.error_history[-10:]]
        pattern_length = len(recent_types) // 2
        
        if pattern_length >= 2:
            first_half = recent_types[:pattern_length]
            second_half = recent_types[pattern_length:pattern_length*2]
            return first_half == second_half
        
        return False
    
    def _detect_degrading_performance(self) -> bool:
        """Detect degrading system performance through error patterns"""
        if len(self.error_history) < 20:
            return False
        
        # Check if error frequency is increasing
        recent_errors = self.error_history[-20:]
        first_half_count = sum(1 for e in recent_errors[:10])
        second_half_count = sum(1 for e in recent_errors[10:])
        
        return second_half_count > first_half_count * 1.5
    
    def add_error(self, error: ErrorRecord):
        """Add error to history and detect patterns"""
        self.error_history.append(error)
        
        # Keep window size limited
        if len(self.error_history) > self.window_size:
            self.error_history = self.error_history[-self.window_size:]
    
    def detect_patterns(self) -> List[str]:
        """Detect all current error patterns"""
        detected_patterns = []
        
        for pattern_name, detector in self.pattern_rules.items():
            if detector():
                detected_patterns.append(pattern_name)
        
        return detected_patterns


class ErrorHandler:
    """
    Centralized error handler for the VRSEN Agency Swarm.
    
    Features:
    - Error classification and categorization
    - Intelligent recovery strategy selection
    - Pattern detection for systematic issues
    - Comprehensive error logging and tracking
    - Error aggregation and reporting
    """
    
    def __init__(self, 
                 agent_name: Optional[str] = None,
                 log_dir: str = "logs/errors",
                 enable_pattern_detection: bool = True):
        """
        Initialize error handler.
        
        Args:
            agent_name: Name of the agent using this handler
            log_dir: Directory for error logs
            enable_pattern_detection: Enable pattern detection
        """
        self.agent_name = agent_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        self.error_registry: Dict[str, ErrorRecord] = {}
        self.pattern_detector = ErrorPatternDetector() if enable_pattern_detection else None
        self.recovery_handlers = self._initialize_recovery_handlers()
        
        # Error statistics
        self.stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_success_rate": 0.0,
            "patterns_detected": []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured error logging"""
        logger_name = f"vrsen.error_handler"
        if self.agent_name:
            logger_name += f".{self.agent_name}"
        
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # File handler for errors
            error_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(error_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _initialize_recovery_handlers(self) -> Dict[RecoveryStrategy, Callable]:
        """Initialize recovery strategy handlers"""
        return {
            RecoveryStrategy.RETRY_IMMEDIATE: self._retry_immediate,
            RecoveryStrategy.RETRY_WITH_BACKOFF: self._retry_with_backoff,
            RecoveryStrategy.SKIP_AND_CONTINUE: self._skip_and_continue,
            RecoveryStrategy.FALLBACK_TO_ALTERNATIVE: self._fallback_to_alternative,
            RecoveryStrategy.ABORT_OPERATION: self._abort_operation
        }
    
    def classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """
        Classify an error into category and severity.
        
        Args:
            error: The exception to classify
            
        Returns:
            Tuple of (ErrorCategory, ErrorSeverity)
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Category classification
        if any(term in error_msg for term in ['timeout', 'timed out']):
            category = ErrorCategory.TIMEOUT
        elif any(term in error_msg for term in ['rate limit', '429', 'too many requests']):
            category = ErrorCategory.RATE_LIMIT
        elif any(term in error_msg for term in ['network', 'connection', 'socket']):
            category = ErrorCategory.NETWORK
        elif any(term in error_msg for term in ['auth', 'permission', '401', '403']):
            category = ErrorCategory.AUTHENTICATION
        elif any(term in error_msg for term in ['parse', 'decode', 'json', 'xml']):
            category = ErrorCategory.PARSING
        elif any(term in error_msg for term in ['validation', 'invalid', 'required']):
            category = ErrorCategory.VALIDATION
        else:
            category = ErrorCategory.UNKNOWN
        
        # Severity classification
        if any(term in error_msg for term in ['critical', 'fatal', 'crash']):
            severity = ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.AUTHENTICATION, ErrorCategory.RATE_LIMIT]:
            severity = ErrorSeverity.HIGH
        elif category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            severity = ErrorSeverity.MEDIUM
        else:
            severity = ErrorSeverity.LOW
        
        return category, severity
    
    def suggest_recovery_strategy(self, 
                                 category: ErrorCategory, 
                                 severity: ErrorSeverity,
                                 context: Optional[ErrorContext] = None) -> RecoveryStrategy:
        """
        Suggest a recovery strategy based on error classification.
        
        Args:
            category: Error category
            severity: Error severity
            context: Error context
            
        Returns:
            Suggested recovery strategy
        """
        # Critical errors should abort
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT_OPERATION
        
        # Category-specific strategies
        strategy_map = {
            ErrorCategory.RATE_LIMIT: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorCategory.NETWORK: RecoveryStrategy.RETRY_IMMEDIATE,
            ErrorCategory.TIMEOUT: RecoveryStrategy.RETRY_WITH_DIFFERENT_PARAMS,
            ErrorCategory.AUTHENTICATION: RecoveryStrategy.MANUAL_INTERVENTION,
            ErrorCategory.PARSING: RecoveryStrategy.SKIP_AND_CONTINUE,
            ErrorCategory.VALIDATION: RecoveryStrategy.SKIP_AND_CONTINUE,
            ErrorCategory.BUSINESS_LOGIC: RecoveryStrategy.FALLBACK_TO_ALTERNATIVE
        }
        
        return strategy_map.get(category, RecoveryStrategy.SKIP_AND_CONTINUE)
    
    def log_error(self,
                  error: Exception,
                  category: Optional[ErrorCategory] = None,
                  severity: Optional[ErrorSeverity] = None,
                  context: Optional[Dict[str, Any]] = None,
                  operation: Optional[str] = None) -> ErrorRecord:
        """
        Log an error with full context and classification.
        
        Args:
            error: The exception to log
            category: Override automatic categorization
            severity: Override automatic severity detection
            context: Additional context information
            operation: Name of the operation that failed
            
        Returns:
            ErrorRecord for the logged error
        """
        # Auto-classify if not provided
        if category is None or severity is None:
            auto_category, auto_severity = self.classify_error(error)
            category = category or auto_category
            severity = severity or auto_severity
        
        # Create error context
        error_context = ErrorContext(
            agent_name=self.agent_name,
            operation=operation,
            input_data=context,
            stack_trace=traceback.format_exc(),
            additional_info={"error_class": type(error).__name__}
        )
        
        # Generate error ID
        error_id = f"{type(error).__name__}_{int(time.time()*1000)}"
        
        # Check if this error type exists
        error_key = f"{type(error).__name__}:{str(error)[:100]}"
        
        if error_key in self.error_registry:
            # Update existing error record
            record = self.error_registry[error_key]
            record.occurrence_count += 1
            record.last_occurrence = time.time()
        else:
            # Create new error record
            strategy = self.suggest_recovery_strategy(category, severity, error_context)
            
            record = ErrorRecord(
                error_id=error_id,
                error_type=type(error).__name__,
                error_message=str(error),
                category=category,
                severity=severity,
                context=error_context,
                suggested_strategy=strategy
            )
            
            self.error_registry[error_key] = record
        
        # Update statistics
        self._update_statistics(category, severity)
        
        # Add to pattern detector
        if self.pattern_detector:
            self.pattern_detector.add_error(record)
            patterns = self.pattern_detector.detect_patterns()
            if patterns:
                self.stats["patterns_detected"] = patterns
                self.logger.warning(f"Error patterns detected: {patterns}")
        
        # Log based on severity
        log_message = self._format_error_log(record)
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Save detailed error record
        self._save_error_record(record)
        
        return record
    
    def _format_error_log(self, record: ErrorRecord) -> str:
        """Format error record for logging"""
        return (
            f"[{record.severity.value.upper()}] {record.category.value} error in "
            f"{record.context.agent_name or 'unknown'}: {record.error_message} "
            f"(Occurrences: {record.occurrence_count}, Strategy: {record.suggested_strategy.value})"
        )
    
    def _save_error_record(self, record: ErrorRecord):
        """Save detailed error record to file"""
        try:
            error_file = self.log_dir / f"error_{record.error_id}.json"
            
            # Convert to serializable format
            record_dict = asdict(record)
            record_dict['category'] = record.category.value
            record_dict['severity'] = record.severity.value
            record_dict['suggested_strategy'] = record.suggested_strategy.value
            
            with open(error_file, 'w') as f:
                json.dump(record_dict, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save error record: {e}")
    
    def _update_statistics(self, category: ErrorCategory, severity: ErrorSeverity):
        """Update error statistics"""
        self.stats["total_errors"] += 1
        
        # By category
        cat_key = category.value
        self.stats["errors_by_category"][cat_key] = (
            self.stats["errors_by_category"].get(cat_key, 0) + 1
        )
        
        # By severity
        sev_key = severity.value
        self.stats["errors_by_severity"][sev_key] = (
            self.stats["errors_by_severity"].get(sev_key, 0) + 1
        )
    
    def attempt_recovery(self, 
                        error: Exception,
                        operation: Callable,
                        *args,
                        strategy: Optional[RecoveryStrategy] = None,
                        **kwargs) -> tuple[bool, Any]:
        """
        Attempt to recover from an error using appropriate strategy.
        
        Args:
            error: The error to recover from
            operation: The operation to retry/recover
            *args: Arguments for the operation
            strategy: Override automatic strategy selection
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Tuple of (success, result)
        """
        # Classify error if strategy not provided
        if strategy is None:
            category, severity = self.classify_error(error)
            strategy = self.suggest_recovery_strategy(category, severity)
        
        self.logger.info(f"Attempting recovery with strategy: {strategy.value}")
        
        # Execute recovery strategy
        handler = self.recovery_handlers.get(strategy)
        if handler:
            return handler(operation, args, kwargs, error)
        else:
            self.logger.warning(f"No handler for strategy: {strategy.value}")
            return False, None
    
    def _retry_immediate(self, operation, args, kwargs, error) -> tuple[bool, Any]:
        """Retry operation immediately"""
        try:
            result = operation(*args, **kwargs)
            self.logger.info("Immediate retry successful")
            return True, result
        except Exception as e:
            self.logger.warning(f"Immediate retry failed: {e}")
            return False, None
    
    def _retry_with_backoff(self, operation, args, kwargs, error) -> tuple[bool, Any]:
        """Retry with exponential backoff"""
        delays = [1, 2, 4, 8, 16]
        
        for attempt, delay in enumerate(delays, 1):
            self.logger.info(f"Retry attempt {attempt}/{len(delays)} after {delay}s")
            time.sleep(delay)
            
            try:
                result = operation(*args, **kwargs)
                self.logger.info(f"Retry successful on attempt {attempt}")
                return True, result
            except Exception as e:
                if attempt == len(delays):
                    self.logger.error(f"All retry attempts failed: {e}")
                    return False, None
                continue
        
        return False, None
    
    def _skip_and_continue(self, operation, args, kwargs, error) -> tuple[bool, Any]:
        """Skip the failed operation and continue"""
        self.logger.info("Skipping failed operation and continuing")
        return True, None
    
    def _fallback_to_alternative(self, operation, args, kwargs, error) -> tuple[bool, Any]:
        """Fallback to alternative implementation"""
        # This would need to be customized per operation
        self.logger.info("Attempting fallback to alternative implementation")
        return False, None
    
    def _abort_operation(self, operation, args, kwargs, error) -> tuple[bool, Any]:
        """Abort the operation"""
        self.logger.error("Aborting operation due to critical error")
        raise error
    
    @contextmanager
    def error_context(self, operation: str, **context):
        """
        Context manager for error handling within an operation.
        
        Args:
            operation: Name of the operation
            **context: Additional context information
        """
        try:
            yield
        except Exception as e:
            self.log_error(
                error=e,
                operation=operation,
                context=context
            )
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error handler statistics"""
        return {
            **self.stats,
            "unique_errors": len(self.error_registry),
            "most_common_errors": self._get_most_common_errors(5)
        }
    
    def _get_most_common_errors(self, limit: int) -> List[Dict[str, Any]]:
        """Get the most common errors"""
        sorted_errors = sorted(
            self.error_registry.values(),
            key=lambda x: x.occurrence_count,
            reverse=True
        )[:limit]
        
        return [
            {
                "type": e.error_type,
                "message": e.error_message[:100],
                "count": e.occurrence_count,
                "category": e.category.value
            }
            for e in sorted_errors
        ]
    
    def clear_statistics(self):
        """Clear error statistics"""
        self.stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_success_rate": 0.0,
            "patterns_detected": []
        }
        self.error_registry.clear()
        if self.pattern_detector:
            self.pattern_detector.error_history.clear()
        
        self.logger.info("Error statistics cleared")