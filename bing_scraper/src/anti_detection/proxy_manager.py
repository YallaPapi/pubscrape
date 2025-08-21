"""
Proxy Management for Anti-Detection
Handles proxy rotation and configuration for enhanced anonymity.
"""

import random
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ProxyStatus(Enum):
    """Proxy status enumeration."""
    ACTIVE = "active"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"
    TESTING = "testing"

@dataclass
class ProxyInfo:
    """Proxy information container."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"
    status: ProxyStatus = ProxyStatus.TESTING
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[float] = None
    response_time: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate proxy success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def proxy_url(self) -> str:
        """Get formatted proxy URL."""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""
        
        return f"{self.proxy_type}://{auth}{self.host}:{self.port}"

class ProxyManager:
    """Manages proxy rotation and health monitoring."""
    
    def __init__(self, settings):
        """Initialize proxy manager with settings."""
        self.settings = settings
        self.proxies: List[ProxyInfo] = []
        self.current_proxy_index = 0
        self.proxy_rotation_enabled = settings.proxy_enabled
        
        # Load proxies from settings
        if self.proxy_rotation_enabled:
            self._load_proxies_from_settings()
        
        logger.info(f"ProxyManager initialized with {len(self.proxies)} proxies")
    
    def _load_proxies_from_settings(self) -> None:
        """Load proxy configuration from settings."""
        # Load main proxy if configured
        if self.settings.proxy_host and self.settings.proxy_port:
            main_proxy = ProxyInfo(
                host=self.settings.proxy_host,
                port=self.settings.proxy_port,
                username=self.settings.proxy_username,
                password=self.settings.proxy_password,
                proxy_type=self.settings.proxy_type,
                status=ProxyStatus.ACTIVE
            )
            self.proxies.append(main_proxy)
        
        # Load residential proxy pool if configured
        if self.settings.residential_proxy_endpoint:
            residential_proxy = ProxyInfo(
                host=self.settings.residential_proxy_endpoint.split(':')[0],
                port=int(self.settings.residential_proxy_endpoint.split(':')[1]),
                username=self.settings.residential_proxy_username,
                password=self.settings.residential_proxy_password,
                proxy_type="http",
                status=ProxyStatus.ACTIVE
            )
            self.proxies.append(residential_proxy)
        
        logger.info(f"Loaded {len(self.proxies)} proxies from settings")
    
    def add_proxy(self, host: str, port: int, username: Optional[str] = None,
                  password: Optional[str] = None, proxy_type: str = "http") -> None:
        """Add a new proxy to the rotation pool."""
        proxy = ProxyInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type
        )
        self.proxies.append(proxy)
        logger.info(f"Added proxy: {host}:{port}")
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next available proxy configuration.
        
        Returns:
            Proxy configuration dictionary or None if no proxies available
        """
        if not self.proxy_rotation_enabled or not self.proxies:
            return None
        
        # Filter active proxies
        active_proxies = [p for p in self.proxies if p.status == ProxyStatus.ACTIVE]
        
        if not active_proxies:
            logger.warning("No active proxies available")
            return None
        
        # Select proxy based on strategy
        proxy = self._select_best_proxy(active_proxies)
        
        if proxy:
            proxy.last_used = time.time()
            return self._format_proxy_config(proxy)
        
        return None
    
    def _select_best_proxy(self, proxies: List[ProxyInfo]) -> Optional[ProxyInfo]:
        """Select best proxy based on performance metrics."""
        if not proxies:
            return None
        
        # Sort by success rate and response time
        sorted_proxies = sorted(
            proxies,
            key=lambda p: (p.success_rate, -(p.response_time or 999)),
            reverse=True
        )
        
        # Use weighted random selection favoring better proxies
        weights = []
        for i, proxy in enumerate(sorted_proxies):
            # Higher weight for better proxies
            weight = max(1, len(sorted_proxies) - i)
            weights.append(weight)
        
        selected_proxy = random.choices(sorted_proxies, weights=weights)[0]
        logger.debug(f"Selected proxy: {selected_proxy.host}:{selected_proxy.port}")
        
        return selected_proxy
    
    def _format_proxy_config(self, proxy: ProxyInfo) -> Dict[str, str]:
        """Format proxy configuration for use with requests/Botasaurus."""
        config = {
            'host': proxy.host,
            'port': str(proxy.port),
            'type': proxy.proxy_type,
            'url': proxy.proxy_url
        }
        
        if proxy.username:
            config['username'] = proxy.username
        if proxy.password:
            config['password'] = proxy.password
        
        return config
    
    def mark_proxy_success(self, proxy_config: Dict[str, str], 
                          response_time: Optional[float] = None) -> None:
        """Mark proxy as successful."""
        proxy = self._find_proxy_by_config(proxy_config)
        if proxy:
            proxy.success_count += 1
            proxy.status = ProxyStatus.ACTIVE
            if response_time:
                proxy.response_time = response_time
            logger.debug(f"Proxy success: {proxy.host}:{proxy.port}")
    
    def mark_proxy_failure(self, proxy_config: Dict[str, str], 
                          failure_type: str = "general") -> None:
        """Mark proxy as failed."""
        proxy = self._find_proxy_by_config(proxy_config)
        if proxy:
            proxy.failure_count += 1
            
            # Determine status based on failure type
            if failure_type == "rate_limit":
                proxy.status = ProxyStatus.RATE_LIMITED
            elif failure_type == "banned":
                proxy.status = ProxyStatus.BANNED
            elif proxy.failure_count > 5:  # Too many failures
                proxy.status = ProxyStatus.FAILED
            
            logger.warning(f"Proxy failure ({failure_type}): {proxy.host}:{proxy.port}")
    
    def _find_proxy_by_config(self, proxy_config: Dict[str, str]) -> Optional[ProxyInfo]:
        """Find proxy by configuration."""
        host = proxy_config.get('host')
        port = proxy_config.get('port')
        
        if not host or not port:
            return None
        
        for proxy in self.proxies:
            if proxy.host == host and str(proxy.port) == str(port):
                return proxy
        
        return None
    
    def rotate_proxy(self) -> Optional[Dict[str, str]]:
        """Force proxy rotation."""
        if not self.proxies:
            return None
        
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        proxy = self.proxies[self.current_proxy_index]
        
        if proxy.status == ProxyStatus.ACTIVE:
            return self._format_proxy_config(proxy)
        
        # If current proxy is not active, get next available
        return self.get_proxy()
    
    def test_proxy(self, proxy: ProxyInfo) -> bool:
        """
        Test proxy connectivity.
        
        Args:
            proxy: Proxy to test
            
        Returns:
            True if proxy is working
        """
        try:
            import requests
            
            proxy.status = ProxyStatus.TESTING
            
            # Test with simple HTTP request
            proxies = {
                'http': proxy.proxy_url,
                'https': proxy.proxy_url
            }
            
            start_time = time.time()
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                proxy.status = ProxyStatus.ACTIVE
                proxy.response_time = response_time
                proxy.success_count += 1
                logger.info(f"Proxy test passed: {proxy.host}:{proxy.port}")
                return True
            else:
                proxy.status = ProxyStatus.FAILED
                proxy.failure_count += 1
                return False
                
        except Exception as e:
            proxy.status = ProxyStatus.FAILED
            proxy.failure_count += 1
            logger.error(f"Proxy test failed: {proxy.host}:{proxy.port} - {e}")
            return False
    
    def test_all_proxies(self) -> Dict[str, int]:
        """Test all proxies and return results."""
        results = {
            'active': 0,
            'failed': 0,
            'total': len(self.proxies)
        }
        
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                results['active'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"Proxy test results: {results}")
        return results
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get comprehensive proxy statistics."""
        if not self.proxies:
            return {'total': 0, 'enabled': self.proxy_rotation_enabled}
        
        stats = {
            'total': len(self.proxies),
            'enabled': self.proxy_rotation_enabled,
            'active': len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE]),
            'failed': len([p for p in self.proxies if p.status == ProxyStatus.FAILED]),
            'rate_limited': len([p for p in self.proxies if p.status == ProxyStatus.RATE_LIMITED]),
            'banned': len([p for p in self.proxies if p.status == ProxyStatus.BANNED]),
        }
        
        # Calculate average metrics
        active_proxies = [p for p in self.proxies if p.status == ProxyStatus.ACTIVE]
        if active_proxies:
            stats['avg_success_rate'] = sum(p.success_rate for p in active_proxies) / len(active_proxies)
            response_times = [p.response_time for p in active_proxies if p.response_time]
            if response_times:
                stats['avg_response_time'] = sum(response_times) / len(response_times)
        
        return stats
    
    def reset_proxy_stats(self) -> None:
        """Reset all proxy statistics."""
        for proxy in self.proxies:
            proxy.success_count = 0
            proxy.failure_count = 0
            proxy.status = ProxyStatus.TESTING
            proxy.last_used = None
            proxy.response_time = None
        
        logger.info("Proxy statistics reset")
    
    def remove_failed_proxies(self) -> int:
        """Remove permanently failed proxies."""
        initial_count = len(self.proxies)
        self.proxies = [p for p in self.proxies 
                       if p.status not in [ProxyStatus.FAILED, ProxyStatus.BANNED]]
        
        removed = initial_count - len(self.proxies)
        if removed > 0:
            logger.info(f"Removed {removed} failed proxies")
        
        return removed