#!/usr/bin/env python3
"""
Anti-Detection Engine Test
Tests all anti-detection features including user agent rotation, delays, and proxy management.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.settings import get_settings
from anti_detection.manager import AntiDetectionManager
from botasaurus.browser import browser

def test_user_agent_rotation():
    """Test user agent rotation functionality."""
    print("\nTesting User Agent Rotation...")
    
    settings = get_settings()
    manager = AntiDetectionManager(settings)
    
    # Test multiple user agents
    user_agents = []
    for i in range(5):
        ua = manager.user_agent_rotator.get_random_user_agent()
        user_agents.append(ua)
        print(f"  {i+1}. {ua[:60]}...")
    
    # Check for variety
    unique_agents = len(set(user_agents))
    print(f"  Generated {unique_agents}/{len(user_agents)} unique user agents")
    
    # Test browser-specific agents
    chrome_ua = manager.user_agent_rotator.get_user_agent_by_browser('chrome')
    firefox_ua = manager.user_agent_rotator.get_user_agent_by_browser('firefox')
    
    print(f"  Chrome UA: {chrome_ua[:50]}...")
    print(f"  Firefox UA: {firefox_ua[:50]}...")
    
    return unique_agents >= 3

def test_delay_patterns():
    """Test human-like delay patterns."""
    print("\nTesting Human-like Delays...")
    
    settings = get_settings()
    manager = AntiDetectionManager(settings)
    
    # Test different delay types
    start_time = time.time()
    
    delays = []
    for action in ['page_load', 'search', 'navigation', 'extraction']:
        delay_start = time.time()
        manager.delays.random_delay(action)
        actual_delay = time.time() - delay_start
        delays.append(actual_delay)
        print(f"  {action}: {actual_delay:.2f}s")
    
    total_time = time.time() - start_time
    print(f"  Total delay time: {total_time:.2f}s")
    
    # Test typing simulation
    typing_start = time.time()
    manager.delays.typing_delay("test query")
    typing_time = time.time() - typing_start
    print(f"  Typing simulation: {typing_time:.2f}s")
    
    return all(d > 0.1 for d in delays)

def test_browser_profile_generation():
    """Test browser profile generation."""
    print("\nTesting Browser Profile Generation...")
    
    settings = get_settings()
    manager = AntiDetectionManager(settings)
    
    # Generate multiple profiles
    profiles = []
    for i in range(3):
        session_id = f"test_session_{i}"
        config = manager.get_browser_config(session_id)
        profiles.append(config)
        
        print(f"  Session {i+1}:")
        print(f"    Headless: {config.get('headless')}")
        print(f"    User Agent Rotation: {config.get('user_agent_rotation')}")
        print(f"    Block Images: {config.get('block_images')}")
        print(f"    Window Size: {config.get('window_size')}")
    
    # Check for profile variety
    window_sizes = [p.get('window_size') for p in profiles]
    unique_sizes = len(set(window_sizes))
    
    print(f"  Generated {unique_sizes} unique window sizes")
    
    return len(profiles) == 3

def test_resource_blocking():
    """Test resource blocking configuration."""
    print("\nTesting Resource Blocking...")
    
    settings = get_settings()
    manager = AntiDetectionManager(settings)
    
    blocking_rules = manager.get_resource_blocking_rules()
    
    print(f"  Total blocking rules: {len(blocking_rules)}")
    print("  Sample rules:")
    for rule in blocking_rules[:5]:
        print(f"    - {rule}")
    
    # Check for expected patterns
    has_images = any('*.jpg' in rule or '*.png' in rule for rule in blocking_rules)
    has_css = any('*.css' in rule for rule in blocking_rules)
    has_tracking = any('analytics' in rule for rule in blocking_rules)
    
    print(f"  Blocks images: {has_images}")
    print(f"  Blocks CSS: {has_css}")
    print(f"  Blocks tracking: {has_tracking}")
    
    return len(blocking_rules) > 0

@browser(headless=True, block_images=True)
def test_browser_integration(driver, data):
    """Test anti-detection integration with Botasaurus browser."""
    results = []
    
    print("\nTesting Browser Integration...")
    
    settings = get_settings()
    manager = AntiDetectionManager(settings)
    
    try:
        # Test navigation with anti-detection
        print("  Navigating to test site...")
        driver.get("https://httpbin.org/headers")
        
        # Apply human behavior
        print("  Applying human behavior patterns...")
        manager.apply_human_behavior(driver)
        
        # Extract headers to verify user agent
        headers_text = driver.run_js("return document.body.innerText;")
        
        # Check if user agent is present
        has_user_agent = "User-Agent" in headers_text
        print(f"  User agent in headers: {has_user_agent}")
        
        # Test session stats
        stats = manager.get_session_stats()
        print(f"  Active sessions: {stats['active_sessions']}")
        
        results.append({
            'test': 'browser_integration',
            'status': 'success',
            'has_user_agent': has_user_agent,
            'stats': stats
        })
        
    except Exception as e:
        print(f"  [ERROR] Browser integration test failed: {e}")
        results.append({
            'test': 'browser_integration',
            'status': 'failed',
            'error': str(e)
        })
    
    return results

def test_proxy_manager():
    """Test proxy manager functionality."""
    print("\nTesting Proxy Manager...")
    
    settings = get_settings()
    manager = AntiDetectionManager(settings)
    
    proxy_stats = manager.proxy_manager.get_proxy_stats()
    print(f"  Proxy enabled: {proxy_stats['enabled']}")
    print(f"  Total proxies: {proxy_stats['total']}")
    
    if proxy_stats['total'] > 0:
        print(f"  Active proxies: {proxy_stats.get('active', 0)}")
        
        # Test proxy retrieval
        proxy_config = manager.proxy_manager.get_proxy()
        if proxy_config:
            print(f"  Retrieved proxy: {proxy_config.get('host')}:{proxy_config.get('port')}")
        else:
            print("  No proxy configuration available")
    else:
        print("  No proxies configured (using direct connection)")
    
    return True

def main():
    """Run all anti-detection tests."""
    print("Anti-Detection Engine Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run individual tests
    try:
        result1 = test_user_agent_rotation()
        test_results.append(("User Agent Rotation", result1))
    except Exception as e:
        print(f"[ERROR] User agent test failed: {e}")
        test_results.append(("User Agent Rotation", False))
    
    try:
        result2 = test_delay_patterns()
        test_results.append(("Delay Patterns", result2))
    except Exception as e:
        print(f"[ERROR] Delay test failed: {e}")
        test_results.append(("Delay Patterns", False))
    
    try:
        result3 = test_browser_profile_generation()
        test_results.append(("Browser Profiles", result3))
    except Exception as e:
        print(f"[ERROR] Profile test failed: {e}")
        test_results.append(("Browser Profiles", False))
    
    try:
        result4 = test_resource_blocking()
        test_results.append(("Resource Blocking", result4))
    except Exception as e:
        print(f"[ERROR] Resource blocking test failed: {e}")
        test_results.append(("Resource Blocking", False))
    
    try:
        result5 = test_proxy_manager()
        test_results.append(("Proxy Manager", result5))
    except Exception as e:
        print(f"[ERROR] Proxy test failed: {e}")
        test_results.append(("Proxy Manager", False))
    
    # Browser integration test
    try:
        print("\nRunning browser integration test...")
        browser_results = test_browser_integration()
        browser_success = browser_results and browser_results[0]['status'] == 'success'
        test_results.append(("Browser Integration", browser_success))
    except Exception as e:
        print(f"[ERROR] Browser integration test failed: {e}")
        test_results.append(("Browser Integration", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Anti-Detection Test Results:")
    print("-" * 30)
    
    passed = 0
    for test_name, result in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(test_results)}")
    
    if passed == len(test_results):
        print("All anti-detection tests passed!")
        return 0
    else:
        print("Some tests failed - check implementation")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)