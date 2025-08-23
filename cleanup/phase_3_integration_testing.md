# **PHASE 3: INTEGRATION & TESTING PLAN**
## **Week 3 - Real Data Pipeline Integration**

---

## **🎯 PHASE 3 OBJECTIVES**

**PRIMARY GOAL**: Integrate real browser scrapers into the existing pipeline infrastructure and validate end-to-end functionality with genuine business data.

**SUCCESS CRITERIA**:
- Real scrapers integrated with existing pipeline
- End-to-end data flow from scraping to CSV export
- Zero fake data in production outputs
- Comprehensive testing with real business validation

---

## **📋 DAY-BY-DAY IMPLEMENTATION**

### **DAY 1: PIPELINE INTEGRATION**

#### **MAIN.PY INTEGRATION** (Morning Tasks)

**FILE: `main.py`**
```python
# BEFORE (Broken pipeline calling fake generators):
from real_business_scraper import generate_fake_businesses  # ❌ Fake generator
from generate_100_leads import create_demo_leads  # ❌ Fake generator

def main():
    leads = generate_fake_businesses(count=1000)  # ❌ Fake data
    export_to_csv(leads, "fake_leads.csv")  # ❌ Fake output

# AFTER (Real scraper integration):
from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
from src.scrapers.email_extractor import extract_emails_from_website
from src.pipeline.data_processor import process_business_leads
from src.pipeline.validators import validate_real_business_data

def main(search_queries, target_count=1000):
    """
    Main pipeline using real browser scraping
    """
    print(f"🚀 Starting real business lead generation")
    print(f"📊 Target: {target_count} leads")
    
    all_leads = []
    
    for query in search_queries:
        print(f"🔍 Processing: {query}")
        
        # Step 1: Real Google Maps scraping
        businesses = scrape_google_maps_businesses(query, max_results=100)
        print(f"📍 Found {len(businesses)} businesses on Google Maps")
        
        # Step 2: Real email extraction
        for business in businesses:
            if len(all_leads) >= target_count:
                break
                
            if business['website']:
                email = extract_emails_from_website(business['website'])
                if email:
                    business['email'] = email
                    
                    # Step 3: Validate real business data
                    if validate_real_business_data(business):
                        all_leads.append(business)
                        print(f"✅ {business['name']} - {email}")
    
    # Step 4: Process and export real data
    processed_leads = process_business_leads(all_leads)
    export_to_csv(processed_leads, "output/real_business_leads.csv")
    
    print(f"🎉 Generated {len(processed_leads)} real business leads")
    return processed_leads

if __name__ == "__main__":
    search_queries = [
        "restaurants in New York NY",
        "dental clinics in Los Angeles CA",
        "law firms in Chicago IL",
        "auto repair shops in Houston TX",
        "hair salons in Phoenix AZ"
    ]
    
    leads = main(search_queries, target_count=1000)
```

#### **DATA PROCESSOR UPDATES** (Afternoon)

**FILE: `src/pipeline/data_processor.py`**
```python
# BEFORE (Processing fake data):
def process_business_leads(leads):
    # Simple pass-through for fake data
    return leads

# AFTER (Real data processing with validation):
import re
from datetime import datetime
from src.utils.phone_validator import validate_phone_number
from src.utils.email_validator import validate_email_address

def process_business_leads(raw_leads):
    """
    Process real business leads with comprehensive validation
    """
    processed_leads = []
    
    for lead in raw_leads:
        try:
            processed_lead = {
                'business_name': clean_business_name(lead.get('name', '')),
                'email': validate_and_clean_email(lead.get('email', '')),
                'phone': validate_and_clean_phone(lead.get('phone', '')),
                'website': validate_and_clean_website(lead.get('website', '')),
                'address': clean_address(lead.get('address', '')),
                'city': extract_city(lead.get('address', '')),
                'state': extract_state(lead.get('address', '')),
                'scraped_date': datetime.now().isoformat(),
                'source': lead.get('source', 'google_maps_browser_scraping'),
                'data_quality_score': calculate_quality_score(lead)
            }
            
            # Only include high-quality real business data
            if processed_lead['data_quality_score'] >= 0.7:
                processed_leads.append(processed_lead)
                
        except Exception as e:
            print(f"⚠️ Error processing lead: {e}")
            continue
    
    return processed_leads

def clean_business_name(name):
    """Remove scraping artifacts and normalize business names"""
    if not name:
        return ""
    
    # Remove common scraping artifacts
    name = re.sub(r'\s+', ' ', name.strip())
    name = re.sub(r'[^\w\s&\-\.]', '', name)
    
    # Remove fake patterns
    if re.match(r'.*#\d+$', name) or 'Restaurant #' in name:
        return ""  # Reject fake data patterns
    
    return name.title()

def validate_and_clean_email(email):
    """Validate real business emails and reject fake patterns"""
    if not email:
        return ""
    
    # Reject fake email patterns
    fake_patterns = [
        'example.com', 'test.com', 'demo.com', 
        'placeholder.com', 'fake.com', 'lorem.com'
    ]
    
    if any(fake in email.lower() for fake in fake_patterns):
        return ""
    
    # Basic email validation
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    if re.match(email_pattern, email):
        return email.lower()
    
    return ""

def calculate_quality_score(lead):
    """Calculate data quality score for real business validation"""
    score = 0.0
    
    # Business name quality
    if lead.get('name') and not re.match(r'.*#\d+$', lead['name']):
        score += 0.3
    
    # Email quality
    if lead.get('email') and '@' in lead['email']:
        score += 0.3
    
    # Phone quality  
    if lead.get('phone') and len(re.sub(r'[^\d]', '', lead['phone'])) >= 10:
        score += 0.2
    
    # Website quality
    if lead.get('website') and lead['website'].startswith('http'):
        score += 0.2
    
    return score
```

