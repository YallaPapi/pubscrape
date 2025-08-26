#!/usr/bin/env python3
"""
Simplified pipeline test that bypasses complex anti-detection for initial testing
"""
import sys
import os
import requests
import time
sys.path.append('src')

def test_manual_bing_search():
    """Test direct requests to Bing to get sample SERP content"""
    print("=== TESTING MANUAL BING SEARCH ===")
    
    # Create simple search using requests
    query = "restaurant New York contact email"
    print(f"Searching for: {query}")
    
    try:
        # Direct request to Bing (this may get blocked, but let's try)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create search URL
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        print(f"URL: {search_url}")
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✓ SUCCESS: Got {len(response.text)} chars of HTML")
            
            # Save for testing parser
            os.makedirs('out', exist_ok=True)
            with open('out/sample_bing_result.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return response.text
        else:
            print(f"✗ FAILED: Status code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ EXCEPTION: {str(e)}")
        return None

def test_serp_parser_with_sample():
    """Test SERP parser with sample HTML"""
    print("\\n=== TESTING SERP PARSER WITH SAMPLE HTML ===")
    
    # Check if we have sample HTML
    sample_file = 'out/sample_bing_result.html'
    if not os.path.exists(sample_file):
        print("✗ No sample HTML file found")
        return []
    
    try:
        from agents.tools.serp_parse_tool import SerpParseTool
        print("✓ Imported SerpParseTool successfully")
        
        parser = SerpParseTool()
        print("✓ Created SerpParseTool instance")
        
        # Read sample HTML
        with open(sample_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"Parsing sample HTML ({len(html_content)} chars)...")
        
        # Parse the HTML
        result = parser.run(
            html_content=html_content,
            query="restaurant New York contact email",
            position_offset=0
        )
        
        urls = result.get('results', [])
        print(f"✓ SUCCESS: Found {len(urls)} URLs")
        
        # Show first few URLs
        for i, url_data in enumerate(urls[:5]):
            print(f"  {i+1}. {url_data.get('url', 'No URL')[:80]}...")
        
        return urls
        
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_domain_classifier():
    """Test domain classification with sample URLs"""
    print("\\n=== TESTING DOMAIN CLASSIFIER ===")
    
    # Sample URLs for testing
    sample_urls = [
        "https://www.restaurantnewyork.com",
        "https://www.nybistro.com/contact",
        "https://yelp.com/biz/restaurant-new-york",  # Should be filtered out
        "https://www.facebook.com/restaurant",      # Should be filtered out
        "https://www.localdiner.com/about",
        "https://www.finedining.net/contact-us"
    ]
    
    try:
        from agents.domain_classifier_agent import DomainClassifier
        print("✓ Imported DomainClassifier successfully")
        
        classifier = DomainClassifier()
        print("✓ Created DomainClassifier instance")
        
        # Process URLs
        business_domains = []
        for url in sample_urls:
            print(f"\\nProcessing: {url}")
            
            # Extract domain
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            
            # Add to classifier
            result = classifier.add_domain(domain, context={'source_url': url})
            
            if result:
                print(f"  ✓ Added as business domain")
                business_domains.append(domain)
            else:
                print(f"  ✗ Filtered out (non-business)")
        
        print(f"\\n✓ SUCCESS: {len(business_domains)} business domains identified")
        
        # Get statistics
        stats = classifier.get_statistics()
        print(f"Total domains processed: {stats.get('total_domains', 0)}")
        print(f"Business domains: {stats.get('business_domains', 0)}")
        
        return business_domains
        
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_email_extraction():
    """Test email extraction with sample content"""
    print("\\n=== TESTING EMAIL EXTRACTION ===")
    
    # Sample HTML content with emails
    sample_content = '''
    <div class="contact-info">
        <h2>Contact Us</h2>
        <p>For reservations, please contact us at <a href="mailto:reservations@nybistro.com">reservations@nybistro.com</a></p>
        <p>General inquiries: info@nybistro.com</p>
        <p>Owner: john.smith@nybistro.com</p>
        <p>Manager: sarah.johnson@nybistro.com</p>
        <div class="footer">
            <p>© 2024 NY Bistro | Email: contact@nybistro.com</p>
        </div>
    </div>
    '''
    
    try:
        from agents.tools.email_extraction_tool import EmailExtractionTool
        print("✓ Imported EmailExtractionTool successfully")
        
        extractor = EmailExtractionTool()
        print("✓ Created EmailExtractionTool instance")
        
        # Extract emails
        result = extractor.run(
            html_content=sample_content,
            url="https://www.nybistro.com/contact",
            domain="nybistro.com"
        )
        
        emails = result.get('emails', [])
        print(f"✓ SUCCESS: Found {len(emails)} emails")
        
        # Show extracted emails
        for i, email_data in enumerate(emails):
            email = email_data.get('email', 'No email')
            confidence = email_data.get('confidence', 0)
            quality = email_data.get('quality', 'UNKNOWN')
            print(f"  {i+1}. {email} (confidence: {confidence:.2f}, quality: {quality})")
        
        return emails
        
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Run simplified pipeline test"""
    print("🚀 STARTING SIMPLIFIED PIPELINE TEST")
    print("=" * 60)
    
    # Step 1: Get sample SERP content
    html_content = test_manual_bing_search()
    
    # Step 2: Test SERP parsing (if we got HTML)
    if html_content:
        urls = test_serp_parser_with_sample()
    else:
        urls = []
        print("\\nSkipping SERP parsing test - no HTML content")
    
    # Step 3: Test domain classification
    domains = test_domain_classifier()
    
    # Step 4: Test email extraction
    emails = test_email_extraction()
    
    # Summary
    print("\\n" + "=" * 60)
    print("🎯 SIMPLIFIED TEST SUMMARY")
    print(f"HTML content retrieved: {'Yes' if html_content else 'No'}")
    print(f"URLs extracted: {len(urls) if urls else 0}")
    print(f"Business domains: {len(domains) if domains else 0}")
    print(f"Emails extracted: {len(emails) if emails else 0}")
    
    # Determine if we can proceed with full pipeline
    working_components = sum([
        1 if html_content else 0,
        1 if urls else 0,
        1 if domains else 0,
        1 if emails else 0
    ])
    
    print(f"\\nWorking components: {working_components}/4")
    
    if working_components >= 3:
        print("\\n✓ PIPELINE CORE IS WORKING! Ready to integrate full system")
        return True
    elif working_components >= 2:
        print("\\n⚠️ PIPELINE PARTIALLY WORKING - needs fixes but promising")
        return True
    else:
        print("\\n✗ PIPELINE NEEDS MAJOR FIXES")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)