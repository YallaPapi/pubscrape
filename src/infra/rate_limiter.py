"""
Rate Limiting Manager

Implements comprehensive rate limiting with adaptive delays, exponential backoff,
circuit breakers, and global governors for Bing and target websites.
"""

import logging
import time
import math
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import random
import threading
from urllib.parse import urlparse


class RateLimitStatus(Enum):
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"
    BACKOFF_REQUIRED = "backoff_required"


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit tripped, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    rpm_soft: int = 12              # Soft limit (requests per minute)
    rpm_hard: int = 18              # Hard limit (requests per minute)
    qps_max: float = 0.5            # Max queries per second
    concurrency_limit: int = 3      # Max concurrent requests
    
    # Backoff configuration
    base_backoff_ms: int = 1000     # Base backoff time
    max_backoff_ms: int = 60000     # Maximum backoff time
    backoff_multiplier: float = 2.0 # Exponential backoff multiplier
    jitter_factor: float = 0.1      # Jitter as fraction of backoff
    
    # Circuit breaker configuration
    failure_threshold: int = 5      # Failures before opening circuit
    success_threshold: int = 3      # Successes needed to close circuit
    timeout_seconds: int = 300      # Circuit open timeout (5 minutes)
    
    # Adaptive configuration
    adaptive_enabled: bool = True   # Enable adaptive rate limiting
    response_time_threshold_ms: int = 2000  # Slow response threshold
    
    # Global limits
    global_rpm_limit: int = 100     # Global requests per minute across all domains
    global_concurrency_limit: int = 10  # Global concurrent requests


@dataclass
class RequestRecord:
    """Record of a request for rate limiting calculations"""
    timestamp: float
    domain: str
    success: bool
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    error_type: Optional[str] = None


@dataclass
class CircuitBreaker:
    """Circuit breaker state for a domain"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    next_attempt_time: float = 0
    
    def should_allow_request(self, current_time: float, timeout_seconds: int) -> bool:
        """Check if request should be allowed based on circuit state"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if current_time >= self.next_attempt_time:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False
    
    def record_success(self, current_time: float, success_threshold: int):
        """Record a successful request"""
        self.last_success_time = current_time
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
    
    def record_failure(self, current_time: float, failure_threshold: int, timeout_seconds: int):
        """Record a failed request"""
        self.last_failure_time = current_time
        self.failure_count += 1
        self.success_count = 0
        
        if self.failure_count >= failure_threshold:
            self.state = CircuitState.OPEN
            self.next_attempt_time = current_time + timeout_seconds


