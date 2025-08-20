"""
Influencer Email Finder
Specialized for finding contact info of YouTubers and content creators
Uses methods that actually work for influencers, not B2B corporate emails
"""

import re
import logging
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InfluencerEmailFinder:
    """Find emails for influencers and content creators."""
    
    def __init__(self):
        """Initialize influencer email finder."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def find_creator_email(self, channel_data: Dict) -> Dict:
        """
        Find email for a content creator using multiple methods.
        
        Priority order:
        1. YouTube description parsing
        2. Instagram bio extraction
        3. Website contact page scraping
        4. Linktree/link aggregator parsing
        5. Common creator email patterns
        """
        results = {
            "email": None,
            "source": None,
            "confidence": 0,
            "alternatives": []
        }
        
        channel_name = channel_data.get("channel_name", "")
        description = channel_data.get("channel_description", "")
        website = channel_data.get("website", "")
        
        # Method 1: Parse YouTube description
        youtube_email = self._extract_email_from_text(description)
        if youtube_email:
            results["email"] = youtube_email
            results["source"] = "YouTube description"
            results["confidence"] = 95
            return results
        
        # Method 2: Check if website is Linktree or similar
        if website:
            if any(domain in website.lower() for domain in ["linktr.ee", "beacons.ai", "bio.link", "linkin.bio"]):
                linktree_email = self._scrape_linktree(website)
                if linktree_email:
                    results["email"] = linktree_email
                    results["source"] = "Link aggregator"
                    results["confidence"] = 90
                    return results
        
        # Method 3: Scrape website contact page
        if website:
            website_email = self._scrape_website_contact(website)
            if website_email:
                results["email"] = website_email
                results["source"] = "Website contact page"
                results["confidence"] = 85
                return results
        
        # Method 4: Try Instagram bio if we have handle
        instagram_handle = self._extract_instagram_handle(description)
        if instagram_handle:
            # Note: Instagram scraping requires additional tools/APIs
            # This is a placeholder for Instagram integration
            results["alternatives"].append(f"Check Instagram: @{instagram_handle}")
        
        # Method 5: Generate common creator email patterns
        creator_emails = self._generate_creator_emails(channel_name, website)
        if creator_emails:
            results["email"] = creator_emails[0]
            results["source"] = "Pattern guess"
            results["confidence"] = 30
            results["alternatives"] = creator_emails[1:5]
        
        # Fallback: Provide YouTube About page URL
        if not results["email"]:
            channel_id = channel_data.get("channel_id", "")
            results["youtube_about"] = f"https://youtube.com/channel/{channel_id}/about"
            results["note"] = "Check About tab for business email (manual verification required)"
        
        return results
    
    def _extract_email_from_text(self, text: str) -> Optional[str]:
        """Extract email from text using regex."""
        if not text:
            return None
        
        # Email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Filter out fake/example emails
        valid_emails = [
            email for email in emails 
            if not any(fake in email.lower() for fake in ["example.com", "email.com", "yourmail"])
        ]
        
        # Prefer business emails
        for email in valid_emails:
            if any(biz in email.lower() for biz in ["business", "contact", "collab", "inquir", "sponsor", "partner"]):
                return email
        
        return valid_emails[0] if valid_emails else None
    
    def _extract_instagram_handle(self, text: str) -> Optional[str]:
        """Extract Instagram handle from text."""
        if not text:
            return None
        
        # Instagram handle patterns
        patterns = [
            r'instagram\.com/([A-Za-z0-9_.]+)',
            r'@([A-Za-z0-9_.]+)',
            r'IG:\s*([A-Za-z0-9_.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _scrape_linktree(self, url: str) -> Optional[str]:
        """Scrape Linktree or similar link aggregator for email."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for email links
                email_links = soup.find_all('a', href=re.compile(r'^mailto:'))
                if email_links:
                    email = email_links[0]['href'].replace('mailto:', '')
                    return email
                
                # Look for contact/email text
                text = soup.get_text()
                return self._extract_email_from_text(text)
        
        except Exception as e:
            logger.debug(f"Error scraping Linktree: {e}")
        
        return None
    
    def _scrape_website_contact(self, url: str) -> Optional[str]:
        """Scrape website for contact email."""
        contact_paths = ['/contact', '/about', '/business', '/collaborate', '/sponsor']
        
        # Try main page first
        email = self._scrape_page_for_email(url)
        if email:
            return email
        
        # Try common contact pages
        base_url = url.rstrip('/')
        for path in contact_paths:
            try:
                contact_url = f"{base_url}{path}"
                email = self._scrape_page_for_email(contact_url)
                if email:
                    return email
            except:
                continue
        
        return None
    
    def _scrape_page_for_email(self, url: str) -> Optional[str]:
        """Scrape a single page for email."""
        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check mailto links
                mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
                if mailto_links:
                    return mailto_links[0]['href'].replace('mailto:', '')
                
                # Extract from text
                return self._extract_email_from_text(soup.get_text())
        
        except:
            pass
        
        return None
    
    def _generate_creator_emails(self, channel_name: str, website: str) -> List[str]:
        """Generate common creator email patterns."""
        emails = []
        
        # Clean channel name
        name = channel_name.lower()
        name = re.sub(r'[^a-z0-9\s]', '', name)
        parts = name.split()
        
        # Common creator email domains
        domains = ['gmail.com', 'outlook.com', 'yahoo.com']
        
        # If we have a website, extract domain
        if website:
            try:
                parsed = urlparse(website)
                domain = parsed.netloc.replace('www.', '')
                if domain and '.' in domain:
                    domains.insert(0, domain)
            except:
                pass
        
        # Generate patterns
        if parts:
            username = ''.join(parts)
            first_name = parts[0] if parts else ""
            
            # Common creator patterns
            patterns = [
                f"{username}business@",
                f"{username}collab@",
                f"contact{username}@",
                f"{username}official@",
                f"hello{username}@",
                f"{first_name}business@",
                f"team{username}@"
            ]
            
            for pattern in patterns:
                for domain in domains[:2]:  # Only use top 2 domains
                    email = pattern + domain
                    if '@' in email and '.' in email:
                        emails.append(email)
        
        return emails[:10]  # Return max 10 suggestions


class SocialMediaExtractor:
    """Extract contact info from social media profiles."""
    
    def extract_from_instagram(self, username: str) -> Optional[str]:
        """
        Extract email from Instagram bio.
        Note: This requires Instagram API access or web scraping tools.
        """
        # Placeholder - would need Instagram Graph API or scraping tool
        logger.info(f"Instagram extraction for @{username} requires API setup")
        return None
    
    def extract_from_tiktok(self, username: str) -> Optional[str]:
        """
        Extract email from TikTok profile.
        Note: This requires TikTok API or scraping tools.
        """
        # Placeholder - would need TikTok API or scraping tool
        logger.info(f"TikTok extraction for @{username} requires API setup")
        return None