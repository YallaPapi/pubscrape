#!/usr/bin/env python3
"""
TED Speaker Scraper - Maximum Stealth Mode
Using Botasaurus with all anti-detection features
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
    headless=False,
    block_images=False,  # Don't block images - looks more human
    reuse_driver=True,
    user_agent=None  # Let Botasaurus use its stealth user agent
)
def scrape_ted_stealth(driver, data):
    """Scrape TED speakers with maximum stealth."""
    results = []
    
    try:
        # First, visit Google to establish a browsing pattern
        logger.info("Establishing browsing pattern...")
        driver.get("https://www.google.com")
        driver.short_random_sleep()
        
        # Search for TED on Google (more natural)
        search_box = driver.get_element_or_none("input[name='q']")
        if search_box:
            search_box.type("TED speakers")
            driver.short_random_sleep()
            search_box.press("Enter")
            driver.short_random_sleep()
        
        # Now go to TED directly
        url = "https://www.ted.com/speakers"
        logger.info(f"Navigating to TED...")
        driver.get(url)
        
        # Wait and act human
        driver.long_random_sleep()
        
        # Check if we're on a Cloudflare page
        if "enable-javascript" in driver.current_url or "cloudflare" in driver.page_html.lower():
            logger.info("Cloudflare detected, attempting bypass...")
            driver.detect_and_bypass_cloudflare()
            driver.long_random_sleep()
        
        # Get page HTML
        html = driver.page_html
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find speaker links
        logger.info("Finding speaker links...")
        speaker_links = []
        
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if re.match(r'^/speakers/[a-z_]+$', href):
                full_url = f"https://www.ted.com{href}"
                if full_url not in speaker_links:
                    speaker_links.append(full_url)
        
        logger.info(f"Found {len(speaker_links)} speaker profiles")
        
        # Process only 5 speakers for testing
        speaker_links = speaker_links[:5]
        
        for i, speaker_url in enumerate(speaker_links, 1):
            logger.info(f"\n[{i}/{len(speaker_links)}] Processing speaker...")
            
            # Navigate naturally - don't use google_get for internal TED pages
            driver.get(speaker_url)
            driver.short_random_sleep()
            
            # Scroll a bit to look human
            driver.run_js("window.scrollTo(0, 300);")
            driver.short_random_sleep()
            
            speaker_html = driver.page_html
            speaker_soup = BeautifulSoup(speaker_html, 'html.parser')
            
            speaker_data = {
                'ted_url': speaker_url,
                'name': None,
                'bio': None,
                'website': None,
                'email': None
            }
            
            # Extract name
            name_elem = speaker_soup.find('h1')
            if name_elem:
                speaker_data['name'] = name_elem.get_text(strip=True)
                logger.info(f"  Name: {speaker_data['name']}")
            
            # Extract bio
            bio_elem = speaker_soup.find(['div', 'p'], class_=re.compile(r'bio|description', re.I))
            if bio_elem:
                speaker_data['bio'] = bio_elem.get_text(strip=True)[:300]
            
            # Instead of following external links, just extract them
            # We'll note them but not visit (to avoid Cloudflare)
            external_links = speaker_soup.find_all('a', href=re.compile(r'^https?://(?!.*ted\.com)'))
            
            for ext_link in external_links:
                href = ext_link.get('href', '')
                if not any(social in href for social in ['twitter', 'facebook', 'instagram', 'youtube', 'linkedin']):
                    if not speaker_data['website']:
                        speaker_data['website'] = href
                        logger.info(f"  Website found (not visiting): {href}")
                        break
            
            # Look for email in the TED page itself (sometimes in bio)
            page_text = speaker_soup.get_text()
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, page_text)
            
            for email in emails:
                if not any(fake in email.lower() for fake in ['example', 'domain', 'ted.com']):
                    speaker_data['email'] = email
                    logger.info(f"  Email found on TED page: {email}")
                    break
            
            results.append(speaker_data)
            
            # Random human-like delay
            if i < len(speaker_links):
                driver.long_random_sleep()
        
        # Now let's try a different approach for one speaker's website
        # Use a completely new browser session
        if results and results[0].get('website'):
            logger.info("\n\nTrying alternative approach for one website...")
            test_site = results[0]['website']
            
            # Open in new tab approach
            driver.run_js(f"window.open('{test_site}', '_blank');")
            driver.short_random_sleep()
            
            # Switch to new tab
            driver.switch_to_window(1)
            driver.short_random_sleep()
            
            # Check if we got blocked
            current_url = driver.current_url
            if "enable-javascript" not in current_url:
                logger.info(f"  Successfully loaded: {current_url}")
                
                # Try to find email
                website_html = driver.page_html
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', website_html)
                
                for email in emails:
                    if not any(fake in email.lower() for fake in ['example', 'domain', 'javascript']):
                        results[0]['email'] = email
                        logger.info(f"  ✓ Found email: {email}")
                        break
            else:
                logger.info(f"  Still blocked by Cloudflare")
            
            # Close tab and switch back
            driver.close()
            driver.switch_to_window(0)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers, filename=None):
    """Save results to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_stealth_{timestamp}.csv"
    
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
    """Run the stealth TED scraper."""
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - STEALTH MODE")
    print("="*80)
    
    # Run scraper
    results = scrape_ted_stealth()
    
    if results:
        # Save results
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
        
        print("\nSpeakers found:")
        for speaker in results:
            print(f"\n{speaker.get('name', 'Unknown')}:")
            if speaker.get('email'):
                print(f"  ✓ Email: {speaker['email']}")
            if speaker.get('website'):
                print(f"  • Website: {speaker['website']}")
    else:
        print("\nNo results found!")

if __name__ == "__main__":
    main()