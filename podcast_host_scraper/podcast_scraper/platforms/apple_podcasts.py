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
    """Safely strip text, handling Botasaurus Elements and non-strings."""
    try:
        if text is None:
            return ""
        # Try common element access patterns first
        if hasattr(text, 'get_attribute'):
            try:
                txt = text.get_attribute('textContent')
                if isinstance(txt, str) and txt.strip():
                    text = txt
            except Exception:
                pass
        if hasattr(text, 'text') and not isinstance(text, str):
            try:
                text = text.text
            except Exception:
                pass
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        return text.strip()
    except Exception:
        return str(text) if text is not None else ""


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
        
        # Collect links from elements
        collected: list[str] = []
        for link in podcast_links:
            try:
                href = None
                try:
                    href = link.get_attribute('href')
                except:
                    pass
                if not href and hasattr(link, 'get_attribute'):
                    try:
                        href = link.get_attribute('href')
                    except:
                        pass
                href_str = safe_strip(href)
                if not href_str:
                    continue
                if '/podcast/' in href_str and href_str.startswith('/'):
                    collected.append(f"https://podcasts.apple.com{href_str}")
                elif href_str.startswith('https://podcasts.apple.com') and '/podcast/' in href_str:
                    collected.append(href_str)
            except Exception:
                continue
        
        # Fallback: parse page source for more links
        try:
            page_source = driver.page_source
        except Exception:
            try:
                page_source = driver.execute_script("return document.documentElement.outerHTML")
            except Exception:
                page_source = ""
        import re as _re
        abs_links = _re.findall(r'https://podcasts\.apple\.com/[^"\']+/podcast/[^"\']+', page_source)
        rel_links = _re.findall(r'\s\"(/[^\"]*/podcast/[^\"]+)\"', page_source)
        for href in abs_links:
            collected.append(href)
        for href in rel_links:
            collected.append(f"https://podcasts.apple.com{href}")
        
        # Dedupe and trim to limit
        seen = set()
        for href in collected:
            if href not in seen:
                seen.add(href)
                results["podcast_urls"].append(href)
                if len(results["podcast_urls"]) >= limit:
                    break
        
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
        
        # Extract podcast name using robust element access
        title_elem = driver.select('h1[data-testid="non-editable-product-title"]') or driver.select('h1.product-header__title') or driver.select('h1')
        if title_elem:
            try:
                text_val = None
                if hasattr(title_elem, 'get_attribute'):
                    text_val = title_elem.get_attribute('textContent')
                if not text_val and hasattr(title_elem, 'text'):
                    text_val = title_elem.text
                result["podcast_name"] = safe_strip(text_val)
            except Exception:
                result["podcast_name"] = ""
        else:
            result["podcast_name"] = ""
        
        # Extract description using robust element access
        desc_elem = driver.select('[data-testid="description"]') or driver.select('.product-header__description') or driver.select('p[dir="ltr"]')
        if desc_elem:
            try:
                text_val = None
                if hasattr(desc_elem, 'get_attribute'):
                    text_val = desc_elem.get_attribute('textContent')
                if not text_val and hasattr(desc_elem, 'text'):
                    text_val = desc_elem.text
                result["description"] = safe_strip(text_val)
            except Exception:
                result["description"] = ""
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
                
                # Try to get website (prefer external site over directories)
                website_candidate = None
                if hasattr(feed_data, 'links'):
                    for link_obj in getattr(feed_data, 'links', []) or []:
                        href = link_obj.get('href') if isinstance(link_obj, dict) else getattr(link_obj, 'href', None)
                        typ = link_obj.get('type') if isinstance(link_obj, dict) else getattr(link_obj, 'type', '')
                        if href and ('apple.com' not in href and 'spotify.com' not in href and 'podcasts.apple.com' not in href):
                            if not typ or 'html' in str(typ).lower():
                                website_candidate = href
                                break
                if not website_candidate and hasattr(feed_data, 'link') and feed_data.link:
                    if ('apple.com' not in feed_data.link and 'spotify.com' not in feed_data.link):
                        website_candidate = feed_data.link
                if not website_candidate and hasattr(feed, 'entries') and feed.entries:
                    entry_link = getattr(feed.entries[0], 'link', None)
                    if entry_link and ('apple.com' not in entry_link and 'spotify.com' not in entry_link):
                        from urllib.parse import urlparse
                        parsed = urlparse(entry_link)
                        website_candidate = f"{parsed.scheme}://{parsed.netloc}"
                if website_candidate:
                    podcast.podcast_website = website_candidate
                
                # Get episode count
                if hasattr(feed, 'entries'):
                    podcast.episode_count = len(feed.entries)
                
                # Try to extract host from feed metadata
                if hasattr(feed_data, 'author') and feed_data.author and not podcast.host_name:
                    podcast.host_name = self.clean_text(feed_data.author)
                
                # Attempt to extract email from feed metadata and entries
                import re
                email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
                email_candidates = []
                author_detail = getattr(feed_data, 'author_detail', None)
                if author_detail:
                    email_val = getattr(author_detail, 'email', None) or (author_detail.get('email') if isinstance(author_detail, dict) else None)
                    if email_val:
                        email_candidates.append(str(email_val))
                for key in ['publisher', 'managingEditor', 'webMaster', 'owner', 'itunes_owner', 'subtitle', 'summary']:
                    val = getattr(feed_data, key, None)
                    if isinstance(val, (str, bytes)):
                        email_candidates.extend(re.findall(email_regex, str(val)))
                for entry in getattr(feed, 'entries', [])[:5]:
                    ad = getattr(entry, 'author_detail', None)
                    if ad:
                        ev = getattr(ad, 'email', None) or (ad.get('email') if isinstance(ad, dict) else None)
                        if ev:
                            email_candidates.append(str(ev))
                    for k in ['author', 'summary', 'subtitle', 'title']:
                        v = getattr(entry, k, None)
                        if isinstance(v, (str, bytes)):
                            email_candidates.extend(re.findall(email_regex, str(v)))
                for em in email_candidates:
                    if '@' in em:
                        podcast.host_email = em
                        break
                
                # Look for iTunes-specific tags that might have contact info
                if hasattr(feed_data, 'tags'):
                    for tag in feed_data.tags:
                        term = tag.get('term', '') if isinstance(tag, dict) else ''
                        label = tag.get('label', '') if isinstance(tag, dict) else ''
                        if 'author' in term.lower() and not podcast.host_name:
                            podcast.host_name = self.clean_text(label)
                        elif 'email' in term.lower() and not podcast.host_email:
                            if '@' in label:
                                podcast.host_email = label
        
        except Exception as e:
            self.logger.warning(f"Error parsing RSS feed {rss_url}: {e}")
            # Don't fail the whole podcast for RSS errors
            pass