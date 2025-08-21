#!/usr/bin/env python3
"""
TED Speaker Scraper using Botasaurus
Bypasses Cloudflare protection and extracts speaker contact information
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
    headless=False,  # Set to False for debugging, True for production
    block_images=True,  # Speed up by not loading images
    reuse_driver=True,  # Reuse browser instance
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
def scrape_ted_speaker_profile(driver, speaker_url):
    """Scrape a single TED speaker profile page."""
    try:
        logger.info(f"Scraping: {speaker_url}")
        driver.get(speaker_url)
        
        # Wait for page to load and handle any Cloudflare challenges
        driver.sleep(3)  # Botasaurus's smart sleep
        
        # Get page source after JavaScript execution
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        speaker_data = {}
        
        # Extract speaker name
        name_elem = soup.find('h1', class_='text-textPrimary') or \
                   soup.find('h1') or \
                   soup.find('div', class_='speaker-name')
        
        speaker_data['name'] = name_elem.get_text(strip=True) if name_elem else None
        
        # Extract bio/description
        bio_elem = soup.find('div', class_='text-textSecondary') or \
                  soup.find('div', class_='speaker-bio') or \
                  soup.find('p', class_='speaker-description')
        
        speaker_data['bio'] = bio_elem.get_text(strip=True)[:500] if bio_elem else None
        
        # Extract occupation/title
        occupation_elem = soup.find('div', class_='speaker-occupation') or \
                         soup.find('span', class_='speaker-title')
        
        speaker_data['occupation'] = occupation_elem.get_text(strip=True) if occupation_elem else None
        
        # Look for external links (personal website, social media)
        links = {
            'website': None,
            'twitter': None,
            'linkedin': None,
            'facebook': None,
            'instagram': None
        }
        
        # Find all external links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            
            # Skip TED internal links
            if 'ted.com' in href:
                continue
                
            # Categorize external links
            if 'twitter.com' in href or 'x.com' in href:
                links['twitter'] = href
            elif 'linkedin.com' in href:
                links['linkedin'] = href
            elif 'facebook.com' in href:
                links['facebook'] = href
            elif 'instagram.com' in href:
                links['instagram'] = href
            elif href.startswith('http') and not any(social in href for social in ['youtube', 'vimeo']):
                # Likely a personal website
                if not links['website']:
                    links['website'] = href
        
        speaker_data.update(links)
        speaker_data['ted_url'] = speaker_url
        
        # If we found a personal website, visit it to find email
        if links['website']:
            logger.info(f"  Found website: {links['website']}")
            contact_info = scrape_personal_website(driver, links['website'])
            speaker_data.update(contact_info)
        
        return speaker_data
        
    except Exception as e:
        logger.error(f"Error scraping {speaker_url}: {e}")
        return {'ted_url': speaker_url, 'error': str(e)}

def scrape_personal_website(driver, website_url):
    """Visit personal website and extract contact information."""
    contact_info = {
        'email': None,
        'contact_form': False,
        'phone': None
    }
    
    try:
        logger.info(f"  Checking personal website: {website_url}")
        driver.get(website_url)
        driver.sleep(2)
        
        # Get page source
        page_text = driver.page_source
        soup = BeautifulSoup(page_text, 'html.parser')
        
        # Look for email addresses
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, page_text)
        
        # Filter out fake/common emails
        for email in emails:
            if not any(fake in email.lower() for fake in ['example', 'domain', 'email@', 'test', 'sample', 'sentry']):
                contact_info['email'] = email
                logger.info(f"    Found email: {email}")
                break
        
        # If no email on main page, check contact/about pages
        if not contact_info['email']:
            contact_links = soup.find_all('a', href=re.compile(r'contact|about', re.I))
            for link in contact_links[:2]:  # Check first 2 contact-related links
                try:
                    contact_url = urljoin(website_url, link.get('href'))
                    driver.get(contact_url)
                    driver.sleep(1)
                    
                    contact_page_text = driver.page_source
                    emails = re.findall(email_pattern, contact_page_text)
                    
                    for email in emails:
                        if not any(fake in email.lower() for fake in ['example', 'domain', 'email@']):
                            contact_info['email'] = email
                            logger.info(f"    Found email on contact page: {email}")
                            break
                    
                    if contact_info['email']:
                        break
                        
                except:
                    continue
        
        # Check for contact forms
        if soup.find('form', {'class': re.compile(r'contact', re.I)}) or \
           soup.find('input', {'type': 'email'}):
            contact_info['contact_form'] = True
            logger.info(f"    Found contact form")
        
        # Look for phone numbers
        phone_pattern = re.search(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', page_text)
        if phone_pattern:
            contact_info['phone'] = phone_pattern.group()
            
    except Exception as e:
        logger.debug(f"    Error scraping website {website_url}: {e}")
    
    return contact_info

@browser(
    headless=False,
    block_images=True,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
def scrape_ted_speakers_list(driver, max_speakers=100):
    """Scrape the main TED speakers listing page."""
    speakers_urls = []
    
    try:
        # Go to TED speakers page
        url = "https://www.ted.com/speakers"
        logger.info(f"Loading TED speakers list from: {url}")
        driver.get(url)
        
        # Wait for page to fully load and handle Cloudflare
        driver.sleep(5)
        
        # Scroll down to load more speakers (TED uses infinite scroll)
        last_height = driver.run_js("return document.body.scrollHeight")
        speakers_found = 0
        
        while speakers_found < max_speakers:
            # Scroll down
            driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            driver.sleep(2)
            
            # Check if more content loaded
            new_height = driver.run_js("return document.body.scrollHeight")
            
            # Get current speaker links
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            speaker_links = soup.find_all('a', href=re.compile(r'/speakers/[^/]+$'))
            
            speakers_found = len(speaker_links)
            logger.info(f"Found {speakers_found} speakers so far...")
            
            if new_height == last_height or speakers_found >= max_speakers:
                break
                
            last_height = new_height
        
        # Extract speaker URLs
        for link in speaker_links[:max_speakers]:
            speaker_url = "https://www.ted.com" + link.get('href')
            speakers_urls.append(speaker_url)
        
        logger.info(f"Found {len(speakers_urls)} speaker profile URLs")
        
    except Exception as e:
        logger.error(f"Error getting speakers list: {e}")
    
    return speakers_urls

def save_to_csv(speakers_data, filename=None):
    """Save speaker data to CSV."""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ted_speakers_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    fieldnames = ['name', 'email', 'occupation', 'bio', 'website', 
                 'twitter', 'linkedin', 'facebook', 'instagram', 
                 'contact_form', 'phone', 'ted_url']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for speaker in speakers_data:
            writer.writerow({
                'name': speaker.get('name', ''),
                'email': speaker.get('email', ''),
                'occupation': speaker.get('occupation', ''),
                'bio': speaker.get('bio', ''),
                'website': speaker.get('website', ''),
                'twitter': speaker.get('twitter', ''),
                'linkedin': speaker.get('linkedin', ''),
                'facebook': speaker.get('facebook', ''),
                'instagram': speaker.get('instagram', ''),
                'contact_form': speaker.get('contact_form', False),
                'phone': speaker.get('phone', ''),
                'ted_url': speaker.get('ted_url', '')
            })
    
    logger.info(f"Saved {len(speakers_data)} speakers to {csv_path}")
    return str(csv_path)

def main():
    """Main function to run the TED speaker scraper."""
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER WITH BOTASAURUS")
    print("="*80)
    
    # Step 1: Get list of speaker URLs
    print("\n[Step 1/3] Getting TED speaker URLs...")
    speaker_urls = scrape_ted_speakers_list(max_speakers=50)  # Start with 50 for testing
    
    if not speaker_urls:
        print("Failed to get speaker URLs!")
        return
    
    print(f"Found {len(speaker_urls)} speaker profiles to scrape")
    
    # Step 2: Scrape each speaker profile
    print("\n[Step 2/3] Scraping speaker profiles...")
    all_speakers = []
    
    for i, url in enumerate(speaker_urls, 1):
        print(f"\nProcessing speaker {i}/{len(speaker_urls)}...")
        speaker_data = scrape_ted_speaker_profile(url)
        all_speakers.append(speaker_data)
        
        # Be polite
        if i < len(speaker_urls):
            time.sleep(2)
    
    # Step 3: Save results
    print("\n[Step 3/3] Saving results...")
    csv_file = save_to_csv(all_speakers)
    
    # Statistics
    with_email = sum(1 for s in all_speakers if s.get('email'))
    with_website = sum(1 for s in all_speakers if s.get('website'))
    with_contact_form = sum(1 for s in all_speakers if s.get('contact_form'))
    with_social = sum(1 for s in all_speakers if s.get('twitter') or s.get('linkedin'))
    
    print(f"\n" + "="*80)
    print("SCRAPING COMPLETE!")
    print("="*80)
    print(f"\nResults:")
    print(f"  • Total speakers scraped: {len(all_speakers)}")
    print(f"  • With email addresses: {with_email} ({with_email/max(len(all_speakers),1)*100:.1f}%)")
    print(f"  • With personal websites: {with_website}")
    print(f"  • With contact forms: {with_contact_form}")
    print(f"  • With social media: {with_social}")
    print(f"  • CSV saved to: {csv_file}")
    
    # Show sample results
    if with_email > 0:
        print(f"\nSample speakers with emails found:")
        for speaker in all_speakers:
            if speaker.get('email'):
                print(f"  • {speaker.get('name')} - {speaker.get('email')}")
                if len([s for s in all_speakers if s.get('email')][:5]) >= 5:
                    break

if __name__ == "__main__":
    # Import urllib for URL joining
    from urllib.parse import urljoin
    main()