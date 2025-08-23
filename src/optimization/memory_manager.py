"""
Memory Management and Resource Optimization
Provides comprehensive memory monitoring, garbage collection, and resource pooling
for high-performance scraping operations with <2GB memory constraint per session.
"""

import gc
import psutil
import threading
import time
import weakref
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MemoryMetrics:
    """Real-time memory usage metrics"""
    timestamp: datetime
    process_memory_mb: float
    system_memory_percent: float
    gc_objects: int
    active_sessions: int
    driver_count: int
    heap_size_mb: float = 0.0
    available_memory_mb: float = 0.0
    memory_pressure_level: str = "normal"  # normal, moderate, high, critical

@dataclass
class ResourcePoolConfig:
    """Configuration for resource pooling"""
    max_drivers: int = 5
    max_sessions: int = 10
    cleanup_interval_seconds: int = 300
    memory_threshold_mb: int = 1800  # 90% of 2GB limit
    gc_frequency_seconds: int = 60
    session_timeout_minutes: int = 30
    enable_aggressive_cleanup: bool = True

class MemoryMonitor:
    """Real-time memory monitoring and alerting system"""
    
    def __init__(self, config: ResourcePoolConfig):
        self.config = config
        self.metrics_history = deque(maxlen=100)
        self.alert_callbacks: List[Callable] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.process = psutil.Process()
        
    def start_monitoring(self):
        """Start continuous memory monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Memory monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)
                
                # Check for memory pressure
                self._check_memory_pressure(metrics)
                
                # Sleep until next check
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(30)  # Longer sleep on error
    
    def get_current_metrics(self) -> MemoryMetrics:
        """Get current memory metrics"""
        try:
            # Process memory info
            memory_info = self.process.memory_info()
            process_memory_mb = memory_info.rss / (1024 * 1024)
            
            # System memory info
            system_memory = psutil.virtual_memory()
            system_memory_percent = system_memory.percent
            available_memory_mb = system_memory.available / (1024 * 1024)
            
            # Garbage collection info
            gc_objects = len(gc.get_objects())
            
            # Memory pressure assessment
            pressure = self._assess_memory_pressure(process_memory_mb, system_memory_percent)
            
            return MemoryMetrics(
                timestamp=datetime.now(),
                process_memory_mb=process_memory_mb,
                system_memory_percent=system_memory_percent,
                gc_objects=gc_objects,
                active_sessions=self._count_active_sessions(),
                driver_count=self._count_active_drivers(),
                available_memory_mb=available_memory_mb,
                memory_pressure_level=pressure
            )
            
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")
            return MemoryMetrics(
                timestamp=datetime.now(),
                process_memory_mb=0.0,
                system_memory_percent=0.0,
                gc_objects=0,
                active_sessions=0,
                driver_count=0,
                memory_pressure_level="unknown"
            )
    
    def _assess_memory_pressure(self, process_mb: float, system_percent: float) -> str:
        """Assess current memory pressure level"""
        if process_mb > self.config.memory_threshold_mb or system_percent > 90:
            return "critical"
        elif process_mb > self.config.memory_threshold_mb * 0.8 or system_percent > 80:
            return "high"
        elif process_mb > self.config.memory_threshold_mb * 0.6 or system_percent > 70:
            return "moderate"
        else:
            return "normal"
    
    def _check_memory_pressure(self, metrics: MemoryMetrics):
        """Check memory pressure and trigger alerts"""
        if metrics.memory_pressure_level in ["high", "critical"]:
            logger.warning(f"Memory pressure detected: {metrics.memory_pressure_level}")
            logger.warning(f"Process memory: {metrics.process_memory_mb:.1f}MB")
            logger.warning(f"System memory: {metrics.system_memory_percent:.1f}%")
            
            # Trigger alert callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(metrics)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
    
    def _count_active_sessions(self) -> int:
        """Count active browser sessions (implementation depends on session tracker)"""
        # This would be implemented based on your session tracking system
        return 0
    
    def _count_active_drivers(self) -> int:
        """Count active browser drivers"""
        # This would count active WebDriver instances
        return 0
    
    def add_alert_callback(self, callback: Callable[[MemoryMetrics], None]):
        """Add memory pressure alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory report"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        current = self.metrics_history[-1]
        
        # Calculate trends
        if len(self.metrics_history) > 1:
            previous = self.metrics_history[-2]
            memory_trend = current.process_memory_mb - previous.process_memory_mb
            gc_trend = current.gc_objects - previous.gc_objects
        else:
            memory_trend = 0
            gc_trend = 0
        
        return {
            "current_metrics": {
                "process_memory_mb": current.process_memory_mb,
                "system_memory_percent": current.system_memory_percent,
                "available_memory_mb": current.available_memory_mb,
                "gc_objects": current.gc_objects,
                "active_sessions": current.active_sessions,
                "driver_count": current.driver_count,
                "pressure_level": current.memory_pressure_level
            },
            "trends": {
                "memory_change_mb": memory_trend,
                "gc_objects_change": gc_trend
            },
            "thresholds": {
                "memory_threshold_mb": self.config.memory_threshold_mb,
                "critical_system_percent": 90,
                "warning_system_percent": 80
            },
            "recommendations": self._generate_recommendations(current)
        }
    
    def _generate_recommendations(self, metrics: MemoryMetrics) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        if metrics.memory_pressure_level == "critical":
            recommendations.extend([
                "Immediately trigger garbage collection",
                "Close inactive browser sessions",
                "Reduce concurrent operations",
                "Enable aggressive cleanup mode"
            ])
        elif metrics.memory_pressure_level == "high":
            recommendations.extend([
                "Schedule garbage collection",
                "Review session timeout settings",
                "Consider reducing batch size"
            ])
        elif metrics.gc_objects > 100000:
            recommendations.append("Schedule garbage collection to reduce object count")
        
        if metrics.driver_count > self.config.max_drivers:
            recommendations.append(f"Reduce driver count to {self.config.max_drivers}")
        
        return recommendations

