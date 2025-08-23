"""
Real-time Performance Monitoring and Metrics Collection
Provides comprehensive performance tracking for scraping operations including
throughput monitoring, success rates, and automated optimization triggers.
"""

import time
import threading
import statistics
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of performance metrics"""
    LEADS_PER_MINUTE = "leads_per_minute"
    SUCCESS_RATE = "success_rate"
    DETECTION_RATE = "detection_rate"
    RESPONSE_TIME = "response_time"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    SESSION_DURATION = "session_duration"

@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SessionMetrics:
    """Metrics for a single scraping session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    leads_extracted: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    detection_attempts: int = 0
    pages_scraped: int = 0
    errors: List[str] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    platform: str = ""
    query: str = ""
    location: str = ""

@dataclass
class ThroughputSnapshot:
    """Snapshot of throughput metrics"""
    timestamp: datetime
    leads_per_minute: float
    requests_per_minute: float
    success_rate_percent: float
    detection_rate_percent: float
    average_response_time: float
    active_sessions: int
    total_leads: int

class PerformanceAggregator:
    """Aggregates and analyzes performance metrics"""
    
    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.metrics: deque = deque(maxlen=10000)
        self.session_metrics: Dict[str, SessionMetrics] = {}
        self.throughput_history: deque = deque(maxlen=288)  # 24 hours at 5-min intervals
        self.lock = threading.RLock()
        
    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric"""
        with self.lock:
            self.metrics.append(metric)
            
            # Update session metrics if available
            if metric.session_id in self.session_metrics:
                self._update_session_metric(metric)
    
    def _update_session_metric(self, metric: PerformanceMetric):
        """Update session-specific metrics"""
        session = self.session_metrics[metric.session_id]
        
        if metric.metric_type == MetricType.RESPONSE_TIME:
            session.response_times.append(metric.value)
        elif metric.metric_type == MetricType.SUCCESS_RATE:
            # Update based on success/failure
            if metric.value == 1.0:
                session.successful_requests += 1
            else:
                session.failed_requests += 1
            session.total_requests += 1
    
    def create_session(self, session_id: str, platform: str = "", 
                      query: str = "", location: str = "") -> SessionMetrics:
        """Create a new session for metrics tracking"""
        with self.lock:
            session = SessionMetrics(
                session_id=session_id,
                start_time=datetime.now(),
                platform=platform,
                query=query,
                location=location
            )
            self.session_metrics[session_id] = session
            logger.info(f"Created performance tracking for session: {session_id}")
            return session
    
    def end_session(self, session_id: str) -> Optional[SessionMetrics]:
        """End a session and finalize metrics"""
        with self.lock:
            if session_id not in self.session_metrics:
                return None
            
            session = self.session_metrics[session_id]
            session.end_time = datetime.now()
            
            # Calculate final metrics
            duration_minutes = (session.end_time - session.start_time).total_seconds() / 60
            if duration_minutes > 0:
                session.leads_per_minute = session.leads_extracted / duration_minutes
            
            logger.info(f"Ended performance tracking for session: {session_id}")
            logger.info(f"Session summary: {session.leads_extracted} leads, "
                       f"{session.successful_requests}/{session.total_requests} success rate")
            
            return session
    
    def get_current_throughput(self) -> ThroughputSnapshot:
        """Get current throughput metrics"""
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(minutes=self.window_minutes)
            
            # Filter metrics to window
            window_metrics = [
                m for m in self.metrics 
                if m.timestamp >= window_start
            ]
            
            # Calculate throughput metrics
            leads_count = len([m for m in window_metrics if m.metric_type == MetricType.LEADS_PER_MINUTE])
            requests_count = len([m for m in window_metrics if m.metric_type == MetricType.SUCCESS_RATE])
            successful_requests = len([m for m in window_metrics 
                                     if m.metric_type == MetricType.SUCCESS_RATE and m.value == 1.0])
            detection_attempts = len([m for m in window_metrics if m.metric_type == MetricType.DETECTION_RATE])
            
            # Calculate rates
            leads_per_minute = leads_count / self.window_minutes if self.window_minutes > 0 else 0
            requests_per_minute = requests_count / self.window_minutes if self.window_minutes > 0 else 0
            success_rate = (successful_requests / max(requests_count, 1)) * 100
            detection_rate = (detection_attempts / max(requests_count, 1)) * 100
            
            # Average response time
            response_times = [m.value for m in window_metrics if m.metric_type == MetricType.RESPONSE_TIME]
            avg_response_time = statistics.mean(response_times) if response_times else 0.0
            
            # Count active sessions
            active_sessions = len([s for s in self.session_metrics.values() if s.end_time is None])
            
            # Total leads across all sessions
            total_leads = sum(s.leads_extracted for s in self.session_metrics.values())
            
            snapshot = ThroughputSnapshot(
                timestamp=now,
                leads_per_minute=leads_per_minute,
                requests_per_minute=requests_per_minute,
                success_rate_percent=success_rate,
                detection_rate_percent=detection_rate,
                average_response_time=avg_response_time,
                active_sessions=active_sessions,
                total_leads=total_leads
            )
            
            # Store in history
            self.throughput_history.append(snapshot)
            
            return snapshot
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific session"""
        with self.lock:
            if session_id not in self.session_metrics:
                return None
            
            session = self.session_metrics[session_id]
            
            # Calculate metrics
            duration = (session.end_time or datetime.now()) - session.start_time
            duration_minutes = duration.total_seconds() / 60
            
            success_rate = (session.successful_requests / max(session.total_requests, 1)) * 100
            error_rate = (session.failed_requests / max(session.total_requests, 1)) * 100
            detection_rate = (session.detection_attempts / max(session.total_requests, 1)) * 100
            
            avg_response_time = statistics.mean(session.response_times) if session.response_times else 0.0
            
            return {
                'session_id': session.session_id,
                'platform': session.platform,
                'query': session.query,
                'location': session.location,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'duration_minutes': duration_minutes,
                'leads_extracted': session.leads_extracted,
                'leads_per_minute': session.leads_extracted / max(duration_minutes, 1),
                'total_requests': session.total_requests,
                'successful_requests': session.successful_requests,
                'failed_requests': session.failed_requests,
                'success_rate_percent': success_rate,
                'error_rate_percent': error_rate,
                'detection_rate_percent': detection_rate,
                'detection_attempts': session.detection_attempts,
                'average_response_time': avg_response_time,
                'pages_scraped': session.pages_scraped,
                'errors': session.errors
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_throughput = self.get_current_throughput()
        
        # Historical analysis
        if len(self.throughput_history) > 1:
            historical_leads = [s.leads_per_minute for s in self.throughput_history]
            historical_success = [s.success_rate_percent for s in self.throughput_history]
            
            avg_leads_per_minute = statistics.mean(historical_leads)
            avg_success_rate = statistics.mean(historical_success)
            
            # Trends
            recent_leads = historical_leads[-5:] if len(historical_leads) >= 5 else historical_leads
            recent_avg = statistics.mean(recent_leads)
            trend = "improving" if recent_avg > avg_leads_per_minute else "declining"
        else:
            avg_leads_per_minute = current_throughput.leads_per_minute
            avg_success_rate = current_throughput.success_rate_percent
            trend = "insufficient_data"
        
        # Session analysis
        completed_sessions = [s for s in self.session_metrics.values() if s.end_time is not None]
        active_sessions = [s for s in self.session_metrics.values() if s.end_time is None]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'current_metrics': {
                'leads_per_minute': current_throughput.leads_per_minute,
                'requests_per_minute': current_throughput.requests_per_minute,
                'success_rate_percent': current_throughput.success_rate_percent,
                'detection_rate_percent': current_throughput.detection_rate_percent,
                'average_response_time': current_throughput.average_response_time,
                'active_sessions': current_throughput.active_sessions,
                'total_leads': current_throughput.total_leads
            },
            'historical_metrics': {
                'average_leads_per_minute': avg_leads_per_minute,
                'average_success_rate': avg_success_rate,
                'performance_trend': trend,
                'data_points': len(self.throughput_history)
            },
            'session_analysis': {
                'total_sessions': len(self.session_metrics),
                'active_sessions': len(active_sessions),
                'completed_sessions': len(completed_sessions),
                'average_session_duration': self._calculate_avg_session_duration(completed_sessions),
                'most_productive_platform': self._get_most_productive_platform(),
                'common_errors': self._get_common_errors()
            },
            'performance_goals': {
                'target_leads_per_minute': 50,  # Configurable target
                'target_success_rate': 95,
                'target_detection_rate': 5,
                'meeting_goals': self._assess_goal_performance(current_throughput)
            }
        }
    
    def _calculate_avg_session_duration(self, sessions: List[SessionMetrics]) -> float:
        """Calculate average session duration in minutes"""
        if not sessions:
            return 0.0
        
        durations = []
        for session in sessions:
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60
                durations.append(duration)
        
        return statistics.mean(durations) if durations else 0.0
    
    def _get_most_productive_platform(self) -> Dict[str, Any]:
        """Identify most productive platform"""
        platform_stats = defaultdict(lambda: {'leads': 0, 'sessions': 0})
        
        for session in self.session_metrics.values():
            if session.platform:
                platform_stats[session.platform]['leads'] += session.leads_extracted
                platform_stats[session.platform]['sessions'] += 1
        
        if not platform_stats:
            return {'platform': 'none', 'avg_leads_per_session': 0}
        
        # Calculate average leads per session for each platform
        best_platform = max(platform_stats.items(), 
                          key=lambda x: x[1]['leads'] / max(x[1]['sessions'], 1))
        
        return {
            'platform': best_platform[0],
            'avg_leads_per_session': best_platform[1]['leads'] / best_platform[1]['sessions'],
            'total_leads': best_platform[1]['leads'],
            'total_sessions': best_platform[1]['sessions']
        }
    
    def _get_common_errors(self) -> List[Dict[str, Any]]:
        """Get most common errors across sessions"""
        error_counts = defaultdict(int)
        
        for session in self.session_metrics.values():
            for error in session.errors:
                error_counts[error] += 1
        
        # Sort by frequency
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'error': error, 'count': count, 'percentage': count / len(self.session_metrics) * 100}
            for error, count in sorted_errors[:5]  # Top 5 errors
        ]
    
    def _assess_goal_performance(self, snapshot: ThroughputSnapshot) -> Dict[str, bool]:
        """Assess if performance goals are being met"""
        return {
            'leads_per_minute_goal': snapshot.leads_per_minute >= 50,
            'success_rate_goal': snapshot.success_rate_percent >= 95,
            'detection_rate_goal': snapshot.detection_rate_percent <= 5,
            'response_time_goal': snapshot.average_response_time <= 3.0
        }

