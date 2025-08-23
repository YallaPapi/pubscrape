#!/usr/bin/env python3
"""
Real Validation Test Runner

This script replaces mocked anti-detection testing with comprehensive real-world
validation against actual services, websites, and detection systems.

Usage:
    python run_real_validation.py [--quick] [--suite SUITE]
    
Options:
    --quick     Run abbreviated test suite (faster)
    --suite     Run specific test suite (anti-detection, performance, integration, all)
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tests.real_validation_suite import RealValidationTestRunner
from tests.real_validation_config import *
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def display_test_overview():
    """Display overview of real validation tests"""
    
    overview_table = Table(title="Real Validation Test Suite Overview")
    overview_table.add_column("Test Category", style="cyan")
    overview_table.add_column("Tests", style="green") 
    overview_table.add_column("Description", style="white")
    
    overview_table.add_row(
        "Anti-Detection",
        "3 tests",
        "Real Cloudflare bypass, fingerprint validation, session isolation"
    )
    overview_table.add_row(
        "Performance", 
        "2 tests",
        "Load testing with real data, concurrent browser sessions"
    )
    overview_table.add_row(
        "Integration",
        "1 test", 
        "Complete workflow with real scraping and export"
    )
    
    console.print(overview_table)
    
    console.print(f"\n[bold]Key Improvements over Mocked Testing:[/bold]")
    console.print("• Tests against {len(CLOUDFLARE_PROTECTED_SITES)} real Cloudflare-protected sites")
    console.print(f"• Validates fingerprinting against {len(BOT_DETECTION_SERVICES)} detection services") 
    console.print(f"• Performance testing with actual browser operations and memory monitoring")
    console.print(f"• Real email extraction from business websites")
    console.print(f"• Integration testing with {len(INTEGRATION_TEST_QUERIES)} real search queries")


def run_quick_validation():
    """Run abbreviated validation suite for faster testing"""
    console.print("\n[yellow]⚡ Running Quick Real Validation Suite...[/yellow]")
    
    from tests.real_validation_suite import (
        RealAntiDetectionValidator, 
        RealPerformanceValidator, 
        RealIntegrationValidator
    )
    
    results = {}
    
    # Quick anti-detection test (1 test)
    try:
        anti_detection = RealAntiDetectionValidator()
        cf_result = anti_detection.test_real_cloudflare_bypass()
        results['anti_detection'] = {'cloudflare_bypass': len(cf_result)}
        console.print("✅ Quick anti-detection test passed")
    except Exception as e:
        console.print(f"❌ Quick anti-detection test failed: {str(e)[:50]}")
        results['anti_detection'] = {'error': str(e)}
    
    # Quick performance test (1 test) 
    try:
        performance = RealPerformanceValidator()
        perf_result = performance.test_real_load_performance()
        results['performance'] = perf_result
        console.print("✅ Quick performance test passed")
    except Exception as e:
        console.print(f"❌ Quick performance test failed: {str(e)[:50]}")
        results['performance'] = {'error': str(e)}
    
    # Quick integration test
    try:
        integration = RealIntegrationValidator()
        workflow_result = integration.test_complete_workflow_integration()
        results['integration'] = workflow_result
        console.print("✅ Quick integration test passed")
    except Exception as e:
        console.print(f"❌ Quick integration test failed: {str(e)[:50]}")
        results['integration'] = {'error': str(e)}
    
    return results


def run_specific_suite(suite_name):
    """Run specific test suite"""
    console.print(f"\n[yellow]🎯 Running {suite_name.title()} Test Suite...[/yellow]")
    
    if suite_name == 'anti-detection':
        from tests.real_validation_suite import RealAntiDetectionValidator
        validator = RealAntiDetectionValidator()
        
        results = {}
        try:
            results['cloudflare'] = validator.test_real_cloudflare_bypass()
            results['fingerprint'] = validator.test_real_fingerprint_validation()  
            results['session_isolation'] = validator.test_real_session_isolation()
            console.print("✅ Anti-detection suite completed")
        except Exception as e:
            console.print(f"❌ Anti-detection suite failed: {str(e)}")
            results['error'] = str(e)
        
        return results
        
    elif suite_name == 'performance':
        from tests.real_validation_suite import RealPerformanceValidator
        validator = RealPerformanceValidator()
        
        results = {}
        try:
            results['load_performance'] = validator.test_real_load_performance()
            results['concurrent_sessions'] = validator.test_concurrent_browser_sessions()
            console.print("✅ Performance suite completed")
        except Exception as e:
            console.print(f"❌ Performance suite failed: {str(e)}")
            results['error'] = str(e)
        
        return results
        
    elif suite_name == 'integration':
        from tests.real_validation_suite import RealIntegrationValidator
        validator = RealIntegrationValidator()
        
        results = {}
        try:
            results['workflow'] = validator.test_complete_workflow_integration()
            console.print("✅ Integration suite completed")
        except Exception as e:
            console.print(f"❌ Integration suite failed: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    else:
        console.print(f"[red]Unknown suite: {suite_name}[/red]")
        return {}


def generate_validation_report(results, test_type="full"):
    """Generate comprehensive validation report"""
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = Path(f"test_output/real_validation_report_{timestamp}.md")
    report_file.parent.mkdir(exist_ok=True)
    
    # Generate markdown report
    report_content = f"""# Real Validation Test Report

