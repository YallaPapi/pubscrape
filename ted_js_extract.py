#!/usr/bin/env python3
"""
TED Speaker Scraper - JavaScript Extraction Version
Attempts to extract real URLs using JavaScript execution
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
    block_images=False,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def scrape_ted_js(driver, data):
    """Extract TED speaker data using JavaScript execution."""
    results = []
    
    try:
        # Load TED speakers page
        logger.info("Loading TED speakers page...")
        driver.google_get("https://www.ted.com/speakers", bypass_cloudflare=True)
        driver.sleep(5)
        
        # Extract speaker links using JavaScript
        speaker_links = driver.run_js("""
            const links = [];
            document.querySelectorAll('a[href*="/speakers/"]').forEach(a => {
                const href = a.getAttribute('href');
                if (href && href.match(/^\\/speakers\\/[a-z_]+$/)) {
                    links.push('https://www.ted.com' + href);
                }
            });
            return [...new Set(links)];
        """)
        
        logger.info(f"Found {len(speaker_links)} speaker profiles")
        
        # Process first 10 speakers
        for i, speaker_url in enumerate(speaker_links[:10], 1):
            logger.info(f"\n[{i}/10] Processing speaker...")
            
            # Load speaker page
            driver.google_get(speaker_url, bypass_cloudflare=True)
            driver.sleep(3)
            
            # Extract all data using JavaScript
            speaker_data = driver.run_js("""
                const data = {
                    name: null,
                    bio: null,
                    links: [],
                    all_hrefs: [],
                    data_attributes: [],
                    onclick_handlers: []
                };
                
                // Get name
                const h1 = document.querySelector('h1');
                if (h1) data.name = h1.textContent.trim();
                
                // Get bio
                const bio = document.querySelector('[class*="description"], [class*="bio"]');
                if (bio) data.bio = bio.textContent.trim().substring(0, 200);
                
                // Extract ALL link information
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.getAttribute('href');
                    const computedHref = a.href;
                    const onclick = a.getAttribute('onclick');
                    const dataUrl = a.getAttribute('data-url');
                    const dataHref = a.getAttribute('data-href');
                    const text = a.textContent.trim();
                    
                    // Collect all href values
                    data.all_hrefs.push({
                        original_href: href,
                        computed_href: computedHref,
                        text: text
                    });
                    
                    // Check for external links
                    if (computedHref && !computedHref.includes('ted.com') && 
                        !computedHref.includes('enable-javascript') &&
                        computedHref.startsWith('http')) {
                        data.links.push({
                            url: computedHref,
                            text: text,
                            type: 'external'
                        });
                    }
                    
                    // Check data attributes
                    if (dataUrl) data.data_attributes.push({attr: 'data-url', value: dataUrl});
                    if (dataHref) data.data_attributes.push({attr: 'data-href', value: dataHref});
                    
                    // Check onclick handlers
                    if (onclick) data.onclick_handlers.push(onclick);
                });
                
                // Also check for any elements with data attributes that might contain URLs
                document.querySelectorAll('*').forEach(elem => {
                    if (elem.attributes) {
                        Array.from(elem.attributes).forEach(attr => {
                            if (attr.name.startsWith('data-') && attr.value && attr.value.includes('http')) {
                                data.data_attributes.push({
                                    attr: attr.name,
                                    value: attr.value
                                });
                            }
                        });
                    }
                });
                
                return data;
            """)
            
            # Process the extracted data
            result = {
                'ted_url': speaker_url,
                'name': speaker_data.get('name'),
                'bio': speaker_data.get('bio'),
                'website': None,
                'email': None,
                'found_links': []
            }
            
            if result['name']:
                logger.info(f"  Name: {result['name']}")
            
            # Check if we found any real external links
            external_links = speaker_data.get('links', [])
            for link in external_links:
                url = link.get('url', '')
                if url and not any(skip in url for skip in [
                    'twitter.com', 'linkedin.com', 'facebook.com', 
                    'instagram.com', 'youtube.com', 'wikipedia.org'
                ]):
                    result['website'] = url
                    logger.info(f"  Found website: {url}")
                    break
            
            # Log what we found for debugging
            all_hrefs = speaker_data.get('all_hrefs', [])
            logger.info(f"  Total links found: {len(all_hrefs)}")
            
            # Show first few links for debugging
            for href_data in all_hrefs[:5]:
                orig = href_data.get('original_href', '')
                comp = href_data.get('computed_href', '')
                if orig != comp:
                    logger.debug(f"    Original: {orig} -> Computed: {comp}")
            
            # Check data attributes
            data_attrs = speaker_data.get('data_attributes', [])
            if data_attrs:
                logger.info(f"  Found {len(data_attrs)} data attributes with URLs")
                for attr in data_attrs[:3]:
                    logger.debug(f"    {attr['attr']}: {attr['value'][:50]}")
            
            # If we found a real website, try to scrape it
            if result['website'] and not result['website'].startswith('https://enable-javascript'):
                try:
                    logger.info(f"  Visiting website: {result['website']}")
                    driver.google_get(result['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Extract emails using JavaScript
                    emails = driver.run_js("""
                        const emailRegex = /[\\w\\.-]+@[\\w\\.-]+\\.\\w+/g;
                        const text = document.body.innerText || document.body.textContent || '';
                        const matches = text.match(emailRegex) || [];
                        return [...new Set(matches)].filter(email => 
                            email.includes('@') && 
                            !email.includes('example') &&
                            !email.includes('test') &&
                            !email.includes('demo')
                        );
                    """)
                    
                    if emails:
                        result['email'] = emails[0]
                        logger.info(f"  EMAIL FOUND: {emails[0]}")
                        
                except Exception as e:
                    logger.info(f"  Error visiting website: {str(e)[:50]}")
            
            results.append(result)
            
            # Show what TED is actually serving
            if not result['website'] or result['website'].startswith('https://enable-javascript'):
                logger.warning(f"  TED is blocking external links for {result['name']}")
                # Log the actual href values to understand the pattern
                for href_data in all_hrefs:
                    orig = href_data.get('original_href', '')
                    if orig and not orig.startswith('/') and not orig.startswith('#'):
                        logger.debug(f"    Found href: {orig[:100]}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers):
    """Save results to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_js_extract_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        # Remove found_links from the data before saving
        clean_speakers = []
        for speaker in speakers:
            clean_speaker = {k: v for k, v in speaker.items() if k != 'found_links'}
            clean_speakers.append(clean_speaker)
        
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'bio', 'ted_url'])
        writer.writeheader()
        writer.writerows(clean_speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - JavaScript Extraction")
    print("Using JS execution to extract real URLs")
    print("="*80)
    
    results = scrape_ted_js()
    
    if results:
        csv_file = save_results(results)
        
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website') and 
                          not s['website'].startswith('https://enable-javascript'))
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  - Total speakers: {len(results)}")
        print(f"  - With real website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  - With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  - Saved to: {csv_file}")
        
        if with_website > 0:
            print(f"\nReal websites found:")
            for s in results:
                if s.get('website') and not s['website'].startswith('https://enable-javascript'):
                    print(f"  - {s['name']}: {s['website']}")
        
        if with_email > 0:
            print(f"\nEmails found:")
            for s in results:
                if s.get('email'):
                    print(f"  - {s['name']}: {s['email']}")

if __name__ == "__main__":
    main()