"""
Bulk processing, error handling, and performance optimization module.
Provides batch processing for large-scale podcast discovery operations.
"""

import asyncio
import logging
import time
import json
import pickle
from typing import List, Dict, Any, Optional, Callable, Generator
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
import threading
from queue import Queue, Empty
from dataclasses import dataclass
from datetime import datetime, timedelta

from .base import PodcastData
from .config import config
from .main import PodcastHostScraper

logger = logging.getLogger(__name__)


@dataclass
class ProcessingProgress:
    """Tracks processing progress for bulk operations."""
    total_queries: int = 0
    completed_queries: int = 0
    failed_queries: int = 0
    total_podcasts_found: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    current_query: str = ""
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.completed_queries / self.total_queries) * 100
    
    @property
    def elapsed_time(self) -> timedelta:
        """Calculate elapsed time."""
        if self.start_time is None:
            return timedelta(0)
        return datetime.now() - self.start_time


class IntelligentRateLimiter:
    """Intelligent rate limiting with backoff and domain-specific limits."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.domain_limits = {
            'podcasts.apple.com': 2.0,  # seconds between requests
            'api.spotify.com': 1.0,
            'youtube.com': 1.5,
            'google.com': 1.0,
            'default': 1.0
        }
        self.last_request_time = {}
        self.consecutive_errors = {}
        self.backoff_until = {}
        self.max_consecutive_errors = 3
        self.base_backoff = 10  # seconds
    
    def wait_if_needed(self, domain: str) -> None:
        """Wait if rate limiting is needed for domain."""
        domain = self._normalize_domain(domain)
        
        # Check if we're in backoff period
        if domain in self.backoff_until:
            backoff_until = self.backoff_until[domain]
            if datetime.now() < backoff_until:
                wait_time = (backoff_until - datetime.now()).total_seconds()
                logger.info(f"Rate limiter: waiting {wait_time:.1f}s for {domain} (backoff)")
                time.sleep(wait_time)
                return
            else:
                # Backoff period ended
                del self.backoff_until[domain]
                self.consecutive_errors[domain] = 0
        
        # Standard rate limiting
        if domain in self.last_request_time:
            time_since_last = time.time() - self.last_request_time[domain]
            required_delay = self.domain_limits.get(domain, self.domain_limits['default'])
            
            if time_since_last < required_delay:
                wait_time = required_delay - time_since_last
                logger.debug(f"Rate limiter: waiting {wait_time:.1f}s for {domain}")
                time.sleep(wait_time)
        
        self.last_request_time[domain] = time.time()
    
    def record_error(self, domain: str) -> None:
        """Record an error for backoff calculation."""
        domain = self._normalize_domain(domain)
        
        self.consecutive_errors[domain] = self.consecutive_errors.get(domain, 0) + 1
        
        if self.consecutive_errors[domain] >= self.max_consecutive_errors:
            # Start exponential backoff
            backoff_time = self.base_backoff * (2 ** (self.consecutive_errors[domain] - self.max_consecutive_errors))
            self.backoff_until[domain] = datetime.now() + timedelta(seconds=backoff_time)
            logger.warning(f"Rate limiter: starting {backoff_time}s backoff for {domain}")
    
    def record_success(self, domain: str) -> None:
        """Record a successful request."""
        domain = self._normalize_domain(domain)
        self.consecutive_errors[domain] = 0
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain for consistent tracking."""
        if not domain:
            return 'default'
        # Extract base domain
        if '://' in domain:
            domain = domain.split('://')[1]
        if '/' in domain:
            domain = domain.split('/')[0]
        return domain.lower()


