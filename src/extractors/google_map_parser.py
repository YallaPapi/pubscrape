"""
Google Maps parser for extracting business information from map results.
Handles infinite scroll results and various card layouts.
"""
from typing import List, Optional, Dict, Any
import re
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
import logging

from ..models.business_entity import BusinessEntity, BusinessRating, BusinessHours


class GoogleMapParser:
    """Parser for Google Maps business listings."""
    
    # CSS selectors for different Google Maps layouts
    SELECTORS = {
        # Main business card containers
        'business_cards': [
            'div[data-result-index]',
            '.g',
            '.VkpGBb',
            '.hfpxzc',
            'div[role="article"]',
            '.ZwVX6c',
            '.UaQhfb'
        ],
        
        # Business name selectors
        'business_name': [
            '.DUwDvf',
            '.qBF1Pd',
            'h3 a span',
            '.BNeawe.vvjwJb.AP7Wnd',
            '.SPZz6b',
            'h3.LC20lb.MBeuO.DKV0Md',
            '.fontHeadlineSmall'
        ],
        
        # Address selectors
        'address': [
            '.W4Efsd:last-child .BNeawe.UPmit.AP7Wnd',
            '.W4Efsd .BNeawe.UPmit.AP7Wnd',
            '.rllt__details div:contains("·")',
            '.VkpGBb .BNeawe.s3v9rd.AP7Wnd',
            '.fontBodyMedium',
            '.Io6YTe.fontBodyMedium'
        ],
        
        # Phone selectors
        'phone': [
            '.BNeawe.tAd8D.AP7Wnd',
            'span[data-phone]',
            'a[href^="tel:"]',
            '.fontBodyMedium[role="link"]',
            '.rogA2c .fontBodyMedium'
        ],
        
        # Website selectors
        'website': [
            '.lcr4fd a',
            'a[data-href*="http"]',
            'a[href^="http"]:not([href*="google.com"])',
            '.fontBodyMedium a[href^="http"]'
        ],
        
        # Rating selectors
        'rating': [
            '.MW4etd',
            '.UY7F9',
            '.RDApEe.YrbPuc',
            '.BNeawe.s3v9rd.AP7Wnd:contains("★")',
            'span[role="img"][aria-label*="star"]',
            '.fontBodyMedium:contains("★")'
        ],
        
        # Hours selectors
        'hours': [
            '.G69Gu',
            '.OqQkHd',
            '.BNeawe.s3v9rd.AP7Wnd:contains("Open")',
            '.BNeawe.s3v9rd.AP7Wnd:contains("Closed")',
            '.fontBodyMedium:contains("Open")',
            '.rogA2c:contains("hours")'
        ],
        
        # Category selectors
        'category': [
            '.W4Efsd .BNeawe.s3v9rd.AP7Wnd',
            '.W4Efsd:first-child .BNeawe.s3v9rd.AP7Wnd',
            '.fontBodyMedium .fontBodyMedium',
            '.RDApEe .fontBodyMedium'
        ],
        
        # Description selectors
        'description': [
            '.Y0A0hc .BNeawe.s3v9rd.AP7Wnd',
            '.VwiC3b.yXK7lf.MUxGbd.yDYNvb.lyLwlc.lEBKkf',
            '.fontBodyMedium:not(:first-child)',
            '.ZwVX6c .fontBodyMedium'
        ]
    }
    
    # XPath fallback selectors
    XPATH_SELECTORS = {
        'business_cards': [
            "//div[@data-result-index]",
            "//div[contains(@class, 'g')]",
            "//div[contains(@class, 'VkpGBb')]",
            "//div[@role='article']"
        ],
        
        'business_name': [
            ".//h3//span[1]",
            ".//*[contains(@class, 'DUwDvf')]//text()",
            ".//*[contains(@class, 'qBF1Pd')]//text()",
            ".//h3//a//span//text()"
        ],
        
        'address': [
            ".//*[contains(@class, 'UPmit')]//text()",
            ".//*[contains(@class, 'fontBodyMedium')]//text()[contains(., ',')]",
            ".//*[contains(text(), '·')]//text()"
        ],
        
        'phone': [
            ".//a[starts-with(@href, 'tel:')]/@href",
            ".//*[@data-phone]/@data-phone",
            ".//*[contains(@class, 'tAd8D')]//text()"
        ],
        
        'website': [
            ".//a[starts-with(@href, 'http') and not(contains(@href, 'google.com'))]/@href",
            ".//*[@data-href]/@data-href"
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
                source="google_maps",
                source_url=source_url,
                raw_data={
                    'html': str(card),
                    'parser': 'google_map_parser'
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
                    # Try to get text from span or direct text
                    name = element.get_text(strip=True)
                    if name and len(name) > 1:
                        return name
            except Exception:
                continue
        
        # Fallback to any heading or prominent text
        try:
            for tag in ['h1', 'h2', 'h3', 'h4']:
                element = card.find(tag)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:
                        return text
            
            # Look for clickable business names
            links = card.find_all('a')
            for link in links:
                if link.get('href', '').startswith('/maps/'):
                    text = link.get_text(strip=True)
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
                    # Check if it looks like an address
                    if address and self._looks_like_address(address):
                        return address
            except Exception:
                continue
        
        # Look for address patterns in all text
        text = card.get_text()
        address_patterns = [
            r'\d+\s+[A-Za-z\s,\.-]+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd|Way|Pkwy|Plaza|Pl)[^·]*',
            r'[A-Za-z\s,\.-]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?',
            r'\d+[^,·]*,[^,·]*,[A-Z]{2}(?:\s*\d{5})?'
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                address = match.group().strip()
                if self._looks_like_address(address):
                    return address
        
        return None
    
    def _extract_phone(self, card: Tag) -> Optional[str]:
        """Extract phone number from card."""
        # Check tel: links first
        tel_link = card.find('a', href=re.compile(r'^tel:'))
        if tel_link:
            phone = tel_link.get('href').replace('tel:', '')
            return self._clean_phone(phone)
        
        # Check data-phone attributes
        phone_element = card.find(attrs={'data-phone': True})
        if phone_element:
            phone = phone_element.get('data-phone')
            if self._is_valid_phone(phone):
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
            r'\+1[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{4}',
            r'\d{3}\.\d{3}\.\d{4}'
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
        # Check data-href attributes first
        data_href_element = card.find(attrs={'data-href': True})
        if data_href_element:
            url = data_href_element.get('data-href')
            if url and self._is_valid_website(url):
                return url
        
        # Try CSS selectors
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
                    # Get rating text
                    rating_text = element.get_text(strip=True)
                    
                    # Check aria-label for rating info
                    aria_label = element.get('aria-label', '')
                    if aria_label:
                        rating_text = f"{rating_text} {aria_label}"
                    
                    # Look for star ratings with review count
                    star_pattern = r'(\d+(?:\.\d+)?)\s*(?:stars?|★)[\s·]*(\d+)\s*reviews?'
                    match = re.search(star_pattern, rating_text, re.IGNORECASE)
                    if match:
                        score = float(match.group(1))
                        review_count = int(match.group(2))
                        return BusinessRating(
                            score=score,
                            max_score=5.0,
                            review_count=review_count,
                            source="google_maps"
                        )
                    
                    # Look for simple rating
                    rating_match = re.search(r'(\d+(?:\.\d+))', rating_text)
                    if rating_match:
                        score = float(rating_match.group(1))
                        if 0 <= score <= 5:
                            # Look for review count separately
                            review_match = re.search(r'(\d+)\s*(?:reviews?|ratings?)', rating_text, re.IGNORECASE)
                            review_count = int(review_match.group(1)) if review_match else None
                            
                            return BusinessRating(
                                score=score,
                                max_score=5.0,
                                review_count=review_count,
                                source="google_maps"
                            )
            except Exception:
                continue
        
        # Look for rating patterns in all text
        text = card.get_text()
        rating_patterns = [
            r'(\d+(?:\.\d+)?)\s*★.*?(\d+)\s*reviews?',
            r'(\d+(?:\.\d+)?)\s*stars?[\s·]*(\d+)\s*reviews?',
            r'(\d+(?:\.\d+)?)\s*out of 5.*?(\d+)\s*reviews?',
            r'Rating:\s*(\d+(?:\.\d+)?)',
            r'Rated\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                review_count = int(match.group(2)) if len(match.groups()) > 1 else None
                return BusinessRating(
                    score=score,
                    max_score=5.0,
                    review_count=review_count,
                    source="google_maps"
                )
        
        return None
    
    def _extract_hours(self, card: Tag) -> Optional[BusinessHours]:
        """Extract business hours from card."""
        for selector in self.SELECTORS['hours']:
            try:
                element = card.select_one(selector)
                if element:
                    hours_text = element.get_text(strip=True)
                    if hours_text and any(day in hours_text.lower() for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'open', 'closed']):
                        return BusinessHours.from_text(hours_text)
            except Exception:
                continue
        
        # Look for hours patterns in text
        text = card.get_text()
        hours_patterns = [
            r'Open\s+(?:24 hours|all day|\d+(?::\d+)?\s*(?:AM|PM))',
            r'(?:Mon|Monday).*?(?:Sun|Sunday).*?\d+(?::\d+)?\s*(?:AM|PM)',
            r'Hours:.*?\d+(?::\d+)?\s*(?:AM|PM)',
            r'(?:Opens|Closes)\s+at\s+\d+(?::\d+)?\s*(?:AM|PM)'
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
                    # Filter out addresses and other non-category text
                    if category and not self._looks_like_address(category) and '·' not in category:
                        # Check if it's a valid category (not too long, not a sentence)
                        if len(category) < 50 and not category.endswith('.'):
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
                    if description and len(description) > 20 and len(description) < 500:
                        # Make sure it's not an address or phone
                        if not self._looks_like_address(description) and not self._is_valid_phone(description):
                            return description
            except Exception:
                continue
        
        return None
    
    def _get_element_position(self, element: Tag) -> str:
        """Get unique position identifier for element."""
        # Create position identifier based on tag and attributes
        attrs = element.attrs or {}
        position_attrs = ['data-result-index', 'data-cid', 'id', 'class']
        
        position_parts = [element.name]
        for attr in position_attrs:
            if attr in attrs:
                value = attrs[attr]
                if isinstance(value, list):
                    value = ' '.join(value)
                position_parts.append(f"{attr}:{value}")
        
        return "|".join(position_parts)
    
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
    
    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number."""
        # Remove common prefixes and clean
        phone = re.sub(r'tel:', '', phone, flags=re.IGNORECASE)
        phone = re.sub(r'[^\d+\-\(\)\s\.]', '', phone)
        return phone.strip()
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Check if phone number looks valid."""
        if not phone:
            return False
        digits = re.sub(r'[^\d]', '', phone)
        return 10 <= len(digits) <= 15
    
    def _is_valid_website(self, url: str) -> bool:
        """Check if URL is a valid business website."""
        if not url or not isinstance(url, str):
            return False
        
        # Skip internal Google URLs
        google_domains = ['google.com', 'googleusercontent.com', 'gstatic.com', 'googleapis.com']
        for domain in google_domains:
            if domain in url.lower():
                return False
        
        # Must be HTTP/HTTPS
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Basic URL validation
        return bool(re.match(r'https?://[^\s<>"{}|\\^`\[\]]+', url))