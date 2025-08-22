#!/usr/bin/env python3
"""
Test if Botasaurus can successfully scrape Bing search results using its anti-detection features.
"""

import time
from botasaurus.browser import browser

@browser(
    headless=False,  # Start with visible to see what's happening
    block_images=True,  # Block images for faster loading
    max_retry=3,     # Retry on failure
    wait_for_complete_page_load=False,  # Don't wait for all resources
    close_on_crash=True  # Close browser on crash
)
def test_bing_search(driver, data):
    """Test if Botasaurus can scrape Bing with anti-detection."""
    results = {
        "success": False,
        "bing_accessible": False,
        "search_executed": False,
        "results_found": False,
        "blocked_indicators": [],
        "error": None
    }
    
    try:
        print("Step 1: Navigating to Bing...")
        driver.get("https://www.bing.com")
        time.sleep(2)
        
        # Check if we reached Bing successfully
        current_url = driver.current_url
        page_title = driver.title
        results["bing_accessible"] = "bing.com" in current_url
        
        print(f"Current URL: {current_url}")
        print(f"Page title: {page_title}")
        
        # Get page content to check for blocking
        page_html = driver.page_html
        html_lower = page_html.lower()
        
        # Check for blocking indicators
        blocking_indicators = [
            "captcha", "blocked", "too many requests", "rate limit",
            "access denied", "suspicious activity", "verify you are human",
            "robot", "automation", "unusual traffic"
        ]
        
        found_blocking = []
        for indicator in blocking_indicators:
            if indicator in html_lower:
                found_blocking.append(indicator)
        
        results["blocked_indicators"] = found_blocking
        
        if found_blocking:
            print(f"WARNING: Found blocking indicators: {found_blocking}")
            return results
        
        print("Step 2: Looking for search box...")
        # Try to find the search input
        search_inputs = [
            'input[name="q"]',
            'input[id="sb_form_q"]',
            'input[class*="search"]',
            'input[type="search"]'
        ]
        
        search_box = None
        for selector in search_inputs:
            try:
                search_box = driver.select(selector)
                if search_box:
                    print(f"Found search box with selector: {selector}")
                    break
            except:
                continue
        
        if not search_box:
            print("ERROR: Could not find search box")
            results["error"] = "Search box not found"
            return results
        
        print("Step 3: Performing search...")
        # Clear and enter search query
        search_query = "optometrist Atlanta"
        search_box.clear()
        time.sleep(1)
        search_box.type(search_query)
        time.sleep(1)
        
        # Submit search
        search_box.type("\n")  # Press Enter
        time.sleep(3)  # Wait for results
        
        results["search_executed"] = True
        print("Search submitted successfully")
        
        print("Step 4: Checking for search results...")
        # Look for search results
        result_selectors = [
            '.b_algo',  # Main search results
            '.b_result',
            '[data-bm]',  # Result containers
            'li.b_algo',
            'ol#b_results li'
        ]
        
        search_results = []
        for selector in result_selectors:
            try:
                elements = driver.select_all(selector)
                if elements:
                    search_results = elements
                    print(f"Found {len(elements)} results with selector: {selector}")
                    break
            except:
                continue
        
        if search_results:
            results["results_found"] = True
            results["num_results"] = len(search_results)
            
            # Extract first few results for verification
            extracted_results = []
            for i, result in enumerate(search_results[:3]):
                try:
                    title_elem = result.select('h2 a, .b_title a, a h2')
                    url_elem = result.select('cite, .b_attribution cite, .tgr-cite')
                    
                    title = title_elem.text if title_elem else "No title"
                    url = url_elem.text if url_elem else "No URL"
                    
                    extracted_results.append({
                        "title": title[:100],
                        "url": url[:100]
                    })
                except Exception as e:
                    print(f"Error extracting result {i}: {e}")
            
            results["sample_results"] = extracted_results
            results["success"] = True
            print(f"SUCCESS: Found {len(search_results)} search results")
        else:
            print("ERROR: No search results found")
            results["error"] = "No search results found"
        
        # Take screenshot for verification
        screenshot_path = f"bing_test_screenshot_{int(time.time())}.png"
        driver.save_screenshot(screenshot_path)
        results["screenshot"] = screenshot_path
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        results["error"] = str(e)
        import traceback
        traceback.print_exc()
    
    return results

if __name__ == "__main__":
    print("Testing Botasaurus with Bing search...")
    print("This will open a visible browser to verify anti-detection is working.")
    
    result = test_bing_search()
    
    print("\n" + "="*50)
    print("VERIFICATION RESULTS:")
    print("="*50)
    print(f"Bing Accessible: {result['bing_accessible']}")
    print(f"Search Executed: {result['search_executed']}")
    print(f"Results Found: {result['results_found']}")
    print(f"Overall Success: {result['success']}")
    
    if result['blocked_indicators']:
        print(f"Blocking Indicators: {result['blocked_indicators']}")
    
    if result.get('num_results'):
        print(f"Number of Results: {result['num_results']}")
    
    if result.get('sample_results'):
        print("\nSample Results:")
        for i, res in enumerate(result['sample_results']):
            print(f"  {i+1}. {res['title']}")
            print(f"     {res['url']}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    print(f"\nFull result: {result}")