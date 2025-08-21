#!/usr/bin/env python3
"""
Direct Lead Generation - Force VRSEN Pipeline Execution
Bypasses planning phase and directly executes the tools
"""

import os
from dotenv import load_dotenv
from agency_swarm import Agency

# Load environment variables
load_dotenv()

def run_direct_pipeline():
    """Run the VRSEN pipeline with direct tool execution"""
    
    print("🏥 DIRECT VRSEN PIPELINE EXECUTION")
    print("=" * 50)
    
    try:
        # Import agents
        from BingNavigator import BingNavigator
        from SerpParser import SerpParser
        from DomainClassifier import DomainClassifier
        from EmailExtractor import EmailExtractor
        from Exporter import Exporter
        
        print("📋 Creating agents...")
        navigator = BingNavigator()
        parser = SerpParser()
        classifier = DomainClassifier()
        extractor = EmailExtractor()
        exporter = Exporter()
        
        # Create minimal agency for communication
        agency = Agency([
            navigator,
            [navigator, parser],
        ])
        
        print("✅ Agency created for BingNavigator → SerpParser")
        
        # Step 1: Direct search execution
        print("\n🔍 STEP 1: Executing direct searches...")
        
        search_queries = [
            "doctor contact information New York",
            "medical practice email directory California", 
            "physician contact details Chicago",
            "family doctor email Houston",
            "cardiologist contact information Phoenix"
        ]
        
        for i, query in enumerate(search_queries):
            print(f"\n📤 Search {i+1}: {query}")
            
            search_task = f"""
            Use your SerpFetchTool to search for "{query}".
            Execute the search with these parameters:
            - query: "{query}"
            - page: 1
            - timeout_s: 20
            - use_stealth: true
            
            Return the HTML content results for processing.
            """
            
            # Use agency to communicate with navigator
            response = agency.get_completion(search_task)
            
            # Handle response
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
            
            print(f"📥 Response length: {len(response_text)} chars")
            
            # Check if we got file references (new pipeline)
            if "html_cache" in response_text or "bing_" in response_text:
                print("✅ File-based response detected!")
            elif len(response_text) > 10000:
                print("⚠️  Large HTML response (may hit 512KB limit)")
            else:
                print(f"📊 Compact response: {response_text[:200]}...")
        
        print("\n🎯 SEARCHES COMPLETED!")
        
        # Step 2: Check for HTML cache files
        print("\n📁 STEP 2: Checking for HTML cache files...")
        
        html_cache_dir = "output/html_cache"
        if os.path.exists(html_cache_dir):
            html_files = [f for f in os.listdir(html_cache_dir) if f.endswith('.html')]
            print(f"✅ Found {len(html_files)} HTML files:")
            for html_file in html_files[:5]:  # Show first 5
                file_path = os.path.join(html_cache_dir, html_file)
                file_size = os.path.getsize(file_path)
                print(f"  - {html_file}: {file_size:,} bytes")
        else:
            print("⚠️  No HTML cache directory found")
        
        # Step 3: Test SerpParser if we have HTML files
        if os.path.exists(html_cache_dir) and html_files:
            print("\n🔧 STEP 3: Testing SerpParser...")
            
            parser_task = f"""
            Process the HTML files in the html_cache directory.
            Extract relevant URLs from the medical search results.
            Focus on:
            - Medical practice websites
            - Doctor directory listings
            - Hospital physician pages
            - Contact information pages
            
            Return a clean list of prioritized URLs for further processing.
            """
            
            # Use agency communication for proper handoff
            full_task = f"""
            BingNavigator has completed searches and saved HTML files.
            
            SerpParser: Please process the saved HTML files and extract medical-relevant URLs.
            
            Task: {parser_task}
            """
            
            parser_response = agency.get_completion(full_task)
            
            # Process parser response
            if hasattr(parser_response, '__iter__') and not isinstance(parser_response, str):
                parser_content = []
                for chunk in parser_response:
                    if hasattr(chunk, 'get_content'):
                        parser_content.append(chunk.get_content())
                    elif hasattr(chunk, 'content'):
                        parser_content.append(chunk.content)
                    else:
                        parser_content.append(str(chunk))
                parser_text = ''.join(parser_content)
            else:
                parser_text = str(parser_response)
            
            print(f"📥 SerpParser response: {len(parser_text)} chars")
            print(f"📊 Sample: {parser_text[:300]}...")
            
            if "http" in parser_text or "url" in parser_text.lower():
                print("✅ URL extraction successful!")
            else:
                print("⚠️  No URLs detected in response")
        
        print(f"\n🎉 DIRECT PIPELINE TEST COMPLETED!")
        print(f"🔍 Searches executed: {len(search_queries)}")
        print(f"📁 HTML files saved: {len(html_files) if 'html_files' in locals() else 0}")
        print(f"🔧 SerpParser tested: {'✅' if 'parser_text' in locals() else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_direct_pipeline()