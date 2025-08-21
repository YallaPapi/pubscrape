#!/usr/bin/env python3
"""
Real End-to-End Test for Podcast Host Scraper
Tests actual functionality with real queries and data.
"""

import sys
import os
import logging
from pathlib import Path
import json
import csv

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from podcast_scraper.main import PodcastHostScraper
from podcast_scraper.config import config

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
    print("🧪 PODCAST HOST SCRAPER - REAL E2E TEST")
    print("="*80)
    
    # Test configuration
    test_topic = "artificial intelligence"
    test_limit = 5  # Small limit for testing
    test_platforms = ["itunes_api"]  # Use iTunes API for reliable results
    output_file = "e2e_test_results.csv"
    
    print(f"\n📋 Test Configuration:")
    print(f"  • Topic: {test_topic}")
    print(f"  • Platforms: {', '.join(test_platforms)}")
    print(f"  • Limit: {test_limit} podcasts")
    print(f"  • Output: {output_file}")
    
    try:
        # Step 1: Initialize scraper
        print(f"\n[1/5] Initializing Podcast Host Scraper...")
        scraper = PodcastHostScraper()
        print("✅ Scraper initialized successfully")
        
        # Step 2: Scrape podcasts from platforms
        print(f"\n[2/5] Scraping podcasts for '{test_topic}'...")
        podcasts = scraper.scrape_podcasts(
            topic=test_topic,
            limit=test_limit,
            platforms=test_platforms
        )
        
        if not podcasts:
            print("❌ No podcasts found!")
            return False
            
        print(f"✅ Found {len(podcasts)} podcasts:")
        for i, p in enumerate(podcasts[:3], 1):
            print(f"   {i}. {p.podcast_name}")
        
        # Step 3: Enrich with contact information
        print(f"\n[3/5] Enriching with contact information...")
        enriched_podcasts = scraper.enrich_with_contact_info(podcasts)
        
        # Count how many have contact info
        with_website = sum(1 for p in enriched_podcasts if p.podcast_website)
        with_email = sum(1 for p in enriched_podcasts if p.contact_email)
        
        print(f"✅ Contact enrichment complete:")
        print(f"   • Podcasts with website: {with_website}/{len(enriched_podcasts)}")
        print(f"   • Podcasts with email: {with_email}/{len(enriched_podcasts)}")
        
        # Step 4: Export to CSV
        print(f"\n[4/5] Exporting results to CSV...")
        csv_path = scraper.export_to_csv(enriched_podcasts, output_file)
        
        if not os.path.exists(csv_path):
            print(f"❌ CSV file not created at {csv_path}")
            return False
            
        print(f"✅ CSV exported to: {csv_path}")
        
        # Step 5: Verify CSV contents
        print(f"\n[5/5] Verifying CSV contents...")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        print(f"✅ CSV contains {len(rows)} rows")
        
        # Check first row for required fields
        if rows:
            first_row = rows[0]
            required_fields = ['podcast_name', 'podcast_website', 'contact_email']
            missing_fields = [f for f in required_fields if f not in first_row]
            
            if missing_fields:
                print(f"⚠️  Missing fields in CSV: {missing_fields}")
            else:
                print(f"✅ All required fields present in CSV")
            
            # Show sample data
            print(f"\n📊 Sample Data (First Podcast):")
            print(f"   • Name: {first_row.get('podcast_name', 'N/A')}")
            print(f"   • Website: {first_row.get('podcast_website', 'N/A')}")
            print(f"   • Email: {first_row.get('contact_email', 'N/A')}")
            print(f"   • RSS Feed: {first_row.get('rss_feed_url', 'N/A')}")
        
        # Final result
        print(f"\n" + "="*80)
        print(f"✅ E2E TEST PASSED!")
        print(f"="*80)
        print(f"\nResults Summary:")
        print(f"  • Total podcasts scraped: {len(podcasts)}")
        print(f"  • Podcasts with websites: {with_website}")
        print(f"  • Podcasts with emails: {with_email}")
        print(f"  • CSV file created: {csv_path}")
        print(f"  • CSV rows: {len(rows)}")
        
        # Check for real emails
        real_emails = []
        for row in rows:
            email = row.get('contact_email', '').strip()
            if email and '@' in email and '.' in email:
                real_emails.append(email)
        
        if real_emails:
            print(f"\n🎯 Found {len(real_emails)} real email addresses!")
            for email in real_emails[:3]:
                print(f"   • {email}")
        else:
            print(f"\n⚠️  No real email addresses found (this is normal for many podcasts)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ E2E TEST FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    dependencies = {
        'requests': 'Network requests',
        'beautifulsoup4': 'HTML parsing',
        'feedparser': 'RSS feed parsing',
        'botasaurus': 'Anti-detection browser automation'
    }
    
    missing = []
    for module, description in dependencies.items():
        try:
            __import__(module.replace('-', '_'))
            print(f"  ✅ {module}: {description}")
        except ImportError:
            print(f"  ❌ {module}: {description} - NOT INSTALLED")
            missing.append(module)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True


if __name__ == "__main__":
    print("\n🚀 Starting Podcast Host Scraper E2E Test")
    print("This will test real functionality with actual API calls")
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        sys.exit(1)
    
    # Run the test
    success = run_e2e_test()
    
    if success:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please check the errors above.")
        sys.exit(1)