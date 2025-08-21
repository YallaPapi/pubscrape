#!/usr/bin/env python3
"""
Working Bing SERP retrieval with Botasaurus
This demonstrates the correct way to integrate with your VRSEN Agency Swarm
"""

from botasaurus.browser import browser, Driver
import json
import time
import re


@browser(
    headless=True,
    block_images=True,
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
)
def bing_serp_retrieval(driver, search_data):
    """
    Working Bing SERP retrieval using correct Botasaurus patterns
    This is the function your SerpFetchTool should use
    """
    try:
        query = search_data['query']
        page_num = search_data.get('page', 1)
        start_time = time.time()
        
        print(f"Searching for: {query} (page {page_num})")
        
        # Method 1: Direct Bing URL (works most of the time)
        if page_num == 1:
            bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        else:
            # For pagination, Bing uses 'first' parameter
            start = (page_num - 1) * 10 + 1
            bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&first={start}"
        
        driver.get(bing_url)
        driver.sleep(3)
        
        # Get page content
        title = driver.title
        current_url = driver.current_url
        page_html = driver.page_html()
        
        # Check for blocking
        blocked_indicators = ['blocked', 'captcha', 'access denied', 'unusual traffic']
        is_blocked = any(indicator in title.lower() for indicator in blocked_indicators)
        
        # Check for successful search
        success_indicators = ['search', 'results', query.split()[0].lower()]
        has_results = any(indicator in page_html.lower() for indicator in success_indicators)
        
        print(f"Title: {title[:100]}...")
        print(f"URL: {current_url}")
        print(f"Blocked: {is_blocked}")
        print(f"Has results: {has_results}")
        print(f"Page length: {len(page_html)}")
        
        # If blocked or no results, try fallback method
        if is_blocked or not has_results or len(page_html) < 5000:
            print("Trying fallback method...")
            
            # Fallback: Use Google to search for our query
            driver.google_get(query)
            driver.sleep(2)
            
            title = driver.title
            current_url = driver.current_url
            page_html = driver.page_html()
            has_results = len(page_html) > 1000
            
            print(f"Fallback - Title: {title[:50]}...")
            print(f"Fallback - URL: {current_url}")
            print(f"Fallback - Page length: {len(page_html)}")
        
        response_time = time.time() - start_time
        
        return {
            'success': has_results and len(page_html) > 1000,
            'html': page_html,
            'title': title,
            'url': current_url,
            'query': query,
            'page': page_num,
            'response_time_ms': int(response_time * 1000),
            'is_blocked': is_blocked,
            'content_length': len(page_html),
            'method': 'google_fallback' if (is_blocked or not has_results) else 'direct_bing',
            'user_agent_used': driver.user_agent
        }
        
    except Exception as e:
        print(f"Error in search: {e}")
        return {
            'success': False,
            'error': str(e),
            'query': query,
            'page': page_num
        }


def test_bing_serp():
    """Test the working Bing SERP function"""
    print("=" * 70)
    print("TESTING WORKING BING SERP RETRIEVAL")
    print("=" * 70)
    
    test_queries = [
        "restaurant chicago owner email",
        "plumber atlanta contact information", 
        "dentist miami phone number"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: {query} ---")
        
        search_data = {
            'query': query,
            'page': 1
        }
        
        result = bing_serp_retrieval(search_data)
        
        if result['success']:
            print(f"✓ SUCCESS!")
            print(f"  Response time: {result['response_time_ms']}ms")
            print(f"  Method: {result['method']}")
            print(f"  Content length: {result['content_length']} chars")
            print(f"  Title: {result['title'][:80]}...")
            
            # Look for business-related content in the HTML
            html_lower = result['html'].lower()
            business_terms = ['contact', 'email', 'phone', 'address', 'business']
            found_terms = [term for term in business_terms if term in html_lower]
            print(f"  Business terms found: {', '.join(found_terms)}")
            
            # Count email patterns
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_found = len(re.findall(email_pattern, result['html']))
            print(f"  Potential emails found: {emails_found}")
            
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        
        # Small delay between requests
        time.sleep(2)
    
    print("\n" + "=" * 70)
    print("BING SERP TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_bing_serp()