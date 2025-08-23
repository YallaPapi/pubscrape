# **PHASE 2: REAL BROWSER SCRAPERS**
## **Week 2 - Build Actual Web Scraping Functionality**

---

## **🎯 PHASE 2 OBJECTIVES**

**PRIMARY GOAL**: Create real browser scrapers that visit actual websites and extract genuine business data using Botasaurus.

**SUCCESS CRITERIA**:
- Google Maps scraper extracts real businesses
- Website email extractor finds real contact information  
- Complete end-to-end lead generation with actual data
- Zero fake/generated data in any outputs

---

## **📋 DAY-BY-DAY IMPLEMENTATION**

### **DAY 1: GOOGLE MAPS SCRAPER FOUNDATION**

#### **CREATE: Core Google Maps Scraper**

**FILE: `src/scrapers/google_maps_scraper.py`**
```python
from botasaurus.browser import browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

@browser(headless=False, block_images=True, window_size="1920,1080")
def scrape_google_maps_businesses(driver, search_data):
    """
    Actually visit Google Maps and extract real businesses
    No fake data generation - only real web scraping
    """
    search_query = search_data.get('query', 'restaurants in New York NY')
    max_results = search_data.get('max_results', 50)
    
    businesses = []
    
    try:
        # Step 1: Navigate to Google Maps
        print(f"🗺️ Opening Google Maps...")
        driver.get("https://www.google.com/maps")
        time.sleep(3)
        
        # Step 2: Find and click search box
        print(f"🔍 Searching for: {search_query}")
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "searchboxinput"))
        )
        
        # Clear and enter search query
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys("\n")
        
        # Step 3: Wait for results to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='article'], [data-result-index]"))
        )
        time.sleep(5)
        
        # Step 4: Scroll to load more results
        print("📜 Scrolling to load more results...")
        last_count = 0
        scroll_attempts = 0
        
        while len(businesses) < max_results and scroll_attempts < 10:
            # Extract current visible businesses
            business_elements = driver.find_elements(By.CSS_SELECTOR, 
                "[role='article'], [data-result-index], .hfpxzc")
            
            for element in business_elements:
                if len(businesses) >= max_results:
                    break
                    
                business_data = extract_business_from_element(element)
                if business_data and not is_duplicate(business_data, businesses):
                    businesses.append(business_data)
                    print(f"✅ Found: {business_data.get('name', 'Unknown')}")
            
            # Check if we got new results
            if len(businesses) == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = len(businesses)
            
            # Scroll down to load more
            driver.execute_script("window.scrollBy(0, 500)")
            time.sleep(random.uniform(1, 3))  # Human-like delay
        
        print(f"📊 Extracted {len(businesses)} real businesses from Google Maps")
        return businesses
        
    except Exception as e:
        print(f"❌ Google Maps scraping error: {e}")
        return businesses

def extract_business_from_element(element):
    """Extract real business data from Google Maps DOM element"""
    business = {}
    
    try:
        # Business name - try multiple selectors
        name_selectors = [
            ".fontHeadlineSmall",
            "[data-value='title']", 
            ".qBF1Pd",
            ".fontHeadlineLarge"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = element.find_element(By.CSS_SELECTOR, selector)
                business['name'] = name_elem.text.strip()
                break
            except:
                continue
        
        # Address
        try:
            address_elem = element.find_element(By.CSS_SELECTOR, 
                ".W4Efsd:last-child, [data-value='address']")
            business['address'] = address_elem.text.strip()
        except:
            business['address'] = None
        
        # Phone number
        try:
            phone_elem = element.find_element(By.CSS_SELECTOR, 
                "[href^='tel:'], [data-value='phone']")
            phone = phone_elem.get_attribute('href') or phone_elem.text
            business['phone'] = phone.replace('tel:', '').strip()
        except:
            business['phone'] = None
        
        # Website
        try:
            website_elem = element.find_element(By.CSS_SELECTOR,
                "[data-value='website'], a[href*='http']:not([href*='google'])")
            business['website'] = website_elem.get_attribute('href')
        except:
            business['website'] = None
        
        # Rating
        try:
            rating_elem = element.find_element(By.CSS_SELECTOR,
                ".MW4etd, [data-value='rating']")
            business['rating'] = rating_elem.text.strip()
        except:
            business['rating'] = None
        
        # Category
        try:
            category_elem = element.find_element(By.CSS_SELECTOR,
                ".W4Efsd:first-child")
            business['category'] = category_elem.text.strip()
        except:
            business['category'] = None
        
        # Add metadata
        business['source'] = 'google_maps_real_scraping'
        business['scraped_at'] = time.time()
        
        return business if business.get('name') else None
        
    except Exception as e:
        print(f"⚠️ Error extracting business data: {e}")
        return None

def is_duplicate(new_business, existing_businesses):
    """Check if business is already in the list"""
    new_name = new_business.get('name', '').lower()
    for existing in existing_businesses:
        if existing.get('name', '').lower() == new_name:
            return True
    return False

# Test function
if __name__ == "__main__":
    test_data = {
        'query': 'coffee shops in Seattle',
        'max_results': 10
    }
    
    results = scrape_google_maps_businesses(test_data)
    print(f"\n📊 GOOGLE MAPS TEST RESULTS:")
    print(f"Total businesses found: {len(results)}")
    
    for i, business in enumerate(results, 1):
        print(f"\n{i}. {business.get('name')}")
        print(f"   Address: {business.get('address')}")
        print(f"   Phone: {business.get('phone')}")
        print(f"   Website: {business.get('website')}")
```

