"""
Validation Reporting Tool

Agency Swarm tool for comprehensive validation and deduplication reporting.
Provides detailed analytics, performance metrics, and configurable reporting
for email validation workflows.
"""

import logging
import json
import time
import os
from typing import Dict, Any, List, Optional, Set
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pydantic import Field

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


@dataclass
class ValidationSummary:
    """Summary of validation results"""
    total_processed: int = 0
    valid_emails: int = 0
    invalid_emails: int = 0
    acceptance_rate: float = 0.0
    processing_time_seconds: float = 0.0
    emails_per_second: float = 0.0
    
    # Quality distribution
    high_quality: int = 0
    medium_quality: int = 0
    low_quality: int = 0
    spam_quality: int = 0
    
    # Rejection reasons
    syntax_errors: int = 0
    domain_errors: int = 0
    blacklisted: int = 0
    duplicates: int = 0
    dns_errors: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ValidationReportingTool(BaseTool):
    """
    Tool for generating comprehensive validation and deduplication reports.
    
    Analyzes validation results and generates detailed reports with metrics,
    charts data, and actionable insights.
    """
    
    validation_results: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation results to analyze and report on"
    )
    
    include_detailed_breakdown: bool = Field(
        default=True,
        description="Include detailed breakdown by rejection reasons and patterns"
    )
    
    include_performance_metrics: bool = Field(
        default=True,
        description="Include performance and timing analysis"
    )
    
    include_quality_analysis: bool = Field(
        default=True,
        description="Include email quality distribution and analysis"
    )
    
    include_domain_analysis: bool = Field(
        default=True,
        description="Include domain-level analysis and statistics"
    )
    
    include_recommendations: bool = Field(
        default=True,
        description="Include actionable recommendations based on analysis"
    )
    
    generate_charts_data: bool = Field(
        default=True,
        description="Generate data suitable for charts and visualizations"
    )
    
    verbosity_level: str = Field(
        default="standard",
        description="Report verbosity level: minimal, standard, detailed, comprehensive"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.
        
        Returns:
            Dictionary with detailed validation analysis and reporting
        """
        if not self.validation_results:
            return {'error': 'No validation results provided'}
        
        start_time = time.time()
        
        # Generate core summary
        summary = self._generate_summary()
        
        # Build report sections based on configuration
        report = {
            'summary': summary.to_dict(),
            'metadata': {
                'report_generated_at': datetime.now().isoformat(),
                'total_results_analyzed': len(self.validation_results),
                'report_generation_time_ms': 0,  # Will be updated at end
                'verbosity_level': self.verbosity_level
            }
        }
        
        # Add detailed sections based on configuration and verbosity
        if self.include_detailed_breakdown and self._should_include_section('breakdown'):
            report['detailed_breakdown'] = self._generate_detailed_breakdown()
        
        if self.include_performance_metrics and self._should_include_section('performance'):
            report['performance_metrics'] = self._generate_performance_metrics()
        
        if self.include_quality_analysis and self._should_include_section('quality'):
            report['quality_analysis'] = self._generate_quality_analysis()
        
        if self.include_domain_analysis and self._should_include_section('domain'):
            report['domain_analysis'] = self._generate_domain_analysis()
        
        if self.generate_charts_data and self._should_include_section('charts'):
            report['charts_data'] = self._generate_charts_data()
        
        if self.include_recommendations and self._should_include_section('recommendations'):
            report['recommendations'] = self._generate_recommendations()
        
        # Add trend analysis for comprehensive reports
        if self.verbosity_level == 'comprehensive':
            report['trend_analysis'] = self._generate_trend_analysis()
            report['comparative_analysis'] = self._generate_comparative_analysis()
        
        # Update generation time
        generation_time = (time.time() - start_time) * 1000
        report['metadata']['report_generation_time_ms'] = generation_time
        
        return report
    
    def _should_include_section(self, section: str) -> bool:
        """Determine if section should be included based on verbosity level"""
        section_levels = {
            'breakdown': ['standard', 'detailed', 'comprehensive'],
            'performance': ['standard', 'detailed', 'comprehensive'],
            'quality': ['detailed', 'comprehensive'],
            'domain': ['detailed', 'comprehensive'],
            'charts': ['standard', 'detailed', 'comprehensive'],
            'recommendations': ['standard', 'detailed', 'comprehensive']
        }
        
        return self.verbosity_level in section_levels.get(section, [])
    
    def _generate_summary(self) -> ValidationSummary:
        """Generate high-level validation summary"""
        summary = ValidationSummary()
        
        total_time = 0.0
        
        for result in self.validation_results:
            summary.total_processed += 1
            
            if result.get('is_valid', False):
                summary.valid_emails += 1
            else:
                summary.invalid_emails += 1
            
            # Quality distribution
            quality = result.get('quality', 'spam')
            if quality == 'high':
                summary.high_quality += 1
            elif quality == 'medium':
                summary.medium_quality += 1
            elif quality == 'low':
                summary.low_quality += 1
            else:
                summary.spam_quality += 1
            
            # Rejection reasons
            status = result.get('status', '')
            if 'syntax' in status.lower():
                summary.syntax_errors += 1
            elif 'domain' in status.lower():
                summary.domain_errors += 1
            elif 'blacklist' in status.lower():
                summary.blacklisted += 1
            elif 'duplicate' in status.lower():
                summary.duplicates += 1
            elif 'dns' in status.lower():
                summary.dns_errors += 1
            
            # Accumulate processing time
            total_time += result.get('validation_time_ms', 0)
        
        # Calculate rates and metrics
        if summary.total_processed > 0:
            summary.acceptance_rate = summary.valid_emails / summary.total_processed
            summary.processing_time_seconds = total_time / 1000.0
            
            if summary.processing_time_seconds > 0:
                summary.emails_per_second = summary.total_processed / summary.processing_time_seconds
        
        return summary
    
    def _generate_detailed_breakdown(self) -> Dict[str, Any]:
        """Generate detailed breakdown of validation results"""
        
        # Rejection reason analysis
        rejection_reasons = Counter()
        status_breakdown = Counter()
        
        # Pattern analysis
        blacklist_patterns = Counter()
        validation_times = []
        
        for result in self.validation_results:
            status = result.get('status', 'unknown')
            status_breakdown[status] += 1
            
            if not result.get('is_valid', False):
                reason = result.get('reason', 'Unknown reason')
                rejection_reasons[reason] += 1
                
                # Track blacklist patterns
                if 'blacklist' in status.lower():
                    pattern = result.get('matched_pattern', 'Unknown pattern')
                    blacklist_patterns[pattern] += 1
            
            # Collect timing data
            validation_time = result.get('validation_time_ms', 0)
            if validation_time > 0:
                validation_times.append(validation_time)
        
        # Calculate timing statistics
        timing_stats = {}
        if validation_times:
            timing_stats = {
                'min_time_ms': min(validation_times),
                'max_time_ms': max(validation_times),
                'avg_time_ms': sum(validation_times) / len(validation_times),
                'median_time_ms': sorted(validation_times)[len(validation_times) // 2],
                'slow_validations': len([t for t in validation_times if t > 1000]),  # > 1 second
                'fast_validations': len([t for t in validation_times if t < 100])    # < 100ms
            }
        
        return {
            'status_breakdown': dict(status_breakdown.most_common()),
            'rejection_reasons': dict(rejection_reasons.most_common(20)),
            'blacklist_patterns': dict(blacklist_patterns.most_common(15)),
            'timing_statistics': timing_stats,
            'validation_distribution': {
                'total_with_timing_data': len(validation_times),
                'average_validation_time_ms': timing_stats.get('avg_time_ms', 0),
                'performance_categories': {
                    'fast_validations': timing_stats.get('fast_validations', 0),
                    'normal_validations': len(validation_times) - timing_stats.get('fast_validations', 0) - timing_stats.get('slow_validations', 0),
                    'slow_validations': timing_stats.get('slow_validations', 0)
                }
            }
        }
    
    def _generate_performance_metrics(self) -> Dict[str, Any]:
        """Generate performance analysis metrics"""
        
        # Calculate throughput metrics
        total_emails = len(self.validation_results)
        total_time_ms = sum(r.get('validation_time_ms', 0) for r in self.validation_results)
        total_time_seconds = total_time_ms / 1000.0
        
        # Efficiency metrics
        valid_emails = sum(1 for r in self.validation_results if r.get('is_valid', False))
        dns_checks = sum(1 for r in self.validation_results if r.get('mx_records'))
        cache_hits = sum(1 for r in self.validation_results if r.get('cache_hit', False))
        
        # Performance categories
        fast_validations = sum(1 for r in self.validation_results if r.get('validation_time_ms', 0) < 100)
        slow_validations = sum(1 for r in self.validation_results if r.get('validation_time_ms', 0) > 1000)
        
        # Resource utilization
        dns_utilization = dns_checks / max(1, total_emails)
        cache_efficiency = cache_hits / max(1, total_emails)
        
        return {
            'throughput': {
                'total_emails_processed': total_emails,
                'total_processing_time_seconds': total_time_seconds,
                'emails_per_second': total_emails / max(0.001, total_time_seconds),
                'average_time_per_email_ms': total_time_ms / max(1, total_emails)
            },
            'efficiency': {
                'validation_success_rate': valid_emails / max(1, total_emails),
                'dns_utilization_rate': dns_utilization,
                'cache_hit_rate': cache_efficiency,
                'fast_validation_rate': fast_validations / max(1, total_emails),
                'slow_validation_rate': slow_validations / max(1, total_emails)
            },
            'resource_usage': {
                'dns_queries_performed': dns_checks,
                'cache_hits': cache_hits,
                'cache_misses': total_emails - cache_hits,
                'total_validation_operations': total_emails
            },
            'performance_recommendations': self._generate_performance_recommendations(
                total_emails, dns_utilization, cache_efficiency, slow_validations
            )
        }
    
    def _generate_quality_analysis(self) -> Dict[str, Any]:
        """Generate email quality analysis"""
        
        # Quality distribution
        quality_counts = Counter()
        confidence_scores = []
        
        # Domain quality analysis
        domain_quality = defaultdict(lambda: {'high': 0, 'medium': 0, 'low': 0, 'spam': 0})
        
        # Pattern analysis
        high_quality_patterns = []
        low_quality_patterns = []
        
        for result in self.validation_results:
            quality = result.get('quality', 'spam')
            quality_counts[quality] += 1
            
            confidence = result.get('confidence_score', 0)
            confidence_scores.append(confidence)
            
            # Domain quality tracking
            email = result.get('email', '')
            if '@' in email:
                domain = email.split('@')[1].lower()
                domain_quality[domain][quality] += 1
            
            # Pattern tracking
            if quality == 'high' and confidence > 0.8:
                local_part = email.split('@')[0] if '@' in email else ''
                if local_part:
                    high_quality_patterns.append(local_part)
            elif quality in ['spam', 'low'] and confidence < 0.3:
                local_part = email.split('@')[0] if '@' in email else ''
                if local_part:
                    low_quality_patterns.append(local_part)
        
        # Confidence statistics
        confidence_stats = {}
        if confidence_scores:
            confidence_stats = {
                'min_confidence': min(confidence_scores),
                'max_confidence': max(confidence_scores),
                'avg_confidence': sum(confidence_scores) / len(confidence_scores),
                'median_confidence': sorted(confidence_scores)[len(confidence_scores) // 2],
                'high_confidence_emails': len([c for c in confidence_scores if c > 0.7]),
                'low_confidence_emails': len([c for c in confidence_scores if c < 0.3])
            }
        
        # Top domains by quality
        quality_domains = []
        for domain, qualities in domain_quality.items():
            total = sum(qualities.values())
            if total >= 3:  # Only domains with sufficient data
                high_ratio = qualities['high'] / total
                quality_domains.append({
                    'domain': domain,
                    'total_emails': total,
                    'high_quality_ratio': high_ratio,
                    'quality_distribution': dict(qualities)
                })
        
        quality_domains.sort(key=lambda x: (x['high_quality_ratio'], x['total_emails']), reverse=True)
        
        return {
            'quality_distribution': dict(quality_counts),
            'confidence_analysis': confidence_stats,
            'top_quality_domains': quality_domains[:15],
            'pattern_analysis': {
                'high_quality_patterns': dict(Counter(high_quality_patterns).most_common(10)),
                'low_quality_patterns': dict(Counter(low_quality_patterns).most_common(10))
            },
            'quality_recommendations': self._generate_quality_recommendations(
                quality_counts, confidence_stats
            )
        }
    
    def _generate_domain_analysis(self) -> Dict[str, Any]:
        """Generate domain-level analysis"""
        
        # Domain statistics
        domain_stats = defaultdict(lambda: {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'high_quality': 0,
            'avg_confidence': 0,
            'confidence_scores': []
        })
        
        # TLD analysis
        tld_stats = defaultdict(lambda: {'total': 0, 'valid': 0})
        
        # Business vs personal domains
        business_domains = set()
        personal_domains = set()
        
        for result in self.validation_results:
            email = result.get('email', '')
            if '@' not in email:
                continue
            
            domain = email.split('@')[1].lower()
            stats = domain_stats[domain]
            
            stats['total'] += 1
            confidence = result.get('confidence_score', 0)
            stats['confidence_scores'].append(confidence)
            
            if result.get('is_valid', False):
                stats['valid'] += 1
            else:
                stats['invalid'] += 1
            
            if result.get('quality') == 'high':
                stats['high_quality'] += 1
            
            # TLD analysis
            tld = domain.split('.')[-1]
            tld_stats[tld]['total'] += 1
            if result.get('is_valid', False):
                tld_stats[tld]['valid'] += 1
            
            # Business vs personal classification
            if result.get('is_business_domain', False):
                business_domains.add(domain)
            if result.get('is_personal_domain', False):
                personal_domains.add(domain)
        
        # Calculate averages
        for domain, stats in domain_stats.items():
            if stats['confidence_scores']:
                stats['avg_confidence'] = sum(stats['confidence_scores']) / len(stats['confidence_scores'])
                stats['validation_rate'] = stats['valid'] / stats['total']
                stats['quality_rate'] = stats['high_quality'] / max(1, stats['valid'])
            del stats['confidence_scores']  # Remove raw data
        
        # Sort domains by various metrics
        domains_by_volume = sorted(
            [(d, s) for d, s in domain_stats.items()],
            key=lambda x: x[1]['total'],
            reverse=True
        )[:20]
        
        domains_by_quality = sorted(
            [(d, s) for d, s in domain_stats.items() if s['total'] >= 3],
            key=lambda x: (x[1]['quality_rate'], x[1]['avg_confidence']),
            reverse=True
        )[:15]
        
        # TLD analysis
        tld_analysis = []
        for tld, stats in tld_stats.items():
            if stats['total'] >= 5:  # Only TLDs with sufficient data
                tld_analysis.append({
                    'tld': tld,
                    'total_emails': stats['total'],
                    'valid_emails': stats['valid'],
                    'validation_rate': stats['valid'] / stats['total']
                })
        
        tld_analysis.sort(key=lambda x: (x['validation_rate'], x['total_emails']), reverse=True)
        
        return {
            'domain_overview': {
                'total_unique_domains': len(domain_stats),
                'business_domains': len(business_domains),
                'personal_domains': len(personal_domains),
                'total_unique_tlds': len(tld_stats)
            },
            'top_domains_by_volume': [
                {'domain': d, 'stats': s} for d, s in domains_by_volume
            ],
            'top_domains_by_quality': [
                {'domain': d, 'stats': s} for d, s in domains_by_quality
            ],
            'tld_analysis': tld_analysis[:20],
            'domain_recommendations': self._generate_domain_recommendations(
                domain_stats, business_domains, personal_domains
            )
        }
    
    def _generate_charts_data(self) -> Dict[str, Any]:
        """Generate data suitable for charts and visualizations"""
        
        # Quality distribution pie chart
        quality_dist = Counter()
        for result in self.validation_results:
            quality_dist[result.get('quality', 'spam')] += 1
        
        # Validation timeline (if timestamps available)
        timeline_data = []
        
        # Status distribution
        status_dist = Counter()
        for result in self.validation_results:
            status_dist[result.get('status', 'unknown')] += 1
        
        # Confidence score histogram
        confidence_ranges = {
            '0.0-0.2': 0, '0.2-0.4': 0, '0.4-0.6': 0,
            '0.6-0.8': 0, '0.8-1.0': 0
        }
        
        for result in self.validation_results:
            confidence = result.get('confidence_score', 0)
            if confidence < 0.2:
                confidence_ranges['0.0-0.2'] += 1
            elif confidence < 0.4:
                confidence_ranges['0.2-0.4'] += 1
            elif confidence < 0.6:
                confidence_ranges['0.4-0.6'] += 1
            elif confidence < 0.8:
                confidence_ranges['0.6-0.8'] += 1
            else:
                confidence_ranges['0.8-1.0'] += 1
        
        # Performance chart data
        validation_times = [r.get('validation_time_ms', 0) for r in self.validation_results]
        time_ranges = {
            '0-50ms': len([t for t in validation_times if 0 <= t < 50]),
            '50-100ms': len([t for t in validation_times if 50 <= t < 100]),
            '100-500ms': len([t for t in validation_times if 100 <= t < 500]),
            '500-1000ms': len([t for t in validation_times if 500 <= t < 1000]),
            '1000ms+': len([t for t in validation_times if t >= 1000])
        }
        
        return {
            'quality_distribution': {
                'chart_type': 'pie',
                'data': dict(quality_dist),
                'title': 'Email Quality Distribution'
            },
            'status_distribution': {
                'chart_type': 'bar',
                'data': dict(status_dist.most_common(10)),
                'title': 'Validation Status Breakdown'
            },
            'confidence_histogram': {
                'chart_type': 'bar',
                'data': confidence_ranges,
                'title': 'Confidence Score Distribution'
            },
            'performance_chart': {
                'chart_type': 'bar',
                'data': time_ranges,
                'title': 'Validation Time Distribution'
            }
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Calculate key metrics
        total_emails = len(self.validation_results)
        valid_emails = sum(1 for r in self.validation_results if r.get('is_valid', False))
        acceptance_rate = valid_emails / max(1, total_emails)
        
        # Quality analysis
        high_quality = sum(1 for r in self.validation_results if r.get('quality') == 'high')
        high_quality_rate = high_quality / max(1, valid_emails)
        
        # Performance analysis
        slow_validations = sum(1 for r in self.validation_results if r.get('validation_time_ms', 0) > 1000)
        slow_rate = slow_validations / max(1, total_emails)
        
        # Generate recommendations
        if acceptance_rate < 0.6:
            recommendations.append(
                f"Low acceptance rate ({acceptance_rate:.1%}). Consider reviewing email sources "
                "and improving data quality at collection time."
            )
        
        if high_quality_rate < 0.3:
            recommendations.append(
                f"Low high-quality email rate ({high_quality_rate:.1%}). Consider targeting "
                "more professional email patterns and business domains."
            )
        
        if slow_rate > 0.1:
            recommendations.append(
                f"High slow validation rate ({slow_rate:.1%}). Consider implementing "
                "more aggressive caching and optimizing DNS timeout settings."
            )
        
        # Domain recommendations
        domain_count = len(set(r.get('email', '').split('@')[1] for r in self.validation_results if '@' in r.get('email', '')))
        if domain_count < total_emails * 0.1:
            recommendations.append(
                "Low domain diversity detected. Consider expanding data sources "
                "to capture more varied business contacts."
            )
        
        return recommendations
    
    def _generate_performance_recommendations(self, total_emails: int, dns_utilization: float, 
                                           cache_efficiency: float, slow_validations: int) -> List[str]:
        """Generate performance-specific recommendations"""
        recommendations = []
        
        if dns_utilization > 0.8:
            recommendations.append(
                "High DNS utilization detected. Consider implementing DNS result caching "
                "or reducing DNS timeout values for better performance."
            )
        
        if cache_efficiency < 0.3:
            recommendations.append(
                "Low cache efficiency detected. Consider increasing cache TTL or "
                "processing emails in domain-grouped batches."
            )
        
        if slow_validations > total_emails * 0.15:
            recommendations.append(
                "Many slow validations detected. Consider implementing parallel processing "
                "or reducing validation timeout thresholds."
            )
        
        return recommendations
    
    def _generate_quality_recommendations(self, quality_counts: Counter, 
                                        confidence_stats: Dict[str, Any]) -> List[str]:
        """Generate quality-specific recommendations"""
        recommendations = []
        
        total = sum(quality_counts.values())
        high_rate = quality_counts.get('high', 0) / max(1, total)
        spam_rate = quality_counts.get('spam', 0) / max(1, total)
        
        if high_rate < 0.2:
            recommendations.append(
                f"Low high-quality rate ({high_rate:.1%}). Consider improving email "
                "collection strategies to target business professionals."
            )
        
        if spam_rate > 0.3:
            recommendations.append(
                f"High spam rate ({spam_rate:.1%}). Consider strengthening blacklist "
                "patterns and improving source data quality."
            )
        
        avg_confidence = confidence_stats.get('avg_confidence', 0)
        if avg_confidence < 0.5:
            recommendations.append(
                f"Low average confidence ({avg_confidence:.2f}). Consider reviewing "
                "scoring algorithms and quality assessment criteria."
            )
        
        return recommendations
    
    def _generate_domain_recommendations(self, domain_stats: Dict, business_domains: Set, 
                                       personal_domains: Set) -> List[str]:
        """Generate domain-specific recommendations"""
        recommendations = []
        
        total_domains = len(domain_stats)
        business_ratio = len(business_domains) / max(1, total_domains)
        personal_ratio = len(personal_domains) / max(1, total_domains)
        
        if personal_ratio > 0.5:
            recommendations.append(
                f"High personal domain ratio ({personal_ratio:.1%}). Consider filtering "
                "for business domains to improve lead quality."
            )
        
        if business_ratio < 0.2:
            recommendations.append(
                f"Low business domain ratio ({business_ratio:.1%}). Consider targeting "
                "professional networks and business directories."
            )
        
        # Check for domain concentration
        domain_volumes = [stats['total'] for stats in domain_stats.values()]
        if domain_volumes:
            max_volume = max(domain_volumes)
            total_volume = sum(domain_volumes)
            concentration = max_volume / total_volume
            
            if concentration > 0.3:
                recommendations.append(
                    f"High domain concentration ({concentration:.1%}). Consider diversifying "
                    "email sources to reduce dependency on single domains."
                )
        
        return recommendations
    
    def _generate_trend_analysis(self) -> Dict[str, Any]:
        """Generate trend analysis (for comprehensive reports)"""
        # This would analyze trends over time if timestamp data is available
        # For now, return placeholder structure
        return {
            'note': 'Trend analysis requires timestamp data in validation results',
            'temporal_patterns': {},
            'performance_trends': {},
            'quality_trends': {}
        }
    
    def _generate_comparative_analysis(self) -> Dict[str, Any]:
        """Generate comparative analysis (for comprehensive reports)"""
        # This would compare against historical data or benchmarks
        # For now, return placeholder structure
        return {
            'note': 'Comparative analysis requires historical baseline data',
            'benchmark_comparison': {},
            'historical_comparison': {},
            'industry_benchmarks': {}
        }


class ValidationLoggerTool(BaseTool):
    """
    Tool for structured logging of validation results with configurable verbosity.
    
    Provides machine-readable logs for analysis and debugging with different
    verbosity levels and output formats.
    """
    
    validation_results: List[Dict[str, Any]] = Field(
        ...,
        description="Validation results to log"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR"
    )
    
    log_format: str = Field(
        default="structured",
        description="Log format: structured, json, csv, plain"
    )
    
    include_accepted: bool = Field(
        default=True,
        description="Include accepted emails in logs"
    )
    
    include_rejected: bool = Field(
        default=True,
        description="Include rejected emails in logs"
    )
    
    output_file: Optional[str] = Field(
        default=None,
        description="Optional file path to write logs to"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Generate structured logs for validation results.
        
        Returns:
            Dictionary with logging summary and log entries
        """
        # Setup logging
        logger = logging.getLogger('ValidationLogger')
        logger.setLevel(getattr(logging, self.log_level.upper()))
        
        log_entries = []
        stats = {'accepted_logged': 0, 'rejected_logged': 0, 'total_logged': 0}
        
        for result in self.validation_results:
            is_valid = result.get('is_valid', False)
            
            # Filter based on configuration
            if is_valid and not self.include_accepted:
                continue
            if not is_valid and not self.include_rejected:
                continue
            
            # Create log entry
            log_entry = self._create_log_entry(result)
            log_entries.append(log_entry)
            
            # Update stats
            stats['total_logged'] += 1
            if is_valid:
                stats['accepted_logged'] += 1
            else:
                stats['rejected_logged'] += 1
            
            # Log to logger
            self._log_entry(logger, result, log_entry)
        
        # Write to file if specified
        if self.output_file:
            self._write_log_file(log_entries)
        
        return {
            'logging_summary': {
                'total_results': len(self.validation_results),
                'entries_logged': stats['total_logged'],
                'accepted_logged': stats['accepted_logged'],
                'rejected_logged': stats['rejected_logged'],
                'log_format': self.log_format,
                'log_level': self.log_level,
                'output_file': self.output_file
            },
            'log_entries': log_entries if self.log_format in ['json', 'structured'] else [],
            'sample_logs': log_entries[:10] if len(log_entries) > 10 else log_entries
        }
    
    def _create_log_entry(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured log entry from validation result"""
        return {
            'timestamp': datetime.now().isoformat(),
            'email': result.get('email', ''),
            'status': result.get('status', ''),
            'is_valid': result.get('is_valid', False),
            'quality': result.get('quality', ''),
            'confidence_score': result.get('confidence_score', 0),
            'reason': result.get('reason', ''),
            'domain': result.get('domain', ''),
            'validation_time_ms': result.get('validation_time_ms', 0),
            'matched_pattern': result.get('matched_pattern'),
            'mx_records': result.get('mx_records', [])
        }
    
    def _log_entry(self, logger: logging.Logger, result: Dict[str, Any], log_entry: Dict[str, Any]):
        """Log entry using configured logger"""
        email = result.get('email', '')
        is_valid = result.get('is_valid', False)
        reason = result.get('reason', '')
        
        if is_valid:
            logger.info(f"ACCEPTED: {email} (quality: {result.get('quality', 'unknown')})")
        else:
            logger.warning(f"REJECTED: {email} - {reason}")
    
    def _write_log_file(self, log_entries: List[Dict[str, Any]]):
        """Write log entries to file in specified format"""
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                if self.log_format == 'json':
                    json.dump(log_entries, f, indent=2, default=str)
                elif self.log_format == 'csv':
                    import csv
                    if log_entries:
                        writer = csv.DictWriter(f, fieldnames=log_entries[0].keys())
                        writer.writeheader()
                        writer.writerows(log_entries)
                elif self.log_format == 'plain':
                    for entry in log_entries:
                        status = 'ACCEPTED' if entry['is_valid'] else 'REJECTED'
                        f.write(f"{entry['timestamp']} - {status}: {entry['email']} - {entry['reason']}\n")
                else:  # structured
                    for entry in log_entries:
                        f.write(f"{json.dumps(entry)}\n")
                        
        except Exception as e:
            logging.error(f"Failed to write log file {self.output_file}: {e}")