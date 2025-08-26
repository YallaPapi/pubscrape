"""In-Memory LRU Cache Implementation"""

import time
import asyncio
import threading
from functools import lru_cache
from typing import Any, Optional, Dict, Set, Tuple
from collections import OrderedDict
from ..logger import get_logger


class LRUCache:
    """Thread-safe LRU Cache implementation"""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._access_count = 0
        self._hit_count = 0
        self._miss_count = 0
        
        self.logger = get_logger("memory_cache.lru")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            self._access_count += 1
            
            if key not in self._cache:
                self._miss_count += 1
                return None
            
            # Check TTL
            if self._is_expired(key):
                self._remove_key(key)
                self._miss_count += 1
                return None
            
            # Move to end (most recently used)
            value = self._cache[key]
            self._cache.move_to_end(key)
            self._hit_count += 1
            
            return value
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache"""
        with self._lock:
            current_time = time.time()
            
            if key in self._cache:
                # Update existing
                self._cache[key] = value
                self._timestamps[key] = current_time
                self._cache.move_to_end(key)
            else:
                # Add new
                if len(self._cache) >= self.maxsize:
                    # Remove least recently used
                    oldest_key = next(iter(self._cache))
                    self._remove_key(oldest_key)
                
                self._cache[key] = value
                self._timestamps[key] = current_time
    
    def remove(self, key: str) -> bool:
        """Remove key from cache"""
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._access_count = 0
            self._hit_count = 0
            self._miss_count = 0
    
    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        with self._lock:
            expired_keys = []
            current_time = time.time()
            
            for key, timestamp in self._timestamps.items():
                if current_time - timestamp > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_key(key)
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = self._hit_count / max(1, self._access_count)
            return {
                'size': len(self._cache),
                'maxsize': self.maxsize,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'access_count': self._access_count,
                'hit_rate': hit_rate,
                'ttl': self.ttl
            }
    
    def _is_expired(self, key: str) -> bool:
        """Check if key is expired"""
        if key not in self._timestamps:
            return True
        return time.time() - self._timestamps[key] > self.ttl
    
    def _remove_key(self, key: str) -> None:
        """Remove key and its timestamp"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)


