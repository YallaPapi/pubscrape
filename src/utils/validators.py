"""
Comprehensive Input Validation and Security Framework

Provides secure input validation, sanitization, and protection against
common web vulnerabilities including XSS, SQL injection, and command injection.
"""

import re
import html
import urllib.parse
import ipaddress
import validators
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum


class ValidationError(ValueError):
    """Custom exception for validation errors"""
    pass


class SecurityLevel(Enum):
    """Security validation levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_value: Any
    errors: List[str]
    warnings: List[str]
    security_issues: List[str]


class InputValidator:
    """
    Comprehensive input validation and sanitization system
    """
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        self.security_level = security_level
        self.logger = logging.getLogger(__name__)
        
        # Dangerous patterns for different attack types
        self._setup_security_patterns()
    
    def _setup_security_patterns(self):
        """Setup patterns for detecting security threats"""
        
        # SQL Injection patterns
        self.sql_injection_patterns = [
            r"('|(\\')|(;)|(\\;)|(\|)|(\*)|(%)|(\$)|(table_name)|(column_name))",
            r"(union|select|insert|delete|update|drop|create|alter|exec|execute|script)",
            r"(\s*(or|and)\s+[\w\s]*\s*[=<>]+)",
            r"(1\s*=\s*1|1\s*=\s*0|true\s*=\s*true|false\s*=\s*false)",
            r"(--|#|\/\*|\*\/)",
            r"(\bor\b|\band\b)\s+\d+\s*[=<>]\s*\d+",
            r"(sleep\s*\(|benchmark\s*\(|pg_sleep\s*\()",
            r"(information_schema|sysobjects|syscolumns|pg_tables)"
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<\s*script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script\s*>",
            r"javascript\s*:",
            r"on\w+\s*=",
            r"<\s*iframe\b",
            r"<\s*object\b",
            r"<\s*embed\b",
            r"<\s*applet\b",
            r"eval\s*\(",
            r"expression\s*\(",
            r"vbscript:",
            r"data:text/html"
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            r"[;&|`$(){}[\]\\]",
            r"(rm\s+|del\s+|format\s+|fdisk\s+)",
            r"(wget\s+|curl\s+|nc\s+|telnet\s+|ssh\s+)",
            r"(\.\./|\.\.\\\|\.\.%2f|\.\.%5c)",
            r"(cmd\.exe|powershell|bash|sh|/bin/)",
            r"(<|>|\||&|;|\$\(|\`)",
            r"(kill\s+-|pkill\s+|killall\s+)"
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"(\.\./|\.\.\\|\.\.%2f|\.\.%5c)",
            r"(%2e%2e%2f|%2e%2e%5c|%2e%2e/|%2e%2e\\)",
            r"(\\?\.\\.+/|\\?\.\\.+\\\\)",
            r"(/etc/passwd|/etc/shadow|/etc/hosts|/boot\.ini|/windows/)",
            r"(\.\.[\\/])",
            r"(\.\.[\\/].*[\\/])",
            r"%c0%af",
            r"%c1%9c"
        ]
        
        # File inclusion patterns
        self.file_inclusion_patterns = [
            r"(file://|ftp://|php://|zip://|jar://|dict://)",
            r"(\.(php|asp|jsp|py|rb|pl|cgi)(\?|&|#|$))",
            r"(data://|expect://|input://|phar://)",
            r"(glob://|rar://|ogg://|ssh2://)",
            r"(include\s*\(|require\s*\(|include_once\s*\(|require_once\s*\()"
        ]
    
    def validate_string(
        self, 
        value: Any, 
        field_name: str = "input",
        min_length: int = 0,
        max_length: int = 10000,
        allow_html: bool = False,
        allow_special_chars: bool = True,
        regex_pattern: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate and sanitize string input
        
        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML content
            allow_special_chars: Whether to allow special characters
            regex_pattern: Optional regex pattern to match
            
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        security_issues = []
        sanitized_value = value
        
        # Convert to string if not already
        if not isinstance(value, str):
            if value is None:
                sanitized_value = ""
            else:
                sanitized_value = str(value)
        
        original_value = sanitized_value
        
        # Length validation
        if len(sanitized_value) < min_length:
            errors.append(f"{field_name} must be at least {min_length} characters")
        
        if len(sanitized_value) > max_length:
            errors.append(f"{field_name} cannot exceed {max_length} characters")
            sanitized_value = sanitized_value[:max_length]
            warnings.append(f"{field_name} was truncated to {max_length} characters")
        
        # Security validation
        self._check_sql_injection(sanitized_value, field_name, security_issues)
        self._check_xss(sanitized_value, field_name, security_issues)
        self._check_command_injection(sanitized_value, field_name, security_issues)
        self._check_path_traversal(sanitized_value, field_name, security_issues)
        self._check_file_inclusion(sanitized_value, field_name, security_issues)
        
        # HTML handling
        if not allow_html and ('<' in sanitized_value or '>' in sanitized_value):
            sanitized_value = html.escape(sanitized_value)
            if sanitized_value != original_value:
                warnings.append(f"HTML characters in {field_name} were escaped")
        
        # Special characters handling
        if not allow_special_chars:
            dangerous_chars = ['<', '>', '"', "'", '&', '`', '$', ';', '|', '\\']
            for char in dangerous_chars:
                if char in sanitized_value:
                    sanitized_value = sanitized_value.replace(char, '')
                    warnings.append(f"Removed dangerous character '{char}' from {field_name}")
        
        # Regex pattern validation
        if regex_pattern:
            if not re.match(regex_pattern, sanitized_value, re.IGNORECASE):
                errors.append(f"{field_name} does not match required pattern")
        
        # Null byte detection
        if '\x00' in sanitized_value:
            security_issues.append(f"Null byte detected in {field_name}")
            sanitized_value = sanitized_value.replace('\x00', '')
        
        # Control character detection
        control_chars = [chr(i) for i in range(32) if i not in [9, 10, 13]]  # Allow tab, LF, CR
        for char in control_chars:
            if char in sanitized_value:
                security_issues.append(f"Control character detected in {field_name}")
                sanitized_value = sanitized_value.replace(char, '')
        
        is_valid = len(errors) == 0 and (self.security_level != SecurityLevel.STRICT or len(security_issues) == 0)
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=sanitized_value,
            errors=errors,
            warnings=warnings,
            security_issues=security_issues
        )
    
    def validate_email(self, email: Any, field_name: str = "email") -> ValidationResult:
        """Validate email address"""
        errors = []
        warnings = []
        security_issues = []
        sanitized_value = str(email).strip().lower() if email else ""
        
        # Basic format validation
        if not sanitized_value:
            errors.append(f"{field_name} is required")
        elif not validators.email(sanitized_value):
            errors.append(f"{field_name} is not a valid email address")
        else:
            # Additional security checks for email
            if len(sanitized_value) > 254:  # RFC 5321 limit
                errors.append(f"{field_name} is too long (max 254 characters)")
            
            # Check for suspicious patterns
            suspicious_patterns = ['+', '%', '..', '--', '@@']
            for pattern in suspicious_patterns:
                if pattern in sanitized_value:
                    warnings.append(f"Potentially suspicious pattern '{pattern}' in {field_name}")
            
            # Domain validation
            try:
                domain = sanitized_value.split('@')[1]
                if not validators.domain(domain):
                    errors.append(f"Invalid domain in {field_name}")
            except IndexError:
                errors.append(f"Invalid email format in {field_name}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, sanitized_value, errors, warnings, security_issues)
    
    def validate_url(self, url: Any, field_name: str = "url", 
                    allowed_schemes: Optional[List[str]] = None) -> ValidationResult:
        """Validate URL"""
        errors = []
        warnings = []
        security_issues = []
        sanitized_value = str(url).strip() if url else ""
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        if not sanitized_value:
            errors.append(f"{field_name} is required")
        elif not validators.url(sanitized_value):
            errors.append(f"{field_name} is not a valid URL")
        else:
            parsed = urllib.parse.urlparse(sanitized_value)
            
            # Scheme validation
            if parsed.scheme.lower() not in allowed_schemes:
                errors.append(f"{field_name} must use one of: {allowed_schemes}")
            
            # Check for dangerous schemes
            dangerous_schemes = ['javascript', 'data', 'file', 'ftp', 'vbscript']
            if parsed.scheme.lower() in dangerous_schemes:
                security_issues.append(f"Dangerous scheme '{parsed.scheme}' in {field_name}")
            
            # Check for IP addresses (may be suspicious)
            try:
                ipaddress.ip_address(parsed.hostname)
                warnings.append(f"IP address detected in {field_name} (may be suspicious)")
            except (ValueError, TypeError):
                pass  # Not an IP address, which is normal
            
            # Check for suspicious TLDs
            suspicious_tlds = ['.tk', '.ml', '.cf', '.ga', '.cc']
            for tld in suspicious_tlds:
                if parsed.hostname and parsed.hostname.endswith(tld):
                    warnings.append(f"Suspicious TLD '{tld}' in {field_name}")
        
        is_valid = len(errors) == 0 and (self.security_level != SecurityLevel.STRICT or len(security_issues) == 0)
        return ValidationResult(is_valid, sanitized_value, errors, warnings, security_issues)
    
    def validate_filename(self, filename: Any, field_name: str = "filename") -> ValidationResult:
        """Validate filename for security"""
        errors = []
        warnings = []
        security_issues = []
        sanitized_value = str(filename).strip() if filename else ""
        
        if not sanitized_value:
            errors.append(f"{field_name} is required")
        else:
            # Check for path traversal
            if '../' in sanitized_value or '..\\' in sanitized_value:
                security_issues.append(f"Path traversal attempt in {field_name}")
                sanitized_value = sanitized_value.replace('../', '').replace('..\\', '')
            
            # Check for dangerous characters
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
            for char in dangerous_chars:
                if char in sanitized_value:
                    security_issues.append(f"Dangerous character '{char}' in {field_name}")
                    sanitized_value = sanitized_value.replace(char, '_')
            
            # Check for reserved names (Windows)
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                            'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 
                            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 
                            'LPT7', 'LPT8', 'LPT9']
            
            name_part = sanitized_value.split('.')[0].upper()
            if name_part in reserved_names:
                security_issues.append(f"Reserved filename '{name_part}' in {field_name}")
                sanitized_value = f"safe_{sanitized_value}"
            
            # Length check
            if len(sanitized_value) > 255:
                errors.append(f"{field_name} too long (max 255 characters)")
                sanitized_value = sanitized_value[:255]
        
        is_valid = len(errors) == 0 and (self.security_level != SecurityLevel.STRICT or len(security_issues) == 0)
        return ValidationResult(is_valid, sanitized_value, errors, warnings, security_issues)
    
    def validate_integer(self, value: Any, field_name: str = "number",
                        min_value: Optional[int] = None,
                        max_value: Optional[int] = None) -> ValidationResult:
        """Validate integer input"""
        errors = []
        warnings = []
        security_issues = []
        sanitized_value = value
        
        try:
            if isinstance(value, str):
                sanitized_value = int(value.strip())
            elif not isinstance(value, int):
                sanitized_value = int(value)
        except (ValueError, TypeError):
            errors.append(f"{field_name} must be a valid integer")
            sanitized_value = 0
        
        if isinstance(sanitized_value, int):
            if min_value is not None and sanitized_value < min_value:
                errors.append(f"{field_name} must be at least {min_value}")
            
            if max_value is not None and sanitized_value > max_value:
                errors.append(f"{field_name} cannot exceed {max_value}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, sanitized_value, errors, warnings, security_issues)
    
    def _check_sql_injection(self, value: str, field_name: str, security_issues: List[str]):
        """Check for SQL injection patterns"""
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_issues.append(f"Potential SQL injection detected in {field_name}")
                break
    
    def _check_xss(self, value: str, field_name: str, security_issues: List[str]):
        """Check for XSS patterns"""
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_issues.append(f"Potential XSS attack detected in {field_name}")
                break
    
    def _check_command_injection(self, value: str, field_name: str, security_issues: List[str]):
        """Check for command injection patterns"""
        for pattern in self.command_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_issues.append(f"Potential command injection detected in {field_name}")
                break
    
    def _check_path_traversal(self, value: str, field_name: str, security_issues: List[str]):
        """Check for path traversal patterns"""
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_issues.append(f"Potential path traversal detected in {field_name}")
                break
    
    def _check_file_inclusion(self, value: str, field_name: str, security_issues: List[str]):
        """Check for file inclusion patterns"""
        for pattern in self.file_inclusion_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                security_issues.append(f"Potential file inclusion detected in {field_name}")
                break
    
    def validate_batch(self, data: Dict[str, Any], 
                      validation_rules: Dict[str, Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """
        Validate multiple fields in batch
        
        Args:
            data: Dictionary of field names to values
            validation_rules: Dictionary of field names to validation parameters
            
        Returns:
            Dictionary of field names to ValidationResult objects
        """
        results = {}
        
        for field_name, field_value in data.items():
            if field_name not in validation_rules:
                continue
            
            rules = validation_rules[field_name]
            validation_type = rules.get('type', 'string')
            
            if validation_type == 'string':
                result = self.validate_string(
                    field_value, 
                    field_name,
                    min_length=rules.get('min_length', 0),
                    max_length=rules.get('max_length', 10000),
                    allow_html=rules.get('allow_html', False),
                    allow_special_chars=rules.get('allow_special_chars', True),
                    regex_pattern=rules.get('regex_pattern')
                )
            elif validation_type == 'email':
                result = self.validate_email(field_value, field_name)
            elif validation_type == 'url':
                result = self.validate_url(
                    field_value, 
                    field_name,
                    allowed_schemes=rules.get('allowed_schemes')
                )
            elif validation_type == 'filename':
                result = self.validate_filename(field_value, field_name)
            elif validation_type == 'integer':
                result = self.validate_integer(
                    field_value,
                    field_name,
                    min_value=rules.get('min_value'),
                    max_value=rules.get('max_value')
                )
            else:
                result = ValidationResult(False, field_value, [f"Unknown validation type: {validation_type}"], [], [])
            
            results[field_name] = result
        
        return results


# Singleton instance for global use
validator = InputValidator()


# Convenience functions
def validate_string_input(value: Any, field_name: str = "input", **kwargs) -> ValidationResult:
    """Convenience function for string validation"""
    return validator.validate_string(value, field_name, **kwargs)


def validate_email_input(email: Any, field_name: str = "email") -> ValidationResult:
    """Convenience function for email validation"""
    return validator.validate_email(email, field_name)


def validate_url_input(url: Any, field_name: str = "url", **kwargs) -> ValidationResult:
    """Convenience function for URL validation"""
    return validator.validate_url(url, field_name, **kwargs)


def sanitize_filename(filename: Any) -> str:
    """Convenience function to safely sanitize filenames"""
    result = validator.validate_filename(filename)
    return result.sanitized_value


def is_safe_input(value: Any, field_name: str = "input") -> bool:
    """Quick check if input is safe"""
    result = validator.validate_string(value, field_name)
    return result.is_valid and len(result.security_issues) == 0


# Decorator for automatic input validation
def validate_inputs(validation_rules: Dict[str, Dict[str, Any]]):
    """
    Decorator to automatically validate function inputs
    
    Args:
        validation_rules: Dictionary mapping parameter names to validation rules
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import inspect
            
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate parameters
            validation_results = validator.validate_batch(bound_args.arguments, validation_rules)
            
            # Check for validation errors
            errors = []
            for field_name, result in validation_results.items():
                if not result.is_valid:
                    errors.extend([f"{field_name}: {error}" for error in result.errors])
                    errors.extend([f"{field_name}: {issue}" for issue in result.security_issues])
            
            if errors:
                raise ValidationError(f"Input validation failed: {'; '.join(errors)}")
            
            # Update arguments with sanitized values
            for field_name, result in validation_results.items():
                bound_args.arguments[field_name] = result.sanitized_value
            
            return func(*bound_args.args, **bound_args.kwargs)
        return wrapper
    return decorator