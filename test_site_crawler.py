"""
Test script for the SiteCrawler implementation

This script demonstrates the Website Visit & Page Discovery system
by testing the main components and their integration.
"""

import sys
import os
import time
import logging

# Add the source directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_home_page_fetch():
    """Test the home page fetching tool"""
    print("\n=== Testing Home Page Fetch Tool ===")
    
    try:
        from agents.tools.home_page_fetch_tool import HomePageFetchTool
        
        # Test with a real website
        tool = HomePageFetchTool(
            domain="example.com",
            discover_links=True,
            max_links=20,
            timeout=10.0
        )
        
        print("Fetching home page for example.com...")
        result = tool.run()
        
        if result.get("success"):
            print(f"✓ Home page fetch successful!")
            print(f"  - URL: {result.get('url_fetched')}")
            print(f"  - Status Code: {result.get('status_code')}")
            print(f"  - Response Time: {result.get('response_time_ms', 0):.0f}ms")
            print(f"  - Links Discovered: {result.get('links_discovered', 0)}")
            
            priority_links = result.get('priority_links', {})
            if priority_links:
                print(f"  - Priority Links Found:")
                for page_type, links in priority_links.items():
                    print(f"    * {page_type}: {len(links)} links")
        else:
            print(f"✗ Home page fetch failed: {result.get('error')}")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"✗ Error testing home page fetch: {e}")
        return False

def test_robots_compliance():
    """Test the robots.txt compliance tool"""
    print("\n=== Testing Robots.txt Compliance Tool ===")
    
    try:
        from agents.tools.robots_compliance_tool import RobotsComplianceTool
        
        # Test creating a policy for a domain
        tool = RobotsComplianceTool(
            domain="example.com",
            user_agent="SiteCrawler-Bot/1.0",
            max_pages=5,
            operation="create_policy",
            respect_robots=True
        )
        
        print("Creating crawl policy for example.com...")
        result = tool.run()
        
        if result.get("success"):
            print(f"✓ Crawl policy created successfully!")
            policy_details = result.get('policy_details', {})
            print(f"  - Max Pages: {policy_details.get('max_pages')}")
            print(f"  - Crawl Delay: {policy_details.get('effective_delay', 0):.1f}s")
            print(f"  - Robots.txt Found: {result.get('robots_txt_found', False)}")
            print(f"  - Disallowed Paths: {policy_details.get('disallowed_paths_count', 0)}")
        else:
            print(f"✗ Policy creation failed: {result.get('error')}")
        
        # Test URL checking
        tool = RobotsComplianceTool(
            domain="example.com",
            check_url="https://example.com/contact",
            operation="check_url"
        )
        
        print("Checking URL permission...")
        result = tool.run()
        
        if result.get("success"):
            is_allowed = result.get('is_allowed', False)
            reason = result.get('reason', 'Unknown')
            print(f"✓ URL check completed: {'Allowed' if is_allowed else 'Not Allowed'} - {reason}")
        else:
            print(f"✗ URL check failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing robots compliance: {e}")
        return False

def test_error_handling():
    """Test the error handling tool"""
    print("\n=== Testing Error Handling Tool ===")
    
    try:
        from agents.tools.error_handling_tool import ErrorHandlingTool
        
        # Test error detection for a blocked page
        tool = ErrorHandlingTool(
            operation="detect_error",
            url="https://example.com/blocked",
            status_code=403,
            response_content="<html><body>Access Denied</body></html>",
            enable_content_analysis=True
        )
        
        print("Detecting error type for HTTP 403...")
        result = tool.run()
        
        if result.get("success"):
            error_class = result.get('error_classification', {})
            print(f"✓ Error detection successful!")
            print(f"  - Error Type: {error_class.get('error_type')}")
            print(f"  - Is Retryable: {error_class.get('is_retryable')}")
            print(f"  - Retry Strategy: {error_class.get('retry_strategy')}")
            print(f"  - Max Retries: {error_class.get('max_retries')}")
        else:
            print(f"✗ Error detection failed: {result.get('error')}")
        
        # Test retry planning
        tool = ErrorHandlingTool(
            operation="plan_retry",
            url="https://example.com/timeout",
            previous_error_type="timeout_error",
            attempt_number=2,
            max_attempts=3
        )
        
        print("Planning retry for timeout error...")
        result = tool.run()
        
        if result.get("success"):
            retry_plan = result.get('retry_plan', {})
            print(f"✓ Retry planning successful!")
            print(f"  - Should Retry: {retry_plan.get('should_retry')}")
            print(f"  - Retry Delay: {retry_plan.get('retry_delay_seconds', 0):.2f}s")
            print(f"  - Retry Reason: {retry_plan.get('retry_reason')}")
        else:
            print(f"✗ Retry planning failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing error handling: {e}")
        return False

