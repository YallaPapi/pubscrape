#!/usr/bin/env python3
"""
Test Cases for Infinite Scroll Handler
Comprehensive testing for map scrolling functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.infinite_scroll_handler import (
    InfiniteScrollHandler, 
    ScrollConfig, 
    MapScrollSession
)
from scrapers.scroll_strategies import (
    SmoothScrollStrategy,
    ChunkScrollStrategy, 
    AdaptiveScrollStrategy,
    ScrollResult
)
from scrapers.map_extractors import (
    BingMapsExtractor,
    GoogleMapsExtractor,
    BusinessCard
)

class TestScrollConfig(unittest.TestCase):
    """Test ScrollConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ScrollConfig()
        
        self.assertEqual(config.max_scroll_iterations, 20)
        self.assertEqual(config.scroll_pause_time, 2.0)
        self.assertEqual(config.stable_height_count, 3)
        self.assertEqual(config.element_batch_size, 10)
        self.assertEqual(config.timeout_seconds, 300)
        self.assertEqual(config.strategy_type, 'adaptive')
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ScrollConfig(
            max_scroll_iterations=10,
            strategy_type='smooth',
            timeout_seconds=120
        )
        
        self.assertEqual(config.max_scroll_iterations, 10)
        self.assertEqual(config.strategy_type, 'smooth')
        self.assertEqual(config.timeout_seconds, 120)

