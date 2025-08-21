#!/usr/bin/env python3
"""
Test the fixed SerpFetchTool with proper Botasaurus integration
"""

import sys
import os
sys.path.append('BingNavigator/tools')

from SerpFetchTool_fixed import SerpFetchTool

def test_serp_fetch_tool():
    """Test the fixed SerpFetchTool"""
    print("=" * 60)
    print("TESTING FIXED SERPFETCHTOOL")
    print("=" * 60)
    
    # Create the tool
    tool = SerpFetchTool(
        query="restaurant chicago owner email",
        page=1,
        timeout_s=30,
        use_stealth=True
    )
    
    print(f"Query: {tool.query}")
    print(f"Page: {tool.page}")
    print(f"Stealth: {tool.use_stealth}")
    print()
    
    # Execute the search
    print("Executing search...")
    result = tool.run()
    
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        meta = result['meta']
        print(f"✓ Success! Retrieved {meta['content_length']} characters")
        print(f"  Response time: {meta['response_time_ms']}ms")
        print(f"  Method: {meta['method']}")
        print(f"  Bing title: {meta['bing_title'][:100]}...")
        print(f"  Session ID: {meta['session_id']}")
        print(f"  User agent: {meta['user_agent'][:50]}...")
        
        # Check if HTML contains search results
        html = result.get('html', '')
        has_search_results = any(term in html.lower() for term in ['restaurant', 'search', 'results'])
        print(f"  Contains search terms: {has_search_results}")
        
    else:
        print(f"❌ Error: {result['error_message']}")
        if 'meta' in result:
            print(f"  Error type: {result['error_type']}")
            if 'recommendation' in result['meta']:
                print(f"  Recommendation: {result['meta']['recommendation']}")
    
    print("\n" + "=" * 60)
    return result['status'] == 'success'

if __name__ == "__main__":
    success = test_serp_fetch_tool()
    print(f"Test {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)