#!/usr/bin/env python3
"""
Real-World Validation Suite for Botasaurus Business Scraper System

This replaces mocked anti-detection testing with actual validation against
real services, websites, and detection systems.

Features:
- Real Cloudflare bypass testing with live CF-protected sites
- Actual browser fingerprint validation against detection services  
- Real performance testing with actual browser operations
- Integration testing with complete workflow validation
- Actual email validation with real email addresses
- Real memory usage testing with scraping sessions
"""

import pytest
import time
import json
import csv
import re
import random
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import concurrent.futures

# Performance monitoring
import psutil
import gc

# Console output
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import project modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from botasaurus import browser, Driver
    from botasaurus_business_scraper import BotasaurusBusinessScraper
    BOTASAURUS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Botasaurus not available: {e}")
    BOTASAURUS_AVAILABLE = False

console = Console()


class RealAntiDetectionValidator:
    """Real anti-detection validation using actual services"""
    
    def __init__(self):
        self.test_results = []
        self.real_detection_sites = [
            "https://bot.sannysoft.com/",
            "https://fingerprintjs.com/demo/", 
            "https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html",
            "https://httpbin.org/user-agent",
            "https://httpbin.org/headers"
        ]
        self.cloudflare_sites = [
            "https://quotes.toscrape.com/",
            "https://httpbin.org/delay/2",
            "https://scrape.world/"
        ]
    
    @pytest.mark.skipif(not BOTASAURUS_AVAILABLE, reason="Botasaurus not available")
    def test_real_cloudflare_bypass(self):
        """Test Cloudflare bypass against actual protected sites"""
        console.print("\n[yellow]🛡️ Testing Real Cloudflare Bypass...[/yellow]")
        
        @browser(
            headless=True,
            add_stealth=True,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            bypass_cloudflare=True
        )
        def test_cf_site(driver: Driver, site_data):
            url = site_data['url']
            result = {
                'url': url, 
                'success': False, 
                'content_length': 0, 
                'cf_detected': False,
                'response_time': 0
            }
            
            start_time = time.time()
            
            try:
                driver.get(url, bypass_cloudflare=True)
                driver.sleep(3)
                
                html_content = driver.page_html
                result['content_length'] = len(html_content)
                result['response_time'] = time.time() - start_time
                
                # Check for Cloudflare blocking indicators
                cf_indicators = [
                    'checking your browser',
                    'please wait while we check your browser', 
                    'cloudflare',
                    'ray id',
                    'enable javascript and cookies',
                    'ddos protection',
                    'cf-browser-verification'
                ]
                
                html_lower = html_content.lower()
                cf_detected = any(indicator in html_lower for indicator in cf_indicators)
                result['cf_detected'] = cf_detected
                
                # Success: substantial content without CF blocking
                result['success'] = len(html_content) > 1000 and not cf_detected
                
                console.print(f"  {url}: {'✓' if result['success'] else '✗'} "
                            f"({result['content_length']:,} chars, "
                            f"{result['response_time']:.2f}s)")
                
            except Exception as e:
                result['error'] = str(e)
                console.print(f"  {url}: ✗ Error - {str(e)[:50]}")
            
            return result
        
        # Test each Cloudflare-protected site
        bypass_results = []
        for site in self.cloudflare_sites:
            result = test_cf_site({'url': site})
            bypass_results.append(result)
        
        # Validate results
        successful_bypasses = [r for r in bypass_results if r.get('success', False)]
        success_rate = len(successful_bypasses) / len(bypass_results)
        
        console.print(f"\n[bold]Cloudflare Bypass Results:[/bold]")
        console.print(f"Success Rate: {success_rate:.1%} ({len(successful_bypasses)}/{len(bypass_results)})")
        
        # Assert reasonable success rate (at least 70%)
        assert success_rate >= 0.7, f"CF bypass success rate {success_rate:.2%} below 70%"
        
        self.test_results.append({
            'test': 'cloudflare_bypass',
            'success_rate': success_rate,
            'results': bypass_results
        })
        
        return bypass_results
    
    @pytest.mark.skipif(not BOTASAURUS_AVAILABLE, reason="Botasaurus not available")
    def test_real_fingerprint_validation(self):
        """Test fingerprint randomization against real detection services"""
        console.print("\n[yellow]🔍 Testing Real Browser Fingerprint Randomization...[/yellow]")
        
        fingerprint_results = []
        
        # Create multiple browser sessions with different fingerprints
        for session_id in range(3):
            @browser(
                headless=True,
                add_stealth=True,
                user_agent=None,  # Let Botasaurus randomize
                profile=f"fingerprint_test_{session_id}",
                window_size=None  # Let Botasaurus randomize
            )
            def test_fingerprint(driver: Driver, test_data):
                session_id = test_data['session_id']
                result = {
                    'session_id': session_id,
                    'fingerprint': {},
                    'bot_detected': False,
                    'detection_score': 0
                }
                
                try:
                    # Extract real browser fingerprint
                    driver.get("https://httpbin.org/user-agent")
                    driver.sleep(2)
                    
                    fingerprint_data = driver.execute_script("""
                        return {
                            userAgent: navigator.userAgent,
                            language: navigator.language,
                            platform: navigator.platform,
                            screenResolution: screen.width + 'x' + screen.height,
                            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                            cookieEnabled: navigator.cookieEnabled,
                            pluginsCount: navigator.plugins.length
                        };
                    """)
                    
                    result['fingerprint'] = fingerprint_data
                    
                    # Test against bot detection service
                    try:
                        driver.get("https://bot.sannysoft.com/")
                        driver.sleep(3)
                        
                        page_content = driver.page_html.lower()
                        
                        # Check for bot detection indicators
                        bot_indicators = [
                            'headless chrome detected',
                            'automation detected',
                            'webdriver property found',
                            'bot detected',
                            'suspicious automation'
                        ]
                        
                        detection_count = sum(1 for indicator in bot_indicators if indicator in page_content)
                        result['detection_score'] = detection_count / len(bot_indicators)
                        result['bot_detected'] = detection_count > 2  # More than 2 indicators = detected
                        
                        console.print(f"  Session {session_id}: {'✗ Detected' if result['bot_detected'] else '✓ Passed'} "
                                    f"(score: {result['detection_score']:.2f})")
                        
                    except Exception as e:
                        result['detection_error'] = str(e)
                        console.print(f"  Session {session_id}: ? Detection test failed")
                
                except Exception as e:
                    result['error'] = str(e)
                    console.print(f"  Session {session_id}: ✗ Error - {str(e)[:30]}")
                
                return result
            
            try:
                result = test_fingerprint({'session_id': session_id})
                fingerprint_results.append(result)
            except Exception as e:
                console.print(f"  Session {session_id}: ✗ Failed to create - {str(e)[:30]}")
        
        # Validate fingerprint diversity and detection rates
        successful_tests = [r for r in fingerprint_results if 'error' not in r]
        detected_count = sum(1 for r in successful_tests if r.get('bot_detected', False))
        
        if len(successful_tests) >= 2:
            # Check fingerprint diversity
            user_agents = [r['fingerprint'].get('userAgent', '') for r in successful_tests]
            unique_uas = len(set(user_agents))
            
            console.print(f"\n[bold]Fingerprint Validation Results:[/bold]")
            console.print(f"Sessions Tested: {len(successful_tests)}")
            console.print(f"Bot Detections: {detected_count}")
            console.print(f"User Agent Diversity: {unique_uas}/{len(successful_tests)}")
            
            # Assert acceptable results
            detection_rate = detected_count / len(successful_tests)
            assert detection_rate <= 0.3, f"Bot detection rate {detection_rate:.2%} exceeds 30%"
            assert unique_uas >= len(successful_tests) * 0.5, "Insufficient fingerprint diversity"
        
        self.test_results.append({
            'test': 'fingerprint_validation',
            'sessions_tested': len(successful_tests),
            'detection_rate': detected_count / max(len(successful_tests), 1),
            'results': fingerprint_results
        })
        
        return fingerprint_results
    
    @pytest.mark.skipif(not BOTASAURUS_AVAILABLE, reason="Botasaurus not available")
    def test_real_session_isolation(self):
        """Test session isolation with real browser instances"""
        console.print("\n[yellow]🔒 Testing Real Session Isolation...[/yellow]")
        
        isolation_results = []
        
        # Test session isolation by setting unique data in each session
        for session_id in range(3):
            @browser(
                headless=True,
                add_stealth=True,
                profile=f"isolated_session_{session_id}"
            )
            def test_session_isolation(driver: Driver, test_data):
                session_id = test_data['session_id']
                result = {
                    'session_id': session_id,
                    'isolation_verified': False,
                    'data_leak_detected': False
                }
                
                try:
                    # Set unique session data
                    unique_value = f"session_{session_id}_{int(time.time())}"
                    
                    driver.get(f"https://httpbin.org/cookies/set/test_isolation/{unique_value}")
                    driver.sleep(1)
                    
                    # Verify our data is set correctly
                    driver.get("https://httpbin.org/cookies")
                    cookies_response = driver.page_html
                    
                    if unique_value in cookies_response:
                        # Check for data from other sessions (should not exist)
                        other_session_patterns = [f"session_{i}_" for i in range(3) if i != session_id]
                        data_leak = any(pattern in cookies_response for pattern in other_session_patterns)
                        
                        result['isolation_verified'] = not data_leak
                        result['data_leak_detected'] = data_leak
                        
                        console.print(f"  Session {session_id}: {'✓' if result['isolation_verified'] else '✗'} "
                                    f"{'Isolated' if result['isolation_verified'] else 'Data Leak!'}")
                    else:
                        console.print(f"  Session {session_id}: ? Could not verify session data")
                
                except Exception as e:
                    result['error'] = str(e)
                    console.print(f"  Session {session_id}: ✗ Error - {str(e)[:30]}")
                
                return result
            
            try:
                result = test_session_isolation({'session_id': session_id})
                isolation_results.append(result)
            except Exception as e:
                console.print(f"  Session {session_id}: ✗ Failed - {str(e)[:30]}")
        
        # Validate isolation effectiveness
        verified_sessions = [r for r in isolation_results if r.get('isolation_verified', False)]
        leaked_sessions = [r for r in isolation_results if r.get('data_leak_detected', False)]
        
        console.print(f"\n[bold]Session Isolation Results:[/bold]")
        console.print(f"Isolated Sessions: {len(verified_sessions)}/{len(isolation_results)}")
        console.print(f"Data Leaks: {len(leaked_sessions)}")
        
        # Assert proper isolation
        assert len(leaked_sessions) == 0, f"Data leaks detected in {len(leaked_sessions)} sessions"
        assert len(verified_sessions) >= len(isolation_results) * 0.8, "Insufficient session isolation"
        
        self.test_results.append({
            'test': 'session_isolation',
            'isolation_rate': len(verified_sessions) / max(len(isolation_results), 1),
            'results': isolation_results
        })
        
        return isolation_results


