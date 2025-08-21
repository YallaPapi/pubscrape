"""
Test script for ValidatorDedupe Agent

Demonstrates the email validation and deduplication system with sample data.
"""

import logging
import time
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Sample test data
SAMPLE_EMAILS = [
    # Valid business emails
    "john.doe@company.com",
    "sarah.smith@techcorp.org", 
    "director@startup.co",
    "ceo@businessfirm.net",
    "contact@consulting.biz",
    
    # Personal emails (lower quality)
    "user123@gmail.com",
    "someone@yahoo.com",
    "person@hotmail.com",
    
    # Blacklisted emails
    "noreply@company.com",
    "donotreply@service.org",
    "test@example.com",
    "admin@localhost",
    "webmaster@site.net",
    
    # Invalid emails
    "invalid-email",
    "missing@",
    "@domain.com",
    "spaces in@email.com",
    "user@invalid-tld.xyz123",
    
    # Duplicates
    "john.doe@company.com",  # Duplicate of first email
    "JOHN.DOE@COMPANY.COM",  # Case variation
    "sarah.smith@techcorp.org",  # Duplicate
    
    # Edge cases
    "very.long.email.address.that.might.cause.issues@some-very-long-domain-name.com",
    "unicode-test@münchen.de",
    "plus+tag@company.com",
]

SAMPLE_CONTACT_DATA = [
    {"name": "John Doe", "title": "CEO", "company": "Company Inc"},
    {"name": "Sarah Smith", "title": "Director", "company": "TechCorp"},
    {"name": "Unknown User", "title": "Manager", "company": "Startup Co"},
    {"name": "Business Owner", "title": "Founder", "company": "Business Firm"},
    {"name": "", "title": "", "company": "Consulting LLC"},
    
    # Personal emails - minimal data
    {"name": "Gmail User", "title": "", "company": ""},
    {"name": "", "title": "", "company": ""},
    {"name": "Personal User", "title": "", "company": ""},
    
    # Blacklisted - system emails
    {"name": "System", "title": "No Reply", "company": "Company Inc"},
    {"name": "Automated", "title": "System", "company": "Service Org"},
    {"name": "", "title": "", "company": "Example"},
    {"name": "Admin", "title": "Administrator", "company": "Local"},
    {"name": "Web Master", "title": "Webmaster", "company": "Site"},
    
    # Invalid emails - no associated data
    {}, {}, {}, {}, {},
    
    # Duplicates - same contact data
    {"name": "John Doe", "title": "CEO", "company": "Company Inc"},  # Duplicate
    {"name": "John Doe", "title": "Chief Executive Officer", "company": "Company Inc"},  # Variation
    {"name": "Sarah Smith", "title": "Director", "company": "TechCorp"},  # Duplicate
    
    # Edge cases
    {"name": "Very Long Name That Might Cause Issues", "title": "Senior Vice President of Technology", "company": "Some Very Long Company Name LLC"},
    {"name": "Unicode User", "title": "Geschäftsführer", "company": "München GmbH"},
    {"name": "John Doe", "title": "CEO", "company": "Company Inc"},  # Tagged email variation
]


def test_email_syntax_validation():
    """Test email syntax validation"""
    print("\n" + "="*50)
    print("Testing Email Syntax Validation")
    print("="*50)
    
    try:
        from validator_dedupe_agent import EmailSyntaxValidator
        
        validator = EmailSyntaxValidator({
            "log_level": logging.INFO,
            "strict_validation": True
        })
        
        print(f"Testing {len(SAMPLE_EMAILS)} email addresses...")
        
        valid_count = 0
        invalid_count = 0
        
        for email in SAMPLE_EMAILS:
            result = validator.validate_syntax(email)
            
            if result.is_valid:
                valid_count += 1
                print(f"✓ VALID: {email} (Quality: {result.quality.value}, Confidence: {result.confidence_score:.2f})")
            else:
                invalid_count += 1
                print(f"✗ INVALID: {email} - {result.reason}")
        
        print(f"\nSummary: {valid_count} valid, {invalid_count} invalid")
        print(f"Acceptance Rate: {valid_count / len(SAMPLE_EMAILS):.1%}")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the validator_dedupe_agent module is in the Python path")


