#!/usr/bin/env python3
"""
Map Business Data Extractors
Handles extraction of business cards from Bing Maps and Google Maps results
"""

from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class BusinessCard:
    """Represents a business card with extracted information"""
    name: str
    address: str = None
    phone: str = None
    email: str = None
    website: str = None
    rating: float = None
    review_count: int = None
    category: str = None
    hours: str = None
    unique_id: str = None
    source_platform: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export"""
        return {
            'business_name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'rating': self.rating,
            'review_count': self.review_count,
            'category': self.category,
            'hours': self.hours,
            'unique_id': self.unique_id,
            'source_platform': self.source_platform
        }

class BaseMapExtractor(ABC):
    """Base class for map extractors"""
    
    def __init__(self):
        self.extracted_ids: Set[str] = set()
        self.business_cache: List[BusinessCard] = []
        
    @abstractmethod
    def extract_business_cards(self, driver) -> List[Dict[str, Any]]:
        """Extract business cards from current view"""
        pass
    
    @abstractmethod
    def extract_all_businesses(self, driver) -> List[Dict[str, Any]]:
        """Extract all visible businesses comprehensively"""
        pass
    
    def _clean_phone_number(self, phone: str) -> Optional[str]:
        """Clean and format phone number"""
        if not phone:
            return None
            
        # Remove all non-digit characters
        digits = re.sub(r'[^\d]', '', phone)
        
        # Format US phone numbers
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        elif len(digits) >= 10:
            return digits
        
        return None
    
    def _extract_email_from_text(self, text: str) -> Optional[str]:
        """Extract email from text content"""
        if not text:
            return None
            
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Filter out fake emails
        for email in emails:
            if not any(fake in email.lower() for fake in [
                'example', 'domain', 'test', 'sample', 'noreply', 'no-reply'
            ]):
                return email
                
        return None
    
    def _generate_unique_id(self, name: str, address: str = None) -> str:
        """Generate unique ID for business"""
        import hashlib
        
        # Combine name and address for unique identifier
        identifier = f"{name}_{address or ''}".lower().strip()
        return hashlib.md5(identifier.encode()).hexdigest()[:12]
    
    def _is_duplicate(self, unique_id: str) -> bool:
        """Check if business already extracted"""
        return unique_id in self.extracted_ids
    
    def _add_to_cache(self, business: BusinessCard) -> None:
        """Add business to cache if not duplicate"""
        if not self._is_duplicate(business.unique_id):
            self.extracted_ids.add(business.unique_id)
            self.business_cache.append(business)

class BingMapsExtractor(BaseMapExtractor):
    """Extractor for Bing Maps business listings"""
    
    def extract_business_cards(self, driver) -> List[Dict[str, Any]]:
        """Extract business cards from current Bing Maps view"""
        businesses = []
        
        try:
            # Get page source and parse
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Bing Maps business cards selectors (multiple patterns)
            card_selectors = [
                'div[data-entity-id]',  # Main business cards
                '.businessCard',        # Alternative selector
                '[data-role="business-card"]',  # Another pattern
                '.b_places_item'        # Search results pattern
            ]
            
            for selector in card_selectors:
                cards = soup.select(selector)
                for card in cards:
                    business = self._extract_bing_business_data(card, driver)
                    if business:
                        businesses.append(business.to_dict())
            
            logger.debug(f"Extracted {len(businesses)} businesses from current Bing view")
            
        except Exception as e:
            logger.error(f"Error extracting Bing business cards: {e}")
        
        return businesses
    
    def extract_all_businesses(self, driver) -> List[Dict[str, Any]]:
        """Extract all visible businesses from Bing Maps"""
        all_businesses = []
        
        try:
            # Scroll through entire page collecting businesses
            driver.run_js("window.scrollTo(0, 0)")
            
            # Get final page state
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract from multiple container types
            container_selectors = [
                '#businessList',
                '.businessesPanel',
                '[data-role="business-list"]',
                '.searchResults'
            ]
            
            for container_selector in container_selectors:
                container = soup.select_one(container_selector)
                if container:
                    businesses = self._extract_businesses_from_container(container, driver)
                    all_businesses.extend(businesses)
            
            # Deduplicate based on unique IDs
            unique_businesses = self._deduplicate_businesses(all_businesses)
            
            logger.info(f"Final Bing extraction: {len(unique_businesses)} unique businesses")
            
        except Exception as e:
            logger.error(f"Error in Bing comprehensive extraction: {e}")
        
        return unique_businesses
    
    def _extract_bing_business_data(self, card_element, driver) -> Optional[BusinessCard]:
        """Extract business data from Bing Maps card element"""
        try:
            # Extract business name
            name_selectors = [
                '.business_name',
                '[data-role="business-name"]',
                'h3 a',
                '.b_title a'
            ]
            
            name = None
            for selector in name_selectors:
                name_elem = card_element.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    break
            
            if not name:
                return None
            
            # Extract address
            address = None
            address_selectors = [
                '.business_address',
                '[data-role="address"]',
                '.address'
            ]
            
            for selector in address_selectors:
                addr_elem = card_element.select_one(selector)
                if addr_elem:
                    address = addr_elem.get_text(strip=True)
                    break
            
            # Extract phone number
            phone = None
            phone_selectors = [
                '.business_phone',
                '[data-role="phone"]',
                '.phone',
                'a[href^="tel:"]'
            ]
            
            for selector in phone_selectors:
                phone_elem = card_element.select_one(selector)
                if phone_elem:
                    phone_text = phone_elem.get('href', '') or phone_elem.get_text(strip=True)
                    phone = self._clean_phone_number(phone_text.replace('tel:', ''))
                    break
            
            # Extract website
            website = None
            website_links = card_element.select('a[href^="http"]')
            for link in website_links:
                href = link.get('href', '')
                # Skip Bing internal links
                if not any(exclude in href for exclude in ['bing.com', 'microsoft.com']):
                    website = href
                    break
            
            # Extract rating
            rating = None
            rating_elem = card_element.select_one('.rating, .stars, [data-role="rating"]')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Extract review count
            review_count = None
            review_elem = card_element.select_one('.review_count, .reviews, [data-role="reviews"]')
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                count_match = re.search(r'(\d+)', review_text)
                if count_match:
                    review_count = int(count_match.group(1))
            
            # Extract category
            category = None
            category_elem = card_element.select_one('.business_category, .category, [data-role="category"]')
            if category_elem:
                category = category_elem.get_text(strip=True)
            
            # Look for email in page content (might require detail page visit)
            email = self._extract_email_from_card(card_element, driver)
            
            # Generate unique ID
            unique_id = self._generate_unique_id(name, address)
            
            business = BusinessCard(
                name=name,
                address=address,
                phone=phone,
                email=email,
                website=website,
                rating=rating,
                review_count=review_count,
                category=category,
                unique_id=unique_id,
                source_platform='bing_maps'
            )
            
            return business
            
        except Exception as e:
            logger.debug(f"Error extracting Bing business data: {e}")
            return None
    
    def _extract_email_from_card(self, card_element, driver) -> Optional[str]:
        """Try to extract email from business card or detail page"""
        try:
            # First check if email is visible in card
            card_text = card_element.get_text()
            email = self._extract_email_from_text(card_text)
            if email:
                return email
            
            # Look for detail page link
            detail_links = card_element.select('a[href*="details"], a[href*="business"]')
            for link in detail_links:
                detail_url = link.get('href')
                if detail_url and 'bing.com' in detail_url:
                    # Visit detail page briefly
                    try:
                        current_url = driver.get_current_url()
                        driver.get(detail_url)
                        driver.sleep(1)
                        
                        detail_text = driver.get_text()
                        email = self._extract_email_from_text(detail_text)
                        
                        # Return to search results
                        driver.get(current_url)
                        driver.sleep(1)
                        
                        if email:
                            return email
                            
                    except Exception as e:
                        logger.debug(f"Error visiting detail page: {e}")
                        break
            
        except Exception as e:
            logger.debug(f"Error extracting email from card: {e}")
        
        return None
    
    def _extract_businesses_from_container(self, container, driver) -> List[Dict[str, Any]]:
        """Extract businesses from a container element"""
        businesses = []
        
        # Find all business cards in container
        card_selectors = [
            'div[data-entity-id]',
            '.businessCard',
            '.business_item',
            '.b_places_item'
        ]
        
        for selector in card_selectors:
            cards = container.select(selector)
            for card in cards:
                business = self._extract_bing_business_data(card, driver)
                if business:
                    businesses.append(business.to_dict())
        
        return businesses

class GoogleMapsExtractor(BaseMapExtractor):
    """Extractor for Google Maps business listings"""
    
    def extract_business_cards(self, driver) -> List[Dict[str, Any]]:
        """Extract business cards from current Google Maps view"""
        businesses = []
        
        try:
            # Get page source and parse
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Google Maps business cards selectors
            card_selectors = [
                'div[data-result-index]',  # Main results
                '.place-result',           # Place results
                '[data-cid]',             # Business with CID
                '.section-result'         # Section results
            ]
            
            for selector in card_selectors:
                cards = soup.select(selector)
                for card in cards:
                    business = self._extract_google_business_data(card, driver)
                    if business:
                        businesses.append(business.to_dict())
            
            logger.debug(f"Extracted {len(businesses)} businesses from current Google view")
            
        except Exception as e:
            logger.error(f"Error extracting Google business cards: {e}")
        
        return businesses
    
    def extract_all_businesses(self, driver) -> List[Dict[str, Any]]:
        """Extract all visible businesses from Google Maps"""
        all_businesses = []
        
        try:
            # Scroll to top first
            driver.run_js("window.scrollTo(0, 0)")
            
            # Get final page state
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract from results panel
            results_panel = soup.select_one('[role="main"]')
            if results_panel:
                businesses = self._extract_businesses_from_google_panel(results_panel, driver)
                all_businesses.extend(businesses)
            
            # Deduplicate
            unique_businesses = self._deduplicate_businesses(all_businesses)
            
            logger.info(f"Final Google extraction: {len(unique_businesses)} unique businesses")
            
        except Exception as e:
            logger.error(f"Error in Google comprehensive extraction: {e}")
        
        return unique_businesses
    
    def _extract_google_business_data(self, card_element, driver) -> Optional[BusinessCard]:
        """Extract business data from Google Maps card element"""
        try:
            # Extract business name
            name_selectors = [
                '[data-value="Name"]',
                '.section-result-title',
                'h3',
                '.place-name'
            ]
            
            name = None
            for selector in name_selectors:
                name_elem = card_element.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    break
            
            if not name:
                return None
            
            # Extract address
            address = None
            address_selectors = [
                '[data-value="Address"]',
                '.section-result-location',
                '.address'
            ]
            
            for selector in address_selectors:
                addr_elem = card_element.select_one(selector)
                if addr_elem:
                    address = addr_elem.get_text(strip=True)
                    break
            
            # Extract phone (often requires detail page)
            phone = None
            phone_selectors = [
                '[data-value="Phone number"]',
                'a[href^="tel:"]',
                '.phone'
            ]
            
            for selector in phone_selectors:
                phone_elem = card_element.select_one(selector)
                if phone_elem:
                    phone_text = phone_elem.get('href', '') or phone_elem.get_text(strip=True)
                    phone = self._clean_phone_number(phone_text.replace('tel:', ''))
                    break
            
            # Extract website
            website = None
            website_links = card_element.select('a[href^="http"]')
            for link in website_links:
                href = link.get('href', '')
                # Skip Google internal links
                if not any(exclude in href for exclude in ['google.com', 'maps.google']):
                    website = href
                    break
            
            # Extract rating
            rating = None
            rating_elem = card_element.select_one('[role="img"][aria-label*="star"]')
            if rating_elem:
                aria_label = rating_elem.get('aria-label', '')
                rating_match = re.search(r'(\d+\.?\d*)', aria_label)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Extract review count
            review_count = None
            review_elem = card_element.select_one('[aria-label*="review"]')
            if review_elem:
                aria_label = review_elem.get('aria-label', '')
                count_match = re.search(r'(\d+)', aria_label)
                if count_match:
                    review_count = int(count_match.group(1))
            
            # Extract category
            category = None
            category_elem = card_element.select_one('.section-result-details')
            if category_elem:
                category = category_elem.get_text(strip=True)
            
            # Generate unique ID
            unique_id = self._generate_unique_id(name, address)
            
            business = BusinessCard(
                name=name,
                address=address,
                phone=phone,
                email=None,  # Google Maps rarely shows emails directly
                website=website,
                rating=rating,
                review_count=review_count,
                category=category,
                unique_id=unique_id,
                source_platform='google_maps'
            )
            
            return business
            
        except Exception as e:
            logger.debug(f"Error extracting Google business data: {e}")
            return None
    
    def _extract_businesses_from_google_panel(self, panel, driver) -> List[Dict[str, Any]]:
        """Extract businesses from Google Maps results panel"""
        businesses = []
        
        # Find all business cards in panel
        card_selectors = [
            'div[data-result-index]',
            '.section-result',
            '[data-cid]'
        ]
        
        for selector in card_selectors:
            cards = panel.select(selector)
            for card in cards:
                business = self._extract_google_business_data(card, driver)
                if business:
                    businesses.append(business.to_dict())
        
        return businesses
    
    def _deduplicate_businesses(self, businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate businesses based on unique ID"""
        seen_ids = set()
        unique_businesses = []
        
        for business in businesses:
            unique_id = business.get('unique_id')
            if unique_id and unique_id not in seen_ids:
                seen_ids.add(unique_id)
                unique_businesses.append(business)
        
        return unique_businesses