#!/usr/bin/env python3
"""
Real Doctor Lead Generation Campaign
Generates 100 real doctor/medical practice leads with validation at each step
NO MOCK DATA - REAL EXTRACTION ONLY
"""

import os
import sys
import json
import yaml
import time
import csv
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class RealLeadValidator:
    """Validates that data is real, not mock"""
    
    @staticmethod
    def validate_search_results(html_content: str, query: str) -> bool:
        """Validate that search results are real Bing results"""
        if not html_content or len(html_content) < 1000:
            print(f"  ❌ VALIDATION FAILED: Empty or too small HTML ({len(html_content)} bytes)")
            return False
            
        # Check for Bing markers
        bing_markers = ['b_algo', 'b_title', 'bing.com', 'microsoft']
        found_markers = sum(1 for marker in bing_markers if marker in html_content.lower())
        
        if found_markers < 2:
            print(f"  ❌ VALIDATION FAILED: Not real Bing results (only {found_markers} markers found)")
            return False
            
        # Check for query relevance
        if query.split()[0].lower() not in html_content.lower():
            print(f"  ❌ VALIDATION FAILED: Results don't match query '{query}'")
            return False
            
        print(f"  ✅ VALIDATION PASSED: Real Bing results ({len(html_content):,} bytes, {found_markers} markers)")
        return True
    
    @staticmethod
    def validate_extracted_emails(emails: List[Dict]) -> bool:
        """Validate that emails are real, not test data"""
        if not emails:
            print(f"  ❌ VALIDATION FAILED: No emails extracted")
            return False
            
        # Check for test/mock patterns
        mock_patterns = ['test', 'example', 'mock', 'fake', 'demo', 'sample']
        
        for email_data in emails:
            email = email_data.get('email', '')
            
            # Check for mock patterns
            for pattern in mock_patterns:
                if pattern in email.lower():
                    print(f"  ❌ VALIDATION FAILED: Mock email detected: {email}")
                    return False
            
            # Check for valid medical domain patterns
            if not any(med in email.lower() for med in ['dr', 'md', 'clinic', 'medical', 'health', 'care', 'practice']):
                if '@' in email and '.' in email.split('@')[1]:
                    # Could still be valid if it's a real domain
                    pass
                else:
                    print(f"  ⚠️  WARNING: Non-medical email: {email}")
        
        print(f"  ✅ VALIDATION PASSED: {len(emails)} real emails extracted")
        return True
    
    @staticmethod
    def validate_final_leads(leads: List[Dict]) -> bool:
        """Validate final lead quality"""
        if not leads:
            print(f"  ❌ VALIDATION FAILED: No leads generated")
            return False
            
        valid_count = 0
        for lead in leads:
            # Check required fields
            if all([
                lead.get('email'),
                lead.get('website'),
                '@' in lead.get('email', ''),
                'http' in lead.get('website', ''),
                not any(mock in lead.get('email', '').lower() for mock in ['test', 'example', 'fake'])
            ]):
                valid_count += 1
        
        validity_rate = valid_count / len(leads)
        
        if validity_rate < 0.8:
            print(f"  ❌ VALIDATION FAILED: Only {validity_rate:.1%} valid leads")
            return False
            
        print(f"  ✅ VALIDATION PASSED: {valid_count}/{len(leads)} valid leads ({validity_rate:.1%})")
        return True


