#!/usr/bin/env python3
"""
TED Speaker Scraper - WORKING Cloudflare Bypass
Using the CORRECT google_get parameters
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

@browser(
    headless=True,  # Run in background
    block_images=True,
    reuse_driver=True  # Reuse browser for speed
)
def scrape_ted_proper(driver, data):
    """Scrape TED speakers with PROPER Cloudflare bypass."""
    results = []
    
    try:
        # Load TED speakers page
        url = "https://www.ted.com/speakers"
        logger.info(f"Loading TED speakers page...")
        driver.get(url)
        driver.sleep(5)
        
        # Get page HTML
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find speaker links
        speaker_links = []
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speaker profiles")
        
        # Process 50 speakers
        for i, speaker_url in enumerate(speaker_links[:50], 1):
            logger.info(f"\n[{i}/50] Processing speaker...")
            
            driver.get(speaker_url)
            driver.sleep(2)
            
            speaker_html = driver.page_html
            speaker_soup = BeautifulSoup(speaker_html, 'html.parser')
            
            speaker_data = {
                'ted_url': speaker_url,
                'name': None,
                'bio': None,
                'website': None,
                'email': None,
                'twitter': None,
                'occupation': None
            }
            
            # Extract name
            name_elem = speaker_soup.find('h1')
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  Name: {speaker_data['name']}")
            
            # Extract occupation
            tagline = speaker_soup.find('p', class_=re.compile(r'tagline|subtitle', re.I))
            if tagline:
                speaker_data['occupation'] = tagline.get_text(strip=True)
            
            # Extract bio
            bio_elem = speaker_soup.find('div', class_=re.compile(r'bio|about', re.I))
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:500]
            
            # Find external links
            external_links = speaker_soup.find_all('a', href=True)
            for link in external_links:
                href = link.get('href', '')
                
                # Get Twitter
                if 'twitter.com' in href or 'x.com' in href:
                    match = re.search(r'(?:twitter\.com|x\.com)/([^/?]+)', href)
                    if match:
                        speaker_data['twitter'] = '@' + match.group(1)
                
                # Get personal website
                elif not any(x in href for x in ['ted.com', 'twitter', 'facebook', 'instagram', 'youtube', 'linkedin']):
                    if href.startswith('http') and not speaker_data['website']:
                        speaker_data['website'] = href
            
            # NOW THE IMPORTANT PART - Visit website with PROPER Cloudflare bypass
            if speaker_data['website']:
                try:
                    logger.info(f"  Checking website: {speaker_data['website']}")
                    
                    # USE google_get WITH bypass_cloudflare=True !!!!
                    driver.google_get(speaker_data['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Check if we actually bypassed
                    current_url = driver.current_url
                    if "enable-javascript" not in current_url and "cloudflare" not in current_url.lower():
                        # We're in! Extract emails
                        website_html = driver.page_html
                        
                        # Find all emails
                        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                        emails = re.findall(email_pattern, website_html)
                        
                        # Filter out fake emails
                        for email in emails:
                            if not any(fake in email.lower() for fake in 
                                     ['example', 'domain', 'email@', 'test', 'sample', 
                                      'javascript', 'cloudflare', 'protected', 'your', 'sentry']):
                                speaker_data['email'] = email
                                logger.info(f"  ✓ Found email: {email}")
                                break
                        
                        # If no email on main page, check contact page
                        if not speaker_data['email']:
                            website_soup = BeautifulSoup(website_html, 'html.parser')
                            contact_links = website_soup.find_all('a', href=re.compile(r'contact|about', re.I))
                            
                            for contact_link in contact_links[:2]:
                                try:
                                    contact_href = contact_link.get('href', '')
                                    if contact_href.startswith('/'):
                                        contact_url = speaker_data['website'].rstrip('/') + contact_href
                                    elif contact_href.startswith('http'):
                                        contact_url = contact_href
                                    else:
                                        continue
                                    
                                    logger.info(f"    Checking contact page...")
                                    # Also use bypass for contact page!
                                    driver.google_get(contact_url, bypass_cloudflare=True)
                                    driver.sleep(2)
                                    
                                    contact_html = driver.page_html
                                    emails = re.findall(email_pattern, contact_html)
                                    
                                    for email in emails:
                                        if not any(fake in email.lower() for fake in 
                                                 ['example', 'domain', 'test', 'sample']):
                                            speaker_data['email'] = email
                                            logger.info(f"    ✓ Found email on contact page: {email}")
                                            break
                                    
                                    if speaker_data['email']:
                                        break
                                        
                                except Exception as e:
                                    logger.debug(f"    Error checking contact page: {e}")
                    else:
                        logger.info(f"    Still blocked by Cloudflare")
                        
                except Exception as e:
                    logger.debug(f"  Error checking website: {e}")
            
            results.append(speaker_data)
            
            # Show progress
            if speaker_data['email']:
                logger.info(f"  SUCCESS: {speaker_data['name']} - {speaker_data['email']}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers, filename=None):
    """Save results to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_cloudflare_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'occupation', 'email', 'website', 'twitter', 'bio', 'ted_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for speaker in speakers:
            writer.writerow(speaker)
    
    return str(csv_path)

def main():
    """Run the WORKING TED scraper."""
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - CLOUDFLARE BYPASS WORKING")
    print("="*80)
    
    # Run scraper
    results = scrape_ted_proper()
    
    if results:
        # Save results
        csv_file = save_results(results)
        
        # Stats
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        with_twitter = sum(1 for s in results if s.get('twitter'))
        
        print(f"\n" + "="*80)
        print("SCRAPING COMPLETE!")
        print("="*80)
        print(f"\nResults:")
        print(f"  • Total speakers: {len(results)}")
        print(f"  • With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  • With website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  • With Twitter: {with_twitter}")
        print(f"  • Saved to: {csv_file}")
        
        # Show all speakers with emails
        if with_email > 0:
            print(f"\nSpeakers with emails found:")
            for speaker in results:
                if speaker.get('email'):
                    print(f"  • {speaker.get('name')}: {speaker['email']}")
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()