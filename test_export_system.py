#!/usr/bin/env python3
"""
Test script for the comprehensive export system.

This script demonstrates the complete export functionality including
CSV generation, JSON statistics, analytics, error logging, and file validation.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test data generation
def generate_test_data() -> List[Dict[str, Any]]:
    """Generate sample contact data for testing"""
    test_contacts = []
    
    # High quality contact
    test_contacts.append({
        "podcast_name": "Tech Innovators Weekly",
        "host_name": "Sarah Johnson",
        "podcast_description": "Weekly interviews with leading technology innovators and entrepreneurs.",
        "host_email": "sarah@techinnovators.com",
        "booking_email": "bookings@techinnovators.com",
        "alternative_emails": ["sarah.johnson@gmail.com"],
        "podcast_website": "https://techinnovators.com",
        "contact_page_url": "https://techinnovators.com/contact",
        "contact_forms_available": "Yes",
        "best_contact_method": "email",
        "contact_strategy": "Professional email with specific value proposition",
        "contact_confidence": "very_high",
        "social_links": {
            "twitter": "https://twitter.com/sarahtech",
            "linkedin": "https://linkedin.com/in/sarahjohnson"
        },
        "social_influence_score": 85.5,
        "social_platforms_count": 2,
        "overall_intelligence_score": 8.7,
        "relevance_score": 9.2,
        "popularity_score": 8.1,
        "authority_score": 8.9,
        "content_quality_score": 9.0,
        "guest_potential_score": 8.8,
        "contact_quality_score": 92.5,
        "response_likelihood": 78.2,
        "validation_status": "Valid",
        "estimated_downloads": 25000,
        "audience_size_category": "Large",
        "episode_count": 156,
        "rating": 4.8,
        "host_authority_level": "Expert",
        "platform_source": "Apple Podcasts",
        "apple_podcasts_url": "https://podcasts.apple.com/podcast/tech-innovators/id123456",
        "spotify_url": "https://open.spotify.com/show/123456",
        "youtube_url": "",
        "google_podcasts_url": "",
        "rss_feed_url": "https://techinnovators.com/feed",
        "content_format_type": "Interview",
        "interview_style": "Yes",
        "target_audience": "Tech professionals, entrepreneurs",
        "content_themes": "Technology, Innovation, Startups",
        "recommendations": ["High priority contact", "Tech industry focus"],
        "risk_factors": ["High competition for guest spots"],
        "outreach_priority": "High",
        "best_pitch_angle": "AI/ML expertise and industry insights",
        "ai_relevance_score": 9.1,
        "discovery_source": "Apple Podcasts API",
        "validation_date": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "data_quality_grade": "A",
        "notes": "Excellent fit for tech-focused guest appearances"
    })
    
    # Medium quality contact
    test_contacts.append({
        "podcast_name": "Business Growth Stories",
        "host_name": "Mike Chen",
        "podcast_description": "Stories of business growth and entrepreneurship.",
        "host_email": "",
        "booking_email": "",
        "alternative_emails": [],
        "podcast_website": "https://businessgrowthstories.com",
        "contact_page_url": "https://businessgrowthstories.com/contact",
        "contact_forms_available": "Yes",
        "best_contact_method": "contact_form",
        "contact_strategy": "Use website contact form with detailed proposal",
        "contact_confidence": "medium",
        "social_links": {
            "twitter": "https://twitter.com/mikechenbc"
        },
        "social_influence_score": 42.3,
        "social_platforms_count": 1,
        "overall_intelligence_score": 6.8,
        "relevance_score": 7.2,
        "popularity_score": 6.1,
        "authority_score": 6.9,
        "content_quality_score": 7.4,
        "guest_potential_score": 6.5,
        "contact_quality_score": 65.8,
        "response_likelihood": 45.3,
        "validation_status": "Valid",
        "estimated_downloads": 5000,
        "audience_size_category": "Medium",
        "episode_count": 87,
        "rating": 4.2,
        "host_authority_level": "Intermediate",
        "platform_source": "Spotify",
        "apple_podcasts_url": "",
        "spotify_url": "https://open.spotify.com/show/789012",
        "youtube_url": "",
        "google_podcasts_url": "",
        "rss_feed_url": "https://businessgrowthstories.com/feed",
        "content_format_type": "Narrative",
        "interview_style": "No",
        "target_audience": "Small business owners",
        "content_themes": "Business, Entrepreneurship, Growth",
        "recommendations": ["Consider for business-focused topics"],
        "risk_factors": ["Limited contact options"],
        "outreach_priority": "Medium",
        "best_pitch_angle": "Business growth and scaling insights",
        "ai_relevance_score": 5.8,
        "discovery_source": "Spotify API",
        "validation_date": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "data_quality_grade": "B",
        "notes": "Good potential but limited contact information"
    })
    
    # Low quality contact
    test_contacts.append({
        "podcast_name": "Random Thoughts Podcast",
        "host_name": "Alex Smith",
        "podcast_description": "Random thoughts and discussions.",
        "host_email": "",
        "booking_email": "",
        "alternative_emails": [],
        "podcast_website": "",
        "contact_page_url": "",
        "contact_forms_available": "No",
        "best_contact_method": "social_media",
        "contact_strategy": "Engage via social media first",
        "contact_confidence": "low",
        "social_links": {
            "twitter": "https://twitter.com/alexrandom"
        },
        "social_influence_score": 12.1,
        "social_platforms_count": 1,
        "overall_intelligence_score": 3.2,
        "relevance_score": 2.8,
        "popularity_score": 3.5,
        "authority_score": 2.9,
        "content_quality_score": 3.8,
        "guest_potential_score": 2.1,
        "contact_quality_score": 25.4,
        "response_likelihood": 15.7,
        "validation_status": "Low_Quality",
        "estimated_downloads": 500,
        "audience_size_category": "Small",
        "episode_count": 23,
        "rating": 3.1,
        "host_authority_level": "Beginner",
        "platform_source": "YouTube",
        "apple_podcasts_url": "",
        "spotify_url": "",
        "youtube_url": "https://youtube.com/channel/randomthoughts",
        "google_podcasts_url": "",
        "rss_feed_url": "",
        "content_format_type": "Conversational",
        "interview_style": "No",
        "target_audience": "General",
        "content_themes": "General discussion",
        "recommendations": ["Low priority"],
        "risk_factors": ["Very limited reach", "Unclear content focus"],
        "outreach_priority": "Low",
        "best_pitch_angle": "General topics",
        "ai_relevance_score": 1.5,
        "discovery_source": "YouTube API",
        "validation_date": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "data_quality_grade": "C",
        "notes": "Limited value for professional outreach"
    })
    
    return test_contacts


def generate_test_campaign_info() -> Dict[str, Any]:
    """Generate sample campaign information"""
    return {
        "campaign_id": "test_campaign_001",
        "topic": "AI and Machine Learning Technology",
        "search_parameters": {
            "keywords": ["AI", "machine learning", "technology", "innovation"],
            "platforms": ["Apple Podcasts", "Spotify", "YouTube"],
            "min_episode_count": 10,
            "target_audience_size": "medium_to_large"
        },
        "processing_duration_minutes": 45.2,
        "start_time": "2025-08-21T00:00:00Z",
        "end_time": datetime.now().isoformat()
    }


def generate_test_proxy_stats() -> Dict[str, Any]:
    """Generate sample proxy performance statistics"""
    return {
        "provider": "test_proxy_provider",
        "total_requests": 1250,
        "successful_requests": 1185,
        "failed_requests": 65,
        "avg_response_time_ms": 850.5,
        "blocked_count": 23,
        "rotation_count": 15,
        "bandwidth_used_mb": 125.8,
        "cost_estimate": 12.45,
        "errors_by_type": {
            "timeout": 32,
            "connection_error": 18,
            "blocked": 23,
            "rate_limit": 12
        }
    }


def test_csv_export():
    """Test CSV export functionality"""
    print("\n=== Testing CSV Export ===")
    
    try:
        from src.agents.tools.csv_export_tool import CSVExportTool
        
        test_data = generate_test_data()
        output_path = os.path.join("output", "test_export.csv")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        csv_tool = CSVExportTool(
            contact_data=test_data,
            output_path=output_path,
            validate_schema=True,
            include_metadata=True
        )
        
        result_str = csv_tool.run()
        result = json.loads(result_str)
        
        print(f"CSV Export Success: {result['success']}")
        if result['success']:
            print(f"CSV File: {result['csv_path']}")
            print(f"Rows Exported: {result['metrics']['total_rows']}")
            print(f"File Size: {result['metrics']['file_size_bytes']} bytes")
        else:
            print(f"CSV Export Error: {result['error']}")
        
        return result['success']
        
    except Exception as e:
        print(f"CSV Export Test Failed: {e}")
        return False


def test_json_export():
    """Test JSON statistics export functionality"""
    print("\n=== Testing JSON Export ===")
    
    try:
        from src.agents.tools.json_stats_export_tool import CampaignSummaryExportTool, ProxyPerformanceExportTool
        
        test_data = generate_test_data()
        campaign_info = generate_test_campaign_info()
        proxy_stats = generate_test_proxy_stats()
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Test campaign summary export
        summary_path = os.path.join("output", "test_campaign_summary.json")
        summary_tool = CampaignSummaryExportTool(
            contact_data=test_data,
            campaign_info=campaign_info,
            output_path=summary_path,
            include_detailed_analytics=True
        )
        
        summary_result_str = summary_tool.run()
        summary_result = json.loads(summary_result_str)
        
        print(f"Campaign Summary Success: {summary_result['success']}")
        if summary_result['success']:
            print(f"Summary File: {summary_result['summary_path']}")
        
        # Test proxy performance export
        proxy_path = os.path.join("output", "test_proxy_performance.json")
        proxy_tool = ProxyPerformanceExportTool(
            proxy_stats=proxy_stats,
            output_path=proxy_path,
            include_cost_analysis=True
        )
        
        proxy_result_str = proxy_tool.run()
        proxy_result = json.loads(proxy_result_str)
        
        print(f"Proxy Performance Success: {proxy_result['success']}")
        if proxy_result['success']:
            print(f"Proxy File: {proxy_result['performance_path']}")
        
        return summary_result['success'] and proxy_result['success']
        
    except Exception as e:
        print(f"JSON Export Test Failed: {e}")
        return False


def test_comprehensive_export():
    """Test comprehensive export functionality"""
    print("\n=== Testing Comprehensive Export ===")
    
    try:
        from src.agents.tools.comprehensive_export_tool import ComprehensiveExportTool
        
        test_data = generate_test_data()
        campaign_info = generate_test_campaign_info()
        proxy_stats = generate_test_proxy_stats()
        
        comprehensive_tool = ComprehensiveExportTool(
            contact_data=test_data,
            campaign_info=campaign_info,
            proxy_stats=proxy_stats,
            export_config={"output_directory": "output"},
            upload_to_drive=False,  # Skip Drive upload for testing
            validate_exports=True,
            generate_analytics=True
        )
        
        result_str = comprehensive_tool.run()
        result = json.loads(result_str)
        
        print(f"Comprehensive Export Success: {result['success']}")
        print(f"Message: {result['message']}")
        
        # Print phase results
        export_results = result.get('export_results', {})
        phases = export_results.get('export_phases', {})
        
        print("\nPhase Results:")
        for phase_name, phase_result in phases.items():
            status = "✓" if phase_result.get('success', False) else "✗"
            print(f"  {status} {phase_name}: {phase_result.get('success', False)}")
        
        # Print performance metrics
        performance = export_results.get('performance_metrics', {})
        if performance:
            print(f"\nPerformance:")
            print(f"  Total Time: {performance.get('total_export_time_seconds', 0):.2f}s")
            print(f"  Contacts/sec: {performance.get('contacts_per_second', 0):.1f}")
        
        return result['success']
        
    except Exception as e:
        print(f"Comprehensive Export Test Failed: {e}")
        return False


def test_file_validation():
    """Test file validation functionality"""
    print("\n=== Testing File Validation ===")
    
    try:
        from src.agents.tools.file_validation_tool import FileValidationTool
        
        # Test with files that should exist from previous tests
        test_files = [
            os.path.join("output", "test_export.csv"),
            os.path.join("output", "test_campaign_summary.json")
        ]
        
        # Filter to only existing files
        existing_files = [f for f in test_files if os.path.exists(f)]
        
        if not existing_files:
            print("No test files found for validation")
            return False
        
        validation_tool = FileValidationTool(
            file_paths=existing_files,
            validation_type="comprehensive",
            expected_schemas={
                "csv": ["podcast_name", "host_name", "host_email"],
                "csv_required": ["podcast_name", "host_name"]
            },
            generate_checksums=True
        )
        
        result_str = validation_tool.run()
        result = json.loads(result_str)
        
        print(f"File Validation Success: {result.get('overall_success', False)}")
        print(f"Files Validated: {result.get('files_validated', 0)}")
        print(f"Files Passed: {result.get('files_passed', 0)}")
        print(f"Files Failed: {result.get('files_failed', 0)}")
        
        return result.get('overall_success', False)
        
    except Exception as e:
        print(f"File Validation Test Failed: {e}")
        return False


def main():
    """Run all export system tests"""
    print("Starting Export System Tests...")
    print("=" * 50)
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Run tests
    tests = [
        ("CSV Export", test_csv_export),
        ("JSON Export", test_json_export),
        ("File Validation", test_file_validation),
        ("Comprehensive Export", test_comprehensive_export)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n{test_name} Test Error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All export system tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    # List generated files
    if os.path.exists("output"):
        print(f"\nGenerated files in 'output' directory:")
        for file in os.listdir("output"):
            file_path = os.path.join("output", file)
            size = os.path.getsize(file_path)
            print(f"  {file} ({size:,} bytes)")


if __name__ == "__main__":
    main()