#!/usr/bin/env python3
"""
Test the URL decoding fix directly using saved HTML
Tests that the HtmlParserTool can properly decode Bing redirect URLs
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_url_decoding_with_saved_html():
    """Test URL decoding using the previously saved HTML file"""
    print("Testing URL decoding fix with saved HTML...")
    
    # Use the HTML file we saved earlier
    html_file = "debug_bing_lawyers.html"
    
    if not os.path.exists(html_file):
        print(f"HTML file not found: {html_file}")
        print("Run test_simple_bing_lawyers.py first to generate the HTML")
        return False
    
    try:
        from SerpParser.tools.HtmlParserTool import HtmlParserTool
        
        print(f"Using HTML file: {html_file}")
        
        # Create parser tool instance
        tool = HtmlParserTool(
            html_file=html_file,
            max_urls=50,  # Get more URLs to test
            filter_domains=False  # Don't filter to see all URLs
        )
        
        print("Parsing HTML for URLs...")
        result = tool.run()
        
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            urls = result.get('urls', [])
            meta = result.get('meta', {})
            
            print("Parsing successful!")
            print(f"   URLs extracted: {len(urls)}")
            print(f"   HTML size: {meta.get('html_size', 0)} chars")
            print(f"   Total URLs found: {meta.get('total_urls_found', 0)}")
            print(f"   URLs after filtering: {meta.get('urls_after_filtering', 0)}")
            
            # Analyze URL types
            decoded_urls = []
            bing_redirect_urls = []
            other_urls = []
            
            for url_data in urls:
                url = url_data.get('url', '')
                domain = url_data.get('domain', '')
                
                if 'bing.com' in domain:
                    bing_redirect_urls.append(url_data)
                elif domain and '.' in domain and domain != 'bing.com':
                    decoded_urls.append(url_data)
                else:
                    other_urls.append(url_data)
            
            print(f"\nURL Analysis:")
            print(f"   Properly decoded URLs: {len(decoded_urls)}")
            print(f"   Still Bing redirects: {len(bing_redirect_urls)}")
            print(f"   Other URLs: {len(other_urls)}")
            
            # Show decoded URLs
            if decoded_urls:
                print(f"\nProperly decoded URLs (first 10):")
                for i, url_data in enumerate(decoded_urls[:10]):
                    url = url_data.get('url', '')
                    domain = url_data.get('domain', '')
                    print(f"   {i+1}. {domain}")
                    print(f"      {url}")
            
            # Show any remaining Bing redirects (these indicate decode failures)
            if bing_redirect_urls:
                print(f"\nStill Bing redirects (decode failed):")
                for i, url_data in enumerate(bing_redirect_urls[:3]):
                    url = url_data.get('url', '')
                    print(f"   {i+1}. {url[:100]}...")
            
            # Test success criteria
            decode_success_rate = len(decoded_urls) / len(urls) if urls else 0
            print(f"\nDecode success rate: {decode_success_rate:.1%}")
            
            if decode_success_rate > 0.8:  # 80% success rate
                print("SUCCESS: URL decoding fix is working!")
                return True
            else:
                print("ISSUE: Many URLs still not decoded properly")
                return False
        else:
            print(f"Parsing failed: {result.get('error_message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Error testing URL decoding: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the URL decoding test"""
    print("Testing Fixed URL Decoding in SerpParser")
    print("=" * 50)
    
    success = test_url_decoding_with_saved_html()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if success:
        print("PASS: URL decoding fix is working correctly!")
        print("- Bing redirect URLs are being properly decoded")
        print("- Business website URLs are being extracted")
        print("- The SerpParser pipeline is functional")
    else:
        print("FAIL: URL decoding fix needs more work")
        print("- URLs are still showing as Bing redirects")
        print("- Need to debug the decoding logic further")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Test crashed: {e}")
        import traceback
        traceback.print_exc()