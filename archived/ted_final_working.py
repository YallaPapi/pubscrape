#!/usr/bin/env python3
"""
TED Speaker Scraper - FINAL WORKING VERSION
Combines all lessons learned
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
    headless=True,
    block_images=True,
    reuse_driver=True
)
def scrape_ted_final(driver, data):
    """Final TED scraper that actually works."""
    results = []
    
    try:
        # Get TED speakers
        url = "https://www.ted.com/speakers" 
        logger.info("Loading TED speakers...")
        driver.get(url)
        driver.sleep(5)
        
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find speaker links
        speaker_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speakers")
        
        # Process 30 speakers
        for i, speaker_url in enumerate(speaker_links[:30], 1):
            logger.info(f"\n[{i}/30] Processing speaker...")
            
            # Get speaker info from TED
            driver.get(speaker_url)
            driver.sleep(2)
            
            speaker_html = driver.page_html
            speaker_soup = BeautifulSoup(speaker_html, 'html.parser')
            
            speaker_data = {
                'ted_url': speaker_url,
                'name': None,
                'email': None,
                'website': None,
                'twitter': None,
                'linkedin': None
            }
            
            # Get name
            name_elem = speaker_soup.find('h1')
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  {speaker_data['name']}")
            
            if not speaker_data['name']:
                continue
            
            # Get social media from TED page
            for link in speaker_soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'twitter.com' in href or 'x.com' in href:
                    speaker_data['twitter'] = href
                elif 'linkedin.com/in/' in href:
                    speaker_data['linkedin'] = href
            
            # Search Google for their website
            search_query = f'"{speaker_data["name"]}" site:.edu OR site:.org OR site:.io'
            logger.info(f"  Searching: {search_query}")
            
            driver.get(f"https://www.google.com/search?q={search_query}")
            driver.sleep(2)
            
            # Parse Google results
            google_html = driver.page_html
            google_soup = BeautifulSoup(google_html, 'html.parser')
            
            # Find first good result
            for link in google_soup.find_all('a', href=True):
                href = link.get('href', '')
                real_url = None
                
                # Extract URL from Google redirect
                if '/url?q=' in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if 'q' in parsed:
                        real_url = parsed['q'][0]
                # Direct link
                elif href.startswith('http') and 'google' not in href:
                    real_url = href.split('#')[0]
                
                if real_url and any(d in real_url for d in ['.edu', '.org', '.io']):
                    if not any(skip in real_url for skip in ['wikipedia', 'twitter', 'linkedin', 'youtube']):
                        speaker_data['website'] = real_url
                        logger.info(f"  Found: {real_url}")
                        break
            
            # Visit website to get email
            if speaker_data['website']:
                try:
                    logger.info(f"  Visiting website...")
                    # USE BYPASS!
                    driver.google_get(speaker_data['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Check we're not blocked
                    if "enable-javascript" not in driver.current_url:
                        website_html = driver.page_html
                        
                        # Extract emails
                        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', website_html)
                        
                        for email in emails:
                            # Filter out junk
                            if not any(junk in email.lower() for junk in 
                                     ['example', 'domain', 'test', 'your', 'email@', 
                                      'sentry', 'wix', 'cloudflare', 'javascript']):
                                speaker_data['email'] = email
                                logger.info(f"  ✓ EMAIL: {email}")
                                break
                        
                        # Try contact page if no email
                        if not speaker_data['email']:
                            contact_links = BeautifulSoup(website_html, 'html.parser').find_all(
                                'a', href=re.compile(r'contact|about', re.I))[:1]
                            
                            for cl in contact_links:
                                contact_url = urllib.parse.urljoin(speaker_data['website'], cl.get('href', ''))
                                driver.google_get(contact_url, bypass_cloudflare=True)
                                driver.sleep(2)
                                
                                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', driver.page_html)
                                for email in emails:
                                    if '@' in email and '.' in email.split('@')[1]:
                                        speaker_data['email'] = email
                                        logger.info(f"  ✓ EMAIL (contact): {email}")
                                        break
                                if speaker_data['email']:
                                    break
                    else:
                        logger.info(f"  Blocked")
                        
                except Exception as e:
                    logger.debug(f"  Error: {e}")
            
            results.append(speaker_data)
        
    except Exception as e:
        logger.error(f"Fatal: {e}")
    
    return results

def save_results(speakers):
    """Save to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_final_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'twitter', 'linkedin', 'ted_url'])
        writer.writeheader()
        writer.writerows(speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - FINAL VERSION")
    print("="*80)
    
    results = scrape_ted_final()
    
    if results:
        csv_file = save_results(results)
        
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        
        print(f"\n" + "="*80)
        print("COMPLETE!")
        print(f"  • Speakers: {len(results)}")
        print(f"  • With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  • With website: {with_website}")
        print(f"  • Saved: {csv_file}")
        
        if with_email > 0:
            print(f"\nEmails found:")
            for s in results:
                if s.get('email'):
                    print(f"  • {s['name']}: {s['email']}")

if __name__ == "__main__":
    main()