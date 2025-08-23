#!/usr/bin/env python3
"""
Comprehensive Test Suite for Email Extraction Components
Tests all email hunting, pattern matching, and scoring functionality
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# Import our modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from extractors.email_patterns import (
    EmailPatternLibrary, ContactFormAnalyzer,
    extract_emails_comprehensive, analyze_contact_forms
)
from extractors.website_navigator import WebsiteNavigator
from extractors.email_hunter import EmailHunter, EmailHuntResult
from scoring.email_scorer import EmailScorer, EmailScore


class TestEmailPatterns(unittest.TestCase):
    """Test email pattern extraction and deobfuscation"""
    
    def setUp(self):
        self.pattern_lib = EmailPatternLibrary()
        self.form_analyzer = ContactFormAnalyzer()
    
    def test_standard_email_extraction(self):
        """Test extraction of standard email formats"""
        test_text = "Contact us at info@example.com or sales@company.org for more information."
        
        emails = extract_emails_comprehensive(test_text)
        
        self.assertGreaterEqual(len(emails), 2)
        email_addresses = [e['email'] for e in emails]
        self.assertIn('info@example.com', email_addresses)
        self.assertIn('sales@company.org', email_addresses)
    
    def test_obfuscated_email_extraction(self):
        """Test extraction of obfuscated emails"""
        test_cases = [
            ("Contact support [at] company [dot] com", "support@company.com"),
            ("Email admin (at) business (dot) net", "admin@business.net"),
            ("Reach ceo AT startup DOT io", "ceo@startup.io"),
            ("Write to info at company dot org", "info@company.org"),
            ("Contact sales_at_business_dot_com", "sales@business.com"),
            ("Email admin-at-company-dot-net", "admin@company.net"),
        ]
        
        for obfuscated_text, expected_email in test_cases:
            with self.subTest(text=obfuscated_text):
                emails = extract_emails_comprehensive(obfuscated_text)
                self.assertGreater(len(emails), 0, f"No emails found in: {obfuscated_text}")
                
                found_emails = [e['email'] for e in emails]
                self.assertIn(expected_email, found_emails, 
                            f"Expected {expected_email} not found in {found_emails}")
    
    def test_mailto_link_extraction(self):
        """Test extraction from mailto links"""
        html_content = '''
        <a href="mailto:contact@example.com">Contact Us</a>
        <a href="mailto:info@company.org?subject=Inquiry">Get Info</a>
        '''
        
        emails = extract_emails_comprehensive("", html_content)
        
        self.assertGreaterEqual(len(emails), 2)
        email_addresses = [e['email'] for e in emails]
        self.assertIn('contact@example.com', email_addresses)
        self.assertIn('info@company.org', email_addresses)
    
    def test_html_entity_deobfuscation(self):
        """Test HTML entity deobfuscation"""
        test_cases = [
            ("Contact info&#64;company&#46;com", "info@company.com"),
            ("Email support&#x40;business&#x2E;org", "support@business.org"),
        ]
        
        for obfuscated_text, expected_email in test_cases:
            with self.subTest(text=obfuscated_text):
                emails = extract_emails_comprehensive(obfuscated_text)
                self.assertGreater(len(emails), 0)
                
                found_emails = [e['email'] for e in emails]
                self.assertIn(expected_email, found_emails)
    
    def test_unicode_deobfuscation(self):
        """Test Unicode character deobfuscation"""
        test_text = "Contact info＠company．com for details"
        
        emails = extract_emails_comprehensive(test_text)
        
        self.assertGreater(len(emails), 0)
        self.assertIn('info@company.com', [e['email'] for e in emails])
    
    def test_email_validation(self):
        """Test email validation logic"""
        valid_emails = [
            "user@domain.com",
            "first.last@company.org",
            "info@sub.domain.net",
            "test123@example.co.uk"
        ]
        
        invalid_emails = [
            "invalid@",
            "@domain.com",
            "user@",
            "nodomain",
            "user@domain",
            ""
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(self.pattern_lib.is_valid_email(email))
        
        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(self.pattern_lib.is_valid_email(email))
    
    def test_contact_form_analysis(self):
        """Test contact form detection and analysis"""
        html_content = '''
        <form action="/contact" method="post">
            <input type="text" name="name" placeholder="Your Name">
            <input type="email" name="email" placeholder="Your Email">
            <textarea name="message" placeholder="Your Message"></textarea>
            <input type="submit" value="Send">
        </form>
        '''
        
        forms = analyze_contact_forms(html_content)
        
        self.assertGreater(len(forms), 0)
        form = forms[0]
        self.assertTrue(form['is_contact_form'])
        self.assertEqual(form['action'], '/contact')
        self.assertEqual(form['method'], 'POST')
        self.assertGreater(len(form['fields']), 2)


class TestWebsiteNavigator(unittest.TestCase):
    """Test website navigation functionality"""
    
    def setUp(self):
        self.navigator = WebsiteNavigator(timeout=5)
    
    @patch('requests.Session.get')
    def test_contact_page_discovery(self, mock_get):
        """Test contact page discovery"""
        # Mock HTML response with navigation links
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <nav>
                <a href="/home">Home</a>
                <a href="/about">About Us</a>
                <a href="/contact">Contact</a>
                <a href="/team">Our Team</a>
            </nav>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = self.navigator.discover_contact_pages("https://example.com", max_pages=3)
        
        self.assertIn('pages_visited', result)
        self.assertIn('contact_pages', result)
        self.assertIn('about_pages', result)
        self.assertIn('team_pages', result)
    
    def test_contact_pattern_scoring(self):
        """Test contact page pattern scoring"""
        test_links = [
            {'url': 'https://example.com/contact', 'text': 'Contact Us', 'title': '', 'href': '/contact', 'parent_context': 'nav', 'is_navigation': True},
            {'url': 'https://example.com/about', 'text': 'About', 'title': '', 'href': '/about', 'parent_context': 'menu', 'is_navigation': True},
            {'url': 'https://example.com/blog', 'text': 'Blog', 'title': '', 'href': '/blog', 'parent_context': '', 'is_navigation': False},
        ]
        
        for link in test_links:
            score = self.navigator._score_contact_page_candidate(link)
            if 'contact' in link['url'] or 'contact' in link['text'].lower():
                self.assertGreater(score, 50, f"Contact page should have high score: {link}")
            elif 'about' in link['url']:
                self.assertGreater(score, 30, f"About page should have medium score: {link}")
    
    def test_url_categorization(self):
        """Test URL categorization logic"""
        test_cases = [
            ("https://example.com/about-us", True, False),  # about page
            ("https://example.com/team", False, True),      # team page
            ("https://example.com/contact", False, False),  # contact page
            ("https://example.com/blog", False, False),     # other page
        ]
        
        for url, should_be_about, should_be_team in test_cases:
            with self.subTest(url=url):
                is_about = self.navigator._is_about_page(url)
                is_team = self.navigator._is_team_page(url)
                
                self.assertEqual(is_about, should_be_about)
                self.assertEqual(is_team, should_be_team)


class TestEmailScorer(unittest.TestCase):
    """Test email scoring functionality"""
    
    def setUp(self):
        self.scorer = EmailScorer()
    
    def test_email_quality_scoring(self):
        """Test email quality scoring"""
        test_cases = [
            ("ceo@company.com", 0.7),          # High quality business email
            ("john.doe@business.org", 0.7),    # Professional format
            ("info@startup.io", 0.6),          # Role-based email
            ("test123@gmail.com", 0.4),        # Personal email
            ("invalid@", 0.0),                 # Invalid format
        ]
        
        for email, min_expected_score in test_cases:
            with self.subTest(email=email):
                score = self.scorer.score_email_quality(email)
                self.assertGreaterEqual(score, min_expected_score, 
                                      f"Quality score for {email} should be >= {min_expected_score}, got {score}")
    
    def test_business_relevance_scoring(self):
        """Test business relevance scoring"""
        test_cases = [
            ("ceo@company.com", "CEO bio page", 0.8),
            ("sales@business.org", "Contact page", 0.7),
            ("john@gmail.com", "Personal contact", 0.3),
            ("noreply@system.com", "Automated email", 0.1),
        ]
        
        for email, context, min_expected_score in test_cases:
            with self.subTest(email=email):
                score = self.scorer.score_business_relevance(email, context)
                self.assertGreaterEqual(score, min_expected_score,
                                      f"Business score for {email} should be >= {min_expected_score}, got {score}")
    
    def test_personal_likelihood_scoring(self):
        """Test personal likelihood scoring"""
        personal_emails = [
            "john@gmail.com",
            "personal.email@yahoo.com",
            "myhome123@hotmail.com"
        ]
        
        business_emails = [
            "ceo@company.com",
            "info@business.org",
            "contact@startup.io"
        ]
        
        for email in personal_emails:
            with self.subTest(email=email):
                score = self.scorer.score_personal_likelihood(email)
                self.assertGreater(score, 0.5, f"Personal email {email} should have high personal score")
        
        for email in business_emails:
            with self.subTest(email=email):
                score = self.scorer.score_personal_likelihood(email)
                self.assertLess(score, 0.5, f"Business email {email} should have low personal score")
    
    def test_comprehensive_scoring(self):
        """Test comprehensive email scoring"""
        email = "ceo@company.com"
        context = "Found on CEO biography page"
        
        score = self.scorer.score_comprehensive(email, context)
        
        self.assertIsInstance(score, EmailScore)
        self.assertEqual(score.email, email)
        self.assertGreater(score.quality_score, 0.5)
        self.assertGreater(score.business_score, 0.5)
        self.assertIn(score.category, ['high_value_business', 'business', 'personal', 'generic', 'unknown'])
        self.assertIsInstance(score.is_actionable, bool)
    
    def test_email_categorization(self):
        """Test email categorization logic"""
        test_cases = [
            ("ceo@company.com", "high_value_business"),
            ("info@business.org", "business"),
            ("john@gmail.com", "personal"),
            ("noreply@system.com", "generic"),
        ]
        
        for email, expected_category in test_cases:
            with self.subTest(email=email):
                score = self.scorer.score_comprehensive(email)
                self.assertEqual(score.category, expected_category,
                               f"Email {email} should be categorized as {expected_category}, got {score.category}")
    
    def test_actionable_email_filtering(self):
        """Test actionable email filtering"""
        emails = [
            "ceo@company.com",       # Should be actionable
            "info@business.org",     # Should be actionable
            "john@gmail.com",        # Might not be actionable (personal)
            "noreply@system.com",    # Should not be actionable
            "invalid@",              # Should not be actionable
        ]
        
        scores = self.scorer.score_email_list(emails)
        actionable = self.scorer.filter_actionable_emails(scores)
        
        actionable_emails = [score.email for score in actionable]
        
        # High-value business emails should be actionable
        self.assertIn("ceo@company.com", actionable_emails)
        self.assertIn("info@business.org", actionable_emails)
        
        # Generic/invalid emails should not be actionable
        self.assertNotIn("noreply@system.com", actionable_emails)
        self.assertNotIn("invalid@", actionable_emails)


class TestEmailHunter(unittest.TestCase):
    """Test complete email hunting functionality"""
    
    def setUp(self):
        self.hunter = EmailHunter(timeout=5, max_pages=2, use_javascript=False)
    
    @patch('extractors.email_hunter.WebsiteNavigator')
    @patch('requests.Session.get')
    def test_email_hunting_workflow(self, mock_get, mock_navigator):
        """Test complete email hunting workflow"""
        # Mock navigation results
        mock_nav_instance = Mock()
        mock_nav_instance.discover_contact_pages.return_value = {
            'pages_visited': ['https://example.com', 'https://example.com/contact'],
            'contact_pages': ['https://example.com/contact'],
            'about_pages': [],
            'team_pages': []
        }
        mock_navigator.return_value = mock_nav_instance
        
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <title>Example Company</title>
            <h1>Welcome to Example Company</h1>
            <p>Contact us at info@example.com or call (555) 123-4567</p>
            <a href="mailto:sales@example.com">Sales Team</a>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = self.hunter.hunt_emails("https://example.com")
        
        self.assertIsInstance(result, EmailHuntResult)
        self.assertEqual(result.url, "https://example.com")
        self.assertGreater(len(result.emails), 0)
        self.assertGreater(result.overall_score, 0)
    
    def test_business_name_extraction(self):
        """Test business name extraction from HTML"""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <head><title>Example Company - Home</title></head>
            <body>
                <h1>Welcome to Example Company</h1>
                <img src="logo.png" alt="Example Company Logo">
            </body>
        </html>
        '''
        
        soup = BeautifulSoup(html_content, 'html.parser')
        business_name = self.hunter._extract_business_name(soup, "https://example.com")
        
        self.assertIn("Example Company", business_name)
    
    def test_phone_number_extraction(self):
        """Test phone number extraction"""
        test_text = """
        Contact our office at (555) 123-4567 or call the sales team at 555.987.6543.
        International number: +1-555-111-2222
        Fax: (555) 123-9999
        """
        
        phones = self.hunter._extract_phone_numbers(test_text)
        
        self.assertGreater(len(phones), 0)
        phone_numbers = [p['phone'] for p in phones]
        self.assertTrue(any('555' in phone for phone in phone_numbers))
    
    def test_social_profile_extraction(self):
        """Test social media profile extraction"""
        from bs4 import BeautifulSoup
        
        html_content = '''
        <html>
            <body>
                <a href="https://www.facebook.com/examplecompany">Facebook</a>
                <a href="https://twitter.com/example">Twitter</a>
                <a href="https://www.linkedin.com/company/example">LinkedIn</a>
            </body>
        </html>
        '''
        
        soup = BeautifulSoup(html_content, 'html.parser')
        social_profiles = self.hunter._extract_social_profiles(soup)
        
        self.assertGreater(len(social_profiles), 0)
        self.assertTrue(any('facebook.com' in profile for profile in social_profiles))
        self.assertTrue(any('twitter.com' in profile for profile in social_profiles))
        self.assertTrue(any('linkedin.com' in profile for profile in social_profiles))
    
    def test_email_deduplication(self):
        """Test email deduplication and scoring"""
        emails = [
            {'email': 'info@example.com', 'source': 'text', 'context': 'Contact page'},
            {'email': 'info@example.com', 'source': 'mailto', 'context': 'Link'},
            {'email': 'sales@example.com', 'source': 'text', 'context': 'Sales page'},
        ]
        
        deduplicated = self.hunter._deduplicate_and_score_emails(emails)
        
        # Should have 2 unique emails
        self.assertEqual(len(deduplicated), 2)
        
        # Check that emails are properly scored
        for email_data in deduplicated:
            self.assertIn('quality_score', email_data)
            self.assertIn('business_score', email_data)
            self.assertIn('combined_score', email_data)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete email extraction workflow"""
    
    def setUp(self):
        self.test_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Company - Contact Us</title>
        </head>
        <body>
            <h1>Contact Test Company</h1>
            <nav>
                <a href="/home">Home</a>
                <a href="/about">About Us</a>
                <a href="/contact">Contact</a>
                <a href="/team">Team</a>
            </nav>
            
            <div class="contact-info">
                <p>Email us at <a href="mailto:info@testcompany.com">info@testcompany.com</a></p>
                <p>Sales inquiries: sales [at] testcompany [dot] com</p>
                <p>CEO: <a href="mailto:ceo@testcompany.com">John Doe</a></p>
                <p>Phone: (555) 123-4567</p>
            </div>
            
            <form action="/contact" method="post">
                <input type="text" name="name" placeholder="Name">
                <input type="email" name="email" placeholder="Email">
                <textarea name="message" placeholder="Message"></textarea>
                <button type="submit">Send</button>
            </form>
            
            <div class="social">
                <a href="https://facebook.com/testcompany">Facebook</a>
                <a href="https://twitter.com/testcompany">Twitter</a>
            </div>
        </body>
        </html>
        '''
    
    def test_complete_extraction_workflow(self):
        """Test complete extraction workflow with mock HTML"""
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(self.test_html)
            temp_file = f.name
        
        try:
            file_url = f"file://{temp_file}"
            
            # Test pattern extraction
            emails = extract_emails_comprehensive(self.test_html, self.test_html)
            self.assertGreater(len(emails), 0)
            
            # Test form analysis
            forms = analyze_contact_forms(self.test_html)
            self.assertGreater(len(forms), 0)
            
            # Test email scoring
            scorer = EmailScorer()
            for email_data in emails:
                score = scorer.score_comprehensive(email_data['email'])
                self.assertIsInstance(score, EmailScore)
            
            print(f"Integration test completed successfully:")
            print(f"  Emails found: {len(emails)}")
            print(f"  Contact forms: {len(forms)}")
            print(f"  Email addresses: {[e['email'] for e in emails]}")
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_performance_benchmarks(self):
        """Test performance of extraction components"""
        import time
        
        # Large text for performance testing
        large_text = self.test_html * 100
        
        # Benchmark email extraction
        start_time = time.time()
        emails = extract_emails_comprehensive(large_text)
        extraction_time = time.time() - start_time
        
        self.assertLess(extraction_time, 5.0, "Email extraction should complete within 5 seconds")
        
        # Benchmark email scoring
        scorer = EmailScorer()
        start_time = time.time()
        
        test_emails = ['info@company.com'] * 100
        scores = scorer.score_email_list(test_emails)
        scoring_time = time.time() - start_time
        
        self.assertLess(scoring_time, 2.0, "Email scoring should complete within 2 seconds")
        
        print(f"Performance benchmarks:")
        print(f"  Email extraction: {extraction_time:.3f}s")
        print(f"  Email scoring: {scoring_time:.3f}s")


def run_test_suite():
    """Run the complete test suite"""
    print("Running Email Extraction Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEmailPatterns,
        TestWebsiteNavigator,
        TestEmailScorer,
        TestEmailHunter,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTest Suite Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors))/result.testsRun*100:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_test_suite()
    exit(0 if success else 1)