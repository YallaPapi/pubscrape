#!/usr/bin/env python3
"""
Bulk processing CLI for the Podcast Host Contact Scraper.
Handles large-scale podcast discovery operations with performance optimization.

Usage:
    python bulk_scrape_podcasts.py --topics-file topics.txt --output-dir bulk_results
    python bulk_scrape_podcasts.py --topics "AI,business,tech" --limit 50 --workers 8
"""

import argparse
import logging
import sys
import os
import json
from pathlib import Path
from typing import List

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from podcast_scraper.bulk_processing import BulkPodcastProcessor, create_progress_bar_callback, estimate_processing_time
from podcast_scraper.config import config


def setup_logging(log_level: str = "INFO", log_file: str = "bulk_scraper.log"):
    """Set up logging configuration for bulk processing."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / log_file)
        ]
    )


def parse_arguments():
    """Parse command line arguments for bulk processing."""
    parser = argparse.ArgumentParser(
        description="Bulk Podcast Host Contact Scraper - Process multiple topics efficiently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bulk process from topics file
  python bulk_scrape_podcasts.py --topics-file topics.txt --limit 100 --workers 8

  # Process specific topics
  python bulk_scrape_podcasts.py --topics "artificial intelligence,business,health" --limit 50

  # Full analysis with all features
  python bulk_scrape_podcasts.py --topics "AI,tech,startup" --enrich-contacts --analyze-intelligence --enhanced-csv

  # Large scale processing with optimization
  python bulk_scrape_podcasts.py --topics-file large_topics.txt --workers 12 --use-cache --optimize-memory

Topics file format (one topic per line):
  artificial intelligence
  business and entrepreneurship
  health and wellness
  technology trends
  personal development
        """
    )
    
    # Topic input options
    topic_group = parser.add_mutually_exclusive_group(required=True)
    topic_group.add_argument(
        "--topics",
        help="Comma-separated list of topics to process"
    )
    topic_group.add_argument(
        "--topics-file",
        help="Path to file containing topics (one per line)"
    )
    
    # Processing options
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of podcasts to scrape per topic (default: 100)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent workers (default: 4, max recommended: 8)"
    )
    
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["apple_podcasts"],
        choices=["apple_podcasts", "spotify", "youtube", "podcast_index", "all"],
        help="Platforms to scrape (default: apple_podcasts)"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir",
        default="bulk_output",
        help="Output directory for results (default: bulk_output)"
    )
    
    parser.add_argument(
        "--export-format",
        choices=["csv", "enhanced_csv", "json", "all"],
        default="enhanced_csv",
        help="Export format (default: enhanced_csv)"
    )
    
    # Feature flags
    parser.add_argument(
        "--enrich-contacts",
        action="store_true",
        help="Enable contact information enrichment (slower but more complete)"
    )
    
    parser.add_argument(
        "--analyze-intelligence",
        action="store_true",
        help="Enable podcast intelligence analysis (popularity, authority, guest potential)"
    )
    
    parser.add_argument(
        "--enhanced-csv",
        action="store_true",
        help="Export enhanced CSV with all metrics (requires --enrich-contacts or --analyze-intelligence)"
    )
    
    # Performance options
    parser.add_argument(
        "--use-cache",
        action="store_true",
        default=True,
        help="Use intelligent caching for better performance (default: enabled)"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (forces fresh data but slower)"
    )
    
    parser.add_argument(
        "--optimize-memory",
        action="store_true",
        help="Enable aggressive memory optimization (recommended for large batches)"
    )
    
    # Monitoring options
    parser.add_argument(
        "--progress-bar",
        action="store_true",
        default=True,
        help="Show progress bar (default: enabled)"
    )
    
    parser.add_argument(
        "--estimate-time",
        action="store_true",
        help="Estimate processing time before starting"
    )
    
    parser.add_argument(
        "--export-stats",
        action="store_true",
        help="Export performance statistics to JSON"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        default="bulk_scraper.log",
        help="Log file name (default: bulk_scraper.log)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Bulk Podcast Host Contact Scraper 1.0.0"
    )
    
    return parser.parse_args()