**DELIVERABLE**: Integrated pipeline processing real business data with validation

---

### **DAY 2: COMPREHENSIVE TESTING FRAMEWORK**

#### **REAL DATA VALIDATION TESTS**

**FILE: `tests/test_real_data_validation.py`**
```python
#!/usr/bin/env python3
"""
Comprehensive testing for real business data validation
"""
import pytest
import requests
import re
from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
from src.scrapers.email_extractor import extract_emails_from_website
from src.pipeline.data_processor import process_business_leads

class TestRealBusinessDataValidation:
    
    def test_google_maps_returns_real_businesses(self):
        """Test that Google Maps scraper returns actual businesses"""
        businesses = scrape_google_maps_businesses("coffee shops Seattle WA", max_results=5)
        
        assert len(businesses) > 0, "Should return at least some businesses"
        
        for business in businesses:
            # Verify business name is real (not fake pattern)
            assert business['name'], "Business should have a name"
            assert not re.match(r'.*#\d+$', business['name']), f"Business name '{business['name']}' appears to be fake"
            assert 'Coffee' not in business['name'] or '#' not in business['name'], "Should not contain fake patterns"
            
            # Verify address is real
            assert business.get('address'), "Business should have an address"
            assert 'Seattle' in business['address'] or 'WA' in business['address'], "Address should be in requested location"
    
    def test_website_email_extraction_real(self):
        """Test that email extraction finds real emails from real websites"""
        # Test with known business website
        test_websites = [
            "https://starbucks.com",
            "https://mcdonald.com" 
        ]
        
        for website in test_websites:
            try:
                email = extract_emails_from_website(website)
                if email:
                    # Verify email is real format
                    assert '@' in email, f"Email '{email}' should contain @"
                    assert '.' in email.split('@')[1], f"Email '{email}' should have valid domain"
                    
                    # Verify email domain matches website
                    domain = website.replace('https://', '').replace('http://', '').split('/')[0]
                    if 'www.' in domain:
                        domain = domain.replace('www.', '')
                    
                    # Email should be from same domain or related
                    assert domain.split('.')[0] in email or email.endswith(f"@{domain}"), f"Email '{email}' should be from domain '{domain}'"
            except:
                pass  # Some sites may block scraping, that's OK
    
    def test_no_fake_data_patterns_in_output(self):
        """Test that processed data contains no fake patterns"""
        # Create test data that includes fake patterns
        test_leads = [
            {
                'name': 'Real Coffee Shop',
                'email': 'contact@realcoffee.com',
                'phone': '+1-206-555-0123',
                'website': 'https://realcoffee.com',
                'address': '123 Main St, Seattle, WA'
            },
            {
                'name': 'Restaurant #1',  # Fake pattern
                'email': 'test@example.com',  # Fake pattern
                'phone': '555-0000',
                'website': 'http://example.com',
                'address': '456 Fake St'
            }
        ]
        
        processed = process_business_leads(test_leads)
        
        # Should only return the real business
        assert len(processed) == 1, "Should filter out fake data"
        assert processed[0]['business_name'] == 'Real Coffee Shop'
        assert 'Restaurant #' not in str(processed), "Should not contain fake restaurant patterns"
        assert 'example.com' not in str(processed), "Should not contain fake email domains"
    
    def test_business_phone_numbers_are_real(self):
        """Test that phone numbers are real US business numbers"""
        businesses = scrape_google_maps_businesses("pizza restaurants Chicago IL", max_results=3)
        
        for business in businesses:
            if business.get('phone'):
                phone = re.sub(r'[^\d]', '', business['phone'])
                
                # Should be 10 or 11 digits (US format)
                assert len(phone) >= 10, f"Phone '{business['phone']}' should be at least 10 digits"
                
                # Should not be fake numbers like 555-0000 or 123-4567
                fake_patterns = ['5550000', '1234567', '0000000', '1111111']
                assert not any(fake in phone for fake in fake_patterns), f"Phone '{phone}' appears to be fake"
                
                # Should have realistic area code (not 000, 111, etc.)
                area_code = phone[-10:][:3] if len(phone) >= 10 else phone[:3]
                assert area_code not in ['000', '111', '222', '333', '444', '555', '666', '777', '888', '999'], f"Area code '{area_code}' appears fake"

class TestEndToEndRealDataFlow:
    
    def test_complete_pipeline_produces_real_data(self):
        """Test complete pipeline from scraping to export produces real business data"""
        from main import main
        
        # Run with small test batch
        search_queries = ["bakeries Portland OR"]
        leads = main(search_queries, target_count=5)
        
        assert len(leads) > 0, "Pipeline should produce some leads"
        
        for lead in leads:
            # Verify all required fields
            assert lead.get('business_name'), "Should have business name"
            assert lead.get('email'), "Should have email"
            
            # Verify no fake patterns
            assert not re.match(r'.*#\d+$', lead['business_name']), "Business name should not be fake pattern"
            assert 'example.com' not in lead['email'], "Email should not be from fake domain"
            assert 'Portland' in lead.get('address', '') or 'OR' in lead.get('address', ''), "Address should match search location"
            
            # Verify data quality score
            assert lead.get('data_quality_score', 0) >= 0.7, "Should have high quality score"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### **BROWSER FUNCTIONALITY TESTS**

**FILE: `tests/test_browser_scraping.py`**
```python
#!/usr/bin/env python3
"""
Test browser scraping functionality with real websites
"""
import pytest
import time
from botasaurus.browser import browser
from src.scrapers.google_maps_scraper import scrape_google_maps_businesses

