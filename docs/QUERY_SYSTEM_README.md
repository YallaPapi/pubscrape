# Query Generation and Management System

A comprehensive search query generation and management system designed for web scraping operations. This system provides template-based query generation, location and business category management, priority-based queuing, and result tracking capabilities.

## 🚀 Features

### Core Components

- **QueryGenerator**: Template-based query generation with multiple search engine support
- **LocationManager**: Geographic location management with city/region handling
- **BusinessCategoryManager**: Business type and category management system
- **QueryQueue**: Priority-based query queue with rate limiting
- **QueryTracker**: Query execution tracking and performance analytics

### Key Capabilities

- ✅ **Multi-Engine Support**: Bing Maps, Google Maps, Bing Web, Google Web, DuckDuckGo
- ✅ **Template System**: Flexible query templates with variable substitution
- ✅ **Location Management**: City/state/country handling with coordinate support
- ✅ **Business Categories**: Hierarchical business categorization system
- ✅ **Priority Queuing**: Advanced queue management with rate limiting
- ✅ **Site-Specific Searches**: Support for site: operator queries
- ✅ **Batch Processing**: Generate multiple queries from CSV data
- ✅ **Analytics**: Performance tracking and query effectiveness scoring
- ✅ **Duplicate Detection**: Automatic filtering of duplicate queries

## 📁 File Structure

```
src/queries/
├── __init__.py                 # Module exports
├── query_generator.py          # Template-based query generation
├── location_manager.py         # Geographic location management
├── business_categories.py      # Business type definitions
├── query_queue.py             # Priority queue with rate limiting
└── query_tracker.py           # Query tracking and analytics

data/
├── cities.csv                 # City database with coordinates
└── business_types.csv         # Business categories and types

tests/
└── test_query_generation.py   # Comprehensive test suite

examples/
├── query_generation_demo.py   # Full feature demonstration
└── simple_query_demo.py       # Core functionality demo
```

## 🛠 Installation

### Dependencies

```bash
# Required
pip install python-dateutil

# Optional (for geocoding features)
pip install geopy
```

### Basic Setup

```python
# Add to your Python path
import sys
sys.path.append('path/to/pubscrape/src')

from queries import (
    QueryGenerator, LocationManager, BusinessCategoryManager,
    QueryQueue, QueryTracker
)
```

## 📖 Usage Guide

### 1. Basic Query Generation

```python
from queries import QueryGenerator, SearchEngine

# Initialize generator
generator = QueryGenerator()

# Generate a business search query
query = generator.generate_query(
    "business_near_location",
    {
        "business_type": "restaurants",
        "location": "Seattle, WA"
    }
)

print(query.query)  # "restaurants near Seattle, WA"
print(query.engine)  # SearchEngine.BING_MAPS
```

### 2. Site-Specific Searches

```python
# Generate site-specific queries
site_query = generator.generate_query(
    "site_specific_business",
    {
        "domain": "yelp.com",
        "business_type": "restaurants", 
        "location": "Seattle"
    }
)

print(site_query.query)  # "site:yelp.com restaurants Seattle"
```

### 3. Batch Query Generation

```python
# Generate multiple queries
variable_sets = [
    {"business_type": "restaurants", "location": "Seattle, WA"},
    {"business_type": "cafes", "location": "Portland, OR"},
    {"business_type": "bars", "location": "San Francisco, CA"}
]

queries = generator.generate_batch("business_near_location", variable_sets)
print(f"Generated {len(queries)} queries")
```

### 4. Location Management

```python
from queries import LocationManager, Location

# Initialize location manager
location_manager = LocationManager()

# Add locations
seattle = Location(
    name="Seattle",
    city="Seattle", 
    state="Washington",
    country="US",
    latitude=47.6062,
    longitude=-122.3321,
    population=737015
)

location_manager.add_location(seattle)

# Search locations
results = location_manager.search_locations("seattle")
print(f"Found {len(results)} locations")

# Generate location variations
variations = location_manager.create_location_variations(seattle)
print(f"Location variations: {variations}")
```

### 5. Business Categories

```python
from queries import BusinessCategoryManager

# Initialize business manager
business_manager = BusinessCategoryManager()

# Search categories
food_categories = business_manager.search_categories("food")
print(f"Found {len(food_categories)} food categories")

# Generate search terms
terms = business_manager.generate_search_terms("restaurant")
print(f"Generated terms: {terms[:5]}")  # First 5 terms
```

### 6. Query Queue Management

