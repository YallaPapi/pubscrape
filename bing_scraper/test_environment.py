#!/usr/bin/env python3
"""
Environment Setup Test for Bing Scraper
Tests Botasaurus functionality and basic browser operations.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from botasaurus.browser import browser

@browser(headless=True, block_images=True)
def test_browser_setup(driver, data):
    """Test basic Botasaurus browser functionality."""
    results = []
    
    print("Testing browser setup...")
    
    # Test 1: Navigate to a test page
    try:
        driver.get("https://httpbin.org/get")
        print("[OK] Navigation successful")
        
        # Test 2: Extract page content
        title = driver.title
        print(f"[OK] Page title extracted: {title}")
        
        # Test 3: Test JavaScript execution
        user_agent = driver.run_js("return navigator.userAgent;")
        print(f"[OK] JavaScript execution successful")
        print(f"User Agent: {user_agent[:50]}...")
        
        # Test 4: Test element selection
        body_text = driver.run_js("return document.body.innerText;")
        if "httpbin" in body_text.lower():
            print("[OK] Element selection working")
        
        results.append({
            'test': 'browser_navigation',
            'status': 'success',
            'title': title,
            'user_agent': user_agent[:100]
        })
        
    except Exception as e:
        print(f"[ERROR] Browser test failed: {e}")
        results.append({
            'test': 'browser_navigation',
            'status': 'failed',
            'error': str(e)
        })
    
    return results

def main():
    """Run environment tests."""
    print("Bing Scraper Environment Test")
    print("=" * 40)
    
    # Test configuration loading
    try:
        from config.settings import get_settings
        settings = get_settings()
        print("[OK] Configuration loading: PASS")
    except Exception as e:
        print(f"[ERROR] Configuration loading: FAIL ({e})")
        return 1
    
    # Test Botasaurus import
    try:
        from botasaurus.browser import browser
        print("[OK] Botasaurus import: PASS")
    except Exception as e:
        print(f"[ERROR] Botasaurus import: FAIL ({e})")
        return 1
    
    # Test browser functionality
    try:
        print("\nRunning browser functionality test...")
        results = test_browser_setup()
        
        if results and results[0]['status'] == 'success':
            print("[OK] Browser functionality: PASS")
            print(f"Test Results: {len(results)} tests completed")
        else:
            print("[ERROR] Browser functionality: FAIL")
            return 1
            
    except Exception as e:
        print(f"[ERROR] Browser test failed: {e}")
        return 1
    
    print("\nAll environment tests passed!")
    print("System ready for Bing scraping operations")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)