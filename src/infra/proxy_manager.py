"""
Proxy Manager for Rotation and Anti-Detection

Handles proxy rotation using a pool of providers, supporting both
per-session and per-request proxy assignment with health monitoring.
"""

import logging
import random
import time
import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from urllib.parse import urlparse
import json


class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    ACTIVE = "active"
    FAILED = "failed"
    TESTING = "testing"
    DISABLED = "disabled"


@dataclass
class ProxyInfo:
    """Information about a proxy server"""
    host: str
    port: int
    proxy_type: ProxyType
    username: Optional[str] = None
    password: Optional[str] = None
    status: ProxyStatus = ProxyStatus.ACTIVE
    provider: str = "unknown"
    country: Optional[str] = None
    city: Optional[str] = None
    last_used: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0
    response_time: Optional[float] = None
    max_failures: int = 5
    cooldown_time: int = 300  # 5 minutes

    @property
    def proxy_url(self) -> str:
        """Get formatted proxy URL"""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is considered healthy"""
        if self.status != ProxyStatus.ACTIVE:
            return False
        
        if self.failure_count >= self.max_failures:
            return False
        
        # Check if in cooldown
        if self.last_used and (time.time() - self.last_used) < self.cooldown_time:
            if self.failure_count > 0:
                return False
        
        return True
    
    def record_success(self, response_time: float):
        """Record a successful proxy usage"""
        self.success_count += 1
        self.response_time = response_time
        self.last_used = time.time()
        self.status = ProxyStatus.ACTIVE
        # Reset failure count on success
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a proxy failure"""
        self.failure_count += 1
        self.last_used = time.time()
        
        if self.failure_count >= self.max_failures:
            self.status = ProxyStatus.FAILED