class CacheManager:
    """Intelligent caching for podcast data and API responses."""
    
    def __init__(self, cache_dir: str = "cache"):
        """Initialize cache manager."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}
        self.cache_ttl = {
            'podcast_search': 3600,  # 1 hour
            'contact_info': 86400,   # 24 hours
            'intelligence': 3600,    # 1 hour
            'social_profiles': 86400 # 24 hours
        }
    
    def get(self, cache_type: str, key: str) -> Optional[Any]:
        """Get cached data if valid."""
        # Check memory cache first
        memory_key = f"{cache_type}:{key}"
        if memory_key in self.memory_cache:
            cached_data, timestamp = self.memory_cache[memory_key]
            if time.time() - timestamp < self.cache_ttl.get(cache_type, 3600):
                return cached_data
            else:
                del self.memory_cache[memory_key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_type}_{hash(key)}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data, timestamp = pickle.load(f)
                
                if time.time() - timestamp < self.cache_ttl.get(cache_type, 3600):
                    # Load into memory cache for faster access
                    self.memory_cache[memory_key] = (cached_data, timestamp)
                    return cached_data
                else:
                    # Remove expired cache
                    cache_file.unlink()
            
            except Exception as e:
                logger.debug(f"Error reading cache file {cache_file}: {e}")
        
        return None
    
    def set(self, cache_type: str, key: str, data: Any) -> None:
        """Cache data both in memory and on disk."""
        timestamp = time.time()
        memory_key = f"{cache_type}:{key}"
        
        # Store in memory cache
        self.memory_cache[memory_key] = (data, timestamp)
        
        # Store on disk
        cache_file = self.cache_dir / f"{cache_type}_{hash(key)}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump((data, timestamp), f)
        except Exception as e:
            logger.debug(f"Error writing cache file {cache_file}: {e}")
    
    def clear_expired(self) -> None:
        """Clear expired cache entries."""
        current_time = time.time()
        
        # Clear memory cache
        expired_keys = []
        for key, (data, timestamp) in self.memory_cache.items():
            cache_type = key.split(':', 1)[0]
            if current_time - timestamp >= self.cache_ttl.get(cache_type, 3600):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    data, timestamp = pickle.load(f)
                
                # Extract cache type from filename
                cache_type = cache_file.stem.split('_')[0]
                if current_time - timestamp >= self.cache_ttl.get(cache_type, 3600):
                    cache_file.unlink()
            
            except Exception as e:
                logger.debug(f"Error checking cache file {cache_file}: {e}")


class AdvancedErrorHandler:
    """Advanced error handling with retry logic and fallback strategies."""
    
    def __init__(self):
        """Initialize error handler."""
        self.retry_strategies = {
            'network_error': {'max_retries': 3, 'backoff_factor': 2.0},
            'rate_limit_error': {'max_retries': 5, 'backoff_factor': 1.5},
            'parsing_error': {'max_retries': 1, 'backoff_factor': 1.0},
            'api_error': {'max_retries': 2, 'backoff_factor': 2.0},
            'default': {'max_retries': 2, 'backoff_factor': 1.5}
        }
        self.error_counts = {}
        self.fallback_strategies = {}
    
    def handle_error(self, error: Exception, context: str, attempt: int = 1) -> bool:
        """
        Handle error with appropriate retry strategy.
        
        Returns:
            bool: True if should retry, False if should give up
        """
        error_type = self._classify_error(error)
        strategy = self.retry_strategies.get(error_type, self.retry_strategies['default'])
        
        # Track error counts
        error_key = f"{context}:{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        if attempt <= strategy['max_retries']:
            wait_time = strategy['backoff_factor'] ** (attempt - 1)
            logger.warning(f"Error in {context}: {error}. Retrying in {wait_time:.1f}s (attempt {attempt}/{strategy['max_retries']})")
            time.sleep(wait_time)
            return True
        else:
            logger.error(f"Max retries exceeded for {context}: {error}")
            return False
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate handling."""
        error_str = str(error).lower()
        
        if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'unreachable']):
            return 'network_error'
        elif any(keyword in error_str for keyword in ['rate limit', 'too many requests', '429']):
            return 'rate_limit_error'
        elif any(keyword in error_str for keyword in ['parse', 'decode', 'json', 'xml', 'html']):
            return 'parsing_error'
        elif any(keyword in error_str for keyword in ['api', '401', '403', '500', '502', '503']):
            return 'api_error'
        else:
            return 'default'
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of all errors encountered."""
        return dict(self.error_counts)


class BulkPodcastProcessor:
    """High-performance bulk processing for large-scale podcast discovery."""
    
    def __init__(self, max_workers: int = 4, use_cache: bool = True):
        """
        Initialize bulk processor.
        
        Args:
            max_workers: Maximum number of concurrent workers
            use_cache: Whether to use caching for performance
        """
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.use_cache = use_cache
        
        # Performance components
        self.rate_limiter = IntelligentRateLimiter()
        self.cache_manager = CacheManager() if use_cache else None
        self.error_handler = AdvancedErrorHandler()
        
        # Progress tracking
        self.progress = ProcessingProgress()
        self.progress_callbacks = []
        
        # Worker management
        self.executor = None
        self.results_queue = Queue()
        self._shutdown_event = threading.Event()
    
    def add_progress_callback(self, callback: Callable[[ProcessingProgress], None]) -> None:
        """Add callback to receive progress updates."""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self) -> None:
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                self.logger.warning(f"Error in progress callback: {e}")
    
    def process_multiple_topics(
        self,
        topics: List[str],
        limit_per_topic: int = 100,
        platforms: Optional[List[str]] = None,
        enrich_contacts: bool = True,
        analyze_intelligence: bool = True
    ) -> Dict[str, List[PodcastData]]:
        """
        Process multiple topics in parallel with optimization.
        
        Args:
            topics: List of topics to search
            limit_per_topic: Max podcasts per topic
            platforms: Platforms to search (default: all)
            enrich_contacts: Whether to enrich contact information
            analyze_intelligence: Whether to analyze intelligence
            
        Returns:
            Dict mapping topics to podcast results
        """
        self.logger.info(f"Starting bulk processing for {len(topics)} topics")
        
        # Initialize progress tracking
        self.progress = ProcessingProgress()
        self.progress.total_queries = len(topics)
        self.progress.start_time = datetime.now()
        
        # Estimate completion time (rough estimate)
        estimated_seconds_per_topic = 30 if enrich_contacts else 10
        estimated_duration = timedelta(seconds=estimated_seconds_per_topic * len(topics))
        self.progress.estimated_completion = self.progress.start_time + estimated_duration
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            self.executor = executor
            
            # Submit all tasks
            future_to_topic = {}
            for topic in topics:
                future = executor.submit(
                    self._process_single_topic,
                    topic,
                    limit_per_topic,
                    platforms,
                    enrich_contacts,
                    analyze_intelligence
                )
                future_to_topic[future] = topic
            
            # Collect results as they complete
            for future in as_completed(future_to_topic):
                topic = future_to_topic[future]
                self.progress.current_query = topic
                
                try:
                    podcasts = future.result()
                    results[topic] = podcasts
                    self.progress.completed_queries += 1
                    self.progress.total_podcasts_found += len(podcasts)
                    
                    self.logger.info(f"Completed topic '{topic}': {len(podcasts)} podcasts found")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process topic '{topic}': {e}")
                    results[topic] = []
                    self.progress.failed_queries += 1
                
                finally:
                    self._notify_progress()
                    
                    # Check for shutdown signal
                    if self._shutdown_event.is_set():
                        self.logger.info("Shutdown requested, canceling remaining tasks")
                        break
        
        self.logger.info(f"Bulk processing completed: {len(results)} topics processed")
        return results
    
    def _process_single_topic(
        self,
        topic: str,
        limit: int,
        platforms: Optional[List[str]],
        enrich_contacts: bool,
        analyze_intelligence: bool
    ) -> List[PodcastData]:
        """Process a single topic with caching and error handling."""
        # Check cache first
        cache_key = f"{topic}:{limit}:{platforms}:{enrich_contacts}:{analyze_intelligence}"
        
        if self.cache_manager:
            cached_result = self.cache_manager.get('topic_processing', cache_key)
            if cached_result:
                self.logger.debug(f"Using cached results for topic: {topic}")
                return cached_result
        
        # Process topic
        attempt = 1
        while attempt <= 3:  # Max 3 attempts per topic
            try:
                # Apply rate limiting
                self.rate_limiter.wait_if_needed('bulk_processing')
                
                # Create scraper instance for this topic
                scraper = PodcastHostScraper()
                
                # Scrape podcasts
                podcasts = scraper.scrape_podcasts(topic, limit, platforms)
                
                if not podcasts:
                    self.logger.warning(f"No podcasts found for topic: {topic}")
                    return []
                
                # Apply enrichment if requested
                if enrich_contacts:
                    podcasts = scraper.enrich_with_contact_info(podcasts)
                
                if analyze_intelligence:
                    podcasts = scraper.analyze_podcast_intelligence(podcasts, topic)
                
                # Cache results
                if self.cache_manager:
                    self.cache_manager.set('topic_processing', cache_key, podcasts)
                
                # Record success
                self.rate_limiter.record_success('bulk_processing')
                
                return podcasts
            
            except Exception as e:
                self.rate_limiter.record_error('bulk_processing')
                
                if self.error_handler.handle_error(e, f"topic_{topic}", attempt):
                    attempt += 1
                    continue
                else:
                    self.logger.error(f"Failed to process topic '{topic}' after all retries: {e}")
                    return []
        
        return []
    
    def optimize_memory_usage(self) -> None:
        """Optimize memory usage by clearing caches and collecting garbage."""
        import gc
        
        if self.cache_manager:
            self.cache_manager.clear_expired()
        
        # Force garbage collection
        gc.collect()
        
        self.logger.debug("Memory optimization completed")
    
    def export_bulk_results(
        self,
        results: Dict[str, List[PodcastData]],
        output_dir: str = "bulk_output",
        export_format: str = "enhanced_csv"
    ) -> Dict[str, str]:
        """
        Export bulk processing results in various formats.
        
        Args:
            results: Results from bulk processing
            output_dir: Output directory
            export_format: Format ('csv', 'enhanced_csv', 'json', 'all')
            
        Returns:
            Dict mapping result types to file paths
        """
        from .enhanced_reporting import EnhancedCSVExporter, ComprehensiveReporter
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        exported_files = {}
        
        # Export individual topic results
        if export_format in ['csv', 'enhanced_csv', 'all']:
            for topic, podcasts in results.items():
                if not podcasts:
                    continue
                
                safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                if export_format == 'enhanced_csv' or export_format == 'all':
                    exporter = EnhancedCSVExporter()
                    csv_file = exporter.export_enhanced_csv(
                        podcasts,
                        str(output_path / f"{safe_topic}_enhanced.csv")
                    )
                    exported_files[f"{topic}_enhanced_csv"] = csv_file
                else:
                    # Standard CSV export
                    scraper = PodcastHostScraper()
                    scraper.all_podcasts = podcasts
                    csv_file = scraper.export_to_csv(
                        podcasts,
                        str(output_path / f"{safe_topic}.csv")
                    )
                    exported_files[f"{topic}_csv"] = csv_file
        
        # Export JSON if requested
        if export_format in ['json', 'all']:
            reporter = ComprehensiveReporter()
            
            for topic, podcasts in results.items():
                if not podcasts:
                    continue
                
                safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
                json_file = reporter.export_json_data(
                    podcasts,
                    str(output_path / f"{safe_topic}.json")
                )
                exported_files[f"{topic}_json"] = json_file
        
        # Export combined summary
        if len(results) > 1:
            all_podcasts = []
            for podcasts in results.values():
                all_podcasts.extend(podcasts)
            
            if all_podcasts:
                # Combined enhanced CSV
                if export_format in ['enhanced_csv', 'all']:
                    exporter = EnhancedCSVExporter()
                    combined_csv = exporter.export_enhanced_csv(
                        all_podcasts,
                        str(output_path / "combined_all_topics_enhanced.csv")
                    )
                    exported_files["combined_enhanced_csv"] = combined_csv
                
                # Combined comprehensive report
                if export_format in ['enhanced_csv', 'all']:
                    reporter = ComprehensiveReporter()
                    combined_report = reporter.generate_comprehensive_report(
                        all_podcasts,
                        f"Combined analysis of {len(results)} topics",
                        str(output_path / "combined_comprehensive_report.md")
                    )
                    exported_files["combined_report"] = combined_report
        
        self.logger.info(f"Bulk export completed: {len(exported_files)} files generated")
        return exported_files
    
    def shutdown(self) -> None:
        """Gracefully shutdown the bulk processor."""
        self.logger.info("Shutting down bulk processor...")
        self._shutdown_event.set()
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        # Final memory cleanup
        self.optimize_memory_usage()
        
        self.logger.info("Bulk processor shutdown completed")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {
            'progress': {
                'total_queries': self.progress.total_queries,
                'completed_queries': self.progress.completed_queries,
                'failed_queries': self.progress.failed_queries,
                'completion_percentage': self.progress.completion_percentage,
                'total_podcasts_found': self.progress.total_podcasts_found,
                'elapsed_time': str(self.progress.elapsed_time),
                'estimated_completion': self.progress.estimated_completion.isoformat() if self.progress.estimated_completion else None
            },
            'errors': self.error_handler.get_error_summary(),
            'rate_limiting': {
                'consecutive_errors': dict(self.rate_limiter.consecutive_errors),
                'domains_in_backoff': len(self.rate_limiter.backoff_until)
            }
        }
        
        if self.cache_manager:
            stats['cache'] = {
                'memory_cache_size': len(self.cache_manager.memory_cache),
                'disk_cache_files': len(list(self.cache_manager.cache_dir.glob("*.pkl")))
            }
        
        return stats


# Utility functions for bulk processing

def create_progress_bar_callback() -> Callable[[ProcessingProgress], None]:
    """Create a simple progress bar callback for terminal output."""
    
    def progress_callback(progress: ProcessingProgress):
        """Display progress bar in terminal."""
        if progress.total_queries == 0:
            return
        
        percentage = progress.completion_percentage
        bar_length = 50
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r[{bar}] {percentage:.1f}% ({progress.completed_queries}/{progress.total_queries}) "
              f"| Podcasts: {progress.total_podcasts_found} | Current: {progress.current_query[:30]}", end='', flush=True)
        
        if progress.completed_queries + progress.failed_queries >= progress.total_queries:
            print()  # New line when complete
    
    return progress_callback


def estimate_processing_time(
    num_topics: int,
    limit_per_topic: int = 100,
    enrich_contacts: bool = True,
    analyze_intelligence: bool = True,
    max_workers: int = 4
) -> Dict[str, float]:
    """
    Estimate processing time for bulk operations.
    
    Returns:
        Dict with time estimates in seconds
    """
    # Base time estimates (in seconds per podcast)
    base_scraping_time = 0.1
    contact_enrichment_time = 2.0 if enrich_contacts else 0
    intelligence_analysis_time = 0.5 if analyze_intelligence else 0
    
    time_per_podcast = base_scraping_time + contact_enrichment_time + intelligence_analysis_time
    time_per_topic = time_per_podcast * limit_per_topic
    
    # Account for parallelization
    total_sequential_time = time_per_topic * num_topics
    estimated_parallel_time = total_sequential_time / min(max_workers, num_topics)
    
    # Add overhead for coordination, rate limiting, etc.
    overhead_factor = 1.3
    estimated_parallel_time *= overhead_factor
    
    return {
        'estimated_seconds': estimated_parallel_time,
        'estimated_minutes': estimated_parallel_time / 60,
        'estimated_hours': estimated_parallel_time / 3600,
        'time_per_topic': time_per_topic,
        'parallelization_factor': min(max_workers, num_topics)
    }