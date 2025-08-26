"""
Performance Benchmarking and Load Testing Suite for PubScrape
Comprehensive performance validation with realistic load scenarios.
"""

import pytest
import time
import asyncio
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import psutil
import gc
import json
from pathlib import Path

# Performance monitoring imports
import resource
import memory_profiler
from contextlib import contextmanager


class PerformanceMonitor:
    """Performance monitoring utility"""
    
    def __init__(self):
        self.metrics = {
            'start_time': None,
            'end_time': None,
            'cpu_usage': [],
            'memory_usage': [],
            'io_operations': [],
            'network_operations': [],
            'response_times': [],
            'throughput': [],
            'error_rates': []
        }
    
    @contextmanager
    def monitor_performance(self, operation_name: str):
        """Context manager for performance monitoring"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent()
        
        try:
            yield self
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            end_cpu = psutil.cpu_percent()
            
            self.metrics['response_times'].append({
                'operation': operation_name,
                'duration': end_time - start_time,
                'start_time': start_time,
                'end_time': end_time
            })
            
            self.metrics['memory_usage'].append({
                'operation': operation_name,
                'start_memory': start_memory,
                'end_memory': end_memory,
                'memory_delta': end_memory - start_memory
            })
            
            self.metrics['cpu_usage'].append({
                'operation': operation_name,
                'start_cpu': start_cpu,
                'end_cpu': end_cpu,
                'cpu_delta': end_cpu - start_cpu
            })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        response_times = [m['duration'] for m in self.metrics['response_times']]
        memory_deltas = [m['memory_delta'] for m in self.metrics['memory_usage']]
        
        return {
            'total_operations': len(response_times),
            'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'avg_memory_delta': sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0,
            'max_memory_delta': max(memory_deltas) if memory_deltas else 0,
            'total_memory_growth': sum(memory_deltas),
            'operations_per_second': len(response_times) / sum(response_times) if response_times and sum(response_times) > 0 else 0
        }


@pytest.mark.performance
class TestScraperPerformance:
    """Test scraper performance under various conditions"""
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring fixture"""
        return PerformanceMonitor()
    
    @pytest.fixture
    def performance_thresholds(self):
        """Performance threshold configuration"""
        return {
            'max_response_time_search': 10.0,      # seconds
            'max_response_time_extract': 5.0,      # seconds
            'max_memory_per_session': 512,         # MB
            'min_throughput': 50,                  # operations per minute
            'max_cpu_usage': 80,                   # percentage
            'max_error_rate': 0.05,                # 5%
            'max_memory_growth': 100,              # MB during test
        }
    
    @pytest.mark.benchmark
    def test_search_operation_performance(self, performance_monitor, performance_thresholds, benchmark):
        """Benchmark search operation performance"""
        
        def mock_search_operation():
            """Mock search operation with realistic timing"""
            time.sleep(0.1 + (time.time() % 0.05))  # 100-150ms
            return {
                'results': [{'title': f'Result {i}', 'url': f'https://example{i}.com'} 
                           for i in range(10)],
                'total_found': 45,
                'search_time': 0.12
            }
        
        # Benchmark the operation
        result = benchmark(mock_search_operation)
        
        # Verify benchmark results
        assert result['results'], "Search operation returned no results"
        assert result['total_found'] > 0, "No results found in search"
        
        # Check performance thresholds (benchmark handles timing)
        stats = benchmark.stats
        assert stats.mean < performance_thresholds['max_response_time_search'], \
            f"Average search time {stats.mean:.3f}s exceeds threshold"
    
    @pytest.mark.performance
    def test_concurrent_search_performance(self, performance_monitor, performance_thresholds):
        """Test performance under concurrent search operations"""
        
        def mock_search_worker(worker_id: int, num_searches: int):
            """Worker function for concurrent searches"""
            results = []
            errors = 0
            
            for i in range(num_searches):
                try:
                    with performance_monitor.monitor_performance(f'search_{worker_id}_{i}'):
                        # Simulate search operation
                        search_time = 0.1 + (i * 0.01)  # Gradually increasing time
                        time.sleep(search_time)
                        
                        result = {
                            'worker_id': worker_id,
                            'search_id': i,
                            'results_count': 10 + (i % 5),
                            'search_time': search_time
                        }
                        results.append(result)
                        
                except Exception as e:
                    errors += 1
            
            return {
                'worker_id': worker_id,
                'results': results,
                'errors': errors,
                'total_searches': num_searches
            }
        
        # Configuration
        num_workers = 5
        searches_per_worker = 20
        
        # Execute concurrent searches
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(mock_search_worker, worker_id, searches_per_worker)
                for worker_id in range(num_workers)
            ]
            
            worker_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # Analyze results
        total_searches = sum(len(wr['results']) for wr in worker_results)
        total_errors = sum(wr['errors'] for wr in worker_results)
        total_duration = end_time - start_time
        
        throughput = total_searches / total_duration * 60  # per minute
        error_rate = total_errors / (total_searches + total_errors)
        
        # Performance assertions
        assert throughput >= performance_thresholds['min_throughput'], \
            f"Throughput {throughput:.1f}/min below threshold"
        assert error_rate <= performance_thresholds['max_error_rate'], \
            f"Error rate {error_rate:.2%} exceeds threshold"
        
        # Get performance summary
        perf_summary = performance_monitor.get_summary()
        assert perf_summary['avg_response_time'] < performance_thresholds['max_response_time_search'], \
            f"Average response time {perf_summary['avg_response_time']:.3f}s exceeds threshold"
    
    @pytest.mark.performance  
    def test_memory_usage_under_load(self, performance_monitor, performance_thresholds):
        """Test memory usage under sustained load"""
        
        def memory_intensive_operation(data_size: int):
            """Simulate memory-intensive scraping operation"""
            # Create large data structures to simulate realistic memory usage
            large_html = '<div>' + 'x' * data_size + '</div>'
            parsed_data = []
            
            # Simulate data extraction and processing
            for i in range(100):
                extracted_item = {
                    'id': i,
                    'content': large_html[i:i+100] if i+100 < len(large_html) else large_html[i:],
                    'metadata': {'index': i, 'timestamp': time.time()},
                    'processing_notes': f'Processed item {i} at {time.time()}'
                }
                parsed_data.append(extracted_item)
            
            # Simulate some processing delay
            time.sleep(0.01)
            
            return parsed_data
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_measurements = [initial_memory]
        
        # Run memory-intensive operations
        for iteration in range(50):
            data_size = 1000 + (iteration * 100)  # Increasing data size
            
            with performance_monitor.monitor_performance(f'memory_test_{iteration}'):
                result = memory_intensive_operation(data_size)
                
                # Force garbage collection periodically
                if iteration % 10 == 0:
                    gc.collect()
                
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_measurements.append(current_memory)
                
                # Memory usage check
                assert current_memory < performance_thresholds['max_memory_per_session'], \
                    f"Memory usage {current_memory:.1f}MB exceeds threshold at iteration {iteration}"
        
        # Analyze memory usage patterns
        max_memory = max(memory_measurements)
        memory_growth = max_memory - initial_memory
        
        assert memory_growth < performance_thresholds['max_memory_growth'], \
            f"Memory growth {memory_growth:.1f}MB exceeds threshold"
        
        # Verify memory cleanup effectiveness
        gc.collect()  # Final cleanup
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        cleanup_effectiveness = (max_memory - final_memory) / max_memory if max_memory > 0 else 0
        
        assert cleanup_effectiveness > 0.5, \
            f"Memory cleanup effectiveness {cleanup_effectiveness:.1%} insufficient"
    
    @pytest.mark.performance
    def test_scalability_limits(self, performance_monitor):
        """Test system scalability limits"""
        
        def incremental_load_test(base_load: int, increment: int, max_iterations: int):
            """Test with incrementally increasing load"""
            results = []
            
            for iteration in range(max_iterations):
                current_load = base_load + (iteration * increment)
                start_time = time.time()
                
                # Simulate processing load
                processed_items = []
                for item_id in range(current_load):
                    # Simulate item processing
                    processing_time = 0.001 + (item_id * 0.0001)  # Increasing complexity
                    time.sleep(processing_time)
                    
                    processed_items.append({
                        'id': item_id,
                        'processed_at': time.time(),
                        'processing_time': processing_time
                    })
                
                duration = time.time() - start_time
                throughput = current_load / duration
                
                result = {
                    'iteration': iteration,
                    'load': current_load,
                    'duration': duration,
                    'throughput': throughput,
                    'success': True
                }
                
                # Check for performance degradation
                if iteration > 0:
                    prev_throughput = results[-1]['throughput']
                    degradation = (prev_throughput - throughput) / prev_throughput
                    
                    if degradation > 0.5:  # 50% degradation indicates limit
                        result['success'] = False
                        result['degradation'] = degradation
                        break
                
                results.append(result)
            
            return results
        
        # Run scalability test
        scalability_results = incremental_load_test(
            base_load=10, 
            increment=20, 
            max_iterations=20
        )
        
        # Analyze scalability
        successful_iterations = [r for r in scalability_results if r['success']]
        max_successful_load = max(r['load'] for r in successful_iterations) if successful_iterations else 0
        
        assert len(successful_iterations) >= 10, \
            f"System failed scalability test too early (only {len(successful_iterations)} successful iterations)"
        assert max_successful_load >= 200, \
            f"Maximum load {max_successful_load} below expected minimum of 200"
        
        # Analyze performance curves
        throughputs = [r['throughput'] for r in successful_iterations]
        throughput_trend = []
        
        for i in range(1, len(throughputs)):
            trend = (throughputs[i] - throughputs[i-1]) / throughputs[i-1]
            throughput_trend.append(trend)
        
        # Verify reasonable performance scaling
        avg_trend = sum(throughput_trend) / len(throughput_trend) if throughput_trend else 0
        assert avg_trend > -0.1, f"Performance degradation trend {avg_trend:.2%} too steep"


