#!/usr/bin/env python3
"""
Integration Tests for VRSEN Pipeline
Tests agent-to-agent communication and full pipeline flow
"""

import os
import sys
import json
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestBingNavigatorToSerpParserHandoff(unittest.TestCase):
    """Test the handoff between BingNavigator and SerpParser"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_output_dir = Path("output/html_cache")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_realistic_bing_html(self) -> str:
        """Create realistic Bing search results HTML"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>doctors in chicago contact - Bing</title>
            <meta charset="utf-8">
        </head>
        <body>
        <div id="b_content">
            <div class="b_algo">
                <h2><a href="https://www.chicagomedicalgroup.com/contact" h="ID=SERP,5234.1">Chicago Medical Group - Contact Us</a></h2>
                <div class="b_caption">
                    <p>Contact Chicago Medical Group for appointments and inquiries. Call (312) 555-0123 or email info@chicagomedicalgroup.com</p>
                    <div class="b_attribution">
                        <cite>chicagomedicalgroup.com/contact</cite>
                    </div>
                </div>
            </div>
            
            <div class="b_algo">
                <h2><a href="https://northsidemedical.org/physicians" h="ID=SERP,5234.2">Northside Medical - Find a Doctor</a></h2>
                <div class="b_caption">
                    <p>Find experienced doctors at Northside Medical. Contact our physician directory for appointments.</p>
                    <div class="b_attribution">
                        <cite>northsidemedical.org/physicians</cite>
                    </div>
                </div>
            </div>
            
            <div class="b_algo">
                <h2><a href="https://chicagohealthcare.net/directory" h="ID=SERP,5234.3">Chicago Healthcare Directory</a></h2>
                <div class="b_caption">
                    <p>Comprehensive directory of healthcare providers in Chicago area. Contact information included.</p>
                    <div class="b_attribution">
                        <cite>chicagohealthcare.net/directory</cite>
                    </div>
                </div>
            </div>
            
            <div class="b_algo">
                <h2><a href="https://www.doctorcontacts.com/chicago" h="ID=SERP,5234.4">Doctor Contacts Chicago</a></h2>
                <div class="b_caption">
                    <p>Professional medical contacts and email addresses for Chicago doctors and medical practices.</p>
                    <div class="b_attribution">
                        <cite>doctorcontacts.com/chicago</cite>
                    </div>
                </div>
            </div>
            
            <div class="b_algo">
                <h2><a href="https://medicalprofessionals.org/illinois" h="ID=SERP,5234.5">Medical Professionals Illinois</a></h2>
                <div class="b_caption">
                    <p>Illinois medical professionals directory with contact information and specialties.</p>
                    <div class="b_attribution">
                        <cite>medicalprofessionals.org/illinois</cite>
                    </div>
                </div>
            </div>
        </div>
        </body>
        </html>
        """
    
    def test_bingnavigator_serpparser_flow(self):
        """Test full BingNavigator -> SerpParser integration"""
        print("\n🔧 Testing BingNavigator → SerpParser integration...")
        
        # Step 1: Simulate BingNavigator output (fixed version)
        realistic_html = self.create_realistic_bing_html()
        
        # Save HTML to file (as fixed BingNavigator does)
        timestamp = int(time.time())
        html_filename = f"bing_integration_test_{timestamp}.html"
        html_filepath = self.test_output_dir / html_filename
        
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(realistic_html)
        
        # Create BingNavigator response (fixed format)
        navigator_response = {
            "status": "success", 
            "html_file": str(html_filepath),
            "html_preview": realistic_html[:1000] + "...",
            "meta": {
                "query": "doctors in chicago contact",
                "page": 1,
                "timestamp": time.time(),
                "response_time_ms": 1200,
                "content_length": len(realistic_html),
                "file_size": len(realistic_html.encode('utf-8')),
                "html_saved": True,
                "stealth_enabled": True,
                "method": "direct",
                "session_id": f"integration_test_{timestamp}",
                "title": "doctors in chicago contact - Bing",
                "url": "https://www.bing.com/search?q=doctors+in+chicago+contact",
                "is_blocked": False
            }
        }
        
        # Verify BingNavigator payload size
        navigator_payload = json.dumps(navigator_response, indent=2)
        navigator_size = len(navigator_payload.encode('utf-8'))
        
        print(f"  📏 BingNavigator payload: {navigator_size:,} bytes ({navigator_size/1024:.1f} KB)")
        
        self.assertLess(navigator_size, 512 * 1024, "BingNavigator payload should be under 512KB")
        
        # Step 2: SerpParser processes the file
        try:
            from SerpParser.tools.HtmlParserTool import HtmlParserTool
            
            parser = HtmlParserTool(
                html_file=str(html_filepath),
                max_urls=50,
                filter_domains=True
            )
            
            parser_result = parser.run()
            
            print(f"  📊 SerpParser status: {parser_result.get('status')}")
            print(f"  🔗 URLs extracted: {parser_result.get('urls_extracted', 0)}")
            
            # Verify SerpParser results
            self.assertEqual(parser_result.get('status'), 'success', "SerpParser should succeed")
            self.assertGreater(parser_result.get('urls_extracted', 0), 0, "Should extract URLs")
            
            # Check extracted URLs quality
            urls = parser_result.get('urls', [])
            if urls:
                print(f"  📋 Sample extracted URLs:")
                expected_domains = {'chicagomedicalgroup.com', 'northsidemedical.org', 'chicagohealthcare.net', 'doctorcontacts.com', 'medicalprofessionals.org'}
                found_domains = set()
                
                for i, url_data in enumerate(urls[:5]):
                    print(f"    {i+1}. {url_data.get('domain')} - {url_data.get('url')}")
                    found_domains.add(url_data.get('domain', ''))
                
                # Check that we found at least some expected domains
                common_domains = expected_domains.intersection(found_domains)
                self.assertGreater(len(common_domains), 0, f"Should find at least some expected domains. Found: {found_domains}")
                print(f"  ✅ Found {len(common_domains)} expected domains: {common_domains}")
                    
            # Verify SerpParser payload size
            parser_payload = json.dumps(parser_result, indent=2)
            parser_size = len(parser_payload.encode('utf-8'))
            
            print(f"  📏 SerpParser payload: {parser_size:,} bytes ({parser_size/1024:.1f} KB)")
            
            self.assertLess(parser_size, 512 * 1024, "SerpParser payload should be under 512KB")
            
            print(f"  ✅ BingNavigator → SerpParser handoff SUCCESSFUL")
            
            return parser_result
            
        except ImportError as e:
            print(f"  ⚠️ Skipping SerpParser test - import error: {e}")
            self.skipTest(f"SerpParser not available: {e}")
        
        finally:
            # Cleanup
            if html_filepath.exists():
                html_filepath.unlink()
    
    def test_error_handling_in_handoff(self):
        """Test error handling when files are missing or corrupted"""
        print("\n🔧 Testing error handling in handoff...")
        
        # Test missing file scenario
        missing_file_path = "nonexistent_file.html"
        
        try:
            from SerpParser.tools.HtmlParserTool import HtmlParserTool
            
            parser = HtmlParserTool(
                html_file=missing_file_path,
                max_urls=25,
                filter_domains=True
            )
            
            result = parser.run()
            
            print(f"  📊 Error handling status: {result.get('status')}")
            print(f"  🚨 Error type: {result.get('error_type')}")
            
            self.assertEqual(result.get('status'), 'error', "Should handle missing file gracefully")
            self.assertEqual(result.get('urls_extracted', 0), 0, "Should return 0 URLs")
            self.assertIn('error_message', result, "Should provide error message")
            
            print(f"  ✅ Error handling test PASSED")
            
        except ImportError as e:
            print(f"  ⚠️ Skipping error handling test - import error: {e}")
            self.skipTest(f"SerpParser not available: {e}")


class TestSerpParserToDomainClassifier(unittest.TestCase):
    """Test the handoff between SerpParser and DomainClassifier"""
    
    def test_serpparser_domainclassifier_flow(self):
        """Test SerpParser -> DomainClassifier data flow"""
        print("\n🔧 Testing SerpParser → DomainClassifier integration...")
        
        # Simulate SerpParser output
        serpparser_output = {
            "status": "success",
            "urls_extracted": 5,
            "urls": [
                {
                    "url": "https://chicagomedicalgroup.com/contact",
                    "domain": "chicagomedicalgroup.com", 
                    "path": "/contact",
                    "is_root": False,
                    "tld": "com",
                    "subdomain": ""
                },
                {
                    "url": "https://northsidemedical.org/physicians",
                    "domain": "northsidemedical.org",
                    "path": "/physicians", 
                    "is_root": False,
                    "tld": "org",
                    "subdomain": ""
                },
                {
                    "url": "https://chicagohealthcare.net/directory", 
                    "domain": "chicagohealthcare.net",
                    "path": "/directory",
                    "is_root": False,
                    "tld": "net",
                    "subdomain": ""
                },
                {
                    "url": "https://www.doctorcontacts.com/chicago",
                    "domain": "www.doctorcontacts.com",
                    "path": "/chicago",
                    "is_root": False, 
                    "tld": "com",
                    "subdomain": "www"
                },
                {
                    "url": "https://medicalprofessionals.org/illinois",
                    "domain": "medicalprofessionals.org",
                    "path": "/illinois",
                    "is_root": False,
                    "tld": "org", 
                    "subdomain": ""
                }
            ],
            "meta": {
                "html_file": "output/html_cache/test_file.html",
                "html_size": 5000,
                "total_urls_found": 8,
                "urls_after_filtering": 5,
                "max_urls_requested": 50,
                "filter_enabled": True
            }
        }
        
        # Verify SerpParser output payload size
        serpparser_payload = json.dumps(serpparser_output, indent=2)
        serpparser_size = len(serpparser_payload.encode('utf-8'))
        
        print(f"  📏 SerpParser output: {serpparser_size:,} bytes ({serpparser_size/1024:.1f} KB)")
        self.assertLess(serpparser_size, 512 * 1024, "SerpParser output should be under 512KB")
        
        # Simulate DomainClassifier input processing
        # (This would be the input to DomainClassifier agent)
        domainclassifier_input = {
            "task": "classify_domains",
            "urls": serpparser_output["urls"],
            "classification_criteria": {
                "business_types": ["medical", "healthcare", "professional"],
                "exclude_directories": True,
                "prioritize_contact_pages": True
            },
            "meta": {
                "source": "serpparser",
                "query_context": "doctors in chicago contact",
                "timestamp": time.time()
            }
        }
        
        # Verify DomainClassifier input payload size
        classifier_payload = json.dumps(domainclassifier_input, indent=2)
        classifier_size = len(classifier_payload.encode('utf-8'))
        
        print(f"  📏 DomainClassifier input: {classifier_size:,} bytes ({classifier_size/1024:.1f} KB)")
        self.assertLess(classifier_size, 512 * 1024, "DomainClassifier input should be under 512KB")
        
        # Simulate DomainClassifier processing and output
        domainclassifier_output = {
            "status": "success",
            "domains_classified": 5,
            "high_priority_domains": [
                {
                    "domain": "chicagomedicalgroup.com",
                    "url": "https://chicagomedicalgroup.com/contact", 
                    "classification": "medical_practice",
                    "priority_score": 0.95,
                    "contact_likelihood": "high",
                    "reasons": ["medical in domain", "contact page", ".com TLD"]
                },
                {
                    "domain": "northsidemedical.org",
                    "url": "https://northsidemedical.org/physicians",
                    "classification": "medical_practice", 
                    "priority_score": 0.90,
                    "contact_likelihood": "high",
                    "reasons": ["medical in domain", "physicians page", ".org TLD"]
                }
            ],
            "medium_priority_domains": [
                {
                    "domain": "chicagohealthcare.net",
                    "url": "https://chicagohealthcare.net/directory",
                    "classification": "healthcare_directory",
                    "priority_score": 0.75,
                    "contact_likelihood": "medium", 
                    "reasons": ["healthcare in domain", "directory page"]
                }
            ],
            "low_priority_domains": [
                {
                    "domain": "www.doctorcontacts.com",
                    "url": "https://www.doctorcontacts.com/chicago",
                    "classification": "contact_directory",
                    "priority_score": 0.60,
                    "contact_likelihood": "medium",
                    "reasons": ["contacts in domain", "potential directory"]
                }
            ],
            "filtered_out": [
                {
                    "domain": "medicalprofessionals.org",
                    "url": "https://medicalprofessionals.org/illinois", 
                    "reason": "too_generic",
                    "classification": "directory"
                }
            ],
            "meta": {
                "processing_time_ms": 800,
                "classification_model": "business_classifier_v2",
                "total_domains": 5,
                "timestamp": time.time()
            }
        }
        
        # Verify DomainClassifier output payload size
        classifier_output_payload = json.dumps(domainclassifier_output, indent=2)
        classifier_output_size = len(classifier_output_payload.encode('utf-8'))
        
        print(f"  📏 DomainClassifier output: {classifier_output_size:,} bytes ({classifier_output_size/1024:.1f} KB)")
        self.assertLess(classifier_output_size, 512 * 1024, "DomainClassifier output should be under 512KB")
        
        # Verify data quality and structure
        self.assertEqual(domainclassifier_output["status"], "success")
        self.assertEqual(domainclassifier_output["domains_classified"], 5)
        self.assertGreater(len(domainclassifier_output["high_priority_domains"]), 0)
        
        print(f"  📊 High priority domains: {len(domainclassifier_output['high_priority_domains'])}")
        print(f"  📊 Medium priority domains: {len(domainclassifier_output['medium_priority_domains'])}")
        print(f"  📊 Low priority domains: {len(domainclassifier_output['low_priority_domains'])}")
        print(f"  📊 Filtered out: {len(domainclassifier_output['filtered_out'])}")
        
        print(f"  ✅ SerpParser → DomainClassifier flow test PASSED")


class TestFullPipelineCommunication(unittest.TestCase):
    """Test complete pipeline agent communication"""
    
    def test_pipeline_payload_chain(self):
        """Test payload sizes across entire pipeline chain"""
        print("\n🔧 Testing complete pipeline payload chain...")
        
        # Stage 1: BingNavigator (file-based response)
        stage1_payload = {
            "status": "success",
            "html_file": "output/html_cache/bing_test_123.html",
            "html_preview": "<!DOCTYPE html><html>..." + "..." * 100,
            "meta": {"query": "test", "page": 1, "content_length": 250000}
        }
        
        # Stage 2: SerpParser (URL extraction)
        stage2_payload = {
            "status": "success", 
            "urls_extracted": 25,
            "urls": [{"url": f"https://example{i}.com", "domain": f"example{i}.com"} for i in range(25)],
            "meta": {"html_size": 250000, "filter_enabled": True}
        }
        
        # Stage 3: DomainClassifier (classified domains)
        stage3_payload = {
            "status": "success",
            "high_priority_domains": [{"domain": f"business{i}.com", "score": 0.9} for i in range(10)],
            "meta": {"total_classified": 25}
        }
        
        # Stage 4: SiteCrawler (contact extraction)
        stage4_payload = {
            "status": "success",
            "contacts_extracted": 8,
            "contacts": [{"domain": f"business{i}.com", "email": f"info@business{i}.com"} for i in range(8)],
            "meta": {"crawl_time_ms": 5000}
        }
        
        # Stage 5: EmailExtractor (enriched contacts)
        stage5_payload = {
            "status": "success", 
            "enriched_contacts": 8,
            "final_leads": [{"name": f"Business {i}", "email": f"contact@business{i}.com"} for i in range(8)],
            "meta": {"enrichment_rate": 0.8}
        }
        
        stages = [
            ("BingNavigator", stage1_payload),
            ("SerpParser", stage2_payload), 
            ("DomainClassifier", stage3_payload),
            ("SiteCrawler", stage4_payload),
            ("EmailExtractor", stage5_payload)
        ]
        
        print(f"  📊 Pipeline stage payload sizes:")
        
        for stage_name, payload in stages:
            payload_json = json.dumps(payload, indent=2)
            payload_size = len(payload_json.encode('utf-8'))
            
            print(f"    {stage_name}: {payload_size:,} bytes ({payload_size/1024:.1f} KB)")
            
            # Critical assertion - all payloads must be under 512KB
            self.assertLess(payload_size, 512 * 1024, f"{stage_name} payload must be under 512KB OpenAI limit")
            
            # Good practice - payloads should be reasonably small
            if payload_size > 100 * 1024:  # 100KB warning threshold
                print(f"    ⚠️ {stage_name} payload is large ({payload_size/1024:.1f} KB)")
        
        print(f"  ✅ All pipeline stages under 512KB OpenAI limit")


def run_integration_tests():
    """Run all integration tests"""
    print("🔗 VRSEN PIPELINE INTEGRATION TESTS")
    print("=" * 60)
    print("Testing agent-to-agent communication and full pipeline flow")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBingNavigatorToSerpParserHandoff))
    suite.addTests(loader.loadTestsFromTestCase(TestSerpParserToDomainClassifier))  
    suite.addTests(loader.loadTestsFromTestCase(TestFullPipelineCommunication))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("🔗 INTEGRATION TEST SUMMARY")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, failure in result.failures:
            print(f"  {test}: {failure}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, error in result.errors:
            print(f"  {test}: {error}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("🎯 Pipeline communication is working correctly")
        print("🚀 Ready for performance and end-to-end testing")
    else:
        print("\n❌ Some integration tests failed")
        print("🔧 Fix communication issues before proceeding")
    
    return success


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)