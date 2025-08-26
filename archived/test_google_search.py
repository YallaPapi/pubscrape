#!/usr/bin/env python3
"""
Test Google search to find speaker websites
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import re
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@browser(headless=False)
def test_google_search(driver, data):
    """Test searching for a TED speaker's website."""
    
    # Search for Jennifer Aaker
    search_query = "Jennifer Aaker Stanford TED speaker website"
    logger.info(f"Searching Google for: {search_query}")
    
    driver.get(f"https://www.google.com/search?q={search_query}")
    driver.sleep(3)
    
    # Get the HTML
    html = driver.page_html
    soup = BeautifulSoup(html, 'html.parser')
    
    logger.info("\n=== ANALYZING GOOGLE SEARCH RESULTS ===")
    
    # Method 1: Look for search result divs
    search_results = soup.find_all('div', class_='g')
    logger.info(f"Found {len(search_results)} search result divs")
    
    # Method 2: Find all links
    all_links = soup.find_all('a', href=True)
    logger.info(f"Found {len(all_links)} total links")
    
    # Look for actual result links
    found_websites = []
    for link in all_links:
        href = link.get('href', '')
        
        # Google wraps URLs in /url?q=
        if '/url?q=' in href:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if 'q' in parsed:
                real_url = parsed['q'][0]
                
                # Check if it's a relevant site
                if 'stanford.edu' in real_url or 'gsb.stanford' in real_url:
                    logger.info(f"✓ Found Stanford URL: {real_url}")
                    found_websites.append(real_url)
        
        # Sometimes Google uses direct links
        elif href.startswith('http') and 'google' not in href:
            if 'stanford' in href:
                logger.info(f"✓ Found direct Stanford URL: {href}")
                found_websites.append(href)
    
    # Try to visit the first Stanford site found
    if found_websites:
        website = found_websites[0]
        logger.info(f"\n=== VISITING WEBSITE WITH BYPASS ===")
        logger.info(f"URL: {website}")
        
        driver.google_get(website, bypass_cloudflare=True)
        driver.sleep(3)
        
        # Check if we bypassed Cloudflare
        current_url = driver.current_url
        if "enable-javascript" in current_url:
            logger.info("❌ Still blocked by Cloudflare")
        else:
            logger.info(f"✓ Successfully loaded: {current_url}")
            
            # Look for email
            website_html = driver.page_html
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, website_html)
            
            unique_emails = []
            for email in emails:
                if not any(fake in email.lower() for fake in 
                         ['example', 'domain', 'test', 'sample', 'javascript', 
                          'cloudflare', 'protected', 'your', 'sentry', 'email@', 'wixpress']):
                    if email not in unique_emails:
                        unique_emails.append(email)
            
            if unique_emails:
                logger.info(f"✓ Found emails: {unique_emails[:5]}")
            else:
                logger.info("❌ No emails found")
    else:
        logger.info("\n❌ No Stanford websites found in search results")
    
    return {"websites_found": found_websites}

if __name__ == "__main__":
    result = test_google_search()
    print(f"\nFound {len(result['websites_found'])} websites")