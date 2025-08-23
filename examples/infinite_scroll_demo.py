#!/usr/bin/env python3
"""
Infinite Scroll Handler Demo
Demonstrates usage of the infinite scroll handler for map results
"""

import sys
import os
import json
import csv
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.infinite_scroll_handler import (
    InfiniteScrollHandler, 
    ScrollConfig,
    create_scroll_handler
)

def demo_bing_maps_scroll():
    """Demonstrate Bing Maps infinite scrolling"""
    print("\n" + "="*80)
    print("BING MAPS INFINITE SCROLL DEMO")
    print("="*80)
    
    # Create scroll handler with adaptive strategy
    config = ScrollConfig(
        max_scroll_iterations=15,
        scroll_pause_time=2.5,
        strategy_type='adaptive',
        timeout_seconds=180
    )
    
    handler = InfiniteScrollHandler(config)
    
    # Test different search scenarios
    test_scenarios = [
        {"query": "restaurants", "location": "Miami, FL"},
        {"query": "doctors", "location": "Seattle, WA"},
        {"query": "coffee shops", "location": "Austin, TX"}
    ]
    
    all_results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n[Scenario {i}/3] Testing: {scenario['query']} in {scenario['location']}")
        print("-" * 60)
        
        try:
            # Execute scroll session
            session = handler.scroll_and_extract_bing_maps(
                scenario['query'], 
                scenario['location']
            )
            
            # Generate session report
            report = handler.create_session_report(session)
            
            # Display results
            print(f"✅ Scroll completed successfully!")
            print(f"   Platform: {session.platform}")
            print(f"   Duration: {report['session_info']['duration_seconds']:.1f} seconds")
            print(f"   Total businesses found: {len(session.extracted_businesses)}")
            
            if session.scroll_metrics:
                print(f"   Scroll iterations: {session.scroll_metrics.get('total_iterations', 'N/A')}")
                print(f"   Completion reason: {session.scroll_metrics.get('completed_reason', 'N/A')}")
            
            # Show sample businesses
            if session.extracted_businesses:
                print(f"\n📋 Sample businesses found:")
                for j, business in enumerate(session.extracted_businesses[:3], 1):
                    print(f"   {j}. {business.get('business_name', 'N/A')}")
                    if business.get('phone'):
                        print(f"      Phone: {business['phone']}")
                    if business.get('email'):
                        print(f"      Email: {business['email']}")
                    if business.get('website'):
                        print(f"      Website: {business['website']}")
                    print()
            
            # Save results
            all_results.append({
                'scenario': scenario,
                'session': session,
                'report': report
            })
            
        except Exception as e:
            print(f"❌ Error in scenario {i}: {e}")
    
    return all_results

def demo_google_maps_scroll():
    """Demonstrate Google Maps infinite scrolling"""
    print("\n" + "="*80)
    print("GOOGLE MAPS INFINITE SCROLL DEMO")
    print("="*80)
    
    # Create handler with chunk strategy for Google Maps
    handler = create_scroll_handler('chunk', 12)
    
    # Test scenario
    query = "gyms"
    location = "Los Angeles, CA"
    
    print(f"Testing: {query} in {location}")
    print("-" * 60)
    
    try:
        session = handler.scroll_and_extract_google_maps(query, location)
        report = handler.create_session_report(session)
        
        print(f"✅ Google Maps scroll completed!")
        print(f"   Duration: {report['session_info']['duration_seconds']:.1f} seconds")
        print(f"   Total businesses: {len(session.extracted_businesses)}")
        print(f"   Strategy used: {handler.config.strategy_type}")
        
        return session, report
        
    except Exception as e:
        print(f"❌ Error in Google Maps demo: {e}")
        return None, None

def demo_strategy_comparison():
    """Compare different scrolling strategies"""
    print("\n" + "="*80)
    print("SCROLLING STRATEGY COMPARISON")
    print("="*80)
    
    strategies = ['smooth', 'chunk', 'adaptive']
    query = "cafes"
    location = "Portland, OR"
    
    results = {}
    
    for strategy in strategies:
        print(f"\n🔄 Testing {strategy.upper()} strategy...")
        print("-" * 40)
        
        try:
            handler = create_scroll_handler(strategy, 8)  # Shorter test
            session = handler.scroll_and_extract_bing_maps(query, location)
            report = handler.create_session_report(session)
            
            results[strategy] = {
                'duration': report['session_info']['duration_seconds'],
                'businesses_found': len(session.extracted_businesses),
                'iterations': session.scroll_metrics.get('total_iterations', 0),
                'completion_reason': session.scroll_metrics.get('completed_reason', 'unknown')
            }
            
            print(f"   ✅ {strategy.title()} completed:")
            print(f"      Duration: {results[strategy]['duration']:.1f}s")
            print(f"      Businesses: {results[strategy]['businesses_found']}")
            print(f"      Iterations: {results[strategy]['iterations']}")
            
        except Exception as e:
            print(f"   ❌ {strategy.title()} failed: {e}")
            results[strategy] = {'error': str(e)}
    
    # Summary comparison
    print(f"\n📊 STRATEGY COMPARISON SUMMARY")
    print("-" * 40)
    
    for strategy, result in results.items():
        if 'error' not in result:
            efficiency = result['businesses_found'] / result['duration'] if result['duration'] > 0 else 0
            print(f"{strategy.title():>10}: {result['businesses_found']:>3} businesses in {result['duration']:>5.1f}s "
                  f"({efficiency:.1f} businesses/sec)")
    
    return results

