#!/usr/bin/env python3
"""
Query Generation System Demo

This script demonstrates the complete query generation and management system
including templates, locations, business categories, queuing, and tracking.
"""

import sys
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from queries import (
    QueryGenerator, LocationManager, BusinessCategoryManager,
    QueryQueue, QueryTracker, SearchEngine, QueuePriority
)

def main():
    """Demonstrate the complete query generation workflow"""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("🚀 Query Generation System Demo")
    print("=" * 50)
    
    # 1. Initialize components
    print("\n1. Initializing Components...")
    generator = QueryGenerator()
    location_manager = LocationManager("../data")
    business_manager = BusinessCategoryManager("../data")
    queue = QueryQueue()
    tracker = QueryTracker(":memory:")  # Use in-memory database for demo
    
    # 2. Load data
    print("\n2. Loading Sample Data...")
    
    # Add sample locations
    from queries.location_manager import Location
    sample_locations = [
        Location("Seattle", "Seattle", "Washington", "US", 47.6062, -122.3321, 737015),
        Location("Portland", "Portland", "Oregon", "US", 45.5152, -122.6784, 647805),
        Location("San Francisco", "San Francisco", "California", "US", 37.7749, -122.4194, 873965),
        Location("New York", "New York", "New York", "US", 40.7128, -74.0060, 8175133),
        Location("Chicago", "Chicago", "Illinois", "US", 41.8781, -87.6298, 2695598)
    ]
    
    for location in sample_locations:
        location_manager.add_location(location)
    
    print(f"   ✓ Loaded {len(sample_locations)} locations")
    print(f"   ✓ Loaded {len(generator.templates)} query templates")
    print(f"   ✓ Loaded {len(business_manager.categories)} business categories")
    
    # 3. Generate queries
    print("\n3. Generating Queries...")
    
    business_types = ["restaurants", "cafes", "bars", "pizza restaurant"]
    all_queries = []
    
    for location in sample_locations[:3]:  # Use first 3 locations
        for business_type in business_types:
            # Generate basic business query
            query = generator.generate_query(
                "business_near_location",
                {
                    "business_type": business_type,
                    "location": location.full_name
                }
            )
            all_queries.append(query)
            
            # Generate site-specific query
            site_query = generator.generate_query(
                "site_specific_business",
                {
                    "domain": "yelp.com",
                    "business_type": business_type,
                    "location": location.city
                }
            )
            all_queries.append(site_query)
    
    print(f"   ✓ Generated {len(all_queries)} queries")
    
    # 4. Queue management
    print("\n4. Managing Query Queue...")
    
    # Add queries to queue with different priorities
    for i, query in enumerate(all_queries):
        priority = QueuePriority.HIGH if i % 3 == 0 else QueuePriority.NORMAL
        
        queue.add_query(
            query=query.query,
            engine=query.engine.value,
            priority=priority,
            category=query.variables.get("business_type"),
            location=query.variables.get("location")
        )
    
    queue_stats = queue.get_queue_stats()
    print(f"   ✓ Queued {queue_stats['pending']} queries")
    print(f"   ✓ {queue_stats['total_added']} total queries added")
    
    # 5. Process queries (simulation)
    print("\n5. Processing Queries (Simulation)...")
    
    processed_count = 0
    while processed_count < 5:  # Process first 5 queries
        queued_query = queue.get_next_query()
        if not queued_query:
            break
        
        print(f"   Processing: {queued_query.query[:60]}...")
        
        # Simulate processing with mock results
        from queries.query_tracker import QueryResult
        import random
        
        result = QueryResult(
            query_id=queued_query.id,
            query=queued_query.query,
            engine=queued_query.engine,
            location=queued_query.location,
            category=queued_query.category,
            result_count=random.randint(10, 100),
            relevance_score=random.uniform(0.6, 1.0),
            completeness_score=random.uniform(0.5, 0.9),
            accuracy_score=random.uniform(0.7, 1.0),
            processing_time=random.uniform(1.0, 3.0)
        )
        result.calculate_overall_score()
        
        # Track result
        tracker.track_query(result)
        
        # Complete in queue
        queue.complete_query(
            queued_query.id, 
            result.result_count, 
            result.processing_time
        )
        
        processed_count += 1
    
    print(f"   ✓ Processed {processed_count} queries")
    
    # 6. Analytics and reporting
    print("\n6. Analytics and Reporting...")
    
    # Queue statistics
    final_stats = queue.get_queue_stats()
    print(f"   Queue Status:")
    print(f"     - Pending: {final_stats['pending']}")
    print(f"     - Completed: {final_stats['completed']}")
    print(f"     - Success Rate: {final_stats['success_rate']:.1f}%")
    
    # Tracker analytics
    analytics = tracker.get_analytics(days=1)
    print(f"   Processing Analytics:")
    print(f"     - Total Queries: {analytics.total_queries}")
    print(f"     - Successful: {analytics.successful_queries}")
    print(f"     - Avg Processing Time: {analytics.avg_processing_time:.2f}s")
    print(f"     - Avg Result Count: {analytics.avg_result_count:.1f}")
    print(f"     - Avg Score: {analytics.avg_score:.2f}")
    
    # Top performing queries
    top_queries = tracker.get_top_performing_queries(limit=3)
    print(f"   Top Performing Queries:")
    for i, query_info in enumerate(top_queries, 1):
        print(f"     {i}. {query_info['query'][:50]}...")
        print(f"        Score: {query_info['avg_score']:.2f}, Results: {query_info['avg_results']:.0f}")
    
    # 7. Advanced features demonstration
    print("\n7. Advanced Features...")
    
    # Generate query variations
    variations = generator.generate_variations(
        "business_near_location",
        {"location": "Seattle, WA"},
        {
            "business_type": ["italian restaurant", "sushi restaurant", "steakhouse"]
        }
    )
    print(f"   ✓ Generated {len(variations)} query variations")
    
    # Business category search
    food_categories = business_manager.search_categories("food", limit=5)
    print(f"   ✓ Found {len(food_categories)} food-related categories")
    
    # Location statistics
    location_stats = location_manager.get_location_statistics()
    print(f"   ✓ Location database: {location_stats['total_locations']} locations")
    
    # Template statistics
    template_stats = generator.get_statistics()
    print(f"   ✓ Template engine: {template_stats['total_templates']} templates")
    
    print("\n✅ Demo completed successfully!")
    print("\nKey Features Demonstrated:")
    print("- ✓ Template-based query generation")
    print("- ✓ Multi-engine search support (Bing, Google, DuckDuckGo)")
    print("- ✓ Location and business category management")
    print("- ✓ Priority-based query queuing")
    print("- ✓ Query execution tracking and analytics")
    print("- ✓ Site-specific and location-based searches")
    print("- ✓ Batch processing and query variations")
    

if __name__ == "__main__":
    main()