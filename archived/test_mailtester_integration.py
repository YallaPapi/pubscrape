"""
Test script for Mailtester Ninja API integration.

This script tests the email validation system with and without the Mailtester Ninja API
to ensure proper integration and fallback behavior.
"""

import os
import sys
import logging
from typing import List

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test emails - mix of valid, invalid, disposable, and business emails
TEST_EMAILS = [
    # Valid business emails (should be high quality)
    "contact@example.com",
    "info@microsoft.com",  
    "support@google.com",
    
    # Personal emails (should be medium/low quality)
    "test.user@gmail.com",
    "someone@yahoo.com",
    
    # Invalid emails
    "invalid-email",
    "missing@",
    "@missing.com",
    "test@nonexistentdomain12345.com",
    
    # Potentially disposable/temp emails
    "temp@10minutemail.com",
    "test@mailinator.com",
    
    # Role-based emails
    "admin@company.com",
    "noreply@service.com",
    "no-reply@notifications.com",
]


def test_mailtester_client():
    """Test the Mailtester Ninja client directly"""
    print("=" * 60)
    print("Testing Mailtester Ninja Client")
    print("=" * 60)
    
    try:
        from agents.tools.mailtester_ninja_client import (
            create_mailtester_client, ValidationLevel
        )
        
        # Check if API key is configured
        api_key = os.getenv('MAILTESTER_NINJA_API_KEY')
        if not api_key or api_key == 'YOUR_MAILTESTER_NINJA_API_KEY_HERE':
            print("[X] MAILTESTER_NINJA_API_KEY not configured")
            print("   Please set a valid API key in the .env file to test API functionality")
            return False
        
        print(f"[OK] API key configured: {api_key[:10]}...")
        
        # Test with a subset of emails
        test_emails = TEST_EMAILS[:5]  # Use first 5 emails for testing
        
        with create_mailtester_client() as client:
            print(f"\n[EMAIL] Testing {len(test_emails)} emails...")
            
            for email in test_emails:
                print(f"\nValidating: {email}")
                try:
                    result = client.validate_email(email, ValidationLevel.BASIC)
                    
                    print(f"   Status: {result.status.value}")
                    print(f"   Score: {result.score:.2f}")
                    print(f"   Quality Score: {result.get_quality_score():.2f}")
                    print(f"   Is Deliverable: {result.is_deliverable()}")
                    print(f"   Is Disposable: {result.is_disposable}")
                    print(f"   Is Role Account: {result.is_role_account}")
                    
                    if result.smtp_check:
                        print(f"   SMTP: can_connect={result.smtp_check.get('can_connect')}, "
                              f"mailbox_exists={result.smtp_check.get('mailbox_exists')}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            # Get client stats
            stats = client.get_stats()
            print(f"\n📊 Client Statistics:")
            print(f"   Total requests: {stats['total_requests']}")
            print(f"   Cache hits: {stats['cache_hits']}")
            print(f"   Error rate: {stats['error_rate']:.1%}")
            print(f"   Avg response time: {stats['average_response_time_ms']:.1f}ms")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_email_validation_tool():
    """Test the updated Email Validation Tool"""
    print("=" * 60)
    print("Testing Email Validation Tool")
    print("=" * 60)
    
    try:
        from agents.tools.email_validation_tool import EmailValidationTool
        
        # Test with Mailtester API (if available)
        print("🔧 Testing with Mailtester API enabled...")
        tool = EmailValidationTool(
            emails=TEST_EMAILS[:8],  # Use subset for testing
            use_mailtester_api=True,
            validation_level="basic"
        )
        
        result = tool.run()
        
        print(f"\n📊 Results Summary:")
        summary = result.get('summary', {})
        print(f"   Total emails: {summary.get('total_emails', 0)}")
        print(f"   Processed: {summary.get('processed', 0)}")
        print(f"   Valid emails: {summary.get('valid_emails', 0)}")
        print(f"   Acceptance rate: {summary.get('acceptance_rate', 0):.1%}")
        print(f"   Validation method: {summary.get('validation_method', 'Unknown')}")
        
        if 'mailtester_stats' in result:
            mt_stats = result['mailtester_stats']
            print(f"\n🎯 Mailtester Stats:")
            print(f"   Valid: {mt_stats.get('valid_count', 0)}")
            print(f"   Risky: {mt_stats.get('risky_count', 0)}")
            print(f"   Catch-all: {mt_stats.get('catch_all_count', 0)}")
            print(f"   Disposable: {mt_stats.get('disposable_count', 0)}")
            print(f"   Role accounts: {mt_stats.get('role_account_count', 0)}")
        
        # Show quality distribution
        quality_dist = result.get('quality_distribution', {})
        print(f"\n🏆 Quality Distribution:")
        for level, count in quality_dist.items():
            print(f"   {level.capitalize()}: {count}")
        
        # Show some example results
        valid_emails = result.get('valid_emails', [])
        if valid_emails:
            print(f"\n✅ Example valid emails:")
            for email_result in valid_emails[:3]:
                email = email_result.get('email', '')
                score = email_result.get('confidence_score', 0)
                quality = email_result.get('quality', '')
                print(f"   {email} - Quality: {quality}, Score: {score:.2f}")
        
        invalid_emails = result.get('invalid_emails', [])
        if invalid_emails:
            print(f"\n❌ Example invalid emails:")
            for email_result in invalid_emails[:3]:
                email = email_result.get('email', '')
                reason = email_result.get('reason', '')
                print(f"   {email} - Reason: {reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_validation():
    """Test fallback validation (without Mailtester API)"""
    print("=" * 60)
    print("Testing Fallback Validation")
    print("=" * 60)
    
    try:
        from agents.tools.email_validation_tool import EmailValidationTool
        
        # Test with API disabled to trigger fallback
        print("🔧 Testing with Mailtester API disabled (fallback mode)...")
        tool = EmailValidationTool(
            emails=TEST_EMAILS[:5],
            use_mailtester_api=False,  # Force fallback
            enable_dns_check=True,
            enable_deliverability_check=True
        )
        
        result = tool.run()
        
        print(f"\n📊 Fallback Results Summary:")
        summary = result.get('summary', {})
        print(f"   Total emails: {summary.get('total_emails', 0)}")
        print(f"   Processed: {summary.get('processed', 0)}")
        print(f"   Valid emails: {summary.get('valid_emails', 0)}")
        print(f"   Acceptance rate: {summary.get('acceptance_rate', 0):.1%}")
        print(f"   Validation method: {summary.get('validation_method', 'Unknown')}")
        
        # Show validation stats
        val_stats = result.get('validation_stats', {})
        print(f"\n📈 Validation Stats:")
        for stat, count in val_stats.items():
            if count > 0:
                print(f"   {stat}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulk_validation():
    """Test the new Mailtester bulk validation tool"""
    print("=" * 60)
    print("Testing Bulk Validation Tool")
    print("=" * 60)
    
    try:
        from agents.tools.mailtester_email_validation_tool import MailtesterBulkValidationTool
        
        # Prepare test data with contact information
        email_data = []
        for i, email in enumerate(TEST_EMAILS):
            email_data.append({
                'email': email,
                'name': f'Contact {i+1}',
                'title': 'Test Contact',
                'company': f'Test Company {i+1}',
                'source_url': 'https://test.com',
                'discovery_method': 'test'
            })
        
        print(f"🔧 Testing bulk validation with {len(email_data)} contacts...")
        
        tool = MailtesterBulkValidationTool(
            email_data=email_data,
            validation_level="basic",
            batch_size=5,
            quality_threshold=0.5
        )
        
        result = tool.run()
        
        if 'error' in result:
            print(f"❌ Bulk validation error: {result['error']}")
            return False
        
        print(f"\n📊 Bulk Results Summary:")
        summary = result.get('summary', {})
        print(f"   Total email records: {summary.get('total_email_records', 0)}")
        print(f"   Valid emails found: {summary.get('valid_emails_found', 0)}")
        print(f"   Total processed: {summary.get('total_processed', 0)}")
        print(f"   Total accepted: {summary.get('total_accepted', 0)}")
        print(f"   Acceptance rate: {summary.get('overall_acceptance_rate', 0):.1%}")
        print(f"   Processing time: {summary.get('total_processing_time_seconds', 0):.1f}s")
        
        # Show accepted contacts
        accepted = result.get('accepted_contacts', [])
        if accepted:
            print(f"\n✅ Accepted contacts ({len(accepted)}):")
            for contact in accepted[:3]:
                email = contact.get('email', '')
                name = contact.get('contact_name', '')
                score = contact.get('score', 0)
                print(f"   {name} <{email}> - Score: {score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("Testing Mailtester Ninja Integration")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    tests = [
        ("Mailtester Client", test_mailtester_client),
        ("Email Validation Tool", test_email_validation_tool),
        ("Fallback Validation", test_fallback_validation),
        ("Bulk Validation Tool", test_bulk_validation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running {test_name} test...")
        try:
            success = test_func()
            results[test_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n❌ {test_name}: FAILED with exception: {e}")
            results[test_name] = False
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🏁 Test Summary")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Mailtester Ninja integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        
        # Provide helpful guidance
        if not results.get("Mailtester Client", False):
            print("\n💡 Tip: Make sure to set MAILTESTER_NINJA_API_KEY in your .env file")
            print("   You can get a free API key from Mailtester Ninja's website")


if __name__ == "__main__":
    main()