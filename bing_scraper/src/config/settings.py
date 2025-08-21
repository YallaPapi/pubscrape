"""Settings configuration for Bing Scraper."""

import os
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Settings:
    """Main configuration settings for Bing Scraper."""
    
    # Proxy Configuration
    proxy_enabled: bool = False
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_type: str = "http"
    
    # Residential Proxy Pool
    residential_proxy_endpoint: Optional[str] = None
    residential_proxy_username: Optional[str] = None
    residential_proxy_password: Optional[str] = None
    
    # Rate Limiting
    max_requests_per_minute: int = 15
    max_concurrent_sessions: int = 2
    base_delay_seconds: float = 3.0
    max_retry_attempts: int = 3
    
    # Anti-Detection
    user_agent_rotation: bool = True
    block_images: bool = True
    block_css: bool = True
    block_js: bool = False
    headless_mode: bool = True
    
    # Output Configuration
    output_directory: str = "output"
    logs_directory: str = "logs"
    csv_filename_prefix: str = "bing_scraper_results"
    
    # Search Configuration
    max_pages_per_query: int = 5
    max_websites_to_visit: int = 100
    contact_page_keywords: List[str] = None
    
    # Email Validation
    min_email_confidence_score: float = 0.5
    exclude_domains: List[str] = None
    
    # Monitoring and Logging
    log_level: str = "INFO"
    enable_performance_monitoring: bool = True
    save_failed_requests: bool = True
    
    # Development Settings
    debug_mode: bool = False
    save_html_snapshots: bool = False
    screenshot_on_error: bool = False
    
    def __post_init__(self):
        """Initialize default values for lists."""
        if self.contact_page_keywords is None:
            self.contact_page_keywords = ["contact", "about", "team", "staff"]
        
        if self.exclude_domains is None:
            self.exclude_domains = [
                "example.com", "test.com", "gmail.com", 
                "yahoo.com", "hotmail.com"
            ]

def get_settings() -> Settings:
    """Load settings from environment variables."""
    
    # Helper function to parse boolean values
    def parse_bool(value: str, default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    # Helper function to parse list values
    def parse_list(value: str, default: List[str] = None) -> List[str]:
        if value is None:
            return default or []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    return Settings(
        # Proxy Configuration
        proxy_enabled=parse_bool(os.getenv('PROXY_ENABLED')),
        proxy_host=os.getenv('PROXY_HOST'),
        proxy_port=int(os.getenv('PROXY_PORT', 0)) if os.getenv('PROXY_PORT') else None,
        proxy_username=os.getenv('PROXY_USERNAME'),
        proxy_password=os.getenv('PROXY_PASSWORD'),
        proxy_type=os.getenv('PROXY_TYPE', 'http'),
        
        # Residential Proxy Pool
        residential_proxy_endpoint=os.getenv('RESIDENTIAL_PROXY_ENDPOINT'),
        residential_proxy_username=os.getenv('RESIDENTIAL_PROXY_USERNAME'),
        residential_proxy_password=os.getenv('RESIDENTIAL_PROXY_PASSWORD'),
        
        # Rate Limiting
        max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', 15)),
        max_concurrent_sessions=int(os.getenv('MAX_CONCURRENT_SESSIONS', 2)),
        base_delay_seconds=float(os.getenv('BASE_DELAY_SECONDS', 3.0)),
        max_retry_attempts=int(os.getenv('MAX_RETRY_ATTEMPTS', 3)),
        
        # Anti-Detection
        user_agent_rotation=parse_bool(os.getenv('USER_AGENT_ROTATION'), True),
        block_images=parse_bool(os.getenv('BLOCK_IMAGES'), True),
        block_css=parse_bool(os.getenv('BLOCK_CSS'), True),
        block_js=parse_bool(os.getenv('BLOCK_JS'), False),
        headless_mode=parse_bool(os.getenv('HEADLESS_MODE'), True),
        
        # Output Configuration
        output_directory=os.getenv('OUTPUT_DIRECTORY', 'output'),
        logs_directory=os.getenv('LOGS_DIRECTORY', 'logs'),
        csv_filename_prefix=os.getenv('CSV_FILENAME_PREFIX', 'bing_scraper_results'),
        
        # Search Configuration
        max_pages_per_query=int(os.getenv('MAX_PAGES_PER_QUERY', 5)),
        max_websites_to_visit=int(os.getenv('MAX_WEBSITES_TO_VISIT', 100)),
        contact_page_keywords=parse_list(
            os.getenv('CONTACT_PAGE_KEYWORDS'), 
            ['contact', 'about', 'team', 'staff']
        ),
        
        # Email Validation
        min_email_confidence_score=float(os.getenv('MIN_EMAIL_CONFIDENCE_SCORE', 0.5)),
        exclude_domains=parse_list(
            os.getenv('EXCLUDE_DOMAINS'),
            ['example.com', 'test.com', 'gmail.com', 'yahoo.com', 'hotmail.com']
        ),
        
        # Monitoring and Logging
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        enable_performance_monitoring=parse_bool(os.getenv('ENABLE_PERFORMANCE_MONITORING'), True),
        save_failed_requests=parse_bool(os.getenv('SAVE_FAILED_REQUESTS'), True),
        
        # Development Settings
        debug_mode=parse_bool(os.getenv('DEBUG_MODE')),
        save_html_snapshots=parse_bool(os.getenv('SAVE_HTML_SNAPSHOTS')),
        screenshot_on_error=parse_bool(os.getenv('SCREENSHOT_ON_ERROR'))
    )