#!/usr/bin/env python3
"""
Simple Business Scraper - Gets real business leads with emails
Uses web scraping to find business information
"""

import time
import json
import csv
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup

class SimpleBusinessScraper:
    """Simple scraper for business leads"""
    
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.total_businesses = 0
        self.emails_found = 0
        self.start_time = time.time()
    
    def search_bing(self, query, max_results=50):
        """Search Bing for businesses"""
        print(f"\n🔍 Searching Bing for: {query}")
        businesses = []
        
        try:
            # Search on Bing
            search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count=50"
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find business results
            results = soup.find_all('li', class_='b_algo') + soup.find_all('div', class_='b_algo')
            
            for result in results[:max_results]:
                business = {}
                
                # Get title and link
                title_elem = result.find('h2')
                if title_elem and title_elem.find('a'):
                    link = title_elem.find('a')
                    business['name'] = link.text.strip()
                    business['website'] = link.get('href', '')
                    
                    # Get snippet for address/phone
                    snippet = result.find('p') or result.find('div', class_='b_caption')
                    if snippet:
                        text = snippet.text
                        
                        # Extract phone
                        phone_match = re.search(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', text)
                        if phone_match:
                            business['phone'] = phone_match.group(1)
                        
                        # Extract address patterns
                        address_match = re.search(r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)', text, re.IGNORECASE)
                        if address_match:
                            business['address'] = address_match.group(0)
                        
                        business['description'] = text[:200]
                    
                    if business.get('name'):
                        businesses.append(business)
                        print(f"  ✓ Found: {business['name']}")
            
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"  ⚠️ Search error: {e}")
        
        return businesses
    
    def search_yellow_pages(self, business_type, city):
        """Search Yellow Pages for businesses"""
        print(f"\n📒 Searching Yellow Pages: {business_type} in {city}")
        businesses = []
        
        try:
            # Format city for URL
            city_formatted = city.lower().replace(' ', '-').replace(',', '')
            
            # Search Yellow Pages
            url = f"https://www.yellowpages.com/search?search_terms={quote_plus(business_type)}&geo_location_terms={quote_plus(city)}"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find business listings
            listings = soup.find_all('div', class_='result') or soup.find_all('div', class_='v-card')
            
            for listing in listings[:30]:
                business = {}
                
                # Business name
                name_elem = listing.find('a', class_='business-name') or listing.find('h2')
                if name_elem:
                    business['name'] = name_elem.text.strip()
                
                # Phone
                phone_elem = listing.find('div', class_='phones') or listing.find('div', class_='phone')
                if phone_elem:
                    business['phone'] = phone_elem.text.strip()
                
                # Address
                addr_elem = listing.find('div', class_='street-address') or listing.find('div', class_='adr')
                if addr_elem:
                    business['address'] = addr_elem.text.strip()
                
                # Website
                website_elem = listing.find('a', class_='track-visit-website')
                if website_elem:
                    business['website'] = website_elem.get('href', '')
                
                # Category
                cat_elem = listing.find('div', class_='categories')
                if cat_elem:
                    business['category'] = cat_elem.text.strip()
                
                if business.get('name'):
                    businesses.append(business)
                    print(f"  ✓ Found: {business['name']}")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"  ⚠️ Yellow Pages error: {e}")
        
        return businesses
    
    def extract_email_from_website(self, url):
        """Extract email from website"""
        if not url or not url.startswith('http'):
            return None
        
        try:
            # Visit website
            response = self.session.get(url, timeout=5)
            text = response.text.lower()
            
            # Find emails
            email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            emails = re.findall(email_pattern, text, re.IGNORECASE)
            
            # Filter and prioritize business emails
            business_emails = []
            other_emails = []
            
            for email in emails:
                email = email.lower()
                if any(x in email for x in ['example.', 'test.', 'demo.', 'sentry.']):
                    continue
                    
                if any(x in email for x in ['info@', 'contact@', 'sales@', 'support@', 'hello@', 'admin@']):
                    business_emails.append(email)
                else:
                    other_emails.append(email)
            
            # Check contact page
            if not business_emails and not other_emails:
                contact_urls = [
                    url.rstrip('/') + '/contact',
                    url.rstrip('/') + '/contact-us',
                    url.rstrip('/') + '/about',
                    url.rstrip('/') + '/about-us'
                ]
                
                for contact_url in contact_urls:
                    try:
                        response = self.session.get(contact_url, timeout=3)
                        text = response.text.lower()
                        emails = re.findall(email_pattern, text, re.IGNORECASE)
                        
                        for email in emails:
                            email = email.lower()
                            if not any(x in email for x in ['example.', 'test.', 'demo.']):
                                business_emails.append(email)
                                break
                        
                        if business_emails:
                            break
                            
                    except:
                        continue
            
            if business_emails:
                return business_emails[0]
            elif other_emails:
                return other_emails[0]
                
        except Exception as e:
            pass
        
        return None
    
    def scrape_businesses(self):
        """Main scraping function"""
        print("\n" + "="*60)
        print("🚀 STARTING BUSINESS LEAD SCRAPER")
        print("="*60)
        
        # Cities to search
        cities = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
            "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
            "Dallas, TX", "Miami, FL", "Atlanta, GA", "Boston, MA",
            "Seattle, WA", "Denver, CO", "Las Vegas, NV"
        ]
        
        # Business types
        business_types = [
            "restaurant", "dental clinic", "law firm", "accounting firm",
            "real estate agency", "auto repair shop", "plumbing service",
            "electrical contractor", "landscaping company", "marketing agency",
            "insurance agency", "medical clinic", "veterinary clinic",
            "hair salon", "fitness center", "coffee shop", "bakery",
            "construction company", "roofing contractor", "HVAC service"
        ]
        
        all_businesses = []
        target = 1000
        
        print(f"\n🎯 Target: {target} business leads with contact info")
        print(f"📍 Cities: {len(cities)}")
        print(f"🏢 Business types: {len(business_types)}\n")
        
        # Search loop
        for city in cities:
            if len(all_businesses) >= target:
                break
                
            for business_type in business_types:
                if len(all_businesses) >= target:
                    break
                
                # Search query
                query = f"{business_type} {city} contact email phone"
                
                # Try Bing search
                businesses = self.search_bing(query, max_results=20)
                
                # Try Yellow Pages
                if len(businesses) < 10:
                    yp_businesses = self.search_yellow_pages(business_type, city)
                    businesses.extend(yp_businesses)
                
                # Process businesses
                for business in businesses:
                    if len(all_businesses) >= target:
                        break
                    
                    # Enrich with email if website available
                    if business.get('website'):
                        print(f"  🌐 Checking website: {business['website'][:50]}...")
                        email = self.extract_email_from_website(business['website'])
                        if email:
                            business['email'] = email
                            self.emails_found += 1
                            print(f"    ✉️ Found email: {email}")
                    
                    # Add metadata
                    business['city'] = city
                    business['search_type'] = business_type
                    business['source'] = 'Web Search'
                    business['scraped_at'] = datetime.now().isoformat()
                    
                    # Add to results
                    all_businesses.append(business)
                    self.total_businesses += 1
                    
                    # Progress update
                    if self.total_businesses % 10 == 0:
                        elapsed = time.time() - self.start_time
                        rate = self.emails_found / max(self.total_businesses, 1) * 100
                        print(f"\n📊 Progress: {self.total_businesses}/{target} businesses")
                        print(f"   Emails found: {self.emails_found} ({rate:.1f}% success rate)")
                        print(f"   Time elapsed: {elapsed:.0f} seconds\n")
                        
                        # Save incrementally
                        self.save_results(all_businesses)
        
        # Final save
        self.save_results(all_businesses)
        
        # Print summary
        print("\n" + "="*60)
        print("✅ SCRAPING COMPLETE!")
        print("="*60)
        print(f"Total businesses found: {len(all_businesses)}")
        print(f"Emails extracted: {self.emails_found}")
        print(f"Email success rate: {(self.emails_found/len(all_businesses)*100):.1f}%")
        print(f"Time taken: {(time.time() - self.start_time):.0f} seconds")
        print(f"\n📁 Results saved to: output/us_business_owners.csv")
        print("="*60 + "\n")
        
        # Show sample results
        if all_businesses:
            print("📋 Sample Results:\n")
            for business in all_businesses[:5]:
                print(f"• {business.get('name', 'Unknown')}")
                print(f"  📍 Location: {business.get('city', 'N/A')}")
                print(f"  📞 Phone: {business.get('phone', 'N/A')}")
                print(f"  ✉️ Email: {business.get('email', 'N/A')}")
                print(f"  🌐 Website: {business.get('website', 'N/A')[:50]}...")
                print()
        
        return all_businesses
    
    def save_results(self, businesses):
        """Save results to CSV and JSON"""
        
        # Save to CSV
        csv_path = self.output_dir / "us_business_owners.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if businesses:
                fieldnames = ['name', 'email', 'phone', 'address', 'website', 'city', 
                             'category', 'search_type', 'source', 'scraped_at', 'description']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
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
            'runtime_seconds': int(time.time() - self.start_time),
            'scraped_at': datetime.now().isoformat()
        }
        
        stats_path = self.output_dir / "scraping_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)

def main():
    """Main execution"""
    # Check for required packages
    try:
        import requests
        import bs4
    except ImportError:
        print("Installing required packages...")
        import os
        os.system("pip install requests beautifulsoup4")
        print("Packages installed. Please run the script again.")
        return
    
    # Run scraper
    scraper = SimpleBusinessScraper()
    results = scraper.scrape_businesses()
    
    print("\n✨ Done! Check the output folder for your business leads.")

if __name__ == "__main__":
    main()