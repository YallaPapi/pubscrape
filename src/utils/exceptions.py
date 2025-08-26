"""
Custom Exception Hierarchy for PubScrape Project

Provides standardized exceptions for consistent error handling
across all scraping operations and data processing workflows.
"""

from typing import Optional, Dict, Any


class PubScrapeException(Exception):
    """Base exception for all PubScrape operations"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        return base_msg


class ScrapingError(PubScrapeException):
    """Raised when web scraping operations fail"""
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 status_code: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        if url:
            context['url'] = url
        if status_code:
            context['status_code'] = status_code
        super().__init__(message, **kwargs)
        self.url = url
        self.status_code = status_code


class ConfigurationError(PubScrapeException):
    """Raised when configuration is invalid or missing"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        super().__init__(message, **kwargs)
        self.config_key = config_key


class ValidationError(PubScrapeException):
    """Raised when data validation fails"""
    
    def __init__(self, message: str, field_name: Optional[str] = None, 
                 field_value: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value:
            context['field_value'] = str(field_value)[:100]  # Truncate for safety
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value


class AuthenticationError(PubScrapeException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if service:
            context['service'] = service
        super().__init__(message, **kwargs)
        self.service = service


class RateLimitError(PubScrapeException):
    """Raised when API rate limits are exceeded"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, 
                 service: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if retry_after:
            context['retry_after'] = retry_after
        if service:
            context['service'] = service
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.service = service


class ParseError(PubScrapeException):
    """Raised when data parsing fails"""
    
    def __init__(self, message: str, data_type: Optional[str] = None, 
                 raw_data: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if data_type:
            context['data_type'] = data_type
        if raw_data:
            context['raw_data_sample'] = str(raw_data)[:200]  # Sample only
        super().__init__(message, **kwargs)
        self.data_type = data_type
        self.raw_data = raw_data


class NetworkError(PubScrapeException):
    """Raised when network operations fail"""
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 timeout: Optional[float] = None, **kwargs):
        context = kwargs.get('context', {})
        if url:
            context['url'] = url
        if timeout:
            context['timeout'] = timeout
        super().__init__(message, **kwargs)
        self.url = url
        self.timeout = timeout


class DataProcessingError(PubScrapeException):
    """Raised when data processing operations fail"""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 record_count: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        if record_count:
            context['record_count'] = record_count
        super().__init__(message, **kwargs)
        self.operation = operation
        self.record_count = record_count


class BrowserError(PubScrapeException):
    """Raised when browser automation fails"""
    
    def __init__(self, message: str, browser_type: Optional[str] = None, 
                 element_selector: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if browser_type:
            context['browser_type'] = browser_type
        if element_selector:
            context['element_selector'] = element_selector
        super().__init__(message, **kwargs)
        self.browser_type = browser_type
        self.element_selector = element_selector