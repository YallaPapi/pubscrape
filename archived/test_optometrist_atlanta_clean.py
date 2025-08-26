#!/usr/bin/env python3
"""
Test Real Optometrist Lead Generation in Atlanta
This will test our system with actual Bing searches for optometrists in Atlanta.
"""

import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_optometrist_atlanta():
    """Test optometrist lead generation in Atlanta"""
    print("TESTING OPTOMETRIST LEAD GENERATION - ATLANTA")
    print("=" * 60)
    print("Target: Find optometrists in Atlanta with email addresses")
    print("Approach: Real Bing searches -> URL extraction -> Email extraction")
    print()
    
    try:
        # Step 1: Import and test the BingSearchTool
        print("Step 1: Testing Bing Search Tool...")
        from agents.tools.bing_search_tool import BingSearchTool
        
        # Create search queries focused on Atlanta optometrists
        optometrist_queries = [
            "optometrist atlanta contact email",
            "eye doctor atlanta contact information", 
            "atlanta optometry practice email",
            "atlanta eye care contact",
            "optometrist atlanta ga email address"
        ]
        
        all_results = []
        
        # Test with first 2 queries to start
        for i, query in enumerate(optometrist_queries[:2]):
            print(f"\n  Query {i+1}: {query}")
            print(f"  Searching Bing...")
            
            # Create BingSearchTool instance
            search_tool = BingSearchTool(
                query=query,
                max_pages=2,  # Get 2 pages for comprehensive coverage
                session_id=f"atlanta_optometrist_{i}",
                store_html=True
            )
            
            # Execute search
            start_time = time.time()
            result = search_tool.run()
            search_time = time.time() - start_time
            
            print(f"    Search completed in {search_time:.2f}s")
            print(f"    Success: {result.get('success', False)}")
            print(f"    Pages retrieved: {result.get('pages_retrieved', 0)}")
            
            if result.get('success'):
                html_files = result.get('html_files', [])
                print(f"    HTML files saved: {len(html_files)}")
                for html_file in html_files:
                    if html_file and os.path.exists(html_file):
                        file_size = os.path.getsize(html_file) / 1024
                        print(f"      - {Path(html_file).name} ({file_size:.1f} KB)")
                
                all_results.append(result)
            else:
                errors = result.get('summary', {}).get('errors_encountered', [])
                print(f"    Errors: {errors}")
            
            # Respectful delay between searches
            time.sleep(2)
        
        print(f"\nBing search tests completed: {len(all_results)} successful")
        
        if not all_results:
            print("No successful searches - cannot continue to URL extraction")
            return False
        
        # Step 2: Test URL extraction from HTML
        print("\nStep 2: Testing URL extraction from SERP HTML...")
        from agents.tools.serp_parse_tool import SerpParseTool
        
        all_urls = []
        
        for i, result in enumerate(all_results):
            html_files = result.get('html_files', [])
            
            for html_file in html_files:
                if html_file and os.path.exists(html_file):
                    print(f"  Parsing {Path(html_file).name}...")
                    
                    try:
                        # Read HTML content
                        with open(html_file, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        
                        # Create SERP parser
                        parser = SerpParseTool(
                            html_content=html_content,
                            query=optometrist_queries[i] if i < len(optometrist_queries) else "optometrist atlanta",
                            page_number=1
                        )
                        
                        # Parse URLs
                        parsed_result = parser.run()
                        urls = parsed_result.get('results', [])
                        
                        print(f"    URLs found: {len(urls)}")
                        
                        # Filter for relevant optometry URLs
                        optometry_urls = []
                        for url_data in urls:
                            url = url_data.get('url', '').lower()
                            title = url_data.get('title', '').lower()
                            
                            # Look for optometry-related keywords
                            optometry_keywords = ['optometr', 'eye', 'vision', 'sight', 'contact', 'glasses']
                            is_relevant = any(keyword in url or keyword in title for keyword in optometry_keywords)
                            
                            if is_relevant:
                                optometry_urls.append(url_data)
                        
                        print(f"    Optometry-relevant URLs: {len(optometry_urls)}")
                        all_urls.extend(optometry_urls)
                        
                        # Show some examples
                        for j, url_data in enumerate(optometry_urls[:3]):
                            print(f"      {j+1}. {url_data.get('title', 'No title')[:60]}...")
                            print(f"         {url_data.get('url', '')}")
                    
                    except Exception as e:
                        print(f"    Error parsing {html_file}: {str(e)}")
        
        print(f"\nURL extraction completed: {len(all_urls)} optometry URLs found")
        
        if not all_urls:
            print("No optometry URLs found - cannot continue to email extraction")
            return False
        
        # Step 3: Test email extraction from top URLs
        print("\nStep 3: Testing email extraction from optometry websites...")
        from agents.tools.email_extraction_tool import EmailExtractionTool
        
        email_tool = EmailExtractionTool()
        leads_found = []
        
        # Test with first 5 URLs to be respectful
        test_urls = all_urls[:5]
        
        for i, url_data in enumerate(test_urls):
            url = url_data.get('url', '')
            title = url_data.get('title', 'Unknown Practice')
            
            print(f"  {i+1}/5: {title[:50]}...")
            print(f"         {url}")
            
            try:
                # Download webpage with proper headers
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    # Extract domain for email context
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc.replace('www.', '')
                    
                    # Use EmailExtractionTool
                    extraction_result = email_tool.run(
                        html_content=response.text,
                        url=url,
                        domain=domain
                    )
                    
                    emails = extraction_result.get('emails', [])
                    
                    if emails:
                        print(f"    FOUND {len(emails)} email(s):")
                        for email_data in emails:
                            email = email_data.get('email', '')
                            confidence = email_data.get('confidence', 0)
                            context = email_data.get('context', 'Unknown')
                            print(f"      - {email} (confidence: {confidence:.2f}, context: {context})")
                        
                        # Create lead entries
                        for email_data in emails:
                            lead = {
                                'business_name': title,
                                'website': url,
                                'email': email_data.get('email', ''),
                                'confidence': email_data.get('confidence', 0),
                                'context': email_data.get('context', ''),
                                'location': 'Atlanta, GA',
                                'specialty': 'Optometry',
                                'source': 'Real Bing Search + Website Extraction',
                                'extraction_date': time.strftime('%Y-%m-%d'),
                                'domain': domain
                            }
                            leads_found.append(lead)
                    else:
                        print(f"    No emails found")
                
                else:
                    print(f"    HTTP {response.status_code}")
            
            except Exception as e:
                print(f"    Error: {str(e)}")
            
            # Be respectful - delay between requests
            time.sleep(3)
        
        print(f"\nEmail extraction completed: {len(leads_found)} leads with emails")
        
        # Step 4: Save results
        if leads_found:
            print("\nStep 4: Saving results...")
            
            import csv
            os.makedirs('out', exist_ok=True)
            filename = f"out/atlanta_optometrists_{int(time.time())}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = leads_found[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for lead in leads_found:
                    writer.writerow(lead)
            
            print(f"  Saved {len(leads_found)} leads to: {filename}")
            
            # Show results summary
            print("\nATLANTA OPTOMETRIST LEADS FOUND:")
            print("-" * 80)
            for i, lead in enumerate(leads_found[:10]):  # Show first 10
                conf = lead['confidence']
                print(f"{i+1:2d}. {lead['business_name'][:40]:40s} | {lead['email']:35s} | {conf:.2f}")
            
            if len(leads_found) > 10:
                print(f"    ... and {len(leads_found) - 10} more leads")
            
            print(f"\nSUCCESS: Found {len(leads_found)} REAL optometrist leads in Atlanta!")
            return True
        
        else:
            print("\nNo leads with emails found")
            return False
    
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optometrist_atlanta()
    print("\n" + "="*60)
    if success:
        print("OPTOMETRIST ATLANTA TEST: SUCCESS")
        print("   System is working for real lead generation!")
    else:
        print("OPTOMETRIST ATLANTA TEST: FAILED")
        print("   Need to investigate issues")
    
    sys.exit(0 if success else 1)