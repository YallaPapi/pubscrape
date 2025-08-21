"""
Metrics Collection and Reporting Tool for Agency Swarm

Tool for comprehensive metrics collection, analysis, and reporting of 
domain classification and prioritization processes.
"""

import logging
import time
import json
import csv
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum

try:
    from agency_swarm.tools import BaseTool
    from pydantic import Field
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class Field:
        def __init__(self, *args, **kwargs):
            pass

# Import the domain classifier components
try:
    from agents.domain_classifier_agent import WebsiteType, PlatformType, PriorityLevel, DomainMetadata, ClassificationStats
except ImportError:
    # Fallback if import fails
    class WebsiteType(Enum):
        BUSINESS = "business"
        PERSONAL = "personal"
        BLOG = "blog"
        ECOMMERCE = "ecommerce"
        PORTFOLIO = "portfolio"
        NEWS_MEDIA = "news_media"
        SOCIAL_MEDIA = "social_media"
        DIRECTORY = "directory"
        GOVERNMENT = "government"
        EDUCATIONAL = "educational"
        NONPROFIT = "nonprofit"
        PLATFORM = "platform"
        UNKNOWN = "unknown"
    
    class PlatformType(Enum):
        WORDPRESS = "wordpress"
        SHOPIFY = "shopify"
        WIX = "wix"
        SQUARESPACE = "squarespace"
        CUSTOM = "custom"
        UNKNOWN = "unknown"
    
    class PriorityLevel(Enum):
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"
        SKIP = "skip"

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for processing performance and efficiency"""
    total_domains_processed: int = 0
    successful_classifications: int = 0
    failed_classifications: int = 0
    
    # Timing metrics
    total_processing_time_seconds: float = 0.0
    average_time_per_domain_ms: float = 0.0
    fastest_classification_ms: float = float('inf')
    slowest_classification_ms: float = 0.0
    
    # Platform detection metrics
    platform_detection_attempts: int = 0
    platform_detection_successes: int = 0
    platform_detection_rate: float = 0.0
    
    # Business scoring metrics
    business_scoring_attempts: int = 0
    business_scoring_successes: int = 0
    business_scoring_rate: float = 0.0
    
    # Error tracking
    http_errors: int = 0
    timeout_errors: int = 0
    parsing_errors: int = 0
    network_errors: int = 0
    
    def calculate_rates(self):
        """Calculate derived metrics and rates"""
        if self.total_domains_processed > 0:
            self.platform_detection_rate = self.platform_detection_successes / self.platform_detection_attempts if self.platform_detection_attempts > 0 else 0.0
            self.business_scoring_rate = self.business_scoring_successes / self.business_scoring_attempts if self.business_scoring_attempts > 0 else 0.0
            
            if self.total_processing_time_seconds > 0:
                self.average_time_per_domain_ms = (self.total_processing_time_seconds * 1000) / self.total_domains_processed


@dataclass
class ClassificationMetrics:
    """Metrics for classification results and accuracy"""
    # Website type distribution
    website_type_counts: Dict[str, int] = field(default_factory=dict)
    website_type_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Platform type distribution
    platform_type_counts: Dict[str, int] = field(default_factory=dict)
    platform_type_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Priority level distribution
    priority_level_counts: Dict[str, int] = field(default_factory=dict)
    priority_level_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Score distributions
    business_score_histogram: Dict[str, int] = field(default_factory=dict)
    average_business_score: float = 0.0
    median_business_score: float = 0.0
    business_score_std_dev: float = 0.0
    
    # Quality metrics
    high_confidence_classifications: int = 0
    contact_info_found_count: int = 0
    address_info_found_count: int = 0
    accessible_sites_count: int = 0
    
    def calculate_percentages(self, total_domains: int):
        """Calculate percentage distributions"""
        if total_domains == 0:
            return
        
        # Calculate website type percentages
        for website_type, count in self.website_type_counts.items():
            self.website_type_percentages[website_type] = (count / total_domains) * 100
        
        # Calculate platform type percentages
        for platform_type, count in self.platform_type_counts.items():
            self.platform_type_percentages[platform_type] = (count / total_domains) * 100
        
        # Calculate priority level percentages
        for priority_level, count in self.priority_level_counts.items():
            self.priority_level_percentages[priority_level] = (count / total_domains) * 100


@dataclass
class ExclusionMetrics:
    """Metrics for domain exclusions and filtering"""
    total_exclusions: int = 0
    exclusion_reasons: Dict[str, int] = field(default_factory=dict)
    exclusion_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Accessibility issues
    inaccessible_domains: int = 0
    timeout_exclusions: int = 0
    error_code_exclusions: Dict[str, int] = field(default_factory=dict)
    
    # Content quality exclusions
    low_score_exclusions: int = 0
    personal_site_exclusions: int = 0
    spam_exclusions: int = 0
    
    def calculate_exclusion_percentages(self, total_domains: int):
        """Calculate exclusion percentages"""
        if total_domains == 0:
            return
        
        for reason, count in self.exclusion_reasons.items():
            self.exclusion_percentages[reason] = (count / total_domains) * 100


@dataclass
class ComprehensiveReport:
    """Comprehensive classification and prioritization report"""
    report_id: str
    generated_at: str
    
    # Summary statistics
    total_domains: int
    processing_duration_seconds: float
    
    # Metrics breakdown
    processing_metrics: ProcessingMetrics
    classification_metrics: ClassificationMetrics
    exclusion_metrics: ExclusionMetrics
    
    # Top performers
    top_business_domains: List[Dict[str, Any]] = field(default_factory=list)
    top_ecommerce_domains: List[Dict[str, Any]] = field(default_factory=list)
    
    # Insights and recommendations
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class MetricsCollector:
    """
    Core metrics collection engine for domain classification processes
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Configuration
        self.enable_detailed_logging = self.config.get("enable_detailed_logging", True)
        self.enable_performance_tracking = self.config.get("enable_performance_tracking", True)
        self.enable_export = self.config.get("enable_export", True)
        self.output_directory = Path(self.config.get("output_directory", "classification_reports"))
        
        # Create output directory
        self.output_directory.mkdir(exist_ok=True)
        
        # Initialize metrics storage
        self.processing_metrics = ProcessingMetrics()
        self.classification_metrics = ClassificationMetrics()
        self.exclusion_metrics = ExclusionMetrics()
        
        # Session tracking
        self.session_start_time = time.time()
        self.session_id = f"classification_{int(self.session_start_time)}"
        
        self.logger.info(f"MetricsCollector initialized for session: {self.session_id}")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the metrics collector"""
        logger = logging.getLogger(f"{__name__}.MetricsCollector")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def collect_classification_metrics(self, domains: Dict[str, DomainMetadata]) -> Dict[str, Any]:
        """
        Collect comprehensive metrics from classified domains
        
        Args:
            domains: Dictionary of domain metadata
            
        Returns:
            Dictionary containing collected metrics
        """
        start_time = time.time()
        
        self.logger.info(f"Collecting metrics for {len(domains)} domains")
        
        # Reset metrics for fresh collection
        self.processing_metrics = ProcessingMetrics()
        self.classification_metrics = ClassificationMetrics()
        self.exclusion_metrics = ExclusionMetrics()
        
        # Collect raw data
        business_scores = []
        processing_times = []
        
        for domain, metadata in domains.items():
            try:
                # Processing metrics
                self.processing_metrics.total_domains_processed += 1
                
                if metadata.response_time_ms:
                    processing_times.append(metadata.response_time_ms)
                    self.processing_metrics.fastest_classification_ms = min(
                        self.processing_metrics.fastest_classification_ms,
                        metadata.response_time_ms
                    )
                    self.processing_metrics.slowest_classification_ms = max(
                        self.processing_metrics.slowest_classification_ms,
                        metadata.response_time_ms
                    )
                
                # Platform detection tracking
                if metadata.platform_type != PlatformType.UNKNOWN:
                    self.processing_metrics.platform_detection_attempts += 1
                    if metadata.platform_indicators:
                        self.processing_metrics.platform_detection_successes += 1
                
                # Business scoring tracking
                if metadata.business_score > 0:
                    self.processing_metrics.business_scoring_attempts += 1
                    if metadata.business_score >= 0.3:  # Reasonable threshold
                        self.processing_metrics.business_scoring_successes += 1
                    business_scores.append(metadata.business_score)
                
                # Classification metrics - website types
                website_type_name = metadata.website_type.value
                self.classification_metrics.website_type_counts[website_type_name] = \
                    self.classification_metrics.website_type_counts.get(website_type_name, 0) + 1
                
                # Classification metrics - platform types
                platform_type_name = metadata.platform_type.value
                self.classification_metrics.platform_type_counts[platform_type_name] = \
                    self.classification_metrics.platform_type_counts.get(platform_type_name, 0) + 1
                
                # Classification metrics - priority levels
                priority_level_name = metadata.priority_level.value
                self.classification_metrics.priority_level_counts[priority_level_name] = \
                    self.classification_metrics.priority_level_counts.get(priority_level_name, 0) + 1
                
                # Quality metrics
                if "contact_info_found" in metadata.business_indicators:
                    self.classification_metrics.contact_info_found_count += 1
                
                if any("address" in indicator for indicator in metadata.business_indicators):
                    self.classification_metrics.address_info_found_count += 1
                
                if metadata.is_accessible:
                    self.classification_metrics.accessible_sites_count += 1
                else:
                    self.exclusion_metrics.inaccessible_domains += 1
                
                # Exclusion tracking
                for reason in metadata.exclusion_reasons:
                    self.exclusion_metrics.exclusion_reasons[reason] = \
                        self.exclusion_metrics.exclusion_reasons.get(reason, 0) + 1
                    self.exclusion_metrics.total_exclusions += 1
                
                # Error tracking
                if "timeout" in " ".join(metadata.exclusion_reasons).lower():
                    self.processing_metrics.timeout_errors += 1
                    self.exclusion_metrics.timeout_exclusions += 1
                
                if "http" in " ".join(metadata.exclusion_reasons).lower():
                    self.processing_metrics.http_errors += 1
                
                if "network" in " ".join(metadata.exclusion_reasons).lower():
                    self.processing_metrics.network_errors += 1
                
            except Exception as e:
                self.logger.error(f"Error collecting metrics for domain {domain}: {e}")
                self.processing_metrics.failed_classifications += 1
                continue
        
        # Calculate derived metrics
        self._calculate_derived_metrics(business_scores, processing_times)
        
        # Calculate percentages
        total_domains = len(domains)
        self.classification_metrics.calculate_percentages(total_domains)
        self.exclusion_metrics.calculate_exclusion_percentages(total_domains)
        
        collection_time = time.time() - start_time
        
        self.logger.info(f"Metrics collection completed in {collection_time:.2f}s")
        
        return {
            "success": True,
            "session_id": self.session_id,
            "collection_time_seconds": collection_time,
            "processing_metrics": asdict(self.processing_metrics),
            "classification_metrics": asdict(self.classification_metrics),
            "exclusion_metrics": asdict(self.exclusion_metrics)
        }
    
    def _calculate_derived_metrics(self, business_scores: List[float], processing_times: List[float]):
        """Calculate derived metrics from collected data"""
        
        # Business score statistics
        if business_scores:
            self.classification_metrics.average_business_score = sum(business_scores) / len(business_scores)
            sorted_scores = sorted(business_scores)
            n = len(sorted_scores)
            self.classification_metrics.median_business_score = (
                sorted_scores[n//2] if n % 2 == 1 
                else (sorted_scores[n//2-1] + sorted_scores[n//2]) / 2
            )
            
            # Standard deviation
            if len(business_scores) > 1:
                mean = self.classification_metrics.average_business_score
                variance = sum((score - mean) ** 2 for score in business_scores) / (len(business_scores) - 1)
                self.classification_metrics.business_score_std_dev = variance ** 0.5
            
            # Create histogram bins
            for score in business_scores:
                bin_key = f"{int(score * 10) / 10:.1f}-{int(score * 10) / 10 + 0.1:.1f}"
                self.classification_metrics.business_score_histogram[bin_key] = \
                    self.classification_metrics.business_score_histogram.get(bin_key, 0) + 1
        
        # Processing time statistics
        if processing_times:
            self.processing_metrics.total_processing_time_seconds = sum(processing_times) / 1000.0  # Convert to seconds
            self.processing_metrics.calculate_rates()
    
    def generate_insights(self, domains: Dict[str, DomainMetadata]) -> List[str]:
        """Generate insights from classification metrics"""
        insights = []
        
        # Platform distribution insights
        total_platforms = sum(self.classification_metrics.platform_type_counts.values())
        if total_platforms > 0:
            wordpress_percentage = self.classification_metrics.platform_type_percentages.get("wordpress", 0)
            shopify_percentage = self.classification_metrics.platform_type_percentages.get("shopify", 0)
            
            if wordpress_percentage > 30:
                insights.append(f"WordPress dominates the platform landscape at {wordpress_percentage:.1f}% of sites")
            
            if shopify_percentage > 10:
                insights.append(f"Strong e-commerce presence with {shopify_percentage:.1f}% Shopify sites")
        
        # Business classification insights
        business_percentage = self.classification_metrics.website_type_percentages.get("business", 0)
        ecommerce_percentage = self.classification_metrics.website_type_percentages.get("ecommerce", 0)
        
        if business_percentage > 50:
            insights.append(f"High business site concentration: {business_percentage:.1f}% classified as business")
        
        if ecommerce_percentage > 15:
            insights.append(f"Significant e-commerce opportunity: {ecommerce_percentage:.1f}% e-commerce sites")
        
        # Quality insights
        contact_rate = (self.classification_metrics.contact_info_found_count / len(domains)) * 100 if domains else 0
        if contact_rate > 60:
            insights.append(f"Excellent contact information availability: {contact_rate:.1f}% of sites")
        elif contact_rate < 30:
            insights.append(f"Low contact information availability: {contact_rate:.1f}% of sites")
        
        # Performance insights
        if self.processing_metrics.average_time_per_domain_ms > 5000:
            insights.append("Processing time is high - consider optimization")
        
        # Accessibility insights
        accessibility_rate = (self.classification_metrics.accessible_sites_count / len(domains)) * 100 if domains else 0
        if accessibility_rate < 80:
            insights.append(f"Accessibility issues detected: {100-accessibility_rate:.1f}% of sites inaccessible")
        
        return insights
    
    def generate_recommendations(self, domains: Dict[str, DomainMetadata]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Platform-based recommendations
        wordpress_count = self.classification_metrics.platform_type_counts.get("wordpress", 0)
        shopify_count = self.classification_metrics.platform_type_counts.get("shopify", 0)
        
        if wordpress_count > shopify_count * 3:
            recommendations.append("Focus crawling efforts on WordPress-specific contact patterns")
        
        if shopify_count > 0:
            recommendations.append("Prioritize Shopify sites for higher conversion potential")
        
        # Priority recommendations
        high_priority_count = self.classification_metrics.priority_level_counts.get("high", 0)
        critical_priority_count = self.classification_metrics.priority_level_counts.get("critical", 0)
        
        if (high_priority_count + critical_priority_count) < len(domains) * 0.2:
            recommendations.append("Consider adjusting scoring thresholds to identify more high-value targets")
        
        # Performance recommendations
        if self.processing_metrics.timeout_errors > len(domains) * 0.1:
            recommendations.append("Increase timeout settings to reduce failed classifications")
        
        # Coverage recommendations
        unknown_count = self.classification_metrics.website_type_counts.get("unknown", 0)
        if unknown_count > len(domains) * 0.3:
            recommendations.append("Enhance classification rules to reduce unknown categorizations")
        
        return recommendations
    
    def generate_comprehensive_report(self, domains: Dict[str, DomainMetadata]) -> ComprehensiveReport:
        """Generate a comprehensive classification report"""
        
        # Collect all metrics
        metrics_result = self.collect_classification_metrics(domains)
        
        # Generate insights and recommendations
        insights = self.generate_insights(domains)
        recommendations = self.generate_recommendations(domains)
        
        # Get top performers
        top_business_domains = self._get_top_domains_by_score(domains, limit=10)
        top_ecommerce_domains = self._get_top_ecommerce_domains(domains, limit=5)
        
        # Create comprehensive report
        report = ComprehensiveReport(
            report_id=self.session_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_domains=len(domains),
            processing_duration_seconds=time.time() - self.session_start_time,
            processing_metrics=self.processing_metrics,
            classification_metrics=self.classification_metrics,
            exclusion_metrics=self.exclusion_metrics,
            top_business_domains=top_business_domains,
            top_ecommerce_domains=top_ecommerce_domains,
            insights=insights,
            recommendations=recommendations
        )
        
        return report
    
    def _get_top_domains_by_score(self, domains: Dict[str, DomainMetadata], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top domains by business score"""
        scored_domains = []
        
        for domain, metadata in domains.items():
            if metadata.business_score > 0:
                scored_domains.append({
                    "domain": domain,
                    "business_score": metadata.business_score,
                    "website_type": metadata.website_type.value,
                    "platform_type": metadata.platform_type.value,
                    "priority_level": metadata.priority_level.value,
                    "has_contact_info": "contact_info_found" in metadata.business_indicators,
                    "business_indicators_count": len(metadata.business_indicators)
                })
        
        # Sort by business score and return top N
        scored_domains.sort(key=lambda x: x["business_score"], reverse=True)
        return scored_domains[:limit]
    
    def _get_top_ecommerce_domains(self, domains: Dict[str, DomainMetadata], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top e-commerce domains"""
        ecommerce_domains = []
        
        for domain, metadata in domains.items():
            if metadata.website_type == WebsiteType.ECOMMERCE:
                ecommerce_domains.append({
                    "domain": domain,
                    "business_score": metadata.business_score,
                    "platform_type": metadata.platform_type.value,
                    "priority_level": metadata.priority_level.value,
                    "crawl_budget": metadata.crawl_budget
                })
        
        # Sort by business score and return top N
        ecommerce_domains.sort(key=lambda x: x["business_score"], reverse=True)
        return ecommerce_domains[:limit]
    
    def export_report(self, report: ComprehensiveReport, format_type: str = "json") -> Dict[str, Any]:
        """Export comprehensive report in various formats"""
        
        try:
            if format_type == "json":
                output_file = self.output_directory / f"classification_report_{report.report_id}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(report), f, indent=2, default=str)
                
                return {
                    "success": True,
                    "format": "json",
                    "output_file": str(output_file),
                    "file_size_bytes": output_file.stat().st_size
                }
            
            elif format_type == "csv":
                # Export summary CSV
                output_file = self.output_directory / f"classification_summary_{report.report_id}.csv"
                
                summary_data = [
                    ["Metric", "Value"],
                    ["Total Domains", report.total_domains],
                    ["Processing Duration (seconds)", report.processing_duration_seconds],
                    ["Average Business Score", report.classification_metrics.average_business_score],
                    ["Business Sites", report.classification_metrics.website_type_counts.get("business", 0)],
                    ["E-commerce Sites", report.classification_metrics.website_type_counts.get("ecommerce", 0)],
                    ["Accessible Sites", report.classification_metrics.accessible_sites_count],
                    ["Contact Info Found", report.classification_metrics.contact_info_found_count],
                    ["Platform Detection Rate", report.processing_metrics.platform_detection_rate]
                ]
                
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(summary_data)
                
                return {
                    "success": True,
                    "format": "csv",
                    "output_file": str(output_file),
                    "file_size_bytes": output_file.stat().st_size
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported export format: {format_type}"
                }
        
        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class MetricsReportingTool(BaseTool):
    """
    Agency Swarm tool for metrics collection and reporting
    """
    
    domains_data: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Dictionary of domain metadata for metrics collection"
    )
    
    generate_insights: bool = Field(
        default=True,
        description="Whether to generate insights and recommendations"
    )
    
    export_format: str = Field(
        default="json",
        description="Export format for the report (json, csv)"
    )
    
    output_directory: str = Field(
        default="classification_reports",
        description="Directory to save exported reports"
    )
    
    enable_detailed_logging: bool = Field(
        default=True,
        description="Enable detailed logging during metrics collection"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def run(self) -> Dict[str, Any]:
        """
        Run comprehensive metrics collection and reporting
        
        Returns:
            Dictionary containing metrics, insights, and export information
        """
        start_time = time.time()
        
        # Initialize metrics collector
        config = {
            "enable_detailed_logging": self.enable_detailed_logging,
            "enable_performance_tracking": True,
            "enable_export": True,
            "output_directory": self.output_directory,
            "log_level": logging.INFO
        }
        
        collector = MetricsCollector(config)
        
        logger.info(f"Starting metrics collection and reporting for {len(self.domains_data)} domains")
        
        try:
            # Convert domains data to proper format (assuming it's passed as serialized data)
            # In a real implementation, this would interface with the DomainClassifier directly
            
            # Generate comprehensive report
            # Note: In actual implementation, this would receive DomainMetadata objects
            # For now, we'll work with the data structure we have
            
            mock_domains = {}  # This would be replaced with actual DomainMetadata objects
            
            # Collect basic metrics from the provided data
            basic_metrics = self._collect_basic_metrics_from_data(self.domains_data)
            
            # Create a simplified report structure
            processing_time = time.time() - start_time
            
            report_data = {
                "success": True,
                "session_id": f"metrics_{int(start_time)}",
                "processing_time_seconds": processing_time,
                "total_domains": len(self.domains_data),
                "basic_metrics": basic_metrics,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Export if requested
            if self.export_format:
                export_result = self._export_basic_report(report_data)
                report_data["export_result"] = export_result
            
            logger.info(f"Metrics collection completed in {processing_time:.2f}s")
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error during metrics collection: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time
            }
    
    def _collect_basic_metrics_from_data(self, domains_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Collect basic metrics from domain data structure"""
        
        website_types = {}
        platform_types = {}
        priority_levels = {}
        business_scores = []
        
        accessible_count = 0
        contact_info_count = 0
        
        for domain, data in domains_data.items():
            # Count website types
            website_type = data.get("website_type", "unknown")
            website_types[website_type] = website_types.get(website_type, 0) + 1
            
            # Count platform types
            platform_type = data.get("platform_type", "unknown")
            platform_types[platform_type] = platform_types.get(platform_type, 0) + 1
            
            # Count priority levels
            priority_level = data.get("priority_level", "medium")
            priority_levels[priority_level] = priority_levels.get(priority_level, 0) + 1
            
            # Collect business scores
            business_score = data.get("business_score", 0)
            if business_score > 0:
                business_scores.append(business_score)
            
            # Check accessibility
            if data.get("is_accessible", True):
                accessible_count += 1
            
            # Check contact info
            business_indicators = data.get("business_indicators", [])
            if any("contact" in indicator for indicator in business_indicators):
                contact_info_count += 1
        
        # Calculate averages
        avg_business_score = sum(business_scores) / len(business_scores) if business_scores else 0
        accessibility_rate = (accessible_count / len(domains_data)) * 100 if domains_data else 0
        contact_info_rate = (contact_info_count / len(domains_data)) * 100 if domains_data else 0
        
        return {
            "website_type_distribution": website_types,
            "platform_type_distribution": platform_types,
            "priority_level_distribution": priority_levels,
            "average_business_score": avg_business_score,
            "accessibility_rate_percent": accessibility_rate,
            "contact_info_rate_percent": contact_info_rate,
            "total_domains_with_scores": len(business_scores)
        }
    
    def _export_basic_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export basic report to file"""
        try:
            output_dir = Path(self.output_directory)
            output_dir.mkdir(exist_ok=True)
            
            if self.export_format == "json":
                output_file = output_dir / f"metrics_report_{report_data['session_id']}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, default=str)
                
                return {
                    "success": True,
                    "format": "json",
                    "output_file": str(output_file),
                    "file_size_bytes": output_file.stat().st_size
                }
            
            elif self.export_format == "csv":
                output_file = output_dir / f"metrics_summary_{report_data['session_id']}.csv"
                
                # Create summary CSV
                basic_metrics = report_data.get("basic_metrics", {})
                summary_rows = [
                    ["Metric", "Value"],
                    ["Total Domains", report_data["total_domains"]],
                    ["Average Business Score", basic_metrics.get("average_business_score", 0)],
                    ["Accessibility Rate %", basic_metrics.get("accessibility_rate_percent", 0)],
                    ["Contact Info Rate %", basic_metrics.get("contact_info_rate_percent", 0)]
                ]
                
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(summary_rows)
                
                return {
                    "success": True,
                    "format": "csv",
                    "output_file": str(output_file),
                    "file_size_bytes": output_file.stat().st_size
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported format: {self.export_format}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }