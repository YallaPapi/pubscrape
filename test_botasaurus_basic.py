#!/usr/bin/env python3
"""
Test basic botasaurus functionality.
This will help us verify the installation works.
"""

from botasaurus import *

@browser
def test_basic_scraping(driver, data):
    """Test basic botasaurus scraping."""
    # Visit a simple test page
    driver.get("https://httpbin.org/html")
    
    # Get page title
    title = driver.title
    
    # Get some text from the page
    body_text = driver.find_element('tag_name', 'body').text[:200]
    
    return {
        "success": True,
        "title": title,
        "body_preview": body_text,
        "url": driver.current_url
    }

if __name__ == "__main__":
    print("Testing basic botasaurus functionality...")
    result = test_basic_scraping()
    print(f"Result: {result}")