#!/usr/bin/env python3
"""
Final verification that Botasaurus is working for Bing scraping.
"""

import json
from botasaurus.browser import browser

@browser(headless=True, block_images=True)
def verify_bing_scraping(driver, data):
    """Simple verification test for Bing scraping with Botasaurus."""
    
    query = "optometrist Atlanta contact"
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    
    try:
        driver.get(url)
        driver.sleep(3)
        
        html = driver.page_html
        results = driver.select_all('.b_algo')
        
        # Extract first result
        first_result = None
        if results:
            try:
                title_elem = results[0].select('h2 a')
                title = title_elem.text if title_elem else 'No title'
                
                url_elem = results[0].select('h2 a')
                result_url = url_elem.get_attribute('href') if url_elem else 'No URL'
                
                first_result = {'title': title, 'url': result_url}
            except:
                pass
        
        return {
            'success': len(results) > 0,
            'query': query,
            'num_results': len(results),
            'content_length': len(html),
            'first_result': first_result
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    print("FINAL BOTASAURUS VERIFICATION")
    print("=" * 40)
    
    result = verify_bing_scraping()
    
    print(f"Success: {result['success']}")
    print(f"Results found: {result.get('num_results', 0)}")
    print(f"Content length: {result.get('content_length', 0):,}")
    
    if result.get('first_result'):
        print(f"Sample result: {result['first_result']['title']}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Save results
    with open('final_verification_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("Results saved to final_verification_results.json")