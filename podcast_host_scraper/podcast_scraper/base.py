"""
Base classes for podcast platform scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PodcastData:
    """Standard podcast data structure."""
    
    # Core podcast information
    podcast_name: str
    host_name: Optional[str] = None
    podcast_description: Optional[str] = None
    
    # URLs and links
    podcast_website: Optional[str] = None
    rss_feed_url: Optional[str] = None
    apple_podcasts_url: Optional[str] = None
    
    # Metrics
    estimated_downloads: Optional[str] = None
    episode_count: Optional[int] = None
    rating: Optional[float] = None
    
    # Contact information (to be filled by contact extraction)
    host_email: Optional[str] = None
    booking_email: Optional[str] = None
    contact_page_url: Optional[str] = None
    
    # Social media
    social_links: Optional[Dict[str, str]] = None
    
    # AI scoring (to be filled by AI module)
    ai_relevance_score: Optional[int] = None
    
    # Metadata
    platform_source: str = "unknown"
    contact_confidence: str = "unknown"
    last_updated: str = ""
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.last_updated == "":
            self.last_updated = datetime.now().isoformat()
        
        if self.social_links is None:
            self.social_links = {}
        
        if self.raw_data is None:
            self.raw_data = {}


class BasePlatformScraper(ABC):
    """Abstract base class for all podcast platform scrapers."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.scraped_podcasts: List[PodcastData] = []
    
    @abstractmethod
    def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
        """
        Scrape podcasts for a given topic.
        
        Args:
            topic: Search topic (e.g., "artificial intelligence")
            limit: Maximum number of podcasts to return
            
        Returns:
            List of PodcastData objects
        """
        pass
    
    def get_platform_name(self) -> str:
        """Get the platform name."""
        return self.name.replace("Scraper", "").replace("Platform", "")
    
    def validate_podcast_data(self, podcast: PodcastData) -> bool:
        """
        Validate that podcast data meets minimum requirements.
        
        Args:
            podcast: PodcastData to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Minimum requirements
        if not podcast.podcast_name:
            self.logger.warning("Podcast missing name")
            return False
        
        # Ensure name is a string
        name = podcast.podcast_name
        if hasattr(name, 'text'):
            name = name.text
        elif not isinstance(name, str):
            name = str(name) if name else ""
        
        if len(name.strip()) == 0:
            self.logger.warning("Podcast missing name")
            return False
        
        # At least one of these should be present
        if not any([
            podcast.podcast_website,
            podcast.rss_feed_url,
            podcast.apple_podcasts_url,
            podcast.host_email
        ]):
            self.logger.warning(f"Podcast '{podcast.podcast_name}' has no discoverable contact info")
            return False
        
        return True
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text fields.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Ensure text is a string
        if hasattr(text, 'text'):
            text = text.text
        elif not isinstance(text, str):
            text = str(text) if text else ""
        
        # Remove extra whitespace
        cleaned = " ".join(text.strip().split())
        
        # Remove common HTML entities
        cleaned = cleaned.replace("&amp;", "&")
        cleaned = cleaned.replace("&lt;", "<")
        cleaned = cleaned.replace("&gt;", ">")
        cleaned = cleaned.replace("&quot;", '"')
        cleaned = cleaned.replace("&#39;", "'")
        
        return cleaned
    
    def extract_host_from_description(self, description: str) -> Optional[str]:
        """
        Try to extract host name from podcast description.
        
        Args:
            description: Podcast description text
            
        Returns:
            Host name if found, None otherwise
        """
        if not description:
            return None
        
        import re
        
        # Common patterns for host identification
        patterns = [
            r"hosted by ([A-Za-z\s]+)",
            r"with host ([A-Za-z\s]+)",
            r"your host ([A-Za-z\s]+)",
            r"I'm ([A-Za-z\s]+),",
            r"I am ([A-Za-z\s]+),",
            r"This is ([A-Za-z\s]+) and",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                host = match.group(1).strip()
                # Filter out overly generic matches
                if len(host) > 3 and len(host) < 50 and host.replace(" ", "").isalpha():
                    return host
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get scraping statistics.
        
        Returns:
            Dictionary with scraping stats
        """
        total = len(self.scraped_podcasts)
        
        if total == 0:
            return {"total": 0, "valid": 0, "with_websites": 0, "with_emails": 0}
        
        valid = sum(1 for p in self.scraped_podcasts if self.validate_podcast_data(p))
        with_websites = sum(1 for p in self.scraped_podcasts if p.podcast_website)
        with_emails = sum(1 for p in self.scraped_podcasts if p.host_email or p.booking_email)
        with_hosts = sum(1 for p in self.scraped_podcasts if p.host_name)
        
        return {
            "total_scraped": total,
            "valid_podcasts": valid,
            "validation_rate": f"{(valid/total*100):.1f}%" if total > 0 else "0%",
            "with_websites": with_websites,
            "website_rate": f"{(with_websites/total*100):.1f}%" if total > 0 else "0%",
            "with_emails": with_emails,
            "email_rate": f"{(with_emails/total*100):.1f}%" if total > 0 else "0%",
            "with_host_names": with_hosts,
            "host_name_rate": f"{(with_hosts/total*100):.1f}%" if total > 0 else "0%",
            "platform": self.get_platform_name()
        }