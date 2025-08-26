#!/usr/bin/env python3
"""
TED Speaker Scraper - Working Version
Focus on what works, skip what's blocked
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
    headless=True,  # Run in background so you can work
    block_images=True
)
def scrape_ted_working(driver, data):
    """Scrape TED speakers - get what we can."""
    results = []
    
    try:
        # Go directly to TED speakers
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
        
        # Process speakers - focus on extracting from TED pages only
        for i, speaker_url in enumerate(speaker_links[:30], 1):  # Get 30 speakers
            logger.info(f"[{i}/30] Processing {speaker_url}")
            
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
            
            # Extract occupation/tagline (usually right under name)
            tagline = speaker_soup.find('p', class_=re.compile(r'tagline|subtitle|occupation', re.I))
            if tagline:
                speaker_data['occupation'] = tagline.get_text(strip=True)
            
            # Extract bio
            bio_elem = speaker_soup.find('div', class_=re.compile(r'bio|about', re.I))
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:500]
            
            # Look for social links ON THE TED PAGE
            # TED sometimes shows social media icons
            social_links = speaker_soup.find_all('a', href=True)
            for link in social_links:
                href = link.get('href', '')
                
                # Get Twitter handle
                if 'twitter.com' in href or 'x.com' in href:
                    match = re.search(r'(?:twitter\.com|x\.com)/([^/?]+)', href)
                    if match:
                        speaker_data['twitter'] = '@' + match.group(1)
                
                # Get personal website (but don't visit it)
                elif not any(x in href for x in ['ted.com', 'twitter', 'facebook', 'instagram', 'youtube', 'linkedin']):
                    if href.startswith('http') and not speaker_data['website']:
                        speaker_data['website'] = href
            
            # Search for email in the bio text itself
            # Some speakers include contact info in their bio
            full_text = speaker_soup.get_text()
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, full_text)
            
            for email in emails:
                if not any(fake in email.lower() for fake in ['example', 'domain', 'ted.com', 'javascript']):
                    speaker_data['email'] = email
                    logger.info(f"  ✓ Found email: {email}")
                    break
            
            # Try to extract email from website URL pattern
            # Many academics use firstname.lastname@university.edu
            if not speaker_data['email'] and speaker_data['name'] and speaker_data['website']:
                website = speaker_data['website']
                
                # Check if it's a university site
                if any(edu in website for edu in ['.edu', '.ac.uk', '.ac.']):
                    # Extract domain
                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', website)
                    if domain_match:
                        domain = domain_match.group(1)
                        
                        # Create likely email from name
                        name_parts = speaker_data['name'].lower().split()
                        if len(name_parts) >= 2:
                            first = name_parts[0]
                            last = name_parts[-1]
                            
                            # Common academic email patterns
                            likely_email = f"{first}.{last}@{domain}"
                            speaker_data['email'] = likely_email + " (predicted)"
                            logger.info(f"  ? Predicted email: {likely_email}")
            
            results.append(speaker_data)
            
            # Show progress
            if speaker_data['name']:
                info = f"  {speaker_data['name']}"
                if speaker_data['occupation']:
                    info += f" - {speaker_data['occupation']}"
                if speaker_data['email']:
                    info += f" ✓"
                logger.info(info)
        
    except Exception as e:
        logger.error(f"Error: {e}")
    
    return results

def save_results(speakers, filename=None):
    """Save results to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_final_{timestamp}.csv"
    
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
    """Run the working TED scraper."""
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - FINAL VERSION")
    print("="*80)
    
    # Run scraper
    results = scrape_ted_working()
    
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
        print(f"  • With email/predicted: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  • With website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  • With Twitter: {with_twitter}")
        print(f"  • Saved to: {csv_file}")
        
        # Show speakers with emails
        if with_email > 0:
            print(f"\nSpeakers with emails:")
            count = 0
            for speaker in results:
                if speaker.get('email'):
                    print(f"  • {speaker.get('name')}: {speaker['email']}")
                    count += 1
                    if count >= 10:
                        print(f"  ... and {with_email - 10} more")
                        break
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()