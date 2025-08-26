"""
Configuration Management System for VRSEN Agency Swarm

Centralized configuration management with environment variable support,
validation, and runtime updates.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from dotenv import load_dotenv
import re
from urllib.parse import urlparse


def validate_api_key(key: str, key_name: str) -> bool:
    """Validate API key format and security"""
    if not key or len(key.strip()) == 0:
        return False
    
    # Check for placeholder values
    placeholder_patterns = [
        r'your_.*_api_key_here',
        r'insert.*key.*here',
        r'add.*key.*here',
        r'replace.*with.*key',
        r'example.*key'
    ]
    
    for pattern in placeholder_patterns:
        if re.match(pattern, key.lower()):
            raise ValueError(f"{key_name} appears to be a placeholder, not a real API key")
    
    # Basic format validation
    if len(key) < 10:
        raise ValueError(f"{key_name} appears to be too short to be valid")
    
    # Check for common test/dummy values
    dummy_values = ['test', 'dummy', 'fake', 'sample', 'example']
    if any(dummy in key.lower() for dummy in dummy_values):
        raise ValueError(f"{key_name} appears to be a test/dummy value")
    
    return True


def sanitize_config_value(value: Any) -> Any:
    """Sanitize configuration values to prevent injection attacks"""
    if isinstance(value, str):
        # Remove potentially dangerous characters
        dangerous_chars = ['$', '`', ';', '|', '&', '>', '<', '"', "'", '\\', '\n', '\r']
        sanitized = value
        for char in dangerous_chars:
            if char in sanitized:
                # Log security warning but don't fail
                logging.getLogger(__name__).warning(f"Removed potentially dangerous character '{char}' from config value")
                sanitized = sanitized.replace(char, '')
        return sanitized
    return value


# Load environment variables
load_dotenv()


class ConfigFormat(Enum):
    """Supported configuration file formats"""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class APIConfig:
    """Configuration for external API connections"""
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4000
    
    bing_api_key: Optional[str] = None
    bing_endpoint: str = "https://www.bing.com"
    
    google_api_key: Optional[str] = None
    google_cx: Optional[str] = None
    
    perplexity_api_key: Optional[str] = None
    
    def __post_init__(self):
        """Load and validate API keys from environment if not provided"""
        # Load from environment with validation
        env_keys = {
            'openai_api_key': 'OPENAI_API_KEY',
            'bing_api_key': 'BING_API_KEY', 
            'google_api_key': 'GOOGLE_API_KEY',
            'perplexity_api_key': 'PERPLEXITY_API_KEY'
        }
        
        for attr, env_var in env_keys.items():
            current_value = getattr(self, attr)
            env_value = os.getenv(env_var)
            
            if not current_value and env_value:
                try:
                    if validate_api_key(env_value, env_var):
                        setattr(self, attr, env_value)
                except ValueError as e:
                    logging.getLogger(__name__).warning(f"API key validation failed for {env_var}: {e}")
        
        # Load non-sensitive environment variables
        self.google_cx = self.google_cx or os.getenv("GOOGLE_CX")


@dataclass
class SearchConfig:
    """Configuration for search operations"""
    max_pages_per_query: int = 5
    results_per_page: int = 10
    timeout_seconds: int = 30
    max_concurrent_searches: int = 2
    rate_limit_rpm: int = 12
    retry_attempts: int = 3
    retry_delay: float = 2.0
    use_stealth_mode: bool = True
    cache_results: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class CrawlingConfig:
    """Configuration for web crawling operations"""
    max_depth: int = 2
    max_pages_per_site: int = 10
    timeout_seconds: int = 20
    respect_robots_txt: bool = True
    user_agent: str = "VRSEN-Bot/1.0 (Lead Generation)"
    concurrent_crawlers: int = 3
    delay_between_requests: float = 1.0
    follow_redirects: bool = True
    max_redirects: int = 5


@dataclass
class ProcessingConfig:
    """Configuration for data processing operations"""
    batch_size: int = 100
    max_workers: int = 4
    deduplication_enabled: bool = True
    validation_enabled: bool = True
    quality_threshold: float = 0.7
    email_validation_level: str = "strict"  # strict, moderate, lenient
    domain_classification_model: str = "rule-based"  # rule-based, ml-based


@dataclass
class ExportConfig:
    """Configuration for data export operations"""
    output_directory: str = "output"
    csv_delimiter: str = ","
    csv_encoding: str = "utf-8"
    include_metadata: bool = True
    compress_output: bool = False
    timestamp_format: str = "%Y%m%d_%H%M%S"
    max_file_size_mb: int = 100
    split_large_files: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging"""
    log_level: str = "INFO"
    log_directory: str = "logs"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_log_size_mb: int = 50
    backup_count: int = 5
    enable_console_logging: bool = True
    enable_file_logging: bool = True
    separate_error_log: bool = True


