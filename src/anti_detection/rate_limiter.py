"""
Advanced Adaptive Rate Limiting System

Implements sophisticated rate limiting with exponential backoff, circuit breakers,
domain-specific policies, and adaptive behavior based on response patterns.
Designed for anti-detection web scraping with human-like request patterns.
"""

import logging
import time
import math
import asyncio
import random
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import threading
import json
from urllib.parse import urlparse
import hashlib


class RequestStatus(Enum):
    """Status of rate limit check"""
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"
    BACKOFF_ACTIVE = "backoff_active"
    QUOTA_EXCEEDED = "quota_exceeded"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Circuit tripped, blocking requests
    HALF_OPEN = "half_open" # Testing recovery


class RateLimitPolicy(Enum):
    """Rate limiting policies for different scenarios"""
    CONSERVATIVE = "conservative"  # Very careful, minimal requests
    MODERATE = "moderate"         # Balanced approach
    AGGRESSIVE = "aggressive"     # Higher request rates
    ADAPTIVE = "adaptive"         # Dynamically adjusting


@dataclass
class RateLimitConfig:
    """Comprehensive rate limiting configuration"""
    # Basic rate limits
    requests_per_minute: int = 12
    requests_per_hour: int = 200
    max_concurrent_requests: int = 3
    min_request_interval: float = 2.0  # seconds
    
    # Adaptive behavior
    adaptive_enabled: bool = True
    success_rate_threshold: float = 0.85  # Below this triggers adaptation
    response_time_threshold: float = 5.0  # Seconds - slow responses trigger adaptation
    adaptation_factor: float = 0.8        # Multiply rates by this when adapting
    recovery_factor: float = 1.1          # Multiply rates by this when recovering
    
    # Exponential backoff
    enable_exponential_backoff: bool = True
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 300.0    # 5 minutes
    backoff_multiplier: float = 2.0
    backoff_jitter_factor: float = 0.1
    
    # Circuit breaker
    enable_circuit_breaker: bool = True
    failure_threshold: int = 5
    success_threshold: int = 3
    circuit_timeout_seconds: int = 300    # 5 minutes
    
    # Domain-specific overrides
    domain_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Human-like patterns
    enable_human_patterns: bool = True
    burst_probability: float = 0.1        # Probability of request bursts
    idle_probability: float = 0.2         # Probability of idle periods
    daily_peak_hours: List[int] = field(default_factory=lambda: [9, 10, 14, 15, 16])
    
    # Monitoring and logging
    enable_detailed_logging: bool = True
    log_request_patterns: bool = True
    statistics_retention_hours: int = 24


@dataclass
class RequestRecord:
    """Record of a request for analysis"""
    timestamp: float
    domain: str
    url: str
    success: bool
    response_time: float
    status_code: Optional[int]
    error_type: Optional[str]
    user_agent: Optional[str]
    proxy_used: Optional[str]


@dataclass
class CircuitBreaker:
    """Circuit breaker for domain protection"""
    domain: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    next_attempt_time: float = 0.0
    total_requests: int = 0
    
    def should_allow_request(self, current_time: float, timeout_seconds: int) -> bool:
        """Check if request should be allowed"""
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
    
    def record_success(self, success_threshold: int):
        """Record successful request"""
        self.success_count += 1
        self.total_requests += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Gradual recovery - reduce failure count on success
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self, current_time: float, failure_threshold: int, timeout_seconds: int):
        """Record failed request"""
        self.failure_count += 1
        self.total_requests += 1
        self.last_failure_time = current_time
        self.success_count = 0
        
        if self.failure_count >= failure_threshold:
            self.state = CircuitState.OPEN
            self.next_attempt_time = current_time + timeout_seconds


