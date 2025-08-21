#!/usr/bin/env python3
"""
TED Speaker Smart Scraper
Since TED blocks direct website links, we'll:
1. Get speaker name and info from TED
2. Search Google for their actual website
3. Visit the real website with Cloudflare bypass
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
    headless=True,
    block_images=True,
    reuse_driver=True
)
def scrape_ted_smart(driver, data):
    """Smart TED scraper that finds real websites."""
    results = []
    
    try:
        # Load TED speakers page
        url = "https://www.ted.com/speakers"
        logger.info(f"Loading TED speakers page...")
        driver.get(url)
        driver.sleep(5)
        
        # Get speaker links
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        speaker_links = []
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speaker profiles")
        
        # Process 20 speakers
        for i, speaker_url in enumerate(speaker_links[:20], 1):
            logger.info(f"\n[{i}/20] Processing speaker...")
            
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
                'linkedin': None,
                'occupation': None
            }
            
            # Extract name
            name_elem = speaker_soup.find('h1')
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  Name: {speaker_data['name']}")
            
            # Extract occupation/tagline
            tagline = speaker_soup.find('p', class_=re.compile(r'tagline|subtitle', re.I))
            if tagline:
                speaker_data['occupation'] = tagline.get_text(strip=True)
            
            # Extract bio
            bio_elem = speaker_soup.find('div', class_=re.compile(r'bio|about', re.I))
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:300]
            
            # Extract social media (these work!)
            external_links = speaker_soup.find_all('a', href=True)
            for link in external_links:
                href = link.get('href', '')
                
                if 'twitter.com' in href or 'x.com' in href:
                    speaker_data['twitter'] = href
                elif 'linkedin.com/in/' in href:
                    speaker_data['linkedin'] = href
            
            # SMART PART: Search for their real website
            if speaker_data['name']:
                logger.info(f"  Searching for real website...")
                
                # Search Google for the person
                occupation = speaker_data.get('occupation', '')
                search_query = f"{speaker_data['name']} {occupation} website TED speaker"
                driver.get(f"https://www.google.com/search?q={search_query}")
                driver.sleep(2)
                
                # Look for likely personal/university websites in search results
                search_html = driver.page_html
                search_soup = BeautifulSoup(search_html, 'html.parser')
                
                # Find search result links
                search_links = search_soup.find_all('a', href=True)
                for search_link in search_links:
                    href = search_link.get('href', '')
                    real_url = None
                    
                    # Extract actual URL from Google's redirect
                    if '/url?q=' in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'q' in parsed:
                            real_url = parsed['q'][0]
                    # Handle direct links
                    elif href.startswith('http') and 'google' not in href:
                        real_url = href.split('#')[0]  # Remove anchor tags
                    
                    if real_url:
                        # Check if it's likely a personal/professional site
                        if any(domain in real_url for domain in ['.edu', '.org', '.io']) and \
                           not any(social in real_url for social in ['twitter', 'linkedin', 'facebook', 'youtube', 'wikipedia', 'ted.com', 'amazon']):
                            
                            # Since we searched for their name, the first non-social result is likely correct
                            speaker_data['website'] = real_url
                            logger.info(f"    Found likely website: {real_url}")
                            break
                        # Also accept .com sites if they contain the person's last name
                        elif '.com' in real_url and not any(social in real_url for social in ['twitter', 'linkedin', 'facebook', 'youtube', 'wikipedia', 'ted.com', 'amazon', 'google']):
                            name_parts = speaker_data['name'].lower().split()
                            last_name = name_parts[-1] if name_parts else ''
                            if last_name and len(last_name) > 2 and last_name in real_url.lower():
                                speaker_data['website'] = real_url
                                logger.info(f"    Found likely website: {real_url}")
                                break
            
            # Now visit the REAL website with bypass
            if speaker_data['website']:
                try:
                    logger.info(f"  Visiting real website with bypass...")
                    driver.google_get(speaker_data['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    website_html = driver.page_html
                    current_url = driver.current_url
                    
                    # Make sure we're not on a block page
                    if "enable-javascript" not in current_url and "cloudflare" not in current_url.lower():
                        # Extract emails
                        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                        emails = re.findall(email_pattern, website_html)
                        
                        for email in emails:
                            if not any(fake in email.lower() for fake in 
                                     ['example', 'domain', 'test', 'sample', 'javascript', 
                                      'cloudflare', 'protected', 'your', 'sentry', 'email@']):
                                speaker_data['email'] = email
                                logger.info(f"  ✓ Found email: {email}")
                                break
                        
                        # Try contact page if no email found
                        if not speaker_data['email']:
                            website_soup = BeautifulSoup(website_html, 'html.parser')
                            contact_links = website_soup.find_all('a', href=re.compile(r'contact|about', re.I))
                            
                            for contact_link in contact_links[:1]:  # Just try first one
                                try:
                                    contact_href = contact_link.get('href', '')
                                    if contact_href.startswith('/'):
                                        contact_url = speaker_data['website'].rstrip('/') + contact_href
                                    else:
                                        continue
                                    
                                    driver.google_get(contact_url, bypass_cloudflare=True)
                                    driver.sleep(2)
                                    
                                    contact_html = driver.page_html
                                    emails = re.findall(email_pattern, contact_html)
                                    
                                    for email in emails:
                                        if not any(fake in email.lower() for fake in ['example', 'domain']):
                                            speaker_data['email'] = email
                                            logger.info(f"  ✓ Found email on contact page: {email}")
                                            break
                                    
                                    if speaker_data['email']:
                                        break
                                        
                                except:
                                    pass
                    
                except Exception as e:
                    logger.debug(f"  Error visiting website: {e}")
            
            # Also check LinkedIn for contact info if we have it
            if not speaker_data['email'] and speaker_data['linkedin']:
                # LinkedIn profiles sometimes have contact info visible
                # but we won't scrape LinkedIn directly to avoid issues
                pass
            
            results.append(speaker_data)
            
            if speaker_data['email']:
                logger.info(f"  SUCCESS: Found {speaker_data['name']} - {speaker_data['email']}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers, filename=None):
    """Save results to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_smart_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'occupation', 'email', 'website', 'twitter', 'linkedin', 'bio', 'ted_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for speaker in speakers:
            writer.writerow(speaker)
    
    return str(csv_path)

def main():
    """Run the smart TED scraper."""
    print("\n" + "="*80)
    print("TED SPEAKER SMART SCRAPER")
    print("Finding real websites through search")
    print("="*80)
    
    # Run scraper
    results = scrape_ted_smart()
    
    if results:
        # Save results
        csv_file = save_results(results)
        
        # Stats
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        with_social = sum(1 for s in results if s.get('twitter') or s.get('linkedin'))
        
        print(f"\n" + "="*80)
        print("SCRAPING COMPLETE!")
        print("="*80)
        print(f"\nResults:")
        print(f"  • Total speakers: {len(results)}")
        print(f"  • With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  • With real website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  • With social media: {with_social}")
        print(f"  • Saved to: {csv_file}")
        
        # Show all emails found
        if with_email > 0:
            print(f"\nEmails found:")
            for speaker in results:
                if speaker.get('email'):
                    print(f"  • {speaker.get('name')}: {speaker['email']}")
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()