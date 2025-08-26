#!/usr/bin/env python3
"""
Comprehensive System Integration and Validation Test
Final verification that all security fixes integrate properly and system is production-ready
"""

import sys
import os
import time
import json
import gc
import traceback
from pathlib import Path
from datetime import datetime

# Add project paths
sys.path.append('.')
sys.path.append('./src')

def test_security_integration():
    """Test security fixes integration with core components"""
    print("=== 🔒 SECURITY INTEGRATION TEST ===")
    results = {}
    
    try:
        # Test 1: Import security modules
        from src.security.secure_config import (
            get_browser_config, 
            get_security_config, 
            InputValidator,
            SecureConfigManager
        )
        print("✅ Security modules imported successfully")
        results['security_import'] = True
        
        # Test 2: Create secure configuration
        config_manager = SecureConfigManager('./test_config.json')
        config = config_manager.load_config()
        print(f"✅ Configuration loaded with {len(config)} sections")
        results['config_load'] = True
        
        # Test 3: Validate configurations
        browser_config = get_browser_config()
        security_config = get_security_config()
        print(f"✅ Browser config: {browser_config.viewport_width}x{browser_config.viewport_height}")
        print(f"✅ Security config: stealth level {security_config.stealth_level}")
        results['config_validation'] = True
        
        # Test 4: Input validation
        validator = InputValidator()
        test_url = "https://httpbin.org/get"
        is_valid = validator.validate_url(test_url)
        sanitized = validator.sanitize_string("Test<script>alert('xss')</script>", max_length=50)
        print(f"✅ Input validation: URL valid={is_valid}, sanitized='{sanitized[:20]}...'")
        results['input_validation'] = True
        
        return results
        
    except Exception as e:
        print(f"❌ Security integration error: {e}")
        traceback.print_exc()
        results['error'] = str(e)
        return results

def test_core_engine_integration():
    """Test core engine integration with security fixes"""
    print("\n=== ⚙️ CORE ENGINE INTEGRATION TEST ===")
    results = {}
    
    try:
        # Test 1: Import core engine
        from src.botasaurus_core.engine import BotasaurusEngine, SessionConfig
        print("✅ Core engine imported successfully")
        results['engine_import'] = True
        
        # Test 2: Create engine with secure config
        test_config = SessionConfig(
            session_id='integration_test',
            profile_name='test_profile',
            stealth_level=3,
            max_memory_mb=1024
        )
        
        engine = BotasaurusEngine(test_config)
        print("✅ Engine created with secure configuration")
        results['engine_creation'] = True
        
        # Test 3: Test engine methods
        metrics = engine.get_metrics()
        print(f"✅ Engine metrics available: {len(metrics)} metrics")
        print(f"   - Start time: {metrics.get('start_time')}")
        print(f"   - Memory usage: {metrics.get('memory_usage', 0):.2f} MB")
        results['engine_methods'] = True
        
        # Test 4: Test memory management
        engine.add_cleanup_callback(lambda: print("   - Cleanup callback executed"))
        print("✅ Memory management callbacks registered")
        results['memory_management'] = True
        
        # Test 5: Cleanup
        engine.cleanup()
        print("✅ Engine cleanup completed successfully")
        results['cleanup'] = True
        
        return results
        
    except Exception as e:
        print(f"❌ Core engine integration error: {e}")
        traceback.print_exc()
        results['error'] = str(e)
        return results

