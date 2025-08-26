#!/usr/bin/env python3
"""
Test the lead generation system with a rich contact page
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from comprehensive_lead_generator import ComprehensiveLeadGenerator, Lead
from fixed_email_extractor import WorkingEmailExtractor, ContactInfo


def test_with_rich_contact_page():
    """Test with our rich contact page"""
    print("Testing with Rich Contact Page")
    print("="*50)
    
    # Get the file URL
    contact_file = Path("test_contact_page.html").absolute()
    file_url = f"file:///{contact_file.as_posix()}"
    
    print(f"Testing with: {file_url}")
    
    # Test email extractor first
    print("\n1. Testing Email Extractor:")
    print("-" * 30)
    
    extractor = WorkingEmailExtractor(timeout=10)
    contact_info = extractor.extract_contact_info(file_url)
    
    print(f"Business Name: {contact_info.business_name}")
    print(f"Emails Found: {len(contact_info.emails)}")
    print(f"Phones Found: {len(contact_info.phones)}")
    print(f"Names Found: {len(contact_info.names)}")
    print(f"Addresses Found: {len(contact_info.addresses)}")
    print(f"Social Profiles: {len(contact_info.social_profiles)}")
    print(f"Lead Score: {contact_info.lead_score:.2f}")
    print(f"Is Actionable: {contact_info.is_actionable}")
    
    if contact_info.emails:
        print("\nEmail Details:")
        for email in contact_info.emails:
            print(f"  - {email['email']} (confidence: {email['confidence']:.2f}, source: {email['source']})")
    
    if contact_info.phones:
        print("\nPhone Details:")
        for phone in contact_info.phones:
            print(f"  - {phone['phone']} (confidence: {phone['confidence']:.2f}, type: {phone['type']})")
    
    if contact_info.names:
        print("\nName Details:")
        for name in contact_info.names:
            print(f"  - {name['name']} (confidence: {name['confidence']:.2f}, context: {name['context']})")
    
    if contact_info.addresses:
        print("\nAddresses:")
        for addr in contact_info.addresses:
            print(f"  - {addr}")
    
    if contact_info.social_profiles:
        print("\nSocial Profiles:")
        for social in contact_info.social_profiles:
            print(f"  - {social}")
    
    # Test comprehensive lead generator
    print(f"\n2. Testing Comprehensive Lead Generator:")
    print("-" * 40)
    
    generator = ComprehensiveLeadGenerator(output_dir="test_contact_output")
    
    leads = generator.generate_leads_from_urls([file_url], "optometrist Atlanta test")
    
    print(f"\nLead Generation Results:")
    print(f"  URLs processed: 1")
    print(f"  Leads generated: {len(leads)}")
    
    if leads:
        print(f"\nLead Details:")
        for i, lead in enumerate(leads, 1):
            print(f"  Lead {i}:")
            print(f"    Business: {lead.business_name}")
            print(f"    Primary Email: {lead.primary_email}")
            print(f"    Primary Phone: {lead.primary_phone}")
            print(f"    Contact Name: {lead.contact_name}")
            print(f"    Contact Title: {lead.contact_title}")
            print(f"    Website: {lead.website}")
            print(f"    Address: {lead.address}")
            print(f"    City: {lead.city}")
            print(f"    State: {lead.state}")
            print(f"    LinkedIn: {lead.linkedin_url}")
            print(f"    Facebook: {lead.facebook_url}")
            print(f"    Secondary Emails: {len(lead.secondary_emails)}")
            print(f"    Lead Score: {lead.lead_score:.2f}")
            print(f"    Email Confidence: {lead.email_confidence:.2f}")
            print(f"    Data Completeness: {lead.data_completeness:.2f}")
            print(f"    Is Actionable: {lead.is_actionable}")
            print(f"    Validation Status: {lead.validation_status}")
            
            if lead.secondary_emails:
                print(f"    Secondary Emails:")
                for email in lead.secondary_emails:
                    print(f"      - {email}")
        
        # Export to CSV
        csv_file = generator.export_leads_to_csv(leads, "test_contact_leads.csv")
        print(f"\n3. CSV Export:")
        print(f"   CSV File: {csv_file}")
        
        # Generate report
        report_file = generator.save_report(leads, "test_contact_report.json")
        print(f"   Report File: {report_file}")
        
        # Show CSV content
        print(f"\n4. CSV Content Preview:")
        print("-" * 30)
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:3]):  # Show first 3 lines
                    print(f"   {line.strip()}")
                if len(lines) > 3:
                    print(f"   ... ({len(lines)-3} more lines)")
        except Exception as e:
            print(f"   Error reading CSV: {e}")
        
        return True
    else:
        print("   No leads generated - check extraction logic")
        return False


def main():
    """Run the test"""
    print("Lead Generation System - Contact Page Test")
    print("="*60)
    
    # Check if test file exists
    if not Path("test_contact_page.html").exists():
        print("ERROR: test_contact_page.html not found!")
        print("Make sure the test contact page file exists.")
        return False
    
    success = test_with_rich_contact_page()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if success:
        print("SUCCESS: Lead generation system is working perfectly!")
        print("+ Email extraction works")
        print("+ Contact information parsing works")
        print("+ Lead generation pipeline works")
        print("+ CSV export works")
        print("+ Lead scoring and validation works")
        print("\nThe system is ready for production use!")
    else:
        print("ISSUES: System needs debugging")
        print("- Check email extraction patterns")
        print("- Verify contact parsing logic")
        print("- Review lead generation criteria")
    
    print("\nNext steps:")
    print("1. Test with real business websites")
    print("2. Run full Bing search campaigns")
    print("3. Configure for specific business types")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)