"""
Simple test script for Mailtester Ninja API integration.
Tests basic functionality without unicode characters.
"""

import os
import sys
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_email_validation_tool():
    """Test the updated Email Validation Tool"""
    print("Testing Email Validation Tool")
    print("=" * 50)
    
    try:
        from agents.tools.email_validation_tool import EmailValidationTool
        
        # Test emails
        test_emails = [
            "test@example.com",
            "invalid-email",
            "contact@microsoft.com",
            "user@gmail.com"
        ]
        
        print("Testing with fallback validation (no API key)...")
        tool = EmailValidationTool(
            emails=test_emails,
            use_mailtester_api=False,  # Force fallback mode
            enable_dns_check=False,    # Disable DNS for faster testing
        )
        
        result = tool.run()
        
        print("\nResults Summary:")
        summary = result.get('summary', {})
        print(f"  Total emails: {summary.get('total_emails', 0)}")
        print(f"  Valid emails: {summary.get('valid_emails', 0)}")
        print(f"  Acceptance rate: {summary.get('acceptance_rate', 0):.1%}")
        print(f"  Method: {summary.get('validation_method', 'Unknown')}")
        
        # Show some results
        valid_emails = result.get('valid_emails', [])
        print(f"\nValid emails: {len(valid_emails)}")
        for email_result in valid_emails[:2]:
            email = email_result.get('email', '')
            quality = email_result.get('quality', '')
            print(f"  {email} - Quality: {quality}")
        
        invalid_emails = result.get('invalid_emails', [])
        print(f"\nInvalid emails: {len(invalid_emails)}")
        for email_result in invalid_emails[:2]:
            email = email_result.get('email', '')
            reason = email_result.get('reason', '')
            print(f"  {email} - Reason: {reason}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mailtester_client():
    """Test Mailtester client (will show API key warning)"""
    print("\nTesting Mailtester Client")
    print("=" * 50)
    
    try:
        from agents.tools.mailtester_ninja_client import create_mailtester_client
        
        api_key = os.getenv('MAILTESTER_NINJA_API_KEY')
        if not api_key or api_key == 'YOUR_MAILTESTER_NINJA_API_KEY_HERE':
            print("MAILTESTER_NINJA_API_KEY not configured")
            print("This is expected for testing - showing proper error handling")
            
            # Try to create client anyway to test error handling
            try:
                client = create_mailtester_client()
                print("ERROR: Client creation should have failed!")
                return False
            except ValueError as e:
                print(f"Good: Got expected error - {e}")
                return True
        else:
            print(f"API key found: {api_key[:10]}...")
            # Could test actual API calls here if key is valid
            return True
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False


def main():
    """Run tests"""
    print("Mailtester Ninja Integration Tests")
    print("=" * 50)
    
    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Environment loaded")
    except ImportError:
        print("dotenv not available, using system environment")
    
    # Run tests
    tests = [
        ("Email Validation Tool", test_email_validation_tool),
        ("Mailtester Client", test_mailtester_client),
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            if test_func():
                print(f"{test_name}: PASSED")
                passed += 1
            else:
                print(f"{test_name}: FAILED")
        except Exception as e:
            print(f"{test_name}: ERROR - {e}")
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("SUCCESS: All tests passed!")
        print("\nTo test with real API calls:")
        print("1. Get a free API key from Mailtester Ninja")
        print("2. Set MAILTESTER_NINJA_API_KEY in your .env file")
        print("3. Run the test again")
    else:
        print("Some tests failed - check output above")


if __name__ == "__main__":
    main()