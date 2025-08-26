"""
Test Script for Query Builder System

Demonstrates the complete functionality of the search query builder
including template expansion, geographic variations, and validation.
"""

import logging
import time
from pathlib import Path
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_query_builder_basic():
    """Test basic query builder functionality."""
    print("=" * 60)
    print("Testing Basic Query Builder Functionality")
    print("=" * 60)
    
    try:
        from src.query_builder import QueryBuilder, VerticalType
        from src.query_builder.campaign_parser import CampaignParser
        
        # Initialize query builder
        query_builder = QueryBuilder()
        
        # Create a simple campaign
        campaign = query_builder.create_sample_campaign(
            vertical=VerticalType.RESTAURANTS,
            cities=["New York", "Los Angeles", "Chicago"]
        )
        
        print(f"Created sample campaign: {campaign.name}")
        print(f"Vertical: {campaign.vertical.value}")
        print(f"Cities: {campaign.cities}")
        print(f"Service terms: {campaign.service_terms}")
        
        # Build queries
        plan = query_builder.build_queries_from_campaign(campaign)
        
        print(f"\nQuery Plan Results:")
        print(f"- Total queries: {plan.total_queries}")
        print(f"- Generation time: {plan.generation_time:.2f}s")
        print(f"- Plan hash: {plan.plan_hash[:16]}...")
        
        # Show first 10 queries
        print(f"\nFirst 10 queries:")
        for i, query in enumerate(plan.queries[:10], 1):
            print(f"  {i}. {query}")
        
        # Show geographic distribution
        geo_dist = plan.geographic_distribution
        print(f"\nGeographic Coverage:")
        print(f"- Unique states: {geo_dist['unique_states']}")
        print(f"- Total locations: {geo_dist['total_locations']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Basic test failed: {e}")
        return False


def test_template_manager():
    """Test template manager functionality."""
    print("\n" + "=" * 60)
    print("Testing Template Manager")
    print("=" * 60)
    
    try:
        from src.query_builder.template_manager import TemplateManager, VerticalType, SearchIntent
        
        # Initialize template manager
        tm = TemplateManager()
        
        # Get statistics
        stats = tm.get_statistics()
        print(f"Template Manager Statistics:")
        print(f"- Total templates: {stats['total_templates']}")
        print(f"- Verticals: {list(stats['verticals'].keys())}")
        print(f"- Intents: {list(stats['intents'].keys())}")
        
        # Get restaurant templates
        restaurant_templates = tm.get_templates_by_vertical(VerticalType.RESTAURANTS)
        print(f"\nRestaurant templates: {len(restaurant_templates)}")
        
        for i, template in enumerate(restaurant_templates[:3], 1):
            print(f"  {i}. {template.template} (Priority: {template.priority})")
        
        # Test template formatting
        if restaurant_templates:
            template = restaurant_templates[0]
            formatted = template.format(service_type="restaurant", city="New York")
            print(f"\nFormatted example: {formatted}")
        
        return True
        
    except Exception as e:
        logger.error(f"Template manager test failed: {e}")
        return False


def test_regional_expander():
    """Test regional expansion functionality."""
    print("\n" + "=" * 60)
    print("Testing Regional Expander")
    print("=" * 60)
    
    try:
        from src.query_builder.regional_expander import RegionalExpander
        
        # Initialize regional expander
        re = RegionalExpander()
        
        # Get statistics
        stats = re.get_statistics()
        print(f"Regional Expander Statistics:")
        print(f"- Total locations: {stats['total_locations']}")
        print(f"- Unique states: {stats['unique_states']}")
        print(f"- Total population: {stats['total_population_covered']:,}")
        
        # Get top cities
        top_cities = re.get_top_cities(10)
        print(f"\nTop 10 cities by population:")
        for i, city in enumerate(top_cities, 1):
            pop = f"{city.population:,}" if city.population else "N/A"
            print(f"  {i}. {city.name}, {city.state_code} ({pop})")
        
        # Test template expansion
        template = "restaurant {city} contact"
        expanded = re.expand_template_regionally(
            template=template,
            max_locations=5
        )
        
        print(f"\nExpanded template '{template}' to {len(expanded)} queries:")
        for i, (query, location) in enumerate(expanded[:5], 1):
            print(f"  {i}. {query}")
        
        return True
        
    except Exception as e:
        logger.error(f"Regional expander test failed: {e}")
        return False


