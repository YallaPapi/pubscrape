"""
Secure Configuration Management System
SECURITY-FIX: Replaces hardcoded environment variables with secure config management

This module provides secure configuration management that:
- Uses config.json for settings instead of hardcoded environment variables
- Validates all inputs with strict type checking
- Never exposes sensitive data in environment variables
- Provides safe defaults for all configuration options
- Implements configuration encryption for sensitive values
"""

import os
import json
import hashlib
import secrets
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

# Configure secure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Secure browser configuration with validation"""
    chrome_binary_location: str = ""  # Auto-detect system Chrome
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_data_dir: Optional[str] = None
    disable_extensions: bool = True
    disable_images: bool = False
    disable_javascript: bool = False
    enable_logging: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate()
    
    def _validate(self):
        """Validate browser configuration"""
        # Validate viewport dimensions
        if not (800 <= self.viewport_width <= 3840):
            raise ValueError("viewport_width must be between 800 and 3840")
        if not (600 <= self.viewport_height <= 2160):
            raise ValueError("viewport_height must be between 600 and 2160")
        
        # Validate chrome binary path if provided
        if self.chrome_binary_location and not os.path.exists(self.chrome_binary_location):
            logger.warning(f"Chrome binary path does not exist: {self.chrome_binary_location}")
        
        # Validate user data directory
        if self.user_data_dir:
            try:
                Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot create user_data_dir: {e}")


@dataclass  
class SecurityConfig:
    """Security configuration with strict validation"""
    stealth_level: int = 3
    enable_proxy: bool = False
    proxy_url: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    request_timeout: int = 30
    user_agent_rotation: bool = True
    fingerprint_randomization: bool = True
    
    def __post_init__(self):
        """Validate security configuration"""
        self._validate()
    
    def _validate(self):
        """Validate security configuration"""
        if not (1 <= self.stealth_level <= 3):
            raise ValueError("stealth_level must be between 1 and 3")
        
        if not (0.1 <= self.rate_limit_delay <= 60.0):
            raise ValueError("rate_limit_delay must be between 0.1 and 60.0 seconds")
        
        if not (1 <= self.max_retries <= 10):
            raise ValueError("max_retries must be between 1 and 10")
            
        if not (5 <= self.request_timeout <= 300):
            raise ValueError("request_timeout must be between 5 and 300 seconds")
        
        # Validate proxy configuration
        if self.enable_proxy and not self.proxy_url:
            raise ValueError("proxy_url is required when enable_proxy is True")
        
        if self.proxy_url and not self.proxy_url.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            raise ValueError("proxy_url must start with http://, https://, socks4://, or socks5://")


@dataclass
class DatabaseConfig:
    """Secure database configuration"""
    db_type: str = "sqlite"
    db_path: str = "./secure_leads.db"
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    
    def __post_init__(self):
        """Validate database configuration"""
        self._validate()
    
    def _validate(self):
        """Validate database configuration"""
        valid_db_types = ["sqlite", "postgresql", "mysql"]
        if self.db_type not in valid_db_types:
            raise ValueError(f"db_type must be one of: {valid_db_types}")
        
        if self.db_type == "sqlite":
            # Validate SQLite path
            db_path = Path(self.db_path)
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot create database directory: {e}")
        else:
            # Validate required fields for remote databases
            if not all([self.host, self.port, self.database, self.username]):
                raise ValueError("host, port, database, and username are required for remote databases")
        
        # Validate connection pool settings
        if not (1 <= self.pool_size <= 100):
            raise ValueError("pool_size must be between 1 and 100")
        if not (0 <= self.max_overflow <= 100):
            raise ValueError("max_overflow must be between 0 and 100")
        if not (1 <= self.pool_timeout <= 300):
            raise ValueError("pool_timeout must be between 1 and 300 seconds")
    
    def get_connection_string(self) -> str:
        """Get secure database connection string"""
        if self.db_type == "sqlite":
            return f"sqlite:///{self.db_path}"
        elif self.db_type == "postgresql":
            password_part = f":{self.password}" if self.password else ""
            return f"postgresql://{self.username}{password_part}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "mysql":
            password_part = f":{self.password}" if self.password else ""
            return f"mysql://{self.username}{password_part}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")


@dataclass
class ApplicationConfig:
    """Main application configuration"""
    app_name: str = "BotasaurusScraper"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    max_memory_mb: int = 2048
    temp_dir: str = "./temp"
    output_dir: str = "./output"
    enable_metrics: bool = True
    
    def __post_init__(self):
        """Validate application configuration"""
        self._validate()
    
    def _validate(self):
        """Validate application configuration"""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"log_level must be one of: {valid_log_levels}")
        
        if not (512 <= self.max_memory_mb <= 16384):
            raise ValueError("max_memory_mb must be between 512 and 16384")
        
        # Create directories if they don't exist
        for dir_path in [self.temp_dir, self.output_dir]:
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot create directory {dir_path}: {e}")


