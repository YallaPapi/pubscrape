#!/usr/bin/env python3
"""
Simple test version of the podcast scraper to verify basic functionality.
"""

import logging
from podcast_scraper.base import PodcastData

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_test_podcast():
    """Create a test podcast entry to verify the system works."""
    podcast = PodcastData(
        podcast_name="Disgraceland",
        podcast_description="A test podcast about music and crime",
        apple_podcasts_url="https://podcasts.apple.com/us/podcast/disgraceland/id1275172907",
        platform_source="Apple Podcasts"
    )
    return podcast

def test_csv_export():
    """Test CSV export functionality."""
    from podcast_scraper.main import PodcastHostScraper
    
    # Create test data
    test_podcasts = [create_test_podcast()]
    
    # Initialize scraper
    scraper = PodcastHostScraper()
    scraper.all_podcasts = test_podcasts
    
    # Export to CSV
    csv_path = scraper.export_to_csv(test_podcasts, "test_results.csv")
    print(f"CSV exported to: {csv_path}")
    
    # Generate report
    report_path = scraper.generate_report(test_podcasts, "test_report.md")
    print(f"Report generated: {report_path}")
    
    # Print statistics
    stats = scraper.get_statistics()
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    print("Testing basic podcast scraper functionality...")
    test_csv_export()
    print("✓ Basic functionality test completed!")