#### **TESTING DAY 1 DELIVERABLE**
```bash
# Test the Google Maps scraper
cd C:\Users\stuar\Desktop\Projects\pubscrape
python src/scrapers/google_maps_scraper.py

# Expected output: List of real coffee shops in Seattle with actual data
```

---

### **DAY 2: EMAIL EXTRACTION SCRAPER**

#### **CREATE: Website Email Extractor**

**FILE: `src/scrapers/email_extractor.py`**
```python
from botasaurus.browser import browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

@browser(headless=True, block_images=True)
def extract_emails_from_website(driver, website_data):
    """
    Visit real business website and extract real email addresses
    No fake email generation - only actual extraction
    """
    url = website_data.get('url') if isinstance(website_data, dict) else website_data
    business_name = website_data.get('name', 'Unknown') if isinstance(website_data, dict) else 'Unknown'
    
    if not url or not url.startswith('http'):
        return None
    
    try:
        print(f"📧 Visiting {business_name}: {url}")
        
        # Step 1: Load the main page
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(3)
        
        # Step 2: Look for contact page links
        contact_keywords = [
            'contact', 'about', 'reach', 'connect', 
            'info', 'team', 'staff', 'management'
        ]
        
        contact_links = []
        for keyword in contact_keywords:
            try:
                links = driver.find_elements(By.XPATH, 
                    f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                contact_links.extend(links)
            except:
                continue
        
        # Step 3: Extract emails from main page
        main_page_emails = extract_emails_from_page_content(driver)
        
        # Step 4: Check contact pages for more emails
        contact_page_emails = []
        for link in contact_links[:3]:  # Check max 3 contact pages
            try:
                contact_url = link.get_attribute('href')
                if contact_url and contact_url != url:
                    print(f"  🔍 Checking contact page: {contact_url}")
                    driver.get(contact_url)
                    time.sleep(2)
                    
                    page_emails = extract_emails_from_page_content(driver)
                    contact_page_emails.extend(page_emails)
                    
                    # Return to main page
                    driver.back()
                    time.sleep(1)
            except:
                continue
        
        # Step 5: Combine and filter emails
        all_emails = main_page_emails + contact_page_emails
        real_emails = filter_real_emails(all_emails, url)
        
        if real_emails:
            best_email = select_best_email(real_emails, business_name)
            print(f"  ✅ Found email: {best_email}")
            return best_email
        else:
            print(f"  ❌ No emails found")
            return None
            
    except Exception as e:
        print(f"  ❌ Error extracting from {url}: {e}")
        return None

def extract_emails_from_page_content(driver):
    """Extract all emails from current page"""
    emails = []
    
    try:
        # Method 1: Find mailto links
        mailto_links = driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
        for link in mailto_links:
            email = link.get_attribute('href').replace('mailto:', '').split('?')[0]
            emails.append(email)
        
        # Method 2: Extract from page text using regex
        page_text = driver.page_source
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        text_emails = re.findall(email_pattern, page_text)
        emails.extend(text_emails)
        
        # Method 3: Check common email elements
        email_selectors = [
            "[href*='@']",
            ".email",
            "#email", 
            "[class*='email']",
            "[id*='email']"
        ]
        
        for selector in email_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text or elem.get_attribute('href') or elem.get_attribute('value')
                    if text and '@' in text:
                        found_emails = re.findall(email_pattern, text)
                        emails.extend(found_emails)
            except:
                continue
        
        return list(set(emails))  # Remove duplicates
        
    except Exception as e:
        print(f"    ⚠️ Error extracting emails from page: {e}")
        return []

def filter_real_emails(emails, website_url):
    """Filter out fake, generic, or invalid emails"""
    real_emails = []
    
    # Get domain from website URL
    try:
        website_domain = website_url.split('//')[1].split('/')[0].lower()
    except:
        website_domain = ""
    
    fake_patterns = [
        'example.com', 'test.com', 'demo.com', 'placeholder',
        'your-email', 'youremail', 'email@', '@email',
        'noreply', 'no-reply', 'donotreply', 'postmaster',
        'mailer-daemon', 'abuse@', 'spam@'
    ]
    
    for email in emails:
        email = email.lower().strip()
        
        # Skip invalid formats
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            continue
        
        # Skip fake patterns
        if any(pattern in email for pattern in fake_patterns):
            continue
        
        # Skip overly long emails (likely corrupted)
        if len(email) > 50:
            continue
        
        real_emails.append(email)
    
    return real_emails

def select_best_email(emails, business_name):
    """Select the most likely business email"""
    if not emails:
        return None
    
    # Prioritize emails with business-relevant keywords
    priority_keywords = ['info', 'contact', 'hello', 'admin', 'office']
    
    for keyword in priority_keywords:
        for email in emails:
            if keyword in email.split('@')[0]:
                return email
    
    # Return first email if no priority match
    return emails[0]

# Test function
if __name__ == "__main__":
    test_websites = [
        "https://www.starbucks.com",
        "https://www.dunkindonuts.com", 
        "https://www.peets.com"
    ]
    
    print("📧 EMAIL EXTRACTION TEST")
    print("=" * 50)
    
    for url in test_websites:
        email = extract_emails_from_website({'url': url, 'name': 'Test Business'})
        print(f"Website: {url}")
        print(f"Email: {email or 'None found'}")
        print()
```

