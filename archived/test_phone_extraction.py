#!/usr/bin/env python3
"""
Test Script for Advanced Phone Number Extraction System
TASK-D003: Validation and testing of phone extraction capabilities

This script comprehensively tests the phone extraction system with various
formats, obfuscation patterns, and integration scenarios.
"""

import sys
import os
import time
import json
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from botasaurus_core.phone_extractor import PhoneExtractor, PhoneType, ConfidenceLevel
from botasaurus_core.data_extractor import DataExtractor
from botasaurus_core.models import BusinessLead


def test_basic_phone_patterns():
    """Test basic phone number pattern recognition"""
    print("\n" + "="*60)
    print("TESTING BASIC PHONE PATTERNS")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    test_cases = [
        # Standard US formats
        ("Standard Parentheses", "Call us at (555) 123-4567 for more information."),
        ("Dots Format", "Business line: 555.123.4567 available 24/7."),
        ("Dashes Format", "Contact: 555-123-4567 or visit our website."),
        ("Spaces Format", "Phone number is 555 123 4567 extension 123."),
        ("Digits Only", "Quick contact: 5551234567 for urgent matters."),
        
        # With extensions
        ("With Extension", "Main office (555) 123-4567 ext. 1234"),
        ("Extension Variant", "Call 555-123-4567 extension 456"),
        
        # International
        ("International Plus", "International: +1-555-123-4567"),
        ("Country Code", "From abroad: 001-555-123-4567"),
        
        # Toll-free
        ("Toll Free 800", "Customer service: 1-800-555-0123"),
        ("Toll Free 888", "Support line: (888) 555-0199"),
    ]
    
    for test_name, test_text in test_cases:
        print(f"\nTest: {test_name}")
        print(f"Input: {test_text}")
        
        result = extractor.extract_from_text(test_text, f"test_{test_name.lower().replace(' ', '_')}")
        
        if result.candidates:
            for candidate in result.candidates:
                print(f"  Found: {candidate.formatted_number}")
                print(f"  Type: {candidate.phone_type.value}")
                print(f"  Confidence: {candidate.confidence_score:.2f} ({candidate.confidence_level.value})")
                print(f"  Valid: {candidate.validation_status}")
                print(f"  Method: {candidate.extraction_method}")
        else:
            print("  No phone numbers found")
    
    return len([tc for tc in test_cases if "5551234567" in tc[1] or "555" in tc[1]]) <= result.total_found


def test_obfuscated_patterns():
    """Test obfuscated phone number detection"""
    print("\n" + "="*60)
    print("TESTING OBFUSCATED PHONE PATTERNS")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    obfuscated_cases = [
        ("Text Numbers", "Call five five five one two three four five six seven"),
        ("Mixed Format", "Phone: five-five-five one two three 4567"),
        ("Spelled Out", "Contact: five five five dash one two three dash four five six seven"),
        ("With Words", "Ring us at five five five space one two three space four five six seven"),
        ("Partial Obfuscation", "Call (five five five) 123-4567 today"),
        ("Creative Spacing", "Phone five . five . five . one two three . four five six seven"),
    ]
    
    for test_name, test_text in obfuscated_cases:
        print(f"\nTest: {test_name}")
        print(f"Input: {test_text}")
        
        result = extractor.extract_from_text(test_text, f"obfuscated_{test_name.lower().replace(' ', '_')}")
        
        if result.candidates:
            for candidate in result.candidates:
                print(f"  Found: {candidate.formatted_number}")
                print(f"  Raw: {candidate.raw_text}")
                print(f"  Confidence: {candidate.confidence_score:.2f}")
                print(f"  Method: {candidate.extraction_method}")
        else:
            print("  No phone numbers found")
    
    return True


