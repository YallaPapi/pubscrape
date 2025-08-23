"""
Load Testing and Performance Validation System
Tests the scraper system with 1000+ leads while maintaining <2GB memory constraint
and <5% detection rate requirements.
"""

import time
import threading
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging
import json
import csv
from pathlib import Path
import psutil
import random

from .session_orchestrator import SessionOrchestrator, get_session_orchestrator
from .memory_manager import ResourcePoolConfig
from .performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    target_leads: int = 1000
    max_memory_mb: int = 2048
    max_detection_rate: float = 0.05  # 5%
    test_duration_minutes: int = 60
    concurrent_sessions: int = 5
    platforms: List[str] = field(default_factory=lambda: ['bing', 'google'])
    test_queries: List[Dict[str, str]] = field(default_factory=list)
    validation_interval_seconds: int = 10
    memory_check_interval_seconds: int = 5
    report_output_dir: str = "load_test_results"

@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    test_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_leads_extracted: int = 0
    total_tasks_submitted: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    peak_memory_usage_mb: float = 0.0
    average_memory_usage_mb: float = 0.0
    peak_detection_rate: float = 0.0
    average_detection_rate: float = 0.0
    leads_per_minute_history: List[float] = field(default_factory=list)
    memory_usage_history: List[float] = field(default_factory=list)
    detection_rate_history: List[float] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    platform_performance: Dict[str, Dict] = field(default_factory=dict)