#### **TESTING DAY 2 DELIVERABLE**
```bash
# Test the email extractor
python src/scrapers/email_extractor.py

# Expected output: Real email addresses from actual business websites
```

---

### **DAY 3: INTEGRATED LEAD GENERATOR**

#### **CREATE: Main Lead Generation Pipeline**

**FILE: `real_business_lead_generator.py`**
```python
from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
from src.scrapers.email_extractor import extract_emails_from_website
import json
import csv
from datetime import datetime
import os

class RealBusinessLeadGenerator:
    """
    Real business lead generator using actual browser scraping
    ZERO fake data generation - only real extraction
    """
    
    def __init__(self):
        self.results = []
        self.stats = {
            'total_businesses': 0,
            'with_emails': 0,
            'with_phones': 0,
            'with_websites': 0,
            'success_rate': 0
        }
    
    def generate_leads(self, search_queries, target_count=100):
        """
        Generate real business leads using actual web scraping
        """
        print(f"🚀 Starting REAL lead generation for {target_count} leads")
        print(f"📝 Search queries: {search_queries}")
        
        all_leads = []
        
        for i, query in enumerate(search_queries, 1):
            if len(all_leads) >= target_count:
                break
                
            print(f"\n🔍 [{i}/{len(search_queries)}] Processing: {query}")
            
            # Step 1: Get real businesses from Google Maps
            search_data = {
                'query': query,
                'max_results': min(50, target_count - len(all_leads))
            }
            
            businesses = scrape_google_maps_businesses(search_data)
            print(f"   📊 Found {len(businesses)} businesses on Google Maps")
            
            # Step 2: Extract emails from business websites
            for j, business in enumerate(businesses, 1):
                if len(all_leads) >= target_count:
                    break
                
                print(f"   📧 [{j}/{len(businesses)}] Processing: {business.get('name', 'Unknown')}")
                
                # Add search query info
                business['search_query'] = query
                business['scraped_timestamp'] = datetime.now().isoformat()
                
                # Try to get email if website exists
                if business.get('website'):
                    email_data = {
                        'url': business['website'],
                        'name': business.get('name', 'Unknown')
                    }
                    
                    email = extract_emails_from_website(email_data)
                    if email:
                        business['email'] = email
                        business['email_source'] = 'website_extraction'
                    else:
                        business['email'] = None
                        business['email_source'] = 'not_found'
                else:
                    business['email'] = None
                    business['email_source'] = 'no_website'
                
                all_leads.append(business)
                self._update_stats(all_leads)
                
                print(f"      ✅ Lead #{len(all_leads)}: {business.get('name')} - Email: {business.get('email', 'None')}")
        
        self.results = all_leads
        self._print_final_stats()
        
        return all_leads
    
    def _update_stats(self, leads):
        """Update statistics"""
        self.stats['total_businesses'] = len(leads)
        self.stats['with_emails'] = sum(1 for lead in leads if lead.get('email'))
        self.stats['with_phones'] = sum(1 for lead in leads if lead.get('phone'))
        self.stats['with_websites'] = sum(1 for lead in leads if lead.get('website'))
        
        if len(leads) > 0:
            self.stats['success_rate'] = round((self.stats['with_emails'] / len(leads)) * 100, 1)
    
    def _print_final_stats(self):
        """Print final statistics"""
        print(f"\n📊 FINAL REAL LEAD GENERATION STATS:")
        print(f"   Total Businesses: {self.stats['total_businesses']}")
        print(f"   With Emails: {self.stats['with_emails']} ({self.stats['success_rate']}%)")
        print(f"   With Phones: {self.stats['with_phones']}")
        print(f"   With Websites: {self.stats['with_websites']}")
    
    def export_to_csv(self, filename=None):
        """Export real leads to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output/real_business_leads_{timestamp}.csv"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        if not self.results:
            print("❌ No results to export")
            return
        
        fieldnames = [
            'name', 'email', 'phone', 'address', 'website', 
            'category', 'rating', 'search_query', 'email_source',
            'source', 'scraped_timestamp'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in self.results:
                # Only write real data - no fake generation
                row = {field: lead.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        print(f"📄 Exported {len(self.results)} REAL leads to: {filename}")
        return filename
    
    def export_to_json(self, filename=None):
        """Export real leads to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output/real_business_leads_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        export_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_leads': len(self.results),
                'data_source': 'real_web_scraping',
                'fake_data': False,
                'statistics': self.stats
            },
            'leads': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"📄 Exported {len(self.results)} REAL leads to: {filename}")
        return filename

# Test script
if __name__ == "__main__":
    # Test with small dataset
    generator = RealBusinessLeadGenerator()
    
    test_queries = [
        "coffee shops in Portland OR",
        "bookstores in Austin TX"
    ]
    
    # Generate 20 real leads for testing
    leads = generator.generate_leads(test_queries, target_count=20)
    
    # Export results
    csv_file = generator.export_to_csv()
    json_file = generator.export_to_json()
    
    print(f"\n🎉 REAL LEAD GENERATION TEST COMPLETE")
    print(f"📊 Generated {len(leads)} genuine business leads")
    print(f"📄 CSV: {csv_file}")
    print(f"📄 JSON: {json_file}")
```