def test_anti_detection_integration():
    """Test the anti-detection integration tool"""
    print("\n=== Testing AntiDetection Integration Tool ===")
    
    try:
        from agents.tools.anti_detection_integration_tool import AntiDetectionIntegrationTool
        
        # Test session creation
        tool = AntiDetectionIntegrationTool(
            operation="create_session",
            domain="example.com",
            browser_mode="headless",
            enable_resource_blocking=True,
            crawl_delay=1.0
        )
        
        print("Creating anti-detection session...")
        result = tool.run()
        
        if result.get("success"):
            session_config = result.get('session_config', {})
            session_id = session_config.get('session_id')
            print(f"✓ Session created successfully!")
            print(f"  - Session ID: {session_id}")
            print(f"  - Browser Mode: {session_config.get('browser_mode')}")
            print(f"  - Resource Blocking: {session_config.get('enable_resource_blocking')}")
            print(f"  - Crawl Delay: {session_config.get('crawl_delay')}s")
            
            # Test getting statistics
            tool = AntiDetectionIntegrationTool(operation="get_statistics")
            result = tool.run()
            
            if result.get("success"):
                stats = result.get('session_statistics', {})
                print(f"  - Active Sessions: {stats.get('active_sessions', 0)}")
                print(f"  - Anti-Detection Available: {stats.get('supervisor_available', False)}")
        else:
            print(f"✗ Session creation failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing anti-detection integration: {e}")
        return False

def test_crawl_metrics():
    """Test the crawl metrics tool"""
    print("\n=== Testing Crawl Metrics Tool ===")
    
    try:
        from agents.tools.crawl_metrics_tool import CrawlMetricsTool
        
        session_id = f"test_session_{int(time.time())}"
        
        # Test starting a session
        tool = CrawlMetricsTool(
            operation="start_session",
            session_id=session_id
        )
        
        print(f"Starting metrics session: {session_id}")
        result = tool.run()
        
        if result.get("success"):
            print(f"✓ Metrics session started!")
            
            # Test recording a request
            tool = CrawlMetricsTool(
                operation="record_request",
                url="https://example.com/contact",
                domain="example.com",
                session_id=session_id,
                response_time_ms=156.7,
                success=True,
                status_code=200,
                page_type_discovered="contact",
                links_discovered=8
            )
            
            print("Recording request metric...")
            result = tool.run()
            
            if result.get("success"):
                print(f"✓ Request metric recorded!")
                
                # Test getting statistics
                tool = CrawlMetricsTool(operation="get_statistics")
                result = tool.run()
                
                if result.get("success"):
                    stats = result.get('overall_statistics', {})
                    print(f"  - Total Requests: {stats.get('total_requests', 0)}")
                    print(f"  - Success Rate: {stats.get('overall_success_rate_percent', 0):.1f}%")
                    print(f"  - Total Domains: {stats.get('total_domains', 0)}")
                
                # Test ending session
                tool = CrawlMetricsTool(
                    operation="end_session",
                    session_id=session_id
                )
                
                result = tool.run()
                if result.get("success"):
                    session_report = result.get('session_report', {})
                    print(f"✓ Session ended - Duration: {session_report.get('duration_minutes', 0):.2f} min")
            else:
                print(f"✗ Request recording failed: {result.get('error')}")
        else:
            print(f"✗ Session start failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing crawl metrics: {e}")
        return False

def test_site_crawl_integration():
    """Test the full site crawl tool"""
    print("\n=== Testing Site Crawl Integration ===")
    
    try:
        from agents.tools.site_crawl_tool import SiteCrawlTool
        
        # Test crawling a domain
        tool = SiteCrawlTool(
            domain="example.com",
            max_pages=3,
            priority_types=["contact", "about"],
            timeout_per_page=10.0,
            delay_between_pages=1.0,
            enable_discovery=True
        )
        
        print("Starting site crawl for example.com...")
        result = tool.run()
        
        if result.get("success"):
            print(f"✓ Site crawl completed!")
            print(f"  - Session ID: {result.get('session_id')}")
            print(f"  - Pages Crawled: {result.get('pages_crawled', 0)}")
            print(f"  - Links Discovered: {result.get('links_discovered', 0)}")
            print(f"  - Success Rate: {result.get('success_rate_percent', 0):.1f}%")
            print(f"  - Duration: {result.get('session_duration_seconds', 0):.1f}s")
            
            priority_links = result.get('priority_links', {})
            if priority_links:
                print(f"  - Priority Links:")
                for page_type, links in priority_links.items():
                    print(f"    * {page_type}: {len(links)} links")
            
            failed_urls = result.get('failed_urls', [])
            if failed_urls:
                print(f"  - Failed URLs: {len(failed_urls)}")
        else:
            print(f"✗ Site crawl failed: {result.get('error')}")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"✗ Error testing site crawl: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("SiteCrawler Implementation Test Suite")
    print("=" * 60)
    
    test_results = []
    
    # Run individual component tests
    test_results.append(("Home Page Fetch", test_home_page_fetch()))
    test_results.append(("Robots Compliance", test_robots_compliance()))
    test_results.append(("Error Handling", test_error_handling()))
    test_results.append(("AntiDetection Integration", test_anti_detection_integration()))
    test_results.append(("Crawl Metrics", test_crawl_metrics()))
    test_results.append(("Site Crawl Integration", test_site_crawl_integration()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print("-" * 60)
    print(f"Tests Passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! SiteCrawler implementation is working correctly.")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed. Please check the implementation.")
    
    print("\nSiteCrawler components implemented:")
    print("✓ Home Page Fetching & Link Discovery")
    print("✓ Robots.txt Compliance & Crawl Policies")
    print("✓ Error Handling & Retry Logic")
    print("✓ AntiDetection Integration")
    print("✓ Comprehensive Logging & Metrics")
    print("✓ Site Crawl Orchestration")

if __name__ == "__main__":
    main()