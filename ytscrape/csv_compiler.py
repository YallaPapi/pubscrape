"""
CSV Compiler Module
Compiles channel data into CSV format matching the exact schema.
"""

import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from .config import config
from .data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class CSVCompiler:
    """Compiles channel data into CSV format."""
    
    def __init__(self):
        """Initialize CSV compiler."""
        self.schema = config.CSV_SCHEMA
        self.normalizer = DataNormalizer()
        self.output_dir = config.OUTPUT_DIR
        
    def compile_to_csv(self, channels: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Compile channels data to CSV file.
        
        Args:
            channels: List of processed channel data
            filename: Optional custom filename
            
        Returns:
            Path to the generated CSV file
        """
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_contacts_{timestamp}.csv"
        
        # Ensure .csv extension
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare data for CSV
        csv_data = self.normalizer.prepare_for_csv(channels)
        
        # Validate all rows have correct schema
        validated_data = self._validate_schema(csv_data)
        
        # Write to CSV
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.schema, quoting=csv.QUOTE_ALL)
                
                # Write header
                writer.writeheader()
                
                # Write data rows
                writer.writerows(validated_data)
            
            logger.info(f"CSV compiled successfully: {filepath}")
            print(f"✅ CSV saved: {filepath}")
            
            # Generate summary
            self._print_summary(validated_data, filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error writing CSV: {e}")
            raise Exception(f"Failed to compile CSV: {e}")
    
    def _validate_schema(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and ensure all rows match the schema exactly.
        
        Args:
            data: List of channel data
            
        Returns:
            Validated data with correct schema
        """
        validated = []
        
        for row in data:
            # Create new row with exact schema fields in order
            validated_row = {}
            for field in self.schema:
                if field in row:
                    validated_row[field] = row[field]
                else:
                    # Add NA for missing fields
                    validated_row[field] = "NA"
                    logger.warning(f"Missing field {field} in row, using NA")
            
            validated.append(validated_row)
        
        return validated
    
    def compile_filtered(self, channels: List[Dict[str, Any]], 
                         min_score: int = 6,
                         filename: str = None) -> str:
        """
        Compile only channels meeting minimum score threshold.
        
        Args:
            channels: List of scored channels
            min_score: Minimum guest score to include
            filename: Optional custom filename
            
        Returns:
            Path to generated CSV
        """
        # Filter channels by score
        filtered = [c for c in channels if int(c.get("GuestScore", "0")) >= min_score]
        
        logger.info(f"Compiling {len(filtered)} channels with score >= {min_score}")
        
        if not filtered:
            logger.warning("No channels meet the minimum score threshold")
            print(f"⚠️  No channels with score >= {min_score} to compile")
            return None
        
        # Add min score to filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_contacts_min{min_score}_{timestamp}.csv"
        
        return self.compile_to_csv(filtered, filename)
    
    def compile_top_n(self, channels: List[Dict[str, Any]], 
                      n: int = 10,
                      filename: str = None) -> str:
        """
        Compile only top N channels by score.
        
        Args:
            channels: List of scored channels
            n: Number of top channels to include
            filename: Optional custom filename
            
        Returns:
            Path to generated CSV
        """
        # Sort by score and take top N
        sorted_channels = sorted(channels, 
                                key=lambda x: int(x.get("GuestScore", "0")), 
                                reverse=True)
        top_channels = sorted_channels[:n]
        
        logger.info(f"Compiling top {len(top_channels)} channels")
        
        # Add top N to filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_contacts_top{n}_{timestamp}.csv"
        
        return self.compile_to_csv(top_channels, filename)
    
    def _print_summary(self, data: List[Dict[str, Any]], filepath: str):
        """
        Print summary of compiled CSV.
        
        Args:
            data: Compiled data
            filepath: Path to CSV file
        """
        if not data:
            return
        
        # Calculate statistics
        total = len(data)
        scores = [int(row.get("GuestScore", "0")) for row in data]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Count channels with emails
        with_emails = sum(1 for row in data 
                         if row.get("DraftEmail", "NA") != "NA" 
                         and "too low" not in row.get("DraftEmail", ""))
        
        # Get file size
        file_size = os.path.getsize(filepath) / 1024  # KB
        
        print(f"\n📊 CSV Summary:")
        print(f"  • Total channels: {total}")
        print(f"  • Average score: {avg_score:.1f}/10")
        print(f"  • Channels with emails: {with_emails}")
        print(f"  • File size: {file_size:.1f} KB")
        print(f"  • Location: {filepath}")
        
        # Show top 3 channels
        if total > 0:
            print(f"\n🏆 Top 3 Channels:")
            for i, row in enumerate(data[:3], 1):
                name = row.get("ChannelName", "Unknown")[:40]
                score = row.get("GuestScore", "NA")
                subs = row.get("SubscriberCount", "NA")
                print(f"  {i}. {name} (Score: {score}, Subs: {subs})")
    
    def export_markdown_report(self, channels: List[Dict[str, Any]], 
                              filename: str = None) -> str:
        """
        Export a markdown report alongside the CSV.
        
        Args:
            channels: List of processed channels
            filename: Optional custom filename
            
        Returns:
            Path to markdown report
        """
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_contacts_report_{timestamp}.md"
        
        if not filename.endswith('.md'):
            filename = filename.replace('.csv', '.md')
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Generate report content
        report = self._generate_markdown_report(channels)
        
        # Write report
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Markdown report generated: {filepath}")
        return filepath
    
    def _generate_markdown_report(self, channels: List[Dict[str, Any]]) -> str:
        """
        Generate markdown report content.
        
        Args:
            channels: List of channels
            
        Returns:
            Markdown report string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = len(channels)
        
        # Calculate statistics
        scores = [int(c.get("GuestScore", "0")) for c in channels]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        report = f"""# YouTube Contact Discovery Report
        
Generated: {timestamp}

## Summary Statistics

- **Total Channels Found**: {total}
- **Average Guest Score**: {avg_score:.1f}/10
- **Excellent Candidates (8-10)**: {sum(1 for s in scores if s >= 8)}
- **Good Candidates (6-7)**: {sum(1 for s in scores if 6 <= s < 8)}
- **Fair Candidates (4-5)**: {sum(1 for s in scores if 4 <= s < 6)}
- **Poor Candidates (1-3)**: {sum(1 for s in scores if s < 4)}

## Top 10 Podcast Guest Candidates

| Rank | Channel Name | Subscribers | Score | Reason |
|------|-------------|-------------|-------|---------|
"""
        
        # Add top 10 channels
        sorted_channels = sorted(channels, 
                               key=lambda x: int(x.get("GuestScore", "0")), 
                               reverse=True)
        
        for i, channel in enumerate(sorted_channels[:10], 1):
            name = channel.get("ChannelName", "Unknown")[:30]
            subs = channel.get("SubscriberCount", "NA")
            score = channel.get("GuestScore", "NA")
            reason = channel.get("ScoreReason", "NA")[:50]
            
            report += f"| {i} | {name} | {subs} | {score}/10 | {reason}... |\n"
        
        report += "\n## Channel Distribution\n\n"
        report += "### By Score\n"
        for score in range(10, 0, -1):
            count = scores.count(score)
            if count > 0:
                bar = "█" * count
                report += f"- Score {score}: {bar} ({count})\n"
        
        return report