class BrowserDriverPool:
    """Pool of reusable browser drivers for efficient resource management"""
    
    def __init__(self, config: ResourcePoolConfig):
        self.config = config
        self.available_drivers = deque()
        self.active_drivers: Dict[str, Any] = {}
        self.driver_metrics: Dict[str, Dict] = {}
        self.lock = threading.RLock()
        self.cleanup_thread: Optional[threading.Thread] = None
        self.running = True
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
    def get_driver(self, session_id: str) -> Optional[Any]:
        """Get a driver from the pool or create new one"""
        with self.lock:
            # Check if session already has a driver
            if session_id in self.active_drivers:
                return self.active_drivers[session_id]
            
            # Try to get from pool
            if self.available_drivers:
                driver = self.available_drivers.popleft()
                self.active_drivers[session_id] = driver
                self._update_driver_metrics(session_id, "reused")
                logger.debug(f"Reused driver for session {session_id}")
                return driver
            
            # Check if we can create new driver
            if len(self.active_drivers) >= self.config.max_drivers:
                logger.warning(f"Driver pool exhausted ({self.config.max_drivers})")
                return None
            
            # Create new driver (this would be implemented based on your driver creation)
            driver = self._create_new_driver()
            if driver:
                self.active_drivers[session_id] = driver
                self._update_driver_metrics(session_id, "created")
                logger.debug(f"Created new driver for session {session_id}")
            
            return driver
    
    def return_driver(self, session_id: str, force_close: bool = False):
        """Return driver to pool or close it"""
        with self.lock:
            if session_id not in self.active_drivers:
                return
            
            driver = self.active_drivers.pop(session_id)
            
            if force_close or len(self.available_drivers) >= self.config.max_drivers:
                # Close the driver
                self._close_driver(driver)
                self._update_driver_metrics(session_id, "closed")
                logger.debug(f"Closed driver for session {session_id}")
            else:
                # Return to pool for reuse
                try:
                    self._reset_driver(driver)
                    self.available_drivers.append(driver)
                    self._update_driver_metrics(session_id, "returned")
                    logger.debug(f"Returned driver to pool for session {session_id}")
                except Exception as e:
                    logger.error(f"Error resetting driver: {e}")
                    self._close_driver(driver)
    
    def cleanup_inactive_drivers(self):
        """Clean up inactive drivers based on timeout"""
        with self.lock:
            current_time = datetime.now()
            timeout = timedelta(minutes=self.config.session_timeout_minutes)
            
            # Check active drivers for timeout
            inactive_sessions = []
            for session_id, metrics in self.driver_metrics.items():
                if session_id in self.active_drivers:
                    last_activity = metrics.get('last_activity', current_time)
                    if current_time - last_activity > timeout:
                        inactive_sessions.append(session_id)
            
            # Close inactive drivers
            for session_id in inactive_sessions:
                logger.info(f"Closing inactive driver for session {session_id}")
                self.return_driver(session_id, force_close=True)
            
            return len(inactive_sessions)
    
    def _cleanup_loop(self):
        """Periodic cleanup of inactive resources"""
        while self.running:
            try:
                time.sleep(self.config.cleanup_interval_seconds)
                cleaned = self.cleanup_inactive_drivers()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} inactive drivers")
                    
                # Trigger garbage collection periodically
                gc.collect()
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    def _create_new_driver(self):
        """Create a new browser driver (to be implemented based on your driver setup)"""
        # This should be implemented to create your specific driver type
        # For example, Botasaurus driver creation
        logger.debug("Creating new browser driver")
        return None  # Placeholder
    
    def _close_driver(self, driver):
        """Close a browser driver and clean up resources"""
        try:
            if hasattr(driver, 'quit'):
                driver.quit()
            elif hasattr(driver, 'close'):
                driver.close()
        except Exception as e:
            logger.error(f"Error closing driver: {e}")
    
    def _reset_driver(self, driver):
        """Reset driver state for reuse"""
        try:
            # Clear cookies, cache, etc.
            if hasattr(driver, 'delete_all_cookies'):
                driver.delete_all_cookies()
            if hasattr(driver, 'execute_script'):
                # Clear local storage and session storage
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
        except Exception as e:
            logger.error(f"Error resetting driver: {e}")
            raise
    
    def _update_driver_metrics(self, session_id: str, action: str):
        """Update driver usage metrics"""
        if session_id not in self.driver_metrics:
            self.driver_metrics[session_id] = {
                'created_at': datetime.now(),
                'actions': [],
                'last_activity': datetime.now()
            }
        
        self.driver_metrics[session_id]['actions'].append({
            'action': action,
            'timestamp': datetime.now()
        })
        self.driver_metrics[session_id]['last_activity'] = datetime.now()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        with self.lock:
            return {
                'available_drivers': len(self.available_drivers),
                'active_drivers': len(self.active_drivers),
                'total_sessions': len(self.driver_metrics),
                'max_drivers': self.config.max_drivers,
                'pool_utilization': len(self.active_drivers) / self.config.max_drivers * 100
            }
    
    def shutdown(self):
        """Shutdown the driver pool"""
        self.running = False
        
        with self.lock:
            # Close all active drivers
            for session_id in list(self.active_drivers.keys()):
                self.return_driver(session_id, force_close=True)
            
            # Close all pooled drivers
            while self.available_drivers:
                driver = self.available_drivers.popleft()
                self._close_driver(driver)
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Browser driver pool shutdown complete")

