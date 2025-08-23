#!/usr/bin/env python3
"""
Email Hunting System Demo
Comprehensive demonstration of the complete email extraction system
"""

import sys
import os
import time
import json
import csv
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.dirname(__file__))

from extractors.email_hunter import EmailHunter, EmailHuntResult
from extractors.email_patterns import extract_emails_comprehensive, test_email_patterns
from extractors.website_navigator import WebsiteNavigator, test_website_navigator
from extractors.botasaurus_integration import BotasaurusEmailExtractor, BOTASAURUS_AVAILABLE
from scoring.email_scorer import EmailScorer, test_email_scorer


class EmailHuntingDemo:
    """
    Complete demonstration of email hunting capabilities
    """
    
    def __init__(self):
        # Initialize components
        self.hunter = EmailHunter(
            timeout=10,
            max_pages=3,
            use_javascript=BOTASAURUS_AVAILABLE,
            enable_contact_forms=True
        )
        
        self.navigator = WebsiteNavigator(timeout=10)
        self.scorer = EmailScorer()
        
        if BOTASAURUS_AVAILABLE:
            self.js_extractor = BotasaurusEmailExtractor(headless=True)
        else:
            self.js_extractor = None
        
        # Demo data
        self.demo_urls = [
            "https://example.com",
            "https://httpbin.org/html",
            "https://www.python.org/community/",
            "https://docs.python.org/",
        ]
        
        self.demo_texts = [
            "Contact us at info@example.com or sales@company.org",
            "Email support [at] business [dot] com for help",
            "Reach our CEO at john.doe@startup.io or call (555) 123-4567",
            "Visit our team page or email team AT company DOT net",
            '<a href="mailto:contact@business.com">Contact Us</a>',
        ]
    
    def run_complete_demo(self):
        """Run complete demonstration of all features"""
        print("🚀 EMAIL HUNTING SYSTEM DEMO")
        print("=" * 60)
        print()
        
        # 1. Test pattern extraction
        print("1️⃣ EMAIL PATTERN EXTRACTION TEST")
        print("-" * 40)
        self.demo_pattern_extraction()
        print()
        
        # 2. Test email scoring
        print("2️⃣ EMAIL SCORING SYSTEM TEST")
        print("-" * 40)
        self.demo_email_scoring()
        print()
        
        # 3. Test website navigation
        print("3️⃣ WEBSITE NAVIGATION TEST")
        print("-" * 40)
        self.demo_website_navigation()
        print()
        
        # 4. Test complete email hunting
        print("4️⃣ COMPLETE EMAIL HUNTING TEST")
        print("-" * 40)
        self.demo_complete_hunting()
        print()
        
        # 5. Test JavaScript extraction (if available)
        if self.js_extractor:
            print("5️⃣ JAVASCRIPT EXTRACTION TEST")
            print("-" * 40)
            self.demo_javascript_extraction()
            print()
        
        # 6. Performance benchmarks
        print("6️⃣ PERFORMANCE BENCHMARKS")
        print("-" * 40)
        self.demo_performance_benchmarks()
        print()
        
        # 7. Export results
        print("7️⃣ EXPORTING DEMO RESULTS")
        print("-" * 40)
        self.demo_export_results()
        
        print("\n✅ DEMO COMPLETED SUCCESSFULLY!")
    
    def demo_pattern_extraction(self):
        """Demonstrate email pattern extraction capabilities"""
        print("Testing email pattern extraction with various obfuscation methods...")
        
        total_extracted = 0
        
        for i, text in enumerate(self.demo_texts, 1):
            print(f"\nSample {i}: {text}")
            
            emails = extract_emails_comprehensive(text, text)
            
            if emails:
                for email in emails:
                    print(f"  ✅ Found: {email['email']} "
                          f"(pattern: {email.get('pattern', 'unknown')}, "
                          f"priority: {email.get('priority', 0)})")
                    total_extracted += 1
            else:
                print("  ❌ No emails found")
        
        print(f"\n📊 Summary: {total_extracted} emails extracted from {len(self.demo_texts)} samples")
        
        # Test the pattern library directly
        print("\nRunning comprehensive pattern tests...")
        pattern_test_result = test_email_patterns()
        print(f"Pattern library test: {'✅ PASSED' if pattern_test_result else '❌ FAILED'}")
    
    def demo_email_scoring(self):
        """Demonstrate email scoring capabilities"""
        print("Testing email scoring system...")
        
        test_emails = [
            ("ceo@company.com", "CEO biography page"),
            ("sales@business.org", "Contact us page"),
            ("info@restaurant.net", "Restaurant contact info"),
            ("john.doe@startup.io", "Team member profile"),
            ("support@helpdesk.com", "Support contact"),
            ("personal123@gmail.com", "Personal email"),
            ("noreply@system.com", "Automated system"),
        ]
        
        scores = []
        
        for email, context in test_emails:
            score = self.scorer.score_comprehensive(email, context)
            scores.append(score)
            
            print(f"\n📧 {email}")
            print(f"   Quality: {score.quality_score:.2f}")
            print(f"   Business: {score.business_score:.2f}")
            print(f"   Personal: {score.personal_score:.2f}")
            print(f"   Category: {score.category}")
            print(f"   Actionable: {'✅' if score.is_actionable else '❌'}")
        
        # Filter actionable emails
        actionable = self.scorer.filter_actionable_emails(scores)
        
        print(f"\n📊 Summary:")
        print(f"   Total emails scored: {len(scores)}")
        print(f"   Actionable emails: {len(actionable)}")
        print(f"   Actionability rate: {len(actionable)/len(scores)*100:.1f}%")
        
        # Test scorer directly
        print("\nRunning comprehensive scorer tests...")
        scorer_test_result = test_email_scorer()
        print(f"Email scorer test: {'✅ PASSED' if scorer_test_result else '❌ FAILED'}")
    
    def demo_website_navigation(self):
        """Demonstrate website navigation capabilities"""
        print("Testing intelligent website navigation...")
        
        # Test with a subset of URLs to avoid long delays
        test_urls = self.demo_urls[:2]
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n🌐 Testing URL {i}: {url}")
            
            try:
                result = self.navigator.discover_contact_pages(url, max_pages=2)
                
                print(f"   Pages visited: {len(result['pages_visited'])}")
                print(f"   Contact pages: {len(result['contact_pages'])}")
                print(f"   About pages: {len(result['about_pages'])}")
                print(f"   Team pages: {len(result['team_pages'])}")
                print(f"   Navigation time: {result['navigation_time']:.2f}s")
                
                # Show discovered pages
                if result['contact_pages']:
                    print("   🎯 Contact pages found:")
                    for page in result['contact_pages'][:3]:
                        print(f"      - {page}")
                
                if result['errors']:
                    print(f"   ⚠️  Errors: {len(result['errors'])}")
                
            except Exception as e:
                print(f"   ❌ Navigation failed: {str(e)[:100]}")
        
        # Test navigator directly
        print("\nRunning comprehensive navigation tests...")
        nav_test_result = test_website_navigator()
        print(f"Website navigator test: {'✅ PASSED' if nav_test_result else '❌ FAILED'}")
    
    def demo_complete_hunting(self):
        """Demonstrate complete email hunting workflow"""
        print("Testing complete email hunting workflow...")
        
        results = []
        
        for i, url in enumerate(self.demo_urls[:2], 1):  # Limit to 2 for demo
            print(f"\n🎯 Hunting emails from URL {i}: {url}")
            
            start_time = time.time()
            
            try:
                result = self.hunter.hunt_emails(url)
                results.append(result)
                
                hunting_time = time.time() - start_time
                
                print(f"   ✅ Hunt completed in {hunting_time:.2f}s")
                print(f"   Business: {result.business_name}")
                print(f"   Emails: {len(result.emails)}")
                print(f"   Phones: {len(result.phones)}")
                print(f"   Forms: {len(result.contact_forms)}")
                print(f"   Social: {len(result.social_profiles)}")
                print(f"   Pages processed: {result.pages_processed}")
                print(f"   Overall score: {result.overall_score:.2f}")
                print(f"   Actionable: {'✅' if result.is_actionable else '❌'}")
                
                # Show top emails
                if result.emails:
                    print("   🏆 Top emails:")
                    for email in result.emails[:3]:
                        score = email.get('combined_score', 0)
                        print(f"      - {email['email']} (score: {score:.2f})")
                
                if result.extraction_errors:
                    print(f"   ⚠️  Errors: {len(result.extraction_errors)}")
                
            except Exception as e:
                print(f"   ❌ Hunting failed: {str(e)[:100]}")
        
        # Summary
        if results:
            total_emails = sum(len(r.emails) for r in results)
            total_actionable = sum(1 for r in results if r.is_actionable)
            avg_score = sum(r.overall_score for r in results) / len(results)
            
            print(f"\n📊 Hunting Summary:")
            print(f"   URLs processed: {len(results)}")
            print(f"   Total emails found: {total_emails}")
            print(f"   Actionable results: {total_actionable}")
            print(f"   Average score: {avg_score:.2f}")
    
    def demo_javascript_extraction(self):
        """Demonstrate JavaScript-based extraction"""
        print("Testing JavaScript extraction capabilities...")
        
        if not self.js_extractor:
            print("❌ Botasaurus not available - JavaScript extraction disabled")
            return
        
        test_url = "https://example.com"
        
        print(f"🔍 Testing JavaScript extraction on: {test_url}")
        
        try:
            # Check if JavaScript needed
            needs_js = self.js_extractor.is_javascript_page(test_url)
            print(f"   Needs JavaScript: {needs_js}")
            
            # Extract with JavaScript
            result = self.js_extractor.extract_from_js_page(test_url)
            
            print(f"   ✅ Extraction completed in {result.extraction_time:.2f}s")
            print(f"   Success: {result.success}")
            print(f"   Business: {result.business_name}")
            print(f"   Emails: {len(result.emails)}")
            print(f"   Phones: {len(result.phones)}")
            print(f"   Forms: {len(result.forms)}")
            print(f"   JS detected: {result.javascript_detected}")
            
            if result.error_message:
                print(f"   ⚠️  Error: {result.error_message}")
            
            # Show extracted emails
            if result.emails:
                print("   📧 Extracted emails:")
                for email in result.emails[:3]:
                    print(f"      - {email['email']}")
            
        except Exception as e:
            print(f"   ❌ JavaScript extraction failed: {str(e)[:100]}")
    
    def demo_performance_benchmarks(self):
        """Demonstrate performance benchmarks"""
        print("Running performance benchmarks...")
        
        # Benchmark 1: Pattern extraction speed
        large_text = " ".join(self.demo_texts) * 50
        
        start_time = time.time()
        emails = extract_emails_comprehensive(large_text)
        pattern_time = time.time() - start_time
        
        print(f"📊 Pattern extraction benchmark:")
        print(f"   Text size: {len(large_text):,} characters")
        print(f"   Emails found: {len(emails)}")
        print(f"   Processing time: {pattern_time:.3f}s")
        print(f"   Speed: {len(large_text)/pattern_time/1000:.1f}k chars/sec")
        
        # Benchmark 2: Email scoring speed
        test_emails = ["info@company.com"] * 100
        
        start_time = time.time()
        scores = self.scorer.score_email_list(test_emails)
        scoring_time = time.time() - start_time
        
        print(f"\n🏃 Email scoring benchmark:")
        print(f"   Emails scored: {len(scores)}")
        print(f"   Processing time: {scoring_time:.3f}s")
        print(f"   Speed: {len(scores)/scoring_time:.1f} emails/sec")
        
        # Performance recommendations
        print(f"\n💡 Performance Analysis:")
        if pattern_time < 1.0:
            print("   ✅ Pattern extraction: Excellent performance")
        elif pattern_time < 3.0:
            print("   ⚠️  Pattern extraction: Good performance")
        else:
            print("   ❌ Pattern extraction: Consider optimization")
        
        if scoring_time < 0.5:
            print("   ✅ Email scoring: Excellent performance")
        elif scoring_time < 2.0:
            print("   ⚠️  Email scoring: Good performance")
        else:
            print("   ❌ Email scoring: Consider optimization")
    
    def demo_export_results(self):
        """Demonstrate result export capabilities"""
        print("Demonstrating result export...")
        
        # Generate sample results
        sample_results = []
        
        for i, url in enumerate(self.demo_urls[:2], 1):
            try:
                result = self.hunter.hunt_emails(url)
                sample_results.append(result)
            except:
                # Create mock result for demo
                result = EmailHuntResult(url=url)
                result.business_name = f"Demo Business {i}"
                result.emails = [
                    {'email': f'info@demo{i}.com', 'combined_score': 0.8, 'source': 'demo'},
                    {'email': f'contact@demo{i}.com', 'combined_score': 0.7, 'source': 'demo'}
                ]
                result.overall_score = 0.75
                result.is_actionable = True
                sample_results.append(result)
        
        # Export to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'email_hunting_demo_{timestamp}.csv'
        
        headers = [
            'url', 'business_name', 'emails_found', 'top_email', 'overall_score',
            'is_actionable', 'pages_processed', 'extraction_time'
        ]
        
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for result in sample_results:
                    top_email = result.emails[0]['email'] if result.emails else ''
                    
                    writer.writerow({
                        'url': result.url,
                        'business_name': result.business_name,
                        'emails_found': len(result.emails),
                        'top_email': top_email,
                        'overall_score': result.overall_score,
                        'is_actionable': result.is_actionable,
                        'pages_processed': result.pages_processed,
                        'extraction_time': result.extraction_time
                    })
            
            print(f"   ✅ CSV exported: {csv_filename}")
            
        except Exception as e:
            print(f"   ❌ CSV export failed: {str(e)}")
        
        # Export detailed JSON
        json_filename = f'email_hunting_detailed_{timestamp}.json'
        
        try:
            detailed_data = {
                'export_timestamp': timestamp,
                'demo_info': {
                    'total_urls_processed': len(sample_results),
                    'total_emails_found': sum(len(r.emails) for r in sample_results),
                    'actionable_results': sum(1 for r in sample_results if r.is_actionable)
                },
                'results': [result.to_dict() for result in sample_results]
            }
            
            with open(json_filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(detailed_data, jsonfile, indent=2, default=str)
            
            print(f"   ✅ JSON exported: {json_filename}")
            
        except Exception as e:
            print(f"   ❌ JSON export failed: {str(e)}")
        
        print(f"\n📁 Export Summary:")
        print(f"   Results processed: {len(sample_results)}")
        print(f"   CSV file: {csv_filename}")
        print(f"   JSON file: {json_filename}")
    
    def run_quick_test(self):
        """Run a quick test of core functionality"""
        print("🚀 QUICK EMAIL HUNTING TEST")
        print("=" * 40)
        
        # Test pattern extraction
        test_text = "Contact us at info@example.com or sales [at] company [dot] com"
        emails = extract_emails_comprehensive(test_text)
        print(f"✅ Pattern extraction: {len(emails)} emails found")
        
        # Test email scoring
        if emails:
            score = self.scorer.score_comprehensive(emails[0]['email'])
            print(f"✅ Email scoring: {score.email} scored {score.business_score:.2f}")
        
        # Test basic hunting (without network calls)
        print("✅ Email hunter initialized successfully")
        
        print("\n🎉 Quick test completed - system is operational!")


def main():
    """Main demo entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Email Hunting System Demo')
    parser.add_argument('--quick', action='store_true', help='Run quick test only')
    parser.add_argument('--patterns', action='store_true', help='Test patterns only')
    parser.add_argument('--scoring', action='store_true', help='Test scoring only')
    parser.add_argument('--navigation', action='store_true', help='Test navigation only')
    parser.add_argument('--hunting', action='store_true', help='Test hunting only')
    parser.add_argument('--javascript', action='store_true', help='Test JavaScript extraction only')
    
    args = parser.parse_args()
    
    demo = EmailHuntingDemo()
    
    if args.quick:
        demo.run_quick_test()
    elif args.patterns:
        demo.demo_pattern_extraction()
    elif args.scoring:
        demo.demo_email_scoring()
    elif args.navigation:
        demo.demo_website_navigation()
    elif args.hunting:
        demo.demo_complete_hunting()
    elif args.javascript:
        demo.demo_javascript_extraction()
    else:
        demo.run_complete_demo()


if __name__ == "__main__":
    main()