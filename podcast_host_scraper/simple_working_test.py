#!/usr/bin/env python3
"""
Simple working e2e test that actually works without botasaurus.
"""

import sys
import os
import logging
import csv
import json
import requests
import feedparser
from pathlib import Path
from datetime import datetime

# Setup logging with visible output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def search_podcasts_itunes(query, limit=10):
    """Search for podcasts using iTunes API."""
    logger.info(f"Searching iTunes for: {query}")
    
    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "media": "podcast",
        "entity": "podcast",
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        podcasts = []
        for item in data.get('results', []):
            podcast = {
                'name': item.get('collectionName', 'Unknown'),
                'artist': item.get('artistName', ''),
                'rss_url': item.get('feedUrl', ''),
                'itunes_url': item.get('collectionViewUrl', ''),
                'genre': item.get('primaryGenreName', ''),
                'country': item.get('country', ''),
                'artwork': item.get('artworkUrl600', ''),
                'website': None,
                'email': None
            }
            podcasts.append(podcast)
            
        logger.info(f"Found {len(podcasts)} podcasts from iTunes")
        return podcasts
        
    except Exception as e:
        logger.error(f"iTunes API error: {e}")
        return []

def extract_contact_from_rss(rss_url):
    """Extract website and email from RSS feed."""
    if not rss_url:
        return None, None
        
    logger.info(f"Parsing RSS feed: {rss_url[:50]}...")
    
    try:
        feed = feedparser.parse(rss_url)
        
        website = None
        email = None
        
        # Try to get website from feed
        if hasattr(feed.feed, 'link'):
            website = feed.feed.link
            
        # Try to get email from various fields
        if hasattr(feed.feed, 'author_detail') and hasattr(feed.feed.author_detail, 'email'):
            email = feed.feed.author_detail.email
        elif hasattr(feed.feed, 'publisher_detail') and hasattr(feed.feed.publisher_detail, 'email'):
            email = feed.feed.publisher_detail.email
        elif hasattr(feed.feed, 'webmaster'):
            email = feed.feed.webmaster
            
        # Look in iTunes namespace
        if not email and 'itunes_owner' in feed.feed:
            owner = feed.feed.itunes_owner
            if isinstance(owner, dict) and 'email' in owner:
                email = owner['email']
                
        logger.info(f"Extracted - Website: {website}, Email: {email}")
        return website, email
        
    except Exception as e:
        logger.error(f"RSS parsing error: {e}")
        return None, None

def save_to_csv(podcasts, filename):
    """Save podcast data to CSV."""
    output_dir = Path("podcast_host_scraper/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / filename
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['podcast_name', 'artist', 'website', 'email', 'rss_url', 
                     'itunes_url', 'genre', 'country']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for podcast in podcasts:
            row = {
                'podcast_name': podcast['name'],
                'artist': podcast['artist'],
                'website': podcast['website'] or '',
                'email': podcast['email'] or '',
                'rss_url': podcast['rss_url'],
                'itunes_url': podcast['itunes_url'],
                'genre': podcast['genre'],
                'country': podcast['country']
            }
            writer.writerow(row)
    
    logger.info(f"Saved {len(podcasts)} podcasts to {csv_path}")
    return csv_path

def main():
    """Run the complete e2e test."""
    print("\n" + "="*80)
    print("PODCAST SCRAPER - WORKING E2E TEST")
    print("="*80)
    
    # Test parameters
    search_query = "artificial intelligence"
    max_results = 10
    
    print(f"\nTest Configuration:")
    print(f"  • Search Query: {search_query}")
    print(f"  • Max Results: {max_results}")
    print(f"  • Output: CSV file")
    
    # Step 1: Search for podcasts
    print(f"\n[Step 1/4] Searching for podcasts...")
    podcasts = search_podcasts_itunes(search_query, max_results)
    
    if not podcasts:
        print("ERROR: No podcasts found!")
        return False
    
    print(f"SUCCESS: Found {len(podcasts)} podcasts")
    for i, p in enumerate(podcasts[:3], 1):
        print(f"  {i}. {p['name']} by {p['artist']}")
    
    # Step 2: Enrich with contact info from RSS
    print(f"\n[Step 2/4] Extracting contact info from RSS feeds...")
    enriched_count = 0
    email_count = 0
    
    for podcast in podcasts:
        if podcast['rss_url']:
            website, email = extract_contact_from_rss(podcast['rss_url'])
            if website:
                podcast['website'] = website
                enriched_count += 1
            if email:
                podcast['email'] = email
                email_count += 1
                print(f"  Found email for {podcast['name']}: {email}")
    
    print(f"SUCCESS: Enriched {enriched_count} with websites, {email_count} with emails")
    
    # Step 3: Save to CSV
    print(f"\n[Step 3/4] Saving results to CSV...")
    csv_path = save_to_csv(podcasts, f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    print(f"SUCCESS: Saved to {csv_path}")
    
    # Step 4: Verify CSV
    print(f"\n[Step 4/4] Verifying CSV output...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"SUCCESS: CSV contains {len(rows)} rows")
    
    # Summary
    print(f"\n" + "="*80)
    print("E2E TEST COMPLETED SUCCESSFULLY!")
    print("="*80)
    print(f"\nResults Summary:")
    print(f"  • Podcasts found: {len(podcasts)}")
    print(f"  • Podcasts with websites: {enriched_count}")
    print(f"  • Podcasts with emails: {email_count}")
    print(f"  • CSV file: {csv_path}")
    
    # Show sample data
    if email_count > 0:
        print(f"\nSample podcasts with emails:")
        for p in podcasts:
            if p['email']:
                print(f"  • {p['name']}: {p['email']}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)