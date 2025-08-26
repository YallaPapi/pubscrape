"""Connection Pool Manager for Async HTTP Operations"""

import asyncio
import aiohttp
import time
import weakref
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientResponse
from typing import Dict, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager
from ..utils.logger import get_logger


class ConnectionPoolManager:
    """Manages connection pools for efficient HTTP requests"""
    
    _instances: Dict[str, 'ConnectionPoolManager'] = {}
    _lock = asyncio.Lock()
    
    def __init__(self, 
                 pool_name: str = "default",
                 max_connections: int = 100,
                 max_connections_per_host: int = 30,
                 keepalive_timeout: int = 30,
                 connect_timeout: int = 10,
                 read_timeout: int = 30,
                 enable_cleanup: bool = True):
        
        self.pool_name = pool_name
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.keepalive_timeout = keepalive_timeout
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.enable_cleanup = enable_cleanup
        
        self.logger = get_logger(f"connection_pool.{pool_name}")
        self._session: Optional[ClientSession] = None
        self._connector: Optional[TCPConnector] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._active_requests = 0
        self._total_requests = 0
        self._failed_requests = 0
        self._start_time = time.time()
        
        # Weak references for cleanup
        self._sessions = weakref.WeakSet()
        
    @classmethod
    async def get_instance(cls, pool_name: str = "default", **kwargs) -> 'ConnectionPoolManager':
        """Get or create connection pool instance"""
        async with cls._lock:
            if pool_name not in cls._instances:
                cls._instances[pool_name] = cls(pool_name=pool_name, **kwargs)
                await cls._instances[pool_name].initialize()
            return cls._instances[pool_name]
    
    async def initialize(self):
        """Initialize the connection pool"""
        if self._session is not None:
            return
        
        # Create TCP connector with connection pooling
        self._connector = TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections_per_host,
            keepalive_timeout=self.keepalive_timeout,
            enable_cleanup_closed=True,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            use_dns_cache=True
        )
        
        # Create session with timeout configuration
        timeout = ClientTimeout(
            total=self.connect_timeout + self.read_timeout,
            connect=self.connect_timeout,
            sock_read=self.read_timeout
        )
        
        self._session = ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        )
        
        self._sessions.add(self._session)
        
        # Start cleanup task if enabled
        if self.enable_cleanup:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        self.logger.info(f"Connection pool '{self.pool_name}' initialized with {self.max_connections} max connections")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncContextManager[ClientSession]:
        """Get a session for making requests"""
        if self._session is None:
            await self.initialize()
        
        self._active_requests += 1
        try:
            yield self._session
        finally:
            self._active_requests -= 1
    
    async def get(self, url: str, **kwargs) -> ClientResponse:
        """Make GET request using the connection pool"""
        async with self.get_session() as session:
            self._total_requests += 1
            try:
                response = await session.get(url, **kwargs)
                return response
            except Exception as e:
                self._failed_requests += 1
                self.logger.error(f"GET request failed for {url}: {e}")
                raise
    
    async def post(self, url: str, **kwargs) -> ClientResponse:
        """Make POST request using the connection pool"""
        async with self.get_session() as session:
            self._total_requests += 1
            try:
                response = await session.post(url, **kwargs)
                return response
            except Exception as e:
                self._failed_requests += 1
                self.logger.error(f"POST request failed for {url}: {e}")
                raise
    
    async def fetch_text(self, url: str, **kwargs) -> str:
        """Fetch URL content as text"""
        async with await self.get(url, **kwargs) as response:
            return await response.text()
    
    async def fetch_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Fetch URL content as JSON"""
        async with await self.get(url, **kwargs) as response:
            return await response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        uptime = time.time() - self._start_time
        connector_stats = {}
        
        if self._connector:
            connector_stats = {
                'total_connections': len(self._connector._conns),
                'available_connections': sum(len(conns) for conns in self._connector._conns.values()),
            }
        
        return {
            'pool_name': self.pool_name,
            'active_requests': self._active_requests,
            'total_requests': self._total_requests,
            'failed_requests': self._failed_requests,
            'success_rate': (self._total_requests - self._failed_requests) / max(1, self._total_requests),
            'uptime_seconds': uptime,
            'requests_per_second': self._total_requests / max(1, uptime),
            **connector_stats
        }
    
    async def _periodic_cleanup(self):
        """Periodic cleanup task for connection pool"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                if self._connector:
                    # Force cleanup of closed connections
                    await self._connector.close()
                    
                # Log stats
                stats = self.get_stats()
                self.logger.debug(f"Pool stats: {stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
    
    async def close(self):
        """Close the connection pool"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._connector:
            await self._connector.close()
            self._connector = None
        
        # Remove from instances
        if self.pool_name in self.__class__._instances:
            del self.__class__._instances[self.pool_name]
        
        self.logger.info(f"Connection pool '{self.pool_name}' closed")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def __del__(self):
        if self._session and not self._session.closed:
            # Schedule cleanup for event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.close())
            except RuntimeError:
                pass


# Global connection pool instances
_default_pool: Optional[ConnectionPoolManager] = None
_scraper_pool: Optional[ConnectionPoolManager] = None


async def get_default_pool() -> ConnectionPoolManager:
    """Get the default connection pool"""
    global _default_pool
    if _default_pool is None:
        _default_pool = await ConnectionPoolManager.get_instance("default")
    return _default_pool


async def get_scraper_pool() -> ConnectionPoolManager:
    """Get the scraper-specific connection pool"""
    global _scraper_pool
    if _scraper_pool is None:
        _scraper_pool = await ConnectionPoolManager.get_instance(
            "scraper",
            max_connections=200,
            max_connections_per_host=50,
            connect_timeout=15,
            read_timeout=45
        )
    return _scraper_pool


async def cleanup_all_pools():
    """Cleanup all connection pools"""
    global _default_pool, _scraper_pool
    
    if _default_pool:
        await _default_pool.close()
        _default_pool = None
    
    if _scraper_pool:
        await _scraper_pool.close()
        _scraper_pool = None
    
    # Cleanup class-level instances
    for pool in list(ConnectionPoolManager._instances.values()):
        await pool.close()
    ConnectionPoolManager._instances.clear()
