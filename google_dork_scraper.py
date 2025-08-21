#!/usr/bin/env python3
"""
Google Dork Scraper - The Ultimate Lead Generation Tool
Scrapes Google search results for any dork/query and extracts emails from found websites
"""

from botasaurus.browser import browser
import csv
import re
import time
import random
from datetime import datetime
from pathlib import Path
import logging
from urllib.parse import urlparse, parse_qs, unquote

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleDorkScraper:
    def __init__(self):
        self.results = []
        self.stats = {
            'searches_performed': 0,
            'urls_found': 0,
            'emails_extracted': 0,
            'blocked_count': 0,
            'error_count': 0
        }
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

@browser(
    headless=True,
    block_images=True,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def google_dork_scraper(driver, dorks_and_settings):
    """
    The ultimate Google dork scraper
    """
    scraper = GoogleDorkScraper()
    
    # Unpack settings
    dorks = dorks_and_settings['dorks']
    max_pages = dorks_and_settings.get('max_pages', 5)
    max_results_per_dork = dorks_and_settings.get('max_results_per_dork', 100)
    delay_range = dorks_and_settings.get('delay_range', (2, 5))
    
    logger.info(f"Starting Google dork scraping with {len(dorks)} dorks")
    
    try:
        for dork_idx, dork in enumerate(dorks, 1):
            logger.info(f"\n[{dork_idx}/{len(dorks)}] Processing dork: {dork}")
            
            # Search Google with the dork
            search_urls = search_google_with_dork(driver, dork, max_pages, scraper)
            
            if not search_urls:
                logger.warning(f"No URLs found for dork: {dork}")
                continue
            
            logger.info(f"Found {len(search_urls)} URLs, extracting emails...")
            
            # Extract emails from found URLs
            extract_emails_from_urls(driver, search_urls, scraper, max_results_per_dork)
            
            # Random delay between dorks to avoid detection
            delay = random.uniform(delay_range[0], delay_range[1])
            logger.info(f"Waiting {delay:.1f}s before next dork...")
            time.sleep(delay)
            
            # Check if we're getting blocked
            if scraper.stats['blocked_count'] > 3:
                logger.warning("Multiple blocks detected, switching tactics...")
                # Try different approach or break
                
        logger.info(f"\nScraping complete! Found {scraper.stats['emails_extracted']} emails")
        
    except Exception as e:
        logger.error(f"Fatal error in scraper: {e}")
    
    return scraper.results, scraper.stats

def search_google_with_dork(driver, dork, max_pages, scraper):
    """Search Google with a specific dork and extract result URLs."""
    found_urls = []
    
    try:
        for page in range(max_pages):
            # Construct Google search URL
            start = page * 10  # Google shows 10 results per page
            search_url = f"https://www.google.com/search?q={dork}&start={start}"
            
            logger.info(f"  Page {page + 1}: {search_url}")
            
            # Use google_get with bypass
            driver.google_get(search_url, bypass_cloudflare=True)
            
            # Random human-like delay
            time.sleep(random.uniform(1, 3))
            
            # Check if we're blocked
            current_url = driver.current_url.lower()
            page_content = driver.page_html.lower()
            
            if any(block_indicator in current_url for block_indicator in [
                'sorry', 'captcha', 'unusual', 'blocked'
            ]) or any(block_text in page_content for block_text in [
                'unusual traffic', 'captcha', 'verify you are human', 'try again later'
            ]):
                logger.warning(f"  Blocked on page {page + 1}")
                scraper.stats['blocked_count'] += 1
                
                # Try alternative approach
                if try_alternative_search(driver, dork, scraper):
                    continue
                else:
                    break
            
            # Extract search result URLs
            page_urls = extract_search_result_urls(driver)
            found_urls.extend(page_urls)
            
            logger.info(f"  Found {len(page_urls)} URLs on page {page + 1}")
            
            # Break if no more results
            if len(page_urls) == 0:
                logger.info(f"  No more results, stopping at page {page + 1}")
                break
                
            scraper.stats['searches_performed'] += 1
    
    except Exception as e:
        logger.error(f"Error searching Google: {e}")
        scraper.stats['error_count'] += 1
    
    scraper.stats['urls_found'] += len(found_urls)
    return list(set(found_urls))  # Remove duplicates

def extract_search_result_urls(driver):
    """Extract URLs from Google search results."""
    urls = driver.run_js("""
        const urls = [];
        
        // Method 1: Standard search results
        document.querySelectorAll('div.g a').forEach(link => {
            const href = link.href;
            if (href && href.startsWith('http') && !href.includes('google.com')) {
                urls.push(href);
            }
        });
        
        // Method 2: Alternative selectors
        if (urls.length === 0) {
            document.querySelectorAll('a[href*="http"]').forEach(link => {
                const href = link.href;
                
                // Skip Google internal links
                if (href && href.startsWith('http') && 
                    !href.includes('google.com') && 
                    !href.includes('youtube.com') &&
                    !href.includes('maps.google') &&
                    !href.includes('accounts.google')) {
                    
                    // Clean URL if it's wrapped in Google redirect
                    let cleanUrl = href;
                    if (href.includes('/url?q=')) {
                        try {
                            const urlParams = new URLSearchParams(href.split('?')[1]);
                            if (urlParams.get('q')) {
                                cleanUrl = urlParams.get('q');
                            }
                        } catch(e) {}
                    }
                    
                    urls.push(cleanUrl);
                }
            });
        }
        
        // Remove duplicates and return
        return [...new Set(urls)];
    """)
    
    return urls or []

def try_alternative_search(driver, dork, scraper):
    """Try alternative search engines or methods when Google blocks."""
    try:
        # Try DuckDuckGo as backup
        logger.info("  Trying DuckDuckGo as backup...")
        ddg_url = f"https://duckduckgo.com/?q={dork}"
        driver.get(ddg_url)
        time.sleep(2)
        
        # Extract DDG results
        ddg_urls = driver.run_js("""
            const urls = [];
            document.querySelectorAll('a[href*="http"]').forEach(link => {
                const href = link.href;
                if (href && href.startsWith('http') && 
                    !href.includes('duckduckgo.com') && 
                    !href.includes('google.com')) {
                    urls.push(href);
                }
            });
            return [...new Set(urls)];
        """)
        
        if ddg_urls and len(ddg_urls) > 0:
            logger.info(f"  Found {len(ddg_urls)} URLs from DuckDuckGo")
            return True
            
    except Exception as e:
        logger.debug(f"Alternative search failed: {e}")
    
    return False

def extract_emails_from_urls(driver, urls, scraper, max_results):
    """Extract emails from a list of URLs."""
    processed = 0
    
    for url in urls[:max_results]:
        if processed >= max_results:
            break
            
        try:
            logger.info(f"    Checking: {url[:50]}...")
            
            # Visit the website
            driver.google_get(url, bypass_cloudflare=True)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Check if blocked
            current_url = driver.current_url.lower()
            if any(block in current_url for block in ['cloudflare', 'enable-javascript', 'captcha']):
                logger.debug(f"    Blocked: {url}")
                continue
            
            # Extract emails from page
            emails = extract_emails_from_page(driver)
            
            if emails:
                domain = urlparse(url).netloc
                for email in emails:
                    result = {
                        'email': email,
                        'source_url': url,
                        'domain': domain,
                        'found_at': datetime.now().isoformat()
                    }
                    scraper.results.append(result)
                    scraper.stats['emails_extracted'] += 1
                
                logger.info(f"    ✓ Found {len(emails)} emails: {emails}")
            else:
                logger.debug(f"    No emails found")
                
            processed += 1
            
        except Exception as e:
            logger.debug(f"    Error processing {url}: {str(e)[:50]}")
            scraper.stats['error_count'] += 1
            continue

def extract_emails_from_page(driver):
    """Extract emails from current page using multiple methods."""
    emails = driver.run_js("""
        const emails = new Set();
        
        // Method 1: Regex on page text
        const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
        const pageText = document.body.innerText || document.body.textContent || '';
        const textMatches = pageText.match(emailRegex) || [];
        textMatches.forEach(email => emails.add(email.toLowerCase()));
        
        // Method 2: Mailto links
        document.querySelectorAll('a[href^="mailto:"]').forEach(link => {
            const email = link.href.replace('mailto:', '').split('?')[0];
            if (email && email.includes('@')) {
                emails.add(email.toLowerCase());
            }
        });
        
        // Method 3: Contact sections
        const contactSelectors = [
            '[class*="contact"]', '[id*="contact"]',
            '[class*="email"]', '[id*="email"]',
            'footer', '.footer', '#footer'
        ];
        
        contactSelectors.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(elem => {
                    const text = elem.innerText || elem.textContent || '';
                    const matches = text.match(emailRegex) || [];
                    matches.forEach(email => emails.add(email.toLowerCase()));
                });
            } catch(e) {}
        });
        
        // Method 4: Data attributes
        document.querySelectorAll('[data-email]').forEach(elem => {
            const email = elem.getAttribute('data-email');
            if (email && email.includes('@')) {
                emails.add(email.toLowerCase());
            }
        });
        
        // Filter out invalid emails
        const validEmails = Array.from(emails).filter(email => {
            // Basic validation
            if (!email.includes('@') || !email.includes('.')) return false;
            
            // Skip common fake/test emails
            const invalidPatterns = [
                'example.com', 'test.com', 'demo.com', 'sample.com',
                'yoursite.com', 'yourdomain.com', 'yourcompany.com',
                'noreply', 'no-reply', 'donotreply',
                '.png', '.jpg', '.gif', '.pdf', '.css', '.js',
                'sentry.io', 'cloudflare.com', 'google.com'
            ];
            
            return !invalidPatterns.some(pattern => email.includes(pattern));
        });
        
        return validEmails;
    """)
    
    return emails or []

def save_results(results, stats, dorks_used):
    """Save scraping results to CSV and stats to text file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save CSV results
    output_dir = Path("google_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_filename = f"google_dork_results_{timestamp}.csv"
    csv_path = output_dir / csv_filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=['email', 'source_url', 'domain', 'found_at'])
            writer.writeheader()
            writer.writerows(results)
    
    # Save stats and settings
    stats_filename = f"google_dork_stats_{timestamp}.txt"
    stats_path = output_dir / stats_filename
    
    with open(stats_path, 'w', encoding='utf-8') as f:
        f.write("Google Dork Scraper Results\n")
        f.write("="*50 + "\n\n")
        f.write(f"Dorks used:\n")
        for i, dork in enumerate(dorks_used, 1):
            f.write(f"  {i}. {dork}\n")
        f.write(f"\nStats:\n")
        f.write(f"  Searches performed: {stats['searches_performed']}\n")
        f.write(f"  URLs found: {stats['urls_found']}\n")
        f.write(f"  Emails extracted: {stats['emails_extracted']}\n")
        f.write(f"  Blocked count: {stats['blocked_count']}\n")
        f.write(f"  Error count: {stats['error_count']}\n")
        
        if results:
            f.write(f"\nSuccess rate: {stats['emails_extracted']/max(stats['urls_found'], 1)*100:.1f}%\n")
    
    return str(csv_path), str(stats_path)

def main():
    """Main function to run Google dork scraper."""
    print("\n" + "="*80)
    print("GOOGLE DORK SCRAPER - ULTIMATE LEAD GENERATION TOOL")
    print("="*80)
    
    # Define powerful Google dorks
    POWERFUL_DORKS = [
        # Shopify stores
        'site:myshopify.com contact',
        '"powered by shopify" email',
        
        # Real estate
        '"real estate agent" email contact',
        'realtor contact email',
        
        # Local businesses
        '"small business" contact email',
        '"family owned" business email',
        
        # WordPress sites
        '"powered by wordpress" contact email',
        'site:wordpress.com contact',
        
        # Professional services
        '"insurance agent" email',
        '"financial advisor" contact',
        '"tax preparer" email',
        
        # E-commerce
        '"online store" contact email',
        '"e-commerce" contact email',
        
        # Service providers
        '"plumber" contact email',
        '"electrician" contact email',
        '"contractor" email',
    ]
    
    # Scraper settings
    settings = {
        'dorks': POWERFUL_DORKS[:5],  # Start with first 5 dorks
        'max_pages': 3,  # 3 pages per dork = ~30 URLs per dork
        'max_results_per_dork': 20,  # Check up to 20 websites per dork
        'delay_range': (2, 4)  # 2-4 second delays between requests
    }
    
    print(f"Testing {len(settings['dorks'])} Google dorks...")
    print("Dorks to test:")
    for i, dork in enumerate(settings['dorks'], 1):
        print(f"  {i}. {dork}")
    
    start_time = time.time()
    
    # Run the scraper
    results, stats = google_dork_scraper(settings)
    
    end_time = time.time()
    
    # Save results
    csv_file, stats_file = save_results(results, stats, settings['dorks'])
    
    # Print results
    print(f"\n" + "="*80)
    print("SCRAPING RESULTS:")
    print(f"  Time taken: {(end_time - start_time)/60:.1f} minutes")
    print(f"  Searches performed: {stats['searches_performed']}")
    print(f"  URLs found: {stats['urls_found']}")
    print(f"  Emails extracted: {stats['emails_extracted']}")
    print(f"  Success rate: {stats['emails_extracted']/max(stats['urls_found'], 1)*100:.1f}%")
    print(f"  Blocked count: {stats['blocked_count']}")
    print(f"  Error count: {stats['error_count']}")
    
    if results:
        print(f"\nEmails found:")
        unique_domains = set()
        for result in results[:20]:  # Show first 20
            domain = result['domain']
            unique_domains.add(domain)
            print(f"  • {result['email']} (from {domain})")
        
        print(f"\nUnique domains: {len(unique_domains)}")
    
    print(f"\nFiles saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Stats: {stats_file}")

if __name__ == "__main__":
    main()