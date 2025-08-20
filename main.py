"""
YouTuber Contact Discovery Agent - Main CLI
"""

import argparse
import sys
import logging
from typing import Optional

# Add project to path
sys.path.insert(0, '.')

from ytscrape import Pipeline


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure basic logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="YouTuber Contact Discovery Agent - Find and score potential podcast guests from YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "AI researchers" --podcast "Tech Talk" --topic "artificial intelligence"
  python main.py "startup founders" --max 30 --min-score 7
  python main.py "fitness coaches" --podcast "Health Heroes" --host "John Smith"
        """
    )
    
    # Required arguments
    parser.add_argument(
        "query",
        help="YouTube search query for finding channels (e.g., 'AI researchers', 'startup founders')"
    )
    
    # Podcast information
    parser.add_argument(
        "--podcast",
        default="Our Podcast",
        help="Name of your podcast (default: Our Podcast)"
    )
    
    parser.add_argument(
        "--topic",
        default="",
        help="Podcast topic/niche for better scoring (default: uses query)"
    )
    
    parser.add_argument(
        "--host",
        default="Host",
        help="Name of the podcast host (default: Host)"
    )
    
    # Pipeline configuration
    parser.add_argument(
        "--max",
        type=int,
        default=20,
        help="Maximum number of channels to fetch (default: 20)"
    )
    
    parser.add_argument(
        "--min-score",
        type=int,
        default=6,
        help="Minimum guest score to include in output (default: 6)"
    )
    
    parser.add_argument(
        "--output",
        default=None,
        help="Custom output filename (default: auto-generated with timestamp)"
    )
    
    # Other options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check configuration without running pipeline"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Print header
    print("\n" + "="*60)
    print("🎙️  YouTuber Contact Discovery Agent")
    print("="*60)
    
    if args.dry_run:
        print("\n🔍 Configuration Check (Dry Run)")
        print(f"  • Query: {args.query}")
        print(f"  • Podcast: {args.podcast}")
        print(f"  • Topic: {args.topic or args.query}")
        print(f"  • Host: {args.host}")
        print(f"  • Max channels: {args.max}")
        print(f"  • Min score: {args.min_score}")
        print(f"  • Output: {args.output or 'auto-generated'}")
        print("\n✅ Configuration valid. Remove --dry-run to execute.")
        return 0
    
    try:
        # Initialize and run pipeline
        pipeline = Pipeline()
        
        output_file = pipeline.run(
            query=args.query,
            podcast_name=args.podcast,
            podcast_topic=args.topic or args.query,
            host_name=args.host,
            max_channels=args.max,
            min_score=args.min_score,
            output_filename=args.output
        )
        
        if output_file:
            print(f"\n✅ Success! Output saved to: {output_file}")
            print(f"📄 Report saved to: {output_file.replace('.csv', '.md')}")
            return 0
        else:
            print("\n❌ Pipeline failed to generate output")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())