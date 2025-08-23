# User Guide - PubScrape Infinite Scroll Scraper System

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Advanced Configuration](#advanced-configuration)
4. [Multi-Agent Workflows](#multi-agent-workflows)
5. [Data Export and Validation](#data-export-and-validation)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

Before you begin, ensure you have:
- Python 3.8 or higher
- Chrome/Chromium browser installed
- At least 4GB of RAM
- Stable internet connection
- API keys for OpenAI (required)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/pubscrape.git
   cd pubscrape
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Environment Configuration

Create a `.env` file with the following variables:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional - Search Configuration
MAX_PAGES_PER_QUERY=5
RATE_LIMIT_RPM=12
TIMEOUT_SECONDS=30

# Optional - System Settings
DEBUG_MODE=false
LOG_LEVEL=INFO
ENABLE_PROXY_ROTATION=false
```

### Verification

Test your installation:

```bash
# Run basic tests
python -c "import botasaurus; print('✅ Botasaurus installed')"
python -c "from src.core.config_manager import ConfigManager; print('✅ Config manager ready')"

# Run test suite
pytest tests/unit/ -v
```

## Basic Usage

### Simple Doctor Lead Scraping

The easiest way to start is with the built-in doctor scraper:

```python
from botasaurus_doctor_scraper import main

# Run the complete doctor scraping pipeline
main()
```

This will:
1. Search Bing for "doctors in miami"
2. Extract URLs from search results
3. Visit each doctor website
4. Extract contact information
5. Export results to CSV

**Expected Output**:
```
🏥 BOTASAURUS DOCTOR SCRAPER - MIAMI
Searching Bing for real doctor websites...
✅ Bing search completed
   Query: doctors in miami
   URLs found: 15
   Search HTML length: 125432 chars

🔍 Extracting contact info from 10 doctor websites...
Processing 1/10: https://miamicardiology.com
   ✅ SUCCESS: Miami Cardiology Associates
      Email: info@miamicardiology.com
      Phone: (305) 555-0123
      Doctor: Dr. John Smith, MD
```

### Custom Query Scraping

For custom searches, use the individual functions:

```python
from botasaurus_doctor_scraper import search_bing_for_doctors, extract_doctor_contact_info

# Step 1: Search for professionals
query = "dentists in Los Angeles"
search_results = search_bing_for_doctors(query)

print(f"Found {search_results['total_urls']} potential websites")

# Step 2: Extract contact information
leads = []
for url in search_results['urls_found'][:5]:  # Process first 5 URLs
    contact_info = extract_doctor_contact_info(url)
    
    if contact_info['extraction_successful']:
        lead = {
            'business_name': contact_info['business_name'],
            'website': url,
            'email': contact_info['emails'][0] if contact_info['emails'] else '',
            'phone': contact_info['phones'][0] if contact_info['phones'] else ''
        }
        leads.append(lead)
        print(f"✅ Extracted: {lead['business_name']}")

print(f"\nTotal leads extracted: {len(leads)}")
```

### Using the Configuration System

```python
from src.core.config_manager import ConfigManager

# Get configuration manager
config = ConfigManager()

# Check current settings
rate_limit = config.get('search.rate_limit_rpm', 12)
max_pages = config.get('search.max_pages_per_query', 5)

print(f"Rate limit: {rate_limit} RPM")
print(f"Max pages: {max_pages}")

# Update configuration
config.set('search.rate_limit_rpm', 6)  # Reduce rate for testing
config.set('search.timeout_seconds', 45)  # Increase timeout

# Save configuration
config.save('custom_config.yaml')
```

## Advanced Configuration

### Browser Configuration

Configure browser behavior for different scenarios:

```python
from src.infra.browser_manager import BrowserManager, BrowserConfig, BrowserMode

# Headless mode for production
config = BrowserConfig(
    mode=BrowserMode.HEADLESS,
    window_size=(1920, 1080),
    timeout=30,
    max_retries=3,
    block_resources=[
        "image", "stylesheet", "font", "media",
        "*.png", "*.jpg", "*.css", "*.mp4"
    ]
)

# Create browser manager
browser_manager = BrowserManager(config)

# Get session
driver = browser_manager.get_browser_session("session_1", "bing.com")
```

### Anti-Detection Configuration

Set up advanced anti-detection features:

```python
from src.infra.anti_detection_supervisor import AntiDetectionSupervisor

# Configure anti-detection
anti_detection_config = {
    "domain_overrides": {
        "bing.com": {
            "browser_mode": "headless",
            "user_agent_preferences": {
                "prefer_chrome": True,
                "desktop_only": True
            },
            "delay_config": {
                "base_delay": 2.0,
                "random_factor": 0.5
            }
        }
    }
}

supervisor = AntiDetectionSupervisor(anti_detection_config)

# Create session with anti-detection
session = supervisor.create_session(
    session_id="test_session",
    domain="bing.com",
    context={"campaign": "doctors_miami"}
)
```

### Custom YAML Configuration

Create a `config.yaml` file for persistent configuration:

```yaml
# config.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}
  openai_model: "gpt-4-turbo-preview"
  openai_temperature: 0.7

search:
  max_pages_per_query: 3
  results_per_page: 10
  rate_limit_rpm: 8
  timeout_seconds: 30
  use_stealth_mode: true
  cache_results: true

processing:
  batch_size: 50
  validation_enabled: true
  email_validation_level: "strict"
  deduplication_enabled: true

export:
  output_directory: "results"
  csv_delimiter: ","
  include_metadata: true
  timestamp_format: "%Y%m%d_%H%M%S"

logging:
  log_level: "INFO"
  enable_file_logging: true
  max_log_size_mb: 50
```

Load the configuration:

```python
from src.core.config_manager import ConfigManager

config = ConfigManager()
config.load_from_file("config.yaml")

# Verify configuration
is_valid, errors = config.validate()
if not is_valid:
    print("Configuration errors:", errors)
```

## Multi-Agent Workflows

### Agent System Overview

The system uses specialized agents for different tasks:

1. **BingNavigatorAgent**: Handles search engine queries
2. **EmailExtractorAgent**: Extracts contact information
3. **DomainClassifierAgent**: Filters and categorizes domains
4. **ValidatorDedupeAgent**: Validates and deduplicates data
5. **ExporterAgent**: Handles data export

### Using Individual Agents

```python
from src.agents.bing_navigator_agent import BingNavigatorAgent
from src.core.base_agent import AgentConfig

# Configure custom agent
agent_config = AgentConfig(
    name="CustomBingAgent",
    description="Custom Bing search agent",
    max_retries=5,
    retry_delay=3.0,
    enable_metrics=True,
    log_level="DEBUG"
)

# Create agent
agent = BingNavigatorAgent(agent_config)

# Get agent capabilities
capabilities = agent.get_search_capabilities()
print("Supported engines:", capabilities["supported_search_engines"])

# Get recommended settings for high-volume scraping
settings = agent.get_recommended_settings("high")
print("Recommended RPM:", settings["requests_per_minute"])
```

### Multi-Agent Pipeline

```python
from src.core.base_agent import BaseAgent, AgentConfig

class CustomLeadPipeline:
    def __init__(self):
        # Initialize agents
        self.navigator = BingNavigatorAgent()
        self.extractor = EmailExtractorAgent()
        self.validator = ValidatorDedupeAgent()
        
    def run_pipeline(self, queries: List[str]) -> List[Dict]:
        all_leads = []
        
        for query in queries:
            # Step 1: Search and get URLs
            search_results = self.navigator.search(query)
            
            # Step 2: Extract contact info from URLs
            for url in search_results['urls']:
                contact_info = self.extractor.extract(url)
                if contact_info['success']:
                    all_leads.append(contact_info['data'])
            
            # Step 3: Validate and deduplicate
            validated_leads = self.validator.process(all_leads)
        
        return validated_leads

# Usage
pipeline = CustomLeadPipeline()
queries = ["doctors in miami", "dentists in miami", "lawyers in miami"]
results = pipeline.run_pipeline(queries)
```

## Data Export and Validation

### Export Formats

#### CSV Export

```python
import csv
from datetime import datetime

def export_to_csv(leads: List[Dict], filename: str = None):
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'leads_{timestamp}.csv'
    
    fieldnames = [
        'business_name', 'website', 'primary_email', 'primary_phone',
        'address', 'doctor_names', 'extraction_date'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
    
    print(f"Exported {len(leads)} leads to {filename}")

# Usage
export_to_csv(leads, "miami_doctors.csv")
```

#### JSON Export with Metadata

```python
import json
from datetime import datetime

def export_to_json(leads: List[Dict], metadata: Dict = None):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'leads_{timestamp}.json'
    
    export_data = {
        'metadata': {
            'timestamp': timestamp,
            'total_leads': len(leads),
            'extraction_method': 'botasaurus_scraper',
            'version': '1.0.0',
            **(metadata or {})
        },
        'leads': leads
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"Exported {len(leads)} leads with metadata to {filename}")

# Usage
metadata = {
    'campaign': 'Miami Medical Professionals',
    'queries_used': ['doctors in miami', 'specialists in miami'],
    'success_rate': '85%'
}
export_to_json(leads, metadata)
```

### Data Validation

#### Email Validation

```python
import re
from email_validator import validate_email, EmailNotValidError

def validate_email_address(email: str) -> Dict[str, Any]:
    """Validate email address with detailed feedback"""
    
    # Basic regex check
    basic_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    basic_valid = bool(re.match(basic_pattern, email))
    
    # Advanced validation
    try:
        validated = validate_email(email)
        return {
            'email': email,
            'is_valid': True,
            'normalized': validated.email,
            'domain': validated.domain,
            'local': validated.local,
            'basic_valid': basic_valid
        }
    except EmailNotValidError as e:
        return {
            'email': email,
            'is_valid': False,
            'error': str(e),
            'basic_valid': basic_valid
        }

# Usage
email_result = validate_email_address("doctor@miamiclinic.com")
print(f"Valid: {email_result['is_valid']}")
print(f"Normalized: {email_result.get('normalized', 'N/A')}")
```

#### Phone Number Validation

```python
import re

def validate_phone_number(phone: str) -> Dict[str, Any]:
    """Validate and format phone numbers"""
    
    # Remove all non-digit characters
    digits = re.sub(r'[^\d]', '', phone)
    
    # Validation patterns
    patterns = {
        'us_10_digit': r'^\d{10}$',
        'us_11_digit': r'^1\d{10}$',
        'international': r'^\+?\d{10,15}$'
    }
    
    results = {}
    for pattern_name, pattern in patterns.items():
        results[pattern_name] = bool(re.match(pattern, digits))
    
    # Format US numbers
    formatted = None
    if len(digits) == 10:
        formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        formatted = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return {
        'original': phone,
        'digits_only': digits,
        'formatted': formatted,
        'is_valid': any(results.values()),
        'patterns': results
    }

# Usage
phone_result = validate_phone_number("(305) 555-0123")
print(f"Formatted: {phone_result['formatted']}")
print(f"Valid: {phone_result['is_valid']}")
```

### Deduplication

```python
import hashlib
from typing import List, Dict, Set

class LeadDeduplicator:
    def __init__(self):
        self.seen_hashes: Set[str] = set()
        self.duplicate_count = 0
    
    def generate_hash(self, lead: Dict) -> str:
        """Generate hash for lead based on key fields"""
        key_fields = [
            lead.get('business_name', '').lower().strip(),
            lead.get('primary_email', '').lower().strip(),
            lead.get('website', '').lower().strip()
        ]
        
        # Create hash from non-empty fields
        hash_string = '|'.join(field for field in key_fields if field)
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def is_duplicate(self, lead: Dict) -> bool:
        """Check if lead is a duplicate"""
        lead_hash = self.generate_hash(lead)
        
        if lead_hash in self.seen_hashes:
            self.duplicate_count += 1
            return True
        
        self.seen_hashes.add(lead_hash)
        return False
    
    def deduplicate(self, leads: List[Dict]) -> List[Dict]:
        """Remove duplicates from lead list"""
        unique_leads = []
        
        for lead in leads:
            if not self.is_duplicate(lead):
                unique_leads.append(lead)
        
        print(f"Removed {self.duplicate_count} duplicates")
        print(f"Unique leads: {len(unique_leads)}")
        
        return unique_leads

# Usage
deduplicator = LeadDeduplicator()
unique_leads = deduplicator.deduplicate(leads)
```

## Performance Optimization

### Rate Limiting Best Practices

```python
import time
import random

class SmartRateLimiter:
    def __init__(self, rpm: int = 12):
        self.rpm = rpm
        self.request_times = []
        self.blocked_until = None
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Check if we're in a blocked state
        if self.blocked_until and now < self.blocked_until:
            wait_time = self.blocked_until - now
            print(f"Rate limited, waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
            return
        
        # Clean old requests (older than 1 minute)
        minute_ago = now - 60
        self.request_times = [t for t in self.request_times if t > minute_ago]
        
        # Check if we need to wait
        if len(self.request_times) >= self.rpm:
            wait_time = 60 - (now - self.request_times[0]) + random.uniform(1, 3)
            print(f"Rate limit reached, waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)
    
    def handle_rate_limit_response(self, retry_after: int = None):
        """Handle 429 response with exponential backoff"""
        if retry_after:
            self.blocked_until = time.time() + retry_after
        else:
            # Exponential backoff: 1, 2, 4, 8 minutes
            backoff_time = 60 * (2 ** min(3, len(self.request_times) // 10))
            self.blocked_until = time.time() + backoff_time
        
        print(f"Rate limited by server, backing off until {self.blocked_until}")

# Usage
rate_limiter = SmartRateLimiter(rpm=8)  # Conservative rate

for query in queries:
    rate_limiter.wait_if_needed()
    try:
        results = search_bing_for_doctors(query)
    except RateLimitError as e:
        rate_limiter.handle_rate_limit_response(e.retry_after)
```

### Memory Management

```python
import gc
import psutil
import os

class MemoryManager:
    def __init__(self, max_memory_mb: int = 2048):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process(os.getpid())
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': self.process.memory_percent()
        }
    
    def check_memory_limit(self) -> bool:
        """Check if memory usage is within limits"""
        usage = self.get_memory_usage()
        if usage['rss_mb'] > self.max_memory_mb:
            print(f"⚠️  Memory usage high: {usage['rss_mb']:.1f}MB")
            return False
        return True
    
    def cleanup_if_needed(self):
        """Perform garbage collection if memory is high"""
        if not self.check_memory_limit():
            print("🧹 Performing garbage collection...")
            gc.collect()
            
            # Check again after cleanup
            usage = self.get_memory_usage()
            print(f"✅ Memory after cleanup: {usage['rss_mb']:.1f}MB")

# Usage
memory_manager = MemoryManager(max_memory_mb=1500)

for i, url in enumerate(urls):
    if i % 10 == 0:  # Check every 10 iterations
        memory_manager.cleanup_if_needed()
    
    contact_info = extract_doctor_contact_info(url)
    leads.append(contact_info)
```

### Browser Session Optimization

```python
from src.infra.browser_manager import BrowserManager, BrowserConfig

class OptimizedBrowserManager:
    def __init__(self, max_sessions: int = 3):
        self.max_sessions = max_sessions
        self.sessions = {}
        self.session_usage = {}
    
    def get_least_used_session(self) -> str:
        """Get the session ID with least usage"""
        if not self.session_usage:
            return f"session_{len(self.sessions)}"
        
        return min(self.session_usage.items(), key=lambda x: x[1])[0]
    
    def get_session(self, domain: str = None):
        """Get optimized browser session"""
        # Reuse existing session if under limit
        if len(self.sessions) < self.max_sessions:
            session_id = f"session_{len(self.sessions)}"
        else:
            session_id = self.get_least_used_session()
        
        # Track usage
        self.session_usage[session_id] = self.session_usage.get(session_id, 0) + 1
        
        # Create or reuse session
        if session_id not in self.sessions:
            config = BrowserConfig(
                mode=BrowserMode.HEADLESS,
                timeout=20,  # Shorter timeout for faster failures
                block_resources=[
                    "image", "stylesheet", "font", "media",
                    "*.png", "*.jpg", "*.css", "*.mp4", "*.mp3"
                ]
            )
            manager = BrowserManager(config)
            self.sessions[session_id] = manager.get_browser_session(session_id, domain)
        
        return self.sessions[session_id]
    
    def cleanup_sessions(self):
        """Clean up all browser sessions"""
        for session_id, session in self.sessions.items():
            try:
                session.quit()
            except:
                pass
        self.sessions.clear()
        self.session_usage.clear()

# Usage
browser_manager = OptimizedBrowserManager(max_sessions=2)

try:
    for url in urls:
        driver = browser_manager.get_session("business.com")
        # Use driver for scraping
        driver.get(url)
        # Extract data...
finally:
    browser_manager.cleanup_sessions()
```

## Best Practices

### 1. Respectful Scraping

```python
# Always include delays
import time
import random

def respectful_delay():
    """Add human-like delays between requests"""
    base_delay = 2.0
    random_factor = random.uniform(0.5, 1.5)
    delay = base_delay * random_factor
    time.sleep(delay)

# Use conservative rate limits
CONSERVATIVE_RPM = 6  # 6 requests per minute
MODERATE_RPM = 12     # 12 requests per minute  
AGGRESSIVE_RPM = 20   # 20 requests per minute (risky)
```

### 2. Error Handling

```python
import logging
from typing import Optional

def robust_extraction(url: str, max_retries: int = 3) -> Optional[Dict]:
    """Extract data with robust error handling"""
    
    for attempt in range(max_retries):
        try:
            contact_info = extract_doctor_contact_info(url)
            
            if contact_info['extraction_successful']:
                return contact_info
            else:
                logging.warning(f"Extraction failed for {url}: {contact_info.get('error', 'Unknown error')}")
                
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
            
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = (2 ** attempt) * random.uniform(1, 2)
                time.sleep(wait_time)
            else:
                logging.error(f"All attempts failed for {url}")
    
    return None

# Usage
for url in urls:
    result = robust_extraction(url)
    if result:
        leads.append(result)
```

### 3. Data Quality Checks

```python
def validate_lead_quality(lead: Dict) -> Dict[str, Any]:
    """Validate lead data quality"""
    
    quality_score = 0
    issues = []
    
    # Check business name
    if lead.get('business_name') and len(lead['business_name']) > 3:
        quality_score += 25
    else:
        issues.append("Missing or short business name")
    
    # Check email
    if lead.get('primary_email') and '@' in lead['primary_email']:
        quality_score += 30
    else:
        issues.append("Missing or invalid email")
    
    # Check phone
    if lead.get('primary_phone'):
        phone_digits = re.sub(r'[^\d]', '', lead['primary_phone'])
        if len(phone_digits) >= 10:
            quality_score += 25
        else:
            issues.append("Invalid phone number")
    else:
        issues.append("Missing phone number")
    
    # Check website
    if lead.get('website') and lead['website'].startswith('http'):
        quality_score += 20
    else:
        issues.append("Missing or invalid website")
    
    return {
        'quality_score': quality_score,
        'grade': 'A' if quality_score >= 80 else 'B' if quality_score >= 60 else 'C' if quality_score >= 40 else 'D',
        'issues': issues,
        'is_high_quality': quality_score >= 70
    }

# Filter high-quality leads
high_quality_leads = []
for lead in leads:
    quality = validate_lead_quality(lead)
    lead['quality'] = quality
    
    if quality['is_high_quality']:
        high_quality_leads.append(lead)

print(f"High quality leads: {len(high_quality_leads)}/{len(leads)}")
```

### 4. Monitoring and Alerting

```python
import time
from datetime import datetime

class ScrapingMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limit_hits = 0
    
    def log_request(self, success: bool, rate_limited: bool = False):
        """Log request outcome"""
        self.total_requests += 1
        
        if rate_limited:
            self.rate_limit_hits += 1
        elif success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        runtime = time.time() - self.start_time
        
        return {
            'runtime_minutes': runtime / 60,
            'total_requests': self.total_requests,
            'success_rate': self.successful_requests / max(1, self.total_requests),
            'failure_rate': self.failed_requests / max(1, self.total_requests),
            'rate_limit_rate': self.rate_limit_hits / max(1, self.total_requests),
            'requests_per_minute': self.total_requests / max(1, runtime / 60)
        }
    
    def should_alert(self) -> bool:
        """Check if we should raise an alert"""
        stats = self.get_stats()
        
        # Alert conditions
        if stats['failure_rate'] > 0.5:  # 50% failure rate
            return True
        if stats['rate_limit_rate'] > 0.2:  # 20% rate limited
            return True
        if stats['runtime_minutes'] > 10 and stats['requests_per_minute'] < 1:  # Too slow
            return True
        
        return False

# Usage
monitor = ScrapingMonitor()

for url in urls:
    try:
        result = extract_doctor_contact_info(url)
        monitor.log_request(success=result['extraction_successful'])
        
        # Check for alerts every 10 requests
        if monitor.total_requests % 10 == 0:
            if monitor.should_alert():
                print("⚠️  Performance alert triggered!")
                print(monitor.get_stats())
                
    except RateLimitError:
        monitor.log_request(success=False, rate_limited=True)
    except Exception:
        monitor.log_request(success=False)

# Final stats
print("📊 Final Statistics:")
print(monitor.get_stats())
```

This user guide provides comprehensive instructions for using the PubScrape system effectively. For more specific use cases or advanced configurations, refer to the API documentation and configuration reference.