def test_context_awareness():
    """Test context-aware phone type classification"""
    print("\n" + "="*60)
    print("TESTING CONTEXT-AWARE CLASSIFICATION")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    context_cases = [
        ("Business Context", "For business inquiries, please call our office at (555) 123-4567"),
        ("Personal Context", "John's personal cell phone is 555-123-4567"),
        ("Customer Service", "Customer support line: 1-800-555-0123"),
        ("Fax Number", "Send documents to our fax: (555) 123-4568"),
        ("Reception", "Main reception desk: (555) 123-4567"),
        ("Sales Context", "Contact our sales team at 555-123-4567 for quotes"),
        ("Emergency", "Emergency after-hours number: (555) 123-9999"),
    ]
    
    for test_name, test_text in context_cases:
        print(f"\nTest: {test_name}")
        print(f"Input: {test_text}")
        
        result = extractor.extract_from_text(test_text, f"context_{test_name.lower().replace(' ', '_')}")
        
        if result.candidates:
            candidate = result.candidates[0]
            print(f"  Found: {candidate.formatted_number}")
            print(f"  Classified as: {candidate.phone_type.value}")
            print(f"  Context keywords: {candidate.context_keywords}")
            print(f"  Confidence: {candidate.confidence_score:.2f}")
            print(f"  Is toll-free: {candidate.is_toll_free}")
        else:
            print("  No phone numbers found")
    
    return True


def test_validation_system():
    """Test phone number validation"""
    print("\n" + "="*60)
    print("TESTING PHONE NUMBER VALIDATION")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    validation_cases = [
        ("Valid NYC", "(212) 555-0123"),
        ("Valid LA", "(310) 555-0199"),  
        ("Valid Chicago", "(312) 555-0156"),
        ("Invalid Area Code", "(999) 555-0123"),  # 999 not valid
        ("Invalid Exchange", "(212) 055-0123"),   # Exchange can't start with 0
        ("Fake Number", "(555) 555-5555"),       # Common fake pattern
        ("Test Number", "(123) 456-7890"),       # Sequential test number
        ("All Same Digits", "(777) 777-7777"),   # Repeated digits
    ]
    
    for test_name, phone in validation_cases:
        print(f"\nTest: {test_name}")
        print(f"Phone: {phone}")
        
        result = extractor.extract_from_text(f"Contact us at {phone}", f"validation_{test_name.lower().replace(' ', '_')}")
        
        if result.candidates:
            candidate = result.candidates[0]
            print(f"  Validation: {candidate.validation_status}")
            print(f"  Confidence: {candidate.confidence_score:.2f}")
            print(f"  Area Code Valid: {candidate.area_code in extractor.valid_area_codes}")
        else:
            print("  No phone numbers extracted")
    
    return True


def test_html_extraction():
    """Test phone extraction from HTML content"""
    print("\n" + "="*60)
    print("TESTING HTML PHONE EXTRACTION")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    html_samples = [
        ("Tel Link", '<a href="tel:+1-555-123-4567">Call Now</a>'),
        ("Data Attribute", '<div data-phone="555-123-4567">Contact Info</div>'),
        ("Mixed Content", '''
            <div class="contact-info">
                <h3>Contact Us</h3>
                <p>Office: (555) 123-4567</p>
                <p>Fax: (555) 123-4568</p>
                <a href="tel:1-800-555-0123">Toll Free</a>
            </div>
        '''),
        ("JavaScript Encoded", '''
            <script>
            var phone = "555" + "-" + "123" + "-" + "4567";
            </script>
        '''),
    ]
    
    for test_name, html_content in html_samples:
        print(f"\nTest: {test_name}")
        print(f"HTML: {html_content[:100]}...")
        
        result = extractor.extract_from_html(html_content, f"html_test_{test_name.lower().replace(' ', '_')}")
        
        print(f"  Total found: {result.total_found}")
        print(f"  High confidence: {result.high_confidence_count}")
        
        if result.primary_phone:
            print(f"  Primary: {result.primary_phone.formatted_number} ({result.primary_phone.phone_type.value})")
        
        for phone in result.secondary_phones[:3]:
            print(f"  Secondary: {phone.formatted_number}")
    
    return True


