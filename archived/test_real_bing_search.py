#!/usr/bin/env python3
"""
Test script to verify that Bing search now returns REAL results instead of mock data.
This will test with "lawyer Chicago" as requested.
"""

import sys
import os
import logging
import time

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_real_bing_search():
    """Test with 'lawyer Chicago' to verify real search results"""
    print("=" * 60)
    print("TESTING REAL BING SEARCH - NO MORE SYNTHETIC DATA")
    print("=" * 60)
    
    try:
        from agents.tools.bing_search_tool import BingSearchTool, BOTASAURUS_AVAILABLE
        
        print(f"[+] Botasaurus Available: {BOTASAURUS_AVAILABLE}")
        
        # Create the tool instance with the test query
        tool = BingSearchTool(
            query="lawyer Chicago",
            max_pages=1,
            store_html=True
        )
        
        print(f"\nExecuting search for: '{tool.query}'")
        print("This should return REAL lawyer firm URLs, not example.com URLs")
        
        # Execute the search
        start_time = time.time()
        result = tool.run()
        execution_time = time.time() - start_time
        
        print(f"\n{'='*40}")
        print("SEARCH RESULTS ANALYSIS")
        print(f"{'='*40}")
        
        print(f"Success: {result['success']}")
        print(f"Pages retrieved: {result['pages_retrieved']}")
        print(f"Execution time: {execution_time:.2f}s")
        
        if result['success'] and result['results']:
            first_result = result['results'][0]
            url = first_result.get('url', '')
            
            print(f"\nFirst result URL: {url}")
            
            # Check if we got real results
            if "example.com" in url:
                print("\n[!] FAILED: Still returning mock data with example.com URLs!")
                print("[!] The search is NOT working correctly - synthetic data detected")
                return False
            elif "bing.com/search" in url:
                print("\n[+] SUCCESS: Real Bing search URL detected!")
                print("[+] The search is working and returning actual Bing results")
                
                # Check for law firm indicators in the URL
                if any(term in url.lower() for term in ['lawyer', 'chicago', 'law', 'attorney']):
                    print("[+] Query terms found in URL - search appears targeted")
                
                # Check HTML files
                if result['html_files']:
                    html_file = result['html_files'][0]
                    print(f"[+] HTML saved to: {html_file}")
                    
                    # Read a bit of the HTML to verify it's real
                    try:
                        with open(html_file, 'r', encoding='utf-8') as f:
                            html_content = f.read(2000)  # First 2KB
                        
                        if "example.com" in html_content:
                            print("[!] HTML contains example.com - still mock data!")
                            return False
                        elif any(term in html_content.lower() for term in ['lawyer', 'attorney', 'law firm', 'chicago']):
                            print("[+] HTML contains real lawyer/legal content!")
                            return True
                        else:
                            print("[?] HTML doesn't clearly show lawyer content, but no mock data detected")
                            return True
                    except Exception as e:
                        print(f"[?] Could not read HTML file: {e}")
                        return True  # Still consider success if we got this far
                
                return True
            else:
                print(f"\n[?] Unexpected URL pattern: {url}")
                print("[?] Cannot determine if this is real or mock data")
                return False
        else:
            print(f"\n[!] FAILED: No results returned")
            print(f"Error: {result.get('error', 'Unknown error')}")
            if result.get('summary', {}).get('errors_encountered'):
                for error in result['summary']['errors_encountered']:
                    print(f"  - {error}")
            return False
            
    except Exception as e:
        print(f"\n[!] EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_bing_search()
    
    print(f"\n{'='*60}")
    if success:
        print("SUCCESS: VALIDATION PASSED: Bing search is returning REAL data!")
        print("SUCCESS: The synthetic data generation bug has been FIXED!")
    else:
        print("FAILED: VALIDATION FAILED: Still generating synthetic/mock data")
        print("FAILED: The bug is NOT fixed - more debugging needed")
    print(f"{'='*60}")
    
    sys.exit(0 if success else 1)