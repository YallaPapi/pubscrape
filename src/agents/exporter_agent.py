"""
Exporter Agent

Agency Swarm agent for exporting and reporting validated contact data.
Provides comprehensive export capabilities including CSV, JSON, analytics,
and Google Drive integration for the final podcast contact discovery results.
"""

import logging
import json
import csv
import os
import pandas as pd
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path

try:
    from agency_swarm import Agent
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    # Create mock classes for testing
    class Agent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field


@dataclass
class ExportMetrics:
    """Metrics for export operations"""
    export_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_rows: int = 0
    write_duration_ms: float = 0.0
    file_size_bytes: int = 0
    validation_errors: int = 0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    export_format: str = ""
    output_path: str = ""
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class CampaignSummary:
    """Campaign summary statistics"""
    campaign_id: str
    topic: str
    total_contacts: int
    high_quality_contacts: int
    medium_quality_contacts: int
    low_quality_contacts: int
    email_contacts: int
    website_contacts: int
    social_contacts: int
    validation_success_rate: float
    avg_confidence_score: float
    platform_distribution: Dict[str, int]
    export_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    processing_duration_minutes: Optional[float] = None


@dataclass
class ProxyPerformance:
    """Proxy performance metrics"""
    proxy_provider: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    blocked_count: int
    rotation_count: int
    bandwidth_used_mb: float
    cost_estimate: Optional[float] = None
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CSVExporter:
    """
    Enhanced CSV exporter with comprehensive schema validation and Excel compatibility.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # CSV schema for podcast outreach matching original requirements
        self.PODCAST_OUTREACH_SCHEMA = [
            # Basic Information
            "podcast_name",
            "host_name",
            "podcast_description",
            
            # Contact Information (Primary)
            "host_email",
            "booking_email",
            "alternative_emails",
            "podcast_website",
            "contact_page_url",
            "contact_forms_available",
            "best_contact_method",
            "contact_strategy",
            "contact_confidence",
            
            # Social Media
            "social_links",
            "social_influence_score",
            "social_platforms_count",
            
            # Intelligence & Scoring
            "overall_intelligence_score",
            "relevance_score",
            "popularity_score",
            "authority_score",
            "content_quality_score",
            "guest_potential_score",
            
            # Contact Quality Assessment
            "contact_quality_score",
            "response_likelihood",
            "validation_status",
            
            # Email Validation Details (Mailtester API)
            "email_validation_method",
            "mailtester_score",
            "mailtester_status",
            "mailtester_confidence_level",
            "is_disposable_email",
            "is_role_account",
            "smtp_verified",
            "is_catch_all_domain",
            "has_mx_records",
            "domain_exists",
            "smtp_can_connect",
            "smtp_accepts_mail",
            "deliverability_verified",
            
            # Podcast Metrics
            "estimated_downloads",
            "audience_size_category",
            "episode_count",
            "rating",
            "host_authority_level",
            
            # Platform Information
            "platform_source",
            "apple_podcasts_url",
            "spotify_url",
            "youtube_url",
            "google_podcasts_url",
            "rss_feed_url",
            
            # Content Analysis
            "content_format_type",
            "interview_style",
            "target_audience",
            "content_themes",
            
            # Outreach Intelligence
            "recommendations",
            "risk_factors",
            "outreach_priority",
            "best_pitch_angle",
            
            # Metadata
            "ai_relevance_score",
            "discovery_source",
            "validation_date",
            "last_updated",
            "data_quality_grade",
            "notes"
        ]
        
        # Data type mappings for pandas
        self.DTYPE_MAPPING = {
            'overall_intelligence_score': 'float64',
            'relevance_score': 'float64',
            'popularity_score': 'float64',
            'authority_score': 'float64',
            'content_quality_score': 'float64',
            'guest_potential_score': 'float64',
            'contact_quality_score': 'float64',
            'response_likelihood': 'float64',
            'social_influence_score': 'float64',
            'social_platforms_count': 'int64',
            'estimated_downloads': 'int64',
            'episode_count': 'int64',
            'rating': 'float64',
            'ai_relevance_score': 'float64',
            
            # Email validation field types
            'mailtester_score': 'float64',
            'mailtester_confidence_level': 'string',
            'is_disposable_email': 'boolean',
            'is_role_account': 'boolean',
            'smtp_verified': 'boolean',
            'is_catch_all_domain': 'boolean',
            'has_mx_records': 'boolean',
            'domain_exists': 'boolean',
            'smtp_can_connect': 'boolean',
            'smtp_accepts_mail': 'boolean',
            'deliverability_verified': 'boolean'
        }
        
        self.logger.info("CSVExporter initialized with podcast outreach schema")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.CSVExporter")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def export_to_csv(self, data: List[Dict[str, Any]], output_path: str, 
                     validate_schema: bool = True) -> ExportMetrics:
        """
        Export data to CSV with proper quoting and schema validation.
        
        Args:
            data: List of dictionaries containing contact data
            output_path: Path for output CSV file
            validate_schema: Whether to validate against schema
            
        Returns:
            ExportMetrics with export performance data
        """
        start_time = time.time()
        metrics = ExportMetrics(
            export_format="CSV",
            output_path=output_path,
            total_rows=len(data)
        )
        
        try:
            if not data:
                raise ValueError("No data provided for export")
            
            self.logger.info(f"Exporting {len(data)} records to CSV: {output_path}")
            
            # Validate schema if requested
            if validate_schema:
                validation_errors = self._validate_schema(data)
                metrics.validation_errors = len(validation_errors)
                if validation_errors:
                    self.logger.warning(f"Schema validation found {len(validation_errors)} errors")
            
            # Prepare data for pandas
            df_data = self._prepare_data_for_export(data)
            
            # Create DataFrame with proper dtypes
            df = pd.DataFrame(df_data)
            
            # Apply data type conversions where possible
            for col, dtype in self.DTYPE_MAPPING.items():
                if col in df.columns:
                    try:
                        if dtype.startswith('float'):
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        elif dtype.startswith('int'):
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
                    except Exception as e:
                        self.logger.debug(f"Could not convert column {col} to {dtype}: {e}")
            
            # Ensure all schema columns are present
            for col in self.PODCAST_OUTREACH_SCHEMA:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns to match schema
            df = df[self.PODCAST_OUTREACH_SCHEMA]
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Export to CSV with Excel-compatible settings
            df.to_csv(
                output_path,
                index=False,
                encoding='utf-8-sig',  # Excel BOM for UTF-8
                quoting=csv.QUOTE_ALL,  # Quote all fields for safety
                escapechar='\\',
                lineterminator='\n'
            )
            
            # Calculate metrics
            metrics.write_duration_ms = (time.time() - start_time) * 1000
            metrics.file_size_bytes = os.path.getsize(output_path)
            metrics.quality_distribution = self._calculate_quality_distribution(data)
            metrics.success = True
            
            self.logger.info(
                f"CSV export completed: {metrics.total_rows} rows, "
                f"{metrics.file_size_bytes:,} bytes, "
                f"{metrics.write_duration_ms:.1f}ms"
            )
            
        except Exception as e:
            metrics.error_message = str(e)
            metrics.write_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"CSV export failed: {e}")
        
        return metrics
    
    def _validate_schema(self, data: List[Dict[str, Any]]) -> List[str]:
        """Validate data against schema"""
        errors = []
        
        for i, record in enumerate(data):
            # Check for required fields
            required_fields = ['podcast_name', 'host_name']
            for field in required_fields:
                if not record.get(field):
                    errors.append(f"Row {i}: Missing required field '{field}'")
            
            # Check email format if present
            email_fields = ['host_email', 'booking_email']
            for field in email_fields:
                email = record.get(field)
                if email and '@' not in email:
                    errors.append(f"Row {i}: Invalid email format in '{field}': {email}")
            
            # Check URL format if present
            url_fields = ['podcast_website', 'apple_podcasts_url', 'spotify_url', 'youtube_url']
            for field in url_fields:
                url = record.get(field)
                if url and not (url.startswith('http://') or url.startswith('https://')):
                    errors.append(f"Row {i}: Invalid URL format in '{field}': {url}")
        
        return errors
    
    def _prepare_data_for_export(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare data for CSV export with proper formatting"""
        prepared_data = []
        
        for record in data:
            prepared_record = {}
            
            # Copy all fields, ensuring they're strings or proper types
            for field in self.PODCAST_OUTREACH_SCHEMA:
                value = record.get(field, "")
                
                # Handle special formatting
                if field == 'social_links' and isinstance(value, dict):
                    # Convert social links dict to formatted string
                    value = "; ".join([f"{platform}: {url}" for platform, url in value.items()])
                elif field == 'alternative_emails' and isinstance(value, list):
                    # Convert list to semicolon-separated string
                    value = "; ".join(value)
                elif field in ['recommendations', 'risk_factors'] and isinstance(value, list):
                    # Convert lists to comma-separated strings
                    value = ", ".join(value)
                elif field == 'contact_forms_available' and isinstance(value, bool):
                    # Convert boolean to Yes/No
                    value = "Yes" if value else "No"
                elif field == 'interview_style' and isinstance(value, bool):
                    # Convert boolean to Yes/No
                    value = "Yes" if value else "No"
                elif isinstance(value, (list, dict)) and field not in ['social_links', 'alternative_emails', 'recommendations', 'risk_factors']:
                    # Convert remaining complex types to JSON strings
                    value = json.dumps(value) if value else ""
                
                # Ensure value is string for CSV compatibility
                if value is None:
                    value = ""
                elif not isinstance(value, str) and field not in self.DTYPE_MAPPING:
                    value = str(value)
                
                prepared_record[field] = value
            
            prepared_data.append(prepared_record)
        
        return prepared_data
    
    def _calculate_quality_distribution(self, data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate quality distribution of contacts"""
        distribution = {
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'unknown_quality': 0
        }
        
        for record in data:
            confidence = record.get('contact_confidence', '').lower()
            if confidence in ['very_high', 'high']:
                distribution['high_quality'] += 1
            elif confidence in ['medium']:
                distribution['medium_quality'] += 1
            elif confidence in ['low', 'very_low']:
                distribution['low_quality'] += 1
            else:
                distribution['unknown_quality'] += 1
        
        return distribution


class JSONStatsExporter:
    """
    JSON statistics exporter for campaign summaries and performance data.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        self.logger.info("JSONStatsExporter initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.JSONStatsExporter")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def export_campaign_summary(self, data: List[Dict[str, Any]], 
                               campaign_info: Dict[str, Any],
                               output_path: str) -> ExportMetrics:
        """
        Export campaign summary to JSON.
        
        Args:
            data: Contact data for analysis
            campaign_info: Campaign metadata
            output_path: Output file path
            
        Returns:
            ExportMetrics with export performance data
        """
        start_time = time.time()
        metrics = ExportMetrics(
            export_format="JSON_CAMPAIGN_SUMMARY",
            output_path=output_path,
            total_rows=len(data)
        )
        
        try:
            self.logger.info(f"Generating campaign summary for {len(data)} contacts")
            
            # Generate campaign summary
            summary = self._generate_campaign_summary(data, campaign_info)
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(summary), f, indent=2, ensure_ascii=False, default=str)
            
            # Calculate metrics
            metrics.write_duration_ms = (time.time() - start_time) * 1000
            metrics.file_size_bytes = os.path.getsize(output_path)
            metrics.success = True
            
            self.logger.info(
                f"Campaign summary exported: {metrics.file_size_bytes:,} bytes, "
                f"{metrics.write_duration_ms:.1f}ms"
            )
            
        except Exception as e:
            metrics.error_message = str(e)
            metrics.write_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Campaign summary export failed: {e}")
        
        return metrics
    
    def export_proxy_performance(self, proxy_stats: Dict[str, Any],
                                output_path: str) -> ExportMetrics:
        """
        Export proxy performance metrics to JSON.
        
        Args:
            proxy_stats: Proxy performance data
            output_path: Output file path
            
        Returns:
            ExportMetrics with export performance data
        """
        start_time = time.time()
        metrics = ExportMetrics(
            export_format="JSON_PROXY_PERFORMANCE",
            output_path=output_path
        )
        
        try:
            self.logger.info("Generating proxy performance report")
            
            # Generate proxy performance summary
            performance = self._generate_proxy_performance(proxy_stats)
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(performance), f, indent=2, ensure_ascii=False, default=str)
            
            # Calculate metrics
            metrics.write_duration_ms = (time.time() - start_time) * 1000
            metrics.file_size_bytes = os.path.getsize(output_path)
            metrics.success = True
            
            self.logger.info(
                f"Proxy performance exported: {metrics.file_size_bytes:,} bytes, "
                f"{metrics.write_duration_ms:.1f}ms"
            )
            
        except Exception as e:
            metrics.error_message = str(e)
            metrics.write_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Proxy performance export failed: {e}")
        
        return metrics
    
    def _generate_campaign_summary(self, data: List[Dict[str, Any]], 
                                  campaign_info: Dict[str, Any]) -> CampaignSummary:
        """Generate comprehensive campaign summary"""
        
        # Calculate quality distribution
        quality_counts = {'high': 0, 'medium': 0, 'low': 0}
        contact_types = {'email': 0, 'website': 0, 'social': 0}
        confidence_scores = []
        platform_counts = {}
        
        for record in data:
            # Quality distribution
            confidence = record.get('contact_confidence', '').lower()
            if confidence in ['very_high', 'high']:
                quality_counts['high'] += 1
            elif confidence == 'medium':
                quality_counts['medium'] += 1
            else:
                quality_counts['low'] += 1
            
            # Contact types
            if record.get('host_email') or record.get('booking_email'):
                contact_types['email'] += 1
            elif record.get('podcast_website') or record.get('contact_page_url'):
                contact_types['website'] += 1
            elif record.get('social_links'):
                contact_types['social'] += 1
            
            # Confidence scores
            try:
                score = float(record.get('contact_quality_score', 0))
                if score > 0:
                    confidence_scores.append(score)
            except (ValueError, TypeError):
                pass
            
            # Platform distribution
            platform = record.get('platform_source', 'Unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        # Calculate averages
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        validation_success_rate = (quality_counts['high'] + quality_counts['medium']) / len(data) if data else 0.0
        
        return CampaignSummary(
            campaign_id=campaign_info.get('campaign_id', 'unknown'),
            topic=campaign_info.get('topic', 'unknown'),
            total_contacts=len(data),
            high_quality_contacts=quality_counts['high'],
            medium_quality_contacts=quality_counts['medium'],
            low_quality_contacts=quality_counts['low'],
            email_contacts=contact_types['email'],
            website_contacts=contact_types['website'],
            social_contacts=contact_types['social'],
            validation_success_rate=validation_success_rate,
            avg_confidence_score=avg_confidence,
            platform_distribution=platform_counts,
            processing_duration_minutes=campaign_info.get('processing_duration_minutes')
        )
    
    def _generate_proxy_performance(self, proxy_stats: Dict[str, Any]) -> ProxyPerformance:
        """Generate proxy performance summary"""
        
        total_requests = proxy_stats.get('total_requests', 0)
        successful_requests = proxy_stats.get('successful_requests', 0)
        failed_requests = proxy_stats.get('failed_requests', 0)
        
        success_rate = (successful_requests / total_requests) if total_requests > 0 else 0.0
        
        return ProxyPerformance(
            proxy_provider=proxy_stats.get('provider', 'unknown'),
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            avg_response_time_ms=proxy_stats.get('avg_response_time_ms', 0.0),
            blocked_count=proxy_stats.get('blocked_count', 0),
            rotation_count=proxy_stats.get('rotation_count', 0),
            bandwidth_used_mb=proxy_stats.get('bandwidth_used_mb', 0.0),
            cost_estimate=proxy_stats.get('cost_estimate'),
            errors_by_type=proxy_stats.get('errors_by_type', {})
        )


class ErrorLogManager:
    """
    Error logging system for tracking failures and issues.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Error log schema
        self.ERROR_LOG_SCHEMA = [
            'timestamp',
            'error_type',
            'error_message',
            'context',
            'severity',
            'component',
            'url',
            'retry_count',
            'resolution_status'
        ]
        
        self.logger.info("ErrorLogManager initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.ErrorLogManager")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def append_error(self, error_log_path: str, error_type: str, error_message: str,
                    context: str = "", severity: str = "medium", component: str = "",
                    url: str = "", retry_count: int = 0) -> bool:
        """
        Append error to error log CSV file.
        
        Args:
            error_log_path: Path to error log CSV file
            error_type: Type of error
            error_message: Error message
            context: Additional context
            severity: Error severity (low, medium, high, critical)
            component: Component where error occurred
            url: URL associated with error
            retry_count: Number of retries attempted
            
        Returns:
            Success status
        """
        try:
            error_record = {
                'timestamp': datetime.now().isoformat(),
                'error_type': error_type,
                'error_message': error_message,
                'context': context,
                'severity': severity,
                'component': component,
                'url': url,
                'retry_count': retry_count,
                'resolution_status': 'unresolved'
            }
            
            # Create directory if needed
            os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
            
            # Check if file exists to determine if header is needed
            file_exists = os.path.exists(error_log_path)
            
            # Append to CSV file
            with open(error_log_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.ERROR_LOG_SCHEMA)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(error_record)
            
            self.logger.debug(f"Error logged: {error_type} - {error_message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to append error log: {e}")
            return False


class ExporterAgent(Agent):
    """
    Agency Swarm agent for comprehensive export and reporting operations.
    
    This agent coordinates all export functionality including CSV, JSON, analytics,
    error logging, and provides the final deliverables for podcast contact discovery.
    """
    
    def __init__(self):
        super().__init__(
            name="Exporter",
            description="Exports and reports validated contact data with comprehensive CSV, JSON, analytics, and Google Drive integration for podcast contact discovery results",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.1,
            max_prompt_tokens=25000,
        )
        
        # Initialize export components
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONStatsExporter()
        self.error_logger = ErrorLogManager()
        
        # Configuration
        self.output_dir = self._ensure_output_dir()
        
        # Statistics
        self.export_stats = {
            'exports_completed': 0,
            'total_records_exported': 0,
            'total_export_time_ms': 0.0,
            'errors_logged': 0
        }
        
        self.logger = logging.getLogger(f"{__name__}.ExporterAgent")
        self.logger.info("ExporterAgent initialized")
    
    def _ensure_output_dir(self) -> str:
        """Ensure output directory exists"""
        output_dir = os.path.join(os.getcwd(), "output", "exports")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def export_comprehensive_results(self, contact_data: List[Dict[str, Any]], 
                                   campaign_info: Dict[str, Any],
                                   proxy_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export comprehensive results including CSV, JSON stats, and error logs.
        
        Args:
            contact_data: Validated contact data
            campaign_info: Campaign metadata
            proxy_stats: Optional proxy performance data
            
        Returns:
            Dictionary with export results and file paths
        """
        start_time = time.time()
        results = {
            'success': False,
            'exports': {},
            'total_contacts': len(contact_data),
            'export_duration_ms': 0.0,
            'errors': []
        }
        
        try:
            self.logger.info(f"Starting comprehensive export for {len(contact_data)} contacts")
            
            # Generate timestamped file names
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"podcast_contacts_{timestamp}"
            
            # 1. Export main CSV file
            csv_path = os.path.join(self.output_dir, f"{base_name}.csv")
            csv_metrics = self.csv_exporter.export_to_csv(contact_data, csv_path)
            results['exports']['csv'] = {
                'path': csv_path,
                'metrics': asdict(csv_metrics)
            }
            
            if not csv_metrics.success:
                results['errors'].append(f"CSV export failed: {csv_metrics.error_message}")
            
            # 2. Export campaign summary JSON
            summary_path = os.path.join(self.output_dir, f"campaign_summary_{timestamp}.json")
            summary_metrics = self.json_exporter.export_campaign_summary(
                contact_data, campaign_info, summary_path
            )
            results['exports']['campaign_summary'] = {
                'path': summary_path,
                'metrics': asdict(summary_metrics)
            }
            
            if not summary_metrics.success:
                results['errors'].append(f"Campaign summary export failed: {summary_metrics.error_message}")
            
            # 3. Export proxy performance JSON (if data available)
            if proxy_stats:
                proxy_path = os.path.join(self.output_dir, f"proxy_performance_{timestamp}.json")
                proxy_metrics = self.json_exporter.export_proxy_performance(proxy_stats, proxy_path)
                results['exports']['proxy_performance'] = {
                    'path': proxy_path,
                    'metrics': asdict(proxy_metrics)
                }
                
                if not proxy_metrics.success:
                    results['errors'].append(f"Proxy performance export failed: {proxy_metrics.error_message}")
            
            # 4. Create error log if any errors occurred during processing
            error_log_path = os.path.join(self.output_dir, f"error_log_{timestamp}.csv")
            
            # Log any export errors
            for error in results['errors']:
                self.error_logger.append_error(
                    error_log_path, 
                    "export_error", 
                    error,
                    context="comprehensive_export",
                    severity="medium",
                    component="exporter_agent"
                )
            
            if os.path.exists(error_log_path):
                results['exports']['error_log'] = {'path': error_log_path}
            
            # Calculate overall success
            successful_exports = sum(1 for exp in results['exports'].values() 
                                   if exp.get('metrics', {}).get('success', True))
            total_exports = len(results['exports'])
            results['success'] = successful_exports == total_exports and len(results['errors']) == 0
            
            # Update statistics
            self.export_stats['exports_completed'] += 1
            self.export_stats['total_records_exported'] += len(contact_data)
            
            results['export_duration_ms'] = (time.time() - start_time) * 1000
            self.export_stats['total_export_time_ms'] += results['export_duration_ms']
            
            self.logger.info(
                f"Comprehensive export completed: {successful_exports}/{total_exports} successful, "
                f"{results['export_duration_ms']:.1f}ms"
            )
            
        except Exception as e:
            results['export_duration_ms'] = (time.time() - start_time) * 1000
            results['errors'].append(f"Export process failed: {str(e)}")
            self.logger.error(f"Comprehensive export failed: {e}")
        
        return results
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export performance statistics"""
        stats = self.export_stats.copy()
        
        if stats['exports_completed'] > 0:
            stats['avg_export_time_ms'] = stats['total_export_time_ms'] / stats['exports_completed']
            stats['avg_records_per_export'] = stats['total_records_exported'] / stats['exports_completed']
        
        return stats