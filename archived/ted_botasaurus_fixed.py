#!/usr/bin/env python3
"""
TED Speaker Scraper with Cloudflare Bypass
Using all available Botasaurus anti-detection features
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import csv
import re
import time
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

@browser(
    headless=False,  # Keep visible for now to debug
    block_images=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def scrape_ted_with_bypass(driver, data):
    """Scrape TED speakers with Cloudflare bypass."""
    results = []
    
    try:
        # Use google_get to appear as coming from Google
        url = "https://www.ted.com/speakers"
        logger.info(f"Loading TED speakers page via Google...")
        driver.google_get(url)
        
        # Add human-like delay
        driver.short_random_sleep()
        
        # Detect and bypass any Cloudflare challenges
        driver.detect_and_bypass_cloudflare()
        
        # Get page HTML
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find speaker links
        logger.info("Finding speaker links...")
        speaker_links = []
        
        # Find all links that match speaker pattern
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speaker profiles")
        
        # Limit to 20 for testing
        speaker_links = speaker_links[:20]
        
        # Process each speaker
        for i, speaker_url in enumerate(speaker_links, 1):
            logger.info(f"\n[{i}/{len(speaker_links)}] Processing speaker...")
            
            # Use google_get for speaker page too
            driver.google_get(speaker_url)
            driver.short_random_sleep()
            
            # Get speaker page HTML
            speaker_html = driver.page_html
            speaker_soup = BeautifulSoup(speaker_html, 'html.parser')
            
            speaker_data = {
                'ted_url': speaker_url,
                'name': None,
                'bio': None,
                'website': None,
                'email': None,
                'twitter': None,
                'linkedin': None
            }
            
            # Extract name
            name_elem = speaker_soup.find('h1') or \
                       speaker_soup.find(['div', 'span'], class_=re.compile(r'name', re.I))
            
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  Name: {speaker_data['name']}")
            
            # Extract bio
            bio_elem = speaker_soup.find(['div', 'p'], class_=re.compile(r'bio|description|about', re.I))
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:300]
            
            # Find all external links
            external_links = speaker_soup.find_all('a', href=re.compile(r'^https?://(?!.*ted\.com)'))
            
            for ext_link in external_links:
                href = ext_link.get('href', '')
                
                # Categorize links
                if 'twitter.com' in href or 'x.com' in href:
                    speaker_data['twitter'] = href
                elif 'linkedin.com' in href:
                    speaker_data['linkedin'] = href
                elif not any(social in href for social in ['facebook', 'instagram', 'youtube']):
                    # Potential personal website
                    if not speaker_data['website']:
                        speaker_data['website'] = href
                        logger.info(f"  Found website: {href}")
            
            # Try to get email from personal website
            if speaker_data['website']:
                try:
                    logger.info(f"  Checking website for contact info...")
                    
                    # Use google_get with bypass for external website
                    driver.google_get(speaker_data['website'])
                    driver.short_random_sleep()
                    
                    # Try to bypass any protection on the personal site
                    driver.detect_and_bypass_cloudflare()
                    
                    website_html = driver.page_html
                    
                    # Extract emails
                    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                    emails = re.findall(email_pattern, website_html)
                    
                    for email in emails:
                        if not any(fake in email.lower() for fake in 
                                 ['example', 'domain', 'email@', 'test', 'sample', 'javascript', 'protected']):
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
                                    contact_url = speaker_data['website'].rstrip('/') + '/' + contact_href
                                
                                logger.info(f"    Checking contact page: {contact_url}")
                                driver.google_get(contact_url)
                                driver.short_random_sleep()
                                
                                contact_html = driver.page_html
                                emails = re.findall(email_pattern, contact_html)
                                
                                for email in emails:
                                    if not any(fake in email.lower() for fake in 
                                             ['example', 'domain', 'email@', 'test', 'sample']):
                                        speaker_data['email'] = email
                                        logger.info(f"  ✓ Found email on contact page: {email}")
                                        break
                                
                                if speaker_data['email']:
                                    break
                                    
                            except Exception as e:
                                logger.debug(f"    Error checking contact page: {e}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"  Error checking website: {e}")
            
            results.append(speaker_data)
            
            # Random delay between speakers
            if i < len(speaker_links):
                driver.short_random_sleep()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers, filename=None):
    """Save results to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_bypass_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'email', 'website', 'twitter', 'linkedin', 'bio', 'ted_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for speaker in speakers:
            writer.writerow(speaker)
    
    return str(csv_path)

def main():
    """Run the TED scraper with Cloudflare bypass."""
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER WITH CLOUDFLARE BYPASS")
    print("="*80)
    
    # Run scraper
    results = scrape_ted_with_bypass()
    
    if results:
        # Save results
        csv_file = save_results(results)
        
        # Calculate stats
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        with_social = sum(1 for s in results if s.get('twitter') or s.get('linkedin'))
        
        print(f"\n" + "="*80)
        print("SCRAPING COMPLETE!")
        print(f"  • Total speakers: {len(results)}")
        print(f"  • With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  • With website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  • With social media: {with_social}")
        print(f"  • Saved to: {csv_file}")
        
        # Show speakers with emails
        if with_email > 0:
            print(f"\nSpeakers with emails found:")
            for speaker in results:
                if speaker.get('email'):
                    print(f"  • {speaker.get('name')}: {speaker['email']}")
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()