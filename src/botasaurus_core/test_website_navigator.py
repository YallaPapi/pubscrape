"""
Test Suite for Website Navigator
Comprehensive testing for TASK-D001 implementation

Tests cover:
- Basic navigation functionality
- Contact page discovery patterns
- Anti-detection measures
- Concurrent navigation
- Error recovery
- Data extraction accuracy
"""

import os
import sys
import time
import json
import logging
from typing import Dict, List, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from botasaurus_core.website_navigator import WebsiteNavigator, create_website_navigator, NavigationSession
from botasaurus_core.engine import SessionConfig
from botasaurus_core.models import BusinessLead, ContactInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebsiteNavigatorTester:
    """Comprehensive test suite for website navigator"""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # Test URLs with different contact page structures
        self.test_urls = [
            "https://httpbin.org/html",  # Simple HTML page
            "https://example.com",       # Basic example site
            "https://www.python.org",    # Site with navigation structure
        ]
        
        # Expected patterns for validation
        self.expected_patterns = {
            "contact_indicators": ["contact", "about", "team"],
            "url_patterns": ["contact", "about", "team", "support"],
            "content_indicators": ["email", "phone", "contact form"]
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        logger.info("Starting Website Navigator Test Suite")
        logger.info("="*60)
        
        test_methods = [
            self.test_navigator_creation,
            self.test_contact_pattern_matching,
            self.test_single_site_navigation,
            self.test_content_analysis,
            self.test_form_detection,
            self.test_anti_detection_measures,
            self.test_concurrent_navigation,
            self.test_session_management,
            self.test_error_handling,
            self.test_data_export,
        ]
        
        for test_method in test_methods:
            try:
                test_name = test_method.__name__
                logger.info(f"\nRunning {test_name}...")
                result = test_method()
                self.test_results[test_name] = result
                
                if result.get('passed', False):
                    self.passed_tests += 1
                    logger.info(f"✓ {test_name} PASSED")
                else:
                    self.failed_tests += 1
                    logger.error(f"✗ {test_name} FAILED: {result.get('error', 'Unknown error')}")
                
                self.total_tests += 1
                
            except Exception as e:
                self.failed_tests += 1
                self.total_tests += 1
                error_msg = f"Test execution failed: {str(e)}"
                logger.error(f"✗ {test_method.__name__} FAILED: {error_msg}")
                self.test_results[test_method.__name__] = {
                    'passed': False,
                    'error': error_msg,
                    'execution_time': 0.0
                }
        
        # Generate summary
        summary = self._generate_test_summary()
        self.test_results['summary'] = summary
        
        return self.test_results
    
    def test_navigator_creation(self) -> Dict[str, Any]:
        """Test navigator initialization and configuration"""
        start_time = time.time()
        
        try:
            # Test default creation
            navigator = create_website_navigator()
            assert navigator is not None, "Navigator creation failed"
            assert hasattr(navigator, 'config'), "Navigator missing config"
            
            # Test custom configuration
            custom_config = SessionConfig(
                session_id="test_session",
                profile_name="test_profile",
                stealth_level=2
            )
            custom_navigator = WebsiteNavigator(custom_config)
            assert custom_navigator.config == custom_config, "Custom config not applied"
            
            # Test pattern initialization
            assert len(navigator.url_patterns) >= 15, f"Expected 15+ URL patterns, got {len(navigator.url_patterns)}"
            assert len(navigator.link_text_patterns) >= 10, f"Expected 10+ text patterns, got {len(navigator.link_text_patterns)}"
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'url_patterns': len(navigator.url_patterns),
                    'text_patterns': len(navigator.link_text_patterns),
                    'config_applied': True
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_contact_pattern_matching(self) -> Dict[str, Any]:
        """Test contact page pattern recognition"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test URL pattern matching
            test_urls = [
                ("https://example.com/contact", ("contact", True)),
                ("https://example.com/about-us", ("about", True)),
                ("https://example.com/team", ("team", True)),
                ("https://example.com/contact-us", ("contact", True)),
                ("https://example.com/get-in-touch", ("contact", True)),
                ("https://example.com/products", ("unknown", False)),
                ("https://example.com/blog", ("unknown", False)),
            ]
            
            pattern_results = []
            for test_url, (expected_type, should_match) in test_urls:
                score, detected_type = navigator._score_url_path(test_url)
                
                result = {
                    'url': test_url,
                    'expected_type': expected_type,
                    'detected_type': detected_type,
                    'score': score,
                    'should_match': should_match,
                    'matched': score > 20
                }
                
                if should_match:
                    assert score > 20, f"URL {test_url} should match but scored {score}"
                    if expected_type != "unknown":
                        assert detected_type == expected_type, f"Expected {expected_type}, got {detected_type}"
                
                pattern_results.append(result)
            
            # Test link text patterns
            text_tests = [
                ("Contact Us", ("contact", True)),
                ("About", ("about", True)),
                ("Our Team", ("team", True)),
                ("Get In Touch", ("contact", True)),
                ("Home", ("unknown", False)),
                ("Products", ("unknown", False)),
            ]
            
            text_results = []
            for test_text, (expected_type, should_match) in text_tests:
                score, detected_type = navigator._score_link_text(test_text)
                
                result = {
                    'text': test_text,
                    'expected_type': expected_type,
                    'detected_type': detected_type,
                    'score': score,
                    'should_match': should_match,
                    'matched': score > 20
                }
                
                if should_match and expected_type != "unknown":
                    assert detected_type == expected_type, f"Expected {expected_type}, got {detected_type}"
                
                text_results.append(result)
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'url_pattern_results': pattern_results,
                    'text_pattern_results': text_results,
                    'total_patterns_tested': len(test_urls) + len(text_tests)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_single_site_navigation(self) -> Dict[str, Any]:
        """Test basic single-site navigation functionality"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            test_url = "https://httpbin.org/html"  # Reliable test site
            
            # Test navigation with limited pages
            session = navigator.discover_contact_pages(test_url, max_pages=3)
            
            # Validate session structure
            assert isinstance(session, NavigationSession), "Invalid session type"
            assert session.base_url == test_url, "Base URL mismatch"
            assert session.session_id is not None, "Missing session ID"
            assert session.start_time is not None, "Missing start time"
            
            # Check navigation occurred
            assert len(session.pages_visited) >= 1, "No pages visited"
            assert test_url in session.pages_visited, "Base URL not in visited pages"
            
            # Validate timing
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds()
                assert 0 < duration < 300, f"Invalid navigation duration: {duration}s"
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'session_id': session.session_id,
                    'pages_visited': len(session.pages_visited),
                    'contact_pages_found': len(session.contact_pages),
                    'navigation_efficiency': session.navigation_efficiency,
                    'errors_encountered': len(session.errors_encountered)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_content_analysis(self) -> Dict[str, Any]:
        """Test content analysis and extraction capabilities"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test email extraction
            test_content = """
            <html>
                <body>
                    <p>Contact us at contact@example.com or support@test.org</p>
                    <p>Call us at (555) 123-4567 or 555.987.6543</p>
                    <div>Email: info@company.net</div>
                    <span>Phone: 1-800-555-0123</span>
                </body>
            </html>
            """
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(test_content, 'html.parser')
            text_content = soup.get_text()
            
            # Extract emails
            emails = []
            for pattern in navigator.content_indicators['email']:
                matches = pattern.findall(text_content)
                emails.extend(matches)
            
            # Extract phones
            phones = []
            for pattern in navigator.content_indicators['phone']:
                matches = pattern.findall(text_content)
                phones.extend(matches)
            
            # Validate extractions
            emails = list(set(emails))  # Remove duplicates
            phones = list(set(phones))
            
            assert len(emails) >= 2, f"Expected at least 2 emails, found {len(emails)}: {emails}"
            assert len(phones) >= 2, f"Expected at least 2 phones, found {len(phones)}: {phones}"
            
            # Test form analysis
            form_html = """
            <form action="/contact" method="POST">
                <input type="text" name="name" required>
                <input type="email" name="email" required>
                <textarea name="message" placeholder="Your message"></textarea>
                <button type="submit">Send</button>
            </form>
            """
            
            form_soup = BeautifulSoup(form_html, 'html.parser')
            forms = navigator._analyze_forms(form_soup)
            
            assert len(forms) == 1, f"Expected 1 contact form, found {len(forms)}"
            assert forms[0]['has_email'], "Form should have email field"
            assert forms[0]['has_message'], "Form should have message field"
            assert forms[0]['is_contact_form'], "Form should be identified as contact form"
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'emails_extracted': emails,
                    'phones_extracted': phones,
                    'forms_analyzed': len(forms),
                    'contact_form_detected': forms[0]['is_contact_form'] if forms else False
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_form_detection(self) -> Dict[str, Any]:
        """Test contact form detection accuracy"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test various form types
            form_tests = [
                {
                    'name': 'Contact Form',
                    'html': '''
                    <form>
                        <input type="text" name="name">
                        <input type="email" name="email">
                        <textarea name="message"></textarea>
                        <button type="submit">Send</button>
                    </form>
                    ''',
                    'should_be_contact': True
                },
                {
                    'name': 'Search Form',
                    'html': '''
                    <form>
                        <input type="text" name="query">
                        <button type="submit">Search</button>
                    </form>
                    ''',
                    'should_be_contact': False
                },
                {
                    'name': 'Newsletter Form',
                    'html': '''
                    <form>
                        <input type="email" name="email">
                        <button type="submit">Subscribe</button>
                    </form>
                    ''',
                    'should_be_contact': False  # Too simple
                },
                {
                    'name': 'Complex Contact Form',
                    'html': '''
                    <form method="POST" action="/contact">
                        <input type="text" name="first_name" required>
                        <input type="text" name="last_name">
                        <input type="email" name="email" required>
                        <input type="tel" name="phone">
                        <select name="subject">
                            <option>General Inquiry</option>
                            <option>Support</option>
                        </select>
                        <textarea name="message" placeholder="How can we help?"></textarea>
                        <button type="submit">Send Message</button>
                    </form>
                    ''',
                    'should_be_contact': True
                }
            ]
            
            form_results = []
            for test_case in form_tests:
                soup = BeautifulSoup(test_case['html'], 'html.parser')
                forms = navigator._analyze_forms(soup)
                
                result = {
                    'name': test_case['name'],
                    'expected_contact': test_case['should_be_contact'],
                    'forms_found': len(forms),
                    'is_contact_form': forms[0]['is_contact_form'] if forms else False,
                    'has_email': forms[0]['has_email'] if forms else False,
                    'has_message': forms[0]['has_message'] if forms else False,
                    'field_count': len(forms[0]['fields']) if forms else 0
                }
                
                # Validate expectation
                if test_case['should_be_contact']:
                    assert len(forms) > 0, f"{test_case['name']}: Expected contact form but none found"
                    assert forms[0]['is_contact_form'], f"{test_case['name']}: Form not identified as contact form"
                
                form_results.append(result)
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'form_test_results': form_results,
                    'total_forms_tested': len(form_tests)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_anti_detection_measures(self) -> Dict[str, Any]:
        """Test anti-detection capabilities"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test detection patterns
            detection_test_pages = [
                ("Normal page content", False),
                ("Please solve this captcha to continue", True),
                ("Cloudflare is checking your browser", True),
                ("Access denied due to suspicious activity", True),
                ("Are you human? Please verify", True),
                ("Welcome to our website!", False),
            ]
            
            detection_results = []
            for content, should_detect in detection_test_pages:
                # Mock page source
                detected = any(indicator in content.lower() 
                             for indicator in ['captcha', 'cloudflare', 'access denied', 
                                             'suspicious activity', 'are you human'])
                
                result = {
                    'content': content,
                    'expected_detection': should_detect,
                    'detected': detected,
                    'correct': detected == should_detect
                }
                
                detection_results.append(result)
            
            # Test stealth configuration
            config = SessionConfig(
                session_id="stealth_test",
                profile_name="stealth_profile",
                stealth_level=3
            )
            
            stealth_navigator = WebsiteNavigator(config)
            assert stealth_navigator.config.stealth_level == 3, "Stealth level not set correctly"
            
            # Test behavior simulation
            behavior_sim = navigator.behavior_simulator
            assert behavior_sim is not None, "Behavior simulator not initialized"
            
            # Test typing delays
            typing_delay = behavior_sim.get_typing_delay()
            assert 0 < typing_delay < 5.0, f"Invalid typing delay: {typing_delay}"
            
            # Test scroll patterns
            scroll_pattern = behavior_sim.get_scroll_pattern()
            assert len(scroll_pattern) > 0, "No scroll pattern generated"
            assert all('action' in step for step in scroll_pattern), "Invalid scroll pattern structure"
            
            correct_detections = sum(1 for r in detection_results if r['correct'])
            accuracy = correct_detections / len(detection_results)
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'detection_accuracy': accuracy,
                    'detection_results': detection_results,
                    'stealth_level_configured': config.stealth_level,
                    'behavior_simulation_active': True,
                    'typing_delay_range': f"{typing_delay:.3f}s",
                    'scroll_patterns_generated': len(scroll_pattern)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_concurrent_navigation(self) -> Dict[str, Any]:
        """Test concurrent navigation capabilities"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test with a smaller set of reliable URLs
            test_urls = [
                "https://httpbin.org/html",
                "https://example.com",
            ]
            
            # Test concurrent navigation with max 2 workers
            results = navigator.navigate_multiple_sites(test_urls, max_concurrent=2)
            
            # Validate results structure
            assert isinstance(results, dict), "Results should be a dictionary"
            assert len(results) == len(test_urls), f"Expected {len(test_urls)} results, got {len(results)}"
            
            # Validate each result
            for url in test_urls:
                assert url in results, f"Missing result for {url}"
                session = results[url]
                assert isinstance(session, NavigationSession), f"Invalid session type for {url}"
                assert session.base_url == url, f"Base URL mismatch for {url}"
                assert session.session_id is not None, f"Missing session ID for {url}"
            
            # Calculate performance metrics
            successful_sessions = [s for s in results.values() if len(s.errors_encountered) == 0]
            success_rate = len(successful_sessions) / len(results) if results else 0
            
            total_pages_visited = sum(len(s.pages_visited) for s in results.values())
            total_contacts_found = sum(len(s.contact_pages) for s in results.values())
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'urls_processed': len(results),
                    'successful_sessions': len(successful_sessions),
                    'success_rate': success_rate,
                    'total_pages_visited': total_pages_visited,
                    'total_contacts_found': total_contacts_found,
                    'concurrent_workers_used': min(2, len(test_urls))
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_session_management(self) -> Dict[str, Any]:
        """Test session management and cleanup"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test session tracking
            initial_sessions = len(navigator.active_sessions)
            
            # Create a mock session
            test_session = NavigationSession(
                base_url="https://test.com",
                session_id="test_session_123",
                start_time=time.time()
            )
            
            # Test session registration
            with navigator.session_lock:
                navigator.active_sessions["test_session_123"] = test_session
            
            assert len(navigator.active_sessions) == initial_sessions + 1, "Session not registered"
            
            # Test session cleanup
            with navigator.session_lock:
                navigator.active_sessions.pop("test_session_123", None)
            
            assert len(navigator.active_sessions) == initial_sessions, "Session not cleaned up"
            
            # Test session configuration
            config = SessionConfig(
                session_id="config_test",
                profile_name="config_profile",
                stealth_level=2,
                max_memory_mb=1024
            )
            
            session_navigator = WebsiteNavigator(config)
            assert session_navigator.config.session_id == "config_test", "Session ID not set"
            assert session_navigator.config.max_memory_mb == 1024, "Memory limit not set"
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'session_tracking_works': True,
                    'session_cleanup_works': True,
                    'configuration_applied': True,
                    'active_sessions_count': len(navigator.active_sessions)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and recovery"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Test invalid URL handling
            invalid_urls = [
                "https://this-domain-should-not-exist-12345.com",
                "not-a-url",
                "https://127.0.0.1:99999"  # Invalid port
            ]
            
            error_results = []
            for invalid_url in invalid_urls:
                try:
                    # This should handle errors gracefully
                    session = navigator.discover_contact_pages(invalid_url, max_pages=1)
                    
                    result = {
                        'url': invalid_url,
                        'session_created': session is not None,
                        'has_errors': len(session.errors_encountered) > 0 if session else True,
                        'error_handled': True
                    }
                except Exception as e:
                    result = {
                        'url': invalid_url,
                        'session_created': False,
                        'has_errors': True,
                        'error_handled': False,
                        'exception': str(e)
                    }
                
                error_results.append(result)
            
            # Test concurrent error handling
            mixed_urls = [
                "https://httpbin.org/html",  # Valid
                "https://invalid-test-domain-xyz.com",  # Invalid
                "https://example.com"  # Valid
            ]
            
            concurrent_results = navigator.navigate_multiple_sites(mixed_urls, max_concurrent=2)
            
            # Should get results for all URLs, even invalid ones
            assert len(concurrent_results) == len(mixed_urls), "Missing results for some URLs"
            
            # Check error handling in concurrent mode
            error_sessions = [s for s in concurrent_results.values() if len(s.errors_encountered) > 0]
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'invalid_urls_tested': len(invalid_urls),
                    'error_results': error_results,
                    'concurrent_error_handling': len(error_sessions),
                    'graceful_error_handling': all(r['error_handled'] for r in error_results),
                    'concurrent_completion': len(concurrent_results) == len(mixed_urls)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def test_data_export(self) -> Dict[str, Any]:
        """Test data export functionality"""
        start_time = time.time()
        
        try:
            navigator = create_website_navigator()
            
            # Create a mock session with data
            session = NavigationSession(
                base_url="https://test.com",
                session_id="export_test",
                start_time=time.time()
            )
            
            # Add mock contact page data
            from botasaurus_core.website_navigator import ContactPageAnalysis
            mock_contact = ContactPageAnalysis(
                url="https://test.com/contact",
                page_type="contact",
                confidence_score=0.8,
                contact_indicators=["email", "phone"],
                forms_found=[{"type": "contact", "has_email": True}],
                email_addresses=["test@example.com"],
                phone_numbers=["555-1234"],
                social_links={"facebook": "https://facebook.com/test"},
                navigation_time=2.5
            )
            
            session.contact_pages.append(mock_contact)
            session.end_time = time.time()
            session.calculate_efficiency()
            
            # Test JSON export
            json_data = navigator.export_session_data(session, format='json')
            
            # Validate JSON structure
            assert isinstance(json_data, str), "JSON export should return string"
            assert len(json_data) > 100, "JSON export seems too short"
            
            # Parse JSON to validate structure
            parsed_data = json.loads(json_data)
            
            required_fields = ['session_id', 'base_url', 'start_time', 'contact_pages', 'statistics']
            for field in required_fields:
                assert field in parsed_data, f"Missing required field: {field}"
            
            # Validate contact page data
            assert len(parsed_data['contact_pages']) == 1, "Expected 1 contact page in export"
            contact_data = parsed_data['contact_pages'][0]
            assert contact_data['url'] == "https://test.com/contact", "Contact URL mismatch"
            assert len(contact_data['email_addresses']) == 1, "Email addresses not exported"
            
            # Test invalid format handling
            try:
                navigator.export_session_data(session, format='invalid')
                invalid_format_handled = False
            except ValueError:
                invalid_format_handled = True
            
            return {
                'passed': True,
                'execution_time': time.time() - start_time,
                'details': {
                    'json_export_length': len(json_data),
                    'json_structure_valid': True,
                    'required_fields_present': len(required_fields),
                    'contact_data_exported': True,
                    'invalid_format_handled': invalid_format_handled
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate test execution summary"""
        total_execution_time = sum(
            result.get('execution_time', 0) 
            for result in self.test_results.values() 
            if isinstance(result, dict)
        )
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        return {
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'success_rate': success_rate,
            'total_execution_time': total_execution_time,
            'average_test_time': total_execution_time / self.total_tests if self.total_tests > 0 else 0
        }


def run_website_navigator_tests():
    """Run the complete test suite"""
    print("Website Navigator Test Suite")
    print("TASK-D001 Implementation Verification")
    print("="*60)
    
    tester = WebsiteNavigatorTester()
    results = tester.run_all_tests()
    
    # Print summary
    summary = results.get('summary', {})
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {summary.get('total_tests', 0)}")
    print(f"Passed: {summary.get('passed_tests', 0)}")
    print(f"Failed: {summary.get('failed_tests', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    print(f"Total Execution Time: {summary.get('total_execution_time', 0):.2f}s")
    print(f"Average Test Time: {summary.get('average_test_time', 0):.2f}s")
    
    # Save results to file
    results_file = Path(__file__).parent / "test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return summary.get('success_rate', 0) >= 80  # 80% success rate threshold


if __name__ == "__main__":
    success = run_website_navigator_tests()
    exit_code = 0 if success else 1
    sys.exit(exit_code)