def test_query_validator():
    """Test query validation functionality."""
    print("\n" + "=" * 60)
    print("Testing Query Validator")
    print("=" * 60)
    
    try:
        from src.query_builder.query_validator import QueryValidator
        
        # Initialize validator
        validator = QueryValidator()
        
        # Test queries with various issues
        test_queries = [
            "restaurant New York contact",  # Good query
            "",  # Empty query
            "restaurant" * 100,  # Too long
            'restaurant "New York" contact email',  # Good with quotes
            "restaurant AND OR contact",  # Invalid operators
            "site:example.com restaurant contact",  # With operator
            'restaurant "" contact',  # Empty quotes
        ]
        
        print(f"Validating {len(test_queries)} test queries:")
        
        results = validator.validate_query_batch(test_queries)
        
        for i, (query, result) in enumerate(zip(test_queries, results), 1):
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            query_preview = query[:30] + "..." if len(query) > 30 else query
            print(f"  {i}. {status} - '{query_preview}'")
            
            if result.issues:
                for severity, message in result.issues[:2]:  # Show first 2 issues
                    print(f"     {severity.value.upper()}: {message}")
        
        # Show summary
        summary = validator.get_validation_summary(results)
        print(f"\nValidation Summary:")
        print(f"- Total queries: {summary['total_queries']}")
        print(f"- Valid queries: {summary['valid_queries']}")
        print(f"- Validation rate: {summary['validation_rate']}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Query validator test failed: {e}")
        return False


def test_campaign_parser():
    """Test campaign YAML parsing."""
    print("\n" + "=" * 60)
    print("Testing Campaign Parser")
    print("=" * 60)
    
    try:
        from src.query_builder.campaign_parser import CampaignParser
        
        # Initialize parser
        parser = CampaignParser()
        
        # Test parsing sample campaign file
        sample_file = Path("sample_campaign.yaml")
        if sample_file.exists():
            campaigns = parser.parse_campaign_file(sample_file)
            
            print(f"Parsed {len(campaigns)} campaigns from {sample_file}")
            
            for campaign in campaigns:
                print(f"\nCampaign: {campaign.name}")
                print(f"- Vertical: {campaign.vertical.value if campaign.vertical else 'None'}")
                print(f"- Service terms: {len(campaign.service_terms)}")
                print(f"- Query templates: {len(campaign.query_templates)}")
                print(f"- Cities: {len(campaign.cities)}")
                print(f"- States: {len(campaign.states)}")
                
                if campaign.query_templates:
                    print(f"- First template: {campaign.query_templates[0]}")
        else:
            print(f"Sample campaign file not found: {sample_file}")
            
            # Create a sample campaign programmatically
            from src.query_builder.template_manager import VerticalType
            
            sample_campaign = parser.create_campaign_from_parameters(
                name="Test Campaign",
                vertical=VerticalType.RESTAURANTS,
                cities=["New York", "Los Angeles"],
                service_terms=["restaurant", "cafe"]
            )
            
            print(f"Created sample campaign: {sample_campaign.name}")
            
            # Export to YAML
            yaml_content = parser.export_campaign_to_yaml(sample_campaign)
            print(f"\nGenerated YAML (first 200 chars):")
            print(yaml_content[:200] + "...")
        
        return True
        
    except Exception as e:
        logger.error(f"Campaign parser test failed: {e}")
        return False


