"""
Google Maps Scraper Core Implementation
TASK-F004: Google Maps search automation with infinite scroll and business extraction

Provides enterprise-grade Google Maps scraping with:
- Stealth navigation and anti-detection
- Infinite scroll handling with human behavior
- Business listing data extraction
- Geographic expansion capabilities
"""

import time
import random
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_plus

from botasaurus import *
from botasaurus.browser import Driver, Wait

from .engine import BotasaurusEngine, SessionConfig
from .models import BusinessLead, ContactInfo, Address, LeadStatus
from .anti_detection import HumanBehaviorSimulator


@dataclass 
class GoogleMapsConfig:
    """Configuration for Google Maps scraping"""
    search_query: str
    location: Optional[str] = None
    max_results: int = 500
    enable_geographic_expansion: bool = True
    expansion_radius_km: int = 10
    scroll_pause_time: Tuple[float, float] = (2.0, 4.0)
    human_behavior: bool = True
    extract_reviews: bool = False
    extract_hours: bool = True
    extract_photos: bool = False
    

class GoogleMapsScraper:
    """
    Advanced Google Maps scraper with anti-detection and infinite scroll
    
    Features:
    - Stealth navigation to avoid detection
    - Human-like scrolling and interaction patterns
    - Comprehensive business data extraction
    - Geographic query expansion for better coverage
    - Automatic retry and error recovery
    """
    
    BASE_URL = "https://www.google.com/maps"
    
    def __init__(self, engine: Optional[BotasaurusEngine] = None):
        """Initialize Google Maps scraper"""
        self.engine = engine or BotasaurusEngine()
        self.behavior_simulator = HumanBehaviorSimulator()
        self.extracted_businesses = []
        self.seen_place_ids = set()
        self.metrics = {
            'searches_performed': 0,
            'businesses_found': 0,
            'scroll_iterations': 0,
            'extraction_errors': 0,
            'geographic_expansions': 0
        }
        
    def search(self, config: GoogleMapsConfig) -> List[BusinessLead]:
        """
        Perform Google Maps search and extract business listings
        
        Args:
            config: Search configuration
            
        Returns:
            List of extracted BusinessLead objects
        """
        self.extracted_businesses.clear()
        self.seen_place_ids.clear()
        
        # Build search URL
        search_url = self._build_search_url(config.search_query, config.location)
        
        print(f"Starting Google Maps search: {config.search_query}")
        print(f"Location: {config.location or 'Current location'}")
        print(f"Target results: {config.max_results}")
        
        # Navigate to Google Maps
        if not self.engine.navigate_with_stealth(search_url, wait_time=5):
            print("Failed to navigate to Google Maps")
            return []
            
        # Wait for results to load
        self._wait_for_results()
        
        # Perform search with infinite scroll
        self._extract_with_infinite_scroll(config)
        
        # Geographic expansion if enabled
        if config.enable_geographic_expansion and len(self.extracted_businesses) < config.max_results:
            self._perform_geographic_expansion(config)
            
        # Convert to BusinessLead objects
        leads = self._convert_to_leads(self.extracted_businesses)
        
        print(f"\nExtraction complete!")
        print(f"Total businesses found: {len(leads)}")
        print(f"Metrics: {json.dumps(self.metrics, indent=2)}")
        
        return leads
    
    def _build_search_url(self, query: str, location: Optional[str] = None) -> str:
        """Build Google Maps search URL"""
        if location:
            search_term = f"{query} near {location}"
        else:
            search_term = query
            
        encoded_query = quote_plus(search_term)
        return f"{self.BASE_URL}/search/{encoded_query}"
    
    def _wait_for_results(self) -> bool:
        """Wait for search results to load"""
        if not self.engine.driver:
            return False
            
        try:
            # Wait for results container
            Wait.until_element_visible(
                self.engine.driver,
                '[role="feed"]',
                timeout=10
            )
            
            # Additional wait for results to populate
            time.sleep(random.uniform(2, 3))
            
            return True
            
        except Exception as e:
            print(f"Error waiting for results: {e}")
            return False
    
    def _extract_with_infinite_scroll(self, config: GoogleMapsConfig) -> None:
        """Extract businesses with infinite scroll handling"""
        if not self.engine.driver:
            return
            
        driver = self.engine.driver
        previous_count = 0
        no_new_results_count = 0
        max_no_new = 3  # Stop after 3 scrolls with no new results
        
        while len(self.extracted_businesses) < config.max_results:
            # Extract visible businesses
            self._extract_visible_businesses(driver)
            
            current_count = len(self.extracted_businesses)
            
            # Check if we got new results
            if current_count == previous_count:
                no_new_results_count += 1
                if no_new_results_count >= max_no_new:
                    print("No new results after multiple scrolls, stopping")
                    break
            else:
                no_new_results_count = 0
                
            previous_count = current_count
            
            print(f"Extracted {current_count} businesses so far...")
            
            # Check if we've reached the end
            if self._is_end_of_results(driver):
                print("Reached end of results")
                break
                
            # Perform human-like scroll
            self._perform_human_scroll(driver, config)
            
            self.metrics['scroll_iterations'] += 1
            
            # Random pause between scrolls
            pause_time = random.uniform(*config.scroll_pause_time)
            time.sleep(pause_time)
    
    def _extract_visible_businesses(self, driver: Driver) -> None:
        """Extract currently visible business listings"""
        try:
            # Find all business cards in the feed
            business_elements = driver.find_elements_by_css_selector(
                '[role="feed"] > div > div[jsaction]'
            )
            
            for element in business_elements:
                try:
                    business_data = self._extract_business_data(element, driver)
                    
                    if business_data and business_data.get('place_id'):
                        place_id = business_data['place_id']
                        
                        # Skip if already seen
                        if place_id in self.seen_place_ids:
                            continue
                            
                        self.seen_place_ids.add(place_id)
                        self.extracted_businesses.append(business_data)
                        self.metrics['businesses_found'] += 1
                        
                except Exception as e:
                    self.metrics['extraction_errors'] += 1
                    continue
                    
        except Exception as e:
            print(f"Error extracting businesses: {e}")
    
    def _extract_business_data(self, element, driver: Driver) -> Optional[Dict[str, Any]]:
        """Extract data from a single business element"""
        try:
            business_data = {
                'place_id': None,
                'name': None,
                'category': None,
                'rating': None,
                'review_count': None,
                'address': None,
                'phone': None,
                'website': None,
                'price_range': None,
                'hours': None,
                'description': None,
                'extracted_at': datetime.now().isoformat()
            }
            
            # Extract aria-label which contains structured data
            aria_label = element.get_attribute('aria-label')
            if aria_label:
                business_data.update(self._parse_aria_label(aria_label))
            
            # Extract name
            name_elem = element.find_element_by_css_selector('[class*="fontHeadlineSmall"]')
            if name_elem:
                business_data['name'] = name_elem.text.strip()
            
            # Extract rating
            rating_elem = element.find_element_by_css_selector('[role="img"][aria-label*="stars"]')
            if rating_elem:
                rating_text = rating_elem.get_attribute('aria-label')
                rating_match = re.search(r'([\d.]+)\s+stars?', rating_text)
                if rating_match:
                    business_data['rating'] = float(rating_match.group(1))
            
            # Extract review count
            review_elem = element.find_element_by_css_selector('[aria-label*="reviews"]')
            if review_elem:
                review_text = review_elem.get_attribute('aria-label')
                review_match = re.search(r'(\d+)\s+reviews?', review_text)
                if review_match:
                    business_data['review_count'] = int(review_match.group(1))
            
            # Extract category/type
            try:
                category_elem = element.find_element_by_css_selector('[class*="fontBodyMedium"] span:nth-child(1)')
                if category_elem:
                    business_data['category'] = category_elem.text.strip()
            except:
                pass
            
            # Extract price range
            try:
                price_elem = element.find_element_by_css_selector('[aria-label*="Price"]')
                if price_elem:
                    business_data['price_range'] = price_elem.text.strip()
            except:
                pass
            
            # Extract address
            try:
                # Address is usually in the second or third span
                address_elems = element.find_elements_by_css_selector('[class*="fontBodyMedium"] span')
                for addr_elem in address_elems:
                    text = addr_elem.text.strip()
                    # Check if it looks like an address
                    if any(keyword in text.lower() for keyword in ['st', 'ave', 'rd', 'blvd', 'drive', 'way']):
                        business_data['address'] = text
                        break
            except:
                pass
            
            # Extract place ID from data attributes
            try:
                data_value = element.get_attribute('data-value')
                if data_value:
                    # Parse the data-value JSON
                    import json
                    data = json.loads(data_value)
                    if isinstance(data, dict) and 'i' in data:
                        business_data['place_id'] = data['i']
            except:
                # Fallback: use name + address as ID
                if business_data['name']:
                    import hashlib
                    id_string = f"{business_data['name']}_{business_data.get('address', '')}"
                    business_data['place_id'] = hashlib.md5(id_string.encode()).hexdigest()[:12]
            
            # Additional data extraction when clicking on the business
            if business_data['name'] and random.random() < 0.1:  # Sample 10% for detailed extraction
                self._extract_detailed_info(element, business_data, driver)
            
            return business_data if business_data['name'] else None
            
        except Exception as e:
            return None
    
    def _parse_aria_label(self, aria_label: str) -> Dict[str, Any]:
        """Parse structured data from aria-label attribute"""
        parsed_data = {}
        
        # Common patterns in aria-label
        patterns = {
            'rating': r'([\d.]+) stars?',
            'reviews': r'(\d+) reviews?',
            'price': r'(\$+)',
            'category': r'(?:·\s*)([^·]+?)(?:\s*·)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, aria_label)
            if match:
                if key == 'rating':
                    parsed_data['rating'] = float(match.group(1))
                elif key == 'reviews':
                    parsed_data['review_count'] = int(match.group(1))
                elif key == 'price':
                    parsed_data['price_range'] = match.group(1)
                elif key == 'category':
                    parsed_data['category'] = match.group(1).strip()
                    
        return parsed_data
    
    def _extract_detailed_info(self, element, business_data: Dict, driver: Driver) -> None:
        """Extract detailed information by clicking on the business"""
        try:
            # Click on the business with human-like behavior
            if self.behavior_simulator:
                # Simulate hovering before click
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                actions.move_to_element(element).perform()
                time.sleep(random.uniform(0.5, 1.0))
            
            element.click()
            time.sleep(random.uniform(2, 3))
            
            # Extract phone number
            try:
                phone_elem = driver.find_element_by_css_selector('[data-tooltip*="phone"]')
                if phone_elem:
                    business_data['phone'] = phone_elem.get_attribute('aria-label').replace('Phone:', '').strip()
            except:
                pass
            
            # Extract website
            try:
                website_elem = driver.find_element_by_css_selector('[data-tooltip*="website"]')
                if website_elem:
                    business_data['website'] = website_elem.get_attribute('href')
            except:
                pass
            
            # Extract hours
            try:
                hours_elem = driver.find_element_by_css_selector('[aria-label*="Hours"]')
                if hours_elem:
                    business_data['hours'] = hours_elem.text.strip()
            except:
                pass
            
            # Go back to results
            driver.execute_script("window.history.back()")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            pass
    
    def _is_end_of_results(self, driver: Driver) -> bool:
        """Check if we've reached the end of search results"""
        try:
            # Check for "You've reached the end" message
            end_indicators = [
                "You've reached the end",
                "No more results",
                "That's all",
                "Can't find"
            ]
            
            page_text = driver.find_element_by_tag_name('body').text
            
            for indicator in end_indicators:
                if indicator in page_text:
                    return True
                    
            return False
            
        except:
            return False
    
    def _perform_human_scroll(self, driver: Driver, config: GoogleMapsConfig) -> None:
        """Perform human-like scrolling behavior"""
        try:
            # Get the scrollable element
            feed_element = driver.find_element_by_css_selector('[role="feed"]')
            
            if config.human_behavior and self.behavior_simulator:
                # Get scroll pattern
                scroll_pattern = self.behavior_simulator.get_scroll_pattern()
                
                for action in scroll_pattern[:3]:  # Limit to 3 actions per scroll
                    if action['action'] == 'scroll':
                        # Scroll the feed element
                        driver.execute_script(
                            "arguments[0].scrollBy(0, arguments[1])",
                            feed_element,
                            action['distance']
                        )
                    elif action['action'] == 'wait':
                        time.sleep(action['duration'])
            else:
                # Simple scroll
                driver.execute_script(
                    "arguments[0].scrollBy(0, 500)",
                    feed_element
                )
                
        except Exception as e:
            # Fallback to page scroll
            driver.execute_script("window.scrollBy(0, 500)")
    
    def _perform_geographic_expansion(self, config: GoogleMapsConfig) -> None:
        """Expand search to nearby areas for better coverage"""
        if not config.location:
            return
            
        print(f"\nPerforming geographic expansion (radius: {config.expansion_radius_km}km)")
        
        # Generate nearby location queries
        nearby_queries = self._generate_nearby_queries(config.location, config.expansion_radius_km)
        
        for nearby_location in nearby_queries[:3]:  # Limit to 3 expansions
            print(f"Expanding search to: {nearby_location}")
            
            # Build new search URL
            search_url = self._build_search_url(config.search_query, nearby_location)
            
            # Navigate to new search
            if self.engine.navigate_with_stealth(search_url, wait_time=5):
                self._wait_for_results()
                
                # Extract with limited scroll
                limited_config = GoogleMapsConfig(
                    search_query=config.search_query,
                    location=nearby_location,
                    max_results=min(100, config.max_results - len(self.extracted_businesses)),
                    enable_geographic_expansion=False  # Don't expand further
                )
                
                self._extract_with_infinite_scroll(limited_config)
                self.metrics['geographic_expansions'] += 1
                
                if len(self.extracted_businesses) >= config.max_results:
                    break
    
    def _generate_nearby_queries(self, location: str, radius_km: int) -> List[str]:
        """Generate nearby location queries for geographic expansion"""
        # Simple approach: add cardinal directions
        nearby = [
            f"North {location}",
            f"South {location}",
            f"East {location}",
            f"West {location}",
            f"Downtown {location}",
            f"Near {location}"
        ]
        
        return nearby
    
    def _convert_to_leads(self, businesses: List[Dict]) -> List[BusinessLead]:
        """Convert extracted business data to BusinessLead objects"""
        leads = []
        
        for business in businesses:
            try:
                # Parse address components
                address = Address()
                if business.get('address'):
                    # Simple address parsing (can be enhanced)
                    parts = business['address'].split(',')
                    if len(parts) >= 2:
                        address.street = parts[0].strip()
                        if len(parts) >= 3:
                            address.city = parts[1].strip()
                            state_zip = parts[2].strip().split()
                            if state_zip:
                                address.state = state_zip[0]
                                if len(state_zip) > 1:
                                    address.postal_code = state_zip[1]
                
                # Create contact info
                contact = ContactInfo(
                    phone=business.get('phone'),
                    website=business.get('website')
                )
                
                # Create lead
                lead = BusinessLead(
                    source="google_maps",
                    source_id=business.get('place_id'),
                    name=business.get('name', ''),
                    category=business.get('category'),
                    contact=contact,
                    address=address,
                    rating=business.get('rating'),
                    review_count=business.get('review_count'),
                    price_range=business.get('price_range'),
                    description=business.get('description'),
                    status=LeadStatus.PENDING
                )
                
                # Calculate confidence
                lead.calculate_confidence()
                
                leads.append(lead)
                
            except Exception as e:
                print(f"Error converting business to lead: {e}")
                continue
                
        return leads


# Decorator for easy use
def scrape_google_maps(query: str, location: str = None, max_results: int = 100):
    """
    Decorator to scrape Google Maps for a function
    
    Usage:
        @scrape_google_maps("restaurants", "New York", 200)
        def process_restaurants(leads):
            # Process the extracted leads
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create scraper configuration
            config = GoogleMapsConfig(
                search_query=query,
                location=location,
                max_results=max_results
            )
            
            # Initialize engine with stealth settings
            session_config = SessionConfig(
                session_id=f"gmaps_{int(time.time())}",
                profile_name=f"gmaps_profile",
                stealth_level=3,
                block_images=True,
                block_media=True
            )
            
            engine = BotasaurusEngine(session_config)
            scraper = GoogleMapsScraper(engine)
            
            try:
                # Perform scraping
                leads = scraper.search(config)
                
                # Pass leads to the wrapped function
                result = func(leads, *args, **kwargs)
                return result
                
            finally:
                engine.cleanup()
                
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test Google Maps scraper
    print("Google Maps Scraper Test")
    print("="*50)
    
    # Test configuration
    test_config = GoogleMapsConfig(
        search_query="coffee shops",
        location="San Francisco",
        max_results=50,
        enable_geographic_expansion=True,
        human_behavior=True
    )
    
    print(f"\nSearch Query: {test_config.search_query}")
    print(f"Location: {test_config.location}")
    print(f"Target Results: {test_config.max_results}")
    print(f"Geographic Expansion: {test_config.enable_geographic_expansion}")
    
    # Create engine with stealth configuration
    session_config = SessionConfig(
        session_id="gmaps_test",
        profile_name="gmaps_test_profile",
        stealth_level=3,
        block_images=True
    )
    
    print("\nInitializing Botasaurus engine...")
    engine = BotasaurusEngine(session_config)
    
    print("Creating Google Maps scraper...")
    scraper = GoogleMapsScraper(engine)
    
    print("\nStarting extraction...")
    print("Note: This is a test configuration. Actual scraping requires a browser.")
    
    # Would perform actual scraping here
    # leads = scraper.search(test_config)
    
    print("\nTest configuration complete!")
    print("Google Maps scraper is ready for use.")
    
    # Cleanup
    engine.cleanup()