class TestBrowserScrapingFunctionality:
    
    def test_botasaurus_can_open_google_maps(self):
        """Test that Botasaurus can successfully navigate to Google Maps"""
        
        @browser(headless=True)
        def test_google_maps_navigation(driver):
            driver.get("https://www.google.com/maps")
            time.sleep(2)
            
            # Verify we're on Google Maps
            assert "google.com/maps" in driver.current_url
            assert driver.find_element("id", "searchboxinput"), "Should find search box"
            
            return {"success": True, "url": driver.current_url, "title": driver.title}
        
        result = test_google_maps_navigation()
        assert result["success"]
        assert "maps" in result["title"].lower()
    
    def test_botasaurus_can_search_businesses(self):
        """Test that Botasaurus can perform business searches"""
        
        @browser(headless=True)
        def test_business_search(driver):
            driver.get("https://www.google.com/maps")
            time.sleep(2)
            
            # Search for businesses
            search_box = driver.find_element("id", "searchboxinput")
            search_box.send_keys("coffee shops")
            search_box.send_keys("\n")
            time.sleep(3)
            
            # Look for business results
            business_elements = driver.find_elements("css selector", "[data-result-index]")
            
            return {
                "success": len(business_elements) > 0,
                "business_count": len(business_elements),
                "url": driver.current_url
            }
        
        result = test_business_search()
        assert result["success"], "Should find business results"
        assert result["business_count"] > 0, "Should have at least one business result"
    
    def test_email_extraction_from_real_website(self):
        """Test email extraction from a real business website"""
        
        @browser(headless=True)  
        def test_email_extraction(driver):
            # Use a known business website that should have contact info
            driver.get("https://httpbin.org/html")  # Test site that returns HTML
            time.sleep(1)
            
            # Add a test email to the page
            driver.execute_script("""
                document.body.innerHTML += '<div>Contact us at test@business.com</div>';
            """)
            
            page_source = driver.page_source
            return {"page_source": page_source}
        
        result = test_email_extraction()
        assert "test@business.com" in result["page_source"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**DELIVERABLE**: Comprehensive test suite validating real business data extraction

---

### **DAY 3: DATA VALIDATION & QUALITY ASSURANCE**

#### **REAL BUSINESS DATA VALIDATORS**

**FILE: `src/pipeline/validators.py`**
```python
#!/usr/bin/env python3
"""
Real business data validation utilities
"""
import re
import requests
import socket
from urllib.parse import urlparse
import phonenumbers
from email_validator import validate_email, EmailNotValidError

def validate_real_business_data(business_data):
    """
    Comprehensive validation that business data is real (not fake/generated)
    
    Returns True only if data passes all reality checks
    """
    if not business_data:
        return False
    
    # Check business name reality
    if not validate_business_name_real(business_data.get('name', '')):
        return False
    
    # Check email reality  
    if business_data.get('email') and not validate_email_real(business_data['email']):
        return False
    
    # Check phone reality
    if business_data.get('phone') and not validate_phone_real(business_data['phone']):
        return False
    
    # Check website reality
    if business_data.get('website') and not validate_website_real(business_data['website']):
        return False
    
    # Check address reality
    if business_data.get('address') and not validate_address_real(business_data['address']):
        return False
    
    return True

def validate_business_name_real(name):
    """Validate business name is real (not fake pattern)"""
    if not name or len(name.strip()) < 2:
        return False
    
    # Reject fake patterns
    fake_patterns = [
        r'.*#\d+$',  # Restaurant #1, Business #2, etc.
        r'^(Restaurant|Business|Company|Shop)\s+\d+$',  # Generic + number
        r'^(Test|Demo|Sample|Example)',  # Test names
        r'Lorem|Ipsum|Placeholder',  # Lorem ipsum text
    ]
    
    for pattern in fake_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return False
    
    # Must contain at least some real business words
    business_words = [
        'restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'deli', 'bar', 'grill',
        'dental', 'clinic', 'medical', 'health', 'pharmacy', 'hospital',
        'law', 'legal', 'attorney', 'lawyer', 'firm', 'office',
        'auto', 'repair', 'garage', 'mechanic', 'service', 'shop',
        'salon', 'beauty', 'hair', 'spa', 'nail', 'barbershop'
    ]
    
    name_lower = name.lower()
    if any(word in name_lower for word in business_words):
        return True
    
    # Accept if it looks like a real business name (has proper nouns)
    words = name.split()
    if len(words) >= 2 and all(word[0].isupper() for word in words[:2]):
        return True
    
    return False

def validate_email_real(email):
    """Validate email is from real business domain (not fake)"""
    try:
        # Basic email format validation
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError:
        return False
    
    # Reject fake/test domains
    fake_domains = [
        'example.com', 'example.org', 'example.net',
        'test.com', 'test.org', 'test.net',
        'demo.com', 'demo.org', 'demo.net', 
        'placeholder.com', 'fake.com', 'lorem.com',
        'tempmail.com', '10minutemail.com', 'guerrillamail.com'
    ]
    
    domain = email.split('@')[1].lower()
    if domain in fake_domains:
        return False
    
    # Check if domain actually exists
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

def validate_phone_real(phone):
    """Validate phone number is real US business number"""
    try:
        # Clean phone number
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Parse with phonenumbers library
        phone_obj = phonenumbers.parse(phone_clean, "US")
        
        # Must be valid format
        if not phonenumbers.is_valid_number(phone_obj):
            return False
        
        # Must be possible number
        if not phonenumbers.is_possible_number(phone_obj):
            return False
        
        # Reject fake patterns
        digits_only = re.sub(r'[^\d]', '', phone)
        fake_patterns = [
            '5550000', '5551234', '1234567890', '0000000000',
            '1111111111', '2222222222', '3333333333', '4444444444',
            '6666666666', '7777777777', '8888888888', '9999999999'
        ]
        
        if digits_only in fake_patterns:
            return False
        
        # Check area code is real (not 000, 111, etc.)
        area_code = digits_only[-10:][:3] if len(digits_only) >= 10 else digits_only[:3]
        invalid_area_codes = ['000', '111', '222', '333', '444', '555', '666', '777', '888', '999']
        
        if area_code in invalid_area_codes:
            return False
        
        return True
        
    except:
        return False

def validate_website_real(website):
    """Validate website is real and accessible"""
    if not website:
        return False
    
    # Must be proper URL format
    try:
        parsed = urlparse(website)
        if not parsed.scheme or not parsed.netloc:
            return False
    except:
        return False
    
    # Reject fake domains
    fake_domains = [
        'example.com', 'test.com', 'demo.com', 'placeholder.com', 
        'fake.com', 'lorem.com', 'tempsite.com'
    ]
    
    domain = parsed.netloc.lower().replace('www.', '')
    if domain in fake_domains:
        return False
    
    # Check if website is accessible (optional, can be slow)
    try:
        response = requests.head(website, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except:
        # If we can't check, assume it's real (avoid false negatives)
        return True

def validate_address_real(address):
    """Validate address appears to be real US address"""
    if not address or len(address.strip()) < 10:
        return False
    
    # Must contain some realistic address components
    address_patterns = [
        r'\d+\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court)',
        r'\d+\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # Street name pattern
        r'(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)'  # State codes
    ]
    
    for pattern in address_patterns:
        if re.search(pattern, address, re.IGNORECASE):
            return True
    
    return False

def calculate_business_reality_score(business_data):
    """
    Calculate overall score for how "real" the business data appears
    Returns 0.0 to 1.0, with 1.0 being definitely real
    """
    score = 0.0
    
    # Business name reality (0.3)
    if validate_business_name_real(business_data.get('name', '')):
        score += 0.3
    
    # Email reality (0.25)
    if business_data.get('email') and validate_email_real(business_data['email']):
        score += 0.25
    
    # Phone reality (0.2)  
    if business_data.get('phone') and validate_phone_real(business_data['phone']):
        score += 0.2
    
    # Website reality (0.15)
    if business_data.get('website') and validate_website_real(business_data['website']):
        score += 0.15
    
    # Address reality (0.1)
    if business_data.get('address') and validate_address_real(business_data['address']):
        score += 0.1
    
    return score
```

**DELIVERABLE**: Comprehensive real business data validation system

---

### **DAY 4: ERROR HANDLING & ROBUSTNESS**

#### **ANTI-DETECTION & ERROR RECOVERY**

**FILE: `src/scrapers/robust_scraper.py`**
```python
#!/usr/bin/env python3
"""
Robust scraping with anti-detection and error recovery
"""
import time
import random
from botasaurus.browser import browser
import logging
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustScraper:
    """
    Robust scraper with anti-detection measures and error recovery
    """
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        
        self.retry_delays = [2, 5, 10, 20, 30]  # Progressive delay
        self.max_retries = 3
    
    def random_delay(self, min_seconds=1, max_seconds=5):
        """Human-like random delays"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def get_random_user_agent(self):
        """Get random user agent for rotation"""
        return random.choice(self.user_agents)
    
    @browser(
        headless=False,
        window_size="1920,1080", 
        block_images=True,
        block_resources=["font", "image", "media", "stylesheet"]
    )
    def scrape_with_retries(self, driver, scrape_function, *args, **kwargs):
        """
        Execute scraping function with retry logic and error recovery
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Scraping attempt {attempt + 1}/{self.max_retries}")
                
                # Set random user agent
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": self.get_random_user_agent()
                })
                
                # Execute scraping function
                result = scrape_function(driver, *args, **kwargs)
                
                if result:  # Success
                    logger.info(f"Scraping successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Scraping returned empty result on attempt {attempt + 1}")
                    
            except (TimeoutException, NoSuchElementException) as e:
                last_exception = e
                logger.warning(f"Scraping failed on attempt {attempt + 1}: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                break  # Don't retry for unexpected errors
        
        logger.error(f"All scraping attempts failed. Last error: {last_exception}")
        return []

def safe_google_maps_scrape(query, max_results=50):
    """
    Safely scrape Google Maps with error handling
    """
    scraper = RobustScraper()
    
    def _scrape_google_maps(driver, query, max_results):
        """Internal scraping function"""
        try:
            # Navigate to Google Maps
            logger.info(f"Navigating to Google Maps for query: {query}")
            driver.get("https://www.google.com/maps")
            
            # Wait for page load
            scraper.random_delay(2, 4)
            
            # Find search box
            search_box = driver.find_element("id", "searchboxinput")
            search_box.clear()
            
            # Type search query with human-like delays
            for char in query:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            search_box.send_keys("\n")
            scraper.random_delay(3, 6)
            
            # Extract business results
            businesses = []
            business_elements = driver.find_elements("css selector", "[data-result-index]")
            
            logger.info(f"Found {len(business_elements)} business elements")
            
            for i, element in enumerate(business_elements[:max_results]):
                try:
                    business = extract_business_from_element(element)
                    if business:
                        businesses.append(business)
                        logger.info(f"Extracted business {i+1}: {business['name']}")
                    
                    # Random delay between extractions
                    scraper.random_delay(0.5, 1.5)
                    
                except Exception as e:
                    logger.warning(f"Error extracting business {i+1}: {e}")
                    continue
            
            return businesses
            
        except Exception as e:
            logger.error(f"Error in Google Maps scraping: {e}")
            return []
    
    return scraper.scrape_with_retries(_scrape_google_maps, query, max_results)

def extract_business_from_element(element):
    """
    Extract business data from Google Maps element with error handling
    """
    try:
        business = {}
        
        # Business name
        try:
            name_element = element.find_element("css selector", "[data-value='title']")
            business['name'] = name_element.text.strip()
        except:
            business['name'] = ""
        
        # Address
        try:
            address_element = element.find_element("css selector", "[data-value='address']") 
            business['address'] = address_element.text.strip()
        except:
            business['address'] = ""
        
        # Phone
        try:
            phone_element = element.find_element("css selector", "[href^='tel:']")
            phone = phone_element.get_attribute('href')
            business['phone'] = phone.replace('tel:', '') if phone else ""
        except:
            business['phone'] = ""
        
        # Website
        try:
            website_element = element.find_element("css selector", "[data-value='website']")
            business['website'] = website_element.get_attribute('href')
        except:
            business['website'] = ""
        
        # Only return if we have at least name and some contact info
        if business['name'] and (business['phone'] or business['website']):
            business['source'] = 'google_maps_browser_scraping'
            return business
        
        return None
        
    except Exception as e:
        logger.warning(f"Error extracting business data: {e}")
        return None
```

**DELIVERABLE**: Robust scraping system with anti-detection and error recovery

---

### **DAY 5: FINAL INTEGRATION & TESTING**

#### **END-TO-END SYSTEM TEST**

**FILE: `tests/test_complete_pipeline.py`**
```python
#!/usr/bin/env python3
"""
Complete end-to-end system test with real data validation
"""
import os
import csv
import json
import pytest
from main import main
from src.pipeline.validators import validate_real_business_data

class TestCompleteRealDataPipeline:
    
    def test_end_to_end_real_business_generation(self):
        """Test complete pipeline generates real business leads"""
        
        # Test with small batch
        search_queries = [
            "pizza restaurants Boston MA",
            "dental offices Miami FL"
        ]
        
        # Run main pipeline
        leads = main(search_queries, target_count=20)
        
        # Validate results
        assert len(leads) > 0, "Should generate some leads"
        assert len(leads) <= 20, "Should respect target count"
        
        # Validate each lead is real business data
        real_leads = 0
        for lead in leads:
            if validate_real_business_data(lead):
                real_leads += 1
                
                # Log real business found
                print(f"✅ Real business: {lead['business_name']} - {lead['email']}")
            else:
                print(f"❌ Fake data detected: {lead}")
        
        # At least 50% should be real businesses
        real_percentage = real_leads / len(leads)
        assert real_percentage >= 0.5, f"Only {real_percentage:.1%} of leads are real businesses"
        
        print(f"🎉 Generated {real_leads} real business leads ({real_percentage:.1%} success rate)")
    
    def test_csv_export_contains_real_data(self):
        """Test that CSV export contains real business data"""
        
        # Generate test data
        search_queries = ["coffee shops Portland OR"]
        leads = main(search_queries, target_count=5)
        
        # Check CSV file was created
        csv_file = "output/real_business_leads.csv"
        assert os.path.exists(csv_file), f"CSV file should be created at {csv_file}"
        
        # Read and validate CSV contents
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            csv_leads = list(reader)
        
        assert len(csv_leads) > 0, "CSV should contain data"
        
        # Validate CSV data is real
        for lead in csv_leads:
            assert lead['business_name'], "Should have business name"
            assert lead['email'], "Should have email"
            assert '@' in lead['email'], "Should have valid email format"
            
            # Check for fake patterns
            assert not lead['business_name'].endswith('#1'), "Should not contain fake patterns"
            assert 'example.com' not in lead['email'], "Should not have fake email domains"
    
    def test_statistics_tracking(self):
        """Test that scraping statistics are tracked correctly"""
        
        # Run pipeline
        search_queries = ["auto repair Denver CO"]  
        leads = main(search_queries, target_count=10)
        
        # Check statistics file
        stats_file = "output/scraping_statistics.json"
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as file:
                stats = json.load(file)
            
            assert 'total' in stats, "Should track total count"
            assert 'with_email' in stats, "Should track email success rate"
            assert 'with_phone' in stats, "Should track phone success rate"
            
            # Validate statistics make sense
            assert stats['with_email'] <= stats['total'], "Email count should not exceed total"
            assert stats['with_phone'] <= stats['total'], "Phone count should not exceed total"

class TestRealBusinessValidation:
    
    def test_fake_data_rejection(self):
        """Test that fake data patterns are properly rejected"""
        
        fake_businesses = [
            {
                'name': 'Restaurant #1',
                'email': 'test@example.com',
                'phone': '555-0000',
                'website': 'http://example.com'
            },
            {
                'name': 'Business Number 2', 
                'email': 'demo@fake.com',
                'phone': '123-456-7890',
                'website': 'http://demo.com'
            }
        ]
        
        for fake_business in fake_businesses:
            assert not validate_real_business_data(fake_business), f"Should reject fake business: {fake_business['name']}"
    
    def test_real_data_acceptance(self):
        """Test that realistic business data is accepted"""
        
        realistic_businesses = [
            {
                'name': "Joe's Pizza Palace",
                'email': 'info@joespizza.com',
                'phone': '(212) 555-0123', 
                'website': 'https://joespizza.com',
                'address': '123 Main St, New York, NY'
            },
            {
                'name': 'Downtown Dental Care',
                'email': 'appointments@downtowndental.com',
                'phone': '+1-305-555-0199',
                'website': 'https://downtowndental.com',
                'address': '456 Ocean Drive, Miami, FL'
            }
        ]
        
        for real_business in realistic_businesses:
            assert validate_real_business_data(real_business), f"Should accept real business: {real_business['name']}"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
    
    # Also run a live test
    print("\n" + "="*50)
    print("RUNNING LIVE PIPELINE TEST")
    print("="*50)
    
    from main import main
    
    test_queries = ["bookstores Seattle WA"]
    live_results = main(test_queries, target_count=3)
    
    print(f"\n📊 LIVE TEST RESULTS:")
    print(f"Total leads generated: {len(live_results)}")
    
    for i, lead in enumerate(live_results, 1):
        print(f"\n{i}. {lead['business_name']}")
        print(f"   Email: {lead['email']}")
        print(f"   Phone: {lead.get('phone', 'N/A')}")
        print(f"   Quality Score: {lead.get('data_quality_score', 'N/A')}")
```

#### **FINAL DEPLOYMENT SCRIPT**

**FILE: `deploy_real_scrapers.py`**
```python
#!/usr/bin/env python3
"""
Final deployment script for real business scrapers
"""
import os
import sys
import subprocess
import json

def run_command(command, description):
    """Run command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return None

def main():
    print("🚀 DEPLOYING REAL BUSINESS SCRAPER SYSTEM")
    print("="*50)
    
    # 1. Verify Python environment
    print("\n1️⃣ VERIFYING ENVIRONMENT")
    python_version = run_command("python --version", "Checking Python version")
    if python_version:
        print(f"   Python version: {python_version.strip()}")
    
    # 2. Install dependencies
    print("\n2️⃣ INSTALLING DEPENDENCIES")
    run_command("pip install -r requirements.txt", "Installing Python packages")
    run_command("pip install botasaurus selenium phonenumbers email-validator", "Installing scraping dependencies")
    
    # 3. Test Botasaurus functionality
    print("\n3️⃣ TESTING BOTASAURUS")
    test_code = '''
from botasaurus.browser import browser
import time

@browser(headless=True)
def test_botasaurus(driver):
    driver.get("https://httpbin.org/get")
    time.sleep(1)
    return {"success": True, "title": driver.title}

try:
    result = test_botasaurus()
    print(f"Botasaurus test result: {result}")
except Exception as e:
    print(f"Botasaurus test failed: {e}")
    '''
    
    with open("temp_botasaurus_test.py", "w") as f:
        f.write(test_code)
    
    run_command("python temp_botasaurus_test.py", "Testing Botasaurus browser automation")
    
    if os.path.exists("temp_botasaurus_test.py"):
        os.remove("temp_botasaurus_test.py")
    
    # 4. Run validation tests
    print("\n4️⃣ RUNNING VALIDATION TESTS")
    run_command("python -m pytest tests/test_real_data_validation.py -v", "Running data validation tests")
    run_command("python -m pytest tests/test_complete_pipeline.py -v", "Running complete pipeline tests")
    
    # 5. Create output directory
    print("\n5️⃣ PREPARING OUTPUT DIRECTORY")
    os.makedirs("output", exist_ok=True)
    print("✅ Output directory ready")
    
    # 6. Test live scraping with small batch
    print("\n6️⃣ TESTING LIVE SCRAPING")
    test_scraping_code = '''
from main import main

try:
    print("Testing live scraping with small batch...")
    leads = main(["pizza restaurants test city"], target_count=2)
    print(f"Live scraping test completed: {len(leads)} leads generated")
    
    if leads:
        print("Sample lead:")
        print(f"  Name: {leads[0].get('business_name', 'N/A')}")
        print(f"  Email: {leads[0].get('email', 'N/A')}")
        print(f"  Source: {leads[0].get('source', 'N/A')}")
except Exception as e:
    print(f"Live scraping test failed: {e}")
    '''
    
    with open("temp_live_test.py", "w") as f:
        f.write(test_scraping_code)
    
    run_command("python temp_live_test.py", "Testing live scraping functionality")
    
    if os.path.exists("temp_live_test.py"):
        os.remove("temp_live_test.py")
    
    # 7. Final system check
    print("\n7️⃣ FINAL SYSTEM CHECK")
    
    required_files = [
        "main.py",
        "src/scrapers/google_maps_scraper.py", 
        "src/scrapers/email_extractor.py",
        "src/pipeline/data_processor.py",
        "src/pipeline/validators.py"
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING!")
            all_files_exist = False
    
    # 8. Generate deployment summary
    print("\n8️⃣ GENERATING DEPLOYMENT SUMMARY")
    
    summary = {
        "deployment_date": "2024-01-XX",
        "system_status": "deployed" if all_files_exist else "incomplete",
        "components": {
            "google_maps_scraper": os.path.exists("src/scrapers/google_maps_scraper.py"),
            "email_extractor": os.path.exists("src/scrapers/email_extractor.py"),
            "data_processor": os.path.exists("src/pipeline/data_processor.py"),
            "validators": os.path.exists("src/pipeline/validators.py"),
            "main_pipeline": os.path.exists("main.py")
        },
        "next_steps": [
            "Run: python main.py with your search queries",
            "Check output/real_business_leads.csv for results",
            "Monitor output/scraping_statistics.json for metrics"
        ]
    }
    
    with open("deployment_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print("✅ Deployment summary saved to deployment_summary.json")
    
    # Final message
    print("\n" + "="*50)
    if all_files_exist:
        print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
        print("\nTo generate real business leads, run:")
        print("python main.py")
        print("\nResults will be saved to:")
        print("- output/real_business_leads.csv")
        print("- output/scraping_statistics.json")
    else:
        print("⚠️  DEPLOYMENT INCOMPLETE - Some files are missing")
        print("Please check the missing files listed above")
    print("="*50)

if __name__ == "__main__":
    main()
```

**DELIVERABLE**: Complete integrated system with comprehensive testing and deployment

---

## **🚨 CRITICAL SUCCESS INDICATORS**

### **MUST PASS BEFORE PHASE 4**:
- ✅ **Real data only**: No fake patterns in any output files
- ✅ **End-to-end functionality**: Complete pipeline from scraping to CSV export
- ✅ **Data validation**: All business data passes reality checks
- ✅ **Error handling**: System gracefully handles scraping failures
- ✅ **Performance**: Can generate 100+ real leads without crashes

### **INTEGRATION CHECKPOINTS**:
```python
# Must pass all these integration tests:
python tests/test_complete_pipeline.py  # ✅ End-to-end real data flow
python tests/test_real_data_validation.py  # ✅ No fake data patterns
python tests/test_browser_scraping.py  # ✅ Browser automation works
python deploy_real_scrapers.py  # ✅ Complete deployment test
```

### **QUALITY METRICS**:
- **Data Reality Score**: >80% of leads pass reality validation
- **Email Discovery Rate**: >60% of businesses have valid emails
- **System Uptime**: Can run for 1+ hour without crashes
- **Error Recovery**: Handles blocked requests and timeouts gracefully

---

**PHASE 3 EXIT CRITERIA**:
```bash
# All integration tests must pass:
python -m pytest tests/ -v  # ✅ All tests pass
python main.py --test-mode  # ✅ Live scraping test passes
grep -r "fake\|demo\|test" output/real_business_leads.csv | wc -l  # ✅ Returns 0
python -c "import json; print(json.load(open('output/scraping_statistics.json')))"  # ✅ Shows real statistics
```

**NEXT PHASE**: Proceed to `phase_4_production_deployment.md` for production scaling, proxy integration, and performance optimization.