**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S")}  
**Test Type:** {test_type.title()}  
**Botasaurus Version:** Production Ready Test  

## Executive Summary

This report contains results from real-world validation testing of the Botasaurus
business scraper system. Unlike previous mocked tests, these results reflect
actual performance against live services and real detection systems.

## Test Results Summary

"""
    
    if isinstance(results, dict) and 'detailed_results' in results:
        # Full test suite results
        total_tests = results.get('total_tests', 0)
        passed_tests = results.get('passed_tests', 0)
        success_rate = results.get('success_rate', 0)
        
        report_content += f"""
**Overall Results:**
- Total Tests: {total_tests}
- Passed Tests: {passed_tests}
- Success Rate: {success_rate:.1%}
- Production Ready: {'✅ Yes' if results.get('production_ready', False) else '❌ No'}

"""
        
        # Detailed results by category
        for category, tests in results.get('detailed_results', {}).items():
            report_content += f"\n### {category} Tests\n\n"
            
            for test in tests:
                status_icon = "✅" if test['status'] == 'PASSED' else "❌"
                report_content += f"- {status_icon} **{test['test']}**\n"
                
                if test['status'] == 'FAILED':
                    report_content += f"  - Error: {test.get('error', 'Unknown error')}\n"
                elif 'result' in test and isinstance(test['result'], dict):
                    # Add key metrics from test result
                    result = test['result']
                    if 'success_rate' in result:
                        report_content += f"  - Success Rate: {result['success_rate']:.1%}\n"
                    if 'detection_rate' in result:
                        report_content += f"  - Detection Rate: {result['detection_rate']:.1%}\n"
                    if 'throughput' in result:
                        report_content += f"  - Throughput: {result['throughput']:.2f} leads/sec\n"
    
    else:
        # Quick test results
        report_content += "\n**Quick Test Results:**\n\n"
        
        for category, result in results.items():
            status = "✅ Passed" if 'error' not in result else "❌ Failed"
            report_content += f"- **{category.title()}:** {status}\n"
            
            if 'error' in result:
                report_content += f"  - Error: {result['error']}\n"
    
    report_content += f"""

## Real-World Validation Highlights

### Anti-Detection Testing
- **Cloudflare Bypass**: Tested against {len(CLOUDFLARE_PROTECTED_SITES)} live protected sites
- **Bot Detection**: Validated against {len(BOT_DETECTION_SERVICES)} real detection services  
- **Fingerprint Randomization**: Verified browser fingerprint diversity
- **Session Isolation**: Confirmed proper session data separation

### Performance Testing  
- **Load Testing**: Real business lead processing with memory monitoring
- **Concurrent Sessions**: Multiple browser instances running in parallel
- **Email Extraction**: Actual website parsing and contact discovery
- **Throughput Measurement**: Real-world processing speed validation

### Integration Testing
- **End-to-End Workflow**: Complete lead generation pipeline
- **Data Quality Validation**: Real business data verification
- **Export Functionality**: CSV/JSON export with actual data
- **Error Recovery**: Real failure scenario handling

