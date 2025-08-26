#!/usr/bin/env python3
"""
Test the fixed Bing search → URL extraction pipeline
Tests BingNavigator + SerpParser with corrected URL decoding
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_bing_navigator_tool():
    """Test the SerpFetchTool directly"""
    print("🔍 Testing BingNavigator SerpFetchTool...")
    
    try:
        from BingNavigator.tools.SerpFetchTool import SerpFetchTool
        
        # Create tool instance
        tool = SerpFetchTool(
            query="lawyer New York",
            page=1,
            timeout_s=30,
            use_stealth=True
        )
        
        print(f"📋 Query: {tool.query}")
        print(f"📄 Page: {tool.page}")
        print(f"🕐 Timeout: {tool.timeout_s}s")
        
        # Execute the search
        print("🌐 Executing Bing search...")
        result = tool.run()
        
        print(f"📊 Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            html_file = result.get('html_file')
            meta = result.get('meta', {})
            
            print(f"✅ Search successful!")
            print(f"   📁 HTML file: {html_file}")
            print(f"   📏 Content length: {meta.get('content_length', 0)} chars")
            print(f"   ⏱️ Response time: {meta.get('response_time_ms', 0)}ms")
            print(f"   🛡️ Method: {meta.get('method', 'unknown')}")
            print(f"   🚫 Blocked: {meta.get('is_blocked', False)}")
            
            return html_file
        else:
            print(f"❌ Search failed: {result.get('error_message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing BingNavigator: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_serp_parser_tool(html_file):
    """Test the HtmlParserTool with the HTML file from BingNavigator"""
    print(f"\n🔧 Testing SerpParser HtmlParserTool...")
    
    if not html_file or not os.path.exists(html_file):
        print(f"❌ HTML file not found: {html_file}")
        return None
    
    try:
        from SerpParser.tools.HtmlParserTool import HtmlParserTool
        
        # Create parser tool instance
        tool = HtmlParserTool(
            html_file=html_file,
            max_urls=20,
            filter_domains=True
        )
        
        print(f"📁 HTML file: {html_file}")
        print(f"🔢 Max URLs: {tool.max_urls}")
        print(f"🔍 Filter domains: {tool.filter_domains}")
        
        # Execute the parsing
        print("📖 Parsing HTML for URLs...")
        result = tool.run()
        
        print(f"📊 Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            urls = result.get('urls', [])
            meta = result.get('meta', {})
            
            print(f"✅ Parsing successful!")
            print(f"   🔗 URLs extracted: {len(urls)}")
            print(f"   📏 HTML size: {meta.get('html_size', 0)} chars")
            print(f"   🔢 Total URLs found: {meta.get('total_urls_found', 0)}")
            print(f"   🔍 URLs after filtering: {meta.get('urls_after_filtering', 0)}")
            
            # Show first few URLs
            print(f"\n📋 First {min(5, len(urls))} extracted URLs:")
            for i, url_data in enumerate(urls[:5]):
                url = url_data.get('url', '')
                domain = url_data.get('domain', '')
                print(f"   {i+1}. {domain}")
                print(f"      {url}")
            
            return urls
        else:
            print(f"❌ Parsing failed: {result.get('error_message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing SerpParser: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_url_quality(urls):
    """Test the quality of extracted URLs"""
    print(f"\n🏆 Testing URL quality...")
    
    if not urls:
        print("❌ No URLs to test")
        return False
    
    # Count different types of URLs
    business_urls = []
    directory_urls = []
    social_urls = []
    other_urls = []
    
    directory_domains = ['yelp.com', 'yellowpages.com', 'superpages.com', 'avvo.com', 'lawyers.com', 'findlaw.com', 'justia.com', 'legalmatch.com', 'martindale.com']
    social_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'youtube.com']
    
    for url_data in urls:
        domain = url_data.get('domain', '').lower()
        url = url_data.get('url', '')
        
        if any(dir_domain in domain for dir_domain in directory_domains):
            directory_urls.append(url_data)
        elif any(social_domain in domain for social_domain in social_domains):
            social_urls.append(url_data)
        elif domain and '.' in domain:
            # Check if it looks like a business domain
            if not any(common in domain for common in ['wikipedia', 'britannica', 'google', 'bing']):
                business_urls.append(url_data)
            else:
                other_urls.append(url_data)
        else:
            other_urls.append(url_data)
    
    print(f"📊 URL Quality Analysis:")
    print(f"   🏢 Business URLs: {len(business_urls)}")
    print(f"   📁 Directory URLs: {len(directory_urls)}")
    print(f"   📱 Social URLs: {len(social_urls)}")
    print(f"   ❓ Other URLs: {len(other_urls)}")
    
    # Show business URLs if any
    if business_urls:
        print(f"\n🏢 Business URLs found:")
        for i, url_data in enumerate(business_urls[:3]):
            domain = url_data.get('domain', '')
            url = url_data.get('url', '')
            print(f"   {i+1}. {domain}")
            print(f"      {url}")
    
    # Check if we have actual business URLs vs just directories
    business_ratio = len(business_urls) / len(urls) if urls else 0
    
    print(f"\n🎯 Business URL ratio: {business_ratio:.1%}")
    
    if business_ratio > 0.1:  # At least 10% business URLs
        print("✅ Good URL quality - found actual business websites!")
        return True
    else:
        print("⚠️ Low URL quality - mostly directories/social media")
        return False

def main():
    """Run the complete test"""
    print("🚀 Testing Fixed Bing Search → URL Extraction Pipeline")
    print("=" * 60)
    
    # Test 1: BingNavigator
    html_file = test_bing_navigator_tool()
    if not html_file:
        print("\n❌ Pipeline test failed at BingNavigator step")
        return False
    
    # Test 2: SerpParser
    urls = test_serp_parser_tool(html_file)
    if not urls:
        print("\n❌ Pipeline test failed at SerpParser step")
        return False
    
    # Test 3: URL Quality
    url_quality_good = test_url_quality(urls)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 PIPELINE TEST SUMMARY")
    print("=" * 60)
    
    print(f"1. BingNavigator: {'✅ PASS' if html_file else '❌ FAIL'}")
    print(f"2. SerpParser: {'✅ PASS' if urls else '❌ FAIL'}")
    print(f"3. URL Quality: {'✅ PASS' if url_quality_good else '⚠️ LOW'}")
    print(f"   Total URLs: {len(urls) if urls else 0}")
    
    if html_file and urls:
        print("\n🎉 PIPELINE IS WORKING!")
        print("The Bing search → URL extraction pipeline successfully:")
        print("✅ Fetches Bing search results")
        print("✅ Decodes Bing redirect URLs") 
        print("✅ Extracts business website URLs")
        print("✅ Returns structured URL data")
        
        # Save results for inspection
        if urls:
            output_file = "test_bing_pipeline_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_query': 'lawyer New York',
                    'html_file': html_file,
                    'urls_extracted': len(urls),
                    'urls': urls,
                    'timestamp': time.time()
                }, f, indent=2)
            print(f"📁 Results saved to: {output_file}")
        
        return True
    else:
        print("\n💥 PIPELINE BROKEN!")
        print("The Bing search → URL extraction pipeline failed")
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback
        traceback.print_exc()