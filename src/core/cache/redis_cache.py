"""Redis-Based Cache Implementation for Production"""

import json
import pickle
import asyncio
from typing import Any, Optional, Dict, Union
from ..logger import get_logger

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None


class RedisCache:
    """Redis-based cache with async support"""
    
    def __init__(self,
                 redis_url: str = "redis://localhost:6379",
                 key_prefix: str = "pubscrape:",
                 default_ttl: int = 3600,
                 serializer: str = "json",
                 max_connections: int = 20):
        
        if not REDIS_AVAILABLE:
            raise ImportError("aioredis is required for Redis cache. Install with: pip install aioredis")
        
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.serializer = serializer
        self.max_connections = max_connections
        
        self.logger = get_logger("redis_cache")
        self._redis: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._errors = 0
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self._redis is not None:
            return
        
        try:
            # Create connection pool
            self._connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                retry_on_timeout=True
            )
            
            # Create Redis client
            self._redis = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis.ping()
            
            self.logger.info(f"Redis cache connected to {self.redis_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from Redis cache"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key)
            value = await self._redis.get(full_key)
            
            if value is None:
                self._misses += 1
                return default
            
            self._hits += 1
            return self._deserialize(value)
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis get error for key {key}: {e}")
            return default
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put value in Redis cache"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key)
            serialized_value = self._serialize(value)
            cache_ttl = ttl or self.default_ttl
            
            await self._redis.setex(full_key, cache_ttl, serialized_value)
            return True
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis put error for key {key}: {e}")
            return False
    
    async def remove(self, key: str) -> bool:
        """Remove key from Redis cache"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key)
            result = await self._redis.delete(full_key)
            return result > 0
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis remove error for key {key}: {e}")
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries"""
        if not self._redis:
            await self.initialize()
        
        try:
            if pattern:
                # Clear keys matching pattern
                search_pattern = self._make_key(pattern)
                keys = await self._redis.keys(search_pattern)
            else:
                # Clear all keys with our prefix
                keys = await self._redis.keys(f"{self.key_prefix}*")
            
            if keys:
                deleted = await self._redis.delete(*keys)
                self.logger.info(f"Cleared {deleted} Redis cache entries")
                return deleted
            
            return 0
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis clear error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key)
            return await self._redis.exists(full_key)
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key)
            return await self._redis.expire(full_key, ttl)
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis expire error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_key = self._make_key(key)
            return await self._redis.incrby(full_key, amount)
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis increment error for key {key}: {e}")
            return None
    
    async def get_multiple(self, keys: list[str]) -> Dict[str, Any]:
        """Get multiple keys at once"""
        if not self._redis:
            await self.initialize()
        
        try:
            full_keys = [self._make_key(key) for key in keys]
            values = await self._redis.mget(full_keys)
            
            result = {}
            for i, (key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    self._hits += 1
                    result[key] = self._deserialize(value)
                else:
                    self._misses += 1
            
            return result
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis mget error: {e}")
            return {}
    
    async def put_multiple(self, key_value_pairs: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Put multiple key-value pairs"""
        if not self._redis:
            await self.initialize()
        
        try:
            cache_ttl = ttl or self.default_ttl
            
            # Use pipeline for efficiency
            pipe = self._redis.pipeline()
            
            for key, value in key_value_pairs.items():
                full_key = self._make_key(key)
                serialized_value = self._serialize(value)
                pipe.setex(full_key, cache_ttl, serialized_value)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Redis mset error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = self._hits / max(1, self._hits + self._misses)
        
        return {
            'redis_url': self.redis_url,
            'key_prefix': self.key_prefix,
            'default_ttl': self.default_ttl,
            'serializer': self.serializer,
            'hits': self._hits,
            'misses': self._misses,
            'errors': self._errors,
            'hit_rate': hit_rate,
            'connected': self._redis is not None
        }
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        if not self._redis:
            await self.initialize()
        
        try:
            info = await self._redis.info()
            return {
                'redis_version': info.get('redis_version', 'unknown'),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
        except Exception as e:
            self.logger.error(f"Redis info error: {e}")
            return {}
    
    def _make_key(self, key: str) -> str:
        """Create full key with prefix"""
        return f"{self.key_prefix}{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            if self.serializer == "json":
                return json.dumps(value, default=str).encode('utf-8')
            elif self.serializer == "pickle":
                return pickle.dumps(value)
            else:
                return str(value).encode('utf-8')
        except Exception as e:
            self.logger.error(f"Serialization error: {e}")
            raise
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            if self.serializer == "json":
                return json.loads(value.decode('utf-8'))
            elif self.serializer == "pickle":
                return pickle.loads(value)
            else:
                return value.decode('utf-8')
        except Exception as e:
            self.logger.error(f"Deserialization error: {e}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
        
        self._redis = None
        self.logger.info("Redis cache closed")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class MockRedisCache:
    """Mock Redis cache when Redis is not available"""
    
    def __init__(self, *args, **kwargs):
        self.logger = get_logger("mock_redis_cache")
        self.logger.warning("Using mock Redis cache - install aioredis for full functionality")
        self._data = {}
    
    async def initialize(self):
        pass
    
    async def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        self._data[key] = value
        return True
    
    async def remove(self, key: str) -> bool:
        return self._data.pop(key, None) is not None
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        count = len(self._data)
        self._data.clear()
        return count
    
    async def exists(self, key: str) -> bool:
        return key in self._data
    
    def get_stats(self) -> Dict[str, Any]:
        return {'mock': True, 'size': len(self._data)}
    
    async def close(self):
        pass


# Global Redis cache instance
_global_redis_cache: Optional[Union[RedisCache, MockRedisCache]] = None


async def get_redis_cache(redis_url: str = "redis://localhost:6379") -> Union[RedisCache, MockRedisCache]:
    """Get global Redis cache instance"""
    global _global_redis_cache
    if _global_redis_cache is None:
        try:
            if REDIS_AVAILABLE:
                _global_redis_cache = RedisCache(redis_url=redis_url)
                await _global_redis_cache.initialize()
            else:
                _global_redis_cache = MockRedisCache()
        except Exception as e:
            get_logger("redis_cache").warning(f"Redis connection failed, using mock cache: {e}")
            _global_redis_cache = MockRedisCache()
    
    return _global_redis_cache