# Botasaurus Performance Optimization System

A comprehensive performance and resource management system for high-volume web scraping operations with the Botasaurus framework.

## 🎯 System Requirements & Goals

- **Process 1000+ business leads efficiently**
- **Maintain <2GB memory usage per session**
- **Keep detection rate <5%**
- **Support 5+ concurrent browser sessions**
- **Achieve 50+ leads per minute throughput**

## 🏗️ Architecture Overview

The optimization system consists of four main components:

### 1. Memory Manager (`memory_manager.py`)
- **Real-time Memory Monitoring**: Tracks process and system memory usage
- **Browser Driver Pool**: Reusable driver instances for efficient resource management
- **Automatic Garbage Collection**: Intelligent cleanup based on memory pressure
- **Resource Allocation**: Dynamic allocation based on available memory

```python
from src.optimization import get_resource_manager, ResourcePoolConfig

# Configure resource limits
config = ResourcePoolConfig(
    max_drivers=5,
    max_sessions=10,
    memory_threshold_mb=1800,  # 90% of 2GB limit
    session_timeout_minutes=30,
    enable_aggressive_cleanup=True
)

# Get global resource manager
resource_manager = get_resource_manager(config)
```

### 2. Performance Monitor (`performance_monitor.py`)
- **Throughput Tracking**: Leads per minute, requests per second
- **Success Rate Monitoring**: Track extraction success/failure rates
- **Detection Rate Tracking**: Monitor bot detection attempts
- **Real-time Alerts**: Automatic alerts for performance degradation

```python
from src.optimization import get_performance_monitor

# Get global performance monitor
perf_monitor = get_performance_monitor()
perf_monitor.start_monitoring()

# Track session performance
session = perf_monitor.create_session("session_1", "bing", "restaurants", "Miami")
perf_monitor.track_leads_extracted("session_1", 25)
perf_monitor.track_request_result("session_1", success=True, response_time=1.5)
```

### 3. Session Orchestrator (`session_orchestrator.py`)
- **Intelligent Load Balancing**: Distribute tasks across sessions optimally
- **Parallel Processing**: Handle multiple scraping operations simultaneously
- **Session Health Monitoring**: Automatically replace unhealthy sessions
- **Task Queue Management**: Priority-based task scheduling

```python
from src.optimization import get_session_orchestrator

# Get global orchestrator
orchestrator = get_session_orchestrator()
orchestrator.start_orchestration()

# Submit scraping tasks
task_id = orchestrator.submit_task(
    platform="bing",
    query="restaurants",
    location="Miami, FL",
    priority=3,
    max_results=500
)

# Check task status
status = orchestrator.get_task_status(task_id)
```

### 4. Load Test Runner (`load_test_runner.py`)
- **Comprehensive Testing**: Validate system under various loads
- **Memory Constraint Testing**: Ensure <2GB memory usage
- **Detection Rate Validation**: Verify <5% detection rate
- **Performance Benchmarking**: Measure throughput and reliability

```python
from src.optimization import LoadTestRunner, LoadTestConfig

# Configure load test
config = LoadTestConfig(
    target_leads=1000,
    max_memory_mb=2048,
    max_detection_rate=0.05,
    test_duration_minutes=30,
    concurrent_sessions=5
)

# Run test
runner = LoadTestRunner(config)
results = runner.run_load_test()
```

## 🚀 Quick Start Guide

### 1. Basic Usage

```python
from src.optimization.integration_example import OptimizedScrapingSession

# Initialize optimized session
session = OptimizedScrapingSession(max_memory_mb=1800, max_sessions=5)

# Define scraping queries
queries = [
    {"platform": "bing", "query": "restaurants", "location": "Miami, FL"},
    {"platform": "google", "query": "doctors", "location": "New York, NY"},
]

# Execute scraping with optimization
results = session.scrape_businesses(queries, target_leads=1000)

print(f"Extracted {results['total_leads']} leads")
print(f"Success rate: {results['success_rate']:.1f}%")

# Cleanup
session.shutdown()
```

### 2. Performance Testing

```python
# Run comprehensive performance validation
python scripts/run_performance_validation.py

# Or run quick validation for CI
python scripts/run_performance_validation.py --quick
```

### 3. System Health Monitoring

```python
# Get real-time system health
health = session.get_system_health()

print(f"System Health: {health['system_health']}")
print(f"Memory Usage: {health['memory_usage_mb']:.1f}MB")
print(f"Active Sessions: {health['active_sessions']}")
print(f"Success Rate: {health['success_rate']:.1f}%")
print(f"Detection Rate: {health['detection_rate']:.1f}%")
```

## 📊 Performance Metrics

### Key Performance Indicators (KPIs)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Throughput** | 50+ leads/min | Real-time tracking |
| **Memory Usage** | <2GB per session | Continuous monitoring |
| **Detection Rate** | <5% | Per-request tracking |
| **Success Rate** | >95% | Task completion rate |
| **Response Time** | <3s average | Request timing |

### Memory Optimization Features

- **Automatic Garbage Collection**: Triggered based on memory pressure
- **Driver Pool Reuse**: Minimize resource allocation overhead  
- **Session Isolation**: Prevent memory leaks between operations
- **Cache Management**: Intelligent cache clearing and optimization
- **Resource Monitoring**: Real-time memory usage tracking

### Anti-Detection Optimizations

- **Stealth Level Adjustment**: Automatic stealth level increases on detection
- **Proxy Rotation**: Health-based proxy selection and rotation  
- **User Agent Cycling**: Diverse browser fingerprints
- **Behavioral Patterns**: Human-like interaction simulation
- **Detection Monitoring**: Real-time detection rate tracking

## 🧪 Testing & Validation

### Test Suites

1. **Memory Constraint Test**: Validates <2GB memory usage with 1000+ leads
2. **High Volume Stress Test**: Tests system with 2000+ leads  
3. **Endurance Test**: Long-running operations (60+ minutes)
4. **Detection Rate Test**: Ensures <5% detection rate
5. **Concurrent Processing Test**: Validates parallel session handling

### Running Tests

```bash
# Full validation suite (recommended)
python scripts/run_performance_validation.py

# Quick validation (10 minutes)
python scripts/run_performance_validation.py --quick

# Load test with custom configuration
python -c "from src.optimization import run_comprehensive_load_test; run_comprehensive_load_test()"
```

### Test Results Interpretation

```json
{
  "overall_result": "PASSED",
  "tests": {
    "memory_constraint": {
      "passed": true,
      "actual_leads": 1250,
      "peak_memory_mb": 1847.2,
      "peak_detection_rate": 0.032
    }
  }
}
```

## ⚙️ Configuration Options

### Resource Pool Configuration

```python
ResourcePoolConfig(
    max_drivers=5,           # Maximum browser drivers
    max_sessions=10,         # Maximum active sessions  
    cleanup_interval_seconds=300,  # Cleanup frequency
    memory_threshold_mb=1800,      # Memory pressure threshold
    gc_frequency_seconds=60,       # Garbage collection frequency
    session_timeout_minutes=30,    # Session timeout
    enable_aggressive_cleanup=True # Enable aggressive memory cleanup
)
```

### Load Test Configuration

```python
LoadTestConfig(
    target_leads=1000,              # Target lead count
    max_memory_mb=2048,            # Memory limit
    max_detection_rate=0.05,       # Detection rate limit (5%)
    test_duration_minutes=60,      # Test timeout
    concurrent_sessions=5,         # Parallel sessions
    platforms=['bing', 'google'], # Target platforms
    validation_interval_seconds=10 # Health check frequency
)
```

## 🔧 Advanced Configuration

### Custom Performance Callbacks

```python
def memory_alert_callback(metrics):
    if metrics.memory_pressure_level == "critical":
        # Implement custom memory management
        trigger_emergency_cleanup()

# Add callback to memory monitor
memory_monitor = get_resource_manager().memory_monitor
memory_monitor.add_alert_callback(memory_alert_callback)
```

### Custom Load Balancing

```python
class CustomLoadBalancer(LoadBalancer):
    def _calculate_session_score(self, task, session):
        # Implement custom scoring logic
        score = super()._calculate_session_score(task, session)
        
        # Add custom factors
        if task.priority >= 4:  # High priority
            score += 0.5
        
        return score
```

## 🐛 Troubleshooting

### Common Issues

**High Memory Usage**
```python
# Check memory metrics
health = session.get_system_health()
if health['memory_pressure'] == 'high':
    # Trigger cleanup
    resource_manager.emergency_cleanup()
```

**High Detection Rate**  
```python
# Check detection metrics
if health['detection_rate'] > 5.0:
    # Increase stealth, rotate proxies
    session.increase_stealth_level()
```

**Low Throughput**
```python
# Check performance metrics
dashboard = perf_monitor.get_performance_dashboard()
if dashboard['current_metrics']['leads_per_minute'] < 20:
    # Increase concurrent sessions
    orchestrator.scale_sessions(target_count=8)
```

### Performance Optimization Tips

1. **Memory Management**
   - Enable aggressive cleanup for high-volume operations
   - Monitor memory usage and adjust thresholds
   - Use driver pooling to reduce allocation overhead

2. **Detection Avoidance**
   - Implement proper delays between requests
   - Rotate user agents and proxies regularly
   - Monitor detection rates in real-time

3. **Throughput Optimization**
   - Balance concurrent sessions vs. detection risk
   - Optimize scroll strategies for target platforms
   - Use intelligent task queuing and prioritization

## 📈 Monitoring & Alerting

### Real-time Dashboards

```python
# Get comprehensive status
status = orchestrator.get_orchestration_status()
performance = perf_monitor.get_performance_dashboard()
system = resource_manager.get_system_status()

# Key metrics to monitor
print(f"Leads/minute: {performance['current_metrics']['leads_per_minute']}")
print(f"Memory usage: {system['memory_metrics']['process_memory_mb']:.1f}MB")
print(f"Active sessions: {status['current_sessions']['active_sessions']}")
print(f"System health: {system['system_health']}")
```

### Alert Thresholds

| Alert Type | Threshold | Action |
|------------|-----------|---------|
| Memory Critical | >90% of limit | Emergency cleanup |
| High Detection Rate | >5% | Increase stealth |
| Low Throughput | <20 leads/min | Scale sessions |
| System Unhealthy | Multiple failures | System restart |

## 🤝 Integration Examples

See `src/optimization/integration_example.py` for complete integration examples and best practices.

## 📋 API Reference

### Core Classes

- **`ResourceManager`**: Central resource management
- **`PerformanceMonitor`**: Performance tracking and alerting  
- **`SessionOrchestrator`**: Session management and load balancing
- **`LoadTestRunner`**: Performance testing and validation

### Global Functions

- **`get_resource_manager(config)`**: Get global resource manager
- **`get_performance_monitor()`**: Get global performance monitor
- **`get_session_orchestrator(config)`**: Get global orchestrator
- **`run_comprehensive_load_test()`**: Execute full load test

## 🎉 Success Metrics

When properly configured, the system achieves:

- ✅ **1000+ leads processed efficiently**
- ✅ **<2GB memory usage maintained**
- ✅ **<5% detection rate achieved**
- ✅ **50+ leads per minute throughput**
- ✅ **95%+ success rate maintained**
- ✅ **Concurrent processing reliability**

---

*For questions or support, refer to the integration examples and test suites for implementation guidance.*