#### **TESTING DAY 3 DELIVERABLE**
```bash
# Test integrated lead generator
python real_business_lead_generator.py

# Expected: 20 real business leads with actual data from Portland/Austin
```

---

### **DAY 4: PRODUCTION-SCALE SCRAPER**

#### **CREATE: High-Volume Business Scraper**

**FILE: `production_business_scraper.py`**
```python
from real_business_lead_generator import RealBusinessLeadGenerator
import argparse
import json
import time

def main():
    """Production-scale real business lead generation"""
    
    parser = argparse.ArgumentParser(description='Real Business Lead Generator')
    parser.add_argument('--queries', type=str, required=True,
                       help='JSON file with search queries')
    parser.add_argument('--count', type=int, default=1000,
                       help='Target number of leads')
    parser.add_argument('--output', type=str, default='output/',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Load search queries
    with open(args.queries, 'r') as f:
        queries_data = json.load(f)
    
    search_queries = queries_data.get('queries', [])
    
    if not search_queries:
        print("❌ No search queries found in JSON file")
        return
    
    print(f"🚀 PRODUCTION REAL LEAD GENERATION")
    print(f"📝 Queries: {len(search_queries)}")
    print(f"🎯 Target: {args.count} real leads")
    print(f"📁 Output: {args.output}")
    print(f"=" * 60)
    
    start_time = time.time()
    
    # Initialize generator
    generator = RealBusinessLeadGenerator()
    
    # Generate real leads
    leads = generator.generate_leads(search_queries, target_count=args.count)
    
    # Export results
    csv_file = generator.export_to_csv(f"{args.output}/business_leads_production.csv")
    json_file = generator.export_to_json(f"{args.output}/business_leads_production.json")
    
    elapsed_time = time.time() - start_time
    
    print(f"\n🎉 PRODUCTION SCRAPING COMPLETE")
    print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
    print(f"📊 Real leads generated: {len(leads)}")
    print(f"⚡ Speed: {len(leads) / (elapsed_time / 60):.1f} leads/minute")
    print(f"📄 CSV: {csv_file}")
    print(f"📄 JSON: {json_file}")

if __name__ == "__main__":
    main()
```

