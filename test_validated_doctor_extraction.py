#!/usr/bin/env python3
"""
Test with URLs that we know contain real email addresses from our validation
"""

import time
import logging
from comprehensive_lead_generator import ComprehensiveLeadGenerator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_validated_doctor_extraction():
    """Test with URLs that we previously validated contain real emails"""
    print("=" * 60)
    print("TESTING VALIDATED DOCTOR EMAIL EXTRACTION")
    print("=" * 60)
    
    # URLs we validated in previous tests that contained real emails
    test_urls = [
        "https://www.obout.com/",  # Had support@obout.com
        "https://www.rvohealth.com/",  # Had emcelroy@rvohealth.com  
        "https://www.healthline.com/health/doctors",  # Medical directory
        "https://www.webmd.com/find-a-doctor/florida/miami",  # Medical directory
    ]
    
    print(f"Testing {len(test_urls)} validated URLs:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    # Initialize lead generator
    lead_generator = ComprehensiveLeadGenerator(output_dir="validation_test")
    
    # Generate leads from these validated URLs
    print(f"\nExtracting leads from validated URLs...")
    leads = lead_generator.generate_leads_from_urls(test_urls, "doctors Miami Florida")
    
    print(f"\nResults:")
    print(f"Total leads extracted: {len(leads)}")
    
    if leads:
        print(f"\nLead Details:")
        print("-" * 60)
        
        real_lead_count = 0
        for i, lead in enumerate(leads, 1):
            print(f"\nLead {i}:")
            print(f"  Business: {lead.business_name}")
            print(f"  Contact: {lead.contact_name}")
            print(f"  Email: {lead.primary_email}")
            print(f"  Phone: {lead.primary_phone}")
            print(f"  Website: {lead.website}")
            print(f"  Lead Score: {lead.lead_score:.2f}")
            print(f"  Email Confidence: {lead.email_confidence:.2f}")
            
            # Check if this looks like real data
            has_real_email = "@" in (lead.primary_email or "") and not lead.primary_email.endswith("@example.com")
            has_business_name = len(lead.business_name or "") > 5
            has_contact_info = bool(lead.primary_phone or lead.primary_email)
            
            print(f"  Real Data Check:")
            print(f"    Has Real Email: {has_real_email}")
            print(f"    Has Business Name: {has_business_name}")
            print(f"    Has Contact Info: {has_contact_info}")
            
            is_real = has_real_email and has_business_name and has_contact_info
            print(f"    REAL LEAD: {is_real}")
            
            if is_real:
                real_lead_count += 1
        
        # Export to CSV for verification
        if leads:
            csv_file = lead_generator.export_leads_to_csv(leads, "validated_doctor_test_results.csv")
            print(f"\nCSV exported to: {csv_file}")
        
        print(f"\nSUMMARY:")
        print(f"  Total leads: {len(leads)}")
        print(f"  Real leads: {real_lead_count}")
        print(f"  Real lead rate: {(real_lead_count/len(leads)*100):.1f}%")
        
        return real_lead_count > 0
    else:
        print("ERROR: No leads extracted!")
        return False

if __name__ == "__main__":
    success = test_validated_doctor_extraction()
    if success:
        print(f"\n✅ SUCCESS: Real email extraction WORKING!")
        print(f"   System can extract real contact information")
        print(f"   Issue is with business URL discovery, not extraction")
    else:
        print(f"\n❌ FAILURE: Email extraction NOT WORKING!")
        print(f"   Need to debug email extraction system")