def save_demo_results(all_results, filename_prefix="infinite_scroll_demo"):
    """Save demo results to files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Ensure output directory exists
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Save comprehensive JSON report
    json_filename = output_dir / f"{filename_prefix}_{timestamp}.json"
    
    json_data = {
        'demo_info': {
            'timestamp': timestamp,
            'total_scenarios': len(all_results),
            'demo_type': 'infinite_scroll_handler'
        },
        'results': []
    }
    
    # Convert results to JSON-serializable format
    for result in all_results:
        scenario_data = {
            'scenario': result['scenario'],
            'session_info': {
                'platform': result['session'].platform,
                'query': result['session'].query,
                'location': result['session'].location,
                'start_time': result['session'].start_time.isoformat(),
                'business_count': len(result['session'].extracted_businesses),
                'scroll_metrics': result['session'].scroll_metrics
            },
            'businesses': result['session'].extracted_businesses,
            'report': result['report']
        }
        json_data['results'].append(scenario_data)
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Save businesses to CSV
    csv_filename = output_dir / f"{filename_prefix}_businesses_{timestamp}.csv"
    
    all_businesses = []
    for result in all_results:
        for business in result['session'].extracted_businesses:
            business_data = business.copy()
            business_data['scenario_query'] = result['scenario']['query']
            business_data['scenario_location'] = result['scenario']['location']
            all_businesses.append(business_data)
    
    if all_businesses:
        fieldnames = [
            'scenario_query', 'scenario_location', 'business_name', 
            'address', 'phone', 'email', 'website', 'rating', 
            'review_count', 'category', 'source_platform'
        ]
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for business in all_businesses:
                # Ensure all fields exist
                row = {field: business.get(field, '') for field in fieldnames}
                writer.writerow(row)
    
    print(f"\n💾 Demo results saved:")
    print(f"   📄 Detailed report: {json_filename}")
    print(f"   📊 Business CSV: {csv_filename}")
    print(f"   📈 Total businesses exported: {len(all_businesses)}")
    
    return json_filename, csv_filename

def main():
    """Main demo function"""
    print("🚀 BOTASAURUS INFINITE SCROLL HANDLER DEMO")
    print("="*80)
    print("This demo showcases the infinite scroll handler capabilities")
    print("for extracting business data from map search results.")
    print()
    
    try:
        # Demo 1: Bing Maps with multiple scenarios
        print("🎯 Running Bing Maps demo with multiple scenarios...")
        bing_results = demo_bing_maps_scroll()
        
        # Demo 2: Google Maps comparison
        print("\n🎯 Running Google Maps demo...")
        google_session, google_report = demo_google_maps_scroll()
        
        if google_session:
            bing_results.append({
                'scenario': {'query': 'gyms', 'location': 'Los Angeles, CA', 'platform': 'google'},
                'session': google_session,
                'report': google_report
            })
        
        # Demo 3: Strategy comparison
        print("\n🎯 Running strategy comparison...")
        strategy_results = demo_strategy_comparison()
        
        # Save all results
        if bing_results:
            json_file, csv_file = save_demo_results(bing_results)
        
        # Final summary
        print(f"\n🎉 DEMO COMPLETE!")
        print("="*80)
        
        total_businesses = sum(len(r['session'].extracted_businesses) for r in bing_results)
        print(f"📊 Overall Statistics:")
        print(f"   • Total scenarios tested: {len(bing_results)}")
        print(f"   • Total businesses extracted: {total_businesses}")
        print(f"   • Platforms tested: Bing Maps, Google Maps")
        print(f"   • Strategies tested: {', '.join(strategy_results.keys())}")
        
        print(f"\n📋 Key Features Demonstrated:")
        print(f"   ✅ Multi-platform support (Bing Maps, Google Maps)")
        print(f"   ✅ Multiple scrolling strategies (smooth, chunk, adaptive)")
        print(f"   ✅ Business data extraction (name, phone, email, website)")
        print(f"   ✅ Infinite scroll detection and handling")
        print(f"   ✅ Anti-detection with Botasaurus")
        print(f"   ✅ Comprehensive reporting and metrics")
        print(f"   ✅ CSV and JSON export capabilities")
        
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()