```python
from queries import QueryQueue, QueuePriority

# Initialize queue
queue = QueryQueue()

# Add queries with priorities
queue.add_query(
    query="urgent restaurants Seattle",
    engine="bing",
    priority=QueuePriority.URGENT,
    category="restaurants",
    location="Seattle, WA"
)

# Process queries
while True:
    next_query = queue.get_next_query()
    if not next_query:
        break
    
    print(f"Processing: {next_query.query}")
    
    # Mark as completed
    queue.complete_query(next_query.id, result_count=25)

# Get statistics
stats = queue.get_queue_stats()
print(f"Queue stats: {stats}")
```

### 7. Query Tracking

```python
from queries import QueryTracker, QueryResult
from datetime import datetime

# Initialize tracker
tracker = QueryTracker("data/queries.db")

# Track a query result
result = QueryResult(
    query_id="test-123",
    query="restaurants near Seattle",
    engine="bing",
    location="Seattle, WA",
    category="restaurants",
    result_count=45,
    relevance_score=0.8,
    processing_time=2.5,
    executed_at=datetime.now()
)

# Track the result
success = tracker.track_query(result)
print(f"Tracked successfully: {success}")

# Get analytics
analytics = tracker.get_analytics(days=30)
print(f"Total queries: {analytics.total_queries}")
print(f"Success rate: {analytics.successful_queries / analytics.total_queries * 100:.1f}%")
```

## 🎯 Query Templates

### Built-in Templates

| Template Name | Description | Example |
|---------------|-------------|---------|
| `business_near_location` | Find businesses near location | "restaurants near Seattle, WA" |
| `business_in_city` | Find businesses in city | "restaurants in Seattle, Washington" |
| `site_specific_business` | Search on specific site | "site:yelp.com restaurants Seattle" |
| `business_with_phone` | Find businesses with contact info | "restaurants Seattle phone number" |
| `business_reviews` | Find business reviews | "restaurants reviews Seattle" |

### Custom Templates

```python
from queries import QueryTemplate, SearchEngine

# Create custom template
custom_template = QueryTemplate(
    name="social_business_search",
    template="site:{platform} {business} {location}",
    variables={"platform", "business", "location"},
    engine=SearchEngine.GOOGLE_WEB,
    description="Find businesses on social platforms"
)

generator.add_template(custom_template)

# Use custom template
query = generator.generate_query(
    "social_business_search",
    {
        "platform": "facebook.com",
        "business": "pizza restaurants",
        "location": "Seattle"
    }
)
```

## 🌍 Search Engines

### Supported Engines

- **Bing Maps**: Business location searches with radius support
- **Google Maps**: Enhanced location searches with detailed results
- **Bing Web**: General web searches with site operators
- **Google Web**: Advanced web searches with multiple operators
- **DuckDuckGo**: Privacy-focused searches

### Engine-Specific Features

```python
# Different engines for different use cases
templates = [
    ("business_near_location", SearchEngine.BING_MAPS),    # Best for local business
    ("site_specific_business", SearchEngine.GOOGLE_WEB),   # Best for site searches
    ("business_reviews", SearchEngine.GOOGLE_WEB),         # Best for review content
]
```

## 📊 Rate Limiting

### Configure Rate Limits

```python
from queries import QueryQueue, RateLimitRule
from datetime import timedelta

# Create queue with rate limiting
queue = QueryQueue()

# Add rate limit rules
bing_limit = RateLimitRule(
    group="bing",
    max_requests=100,
    time_window=timedelta(minutes=1),
    cooldown=timedelta(seconds=1)
)

queue.add_rate_limit(bing_limit)

# Queries with rate_limit_group will be throttled
queue.add_query(
    "restaurants Seattle",
    "bing",
    rate_limit_group="bing"
)
```

## 📈 Analytics and Reporting

### Performance Metrics

```python
# Get comprehensive analytics
analytics = tracker.get_analytics(days=30)

print(f"Performance Summary:")
print(f"- Total Queries: {analytics.total_queries}")
print(f"- Success Rate: {analytics.successful_queries/analytics.total_queries*100:.1f}%")
print(f"- Avg Processing Time: {analytics.avg_processing_time:.2f}s")
print(f"- Avg Results per Query: {analytics.avg_result_count:.1f}")

# Engine performance breakdown
for engine, stats in analytics.engine_stats.items():
    print(f"{engine}: {stats['success_rate']:.1f}% success, {stats['avg_results']:.1f} avg results")
```

### Top Performing Queries

```python
# Identify best performing queries
top_queries = tracker.get_top_performing_queries(limit=10)

for query_info in top_queries:
    print(f"Query: {query_info['query']}")
    print(f"Score: {query_info['avg_score']:.2f}")
    print(f"Avg Results: {query_info['avg_results']:.0f}")
    print("---")
```

## 🗂 Data Management

### CSV Data Loading

