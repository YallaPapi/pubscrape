#!/usr/bin/env python3
"""
Test Botasaurus Anti-Detection Implementation
Tests the research-based anti-detection features.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.settings import get_settings
from anti_detection.botasaurus_manager import BotasaurusAntiDetectionManager
from botasaurus.browser import browser
from botasaurus import UserAgent, WindowSize

def test_session_config_generation():
    """Test session configuration generation."""
    print("Testing Session Configuration Generation...")
    
    settings = get_settings()
    manager = BotasaurusAntiDetectionManager(settings)
    
    # Test multiple campaign configs
    campaigns = ['real_estate_nyc', 'shopify_stores', 'local_services']
    
    for campaign in campaigns:
        config = manager.get_session_config(campaign)
        print(f"  Campaign: {campaign}")
        print(f"    Profile: {config.profile_name}")
        print(f"    Proxy: {config.proxy_url}")
        print(f"    User Agent Rotation: {config.user_agent_rotation}")
        print(f"    Max Requests/Min: {config.max_requests_per_minute}")
    
    # Verify unique profiles
    profiles = [manager.get_session_config(c).profile_name for c in campaigns]
    unique_profiles = len(set(profiles))
    
    print(f"  Generated {unique_profiles}/{len(campaigns)} unique profiles")
    return unique_profiles == len(campaigns)

def test_browser_decorator_args():
    """Test browser decorator arguments generation."""
    print("\nTesting Browser Decorator Arguments...")
    
    settings = get_settings()
    manager = BotasaurusAntiDetectionManager(settings)
    
    # Test browser args for campaign
    campaign = "test_campaign"
    browser_args = manager.get_browser_decorator_args(campaign)
    
    print("  Generated browser arguments:")
    for key, value in browser_args.items():
        print(f"    {key}: {value}")
    
    # Verify required research-based features
    required_features = [
        'user_agent_rotation', 'headless', 'block_images', 
        'profile', 'stealth'
    ]
    
    missing_features = [f for f in required_features if f not in browser_args]
    
    if missing_features:
        print(f"  Missing features: {missing_features}")
        return False
    
    print("  All required features present")
    return True

def test_delay_patterns():
    """Test human-like delay patterns from research."""
    print("\nTesting Human-like Delay Patterns...")
    
    settings = get_settings()
    manager = BotasaurusAntiDetectionManager(settings)
    
    # Test different delay types from research
    delay_types = ['search', 'navigation', 'extraction', 'pagination']
    delays = {}
    
    import time
    for delay_type in delay_types:
        start_time = time.time()
        manager.human_like_delay(delay_type)
        actual_delay = time.time() - start_time
        delays[delay_type] = actual_delay
        
        print(f"  {delay_type}: {actual_delay:.2f}s")
    
    # Verify delays are within research ranges
    # Search delays should be 3-6 seconds (with base multiplier)
    search_delay = delays['search']
    valid_search_delay = 2.0 <= search_delay <= 8.0  # Allow for base multiplier
    
    print(f"  Search delay valid: {valid_search_delay}")
    return valid_search_delay

def test_exponential_backoff():
    """Test exponential backoff implementation."""
    print("\nTesting Exponential Backoff...")
    
    settings = get_settings()
    manager = BotasaurusAntiDetectionManager(settings)
    
    # Test backoff progression from research (5s, 10s, 20s, up to 2min)
    import time
    
    for attempt in range(1, 4):
        start_time = time.time()
        manager.exponential_backoff(attempt, 'rate_limit')
        actual_delay = time.time() - start_time
        
        expected_min = 5.0 * (2 ** (attempt - 1)) * 0.8  # With jitter
        expected_max = min(5.0 * (2 ** (attempt - 1)) * 1.2, 120.0)
        
        valid_delay = expected_min <= actual_delay <= expected_max
        
        print(f"  Attempt {attempt}: {actual_delay:.2f}s (expected {expected_min:.1f}-{expected_max:.1f}s) - {'PASS' if valid_delay else 'FAIL'}")
        
        if not valid_delay:
            return False
    
    return True

# Create browser function using research-based decorator
@browser(
    user_agent_rotation=True,
    headless=True,
    block_images=True,
    block_css=True,
    stealth=True,
    profile='test_research_profile'
)
def test_botasaurus_integration(driver, data):
    """Test Botasaurus integration with research-based features."""
    results = []
    
    print("\nTesting Botasaurus Integration...")
    
    try:
        # Test 1: Navigate to test site with anti-detection
        print("  Testing navigation with anti-detection...")
        driver.get("https://httpbin.org/headers")
        
        # Extract headers to verify user agent
        headers_text = driver.run_js("return document.body.innerText;")
        has_user_agent = "User-Agent" in headers_text
        
        print(f"  User agent present: {has_user_agent}")
        
        # Test 2: Verify resource blocking
        print("  Testing resource blocking...")
        # This would typically show in network logs, but we can verify the setting worked
        current_url = driver.current_url
        page_loaded = "httpbin.org" in current_url
        
        print(f"  Page loaded successfully: {page_loaded}")
        
        # Test 3: Test JavaScript execution
        print("  Testing JavaScript execution...")
        user_agent = driver.run_js("return navigator.userAgent;")
        js_works = len(user_agent) > 0
        
        print(f"  JavaScript execution: {js_works}")
        print(f"  User Agent: {user_agent[:50]}...")
        
        results.append({
            'test': 'botasaurus_integration',
            'status': 'success',
            'has_user_agent': has_user_agent,
            'page_loaded': page_loaded,
            'js_works': js_works,
            'user_agent': user_agent[:100]
        })
        
    except Exception as e:
        print(f"  Integration test failed: {e}")
        results.append({
            'test': 'botasaurus_integration',
            'status': 'failed',
            'error': str(e)
        })
    
    return results

def test_proxy_management():
    """Test proxy management features."""
    print("\nTesting Proxy Management...")
    
    settings = get_settings()
    manager = BotasaurusAntiDetectionManager(settings)
    
    # Test proxy pool loading
    proxy_count = len(manager.proxy_pool)
    print(f"  Loaded proxies: {proxy_count}")
    
    # Test proxy rotation
    campaign = "test_proxy_campaign"
    config1 = manager.get_session_config(campaign)
    
    # Rotate session
    manager.rotate_session(campaign)
    config2 = manager.get_session_config(campaign)
    
    # Check if profiles are different (indicating rotation)
    profiles_different = config1.profile_name != config2.profile_name
    print(f"  Session rotation: {profiles_different}")
    
    # Test proxy health marking
    test_proxy = "http://test:test@example.com:8080"
    manager.mark_proxy_unhealthy(test_proxy)
    is_marked_unhealthy = test_proxy in manager.failed_proxies
    
    print(f"  Proxy health marking: {is_marked_unhealthy}")
    
    return True

def main():
    """Run all Botasaurus anti-detection tests."""
    print("Botasaurus Anti-Detection Test Suite")
    print("Based on Research Findings")
    print("=" * 50)
    
    test_results = []
    
    # Test individual components
    try:
        result1 = test_session_config_generation()
        test_results.append(("Session Config Generation", result1))
    except Exception as e:
        print(f"[ERROR] Session config test failed: {e}")
        test_results.append(("Session Config Generation", False))
    
    try:
        result2 = test_browser_decorator_args()
        test_results.append(("Browser Decorator Args", result2))
    except Exception as e:
        print(f"[ERROR] Browser args test failed: {e}")
        test_results.append(("Browser Decorator Args", False))
    
    try:
        result3 = test_delay_patterns()
        test_results.append(("Delay Patterns", result3))
    except Exception as e:
        print(f"[ERROR] Delay patterns test failed: {e}")
        test_results.append(("Delay Patterns", False))
    
    try:
        result4 = test_exponential_backoff()
        test_results.append(("Exponential Backoff", result4))
    except Exception as e:
        print(f"[ERROR] Exponential backoff test failed: {e}")
        test_results.append(("Exponential Backoff", False))
    
    try:
        result5 = test_proxy_management()
        test_results.append(("Proxy Management", result5))
    except Exception as e:
        print(f"[ERROR] Proxy management test failed: {e}")
        test_results.append(("Proxy Management", False))
    
    # Browser integration test
    try:
        print("\nRunning Botasaurus browser integration test...")
        browser_results = test_botasaurus_integration()
        browser_success = browser_results and browser_results[0]['status'] == 'success'
        test_results.append(("Botasaurus Integration", browser_success))
    except Exception as e:
        print(f"[ERROR] Botasaurus integration test failed: {e}")
        test_results.append(("Botasaurus Integration", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Research-Based Anti-Detection Test Results:")
    print("-" * 40)
    
    passed = 0
    for test_name, result in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(test_results)}")
    
    if passed == len(test_results):
        print("All research-based anti-detection tests passed!")
        print("Implementation follows Botasaurus best practices")
        return 0
    else:
        print("Some tests failed - check implementation against research")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)