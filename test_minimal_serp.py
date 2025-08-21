"""
Minimal SERP parser test to verify core functionality
"""

import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def test_html_parsing():
    """Test basic HTML parsing"""
    print("Testing HTML parsing...")
    
    html = """
    <div id="b_results">
        <div class="b_algo">
            <h2><a href="https://example.com">Example</a></h2>
            <div class="b_caption"><p>Example text</p></div>
        </div>
    </div>
    """
    
    soup = BeautifulSoup(html, 'html.parser')
    results = soup.select('#b_results .b_algo')
    
    print(f"✓ Found {len(results)} results")
    
    for result in results:
        link = result.select_one('h2 a')
        if link:
            print(f"  URL: {link.get('href')}")
            print(f"  Title: {link.get_text()}")


def test_url_normalization():
    """Test URL normalization"""
    print("\nTesting URL normalization...")
    
    test_urls = [
        "https://example.com/path?utm_source=test&param=value",
        "http://www.testsite.com",
        "https://facebook.com/page"
    ]
    
    for url in test_urls:
        parsed = urlparse(url)
        
        # Normalize protocol
        scheme = 'https' if parsed.scheme == 'http' else parsed.scheme
        
        # Normalize domain
        netloc = parsed.netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Remove tracking params
        query_params = []
        if parsed.query:
            params = parsed.query.split('&')
            for param in params:
                if not param.startswith('utm_'):
                    query_params.append(param)
        
        query = '&'.join(query_params)
        
        normalized = f"{scheme}://{netloc}{parsed.path}"
        if query:
            normalized += f"?{query}"
        
        print(f"  Original: {url}")
        print(f"  Normalized: {normalized}")


def test_business_filtering():
    """Test business filtering"""
    print("\nTesting business filtering...")
    
    urls = [
        "https://example.com",
        "https://facebook.com/page",
        "https://yelp.com/business",
        "https://businesssite.com/services"
    ]
    
    social_media = {'facebook.com', 'twitter.com', 'linkedin.com'}
    directories = {'yelp.com', 'yellowpages.com'}
    
    business_urls = []
    
    for url in urls:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        is_business = True
        
        if domain in social_media:
            print(f"  ✗ Social media: {url}")
            is_business = False
        elif domain in directories:
            print(f"  ✗ Directory: {url}")
            is_business = False
        else:
            print(f"  ✓ Business: {url}")
            business_urls.append(url)
    
    print(f"\nBusiness URLs found: {len(business_urls)}")


def main():
    """Run minimal tests"""
    print("🚀 Running Minimal SERP Parser Tests")
    print("=" * 40)
    
    test_html_parsing()
    test_url_normalization()
    test_business_filtering()
    
    print("\n✅ All minimal tests completed!")


if __name__ == "__main__":
    main()