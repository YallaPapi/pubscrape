#!/usr/bin/env python3
"""
TED Speaker Scraper - Smart Website Extractor
Prioritizes real websites over social media links
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
def scrape_ted_smart(driver, data):
    """Smart TED scraper that prioritizes real websites."""
    results = []
    
    # Social media domains to deprioritize
    SOCIAL_MEDIA = [
        'facebook.com', 'twitter.com', 'x.com', 'instagram.com', 
        'youtube.com', 'linkedin.com', 'tiktok.com', 'pinterest.com'
    ]
    
    # Generic/redirect domains to avoid
    AVOID_DOMAINS = [
        'ted.com', 'imdb.com', 'wikipedia.org', 'amazon.com',
        'geni.us', 'bit.ly', 'tinyurl.com', 'shorturl.at'
    ]
    
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
        
        # Process speakers (reduced count for speed)
        for i, speaker_url in enumerate(speaker_links[:15], 1):
            logger.info(f"\n[{i}/15] Processing speaker...")
            
            # Load speaker page
            driver.google_get(speaker_url, bypass_cloudflare=True)
            driver.sleep(2)
            
            # Extract ALL external links and speaker info
            speaker_data = driver.run_js("""
                const data = {
                    name: null,
                    bio: null,
                    all_links: [],
                    social_links: {}
                };
                
                // Get name
                const h1 = document.querySelector('h1');
                if (h1) data.name = h1.textContent.trim();
                
                // Get bio
                const bio = document.querySelector('[class*="description"], [class*="bio"], [class*="about"]');
                if (bio) data.bio = bio.textContent.trim().substring(0, 300);
                
                // Collect ALL external links
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    const text = a.textContent.trim();
                    
                    // Only external links
                    if (href && href.startsWith('http') && !href.includes('ted.com')) {
                        data.all_links.push({
                            url: href,
                            text: text,
                            domain: new URL(href).hostname
                        });
                        
                        // Track social media separately
                        if (href.includes('twitter.com') || href.includes('x.com')) {
                            data.social_links.twitter = href;
                        } else if (href.includes('linkedin.com')) {
                            data.social_links.linkedin = href;
                        } else if (href.includes('facebook.com')) {
                            data.social_links.facebook = href;
                        } else if (href.includes('instagram.com')) {
                            data.social_links.instagram = href;
                        }
                    }
                });
                
                return data;
            """)
            
            # Smart website selection
            result = {
                'name': speaker_data.get('name'),
                'bio': speaker_data.get('bio', ''),
                'website': None,
                'website_type': None,
                'email': None,
                'ted_url': speaker_url,
                'twitter': speaker_data['social_links'].get('twitter'),
                'linkedin': speaker_data['social_links'].get('linkedin'),
                'all_external_links': len(speaker_data.get('all_links', []))
            }
            
            logger.info(f"  {result['name']}")
            logger.info(f"  Found {result['all_external_links']} external links")
            
            # Prioritize links to find best website
            all_links = speaker_data.get('all_links', [])
            
            # Priority 1: Academic websites (.edu)
            edu_sites = [l for l in all_links if '.edu' in l['domain']]
            
            # Priority 2: Personal websites (name in domain)
            name_parts = result['name'].lower().split() if result['name'] else []
            personal_sites = []
            for link in all_links:
                domain_lower = link['domain'].lower()
                if any(part in domain_lower for part in name_parts if len(part) > 3):
                    if not any(social in domain_lower for social in SOCIAL_MEDIA):
                        personal_sites.append(link)
            
            # Priority 3: Professional sites (.org, .io, .net)
            prof_sites = []
            for link in all_links:
                domain = link['domain']
                if any(ext in domain for ext in ['.org', '.io', '.net']):
                    if not any(avoid in domain for avoid in AVOID_DOMAINS + SOCIAL_MEDIA):
                        prof_sites.append(link)
            
            # Priority 4: Any .com that's not social/generic
            com_sites = []
            for link in all_links:
                domain = link['domain']
                if '.com' in domain:
                    if not any(avoid in domain for avoid in AVOID_DOMAINS + SOCIAL_MEDIA):
                        com_sites.append(link)
            
            # Select best website
            if edu_sites:
                result['website'] = edu_sites[0]['url']
                result['website_type'] = 'academic'
                logger.info(f"  Selected academic site: {edu_sites[0]['domain']}")
            elif personal_sites:
                result['website'] = personal_sites[0]['url']
                result['website_type'] = 'personal'
                logger.info(f"  Selected personal site: {personal_sites[0]['domain']}")
            elif prof_sites:
                result['website'] = prof_sites[0]['url']
                result['website_type'] = 'professional'
                logger.info(f"  Selected professional site: {prof_sites[0]['domain']}")
            elif com_sites:
                result['website'] = com_sites[0]['url']
                result['website_type'] = 'commercial'
                logger.info(f"  Selected commercial site: {com_sites[0]['domain']}")
            else:
                # Last resort - first non-social link
                for link in all_links:
                    if not any(social in link['domain'] for social in SOCIAL_MEDIA):
                        result['website'] = link['url']
                        result['website_type'] = 'other'
                        logger.info(f"  Selected other site: {link['domain']}")
                        break
            
            # If we found a real website, extract email
            if result['website']:
                logger.info(f"  Visiting {result['website_type']} website...")
                
                try:
                    driver.google_get(result['website'], bypass_cloudflare=True)
                    driver.sleep(3)
                    
                    # Check we're not blocked
                    if "cloudflare" not in driver.current_url.lower():
                        # Extract emails with multiple methods
                        emails_found = driver.run_js("""
                            const emails = new Set();
                            
                            // Method 1: Text content
                            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                            const pageText = document.body.innerText || '';
                            const textMatches = pageText.match(emailRegex) || [];
                            textMatches.forEach(e => emails.add(e.toLowerCase()));
                            
                            // Method 2: Mailto links
                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                const email = a.href.replace('mailto:', '').split('?')[0];
                                if (email) emails.add(email.toLowerCase());
                            });
                            
                            // Method 3: Contact sections
                            const contactSelectors = [
                                '[class*="contact"]', '[id*="contact"]',
                                '[class*="email"]', '[id*="email"]',
                                '[class*="about"]', '[class*="footer"]',
                                'footer'
                            ];
                            
                            contactSelectors.forEach(selector => {
                                try {
                                    document.querySelectorAll(selector).forEach(elem => {
                                        const text = elem.textContent || '';
                                        const matches = text.match(emailRegex) || [];
                                        matches.forEach(e => emails.add(e.toLowerCase()));
                                    });
                                } catch(e) {}
                            });
                            
                            // Filter valid emails
                            return Array.from(emails).filter(email => {
                                if (!email.includes('@') || !email.includes('.')) return false;
                                
                                const skipWords = [
                                    'example', 'test', 'demo', 'sample',
                                    'noreply', 'no-reply', 'donotreply',
                                    '.png', '.jpg', '.gif', '.css', '.js',
                                    'sentry', 'cloudflare', 'protected'
                                ];
                                
                                return !skipWords.some(skip => email.includes(skip));
                            });
                        """)
                        
                        # Find best email match
                        if emails_found:
                            best_email = None
                            
                            # Prefer email with speaker's name
                            for email in emails_found:
                                if any(part in email for part in name_parts if len(part) > 3):
                                    best_email = email
                                    break
                            
                            # Otherwise take first valid one
                            if not best_email and emails_found:
                                best_email = emails_found[0]
                            
                            if best_email:
                                result['email'] = best_email
                                logger.info(f"  ✓ EMAIL: {best_email}")
                        
                        # Try contact page if no email
                        if not result['email']:
                            contact_urls = driver.run_js("""
                                const urls = [];
                                document.querySelectorAll('a').forEach(a => {
                                    const href = a.href;
                                    const text = a.textContent.toLowerCase();
                                    if ((text.includes('contact') || href.includes('contact')) &&
                                        href.startsWith('http')) {
                                        urls.push(href);
                                    }
                                });
                                return urls.slice(0, 2);
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
                                            
                                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                                const email = a.href.replace('mailto:', '').split('?')[0];
                                                if (email) matches.push(email);
                                            });
                                            
                                            return [...new Set(matches)].filter(e => 
                                                e.includes('@') && !e.includes('example')
                                            );
                                        """)
                                        
                                        if contact_emails:
                                            result['email'] = contact_emails[0].lower()
                                            logger.info(f"  ✓ EMAIL (contact): {contact_emails[0]}")
                                            
                                    except Exception as e:
                                        logger.debug(f"  Contact page error: {str(e)[:50]}")
                        
                except Exception as e:
                    logger.info(f"  Error visiting website: {str(e)[:50]}")
            else:
                logger.info(f"  No suitable website found (only social media)")
            
            results.append(result)
            time.sleep(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results

def save_results(speakers):
    """Save results to CSV."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ted_smart_{timestamp}.csv"
    
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'email', 'website', 'website_type', 
            'twitter', 'linkedin', 'ted_url', 'all_external_links'
        ])
        writer.writeheader()
        
        # Remove bio from output
        clean_speakers = []
        for speaker in speakers:
            clean_speaker = {k: v for k, v in speaker.items() if k != 'bio'}
            clean_speakers.append(clean_speaker)
        
        writer.writerows(clean_speakers)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER SCRAPER - SMART WEBSITE EXTRACTOR")
    print("Prioritizes real websites over social media")
    print("="*80)
    
    results = scrape_ted_smart()
    
    if results:
        csv_file = save_results(results)
        
        # Statistics
        with_email = sum(1 for s in results if s.get('email'))
        with_website = sum(1 for s in results if s.get('website'))
        
        website_types = {}
        for s in results:
            if s.get('website_type'):
                website_types[s['website_type']] = website_types.get(s['website_type'], 0) + 1
        
        print(f"\n" + "="*80)
        print("RESULTS:")
        print(f"  Total speakers: {len(results)}")
        print(f"  With real website: {with_website} ({with_website/len(results)*100:.0f}%)")
        print(f"  With email: {with_email} ({with_email/len(results)*100:.0f}%)")
        
        print(f"\nWebsite types found:")
        for wtype, count in website_types.items():
            print(f"  - {wtype}: {count}")
        
        print(f"\nEmails extracted:")
        for s in results:
            if s.get('email'):
                print(f"  • {s['name']}: {s['email']} (from {s['website_type']} site)")
        
        print(f"\nSaved to: {csv_file}")

if __name__ == "__main__":
    main()