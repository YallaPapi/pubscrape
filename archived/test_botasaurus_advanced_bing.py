#!/usr/bin/env python3
"""
Advanced Botasaurus test for Bing with better anti-detection configuration.
Testing Botasaurus's built-in stealth capabilities against Bing.
"""

import time
import random
import hashlib
from botasaurus.browser import browser

# Generate a unique profile name for this session
session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

@browser(
    headless=True,  # Run headless for stealth
    block_images=True,  # Block images to avoid fingerprinting
    wait_for_complete_page_load=False,  # Don't wait for all resources
    profile=f"bing_stealth_{session_id}",  # Unique profile per run
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    max_retry=3,  # Retry on failure
    create_error_logs=True  # Capture errors
)
def test_advanced_bing_stealth(driver, data):
    """
    Advanced test using Botasaurus's anti-detection features.
    """
    results = {
        "success": False,
        "bing_accessible": False,
        "search_executed": False,
        "results_found": False,
        "blocked_indicators": [],
        "stealth_detected": False,
        "page_behavior": {},
        "error": None
    }
    
    try:
        print("Phase 1: Advanced stealth navigation to Bing...")
        
        # Add random initial delay
        initial_delay = random.uniform(2, 5)
        print(f"Initial delay: {initial_delay:.2f}s")
        driver.sleep(initial_delay)
        
        # Navigate to Bing homepage first (more natural)
        driver.get("https://www.bing.com")
        
        # Wait and analyze initial response
        driver.sleep(random.uniform(3, 6))
        
        current_url = driver.current_url
        page_title = driver.title
        page_html = driver.page_html
        
        results["bing_accessible"] = "bing.com" in current_url
        results["page_behavior"]["initial_url"] = current_url
        results["page_behavior"]["page_title"] = page_title
        results["page_behavior"]["content_length"] = len(page_html)
        
        print(f"Initial URL: {current_url}")
        print(f"Page title: {page_title}")
        print(f"Content length: {len(page_html)}")
        
        # Check for blocking/bot detection
        html_lower = page_html.lower()
        blocking_indicators = [
            "captcha", "blocked", "too many requests", "rate limit",
            "access denied", "suspicious activity", "verify you are human",
            "unusual traffic", "automated", "robot", "bot"
        ]
        
        found_blocking = []
        for indicator in blocking_indicators:
            if indicator in html_lower:
                found_blocking.append(indicator)
        
        results["blocked_indicators"] = found_blocking
        
        if found_blocking:
            print(f"Phase 1 ISSUE: Blocking indicators found: {found_blocking}")
            # Don't return yet, try to proceed
        else:
            print("Phase 1 SUCCESS: No blocking indicators found")
        
        print("Phase 2: Attempting stealth search...")
        
        # Look for search box with multiple strategies
        search_selectors = [
            '#sb_form_q',
            'input[name="q"]',
            'input[type="search"]',
            'input[aria-label*="search"]',
            'input[placeholder*="search"]'
        ]
        
        search_box = None
        search_selector_used = None
        
        for selector in search_selectors:
            try:
                search_box = driver.select(selector)
                if search_box and search_box.is_displayed():
                    search_selector_used = selector
                    print(f"Found search box: {selector}")
                    break
            except:
                continue
        
        if not search_box:
            print("Phase 2 ISSUE: No search box found")
            results["error"] = "Search box not found"
            
            # Try direct search URL as fallback
            print("Attempting direct search URL...")
            search_query = "optometrist Atlanta contact"
            search_url = f"https://www.bing.com/search?q={search_query.replace(' ', '+')}"
            driver.get(search_url)
            driver.sleep(random.uniform(4, 7))
            
            search_results_html = driver.page_html
            results["page_behavior"]["search_url"] = search_url
            results["page_behavior"]["search_content_length"] = len(search_results_html)
            
            # Check if we got search results via direct URL
            if "search" in driver.current_url and len(search_results_html) > 10000:
                results["search_executed"] = True
                page_html = search_results_html  # Use this for result extraction
                print("Direct search URL method worked")
            else:
                print("Direct search URL also failed")
                return results
        else:
            # Interactive search via search box
            search_query = "optometrist Atlanta contact"
            
            # Human-like typing
            search_box.clear()
            driver.sleep(random.uniform(0.5, 1.5))
            
            # Type with human-like delays
            for char in search_query:
                search_box.type(char)
                driver.sleep(random.uniform(0.05, 0.15))
            
            driver.sleep(random.uniform(1, 3))
            
            # Submit search (try Enter key first, then button)
            try:
                search_box.type("\n")
                driver.sleep(random.uniform(3, 6))
                results["search_executed"] = True
                print("Search submitted via Enter key")
            except:
                try:
                    submit_button = driver.select('input[type="submit"], button[type="submit"], #sb_form_go')
                    if submit_button:
                        submit_button.click()
                        driver.sleep(random.uniform(3, 6))
                        results["search_executed"] = True
                        print("Search submitted via button click")
                except:
                    print("Could not submit search")
                    results["error"] = "Could not submit search"
                    return results
        
        if results["search_executed"]:
            print("Phase 3: Analyzing search results...")
            
            # Get current state after search
            final_url = driver.current_url
            final_html = driver.page_html
            
            results["page_behavior"]["final_url"] = final_url
            results["page_behavior"]["final_content_length"] = len(final_html)
            
            print(f"Final URL: {final_url}")
            print(f"Final content length: {len(final_html)}")
            
            # Check for search results
            result_indicators = [
                '.b_algo',  # Main Bing result class
                'li.b_algo',
                '.b_result',
                '[data-bm]',
                'ol#b_results li',
                '.b_title'
            ]
            
            found_results = False
            result_count = 0
            
            for indicator in result_indicators:
                try:
                    elements = driver.select_all(indicator)
                    if elements and len(elements) > 0:
                        found_results = True
                        result_count = len(elements)
                        print(f"Found {result_count} results with selector: {indicator}")
                        break
                except:
                    continue
            
            results["results_found"] = found_results
            results["page_behavior"]["result_count"] = result_count
            
            if found_results:
                print("Phase 3 SUCCESS: Search results found!")
                results["success"] = True
                
                # Try to extract a few sample results
                try:
                    sample_results = []
                    result_elements = driver.select_all('.b_algo, li.b_algo')[:3]
                    
                    for i, elem in enumerate(result_elements):
                        try:
                            title_elem = elem.select('h2 a, .b_title a')
                            url_elem = elem.select('cite, .b_cit, .tgr-cite')
                            
                            title = title_elem.text if title_elem else "No title"
                            url = url_elem.text if url_elem else "No URL"
                            
                            sample_results.append({
                                "position": i + 1,
                                "title": title[:100],
                                "url": url[:100]
                            })
                        except:
                            continue
                    
                    results["sample_results"] = sample_results
                    print(f"Extracted {len(sample_results)} sample results")
                    
                except Exception as e:
                    print(f"Warning: Could not extract sample results: {e}")
            else:
                print("Phase 3 ISSUE: No search results found")
                
                # Check if we're being blocked on results page
                final_html_lower = final_html.lower()
                result_blocking = []
                for indicator in blocking_indicators:
                    if indicator in final_html_lower:
                        result_blocking.append(indicator)
                
                if result_blocking:
                    results["blocked_indicators"].extend(result_blocking)
                    print(f"Blocking indicators on results page: {result_blocking}")
        
        # Take final screenshot for analysis
        try:
            screenshot_path = f"bing_advanced_test_{session_id}.png"
            driver.save_screenshot(screenshot_path)
            results["screenshot"] = screenshot_path
        except:
            pass
            
    except Exception as e:
        print(f"ERROR in advanced test: {str(e)}")
        results["error"] = str(e)
        import traceback
        traceback.print_exc()
    
    return results

