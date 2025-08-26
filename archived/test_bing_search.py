#!/usr/bin/env python3
"""
Test script for the updated BingSearchTool to verify real browser automation works.
"""

import os
import sys
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from agents.tools.bing_search_tool import BingSearchTool

def test_real_bing_search():
    """Test the BingSearchTool with a simple query"""
    print("Testing BingSearchTool with real browser automation...")
    
    # Create the tool instance
    tool = BingSearchTool(
        query="optometrist Atlanta",
        max_pages=1,
        store_html=True
    )
    
    print(f"Query: {tool.query}")
    print(f"Max pages: {tool.max_pages}")
    print(f"Store HTML: {tool.store_html}")
    
    try:
        # Execute the search
        print("\nExecuting search...")
        result = tool.run()
        
        print(f"\nSearch Results:")
        print(f"Success: {result['success']}")
        print(f"Query: {result['query']}")
        print(f"Session ID: {result['session_id']}")
        print(f"Pages retrieved: {result['pages_retrieved']}")
        print(f"Total time: {result['total_time_seconds']:.2f}s")
        
        if result['html_files']:
            print(f"HTML files saved: {len(result['html_files'])}")
            for html_file in result['html_files']:
                print(f"  - {html_file}")
        
        if result['summary']['errors_encountered']:
            print(f"Errors: {result['summary']['errors_encountered']}")
        
        # Check if we got real results vs mock
        if result['results'] and result['results'][0]['url']:
            url = result['results'][0]['url']
            if "bing.com/search" in url and "example.com" not in url:
                print("\n✓ SUCCESS: Real Bing search executed (not mock)")
            elif "example.com" in url:
                print("\n✗ STILL MOCK: Tool is still using mock implementation")
            else:
                print(f"\n? UNKNOWN: Unexpected URL pattern: {url}")
        
        return result
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_real_bing_search()