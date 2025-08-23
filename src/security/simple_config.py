"""
Simple Secure Configuration Management (No External Dependencies)
SECURITY-FIX: Secure configuration without cryptography dependency

This provides a lightweight secure configuration system for testing.
"""

import os
import json
import re
from typing import Dict, Any, Optional
from pathlib import Path


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
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))


class SimpleConfigManager:
    """Simple secure configuration manager"""
    
    def __init__(self, config_path: str = "./config/config.json"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def create_default_config(self) -> Dict[str, Any]:
        """Create default secure configuration"""
        return {
            "application": {
                "app_name": "BotasaurusScraper",
                "version": "1.0.0",
                "debug": False,
                "log_level": "INFO",
                "max_memory_mb": 2048,
                "temp_dir": "./temp",
                "output_dir": "./output",
                "enable_metrics": True
            },
            "browser": {
                "chrome_binary_location": "",  # Auto-detect
                "headless": False,
                "viewport_width": 1920,
                "viewport_height": 1080,
                "user_data_dir": None,
                "disable_extensions": True,
                "disable_images": False,
                "disable_javascript": False,
                "enable_logging": False
            },
            "security": {
                "stealth_level": 3,
                "enable_proxy": False,
                "proxy_url": None,
                "proxy_username": None,
                "proxy_password": None,
                "rate_limit_delay": 1.0,
                "max_retries": 3,
                "request_timeout": 30,
                "user_agent_rotation": True,
                "fingerprint_randomization": True
            },
            "database": {
                "db_type": "sqlite",
                "db_path": "./secure_leads.db",
                "host": None,
                "port": None,
                "database": None,
                "username": None,
                "password": None,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 30
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_path.exists():
            default_config = self.create_default_config()
            self.save_config(default_config)
            return default_config
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Invalid configuration file: {e}")
            return self.create_default_config()
    
    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save configuration: {e}")


# Simple mock classes for testing
class BrowserConfig:
    def __init__(self, **kwargs):
        self.viewport_width = kwargs.get('viewport_width', 1920)
        self.viewport_height = kwargs.get('viewport_height', 1080)
        self.headless = kwargs.get('headless', False)
        self.disable_images = kwargs.get('disable_images', False)


class SecurityConfig:
    def __init__(self, **kwargs):
        self.stealth_level = kwargs.get('stealth_level', 3)
        self.rate_limit_delay = kwargs.get('rate_limit_delay', 1.0)
        self.max_retries = kwargs.get('max_retries', 3)
        self.request_timeout = kwargs.get('request_timeout', 30)
        self.enable_proxy = kwargs.get('enable_proxy', False)
        self.proxy_url = kwargs.get('proxy_url', None)
        
        # Validate stealth level
        if not (1 <= self.stealth_level <= 3):
            raise ValueError("stealth_level must be between 1 and 3")


class SecureConfigManager:
    """Alias for SimpleConfigManager for compatibility"""
    
    def __init__(self, config_path: str = "./config/config.json"):
        self.manager = SimpleConfigManager(config_path)
    
    def load_config(self) -> Dict[str, Any]:
        return self.manager.load_config()
    
    def get_browser_config(self) -> BrowserConfig:
        config = self.load_config()
        return BrowserConfig(**config.get('browser', {}))
    
    def get_security_config(self) -> SecurityConfig:
        config = self.load_config()
        return SecurityConfig(**config.get('security', {}))


# Global functions for compatibility
def get_browser_config() -> BrowserConfig:
    manager = SecureConfigManager()
    return manager.get_browser_config()


def get_security_config() -> SecurityConfig:
    manager = SecureConfigManager()
    return manager.get_security_config()