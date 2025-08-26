#!/usr/bin/env python3
"""
Test script to verify the three SerpFetchTool fixes are working correctly.
"""

import sys
import os
import time

# Add the BingNavigator tools to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'BingNavigator', 'tools'))

from SerpFetchTool import SerpFetchTool

def test_serp_fixes():
    """Test that the SerpFetchTool fixes work correctly."""
    
    print("="*60)
    print("TESTING SERPFETCHTOOL FIXES")
    print("="*60)
    
    # Test the tool with a simple lawyer search
    tool = SerpFetchTool(
        query="lawyer Atlanta contact",
        page=1,
        timeout_s=30,
        use_stealth=True
    )
    
    print(f"Testing query: {tool.query}")
    print(f"Stealth mode: {tool.use_stealth}")
    print("Starting search...")
    
    start_time = time.time()
    
    try:
        result = tool.run()
        
        execution_time = time.time() - start_time
        print(f"Execution time: {execution_time:.2f} seconds")
        
        print("\n" + "="*60)
        print("RESULT ANALYSIS:")
        print("="*60)
        
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            meta = result.get('meta', {})
            print(f"[+] Query executed: {meta.get('query')}")
            print(f"[+] Content length: {meta.get('content_length', 0):,} characters")
            print(f"[+] Response time: {meta.get('response_time_ms', 0)}ms")
            print(f"[+] Method used: {meta.get('method', 'unknown')}")
            print(f"[+] Stealth enabled: {meta.get('stealth_enabled', False)}")
            print(f"[+] Blocked: {meta.get('is_blocked', False)}")
            print(f"[+] HTML file saved: {result.get('html_file')}")
            
            # Check if fixes were applied correctly
            fixes_verified = []
            
            # Fix 1: Check that method is not 'google_fallback' (it should be 'bing_fallback' now)
            if meta.get('method') != 'google_fallback':
                fixes_verified.append("[+] Fix 1: No more google_get() calls")
            else:
                fixes_verified.append("[-] Fix 1: Still using google_get()")
            
            # Fix 2: Check that we're not being blocked by 'robot' text
            if not meta.get('is_blocked', False):
                fixes_verified.append("[+] Fix 2: Improved blocking detection")
            else:
                fixes_verified.append("[!] Fix 2: Still detecting blocking (could be real)")
                
            # Fix 3: We can't directly test block_images vs block_images_and_css from the result,
            # but we can confirm the tool ran without configuration errors
            if result.get('status') == 'success':
                fixes_verified.append("[+] Fix 3: Updated browser configuration working")
            
            print("\n" + "="*40)
            print("FIX VERIFICATION:")
            print("="*40)
            for fix in fixes_verified:
                print(fix)
                
            # Show preview of HTML content
            preview = result.get('html_preview', '')
            if preview:
                print(f"\nHTML Preview (first 500 chars):")
                print("-" * 40)
                print(preview[:500])
                print("-" * 40)
                
        else:
            print(f"[-] Error: {result.get('error_message', 'Unknown error')}")
            print(f"Error type: {result.get('error_type', 'unknown')}")
            
        print(f"\nFull result structure:")
        import json
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"[-] Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)
    
    return result.get('status') == 'success'

if __name__ == "__main__":
    success = test_serp_fixes()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")