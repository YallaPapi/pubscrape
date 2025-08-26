"""
Base configuration management class.

Handles configuration lifecycle, property access, and persistence.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import asdict

from .environment_config import SystemConfig
from .validation import ConfigValidator
from .loaders import ConfigLoader
from .defaults import get_default_config


class ConfigFormat(Enum):
    """Supported configuration file formats"""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


class ConfigManager:
    """
    Centralized configuration manager for the VRSEN Agency Swarm.
    
    Features:
    - Load configuration from multiple sources (files, environment, runtime)
    - Configuration validation and type checking
    - Runtime configuration updates
    - Configuration persistence
    - Environment-specific configurations
    """
    
    _instance = None
    _config: SystemConfig = None
    
    def __new__(cls):
        """Singleton pattern for configuration manager"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager"""
        if self._config is None:
            self.logger = self._setup_logging()
            self._config = get_default_config()
            self._config_file_path: Optional[Path] = None
            self._loader = ConfigLoader()
            self._validator = ConfigValidator()
            self._load_default_configuration()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for config manager"""
        logger = logging.getLogger("vrsen.config_manager")
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - ConfigManager - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_default_configuration(self):
        """Load default configuration from environment and files"""
        # Try to load from default config file locations
        config_locations = [
            Path("config.yaml"),
            Path("config.json"),
            Path("configs/config.yaml"),
            Path("configs/config.json"),
            Path(".env")
        ]
        
        for config_path in config_locations:
            if config_path.exists():
                self.logger.info(f"Loading configuration from {config_path}")
                self.load_from_file(str(config_path))
                break
        
        # Override with environment variables
        self._loader.load_from_environment(self._config)
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"Configuration file not found: {file_path}")
                return False
            
            self._config_file_path = path
            
            # Use loader to load configuration
            loaded_config = self._loader.load_from_file(path, self._config)
            if loaded_config:
                self._config = loaded_config
                self.logger.info(f"Configuration loaded from {path}")
                return True
            
            return False
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {file_path}: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation path.
        
        Args:
            key_path: Dot-notation path (e.g., "api.openai_api_key")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                if hasattr(value, key):
                    value = getattr(value, key)
                else:
                    return default
            
            return value
            
        except Exception as e:
            self.logger.error(f"Error getting config value for {key_path}: {e}")
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        Set configuration value by dot-notation path.
        
        Args:
            key_path: Dot-notation path (e.g., "api.openai_api_key")
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            keys = key_path.split('.')
            obj = self._config
            
            # Navigate to parent object
            for key in keys[:-1]:
                if hasattr(obj, key):
                    obj = getattr(obj, key)
                else:
                    self.logger.error(f"Invalid configuration path: {key_path}")
                    return False
            
            # Set the value
            if hasattr(obj, keys[-1]):
                setattr(obj, keys[-1], value)
                self.logger.debug(f"Configuration updated: {key_path} = {value}")
                return True
            else:
                self.logger.error(f"Invalid configuration key: {keys[-1]}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting config value for {key_path}: {e}")
            return False
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        is_valid, errors = self._validator.validate(self._config)
        
        if not is_valid:
            self.logger.error(f"Configuration validation failed: {errors}")
        
        return is_valid, errors
    
    def save(self, file_path: Optional[str] = None, format: ConfigFormat = ConfigFormat.YAML) -> bool:
        """
        Save current configuration to file.
        
        Args:
            file_path: Path to save configuration (uses original path if None)
            format: Format to save in
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path is None:
                if self._config_file_path:
                    file_path = str(self._config_file_path)
                else:
                    file_path = "config.yaml"
            
            path = Path(file_path)
            
            # Use loader to save configuration
            success = self._loader.save_to_file(self._config, path, format)
            
            if success:
                self.logger.info(f"Configuration saved to {path}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reset(self):
        """Reset configuration to defaults"""
        self._config = get_default_config()
        self._load_default_configuration()
        self.logger.info("Configuration reset to defaults")
    
    @property
    def config(self) -> SystemConfig:
        """Get current configuration object"""
        return self._config
    
    @property
    def api(self):
        """Get API configuration"""
        return self._config.api
    
    @property
    def search(self):
        """Get search configuration"""
        return self._config.search
    
    @property
    def crawling(self):
        """Get crawling configuration"""
        return self._config.crawling
    
    @property
    def processing(self):
        """Get processing configuration"""
        return self._config.processing
    
    @property
    def export(self):
        """Get export configuration"""
        return self._config.export
    
    @property
    def logging(self):
        """Get logging configuration"""
        return self._config.logging