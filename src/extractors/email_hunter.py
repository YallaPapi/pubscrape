#!/usr/bin/env python3
"""
Email Hunter - Main Email Extraction Logic
Comprehensive email discovery system with intelligent website navigation
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

from .email_patterns import extract_emails_comprehensive, analyze_contact_forms
from .website_navigator import WebsiteNavigator


@dataclass
class EmailHuntResult:
    """Result of email hunting operation"""
    url: str
    business_name: str = ""
    emails: List[Dict[str, Any]] = field(default_factory=list)
    phones: List[Dict[str, Any]] = field(default_factory=list)
    contact_forms: List[Dict[str, Any]] = field(default_factory=list)
    social_profiles: List[str] = field(default_factory=list)
    
    # Navigation data
    pages_visited: List[str] = field(default_factory=list)
    contact_pages_found: List[str] = field(default_factory=list)
    
    # Quality metrics
    overall_score: float = 0.0
    confidence: float = 0.0
    is_actionable: bool = False
    
    # Performance metrics
    extraction_time: float = 0.0
    pages_processed: int = 0
    javascript_pages: int = 0
    
    # Metadata
    extraction_timestamp: float = field(default_factory=time.time)
    extraction_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'url': self.url,
            'business_name': self.business_name,
            'emails': self.emails,
            'phones': self.phones,
            'contact_forms': self.contact_forms,
            'social_profiles': self.social_profiles,
            'pages_visited': self.pages_visited,
            'contact_pages_found': self.contact_pages_found,
            'overall_score': self.overall_score,
            'confidence': self.confidence,
            'is_actionable': self.is_actionable,
            'extraction_time': self.extraction_time,
            'pages_processed': self.pages_processed,
            'javascript_pages': self.javascript_pages,
            'extraction_timestamp': self.extraction_timestamp,
            'extraction_errors': self.extraction_errors
        }


class EmailHunter:
    """
    Comprehensive email hunting system with intelligent navigation
    and multi-method extraction
    """
    
    def __init__(self, 
                 timeout: int = 10,
                 max_pages: int = 5,
                 use_javascript: bool = True,
                 enable_contact_forms: bool = True):
        
        self.timeout = timeout
        self.max_pages = max_pages
        self.use_javascript = use_javascript
        self.enable_contact_forms = enable_contact_forms
        
        # Initialize components
        self.navigator = WebsiteNavigator(timeout=timeout)
        
        # Import EmailScorer here to avoid circular imports
        try:
            from ..scoring.email_scorer import EmailScorer
            self.scorer = EmailScorer()
        except ImportError:
            # Fallback if scoring package not available
            self.scorer = None
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Phone extraction patterns
        self.phone_patterns = [
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})\.([0-9]{3})\.([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})-([0-9]{3})-([0-9]{4})\b'),
            re.compile(r'\b\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}\b'),
        ]
        
        # Social media patterns
        self.social_patterns = {
            'facebook': re.compile(r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+', re.IGNORECASE),
            'twitter': re.compile(r'https?://(?:www\.)?twitter\.com/[a-zA-Z0-9._-]+', re.IGNORECASE),
            'linkedin': re.compile(r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9._-]+', re.IGNORECASE),
            'instagram': re.compile(r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._-]+', re.IGNORECASE),
            'youtube': re.compile(r'https?://(?:www\.)?youtube\.com/(?:c|channel|user)/[a-zA-Z0-9._-]+', re.IGNORECASE),
        }
    
    def hunt_emails(self, url: str) -> EmailHuntResult:
        """
        Main email hunting method - comprehensive extraction from website
        
        Args:
            url: Website URL to hunt emails from
            
        Returns:
            EmailHuntResult with all discovered information
        """
        start_time = time.time()
        result = EmailHuntResult(url=url)
        
        try:
            self.logger.info(f"Starting email hunt for: {url}")
            
            # Step 1: Navigate and discover contact pages
            navigation_result = self.navigator.discover_contact_pages(url, max_pages=self.max_pages)
            result.pages_visited = navigation_result.get('pages_visited', [])
            result.contact_pages_found = navigation_result.get('contact_pages', [])
            
            # Step 2: Extract from all discovered pages
            all_emails = []
            all_phones = []
            all_forms = []
            all_social = []
            
            # Always process the main page first
            pages_to_process = [url] + [page for page in result.contact_pages_found if page != url]
            
            for page_url in pages_to_process[:self.max_pages]:
                try:
                    self.logger.info(f"Processing page: {page_url}")
                    
                    # Extract from this page
                    page_result = self._extract_from_page(page_url)
                    
                    if page_result:
                        # Merge results
                        all_emails.extend(page_result.get('emails', []))
                        all_phones.extend(page_result.get('phones', []))
                        all_forms.extend(page_result.get('forms', []))
                        all_social.extend(page_result.get('social', []))
                        
                        # Update business name if not found yet
                        if not result.business_name and page_result.get('business_name'):
                            result.business_name = page_result['business_name']
                        
                        result.pages_processed += 1
                        if page_result.get('is_javascript'):
                            result.javascript_pages += 1
                    
                except Exception as e:
                    error_msg = f"Error processing page {page_url}: {str(e)}"
                    self.logger.error(error_msg)
                    result.extraction_errors.append(error_msg)
                
                # Rate limiting
                time.sleep(1)
            
            # Step 3: Deduplicate and score results
            result.emails = self._deduplicate_and_score_emails(all_emails)
            result.phones = self._deduplicate_phones(all_phones)
            result.contact_forms = all_forms
            result.social_profiles = list(set(all_social))
            
            # Step 4: Calculate quality metrics
            result.overall_score = self._calculate_overall_score(result)
            result.confidence = self._calculate_confidence(result)
            result.is_actionable = self._is_actionable_result(result)
            
            result.extraction_time = time.time() - start_time
            
            self.logger.info(f"Email hunt completed for {url}: "
                           f"{len(result.emails)} emails, "
                           f"{len(result.phones)} phones, "
                           f"{len(result.contact_forms)} forms, "
                           f"score: {result.overall_score:.2f}")
            
        except Exception as e:
            error_msg = f"Email hunt failed for {url}: {str(e)}"
            self.logger.error(error_msg)
            result.extraction_errors.append(error_msg)
            result.extraction_time = time.time() - start_time
        
        return result
    
    def _extract_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract all information from a single page"""
        try:
            # Fetch page content
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text()
            html_content = response.text
            
            # Check if JavaScript rendering needed
            is_javascript = self._needs_javascript_rendering(soup, text_content)
            
            # If JavaScript needed and enabled, try Botasaurus
            if is_javascript and self.use_javascript:
                js_result = self._extract_with_javascript(url)
                if js_result:
                    return js_result
            
            # Standard extraction
            result = {
                'business_name': self._extract_business_name(soup, url),
                'emails': [],
                'phones': [],
                'forms': [],
                'social': [],
                'is_javascript': is_javascript
            }
            
            # Extract emails using comprehensive patterns
            emails = extract_emails_comprehensive(text_content, html_content)
            result['emails'] = emails
            
            # Extract phone numbers
            phones = self._extract_phone_numbers(text_content)
            result['phones'] = phones
            
            # Extract contact forms if enabled
            if self.enable_contact_forms:
                forms = analyze_contact_forms(html_content)
                result['forms'] = forms
            
            # Extract social profiles
            social = self._extract_social_profiles(soup)
            result['social'] = social
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting from page {url}: {e}")
            return None
    
    def _needs_javascript_rendering(self, soup: BeautifulSoup, text_content: str) -> bool:
        """Determine if page needs JavaScript rendering"""
        # Check for React/Vue/Angular indicators
        js_indicators = [
            'data-react', 'ng-app', 'ng-controller', 'v-app', 'vue-app',
            '__NUXT__', '__NEXT_DATA__', 'angular.module'
        ]
        
        html_str = str(soup)
        if any(indicator in html_str for indicator in js_indicators):
            return True
        
        # Check for minimal content (possible SPA)
        if len(text_content.strip()) < 500:
            return True
        
        # Check for heavy JavaScript usage
        script_tags = soup.find_all('script')
        if len(script_tags) > 10:
            return True
        
        return False
    
    def _extract_with_javascript(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract using JavaScript rendering (Botasaurus integration)"""
        try:
            # Import Botasaurus if available
            from botasaurus import browser
            
            @browser
            def extract_js_page(driver, url):
                driver.get(url)
                
                # Wait for content to load
                time.sleep(3)
                
                # Get page source after JavaScript execution
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text()
                
                return {
                    'html': html_content,
                    'text': text_content,
                    'soup': soup
                }
            
            # Execute JavaScript extraction
            js_data = extract_js_page(url)
            
            if js_data:
                result = {
                    'business_name': self._extract_business_name(js_data['soup'], url),
                    'emails': extract_emails_comprehensive(js_data['text'], js_data['html']),
                    'phones': self._extract_phone_numbers(js_data['text']),
                    'forms': analyze_contact_forms(js_data['html']) if self.enable_contact_forms else [],
                    'social': self._extract_social_profiles(js_data['soup']),
                    'is_javascript': True
                }
                
                self.logger.info(f"Successfully extracted from JavaScript page: {url}")
                return result
            
        except ImportError:
            self.logger.warning("Botasaurus not available for JavaScript rendering")
        except Exception as e:
            self.logger.error(f"JavaScript extraction failed for {url}: {e}")
        
        return None
    
    def _extract_business_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract business name from page"""
        candidates = []
        
        # Method 1: Page title
        if soup.title:
            title = soup.title.get_text(strip=True)
            title = re.sub(r'\s*[|-].*$', '', title)
            title = re.sub(r'\s*-\s*(Home|Contact|About).*$', '', title, re.IGNORECASE)
            if title and len(title) < 100:
                candidates.append((title, 0.8))
        
        # Method 2: H1 tags
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags[:2]:
            text = h1.get_text(strip=True)
            if text and len(text) < 80 and not re.match(r'^(Contact|About|Welcome)', text, re.IGNORECASE):
                candidates.append((text, 0.7))
        
        # Method 3: Logo alt text
        logo_imgs = soup.find_all('img', alt=re.compile(r'logo', re.IGNORECASE))
        for img in logo_imgs[:2]:
            alt_text = img.get('alt', '').strip()
            if alt_text and len(alt_text) < 60 and 'logo' not in alt_text.lower():
                candidates.append((alt_text, 0.6))
        
        # Method 4: Extract from domain
        domain = urlparse(url).netloc.replace('www.', '')
        domain_name = domain.split('.')[0].replace('-', ' ').title()
        candidates.append((domain_name, 0.3))
        
        # Choose best candidate
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return "Unknown Business"
    
    def _extract_phone_numbers(self, text_content: str) -> List[Dict[str, Any]]:
        """Extract phone numbers with context"""
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
                    
                    # Score based on context
                    confidence = 0.7
                    context_lower = context.lower()
                    if any(keyword in context_lower for keyword in ['phone', 'call', 'contact', 'office', 'tel']):
                        confidence += 0.2
                    
                    found_phones.append({
                        'phone': phone,
                        'context': context,
                        'confidence': confidence,
                        'type': self._classify_phone_type(context)
                    })
        
        return found_phones
    
    def _classify_phone_type(self, context: str) -> str:
        """Classify phone number type"""
        context_lower = context.lower()
        if 'fax' in context_lower:
            return 'fax'
        elif any(keyword in context_lower for keyword in ['toll', '800', '888', '877', '866']):
            return 'toll_free'
        elif any(keyword in context_lower for keyword in ['mobile', 'cell', 'cellular']):
            return 'mobile'
        else:
            return 'office'
    
    def _extract_social_profiles(self, soup: BeautifulSoup) -> List[str]:
        """Extract social media profile links"""
        social_profiles = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            for platform, pattern in self.social_patterns.items():
                if pattern.match(href):
                    social_profiles.append(href)
                    break
        
        return list(set(social_profiles))
    
    def _deduplicate_and_score_emails(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate emails and apply scoring"""
        unique_emails = {}
        
        for email_data in emails:
            email = email_data['email']
            
            # Apply email scoring if scorer available
            if self.scorer:
                quality_score = self.scorer.score_email_quality(email)
                business_score = self.scorer.score_business_relevance(email, email_data.get('context', ''))
                combined_score = (quality_score + business_score) / 2
            else:
                # Fallback scoring based on priority and source
                quality_score = 0.5
                business_score = email_data.get('priority', 50) / 100
                combined_score = (quality_score + business_score) / 2
            
            email_data['quality_score'] = quality_score
            email_data['business_score'] = business_score
            email_data['combined_score'] = combined_score
            
            # Keep highest scoring version
            if email not in unique_emails or combined_score > unique_emails[email]['combined_score']:
                unique_emails[email] = email_data
        
        # Sort by combined score
        return sorted(unique_emails.values(), key=lambda x: x['combined_score'], reverse=True)
    
    def _deduplicate_phones(self, phones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate phone numbers"""
        unique_phones = {}
        
        for phone_data in phones:
            phone = phone_data['phone']
            if phone not in unique_phones or phone_data['confidence'] > unique_phones[phone]['confidence']:
                unique_phones[phone] = phone_data
        
        return sorted(unique_phones.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _calculate_overall_score(self, result: EmailHuntResult) -> float:
        """Calculate overall result quality score"""
        score = 0.0
        
        # Email quality (50% of score)
        if result.emails:
            best_email = max(result.emails, key=lambda x: x.get('combined_score', 0))
            score += best_email.get('combined_score', 0) * 0.5
        
        # Contact completeness (50% of score)
        if result.emails:
            score += 0.2
        if result.phones:
            score += 0.15
        if result.contact_forms:
            score += 0.1
        if result.business_name and result.business_name != 'Unknown Business':
            score += 0.05
        
        return min(1.0, score)
    
    def _calculate_confidence(self, result: EmailHuntResult) -> float:
        """Calculate extraction confidence"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on data richness
        if result.emails:
            confidence += 0.3
        if result.phones:
            confidence += 0.1
        if result.contact_forms:
            confidence += 0.05
        if result.pages_processed > 1:
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def _is_actionable_result(self, result: EmailHuntResult) -> bool:
        """Determine if result is actionable for outreach"""
        # Must have at least one email
        if not result.emails:
            return False
        
        # Must have reasonable score
        if result.overall_score < 0.4:
            return False
        
        # Must have identifiable business
        if not result.business_name or result.business_name == 'Unknown Business':
            return False
        
        return True
    
    def hunt_bulk(self, urls: List[str], 
                  progress_callback: Optional[callable] = None) -> List[EmailHuntResult]:
        """
        Hunt emails from multiple URLs with progress reporting
        
        Args:
            urls: List of URLs to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of EmailHuntResult objects
        """
        results = []
        
        for i, url in enumerate(urls):
            try:
                if progress_callback:
                    progress_callback(i, len(urls), url)
                
                result = self.hunt_emails(url)
                results.append(result)
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                error_result = EmailHuntResult(url=url)
                error_result.extraction_errors.append(f"Bulk processing error: {str(e)}")
                results.append(error_result)
        
        return results


def test_email_hunter():
    """Test the email hunter with sample URLs"""
    print("Testing Email Hunter")
    print("=" * 40)
    
    hunter = EmailHunter(max_pages=3, use_javascript=False)
    
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://www.python.org/community/",
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTesting URL {i}: {url}")
        print("-" * 30)
        
        result = hunter.hunt_emails(url)
        
        print(f"Business Name: {result.business_name}")
        print(f"Emails Found: {len(result.emails)}")
        for email in result.emails[:3]:
            print(f"  - {email['email']} (score: {email.get('combined_score', 0):.2f})")
        
        print(f"Phones Found: {len(result.phones)}")
        print(f"Contact Forms: {len(result.contact_forms)}")
        print(f"Pages Processed: {result.pages_processed}")
        print(f"Overall Score: {result.overall_score:.2f}")
        print(f"Is Actionable: {result.is_actionable}")
        print(f"Extraction Time: {result.extraction_time:.2f}s")
        
        if result.extraction_errors:
            print(f"Errors: {result.extraction_errors}")
    
    return True


if __name__ == "__main__":
    test_email_hunter()