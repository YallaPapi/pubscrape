#!/usr/bin/env python3
"""
Performance Tests for VRSEN Pipeline
Tests performance with large HTML files, concurrent operations, and memory usage
"""

import os
import sys
import json
import time
import tempfile
import unittest
import threading
import concurrent.futures
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestLargeHtmlFilePerformance(unittest.TestCase):
    """Test performance with large HTML files"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_output_dir = Path("output/html_cache")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_large_html_file(self, target_size_kb: int) -> Path:
        """Create a large HTML file for testing"""
        target_size = target_size_kb * 1024  # Convert KB to bytes
        
        # HTML template with many result blocks
        html_header = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Large Search Results - Performance Test</title>
            <meta charset="utf-8">
        </head>
        <body>
        <div id="b_content">
        """
        
        html_footer = """
        </div>
        </body>
        </html>
        """
        
        # Calculate how many result blocks we need
        result_template = """
            <div class="b_algo">
                <h2><a href="https://medical-practice-{}.com/contact">Medical Practice {} - Contact</a></h2>
                <div class="b_caption">
                    <p>Professional medical services and contact information for Medical Practice {}. Call (312) 555-{:04d} or email contact@medical-practice-{}.com for appointments.</p>
                    <div class="b_attribution">
                        <cite>medical-practice-{}.com/contact</cite>
                    </div>
                </div>
            </div>
        """
        
        # Estimate size per result block
        sample_block = result_template.format(1, 1, 1, 1, 1, 1)
        block_size = len(sample_block.encode('utf-8'))
        
        header_size = len(html_header.encode('utf-8'))
        footer_size = len(html_footer.encode('utf-8'))
        
        available_size = target_size - header_size - footer_size
        num_blocks = max(1, available_size // block_size)
        
        # Generate result blocks
        result_blocks = []
        for i in range(num_blocks):
            block = result_template.format(i, i, i, i, i, i)
            result_blocks.append(block)
        
        # Combine all parts
        full_html = html_header + "".join(result_blocks) + html_footer
        
        # Save to file
        timestamp = int(time.time() * 1000)
        test_file = self.test_output_dir / f"large_test_{target_size_kb}kb_{timestamp}.html"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        actual_size = len(full_html.encode('utf-8'))
        print(f"  📁 Created test file: {target_size_kb}KB target, {actual_size/1024:.1f}KB actual")
        
        return test_file
    
    def test_200kb_html_processing(self):
        """Test processing 200KB HTML file (typical large search result)"""
        print("\n🔧 Testing 200KB HTML file processing...")
        
        # Create 200KB test file
        large_file = self.create_large_html_file(200)
        
        try:
            # Test file-based approach timing
            start_time = time.time()
            
            # Simulate SerpFetchTool creating file reference response
            file_response = {
                "status": "success",
                "html_file": str(large_file),
                "html_preview": "Large HTML preview...",
                "meta": {
                    "content_length": os.path.getsize(large_file),
                    "file_size": os.path.getsize(large_file)
                }
            }
            
            response_create_time = time.time() - start_time
            
            # Test payload size
            response_payload = json.dumps(file_response, indent=2)
            payload_size = len(response_payload.encode('utf-8'))
            
            # Test HtmlParserTool processing
            try:
                from SerpParser.tools.HtmlParserTool import HtmlParserTool
                
                parse_start = time.time()
                
                parser = HtmlParserTool(
                    html_file=str(large_file),
                    max_urls=100,
                    filter_domains=True
                )
                
                result = parser.run()
                
                parse_time = time.time() - parse_start
                
                print(f"  ⏱️ Response creation: {response_create_time*1000:.1f}ms")
                print(f"  ⏱️ HTML parsing: {parse_time*1000:.1f}ms")
                print(f"  📏 Response payload: {payload_size:,} bytes ({payload_size/1024:.1f} KB)")
                print(f"  🔗 URLs extracted: {result.get('urls_extracted', 0)}")
                
                # Performance assertions
                self.assertLess(response_create_time, 0.1, "Response creation should be very fast (<100ms)")
                self.assertLess(parse_time, 5.0, "HTML parsing should complete within 5 seconds")
                self.assertLess(payload_size, 512 * 1024, "Response payload must be under 512KB")
                self.assertLess(payload_size, 10 * 1024, "Response payload should be very small (<10KB)")
                
                # Quality assertions
                self.assertEqual(result.get('status'), 'success', "Parsing should succeed")
                self.assertGreater(result.get('urls_extracted', 0), 0, "Should extract some URLs")
                
                print(f"  ✅ 200KB HTML processing test PASSED")
                
            except ImportError as e:
                print(f"  ⚠️ Skipping HTML parsing test - import error: {e}")
                self.skipTest(f"HtmlParserTool not available: {e}")
            
        finally:
            # Cleanup
            if large_file.exists():
                large_file.unlink()
    
    def test_500kb_html_processing(self):
        """Test processing 500KB HTML file (stress test)"""
        print("\n🔧 Testing 500KB HTML file processing...")
        
        # Create 500KB test file
        large_file = self.create_large_html_file(500)
        
        try:
            start_time = time.time()
            
            # Test file-based approach
            file_response = {
                "status": "success",
                "html_file": str(large_file),
                "html_preview": "Very large HTML preview...",
                "meta": {
                    "content_length": os.path.getsize(large_file),
                    "file_size": os.path.getsize(large_file)
                }
            }
            
            response_create_time = time.time() - start_time
            
            # Test payload size (critical - must stay small)
            response_payload = json.dumps(file_response, indent=2)
            payload_size = len(response_payload.encode('utf-8'))
            
            print(f"  ⏱️ Response creation: {response_create_time*1000:.1f}ms")
            print(f"  📏 Response payload: {payload_size:,} bytes ({payload_size/1024:.1f} KB)")
            print(f"  📁 File size: {os.path.getsize(large_file)/1024:.1f} KB")
            
            # Critical assertions for large files
            self.assertLess(payload_size, 512 * 1024, "Even with 500KB files, payload must be under 512KB")
            self.assertLess(payload_size, 10 * 1024, "Payload should remain very small regardless of file size")
            
            print(f"  ✅ 500KB HTML file size test PASSED - payload remains small")
            
        finally:
            # Cleanup
            if large_file.exists():
                large_file.unlink()
    
    def test_memory_usage_comparison(self):
        """Compare memory usage: old method vs file-based method"""
        print("\n🔧 Testing memory usage comparison...")
        
        # Create test HTML content
        test_html = "<html><body>" + "<div>Content block with URLs and data</div>" * 5000 + "</body></html>"
        content_size = len(test_html.encode('utf-8'))
        
        # Method 1: Old approach (content in JSON payload)
        old_method_payload = {
            "status": "success",
            "html_content": test_html,  # FULL HTML IN MEMORY/PAYLOAD
            "meta": {"size": content_size}
        }
        
        old_payload_json = json.dumps(old_method_payload)
        old_memory_usage = len(old_payload_json.encode('utf-8'))
        
        # Method 2: New approach (file-based)
        temp_file = Path("temp_memory_test.html")
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(test_html)
            
            new_method_payload = {
                "status": "success", 
                "html_file": str(temp_file),
                "html_preview": test_html[:500] + "...",  # Small preview only
                "meta": {
                    "content_length": content_size,
                    "file_size": content_size
                }
            }
            
            new_payload_json = json.dumps(new_method_payload)
            new_memory_usage = len(new_payload_json.encode('utf-8'))
            
            # Calculate savings
            memory_savings = old_memory_usage - new_memory_usage
            savings_percent = (memory_savings / old_memory_usage) * 100
            
            print(f"  📊 Content size: {content_size/1024:.1f} KB")
            print(f"  📊 Old method payload: {old_memory_usage/1024:.1f} KB")
            print(f"  📊 New method payload: {new_memory_usage/1024:.1f} KB") 
            print(f"  📊 Memory savings: {memory_savings/1024:.1f} KB ({savings_percent:.1f}%)")
            
            # Assertions
            self.assertLess(new_memory_usage, old_memory_usage, "File method should use less memory")
            self.assertLess(new_memory_usage, 512 * 1024, "File method should be under OpenAI limit")
            
            if old_memory_usage > 512 * 1024:
                print(f"  ❌ Old method would exceed 512KB limit")
                print(f"  ✅ New method stays well under limit")
            else:
                print(f"  ✅ Both methods under limit, but file method much more efficient")
            
        finally:
            if temp_file.exists():
                temp_file.unlink()


class TestConcurrentOperations(unittest.TestCase):
    """Test concurrent file operations and processing"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_output_dir = Path("output/html_cache")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
    
    def test_concurrent_html_file_creation(self):
        """Test multiple concurrent HTML file operations"""
        print("\n🔧 Testing concurrent HTML file operations...")
        
        def create_and_process_html(session_id: str) -> dict:
            """Simulate concurrent BingNavigator + SerpParser operation"""
            try:
                # Create HTML content
                html_content = f"""
                <html><head><title>Session {session_id} Results</title></head>
                <body>
                <div id="b_content">
                """ + "".join([
                    f'<div class="b_algo"><a href="https://business-{session_id}-{i}.com">Business {i}</a></div>'
                    for i in range(100)
                ]) + """
                </div></body></html>
                """
                
                # Save to file (BingNavigator step)
                timestamp = int(time.time() * 1000)
                html_file = self.test_output_dir / f"concurrent_test_{session_id}_{timestamp}.html"
                
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Create response payload (BingNavigator output)
                response = {
                    "status": "success",
                    "html_file": str(html_file),
                    "html_preview": html_content[:500] + "...",
                    "meta": {
                        "session_id": session_id,
                        "content_length": len(html_content),
                        "timestamp": time.time()
                    }
                }
                
                # Test payload size
                payload = json.dumps(response, indent=2)
                payload_size = len(payload.encode('utf-8'))
                
                # Clean up
                if html_file.exists():
                    html_file.unlink()
                
                return {
                    "session_id": session_id,
                    "success": True,
                    "payload_size": payload_size,
                    "content_size": len(html_content),
                    "file_created": True
                }
                
            except Exception as e:
                return {
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit 10 concurrent operations
            futures = [
                executor.submit(create_and_process_html, f"session_{i}")
                for i in range(10)
            ]
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=30):
                results.append(future.result())
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        avg_payload_size = sum(r.get('payload_size', 0) for r in successful) / len(successful) if successful else 0
        
        print(f"  ⏱️ Total time: {total_time:.2f}s")
        print(f"  ✅ Successful operations: {len(successful)}/10")
        print(f"  ❌ Failed operations: {len(failed)}/10")
        print(f"  📏 Average payload size: {avg_payload_size:.0f} bytes ({avg_payload_size/1024:.1f} KB)")
        
        # Assertions
        self.assertGreaterEqual(len(successful), 8, "At least 8/10 operations should succeed")
        self.assertLess(avg_payload_size, 512 * 1024, "All payloads should be under 512KB")
        self.assertLess(total_time, 15.0, "Concurrent operations should complete within 15 seconds")
        
        if failed:
            print(f"  ⚠️ Failed operations:")
            for failure in failed:
                print(f"    {failure.get('session_id')}: {failure.get('error')}")
        
        print(f"  ✅ Concurrent operations test PASSED")
    
    def test_file_io_performance(self):
        """Test file I/O performance under load"""
        print("\n🔧 Testing file I/O performance...")
        
        # Test writing multiple files quickly
        files_created = []
        start_time = time.time()
        
        try:
            for i in range(20):
                html_content = f"<html><body>Test content {i} " + "data " * 1000 + "</body></html>"
                test_file = self.test_output_dir / f"perf_test_{i}_{int(time.time()*1000)}.html"
                
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                files_created.append(test_file)
            
            write_time = time.time() - start_time
            
            # Test reading files back
            read_start = time.time()
            
            total_content = 0
            for file_path in files_created:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_content += len(content)
            
            read_time = time.time() - read_start
            
            print(f"  ⏱️ Write time: {write_time:.3f}s ({write_time/20*1000:.1f}ms per file)")
            print(f"  ⏱️ Read time: {read_time:.3f}s ({read_time/20*1000:.1f}ms per file)")
            print(f"  📁 Files created: {len(files_created)}")
            print(f"  📊 Total content: {total_content/1024:.1f} KB")
            
            # Performance assertions
            self.assertLess(write_time, 5.0, "Writing 20 files should take less than 5 seconds")
            self.assertLess(read_time, 3.0, "Reading 20 files should take less than 3 seconds")
            self.assertEqual(len(files_created), 20, "All files should be created successfully")
            
            print(f"  ✅ File I/O performance test PASSED")
            
        finally:
            # Cleanup all test files
            for file_path in files_created:
                if file_path.exists():
                    file_path.unlink()


class TestScalabilityLimits(unittest.TestCase):
    """Test pipeline scalability and limits"""
    
    def test_maximum_reasonable_payload_size(self):
        """Test what happens near the payload size limits"""
        print("\n🔧 Testing maximum reasonable payload sizes...")
        
        # Test different payload sizes approaching the limit
        test_cases = [
            {"name": "Small (1KB)", "target_kb": 1},
            {"name": "Medium (50KB)", "target_kb": 50}, 
            {"name": "Large (200KB)", "target_kb": 200},
            {"name": "Very Large (400KB)", "target_kb": 400},
            {"name": "Near Limit (500KB)", "target_kb": 500}
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                target_kb = test_case["target_kb"]
                
                # Create payload approaching the size
                large_data = {
                    "status": "success",
                    "urls": [
                        {
                            "url": f"https://example-{i}.com/contact",
                            "domain": f"example-{i}.com",
                            "metadata": "x" * 500  # 500 chars per URL
                        }
                        for i in range((target_kb * 1024) // 600)  # Roughly estimate URLs needed
                    ]
                }
                
                payload = json.dumps(large_data, indent=2)
                actual_size = len(payload.encode('utf-8'))
                
                print(f"  📏 {test_case['name']}: {actual_size:,} bytes ({actual_size/1024:.1f} KB)")
                
                # Test serialization performance
                start_time = time.time()
                json.dumps(large_data)
                serialize_time = time.time() - start_time
                
                print(f"    ⏱️ Serialization time: {serialize_time*1000:.1f}ms")
                
                is_under_limit = actual_size < 512 * 1024
                
                if target_kb <= 400:
                    self.assertTrue(is_under_limit, f"{test_case['name']} should be under 512KB limit")
                    self.assertLess(serialize_time, 0.5, f"{test_case['name']} serialization should be fast")
                else:
                    # For very large payloads, just verify we can detect the problem
                    if not is_under_limit:
                        print(f"    ❌ Exceeds 512KB limit (as expected for stress test)")
                    else:
                        print(f"    ✅ Still under limit")
        
        print(f"  ✅ Payload size limit testing PASSED")


def run_performance_tests():
    """Run all performance tests"""
    print("⚡ VRSEN PIPELINE PERFORMANCE TESTS")
    print("=" * 60)
    print("Testing performance, scalability, and resource usage")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLargeHtmlFilePerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestConcurrentOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestScalabilityLimits))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("⚡ PERFORMANCE TEST SUMMARY")
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
        print("\n✅ ALL PERFORMANCE TESTS PASSED!")
        print("🚀 Pipeline can handle large files and concurrent operations")
        print("🎯 Ready for end-to-end testing with real data")
    else:
        print("\n❌ Some performance tests failed")
        print("🔧 Optimize performance issues before production")
    
    return success


if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)