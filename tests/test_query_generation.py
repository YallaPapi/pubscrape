"""
Test suite for query generation system

Tests:
- Query template engine
- Location manager functionality
- Business category management
- Query queue operations
- Query tracking and analytics
"""
import pytest
import tempfile
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import modules to test
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from queries.query_generator import (
    QueryGenerator, QueryTemplate, GeneratedQuery, SearchEngine,
    create_business_query, create_site_search
)
from queries.location_manager import (
    LocationManager, Location, Region, create_us_cities_manager
)
from queries.business_categories import (
    BusinessCategoryManager, BusinessCategory, BusinessType, BusinessTier,
    create_default_manager
)
from queries.query_queue import (
    QueryQueue, QueuedQuery, QueryStatus, QueuePriority, RateLimitRule,
    create_search_queue
)
from queries.query_tracker import (
    QueryTracker, QueryResult, QueryAnalytics, create_tracker
)


class TestQueryGenerator:
    """Test query generator functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = QueryGenerator()
    
    def test_add_template(self):
        """Test adding custom templates"""
        template = QueryTemplate(
            name="test_template",
            template="{business} in {city}",
            variables={"business", "city"},
            engine=SearchEngine.GOOGLE_WEB,
            description="Test template"
        )
        
        self.generator.add_template(template)
        
        retrieved = self.generator.get_template("test_template")
        assert retrieved is not None
        assert retrieved.name == "test_template"
        assert retrieved.template == "{business} in {city}"
    
    def test_generate_query(self):
        """Test query generation from template"""
        variables = {
            "business_type": "restaurants",
            "location": "Seattle, WA"
        }
        
        query = self.generator.generate_query(
            "business_near_location", 
            variables
        )
        
        assert isinstance(query, GeneratedQuery)
        assert "restaurants" in query.query
        assert "Seattle" in query.query
        assert query.engine == SearchEngine.BING_MAPS
        assert query.variables == variables
    
    def test_generate_batch(self):
        """Test batch query generation"""
        variable_sets = [
            {"business_type": "restaurants", "location": "Seattle, WA"},
            {"business_type": "cafes", "location": "Portland, OR"},
            {"business_type": "bars", "location": "San Francisco, CA"}
        ]
        
        queries = self.generator.generate_batch(
            "business_near_location", 
            variable_sets
        )
        
        assert len(queries) == 3
        assert all(isinstance(q, GeneratedQuery) for q in queries)
        assert queries[0].variables["business_type"] == "restaurants"
        assert queries[1].variables["location"] == "Portland, OR"
    
    def test_generate_variations(self):
        """Test query variation generation"""
        base_variables = {"location": "Seattle, WA"}
        variations = {
            "business_type": ["restaurants", "cafes", "bars"]
        }
        
        queries = self.generator.generate_variations(
            "business_near_location",
            base_variables,
            variations
        )
        
        assert len(queries) == 3
        business_types = [q.variables["business_type"] for q in queries]
        assert "restaurants" in business_types
        assert "cafes" in business_types
        assert "bars" in business_types
    
    def test_validate_query(self):
        """Test query validation"""
        # Valid query
        result = self.generator.validate_query(
            "restaurants near Seattle",
            SearchEngine.BING_WEB
        )
        assert result['valid'] is True
        assert len(result['errors']) == 0
        
        # Too long query
        long_query = "x" * 1000
        result = self.generator.validate_query(
            long_query,
            SearchEngine.BING_WEB
        )
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_missing_variables(self):
        """Test handling of missing variables"""
        with pytest.raises(ValueError, match="Missing required variables"):
            self.generator.generate_query(
                "business_near_location",
                {"business_type": "restaurants"}  # Missing location
            )
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        # Test business query creation
        query = create_business_query("pizza", "New York")
        assert "pizza" in query.query
        assert "New York" in query.query
        
        # Test site search creation
        site_query = create_site_search("yelp.com", "restaurants")
        assert "site:yelp.com" in site_query.query
        assert "restaurants" in site_query.query


class TestLocationManager:
    """Test location manager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = LocationManager()
    
    def test_add_location(self):
        """Test adding locations"""
        location = Location(
            name="Seattle",
            city="Seattle",
            state="Washington",
            country="US",
            latitude=47.6062,
            longitude=-122.3321,
            population=737015
        )
        
        self.manager.add_location(location)
        
        # Test retrieval
        found = self.manager.find_location("Seattle")
        assert found is not None
        assert found.city == "Seattle"
        assert found.state == "Washington"
    
    def test_search_locations(self):
        """Test location search"""
        # Add test locations
        locations = [
            Location("Seattle", "Seattle", "Washington", "US"),
            Location("Portland", "Portland", "Oregon", "US"),
            Location("New York", "New York", "New York", "US")
        ]
        
        for loc in locations:
            self.manager.add_location(loc)
        
        # Search for locations
        results = self.manager.search_locations("seattle")
        assert len(results) >= 1
        assert any(loc.city == "Seattle" for loc in results)
    
    def test_locations_by_state(self):
        """Test getting locations by state"""
        locations = [
            Location("Seattle", "Seattle", "Washington", "US"),
            Location("Spokane", "Spokane", "Washington", "US"),
            Location("Portland", "Portland", "Oregon", "US")
        ]
        
        for loc in locations:
            self.manager.add_location(loc)
        
        wa_locations = self.manager.get_locations_by_state("Washington")
        assert len(wa_locations) == 2
        assert all(loc.state == "Washington" for loc in wa_locations)
    
    def test_distance_calculation(self):
        """Test distance calculations"""
        seattle = Location(
            "Seattle", "Seattle", "Washington", "US",
            latitude=47.6062, longitude=-122.3321
        )
        portland = Location(
            "Portland", "Portland", "Oregon", "US",
            latitude=45.5152, longitude=-122.6784
        )
        
        distance = seattle.distance_to(portland)
        assert distance is not None
        assert 200 < distance < 300  # Approximate distance in km
    
    def test_location_variations(self):
        """Test location variation generation"""
        location = Location(
            "Seattle", "Seattle", "Washington", "US"
        )
        
        variations = self.manager.create_location_variations(location)
        
        assert "Seattle" in variations
        assert "Seattle, Washington" in variations
        assert "Seattle, WA" in variations
    
    def test_csv_loading(self):
        """Test loading locations from CSV"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['city', 'state', 'country', 'latitude', 'longitude', 'population'])
            writer.writerow(['Seattle', 'Washington', 'US', '47.6062', '-122.3321', '737015'])
            writer.writerow(['Portland', 'Oregon', 'US', '45.5152', '-122.6784', '647805'])
            csv_path = f.name
        
        try:
            # Test loading
            manager = LocationManager(str(Path(csv_path).parent))
            manager.load_from_csv(Path(csv_path).name)
            
            # Verify locations loaded
            stats = manager.get_location_statistics()
            assert stats['total_locations'] >= 2
            
            seattle = manager.find_location("Seattle")
            assert seattle is not None
            assert seattle.population == 737015
            
        finally:
            Path(csv_path).unlink()


class TestBusinessCategoryManager:
    """Test business category manager functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = BusinessCategoryManager()
    
    def test_search_categories(self):
        """Test category search"""
        results = self.manager.search_categories("food")
        assert len(results) > 0
        
        # Should find restaurant-related categories
        category_names = [cat.name for cat in results]
        assert any("restaurant" in name for name in category_names)
    
    def test_search_types(self):
        """Test business type search"""
        results = self.manager.search_types("pizza")
        assert len(results) > 0
        
        # Should find pizza-related types
        type_names = [btype.name for btype in results]
        assert any("pizza" in name for name in type_names)
    
    def test_generate_search_terms(self):
        """Test search term generation"""
        terms = self.manager.generate_search_terms("restaurant")
        
        assert "restaurant" in terms
        assert len(terms) > 1  # Should generate variations
        
        # Check for common restaurant-related terms
        terms_lower = [term.lower() for term in terms]
        assert any("dining" in term for term in terms_lower)
    
    def test_category_hierarchy(self):
        """Test category hierarchy"""
        # Get a subcategory
        cafes = self.manager.get_category("cafes")
        if cafes and cafes.parent:
            hierarchy = self.manager.get_category_hierarchy("cafes")
            assert len(hierarchy) >= 2  # At least cafes and its parent
            assert hierarchy[-1].name == "cafes"  # Last item should be cafes
    
    def test_tier_filtering(self):
        """Test filtering by business tier"""
        small_categories = self.manager.get_categories_by_tier(BusinessTier.SMALL)
        assert len(small_categories) > 0
        assert all(cat.tier == BusinessTier.SMALL for cat in small_categories)
    
    def test_types_in_category(self):
        """Test getting types in category"""
        restaurant_types = self.manager.get_types_in_category("restaurants")
        assert len(restaurant_types) > 0
        
        # All should be restaurant-related
        assert all(btype.category == "restaurants" for btype in restaurant_types)


