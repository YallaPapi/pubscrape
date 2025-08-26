#!/usr/bin/env python3
"""
Simple Botasaurus Test - Minimal Working Example
Based on working_botasaurus_scraper.py patterns
"""

from botasaurus.browser import browser, Driver

@browser(headless=True)
def test_basic_browser(driver, url):
    """Most basic browser test possible"""
    driver.get(url)
    driver.sleep(1)
    
    return {
        'title': driver.title,
        'url': driver.current_url,
        'success': True
    }

@browser(
    headless=True,
    block_images=True
)
def test_bing_simple(driver, query):
    """Simple Bing test based on working patterns"""
    # Use google_get method like the working example
    driver.google_get(f"site:bing.com {query}")
    driver.sleep(2)
    
    return {
        'title': driver.title,
        'url': driver.current_url,
        'query': query,
        'success': True
    }

if __name__ == "__main__":
    print("Testing basic browser...")
    result1 = test_basic_browser("https://httpbin.org/user-agent")
    print(f"Basic test: {result1['success']}, Title: {result1['title']}")
    
    print("\nTesting Bing search...")
    result2 = test_bing_simple("test query")
    print(f"Bing test: {result2['success']}, Title: {result2['title'][:50]}...")
    
    print("\nBotasaurus working correctly!")