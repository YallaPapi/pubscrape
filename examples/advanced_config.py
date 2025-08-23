#!/usr/bin/env python3
"""
Advanced Configuration Examples for PubScrape Infinite Scroll Scraper System

This file demonstrates advanced configuration patterns, performance optimization,
multi-agent workflows, and production-ready setups.
"""

import os
import sys
import time
import threading
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import advanced modules
from src.core.config_manager import ConfigManager
from src.infra.browser_manager import BrowserManager, BrowserConfig, BrowserMode
from src.infra.anti_detection_supervisor import AntiDetectionSupervisor, DomainOverride
from src.core.base_agent import BaseAgent, AgentConfig
from botasaurus_doctor_scraper import search_bing_for_doctors, extract_doctor_contact_info


class AdvancedConfigurationExamples:
    """Advanced configuration examples and patterns"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.results = {}
    
    def example_1_production_configuration(self):
        """
        Example 1: Production-grade configuration setup
        
        Shows how to configure the system for production use with
        performance optimizations and reliability features.
        """
        print("\n" + "="*60)
        print("🏭 EXAMPLE 1: Production Configuration")
        print("="*60)
        
        # Production configuration dictionary
        production_config = {
            "api": {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "openai_model": "gpt-3.5-turbo",  # Faster model for production
                "openai_temperature": 0.3,  # More deterministic
                "openai_max_tokens": 2000
            },
            "search": {
                "max_pages_per_query": 5,
                "results_per_page": 12,
                "rate_limit_rpm": 18,  # Optimized rate
                "timeout_seconds": 25,
                "max_concurrent_searches": 4,
                "retry_attempts": 3,
                "retry_delay": 2.5,
                "use_stealth_mode": True,
                "cache_results": True,
                "cache_ttl_seconds": 1800  # 30 minutes
            },
            "browser": {
                "mode": "headless",
                "timeout": 25,
                "max_retries": 3,
                "window_size": [1366, 768],  # Standard resolution
                "chrome_options": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-images",
                    "--disable-extensions",
                    "--memory-pressure-off",
                    "--max_old_space_size=2048"
                ]
            },
            "processing": {
                "batch_size": 150,
                "max_workers": 6,
                "validation_enabled": True,
                "email_validation_level": "strict",
                "deduplication_enabled": True,
                "quality_threshold": 0.75
            },
            "export": {
                "output_directory": "production_output",
                "csv_delimiter": ",",
                "csv_encoding": "utf-8",
                "include_metadata": True,
                "compress_output": False,
                "timestamp_format": "%Y%m%d_%H%M%S",
                "max_file_size_mb": 50,
                "split_large_files": True
            },
            "logging": {
                "log_level": "INFO",
                "log_directory": "production_logs",
                "enable_console_logging": True,
                "enable_file_logging": True,
                "separate_error_log": True,
                "max_log_size_mb": 25,
                "backup_count": 10
            },
            "performance": {
                "memory": {
                    "max_memory_mb": 4096,
                    "cleanup_threshold": 0.8,
                    "gc_interval": 100
                },
                "network": {
                    "connection_pool_size": 25,
                    "max_retries": 3,
                    "timeout": (8, 20)
                }
            },
            "debug_mode": False,
            "enable_metrics": True,
            "profile_performance": True
        }
        
        print("🔧 Applying production configuration...")
        
        # Apply configuration using the config manager
        for section, settings in production_config.items():
            if isinstance(settings, dict):
                for key, value in settings.items():
                    config_path = f"{section}.{key}"
                    self.config_manager.set(config_path, value)
                    print(f"   Set {config_path} = {value}")
            else:
                self.config_manager.set(section, settings)
                print(f"   Set {section} = {settings}")
        
        # Validate configuration
        print("\n✅ Validating production configuration...")
        is_valid, errors = self.config_manager.validate()
        
        if is_valid:
            print("   ✅ Configuration is valid!")
        else:
            print("   ❌ Configuration errors:")
            for error in errors:
                print(f"      - {error}")
        
        # Save production configuration
        config_file = "examples/production_config.yaml"
        if self.config_manager.save(config_file):
            print(f"   📁 Production config saved to: {config_file}")
        
        # Display key production settings
        print("\n📊 Key Production Settings:")
        key_settings = [
            ("Rate Limit", "search.rate_limit_rpm"),
            ("Max Workers", "processing.max_workers"),
            ("Batch Size", "processing.batch_size"),
            ("Memory Limit", "performance.memory.max_memory_mb"),
            ("Log Level", "logging.log_level"),
            ("Metrics Enabled", "enable_metrics")
        ]
        
        for name, path in key_settings:
            value = self.config_manager.get(path)
            print(f"   {name}: {value}")
    
    def example_2_domain_specific_configuration(self):
        """
        Example 2: Domain-specific configuration and overrides
        
        Shows how to configure different behavior for different domains.
        """
        print("\n" + "="*60)
        print("🌐 EXAMPLE 2: Domain-Specific Configuration")
        print("="*60)
        
        # Define domain-specific overrides
        domain_overrides = {
            "bing.com": DomainOverride(
                domain="bing.com",
                browser_mode="headless",
                user_agent_preferences={
                    "prefer_chrome": True,
                    "desktop_only": True,
                    "rotation_enabled": True
                },
                proxy_preferences={
                    "enable_rotation": False,  # More stable for search engines
                    "prefer_residential": True
                },
                delay_config={
                    "base_delay": 4.0,  # Longer delays for search engines
                    "random_factor": 0.8,
                    "human_like_patterns": True
                },
                resource_blocking={
                    "block_images": True,
                    "block_css": True,
                    "block_javascript": False  # May need JS for search
                },
                custom_settings={
                    "max_retries": 5,
                    "timeout": 45,
                    "priority": "high"
                }
            ),
            
            "google.com": DomainOverride(
                domain="google.com",
                browser_mode="headful",  # More human-like for Google
                user_agent_preferences={
                    "prefer_chrome": True,
                    "desktop_only": True,
                    "rotation_enabled": True
                },
                delay_config={
                    "base_delay": 6.0,  # Very conservative for Google
                    "random_factor": 1.2,
                    "human_like_patterns": True
                },
                resource_blocking={
                    "block_images": False,  # Keep images for Google
                    "block_css": False,
                    "block_javascript": False
                },
                custom_settings={
                    "max_retries": 3,
                    "timeout": 60,
                    "priority": "critical"
                }
            ),
            
            "*.com": DomainOverride(  # Business websites
                domain="*.com",
                browser_mode="headless",
                user_agent_preferences={
                    "prefer_chrome": True,
                    "rotation_enabled": False  # Consistent for business sites
                },
                delay_config={
                    "base_delay": 1.5,  # Faster for business sites
                    "random_factor": 0.4
                },
                resource_blocking={
                    "block_images": True,
                    "block_css": True,
                    "block_javascript": True  # Often not needed
                },
                custom_settings={
                    "max_retries": 2,
                    "timeout": 20,
                    "priority": "normal"
                }
            )
        }
        
        print("🔧 Setting up domain-specific configurations...")
        
        # Create anti-detection supervisor with domain overrides
        supervisor_config = {
            "domain_overrides": {
                domain_override.domain: {
                    "browser_mode": domain_override.browser_mode,
                    "user_agent_preferences": domain_override.user_agent_preferences,
                    "proxy_preferences": domain_override.proxy_preferences,
                    "delay_config": domain_override.delay_config,
                    "resource_blocking": domain_override.resource_blocking,
                    "custom_settings": domain_override.custom_settings
                }
                for domain_override in domain_overrides.values()
            }
        }
        
        supervisor = AntiDetectionSupervisor(supervisor_config)
        
        # Test domain classification and configuration
        test_domains = [
            "bing.com",
            "google.com", 
            "medicalpractice.com",
            "lawfirm.org",
            "dentistoffice.net"
        ]
        
        print("\n🧪 Testing domain-specific configurations:")
        
        for domain in test_domains:
            print(f"\n   Domain: {domain}")
            
            # Create session for domain
            try:
                session_config = supervisor.create_session(
                    session_id=f"test_{domain.replace('.', '_')}",
                    domain=domain
                )
                
                print(f"      Browser Mode: {session_config.get('browser_mode', 'default')}")
                print(f"      Has Proxy: {bool(session_config.get('proxy'))}")
                print(f"      Profile Path: {session_config.get('profile_path', 'default')}")
                print(f"      Resource Blocking: {bool(session_config.get('resource_blocking'))}")
                
                # Clean up session
                supervisor.close_session(f"test_{domain.replace('.', '_')}")
                
            except Exception as e:
                print(f"      ❌ Configuration failed: {e}")
        
        # Display statistics
        print(f"\n📊 Anti-Detection Supervisor Statistics:")
        stats = supervisor.get_statistics()
        print(f"   Active sessions: {stats['active_sessions']}")
        print(f"   Domain overrides: {stats['domain_overrides']}")
        print(f"   Component stats available: {len(stats['component_stats'])}")
    
    def example_3_performance_optimization(self):
        """
        Example 3: Advanced performance optimization techniques
        
        Shows memory management, connection pooling, and parallel processing.
        """
        print("\n" + "="*60)
        print("⚡ EXAMPLE 3: Performance Optimization")
        print("="*60)
        
        class PerformanceOptimizedExtractor:
            def __init__(self, max_workers=4, session_pool_size=3):
                self.max_workers = max_workers
                self.session_pool_size = session_pool_size
                self.session_pool = []
                self.session_usage = {}
                self.performance_stats = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'avg_response_time': 0,
                    'memory_usage_mb': 0
                }
                
                # Initialize session pool
                self._initialize_session_pool()
            
            def _initialize_session_pool(self):
                """Initialize pool of reusable browser sessions"""
                print(f"🌐 Initializing session pool with {self.session_pool_size} sessions...")
                
                config = BrowserConfig(
                    mode=BrowserMode.HEADLESS,
                    timeout=20,
                    max_retries=2,
                    block_resources=[
                        "image", "stylesheet", "font", "media",
                        "*.png", "*.jpg", "*.css", "*.mp4"
                    ]
                )
                
                for i in range(self.session_pool_size):
                    try:
                        manager = BrowserManager(config)
                        session = manager.get_browser_session(f"pool_session_{i}")
                        self.session_pool.append(session)
                        self.session_usage[i] = 0
                        print(f"   ✅ Session {i} initialized")
                    except Exception as e:
                        print(f"   ❌ Failed to initialize session {i}: {e}")
            
            def _get_least_used_session(self):
                """Get the least used session from pool"""
                if not self.session_pool:
                    return None
                
                least_used_index = min(self.session_usage.items(), key=lambda x: x[1])[0]
                self.session_usage[least_used_index] += 1
                return self.session_pool[least_used_index]
            
            def extract_parallel(self, urls):
                """Extract data from URLs using parallel processing"""
                print(f"🚀 Starting parallel extraction for {len(urls)} URLs...")
                
                results = []
                failed_urls = []
                
                # Use ThreadPoolExecutor for parallel processing
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit tasks
                    future_to_url = {
                        executor.submit(self._extract_single_url, url): url
                        for url in urls
                    }
                    
                    # Collect results
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            result = future.result(timeout=60)
                            if result['extraction_successful']:
                                results.append(result)
                                print(f"   ✅ {url}")
                            else:
                                failed_urls.append(url)
                                print(f"   ❌ {url}")
                        except Exception as e:
                            failed_urls.append(url)
                            print(f"   💥 {url}: {e}")
                
                return {
                    'successful': results,
                    'failed': failed_urls,
                    'stats': self.performance_stats
                }
            
            def _extract_single_url(self, url):
                """Extract data from single URL with performance tracking"""
                start_time = time.time()
                
                try:
                    # Use session from pool
                    session = self._get_least_used_session()
                    if not session:
                        raise Exception("No available sessions in pool")
                    
                    # Mock extraction (replace with actual extraction logic)
                    session.get(url)
                    time.sleep(0.5)  # Simulate processing time
                    
                    # Update performance stats
                    self.performance_stats['total_requests'] += 1
                    self.performance_stats['successful_requests'] += 1
                    
                    response_time = time.time() - start_time
                    self.performance_stats['avg_response_time'] = (
                        (self.performance_stats['avg_response_time'] * 
                         (self.performance_stats['successful_requests'] - 1) + response_time) /
                        self.performance_stats['successful_requests']
                    )
                    
                    return {
                        'url': url,
                        'extraction_successful': True,
                        'response_time': response_time,
                        'business_name': f"Business at {url}",
                        'emails': ['contact@example.com'],
                        'phones': ['(555) 123-4567']
                    }
                    
                except Exception as e:
                    self.performance_stats['total_requests'] += 1
                    return {
                        'url': url,
                        'extraction_successful': False,
                        'error': str(e)
                    }
            
            def cleanup(self):
                """Clean up session pool"""
                print("🧹 Cleaning up session pool...")
                for i, session in enumerate(self.session_pool):
                    try:
                        session.quit()
                        print(f"   ✅ Session {i} closed")
                    except:
                        print(f"   ⚠️  Session {i} cleanup failed")
                
                self.session_pool.clear()
                self.session_usage.clear()
        
        # Test performance optimization
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://httpbin.org/xml",
            "https://httpbin.org/robots.txt",
            "https://httpbin.org/user-agent"
        ]
        
        extractor = PerformanceOptimizedExtractor(max_workers=3, session_pool_size=2)
        
        try:
            start_time = time.time()
            results = extractor.extract_parallel(test_urls)
            total_time = time.time() - start_time
            
            print(f"\n📊 Performance Results:")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Successful extractions: {len(results['successful'])}")
            print(f"   Failed extractions: {len(results['failed'])}")
            print(f"   Success rate: {len(results['successful'])/len(test_urls)*100:.1f}%")
            print(f"   Average response time: {results['stats']['avg_response_time']:.2f}s")
            print(f"   Throughput: {len(test_urls)/total_time:.2f} URLs/second")
            
        finally:
            extractor.cleanup()
    
    def example_4_advanced_agent_configuration(self):
        """
        Example 4: Advanced agent configuration and customization
        
        Shows how to create custom agents with specialized configurations.
        """
        print("\n" + "="*60)
        print("🤖 EXAMPLE 4: Advanced Agent Configuration")
        print("="*60)
        
        # Custom agent configurations for different use cases
        agent_configs = {
            "high_performance": AgentConfig(
                name="HighPerformanceAgent",
                description="Optimized for speed and throughput",
                model="gpt-3.5-turbo",
                temperature=0.3,
                max_retries=2,
                retry_delay=1.0,
                enable_metrics=True,
                enable_caching=True,
                log_level="WARNING"
            ),
            
            "high_accuracy": AgentConfig(
                name="HighAccuracyAgent", 
                description="Optimized for accuracy and quality",
                model="gpt-4-turbo-preview",
                temperature=0.1,
                max_retries=5,
                retry_delay=3.0,
                enable_metrics=True,
                enable_caching=False,
                log_level="DEBUG"
            ),
            
            "balanced": AgentConfig(
                name="BalancedAgent",
                description="Balanced performance and accuracy",
                model="gpt-3.5-turbo",
                temperature=0.5,
                max_retries=3,
                retry_delay=2.0,
                enable_metrics=True,
                enable_caching=True,
                log_level="INFO"
            )
        }
        
        print("🔧 Creating specialized agents...")
        
        # Create and test agents
        for agent_type, config in agent_configs.items():
            print(f"\n   Agent Type: {agent_type}")
            print(f"      Name: {config.name}")
            print(f"      Model: {config.model}")
            print(f"      Temperature: {config.temperature}")
            print(f"      Max Retries: {config.max_retries}")
            print(f"      Caching: {config.enable_caching}")
            print(f"      Log Level: {config.log_level}")
            
            # Mock agent usage metrics
            mock_metrics = {
                "total_requests": 100,
                "successful_requests": 85 if agent_type == "high_performance" else 95 if agent_type == "high_accuracy" else 90,
                "average_response_time": 0.5 if agent_type == "high_performance" else 2.0 if agent_type == "high_accuracy" else 1.0,
                "success_rate": 0.85 if agent_type == "high_performance" else 0.95 if agent_type == "high_accuracy" else 0.90
            }
            
            print(f"      Performance Metrics:")
            print(f"         Success Rate: {mock_metrics['success_rate']*100:.1f}%")
            print(f"         Avg Response Time: {mock_metrics['average_response_time']:.1f}s")
            print(f"         Throughput: {100/mock_metrics['average_response_time']:.1f} requests/min")
        
        # Agent selection recommendation
        print(f"\n🎯 Agent Selection Recommendations:")
        print(f"   High Performance: Use for large-scale scraping (1000+ URLs)")
        print(f"   High Accuracy: Use for critical data extraction (medical, legal)")
        print(f"   Balanced: Use for general-purpose lead generation")
    
    def example_5_monitoring_and_alerting(self):
        """
        Example 5: Advanced monitoring and alerting system
        
        Shows how to implement comprehensive monitoring with alerts.
        """
        print("\n" + "="*60)
        print("📊 EXAMPLE 5: Monitoring and Alerting")
        print("="*60)
        
        class AdvancedMonitoringSystem:
            def __init__(self):
                self.metrics = {
                    'requests_total': 0,
                    'requests_successful': 0,
                    'requests_failed': 0,
                    'requests_blocked': 0,
                    'avg_response_time': 0,
                    'memory_usage_mb': 0,
                    'cpu_usage_percent': 0
                }
                
                self.alerts = {
                    'high_failure_rate': {'threshold': 0.3, 'triggered': False},
                    'high_block_rate': {'threshold': 0.2, 'triggered': False},
                    'slow_response_time': {'threshold': 5.0, 'triggered': False},
                    'high_memory_usage': {'threshold': 2048, 'triggered': False}
                }
                
                self.performance_history = []
            
            def record_request(self, success=True, blocked=False, response_time=1.0):
                """Record a request and update metrics"""
                self.metrics['requests_total'] += 1
                
                if blocked:
                    self.metrics['requests_blocked'] += 1
                elif success:
                    self.metrics['requests_successful'] += 1
                else:
                    self.metrics['requests_failed'] += 1
                
                # Update average response time
                total_successful = self.metrics['requests_successful']
                if total_successful > 0:
                    self.metrics['avg_response_time'] = (
                        (self.metrics['avg_response_time'] * (total_successful - 1) + response_time) /
                        total_successful
                    )
                
                # Mock system metrics
                import random
                self.metrics['memory_usage_mb'] = random.randint(500, 3000)
                self.metrics['cpu_usage_percent'] = random.randint(20, 90)
                
                # Check alerts
                self._check_alerts()
                
                # Store performance snapshot
                self.performance_history.append({
                    'timestamp': time.time(),
                    'metrics': self.metrics.copy()
                })
                
                # Keep only last 100 snapshots
                if len(self.performance_history) > 100:
                    self.performance_history = self.performance_history[-100:]
            
            def _check_alerts(self):
                """Check alert conditions and trigger alerts"""
                total_requests = self.metrics['requests_total']
                
                if total_requests < 10:  # Need minimum data
                    return
                
                # High failure rate alert
                failure_rate = self.metrics['requests_failed'] / total_requests
                if failure_rate > self.alerts['high_failure_rate']['threshold']:
                    if not self.alerts['high_failure_rate']['triggered']:
                        self._trigger_alert('high_failure_rate', f"Failure rate: {failure_rate*100:.1f}%")
                        self.alerts['high_failure_rate']['triggered'] = True
                else:
                    self.alerts['high_failure_rate']['triggered'] = False
                
                # High block rate alert
                block_rate = self.metrics['requests_blocked'] / total_requests
                if block_rate > self.alerts['high_block_rate']['threshold']:
                    if not self.alerts['high_block_rate']['triggered']:
                        self._trigger_alert('high_block_rate', f"Block rate: {block_rate*100:.1f}%")
                        self.alerts['high_block_rate']['triggered'] = True
                else:
                    self.alerts['high_block_rate']['triggered'] = False
                
                # Slow response time alert
                avg_time = self.metrics['avg_response_time']
                if avg_time > self.alerts['slow_response_time']['threshold']:
                    if not self.alerts['slow_response_time']['triggered']:
                        self._trigger_alert('slow_response_time', f"Avg response time: {avg_time:.2f}s")
                        self.alerts['slow_response_time']['triggered'] = True
                else:
                    self.alerts['slow_response_time']['triggered'] = False
                
                # High memory usage alert
                memory_mb = self.metrics['memory_usage_mb']
                if memory_mb > self.alerts['high_memory_usage']['threshold']:
                    if not self.alerts['high_memory_usage']['triggered']:
                        self._trigger_alert('high_memory_usage', f"Memory usage: {memory_mb}MB")
                        self.alerts['high_memory_usage']['triggered'] = True
                else:
                    self.alerts['high_memory_usage']['triggered'] = False
            
            def _trigger_alert(self, alert_type, message):
                """Trigger an alert"""
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"🚨 ALERT [{timestamp}] {alert_type.upper()}: {message}")
            
            def get_dashboard(self):
                """Get monitoring dashboard data"""
                total = self.metrics['requests_total']
                success_rate = (self.metrics['requests_successful'] / total * 100) if total > 0 else 0
                failure_rate = (self.metrics['requests_failed'] / total * 100) if total > 0 else 0
                block_rate = (self.metrics['requests_blocked'] / total * 100) if total > 0 else 0
                
                return {
                    'summary': {
                        'total_requests': total,
                        'success_rate': f"{success_rate:.1f}%",
                        'failure_rate': f"{failure_rate:.1f}%",
                        'block_rate': f"{block_rate:.1f}%",
                        'avg_response_time': f"{self.metrics['avg_response_time']:.2f}s"
                    },
                    'system': {
                        'memory_usage': f"{self.metrics['memory_usage_mb']}MB",
                        'cpu_usage': f"{self.metrics['cpu_usage_percent']}%"
                    },
                    'alerts': {
                        name: alert['triggered'] for name, alert in self.alerts.items()
                    }
                }
        
        # Test monitoring system
        print("🔧 Setting up monitoring system...")
        monitor = AdvancedMonitoringSystem()
        
        print("\n📈 Simulating requests and monitoring...")
        
        # Simulate various request scenarios
        scenarios = [
            # Normal operation
            *[(True, False, 1.0) for _ in range(20)],
            # Some failures
            *[(False, False, 2.0) for _ in range(5)],
            # Some blocks
            *[(False, True, 0.5) for _ in range(3)],
            # Slow responses
            *[(True, False, 6.0) for _ in range(4)],
            # More normal operation
            *[(True, False, 1.5) for _ in range(10)]
        ]
        
        for i, (success, blocked, response_time) in enumerate(scenarios):
            monitor.record_request(success, blocked, response_time)
            
            # Show dashboard every 10 requests
            if (i + 1) % 10 == 0:
                print(f"\n📊 Dashboard Update (Request {i + 1}):")
                dashboard = monitor.get_dashboard()
                
                print(f"   Summary:")
                for key, value in dashboard['summary'].items():
                    print(f"      {key.replace('_', ' ').title()}: {value}")
                
                print(f"   System:")
                for key, value in dashboard['system'].items():
                    print(f"      {key.replace('_', ' ').title()}: {value}")
                
                active_alerts = [name for name, triggered in dashboard['alerts'].items() if triggered]
                if active_alerts:
                    print(f"   Active Alerts: {', '.join(active_alerts)}")
                else:
                    print(f"   Active Alerts: None")
        
        print(f"\n✅ Monitoring simulation completed!")
        final_dashboard = monitor.get_dashboard()
        print(f"Final Success Rate: {final_dashboard['summary']['success_rate']}")
    
    def example_6_async_processing(self):
        """
        Example 6: Asynchronous processing for high-performance extraction
        
        Shows how to use asyncio for concurrent processing.
        """
        print("\n" + "="*60)
        print("⚡ EXAMPLE 6: Asynchronous Processing")
        print("="*60)
        
        async def async_extraction_example():
            """Demonstrate asynchronous extraction processing"""
            
            class AsyncExtractor:
                def __init__(self, max_concurrent=5):
                    self.max_concurrent = max_concurrent
                    self.semaphore = asyncio.Semaphore(max_concurrent)
                    self.session_count = 0
                
                async def extract_url(self, url):
                    """Extract data from a single URL asynchronously"""
                    async with self.semaphore:
                        session_id = self.session_count
                        self.session_count += 1
                        
                        print(f"   🔍 Session {session_id}: Starting {url}")
                        
                        # Simulate async extraction
                        await asyncio.sleep(1 + (session_id % 3))  # Variable processing time
                        
                        # Mock success/failure
                        import random
                        success = random.random() > 0.2  # 80% success rate
                        
                        if success:
                            print(f"   ✅ Session {session_id}: Completed {url}")
                            return {
                                'url': url,
                                'extraction_successful': True,
                                'business_name': f"Business {session_id}",
                                'emails': [f"contact{session_id}@business.com"],
                                'phones': [f"555-{session_id:04d}"]
                            }
                        else:
                            print(f"   ❌ Session {session_id}: Failed {url}")
                            return {
                                'url': url,
                                'extraction_successful': False,
                                'error': 'Simulated failure'
                            }
                
                async def extract_batch(self, urls):
                    """Extract data from multiple URLs concurrently"""
                    print(f"🚀 Starting async extraction for {len(urls)} URLs...")
                    print(f"   Max concurrent sessions: {self.max_concurrent}")
                    
                    # Create tasks for all URLs
                    tasks = [self.extract_url(url) for url in urls]
                    
                    # Wait for all tasks to complete
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    successful = []
                    failed = []
                    
                    for result in results:
                        if isinstance(result, Exception):
                            failed.append({'error': str(result)})
                        elif result.get('extraction_successful'):
                            successful.append(result)
                        else:
                            failed.append(result)
                    
                    return {
                        'successful': successful,
                        'failed': failed,
                        'total': len(urls),
                        'success_rate': len(successful) / len(urls) * 100
                    }
            
            # Test URLs
            test_urls = [
                f"https://business{i}.example.com" for i in range(1, 11)
            ]
            
            # Create async extractor
            extractor = AsyncExtractor(max_concurrent=3)
            
            # Run async extraction
            start_time = time.time()
            results = await extractor.extract_batch(test_urls)
            total_time = time.time() - start_time
            
            # Display results
            print(f"\n📊 Async Processing Results:")
            print(f"   Total URLs: {results['total']}")
            print(f"   Successful: {len(results['successful'])}")
            print(f"   Failed: {len(results['failed'])}")
            print(f"   Success Rate: {results['success_rate']:.1f}%")
            print(f"   Total Time: {total_time:.2f}s")
            print(f"   Throughput: {results['total']/total_time:.2f} URLs/second")
            
            # Show sample results
            if results['successful']:
                print(f"\n📋 Sample Successful Extractions:")
                for result in results['successful'][:3]:
                    print(f"      {result['business_name']} - {result['emails'][0]}")
        
        # Run async example
        print("🔧 Setting up async processing...")
        try:
            asyncio.run(async_extraction_example())
        except Exception as e:
            print(f"❌ Async processing failed: {e}")
    
    def run_all_examples(self):
        """Run all advanced configuration examples"""
        examples = [
            ("Production Configuration", self.example_1_production_configuration),
            ("Domain-Specific Configuration", self.example_2_domain_specific_configuration),
            ("Performance Optimization", self.example_3_performance_optimization),
            ("Advanced Agent Configuration", self.example_4_advanced_agent_configuration),
            ("Monitoring and Alerting", self.example_5_monitoring_and_alerting),
            ("Asynchronous Processing", self.example_6_async_processing)
        ]
        
        print("🚀 PUBSCRAPE ADVANCED CONFIGURATION EXAMPLES")
        print("These examples demonstrate advanced patterns and optimizations.")
        
        # Check API key
        if not os.getenv('OPENAI_API_KEY'):
            print("\n❌ ERROR: OPENAI_API_KEY environment variable not set")
            print("Some examples may not work without proper API configuration.")
        else:
            print("\n✅ OpenAI API key detected")
        
        print(f"\nRunning {len(examples)} advanced examples...")
        
        for i, (name, example_func) in enumerate(examples, 1):
            try:
                print(f"\n{'='*80}")
                print(f"RUNNING ADVANCED EXAMPLE {i}/{len(examples)}: {name}")
                print('='*80)
                
                example_func()
                
                print(f"\n✅ Advanced example {i} completed successfully!")
                
                if i < len(examples):
                    print("\n⏳ Waiting 2 seconds before next example...")
                    time.sleep(2)
                
            except KeyboardInterrupt:
                print(f"\n🛑 Examples interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Advanced example {i} failed: {e}")
                import traceback
                traceback.print_exc()
                print("Continuing with next example...")
        
        print(f"\n🎉 All advanced examples completed!")
        print("\nThese examples show production-ready patterns for:")
        print("  • High-performance lead generation")
        print("  • Scalable multi-agent architectures") 
        print("  • Advanced monitoring and alerting")
        print("  • Domain-specific optimizations")


def main():
    """Main function to run advanced configuration examples"""
    examples = AdvancedConfigurationExamples()
    examples.run_all_examples()


if __name__ == "__main__":
    main()