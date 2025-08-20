"""
Website and contact page discovery module.
Finds website URLs and contact pages for podcasts.
"""

import re
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from botasaurus.browser import browser, Driver

from .base import PodcastData
from .config import config
from .contact_extraction import ContactExtractor, ContactValidator
from .social_media_enrichment import SocialMediaEnricher

logger = logging.getLogger(__name__)


class ContactPageDiscovery:
    """Discovers and scrapes contact information from podcast websites."""
    
    def __init__(self):
        """Initialize the contact discovery module."""
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
        self.logger = logging.getLogger(__name__)
        
        # Initialize enhanced contact extraction
        self.contact_extractor = ContactExtractor()
        self.contact_validator = ContactValidator()
        self.social_enricher = SocialMediaEnricher()
        
        # Common contact page paths to try
        self.contact_paths = config.CONTACT_EXTRACTION_SETTINGS['contact_page_paths']
    
    def discover_website(self, podcast: PodcastData) -> Optional[str]:
        """
        Discover the main website URL for a podcast.
        
        Args:
            podcast: PodcastData object
            
        Returns:
            Website URL if found, None otherwise
        """
        if podcast.podcast_website:
            return podcast.podcast_website
        
        # Try to extract from RSS feed if available
        if podcast.rss_feed_url:
            website_url = self._extract_website_from_rss(podcast.rss_feed_url)
            if website_url:
                return website_url
        
        # Try to extract from Apple Podcasts page description
        if podcast.apple_podcasts_url:
            website_url = self._extract_website_from_apple_page(podcast.apple_podcasts_url)
            # Avoid falsely treating Apple Podcasts domain as the podcast website
            if website_url and 'podcasts.apple.com' not in website_url:
                return website_url
        
        # Try Google search as fallback (if API keys available)
        if config.has_google_search_keys():
            website_url = self._google_search_for_website(podcast.podcast_name)
            if website_url:
                return website_url
        else:
            # Fallback: DuckDuckGo HTML search (no API key needed)
            website_url = self._duckduckgo_search_for_website(podcast.podcast_name)
            if website_url:
                return website_url
        
        return None
    
    def find_contact_pages(self, website_url: str) -> List[str]:
        """
        Find potential contact pages on a website.
        
        Args:
            website_url: Base website URL
            
        Returns:
            List of contact page URLs
        """
        contact_pages = []
        
        try:
            # Parse the base URL
            parsed_url = urlparse(website_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check common contact page paths
            for path in self.contact_paths:
                contact_url = urljoin(base_domain, path)
                if self._is_valid_contact_page(contact_url):
                    contact_pages.append(contact_url)
            
            # Try to find contact links in the main page
            main_page_contacts = self._find_contact_links_in_page(website_url)
            contact_pages.extend(main_page_contacts)
            
        except Exception as e:
            self.logger.warning(f"Error finding contact pages for {website_url}: {e}")
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(contact_pages))
    
    def extract_contact_info(self, contact_page_url: str) -> Dict[str, Any]:
        """
        Extract contact information from a contact page using enhanced extraction.
        
        Args:
            contact_page_url: URL of the contact page
            
        Returns:
            Dict with extracted contact information and validation scores
        """
        contact_info = {
            'emails': [],
            'social_links': {},
            'contact_forms': [],
            'phone_numbers': [],
            'addresses': [],
            'validation': {}
        }
        
        try:
            response = self.session.get(contact_page_url, timeout=10)
            response.raise_for_status()
            
            page_content = response.text
            
            # Use enhanced email extraction with confidence scoring
            email_results = self.contact_extractor.extract_emails(page_content, contact_page_url)
            contact_info['emails'] = [result['email'] for result in email_results]
            contact_info['email_details'] = email_results  # Keep detailed info
            
            # Extract phone numbers with classification
            phone_results = self.contact_extractor.extract_phone_numbers(page_content)
            contact_info['phone_numbers'] = [result['phone'] for result in phone_results]
            contact_info['phone_details'] = phone_results
            
            # Extract addresses
            contact_info['addresses'] = self.contact_extractor.extract_addresses(page_content)
            
            # Extract social media links (keep existing logic)
            contact_info['social_links'] = self._extract_social_links(page_content)
            
            # Check for contact forms
            if self._has_contact_form(page_content):
                contact_info['contact_forms'].append(contact_page_url)
            
            # Validate the extracted contact information
            validation_result = self.contact_validator.validate_contact_info(contact_info)
            contact_info['validation'] = validation_result
            
            self.logger.info(f"Contact extraction completed with score: {validation_result['overall_score']:.2f}")
            
        except Exception as e:
            self.logger.warning(f"Error extracting contact info from {contact_page_url}: {e}")
        
        return contact_info
    
    def enrich_with_social_media(self, podcast: PodcastData) -> PodcastData:
        """
        Enrich podcast data with social media profile information.
        
        Args:
            podcast: PodcastData object to enrich
            
        Returns:
            Enriched PodcastData object
        """
        try:
            self.logger.info(f"Starting social media enrichment for: {podcast.podcast_name}")
            
            # Discover social media profiles
            social_profiles = self.social_enricher.discover_social_profiles(podcast)
            
            if social_profiles:
                self.logger.info(f"Found {len(social_profiles)} social media profiles")
                
                # Update podcast social links
                if not podcast.social_links:
                    podcast.social_links = {}
                podcast.social_links.update(social_profiles)
                
                # Enrich profiles with detailed information
                enriched_profiles = self.social_enricher.enrich_social_profiles(social_profiles)
                
                # Store enriched data in raw_data for detailed analysis
                if not podcast.raw_data:
                    podcast.raw_data = {}
                podcast.raw_data['social_profiles'] = enriched_profiles
                
                # Extract additional contact information from social profiles
                additional_contacts = self._extract_contacts_from_social(enriched_profiles)
                
                # Update podcast with any new contact information found
                if additional_contacts.get('emails') and not podcast.host_email:
                    podcast.host_email = additional_contacts['emails'][0]
                
                if additional_contacts.get('websites') and not podcast.podcast_website:
                    podcast.podcast_website = additional_contacts['websites'][0]
                
                # Calculate overall social influence score
                influence_score = self._calculate_overall_influence(enriched_profiles)
                podcast.raw_data['social_influence_score'] = influence_score
                
                self.logger.info(f"Social media enrichment completed. Influence score: {influence_score:.1f}")
            
            else:
                self.logger.info("No social media profiles found")
            
        except Exception as e:
            self.logger.warning(f"Error during social media enrichment: {e}")
        
        return podcast
    
    def _extract_contacts_from_social(self, enriched_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract contact information from enriched social profiles."""
        all_contacts = {
            'emails': [],
            'websites': [],
            'phone_numbers': []
        }
        
        for platform, profile_data in enriched_profiles.items():
            contact_info = profile_data.get('contact_info', {})
            
            # Collect emails
            emails = contact_info.get('emails', [])
            all_contacts['emails'].extend(emails)
            
            # Collect websites
            websites = contact_info.get('websites', [])
            all_contacts['websites'].extend(websites)
        
        # Remove duplicates
        for key in all_contacts:
            all_contacts[key] = list(set(all_contacts[key]))
        
        return all_contacts
    
    def _calculate_overall_influence(self, enriched_profiles: Dict[str, Dict[str, Any]]) -> float:
        """Calculate overall social media influence score."""
        if not enriched_profiles:
            return 0.0
        
        total_score = 0.0
        platform_count = 0
        
        for platform, profile_data in enriched_profiles.items():
            influence_score = profile_data.get('influence_score', 0.0)
            total_score += influence_score
            platform_count += 1
        
        # Average score with bonus for multiple platforms
        if platform_count == 0:
            return 0.0
        
        average_score = total_score / platform_count
        
        # Bonus for having multiple social media platforms
        platform_bonus = min(1.0, (platform_count - 1) * 0.2)
        
        return round(average_score + platform_bonus, 1)
    
    def _extract_website_from_rss(self, rss_url: str) -> Optional[str]:
        """Extract website URL from RSS feed."""
        try:
            import feedparser
            
            feed = feedparser.parse(rss_url)
            if hasattr(feed, 'feed') and hasattr(feed.feed, 'link'):
                return feed.feed.link
        except Exception as e:
            self.logger.debug(f"Error parsing RSS feed {rss_url}: {e}")
        
        return None
    
    def _extract_website_from_apple_page(self, apple_url: str) -> Optional[str]:
        """Extract website URL from Apple Podcasts page."""
        try:
            response = self.session.get(apple_url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            # Prefer explicit "Website" anchors pointing off Apple/Spotify domains
            website_patterns = [
                r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>[^<]*(?:website|official|site)[^<]*</a>',
                r'Website:\s*<a[^>]+href=["\'](https?://[^"\']+)["\']'
            ]
            for pattern in website_patterns:
                m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if m:
                    url = m.group(1)
                    if not any(domain in url for domain in ['podcasts.apple.com', 'apple.com', 'spotify.com']):
                        return url
            
            # Fallback: first external link on the page that is not Apple/Spotify
            link_pattern = r'<a[^>]+href=["\'](https?://[^"\']+)["\']'
            for m in re.finditer(link_pattern, html, re.IGNORECASE):
                url = m.group(1)
                if not any(domain in url for domain in ['podcasts.apple.com', 'apple.com', 'spotify.com']):
                    return url
        
        except Exception as e:
            self.logger.debug(f"Error extracting website from Apple page {apple_url}: {e}")
        
        return None
    
    def _google_search_for_website(self, podcast_name: str) -> Optional[str]:
        """Use Google Custom Search to find podcast website."""
        if not config.has_google_search_keys():
            return None
        
        try:
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_CUSTOM_SEARCH_KEY)
            
            # Search for podcast + "official website"
            query = f'"{podcast_name}" podcast official website'
            
            result = service.cse().list(
                q=query,
                cx=config.GOOGLE_SEARCH_ENGINE_ID,
                num=5
            ).execute()
            
            # Return the first result that looks like a podcast website
            for item in result.get('items', []):
                url = item.get('link', '')
                if self._looks_like_podcast_website(url, podcast_name):
                    return url
        
        except Exception as e:
            self.logger.warning(f"Error in Google search for {podcast_name}: {e}")
        
        return None
    
    def _duckduckgo_search_for_website(self, podcast_name: str) -> Optional[str]:
        """Use DuckDuckGo HTML search to find likely official website (no API key)."""
        try:
            q = f"{podcast_name} podcast official website"
            ddg_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(q)}"
            resp = self.session.get(ddg_url, timeout=10)
            resp.raise_for_status()
            # Extract first external result link
            links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', resp.text)
            for url in links:
                if not any(b in url for b in ['duckduckgo.com', 'apple.com', 'spotify.com', 'podcasts.apple.com']):
                    return url
        except Exception as e:
            self.logger.debug(f"DuckDuckGo search failed for {podcast_name}: {e}")
        return None

    def _is_valid_contact_page(self, url: str) -> bool:
        """Check if a URL is a valid contact page."""
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return 200 <= response.status_code < 400
        except:
            return False
    
    def _find_contact_links_in_page(self, page_url: str) -> List[str]:
        """Find contact links in a page's content."""
        contact_links = []
        
        try:
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()
            
            # Look for links containing contact-related keywords
            contact_keywords = ['contact', 'about', 'booking', 'business', 'collaborate']
            
            link_pattern = r'<a[^>]+href=["\'](([^"\']+))["\'][^>]*>([^<]+)</a>'
            links = re.findall(link_pattern, response.text, re.IGNORECASE)
            
            base_url = '/'.join(page_url.split('/')[:3])
            
            for full_match, href, text in links:
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in contact_keywords):
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        contact_url = base_url + href
                    elif href.startswith('http'):
                        contact_url = href
                    else:
                        contact_url = urljoin(page_url, href)
                    
                    contact_links.append(contact_url)
        
        except Exception as e:
            self.logger.debug(f"Error finding contact links in {page_url}: {e}")
        
        return contact_links
    
    
    def _extract_social_links(self, page_content: str) -> Dict[str, str]:
        """Extract social media links from page content."""
        social_links = {}
        
        social_patterns = {
            'twitter': r'https?://(?:www\.)?twitter\.com/[\w_]+',
            'instagram': r'https?://(?:www\.)?instagram\.com/[\w_.]+',
            'facebook': r'https?://(?:www\.)?facebook\.com/[\w.-]+',
            'linkedin': r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[\w-]+',
            'youtube': r'https?://(?:www\.)?youtube\.com/(?:channel/|c/|user/)[\w-]+',
            'tiktok': r'https?://(?:www\.)?tiktok\.com/@[\w_.]+',
        }
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                social_links[platform] = matches[0]
        
        return social_links
    
    def _has_contact_form(self, page_content: str) -> bool:
        """Check if page has a contact form."""
        form_indicators = [
            '<form',
            'contact-form',
            'name="message"',
            'name="email"',
            'type="submit"'
        ]
        
        content_lower = page_content.lower()
        return any(indicator in content_lower for indicator in form_indicators)
    
    def _looks_like_podcast_website(self, url: str, podcast_name: str) -> bool:
        """Check if URL looks like it belongs to the podcast."""
        url_lower = url.lower()
        name_words = podcast_name.lower().split()
        
        # Check if any significant words from podcast name appear in URL
        significant_words = [word for word in name_words if len(word) > 3]
        if significant_words and any(word in url_lower for word in significant_words):
            return True
        
        # Avoid generic domains
        generic_domains = ['wikipedia', 'apple.com', 'spotify.com', 'youtube.com', 'facebook.com']
        return not any(domain in url_lower for domain in generic_domains)


