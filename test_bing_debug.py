#!/usr/bin/env python3
"""
Debug script to see what HTML Bing is actually returning.
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from botasaurus.browser import browser

@browser(headless=False)  # Use visible browser for debugging
def debug_bing_search(driver, data):
    """Debug function to see what's happening with Bing"""
    
    print("Navigating to Bing...")
    driver.get("https://www.bing.com")
    
    # Take a screenshot
    print("Taking screenshot...")
    driver.save_screenshot("debug_bing_start.png")
    
    # Get page HTML
    html_content = driver.page_html
    
    # Save HTML to file
    with open("debug_bing_html.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Page title: {driver.title}")
    print(f"Current URL: {driver.current_url}")
    print(f"HTML length: {len(html_content)} characters")
    
    # Check for blocking indicators
    blocking_indicators = [
        "captcha",
        "blocked",
        "too many requests",
        "rate limit",
        "access denied",
        "suspicious activity",
        "verify you are human",
        "robot",
        "automation"
    ]
    
    html_lower = html_content.lower()
    found_indicators = []
    for indicator in blocking_indicators:
        if indicator in html_lower:
            found_indicators.append(indicator)
    
    if found_indicators:
        print(f"Found blocking indicators: {found_indicators}")
    else:
        print("No blocking indicators found")
    
    # Look for search box
    try:
        search_box = driver.select('input[name="q"]')
        if search_box:
            print("Search box found successfully")
        else:
            print("Search box NOT found")
    except Exception as e:
        print(f"Error finding search box: {e}")
    
    # Wait for user input to close
    input("Press Enter to close browser...")
    
    return {
        "url": driver.current_url,
        "title": driver.title,
        "html_length": len(html_content),
        "blocking_indicators": found_indicators
    }

if __name__ == "__main__":
    result = debug_bing_search(data={})
    print(f"Debug result: {result}")