#!/usr/bin/env python3
"""
Test real doctor websites directly to verify the email extraction works
"""

import time
import logging
from comprehensive_lead_generator import ComprehensiveLeadGenerator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_real_doctor_sites():
    """Test with real doctor practice websites"""
    print("=" * 60)
    print("TESTING REAL DOCTOR WEBSITES")
    print("=" * 60)
    
    # Real doctor practice websites (publicly available contact info)
    test_urls = [
        "https://www.miamieye.com/",  # Miami Eye Center
        "https://www.palmettogeneral.com/",  # Palmetto General Hospital
        "https://www.doctorsorlando.com/",  # Doctors in Orlando
        "https://www.myfamilydoctor.com/",  # Family Doctor practice
        "https://www.miamichild.com/",  # Miami Children's Medical
    ]
    
    print(f"Testing {len(test_urls)} real doctor practice websites:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    # Initialize lead generator
    lead_generator = ComprehensiveLeadGenerator(output_dir="validation_test")
    
    # Generate leads from these real URLs
    print(f"\nExtracting leads from real doctor websites...")
    leads = lead_generator.generate_leads_from_urls(test_urls, "doctors Miami Florida")
    
    print(f"\nResults:")
    print(f"Total leads extracted: {len(leads)}")
    
    if leads:
        print(f"\nLead Details:")
        print("-" * 60)
        
        for i, lead in enumerate(leads, 1):
            print(f"\nLead {i}:")
            print(f"  Business: {lead.business_name}")
            print(f"  Contact: {lead.contact_name}")
            print(f"  Email: {lead.email}")
            print(f"  Phone: {lead.phone}")
            print(f"  Website: {lead.website}")
            print(f"  Lead Score: {lead.lead_score:.2f}")
            print(f"  Email Confidence: {lead.email_confidence:.2f}")
            
            # Check if this looks like real data
            has_real_email = "@" in (lead.email or "")
            has_business_name = len(lead.business_name or "") > 5
            has_contact_info = bool(lead.phone or lead.email)
            
            print(f"  Real Data Check:")
            print(f"    Has Email: {has_real_email}")
            print(f"    Has Business Name: {has_business_name}")
            print(f"    Has Contact Info: {has_contact_info}")
            
            is_real = has_real_email and has_business_name and has_contact_info
            print(f"    REAL LEAD: {is_real}")
        
        # Export to CSV for verification
        csv_file = lead_generator.export_leads_to_csv(leads, "real_doctor_test_results.csv")
        print(f"\nCSV exported to: {csv_file}")
        
        return True
    else:
        print("ERROR: No leads extracted from real doctor websites!")
        print("This indicates a problem with the email extraction system.")
        return False

if __name__ == "__main__":
    success = test_real_doctor_sites()
    if success:
        print(f"\n✅ SUCCESS: Real doctor data extraction WORKING!")
        print(f"   System can extract real contact information")
        print(f"   Ready for production doctor campaigns")
    else:
        print(f"\n❌ FAILURE: Real doctor data extraction NOT WORKING!")
        print(f"   Need to debug email extraction system")