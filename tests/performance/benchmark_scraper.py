"""
Performance benchmarking tests for the scraper system.

Measures throughput, latency, memory usage, and scalability
under various load conditions and configuration scenarios.
"""

import pytest
import time
import psutil
import statistics
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable
from unittest.mock import Mock, patch
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data"""
    operation_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float
    success_rate: float
    error_count: int
    timestamp: datetime
    metadata: Dict[str, Any]


class PerformanceBenchmark:
    """Performance benchmarking utility class"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
    
    def measure_operation(self, 
                         operation: Callable,
                         operation_name: str,
                         iterations: int = 100,
                         **kwargs) -> PerformanceMetrics:
        """Measure performance of a single operation"""
        execution_times = []
        memory_readings = []
        cpu_readings = []
        errors = 0
        
        # Baseline measurements
        baseline_memory = self.process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                # Memory before operation
                mem_before = self.process.memory_info().rss / 1024 / 1024
                cpu_before = self.process.cpu_percent()
                
                # Execute operation
                op_start = time.perf_counter()
                result = operation(**kwargs)
                op_end = time.perf_counter()
                
                # Memory after operation
                mem_after = self.process.memory_info().rss / 1024 / 1024
                cpu_after = self.process.cpu_percent()
                
                execution_times.append(op_end - op_start)
                memory_readings.append(mem_after - mem_before)
                cpu_readings.append(max(cpu_after - cpu_before, 0))
                
            except Exception as e:
                errors += 1
                execution_times.append(float('inf'))
                memory_readings.append(0)
                cpu_readings.append(0)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate metrics
        valid_times = [t for t in execution_times if t != float('inf')]
        avg_execution_time = statistics.mean(valid_times) if valid_times else 0
        avg_memory_usage = statistics.mean(memory_readings)
        avg_cpu_usage = statistics.mean(cpu_readings)
        throughput = len(valid_times) / total_duration if total_duration > 0 else 0
        success_rate = len(valid_times) / iterations
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            execution_time=avg_execution_time,
            memory_usage_mb=avg_memory_usage,
            cpu_usage_percent=avg_cpu_usage,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            timestamp=datetime.now(),
            metadata={
                "iterations": iterations,
                "total_duration": total_duration,
                "min_execution_time": min(valid_times) if valid_times else 0,
                "max_execution_time": max(valid_times) if valid_times else 0,
                "median_execution_time": statistics.median(valid_times) if valid_times else 0,
                "std_deviation": statistics.stdev(valid_times) if len(valid_times) > 1 else 0
            }
        )
        
        self.metrics.append(metrics)
        return metrics
    
    def stress_test(self,
                   operation: Callable,
                   operation_name: str,
                   concurrent_threads: int = 10,
                   duration_seconds: int = 60,
                   **kwargs) -> Dict[str, Any]:
        """Perform stress testing with concurrent operations"""
        results = {
            "start_time": datetime.now(),
            "concurrent_threads": concurrent_threads,
            "duration_seconds": duration_seconds,
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "operations_per_second": 0,
            "response_times": [],
            "memory_peak_mb": 0,
            "cpu_peak_percent": 0,
            "errors": []
        }
        
        stop_time = time.time() + duration_seconds
        operation_count = 0
        operation_lock = threading.Lock()
        
        def worker():
            nonlocal operation_count
            while time.time() < stop_time:
                try:
                    start = time.perf_counter()
                    result = operation(**kwargs)
                    end = time.perf_counter()
                    
                    with operation_lock:
                        operation_count += 1
                        results["successful_operations"] += 1
                        results["response_times"].append(end - start)
                        
                except Exception as e:
                    with operation_lock:
                        operation_count += 1
                        results["failed_operations"] += 1
                        results["errors"].append(str(e))
        
        # Start monitoring thread
        def monitor():
            peak_memory = 0
            peak_cpu = 0
            
            while time.time() < stop_time:
                try:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    current_cpu = self.process.cpu_percent()
                    
                    peak_memory = max(peak_memory, current_memory)
                    peak_cpu = max(peak_cpu, current_cpu)
                    
                    time.sleep(1)  # Monitor every second
                except:
                    pass
            
            results["memory_peak_mb"] = peak_memory
            results["cpu_peak_percent"] = peak_cpu
        
        # Start all threads
        threads = []
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.start()
        
        for _ in range(concurrent_threads):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        monitor_thread.join()
        
        # Calculate final metrics
        results["end_time"] = datetime.now()
        results["total_operations"] = operation_count
        actual_duration = (results["end_time"] - results["start_time"]).total_seconds()
        results["operations_per_second"] = operation_count / actual_duration if actual_duration > 0 else 0
        
        if results["response_times"]:
            results["avg_response_time"] = statistics.mean(results["response_times"])
            results["min_response_time"] = min(results["response_times"])
            results["max_response_time"] = max(results["response_times"])
            results["median_response_time"] = statistics.median(results["response_times"])
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.metrics:
            return {"error": "No metrics collected"}
        
        report = {
            "summary": {
                "total_operations_tested": len(self.metrics),
                "test_period": {
                    "start": min(m.timestamp for m in self.metrics),
                    "end": max(m.timestamp for m in self.metrics)
                },
                "overall_success_rate": statistics.mean([m.success_rate for m in self.metrics])
            },
            "operations": {},
            "recommendations": []
        }
        
        # Group metrics by operation
        operations = {}
        for metric in self.metrics:
            if metric.operation_name not in operations:
                operations[metric.operation_name] = []
            operations[metric.operation_name].append(metric)
        
        # Analyze each operation
        for op_name, op_metrics in operations.items():
            analysis = {
                "total_tests": len(op_metrics),
                "avg_execution_time": statistics.mean([m.execution_time for m in op_metrics]),
                "avg_memory_usage": statistics.mean([m.memory_usage_mb for m in op_metrics]),
                "avg_throughput": statistics.mean([m.throughput_ops_per_sec for m in op_metrics]),
                "success_rate": statistics.mean([m.success_rate for m in op_metrics]),
                "total_errors": sum(m.error_count for m in op_metrics)
            }
            
            # Add performance ratings
            if analysis["avg_execution_time"] < 0.1:
                analysis["performance_rating"] = "Excellent"
            elif analysis["avg_execution_time"] < 1.0:
                analysis["performance_rating"] = "Good"
            elif analysis["avg_execution_time"] < 5.0:
                analysis["performance_rating"] = "Acceptable"
            else:
                analysis["performance_rating"] = "Poor"
            
            report["operations"][op_name] = analysis
        
        # Generate recommendations
        for op_name, analysis in report["operations"].items():
            if analysis["avg_execution_time"] > 2.0:
                report["recommendations"].append(
                    f"Optimize {op_name} - execution time is {analysis['avg_execution_time']:.2f}s"
                )
            
            if analysis["avg_memory_usage"] > 100:
                report["recommendations"].append(
                    f"Reduce memory usage for {op_name} - currently using {analysis['avg_memory_usage']:.1f}MB"
                )
            
            if analysis["success_rate"] < 0.95:
                report["recommendations"].append(
                    f"Improve reliability of {op_name} - success rate is {analysis['success_rate']:.1%}"
                )
        
        return report


