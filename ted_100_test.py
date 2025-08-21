#!/usr/bin/env python3
"""
TED Speaker Scraper - 100 Speaker Test
Test email extraction on 100 speakers to get real statistics
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
def test_100_speakers(driver, data):
    """Test email extraction on 100 TED speakers."""
    results = []
    stats = {
        'total_processed': 0,
        'websites_found': 0,
        'emails_found': 0,
        'website_types': {},
        'failure_reasons': {}
    }
    
    # Social media to skip
    SOCIAL_MEDIA = ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'youtube.com', 'linkedin.com']
    AVOID_DOMAINS = ['ted.com', 'imdb.com', 'wikipedia.org', 'amazon.com', 'geni.us', 'bit.ly']
    
    try:
        # Get ALL TED speakers
        logger.info("Loading TED speakers page...")
        driver.google_get("https://www.ted.com/speakers", bypass_cloudflare=True)
        driver.sleep(3)
        
        # Get speaker links
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
        
        logger.info(f"Found {len(speaker_links)} total speakers, testing first 100")
        
        # Process 100 speakers
        for i, speaker_url in enumerate(speaker_links[:100], 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/100 ({i}%)")
            
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
                driver.sleep(1)
                
                # Extract data quickly
                speaker_data = driver.run_js("""
                    const data = {
                        name: null,
                        all_links: []
                    };
                    
                    // Get name
                    const h1 = document.querySelector('h1');
                    if (h1) data.name = h1.textContent.trim();
                    
                    // Get ALL external links
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href && href.startsWith('http') && !href.includes('ted.com')) {
                            data.all_links.push({
                                url: href,
                                domain: new URL(href).hostname
                            });
                        }
                    });
                    
                    return data;
                """)
                
                result['name'] = speaker_data.get('name')
                all_links = speaker_data.get('all_links', [])
                
                # Smart website selection
                if all_links:
                    # Skip social media and bad domains
                    good_links = []
                    for link in all_links:
                        domain = link['domain']
                        if not any(bad in domain for bad in SOCIAL_MEDIA + AVOID_DOMAINS):
                            good_links.append(link)
                    
                    if good_links:
                        # Prioritize by domain type
                        edu_sites = [l for l in good_links if '.edu' in l['domain']]
                        org_sites = [l for l in good_links if '.org' in l['domain']]
                        com_sites = [l for l in good_links if '.com' in l['domain']]
                        other_sites = [l for l in good_links if l not in edu_sites + org_sites + com_sites]
                        
                        # Select best website
                        if edu_sites:
                            result['website'] = edu_sites[0]['url']
                            result['website_type'] = 'academic'
                        elif org_sites:
                            result['website'] = org_sites[0]['url']
                            result['website_type'] = 'organization'
                        elif com_sites:
                            result['website'] = com_sites[0]['url']
                            result['website_type'] = 'commercial'
                        elif other_sites:
                            result['website'] = other_sites[0]['url']
                            result['website_type'] = 'other'
                        
                        stats['websites_found'] += 1
                        stats['website_types'][result['website_type']] = stats['website_types'].get(result['website_type'], 0) + 1
                    else:
                        result['failure_reason'] = 'only_social_media'
                else:
                    result['failure_reason'] = 'no_external_links'
                
                # If we have a website, try to extract email
                if result['website']:
                    try:
                        driver.google_get(result['website'], bypass_cloudflare=True)
                        driver.sleep(1.5)
                        
                        # Quick email extraction
                        emails = driver.run_js("""
                            const emails = new Set();
                            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
                            
                            // Check page text
                            const pageText = document.body.innerText || '';
                            const textMatches = pageText.match(emailRegex) || [];
                            textMatches.forEach(e => emails.add(e.toLowerCase()));
                            
                            // Check mailto links
                            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                                const email = a.href.replace('mailto:', '').split('?')[0];
                                if (email) emails.add(email.toLowerCase());
                            });
                            
                            // Filter valid emails
                            return Array.from(emails).filter(email => {
                                if (!email.includes('@') || !email.includes('.')) return false;
                                const skipWords = ['example', 'test', 'demo', 'noreply', '.png', '.jpg'];
                                return !skipWords.some(skip => email.includes(skip));
                            });
                        """)
                        
                        if emails:
                            result['email'] = emails[0]
                            stats['emails_found'] += 1
                        else:
                            result['failure_reason'] = 'no_email_on_page'
                            
                    except Exception as e:
                        result['failure_reason'] = f'website_error: {str(e)[:50]}'
                
            except Exception as e:
                result['failure_reason'] = f'processing_error: {str(e)[:50]}'
            
            # Track failure reasons
            if result['failure_reason']:
                reason = result['failure_reason']
                stats['failure_reasons'][reason] = stats['failure_reasons'].get(reason, 0) + 1
            
            results.append(result)
            stats['total_processed'] += 1
            
            # Quick progress update
            if i % 25 == 0:
                success_rate = (stats['emails_found'] / i) * 100
                logger.info(f"  Current success rate: {stats['emails_found']}/{i} ({success_rate:.1f}%)")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    return results, stats

def save_test_results(results, stats):
    """Save test results."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save CSV
    csv_filename = f"ted_100_test_{timestamp}.csv"
    output_dir = Path("ted_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / csv_filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'email', 'website', 'website_type', 'failure_reason', 'ted_url'
        ])
        writer.writeheader()
        writer.writerows(results)
    
    # Save detailed stats
    stats_filename = f"ted_100_stats_{timestamp}.txt"
    stats_path = output_dir / stats_filename
    
    with open(stats_path, 'w') as f:
        f.write("TED 100 Speaker Test Results\n")
        f.write("="*50 + "\n\n")
        f.write(f"Total processed: {stats['total_processed']}\n")
        f.write(f"Websites found: {stats['websites_found']}\n")
        f.write(f"Emails found: {stats['emails_found']}\n")
        f.write(f"Success rate: {(stats['emails_found']/stats['total_processed']*100):.1f}%\n\n")
        
        f.write("Website Types:\n")
        for wtype, count in stats['website_types'].items():
            f.write(f"  {wtype}: {count}\n")
        
        f.write("\nFailure Reasons:\n")
        for reason, count in stats['failure_reasons'].items():
            f.write(f"  {reason}: {count}\n")
    
    return str(csv_path), str(stats_path)