@dataclass
class SystemConfig:
    """Overall system configuration"""
    api: APIConfig = field(default_factory=APIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    crawling: CrawlingConfig = field(default_factory=CrawlingConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Runtime settings
    debug_mode: bool = False
    dry_run: bool = False
    profile_performance: bool = False
    enable_metrics: bool = True
    
    # Paths
    data_directory: str = "data"
    cache_directory: str = "cache"
    temp_directory: str = "temp"


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
            self._config = SystemConfig()
            self._config_file_path: Optional[Path] = None
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
        self._load_from_environment()
    
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
            
            # Determine format
            if path.suffix in ['.yaml', '.yml']:
                return self._load_yaml(path)
            elif path.suffix == '.json':
                return self._load_json(path)
            elif path.suffix == '.env':
                return self._load_env(path)
            else:
                self.logger.error(f"Unsupported configuration format: {path.suffix}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {file_path}: {e}")
            return False
    
    def _load_yaml(self, path: Path) -> bool:
        """Load configuration from YAML file"""
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            
            self._update_config_from_dict(data)
            self.logger.info(f"Configuration loaded from {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load YAML configuration: {e}")
            return False
    
    def _load_json(self, path: Path) -> bool:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self._update_config_from_dict(data)
            self.logger.info(f"Configuration loaded from {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load JSON configuration: {e}")
            return False
    
    def _load_env(self, path: Path) -> bool:
        """Load configuration from .env file"""
        try:
            load_dotenv(path)
            self._load_from_environment()
            self.logger.info(f"Environment variables loaded from {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load .env file: {e}")
            return False
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # API keys
        if os.getenv("OPENAI_API_KEY"):
            self._config.api.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Search settings
        if os.getenv("MAX_PAGES_PER_QUERY"):
            self._config.search.max_pages_per_query = int(os.getenv("MAX_PAGES_PER_QUERY"))
        
        if os.getenv("RATE_LIMIT_RPM"):
            self._config.search.rate_limit_rpm = int(os.getenv("RATE_LIMIT_RPM"))
        
        # System settings
        if os.getenv("DEBUG_MODE"):
            self._config.debug_mode = os.getenv("DEBUG_MODE").lower() == "true"
        
        if os.getenv("LOG_LEVEL"):
            self._config.logging.log_level = os.getenv("LOG_LEVEL")
    
    def _update_config_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary"""
        if "api" in data:
            self._update_dataclass(self._config.api, data["api"])
        
        if "search" in data:
            self._update_dataclass(self._config.search, data["search"])
        
        if "crawling" in data:
            self._update_dataclass(self._config.crawling, data["crawling"])
        
        if "processing" in data:
            self._update_dataclass(self._config.processing, data["processing"])
        
        if "export" in data:
            self._update_dataclass(self._config.export, data["export"])
        
        if "logging" in data:
            self._update_dataclass(self._config.logging, data["logging"])
        
        # Update root level settings
        for key in ["debug_mode", "dry_run", "profile_performance", "enable_metrics",
                    "data_directory", "cache_directory", "temp_directory"]:
            if key in data:
                setattr(self._config, key, data[key])
    
    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """Update dataclass fields from dictionary"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
    
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
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate API keys if present
        api_keys = {
            'OpenAI': self._config.api.openai_api_key,
            'Bing': self._config.api.bing_api_key,
            'Google': self._config.api.google_api_key,
            'Perplexity': self._config.api.perplexity_api_key
        }
        
        for service, key in api_keys.items():
            if key:
                try:
                    validate_api_key(key, f"{service} API key")
                except ValueError as e:
                    errors.append(str(e))
        
        # Check if at least one API key is configured
        if not any(api_keys.values()):
            errors.append("At least one API key must be configured")
        
        # Validate numeric ranges
        if self._config.search.max_pages_per_query < 1:
            errors.append("max_pages_per_query must be at least 1")
        
        if self._config.search.rate_limit_rpm < 1:
            errors.append("rate_limit_rpm must be at least 1")
        
        if self._config.processing.batch_size < 1:
            errors.append("batch_size must be at least 1")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self._config.logging.log_level not in valid_log_levels:
            errors.append(f"Invalid log level: {self._config.logging.log_level}")
        
        is_valid = len(errors) == 0
        
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
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dictionary
            config_dict = self._config_to_dict()
            
            # Save based on format
            if format == ConfigFormat.YAML or path.suffix in ['.yaml', '.yml']:
                with open(path, 'w') as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            elif format == ConfigFormat.JSON or path.suffix == '.json':
                with open(path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
            else:
                self.logger.error(f"Unsupported save format: {format}")
                return False
            
            self.logger.info(f"Configuration saved to {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "api": asdict(self._config.api),
            "search": asdict(self._config.search),
            "crawling": asdict(self._config.crawling),
            "processing": asdict(self._config.processing),
            "export": asdict(self._config.export),
            "logging": asdict(self._config.logging),
            "debug_mode": self._config.debug_mode,
            "dry_run": self._config.dry_run,
            "profile_performance": self._config.profile_performance,
            "enable_metrics": self._config.enable_metrics,
            "data_directory": self._config.data_directory,
            "cache_directory": self._config.cache_directory,
            "temp_directory": self._config.temp_directory
        }
    
    def reset(self):
        """Reset configuration to defaults"""
        self._config = SystemConfig()
        self._load_default_configuration()
        self.logger.info("Configuration reset to defaults")
    
    @property
    def config(self) -> SystemConfig:
        """Get current configuration object"""
        return self._config
    
    @property
    def api(self) -> APIConfig:
        """Get API configuration"""
        return self._config.api
    
    @property
    def search(self) -> SearchConfig:
        """Get search configuration"""
        return self._config.search
    
    @property
    def crawling(self) -> CrawlingConfig:
        """Get crawling configuration"""
        return self._config.crawling
    
    @property
    def processing(self) -> ProcessingConfig:
        """Get processing configuration"""
        return self._config.processing
    
    @property
    def export(self) -> ExportConfig:
        """Get export configuration"""
        return self._config.export
    
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration"""
        return self._config.logging


# Singleton instance
config_manager = ConfigManager()