class TestScrollStrategies(unittest.TestCase):
    """Test scrolling strategies"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_driver = Mock()
        self.mock_driver.run_js = Mock()
        
    def test_smooth_scroll_strategy(self):
        """Test smooth scrolling strategy"""
        strategy = SmoothScrollStrategy(scroll_increment=300, pause_time=1.0)
        
        # Mock page state
        self.mock_driver.run_js.side_effect = [
            500,   # current scroll position
            2000,  # page height  
            800    # viewport height
        ]
        
        with patch('time.sleep'):
            result = strategy.scroll(self.mock_driver, 1)
        
        self.assertTrue(result)
        self.assertEqual(len(strategy.scroll_history), 1)
        self.assertEqual(strategy.total_scrolled, 300)
    
    def test_smooth_scroll_bottom_detection(self):
        """Test smooth scroll bottom detection"""
        strategy = SmoothScrollStrategy()
        
        # Mock at bottom of page
        self.mock_driver.run_js.side_effect = [
            1900,  # current scroll (near bottom)
            2000,  # page height
            800    # viewport height
        ]
        
        result = strategy.scroll(self.mock_driver, 1)
        self.assertFalse(result)  # Should stop scrolling
    
    def test_chunk_scroll_strategy(self):
        """Test chunk-based scrolling strategy"""
        strategy = ChunkScrollStrategy(chunk_size=0.8, wait_time=1.0)
        
        # Mock page state
        self.mock_driver.run_js.side_effect = [
            800,   # viewport height
            500,   # current scroll
            2000,  # page height (pre-scroll)
            2500   # page height (post-scroll)
        ]
        
        with patch('time.sleep'):
            result = strategy.scroll(self.mock_driver, 1)
        
        self.assertTrue(result)
        self.assertEqual(strategy.chunks_scrolled, 1)
    
    def test_adaptive_scroll_strategy(self):
        """Test adaptive scrolling strategy"""
        strategy = AdaptiveScrollStrategy(initial_increment=400)
        
        # Mock page state for successful scroll
        self.mock_driver.run_js.side_effect = [
            500,   # current scroll
            2000,  # page height
            800,   # viewport height
            2000,  # pre-scroll height
            2300   # post-scroll height (new content loaded)
        ]
        
        with patch('time.sleep'):
            result = strategy.scroll(self.mock_driver, 1)
        
        self.assertTrue(result)
        self.assertEqual(strategy.current_increment, 400)
    
    def test_adaptive_scroll_adaptation(self):
        """Test adaptive scroll increment adjustment"""
        strategy = AdaptiveScrollStrategy(adaptation_threshold=2)
        
        # Simulate fast loading iterations
        strategy.fast_loading_iterations = 2
        strategy._adapt_scroll_increment()
        
        # Should increase increment
        self.assertGreater(strategy.current_increment, 400)

class TestMapExtractors(unittest.TestCase):
    """Test map data extractors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_driver = Mock()
        self.bing_extractor = BingMapsExtractor()
        self.google_extractor = GoogleMapsExtractor()
    
    def test_business_card_creation(self):
        """Test BusinessCard creation and conversion"""
        business = BusinessCard(
            name="Test Business",
            address="123 Main St",
            phone="(555) 123-4567",
            email="test@business.com",
            website="https://testbusiness.com",
            rating=4.5,
            source_platform="bing_maps"
        )
        
        business_dict = business.to_dict()
        
        self.assertEqual(business_dict['business_name'], "Test Business")
        self.assertEqual(business_dict['phone'], "(555) 123-4567")
        self.assertEqual(business_dict['source_platform'], "bing_maps")
    
    def test_phone_number_cleaning(self):
        """Test phone number cleaning functionality"""
        extractor = BingMapsExtractor()
        
        # Test various phone formats
        test_cases = [
            ("(555) 123-4567", "(555) 123-4567"),
            ("555-123-4567", "(555) 123-4567"),
            ("555.123.4567", "(555) 123-4567"),
            ("15551234567", "(555) 123-4567"),
            ("5551234567", "(555) 123-4567"),
            ("invalid", None),
            ("123", None)
        ]
        
        for input_phone, expected in test_cases:
            result = extractor._clean_phone_number(input_phone)
            self.assertEqual(result, expected, f"Failed for input: {input_phone}")
    
    def test_email_extraction(self):
        """Test email extraction from text"""
        extractor = BingMapsExtractor()
        
        # Test email extraction
        test_cases = [
            ("Contact us at info@business.com for more info", "info@business.com"),
            ("Email: admin@company.org", "admin@company.org"),
            ("No email here", None),
            ("Fake: example@domain.com", None),  # Should filter fake emails
            ("Multiple: first@test.com and second@test.org", "first@test.com")  # Returns first valid
        ]
        
        for text, expected in test_cases:
            result = extractor._extract_email_from_text(text)
            self.assertEqual(result, expected, f"Failed for text: {text}")
    
    def test_unique_id_generation(self):
        """Test unique ID generation"""
        extractor = BingMapsExtractor()
        
        # Same business should get same ID
        id1 = extractor._generate_unique_id("Test Business", "123 Main St")
        id2 = extractor._generate_unique_id("Test Business", "123 Main St")
        self.assertEqual(id1, id2)
        
        # Different businesses should get different IDs
        id3 = extractor._generate_unique_id("Other Business", "456 Oak Ave")
        self.assertNotEqual(id1, id3)
    
    def test_duplicate_detection(self):
        """Test duplicate business detection"""
        extractor = BingMapsExtractor()
        
        # Add a business ID
        test_id = "test_business_123"
        extractor.extracted_ids.add(test_id)
        
        # Should detect as duplicate
        self.assertTrue(extractor._is_duplicate(test_id))
        self.assertFalse(extractor._is_duplicate("new_business_456"))