@pytest.mark.performance
class TestScraperPerformance:
    """Performance tests for scraper components"""
    
    @pytest.fixture
    def benchmark(self):
        """Create performance benchmark instance"""
        return PerformanceBenchmark()
    
    @pytest.fixture
    def mock_search_operation(self):
        """Mock search operation for performance testing"""
        def search_operation(query="test query", delay=0.01):
            time.sleep(delay)  # Simulate work
            return {
                "status": "success",
                "results": [f"result_{i}" for i in range(10)],
                "query": query
            }
        return search_operation
    
    @pytest.fixture
    def mock_parse_operation(self):
        """Mock parsing operation for performance testing"""
        def parse_operation(html="<html>test</html>", complexity=1):
            # Simulate parsing complexity
            for i in range(complexity * 100):
                _ = html.count("test")
            
            return {
                "status": "success",
                "parsed_data": [f"data_{i}" for i in range(5)]
            }
        return parse_operation
    
    @pytest.fixture
    def mock_extraction_operation(self):
        """Mock email extraction operation"""
        def extract_operation(url="https://example.com", depth=1):
            # Simulate extraction work
            time.sleep(0.005 * depth)
            
            return {
                "status": "success",
                "emails": [f"email{i}@example.com" for i in range(depth * 2)]
            }
        return extract_operation
    
    def test_search_operation_performance(self, benchmark, mock_search_operation, benchmark_thresholds):
        """Test search operation performance"""
        metrics = benchmark.measure_operation(
            operation=mock_search_operation,
            operation_name="bing_search",
            iterations=50,
            delay=0.01
        )
        
        # Validate against thresholds
        assert metrics.execution_time <= benchmark_thresholds["max_response_time"]
        assert metrics.success_rate >= benchmark_thresholds["min_success_rate"]
        assert metrics.memory_usage_mb <= benchmark_thresholds["max_memory_usage"]
        assert metrics.throughput_ops_per_sec >= 5  # At least 5 searches per second
    
    def test_parsing_operation_performance(self, benchmark, mock_parse_operation, benchmark_thresholds):
        """Test parsing operation performance"""
        metrics = benchmark.measure_operation(
            operation=mock_parse_operation,
            operation_name="serp_parsing",
            iterations=100,
            complexity=1
        )
        
        assert metrics.execution_time <= 0.1  # Parsing should be fast
        assert metrics.success_rate >= benchmark_thresholds["min_success_rate"]
        assert metrics.throughput_ops_per_sec >= 50  # At least 50 parses per second
    
    def test_extraction_operation_performance(self, benchmark, mock_extraction_operation):
        """Test email extraction performance"""
        metrics = benchmark.measure_operation(
            operation=mock_extraction_operation,
            operation_name="email_extraction",
            iterations=30,
            depth=2
        )
        
        assert metrics.execution_time <= 0.5  # Extraction should be reasonable
        assert metrics.success_rate >= 0.95
        assert metrics.throughput_ops_per_sec >= 10  # At least 10 extractions per second
    
    @pytest.mark.slow
    def test_concurrent_search_performance(self, benchmark, mock_search_operation):
        """Test performance under concurrent load"""
        stress_results = benchmark.stress_test(
            operation=mock_search_operation,
            operation_name="concurrent_search",
            concurrent_threads=5,
            duration_seconds=10,
            delay=0.02
        )
        
        assert stress_results["operations_per_second"] >= 20  # Reasonable throughput
        assert stress_results["successful_operations"] > 0
        assert stress_results["failed_operations"] / stress_results["total_operations"] < 0.05  # <5% failure rate
        
        if stress_results["response_times"]:
            assert stress_results["avg_response_time"] <= 1.0  # Average response time
            assert stress_results["max_response_time"] <= 5.0  # Max response time
    
    def test_memory_usage_scaling(self, benchmark, mock_parse_operation):
        """Test memory usage scaling with workload size"""
        workload_sizes = [10, 50, 100, 200]
        memory_usage = []
        
        for size in workload_sizes:
            metrics = benchmark.measure_operation(
                operation=mock_parse_operation,
                operation_name=f"parse_scaling_{size}",
                iterations=size,
                complexity=1
            )
            memory_usage.append(metrics.memory_usage_mb)
        
        # Memory usage should not grow exponentially
        for i in range(1, len(memory_usage)):
            growth_ratio = memory_usage[i] / memory_usage[i-1] if memory_usage[i-1] > 0 else 1
            assert growth_ratio <= 3.0  # Memory shouldn't triple between workload sizes
    
    def test_throughput_degradation(self, benchmark, mock_search_operation):
        """Test throughput degradation under sustained load"""
        # Test different load levels
        thread_counts = [1, 2, 5, 10]
        throughputs = []
        
        for threads in thread_counts:
            stress_results = benchmark.stress_test(
                operation=mock_search_operation,
                operation_name=f"throughput_test_{threads}_threads",
                concurrent_threads=threads,
                duration_seconds=5,
                delay=0.01
            )
            throughputs.append(stress_results["operations_per_second"])
        
        # Throughput should generally increase with more threads (up to a point)
        assert throughputs[1] >= throughputs[0]  # 2 threads should be better than 1
        assert throughputs[2] >= throughputs[1] * 0.8  # 5 threads should be reasonably good
        
        # But shouldn't degrade too much with many threads
        efficiency_ratio = throughputs[-1] / (throughputs[0] * thread_counts[-1])
        assert efficiency_ratio >= 0.3  # At least 30% efficiency with 10 threads
    
    def test_error_rate_under_stress(self, benchmark):
        """Test error rates under stress conditions"""
        def unreliable_operation(failure_rate=0.1):
            import random
            if random.random() < failure_rate:
                raise Exception("Simulated failure")
            time.sleep(0.01)
            return {"status": "success"}
        
        # Test with moderate failure rate
        metrics = benchmark.measure_operation(
            operation=unreliable_operation,
            operation_name="unreliable_operation",
            iterations=100,
            failure_rate=0.1
        )
        
        # Should handle failures gracefully
        assert metrics.success_rate >= 0.85  # Should succeed most of the time
        assert metrics.error_count <= 15  # Error count should be reasonable
    
    @pytest.mark.slow
    def test_sustained_performance(self, benchmark, mock_search_operation):
        """Test performance over extended period"""
        # Run for extended period to check for memory leaks or degradation
        long_stress_results = benchmark.stress_test(
            operation=mock_search_operation,
            operation_name="sustained_performance",
            concurrent_threads=3,
            duration_seconds=30,
            delay=0.005
        )
        
        # Performance should remain stable
        assert long_stress_results["operations_per_second"] >= 50
        assert long_stress_results["memory_peak_mb"] <= 200  # Reasonable memory usage
        assert long_stress_results["cpu_peak_percent"] <= 90  # Shouldn't max out CPU
        
        # Response time variance should be reasonable
        if long_stress_results["response_times"]:
            response_times = long_stress_results["response_times"]
            std_dev = statistics.stdev(response_times)
            mean_time = statistics.mean(response_times)
            coefficient_of_variation = std_dev / mean_time if mean_time > 0 else 0
            
            assert coefficient_of_variation <= 2.0  # Response times shouldn't be too variable


