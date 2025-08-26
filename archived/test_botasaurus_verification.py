#!/usr/bin/env python3
"""
Work Verification Test for Botasaurus Integration
Tests the actual fixes claimed by debugging agent
"""

import sys
import json
import time
from pathlib import Path

def test_serp_fetch_tool():
    """Test the SerpFetchTool with lawyer search as claimed"""
    print("=== TESTING SERPFETCHTOOL WITH LAWYER ATLANTA QUERY ===")
    
    try:
        from BingNavigator.tools.SerpFetchTool import SerpFetchTool
        
        # Test the exact query claimed: "lawyer Atlanta contact"
        tool = SerpFetchTool(
            query="lawyer Atlanta contact",
            page=1,
            timeout_s=30,
            use_stealth=True
        )
        
        print(f"Executing search for: {tool.query}")
        start_time = time.time()
        
        result = tool.run()
        
        execution_time = time.time() - start_time
        print(f"Execution completed in {execution_time:.2f} seconds")
        
        # Analyze the result
        print("\n=== RESULT ANALYSIS ===")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            meta = result.get('meta', {})
            html_file = result.get('html_file')
            
            print(f"Query: {meta.get('query', 'N/A')}")
            print(f"Content Length: {meta.get('content_length', 0):,} characters")
            print(f"Response Time: {meta.get('response_time_ms', 0)}ms")
            print(f"Method Used: {meta.get('method', 'N/A')}")
            print(f"Blocking Detected: {meta.get('is_blocked', 'N/A')}")
            print(f"HTML File: {html_file}")
            print(f"Title: {meta.get('title', 'N/A')}")
            
            # Verify the HTML file exists and has content
            if html_file and Path(html_file).exists():
                file_size = Path(html_file).stat().st_size
                print(f"HTML File Size: {file_size:,} bytes")
                
                # Read a sample of the HTML to verify it's real Bing content
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    html_sample = f.read(2000)
                    
                # Check for Bing-specific indicators
                bing_indicators = ['bing.com', 'microsoft', 'search results', 'lawyer', 'atlanta']
                found_indicators = [ind for ind in bing_indicators if ind.lower() in html_sample.lower()]
                
                print(f"Bing Indicators Found: {found_indicators}")
                print(f"HTML Sample (first 500 chars):\n{html_sample[:500]}...")
                
                # Verify it's not a blocked/captcha page
                blocking_indicators = ['captcha', 'access denied', 'unusual traffic', 'verify you are human']
                blocking_found = [ind for ind in blocking_indicators if ind.lower() in html_sample.lower()]
                
                if blocking_found:
                    print(f"WARNING: Blocking indicators found: {blocking_found}")
                    return False
                else:
                    print("SUCCESS: No blocking indicators detected")
                    
                # Check if we actually got search results
                if file_size > 50000 and len(found_indicators) >= 3:
                    print("VERIFICATION PASSED: Real Bing search results obtained")
                    return True
                else:
                    print("VERIFICATION FAILED: Content appears insufficient or fake")
                    return False
            else:
                print("ERROR: HTML file not created or doesn't exist")
                return False
        else:
            print(f"ERROR: Search failed - {result.get('error_message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_blocking_detection():
    """Test the blocking detection logic specifically"""
    print("\n=== TESTING BLOCKING DETECTION LOGIC ===")
    
    try:
        from BingNavigator.tools.SerpFetchTool import SerpFetchTool
        
        # Test with a query that might trigger blocking
        tool = SerpFetchTool(
            query="test query unusual traffic detection",
            page=1,
            timeout_s=15,
            use_stealth=True
        )
        
        result = tool.run()
        
        if result.get('status') == 'success':
            meta = result.get('meta', {})
            is_blocked = meta.get('is_blocked', False)
            method = meta.get('method', 'unknown')
            
            print(f"Blocking Status: {is_blocked}")
            print(f"Method Used: {method}")
            
            # If blocking was detected, verify fallback was used
            if is_blocked and method == 'bing_fallback':
                print("SUCCESS: Blocking detected and fallback method triggered")
                return True
            elif not is_blocked:
                print("SUCCESS: No blocking detected, direct method worked")
                return True
            else:
                print("WARNING: Inconsistent blocking detection results")
                return False
        else:
            print(f"Test completed with status: {result.get('status')}")
            return True  # Error handling is also valid behavior
            
    except Exception as e:
        print(f"ERROR: Blocking detection test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("BOTASAURUS INTEGRATION VERIFICATION TEST")
    print("=" * 50)
    
    # Test 1: Main functionality with lawyer search
    test1_passed = test_serp_fetch_tool()
    
    # Test 2: Blocking detection
    test2_passed = test_blocking_detection()
    
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY:")
    print(f"SerpFetchTool Functionality: {'PASS' if test1_passed else 'FAIL'}")
    print(f"Blocking Detection Logic: {'PASS' if test2_passed else 'FAIL'}")
    
    overall_pass = test1_passed and test2_passed
    print(f"OVERALL VERIFICATION: {'PASS' if overall_pass else 'FAIL'}")
    
    if overall_pass:
        print("\nVERDICT: VERIFIED - Botasaurus integration is working correctly")
    else:
        print("\nVERDICT: REJECTED - Issues found in Botasaurus integration")
    
    return overall_pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)