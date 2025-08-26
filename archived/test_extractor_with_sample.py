#!/usr/bin/env python3
"""
Test the fixed email extractor with a sample HTML page that contains contact info
"""

import os
from fixed_email_extractor import WorkingEmailExtractor, ContactInfo
from bs4 import BeautifulSoup


def test_with_sample_html():
    """Test extractor with our sample HTML containing contact info"""
    print("Testing Email Extractor with Sample Contact Page")
    print("=" * 55)
    
    # Read the sample HTML file
    html_file = "test_contact_page.html"
    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found")
        return False
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Create extractor and manually parse the HTML (simulate website fetch)
    extractor = WorkingEmailExtractor()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Create a ContactInfo object to test extraction methods
    contact_info = ContactInfo(url="file://test_contact_page.html")
    
    # Test business name extraction
    business_name = extractor.extract_business_name(soup, "file://test_contact_page.html")
    print(f"Business Name: {business_name}")
    
    # Test email extraction
    emails = extractor.extract_emails(soup, html_content, "file://test_contact_page.html")
    print(f"\nEmails Found: {len(emails)}")
    for i, email in enumerate(emails, 1):
        print(f"  {i}. {email['email']} (confidence: {email['confidence']:.2f}, source: {email['source']})")
        print(f"     Context: {email['context'][:60]}...")
    
    # Test phone extraction
    phones = extractor.extract_phone_numbers(html_content)
    print(f"\nPhones Found: {len(phones)}")
    for i, phone in enumerate(phones, 1):
        print(f"  {i}. {phone['phone']} (confidence: {phone['confidence']:.2f}, type: {phone['type']})")
        print(f"     Context: {phone['context'][:60]}...")
    
    # Test name extraction
    names = extractor.extract_names(soup, html_content)
    print(f"\nNames Found: {len(names)}")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name['name']} (confidence: {name['confidence']:.2f}, context: {name['context']})")
    
    # Test address extraction
    addresses = extractor.extract_addresses(html_content)
    print(f"\nAddresses Found: {len(addresses)}")
    for i, address in enumerate(addresses, 1):
        print(f"  {i}. {address}")
    
    # Test social profile extraction
    social_profiles = extractor.extract_social_profiles(soup)
    print(f"\nSocial Profiles Found: {len(social_profiles)}")
    for i, profile in enumerate(social_profiles, 1):
        print(f"  {i}. {profile}")
    
    # Create complete contact info object for scoring
    contact_info.business_name = business_name
    contact_info.emails = emails
    contact_info.phones = phones
    contact_info.names = names
    contact_info.addresses = addresses
    contact_info.social_profiles = social_profiles
    
    # Calculate scores
    contact_info.lead_score = extractor.calculate_lead_score(contact_info)
    contact_info.extraction_confidence = extractor.calculate_confidence(contact_info)
    contact_info.is_actionable = extractor.is_actionable_lead(contact_info)
    
    print(f"\n{'='*55}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*55}")
    print(f"Business Name: {contact_info.business_name}")
    print(f"Total Emails: {len(contact_info.emails)}")
    print(f"Total Phones: {len(contact_info.phones)}")
    print(f"Total Names: {len(contact_info.names)}")
    print(f"Total Addresses: {len(contact_info.addresses)}")
    print(f"Total Social: {len(contact_info.social_profiles)}")
    print(f"Lead Score: {contact_info.lead_score:.2f}")
    print(f"Extraction Confidence: {contact_info.extraction_confidence:.2f}")
    print(f"Is Actionable Lead: {contact_info.is_actionable}")
    
    # Success criteria
    success = (
        len(contact_info.emails) >= 3 and
        len(contact_info.phones) >= 1 and
        len(contact_info.names) >= 2 and
        contact_info.lead_score >= 0.5 and
        contact_info.is_actionable
    )
    
    print(f"\n{'='*55}")
    if success:
        print("SUCCESS: Email extractor is working correctly!")
        print("- Extracted multiple emails with high confidence")
        print("- Extracted phone numbers with context")
        print("- Extracted person names from staff sections")
        print("- Generated actionable lead with good score")
    else:
        print("ISSUES FOUND:")
        if len(contact_info.emails) < 3:
            print(f"- Expected ≥3 emails, got {len(contact_info.emails)}")
        if len(contact_info.phones) < 1:
            print(f"- Expected ≥1 phone, got {len(contact_info.phones)}")
        if len(contact_info.names) < 2:
            print(f"- Expected ≥2 names, got {len(contact_info.names)}")
        if contact_info.lead_score < 0.5:
            print(f"- Expected lead score ≥0.5, got {contact_info.lead_score:.2f}")
        if not contact_info.is_actionable:
            print("- Lead is not marked as actionable")
    
    return success


def test_email_patterns():
    """Test email pattern matching with various formats"""
    print("\nTesting Email Pattern Recognition")
    print("=" * 35)
    
    extractor = WorkingEmailExtractor()
    
    test_texts = [
        "Contact us at info@example.com for more information",
        "Email: john.smith@company.org or call us",
        "Send emails to support [at] service [dot] net",
        "Reach out: contact(at)business(dot)com",
        "Our CEO: ceo AT company DOT com",
        "Invalid: not-an-email-address",
        "Multiple: first@test.com and second@demo.org",
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        
        # Test with BeautifulSoup parsing
        soup = BeautifulSoup(f"<p>{text}</p>", 'html.parser')
        emails = extractor.extract_emails(soup, text, "test://")
        
        print(f"  Found {len(emails)} email(s):")
        for email in emails:
            print(f"    - {email['email']} (confidence: {email['confidence']:.2f})")
    
    print("\nEmail Pattern Test Complete")


if __name__ == "__main__":
    print("COMPREHENSIVE EMAIL EXTRACTOR TESTING")
    print("=" * 60)
    
    # Test 1: Sample HTML with rich contact info
    success = test_with_sample_html()
    
    # Test 2: Email pattern recognition
    test_email_patterns()
    
    print("\n" + "=" * 60)
    if success:
        print("OVERALL RESULT: Email extractor is WORKING!")
        print("Ready to integrate into the main pipeline.")
    else:
        print("OVERALL RESULT: Email extractor needs fixes.")
        print("Review the issues above before integration.")
    print("=" * 60)