def load_topics_from_file(file_path: str) -> List[str]:
    """Load topics from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            topics = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return topics
    except FileNotFoundError:
        print(f"Error: Topics file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading topics file: {e}")
        sys.exit(1)


def print_banner():
    """Print application banner."""
    banner = """
    ======================================================================
                       BULK PODCAST HOST CONTACT SCRAPER                    
                                                                      
      High-Performance Batch Processing for Large-Scale Discovery          
      Process hundreds of topics with intelligent optimization         
    ======================================================================
    """
    print(banner)


def print_configuration(args, topics: List[str]):
    """Print processing configuration."""
    print("Bulk Processing Configuration:")
    print(f"   • Topics: {len(topics)} topics to process")
    print(f"   • Limit: {args.limit} podcasts per topic")
    print(f"   • Workers: {args.workers} concurrent workers")
    print(f"   • Platforms: {', '.join(args.platforms)}")
    print(f"   • Output: {args.output_dir}/")
    print(f"   • Export Format: {args.export_format}")
    
    print("\nProcessing Features:")
    print(f"   • Contact Enrichment: {'✓' if args.enrich_contacts else '✗'}")
    print(f"   • Intelligence Analysis: {'✓' if args.analyze_intelligence else '✗'}")
    print(f"   • Enhanced CSV: {'✓' if args.enhanced_csv else '✗'}")
    print(f"   • Caching: {'✓' if args.use_cache and not args.no_cache else '✗'}")
    print(f"   • Memory Optimization: {'✓' if args.optimize_memory else '✗'}")


def main():
    """Main entry point for bulk processing."""
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    # Print banner
    print_banner()
    
    # Load topics
    if args.topics:
        topics = [topic.strip() for topic in args.topics.split(',') if topic.strip()]
    else:
        topics = load_topics_from_file(args.topics_file)
    
    if not topics:
        print("Error: No topics to process")
        sys.exit(1)
    
    # Validate arguments
    if args.workers > 12:
        print("Warning: Using more than 12 workers may cause rate limiting issues")
        args.workers = 12
    
    if args.enhanced_csv and not (args.enrich_contacts or args.analyze_intelligence):
        print("Warning: Enhanced CSV requires --enrich-contacts or --analyze-intelligence")
        args.export_format = "csv"
    
    # Handle cache settings
    use_cache = args.use_cache and not args.no_cache
    
    # Print configuration
    print_configuration(args, topics)
    
    # Estimate processing time if requested
    if args.estimate_time:
        print("\nProcessing Time Estimation:")
        time_estimate = estimate_processing_time(
            num_topics=len(topics),
            limit_per_topic=args.limit,
            enrich_contacts=args.enrich_contacts,
            analyze_intelligence=args.analyze_intelligence,
            max_workers=args.workers
        )
        
        print(f"   • Estimated Time: {time_estimate['estimated_minutes']:.1f} minutes")
        print(f"   • Time per Topic: {time_estimate['time_per_topic']:.1f} seconds")
        print(f"   • Parallelization Factor: {time_estimate['parallelization_factor']}x")
        
        confirm = input("\nContinue with processing? (y/N): ")
        if confirm.lower() != 'y':
            print("Processing cancelled")
            sys.exit(0)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    try:
        print(f"\n[INIT] Initializing bulk processor...")
        
        # Initialize bulk processor
        processor = BulkPodcastProcessor(
            max_workers=args.workers,
            use_cache=use_cache
        )
        
        # Set up progress tracking
        if args.progress_bar:
            progress_callback = create_progress_bar_callback()
            processor.add_progress_callback(progress_callback)
        
        print(f"\n[START] Starting bulk processing...")
        print(f"   Processing {len(topics)} topics with {args.workers} workers")
        
        # Handle platforms
        platforms = args.platforms
        if "all" in platforms:
            platforms = ["apple_podcasts", "spotify", "youtube"]
        
        # Process all topics
        results = processor.process_multiple_topics(
            topics=topics,
            limit_per_topic=args.limit,
            platforms=platforms,
            enrich_contacts=args.enrich_contacts,
            analyze_intelligence=args.analyze_intelligence
        )
        
        # Memory optimization if requested
        if args.optimize_memory:
            print(f"\n[OPTIMIZE] Optimizing memory usage...")
            processor.optimize_memory_usage()
        
        # Export results
        print(f"\n[EXPORT] Exporting results...")
        exported_files = processor.export_bulk_results(
            results=results,
            output_dir=args.output_dir,
            export_format=args.export_format
        )
        
        # Show final statistics
        stats = processor.get_performance_stats()
        print(f"\n[STATS] Bulk Processing Results:")
        print(f"   • Total Topics: {stats['progress']['total_queries']}")
        print(f"   • Completed: {stats['progress']['completed_queries']}")
        print(f"   • Failed: {stats['progress']['failed_queries']}")
        print(f"   • Success Rate: {(stats['progress']['completed_queries']/stats['progress']['total_queries']*100):.1f}%")
        print(f"   • Total Podcasts Found: {stats['progress']['total_podcasts_found']}")
        print(f"   • Processing Time: {stats['progress']['elapsed_time']}")
        
        # Show exported files
        print(f"\n[FILES] Exported Files ({len(exported_files)}):")
        for file_type, file_path in exported_files.items():
            file_name = os.path.basename(file_path)
            print(f"   • {file_type}: {file_name}")
        
        # Export performance stats if requested
        if args.export_stats:
            stats_file = output_dir / "performance_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            print(f"   • Performance Stats: {stats_file.name}")
        
        # Show top results summary
        total_podcasts = sum(len(podcasts) for podcasts in results.values())
        if total_podcasts > 0:
            print(f"\n[SUMMARY] Discovered {total_podcasts} podcasts across {len(topics)} topics")
            
            # Show best performing topics
            topic_results = [(topic, len(podcasts)) for topic, podcasts in results.items()]
            topic_results.sort(key=lambda x: x[1], reverse=True)
            
            print(f"\nTop Performing Topics:")
            for i, (topic, count) in enumerate(topic_results[:5], 1):
                print(f"   {i}. {topic}: {count} podcasts")
        
        print(f"\n[DONE] Bulk processing completed successfully!")
        print(f"[TIP] Check {args.output_dir}/ for all exported files")
        
        # Shutdown processor
        processor.shutdown()
        
    except KeyboardInterrupt:
        print(f"\n[STOP] Bulk processing interrupted by user")
        if 'processor' in locals():
            processor.shutdown()
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Bulk processing failed: {e}")
        print(f"\n[ERROR] Processing failed: {e}")
        print(f"[TIP] Check the log file for details: logs/{args.log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()