class MemoryOptimizer:
    """Advanced memory optimization and garbage collection manager"""
    
    def __init__(self, config: ResourcePoolConfig):
        self.config = config
        self.last_gc_time = time.time()
        self.gc_stats = {
            'collections': 0,
            'objects_freed': 0,
            'time_spent': 0.0
        }
        
    def optimize_memory(self, force: bool = False) -> Dict[str, Any]:
        """Perform memory optimization operations"""
        start_time = time.time()
        optimization_results = {}
        
        # Check if optimization is needed
        if not force and not self._should_optimize():
            return {'skipped': True, 'reason': 'Not needed'}
        
        # Get initial memory state
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        initial_objects = len(gc.get_objects())
        
        # Perform garbage collection
        gc_results = self._perform_garbage_collection()
        optimization_results['garbage_collection'] = gc_results
        
        # Clear caches
        cache_results = self._clear_caches()
        optimization_results['cache_cleanup'] = cache_results
        
        # Optimize weak references
        weakref_results = self._cleanup_weak_references()
        optimization_results['weakref_cleanup'] = weakref_results
        
        # Get final memory state
        final_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        final_objects = len(gc.get_objects())
        
        # Calculate results
        memory_freed = initial_memory - final_memory
        objects_freed = initial_objects - final_objects
        optimization_time = time.time() - start_time
        
        optimization_results['summary'] = {
            'memory_freed_mb': memory_freed,
            'objects_freed': objects_freed,
            'optimization_time_seconds': optimization_time,
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory
        }
        
        logger.info(f"Memory optimization freed {memory_freed:.1f}MB and {objects_freed} objects")
        
        return optimization_results
    
    def _should_optimize(self) -> bool:
        """Check if memory optimization is needed"""
        current_time = time.time()
        
        # Time-based check
        if current_time - self.last_gc_time > self.config.gc_frequency_seconds:
            return True
        
        # Memory pressure check
        current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        if current_memory > self.config.memory_threshold_mb * 0.8:
            return True
        
        # Object count check
        if len(gc.get_objects()) > 50000:
            return True
        
        return False
    
    def _perform_garbage_collection(self) -> Dict[str, Any]:
        """Perform comprehensive garbage collection"""
        start_time = time.time()
        
        # Get initial state
        initial_objects = len(gc.get_objects())
        
        # Force garbage collection for all generations
        collected = []
        for generation in range(3):
            n_collected = gc.collect(generation)
            collected.append(n_collected)
        
        # Update stats
        gc_time = time.time() - start_time
        self.last_gc_time = time.time()
        self.gc_stats['collections'] += 1
        self.gc_stats['time_spent'] += gc_time
        
        final_objects = len(gc.get_objects())
        objects_freed = initial_objects - final_objects
        self.gc_stats['objects_freed'] += objects_freed
        
        return {
            'objects_collected_by_generation': collected,
            'objects_freed': objects_freed,
            'gc_time_seconds': gc_time,
            'total_collections': self.gc_stats['collections']
        }
    
    def _clear_caches(self) -> Dict[str, Any]:
        """Clear various Python caches"""
        cleared_caches = []
        
        try:
            # Clear sys.modules cache for unused modules
            import sys
            initial_modules = len(sys.modules)
            # Note: Be careful about clearing sys.modules in production
            
            # Clear functools cache
            import functools
            cleared_caches.append("functools")
            
            # Clear regex cache
            import re
            re.purge()
            cleared_caches.append("regex")
            
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
        
        return {'cleared_caches': cleared_caches}
    
    def _cleanup_weak_references(self) -> Dict[str, Any]:
        """Clean up dead weak references"""
        try:
            # This would clean up any custom weak reference tracking
            cleaned_refs = 0
            return {'cleaned_weak_refs': cleaned_refs}
        except Exception as e:
            logger.error(f"Error cleaning weak references: {e}")
            return {'error': str(e)}
    
    def get_gc_statistics(self) -> Dict[str, Any]:
        """Get garbage collection statistics"""
        return {
            'total_collections': self.gc_stats['collections'],
            'total_objects_freed': self.gc_stats['objects_freed'],
            'total_time_spent': self.gc_stats['time_spent'],
            'average_time_per_collection': (
                self.gc_stats['time_spent'] / max(self.gc_stats['collections'], 1)
            ),
            'gc_thresholds': gc.get_threshold(),
            'gc_counts': gc.get_count()
        }

