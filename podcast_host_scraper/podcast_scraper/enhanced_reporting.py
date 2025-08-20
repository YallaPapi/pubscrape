"""
Enhanced CSV output generation and comprehensive reporting module.
Provides detailed analytics, multiple export formats, and actionable insights.
"""

import csv
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base import PodcastData
from .config import config

logger = logging.getLogger(__name__)


class EnhancedCSVExporter:
    """Enhanced CSV exporter with comprehensive data fields."""
    
    def __init__(self):
        """Initialize enhanced CSV exporter."""
        self.logger = logging.getLogger(__name__)
    
    def export_enhanced_csv(self, podcasts: List[PodcastData], filename: Optional[str] = None) -> str:
        """
        Export podcasts to enhanced CSV with all intelligence and contact data.
        
        Args:
            podcasts: List of PodcastData objects
            filename: Optional output filename
            
        Returns:
            Path to exported CSV file
        """
        if not podcasts:
            raise ValueError("No podcasts to export")
        
        # Get output path
        if filename:
            output_path = config.get_output_path(filename)
        else:
            output_path = config.get_output_path("enhanced_podcast_contacts.csv")
        
        self.logger.info(f"Exporting {len(podcasts)} podcasts to enhanced CSV: {output_path}")
        
        # Prepare CSV data
        csv_data = []
        for podcast in podcasts:
            row = self._extract_enhanced_row_data(podcast)
            csv_data.append(row)
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=config.ENHANCED_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(csv_data)
        
        self.logger.info(f"Enhanced CSV export completed: {output_path}")
        return output_path
    
    def _extract_enhanced_row_data(self, podcast: PodcastData) -> Dict[str, str]:
        """Extract comprehensive row data for enhanced CSV."""
        row = {}
        
        # Initialize all columns with empty strings
        for column in config.ENHANCED_CSV_COLUMNS:
            row[column] = ""
        
        # Basic Information
        row["podcast_name"] = podcast.podcast_name or ""
        row["host_name"] = podcast.host_name or ""
        row["podcast_description"] = self._truncate_text(podcast.podcast_description or "", 500)
        
        # Contact Information
        row["host_email"] = podcast.host_email or ""
        row["booking_email"] = podcast.booking_email or ""
        row["podcast_website"] = podcast.podcast_website or ""
        row["contact_page_url"] = podcast.contact_page_url or ""
        
        # Extract advanced contact data
        if podcast.raw_data and 'advanced_contact_enrichment' in podcast.raw_data:
            enrichment = podcast.raw_data['advanced_contact_enrichment']
            
            # Alternative emails
            primary_contacts = enrichment.get('primary_contacts', [])
            alt_emails = [c['value'] for c in primary_contacts if c['type'] == 'email' and c['value'] not in [podcast.host_email, podcast.booking_email]]
            row["alternative_emails"] = "; ".join(alt_emails[:3])  # Limit to 3
            
            # Contact forms
            row["contact_forms_available"] = "Yes" if enrichment.get('contact_forms', []) else "No"
            
            # Contact quality data
            row["best_contact_method"] = enrichment.get('best_contact_method', '')
            row["contact_strategy"] = self._truncate_text(enrichment.get('contact_strategy', ''), 200)
        
        # Social Media
        if podcast.social_links:
            # Format social links as "platform:url, platform:url"
            social_list = [f"{platform}:{url}" for platform, url in podcast.social_links.items()]
            row["social_links"] = "; ".join(social_list)
            row["social_platforms_count"] = str(len(podcast.social_links))
        
        # Social influence score
        if podcast.raw_data and 'social_influence_score' in podcast.raw_data:
            row["social_influence_score"] = str(podcast.raw_data['social_influence_score'])
        
        # Intelligence Metrics
        if podcast.raw_data and 'intelligence' in podcast.raw_data:
            intelligence = podcast.raw_data['intelligence']
            
            row["overall_intelligence_score"] = str(intelligence.get('overall_score', ''))
            row["relevance_score"] = str(intelligence.get('relevance_score', ''))
            row["popularity_score"] = str(intelligence.get('popularity_score', ''))
            row["authority_score"] = str(intelligence.get('authority_score', ''))
            row["content_quality_score"] = str(intelligence.get('content_quality_score', ''))
            row["guest_potential_score"] = str(intelligence.get('guest_potential_score', ''))
            
            row["estimated_downloads"] = intelligence.get('estimated_downloads', '')
            row["audience_size_category"] = intelligence.get('audience_size_category', '')
            row["host_authority_level"] = intelligence.get('host_authority_level', '')
            
            # Content analysis
            content_analysis = intelligence.get('content_analysis', {})
            row["content_format_type"] = content_analysis.get('format_type', '')
            row["interview_style"] = "Yes" if content_analysis.get('interview_style') else "No"
            
            # Recommendations and risks
            recommendations = intelligence.get('recommendations', [])
            row["recommendations"] = "; ".join(recommendations[:2])  # Top 2 recommendations
            
            risk_factors = intelligence.get('risk_factors', [])
            row["risk_factors"] = "; ".join(risk_factors[:2])  # Top 2 risks
        
        # Contact Quality Scoring
        if podcast.raw_data and 'contact_quality_score' in podcast.raw_data:
            quality = podcast.raw_data['contact_quality_score']
            
            row["contact_quality_score"] = str(quality.get('overall_score', ''))
            row["response_likelihood"] = f"{quality.get('response_probability', 0):.1f}%"
        
        # Podcast Metrics
        row["episode_count"] = str(podcast.episode_count) if podcast.episode_count else ""
        row["rating"] = str(podcast.rating) if podcast.rating else ""
        row["contact_confidence"] = podcast.contact_confidence or ""
        
        # Platform Information
        row["platform_source"] = podcast.platform_source or ""
        row["apple_podcasts_url"] = podcast.apple_podcasts_url or ""
        row["rss_feed_url"] = podcast.rss_feed_url or ""
        
        # Extract platform-specific URLs from raw data
        if podcast.raw_data:
            row["spotify_url"] = podcast.raw_data.get('spotify_url', '')
            if podcast.platform_source == "YouTube/Google Podcasts":
                row["youtube_url"] = podcast.podcast_website or ""
        
        # Metadata
        row["ai_relevance_score"] = str(podcast.ai_relevance_score) if podcast.ai_relevance_score else ""
        row["last_updated"] = podcast.last_updated or ""
        
        return row
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."


