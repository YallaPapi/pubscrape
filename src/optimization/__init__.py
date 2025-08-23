"""
Optimization Package - Performance and Resource Management
Provides comprehensive optimization tools for high-performance scraping operations.
"""

from .memory_manager import (
    MemoryMonitor,
    BrowserDriverPool, 
    MemoryOptimizer,
    ResourceManager,
    ResourcePoolConfig,
    get_resource_manager,
    shutdown_resource_manager
)

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetric,
    MetricType,
    SessionMetrics,
    get_performance_monitor
)

from .session_orchestrator import (
    SessionOrchestrator,
    ScrapingTask,
    SessionInfo,
    SessionState,
    LoadBalancer,
    get_session_orchestrator,
    shutdown_session_orchestrator
)

from .load_test_runner import (
    LoadTestRunner,
    LoadTestConfig,
    LoadTestMetrics,
    run_comprehensive_load_test
)

__all__ = [
    # Memory Management
    'MemoryMonitor',
    'BrowserDriverPool',
    'MemoryOptimizer', 
    'ResourceManager',
    'ResourcePoolConfig',
    'get_resource_manager',
    'shutdown_resource_manager',
    
    # Performance Monitoring
    'PerformanceMonitor',
    'PerformanceMetric',
    'MetricType',
    'SessionMetrics',
    'get_performance_monitor',
    
    # Session Orchestration
    'SessionOrchestrator',
    'ScrapingTask',
    'SessionInfo',
    'SessionState',
    'LoadBalancer',
    'get_session_orchestrator',
    'shutdown_session_orchestrator',
    
    # Load Testing
    'LoadTestRunner',
    'LoadTestConfig',
    'LoadTestMetrics',
    'run_comprehensive_load_test'
]

# Package version
__version__ = "1.0.0"