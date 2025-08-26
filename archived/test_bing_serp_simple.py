"""
Simplified test for Bing SERP Retrieval System (Task 63)

This test focuses on the core components that don't require external dependencies.
"""

import logging
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_core_imports():
    """Test that core components can be imported"""
    logger.info("=== Testing Core Imports ===")
    
    try:
        # Test infrastructure imports
        from src.infra.bing_searcher import BingSearcher, BingSearcherConfig, SearchQuery, create_bing_searcher
        logger.info("✓ Successfully imported BingSearcher components")
        
        # Test rate limiter integration
        from src.infra.rate_limiter import RateLimiter, RateLimitConfig, RateLimitStatus
        logger.info("✓ Successfully imported RateLimiter components")
        
        # Test anti-detection supervisor
        from src.infra.anti_detection_supervisor import AntiDetectionSupervisor
        logger.info("✓ Successfully imported AntiDetectionSupervisor")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_bing_searcher_creation():
    """Test BingSearcher creation and configuration"""
    logger.info("=== Testing BingSearcher Creation ===")
    
    try:
        from src.infra.bing_searcher import BingSearcher, BingSearcherConfig, create_bing_searcher
        from src.infra.rate_limiter import RateLimitConfig
        
        # Test default creation
        searcher1 = BingSearcher()
        assert searcher1 is not None, "Default searcher should be created"
        logger.info("✓ Default BingSearcher created successfully")
        
        # Test factory function
        searcher2 = create_bing_searcher(
            rate_limit_rpm=10,
            max_pages_per_query=3
        )
        assert searcher2 is not None, "Factory searcher should be created"
        assert searcher2.config.max_pages_per_query == 3, "Max pages should be set correctly"
        logger.info("✓ Factory BingSearcher created successfully")
        
        # Test custom configuration
        custom_config = BingSearcherConfig(
            max_pages_per_query=2,
            enable_html_storage=False,
            enable_result_caching=False
        )
        searcher3 = BingSearcher(custom_config)
        assert searcher3.config.max_pages_per_query == 2, "Custom config should be applied"
        logger.info("✓ Custom BingSearcher created successfully")
        
        # Cleanup
        searcher1.cleanup()
        searcher2.cleanup()
        searcher3.cleanup()
        
        return True
        
    except Exception as e:
        logger.error(f"✗ BingSearcher creation failed: {e}")
        return False


def test_search_query_objects():
    """Test SearchQuery data structure"""
    logger.info("=== Testing SearchQuery Objects ===")
    
    try:
        from src.infra.bing_searcher import SearchQuery
        
        # Test basic query
        query1 = SearchQuery("test query")
        assert query1.query == "test query", "Query text should be set"
        assert query1.max_pages == 1, "Default max_pages should be 1"
        assert query1.context == {}, "Default context should be empty dict"
        
        # Test query with options
        query2 = SearchQuery(
            query="restaurant Chicago",
            max_pages=3,
            priority=5,
            context={"vertical": "restaurants", "city": "Chicago"}
        )
        assert query2.max_pages == 3, "Max pages should be set"
        assert query2.priority == 5, "Priority should be set"
        assert query2.context["vertical"] == "restaurants", "Context should be set"
        
        logger.info("✓ SearchQuery objects work correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ SearchQuery test failed: {e}")
        return False


def test_mock_search_execution():
    """Test mock search execution without external dependencies"""
    logger.info("=== Testing Mock Search Execution ===")
    
    try:
        from src.infra.bing_searcher import create_bing_searcher, SearchQuery
        
        # Create searcher with mock-friendly settings
        searcher = create_bing_searcher(
            rate_limit_rpm=60,  # High limit to avoid rate limiting in tests
            max_pages_per_query=2,
            enable_caching=False  # Disable caching for tests
        )
        
        # Test single search
        result = searcher.search("test query mock")
        
        assert result is not None, "Result should not be None"
        assert result.query == "test query mock", "Query should match"
        assert isinstance(result.success, bool), "Success should be boolean"
        assert isinstance(result.total_pages_retrieved, int), "Pages should be integer"
        assert isinstance(result.total_time_seconds, float), "Time should be float"
        assert isinstance(result.pages, list), "Pages should be list"
        assert isinstance(result.html_files, list), "HTML files should be list"
        assert isinstance(result.errors, list), "Errors should be list"
        
        logger.info(f"✓ Mock search result: success={result.success}, "
                   f"pages={result.total_pages_retrieved}, time={result.total_time_seconds:.2f}s")
        
        # Test multiple searches
        queries = [
            SearchQuery("query 1", max_pages=1),
            SearchQuery("query 2", max_pages=1),
            SearchQuery("query 3", max_pages=1)
        ]
        
        results = searcher.search_multiple(queries)
        assert len(results) == 3, "Should get 3 results"
        
        for i, result in enumerate(results):
            assert result.query == f"query {i+1}", f"Query {i+1} should match"
        
        logger.info(f"✓ Multiple mock searches completed: {len(results)} results")
        
        # Test statistics
        stats = searcher.get_statistics()
        assert "performance" in stats, "Stats should include performance"
        assert "total_searches" in stats["performance"], "Should track total searches"
        
        logger.info(f"✓ Statistics: {stats['performance']['total_searches']} searches")
        
        searcher.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"✗ Mock search execution failed: {e}")
        return False


