#!/usr/bin/env python3
"""
TED Lightning Scraper - Ultra Fast
No delays, strict timeouts, maximum speed
"""

from botasaurus.browser import browser
import csv
from datetime import datetime
from pathlib import Path

@browser(headless=True, block_images=True)
def lightning_scrape(driver, data):
    """Lightning fast TED email extraction."""
    results = []
    
    # Get speakers
    driver.google_get("https://www.ted.com/speakers", bypass_cloudflare=True)
    
    speakers = driver.run_js("""
        const links = [];
        document.querySelectorAll('a[href*="/speakers/"]').forEach(a => {
            const href = a.getAttribute('href');
            if (href && href.match(/^\\/speakers\\/[a-z_]+$/)) {
                links.push('https://www.ted.com' + href);
            }
        });
        return [...new Set(links)];
    """)
    
    print(f"Processing {len(speakers)} speakers...")
    
    for i, speaker_url in enumerate(speakers, 1):
        print(f"{i}. ", end='', flush=True)
        
        result = {'name': '', 'email': '', 'website': '', 'ted_url': speaker_url}
        
        try:
            # Get speaker page
            driver.get(speaker_url)
            
            # Extract everything in one go
            data = driver.run_js("""
                const result = {name: '', website: '', email: ''};
                
                // Name
                const h1 = document.querySelector('h1');
                if (h1) result.name = h1.textContent.trim();
                
                // Find website (skip social media)
                const links = document.querySelectorAll('a[href]');
                for (let link of links) {
                    const href = link.href;
                    if (href && href.startsWith('http') && !href.includes('ted.com')) {
                        const domain = href.toLowerCase();
                        if (!domain.includes('facebook') && !domain.includes('twitter') && 
                            !domain.includes('instagram') && !domain.includes('youtube') &&
                            !domain.includes('linkedin') && !domain.includes('imdb') &&
                            !domain.includes('wikipedia') && !domain.includes('amazon')) {
                            result.website = href;
                            break;
                        }
                    }
                }
                
                return result;
            """)
            
            result.update(data)
            print(f"{result['name'][:15]} ", end='', flush=True)
            
            # If website found, get email
            if result['website']:
                try:
                    driver.get(result['website'])
                    
                    email = driver.run_js("""
                        const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                        const text = document.body.innerText || '';
                        const emails = text.match(emailRegex) || [];
                        
                        // Check mailto links too
                        document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                            const email = a.href.replace('mailto:', '').split('?')[0];
                            if (email) emails.push(email);
                        });
                        
                        // Return first valid email
                        for (let email of emails) {
                            if (email.includes('@') && !email.includes('example') && !email.includes('test')) {
                                return email.toLowerCase();
                            }
                        }
                        return '';
                    """)
                    
                    if email:
                        result['email'] = email
                        print(f"EMAIL: {email}")
                    else:
                        print("No email")
                except:
                    print("Site error")
            else:
                print("No website")
                
        except Exception as e:
            print(f"Error: {str(e)[:20]}")
        
        results.append(result)
    
    return results

def main():
    print("TED LIGHTNING EMAIL SCRAPER")
    print("="*30)
    
    import time
    start = time.time()
    
    # Run scraper
    results = lightning_scrape()
    
    end = time.time()
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_lightning_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'ted_url'])
        writer.writeheader()
        writer.writerows(results)
    
    # Results
    total = len(results)
    with_email = sum(1 for r in results if r.get('email'))
    
    print(f"\n" + "="*30)
    print(f"Time: {end-start:.1f} seconds")
    print(f"Speakers: {total}")
    print(f"Emails found: {with_email}")
    print(f"Success rate: {with_email/total*100:.1f}%")
    
    print(f"\nEmails:")
    for r in results:
        if r.get('email'):
            print(f"• {r['name']}: {r['email']}")
    
    print(f"\nSaved: {csv_path}")

if __name__ == "__main__":
    main()