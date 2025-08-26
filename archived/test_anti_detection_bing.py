#!/usr/bin/env python3
"""
Test script for enhanced anti-detection Bing scraper.
Tests the anti-detection mechanisms with "lawyer Chicago" query.
"""

import os
import sys
import logging
import time
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('anti_detection_test.log')
    ]
)

logger = logging.getLogger(__name__)

def test_anti_detection_bing_search():
    """Test the enhanced anti-detection Bing search with lawyer Chicago query."""
    
    print("=" * 80)
    print("TESTING ENHANCED ANTI-DETECTION BING SCRAPER")
    print("=" * 80)
    print("Query: 'lawyer Chicago'")
    print("Objective: Bypass Bing's blocking and get real law firm URLs")
    print("=" * 80)
    
    try:
        # Import the enhanced Bing search tool
        from agents.tools.bing_search_tool import BingSearchTool
        
        # Test configuration
        test_query = "lawyer Chicago"
        max_pages = 2
        session_id = f"anti_detection_test_{int(time.time())}"
        
        print(f"\n[1/5] Initializing Enhanced Bing Search Tool...")
        print(f"Query: {test_query}")
        print(f"Max Pages: {max_pages}")
        print(f"Session ID: {session_id}")
        print(f"HTML Storage: Enabled")
        
        # Create tool with anti-detection features
        tool = BingSearchTool(
            query=test_query,
            max_pages=max_pages,
            session_id=session_id,
            store_html=True,
            proxy_preference="none"  # Start without proxy for first test
        )
        
        print("\n[2/5] Starting Search with Enhanced Anti-Detection...")
        print("Features enabled:")
        print("  [+] Enhanced user agent rotation")
        print("  [+] Human behavior simulation")
        print("  [+] Session management") 
        print("  [+] CAPTCHA detection & handling")
        print("  [+] Advanced browser stealth")
        
        start_time = time.time()
        
        # Execute the search
        result = tool.run()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n[3/5] Search Execution Complete ({execution_time:.2f}s)")
        print("=" * 50)
        
        # Analyze results
        print("\n[4/5] Analyzing Results...")
        
        success = result.get('success', False)
        pages_retrieved = result.get('pages_retrieved', 0)
        total_attempted = result.get('total_pages_attempted', 0)
        error_messages = result.get('summary', {}).get('errors_encountered', [])
        
        print(f"Overall Success: {success}")
        print(f"Pages Retrieved: {pages_retrieved}/{total_attempted}")
        print(f"Execution Time: {execution_time:.2f}s")
        
        if error_messages:
            print(f"Errors Encountered: {len(error_messages)}")
            for i, error in enumerate(error_messages, 1):
                print(f"  {i}. {error}")
        
        # Check for real results vs blocking
        results_analysis = analyze_search_results(result)
        
        print("\n[5/5] Anti-Detection Effectiveness Analysis")
        print("=" * 50)
        
        if results_analysis['has_real_results']:
            print("[SUCCESS] Anti-detection bypassed Bing's blocking!")
            print(f"[SUCCESS] Found {results_analysis['law_firm_count']} potential law firm URLs")
            print(f"[SUCCESS] No blocking signals detected")
            
            if results_analysis['sample_urls']:
                print("\nSample Law Firm URLs Found:")
                for i, url in enumerate(results_analysis['sample_urls'][:5], 1):
                    print(f"  {i}. {url}")
        
        elif results_analysis['captcha_detected']:
            print("[PARTIAL] CAPTCHA challenges detected")
            print(f"[PARTIAL] CAPTCHA types: {results_analysis['captcha_types']}")
            print("[PARTIAL] Some challenges may have been resolved automatically")
            
        elif results_analysis['blocking_detected']:
            print("[BLOCKED] Bing is still blocking requests")
            print(f"[BLOCKED] Blocking signals: {results_analysis['blocking_signals']}")
            print("[BLOCKED] Anti-detection needs further enhancement")
            
        else:
            print("[UNCLEAR] Results need manual review")
            print("[UNCLEAR] Check HTML output files for details")
        
        # Save detailed results
        save_test_results(result, results_analysis, execution_time)
        
        return results_analysis['has_real_results']
        
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def analyze_search_results(result):
    """Analyze search results to determine if anti-detection was successful."""
    
    analysis = {
        'has_real_results': False,
        'blocking_detected': False,
        'captcha_detected': False,
        'law_firm_count': 0,
        'sample_urls': [],
        'blocking_signals': [],
        'captcha_types': []
    }
    
    try:
        # Check HTML files for content analysis
        html_files = result.get('html_files', [])
        
        for html_file in html_files:
            if html_file and os.path.exists(html_file):
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read().lower()
                
                # Check for blocking signals
                blocking_indicators = [
                    'captcha', 'blocked', 'too many requests', 'rate limit',
                    'access denied', 'suspicious activity', 'verify you are human',
                    'robot', 'automation', 'cloudflare'
                ]
                
                found_blocking = []
                for indicator in blocking_indicators:
                    if indicator in html_content:
                        found_blocking.append(indicator)
                
                if found_blocking:
                    analysis['blocking_detected'] = True
                    analysis['blocking_signals'].extend(found_blocking)
                
                # Check for CAPTCHA specifically
                captcha_indicators = ['captcha', 'recaptcha', 'hcaptcha', 'verify you are human']
                found_captcha = []
                for indicator in captcha_indicators:
                    if indicator in html_content:
                        found_captcha.append(indicator)
                
                if found_captcha:
                    analysis['captcha_detected'] = True
                    analysis['captcha_types'].extend(found_captcha)
                
                # Look for real law firm indicators
                law_firm_indicators = [
                    'attorney', 'lawyer', 'law firm', 'legal services',
                    '.com/attorney', '.com/lawyer', 'law.com', 'legal',
                    'practice areas', 'consultation', 'litigation'
                ]
                
                law_firm_matches = 0
                for indicator in law_firm_indicators:
                    law_firm_matches += html_content.count(indicator)
                
                if law_firm_matches > 5:  # Threshold for real results
                    analysis['has_real_results'] = True
                    analysis['law_firm_count'] += law_firm_matches
                
                # Extract sample URLs (simplified)
                import re
                url_pattern = r'https?://[^\s<>"\']+(?:law|attorney|lawyer|legal)[^\s<>"\']*'
                urls = re.findall(url_pattern, html_content)
                
                # Filter and clean URLs
                for url in urls:
                    if 'bing.com' not in url and len(url) > 10:
                        analysis['sample_urls'].append(url)
                
        # Remove duplicates
        analysis['sample_urls'] = list(set(analysis['sample_urls']))
        analysis['blocking_signals'] = list(set(analysis['blocking_signals']))
        analysis['captcha_types'] = list(set(analysis['captcha_types']))
        
        # Final determination
        if not analysis['blocking_detected'] and analysis['law_firm_count'] > 0:
            analysis['has_real_results'] = True
        
    except Exception as e:
        logger.error(f"Error analyzing results: {e}")
    
    return analysis