class TestQueryQueue:
    """Test query queue functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.queue = QueryQueue()
    
    def test_add_query(self):
        """Test adding queries to queue"""
        query_id = self.queue.add_query(
            query="restaurants near Seattle",
            engine="bing",
            priority=QueuePriority.HIGH,
            category="restaurants",
            location="Seattle, WA"
        )
        
        assert query_id is not None
        
        stats = self.queue.get_queue_stats()
        assert stats['pending'] == 1
        assert stats['total_added'] == 1
    
    def test_get_next_query(self):
        """Test retrieving next query"""
        # Add queries with different priorities
        high_id = self.queue.add_query(
            "urgent query", "bing", QueuePriority.URGENT
        )
        low_id = self.queue.add_query(
            "low priority query", "bing", QueuePriority.LOW
        )
        
        # Should get urgent query first
        next_query = self.queue.get_next_query()
        assert next_query is not None
        assert next_query.id == high_id
        assert next_query.priority == QueuePriority.URGENT
    
    def test_complete_query(self):
        """Test completing queries"""
        query_id = self.queue.add_query("test query", "bing")
        
        # Get and complete query
        next_query = self.queue.get_next_query()
        assert next_query.id == query_id
        
        self.queue.complete_query(query_id, result_count=25, processing_time=1.5)
        
        stats = self.queue.get_queue_stats()
        assert stats['completed'] == 1
        assert stats['processing'] == 0
    
    def test_fail_query(self):
        """Test failing queries"""
        query_id = self.queue.add_query("test query", "bing")
        
        # Get query
        next_query = self.queue.get_next_query()
        
        # Fail it
        self.queue.fail_query(query_id, "Test error", retry=False)
        
        stats = self.queue.get_queue_stats()
        assert stats['failed'] == 1
        assert stats['processing'] == 0
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Add rate limit rule
        rule = RateLimitRule(
            group="test",
            max_requests=2,
            time_window=timedelta(minutes=1)
        )
        self.queue.add_rate_limit(rule)
        
        # Add queries
        for i in range(3):
            self.queue.add_query(
                f"query {i}", "bing", 
                rate_limit_group="test"
            )
        
        # Should be able to get first two queries
        query1 = self.queue.get_next_query()
        query2 = self.queue.get_next_query()
        query3 = self.queue.get_next_query()  # Should be None due to rate limit
        
        assert query1 is not None
        assert query2 is not None
        assert query3 is None
    
    def test_duplicate_filtering(self):
        """Test duplicate query filtering"""
        # Add same query twice
        id1 = self.queue.add_query("duplicate query", "bing", check_duplicates=True)
        id2 = self.queue.add_query("duplicate query", "bing", check_duplicates=True)
        
        assert id1 is not None
        assert id2 is None  # Should be filtered as duplicate
        
        stats = self.queue.get_queue_stats()
        assert stats['total_added'] == 1
        assert stats['duplicates_filtered'] == 1
    
    def test_batch_add(self):
        """Test batch query addition"""
        queries = [
            {"query": "query 1", "engine": "bing"},
            {"query": "query 2", "engine": "google"},
            {"query": "query 3", "engine": "duckduckgo"}
        ]
        
        added_ids = self.queue.add_batch(queries)
        
        assert len(added_ids) == 3
        
        stats = self.queue.get_queue_stats()
        assert stats['pending'] == 3


class TestQueryTracker:
    """Test query tracker functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Use temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.tracker = QueryTracker(self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        Path(self.temp_db.name).unlink(missing_ok=True)
    
    def test_track_query(self):
        """Test tracking query results"""
        result = QueryResult(
            query_id="test-123",
            query="restaurants near Seattle",
            engine="bing",
            location="Seattle, WA",
            category="restaurants",
            result_count=45,
            relevance_score=0.8,
            processing_time=2.5
        )
        
        success = self.tracker.track_query(result)
        assert success is True
        
        # Retrieve result
        retrieved = self.tracker.get_query_result("test-123")
        assert retrieved is not None
        assert retrieved.query == "restaurants near Seattle"
        assert retrieved.result_count == 45
    
    def test_duplicate_detection(self):
        """Test duplicate query detection"""
        # Track first query
        result1 = QueryResult(
            query_id="test-1",
            query="restaurants near Seattle",
            engine="bing",
            location="Seattle, WA"
        )
        
        success1 = self.tracker.track_query(result1)
        assert success1 is True
        
        # Try to track duplicate
        result2 = QueryResult(
            query_id="test-2",
            query="restaurants near Seattle",  # Same query
            engine="bing",
            location="Seattle, WA"
        )
        
        success2 = self.tracker.track_query(result2)
        assert success2 is False  # Should be rejected as duplicate
    
    def test_query_history(self):
        """Test query history retrieval"""
        # Track multiple queries
        for i in range(5):
            result = QueryResult(
                query_id=f"test-{i}",
                query=f"query {i}",
                engine="bing"
            )
            self.tracker.track_query(result)
        
        # Get history
        history = self.tracker.get_query_history(limit=3)
        assert len(history) == 3
        
        # Should be in reverse chronological order
        assert history[0].query_id == "test-4"  # Most recent
    
    def test_analytics(self):
        """Test analytics calculation"""
        # Track some queries with different outcomes
        successful = QueryResult(
            query_id="success-1",
            query="successful query",
            engine="bing",
            result_count=50,
            overall_score=0.8,
            processing_time=1.0,
            status="completed"
        )
        
        failed = QueryResult(
            query_id="failed-1",
            query="failed query",
            engine="bing",
            result_count=0,
            overall_score=0.0,
            processing_time=2.0,
            status="failed"
        )
        
        self.tracker.track_query(successful)
        self.tracker.track_query(failed)
        
        # Get analytics
        analytics = self.tracker.get_analytics(days=1)
        
        assert analytics.total_queries == 2
        assert analytics.successful_queries == 1
        assert analytics.failed_queries == 1
        assert analytics.avg_processing_time == 1.5  # Average of 1.0 and 2.0
    
    def test_top_performing_queries(self):
        """Test top performing query identification"""
        # Add queries with different performance
        high_performer = QueryResult(
            query_id="high-1",
            query="high performing query",
            engine="bing",
            result_count=100,
            overall_score=0.9,
            status="completed"
        )
        
        low_performer = QueryResult(
            query_id="low-1",
            query="low performing query",
            engine="bing",
            result_count=5,
            overall_score=0.2,
            status="completed"
        )
        
        self.tracker.track_query(high_performer)
        self.tracker.track_query(low_performer)
        
        # Get top performers
        top_queries = self.tracker.get_top_performing_queries(limit=1)
        assert len(top_queries) == 1
        assert top_queries[0]['query'] == "high performing query"
    
    def test_business_results_tracking(self):
        """Test tracking business results"""
        businesses = [
            {
                'name': 'Test Restaurant',
                'address': '123 Main St',
                'phone': '555-1234',
                'website': 'https://test.com',
                'rating': 4.5,
                'review_count': 100
            }
        ]
        
        result = QueryResult(
            query_id="business-test",
            query="restaurants",
            engine="bing",
            businesses_found=businesses
        )
        
        self.tracker.track_query(result)
        
        # Retrieve and verify business data was stored
        retrieved = self.tracker.get_query_result("business-test")
        assert len(retrieved.businesses_found) == 1
        assert retrieved.businesses_found[0]['name'] == 'Test Restaurant'


class TestIntegration:
    """Integration tests combining multiple components"""
    
    def test_end_to_end_query_workflow(self):
        """Test complete query workflow from generation to tracking"""
        # Set up components
        generator = QueryGenerator()
        queue = QueryQueue()
        tracker = QueryTracker(":memory:")  # In-memory database
        
        # Generate queries
        variable_sets = [
            {"business_type": "restaurants", "location": "Seattle, WA"},
            {"business_type": "cafes", "location": "Portland, OR"}
        ]
        
        generated_queries = generator.generate_batch(
            "business_near_location",
            variable_sets
        )
        
        # Add to queue
        for gq in generated_queries:
            queue.add_query(
                query=gq.query,
                engine=gq.engine.value,
                category=gq.variables.get("business_type"),
                location=gq.variables.get("location")
            )
        
        # Process queries
        while True:
            queued_query = queue.get_next_query()
            if not queued_query:
                break
            
            # Simulate processing
            result = QueryResult(
                query_id=queued_query.id,
                query=queued_query.query,
                engine=queued_query.engine,
                location=queued_query.location,
                category=queued_query.category,
                result_count=25,
                processing_time=1.0,
                overall_score=0.7
            )
            
            # Track result
            tracker.track_query(result)
            
            # Complete in queue
            queue.complete_query(queued_query.id, 25, 1.0)
        
        # Verify end-to-end workflow
        queue_stats = queue.get_queue_stats()
        assert queue_stats['completed'] == 2
        assert queue_stats['pending'] == 0
        
        analytics = tracker.get_analytics(days=1)
        assert analytics.total_queries == 2
        assert analytics.successful_queries == 2
    
    def test_location_business_query_generation(self):
        """Test generating queries for multiple locations and business types"""
        # Set up managers
        location_manager = LocationManager()
        business_manager = BusinessCategoryManager()
        generator = QueryGenerator()
        
        # Add test data
        locations = [
            Location("Seattle", "Seattle", "Washington", "US"),
            Location("Portland", "Portland", "Oregon", "US")
        ]
        for loc in locations:
            location_manager.add_location(loc)
        
        # Generate queries for all combinations
        business_types = ["restaurants", "cafes", "bars"]
        all_queries = []
        
        for location in locations:
            for business_type in business_types:
                # Generate location variations
                location_variations = location_manager.create_location_variations(location)
                
                # Generate business term variations
                business_terms = business_manager.generate_search_terms(business_type)
                
                # Create queries for each combination
                for loc_var in location_variations[:2]:  # Limit variations
                    for bus_term in business_terms[:2]:  # Limit variations
                        query = generator.generate_query(
                            "business_near_location",
                            {"business_type": bus_term, "location": loc_var}
                        )
                        all_queries.append(query)
        
        # Should have generated multiple query variations
        assert len(all_queries) > 0
        
        # Verify query diversity
        unique_queries = set(q.query for q in all_queries)
        assert len(unique_queries) > 1  # Should have variations


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])