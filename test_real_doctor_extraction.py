#!/usr/bin/env python3
"""
Test script to validate real doctor lead extraction with 'doctor Miami' query
This will test the end-to-end pipeline with real data extraction
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_real_doctor_miami_extraction():
    """Test real doctor Miami lead extraction"""
    print("🏥 TESTING REAL DOCTOR MIAMI LEAD EXTRACTION")
    print("=" * 60)
    
    # Test with a known working URL that should have contact information
    real_medical_urls = [
        "https://www.mayoclinic.org/about-mayo-clinic/contact",
        "https://www.health.harvard.edu/contact",
        "https://www.hopkinsmedicine.org/contact/",
        "https://www.webmd.com/about-webmd-policies/contact-us"
    ]
    
    try:
        from comprehensive_lead_generator import ComprehensiveLeadGenerator
        
        print(f"Testing comprehensive lead generator with {len(real_medical_urls)} medical URLs...")
        
        generator = ComprehensiveLeadGenerator()
        
        # Generate leads from real medical websites
        start_time = time.time()
        leads = generator.generate_leads_from_urls(real_medical_urls, "doctor Miami test")
        processing_time = time.time() - start_time
        
        print(f"\n{'='*50}")
        print("REAL DATA EXTRACTION RESULTS")
        print(f"{'='*50}")
        
        print(f"Processing time: {processing_time:.2f}s")
        print(f"URLs processed: {generator.stats['urls_processed']}")
        print(f"Contacts extracted: {generator.stats['contacts_extracted']}")
        print(f"Leads generated: {len(leads)}")
        
        # Analyze extracted leads
        real_data_count = 0
        fake_data_count = 0
        
        for i, lead in enumerate(leads):
            print(f"\n--- Lead {i+1} ---")
            print(f"Business: {lead.business_name}")
            print(f"Email: {lead.primary_email}")
            print(f"Phone: {lead.primary_phone}")
            print(f"Website: {lead.website}")
            print(f"Lead Score: {lead.lead_score}")
            print(f"Is Actionable: {lead.is_actionable}")
            
            # Check for real vs fake data indicators
            if lead.primary_email and '@' in lead.primary_email:
                if any(fake_indicator in lead.primary_email.lower() for fake_indicator in ['example.com', 'test@', 'mock', 'fake']):
                    fake_data_count += 1
                    print("⚠️  FAKE DATA DETECTED")
                else:
                    real_data_count += 1
                    print("✅ REAL DATA DETECTED")
            
            if lead.primary_phone and '555-' in lead.primary_phone:
                fake_data_count += 1
                print("⚠️  FAKE PHONE NUMBER (555-) DETECTED")
            elif lead.primary_phone:
                real_data_count += 1
                print("✅ REAL PHONE NUMBER DETECTED")
        
        # Generate CSV export to verify output
        if leads:
            csv_file = generator.export_leads_to_csv(leads, "real_doctor_miami_test.csv")
            print(f"\n📄 Leads exported to: {csv_file}")
            
            # Read and verify CSV content
            csv_content = csv_file.read_text(encoding='utf-8')
            print(f"📊 CSV size: {len(csv_content)} characters")
            
            if "example.com" in csv_content:
                print("⚠️  CSV contains example.com domains (fake data)")
            else:
                print("✅ CSV appears to contain real data")
        
        # Final assessment
        print(f"\n{'='*50}")
        print("VALIDATION SUMMARY")
        print(f"{'='*50}")
        print(f"Real data indicators: {real_data_count}")
        print(f"Fake data indicators: {fake_data_count}")
        
        if real_data_count > fake_data_count:
            print("✅ PRIMARILY REAL DATA EXTRACTION")
            validation_result = "REAL_DATA"
        elif fake_data_count > real_data_count:
            print("⚠️  PRIMARILY FAKE DATA GENERATION")
            validation_result = "FAKE_DATA"
        elif len(leads) == 0:
            print("❌ NO DATA EXTRACTED")
            validation_result = "NO_DATA"
        else:
            print("🤔 MIXED DATA RESULTS")
            validation_result = "MIXED_DATA"
        
        return {
            "validation_result": validation_result,
            "leads_generated": len(leads),
            "real_data_count": real_data_count,
            "fake_data_count": fake_data_count,
            "processing_time": processing_time,
            "urls_processed": generator.stats['urls_processed'],
            "csv_file": str(csv_file) if leads else None,
            "leads": [lead.to_dict() for lead in leads[:3]]  # Sample leads
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "validation_result": "ERROR"}

def test_individual_components():
    """Test individual components for real data handling"""
    print("\n🔧 TESTING INDIVIDUAL COMPONENTS")
    print("=" * 40)
    
    results = {}
    
    # Test Email Extractor directly
    print("\n1. Testing EmailExtractor...")
    try:
        from fixed_email_extractor import WorkingEmailExtractor
        extractor = WorkingEmailExtractor(timeout=8)
        
        test_url = "https://www.mayoclinic.org/about-mayo-clinic/contact"
        contact_info = extractor.extract_contact_info(test_url)
        
        results["email_extractor"] = {
            "success": True,
            "business_name": contact_info.business_name,
            "emails_found": len(contact_info.emails),
            "phones_found": len(contact_info.phones),
            "is_real": len(contact_info.emails) > 0 or len(contact_info.phones) > 0
        }
        
        print(f"✅ EmailExtractor: {results['email_extractor']['emails_found']} emails, {results['email_extractor']['phones_found']} phones")
        
    except Exception as e:
        results["email_extractor"] = {"success": False, "error": str(e)}
        print(f"❌ EmailExtractor failed: {e}")
    
    # Test if BingNavigator can be used
    print("\n2. Testing BingNavigator availability...")
    try:
        from BingNavigator.BingNavigator import BingNavigator
        results["bing_navigator"] = {"available": True}
        print("✅ BingNavigator: Available")
    except ImportError as e:
        results["bing_navigator"] = {"available": False, "error": str(e)}
        print(f"❌ BingNavigator: {e}")
    
    return results

def main():
    """Main test function"""
    print("🎯 REAL DOCTOR MIAMI LEAD EXTRACTION VALIDATION")
    print("=" * 70)
    
    # Test 1: Individual components
    component_results = test_individual_components()
    
    # Test 2: End-to-end real data extraction
    extraction_results = test_real_doctor_miami_extraction()
    
    # Combine results
    final_results = {
        "test_timestamp": time.time(),
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "components": component_results,
        "extraction": extraction_results
    }
    
    # Save results
    results_file = Path("output/real_doctor_test_results.json")
    results_file.parent.mkdir(exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    # Final verdict
    print(f"\n{'='*70}")
    print("🏥 FINAL VALIDATION VERDICT")
    print(f"{'='*70}")
    
    validation_result = extraction_results.get("validation_result", "ERROR")
    
    if validation_result == "REAL_DATA":
        print("✅ SUCCESS: System is extracting REAL medical contact data")
        print("✅ Email extractor connects to real websites")
        print("✅ Contact information is being extracted from actual medical sites")
        print("✅ CSV output contains real business data")
        verdict = "WORKING_WITH_REAL_DATA"
    elif validation_result == "FAKE_DATA":
        print("⚠️  ISSUE: System is generating FAKE/MOCK data")
        print("⚠️  Email extractor may be using placeholder data")
        print("⚠️  CSV output contains mock business information")
        verdict = "GENERATING_FAKE_DATA"
    elif validation_result == "NO_DATA":
        print("❌ PROBLEM: No contact data is being extracted")
        print("❌ Email extractor is not finding contact information")
        print("❌ May need to adjust extraction methods")
        verdict = "NO_DATA_EXTRACTION"
    else:
        print("🤔 UNCLEAR: Mixed or error results")
        print("🤔 Further investigation needed")
        verdict = "INCONCLUSIVE"
    
    # Component availability summary
    if component_results.get("email_extractor", {}).get("success"):
        print("✅ EmailExtractor: Working")
    else:
        print("❌ EmailExtractor: Issues detected")
    
    if component_results.get("bing_navigator", {}).get("available"):
        print("✅ BingNavigator: Available for search")
    else:
        print("❌ BingNavigator: Not available")
    
    print(f"\n📊 Detailed results saved to: {results_file}")
    
    final_results["verdict"] = verdict
    return final_results

if __name__ == "__main__":
    results = main()