def test_dns_validation():
    """Test DNS validation with caching"""
    print("\n" + "="*50)
    print("Testing DNS Validation")
    print("="*50)
    
    try:
        from validator_dedupe_agent import DNSValidator, ValidationResult, ValidationStatus
        
        dns_validator = DNSValidator({
            "enable_mx_check": True,
            "dns_timeout": 3.0,
            "enable_caching": True,
            "log_level": logging.INFO
        })
        
        # Test with valid business domains
        test_domains = [
            "company.com", "techcorp.org", "startup.co", 
            "gmail.com", "yahoo.com", "nonexistent-domain-12345.com"
        ]
        
        print(f"Testing DNS validation for {len(test_domains)} domains...")
        
        for domain in test_domains:
            # Create a mock validation result
            result = ValidationResult(
                email=f"test@{domain}",
                status=ValidationStatus.VALID,
                is_valid=True,
                domain=domain
            )
            
            # Validate domain
            result = dns_validator.validate_domain(domain, result)
            
            if result.mx_records:
                print(f"✓ {domain}: {len(result.mx_records)} MX records - {', '.join(result.mx_records[:2])}")
            else:
                print(f"✗ {domain}: No MX records found - {result.reason}")
        
    except ImportError as e:
        print(f"Import error: {e}")


def test_blacklist_filtering():
    """Test blacklist filtering"""
    print("\n" + "="*50)
    print("Testing Blacklist Filtering")
    print("="*50)
    
    try:
        from validator_dedupe_agent import BlacklistFilter, ValidationResult, ValidationStatus
        
        blacklist_filter = BlacklistFilter({
            "log_level": logging.INFO
        })
        
        print(f"Testing blacklist filtering for {len(SAMPLE_EMAILS)} emails...")
        
        blacklisted_count = 0
        allowed_count = 0
        
        for email in SAMPLE_EMAILS:
            # Create mock validation result
            result = ValidationResult(
                email=email,
                status=ValidationStatus.VALID,
                is_valid=True
            )
            
            # Apply blacklist filter
            result = blacklist_filter.check_blacklist(email, result)
            
            if result.status == ValidationStatus.BLACKLISTED:
                blacklisted_count += 1
                print(f"🚫 BLACKLISTED: {email} - {result.reason}")
            else:
                allowed_count += 1
                print(f"✓ ALLOWED: {email}")
        
        print(f"\nSummary: {allowed_count} allowed, {blacklisted_count} blacklisted")
        print(f"Blacklist Rate: {blacklisted_count / len(SAMPLE_EMAILS):.1%}")
        
    except ImportError as e:
        print(f"Import error: {e}")


def test_deduplication():
    """Test email deduplication"""
    print("\n" + "="*50)
    print("Testing Email Deduplication")
    print("="*50)
    
    try:
        from validator_dedupe_agent import EmailDeduplicator, ValidationResult, ValidationStatus
        
        deduplicator = EmailDeduplicator({
            "strict_deduplication": False,
            "merge_similar_domains": True,
            "similarity_threshold": 0.8,
            "log_level": logging.INFO
        })
        
        print(f"Testing deduplication for {len(SAMPLE_EMAILS)} emails...")
        
        duplicate_count = 0
        unique_count = 0
        
        for i, email in enumerate(SAMPLE_EMAILS):
            # Create mock validation result
            result = ValidationResult(
                email=email,
                status=ValidationStatus.VALID,
                is_valid=True,
                confidence_score=0.7
            )
            
            # Get contact data if available
            contact_data = SAMPLE_CONTACT_DATA[i] if i < len(SAMPLE_CONTACT_DATA) else {}
            
            # Check for duplicate
            result, is_duplicate = deduplicator.check_duplicate(email, result, contact_data)
            
            if is_duplicate:
                duplicate_count += 1
                print(f"🔄 DUPLICATE: {email}")
            else:
                unique_count += 1
                print(f"✓ UNIQUE: {email}")
        
        # Get final statistics
        stats = deduplicator.get_deduplication_stats()
        final_contacts = deduplicator.get_final_contacts()
        
        print(f"\nDeduplication Summary:")
        print(f"  Original emails: {len(SAMPLE_EMAILS)}")
        print(f"  Unique emails: {unique_count}")
        print(f"  Duplicates found: {duplicate_count}")
        print(f"  Final contact records: {len(final_contacts)}")
        print(f"  Duplicate rate: {stats.get('duplicate_rate', 0):.1%}")
        
    except ImportError as e:
        print(f"Import error: {e}")