#### Cities Data (data/cities.csv)
```csv
city,state,country,latitude,longitude,population,timezone
Seattle,Washington,US,47.6062,-122.3321,737015,America/Los_Angeles
Portland,Oregon,US,45.5152,-122.6784,647805,America/Los_Angeles
```

#### Business Types (data/business_types.csv)
```csv
name,category,keywords,synonyms,tier,priority
restaurants,food_dining,"restaurant,dining,eatery","food,cuisine,meals",all,5
cafes,food_dining,"cafe,coffee shop","coffee,espresso",small,4
```

### Loading Data

```python
# Load cities
location_manager.load_from_csv("cities.csv")

# Load business types
business_manager.load_from_csv("business_types.csv", "categories")
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python -m pytest tests/test_query_generation.py -v

# Run specific test class
python -m pytest tests/test_query_generation.py::TestQueryGenerator -v

# Run with coverage
python -m pytest tests/test_query_generation.py --cov=src/queries
```

### Test Categories

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Complete workflow validation

## 🚀 Quick Start Examples

### Run Demo Scripts

```bash
# Core functionality demo (no external dependencies)
cd examples
python simple_query_demo.py

# Full feature demo (requires database)
python query_generation_demo.py
```

### Integration with Web Scrapers

```python
# Example integration with scraping framework
from queries import QueryGenerator, QueryQueue

def scraping_workflow():
    # 1. Generate queries
    generator = QueryGenerator()
    queries = generator.generate_batch("business_near_location", variable_sets)
    
    # 2. Queue for processing
    queue = QueryQueue()
    for query in queries:
        queue.add_query(query.query, query.engine.value)
    
    # 3. Process with your scraper
    while True:
        next_query = queue.get_next_query()
        if not next_query:
            break
            
        # Your scraping logic here
        results = your_scraper.scrape(next_query.query)
        
        # Mark completed
        queue.complete_query(next_query.id, len(results))
```

## 🛠 Advanced Configuration

### Custom Business Categories

```python
from queries import BusinessCategory, BusinessTier

# Define custom category
custom_category = BusinessCategory(
    name="tech_startups",
    tier=BusinessTier.SMALL,
    keywords=["startup", "tech company", "software"],
    synonyms=["technology", "innovation", "digital"],
    search_priority=4
)

business_manager.add_category(custom_category)
```

### Query Validation

```python
# Validate queries for specific engines
query = "very long query that might exceed engine limits..."

for engine in [SearchEngine.BING_WEB, SearchEngine.GOOGLE_WEB]:
    validation = generator.validate_query(query, engine)
    
    if not validation['valid']:
        print(f"Invalid for {engine.value}: {validation['errors']}")
    elif validation['warnings']:
        print(f"Warnings for {engine.value}: {validation['warnings']}")
```

## 📋 Best Practices

### 1. Query Design
- Use specific business types for better results
- Include location context when possible
- Test queries manually before batch processing
- Consider search engine limitations

### 2. Rate Limiting
- Set conservative rate limits to avoid blocking
- Use different limits for different engines
- Monitor rate limit effectiveness
- Implement backoff strategies

### 3. Data Management
- Regularly update city and business data
- Clean old query tracking data
- Monitor database size growth
- Use appropriate data types

### 4. Performance Optimization
- Index frequently searched fields
- Use batch operations when possible
- Cache common query patterns
- Monitor memory usage

## 🐛 Troubleshooting

### Common Issues

#### 1. Missing Dependencies
```bash
# Install optional dependencies
pip install geopy  # For geocoding features
```

#### 2. Database Errors
```python
# Check database initialization
tracker = QueryTracker("test.db")  # Use file-based DB for testing
```

#### 3. Template Variables
```python
# Ensure all required variables are provided
template = generator.get_template("business_near_location")
print(f"Required variables: {template.variables}")
```

#### 4. Rate Limiting Issues
```python
# Check rate limit status
next_query = queue.get_next_query(respect_rate_limits=False)  # Bypass for testing
```

## 📞 Support and Contributing

### Getting Help
- Check the examples directory for usage patterns
- Run the test suite to verify functionality
- Review error messages for debugging hints

### Contributing
- Follow existing code patterns
- Add tests for new features
- Update documentation
- Consider backward compatibility

## 📄 License

This query generation system is part of the PubScrape project. See the main project documentation for licensing information.

---

## 🔗 Related Documentation

- [Web Scraping Guide](./WEB_SCRAPING_GUIDE.md)
- [Data Processing Documentation](./DATA_PROCESSING.md)
- [API Reference](./API_REFERENCE.md)
- [Performance Tuning Guide](./PERFORMANCE_GUIDE.md)