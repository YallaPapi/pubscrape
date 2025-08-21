"""
Crawl Metrics Tool

Tool for comprehensive logging and metrics collection during crawling operations.
Tracks per-domain latencies, retries, challenge signals, and crawl statistics.
"""

import logging
import time
import json
import csv
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import statistics

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field

# Optional structured logging
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None


class LogLevel(Enum):
    """Log verbosity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics that can be tracked"""
    REQUEST_LATENCY = "request_latency"
    RETRY_COUNT = "retry_count"
    CHALLENGE_SIGNAL = "challenge_signal"
    PAGE_DISCOVERY = "page_discovery"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"


@dataclass
class RequestMetric:
    """Metrics for a single request"""
    url: str
    domain: str
    session_id: str
    timestamp: float
    response_time_ms: float
    status_code: Optional[int] = None
    success: bool = True
    error_type: Optional[str] = None
    retry_count: int = 0
    challenge_detected: bool = False
    page_type_discovered: Optional[str] = None
    links_discovered: int = 0
    content_length: Optional[int] = None
    user_agent: Optional[str] = None
    proxy_used: Optional[str] = None
    
    @property
    def response_time_seconds(self) -> float:
        """Get response time in seconds"""
        return self.response_time_ms / 1000.0


@dataclass
class DomainMetrics:
    """Aggregated metrics for a domain"""
    domain: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    retry_attempts: int = 0
    challenges_detected: int = 0
    blocks_detected: int = 0
    pages_discovered_by_type: Dict[str, int] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)
    status_codes: Dict[int, int] = field(default_factory=dict)
    response_times: List[float] = field(default_factory=list)
    first_request_time: Optional[float] = None
    last_request_time: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        return (self.successful_requests / self.total_requests) * 100 if self.total_requests > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage"""
        return (self.failed_requests / self.total_requests) * 100 if self.total_requests > 0 else 0.0
    
    @property
    def challenge_rate(self) -> float:
        """Calculate challenge detection rate percentage"""
        return (self.challenges_detected / self.total_requests) * 100 if self.total_requests > 0 else 0.0
    
    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time"""
        return self.total_response_time_ms / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def median_response_time_ms(self) -> float:
        """Calculate median response time"""
        return statistics.median(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time_ms(self) -> float:
        """Calculate 95th percentile response time"""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    @property
    def requests_per_minute(self) -> float:
        """Calculate request rate per minute"""
        if not self.first_request_time or not self.last_request_time:
            return 0.0
        
        duration_minutes = (self.last_request_time - self.first_request_time) / 60.0
        return self.total_requests / duration_minutes if duration_minutes > 0 else 0.0


@dataclass
class CrawlSessionReport:
    """Comprehensive report for a crawl session"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    total_domains: int = 0
    total_requests: int = 0
    total_success: int = 0
    total_failures: int = 0
    total_challenges: int = 0
    total_pages_discovered: int = 0
    domain_metrics: Dict[str, DomainMetrics] = field(default_factory=dict)
    page_type_distribution: Dict[str, int] = field(default_factory=dict)
    error_distribution: Dict[str, int] = field(default_factory=dict)
    performance_summary: Dict[str, float] = field(default_factory=dict)
    
    @property
    def duration_minutes(self) -> float:
        """Get session duration in minutes"""
        end = self.end_time or time.time()
        return (end - self.start_time) / 60.0
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate"""
        return (self.total_success / self.total_requests) * 100 if self.total_requests > 0 else 0.0
    
    @property
    def overall_throughput(self) -> float:
        """Calculate overall throughput (requests per minute)"""
        return self.total_requests / self.duration_minutes if self.duration_minutes > 0 else 0.0


class CrawlMetricsCollector:
    """
    Collector for crawl metrics with structured logging and reporting.
    
    This class handles the collection, aggregation, and reporting of
    comprehensive crawling metrics including latencies, error rates,
    and discovery statistics.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Metrics storage
        self.request_metrics: List[RequestMetric] = []
        self.domain_metrics: Dict[str, DomainMetrics] = {}
        self.session_reports: Dict[str, CrawlSessionReport] = {}
        
        # Configuration
        self.log_level = LogLevel(self.config.get("log_level", "info"))
        self.enable_structured_logging = self.config.get("enable_structured_logging", STRUCTLOG_AVAILABLE)
        self.max_stored_requests = self.config.get("max_stored_requests", 10000)
        self.enable_file_logging = self.config.get("enable_file_logging", True)
        self.log_directory = Path(self.config.get("log_directory", "logs"))
        
        # Ensure log directory exists
        if self.enable_file_logging:
            self.log_directory.mkdir(exist_ok=True)
        
        # Initialize structured logging if available
        if self.enable_structured_logging and structlog:
            self._setup_structured_logging()
        
        self.logger.info("CrawlMetricsCollector initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the metrics collector"""
        logger = logging.getLogger(f"{__name__}.CrawlMetricsCollector")
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # File handler if enabled
            if self.enable_file_logging:
                try:
                    log_file = self.log_directory / "crawl_metrics.log"
                    file_handler = logging.FileHandler(log_file)
                    file_formatter = logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                    file_handler.setFormatter(file_formatter)
                    logger.addHandler(file_handler)
                except Exception as e:
                    print(f"Failed to setup file logging: {e}")
            
            # Set log level
            log_level_map = {
                "debug": logging.DEBUG,
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL
            }
            logger.setLevel(log_level_map.get(self.log_level.value, logging.INFO))
        
        return logger
    
    def _setup_structured_logging(self):
        """Set up structured logging with structlog"""
        if not structlog:
            return
        
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self.structured_logger = structlog.get_logger("crawl_metrics")
    
    def record_request(self, url: str, domain: str, session_id: str,
                      response_time_ms: float, success: bool = True,
                      status_code: Optional[int] = None,
                      error_type: Optional[str] = None,
                      retry_count: int = 0,
                      challenge_detected: bool = False,
                      page_type_discovered: Optional[str] = None,
                      links_discovered: int = 0,
                      content_length: Optional[int] = None,
                      user_agent: Optional[str] = None,
                      proxy_used: Optional[str] = None):
        """
        Record metrics for a single request.
        
        Args:
            url: URL that was requested
            domain: Domain of the request
            session_id: Session ID used for the request
            response_time_ms: Response time in milliseconds
            success: Whether the request was successful
            status_code: HTTP status code
            error_type: Type of error if request failed
            retry_count: Number of retries attempted
            challenge_detected: Whether a challenge was detected
            page_type_discovered: Type of page discovered (if any)
            links_discovered: Number of links discovered on the page
            content_length: Response content length
            user_agent: User agent used
            proxy_used: Proxy used (if any)
        """
        try:
            # Create request metric
            metric = RequestMetric(
                url=url,
                domain=domain,
                session_id=session_id,
                timestamp=time.time(),
                response_time_ms=response_time_ms,
                status_code=status_code,
                success=success,
                error_type=error_type,
                retry_count=retry_count,
                challenge_detected=challenge_detected,
                page_type_discovered=page_type_discovered,
                links_discovered=links_discovered,
                content_length=content_length,
                user_agent=user_agent,
                proxy_used=proxy_used
            )
            
            # Store request metric
            self.request_metrics.append(metric)
            
            # Update domain metrics
            self._update_domain_metrics(metric)
            
            # Update session report
            self._update_session_report(metric)
            
            # Log the request
            self._log_request(metric)
            
            # Cleanup old metrics if needed
            if len(self.request_metrics) > self.max_stored_requests:
                self.request_metrics = self.request_metrics[-self.max_stored_requests:]
            
        except Exception as e:
            self.logger.error(f"Error recording request metric: {e}")
    
    def _update_domain_metrics(self, metric: RequestMetric):
        """Update aggregated metrics for a domain"""
        domain = metric.domain
        
        if domain not in self.domain_metrics:
            self.domain_metrics[domain] = DomainMetrics(domain=domain)
        
        dm = self.domain_metrics[domain]
        dm.total_requests += 1
        dm.total_response_time_ms += metric.response_time_ms
        dm.response_times.append(metric.response_time_ms)
        
        if metric.success:
            dm.successful_requests += 1
        else:
            dm.failed_requests += 1
            if metric.error_type:
                dm.error_types[metric.error_type] = dm.error_types.get(metric.error_type, 0) + 1
        
        if metric.status_code:
            dm.status_codes[metric.status_code] = dm.status_codes.get(metric.status_code, 0) + 1
        
        if metric.retry_count > 0:
            dm.retry_attempts += metric.retry_count
        
        if metric.challenge_detected:
            dm.challenges_detected += 1
            if "block" in (metric.error_type or "").lower():
                dm.blocks_detected += 1
        
        if metric.page_type_discovered:
            dm.pages_discovered_by_type[metric.page_type_discovered] = (
                dm.pages_discovered_by_type.get(metric.page_type_discovered, 0) + 1
            )
        
        # Update timestamps
        if dm.first_request_time is None:
            dm.first_request_time = metric.timestamp
        dm.last_request_time = metric.timestamp
    
    def _update_session_report(self, metric: RequestMetric):
        """Update session report with request metric"""
        session_id = metric.session_id
        
        if session_id not in self.session_reports:
            self.session_reports[session_id] = CrawlSessionReport(
                session_id=session_id,
                start_time=metric.timestamp
            )
        
        report = self.session_reports[session_id]
        report.total_requests += 1
        
        if metric.success:
            report.total_success += 1
        else:
            report.total_failures += 1
            if metric.error_type:
                report.error_distribution[metric.error_type] = (
                    report.error_distribution.get(metric.error_type, 0) + 1
                )
        
        if metric.challenge_detected:
            report.total_challenges += 1
        
        if metric.page_type_discovered:
            report.total_pages_discovered += 1
            report.page_type_distribution[metric.page_type_discovered] = (
                report.page_type_distribution.get(metric.page_type_discovered, 0) + 1
            )
        
        # Track unique domains
        domains = set(m.domain for m in self.request_metrics if m.session_id == session_id)
        report.total_domains = len(domains)
        
        # Update domain metrics reference
        if metric.domain not in report.domain_metrics:
            report.domain_metrics[metric.domain] = self.domain_metrics[metric.domain]
    
    def _log_request(self, metric: RequestMetric):
        """Log a request with appropriate verbosity"""
        
        # Structured logging if available
        if self.enable_structured_logging and hasattr(self, 'structured_logger'):
            log_data = {
                "event": "request_completed",
                "url": metric.url,
                "domain": metric.domain,
                "session_id": metric.session_id,
                "response_time_ms": metric.response_time_ms,
                "success": metric.success,
                "status_code": metric.status_code,
                "retry_count": metric.retry_count,
                "challenge_detected": metric.challenge_detected,
                "page_type": metric.page_type_discovered,
                "links_discovered": metric.links_discovered
            }
            
            if metric.error_type:
                log_data["error_type"] = metric.error_type
            
            self.structured_logger.info(**log_data)
        
        # Standard logging
        log_message = (
            f"Request: {metric.url} | "
            f"Domain: {metric.domain} | "
            f"Success: {metric.success} | "
            f"Response Time: {metric.response_time_ms:.0f}ms"
        )
        
        if metric.status_code:
            log_message += f" | Status: {metric.status_code}"
        
        if metric.retry_count > 0:
            log_message += f" | Retries: {metric.retry_count}"
        
        if metric.challenge_detected:
            log_message += " | Challenge Detected"
        
        if metric.page_type_discovered:
            log_message += f" | Page Type: {metric.page_type_discovered}"
        
        if metric.links_discovered > 0:
            log_message += f" | Links: {metric.links_discovered}"
        
        if metric.success:
            self.logger.info(log_message)
        else:
            error_msg = log_message
            if metric.error_type:
                error_msg += f" | Error: {metric.error_type}"
            self.logger.warning(error_msg)
    
    def start_session(self, session_id: str) -> bool:
        """Start tracking a new session"""
        if session_id not in self.session_reports:
            self.session_reports[session_id] = CrawlSessionReport(
                session_id=session_id,
                start_time=time.time()
            )
            self.logger.info(f"Started tracking session: {session_id}")
            return True
        else:
            self.logger.warning(f"Session {session_id} already exists")
            return False
    
    def end_session(self, session_id: str) -> Optional[CrawlSessionReport]:
        """End a session and return final report"""
        if session_id in self.session_reports:
            report = self.session_reports[session_id]
            report.end_time = time.time()
            
            # Calculate performance summary
            report.performance_summary = self._calculate_performance_summary(report)
            
            self.logger.info(f"Ended session: {session_id} | "
                           f"Duration: {report.duration_minutes:.1f}min | "
                           f"Requests: {report.total_requests} | "
                           f"Success Rate: {report.overall_success_rate:.1f}%")
            
            return report
        else:
            self.logger.warning(f"Session {session_id} not found")
            return None
    
    def _calculate_performance_summary(self, report: CrawlSessionReport) -> Dict[str, float]:
        """Calculate performance summary for a session"""
        all_response_times = []
        for metric in self.request_metrics:
            if metric.session_id == report.session_id:
                all_response_times.append(metric.response_time_ms)
        
        summary = {
            "avg_response_time_ms": statistics.mean(all_response_times) if all_response_times else 0.0,
            "median_response_time_ms": statistics.median(all_response_times) if all_response_times else 0.0,
            "min_response_time_ms": min(all_response_times) if all_response_times else 0.0,
            "max_response_time_ms": max(all_response_times) if all_response_times else 0.0,
            "requests_per_minute": report.overall_throughput,
            "success_rate_percent": report.overall_success_rate,
            "challenge_rate_percent": (report.total_challenges / report.total_requests) * 100 if report.total_requests > 0 else 0.0
        }
        
        if len(all_response_times) > 1:
            summary["p95_response_time_ms"] = statistics.quantiles(all_response_times, n=20)[18]  # 95th percentile
            summary["stddev_response_time_ms"] = statistics.stdev(all_response_times)
        
        return summary
    
    def get_domain_summary(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive summary for a specific domain"""
        if domain not in self.domain_metrics:
            return None
        
        dm = self.domain_metrics[domain]
        
        return {
            "domain": domain,
            "request_count": dm.total_requests,
            "success_rate_percent": dm.success_rate,
            "error_rate_percent": dm.error_rate,
            "challenge_rate_percent": dm.challenge_rate,
            "avg_response_time_ms": dm.avg_response_time_ms,
            "median_response_time_ms": dm.median_response_time_ms,
            "p95_response_time_ms": dm.p95_response_time_ms,
            "requests_per_minute": dm.requests_per_minute,
            "retry_attempts": dm.retry_attempts,
            "challenges_detected": dm.challenges_detected,
            "blocks_detected": dm.blocks_detected,
            "pages_discovered": dm.pages_discovered_by_type,
            "error_types": dm.error_types,
            "status_codes": dm.status_codes,
            "first_request": dm.first_request_time,
            "last_request": dm.last_request_time
        }
    
    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall statistics across all domains and sessions"""
        total_requests = len(self.request_metrics)
        successful_requests = sum(1 for m in self.request_metrics if m.success)
        challenges_detected = sum(1 for m in self.request_metrics if m.challenge_detected)
        
        all_response_times = [m.response_time_ms for m in self.request_metrics]
        
        return {
            "total_requests": total_requests,
            "total_domains": len(self.domain_metrics),
            "total_sessions": len(self.session_reports),
            "overall_success_rate_percent": (successful_requests / total_requests) * 100 if total_requests > 0 else 0.0,
            "overall_challenge_rate_percent": (challenges_detected / total_requests) * 100 if total_requests > 0 else 0.0,
            "avg_response_time_ms": statistics.mean(all_response_times) if all_response_times else 0.0,
            "median_response_time_ms": statistics.median(all_response_times) if all_response_times else 0.0,
            "total_retries": sum(m.retry_count for m in self.request_metrics),
            "unique_page_types": len(set(m.page_type_discovered for m in self.request_metrics if m.page_type_discovered)),
            "total_links_discovered": sum(m.links_discovered for m in self.request_metrics),
            "domains_with_challenges": len([d for d, dm in self.domain_metrics.items() if dm.challenges_detected > 0]),
            "top_domains_by_requests": sorted(
                [(d, dm.total_requests) for d, dm in self.domain_metrics.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
        }
    
    def export_metrics(self, output_format: str = "json", 
                      output_path: Optional[Path] = None) -> Path:
        """
        Export metrics to file.
        
        Args:
            output_format: Format to export ("json", "csv")
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if not output_path:
            timestamp = int(time.time())
            output_path = self.log_directory / f"crawl_metrics_{timestamp}.{output_format}"
        
        try:
            if output_format == "json":
                export_data = {
                    "export_timestamp": time.time(),
                    "overall_statistics": self.get_overall_statistics(),
                    "domain_metrics": {
                        domain: self.get_domain_summary(domain)
                        for domain in self.domain_metrics.keys()
                    },
                    "session_reports": {
                        session_id: asdict(report)
                        for session_id, report in self.session_reports.items()
                    },
                    "recent_requests": [
                        asdict(metric) for metric in self.request_metrics[-1000:]  # Last 1000 requests
                    ]
                }
                
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif output_format == "csv":
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Header
                    writer.writerow([
                        'timestamp', 'url', 'domain', 'session_id', 'response_time_ms',
                        'success', 'status_code', 'error_type', 'retry_count',
                        'challenge_detected', 'page_type', 'links_discovered',
                        'content_length', 'user_agent', 'proxy_used'
                    ])
                    
                    # Data rows
                    for metric in self.request_metrics:
                        writer.writerow([
                            metric.timestamp, metric.url, metric.domain, metric.session_id,
                            metric.response_time_ms, metric.success, metric.status_code,
                            metric.error_type, metric.retry_count, metric.challenge_detected,
                            metric.page_type_discovered, metric.links_discovered,
                            metric.content_length, metric.user_agent, metric.proxy_used
                        ])
            
            else:
                raise ValueError(f"Unsupported export format: {output_format}")
            
            self.logger.info(f"Exported metrics to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {e}")
            raise


class CrawlMetricsTool(BaseTool):
    """
    Tool for managing crawl metrics collection and reporting.
    
    This tool provides an interface to the CrawlMetricsCollector for
    recording metrics, generating reports, and exporting data.
    """
    
    operation: str = Field(
        ...,
        description="Operation to perform: 'record_request', 'start_session', 'end_session', 'get_statistics', 'export_metrics'"
    )
    
    # Request recording parameters
    url: Optional[str] = Field(None, description="URL that was requested")
    domain: Optional[str] = Field(None, description="Domain of the request")
    session_id: Optional[str] = Field(None, description="Session ID used for the request")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    success: bool = Field(True, description="Whether the request was successful")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error_type: Optional[str] = Field(None, description="Type of error if request failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    challenge_detected: bool = Field(False, description="Whether a challenge was detected")
    page_type_discovered: Optional[str] = Field(None, description="Type of page discovered")
    links_discovered: int = Field(0, description="Number of links discovered")
    content_length: Optional[int] = Field(None, description="Response content length")
    user_agent: Optional[str] = Field(None, description="User agent used")
    proxy_used: Optional[str] = Field(None, description="Proxy used")
    
    # Export parameters
    export_format: str = Field("json", description="Export format: json, csv")
    output_path: Optional[str] = Field(None, description="Output file path")
    
    # Statistics parameters
    target_domain: Optional[str] = Field(None, description="Specific domain for statistics")
    
    # Configuration
    log_level: str = Field("info", description="Log level: debug, info, warning, error, critical")
    enable_file_logging: bool = Field(True, description="Whether to enable file logging")
    log_directory: str = Field("logs", description="Directory for log files")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics_collector = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.CrawlMetricsTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_collector(self) -> bool:
        """Initialize the metrics collector"""
        if self.metrics_collector is None:
            try:
                config = {
                    "log_level": self.log_level,
                    "enable_file_logging": self.enable_file_logging,
                    "log_directory": self.log_directory,
                    "enable_structured_logging": True,
                    "max_stored_requests": 10000
                }
                self.metrics_collector = CrawlMetricsCollector(config)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize metrics collector: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the crawl metrics operation.
        
        Returns:
            Dictionary containing operation results
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting crawl metrics operation: {self.operation}")
            
            # Initialize collector
            if not self._initialize_collector():
                return {
                    "success": False,
                    "error": "Failed to initialize metrics collector",
                    "operation": self.operation
                }
            
            if self.operation == "record_request":
                return self._record_request_operation(start_time)
            
            elif self.operation == "start_session":
                return self._start_session_operation(start_time)
            
            elif self.operation == "end_session":
                return self._end_session_operation(start_time)
            
            elif self.operation == "get_statistics":
                return self._get_statistics_operation(start_time)
            
            elif self.operation == "export_metrics":
                return self._export_metrics_operation(start_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {self.operation}",
                    "operation": self.operation,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            self.logger.error(f"Error during crawl metrics operation: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": self.operation,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _record_request_operation(self, start_time: float) -> Dict[str, Any]:
        """Record a request metric"""
        required_fields = [self.url, self.domain, self.session_id, self.response_time_ms]
        if any(field is None for field in required_fields):
            return {
                "success": False,
                "error": "Missing required fields: url, domain, session_id, response_time_ms",
                "operation": "record_request",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            self.metrics_collector.record_request(
                url=self.url,
                domain=self.domain,
                session_id=self.session_id,
                response_time_ms=self.response_time_ms,
                success=self.success,
                status_code=self.status_code,
                error_type=self.error_type,
                retry_count=self.retry_count,
                challenge_detected=self.challenge_detected,
                page_type_discovered=self.page_type_discovered,
                links_discovered=self.links_discovered,
                content_length=self.content_length,
                user_agent=self.user_agent,
                proxy_used=self.proxy_used
            )
            
            return {
                "success": True,
                "operation": "record_request",
                "url": self.url,
                "domain": self.domain,
                "session_id": self.session_id,
                "metric_recorded": True,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "record_request",
                "url": self.url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _start_session_operation(self, start_time: float) -> Dict[str, Any]:
        """Start session tracking"""
        if not self.session_id:
            return {
                "success": False,
                "error": "Session ID required for start_session",
                "operation": "start_session",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            success = self.metrics_collector.start_session(self.session_id)
            
            return {
                "success": success,
                "operation": "start_session",
                "session_id": self.session_id,
                "session_started": success,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "start_session",
                "session_id": self.session_id,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _end_session_operation(self, start_time: float) -> Dict[str, Any]:
        """End session and get report"""
        if not self.session_id:
            return {
                "success": False,
                "error": "Session ID required for end_session",
                "operation": "end_session",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            report = self.metrics_collector.end_session(self.session_id)
            
            if report:
                return {
                    "success": True,
                    "operation": "end_session",
                    "session_id": self.session_id,
                    "session_ended": True,
                    "session_report": {
                        "session_id": report.session_id,
                        "duration_minutes": report.duration_minutes,
                        "total_requests": report.total_requests,
                        "success_rate_percent": report.overall_success_rate,
                        "throughput_rpm": report.overall_throughput,
                        "domains_crawled": report.total_domains,
                        "pages_discovered": report.total_pages_discovered,
                        "challenges_detected": report.total_challenges,
                        "page_type_distribution": report.page_type_distribution,
                        "error_distribution": report.error_distribution,
                        "performance_summary": report.performance_summary
                    },
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            else:
                return {
                    "success": False,
                    "error": "Session not found",
                    "operation": "end_session",
                    "session_id": self.session_id,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "end_session",
                "session_id": self.session_id,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_statistics_operation(self, start_time: float) -> Dict[str, Any]:
        """Get statistics"""
        try:
            if self.target_domain:
                domain_summary = self.metrics_collector.get_domain_summary(self.target_domain)
                if domain_summary:
                    return {
                        "success": True,
                        "operation": "get_statistics",
                        "target_domain": self.target_domain,
                        "domain_statistics": domain_summary,
                        "processing_time_ms": (time.time() - start_time) * 1000
                    }
                else:
                    return {
                        "success": False,
                        "error": f"No statistics found for domain: {self.target_domain}",
                        "operation": "get_statistics",
                        "processing_time_ms": (time.time() - start_time) * 1000
                    }
            else:
                overall_stats = self.metrics_collector.get_overall_statistics()
                return {
                    "success": True,
                    "operation": "get_statistics",
                    "overall_statistics": overall_stats,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "get_statistics",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _export_metrics_operation(self, start_time: float) -> Dict[str, Any]:
        """Export metrics to file"""
        try:
            output_path = Path(self.output_path) if self.output_path else None
            exported_path = self.metrics_collector.export_metrics(
                output_format=self.export_format,
                output_path=output_path
            )
            
            return {
                "success": True,
                "operation": "export_metrics",
                "export_format": self.export_format,
                "output_file": str(exported_path),
                "file_exists": exported_path.exists(),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "export_metrics",
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the crawl metrics tool
    print("Testing CrawlMetricsTool...")
    
    # Test starting a session
    tool = CrawlMetricsTool(
        operation="start_session",
        session_id="test_session_123"
    )
    
    result = tool.run()
    print(f"Start session result: {result.get('success', False)}")
    
    # Test recording a request
    tool = CrawlMetricsTool(
        operation="record_request",
        url="https://example.com/contact",
        domain="example.com",
        session_id="test_session_123",
        response_time_ms=150.5,
        success=True,
        status_code=200,
        page_type_discovered="contact",
        links_discovered=5
    )
    
    result = tool.run()
    print(f"Record request result: {result.get('success', False)}")
    
    # Test getting statistics
    tool = CrawlMetricsTool(operation="get_statistics")
    result = tool.run()
    print(f"Get statistics result: {result.get('success', False)}")
    
    if result.get("success"):
        stats = result.get("overall_statistics", {})
        print(f"Total requests: {stats.get('total_requests', 0)}")
        print(f"Success rate: {stats.get('overall_success_rate_percent', 0):.1f}%")
    
    # Test ending session
    tool = CrawlMetricsTool(
        operation="end_session",
        session_id="test_session_123"
    )
    
    result = tool.run()
    print(f"End session result: {result.get('success', False)}")
    
    if result.get("success"):
        session_report = result.get("session_report", {})
        print(f"Session duration: {session_report.get('duration_minutes', 0):.2f} minutes")
        print(f"Total requests: {session_report.get('total_requests', 0)}")