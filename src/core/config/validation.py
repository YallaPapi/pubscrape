"""
Configuration validation utilities.

Provides comprehensive validation for configuration objects.
"""

from typing import List, Tuple
from .environment_config import SystemConfig


class ConfigValidator:
    """Validates configuration objects for correctness and completeness."""
    
    def validate(self, config: SystemConfig) -> Tuple[bool, List[str]]:
        """
        Validate a system configuration.
        
        Args:
            config: SystemConfig object to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate API configuration
        errors.extend(self._validate_api_config(config.api))
        
        # Validate search configuration
        errors.extend(self._validate_search_config(config.search))
        
        # Validate crawling configuration
        errors.extend(self._validate_crawling_config(config.crawling))
        
        # Validate processing configuration
        errors.extend(self._validate_processing_config(config.processing))
        
        # Validate export configuration
        errors.extend(self._validate_export_config(config.export))
        
        # Validate logging configuration
        errors.extend(self._validate_logging_config(config.logging))
        
        # Validate system paths
        errors.extend(self._validate_system_paths(config))
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_api_config(self, api_config) -> List[str]:
        """Validate API configuration"""
        errors = []
        
        # Check for required API keys based on usage
        if not api_config.openai_api_key:
            errors.append("OpenAI API key is required for AI-powered features")
        
        # Validate model parameters
        if api_config.openai_temperature < 0 or api_config.openai_temperature > 2:
            errors.append("OpenAI temperature must be between 0 and 2")
        
        if api_config.openai_max_tokens < 1 or api_config.openai_max_tokens > 128000:
            errors.append("OpenAI max_tokens must be between 1 and 128000")
        
        return errors
    
    def _validate_search_config(self, search_config) -> List[str]:
        """Validate search configuration"""
        errors = []
        
        if search_config.max_pages_per_query < 1:
            errors.append("max_pages_per_query must be at least 1")
        
        if search_config.results_per_page < 1:
            errors.append("results_per_page must be at least 1")
        
        if search_config.timeout_seconds < 1:
            errors.append("Search timeout_seconds must be at least 1")
        
        if search_config.max_concurrent_searches < 1:
            errors.append("max_concurrent_searches must be at least 1")
        
        if search_config.rate_limit_rpm < 1:
            errors.append("rate_limit_rpm must be at least 1")
        
        if search_config.retry_attempts < 0:
            errors.append("retry_attempts cannot be negative")
        
        if search_config.retry_delay < 0:
            errors.append("retry_delay cannot be negative")
        
        if search_config.cache_ttl_seconds < 0:
            errors.append("cache_ttl_seconds cannot be negative")
        
        return errors
    
    def _validate_crawling_config(self, crawling_config) -> List[str]:
        """Validate crawling configuration"""
        errors = []
        
        if crawling_config.max_depth < 0:
            errors.append("max_depth cannot be negative")
        
        if crawling_config.max_pages_per_site < 1:
            errors.append("max_pages_per_site must be at least 1")
        
        if crawling_config.timeout_seconds < 1:
            errors.append("Crawling timeout_seconds must be at least 1")
        
        if crawling_config.concurrent_crawlers < 1:
            errors.append("concurrent_crawlers must be at least 1")
        
        if crawling_config.delay_between_requests < 0:
            errors.append("delay_between_requests cannot be negative")
        
        if crawling_config.max_redirects < 0:
            errors.append("max_redirects cannot be negative")
        
        if not crawling_config.user_agent:
            errors.append("user_agent cannot be empty")
        
        return errors
    
    def _validate_processing_config(self, processing_config) -> List[str]:
        """Validate processing configuration"""
        errors = []
        
        if processing_config.batch_size < 1:
            errors.append("batch_size must be at least 1")
        
        if processing_config.max_workers < 1:
            errors.append("max_workers must be at least 1")
        
        if processing_config.quality_threshold < 0 or processing_config.quality_threshold > 1:
            errors.append("quality_threshold must be between 0 and 1")
        
        valid_validation_levels = ["strict", "moderate", "lenient"]
        if processing_config.email_validation_level not in valid_validation_levels:
            errors.append(f"email_validation_level must be one of: {valid_validation_levels}")
        
        valid_classification_models = ["rule-based", "ml-based"]
        if processing_config.domain_classification_model not in valid_classification_models:
            errors.append(f"domain_classification_model must be one of: {valid_classification_models}")
        
        return errors
    
    def _validate_export_config(self, export_config) -> List[str]:
        """Validate export configuration"""
        errors = []
        
        if not export_config.output_directory:
            errors.append("output_directory cannot be empty")
        
        if not export_config.csv_delimiter:
            errors.append("csv_delimiter cannot be empty")
        
        if not export_config.csv_encoding:
            errors.append("csv_encoding cannot be empty")
        
        if not export_config.timestamp_format:
            errors.append("timestamp_format cannot be empty")
        
        if export_config.max_file_size_mb < 1:
            errors.append("max_file_size_mb must be at least 1")
        
        return errors
    
    def _validate_logging_config(self, logging_config) -> List[str]:
        """Validate logging configuration"""
        errors = []
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if logging_config.log_level not in valid_log_levels:
            errors.append(f"log_level must be one of: {valid_log_levels}")
        
        if not logging_config.log_directory:
            errors.append("log_directory cannot be empty")
        
        if not logging_config.log_format:
            errors.append("log_format cannot be empty")
        
        if logging_config.max_log_size_mb < 1:
            errors.append("max_log_size_mb must be at least 1")
        
        if logging_config.backup_count < 0:
            errors.append("backup_count cannot be negative")
        
        return errors
    
    def _validate_system_paths(self, config: SystemConfig) -> List[str]:
        """Validate system path configuration"""
        errors = []
        
        if not config.data_directory:
            errors.append("data_directory cannot be empty")
        
        if not config.cache_directory:
            errors.append("cache_directory cannot be empty")
        
        if not config.temp_directory:
            errors.append("temp_directory cannot be empty")
        
        return errors