class SecureConfigManager:
    """Secure configuration manager with encryption and validation"""
    
    def __init__(self, config_path: str = "./config/secure_config.json"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self._encryption_key: Optional[bytes] = None
        self._config_cache: Optional[Dict[str, Any]] = None
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption key
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption for sensitive configuration values"""
        key_file = self.config_dir / ".config_key"
        
        if key_file.exists():
            # Load existing key
            with open(key_file, 'rb') as f:
                self._encryption_key = f.read()
        else:
            # Generate new key
            password = os.environ.get('CONFIG_PASSWORD', secrets.token_urlsafe(32)).encode()
            salt = secrets.token_bytes(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Save key securely
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod
            
            self._encryption_key = key
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt sensitive configuration value"""
        if not self._encryption_key:
            raise ValueError("Encryption key not initialized")
        
        f = Fernet(self._encryption_key)
        encrypted_value = f.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted_value).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt sensitive configuration value"""
        if not self._encryption_key:
            raise ValueError("Encryption key not initialized")
        
        try:
            f = Fernet(self._encryption_key)
            decoded_value = base64.urlsafe_b64decode(encrypted_value.encode())
            return f.decrypt(decoded_value).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt configuration value: {e}")
    
    def create_default_config(self) -> Dict[str, Any]:
        """Create default secure configuration"""
        return {
            "application": asdict(ApplicationConfig()),
            "browser": asdict(BrowserConfig()),
            "security": asdict(SecurityConfig()),
            "database": asdict(DatabaseConfig()),
            "encrypted_fields": []  # List of fields that are encrypted
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load and validate configuration from file"""
        if self._config_cache:
            return self._config_cache
        
        if not self.config_path.exists():
            logger.info("Configuration file not found, creating default config")
            default_config = self.create_default_config()
            self.save_config(default_config)
            return default_config
        
        try:
            with open(self.config_path, 'r') as f:
                raw_config = json.load(f)
            
            # Decrypt sensitive fields
            encrypted_fields = raw_config.get('encrypted_fields', [])
            for field_path in encrypted_fields:
                self._decrypt_field(raw_config, field_path)
            
            # Validate configuration
            validated_config = self._validate_config(raw_config)
            self._config_cache = validated_config
            
            return validated_config
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid configuration file: {e}")
            raise ValueError(f"Configuration file is invalid: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file with encryption for sensitive data"""
        # Create a copy for modification
        save_config = json.loads(json.dumps(config))
        
        # Identify and encrypt sensitive fields
        sensitive_fields = [
            "database.password",
            "security.proxy_password",
        ]
        
        encrypted_fields = []
        for field_path in sensitive_fields:
            if self._has_field(save_config, field_path):
                value = self._get_field(save_config, field_path)
                if value:
                    encrypted_value = self._encrypt_value(str(value))
                    self._set_field(save_config, field_path, encrypted_value)
                    encrypted_fields.append(field_path)
        
        save_config['encrypted_fields'] = encrypted_fields
        
        # Save to file with backup
        backup_path = self.config_path.with_suffix('.json.bak')
        if self.config_path.exists():
            self.config_path.replace(backup_path)
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(save_config, f, indent=2)
            
            # Set restrictive permissions
            try:
                os.chmod(self.config_path, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod
                
            logger.info(f"Configuration saved to {self.config_path}")
            self._config_cache = None  # Clear cache
            
        except Exception as e:
            # Restore backup if save failed
            if backup_path.exists():
                backup_path.replace(self.config_path)
            raise ValueError(f"Failed to save configuration: {e}")
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration structure and values"""
        try:
            # Validate each section
            app_config = ApplicationConfig(**config.get('application', {}))
            browser_config = BrowserConfig(**config.get('browser', {}))
            security_config = SecurityConfig(**config.get('security', {}))
            database_config = DatabaseConfig(**config.get('database', {}))
            
            return {
                "application": asdict(app_config),
                "browser": asdict(browser_config),
                "security": asdict(security_config),
                "database": asdict(database_config),
                "encrypted_fields": config.get('encrypted_fields', [])
            }
        except (TypeError, ValueError) as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _has_field(self, config: Dict[str, Any], field_path: str) -> bool:
        """Check if a nested field exists in configuration"""
        keys = field_path.split('.')
        current = config
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        
        return True
    
    def _get_field(self, config: Dict[str, Any], field_path: str) -> Any:
        """Get a nested field from configuration"""
        keys = field_path.split('.')
        current = config
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        
        return current
    
    def _set_field(self, config: Dict[str, Any], field_path: str, value: Any):
        """Set a nested field in configuration"""
        keys = field_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _decrypt_field(self, config: Dict[str, Any], field_path: str):
        """Decrypt a specific field in configuration"""
        encrypted_value = self._get_field(config, field_path)
        if encrypted_value:
            decrypted_value = self._decrypt_value(encrypted_value)
            self._set_field(config, field_path, decrypted_value)
    
    def get_browser_config(self) -> BrowserConfig:
        """Get validated browser configuration"""
        config = self.load_config()
        return BrowserConfig(**config['browser'])
    
    def get_security_config(self) -> SecurityConfig:
        """Get validated security configuration"""
        config = self.load_config()
        return SecurityConfig(**config['security'])
    
    def get_database_config(self) -> DatabaseConfig:
        """Get validated database configuration"""
        config = self.load_config()
        return DatabaseConfig(**config['database'])
    
    def get_application_config(self) -> ApplicationConfig:
        """Get validated application configuration"""
        config = self.load_config()
        return ApplicationConfig(**config['application'])
    
    def update_config(self, section: str, updates: Dict[str, Any]):
        """Update a specific configuration section"""
        config = self.load_config()
        
        if section not in config:
            raise ValueError(f"Unknown configuration section: {section}")
        
        # Merge updates
        config[section].update(updates)
        
        # Validate and save
        validated_config = self._validate_config(config)
        self.save_config(validated_config)
        
        logger.info(f"Updated configuration section: {section}")


# Input validation and sanitization utilities
class InputValidator:
    """Input validation and sanitization utilities"""
    
    @staticmethod
    def sanitize_string(value: Any, max_length: int = 1000, allow_none: bool = True) -> Optional[str]:
        """Sanitize string input"""
        if value is None:
            return None if allow_none else ""
        
        if not isinstance(value, str):
            value = str(value)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        if not url:
            return False
        
        # Basic URL validation
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None) -> int:
        """Validate and convert to integer"""
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                raise ValueError(f"Value {int_val} is below minimum {min_val}")
            
            if max_val is not None and int_val > max_val:
                raise ValueError(f"Value {int_val} is above maximum {max_val}")
            
            return int_val
        except (ValueError, TypeError):
            raise ValueError(f"Invalid integer value: {value}")
    
    @staticmethod
    def validate_float(value: Any, min_val: float = None, max_val: float = None) -> float:
        """Validate and convert to float"""
        try:
            float_val = float(value)
            
            if min_val is not None and float_val < min_val:
                raise ValueError(f"Value {float_val} is below minimum {min_val}")
            
            if max_val is not None and float_val > max_val:
                raise ValueError(f"Value {float_val} is above maximum {max_val}")
            
            return float_val
        except (ValueError, TypeError):
            raise ValueError(f"Invalid float value: {value}")


# Global configuration manager instance
_config_manager: Optional[SecureConfigManager] = None

def get_config_manager() -> SecureConfigManager:
    """Get or create global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager


def get_browser_config() -> BrowserConfig:
    """Get browser configuration"""
    return get_config_manager().get_browser_config()


def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return get_config_manager().get_security_config()


def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config_manager().get_database_config()


def get_application_config() -> ApplicationConfig:
    """Get application configuration"""
    return get_config_manager().get_application_config()


if __name__ == "__main__":
    # Test the secure configuration system
    print("Testing Secure Configuration Management System")
    print("=" * 60)
    
    # Create test configuration manager
    test_config_path = "./test_config.json"
    manager = SecureConfigManager(test_config_path)
    
    # Load default configuration
    config = manager.load_config()
    print(f"Loaded configuration with {len(config)} sections")
    
    # Test configuration validation
    try:
        browser_config = manager.get_browser_config()
        print(f"Browser config: {browser_config.viewport_width}x{browser_config.viewport_height}")
        
        security_config = manager.get_security_config()
        print(f"Security config: stealth level {security_config.stealth_level}")
        
        database_config = manager.get_database_config()
        print(f"Database config: {database_config.db_type} at {database_config.db_path}")
        
    except ValueError as e:
        print(f"Configuration validation error: {e}")
    
    # Test input validation
    validator = InputValidator()
    
    # Test string sanitization
    dirty_string = "Hello\x00World\x01"
    clean_string = validator.sanitize_string(dirty_string)
    print(f"Sanitized: '{dirty_string}' -> '{clean_string}'")
    
    # Test URL validation
    test_urls = ["https://example.com", "http://localhost:8080", "invalid-url"]
    for url in test_urls:
        is_valid = validator.validate_url(url)
        print(f"URL '{url}' is valid: {is_valid}")
    
    # Clean up test file
    try:
        os.unlink(test_config_path)
    except OSError:
        pass
    
    print("\nSecure configuration system test complete!")