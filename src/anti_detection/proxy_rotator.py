"""
Advanced Proxy Rotation and Management System

Handles proxy pool management, rotation strategies, health monitoring,
and geographic distribution for anti-detection web scraping.
"""

import logging
import random
import time
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import threading


class ProxyType(Enum):
    """Types of proxy protocols"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    """Proxy health status"""
    ACTIVE = "active"
    FAILED = "failed"
    TESTING = "testing"
    DISABLED = "disabled"
    COOLDOWN = "cooldown"


class ProxyProvider(Enum):
    """Supported proxy providers"""
    MANUAL = "manual"
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    ROTATING = "rotating"
    FREE = "free"


@dataclass
class ProxyInfo:
    """Comprehensive proxy information and statistics"""
    host: str
    port: int
    proxy_type: ProxyType
    provider: ProxyProvider = ProxyProvider.MANUAL
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Geographic information
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    timezone: Optional[str] = None
    
    # Health and performance
    status: ProxyStatus = ProxyStatus.ACTIVE
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[float] = None
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    response_time: Optional[float] = None
    avg_response_time: float = 0.0
    
    # Configuration
    max_failures: int = 5
    cooldown_seconds: int = 300
    timeout_seconds: int = 30
    
    # Session tracking
    active_sessions: int = 0
    total_sessions: int = 0
    concurrent_limit: int = 3
    
    # Detection indicators
    detection_events: int = 0
    cloudflare_blocks: int = 0
    rate_limit_hits: int = 0
    
    @property
    def proxy_url(self) -> str:
        """Get formatted proxy URL"""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is healthy and available"""
        if self.status not in [ProxyStatus.ACTIVE, ProxyStatus.COOLDOWN]:
            return False
        
        # Check failure threshold
        if self.failure_count >= self.max_failures:
            return False
        
        # Check cooldown period
        if (self.status == ProxyStatus.COOLDOWN and 
            self.last_failure and 
            time.time() - self.last_failure < self.cooldown_seconds):
            return False
        
        # Check concurrent usage limit
        if self.active_sessions >= self.concurrent_limit:
            return False
        
        return True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability score (0.0 to 1.0)"""
        if self.success_count + self.failure_count == 0:
            return 0.5  # Neutral for untested proxies
        
        # Base score from success rate
        base_score = self.success_rate / 100.0
        
        # Penalty for detection events
        detection_penalty = min(0.3, self.detection_events * 0.1)
        
        # Bonus for response time (faster is better)
        time_bonus = 0.0
        if self.avg_response_time > 0:
            if self.avg_response_time < 1.0:
                time_bonus = 0.1
            elif self.avg_response_time < 2.0:
                time_bonus = 0.05
        
        final_score = max(0.0, min(1.0, base_score - detection_penalty + time_bonus))
        return final_score
    
    def record_success(self, response_time: float):
        """Record successful proxy usage"""
        self.success_count += 1
        self.last_success = time.time()
        self.last_used = time.time()
        self.response_time = response_time
        
        # Update average response time
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time + response_time) / 2
        
        # Reset status if was in cooldown
        if self.status == ProxyStatus.COOLDOWN:
            self.status = ProxyStatus.ACTIVE
        
        # Reduce failure count on success (gradual recovery)
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self, error_type: Optional[str] = None):
        """Record proxy failure"""
        self.failure_count += 1
        self.last_failure = time.time()
        self.last_used = time.time()
        
        # Categorize detection events
        if error_type:
            error_lower = error_type.lower()
            if "cloudflare" in error_lower or "cf-ray" in error_lower:
                self.cloudflare_blocks += 1
                self.detection_events += 1
            elif "rate limit" in error_lower or "429" in error_lower:
                self.rate_limit_hits += 1
                self.detection_events += 1
            elif "captcha" in error_lower or "recaptcha" in error_lower:
                self.detection_events += 1
        
        # Update status based on failure count
        if self.failure_count >= self.max_failures:
            self.status = ProxyStatus.FAILED
        else:
            self.status = ProxyStatus.COOLDOWN
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxyInfo':
        """Create from dictionary"""
        # Convert enum strings back to enums
        if 'proxy_type' in data and isinstance(data['proxy_type'], str):
            data['proxy_type'] = ProxyType(data['proxy_type'])
        if 'provider' in data and isinstance(data['provider'], str):
            data['provider'] = ProxyProvider(data['provider'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ProxyStatus(data['status'])
        
        return cls(**data)


@dataclass
class RotationConfig:
    """Configuration for proxy rotation strategies"""
    rotation_strategy: str = "weighted"  # weighted, round_robin, random, geographic
    rotation_interval: int = 600  # seconds
    max_requests_per_proxy: int = 100
    geographic_distribution: bool = True
    sticky_sessions: bool = True
    health_check_enabled: bool = True
    health_check_interval: int = 300
    health_check_url: str = "http://httpbin.org/ip"
    concurrent_health_checks: int = 5


class ProxyRotator:
    """
    Advanced proxy rotation and management system
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Proxy pool management
        self.proxies: List[ProxyInfo] = []
        self.proxy_index: Dict[str, int] = {}  # proxy_id -> index
        
        # Rotation configuration
        self.rotation_config = RotationConfig(**self.config.get("rotation", {}))
        
        # Session tracking
        self.session_proxies: Dict[str, ProxyInfo] = {}
        self.proxy_sessions: Dict[str, List[str]] = defaultdict(list)
        
        # Statistics and monitoring
        self.request_history: deque = deque(maxlen=10000)
        self.proxy_usage_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Geographic distribution tracking
        self.country_usage: Dict[str, int] = defaultdict(int)
        self.region_rotation_index: Dict[str, int] = defaultdict(int)
        
        # Health monitoring
        self.health_monitor_active = False
        self.health_check_lock = threading.Lock()
        
        # Load proxies from configuration
        self._load_proxies()
        
        # Start health monitoring if enabled
        if self.rotation_config.health_check_enabled and self.proxies:
            self._start_health_monitoring()
        
        self.logger.info(f"ProxyRotator initialized with {len(self.proxies)} proxies")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for proxy rotator"""
        logger = logging.getLogger("proxy_rotator")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_proxies(self):
        """Load proxies from various sources"""
        # Load from direct proxy list
        proxy_list = self.config.get("proxies", [])
        for proxy_data in proxy_list:
            proxy = self._create_proxy_from_config(proxy_data)
            if proxy:
                self.add_proxy(proxy)
        
        # Load from files
        proxy_files = self.config.get("proxy_files", [])
        for file_path in proxy_files:
            self._load_proxies_from_file(file_path)
        
        # Load from providers (future implementation)
        providers = self.config.get("providers", {})
        for provider_name, provider_config in providers.items():
            self.logger.info(f"Provider {provider_name} integration not implemented yet")
    
    def _create_proxy_from_config(self, proxy_data: Dict[str, Any]) -> Optional[ProxyInfo]:
        """Create ProxyInfo from configuration data"""
        try:
            return ProxyInfo(
                host=proxy_data["host"],
                port=proxy_data["port"],
                proxy_type=ProxyType(proxy_data.get("type", "http")),
                provider=ProxyProvider(proxy_data.get("provider", "manual")),
                username=proxy_data.get("username"),
                password=proxy_data.get("password"),
                country=proxy_data.get("country"),
                city=proxy_data.get("city"),
                region=proxy_data.get("region"),
                max_failures=proxy_data.get("max_failures", 5),
                cooldown_seconds=proxy_data.get("cooldown_seconds", 300),
                concurrent_limit=proxy_data.get("concurrent_limit", 3)
            )
        except Exception as e:
            self.logger.error(f"Error creating proxy from config: {e}")
            return None
    
    def _load_proxies_from_file(self, file_path: str):
        """Load proxies from a file"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy = self._parse_proxy_line(line, f"file_{Path(file_path).stem}")
                    if proxy:
                        self.add_proxy(proxy)
                    else:
                        self.logger.warning(f"Invalid proxy line {line_num} in {file_path}: {line}")
        
        except Exception as e:
            self.logger.error(f"Error loading proxies from {file_path}: {e}")
    
    def _parse_proxy_line(self, line: str, provider_name: str) -> Optional[ProxyInfo]:
        """Parse various proxy line formats"""
        try:
            # Format: host:port or host:port:username:password or protocol://host:port
            if "://" in line:
                # URL format: http://host:port or http://user:pass@host:port
                from urllib.parse import urlparse
                parsed = urlparse(line)
                
                proxy = ProxyInfo(
                    host=parsed.hostname,
                    port=parsed.port,
                    proxy_type=ProxyType(parsed.scheme),
                    username=parsed.username,
                    password=parsed.password,
                    provider=ProxyProvider.MANUAL
                )
            else:
                # host:port:user:pass format
                parts = line.split(':')
                if len(parts) >= 2:
                    proxy = ProxyInfo(
                        host=parts[0],
                        port=int(parts[1]),
                        proxy_type=ProxyType.HTTP,  # Default
                        username=parts[2] if len(parts) > 2 else None,
                        password=parts[3] if len(parts) > 3 else None,
                        provider=ProxyProvider.MANUAL
                    )
                else:
                    return None
            
            return proxy
        
        except Exception as e:
            self.logger.error(f"Error parsing proxy line '{line}': {e}")
            return None
    
    def add_proxy(self, proxy: ProxyInfo):
        """Add a proxy to the rotation pool"""
        proxy_id = f"{proxy.host}:{proxy.port}"
        
        # Check for duplicates
        if proxy_id in self.proxy_index:
            self.logger.warning(f"Proxy {proxy_id} already exists, skipping")
            return
        
        self.proxies.append(proxy)
        self.proxy_index[proxy_id] = len(self.proxies) - 1
        
        self.logger.debug(f"Added proxy {proxy_id} from {proxy.provider.value}")
    
    def remove_proxy(self, host: str, port: int) -> bool:
        """Remove a proxy from the rotation pool"""
        proxy_id = f"{host}:{port}"
        
        if proxy_id not in self.proxy_index:
            return False
        
        index = self.proxy_index[proxy_id]
        removed_proxy = self.proxies.pop(index)
        
        # Update indices
        del self.proxy_index[proxy_id]
        for pid, idx in self.proxy_index.items():
            if idx > index:
                self.proxy_index[pid] = idx - 1
        
        # Clean up session assignments
        sessions_to_clean = []
        for session_id, session_proxy in self.session_proxies.items():
            if session_proxy.host == host and session_proxy.port == port:
                sessions_to_clean.append(session_id)
        
        for session_id in sessions_to_clean:
            del self.session_proxies[session_id]
        
        self.logger.info(f"Removed proxy {proxy_id}")
        return True
    
    async def get_proxy(self, 
                       session_id: Optional[str] = None,
                       domain: Optional[str] = None,
                       country_preference: Optional[str] = None) -> Optional[ProxyInfo]:
        """
        Get a proxy using the configured rotation strategy
        
        Args:
            session_id: Session identifier for sticky sessions
            domain: Target domain for domain-specific preferences
            country_preference: Preferred country code
            
        Returns:
            Selected ProxyInfo or None if no healthy proxies available
        """
        if not self.proxies:
            self.logger.warning("No proxies available")
            return None
        
        # Check for sticky session
        if (session_id and 
            self.rotation_config.sticky_sessions and 
            session_id in self.session_proxies):
            existing_proxy = self.session_proxies[session_id]
            if existing_proxy.is_healthy:
                return existing_proxy
            else:
                # Remove unhealthy sticky proxy
                del self.session_proxies[session_id]
        
        # Get healthy proxy candidates
        candidates = [p for p in self.proxies if p.is_healthy]
        
        if not candidates:
            self.logger.warning("No healthy proxies available")
            return None
        
        # Apply filters
        candidates = self._apply_filters(candidates, domain, country_preference)
        
        if not candidates:
            self.logger.warning("No proxies match the specified criteria")
            return None
        
        # Select proxy using rotation strategy
        selected_proxy = self._select_proxy(candidates, session_id)
        
        # Assign to session if sticky sessions enabled
        if session_id and self.rotation_config.sticky_sessions:
            self.session_proxies[session_id] = selected_proxy
            self.proxy_sessions[f"{selected_proxy.host}:{selected_proxy.port}"].append(session_id)
        
        # Update usage tracking
        selected_proxy.active_sessions += 1
        selected_proxy.total_sessions += 1
        
        self.logger.debug(f"Selected proxy {selected_proxy.host}:{selected_proxy.port} "
                         f"({selected_proxy.provider.value}) for session {session_id}")
        
        return selected_proxy
    
    def _apply_filters(self, 
                      candidates: List[ProxyInfo], 
                      domain: Optional[str], 
                      country_preference: Optional[str]) -> List[ProxyInfo]:
        """Apply various filters to proxy candidates"""
        
        # Country preference filter
        if country_preference:
            country_candidates = [p for p in candidates if p.country == country_preference]
            if country_candidates:
                candidates = country_candidates
        
        # Domain-specific filters
        if domain:
            domain_candidates = self._filter_by_domain(candidates, domain)
            if domain_candidates:
                candidates = domain_candidates
        
        # Geographic distribution filter
        if self.rotation_config.geographic_distribution:
            candidates = self._apply_geographic_distribution(candidates)
        
        return candidates
    
    def _filter_by_domain(self, candidates: List[ProxyInfo], domain: str) -> List[ProxyInfo]:
        """Apply domain-specific proxy filtering"""
        domain_lower = domain.lower()
        
        # For search engines, prefer diverse geographic distribution
        if any(se in domain_lower for se in ["bing.com", "google.com", "duckduckgo.com"]):
            # Prefer proxies with good success rates for search engines
            search_candidates = [p for p in candidates if p.success_rate >= 70 or p.success_count == 0]
            if search_candidates:
                return search_candidates
        
        # For region-specific domains, prefer local proxies
        region_mapping = {
            ".co.uk": "UK", ".uk": "UK",
            ".ca": "CA", ".canada": "CA", 
            ".au": "AU", ".australia": "AU",
            ".de": "DE", ".germany": "DE",
            ".fr": "FR", ".france": "FR",
            ".jp": "JP", ".japan": "JP",
            ".cn": "CN", ".china": "CN"
        }
        
        for suffix, country in region_mapping.items():
            if suffix in domain_lower:
                local_candidates = [p for p in candidates if p.country == country]
                if local_candidates:
                    return local_candidates
        
        return candidates
    
    def _apply_geographic_distribution(self, candidates: List[ProxyInfo]) -> List[ProxyInfo]:
        """Apply geographic distribution to avoid concentration in one region"""
        if len(candidates) <= 3:
            return candidates
        
        # Group by country
        country_groups = defaultdict(list)
        for proxy in candidates:
            country = proxy.country or "unknown"
            country_groups[country].append(proxy)
        
        # Select proxies ensuring geographic diversity
        distributed_candidates = []
        countries = list(country_groups.keys())
        
        # Prioritize less-used countries
        countries.sort(key=lambda c: self.country_usage.get(c, 0))
        
        for country in countries:
            if len(distributed_candidates) >= min(10, len(candidates)):
                break
            
            # Add best proxies from this country
            country_proxies = country_groups[country]
            country_proxies.sort(key=lambda p: p.reliability_score, reverse=True)
            
            # Add up to 2 proxies per country
            for proxy in country_proxies[:2]:
                distributed_candidates.append(proxy)
                if len(distributed_candidates) >= min(10, len(candidates)):
                    break
        
        return distributed_candidates or candidates
    
    def _select_proxy(self, candidates: List[ProxyInfo], session_id: Optional[str]) -> ProxyInfo:
        """Select proxy based on rotation strategy"""
        strategy = self.rotation_config.rotation_strategy
        
        if strategy == "weighted":
            return self._weighted_selection(candidates)
        elif strategy == "round_robin":
            return self._round_robin_selection(candidates, session_id)
        elif strategy == "random":
            return random.choice(candidates)
        elif strategy == "geographic":
            return self._geographic_selection(candidates)
        else:
            # Default: best reliability score
            return max(candidates, key=lambda p: p.reliability_score)
    
    def _weighted_selection(self, candidates: List[ProxyInfo]) -> ProxyInfo:
        """Select proxy using weighted random selection based on reliability"""
        weights = []
        
        for proxy in candidates:
            # Base weight from reliability score
            weight = max(0.1, proxy.reliability_score)
            
            # Bonus for unused proxies
            if proxy.success_count == 0 and proxy.failure_count == 0:
                weight *= 1.5
            
            # Penalty for recently used proxies
            if proxy.last_used:
                time_since_use = time.time() - proxy.last_used
                if time_since_use < 60:  # 1 minute
                    weight *= 0.3
                elif time_since_use < 300:  # 5 minutes
                    weight *= 0.7
            
            # Penalty for high concurrent usage
            if proxy.active_sessions > 0:
                weight *= 0.8 ** proxy.active_sessions
            
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
    
    def _round_robin_selection(self, candidates: List[ProxyInfo], session_id: Optional[str]) -> ProxyInfo:
        """Select proxy using round-robin strategy"""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        # Sort candidates by ID for consistent ordering
        sorted_candidates = sorted(candidates, key=lambda p: f"{p.host}:{p.port}")
        
        self._round_robin_index = (self._round_robin_index + 1) % len(sorted_candidates)
        return sorted_candidates[self._round_robin_index]
    
    def _geographic_selection(self, candidates: List[ProxyInfo]) -> ProxyInfo:
        """Select proxy prioritizing geographic distribution"""
        # Group by country and select from least used country
        country_groups = defaultdict(list)
        for proxy in candidates:
            country = proxy.country or "unknown"
            country_groups[country].append(proxy)
        
        # Find least used country
        min_usage = min(self.country_usage.get(country, 0) for country in country_groups.keys())
        least_used_countries = [country for country in country_groups.keys() 
                               if self.country_usage.get(country, 0) == min_usage]
        
        selected_country = random.choice(least_used_countries)
        country_proxies = country_groups[selected_country]
        
        # Select best proxy from the chosen country
        return max(country_proxies, key=lambda p: p.reliability_score)
    
    async def rotate_proxy(self, session_id: str) -> Optional[ProxyInfo]:
        """Force rotation of proxy for a session"""
        if session_id in self.session_proxies:
            old_proxy = self.session_proxies[session_id]
            old_proxy.active_sessions = max(0, old_proxy.active_sessions - 1)
            
            # Remove from session assignments
            proxy_id = f"{old_proxy.host}:{old_proxy.port}"
            if proxy_id in self.proxy_sessions:
                try:
                    self.proxy_sessions[proxy_id].remove(session_id)
                except ValueError:
                    pass
            
            del self.session_proxies[session_id]
        
        # Get new proxy
        new_proxy = await self.get_proxy(session_id)
        
        if new_proxy:
            self.logger.info(f"Rotated proxy for session {session_id}: "
                           f"{new_proxy.host}:{new_proxy.port}")
        
        return new_proxy
    
    def record_request_result(self, 
                             proxy: ProxyInfo,
                             success: bool,
                             response_time: Optional[float] = None,
                             error_type: Optional[str] = None):
        """Record the result of using a proxy"""
        if success:
            proxy.record_success(response_time or 1.0)
        else:
            proxy.record_failure(error_type)
        
        # Update country usage statistics
        if proxy.country:
            if success:
                self.country_usage[proxy.country] = self.country_usage.get(proxy.country, 0) + 1
        
        # Log significant events
        if not success:
            self.logger.warning(f"Proxy {proxy.host}:{proxy.port} failed: {error_type}")
        elif proxy.success_rate < 50 and proxy.success_count + proxy.failure_count >= 10:
            self.logger.warning(f"Proxy {proxy.host}:{proxy.port} has low success rate: "
                               f"{proxy.success_rate:.1f}%")
    
    def release_proxy(self, proxy: ProxyInfo, session_id: Optional[str] = None):
        """Release a proxy when session is complete"""
        proxy.active_sessions = max(0, proxy.active_sessions - 1)
        
        if session_id:
            # Remove from session tracking
            if session_id in self.session_proxies:
                del self.session_proxies[session_id]
            
            proxy_id = f"{proxy.host}:{proxy.port}"
            if proxy_id in self.proxy_sessions:
                try:
                    self.proxy_sessions[proxy_id].remove(session_id)
                except ValueError:
                    pass
    
    def _start_health_monitoring(self):
        """Start background health monitoring for proxies"""
        if self.health_monitor_active:
            return
        
        self.health_monitor_active = True
        
        def health_monitor_worker():
            while self.health_monitor_active:
                try:
                    asyncio.run(self._perform_health_checks())
                    time.sleep(self.rotation_config.health_check_interval)
                except Exception as e:
                    self.logger.error(f"Health monitor error: {e}")
                    time.sleep(60)
        
        health_thread = threading.Thread(target=health_monitor_worker, daemon=True)
        health_thread.start()
        self.logger.info("Started proxy health monitoring")
    
    async def _perform_health_checks(self):
        """Perform health checks on all proxies"""
        with self.health_check_lock:
            unhealthy_proxies = [p for p in self.proxies if not p.is_healthy]
            
            if not unhealthy_proxies:
                return
            
            self.logger.debug(f"Performing health checks on {len(unhealthy_proxies)} proxies")
            
            # Limit concurrent health checks
            semaphore = asyncio.Semaphore(self.rotation_config.concurrent_health_checks)
            
            tasks = [self._check_proxy_health(proxy, semaphore) for proxy in unhealthy_proxies]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_proxy_health(self, proxy: ProxyInfo, semaphore: asyncio.Semaphore):
        """Check health of a specific proxy"""
        async with semaphore:
            try:
                proxy.status = ProxyStatus.TESTING
                start_time = time.time()
                
                timeout = aiohttp.ClientTimeout(total=proxy.timeout_seconds)
                proxy_url = proxy.proxy_url
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(
                        self.rotation_config.health_check_url,
                        proxy=proxy_url
                    ) as response:
                        response_time = time.time() - start_time
                        
                        if response.status == 200:
                            proxy.record_success(response_time)
                        else:
                            proxy.record_failure(f"HTTP {response.status}")
            
            except Exception as e:
                proxy.record_failure(str(e))
                self.logger.debug(f"Health check failed for {proxy.host}:{proxy.port}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive proxy pool statistics"""
        if not self.proxies:
            return {"total_proxies": 0}
        
        healthy_count = sum(1 for p in self.proxies if p.is_healthy)
        active_count = sum(1 for p in self.proxies if p.status == ProxyStatus.ACTIVE)
        failed_count = sum(1 for p in self.proxies if p.status == ProxyStatus.FAILED)
        
        # Provider breakdown
        provider_stats = defaultdict(lambda: {"total": 0, "healthy": 0, "active": 0})
        for proxy in self.proxies:
            provider = proxy.provider.value
            provider_stats[provider]["total"] += 1
            if proxy.is_healthy:
                provider_stats[provider]["healthy"] += 1
            if proxy.status == ProxyStatus.ACTIVE:
                provider_stats[provider]["active"] += 1
        
        # Country distribution
        country_stats = defaultdict(int)
        for proxy in self.proxies:
            country = proxy.country or "unknown"
            country_stats[country] += 1
        
        # Performance metrics
        success_rates = [p.success_rate for p in self.proxies if p.success_count + p.failure_count > 0]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        response_times = [p.avg_response_time for p in self.proxies if p.avg_response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": healthy_count,
            "active_proxies": active_count,
            "failed_proxies": failed_count,
            "health_percentage": (healthy_count / len(self.proxies) * 100) if self.proxies else 0,
            "active_sessions": sum(p.active_sessions for p in self.proxies),
            "provider_breakdown": dict(provider_stats),
            "country_distribution": dict(country_stats),
            "average_success_rate": round(avg_success_rate, 2),
            "average_response_time": round(avg_response_time, 2),
            "rotation_strategy": self.rotation_config.rotation_strategy,
            "geographic_distribution": self.rotation_config.geographic_distribution
        }
    
    def export_proxy_pool(self, file_path: str):
        """Export proxy pool configuration to file"""
        proxy_data = []
        for proxy in self.proxies:
            proxy_dict = proxy.to_dict()
            # Convert enums to strings for JSON serialization
            proxy_dict['proxy_type'] = proxy_dict['proxy_type'].value
            proxy_dict['provider'] = proxy_dict['provider'].value
            proxy_dict['status'] = proxy_dict['status'].value
            proxy_data.append(proxy_dict)
        
        with open(file_path, 'w') as f:
            json.dump({
                "proxies": proxy_data,
                "config": asdict(self.rotation_config),
                "exported_at": time.time()
            }, f, indent=2)
        
        self.logger.info(f"Exported {len(proxy_data)} proxies to {file_path}")
    
    def import_proxy_pool(self, file_path: str):
        """Import proxy pool configuration from file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        imported_count = 0
        for proxy_dict in data.get("proxies", []):
            try:
                proxy = ProxyInfo.from_dict(proxy_dict)
                self.add_proxy(proxy)
                imported_count += 1
            except Exception as e:
                self.logger.error(f"Error importing proxy {proxy_dict.get('host')}: {e}")
        
        self.logger.info(f"Imported {imported_count} proxies from {file_path}")
    
    def stop_health_monitoring(self):
        """Stop background health monitoring"""
        self.health_monitor_active = False
        self.logger.info("Stopped proxy health monitoring")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_health_monitoring()


# Factory function for easy creation
def create_proxy_rotator(proxy_list: Optional[List[Dict[str, Any]]] = None,
                        rotation_strategy: str = "weighted",
                        health_check_enabled: bool = True) -> ProxyRotator:
    """
    Factory function to create a ProxyRotator with common configurations
    
    Args:
        proxy_list: List of proxy configurations
        rotation_strategy: Strategy for proxy selection
        health_check_enabled: Whether to enable health monitoring
        
    Returns:
        Configured ProxyRotator instance
    """
    config = {
        "proxies": proxy_list or [],
        "rotation": {
            "rotation_strategy": rotation_strategy,
            "health_check_enabled": health_check_enabled
        }
    }
    
    return ProxyRotator(config)