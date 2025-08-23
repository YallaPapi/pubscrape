# Configuration Reference - PubScrape Infinite Scroll Scraper System

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [YAML Configuration](#yaml-configuration)
3. [JSON Configuration](#json-configuration)
4. [Runtime Configuration](#runtime-configuration)
5. [Domain-Specific Overrides](#domain-specific-overrides)
6. [Agent Configuration](#agent-configuration)
7. [Performance Tuning](#performance-tuning)
8. [Security Configuration](#security-configuration)

## Environment Variables

### Required Variables

```bash
# OpenAI API Key (Required)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### Search Configuration

```bash
# Search Engine Settings
MAX_PAGES_PER_QUERY=5                    # Maximum pages to scrape per query (1-10)
RESULTS_PER_PAGE=10                      # Results per search page (5-20)
RATE_LIMIT_RPM=12                        # Requests per minute (1-60)
TIMEOUT_SECONDS=30                       # Request timeout in seconds (10-60)
MAX_CONCURRENT_SEARCHES=2                # Concurrent search operations (1-5)
RETRY_ATTEMPTS=3                         # Number of retry attempts (1-10)
RETRY_DELAY=2.0                          # Base retry delay in seconds (0.5-10.0)

# Search Behavior
USE_STEALTH_MODE=true                    # Enable anti-detection features
CACHE_RESULTS=true                       # Cache search results
CACHE_TTL_SECONDS=3600                   # Cache time-to-live (300-86400)
```

### Browser Configuration

```bash
# Browser Settings
BROWSER_MODE=headless                    # headless, headful, auto
BROWSER_TIMEOUT=30                       # Browser timeout (10-120)
BROWSER_WINDOW_WIDTH=1920               # Browser window width
BROWSER_WINDOW_HEIGHT=1080              # Browser window height
BROWSER_MAX_RETRIES=3                   # Browser operation retries

# Resource Blocking
BLOCK_IMAGES=true                       # Block image loading
BLOCK_STYLESHEETS=true                  # Block CSS loading
BLOCK_FONTS=true                        # Block font loading
BLOCK_MEDIA=true                        # Block video/audio
```

### Anti-Detection Settings

```bash
# Proxy Configuration
ENABLE_PROXY_ROTATION=false             # Enable proxy rotation
PROXY_LIST_URL=                         # URL to proxy list
PROXY_USERNAME=                         # Proxy authentication username
PROXY_PASSWORD=                         # Proxy authentication password

# User Agent Management
ROTATE_USER_AGENTS=true                 # Rotate user agents
PREFER_CHROME_AGENTS=true              # Prefer Chrome user agents
DESKTOP_AGENTS_ONLY=true               # Use only desktop user agents

# Delay Management
BASE_DELAY_SECONDS=2.0                 # Base delay between requests
RANDOM_DELAY_FACTOR=0.5                # Random delay multiplier (0.1-2.0)
HUMAN_LIKE_DELAYS=true                 # Use human-like delay patterns
```

### Data Processing

```bash
# Processing Settings
BATCH_SIZE=100                          # Processing batch size (10-500)
MAX_WORKERS=4                           # Maximum worker threads (1-8)
ENABLE_DEDUPLICATION=true              # Enable duplicate removal
ENABLE_VALIDATION=true                 # Enable data validation
QUALITY_THRESHOLD=0.7                  # Quality score threshold (0.0-1.0)

# Email Validation
EMAIL_VALIDATION_LEVEL=strict          # strict, moderate, lenient
VALIDATE_EMAIL_DOMAINS=true            # Validate email domain existence
CHECK_DISPOSABLE_EMAILS=true           # Filter disposable email addresses

# Phone Validation
PHONE_VALIDATION_ENABLED=true          # Enable phone validation
PHONE_FORMAT_COUNTRY=US                # Default phone format country
NORMALIZE_PHONE_NUMBERS=true           # Normalize phone number format
```

### Export Configuration

```bash
# Export Settings
OUTPUT_DIRECTORY=output                 # Output directory path
CSV_DELIMITER=,                         # CSV field delimiter
CSV_ENCODING=utf-8                      # CSV file encoding
INCLUDE_METADATA=true                   # Include metadata in exports
COMPRESS_OUTPUT=false                   # Compress output files
TIMESTAMP_FORMAT=%Y%m%d_%H%M%S         # Filename timestamp format
MAX_FILE_SIZE_MB=100                   # Maximum file size before splitting
SPLIT_LARGE_FILES=true                 # Split large output files
```

### Logging Configuration

```bash
# Logging Settings
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIRECTORY=logs                      # Log directory path
ENABLE_CONSOLE_LOGGING=true            # Enable console output
ENABLE_FILE_LOGGING=true               # Enable file logging
SEPARATE_ERROR_LOG=true                # Separate error log file
MAX_LOG_SIZE_MB=50                     # Maximum log file size
LOG_BACKUP_COUNT=5                     # Number of log backups to keep
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### System Settings

```bash
# System Configuration
DEBUG_MODE=false                        # Enable debug mode
DRY_RUN=false                          # Enable dry run mode (no actual requests)
PROFILE_PERFORMANCE=false              # Enable performance profiling
ENABLE_METRICS=true                    # Enable metrics collection
DATA_DIRECTORY=data                    # Data storage directory
CACHE_DIRECTORY=cache                  # Cache directory
TEMP_DIRECTORY=temp                    # Temporary files directory
```

## YAML Configuration

### Complete Configuration Example

```yaml
# config.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}
  openai_model: "gpt-4-turbo-preview"
  openai_temperature: 0.7
  openai_max_tokens: 4000
  bing_api_key: ${BING_API_KEY}
  bing_endpoint: "https://www.bing.com"
  google_api_key: ${GOOGLE_API_KEY}
  google_cx: ${GOOGLE_CX}
  perplexity_api_key: ${PERPLEXITY_API_KEY}

search:
  max_pages_per_query: 5
  results_per_page: 10
  timeout_seconds: 30
  max_concurrent_searches: 2
  rate_limit_rpm: 12
  retry_attempts: 3
  retry_delay: 2.0
  use_stealth_mode: true
  cache_results: true
  cache_ttl_seconds: 3600

crawling:
  max_depth: 2
  max_pages_per_site: 10
  timeout_seconds: 20
  respect_robots_txt: true
  user_agent: "VRSEN-Bot/1.0 (Lead Generation)"
  concurrent_crawlers: 3
  delay_between_requests: 1.0
  follow_redirects: true
  max_redirects: 5

processing:
  batch_size: 100
  max_workers: 4
  deduplication_enabled: true
  validation_enabled: true
  quality_threshold: 0.7
  email_validation_level: "strict"
  domain_classification_model: "rule-based"

export:
  output_directory: "output"
  csv_delimiter: ","
  csv_encoding: "utf-8"
  include_metadata: true
  compress_output: false
  timestamp_format: "%Y%m%d_%H%M%S"
  max_file_size_mb: 100
  split_large_files: true

logging:
  log_level: "INFO"
  log_directory: "logs"
  log_format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_log_size_mb: 50
  backup_count: 5
  enable_console_logging: true
  enable_file_logging: true
  separate_error_log: true

# Runtime settings
debug_mode: false
dry_run: false
profile_performance: false
enable_metrics: true

# Paths
data_directory: "data"
cache_directory: "cache"
temp_directory: "temp"
```

### Browser Configuration Section

```yaml
browser:
  mode: "headless"                      # headless, headful, auto
  user_agent: null                      # Custom user agent (null for auto)
  profile_path: null                    # Browser profile path
  proxy: null                           # Proxy URL
  window_size: [1920, 1080]           # Browser window size
  timeout: 30                          # Operation timeout
  max_retries: 3                       # Maximum retries
  
  # Resource blocking
  block_resources:
    - "image"
    - "stylesheet"
    - "font"
    - "media"
    - "*.png"
    - "*.jpg"
    - "*.jpeg"
    - "*.gif"
    - "*.css"
    - "*.woff"
    - "*.woff2"
    - "*.ttf"
    - "*.mp4"
    - "*.mp3"
  
  # Domain-specific overrides
  domain_overrides:
    "bing.com":
      mode: "headless"
      timeout: 45
      user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    "google.com":
      mode: "headful"
      timeout: 60
      block_resources: []               # Don't block resources for Google
```

### Anti-Detection Configuration

```yaml
anti_detection:
  # User Agent Management
  user_agents:
    rotation_enabled: true
    prefer_chrome: true
    desktop_only: true
    custom_agents:
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
  
  # Proxy Management
  proxies:
    enabled: false
    rotation_interval: 10               # Requests per proxy
    providers:
      - type: "http"
        url: "http://proxy1.example.com:8080"
        username: "user"
        password: "pass"
      - type: "socks5"
        url: "socks5://proxy2.example.com:1080"
  
  # Delay Management
  delays:
    base_delay: 2.0                     # Base delay in seconds
    random_factor: 0.5                  # Random multiplier
    action_delays:
      search: 3.0
      page_load: 2.0
      extraction: 1.5
      navigation: 1.0
  
  # Resource Blocking
  resource_blocking:
    enabled: true
    block_types:
      - "image"
      - "stylesheet"
      - "font"
      - "media"
    whitelist_domains:
      - "bing.com"
      - "microsoft.com"
```

## JSON Configuration

### Minimal JSON Configuration

```json
{
  "api": {
    "openai_api_key": "sk-your-key-here",
    "openai_model": "gpt-4-turbo-preview"
  },
  "search": {
    "max_pages_per_query": 3,
    "rate_limit_rpm": 8,
    "use_stealth_mode": true
  },
  "processing": {
    "batch_size": 50,
    "validation_enabled": true
  },
  "export": {
    "output_directory": "results",
    "include_metadata": true
  }
}
```

### Complete JSON Configuration

```json
{
  "api": {
    "openai_api_key": "${OPENAI_API_KEY}",
    "openai_model": "gpt-4-turbo-preview",
    "openai_temperature": 0.7,
    "openai_max_tokens": 4000
  },
  "search": {
    "max_pages_per_query": 5,
    "results_per_page": 10,
    "timeout_seconds": 30,
    "rate_limit_rpm": 12,
    "retry_attempts": 3,
    "use_stealth_mode": true,
    "cache_results": true
  },
  "browser": {
    "mode": "headless",
    "timeout": 30,
    "window_size": [1920, 1080],
    "block_resources": [
      "image", "stylesheet", "font", "media"
    ]
  },
  "processing": {
    "batch_size": 100,
    "validation_enabled": true,
    "email_validation_level": "strict",
    "deduplication_enabled": true
  },
  "export": {
    "output_directory": "output",
    "csv_delimiter": ",",
    "include_metadata": true,
    "timestamp_format": "%Y%m%d_%H%M%S"
  },
  "logging": {
    "log_level": "INFO",
    "enable_console_logging": true,
    "enable_file_logging": true
  }
}
```

## Runtime Configuration

### Programmatic Configuration

```python
from src.core.config_manager import ConfigManager

# Get configuration manager instance
config = ConfigManager()

# Update search settings
config.set('search.rate_limit_rpm', 8)
config.set('search.max_pages_per_query', 3)
config.set('search.timeout_seconds', 45)

# Update processing settings
config.set('processing.batch_size', 50)
config.set('processing.email_validation_level', 'moderate')

# Update browser settings
config.set('browser.mode', 'headful')
config.set('browser.timeout', 60)

# Update logging
config.set('logging.log_level', 'DEBUG')

# Save configuration
config.save('runtime_config.yaml')
```

### Configuration Validation

```python
# Validate current configuration
is_valid, errors = config.validate()

if not is_valid:
    print("Configuration errors found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration is valid")

# Get specific configuration values
api_key = config.get('api.openai_api_key')
rate_limit = config.get('search.rate_limit_rpm', 12)  # Default to 12
debug_mode = config.get('debug_mode', False)

print(f"API Key configured: {bool(api_key)}")
print(f"Rate limit: {rate_limit} RPM")
print(f"Debug mode: {debug_mode}")
```

## Domain-Specific Overrides

### Configuration by Domain

```yaml
domain_overrides:
  # Bing-specific settings
  "bing.com":
    browser_mode: "headless"
    timeout: 45
    user_agent_preferences:
      prefer_chrome: true
      desktop_only: true
    proxy_preferences:
      enable_rotation: false
    delay_config:
      base_delay: 3.0
      random_factor: 0.7
    resource_blocking:
      block_images: true
      block_css: true
  
  # Google-specific settings
  "google.com":
    browser_mode: "headful"
    timeout: 60
    user_agent_preferences:
      prefer_chrome: true
      desktop_only: true
    delay_config:
      base_delay: 5.0
      random_factor: 1.0
    resource_blocking:
      block_images: false
      block_css: false
  
  # Business websites
  "*.com":
    browser_mode: "headless"
    timeout: 20
    user_agent_preferences:
      prefer_chrome: true
    delay_config:
      base_delay: 1.5
      random_factor: 0.3
```

### Programmatic Domain Overrides

```python
from src.infra.anti_detection_supervisor import AntiDetectionSupervisor, DomainOverride

# Create domain-specific configuration
domain_overrides = {
    "bing.com": DomainOverride(
        domain="bing.com",
        browser_mode="headless",
        user_agent_preferences={"prefer_chrome": True},
        delay_config={"base_delay": 3.0, "random_factor": 0.5}
    ),
    "medical-practice.com": DomainOverride(
        domain="medical-practice.com",
        browser_mode="headless",
        delay_config={"base_delay": 1.0, "random_factor": 0.2}
    )
}

# Configure anti-detection supervisor
supervisor_config = {
    "domain_overrides": {
        domain: {
            "browser_mode": override.browser_mode,
            "user_agent_preferences": override.user_agent_preferences,
            "delay_config": override.delay_config
        }
        for domain, override in domain_overrides.items()
    }
}

supervisor = AntiDetectionSupervisor(supervisor_config)
```

## Agent Configuration

### Base Agent Configuration

```python
from src.core.base_agent import AgentConfig

# Conservative configuration for testing
conservative_config = AgentConfig(
    name="ConservativeAgent",
    description="Conservative agent for testing",
    model="gpt-4-turbo-preview",
    temperature=0.3,
    max_retries=5,
    retry_delay=3.0,
    enable_metrics=True,
    log_level="DEBUG"
)

# Production configuration
production_config = AgentConfig(
    name="ProductionAgent",
    description="Optimized agent for production",
    model="gpt-4-turbo-preview", 
    temperature=0.7,
    max_retries=3,
    retry_delay=2.0,
    enable_metrics=True,
    log_level="INFO"
)

# High-performance configuration
performance_config = AgentConfig(
    name="PerformanceAgent",
    description="High-performance agent",
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_retries=2,
    retry_delay=1.0,
    enable_metrics=False,
    log_level="WARNING"
)
```

### Bing Navigator Agent Configuration

```python
from src.agents.bing_navigator_agent import BingNavigatorAgent

# Get volume-specific recommendations
low_volume_settings = BingNavigatorAgent().get_recommended_settings("low")
medium_volume_settings = BingNavigatorAgent().get_recommended_settings("medium")
high_volume_settings = BingNavigatorAgent().get_recommended_settings("high")

print("Low volume settings:", low_volume_settings)
# {
#     "max_pages_per_query": 3,
#     "requests_per_minute": 6,
#     "base_delay_seconds": 5.0,
#     "session_rotation_interval": 20,
#     "proxy_rotation": True
# }

print("High volume settings:", high_volume_settings)
# {
#     "max_pages_per_query": 7,
#     "requests_per_minute": 18,
#     "base_delay_seconds": 2.0,
#     "session_rotation_interval": 10,
#     "proxy_rotation": True
# }
```

## Performance Tuning

### Memory Optimization

```yaml
performance:
  memory:
    max_memory_mb: 2048                 # Maximum memory usage
    gc_threshold: 1500                  # Garbage collection threshold
    cache_size: 1000                    # Maximum cache entries
    
  browser:
    max_sessions: 3                     # Maximum concurrent browser sessions
    session_timeout: 300                # Session timeout in seconds
    cleanup_interval: 600               # Cleanup interval in seconds
    
  processing:
    chunk_size: 100                     # Processing chunk size
    worker_pool_size: 4                 # Worker thread pool size
    queue_size: 500                     # Maximum queue size
```

### CPU Optimization

```yaml
performance:
  cpu:
    max_workers: 4                      # Maximum worker processes
    thread_pool_size: 8                 # Thread pool size
    async_batch_size: 10                # Async operation batch size
    
  timeouts:
    connect_timeout: 10                 # Connection timeout
    read_timeout: 30                    # Read timeout
    total_timeout: 60                   # Total request timeout
```

### Network Optimization

```yaml
performance:
  network:
    connection_pool_size: 20            # HTTP connection pool size
    max_retries: 3                      # Maximum network retries
    backoff_factor: 1.0                 # Exponential backoff factor
    
  rate_limiting:
    adaptive_rate_limiting: true        # Enable adaptive rate limiting
    burst_allowance: 5                  # Burst request allowance
    cooldown_period: 60                 # Cooldown period in seconds
```

## Security Configuration

### API Key Management

```yaml
security:
  api_keys:
    rotation_enabled: false             # Enable API key rotation
    rotation_interval_days: 30          # Rotation interval
    validation_enabled: true            # Validate API keys on startup
    
  encryption:
    encrypt_config: false               # Encrypt configuration files
    encryption_key: ${ENCRYPTION_KEY}   # Encryption key from environment
```

### Access Control

```yaml
security:
  access_control:
    enable_rate_limiting: true          # Enable user rate limiting
    max_requests_per_hour: 1000         # Maximum requests per hour
    blocked_domains:                    # Domains to block
      - "malicious.com"
      - "spam.net"
    
  logging:
    log_sensitive_data: false           # Log sensitive information
    audit_enabled: true                 # Enable audit logging
    audit_level: "INFO"                 # Audit logging level
```

### Data Privacy

```yaml
security:
  privacy:
    anonymize_logs: true                # Anonymize log data
    data_retention_days: 90             # Data retention period
    gdpr_compliance: true               # GDPR compliance mode
    
  output:
    redact_emails: false                # Redact email addresses in logs
    redact_phones: false                # Redact phone numbers in logs
    hash_personal_data: false           # Hash personal data
```

## Configuration Loading Priority

The system loads configuration in the following order (later sources override earlier ones):

1. **Default values** - Built-in defaults
2. **Configuration files** - YAML/JSON files
3. **Environment variables** - System environment
4. **Runtime updates** - Programmatic changes

### Configuration File Search Order

1. `config.yaml` (current directory)
2. `config.json` (current directory)  
3. `configs/config.yaml`
4. `configs/config.json`
5. `.env` file

### Environment Variable Mapping

```bash
# Nested configuration mapping
OPENAI_API_KEY           -> api.openai_api_key
MAX_PAGES_PER_QUERY     -> search.max_pages_per_query
RATE_LIMIT_RPM          -> search.rate_limit_rpm
DEBUG_MODE              -> debug_mode
LOG_LEVEL               -> logging.log_level
```

## Configuration Templates

### Development Template

```yaml
# dev_config.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}
  
search:
  max_pages_per_query: 2
  rate_limit_rpm: 6
  timeout_seconds: 45
  
browser:
  mode: "headful"
  timeout: 60
  
processing:
  batch_size: 10
  validation_enabled: true
  
logging:
  log_level: "DEBUG"
  enable_console_logging: true
  
debug_mode: true
dry_run: false
```

### Production Template

```yaml
# prod_config.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}
  
search:
  max_pages_per_query: 5
  rate_limit_rpm: 12
  timeout_seconds: 30
  cache_results: true
  
browser:
  mode: "headless"
  timeout: 30
  
processing:
  batch_size: 100
  validation_enabled: true
  deduplication_enabled: true
  
export:
  output_directory: "/data/output"
  include_metadata: true
  compress_output: true
  
logging:
  log_level: "INFO"
  enable_file_logging: true
  log_directory: "/var/log/pubscrape"
  
debug_mode: false
enable_metrics: true
```

### High-Performance Template

```yaml
# performance_config.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}
  openai_model: "gpt-3.5-turbo"
  
search:
  max_pages_per_query: 7
  rate_limit_rpm: 20
  timeout_seconds: 20
  max_concurrent_searches: 4
  
browser:
  mode: "headless"
  timeout: 20
  max_retries: 2
  
processing:
  batch_size: 200
  max_workers: 8
  validation_enabled: false
  
logging:
  log_level: "WARNING"
  enable_metrics: false
  
performance:
  memory:
    max_memory_mb: 4096
  cpu:
    max_workers: 8
```

---

This configuration reference provides comprehensive documentation for all configuration options in the PubScrape system. Use appropriate templates based on your use case and environment.