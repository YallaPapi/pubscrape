"""
Test Suite for SERP Parser System

Comprehensive tests for the SERP parsing and URL normalization system,
including unit tests for HTML parsing, URL normalization, and business filtering.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test imports
try:
    from src.agents.serp_parser_agent import SerpParserAgent
    from src.agents.tools.serp_parse_tool import SerpParseTool
    from src.agents.tools.url_normalize_tool import UrlNormalizeTool  
    from src.agents.tools.business_filter_tool import BusinessFilterTool
    print("✓ Successfully imported SERP parser components")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def create_mock_bing_html() -> str:
    """Create mock Bing SERP HTML for testing"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Bing Search Results</title>
</head>
<body>
    <div id="b_results">
        <div class="b_algo">
            <h2><a href="https://www.bing.com/ck/a?!&&p=123&u=aHR0cHM6Ly93d3cuZXhhbXBsZS1idXNpbmVzcy5jb20%3d">Example Business Services</a></h2>
            <div class="b_caption">
                <p>Professional business services company providing consulting and solutions.</p>
            </div>
        </div>
        
        <div class="b_algo">
            <h2><a href="https://www.testcompany.com/services?utm_source=bing&utm_campaign=search">Test Company</a></h2>
            <div class="b_caption">
                <p>Leading provider of business solutions and professional services.</p>
            </div>
        </div>
        
        <div class="b_algo">
            <h2><a href="https://facebook.com/somecompany">Company Facebook Page</a></h2>
            <div class="b_caption">
                <p>Official Facebook page for Some Company</p>
            </div>
        </div>
        
        <div class="b_algo">
            <h2><a href="https://www.yelp.com/biz/local-business">Yelp Review</a></h2>
            <div class="b_caption">
                <p>Reviews and ratings for Local Business on Yelp</p>
            </div>
        </div>
        
        <div class="b_algo">
            <h2><a href="https://manufacturing-corp.biz/contact">Manufacturing Corp</a></h2>
            <div class="b_caption">
                <p>Industrial manufacturing company specializing in commercial products.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""


def test_serp_parse_tool():
    """Test the SERP parsing tool"""
    print("\n=== Testing SERP Parse Tool ===")
    
    try:
        # Create mock HTML
        html_content = create_mock_bing_html()
        
        # Initialize the tool
        tool = SerpParseTool(
            html_content=html_content,
            query="business services consulting",
            page_number=1,
            selector_mode="adaptive"
        )
        
        # Run the parsing
        result = tool.run()
        
        # Verify results
        assert result["success"] == True, "Parsing should succeed"
        assert result["results_count"] > 0, "Should extract some results"
        assert len(result["results"]) >= 3, "Should extract at least 3 results"
        
        print(f"✓ Extracted {result['results_count']} results")
        print(f"✓ Processing time: {result['processing_time_seconds']:.2f}s")
        
        # Check that URLs were extracted
        urls_found = [r["url"] for r in result["results"]]
        print(f"✓ URLs extracted: {len(urls_found)}")
        for url in urls_found[:3]:  # Show first 3
            print(f"  - {url}")
        
        return result
        
    except Exception as e:
        print(f"✗ SERP Parse Tool test failed: {e}")
        return None


def test_url_normalize_tool():
    """Test the URL normalization tool"""
    print("\n=== Testing URL Normalize Tool ===")
    
    try:
        # Test URLs with various issues
        test_urls = [
            "https://www.bing.com/ck/a?!&&p=123&u=aHR0cHM6Ly93d3cuZXhhbXBsZS1idXNpbmVzcy5jb20%3d",
            "https://www.testcompany.com/services?utm_source=bing&utm_campaign=search&fbclid=123",
            "http://www.example.com/path//double-slash/",
            "https://www.facebook.com/somecompany",
            "https://manufacturing-corp.biz/contact#section1"
        ]
        
        # Initialize the tool
        tool = UrlNormalizeTool(
            urls=test_urls,
            remove_tracking=True,
            unwrap_redirects=True,
            normalize_protocol=True
        )
        
        # Run normalization
        result = tool.run()
        
        # Verify results
        assert result["success"] == True, "Normalization should succeed"
        assert len(result["normalized_urls"]) == len(test_urls), "Should process all URLs"
        
        print(f"✓ Normalized {result['total_urls']} URLs")
        print(f"✓ Processing time: {result['processing_time_seconds']:.2f}s")
        print(f"✓ Statistics: {result['statistics']}")
        
        # Show normalization examples
        for i, norm_result in enumerate(result["normalized_urls"]):
            original = norm_result["original_url"]
            normalized = norm_result["normalized_url"] 
            changes = norm_result["changes_made"]
            
            print(f"\nURL {i+1}:")
            print(f"  Original:   {original}")
            print(f"  Normalized: {normalized}")
            print(f"  Changes:    {changes}")
        
        return result
        
    except Exception as e:
        print(f"✗ URL Normalize Tool test failed: {e}")
        return None