def test_full_integration():
    """Test full integration from YAML to queries."""
    print("\n" + "=" * 60)
    print("Testing Full Integration")
    print("=" * 60)
    
    try:
        from src.query_builder import QueryBuilder
        
        # Initialize query builder
        query_builder = QueryBuilder()
        
        # Test with sample YAML file
        yaml_file = Path("sample_campaign.yaml")
        
        if yaml_file.exists():
            # Build queries from YAML
            output_file = Path("out/test_queries.txt")
            
            plans = query_builder.build_queries_from_yaml(
                yaml_file=yaml_file,
                output_file=output_file
            )
            
            print(f"Built {len(plans)} query plans from {yaml_file}")
            
            total_queries = sum(plan.total_queries for plan in plans)
            total_time = sum(plan.generation_time for plan in plans)
            
            print(f"Overall Results:")
            print(f"- Total queries: {total_queries}")
            print(f"- Generation time: {total_time:.2f}s")
            print(f"- Output file: {output_file}")
            
            # Check if file was created
            if output_file.exists():
                file_size = output_file.stat().st_size
                print(f"- File size: {file_size} bytes")
                
                # Show first few lines
                with open(output_file, 'r') as f:
                    lines = f.readlines()[:5]
                    
                print(f"- First 5 queries:")
                for i, line in enumerate(lines, 1):
                    print(f"  {i}. {line.strip()}")
            
            return True
        else:
            print(f"Sample YAML file not found: {yaml_file}")
            return False
        
    except Exception as e:
        logger.error(f"Full integration test failed: {e}")
        return False


def test_agency_swarm_tools():
    """Test Agency Swarm tools."""
    print("\n" + "=" * 60)
    print("Testing Agency Swarm Tools")
    print("=" * 60)
    
    try:
        from src.agents.tools.build_queries_tool import BuildQueriesTool
        from src.agents.tools.geo_expand_tool import GeoExpandTool
        
        print("Testing BuildQueriesTool...")
        
        # Test with sample YAML
        sample_yaml = """
name: "Test Campaign"
vertical: "restaurants"
service_terms:
  - "restaurant"
  - "cafe"
query_templates:
  - "{service_type} {city} contact"
cities:
  - "New York"
  - "Los Angeles"
max_queries_per_template: 5
"""
        
        tool = BuildQueriesTool(
            campaign_yaml=sample_yaml,
            output_file="out/agency_test_queries.txt",
            max_queries_per_template=5
        )
        
        result = tool.run()
        print("BuildQueriesTool result:")
        print(result[:500] + "..." if len(result) > 500 else result)
        
        print("\nTesting GeoExpandTool...")
        
        geo_tool = GeoExpandTool(
            templates=["restaurant {city} contact", "cafe {city} {state}"],
            max_locations=5,
            target_states=["CA", "NY"],
            output_file="out/geo_test_queries.txt"
        )
        
        geo_result = geo_tool.run()
        print("GeoExpandTool result:")
        print(geo_result[:500] + "..." if len(geo_result) > 500 else geo_result)
        
        return True
        
    except Exception as e:
        logger.error(f"Agency Swarm tools test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Starting Query Builder System Tests")
    print("=" * 60)
    
    start_time = time.time()
    
    tests = [
        ("Basic Query Builder", test_query_builder_basic),
        ("Template Manager", test_template_manager),
        ("Regional Expander", test_regional_expander),
        ("Query Validator", test_query_validator),
        ("Campaign Parser", test_campaign_parser),
        ("Full Integration", test_full_integration),
        ("Agency Swarm Tools", test_agency_swarm_tools)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 Running: {test_name}")
            success = test_func()
            results[test_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {status}")
        except Exception as e:
            results[test_name] = False
            print(f"   ❌ FAILED: {e}")
    
    # Final summary
    total_time = time.time() - start_time
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    print(f"Total time: {total_time:.2f}s")
    
    print(f"\nDetailed Results:")
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status} {test_name}")
    
    if passed == total:
        print(f"\n🎉 All tests passed! Query Builder System is working correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)