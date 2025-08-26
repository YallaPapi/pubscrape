"""
Advanced Logging Configuration for VRSEN Agency Swarm

Provides structured logging with multiple handlers, performance tracking,
and context-aware logging capabilities.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Union
try:
    import structlog  # type: ignore
except Exception:  # pragma: no cover
    structlog = None  # fallback
try:
    import coloredlogs  # type: ignore
except Exception:  # pragma: no cover
    coloredlogs = None  # fallback
import json
from contextvars import ContextVar

# Context variables for structured logging
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
agent_id: ContextVar[Optional[str]] = ContextVar('agent_id', default=None)


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context variables
        if request_id.get():
            log_data['request_id'] = request_id.get()
        if session_id.get():
            log_data['session_id'] = session_id.get()
        if agent_id.get():
            log_data['agent_id'] = agent_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'message', 'exc_info',
                          'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class ContextFilter(logging.Filter):
    """
    Add context information to log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context variables to log record"""
        record.request_id = request_id.get()
        record.session_id = session_id.get()
        record.agent_id = agent_id.get()
        return True


class PerformanceLogger:
    """
    Specialized logger for performance metrics
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._start_times = {}
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation"""
        self._start_times[operation] = datetime.now()
        self.logger.debug(f"Started operation: {operation}")
    
    def end_timer(self, operation: str, extra_data: Optional[Dict[str, Any]] = None) -> float:
        """End timing an operation and log the duration"""
        if operation not in self._start_times:
            self.logger.warning(f"Timer for operation '{operation}' was not started")
            return 0.0
        
        start_time = self._start_times.pop(operation)
        duration = (datetime.now() - start_time).total_seconds()
        
        log_data = {
            'operation': operation,
            'duration_seconds': duration,
            'performance_metric': True
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        self.logger.info(f"Completed operation: {operation} in {duration:.3f}s", extra=log_data)
        return duration
    
    def log_metric(self, metric_name: str, value: Union[int, float], unit: str = "", 
                   extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a performance metric"""
        log_data = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit,
            'performance_metric': True
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        self.logger.info(f"Metric: {metric_name} = {value}{unit}", extra=log_data)


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False,
    enable_structured: bool = True,
    max_file_size: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5,
    app_name: str = "vrsen-pubscrape"
) -> logging.Logger:
    """
    Setup comprehensive logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_json: Enable JSON structured logging
        enable_structured: Enable structlog for structured logging
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        app_name: Application name for log files
        
    Returns:
        Configured logger instance
    """
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add context filter to all handlers
    context_filter = ContextFilter()
    
    # Console handler with colored output
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_json:
            console_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(console_handler)
        else:
            # Use coloredlogs if available; else basic formatter
            if coloredlogs is not None:
                try:
                    coloredlogs.install(
                        level=level.upper(),
                        logger=root_logger,
                        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        field_styles={
                            'asctime': {'color': 'green'},
                            'hostname': {'color': 'magenta'},
                            'levelname': {'color': 'black', 'bold': True},
                            'name': {'color': 'blue'},
                            'programname': {'color': 'cyan'}
                        }
                    )
                except Exception:
                    console_handler.setFormatter(logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    ))
                    root_logger.addHandler(console_handler)
            else:
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file:
        # Main application log
        main_log_file = log_path / f"{app_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)
        
        # Error log (ERROR and CRITICAL only)
        error_log_file = log_path / f"{app_name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        if enable_json:
            error_handler.setFormatter(JSONFormatter())
        else:
            error_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        error_handler.addFilter(context_filter)
        root_logger.addHandler(error_handler)
        
        # Performance log
        perf_log_file = log_path / f"{app_name}_performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        class PerformanceFilter(logging.Filter):
            def filter(self, record):
                return hasattr(record, 'performance_metric') and record.performance_metric
        
        perf_handler.addFilter(PerformanceFilter())
        perf_handler.addFilter(context_filter)
        
        if enable_json:
            perf_handler.setFormatter(JSONFormatter())
        else:
            perf_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(operation)s - %(duration_seconds).3fs - %(message)s'
            ))
        
        root_logger.addHandler(perf_handler)
    
    # Configure structlog if enabled
    if enable_structured and structlog is not None:
        try:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer() if enable_json else structlog.dev.ConsoleRenderer(),
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
        except Exception:
            # Fallback to non-structured logging
            pass
    
    # Create application logger
    app_logger = logging.getLogger(app_name)
    
    # Log startup message
    app_logger.info(f"Logging initialized - Level: {level}, Directory: {log_dir}")
    
    return app_logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (defaults to caller's module)
        
    Returns:
        Logger instance
    """
    if name is None:
        # Get caller's module name
        import inspect
        frame = inspect.currentframe()
        try:
            caller_module = frame.f_back.f_globals.get('__name__', 'unknown')
            name = caller_module
        finally:
            del frame
    return logging.getLogger(name)


def get_performance_logger(name: str = None) -> PerformanceLogger:
    """
    Get a performance logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        PerformanceLogger instance
    """
    logger = get_logger(name)
    return PerformanceLogger(logger)


def set_context(request_id_val: str = None, session_id_val: str = None, agent_id_val: str = None):
    """
    Set logging context variables.
    
    Args:
        request_id_val: Request ID
        session_id_val: Session ID  
        agent_id_val: Agent ID
    """
    if request_id_val:
        request_id.set(request_id_val)
    if session_id_val:
        session_id.set(session_id_val)
    if agent_id_val:
        agent_id.set(agent_id_val)


def clear_context():
    """Clear all logging context variables"""
    request_id.set(None)
    session_id.set(None)
    agent_id.set(None)


class LoggingMixin:
    """
    Mixin class to add logging capabilities to any class
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self._logger
    
    @property
    def perf_logger(self) -> PerformanceLogger:
        """Get performance logger for this class"""
        if not hasattr(self, '_perf_logger'):
            self._perf_logger = get_performance_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self._perf_logger


def configure_agent_logging(agent_name: str, agent_id: str) -> logging.Logger:
    """
    Configure logging for a specific agent.
    
    Args:
        agent_name: Name of the agent
        agent_id: Unique agent ID
        
    Returns:
        Configured logger for the agent
    """
    # Set agent context
    set_context(agent_id_val=agent_id)
    
    # Create agent-specific logger
    logger = get_logger(f"agent.{agent_name}")
    
    logger.info(f"Agent logger configured: {agent_name} ({agent_id})")
    
    return logger


def log_function_call(func):
    """
    Decorator to automatically log function calls with performance timing.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import functools
    import inspect
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        perf_logger = get_performance_logger(func.__module__)
        
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        # Log function entry
        arg_names = inspect.signature(func).parameters.keys()
        arg_values = dict(zip(arg_names, args))
        arg_values.update(kwargs)
        
        logger.debug(f"Entering function: {func_name}", extra={
            'function': func_name,
            'arguments': {k: str(v)[:100] for k, v in arg_values.items()}
        })
        
        # Start performance timer
        perf_logger.start_timer(func_name)
        
        try:
            result = func(*args, **kwargs)
            
            # Log successful completion
            duration = perf_logger.end_timer(func_name)
            logger.debug(f"Function completed: {func_name} in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            # Log exception
            duration = perf_logger.end_timer(func_name)
            logger.error(f"Function failed: {func_name} after {duration:.3f}s", 
                        exc_info=True, extra={
                'function': func_name,
                'exception_type': type(e).__name__,
                'exception_message': str(e)
            })
            raise
    return wrapper


# Convenience function for quick logger setup
def quick_setup(level: str = "INFO", console_only: bool = False) -> logging.Logger:
    """
    Quick logger setup for simple use cases.
    
    Args:
        level: Logging level
        console_only: Only log to console
        
    Returns:
        Configured logger
    """
    return setup_logging(
        level=level,
        enable_console=True,
        enable_file=not console_only,
        enable_json=False,
        enable_structured=False
    )