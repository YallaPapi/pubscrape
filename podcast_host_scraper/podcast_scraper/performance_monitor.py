"""
Performance monitoring and optimization utilities.
Provides real-time monitoring, memory management, and performance analytics.
"""

import psutil
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    active_threads: int = 0
    open_files: int = 0
    
    # Application-specific metrics
    requests_per_second: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    avg_response_time: float = 0.0


class PerformanceMonitor:
    """Real-time performance monitoring and analytics."""
    
    def __init__(self, monitoring_interval: float = 5.0, history_size: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            monitoring_interval: Seconds between metric collections
            history_size: Maximum number of historical metrics to keep
        """
        self.logger = logging.getLogger(__name__)
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        
        # Metrics storage
        self.metrics_history: List[PerformanceMetrics] = []
        self.current_metrics = PerformanceMetrics()
        
        # Monitoring control
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # Performance thresholds for alerts
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'disk_io_warning': 100.0,  # MB/s
            'disk_io_critical': 200.0,
            'error_rate_warning': 5.0,  # %
            'error_rate_critical': 10.0
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[str, PerformanceMetrics], None]] = []
        
        # Application-specific counters
        self.request_counter = 0
        self.error_counter = 0
        self.response_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Baseline metrics
        self.baseline_metrics = None
        self._last_io_counters = None
        self._last_net_counters = None
        
        self.logger.info("Performance monitor initialized")
    
    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if self._monitoring:
            self.logger.warning("Performance monitoring already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info(f"Performance monitoring started (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self.monitoring_interval + 1)
        
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                metrics = self._collect_metrics()
                
                with self._lock:
                    self.current_metrics = metrics
                    self.metrics_history.append(metrics)
                    
                    # Trim history if needed
                    if len(self.metrics_history) > self.history_size:
                        self.metrics_history.pop(0)
                
                # Check for alerts
                self._check_alerts(metrics)
                
                # Set baseline if not set
                if self.baseline_metrics is None:
                    self.baseline_metrics = metrics
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current system and application metrics."""
        metrics = PerformanceMetrics()
        
        try:
            # System metrics
            metrics.cpu_percent = psutil.cpu_percent()
            
            memory_info = psutil.virtual_memory()
            metrics.memory_percent = memory_info.percent
            metrics.memory_used_mb = memory_info.used / (1024 * 1024)
            metrics.memory_available_mb = memory_info.available / (1024 * 1024)
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io and self._last_io_counters:
                read_diff = disk_io.read_bytes - self._last_io_counters.read_bytes
                write_diff = disk_io.write_bytes - self._last_io_counters.write_bytes
                metrics.disk_io_read_mb = read_diff / (1024 * 1024) / self.monitoring_interval
                metrics.disk_io_write_mb = write_diff / (1024 * 1024) / self.monitoring_interval
            
            if disk_io:
                self._last_io_counters = disk_io
            
            # Network I/O
            net_io = psutil.net_io_counters()
            if net_io and self._last_net_counters:
                sent_diff = net_io.bytes_sent - self._last_net_counters.bytes_sent
                recv_diff = net_io.bytes_recv - self._last_net_counters.bytes_recv
                metrics.network_sent_mb = sent_diff / (1024 * 1024) / self.monitoring_interval
                metrics.network_recv_mb = recv_diff / (1024 * 1024) / self.monitoring_interval
            
            if net_io:
                self._last_net_counters = net_io
            
            # Process metrics
            process = psutil.Process()
            metrics.active_threads = process.num_threads()
            try:
                metrics.open_files = len(process.open_files())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                metrics.open_files = 0
            
            # Application metrics
            if self.request_counter > 0:
                metrics.requests_per_second = self.request_counter / self.monitoring_interval
                self.request_counter = 0
            
            total_cache_requests = self.cache_hits + self.cache_misses
            if total_cache_requests > 0:
                metrics.cache_hit_rate = (self.cache_hits / total_cache_requests) * 100
            
            total_requests = self.request_counter + self.error_counter
            if total_requests > 0:
                metrics.error_rate = (self.error_counter / total_requests) * 100
            
            if self.response_times:
                metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
                self.response_times.clear()
        
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _check_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check metrics against thresholds and trigger alerts."""
        alerts = []
        
        # CPU alerts
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(('CPU_CRITICAL', f"CPU usage critically high: {metrics.cpu_percent:.1f}%"))
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(('CPU_WARNING', f"CPU usage high: {metrics.cpu_percent:.1f}%"))
        
        # Memory alerts
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(('MEMORY_CRITICAL', f"Memory usage critically high: {metrics.memory_percent:.1f}%"))
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(('MEMORY_WARNING', f"Memory usage high: {metrics.memory_percent:.1f}%"))
        
        # Disk I/O alerts
        total_io = metrics.disk_io_read_mb + metrics.disk_io_write_mb
        if total_io >= self.thresholds['disk_io_critical']:
            alerts.append(('DISK_IO_CRITICAL', f"Disk I/O critically high: {total_io:.1f} MB/s"))
        elif total_io >= self.thresholds['disk_io_warning']:
            alerts.append(('DISK_IO_WARNING', f"Disk I/O high: {total_io:.1f} MB/s"))
        
        # Error rate alerts
        if metrics.error_rate >= self.thresholds['error_rate_critical']:
            alerts.append(('ERROR_RATE_CRITICAL', f"Error rate critically high: {metrics.error_rate:.1f}%"))
        elif metrics.error_rate >= self.thresholds['error_rate_warning']:
            alerts.append(('ERROR_RATE_WARNING', f"Error rate high: {metrics.error_rate:.1f}%"))
        
        # Trigger alert callbacks
        for alert_type, alert_message in alerts:
            self.logger.warning(f"PERFORMANCE ALERT: {alert_message}")
            for callback in self.alert_callbacks:
                try:
                    callback(alert_type, metrics)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[str, PerformanceMetrics], None]) -> None:
        """Add callback for performance alerts."""
        self.alert_callbacks.append(callback)
    
    def record_request(self, response_time: float = 0.0, is_error: bool = False) -> None:
        """Record a request for metrics calculation."""
        if is_error:
            self.error_counter += 1
        else:
            self.request_counter += 1
        
        if response_time > 0:
            self.response_times.append(response_time)
    
    def record_cache_access(self, hit: bool = True) -> None:
        """Record cache access for hit rate calculation."""
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        with self._lock:
            return self.current_metrics
    
    def get_metrics_history(self, last_n: Optional[int] = None) -> List[PerformanceMetrics]:
        """Get historical metrics."""
        with self._lock:
            if last_n is None:
                return self.metrics_history.copy()
            else:
                return self.metrics_history[-last_n:].copy()
    
    def get_performance_summary(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get performance summary for the specified time window."""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        with self._lock:
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {'error': 'No metrics available for the specified window'}
        
        # Calculate aggregates
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        io_values = [m.disk_io_read_mb + m.disk_io_write_mb for m in recent_metrics]
        
        summary = {
            'window_minutes': window_minutes,
            'sample_count': len(recent_metrics),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'min': min(memory_values),
                'max': max(memory_values),
                'current_used_mb': recent_metrics[-1].memory_used_mb
            },
            'disk_io': {
                'avg_mb_per_sec': sum(io_values) / len(io_values),
                'max_mb_per_sec': max(io_values)
            },
            'requests_per_second': recent_metrics[-1].requests_per_second if recent_metrics else 0,
            'cache_hit_rate': recent_metrics[-1].cache_hit_rate if recent_metrics else 0,
            'error_rate': recent_metrics[-1].error_rate if recent_metrics else 0,
            'avg_response_time': recent_metrics[-1].avg_response_time if recent_metrics else 0
        }
        
        return summary
    
    def export_metrics(self, output_file: str, format: str = 'json') -> None:
        """Export metrics to file."""
        with self._lock:
            metrics_data = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'cpu_percent': m.cpu_percent,
                    'memory_percent': m.memory_percent,
                    'memory_used_mb': m.memory_used_mb,
                    'disk_io_read_mb': m.disk_io_read_mb,
                    'disk_io_write_mb': m.disk_io_write_mb,
                    'network_sent_mb': m.network_sent_mb,
                    'network_recv_mb': m.network_recv_mb,
                    'active_threads': m.active_threads,
                    'requests_per_second': m.requests_per_second,
                    'cache_hit_rate': m.cache_hit_rate,
                    'error_rate': m.error_rate,
                    'avg_response_time': m.avg_response_time
                }
                for m in self.metrics_history
            ]
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'json':
            with open(output_path, 'w') as f:
                json.dump(metrics_data, f, indent=2)
        elif format.lower() == 'csv':
            import csv
            if metrics_data:
                with open(output_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=metrics_data[0].keys())
                    writer.writeheader()
                    writer.writerows(metrics_data)
        
        self.logger.info(f"Metrics exported to {output_path}")
    
    def optimize_performance(self) -> Dict[str, str]:
        """Provide performance optimization recommendations."""
        current = self.get_current_metrics()
        recommendations = []
        
        # Memory optimization
        if current.memory_percent > 80:
            recommendations.append("High memory usage detected. Consider enabling garbage collection or reducing cache size.")
        
        # CPU optimization
        if current.cpu_percent > 80:
            recommendations.append("High CPU usage detected. Consider reducing concurrent workers or adding delays between requests.")
        
        # Disk I/O optimization
        total_io = current.disk_io_read_mb + current.disk_io_write_mb
        if total_io > 50:
            recommendations.append("High disk I/O detected. Consider enabling caching or using in-memory processing.")
        
        # Threading optimization
        if current.active_threads > 20:
            recommendations.append("High thread count detected. Consider using thread pools or async processing.")
        
        # Application-specific recommendations
        if current.cache_hit_rate < 50 and current.cache_hit_rate > 0:
            recommendations.append("Low cache hit rate. Consider increasing cache size or improving cache key strategy.")
        
        if current.error_rate > 5:
            recommendations.append("High error rate detected. Consider implementing retry logic and better error handling.")
        
        if current.avg_response_time > 5.0:
            recommendations.append("Slow response times detected. Consider optimizing queries or adding connection pooling.")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'current_metrics': {
                'cpu_percent': current.cpu_percent,
                'memory_percent': current.memory_percent,
                'disk_io_mb_per_sec': total_io,
                'active_threads': current.active_threads,
                'error_rate': current.error_rate,
                'cache_hit_rate': current.cache_hit_rate
            },
            'recommendations': recommendations
        }


