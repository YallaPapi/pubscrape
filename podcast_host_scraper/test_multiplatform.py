#!/usr/bin/env python3
"""
Test multi-platform podcast scraping functionality.
"""

import logging
from podcast_scraper.main import PodcastHostScraper
from podcast_scraper.platforms.spotify import SpotifyPodcastsScraper
from podcast_scraper.platforms.google_podcasts import GooglePodcastsScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_spotify_scraper():
    """Test Spotify scraper independently."""
    print("Testing Spotify Scraper...")
    print("=" * 40)
    
    scraper = SpotifyPodcastsScraper()
    
    # Test with AI topic
    podcasts = scraper.scrape_podcasts("artificial intelligence", limit=5)
    
    print(f"Found {len(podcasts)} podcasts from Spotify:")
    for i, podcast in enumerate(podcasts, 1):
        print(f"  {i}. {podcast.podcast_name}")
        print(f"     Host: {podcast.host_name or 'Unknown'}")
        print(f"     Episodes: {podcast.episode_count or 'Unknown'}")
        print(f"     Platform: {podcast.platform_source}")
        print()

def test_youtube_scraper():
    """Test YouTube/Google Podcasts scraper."""
    print("\nTesting YouTube/Google Podcasts Scraper...")
    print("=" * 40)
    
    scraper = GooglePodcastsScraper()
    
    # Test with technology topic
    podcasts = scraper.scrape_podcasts("technology", limit=5)
    
    print(f"Found {len(podcasts)} podcasts from YouTube:")
    for i, podcast in enumerate(podcasts, 1):
        print(f"  {i}. {podcast.podcast_name}")
        print(f"     Host: {podcast.host_name or 'Unknown'}")
        print(f"     Website: {podcast.podcast_website or 'Unknown'}")
        print(f"     Platform: {podcast.platform_source}")
        print()

def test_multiplatform_scraper():
    """Test integrated multi-platform scraper."""
    print("\n" + "=" * 60)
    print("Testing Integrated Multi-Platform Scraper")
    print("=" * 60)
    
    main_scraper = PodcastHostScraper()
    
    # Test with business topic across multiple platforms
    platforms = ["apple_podcasts", "spotify", "youtube"]
    
    print(f"Testing with platforms: {platforms}")
    print("Topic: business")
    print("Limit: 3 per platform")
    print()
    
    podcasts = main_scraper.scrape_podcasts(
        topic="business",
        limit=3,
        platforms=platforms
    )
    
    print(f"\nTotal unique podcasts found: {len(podcasts)}")
    
    # Group by platform
    platform_counts = {}
    for podcast in podcasts:
        platform = podcast.platform_source
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    print("\nPlatform breakdown:")
    for platform, count in platform_counts.items():
        print(f"  {platform}: {count} podcasts")
    
    print(f"\nTop 5 Results (across all platforms):")
    for i, podcast in enumerate(podcasts[:5], 1):
        print(f"  {i}. {podcast.podcast_name}")
        print(f"     Host: {podcast.host_name or 'Unknown'}")
        print(f"     Platform: {podcast.platform_source}")
        print(f"     Website: {podcast.podcast_website or 'None'}")
        print()
    
    # Test statistics
    stats = main_scraper.get_statistics()
    print("Overall Statistics:")
    print(f"  Total: {stats.get('total', 0)}")
    print(f"  With Host Names: {stats.get('with_host_names', 0)} ({stats.get('host_name_rate', '0%')})")
    print(f"  With Websites: {stats.get('with_websites', 0)} ({stats.get('website_rate', '0%')})")

def test_configuration_check():
    """Test platform availability based on configuration."""
    print("\n" + "=" * 60)
    print("Testing Platform Configuration")
    print("=" * 60)
    
    from podcast_scraper.config import config
    
    features = config.get_available_features()
    
    print("Platform Availability:")
    platform_features = {
        'Apple Podcasts': features.get('apple_podcasts', False),
        'Spotify': features.get('spotify_discovery', False),
        'YouTube/Google': True,  # Always available (web scraping)
        'Contact Extraction': features.get('contact_extraction', False),
        'AI Scoring': features.get('ai_scoring', False)
    }
    
    for platform, available in platform_features.items():
        status = "[OK]" if available else "[--]"
        print(f"  {status} {platform}")
    
    print("\nAPI Keys Status:")
    print(f"  Spotify Keys: {'Available' if config.has_spotify_keys() else 'Not configured'}")
    print(f"  OpenAI Key: {'Available' if config.has_openai_key() else 'Not configured'}")
    print(f"  Google Search Keys: {'Available' if config.has_google_search_keys() else 'Not configured'}")

if __name__ == "__main__":
    try:
        test_configuration_check()
        test_spotify_scraper()
        test_youtube_scraper()
        test_multiplatform_scraper()
        
        print("\n" + "="*60)
        print("[SUCCESS] Multi-platform scraping tests completed!")
        print("="*60)
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()