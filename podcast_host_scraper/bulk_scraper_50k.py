#!/usr/bin/env python3
"""
Bulk scraper for 50,000+ podcasts with rate limiting and parallel processing.
"""

import time
import requests
import feedparser
import csv
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
import logging
from threading import Lock
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BulkPodcastScraper:
    """Bulk scraper with rate limiting and parallel processing."""
    
    def __init__(self):
        self.processed_count = 0
        self.count_lock = Lock()
        self.results = []
        self.results_lock = Lock()
        
        # Rate limiting
        self.itunes_delay = 3.0  # 20 requests/minute = 1 request every 3 seconds
        self.rss_delay = 0.5  # 2 feeds/second per thread
        self.last_itunes_request = 0
        
    def get_top_podcasts_by_genre(self, limit=50000):
        """Get top podcasts across all genres."""
        
        # iTunes genre IDs for comprehensive coverage
        genres = {
            '1301': 'Arts',
            '1303': 'Comedy', 
            '1304': 'Education',
            '1305': 'Kids & Family',
            '1307': 'Health & Fitness',
            '1309': 'TV & Film',
            '1310': 'Music',
            '1311': 'News',
            '1314': 'Religion & Spirituality',
            '1315': 'Science',
            '1316': 'Sports',
            '1318': 'Technology',
            '1320': 'True Crime',
            '1321': 'Business',
            '1323': 'Games & Hobbies',
            '1324': 'Society & Culture',
            '1325': 'Government',
            '1533': 'Science',
            '1543': 'Fiction',
            '1545': 'History'
        }
        
        # Also search by popular terms
        search_terms = [
            'podcast', 'news', 'comedy', 'true crime', 'business',
            'health', 'fitness', 'technology', 'science', 'history',
            'politics', 'sports', 'music', 'arts', 'culture',
            'education', 'self improvement', 'entrepreneurship',
            'AI', 'crypto', 'investing', 'marketing', 'design'
        ]
        
        all_podcasts = {}  # Use dict to avoid duplicates
        
        print(f"Fetching top {limit} podcasts across genres...")
        
        # Method 1: Search by genre charts (gets top podcasts)
        for genre_id, genre_name in genres.items():
            if len(all_podcasts) >= limit:
                break
                
            try:
                # Get top podcasts in this genre
                url = "https://itunes.apple.com/search"
                params = {
                    'term': 'podcast',
                    'genreId': genre_id,
                    'media': 'podcast',
                    'entity': 'podcast',
                    'limit': 200,  # Max per request
                    'country': 'US'
                }
                
                response = requests.get(url, params=params, timeout=10)
                time.sleep(self.itunes_delay)  # Rate limit
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('results', []):
                        podcast_id = item.get('collectionId')
                        if podcast_id and podcast_id not in all_podcasts:
                            all_podcasts[podcast_id] = {
                                'id': podcast_id,
                                'name': item.get('collectionName', ''),
                                'artist': item.get('artistName', ''),
                                'rss_url': item.get('feedUrl', ''),
                                'genre': genre_name,
                                'itunes_url': item.get('collectionViewUrl', ''),
                                'episode_count': item.get('trackCount', 0)
                            }
                    
                    logger.info(f"Genre {genre_name}: Found {len(data.get('results', []))} podcasts")
                    
            except Exception as e:
                logger.error(f"Error fetching genre {genre_name}: {e}")
        
        # Method 2: Search by popular terms (gets different podcasts)
        for term in search_terms:
            if len(all_podcasts) >= limit:
                break
                
            try:
                url = "https://itunes.apple.com/search"
                params = {
                    'term': term,
                    'media': 'podcast',
                    'entity': 'podcast', 
                    'limit': 200,
                    'country': 'US'
                }
                
                response = requests.get(url, params=params, timeout=10)
                time.sleep(self.itunes_delay)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('results', []):
                        podcast_id = item.get('collectionId')
                        if podcast_id and podcast_id not in all_podcasts:
                            all_podcasts[podcast_id] = {
                                'id': podcast_id,
                                'name': item.get('collectionName', ''),
                                'artist': item.get('artistName', ''),
                                'rss_url': item.get('feedUrl', ''),
                                'genre': item.get('primaryGenreName', ''),
                                'itunes_url': item.get('collectionViewUrl', ''),
                                'episode_count': item.get('trackCount', 0)
                            }
                    
                    logger.info(f"Search '{term}': Found {len(data.get('results', []))} podcasts")
                    
            except Exception as e:
                logger.error(f"Error searching '{term}': {e}")
        
        # Convert to list and limit
        podcast_list = list(all_podcasts.values())[:limit]
        
        # Sort by episode count (likely more active/popular)
        podcast_list.sort(key=lambda x: x.get('episode_count', 0), reverse=True)
        
        print(f"Collected {len(podcast_list)} unique podcasts")
        return podcast_list
    
    def parse_rss_feed(self, podcast: Dict) -> Dict:
        """Parse a single RSS feed with timeout and error handling."""
        
        if not podcast.get('rss_url'):
            return podcast
        
        try:
            # Add timeout to feedparser
            feed = feedparser.parse(
                podcast['rss_url'],
                agent='PodcastScraper/1.0',
                timeout=5  # 5 second timeout
            )
            
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
            
            # Get latest episode info
            last_episode = None
            if feed.entries:
                last_episode = feed.entries[0].get('published', '')
            
            # Update podcast data
            podcast['email'] = email
            podcast['website'] = website
            podcast['last_episode'] = last_episode
            podcast['feed_parsed'] = True
            
            # Rate limit
            time.sleep(self.rss_delay + random.uniform(0, 0.5))  # Add jitter
            
            with self.count_lock:
                self.processed_count += 1
                if self.processed_count % 100 == 0:
                    logger.info(f"Progress: {self.processed_count} RSS feeds parsed")
            
            return podcast
            
        except Exception as e:
            logger.debug(f"RSS error for {podcast['name']}: {e}")
            podcast['feed_parsed'] = False
            return podcast
    
    def process_batch_parallel(self, podcasts: List[Dict], max_workers: int = 10):
        """Process podcasts in parallel with thread pool."""
        
        print(f"\nProcessing {len(podcasts)} RSS feeds with {max_workers} threads...")
        print("This will take approximately {} minutes".format(
            int((len(podcasts) * 2) / (max_workers * 60))
        ))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.parse_rss_feed, podcast): podcast 
                for podcast in podcasts
            }
            
            # Process completed tasks
            for future in as_completed(futures):
                try:
                    result = future.result()
                    with self.results_lock:
                        self.results.append(result)
                except Exception as e:
                    logger.error(f"Thread error: {e}")
        
        return self.results
    
    def save_results(self, podcasts: List[Dict], filename: str):
        """Save results to CSV with progress tracking."""
        
        output_dir = Path("podcast_host_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / filename
        
        # Count statistics
        with_email = sum(1 for p in podcasts if p.get('email'))
        with_website = sum(1 for p in podcasts if p.get('website'))
        parsed = sum(1 for p in podcasts if p.get('feed_parsed'))
        
        # Save to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'artist', 'email', 'website', 'genre', 
                         'episode_count', 'last_episode', 'rss_url', 'itunes_url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for podcast in podcasts:
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
        
        print(f"\n" + "="*80)
        print("SCRAPING COMPLETE!")
        print("="*80)
        print(f"Results saved to: {csv_path}")
        print(f"Total podcasts: {len(podcasts)}")
        print(f"RSS feeds parsed: {parsed}")
        print(f"Emails found: {with_email} ({with_email/len(podcasts)*100:.1f}%)")
        print(f"Websites found: {with_website} ({with_website/len(podcasts)*100:.1f}%)")
        
        return str(csv_path)

def main():
    """Run bulk scraper."""
    
    print("\n" + "="*80)
    print("BULK PODCAST SCRAPER - 50,000 PODCASTS")
    print("="*80)
    
    scraper = BulkPodcastScraper()
    
    # Configuration
    target_count = 1000  # Start with 1000 for testing (change to 50000 for full run)
    thread_count = 10  # Number of parallel threads for RSS parsing
    
    # Step 1: Get podcast list from iTunes
    print(f"\n[Step 1/3] Fetching top {target_count} podcasts from iTunes...")
    start_time = time.time()
    
    podcasts = scraper.get_top_podcasts_by_genre(limit=target_count)
    
    fetch_time = time.time() - start_time
    print(f"Fetched {len(podcasts)} podcasts in {fetch_time:.1f} seconds")
    
    # Step 2: Parse RSS feeds in parallel
    print(f"\n[Step 2/3] Parsing RSS feeds for contact info...")
    parse_start = time.time()
    
    enriched_podcasts = scraper.process_batch_parallel(podcasts, max_workers=thread_count)
    
    parse_time = time.time() - parse_start
    print(f"Parsed {len(enriched_podcasts)} RSS feeds in {parse_time:.1f} seconds")
    
    # Step 3: Save results
    print(f"\n[Step 3/3] Saving results to CSV...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = scraper.save_results(
        enriched_podcasts, 
        f"bulk_podcasts_{len(enriched_podcasts)}_{timestamp}.csv"
    )
    
    total_time = time.time() - start_time
    print(f"\nTotal time: {total_time/60:.1f} minutes")
    print(f"Average time per podcast: {total_time/len(podcasts):.2f} seconds")
    
    return True

if __name__ == "__main__":
    main()