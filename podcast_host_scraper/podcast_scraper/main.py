"""
Main podcast host contact scraper class.
Coordinates all platform scrapers and contact extraction.
"""

import csv
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import PodcastData
from .platforms.apple_podcasts import ApplePodcastsScraper
from .platforms.spotify import SpotifyPodcastsScraper
from .platforms.google_podcasts import GooglePodcastsScraper, PodcastIndexScraper
from .platforms.learnoutloud import LearnOutLoudScraper
from .platforms.itunes_api import ITunesApiScraper
from .contact_discovery import ContactPageDiscovery
from .intelligence_analysis import PodcastIntelligenceAnalyzer, TopicRelevanceAnalyzer
from .advanced_contact_enrichment import AdvancedContactEnricher, ContactQualityScorer
from .enhanced_reporting import EnhancedCSVExporter, ComprehensiveReporter
from .performance_monitor import PerformanceMonitor, MemoryOptimizer
from .config import config

logger = logging.getLogger(__name__)


class PodcastHostScraper:
    """Main scraper that coordinates all platforms and features."""
    
    def __init__(self):
        """Initialize the podcast host scraper."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize platform scrapers
        self.scrapers = {
            "apple_podcasts": ApplePodcastsScraper(),
            "spotify": SpotifyPodcastsScraper(),
            "youtube": GooglePodcastsScraper(),
            "podcast_index": PodcastIndexScraper(),
            "learnoutloud": LearnOutLoudScraper(),
            "itunes_api": ITunesApiScraper(),
        }
        
        # Initialize contact discovery
        self.contact_discovery = ContactPageDiscovery()
        
        # Initialize intelligence analysis
        self.intelligence_analyzer = PodcastIntelligenceAnalyzer()
        self.relevance_analyzer = TopicRelevanceAnalyzer()
        
        # Initialize advanced contact enrichment
        self.advanced_enricher = AdvancedContactEnricher()
        self.contact_scorer = ContactQualityScorer()
        
        # Initialize enhanced reporting
        self.enhanced_csv_exporter = EnhancedCSVExporter()
        self.comprehensive_reporter = ComprehensiveReporter()
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # Storage for scraped data
        self.all_podcasts: List[PodcastData] = []
        
        self.logger.info("Podcast Host Scraper initialized")
        self._log_available_features()
    
    def scrape_podcasts(
        self,
        topic: str,
        limit: int = 100,
        platforms: Optional[List[str]] = None
    ) -> List[PodcastData]:
        """
        Scrape podcasts from multiple platforms.
        
        Args:
            topic: Search topic (e.g., "artificial intelligence")
            limit: Maximum podcasts per platform
            platforms: List of platforms to scrape (default: all available)
            
        Returns:
            List of PodcastData objects
        """
        if platforms is None:
            platforms = list(self.scrapers.keys())
        
        self.logger.info(f"Starting podcast scrape for topic: '{topic}'")
        self.logger.info(f"Platforms: {platforms}, Limit: {limit} per platform")
        
        all_results = []
        
        for platform_name in platforms:
            if platform_name not in self.scrapers:
                self.logger.warning(f"Unknown platform: {platform_name}")
                continue
            
            try:
                self.logger.info(f"\n--- Scraping {platform_name} ---")
                scraper = self.scrapers[platform_name]
                
                platform_results = scraper.scrape_podcasts(topic, limit)
                all_results.extend(platform_results)
                
                # Log platform statistics
                stats = scraper.get_statistics()
                self.logger.info(f"{platform_name} results: {stats}")
                
            except Exception as e:
                self.logger.error(f"Error scraping {platform_name}: {e}")
                continue
        
        # Remove duplicates (same podcast from multiple platforms)
        unique_results = self._deduplicate_podcasts(all_results)
        
        self.all_podcasts = unique_results
        self.logger.info(f"Total unique podcasts found: {len(unique_results)}")
        
        return unique_results
    
    def enrich_with_contact_info(self, podcasts: List[PodcastData]) -> List[PodcastData]:
        """
        Enrich podcast data with contact information.
        
        Args:
            podcasts: List of podcasts to enrich
            
        Returns:
            List of enriched podcasts
        """
        self.logger.info(f"Starting contact enrichment for {len(podcasts)} podcasts")
        
        enriched_podcasts = []
        
        for i, podcast in enumerate(podcasts):
            try:
                self.logger.info(f"Enriching contact info for podcast {i+1}/{len(podcasts)}: {podcast.podcast_name}")
                
                # Discover website if not already present
                if not podcast.podcast_website:
                    website_url = self.contact_discovery.discover_website(podcast)
                    if website_url:
                        podcast.podcast_website = website_url
                        self.logger.info(f"Found website: {website_url}")
                
                # Find contact pages and extract contact info
                if podcast.podcast_website:
                    contact_pages = self.contact_discovery.find_contact_pages(podcast.podcast_website)
                    self.logger.debug(f"Found {len(contact_pages)} contact pages")
                    
                    # Use the first contact page or the main website
                    contact_url = contact_pages[0] if contact_pages else podcast.podcast_website
                    podcast.contact_page_url = contact_url
                    
                    # Extract contact information
                    contact_info = self.contact_discovery.extract_contact_info(contact_url)
                    
                    # Update podcast with extracted contact info
                    if contact_info['emails']:
                        # Use the first email as the primary host email
                        podcast.host_email = contact_info['emails'][0]
                        # If there are multiple emails, use the second as booking email
                        if len(contact_info['emails']) > 1:
                            podcast.booking_email = contact_info['emails'][1]
                        
                        self.logger.info(f"Found {len(contact_info['emails'])} email(s)")
                    
                    # Update social links
                    if contact_info['social_links']:
                        if not podcast.social_links:
                            podcast.social_links = {}
                        podcast.social_links.update(contact_info['social_links'])
                        self.logger.debug(f"Found social links: {list(contact_info['social_links'].keys())}")
                    
                    # Set contact confidence based on what we found
                    if podcast.host_email:
                        podcast.contact_confidence = "high"
                    elif contact_info['contact_forms'] or contact_info['social_links']:
                        podcast.contact_confidence = "medium"
                    elif podcast.podcast_website:
                        podcast.contact_confidence = "low"
                    else:
                        podcast.contact_confidence = "none"
                
                # Enrich with social media profiles
                podcast = self.contact_discovery.enrich_with_social_media(podcast)
                
                # Perform advanced contact enrichment and scoring
                advanced_enrichment = self.advanced_enricher.enrich_contact_comprehensive(podcast)
                contact_quality = self.contact_scorer.score_contact_portfolio(podcast)
                
                # Store advanced enrichment data
                if not podcast.raw_data:
                    podcast.raw_data = {}
                podcast.raw_data['advanced_contact_enrichment'] = advanced_enrichment
                podcast.raw_data['contact_quality_score'] = contact_quality
                
                # Update contact confidence with advanced scoring
                podcast.contact_confidence = contact_quality['contact_confidence']
                
                enriched_podcasts.append(podcast)
                
            except Exception as e:
                self.logger.warning(f"Error enriching contact info for {podcast.podcast_name}: {e}")
                # Still add the podcast even if enrichment fails
                enriched_podcasts.append(podcast)
                continue
        
        self.logger.info(f"Contact enrichment completed for {len(enriched_podcasts)} podcasts")
        return enriched_podcasts
    
    def analyze_podcast_intelligence(self, podcasts: List[PodcastData], topic: str = "") -> List[PodcastData]:
        """
        Analyze podcast intelligence and add scoring metrics.
        
        Args:
            podcasts: List of podcasts to analyze
            topic: Original search topic for relevance analysis
            
        Returns:
            List of podcasts with intelligence analysis added
        """
        self.logger.info(f"Starting intelligence analysis for {len(podcasts)} podcasts")
        
        analyzed_podcasts = []
        
        for i, podcast in enumerate(podcasts):
            try:
                self.logger.info(f"Analyzing podcast {i+1}/{len(podcasts)}: {podcast.podcast_name}")
                
                # Perform comprehensive intelligence analysis
                intelligence = self.intelligence_analyzer.analyze_podcast_intelligence(podcast, topic)
                
                # Store intelligence data in podcast
                if not podcast.raw_data:
                    podcast.raw_data = {}
                podcast.raw_data['intelligence'] = intelligence
                
                # Update main podcast fields with key metrics
                podcast.ai_relevance_score = int(intelligence['relevance_score'])
                
                # Add estimated downloads to description for visibility
                if intelligence['estimated_downloads'] != 'Unknown':
                    download_info = f" (Est. downloads: {intelligence['estimated_downloads']})"
                    if podcast.podcast_description:
                        if download_info not in podcast.podcast_description:
                            podcast.podcast_description += download_info
                    else:
                        podcast.podcast_description = f"Podcast with {intelligence['estimated_downloads']} estimated downloads"
                
                self.logger.info(f"Intelligence analysis completed. Overall score: {intelligence['overall_score']:.1f}")
                
                # Use AI for enhanced relevance analysis if available
                if config.has_openai_key() and topic:
                    ai_relevance = self.relevance_analyzer.analyze_ai_relevance(podcast, topic)
                    intelligence['ai_relevance_analysis'] = ai_relevance
                    # Update relevance score with AI input
                    if ai_relevance['score'] > 0:
                        # Weighted average of rule-based and AI score
                        combined_score = (intelligence['relevance_score'] * 0.6 + ai_relevance['score'] * 0.4)
                        intelligence['relevance_score'] = round(combined_score, 1)
                        podcast.ai_relevance_score = int(combined_score)
                
                analyzed_podcasts.append(podcast)
                
            except Exception as e:
                self.logger.warning(f"Error analyzing intelligence for {podcast.podcast_name}: {e}")
                # Still add the podcast even if analysis fails
                analyzed_podcasts.append(podcast)
                continue
        
        # Sort podcasts by overall intelligence score (highest first)
        analyzed_podcasts.sort(key=lambda p: p.raw_data.get('intelligence', {}).get('overall_score', 0), reverse=True)
        
        self.logger.info(f"Intelligence analysis completed for {len(analyzed_podcasts)} podcasts")
        return analyzed_podcasts
    
    def export_to_csv(
        self,
        podcasts: Optional[List[PodcastData]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Export podcasts to CSV file.
        
        Args:
            podcasts: List of podcasts to export (default: all scraped)
            filename: Output filename (default: from config)
            
        Returns:
            Path to exported CSV file
        """
        if podcasts is None:
            podcasts = self.all_podcasts
        
        if not podcasts:
            raise ValueError("No podcasts to export")
        
        # Get output path
        output_path = config.get_output_path(filename)
        
        self.logger.info(f"Exporting {len(podcasts)} podcasts to {output_path}")
        
        # Prepare CSV data
        csv_data = []
        for podcast in podcasts:
            row = {}
            
            # Map PodcastData fields to CSV columns
            for column in config.CSV_COLUMNS:
                if hasattr(podcast, column):
                    value = getattr(podcast, column)
                    
                    # Handle special formatting
                    if column == "social_links" and isinstance(value, dict):
                        # Format social links as "platform: url, platform: url"
                        formatted_links = []
                        for platform, url in value.items():
                            if url:
                                formatted_links.append(f"{platform}: {url}")
                        row[column] = ", ".join(formatted_links) if formatted_links else ""
                    elif value is None:
                        row[column] = ""
                    else:
                        row[column] = str(value)
                else:
                    row[column] = ""
            
            csv_data.append(row)
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=config.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(csv_data)
        
        self.logger.info(f"CSV export completed: {output_path}")
        return output_path
    
    def export_enhanced_csv(
        self,
        podcasts: Optional[List[PodcastData]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Export podcasts to enhanced CSV with all intelligence and contact data.
        
        Args:
            podcasts: List of podcasts to export (default: all scraped)
            filename: Output filename (default: enhanced_podcast_contacts.csv)
            
        Returns:
            Path to exported enhanced CSV file
        """
        if podcasts is None:
            podcasts = self.all_podcasts
        
        if not podcasts:
            raise ValueError("No podcasts to export")
        
        return self.enhanced_csv_exporter.export_enhanced_csv(podcasts, filename)
    
    def generate_comprehensive_report(
        self,
        podcasts: Optional[List[PodcastData]] = None,
        topic: str = "",
        filename: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive analytics report with detailed insights.
        
        Args:
            podcasts: List of podcasts to report on (default: all scraped)
            topic: Search topic for context
            filename: Output filename (default: comprehensive_podcast_analysis.md)
            
        Returns:
            Path to generated comprehensive report file
        """
        if podcasts is None:
            podcasts = self.all_podcasts
        
        if not podcasts:
            raise ValueError("No podcasts to report on")
        
        return self.comprehensive_reporter.generate_comprehensive_report(podcasts, topic, filename)
    
    def export_json_data(
        self,
        podcasts: Optional[List[PodcastData]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Export all podcast data to JSON format for advanced analysis.
        
        Args:
            podcasts: List of podcasts to export (default: all scraped)
            filename: Output filename (default: podcast_data.json)
            
        Returns:
            Path to exported JSON file
        """
        if podcasts is None:
            podcasts = self.all_podcasts
        
        if not podcasts:
            raise ValueError("No podcasts to export")
        
        return self.comprehensive_reporter.export_json_data(podcasts, filename)
    
    def start_performance_monitoring(self) -> None:
        """Start performance monitoring for the scraper."""
        self.performance_monitor.start_monitoring()
        self.logger.info("Performance monitoring started")
    
    def stop_performance_monitoring(self) -> None:
        """Stop performance monitoring and get final stats."""
        self.performance_monitor.stop_monitoring()
        self.logger.info("Performance monitoring stopped")
    
    def get_performance_summary(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get performance summary for the specified time window."""
        return self.performance_monitor.get_performance_summary(window_minutes)
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage and return optimization stats."""
        return MemoryOptimizer.optimize_memory_usage()
    
    def export_performance_metrics(self, output_file: str, format: str = 'json') -> None:
        """Export performance metrics to file."""
        self.performance_monitor.export_metrics(output_file, format)
    
    def generate_report(
        self,
        podcasts: Optional[List[PodcastData]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate a markdown report with statistics and top podcasts.
        
        Args:
            podcasts: List of podcasts to report on (default: all scraped)
            filename: Output filename (default: from config)
            
        Returns:
            Path to generated report file
        """
        if podcasts is None:
            podcasts = self.all_podcasts
        
        if not podcasts:
            raise ValueError("No podcasts to report on")
        
        # Get output path
        report_filename = filename or config.REPORT_FILENAME
        report_path = config.get_output_path(report_filename)
        
        self.logger.info(f"Generating report for {len(podcasts)} podcasts")
        
        # Calculate statistics
        stats = self._calculate_statistics(podcasts)
        
        # Generate markdown report
        report_content = self._generate_markdown_report(stats, podcasts)
        
        # Write report file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"Report generated: {report_path}")
        return report_path
    
    def _deduplicate_podcasts(self, podcasts: List[PodcastData]) -> List[PodcastData]:
        """
        Remove duplicate podcasts based on name similarity.
        
        Args:
            podcasts: List of podcasts that may contain duplicates
            
        Returns:
            List of unique podcasts
        """
        if not podcasts:
            return []
        
        unique_podcasts = []
        seen_names = set()
        
        for podcast in podcasts:
            # Create a normalized name for comparison
            normalized_name = podcast.podcast_name.lower().strip()
            # Remove common words and punctuation
            normalized_name = normalized_name.replace("the ", "").replace("podcast", "").replace("show", "")
            normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c.isspace())
            
            if normalized_name not in seen_names:
                unique_podcasts.append(podcast)
                seen_names.add(normalized_name)
            else:
                self.logger.debug(f"Duplicate podcast filtered: {podcast.podcast_name}")
        
        self.logger.info(f"Deduplication: {len(podcasts)} -> {len(unique_podcasts)} podcasts")
        return unique_podcasts
    
    def _calculate_statistics(self, podcasts: List[PodcastData]) -> Dict[str, Any]:
        """Calculate statistics for podcast data."""
        total = len(podcasts)
        
        if total == 0:
            return {"total": 0}
        
        # Count podcasts with various attributes
        with_hosts = sum(1 for p in podcasts if p.host_name)
        with_emails = sum(1 for p in podcasts if p.host_email or p.booking_email)
        with_websites = sum(1 for p in podcasts if p.podcast_website)
        with_episodes = sum(1 for p in podcasts if p.episode_count and p.episode_count > 0)
        with_descriptions = sum(1 for p in podcasts if p.podcast_description)
        
        # Platform breakdown
        platform_counts = {}
        for podcast in podcasts:
            platform = podcast.platform_source
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        # Episode count statistics
        episode_counts = [p.episode_count for p in podcasts if p.episode_count and p.episode_count > 0]
        avg_episodes = sum(episode_counts) / len(episode_counts) if episode_counts else 0
        
        return {
            "total": total,
            "with_host_names": with_hosts,
            "with_emails": with_emails,
            "with_websites": with_websites,
            "with_episodes": with_episodes,
            "with_descriptions": with_descriptions,
            "platform_breakdown": platform_counts,
            "host_name_rate": f"{(with_hosts/total*100):.1f}%",
            "email_rate": f"{(with_emails/total*100):.1f}%",
            "website_rate": f"{(with_websites/total*100):.1f}%",
            "avg_episode_count": f"{avg_episodes:.0f}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_markdown_report(self, stats: Dict[str, Any], podcasts: List[PodcastData]) -> str:
        """Generate markdown report content."""
        report = f"""# Podcast Host Contact Discovery Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics

- **Total Podcasts Found**: {stats['total']}
- **Podcasts with Host Names**: {stats['with_host_names']} ({stats['host_name_rate']})
- **Podcasts with Email Contacts**: {stats['with_emails']} ({stats['email_rate']})
- **Podcasts with Websites**: {stats['with_websites']} ({stats['website_rate']})
- **Average Episode Count**: {stats['avg_episode_count']}

## Platform Breakdown

"""
        
        for platform, count in stats['platform_breakdown'].items():
            percentage = (count / stats['total'] * 100)
            report += f"- **{platform}**: {count} podcasts ({percentage:.1f}%)\n"
        
        report += f"""

## Top 20 Podcast Contacts

| Rank | Podcast Name | Host | Email | Website | Episodes |
|------|-------------|------|--------|---------|----------|
"""
        
        # Sort podcasts by episode count (popularity proxy)
        sorted_podcasts = sorted(
            podcasts, 
            key=lambda p: p.episode_count or 0, 
            reverse=True
        )
        
        for i, podcast in enumerate(sorted_podcasts[:20], 1):
            name = podcast.podcast_name[:30] + "..." if len(podcast.podcast_name) > 30 else podcast.podcast_name
            host = podcast.host_name[:20] + "..." if podcast.host_name and len(podcast.host_name) > 20 else (podcast.host_name or "Unknown")
            email = podcast.host_email or podcast.booking_email or "Not found"
            website = "Yes" if podcast.podcast_website else "No"
            episodes = str(podcast.episode_count) if podcast.episode_count else "Unknown"
            
            report += f"| {i} | {name} | {host} | {email} | {website} | {episodes} |\n"
        
        report += f"""

## Contact Success Rates

- **Email Discovery**: {stats['email_rate']} of podcasts have discoverable email addresses
- **Website Discovery**: {stats['website_rate']} of podcasts have associated websites
- **Host Identification**: {stats['host_name_rate']} of podcasts have identified host names

## Next Steps

1. **Review CSV Export**: Open the CSV file to see all contact details
2. **Prioritize Outreach**: Focus on podcasts with email contacts and relevant topics
3. **Verify Contacts**: Double-check email addresses before sending outreach
4. **Personalize Messages**: Reference specific podcast content in your pitches

---

*Generated by Podcast Host Contact Scraper - 100% Free & Open Source*
"""
        
        return report
    
    def _log_available_features(self):
        """Log which features are available based on API keys."""
        features = config.get_available_features()
        
        available = []
        unavailable = []
        
        for feature, available_flag in features.items():
            if available_flag:
                available.append(feature)
            else:
                unavailable.append(feature)
        
        self.logger.info(f"Available features: {', '.join(available)}")
        if unavailable:
            self.logger.info(f"Unavailable features (missing API keys): {', '.join(unavailable)}")
    
    def get_scraped_podcasts(self) -> List[PodcastData]:
        """Get all scraped podcasts."""
        return self.all_podcasts
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall scraping statistics."""
        if not self.all_podcasts:
            return {"total": 0, "message": "No podcasts scraped yet"}
        
        return self._calculate_statistics(self.all_podcasts)