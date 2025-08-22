#!/usr/bin/env python3
"""
VALIDATION SCRIPT: Real vs Mock Data Check
Tests each component to identify what's using real data vs fake/mock data
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_email_extractor_real_data():
    """Test if email extractor works with real business websites"""
    print("\n=== TESTING EMAIL EXTRACTOR WITH REAL DATA ===")
    
    # Real business websites to test
    real_test_urls = [
        "https://www.mayoclinic.org/about-mayo-clinic/contact",
        "https://www.clevelandclinic.org/about/contact",
        "https://httpbin.org/html"  # Known working test site
    ]
    
    try:
        from fixed_email_extractor import WorkingEmailExtractor
        extractor = WorkingEmailExtractor(timeout=10)
        
        results = {}
        
        for url in real_test_urls:
            print(f"\nTesting: {url}")
            try:
                start_time = time.time()
                contact_info = extractor.extract_contact_info(url)
                processing_time = time.time() - start_time
                
                result = {
                    "success": True,
                    "url": url,
                    "processing_time": processing_time,
                    "business_name": contact_info.business_name,
                    "emails_found": len(contact_info.emails),
                    "phones_found": len(contact_info.phones),
                    "names_found": len(contact_info.names),
                    "addresses_found": len(contact_info.addresses),
                    "is_real_extraction": len(contact_info.emails) > 0 or len(contact_info.phones) > 0,
                    "sample_emails": [e['email'] for e in contact_info.emails[:2]],
                    "sample_phones": [p['phone'] for p in contact_info.phones[:2]]
                }
                
                print(f"  ✓ Business: {contact_info.business_name}")
                print(f"  ✓ Emails: {len(contact_info.emails)} found")
                print(f"  ✓ Phones: {len(contact_info.phones)} found")
                print(f"  ✓ Processing time: {processing_time:.2f}s")
                
                if result["is_real_extraction"]:
                    print(f"  ✓ REAL DATA EXTRACTED")
                else:
                    print(f"  ⚠ NO CONTACT DATA FOUND")
                
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                result = {
                    "success": False,
                    "url": url,
                    "error": str(e),
                    "is_real_extraction": False
                }
            
            results[url] = result
        
        return results
        
    except ImportError as e:
        print(f"✗ EMAIL EXTRACTOR NOT AVAILABLE: {e}")
        return {}

def test_comprehensive_lead_generator():
    """Test the comprehensive lead generator with minimal URLs"""
    print("\n=== TESTING COMPREHENSIVE LEAD GENERATOR ===")
    
    try:
        from comprehensive_lead_generator import ComprehensiveLeadGenerator
        
        generator = ComprehensiveLeadGenerator()
        
        # Test with a few real URLs
        test_urls = [
            "https://httpbin.org/html",
            "https://example.com"
        ]
        
        print(f"Testing with {len(test_urls)} URLs...")
        
        start_time = time.time()
        leads = generator.generate_leads_from_urls(test_urls, "test validation")
        processing_time = time.time() - start_time
        
        print(f"\nResults:")
        print(f"  Leads generated: {len(leads)}")
        print(f"  Processing time: {processing_time:.2f}s")
        print(f"  URLs processed: {generator.stats['urls_processed']}")
        print(f"  Contacts extracted: {generator.stats['contacts_extracted']}")
        
        # Analyze leads for real vs fake data
        real_data_indicators = 0
        fake_data_indicators = 0
        
        for i, lead in enumerate(leads[:3]):  # Check first 3 leads
            print(f"\n  Lead {i+1}:")
            print(f"    Business: {lead.business_name}")
            print(f"    Email: {lead.primary_email}")
            print(f"    Phone: {lead.primary_phone}")
            print(f"    Website: {lead.website}")
            
            # Check for mock/fake data patterns
            if any(fake in str(lead.__dict__).lower() for fake in ['example.com', 'test@', 'mock', 'fake', '555-']):
                fake_data_indicators += 1
                print(f"    ⚠ POTENTIAL FAKE DATA DETECTED")
            elif lead.primary_email and '@' in lead.primary_email:
                real_data_indicators += 1
                print(f"    ✓ APPEARS TO BE REAL DATA")
        
        result = {
            "success": len(leads) > 0,
            "leads_generated": len(leads),
            "processing_time": processing_time,
            "real_data_indicators": real_data_indicators,
            "fake_data_indicators": fake_data_indicators,
            "is_generating_real_data": real_data_indicators > fake_data_indicators,
            "stats": generator.stats
        }
        
        return result
        
    except Exception as e:
        print(f"✗ COMPREHENSIVE LEAD GENERATOR ERROR: {e}")
        return {"success": False, "error": str(e)}

def check_bing_scraper_availability():
    """Check if Bing scraper components are available and working"""
    print("\n=== CHECKING BING SCRAPER COMPONENTS ===")
    
    components_status = {}
    
    # Check BingNavigator
    try:
        from BingNavigator.BingNavigator import BingNavigator
        components_status["BingNavigator"] = "available"
        print("✓ BingNavigator: Available")
    except ImportError as e:
        components_status["BingNavigator"] = f"unavailable: {e}"
        print(f"✗ BingNavigator: {e}")
    
    # Check SerpParser
    try:
        from SerpParser.SerpParser import SerpParser
        components_status["SerpParser"] = "available"
        print("✓ SerpParser: Available")
    except ImportError as e:
        components_status["SerpParser"] = f"unavailable: {e}"
        print(f"✗ SerpParser: {e}")
    
    # Check if Botasaurus is available
    try:
        import botasaurus
        components_status["Botasaurus"] = "available"
        print("✓ Botasaurus: Available")
    except ImportError as e:
        components_status["Botasaurus"] = f"unavailable: {e}"
        print(f"✗ Botasaurus: {e}")
    
    # Check existing output files for evidence of real data
    output_dir = Path("output")
    html_cache_dir = output_dir / "html_cache"
    
    print(f"\n=== CHECKING OUTPUT FILES ===")
    
    if html_cache_dir.exists():
        html_files = list(html_cache_dir.glob("*.html"))
        print(f"HTML cache files found: {len(html_files)}")
        
        if html_files:
            # Check a recent HTML file for real vs fake content
            latest_html = max(html_files, key=lambda x: x.stat().st_mtime)
            print(f"Latest HTML file: {latest_html.name}")
            
            try:
                content = latest_html.read_text(encoding='utf-8')[:1000]  # First 1KB
                
                if "example.com" in content:
                    print("⚠ HTML contains example.com - possible mock data")
                    components_status["html_content"] = "contains_mock_data"
                elif any(term in content.lower() for term in ['bing', 'search', 'results']):
                    print("✓ HTML appears to contain real Bing search results")
                    components_status["html_content"] = "real_bing_data"
                else:
                    print("? HTML content unclear")
                    components_status["html_content"] = "unclear"
                    
            except Exception as e:
                print(f"✗ Error reading HTML: {e}")
                components_status["html_content"] = f"error: {e}"
    else:
        print("No HTML cache directory found")
        components_status["html_cache"] = "not_found"
    
    return components_status

def analyze_existing_lead_files():
    """Analyze existing CSV files for real vs fake data patterns"""
    print("\n=== ANALYZING EXISTING LEAD FILES ===")
    
    # Check output directory for CSV files
    output_dir = Path("output")
    csv_files = list(output_dir.glob("*.csv"))
    
    if not csv_files:
        # Check other directories
        csv_files.extend(Path(".").glob("*leads*.csv"))
        csv_files.extend(Path("lawyer_leads_output").glob("*.csv"))
    
    print(f"CSV files found: {len(csv_files)}")
    
    analysis_results = {}
    
    for csv_file in csv_files[-3:]:  # Check last 3 CSV files
        print(f"\nAnalyzing: {csv_file.name}")
        
        try:
            content = csv_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Basic stats
            data_lines = [line for line in lines[1:] if line.strip()]  # Skip header
            
            result = {
                "file": csv_file.name,
                "total_records": len(data_lines),
                "file_size_kb": len(content.encode('utf-8')) / 1024,
                "contains_real_domains": False,
                "contains_fake_domains": False,
                "sample_data": []
            }
            
            # Check for real vs fake patterns
            for line in data_lines[:5]:  # Check first 5 records
                if 'example.com' in line or '555-' in line:
                    result["contains_fake_domains"] = True
                
                if any(domain in line.lower() for domain in ['.com', '.org', '.net']) and 'example.com' not in line:
                    result["contains_real_domains"] = True
                
                # Extract sample data (safely)
                parts = line.split(',')
                if len(parts) >= 3:
                    result["sample_data"].append({
                        "business": parts[0].strip('"'),
                        "email": parts[1].strip('"') if len(parts) > 1 else "",
                        "phone": parts[2].strip('"') if len(parts) > 2 else ""
                    })
            
            print(f"  Records: {result['total_records']}")
            print(f"  File size: {result['file_size_kb']:.1f}KB")
            print(f"  Real domains: {result['contains_real_domains']}")
            print(f"  Fake domains: {result['contains_fake_domains']}")
            
            if result["sample_data"]:
                sample = result["sample_data"][0]
                print(f"  Sample business: {sample['business'][:50]}...")
                print(f"  Sample email: {sample['email']}")
            
            analysis_results[csv_file.name] = result
            
        except Exception as e:
            print(f"  ✗ Error analyzing {csv_file.name}: {e}")
            analysis_results[csv_file.name] = {"error": str(e)}
    
    return analysis_results

def main():
    """Main validation function"""
    print("🔍 LEAD GENERATION SYSTEM VALIDATION")
    print("=" * 60)
    print("Testing to identify REAL vs MOCK/FAKE data generation")
    print()
    
    validation_results = {
        "timestamp": time.time(),
        "validation_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Test 1: Email Extractor
    validation_results["email_extractor"] = test_email_extractor_real_data()
    
    # Test 2: Comprehensive Lead Generator  
    validation_results["lead_generator"] = test_comprehensive_lead_generator()
    
    # Test 3: Component Availability
    validation_results["components"] = check_bing_scraper_availability()
    
    # Test 4: Existing Files Analysis
    validation_results["existing_files"] = analyze_existing_lead_files()
    
    # Generate final assessment
    print("\n" + "=" * 60)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 60)
    
    real_data_components = []
    fake_data_components = []
    broken_components = []
    
    # Analyze email extractor
    if validation_results["email_extractor"]:
        real_extractions = sum(1 for r in validation_results["email_extractor"].values() 
                             if r.get("is_real_extraction", False))
        if real_extractions > 0:
            real_data_components.append("EmailExtractor")
        else:
            fake_data_components.append("EmailExtractor")
    else:
        broken_components.append("EmailExtractor")
    
    # Analyze lead generator
    if validation_results["lead_generator"].get("success"):
        if validation_results["lead_generator"].get("is_generating_real_data"):
            real_data_components.append("LeadGenerator")
        else:
            fake_data_components.append("LeadGenerator")
    else:
        broken_components.append("LeadGenerator")
    
    # Analyze components
    available_components = []
    unavailable_components = []
    for comp, status in validation_results["components"].items():
        if status == "available":
            available_components.append(comp)
        elif "unavailable" in str(status):
            unavailable_components.append(comp)
    
    # Analyze existing files
    real_data_files = []
    fake_data_files = []
    for filename, analysis in validation_results["existing_files"].items():
        if isinstance(analysis, dict) and not analysis.get("error"):
            if analysis.get("contains_real_domains") and not analysis.get("contains_fake_domains"):
                real_data_files.append(filename)
            elif analysis.get("contains_fake_domains"):
                fake_data_files.append(filename)
    
    print(f"✅ WORKING WITH REAL DATA: {', '.join(real_data_components) if real_data_components else 'NONE'}")
    print(f"⚠️  USING FAKE/MOCK DATA: {', '.join(fake_data_components) if fake_data_components else 'NONE'}")
    print(f"❌ BROKEN COMPONENTS: {', '.join(broken_components) if broken_components else 'NONE'}")
    print(f"📦 AVAILABLE COMPONENTS: {', '.join(available_components) if available_components else 'NONE'}")
    print(f"🚫 UNAVAILABLE COMPONENTS: {', '.join(unavailable_components) if unavailable_components else 'NONE'}")
    print(f"📄 FILES WITH REAL DATA: {', '.join(real_data_files) if real_data_files else 'NONE'}")
    print(f"📄 FILES WITH FAKE DATA: {', '.join(fake_data_files) if fake_data_files else 'NONE'}")
    
    # Overall assessment
    real_data_score = len(real_data_components) + len(real_data_files)
    fake_data_score = len(fake_data_components) + len(fake_data_files)
    
    print(f"\n🎯 OVERALL ASSESSMENT:")
    if real_data_score > fake_data_score:
        print(f"✅ SYSTEM IS PRIMARILY USING REAL DATA (Score: {real_data_score} vs {fake_data_score})")
    elif fake_data_score > real_data_score:
        print(f"⚠️  SYSTEM IS PRIMARILY USING FAKE/MOCK DATA (Score: {fake_data_score} vs {real_data_score})")
    else:
        print(f"🤔 MIXED RESULTS - NEED FURTHER INVESTIGATION (Score: {real_data_score} vs {fake_data_score})")
    
    # Save detailed results
    results_file = Path("output/validation_results.json")
    results_file.parent.mkdir(exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(validation_results, f, indent=2, default=str)
    
    print(f"\n📊 Detailed results saved to: {results_file}")
    
    return validation_results

if __name__ == "__main__":
    results = main()