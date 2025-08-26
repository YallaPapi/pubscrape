#!/usr/bin/env python3
"""
Production-ready test to verify Botasaurus can consistently scrape Bing 
for the VRSEN lead generation pipeline.
"""

import time
import json
from botasaurus.browser import browser

@browser(
    headless=True,
    block_images=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    create_error_logs=True
)
def production_bing_scraper(driver, search_data):
    """
    Production-ready Bing scraper using Botasaurus anti-detection.
    """
    query = search_data.get('query', 'optometrist Atlanta')
    page = search_data.get('page', 1)
    
    results = {
        'success': False,
        'query': query,
        'page': page,
        'results': [],
        'html_content': '',
        'metadata': {}
    }
    
    try:
        # Build search URL
        encoded_query = query.replace(' ', '+')
        if page == 1:
            url = f"https://www.bing.com/search?q={encoded_query}"
        else:
            start = (page - 1) * 10 + 1
            url = f"https://www.bing.com/search?q={encoded_query}&first={start}"
        
        print(f"Searching: {url}")
        
        # Navigate with delay
        driver.get(url)
        driver.sleep(3)
        
        # Get content
        html_content = driver.page_html
        current_url = driver.current_url
        
        results['html_content'] = html_content
        results['metadata'] = {
            'final_url': current_url,
            'content_length': len(html_content),
            'page_title': driver.title
        }
        
        # Extract search results
        search_results = []
        
        # Try multiple selectors for Bing results
        result_selectors = [
            '.b_algo',
            'li.b_algo', 
            '.b_result',
            '[data-bm]'
        ]
        
        for selector in result_selectors:
            try:
                elements = driver.select_all(selector)
                if elements and len(elements) > 0:
                    print(f"Found {len(elements)} results with {selector}")
                    
                    for i, elem in enumerate(elements[:10]):  # Top 10 results
                        try:
                            # Extract title
                            title_elem = elem.select('h2 a, .b_title a, a h2')
                            title = title_elem.text.strip() if title_elem else ''
                            
                            # Extract URL
                            url_elem = elem.select('h2 a, .b_title a, a h2')
                            url = url_elem.get_attribute('href') if url_elem else ''
                            
                            # Extract snippet
                            snippet_elem = elem.select('.b_caption p, .b_descript, .b_snippet')
                            snippet = snippet_elem.text.strip() if snippet_elem else ''
                            
                            if title and url:
                                search_results.append({
                                    'position': i + 1,
                                    'title': title,
                                    'url': url,
                                    'snippet': snippet[:200]  # Limit snippet length
                                })
                        except Exception as e:
                            print(f"Error extracting result {i}: {e}")
                            continue
                    
                    break  # Stop after finding results with first working selector
                        
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue
        
        results['results'] = search_results
        results['success'] = len(search_results) > 0
        
        if results['success']:
            print(f"SUCCESS: Extracted {len(search_results)} results")
        else:
            print("WARNING: No results extracted")
            # Check if we got any content at all
            if len(html_content) < 10000:
                print(f"Low content warning: only {len(html_content)} characters")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results['error'] = str(e)
        import traceback
        traceback.print_exc()
    
    return results

def test_multiple_queries():
    """Test multiple different search queries to verify consistency."""
    
    test_queries = [
        "optometrist Atlanta contact",
        "restaurant Chicago owner email", 
        "dentist Miami phone number",
        "lawyer Dallas contact information"
    ]
    
    all_results = []
    
    print("=" * 60)
    print("BOTASAURUS PRODUCTION READINESS TEST")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}/4: {query}")
        print("-" * 40)
        
        start_time = time.time()
        result = production_bing_scraper({'query': query})
        end_time = time.time()
        
        duration = end_time - start_time
        
        test_result = {
            'query': query,
            'success': result['success'],
            'num_results': len(result['results']),
            'content_length': len(result['html_content']),
            'duration_seconds': round(duration, 2),
            'error': result.get('error')
        }
        
        all_results.append(test_result)
        
        # Print summary
        if result['success']:
            print(f"✓ SUCCESS: {len(result['results'])} results in {duration:.2f}s")
            print(f"  Content: {len(result['html_content']):,} characters")
            
            # Show first result
            if result['results']:
                first = result['results'][0]
                print(f"  Sample: {first['title'][:60]}...")
        else:
            print(f"✗ FAILED: {result.get('error', 'No results')}")
        
        # Delay between tests
        if i < len(test_queries):
            print("Waiting 5s before next test...")
            time.sleep(5)
    
    # Overall summary
    print("\n" + "=" * 60)
    print("FINAL VERIFICATION SUMMARY")
    print("=" * 60)
    
    successful_tests = sum(1 for r in all_results if r['success'])
    total_results = sum(r['num_results'] for r in all_results)
    avg_duration = sum(r['duration_seconds'] for r in all_results) / len(all_results)
    avg_content = sum(r['content_length'] for r in all_results) / len(all_results)
    
    print(f"Tests passed: {successful_tests}/{len(test_queries)}")
    print(f"Total results extracted: {total_results}")
    print(f"Average duration: {avg_duration:.2f}s")
    print(f"Average content length: {avg_content:,.0f} characters")
    
    # Determine if production-ready
    if successful_tests >= 3:  # At least 75% success rate
        print("\n🎉 VERDICT: BOTASAURUS IS PRODUCTION-READY FOR BING SCRAPING!")
        print("✓ Consistent results across multiple queries")
        print("✓ Anti-detection features working effectively")
        print("✓ Suitable for VRSEN lead generation pipeline")
    elif successful_tests >= 2:
        print("\n⚠️  VERDICT: BOTASAURUS WORKS BUT NEEDS MONITORING")
        print("✓ Basic functionality confirmed")
        print("⚠ May need additional error handling")
    else:
        print("\n❌ VERDICT: BOTASAURUS NEEDS SIGNIFICANT FIXES")
        print("✗ Inconsistent or failing results")
        print("✗ Not ready for production use")
    
    # Save detailed results
    with open('botasaurus_production_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nDetailed results saved to: botasaurus_production_test_results.json")
    
    return all_results

if __name__ == "__main__":
    test_multiple_queries()