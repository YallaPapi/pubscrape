#!/usr/bin/env python3
"""
Website Navigator - Smart Navigation to Contact Pages
Intelligently discovers and navigates to contact/about pages on websites
"""

import re
import time
import logging
from typing import List, Dict, Any, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field


@dataclass
class NavigationResult:
    """Result of website navigation"""
    base_url: str
    pages_visited: List[str] = field(default_factory=list)
    contact_pages: List[str] = field(default_factory=list)
    about_pages: List[str] = field(default_factory=list)
    team_pages: List[str] = field(default_factory=list)
    navigation_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class WebsiteNavigator:
    """
    Intelligent website navigator that discovers contact-related pages
    """
    
    def __init__(self, timeout: int = 10, delay: float = 1.0):
        self.timeout = timeout
        self.delay = delay
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Contact page patterns (ordered by priority)
        self.contact_patterns = [
            # Direct contact patterns
            (re.compile(r'^contact(?:-us)?/?$', re.IGNORECASE), 100),
            (re.compile(r'^contact[-_]?us/?$', re.IGNORECASE), 95),
            (re.compile(r'^get[-_]?in[-_]?touch/?$', re.IGNORECASE), 90),
            (re.compile(r'^reach[-_]?out/?$', re.IGNORECASE), 85),
            
            # Contact with modifiers
            (re.compile(r'^contact[-_]?info(?:rmation)?/?$', re.IGNORECASE), 80),
            (re.compile(r'^contact[-_]?details/?$', re.IGNORECASE), 75),
            (re.compile(r'^contact[-_]?form/?$', re.IGNORECASE), 70),
            
            # About patterns
            (re.compile(r'^about(?:-us)?/?$', re.IGNORECASE), 65),
            (re.compile(r'^about[-_]?us/?$', re.IGNORECASE), 60),
            (re.compile(r'^who[-_]?we[-_]?are/?$', re.IGNORECASE), 55),
            (re.compile(r'^our[-_]?story/?$', re.IGNORECASE), 50),
            
            # Team patterns
            (re.compile(r'^team/?$', re.IGNORECASE), 45),
            (re.compile(r'^our[-_]?team/?$', re.IGNORECASE), 40),
            (re.compile(r'^staff/?$', re.IGNORECASE), 35),
            (re.compile(r'^people/?$', re.IGNORECASE), 30),
            (re.compile(r'^leadership/?$', re.IGNORECASE), 25),
            (re.compile(r'^management/?$', re.IGNORECASE), 20),
            
            # Location patterns
            (re.compile(r'^location(?:s)?/?$', re.IGNORECASE), 15),
            (re.compile(r'^office(?:s)?/?$', re.IGNORECASE), 10),
            (re.compile(r'^find[-_]?us/?$', re.IGNORECASE), 5),
        ]
        
        # Link text patterns for contact discovery
        self.link_text_patterns = [
            # High priority text patterns
            (re.compile(r'^contact\s*us$', re.IGNORECASE), 100),
            (re.compile(r'^contact$', re.IGNORECASE), 95),
            (re.compile(r'^get\s*in\s*touch$', re.IGNORECASE), 90),
            (re.compile(r'^reach\s*out$', re.IGNORECASE), 85),
            
            # Medium priority
            (re.compile(r'^about\s*us$', re.IGNORECASE), 80),
            (re.compile(r'^about$', re.IGNORECASE), 75),
            (re.compile(r'^our\s*team$', re.IGNORECASE), 70),
            (re.compile(r'^team$', re.IGNORECASE), 65),
            
            # Lower priority
            (re.compile(r'^staff$', re.IGNORECASE), 60),
            (re.compile(r'^location$', re.IGNORECASE), 55),
            (re.compile(r'^office$', re.IGNORECASE), 50),
            (re.compile(r'^find\s*us$', re.IGNORECASE), 45),
        ]
        
        # Page content indicators for contact pages
        self.content_indicators = [
            'email', 'phone', 'address', 'contact form', 'get in touch',
            'reach out', 'send message', 'contact information'
        ]
        
        # Navigation depth limits
        self.max_depth = 2
        self.max_links_per_page = 50
    
    def discover_contact_pages(self, base_url: str, max_pages: int = 5) -> Dict[str, Any]:
        """
        Discover contact-related pages on a website
        
        Args:
            base_url: Base website URL
            max_pages: Maximum number of pages to visit
            
        Returns:
            Dictionary with discovered pages and navigation data
        """
        start_time = time.time()
        
        result = NavigationResult(base_url=base_url)
        visited_urls = set()
        contact_candidates = []
        
        try:
            self.logger.info(f"Starting contact page discovery for: {base_url}")
            
            # Step 1: Analyze main page
            main_page_links = self._extract_navigation_links(base_url)
            if main_page_links:
                result.pages_visited.append(base_url)
                visited_urls.add(base_url)
            
            # Step 2: Score and prioritize contact page candidates
            for link_data in main_page_links:
                score = self._score_contact_page_candidate(link_data)
                if score > 0:
                    contact_candidates.append((link_data['url'], score, link_data))
            
            # Sort by score (highest first)
            contact_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Step 3: Visit top contact page candidates
            pages_processed = 1  # Already processed main page
            
            for candidate_url, score, link_data in contact_candidates:
                if pages_processed >= max_pages:
                    break
                
                if candidate_url in visited_urls:
                    continue
                
                try:
                    self.logger.info(f"Visiting candidate page: {candidate_url} (score: {score})")
                    
                    # Verify this is actually a contact page
                    if self._verify_contact_page(candidate_url):
                        result.contact_pages.append(candidate_url)
                        self.logger.info(f"Confirmed contact page: {candidate_url}")
                    
                    result.pages_visited.append(candidate_url)
                    visited_urls.add(candidate_url)
                    pages_processed += 1
                    
                    # Rate limiting
                    time.sleep(self.delay)
                    
                except Exception as e:
                    error_msg = f"Error visiting {candidate_url}: {str(e)}"
                    self.logger.error(error_msg)
                    result.errors.append(error_msg)
            
            # Step 4: Categorize discovered pages
            result.about_pages = [url for url in result.contact_pages 
                                if self._is_about_page(url)]
            result.team_pages = [url for url in result.contact_pages 
                               if self._is_team_page(url)]
            
            # Remove about/team pages from contact pages list
            result.contact_pages = [url for url in result.contact_pages 
                                  if url not in result.about_pages and url not in result.team_pages]
            
            result.navigation_time = time.time() - start_time
            
            self.logger.info(f"Contact discovery completed: "
                           f"{len(result.contact_pages)} contact pages, "
                           f"{len(result.about_pages)} about pages, "
                           f"{len(result.team_pages)} team pages")
            
        except Exception as e:
            error_msg = f"Contact page discovery failed: {str(e)}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            result.navigation_time = time.time() - start_time
        
        return {
            'pages_visited': result.pages_visited,
            'contact_pages': result.contact_pages,
            'about_pages': result.about_pages,
            'team_pages': result.team_pages,
            'navigation_time': result.navigation_time,
            'errors': result.errors
        }
    
    def _extract_navigation_links(self, url: str) -> List[Dict[str, Any]]:
        """Extract navigation links from a webpage"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            base_domain = urlparse(url).netloc
            
            links = []
            processed_hrefs = set()
            
            # Find all navigation links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                if not href or href.startswith('#'):
                    continue
                
                # Convert relative URLs to absolute
                full_url = urljoin(url, href)
                parsed_url = urlparse(full_url)
                
                # Only process links from same domain
                if parsed_url.netloc and parsed_url.netloc != base_domain:
                    continue
                
                # Avoid duplicates
                if full_url in processed_hrefs:
                    continue
                processed_hrefs.add(full_url)
                
                # Extract link information
                link_text = link.get_text(strip=True)
                link_title = link.get('title', '')
                
                # Get parent context
                parent_context = self._get_parent_context(link)
                
                link_data = {
                    'url': full_url,
                    'text': link_text,
                    'title': link_title,
                    'href': href,
                    'parent_context': parent_context,
                    'is_navigation': self._is_navigation_link(link)
                }
                
                links.append(link_data)
                
                # Limit number of links processed
                if len(links) >= self.max_links_per_page:
                    break
            
            return links
            
        except Exception as e:
            self.logger.error(f"Error extracting links from {url}: {e}")
            return []
    
    def _score_contact_page_candidate(self, link_data: Dict[str, Any]) -> int:
        """Score a link as a potential contact page candidate"""
        score = 0
        
        url = link_data['url']
        text = link_data['text'].lower()
        title = link_data['title'].lower()
        href = link_data['href'].lower()
        parent_context = link_data['parent_context'].lower()
        
        # Score based on URL path
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/').lower()
        
        for pattern, pattern_score in self.contact_patterns:
            if pattern.match(path):
                score += pattern_score
                break
        
        # Score based on link text
        for pattern, pattern_score in self.link_text_patterns:
            if pattern.match(text):
                score += pattern_score
                break
        
        # Score based on title attribute
        if any(keyword in title for keyword in ['contact', 'about', 'team']):
            score += 20
        
        # Score based on parent context
        if any(keyword in parent_context for keyword in ['navigation', 'menu', 'nav']):
            score += 10
        
        # Bonus for being in navigation
        if link_data['is_navigation']:
            score += 15
        
        # Penalties
        # Avoid file downloads
        if any(ext in href for ext in ['.pdf', '.doc', '.zip', '.jpg', '.png']):
            score -= 50
        
        # Avoid external links
        if 'http' in href and urlparse(link_data['url']).netloc != urlparse(link_data['url']).netloc:
            score -= 30
        
        return max(0, score)
    
    def _verify_contact_page(self, url: str) -> bool:
        """Verify that a page is actually a contact page by analyzing content"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text().lower()
            
            # Count contact indicators
            indicator_count = 0
            for indicator in self.content_indicators:
                if indicator in text_content:
                    indicator_count += 1
            
            # Must have at least 2 contact indicators
            return indicator_count >= 2
            
        except Exception as e:
            self.logger.error(f"Error verifying contact page {url}: {e}")
            return False
    
    def _is_about_page(self, url: str) -> bool:
        """Check if URL represents an about page"""
        path = urlparse(url).path.lower()
        about_patterns = ['about', 'story', 'history', 'mission', 'vision']
        return any(pattern in path for pattern in about_patterns)
    
    def _is_team_page(self, url: str) -> bool:
        """Check if URL represents a team page"""
        path = urlparse(url).path.lower()
        team_patterns = ['team', 'staff', 'people', 'leadership', 'management', 'bio']
        return any(pattern in path for pattern in team_patterns)
    
    def _get_parent_context(self, link) -> str:
        """Get context from parent elements of a link"""
        context_parts = []
        
        # Check parent elements
        parent = link.parent
        for _ in range(3):  # Check up to 3 levels up
            if parent and parent.name:
                # Get class and id attributes
                classes = parent.get('class', [])
                id_attr = parent.get('id', '')
                
                context_parts.extend(classes)
                if id_attr:
                    context_parts.append(id_attr)
                
                parent = parent.parent
            else:
                break
        
        return ' '.join(context_parts)
    
    def _is_navigation_link(self, link) -> bool:
        """Determine if a link is part of site navigation"""
        # Check if link is within navigation elements
        nav_elements = ['nav', 'header', 'menu']
        nav_classes = ['nav', 'navigation', 'menu', 'header', 'navbar']
        nav_ids = ['nav', 'navigation', 'menu', 'header', 'navbar']
        
        # Check parent elements
        parent = link.parent
        for _ in range(5):  # Check up to 5 levels up
            if parent:
                # Check element type
                if parent.name in nav_elements:
                    return True
                
                # Check class attributes
                classes = parent.get('class', [])
                if any(nav_class in ' '.join(classes).lower() for nav_class in nav_classes):
                    return True
                
                # Check id attribute
                id_attr = parent.get('id', '').lower()
                if any(nav_id in id_attr for nav_id in nav_ids):
                    return True
                
                parent = parent.parent
            else:
                break
        
        return False
    
    def find_contact_forms(self, url: str) -> List[Dict[str, Any]]:
        """
        Specifically look for contact forms on a page
        
        Args:
            url: URL to analyze for contact forms
            
        Returns:
            List of contact form data
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            forms = []
            
            # Find all forms
            for i, form in enumerate(soup.find_all('form')):
                form_data = {
                    'form_index': i,
                    'action': form.get('action', ''),
                    'method': form.get('method', 'GET').upper(),
                    'has_email_field': False,
                    'has_message_field': False,
                    'field_count': 0,
                    'is_contact_form': False
                }
                
                # Analyze form fields
                inputs = form.find_all(['input', 'textarea', 'select'])
                form_data['field_count'] = len(inputs)
                
                for input_elem in inputs:
                    input_type = input_elem.get('type', '').lower()
                    input_name = input_elem.get('name', '').lower()
                    input_placeholder = input_elem.get('placeholder', '').lower()
                    
                    # Check for email field
                    if (input_type == 'email' or 
                        'email' in input_name or 
                        'email' in input_placeholder):
                        form_data['has_email_field'] = True
                    
                    # Check for message field
                    if (input_elem.name == 'textarea' or
                        'message' in input_name or
                        'comment' in input_name or
                        'message' in input_placeholder):
                        form_data['has_message_field'] = True
                
                # Determine if this is likely a contact form
                form_data['is_contact_form'] = (
                    form_data['has_email_field'] and 
                    form_data['field_count'] >= 2
                )
                
                forms.append(form_data)
            
            # Return only contact forms
            return [form for form in forms if form['is_contact_form']]
            
        except Exception as e:
            self.logger.error(f"Error finding contact forms on {url}: {e}")
            return []
    
    def get_sitemap_urls(self, base_url: str) -> List[str]:
        """
        Attempt to discover URLs from sitemap.xml
        
        Args:
            base_url: Base website URL
            
        Returns:
            List of URLs from sitemap
        """
        sitemap_urls = []
        
        # Common sitemap locations
        sitemap_locations = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap.xml.gz',
            '/sitemaps/sitemap.xml'
        ]
        
        for sitemap_path in sitemap_locations:
            sitemap_url = urljoin(base_url, sitemap_path)
            
            try:
                response = self.session.get(sitemap_url, timeout=self.timeout)
                if response.status_code == 200:
                    # Parse XML sitemap
                    soup = BeautifulSoup(response.text, 'xml')
                    
                    # Extract URLs
                    for url_elem in soup.find_all('url'):
                        loc_elem = url_elem.find('loc')
                        if loc_elem:
                            sitemap_urls.append(loc_elem.get_text().strip())
                    
                    # If we found URLs, break
                    if sitemap_urls:
                        self.logger.info(f"Found {len(sitemap_urls)} URLs in sitemap: {sitemap_url}")
                        break
                        
            except Exception as e:
                self.logger.debug(f"Could not access sitemap {sitemap_url}: {e}")
                continue
        
        return sitemap_urls[:100]  # Limit to first 100 URLs


def test_website_navigator():
    """Test the website navigator"""
    print("Testing Website Navigator")
    print("=" * 40)
    
    navigator = WebsiteNavigator()
    
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://www.python.org"
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTesting URL {i}: {url}")
        print("-" * 30)
        
        result = navigator.discover_contact_pages(url, max_pages=3)
        
        print(f"Pages Visited: {len(result['pages_visited'])}")
        for page in result['pages_visited']:
            print(f"  - {page}")
        
        print(f"Contact Pages: {len(result['contact_pages'])}")
        for page in result['contact_pages']:
            print(f"  - {page}")
        
        print(f"About Pages: {len(result['about_pages'])}")
        print(f"Team Pages: {len(result['team_pages'])}")
        print(f"Navigation Time: {result['navigation_time']:.2f}s")
        
        if result['errors']:
            print(f"Errors: {result['errors']}")
        
        print()
    
    return True


if __name__ == "__main__":
    test_website_navigator()