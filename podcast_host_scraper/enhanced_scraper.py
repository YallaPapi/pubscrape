#!/usr/bin/env python3
"""
Enhanced podcast scraper with full data enrichment for AI personalization.
"""

import sys
import os
import logging
import csv
import json
import requests
import feedparser
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class EnhancedPodcastScraper:
    """Scraper with full enrichment capabilities."""
    
    def search_podcasts(self, query: str, limit: int = 10) -> List[Dict]:
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
                # Extract all iTunes data
                podcast = {
                    # Basic info
                    'name': item.get('collectionName', 'Unknown'),
                    'artist': item.get('artistName', ''),
                    'description_short': item.get('collectionName', ''),
                    
                    # URLs
                    'rss_url': item.get('feedUrl', ''),
                    'itunes_url': item.get('collectionViewUrl', ''),
                    'artwork_url': item.get('artworkUrl600', ''),
                    
                    # Metadata
                    'genre': item.get('primaryGenreName', ''),
                    'genres_all': ', '.join(item.get('genres', [])),
                    'country': item.get('country', ''),
                    'language': '',  # Will get from RSS
                    'content_rating': item.get('contentAdvisoryRating', ''),
                    
                    # Stats
                    'episode_count': item.get('trackCount', 0),
                    'release_date': item.get('releaseDate', ''),
                    
                    # To be enriched from RSS
                    'website': None,
                    'email': None,
                    'description_long': None,
                    'last_episode_date': None,
                    'publishing_frequency': None,
                    'recent_episodes': [],
                    'recent_guests': [],
                    'recent_topics': [],
                    'average_duration': None,
                    'host_full_name': None,
                    'publishing_platform': None
                }
                podcasts.append(podcast)
                
            logger.info(f"Found {len(podcasts)} podcasts from iTunes")
            return podcasts
            
        except Exception as e:
            logger.error(f"iTunes API error: {e}")
            return []
    
    def extract_guests_from_text(self, text: str) -> List[str]:
        """Extract potential guest names from episode titles/descriptions."""
        guests = []
        
        # Common patterns for guest mentions
        patterns = [
            r'with ([A-Z][a-z]+ [A-Z][a-z]+)',  # "with John Smith"
            r'feat(?:uring)?\.? ([A-Z][a-z]+ [A-Z][a-z]+)',  # "featuring John Smith"
            r'guest[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',  # "guest: John Smith"
            r'([A-Z][a-z]+ [A-Z][a-z]+)[\s\-–—:]+',  # "John Smith - " at start
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            guests.extend(matches)
        
        # Remove duplicates and return
        return list(set(guests))[:5]  # Max 5 guests
    
    def extract_topics_from_text(self, text: str) -> List[str]:
        """Extract key topics from episode descriptions."""
        # Simple keyword extraction - could be enhanced with NLP
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
        
        # Find capitalized phrases (likely important topics)
        topic_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        potential_topics = re.findall(topic_pattern, text)
        
        # Filter out common words and names
        topics = []
        for topic in potential_topics:
            if len(topic.split()) <= 3 and topic.lower() not in stop_words:
                topics.append(topic)
        
        return list(set(topics))[:10]  # Max 10 topics
    
    def calculate_publishing_frequency(self, dates: List) -> str:
        """Calculate average publishing frequency."""
        if len(dates) < 2:
            return "Unknown"
        
        try:
            # Convert to timestamps
            import time
            timestamps = []
            for date in dates[:10]:  # Use last 10 episodes
                if date:
                    timestamps.append(time.mktime(date))
            
            if len(timestamps) < 2:
                return "Unknown"
            
            # Calculate average days between episodes
            diffs = []
            for i in range(len(timestamps)-1):
                diff_days = abs(timestamps[i] - timestamps[i+1]) / 86400
                diffs.append(diff_days)
            
            avg_days = sum(diffs) / len(diffs)
            
            # Convert to readable format
            if avg_days <= 1.5:
                return "Daily"
            elif avg_days <= 3.5:
                return "2-3 times per week"
            elif avg_days <= 8:
                return "Weekly"
            elif avg_days <= 16:
                return "Bi-weekly"
            elif avg_days <= 35:
                return "Monthly"
            else:
                return f"Every {int(avg_days)} days"
                
        except Exception as e:
            logger.error(f"Error calculating frequency: {e}")
            return "Unknown"
    
    def enrich_from_rss(self, podcast: Dict) -> Dict:
        """Enrich podcast data from RSS feed."""
        if not podcast['rss_url']:
            return podcast
            
        logger.info(f"Enriching from RSS: {podcast['name']}")
        
        try:
            feed = feedparser.parse(podcast['rss_url'])
            
            # Extract website
            if hasattr(feed.feed, 'link'):
                podcast['website'] = feed.feed.link
            
            # Extract email
            if hasattr(feed.feed, 'author_detail') and hasattr(feed.feed.author_detail, 'email'):
                podcast['email'] = feed.feed.author_detail.email
            elif hasattr(feed.feed, 'publisher_detail') and hasattr(feed.feed.publisher_detail, 'email'):
                podcast['email'] = feed.feed.publisher_detail.email
            
            # iTunes owner email (often different)
            if not podcast['email'] and 'itunes_owner' in feed.feed:
                owner = feed.feed.itunes_owner
                if isinstance(owner, dict) and 'email' in owner:
                    podcast['email'] = owner['email']
            
            # Long description
            if hasattr(feed.feed, 'description'):
                podcast['description_long'] = feed.feed.description[:1000]  # Limit to 1000 chars
            elif hasattr(feed.feed, 'subtitle'):
                podcast['description_long'] = feed.feed.subtitle[:1000]
            
            # Language
            if hasattr(feed.feed, 'language'):
                podcast['language'] = feed.feed.language
            
            # Host full name
            if hasattr(feed.feed, 'author'):
                podcast['host_full_name'] = feed.feed.author
            
            # Publishing platform
            if hasattr(feed.feed, 'generator'):
                podcast['publishing_platform'] = feed.feed.generator
            
            # Process episodes
            if feed.entries:
                # Last episode date
                if hasattr(feed.entries[0], 'published'):
                    podcast['last_episode_date'] = feed.entries[0].published
                
                # Recent episodes info
                recent_episodes = []
                all_guests = []
                all_topics = []
                durations = []
                dates = []
                
                for entry in feed.entries[:10]:  # Last 10 episodes
                    episode_info = {
                        'title': getattr(entry, 'title', ''),
                        'date': getattr(entry, 'published', ''),
                        'description': getattr(entry, 'description', '')[:200]  # First 200 chars
                    }
                    recent_episodes.append(episode_info)
                    
                    # Extract guests from title and description
                    text = f"{episode_info['title']} {episode_info['description']}"
                    guests = self.extract_guests_from_text(text)
                    all_guests.extend(guests)
                    
                    # Extract topics
                    topics = self.extract_topics_from_text(text)
                    all_topics.extend(topics)
                    
                    # Duration
                    if hasattr(entry, 'itunes_duration'):
                        duration = entry.itunes_duration
                        if ':' in str(duration):
                            # Convert HH:MM:SS to minutes
                            parts = str(duration).split(':')
                            if len(parts) == 3:
                                minutes = int(parts[0]) * 60 + int(parts[1])
                                durations.append(minutes)
                            elif len(parts) == 2:
                                durations.append(int(parts[0]))
                    
                    # Dates for frequency calculation
                    if hasattr(entry, 'published_parsed'):
                        dates.append(entry.published_parsed)
                
                # Store enriched data
                podcast['recent_episodes'] = json.dumps(recent_episodes[:5])  # Store as JSON string
                podcast['recent_guests'] = ', '.join(list(set(all_guests))[:5])
                podcast['recent_topics'] = ', '.join(list(set(all_topics))[:10])
                
                # Average duration
                if durations:
                    podcast['average_duration'] = f"{sum(durations) / len(durations):.0f} minutes"
                
                # Publishing frequency
                podcast['publishing_frequency'] = self.calculate_publishing_frequency(dates)
                
            logger.info(f"Enriched {podcast['name']} - Email: {podcast['email']}, Frequency: {podcast['publishing_frequency']}")
            
        except Exception as e:
            logger.error(f"RSS parsing error for {podcast['name']}: {e}")
        
        return podcast
    
    def export_to_csv(self, podcasts: List[Dict], filename: str) -> str:
        """Export enriched podcast data to CSV."""
        output_dir = Path("podcast_host_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = output_dir / filename
        
        # Define all fields for export
        fieldnames = [
            # Basic info
            'podcast_name', 'host_name', 'host_full_name',
            
            # Contact
            'email', 'website',
            
            # Descriptions
            'description_short', 'description_long',
            
            # URLs
            'rss_url', 'itunes_url', 'artwork_url',
            
            # Metadata
            'genre', 'genres_all', 'country', 'language', 
            'content_rating', 'publishing_platform',
            
            # Statistics
            'episode_count', 'release_date', 'last_episode_date',
            'publishing_frequency', 'average_duration',
            
            # Recent content (for AI personalization)
            'recent_guests', 'recent_topics', 'recent_episodes'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for podcast in podcasts:
                row = {
                    'podcast_name': podcast['name'],
                    'host_name': podcast['artist'],
                    'host_full_name': podcast.get('host_full_name', ''),
                    'email': podcast.get('email', ''),
                    'website': podcast.get('website', ''),
                    'description_short': podcast.get('description_short', ''),
                    'description_long': podcast.get('description_long', ''),
                    'rss_url': podcast.get('rss_url', ''),
                    'itunes_url': podcast.get('itunes_url', ''),
                    'artwork_url': podcast.get('artwork_url', ''),
                    'genre': podcast.get('genre', ''),
                    'genres_all': podcast.get('genres_all', ''),
                    'country': podcast.get('country', ''),
                    'language': podcast.get('language', ''),
                    'content_rating': podcast.get('content_rating', ''),
                    'publishing_platform': podcast.get('publishing_platform', ''),
                    'episode_count': podcast.get('episode_count', ''),
                    'release_date': podcast.get('release_date', ''),
                    'last_episode_date': podcast.get('last_episode_date', ''),
                    'publishing_frequency': podcast.get('publishing_frequency', ''),
                    'average_duration': podcast.get('average_duration', ''),
                    'recent_guests': podcast.get('recent_guests', ''),
                    'recent_topics': podcast.get('recent_topics', ''),
                    'recent_episodes': podcast.get('recent_episodes', '')
                }
                writer.writerow(row)
        
        logger.info(f"Exported {len(podcasts)} podcasts to {csv_path}")
        return str(csv_path)

def main():
    """Run the enhanced scraper."""
    print("\n" + "="*80)
    print("ENHANCED PODCAST SCRAPER - FULL DATA ENRICHMENT")
    print("="*80)
    
    scraper = EnhancedPodcastScraper()
    
    # Search for podcasts
    query = "artificial intelligence"
    limit = 5  # Small test
    
    print(f"\nSearching for: {query}")
    print(f"Limit: {limit} podcasts")
    
    podcasts = scraper.search_podcasts(query, limit)
    
    if not podcasts:
        print("No podcasts found!")
        return False
    
    print(f"\nFound {len(podcasts)} podcasts, enriching...")
    
    # Enrich each podcast
    for i, podcast in enumerate(podcasts, 1):
        print(f"\n[{i}/{len(podcasts)}] Enriching: {podcast['name']}")
        scraper.enrich_from_rss(podcast)
    
    # Export to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = scraper.export_to_csv(podcasts, f"enriched_podcasts_{timestamp}.csv")
    
    # Summary
    print(f"\n" + "="*80)
    print("ENRICHMENT COMPLETE!")
    print("="*80)
    
    emails_found = sum(1 for p in podcasts if p.get('email'))
    websites_found = sum(1 for p in podcasts if p.get('website'))
    guests_found = sum(1 for p in podcasts if p.get('recent_guests'))
    
    print(f"\nResults:")
    print(f"  • Podcasts processed: {len(podcasts)}")
    print(f"  • Emails found: {emails_found}")
    print(f"  • Websites found: {websites_found}")
    print(f"  • With recent guests: {guests_found}")
    print(f"  • CSV exported to: {csv_file}")
    
    # Show sample enriched data
    if podcasts:
        p = podcasts[0]
        print(f"\nSample enriched data for '{p['name']}':")
        print(f"  • Email: {p.get('email', 'N/A')}")
        print(f"  • Publishing frequency: {p.get('publishing_frequency', 'N/A')}")
        print(f"  • Recent guests: {p.get('recent_guests', 'N/A')[:100]}")
        print(f"  • Recent topics: {p.get('recent_topics', 'N/A')[:100]}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)