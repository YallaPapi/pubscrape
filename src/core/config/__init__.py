"""
Configuration Management System for VRSEN Agency Swarm

Modular configuration management with environment variable support,
validation, and runtime updates.
"""

from .base_config import ConfigFormat, ConfigManager
from .environment_config import (
    APIConfig,
    SearchConfig,
    CrawlingConfig,
    ProcessingConfig,
    ExportConfig,
    LoggingConfig,
    SystemConfig
)
from .validation import ConfigValidator
from .loaders import ConfigLoader
from .defaults import get_default_config

# Singleton instance
config_manager = ConfigManager()

__all__ = [
    'ConfigManager',
    'ConfigFormat',
    'APIConfig',
    'SearchConfig', 
    'CrawlingConfig',
    'ProcessingConfig',
    'ExportConfig',
    'LoggingConfig',
    'SystemConfig',
    'ConfigValidator',
    'ConfigLoader',
    'config_manager',
    'get_default_config'
]