#!/usr/bin/env python3
"""
Test the complete Bing search -> URL extraction pipeline
Uses requests-based SerpFetchTool + fixed URL decoding HtmlParserTool
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_bing_search_tool():
    """Test the requests-based SerpFetchTool"""
    print("Testing requests-based SerpFetchTool...")
    
    try:
        from BingNavigator.tools.SerpFetchTool_requests import SerpFetchTool
        
        # Create tool instance
        tool = SerpFetchTool(
            query="lawyer New York",
            page=1,
            timeout_s=30,
            use_stealth=True
        )
        
        print(f"Query: {tool.query}")
        print(f"Page: {tool.page}")
        print(f"Timeout: {tool.timeout_s}s")
        
        # Execute the search
        print("Executing Bing search...")
        result = tool.run()
        
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            html_file = result.get('html_file')
            meta = result.get('meta', {})
            
            print("Search successful!")
            print(f"   HTML file: {html_file}")
            print(f"   Content length: {meta.get('content_length', 0)} chars")
            print(f"   Response time: {meta.get('response_time_ms', 0)}ms")
            print(f"   Method: {meta.get('method', 'unknown')}")
            print(f"   Status code: {meta.get('status_code', 'unknown')}")
            print(f"   Blocked: {meta.get('is_blocked', False)}")
            
            return html_file
        else:
            print(f"Search failed: {result.get('error_message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"Error testing SerpFetchTool: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_html_parser_tool(html_file):
    """Test the fixed HtmlParserTool with URL decoding"""
    print(f"\nTesting fixed HtmlParserTool...")
    
    if not html_file or not os.path.exists(html_file):
        print(f"HTML file not found: {html_file}")
        return None
    
    try:
        from SerpParser.tools.HtmlParserTool import HtmlParserTool
        
        # Create parser tool instance
        tool = HtmlParserTool(
            html_file=html_file,
            max_urls=30,
            filter_domains=True
        )
        
        print(f"HTML file: {html_file}")
        print(f"Max URLs: {tool.max_urls}")
        print(f"Filter domains: {tool.filter_domains}")
        
        # Execute the parsing
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
            business_urls = []
            directory_urls = []
            
            directory_domains = ['yelp.com', 'yellowpages.com', 'lawyers.com', 'avvo.com', 'findlaw.com', 'justia.com', 'legalmatch.com', 'martindale.com', 'superlawyers.com']
            
            for url_data in urls:
                domain = url_data.get('domain', '').lower()
                
                if any(dir_domain in domain for dir_domain in directory_domains):
                    directory_urls.append(url_data)
                elif domain and '.' in domain:
                    # Check if it looks like a business domain
                    if not any(common in domain for common in ['wikipedia', 'britannica', 'google', 'bing']):
                        business_urls.append(url_data)
            
            print(f"\nURL Analysis:")
            print(f"   Business URLs: {len(business_urls)}")
            print(f"   Directory URLs: {len(directory_urls)}")
            
            # Show first few URLs
            print(f"\nFirst {min(8, len(urls))} extracted URLs:")
            for i, url_data in enumerate(urls[:8]):
                url = url_data.get('url', '')
                domain = url_data.get('domain', '')
                tld = url_data.get('tld', '')
                print(f"   {i+1}. {domain} (.{tld})")
                print(f"      {url}")
            
            return urls
        else:
            print(f"Parsing failed: {result.get('error_message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"Error testing HtmlParserTool: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_pipeline_results(urls):
    """Analyze the quality of the complete pipeline results"""
    print(f"\nAnalyzing pipeline results...")
    
    if not urls:
        print("No URLs to analyze")
        return False
    
    # Filter for business-relevant URLs
    business_urls = []
    for url_data in urls:
        domain = url_data.get('domain', '').lower()
        url = url_data.get('url', '')
        
        # Skip directories and generic sites
        skip_domains = ['wikipedia', 'britannica', 'yelp', 'yellowpages', 'google', 'bing', 'facebook', 'twitter', 'linkedin']
        if not any(skip in domain for skip in skip_domains):
            if domain and '.' in domain:
                business_urls.append(url_data)
    
    print(f"Business-relevant URLs: {len(business_urls)}")
    
    if business_urls:
        print("Top business URLs found:")
        for i, url_data in enumerate(business_urls[:5]):
            domain = url_data.get('domain', '')
            url = url_data.get('url', '')
            print(f"   {i+1}. {domain}")
            print(f"      {url}")
    
    # Success criteria
    total_urls = len(urls)
    business_ratio = len(business_urls) / total_urls if total_urls > 0 else 0
    
    print(f"\nPipeline Quality Metrics:")
    print(f"   Total URLs extracted: {total_urls}")
    print(f"   Business URLs: {len(business_urls)}")
    print(f"   Business ratio: {business_ratio:.1%}")
    
    # Pipeline is successful if we get business URLs
    success = len(business_urls) > 0
    
    if success:
        print("PIPELINE SUCCESS: Found business website URLs!")
    else:
        print("PIPELINE ISSUE: No business URLs found")
    
    return success

def main():
    """Run the complete pipeline test"""
    print("Testing Complete Bing Search -> URL Extraction Pipeline")
    print("=" * 60)
    
    # Step 1: Bing Search
    html_file = test_bing_search_tool()
    if not html_file:
        print("\nPipeline failed at search step")
        return False
    
    # Step 2: URL Extraction
    urls = test_html_parser_tool(html_file)
    if not urls:
        print("\nPipeline failed at URL extraction step")
        return False
    
    # Step 3: Results Analysis
    pipeline_success = analyze_pipeline_results(urls)
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE PIPELINE TEST SUMMARY")
    print("=" * 60)
    
    print(f"1. Bing Search: {'PASS' if html_file else 'FAIL'}")
    print(f"2. URL Extraction: {'PASS' if urls else 'FAIL'}")
    print(f"3. Business URLs Found: {'PASS' if pipeline_success else 'FAIL'}")
    print(f"   Total URLs: {len(urls) if urls else 0}")
    
    if html_file and urls and pipeline_success:
        print("\nPIPELINE IS FULLY WORKING!")
        print("Fixed issues:")
        print("- Bing redirect URL decoding works correctly")
        print("- Search results are being fetched")
        print("- Business website URLs are being extracted")
        print("- The system can find actual law firm websites")
        
        # Save final results
        if urls:
            output_file = "pipeline_test_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_query': 'lawyer New York',
                    'html_file': html_file,
                    'urls_extracted': len(urls),
                    'urls': urls,
                    'timestamp': time.time(),
                    'pipeline_working': True
                }, f, indent=2)
            print(f"Results saved to: {output_file}")
        
        return True
    else:
        print("\nPIPELINE STILL HAS ISSUES")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"\nFinal result: {'SUCCESS' if success else 'FAILED'}")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest crashed: {e}")
        import traceback
        traceback.print_exc()