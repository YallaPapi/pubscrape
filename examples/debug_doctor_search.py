#!/usr/bin/env python3
"""
Debug script for doctor search to understand why business detection is failing
"""

import time
import logging
from lead_generator_main import scrape_bing_results, detect_business_relevance

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_doctor_search():
    """Debug the doctor search process"""
    print("=" * 60)
    print("DEBUGGING DOCTOR SEARCH")
    print("=" * 60)
    
    # Test query
    query = "doctors Miami Florida"
    print(f"Testing query: {query}")
    
    # Scrape results
    print("\nScraping Bing search results...")
    try:
        results = scrape_bing_results(query, max_pages=1)
        print(f"Found {len(results)} search results")
        
        if len(results) == 0:
            print("ERROR: No search results found!")
            return
        
        # Analyze each result
        print(f"\nAnalyzing search results:")
        print("-" * 60)
        
        business_count = 0
        for i, result in enumerate(results[:10], 1):
            print(f"\nResult {i}:")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  URL: {result.get('url', 'N/A')}")
            print(f"  Description: {result.get('description', 'N/A')[:100]}...")
            print(f"  Domain: {result.get('domain', 'N/A')}")
            
            # Test business detection
            is_business = result.get('is_business', False)
            print(f"  Is Business: {is_business}")
            
            if is_business:
                business_count += 1
            else:
                # Debug why it's not classified as business
                print(f"  >>> NOT classified as business - debugging...")
                title = result.get('title', '')
                description = result.get('description', '')
                url = result.get('url', '')
                
                # Re-run business detection with debug info
                business_check = detect_business_relevance(title, description, url, query)
                print(f"  >>> Business detection result: {business_check}")
                
                # Check for exclusions
                exclude_patterns = [
                    'wikipedia', 'facebook.com', 'twitter.com', 'instagram.com',
                    'linkedin.com', 'youtube.com', 'yelp.com', 'google.com',
                    'directory', 'listing', 'review', 'forum', 'blog'
                ]
                
                url_lower = url.lower()
                text_lower = f"{title} {description}".lower()
                
                exclusions_found = []
                for pattern in exclude_patterns:
                    if pattern in url_lower or pattern in text_lower:
                        exclusions_found.append(pattern)
                
                if exclusions_found:
                    print(f"  >>> EXCLUDED due to: {exclusions_found}")
                else:
                    print(f"  >>> Not excluded, checking business indicators...")
                    
                    business_indicators = [
                        'contact', 'about', 'services', 'location', 'phone', 'email',
                        'hours', 'appointment', 'consultation', 'clinic', 'office',
                        'practice', 'company', 'business', 'professional', 'service'
                    ]
                    
                    indicators_found = []
                    for indicator in business_indicators:
                        if indicator in text_lower:
                            indicators_found.append(indicator)
                    
                    print(f"  >>> Business indicators found: {indicators_found} (need >= 2)")
        
        print(f"\n" + "=" * 60)
        print(f"SUMMARY:")
        print(f"Total search results: {len(results)}")
        print(f"Classified as businesses: {business_count}")
        print(f"Business detection rate: {(business_count/len(results)*100):.1f}%")
        
        if business_count == 0:
            print(f"\nPROBLEM: No results classified as businesses!")
            print(f"This explains why 0 leads were generated.")
            print(f"Need to adjust business detection logic.")
        
    except Exception as e:
        print(f"ERROR during scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_doctor_search()