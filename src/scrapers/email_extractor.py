from botasaurus.browser import browser
import re
from typing import Optional, List, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    WebDriverException
)

from ..utils.exceptions import ScrapingError, BrowserError, ValidationError


@browser(headless=True, block_images=True)
def extract_emails_from_website(driver: WebDriver, website_url: str) -> Optional[str]:
    """
    Visit website and extract a likely business email address.
    
    This function navigates to a website and attempts to find business email
    addresses by checking contact/about pages and extracting email patterns
    from the page source.
    
    Args:
        driver: Selenium WebDriver instance for browser automation
        website_url: The URL of the website to scrape for emails
        
    Returns:
        str or None: The most relevant business email found, or None if no valid emails
        
    Raises:
        ValidationError: When website_url is invalid or malformed
        BrowserError: When browser navigation or element interaction fails
        ScrapingError: When email extraction process fails
        
    Example:
        >>> email = extract_emails_from_website(driver, "https://example.com")
        >>> print(email)  # "contact@example.com"
    """
    if not _validate_url(website_url):
        raise ValidationError("Invalid or malformed website URL", field_name="website_url", field_value=website_url)
    
    try:
        driver.get(website_url)
        
        # Try to navigate to contact/about pages for better email discovery
        _try_navigate_to_contact_pages(driver)
        
        # Extract and filter emails from page content
        page_html = driver.page_source
        emails = _extract_emails_from_html(page_html)
        filtered_emails = _filter_valid_emails(emails)
        
        # Return best email based on business relevance
        return _select_best_email(filtered_emails)
        
    except (TimeoutException, WebDriverException) as e:
        raise BrowserError(f"Browser operation failed: {str(e)}", browser_type="selenium", context={"url": website_url})
    except Exception as e:
        raise ScrapingError(f"Email extraction failed: {str(e)}", url=website_url)


def _validate_url(url: str) -> bool:
    """
    Validate if the provided URL is properly formatted.
    
    Args:
        url: URL string to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    return bool(url and isinstance(url, str) and url.startswith(("http://", "https://")))


def _try_navigate_to_contact_pages(driver: WebDriver) -> None:
    """
    Attempt to navigate to contact or about pages for better email discovery.
    
    Args:
        driver: Selenium WebDriver instance
        
    Raises:
        BrowserError: When navigation fails due to browser issues
    """
    contact_selectors = [
        "a[href*='contact']",
        "a[href*='about']", 
        "a:contains('Contact')",
        "a:contains('About')",
    ]
    
    for selector in contact_selectors:
        try:
            link = driver.find_element("css selector", selector)
            link.click()
            break
        except NoSuchElementException:
            continue
        except WebDriverException as e:
            raise BrowserError(f"Failed to click contact link: {str(e)}", element_selector=selector)


def _extract_emails_from_html(html_content: str) -> List[str]:
    """
    Extract all email addresses from HTML content using regex pattern.
    
    Args:
        html_content: HTML source code to search for emails
        
    Returns:
        List[str]: List of email addresses found in the HTML
    """
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    return re.findall(email_pattern, html_content)


def _filter_valid_emails(emails: List[str]) -> List[str]:
    """
    Filter out test, example, and invalid email addresses.
    
    Args:
        emails: List of email addresses to filter
        
    Returns:
        List[str]: Filtered list of potentially valid business emails
    """
    excluded_keywords = ['example', 'test', 'demo', 'noreply', 'no-reply', 'donotreply']
    return [
        email.lower() for email in emails 
        if not any(keyword in email.lower() for keyword in excluded_keywords)
    ]


def _select_best_email(emails: List[str]) -> Optional[str]:
    """
    Select the most relevant business email from the filtered list.
    
    Prioritizes emails with business-oriented prefixes like info@, contact@, etc.
    
    Args:
        emails: List of filtered email addresses
        
    Returns:
        str or None: The best business email found, or None if no emails available
    """
    if not emails:
        return None
        
    # Prioritize business-oriented email prefixes
    preferred_prefixes = ("info@", "contact@", "sales@", "support@", "hello@", "admin@")
    
    for email in emails:
        if email.startswith(preferred_prefixes):
            return email
            
    # Return first available email if no preferred prefix found
    return emails[0]
