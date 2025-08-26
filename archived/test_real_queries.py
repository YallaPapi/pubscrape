#!/usr/bin/env python3
"""
Test script to generate real search queries and test the Bing searcher
"""
import sys
import os
sys.path.append('src')

# Create some real, concrete search queries for testing
test_queries = [
    "restaurant New York contact email",
    "restaurant Los Angeles owner email",
    "cafe Chicago contact information",
    "restaurant Houston manager phone",
    "restaurant Phoenix owner contact",
    "restaurant Philadelphia contact",
    "restaurant San Antonio email",
    "restaurant Dallas contact information",
    "restaurant Miami owner email",
    "restaurant Seattle contact"
]

def test_query_generation():
    """Test that we can generate proper queries"""
    print("=== TESTING QUERY GENERATION ===")
    
    # Ensure out directory exists
    os.makedirs('out', exist_ok=True)
    
    # Write test queries to file
    with open('out/real_test_queries.txt', 'w') as f:
        for query in test_queries:
            f.write(f"{query}\n")
    
    print(f"✓ Generated {len(test_queries)} test queries")
    print("Sample queries:")
    for i, query in enumerate(test_queries[:3]):
        print(f"  {i+1}. {query}")
    print(f"  ... and {len(test_queries)-3} more")
    return test_queries

def test_bing_searcher():
    """Test the Bing searcher with real queries"""
    print("\n=== TESTING BING SEARCHER ===")
    
    try:
        from infra.bing_searcher import BingSearcher
        print("✓ Imported BingSearcher successfully")
        
        searcher = BingSearcher()
        print("✓ Created BingSearcher instance")
        
        # Test with first 3 queries
        test_count = 3
        results = []
        
        for i, query in enumerate(test_queries[:test_count]):
            print(f"\nTesting search {i+1}: {query}")
            try:
                result = searcher.search(query, session_id=f"test_session_{i}")
                
                if result and result.get('success'):
                    html_len = len(result.get('raw_html', ''))
                    results.append(result)
                    print(f"  ✓ SUCCESS: Got {html_len} chars of HTML")
                else:
                    error = result.get('error', 'Unknown error') if result else 'No result returned'
                    print(f"  ✗ FAILED: {error}")
                    
            except Exception as e:
                print(f"  ✗ EXCEPTION: {str(e)}")
        
        print(f"\n✓ Completed {len(results)}/{test_count} successful searches")
        return results
        
    except Exception as e:
        print(f"✗ FAILED to test Bing searcher: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_serp_parser(search_results):
    """Test the SERP parser with search results"""
    print("\n=== TESTING SERP PARSER ===")
    
    if not search_results:
        print("✗ No search results to parse")
        return []
    
    try:
        from agents.tools.serp_parse_tool import SerpParseTool
        print("✓ Imported SerpParseTool successfully")
        
        parser = SerpParseTool()
        print("✓ Created SerpParseTool instance")
        
        all_urls = []
        for i, result in enumerate(search_results):
            html_content = result.get('raw_html', '')
            if html_content:
                print(f"\nParsing search result {i+1} ({len(html_content)} chars)...")
                try:
                    parsed = parser.run(
                        html_content=html_content,
                        query=f"test_query_{i}",
                        position_offset=0
                    )
                    
                    urls_found = len(parsed.get('results', []))
                    all_urls.extend(parsed.get('results', []))
                    print(f"  ✓ SUCCESS: Found {urls_found} URLs")
                    
                    # Show first few URLs
                    for j, url_data in enumerate(parsed.get('results', [])[:2]):
                        print(f"    {j+1}. {url_data.get('url', 'No URL')}")
                        
                except Exception as e:
                    print(f"  ✗ FAILED: {str(e)}")
        
        print(f"\n✓ Total URLs extracted: {len(all_urls)}")
        return all_urls
        
    except Exception as e:
        print(f"✗ FAILED to test SERP parser: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Run the full test pipeline"""
    print("🚀 STARTING PIPELINE TEST")
    print("=" * 50)
    
    # Step 1: Generate queries
    queries = test_query_generation()
    
    # Step 2: Test searches
    search_results = test_bing_searcher()
    
    # Step 3: Test SERP parsing
    urls = test_serp_parser(search_results)
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 PIPELINE TEST SUMMARY")
    print(f"Queries generated: {len(queries)}")
    print(f"Searches completed: {len(search_results)}")
    print(f"URLs extracted: {len(urls)}")
    
    if len(urls) > 0:
        print("\n✓ PIPELINE IS WORKING! Ready to scale up for 100 leads")
        return True
    else:
        print("\n✗ PIPELINE NEEDS FIXES")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)