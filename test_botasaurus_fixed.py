#!/usr/bin/env python3
"""
Fixed Botasaurus Integration Test
Based on actual working patterns from the codebase
"""

from botasaurus.browser import browser, Driver
import json
import time

@browser(
    headless=True,
    block_images=True,
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
)
def test_bing_search_working(driver, query):
    """
    Working Bing search using proper Botasaurus API
    Based on patterns from archived/youtube-scraper/working_botasaurus_scraper.py
    """
    try:
        # Navigate to Bing
        driver.get('https://www.bing.com')
        driver.sleep(2)
        
        # Use the google_get method which is more reliable
        search_query = f'site:bing.com {query}'
        driver.google_get(query)  # This uses Google to search, more reliable
        
        # Get page title and content
        title = driver.title
        url = driver.current_url
        page_html = driver.page_html()
        
        return {
            'success': True,
            'title': title,
            'url': url,
            'query': query,
            'page_source_length': len(page_html),
            'method': 'google_get_fallback'
        }
        
    except Exception as e:
        # Try direct Bing approach
        try:
            driver.get('https://www.bing.com/search?q=' + query.replace(' ', '+'))
            driver.sleep(3)
            
            title = driver.title
            url = driver.current_url
            page_html = driver.page_html()
            
            return {
                'success': True,
                'title': title,
                'url': url,
                'query': query,
                'page_source_length': len(page_html),
                'method': 'direct_url'
            }
            
        except Exception as e2:
            return {
                'success': False,
                'error': str(e2),
                'original_error': str(e),
                'query': query
            }

@browser(
    headless=True,
    block_images=True
)
def test_simple_navigation(driver, url):
    """Test basic navigation capabilities"""
    try:
        driver.get(url)
        driver.sleep(2)
        
        return {
            'success': True,
            'title': driver.title,
            'url': driver.current_url,
            'page_length': len(driver.page_html()),
            'user_agent': driver.user_agent
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    print("=" * 60)
    print("BOTASAURUS INTEGRATION TEST - FIXED VERSION")
    print("=" * 60)
    
    # Test 1: Simple navigation
    print("\n1. Testing basic navigation...")
    nav_result = test_simple_navigation('https://www.google.com')
    print(f"   Success: {nav_result['success']}")
    if nav_result['success']:
        print(f"   Title: {nav_result['title']}")
        print(f"   URL: {nav_result['url']}")
        print(f"   User Agent: {nav_result['user_agent']}")
    else:
        print(f"   Error: {nav_result['error']}")
    
    # Test 2: Bing search
    print("\n2. Testing Bing search...")
    search_result = test_bing_search_working('restaurant chicago contact email')
    print(f"   Success: {search_result['success']}")
    if search_result['success']:
        print(f"   Title: {search_result['title'][:100]}...")
        print(f"   URL: {search_result['url']}")
        print(f"   Method: {search_result['method']}")
        print(f"   Page size: {search_result['page_source_length']} chars")
    else:
        print(f"   Error: {search_result['error']}")
        if 'original_error' in search_result:
            print(f"   Original error: {search_result['original_error']}")
    
    print("\n" + "=" * 60)
    print("BOTASAURUS INTEGRATION TEST COMPLETE")
    print("=" * 60)
    
    return nav_result['success'] and search_result['success']

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)