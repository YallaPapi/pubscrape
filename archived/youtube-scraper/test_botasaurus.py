"""
Simple test of Botasaurus for finding guest contacts
"""

from botasaurus import *
from botasaurus.browser import browser, Driver

@browser(headless=False)  # Show browser for debugging
def test_scrape(driver: Driver, data):
    """Test basic scraping with Botasaurus"""
    
    # Test 1: Can we scrape a public site?
    driver.get("https://www.example.com")
    title = driver.get_text("h1")
    print(f"✅ Basic scrape works: {title}")
    
    # Test 2: Can we search Google?
    driver.google_get("podcast guests technology")
    results = driver.find_elements("h3")[:3]
    print(f"✅ Found {len(results)} Google results")
    
    return {"status": "success", "title": title}

if __name__ == "__main__":
    print("Testing Botasaurus...")
    result = test_scrape()
    print(f"Result: {result}")