@dataclass
class DomainRateLimit:
    """Rate limiting state for a specific domain"""
    domain: str
    config: RateLimitConfig
    
    # Request tracking
    request_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    active_requests: int = 0
    
    # Rate limiting state
    last_request_time: float = 0.0
    next_allowed_time: float = 0.0
    
    # Backoff state
    backoff_level: int = 0
    backoff_until: float = 0.0
    
    # Circuit breaker
    circuit_breaker: CircuitBreaker = field(default_factory=lambda: CircuitBreaker(""))
    
    # Adaptive rate limiting
    current_rpm: float = 0.0
    current_rph: float = 0.0
    current_interval: float = 0.0
    adaptation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    recent_success_rate: float = 1.0
    recent_avg_response_time: float = 1.0
    last_adaptation_time: float = 0.0
    
    def __post_init__(self):
        if self.circuit_breaker.domain == "":
            self.circuit_breaker.domain = self.domain
        
        # Initialize current limits from config
        self.current_rpm = float(self.config.requests_per_minute)
        self.current_rph = float(self.config.requests_per_hour)
        self.current_interval = self.config.min_request_interval


class AdaptiveRateLimiter:
    """
    Advanced adaptive rate limiting system with human-like patterns
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.logger = self._setup_logging()
        
        # Domain-specific rate limiters
        self.domain_limiters: Dict[str, DomainRateLimit] = {}
        
        # Global tracking
        self.global_request_history: deque = deque(maxlen=10000)
        self.global_active_requests: int = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Human pattern simulation
        self.daily_pattern_modifier = 1.0
        self.burst_mode_until = 0.0
        self.idle_mode_until = 0.0
        
        # Statistics
        self.statistics: Dict[str, Any] = {
            "total_requests": 0,
            "total_blocked": 0,
            "total_adaptations": 0,
            "start_time": time.time()
        }
        
        self.logger.info("AdaptiveRateLimiter initialized with adaptive behavior enabled")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger("adaptive_rate_limiter")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _get_domain_limiter(self, domain: str) -> DomainRateLimit:
        """Get or create domain-specific rate limiter"""
        if domain not in self.domain_limiters:
            # Apply domain-specific overrides
            domain_config = self._create_domain_config(domain)
            
            limiter = DomainRateLimit(
                domain=domain,
                config=domain_config,
                circuit_breaker=CircuitBreaker(domain)
            )
            
            self.domain_limiters[domain] = limiter
            self.logger.info(f"Created rate limiter for domain: {domain}")
        
        return self.domain_limiters[domain]
    
    def _create_domain_config(self, domain: str) -> RateLimitConfig:
        """Create domain-specific configuration"""
        base_config = self.config
        domain_lower = domain.lower()
        
        # Start with base config
        domain_config = RateLimitConfig(
            requests_per_minute=base_config.requests_per_minute,
            requests_per_hour=base_config.requests_per_hour,
            max_concurrent_requests=base_config.max_concurrent_requests,
            min_request_interval=base_config.min_request_interval,
            adaptive_enabled=base_config.adaptive_enabled,
            enable_exponential_backoff=base_config.enable_exponential_backoff,
            enable_circuit_breaker=base_config.enable_circuit_breaker,
            enable_human_patterns=base_config.enable_human_patterns
        )
        
        # Apply domain-specific overrides
        if domain in base_config.domain_overrides:
            overrides = base_config.domain_overrides[domain]
            for key, value in overrides.items():
                if hasattr(domain_config, key):
                    setattr(domain_config, key, value)
        
        # Built-in domain-specific rules
        if "bing.com" in domain_lower:
            # Conservative settings for Bing
            domain_config.requests_per_minute = min(10, domain_config.requests_per_minute)
            domain_config.requests_per_hour = min(150, domain_config.requests_per_hour)
            domain_config.min_request_interval = max(3.0, domain_config.min_request_interval)
            domain_config.max_concurrent_requests = min(2, domain_config.max_concurrent_requests)
        
        elif any(se in domain_lower for se in ["google.com", "duckduckgo.com", "yahoo.com"]):
            # Very conservative for other search engines
            domain_config.requests_per_minute = min(6, domain_config.requests_per_minute)
            domain_config.requests_per_hour = min(100, domain_config.requests_per_hour)
            domain_config.min_request_interval = max(5.0, domain_config.min_request_interval)
            domain_config.max_concurrent_requests = 1
        
        elif any(social in domain_lower for social in ["facebook", "twitter", "linkedin", "instagram"]):
            # Moderate settings for social media
            domain_config.requests_per_minute = min(15, domain_config.requests_per_minute)
            domain_config.min_request_interval = max(2.0, domain_config.min_request_interval)
        
        return domain_config
    
    async def check_rate_limit(self, 
                             url: str,
                             session_id: Optional[str] = None,
                             request_context: Optional[Dict[str, Any]] = None) -> Tuple[RequestStatus, float]:
        """
        Check if request is allowed and return required delay
        
        Args:
            url: Target URL
            session_id: Optional session identifier
            request_context: Additional context for rate limiting decisions
            
        Returns:
            Tuple of (status, delay_seconds)
        """
        domain = urlparse(url).netloc
        current_time = time.time()
        
        with self._lock:
            # Update human behavior patterns
            self._update_human_patterns(current_time)
            
            # Get domain-specific limiter
            limiter = self._get_domain_limiter(domain)
            
            # Check circuit breaker
            if (limiter.config.enable_circuit_breaker and
                not limiter.circuit_breaker.should_allow_request(
                    current_time, limiter.config.circuit_timeout_seconds)):
                
                circuit_delay = max(0, limiter.circuit_breaker.next_attempt_time - current_time)
                return RequestStatus.CIRCUIT_OPEN, circuit_delay
            
            # Check backoff
            if limiter.backoff_until > current_time:
                backoff_delay = limiter.backoff_until - current_time
                return RequestStatus.BACKOFF_ACTIVE, backoff_delay
            
            # Check global limits
            global_delay = self._check_global_limits(current_time)
            if global_delay > 0:
                return RequestStatus.RATE_LIMITED, global_delay
            
            # Check domain-specific limits
            domain_delay = await self._check_domain_limits(limiter, current_time)
            if domain_delay > 0:
                return RequestStatus.RATE_LIMITED, domain_delay
            
            # Check concurrent requests
            if limiter.active_requests >= limiter.config.max_concurrent_requests:
                return RequestStatus.RATE_LIMITED, 1.0
            
            # Apply human pattern modifiers
            human_delay = self._calculate_human_pattern_delay(limiter, current_time)
            if human_delay > 0:
                return RequestStatus.RATE_LIMITED, human_delay
            
            return RequestStatus.ALLOWED, 0.0
    
    def _update_human_patterns(self, current_time: float):
        """Update human behavior pattern modifiers"""
        if not self.config.enable_human_patterns:
            return
        
        # Check for burst mode expiry
        if self.burst_mode_until > 0 and current_time > self.burst_mode_until:
            self.burst_mode_until = 0.0
            self.logger.debug("Exiting burst mode")
        
        # Check for idle mode expiry
        if self.idle_mode_until > 0 and current_time > self.idle_mode_until:
            self.idle_mode_until = 0.0
            self.logger.debug("Exiting idle mode")
        
        # Randomly enter burst mode
        if (self.burst_mode_until == 0 and 
            random.random() < self.config.burst_probability / 3600):  # Per hour probability
            self.burst_mode_until = current_time + random.uniform(30, 120)
            self.logger.debug("Entering burst mode")
        
        # Randomly enter idle mode
        if (self.idle_mode_until == 0 and 
            random.random() < self.config.idle_probability / 3600):  # Per hour probability
            self.idle_mode_until = current_time + random.uniform(60, 300)
            self.logger.debug("Entering idle mode")
        
        # Update daily pattern modifier
        import datetime
        current_hour = datetime.datetime.now().hour
        if current_hour in self.config.daily_peak_hours:
            self.daily_pattern_modifier = 1.2
        elif 22 <= current_hour or current_hour <= 6:
            self.daily_pattern_modifier = 0.5
        else:
            self.daily_pattern_modifier = 1.0
    
    def _check_global_limits(self, current_time: float) -> float:
        """Check global rate limits"""
        # Clean old requests
        cutoff_time = current_time - 3600  # 1 hour
        while (self.global_request_history and 
               self.global_request_history[0].timestamp < cutoff_time):
            self.global_request_history.popleft()
        
        # Check global hourly limit (if configured)
        global_hourly_limit = getattr(self.config, 'global_requests_per_hour', None)
        if global_hourly_limit and len(self.global_request_history) >= global_hourly_limit:
            oldest_request = self.global_request_history[0]
            return max(0, 3600 - (current_time - oldest_request.timestamp))
        
        # Check global concurrent limit
        global_concurrent_limit = getattr(self.config, 'global_concurrent_requests', 10)
        if self.global_active_requests >= global_concurrent_limit:
            return 2.0
        
        return 0.0
    
    async def _check_domain_limits(self, limiter: DomainRateLimit, current_time: float) -> float:
        """Check domain-specific rate limits"""
        # Clean old requests from domain history
        cutoff_minute = current_time - 60
        cutoff_hour = current_time - 3600
        
        while (limiter.request_history and 
               limiter.request_history[0].timestamp < cutoff_hour):
            limiter.request_history.popleft()
        
        # Get recent requests
        recent_minute = [r for r in limiter.request_history if r.timestamp >= cutoff_minute]
        recent_hour = list(limiter.request_history)
        
        # Check per-minute limit
        if len(recent_minute) >= limiter.current_rpm:
            oldest_in_minute = min(r.timestamp for r in recent_minute)
            delay = max(0, 60 - (current_time - oldest_in_minute))
            return delay
        
        # Check per-hour limit  
        if len(recent_hour) >= limiter.current_rph:
            oldest_in_hour = min(r.timestamp for r in recent_hour)
            delay = max(0, 3600 - (current_time - oldest_in_hour))
            return delay
        
        # Check minimum interval
        if (limiter.last_request_time > 0 and 
            current_time - limiter.last_request_time < limiter.current_interval):
            delay = limiter.current_interval - (current_time - limiter.last_request_time)
            return delay
        
        return 0.0
    
    def _calculate_human_pattern_delay(self, limiter: DomainRateLimit, current_time: float) -> float:
        """Calculate additional delay based on human behavior patterns"""
        if not limiter.config.enable_human_patterns:
            return 0.0
        
        base_delay = 0.0
        
        # Idle mode - longer delays
        if self.idle_mode_until > current_time:
            base_delay += random.uniform(5.0, 15.0)
        
        # Burst mode - shorter delays (but still respectful)
        elif self.burst_mode_until > current_time:
            base_delay *= 0.7
        
        # Daily pattern modifier
        base_delay *= (2.0 - self.daily_pattern_modifier)
        
        # Add small random variation
        if base_delay > 0:
            jitter = base_delay * 0.1 * random.uniform(-1, 1)
            base_delay += jitter
        
        return max(0.0, base_delay)
    
    async def acquire_request_slot(self, 
                                 url: str,
                                 session_id: Optional[str] = None,
                                 request_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Acquire a request slot if allowed
        
        Args:
            url: Target URL
            session_id: Optional session identifier
            request_context: Additional context
            
        Returns:
            True if slot acquired, False if rate limited
        """
        status, delay = await self.check_rate_limit(url, session_id, request_context)
        
        if status == RequestStatus.ALLOWED:
            domain = urlparse(url).netloc
            
            with self._lock:
                limiter = self._get_domain_limiter(domain)
                limiter.active_requests += 1
                limiter.last_request_time = time.time()
                self.global_active_requests += 1
                
                self.statistics["total_requests"] += 1
                
                self.logger.debug(f"Acquired request slot for {domain} "
                                f"(active: {limiter.active_requests})")
                return True
        else:
            self.statistics["total_blocked"] += 1
            self.logger.debug(f"Request blocked for {url}: {status.value} (delay: {delay:.2f}s)")
            return False
    
    def release_request_slot(self, 
                           url: str,
                           success: bool,
                           response_time: float,
                           status_code: Optional[int] = None,
                           error_type: Optional[str] = None,
                           user_agent: Optional[str] = None,
                           proxy_used: Optional[str] = None):
        """
        Release a request slot and record results
        
        Args:
            url: Target URL
            success: Whether request was successful
            response_time: Response time in seconds
            status_code: HTTP status code
            error_type: Error type if failed
            user_agent: User agent used
            proxy_used: Proxy identifier if used
        """
        domain = urlparse(url).netloc
        current_time = time.time()
        
        with self._lock:
            limiter = self._get_domain_limiter(domain)
            
            # Release active request slot
            limiter.active_requests = max(0, limiter.active_requests - 1)
            self.global_active_requests = max(0, self.global_active_requests - 1)
            
            # Create request record
            record = RequestRecord(
                timestamp=current_time,
                domain=domain,
                url=url,
                success=success,
                response_time=response_time,
                status_code=status_code,
                error_type=error_type,
                user_agent=user_agent,
                proxy_used=proxy_used
            )
            
            # Store request record
            limiter.request_history.append(record)
            self.global_request_history.append(record)
            
            # Update circuit breaker
            if success:
                limiter.circuit_breaker.record_success(limiter.config.success_threshold)
            else:
                limiter.circuit_breaker.record_failure(
                    current_time, 
                    limiter.config.failure_threshold,
                    limiter.config.circuit_timeout_seconds
                )
            
            # Handle backoff for failures
            if not success:
                self._apply_exponential_backoff(limiter, status_code, error_type)
            else:
                # Reset backoff on success
                if limiter.backoff_level > 0:
                    limiter.backoff_level = max(0, limiter.backoff_level - 1)
                    limiter.backoff_until = 0.0
            
            # Perform adaptive rate limiting
            if limiter.config.adaptive_enabled:
                await self._perform_adaptive_adjustment(limiter, current_time)
            
            self.logger.debug(f"Released request slot for {domain} "
                            f"(success: {success}, response_time: {response_time:.2f}s)")
    
    def _apply_exponential_backoff(self, 
                                  limiter: DomainRateLimit, 
                                  status_code: Optional[int],
                                  error_type: Optional[str]):
        """Apply exponential backoff for failed requests"""
        if not limiter.config.enable_exponential_backoff:
            return
        
        # Determine if this error should trigger backoff
        should_backoff = False
        
        if status_code:
            if status_code in [429, 503, 502, 504]:  # Rate limit or server errors
                should_backoff = True
            elif 500 <= status_code < 600:  # Other server errors
                should_backoff = True
        else:
            # Network errors (no status code)
            should_backoff = True
        
        if not should_backoff:
            return
        
        # Calculate backoff delay
        limiter.backoff_level += 1
        base_delay = limiter.config.base_backoff_seconds
        
        # Exponential backoff
        delay = base_delay * (limiter.config.backoff_multiplier ** (limiter.backoff_level - 1))
        delay = min(delay, limiter.config.max_backoff_seconds)
        
        # Add jitter to avoid thundering herd
        jitter = delay * limiter.config.backoff_jitter_factor
        delay += random.uniform(-jitter, jitter)
        
        limiter.backoff_until = time.time() + delay
        
        self.logger.warning(f"Applied exponential backoff to {limiter.domain}: "
                          f"{delay:.2f}s (level {limiter.backoff_level}, status {status_code})")
    
    async def _perform_adaptive_adjustment(self, limiter: DomainRateLimit, current_time: float):
        """Perform adaptive rate limiting adjustments"""
        # Only adjust periodically
        if (limiter.last_adaptation_time > 0 and 
            current_time - limiter.last_adaptation_time < 300):  # 5 minutes
            return
        
        # Need enough data to make decisions
        if len(limiter.request_history) < 10:
            return
        
        # Calculate recent performance metrics
        recent_requests = [r for r in limiter.request_history 
                          if current_time - r.timestamp <= 300]  # Last 5 minutes
        
        if not recent_requests:
            return
        
        success_count = sum(1 for r in recent_requests if r.success)
        success_rate = success_count / len(recent_requests)
        avg_response_time = sum(r.response_time for r in recent_requests) / len(recent_requests)
        
        limiter.recent_success_rate = success_rate
        limiter.recent_avg_response_time = avg_response_time
        
        # Determine if adaptation is needed
        needs_reduction = (
            success_rate < limiter.config.success_rate_threshold or
            avg_response_time > limiter.config.response_time_threshold
        )
        
        needs_recovery = (
            success_rate > 0.95 and
            avg_response_time < limiter.config.response_time_threshold * 0.5 and
            current_time - limiter.last_adaptation_time > 900  # 15 minutes since last change
        )
        
        if needs_reduction:
            # Reduce rate limits
            old_rpm = limiter.current_rpm
            limiter.current_rpm *= limiter.config.adaptation_factor
            limiter.current_rph *= limiter.config.adaptation_factor
            limiter.current_interval /= limiter.config.adaptation_factor
            
            # Ensure minimum values
            limiter.current_rpm = max(1.0, limiter.current_rpm)
            limiter.current_rph = max(10.0, limiter.current_rph)
            limiter.current_interval = min(60.0, limiter.current_interval)
            
            limiter.last_adaptation_time = current_time
            self.statistics["total_adaptations"] += 1
            
            self.logger.info(f"Reduced rate limits for {limiter.domain}: "
                           f"RPM {old_rpm:.1f} -> {limiter.current_rpm:.1f} "
                           f"(success_rate: {success_rate:.2f}, avg_time: {avg_response_time:.2f}s)")
        
        elif needs_recovery:
            # Gradually increase rate limits back toward original
            original_config = self._create_domain_config(limiter.domain)
            
            old_rpm = limiter.current_rpm
            limiter.current_rpm = min(
                original_config.requests_per_minute,
                limiter.current_rpm * limiter.config.recovery_factor
            )
            limiter.current_rph = min(
                original_config.requests_per_hour,
                limiter.current_rph * limiter.config.recovery_factor
            )
            limiter.current_interval = max(
                original_config.min_request_interval,
                limiter.current_interval * limiter.config.recovery_factor
            )
            
            limiter.last_adaptation_time = current_time
            
            self.logger.info(f"Increased rate limits for {limiter.domain}: "
                           f"RPM {old_rpm:.1f} -> {limiter.current_rpm:.1f} "
                           f"(recovery mode)")
        
        # Record adaptation history
        if needs_reduction or needs_recovery:
            adaptation_record = {
                "timestamp": current_time,
                "action": "reduction" if needs_reduction else "recovery",
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "new_rpm": limiter.current_rpm,
                "new_rph": limiter.current_rph,
                "new_interval": limiter.current_interval
            }
            
            limiter.adaptation_history.append(adaptation_record)
            
            # Keep history manageable
            if len(limiter.adaptation_history) > 100:
                limiter.adaptation_history = limiter.adaptation_history[-100:]
    
    def get_domain_statistics(self, domain: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a domain"""
        if domain not in self.domain_limiters:
            return {"domain": domain, "error": "No data available"}
        
        limiter = self.domain_limiters[domain]
        current_time = time.time()
        
        # Recent requests analysis
        recent_requests = [r for r in limiter.request_history 
                          if current_time - r.timestamp <= 300]
        
        success_count = sum(1 for r in recent_requests if r.success)
        success_rate = (success_count / len(recent_requests) * 100) if recent_requests else 0
        
        avg_response_time = (sum(r.response_time for r in recent_requests) / 
                           len(recent_requests)) if recent_requests else 0
        
        return {
            "domain": domain,
            "circuit_state": limiter.circuit_breaker.state.value,
            "active_requests": limiter.active_requests,
            "total_requests": len(limiter.request_history),
            "recent_requests_5min": len(recent_requests),
            "success_rate_percentage": round(success_rate, 2),
            "avg_response_time": round(avg_response_time, 2),
            "current_limits": {
                "rpm": limiter.current_rpm,
                "rph": limiter.current_rph,
                "interval": limiter.current_interval
            },
            "original_limits": {
                "rpm": limiter.config.requests_per_minute,
                "rph": limiter.config.requests_per_hour,
                "interval": limiter.config.min_request_interval
            },
            "backoff_status": {
                "level": limiter.backoff_level,
                "until": limiter.backoff_until,
                "active": limiter.backoff_until > current_time
            },
            "adaptations_count": len(limiter.adaptation_history),
            "last_adaptation": limiter.adaptation_history[-1] if limiter.adaptation_history else None
        }
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global rate limiter statistics"""
        current_time = time.time()
        uptime = current_time - self.statistics["start_time"]
        
        # Calculate global success rate
        recent_global = [r for r in self.global_request_history 
                        if current_time - r.timestamp <= 300]
        
        global_success_rate = 0
        if recent_global:
            global_success_count = sum(1 for r in recent_global if r.success)
            global_success_rate = (global_success_count / len(recent_global)) * 100
        
        return {
            "uptime_seconds": uptime,
            "total_domains": len(self.domain_limiters),
            "global_active_requests": self.global_active_requests,
            "total_requests": self.statistics["total_requests"],
            "total_blocked": self.statistics["total_blocked"],
            "total_adaptations": self.statistics["total_adaptations"],
            "block_rate_percentage": (
                (self.statistics["total_blocked"] / 
                 max(1, self.statistics["total_requests"] + self.statistics["total_blocked"])) * 100
            ),
            "global_success_rate_percentage": round(global_success_rate, 2),
            "recent_requests_5min": len(recent_global),
            "human_patterns": {
                "burst_mode_active": self.burst_mode_until > current_time,
                "idle_mode_active": self.idle_mode_until > current_time,
                "daily_pattern_modifier": self.daily_pattern_modifier
            },
            "circuit_breakers_open": sum(
                1 for limiter in self.domain_limiters.values()
                if limiter.circuit_breaker.state == CircuitState.OPEN
            )
        }
    
    def export_configuration(self, file_path: str):
        """Export current rate limiting configuration"""
        config_data = {
            "global_config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "min_request_interval": self.config.min_request_interval,
                "adaptive_enabled": self.config.adaptive_enabled,
                "enable_exponential_backoff": self.config.enable_exponential_backoff,
                "enable_circuit_breaker": self.config.enable_circuit_breaker,
                "enable_human_patterns": self.config.enable_human_patterns
            },
            "domain_configs": {},
            "current_state": {},
            "exported_at": time.time()
        }
        
        # Export domain-specific configurations and current state
        for domain, limiter in self.domain_limiters.items():
            config_data["domain_configs"][domain] = {
                "requests_per_minute": limiter.config.requests_per_minute,
                "requests_per_hour": limiter.config.requests_per_hour,
                "min_request_interval": limiter.config.min_request_interval
            }
            
            config_data["current_state"][domain] = {
                "current_rpm": limiter.current_rpm,
                "current_rph": limiter.current_rph,
                "current_interval": limiter.current_interval,
                "backoff_level": limiter.backoff_level,
                "circuit_state": limiter.circuit_breaker.state.value
            }
        
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        self.logger.info(f"Exported rate limiter configuration to {file_path}")
    
    def reset_domain_limits(self, domain: str):
        """Reset rate limits for a specific domain to original values"""
        if domain not in self.domain_limiters:
            return
        
        limiter = self.domain_limiters[domain]
        original_config = self._create_domain_config(domain)
        
        limiter.current_rpm = original_config.requests_per_minute
        limiter.current_rph = original_config.requests_per_hour  
        limiter.current_interval = original_config.min_request_interval
        limiter.backoff_level = 0
        limiter.backoff_until = 0.0
        limiter.circuit_breaker.state = CircuitState.CLOSED
        limiter.circuit_breaker.failure_count = 0
        
        self.logger.info(f"Reset rate limits for domain: {domain}")


# Factory function for easy creation
def create_adaptive_rate_limiter(
    requests_per_minute: int = 12,
    adaptive_enabled: bool = True,
    enable_human_patterns: bool = True,
    domain_overrides: Optional[Dict[str, Dict[str, Any]]] = None
) -> AdaptiveRateLimiter:
    """
    Factory function to create an AdaptiveRateLimiter
    
    Args:
        requests_per_minute: Base requests per minute limit
        adaptive_enabled: Enable adaptive behavior
        enable_human_patterns: Enable human-like request patterns
        domain_overrides: Domain-specific configuration overrides
        
    Returns:
        Configured AdaptiveRateLimiter instance
    """
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        adaptive_enabled=adaptive_enabled,
        enable_human_patterns=enable_human_patterns,
        domain_overrides=domain_overrides or {}
    )
    
    return AdaptiveRateLimiter(config)