#!/usr/bin/env python3
"""
TED Speaker Scraper - DuckDuckGo Version
Uses DuckDuckGo search instead of Google to avoid CAPTCHA
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
from pathlib import Path
import logging
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

@browser(
    headless=False,  # Watch it work
    block_images=True,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def scrape_ted_ddg(driver, data):
    """TED scraper using DuckDuckGo search."""
    results = []
    
    try:
        # Test with known speakers
        test_speakers = [
            {"name": "Jennifer Aaker", "title": "Stanford GSB Professor"},
            {"name": "Brené Brown", "title": "Researcher and Author"},
            {"name": "Simon Sinek", "title": "Author and Speaker"},
            {"name": "Amy Cuddy", "title": "Social Psychologist"},
            {"name": "Dan Gilbert", "title": "Harvard Psychology Professor"},
            {"name": "Susan Cain", "title": "Author of Quiet"},
            {"name": "Angela Duckworth", "title": "UPenn Psychology Professor"},
            {"name": "Carol Dweck", "title": "Stanford Psychology Professor"},
            {"name": "Adam Grant", "title": "Wharton Professor"},
            {"name": "Kelly McGonigal", "title": "Stanford Health Psychologist"}
        ]
        
        for i, speaker in enumerate(test_speakers, 1):
            logger.info(f"\n[{i}/{len(test_speakers)}] Processing {speaker['name']}")
            
            speaker_data = {
                'name': speaker['name'],
                'title': speaker['title'],
                'email': None,
                'website': None,
                'found_on': None
            }
            
            # Search DuckDuckGo
            search_query = f"{speaker['name']} {speaker['title']} email contact"
            logger.info(f"  Searching DuckDuckGo: {search_query}")
            
            ddg_url = f"https://duckduckgo.com/?q={urllib.parse.quote(search_query)}"
            driver.get(ddg_url)
            driver.sleep(3)
            
            # Parse DDG results
            html = driver.page_html
            soup = BeautifulSoup(html, 'html.parser')
            
            # DuckDuckGo result structure
            found_url = None
            
            # Method 1: Look for result links
            result_links = soup.find_all('a', class_='result__a')
            for link in result_links[:5]:
                href = link.get('href', '')
                if any(domain in href for domain in ['.edu', '.org']) and \
                   not any(skip in href for skip in ['wikipedia', 'youtube', 'twitter', 'linkedin']):
                    found_url = href
                    logger.info(f"  Found from DDG results: {found_url}")
                    break
            
            # Method 2: Look for all external links
            if not found_url:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    # DuckDuckGo uses //duckduckgo.com/l/?uddg= for external links
                    if '//duckduckgo.com/l/?uddg=' in href:
                        # Extract actual URL
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'uddg' in parsed:
                            real_url = urllib.parse.unquote(parsed['uddg'][0])
                            if any(domain in real_url for domain in ['.edu', '.org', '.com']):
                                if not any(skip in real_url.lower() for skip in [
                                    'wikipedia', 'youtube', 'twitter', 'linkedin', 'facebook',
                                    'instagram', 'amazon', 'duckduckgo', 'ted.com'
                                ]):
                                    found_url = real_url
                                    logger.info(f"  Found from DDG redirect: {found_url}")
                                    break
                    # Direct links
                    elif href.startswith('http') and 'duckduckgo' not in href:
                        if any(domain in href for domain in ['.edu', '.org']):
                            if not any(skip in href.lower() for skip in [
                                'wikipedia', 'youtube', 'twitter', 'linkedin'
                            ]):
                                found_url = href
                                logger.info(f"  Found direct link: {found_url}")
                                break
            
            if found_url:
                speaker_data['website'] = found_url
                
                # Visit the website with Cloudflare bypass
                try:
                    logger.info(f"  Visiting website with bypass...")
                    driver.google_get(found_url, bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Check if we're not blocked
                    current_url = driver.current_url
                    if "enable-javascript" not in current_url.lower() and "cloudflare" not in current_url.lower():
                        website_html = driver.page_html
                        
                        # Extract emails
                        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                        emails = re.findall(email_pattern, website_html)
                        
                        # Filter and validate emails
                        for email in emails:
                            email = email.lower()
                            # Skip common fake/system emails
                            if not any(skip in email for skip in [
                                'example', 'test', 'demo', 'sample', 'your',
                                'email@', 'user@', 'name@', 'firstname',
                                'lastname', 'sentry', 'wix', 'cloudflare',
                                'javascript', 'noreply', 'donotreply',
                                'webmaster', 'postmaster', 'admin@',
                                'info@', 'support@', 'sales@', 'protected',
                                '.png', '.jpg', '.gif', '.css', '.js'
                            ]):
                                # Check if email might belong to the speaker
                                name_parts = speaker['name'].lower().split()
                                last_name = name_parts[-1] if name_parts else ''
                                
                                # Accept email if it contains part of their name or is from .edu
                                if (any(part in email for part in name_parts if len(part) > 3) or 
                                    '.edu' in email):
                                    speaker_data['email'] = email
                                    speaker_data['found_on'] = current_url
                                    logger.info(f"  EMAIL FOUND: {email}")
                                    break
                        
                        # If no email with name match, take first .edu email
                        if not speaker_data['email'] and '.edu' in found_url:
                            for email in emails:
                                if '.edu' in email and '@' in email:
                                    if not any(skip in email.lower() for skip in [
                                        'example', 'webmaster', 'postmaster', 'admin'
                                    ]):
                                        speaker_data['email'] = email
                                        speaker_data['found_on'] = current_url
                                        logger.info(f"  EMAIL FOUND (edu): {email}")
                                        break
                        
                        # Try to find contact page
                        if not speaker_data['email']:
                            website_soup = BeautifulSoup(website_html, 'html.parser')
                            contact_links = website_soup.find_all('a', href=re.compile(r'contact|about', re.I))
                            
                            for contact_link in contact_links[:1]:  # Just try first one
                                try:
                                    contact_href = contact_link.get('href', '')
                                    if contact_href.startswith('/'):
                                        contact_url = found_url.rstrip('/') + contact_href
                                    elif not contact_href.startswith('http'):
                                        contact_url = found_url.rstrip('/') + '/' + contact_href
                                    else:
                                        contact_url = contact_href
                                    
                                    logger.info(f"  Checking contact page: {contact_url}")
                                    driver.google_get(contact_url, bypass_cloudflare=True)
                                    driver.sleep(2)
                                    
                                    contact_html = driver.page_html
                                    emails = re.findall(email_pattern, contact_html)
                                    
                                    for email in emails:
                                        email = email.lower()
                                        if not any(fake in email for fake in ['example', 'domain', 'test']):
                                            if '@' in email and '.' in email.split('@')[1]:
                                                speaker_data['email'] = email
                                                speaker_data['found_on'] = driver.current_url
                                                logger.info(f"  EMAIL FOUND (contact page): {email}")
                                                break
                                    
                                    if speaker_data['email']:
                                        break
                                        
                                except Exception as e:
                                    logger.debug(f"  Error checking contact page: {e}")
                    else:
                        logger.info(f"  Blocked by Cloudflare/JavaScript check")
                        
                except Exception as e:
                    logger.info(f"  Error visiting website: {str(e)[:100]}")
            else:
                logger.info(f"  No website found in DuckDuckGo results")
            
            results.append(speaker_data)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers):
    """Save results to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_duckduckgo_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'title', 'email', 'website', 'found_on'])
        writer.writeheader()
        writer.writerows(speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - DUCKDUCKGO VERSION")
    print("Using DuckDuckGo to avoid Google CAPTCHA")
    print("="*80)
    
    results = scrape_ted_ddg()
    
    if results:
        csv_file = save_results(results)
        
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  - Total speakers: {len(results)}")
        print(f"  - With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  - With website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  - Saved to: {csv_file}")
        
        print(f"\nSpeakers with emails found:")
        for s in results:
            if s.get('email'):
                print(f"  - {s['name']}: {s['email']}")
        
        print(f"\nSpeakers without emails:")
        for s in results:
            if not s.get('email'):
                status = f"website: {s['website'][:50]}..." if s.get('website') else "no website found"
                print(f"  - {s['name']}: {status}")
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()