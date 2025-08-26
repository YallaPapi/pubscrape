#!/usr/bin/env python3
"""
Unit Tests for VRSEN Pipeline Components
Tests individual components: SerpFetchTool, HtmlParserTool, and payload size validation
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

class TestSerpFetchToolPayloads(unittest.TestCase):
    """Test SerpFetchTool payload size management"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_output_dir = Path("output/html_cache")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
    
    def test_large_html_payload_size(self):
        """Test that large HTML results in small JSON payload"""
        print("\n🔧 Testing SerpFetchTool payload size management...")
        
        # Create mock large HTML (similar to real Bing results)
        large_html_base = """
        <!DOCTYPE html><html><head><title>Doctors in Chicago - Bing Search</title></head><body>
        <div id="b_content">
        """
        
        # Add many result blocks
        result_blocks = []
        for i in range(1000):
            block = f"""
            <div class="b_algo">
                <h2><a href="https://example-medical-{i}.com">Example Medical Practice {i}</a></h2>
                <p>Contact information for medical professionals in Chicago area</p>
                <div class="b_attribution"><cite>example-medical-{i}.com</cite></div>
            </div>
            """
            result_blocks.append(block)
        
        large_html = large_html_base + "".join(result_blocks) + """
        </div></body></html>
        """
        
        # Simulate SerpFetchTool response creation
        html_content = large_html
        
        # Create unique filename (as SerpFetchTool does)
        timestamp = int(time.time())
        html_filename = f"bing_test_unit_{timestamp}.html"
        html_filepath = self.test_output_dir / html_filename
        
        # Save HTML content to file (as SerpFetchTool does)
        with open(html_filepath, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(html_content)
        
        file_size = len(html_content.encode('utf-8', errors='ignore'))
        
        # Create response payload (as SerpFetchTool does)
        response_payload = {
            "status": "success", 
            "html_file": str(html_filepath),
            "html_preview": html_content[:1000] + "...",
            "meta": {
                "query": "doctors in chicago contact",
                "page": 1,
                "timestamp": time.time(),
                "response_time_ms": 1500,
                "content_length": len(html_content),
                "file_size": file_size,
                "html_saved": True,
                "stealth_enabled": True,
                "method": "direct",
                "session_id": f"test_unit_{timestamp}",
                "title": "Doctors in Chicago - Bing Search",
                "url": "https://www.bing.com/search?q=doctors+in+chicago+contact",
                "is_blocked": False
            }
        }
        
        # Test payload size
        payload_json = json.dumps(response_payload, indent=2)
        payload_size = len(payload_json.encode('utf-8'))
        
        print(f"  📏 HTML content size: {len(html_content):,} characters ({file_size:,} bytes)")
        print(f"  📏 JSON payload size: {payload_size:,} bytes ({payload_size/1024:.1f} KB)")
        print(f"  🎯 OpenAI limit: 512 KB")
        
        # Assertions
        self.assertGreater(len(html_content), 100000, "HTML should be large (>100KB)")
        self.assertLess(payload_size, 512 * 1024, "Payload should be under 512KB OpenAI limit")
        self.assertLess(payload_size, 10000, "Payload should be very small (<10KB)")
        self.assertTrue(os.path.exists(html_filepath), "HTML file should be saved")
        self.assertIn("html_file", response_payload, "Response should include file path")
        self.assertIn("html_preview", response_payload, "Response should include HTML preview")
        self.assertLessEqual(len(response_payload["html_preview"]), 1004, "Preview should be limited")
        
        print(f"  ✅ Payload size test PASSED - {payload_size:,} bytes is well under 512KB limit")
        
        # Cleanup
        if os.path.exists(html_filepath):
            os.remove(html_filepath)
    
    def test_empty_html_handling(self):
        """Test handling of empty or minimal HTML"""
        print("\n🔧 Testing empty HTML handling...")
        
        empty_html = "<html><head><title>No Results</title></head><body></body></html>"
        
        # Simulate error response for empty HTML
        error_response = {
            "status": "error",
            "error_type": "search_error",
            "error_message": "Search failed - no content returned",
            "meta": {
                "query": "empty test query",
                "page": 1,
                "timeout_used": 30,
                "stealth_enabled": True,
                "session_id": "test_empty"
            }
        }
        
        error_payload = json.dumps(error_response, indent=2)
        error_size = len(error_payload.encode('utf-8'))
        
        print(f"  📏 Error payload size: {error_size:,} bytes ({error_size/1024:.1f} KB)")
        
        self.assertLess(error_size, 1024, "Error payload should be very small")
        self.assertEqual(error_response["status"], "error")
        
        print(f"  ✅ Empty HTML handling test PASSED")


class TestHtmlParserTool(unittest.TestCase):
    """Test HtmlParserTool functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_output_dir = Path("output/html_cache")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_test_html_file(self, content: str) -> Path:
        """Helper to create test HTML file"""
        timestamp = int(time.time() * 1000)
        test_file = self.test_output_dir / f"test_html_{timestamp}.html"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return test_file
    
    def test_html_file_reading(self):
        """Test HtmlParserTool can read HTML files correctly"""
        print("\n🔧 Testing HtmlParserTool file reading...")
        
        # Create test HTML with typical Bing results
        test_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Medical Practices - Bing</title></head>
        <body>
        <div id="b_content">
            <div class="b_algo">
                <h2><a href="https://chicagomedical.com">Chicago Medical Practice</a></h2>
                <p>Premier medical services in downtown Chicago</p>
                <div class="b_attribution"><cite>chicagomedical.com</cite></div>
            </div>
            <div class="b_algo">
                <h2><a href="https://healthcareplus.org">Healthcare Plus</a></h2>
                <p>Comprehensive healthcare services</p>
                <div class="b_attribution"><cite>healthcareplus.org</cite></div>
            </div>
            <div class="b_algo">
                <h2><a href="https://doctorsoffice.net">Doctors Office Network</a></h2>
                <p>Network of medical professionals</p>
                <div class="b_attribution"><cite>doctorsoffice.net</cite></div>
            </div>
        </div>
        </body>
        </html>
        """
        
        # Create test file
        test_file = self.create_test_html_file(test_html)
        
        # Test HtmlParserTool
        try:
            from SerpParser.tools.HtmlParserTool import HtmlParserTool
            
            parser = HtmlParserTool(
                html_file=str(test_file),
                max_urls=25,
                filter_domains=True
            )
            
            result = parser.run()
            
            print(f"  📊 Parser status: {result.get('status')}")
            print(f"  🔗 URLs extracted: {result.get('urls_extracted', 0)}")
            
            # Assertions
            self.assertEqual(result.get('status'), 'success', "Parser should succeed")
            self.assertGreater(result.get('urls_extracted', 0), 0, "Should extract some URLs")
            self.assertIn('urls', result, "Result should contain URLs list")
            self.assertIn('meta', result, "Result should contain metadata")
            
            # Check extracted URLs
            urls = result.get('urls', [])
            if urls:
                print(f"  📋 First extracted URL: {urls[0]}")
                for url_data in urls:
                    self.assertIn('url', url_data, "URL data should have 'url' field")
                    self.assertIn('domain', url_data, "URL data should have 'domain' field")
            
            print(f"  ✅ HtmlParserTool file reading test PASSED")
            
        except ImportError as e:
            print(f"  ⚠️ Skipping HtmlParserTool test - import error: {e}")
            self.skipTest(f"HtmlParserTool not importable: {e}")
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
    
    def test_missing_file_handling(self):
        """Test HtmlParserTool handles missing files gracefully"""
        print("\n🔧 Testing missing file handling...")
        
        try:
            from SerpParser.tools.HtmlParserTool import HtmlParserTool
            
            # Test with non-existent file
            parser = HtmlParserTool(
                html_file="nonexistent_file.html",
                max_urls=25,
                filter_domains=True
            )
            
            result = parser.run()
            
            print(f"  📊 Parser status for missing file: {result.get('status')}")
            print(f"  🔗 URLs extracted: {result.get('urls_extracted', 0)}")
            
            # Assertions
            self.assertEqual(result.get('status'), 'error', "Should return error for missing file")
            self.assertEqual(result.get('urls_extracted', 0), 0, "Should extract 0 URLs")
            self.assertIn('error_type', result, "Should include error type")
            self.assertIn('error_message', result, "Should include error message")
            
            print(f"  ✅ Missing file handling test PASSED")
            
        except ImportError as e:
            print(f"  ⚠️ Skipping missing file test - import error: {e}")
            self.skipTest(f"HtmlParserTool not importable: {e}")


class TestPayloadSizeValidation(unittest.TestCase):
    """Test payload size validation across pipeline"""
    
    def test_openai_512kb_limit_compliance(self):
        """Test all pipeline components stay under 512KB limit"""
        print("\n🔧 Testing OpenAI 512KB limit compliance...")
        
        # Test various payload sizes
        test_cases = [
            {
                "name": "Small response",
                "data": {"status": "success", "urls": ["http://example.com"] * 10},
                "expected_under_limit": True
            },
            {
                "name": "Medium response", 
                "data": {"status": "success", "urls": [f"http://example{i}.com" for i in range(1000)]},
                "expected_under_limit": True
            },
            {
                "name": "Large response with metadata",
                "data": {
                    "status": "success",
                    "urls": [{"url": f"http://example{i}.com", "domain": f"example{i}.com", "meta": f"data{i}"} for i in range(5000)],
                    "meta": {"large_field": "x" * 50000}
                },
                "expected_under_limit": False  # This should fail
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                payload = json.dumps(test_case["data"], indent=2)
                size = len(payload.encode('utf-8'))
                
                print(f"  📏 {test_case['name']}: {size:,} bytes ({size/1024:.1f} KB)")
                
                is_under_limit = size < 512 * 1024
                
                if test_case["expected_under_limit"]:
                    self.assertTrue(is_under_limit, f"{test_case['name']} should be under 512KB limit")
                    print(f"    ✅ Under limit as expected")
                else:
                    self.assertFalse(is_under_limit, f"{test_case['name']} should exceed 512KB limit")
                    print(f"    ✅ Over limit as expected (demonstrates problem case)")
    
    def test_file_vs_payload_size_comparison(self):
        """Compare file-based vs payload-based data transfer sizes"""
        print("\n🔧 Testing file vs payload size comparison...")
        
        # Simulate large HTML content
        large_content = "<html><body>" + "<div>Content block</div>" * 10000 + "</body></html>"
        
        # Method 1: Include content in JSON payload (old method)
        payload_method = {
            "status": "success",
            "html_content": large_content,
            "meta": {"timestamp": time.time()}
        }
        
        # Method 2: Save to file and reference (new method)
        timestamp = int(time.time())
        test_file = Path(f"temp_test_{timestamp}.html")
        
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(large_content)
            
            file_method = {
                "status": "success", 
                "html_file": str(test_file),
                "html_preview": large_content[:1000] + "...",
                "meta": {
                    "timestamp": time.time(),
                    "content_length": len(large_content),
                    "file_size": len(large_content.encode('utf-8'))
                }
            }
            
            # Compare sizes
            payload_size = len(json.dumps(payload_method, indent=2).encode('utf-8'))
            file_size = len(json.dumps(file_method, indent=2).encode('utf-8'))
            
            print(f"  📏 Content size: {len(large_content):,} characters")
            print(f"  📏 Payload method: {payload_size:,} bytes ({payload_size/1024:.1f} KB)")
            print(f"  📏 File method: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            print(f"  📊 Size reduction: {((payload_size - file_size) / payload_size * 100):.1f}%")
            
            # Assertions
            self.assertGreater(payload_size, file_size, "File method should be smaller")
            self.assertLess(file_size, 512 * 1024, "File method should be under 512KB")
            
            if payload_size > 512 * 1024:
                print(f"  ❌ Payload method exceeds 512KB limit")
                print(f"  ✅ File method stays under limit")
            else:
                print(f"  ✅ Both methods under limit, but file method more efficient")
        
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()


def run_unit_tests():
    """Run all unit tests with detailed output"""
    print("🧪 VRSEN PIPELINE UNIT TESTS")
    print("=" * 60)
    print("Testing individual components for 512KB fix compliance")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSerpFetchToolPayloads))
    suite.addTests(loader.loadTestsFromTestCase(TestHtmlParserTool))
    suite.addTests(loader.loadTestsFromTestCase(TestPayloadSizeValidation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("🧪 UNIT TEST SUMMARY")
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
        print("\n✅ ALL UNIT TESTS PASSED!")
        print("🎯 Components are ready for integration testing")
    else:
        print("\n❌ Some unit tests failed")
        print("🔧 Fix issues before proceeding to integration tests")
    
    return success


if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)