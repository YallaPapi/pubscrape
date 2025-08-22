#!/usr/bin/env python3
"""
Debug script to see exactly what's happening during the search process.
"""

import os
import sys
import time

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from botasaurus.browser import browser

@browser(headless=False)  # Use visible browser for debugging
def debug_bing_typing(driver, data):
    """Debug function to see exactly what happens during search"""
    
    print("Navigating to Bing...")
    driver.get("https://www.bing.com")
    time.sleep(3)
    
    print(f"Initial URL: {driver.current_url}")
    
    # Find and examine the search box
    search_box_selector = '#sb_form_q'
    
    try:
        print("Looking for search box...")
        driver.wait_for_element(search_box_selector)
        print("Search box found!")
        
        search_box = driver.select(search_box_selector)
        print(f"Search box element: {search_box}")
        
        # Check the current value
        current_value = search_box.get_attribute("value") if search_box else "NO ELEMENT"
        print(f"Current search box value: '{current_value}'")
        
        # Clear and type slowly 
        print("Typing query...")
        driver.type(search_box_selector, "optometrist Atlanta")
        time.sleep(2)
        
        # Check value after typing
        search_box = driver.select(search_box_selector)
        new_value = search_box.get_attribute("value") if search_box else "NO ELEMENT"
        print(f"Search box value after typing: '{new_value}'")
        
        # Try to find and click a submit button instead of pressing Enter
        submit_selectors = [
            'input[type="submit"]',
            '#sb_form_go',
            '.b_searchboxSubmit',
            'button[aria-label*="Search"]',
            'svg[role="img"]'
        ]
        
        submit_found = False
        for selector in submit_selectors:
            try:
                submit_btn = driver.select(selector)
                if submit_btn:
                    print(f"Found submit element with selector: {selector}")
                    submit_btn.click()
                    submit_found = True
                    break
            except Exception as e:
                print(f"Selector {selector} failed: {e}")
        
        if not submit_found:
            print("No submit button found, trying Enter key...")
            # Focus the search box and press Enter
            search_box = driver.select(search_box_selector)
            if search_box:
                search_box.send_keys("\n")
                print("Pressed Enter")
            else:
                print("Could not focus search box for Enter")
        
        # Wait and check URL change
        print("Waiting for URL change...")
        initial_url = driver.current_url
        for i in range(20):  # Wait up to 20 seconds
            time.sleep(1)
            current_url = driver.current_url
            print(f"Second {i+1}: URL = {current_url}")
            if current_url != initial_url and "/search?" in current_url:
                print("SUCCESS: URL changed to search results!")
                break
        else:
            print("FAILED: URL never changed")
        
        # Final check
        final_url = driver.current_url
        print(f"Final URL: {final_url}")
        
        # Take a screenshot
        driver.save_screenshot("debug_final_state.png")
        print("Screenshot saved as debug_final_state.png")
        
        # Wait for user input to close
        input("Press Enter to close browser...")
        
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close browser...")
    
    return {
        "final_url": driver.current_url,
        "search_completed": "/search?" in driver.current_url
    }

if __name__ == "__main__":
    result = debug_bing_typing(data={})
    print(f"Debug result: {result}")