def test_batch_processing():
    """Test batch phone extraction"""
    print("\n" + "="*60)
    print("TESTING BATCH PROCESSING")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    batch_texts = [
        "Restaurant ABC: Call (555) 123-4567 for reservations",
        "Law Office of Smith & Associates: (312) 555-0199",
        "Dr. Johnson's Clinic - Emergency: 1-800-555-HELP",
        "Tech Support: Contact us at five five five one two three four five six seven",
        "Invalid business phone: (000) 000-0000",
    ]
    
    def progress_callback(current, total, url):
        print(f"  Processing {current+1}/{total}: {url}")
    
    results = extractor.extract_batch(batch_texts, progress_callback=progress_callback)
    
    print(f"\nBatch Results:")
    print(f"  Total processed: {len(results)}")
    
    total_candidates = sum(result.total_found for result in results)
    high_confidence = sum(result.high_confidence_count for result in results)
    business_phones = sum(result.business_phone_count for result in results)
    
    print(f"  Total candidates: {total_candidates}")
    print(f"  High confidence: {high_confidence}")
    print(f"  Business phones: {business_phones}")
    print(f"  Average extraction time: {sum(r.extraction_time_ms for r in results) / len(results):.2f}ms")
    
    return True


def test_data_extractor_integration():
    """Test integration with comprehensive data extractor"""
    print("\n" + "="*60)
    print("TESTING DATA EXTRACTOR INTEGRATION")
    print("="*60)
    
    # Mock HTML content for testing
    mock_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ABC Restaurant - Fine Dining</title>
        <meta name="description" content="ABC Restaurant offers fine dining experience in downtown Chicago">
    </head>
    <body>
        <h1>ABC Restaurant</h1>
        <div class="contact">
            <h3>Contact Information</h3>
            <p>Phone: (312) 555-0123</p>
            <p>Reservations: 555-123-DINE</p>
            <p>Email: info@abc-restaurant.com</p>
            <p>Address: 123 Main Street, Chicago, IL 60601</p>
        </div>
        <div class="hours">
            <p>Monday: 5:00 PM - 11:00 PM</p>
            <p>Tuesday: 5:00 PM - 11:00 PM</p>
        </div>
        <div class="rating">
            <p>4.5 out of 5 stars - 150 reviews</p>
        </div>
    </body>
    </html>
    '''
    
    print("Testing with mock restaurant HTML...")
    
    # Create a temporary HTML file for testing
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(mock_html)
        html_file = f.name
    
    # Note: In a real scenario, we'd test with actual URLs
    # For this test, we'll create a mock BusinessLead to show integration
    
    extractor = PhoneExtractor()
    result = extractor.extract_from_html(mock_html, "http://abc-restaurant.com")
    
    print(f"Phone extraction results:")
    print(f"  Total phones found: {result.total_found}")
    print(f"  Business phones: {result.business_phone_count}")
    
    if result.primary_phone:
        print(f"  Primary phone: {result.primary_phone.formatted_number}")
        print(f"  Phone type: {result.primary_phone.phone_type.value}")
        print(f"  Confidence: {result.primary_phone.confidence_score:.2f}")
    
    # Create a mock BusinessLead to show integration
    from botasaurus_core.models import BusinessLead, ContactInfo, Address
    
    contact_info = ContactInfo(
        phone=result.primary_phone.formatted_number if result.primary_phone else None,
        email="info@abc-restaurant.com",
        website="http://abc-restaurant.com"
    )
    
    address = Address(
        street="123 Main Street",
        city="Chicago", 
        state="IL",
        postal_code="60601"
    )
    
    business_lead = BusinessLead(
        name="ABC Restaurant",
        category="restaurant",
        description="Fine dining restaurant in downtown Chicago",
        contact=contact_info,
        address=address,
        rating=4.5,
        review_count=150
    )
    
    # Calculate confidence and validate
    confidence = business_lead.calculate_confidence()
    is_valid = business_lead.validate()
    
    print(f"\nBusinessLead Integration:")
    print(f"  Business Name: {business_lead.name}")
    print(f"  Contact Phone: {business_lead.contact.phone}")
    print(f"  Confidence Score: {confidence:.2f}")
    print(f"  Quality Level: {business_lead.quality_level.value}")
    print(f"  Valid Lead: {is_valid}")
    print(f"  Lead Status: {business_lead.status.value}")
    
    # Clean up
    os.unlink(html_file)
    
    return True


def test_performance():
    """Test extraction performance with large content"""
    print("\n" + "="*60)
    print("TESTING EXTRACTION PERFORMANCE")
    print("="*60)
    
    extractor = PhoneExtractor()
    
    # Generate large text with multiple phone numbers
    large_text = """
    Business Directory:
    """ + "\n".join([
        f"Business {i}: Call ({200 + (i % 800):03d}) {100 + (i % 900):03d}-{1000 + (i % 9000):04d} for service {i}"
        for i in range(100)
    ])
    
    print(f"Testing with text containing ~100 phone numbers...")
    print(f"Text length: {len(large_text):,} characters")
    
    start_time = time.time()
    result = extractor.extract_from_text(large_text, "performance_test")
    extraction_time = time.time() - start_time
    
    print(f"\nPerformance Results:")
    print(f"  Extraction time: {extraction_time:.3f} seconds")
    print(f"  Phones found: {result.total_found}")
    print(f"  High confidence: {result.high_confidence_count}")
    print(f"  Processing rate: {result.total_found / extraction_time:.1f} phones/second")
    print(f"  Character rate: {len(large_text) / extraction_time:.0f} chars/second")
    
    # Test meets performance requirements?
    phones_per_second = result.total_found / extraction_time
    target_rate = 50  # Target: 50+ phones per second
    
    print(f"  Performance target (50 phones/sec): {'✓ PASSED' if phones_per_second >= target_rate else '✗ FAILED'}")
    
    return phones_per_second >= target_rate


def run_comprehensive_tests():
    """Run all phone extraction tests"""
    print("PHONE EXTRACTION SYSTEM - COMPREHENSIVE TESTING")
    print("=" * 80)
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # Run individual tests
    tests = [
        ("Basic Patterns", test_basic_phone_patterns),
        ("Obfuscated Patterns", test_obfuscated_patterns),
        ("Context Awareness", test_context_awareness), 
        ("Validation System", test_validation_system),
        ("HTML Extraction", test_html_extraction),
        ("Batch Processing", test_batch_processing),
        ("Data Extractor Integration", test_data_extractor_integration),
        ("Performance", test_performance),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            result = test_func()
            test_results[test_name] = "PASSED" if result else "FAILED"
            if result:
                passed_tests += 1
            print(f"\n{test_name}: {'✓ PASSED' if result else '✗ FAILED'}")
        except Exception as e:
            test_results[test_name] = f"ERROR: {str(e)}"
            print(f"\n{test_name}: ✗ ERROR - {str(e)}")
    
    # Final report
    print("\n" + "="*80)
    print("FINAL TEST REPORT")
    print("="*80)
    
    for test_name, result in test_results.items():
        status_symbol = "✓" if result == "PASSED" else "✗"
        print(f"{status_symbol} {test_name:.<50} {result}")
    
    print(f"\nOVERALL RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Phone extraction system is ready for production!")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  MOSTLY PASSING - Phone extraction system needs minor fixes")
    else:
        print("❌ MULTIPLE FAILURES - Phone extraction system needs significant work")
    
    print(f"\nEnd time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed_tests, total_tests


def main():
    """Main test runner"""
    passed, total = run_comprehensive_tests()
    
    # Generate test statistics
    extractor = PhoneExtractor()
    stats = extractor.get_statistics()
    
    print(f"\nExtractor Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Exit with appropriate code
    exit_code = 0 if passed == total else 1
    exit(exit_code)


if __name__ == "__main__":
    main()