class TestInfiniteScrollHandler(unittest.TestCase):
    """Test main infinite scroll handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ScrollConfig(max_scroll_iterations=5, timeout_seconds=30)
        self.handler = InfiniteScrollHandler(self.config)
        self.mock_driver = Mock()
    
    def test_handler_initialization(self):
        """Test handler initialization"""
        self.assertIsNotNone(self.handler.extractors)
        self.assertIsNotNone(self.handler.scroll_strategies)
        self.assertIn('bing', self.handler.extractors)
        self.assertIn('google', self.handler.extractors)
        self.assertIn('adaptive', self.handler.scroll_strategies)
    
    def test_bing_maps_url_building(self):
        """Test Bing Maps URL construction"""
        # Test with location
        url1 = self.handler._build_bing_maps_url("restaurants", "Miami FL")
        self.assertIn("restaurants+in+Miami+FL", url1)
        self.assertIn("bing.com/maps", url1)
        
        # Test without location
        url2 = self.handler._build_bing_maps_url("doctors")
        self.assertIn("doctors", url2)
        self.assertIn("bing.com/maps", url2)
    
    def test_google_maps_url_building(self):
        """Test Google Maps URL construction"""
        # Test with location
        url1 = self.handler._build_google_maps_url("cafes", "Seattle WA")
        self.assertIn("cafes+Seattle+WA", url1)
        self.assertIn("google.com/maps", url1)
        
        # Test without location
        url2 = self.handler._build_google_maps_url("gyms")
        self.assertIn("gyms", url2)
        self.assertIn("google.com/maps", url2)
    
    def test_completion_reason_determination(self):
        """Test scroll completion reason logic"""
        # Test max iterations
        reason1 = self.handler._determine_completion_reason(20, 1, True, 100)
        self.assertEqual(reason1, "max_iterations_reached")
        
        # Test stable height
        reason2 = self.handler._determine_completion_reason(5, 3, True, 100)
        self.assertEqual(reason2, "stable_height_detected")
        
        # Test no new businesses
        reason3 = self.handler._determine_completion_reason(5, 1, False, 100)
        self.assertEqual(reason3, "no_new_businesses")
        
        # Test timeout
        reason4 = self.handler._determine_completion_reason(5, 1, True, 400)
        self.assertEqual(reason4, "timeout_reached")
    
    def test_session_report_creation(self):
        """Test session report generation"""
        # Create mock session
        session = MapScrollSession(
            platform='bing',
            query='test query',
            location='test location',
            config=self.config,
            start_time=datetime.now(),
            extracted_businesses=[
                {'name': 'Business 1', 'email': 'test1@example.com', 'phone': '555-1234'},
                {'name': 'Business 2', 'website': 'https://business2.com'},
                {'name': 'Business 3', 'email': 'test3@example.com', 'phone': '555-5678'}
            ],
            scroll_metrics={'total_iterations': 10}
        )
        
        report = self.handler.create_session_report(session)
        
        # Verify report structure
        self.assertIn('session_info', report)
        self.assertIn('extraction_results', report)
        self.assertIn('scroll_metrics', report)
        self.assertIn('configuration', report)
        
        # Verify statistics
        self.assertEqual(report['extraction_results']['total_businesses'], 3)
        self.assertEqual(report['extraction_results']['businesses_with_email'], 2)
        self.assertEqual(report['extraction_results']['businesses_with_phone'], 2)

class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for complete scroll scenarios"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.handler = InfiniteScrollHandler()
    
    @patch('scrapers.infinite_scroll_handler.browser')
    def test_successful_bing_scroll_session(self, mock_browser):
        """Test complete Bing Maps scroll session"""
        # Mock the browser decorator and driver
        mock_driver = Mock()
        mock_driver.get = Mock()
        mock_driver.sleep = Mock()
        mock_driver.run_js = Mock(return_value=1000)
        mock_driver.page_source = "<div>Mock HTML</div>"
        
        # Mock the decorated function to return the driver
        mock_browser.return_value = lambda func: lambda *args, **kwargs: func(mock_driver, *args, **kwargs)
        
        # Mock extractor methods
        with patch.object(self.handler.extractors['bing'], 'extract_business_cards', return_value=[]):
            with patch.object(self.handler.extractors['bing'], 'extract_all_businesses', return_value=[
                {'name': 'Test Business', 'phone': '555-1234'}
            ]):
                with patch('time.time', return_value=1000):
                    session = self.handler.scroll_and_extract_bing_maps("test query", "test location")
        
        # Verify session results
        self.assertEqual(session.platform, 'bing')
        self.assertEqual(session.query, 'test query')
        self.assertEqual(session.location, 'test location')
    
    def test_factory_function(self):
        """Test scroll handler factory function"""
        from scrapers.infinite_scroll_handler import create_scroll_handler
        
        handler = create_scroll_handler('smooth', 15)
        
        self.assertEqual(handler.config.strategy_type, 'smooth')
        self.assertEqual(handler.config.max_scroll_iterations, 15)

if __name__ == '__main__':
    # Run tests with pytest for better output
    pytest.main([__file__, '-v', '--tb=short'])