class ComprehensiveReporter:
    """Generates comprehensive analytics reports and dashboards."""
    
    def __init__(self):
        """Initialize comprehensive reporter."""
        self.logger = logging.getLogger(__name__)
    
    def generate_comprehensive_report(self, podcasts: List[PodcastData], topic: str = "", filename: Optional[str] = None) -> str:
        """
        Generate comprehensive analytics report.
        
        Args:
            podcasts: List of podcasts to analyze
            topic: Search topic for context
            filename: Optional output filename
            
        Returns:
            Path to generated report file
        """
        if not podcasts:
            raise ValueError("No podcasts to report on")
        
        # Get output path
        if filename:
            report_path = config.get_output_path(filename)
        else:
            report_path = config.get_output_path("comprehensive_podcast_analysis.md")
        
        self.logger.info(f"Generating comprehensive report for {len(podcasts)} podcasts")
        
        # Calculate comprehensive statistics
        stats = self._calculate_comprehensive_stats(podcasts, topic)
        
        # Generate report content
        report_content = self._generate_comprehensive_markdown(stats, podcasts, topic)
        
        # Write report file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"Comprehensive report generated: {report_path}")
        return report_path
    
    def _calculate_comprehensive_stats(self, podcasts: List[PodcastData], topic: str) -> Dict[str, Any]:
        """Calculate comprehensive statistics."""
        stats = {
            'total_podcasts': len(podcasts),
            'topic': topic,
            'timestamp': datetime.now(),
            
            # Contact Statistics
            'contact_stats': {},
            'intelligence_stats': {},
            'platform_stats': {},
            'quality_distribution': {},
            'top_prospects': [],
            'contact_methods': {},
            'response_likelihood_dist': {},
            'recommendations_summary': {}
        }
        
        # Contact statistics
        with_emails = sum(1 for p in podcasts if p.host_email or p.booking_email)
        with_websites = sum(1 for p in podcasts if p.podcast_website)
        with_social = sum(1 for p in podcasts if p.social_links)
        with_contact_pages = sum(1 for p in podcasts if p.contact_page_url)
        
        stats['contact_stats'] = {
            'with_emails': with_emails,
            'email_rate': f"{(with_emails/len(podcasts)*100):.1f}%",
            'with_websites': with_websites,
            'website_rate': f"{(with_websites/len(podcasts)*100):.1f}%",
            'with_social': with_social,
            'social_rate': f"{(with_social/len(podcasts)*100):.1f}%",
            'with_contact_pages': with_contact_pages,
            'contact_page_rate': f"{(with_contact_pages/len(podcasts)*100):.1f}%"
        }
        
        # Intelligence statistics
        if any(p.raw_data and 'intelligence' in p.raw_data for p in podcasts):
            intelligence_podcasts = [p for p in podcasts if p.raw_data and 'intelligence' in p.raw_data]
            
            avg_relevance = sum(p.raw_data['intelligence']['relevance_score'] for p in intelligence_podcasts) / len(intelligence_podcasts)
            avg_authority = sum(p.raw_data['intelligence']['authority_score'] for p in intelligence_podcasts) / len(intelligence_podcasts)
            avg_popularity = sum(p.raw_data['intelligence']['popularity_score'] for p in intelligence_podcasts) / len(intelligence_podcasts)
            avg_guest_potential = sum(p.raw_data['intelligence']['guest_potential_score'] for p in intelligence_podcasts) / len(intelligence_podcasts)
            
            stats['intelligence_stats'] = {
                'analyzed_count': len(intelligence_podcasts),
                'avg_relevance_score': f"{avg_relevance:.1f}",
                'avg_authority_score': f"{avg_authority:.1f}",
                'avg_popularity_score': f"{avg_popularity:.1f}",
                'avg_guest_potential': f"{avg_guest_potential:.1f}",
                'high_potential_count': sum(1 for p in intelligence_podcasts if p.raw_data['intelligence']['guest_potential_score'] >= 7)
            }
        
        # Platform distribution
        platform_counts = {}
        for podcast in podcasts:
            platform = podcast.platform_source
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        stats['platform_stats'] = platform_counts
        
        # Quality distribution
        quality_levels = {'very_high': 0, 'high': 0, 'medium': 0, 'low': 0, 'very_low': 0, 'unknown': 0}
        for podcast in podcasts:
            confidence = podcast.contact_confidence or 'unknown'
            if confidence in quality_levels:
                quality_levels[confidence] += 1
            else:
                quality_levels['unknown'] += 1
        stats['quality_distribution'] = quality_levels
        
        # Top prospects (highest guest potential scores)
        if any(p.raw_data and 'intelligence' in p.raw_data for p in podcasts):
            top_prospects = sorted(
                [p for p in podcasts if p.raw_data and 'intelligence' in p.raw_data],
                key=lambda p: p.raw_data['intelligence']['guest_potential_score'],
                reverse=True
            )[:10]
            stats['top_prospects'] = top_prospects
        
        # Contact method analysis
        contact_methods = {'email': 0, 'website': 0, 'social_only': 0, 'none': 0}
        for podcast in podcasts:
            if podcast.host_email or podcast.booking_email:
                contact_methods['email'] += 1
            elif podcast.podcast_website or podcast.contact_page_url:
                contact_methods['website'] += 1
            elif podcast.social_links:
                contact_methods['social_only'] += 1
            else:
                contact_methods['none'] += 1
        stats['contact_methods'] = contact_methods
        
        # Response likelihood distribution
        if any(p.raw_data and 'contact_quality_score' in p.raw_data for p in podcasts):
            likelihood_ranges = {'80-100%': 0, '60-79%': 0, '40-59%': 0, '20-39%': 0, '0-19%': 0}
            
            for podcast in podcasts:
                if podcast.raw_data and 'contact_quality_score' in podcast.raw_data:
                    likelihood = podcast.raw_data['contact_quality_score'].get('response_probability', 0)
                    if likelihood >= 80:
                        likelihood_ranges['80-100%'] += 1
                    elif likelihood >= 60:
                        likelihood_ranges['60-79%'] += 1
                    elif likelihood >= 40:
                        likelihood_ranges['40-59%'] += 1
                    elif likelihood >= 20:
                        likelihood_ranges['20-39%'] += 1
                    else:
                        likelihood_ranges['0-19%'] += 1
            
            stats['response_likelihood_dist'] = likelihood_ranges
        
        return stats
    
    def _generate_comprehensive_markdown(self, stats: Dict[str, Any], podcasts: List[PodcastData], topic: str) -> str:
        """Generate comprehensive markdown report."""
        
        report = f"""# Comprehensive Podcast Host Contact Analysis Report

**Generated:** {stats['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
**Search Topic:** {topic or 'General'}
**Total Podcasts Analyzed:** {stats['total_podcasts']}

---

## 🎯 Executive Summary

This comprehensive analysis covers {stats['total_podcasts']} podcasts discovered across multiple platforms. The report provides detailed insights into contact availability, host authority levels, audience reach, and guest appearance potential.

### Key Findings

- **Contact Success Rate:** {stats['contact_stats']['email_rate']} of podcasts have direct email contacts
- **High-Quality Prospects:** {stats.get('intelligence_stats', {}).get('high_potential_count', 'N/A')} podcasts identified as high guest potential
- **Average Authority Score:** {stats.get('intelligence_stats', {}).get('avg_authority_score', 'N/A')}/10
- **Best Contact Method:** Email contact available for {stats['contact_stats']['with_emails']} podcasts

---

## 📊 Contact Availability Analysis

### Contact Method Distribution

| Contact Type | Count | Percentage |
|--------------|--------|------------|
| **Direct Email** | {stats['contact_stats']['with_emails']} | {stats['contact_stats']['email_rate']} |
| **Website/Contact Page** | {stats['contact_stats']['with_websites']} | {stats['contact_stats']['website_rate']} |
| **Social Media Only** | {stats['contact_stats']['with_social']} | {stats['contact_stats']['social_rate']} |
| **Contact Forms** | {stats['contact_stats']['with_contact_pages']} | {stats['contact_stats']['contact_page_rate']} |

### Contact Quality Distribution

"""

        # Add quality distribution
        for quality, count in stats['quality_distribution'].items():
            percentage = (count / stats['total_podcasts'] * 100) if stats['total_podcasts'] > 0 else 0
            quality_display = quality.replace('_', ' ').title()
            report += f"- **{quality_display}:** {count} podcasts ({percentage:.1f}%)\n"

        # Intelligence Analysis section
        if stats.get('intelligence_stats'):
            intelligence = stats['intelligence_stats']
            report += f"""

---

## 🧠 Intelligence Analysis

**Analyzed Podcasts:** {intelligence['analyzed_count']} of {stats['total_podcasts']}

### Average Scores (0-10 scale)

| Metric | Score | Description |
|--------|--------|-------------|
| **Topic Relevance** | {intelligence['avg_relevance_score']} | How well content matches search topic |
| **Host Authority** | {intelligence['avg_authority_score']} | Host expertise and industry recognition |
| **Podcast Popularity** | {intelligence['avg_popularity_score']} | Audience size and engagement indicators |
| **Guest Potential** | {intelligence['avg_guest_potential']} | Likelihood of accepting guest appearances |

### High-Potential Prospects

{intelligence['high_potential_count']} podcasts identified as high guest potential (7+ score):

"""

        # Add top prospects if available
        if stats.get('top_prospects'):
            for i, podcast in enumerate(stats['top_prospects'][:5], 1):
                intelligence = podcast.raw_data.get('intelligence', {})
                guest_score = intelligence.get('guest_potential_score', 0)
                contact_method = "📧 Email" if (podcast.host_email or podcast.booking_email) else "🌐 Website" if podcast.podcast_website else "📱 Social"
                
                report += f"{i}. **{podcast.podcast_name}** (Score: {guest_score:.1f}/10)\n"
                report += f"   - Host: {podcast.host_name or 'Unknown'}\n"
                report += f"   - Contact: {contact_method}\n"
                report += f"   - Authority: {intelligence.get('host_authority_level', 'Unknown')}\n\n"

        # Platform Analysis
        report += f"""

---

## 📱 Platform Distribution

"""
        for platform, count in stats['platform_stats'].items():
            percentage = (count / stats['total_podcasts'] * 100) if stats['total_podcasts'] > 0 else 0
            report += f"- **{platform}:** {count} podcasts ({percentage:.1f}%)\n"

        # Response Likelihood Analysis
        if stats.get('response_likelihood_dist'):
            report += f"""

---

## 📈 Response Likelihood Analysis

Based on contact quality, host authority, and podcast characteristics:

"""
            for range_label, count in stats['response_likelihood_dist'].items():
                percentage = (count / stats['total_podcasts'] * 100) if stats['total_podcasts'] > 0 else 0
                report += f"- **{range_label} Response Likelihood:** {count} podcasts ({percentage:.1f}%)\n"

        # Recommendations section
        report += f"""

---

## 🎯 Strategic Recommendations

### Priority Contact Approach

1. **Tier 1 (Immediate Contact):** {stats['contact_stats']['with_emails']} podcasts with direct email access
   - Use personalized email outreach with specific podcast references
   - Mention relevant expertise and value proposition
   - Follow up within 1-2 weeks if no response

2. **Tier 2 (Secondary Contact):** {stats['contact_stats']['with_websites']} podcasts with website/contact forms
   - Use professional contact forms with detailed proposals
   - Include media kit and speaking topics
   - Allow 2-3 weeks for response

3. **Tier 3 (Relationship Building):** {stats['contact_stats']['with_social']} podcasts with social media only
   - Engage with content before direct outreach
   - Build relationship through comments and shares
   - Move to DM after establishing connection

### Success Optimization Tips

"""

        # Add specific recommendations based on data
        if stats.get('intelligence_stats'):
            high_potential = stats['intelligence_stats'].get('high_potential_count', 0)
            if high_potential > 0:
                report += f"- **Focus on High-Potential Prospects:** {high_potential} podcasts identified as most likely to accept guests\n"
        
        if stats['contact_stats']['with_emails'] > stats['total_podcasts'] * 0.5:
            report += "- **Email-First Strategy:** High email availability suggests direct outreach will be most effective\n"
        
        if stats['contact_stats']['with_social'] > stats['total_podcasts'] * 0.7:
            report += "- **Social Media Engagement:** Strong social presence suggests relationship-building approach\n"

        report += f"""
- **Batch Processing:** Group outreach by platform and contact method for efficiency
- **Personalization:** Reference specific episodes and topics for higher response rates
- **Follow-up Cadence:** Space follow-ups 1-2 weeks apart, maximum 3 attempts
- **Value Proposition:** Lead with audience benefit and unique insights

---

## 📋 Next Steps

1. **Export Data:** Use the enhanced CSV export for detailed contact information
2. **Prioritize Outreach:** Start with Tier 1 prospects (direct email contacts)
3. **Prepare Materials:** Create tailored pitch templates for each contact method
4. **Track Results:** Monitor response rates to optimize future campaigns
5. **Relationship Nurturing:** Follow discovered social profiles for ongoing engagement

---

## 📊 Data Export Information

- **Enhanced CSV:** Contains all contact details, scores, and recommendations
- **Platform URLs:** Direct links to podcast profiles across platforms
- **Intelligence Metrics:** Comprehensive scoring for prioritization
- **Contact Strategies:** Personalized approach recommendations per podcast

---

*Report generated by Podcast Host Contact Scraper - 100% Free & Open Source*
*For questions or support, visit the project documentation*

"""

        return report
    
    def export_json_data(self, podcasts: List[PodcastData], filename: Optional[str] = None) -> str:
        """Export all podcast data to JSON format for advanced analysis."""
        if not podcasts:
            raise ValueError("No podcasts to export")
        
        # Get output path
        if filename:
            output_path = config.get_output_path(filename)
        else:
            output_path = config.get_output_path("podcast_data.json")
        
        self.logger.info(f"Exporting {len(podcasts)} podcasts to JSON: {output_path}")
        
        # Convert podcasts to serializable format
        json_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_podcasts': len(podcasts),
            'podcasts': []
        }
        
        for podcast in podcasts:
            podcast_dict = {
                'podcast_name': podcast.podcast_name,
                'host_name': podcast.host_name,
                'podcast_description': podcast.podcast_description,
                'host_email': podcast.host_email,
                'booking_email': podcast.booking_email,
                'podcast_website': podcast.podcast_website,
                'contact_page_url': podcast.contact_page_url,
                'social_links': podcast.social_links,
                'estimated_downloads': podcast.estimated_downloads,
                'episode_count': podcast.episode_count,
                'rating': podcast.rating,
                'ai_relevance_score': podcast.ai_relevance_score,
                'contact_confidence': podcast.contact_confidence,
                'platform_source': podcast.platform_source,
                'apple_podcasts_url': podcast.apple_podcasts_url,
                'rss_feed_url': podcast.rss_feed_url,
                'last_updated': podcast.last_updated,
                'raw_data': podcast.raw_data
            }
            json_data['podcasts'].append(podcast_dict)
        
        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"JSON export completed: {output_path}")
        return output_path