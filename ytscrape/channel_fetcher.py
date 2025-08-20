"""
Channel Data Fetcher Module
Fetches public YouTube channel data via YouTube Data API v3.
Implements quota management and error handling per mandate.
"""

import logging
import time
import json
from typing import List, Dict, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import config
from .error_handler import ErrorHandler
from .quota_manager import QuotaManager
from .influencer_email_finder import InfluencerEmailFinder

logger = logging.getLogger(__name__)


class ChannelFetcher:
    """Fetches YouTube channel data based on search queries."""
    
    def __init__(self):
        """Initialize YouTube API client and quota manager."""
        self.youtube = build(
            config.YOUTUBE_API_SERVICE_NAME,
            config.YOUTUBE_API_VERSION,
            developerKey=config.YOUTUBE_API_KEY
        )
        self.quota_manager = QuotaManager()
        self.error_handler = ErrorHandler()
        self.email_finder = InfluencerEmailFinder()
        
    def search_channels(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search for YouTube channels matching the query.
        
        Args:
            query: Search term for finding channels (e.g., "AI researchers")
            max_results: Maximum number of channels to return
            
        Returns:
            List of channel data dictionaries
        """
        channels = []
        
        # Check quota before making request
        if not self.quota_manager.can_make_request(config.QUOTA_PER_SEARCH):
            logger.error("Insufficient quota for search request")
            raise Exception("YouTube API quota exhausted. Please wait for daily reset.")
        
        try:
            # Search for channels
            search_request = self.youtube.search().list(
                q=query,
                part="snippet",
                type="channel",
                maxResults=min(max_results, config.MAX_RESULTS_PER_SEARCH),
                order="relevance"
            )
            
            search_response = self._execute_with_retry(search_request)
            self.quota_manager.record_request(config.QUOTA_PER_SEARCH)
            
            # Extract channel IDs
            channel_ids = [item["id"]["channelId"] for item in search_response.get("items", [])]
            
            if channel_ids:
                # Fetch detailed channel information
                channels = self._fetch_channel_details(channel_ids)
            
            logger.info(f"Found {len(channels)} channels for query: {query}")
            return channels
            
        except HttpError as e:
            error_msg = f"YouTube API error: {e}"
            logger.error(error_msg)
            self.error_handler.handle_api_error(e, "search_channels")
            raise
    
    def _fetch_channel_details(self, channel_ids: List[str]) -> List[Dict]:
        """
        Fetch detailed information for a list of channel IDs.
        
        Args:
            channel_ids: List of YouTube channel IDs
            
        Returns:
            List of detailed channel information
        """
        # Check quota for channel details request
        quota_needed = len(channel_ids) * config.QUOTA_PER_CHANNEL
        if not self.quota_manager.can_make_request(quota_needed):
            logger.warning(f"Insufficient quota for fetching {len(channel_ids)} channels")
            # Fetch as many as quota allows
            available_channels = self.quota_manager.get_remaining_quota() // config.QUOTA_PER_CHANNEL
            if available_channels > 0:
                channel_ids = channel_ids[:available_channels]
                logger.info(f"Fetching {available_channels} channels due to quota limits")
            else:
                raise Exception("Insufficient quota for channel details")
        
        try:
            # Fetch channel details
            channels_request = self.youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                id=",".join(channel_ids)
            )
            
            channels_response = self._execute_with_retry(channels_request)
            self.quota_manager.record_request(len(channel_ids) * config.QUOTA_PER_CHANNEL)
            
            # Process channel data
            channels = []
            for item in channels_response.get("items", []):
                channel_data = self._extract_channel_data(item)
                channels.append(channel_data)
            
            return channels
            
        except HttpError as e:
            error_msg = f"Error fetching channel details: {e}"
            logger.error(error_msg)
            self.error_handler.handle_api_error(e, "fetch_channel_details")
            raise
    
    def _extract_channel_data(self, channel_item: Dict) -> Dict:
        """
        Extract relevant data from YouTube API channel response.
        
        Args:
            channel_item: Raw channel data from YouTube API
            
        Returns:
            Processed channel data dictionary
        """
        snippet = channel_item.get("snippet", {})
        statistics = channel_item.get("statistics", {})
        branding = channel_item.get("brandingSettings", {})
        
        # Basic channel data
        description = snippet.get("description", "")
        channel_data = {
            "channel_name": snippet.get("title", ""),
            "channel_id": channel_item.get("id", ""),
            "channel_description": description,
            "subscriber_count": statistics.get("subscriberCount", "0"),
            "view_count": statistics.get("viewCount", "0"),
            "video_count": statistics.get("videoCount", "0"),
            "country": snippet.get("country", ""),
            "custom_url": snippet.get("customUrl", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "keywords": branding.get("channel", {}).get("keywords", ""),
            "raw_data": channel_item  # Store raw data for debugging
        }
        
        # Extract website and social links from description
        website, social_links = self._extract_links_from_description(description)
        channel_data["website"] = website
        channel_data["social_links"] = social_links
        
        # Use InfluencerEmailFinder to find creator email
        email_result = self.email_finder.find_creator_email(channel_data)
        
        # Add email info to channel data
        channel_data["business_email"] = email_result.get("email", "")
        channel_data["email_confidence"] = email_result.get("confidence", 0)
        channel_data["email_source"] = email_result.get("source", "")
        channel_data["email_verified"] = email_result.get("verified", False)
        
        # If no email found, provide YouTube About URL as fallback
        if not channel_data["business_email"] and "youtube_about" in email_result:
            channel_data["youtube_about_url"] = email_result["youtube_about"]
        
        # Add alternative emails if available
        if "alternatives" in email_result:
            channel_data["alternative_emails"] = email_result["alternatives"]
        
        return channel_data
    
    def _extract_links_from_description(self, description: str) -> tuple:
        """
        Extract website and social media links from channel description.
        
        Args:
            description: Channel description text
            
        Returns:
            Tuple of (website, social_links_list)
        """
        import re
        
        # Common URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, description)
        
        website = ""
        social_links = []
        
        for url in urls:
            url_lower = url.lower()
            if any(social in url_lower for social in ["twitter.com", "instagram.com", "facebook.com", "linkedin.com", "tiktok.com"]):
                social_links.append(url)
            elif not website and not any(yt in url_lower for yt in ["youtube.com", "youtu.be"]):
                website = url
        
        return website, ", ".join(social_links)
    
    def _execute_with_retry(self, request, max_retries=3):
        """
        Execute YouTube API request with retry logic.
        
        Args:
            request: YouTube API request object
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response
        """
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status == 403 and "quotaExceeded" in str(e):
                    logger.error("YouTube API quota exceeded")
                    self.quota_manager.handle_quota_exceeded()
                    raise
                elif e.resp.status in [500, 502, 503, 504]:
                    logger.warning(f"YouTube API temporary error: {e.resp.status} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        raise
                else:
                    raise
    
    def fetch_channels_for_topic(self, topic: str, max_channels: int = 20) -> List[Dict]:
        """
        Main method to fetch channels for a given podcast topic.
        
        Args:
            topic: Podcast topic/niche query
            max_channels: Maximum number of channels to fetch
            
        Returns:
            List of channel data ready for processing
        """
        logger.info(f"Fetching channels for topic: {topic}")
        print(f"\n🔍 Searching YouTube for: {topic}")
        
        try:
            channels = self.search_channels(topic, max_channels)
            print(f"✅ Found {len(channels)} channels")
            
            # Log quota usage
            quota_used = self.quota_manager.get_used_quota()
            quota_remaining = config.YOUTUBE_DAILY_QUOTA - quota_used
            print(f"📊 Quota used: {quota_used}/{config.YOUTUBE_DAILY_QUOTA} ({quota_remaining} remaining)")
            
            return channels
            
        except Exception as e:
            logger.error(f"Failed to fetch channels: {e}")
            print(f"❌ Error fetching channels: {e}")
            raise