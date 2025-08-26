#!/usr/bin/env python3
"""
TED Fast Bulk Scraper
No bullshit, just fast email extraction
"""

from botasaurus.browser import browser
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
def fast_bulk_scrape(driver, data):
    """Fast bulk email extraction from TED speakers."""
    results = []
    
    try:
        # Get speakers fast
        driver.google_get("https://www.ted.com/speakers", bypass_cloudflare=True)
        driver.sleep(1)
        
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
        
        logger.info(f"Found {len(speaker_links)} speakers, extracting emails...")
        
        for i, speaker_url in enumerate(speaker_links, 1):
            print(f"[{i}/{len(speaker_links)}] Processing...", end=' ')
            
            result = {'name': None, 'email': None, 'website': None, 'ted_url': speaker_url}
            
            try:
                # Get speaker data fast
                driver.google_get(speaker_url, bypass_cloudflare=True)
                
                speaker_data = driver.run_js("""
                    const data = {name: null, website: null};
                    
                    // Name
                    const h1 = document.querySelector('h1');
                    if (h1) data.name = h1.textContent.trim();
                    
                    // Find first real website (not social media)
                    const links = document.querySelectorAll('a[href]');
                    for (let link of links) {
                        const href = link.href;
                        if (href && href.startsWith('http') && !href.includes('ted.com')) {
                            const domain = new URL(href).hostname;
                            const social = ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin'];
                            const bad = ['imdb', 'wikipedia', 'amazon', 'geni.us'];
                            
                            if (!social.some(s => domain.includes(s)) && !bad.some(b => domain.includes(b))) {
                                data.website = href;
                                break;
                            }
                        }
                    }
                    
                    return data;
                """)
                
                result['name'] = speaker_data.get('name')
                result['website'] = speaker_data.get('website')
                
                print(f"{result['name']}", end=' ')
                
                # If we have a website, get email fast
                if result['website']:
                    try:
                        driver.google_get(result['website'], bypass_cloudflare=True)
                        
                        emails = driver.run_js("""
                            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                            const text = document.body.innerText || '';
                            const matches = text.match(emailRegex) || [];
                            
                            // Also check mailto links
                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                const email = a.href.replace('mailto:', '').split('?')[0];
                                if (email) matches.push(email);
                            });
                            
                            // Return first valid email
                            for (let email of matches) {
                                email = email.toLowerCase();
                                if (email.includes('@') && email.includes('.') && 
                                    !email.includes('example') && !email.includes('test')) {
                                    return email;
                                }
                            }
                            return null;
                        """)
                        
                        if emails:
                            result['email'] = emails
                            print(f"FOUND: {emails}")
                        else:
                            print("No email")
                    except:
                        print("Website error")
                else:
                    print("No website")
                    
            except Exception as e:
                print(f"Error: {str(e)[:30]}")
            
            results.append(result)
        
        print(f"\nProcessed {len(results)} speakers total")
        
    except Exception as e:
        logger.error(f"Fatal: {e}")
    
    return results

def save_fast_results(results):
    """Save results fast."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_fast_bulk_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'ted_url'])
        writer.writeheader()
        writer.writerows(results)
    
    return str(csv_path)

def main():
    print("TED FAST BULK EMAIL SCRAPER")
    print("="*40)
    
    import time
    start = time.time()
    
    # Call the function with empty data parameter
    results = fast_bulk_scrape(None)
    print(f"DEBUG: Received {len(results) if results else 0} results")
    
    end = time.time()
    
    csv_file = save_fast_results(results or [])
    
    # Count results
    results = results or []
    total = len(results)
    with_email = sum(1 for r in results if r.get('email'))
    with_website = sum(1 for r in results if r.get('website'))
    
    print(f"\n" + "="*40)
    print("RESULTS:")
    print(f"Time: {end-start:.1f} seconds")
    print(f"Speakers: {total}")
    print(f"Websites: {with_website}")
    if total > 0:
        print(f"Emails: {with_email} ({with_email/total*100:.1f}%)")
    else:
        print("Emails: 0 (No speakers processed)")
    
    print(f"\nEmails found:")
    for r in results:
        if r.get('email'):
            print(f"• {r['name']}: {r['email']}")
    
    print(f"\nSaved: {csv_file}")

if __name__ == "__main__":
    main()