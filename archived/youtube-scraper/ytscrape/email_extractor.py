"""
Email Extractor Module
Extracts email addresses from YouTube channel descriptions and linked websites.
Free and open source approach that respects terms of service.
"""

import re
import logging
import time
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class EmailExtractor:
    """Extracts email addresses from various sources."""
    
    def __init__(self):
        """Initialize email extractor."""
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Z|a-z]{2,}\b'
        )
        
        # Common business email patterns
        self.business_indicators = [
            'business', 'contact', 'inquir', 'collab', 'sponsor',
            'booking', 'press', 'media', 'partner', 'pr@', 'info@',
            'hello@', 'team@', 'support@', 'admin@'
        ]
        
        # Request headers to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_delay = 1.0  # Minimum 1 second between requests
    
    def extract_from_channel(self, channel_data: Dict) -> Dict[str, any]:
        """
        Extract all possible email addresses from a YouTube channel.
        
        Args:
            channel_data: Channel data dictionary
            
        Returns:
            Dictionary with extracted emails and contact info
        """
        contact_info = {
            'business_email': None,
            'all_emails': [],
            'website': None,
            'social_links': {},
            'contact_method': None
        }
        
        # Extract from channel description
        description = channel_data.get('channel_description', '')
        if description:
            desc_emails = self.extract_emails_from_text(description)
            contact_info['all_emails'].extend(desc_emails)
            
            # Find business email
            business_email = self.identify_business_email(desc_emails, description)
            if business_email:
                contact_info['business_email'] = business_email
                contact_info['contact_method'] = 'YouTube Description'
        
        # Extract links from description
        links = self.extract_links_from_text(description)
        contact_info['website'] = links['website']
        contact_info['social_links'] = links['social']
        
        # Try to get emails from website if available
        if contact_info['website'] and not contact_info['business_email']:
            website_emails = self.extract_from_website(contact_info['website'])
            if website_emails:
                contact_info['all_emails'].extend(website_emails)
                if not contact_info['business_email']:
                    contact_info['business_email'] = website_emails[0]
                    contact_info['contact_method'] = 'Website'
        
        # Remove duplicates
        contact_info['all_emails'] = list(set(contact_info['all_emails']))
        
        # If still no email, construct YouTube channel URL for manual checking
        if not contact_info['business_email']:
            channel_id = channel_data.get('channel_id', '')
            if channel_id:
                contact_info['youtube_about_url'] = f"https://youtube.com/channel/{channel_id}/about"
                contact_info['contact_method'] = 'Check YouTube About Page'
        
        return contact_info
    
    def extract_emails_from_text(self, text: str) -> List[str]:
        """
        Extract email addresses from text using regex.
        
        Args:
            text: Text to search for emails
            
        Returns:
            List of email addresses found
        """
        if not text:
            return []
        
        # Find all email-like patterns
        emails = self.email_pattern.findall(text)
        
        # Filter out common false positives
        valid_emails = []
        for email in emails:
            email_lower = email.lower()
            # Skip image files and other non-email patterns
            if not any(ext in email_lower for ext in ['.png', '.jpg', '.gif', '.jpeg']):
                valid_emails.append(email)
        
        return valid_emails
    
    def identify_business_email(self, emails: List[str], context: str) -> Optional[str]:
        """
        Identify the most likely business email from a list.
        
        Args:
            emails: List of email addresses
            context: Text context where emails were found
            
        Returns:
            Most likely business email or None
        """
        if not emails:
            return None
        
        context_lower = context.lower()
        
        # Look for business email indicators
        for email in emails:
            email_lower = email.lower()
            
            # Check if email is explicitly marked as business
            for indicator in self.business_indicators:
                if indicator in email_lower:
                    return email
                
                # Check if email is near business keywords in context
                if indicator in context_lower:
                    # Find position of indicator and email
                    indicator_pos = context_lower.find(indicator)
                    email_pos = context_lower.find(email_lower)
                    
                    # If email is within 50 characters of indicator, likely business
                    if abs(indicator_pos - email_pos) < 50:
                        return email
        
        # If no business indicators, return first email
        return emails[0]
    
    def extract_links_from_text(self, text: str) -> Dict:
        """
        Extract website and social media links from text.
        
        Args:
            text: Text to search for links
            
        Returns:
            Dictionary with categorized links
        """
        links = {
            'website': None,
            'social': {
                'twitter': None,
                'instagram': None,
                'linkedin': None,
                'facebook': None,
                'tiktok': None
            },
            'other': []
        }
        
        if not text:
            return links
        
        # Find all URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            url_lower = url.lower()
            
            # Categorize URLs
            if 'twitter.com' in url_lower or 'x.com' in url_lower:
                links['social']['twitter'] = url
            elif 'instagram.com' in url_lower:
                links['social']['instagram'] = url
            elif 'linkedin.com' in url_lower:
                links['social']['linkedin'] = url
            elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
                links['social']['facebook'] = url
            elif 'tiktok.com' in url_lower:
                links['social']['tiktok'] = url
            elif not any(yt in url_lower for yt in ['youtube.com', 'youtu.be', 'discord.', 'patreon.']):
                # First non-social, non-YouTube link is likely the main website
                if not links['website']:
                    links['website'] = url
                else:
                    links['other'].append(url)
        
        return links
    
    def extract_from_website(self, website_url: str) -> List[str]:
        """
        Extract email addresses from a website.
        
        Args:
            website_url: URL of the website to scrape
            
        Returns:
            List of email addresses found
        """
        if not website_url:
            return []
        
        # Rate limiting
        self._rate_limit()
        
        all_emails = []
        
        try:
            # Try main page first
            main_emails = self._scrape_page_for_emails(website_url)
            all_emails.extend(main_emails)
            
            # Common contact page paths
            contact_paths = [
                '/contact', '/contact-us', '/about', '/about-us',
                '/business', '/collaborate', '/inquiries', '/press'
            ]
            
            # Try each contact page path
            for path in contact_paths:
                # Rate limiting between requests
                self._rate_limit()
                
                contact_url = urljoin(website_url, path)
                page_emails = self._scrape_page_for_emails(contact_url)
                all_emails.extend(page_emails)
                
                # If we found emails, stop searching
                if page_emails:
                    break
            
        except Exception as e:
            logger.warning(f"Error extracting from website {website_url}: {e}")
        
        # Remove duplicates and return
        return list(set(all_emails))
    
    def _scrape_page_for_emails(self, url: str) -> List[str]:
        """
        Scrape a single web page for email addresses.
        
        Args:
            url: URL to scrape
            
        Returns:
            List of emails found
        """
        emails = []
        
        try:
            # Make request with timeout
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find mailto links
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
            for link in mailto_links:
                email = link['href'].replace('mailto:', '').split('?')[0]
                if '@' in email:
                    emails.append(email)
            
            # Find emails in visible text
            text = soup.get_text()
            text_emails = self.extract_emails_from_text(text)
            emails.extend(text_emails)
            
            # Look for emails in meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                content = tag.get('content', '')
                meta_emails = self.extract_emails_from_text(content)
                emails.extend(meta_emails)
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Could not access {url}: {e}")
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
        
        return emails
    
    def _rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def format_contact_info(self, contact_info: Dict) -> str:
        """
        Format contact information for display.
        
        Args:
            contact_info: Contact information dictionary
            
        Returns:
            Formatted string
        """
        if contact_info.get('business_email'):
            return contact_info['business_email']
        elif contact_info.get('all_emails'):
            return contact_info['all_emails'][0]
        elif contact_info.get('website'):
            return f"Website: {contact_info['website']}"
        elif contact_info.get('youtube_about_url'):
            return f"Check: {contact_info['youtube_about_url']}"
        else:
            return "No contact info found"