def main():
    print("\n" + "="*80)
    print("TED SPEAKER EMAIL EXTRACTION - 100 SPEAKER TEST")
    print("Testing real success rates on 100 speakers")
    print("="*80)
    
    start_time = time.time()
    results, stats = test_100_speakers()
    end_time = time.time()
    
    csv_file, stats_file = save_test_results(results, stats)
    
    # Print results
    total = stats['total_processed']
    websites = stats['websites_found']
    emails = stats['emails_found']
    
    print(f"\n" + "="*80)
    print("FINAL RESULTS:")
    print(f"  Time taken: {(end_time - start_time)/60:.1f} minutes")
    print(f"  Speakers processed: {total}")
    print(f"  Websites found: {websites} ({websites/total*100:.1f}%)")
    print(f"  Emails extracted: {emails} ({emails/total*100:.1f}%)")
    print(f"  Email rate from valid sites: {emails/max(websites,1)*100:.1f}%")
    
    print(f"\nWebsite types found:")
    for wtype, count in stats['website_types'].items():
        print(f"  {wtype}: {count}")
    
    print(f"\nTop failure reasons:")
    sorted_failures = sorted(stats['failure_reasons'].items(), key=lambda x: x[1], reverse=True)
    for reason, count in sorted_failures[:5]:
        print(f"  {reason}: {count}")
    
    print(f"\nSuccessful emails found:")
    success_count = 0
    for result in results:
        if result.get('email'):
            success_count += 1
            if success_count <= 10:  # Show first 10
                print(f"  {result['name']}: {result['email']} ({result['website_type']})")
    
    print(f"\nFiles saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Stats: {stats_file}")

if __name__ == "__main__":
    main()