class ProxyManager:
    """
    Manages proxy rotation and health monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Proxy pool
        self.proxies: List[ProxyInfo] = []
        self.proxy_providers: Dict[str, Dict[str, Any]] = {}
        
        # Rotation settings
        self.rotation_mode = self.config.get("rotation_mode", "round_robin")  # round_robin, random, weighted
        self.current_index = 0
        
        # Health check settings
        self.health_check_enabled = self.config.get("health_check_enabled", True)
        self.health_check_interval = self.config.get("health_check_interval", 300)  # 5 minutes
        self.health_check_url = self.config.get("health_check_url", "http://httpbin.org/ip")
        
        # Load proxies from configuration
        self._load_proxies()
        
        # Start health monitoring if enabled
        if self.health_check_enabled and self.proxies:
            self._start_health_monitoring()
        
        self.logger.info(f"Initialized ProxyManager with {len(self.proxies)} proxies")
    
    def _load_proxies(self):
        """Load proxies from configuration"""
        # Load from direct proxy list
        proxy_list = self.config.get("proxies", [])
        for proxy_data in proxy_list:
            proxy = self._create_proxy_from_config(proxy_data)
            if proxy:
                self.proxies.append(proxy)
        
        # Load from proxy providers
        providers = self.config.get("proxy_providers", {})
        for provider_name, provider_config in providers.items():
            self.proxy_providers[provider_name] = provider_config
            provider_proxies = self._load_from_provider(provider_name, provider_config)
            self.proxies.extend(provider_proxies)
    
    def _create_proxy_from_config(self, proxy_data: Dict[str, Any]) -> Optional[ProxyInfo]:
        """Create ProxyInfo from configuration data"""
        try:
            proxy = ProxyInfo(
                host=proxy_data["host"],
                port=proxy_data["port"],
                proxy_type=ProxyType(proxy_data.get("type", "http")),
                username=proxy_data.get("username"),
                password=proxy_data.get("password"),
                provider=proxy_data.get("provider", "manual"),
                country=proxy_data.get("country"),
                city=proxy_data.get("city"),
                max_failures=proxy_data.get("max_failures", 5)
            )
            return proxy
        except Exception as e:
            self.logger.error(f"Error creating proxy from config: {e}")
            return None
    
    def _load_from_provider(self, provider_name: str, provider_config: Dict[str, Any]) -> List[ProxyInfo]:
        """Load proxies from a provider (placeholder for provider integration)"""
        # This is a placeholder for provider-specific loading logic
        # In a real implementation, this would integrate with proxy providers' APIs
        
        provider_type = provider_config.get("type", "api")
        proxies = []
        
        if provider_type == "file":
            # Load from file
            file_path = provider_config.get("file_path")
            if file_path:
                proxies = self._load_from_file(file_path, provider_name)
        
        elif provider_type == "api":
            # Load from API (placeholder)
            self.logger.info(f"Provider {provider_name} API integration not implemented yet")
        
        return proxies
    
    def _load_from_file(self, file_path: str, provider_name: str) -> List[ProxyInfo]:
        """Load proxies from a file"""
        proxies = []
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy = self._parse_proxy_line(line, provider_name)
                    if proxy:
                        proxies.append(proxy)
        
        except Exception as e:
            self.logger.error(f"Error loading proxies from file {file_path}: {e}")
        
        return proxies
    
    def _parse_proxy_line(self, line: str, provider_name: str) -> Optional[ProxyInfo]:
        """Parse a proxy line in various formats"""
        try:
            # Format: host:port or host:port:username:password
            parts = line.split(':')
            
            if len(parts) >= 2:
                proxy = ProxyInfo(
                    host=parts[0],
                    port=int(parts[1]),
                    proxy_type=ProxyType.HTTP,  # Default
                    username=parts[2] if len(parts) > 2 else None,
                    password=parts[3] if len(parts) > 3 else None,
                    provider=provider_name
                )
                return proxy
        
        except Exception as e:
            self.logger.error(f"Error parsing proxy line '{line}': {e}")
        
        return None
    
    def get_proxy(self, 
                  session_id: Optional[str] = None,
                  domain: Optional[str] = None,
                  prefer_country: Optional[str] = None) -> Optional[ProxyInfo]:
        """
        Get a proxy for use
        
        Args:
            session_id: Optional session ID for session-specific rotation
            domain: Optional domain for domain-specific preferences
            prefer_country: Preferred country for proxy location
            
        Returns:
            Selected ProxyInfo or None if no healthy proxies available
        """
        # Get healthy proxies
        healthy_proxies = [p for p in self.proxies if p.is_healthy]
        
        if not healthy_proxies:
            self.logger.warning("No healthy proxies available")
            return None
        
        # Apply filters
        candidates = healthy_proxies
        
        # Country preference
        if prefer_country:
            country_proxies = [p for p in candidates if p.country == prefer_country]
            if country_proxies:
                candidates = country_proxies
        
        # Domain-specific logic
        if domain:
            domain_candidates = self._filter_by_domain(candidates, domain)
            if domain_candidates:
                candidates = domain_candidates
        
        # Select based on rotation mode
        selected_proxy = self._select_proxy(candidates, session_id)
        
        if selected_proxy:
            self.logger.debug(f"Selected proxy: {selected_proxy.host}:{selected_proxy.port} "
                             f"({selected_proxy.provider})")
        
        return selected_proxy
    
    def _filter_by_domain(self, proxies: List[ProxyInfo], domain: str) -> List[ProxyInfo]:
        """Apply domain-specific proxy filtering"""
        domain_lower = domain.lower()
        
        # For search engines, prefer diverse geographic distribution
        if any(search in domain_lower for search in ["bing.com", "google.com", "duckduckgo.com"]):
            # Prefer proxies from different countries
            countries_used = set()
            diverse_proxies = []
            
            for proxy in proxies:
                if proxy.country not in countries_used or len(diverse_proxies) < 3:
                    diverse_proxies.append(proxy)
                    if proxy.country:
                        countries_used.add(proxy.country)
            
            if diverse_proxies:
                return diverse_proxies
        
        # For specific regions, prefer local proxies
        if any(region in domain_lower for region in [".co.uk", ".ca", ".au", ".de", ".fr"]):
            region_map = {
                ".co.uk": "UK",
                ".ca": "CA", 
                ".au": "AU",
                ".de": "DE",
                ".fr": "FR"
            }
            
            for suffix, country in region_map.items():
                if suffix in domain_lower:
                    local_proxies = [p for p in proxies if p.country == country]
                    if local_proxies:
                        return local_proxies
        
        return proxies
    
    def _select_proxy(self, candidates: List[ProxyInfo], session_id: Optional[str] = None) -> Optional[ProxyInfo]:
        """Select a proxy based on rotation mode"""
        if not candidates:
            return None
        
        if self.rotation_mode == "random":
            return random.choice(candidates)
        
        elif self.rotation_mode == "weighted":
            return self._weighted_selection(candidates)
        
        elif self.rotation_mode == "round_robin":
            if session_id:
                # Session-specific round robin
                session_hash = hash(session_id) % len(candidates)
                return candidates[session_hash]
            else:
                # Global round robin
                self.current_index = (self.current_index + 1) % len(candidates)
                return candidates[self.current_index]
        
        else:
            # Default: first available
            return candidates[0]
    
    def _weighted_selection(self, candidates: List[ProxyInfo]) -> ProxyInfo:
        """Select proxy using weighted selection based on performance"""
        # Calculate weights based on success rate and response time
        weights = []
        
        for proxy in candidates:
            total_requests = proxy.success_count + proxy.failure_count
            if total_requests == 0:
                weight = 1.0  # Neutral weight for unused proxies
            else:
                success_rate = proxy.success_count / total_requests
                # Factor in response time (lower is better)
                time_factor = 1.0
                if proxy.response_time:
                    time_factor = max(0.1, 1.0 / proxy.response_time)
                
                weight = success_rate * time_factor
            
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(candidates)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return candidates[i]
        
        return candidates[-1]
    
    def record_proxy_result(self, proxy: ProxyInfo, success: bool, response_time: Optional[float] = None):
        """Record the result of using a proxy"""
        if success:
            proxy.record_success(response_time or 1.0)
            self.logger.debug(f"Proxy {proxy.host}:{proxy.port} succeeded "
                             f"(success_rate: {proxy.success_count}/{proxy.success_count + proxy.failure_count})")
        else:
            proxy.record_failure()
            self.logger.warning(f"Proxy {proxy.host}:{proxy.port} failed "
                               f"(failures: {proxy.failure_count}/{proxy.max_failures})")
    
    def _start_health_monitoring(self):
        """Start background health monitoring for proxies"""
        def health_check_worker():
            while True:
                try:
                    self._perform_health_checks()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    self.logger.error(f"Error in health check worker: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        import threading
        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()
        self.logger.info("Started proxy health monitoring")
    
    def _perform_health_checks(self):
        """Perform health checks on all proxies"""
        self.logger.debug("Performing proxy health checks")
        
        for proxy in self.proxies:
            # Skip recently checked proxies
            if proxy.last_used and (time.time() - proxy.last_used) < 60:
                continue
            
            # Skip failed proxies temporarily
            if proxy.status == ProxyStatus.FAILED:
                # Allow recovery after cooldown
                if time.time() - proxy.last_used > proxy.cooldown_time * 2:
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.failure_count = 0
                continue
            
            # Perform health check
            self._check_proxy_health(proxy)
    
    def _check_proxy_health(self, proxy: ProxyInfo):
        """Check the health of a specific proxy"""
        try:
            proxy.status = ProxyStatus.TESTING
            start_time = time.time()
            
            proxies = {
                'http': proxy.proxy_url,
                'https': proxy.proxy_url
            }
            
            response = requests.get(
                self.health_check_url,
                proxies=proxies,
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                proxy.record_success(response_time)
            else:
                proxy.record_failure()
        
        except Exception as e:
            proxy.record_failure()
            self.logger.debug(f"Health check failed for {proxy.host}:{proxy.port}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get proxy usage and health statistics"""
        total_proxies = len(self.proxies)
        healthy_proxies = len([p for p in self.proxies if p.is_healthy])
        failed_proxies = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
        
        # Provider breakdown
        provider_stats = {}
        for proxy in self.proxies:
            provider = proxy.provider
            if provider not in provider_stats:
                provider_stats[provider] = {"total": 0, "healthy": 0, "failed": 0}
            
            provider_stats[provider]["total"] += 1
            if proxy.is_healthy:
                provider_stats[provider]["healthy"] += 1
            elif proxy.status == ProxyStatus.FAILED:
                provider_stats[provider]["failed"] += 1
        
        return {
            "total_proxies": total_proxies,
            "healthy_proxies": healthy_proxies,
            "failed_proxies": failed_proxies,
            "health_percentage": round((healthy_proxies / total_proxies * 100), 2) if total_proxies > 0 else 0,
            "provider_breakdown": provider_stats,
            "rotation_mode": self.rotation_mode
        }
    
    def reset_all_proxies(self):
        """Reset all proxy statistics and statuses"""
        for proxy in self.proxies:
            proxy.success_count = 0
            proxy.failure_count = 0
            proxy.status = ProxyStatus.ACTIVE
            proxy.last_used = None
            proxy.response_time = None
        
        self.logger.info("Reset all proxy statistics")


# Factory function for easy creation
def create_proxy_manager(
    proxies: Optional[List[Dict[str, Any]]] = None,
    rotation_mode: str = "round_robin",
    health_check_enabled: bool = True
) -> ProxyManager:
    """
    Factory function to create a ProxyManager
    
    Args:
        proxies: List of proxy configurations
        rotation_mode: Proxy rotation strategy
        health_check_enabled: Whether to enable health monitoring
        
    Returns:
        Configured ProxyManager instance
    """
    config = {
        "proxies": proxies or [],
        "rotation_mode": rotation_mode,
        "health_check_enabled": health_check_enabled
    }
    
    return ProxyManager(config)