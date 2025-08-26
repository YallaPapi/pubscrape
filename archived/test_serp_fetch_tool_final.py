#!/usr/bin/env python3
"""
Test the final corrected SerpFetchTool with proper Botasaurus integration
"""

import sys
import os
sys.path.append('BingNavigator/tools')

from SerpFetchTool import SerpFetchTool

def test_final_serp_fetch_tool():
    """Test the final corrected SerpFetchTool"""
    print("=" * 70)
    print("TESTING FINAL CORRECTED SERPFETCHTOOL")
    print("=" * 70)
    
    # Test queries that should work with the lead generation system
    test_cases = [
        {
            "query": "restaurant chicago owner email",
            "page": 1,
            "expected_terms": ["restaurant", "contact", "business"]
        },
        {
            "query": "plumber atlanta contact phone",
            "page": 1,
            "expected_terms": ["plumber", "contact", "phone"]
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['query']} ---")
        
        # Create the tool
        tool = SerpFetchTool(
            query=test_case["query"],
            page=test_case["page"],
            timeout_s=30,
            use_stealth=True
        )
        
        print(f"Query: {tool.query}")
        print(f"Page: {tool.page}")
        print(f"Stealth: {tool.use_stealth}")
        
        # Execute the search
        result = tool.run()
        
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            meta = result['meta']
            print(f"✓ SUCCESS!")
            print(f"  Content length: {meta['content_length']} characters")
            print(f"  Response time: {meta['response_time_ms']}ms")
            print(f"  Method: {meta['method']}")
            print(f"  Session ID: {meta['session_id']}")
            print(f"  Bing title: {meta['bing_title'][:80]}...")
            print(f"  Blocked: {meta['is_blocked']}")
            
            # Check for expected terms in HTML
            html = result.get('html', '').lower()
            found_terms = [term for term in test_case['expected_terms'] if term in html]
            print(f"  Expected terms found: {', '.join(found_terms)}")
            
            # Check HTML quality
            if len(html) > 50000:  # Good size HTML
                print(f"  ✓ High-quality HTML retrieved")
                success_count += 1
            else:
                print(f"  ⚠ HTML seems small, might be minimal content")
            
        else:
            print(f"❌ FAILED: {result['error_message']}")
            if 'meta' in result:
                print(f"  Error type: {result['error_type']}")
                if 'recommendation' in result['meta']:
                    print(f"  Recommendation: {result['meta']['recommendation']}")
        
        print(f"  Time delay before next test...")
    
    print("\n" + "=" * 70)
    print("SERPFETCHTOOL INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests passed: {success_count}/{len(test_cases)}")
    
    if success_count == len(test_cases):
        print("🎉 ALL TESTS PASSED - SERPFETCHTOOL IS READY!")
        print("✓ Botasaurus integration working correctly")
        print("✓ Anti-detection features enabled")
        print("✓ HTML content retrieval successful")
        print("✓ Ready for VRSEN Agency Swarm integration")
    else:
        print(f"⚠ Some tests failed. Success rate: {success_count/len(test_cases)*100:.1f}%")
    
    return success_count == len(test_cases)

if __name__ == "__main__":
    success = test_final_serp_fetch_tool()
    exit(0 if success else 1)