@pytest.mark.performance
class TestRealWorldScenarios:
    """Performance tests for real-world usage scenarios"""
    
    @pytest.fixture
    def benchmark(self):
        return PerformanceBenchmark()
    
    def test_typical_campaign_performance(self, benchmark):
        """Test performance of a typical campaign scenario"""
        def simulate_campaign(num_queries=10, results_per_query=20):
            """Simulate a typical lead generation campaign"""
            campaign_start = time.time()
            
            # Simulate search phase
            search_time = 0
            for i in range(num_queries):
                start = time.time()
                time.sleep(0.05)  # Simulate search delay
                search_time += time.time() - start
            
            # Simulate parsing phase
            parse_time = 0
            total_results = num_queries * results_per_query
            for i in range(total_results):
                start = time.time()
                time.sleep(0.001)  # Simulate parsing
                parse_time += time.time() - start
            
            # Simulate extraction phase
            extraction_time = 0
            for i in range(total_results):
                start = time.time()
                time.sleep(0.002)  # Simulate extraction
                extraction_time += time.time() - start
            
            campaign_duration = time.time() - campaign_start
            
            return {
                "status": "success",
                "total_duration": campaign_duration,
                "search_time": search_time,
                "parse_time": parse_time,
                "extraction_time": extraction_time,
                "results_processed": total_results
            }
        
        metrics = benchmark.measure_operation(
            operation=simulate_campaign,
            operation_name="typical_campaign",
            iterations=5,
            num_queries=10,
            results_per_query=20
        )
        
        # Campaign should complete in reasonable time
        assert metrics.execution_time <= 30.0  # 30 seconds max
        assert metrics.success_rate == 1.0  # Should always succeed
        assert metrics.throughput_ops_per_sec >= 0.1  # At least 1 campaign per 10 seconds
    
    def test_bulk_processing_performance(self, benchmark):
        """Test performance when processing large batches"""
        def bulk_process(batch_size=1000):
            """Simulate bulk data processing"""
            start_time = time.time()
            
            # Simulate processing each item
            processed = 0
            for i in range(batch_size):
                # Simulate some processing work
                _ = str(i) * 10
                processed += 1
                
                # Simulate memory allocation/deallocation
                if i % 100 == 0:
                    time.sleep(0.001)  # Simulate GC or I/O
            
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "processed_items": processed,
                "duration": duration,
                "items_per_second": processed / duration if duration > 0 else 0
            }
        
        # Test different batch sizes
        for batch_size in [100, 500, 1000, 2000]:
            metrics = benchmark.measure_operation(
                operation=bulk_process,
                operation_name=f"bulk_process_{batch_size}",
                iterations=3,
                batch_size=batch_size
            )
            
            # Processing rate should be reasonable
            assert metrics.execution_time <= batch_size * 0.001  # Max 1ms per item
            assert metrics.success_rate == 1.0
    
    def test_data_export_performance(self, benchmark):
        """Test performance of data export operations"""
        def export_data(record_count=1000, format_type="csv"):
            """Simulate data export"""
            import io
            import csv
            import json
            
            start_time = time.time()
            
            # Generate sample data
            data = []
            for i in range(record_count):
                data.append({
                    "id": i,
                    "email": f"user{i}@example.com",
                    "business": f"Business {i}",
                    "phone": f"555-{i:04d}",
                    "address": f"{i} Main St, City, State"
                })
            
            # Export data
            if format_type == "csv":
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                result = output.getvalue()
            
            elif format_type == "json":
                result = json.dumps(data, indent=2)
            
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "records_exported": record_count,
                "format": format_type,
                "duration": duration,
                "output_size": len(result)
            }
        
        # Test CSV export
        csv_metrics = benchmark.measure_operation(
            operation=export_data,
            operation_name="csv_export",
            iterations=10,
            record_count=1000,
            format_type="csv"
        )
        
        # Test JSON export
        json_metrics = benchmark.measure_operation(
            operation=export_data,
            operation_name="json_export",
            iterations=10,
            record_count=1000,
            format_type="json"
        )
        
        # Export should be fast
        assert csv_metrics.execution_time <= 1.0  # CSV export should be under 1s
        assert json_metrics.execution_time <= 2.0  # JSON export can be slightly slower
        
        # Both should have high success rates
        assert csv_metrics.success_rate >= 0.95
        assert json_metrics.success_rate >= 0.95
    
    def test_concurrent_campaign_performance(self, benchmark):
        """Test performance when running multiple campaigns concurrently"""
        def mini_campaign(campaign_id=1):
            """Simulate a small campaign"""
            start_time = time.time()
            
            # Simulate campaign work
            for phase in ["search", "parse", "extract", "validate", "export"]:
                time.sleep(0.01)  # Each phase takes some time
            
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "campaign_id": campaign_id,
                "duration": duration
            }
        
        # Test concurrent execution
        stress_results = benchmark.stress_test(
            operation=mini_campaign,
            operation_name="concurrent_campaigns",
            concurrent_threads=5,
            duration_seconds=15
        )
        
        # Should handle multiple campaigns efficiently
        assert stress_results["operations_per_second"] >= 10  # At least 10 campaigns per second
        assert stress_results["memory_peak_mb"] <= 300  # Reasonable memory usage
        
        # Response times should be consistent
        if stress_results["response_times"]:
            max_response = max(stress_results["response_times"])
            min_response = min(stress_results["response_times"])
            assert max_response / min_response <= 5  # Response times shouldn't vary too much


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression testing"""
    
    @pytest.fixture
    def baseline_metrics(self):
        """Baseline performance metrics for regression testing"""
        return {
            "search_operation": {
                "max_execution_time": 2.0,
                "min_throughput": 10.0,
                "max_memory_usage": 50.0
            },
            "parse_operation": {
                "max_execution_time": 0.1,
                "min_throughput": 100.0,
                "max_memory_usage": 20.0
            },
            "extract_operation": {
                "max_execution_time": 1.0,
                "min_throughput": 20.0,
                "max_memory_usage": 30.0
            }
        }
    
    def test_search_performance_regression(self, baseline_metrics):
        """Test for performance regression in search operations"""
        benchmark = PerformanceBenchmark()
        
        def mock_search(delay=0.05):
            time.sleep(delay)
            return {"status": "success", "results": ["test"]}
        
        metrics = benchmark.measure_operation(
            operation=mock_search,
            operation_name="search_regression_test",
            iterations=20,
            delay=0.05
        )
        
        baseline = baseline_metrics["search_operation"]
        
        # Check for regressions
        assert metrics.execution_time <= baseline["max_execution_time"], \
            f"Execution time regression: {metrics.execution_time} > {baseline['max_execution_time']}"
        
        assert metrics.throughput_ops_per_sec >= baseline["min_throughput"], \
            f"Throughput regression: {metrics.throughput_ops_per_sec} < {baseline['min_throughput']}"
        
        assert metrics.memory_usage_mb <= baseline["max_memory_usage"], \
            f"Memory usage regression: {metrics.memory_usage_mb} > {baseline['max_memory_usage']}"
    
    def test_parse_performance_regression(self, baseline_metrics):
        """Test for performance regression in parsing operations"""
        benchmark = PerformanceBenchmark()
        
        def mock_parse(complexity=100):
            # Simulate parsing work
            for i in range(complexity):
                _ = str(i)
            return {"status": "success", "data": "parsed"}
        
        metrics = benchmark.measure_operation(
            operation=mock_parse,
            operation_name="parse_regression_test",
            iterations=50,
            complexity=100
        )
        
        baseline = baseline_metrics["parse_operation"]
        
        # Check for regressions
        assert metrics.execution_time <= baseline["max_execution_time"]
        assert metrics.throughput_ops_per_sec >= baseline["min_throughput"]
        assert metrics.memory_usage_mb <= baseline["max_memory_usage"]
    
    def test_extract_performance_regression(self, baseline_metrics):
        """Test for performance regression in extraction operations"""
        benchmark = PerformanceBenchmark()
        
        def mock_extract(work_units=10):
            time.sleep(0.01 * work_units)
            return {"status": "success", "extracted": work_units}
        
        metrics = benchmark.measure_operation(
            operation=mock_extract,
            operation_name="extract_regression_test",
            iterations=30,
            work_units=2
        )
        
        baseline = baseline_metrics["extract_operation"]
        
        # Check for regressions
        assert metrics.execution_time <= baseline["max_execution_time"]
        assert metrics.throughput_ops_per_sec >= baseline["min_throughput"]
        assert metrics.memory_usage_mb <= baseline["max_memory_usage"]
    
    def test_performance_report_generation(self):
        """Test performance report generation"""
        benchmark = PerformanceBenchmark()
        
        # Generate some test metrics
        def dummy_operation():
            time.sleep(0.01)
            return {"status": "success"}
        
        # Run several operations
        for i in range(3):
            benchmark.measure_operation(
                operation=dummy_operation,
                operation_name=f"test_operation_{i}",
                iterations=10
            )
        
        # Generate report
        report = benchmark.generate_report()
        
        # Validate report structure
        assert "summary" in report
        assert "operations" in report
        assert "recommendations" in report
        
        assert report["summary"]["total_operations_tested"] == 3
        assert len(report["operations"]) == 3
        
        # Check operation details
        for op_name, op_data in report["operations"].items():
            assert "avg_execution_time" in op_data
            assert "performance_rating" in op_data
            assert "success_rate" in op_data
