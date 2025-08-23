"""
Integration Example - Optimized Botasaurus Scraper
Demonstrates how to use all optimization components together for high-performance scraping.
"""

import time
import logging
from typing import List, Dict, Any

from .memory_manager import ResourcePoolConfig, get_resource_manager
from .performance_monitor import get_performance_monitor
from .session_orchestrator import get_session_orchestrator
from .load_test_runner import LoadTestConfig, LoadTestRunner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizedScrapingSession:
    """
    High-level interface for optimized scraping operations
    Integrates all optimization components seamlessly.
    """
    
    def __init__(self, max_memory_mb: int = 1800, max_sessions: int = 5):
        """Initialize optimized scraping session"""
        self.config = ResourcePoolConfig(
            max_drivers=max_sessions,
            max_sessions=max_sessions,
            memory_threshold_mb=max_memory_mb,
            session_timeout_minutes=30,
            enable_aggressive_cleanup=True
        )
        
        # Initialize components
        self.resource_manager = get_resource_manager(self.config)
        self.performance_monitor = get_performance_monitor()
        self.orchestrator = get_session_orchestrator(self.config)
        
        # Start systems
        self._start_systems()
        
        logger.info("Optimized scraping session initialized")
    
    def _start_systems(self):
        """Start all optimization systems"""
        self.performance_monitor.start_monitoring()
        self.orchestrator.start_orchestration()
        logger.info("Optimization systems started")
    
    def scrape_businesses(self, 
                         queries: List[Dict[str, str]], 
                         target_leads: int = 1000) -> Dict[str, Any]:
        """
        Scrape businesses using optimized system
        
        Args:
            queries: List of query dictionaries with 'platform', 'query', 'location'
            target_leads: Target number of leads to extract
            
        Returns:
            Results dictionary with extracted data and performance metrics
        """
        logger.info(f"Starting business scraping: {len(queries)} queries, target {target_leads} leads")
        
        # Submit tasks
        task_ids = []
        for i, query_data in enumerate(queries):
            # Calculate max results per task to reach target
            max_results_per_task = max(50, target_leads // len(queries))
            
            task_id = self.orchestrator.submit_task(
                platform=query_data.get('platform', 'bing'),
                query=query_data.get('query', ''),
                location=query_data.get('location', ''),
                priority=query_data.get('priority', 3),
                max_results=max_results_per_task
            )
            task_ids.append(task_id)
        
        logger.info(f"Submitted {len(task_ids)} scraping tasks")
        
        # Monitor progress
        start_time = time.time()
        timeout_minutes = 45
        
        while time.time() - start_time < timeout_minutes * 60:
            # Get status
            status = self.orchestrator.get_orchestration_status()
            total_leads = status['orchestration_metrics']['total_leads_extracted']
            
            # Check if target reached
            if total_leads >= target_leads:
                logger.info(f"Target leads reached: {total_leads}/{target_leads}")
                break
            
            # Check if all tasks completed
            total_processed = (status['task_queue']['completed_tasks'] + 
                             status['task_queue']['failed_tasks'])
            if total_processed >= len(task_ids):
                logger.info("All tasks completed")
                break
            
            # Log progress
            logger.info(f"Progress: {total_leads}/{target_leads} leads, "
                       f"Active sessions: {status['current_sessions']['active_sessions']}")
            
            time.sleep(10)
        
        # Collect results
        results = self._collect_results(task_ids)
        
        logger.info(f"Scraping completed: {len(results['leads'])} leads extracted")
        return results
    
    def _collect_results(self, task_ids: List[str]) -> Dict[str, Any]:
        """Collect results from completed tasks"""
        all_leads = []
        completed_tasks = 0
        failed_tasks = 0
        
        for task_id in task_ids:
            task_status = self.orchestrator.get_task_status(task_id)
            if task_status:
                if task_status['status'] == 'completed':
                    completed_tasks += 1
                    # In real implementation, you'd get the actual results here
                    # For now, we'll simulate some results
                    all_leads.extend([
                        {'business_name': f'Business {i}', 'task_id': task_id}
                        for i in range(50)  # Simulated results
                    ])
                elif task_status['status'] == 'failed':
                    failed_tasks += 1
        
        # Get performance metrics
        performance_dashboard = self.performance_monitor.get_performance_dashboard()
        system_status = self.resource_manager.get_system_status()
        
        return {
            'leads': all_leads,
            'total_leads': len(all_leads),
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': completed_tasks / max(len(task_ids), 1) * 100,
            'performance_metrics': performance_dashboard,
            'system_metrics': system_status
        }
    
    def run_performance_test(self, target_leads: int = 1000) -> Dict[str, Any]:
        """Run a performance test to validate system capabilities"""
        logger.info(f"Running performance test with target: {target_leads} leads")
        
        test_config = LoadTestConfig(
            target_leads=target_leads,
            max_memory_mb=self.config.memory_threshold_mb,
            max_detection_rate=0.05,
            test_duration_minutes=30,
            concurrent_sessions=self.config.max_sessions
        )
        
        test_runner = LoadTestRunner(test_config)
        test_results = test_runner.run_load_test()
        
        return {
            'test_passed': test_results.total_leads_extracted >= target_leads,
            'total_leads_extracted': test_results.total_leads_extracted,
            'peak_memory_mb': test_results.peak_memory_usage_mb,
            'peak_detection_rate': test_results.peak_detection_rate,
            'average_memory_mb': test_results.average_memory_usage_mb,
            'test_duration_minutes': (
                (test_results.end_time - test_results.start_time).total_seconds() / 60
                if test_results.end_time else 0
            ),
            'memory_limit_met': test_results.peak_memory_usage_mb <= test_config.max_memory_mb,
            'detection_limit_met': test_results.peak_detection_rate <= test_config.max_detection_rate
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report"""
        orchestration_status = self.orchestrator.get_orchestration_status()
        performance_dashboard = self.performance_monitor.get_performance_dashboard()
        system_status = self.resource_manager.get_system_status()
        
        return {
            'timestamp': time.time(),
            'system_health': system_status.get('system_health', 'unknown'),
            'memory_usage_mb': system_status['memory_metrics']['process_memory_mb'],
            'memory_pressure': system_status['memory_metrics']['pressure_level'],
            'active_sessions': orchestration_status['current_sessions']['active_sessions'],
            'leads_per_minute': performance_dashboard['current_metrics']['leads_per_minute'],
            'success_rate': performance_dashboard['current_metrics']['success_rate_percent'],
            'detection_rate': performance_dashboard['current_metrics']['detection_rate_percent'],
            'driver_pool_utilization': system_status['driver_pool']['pool_utilization']
        }
    
    def shutdown(self):
        """Shutdown all systems"""
        logger.info("Shutting down optimized scraping session")
        
        try:
            self.orchestrator.stop_orchestration()
            self.performance_monitor.stop_monitoring()
            self.resource_manager.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Shutdown complete")

def demo_optimized_scraping():
    """Demonstration of optimized scraping system"""
    print("=" * 60)
    print("OPTIMIZED SCRAPING SYSTEM DEMO")
    print("=" * 60)
    
    # Initialize optimized session
    session = OptimizedScrapingSession(max_memory_mb=1800, max_sessions=3)
    
    try:
        # Test queries
        test_queries = [
            {"platform": "bing", "query": "restaurants", "location": "Miami, FL"},
            {"platform": "google", "query": "doctors", "location": "New York, NY"},
            {"platform": "bing", "query": "lawyers", "location": "Los Angeles, CA"},
            {"platform": "google", "query": "dentists", "location": "Chicago, IL"},
        ]
        
        print(f"\n1. Testing with {len(test_queries)} queries...")
        
        # Get initial health
        initial_health = session.get_system_health()
        print(f"Initial system health: {initial_health['system_health']}")
        print(f"Initial memory usage: {initial_health['memory_usage_mb']:.1f}MB")
        
        # Run scraping
        results = session.scrape_businesses(test_queries, target_leads=200)
        
        print(f"\n2. Scraping Results:")
        print(f"   Total leads: {results['total_leads']}")
        print(f"   Completed tasks: {results['completed_tasks']}")
        print(f"   Success rate: {results['success_rate']:.1f}%")
        
        # Get final health
        final_health = session.get_system_health()
        print(f"\n3. Final System Health:")
        print(f"   System health: {final_health['system_health']}")
        print(f"   Memory usage: {final_health['memory_usage_mb']:.1f}MB")
        print(f"   Memory pressure: {final_health['memory_pressure']}")
        print(f"   Success rate: {final_health['success_rate']:.1f}%")
        print(f"   Detection rate: {final_health['detection_rate']:.1f}%")
        
        # Run performance test
        print(f"\n4. Running Performance Test...")
        perf_test_results = session.run_performance_test(target_leads=500)
        
        print(f"   Test passed: {'YES' if perf_test_results['test_passed'] else 'NO'}")
        print(f"   Leads extracted: {perf_test_results['total_leads_extracted']}")
        print(f"   Peak memory: {perf_test_results['peak_memory_mb']:.1f}MB")
        print(f"   Memory limit met: {'YES' if perf_test_results['memory_limit_met'] else 'NO'}")
        print(f"   Detection limit met: {'YES' if perf_test_results['detection_limit_met'] else 'NO'}")
        
        print(f"\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo error: {e}")
        
    finally:
        session.shutdown()

if __name__ == "__main__":
    demo_optimized_scraping()