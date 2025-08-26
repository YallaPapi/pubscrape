#!/usr/bin/env python3
"""
TED Speaker Scraper - Enhanced Email Extraction
Improved email finding with better patterns and contact page checking
"""

from botasaurus.browser import browser
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
from pathlib import Path
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

@browser(
    headless=True,
    block_images=True,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def scrape_ted_enhanced(driver, data):
    """Enhanced TED scraper with better email extraction."""
    results = []
    
    try:
        # Load TED speakers page
        logger.info("Loading TED speakers page...")
        driver.google_get("https://www.ted.com/speakers", bypass_cloudflare=True)
        driver.sleep(5)
        
        # Extract speaker links
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
        
        # Process first 30 speakers
        for i, speaker_url in enumerate(speaker_links[:30], 1):
            logger.info(f"\n[{i}/30] Processing speaker...")
            
            # Load speaker page
            driver.google_get(speaker_url, bypass_cloudflare=True)
            driver.sleep(2)
            
            # Extract speaker data
            speaker_data = driver.run_js("""
                const data = {
                    name: null,
                    bio: null,
                    website: null,
                    social_links: []
                };
                
                // Get name
                const h1 = document.querySelector('h1');
                if (h1) data.name = h1.textContent.trim();
                
                // Get bio
                const bio = document.querySelector('[class*="description"], [class*="bio"], [class*="about"]');
                if (bio) data.bio = bio.textContent.trim().substring(0, 300);
                
                // Find external links
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    const original = a.getAttribute('href');
                    
                    // Skip TED internal links
                    if (href && !href.includes('ted.com') && !href.includes('enable-javascript')) {
                        if (href.includes('twitter.com') || href.includes('x.com')) {
                            data.social_links.push({type: 'twitter', url: href});
                        } else if (href.includes('linkedin.com')) {
                            data.social_links.push({type: 'linkedin', url: href});
                        } else if (href.startsWith('http') && !data.website) {
                            // First external non-social link is likely their website
                            data.website = href;
                        }
                    }
                });
                
                return data;
            """)
            
            result = {
                'name': speaker_data.get('name'),
                'bio': speaker_data.get('bio', ''),
                'website': speaker_data.get('website'),
                'email': None,
                'ted_url': speaker_url,
                'twitter': None,
                'linkedin': None
            }
            
            # Extract social media
            for social in speaker_data.get('social_links', []):
                if social['type'] == 'twitter':
                    result['twitter'] = social['url']
                elif social['type'] == 'linkedin':
                    result['linkedin'] = social['url']
            
            logger.info(f"  {result['name']}")
            
            # If we found a website, scrape it for email
            if result['website'] and not result['website'].startswith('https://enable-javascript'):
                logger.info(f"  Website: {result['website']}")
                
                try:
                    # Visit the website
                    driver.google_get(result['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Check we're not blocked
                    if "cloudflare" not in driver.current_url.lower():
                        # Extract emails with multiple methods
                        emails_found = driver.run_js("""
                            const emails = new Set();
                            
                            // Method 1: Look in text content
                            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                            const pageText = document.body.innerText || '';
                            const textMatches = pageText.match(emailRegex) || [];
                            textMatches.forEach(e => emails.add(e.toLowerCase()));
                            
                            // Method 2: Look in mailto links
                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                const email = a.href.replace('mailto:', '').split('?')[0];
                                if (email) emails.add(email.toLowerCase());
                            });
                            
                            // Method 3: Look in contact info sections
                            const contactSelectors = [
                                '[class*="contact"]', '[id*="contact"]',
                                '[class*="email"]', '[id*="email"]',
                                '[class*="about"]', '[class*="footer"]'
                            ];
                            
                            contactSelectors.forEach(selector => {
                                document.querySelectorAll(selector).forEach(elem => {
                                    const text = elem.textContent || '';
                                    const matches = text.match(emailRegex) || [];
                                    matches.forEach(e => emails.add(e.toLowerCase()));
                                });
                            });
                            
                            // Convert Set to Array and filter
                            return Array.from(emails).filter(email => {
                                // Basic validation
                                if (!email.includes('@') || !email.includes('.')) return false;
                                
                                // Skip common fake emails
                                const skipWords = [
                                    'example', 'test', 'demo', 'sample', 'your',
                                    'email@', 'user@', 'name@', 'firstname',
                                    'lastname', 'sentry', 'wix', 'cloudflare',
                                    'javascript', 'noreply', 'donotreply',
                                    '.png', '.jpg', '.gif', '.css', '.js'
                                ];
                                
                                return !skipWords.some(skip => email.includes(skip));
                            });
                        """)
                        
                        # Find best email match
                        if emails_found:
                            # Prefer emails with speaker's name
                            name_parts = result['name'].lower().split() if result['name'] else []
                            best_email = None
                            
                            # First try: email contains speaker's name
                            for email in emails_found:
                                if any(part in email for part in name_parts if len(part) > 3):
                                    best_email = email
                                    break
                            
                            # Second try: academic email
                            if not best_email:
                                for email in emails_found:
                                    if '.edu' in email:
                                        best_email = email
                                        break
                            
                            # Third try: professional domain
                            if not best_email:
                                for email in emails_found:
                                    if any(domain in email for domain in ['.org', '.io', '.net']):
                                        best_email = email
                                        break
                            
                            # Last resort: first valid email
                            if not best_email and emails_found:
                                best_email = emails_found[0]
                            
                            if best_email:
                                result['email'] = best_email
                                logger.info(f"  ✓ EMAIL: {best_email}")
                        
                        # If no email found, try contact page
                        if not result['email']:
                            contact_urls = driver.run_js("""
                                const urls = [];
                                document.querySelectorAll('a').forEach(a => {
                                    const href = a.href;
                                    const text = a.textContent.toLowerCase();
                                    if ((text.includes('contact') || text.includes('about') || 
                                         href.includes('contact') || href.includes('about')) &&
                                        href.startsWith('http')) {
                                        urls.push(href);
                                    }
                                });
                                return urls.slice(0, 2); // First 2 contact-related links
                            """)
                            
                            for contact_url in contact_urls:
                                if not result['email']:
                                    try:
                                        logger.info(f"  Checking contact page...")
                                        driver.google_get(contact_url, bypass_cloudflare=True)
                                        driver.sleep(2)
                                        
                                        contact_emails = driver.run_js("""
                                            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                                            const text = document.body.innerText || '';
                                            const matches = text.match(emailRegex) || [];
                                            
                                            // Also check mailto links
                                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                                const email = a.href.replace('mailto:', '').split('?')[0];
                                                if (email) matches.push(email);
                                            });
                                            
                                            return [...new Set(matches)].filter(e => 
                                                e.includes('@') && !e.includes('example')
                                            );
                                        """)
                                        
                                        if contact_emails:
                                            # Prefer email with name match
                                            for email in contact_emails:
                                                if any(part in email.lower() for part in name_parts if len(part) > 3):
                                                    result['email'] = email.lower()
                                                    logger.info(f"  ✓ EMAIL (contact): {email}")
                                                    break
                                            
                                            # Otherwise take first valid one
                                            if not result['email'] and contact_emails:
                                                result['email'] = contact_emails[0].lower()
                                                logger.info(f"  ✓ EMAIL (contact): {contact_emails[0]}")
                                                
                                    except Exception as e:
                                        logger.debug(f"  Contact page error: {str(e)[:50]}")
                        
                except Exception as e:
                    logger.info(f"  Error visiting website: {str(e)[:50]}")
            else:
                if result['website'] and 'enable-javascript' in result['website']:
                    logger.info(f"  Website blocked by TED")
                else:
                    logger.info(f"  No website found")
            
            results.append(result)
            
            # Rate limiting
            time.sleep(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers):
    """Save results to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_enhanced_{timestamp}.csv"
    
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
    print("TED SPEAKER SCRAPER - ENHANCED VERSION")
    print("Improved email extraction with multiple methods")
    print("="*80)
    
    results = scrape_ted_enhanced()
    
    if results:
        csv_file = save_results(results)
        
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website') and 
                          not s['website'].startswith('https://enable-javascript'))
        with_social = sum(1 for s in results if s.get('twitter') or s.get('linkedin'))
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  Total speakers: {len(results)}")
        print(f"  With website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        print(f"  With social: {with_social} ({with_social/len(results)*100:.0f}%)")
        print(f"  Saved to: {csv_file}")
        
        if with_email > 0:
            print(f"\nEmails found:")
            for s in results:
                if s.get('email'):
                    print(f"  • {s['name']}: {s['email']}")
        
        print(f"\nSample results:")
        for s in results[:5]:
            print(f"\n{s['name']}:")
            if s.get('website'):
                print(f"  Website: {s['website'][:50]}...")
            if s.get('email'):
                print(f"  Email: {s['email']}")
            if s.get('twitter'):
                print(f"  Twitter: {s['twitter']}")

if __name__ == "__main__":
    main()