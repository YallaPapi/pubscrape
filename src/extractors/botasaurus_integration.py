#!/usr/bin/env python3
"""
Botasaurus Integration for JavaScript-Rendered Pages
Handles SPA and dynamically loaded content for email extraction
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from botasaurus import browser, Wait
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    print("Botasaurus not available. Install with: pip install botasaurus")

from .email_patterns import extract_emails_comprehensive, analyze_contact_forms


@dataclass
class JavaScriptExtractionResult:
    """Result of JavaScript-based extraction"""
    url: str
    emails: List[Dict[str, Any]]
    phones: List[Dict[str, Any]]
    forms: List[Dict[str, Any]]
    business_name: str
    page_source: str
    extraction_time: float
    javascript_detected: bool
    success: bool
    error_message: str = ""


class BotasaurusEmailExtractor:
    """
    Email extractor that handles JavaScript-rendered pages using Botasaurus
    """
    
    def __init__(self, 
                 headless: bool = True,
                 wait_time: int = 5,
                 enable_images: bool = False,
                 enable_css: bool = False):
        
        self.headless = headless
        self.wait_time = wait_time
        self.enable_images = enable_images
        self.enable_css = enable_css
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        if not BOTASAURUS_AVAILABLE:
            self.logger.warning("Botasaurus not available. JavaScript extraction disabled.")
        
        # Phone patterns
        import re
        self.phone_patterns = [
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})\.([0-9]{3})\.([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})-([0-9]{3})-([0-9]{4})\b'),
        ]
    
    def extract_from_js_page(self, url: str) -> JavaScriptExtractionResult:
        """
        Extract emails from JavaScript-rendered page
        
        Args:
            url: URL to extract from
            
        Returns:
            JavaScriptExtractionResult with extracted data
        """
        start_time = time.time()
        
        if not BOTASAURUS_AVAILABLE:
            return JavaScriptExtractionResult(
                url=url,
                emails=[],
                phones=[],
                forms=[],
                business_name="",
                page_source="",
                extraction_time=time.time() - start_time,
                javascript_detected=False,
                success=False,
                error_message="Botasaurus not available"
            )
        
        try:
            result = self._extract_with_browser(url)
            result.extraction_time = time.time() - start_time
            return result
            
        except Exception as e:
            error_msg = f"JavaScript extraction failed for {url}: {str(e)}"
            self.logger.error(error_msg)
            
            return JavaScriptExtractionResult(
                url=url,
                emails=[],
                phones=[],
                forms=[],
                business_name="",
                page_source="",
                extraction_time=time.time() - start_time,
                javascript_detected=True,
                success=False,
                error_message=error_msg
            )
    
    def _extract_with_browser(self, url: str) -> JavaScriptExtractionResult:
        """Internal browser-based extraction method"""
        
        @browser(
            headless=self.headless,
            block_images=not self.enable_images,
            block_resources=['stylesheet'] if not self.enable_css else []
        )
        def extract_page_content(driver, target_url):
            """Browser function to extract page content"""
            try:
                # Navigate to page
                driver.get(target_url)
                
                # Wait for initial load
                Wait.for_non_empty_text('body', timeout=self.wait_time)
                
                # Check for common JavaScript frameworks
                js_indicators = self._detect_javascript_frameworks(driver)
                
                # Additional wait for SPAs
                if js_indicators['is_spa']:
                    time.sleep(3)
                    
                    # Try to trigger any lazy loading
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, 0);")
                
                # Wait for contact information to potentially load
                self._wait_for_contact_elements(driver)
                
                # Get final page source
                page_source = driver.page_source
                
                # Extract page title for business name
                try:
                    page_title = driver.title
                except:
                    page_title = ""
                
                return {
                    'page_source': page_source,
                    'page_title': page_title,
                    'javascript_detected': js_indicators['detected'],
                    'is_spa': js_indicators['is_spa'],
                    'frameworks': js_indicators['frameworks']
                }
                
            except Exception as e:
                return {
                    'error': str(e),
                    'page_source': '',
                    'page_title': '',
                    'javascript_detected': False,
                    'is_spa': False,
                    'frameworks': []
                }
        
        # Execute browser extraction
        browser_result = extract_page_content(url)
        
        if 'error' in browser_result:
            raise Exception(browser_result['error'])
        
        # Process extracted content
        page_source = browser_result['page_source']
        page_title = browser_result['page_title']
        
        # Extract emails using comprehensive patterns
        emails = extract_emails_comprehensive(page_source, page_source)
        
        # Extract phone numbers
        phones = self._extract_phone_numbers(page_source)
        
        # Analyze contact forms
        forms = analyze_contact_forms(page_source)
        
        # Extract business name
        business_name = self._extract_business_name_from_title(page_title, url)
        
        return JavaScriptExtractionResult(
            url=url,
            emails=emails,
            phones=phones,
            forms=forms,
            business_name=business_name,
            page_source=page_source[:10000],  # Limit size
            extraction_time=0.0,  # Will be set by caller
            javascript_detected=browser_result['javascript_detected'],
            success=True
        )
    
    def _detect_javascript_frameworks(self, driver) -> Dict[str, Any]:
        """Detect JavaScript frameworks and SPA indicators"""
        try:
            # Check for common framework indicators
            react_check = driver.execute_script("return window.React !== undefined;")
            vue_check = driver.execute_script("return window.Vue !== undefined;")
            angular_check = driver.execute_script("return window.angular !== undefined || window.ng !== undefined;")
            
            # Check for SPA indicators
            spa_indicators = driver.execute_script("""
                return {
                    hasRouter: window.history && window.history.pushState,
                    hasShadowDOM: document.head.querySelector('base[href]') !== null,
                    dynamicContent: document.querySelectorAll('[data-react-root], [ng-app], [v-app]').length > 0
                };
            """)
            
            frameworks = []
            if react_check:
                frameworks.append('React')
            if vue_check:
                frameworks.append('Vue')
            if angular_check:
                frameworks.append('Angular')
            
            is_spa = (spa_indicators['hasRouter'] or 
                     spa_indicators['dynamicContent'] or 
                     len(frameworks) > 0)
            
            return {
                'detected': len(frameworks) > 0 or is_spa,
                'is_spa': is_spa,
                'frameworks': frameworks
            }
            
        except Exception as e:
            self.logger.warning(f"Error detecting JavaScript frameworks: {e}")
            return {
                'detected': False,
                'is_spa': False,
                'frameworks': []
            }
    
    def _wait_for_contact_elements(self, driver, timeout: int = 5):
        """Wait for contact elements to load"""
        try:
            # Common selectors for contact information
            contact_selectors = [
                "[href*='mailto:']",
                "[href*='tel:']",
                ".contact",
                ".email",
                ".phone",
                "form[action*='contact']",
                "input[type='email']"
            ]
            
            for selector in contact_selectors:
                try:
                    Wait.for_element(selector, timeout=2)
                    self.logger.debug(f"Found contact element: {selector}")
                    break
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"No specific contact elements found: {e}")
    
    def _extract_phone_numbers(self, text_content: str) -> List[Dict[str, Any]]:
        """Extract phone numbers from text content"""
        found_phones = []
        
        for pattern in self.phone_patterns:
            matches = pattern.finditer(text_content)
            for match in matches:
                if len(match.groups()) >= 3:
                    area_code, exchange, number = match.groups()[:3]
                    phone = f"({area_code}) {exchange}-{number}"
                    
                    # Get context
                    start = max(0, match.start() - 30)
                    end = min(len(text_content), match.end() + 30)
                    context = text_content[start:end].strip()
                    
                    found_phones.append({
                        'phone': phone,
                        'context': context,
                        'confidence': 0.8,
                        'source': 'javascript_page'
                    })
        
        return found_phones
    
    def _extract_business_name_from_title(self, page_title: str, url: str) -> str:
        """Extract business name from page title"""
        if not page_title:
            # Fallback to domain name
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            return domain.split('.')[0].title()
        
        # Clean up title
        import re
        title = re.sub(r'\s*[|-].*$', '', page_title)
        title = re.sub(r'\s*-\s*(Home|Contact|About).*$', '', title, re.IGNORECASE)
        
        return title.strip() if title else "Unknown Business"
    
    def is_javascript_page(self, url: str) -> bool:
        """
        Quick check if a page likely needs JavaScript rendering
        
        Args:
            url: URL to check
            
        Returns:
            True if page likely needs JavaScript rendering
        """
        if not BOTASAURUS_AVAILABLE:
            return False
        
        try:
            import requests
            
            # Quick HEAD request to check response
            response = requests.head(url, timeout=5)
            content_type = response.headers.get('content-type', '').lower()
            
            # Check for SPA indicators in URL
            spa_indicators = [
                '#/', '#!/', '/app/', '/spa/', 'react', 'vue', 'angular'
            ]
            
            if any(indicator in url.lower() for indicator in spa_indicators):
                return True
            
            # Check content type
            if 'application/json' in content_type:
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking if JavaScript page: {e}")
            return False


def test_botasaurus_integration():
    """Test Botasaurus integration"""
    print("Testing Botasaurus Integration")
    print("=" * 40)
    
    if not BOTASAURUS_AVAILABLE:
        print("❌ Botasaurus not available. Install with: pip install botasaurus")
        return False
    
    extractor = BotasaurusEmailExtractor(headless=True)
    
    # Test URLs that might have JavaScript content
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTesting URL {i}: {url}")
        print("-" * 30)
        
        # Check if JavaScript needed
        needs_js = extractor.is_javascript_page(url)
        print(f"Needs JavaScript: {needs_js}")
        
        # Extract content
        result = extractor.extract_from_js_page(url)
        
        print(f"Success: {result.success}")
        print(f"Business Name: {result.business_name}")
        print(f"Emails Found: {len(result.emails)}")
        print(f"Phones Found: {len(result.phones)}")
        print(f"Forms Found: {len(result.forms)}")
        print(f"JavaScript Detected: {result.javascript_detected}")
        print(f"Extraction Time: {result.extraction_time:.2f}s")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
        # Show sample emails
        for email in result.emails[:3]:
            print(f"  Email: {email['email']} (pattern: {email.get('pattern', 'unknown')})")
    
    return True


if __name__ == "__main__":
    test_botasaurus_integration()