class MemoryOptimizer:
    """Memory usage optimization utilities."""
    
    @staticmethod
    def force_garbage_collection() -> Dict[str, int]:
        """Force garbage collection and return collection stats."""
        import gc
        
        # Get before stats
        before_objects = len(gc.get_objects())
        before_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        # Force collection
        collected = gc.collect()
        
        # Get after stats
        after_objects = len(gc.get_objects())
        after_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        return {
            'objects_before': before_objects,
            'objects_after': after_objects,
            'objects_collected': before_objects - after_objects,
            'memory_before_mb': before_memory,
            'memory_after_mb': after_memory,
            'memory_freed_mb': before_memory - after_memory,
            'gc_collected': collected
        }
    
    @staticmethod
    def get_memory_usage_by_type() -> Dict[str, int]:
        """Get memory usage breakdown by object type."""
        import gc
        from collections import defaultdict
        
        type_counts = defaultdict(int)
        for obj in gc.get_objects():
            type_counts[type(obj).__name__] += 1
        
        # Sort by count
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_types[:20])  # Top 20 types
    
    @staticmethod
    def optimize_memory_usage() -> Dict[str, Any]:
        """Perform comprehensive memory optimization."""
        # Clear caches
        import sys
        
        # Force garbage collection
        gc_stats = MemoryOptimizer.force_garbage_collection()
        
        # Clear import caches
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
        
        # Get final memory usage
        final_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        return {
            'gc_stats': gc_stats,
            'final_memory_mb': final_memory,
            'optimization_completed': True
        }


def create_performance_alert_handler(log_file: str = "performance_alerts.log") -> Callable:
    """Create a performance alert handler that logs to file."""
    
    alert_logger = logging.getLogger('performance_alerts')
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - ALERT - %(message)s')
    handler.setFormatter(formatter)
    alert_logger.addHandler(handler)
    alert_logger.setLevel(logging.WARNING)
    
    def alert_handler(alert_type: str, metrics: PerformanceMetrics):
        """Handle performance alerts."""
        alert_logger.warning(f"{alert_type}: CPU={metrics.cpu_percent:.1f}%, "
                           f"Memory={metrics.memory_percent:.1f}%, "
                           f"Errors={metrics.error_rate:.1f}%")
    
    return alert_handler