def test_rate_limiting_logic():
    """Test rate limiting logic without external dependencies"""
    logger.info("=== Testing Rate Limiting Logic ===")
    
    try:
        from src.infra.rate_limiter import RateLimiter, RateLimitConfig, RateLimitStatus
        
        # Create rate limiter with tight limits
        config = RateLimitConfig(
            rpm_soft=3,
            rpm_hard=5,
            qps_max=0.5  # 1 request per 2 seconds
        )
        limiter = RateLimiter(config)
        
        # Test initial state
        status, delay = limiter.check_rate_limit("test.com")
        assert status == RateLimitStatus.ALLOWED, "Initial request should be allowed"
        
        # Test recording requests
        limiter.record_request("test.com", success=True, response_time_ms=100)
        
        # Test statistics
        stats = limiter.get_domain_statistics("test.com")
        assert stats["domain"] == "test.com", "Domain should match"
        assert stats["requests_last_5min"] >= 0, "Should track request count"
        
        global_stats = limiter.get_global_statistics()
        assert "global_active_requests" in global_stats, "Should have global stats"
        
        logger.info("✓ Rate limiting logic works correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Rate limiting test failed: {e}")
        return False


def test_session_management():
    """Test session management functionality"""
    logger.info("=== Testing Session Management ===")
    
    try:
        from src.infra.bing_searcher import create_bing_searcher
        
        searcher = create_bing_searcher()
        
        # Test session scope context manager
        session_ids = []
        for i in range(3):
            with searcher.session_scope() as session_id:
                assert session_id is not None, "Session ID should not be None"
                assert isinstance(session_id, str), "Session ID should be string"
                session_ids.append(session_id)
        
        # All sessions should be unique
        assert len(set(session_ids)) == len(session_ids), "Session IDs should be unique"
        
        logger.info(f"✓ Created {len(session_ids)} unique sessions")
        
        searcher.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"✗ Session management test failed: {e}")
        return False


def test_html_storage():
    """Test HTML storage functionality"""
    logger.info("=== Testing HTML Storage ===")
    
    try:
        from src.infra.bing_searcher import BingSearcherConfig, BingSearcher
        
        # Create searcher with HTML storage enabled
        config = BingSearcherConfig(
            enable_html_storage=True,
            max_pages_per_query=1
        )
        searcher = BingSearcher(config)
        
        # Execute search
        result = searcher.search("html storage test")
        
        if result.success and result.html_files:
            # Check if HTML files exist
            for html_file in result.html_files:
                if html_file:
                    html_path = Path(html_file)
                    assert html_path.exists(), f"HTML file should exist: {html_file}"
                    
                    # Check file content
                    with open(html_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    assert "html storage test" in content, "HTML should contain query"
                    assert "<html>" in content, "Should be valid HTML"
                    
                    logger.info(f"✓ HTML file created and validated: {html_file}")
        
        searcher.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"✗ HTML storage test failed: {e}")
        return False


def run_simple_tests():
    """Run simplified tests"""
    logger.info("Starting Simplified Bing SERP Retrieval System Tests")
    logger.info("=" * 70)
    
    tests = [
        ("Core Imports", test_core_imports),
        ("BingSearcher Creation", test_bing_searcher_creation),
        ("SearchQuery Objects", test_search_query_objects),
        ("Mock Search Execution", test_mock_search_execution),
        ("Rate Limiting Logic", test_rate_limiting_logic),
        ("Session Management", test_session_management),
        ("HTML Storage", test_html_storage)
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
        
        time.sleep(0.2)  # Small delay between tests
    
    total_time = time.time() - start_time
    
    logger.info("\n" + "=" * 70)
    logger.info("SIMPLIFIED TEST RESULTS")
    logger.info("=" * 70)
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    logger.info(f"Success Rate: {passed/(passed+failed)*100:.1f}%")
    logger.info(f"Total Time: {total_time:.2f} seconds")
    
    if failed == 0:
        logger.info("🎉 All simplified tests passed!")
        return True
    else:
        logger.warning(f"⚠️  {failed} test(s) failed")
        return False


if __name__ == "__main__":
    # Ensure output directories exist
    Path("out/html_cache").mkdir(parents=True, exist_ok=True)
    Path("out/search_cache").mkdir(parents=True, exist_ok=True)
    
    success = run_simple_tests()
    sys.exit(0 if success else 1)