class LoadTestRunner:
    """Executes comprehensive load tests on the scraping system"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.test_metrics = LoadTestMetrics(
            test_id=f"load_test_{int(time.time())}",
            start_time=datetime.now()
        )
        
        # System components
        resource_config = ResourcePoolConfig(
            max_sessions=self.config.concurrent_sessions,
            memory_threshold_mb=int(self.config.max_memory_mb * 0.9),  # 90% threshold
            session_timeout_minutes=30,
            enable_aggressive_cleanup=True
        )
        
        self.orchestrator = get_session_orchestrator(resource_config)
        self.performance_monitor = get_performance_monitor()
        
        # Test management
        self.running = False
        self.monitoring_threads: List[threading.Thread] = []
        self.task_ids: List[str] = []
        self.validation_results: List[Dict] = []
        
        # Initialize test queries if not provided
        if not self.config.test_queries:
            self._generate_default_test_queries()
        
        # Create output directory
        self.output_dir = Path(self.config.report_output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def _generate_default_test_queries(self):
        """Generate default test queries for comprehensive testing"""
        business_types = [
            "restaurants", "doctors", "lawyers", "dentists", "hotels",
            "gyms", "pharmacies", "banks", "gas stations", "grocery stores",
            "coffee shops", "nail salons", "auto repair", "real estate agents",
            "insurance agencies", "accounting firms", "hair salons", "pet stores",
            "hardware stores", "medical clinics"
        ]
        
        locations = [
            "Miami, FL", "New York, NY", "Los Angeles, CA", "Chicago, IL",
            "Houston, TX", "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX",
            "San Diego, CA", "Dallas, TX", "San Jose, CA", "Austin, TX",
            "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC",
            "San Francisco, CA", "Indianapolis, IN", "Seattle, WA", "Denver, CO"
        ]
        
        # Generate combinations
        for i in range(min(50, len(business_types) * 2)):  # 50 test queries max
            business = random.choice(business_types)
            location = random.choice(locations)
            platform = random.choice(self.config.platforms)
            
            self.config.test_queries.append({
                "platform": platform,
                "query": business,
                "location": location,
                "priority": random.randint(1, 5)
            })
        
        logger.info(f"Generated {len(self.config.test_queries)} test queries")
    
    def run_load_test(self) -> LoadTestMetrics:
        """Execute the complete load test"""
        logger.info(f"Starting load test: {self.test_metrics.test_id}")
        logger.info(f"Target: {self.config.target_leads} leads")
        logger.info(f"Memory limit: {self.config.max_memory_mb}MB")
        logger.info(f"Detection rate limit: {self.config.max_detection_rate:.1%}")
        logger.info(f"Test duration: {self.config.test_duration_minutes} minutes")
        
        try:
            # Start system components
            self._setup_test_environment()
            
            # Start monitoring
            self._start_monitoring()
            
            # Execute test phases
            self._execute_test_phases()
            
            # Wait for completion or timeout
            self._wait_for_test_completion()
            
            # Collect final metrics
            self._collect_final_metrics()
            
        except Exception as e:
            logger.error(f"Load test error: {e}")
            self.test_metrics.error_messages.append(str(e))
        
        finally:
            # Clean up
            self._cleanup_test_environment()
        
        # Generate report
        self._generate_test_report()
        
        logger.info(f"Load test completed: {self.test_metrics.test_id}")
        return self.test_metrics
    
    def _setup_test_environment(self):
        """Set up the test environment"""
        # Start orchestration
        self.orchestrator.start_orchestration()
        
        # Start performance monitoring
        self.performance_monitor.start_monitoring()
        
        # Initialize platform performance tracking
        for platform in self.config.platforms:
            self.test_metrics.platform_performance[platform] = {
                'tasks_submitted': 0,
                'tasks_completed': 0,
                'leads_extracted': 0,
                'average_leads_per_task': 0.0,
                'error_count': 0,
                'detection_count': 0
            }
        
        self.running = True
        logger.info("Test environment setup complete")
    
    def _start_monitoring(self):
        """Start monitoring threads"""
        # Memory monitoring thread
        memory_thread = threading.Thread(
            target=self._memory_monitoring_loop,
            name="MemoryMonitor",
            daemon=True
        )
        memory_thread.start()
        self.monitoring_threads.append(memory_thread)
        
        # Performance monitoring thread
        performance_thread = threading.Thread(
            target=self._performance_monitoring_loop,
            name="PerformanceMonitor",
            daemon=True
        )
        performance_thread.start()
        self.monitoring_threads.append(performance_thread)
        
        # Validation monitoring thread
        validation_thread = threading.Thread(
            target=self._validation_monitoring_loop,
            name="ValidationMonitor",
            daemon=True
        )
        validation_thread.start()
        self.monitoring_threads.append(validation_thread)
        
        logger.info("Monitoring threads started")
    
    def _execute_test_phases(self):
        """Execute test phases with progressive load"""
        logger.info("Executing test phases")
        
        # Phase 1: Ramp up (25% of queries)
        phase1_queries = self.config.test_queries[:len(self.config.test_queries)//4]
        self._submit_task_batch(phase1_queries, "Phase 1: Ramp Up")
        time.sleep(30)  # Allow initial tasks to start
        
        # Phase 2: Full load (remaining queries)
        phase2_queries = self.config.test_queries[len(self.config.test_queries)//4:]
        self._submit_task_batch(phase2_queries, "Phase 2: Full Load")
    
    def _submit_task_batch(self, queries: List[Dict], phase_name: str):
        """Submit a batch of tasks"""
        logger.info(f"{phase_name}: Submitting {len(queries)} tasks")
        
        batch_task_data = []
        for query_data in queries:
            batch_task_data.append({
                'platform': query_data['platform'],
                'query': query_data['query'],
                'location': query_data['location'],
                'priority': query_data.get('priority', 1),
                'max_results': min(200, self.config.target_leads // len(self.config.test_queries))
            })
        
        # Submit batch
        batch_task_ids = self.orchestrator.submit_batch_tasks(batch_task_data)
        self.task_ids.extend(batch_task_ids)
        
        # Update metrics
        self.test_metrics.total_tasks_submitted += len(batch_task_ids)
        
        # Update platform metrics
        for query_data in queries:
            platform = query_data['platform']
            if platform in self.test_metrics.platform_performance:
                self.test_metrics.platform_performance[platform]['tasks_submitted'] += 1
        
        logger.info(f"{phase_name}: Submitted {len(batch_task_ids)} tasks")
    
    def _memory_monitoring_loop(self):
        """Monitor memory usage continuously"""
        logger.info("Memory monitoring started")
        
        while self.running:
            try:
                # Get current memory usage
                process = psutil.Process()
                memory_info = process.memory_info()
                current_memory_mb = memory_info.rss / (1024 * 1024)
                
                # Update metrics
                self.test_metrics.memory_usage_history.append(current_memory_mb)
                if current_memory_mb > self.test_metrics.peak_memory_usage_mb:
                    self.test_metrics.peak_memory_usage_mb = current_memory_mb
                
                # Check memory limit
                if current_memory_mb > self.config.max_memory_mb:
                    error_msg = f"Memory limit exceeded: {current_memory_mb:.1f}MB > {self.config.max_memory_mb}MB"
                    logger.critical(error_msg)
                    self.test_metrics.error_messages.append(error_msg)
                    
                    # Trigger emergency cleanup
                    try:
                        from .memory_manager import get_resource_manager
                        resource_manager = get_resource_manager()
                        resource_manager.emergency_cleanup()
                    except Exception as e:
                        logger.error(f"Emergency cleanup failed: {e}")
                
                time.sleep(self.config.memory_check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(30)
    
    def _performance_monitoring_loop(self):
        """Monitor performance metrics continuously"""
        logger.info("Performance monitoring started")
        
        while self.running:
            try:
                # Get performance dashboard
                dashboard = self.performance_monitor.get_performance_dashboard()
                current_metrics = dashboard['current_metrics']
                
                # Track leads per minute
                leads_per_minute = current_metrics.get('leads_per_minute', 0)
                self.test_metrics.leads_per_minute_history.append(leads_per_minute)
                
                # Track detection rate
                detection_rate = current_metrics.get('detection_rate_percent', 0) / 100
                self.test_metrics.detection_rate_history.append(detection_rate)
                
                if detection_rate > self.test_metrics.peak_detection_rate:
                    self.test_metrics.peak_detection_rate = detection_rate
                
                # Check detection rate limit
                if detection_rate > self.config.max_detection_rate:
                    error_msg = f"Detection rate exceeded: {detection_rate:.1%} > {self.config.max_detection_rate:.1%}"
                    logger.warning(error_msg)
                    self.test_metrics.error_messages.append(error_msg)
                
                time.sleep(self.config.validation_interval_seconds)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(30)
    
    def _validation_monitoring_loop(self):
        """Monitor validation criteria continuously"""
        logger.info("Validation monitoring started")
        
        while self.running:
            try:
                # Get orchestration status
                status = self.orchestrator.get_orchestration_status()
                
                # Update task completion metrics
                completed_tasks = status['task_queue']['completed_tasks']
                failed_tasks = status['task_queue']['failed_tasks']
                total_leads = status['orchestration_metrics']['total_leads_extracted']
                
                self.test_metrics.total_tasks_completed = completed_tasks
                self.test_metrics.total_tasks_failed = failed_tasks
                self.test_metrics.total_leads_extracted = total_leads
                
                # Check if target reached
                if total_leads >= self.config.target_leads:
                    logger.info(f"Target leads reached: {total_leads}/{self.config.target_leads}")
                    break
                
                # Validation check
                validation_result = {
                    'timestamp': datetime.now().isoformat(),
                    'total_leads': total_leads,
                    'memory_usage_mb': self.test_metrics.peak_memory_usage_mb,
                    'detection_rate': self.test_metrics.peak_detection_rate,
                    'within_memory_limit': self.test_metrics.peak_memory_usage_mb <= self.config.max_memory_mb,
                    'within_detection_limit': self.test_metrics.peak_detection_rate <= self.config.max_detection_rate,
                    'active_sessions': status['current_sessions']['active_sessions'],
                    'system_health': status['system_health']
                }
                
                self.validation_results.append(validation_result)
                
                # Log progress
                if len(self.validation_results) % 6 == 0:  # Every minute with 10s interval
                    logger.info(f"Progress: {total_leads}/{self.config.target_leads} leads, "
                               f"Memory: {self.test_metrics.peak_memory_usage_mb:.1f}MB, "
                               f"Detection: {self.test_metrics.peak_detection_rate:.1%}")
                
                time.sleep(self.config.validation_interval_seconds)
                
            except Exception as e:
                logger.error(f"Validation monitoring error: {e}")
                time.sleep(30)
    
    def _wait_for_test_completion(self):
        """Wait for test completion or timeout"""
        start_time = time.time()
        timeout_seconds = self.config.test_duration_minutes * 60
        
        while self.running:
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                logger.info("Test duration timeout reached")
                break
            
            # Check if target leads reached
            if self.test_metrics.total_leads_extracted >= self.config.target_leads:
                logger.info("Target leads reached, test complete")
                break
            
            # Check if all tasks completed
            status = self.orchestrator.get_orchestration_status()
            total_processed = status['task_queue']['completed_tasks'] + status['task_queue']['failed_tasks']
            if total_processed >= self.test_metrics.total_tasks_submitted:
                logger.info("All tasks processed")
                time.sleep(10)  # Allow final processing
                break
            
            time.sleep(5)
    
    def _collect_final_metrics(self):
        """Collect final test metrics"""
        self.test_metrics.end_time = datetime.now()
        
        # Calculate averages
        if self.test_metrics.memory_usage_history:
            self.test_metrics.average_memory_usage_mb = statistics.mean(
                self.test_metrics.memory_usage_history
            )
        
        if self.test_metrics.detection_rate_history:
            self.test_metrics.average_detection_rate = statistics.mean(
                self.test_metrics.detection_rate_history
            )
        
        # Update platform performance
        for task_id in self.task_ids:
            task_status = self.orchestrator.get_task_status(task_id)
            if task_status:
                # This is a simplified approach - in real implementation,
                # you'd track platform-specific metrics more precisely
                pass
        
        logger.info("Final metrics collected")
    
    def _cleanup_test_environment(self):
        """Clean up test environment"""
        self.running = False
        
        # Stop monitoring threads
        for thread in self.monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        # Stop orchestration
        self.orchestrator.stop_orchestration()
        
        logger.info("Test environment cleanup complete")
    
    def _generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("Generating test report")
        
        # Calculate test results
        test_duration = (
            self.test_metrics.end_time - self.test_metrics.start_time
        ).total_seconds() / 60  # Minutes
        
        success_rate = (
            self.test_metrics.total_tasks_completed / 
            max(self.test_metrics.total_tasks_submitted, 1)
        ) * 100
        
        leads_per_minute = self.test_metrics.total_leads_extracted / max(test_duration, 1)
        
        # Determine pass/fail
        test_passed = (
            self.test_metrics.total_leads_extracted >= self.config.target_leads and
            self.test_metrics.peak_memory_usage_mb <= self.config.max_memory_mb and
            self.test_metrics.peak_detection_rate <= self.config.max_detection_rate
        )
        
        # Create report data
        report_data = {
            'test_summary': {
                'test_id': self.test_metrics.test_id,
                'test_passed': test_passed,
                'start_time': self.test_metrics.start_time.isoformat(),
                'end_time': self.test_metrics.end_time.isoformat() if self.test_metrics.end_time else None,
                'duration_minutes': test_duration
            },
            'targets_and_results': {
                'target_leads': self.config.target_leads,
                'actual_leads': self.test_metrics.total_leads_extracted,
                'leads_target_met': self.test_metrics.total_leads_extracted >= self.config.target_leads,
                'memory_limit_mb': self.config.max_memory_mb,
                'peak_memory_mb': self.test_metrics.peak_memory_usage_mb,
                'memory_limit_met': self.test_metrics.peak_memory_usage_mb <= self.config.max_memory_mb,
                'detection_rate_limit': self.config.max_detection_rate,
                'peak_detection_rate': self.test_metrics.peak_detection_rate,
                'detection_rate_met': self.test_metrics.peak_detection_rate <= self.config.max_detection_rate
            },
            'performance_metrics': {
                'total_tasks_submitted': self.test_metrics.total_tasks_submitted,
                'total_tasks_completed': self.test_metrics.total_tasks_completed,
                'total_tasks_failed': self.test_metrics.total_tasks_failed,
                'success_rate_percent': success_rate,
                'leads_per_minute': leads_per_minute,
                'average_memory_usage_mb': self.test_metrics.average_memory_usage_mb,
                'average_detection_rate': self.test_metrics.average_detection_rate
            },
            'platform_performance': self.test_metrics.platform_performance,
            'error_summary': {
                'error_count': len(self.test_metrics.error_messages),
                'error_messages': self.test_metrics.error_messages
            },
            'validation_results': self.validation_results
        }
        
        # Save JSON report
        json_report_path = self.output_dir / f"{self.test_metrics.test_id}_report.json"
        with open(json_report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Save CSV metrics
        self._save_metrics_csv()
        
        # Print summary
        self._print_test_summary(report_data)
        
        logger.info(f"Test report saved: {json_report_path}")
    
    def _save_metrics_csv(self):
        """Save time-series metrics to CSV"""
        csv_path = self.output_dir / f"{self.test_metrics.test_id}_metrics.csv"
        
        # Combine time-series data
        max_length = max(
            len(self.test_metrics.leads_per_minute_history),
            len(self.test_metrics.memory_usage_history),
            len(self.test_metrics.detection_rate_history)
        )
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp_index', 'leads_per_minute', 
                'memory_usage_mb', 'detection_rate'
            ])
            
            for i in range(max_length):
                row = [i]
                
                # Leads per minute
                if i < len(self.test_metrics.leads_per_minute_history):
                    row.append(self.test_metrics.leads_per_minute_history[i])
                else:
                    row.append('')
                
                # Memory usage
                if i < len(self.test_metrics.memory_usage_history):
                    row.append(self.test_metrics.memory_usage_history[i])
                else:
                    row.append('')
                
                # Detection rate
                if i < len(self.test_metrics.detection_rate_history):
                    row.append(self.test_metrics.detection_rate_history[i])
                else:
                    row.append('')
                
                writer.writerow(row)
        
        logger.info(f"Metrics CSV saved: {csv_path}")
    
    def _print_test_summary(self, report_data: Dict[str, Any]):
        """Print test summary to console"""
        summary = report_data['test_summary']
        targets = report_data['targets_and_results']
        performance = report_data['performance_metrics']
        
        print("\n" + "=" * 60)
        print("LOAD TEST SUMMARY")
        print("=" * 60)
        print(f"Test ID: {summary['test_id']}")
        print(f"Test Result: {'PASS' if summary['test_passed'] else 'FAIL'}")
        print(f"Duration: {summary['duration_minutes']:.1f} minutes")
        print()
        
        print("TARGETS vs RESULTS:")
        print(f"  Leads Target: {targets['target_leads']} | Actual: {targets['actual_leads']} | {'✓' if targets['leads_target_met'] else '✗'}")
        print(f"  Memory Limit: {targets['memory_limit_mb']}MB | Peak: {targets['peak_memory_mb']:.1f}MB | {'✓' if targets['memory_limit_met'] else '✗'}")
        print(f"  Detection Limit: {targets['detection_rate_limit']:.1%} | Peak: {targets['peak_detection_rate']:.1%} | {'✓' if targets['detection_rate_met'] else '✗'}")
        print()
        
        print("PERFORMANCE METRICS:")
        print(f"  Success Rate: {performance['success_rate_percent']:.1f}%")
        print(f"  Leads/Minute: {performance['leads_per_minute']:.1f}")
        print(f"  Avg Memory: {performance['average_memory_usage_mb']:.1f}MB")
        print(f"  Avg Detection Rate: {performance['average_detection_rate']:.1%}")
        print()
        
        if report_data['error_summary']['error_count'] > 0:
            print("ERRORS:")
            for error in report_data['error_summary']['error_messages'][:5]:
                print(f"  - {error}")
            print()
        
        print("=" * 60)

def run_comprehensive_load_test() -> LoadTestMetrics:
    """Run a comprehensive load test with default configuration"""
    config = LoadTestConfig(
        target_leads=1000,
        max_memory_mb=2048,
        max_detection_rate=0.05,
        test_duration_minutes=45,
        concurrent_sessions=5,
        platforms=['bing', 'google']
    )
    
    runner = LoadTestRunner(config)
    return runner.run_load_test()

if __name__ == "__main__":
    # Run comprehensive load test
    print("Starting comprehensive load test...")
    
    test_result = run_comprehensive_load_test()
    
    print(f"\nLoad test completed: {test_result.test_id}")
    print(f"Test passed: {'Yes' if test_result.total_leads_extracted >= 1000 else 'No'}")
    print(f"Total leads extracted: {test_result.total_leads_extracted}")
    print(f"Peak memory usage: {test_result.peak_memory_usage_mb:.1f}MB")
    print(f"Peak detection rate: {test_result.peak_detection_rate:.1%}")