#!/usr/bin/env python3
"""
Test enhanced contact information extraction functionality.
"""

import logging
from podcast_scraper.contact_extraction import ContactExtractor, ContactValidator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_email_extraction():
    """Test enhanced email extraction with various patterns."""
    
    print("Testing Enhanced Email Extraction...")
    print("=" * 50)
    
    extractor = ContactExtractor()
    
    # Test content with various email patterns
    test_content = """
    Contact us at info@podcast.com for general inquiries.
    For booking guests, reach out to booking@showname.com
    Host email: john.doe@example.org
    
    You can also write to us: hello AT domain DOT com
    
    Business inquiries: mailto:business@podcastnetwork.io
    
    Avoid this spam@example.com and noreply@test.com
    
    Social media manager: sarah.smith@marketing.agency
    """
    
    context = "https://example.com/contact"
    
    # Extract emails
    email_results = extractor.extract_emails(test_content, context)
    
    print(f"Found {len(email_results)} validated emails:")
    for i, email_info in enumerate(email_results, 1):
        print(f"  {i}. {email_info['email']}")
        print(f"     Confidence: {email_info['confidence']:.2f}")
        print(f"     Domain: {email_info['domain']}")
        print(f"     Validation: Format valid = {email_info['validation']['format_valid']}")
        
        # Classify contact type
        contact_type = extractor.classify_contact_type(email_info['email'], email_info['context'])
        print(f"     Type: {contact_type}")
        print()

def test_phone_extraction():
    """Test phone number extraction."""
    
    print("\nTesting Phone Number Extraction...")
    print("=" * 50)
    
    extractor = ContactExtractor()
    
    test_content = """
    Call us at (555) 123-4567 for more information.
    International: +1 (800) 555-0199
    Toll-free: 1-800-PODCAST (1-800-762-2278)
    UK office: +44 20 7946 0958
    Business line: 555.987.6543
    """
    
    phone_results = extractor.extract_phone_numbers(test_content)
    
    print(f"Found {len(phone_results)} phone numbers:")
    for i, phone_info in enumerate(phone_results, 1):
        print(f"  {i}. {phone_info['phone']}")
        print(f"     Formatted: {phone_info['formatted']}")
        print(f"     Type: {phone_info['type']}")
        print(f"     Confidence: {phone_info['confidence']}")
        print()

def test_address_extraction():
    """Test address extraction."""
    
    print("\nTesting Address Extraction...")
    print("=" * 50)
    
    extractor = ContactExtractor()
    
    test_content = """
    Visit us at our studio:
    123 Main Street, Suite 456
    New York, NY 10001
    
    Mailing address:
    PO Box 789
    Los Angeles, CA 90210
    
    Our headquarters:
    456 Oak Avenue, Building B
    Austin, TX 73301-1234
    """
    
    addresses = extractor.extract_addresses(test_content)
    
    print(f"Found {len(addresses)} addresses:")
    for i, address in enumerate(addresses, 1):
        print(f"  {i}. {address}")
        print()

def test_contact_validation():
    """Test contact information validation and scoring."""
    
    print("\nTesting Contact Validation...")
    print("=" * 50)
    
    validator = ContactValidator()
    
    # Mock contact info for testing
    test_contact_info = {
        'emails': [
            {'email': 'host@podcast.com', 'confidence': 0.9},
            {'email': 'booking@podcast.com', 'confidence': 0.8}
        ],
        'phone_numbers': [
            {'phone': '(555) 123-4567', 'type': 'us_domestic'}
        ],
        'social_links': {
            'twitter': 'https://twitter.com/podcast',
            'instagram': 'https://instagram.com/podcast'
        },
        'contact_forms': ['https://podcast.com/contact'],
        'addresses': ['123 Main St, New York, NY']
    }
    
    validation_result = validator.validate_contact_info(test_contact_info)
    
    print("Validation Results:")
    print(f"  Overall Score: {validation_result['overall_score']:.2f}")
    print(f"  Email Score: {validation_result['email_score']:.2f}")
    print(f"  Completeness Score: {validation_result['completeness_score']:.2f}")
    
    print("\nQuality Indicators:")
    for indicator in validation_result['quality_indicators']:
        print(f"  + {indicator}")
    
    print("\nIssues:")
    for issue in validation_result['issues']:
        print(f"  - {issue}")
    
    print("\nRecommendations:")
    for rec in validation_result['recommendations']:
        print(f"  * {rec}")

def test_real_website():
    """Test extraction on a real website (if available)."""
    
    print("\n" + "=" * 60)
    print("Testing Real Website Integration")
    print("=" * 60)
    
    from podcast_scraper.contact_discovery import ContactPageDiscovery
    from podcast_scraper.base import PodcastData
    
    # Test with a well-known podcast
    test_podcast = PodcastData(
        podcast_name="The Tim Ferriss Show",
        rss_feed_url="https://rss.art19.com/tim-ferriss-show",
        platform_source="Test"
    )
    
    contact_discovery = ContactPageDiscovery()
    
    print(f"Testing enhanced contact extraction for: {test_podcast.podcast_name}")
    
    # Discover website
    website = contact_discovery.discover_website(test_podcast)
    print(f"Website discovered: {website}")
    
    if website:
        # Find contact pages
        contact_pages = contact_discovery.find_contact_pages(website)
        print(f"Contact pages found: {len(contact_pages)}")
        
        # Extract enhanced contact info
        if contact_pages:
            contact_info = contact_discovery.extract_contact_info(contact_pages[0])
            
            print("\nEnhanced Contact Information:")
            print(f"  Emails: {len(contact_info.get('emails', []))}")
            print(f"  Phone Numbers: {len(contact_info.get('phone_numbers', []))}")
            print(f"  Addresses: {len(contact_info.get('addresses', []))}")
            print(f"  Social Links: {len(contact_info.get('social_links', {}))}")
            print(f"  Contact Forms: {len(contact_info.get('contact_forms', []))}")
            
            # Show validation results
            if 'validation' in contact_info:
                val = contact_info['validation']
                print(f"\nValidation Score: {val.get('overall_score', 0):.2f}")
                print(f"Quality Score: {val.get('email_score', 0):.2f}")
    
    print("\n[DONE] Real website test completed!")

if __name__ == "__main__":
    try:
        test_email_extraction()
        test_phone_extraction() 
        test_address_extraction()
        test_contact_validation()
        test_real_website()
        
        print("\n" + "="*60)
        print("[SUCCESS] All enhanced contact extraction tests completed!")
        print("="*60)
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()