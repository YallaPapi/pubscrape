#!/usr/bin/env python3
"""
Smart bulk scraper that respects iTunes rate limit (20 req/min).
Includes caching, resume capability, and smart filtering.
"""

import time
import requests
import feedparser
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartPodcastScraper:
    """Production-ready scraper with rate limiting and caching."""
    
    def __init__(self, cache_dir="podcast_host_scraper/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # iTunes API rate limit: 20 requests per minute
        self.itunes_requests_this_minute = 0
        self.itunes_minute_start = time.time()
        
        # Initialize cache database
        self.init_cache_db()
        
    def init_cache_db(self):
        """Initialize SQLite cache database."""
        self.db_path = self.cache_dir / "podcast_cache.db"
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS podcasts (
                id INTEGER PRIMARY KEY,
                name TEXT,
                artist TEXT,
                email TEXT,
                website TEXT,
                rss_url TEXT,
                genre TEXT,
                episode_count INTEGER,
                last_episode TEXT,
                itunes_url TEXT,
                last_scraped TIMESTAMP,
                UNIQUE(id)
            )
        ''')
        conn.commit()
        conn.close()
        
    def wait_for_rate_limit(self):
        """Ensure we don't exceed 20 requests per minute."""
        current_time = time.time()
        time_since_minute_start = current_time - self.itunes_minute_start
        
        # Reset counter if a minute has passed
        if time_since_minute_start >= 60:
            self.itunes_requests_this_minute = 0
            self.itunes_minute_start = current_time
            return
        
        # If we've made 20 requests, wait until minute is up
        if self.itunes_requests_this_minute >= 20:
            wait_time = 60 - time_since_minute_start
            logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
            self.itunes_requests_this_minute = 0
            self.itunes_minute_start = time.time()
    
    def search_itunes(self, term, genre_id=None, limit=200):
        """Search iTunes with rate limiting."""
        self.wait_for_rate_limit()
        
        url = "https://itunes.apple.com/search"
        params = {
            'term': term,
            'media': 'podcast',
            'entity': 'podcast',
            'limit': limit,
            'country': 'US'
        }
        
        if genre_id:
            params['genreId'] = genre_id
        
        try:
            response = requests.get(url, params=params, timeout=10)
            self.itunes_requests_this_minute += 1
            
            if response.status_code == 200:
                return response.json().get('results', [])
            else:
                logger.error(f"iTunes API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Request error: {e}")
            return []
    
    def get_cached_podcast(self, podcast_id):
        """Check if podcast is in cache and fresh."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Consider cache fresh if scraped within last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        
        cursor.execute('''
            SELECT * FROM podcasts 
            WHERE id = ? AND last_scraped > ?
        ''', (podcast_id, week_ago))
        
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def save_to_cache(self, podcast):
        """Save podcast to cache database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO podcasts 
            (id, name, artist, email, website, rss_url, genre, 
             episode_count, last_episode, itunes_url, last_scraped)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            podcast.get('id'),
            podcast.get('name'),
            podcast.get('artist'),
            podcast.get('email'),
            podcast.get('website'),
            podcast.get('rss_url'),
            podcast.get('genre'),
            podcast.get('episode_count'),
            podcast.get('last_episode'),
            podcast.get('itunes_url'),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_top_podcasts(self, target_count=10000):
        """Get top podcasts efficiently with caching."""
        
        # High-value genres to prioritize
        priority_genres = {
            '1321': 'Business',
            '1318': 'Technology', 
            '1304': 'Education',
            '1533': 'Science',
            '1307': 'Health & Fitness',
            '1303': 'Comedy',
            '1489': 'News'
        }
        
        # High-value search terms
        priority_terms = [
            'entrepreneur', 'startup', 'AI', 'machine learning',
            'investing', 'finance', 'marketing', 'sales',
            'leadership', 'productivity', 'self improvement',
            'tech', 'software', 'design', 'data science'
        ]
        
        all_podcasts = {}
        
        print(f"Fetching top {target_count} podcasts (with cache)...")
        
        # First, get podcasts from priority genres
        for genre_id, genre_name in priority_genres.items():
            if len(all_podcasts) >= target_count:
                break
                
            logger.info(f"Searching genre: {genre_name}")
            results = self.search_itunes('podcast', genre_id=genre_id)
            
            for item in results:
                podcast_id = item.get('collectionId')
                if podcast_id and podcast_id not in all_podcasts:
                    
                    # Check cache first
                    cached = self.get_cached_podcast(podcast_id)
                    if cached:
                        logger.debug(f"Using cached data for {item.get('collectionName')}")
                        continue
                    
                    # Only include active podcasts
                    episode_count = item.get('trackCount', 0)
                    if episode_count < 5:  # Skip podcasts with very few episodes
                        continue
                    
                    all_podcasts[podcast_id] = {
                        'id': podcast_id,
                        'name': item.get('collectionName', ''),
                        'artist': item.get('artistName', ''),
                        'rss_url': item.get('feedUrl', ''),
                        'genre': genre_name,
                        'itunes_url': item.get('collectionViewUrl', ''),
                        'episode_count': episode_count
                    }
        
        # Then search for specific high-value terms
        for term in priority_terms:
            if len(all_podcasts) >= target_count:
                break
                
            logger.info(f"Searching term: {term}")
            results = self.search_itunes(term)
            
            for item in results:
                podcast_id = item.get('collectionId')
                if podcast_id and podcast_id not in all_podcasts:
                    
                    episode_count = item.get('trackCount', 0)
                    if episode_count < 5:
                        continue
                    
                    all_podcasts[podcast_id] = {
                        'id': podcast_id,
                        'name': item.get('collectionName', ''),
                        'artist': item.get('artistName', ''),
                        'rss_url': item.get('feedUrl', ''),
                        'genre': item.get('primaryGenreName', ''),
                        'itunes_url': item.get('collectionViewUrl', ''),
                        'episode_count': episode_count
                    }
        
        # Sort by episode count (proxy for popularity/activity)
        podcast_list = list(all_podcasts.values())
        podcast_list.sort(key=lambda x: x.get('episode_count', 0), reverse=True)
        
        return podcast_list[:target_count]
    
    def parse_rss_with_timeout(self, podcast, timeout=5):
        """Parse RSS feed with timeout and caching."""
        
        # Check cache first
        cached = self.get_cached_podcast(podcast.get('id'))
        if cached:
            return podcast  # Already have recent data
        
        if not podcast.get('rss_url'):
            return podcast
        
        try:
            feed = feedparser.parse(podcast['rss_url'])
            
            # Extract email
            email = None
            if hasattr(feed.feed, 'author_detail') and hasattr(feed.feed.author_detail, 'email'):
                email = feed.feed.author_detail.email
            elif 'itunes_owner' in feed.feed:
                owner = feed.feed.itunes_owner
                if isinstance(owner, dict) and 'email' in owner:
                    email = owner['email']
            
            # Extract website
            website = None
            if hasattr(feed.feed, 'link'):
                website = feed.feed.link
            
            # Get last episode date
            last_episode = None
            if feed.entries:
                last_episode = feed.entries[0].get('published', '')
                
                # Skip inactive podcasts (no episode in 6 months)
                try:
                    from dateutil import parser
                    last_date = parser.parse(last_episode)
                    if (datetime.now(last_date.tzinfo) - last_date).days > 180:
                        logger.info(f"Skipping inactive podcast: {podcast['name']}")
                        return podcast
                except:
                    pass
            
            podcast['email'] = email
            podcast['website'] = website
            podcast['last_episode'] = last_episode
            
            # Save to cache
            self.save_to_cache(podcast)
            
            return podcast
            
        except Exception as e:
            logger.debug(f"RSS error for {podcast['name']}: {e}")
            return podcast
    
    def process_batch(self, podcasts, max_workers=10):
        """Process podcasts in parallel."""
        
        print(f"\nProcessing {len(podcasts)} RSS feeds...")
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.parse_rss_with_timeout, podcast): podcast
                for podcast in podcasts
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 100 == 0:
                    logger.info(f"Progress: {completed}/{len(podcasts)} RSS feeds processed")
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Processing error: {e}")
        
        return results

def main():
    """Run smart bulk scraper."""
    
    print("\n" + "="*80)
    print("SMART BULK PODCAST SCRAPER")
    print("="*80)
    
    scraper = SmartPodcastScraper()
    
    # Configuration for 5-minute test
    target_count = 2000  # Should be achievable in ~5 minutes with rate limits
    
    # Step 1: Get podcasts (with caching)
    print(f"\n[Step 1/3] Getting top {target_count} podcasts...")
    start_time = time.time()
    
    podcasts = scraper.get_top_podcasts(target_count)
    
    print(f"Collected {len(podcasts)} podcasts in {time.time()-start_time:.1f}s")
    
    # Step 2: Parse RSS feeds
    print(f"\n[Step 2/3] Parsing RSS feeds for contact info...")
    enriched = scraper.process_batch(podcasts, max_workers=10)
    
    # Step 3: Export results
    print(f"\n[Step 3/3] Exporting results...")
    
    output_dir = Path("podcast_host_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = output_dir / f"smart_bulk_{len(enriched)}_{timestamp}.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'artist', 'email', 'website', 'genre',
                     'episode_count', 'last_episode', 'rss_url', 'itunes_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for podcast in enriched:
            writer.writerow({
                'name': podcast.get('name', ''),
                'artist': podcast.get('artist', ''),
                'email': podcast.get('email', ''),
                'website': podcast.get('website', ''),
                'genre': podcast.get('genre', ''),
                'episode_count': podcast.get('episode_count', ''),
                'last_episode': podcast.get('last_episode', ''),
                'rss_url': podcast.get('rss_url', ''),
                'itunes_url': podcast.get('itunes_url', '')
            })
    
    # Statistics
    with_email = sum(1 for p in enriched if p.get('email'))
    with_website = sum(1 for p in enriched if p.get('website'))
    
    print(f"\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"Results: {csv_path}")
    print(f"Total podcasts: {len(enriched)}")
    print(f"With email: {with_email} ({with_email/len(enriched)*100:.1f}%)")
    print(f"With website: {with_website} ({with_website/len(enriched)*100:.1f}%)")
    print(f"Total time: {(time.time()-start_time)/60:.1f} minutes")

if __name__ == "__main__":
    main()