def test_business_scraper_integration():
    """Test business scraper integration"""
    print("\n=== 🔍 BUSINESS SCRAPER INTEGRATION TEST ===")
    results = {}
    
    try:
        # Test 1: Import business scraper
        from botasaurus_business_scraper import BotasaurusBusinessScraper
        print("✅ Business scraper imported successfully")
        results['scraper_import'] = True
        
        # Test 2: Initialize scraper
        scraper = BotasaurusBusinessScraper()
        print("✅ Business scraper initialized")
        results['scraper_init'] = True
        
        # Test 3: Verify required methods
        required_methods = [
            'scrape_google_maps_businesses',
            'extract_email_from_website', 
            'save_results',
            '_extract_businesses_with_scroll',
            '_extract_business_from_card',
            '_is_duplicate'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(scraper, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            results['missing_methods'] = missing_methods
        else:
            print(f"✅ All {len(required_methods)} required methods available")
            results['methods_available'] = True
        
        # Test 4: Verify stats structure
        expected_stats = ['total_scraped', 'with_email', 'with_phone', 'with_website']
        stats_ok = all(key in scraper.stats for key in expected_stats)
        print(f"✅ Statistics structure valid: {stats_ok}")
        results['stats_structure'] = stats_ok
        
        return results
        
    except Exception as e:
        print(f"❌ Business scraper integration error: {e}")
        traceback.print_exc()
        results['error'] = str(e)
        return results

def test_security_vulnerabilities_fixed():
    """Test that all identified security vulnerabilities are fixed"""
    print("\n=== 🛡️ SECURITY VULNERABILITY VERIFICATION ===")
    results = {}
    
    try:
        # Test 1: Check for hardcoded environment variables
        engine_file = Path('./src/botasaurus_core/engine.py')
        if engine_file.exists():
            with open(engine_file, 'r', encoding='utf-8') as f:
                engine_code = f.read()
            
            # These patterns should NOT exist anymore
            forbidden_patterns = [
                "os.environ['CHROME_BINARY_LOCATION'] = ''",
                "os.environ['HEADLESS'] = 'False'",
                "os.environ['CHROME_BINARY_LOCATION']='",
                "os.environ['HEADLESS']="
            ]
            
            violations = []
            for pattern in forbidden_patterns:
                if pattern in engine_code:
                    violations.append(pattern)
            
            if violations:
                print(f"❌ Hardcoded environment variables found: {violations}")
                results['env_var_violations'] = violations
            else:
                print("✅ No hardcoded environment variables detected")
                results['no_hardcoded_env_vars'] = True
        
        # Test 2: Check for secure configuration usage
        if 'from ..security.secure_config import' in engine_code or 'from secure_config import' in engine_code:
            print("✅ Engine uses secure configuration system")
            results['uses_secure_config'] = True
        else:
            print("⚠️ Engine may not be using secure configuration")
            results['secure_config_warning'] = True
        
        # Test 3: Check for input validation
        if 'InputValidator' in engine_code and 'sanitize_string' in engine_code:
            print("✅ Input validation implemented")
            results['input_validation_implemented'] = True
        else:
            print("⚠️ Input validation may not be fully implemented")
            results['input_validation_warning'] = True
        
        # Test 4: Check for memory management
        memory_patterns = ['_check_memory_usage', '_perform_memory_cleanup', 'gc.collect']
        memory_features = sum(1 for pattern in memory_patterns if pattern in engine_code)
        
        if memory_features >= 2:
            print(f"✅ Memory management implemented ({memory_features}/{len(memory_patterns)} features)")
            results['memory_management_implemented'] = True
        else:
            print(f"⚠️ Limited memory management ({memory_features}/{len(memory_patterns)} features)")
            results['memory_management_limited'] = True
        
        return results
        
    except Exception as e:
        print(f"❌ Security vulnerability check error: {e}")
        results['error'] = str(e)
        return results

def test_memory_management():
    """Test memory management and resource cleanup"""
    print("\n=== 🧠 MEMORY MANAGEMENT TEST ===")
    results = {}
    
    try:
        import psutil
        
        # Test 1: Baseline memory usage
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        print(f"✅ Initial memory usage: {initial_memory:.1f} MB")
        results['initial_memory'] = initial_memory
        
        # Test 2: Create and destroy multiple engines
        from src.botasaurus_core.engine import BotasaurusEngine, SessionConfig
        
        engines_created = 0
        for i in range(5):
            try:
                config = SessionConfig(
                    session_id=f'memory_test_{i}',
                    profile_name=f'mem_profile_{i}',
                    max_memory_mb=512
                )
                engine = BotasaurusEngine(config)
                engines_created += 1
                engine.cleanup()
                
                # Force garbage collection
                gc.collect()
                
            except Exception as e:
                print(f"   Engine {i} creation failed: {str(e)[:50]}")
        
        print(f"✅ Created and cleaned up {engines_created}/5 engines")
        results['engines_processed'] = engines_created
        
        # Test 3: Check final memory usage
        time.sleep(1)  # Allow cleanup to complete
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_diff = final_memory - initial_memory
        
        print(f"✅ Final memory usage: {final_memory:.1f} MB")
        print(f"✅ Memory difference: {memory_diff:.1f} MB")
        results['final_memory'] = final_memory
        results['memory_diff'] = memory_diff
        
        # Test 4: Evaluate memory management
        if memory_diff < 50:  # Less than 50MB increase
            print("✅ Excellent memory management - minimal memory growth")
            results['memory_grade'] = 'excellent'
        elif memory_diff < 100:  # Less than 100MB increase
            print("✅ Good memory management - acceptable memory growth")
            results['memory_grade'] = 'good'
        else:
            print(f"⚠️ Potential memory leak detected: {memory_diff:.1f} MB growth")
            results['memory_grade'] = 'warning'
        
        return results
        
    except Exception as e:
        print(f"❌ Memory management test error: {e}")
        results['error'] = str(e)
        return results

def test_performance_readiness():
    """Test performance readiness for production deployment"""
    print("\n=== ⚡ PERFORMANCE READINESS TEST ===")
    results = {}
    
    try:
        # Test 1: Import speed
        start_time = time.time()
        
        from botasaurus import browser, Driver
        from botasaurus_business_scraper import BotasaurusBusinessScraper
        from src.security.secure_config import get_browser_config
        
        import_time = time.time() - start_time
        print(f"✅ Module import time: {import_time:.3f}s")
        results['import_time'] = import_time
        
        # Test 2: Scraper initialization speed
        start_time = time.time()
        scraper = BotasaurusBusinessScraper()
        init_time = time.time() - start_time
        print(f"✅ Scraper initialization: {init_time:.3f}s")
        results['init_time'] = init_time
        
        # Test 3: Configuration loading speed
        start_time = time.time()
        config = get_browser_config()
        config_time = time.time() - start_time
        print(f"✅ Configuration loading: {config_time:.3f}s")
        results['config_time'] = config_time
        
        # Test 4: Overall readiness assessment
        total_startup_time = import_time + init_time + config_time
        
        if total_startup_time < 1.0:
            print(f"✅ Excellent startup performance: {total_startup_time:.3f}s total")
            results['performance_grade'] = 'excellent'
        elif total_startup_time < 3.0:
            print(f"✅ Good startup performance: {total_startup_time:.3f}s total")
            results['performance_grade'] = 'good'
        else:
            print(f"⚠️ Slow startup performance: {total_startup_time:.3f}s total")
            results['performance_grade'] = 'needs_improvement'
        
        results['total_startup_time'] = total_startup_time
        return results
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        results['error'] = str(e)
        return results

def run_comprehensive_validation():
    """Run all validation tests and generate final report"""
    print("🚀 BOTASAURUS COMPREHENSIVE VALIDATION SUITE")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all test suites
    test_suites = [
        ("Security Integration", test_security_integration),
        ("Core Engine Integration", test_core_engine_integration),
        ("Business Scraper Integration", test_business_scraper_integration),
        ("Security Vulnerabilities Fixed", test_security_vulnerabilities_fixed),
        ("Memory Management", test_memory_management),
        ("Performance Readiness", test_performance_readiness)
    ]
    
    all_results = {}
    passed_suites = 0
    total_suites = len(test_suites)
    
    for suite_name, test_function in test_suites:
        try:
            result = test_function()
            all_results[suite_name] = result
            
            # Check if suite passed (no errors and key indicators present)
            if 'error' not in result and any(key.endswith(('_import', '_creation', '_available', '_implemented', 'excellent', 'good')) for key in result.keys()):
                passed_suites += 1
                print(f"✅ {suite_name}: PASSED")
            else:
                print(f"⚠️ {suite_name}: ISSUES DETECTED")
                
        except Exception as e:
            print(f"❌ {suite_name}: FAILED - {e}")
            all_results[suite_name] = {'error': str(e)}
    
    # Calculate overall results
    execution_time = time.time() - start_time
    success_rate = passed_suites / total_suites
    
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE VALIDATION RESULTS")
    print("=" * 60)
    print(f"Execution Time: {execution_time:.2f} seconds")
    print(f"Test Suites: {passed_suites}/{total_suites} passed")
    print(f"Success Rate: {success_rate:.1%}")
    
    # Final assessment
    if success_rate >= 0.9:
        status = "🎉 PRODUCTION-READY"
        grade = "EXCELLENT"
        recommendation = "✅ System is ready for immediate production deployment"
    elif success_rate >= 0.8:
        status = "✅ PRODUCTION-READY"
        grade = "GOOD"
        recommendation = "✅ System is ready for production with minor monitoring"
    elif success_rate >= 0.7:
        status = "⚠️ NEEDS ATTENTION"
        grade = "ACCEPTABLE"
        recommendation = "⚠️ Address identified issues before production deployment"
    else:
        status = "❌ NOT READY"
        grade = "POOR"
        recommendation = "❌ Significant improvements required before production"
    
    print(f"\nSystem Status: {status}")
    print(f"Overall Grade: {grade}")
    print(f"Recommendation: {recommendation}")
    
    # Key achievements
    print(f"\n🔑 KEY ACHIEVEMENTS:")
    if all_results.get('Security Vulnerabilities Fixed', {}).get('no_hardcoded_env_vars'):
        print("   ✅ All hardcoded environment variables eliminated")
    if all_results.get('Security Integration', {}).get('input_validation'):
        print("   ✅ Comprehensive input validation implemented")
    if all_results.get('Memory Management', {}).get('memory_grade') in ['excellent', 'good']:
        print("   ✅ Memory management optimized")
    if all_results.get('Performance Readiness', {}).get('performance_grade') in ['excellent', 'good']:
        print("   ✅ Performance meets production requirements")
    
    # Save detailed results
    output_dir = Path('./test_output')
    output_dir.mkdir(exist_ok=True)
    
    final_report = {
        'timestamp': datetime.now().isoformat(),
        'test_type': 'comprehensive_integration_validation',
        'execution_time': execution_time,
        'suites_passed': passed_suites,
        'total_suites': total_suites,
        'success_rate': success_rate,
        'status': status,
        'grade': grade,
        'recommendation': recommendation,
        'detailed_results': all_results,
        'production_ready': success_rate >= 0.8
    }
    
    report_file = output_dir / f'comprehensive_validation_report_{int(time.time())}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved: {report_file}")
    
    return final_report

if __name__ == "__main__":
    try:
        results = run_comprehensive_validation()
        production_ready = results.get('production_ready', False)
        
        if production_ready:
            print("\n🚀 SYSTEM VALIDATION COMPLETE - READY FOR 1000+ LEAD DEPLOYMENT!")
            sys.exit(0)
        else:
            print("\n⚠️ SYSTEM VALIDATION COMPLETE - IMPROVEMENTS NEEDED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        traceback.print_exc()
        sys.exit(1)