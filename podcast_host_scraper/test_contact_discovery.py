#!/usr/bin/env python3
"""
Test the contact discovery functionality.
"""

import logging
from podcast_scraper.base import PodcastData
from podcast_scraper.contact_discovery import ContactPageDiscovery

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_contact_discovery():
    """Test contact discovery functionality."""
    
    # Create a test podcast
    test_podcast = PodcastData(
        podcast_name="The Tim Ferriss Show",
        podcast_description="A popular interview show about productivity and success",
        rss_feed_url="https://rss.art19.com/tim-ferriss-show",
        apple_podcasts_url="https://podcasts.apple.com/us/podcast/the-tim-ferriss-show/id863897795",
        platform_source="Apple Podcasts"
    )
    
    # Initialize contact discovery
    contact_discovery = ContactPageDiscovery()
    
    print("Testing Contact Discovery...")
    print(f"Test Podcast: {test_podcast.podcast_name}")
    
    # Test website discovery
    print("\n1. Testing website discovery...")
    website_url = contact_discovery.discover_website(test_podcast)
    print(f"   Discovered website: {website_url}")
    
    if website_url:
        test_podcast.podcast_website = website_url
        
        # Test contact page discovery
        print("\n2. Testing contact page discovery...")
        contact_pages = contact_discovery.find_contact_pages(website_url)
        print(f"   Found {len(contact_pages)} contact pages:")
        for page in contact_pages[:3]:  # Show first 3
            print(f"   - {page}")
        
        # Test contact info extraction
        if contact_pages:
            print("\n3. Testing contact info extraction...")
            contact_info = contact_discovery.extract_contact_info(contact_pages[0])
            print(f"   Emails found: {len(contact_info['emails'])}")
            print(f"   Social links found: {len(contact_info['social_links'])}")
            print(f"   Contact forms: {len(contact_info['contact_forms'])}")
            
            if contact_info['emails']:
                print(f"   First email: {contact_info['emails'][0]}")
            if contact_info['social_links']:
                print(f"   Social platforms: {list(contact_info['social_links'].keys())}")
    
    print("\n✓ Contact discovery test completed!")

def test_with_main_scraper():
    """Test contact discovery integration with main scraper."""
    from podcast_scraper.main import PodcastHostScraper
    
    print("\n" + "="*60)
    print("Testing Contact Discovery Integration")
    print("="*60)
    
    # Create test podcasts
    test_podcasts = [
        PodcastData(
            podcast_name="The Tim Ferriss Show",
            rss_feed_url="https://rss.art19.com/tim-ferriss-show",
            platform_source="Apple Podcasts"
        ),
        PodcastData(
            podcast_name="How I Built This",
            apple_podcasts_url="https://podcasts.apple.com/us/podcast/how-i-built-this-with-guy-raz/id1150510297",
            platform_source="Apple Podcasts"
        )
    ]
    
    # Initialize scraper
    scraper = PodcastHostScraper()
    
    # Test enrichment
    print(f"Enriching {len(test_podcasts)} test podcasts...")
    enriched_podcasts = scraper.enrich_with_contact_info(test_podcasts)
    
    # Show results
    print(f"\nEnrichment Results:")
    for i, podcast in enumerate(enriched_podcasts, 1):
        print(f"\n{i}. {podcast.podcast_name}")
        print(f"   Website: {podcast.podcast_website or 'Not found'}")
        print(f"   Host Email: {podcast.host_email or 'Not found'}")
        print(f"   Contact Confidence: {podcast.contact_confidence}")
        print(f"   Social Links: {len(podcast.social_links) if podcast.social_links else 0}")
    
    print("\n✓ Integration test completed!")

if __name__ == "__main__":
    try:
        test_contact_discovery()
        test_with_main_scraper()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()