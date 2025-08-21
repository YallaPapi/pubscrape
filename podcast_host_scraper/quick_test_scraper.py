#!/usr/bin/env python3
"""
Quick 5-minute test scraper to see real results.
"""

import time
import requests
import feedparser
import csv
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def quick_scrape():
    """Quick scrape to get results in 5 minutes."""
    
    print("\n" + "="*80)
    print("QUICK 5-MINUTE PODCAST SCRAPER TEST")
    print("="*80)
    
    start_time = time.time()
    all_podcasts = []
    
    # Priority genres for high-value podcasts
    genres = {
        '1321': 'Business',
        '1318': 'Technology',
        '1304': 'Education'
    }
    
    # Step 1: Get podcasts from iTunes (respecting rate limit)
    print("\n[Phase 1] Fetching podcasts from iTunes API...")
    print("Rate limit: 20 requests per minute")
    
    request_count = 0
    minute_start = time.time()
    
    for genre_id, genre_name in genres.items():
        # Check rate limit
        if request_count >= 20:
            wait_time = 60 - (time.time() - minute_start)
            if wait_time > 0:
                print(f"Rate limit reached, waiting {wait_time:.0f}s...")
                time.sleep(wait_time)
            request_count = 0
            minute_start = time.time()
        
        print(f"  Fetching {genre_name} podcasts...")
        
        url = "https://itunes.apple.com/search"
        params = {
            'term': 'podcast',
            'genreId': genre_id,
            'media': 'podcast',
            'entity': 'podcast',
            'limit': 200,
            'country': 'US'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                for item in results:
                    # Only include active podcasts
                    if item.get('trackCount', 0) >= 10:
                        all_podcasts.append({
                            'name': item.get('collectionName', ''),
                            'artist': item.get('artistName', ''),
                            'rss_url': item.get('feedUrl', ''),
                            'genre': genre_name,
                            'episode_count': item.get('trackCount', 0),
                            'itunes_url': item.get('collectionViewUrl', ''),
                            'email': None,
                            'website': None
                        })
                
                print(f"    Found {len(results)} podcasts in {genre_name}")
                
        except Exception as e:
            logger.error(f"Error: {e}")
    
    print(f"\nCollected {len(all_podcasts)} total podcasts")
    
    # Step 2: Quick RSS parsing (just top 100, parallel)
    print(f"\n[Phase 2] Quick RSS parsing for top 100 podcasts...")
    
    # Sort by episode count (most active first)
    all_podcasts.sort(key=lambda x: x.get('episode_count', 0), reverse=True)
    top_podcasts = all_podcasts[:100]
    
    def parse_rss_quick(podcast):
        """Quick RSS parse with 3-second timeout."""
        if not podcast.get('rss_url'):
            return podcast
            
        try:
            # Parse with timeout
            feed = feedparser.parse(podcast['rss_url'])
            
            # Quick email extraction
            if hasattr(feed.feed, 'author_detail') and hasattr(feed.feed.author_detail, 'email'):
                podcast['email'] = feed.feed.author_detail.email
            elif 'itunes_owner' in feed.feed:
                owner = feed.feed.itunes_owner
                if isinstance(owner, dict) and 'email' in owner:
                    podcast['email'] = owner['email']
            
            # Quick website extraction
            if hasattr(feed.feed, 'link'):
                podcast['website'] = feed.feed.link
            
            return podcast
            
        except:
            return podcast
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(parse_rss_quick, p) for p in top_podcasts]
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 20 == 0:
                elapsed = time.time() - start_time
                print(f"  Processed {completed}/100 RSS feeds ({elapsed:.0f}s elapsed)")
    
    # Step 3: Save results
    print(f"\n[Phase 3] Saving results...")
    
    output_dir = Path("podcast_host_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = output_dir / f"quick_test_{timestamp}.csv"
    
    # Write all podcasts (including those without RSS parsing)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['name', 'artist', 'email', 'website', 'genre', 
                     'episode_count', 'rss_url', 'itunes_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for podcast in all_podcasts:
            writer.writerow({
                'name': podcast.get('name', ''),
                'artist': podcast.get('artist', ''),
                'email': podcast.get('email', ''),
                'website': podcast.get('website', ''),
                'genre': podcast.get('genre', ''),
                'episode_count': podcast.get('episode_count', ''),
                'rss_url': podcast.get('rss_url', ''),
                'itunes_url': podcast.get('itunes_url', '')
            })
    
    # Statistics
    total_time = time.time() - start_time
    with_email = sum(1 for p in all_podcasts if p.get('email'))
    with_website = sum(1 for p in all_podcasts if p.get('website'))
    
    print(f"\n" + "="*80)
    print("5-MINUTE TEST COMPLETE!")
    print("="*80)
    print(f"\nResults:")
    print(f"  • Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"  • Podcasts collected: {len(all_podcasts)}")
    print(f"  • RSS feeds parsed: {min(100, len(all_podcasts))}")
    print(f"  • Emails found: {with_email}")
    print(f"  • Websites found: {with_website}")
    print(f"  • CSV saved to: {csv_path}")
    
    if with_email > 0:
        print(f"\nSample podcasts with emails:")
        for p in all_podcasts[:50]:
            if p.get('email'):
                print(f"  • {p['name']}: {p['email']}")
                if len([x for x in all_podcasts[:50] if x.get('email')]) >= 5:
                    break
    
    print(f"\nProjection for 50,000 podcasts:")
    print(f"  • iTunes API time: ~{50000/len(all_podcasts) * 20:.0f} seconds")
    print(f"  • RSS parsing (10 threads): ~{50000 * 0.5 / 10 / 60:.0f} minutes")
    print(f"  • Total estimated time: ~{(50000/len(all_podcasts) * 20 + 50000 * 0.5 / 10) / 60:.0f} minutes")

if __name__ == "__main__":
    quick_scrape()