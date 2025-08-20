"""
Google Podcasts / YouTube Music podcasts scraper.
Since Google Podcasts was discontinued, this focuses on YouTube Music podcast content.
"""

import re
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from botasaurus.browser import browser, Driver

from ..base import BasePlatformScraper, PodcastData
from ..config import config

logger = logging.getLogger(__name__)


@browser(headless=True, block_images=True)
def search_youtube_podcasts(driver: Driver, data: Dict[str, Any]):
    """
    Search YouTube for podcast content using Botasaurus.
    
    Args:
        driver: Botasaurus Driver instance
        data: Search parameters
        
    Returns:
        Dict with search results
    """
    query = data.get('query', '')
    limit = data.get('limit', 50)
    
    results = {
        'query': query,
        'podcasts': [],
        'error': None
    }
    
    try:
        # Search YouTube for podcast content
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query + ' podcast')}"
        
        logger.info(f"Searching YouTube for: {query}")
        driver.get(search_url)
        driver.sleep(3)
        
        # Get page source for parsing
        page_source = driver.page_source
        
        # Extract video/channel information from YouTube search results
        # YouTube search results are in JSON-LD format embedded in the page
        
        # Look for channel links (podcast shows often have dedicated channels)
        channel_pattern = r'/channel/([A-Za-z0-9_-]{24})'
        channel_matches = re.findall(channel_pattern, page_source)
        
        # Look for video titles that might be podcasts
        title_pattern = r'"title":{"runs":\[{"text":"([^"]+)"}\]'
        title_matches = re.findall(title_pattern, page_source)
        
        # Look for channel names
        channel_name_pattern = r'"ownerText":{"runs":\[{"text":"([^"]+)"'
        channel_name_matches = re.findall(channel_name_pattern, page_source)
        
        # Look for view counts and video IDs
        video_id_pattern = r'"videoId":"([A-Za-z0-9_-]{11})"'
        video_ids = re.findall(video_id_pattern, page_source)
        
        logger.info(f"Found {len(title_matches)} video titles, {len(channel_matches)} channels")
        
        # Combine the extracted data
        podcast_candidates = []
        
        for i, title in enumerate(title_matches[:limit]):
            try:
                # Skip if title doesn't look like a podcast
                if not _looks_like_podcast(title):
                    continue
                
                channel_name = channel_name_matches[i] if i < len(channel_name_matches) else None
                video_id = video_ids[i] if i < len(video_ids) else None
                
                podcast_info = {
                    'title': title,
                    'channel_name': channel_name,
                    'video_id': video_id,
                    'youtube_url': f"https://www.youtube.com/watch?v={video_id}" if video_id else None
                }
                
                podcast_candidates.append(podcast_info)
                
            except Exception as e:
                logger.debug(f"Error processing YouTube result {i}: {e}")
                continue
        
        results['podcasts'] = podcast_candidates[:limit]
        logger.info(f"Extracted {len(results['podcasts'])} podcast candidates")
        
    except Exception as e:
        logger.error(f"Error searching YouTube for podcasts: {e}")
        results['error'] = str(e)
    
    return results


def _looks_like_podcast(title: str) -> bool:
    """Check if a title looks like a podcast episode or show."""
    title_lower = title.lower()
    
    podcast_indicators = [
        'podcast', 'episode', 'ep ', '#', 'interview', 'conversation',
        'talk', 'discussion', 'show', 'series', 'season'
    ]
    
    # Must have at least one podcast indicator
    has_indicator = any(indicator in title_lower for indicator in podcast_indicators)
    
    # Skip obvious non-podcasts
    skip_terms = [
        'music video', 'official video', 'trailer', 'clip', 'highlights',
        'live stream', 'compilation', 'best of', 'reaction'
    ]
    
    has_skip_term = any(term in title_lower for term in skip_terms)
    
    return has_indicator and not has_skip_term


