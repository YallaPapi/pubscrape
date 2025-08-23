#!/usr/bin/env python3
"""
Performance Validation Script
Validates the optimized scraper system meets all performance requirements:
- Process 1000+ leads efficiently
- Maintain <2GB memory usage per session
- Keep <5% detection rate
- Ensure reliable concurrent processing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import json
import logging
from datetime import datetime
from pathlib import Path

from src.optimization import (
    ResourcePoolConfig,
    LoadTestConfig,
    LoadTestRunner,
    run_comprehensive_load_test
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_validation_suite():
    """Run comprehensive performance validation suite"""
    print("=" * 70)
    print("BOTASAURUS PERFORMANCE VALIDATION SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    validation_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'overall_result': 'UNKNOWN'
    }
    
    try:
        # Test 1: Memory Constraint Test (1000 leads, <2GB memory)
        print("🧪 Test 1: Memory Constraint Validation")
        print("-" * 50)
        
        memory_test_config = LoadTestConfig(
            target_leads=1000,
            max_memory_mb=2048,  # 2GB limit
            max_detection_rate=0.05,  # 5% limit
            test_duration_minutes=30,
            concurrent_sessions=5,
            platforms=['bing', 'google']
        )
        
        memory_test_runner = LoadTestRunner(memory_test_config)
        memory_test_result = memory_test_runner.run_load_test()
        
        # Evaluate memory test
        memory_test_passed = (
            memory_test_result.total_leads_extracted >= 1000 and
            memory_test_result.peak_memory_usage_mb <= 2048 and
            memory_test_result.peak_detection_rate <= 0.05
        )
        
        validation_results['tests']['memory_constraint'] = {
            'passed': memory_test_passed,
            'target_leads': 1000,
            'actual_leads': memory_test_result.total_leads_extracted,
            'memory_limit_mb': 2048,
            'peak_memory_mb': memory_test_result.peak_memory_usage_mb,
            'detection_limit': 0.05,
            'peak_detection_rate': memory_test_result.peak_detection_rate,
            'test_duration_minutes': (
                (memory_test_result.end_time - memory_test_result.start_time).total_seconds() / 60
                if memory_test_result.end_time else 0
            )
        }
        
        print(f"   Target Leads: 1000 | Actual: {memory_test_result.total_leads_extracted} | {'✅' if memory_test_result.total_leads_extracted >= 1000 else '❌'}")
        print(f"   Memory Limit: 2048MB | Peak: {memory_test_result.peak_memory_usage_mb:.1f}MB | {'✅' if memory_test_result.peak_memory_usage_mb <= 2048 else '❌'}")
        print(f"   Detection Limit: 5.0% | Peak: {memory_test_result.peak_detection_rate:.1%} | {'✅' if memory_test_result.peak_detection_rate <= 0.05 else '❌'}")
        print(f"   Overall Test 1: {'✅ PASSED' if memory_test_passed else '❌ FAILED'}")
        print()
        
        # Test 2: High Volume Test (2000 leads for stress testing)
        print("🧪 Test 2: High Volume Stress Test")
        print("-" * 50)
        
        volume_test_config = LoadTestConfig(
            target_leads=2000,
            max_memory_mb=3072,  # 3GB limit for stress test
            max_detection_rate=0.08,  # Slightly higher tolerance for stress
            test_duration_minutes=45,
            concurrent_sessions=8,  # More sessions
            platforms=['bing', 'google']
        )
        
        volume_test_runner = LoadTestRunner(volume_test_config)
        volume_test_result = volume_test_runner.run_load_test()
        
        volume_test_passed = (
            volume_test_result.total_leads_extracted >= 1500 and  # 75% of target
            volume_test_result.peak_memory_usage_mb <= 3072 and
            volume_test_result.peak_detection_rate <= 0.08
        )
        
        validation_results['tests']['high_volume'] = {
            'passed': volume_test_passed,
            'target_leads': 2000,
            'actual_leads': volume_test_result.total_leads_extracted,
            'memory_limit_mb': 3072,
            'peak_memory_mb': volume_test_result.peak_memory_usage_mb,
            'detection_limit': 0.08,
            'peak_detection_rate': volume_test_result.peak_detection_rate,
            'concurrent_sessions': 8
        }
        
        print(f"   Target Leads: 2000 | Actual: {volume_test_result.total_leads_extracted} | {'✅' if volume_test_result.total_leads_extracted >= 1500 else '❌'}")
        print(f"   Memory Limit: 3072MB | Peak: {volume_test_result.peak_memory_usage_mb:.1f}MB | {'✅' if volume_test_result.peak_memory_usage_mb <= 3072 else '❌'}")
        print(f"   Detection Limit: 8.0% | Peak: {volume_test_result.peak_detection_rate:.1%} | {'✅' if volume_test_result.peak_detection_rate <= 0.08 else '❌'}")
        print(f"   Overall Test 2: {'✅ PASSED' if volume_test_passed else '❌ FAILED'}")
        print()
        
        # Test 3: Endurance Test (Longer duration)
        print("🧪 Test 3: Endurance Test")
        print("-" * 50)
        
        endurance_test_config = LoadTestConfig(
            target_leads=1500,
            max_memory_mb=2048,
            max_detection_rate=0.06,
            test_duration_minutes=60,  # 1 hour
            concurrent_sessions=4,  # Conservative for endurance
            platforms=['bing', 'google']
        )
        
        endurance_test_runner = LoadTestRunner(endurance_test_config)
        endurance_test_result = endurance_test_runner.run_load_test()
        
        endurance_test_passed = (
            endurance_test_result.total_leads_extracted >= 1200 and  # 80% of target
            endurance_test_result.peak_memory_usage_mb <= 2048 and
            endurance_test_result.peak_detection_rate <= 0.06
        )
        
        validation_results['tests']['endurance'] = {
            'passed': endurance_test_passed,
            'target_leads': 1500,
            'actual_leads': endurance_test_result.total_leads_extracted,
            'memory_limit_mb': 2048,
            'peak_memory_mb': endurance_test_result.peak_memory_usage_mb,
            'detection_limit': 0.06,
            'peak_detection_rate': endurance_test_result.peak_detection_rate,
            'duration_minutes': 60
        }
        
        print(f"   Target Leads: 1500 | Actual: {endurance_test_result.total_leads_extracted} | {'✅' if endurance_test_result.total_leads_extracted >= 1200 else '❌'}")
        print(f"   Memory Limit: 2048MB | Peak: {endurance_test_result.peak_memory_usage_mb:.1f}MB | {'✅' if endurance_test_result.peak_memory_usage_mb <= 2048 else '❌'}")
        print(f"   Detection Limit: 6.0% | Peak: {endurance_test_result.peak_detection_rate:.1%} | {'✅' if endurance_test_result.peak_detection_rate <= 0.06 else '❌'}")
        print(f"   Overall Test 3: {'✅ PASSED' if endurance_test_passed else '❌ FAILED'}")
        print()
        
        # Overall validation result
        all_tests_passed = (
            memory_test_passed and 
            volume_test_passed and 
            endurance_test_passed
        )
        
        validation_results['overall_result'] = 'PASSED' if all_tests_passed else 'FAILED'
        
        # Summary
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Test 1 - Memory Constraint: {'✅ PASSED' if memory_test_passed else '❌ FAILED'}")
        print(f"Test 2 - High Volume Stress: {'✅ PASSED' if volume_test_passed else '❌ FAILED'}")
        print(f"Test 3 - Endurance: {'✅ PASSED' if endurance_test_passed else '❌ FAILED'}")
        print()
        print(f"🎯 OVERALL RESULT: {'✅ SYSTEM VALIDATED' if all_tests_passed else '❌ VALIDATION FAILED'}")
        print()
        
        if all_tests_passed:
            print("🎉 The Botasaurus scraper system meets all performance requirements:")
            print("   ✅ Can process 1000+ leads efficiently")
            print("   ✅ Maintains <2GB memory usage per session")
            print("   ✅ Keeps detection rate <5%")
            print("   ✅ Handles concurrent processing reliably")
            print("   ✅ Performs well under stress and endurance conditions")
        else:
            print("⚠️  The system requires optimization to meet requirements.")
            print("   Please review the test results and optimize accordingly.")
        
    except Exception as e:
        logger.error(f"Validation suite error: {e}")
        validation_results['error'] = str(e)
        validation_results['overall_result'] = 'ERROR'
        print(f"\n❌ Validation suite failed with error: {e}")
    
    finally:
        # Save results
        results_file = Path('validation_results.json')
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        print(f"📄 Logs saved to: performance_validation.log")
        print()
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
    
    return validation_results

def quick_validation():
    """Run a quick validation test (shorter duration for CI/testing)"""
    print("🚀 Running Quick Performance Validation")
    print("-" * 50)
    
    quick_config = LoadTestConfig(
        target_leads=200,
        max_memory_mb=1500,
        max_detection_rate=0.05,
        test_duration_minutes=10,
        concurrent_sessions=3,
        platforms=['bing']  # Just one platform for speed
    )
    
    runner = LoadTestRunner(quick_config)
    result = runner.run_load_test()
    
    passed = (
        result.total_leads_extracted >= 150 and  # 75% of target
        result.peak_memory_usage_mb <= 1500 and
        result.peak_detection_rate <= 0.05
    )
    
    print(f"✅ Quick validation: {'PASSED' if passed else 'FAILED'}")
    print(f"   Leads: {result.total_leads_extracted}/200")
    print(f"   Memory: {result.peak_memory_usage_mb:.1f}MB/1500MB")
    print(f"   Detection: {result.peak_detection_rate:.1%}/5.0%")
    
    return passed

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run performance validation')
    parser.add_argument('--quick', action='store_true', help='Run quick validation only')
    args = parser.parse_args()
    
    if args.quick:
        success = quick_validation()
        sys.exit(0 if success else 1)
    else:
        results = run_validation_suite()
        success = results.get('overall_result') == 'PASSED'
        sys.exit(0 if success else 1)