"""
Bing Maps parser for extracting business information from map results.
Handles infinite scroll results and various card layouts.
"""
from typing import List, Optional, Dict, Any
import re
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
import logging

from ..models.business_entity import BusinessEntity, BusinessRating, BusinessHours


class BingMapParser:
    """Parser for Bing Maps business listings."""
    
    # CSS selectors for different Bing Maps layouts
    SELECTORS = {
        # Main business card containers
        'business_cards': [
            'div[data-entity-type="business"]',
            '.b_entityTP',
            '.entityCard',
            '.businessResult',
            'li.b_algo'
        ],
        
        # Business name selectors
        'business_name': [
            'h3.b_entityTitle a',
            '.b_entityTitle',
            'h3 a',
            '.entityTitle',
            'h2 a',
            'h1'
        ],
        
        # Address selectors
        'address': [
            '.b_factrow .b_factCell',
            '.address',
            '.b_address',
            '.entityAddress',
            '[data-local-attribute="d"]',
            '.factRow .factCell'
        ],
        
        # Phone selectors
        'phone': [
            '.b_factrow .b_factCell',
            '.phone',
            '.b_phone',
            '.entityPhone',
            'a[href^="tel:"]',
            '[data-local-attribute="t"]'
        ],
        
        # Website selectors
        'website': [
            '.b_factrow:contains("Website") .b_factCell a',
            '.website a',
            '.b_website a',
            '.entityWebsite a',
            'a[href^="http"]:not([href*="bing.com"])',
            '[data-local-attribute="u"] a'
        ],
        
        # Rating selectors
        'rating': [
            '.b_starDU',
            '.rating',
            '.stars',
            '.b_rating',
            '.entityRating',
            '[data-local-attribute="r"]'
        ],
        
        # Hours selectors
        'hours': [
            '.b_factrow:contains("Hours") .b_factCell',
            '.hours',
            '.b_hours',
            '.entityHours',
            '.hoursInfo',
            '[data-local-attribute="h"]'
        ],
        
        # Category selectors
        'category': [
            '.b_factrow:contains("Category") .b_factCell',
            '.category',
            '.b_category',
            '.entityCategory',
            '.businessType'
        ],
        
        # Description selectors
        'description': [
            '.b_caption p',
            '.description',
            '.b_desc',
            '.entityDescription',
            '.snippet'
        ]
    }
    
    # XPath fallback selectors
    XPATH_SELECTORS = {
        'business_cards': [
            "//div[contains(@class, 'b_algo') or contains(@class, 'entityCard')]",
            "//li[contains(@class, 'b_algo')]//div[contains(@class, 'b_title')]/..",
            "//*[@data-entity-type='business']"
        ],
        
        'business_name': [
            ".//h3//a[1]",
            ".//h2//a[1]",
            ".//a[contains(@class, 'b_title')]",
            ".//*[contains(@class, 'entityTitle')]//text()"
        ],
        
        'address': [
            ".//*[contains(text(), 'Address')]/following-sibling::*//text()",
            ".//*[contains(@class, 'address')]//text()",
            ".//*[@data-local-attribute='d']//text()"
        ],
        
        'phone': [
            ".//a[starts-with(@href, 'tel:')]/@href",
            ".//*[contains(text(), 'Phone')]/following-sibling::*//text()",
            ".//*[contains(@class, 'phone')]//text()",
            ".//*[@data-local-attribute='t']//text()"
        ],
        
        'website': [
            ".//a[starts-with(@href, 'http') and not(contains(@href, 'bing.com'))]/@href",
            ".//*[contains(text(), 'Website')]/following-sibling::*//a/@href",
            ".//*[contains(@class, 'website')]//a/@href"
        ]
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_business_cards(self, html_content: str, source_url: str = None) -> List[BusinessEntity]:
        """Parse business cards from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        businesses = []
        
        # Find all business cards using multiple selectors
        business_cards = []
        for selector in self.SELECTORS['business_cards']:
            cards = soup.select(selector)
            business_cards.extend(cards)
        
        # Remove duplicates based on position in DOM
        seen_positions = set()
        unique_cards = []
        for card in business_cards:
            position = self._get_element_position(card)
            if position not in seen_positions:
                unique_cards.append(card)
                seen_positions.add(position)
        
        for card in unique_cards:
            try:
                business = self._parse_single_business_card(card, source_url)
                if business and business.is_valid():
                    businesses.append(business)
            except Exception as e:
                self.logger.warning(f"Failed to parse business card: {e}")
                continue
        
        return businesses
    
    def parse_selenium_elements(self, elements: List[WebElement], source_url: str = None) -> List[BusinessEntity]:
        """Parse business cards from Selenium WebElements."""
        businesses = []
        
        for element in elements:
            try:
                # Convert WebElement to HTML and parse
                html = element.get_attribute('outerHTML')
                soup = BeautifulSoup(html, 'html.parser')
                card = soup.find()
                
                business = self._parse_single_business_card(card, source_url)
                if business and business.is_valid():
                    businesses.append(business)
            except Exception as e:
                self.logger.warning(f"Failed to parse Selenium element: {e}")
                continue
        
        return businesses
    
    def _parse_single_business_card(self, card: Tag, source_url: str = None) -> Optional[BusinessEntity]:
        """Parse a single business card element."""
        try:
            # Extract basic information
            name = self._extract_business_name(card)
            if not name:
                return None
            
            address = self._extract_address(card)
            phone = self._extract_phone(card)
            website = self._extract_website(card)
            rating = self._extract_rating(card)
            hours = self._extract_hours(card)
            category = self._extract_category(card)
            description = self._extract_description(card)
            
            # Create business entity
            business = BusinessEntity(
                name=name,
                address=address,
                phone=phone,
                website=website,
                rating=rating,
                hours=hours,
                category=category,
                description=description,
                source="bing_maps",
                source_url=source_url,
                raw_data={
                    'html': str(card),
                    'parser': 'bing_map_parser'
                }
            )
            
            return business
            
        except Exception as e:
            self.logger.error(f"Error parsing business card: {e}")
            return None
    
    def _extract_business_name(self, card: Tag) -> Optional[str]:
        """Extract business name from card."""
        for selector in self.SELECTORS['business_name']:
            try:
                element = card.select_one(selector)
                if element:
                    # Try to get text from link or direct text
                    name = element.get_text(strip=True) or element.get('title', '')
                    if name:
                        return name
            except Exception:
                continue
        
        # Fallback to any link or heading text
        try:
            for tag in ['h1', 'h2', 'h3', 'h4', 'a']:
                element = card.find(tag)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:
                        return text
        except Exception:
            pass
        
        return None
    
    def _extract_address(self, card: Tag) -> Optional[str]:
        """Extract address from card."""
        for selector in self.SELECTORS['address']:
            try:
                element = card.select_one(selector)
                if element:
                    address = element.get_text(strip=True)
                    if address and len(address) > 10 and self._looks_like_address(address):
                        return address
            except Exception:
                continue
        
        # Look for address patterns in text
        text = card.get_text()
        address_patterns = [
            r'\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)',
            r'[A-Za-z\s,]+,\s*[A-Z]{2}\s*\d{5}',
            r'\d+[^,]*,[^,]*,[A-Z]{2}'
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group().strip()
        
        return None
    
    def _extract_phone(self, card: Tag) -> Optional[str]:
        """Extract phone number from card."""
        # Check tel: links first
        tel_link = card.find('a', href=re.compile(r'^tel:'))
        if tel_link:
            phone = tel_link.get('href').replace('tel:', '')
            return self._clean_phone(phone)
        
        # Try CSS selectors
        for selector in self.SELECTORS['phone']:
            try:
                element = card.select_one(selector)
                if element:
                    phone = element.get_text(strip=True)
                    if self._is_valid_phone(phone):
                        return self._clean_phone(phone)
            except Exception:
                continue
        
        # Search for phone patterns in text
        text = card.get_text()
        phone_patterns = [
            r'\(\d{3}\)\s*\d{3}[-\s]?\d{4}',
            r'\d{3}[-\s\.]?\d{3}[-\s\.]?\d{4}',
            r'\+1[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{4}'
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group().strip()
                if self._is_valid_phone(phone):
                    return self._clean_phone(phone)
        
        return None
    
    def _extract_website(self, card: Tag) -> Optional[str]:
        """Extract website URL from card."""
        for selector in self.SELECTORS['website']:
            try:
                element = card.select_one(selector)
                if element:
                    url = element.get('href', '')
                    if url and self._is_valid_website(url):
                        return url
            except Exception:
                continue
        
        # Look for any external links
        links = card.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            if self._is_valid_website(href):
                return href
        
        return None
    
    def _extract_rating(self, card: Tag) -> Optional[BusinessRating]:
        """Extract rating information from card."""
        for selector in self.SELECTORS['rating']:
            try:
                element = card.select_one(selector)
                if element:
                    # Try to extract rating from various formats
                    rating_text = element.get_text(strip=True)
                    
                    # Look for star ratings with review count
                    star_review_match = re.search(r'(\d+(?:\.\d+)?)\s*stars?.*?(\d+)\s*reviews?', rating_text, re.IGNORECASE)
                    if star_review_match:
                        score = float(star_review_match.group(1))
                        review_count = int(star_review_match.group(2))
                        return BusinessRating(
                            score=score,
                            max_score=5.0,
                            review_count=review_count,
                            source="bing_maps"
                        )
                    
                    # Look for simple star ratings
                    star_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:out of|\/|\s)\s*(\d+(?:\.\d+)?)', rating_text)
                    if star_match:
                        score = float(star_match.group(1))
                        max_score = float(star_match.group(2))
                        
                        return BusinessRating(
                            score=score,
                            max_score=max_score,
                            review_count=None,
                            source="bing_maps"
                        )
                    
                    # Look for decimal ratings
                    rating_match = re.search(r'(\d+(?:\.\d+))', rating_text)
                    if rating_match:
                        score = float(rating_match.group(1))
                        if 0 <= score <= 5:
                            return BusinessRating(score=score, source="bing_maps")
            except Exception:
                continue
        
        return None
    
    def _extract_hours(self, card: Tag) -> Optional[BusinessHours]:
        """Extract business hours from card."""
        for selector in self.SELECTORS['hours']:
            try:
                element = card.select_one(selector)
                if element:
                    hours_text = element.get_text(strip=True)
                    if hours_text:
                        return BusinessHours.from_text(hours_text)
            except Exception:
                continue
        
        # Look for hours patterns in text
        text = card.get_text()
        hours_patterns = [
            r'(?:Mon|Monday).*?(?:Sun|Sunday).*?(?:\d+(?::\d+)?(?:AM|PM))',
            r'Hours:.*?(?:\d+(?::\d+)?(?:AM|PM))',
            r'Open.*?(?:\d+(?::\d+)?(?:AM|PM))'
        ]
        
        for pattern in hours_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                hours_text = match.group().strip()
                return BusinessHours.from_text(hours_text)
        
        return None
    
    def _extract_category(self, card: Tag) -> Optional[str]:
        """Extract business category from card."""
        for selector in self.SELECTORS['category']:
            try:
                element = card.select_one(selector)
                if element:
                    category = element.get_text(strip=True)
                    if category:
                        return category
            except Exception:
                continue
        
        return None
    
    def _extract_description(self, card: Tag) -> Optional[str]:
        """Extract business description from card."""
        for selector in self.SELECTORS['description']:
            try:
                element = card.select_one(selector)
                if element:
                    description = element.get_text(strip=True)
                    if description and len(description) > 20:
                        return description
            except Exception:
                continue
        
        return None
    
    def _get_element_position(self, element: Tag) -> str:
        """Get unique position identifier for element."""
        # Create position identifier based on tag and attributes
        attrs = element.attrs or {}
        position_attrs = ['id', 'class', 'data-entity-id']
        
        position_parts = [element.name]
        for attr in position_attrs:
            if attr in attrs:
                position_parts.append(f"{attr}:{attrs[attr]}")
        
        return "|".join(position_parts)
    
    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number."""
        # Remove common prefixes and clean
        phone = re.sub(r'tel:', '', phone, flags=re.IGNORECASE)
        phone = re.sub(r'[^\d+\-\(\)\s]', '', phone)
        return phone.strip()
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Check if phone number looks valid."""
        digits = re.sub(r'[^\d]', '', phone)
        return 10 <= len(digits) <= 15
    
    def _looks_like_address(self, text: str) -> bool:
        """Check if text looks like an address."""
        if not text or len(text) < 10:
            return False
        
        # Common address indicators
        address_indicators = [
            r'\d+.*(?:street|st|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|way|pkwy)',
            r'.*,\s*[A-Z]{2}\s*\d{5}',
            r'\d+.*,.*,.*[A-Z]{2}',
            r'suite|ste|apt|apartment|unit|floor|#'
        ]
        
        for pattern in address_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_valid_website(self, url: str) -> bool:
        """Check if URL is a valid business website."""
        if not url or not isinstance(url, str):
            return False
        
        # Skip internal Bing URLs
        bing_domains = ['bing.com', 'microsoft.com', 'msn.com']
        for domain in bing_domains:
            if domain in url.lower():
                return False
        
        # Must be HTTP/HTTPS
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Basic URL validation
        return bool(re.match(r'https?://[^\s<>"{}|\\^`\[\]]+', url))