class MemoryCache:
    """High-performance in-memory cache with multiple strategies"""
    
    def __init__(self, 
                 maxsize: int = 10000,
                 ttl: int = 3600,
                 enable_lru: bool = True,
                 enable_function_cache: bool = True):
        
        self.maxsize = maxsize
        self.ttl = ttl
        self.enable_lru = enable_lru
        self.enable_function_cache = enable_function_cache
        
        self.logger = get_logger("memory_cache")
        
        # Initialize cache layers
        if enable_lru:
            self._lru_cache = LRUCache(maxsize, ttl)
        
        # Simple dict cache for high-frequency access
        self._simple_cache: Dict[str, Tuple[Any, float]] = {}
        self._simple_lock = threading.RLock()
        
        # Function result cache
        if enable_function_cache:
            self._function_cache = {}
        
        # Cache categories for different data types
        self._category_caches: Dict[str, LRUCache] = {}
        self._category_lock = threading.RLock()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
        self.logger.info(f"Memory cache initialized with maxsize={maxsize}, ttl={ttl}")
    
    def get(self, key: str, category: str = "default") -> Optional[Any]:
        """Get value from cache"""
        try:
            # Try category-specific cache first
            if category != "default":
                cache = self._get_category_cache(category)
                result = cache.get(key)
                if result is not None:
                    return result
            
            # Try LRU cache
            if self.enable_lru:
                result = self._lru_cache.get(key)
                if result is not None:
                    return result
            
            # Try simple cache
            with self._simple_lock:
                if key in self._simple_cache:
                    value, timestamp = self._simple_cache[key]
                    if time.time() - timestamp <= self.ttl:
                        return value
                    else:
                        del self._simple_cache[key]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
            return None
    
    def put(self, key: str, value: Any, category: str = "default", ttl: Optional[int] = None) -> None:
        """Put value in cache"""
        try:
            cache_ttl = ttl or self.ttl
            
            # Store in category-specific cache
            if category != "default":
                cache = self._get_category_cache(category)
                cache.put(key, value)
            
            # Store in LRU cache
            if self.enable_lru:
                self._lru_cache.put(key, value)
            
            # Store in simple cache for high-frequency items
            with self._simple_lock:
                self._simple_cache[key] = (value, time.time())
                
                # Limit simple cache size
                if len(self._simple_cache) > self.maxsize // 4:
                    # Remove oldest entries
                    sorted_items = sorted(
                        self._simple_cache.items(),
                        key=lambda x: x[1][1]  # Sort by timestamp
                    )
                    for old_key, _ in sorted_items[:len(self._simple_cache) // 4]:
                        del self._simple_cache[old_key]
        
        except Exception as e:
            self.logger.error(f"Cache put error: {e}")
    
    def remove(self, key: str, category: str = "default") -> bool:
        """Remove key from cache"""
        removed = False
        
        try:
            # Remove from category cache
            if category != "default":
                cache = self._get_category_cache(category)
                if cache.remove(key):
                    removed = True
            
            # Remove from LRU cache
            if self.enable_lru:
                if self._lru_cache.remove(key):
                    removed = True
            
            # Remove from simple cache
            with self._simple_lock:
                if key in self._simple_cache:
                    del self._simple_cache[key]
                    removed = True
            
            return removed
            
        except Exception as e:
            self.logger.error(f"Cache remove error: {e}")
            return False
    
    def clear(self, category: Optional[str] = None) -> None:
        """Clear cache entries"""
        try:
            if category:
                # Clear specific category
                if category in self._category_caches:
                    self._category_caches[category].clear()
            else:
                # Clear all caches
                if self.enable_lru:
                    self._lru_cache.clear()
                
                with self._simple_lock:
                    self._simple_cache.clear()
                
                with self._category_lock:
                    for cache in self._category_caches.values():
                        cache.clear()
                    self._category_caches.clear()
            
            self.logger.info(f"Cache cleared for category: {category or 'all'}")
            
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
    
    def cached_function(self, ttl: Optional[int] = None, category: str = "functions"):
        """Decorator for caching function results"""
        def decorator(func):
            if not self.enable_function_cache:
                return func
            
            def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # Try to get from cache
                result = self.get(cache_key, category)
                if result is not None:
                    return result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.put(cache_key, result, category, ttl)
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {
            'maxsize': self.maxsize,
            'ttl': self.ttl,
            'categories': len(self._category_caches)
        }
        
        if self.enable_lru:
            stats['lru'] = self._lru_cache.get_stats()
        
        with self._simple_lock:
            stats['simple_cache_size'] = len(self._simple_cache)
        
        # Category stats
        category_stats = {}
        with self._category_lock:
            for name, cache in self._category_caches.items():
                category_stats[name] = cache.get_stats()
        stats['category_stats'] = category_stats
        
        return stats
    
    def _get_category_cache(self, category: str) -> LRUCache:
        """Get or create category-specific cache"""
        with self._category_lock:
            if category not in self._category_caches:
                self._category_caches[category] = LRUCache(
                    maxsize=self.maxsize // 4,  # Smaller size for categories
                    ttl=self.ttl
                )
            return self._category_caches[category]
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop, cleanup will be manual
            pass
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                total_cleaned = 0
                
                # Cleanup LRU cache
                if self.enable_lru:
                    cleaned = self._lru_cache.cleanup_expired()
                    total_cleaned += cleaned
                
                # Cleanup simple cache
                current_time = time.time()
                with self._simple_lock:
                    expired_keys = [
                        key for key, (_, timestamp) in self._simple_cache.items()
                        if current_time - timestamp > self.ttl
                    ]
                    for key in expired_keys:
                        del self._simple_cache[key]
                    total_cleaned += len(expired_keys)
                
                # Cleanup category caches
                with self._category_lock:
                    for cache in self._category_caches.values():
                        cleaned = cache.cleanup_expired()
                        total_cleaned += cleaned
                
                if total_cleaned > 0:
                    self.logger.debug(f"Cleaned up {total_cleaned} expired cache entries")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
    
    async def close(self):
        """Close the cache and cleanup resources"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.clear()
        self.logger.info("Memory cache closed")
    
    def __del__(self):
        if self._cleanup_task and not self._cleanup_task.done():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.close())
            except RuntimeError:
                pass


# Global memory cache instance
_global_cache: Optional[MemoryCache] = None


def get_memory_cache() -> MemoryCache:
    """Get global memory cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = MemoryCache()
    return _global_cache


# Convenience decorators
def cached(ttl: int = 3600, category: str = "default"):
    """Convenient caching decorator"""
    cache = get_memory_cache()
    return cache.cached_function(ttl=ttl, category=category)


@lru_cache(maxsize=1000)
def fast_cached_function(func_name: str, args_hash: str, func_result: Any) -> Any:
    """Fast LRU cache for function results using built-in lru_cache"""
    return func_result