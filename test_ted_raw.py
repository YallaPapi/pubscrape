#!/usr/bin/env python3
"""
Test what TED actually returns
Check if the URLs are already blocked or if we can get real ones
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@browser(headless=False)
def check_ted_raw(driver, data):
    """Check what TED page actually contains."""
    
    # Go to a specific TED speaker page
    speaker_url = "https://www.ted.com/speakers/jennifer_aaker"
    logger.info(f"Loading: {speaker_url}")
    
    # Try using google_get with bypass from the start
    driver.google_get(speaker_url, bypass_cloudflare=True)
    driver.sleep(5)
    
    # Get the raw HTML
    html = driver.page_html
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find ALL links on the page
    logger.info("\n=== ALL LINKS ON PAGE ===")
    all_links = soup.find_all('a', href=True)
    
    external_links = []
    for link in all_links:
        href = link.get('href', '')
        # Only show external links
        if href.startswith('http') and 'ted.com' not in href:
            external_links.append(href)
            logger.info(f"External link found: {href}")
    
    if not external_links:
        logger.info("No external links found!")
    
    # Check if there's any text that looks like a URL
    logger.info("\n=== SEARCHING FOR URL PATTERNS IN TEXT ===")
    text = soup.get_text()
    
    # Look for domain patterns
    domain_patterns = [
        r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}',
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        r'[a-zA-Z0-9-]+\.stanford\.edu',
        r'[a-zA-Z0-9-]+\.edu'
    ]
    
    for pattern in domain_patterns:
        matches = re.findall(pattern, text)
        if matches:
            logger.info(f"Pattern {pattern} found: {matches[:3]}")
    
    # Check meta tags and other places where URLs might hide
    logger.info("\n=== CHECKING META TAGS ===")
    meta_tags = soup.find_all('meta')
    for meta in meta_tags:
        content = meta.get('content', '')
        if 'http' in content and 'ted.com' not in content:
            logger.info(f"Meta content with URL: {content}")
    
    # Check for JavaScript variables that might contain URLs
    logger.info("\n=== CHECKING SCRIPTS ===")
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Look for URLs in JavaScript
            js_urls = re.findall(r'"(https?://[^"]+)"', script.string)
            for url in js_urls:
                if 'ted.com' not in url and 'enable-javascript' not in url:
                    logger.info(f"URL in script: {url}")
    
    return {"external_links": external_links}

if __name__ == "__main__":
    result = check_ted_raw()
    print(f"\nFound {len(result['external_links'])} external links")