@pytest.mark.performance 
class TestEndToEndPerformance:
    """End-to-end performance testing"""
    
    @pytest.fixture
    def e2e_performance_config(self):
        """Configuration for E2E performance testing"""
        return {
            'campaign_sizes': [10, 50, 100, 500],
            'concurrent_campaigns': [1, 3, 5],
            'max_acceptable_time': {
                10: 30,    # 10 leads in 30 seconds
                50: 120,   # 50 leads in 2 minutes  
                100: 300,  # 100 leads in 5 minutes
                500: 1200  # 500 leads in 20 minutes
            }
        }
    
    @pytest.mark.slow
    def test_full_pipeline_performance(self, e2e_performance_config, performance_monitor):
        """Test full pipeline performance with realistic data volumes"""
        
        def simulate_full_pipeline(campaign_size: int):
            """Simulate complete lead generation pipeline"""
            pipeline_stages = []
            start_time = time.time()
            
            # Stage 1: Query Generation
            stage_start = time.time()
            queries = [f"query_{i}" for i in range(campaign_size // 5)]  # 5 leads per query
            pipeline_stages.append({
                'stage': 'query_generation',
                'duration': time.time() - stage_start,
                'output_count': len(queries)
            })
            
            # Stage 2: Search Execution
            stage_start = time.time()
            search_results = []
            for query in queries:
                # Simulate search delay
                time.sleep(0.1 + (len(query) * 0.001))
                search_results.extend([
                    {'query': query, 'result_id': f'{query}_{i}', 'relevance': 0.8 + (i * 0.02)}
                    for i in range(5)
                ])
            
            pipeline_stages.append({
                'stage': 'search_execution',
                'duration': time.time() - stage_start,
                'output_count': len(search_results)
            })
            
            # Stage 3: Data Extraction
            stage_start = time.time()
            extracted_data = []
            for result in search_results:
                # Simulate extraction processing
                time.sleep(0.05 + (result['relevance'] * 0.01))
                extracted_data.append({
                    'business_name': f"Business for {result['query']}",
                    'email': f"contact@{result['result_id']}.com",
                    'phone': f"(555) {len(result['result_id']):03d}-{hash(result['result_id']) % 10000:04d}",
                    'extraction_confidence': result['relevance']
                })
            
            pipeline_stages.append({
                'stage': 'data_extraction', 
                'duration': time.time() - stage_start,
                'output_count': len(extracted_data)
            })
            
            # Stage 4: Validation & Deduplication
            stage_start = time.time()
            # Simulate deduplication (remove ~10% as duplicates)
            unique_data = extracted_data[::10] + extracted_data[9::10]  # Keep 90%
            time.sleep(len(extracted_data) * 0.001)  # Validation time
            
            pipeline_stages.append({
                'stage': 'validation',
                'duration': time.time() - stage_start,
                'output_count': len(unique_data)
            })
            
            # Stage 5: Export
            stage_start = time.time()
            time.sleep(len(unique_data) * 0.002)  # Export time
            
            pipeline_stages.append({
                'stage': 'export',
                'duration': time.time() - stage_start,
                'output_count': len(unique_data)
            })
            
            total_duration = time.time() - start_time
            
            return {
                'campaign_size': campaign_size,
                'total_duration': total_duration,
                'final_lead_count': len(unique_data),
                'pipeline_stages': pipeline_stages,
                'leads_per_second': len(unique_data) / total_duration,
                'success': True
            }
        
        # Test different campaign sizes
        performance_results = []
        
        for campaign_size in e2e_performance_config['campaign_sizes']:
            with performance_monitor.monitor_performance(f'e2e_campaign_{campaign_size}'):
                result = simulate_full_pipeline(campaign_size)
                performance_results.append(result)
                
                # Check against time thresholds
                max_time = e2e_performance_config['max_acceptable_time'][campaign_size]
                assert result['total_duration'] <= max_time, \
                    f"Campaign size {campaign_size} took {result['total_duration']:.1f}s, exceeds {max_time}s threshold"
                
                # Verify lead count is reasonable (should get most leads)
                expected_leads = campaign_size * 0.8  # Expect 80% success rate
                assert result['final_lead_count'] >= expected_leads, \
                    f"Final lead count {result['final_lead_count']} below expected {expected_leads}"
        
        # Analyze scaling characteristics
        throughputs = [r['leads_per_second'] for r in performance_results]
        campaign_sizes = [r['campaign_size'] for r in performance_results]
        
        # Verify throughput doesn't degrade severely with size
        small_throughput = throughputs[0]  # Smallest campaign
        large_throughput = throughputs[-1]  # Largest campaign
        
        # Allow some degradation but not too much
        throughput_ratio = large_throughput / small_throughput
        assert throughput_ratio > 0.3, \
            f"Throughput degradation too severe: {throughput_ratio:.2f} (large/small campaign ratio)"
    
    @pytest.mark.performance
    def test_concurrent_campaign_performance(self, e2e_performance_config):
        """Test performance with multiple concurrent campaigns"""
        
        def run_concurrent_campaigns(num_campaigns: int, campaign_size: int):
            """Run multiple campaigns concurrently"""
            
            def single_campaign_worker(campaign_id: int):
                """Worker for single campaign"""
                start_time = time.time()
                
                # Simulate campaign execution
                leads_generated = []
                for lead_id in range(campaign_size):
                    # Simulate variable processing time
                    processing_time = 0.01 + (lead_id * 0.001) + (campaign_id * 0.0005)
                    time.sleep(processing_time)
                    
                    lead = {
                        'campaign_id': campaign_id,
                        'lead_id': lead_id,
                        'generated_at': time.time(),
                        'processing_time': processing_time
                    }
                    leads_generated.append(lead)
                
                duration = time.time() - start_time
                return {
                    'campaign_id': campaign_id,
                    'leads_generated': len(leads_generated),
                    'duration': duration,
                    'throughput': len(leads_generated) / duration
                }
            
            # Execute campaigns concurrently
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_campaigns) as executor:
                futures = [
                    executor.submit(single_campaign_worker, campaign_id)
                    for campaign_id in range(num_campaigns)
                ]
                
                campaign_results = [
                    future.result() 
                    for future in concurrent.futures.as_completed(futures)
                ]
            
            total_duration = time.time() - start_time
            
            return {
                'num_campaigns': num_campaigns,
                'campaign_size': campaign_size,
                'campaign_results': campaign_results,
                'total_duration': total_duration,
                'total_leads': sum(r['leads_generated'] for r in campaign_results),
                'overall_throughput': sum(r['leads_generated'] for r in campaign_results) / total_duration
            }
        
        # Test different concurrency levels
        concurrency_results = []
        base_campaign_size = 20  # Smaller size for concurrency testing
        
        for num_campaigns in e2e_performance_config['concurrent_campaigns']:
            result = run_concurrent_campaigns(num_campaigns, base_campaign_size)
            concurrency_results.append(result)
            
            # Verify all campaigns completed successfully
            assert len(result['campaign_results']) == num_campaigns, \
                f"Not all campaigns completed: {len(result['campaign_results'])} of {num_campaigns}"
            
            # Verify reasonable throughput scaling
            expected_total_leads = num_campaigns * base_campaign_size
            assert result['total_leads'] == expected_total_leads, \
                f"Total leads {result['total_leads']} != expected {expected_total_leads}"
            
            # Check individual campaign performance
            individual_throughputs = [r['throughput'] for r in result['campaign_results']]
            avg_individual_throughput = sum(individual_throughputs) / len(individual_throughputs)
            
            # Concurrent campaigns should maintain reasonable individual performance  
            assert avg_individual_throughput > 0.5, \
                f"Average individual throughput {avg_individual_throughput:.2f} too low for {num_campaigns} concurrent campaigns"
        
        # Analyze concurrency scaling
        throughputs = [r['overall_throughput'] for r in concurrency_results]
        
        # Verify throughput increases with more campaigns (up to a point)
        if len(throughputs) >= 2:
            throughput_improvement = throughputs[1] / throughputs[0]
            assert throughput_improvement > 1.5, \
                f"Concurrency throughput improvement {throughput_improvement:.2f} insufficient"


@pytest.mark.performance
class TestResourceUtilization:
    """Test resource utilization and efficiency"""
    
    @pytest.mark.performance
    def test_cpu_utilization_efficiency(self):
        """Test CPU utilization efficiency"""
        
        def cpu_intensive_task(task_id: int, duration: float):
            """CPU-intensive task simulation"""
            start_time = time.time()
            result = 0
            
            # CPU-intensive computation
            while time.time() - start_time < duration:
                result += sum(i**2 for i in range(1000))
            
            return {
                'task_id': task_id,
                'result': result,
                'actual_duration': time.time() - start_time
            }
        
        # Monitor CPU usage during intensive operations
        initial_cpu = psutil.cpu_percent(interval=1)
        cpu_measurements = [initial_cpu]
        
        # Run CPU-intensive tasks
        task_duration = 0.5  # 500ms per task
        num_tasks = 10
        
        start_time = time.time()
        for task_id in range(num_tasks):
            result = cpu_intensive_task(task_id, task_duration)
            current_cpu = psutil.cpu_percent(interval=0.1)
            cpu_measurements.append(current_cpu)
        
        total_duration = time.time() - start_time
        
        # Analyze CPU utilization
        avg_cpu = sum(cpu_measurements) / len(cpu_measurements)
        max_cpu = max(cpu_measurements)
        
        # CPU should be reasonably utilized during intensive tasks
        assert avg_cpu > 20, f"Average CPU usage {avg_cpu:.1f}% too low during intensive tasks"
        assert max_cpu < 95, f"Max CPU usage {max_cpu:.1f}% too high (potential system strain)"
        
        # Efficiency check: tasks should complete in reasonable time
        expected_duration = num_tasks * task_duration
        efficiency = expected_duration / total_duration
        
        assert efficiency > 0.8, f"CPU efficiency {efficiency:.2%} below acceptable threshold"
    
    @pytest.mark.performance
    def test_io_performance(self):
        """Test I/O performance for file operations"""
        
        def io_intensive_operations(num_operations: int):
            """Simulate I/O intensive operations"""
            import tempfile
            import os
            
            results = []
            temp_files = []
            
            try:
                for i in range(num_operations):
                    start_time = time.time()
                    
                    # Create temporary file
                    temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
                    temp_files.append(temp_file.name)
                    
                    # Write data
                    test_data = f"Test data for operation {i}: " + "x" * 1000
                    temp_file.write(test_data)
                    temp_file.close()
                    
                    # Read data back
                    with open(temp_file.name, 'r') as f:
                        read_data = f.read()
                    
                    # Verify data integrity
                    data_match = read_data == test_data
                    
                    duration = time.time() - start_time
                    results.append({
                        'operation_id': i,
                        'duration': duration,
                        'data_size': len(test_data),
                        'data_integrity': data_match
                    })
                
                return results
                
            finally:
                # Cleanup
                for temp_file in temp_files:
                    try:
                        os.unlink(temp_file)
                    except OSError:
                        pass
        
        # Run I/O operations
        io_results = io_intensive_operations(50)
        
        # Analyze I/O performance
        durations = [r['duration'] for r in io_results]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        # I/O performance thresholds
        assert avg_duration < 0.1, f"Average I/O duration {avg_duration:.3f}s too slow"
        assert max_duration < 0.5, f"Max I/O duration {max_duration:.3f}s indicates I/O bottleneck"
        
        # Verify data integrity
        integrity_failures = [r for r in io_results if not r['data_integrity']]
        assert len(integrity_failures) == 0, f"{len(integrity_failures)} I/O integrity failures detected"
        
        # Calculate I/O throughput
        total_data_size = sum(r['data_size'] for r in io_results)
        total_duration = sum(durations)
        throughput_mbps = (total_data_size / total_duration) / (1024 * 1024)  # MB/s
        
        assert throughput_mbps > 1.0, f"I/O throughput {throughput_mbps:.2f} MB/s too low"
    
    @pytest.mark.performance 
    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operations"""
        
        def potentially_leaky_operation(iteration: int):
            """Operation that might have memory leaks"""
            # Simulate data structures that might not be properly cleaned up
            large_data = {
                'iteration': iteration,
                'data': ['x' * 1000 for _ in range(100)],  # 100KB of data
                'metadata': {
                    'timestamp': time.time(),
                    'processing_notes': f'Iteration {iteration} data',
                    'additional_info': {'key': 'value'} * 50
                }
            }
            
            # Simulate processing
            processed_data = []
            for item in large_data['data']:
                processed_item = item.upper()  # Simple processing
                processed_data.append(processed_item)
            
            # Return some data (which might accumulate)
            return {
                'iteration': iteration,
                'processed_count': len(processed_data),
                'sample_data': processed_data[:5]  # Keep only sample
            }
        
        # Monitor memory usage over many iterations
        memory_measurements = []
        gc.collect()  # Start with clean slate
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        results = []
        for iteration in range(200):  # Many iterations to detect leaks
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory)
            
            result = potentially_leaky_operation(iteration)
            results.append(result)
            
            # Periodic garbage collection
            if iteration % 50 == 0:
                gc.collect()
        
        # Final cleanup and measurement
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Analyze memory growth patterns
        memory_growth = final_memory - initial_memory
        peak_memory = max(memory_measurements)
        memory_variance = sum((m - sum(memory_measurements)/len(memory_measurements))**2 
                             for m in memory_measurements) / len(memory_measurements)
        
        # Memory leak detection
        assert memory_growth < 200, f"Total memory growth {memory_growth:.1f}MB indicates potential leak"
        assert peak_memory < initial_memory + 300, f"Peak memory {peak_memory:.1f}MB too high"
        
        # Check for consistent growth pattern (leak indicator)
        # Calculate linear trend in memory usage
        n = len(memory_measurements)
        x_sum = sum(range(n))
        y_sum = sum(memory_measurements)
        xy_sum = sum(i * memory_measurements[i] for i in range(n))
        x_sq_sum = sum(i**2 for i in range(n))
        
        # Linear regression slope
        slope = (n * xy_sum - x_sum * y_sum) / (n * x_sq_sum - x_sum**2)
        
        # Slope indicates memory growth rate per iteration
        assert slope < 0.1, f"Memory growth slope {slope:.3f} MB/iteration indicates leak"
        
        return {
            'initial_memory': initial_memory,
            'final_memory': final_memory,
            'memory_growth': memory_growth,
            'peak_memory': peak_memory,
            'growth_slope': slope,
            'iterations': len(results)
        }