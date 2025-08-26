"""
Environment-specific configuration dataclasses.

Defines configuration structures for different components of the system.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


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
        """Load API keys from environment if not provided"""
        self.openai_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.bing_api_key = self.bing_api_key or os.getenv("BING_API_KEY")
        self.google_api_key = self.google_api_key or os.getenv("GOOGLE_API_KEY")
        self.google_cx = self.google_cx or os.getenv("GOOGLE_CX")
        self.perplexity_api_key = self.perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")


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