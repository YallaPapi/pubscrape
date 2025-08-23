#!/usr/bin/env python3
"""
Simple Query Generation Demo

Demonstrates the core query generation functionality without database components.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from queries import (
    QueryGenerator, LocationManager, BusinessCategoryManager,
    QueryQueue, SearchEngine, QueuePriority
)

def main():
    """Demonstrate core query generation features"""
    
    print("🚀 Simple Query Generation Demo")
    print("=" * 50)
    
    # 1. Initialize components
    print("\n1. Initialize Query Generator")
    generator = QueryGenerator()
    
    # Show available templates
    templates = generator.list_templates()
    print(f"   ✓ Loaded {len(templates)} templates:")
    for template in templates[:5]:
        print(f"     - {template.name}: {template.description}")
    
    # 2. Generate basic business queries
    print("\n2. Generate Business Queries")
    
    business_locations = [
        ("restaurants", "Seattle, WA"),
        ("coffee shops", "Portland, OR"), 
        ("pizza places", "San Francisco, CA"),
        ("bars", "New York, NY")
    ]
    
    for business_type, location in business_locations:
        query = generator.generate_query(
            "business_near_location",
            {"business_type": business_type, "location": location}
        )
        print(f"   ✓ {query.query}")
        print(f"     Engine: {query.engine.value}, Priority: {query.priority}")
    
    # 3. Generate site-specific queries
    print("\n3. Generate Site-Specific Queries")
    
    sites = ["yelp.com", "google.com", "tripadvisor.com"]
    
    for site in sites:
        query = generator.generate_query(
            "site_specific_business",
            {
                "domain": site,
                "business_type": "restaurants",
                "location": "Seattle"
            }
        )
        print(f"   ✓ {query.query}")
    
    # 4. Generate query variations
    print("\n4. Generate Query Variations")
    
    variations = generator.generate_variations(
        "business_near_location",
        {"location": "Seattle, WA"},
        {
            "business_type": ["italian restaurants", "sushi bars", "coffee shops"]
        }
    )
    
    print(f"   ✓ Generated {len(variations)} variations:")
    for var in variations:
        print(f"     - {var.query}")
    
    # 5. Location Manager Demo
    print("\n5. Location Manager Features")
    
    location_manager = LocationManager()
    
    # Add sample locations
    from queries.location_manager import Location
    sample_locations = [
        Location("Seattle", "Seattle", "Washington", "US", 47.6062, -122.3321),
        Location("Portland", "Portland", "Oregon", "US", 45.5152, -122.6784)
    ]
    
    for loc in sample_locations:
        location_manager.add_location(loc)
    
    # Test location search
    results = location_manager.search_locations("seattle")
    print(f"   ✓ Found {len(results)} locations for 'seattle'")
    
    # Generate location variations
    if results:
        variations = location_manager.create_location_variations(results[0])
        print(f"   ✓ Location variations: {variations}")
    
    # 6. Business Category Manager Demo
    print("\n6. Business Category Features")
    
    business_manager = BusinessCategoryManager()
    
    # Search categories
    food_categories = business_manager.search_categories("food")
    print(f"   ✓ Found {len(food_categories)} food categories:")
    for cat in food_categories[:3]:
        desc = getattr(cat, 'description', 'Business category')
        print(f"     - {cat.name}: {desc}")
    
    # Generate search terms
    terms = business_manager.generate_search_terms("restaurant")
    print(f"   ✓ Generated {len(terms)} search terms for 'restaurant':")
    for term in terms[:5]:
        print(f"     - {term}")
    
    # 7. Query Queue Demo
    print("\n7. Query Queue Management")
    
    queue = QueryQueue()
    
    # Add queries with different priorities
    test_queries = [
        ("urgent: restaurants Seattle", QueuePriority.URGENT),
        ("normal: cafes Portland", QueuePriority.NORMAL),
        ("low: bars San Francisco", QueuePriority.LOW)
    ]
    
    for query_text, priority in test_queries:
        queue.add_query(query_text, "bing", priority)
    
    stats = queue.get_queue_stats()
    print(f"   ✓ Queue stats: {stats['pending']} pending, {stats['total_added']} total")
    
    # Process queries in priority order
    print("   ✓ Processing queries in priority order:")
    while True:
        next_query = queue.get_next_query()
        if not next_query:
            break
        print(f"     - Processing: {next_query.query} (Priority: {next_query.priority.name})")
        queue.complete_query(next_query.id, result_count=25)
    
    final_stats = queue.get_queue_stats()
    print(f"   ✓ Final stats: {final_stats['completed']} completed")
    
    # 8. Advanced Template Features
    print("\n8. Advanced Template Features")
    
    # Validate queries for different engines
    test_query = "restaurants near Seattle"
    
    for engine in [SearchEngine.BING_WEB, SearchEngine.GOOGLE_WEB, SearchEngine.DUCKDUCKGO]:
        validation = generator.validate_query(test_query, engine)
        status = "✓ Valid" if validation['valid'] else "✗ Invalid"
        print(f"   {status} for {engine.value}: {len(validation.get('warnings', []))} warnings")
    
    # Show template statistics
    template_stats = generator.get_statistics()
    print(f"   ✓ Template statistics:")
    print(f"     - Total templates: {template_stats['total_templates']}")
    print(f"     - By engine: {template_stats['by_engine']}")
    print(f"     - Average variables per template: {template_stats['average_variables']}")
    
    print("\n✅ Demo completed successfully!")
    print("\nKey Features Demonstrated:")
    print("- ✓ Template-based query generation with multiple engines")
    print("- ✓ Business location and category management")
    print("- ✓ Site-specific search query creation")
    print("- ✓ Query variations and batch generation")
    print("- ✓ Priority-based query queue management")
    print("- ✓ Query validation and template statistics")
    print("- ✓ Location search and variation generation")
    print("- ✓ Business category search and term generation")


if __name__ == "__main__":
    main()