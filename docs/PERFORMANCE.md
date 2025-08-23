# Performance Tuning Guide - PubScrape Infinite Scroll Scraper System

## Table of Contents

1. [Performance Overview](#performance-overview)
2. [System Requirements](#system-requirements)
3. [Rate Limiting Optimization](#rate-limiting-optimization)
4. [Browser Performance](#browser-performance)
5. [Memory Management](#memory-management)
6. [CPU Optimization](#cpu-optimization)
7. [Network Optimization](#network-optimization)
8. [Scaling Strategies](#scaling-strategies)
9. [Monitoring and Metrics](#monitoring-and-metrics)
10. [Configuration Tuning](#configuration-tuning)

## Performance Overview

### Current Performance Metrics

| Metric | Low Volume | Medium Volume | High Volume |
|--------|------------|---------------|-------------|
| **Throughput** | 200-300 leads/hour | 500-800 leads/hour | 1000-1500 leads/hour |
| **Success Rate** | 90-95% | 85-90% | 80-85% |
| **Memory Usage** | 1-2GB | 2-4GB | 4-8GB |
| **CPU Usage** | 30-50% | 50-70% | 70-90% |
| **Block Rate** | <5% | 5-10% | 10-15% |

### Performance Targets

- **Primary Goal**: 1000+ leads per hour with 85%+ success rate
- **Memory Efficiency**: <4GB RAM usage for 1000 leads/hour
- **CPU Efficiency**: <80% CPU usage under normal load
- **Anti-Detection**: <10% block rate even at high volume
- **Reliability**: 99%+ uptime during extraction campaigns

## System Requirements

### Minimum Requirements (Development)

```yaml
hardware:
  cpu: 2 cores, 2.5GHz
  memory: 4GB RAM
  storage: 10GB SSD
  network: 10Mbps

software:
  python: 3.8+
  chrome: Latest stable
  os: Windows 10/Linux Ubuntu 18+/macOS 10.15+
```

### Recommended Requirements (Production)

```yaml
hardware:
  cpu: 8 cores, 3.0GHz
  memory: 16GB RAM
  storage: 50GB SSD
  network: 100Mbps

software:
  python: 3.11+
  chrome: Latest stable
  os: Linux Ubuntu 20+/Docker
```

### High-Performance Requirements (Scale)

```yaml
hardware:
  cpu: 16+ cores, 3.5GHz
  memory: 32GB+ RAM
  storage: 100GB+ NVMe SSD
  network: 1Gbps

infrastructure:
  load_balancer: Nginx/HAProxy
  database: PostgreSQL cluster
  cache: Redis cluster
  monitoring: Prometheus + Grafana
```

## Rate Limiting Optimization

### Adaptive Rate Limiting

```python
class AdaptiveRateManager:
    def __init__(self, initial_rpm=12, target_success_rate=0.9):
        self.base_rpm = initial_rpm
        self.current_rpm = initial_rpm
        self.target_success_rate = target_success_rate
        self.success_window = []
        self.window_size = 50
        self.adjustment_factor = 1.2
        
    def record_result(self, success: bool):
        """Record request result and adjust rate if needed"""
        self.success_window.append(success)
        
        # Keep only recent results
        if len(self.success_window) > self.window_size:
            self.success_window.pop(0)
        
        # Adjust rate every 10 requests
        if len(self.success_window) >= 10 and len(self.success_window) % 10 == 0:
            self._adjust_rate()
    
    def _adjust_rate(self):
        """Adjust rate based on recent success rate"""
        recent_success_rate = sum(self.success_window[-10:]) / 10
        
        if recent_success_rate > self.target_success_rate:
            # Increase rate if doing well
            new_rpm = min(self.current_rpm * self.adjustment_factor, self.base_rpm * 3)
            if new_rpm != self.current_rpm:
                print(f"📈 Increasing rate: {self.current_rpm:.1f} → {new_rpm:.1f} RPM")
                self.current_rpm = new_rpm
        
        elif recent_success_rate < self.target_success_rate * 0.8:
            # Decrease rate if too many failures
            new_rpm = max(self.current_rpm / self.adjustment_factor, self.base_rpm * 0.3)
            if new_rpm != self.current_rpm:
                print(f"📉 Decreasing rate: {self.current_rpm:.1f} → {new_rpm:.1f} RPM")
                self.current_rpm = new_rpm
    
    def get_delay(self) -> float:
        """Get current delay between requests"""
        return 60.0 / self.current_rpm if self.current_rpm > 0 else 5.0
    
    def get_stats(self) -> dict:
        """Get current rate limiting statistics"""
        if self.success_window:
            recent_success_rate = sum(self.success_window[-10:]) / min(10, len(self.success_window))
        else:
            recent_success_rate = 0
        
        return {
            'current_rpm': self.current_rpm,
            'recent_success_rate': recent_success_rate,
            'total_requests': len(self.success_window),
            'adjustment_ratio': self.current_rpm / self.base_rpm
        }
```

### Domain-Specific Rate Limiting

```python
class DomainRateManager:
    def __init__(self):
        self.domain_rates = {}
        self.domain_stats = {}
        
        # Default rates by domain type
        self.default_rates = {
            'search_engines': {'rpm': 8, 'burst': 3},
            'business_sites': {'rpm': 15, 'burst': 5},
            'social_media': {'rpm': 5, 'burst': 2},
            'government': {'rpm': 3, 'burst': 1}
        }
    
    def classify_domain(self, domain: str) -> str:
        """Classify domain type for appropriate rate limiting"""
        domain_lower = domain.lower()
        
        if any(engine in domain_lower for engine in ['bing.com', 'google.com', 'duckduckgo.com']):
            return 'search_engines'
        elif any(social in domain_lower for social in ['facebook.com', 'linkedin.com', 'twitter.com']):
            return 'social_media'
        elif domain_lower.endswith('.gov') or domain_lower.endswith('.mil'):
            return 'government'
        else:
            return 'business_sites'
    
    def get_rate_for_domain(self, domain: str) -> dict:
        """Get appropriate rate limit for domain"""
        if domain not in self.domain_rates:
            domain_type = self.classify_domain(domain)
            self.domain_rates[domain] = self.default_rates[domain_type].copy()
            self.domain_stats[domain] = {'requests': 0, 'failures': 0, 'blocks': 0}
        
        return self.domain_rates[domain]
    
    def record_domain_result(self, domain: str, success: bool, blocked: bool = False):
        """Record result for domain-specific rate adjustment"""
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {'requests': 0, 'failures': 0, 'blocks': 0}
        
        stats = self.domain_stats[domain]
        stats['requests'] += 1
        
        if blocked:
            stats['blocks'] += 1
            # Immediately reduce rate for blocked domains
            current_rate = self.domain_rates.get(domain, {'rpm': 10})
            self.domain_rates[domain] = {'rpm': max(current_rate['rpm'] * 0.5, 1), 'burst': 1}
            print(f"🚫 Domain blocked, reducing rate for {domain}: {self.domain_rates[domain]['rpm']:.1f} RPM")
        
        elif not success:
            stats['failures'] += 1
            
            # Adjust rate based on failure rate
            if stats['requests'] >= 10:
                failure_rate = stats['failures'] / stats['requests']
                if failure_rate > 0.3:  # 30% failure rate
                    current_rate = self.domain_rates[domain]
                    new_rpm = max(current_rate['rpm'] * 0.8, 2)
                    self.domain_rates[domain]['rpm'] = new_rpm
```

### Burst Rate Management

```python
class BurstRateController:
    def __init__(self, sustained_rpm=12, burst_rpm=30, burst_duration=10):
        self.sustained_rpm = sustained_rpm
        self.burst_rpm = burst_rpm
        self.burst_duration = burst_duration
        
        self.request_times = []
        self.burst_start = None
        self.burst_remaining = burst_duration
    
    def can_make_request(self) -> bool:
        """Check if request can be made based on burst/sustained limits"""
        now = time.time()
        
        # Clean old requests (older than 1 minute)
        minute_ago = now - 60
        self.request_times = [t for t in self.request_times if t > minute_ago]
        
        # Check if we're in burst mode
        if self.burst_remaining > 0:
            # Can make burst requests
            if len(self.request_times) < self.burst_rpm:
                return True
            else:
                # Burst rate exceeded, switch to sustained mode
                self.burst_remaining = 0
                return len(self.request_times) < self.sustained_rpm
        else:
            # Sustained mode
            return len(self.request_times) < self.sustained_rpm
    
    def record_request(self):
        """Record a request and update burst status"""
        now = time.time()
        self.request_times.append(now)
        
        if self.burst_start is None:
            self.burst_start = now
        
        # Check if burst period is over
        if self.burst_start and (now - self.burst_start) > self.burst_duration:
            self.burst_remaining = 0
    
    def reset_burst(self):
        """Reset burst allowance (call after successful batch)"""
        self.burst_start = None
        self.burst_remaining = self.burst_duration
        print(f"🚀 Burst mode reset: {self.burst_rpm} RPM for {self.burst_duration}s")
```

## Browser Performance

### Optimized Browser Configuration

```python
def create_high_performance_browser_config():
    """Create optimized browser configuration for high performance"""
    
    chrome_options = [
        # Performance optimizations
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-features=TranslateUI',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-images',
        '--disable-javascript',  # If scraping doesn't need JS
        
        # Memory optimizations
        '--memory-pressure-off',
        '--max_old_space_size=4096',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        
        # Network optimizations
        '--aggressive-cache-discard',
        '--disable-background-networking',
        '--disable-default-apps',
        '--disable-sync',
        
        # Security (can be disabled for performance)
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        
        # Window and display
        '--window-size=1280,720',  # Smaller window for less memory
        '--headless=new',  # Use new headless mode
    ]
    
    # Resource blocking
    block_resources = [
        'stylesheet', 'image', 'media', 'font', 'texttrack', 
        'object', 'beacon', 'csp_report', 'imageset'
    ]
    
    return BrowserConfig(
        mode=BrowserMode.HEADLESS,
        chrome_options=chrome_options,
        block_resources=block_resources,
        timeout=20,  # Shorter timeout for faster failures
        page_load_strategy='eager',  # Don't wait for all resources
        max_retries=2  # Fewer retries for faster processing
    )
```

### Browser Session Pooling

```python
class BrowserSessionPool:
    def __init__(self, pool_size=5, session_lifetime=100):
        self.pool_size = pool_size
        self.session_lifetime = session_lifetime
        self.sessions = {}
        self.session_usage = {}
        self.session_created = {}
        self.lock = threading.Lock()
    
    def get_session(self, domain_hint=None):
        """Get an optimized browser session from pool"""
        with self.lock:
            # Clean up expired sessions
            self._cleanup_expired_sessions()
            
            # Find least used session
            available_sessions = [
                sid for sid, usage in self.session_usage.items()
                if usage < self.session_lifetime
            ]
            
            if available_sessions:
                # Use existing session
                session_id = min(available_sessions, key=lambda x: self.session_usage[x])
            elif len(self.sessions) < self.pool_size:
                # Create new session
                session_id = f"pool_session_{len(self.sessions)}_{int(time.time())}"
                self._create_session(session_id)
            else:
                # Replace oldest session
                oldest_session = min(self.session_created.items(), key=lambda x: x[1])[0]
                self._replace_session(oldest_session)
                session_id = oldest_session
            
            # Update usage
            self.session_usage[session_id] += 1
            
            return self.sessions[session_id]
    
    def _create_session(self, session_id):
        """Create a new browser session"""
        config = create_high_performance_browser_config()
        manager = BrowserManager(config)
        
        self.sessions[session_id] = manager.get_browser_session(session_id)
        self.session_usage[session_id] = 0
        self.session_created[session_id] = time.time()
        
        print(f"🌐 Created browser session: {session_id}")
    
    def _replace_session(self, session_id):
        """Replace an existing session"""
        try:
            old_session = self.sessions[session_id]
            old_session.quit()
        except:
            pass
        
        self._create_session(session_id)
        print(f"🔄 Replaced browser session: {session_id}")
    
    def _cleanup_expired_sessions(self):
        """Clean up sessions that have exceeded their lifetime"""
        expired_sessions = [
            sid for sid, usage in self.session_usage.items()
            if usage >= self.session_lifetime
        ]
        
        for session_id in expired_sessions:
            self._replace_session(session_id)
    
    def get_pool_stats(self):
        """Get pool statistics"""
        return {
            'active_sessions': len(self.sessions),
            'total_usage': sum(self.session_usage.values()),
            'average_usage': sum(self.session_usage.values()) / len(self.sessions) if self.sessions else 0,
            'pool_utilization': len(self.sessions) / self.pool_size
        }
```

### Page Load Optimization

```python
class OptimizedPageLoader:
    def __init__(self, driver):
        self.driver = driver
        self.load_strategies = {
            'fast': self._fast_load,
            'minimal': self._minimal_load,
            'full': self._full_load
        }
    
    def load_page(self, url, strategy='fast', timeout=20):
        """Load page with specified optimization strategy"""
        start_time = time.time()
        
        try:
            result = self.load_strategies[strategy](url, timeout)
            load_time = time.time() - start_time
            
            print(f"⚡ Page loaded in {load_time:.2f}s using {strategy} strategy")
            return result
            
        except Exception as e:
            load_time = time.time() - start_time
            print(f"❌ Page load failed after {load_time:.2f}s: {e}")
            raise
    
    def _fast_load(self, url, timeout):
        """Fast loading with minimal resource loading"""
        # Set page load strategy to 'none' for immediate return
        self.driver.execute_cdp_cmd('Page.enable', {})
        self.driver.execute_cdp_cmd('Page.setLifecycleEventsEnabled', {'enabled': True})
        
        # Navigate
        self.driver.get(url)
        
        # Wait for basic DOM ready
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") != "loading"
        )
        
        return {'strategy': 'fast', 'status': 'success'}
    
    def _minimal_load(self, url, timeout):
        """Minimal loading - wait for DOM content loaded"""
        self.driver.get(url)
        
        # Wait for DOM content loaded
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") in ["interactive", "complete"]
        )
        
        return {'strategy': 'minimal', 'status': 'success'}
    
    def _full_load(self, url, timeout):
        """Full loading - wait for all resources"""
        self.driver.get(url)
        
        # Wait for complete page load
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        return {'strategy': 'full', 'status': 'success'}
```

## Memory Management

### Memory Monitoring and Cleanup

```python
import gc
import psutil
import weakref

class MemoryManager:
    def __init__(self, max_memory_mb=4096, cleanup_threshold=0.8):
        self.max_memory_mb = max_memory_mb
        self.cleanup_threshold = cleanup_threshold
        self.process = psutil.Process()
        self.object_registry = weakref.WeakSet()
        
    def get_memory_info(self):
        """Get detailed memory information"""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': memory_percent,
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
            'usage_ratio': memory_info.rss / (self.max_memory_mb * 1024 * 1024)
        }
    
    def should_cleanup(self):
        """Check if memory cleanup is needed"""
        info = self.get_memory_info()
        return info['usage_ratio'] > self.cleanup_threshold
    
    def force_cleanup(self):
        """Force aggressive memory cleanup"""
        print("🧹 Starting aggressive memory cleanup...")
        
        initial_memory = self.get_memory_info()['rss_mb']
        
        # Clear weak references
        self.object_registry.clear()
        
        # Multiple garbage collection passes
        for i in range(3):
            collected = gc.collect()
            print(f"   GC pass {i+1}: collected {collected} objects")
        
        # Force garbage collection of all generations
        for generation in range(3):
            gc.collect(generation)
        
        final_memory = self.get_memory_info()['rss_mb']
        freed = initial_memory - final_memory
        
        print(f"✅ Memory cleanup completed: freed {freed:.1f}MB")
        return freed
    
    def register_object(self, obj):
        """Register object for cleanup tracking"""
        self.object_registry.add(obj)
    
    def memory_context(self):
        """Context manager for memory monitoring"""
        return MemoryContext(self)

class MemoryContext:
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.start_memory = None
    
    def __enter__(self):
        self.start_memory = self.memory_manager.get_memory_info()['rss_mb']
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_memory = self.memory_manager.get_memory_info()['rss_mb']
        memory_delta = end_memory - self.start_memory
        
        if memory_delta > 100:  # More than 100MB increase
            print(f"⚠️  High memory usage in context: +{memory_delta:.1f}MB")
            if self.memory_manager.should_cleanup():
                self.memory_manager.force_cleanup()
```

### Object Pool Management

```python
class ObjectPool:
    def __init__(self, factory_func, max_size=10, cleanup_func=None):
        self.factory_func = factory_func
        self.cleanup_func = cleanup_func
        self.max_size = max_size
        self.pool = []
        self.active_objects = set()
        self.lock = threading.Lock()
    
    def acquire(self):
        """Acquire object from pool or create new one"""
        with self.lock:
            if self.pool:
                obj = self.pool.pop()
                self.active_objects.add(id(obj))
                return obj
            else:
                obj = self.factory_func()
                self.active_objects.add(id(obj))
                return obj
    
    def release(self, obj):
        """Release object back to pool"""
        with self.lock:
            obj_id = id(obj)
            if obj_id in self.active_objects:
                self.active_objects.remove(obj_id)
                
                if len(self.pool) < self.max_size:
                    # Reset object state if needed
                    if hasattr(obj, 'reset'):
                        obj.reset()
                    self.pool.append(obj)
                else:
                    # Pool is full, cleanup object
                    if self.cleanup_func:
                        self.cleanup_func(obj)
    
    def cleanup_all(self):
        """Cleanup all objects in pool"""
        with self.lock:
            if self.cleanup_func:
                for obj in self.pool:
                    self.cleanup_func(obj)
            self.pool.clear()
            self.active_objects.clear()
    
    def get_stats(self):
        """Get pool statistics"""
        with self.lock:
            return {
                'pool_size': len(self.pool),
                'active_objects': len(self.active_objects),
                'total_capacity': self.max_size,
                'utilization': len(self.active_objects) / self.max_size
            }

# Example usage
def create_browser_session():
    """Factory function for browser sessions"""
    config = create_high_performance_browser_config()
    manager = BrowserManager(config)
    return manager.get_browser_session("pooled_session")

def cleanup_browser_session(session):
    """Cleanup function for browser sessions"""
    try:
        session.quit()
    except:
        pass

# Create browser session pool
browser_pool = ObjectPool(
    factory_func=create_browser_session,
    cleanup_func=cleanup_browser_session,
    max_size=5
)
```

## CPU Optimization

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp

class ParallelProcessor:
    def __init__(self, max_workers=None, use_threads=True):
        self.max_workers = max_workers or mp.cpu_count()
        self.use_threads = use_threads
        self.executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    
    def process_urls_parallel(self, urls, extraction_func, chunk_size=10):
        """Process URLs in parallel with optimal chunking"""
        
        # Split URLs into chunks for better load distribution
        url_chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]
        
        results = []
        failed_urls = []
        
        with self.executor_class(max_workers=self.max_workers) as executor:
            # Submit chunk processing tasks
            future_to_chunk = {
                executor.submit(self._process_chunk, chunk, extraction_func): chunk
                for chunk in url_chunks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result(timeout=300)  # 5 minute timeout per chunk
                    results.extend(chunk_results['success'])
                    failed_urls.extend(chunk_results['failed'])
                    
                    print(f"✅ Processed chunk: {len(chunk_results['success'])} success, "
                          f"{len(chunk_results['failed'])} failed")
                    
                except Exception as e:
                    print(f"❌ Chunk processing failed: {e}")
                    failed_urls.extend([{'url': url, 'error': str(e)} for url in chunk])
        
        return {
            'results': results,
            'failed': failed_urls,
            'total_processed': len(results) + len(failed_urls),
            'success_rate': len(results) / (len(results) + len(failed_urls)) if (len(results) + len(failed_urls)) > 0 else 0
        }
    
    def _process_chunk(self, urls, extraction_func):
        """Process a chunk of URLs"""
        success_results = []
        failed_results = []
        
        for url in urls:
            try:
                result = extraction_func(url)
                if result.get('extraction_successful', False):
                    success_results.append(result)
                else:
                    failed_results.append({'url': url, 'error': result.get('error', 'Unknown error')})
            except Exception as e:
                failed_results.append({'url': url, 'error': str(e)})
        
        return {'success': success_results, 'failed': failed_results}
```

### CPU Load Balancing

```python
class CPULoadBalancer:
    def __init__(self, target_cpu_percent=70):
        self.target_cpu_percent = target_cpu_percent
        self.current_workers = mp.cpu_count() // 2
        self.min_workers = 1
        self.max_workers = mp.cpu_count()
        self.adjustment_interval = 30  # seconds
        self.last_adjustment = time.time()
    
    def get_optimal_workers(self):
        """Get optimal number of workers based on CPU usage"""
        if time.time() - self.last_adjustment < self.adjustment_interval:
            return self.current_workers
        
        # Get current CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Adjust worker count based on CPU usage
        if cpu_percent > self.target_cpu_percent + 10:
            # CPU usage too high, reduce workers
            self.current_workers = max(self.current_workers - 1, self.min_workers)
            print(f"📉 Reducing workers to {self.current_workers} (CPU: {cpu_percent:.1f}%)")
        
        elif cpu_percent < self.target_cpu_percent - 10:
            # CPU usage low, can add more workers
            self.current_workers = min(self.current_workers + 1, self.max_workers)
            print(f"📈 Increasing workers to {self.current_workers} (CPU: {cpu_percent:.1f}%)")
        
        self.last_adjustment = time.time()
        return self.current_workers
    
    def monitor_and_adjust(self, task_queue):
        """Monitor CPU and adjust workers dynamically"""
        while not task_queue.empty():
            optimal_workers = self.get_optimal_workers()
            
            # Implement worker adjustment logic here
            # This would integrate with your parallel processing system
            
            time.sleep(5)  # Check every 5 seconds
```

### Asynchronous Processing

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class AsyncProcessor:
    def __init__(self, max_concurrent=10, thread_pool_size=4):
        self.max_concurrent = max_concurrent
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_urls_async(self, urls, extraction_func):
        """Process URLs asynchronously with concurrency control"""
        
        async def process_single_url(url):
            async with self.semaphore:
                loop = asyncio.get_event_loop()
                try:
                    # Run CPU-bound extraction in thread pool
                    result = await loop.run_in_executor(
                        self.thread_pool, 
                        extraction_func, 
                        url
                    )
                    return result
                except Exception as e:
                    return {'url': url, 'error': str(e), 'extraction_successful': False}
        
        # Create tasks for all URLs
        tasks = [process_single_url(url) for url in urls]
        
        # Process with progress tracking
        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"⚡ Processed {i + 1}/{len(urls)} URLs asynchronously")
        
        return results
    
    async def batch_process_with_delays(self, urls, extraction_func, batch_size=5, delay_between_batches=2):
        """Process URLs in batches with delays between batches"""
        results = []
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            print(f"🔄 Processing batch {i//batch_size + 1}: {len(batch)} URLs")
            
            # Process batch
            batch_results = await self.process_urls_async(batch, extraction_func)
            results.extend(batch_results)
            
            # Delay between batches (except for last batch)
            if i + batch_size < len(urls):
                print(f"⏳ Waiting {delay_between_batches}s before next batch...")
                await asyncio.sleep(delay_between_batches)
        
        return results
```

## Network Optimization

### Connection Pooling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedSession:
    def __init__(self, pool_connections=20, pool_maxsize=20, max_retries=3):
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"]
        )
        
        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set reasonable timeouts
        self.session.timeout = (10, 30)  # (connect, read) timeout
        
        # Common headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get(self, url, **kwargs):
        """Make optimized GET request"""
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {url}: {e}")
            raise
    
    def close(self):
        """Close session and cleanup connections"""
        self.session.close()
```

### DNS Optimization

```python
import socket
import dns.resolver
from functools import lru_cache

class DNSOptimizer:
    def __init__(self, cache_size=1000, timeout=5):
        self.cache_size = cache_size
        self.timeout = timeout
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = timeout
        
        # Configure DNS servers (Google DNS for reliability)
        self.resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
    
    @lru_cache(maxsize=1000)
    def resolve_domain(self, domain):
        """Resolve domain with caching"""
        try:
            result = self.resolver.resolve(domain, 'A')
            return [str(ip) for ip in result]
        except Exception as e:
            print(f"❌ DNS resolution failed for {domain}: {e}")
            return []
    
    def warm_dns_cache(self, domains):
        """Pre-warm DNS cache with common domains"""
        print(f"🔥 Warming DNS cache with {len(domains)} domains...")
        
        for domain in domains:
            try:
                self.resolve_domain(domain)
            except:
                pass
        
        print("✅ DNS cache warmed")
    
    def get_cache_stats(self):
        """Get DNS cache statistics"""
        return {
            'cache_size': self.resolve_domain.cache_info().currsize,
            'cache_hits': self.resolve_domain.cache_info().hits,
            'cache_misses': self.resolve_domain.cache_info().misses,
            'hit_rate': self.resolve_domain.cache_info().hits / (self.resolve_domain.cache_info().hits + self.resolve_domain.cache_info().misses) if (self.resolve_domain.cache_info().hits + self.resolve_domain.cache_info().misses) > 0 else 0
        }
```

## Scaling Strategies

### Horizontal Scaling with Load Distribution

```python
class LoadDistributor:
    def __init__(self, worker_configs):
        self.workers = []
        self.worker_stats = {}
        
        for config in worker_configs:
            worker = {
                'id': config['id'],
                'capacity': config['capacity'],
                'current_load': 0,
                'total_processed': 0,
                'success_rate': 1.0,
                'endpoint': config.get('endpoint'),
                'active': True
            }
            self.workers.append(worker)
            self.worker_stats[worker['id']] = []
    
    def distribute_tasks(self, tasks):
        """Distribute tasks optimally across workers"""
        if not tasks:
            return {}
        
        # Sort workers by availability and performance
        available_workers = [w for w in self.workers if w['active']]
        available_workers.sort(key=lambda w: (w['current_load'] / w['capacity'], -w['success_rate']))
        
        distribution = {worker['id']: [] for worker in available_workers}
        
        # Distribute tasks using round-robin with capacity consideration
        worker_index = 0
        for task in tasks:
            if not available_workers:
                break
            
            # Find next available worker
            attempts = 0
            while attempts < len(available_workers):
                worker = available_workers[worker_index]
                
                if worker['current_load'] < worker['capacity']:
                    distribution[worker['id']].append(task)
                    worker['current_load'] += 1
                    break
                
                worker_index = (worker_index + 1) % len(available_workers)
                attempts += 1
            
            worker_index = (worker_index + 1) % len(available_workers)
        
        return distribution
    
    def record_task_completion(self, worker_id, success=True, processing_time=None):
        """Record task completion for load balancing optimization"""
        worker = next((w for w in self.workers if w['id'] == worker_id), None)
        if not worker:
            return
        
        worker['current_load'] = max(0, worker['current_load'] - 1)
        worker['total_processed'] += 1
        
        # Update success rate (exponential moving average)
        alpha = 0.1  # Smoothing factor
        worker['success_rate'] = (alpha * (1 if success else 0) + 
                                (1 - alpha) * worker['success_rate'])
        
        # Record statistics
        self.worker_stats[worker_id].append({
            'timestamp': time.time(),
            'success': success,
            'processing_time': processing_time
        })
        
        # Keep only recent stats (last 100 tasks)
        if len(self.worker_stats[worker_id]) > 100:
            self.worker_stats[worker_id] = self.worker_stats[worker_id][-100:]
    
    def get_worker_stats(self):
        """Get comprehensive worker statistics"""
        stats = {}
        
        for worker in self.workers:
            worker_id = worker['id']
            recent_stats = self.worker_stats[worker_id][-50:]  # Last 50 tasks
            
            if recent_stats:
                avg_time = sum(s['processing_time'] for s in recent_stats if s['processing_time']) / len([s for s in recent_stats if s['processing_time']])
                recent_success_rate = sum(s['success'] for s in recent_stats) / len(recent_stats)
            else:
                avg_time = 0
                recent_success_rate = worker['success_rate']
            
            stats[worker_id] = {
                'capacity': worker['capacity'],
                'current_load': worker['current_load'],
                'utilization': worker['current_load'] / worker['capacity'],
                'total_processed': worker['total_processed'],
                'overall_success_rate': worker['success_rate'],
                'recent_success_rate': recent_success_rate,
                'average_processing_time': avg_time,
                'active': worker['active']
            }
        
        return stats
```

### Auto-Scaling Configuration

```yaml
# autoscaling.yaml
autoscaling:
  enabled: true
  
  # Scaling triggers
  triggers:
    cpu_threshold: 70          # Scale up if CPU > 70%
    memory_threshold: 80       # Scale up if memory > 80%
    queue_size_threshold: 100  # Scale up if queue > 100 items
    success_rate_threshold: 85 # Scale down if success rate < 85%
  
  # Scaling parameters
  scaling:
    min_instances: 2
    max_instances: 10
    scale_up_increment: 2
    scale_down_increment: 1
    cooldown_period: 300       # seconds
  
  # Instance configuration
  instance:
    cpu: 2
    memory: 4096              # MB
    max_concurrent_tasks: 5
    
  # Monitoring
  monitoring:
    check_interval: 60        # seconds
    metrics_retention: 3600   # seconds
```

## Monitoring and Metrics

### Performance Metrics Collection

```python
import time
import threading
from collections import defaultdict, deque

class PerformanceMonitor:
    def __init__(self, window_size=300):  # 5 minute window
        self.window_size = window_size
        self.metrics = defaultdict(deque)
        self.counters = defaultdict(int)
        self.timers = {}
        self.lock = threading.Lock()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self.cleanup_thread.start()
    
    def record_metric(self, metric_name, value, timestamp=None):
        """Record a metric value with timestamp"""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.metrics[metric_name].append((timestamp, value))
            self._cleanup_metric(metric_name)
    
    def increment_counter(self, counter_name, increment=1):
        """Increment a counter"""
        with self.lock:
            self.counters[counter_name] += increment
    
    def start_timer(self, timer_name):
        """Start a timer"""
        self.timers[timer_name] = time.time()
    
    def end_timer(self, timer_name):
        """End a timer and record duration"""
        if timer_name in self.timers:
            duration = time.time() - self.timers[timer_name]
            self.record_metric(f"{timer_name}_duration", duration)
            del self.timers[timer_name]
            return duration
        return None
    
    def get_metric_stats(self, metric_name):
        """Get statistics for a metric"""
        with self.lock:
            values = [value for _, value in self.metrics[metric_name]]
            
            if not values:
                return None
            
            return {
                'count': len(values),
                'sum': sum(values),
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values),
                'latest': values[-1] if values else None
            }
    
    def get_all_stats(self):
        """Get all metric statistics"""
        stats = {}
        
        with self.lock:
            # Metric statistics
            for metric_name in self.metrics:
                stats[metric_name] = self.get_metric_stats(metric_name)
            
            # Counter values
            stats['counters'] = dict(self.counters)
            
            # System metrics
            stats['system'] = self._get_system_metrics()
        
        return stats
    
    def _cleanup_metric(self, metric_name):
        """Clean up old entries for a specific metric"""
        cutoff_time = time.time() - self.window_size
        metric_deque = self.metrics[metric_name]
        
        while metric_deque and metric_deque[0][0] < cutoff_time:
            metric_deque.popleft()
    
    def _cleanup_old_metrics(self):
        """Periodically clean up old metrics"""
        while True:
            time.sleep(60)  # Clean up every minute
            
            with self.lock:
                for metric_name in list(self.metrics.keys()):
                    self._cleanup_metric(metric_name)
    
    def _get_system_metrics(self):
        """Get current system metrics"""
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'active_threads': threading.active_count(),
            'timestamp': time.time()
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorator for timing functions
def timed(metric_name=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            timer_name = metric_name or f"{func.__name__}_timer"
            performance_monitor.start_timer(timer_name)
            try:
                result = func(*args, **kwargs)
                performance_monitor.increment_counter(f"{func.__name__}_success")
                return result
            except Exception as e:
                performance_monitor.increment_counter(f"{func.__name__}_error")
                raise
            finally:
                performance_monitor.end_timer(timer_name)
        return wrapper
    return decorator
```

### Real-time Dashboard

```python
import json
from datetime import datetime

class PerformanceDashboard:
    def __init__(self, monitor):
        self.monitor = monitor
        self.start_time = time.time()
    
    def get_dashboard_data(self):
        """Get formatted data for dashboard display"""
        stats = self.monitor.get_all_stats()
        
        # Calculate derived metrics
        uptime = time.time() - self.start_time
        total_requests = stats['counters'].get('requests_total', 0)
        successful_requests = stats['counters'].get('extraction_success', 0)
        failed_requests = stats['counters'].get('extraction_error', 0)
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        throughput = (total_requests / uptime * 3600) if uptime > 0 else 0  # per hour
        
        dashboard_data = {
            'overview': {
                'uptime_seconds': uptime,
                'uptime_formatted': self._format_duration(uptime),
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': round(success_rate, 2),
                'throughput_per_hour': round(throughput, 1)
            },
            'performance': {
                'avg_response_time': stats.get('extraction_duration', {}).get('avg', 0),
                'min_response_time': stats.get('extraction_duration', {}).get('min', 0),
                'max_response_time': stats.get('extraction_duration', {}).get('max', 0)
            },
            'system': stats.get('system', {}),
            'counters': stats.get('counters', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        return dashboard_data
    
    def print_dashboard(self):
        """Print dashboard to console"""
        data = self.get_dashboard_data()
        
        print("\n" + "="*60)
        print("📊 PUBSCRAPE PERFORMANCE DASHBOARD")
        print("="*60)
        
        overview = data['overview']
        print(f"⏱️  Uptime: {overview['uptime_formatted']}")
        print(f"📈 Total Requests: {overview['total_requests']:,}")
        print(f"✅ Success Rate: {overview['success_rate']}%")
        print(f"🚀 Throughput: {overview['throughput_per_hour']:.1f} requests/hour")
        
        performance = data['performance']
        print(f"⚡ Avg Response Time: {performance['avg_response_time']:.2f}s")
        
        system = data['system']
        print(f"💾 CPU Usage: {system.get('cpu_percent', 0):.1f}%")
        print(f"🧠 Memory Usage: {system.get('memory_percent', 0):.1f}%")
        
        print("="*60)
    
    def _format_duration(self, seconds):
        """Format duration in human readable format"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def export_metrics(self, filepath):
        """Export metrics to JSON file"""
        data = self.get_dashboard_data()
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📁 Metrics exported to {filepath}")
```

## Configuration Tuning

### Performance Configuration Templates

```yaml
# High Performance Configuration
# config/performance.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}
  openai_model: "gpt-3.5-turbo"  # Faster model
  openai_temperature: 0.5

search:
  max_pages_per_query: 7
  results_per_page: 15
  rate_limit_rpm: 24            # Aggressive rate limiting
  timeout_seconds: 20           # Shorter timeouts
  max_concurrent_searches: 6    # More concurrent operations
  retry_attempts: 2             # Fewer retries for speed
  use_stealth_mode: true
  cache_results: true
  cache_ttl_seconds: 7200       # Longer cache TTL

browser:
  mode: "headless"
  timeout: 20
  max_retries: 2
  window_size: [1280, 720]      # Smaller window
  chrome_options:
    - "--no-sandbox"
    - "--disable-dev-shm-usage"
    - "--disable-gpu"
    - "--disable-images"
    - "--disable-javascript"     # If not needed
    - "--memory-pressure-off"
  
processing:
  batch_size: 200               # Larger batches
  max_workers: 8                # More parallel workers
  validation_enabled: false     # Skip validation for speed
  deduplication_enabled: true

export:
  output_directory: "output"
  include_metadata: false       # Less data to write
  compress_output: true         # Compress for faster I/O

performance:
  memory:
    max_memory_mb: 6144         # Higher memory limit
    cleanup_threshold: 0.9      # More aggressive cleanup
  
  cpu:
    max_workers: 8
    thread_pool_size: 16
  
  network:
    connection_pool_size: 30
    max_retries: 2
    timeout: (5, 15)            # Faster timeouts

logging:
  log_level: "WARNING"          # Less logging overhead
  enable_file_logging: false    # Disable file logging for speed
```

```yaml
# Memory Optimized Configuration
# config/memory_optimized.yaml
api:
  openai_api_key: ${OPENAI_API_KEY}

search:
  max_pages_per_query: 3        # Fewer pages to reduce memory
  rate_limit_rpm: 8             # Conservative rate
  timeout_seconds: 30
  max_concurrent_searches: 2    # Fewer concurrent operations
  cache_results: false          # Disable caching to save memory

browser:
  mode: "headless"
  timeout: 25
  max_retries: 2
  chrome_options:
    - "--no-sandbox"
    - "--disable-dev-shm-usage"
    - "--disable-gpu"
    - "--disable-images"
    - "--disable-extensions"
    - "--disable-plugins"
    - "--memory-pressure-off"
    - "--max_old_space_size=1024"

processing:
  batch_size: 25                # Smaller batches
  max_workers: 2                # Fewer workers
  validation_enabled: true
  deduplication_enabled: true

performance:
  memory:
    max_memory_mb: 2048         # Lower memory limit
    cleanup_threshold: 0.7      # Earlier cleanup
    gc_interval: 50             # More frequent GC
  
  browser:
    session_pool_size: 2        # Smaller session pool
    session_lifetime: 25        # Shorter session life
    
logging:
  log_level: "INFO"
  max_log_size_mb: 10          # Smaller log files
```

This performance tuning guide provides comprehensive strategies for optimizing the PubScrape system across all dimensions - from rate limiting to memory management to scaling strategies. Use the appropriate configuration templates based on your performance requirements and system constraints.