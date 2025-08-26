#!/usr/bin/env python3
"""
Actually USE the agents I built to get real leads
"""
import sys
import os

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_real_pipeline():
    """Use the actual agents to get real leads"""
    print("🚀 RUNNING REAL PIPELINE WITH ACTUAL AGENTS")
    print("=" * 60)
    
    try:
        # Step 1: Create proper search queries (skip broken template system)
        print("Step 1: Creating search queries...")
        
        queries = [
            "restaurant New York contact email",
            "restaurant Los Angeles contact information", 
            "restaurant Chicago owner email",
            "restaurant Houston manager contact",
            "restaurant Phoenix contact email",
            "restaurant Seattle restaurant email",
            "restaurant Miami owner contact",
            "restaurant Denver contact information",
            "restaurant Atlanta restaurant contact",
            "restaurant Boston manager email"
        ]
        
        print(f"✓ Created {len(queries)} search queries")
        for i, q in enumerate(queries[:5]):
            print(f"  {i+1}. {q}")
        if len(queries) > 5:
            print(f"  ... and {len(queries)-5} more")
        
        # Step 2: Use BingNavigator agent to get real SERP data  
        print(f"\\nStep 2: Searching Bing for real results...")
        from agents.tools.bing_search_tool import BingSearchTool
        
        all_results = []
        
        for i, query in enumerate(queries[:5]):  # Test with first 5 queries
            print(f"  Searching: {query[:60]}...")
            try:
                # Create tool instance with query parameters
                bing_tool = BingSearchTool(
                    query=query,
                    max_pages=2,  # Keep it reasonable
                    session_id=f"pipeline_session_{i}"
                )
                
                # Run the search
                result = bing_tool.run()
                
                if result.get('success'):
                    all_results.append(result)
                    print(f"    ✓ Success: Got HTML content")
                else:
                    print(f"    ✗ Failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"    ✗ Exception: {str(e)}")
        
        print(f"✓ Completed {len(all_results)} successful searches")
        
        if not all_results:
            print("❌ No search results obtained. Cannot continue.")
            return []
        
        # Step 3: Use SerpParser agent to extract URLs
        print(f"\\nStep 3: Parsing SERP results for business URLs...")
        from agents.tools.serp_parse_tool import SerpParseTool
        
        all_urls = []
        
        for i, result in enumerate(all_results):
            html_files = result.get('html_files', [])
            if html_files:
                # Read the HTML file
                html_file = html_files[0]  # Use first HTML file
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    print(f"  Parsing HTML from search {i+1} ({len(html_content)} chars)...")
                    
                    # Create SerpParseTool with HTML content
                    serp_tool = SerpParseTool(
                        html_content=html_content,
                        query=queries[i] if i < len(queries) else "restaurant search",
                        position_offset=0
                    )
                    
                    # Run the parsing
                    parsed = serp_tool.run()
                    
                    results = parsed.get('results', [])
                    all_urls.extend(results)
                    print(f"    ✓ Found {len(results)} URLs")
                    
                except Exception as e:
                    print(f"    ✗ Failed to parse: {str(e)}")
        
        print(f"✓ Total URLs extracted: {len(all_urls)}")
        
        if not all_urls:
            print("❌ No URLs extracted. Cannot continue.")
            return []
        
        # Step 4: Use DomainClassifier to filter business URLs
        print(f"\\nStep 4: Filtering for business websites...")
        from agents.domain_classifier_agent import DomainClassifier
        
        classifier = DomainClassifier()
        business_urls = []
        
        for url_data in all_urls[:20]:  # Process first 20 URLs
            url = url_data.get('url', '')
            if url:
                # Extract domain
                from urllib.parse import urlparse
                try:
                    domain = urlparse(url).netloc.replace('www.', '')
                    
                    # Add to classifier
                    result = classifier.add_domain(domain, context={
                        'source_url': url,
                        'title': url_data.get('title', ''),
                        'snippet': url_data.get('snippet', '')
                    })
                    
                    if result:
                        business_urls.append(url_data)
                        print(f"  ✓ Business: {url_data.get('title', 'No title')[:50]}...")
                    else:
                        print(f"  ✗ Filtered: {url_data.get('title', 'No title')[:50]}...")
                        
                except Exception as e:
                    print(f"  ✗ Error processing {url}: {str(e)}")
        
        print(f"✓ Business URLs identified: {len(business_urls)}")
        
        if not business_urls:
            print("❌ No business URLs identified. Cannot continue.")
            return []
        
        # Step 5: Use EmailExtractor to get contact info
        print(f"\\nStep 5: Extracting contact information from websites...")
        from agents.email_extractor_agent import EmailExtractorAgent
        from agents.tools.email_extraction_tool import EmailExtractionTool
        
        email_tool = EmailExtractionTool()
        leads = []
        
        for i, url_data in enumerate(business_urls[:10]):  # Process first 10 business URLs
            url = url_data.get('url', '')
            print(f"  Processing {i+1}/10: {url[:60]}...")
            
            try:
                # Download the webpage
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # Extract domain
                    domain = urlparse(url).netloc.replace('www.', '')
                    
                    # Use EmailExtractionTool
                    result = email_tool.run(
                        html_content=response.text,
                        url=url,
                        domain=domain
                    )
                    
                    emails = result.get('emails', [])
                    if emails:
                        # Create leads
                        for email_data in emails[:2]:  # Max 2 emails per site
                            lead = {
                                'business_name': url_data.get('title', domain.split('.')[0].title()),
                                'website': url,
                                'email': email_data.get('email', ''),
                                'quality_score': email_data.get('confidence', 0.5),
                                'source': 'Real website extraction',
                                'extraction_date': '2025-08-21',
                                'contact_type': email_data.get('context', 'Unknown'),
                                'domain': domain
                            }
                            leads.append(lead)
                        
                        print(f"    ✓ Found {len(emails)} emails: {', '.join([e.get('email', '') for e in emails])}")
                    else:
                        print(f"    ⚠️ No emails found")
                else:
                    print(f"    ✗ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
            
            # Be polite
            import time
            import random
            time.sleep(random.uniform(1, 2))
        
        print(f"✓ Total real leads extracted: {len(leads)}")
        return leads
        
    except Exception as e:
        print(f"❌ Pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def save_real_leads(leads):
    """Save the real leads"""
    if not leads:
        print("❌ No leads to save")
        return None
    
    print(f"\\n💾 SAVING {len(leads)} REAL LEADS")
    
    import csv
    os.makedirs('out', exist_ok=True)
    filename = 'out/actual_real_leads.csv'
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = leads[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)
    
    print(f"✅ Saved to: {filename}")
    
    # Show results
    print("\\n📋 REAL LEADS EXTRACTED:")
    for i, lead in enumerate(leads):
        print(f"  {i+1:2d}. {lead['business_name'][:35]:35s} | {lead['email']:40s} | Score: {lead['quality_score']:.2f}")
    
    return filename

def main():
    """Run the real pipeline using actual agents"""
    print("🎯 USING THE ACTUAL AGENT SYSTEM I BUILT")
    print()
    
    leads = run_real_pipeline()
    
    if leads:
        filename = save_real_leads(leads)
        print(f"\\n🎉 SUCCESS: Generated {len(leads)} REAL leads using the agent system!")
        print(f"📁 File: {filename}")
        return True
    else:
        print("\\n❌ Failed to generate real leads")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)