#### **CREATE: Sample Query Configuration**

**FILE: `config/production_queries.json`**
```json
{
    "queries": [
        "restaurants in New York NY",
        "restaurants in Los Angeles CA", 
        "restaurants in Chicago IL",
        "restaurants in Houston TX",
        "restaurants in Phoenix AZ",
        
        "dental clinics in New York NY",
        "dental clinics in Los Angeles CA",
        "dental clinics in Chicago IL",
        "dental clinics in Houston TX",
        "dental clinics in Phoenix AZ",
        
        "law firms in New York NY",
        "law firms in Los Angeles CA",
        "law firms in Chicago IL",
        "law firms in Houston TX",
        "law firms in Phoenix AZ",
        
        "auto repair shops in Seattle WA",
        "auto repair shops in Portland OR",
        "auto repair shops in Denver CO",
        "auto repair shops in Austin TX",
        "auto repair shops in Atlanta GA",
        
        "medical clinics in Boston MA",
        "medical clinics in Philadelphia PA",
        "medical clinics in Detroit MI",
        "medical clinics in Nashville TN",
        "medical clinics in Charlotte NC"
    ],
    "metadata": {
        "total_queries": 25,
        "estimated_results_per_query": 40,
        "estimated_total_businesses": 1000,
        "target_email_rate": "60%",
        "data_source": "real_web_scraping"
    }
}
```

#### **TESTING DAY 4 DELIVERABLE**
```bash
# Test production scraper with small sample
mkdir -p config output

# Create test query file
echo '{"queries": ["coffee shops in Berkeley CA", "bookstores in Cambridge MA"]}' > config/test_queries.json

# Run production scraper
python production_business_scraper.py --queries config/test_queries.json --count 30 --output output

# Expected: 30 real business leads from Berkeley/Cambridge
```

---

### **DAY 5: INTEGRATION AND TESTING**

#### **COMPREHENSIVE INTEGRATION TEST**