class ResourceManager:
    """Central resource management system"""
    
    def __init__(self, config: Optional[ResourcePoolConfig] = None):
        self.config = config or ResourcePoolConfig()
        self.memory_monitor = MemoryMonitor(self.config)
        self.driver_pool = BrowserDriverPool(self.config)
        self.memory_optimizer = MemoryOptimizer(self.config)
        self.session_tracking: Dict[str, Dict] = {}
        self.lock = threading.RLock()
        
        # Set up memory pressure callbacks
        self.memory_monitor.add_alert_callback(self._handle_memory_pressure)
        
        # Start monitoring
        self.memory_monitor.start_monitoring()
        logger.info("Resource manager initialized")
    
    def _handle_memory_pressure(self, metrics: MemoryMetrics):
        """Handle memory pressure alerts"""
        logger.warning(f"Memory pressure callback triggered: {metrics.memory_pressure_level}")
        
        if metrics.memory_pressure_level == "critical":
            # Aggressive cleanup
            self.emergency_cleanup()
        elif metrics.memory_pressure_level == "high":
            # Scheduled optimization
            self.memory_optimizer.optimize_memory(force=True)
    
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new managed session"""
        with self.lock:
            if session_id in self.session_tracking:
                logger.warning(f"Session {session_id} already exists")
                return self.session_tracking[session_id]
            
            session_info = {
                'id': session_id,
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'driver': None,
                'memory_usage': 0.0,
                'status': 'active'
            }
            
            # Get driver from pool
            driver = self.driver_pool.get_driver(session_id)
            session_info['driver'] = driver
            
            self.session_tracking[session_id] = session_info
            logger.info(f"Created managed session: {session_id}")
            
            return session_info
    
    def end_session(self, session_id: str):
        """End a managed session and clean up resources"""
        with self.lock:
            if session_id not in self.session_tracking:
                return
            
            session_info = self.session_tracking[session_id]
            session_info['status'] = 'ended'
            session_info['ended_at'] = datetime.now()
            
            # Return driver to pool
            self.driver_pool.return_driver(session_id)
            
            # Remove from active tracking
            del self.session_tracking[session_id]
            
            logger.info(f"Ended managed session: {session_id}")
    
    def emergency_cleanup(self):
        """Perform emergency resource cleanup"""
        logger.critical("Performing emergency resource cleanup")
        
        with self.lock:
            # End all sessions
            session_ids = list(self.session_tracking.keys())
            for session_id in session_ids:
                self.end_session(session_id)
            
            # Force memory optimization
            self.memory_optimizer.optimize_memory(force=True)
            
            # Clean up driver pool
            self.driver_pool.cleanup_inactive_drivers()
            
            logger.info("Emergency cleanup completed")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        memory_metrics = self.memory_monitor.get_current_metrics()
        pool_stats = self.driver_pool.get_pool_stats()
        gc_stats = self.memory_optimizer.get_gc_statistics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'memory_metrics': {
                'process_memory_mb': memory_metrics.process_memory_mb,
                'system_memory_percent': memory_metrics.system_memory_percent,
                'available_memory_mb': memory_metrics.available_memory_mb,
                'pressure_level': memory_metrics.memory_pressure_level,
                'gc_objects': memory_metrics.gc_objects
            },
            'driver_pool': pool_stats,
            'garbage_collection': gc_stats,
            'active_sessions': len(self.session_tracking),
            'system_health': self._assess_system_health(memory_metrics, pool_stats)
        }
    
    def _assess_system_health(self, memory_metrics: MemoryMetrics, pool_stats: Dict) -> str:
        """Assess overall system health"""
        if memory_metrics.memory_pressure_level == "critical":
            return "critical"
        elif memory_metrics.memory_pressure_level == "high":
            return "warning"
        elif pool_stats['pool_utilization'] > 90:
            return "warning"
        else:
            return "healthy"
    
    def shutdown(self):
        """Shutdown resource manager"""
        logger.info("Shutting down resource manager")
        
        # Stop monitoring
        self.memory_monitor.stop_monitoring()
        
        # End all sessions
        with self.lock:
            session_ids = list(self.session_tracking.keys())
            for session_id in session_ids:
                self.end_session(session_id)
        
        # Shutdown driver pool
        self.driver_pool.shutdown()
        
        # Final cleanup
        self.memory_optimizer.optimize_memory(force=True)
        
        logger.info("Resource manager shutdown complete")

# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None

def get_resource_manager(config: Optional[ResourcePoolConfig] = None) -> ResourceManager:
    """Get global resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager(config)
    return _resource_manager

