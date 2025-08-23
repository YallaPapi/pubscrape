# Infinite Scroll Handler Usage Guide

## Overview

The Botasaurus Infinite Scroll Handler provides robust capabilities for extracting business data from map search results with dynamic content loading. It supports both Bing Maps and Google Maps with multiple scrolling strategies.

## Key Features

### 🚀 **Multi-Platform Support**
- **Bing Maps**: Full support with business card extraction
- **Google Maps**: Comprehensive listing extraction
- **Unified API**: Same interface for both platforms

### 🎯 **Advanced Scrolling Strategies**
- **Smooth Scroll**: Natural, gradual scrolling that mimics human behavior
- **Chunk Scroll**: Efficient large-increment scrolling with content stabilization
- **Adaptive Scroll**: AI-like strategy that learns optimal patterns during execution
- **Intelligent Scroll**: Machine learning-inspired optimization

### 🛡️ **Anti-Detection Features**
- **Botasaurus Integration**: Native stealth and anti-detection
- **Human-like Delays**: Jittered timing to avoid detection
- **Session Isolation**: Separate profiles for each campaign
- **Resource Blocking**: Speed optimization while maintaining stealth

### 📊 **Comprehensive Data Extraction**
- **Business Information**: Name, address, phone, email, website
- **Ratings & Reviews**: Star ratings and review counts
- **Categories**: Business type classification
- **Operating Hours**: Business hours where available
- **Deduplication**: Automatic removal of duplicate entries

## Quick Start

### Basic Usage

```python
from src.scrapers.infinite_scroll_handler import create_scroll_handler

# Create handler with adaptive strategy
handler = create_scroll_handler('adaptive', max_iterations=20)

# Extract from Bing Maps
session = handler.scroll_and_extract_bing_maps(
    query="restaurants", 
    location="Miami, FL"
)

# Extract from Google Maps  
session = handler.scroll_and_extract_google_maps(
    query="doctors",
    location="Seattle, WA"
)

print(f"Found {len(session.extracted_businesses)} businesses")
```

### Advanced Configuration

```python
from src.scrapers.infinite_scroll_handler import InfiniteScrollHandler, ScrollConfig

# Custom configuration
config = ScrollConfig(
    max_scroll_iterations=30,
    scroll_pause_time=2.5,
    stable_height_count=4,
    timeout_seconds=300,
    strategy_type='adaptive'
)

handler = InfiniteScrollHandler(config)
```

## Scrolling Strategies

### 1. Smooth Scroll Strategy
```python
handler = create_scroll_handler('smooth', 15)
```
- **Best for**: Sites with sensitive detection
- **Behavior**: Gradual 300px increments with easing
- **Speed**: Slower but more natural
- **Detection Risk**: Lowest

### 2. Chunk Scroll Strategy  
```python
handler = create_scroll_handler('chunk', 12)
```
- **Best for**: Fast extraction needs
- **Behavior**: Large viewport-based chunks
- **Speed**: Fastest
- **Detection Risk**: Medium

### 3. Adaptive Scroll Strategy
```python
handler = create_scroll_handler('adaptive', 20)
```
- **Best for**: Unknown sites or general use
- **Behavior**: Learns optimal patterns during execution
- **Speed**: Optimizes automatically
- **Detection Risk**: Low (adapts to site behavior)

## Data Extraction Features

### Business Card Structure
```python
{
    'business_name': 'The Coffee Shop',
    'address': '123 Main St, City, State 12345',
    'phone': '(555) 123-4567',
    'email': 'info@coffeeshop.com',
    'website': 'https://coffeeshop.com',
    'rating': 4.5,
    'review_count': 127,
    'category': 'Coffee Shop',
    'hours': 'Mon-Fri 7AM-7PM',
    'unique_id': 'abc123def456',
    'source_platform': 'bing_maps'
}
```

### Platform-Specific Features

#### Bing Maps Extraction
- **Rich Contact Data**: Often includes direct phone/email
- **Business Details**: Category, hours, detailed descriptions
- **Website Links**: Direct business website extraction
- **Ratings**: Star ratings and review counts

#### Google Maps Extraction  
- **Location Data**: Precise address information
- **Review Metrics**: Detailed rating and review data
- **Categories**: Comprehensive business classification
- **Photos**: Business image URLs (when available)

## Session Management

### Session Reports
```python
session = handler.scroll_and_extract_bing_maps("cafes", "Portland, OR")
report = handler.create_session_report(session)

print(f"Duration: {report['session_info']['duration_seconds']}s")
print(f"Businesses: {report['extraction_results']['total_businesses']}")
print(f"Email rate: {report['extraction_results']['email_rate']}%")
```

