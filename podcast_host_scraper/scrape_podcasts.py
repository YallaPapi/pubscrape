#!/usr/bin/env python3
"""
Command-line interface for the Podcast Host Contact Scraper.

Usage:
    python scrape_podcasts.py --topic "artificial intelligence" --limit 50
    python scrape_podcasts.py --topic "business" --platforms apple_podcasts --output results.csv
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import threading
import time

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from podcast_scraper.main import PodcastHostScraper
from podcast_scraper.config import config


class ProgressReporter:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self._stop = False
        self._thread = None
        self.progress_path = config.get_output_path("progress.json")
        self._lock = threading.Lock()

    def start(self):
        if not self.enabled:
            return
        def loop():
            beat = 0
            while not self._stop:
                beat += 1
                self._write({"heartbeat": beat, "timestamp": datetime.now().isoformat()})
                print("[LIVE] working...", flush=True)
                time.sleep(2)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def update(self, **fields):
        if not self.enabled:
            return
        payload = {"timestamp": datetime.now().isoformat(), **fields}
        self._write(payload)
        msg = fields.get("message")
        if msg:
            print(f"[LIVE] {msg}", flush=True)

    def stop(self):
        self._stop = True
        if self._thread:
            self._thread.join(timeout=1)

    def _write(self, data):
        try:
            with self._lock:
                with open(self.progress_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
        except Exception:
            pass


def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.get_output_path("scraper.log"))
        ],
        force=True
    )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Podcast Host Contact Scraper - Find podcast host contact information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find AI podcast hosts
  python scrape_podcasts.py --topic "artificial intelligence" --limit 100

  # Find business podcasters with custom output
  python scrape_podcasts.py --topic "business" --limit 50 --output business_podcasts.csv

  # Scrape specific platforms only
  python scrape_podcasts.py --topic "technology" --platforms apple_podcasts --limit 25

  # Enable debug logging
  python scrape_podcasts.py --topic "health" --log-level DEBUG

  # Full analysis with enhanced outputs
  python scrape_podcasts.py --topic "AI" --enrich-contacts --analyze-intelligence --enhanced-csv --comprehensive-report

  # Export all data formats
  python scrape_podcasts.py --topic "business" --enrich-contacts --enhanced-csv --export-json

Available topics: artificial intelligence, business, technology, health, education, 
                  science, entertainment, sports, news, comedy, etc.
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--topic", 
        required=True,
        help="Search topic (e.g., 'artificial intelligence', 'business', 'health')"
    )
    
    # Optional arguments
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of podcasts to scrape per platform (default: 100)"
    )
    
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["apple_podcasts"],
        choices=["apple_podcasts", "itunes_api", "spotify", "youtube", "podcast_index", "learnoutloud", "all"],
        help="Platforms to scrape (default: apple_podcasts, use 'all' for all platforms)"
    )
    
    parser.add_argument(
        "--output",
        help="Output CSV filename (default: podcast_contacts.csv)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating markdown report"
    )
    
    parser.add_argument(
        "--enrich-contacts",
        action="store_true", 
        help="Enable contact information enrichment (slower but finds emails/websites)"
    )
    
    parser.add_argument(
        "--analyze-intelligence",
        action="store_true",
        help="Enable podcast intelligence analysis (popularity, authority, guest potential)"
    )
    
    parser.add_argument(
        "--enhanced-csv",
        action="store_true",
        help="Export enhanced CSV with all intelligence metrics and contact analysis"
    )
    
    parser.add_argument(
        "--comprehensive-report",
        action="store_true",
        help="Generate comprehensive analytics report with detailed insights"
    )
    
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export all data to JSON format for advanced analysis"
    )
    
    parser.add_argument(
        "--monitor-performance",
        action="store_true",
        help="Enable real-time performance monitoring during scraping"
    )
    
    parser.add_argument(
        "--optimize-memory",
        action="store_true",
        help="Optimize memory usage after processing"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show live progress and write output/progress.json"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Podcast Host Contact Scraper 1.0.0"
    )
    
    return parser.parse_args()


def print_banner():
    """Print application banner."""
    banner = """
    ======================================================================
                       PODCAST HOST CONTACT SCRAPER                    
                                                                      
      100% Free, Open Source Tool for Podcast Guest Discovery          
      Find contact info for popular podcast hosts in any niche         
    ======================================================================
    """
    print(banner)


def print_config_info():
    """Print configuration and feature availability."""
    features = config.get_available_features()
    
    print("Configuration Status:")
    print(f"   • Output Directory: {config.OUTPUT_DIR}")
    print(f"   • Max Podcasts: {config.MAX_PODCASTS_PER_SEARCH}")
    
    print("\nAvailable Features:")
    for feature, available in features.items():
        status = "[OK]" if available else "[--]" 
        feature_name = feature.replace("_", " ").title()
        print(f"   {status} {feature_name}")
    
    # Show missing API key info
    missing_keys = []
    if not config.has_openai_key():
        missing_keys.append("OPENAI_API_KEY (for AI relevance scoring)")
    if not config.has_spotify_keys():
        missing_keys.append("SPOTIFY_CLIENT_ID/SECRET (for Spotify discovery)")
    if not config.has_google_search_keys():
        missing_keys.append("GOOGLE_CUSTOM_SEARCH_KEY (for website discovery)")
    
    if missing_keys:
        print(f"\nOptional API Keys (add to .env for extra features):")
        for key in missing_keys:
            print(f"   • {key}")


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set up environment
    if args.output_dir:
        config.OUTPUT_DIR = args.output_dir
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    reporter = ProgressReporter(args.progress)
    reporter.start()
    
    try:
        # Print banner and config
        print_banner()
        print_config_info()
        reporter.update(message="Initialized and printed config")
        
        # Initialize scraper
        try:
            print(f"\n[INIT] Initializing Podcast Host Contact Scraper...")
            scraper = PodcastHostScraper()
            if args.monitor_performance:
                print(f"[MONITOR] Starting performance monitoring...")
                scraper.start_performance_monitoring()
        except Exception as init_err:
            reporter.update(message=f"Init error: {init_err}")
            raise
        
        print(f"\n[SEARCH] Searching for '{args.topic}' podcasts...")
        print(f"   • Platforms: {', '.join(args.platforms)}")
        print(f"   • Limit: {args.limit} podcasts per platform")
        print(f"   • Output: {config.OUTPUT_DIR}/")
        reporter.update(stage="search", topic=args.topic, platforms=args.platforms, limit=args.limit)
        
        # Handle "all" platforms option
        platforms = args.platforms
        if "all" in platforms:
            platforms = ["apple_podcasts", "learnoutloud", "spotify", "youtube"]  # Exclude podcast_index as it's placeholder
        
        # Scrape podcasts
        podcasts = scraper.scrape_podcasts(
            topic=args.topic,
            limit=args.limit,
            platforms=platforms
        )
        reporter.update(stage="scrape_done", total=len(podcasts))
        
        if not podcasts:
            print(f"\n[ERROR] No podcasts found for topic: {args.topic}")
            print("[TIP] Try different topics like: 'business', 'technology', 'health', 'education'")
            sys.exit(1)
        
        print(f"\n[SUCCESS] Found {len(podcasts)} unique podcasts!")
        
        # Enrich with contact information if requested
        if args.enrich_contacts:
            print(f"\n[ENRICH] Discovering contact information...")
            print("   This may take a few minutes as we discover websites and extract contacts...")
            reporter.update(stage="enrich_start", count=len(podcasts))
            podcasts = scraper.enrich_with_contact_info(podcasts)
            reporter.update(stage="enrich_done")
            print(f"[ENRICH] Contact enrichment completed!")
        
        # Analyze intelligence if requested
        if args.analyze_intelligence:
            print(f"\n[ANALYZE] Performing podcast intelligence analysis...")
            print("   Analyzing popularity, authority, relevance, and guest potential...")
            reporter.update(stage="analyze_start")
            podcasts = scraper.analyze_podcast_intelligence(podcasts, args.topic)
            reporter.update(stage="analyze_done")
            print(f"[ANALYZE] Intelligence analysis completed!")
        
        # Export to CSV (enhanced or standard)
        print(f"\n[EXPORT] Exporting results to CSV...")
        if args.enhanced_csv and (args.enrich_contacts or args.analyze_intelligence):
            print(f"   Using enhanced CSV format with intelligence and contact analysis...")
            csv_path = scraper.export_enhanced_csv(podcasts, args.output)
        else:
            csv_path = scraper.export_to_csv(podcasts, args.output)
        reporter.update(stage="export_done", csv=csv_path)
        
        # Generate comprehensive report if requested
        if args.comprehensive_report and (args.enrich_contacts or args.analyze_intelligence):
            print(f"[REPORT] Generating comprehensive analytics report...")
            comprehensive_report_path = scraper.generate_comprehensive_report(podcasts, args.topic)
            reporter.update(stage="report_done", report=comprehensive_report_path)
        
        # Generate standard report (unless disabled or comprehensive report generated)
        if not args.no_report and not args.comprehensive_report:
            print(f"[REPORT] Generating summary report...")
            report_path = scraper.generate_report(podcasts)
            reporter.update(stage="report_done", report=report_path)
        
        # Export JSON data if requested
        if args.export_json:
            print(f"[JSON] Exporting data to JSON format...")
            json_path = scraper.export_json_data(podcasts)
            reporter.update(stage="json_done", json=json_path)
        
        # Optimize memory if requested
        if args.optimize_memory:
            print(f"[OPTIMIZE] Optimizing memory usage...")
            optimization_stats = scraper.optimize_memory()
            print(f"   Memory freed: {optimization_stats['gc_stats']['memory_freed_mb']:.1f} MB")
        
        # Stop performance monitoring and show summary
        if args.monitor_performance:
            print(f"[MONITOR] Stopping performance monitoring...")
            scraper.stop_performance_monitoring()
            perf_summary = scraper.get_performance_summary()
            print(f"   Average CPU: {perf_summary['cpu']['avg']:.1f}%")
            print(f"   Average Memory: {perf_summary['memory']['avg']:.1f}%")
        
        # Show statistics
        stats = scraper.get_statistics()
        print(f"\n[STATS] Scraping Results:")
        print(f"   • Total Podcasts: {stats['total']}")
        print(f"   • With Host Names: {stats['with_host_names']} ({stats['host_name_rate']})")
        print(f"   • With Email Contacts: {stats['with_emails']} ({stats['email_rate']})")  
        print(f"   • With Websites: {stats['with_websites']} ({stats['website_rate']})")
        
        # Show output files
        print(f"\n[FILES] Output Files:")
        print(f"   • CSV: {csv_path}")
        if args.comprehensive_report and (args.enrich_contacts or args.analyze_intelligence):
            print(f"   • Comprehensive Report: {comprehensive_report_path}")
        elif not args.no_report:
            print(f"   • Report: {report_path}")
        if args.export_json:
            print(f"   • JSON Data: {json_path}")
        
        # Show top results preview
        print(f"\n[PREVIEW] Top 5 Results Preview:")
        for i, podcast in enumerate(podcasts[:5], 1):
            email_status = "[E]" if (podcast.host_email or podcast.booking_email) else "[-]"
            website_status = "[W]" if podcast.podcast_website else "[-]"
            host = podcast.host_name or "Unknown Host"
            
            print(f"   {i}. {podcast.podcast_name}")
            print(f"      Host: {host} {email_status} {website_status}")
        
        if len(podcasts) > 5:
            print(f"   ... and {len(podcasts) - 5} more podcasts in the CSV file")
        
        print(f"\n[DONE] Scraping completed successfully!")
        print(f"[TIP] Open {os.path.basename(csv_path)} to see all contact details")
    except KeyboardInterrupt:
        print(f"\n[STOP] Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"\n[ERROR] Error: {e}")
        print(f"[TIP] Check the log file for details: {config.get_output_path('scraper.log')}")
        sys.exit(1)
    finally:
        reporter.stop()


if __name__ == "__main__":
    main()