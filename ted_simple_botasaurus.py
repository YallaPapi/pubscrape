#!/usr/bin/env python3
"""
Simplified TED Speaker Scraper using Botasaurus
Focus on getting it working first, then optimize
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
    headless=False,  # Show browser for debugging
    block_images=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
def scrape_ted_speakers(driver, data):
    """Scrape TED speakers and their contact info."""
    results = []
    
    try:
        # Go to TED speakers page
        url = "https://www.ted.com/speakers"
        logger.info(f"Loading: {url}")
        driver.get(url)
        
        # Wait for page to load
        logger.info("Waiting for page to load...")
        driver.sleep(5)
        
        # Get HTML after JavaScript execution
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find speaker links
        logger.info("Looking for speaker links...")
        speaker_links = []
        
        # Try different selectors for speaker links
        # TED might use different class names
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            # Match pattern like /speakers/firstname_lastname
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speaker URLs")
        
        # Limit to first 10 for testing
        speaker_links = speaker_links[:10]
        
        # Visit each speaker page
        for i, speaker_url in enumerate(speaker_links, 1):
            logger.info(f"\n[{i}/{len(speaker_links)}] Visiting: {speaker_url}")
            driver.get(speaker_url)
            driver.sleep(3)
            
            # Get speaker page HTML
            speaker_html = driver.page_html
            speaker_soup = BeautifulSoup(speaker_html, 'html.parser')
            
            speaker_data = {
                'ted_url': speaker_url,
                'name': None,
                'bio': None,
                'website': None,
                'email': None
            }
            
            # Extract name (try multiple selectors)
            name_elem = speaker_soup.find('h1') or \
                       speaker_soup.find('div', class_='speaker-name') or \
                       speaker_soup.find('span', class_='name')
            
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  Name: {speaker_data['name']}")
            
            # Extract bio
            bio_elem = speaker_soup.find('div', class_='bio') or \
                      speaker_soup.find('p', class_='description')
            
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:300]
            
            # Look for external links (website, social media)
            external_links = speaker_soup.find_all('a', href=re.compile(r'^https?://(?!.*ted\.com)'))
            
            for ext_link in external_links:
                href = ext_link.get('href', '')
                if 'twitter' not in href and 'facebook' not in href and 'linkedin' not in href:
                    # Likely a personal website
                    speaker_data['website'] = href
                    logger.info(f"  Website: {href}")
                    break
            
            # If we found a website, visit it to find email
            if speaker_data['website']:
                try:
                    logger.info(f"  Checking website for email...")
                    driver.get(speaker_data['website'])
                    driver.sleep(2)
                    
                    website_html = driver.page_html
                    
                    # Look for email
                    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                    emails = re.findall(email_pattern, website_html)
                    
                    for email in emails:
                        if not any(fake in email.lower() for fake in ['example', 'domain', 'email@', 'test']):
                            speaker_data['email'] = email
                            logger.info(f"  Found email: {email}")
                            break
                            
                except Exception as e:
                    logger.debug(f"  Error checking website: {e}")
            
            results.append(speaker_data)
            
    except Exception as e:
        logger.error(f"Error: {e}")
    
    return results

def save_results(speakers, filename=None):
    """Save results to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'email', 'website', 'bio', 'ted_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for speaker in speakers:
            writer.writerow(speaker)
    
    return str(csv_path)

def main():
    """Run the simplified TED scraper."""
    print("\n" + "="*80)
    print("SIMPLIFIED TED SPEAKER SCRAPER")
    print("="*80)
    
    # Run the scraper
    results = scrape_ted_speakers()
    
    if results:
        # Save to CSV
        csv_file = save_results(results)
        
        # Stats
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  • Speakers scraped: {len(results)}")
        print(f"  • With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  • With website: {with_website}")
        print(f"  • Saved to: {csv_file}")
        
        # Show sample
        print("\nSample results:")
        for speaker in results[:5]:
            print(f"\n{speaker.get('name', 'Unknown')}:")
            if speaker.get('email'):
                print(f"  Email: {speaker['email']}")
            if speaker.get('website'):
                print(f"  Website: {speaker['website']}")
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()