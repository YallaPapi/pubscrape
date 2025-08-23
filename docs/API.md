# API Reference - PubScrape Infinite Scroll Scraper System

## Overview

This document provides comprehensive API documentation for all modules in the PubScrape system, including classes, methods, and configuration options.

## Table of Contents

- [Core Modules](#core-modules)
- [Agent System](#agent-system)
- [Infrastructure](#infrastructure)
- [Pipeline Components](#pipeline-components)
- [Configuration](#configuration)
- [Utilities](#utilities)

## Core Modules

### BrowserManager

**Location**: `src/infra/browser_manager.py`

Manages browser sessions with anti-detection capabilities using Botasaurus.

#### Class: `BrowserManager`

```python
class BrowserManager:
    def __init__(self, config: BrowserConfig)
```

##### Methods

**`get_browser_session(session_id: str, domain: Optional[str] = None) -> Driver`**

Get or create a browser session with anti-detection features.

- **Parameters**:
  - `session_id` (str): Unique identifier for the session
  - `domain` (Optional[str]): Domain for domain-specific overrides
- **Returns**: Configured Driver instance
- **Example**:
  ```python
  manager = BrowserManager(config)
  driver = manager.get_browser_session("session_1", "bing.com")
  ```

**`close_session(session_id: str) -> None`**

Close a browser session and clean up resources.

- **Parameters**:
  - `session_id` (str): Session identifier to close

**`get_session_stats(session_id: str) -> Optional[Dict[str, Any]]`**

Get statistics for a browser session.

- **Returns**: Dictionary containing session metrics or None

#### Configuration Classes

**`BrowserConfig`**

```python
@dataclass
class BrowserConfig:
    mode: BrowserMode = BrowserMode.HEADLESS
    user_agent: Optional[str] = None
    profile_path: Optional[str] = None
    proxy: Optional[str] = None
    block_resources: List[str] = None
    window_size: tuple = (1920, 1080)
    timeout: int = 30
    max_retries: int = 3
    domain_overrides: Dict[str, Dict[str, Any]] = None
```

**`BrowserMode`**

```python
class BrowserMode(Enum):
    HEADLESS = "headless"
    HEADFUL = "headful"
    AUTO = "auto"
```

#### Factory Function

**`create_browser_manager(mode: str = "headless", block_resources: bool = True, domain_overrides: Optional[Dict] = None) -> BrowserManager`**

Factory function to create a BrowserManager with common configurations.

### Anti-Detection Supervisor

**Location**: `src/infra/anti_detection_supervisor.py`

Coordinates all anti-detection components with per-domain overrides.

#### Class: `AntiDetectionSupervisor`

```python
class AntiDetectionSupervisor:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

##### Methods

**`create_session(session_id: str, domain: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`**

Create a new anti-detection session with all components configured.

- **Parameters**:
  - `session_id` (str): Unique session identifier
  - `domain` (Optional[str]): Target domain for domain-specific overrides
  - `context` (Optional[Dict]): Additional context for session creation
- **Returns**: Session configuration dictionary
- **Example**:
  ```python
  supervisor = AntiDetectionSupervisor()
  session = supervisor.create_session("test_session", "bing.com")
  ```

**`delay_for_action(session_id: str, action_type: ActionType, context: Optional[Dict] = None) -> float`**

Execute a delay for an action with logging.

**`record_request_result(session_id: str, url: str, success: bool, response_time: Optional[float] = None, status_code: Optional[int] = None, error: Optional[str] = None) -> None`**

Record the result of a request for monitoring.

**`get_statistics() -> Dict[str, Any]`**

Get comprehensive statistics from all components.

## Agent System

### Base Agent

**Location**: `src/core/base_agent.py`

Enhanced base agent with common functionality for all agents.

#### Class: `BaseAgent`

```python
class BaseAgent(Agent):
    def __init__(self, config: AgentConfig, **kwargs)
```

##### Configuration

**`AgentConfig`**

```python
@dataclass
class AgentConfig:
    name: str
    description: str
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_retries: int = 3
    retry_delay: float = 2.0
    enable_metrics: bool = True
    enable_caching: bool = True
    log_level: str = "INFO"
    instructions_path: Optional[str] = None
    tools: List[Type[BaseTool]] = field(default_factory=list)
```

##### Methods

**`execute_with_retry(func: callable, *args, max_retries: Optional[int] = None, **kwargs) -> Any`**

Execute a function with retry logic and exponential backoff.

**`get_metrics() -> Dict[str, Any]`**

Get current agent metrics including success rate and response times.

**`reset_metrics() -> None`**

Reset agent metrics to initial state.

### Bing Navigator Agent

**Location**: `src/agents/bing_navigator_agent.py`

Specialized agent for Bing SERP retrieval using Botasaurus.

#### Class: `BingNavigatorAgent`

```python
class BingNavigatorAgent(Agent):
    def __init__(self, name: str = "BingNavigator", description: str = None, instructions: str = None, tools: Optional[List] = None, **kwargs)
```

##### Methods

**`get_search_capabilities() -> dict`**

Get information about search capabilities and current configuration.

- **Returns**: Dictionary containing capability information
- **Example**:
  ```python
  agent = BingNavigatorAgent()
  capabilities = agent.get_search_capabilities()
  print(capabilities["supported_search_engines"])  # ["bing.com"]
  ```

**`get_recommended_settings(volume: str = "medium") -> dict`**

Get recommended settings based on scraping volume.

- **Parameters**:
  - `volume` (str): Expected volume ("low", "medium", "high")
- **Returns**: Dictionary of recommended settings

## Infrastructure

### Configuration Manager

**Location**: `src/core/config_manager.py`

Centralized configuration management with environment variable support.

#### Class: `ConfigManager`

Singleton configuration manager for the system.

##### Methods

**`get(key_path: str, default: Any = None) -> Any`**

Get configuration value by dot-notation path.

- **Parameters**:
  - `key_path` (str): Dot-notation path (e.g., "api.openai_api_key")
  - `default` (Any): Default value if key not found
- **Example**:
  ```python
  config = ConfigManager()
  api_key = config.get("api.openai_api_key")
  rate_limit = config.get("search.rate_limit_rpm", 12)
  ```

**`set(key_path: str, value: Any) -> bool`**

Set configuration value by dot-notation path.

**`load_from_file(file_path: str) -> bool`**

Load configuration from a file (YAML, JSON, or .env).

**`validate() -> tuple[bool, List[str]]`**

Validate current configuration and return errors if any.

**`save(file_path: Optional[str] = None, format: ConfigFormat = ConfigFormat.YAML) -> bool`**

Save current configuration to file.

#### Configuration Classes

**`SystemConfig`**

```python
@dataclass
class SystemConfig:
    api: APIConfig = field(default_factory=APIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    crawling: CrawlingConfig = field(default_factory=CrawlingConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    debug_mode: bool = False
    dry_run: bool = False
    profile_performance: bool = False
    enable_metrics: bool = True
```

**`APIConfig`**

```python
@dataclass
class APIConfig:
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4000
    bing_api_key: Optional[str] = None
    bing_endpoint: str = "https://www.bing.com"
    google_api_key: Optional[str] = None
    google_cx: Optional[str] = None
```

**`SearchConfig`**

```python
@dataclass
class SearchConfig:
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
```

## Pipeline Components

### Botasaurus Doctor Scraper

**Location**: `botasaurus_doctor_scraper.py`

Main scraper functions for doctor lead generation.

#### Functions

**`search_bing_for_doctors(query: str) -> Dict[str, Any]`**

Search Bing for doctors and extract URLs from search results.

- **Parameters**:
  - `query` (str): Search query for doctors
- **Returns**: Dictionary containing search results
- **Decorators**: `@request(use_stealth=True, block_detection=True, timeout=30, cache=False)`
- **Example**:
  ```python
  results = search_bing_for_doctors("doctors in miami")
  print(f"Found {results['total_urls']} URLs")
  for url in results['urls_found']:
      print(url)
  ```

**Response Format**:
```python
{
    'query': str,
    'urls_found': List[str],
    'total_urls': int,
    'search_html_length': int,
    'bing_search_url': str
}
```

**`extract_doctor_contact_info(url: str) -> Dict[str, Any]`**

Extract contact information from doctor/medical practice website.

- **Parameters**:
  - `url` (str): URL of the doctor's website
- **Returns**: Dictionary containing extracted contact information
- **Decorators**: `@request(use_stealth=True, block_detection=True, timeout=30, cache=False)`

**Response Format**:
```python
{
    'url': str,
    'business_name': str,
    'emails': List[str],
    'phones': List[str],
    'addresses': List[str],
    'doctor_names': List[str],
    'extraction_successful': bool,
    'extraction_timestamp': str
}
```

**`main() -> None`**

Main function to run the doctor lead scraping process.

## Error Handling

### Error Categories

```python
class ErrorCategory(Enum):
    NETWORK = "network"
    PARSING = "parsing"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
```

### Error Severity

```python
class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

## Rate Limiting

### Rate Limit Configuration

```python
# Configure rate limiting
config.set("search.rate_limit_rpm", 12)  # 12 requests per minute
config.set("search.retry_attempts", 3)
config.set("search.retry_delay", 2.0)
```

### Circuit Breaker Pattern

The system implements circuit breaker patterns for:
- Bing search requests
- Website crawling
- Email extraction

## Metrics and Monitoring

### Agent Metrics

```python
{
    "agent_name": str,
    "total_requests": int,
    "successful_requests": int,
    "failed_requests": int,
    "success_rate": float,
    "average_response_time": float,
    "error_counts": Dict[str, int],
    "last_error": Optional[str],
    "last_success_time": Optional[float]
}
```

### System Performance Metrics

```python
{
    "throughput": "500-1000 leads per hour",
    "success_rate": "85-95%",
    "anti_detection_success": "99%+",
    "resource_usage": "2-4GB RAM, 1-2 CPU cores"
}
```

## OpenAPI Schema

### Search Endpoint

```yaml
openapi: 3.0.0
info:
  title: PubScrape API
  version: 1.0.0
  description: Infinite scroll scraper system API

paths:
  /api/search:
    post:
      summary: Execute search query
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                  description: Search query
                max_pages:
                  type: integer
                  default: 5
                timeout:
                  type: integer
                  default: 30
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      type: object
                  total_count:
                    type: integer
                  execution_time:
                    type: number
```

### Configuration Endpoint

```yaml
  /api/config:
    get:
      summary: Get current configuration
      responses:
        '200':
          description: Current configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SystemConfig'
    
    put:
      summary: Update configuration
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SystemConfig'
```

## SDK Usage Examples

### Python SDK

```python
from pubscrape import PubScrapeClient

# Initialize client
client = PubScrapeClient(api_key="your_api_key")

# Execute search
results = client.search(
    query="doctors in miami",
    max_pages=3,
    extract_contacts=True
)

# Process results
for lead in results.leads:
    print(f"Business: {lead.business_name}")
    print(f"Email: {lead.email}")
    print(f"Phone: {lead.phone}")
```

### JavaScript SDK

```javascript
import { PubScrapeClient } from 'pubscrape-js';

const client = new PubScrapeClient({ apiKey: 'your_api_key' });

// Execute search
const results = await client.search({
  query: 'doctors in miami',
  maxPages: 3,
  extractContacts: true
});

// Process results
results.leads.forEach(lead => {
  console.log(`Business: ${lead.businessName}`);
  console.log(`Email: ${lead.email}`);
  console.log(`Phone: ${lead.phone}`);
});
```

## Environment Variables Reference

```bash
# Required
OPENAI_API_KEY=sk-...                    # OpenAI API key

# Optional - Search Configuration
MAX_PAGES_PER_QUERY=5                    # Maximum pages to scrape per query
RATE_LIMIT_RPM=12                        # Requests per minute limit
TIMEOUT_SECONDS=30                       # Request timeout
USE_STEALTH_MODE=true                    # Enable anti-detection

# Optional - System Configuration
DEBUG_MODE=false                         # Enable debug mode
LOG_LEVEL=INFO                          # Logging level
ENABLE_PROXY_ROTATION=true              # Enable proxy rotation
ENABLE_METRICS=true                     # Enable metrics collection

# Optional - Export Configuration
OUTPUT_DIRECTORY=output                  # Output directory
INCLUDE_METADATA=true                   # Include metadata in exports
COMPRESS_OUTPUT=false                   # Compress output files
```

## Dependencies

### Core Dependencies

```python
# Web scraping and automation
botasaurus>=4.0.0
selenium>=4.15.0

# Multi-agent orchestration
agency-swarm>=0.4.0

# Web scraping utilities
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Data validation
pydantic>=2.5.0
email-validator>=2.1.0

# Configuration management
pyyaml>=6.0.1
python-dotenv>=1.0.0
```

### Optional Dependencies

```python
# Advanced logging
structlog>=23.2.0
coloredlogs>=15.0.1

# Data processing
pandas>=2.1.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
```

---

For more detailed information on specific components, refer to the individual module documentation and inline code comments.