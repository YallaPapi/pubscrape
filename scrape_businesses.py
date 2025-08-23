#!/usr/bin/env python3
"""
Production Business Lead Scraper
Scrapes real business data from Bing Maps and Google Maps
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import csv
from typing import List, Dict
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import our components
try:
    from botasaurus import *
    from botasaurus.browser import browser, Driver
    from botasaurus.request import request
    print("✓ Botasaurus imported successfully")
except ImportError as e:
    print(f"⚠ Botasaurus not found: {e}")
    print("Installing botasaurus...")
    os.system("pip install botasaurus")
    from botasaurus import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BusinessScraper:
    """Main business scraper using Botasaurus"""
    
    def __init__(self):
        self.results = []
        self.emails_found = 0
        self.businesses_scraped = 0
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
    @browser(
        headless=False,  # Set to True for production
        block_resources=True,
        block_images=True,
        add_arguments=["--disable-blink-features=AutomationControlled"],
    )
    def scrape_bing_maps(self, driver: Driver, query: str):
        """Scrape business listings from Bing Maps"""
        try:
            logger.info(f"Searching Bing Maps for: {query}")
            
            # Navigate to Bing Maps
            driver.get("https://www.bing.com/maps")
            driver.sleep(2)
            
            # Search for businesses
            search_box = driver.select('input[type="search"], input[name="q"], #maps_sb')
            if search_box:
                search_box.type(query)
                driver.sleep(1)
                search_box.press("Enter")
                driver.sleep(3)
            
            # Wait for results to load
            driver.wait_for_element('.b_entityTP', timeout=10)
            
            # Scroll to load more results
            businesses = []
            last_count = 0
            scroll_attempts = 0
            max_scrolls = 10
            
            while scroll_attempts < max_scrolls:
                # Get current business cards
                cards = driver.select_all('.b_entityTP, .microcard, div[data-entityid]')
                
                for card in cards:
                    try:
                        business_data = self.extract_bing_business(driver, card)
                        if business_data and business_data not in businesses:
                            businesses.append(business_data)
                            logger.info(f"Found business: {business_data.get('name', 'Unknown')}")
                    except Exception as e:
                        logger.debug(f"Error extracting business card: {e}")
                
                # Check if we got new results
                if len(businesses) == last_count:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_count = len(businesses)
                
                # Scroll to load more
                driver.execute_script("window.scrollBy(0, 500)")
                driver.sleep(1.5)
                
                # Check for "Load more" button
                load_more = driver.select('button:contains("more"), a:contains("more results")')
                if load_more:
                    load_more.click()
                    driver.sleep(2)
            
            logger.info(f"Found {len(businesses)} businesses from Bing Maps")
            return businesses
            
        except Exception as e:
            logger.error(f"Error scraping Bing Maps: {e}")
            return []
    
    def extract_bing_business(self, driver: Driver, card):
        """Extract business data from Bing Maps card"""
        business = {}
        
        try:
            # Business name
            name_elem = card.select('h2, .b_entityTitle, [class*="title"]')
            if name_elem:
                business['name'] = name_elem.text.strip()
            
            # Address
            addr_elem = card.select('.b_factrow:contains("Address"), [class*="address"]')
            if addr_elem:
                business['address'] = addr_elem.text.replace('Address:', '').strip()
            
            # Phone
            phone_elem = card.select('.b_factrow:contains("Phone"), [class*="phone"], a[href^="tel:"]')
            if phone_elem:
                phone = phone_elem.get_attribute('href') or phone_elem.text
                business['phone'] = phone.replace('tel:', '').replace('Phone:', '').strip()
            
            # Website
            website_elem = card.select('a[href*="http"]:not([href*="bing"]):not([href*="microsoft"])')
            if website_elem:
                business['website'] = website_elem.get_attribute('href')
            
            # Rating
            rating_elem = card.select('[class*="rating"], .csrc_rating')
            if rating_elem:
                business['rating'] = rating_elem.text.strip()
            
            # Category
            cat_elem = card.select('.b_factrow:contains("Category"), [class*="category"]')
            if cat_elem:
                business['category'] = cat_elem.text.replace('Category:', '').strip()
                
        except Exception as e:
            logger.debug(f"Error extracting business fields: {e}")
        
        return business if business.get('name') else None
    
    @browser(
        headless=False,
        block_resources=True,
        block_images=True,
    )
    def extract_emails_from_website(self, driver: Driver, url: str):
        """Visit website and extract email addresses"""
        try:
            if not url or not url.startswith('http'):
                return None
                
            logger.info(f"Visiting website: {url}")
            driver.get(url, timeout=15)
            driver.sleep(2)
            
            emails = set()
            
            # Check common contact pages
            contact_links = [
                'a:contains("Contact")',
                'a:contains("About")',
                'a:contains("Team")',
                'a:contains("Staff")',
                'a[href*="contact"]',
                'a[href*="about"]'
            ]
            
            for selector in contact_links:
                link = driver.select(selector)
                if link:
                    try:
                        link.click()
                        driver.sleep(1.5)
                        break
                    except:
                        pass
            
            # Extract emails from page
            page_text = driver.get_text()
            
            # Find mailto links
            mailto_links = driver.select_all('a[href^="mailto:"]')
            for link in mailto_links:
                email = link.get_attribute('href').replace('mailto:', '').split('?')[0]
                if '@' in email:
                    emails.add(email.lower())
            
            # Find emails in text using regex
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found_emails = re.findall(email_pattern, page_text)
            
            for email in found_emails:
                email = email.lower()
                # Filter out common non-business emails
                if not any(x in email for x in ['example.', 'test.', 'demo.', 'sample.']):
                    emails.add(email)
            
            # Look for obfuscated emails
            obfuscated_patterns = [
                r'([a-zA-Z0-9._%+-]+)\s*\[\s*at\s*\]\s*([a-zA-Z0-9.-]+)\s*\[\s*dot\s*\]\s*([a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+)\s*\(\s*at\s*\)\s*([a-zA-Z0-9.-]+)\s*\(\s*dot\s*\)\s*([a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+)\s+at\s+([a-zA-Z0-9.-]+)\s+dot\s+([a-zA-Z]{2,})',
            ]
            
            for pattern in obfuscated_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    if len(match) == 3:
                        email = f"{match[0]}@{match[1]}.{match[2]}".lower()
                        emails.add(email)
            
            # Return primary business email
            business_emails = [e for e in emails if any(x in e for x in ['info@', 'contact@', 'sales@', 'support@', 'admin@', 'hello@'])]
            
            if business_emails:
                return business_emails[0]
            elif emails:
                return list(emails)[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting emails from {url}: {e}")
            return None
    
    async def scrape_businesses(self, queries: List[str], max_results: int = 1000):
        """Main scraping orchestrator"""
        logger.info(f"Starting scrape for {len(queries)} queries, target: {max_results} leads")
        
        all_businesses = []
        
        for query in queries:
            if len(all_businesses) >= max_results:
                break
                
            # Scrape from Bing Maps
            businesses = self.scrape_bing_maps(query)
            
            # Enrich with email data
            for business in businesses:
                if len(all_businesses) >= max_results:
                    break
                    
                if business.get('website'):
                    email = self.extract_emails_from_website(business['website'])
                    if email:
                        business['email'] = email
                        self.emails_found += 1
                
                business['source'] = 'Bing Maps'
                business['query'] = query
                business['scraped_at'] = datetime.now().isoformat()
                
                all_businesses.append(business)
                self.businesses_scraped += 1
                
                # Save incrementally
                if len(all_businesses) % 10 == 0:
                    self.save_results(all_businesses)
                    logger.info(f"Progress: {len(all_businesses)}/{max_results} businesses, {self.emails_found} emails found")
        
        # Final save
        self.save_results(all_businesses)
        return all_businesses
    
    def save_results(self, businesses: List[Dict]):
        """Save results to CSV and JSON"""
        
        # Save to CSV
        csv_path = self.output_dir / "us_business_owners.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if businesses:
                writer = csv.DictWriter(f, fieldnames=businesses[0].keys())
                writer.writeheader()
                writer.writerows(businesses)
        
        # Save to JSON
        json_path = self.output_dir / "us_business_owners.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(businesses, f, indent=2, ensure_ascii=False)
        
        # Save statistics
        stats = {
            'total_businesses': len(businesses),
            'emails_found': self.emails_found,
            'email_rate': f"{(self.emails_found/len(businesses)*100):.1f}%" if businesses else "0%",
            'scraped_at': datetime.now().isoformat()
        }
        
        stats_path = self.output_dir / "scraping_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Results saved to {csv_path}")

def generate_queries():
    """Generate search queries for US businesses"""
    cities = [
        "New York NY", "Los Angeles CA", "Chicago IL", "Houston TX",
        "Phoenix AZ", "Philadelphia PA", "San Antonio TX", "San Diego CA",
        "Dallas TX", "Miami FL", "Atlanta GA", "Boston MA", "Seattle WA",
        "Denver CO", "Las Vegas NV", "Portland OR", "Detroit MI",
        "Nashville TN", "Austin TX", "San Francisco CA"
    ]
    
    business_types = [
        "restaurant", "dental clinic", "law firm", "accounting firm",
        "real estate agency", "auto repair", "plumbing service",
        "electrical contractor", "landscaping", "marketing agency",
        "insurance agency", "medical clinic", "veterinary clinic",
        "hair salon", "fitness center", "coffee shop", "bakery",
        "construction company", "roofing contractor", "HVAC service"
    ]
    
    queries = []
    for city in cities[:10]:  # Start with 10 cities
        for business_type in business_types[:10]:  # Start with 10 business types
            queries.append(f"{business_type} near {city}")
    
    return queries

async def main():
    """Main execution"""
    print("\n" + "="*60)
    print("US BUSINESS OWNER LEAD SCRAPER")
    print("="*60 + "\n")
    
    scraper = BusinessScraper()
    queries = generate_queries()
    
    print(f"Generated {len(queries)} search queries")
    print(f"Target: 1000 business leads with emails\n")
    
    # Run scraper
    results = await scraper.scrape_businesses(queries, max_results=1000)
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    print(f"Total businesses found: {len(results)}")
    print(f"Emails extracted: {scraper.emails_found}")
    print(f"Email success rate: {(scraper.emails_found/len(results)*100):.1f}%" if results else "0%")
    print(f"\nResults saved to: output/us_business_owners.csv")
    print("="*60 + "\n")
    
    # Show sample results
    if results:
        print("Sample results:")
        for business in results[:5]:
            print(f"\n• {business.get('name', 'Unknown')}")
            print(f"  Address: {business.get('address', 'N/A')}")
            print(f"  Phone: {business.get('phone', 'N/A')}")
            print(f"  Email: {business.get('email', 'N/A')}")
            print(f"  Website: {business.get('website', 'N/A')}")

if __name__ == "__main__":
    # Check if botasaurus is installed
    try:
        import botasaurus
        print("✓ Botasaurus is installed")
    except ImportError:
        print("Installing botasaurus...")
        os.system("pip install botasaurus")
    
    # Run the scraper
    asyncio.run(main())