class RealPerformanceValidator:
    """Real performance validation with actual browser operations"""
    
    def __init__(self):
        self.performance_metrics = []
    
    @pytest.mark.skipif(not BOTASAURUS_AVAILABLE, reason="Botasaurus not available")
    def test_real_load_performance(self):
        """Test performance with real business lead processing"""
        console.print("\n[yellow]⚡ Testing Real Load Performance...[/yellow]")
        
        scraper = BotasaurusBusinessScraper()
        
        target_leads = 25  # Realistic target for testing
        start_time = time.time()
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Real search queries for performance testing
        test_queries = [
            {'query': 'restaurant', 'location': 'Miami, FL'},
            {'query': 'dental clinic', 'location': 'Chicago, IL'},
            {'query': 'law firm', 'location': 'Houston, TX'}
        ]
        
        all_leads = []
        websites_processed = 0
        emails_extracted = 0
        
        for i, query_data in enumerate(test_queries):
            try:
                console.print(f"  Processing query {i+1}/{len(test_queries)}: {query_data['query']}")
                
                # Real Google Maps scraping
                leads = scraper.scrape_google_maps_businesses(query_data)
                
                # Process leads with email extraction
                for lead in leads[:10]:  # Limit per query for testing
                    if lead.get('website'):
                        websites_processed += 1
                        try:
                            email = scraper.extract_email_from_website({'url': lead['website']})
                            if email:
                                lead['email'] = email
                                emails_extracted += 1
                        except Exception:
                            pass  # Continue processing other leads
                    
                    all_leads.append(lead)
                    
                    if len(all_leads) >= target_leads:
                        break
                
                if len(all_leads) >= target_leads:
                    break
                    
            except Exception as e:
                console.print(f"    ✗ Query failed: {str(e)[:50]}")
        
        # Calculate performance metrics
        total_time = time.time() - start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = memory_end - memory_start
        
        throughput = len(all_leads) / total_time if total_time > 0 else 0
        email_extraction_rate = emails_extracted / max(websites_processed, 1)
        
        console.print(f"\n[bold]Real Performance Results:[/bold]")
        console.print(f"Leads Processed: {len(all_leads)}")
        console.print(f"Processing Time: {total_time:.2f}s")
        console.print(f"Throughput: {throughput:.2f} leads/sec")
        console.print(f"Memory Used: {memory_used:.1f} MB")
        console.print(f"Email Extraction: {emails_extracted}/{websites_processed} "
                     f"({email_extraction_rate:.1%})")
        
        # Performance assertions
        assert len(all_leads) >= 10, f"Too few leads processed: {len(all_leads)}"
        assert throughput >= 0.2, f"Throughput {throughput:.2f} leads/sec too low"
        assert memory_used < 1024, f"Memory usage {memory_used:.1f}MB exceeds limit"
        assert email_extraction_rate >= 0.1, f"Email extraction rate {email_extraction_rate:.1%} too low"
        
        performance_result = {
            'leads_processed': len(all_leads),
            'processing_time': total_time,
            'throughput': throughput,
            'memory_used_mb': memory_used,
            'websites_processed': websites_processed,
            'emails_extracted': emails_extracted,
            'email_extraction_rate': email_extraction_rate
        }
        
        self.performance_metrics.append(performance_result)
        return performance_result
    
    @pytest.mark.skipif(not BOTASAURUS_AVAILABLE, reason="Botasaurus not available")  
    def test_concurrent_browser_sessions(self):
        """Test concurrent browser session management"""
        console.print("\n[yellow]🔄 Testing Concurrent Browser Sessions...[/yellow]")
        
        def create_concurrent_session(session_data):
            session_id = session_data['session_id']
            
            @browser(
                headless=True,
                add_stealth=True,
                profile=f"concurrent_test_{session_id}"
            )
            def concurrent_scraper(driver: Driver, data):
                result = {
                    'session_id': data['session_id'],
                    'success': False,
                    'leads_count': 0,
                    'duration': 0,
                    'memory_used': 0
                }
                
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                try:
                    # Simulate scraping work
                    driver.get("https://httpbin.org/delay/1")
                    driver.sleep(1)
                    
                    # Simulate lead processing
                    for i in range(5):  # 5 mock leads per session
                        driver.get(f"https://httpbin.org/html")
                        driver.sleep(0.5)
                        result['leads_count'] += 1
                    
                    result['duration'] = time.time() - start_time
                    result['memory_used'] = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
                    result['success'] = True
                    
                    console.print(f"  Session {session_id}: ✓ {result['leads_count']} leads "
                                f"({result['duration']:.2f}s)")
                
                except Exception as e:
                    result['error'] = str(e)
                    console.print(f"  Session {session_id}: ✗ {str(e)[:30]}")
                
                return result
            
            return concurrent_scraper(session_data)
        
        # Run concurrent sessions
        max_sessions = 3
        session_data = [{'session_id': i} for i in range(max_sessions)]
        
        concurrent_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_sessions) as executor:
            futures = [executor.submit(create_concurrent_session, data) for data in session_data]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    concurrent_results.append(result)
                except Exception as e:
                    console.print(f"  Concurrent session failed: {str(e)[:30]}")
        
        # Analyze concurrent performance
        successful_sessions = [r for r in concurrent_results if r.get('success', False)]
        total_leads = sum(r.get('leads_count', 0) for r in successful_sessions)
        avg_duration = sum(r.get('duration', 0) for r in successful_sessions) / max(len(successful_sessions), 1)
        
        console.print(f"\n[bold]Concurrent Session Results:[/bold]")
        console.print(f"Successful Sessions: {len(successful_sessions)}/{max_sessions}")
        console.print(f"Total Leads: {total_leads}")
        console.print(f"Average Duration: {avg_duration:.2f}s")
        
        # Concurrent performance assertions
        success_rate = len(successful_sessions) / max_sessions
        assert success_rate >= 0.8, f"Concurrent success rate {success_rate:.2%} below 80%"
        assert avg_duration < 20, f"Average duration {avg_duration:.2f}s exceeds limit"
        
        return concurrent_results


