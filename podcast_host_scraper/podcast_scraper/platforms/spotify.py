"""
Spotify podcast scraper for discovering podcasts and metadata.
Uses Spotify Web API for legitimate podcast discovery.
"""

import re
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List, Dict, Any, Optional

from ..base import BasePlatformScraper, PodcastData
from ..config import config

logger = logging.getLogger(__name__)


class SpotifyPodcastsScraper(BasePlatformScraper):
    """Scraper for Spotify Podcasts using official API."""
    
    def __init__(self):
        """Initialize Spotify scraper."""
        super().__init__()
        self.platform_name = "Spotify"
        self.spotify = None
        
        # Initialize Spotify client if credentials available
        if config.has_spotify_keys():
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=config.SPOTIFY_CLIENT_ID,
                    client_secret=config.SPOTIFY_CLIENT_SECRET
                )
                self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                self.logger.info("Spotify API client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Spotify client: {e}")
        else:
            self.logger.warning("Spotify API keys not available")
        
        # Topic to Spotify search query mapping
        self.topic_queries = {
            "artificial intelligence": "artificial intelligence AI technology",
            "ai": "artificial intelligence machine learning",
            "technology": "technology tech startup",
            "business": "business entrepreneur startup",
            "startup": "startup entrepreneur business",
            "health": "health wellness fitness",
            "fitness": "fitness health wellness",
            "science": "science research innovation",
            "education": "education learning knowledge",
            "news": "news current events politics",
            "politics": "politics government news",
            "history": "history historical past",
            "comedy": "comedy humor funny",
            "entertainment": "entertainment celebrity pop culture",
            "music": "music musician artist",
            "sports": "sports athletics competition",
            "true crime": "true crime mystery investigation",
            "crime": "crime investigation mystery"
        }
    
    def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
        """
        Scrape podcasts from Spotify for a given topic.
        
        Args:
            topic: Search topic
            limit: Maximum number of podcasts to return
            
        Returns:
            List of PodcastData objects
        """
        if not self.spotify:
            self.logger.error("Spotify client not available - check API credentials")
            return []
        
        self.logger.info(f"Starting Spotify scrape for topic: {topic}")
        
        # Get search query for topic
        search_query = self._get_search_query(topic)
        self.logger.info(f"Using Spotify search query: {search_query}")
        
        podcasts_data = []
        
        try:
            # Search for shows (podcasts)
            results = self.spotify.search(
                q=search_query,
                type='show',
                limit=min(limit, 50),  # Spotify API limit
                market='US'
            )
            
            shows = results.get('shows', {}).get('items', [])
            self.logger.info(f"Found {len(shows)} shows from Spotify API")
            
            for i, show in enumerate(shows):
                try:
                    self.logger.info(f"Processing show {i+1}/{len(shows)}: {show.get('name')}")
                    
                    podcast = self._parse_spotify_show(show)
                    
                    if podcast and self.validate_podcast_data(podcast):
                        podcasts_data.append(podcast)
                        self.logger.info(f"Successfully processed: {podcast.podcast_name}")
                    
                except Exception as e:
                    self.logger.warning(f"Error processing show {show.get('name', 'unknown')}: {e}")
                    continue
            
            # If we got fewer results than requested and there might be more, try additional searches
            if len(podcasts_data) < limit and len(shows) >= 50:
                additional_results = self._search_additional_terms(topic, limit - len(podcasts_data))
                podcasts_data.extend(additional_results)
            
        except Exception as e:
            self.logger.error(f"Error during Spotify search: {e}")
            return []
        
        self.scraped_podcasts = podcasts_data
        self.logger.info(f"Completed Spotify scraping: {len(podcasts_data)} valid podcasts")
        
        return podcasts_data
    
    def _get_search_query(self, topic: str) -> str:
        """Convert topic to Spotify search query."""
        topic_lower = topic.lower()
        
        # Check for exact matches first
        if topic_lower in self.topic_queries:
            return self.topic_queries[topic_lower]
        
        # Check for partial matches
        for key, query in self.topic_queries.items():
            if key in topic_lower or topic_lower in key:
                return query
        
        # Default: use topic as is with "podcast" added
        return f"{topic} podcast"
    
    def _parse_spotify_show(self, show: Dict[str, Any]) -> Optional[PodcastData]:
        """
        Parse Spotify show data into PodcastData object.
        
        Args:
            show: Spotify show object from API
            
        Returns:
            PodcastData object or None if parsing fails
        """
        try:
            # Extract basic information
            podcast_name = show.get('name', '')
            description = show.get('description', '')
            
            # Get external URLs
            external_urls = show.get('external_urls', {})
            spotify_url = external_urls.get('spotify', '')
            
            # Get images
            images = show.get('images', [])
            image_url = images[0]['url'] if images else None
            
            # Get publisher (often the host/network)
            publisher = show.get('publisher', '')
            
            # Extract host from description if possible
            host_name = self.extract_host_from_description(description)
            if not host_name and publisher:
                # Sometimes publisher is the host name
                host_name = publisher
            
            # Get episode count (total_episodes)
            episode_count = show.get('total_episodes', 0)
            
            # Create podcast data
            podcast = PodcastData(
                podcast_name=self.clean_text(podcast_name),
                host_name=self.clean_text(host_name) if host_name else None,
                podcast_description=self.clean_text(description),
                episode_count=episode_count,
                platform_source="Spotify",
                raw_data=show
            )
            
            # Add Spotify-specific URLs
            if spotify_url:
                podcast.rss_feed_url = None  # Spotify doesn't provide RSS directly
                # Store Spotify URL in raw data for reference
                podcast.raw_data['spotify_url'] = spotify_url
            
            # Try to extract website from description
            website_match = re.search(r'https?://[^\s<>"\']+\.(?:com|org|net|io|co)[^\s<>"\']*', description)
            if website_match:
                potential_website = website_match.group(0)
                # Clean up URL (remove trailing punctuation)
                potential_website = re.sub(r'[.,;!?]+$', '', potential_website)
                podcast.podcast_website = potential_website
            
            return podcast
            
        except Exception as e:
            self.logger.error(f"Error parsing Spotify show data: {e}")
            return None
    
    def _search_additional_terms(self, original_topic: str, remaining_limit: int) -> List[PodcastData]:
        """Search with additional terms to get more results."""
        additional_podcasts = []
        
        # Try variations of the original topic
        variations = [
            f"{original_topic} interview",
            f"{original_topic} discussion", 
            f"{original_topic} talk show",
            f"{original_topic} weekly",
            f"{original_topic} daily"
        ]
        
        for variation in variations:
            if len(additional_podcasts) >= remaining_limit:
                break
            
            try:
                results = self.spotify.search(
                    q=variation,
                    type='show',
                    limit=min(20, remaining_limit - len(additional_podcasts)),
                    market='US'
                )
                
                shows = results.get('shows', {}).get('items', [])
                
                for show in shows:
                    if len(additional_podcasts) >= remaining_limit:
                        break
                    
                    try:
                        podcast = self._parse_spotify_show(show)
                        if podcast and self.validate_podcast_data(podcast):
                            # Check for duplicates by name
                            existing_names = [p.podcast_name.lower() for p in additional_podcasts]
                            if podcast.podcast_name.lower() not in existing_names:
                                additional_podcasts.append(podcast)
                    
                    except Exception as e:
                        self.logger.debug(f"Error processing additional show: {e}")
                        continue
            
            except Exception as e:
                self.logger.debug(f"Error in additional search for '{variation}': {e}")
                continue
        
        self.logger.info(f"Found {len(additional_podcasts)} additional podcasts via variations")
        return additional_podcasts