@browser(headless=True, block_images=True)
def scrape_website_with_botasaurus(driver: Driver, data: Dict[str, Any]):
    """
    Use Botasaurus to scrape website information with anti-detection.
    
    Args:
        driver: Botasaurus Driver instance
        data: Dict containing 'url' to scrape
        
    Returns:
        Dict with scraped website data
    """
    url = data.get('url')
    result = {
        'url': url,
        'title': None,
        'description': None,
        'contact_links': [],
        'emails': [],
        'social_links': {},
        'error': None
    }
    
    try:
        driver.get(url)
        driver.sleep(2)
        
        # Get page source for parsing
        page_source = driver.page_source
        
        # Extract title
        title_match = re.search(r'<title>([^<]+)</title>', page_source, re.IGNORECASE)
        if title_match:
            result['title'] = title_match.group(1).strip()
        
        # Extract meta description
        desc_patterns = [
            r'<meta\s+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta\s+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']'
        ]
        
        for pattern in desc_patterns:
            desc_match = re.search(pattern, page_source, re.IGNORECASE)
            if desc_match:
                result['description'] = desc_match.group(1).strip()
                break
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, page_source)
        result['emails'] = list(set(emails))
        
        # Extract social links
        social_patterns = {
            'twitter': r'https?://(?:www\.)?twitter\.com/[\w_]+',
            'instagram': r'https?://(?:www\.)?instagram\.com/[\w_.]+',
            'facebook': r'https?://(?:www\.)?facebook\.com/[\w.-]+',
            'youtube': r'https?://(?:www\.)?youtube\.com/(?:channel/|c/|user/)[\w-]+',
        }
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                result['social_links'][platform] = matches[0]
        
        # Find contact-related links
        contact_keywords = ['contact', 'about', 'booking', 'business']
        link_pattern = r'<a[^>]+href=["\'](([^"\']+))["\'][^>]*>([^<]*(?:' + '|'.join(contact_keywords) + ')[^<]*)</a>'
        contact_matches = re.findall(link_pattern, page_source, re.IGNORECASE)
        
        for full_match, href, text in contact_matches:
            if href.startswith('http'):
                result['contact_links'].append(href)
            elif href.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                result['contact_links'].append(base_url + href)
        
    except Exception as e:
        logger.error(f"Error scraping website {url}: {e}")
        result['error'] = str(e)
    
    return result