class PerformanceAlertSystem:
    """System for monitoring performance and triggering alerts"""
    
    def __init__(self, aggregator: PerformanceAggregator):
        self.aggregator = aggregator
        self.alert_callbacks: List[Callable] = []
        self.alert_thresholds = {
            'min_leads_per_minute': 10,
            'min_success_rate': 80,
            'max_detection_rate': 10,
            'max_response_time': 5.0,
            'max_error_rate': 20
        }
        self.last_alert_time = {}
        self.alert_cooldown_minutes = 5
        
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add an alert callback function"""
        self.alert_callbacks.append(callback)
    
    def check_performance_alerts(self):
        """Check current performance against thresholds and trigger alerts"""
        current_throughput = self.aggregator.get_current_throughput()
        alerts_triggered = []
        
        # Check leads per minute
        if current_throughput.leads_per_minute < self.alert_thresholds['min_leads_per_minute']:
            alert = {
                'type': 'low_throughput',
                'message': f"Low throughput: {current_throughput.leads_per_minute:.1f} leads/min",
                'severity': 'warning',
                'current_value': current_throughput.leads_per_minute,
                'threshold': self.alert_thresholds['min_leads_per_minute']
            }
            if self._should_send_alert('low_throughput'):
                alerts_triggered.append(alert)
        
        # Check success rate
        if current_throughput.success_rate_percent < self.alert_thresholds['min_success_rate']:
            alert = {
                'type': 'low_success_rate',
                'message': f"Low success rate: {current_throughput.success_rate_percent:.1f}%",
                'severity': 'error',
                'current_value': current_throughput.success_rate_percent,
                'threshold': self.alert_thresholds['min_success_rate']
            }
            if self._should_send_alert('low_success_rate'):
                alerts_triggered.append(alert)
        
        # Check detection rate
        if current_throughput.detection_rate_percent > self.alert_thresholds['max_detection_rate']:
            alert = {
                'type': 'high_detection_rate',
                'message': f"High detection rate: {current_throughput.detection_rate_percent:.1f}%",
                'severity': 'critical',
                'current_value': current_throughput.detection_rate_percent,
                'threshold': self.alert_thresholds['max_detection_rate']
            }
            if self._should_send_alert('high_detection_rate'):
                alerts_triggered.append(alert)
        
        # Check response time
        if current_throughput.average_response_time > self.alert_thresholds['max_response_time']:
            alert = {
                'type': 'slow_response',
                'message': f"Slow response time: {current_throughput.average_response_time:.1f}s",
                'severity': 'warning',
                'current_value': current_throughput.average_response_time,
                'threshold': self.alert_thresholds['max_response_time']
            }
            if self._should_send_alert('slow_response'):
                alerts_triggered.append(alert)
        
        # Send alerts
        for alert in alerts_triggered:
            self._send_alert(alert)
        
        return alerts_triggered
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """Check if alert should be sent based on cooldown"""
        now = datetime.now()
        last_alert = self.last_alert_time.get(alert_type)
        
        if not last_alert:
            return True
        
        cooldown = timedelta(minutes=self.alert_cooldown_minutes)
        return now - last_alert > cooldown
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert to all registered callbacks"""
        self.last_alert_time[alert['type']] = datetime.now()
        
        logger.warning(f"Performance Alert: {alert['message']}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert['type'], alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

class PerformanceOptimizer:
    """Automatic performance optimization system"""
    
    def __init__(self, aggregator: PerformanceAggregator, alert_system: PerformanceAlertSystem):
        self.aggregator = aggregator
        self.alert_system = alert_system
        self.optimization_rules = []
        self.optimization_history = []
        
        # Register alert callback
        self.alert_system.add_alert_callback(self._handle_performance_alert)
    
    def _handle_performance_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """Handle performance alerts by triggering optimizations"""
        optimization_actions = {
            'low_throughput': self._optimize_throughput,
            'low_success_rate': self._optimize_success_rate,
            'high_detection_rate': self._optimize_stealth,
            'slow_response': self._optimize_response_time
        }
        
        if alert_type in optimization_actions:
            try:
                optimization_actions[alert_type](alert_data)
            except Exception as e:
                logger.error(f"Optimization error for {alert_type}: {e}")
    
    def _optimize_throughput(self, alert_data: Dict[str, Any]):
        """Optimize system for better throughput"""
        logger.info("Triggering throughput optimization")
        
        optimization = {
            'type': 'throughput',
            'timestamp': datetime.now(),
            'trigger': alert_data,
            'actions': [
                'Increase concurrent sessions',
                'Optimize scroll strategies',
                'Enable aggressive caching'
            ]
        }
        
        self.optimization_history.append(optimization)
        # Implementation would depend on your specific system architecture
    
    def _optimize_success_rate(self, alert_data: Dict[str, Any]):
        """Optimize system for better success rate"""
        logger.info("Triggering success rate optimization")
        
        optimization = {
            'type': 'success_rate',
            'timestamp': datetime.now(),
            'trigger': alert_data,
            'actions': [
                'Increase retry attempts',
                'Add request delays',
                'Switch to backup proxy pool'
            ]
        }
        
        self.optimization_history.append(optimization)
    
    def _optimize_stealth(self, alert_data: Dict[str, Any]):
        """Optimize anti-detection mechanisms"""
        logger.info("Triggering stealth optimization")
        
        optimization = {
            'type': 'stealth',
            'timestamp': datetime.now(),
            'trigger': alert_data,
            'actions': [
                'Increase stealth level',
                'Rotate user agents',
                'Enable proxy rotation',
                'Add human behavior delays'
            ]
        }
        
        self.optimization_history.append(optimization)
    
    def _optimize_response_time(self, alert_data: Dict[str, Any]):
        """Optimize system for better response times"""
        logger.info("Triggering response time optimization")
        
        optimization = {
            'type': 'response_time',
            'timestamp': datetime.now(),
            'trigger': alert_data,
            'actions': [
                'Enable image blocking',
                'Optimize scroll strategies',
                'Reduce wait times'
            ]
        }
        
        self.optimization_history.append(optimization)

class PerformanceMonitor:
    """Central performance monitoring system"""
    
    def __init__(self):
        self.aggregator = PerformanceAggregator()
        self.alert_system = PerformanceAlertSystem(self.aggregator)
        self.optimizer = PerformanceOptimizer(self.aggregator, self.alert_system)
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Check for performance alerts
                self.alert_system.check_performance_alerts()
                
                # Update throughput metrics
                self.aggregator.get_current_throughput()
                
                # Sleep until next check
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(60)
    
    def track_leads_extracted(self, session_id: str, count: int):
        """Track leads extracted for a session"""
        if session_id in self.aggregator.session_metrics:
            self.aggregator.session_metrics[session_id].leads_extracted += count
        
        # Add metric
        metric = PerformanceMetric(
            metric_type=MetricType.LEADS_PER_MINUTE,
            value=count,
            timestamp=datetime.now(),
            session_id=session_id
        )
        self.aggregator.add_metric(metric)
    
    def track_request_result(self, session_id: str, success: bool, response_time: float):
        """Track individual request results"""
        # Success rate metric
        success_metric = PerformanceMetric(
            metric_type=MetricType.SUCCESS_RATE,
            value=1.0 if success else 0.0,
            timestamp=datetime.now(),
            session_id=session_id
        )
        self.aggregator.add_metric(success_metric)
        
        # Response time metric
        time_metric = PerformanceMetric(
            metric_type=MetricType.RESPONSE_TIME,
            value=response_time,
            timestamp=datetime.now(),
            session_id=session_id
        )
        self.aggregator.add_metric(time_metric)
    
    def track_detection_attempt(self, session_id: str):
        """Track bot detection attempt"""
        if session_id in self.aggregator.session_metrics:
            self.aggregator.session_metrics[session_id].detection_attempts += 1
        
        metric = PerformanceMetric(
            metric_type=MetricType.DETECTION_RATE,
            value=1.0,
            timestamp=datetime.now(),
            session_id=session_id
        )
        self.aggregator.add_metric(metric)
    
    def create_session(self, session_id: str, platform: str = "", 
                      query: str = "", location: str = "") -> SessionMetrics:
        """Create performance tracking session"""
        return self.aggregator.create_session(session_id, platform, query, location)
    
    def end_session(self, session_id: str) -> Optional[SessionMetrics]:
        """End performance tracking session"""
        return self.aggregator.end_session(session_id)
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        return self.aggregator.get_performance_report()
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        report = self.get_performance_dashboard()
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Performance metrics exported to: {filepath}")

# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

if __name__ == "__main__":
    # Test performance monitoring system
    print("Performance Monitoring System Test")
    print("=" * 50)
    
    # Create monitor
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    try:
        # Create test session
        session = monitor.create_session("test_session", "bing", "restaurants", "Miami")
        print(f"Created session: {session.session_id}")
        
        # Simulate some metrics
        for i in range(10):
            monitor.track_leads_extracted("test_session", 5)
            monitor.track_request_result("test_session", True, 1.5)
            time.sleep(1)
        
        # Get dashboard
        dashboard = monitor.get_performance_dashboard()
        print(f"Current leads/min: {dashboard['current_metrics']['leads_per_minute']:.1f}")
        print(f"Success rate: {dashboard['current_metrics']['success_rate_percent']:.1f}%")
        
        # End session
        final_session = monitor.end_session("test_session")
        print(f"Session ended with {final_session.leads_extracted} total leads")
        
    finally:
        monitor.stop_monitoring()