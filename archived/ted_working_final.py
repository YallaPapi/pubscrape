#!/usr/bin/env python3
"""
TED Speaker Scraper - Working Final Version
Uses proper Google search parsing to find speaker websites and emails
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
    reuse_driver=True
)
def scrape_ted_working(driver, data):
    """TED scraper with improved Google search parsing."""
    results = []
    
    try:
        # Test with known speakers
        test_speakers = [
            {"name": "Jennifer Aaker", "url": "https://www.ted.com/speakers/jennifer_aaker"},
            {"name": "Brené Brown", "url": "https://www.ted.com/speakers/brene_brown"},
            {"name": "Simon Sinek", "url": "https://www.ted.com/speakers/simon_sinek"},
            {"name": "Amy Cuddy", "url": "https://www.ted.com/speakers/amy_cuddy"},
            {"name": "Dan Gilbert", "url": "https://www.ted.com/speakers/dan_gilbert"},
            {"name": "Susan Cain", "url": "https://www.ted.com/speakers/susan_cain"},
            {"name": "Angela Duckworth", "url": "https://www.ted.com/speakers/angela_duckworth"},
            {"name": "Carol Dweck", "url": "https://www.ted.com/speakers/carol_dweck"},
            {"name": "Adam Grant", "url": "https://www.ted.com/speakers/adam_grant"},
            {"name": "Kelly McGonigal", "url": "https://www.ted.com/speakers/kelly_mcgonigal"}
        ]
        
        for i, speaker in enumerate(test_speakers, 1):
            logger.info(f"\n[{i}/{len(test_speakers)}] Processing {speaker['name']}")
            
            speaker_data = {
                'name': speaker['name'],
                'ted_url': speaker['url'],
                'email': None,
                'website': None,
                'found_on': None
            }
            
            # Search Google for speaker's university/organization page
            search_query = f"{speaker['name']} university professor contact"
            logger.info(f"  Searching: {search_query}")
            
            google_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}"
            driver.get(google_url)
            driver.sleep(2)
            
            # Parse Google results
            html = driver.page_html
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: Find links in search result divs
            found_url = None
            search_results = soup.find_all('div', class_='g')
            
            for result in search_results[:5]:  # Check first 5 results
                link_elem = result.find('a', href=True)
                if link_elem:
                    href = link_elem.get('href', '')
                    # Check if it's a university or org site
                    if any(domain in href for domain in ['.edu', '.org']) and \
                       not any(skip in href for skip in ['wikipedia', 'youtube', 'twitter', 'linkedin']):
                        found_url = href
                        logger.info(f"  Found from search div: {found_url}")
                        break
            
            # Method 2: Look through all links if method 1 didn't work
            if not found_url:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    
                    # Extract real URL from Google redirect
                    real_url = None
                    if '/url?q=' in href:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'q' in parsed:
                            real_url = parsed['q'][0]
                    elif href.startswith('http') and 'google' not in href:
                        real_url = href
                    
                    if real_url and any(domain in real_url for domain in ['.edu', '.org', '.com']):
                        if not any(skip in real_url.lower() for skip in [
                            'wikipedia', 'youtube', 'twitter', 'linkedin', 'facebook',
                            'instagram', 'amazon', 'google', 'ted.com'
                        ]):
                            found_url = real_url.split('#')[0].split('&')[0]  # Clean URL
                            logger.info(f"  Found from all links: {found_url}")
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
                                    '.edu' in email or
                                    (last_name and len(last_name) > 3 and last_name in email)):
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
                    else:
                        logger.info(f"  Blocked by Cloudflare/JavaScript check")
                        
                except Exception as e:
                    logger.info(f"  Error visiting website: {str(e)[:100]}")
            else:
                logger.info(f"  No website found in search results")
            
            results.append(speaker_data)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers):
    """Save results to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_working_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'found_on', 'ted_url'])
        writer.writeheader()
        writer.writerows(speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - WORKING FINAL VERSION")
    print("Testing with 10 well-known TED speakers")
    print("="*80)
    
    results = scrape_ted_working()
    
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
                print(f"  - {s['name']}: {s['email']} (from {s.get('found_on', 'unknown')})")
        
        print(f"\nSpeakers without emails:")
        for s in results:
            if not s.get('email'):
                status = f"website: {s['website'][:50]}..." if s.get('website') else "no website found"
                print(f"  - {s['name']}: {status}")

if __name__ == "__main__":
    main()