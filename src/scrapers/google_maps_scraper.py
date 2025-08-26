from botasaurus.browser import browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException
)
from typing import List, Dict, Optional, Any, Set, Union
import time
import logging

from ..utils.exceptions import ScrapingError, BrowserError, ValidationError

logger = logging.getLogger(__name__)

# Constants for better maintainability
DEFAULT_TIMEOUT = 10
SCROLL_AMOUNT = 700
SCROLL_DELAY = 0.7
MAX_SCROLL_ITERATIONS = 8
GOOGLE_MAPS_URL = "https://www.google.com/maps"


@browser(headless=True, block_images=True, window_size=(1280, 800))
def scrape_google_maps_businesses(
    driver: WebDriver, 
    search_query: str, 
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    Visit Google Maps and extract real businesses for the given search query.
    
    This function performs a comprehensive search on Google Maps, extracting
    business information including names, addresses, phone numbers, and websites.
    It implements intelligent scrolling and data deduplication.
    
    Args:
        driver: Selenium WebDriver instance for browser automation
        search_query: The search term to find businesses (e.g., "restaurants in NYC")
        max_results: Maximum number of business records to return (default: 100)
        
    Returns:
        List[Dict[str, Any]]: List of business data dictionaries containing:
            - name: Business name
            - address: Business address
            - phone: Phone number (if available)
            - website: Website URL (if available)
            - source: Always "google_maps"
            
    Raises:
        ValidationError: When search_query is invalid or empty
        BrowserError: When browser navigation or element interaction fails
        ScrapingError: When the scraping process fails
        
    Example:
        >>> businesses = scrape_google_maps_businesses(driver, "coffee shops NYC", 50)
        >>> print(len(businesses))  # Up to 50 coffee shop records
        >>> print(businesses[0]['name'])  # "Starbucks Coffee"
    """
    if not _validate_search_query(search_query):
        raise ValidationError("Search query cannot be empty or invalid", field_name="search_query")
        
    if max_results <= 0:
        raise ValidationError("max_results must be greater than 0", field_name="max_results", field_value=str(max_results))

    try:
        # Navigate to Google Maps
        driver.get(GOOGLE_MAPS_URL)
        
        # Wait for and interact with search box
        _perform_search(driver, search_query)
        
        # Extract business data with scrolling
        businesses = _extract_all_businesses(driver, max_results)
        
        logger.info(f"Successfully extracted {len(businesses)} businesses for query: {search_query}")
        return businesses
        
    except (TimeoutException, WebDriverException) as e:
        raise BrowserError(f"Browser operation failed during Maps scraping: {str(e)}", browser_type="selenium")
    except Exception as e:
        raise ScrapingError(f"Google Maps scraping failed: {str(e)}", url=GOOGLE_MAPS_URL)


def _validate_search_query(query: str) -> bool:
    """
    Validate the search query input.
    
    Args:
        query: Search query string to validate
        
    Returns:
        bool: True if query is valid, False otherwise
    """
    return bool(query and isinstance(query, str) and query.strip())


def _perform_search(driver: WebDriver, search_query: str) -> None:
    """
    Perform search operation on Google Maps.
    
    Args:
        driver: Selenium WebDriver instance
        search_query: Query to search for
        
    Raises:
        BrowserError: When search interaction fails
    """
    try:
        # Wait for search box to be present
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
    except TimeoutException:
        raise BrowserError("Search box not found on Google Maps", element_selector="#searchboxinput")

    try:
        # Perform search
        search_box = driver.find_element(By.ID, "searchboxinput")
        search_box.clear()
        search_box.send_keys(search_query + "\n")
    except NoSuchElementException:
        raise BrowserError("Could not interact with search box", element_selector="#searchboxinput")


def _extract_all_businesses(driver: WebDriver, max_results: int) -> List[Dict[str, Any]]:
    """
    Extract all business data with intelligent scrolling and deduplication.
    
    Args:
        driver: Selenium WebDriver instance
        max_results: Maximum number of businesses to extract
        
    Returns:
        List[Dict[str, Any]]: List of business data records
    """
    businesses: List[Dict[str, Any]] = []
    cards_seen: Set[Union[str, int]] = set()
    
    for iteration in range(MAX_SCROLL_ITERATIONS):
        try:
            result_cards = _find_business_cards(driver)
            new_businesses_found = False
            
            for card in result_cards:
                card_id = _get_card_identifier(card)
                
                if card_id in cards_seen:
                    continue
                    
                business_data = _extract_business_data(card)
                if business_data:
                    businesses.append(business_data)
                    cards_seen.add(card_id)
                    new_businesses_found = True
                    
                    if len(businesses) >= max_results:
                        return businesses
            
            # If no new businesses found, stop scrolling
            if not new_businesses_found:
                logger.info(f"No new businesses found after iteration {iteration + 1}")
                break
                
            # Scroll to load more results
            _scroll_for_more_results(driver)
            
        except Exception as e:
            logger.warning(f"Error during business extraction iteration {iteration + 1}: {str(e)}")
            continue
    
    return businesses


def _find_business_cards(driver: WebDriver) -> List[WebElement]:
    """
    Find all business card elements on the current page.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        List[WebElement]: List of business card web elements
    """
    selectors = [
        "[data-result-index]",
        "div.Nv2PK", 
        "a.hfpxzc"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
        except NoSuchElementException:
            continue
    
    return []


def _get_card_identifier(card: WebElement) -> Union[str, int]:
    """
    Get a unique identifier for a business card element.
    
    Args:
        card: WebElement representing a business card
        
    Returns:
        Union[str, int]: Unique identifier for the card
    """
    identifiers = [
        card.get_attribute("data-result-index"),
        card.get_attribute("data-cid"),
        card.get_attribute("href"),
    ]
    
    for identifier in identifiers:
        if identifier:
            return identifier
    
    # Fallback to element ID
    return id(card)


def _extract_business_data(card: WebElement) -> Optional[Dict[str, Any]]:
    """
    Extract comprehensive business data from a business card element.
    
    Args:
        card: WebElement containing business information
        
    Returns:
        Optional[Dict[str, Any]]: Business data dictionary or None if extraction fails
    """
    try:
        # Extract business name (required field)
        name = _extract_business_name(card)
        if not name:
            return None
        
        # Extract optional fields
        address = _extract_business_address(card)
        phone = _extract_business_phone(card)
        website = _extract_business_website(card)
        
        return {
            'name': name,
            'address': address,
            'phone': phone,
            'website': website,
            'source': 'google_maps'
        }
    except Exception as e:
        logger.warning(f"Failed to extract business data: {str(e)}")
        return None


def _extract_business_name(card: WebElement) -> Optional[str]:
    """
    Extract business name from card element.
    
    Args:
        card: WebElement containing business information
        
    Returns:
        Optional[str]: Business name or None if not found
    """
    name_selectors = [
        '[data-value="title"]',
        'div[class*="fontHeadline"]',
        'h3, h2, h1',
        '.qBF1Pd.fontHeadlineSmall',
    ]
    
    for selector in name_selectors:
        text = _get_element_text(card, selector)
        if text:
            return text
    
    return None


def _extract_business_address(card: WebElement) -> Optional[str]:
    """
    Extract business address from card element.
    
    Args:
        card: WebElement containing business information
        
    Returns:
        Optional[str]: Business address or None if not found
    """
    address_selectors = [
        '[data-value="address"]',
        'span[class*="address"]',
        'div[class*="address"]',
        '.W4Efsd'
    ]
    
    for selector in address_selectors:
        address = _get_element_text(card, selector)
        if address:
            return address
    
    return None


def _extract_business_phone(card: WebElement) -> Optional[str]:
    """
    Extract business phone number from card element.
    
    Args:
        card: WebElement containing business information
        
    Returns:
        Optional[str]: Phone number or None if not found
    """
    try:
        phone_element = card.find_element(By.CSS_SELECTOR, 'a[href^="tel:"]')
        phone_href = phone_element.get_attribute('href')
        if phone_href:
            return phone_href.replace('tel:', '').strip()
    except NoSuchElementException:
        pass
    
    return None


def _extract_business_website(card: WebElement) -> Optional[str]:
    """
    Extract business website from card element.
    
    Args:
        card: WebElement containing business information
        
    Returns:
        Optional[str]: Website URL or None if not found
    """
    website_selectors = [
        'a[data-value="website"]',
        'a[href^="http"]:not([href*="google"])'
    ]
    
    for selector in website_selectors:
        try:
            website_element = card.find_element(By.CSS_SELECTOR, selector)
            href = website_element.get_attribute('href')
            if href and 'google.' not in href:
                return href
        except NoSuchElementException:
            continue
    
    return None


def _get_element_text(parent: WebElement, selector: str) -> Optional[str]:
    """
    Safely extract text from an element using CSS selector.
    
    Args:
        parent: Parent WebElement to search within
        selector: CSS selector for the target element
        
    Returns:
        Optional[str]: Element text content or None if not found/empty
    """
    try:
        element = parent.find_element(By.CSS_SELECTOR, selector)
        text = element.text.strip()
        return text if text else None
    except NoSuchElementException:
        return None


def _scroll_for_more_results(driver: WebDriver) -> None:
    """
    Scroll the page to load more business results.
    
    Args:
        driver: Selenium WebDriver instance
    """
    driver.execute_script(f"window.scrollBy(0, {SCROLL_AMOUNT})")
    time.sleep(SCROLL_DELAY)
