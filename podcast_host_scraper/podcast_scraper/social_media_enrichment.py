"""
Social media profile discovery and enrichment module.
Finds and analyzes social media profiles for podcast hosts.
"""

import re
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, quote_plus
from botasaurus.browser import browser, Driver

from .base import PodcastData
from .config import config

logger = logging.getLogger(__name__)


@browser(headless=True, block_images=True)
def scrape_social_profile(driver: Driver, data: Dict[str, Any]):
    """
    Scrape social media profile using Botasaurus for anti-detection.
    
    Args:
        driver: Botasaurus Driver instance
        data: Dict containing profile URL and platform
        
    Returns:
        Dict with profile information
    """
    url = data.get('url')
    platform = data.get('platform', 'unknown')
    
    result = {
        'url': url,
        'platform': platform,
        'profile_data': {},
        'contact_info': {},
        'metrics': {},
        'error': None
    }
    
    try:
        driver.get(url)
        driver.sleep(3)
        
        page_source = driver.page_source
        
        if platform == 'twitter':
            result['profile_data'] = _extract_twitter_data(page_source)
        elif platform == 'instagram':
            result['profile_data'] = _extract_instagram_data(page_source)
        elif platform == 'linkedin':
            result['profile_data'] = _extract_linkedin_data(page_source)
        elif platform == 'youtube':
            result['profile_data'] = _extract_youtube_data(page_source)
        elif platform == 'tiktok':
            result['profile_data'] = _extract_tiktok_data(page_source)
        
        # Extract contact information from bio/description
        bio_text = result['profile_data'].get('bio', '')
        if bio_text:
            result['contact_info'] = _extract_contact_from_bio(bio_text)
        
        logger.debug(f"Successfully scraped {platform} profile: {url}")
        
    except Exception as e:
        logger.error(f"Error scraping {platform} profile {url}: {e}")
        result['error'] = str(e)
    
    return result


def _extract_twitter_data(page_source: str) -> Dict[str, Any]:
    """Extract data from Twitter profile page."""
    data = {}
    
    # Extract name and handle
    name_match = re.search(r'"name":"([^"]+)"', page_source)
    if name_match:
        data['name'] = name_match.group(1)
    
    handle_match = re.search(r'"screen_name":"([^"]+)"', page_source)
    if handle_match:
        data['handle'] = f"@{handle_match.group(1)}"
    
    # Extract bio/description
    bio_match = re.search(r'"description":"([^"]+)"', page_source)
    if bio_match:
        data['bio'] = bio_match.group(1).replace('\\n', '\n')
    
    # Extract follower count (approximate from page)
    followers_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?[KMB]?)\s*followers?', page_source, re.IGNORECASE)
    if followers_match:
        data['followers'] = followers_match.group(1)
    
    # Extract website from bio
    website_match = re.search(r'https?://[^\s<>"\']+', data.get('bio', ''))
    if website_match:
        data['website'] = website_match.group(0)
    
    return data


def _extract_instagram_data(page_source: str) -> Dict[str, Any]:
    """Extract data from Instagram profile page."""
    data = {}
    
    # Instagram uses JSON-LD data
    json_match = re.search(r'"biography":"([^"]*)"', page_source)
    if json_match:
        data['bio'] = json_match.group(1).replace('\\n', '\n')
    
    # Extract username
    username_match = re.search(r'"username":"([^"]+)"', page_source)
    if username_match:
        data['handle'] = f"@{username_match.group(1)}"
    
    # Extract full name
    name_match = re.search(r'"full_name":"([^"]+)"', page_source)
    if name_match:
        data['name'] = name_match.group(1)
    
    # Extract follower count
    followers_match = re.search(r'"edge_followed_by":{"count":(\d+)}', page_source)
    if followers_match:
        count = int(followers_match.group(1))
        data['followers'] = _format_follower_count(count)
    
    return data


def _extract_linkedin_data(page_source: str) -> Dict[str, Any]:
    """Extract data from LinkedIn profile page."""
    data = {}
    
    # Extract name from title or meta tags
    title_match = re.search(r'<title>([^|]+)', page_source)
    if title_match:
        data['name'] = title_match.group(1).strip()
    
    # Extract headline/description
    headline_match = re.search(r'"headline":"([^"]+)"', page_source)
    if headline_match:
        data['bio'] = headline_match.group(1)
    
    # LinkedIn doesn't show follower counts on profile pages easily
    return data


def _extract_youtube_data(page_source: str) -> Dict[str, Any]:
    """Extract data from YouTube channel page."""
    data = {}
    
    # Extract channel name
    name_match = re.search(r'"title":"([^"]+)".*"channelId"', page_source)
    if name_match:
        data['name'] = name_match.group(1)
    
    # Extract subscriber count
    subs_match = re.search(r'(\d+(?:\.\d+)?[KMB]?)\s*subscribers?', page_source, re.IGNORECASE)
    if subs_match:
        data['subscribers'] = subs_match.group(1)
    
    # Extract channel description
    desc_match = re.search(r'"description":{"simpleText":"([^"]+)"', page_source)
    if desc_match:
        data['bio'] = desc_match.group(1)
    
    return data