if __name__ == "__main__":
    print("="*60)
    print("ADVANCED BOTASAURUS ANTI-DETECTION TEST FOR BING")
    print("="*60)
    print(f"Session ID: {session_id}")
    print("Testing Botasaurus's built-in stealth capabilities...")
    
    result = test_advanced_bing_stealth()
    
    print("\n" + "="*60)
    print("COMPREHENSIVE VERIFICATION RESULTS:")
    print("="*60)
    
    # Core accessibility
    print(f"✓ Bing Accessible: {result['bing_accessible']}")
    print(f"✓ Search Executed: {result['search_executed']}")
    print(f"✓ Results Found: {result['results_found']}")
    print(f"✓ Overall Success: {result['success']}")
    
    # Blocking analysis
    if result['blocked_indicators']:
        print(f"⚠ Blocking Indicators: {result['blocked_indicators']}")
    else:
        print("✓ No Blocking Indicators Found")
    
    # Performance metrics
    if result.get('page_behavior'):
        behavior = result['page_behavior']
        print(f"\nPage Behavior Analysis:")
        print(f"  Initial Content: {behavior.get('content_length', 0):,} characters")
        print(f"  Final Content: {behavior.get('final_content_length', 0):,} characters")
        print(f"  Result Count: {behavior.get('result_count', 0)}")
    
    # Sample results
    if result.get('sample_results'):
        print(f"\nSample Results Extracted:")
        for res in result['sample_results']:
            print(f"  {res['position']}. {res['title']}")
            print(f"     URL: {res['url']}")
    
    # Error reporting
    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")
    
    # Final verdict
    print(f"\n{'='*60}")
    if result['success']:
        print("🎉 VERDICT: BOTASAURUS ANTI-DETECTION IS WORKING!")
        print("   - Successfully bypassed Bing's bot detection")
        print("   - Retrieved real search results")
        print("   - Stealth features are functional")
    elif result['bing_accessible'] and not result['results_found']:
        print("⚠️  VERDICT: PARTIAL SUCCESS - STEALTH NEEDS IMPROVEMENT")
        print("   - Can access Bing but results are limited")
        print("   - May need additional anti-detection measures")
    else:
        print("❌ VERDICT: ANTI-DETECTION NEEDS SIGNIFICANT WORK")
        print("   - Bing is detecting and blocking the bot")
        print("   - Current stealth configuration insufficient")
    
    print(f"\nFull technical details: {result}")