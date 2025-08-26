#!/usr/bin/env python3
"""
Test Bing lawyer search to debug URL discovery issues
"""

import time
import logging
from botasaurus.browser import browser, Driver
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)

@browser(
    headless=True,
    user_agent_rotation=True,
    block_images=True,
    stealth=True,
    page_load_strategy='eager'
)
def test_bing_lawyer_search(driver: Driver, query: str):
    """Test Bing search for lawyers"""
    results = []
    
    try:
        # Construct search URL
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        print(f"Searching: {search_url}")
        
        # Navigate to search page
        driver.get(search_url)
        
        # Wait for results to load
        time.sleep(3)
        
        # Take screenshot for debugging
        driver.save_screenshot("debug_bing_lawyer_search.png")
        
        # Find search result containers
        result_selectors = [
            'li.b_algo',
            '.b_algo',
            'li[class*="algo"]',
            'div.b_title',
        ]
        
        search_results = None
        for selector in result_selectors:
            try:
                search_results = driver.find_elements_by_css_selector(selector)
                if search_results:
                    print(f"Found {len(search_results)} results with selector: {selector}")
                    break
            except:
                continue
        
        if not search_results:
            print("No search results found with any selector")
            # Try to save page HTML for debugging
            with open("debug_bing_lawyer_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        
        for i, result in enumerate(search_results[:10]):
            try:
                # Extract title and URL
                title_element = None
                title_selectors = ['h2 a', 'h3 a', '.b_title a', 'a']
                for selector in title_selectors:
                    try:
                        title_element = result.find_element_by_css_selector(selector)
                        break
                    except:
                        continue
                
                if not title_element:
                    continue
                
                title = title_element.text.strip()
                url = title_element.get_attribute('href')
                
                if not url or not url.startswith('http'):
                    continue
                
                # Extract description
                description = ""
                desc_selectors = ['.b_caption p', '.b_dsc', 'p', '.snippet']
                for selector in desc_selectors:
                    try:
                        desc_element = result.find_element_by_css_selector(selector)
                        description = desc_element.text.strip()
                        break
                    except:
                        continue
                
                # Extract domain
                domain = urlparse(url).netloc.lower()
                
                # Check if it's a business (not social media or directories)
                excluded_domains = [
                    'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
                    'youtube.com', 'yelp.com', 'yellowpages.com', 'google.com',
                    'wikipedia.org', 'reddit.com', 'pinterest.com'
                ]
                
                is_business = not any(excluded in domain for excluded in excluded_domains)
                
                # Business indicators
                business_indicators = [
                    'contact', 'about', 'services', 'location', 'phone', 'email',
                    'hours', 'appointment', 'consultation', 'law', 'attorney',
                    'lawyer', 'legal', 'practice', 'firm'
                ]
                
                text_to_check = f"{title} {description}".lower()
                indicator_count = sum(1 for indicator in business_indicators 
                                    if indicator in text_to_check)
                
                is_lawyer_business = is_business and (indicator_count >= 2 or 
                                   any(word in text_to_check for word in ['lawyer', 'attorney', 'law firm', 'legal']))
                
                result_data = {
                    'title': title,
                    'url': url,
                    'description': description,
                    'domain': domain,
                    'is_business': is_lawyer_business,
                    'indicator_count': indicator_count
                }
                
                results.append(result_data)
                print(f"Result {i+1}: {title[:50]}... - Business: {is_lawyer_business}")
                
            except Exception as e:
                print(f"Error extracting result {i}: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"Error in Bing search: {e}")
        return []

if __name__ == "__main__":
    # Test the search
    query = "lawyer New York"
    print(f"Testing Bing search for: {query}")
    
    results = test_bing_lawyer_search(query)
    
    print(f"\n=== RESULTS ===")
    print(f"Total results found: {len(results)}")
    
    business_results = [r for r in results if r['is_business']]
    print(f"Business results: {len(business_results)}")
    
    if business_results:
        print(f"\nTop business results:")
        for i, result in enumerate(business_results[:5]):
            print(f"{i+1}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Domain: {result['domain']}")
            print(f"   Business indicators: {result['indicator_count']}")
            print()
    else:
        print("No business results found - this explains the lead generation issue!")
    
    # Save results for debugging
    import json
    with open("debug_bing_lawyer_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to debug_bing_lawyer_results.json")