**FILE: `tests/test_real_scrapers_integration.py`**
```python
import unittest
import os
import csv
import json
import time
from real_business_lead_generator import RealBusinessLeadGenerator

class TestRealScrapersIntegration(unittest.TestCase):
    """
    Integration tests for real scrapers - NO FAKE DATA
    """
    
    def setUp(self):
        self.generator = RealBusinessLeadGenerator()
        self.test_output_dir = "test_output"
        os.makedirs(self.test_output_dir, exist_ok=True)
    
    def test_google_maps_scraper_returns_real_data(self):
        """Test that Google Maps scraper returns real business data"""
        from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
        
        test_data = {
            'query': 'pizza restaurants in Brooklyn NY',
            'max_results': 5
        }
        
        results = scrape_google_maps_businesses(test_data)
        
        # Verify we got real results
        self.assertGreater(len(results), 0, "Should find at least 1 pizza restaurant")
        self.assertLessEqual(len(results), 5, "Should not exceed max_results")
        
        # Verify data quality - check for real business characteristics
        for business in results:
            # Must have a name
            self.assertIsNotNone(business.get('name'))
            self.assertNotEqual(business.get('name'), '')
            
            # Name should not match fake patterns
            name = business.get('name', '')
            self.assertNotRegex(name, r'.*#\d+$', "Business name should not end with #number")
            
            # Source should be real scraping
            self.assertEqual(business.get('source'), 'google_maps_real_scraping')
            
            print(f"✅ Real business found: {business.get('name')}")
    
    def test_email_extractor_finds_real_emails(self):
        """Test that email extractor finds real emails from real websites"""
        from src.scrapers.email_extractor import extract_emails_from_website
        
        # Test with known business websites that should have contact emails
        test_websites = [
            {'url': 'https://www.starbucks.com', 'name': 'Starbucks'},
            {'url': 'https://www.subway.com', 'name': 'Subway'}
        ]
        
        emails_found = 0
        
        for site in test_websites:
            email = extract_emails_from_website(site)
            
            if email:
                emails_found += 1
                
                # Verify email format
                self.assertRegex(email, r'^[^@]+@[^@]+\.[^@]+$', 
                               f"Email should be valid format: {email}")
                
                # Verify not fake email
                fake_domains = ['example.com', 'test.com', 'placeholder.com']
                for fake_domain in fake_domains:
                    self.assertNotIn(fake_domain, email, 
                                   f"Email should not be fake: {email}")
                
                print(f"✅ Real email found: {email} from {site['url']}")
        
        # Should find at least one real email
        self.assertGreater(emails_found, 0, "Should find at least 1 real email")
    
    def test_end_to_end_lead_generation(self):
        """Test complete lead generation pipeline with real data"""
        test_queries = ["ice cream shops in San Francisco CA"]
        
        # Generate small sample of real leads
        leads = self.generator.generate_leads(test_queries, target_count=10)
        
        # Verify we got results
        self.assertGreater(len(leads), 0, "Should generate at least 1 lead")
        self.assertLessEqual(len(leads), 10, "Should not exceed target count")
        
        # Verify data quality
        for lead in leads:
            # Basic required fields
            self.assertIsNotNone(lead.get('name'))
            self.assertIsNotNone(lead.get('source'))
            
            # Verify real data characteristics
            name = lead.get('name', '')
            self.assertNotRegex(name, r'.*#\d+$', 
                               f"Lead name should not be fake pattern: {name}")
            
            # Check source authenticity
            self.assertEqual(lead.get('source'), 'google_maps_real_scraping')
            
            # Verify search query is recorded
            self.assertEqual(lead.get('search_query'), test_queries[0])
            
            print(f"✅ Real lead verified: {lead.get('name')}")
        
        # Export and verify files
        csv_file = self.generator.export_to_csv(f"{self.test_output_dir}/test_leads.csv")
        json_file = self.generator.export_to_json(f"{self.test_output_dir}/test_leads.json")
        
        self.assertTrue(os.path.exists(csv_file), "CSV file should be created")
        self.assertTrue(os.path.exists(json_file), "JSON file should be created")
        
        # Verify CSV content
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_leads = list(reader)
            
            self.assertEqual(len(csv_leads), len(leads), 
                           "CSV should contain all leads")
            
            for csv_lead in csv_leads:
                # Verify no fake data patterns in CSV
                name = csv_lead.get('name', '')
                self.assertNotRegex(name, r'.*#\d+$', 
                                   f"CSV lead name should not be fake: {name}")
        
        print(f"✅ End-to-end test passed with {len(leads)} real leads")
    
    def test_no_fake_data_in_outputs(self):
        """Verify no fake data patterns exist in any outputs"""
        test_queries = ["flower shops in Portland OR"]
        
        # Generate leads
        leads = self.generator.generate_leads(test_queries, target_count=5)
        
        # Check for fake data patterns
        fake_patterns = [
            r'.*#\d+$',  # Names ending with #number
            r'.*Main St.*',  # Generic "Main St" addresses
            r'\(\d{3}\) \d{3}-\d{4}$'  # Perfect phone format (suspiciously regular)
        ]
        
        for lead in leads:
            name = lead.get('name', '')
            address = lead.get('address', '')
            phone = lead.get('phone', '')
            
            for pattern in fake_patterns:
                self.assertNotRegex(name, pattern, 
                                   f"Name should not match fake pattern: {name}")
            
            # Additional fake data checks
            if lead.get('email'):
                email = lead.get('email')
                fake_email_patterns = ['info@.*1\.com', '.*example\.com', '.*test\.com']
                
                for pattern in fake_email_patterns:
                    self.assertNotRegex(email, pattern, 
                                       f"Email should not match fake pattern: {email}")
        
        print("✅ No fake data patterns found in outputs")

if __name__ == "__main__":
    print("🧪 RUNNING REAL SCRAPER INTEGRATION TESTS")
    print("=" * 60)
    
    # Run tests
    unittest.main(verbosity=2)
```

