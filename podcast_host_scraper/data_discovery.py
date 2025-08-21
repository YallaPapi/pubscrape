#!/usr/bin/env python3
"""
Discover all available data from iTunes API and RSS feeds
"""

import requests
import feedparser
import json
from datetime import datetime

def explore_itunes_data():
    """Get all available fields from iTunes API"""
    print("\n" + "="*80)
    print("ITUNES API - AVAILABLE DATA FIELDS")
    print("="*80)
    
    url = "https://itunes.apple.com/search"
    params = {
        "term": "lex fridman",
        "media": "podcast",
        "entity": "podcast",
        "limit": 1
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['results']:
        podcast = data['results'][0]
        print("\nAvailable iTunes fields:")
        for key, value in podcast.items():
            value_preview = str(value)[:100] if value else "None"
            print(f"  • {key}: {value_preview}")
        
        return podcast.get('feedUrl')
    return None

def explore_rss_data(rss_url):
    """Get all available fields from RSS feed"""
    print("\n" + "="*80)
    print("RSS FEED - AVAILABLE DATA FIELDS")
    print("="*80)
    
    feed = feedparser.parse(rss_url)
    
    # Feed-level metadata
    print("\nFEED METADATA:")
    feed_attrs = ['title', 'subtitle', 'link', 'description', 'language', 
                  'copyright', 'author', 'author_detail', 'publisher',
                  'publisher_detail', 'webmaster', 'updated', 'updated_parsed',
                  'image', 'generator', 'docs', 'cloud', 'ttl', 'rating']
    
    for attr in feed_attrs:
        if hasattr(feed.feed, attr):
            value = getattr(feed.feed, attr)
            value_preview = str(value)[:200] if value else "None"
            print(f"  • {attr}: {value_preview}")
    
    # iTunes-specific metadata
    print("\nITUNES NAMESPACE DATA:")
    itunes_attrs = ['itunes_author', 'itunes_subtitle', 'itunes_summary',
                    'itunes_owner', 'itunes_image', 'itunes_categories',
                    'itunes_keywords', 'itunes_explicit', 'itunes_type',
                    'itunes_complete', 'itunes_new_feed_url']
    
    for attr in itunes_attrs:
        if hasattr(feed.feed, attr):
            value = getattr(feed.feed, attr)
            value_preview = str(value)[:200] if value else "None"
            print(f"  • {attr}: {value_preview}")
    
    # Episode data
    print("\nEPISODE/ENTRY DATA (Latest 3 episodes):")
    for i, entry in enumerate(feed.entries[:3], 1):
        print(f"\n  Episode {i}:")
        episode_attrs = ['title', 'link', 'description', 'published', 
                        'author', 'enclosures', 'guid', 'itunes_duration',
                        'itunes_episode', 'itunes_season', 'itunes_episodetype',
                        'itunes_explicit', 'itunes_subtitle', 'itunes_summary']
        
        for attr in episode_attrs:
            if hasattr(entry, attr):
                value = getattr(entry, attr)
                value_preview = str(value)[:150] if value else "None"
                print(f"    • {attr}: {value_preview}")
    
    # Statistics
    print("\nFEED STATISTICS:")
    print(f"  • Total episodes available: {len(feed.entries)}")
    if feed.entries:
        latest = feed.entries[0]
        if hasattr(latest, 'published'):
            print(f"  • Latest episode date: {latest.published}")
        
        # Calculate publishing frequency
        if len(feed.entries) >= 2:
            dates = []
            for entry in feed.entries[:10]:  # Last 10 episodes
                if hasattr(entry, 'published_parsed'):
                    dates.append(entry.published_parsed)
            
            if len(dates) >= 2:
                # Calculate average days between episodes
                import time
                timestamps = [time.mktime(d) for d in dates if d]
                if len(timestamps) >= 2:
                    diffs = []
                    for i in range(len(timestamps)-1):
                        diff_days = (timestamps[i] - timestamps[i+1]) / 86400
                        diffs.append(diff_days)
                    avg_days = sum(diffs) / len(diffs)
                    print(f"  • Average days between episodes: {avg_days:.1f}")

def explore_all_data():
    """Main function to explore all available data"""
    print("\nDISCOVERING ALL AVAILABLE PODCAST DATA SOURCES")
    print("="*80)
    
    # First get iTunes data
    rss_url = explore_itunes_data()
    
    # Then explore RSS feed
    if rss_url:
        explore_rss_data(rss_url)
    
    print("\n" + "="*80)
    print("SUMMARY OF ENRICHMENT POSSIBILITIES:")
    print("="*80)
    print("""
From iTunes API:
  ✓ Podcast description (long form)
  ✓ Release date
  ✓ Country
  ✓ Genre categories
  ✓ Artwork URLs
  ✓ Content advisory rating
  ✓ Track/collection counts

From RSS Feed:
  ✓ Detailed podcast description/about section
  ✓ Author/host information
  ✓ Copyright info
  ✓ Language
  ✓ Publishing schedule/frequency
  ✓ iTunes categories and keywords
  ✓ Owner contact info
  
Per Episode (from RSS):
  ✓ Episode titles and descriptions
  ✓ Guest names (often in title/description)
  ✓ Publication dates
  ✓ Episode duration
  ✓ Season/episode numbers
  ✓ Detailed show notes/summaries
  ✓ Links mentioned in episodes

Calculated Metrics:
  ✓ Total episode count
  ✓ Publishing frequency
  ✓ Latest episode date
  ✓ Active/inactive status
  ✓ Episode trends
    """)

if __name__ == "__main__":
    explore_all_data()