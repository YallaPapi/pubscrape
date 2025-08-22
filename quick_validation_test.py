"""
Quick Validation Framework Test
==============================

Fast test to demonstrate that the validation framework properly detects
fake data and accepts real restaurant data without slow DNS lookups.
"""

import logging
from restaurant_validation_framework import (
    RestaurantValidationFramework,
    RestaurantLead,
    ValidationLevel
)

def run_quick_validation_test():
    """Run a quick validation test to prove the framework works"""
    
    print("=== Restaurant Validation Framework Test ===")
    print("Testing fake data detection and real data acceptance...\n")
    
    # Initialize framework with DNS checking disabled for speed
    config = {
        'email': {'enable_dns_check': False},  # Disable DNS for speed
        'phone': {'enable_mx_check': False}
    }
    
    framework = RestaurantValidationFramework(ValidationLevel.STRICT, config)
    
    # Test cases
    test_leads = [
        # FAKE DATA - Should be rejected
        RestaurantLead(
            name="Test Restaurant 123",
            address="123 Test Street, Santa Monica, CA 90401",
            phone="(555) 123-4567",  # Fake 555 number
            email="test@example.com",  # Test domain
            website="http://test.example.com"
        ),
        
        RestaurantLead(
            name="Sample Eatery",
            address="Sample Address, Santa Monica, CA",
            phone="(555) 000-0000",  # Fake number
            email="fake@test.com",
            website="http://fake.local"
        ),
        
        # REAL DATA - Should be accepted
        RestaurantLead(
            name="Boa Steakhouse",
            address="101 Santa Monica Blvd, Santa Monica, CA 90401",
            phone="(310) 899-4466",  # Real LA area code
            email="info@boasteakhouse.com",  # Real business domain
            website="https://boasteakhouse.com",
            cuisine_type="American"
        ),
        
        RestaurantLead(
            name="Ocean View Seafood",
            address="1602 Ocean Ave, Santa Monica, CA 90401",
            phone="(310) 458-9294",  # Real LA area code
            email="reservations@oceanview.com",
            website="https://oceanview.com",
            cuisine_type="Seafood"
        ),
        
        # QUESTIONABLE DATA - Should get medium scores
        RestaurantLead(
            name="Local Pizza",  # Generic but not fake
            address="Santa Monica, CA",  # Incomplete but valid
            phone="(310) 555-9876",  # 555 in middle (questionable)
            email="owner@gmail.com",  # Personal email but legitimate
            website="https://localpizza.com"
        )
    ]
    
    print("Testing individual leads:\n")
    results = []
    
    for i, lead in enumerate(test_leads, 1):
        print(f"{i}. Testing: {lead.name}")
        
        # Validate the lead
        validated_lead = framework.validate_lead(lead)
        
        # Display results
        status = "✅ AUTHENTIC" if validated_lead.is_authentic else "❌ REJECTED"
        score = validated_lead.overall_score
        
        print(f"   Result: {status} (Score: {score:.2f})")
        
        # Show key validation details
        for result in validated_lead.validation_results:
            print(f"   - {result.status.value.upper()}: {result.message}")
        
        results.append({
            'name': lead.name,
            'authentic': validated_lead.is_authentic,
            'score': score,
            'expected_fake': any(word in lead.name.lower() for word in ['test', 'sample', 'fake']),
            'has_555_phone': '555' in (lead.phone or ''),
            'has_test_email': any(word in (lead.email or '').lower() for word in ['test', 'fake', 'example'])
        })
        
        print()
    
    # Summary
    print("=== VALIDATION SUMMARY ===")
    
    fake_leads_detected = sum(1 for r in results if r['expected_fake'] and not r['authentic'])
    real_leads_accepted = sum(1 for r in results if not r['expected_fake'] and r['authentic'])
    total_fake = sum(1 for r in results if r['expected_fake'])
    total_real = sum(1 for r in results if not r['expected_fake'])
    
    print(f"Fake Data Detection: {fake_leads_detected}/{total_fake} fake leads properly rejected")
    print(f"Real Data Acceptance: {real_leads_accepted}/{total_real} real leads properly accepted")
    
    # Detailed results
    print("\nDetailed Results:")
    print("Name | Authentic | Score | Expected Fake | 555 Phone | Test Email")
    print("-" * 75)
    
    for result in results:
        authentic_symbol = "✅" if result['authentic'] else "❌"
        print(f"{result['name']:<25} | {authentic_symbol:<9} | {result['score']:.2f}  | "
              f"{result['expected_fake']:<13} | {result['has_555_phone']:<9} | {result['has_test_email']}")
    
    # Test success criteria
    print("\n=== TEST RESULTS ===")
    
    success_criteria = [
        (fake_leads_detected == total_fake, f"Fake data detection: {fake_leads_detected}/{total_fake}"),
        (real_leads_accepted >= total_real * 0.8, f"Real data acceptance: {real_leads_accepted}/{total_real}"),
    ]
    
    all_passed = True
    for passed, message in success_criteria:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {message}")
        if not passed:
            all_passed = False
    
    overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    print(f"\nOverall Result: {overall_status}")
    
    if all_passed:
        print("\n🎉 The validation framework is working correctly!")
        print("✅ Fake data is being properly detected and rejected")
        print("✅ Real restaurant data is being accepted")
        print("✅ The framework is ready for production use")
    else:
        print("\n⚠️  The validation framework needs adjustments")
    
    return all_passed


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise for demo
    
    success = run_quick_validation_test()
    exit(0 if success else 1)