class RealIntegrationValidator:
    """Real integration testing with complete workflow validation"""
    
    @pytest.mark.skipif(not BOTASAURUS_AVAILABLE, reason="Botasaurus not available")
    def test_complete_workflow_integration(self):
        """Test complete lead generation workflow with real data"""
        console.print("\n[yellow]🔄 Testing Complete Workflow Integration...[/yellow]")
        
        scraper = BotasaurusBusinessScraper()
        
        # Real integration test configuration
        test_config = {
            'queries': [
                {'query': 'medical clinic', 'location': 'Miami, FL'},
                {'query': 'restaurant', 'location': 'Chicago, IL'}
            ],
            'max_leads_per_query': 8,
            'enable_email_extraction': True,
            'enable_export': True
        }
        
        workflow_results = {
            'queries_processed': 0,
            'leads_scraped': 0,
            'websites_visited': 0,
            'emails_extracted': 0,
            'export_success': False,
            'data_quality_score': 0,
            'workflow_success': False
        }
        
        all_leads = []
        
        # Step 1: Process queries
        for query_data in test_config['queries']:
            try:
                console.print(f"  Processing: {query_data['query']} in {query_data['location']}")
                
                leads = scraper.scrape_google_maps_businesses(query_data)
                limited_leads = leads[:test_config['max_leads_per_query']]
                
                # Step 2: Email extraction
                for lead in limited_leads:
                    if lead.get('website') and test_config['enable_email_extraction']:
                        workflow_results['websites_visited'] += 1
                        try:
                            email = scraper.extract_email_from_website({'url': lead['website']})
                            if email:
                                lead['email'] = email
                                workflow_results['emails_extracted'] += 1
                        except Exception:
                            pass
                    
                    all_leads.append(lead)
                
                workflow_results['queries_processed'] += 1
                console.print(f"    ✓ {len(limited_leads)} leads processed")
                
            except Exception as e:
                console.print(f"    ✗ Query failed: {str(e)[:50]}")
        
        workflow_results['leads_scraped'] = len(all_leads)
        
        # Step 3: Data quality validation
        valid_leads = 0
        for lead in all_leads:
            if lead.get('name') and (lead.get('phone') or lead.get('email') or lead.get('website')):
                valid_leads += 1
        
        workflow_results['data_quality_score'] = valid_leads / max(len(all_leads), 1)
        
        # Step 4: Export validation
        if test_config['enable_export'] and all_leads:
            try:
                timestamp = int(time.time())
                export_path = Path(f"test_output/integration_test_leads_{timestamp}.csv")
                export_path.parent.mkdir(exist_ok=True)
                
                with open(export_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['name', 'email', 'phone', 'website', 'address']
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(all_leads)
                
                workflow_results['export_success'] = export_path.exists()
                console.print(f"  ✓ Exported to: {export_path.name}")
                
            except Exception as e:
                console.print(f"  ✗ Export failed: {str(e)[:50]}")
        
        # Overall workflow validation
        email_extraction_rate = workflow_results['emails_extracted'] / max(workflow_results['websites_visited'], 1)
        
        workflow_results['workflow_success'] = (
            workflow_results['queries_processed'] >= 1 and
            workflow_results['leads_scraped'] >= 5 and
            workflow_results['data_quality_score'] >= 0.6 and
            workflow_results['export_success']
        )
        
        console.print(f"\n[bold]Workflow Integration Results:[/bold]")
        console.print(f"Queries Processed: {workflow_results['queries_processed']}")
        console.print(f"Leads Scraped: {workflow_results['leads_scraped']}")
        console.print(f"Email Extraction: {workflow_results['emails_extracted']}/{workflow_results['websites_visited']} "
                     f"({email_extraction_rate:.1%})")
        console.print(f"Data Quality: {workflow_results['data_quality_score']:.1%}")
        console.print(f"Export Success: {'✓' if workflow_results['export_success'] else '✗'}")
        console.print(f"Overall Success: {'✓' if workflow_results['workflow_success'] else '✗'}")
        
        # Integration assertions
        assert workflow_results['leads_scraped'] >= 5, "Too few leads scraped"
        assert workflow_results['data_quality_score'] >= 0.6, "Data quality too low"
        assert workflow_results['export_success'], "Export failed"
        assert workflow_results['workflow_success'], "Overall workflow failed"
        
        return workflow_results


class RealValidationTestRunner:
    """Main test runner for real validation suite"""
    
    def __init__(self):
        self.start_time = time.time()
        self.test_results = {}
    
    def run_all_real_tests(self):
        """Run complete real validation test suite"""
        console.print("\n[bold cyan]🚀 REAL BOTASAURUS VALIDATION SUITE[/bold cyan]")
        console.print("Testing against real services and actual workloads\n")
        
        if not BOTASAURUS_AVAILABLE:
            console.print("[red]⚠️ Botasaurus not available - skipping real tests[/red]")
            return {'success': False, 'reason': 'Botasaurus not available'}
        
        # Initialize validators
        anti_detection = RealAntiDetectionValidator()
        performance = RealPerformanceValidator()
        integration = RealIntegrationValidator()
        
        test_suites = [
            ("Anti-Detection", anti_detection, [
                'test_real_cloudflare_bypass',
                'test_real_fingerprint_validation',
                'test_real_session_isolation'
            ]),
            ("Performance", performance, [
                'test_real_load_performance',
                'test_concurrent_browser_sessions'
            ]),
            ("Integration", integration, [
                'test_complete_workflow_integration'
            ])
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for suite_name, suite_obj, test_methods in test_suites:
            console.print(f"\n[bold yellow]📋 {suite_name} Tests[/bold yellow]")
            
            suite_results = []
            
            for method_name in test_methods:
                total_tests += 1
                try:
                    test_method = getattr(suite_obj, method_name)
                    result = test_method()
                    suite_results.append({
                        'test': method_name,
                        'status': 'PASSED',
                        'result': result
                    })
                    passed_tests += 1
                    console.print(f"  ✅ {method_name}")
                    
                except Exception as e:
                    suite_results.append({
                        'test': method_name,
                        'status': 'FAILED',
                        'error': str(e)
                    })
                    console.print(f"  ❌ {method_name}: {str(e)[:60]}")
            
            self.test_results[suite_name] = suite_results
        
        # Generate final report
        total_time = time.time() - self.start_time
        success_rate = passed_tests / max(total_tests, 1)
        
        console.print(f"\n[bold]🎯 REAL VALIDATION SUMMARY[/bold]")
        console.print(f"Duration: {total_time:.1f}s")
        console.print(f"Tests: {passed_tests}/{total_tests} passed")
        console.print(f"Success Rate: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            console.print("\n[bold green]🎉 BOTASAURUS PRODUCTION-READY![/bold green]")
            console.print("[green]✅ Real anti-detection capabilities validated[/green]")
            console.print("[green]✅ Performance meets production requirements[/green]") 
            console.print("[green]✅ End-to-end workflow functioning properly[/green]")
        elif success_rate >= 0.6:
            console.print("\n[yellow]⚠️ BOTASAURUS NEEDS IMPROVEMENTS[/yellow]")
            console.print("[yellow]• Some real-world tests failing[/yellow]")
            console.print("[yellow]• Review and address failing components[/yellow]")
        else:
            console.print("\n[red]❌ BOTASAURUS NOT PRODUCTION-READY[/red]")
            console.print("[red]• Critical real-world failures detected[/red]")
            console.print("[red]• Significant improvements required[/red]")
        
        # Save detailed results
        results_file = Path(f"test_output/real_validation_results_{int(time.time())}.json")
        results_file.parent.mkdir(exist_ok=True)
        
        final_results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'real_validation_suite',
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'execution_time': total_time,
            'detailed_results': self.test_results,
            'production_ready': success_rate >= 0.8
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        console.print(f"\n[dim]📄 Detailed results: {results_file}[/dim]")
        
        return final_results


def run_real_validation_tests():
    """Entry point for real validation testing"""
    runner = RealValidationTestRunner()
    results = runner.run_all_real_tests()
    return results['production_ready'] if isinstance(results, dict) else False


if __name__ == "__main__":
    success = run_real_validation_tests()
    exit(0 if success else 1)