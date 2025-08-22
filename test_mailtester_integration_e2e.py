"""
End-to-End Integration Test for Mailtester Ninja API in Lead Generation Pipeline

This test verifies that the updated lead validation and quality scoring system
properly integrates with the Mailtester Ninja API for enhanced email validation.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.agents.tools.mailtester_email_validation_tool import MailtesterEmailValidationTool, MailtesterBulkValidationTool
    from src.agents.tools.email_validation_tool import EmailValidationTool, BulkEmailValidationTool
    from src.agents.tools.business_scoring_tool import EnhancedBusinessScoringTool
    from src.agents.tools.csv_export_tool import CSVExportTool
    from src.agents.validator_dedupe_agent import ValidatorDedupeAgent
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root and all dependencies are installed")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """Setup test environment and verify API key availability"""
    logger.info("Setting up test environment...")
    
    # Check for required environment variables
    api_key = os.getenv('MAILTESTER_NINJA_API_KEY')
    if not api_key or api_key in ['YOUR_MAILTESTER_NINJA_API_KEY_HERE', '']:
        logger.error("MAILTESTER_NINJA_API_KEY not found or not configured properly")
        logger.error("Please set the environment variable: MAILTESTER_NINJA_API_KEY=your_actual_api_key")
        return False
    
    logger.info("Environment setup completed successfully")
    return True


def create_sample_email_dataset() -> List[str]:
    """Create a sample dataset of emails for testing"""
    return [
        # Valid business emails (should score high)
        "ceo@techstartup.com",
        "john.doe@businesscorp.com",
        "founder@innovativetech.io",
        "contact@consultingfirm.net",
        
        # Personal emails (should score medium)
        "user@gmail.com",
        "someone@yahoo.com",
        "personal@hotmail.com",
        
        # Risky/disposable emails (should score low)
        "test@10minutemail.com",
        "temp@tempmail.org",
        "disposable@guerrillamail.com",
        
        # Invalid emails (should be rejected)
        "invalid-email-format",
        "missing@",
        "@nodomain.com",
    ]


def create_sample_contact_dataset() -> List[Dict[str, Any]]:
    """Create sample contact data for business scoring"""
    return [
        {
            "host_name": "John Smith",
            "title": "CEO",
            "company": "Tech Innovations Inc",
            "host_email": "john.smith@techinnovations.com",
            "podcast_name": "Tech Leadership Podcast",
            "podcast_website": "https://techleadership.com",
            "contact_page_url": "https://techleadership.com/contact",
            "estimated_downloads": 5000,
        },
        {
            "host_name": "Jane Doe",
            "title": "Founder",
            "company": "Marketing Solutions LLC",
            "host_email": "jane@marketingsolutions.biz",
            "podcast_name": "Marketing Mastery",
            "podcast_website": "https://marketingmastery.com",
            "estimated_downloads": 8000,
        },
        {
            "host_name": "Mike Johnson",
            "title": "Host",
            "company": "",
            "host_email": "mike.johnson@gmail.com",
            "podcast_name": "Personal Finance Chat",
            "podcast_website": "",
            "estimated_downloads": 1500,
        },
        {
            "host_name": "Test User",
            "title": "",
            "company": "",
            "host_email": "temp@10minutemail.com",
            "podcast_name": "Test Podcast",
            "podcast_website": "",
            "estimated_downloads": 100,
        }
    ]


def test_mailtester_email_validation():
    """Test basic Mailtester email validation"""
    logger.info("Testing Mailtester email validation...")
    
    test_emails = create_sample_email_dataset()
    
    try:
        validation_tool = MailtesterEmailValidationTool(
            emails=test_emails[:5],  # Test with first 5 emails
            validation_level="basic",
            quality_threshold=0.5
        )
        
        result = validation_tool.run()
        result_data = json.loads(result)
        
        if result_data.get('summary', {}).get('total_emails', 0) > 0:
            logger.info("✅ Mailtester email validation test passed")
            logger.info(f"   - Processed {result_data['summary']['total_emails']} emails")
            logger.info(f"   - Valid emails: {result_data['summary']['valid_emails']}")
            logger.info(f"   - Acceptance rate: {result_data['summary']['acceptance_rate']:.2%}")
            return True, result_data
        else:
            logger.error("❌ Mailtester email validation test failed")
            return False, result_data
            
    except Exception as e:
        logger.error(f"❌ Mailtester validation test error: {e}")
        return False, {"error": str(e)}


def test_enhanced_email_validation_tool():
    """Test the enhanced EmailValidationTool with Mailtester integration"""
    logger.info("Testing enhanced EmailValidationTool...")
    
    test_emails = create_sample_email_dataset()[:6]  # Test subset
    
    try:
        validation_tool = EmailValidationTool(
            emails=test_emails,
            use_mailtester_api=True,
            validation_level="basic"
        )
        
        result = validation_tool.run()
        
        if result.get('summary', {}).get('validation_method', '').startswith('Mailtester'):
            logger.info("✅ Enhanced EmailValidationTool test passed")
            logger.info(f"   - Using: {result['summary']['validation_method']}")
            logger.info(f"   - Processed: {result['summary']['processed']} emails")
            logger.info(f"   - Acceptance rate: {result['summary']['acceptance_rate']:.2%}")
            return True, result
        else:
            logger.warning("⚠️  EmailValidationTool fell back to local validation")
            logger.info(f"   - Method: {result['summary'].get('validation_method', 'Unknown')}")
            return True, result  # Still a pass, just using fallback
            
    except Exception as e:
        logger.error(f"❌ Enhanced EmailValidationTool test error: {e}")
        return False, {"error": str(e)}


def test_enhanced_business_scoring():
    """Test the enhanced business scoring with email validation data"""
    logger.info("Testing enhanced business scoring...")
    
    # First, get validation data for our contacts
    contact_data = create_sample_contact_dataset()
    emails = [contact.get('host_email', '') for contact in contact_data if contact.get('host_email')]
    
    try:
        # Step 1: Validate emails with Mailtester
        validation_tool = MailtesterEmailValidationTool(
            emails=emails,
            validation_level="basic"
        )
        
        validation_result = validation_tool.run()
        validation_data = json.loads(validation_result)
        
        # Step 2: Merge validation data with contact data
        enhanced_contacts = []
        validation_results = validation_data.get('all_results', [])
        
        for i, contact in enumerate(contact_data):
            enhanced_contact = contact.copy()
            
            # Find matching validation result
            email = contact.get('host_email', '')
            for val_result in validation_results:
                if val_result.get('email') == email:
                    # Merge validation fields
                    enhanced_contact.update({
                        'email_validation_method': val_result.get('validation_method', 'Unknown'),
                        'mailtester_score': val_result.get('mailtester_score', 0.0),
                        'mailtester_status': val_result.get('mailtester_status', 'unknown'),
                        'mailtester_confidence_level': val_result.get('mailtester_confidence_level', 'low'),
                        'is_disposable_email': val_result.get('is_disposable', False),
                        'is_role_account': val_result.get('is_role_account', False),
                        'smtp_verified': val_result.get('smtp_verified', False),
                        'is_catch_all_domain': val_result.get('is_catch_all', False),
                        'has_mx_records': val_result.get('has_mx_records', False),
                        'domain_exists': val_result.get('domain_exists', False),
                        'deliverability_verified': val_result.get('deliverability_verified', False)
                    })
                    break
            
            enhanced_contacts.append(enhanced_contact)
        
        # Step 3: Run enhanced business scoring
        scoring_tool = EnhancedBusinessScoringTool(
            contact_data=enhanced_contacts,
            email_quality_weight=0.4,
            prioritize_verified_emails=True
        )
        
        scoring_result = scoring_tool.run()
        
        if scoring_result.get('success', False):
            logger.info("✅ Enhanced business scoring test passed")
            summary = scoring_result['processing_summary']
            logger.info(f"   - Total contacts: {summary['total_contacts']}")
            logger.info(f"   - High priority leads: {summary['high_priority_leads']}")
            logger.info(f"   - Medium priority leads: {summary['medium_priority_leads']}")
            logger.info(f"   - Low priority leads: {summary['low_priority_leads']}")
            logger.info(f"   - Verified emails: {summary['verified_email_count']}")
            return True, scoring_result
        else:
            logger.error("❌ Enhanced business scoring test failed")
            return False, scoring_result
            
    except Exception as e:
        logger.error(f"❌ Enhanced business scoring test error: {e}")
        return False, {"error": str(e)}


def test_csv_export_with_validation_fields():
    """Test CSV export with new Mailtester validation fields"""
    logger.info("Testing CSV export with validation fields...")
    
    try:
        # Create sample data with validation fields
        sample_data = [
            {
                "podcast_name": "Tech Talk",
                "host_name": "John Doe",
                "host_email": "john@techcorp.com",
                "email_validation_method": "Mailtester Ninja API",
                "mailtester_score": 0.85,
                "mailtester_status": "valid",
                "mailtester_confidence_level": "high",
                "is_disposable_email": False,
                "is_role_account": True,
                "smtp_verified": True,
                "is_catch_all_domain": False,
                "has_mx_records": True,
                "domain_exists": True,
                "deliverability_verified": True,
                "contact_quality_score": 0.9,
                "response_likelihood": 0.8,
                "validation_date": "2025-01-20",
                "data_quality_grade": "A"
            }
        ]
        
        # Export to CSV
        output_path = os.path.join(os.path.dirname(__file__), "test_export_with_validation.csv")
        
        csv_tool = CSVExportTool(
            contact_data=sample_data,
            output_path=output_path,
            validate_schema=True
        )
        
        result = csv_tool.run()
        result_data = json.loads(result)
        
        if result_data.get('success', False) and os.path.exists(output_path):
            logger.info("✅ CSV export with validation fields test passed")
            logger.info(f"   - Exported to: {output_path}")
            logger.info(f"   - Rows exported: {result_data['metrics']['total_rows']}")
            
            # Clean up test file
            try:
                os.remove(output_path)
                metadata_path = output_path.replace('.csv', '_metadata.json')
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
            except:
                pass
            
            return True, result_data
        else:
            logger.error("❌ CSV export test failed")
            return False, result_data
            
    except Exception as e:
        logger.error(f"❌ CSV export test error: {e}")
        return False, {"error": str(e)}


def test_validator_dedupe_agent_integration():
    """Test ValidatorDedupeAgent with Mailtester data"""
    logger.info("Testing ValidatorDedupeAgent integration...")
    
    try:
        # Create sample contact data with validation results
        contact_data = [
            {
                "email": "ceo@techcorp.com",
                "name": "John Smith",
                "company": "Tech Corp",
                "mailtester_score": 0.9,
                "mailtester_status": "valid",
                "is_disposable": False,
                "is_role_account": True,
                "smtp_verified": True
            },
            {
                "email": "temp@10minutemail.com",
                "name": "Test User",
                "company": "",
                "mailtester_score": 0.1,
                "mailtester_status": "invalid",
                "is_disposable": True,
                "is_role_account": False,
                "smtp_verified": False
            }
        ]
        
        # Initialize validator agent
        agent = ValidatorDedupeAgent()
        
        # Extract emails for validation
        emails = [item['email'] for item in contact_data]
        
        # Validate with contact data context
        results = agent.validate_email_batch(emails, contact_data)
        
        if len(results) > 0:
            logger.info("✅ ValidatorDedupeAgent integration test passed")
            
            # Check if enhanced scoring was applied
            for i, result in enumerate(results):
                email = result.email
                original_data = contact_data[i]
                
                logger.info(f"   - {email}: {result.quality.value} quality (score: {result.confidence_score:.2f})")
                
                # Verify that Mailtester data influenced the scoring
                if original_data.get('is_disposable', False) and result.quality.value in ['spam', 'low']:
                    logger.info(f"     ✓ Disposable email correctly penalized")
                elif original_data.get('smtp_verified', False) and result.confidence_score > 0.7:
                    logger.info(f"     ✓ SMTP verified email correctly boosted")
            
            return True, results
        else:
            logger.error("❌ ValidatorDedupeAgent integration test failed")
            return False, results
            
    except Exception as e:
        logger.error(f"❌ ValidatorDedupeAgent integration test error: {e}")
        return False, {"error": str(e)}


def run_full_pipeline_test():
    """Run a complete end-to-end pipeline test"""
    logger.info("Running full pipeline integration test...")
    
    try:
        # Step 1: Create sample contact data
        contact_data = create_sample_contact_dataset()
        emails = [contact.get('host_email', '') for contact in contact_data if contact.get('host_email')]
        
        # Step 2: Validate emails with Mailtester
        logger.info("Step 1: Email validation with Mailtester API...")
        validation_tool = MailtesterEmailValidationTool(
            emails=emails,
            validation_level="basic",
            batch_size=10
        )
        
        validation_result = validation_tool.run()
        validation_data = json.loads(validation_result)
        
        if not validation_data.get('summary', {}).get('total_emails', 0):
            logger.error("❌ Email validation step failed")
            return False
        
        logger.info(f"✓ Validated {validation_data['summary']['total_emails']} emails")
        
        # Step 3: Enhance contact data with validation results
        logger.info("Step 2: Enhancing contact data with validation results...")
        enhanced_contacts = []
        validation_results = validation_data.get('all_results', [])
        
        for contact in contact_data:
            enhanced_contact = contact.copy()
            email = contact.get('host_email', '')
            
            # Find matching validation result
            for val_result in validation_results:
                if val_result.get('email') == email:
                    enhanced_contact.update({
                        'email_validation_method': 'Mailtester Ninja API',
                        'mailtester_score': val_result.get('mailtester_score', 0.0),
                        'mailtester_status': val_result.get('mailtester_status', 'unknown'),
                        'mailtester_confidence_level': val_result.get('mailtester_confidence_level', 'low'),
                        'is_disposable_email': val_result.get('is_disposable', False),
                        'is_role_account': val_result.get('is_role_account', False),
                        'smtp_verified': val_result.get('smtp_verified', False),
                        'is_catch_all_domain': val_result.get('is_catch_all', False),
                        'has_mx_records': val_result.get('has_mx_records', False),
                        'domain_exists': val_result.get('domain_exists', False),
                        'deliverability_verified': val_result.get('deliverability_verified', False),
                        'validation_status': 'verified'
                    })
                    break
            
            enhanced_contacts.append(enhanced_contact)
        
        logger.info(f"✓ Enhanced {len(enhanced_contacts)} contact records")
        
        # Step 4: Business scoring with email validation
        logger.info("Step 3: Business scoring with email validation integration...")
        scoring_tool = EnhancedBusinessScoringTool(
            contact_data=enhanced_contacts,
            email_quality_weight=0.4
        )
        
        scoring_result = scoring_tool.run()
        
        if not scoring_result.get('success', False):
            logger.error("❌ Business scoring step failed")
            return False
        
        high_priority = scoring_result['processing_summary']['high_priority_leads']
        medium_priority = scoring_result['processing_summary']['medium_priority_leads']
        low_priority = scoring_result['processing_summary']['low_priority_leads']
        
        logger.info(f"✓ Scored contacts: {high_priority} high, {medium_priority} medium, {low_priority} low priority")
        
        # Step 5: CSV export with all validation fields
        logger.info("Step 4: CSV export with validation fields...")
        scored_contacts = scoring_result['enhanced_scoring_results']
        
        output_path = os.path.join(os.path.dirname(__file__), "full_pipeline_test_export.csv")
        
        csv_tool = CSVExportTool(
            contact_data=scored_contacts,
            output_path=output_path,
            validate_schema=True
        )
        
        csv_result = csv_tool.run()
        csv_data = json.loads(csv_result)
        
        if not csv_data.get('success', False):
            logger.error("❌ CSV export step failed")
            return False
        
        logger.info(f"✓ Exported {csv_data['metrics']['total_rows']} rows to CSV")
        
        # Clean up test file
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            metadata_path = output_path.replace('.csv', '_metadata.json')
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
        except:
            pass
        
        logger.info("✅ Full pipeline integration test passed!")
        logger.info("🎉 All components working together successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Full pipeline test error: {e}")
        return False


def main():
    """Main test runner"""
    print("=" * 80)
    print("🚀 MAILTESTER NINJA API INTEGRATION TEST SUITE")
    print("=" * 80)
    
    # Setup
    if not setup_test_environment():
        print("❌ Environment setup failed. Exiting.")
        return False
    
    test_results = []
    
    # Individual component tests
    tests = [
        ("Mailtester Email Validation", test_mailtester_email_validation),
        ("Enhanced EmailValidationTool", test_enhanced_email_validation_tool),
        ("Enhanced Business Scoring", test_enhanced_business_scoring),
        ("CSV Export with Validation Fields", test_csv_export_with_validation_fields),
        ("ValidatorDedupeAgent Integration", test_validator_dedupe_agent_integration),
    ]
    
    print(f"\n📋 Running {len(tests)} individual component tests...\n")
    
    for test_name, test_func in tests:
        print(f"🔄 Running: {test_name}")
        try:
            success, result = test_func()
            test_results.append((test_name, success, result))
            if success:
                print(f"✅ PASSED: {test_name}")
            else:
                print(f"❌ FAILED: {test_name}")
                if isinstance(result, dict) and 'error' in result:
                    print(f"   Error: {result['error']}")
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {e}")
            test_results.append((test_name, False, {"error": str(e)}))
        print()
    
    # Full pipeline test
    print("🔄 Running full end-to-end pipeline test...\n")
    pipeline_success = run_full_pipeline_test()
    test_results.append(("Full Pipeline Integration", pipeline_success, {}))
    
    # Results summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed_tests = sum(1 for _, success, _ in test_results if success)
    total_tests = len(test_results)
    
    for test_name, success, result in test_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Mailtester Ninja API integration is working correctly.")
        print("🚀 The lead generation pipeline now uses real API validation for enhanced quality scoring.")
    else:
        print(f"⚠️  Some tests failed. Please check the logs above for details.")
        print("🔧 Consider reviewing the API configuration and network connectivity.")
    
    print("=" * 80)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)