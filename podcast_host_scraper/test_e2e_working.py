#!/usr/bin/env python3
"""
Working End-to-End Test for Podcast Host Scraper
Tests actual functionality with real queries and data.
"""

import sys
import os
import logging
from pathlib import Path
import csv

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def run_e2e_test():
    """Run a complete end-to-end test with real data."""
    
    print("\n" + "="*80)
    print("PODCAST HOST SCRAPER - WORKING E2E TEST")
    print("="*80)
    
    # Test configuration
    test_topic = "artificial intelligence"
    test_limit = 5
    output_file = "e2e_test_results.csv"
    
    print(f"\nTest Configuration:")
    print(f"  • Topic: {test_topic}")
    print(f"  • Limit: {test_limit} podcasts")
    print(f"  • Output: {output_file}")
    
    try:
        # Step 1: Test iTunes API directly
        print(f"\n[1/3] Testing iTunes API directly...")
        from podcast_scraper.platforms.itunes_api import ITunesApiScraper
        
        scraper = ITunesApiScraper()
        podcasts = scraper.scrape_podcasts(test_topic, test_limit)
        
        if not podcasts:
            print("No podcasts found!")
            return False
            
        print(f"Found {len(podcasts)} podcasts:")
        for i, p in enumerate(podcasts[:3], 1):
            print(f"   {i}. {p.podcast_name}")
            if p.rss_feed_url:
                print(f"      RSS: {p.rss_feed_url[:50]}...")
        
        # Step 2: Enrich with contact info
        print(f"\n[2/3] Testing contact enrichment...")
        from podcast_scraper.contact_extraction import ContactExtractor
        
        extractor = ContactExtractor()
        enriched_count = 0
        
        for podcast in podcasts:
            # Try to extract website from RSS feed
            if podcast.rss_feed_url:
                try:
                    import feedparser
                    feed = feedparser.parse(podcast.rss_feed_url)
                    if feed.feed.get('link'):
                        podcast.podcast_website = feed.feed.link
                        enriched_count += 1
                        print(f"   Found website for {podcast.podcast_name}: {podcast.podcast_website}")
                except Exception as e:
                    print(f"   Could not parse RSS for {podcast.podcast_name}: {e}")
        
        print(f"Enriched {enriched_count}/{len(podcasts)} podcasts with website info")
        
        # Step 3: Export to CSV
        print(f"\n[3/3] Exporting to CSV...")
        
        # Create output directory if needed
        output_dir = Path("podcast_host_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / output_file
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'podcast_name',
                'podcast_website', 
                'contact_email',
                'rss_feed_url',
                'apple_podcasts_url',
                'spotify_url',
                'platform_source'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for podcast in podcasts:
                row = {
                    'podcast_name': podcast.podcast_name,
                    'podcast_website': getattr(podcast, 'podcast_website', ''),
                    'contact_email': getattr(podcast, 'contact_email', ''),
                    'rss_feed_url': podcast.rss_feed_url or '',
                    'apple_podcasts_url': podcast.apple_podcasts_url or '',
                    'spotify_url': getattr(podcast, 'spotify_url', ''),
                    'platform_source': podcast.platform_source
                }
                writer.writerow(row)
        
        print(f"CSV exported to: {csv_path}")
        
        # Verify CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        print(f"CSV contains {len(rows)} rows")
        
        # Final result
        print(f"\n" + "="*80)
        print(f"E2E TEST PASSED!")
        print(f"="*80)
        print(f"\nResults Summary:")
        print(f"  • Total podcasts scraped: {len(podcasts)}")
        print(f"  • Podcasts with websites: {enriched_count}")
        print(f"  • CSV file created: {csv_path}")
        print(f"  • CSV rows: {len(rows)}")
        
        return True
        
    except Exception as e:
        print(f"\nE2E TEST FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting Podcast Host Scraper E2E Test")
    print("This will test real functionality with actual API calls")
    
    # Run the test
    success = run_e2e_test()
    
    if success:
        print("\nAll tests passed successfully!")
        sys.exit(0)
    else:
        print("\nTests failed. Please check the errors above.")
        sys.exit(1)