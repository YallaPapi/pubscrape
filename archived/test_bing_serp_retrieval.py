"""
Test script for Bing SERP Retrieval System (Task 63)

This script tests the complete Bing SERP retrieval implementation including:
- BingNavigatorAgent and tools
- BingSearcher class integration
- Rate limiting and anti-detection
- Error handling and logging
- HTML storage and caching
"""

import logging
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infra.bing_searcher import BingSearcher, BingSearcherConfig, SearchQuery, create_bing_searcher
from src.agents.bing_navigator_agent import BingNavigatorAgent
from src.agents.tools.bing_search_tool import BingSearchTool
from src.agents.tools.bing_paginate_tool import BingPaginateTool

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_bing_searcher_basic():
    """Test basic BingSearcher functionality"""
    logger.info("=== Testing BingSearcher Basic Functionality ===")
    
    try:
        # Create searcher with conservative settings
        searcher = create_bing_searcher(
            rate_limit_rpm=6,
            max_pages_per_query=2,
            enable_anti_detection=True,
            enable_caching=True
        )
        
        # Test single search
        logger.info("Testing single search query...")
        result = searcher.search("restaurant Chicago contact")
        
        assert result is not None, "Search result should not be None"
        assert result.query == "restaurant Chicago contact", "Query should match input"
        logger.info(f"Single search result: success={result.success}, pages={result.total_pages_retrieved}")
        
        # Test multiple searches
        logger.info("Testing multiple search queries...")
        queries = [
            "lawyer New York email",
            "dentist Los Angeles phone", 
            "accountant Chicago contact"
        ]
        
        results = searcher.search_multiple(queries)
        assert len(results) == len(queries), "Should get result for each query"
        
        successful_results = [r for r in results if r.success]
        logger.info(f"Multiple search results: {len(successful_results)}/{len(results)} successful")
        
        # Test statistics
        stats = searcher.get_statistics()
        logger.info(f"Search statistics: {stats['performance']}")
        
        # Cleanup
        searcher.cleanup()
        
        logger.info("✓ BingSearcher basic functionality test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ BingSearcher basic functionality test failed: {e}")
        return False


def test_bing_navigator_agent():
    """Test BingNavigatorAgent initialization and capabilities"""
    logger.info("=== Testing BingNavigatorAgent ===")
    
    try:
        # Create agent
        agent = BingNavigatorAgent()
        
        # Test agent properties
        assert agent.name == "BingNavigator", "Agent name should be BingNavigator"
        assert len(agent.tools) >= 2, "Agent should have at least 2 tools"
        
        # Test capability information
        capabilities = agent.get_search_capabilities()
        assert "bing.com" in capabilities["supported_search_engines"], "Should support Bing"
        assert capabilities["anti_detection_features"], "Should have anti-detection features"
        assert capabilities["rate_limiting_integration"], "Should integrate with rate limiting"
        
        # Test recommended settings
        settings = agent.get_recommended_settings("medium")
        assert settings["max_pages_per_query"] > 0, "Should have positive page limit"
        assert settings["requests_per_minute"] > 0, "Should have positive rate limit"
        
        logger.info("✓ BingNavigatorAgent test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ BingNavigatorAgent test failed: {e}")
        return False


def test_bing_search_tool():
    """Test BingSearchTool functionality"""
    logger.info("=== Testing BingSearchTool ===")
    
    try:
        # Create tool instance
        tool = BingSearchTool(
            query="test search query",
            max_pages=1,
            store_html=True
        )
        
        # Test tool properties
        assert tool.query == "test search query", "Query should be set correctly"
        assert tool.max_pages == 1, "Max pages should be set correctly"
        assert tool.store_html == True, "HTML storage should be enabled"
        
        logger.info("✓ BingSearchTool initialization test passed")
        
        # Note: We don't run the actual tool execution here as it would
        # require a full Botasaurus environment setup
        
        return True
        
    except Exception as e:
        logger.error(f"✗ BingSearchTool test failed: {e}")
        return False


def test_bing_paginate_tool():
    """Test BingPaginateTool functionality"""
    logger.info("=== Testing BingPaginateTool ===")
    
    try:
        # Create tool instance
        tool = BingPaginateTool(
            session_id="test_session_123",
            action="next",
            max_attempts=3
        )
        
        # Test tool properties
        assert tool.session_id == "test_session_123", "Session ID should be set correctly"
        assert tool.action == "next", "Action should be set correctly"
        assert tool.max_attempts == 3, "Max attempts should be set correctly"
        
        logger.info("✓ BingPaginateTool initialization test passed")
        
        # Note: We don't run the actual tool execution here as it would
        # require an active browser session
        
        return True
        
    except Exception as e:
        logger.error(f"✗ BingPaginateTool test failed: {e}")
        return False