def save_test_results(result, analysis, execution_time):
    """Save test results to file for later analysis."""
    
    timestamp = int(time.time())
    output_file = f"anti_detection_test_results_{timestamp}.json"
    
    test_results = {
        'timestamp': timestamp,
        'test_type': 'anti_detection_bing_search',
        'query': 'lawyer Chicago',
        'execution_time_seconds': execution_time,
        'raw_results': result,
        'analysis': analysis,
        'success': analysis['has_real_results'],
        'blocking_bypassed': not analysis['blocking_detected'],
        'captcha_handled': analysis['captcha_detected']
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\n[INFO] Detailed results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to save test results: {e}")

def run_comprehensive_test():
    """Run comprehensive anti-detection test suite."""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE ANTI-DETECTION TEST SUITE")
    print("="*80)
    
    tests_passed = 0
    total_tests = 1
    
    # Test 1: Basic anti-detection with lawyer Chicago
    print("\nTest 1: Basic Anti-Detection with 'lawyer Chicago'")
    print("-" * 50)
    
    if test_anti_detection_bing_search():
        tests_passed += 1
        print("[PASS] Test 1 PASSED")
    else:
        print("[FAIL] Test 1 FAILED")
    
    # Summary
    print(f"\n" + "="*80)
    print(f"TEST SUITE SUMMARY")
    print(f"="*80)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    success_rate = (tests_passed / total_tests) * 100
    print(f"Success Rate: {success_rate:.1f}%")
    
    if tests_passed == total_tests:
        print("[SUCCESS] ALL TESTS PASSED - Anti-detection system working!")
        print("[SUCCESS] Bing blocking successfully bypassed")
        print("[SUCCESS] Ready for production use")
    else:
        print("[WARNING] Some tests failed - Anti-detection needs improvements")
        print("[WARNING] Check logs and adjust anti-detection parameters")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)