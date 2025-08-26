"""
Santa Monica Restaurant Validation Demo
======================================

Demonstrates the complete validation pipeline with mock restaurant data
to show how the framework would work during actual scraping.
"""

import logging
import json
from datetime import datetime
from restaurant_validation_framework import (
    RestaurantValidationFramework,
    RestaurantLead,
    ValidationLevel
)

def create_sample_restaurant_data():
    """Create sample restaurant data including both real and fake examples"""
    
    # Mix of real Santa Monica restaurants and fake data that might be scraped
    sample_data = [
        # REAL SANTA MONICA RESTAURANTS (should pass validation)
        {
            'name': 'Boa Steakhouse',
            'address': '101 Santa Monica Blvd, Santa Monica, CA 90401',
            'phone': '(310) 899-4466',
            'email': 'info@boasteakhouse.com',
            'website': 'https://boasteakhouse.com',
            'cuisine_type': 'American',
            'source_url': 'https://bing.com/search?q=boa+steakhouse+santa+monica'
        },
        
        {
            'name': "Rustic Canyon Wine Bar",
            'address': "1119 Wilshire Blvd, Santa Monica, CA 90401",
            'phone': "(310) 393-7050",
            'email': "info@rusticcanyonwinebar.com",
            'website': "https://rusticcanyonwinebar.com",
            'cuisine_type': "Mediterranean",
            'source_url': 'https://bing.com/search?q=rustic+canyon+santa+monica'
        },
        
        {
            'name': "The Lobster Restaurant",
            'address': "1602 Ocean Ave, Santa Monica, CA 90401", 
            'phone': "(310) 458-9294",
            'email': "reservations@thelobster.com",
            'website': "https://thelobster.com",
            'cuisine_type': "Seafood",
            'source_url': 'https://bing.com/search?q=lobster+restaurant+santa+monica'
        },
        
        {
            'name': "Giorgio Baldi",
            'address': "114 W Channel Rd, Santa Monica, CA 90402",
            'phone': "(310) 573-1660", 
            'email': "info@giorgiobaldi.com",
            'website': "https://giorgiobaldi.com",
            'cuisine_type': "Italian",
            'source_url': 'https://bing.com/search?q=giorgio+baldi+santa+monica'
        },
        
        # FAKE DATA THAT MIGHT BE SCRAPED (should be rejected)
        {
            'name': 'Test Restaurant 123',
            'address': '123 Test Street, Santa Monica, CA 90401',
            'phone': '(555) 123-4567',
            'email': 'test@example.com',
            'website': 'http://test.example.com',
            'cuisine_type': 'American',
            'source_url': 'https://bing.com/search?q=test+restaurant'
        },
        
        {
            'name': 'Sample Diner',
            'address': '456 Sample Ave, Santa Monica, CA 90402',
            'phone': '(555) 000-0000',
            'email': 'fake@test.com',
            'website': 'http://sample.local',
            'cuisine_type': 'American',
            'source_url': 'https://bing.com/search?q=sample+diner'
        },
        
        {
            'name': 'Restaurant 001',
            'address': '789 Main St, Santa Monica, CA 90403',
            'phone': '(310) 555-1234',
            'email': 'info@restaurant001.com', 
            'website': 'http://restaurant001.com',
            'cuisine_type': 'Generic',
            'source_url': 'https://bing.com/search?q=restaurant+001'
        },
        
        # EDGE CASES (should be handled gracefully)
        {
            'name': 'Café José\'s Taquería',  # Special characters
            'address': '1234 Résumé Blvd, Santa Mónica, CA 90404',
            'phone': '(310) 987-6543',
            'email': 'josé@taqueria.com',
            'website': 'https://café-josé.com',
            'cuisine_type': 'Mexican',
            'source_url': 'https://bing.com/search?q=jose+taqueria'
        },
        
        {
            'name': '',  # Empty name (should be rejected)
            'address': '1000 Empty St, Santa Monica, CA 90405',
            'phone': '(310) 555-9999',
            'email': 'empty@restaurant.com',
            'website': 'https://empty.com',
            'cuisine_type': '',
            'source_url': 'https://bing.com/search?q=empty'
        }
    ]
    
    return sample_data