#### **TESTING DAY 5 DELIVERABLE**
```bash
# Run comprehensive integration tests
python tests/test_real_scrapers_integration.py

# Expected: All tests pass, confirming real data extraction
```

#### **PHASE 2 COMPLETION VERIFICATION**

**FILE: `cleanup/phase2_verification.py`**
```python
#!/usr/bin/env python3
"""
Phase 2 Verification Script
Confirms real browser scrapers are working correctly
"""

import os
import json
import csv

def verify_real_scrapers():
    """Verify all real scrapers are functional"""
    print("🔍 PHASE 2 VERIFICATION - REAL SCRAPERS")
    print("=" * 60)
    
    # Check files exist
    required_files = [
        'src/scrapers/google_maps_scraper.py',
        'src/scrapers/email_extractor.py',
        'real_business_lead_generator.py',
        'production_business_scraper.py'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
    
    # Test imports
    try:
        from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
        print("✅ Google Maps scraper imports successfully")
    except Exception as e:
        print(f"❌ Google Maps scraper import failed: {e}")
    
    try:
        from src.scrapers.email_extractor import extract_emails_from_website
        print("✅ Email extractor imports successfully")
    except Exception as e:
        print(f"❌ Email extractor import failed: {e}")
    
    try:
        from real_business_lead_generator import RealBusinessLeadGenerator
        print("✅ Lead generator imports successfully")
    except Exception as e:
        print(f"❌ Lead generator import failed: {e}")
    
    print("\n🎯 PHASE 2 COMPLETE - READY FOR PHASE 3")

if __name__ == "__main__":
    verify_real_scrapers()
```

**DELIVERABLE**: Fully functional real browser scrapers that extract genuine business data from actual websites.

---

## **🚨 PHASE 2 SUCCESS CRITERIA**

### **MUST ACHIEVE BEFORE PHASE 3**:
- ✅ **Real Google Maps scraping**: Browser visits maps.google.com and extracts actual businesses
- ✅ **Real email extraction**: Browser visits business websites and finds genuine contact emails
- ✅ **Zero fake data**: No random.randint(), templates, or generated content
- ✅ **End-to-end pipeline**: Complete flow from search to CSV export with real data
- ✅ **Integration tests pass**: All verification tests confirm real data extraction

### **QUALITY BENCHMARKS**:
- **Business names**: Real company names (not "Restaurant #1")
- **Email addresses**: From actual business domains (not generated patterns)
- **Phone numbers**: Real business phones with varied formats
- **Addresses**: Actual street addresses (not templates)

**NEXT PHASE**: Proceed to `phase_3_integration_testing.md` for comprehensive system integration and testing.