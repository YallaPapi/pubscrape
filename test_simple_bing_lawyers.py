#!/usr/bin/env python3
"""
Simple test of Bing search for lawyers using requests
"""

import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json

def test_bing_search_lawyers(query="lawyer New York"):
    """Test Bing search for lawyers using requests"""
    print(f"Testing Bing search for: {query}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    results = []
    
    try:
        # Construct search URL
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        print(f"Search URL: {search_url}")
        
        # Make request
        response = session.get(search_url, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Bing returned status {response.status_code}")
            return []
        
        # Save HTML for debugging
        with open("debug_bing_lawyers.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("HTML saved to debug_bing_lawyers.html")
        
        # Parse results
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple selectors to find results
        result_selectors = [
            'li.b_algo',
            '.b_algo',
            'li[class*="algo"]',
            '.b_results li'
        ]
        
        search_results = None
        used_selector = None
        for selector in result_selectors:
            search_results = soup.select(selector)
            if search_results:
                used_selector = selector
                print(f"Found {len(search_results)} results with selector: {selector}")
                break
        
        if not search_results:
            print("No search results found with any selector")
            # Try to find any links that might be results
            all_links = soup.find_all('a', href=True)
            print(f"Found {len(all_links)} total links on page")
            
            # Show first few links for debugging
            for i, link in enumerate(all_links[:10]):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if href.startswith('http') and text:
                    print(f"Link {i+1}: {text[:50]} -> {href[:100]}")
            
            return []
        
        for i, result in enumerate(search_results[:10]):
            try:
                # Extract title and URL
                title_element = result.select_one('h2 a, h3 a, .b_title a, a[href^="http"]')
                if not title_element:
                    continue
                
                title = title_element.get_text(strip=True)
                url = title_element.get('href', '')
                
                if not url or not url.startswith('http'):
                    continue
                
                # Extract description
                description = ""
                desc_element = result.select_one('.b_caption p, .b_dsc, p')
                if desc_element:
                    description = desc_element.get_text(strip=True)
                
                # Extract domain
                domain = urlparse(url).netloc.lower()
                
                # Check if it's relevant for lawyers
                excluded_domains = [
                    'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
                    'youtube.com', 'yelp.com', 'yellowpages.com', 'google.com',
                    'wikipedia.org', 'reddit.com', 'pinterest.com', 'avvo.com'
                ]
                
                is_excluded = any(excluded in domain for excluded in excluded_domains)
                
                # Lawyer/legal indicators
                lawyer_indicators = [
                    'lawyer', 'attorney', 'law firm', 'legal', 'counsel', 'esquire',
                    'practice', 'law office', 'legal services', 'law group'
                ]
                
                text_to_check = f"{title} {description}".lower()
                lawyer_indicator_count = sum(1 for indicator in lawyer_indicators 
                                           if indicator in text_to_check)
                
                is_lawyer_relevant = not is_excluded and lawyer_indicator_count >= 1
                
                result_data = {
                    'title': title,
                    'url': url,
                    'description': description,
                    'domain': domain,
                    'is_lawyer_relevant': is_lawyer_relevant,
                    'lawyer_indicators': lawyer_indicator_count,
                    'is_excluded': is_excluded,
                    'position': i + 1
                }
                
                results.append(result_data)
                
                print(f"Result {i+1}: {title[:60]}...")
                print(f"  URL: {url}")
                print(f"  Domain: {domain}")
                print(f"  Lawyer relevant: {is_lawyer_relevant}")
                print(f"  Excluded: {is_excluded}")
                print(f"  Lawyer indicators: {lawyer_indicator_count}")
                print()
                
            except Exception as e:
                print(f"Error extracting result {i}: {e}")
                continue
        
    except Exception as e:
        print(f"Error in Bing search: {e}")
        import traceback
        traceback.print_exc()
    
    return results

if __name__ == "__main__":
    # Test the search
    results = test_bing_search_lawyers("lawyer New York")
    
    print(f"\n=== SUMMARY ===")
    print(f"Total results: {len(results)}")
    
    relevant_results = [r for r in results if r['is_lawyer_relevant']]
    print(f"Lawyer-relevant results: {len(relevant_results)}")
    
    if relevant_results:
        print(f"\nTop lawyer-relevant results:")
        for i, result in enumerate(relevant_results[:5]):
            print(f"{i+1}. {result['title']}")
            print(f"   URL: {result['url']}")
            print()
    
    # Save results
    with open("debug_lawyer_search_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to debug_lawyer_search_results.json")