"""Unified Cache Manager - Orchestrates Multi-Layer Caching"""

import asyncio
import time
from typing import Any, Optional, Dict, List, Union
from enum import Enum
from ..logger import get_logger
from .memory_cache import MemoryCache, get_memory_cache
from .file_cache import FileCache, get_file_cache
from .redis_cache import RedisCache, get_redis_cache, REDIS_AVAILABLE


class CacheStrategy(Enum):
    """Cache storage and retrieval strategies"""
    MEMORY_ONLY = "memory_only"
    FILE_ONLY = "file_only"
    REDIS_ONLY = "redis_only"
    MEMORY_FIRST = "memory_first"  # Memory -> File -> Redis
    REDIS_FIRST = "redis_first"    # Redis -> Memory -> File
    WRITE_THROUGH = "write_through" # Write to all layers
    WRITE_BEHIND = "write_behind"   # Write to memory first, async to others


class CacheManager:
    """Unified multi-layer cache manager"""
    
    def __init__(self,
                 strategy: CacheStrategy = CacheStrategy.MEMORY_FIRST,
                 memory_cache: Optional[MemoryCache] = None,
                 file_cache: Optional[FileCache] = None,
                 redis_cache: Optional[Union[RedisCache, Any]] = None,
                 default_ttl: int = 3600,
                 enable_metrics: bool = True):
        
        self.strategy = strategy
        self.default_ttl = default_ttl
        self.enable_metrics = enable_metrics
        
        self.logger = get_logger("cache_manager")
        
        # Cache layers
        self.memory_cache = memory_cache or get_memory_cache()
        self.file_cache = file_cache
        self.redis_cache = redis_cache
        
        # Metrics
        self._total_gets = 0
        self._total_puts = 0
        self._memory_hits = 0
        self._file_hits = 0
        self._redis_hits = 0
        self._misses = 0
        self._errors = 0
        
        # Background tasks
        self._write_behind_queue: asyncio.Queue = asyncio.Queue()
        self._write_behind_task: Optional[asyncio.Task] = None
        
        if strategy == CacheStrategy.WRITE_BEHIND:
            self._start_write_behind_worker()
        
        self.logger.info(f"Cache manager initialized with strategy: {strategy.value}")
    
    async def get(self, key: str, default: Any = None, category: str = "default") -> Any:
        """Get value from cache using configured strategy"""
        self._total_gets += 1
        
        try:
            if self.strategy == CacheStrategy.MEMORY_ONLY:
                return await self._get_from_memory(key, default, category)
            
            elif self.strategy == CacheStrategy.FILE_ONLY:
                return await self._get_from_file(key, default)
            
            elif self.strategy == CacheStrategy.REDIS_ONLY:
                return await self._get_from_redis(key, default)
            
            elif self.strategy == CacheStrategy.MEMORY_FIRST:
                return await self._get_memory_first(key, default, category)
            
            elif self.strategy == CacheStrategy.REDIS_FIRST:
                return await self._get_redis_first(key, default, category)
            
            else:  # Default to memory first
                return await self._get_memory_first(key, default, category)
        
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None, 
                  category: str = "default") -> bool:
        """Put value in cache using configured strategy"""
        self._total_puts += 1
        cache_ttl = ttl or self.default_ttl
        
        try:
            if self.strategy == CacheStrategy.MEMORY_ONLY:
                return await self._put_to_memory(key, value, cache_ttl, category)
            
            elif self.strategy == CacheStrategy.FILE_ONLY:
                return await self._put_to_file(key, value, cache_ttl)
            
            elif self.strategy == CacheStrategy.REDIS_ONLY:
                return await self._put_to_redis(key, value, cache_ttl)
            
            elif self.strategy == CacheStrategy.WRITE_THROUGH:
                return await self._put_write_through(key, value, cache_ttl, category)
            
            elif self.strategy == CacheStrategy.WRITE_BEHIND:
                return await self._put_write_behind(key, value, cache_ttl, category)
            
            else:  # Default strategies store in primary layer
                return await self._put_to_memory(key, value, cache_ttl, category)
        
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache put error for key {key}: {e}")
            return False
    
    async def remove(self, key: str, category: str = "default") -> bool:
        """Remove key from all cache layers"""
        try:
            removed = False
            
            # Remove from all available layers
            if self.memory_cache:
                if self.memory_cache.remove(key, category):
                    removed = True
            
            if self.file_cache:
                if await self.file_cache.remove(key):
                    removed = True
            
            if self.redis_cache:
                if await self.redis_cache.remove(key):
                    removed = True
            
            return removed
        
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache remove error for key {key}: {e}")
            return False
    
    async def clear(self, category: Optional[str] = None) -> Dict[str, int]:
        """Clear cache entries from all layers"""
        try:
            results = {}
            
            if self.memory_cache:
                self.memory_cache.clear(category)
                results['memory'] = 1  # Memory cache doesn't return count
            
            if self.file_cache:
                results['file'] = await self.file_cache.clear()
            
            if self.redis_cache:
                pattern = f"{category}:*" if category else None
                results['redis'] = await self.redis_cache.clear(pattern)
            
            total = sum(results.values())
            self.logger.info(f"Cleared {total} entries from cache layers")
            
            return results
        
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Cache clear error: {e}")
            return {}
    
    async def warm_up(self, key_value_pairs: Dict[str, Any], 
                      ttl: Optional[int] = None, category: str = "default") -> int:
        """Pre-populate cache with key-value pairs"""
        try:
            success_count = 0
            cache_ttl = ttl or self.default_ttl
            
            # Use batch operations where possible
            if self.redis_cache and hasattr(self.redis_cache, 'put_multiple'):
                if await self.redis_cache.put_multiple(key_value_pairs, cache_ttl):
                    success_count += len(key_value_pairs)
            
            # Warm up other layers
            for key, value in key_value_pairs.items():
                if await self.put(key, value, cache_ttl, category):
                    if not (self.redis_cache and hasattr(self.redis_cache, 'put_multiple')):
                        success_count += 1
            
            self.logger.info(f"Warmed up cache with {success_count} entries")
            return success_count
        
        except Exception as e:
            self.logger.error(f"Cache warm-up error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            total_accesses = self._total_gets
            hit_rate = (self._memory_hits + self._file_hits + self._redis_hits) / max(1, total_accesses)
            
            stats = {
                'strategy': self.strategy.value,
                'total_gets': self._total_gets,
                'total_puts': self._total_puts,
                'memory_hits': self._memory_hits,
                'file_hits': self._file_hits,
                'redis_hits': self._redis_hits,
                'misses': self._misses,
                'errors': self._errors,
                'hit_rate': hit_rate,
                'layers_enabled': {
                    'memory': self.memory_cache is not None,
                    'file': self.file_cache is not None,
                    'redis': self.redis_cache is not None
                }
            }
            
            # Add layer-specific stats
            if self.memory_cache:
                stats['memory_cache'] = self.memory_cache.get_stats()
            
            if self.file_cache:
                stats['file_cache'] = self.file_cache.get_stats()
            
            if self.redis_cache:
                stats['redis_cache'] = self.redis_cache.get_stats()
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Stats error: {e}")
            return {'error': str(e)}
    
    # Private methods for different strategies
    
    async def _get_from_memory(self, key: str, default: Any, category: str) -> Any:
        """Get from memory cache only"""
        if not self.memory_cache:
            self._misses += 1
            return default
        
        result = self.memory_cache.get(key, category)
        if result is not None:
            self._memory_hits += 1
            return result
        
        self._misses += 1
        return default
    
    async def _get_from_file(self, key: str, default: Any) -> Any:
        """Get from file cache only"""
        if not self.file_cache:
            self._misses += 1
            return default
        
        result = await self.file_cache.get(key, default)
        if result != default:
            self._file_hits += 1
            return result
        
        self._misses += 1
        return default
    
    async def _get_from_redis(self, key: str, default: Any) -> Any:
        """Get from Redis cache only"""
        if not self.redis_cache:
            self._misses += 1
            return default
        
        result = await self.redis_cache.get(key, default)
        if result != default:
            self._redis_hits += 1
            return result
        
        self._misses += 1
        return default
    
    async def _get_memory_first(self, key: str, default: Any, category: str) -> Any:
        """Get with memory-first strategy"""
        # Try memory first
        if self.memory_cache:
            result = self.memory_cache.get(key, category)
            if result is not None:
                self._memory_hits += 1
                return result
        
        # Try file cache
        if self.file_cache:
            result = await self.file_cache.get(key, default)
            if result != default:
                self._file_hits += 1
                # Store in memory for faster access
                if self.memory_cache:
                    self.memory_cache.put(key, result, category)
                return result
        
        # Try Redis cache
        if self.redis_cache:
            result = await self.redis_cache.get(key, default)
            if result != default:
                self._redis_hits += 1
                # Store in higher-priority caches
                if self.memory_cache:
                    self.memory_cache.put(key, result, category)
                if self.file_cache:
                    await self.file_cache.put(key, result)
                return result
        
        self._misses += 1
        return default
    
    async def _get_redis_first(self, key: str, default: Any, category: str) -> Any:
        """Get with Redis-first strategy"""
        # Try Redis first
        if self.redis_cache:
            result = await self.redis_cache.get(key, default)
            if result != default:
                self._redis_hits += 1
                # Store in memory for faster access
                if self.memory_cache:
                    self.memory_cache.put(key, result, category)
                return result
        
        # Try memory cache
        if self.memory_cache:
            result = self.memory_cache.get(key, category)
            if result is not None:
                self._memory_hits += 1
                return result
        
        # Try file cache
        if self.file_cache:
            result = await self.file_cache.get(key, default)
            if result != default:
                self._file_hits += 1
                return result
        
        self._misses += 1
        return default
    
    async def _put_to_memory(self, key: str, value: Any, ttl: int, category: str) -> bool:
        """Put to memory cache only"""
        if not self.memory_cache:
            return False
        
        self.memory_cache.put(key, value, category, ttl)
        return True
    
    async def _put_to_file(self, key: str, value: Any, ttl: int) -> bool:
        """Put to file cache only"""
        if not self.file_cache:
            return False
        
        return await self.file_cache.put(key, value, ttl)
    
    async def _put_to_redis(self, key: str, value: Any, ttl: int) -> bool:
        """Put to Redis cache only"""
        if not self.redis_cache:
            return False
        
        return await self.redis_cache.put(key, value, ttl)
    
    async def _put_write_through(self, key: str, value: Any, ttl: int, category: str) -> bool:
        """Write through to all available cache layers"""
        success = True
        
        # Write to all layers
        if self.memory_cache:
            self.memory_cache.put(key, value, category, ttl)
        
        if self.file_cache:
            if not await self.file_cache.put(key, value, ttl):
                success = False
        
        if self.redis_cache:
            if not await self.redis_cache.put(key, value, ttl):
                success = False
        
        return success
    
    async def _put_write_behind(self, key: str, value: Any, ttl: int, category: str) -> bool:
        """Write to memory immediately, queue write to other layers"""
        # Write to memory immediately
        if self.memory_cache:
            self.memory_cache.put(key, value, category, ttl)
        
        # Queue write to other layers
        await self._write_behind_queue.put({
            'key': key,
            'value': value,
            'ttl': ttl,
            'category': category,
            'timestamp': time.time()
        })
        
        return True
    
    def _start_write_behind_worker(self):
        """Start background worker for write-behind strategy"""
        try:
            loop = asyncio.get_event_loop()
            self._write_behind_task = loop.create_task(self._write_behind_worker())
        except RuntimeError:
            pass
    
    async def _write_behind_worker(self):
        """Background worker for processing write-behind queue"""
        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(self._write_behind_queue.get(), timeout=1.0)
                
                key = item['key']
                value = item['value']
                ttl = item['ttl']
                
                # Write to file cache
                if self.file_cache:
                    await self.file_cache.put(key, value, ttl)
                
                # Write to Redis cache
                if self.redis_cache:
                    await self.redis_cache.put(key, value, ttl)
                
                self._write_behind_queue.task_done()
                
            except asyncio.TimeoutError:
                # No items in queue, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Write-behind worker error: {e}")
    
    async def close(self):
        """Close cache manager and all layers"""
        # Stop write-behind worker
        if self._write_behind_task:
            self._write_behind_task.cancel()
            try:
                await self._write_behind_task
            except asyncio.CancelledError:
                pass
        
        # Close cache layers
        if self.memory_cache:
            await self.memory_cache.close()
        
        if self.file_cache:
            await self.file_cache.close()
        
        if self.redis_cache:
            await self.redis_cache.close()
        
        self.logger.info("Cache manager closed")


# Global cache manager instance
_global_cache_manager: Optional[CacheManager] = None


async def get_cache_manager(
    strategy: CacheStrategy = CacheStrategy.MEMORY_FIRST,
    enable_file_cache: bool = True,
    enable_redis_cache: bool = True,
    redis_url: str = "redis://localhost:6379"
) -> CacheManager:
    """Get global cache manager instance"""
    global _global_cache_manager
    
    if _global_cache_manager is None:
        # Initialize cache layers
        memory_cache = get_memory_cache()
        
        file_cache = None
        if enable_file_cache:
            file_cache = get_file_cache()
        
        redis_cache = None
        if enable_redis_cache and REDIS_AVAILABLE:
            try:
                redis_cache = await get_redis_cache(redis_url)
            except Exception as e:
                get_logger("cache_manager").warning(f"Redis cache disabled: {e}")
        
        _global_cache_manager = CacheManager(
            strategy=strategy,
            memory_cache=memory_cache,
            file_cache=file_cache,
            redis_cache=redis_cache
        )
    
    return _global_cache_manager