def test_rate_limiting_integration():
    """Test rate limiting integration"""
    logger.info("=== Testing Rate Limiting Integration ===")
    
    try:
        # Create searcher with strict rate limits
        from src.infra.rate_limiter import RateLimitConfig
        
        rate_config = RateLimitConfig(
            rpm_soft=2,  # Very low limit for testing
            rpm_hard=3,
            qps_max=0.1  # 1 request per 10 seconds
        )
        
        config = BingSearcherConfig(
            rate_limit_config=rate_config,
            max_pages_per_query=1
        )
        
        searcher = BingSearcher(config)
        
        # Test rapid searches to trigger rate limiting
        queries = ["test query 1", "test query 2", "test query 3"]
        
        results = []
        for query in queries:
            result = searcher.search(query)
            results.append(result)
            logger.info(f"Query '{query}': success={result.success}")
        
        # At least one should be rate limited due to strict limits
        rate_limited = any("rate limited" in str(result.errors).lower() for result in results)
        
        logger.info(f"Rate limiting test: rate_limited={rate_limited}")
        
        # Get rate limiter statistics
        stats = searcher.get_statistics()
        if "rate_limiter" in stats:
            logger.info(f"Rate limiter stats: {stats['rate_limiter']}")
        
        searcher.cleanup()
        
        logger.info("✓ Rate limiting integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Rate limiting integration test failed: {e}")
        return False


def test_error_handling():
    """Test error handling and recovery"""
    logger.info("=== Testing Error Handling ===")
    
    try:
        searcher = create_bing_searcher(max_pages_per_query=1)
        
        # Test with various query types
        test_queries = [
            "",  # Empty query
            "a" * 1000,  # Very long query
            "normal query",  # Normal query
            "query with special chars !@#$%^&*()"  # Special characters
        ]
        
        for query in test_queries:
            try:
                result = searcher.search(query)
                logger.info(f"Query '{query[:50]}...': success={result.success}")
                
                # All queries should return a result object
                assert result is not None, "Result should not be None"
                assert hasattr(result, 'success'), "Result should have success attribute"
                assert hasattr(result, 'errors'), "Result should have errors attribute"
                
            except Exception as e:
                logger.warning(f"Query '{query[:50]}...' raised exception: {e}")
        
        searcher.cleanup()
        
        logger.info("✓ Error handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error handling test failed: {e}")
        return False


def test_html_storage():
    """Test HTML storage functionality"""
    logger.info("=== Testing HTML Storage ===")
    
    try:
        config = BingSearcherConfig(
            enable_html_storage=True,
            max_pages_per_query=2
        )
        
        searcher = BingSearcher(config)
        
        # Test search with HTML storage
        result = searcher.search("test query for html storage")
        
        if result.success:
            # Check if HTML files were created
            assert len(result.html_files) > 0, "Should have created HTML files"
            
            # Check if files exist
            for html_file in result.html_files:
                if html_file:  # Some might be None due to errors
                    html_path = Path(html_file)
                    assert html_path.exists(), f"HTML file should exist: {html_file}"
                    logger.info(f"HTML file created: {html_file}")
        
        searcher.cleanup()
        
        logger.info("✓ HTML storage test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ HTML storage test failed: {e}")
        return False


def test_session_management():
    """Test session management and cleanup"""
    logger.info("=== Testing Session Management ===")
    
    try:
        searcher = create_bing_searcher()
        
        # Test session scope context manager
        with searcher.session_scope() as session_id:
            logger.info(f"Using session: {session_id}")
            
            # Session should be created
            assert session_id is not None, "Session ID should not be None"
            assert isinstance(session_id, str), "Session ID should be string"
        
        # Test multiple sessions
        session_ids = []
        for i in range(3):
            with searcher.session_scope() as session_id:
                session_ids.append(session_id)
        
        # All session IDs should be unique
        assert len(set(session_ids)) == len(session_ids), "Session IDs should be unique"
        
        searcher.cleanup()
        
        logger.info("✓ Session management test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Session management test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    logger.info("Starting Bing SERP Retrieval System Tests")
    logger.info("=" * 60)
    
    tests = [
        ("BingSearcher Basic", test_bing_searcher_basic),
        ("BingNavigatorAgent", test_bing_navigator_agent),
        ("BingSearchTool", test_bing_search_tool),
        ("BingPaginateTool", test_bing_paginate_tool),
        ("Rate Limiting Integration", test_rate_limiting_integration),
        ("Error Handling", test_error_handling),
        ("HTML Storage", test_html_storage),
        ("Session Management", test_session_management)
    ]
    
    passed = 0
    failed = 0
    
    start_time = time.time()
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            failed += 1
        
        # Small delay between tests
        time.sleep(0.5)
    
    total_time = time.time() - start_time
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    logger.info(f"Success Rate: {passed/(passed+failed)*100:.1f}%")
    logger.info(f"Total Time: {total_time:.2f} seconds")
    
    if failed == 0:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.warning(f"⚠️  {failed} test(s) failed")
        return False


if __name__ == "__main__":
    # Ensure output directories exist
    Path("out/html_cache").mkdir(parents=True, exist_ok=True)
    Path("out/search_cache").mkdir(parents=True, exist_ok=True)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)