def test_full_validation_pipeline():
    """Test the complete validation pipeline"""
    print("\n" + "="*50)
    print("Testing Complete Validation Pipeline")
    print("="*50)
    
    try:
        from validator_dedupe_agent import ValidatorDedupeAgent
        
        # Create agent
        agent = ValidatorDedupeAgent()
        
        print(f"Testing complete pipeline with {len(SAMPLE_EMAILS)} emails...")
        start_time = time.time()
        
        # Validate batch
        results = agent.validate_email_batch(
            emails=SAMPLE_EMAILS,
            contact_data=SAMPLE_CONTACT_DATA[:len(SAMPLE_EMAILS)],
            max_workers=5
        )
        
        processing_time = time.time() - start_time
        
        # Analyze results
        valid_emails = [r for r in results if r.is_valid]
        high_quality = [r for r in valid_emails if r.quality.value == 'high']
        
        print(f"\nPipeline Results:")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Emails per second: {len(SAMPLE_EMAILS) / processing_time:.1f}")
        print(f"  Total processed: {len(results)}")
        print(f"  Valid emails: {len(valid_emails)}")
        print(f"  High quality: {len(high_quality)}")
        print(f"  Acceptance rate: {len(valid_emails) / len(results):.1%}")
        print(f"  Quality rate: {len(high_quality) / max(1, len(valid_emails)):.1%}")
        
        # Get comprehensive report
        report = agent.get_validation_report()
        
        print(f"\nFinal Statistics:")
        print(f"  Validation acceptance rate: {report['validation']['summary']['acceptance_rate']:.1%}")
        print(f"  Deduplication rate: {report['deduplication']['duplicate_rate']:.1%}")
        print(f"  Final contact records: {report['final_contacts']}")
        
        # Log summary
        agent.log_summary()
        
    except ImportError as e:
        print(f"Import error: {e}")


def test_validation_tools():
    """Test the Agency Swarm tools"""
    print("\n" + "="*50)
    print("Testing Validation Tools")
    print("="*50)
    
    try:
        from tools.email_validation_tool import EmailValidationTool
        from tools.email_deduplication_tool import EmailDeduplicationTool
        
        # Test email validation tool
        print("Testing EmailValidationTool...")
        validation_tool = EmailValidationTool(
            emails=SAMPLE_EMAILS[:10],  # Test subset
            enable_dns_check=False,  # Skip DNS for speed
            max_workers=3
        )
        
        validation_results = validation_tool.run()
        print(f"Validation tool processed {validation_results['summary']['processed']} emails")
        print(f"Acceptance rate: {validation_results['summary']['acceptance_rate']:.1%}")
        
        # Test deduplication tool
        print("\nTesting EmailDeduplicationTool...")
        
        # Prepare contact data
        contacts = []
        for i, email in enumerate(SAMPLE_EMAILS):
            contact_data = SAMPLE_CONTACT_DATA[i] if i < len(SAMPLE_CONTACT_DATA) else {}
            contact_data['email'] = email
            contacts.append(contact_data)
        
        dedup_tool = EmailDeduplicationTool(
            contacts=contacts,
            strict_mode=False,
            similarity_threshold=0.8
        )
        
        dedup_results = dedup_tool.run()
        print(f"Deduplication tool processed {dedup_results['summary']['original_contacts']} contacts")
        print(f"Final unique contacts: {dedup_results['summary']['final_contacts']}")
        print(f"Duplicate rate: {dedup_results['summary']['duplicate_rate']:.1%}")
        
    except ImportError as e:
        print(f"Tool import error: {e}")


if __name__ == "__main__":
    print("ValidatorDedupe Agent Test Suite")
    print("=" * 60)
    
    # Run all tests
    test_email_syntax_validation()
    test_dns_validation()
    test_blacklist_filtering()
    test_deduplication()
    test_full_validation_pipeline()
    test_validation_tools()
    
    print("\n" + "="*60)
    print("Test Suite Complete")
    print("="*60)