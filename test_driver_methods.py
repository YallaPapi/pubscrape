#!/usr/bin/env python3
"""Test what methods are available on the Driver object"""

from botasaurus.browser import browser

@browser(headless=False)
def test_driver_methods(driver, data):
    """Check available driver methods."""
    driver.get("https://httpbin.org/html")
    driver.sleep(2)
    
    # List all available methods
    methods = [m for m in dir(driver) if not m.startswith('_')]
    print("Available Driver methods:")
    for method in sorted(methods):
        print(f"  - {method}")
    
    # Try to get page content
    try:
        # Try different methods to get HTML
        if hasattr(driver, 'page_source'):
            print("\ndriver.page_source exists")
            html = driver.page_source
            print(f"Got {len(html)} characters of HTML")
        
        if hasattr(driver, 'html'):
            print("\ndriver.html exists")
            html = driver.html
            print(f"Got {len(html)} characters of HTML")
            
        if hasattr(driver, 'get_html'):
            print("\ndriver.get_html exists")
            
        if hasattr(driver, 'get_page_source'):
            print("\ndriver.get_page_source exists")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return {"success": True}

if __name__ == "__main__":
    test_driver_methods()