"""Persistent File-Based Cache Implementation"""

import os
import time
import json
import pickle
import hashlib
import asyncio
import aiofiles
from pathlib import Path
from typing import Any, Optional, Dict, Union
from ..logger import get_logger


class FileCache:
    """Persistent file-based cache with async I/O"""
    
    def __init__(self,
                 cache_dir: Union[str, Path] = ".cache",
                 default_ttl: int = 86400,  # 24 hours
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 compression: bool = False,
                 serializer: str = "pickle"):
        
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.max_file_size = max_file_size
        self.compression = compression
        self.serializer = serializer
        
        self.logger = get_logger("file_cache")
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache metadata
        self.metadata_file = self.cache_dir / ".metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = {}
        
        # Load existing metadata
        self._load_metadata()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
        self.logger.info(f"File cache initialized at {self.cache_dir}")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from file cache"""
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return default
            
            # Check metadata for TTL
            if not self._is_valid(key):
                await self._remove_file(file_path)
                return default
            
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Check file size
            if len(content) > self.max_file_size:
                self.logger.warning(f"Cache file too large: {len(content)} bytes")
                await self._remove_file(file_path)
                return default
            
            # Deserialize content
            try:
                if self.serializer == "json":
                    return json.loads(content.decode('utf-8'))
                elif self.serializer == "pickle":
                    return pickle.loads(content)
                else:
                    return content.decode('utf-8')
            except (json.JSONDecodeError, pickle.UnpicklingError, UnicodeDecodeError) as e:
                self.logger.error(f"Deserialization error for key {key}: {e}")
                await self._remove_file(file_path)
                return default
                
        except Exception as e:
            self.logger.error(f"File cache get error for key {key}: {e}")
            return default
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put value in file cache"""
        try:
            file_path = self._get_file_path(key)
            cache_ttl = ttl or self.default_ttl
            
            # Serialize content
            try:
                if self.serializer == "json":
                    content = json.dumps(value, default=str).encode('utf-8')
                elif self.serializer == "pickle":
                    content = pickle.dumps(value)
                else:
                    content = str(value).encode('utf-8')
            except (TypeError, pickle.PicklingError) as e:
                self.logger.error(f"Serialization error for key {key}: {e}")
                return False
            
            # Check content size
            if len(content) > self.max_file_size:
                self.logger.warning(f"Content too large for cache: {len(content)} bytes")
                return False
            
            # Write to temporary file first
            temp_path = file_path.with_suffix('.tmp')
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(content)
            
            # Atomic move
            temp_path.rename(file_path)
            
            # Update metadata
            current_time = time.time()
            self._metadata[key] = {
                'created': current_time,
                'expires': current_time + cache_ttl,
                'size': len(content),
                'ttl': cache_ttl
            }
            
            await self._save_metadata()
            return True
            
        except Exception as e:
            self.logger.error(f"File cache put error for key {key}: {e}")
            return False
    
    async def remove(self, key: str) -> bool:
        """Remove key from cache"""
        try:
            file_path = self._get_file_path(key)
            removed = await self._remove_file(file_path)
            
            if key in self._metadata:
                del self._metadata[key]
                await self._save_metadata()
            
            return removed
            
        except Exception as e:
            self.logger.error(f"File cache remove error for key {key}: {e}")
            return False
    
    async def clear(self) -> int:
        """Clear all cache files"""
        try:
            removed_count = 0
            
            for file_path in self.cache_dir.glob("*.cache"):
                if await self._remove_file(file_path):
                    removed_count += 1
            
            # Clear metadata
            self._metadata.clear()
            await self._save_metadata()
            
            self.logger.info(f"Cleared {removed_count} cache files")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"File cache clear error: {e}")
            return 0
    
    async def cleanup_expired(self) -> int:
        """Remove expired cache files"""
        try:
            current_time = time.time()
            removed_count = 0
            expired_keys = []
            
            for key, metadata in self._metadata.items():
                if current_time > metadata.get('expires', 0):
                    expired_keys.append(key)
            
            for key in expired_keys:
                if await self.remove(key):
                    removed_count += 1
            
            # Also check for orphaned files
            for file_path in self.cache_dir.glob("*.cache"):
                if file_path.stem not in self._metadata:
                    if await self._remove_file(file_path):
                        removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} expired cache files")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"File cache cleanup error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is valid"""
        return self._is_valid(key) and self._get_file_path(key).exists()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_size = 0
            valid_files = 0
            expired_files = 0
            current_time = time.time()
            
            for key, metadata in self._metadata.items():
                total_size += metadata.get('size', 0)
                if current_time <= metadata.get('expires', 0):
                    valid_files += 1
                else:
                    expired_files += 1
            
            return {
                'cache_dir': str(self.cache_dir),
                'total_files': len(self._metadata),
                'valid_files': valid_files,
                'expired_files': expired_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'default_ttl': self.default_ttl,
                'max_file_size': self.max_file_size,
                'serializer': self.serializer
            }
            
        except Exception as e:
            self.logger.error(f"Stats error: {e}")
            return {}
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Hash key to avoid filesystem issues
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _is_valid(self, key: str) -> bool:
        """Check if cache key is still valid"""
        if key not in self._metadata:
            return False
        
        metadata = self._metadata[key]
        current_time = time.time()
        return current_time <= metadata.get('expires', 0)
    
    async def _remove_file(self, file_path: Path) -> bool:
        """Remove cache file"""
        try:
            if file_path.exists():
                await asyncio.get_event_loop().run_in_executor(
                    None, file_path.unlink
                )
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing file {file_path}: {e}")
            return False
    
    def _load_metadata(self):
        """Load cache metadata"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self._metadata = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading metadata: {e}")
            self._metadata = {}
    
    async def _save_metadata(self):
        """Save cache metadata"""
        try:
            temp_file = self.metadata_file.with_suffix('.tmp')
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(self._metadata, indent=2))
            
            # Atomic move
            await asyncio.get_event_loop().run_in_executor(
                None, temp_file.rename, self.metadata_file
            )
            
        except Exception as e:
            self.logger.error(f"Error saving metadata: {e}")
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop, cleanup will be manual
            pass
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired files"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Periodic cleanup error: {e}")
    
    async def close(self):
        """Close the file cache"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self._save_metadata()
        self.logger.info("File cache closed")


# Global file cache instance
_global_file_cache: Optional[FileCache] = None


def get_file_cache(cache_dir: str = ".cache") -> FileCache:
    """Get global file cache instance"""
    global _global_file_cache
    if _global_file_cache is None:
        _global_file_cache = FileCache(cache_dir=cache_dir)
    return _global_file_cache