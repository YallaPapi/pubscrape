#!/usr/bin/env python3
"""
Basic Usage Examples for PubScrape Infinite Scroll Scraper System

This file demonstrates the most common and straightforward ways to use
the PubScrape system for lead generation and data extraction.
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core modules
from botasaurus_doctor_scraper import search_bing_for_doctors, extract_doctor_contact_info, main
from src.core.config_manager import ConfigManager
from src.infra.browser_manager import create_browser_manager, BrowserConfig, BrowserMode


def example_1_simple_doctor_search():
    """
    Example 1: Simple doctor search and extraction
    
    This is the most basic usage - just run the built-in doctor scraper.
    """
    print("\n" + "="*60)
    print("🏥 EXAMPLE 1: Simple Doctor Search")
    print("="*60)
    
    print("Running the built-in doctor scraper...")
    print("This will search for 'doctors in miami' and extract contact info.")
    
    # Simply call the main function
    main()
    
    print("✅ Simple doctor search completed!")
    print("Check the generated CSV file for results.")


def example_2_custom_search_query():
    """
    Example 2: Custom search query with specific extraction
    
    Shows how to use individual functions for custom queries.
    """
    print("\n" + "="*60)
    print("🔍 EXAMPLE 2: Custom Search Query")
    print("="*60)
    
    # Define custom search query
    custom_query = "pediatricians in Los Angeles contact information"
    print(f"Searching for: {custom_query}")
    
    # Step 1: Search Bing for relevant URLs
    print("\n📋 Step 1: Searching Bing...")
    search_results = search_bing_for_doctors(custom_query)
    
    print(f"✅ Search completed:")
    print(f"   Query: {search_results['query']}")
    print(f"   URLs found: {search_results['total_urls']}")
    print(f"   HTML length: {search_results['search_html_length']} characters")
    
    if search_results['total_urls'] == 0:
        print("❌ No URLs found. Try a different query.")
        return
    
    # Show first few URLs
    print(f"\n📄 Sample URLs found:")
    for i, url in enumerate(search_results['urls_found'][:3]):
        print(f"   {i+1}. {url}")
    
    # Step 2: Extract contact information from first 3 URLs
    print(f"\n🔍 Step 2: Extracting contact info from first 3 URLs...")
    extracted_leads = []
    
    for i, url in enumerate(search_results['urls_found'][:3], 1):
        print(f"\nProcessing {i}/3: {url}")
        
        try:
            contact_info = extract_doctor_contact_info(url)
            
            if contact_info['extraction_successful']:
                lead = {
                    'business_name': contact_info['business_name'],
                    'website': url,
                    'emails': contact_info['emails'],
                    'phones': contact_info['phones'],
                    'doctor_names': contact_info['doctor_names']
                }
                extracted_leads.append(lead)
                
                print(f"   ✅ SUCCESS: {lead['business_name']}")
                print(f"      Emails: {len(lead['emails'])} found")
                print(f"      Phones: {len(lead['phones'])} found")
            else:
                print(f"   ❌ FAILED: {contact_info.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
    
    # Step 3: Display results
    print(f"\n📊 Extraction Results:")
    print(f"   Total leads extracted: {len(extracted_leads)}")
    
    for i, lead in enumerate(extracted_leads, 1):
        print(f"\n   Lead {i}:")
        print(f"      Business: {lead['business_name']}")
        print(f"      Website: {lead['website']}")
        print(f"      Primary Email: {lead['emails'][0] if lead['emails'] else 'None'}")
        print(f"      Primary Phone: {lead['phones'][0] if lead['phones'] else 'None'}")


def example_3_configuration_usage():
    """
    Example 3: Using the configuration system
    
    Shows how to load, modify, and use configuration settings.
    """
    print("\n" + "="*60)
    print("⚙️ EXAMPLE 3: Configuration Usage")
    print("="*60)
    
    # Get configuration manager
    config = ConfigManager()
    
    print("Current configuration settings:")
    
    # Display current settings
    current_settings = {
        'Max pages per query': config.get('search.max_pages_per_query', 5),
        'Rate limit (RPM)': config.get('search.rate_limit_rpm', 12),
        'Timeout (seconds)': config.get('search.timeout_seconds', 30),
        'Debug mode': config.get('debug_mode', False),
        'Log level': config.get('logging.log_level', 'INFO')
    }
    
    for setting, value in current_settings.items():
        print(f"   {setting}: {value}")
    
    # Modify settings for conservative scraping
    print(f"\n🔧 Modifying settings for conservative scraping...")
    config.set('search.max_pages_per_query', 2)
    config.set('search.rate_limit_rpm', 6)
    config.set('search.timeout_seconds', 45)
    config.set('debug_mode', True)
    config.set('logging.log_level', 'DEBUG')
    
    print("Updated settings:")
    updated_settings = {
        'Max pages per query': config.get('search.max_pages_per_query'),
        'Rate limit (RPM)': config.get('search.rate_limit_rpm'),
        'Timeout (seconds)': config.get('search.timeout_seconds'),
        'Debug mode': config.get('debug_mode'),
        'Log level': config.get('logging.log_level')
    }
    
    for setting, value in updated_settings.items():
        print(f"   {setting}: {value}")
    
    # Validate configuration
    print(f"\n✅ Validating configuration...")
    is_valid, errors = config.validate()
    
    if is_valid:
        print("   Configuration is valid!")
    else:
        print("   Configuration errors found:")
        for error in errors:
            print(f"      - {error}")
    
    # Save configuration to file
    config_file = "examples/example_config.yaml"
    if config.save(config_file):
        print(f"   Configuration saved to: {config_file}")
    else:
        print(f"   Failed to save configuration")


def example_4_browser_management():
    """
    Example 4: Browser session management
    
    Shows how to create and manage browser sessions manually.
    """
    print("\n" + "="*60)
    print("🌐 EXAMPLE 4: Browser Management")
    print("="*60)
    
    print("Creating browser manager with custom configuration...")
    
    # Create browser manager with custom settings
    browser_manager = create_browser_manager(
        mode="headless",  # Use headless mode
        block_resources=True,  # Block images, CSS, etc. for speed
        domain_overrides={
            "bing.com": {
                "timeout": 45,
                "user_agent": "Custom User Agent 1.0"
            }
        }
    )
    
    try:
        # Create a browser session
        print("\n🚀 Creating browser session...")
        session = browser_manager.get_browser_session("example_session", "bing.com")
        
        print("✅ Browser session created successfully")
        
        # Test navigation
        print("\n🔍 Testing navigation to a simple page...")
        session.get("https://httpbin.org/html")
        
        page_title = session.title
        print(f"   Page title: {page_title}")
        
        # Get page source length
        html_length = len(session.page_source)
        print(f"   HTML length: {html_length} characters")
        
        # Test JavaScript execution
        print("\n⚡ Testing JavaScript execution...")
        js_result = session.execute_script("return document.readyState;")
        print(f"   Document ready state: {js_result}")
        
        # Get session statistics
        print("\n📊 Session statistics:")
        stats = browser_manager.get_session_stats("example_session")
        if stats:
            print(f"   Created at: {stats['created_at']}")
            print(f"   Requests made: {stats['requests_count']}")
            print(f"   Domain: {stats['domain']}")
        
    except Exception as e:
        print(f"❌ Browser session error: {e}")
    
    finally:
        # Clean up
        print("\n🧹 Cleaning up browser sessions...")
        browser_manager.close_all_sessions()
        print("   All sessions closed")


def example_5_batch_processing():
    """
    Example 5: Processing multiple queries in batch
    
    Shows how to process multiple search queries efficiently.
    """
    print("\n" + "="*60)
    print("📦 EXAMPLE 5: Batch Processing")
    print("="*60)
    
    # Define multiple queries
    queries = [
        "dentists in Chicago contact",
        "lawyers in New York email",
        "accountants in Dallas phone"
    ]
    
    print(f"Processing {len(queries)} queries in batch:")
    for i, query in enumerate(queries, 1):
        print(f"   {i}. {query}")
    
    all_results = {}
    total_urls_found = 0
    
    # Process each query
    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Processing query {i}/{len(queries)}: {query}")
        
        try:
            # Search for URLs
            search_results = search_bing_for_doctors(query)
            urls_found = search_results['total_urls']
            total_urls_found += urls_found
            
            print(f"   ✅ Found {urls_found} URLs")
            
            # Store results
            all_results[query] = {
                'urls_found': urls_found,
                'urls': search_results['urls_found'][:5],  # Keep first 5 URLs
                'status': 'success'
            }
            
            # Add delay between queries to be respectful
            if i < len(queries):
                print(f"   ⏳ Waiting 3 seconds before next query...")
                time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            all_results[query] = {
                'urls_found': 0,
                'urls': [],
                'status': 'failed',
                'error': str(e)
            }
    
    # Summary results
    print(f"\n📊 Batch Processing Summary:")
    print(f"   Queries processed: {len(queries)}")
    print(f"   Total URLs found: {total_urls_found}")
    print(f"   Average URLs per query: {total_urls_found / len(queries):.1f}")
    
    successful_queries = sum(1 for result in all_results.values() if result['status'] == 'success')
    print(f"   Success rate: {successful_queries}/{len(queries)} ({successful_queries/len(queries)*100:.1f}%)")
    
    # Show detailed results
    print(f"\n📋 Detailed Results:")
    for query, result in all_results.items():
        print(f"\n   Query: {query}")
        print(f"   Status: {result['status']}")
        print(f"   URLs found: {result['urls_found']}")
        
        if result['status'] == 'success' and result['urls']:
            print(f"   Sample URLs:")
            for j, url in enumerate(result['urls'][:2], 1):
                print(f"      {j}. {url}")
        elif result['status'] == 'failed':
            print(f"   Error: {result.get('error', 'Unknown error')}")


def example_6_error_handling():
    """
    Example 6: Proper error handling and recovery
    
    Shows how to handle common errors gracefully.
    """
    print("\n" + "="*60)
    print("🛡️ EXAMPLE 6: Error Handling")
    print("="*60)
    
    def safe_extraction_with_retry(url, max_retries=3):
        """Extract data with retry logic and error handling"""
        
        for attempt in range(max_retries):
            try:
                print(f"   Attempt {attempt + 1}/{max_retries}: {url}")
                
                # Try extraction
                result = extract_doctor_contact_info(url)
                
                if result['extraction_successful']:
                    print(f"   ✅ Success on attempt {attempt + 1}")
                    return result
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"   ⚠️  Extraction failed: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # Exponential backoff
                        print(f"   ⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                
            except Exception as e:
                print(f"   ❌ Exception on attempt {attempt + 1}: {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"   ⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"   💀 All attempts failed for {url}")
                    return {
                        'url': url,
                        'extraction_successful': False,
                        'error': f"All {max_retries} attempts failed: {str(e)}"
                    }
        
        return {
            'url': url,
            'extraction_successful': False,
            'error': f"Failed after {max_retries} attempts"
        }
    
    # Test URLs (some may be invalid for demonstration)
    test_urls = [
        "https://httpbin.org/html",  # Should work
        "https://invalid-domain-that-does-not-exist.com",  # Should fail
        "https://httpbin.org/status/500",  # Should return 500 error
    ]
    
    print("Testing error handling with various URLs...")
    
    results = []
    for i, url in enumerate(test_urls, 1):
        print(f"\n🔍 Testing URL {i}/{len(test_urls)}:")
        result = safe_extraction_with_retry(url, max_retries=2)
        results.append(result)
    
    # Summary
    print(f"\n📊 Error Handling Test Results:")
    successful = sum(1 for r in results if r['extraction_successful'])
    failed = len(results) - successful
    
    print(f"   Successful extractions: {successful}/{len(results)}")
    print(f"   Failed extractions: {failed}/{len(results)}")
    
    print(f"\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        status = "✅ SUCCESS" if result['extraction_successful'] else "❌ FAILED"
        print(f"   {i}. {status}")
        print(f"      URL: {result['url']}")
        if not result['extraction_successful']:
            print(f"      Error: {result.get('error', 'Unknown error')}")


def main_examples():
    """
    Run all basic usage examples
    """
    print("🚀 PUBSCRAPE BASIC USAGE EXAMPLES")
    print("This script demonstrates common usage patterns for the PubScrape system.")
    print("\nNote: These examples require an OPENAI_API_KEY environment variable.")
    
    # Check if API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("\n❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key before running examples:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    print("\n✅ OpenAI API key detected")
    
    # Run examples
    examples = [
        ("Configuration Usage", example_3_configuration_usage),
        ("Browser Management", example_4_browser_management),
        ("Custom Search Query", example_2_custom_search_query),
        ("Batch Processing", example_5_batch_processing),
        ("Error Handling", example_6_error_handling),
        # Note: Commented out the full scraper to avoid making actual requests in demo
        # ("Simple Doctor Search", example_1_simple_doctor_search),
    ]
    
    print(f"\nRunning {len(examples)} examples...")
    
    for i, (name, example_func) in enumerate(examples, 1):
        try:
            print(f"\n{'='*80}")
            print(f"RUNNING EXAMPLE {i}/{len(examples)}: {name}")
            print('='*80)
            
            example_func()
            
            print(f"\n✅ Example {i} completed successfully!")
            
            if i < len(examples):
                print("\n⏳ Waiting 2 seconds before next example...")
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Examples interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Example {i} failed: {e}")
            print("Continuing with next example...")
    
    print(f"\n🎉 All examples completed!")
    print("\nFor more advanced usage, see examples/advanced_config.py")


if __name__ == "__main__":
    main_examples()