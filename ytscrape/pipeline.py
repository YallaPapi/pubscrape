"""
End-to-End Pipeline Module
Orchestrates the complete YouTuber contact discovery workflow.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from .config import config
from .channel_fetcher import ChannelFetcher
from .data_normalizer import DataNormalizer
from .guest_scorer import GuestScorer
from .email_drafter import EmailDrafter
from .csv_compiler import CSVCompiler
from .error_handler import ErrorHandler
from .quota_manager import QuotaManager

logger = logging.getLogger(__name__)


class Pipeline:
    """Main pipeline orchestrating the YouTuber discovery process."""
    
    def __init__(self):
        """Initialize pipeline with all components."""
        logger.info("Initializing YouTuber Contact Discovery Pipeline")
        
        # Initialize components
        self.channel_fetcher = ChannelFetcher()
        self.data_normalizer = DataNormalizer()
        self.guest_scorer = None  # Initialized with topic
        self.email_drafter = None  # Initialized with podcast info
        self.csv_compiler = CSVCompiler()
        self.error_handler = ErrorHandler()
        self.quota_manager = QuotaManager()
        
        # Pipeline state
        self.raw_channels = []
        self.normalized_channels = []
        self.scored_channels = []
        self.final_channels = []
        self.output_file = None
        
    def run(self, 
            query: str,
            podcast_name: str = "Our Podcast",
            podcast_topic: str = "",
            host_name: str = "Host",
            max_channels: int = 20,
            min_score: int = 6,
            output_filename: str = None) -> str:
        """
        Run the complete pipeline from query to CSV.
        
        Args:
            query: YouTube search query for finding channels
            podcast_name: Name of the podcast
            podcast_topic: Topic/niche of the podcast
            host_name: Name of the host
            max_channels: Maximum channels to fetch
            min_score: Minimum score to include in output
            output_filename: Optional custom output filename
            
        Returns:
            Path to generated CSV file
        """
        print(f"\n{'='*60}")
        print(f"🚀 YouTuber Contact Discovery Pipeline")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"Podcast: {podcast_name}")
        print(f"Topic: {podcast_topic or query}")
        print(f"{'='*60}\n")
        
        try:
            # Step 1: Fetch channels from YouTube
            print(f"\n[Step 1/5] Fetching YouTube Channels")
            print(f"-" * 40)
            self.raw_channels = self.channel_fetcher.fetch_channels_for_topic(query, max_channels)
            
            if not self.raw_channels:
                logger.error("No channels found for query")
                print(f"❌ No channels found for query: {query}")
                return None
            
            # Step 2: Normalize channel data
            print(f"\n[Step 2/5] Normalizing Channel Data")
            print(f"-" * 40)
            self.normalized_channels = self.data_normalizer.normalize_batch(self.raw_channels)
            print(f"✅ Normalized {len(self.normalized_channels)} channels")
            
            # Print normalization statistics
            stats = self.data_normalizer.get_statistics(self.normalized_channels)
            print(f"  • Channels with website: {stats['channels_with_website']} ({stats['website_percentage']:.1f}%)")
            print(f"  • Channels with social: {stats['channels_with_social']} ({stats['social_percentage']:.1f}%)")
            print(f"  • Average subscribers: {stats['average_subscribers']}")
            
            # Step 3: Score channels with AI
            print(f"\n[Step 3/5] AI Guest Scoring")
            print(f"-" * 40)
            self.guest_scorer = GuestScorer(podcast_topic or query)
            self.scored_channels = self.guest_scorer.score_batch(self.normalized_channels, podcast_topic or query)
            
            # Print scoring summary
            summary = self.guest_scorer.get_scoring_summary(self.scored_channels)
            print(f"\n📊 Scoring Summary:")
            print(f"  • Average score: {summary['average_score']:.1f}/10")
            print(f"  • Excellent (8-10): {summary['excellent_guests']} channels")
            print(f"  • Good (6-7): {summary['good_guests']} channels")
            print(f"  • Fair (4-5): {summary['fair_guests']} channels")
            
            # Step 4: Generate outreach emails
            print(f"\n[Step 4/5] Generating Outreach Emails")
            print(f"-" * 40)
            self.email_drafter = EmailDrafter(podcast_name, podcast_topic or query, host_name)
            self.final_channels = self.email_drafter.draft_batch(
                self.scored_channels,
                podcast_name,
                podcast_topic or query,
                host_name
            )
            
            # Step 5: Compile to CSV
            print(f"\n[Step 5/5] Compiling CSV Output")
            print(f"-" * 40)
            
            # Filter by minimum score if specified
            if min_score > 0:
                self.output_file = self.csv_compiler.compile_filtered(
                    self.final_channels,
                    min_score,
                    output_filename
                )
            else:
                self.output_file = self.csv_compiler.compile_to_csv(
                    self.final_channels,
                    output_filename
                )
            
            # Generate markdown report
            report_file = self.csv_compiler.export_markdown_report(
                self.final_channels,
                output_filename
            )
            
            # Print final summary
            self._print_pipeline_summary()
            
            return self.output_file
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            print(f"\n❌ Pipeline Error: {e}")
            
            # Try error recovery
            if self.error_handler.handle_recoverable_error(e, "pipeline_main"):
                print("🔄 Attempting recovery...")
                return self.run(query, podcast_name, podcast_topic, host_name, 
                              max_channels, min_score, output_filename)
            else:
                print("❌ Pipeline failed after error recovery attempts")
                return None
    
    def run_with_config(self, config_dict: Dict[str, Any]) -> str:
        """
        Run pipeline with configuration dictionary.
        
        Args:
            config_dict: Configuration parameters
            
        Returns:
            Path to generated CSV
        """
        return self.run(
            query=config_dict.get("query"),
            podcast_name=config_dict.get("podcast_name", "Our Podcast"),
            podcast_topic=config_dict.get("podcast_topic", ""),
            host_name=config_dict.get("host_name", "Host"),
            max_channels=config_dict.get("max_channels", 20),
            min_score=config_dict.get("min_score", 6),
            output_filename=config_dict.get("output_filename")
        )
    
    def _print_pipeline_summary(self):
        """Print comprehensive pipeline execution summary."""
        print(f"\n{'='*60}")
        print(f"✅ Pipeline Complete!")
        print(f"{'='*60}")
        
        if self.output_file:
            print(f"\n📁 Output Files:")
            print(f"  • CSV: {self.output_file}")
            print(f"  • Report: {self.output_file.replace('.csv', '.md')}")
        
        # Quota usage
        quota_status = self.quota_manager.get_quota_status()
        print(f"\n📊 Quota Usage:")
        print(f"  • Used: {quota_status['used']}/{quota_status['total']} units")
        print(f"  • Remaining: {quota_status['remaining']} units")
        
        # Error status
        error_status = self.error_handler.get_error_status()
        if error_status['active_errors'] > 0:
            print(f"\n⚠️  Errors Encountered:")
            print(f"  • Active errors: {error_status['active_errors']}")
            print(f"  • Blocked errors: {error_status['blocked_errors']}")
        
        print(f"\n🎉 Ready for outreach!")
    
    def get_pipeline_state(self) -> Dict[str, Any]:
        """Get current pipeline state and statistics."""
        return {
            "raw_channels": len(self.raw_channels),
            "normalized_channels": len(self.normalized_channels),
            "scored_channels": len(self.scored_channels),
            "final_channels": len(self.final_channels),
            "output_file": self.output_file,
            "quota_status": self.quota_manager.get_quota_status(),
            "error_status": self.error_handler.get_error_status()
        }
    
    def reset(self):
        """Reset pipeline state for new run."""
        self.raw_channels = []
        self.normalized_channels = []
        self.scored_channels = []
        self.final_channels = []
        self.output_file = None
        logger.info("Pipeline state reset")