class RateLimiter:
    """
    Comprehensive rate limiting with circuit breakers and adaptive behavior
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.logger = logging.getLogger(__name__)
        
        # Request tracking
        self.request_history: deque = deque(maxlen=10000)
        self.domain_requests: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.active_requests: Dict[str, int] = defaultdict(int)
        self.global_active_requests = 0
        
        # Circuit breakers per domain
        self.circuit_breakers: Dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)
        
        # Backoff tracking
        self.domain_backoff: Dict[str, float] = {}  # Domain -> next allowed time
        self.backoff_levels: Dict[str, int] = defaultdict(int)  # Domain -> backoff level
        
        # Adaptive rate limiting
        self.domain_response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.domain_configs: Dict[str, RateLimitConfig] = {}
        
        # Threading locks
        self._lock = threading.RLock()
        
        self.logger.info(f"Initialized RateLimiter with RPM {self.config.rpm_soft}/{self.config.rpm_hard}")
    
    def check_rate_limit(self, 
                        domain: str, 
                        request_id: Optional[str] = None) -> Tuple[RateLimitStatus, float]:
        """
        Check if a request should be allowed and calculate required delay
        
        Args:
            domain: Target domain
            request_id: Optional request identifier
            
        Returns:
            Tuple of (status, delay_seconds)
        """
        with self._lock:
            current_time = time.time()
            
            # Get domain-specific config
            domain_config = self._get_domain_config(domain)
            
            # Check circuit breaker
            circuit = self.circuit_breakers[domain]
            if not circuit.should_allow_request(current_time, domain_config.timeout_seconds):
                return RateLimitStatus.CIRCUIT_OPEN, self._calculate_circuit_delay(circuit, current_time)
            
            # Check backoff requirement
            if domain in self.domain_backoff:
                backoff_until = self.domain_backoff[domain]
                if current_time < backoff_until:
                    delay = backoff_until - current_time
                    return RateLimitStatus.BACKOFF_REQUIRED, delay
            
            # Check global limits
            global_delay = self._check_global_limits(current_time)
            if global_delay > 0:
                return RateLimitStatus.RATE_LIMITED, global_delay
            
            # Check domain-specific limits
            domain_delay = self._check_domain_limits(domain, domain_config, current_time)
            if domain_delay > 0:
                return RateLimitStatus.RATE_LIMITED, domain_delay
            
            # Check concurrency limits
            concurrency_delay = self._check_concurrency_limits(domain, domain_config)
            if concurrency_delay > 0:
                return RateLimitStatus.RATE_LIMITED, concurrency_delay
            
            return RateLimitStatus.ALLOWED, 0.0
    
    def acquire_request_slot(self, domain: str, request_id: Optional[str] = None) -> bool:
        """
        Acquire a request slot for the domain
        
        Args:
            domain: Target domain
            request_id: Optional request identifier
            
        Returns:
            True if slot acquired, False otherwise
        """
        with self._lock:
            status, delay = self.check_rate_limit(domain, request_id)
            
            if status == RateLimitStatus.ALLOWED:
                self.active_requests[domain] += 1
                self.global_active_requests += 1
                return True
            
            return False
    
    def release_request_slot(self, domain: str, request_id: Optional[str] = None):
        """Release a request slot for the domain"""
        with self._lock:
            if self.active_requests[domain] > 0:
                self.active_requests[domain] -= 1
            if self.global_active_requests > 0:
                self.global_active_requests -= 1
    
    def record_request(self, 
                      domain: str,
                      success: bool,
                      response_time_ms: Optional[float] = None,
                      status_code: Optional[int] = None,
                      error_type: Optional[str] = None):
        """
        Record a completed request for rate limiting calculations
        
        Args:
            domain: Target domain
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            error_type: Type of error if failed
        """
        with self._lock:
            current_time = time.time()
            
            # Create request record
            record = RequestRecord(
                timestamp=current_time,
                domain=domain,
                success=success,
                response_time_ms=response_time_ms,
                status_code=status_code,
                error_type=error_type
            )
            
            # Store in history
            self.request_history.append(record)
            self.domain_requests[domain].append(record)
            
            # Update circuit breaker
            circuit = self.circuit_breakers[domain]
            domain_config = self._get_domain_config(domain)
            
            if success:
                circuit.record_success(current_time, domain_config.success_threshold)
                # Reset backoff on success
                if domain in self.domain_backoff:
                    del self.domain_backoff[domain]
                self.backoff_levels[domain] = 0
            else:
                circuit.record_failure(current_time, domain_config.failure_threshold, domain_config.timeout_seconds)
                self._apply_backoff(domain, status_code)
            
            # Update response time tracking
            if response_time_ms is not None:
                self.domain_response_times[domain].append(response_time_ms)
            
            # Adaptive rate limiting adjustment
            if domain_config.adaptive_enabled:
                self._adjust_adaptive_limits(domain, record)
            
            self.logger.debug(f"Recorded request for {domain}: success={success}, "
                             f"response_time={response_time_ms}ms, status={status_code}")
    
    def _check_global_limits(self, current_time: float) -> float:
        """Check global rate limits and return required delay"""
        # Global RPM check
        recent_requests = [r for r in self.request_history 
                          if current_time - r.timestamp <= 60]
        
        if len(recent_requests) >= self.config.global_rpm_limit:
            # Find when the oldest request will expire
            oldest_request_time = min(r.timestamp for r in recent_requests)
            delay = 60 - (current_time - oldest_request_time)
            return max(0, delay)
        
        # Global concurrency check
        if self.global_active_requests >= self.config.global_concurrency_limit:
            return 1.0  # Wait 1 second and retry
        
        return 0.0
    
    def _check_domain_limits(self, domain: str, config: RateLimitConfig, current_time: float) -> float:
        """Check domain-specific rate limits"""
        domain_requests = list(self.domain_requests[domain])
        recent_requests = [r for r in domain_requests 
                          if current_time - r.timestamp <= 60]
        
        # Hard limit check
        if len(recent_requests) >= config.rpm_hard:
            oldest_request_time = min(r.timestamp for r in recent_requests)
            delay = 60 - (current_time - oldest_request_time)
            return max(0, delay)
        
        # Soft limit with QPS check
        if len(recent_requests) >= config.rpm_soft:
            # Check QPS compliance
            last_request_time = max((r.timestamp for r in recent_requests), default=0)
            min_interval = 1.0 / config.qps_max
            since_last = current_time - last_request_time
            
            if since_last < min_interval:
                return min_interval - since_last
        
        return 0.0
    
    def _check_concurrency_limits(self, domain: str, config: RateLimitConfig) -> float:
        """Check concurrency limits for the domain"""
        if self.active_requests[domain] >= config.concurrency_limit:
            return 1.0  # Wait 1 second and retry
        
        return 0.0
    
    def _apply_backoff(self, domain: str, status_code: Optional[int]):
        """Apply exponential backoff for failed requests"""
        current_time = time.time()
        
        # Determine if this error requires backoff
        requires_backoff = False
        if status_code in [429, 503, 502, 504]:  # Rate limited or server errors
            requires_backoff = True
        elif status_code is None:  # Network errors
            requires_backoff = True
        
        if not requires_backoff:
            return
        
        # Calculate backoff delay
        level = self.backoff_levels[domain]
        base_delay = self.config.base_backoff_ms
        multiplier = self.config.backoff_multiplier ** level
        delay_ms = min(base_delay * multiplier, self.config.max_backoff_ms)
        
        # Add jitter
        jitter = delay_ms * self.config.jitter_factor * (random.random() - 0.5)
        final_delay_ms = delay_ms + jitter
        
        # Set backoff time
        backoff_until = current_time + (final_delay_ms / 1000.0)
        self.domain_backoff[domain] = backoff_until
        self.backoff_levels[domain] = min(level + 1, 10)  # Cap at level 10
        
        self.logger.warning(f"Applied backoff to {domain}: {final_delay_ms:.0f}ms "
                           f"(level {level}, status {status_code})")
    
    def _calculate_circuit_delay(self, circuit: CircuitBreaker, current_time: float) -> float:
        """Calculate delay until circuit allows next attempt"""
        if circuit.state == CircuitState.OPEN:
            return max(0, circuit.next_attempt_time - current_time)
        return 0.0
    
    def _get_domain_config(self, domain: str) -> RateLimitConfig:
        """Get domain-specific configuration with overrides"""
        if domain in self.domain_configs:
            return self.domain_configs[domain]
        
        # Create domain-specific config based on domain type
        config = self._create_domain_config(domain)
        self.domain_configs[domain] = config
        return config
    
    def _create_domain_config(self, domain: str) -> RateLimitConfig:
        """Create domain-specific rate limit configuration"""
        base_config = self.config
        
        # Bing gets more aggressive limits
        if "bing.com" in domain.lower():
            return RateLimitConfig(
                rpm_soft=base_config.rpm_soft,
                rpm_hard=base_config.rpm_hard,
                qps_max=base_config.qps_max,
                concurrency_limit=2,  # More conservative for search engines
                base_backoff_ms=2000,  # Longer backoff for Bing
                max_backoff_ms=120000,  # 2 minutes max
                failure_threshold=3,   # Trip circuit faster
                timeout_seconds=600,   # 10 minute timeout
                adaptive_enabled=True
            )
        
        # Other search engines
        elif any(se in domain.lower() for se in ["google.com", "duckduckgo.com", "yahoo.com"]):
            return RateLimitConfig(
                rpm_soft=6,           # Very conservative for other search engines
                rpm_hard=10,
                qps_max=0.2,          # 1 request per 5 seconds
                concurrency_limit=1,  # Single requests only
                base_backoff_ms=5000,
                failure_threshold=2,
                timeout_seconds=900,  # 15 minute timeout
                adaptive_enabled=True
            )
        
        # Regular websites get more relaxed limits
        else:
            return RateLimitConfig(
                rpm_soft=int(base_config.rpm_soft * 1.5),
                rpm_hard=int(base_config.rpm_hard * 1.5),
                qps_max=base_config.qps_max * 2,
                concurrency_limit=base_config.concurrency_limit,
                base_backoff_ms=base_config.base_backoff_ms,
                failure_threshold=base_config.failure_threshold,
                timeout_seconds=base_config.timeout_seconds,
                adaptive_enabled=base_config.adaptive_enabled
            )
    
    def _adjust_adaptive_limits(self, domain: str, record: RequestRecord):
        """Adjust rate limits based on server response patterns"""
        if not self.config.adaptive_enabled:
            return
        
        domain_config = self.domain_configs.get(domain)
        if not domain_config:
            return
        
        response_times = list(self.domain_response_times[domain])
        if len(response_times) < 10:  # Need enough data
            return
        
        # Calculate average response time
        avg_response_time = sum(response_times) / len(response_times)
        
        # If responses are consistently slow, reduce rate
        if avg_response_time > self.config.response_time_threshold_ms:
            # Reduce rate by 20%
            domain_config.rpm_soft = max(1, int(domain_config.rpm_soft * 0.8))
            domain_config.qps_max = max(0.1, domain_config.qps_max * 0.8)
            
            self.logger.info(f"Reduced rate limits for {domain} due to slow responses "
                           f"(avg: {avg_response_time:.0f}ms)")
        
        # If responses are fast and no errors, can increase rate slightly
        elif avg_response_time < self.config.response_time_threshold_ms / 2:
            recent_errors = [r for r in self.domain_requests[domain]
                           if not r.success and time.time() - r.timestamp <= 300]
            
            if len(recent_errors) == 0:  # No errors in last 5 minutes
                original_config = self._create_domain_config(domain)
                # Gradually increase back toward original limits
                domain_config.rpm_soft = min(original_config.rpm_soft,
                                           int(domain_config.rpm_soft * 1.1))
                domain_config.qps_max = min(original_config.qps_max,
                                          domain_config.qps_max * 1.1)
    
    def get_domain_statistics(self, domain: str) -> Dict[str, Any]:
        """Get statistics for a specific domain"""
        current_time = time.time()
        domain_requests = list(self.domain_requests[domain])
        recent_requests = [r for r in domain_requests 
                          if current_time - r.timestamp <= 300]  # Last 5 minutes
        
        circuit = self.circuit_breakers[domain]
        config = self._get_domain_config(domain)
        
        # Calculate success rate
        if recent_requests:
            success_rate = sum(1 for r in recent_requests if r.success) / len(recent_requests)
        else:
            success_rate = 1.0
        
        # Calculate average response time
        response_times = [r.response_time_ms for r in recent_requests 
                         if r.response_time_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "domain": domain,
            "circuit_state": circuit.state.value,
            "active_requests": self.active_requests[domain],
            "requests_last_5min": len(recent_requests),
            "success_rate": round(success_rate * 100, 2),
            "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
            "current_rpm_soft": config.rpm_soft,
            "current_qps_max": config.qps_max,
            "backoff_level": self.backoff_levels[domain],
            "backoff_until": self.domain_backoff.get(domain, 0),
            "failure_count": circuit.failure_count
        }
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        current_time = time.time()
        recent_requests = [r for r in self.request_history 
                          if current_time - r.timestamp <= 300]
        
        domains_active = len([d for d, count in self.active_requests.items() if count > 0])
        
        return {
            "global_active_requests": self.global_active_requests,
            "requests_last_5min": len(recent_requests),
            "domains_active": domains_active,
            "total_domains_tracked": len(self.domain_requests),
            "circuits_open": len([c for c in self.circuit_breakers.values() 
                                if c.state == CircuitState.OPEN]),
            "domains_in_backoff": len(self.domain_backoff),
            "config": {
                "global_rpm_limit": self.config.global_rpm_limit,
                "global_concurrency_limit": self.config.global_concurrency_limit
            }
        }


# Factory function for easy creation
def create_rate_limiter(
    rpm_soft: int = 12,
    rpm_hard: int = 18,
    qps_max: float = 0.5,
    adaptive_enabled: bool = True
) -> RateLimiter:
    """
    Factory function to create a RateLimiter
    
    Args:
        rpm_soft: Soft requests per minute limit
        rpm_hard: Hard requests per minute limit
        qps_max: Maximum queries per second
        adaptive_enabled: Enable adaptive rate limiting
        
    Returns:
        Configured RateLimiter instance
    """
    config = RateLimitConfig(
        rpm_soft=rpm_soft,
        rpm_hard=rpm_hard,
        qps_max=qps_max,
        adaptive_enabled=adaptive_enabled
    )
    
    return RateLimiter(config)