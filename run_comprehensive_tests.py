#!/usr/bin/env python3
"""
Comprehensive VRSEN Pipeline Test Suite Runner
Executes all tests to validate 512KB fix and production readiness
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_test_file(test_file: str, description: str) -> tuple[bool, str]:
    """Run a test file and return success status with output"""
    print(f"\n{'='*60}")
    print(f"🧪 RUNNING: {description}")
    print(f"📁 File: {test_file}")
    print('='*60)
    
    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} PASSED ({duration:.1f}s)")
            print(f"📊 Output lines: {len(result.stdout.splitlines())}")
            return True, result.stdout
        else:
            print(f"❌ {description} FAILED ({duration:.1f}s)")
            print(f"🚨 Error output:\n{result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} TIMED OUT (>5 minutes)")
        return False, "Test timed out"
    except Exception as e:
        print(f"💥 {description} CRASHED: {e}")
        return False, str(e)

def main():
    """Run comprehensive VRSEN pipeline test suite"""
    print("🏥 VRSEN AGENCY SWARM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print("Testing 512KB OpenAI limit fix and production readiness")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test files to run in order
    test_suite = [
        ("test_pipeline_fix.py", "Basic Pipeline Fix Verification"),
        ("test_unit_components.py", "Unit Tests - Individual Components"),
        ("test_integration_pipeline.py", "Integration Tests - Agent Communication"), 
        ("test_performance_pipeline.py", "Performance Tests - Large Files & Concurrency"),
        ("test_end_to_end_50_doctors.py", "End-to-End Test - Doctor Lead Campaign"),
    ]
    
    # Results tracking
    results = []
    total_start_time = time.time()
    
    # Run each test
    for test_file, description in test_suite:
        if not os.path.exists(test_file):
            print(f"⚠️  Skipping {test_file} - file not found")
            results.append((description, False, "File not found"))
            continue
            
        success, output = run_test_file(test_file, description)
        results.append((description, success, output))
        
        if not success:
            print(f"\n🛑 Test failure detected in {description}")
            print("⚠️  Continuing with remaining tests for complete assessment...")
    
    # Final summary
    total_duration = time.time() - total_start_time
    
    print("\n" + "="*80)
    print("🎯 COMPREHENSIVE TEST SUITE RESULTS")
    print("="*80)
    
    passed_tests = [r for r in results if r[1]]
    failed_tests = [r for r in results if not r[1]]
    
    print(f"📊 Tests Run: {len(results)}")
    print(f"✅ Tests Passed: {len(passed_tests)}")
    print(f"❌ Tests Failed: {len(failed_tests)}")
    print(f"⏱️  Total Duration: {total_duration:.1f}s")
    print()
    
    # Detailed results
    for description, success, output in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {description}")
    
    # Critical assessment
    print("\n" + "="*80)
    print("🔍 CRITICAL ASSESSMENT: 512KB OPENAI LIMIT FIX")
    print("="*80)
    
    critical_checks = []
    
    # Check for payload size mentions in outputs
    for description, success, output in results:
        if success and "bytes" in output and "KB" in output:
            # Extract payload sizes mentioned in output
            import re
            kb_sizes = re.findall(r'(\d+\.?\d*)\s*KB', output)
            max_kb = max(float(size) for size in kb_sizes) if kb_sizes else 0
            
            critical_checks.append((description, max_kb < 512, max_kb))
    
    print("📏 Payload Size Analysis:")
    all_under_limit = True
    for test_name, under_limit, max_size in critical_checks:
        status = "✅" if under_limit else "❌"
        print(f"  {status} {test_name}: Max payload {max_size:.1f}KB")
        if not under_limit:
            all_under_limit = False
    
    print(f"\n🎯 512KB OpenAI Limit Compliance: {'✅ ALL TESTS PASSED' if all_under_limit else '❌ SOME TESTS EXCEEDED LIMIT'}")
    
    # Production readiness assessment
    print("\n📋 PRODUCTION READINESS CHECKLIST:")
    
    checklist_items = [
        ("Basic Pipeline Fix", any(r[0] == "Basic Pipeline Fix Verification" and r[1] for r in results)),
        ("Unit Tests", any(r[0] == "Unit Tests - Individual Components" and r[1] for r in results)),
        ("Integration Tests", any(r[0] == "Integration Tests - Agent Communication" and r[1] for r in results)),
        ("Performance Tests", any(r[0] == "Performance Tests - Large Files & Concurrency" and r[1] for r in results)),
        ("End-to-End Test", any(r[0] == "End-to-End Test - Doctor Lead Campaign" and r[1] for r in results)),
        ("512KB Compliance", all_under_limit),
    ]
    
    all_ready = all(item[1] for item in checklist_items)
    
    for item_name, status in checklist_items:
        print(f"  {'✅' if status else '❌'} {item_name}")
    
    # Final verdict
    print("\n" + "="*80)
    if all_ready and len(failed_tests) == 0:
        print("🎉 COMPREHENSIVE TEST SUITE: ALL TESTS PASSED!")
        print("✅ VRSEN Agency Swarm Pipeline is PRODUCTION READY")
        print("✅ 512KB OpenAI limit issue is RESOLVED")
        print("✅ File-based HTML processing is WORKING")
        print("✅ Agent-to-agent communication is VERIFIED")
        print("✅ Performance and scalability are VALIDATED")
        print()
        print("🚀 READY TO LAUNCH 500 DOCTOR LEAD CAMPAIGN!")
        print()
        print("Next Steps:")
        print("1. Deploy pipeline to production environment")
        print("2. Configure monitoring for payload sizes")
        print("3. Set up disk space management for HTML cache")
        print("4. Run production campaign with confidence")
        
        exit_code = 0
        
    else:
        print("⚠️  COMPREHENSIVE TEST SUITE: ISSUES DETECTED")
        print(f"❌ {len(failed_tests)} test(s) failed")
        if not all_under_limit:
            print("❌ Some payloads exceed 512KB OpenAI limit")
        print()
        print("🔧 Required Actions:")
        for description, success, output in failed_tests:
            print(f"  • Fix issues in: {description}")
        if not all_under_limit:
            print("  • Investigate payload size issues")
        print("  • Re-run comprehensive tests after fixes")
        
        exit_code = 1
    
    print("="*80)
    print(f"⏰ Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("📋 Full test report: VRSEN_PIPELINE_TEST_REPORT.md")
    print("="*80)
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)