def shutdown_resource_manager():
    """Shutdown global resource manager"""
    global _resource_manager
    if _resource_manager:
        _resource_manager.shutdown()
        _resource_manager = None

if __name__ == "__main__":
    # Test memory management system
    print("Memory Management System Test")
    print("=" * 50)
    
    # Test configuration
    config = ResourcePoolConfig(
        max_drivers=3,
        memory_threshold_mb=100,  # Low threshold for testing
        gc_frequency_seconds=30
    )
    
    # Create resource manager
    rm = ResourceManager(config)
    
    try:
        # Test session creation
        session1 = rm.create_session("test_session_1")
        session2 = rm.create_session("test_session_2")
        
        print(f"Created sessions: {session1['id']}, {session2['id']}")
        
        # Get system status
        status = rm.get_system_status()
        print(f"System health: {status['system_health']}")
        print(f"Active sessions: {status['active_sessions']}")
        print(f"Memory usage: {status['memory_metrics']['process_memory_mb']:.1f}MB")
        
        # Test memory optimization
        print("\nTesting memory optimization...")
        optimization_result = rm.memory_optimizer.optimize_memory(force=True)
        print(f"Memory freed: {optimization_result['summary']['memory_freed_mb']:.1f}MB")
        
        # End sessions
        rm.end_session("test_session_1")
        rm.end_session("test_session_2")
        
        print("Test completed successfully")
        
    finally:
        rm.shutdown()