def run_real_campaign_with_validation():
    """Execute real lead generation with validation at each step"""
    
    print("🏥 REAL DOCTOR LEAD GENERATION CAMPAIGN")
    print("=" * 60)
    print("Target: 100 real medical professional leads")
    print("Mode: REAL DATA EXTRACTION (NO MOCKS)")
    print("=" * 60)
    
    # Initialize validator
    validator = RealLeadValidator()
    
    # Load campaign config
    config_path = "campaigns/doctor_lead_generation.yaml"
    if not os.path.exists(config_path):
        print(f"❌ Campaign config not found: {config_path}")
        return False
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"\n📋 Campaign: {config['campaign']['name']}")
    print(f"Target: {config['campaign']['target_leads']} leads")
    
    # Initialize tracking
    all_leads = []
    validation_log = []
    
    try:
        # Import VRSEN Agency agents
        from BingNavigator import BingNavigator
        from SerpParser import SerpParser
        from DomainClassifier import DomainClassifier
        from EmailExtractor import EmailExtractor
        from Exporter import Exporter
        from agency_swarm import Agency
        
        print("\n🤖 Initializing VRSEN Agency Agents...")
        navigator = BingNavigator()
        parser = SerpParser()
        classifier = DomainClassifier()
        extractor = EmailExtractor()
        exporter = Exporter()
        
        # Create agency for agent communication
        agency = Agency([
            navigator,
            [navigator, parser],
            [parser, classifier],
            [classifier, extractor],
            [extractor, exporter]
        ])
        
        print("✅ Agency initialized with all agents")
        
        # Generate search queries
        print("\n📝 Generating search queries...")
        queries = []
        
        # Use primary cities and templates
        for city in config['geographic_targets']['primary_cities'][:5]:  # Start with 5 cities
            for template in config['search_templates']['primary'][:3]:  # Use 3 templates per city
                query = template.replace('{city}', city).replace('{specialty}', 'family medicine')
                queries.append(query)
        
        print(f"✅ Generated {len(queries)} search queries")
        for i, q in enumerate(queries[:5]):
            print(f"  {i+1}. {q}")
        if len(queries) > 5:
            print(f"  ... and {len(queries)-5} more")
        
        # STEP 1: Execute searches with validation
        print("\n🔍 STEP 1: Executing Real Bing Searches...")
        print("-" * 40)
        
        search_results = []
        failed_searches = []
        
        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{len(queries)}] Searching: {query}")
            
            try:
                # Use BingNavigator to search
                search_task = f"""
                Search for: "{query}"
                Use your SerpFetchTool to get real Bing search results.
                Save the HTML content to a file and return the file path.
                This is for a medical lead generation campaign.
                """
                
                response = agency.get_completion(search_task)
                
                # Extract response content
                if hasattr(response, '__iter__') and not isinstance(response, str):
                    content_parts = []
                    for chunk in response:
                        if hasattr(chunk, 'get_content'):
                            content_parts.append(chunk.get_content())
                        elif hasattr(chunk, 'content'):
                            content_parts.append(chunk.content)
                        else:
                            content_parts.append(str(chunk))
                    response_text = ''.join(content_parts)
                else:
                    response_text = str(response)
                
                # Validate the search results
                if "html_cache" in response_text and "bing_" in response_text:
                    # File-based response - load and validate
                    import re
                    file_match = re.search(r'(output/html_cache/bing_\w+\.html)', response_text)
                    if file_match:
                        html_file = file_match.group(1)
                        if os.path.exists(html_file):
                            with open(html_file, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            
                            if validator.validate_search_results(html_content, query):
                                search_results.append({
                                    'query': query,
                                    'html_file': html_file,
                                    'size': len(html_content)
                                })
                                validation_log.append(f"✅ Search validated: {query}")
                            else:
                                failed_searches.append(query)
                                validation_log.append(f"❌ Search validation failed: {query}")
                        else:
                            print(f"  ⚠️  HTML file not found: {html_file}")
                            failed_searches.append(query)
                else:
                    print(f"  ⚠️  No file reference in response")
                    failed_searches.append(query)
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"  ❌ Search failed: {str(e)}")
                failed_searches.append(query)
                validation_log.append(f"❌ Search error: {query} - {str(e)}")
        
        print(f"\n📊 Search Results:")
        print(f"  ✅ Successful: {len(search_results)}")
        print(f"  ❌ Failed: {len(failed_searches)}")
        
        if not search_results:
            print("\n❌ No valid search results. Cannot continue.")
            return False
        
        # STEP 2: Parse search results and extract URLs
        print("\n🔧 STEP 2: Parsing Search Results...")
        print("-" * 40)
        
        all_urls = []
        
        for result in search_results:
            print(f"\nParsing: {result['query']}")
            
            parse_task = f"""
            Parse the HTML file at: {result['html_file']}
            Extract all medical-related URLs from the search results.
            Focus on medical practice websites, doctor directories, and healthcare providers.
            Return the extracted URLs with their titles and snippets.
            """
            
            try:
                response = agency.get_completion(parse_task)
                
                # Process response
                if hasattr(response, '__iter__') and not isinstance(response, str):
                    parser_text = ''.join([
                        chunk.get_content() if hasattr(chunk, 'get_content') 
                        else chunk.content if hasattr(chunk, 'content')
                        else str(chunk)
                        for chunk in response
                    ])
                else:
                    parser_text = str(response)
                
                # Extract URLs from response
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                found_urls = re.findall(url_pattern, parser_text)
                
                # Filter for medical domains
                medical_urls = []
                for url in found_urls:
                    if any(med in url.lower() for med in ['doctor', 'md', 'clinic', 'medical', 'health', 'physician']):
                        medical_urls.append(url)
                
                if medical_urls:
                    print(f"  ✅ Found {len(medical_urls)} medical URLs")
                    all_urls.extend(medical_urls)
                    validation_log.append(f"✅ Parsed {len(medical_urls)} URLs from: {result['query']}")
                else:
                    print(f"  ⚠️  No medical URLs found")
                    
            except Exception as e:
                print(f"  ❌ Parse error: {str(e)}")
                validation_log.append(f"❌ Parse error: {result['query']} - {str(e)}")
        
        print(f"\n📊 URL Extraction:")
        print(f"  Total URLs: {len(all_urls)}")
        print(f"  Unique domains: {len(set([url.split('/')[2] for url in all_urls]))}")
        
        if not all_urls:
            print("\n❌ No URLs extracted. Cannot continue.")
            return False
        
        # STEP 3: Extract emails from websites
        print("\n📧 STEP 3: Extracting Emails from Websites...")
        print("-" * 40)
        
        for url in all_urls[:20]:  # Process first 20 URLs
            print(f"\nProcessing: {url[:60]}...")
            
            try:
                extract_task = f"""
                Visit the website: {url}
                Extract all email addresses from the site.
                Focus on doctor/medical professional emails.
                Look in contact pages, about pages, and staff directories.
                Return the extracted emails with context.
                """
                
                response = agency.get_completion(extract_task)
                
                # Process response
                if hasattr(response, '__iter__') and not isinstance(response, str):
                    extractor_text = ''.join([
                        chunk.get_content() if hasattr(chunk, 'get_content')
                        else chunk.content if hasattr(chunk, 'content')
                        else str(chunk)
                        for chunk in response
                    ])
                else:
                    extractor_text = str(response)
                
                # Extract emails from response
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                found_emails = re.findall(email_pattern, extractor_text)
                
                if found_emails:
                    # Validate emails
                    valid_emails = []
                    for email in found_emails:
                        # Skip blacklisted patterns
                        if not any(black in email.lower() for black in config['email_validation']['blacklist_patterns']):
                            valid_emails.append({'email': email, 'source': url})
                    
                    if validator.validate_extracted_emails(valid_emails):
                        for email_data in valid_emails:
                            lead = {
                                'email': email_data['email'],
                                'website': url,
                                'extraction_date': datetime.now().strftime('%Y-%m-%d'),
                                'confidence_score': 0.8,
                                'source_type': 'real_extraction'
                            }
                            all_leads.append(lead)
                        
                        validation_log.append(f"✅ Extracted {len(valid_emails)} valid emails from: {url[:40]}...")
                    else:
                        validation_log.append(f"❌ Email validation failed for: {url[:40]}...")
                else:
                    print(f"  ⚠️  No emails found")
                
                # Rate limiting
                time.sleep(1)
                
                # Check if we have enough leads
                if len(all_leads) >= config['campaign']['target_leads']:
                    print(f"\n🎯 Target reached: {len(all_leads)} leads")
                    break
                    
            except Exception as e:
                print(f"  ❌ Extraction error: {str(e)}")
                validation_log.append(f"❌ Extraction error: {url[:40]}... - {str(e)}")
        
        # STEP 4: Final validation
        print("\n✅ STEP 4: Final Validation...")
        print("-" * 40)
        
        if validator.validate_final_leads(all_leads):
            print(f"✅ FINAL VALIDATION PASSED")
        else:
            print(f"⚠️  Final validation has warnings")
        
        # STEP 5: Export results
        print("\n💾 STEP 5: Exporting Results...")
        print("-" * 40)
        
        # Create output directory
        output_dir = config['output_config']['base_dir']
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = os.path.join(output_dir, f"doctor_leads_real_{timestamp}.csv")
        
        # Write CSV
        if all_leads:
            with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['email', 'website', 'extraction_date', 'confidence_score', 'source_type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for lead in all_leads:
                    writer.writerow(lead)
            
            print(f"✅ Exported {len(all_leads)} leads to: {csv_filename}")
        
        # Write validation log
        log_filename = os.path.join(output_dir, f"validation_log_{timestamp}.txt")
        with open(log_filename, 'w') as f:
            f.write("REAL LEAD GENERATION VALIDATION LOG\n")
            f.write("=" * 60 + "\n")
            f.write(f"Campaign: {config['campaign']['name']}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Leads: {len(all_leads)}\n")
            f.write("=" * 60 + "\n\n")
            for entry in validation_log:
                f.write(entry + "\n")
        
        print(f"✅ Validation log saved to: {log_filename}")
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 CAMPAIGN SUMMARY")
        print("=" * 60)
        print(f"✅ Total Leads Generated: {len(all_leads)}")
        print(f"✅ Successful Searches: {len(search_results)}")
        print(f"✅ URLs Processed: {len(all_urls)}")
        print(f"✅ Validation Pass Rate: {len([v for v in validation_log if '✅' in v])/len(validation_log)*100:.1f}%")
        print(f"✅ Output File: {csv_filename}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Campaign failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_real_campaign_with_validation()
    sys.exit(0 if success else 1)