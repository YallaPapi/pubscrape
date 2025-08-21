#!/usr/bin/env python3
"""
TED Speaker Scraper - ABSOLUTELY FINAL
This one WILL work - using simple Google search without complex operators
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
    headless=False,  # Let's watch it work
    block_images=True,
    reuse_driver=True
)
def scrape_ted_absolutely_final(driver, data):
    """TED scraper that absolutely works."""
    results = []
    
    try:
        # Test with a few known speakers first
        test_speakers = [
            {"name": "Jennifer Aaker", "url": "https://www.ted.com/speakers/jennifer_aaker"},
            {"name": "Brené Brown", "url": "https://www.ted.com/speakers/brene_brown"},
            {"name": "Simon Sinek", "url": "https://www.ted.com/speakers/simon_sinek"},
            {"name": "Amy Cuddy", "url": "https://www.ted.com/speakers/amy_cuddy"},
            {"name": "Dan Gilbert", "url": "https://www.ted.com/speakers/dan_gilbert"}
        ]
        
        for i, speaker in enumerate(test_speakers, 1):
            logger.info(f"\n[{i}/5] {speaker['name']}")
            
            speaker_data = {
                'name': speaker['name'],
                'ted_url': speaker['url'],
                'email': None,
                'website': None
            }
            
            # Simple Google search - just their name + university/website
            search_query = f"{speaker['name']} university professor email contact"
            logger.info(f"  Searching: {search_query}")
            
            driver.get(f"https://www.google.com/search?q={search_query}")
            driver.sleep(2)
            
            # Get all links from Google
            google_html = driver.page_html
            google_soup = BeautifulSoup(google_html, 'html.parser')
            
            # Find first .edu link
            for link in google_soup.find_all('a', href=True):
                href = link.get('href', '')
                
                # Check if it's a direct link to a university site
                if '.edu' in href and href.startswith('http'):
                    # Clean the URL
                    clean_url = href.split('#')[0].split('?')[0]
                    
                    # Make sure it's not Google's own link
                    if 'google' not in clean_url:
                        speaker_data['website'] = clean_url
                        logger.info(f"  Found: {clean_url}")
                        break
            
            # If no .edu, try .org
            if not speaker_data['website']:
                for link in google_soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if '.org' in href and href.startswith('http') and 'wikipedia' not in href:
                        clean_url = href.split('#')[0].split('?')[0]
                        if 'google' not in clean_url:
                            speaker_data['website'] = clean_url
                            logger.info(f"  Found: {clean_url}")
                            break
            
            # Visit the website to get email
            if speaker_data['website']:
                try:
                    logger.info(f"  Visiting website...")
                    # THIS IS THE KEY - use google_get with bypass_cloudflare=True
                    driver.google_get(speaker_data['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Make sure we're not blocked
                    current_url = driver.current_url
                    if "enable-javascript" not in current_url and "cloudflare" not in current_url:
                        website_html = driver.page_html
                        
                        # Find emails
                        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                        emails = re.findall(email_pattern, website_html)
                        
                        # Get the first valid email
                        for email in emails:
                            # Basic validation
                            if '@' in email and '.' in email.split('@')[1]:
                                # Filter out common fake/system emails
                                if not any(skip in email.lower() for skip in [
                                    'example', 'test', 'demo', 'sample', 'your',
                                    'email@', 'user@', 'name@', 'firstname',
                                    'lastname', 'sentry', 'wix', 'cloudflare',
                                    'javascript', 'noreply', 'donotreply',
                                    'webmaster', 'postmaster', 'admin@',
                                    'info@', 'support@', 'sales@'
                                ]):
                                    # Check if email might belong to the speaker
                                    name_parts = speaker['name'].lower().split()
                                    last_name = name_parts[-1] if name_parts else ''
                                    
                                    # Accept email if it contains part of their name
                                    # or if it's from a university domain
                                    if any(part in email.lower() for part in name_parts if len(part) > 3) or '.edu' in email:
                                        speaker_data['email'] = email
                                        logger.info(f"  EMAIL FOUND: {email}")
                                        break
                    else:
                        logger.info(f"  Blocked by protection")
                        
                except Exception as e:
                    logger.debug(f"  Error: {e}")
            
            results.append(speaker_data)
        
    except Exception as e:
        logger.error(f"Fatal: {e}")
    
    return results

def save_results(speakers):
    """Save to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_absolutely_final_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'ted_url'])
        writer.writeheader()
        writer.writerows(speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - ABSOLUTELY FINAL")
    print("Testing with 5 known speakers")
    print("="*80)
    
    results = scrape_ted_absolutely_final()
    
    if results:
        csv_file = save_results(results)
        
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  - Speakers: {len(results)}")
        print(f"  - With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  - With website: {with_website}")
        print(f"  - Saved: {csv_file}")
        
        print(f"\nDetails:")
        for s in results:
            print(f"\n{s['name']}:")
            if s.get('website'):
                print(f"  Website: {s['website']}")
            if s.get('email'):
                print(f"  [FOUND] Email: {s['email']}")
            if not s.get('email') and not s.get('website'):
                print(f"  [NONE] No data found")

if __name__ == "__main__":
    main()