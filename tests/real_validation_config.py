#!/usr/bin/env python3
"""
Configuration for Real Validation Testing

This file contains configuration for real-world testing scenarios,
including live websites, detection services, and performance benchmarks.
"""

# Real websites for Cloudflare bypass testing
CLOUDFLARE_PROTECTED_SITES = [
    "https://quotes.toscrape.com/",  # Known Cloudflare-protected site
    "https://httpbin.org/delay/2",   # May have CF protection
    "https://scrape.world/",         # Scraping test site with protection
    "https://nowsecure.nl/",         # Bot detection test site
]

# Real bot detection services for fingerprinting tests
BOT_DETECTION_SERVICES = [
    "https://bot.sannysoft.com/",    # Comprehensive bot detection
    "https://fingerprintjs.com/demo/", # Fingerprinting service
    "https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html",  # Headless detection
    "https://httpbin.org/user-agent", # User agent analysis
    "https://httpbin.org/headers",    # Header analysis
    "https://www.whatismybrowser.com/detect/what-is-my-user-agent", # Browser detection
]

# Real business websites for email extraction testing
BUSINESS_TEST_WEBSITES = [
    "https://example.com",           # Basic HTML site
    "https://httpbin.org/html",      # Test HTML content
    # Note: Add real business websites for comprehensive testing
    # These should be sites you have permission to test against
]

# Performance benchmarks for real load testing
PERFORMANCE_BENCHMARKS = {
    'min_throughput_leads_per_second': 0.3,    # Minimum processing speed
    'max_memory_usage_mb': 1024,               # Maximum memory per session
    'max_response_time_seconds': 10,           # Maximum response time
    'min_email_extraction_rate': 0.15,         # Minimum email extraction success
    'min_data_quality_score': 0.6,            # Minimum valid lead percentage
    'max_detection_rate': 0.2,                # Maximum bot detection rate
    'min_session_isolation_rate': 0.8,        # Minimum session isolation success
}

# Real search queries for integration testing
INTEGRATION_TEST_QUERIES = [
    {'query': 'restaurant', 'location': 'Miami, FL', 'expected_min_results': 3},
    {'query': 'dental clinic', 'location': 'Chicago, IL', 'expected_min_results': 3},
    {'query': 'law firm', 'location': 'Houston, TX', 'expected_min_results': 3},
    {'query': 'medical clinic', 'location': 'Phoenix, AZ', 'expected_min_results': 3},
    {'query': 'accounting firm', 'location': 'Seattle, WA', 'expected_min_results': 3},
]

# Error recovery test scenarios
ERROR_RECOVERY_SCENARIOS = [
    {
        'name': 'Invalid URL',
        'url': 'https://this-domain-definitely-does-not-exist-12345.com',
        'expected_recovery': True,
        'timeout_seconds': 10
    },
    {
        'name': 'Timeout URL',
        'url': 'https://httpbin.org/delay/15',
        'expected_recovery': True,
        'timeout_seconds': 12
    },
    {
        'name': 'Empty Response',
        'url': 'data:text/html,<html></html>',
        'expected_recovery': True,
        'timeout_seconds': 5
    },
    {
        'name': 'Malformed HTML',
        'url': 'data:text/html,<html><body>Incomplete',
        'expected_recovery': True,
        'timeout_seconds': 5
    }
]

# Anti-detection test configuration
ANTI_DETECTION_CONFIG = {
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ],
    'screen_resolutions': [
        (1920, 1080), (1440, 900), (1366, 768), (1536, 864), (1280, 720), (1600, 900)
    ],
    'request_delays': {
        'min_delay_seconds': 1.0,
        'max_delay_seconds': 3.0,
        'randomization_factor': 0.3
    }
}

# Email validation test data
EMAIL_VALIDATION_TESTS = [
    # Valid emails (should pass validation)
    {'email': 'info@google.com', 'expected_valid': True, 'category': 'major_domain'},
    {'email': 'contact@microsoft.com', 'expected_valid': True, 'category': 'major_domain'},
    {'email': 'support@github.com', 'expected_valid': True, 'category': 'major_domain'},
    
    # Invalid format emails (should fail validation)
    {'email': 'notanemail', 'expected_valid': False, 'category': 'invalid_format'},
    {'email': 'incomplete@', 'expected_valid': False, 'category': 'invalid_format'},
    {'email': '@nodomain.com', 'expected_valid': False, 'category': 'invalid_format'},
    
    # Questionable domains (should fail validation)
    {'email': 'test@example.com', 'expected_valid': False, 'category': 'example_domain'},
    {'email': 'user@nonexistentdomain12345.com', 'expected_valid': False, 'category': 'nonexistent_domain'},
]

# Export validation configuration
EXPORT_TEST_CONFIG = {
    'formats': ['csv', 'json'],
    'required_fields': ['name', 'email', 'phone', 'website', 'address'],
    'min_export_size_bytes': 100,
    'max_export_time_seconds': 30
}

# Concurrent testing configuration
CONCURRENCY_TEST_CONFIG = {
    'max_concurrent_sessions': 3,
    'leads_per_session': 5,
    'session_timeout_seconds': 30,
    'expected_success_rate': 0.8
}

# Test environment configuration
TEST_ENVIRONMENT = {
    'output_directory': 'test_output',
    'log_level': 'INFO',
    'save_html_snapshots': True,
    'save_performance_metrics': True,
    'cleanup_test_files': True
}