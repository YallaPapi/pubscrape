"""
Apple Podcasts scraper using Botasaurus for anti-detection.
Scrapes Apple Podcasts charts and parses RSS feeds for podcast metadata.
"""

import re
import logging
import feedparser
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from botasaurus.browser import browser, Driver

from ..base import BasePlatformScraper, PodcastData

logger = logging.getLogger(__name__)


def safe_strip(text):
    """Safely strip text, handling any type of input."""
    if text is None:
        return ""
    if hasattr(text, 'text'):
        text = text.text
    if not isinstance(text, str):
        text = str(text) if text else ""
    return text.strip() if text else ""


@browser(
    headless=True,
    block_images=True,  # Faster loading
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
def scrape_apple_podcasts_charts(driver: Driver, data: Dict[str, Any]):
    """
    Scrape Apple Podcasts charts using Botasaurus.
    
    Args:
        driver: Botasaurus Driver instance
        data: Dict containing 'category' and 'limit'
        
    Returns:
        Dict with scraped podcast URLs and metadata
    """
    category = data.get("category", "arts")
    limit = data.get("limit", 100)
    
    results = {
        "category": category,
        "podcast_urls": [],
        "error": None
    }
    
    try:
        # Apple Podcasts chart URL
        chart_url = f"https://podcasts.apple.com/us/genre/podcasts-{category}/id1310"
        
        logger.info(f"Scraping Apple Podcasts {category} chart...")
        driver.get(chart_url)
        
        # Wait for content to load
        driver.sleep(3)
        
        # Find podcast links - Apple uses dynamic class names, so we use more stable selectors
        podcast_links = driver.select('a[href*="/us/podcast/"]')
        
        if not podcast_links:
            # Fallback: try different selectors
            podcast_links = driver.select('a[href*="podcast"]')
        
        # Convert single element or list to list
        if podcast_links is None:
            podcast_links = []
        elif not isinstance(podcast_links, list):
            podcast_links = [podcast_links] if podcast_links else []
        
        logger.info(f"Found {len(podcast_links)} podcast links")
        
        for link in podcast_links[:limit]:
            try:
                # Try different ways to get href attribute from Botasaurus element
                href = None
                
                # Method 1: Direct attribute access
                try:
                    href = link.get_attribute('href')
                except:
                    pass
                    
                # Method 2: Via driver
                if not href:
                    try:
                        href = driver.get_attribute(link, 'href')
                    except:
                        pass
                
                # Method 3: Check if it's a selenium-like element
                if not href:
                    try:
                        if hasattr(link, 'get_attribute'):
                            href = link.get_attribute('href')
                        elif hasattr(link, 'getAttribute'):
                            href = link.getAttribute('href')
                    except:
                        pass
                
                logger.debug(f"Link href value: {href} (type: {type(href)})")
                
                if href is None:
                    logger.debug("Href is None, skipping")
                    continue
                    
                # Ensure href is a string - handle case where href might be an Element
                if hasattr(href, 'text'):
                    href_str = href.text
                else:
                    href_str = str(href)
                
                # Ensure href_str is definitely a string
                if not isinstance(href_str, str):
                    href_str = str(href_str) if href_str else ''
                    
                href_str = safe_strip(href_str)
                
                if not href_str:
                    logger.debug("Empty href, skipping")
                    continue
                
                if '/podcast/' in href_str and href_str.startswith('/'):
                    # Convert relative URL to absolute
                    full_url = f"https://podcasts.apple.com{href_str}"
                    results["podcast_urls"].append(full_url)
                    logger.debug(f"Added relative URL: {full_url}")
                elif href_str.startswith('https://podcasts.apple.com') and '/podcast/' in href_str:
                    results["podcast_urls"].append(href_str)
                    logger.debug(f"Added absolute URL: {href_str}")
                else:
                    logger.debug(f"Skipped URL (doesn't match pattern): {href_str}")
            except Exception as e:
                logger.warning(f"Error processing link: {e}")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"Collected {len(results['podcast_urls'])} podcast URLs from charts")
        
    except Exception as e:
        logger.error(f"Error scraping Apple Podcasts charts: {e}")
        results["error"] = str(e)
    
    return results


