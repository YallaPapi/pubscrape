"""
Email Metrics and Reporting Tool

Agency Swarm tool for generating comprehensive metrics and reports 
on email extraction performance and quality distribution.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from pydantic import Field, BaseModel
from collections import defaultdict, Counter
import json

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool(BaseModel):
        pass


class EmailMetricsTool(BaseTool):
    """
    Tool for generating comprehensive email extraction metrics and quality analysis.
    
    Analyzes email extraction results to provide insights into:
    - Extraction performance by source and method
    - Quality distribution and scoring patterns
    - Domain and pattern analysis
    - Success rates and efficiency metrics
    """
    
    name: str = "email_metrics_analysis"
    description: str = "Generate comprehensive metrics and analysis of email extraction results"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailMetricsTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run(self, 
            extraction_results: Dict[str, Any],
            include_detailed_analysis: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive metrics from email extraction results.
        
        Args:
            extraction_results: Results from bulk email extraction
            include_detailed_analysis: Whether to include detailed breakdowns
            
        Returns:
            Dictionary containing comprehensive metrics and analysis
        """
        try:
            self.logger.info("Generating email extraction metrics")
            
            # Extract data from results
            page_results = extraction_results.get('page_results', {})
            all_candidates = extraction_results.get('all_candidates', [])
            
            # Generate metrics
            metrics = {
                'extraction_overview': self._generate_overview_metrics(extraction_results),
                'quality_distribution': self._analyze_quality_distribution(all_candidates),
                'source_analysis': self._analyze_extraction_sources(all_candidates),
                'method_analysis': self._analyze_extraction_methods(all_candidates),
                'page_performance': self._analyze_page_performance(page_results),
                'domain_analysis': self._analyze_domain_patterns(all_candidates),
                'timestamp': time.time(),
                'report_id': f"email_metrics_{int(time.time())}"
            }
            
            if include_detailed_analysis:
                metrics.update({
                    'detailed_breakdown': self._generate_detailed_breakdown(all_candidates),
                    'efficiency_metrics': self._calculate_efficiency_metrics(extraction_results),
                    'quality_trends': self._analyze_quality_trends(all_candidates),
                    'recommendations': self._generate_recommendations(metrics)
                })
            
            self.logger.info(f"Metrics generated for {len(all_candidates)} candidates across {len(page_results)} pages")
            
            return {
                'success': True,
                'metrics': metrics,
                'summary': self._generate_summary(metrics)
            }
            
        except Exception as e:
            error_msg = f"Email metrics generation failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'metrics': {},
                'summary': {}
            }
    
    def _generate_overview_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level overview metrics"""
        return {
            'total_pages_processed': results.get('pages_processed', 0),
            'pages_with_emails': results.get('pages_with_emails', 0),
            'total_candidates_found': results.get('total_candidates', 0),
            'unique_high_quality_emails': results.get('unique_high_quality', 0),
            'unique_business_emails': results.get('unique_business_emails', 0),
            'total_extraction_time_ms': results.get('total_extraction_time_ms', 0),
            'average_extraction_time_ms': results.get('avg_extraction_time_ms', 0),
            'success_rate': (results.get('pages_with_emails', 0) / max(1, results.get('pages_processed', 1))) * 100
        }
    
    def _analyze_quality_distribution(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the distribution of email quality levels"""
        quality_counts = Counter()
        confidence_scores = []
        
        for candidate in candidates:
            quality = candidate.get('quality', 'unknown')
            quality_counts[quality] += 1
            
            score = candidate.get('confidence_score', 0.0)
            if isinstance(score, (int, float)):
                confidence_scores.append(score)
        
        # Calculate confidence score statistics
        conf_stats = {}
        if confidence_scores:
            conf_stats = {
                'mean': sum(confidence_scores) / len(confidence_scores),
                'min': min(confidence_scores),
                'max': max(confidence_scores),
                'median': sorted(confidence_scores)[len(confidence_scores) // 2]
            }
        
        return {
            'quality_distribution': dict(quality_counts),
            'quality_percentages': {
                quality: (count / max(1, len(candidates))) * 100 
                for quality, count in quality_counts.items()
            },
            'confidence_score_stats': conf_stats,
            'high_confidence_count': len([s for s in confidence_scores if s >= 0.7]),
            'medium_confidence_count': len([s for s in confidence_scores if 0.4 <= s < 0.7]),
            'low_confidence_count': len([s for s in confidence_scores if s < 0.4])
        }
    
    def _analyze_extraction_sources(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email extraction by source type"""
        source_stats = defaultdict(lambda: {
            'count': 0,
            'avg_confidence': 0.0,
            'quality_distribution': Counter()
        })
        
        for candidate in candidates:
            source = candidate.get('source', 'unknown')
            confidence = candidate.get('confidence_score', 0.0)
            quality = candidate.get('quality', 'unknown')
            
            source_stats[source]['count'] += 1
            source_stats[source]['avg_confidence'] += confidence
            source_stats[source]['quality_distribution'][quality] += 1
        
        # Calculate averages
        for source, stats in source_stats.items():
            if stats['count'] > 0:
                stats['avg_confidence'] /= stats['count']
                stats['quality_distribution'] = dict(stats['quality_distribution'])
        
        return dict(source_stats)
    
    def _analyze_extraction_methods(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email extraction by method"""
        method_stats = defaultdict(lambda: {
            'count': 0,
            'success_rate': 0.0,
            'avg_quality_score': 0.0
        })
        
        for candidate in candidates:
            method = candidate.get('extraction_method', 'unknown')
            is_valid = candidate.get('validation_status') == 'Valid'
            confidence = candidate.get('confidence_score', 0.0)
            
            method_stats[method]['count'] += 1
            if is_valid:
                method_stats[method]['success_rate'] += 1
            method_stats[method]['avg_quality_score'] += confidence
        
        # Calculate rates and averages
        for method, stats in method_stats.items():
            if stats['count'] > 0:
                stats['success_rate'] = (stats['success_rate'] / stats['count']) * 100
                stats['avg_quality_score'] /= stats['count']
        
        return dict(method_stats)
    
    def _analyze_page_performance(self, page_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze extraction performance by page"""
        performance_stats = {
            'pages_by_candidate_count': Counter(),
            'avg_candidates_per_page': 0.0,
            'top_performing_pages': [],
            'pages_with_no_emails': 0,
            'extraction_time_stats': {}
        }
        
        extraction_times = []
        candidate_counts = []
        page_performances = []
        
        for url, page_data in page_results.items():
            candidates = page_data.get('candidates', 0)
            high_quality = page_data.get('high_quality', 0)
            extraction_time = page_data.get('extraction_time_ms', 0)
            
            candidate_counts.append(candidates)
            if extraction_time:
                extraction_times.append(extraction_time)
            
            # Categorize pages by candidate count
            if candidates == 0:
                performance_stats['pages_with_no_emails'] += 1
                performance_stats['pages_by_candidate_count']['0'] += 1
            elif candidates <= 3:
                performance_stats['pages_by_candidate_count']['1-3'] += 1
            elif candidates <= 10:
                performance_stats['pages_by_candidate_count']['4-10'] += 1
            else:
                performance_stats['pages_by_candidate_count']['10+'] += 1
            
            # Track top performing pages
            page_performances.append({
                'url': url,
                'candidates': candidates,
                'high_quality': high_quality,
                'performance_score': high_quality * 2 + candidates
            })
        
        # Calculate statistics
        if candidate_counts:
            performance_stats['avg_candidates_per_page'] = sum(candidate_counts) / len(candidate_counts)
        
        if extraction_times:
            performance_stats['extraction_time_stats'] = {
                'avg_ms': sum(extraction_times) / len(extraction_times),
                'min_ms': min(extraction_times),
                'max_ms': max(extraction_times),
                'total_ms': sum(extraction_times)
            }
        
        # Top performing pages
        page_performances.sort(key=lambda x: x['performance_score'], reverse=True)
        performance_stats['top_performing_pages'] = page_performances[:10]
        
        return performance_stats
    
    def _analyze_domain_patterns(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email domain patterns and distribution"""
        domain_stats = defaultdict(lambda: {
            'count': 0,
            'quality_levels': Counter(),
            'avg_confidence': 0.0
        })
        
        tld_stats = Counter()
        domain_categories = {
            'business': ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com'],
            'personal': ['aol.com', 'icloud.com', 'protonmail.com'],
            'custom': []
        }
        
        for candidate in candidates:
            email = candidate.get('email', '')
            if '@' not in email:
                continue
            
            domain = email.split('@')[1].lower()
            tld = domain.split('.')[-1]
            
            # Domain statistics
            domain_stats[domain]['count'] += 1
            domain_stats[domain]['quality_levels'][candidate.get('quality', 'unknown')] += 1
            domain_stats[domain]['avg_confidence'] += candidate.get('confidence_score', 0.0)
            
            # TLD statistics
            tld_stats[tld] += 1
            
            # Categorize domain
            if domain not in domain_categories['business'] and domain not in domain_categories['personal']:
                domain_categories['custom'].append(domain)
        
        # Calculate averages
        for domain, stats in domain_stats.items():
            if stats['count'] > 0:
                stats['avg_confidence'] /= stats['count']
                stats['quality_levels'] = dict(stats['quality_levels'])
        
        # Get unique custom domains
        domain_categories['custom'] = list(set(domain_categories['custom']))
        
        return {
            'domain_distribution': dict(domain_stats),
            'tld_distribution': dict(tld_stats),
            'domain_categories': domain_categories,
            'most_common_domains': dict(Counter(domain_stats.keys()).most_common(10)),
            'custom_domain_count': len(domain_categories['custom'])
        }
    
    def _generate_detailed_breakdown(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate detailed breakdown of extraction results"""
        return {
            'validation_status_breakdown': Counter(
                c.get('validation_status', 'unknown') for c in candidates
            ),
            'source_method_combinations': Counter(
                f"{c.get('source', 'unknown')}_{c.get('extraction_method', 'unknown')}" 
                for c in candidates
            ),
            'quality_confidence_correlation': self._analyze_quality_confidence_correlation(candidates),
            'context_richness_analysis': self._analyze_context_richness(candidates)
        }
    
    def _analyze_quality_confidence_correlation(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correlation between quality levels and confidence scores"""
        quality_confidence = defaultdict(list)
        
        for candidate in candidates:
            quality = candidate.get('quality', 'unknown')
            confidence = candidate.get('confidence_score', 0.0)
            
            if isinstance(confidence, (int, float)):
                quality_confidence[quality].append(confidence)
        
        correlation_stats = {}
        for quality, scores in quality_confidence.items():
            if scores:
                correlation_stats[quality] = {
                    'avg_confidence': sum(scores) / len(scores),
                    'min_confidence': min(scores),
                    'max_confidence': max(scores),
                    'count': len(scores)
                }
        
        return correlation_stats
    
    def _analyze_context_richness(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze richness of context information"""
        context_stats = {
            'candidates_with_names': 0,
            'candidates_with_titles': 0,
            'candidates_with_departments': 0,
            'candidates_with_phones': 0,
            'candidates_with_full_context': 0
        }
        
        for candidate in candidates:
            if candidate.get('associated_name'):
                context_stats['candidates_with_names'] += 1
            if candidate.get('associated_title'):
                context_stats['candidates_with_titles'] += 1
            if candidate.get('associated_department'):
                context_stats['candidates_with_departments'] += 1
            if candidate.get('phone_number'):
                context_stats['candidates_with_phones'] += 1
            
            # Full context = at least 2 pieces of additional info
            context_count = sum([
                bool(candidate.get('associated_name')),
                bool(candidate.get('associated_title')),
                bool(candidate.get('associated_department')),
                bool(candidate.get('phone_number'))
            ])
            
            if context_count >= 2:
                context_stats['candidates_with_full_context'] += 1
        
        return context_stats
    
    def _calculate_efficiency_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate extraction efficiency metrics"""
        total_time = results.get('total_extraction_time_ms', 0)
        pages_processed = results.get('pages_processed', 1)
        total_candidates = results.get('total_candidates', 0)
        high_quality = results.get('unique_high_quality', 0)
        
        return {
            'emails_per_second': (total_candidates / max(1, total_time / 1000)) if total_time > 0 else 0,
            'high_quality_emails_per_minute': (high_quality / max(1, total_time / 60000)) if total_time > 0 else 0,
            'pages_per_minute': (pages_processed / max(1, total_time / 60000)) if total_time > 0 else 0,
            'success_efficiency': (high_quality / max(1, total_candidates)) * 100,
            'time_per_quality_email': (total_time / max(1, high_quality)) if high_quality > 0 else 0
        }
    
    def _analyze_quality_trends(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality trends in extraction"""
        # Group by extraction time (if available) to see trends
        time_quality = []
        
        for candidate in candidates:
            timestamp = candidate.get('discovery_timestamp', 0)
            quality = candidate.get('quality', 'unknown')
            confidence = candidate.get('confidence_score', 0.0)
            
            time_quality.append({
                'timestamp': timestamp,
                'quality': quality,
                'confidence': confidence
            })
        
        # Sort by timestamp
        time_quality.sort(key=lambda x: x['timestamp'])
        
        # Analyze trends (simplified)
        quality_over_time = {
            'early_high_quality_rate': 0.0,
            'late_high_quality_rate': 0.0,
            'confidence_trend': 'stable'
        }
        
        if len(time_quality) >= 10:
            # Split into early and late groups
            split_point = len(time_quality) // 2
            early_group = time_quality[:split_point]
            late_group = time_quality[split_point:]
            
            # Calculate quality rates
            early_high = len([t for t in early_group if t['quality'] in ['high', 'medium']])
            late_high = len([t for t in late_group if t['quality'] in ['high', 'medium']])
            
            quality_over_time['early_high_quality_rate'] = (early_high / len(early_group)) * 100
            quality_over_time['late_high_quality_rate'] = (late_high / len(late_group)) * 100
            
            # Confidence trend
            early_conf = sum(t['confidence'] for t in early_group) / len(early_group)
            late_conf = sum(t['confidence'] for t in late_group) / len(late_group)
            
            if late_conf > early_conf * 1.1:
                quality_over_time['confidence_trend'] = 'improving'
            elif late_conf < early_conf * 0.9:
                quality_over_time['confidence_trend'] = 'declining'
        
        return quality_over_time
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on metrics analysis"""
        recommendations = []
        
        overview = metrics.get('extraction_overview', {})
        quality_dist = metrics.get('quality_distribution', {})
        source_analysis = metrics.get('source_analysis', {})
        
        # Success rate recommendations
        success_rate = overview.get('success_rate', 0)
        if success_rate < 50:
            recommendations.append("Low email discovery rate - consider expanding crawl depth or targeting contact pages")
        
        # Quality recommendations
        high_quality_pct = quality_dist.get('quality_percentages', {}).get('high', 0)
        if high_quality_pct < 20:
            recommendations.append("Low high-quality email rate - review quality scoring criteria and business indicators")
        
        # Source recommendations
        if 'mailto_link' in source_analysis and source_analysis['mailto_link']['count'] < overview.get('total_candidates_found', 0) * 0.3:
            recommendations.append("Consider prioritizing pages with contact forms and mailto links")
        
        # Performance recommendations
        efficiency = metrics.get('efficiency_metrics', {})
        if efficiency.get('time_per_quality_email', 1000) > 500:
            recommendations.append("Extraction time per quality email is high - consider optimizing pattern matching")
        
        return recommendations
    
    def _generate_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of metrics"""
        overview = metrics.get('extraction_overview', {})
        quality_dist = metrics.get('quality_distribution', {})
        
        return {
            'total_emails_found': overview.get('total_candidates_found', 0),
            'business_quality_emails': overview.get('unique_business_emails', 0),
            'extraction_success_rate': round(overview.get('success_rate', 0), 1),
            'average_quality_score': round(quality_dist.get('confidence_score_stats', {}).get('mean', 0), 2),
            'top_performing_source': self._get_best_source(metrics.get('source_analysis', {})),
            'efficiency_score': round(metrics.get('efficiency_metrics', {}).get('success_efficiency', 0), 1),
            'recommendation_count': len(metrics.get('recommendations', []))
        }
    
    def _get_best_source(self, source_analysis: Dict[str, Any]) -> str:
        """Get the best performing source type"""
        best_source = 'unknown'
        best_score = 0.0
        
        for source, stats in source_analysis.items():
            # Score based on count and average confidence
            score = stats.get('count', 0) * stats.get('avg_confidence', 0)
            if score > best_score:
                best_score = score
                best_source = source
        
        return best_source


class EmailReportGeneratorTool(BaseTool):
    """
    Tool for generating formatted reports from email extraction metrics.
    
    Creates human-readable reports in various formats including
    executive summaries, detailed analysis reports, and data exports.
    """
    
    name: str = "email_report_generator"
    description: str = "Generate formatted reports from email extraction metrics"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailReportGeneratorTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run(self,
            metrics_data: Dict[str, Any],
            report_type: str = "executive_summary",
            include_charts: bool = False) -> Dict[str, Any]:
        """
        Generate formatted report from metrics data.
        
        Args:
            metrics_data: Metrics data from EmailMetricsTool
            report_type: Type of report ("executive_summary", "detailed_analysis", "data_export")
            include_charts: Whether to include chart data for visualization
            
        Returns:
            Dictionary containing formatted report
        """
        try:
            self.logger.info(f"Generating {report_type} report")
            
            metrics = metrics_data.get('metrics', {})
            
            if report_type == "executive_summary":
                report = self._generate_executive_summary(metrics)
            elif report_type == "detailed_analysis":
                report = self._generate_detailed_analysis(metrics)
            elif report_type == "data_export":
                report = self._generate_data_export(metrics)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            if include_charts:
                report['chart_data'] = self._generate_chart_data(metrics)
            
            report.update({
                'report_type': report_type,
                'generated_at': time.time(),
                'report_id': f"email_report_{report_type}_{int(time.time())}"
            })
            
            self.logger.info(f"Report generated successfully: {report_type}")
            
            return {
                'success': True,
                'report': report
            }
            
        except Exception as e:
            error_msg = f"Report generation failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'report': {}
            }
    
    def _generate_executive_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary report"""
        overview = metrics.get('extraction_overview', {})
        summary = metrics.get('summary', {})
        recommendations = metrics.get('recommendations', [])
        
        return {
            'title': 'Email Extraction Executive Summary',
            'key_metrics': {
                'Total Pages Processed': overview.get('total_pages_processed', 0),
                'Business Emails Found': summary.get('business_quality_emails', 0),
                'Success Rate': f"{summary.get('extraction_success_rate', 0)}%",
                'Average Quality Score': summary.get('average_quality_score', 0),
                'Efficiency Score': f"{summary.get('efficiency_score', 0)}%"
            },
            'performance_highlights': [
                f"Discovered {overview.get('total_candidates_found', 0)} email candidates",
                f"Achieved {summary.get('extraction_success_rate', 0)}% success rate",
                f"Found {overview.get('unique_high_quality_emails', 0)} high-quality emails",
                f"Processing time: {overview.get('total_extraction_time_ms', 0)/1000:.1f} seconds"
            ],
            'recommendations': recommendations[:5],  # Top 5 recommendations
            'next_steps': [
                "Review high-quality email candidates for outreach prioritization",
                "Implement recommended improvements for extraction efficiency",
                "Expand crawling to additional contact-relevant pages if needed"
            ]
        }
    
    def _generate_detailed_analysis(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed analysis report"""
        return {
            'title': 'Detailed Email Extraction Analysis',
            'sections': {
                'extraction_overview': {
                    'title': 'Extraction Overview',
                    'data': metrics.get('extraction_overview', {})
                },
                'quality_analysis': {
                    'title': 'Quality Distribution Analysis',
                    'data': metrics.get('quality_distribution', {})
                },
                'source_performance': {
                    'title': 'Extraction Source Performance',
                    'data': metrics.get('source_analysis', {})
                },
                'method_effectiveness': {
                    'title': 'Extraction Method Effectiveness',
                    'data': metrics.get('method_analysis', {})
                },
                'page_performance': {
                    'title': 'Page-by-Page Performance',
                    'data': metrics.get('page_performance', {})
                },
                'domain_insights': {
                    'title': 'Domain Pattern Analysis',
                    'data': metrics.get('domain_analysis', {})
                },
                'efficiency_metrics': {
                    'title': 'Efficiency and Performance Metrics',
                    'data': metrics.get('efficiency_metrics', {})
                }
            },
            'detailed_breakdown': metrics.get('detailed_breakdown', {}),
            'recommendations': metrics.get('recommendations', []),
            'methodology': {
                'extraction_methods': [
                    'RFC-5322 compliant regex pattern matching',
                    'Obfuscated email detection ([at], [dot], etc.)',
                    'Mailto link extraction',
                    'HTML attribute scanning',
                    'Context-aware quality scoring'
                ],
                'quality_factors': [
                    'Email validation and syntax checking',
                    'Business keyword presence',
                    'Source type and context',
                    'Domain reputation analysis',
                    'Contact information richness'
                ]
            }
        }
    
    def _generate_data_export(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data export report"""
        return {
            'title': 'Email Extraction Data Export',
            'export_format': 'structured_data',
            'data': {
                'raw_metrics': metrics,
                'csv_ready_data': self._prepare_csv_data(metrics),
                'json_export': json.dumps(metrics, indent=2),
                'summary_table': self._create_summary_table(metrics)
            },
            'export_instructions': {
                'csv_usage': 'Use csv_ready_data for spreadsheet import',
                'json_usage': 'Use json_export for programmatic access',
                'summary_usage': 'Use summary_table for dashboard display'
            }
        }
    
    def _prepare_csv_data(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare data in CSV-ready format"""
        csv_data = []
        
        # Page performance data
        page_perf = metrics.get('page_performance', {})
        top_pages = page_perf.get('top_performing_pages', [])
        
        for page in top_pages:
            csv_data.append({
                'type': 'page_performance',
                'url': page.get('url', ''),
                'candidates': page.get('candidates', 0),
                'high_quality': page.get('high_quality', 0),
                'performance_score': page.get('performance_score', 0)
            })
        
        # Source analysis data
        source_analysis = metrics.get('source_analysis', {})
        for source, stats in source_analysis.items():
            csv_data.append({
                'type': 'source_analysis',
                'source': source,
                'count': stats.get('count', 0),
                'avg_confidence': stats.get('avg_confidence', 0),
                'quality_high': stats.get('quality_distribution', {}).get('high', 0),
                'quality_medium': stats.get('quality_distribution', {}).get('medium', 0),
                'quality_low': stats.get('quality_distribution', {}).get('low', 0)
            })
        
        return csv_data
    
    def _create_summary_table(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create summary table for dashboard display"""
        overview = metrics.get('extraction_overview', {})
        quality = metrics.get('quality_distribution', {})
        
        return [
            {'metric': 'Pages Processed', 'value': overview.get('total_pages_processed', 0), 'unit': 'pages'},
            {'metric': 'Emails Found', 'value': overview.get('total_candidates_found', 0), 'unit': 'emails'},
            {'metric': 'High Quality Rate', 'value': quality.get('quality_percentages', {}).get('high', 0), 'unit': '%'},
            {'metric': 'Success Rate', 'value': overview.get('success_rate', 0), 'unit': '%'},
            {'metric': 'Avg Extraction Time', 'value': overview.get('average_extraction_time_ms', 0), 'unit': 'ms'},
            {'metric': 'Business Emails', 'value': overview.get('unique_business_emails', 0), 'unit': 'emails'}
        ]
    
    def _generate_chart_data(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data for charts and visualizations"""
        return {
            'quality_pie_chart': {
                'labels': list(metrics.get('quality_distribution', {}).get('quality_distribution', {}).keys()),
                'values': list(metrics.get('quality_distribution', {}).get('quality_distribution', {}).values())
            },
            'source_bar_chart': {
                'labels': list(metrics.get('source_analysis', {}).keys()),
                'values': [stats.get('count', 0) for stats in metrics.get('source_analysis', {}).values()]
            },
            'confidence_histogram': {
                'bins': [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                'counts': [
                    metrics.get('quality_distribution', {}).get('low_confidence_count', 0),
                    metrics.get('quality_distribution', {}).get('medium_confidence_count', 0),
                    metrics.get('quality_distribution', {}).get('high_confidence_count', 0)
                ]
            },
            'domain_top10': {
                'labels': list(metrics.get('domain_analysis', {}).get('most_common_domains', {}).keys())[:10],
                'values': list(metrics.get('domain_analysis', {}).get('most_common_domains', {}).values())[:10]
            }
        }