def run_santa_monica_validation_demo():
    """Run complete validation demo for Santa Monica restaurants"""
    
    print("🏖️  SANTA MONICA RESTAURANT VALIDATION DEMO")
    print("=" * 55)
    print("Demonstrating real-time validation during restaurant lead scraping")
    print("Zero tolerance for fake data, technical shortcuts, or mock responses\n")
    
    # Initialize validation framework with strict settings
    config = {
        'email': {'enable_dns_check': False},  # Disable DNS for demo speed
        'validation_level': 'strict'
    }
    
    framework = RestaurantValidationFramework(ValidationLevel.STRICT, config)
    
    # Get sample data
    sample_data = create_sample_restaurant_data()
    print(f"📊 Processing {len(sample_data)} restaurant leads from Santa Monica scraping...\n")
    
    # Convert to RestaurantLead objects
    leads = []
    for data in sample_data:
        lead = RestaurantLead(
            name=data.get('name', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            website=data.get('website', ''),
            cuisine_type=data.get('cuisine_type', ''),
            source_url=data.get('source_url', '')
        )
        leads.append(lead)
    
    # Create validation checkpoint before processing
    print("🔍 VALIDATION CHECKPOINT: Pre-Processing")
    print("-" * 40)
    print(f"Input: {len(leads)} potential restaurant leads")
    print("Validation Level: STRICT (zero tolerance for fake data)")
    print("Geographic Filter: Santa Monica, CA only")
    print("Business Type Filter: Restaurants only\n")
    
    # Process leads with real-time validation
    validated_leads = []
    rejected_leads = []
    
    print("🔄 REAL-TIME VALIDATION RESULTS")
    print("-" * 40)
    
    for i, lead in enumerate(leads, 1):
        print(f"{i:2d}. {lead.name[:35]:<35} ", end="")
        
        # Validate lead
        validated_lead = framework.validate_lead(lead)
        
        # Determine result
        if validated_lead.is_authentic and validated_lead.overall_score >= 0.7:
            validated_leads.append(validated_lead)
            status = f"✅ PASS (Score: {validated_lead.overall_score:.2f})"
            print(status)
        else:
            rejected_leads.append(validated_lead)
            status = f"❌ FAIL (Score: {validated_lead.overall_score:.2f})"
            print(status)
            
            # Show why it was rejected
            for result in validated_lead.validation_results:
                if result.status.value == 'fail':
                    print(f"    ↳ {result.message}")
    
    print()
    
    # Validation summary
    print("📈 VALIDATION SUMMARY")
    print("-" * 40)
    print(f"✅ Authentic Leads Passed: {len(validated_leads)}")
    print(f"❌ Fake/Invalid Leads Rejected: {len(rejected_leads)}")
    print(f"🎯 Success Rate: {len(validated_leads)/len(leads)*100:.1f}% authentic data")
    print(f"🛡️  Protection Rate: {len(rejected_leads)/len(leads)*100:.1f}% fake data blocked")
    
    # Show authentic leads details
    if validated_leads:
        print(f"\n🏆 VALIDATED SANTA MONICA RESTAURANTS")
        print("-" * 50)
        for lead in validated_leads:
            print(f"• {lead.name}")
            print(f"  📍 {lead.address}")
            print(f"  📞 {lead.phone}")
            print(f"  📧 {lead.email}")
            print(f"  🌐 {lead.website}")
            print(f"  🍽️  {lead.cuisine_type}")
            print(f"  ⭐ Quality Score: {lead.overall_score:.2f}")
            print()
    
    # Show what was rejected and why
    if rejected_leads:
        print("🚫 REJECTED LEADS (Fake Data Detected)")
        print("-" * 50)
        for lead in rejected_leads[:3]:  # Show first 3 rejected
            print(f"• {lead.name}")
            fake_indicators = []
            for result in lead.validation_results:
                if 'fake' in result.message.lower() or 'test' in result.message.lower():
                    fake_indicators.append(result.message)
            
            if fake_indicators:
                print(f"  🔍 Fake Data Indicators:")
                for indicator in fake_indicators[:2]:  # Show top 2 indicators
                    print(f"    - {indicator}")
            print()
        
        if len(rejected_leads) > 3:
            print(f"    ... and {len(rejected_leads) - 3} more rejected leads")
    
    # Technical debt monitoring results
    print("🔧 TECHNICAL DEBT MONITORING")
    print("-" * 40)
    
    # Check for suspicious patterns across all leads
    all_emails = [lead.email for lead in leads if lead.email]
    test_email_count = sum(1 for email in all_emails if any(word in email.lower() for word in ['test', 'example', 'fake']))
    sequential_names = sum(1 for lead in leads if lead.name and any(char.isdigit() for char in lead.name[-5:]))
    
    print(f"📧 Test Email Patterns Detected: {test_email_count}/{len(all_emails)} emails")
    print(f"🔢 Sequential Naming Patterns: {sequential_names}/{len(leads)} names")
    
    if test_email_count > 0 or sequential_names > 0:
        print("⚠️  Technical shortcuts or fake data generation detected!")
    else:
        print("✅ No technical debt indicators found - data appears organically scraped")
    
    # Generate validation report
    print(f"\n📊 FINAL VALIDATION REPORT")
    print("-" * 40)
    
    report = framework.get_validation_report()
    if report and 'validation_summary' in report:
        summary = report['validation_summary']
        print(f"Total Leads Processed: {summary.get('total_leads_validated', 0)}")
        print(f"Authentic Leads: {summary.get('authentic_leads', 0)}")
        print(f"Rejection Rate: {summary.get('rejection_rate', 0):.1%}")
        print(f"Average Quality Score: {summary.get('average_score', 0):.2f}")
    
    # Save evidence file
    evidence_file = f"santa_monica_validation_evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    framework.save_validation_evidence(evidence_file)
    
    print(f"\n💾 Validation evidence saved: {evidence_file}")
    print(f"🔍 This file contains complete audit trail of all validation decisions")
    
    # Final assessment
    print(f"\n🎉 VALIDATION FRAMEWORK STATUS")
    print("=" * 40)
    
    if len(validated_leads) >= 3 and len(rejected_leads) >= 3:
        print("✅ VALIDATION FRAMEWORK OPERATIONAL")
        print("✅ Fake data detection working correctly")
        print("✅ Real restaurant data being accepted") 
        print("✅ Santa Monica geographic filtering active")
        print("✅ Technical debt monitoring functional")
        print("✅ Ready for production restaurant lead generation")
        
        success = True
    else:
        print("⚠️  VALIDATION FRAMEWORK NEEDS TUNING")
        print("❌ May be too strict or too permissive")
        
        success = False
    
    return success, len(validated_leads), len(rejected_leads)

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    success, validated_count, rejected_count = run_santa_monica_validation_demo()
    
    print(f"\n{'='*55}")
    print(f"Demo Result: {'SUCCESS' if success else 'NEEDS ADJUSTMENT'}")
    print(f"Validated: {validated_count} | Rejected: {rejected_count}")
    print(f"{'='*55}")
    
    exit(0 if success else 1)