### Export Options
```python
# Export to CSV
businesses = session.extracted_businesses
df = pd.DataFrame(businesses)
df.to_csv('businesses.csv', index=False)

# Export to JSON
import json
with open('session_report.json', 'w') as f:
    json.dump(report, f, indent=2)
```

## Error Handling & Resilience

### Automatic Recovery
- **Popup Handling**: Automatically closes cookie/location popups
- **Rate Limit Detection**: Respects rate limits with exponential backoff
- **Content Stabilization**: Waits for dynamic content to fully load
- **Bottom Detection**: Intelligently detects when no more content is available

### Timeout Management
```python
config = ScrollConfig(
    timeout_seconds=180,  # 3 minute timeout
    stable_height_count=5,  # More conservative completion detection
    max_scroll_iterations=25
)
```

## Performance Optimization

### Resource Blocking
```python
# Handler automatically blocks images and CSS for speed
# Configured in @browser decorator:
# block_images=True, block_css=True
```

### Memory Management
- **Session Isolation**: Each search uses separate browser profile
- **Deduplication**: Automatic removal of duplicate businesses
- **Cleanup**: Proper session cleanup after extraction

### Concurrent Execution
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Multiple locations concurrently
locations = ["Miami FL", "Seattle WA", "Austin TX"]
query = "restaurants"

def extract_location(location):
    handler = create_scroll_handler('adaptive')
    return handler.scroll_and_extract_bing_maps(query, location)

with ThreadPoolExecutor(max_workers=3) as executor:
    sessions = list(executor.map(extract_location, locations))
```

## Best Practices

### 1. Strategy Selection
- **Unknown sites**: Use 'adaptive' strategy
- **Speed priority**: Use 'chunk' strategy  
- **Stealth priority**: Use 'smooth' strategy

### 2. Configuration Tuning
```python
# For large datasets
config = ScrollConfig(
    max_scroll_iterations=50,
    timeout_seconds=600,  # 10 minutes
    scroll_pause_time=3.0
)

# For quick tests
config = ScrollConfig(
    max_scroll_iterations=10,
    timeout_seconds=120,  # 2 minutes
    scroll_pause_time=1.5
)
```

### 3. Rate Limiting
- **Delay between sessions**: Add 30-60 second delays between campaigns
- **Session rotation**: Use different profiles for different searches
- **Proxy rotation**: Configure proxy pools for large-scale extraction

### 4. Data Quality
```python
# Filter results for quality
quality_businesses = [
    b for b in session.extracted_businesses 
    if b.get('phone') or b.get('email') or b.get('website')
]

# Validation
for business in quality_businesses:
    if business.get('email'):
        # Validate email format
        import re
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', business['email']):
            print(f"Valid email: {business['email']}")
```

## Troubleshooting

### Common Issues

1. **No businesses found**
   - Check query and location specificity
   - Verify platform accessibility
   - Try different scrolling strategy

2. **Slow performance**
   - Reduce `max_scroll_iterations`
   - Use 'chunk' strategy
   - Decrease `scroll_pause_time`

3. **Detection/blocking**
   - Use 'smooth' strategy
   - Increase delays
   - Enable proxy rotation

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging
handler = create_scroll_handler('adaptive')
# Will show detailed scroll metrics and extraction progress
```

## Integration Examples

### With Existing Scrapers
```python
# Integrate with Ted scraper patterns
from src.scrapers.infinite_scroll_handler import create_scroll_handler

def scrape_ted_speakers_with_maps():
    # First get speaker list from TED
    # Then use maps to find their speaking venues
    
    handler = create_scroll_handler('adaptive')
    
    for speaker in speakers:
        venue_query = f"conference venues {speaker['location']}"
        session = handler.scroll_and_extract_bing_maps(venue_query)
        # Process venue results...
```

### With Campaign System
```python
# Integration with existing campaign structure
def run_map_campaign(campaign_config):
    handler = create_scroll_handler(
        strategy=campaign_config.get('scroll_strategy', 'adaptive'),
        max_iterations=campaign_config.get('max_results', 20)
    )
    
    results = []
    for location in campaign_config['locations']:
        session = handler.scroll_and_extract_bing_maps(
            campaign_config['query'], 
            location
        )
        results.extend(session.extracted_businesses)
    
    return results
```

This infinite scroll handler provides a robust foundation for extracting business data from map search results while maintaining stealth and efficiency through Botasaurus integration.