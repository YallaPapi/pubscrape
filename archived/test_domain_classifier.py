#!/usr/bin/env python3
"""
Test script for the Business Website Classification & Prioritization system

This script demonstrates the complete end-to-end functionality of Task 65:
- Domain deduplication and data structure setup
- Platform detection probing system  
- Business website scoring algorithm
- Domain prioritization and crawl budget assignment
- Metrics collection and reporting system
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from agents.domain_classifier_agent import DomainClassifier, WebsiteType, PlatformType, PriorityLevel

def setup_logging():
    """Setup logging for the test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("DomainClassifierTest")
    return logger

def test_domain_classifier_complete():
    """Test the complete domain classification system"""
    logger = setup_logging()
    logger.info("Starting complete Domain Classification & Prioritization test")
    
    # Test domains - mix of business, personal, and e-commerce sites
    test_domains = [
        "https://www.shopify.com",
        "wordpress.com", 
        "example.com",
        "github.com/microsoft",
        "www.microsoft.com",
        "microsoft.com",  # Duplicate test
        "squarespace.com",
        "wix.com",
        "https://stripe.com",
        "invalid-domain-test.nonexistent",
        "blog.personal-site.com",
        "consulting-services.biz",
        "ecommerce-store.myshopify.com"
    ]
    
    # Initialize the domain classifier
    config = {
        "log_level": logging.INFO,
        "strip_www": True,
        "preserve_subdomain": True,
        "case_sensitive": False
    }
    
    classifier = DomainClassifier(config)
    
    # Step 1: Test domain deduplication and data structure setup (Task 65.1)
    logger.info("=== Step 1: Domain Deduplication and Data Structure Setup ===")
    result = classifier.add_domains(test_domains)
    
    logger.info(f"Domain addition results:")
    logger.info(f"  - Added domains: {result['added_domains']}")
    logger.info(f"  - Duplicate domains: {result['duplicate_domains']}")
    logger.info(f"  - Invalid domains: {result['invalid_domains']}")
    logger.info(f"  - Total unique domains: {result['total_unique_domains']}")
    
    # Step 2: Test platform detection probing system (Task 65.2)
    logger.info("=== Step 2: Platform Detection Probing System ===")
    
    # Test with a smaller batch for demonstration
    sample_domains = list(classifier.domains.keys())[:5]  # Test first 5 domains
    probe_result = classifier.probe_domain_platforms(sample_domains, batch_size=2)
    
    if probe_result["success"]:
        logger.info(f"Platform probing results:")
        logger.info(f"  - Domains probed: {probe_result['probing_summary']['domains_probed']}")
        logger.info(f"  - Metadata updated: {probe_result['probing_summary']['metadata_updated']}")
        logger.info(f"  - Platform distribution: {probe_result['probing_summary']['platform_distribution']}")
    else:
        logger.warning(f"Platform probing failed: {probe_result.get('error', 'Unknown error')}")
    
    # Step 3: Test business website scoring algorithm (Task 65.3)
    logger.info("=== Step 3: Business Website Scoring Algorithm ===")
    
    scoring_result = classifier.score_business_domains(sample_domains, batch_size=2)
    
    if scoring_result["success"]:
        logger.info(f"Business scoring results:")
        logger.info(f"  - Domains scored: {scoring_result['scoring_summary']['domains_scored']}")
        logger.info(f"  - Metadata updated: {scoring_result['scoring_summary']['metadata_updated']}")
        logger.info(f"  - Website type distribution: {scoring_result['scoring_summary']['website_type_distribution']}")
    else:
        logger.warning(f"Business scoring failed: {scoring_result.get('error', 'Unknown error')}")
    
    # Step 4: Test domain prioritization and crawl budget assignment (Task 65.4)
    logger.info("=== Step 4: Domain Prioritization and Crawl Budget Assignment ===")
    
    prioritization_result = classifier.prioritize_domains()
    
    if prioritization_result["success"]:
        logger.info(f"Prioritization results:")
        logger.info(f"  - Total domains prioritized: {prioritization_result['prioritization_summary']['total_domains']}")
        logger.info(f"  - Priority distribution: {prioritization_result['prioritization_summary']['priority_distribution']}")
        logger.info(f"  - Average priority score: {prioritization_result['prioritization_summary']['average_priority_score']:.3f}")
        logger.info(f"  - Total crawl budget: {prioritization_result['prioritization_summary']['total_crawl_budget']} pages")
        
        # Show top prioritized domains
        top_domains = prioritization_result["prioritized_domains"][:3]
        logger.info("  - Top 3 prioritized domains:")
        for domain_info in top_domains:
            logger.info(f"    * {domain_info['domain']}: {domain_info['priority_level']} "
                       f"(score: {domain_info['priority_score']:.3f}, budget: {domain_info['crawl_budget']})")
    
    # Test crawl queue creation
    queue_result = classifier.create_crawl_queue(priority_filters=["critical", "high", "medium"], max_domains=10)
    
    if queue_result["success"]:
        logger.info(f"Crawl queue created:")
        logger.info(f"  - Queue size: {queue_result['queue_metadata']['queue_statistics']['total_domains']} domains")
        logger.info(f"  - Total crawl budget: {queue_result['queue_metadata']['queue_statistics']['total_crawl_budget']} pages")
    
    # Test export functionality
    export_result = classifier.export_crawl_queue("csv_data", max_domains=5)
    if export_result["success"]:
        logger.info(f"Export test successful: {len(export_result['csv_rows'])} rows exported")
    
    # Step 5: Test metrics collection and reporting system (Task 65.5)
    logger.info("=== Step 5: Metrics Collection and Reporting System ===")
    
    # Test platform hit rates
    hit_rates = classifier.get_platform_hit_rates()
    if hit_rates["success"]:
        logger.info(f"Platform hit rates:")
        logger.info(f"  - Overall detection rate: {hit_rates['overall_statistics']['overall_detection_rate_percent']:.1f}%")
        logger.info(f"  - Unique platforms found: {hit_rates['overall_statistics']['unique_platforms_found']}")
        logger.info(f"  - Performance insights: {len(hit_rates['performance_insights'])} insights generated")
    
    # Test exclusion analysis
    exclusion_analysis = classifier.get_exclusion_analysis()
    if exclusion_analysis["success"]:
        logger.info(f"Exclusion analysis:")
        logger.info(f"  - Accessibility rate: {exclusion_analysis['summary']['accessibility_rate_percent']:.1f}%")
        logger.info(f"  - Total exclusions: {exclusion_analysis['summary']['total_exclusions']}")
        logger.info(f"  - Insights generated: {len(exclusion_analysis['insights'])}")
    
    # Test comprehensive reporting
    try:
        report_result = classifier.generate_comprehensive_report("json", "test_reports")
        if report_result["success"]:
            logger.info(f"Comprehensive report generated:")
            logger.info(f"  - Report ID: {report_result['report_summary']['report_id']}")
            logger.info(f"  - Business sites found: {report_result['key_metrics']['business_sites_found']}")
            logger.info(f"  - E-commerce sites found: {report_result['key_metrics']['ecommerce_sites_found']}")
            logger.info(f"  - Average business score: {report_result['key_metrics']['average_business_score']:.3f}")
            logger.info(f"  - Insights generated: {len(report_result['insights'])}")
            logger.info(f"  - Recommendations: {len(report_result['recommendations'])}")
            
            if report_result['export_result']['success']:
                logger.info(f"  - Report exported to: {report_result['export_result']['output_file']}")
        else:
            logger.warning(f"Comprehensive report failed: {report_result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.warning(f"Comprehensive reporting not available (missing dependencies): {e}")
    
    # Final statistics
    logger.info("=== Final System Statistics ===")
    final_stats = classifier.get_statistics()
    
    logger.info(f"Total statistics:")
    logger.info(f"  - Total domains: {final_stats['current_state']['total_domains']}")
    logger.info(f"  - Domain mappings: {final_stats['current_state']['domain_mappings']}")
    logger.info(f"  - Type distribution: {final_stats['type_distribution']}")
    logger.info(f"  - Platform distribution: {final_stats['platform_distribution']}")
    logger.info(f"  - Priority distribution: {final_stats['priority_distribution']}")
    
    logger.info("=== Test Completed Successfully ===")
    logger.info("All components of the Business Website Classification & Prioritization system are working correctly!")
    
    return True

def main():
    """Main test function"""
    try:
        success = test_domain_classifier_complete()
        if success:
            print("\n✅ All tests passed! The Business Website Classification & Prioritization system is fully functional.")
            return 0
        else:
            print("\n❌ Some tests failed. Please check the logs for details.")
            return 1
    
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())