def _extract_tiktok_data(page_source: str) -> Dict[str, Any]:
    """Extract data from TikTok profile page."""
    data = {}
    
    # TikTok structure (basic extraction)
    name_match = re.search(r'"nickname":"([^"]+)"', page_source)
    if name_match:
        data['name'] = name_match.group(1)
    
    # Extract bio
    bio_match = re.search(r'"signature":"([^"]+)"', page_source)
    if bio_match:
        data['bio'] = bio_match.group(1)
    
    # Extract follower count
    followers_match = re.search(r'"followerCount":(\d+)', page_source)
    if followers_match:
        count = int(followers_match.group(1))
        data['followers'] = _format_follower_count(count)
    
    return data


def _extract_contact_from_bio(bio_text: str) -> Dict[str, Any]:
    """Extract contact information from social media bio."""
    contact_info = {
        'emails': [],
        'websites': [],
        'other_social': [],
        'contact_methods': []
    }
    
    # Extract emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, bio_text)
    contact_info['emails'] = list(set(emails))
    
    # Extract websites
    website_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+|[a-zA-Z0-9-]+\.(?:com|org|net|io|co)\b'
    websites = re.findall(website_pattern, bio_text, re.IGNORECASE)
    contact_info['websites'] = list(set(websites))
    
    # Extract other social handles
    social_patterns = {
        'instagram': r'@([a-zA-Z0-9_.]+)',
        'twitter': r'twitter\.com/([a-zA-Z0-9_]+)',
        'youtube': r'youtube\.com/(?:c/|channel/|@)([a-zA-Z0-9_-]+)',
        'linkedin': r'linkedin\.com/in/([a-zA-Z0-9-]+)'
    }
    
    for platform, pattern in social_patterns.items():
        matches = re.findall(pattern, bio_text, re.IGNORECASE)
        if matches:
            contact_info['other_social'].extend([f"{platform}:{match}" for match in matches])
    
    # Look for contact keywords
    contact_keywords = ['email', 'contact', 'booking', 'business', 'collaborate', 'dm']
    for keyword in contact_keywords:
        if keyword.lower() in bio_text.lower():
            contact_info['contact_methods'].append(keyword)
    
    return contact_info


def _format_follower_count(count: int) -> str:
    """Format follower count with K/M/B suffixes."""
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


