"""
Live Metrics Collector for Real-Time Dashboard
Tracks actual performance metrics during scraping
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import deque
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    context: str = ""
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "context": self.context
        }

@dataclass
class ScrapingMetrics:
    """Current scraping session metrics"""
    session_id: str
    start_time: datetime
    leads_found: int = 0
    emails_extracted: int = 0
    phones_extracted: int = 0
    pages_visited: int = 0
    http_requests: int = 0
    errors_encountered: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def to_dict(self):
        return asdict(self)

class LiveMetricsCollector:
    """Collects and manages live performance metrics"""
    
    def __init__(self, max_history_points: int = 1000):
        self.max_history_points = max_history_points
        self.metrics_history = deque(maxlen=max_history_points)
        self.current_metrics = None
        self.callbacks = []
        self.is_collecting = False
        self.collection_interval = 1.0  # seconds
        self.collection_thread = None
        
        # Metric tracking
        self.response_times = deque(maxlen=100)
        self.error_count = 0
        self.total_requests = 0
        
    def start_collection(self, session_id: str):
        """Start metrics collection for a session"""
        self.current_metrics = ScrapingMetrics(
            session_id=session_id,
            start_time=datetime.now()
        )
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(
            target=self._collection_worker, 
            daemon=True
        )
        self.collection_thread.start()
        
        logger.info(f"Started metrics collection for session: {session_id}")
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2)
        
        logger.info("Stopped metrics collection")
    
    def add_callback(self, callback: Callable[[ScrapingMetrics], None]):
        """Add callback for metrics updates"""
        self.callbacks.append(callback)
    
    def _collection_worker(self):
        """Background worker for metrics collection"""
        while self.is_collecting:
            try:
                self._collect_system_metrics()
                self._calculate_derived_metrics()
                self._notify_callbacks()
                
                # Store metrics point
                self.metrics_history.append(
                    MetricPoint(
                        timestamp=datetime.now(),
                        value=self.current_metrics.success_rate,
                        context="success_rate"
                    )
                )
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        if not self.current_metrics:
            return
        
        try:
            # CPU usage
            self.current_metrics.cpu_usage_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            process = psutil.Process()
            self.current_metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _calculate_derived_metrics(self):
        """Calculate derived metrics"""
        if not self.current_metrics:
            return
        
        try:
            # Success rate
            if self.total_requests > 0:
                success_requests = self.total_requests - self.error_count
                self.current_metrics.success_rate = (success_requests / self.total_requests) * 100
            
            # Average response time
            if self.response_times:
                self.current_metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
            
            # Update error count
            self.current_metrics.errors_encountered = self.error_count
            self.current_metrics.http_requests = self.total_requests
            
        except Exception as e:
            logger.error(f"Error calculating derived metrics: {e}")
    
    def _notify_callbacks(self):
        """Notify all callbacks with current metrics"""
        for callback in self.callbacks:
            try:
                callback(self.current_metrics)
            except Exception as e:
                logger.error(f"Error in metrics callback: {e}")
    
    def record_lead_found(self, lead_data: Dict[str, Any]):
        """Record a new lead found"""
        if self.current_metrics:
            self.current_metrics.leads_found += 1
            
            # Count emails and phones
            if lead_data.get('email'):
                self.current_metrics.emails_extracted += 1
            if lead_data.get('phone'):
                self.current_metrics.phones_extracted += 1
    
    def record_page_visit(self, url: str, response_time: float):
        """Record a page visit"""
        if self.current_metrics:
            self.current_metrics.pages_visited += 1
            self.response_times.append(response_time)
    
    def record_http_request(self, response_time: float, success: bool = True):
        """Record an HTTP request"""
        self.total_requests += 1
        self.response_times.append(response_time)
        
        if not success:
            self.error_count += 1
    
    def record_error(self, error_type: str, error_message: str):
        """Record an error occurrence"""
        self.error_count += 1
        
        logger.warning(f"Recorded error: {error_type} - {error_message}")
    
    def get_current_metrics(self) -> Optional[ScrapingMetrics]:
        """Get current metrics snapshot"""
        return self.current_metrics
    
    def get_metrics_history(self, metric_name: str = None, 
                           last_minutes: int = None) -> List[MetricPoint]:
        """Get metrics history"""
        history = list(self.metrics_history)
        
        # Filter by metric name
        if metric_name:
            history = [point for point in history if point.context == metric_name]
        
        # Filter by time range
        if last_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=last_minutes)
            history = [point for point in history if point.timestamp >= cutoff_time]
        
        return history
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for current session"""
        if not self.current_metrics:
            return {}
        
        elapsed_time = datetime.now() - self.current_metrics.start_time
        
        return {
            "session_id": self.current_metrics.session_id,
            "elapsed_time_minutes": elapsed_time.total_seconds() / 60,
            "leads_per_minute": self.current_metrics.leads_found / max(elapsed_time.total_seconds() / 60, 0.1),
            "success_rate": self.current_metrics.success_rate,
            "avg_response_time": self.current_metrics.avg_response_time,
            "total_leads": self.current_metrics.leads_found,
            "total_emails": self.current_metrics.emails_extracted,
            "total_phones": self.current_metrics.phones_extracted,
            "pages_visited": self.current_metrics.pages_visited,
            "errors_encountered": self.current_metrics.errors_encountered,
            "memory_usage_mb": self.current_metrics.memory_usage_mb,
            "cpu_usage_percent": self.current_metrics.cpu_usage_percent
        }
    
    def export_metrics(self, filepath: str):
        """Export metrics to file"""
        try:
            export_data = {
                "current_metrics": self.current_metrics.to_dict() if self.current_metrics else None,
                "performance_summary": self.get_performance_summary(),
                "metrics_history": [point.to_dict() for point in self.metrics_history],
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Metrics exported to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")

class RealTimePerformanceMonitor:
    """Real-time performance monitoring with alerts"""
    
    def __init__(self, metrics_collector: LiveMetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_callbacks = []
        self.thresholds = {
            "max_response_time": 5.0,  # seconds
            "min_success_rate": 80.0,  # percent
            "max_memory_usage": 1000.0,  # MB
            "max_cpu_usage": 90.0,  # percent
            "max_error_rate": 20.0  # percent
        }
        
    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)
    
    def check_performance(self):
        """Check current performance against thresholds"""
        metrics = self.metrics_collector.get_current_metrics()
        if not metrics:
            return
        
        alerts = []
        
        # Check response time
        if metrics.avg_response_time > self.thresholds["max_response_time"]:
            alerts.append({
                "type": "high_response_time",
                "message": f"High response time: {metrics.avg_response_time:.2f}s",
                "value": metrics.avg_response_time,
                "threshold": self.thresholds["max_response_time"]
            })
        
        # Check success rate
        if metrics.success_rate < self.thresholds["min_success_rate"]:
            alerts.append({
                "type": "low_success_rate",
                "message": f"Low success rate: {metrics.success_rate:.1f}%",
                "value": metrics.success_rate,
                "threshold": self.thresholds["min_success_rate"]
            })
        
        # Check memory usage
        if metrics.memory_usage_mb > self.thresholds["max_memory_usage"]:
            alerts.append({
                "type": "high_memory_usage",
                "message": f"High memory usage: {metrics.memory_usage_mb:.1f}MB",
                "value": metrics.memory_usage_mb,
                "threshold": self.thresholds["max_memory_usage"]
            })
        
        # Check CPU usage
        if metrics.cpu_usage_percent > self.thresholds["max_cpu_usage"]:
            alerts.append({
                "type": "high_cpu_usage",
                "message": f"High CPU usage: {metrics.cpu_usage_percent:.1f}%",
                "value": metrics.cpu_usage_percent,
                "threshold": self.thresholds["max_cpu_usage"]
            })
        
        # Notify callbacks
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert["type"], alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def set_threshold(self, metric: str, value: float):
        """Update performance threshold"""
        if metric in self.thresholds:
            self.thresholds[metric] = value
            logger.info(f"Updated threshold {metric}: {value}")
        else:
            logger.warning(f"Unknown threshold metric: {metric}")

class MetricsAggregator:
    """Aggregates metrics across multiple sessions"""
    
    def __init__(self):
        self.session_metrics = {}
        self.global_stats = {
            "total_sessions": 0,
            "total_leads": 0,
            "total_emails": 0,
            "total_phones": 0,
            "avg_success_rate": 0.0,
            "avg_response_time": 0.0
        }
    
    def add_session_metrics(self, session_id: str, metrics: ScrapingMetrics):
        """Add metrics for a session"""
        self.session_metrics[session_id] = metrics
        self._update_global_stats()
    
    def _update_global_stats(self):
        """Update global statistics"""
        if not self.session_metrics:
            return
        
        sessions = list(self.session_metrics.values())
        self.global_stats["total_sessions"] = len(sessions)
        self.global_stats["total_leads"] = sum(s.leads_found for s in sessions)
        self.global_stats["total_emails"] = sum(s.emails_extracted for s in sessions)
        self.global_stats["total_phones"] = sum(s.phones_extracted for s in sessions)
        
        if sessions:
            self.global_stats["avg_success_rate"] = sum(s.success_rate for s in sessions) / len(sessions)
            self.global_stats["avg_response_time"] = sum(s.avg_response_time for s in sessions) / len(sessions)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        return self.global_stats.copy()
    
    def get_session_comparison(self) -> List[Dict[str, Any]]:
        """Get comparison data across sessions"""
        comparisons = []
        
        for session_id, metrics in self.session_metrics.items():
            elapsed = datetime.now() - metrics.start_time
            
            comparisons.append({
                "session_id": session_id,
                "leads_found": metrics.leads_found,
                "success_rate": metrics.success_rate,
                "duration_minutes": elapsed.total_seconds() / 60,
                "leads_per_minute": metrics.leads_found / max(elapsed.total_seconds() / 60, 0.1)
            })
        
        return sorted(comparisons, key=lambda x: x["leads_per_minute"], reverse=True)