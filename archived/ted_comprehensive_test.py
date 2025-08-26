#!/usr/bin/env python3
"""
TED Speaker Comprehensive Test
Gets more speakers by scrolling/pagination and tests email extraction
"""

from botasaurus.browser import browser
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
def comprehensive_ted_test(driver, data):
    """Get more TED speakers and test email extraction."""
    all_results = []
    stats = {
        'total_speakers_found': 0,
        'total_processed': 0,
        'websites_found': 0,
        'emails_found': 0,
        'website_types': {},
        'failure_reasons': {}
    }
    
    SOCIAL_MEDIA = ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'linkedin.com']
    AVOID_DOMAINS = ['ted.com', 'imdb.com', 'wikipedia.org', 'amazon.com', 'geni.us', 'bit.ly']
    
    try:
        # Try different approaches to get more speakers
        all_speaker_links = set()
        
        # Method 1: Main speakers page
        logger.info("Loading main TED speakers page...")
        driver.google_get("https://www.ted.com/speakers", bypass_cloudflare=True)
        driver.sleep(3)
        
        # Get initial speaker links
        initial_links = driver.run_js("""
            const links = [];
            document.querySelectorAll('a[href*="/speakers/"]').forEach(a => {
                const href = a.getAttribute('href');
                if (href && href.match(/^\\/speakers\\/[a-z_]+$/)) {
                    links.push('https://www.ted.com' + href);
                }
            });
            return [...new Set(links)];
        """)
        
        for link in initial_links:
            all_speaker_links.add(link)
        
        logger.info(f"Found {len(initial_links)} speakers from main page")
        
        # Method 2: Try to load more by scrolling
        logger.info("Attempting to load more speakers by scrolling...")
        for scroll_attempt in range(5):
            driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            driver.sleep(2)
            
            # Check if more speakers loaded
            new_links = driver.run_js("""
                const links = [];
                document.querySelectorAll('a[href*="/speakers/"]').forEach(a => {
                    const href = a.getAttribute('href');
                    if (href && href.match(/^\\/speakers\\/[a-z_]+$/)) {
                        links.push('https://www.ted.com' + href);
                    }
                });
                return [...new Set(links)];
            """)
            
            before_count = len(all_speaker_links)
            for link in new_links:
                all_speaker_links.add(link)
            after_count = len(all_speaker_links)
            
            if after_count > before_count:
                logger.info(f"  Scroll {scroll_attempt + 1}: Found {after_count - before_count} new speakers")
            else:
                logger.info(f"  Scroll {scroll_attempt + 1}: No new speakers found")
                break
        
        # Method 3: Try alphabet pages (if they exist)
        logger.info("Trying alphabet-based speaker pages...")
        for letter in ['a', 'b', 'c', 'd', 'e']:
            try:
                alphabet_url = f"https://www.ted.com/speakers?letter={letter}"
                driver.get(alphabet_url)
                driver.sleep(2)
                
                letter_links = driver.run_js("""
                    const links = [];
                    document.querySelectorAll('a[href*="/speakers/"]').forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && href.match(/^\\/speakers\\/[a-z_]+$/)) {
                            links.push('https://www.ted.com' + href);
                        }
                    });
                    return [...new Set(links)];
                """)
                
                before_count = len(all_speaker_links)
                for link in letter_links:
                    all_speaker_links.add(link)
                after_count = len(all_speaker_links)
                
                if after_count > before_count:
                    logger.info(f"  Letter {letter}: Found {after_count - before_count} new speakers")
            except:
                logger.info(f"  Letter {letter}: Page not found")
        
        all_speaker_links = list(all_speaker_links)
        stats['total_speakers_found'] = len(all_speaker_links)
        logger.info(f"\nTotal unique speakers found: {len(all_speaker_links)}")
        
        # Test on available speakers (up to 50 to avoid timeout)
        test_count = min(50, len(all_speaker_links))
        logger.info(f"Testing email extraction on {test_count} speakers...\n")
        
        # Process speakers efficiently
        for i, speaker_url in enumerate(all_speaker_links[:test_count], 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{test_count} - Emails found so far: {stats['emails_found']}")
            
            result = {
                'name': None,
                'website': None,
                'website_type': None,
                'email': None,
                'ted_url': speaker_url,
                'failure_reason': None
            }
            
            try:
                # Load speaker page quickly
                driver.google_get(speaker_url, bypass_cloudflare=True)
                driver.sleep(0.8)
                
                # Extract name and links quickly
                speaker_data = driver.run_js("""
                    const data = { name: null, all_links: [] };
                    
                    // Get name
                    const h1 = document.querySelector('h1');
                    if (h1) data.name = h1.textContent.trim();
                    
                    // Get external links
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href && href.startsWith('http') && !href.includes('ted.com')) {
                            try {
                                data.all_links.push({
                                    url: href,
                                    domain: new URL(href).hostname
                                });
                            } catch(e) {}
                        }
                    });
                    
                    return data;
                """)
                
                result['name'] = speaker_data.get('name')
                all_links = speaker_data.get('all_links', [])
                
                # Find best website
                if all_links:
                    good_links = [l for l in all_links 
                                 if not any(bad in l['domain'] for bad in SOCIAL_MEDIA + AVOID_DOMAINS)]
                    
                    if good_links:
                        # Prioritize website types
                        for link in good_links:
                            domain = link['domain']
                            if '.edu' in domain:
                                result['website'] = link['url']
                                result['website_type'] = 'academic'
                                break
                            elif '.org' in domain:
                                result['website'] = link['url']
                                result['website_type'] = 'organization'
                                break
                            elif '.com' in domain:
                                result['website'] = link['url']
                                result['website_type'] = 'commercial'
                                break
                        
                        # If no priority match, take first good link
                        if not result['website'] and good_links:
                            result['website'] = good_links[0]['url']
                            result['website_type'] = 'other'
                        
                        if result['website']:
                            stats['websites_found'] += 1
                            stats['website_types'][result['website_type']] = stats['website_types'].get(result['website_type'], 0) + 1
                    else:
                        result['failure_reason'] = 'only_social_media'
                else:
                    result['failure_reason'] = 'no_external_links'
                
                # Extract email if we have a website
                if result['website']:
                    try:
                        driver.google_get(result['website'], bypass_cloudflare=True)
                        driver.sleep(1)
                        
                        # Quick email extraction
                        emails = driver.run_js("""
                            const emails = new Set();
                            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                            
                            // Check page text
                            const pageText = document.body.innerText || '';
                            const matches = pageText.match(emailRegex) || [];
                            matches.forEach(e => emails.add(e.toLowerCase()));
                            
                            // Check mailto links
                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                const email = a.href.replace('mailto:', '').split('?')[0];
                                if (email) emails.add(email.toLowerCase());
                            });
                            
                            // Filter
                            return Array.from(emails).filter(email => {
                                if (!email.includes('@')) return false;
                                const bad = ['example', 'test', 'noreply', '.png', '.jpg'];
                                return !bad.some(b => email.includes(b));
                            });
                        """)
                        
                        if emails:
                            result['email'] = emails[0]
                            stats['emails_found'] += 1
                        else:
                            result['failure_reason'] = 'no_email_on_page'
                            
                    except Exception as e:
                        result['failure_reason'] = f'website_error'
                
            except Exception as e:
                result['failure_reason'] = 'processing_error'
            
            # Track failures
            if result['failure_reason']:
                reason = result['failure_reason']
                stats['failure_reasons'][reason] = stats['failure_reasons'].get(reason, 0) + 1
            
            all_results.append(result)
            stats['total_processed'] += 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return all_results, stats

def save_comprehensive_results(results, stats):
    """Save comprehensive test results."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save CSV
    csv_filename = f"ted_comprehensive_{timestamp}.csv"
    csv_path = output_dir / csv_filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'email', 'website', 'website_type', 'failure_reason', 'ted_url'
        ])
        writer.writeheader()
        writer.writerows(results)
    
    return str(csv_path)

def main():
    print("\n" + "="*80)
    print("TED COMPREHENSIVE EMAIL EXTRACTION TEST")
    print("Finding more speakers and testing real success rates")
    print("="*80)
    
    start_time = time.time()
    results, stats = comprehensive_ted_test()
    end_time = time.time()
    
    csv_file = save_comprehensive_results(results, stats)
    
    # Print brutal honest results
    total = stats['total_processed']
    websites = stats['websites_found']
    emails = stats['emails_found']
    
    print(f"\n" + "="*80)
    print("BRUTAL HONEST RESULTS:")
    print(f"  Time: {(end_time - start_time)/60:.1f} minutes")
    print(f"  Total speakers found on TED: {stats['total_speakers_found']}")
    print(f"  Speakers tested: {total}")
    print(f"  Real websites found: {websites} ({websites/total*100:.1f}%)")
    print(f"  Emails extracted: {emails} ({emails/total*100:.1f}%)")
    
    if emails > 0:
        print(f"\nACTUAL SUCCESS STORIES:")
        count = 0
        for result in results:
            if result.get('email'):
                count += 1
                print(f"  {count}. {result['name']}: {result['email']} ({result['website_type']})")
    
    print(f"\nWHY IT'S FAILING:")
    sorted_failures = sorted(stats['failure_reasons'].items(), key=lambda x: x[1], reverse=True)
    for reason, count in sorted_failures:
        print(f"  {reason}: {count} ({count/total*100:.1f}%)")
    
    print(f"\nWebsite types when found:")
    for wtype, count in stats['website_types'].items():
        print(f"  {wtype}: {count}")
    
    print(f"\nSaved to: {csv_file}")

if __name__ == "__main__":
    main()