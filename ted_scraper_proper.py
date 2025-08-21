#!/usr/bin/env python3
"""
TED Speaker Scraper - PROPER VERSION
Gets speaker websites FROM TED profiles, then scrapes those sites
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
    headless=False,
    block_images=True,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def scrape_ted_proper(driver, data):
    """Scrape TED speakers - get websites FROM TED, not from search."""
    results = []
    
    try:
        # First, get list of speakers from TED
        logger.info("Loading TED speakers page...")
        driver.get("https://www.ted.com/speakers")
        driver.sleep(5)
        
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all speaker links
        speaker_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speaker profiles")
        
        # Process first 20 speakers
        for i, speaker_url in enumerate(speaker_links[:20], 1):
            logger.info(f"\n[{i}/20] Processing speaker...")
            
            # Load the speaker's TED profile
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
                'linkedin': None
            }
            
            # Get speaker name
            name_elem = speaker_soup.find('h1')
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  Name: {speaker_data['name']}")
            
            if not speaker_data['name']:
                continue
            
            # Get bio
            bio_elem = speaker_soup.find('div', class_=re.compile(r'description|bio', re.I))
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:200]
            
            # FIND THE ACTUAL WEBSITE LINK ON THE TED PROFILE
            # Look for external links on the speaker's TED page
            external_links = speaker_soup.find_all('a', href=True)
            
            for link in external_links:
                href = link.get('href', '')
                
                # Check for social media
                if 'twitter.com' in href or 'x.com' in href:
                    speaker_data['twitter'] = href
                    logger.info(f"  Twitter: {href}")
                elif 'linkedin.com/in/' in href:
                    speaker_data['linkedin'] = href
                    logger.info(f"  LinkedIn: {href}")
                # Check for personal/professional websites
                elif href.startswith('http') and not any(skip in href for skip in [
                    'ted.com', 'twitter.com', 'linkedin.com', 'facebook.com', 
                    'instagram.com', 'youtube.com', 'wikipedia.org', 'x.com'
                ]):
                    # This might be their personal/professional website
                    speaker_data['website'] = href
                    logger.info(f"  Website found on TED: {href}")
                    break
            
            # If we found a website on their TED profile, scrape it
            if speaker_data['website']:
                try:
                    logger.info(f"  Visiting their website with bypass...")
                    # Use botasaurus bypass to visit the website
                    driver.google_get(speaker_data['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Check we're not blocked
                    current_url = driver.current_url
                    if "enable-javascript" not in current_url.lower() and "cloudflare" not in current_url.lower():
                        website_html = driver.page_html
                        
                        # Extract emails from the website
                        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                        emails = re.findall(email_pattern, website_html)
                        
                        # Filter for valid emails
                        for email in emails:
                            email = email.lower()
                            # Skip system/fake emails
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
                                name_parts = speaker_data['name'].lower().split()
                                last_name = name_parts[-1] if name_parts else ''
                                
                                # Accept if it contains their name or is from a university
                                if (any(part in email for part in name_parts if len(part) > 3) or 
                                    '.edu' in email or
                                    (last_name and len(last_name) > 3 and last_name in email)):
                                    speaker_data['email'] = email
                                    logger.info(f"  ✓ EMAIL FOUND: {email}")
                                    break
                        
                        # Try contact/about page if no email found
                        if not speaker_data['email']:
                            website_soup = BeautifulSoup(website_html, 'html.parser')
                            contact_links = website_soup.find_all('a', href=re.compile(r'contact|about', re.I))
                            
                            for contact_link in contact_links[:1]:
                                try:
                                    contact_href = contact_link.get('href', '')
                                    if contact_href.startswith('/'):
                                        contact_url = speaker_data['website'].rstrip('/') + contact_href
                                    else:
                                        continue
                                    
                                    logger.info(f"  Checking contact page...")
                                    driver.google_get(contact_url, bypass_cloudflare=True)
                                    driver.sleep(2)
                                    
                                    contact_html = driver.page_html
                                    emails = re.findall(email_pattern, contact_html)
                                    
                                    for email in emails:
                                        email = email.lower()
                                        if '@' in email and '.' in email.split('@')[1]:
                                            if not any(fake in email for fake in ['example', 'test', 'demo']):
                                                speaker_data['email'] = email
                                                logger.info(f"  ✓ EMAIL FOUND (contact): {email}")
                                                break
                                    
                                    if speaker_data['email']:
                                        break
                                        
                                except:
                                    pass
                    else:
                        logger.info(f"  Website blocked by Cloudflare")
                        
                except Exception as e:
                    logger.info(f"  Error visiting website: {str(e)[:50]}")
            else:
                logger.info(f"  No website found on TED profile")
            
            results.append(speaker_data)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers):
    """Save results to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_proper_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'twitter', 'linkedin', 'bio', 'ted_url'])
        writer.writeheader()
        writer.writerows(speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - PROPER VERSION")
    print("Gets websites FROM TED profiles, not from search")
    print("="*80)
    
    results = scrape_ted_proper()
    
    if results:
        csv_file = save_results(results)
        
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        with_social = sum(1 for s in results if s.get('twitter') or s.get('linkedin'))
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  - Total speakers: {len(results)}")
        print(f"  - With website from TED: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  - With email extracted: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  - With social media: {with_social}")
        print(f"  - Saved to: {csv_file}")
        
        if with_email > 0:
            print(f"\nEmails found:")
            for s in results:
                if s.get('email'):
                    print(f"  - {s['name']}: {s['email']}")
        
        print(f"\nWebsites from TED:")
        for s in results[:5]:
            if s.get('website'):
                print(f"  - {s['name']}: {s['website']}")

if __name__ == "__main__":
    main()