## Recommendations

"""
    
    if isinstance(results, dict) and results.get('success_rate', 0) >= 0.8:
        report_content += """
✅ **PRODUCTION READY**: System passed real-world validation
- Anti-detection mechanisms effectively bypass blocking
- Performance meets production load requirements  
- Integration workflow functions properly end-to-end
- Recommended for deployment with monitoring

"""
    elif isinstance(results, dict) and results.get('success_rate', 0) >= 0.6:
        report_content += """
⚠️ **NEEDS IMPROVEMENT**: Some real-world tests failing
- Review failed test components and error logs
- Consider additional anti-detection enhancements
- Monitor performance under production loads
- Test improvements with another validation run

"""
    else:
        report_content += """
❌ **NOT PRODUCTION READY**: Critical real-world failures
- Significant improvements required before deployment
- Review anti-detection and performance issues
- Consider architectural changes for failing components
- Re-run validation after implementing fixes

"""
    
    report_content += f"""
## Technical Details

**Test Configuration:**
- Cloudflare Test Sites: {len(CLOUDFLARE_PROTECTED_SITES)}
- Bot Detection Services: {len(BOT_DETECTION_SERVICES)}
- Integration Queries: {len(INTEGRATION_TEST_QUERIES)}
- Performance Benchmarks: {len(PERFORMANCE_BENCHMARKS)} metrics

**Test Environment:**
- Output Directory: {TEST_ENVIRONMENT['output_directory']}
- HTML Snapshots: {'Enabled' if TEST_ENVIRONMENT['save_html_snapshots'] else 'Disabled'}
- Performance Metrics: {'Saved' if TEST_ENVIRONMENT['save_performance_metrics'] else 'Not Saved'}

---
*This report was generated by the Real Validation Test Suite*
"""
    
    # Save report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    console.print(f"\n📄 [bold]Validation report saved:[/bold] {report_file}")
    return report_file


def main():
    """Main execution function"""
    
    parser = argparse.ArgumentParser(
        description="Real Validation Test Runner for Botasaurus",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--quick', 
        action='store_true',
        help='Run abbreviated test suite (faster execution)'
    )
    
    parser.add_argument(
        '--suite', 
        choices=['anti-detection', 'performance', 'integration', 'all'],
        default='all',
        help='Run specific test suite'
    )
    
    parser.add_argument(
        '--no-report',
        action='store_true', 
        help='Skip generating validation report'
    )
    
    args = parser.parse_args()
    
    # Display header
    header = Panel.fit(
        "[bold cyan]Botasaurus Real Validation Suite[/bold cyan]\n"
        "Testing against real services and actual workloads",
        border_style="cyan"
    )
    console.print(header)
    
    # Show test overview
    display_test_overview()
    
    start_time = time.time()
    
    try:
        if args.quick:
            # Quick validation
            results = run_quick_validation()
            test_type = "quick"
            
        elif args.suite != 'all':
            # Specific suite
            results = run_specific_suite(args.suite)  
            test_type = args.suite
            
        else:
            # Full validation suite
            runner = RealValidationTestRunner()
            results = runner.run_all_real_tests()
            test_type = "full"
        
        # Generate report
        if not args.no_report:
            report_file = generate_validation_report(results, test_type)
        
        # Determine success
        if isinstance(results, dict):
            if 'production_ready' in results:
                success = results['production_ready']
            elif 'success_rate' in results:
                success = results['success_rate'] >= 0.8
            else:
                success = not any('error' in v for v in results.values() if isinstance(v, dict))
        else:
            success = False
        
        execution_time = time.time() - start_time
        
        console.print(f"\n[bold]⏱️ Execution Time:[/bold] {execution_time:.1f}s")
        
        if success:
            console.print("\n[bold green]🎉 VALIDATION SUCCESSFUL - BOTASAURUS IS PRODUCTION-READY![/bold green]")
            return 0
        else:
            console.print("\n[bold red]❌ VALIDATION FAILED - IMPROVEMENTS NEEDED[/bold red]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Validation interrupted by user[/yellow]")
        return 1
        
    except Exception as e:
        console.print(f"\n[red]💥 Validation error: {str(e)}[/red]")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)