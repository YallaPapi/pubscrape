"""
Simple test for SERP parser system - focuses on functionality testing
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.agents.tools.serp_parse_tool import SerpParseTool
    from src.agents.tools.url_normalize_tool import UrlNormalizeTool  
    from src.agents.tools.business_filter_tool import BusinessFilterTool
    print("✓ Successfully imported tools")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def create_mock_html():
    """Create mock Bing HTML"""
    return """
<!DOCTYPE html>
<html>
<head><title>Bing Search Results</title></head>
<body>
    <div id="b_results">
        <div class="b_algo">
            <h2><a href="https://example.com/business">Example Business</a></h2>
            <div class="b_caption"><p>Professional business services</p></div>
        </div>
        <div class="b_algo">
            <h2><a href="https://testcompany.com/services?utm_source=bing">Test Company</a></h2>
            <div class="b_caption"><p>Leading business solutions provider</p></div>
        </div>
        <div class="b_algo">
            <h2><a href="https://facebook.com/company">Facebook Page</a></h2>
            <div class="b_caption"><p>Company Facebook page</p></div>
        </div>
    </div>
</body>
</html>
"""


def test_serp_parse():
    """Test SERP parsing"""
    print("Testing SERP Parse Tool...")
    
    tool = SerpParseTool(
        html_content=create_mock_html(),
        query="business services",
        page_number=1
    )
    
    result = tool.run()
    
    if result["success"]:
        print(f"✓ Extracted {result['results_count']} results")
        return [r["url"] for r in result["results"]]
    else:
        print(f"✗ SERP parsing failed: {result.get('error', 'Unknown error')}")
        return []


def test_url_normalize(urls):
    """Test URL normalization"""
    print("Testing URL Normalize Tool...")
    
    tool = UrlNormalizeTool(
        urls=urls,
        remove_tracking=True,
        unwrap_redirects=True
    )
    
    result = tool.run()
    
    if result["success"]:
        print(f"✓ Normalized {result['total_urls']} URLs")
        return result["valid_urls"]
    else:
        print(f"✗ URL normalization failed")
        return urls


def test_business_filter(urls):
    """Test business filtering"""
    print("Testing Business Filter Tool...")
    
    tool = BusinessFilterTool(
        urls=urls,
        exclude_social_media=True,
        exclude_directories=True,
        minimum_confidence=0.3
    )
    
    result = tool.run()
    
    if result["success"]:
        print(f"✓ Found {result['business_urls']} business URLs out of {result['total_urls']}")
        return result["business_urls_only"]
    else:
        print(f"✗ Business filtering failed")
        return []


def main():
    """Run simple tests"""
    print("🚀 Running Simple SERP Parser Tests\n")
    
    # Test pipeline
    urls = test_serp_parse()
    if urls:
        normalized_urls = test_url_normalize(urls)
        business_urls = test_business_filter(normalized_urls)
        
        print(f"\nPipeline Results:")
        print(f"Original URLs: {len(urls)}")
        print(f"Normalized URLs: {len(normalized_urls)}")
        print(f"Business URLs: {len(business_urls)}")
        
        print(f"\nFinal business URLs:")
        for url in business_urls:
            print(f"  → {url}")
        
        if business_urls:
            print("\n✅ Pipeline working successfully!")
            return True
    
    print("\n❌ Pipeline failed")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)