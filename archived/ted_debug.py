#!/usr/bin/env python3
"""
TED Speaker Scraper - Debug Version
Diagnose why Google search isn't returning results
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

@browser(
    headless=False,
    block_images=False,
    reuse_driver=False
)
def debug_google_search(driver, data):
    """Debug Google search to see what's happening."""
    
    try:
        # Test with Jennifer Aaker
        search_query = "Jennifer Aaker Stanford university"
        logger.info(f"Searching for: {search_query}")
        
        # Go to Google
        driver.get("https://www.google.com")
        driver.sleep(2)
        
        # Check if we're on Google
        current_url = driver.current_url
        logger.info(f"Current URL after going to Google: {current_url}")
        
        # Try to search
        driver.get(f"https://www.google.com/search?q={search_query}")
        driver.sleep(3)
        
        # Get the HTML
        html = driver.page_html
        current_url = driver.current_url
        
        logger.info(f"Current URL after search: {current_url}")
        logger.info(f"HTML length: {len(html)}")
        
        # Save HTML to file for inspection
        with open("google_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Saved HTML to google_debug.html")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for different types of elements
        logger.info(f"Title: {soup.title.string if soup.title else 'No title'}")
        
        # Count different types of links
        all_links = soup.find_all('a', href=True)
        logger.info(f"Total links found: {len(all_links)}")
        
        # Check for search result divs
        search_divs = soup.find_all('div', class_='g')
        logger.info(f"Search result divs (class='g'): {len(search_divs)}")
        
        # Look for any divs with 'search' in class
        search_related = soup.find_all('div', class_=lambda x: x and 'search' in x.lower())
        logger.info(f"Divs with 'search' in class: {len(search_related)}")
        
        # Print first 10 links
        logger.info("\nFirst 10 links found:")
        for i, link in enumerate(all_links[:10], 1):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            logger.info(f"  {i}. {text} -> {href[:100]}")
        
        # Look for Stanford links specifically
        stanford_links = []
        for link in all_links:
            href = link.get('href', '')
            if 'stanford' in href.lower():
                stanford_links.append(href)
        
        logger.info(f"\nFound {len(stanford_links)} Stanford links:")
        for link in stanford_links[:5]:
            logger.info(f"  - {link}")
        
        # Check if we're being blocked
        if "captcha" in html.lower():
            logger.warning("CAPTCHA detected!")
        if "unusual traffic" in html.lower():
            logger.warning("Google detected unusual traffic!")
        if "enable cookies" in html.lower():
            logger.warning("Google wants cookies enabled!")
        
        return {
            "url": current_url,
            "links_found": len(all_links),
            "search_divs": len(search_divs),
            "stanford_links": len(stanford_links)
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    result = debug_google_search()
    print(f"\nDebug Results: {result}")