def test_business_filter_tool():
    """Test the business filtering tool"""
    print("\n=== Testing Business Filter Tool ===")
    
    try:
        # Test URLs with mix of business and non-business sites
        test_urls = [
            "https://example-business.com",
            "https://testcompany.com/services",
            "https://facebook.com/somecompany",
            "https://yelp.com/biz/local-business",
            "https://manufacturing-corp.biz/contact",
            "https://cnn.com/news/article",
            "https://local-restaurant.com/menu",
            "https://wordpress.com/blog",
            "https://consulting-firm.net/about"
        ]
        
        # Initialize the tool
        tool = BusinessFilterTool(
            urls=test_urls,
            exclude_social_media=True,
            exclude_directories=True,
            exclude_news_media=True,
            minimum_confidence=0.3
        )
        
        # Run filtering
        result = tool.run()
        
        # Verify results
        assert result["success"] == True, "Filtering should succeed"
        assert result["total_urls"] == len(test_urls), "Should process all URLs"
        
        print(f"✓ Filtered {result['total_urls']} URLs")
        print(f"✓ Business URLs: {result['business_urls']}")
        print(f"✓ Filtered out: {result['filtered_urls']}")
        print(f"✓ Processing time: {result['processing_time_seconds']:.2f}s")
        print(f"✓ Statistics: {result['statistics']}")
        
        # Show filtering results
        business_urls = result["business_urls_only"]
        print(f"\nBusiness URLs identified ({len(business_urls)}):")
        for url in business_urls:
            print(f"  ✓ {url}")
        
        # Show filter details
        print(f"\nFilter details:")
        for filter_result in result["filtered_results"]:
            url = filter_result["url"]
            is_business = filter_result["is_business"]
            confidence = filter_result["confidence_score"]
            reasons = filter_result["filter_reasons"]
            
            status = "✓ BUSINESS" if is_business else "✗ FILTERED"
            print(f"  {status} {url} (confidence: {confidence:.2f}) {reasons}")
        
        return result
        
    except Exception as e:
        print(f"✗ Business Filter Tool test failed: {e}")
        return None


def test_integrated_workflow():
    """Test the complete integrated workflow"""
    print("\n=== Testing Integrated Workflow ===")
    
    try:
        # Step 1: Parse SERP HTML
        html_content = create_mock_bing_html()
        
        parse_tool = SerpParseTool(
            html_content=html_content,
            query="business services consulting",
            page_number=1
        )
        
        parse_result = parse_tool.run()
        if not parse_result["success"]:
            raise Exception("SERP parsing failed")
        
        extracted_urls = [r["url"] for r in parse_result["results"]]
        print(f"✓ Step 1: Extracted {len(extracted_urls)} URLs from SERP")
        
        # Step 2: Normalize URLs
        normalize_tool = UrlNormalizeTool(
            urls=extracted_urls,
            remove_tracking=True,
            unwrap_redirects=True
        )
        
        normalize_result = normalize_tool.run()
        if not normalize_result["success"]:
            raise Exception("URL normalization failed")
        
        normalized_urls = normalize_result["valid_urls"]
        print(f"✓ Step 2: Normalized to {len(normalized_urls)} valid URLs")
        
        # Step 3: Filter for business URLs
        filter_tool = BusinessFilterTool(
            urls=normalized_urls,
            exclude_social_media=True,
            exclude_directories=True,
            minimum_confidence=0.3
        )
        
        filter_result = filter_tool.run()
        if not filter_result["success"]:
            raise Exception("Business filtering failed")
        
        business_urls = filter_result["business_urls_only"]
        print(f"✓ Step 3: Identified {len(business_urls)} business URLs")
        
        # Show final results
        print(f"\nFinal business URLs:")
        for url in business_urls:
            print(f"  → {url}")
        
        # Calculate pipeline statistics
        pipeline_stats = {
            "original_results": len(extracted_urls),
            "normalized_urls": len(normalized_urls),
            "business_urls": len(business_urls),
            "conversion_rate": len(business_urls) / len(extracted_urls) if extracted_urls else 0
        }
        
        print(f"\nPipeline Statistics:")
        print(f"  Original SERP results: {pipeline_stats['original_results']}")
        print(f"  Normalized URLs: {pipeline_stats['normalized_urls']}")
        print(f"  Business URLs: {pipeline_stats['business_urls']}")
        print(f"  Conversion rate: {pipeline_stats['conversion_rate']:.1%}")
        
        return pipeline_stats
        
    except Exception as e:
        print(f"✗ Integrated workflow test failed: {e}")
        return None


def test_serp_parser_agent():
    """Test the SERP Parser Agent initialization"""
    print("\n=== Testing SERP Parser Agent ===")
    
    try:
        # Initialize the agent
        agent = SerpParserAgent(
            name="TestSerpParser",
            description="Test SERP parsing agent"
        )
        
        print(f"✓ Agent initialized: {agent.name}")
        print(f"✓ Tools available: {len(agent.tools)}")
        
        # Test capability methods
        capabilities = agent.get_parsing_capabilities()
        print(f"✓ Parsing capabilities: {list(capabilities.keys())}")
        
        selector_config = agent.get_selector_configuration()
        print(f"✓ Selector configuration: {list(selector_config.keys())}")
        
        business_filters = agent.get_business_filters()
        print(f"✓ Business filters configured: {len(business_filters['exclude_domains'])} domains")
        
        return True
        
    except Exception as e:
        print(f"✗ SERP Parser Agent test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting SERP Parser System Tests")
    print("=" * 50)
    
    test_results = {}
    
    # Run individual component tests
    test_results["serp_parse"] = test_serp_parse_tool()
    test_results["url_normalize"] = test_url_normalize_tool()  
    test_results["business_filter"] = test_business_filter_tool()
    test_results["agent_init"] = test_serp_parser_agent()
    test_results["integrated"] = test_integrated_workflow()
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 Test Summary")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! SERP Parser System is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)