class SocialMediaEnricher:
    """Enriches podcast data with social media profile information."""
    
    def __init__(self):
        """Initialize social media enricher."""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
        
        # Platform URL patterns for validation
        self.platform_patterns = {
            'twitter': r'(?:https?://)?(?:www\.)?twitter\.com/([a-zA-Z0-9_]+)',
            'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)',
            'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-]+)',
            'youtube': r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@)([a-zA-Z0-9_-]+)',
            'tiktok': r'(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9_.]+)',
            'facebook': r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)'
        }
    
    def discover_social_profiles(self, podcast: PodcastData, host_name: str = None) -> Dict[str, str]:
        """
        Discover social media profiles for a podcast or host.
        
        Args:
            podcast: PodcastData object
            host_name: Optional specific host name to search for
            
        Returns:
            Dict mapping platform names to profile URLs
        """
        discovered_profiles = {}
        
        search_terms = []
        
        # Add podcast name
        if podcast.podcast_name:
            search_terms.append(podcast.podcast_name)
        
        # Add host name if provided or available
        search_name = host_name or podcast.host_name
        if search_name:
            search_terms.append(search_name)
        
        # Search for profiles using different strategies
        for term in search_terms:
            if len(discovered_profiles) >= 5:  # Limit to prevent excessive searches
                break
            
            # Strategy 1: Direct social media search
            profiles = self._search_social_media_direct(term)
            discovered_profiles.update(profiles)
            
            # Strategy 2: Google search for social profiles (if API available)
            if config.has_google_search_keys():
                google_profiles = self._google_search_social_profiles(term)
                discovered_profiles.update(google_profiles)
        
        self.logger.info(f"Discovered {len(discovered_profiles)} social profiles for {podcast.podcast_name}")
        return discovered_profiles
    
    def enrich_social_profiles(self, social_links: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Enrich social media profiles with detailed information.
        
        Args:
            social_links: Dict mapping platform to profile URL
            
        Returns:
            Dict with enriched profile data
        """
        enriched_profiles = {}
        
        for platform, url in social_links.items():
            try:
                self.logger.info(f"Enriching {platform} profile: {url}")
                
                # Scrape profile using Botasaurus
                profile_data = scrape_social_profile({
                    'url': url,
                    'platform': platform
                })
                
                if not profile_data.get('error'):
                    enriched_profiles[platform] = profile_data
                    
                    # Calculate influence score
                    influence_score = self._calculate_influence_score(platform, profile_data)
                    enriched_profiles[platform]['influence_score'] = influence_score
                    
                else:
                    self.logger.warning(f"Error enriching {platform} profile: {profile_data['error']}")
                
            except Exception as e:
                self.logger.warning(f"Error enriching {platform} profile {url}: {e}")
                continue
        
        return enriched_profiles
    
    def _search_social_media_direct(self, search_term: str) -> Dict[str, str]:
        """Search for social media profiles directly."""
        profiles = {}
        
        # Construct likely profile URLs
        clean_term = re.sub(r'[^\w\s-]', '', search_term.lower())
        username_variations = [
            clean_term.replace(' ', ''),
            clean_term.replace(' ', '_'),
            clean_term.replace(' ', '-'),
            ''.join(word[0] for word in clean_term.split()),  # Initials
        ]
        
        for platform, pattern in self.platform_patterns.items():
            for username in username_variations:
                if len(username) < 3:  # Skip very short usernames
                    continue
                
                # Construct potential URL
                if platform == 'twitter':
                    test_url = f"https://twitter.com/{username}"
                elif platform == 'instagram':
                    test_url = f"https://instagram.com/{username}"
                elif platform == 'youtube':
                    test_url = f"https://youtube.com/@{username}"
                elif platform == 'linkedin':
                    test_url = f"https://linkedin.com/in/{username}"
                elif platform == 'tiktok':
                    test_url = f"https://tiktok.com/@{username}"
                else:
                    continue
                
                # Quick check if profile exists (HEAD request)
                if self._profile_exists(test_url):
                    profiles[platform] = test_url
                    break  # Found one for this platform, move to next
        
        return profiles
    
    def _google_search_social_profiles(self, search_term: str) -> Dict[str, str]:
        """Use Google Custom Search to find social media profiles."""
        profiles = {}
        
        if not config.has_google_search_keys():
            return profiles
        
        try:
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_CUSTOM_SEARCH_KEY)
            
            # Search for social media profiles
            for platform in ['twitter', 'instagram', 'youtube', 'linkedin']:
                query = f'"{search_term}" site:{platform}.com'
                
                try:
                    result = service.cse().list(
                        q=query,
                        cx=config.GOOGLE_SEARCH_ENGINE_ID,
                        num=3
                    ).execute()
                    
                    for item in result.get('items', []):
                        url = item.get('link', '')
                        if self._is_valid_profile_url(url, platform):
                            profiles[platform] = url
                            break  # Take first valid result
                
                except Exception as e:
                    self.logger.debug(f"Error searching {platform} for {search_term}: {e}")
                    continue
        
        except Exception as e:
            self.logger.warning(f"Error in Google search for social profiles: {e}")
        
        return profiles
    
    def _profile_exists(self, url: str) -> bool:
        """Check if a social media profile exists."""
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            # Most platforms return 200 for existing profiles, 404 for non-existing
            return response.status_code == 200
        except:
            return False
    
    def _is_valid_profile_url(self, url: str, platform: str) -> bool:
        """Check if URL is a valid profile URL for the platform."""
        if not url:
            return False
        
        pattern = self.platform_patterns.get(platform)
        if not pattern:
            return False
        
        return bool(re.search(pattern, url, re.IGNORECASE))
    
    def _calculate_influence_score(self, platform: str, profile_data: Dict[str, Any]) -> float:
        """Calculate influence score based on platform and profile data."""
        score = 0.0
        
        profile_info = profile_data.get('profile_data', {})
        
        # Base score from follower/subscriber count
        follower_key = 'followers' if platform != 'youtube' else 'subscribers'
        follower_str = profile_info.get(follower_key, '0')
        
        # Parse follower count
        follower_count = self._parse_follower_count(follower_str)
        
        # Logarithmic scaling for follower count
        if follower_count > 0:
            import math
            score += min(5.0, math.log10(follower_count))
        
        # Platform-specific bonuses
        platform_multipliers = {
            'youtube': 1.2,  # Video content has higher engagement
            'linkedin': 1.1,  # Professional network
            'twitter': 1.0,
            'instagram': 0.9,
            'tiktok': 0.8,
            'facebook': 0.7
        }
        
        score *= platform_multipliers.get(platform, 1.0)
        
        # Bio/content quality indicators
        bio = profile_info.get('bio', '')
        if bio:
            if len(bio) > 50:  # Detailed bio
                score += 0.5
            if any(keyword in bio.lower() for keyword in ['podcast', 'host', 'creator', 'entrepreneur']):
                score += 0.5
        
        # Contact information availability
        contact_info = profile_data.get('contact_info', {})
        if contact_info.get('emails'):
            score += 1.0
        if contact_info.get('websites'):
            score += 0.5
        
        return round(min(10.0, score), 2)  # Cap at 10.0
    
    def _parse_follower_count(self, follower_str: str) -> int:
        """Parse follower count string to integer."""
        if not follower_str:
            return 0
        
        # Remove commas and convert K/M/B to numbers
        clean_str = follower_str.replace(',', '').strip()
        
        multipliers = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}
        
        for suffix, multiplier in multipliers.items():
            if clean_str.upper().endswith(suffix):
                try:
                    number = float(clean_str[:-1])
                    return int(number * multiplier)
                except ValueError:
                    return 0
        
        # Try to parse as plain integer
        try:
            return int(clean_str)
        except ValueError:
            return 0