@browser(
    headless=True,
    block_images=True,
)
def scrape_podcast_page(driver: Driver, podcast_url: str):
    """
    Scrape individual podcast page to get RSS feed URL and metadata.
    
    Args:
        driver: Botasaurus Driver instance  
        podcast_url: Apple Podcasts URL for specific podcast
        
    Returns:
        Dict with RSS feed URL and basic metadata
    """
    result = {
        "apple_url": podcast_url,
        "rss_feed_url": None,
        "podcast_name": None,
        "description": None,
        "error": None
    }
    
    try:
        logger.debug(f"Scraping podcast page: {podcast_url}")
        driver.get(podcast_url)
        driver.sleep(2)
        
        # Extract podcast name using element-based approach
        title_elem = driver.select('h1[data-testid="non-editable-product-title"]')
        if not title_elem:
            title_elem = driver.select('h1.product-header__title')
        if not title_elem:
            title_elem = driver.select('h1')
        
        if title_elem:
            result["podcast_name"] = safe_strip(title_elem.text if hasattr(title_elem, 'text') else str(title_elem))
        else:
            result["podcast_name"] = ""
        
        # Extract description using element-based approach
        desc_elem = driver.select('[data-testid="description"]')
        if not desc_elem:
            desc_elem = driver.select('.product-header__description')
        if not desc_elem:
            desc_elem = driver.select('p[dir="ltr"]')
        
        if desc_elem:
            result["description"] = safe_strip(desc_elem.text if hasattr(desc_elem, 'text') else str(desc_elem))
        else:
            result["description"] = ""
        
        # Look for RSS feed link in page source
        try:
            page_source = driver.page_source
        except AttributeError:
            # Try alternative method if page_source doesn't exist
            try:
                page_source = driver.execute_script("return document.documentElement.outerHTML")
            except:
                page_source = ""
        
        # Method 1: Look for RSS feed URL in JavaScript or meta tags
        rss_patterns = [
            r'feedURL["\']:\s*["\']([^"\']+)["\']',
            r'rss["\']:\s*["\']([^"\']+)["\']',
            r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/rss\+xml["\']'
        ]
        
        for pattern in rss_patterns:
            match = re.search(pattern, page_source, re.IGNORECASE)
            if match:
                potential_rss = match.group(1)
                if potential_rss.startswith('http') and ('rss' in potential_rss.lower() or 'feed' in potential_rss.lower()):
                    result["rss_feed_url"] = potential_rss
                    logger.debug(f"Found RSS feed: {potential_rss}")
                    break
        
        # Method 2: Look for common RSS feed patterns in URLs
        if not result["rss_feed_url"]:
            url_matches = re.findall(r'https?://[^\s<>"\']+(?:rss|feed)[^\s<>"\']*', page_source, re.IGNORECASE)
            if url_matches:
                result["rss_feed_url"] = url_matches[0]
                logger.debug(f"Found RSS feed via URL pattern: {url_matches[0]}")
        
    except Exception as e:
        logger.error(f"Error scraping podcast page {podcast_url}: {e}")
        result["error"] = str(e)
    
    return result


class ApplePodcastsScraper(BasePlatformScraper):
    """Scraper for Apple Podcasts using Botasaurus."""
    
    def __init__(self):
        """Initialize Apple Podcasts scraper."""
        super().__init__()
        self.platform_name = "Apple Podcasts"
        
        # Apple Podcasts categories for discovery
        self.categories = {
            "arts": "Arts",
            "business": "Business", 
            "comedy": "Comedy",
            "education": "Education",
            "health-fitness": "Health & Fitness",
            "history": "History",
            "leisure": "Leisure",
            "music": "Music",
            "news": "News",
            "religion-spirituality": "Religion & Spirituality",
            "science": "Science",
            "society-culture": "Society & Culture",
            "sports": "Sports",
            "technology": "Technology",
            "true-crime": "True Crime"
        }
    
    def scrape_podcasts(self, topic: str, limit: int = 100) -> List[PodcastData]:
        """
        Scrape podcasts from Apple Podcasts for a given topic.
        
        Args:
            topic: Search topic (maps to Apple Podcasts categories)
            limit: Maximum number of podcasts to scrape
            
        Returns:
            List of PodcastData objects
        """
        self.logger.info(f"Starting Apple Podcasts scrape for topic: {topic}")
        
        # Map topic to Apple Podcasts category
        category = self._map_topic_to_category(topic)
        self.logger.info(f"Using Apple Podcasts category: {category}")
        
        # Step 1: Get podcast URLs from charts
        chart_data = scrape_apple_podcasts_charts({
            "category": category,
            "limit": limit
        })
        
        if chart_data.get("error"):
            self.logger.error(f"Error getting chart data: {chart_data['error']}")
            return []
        
        podcast_urls = chart_data.get("podcast_urls", [])
        self.logger.info(f"Found {len(podcast_urls)} podcast URLs from charts")
        
        if not podcast_urls:
            self.logger.warning("No podcast URLs found from charts")
            return []
        
        # Step 2: Scrape individual podcast pages for RSS feeds
        podcasts_data = []
        
        for i, url in enumerate(podcast_urls[:limit]):
            try:
                self.logger.info(f"Processing podcast {i+1}/{len(podcast_urls[:limit])}: {url}")
                
                # Get RSS feed and basic metadata
                page_data = scrape_podcast_page(url)
                
                if page_data.get("error"):
                    self.logger.warning(f"Error scraping page {url}: {page_data['error']}")
                    continue
                
                # Step 3: Parse RSS feed for detailed metadata
                podcast = self._parse_podcast_data(page_data)
                
                if podcast and self.validate_podcast_data(podcast):
                    podcasts_data.append(podcast)
                    self.logger.info(f"Successfully processed: {podcast.podcast_name}")
                else:
                    self.logger.warning(f"Invalid podcast data for URL: {url}")
                
            except Exception as e:
                self.logger.error(f"Error processing podcast URL {url}: {e}")
                continue
        
        self.scraped_podcasts = podcasts_data
        self.logger.info(f"Completed Apple Podcasts scraping: {len(podcasts_data)} valid podcasts")
        
        return podcasts_data
    
    def _map_topic_to_category(self, topic: str) -> str:
        """
        Map search topic to Apple Podcasts category.
        
        Args:
            topic: Search topic
            
        Returns:
            Apple Podcasts category slug
        """
        topic_lower = topic.lower()
        
        # Topic mapping
        topic_mapping = {
            "artificial intelligence": "technology",
            "ai": "technology", 
            "machine learning": "technology",
            "tech": "technology",
            "technology": "technology",
            "startup": "business",
            "entrepreneur": "business",
            "business": "business",
            "marketing": "business",
            "productivity": "business",
            "health": "health-fitness",
            "wellness": "health-fitness",
            "fitness": "health-fitness", 
            "science": "science",
            "education": "education",
            "learning": "education",
            "news": "news",
            "politics": "news",
            "history": "history",
            "comedy": "comedy",
            "entertainment": "leisure",
            "music": "music",
            "arts": "arts",
            "culture": "society-culture",
            "society": "society-culture",
            "sports": "sports",
            "true crime": "true-crime",
            "crime": "true-crime"
        }
        
        # Check for exact matches first
        for key, category in topic_mapping.items():
            if key in topic_lower:
                return category
        
        # Default to technology for unknown topics (good for AI/tech focus)
        return "technology"
    
    def _parse_podcast_data(self, page_data: Dict[str, Any]) -> Optional[PodcastData]:
        """
        Parse scraped page data and RSS feed into PodcastData object.
        
        Args:
            page_data: Data from scraping podcast page
            
        Returns:
            PodcastData object or None if parsing fails
        """
        try:
            # Create base podcast data from page
            podcast = PodcastData(
                podcast_name=self.clean_text(page_data.get("podcast_name", "")),
                podcast_description=self.clean_text(page_data.get("description", "")),
                apple_podcasts_url=page_data.get("apple_url"),
                rss_feed_url=page_data.get("rss_feed_url"),
                platform_source="Apple Podcasts",
                raw_data=page_data
            )
            
            # Try to extract host from description
            if podcast.podcast_description:
                podcast.host_name = self.extract_host_from_description(podcast.podcast_description)
            
            # If we have RSS feed, parse it for more details
            if page_data.get("rss_feed_url"):
                self._enrich_with_rss_data(podcast, page_data["rss_feed_url"])
            
            return podcast
            
        except Exception as e:
            self.logger.error(f"Error parsing podcast data: {e}")
            return None
    
    def _enrich_with_rss_data(self, podcast: PodcastData, rss_url: str) -> None:
        """
        Enrich podcast data with information from RSS feed.
        
        Args:
            podcast: PodcastData object to enrich
            rss_url: RSS feed URL to parse
        """
        try:
            self.logger.debug(f"Parsing RSS feed: {rss_url}")
            
            # Parse RSS feed
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                self.logger.warning(f"RSS feed may be malformed: {rss_url}")
            
            # Extract feed-level data
            if hasattr(feed, 'feed'):
                feed_data = feed.feed
                
                # Update description if we have a better one
                if hasattr(feed_data, 'description') and feed_data.description:
                    if not podcast.podcast_description or len(feed_data.description) > len(podcast.podcast_description):
                        podcast.podcast_description = self.clean_text(feed_data.description)
                
                # Try to get website
                if hasattr(feed_data, 'link') and feed_data.link:
                    podcast.podcast_website = feed_data.link
                
                # Get episode count
                if hasattr(feed, 'entries'):
                    podcast.episode_count = len(feed.entries)
                
                # Try to extract host from feed metadata
                if hasattr(feed_data, 'author') and feed_data.author and not podcast.host_name:
                    podcast.host_name = self.clean_text(feed_data.author)
                
                # Look for iTunes-specific tags that might have contact info
                if hasattr(feed_data, 'tags'):
                    for tag in feed_data.tags:
                        if 'author' in tag.get('term', '').lower() and not podcast.host_name:
                            podcast.host_name = self.clean_text(tag.get('label', ''))
                        elif 'email' in tag.get('term', '').lower():
                            # Found email in iTunes tags
                            email = tag.get('label', '')
                            if '@' in email:
                                podcast.host_email = email
        
        except Exception as e:
            self.logger.warning(f"Error parsing RSS feed {rss_url}: {e}")
            # Don't fail the whole podcast for RSS errors
            pass