class GooglePodcastsScraper(BasePlatformScraper):
    """Scraper for podcast content via YouTube (since Google Podcasts discontinued)."""
    
    def __init__(self):
        """Initialize Google/YouTube podcasts scraper."""
        super().__init__()
        self.platform_name = "YouTube/Google Podcasts"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
        
        # Topic to search query mapping
        self.topic_queries = {
            "artificial intelligence": "artificial intelligence AI podcast interview",
            "ai": "AI machine learning podcast discussion", 
            "technology": "technology tech podcast startup",
            "business": "business entrepreneur podcast interview",
            "startup": "startup founder podcast conversation",
            "health": "health wellness podcast discussion",
            "fitness": "fitness health podcast tips",
            "science": "science research podcast interview",
            "education": "education learning podcast conversation",
            "news": "news analysis podcast discussion",
            "politics": "politics government podcast interview",
            "history": "history historical podcast stories",
            "comedy": "comedy podcast funny interview",
            "entertainment": "entertainment podcast celebrity interview",
            "music": "music industry podcast interview",
            "sports": "sports podcast interview athlete",
            "true crime": "true crime podcast investigation",
            "crime": "crime investigation podcast mystery"
        }
    
    def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
        """
        Scrape podcast content from YouTube for a given topic.
        
        Args:
            topic: Search topic
            limit: Maximum number of podcasts to return
            
        Returns:
            List of PodcastData objects
        """
        self.logger.info(f"Starting YouTube podcast scrape for topic: {topic}")
        
        # Get search query for topic
        search_query = self._get_search_query(topic)
        self.logger.info(f"Using YouTube search query: {search_query}")
        
        # Search YouTube using Botasaurus
        search_results = search_youtube_podcasts({
            'query': search_query,
            'limit': limit
        })
        
        if search_results.get('error'):
            self.logger.error(f"YouTube search error: {search_results['error']}")
            return []
        
        podcast_candidates = search_results.get('podcasts', [])
        self.logger.info(f"Found {len(podcast_candidates)} podcast candidates from YouTube")
        
        # Convert to PodcastData objects
        podcasts_data = []
        
        for i, candidate in enumerate(podcast_candidates):
            try:
                self.logger.info(f"Processing candidate {i+1}/{len(podcast_candidates)}: {candidate.get('title')}")
                
                podcast = self._parse_youtube_podcast(candidate)
                
                if podcast and self.validate_podcast_data(podcast):
                    podcasts_data.append(podcast)
                    self.logger.info(f"Successfully processed: {podcast.podcast_name}")
                
            except Exception as e:
                self.logger.warning(f"Error processing YouTube candidate: {e}")
                continue
        
        self.scraped_podcasts = podcasts_data
        self.logger.info(f"Completed YouTube podcast scraping: {len(podcasts_data)} valid podcasts")
        
        return podcasts_data
    
    def _get_search_query(self, topic: str) -> str:
        """Convert topic to YouTube search query."""
        topic_lower = topic.lower()
        
        # Check for exact matches first
        if topic_lower in self.topic_queries:
            return self.topic_queries[topic_lower]
        
        # Check for partial matches
        for key, query in self.topic_queries.items():
            if key in topic_lower or topic_lower in key:
                return query
        
        # Default: use topic with podcast keywords
        return f"{topic} podcast interview discussion"
    
    def _parse_youtube_podcast(self, candidate: Dict[str, Any]) -> Optional[PodcastData]:
        """
        Parse YouTube podcast candidate into PodcastData object.
        
        Args:
            candidate: YouTube video/channel data
            
        Returns:
            PodcastData object or None if parsing fails
        """
        try:
            title = candidate.get('title', '')
            channel_name = candidate.get('channel_name', '')
            youtube_url = candidate.get('youtube_url', '')
            
            # Clean and parse the title to extract show name vs episode
            podcast_name, episode_info = self._parse_podcast_title(title)
            
            # Try to determine host name
            host_name = None
            if channel_name:
                # Channel name might be the host name or show name
                if channel_name.lower() != podcast_name.lower():
                    host_name = channel_name
            
            # Create podcast data
            podcast = PodcastData(
                podcast_name=self.clean_text(podcast_name),
                host_name=self.clean_text(host_name) if host_name else None,
                podcast_description=f"Podcast content from YouTube channel: {channel_name}" if channel_name else None,
                platform_source="YouTube/Google Podcasts",
                raw_data=candidate
            )
            
            # Set YouTube URL as the main reference
            if youtube_url:
                podcast.podcast_website = youtube_url
            
            # Try to extract additional info from title
            if episode_info:
                podcast.raw_data['episode_info'] = episode_info
            
            return podcast
            
        except Exception as e:
            self.logger.error(f"Error parsing YouTube podcast data: {e}")
            return None
    
    def _parse_podcast_title(self, title: str) -> tuple[str, Optional[str]]:
        """
        Parse podcast title to extract show name and episode info.
        
        Args:
            title: Full video title
            
        Returns:
            Tuple of (show_name, episode_info)
        """
        # Common patterns for podcast titles
        patterns = [
            # "Show Name - Episode Title" or "Show Name: Episode Title"
            r'^([^-:]+)[-:](.+)$',
            # "Show Name #123: Episode Title"  
            r'^([^#]+)#\d+:(.+)$',
            # "Show Name Ep 123 - Episode Title"
            r'^(.+?)(?:Episode|Ep)\s*\d+[-:](.+)$',
            # "Episode Title | Show Name"
            r'^([^|]+)\|\s*(.+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                part1 = match.group(1).strip()
                part2 = match.group(2).strip()
                
                # Determine which part is likely the show name
                if 'podcast' in part1.lower() or 'show' in part1.lower():
                    return part1, part2
                elif 'podcast' in part2.lower() or 'show' in part2.lower():
                    return part2, part1
                else:
                    # Default: first part is show name
                    return part1, part2
        
        # If no pattern matches, use the full title as show name
        return title, None


class PodcastIndexScraper(BasePlatformScraper):
    """Scraper for Podcast Index API - open podcast directory."""
    
    def __init__(self):
        """Initialize Podcast Index scraper."""
        super().__init__()
        self.platform_name = "Podcast Index"
        self.base_url = "https://api.podcastindex.org/api/1.0"
        
        # Would need API credentials for full functionality
        self.api_key = None
        self.api_secret = None
    
    def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
        """
        Scrape podcasts from Podcast Index API.
        
        Note: This is a placeholder - would need API credentials for full implementation.
        """
        self.logger.info("Podcast Index scraper - placeholder implementation")
        
        # For now, return empty list since we don't have API credentials
        # In a full implementation, this would:
        # 1. Use Podcast Index API to search for podcasts by topic
        # 2. Parse the results into PodcastData objects
        # 3. Return the list of podcasts
        
        return []