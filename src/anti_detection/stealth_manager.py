"""
Comprehensive Anti-Detection and Stealth Manager

Orchestrates all anti-detection components including user agents, proxies,
human behavior simulation, rate limiting, and session management to evade
detection by Cloudflare, reCAPTCHA, and other anti-bot systems.
"""

import logging
import time
import random
import hashlib
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
from urllib.parse import urlparse

# Optional imports for components
try:
    from .proxy_rotator import ProxyRotator, ProxyInfo
    PROXY_ROTATOR_AVAILABLE = True
except ImportError:
    PROXY_ROTATOR_AVAILABLE = False
    ProxyRotator = None

try:
    from .behavior_simulator import BehaviorSimulator, BehaviorProfile
    BEHAVIOR_SIMULATOR_AVAILABLE = True
except ImportError:
    BEHAVIOR_SIMULATOR_AVAILABLE = False
    BehaviorSimulator = None

try:
    from .rate_limiter import RateLimiter, RateLimitConfig, RateLimitStatus
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    RateLimiter = None

# Optional imports for existing infrastructure
try:
    from ..infra.user_agent_manager import UserAgentManager, UserAgentProfile
    USER_AGENT_MANAGER_AVAILABLE = True
except ImportError:
    USER_AGENT_MANAGER_AVAILABLE = False
    UserAgentManager = None

try:
    from botasaurus.browser import browser, Driver
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    browser = None
    Driver = None


class StealthLevel(Enum):
    """Anti-detection stealth levels"""
    MINIMAL = "minimal"      # Basic UA rotation
    MODERATE = "moderate"    # UA + delays + basic behavior
    AGGRESSIVE = "aggressive"  # Full stealth with proxies
    MAXIMUM = "maximum"      # All features + adaptive behavior


class DetectionRisk(Enum):
    """Current detection risk assessment"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StealthConfig:
    """Configuration for stealth operations"""
    # Stealth level
    stealth_level: StealthLevel = StealthLevel.MODERATE
    
    # User agent settings
    rotate_user_agents: bool = True
    user_agent_pool_size: int = 20
    user_agent_rotation_interval: int = 300  # seconds
    
    # Proxy settings
    use_proxies: bool = False
    proxy_rotation_interval: int = 600  # 10 minutes
    proxy_failure_threshold: int = 3
    
    # Behavior simulation
    simulate_human_behavior: bool = True
    mouse_movements: bool = True
    scroll_patterns: bool = True
    typing_delays: bool = True
    random_pauses: bool = True
    
    # Rate limiting
    adaptive_rate_limiting: bool = True
    base_delay_range: Tuple[float, float] = (1.0, 3.0)
    detection_delay_multiplier: float = 2.0
    
    # Session management
    session_rotation_interval: int = 1800  # 30 minutes
    cookie_persistence: bool = True
    browser_profile_isolation: bool = True
    
    # Detection evasion
    cloudflare_evasion: bool = True
    recaptcha_detection: bool = True
    javascript_execution: bool = True
    headless_detection_evasion: bool = True
    
    # Monitoring
    detection_monitoring: bool = True
    response_time_monitoring: bool = True
    success_rate_monitoring: bool = True


@dataclass
class SessionMetrics:
    """Metrics for a stealth session"""
    session_id: str
    start_time: float
    domain: str
    requests_made: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    detection_events: int = 0
    avg_response_time: float = 0.0
    current_risk_level: DetectionRisk = DetectionRisk.LOW
    last_user_agent_rotation: Optional[float] = None
    last_proxy_rotation: Optional[float] = None
    cloudflare_encounters: int = 0
    recaptcha_encounters: int = 0


class StealthManager:
    """
    Main orchestrator for all anti-detection and stealth operations
    """
    
    def __init__(self, config: Optional[StealthConfig] = None):
        self.config = config or StealthConfig()
        self.logger = self._setup_logging()
        
        # Initialize components
        self.user_agent_manager = None
        self.proxy_rotator = None
        self.behavior_simulator = None
        self.rate_limiter = None
        
        # Session tracking
        self.active_sessions: Dict[str, SessionMetrics] = {}
        self.session_configs: Dict[str, Dict[str, Any]] = {}
        
        # Detection monitoring
        self.detection_patterns = self._load_detection_patterns()
        self.risk_assessments: Dict[str, DetectionRisk] = {}
        
        # Component initialization
        self._initialize_components()
        
        self.logger.info(f"StealthManager initialized with level {self.config.stealth_level.value}")
    
    def _setup_logging(self):
        """Setup structured logging for stealth operations"""
        logger = logging.getLogger("stealth_manager")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _initialize_components(self):
        """Initialize all stealth components based on configuration"""
        try:
            # User Agent Manager
            if USER_AGENT_MANAGER_AVAILABLE:
                ua_config = {
                    "profile_base_path": "profiles/stealth_sessions",
                    "custom_user_agents": self._get_stealth_user_agents()
                }
                self.user_agent_manager = UserAgentManager(ua_config)
                self.logger.info("UserAgentManager initialized")
            
            # Proxy Rotator
            if PROXY_ROTATOR_AVAILABLE and self.config.use_proxies:
                proxy_config = {
                    "rotation_interval": self.config.proxy_rotation_interval,
                    "failure_threshold": self.config.proxy_failure_threshold
                }
                self.proxy_rotator = ProxyRotator(proxy_config)
                self.logger.info("ProxyRotator initialized")
            
            # Behavior Simulator
            if BEHAVIOR_SIMULATOR_AVAILABLE and self.config.simulate_human_behavior:
                behavior_config = {
                    "mouse_movements": self.config.mouse_movements,
                    "scroll_patterns": self.config.scroll_patterns,
                    "typing_delays": self.config.typing_delays,
                    "random_pauses": self.config.random_pauses
                }
                self.behavior_simulator = BehaviorSimulator(behavior_config)
                self.logger.info("BehaviorSimulator initialized")
            
            # Rate Limiter
            if RATE_LIMITER_AVAILABLE:
                rate_config = RateLimitConfig(
                    adaptive_enabled=self.config.adaptive_rate_limiting,
                    rpm_soft=12,
                    rpm_hard=18,
                    qps_max=0.3
                )
                self.rate_limiter = RateLimiter(rate_config)
                self.logger.info("RateLimiter initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
    
    def _get_stealth_user_agents(self) -> List[Dict[str, Any]]:
        """Get user agents optimized for stealth operations"""
        return [
            # Chrome Windows - Most common and least suspicious
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "platform": "Windows",
                "browser": "Chrome",
                "version": "120.0.0.0",
                "weight": 15
            },
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "platform": "Windows", 
                "browser": "Chrome",
                "version": "119.0.0.0",
                "weight": 12
            },
            # Chrome macOS - Second most common
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "platform": "macOS",
                "browser": "Chrome", 
                "version": "120.0.0.0",
                "weight": 10
            },
            # Firefox Windows - Good for diversity
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "platform": "Windows",
                "browser": "Firefox",
                "version": "121.0",
                "weight": 8
            },
            # Edge Windows - Microsoft properties
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "platform": "Windows",
                "browser": "Edge",
                "version": "120.0.0.0", 
                "weight": 6
            }
        ]
    
    def _load_detection_patterns(self) -> Dict[str, List[str]]:
        """Load patterns that indicate anti-bot detection"""
        return {
            "cloudflare": [
                "cloudflare", "cf-ray", "enable-javascript", 
                "checking your browser", "please wait", "ddos protection"
            ],
            "recaptcha": [
                "recaptcha", "i'm not a robot", "verify you are human",
                "captcha", "prove you are not a robot"
            ],
            "rate_limiting": [
                "too many requests", "rate limit", "429", "slow down",
                "try again later", "request limit exceeded"
            ],
            "bot_detection": [
                "bot detected", "automated traffic", "suspicious activity",
                "access denied", "blocked", "forbidden"
            ]
        }
    
    async def create_stealth_session(self, 
                                   domain: str, 
                                   session_id: Optional[str] = None) -> str:
        """
        Create a new stealth session with full anti-detection setup
        
        Args:
            domain: Target domain for the session
            session_id: Optional custom session ID
            
        Returns:
            Session ID for the created session
        """
        if not session_id:
            session_id = self._generate_session_id(domain)
        
        current_time = time.time()
        
        # Create session metrics
        metrics = SessionMetrics(
            session_id=session_id,
            start_time=current_time,
            domain=domain
        )
        self.active_sessions[session_id] = metrics
        
        # Get user agent
        user_agent = None
        if self.user_agent_manager:
            user_agent = self.user_agent_manager.get_user_agent(domain=domain)
        
        # Get proxy if enabled
        proxy = None
        if self.proxy_rotator:
            proxy = await self.proxy_rotator.get_proxy(domain=domain)
        
        # Create session configuration
        session_config = {
            "session_id": session_id,
            "domain": domain,
            "user_agent": user_agent.user_agent if user_agent else None,
            "proxy": proxy.to_dict() if proxy else None,
            "stealth_level": self.config.stealth_level.value,
            "created_at": current_time,
            "browser_config": self._get_browser_config(domain, user_agent, proxy)
        }
        
        self.session_configs[session_id] = session_config
        
        self.logger.info(f"Created stealth session {session_id} for {domain} "
                        f"with stealth level {self.config.stealth_level.value}")
        
        return session_id
    
    def _generate_session_id(self, domain: str) -> str:
        """Generate unique session ID"""
        timestamp = str(time.time())
        random_part = str(random.randint(1000, 9999))
        domain_hash = hashlib.md5(domain.encode()).hexdigest()[:8]
        return f"stealth_{domain_hash}_{timestamp}_{random_part}"
    
    def _get_browser_config(self, 
                           domain: str, 
                           user_agent: Optional[UserAgentProfile], 
                           proxy: Optional[ProxyInfo]) -> Dict[str, Any]:
        """Get browser configuration optimized for stealth"""
        config = {
            "headless": False if self.config.stealth_level in [StealthLevel.AGGRESSIVE, StealthLevel.MAXIMUM] else True,
            "user_agent": user_agent.user_agent if user_agent else None,
            "proxy": proxy.proxy_url if proxy else None,
            "block_images": True,
            "block_resources": True,
            "reuse_driver": True,
            "window_size": (1920, 1080),
            "stealth_options": self._get_stealth_options(domain)
        }
        
        return config
    
    def _get_stealth_options(self, domain: str) -> Dict[str, Any]:
        """Get domain-specific stealth options"""
        options = {
            "webRTC_leak_protection": True,
            "disable_blink_features": True,
            "disable_extensions": True,
            "disable_plugins": True,
            "disable_images": True,
            "disable_javascript": False,  # Keep JS for functionality
            "disable_notifications": True,
            "disable_popups": True,
            "navigator_override": True,
            "webgl_vendor_override": True,
            "timezone_override": True,
            "geolocation_override": True
        }
        
        # Domain-specific adjustments
        domain_lower = domain.lower()
        if "bing.com" in domain_lower:
            options["disable_javascript"] = False  # Bing needs JS
            options["disable_images"] = False      # May need images for SERP
        
        return options
    
    async def execute_stealth_request(self, 
                                    session_id: str,
                                    url: str,
                                    method: str = "GET",
                                    **kwargs) -> Dict[str, Any]:
        """
        Execute a request with full stealth protection
        
        Args:
            session_id: Active session ID
            url: Target URL
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response data and metadata
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        domain = urlparse(url).netloc
        
        # Pre-request checks
        await self._pre_request_checks(session_id, domain)
        
        # Apply rate limiting
        if self.rate_limiter:
            status, delay = self.rate_limiter.check_rate_limit(domain)
            if status != RateLimitStatus.ALLOWED:
                self.logger.info(f"Rate limited for {domain}, waiting {delay:.2f}s")
                await asyncio.sleep(delay)
        
        # Apply human behavior simulation
        if self.behavior_simulator:
            await self.behavior_simulator.pre_request_behavior(session_id)
        
        # Execute request
        start_time = time.time()
        try:
            response = await self._execute_request_with_detection(
                session_id, url, method, **kwargs
            )
            
            success = True
            session.requests_successful += 1
            
        except Exception as e:
            self.logger.error(f"Request failed for {url}: {e}")
            response = {"error": str(e), "success": False}
            success = False
            session.requests_failed += 1
        
        response_time = time.time() - start_time
        session.requests_made += 1
        
        # Record request results
        if self.rate_limiter:
            self.rate_limiter.record_request(
                domain=domain,
                success=success,
                response_time_ms=response_time * 1000,
                status_code=response.get("status_code")
            )
        
        # Post-request analysis
        await self._post_request_analysis(session_id, response, response_time)
        
        # Apply post-request behavior
        if self.behavior_simulator:
            await self.behavior_simulator.post_request_behavior(session_id, success)
        
        return response
    
    async def _pre_request_checks(self, session_id: str, domain: str):
        """Perform pre-request stealth checks and rotations"""
        session = self.active_sessions[session_id]
        current_time = time.time()
        
        # Check if user agent rotation is needed
        if (self.config.rotate_user_agents and 
            self.user_agent_manager and
            (not session.last_user_agent_rotation or 
             current_time - session.last_user_agent_rotation > self.config.user_agent_rotation_interval)):
            
            new_ua = self.user_agent_manager.get_user_agent(domain=domain)
            session.last_user_agent_rotation = current_time
            self.logger.debug(f"Rotated user agent for session {session_id}")
        
        # Check if proxy rotation is needed
        if (self.proxy_rotator and 
            (not session.last_proxy_rotation or
             current_time - session.last_proxy_rotation > self.config.proxy_rotation_interval)):
            
            new_proxy = await self.proxy_rotator.rotate_proxy(session_id)
            session.last_proxy_rotation = current_time
            self.logger.debug(f"Rotated proxy for session {session_id}")
        
        # Assess current risk level
        risk_level = self._assess_detection_risk(session)
        session.current_risk_level = risk_level
        
        # Apply risk-based delays
        if risk_level in [DetectionRisk.HIGH, DetectionRisk.CRITICAL]:
            delay_multiplier = 2.0 if risk_level == DetectionRisk.HIGH else 4.0
            base_delay = random.uniform(*self.config.base_delay_range)
            delay = base_delay * delay_multiplier
            
            self.logger.warning(f"High detection risk for {session_id}, "
                               f"applying {delay:.2f}s delay")
            await asyncio.sleep(delay)
    
    async def _execute_request_with_detection(self, 
                                            session_id: str,
                                            url: str, 
                                            method: str,
                                            **kwargs) -> Dict[str, Any]:
        """Execute request with detection monitoring"""
        session_config = self.session_configs[session_id]
        
        # Use Botasaurus if available for maximum stealth
        if BOTASAURUS_AVAILABLE and self.config.stealth_level in [StealthLevel.AGGRESSIVE, StealthLevel.MAXIMUM]:
            return await self._execute_with_botasaurus(session_id, url, method, **kwargs)
        
        # Fallback to requests with stealth headers
        return await self._execute_with_requests(session_id, url, method, **kwargs)
    
    async def _execute_with_botasaurus(self, 
                                     session_id: str,
                                     url: str, 
                                     method: str,
                                     **kwargs) -> Dict[str, Any]:
        """Execute request using Botasaurus for maximum stealth"""
        session_config = self.session_configs[session_id]
        
        @browser(
            headless=False,
            block_images=True,
            reuse_driver=True,
            user_agent=session_config["browser_config"]["user_agent"],
            proxy=session_config["browser_config"]["proxy"],
            window_size=(1920, 1080)
        )
        def stealth_scrape(driver, data):
            try:
                # Navigate to URL
                driver.get(url)
                
                # Check for detection patterns
                html = driver.page_html
                detection_info = self._detect_anti_bot_measures(html)
                
                # Handle Cloudflare if detected
                if detection_info["cloudflare_detected"]:
                    self.logger.warning(f"Cloudflare detected for {url}")
                    driver.detect_and_bypass_cloudflare()
                    driver.long_random_sleep()
                    html = driver.page_html
                
                # Simulate human behavior
                if self.behavior_simulator:
                    # Scroll and mouse movements
                    driver.run_js("window.scrollTo(0, 300);")
                    driver.short_random_sleep()
                    driver.run_js("window.scrollTo(0, 600);") 
                    driver.short_random_sleep()
                    driver.run_js("window.scrollTo(0, 0);")
                    driver.short_random_sleep()
                
                return {
                    "html": html,
                    "url": driver.current_url,
                    "status_code": 200,
                    "success": True,
                    "detection_info": detection_info
                }
                
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False,
                    "status_code": None
                }
        
        # Execute the scraping function
        try:
            result = stealth_scrape({"url": url})
            return result[0] if result else {"error": "No result", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def _execute_with_requests(self, 
                                   session_id: str,
                                   url: str, 
                                   method: str,
                                   **kwargs) -> Dict[str, Any]:
        """Execute request using requests with stealth headers"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session_config = self.session_configs[session_id]
        
        # Create session with stealth headers
        session = requests.Session()
        
        # Set user agent
        if session_config["browser_config"]["user_agent"]:
            session.headers.update({
                "User-Agent": session_config["browser_config"]["user_agent"]
            })
        
        # Add stealth headers
        stealth_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        session.headers.update(stealth_headers)
        
        # Configure proxy if available
        proxies = None
        if session_config["browser_config"]["proxy"]:
            proxy_url = session_config["browser_config"]["proxy"]
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            response = session.request(
                method=method,
                url=url,
                proxies=proxies,
                timeout=30,
                **kwargs
            )
            
            # Check for detection patterns
            detection_info = self._detect_anti_bot_measures(response.text)
            
            return {
                "html": response.text,
                "url": response.url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "success": response.status_code < 400,
                "detection_info": detection_info
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
                "status_code": None
            }
    
    def _detect_anti_bot_measures(self, html_content: str) -> Dict[str, Any]:
        """Detect anti-bot measures in response content"""
        html_lower = html_content.lower()
        
        detection_info = {
            "cloudflare_detected": False,
            "recaptcha_detected": False,
            "rate_limiting_detected": False,
            "bot_detection_detected": False,
            "patterns_found": []
        }
        
        for detection_type, patterns in self.detection_patterns.items():
            for pattern in patterns:
                if pattern in html_lower:
                    detection_info[f"{detection_type}_detected"] = True
                    detection_info["patterns_found"].append(pattern)
        
        return detection_info
    
    async def _post_request_analysis(self, 
                                   session_id: str,
                                   response: Dict[str, Any], 
                                   response_time: float):
        """Analyze response for detection indicators and adjust strategy"""
        session = self.active_sessions[session_id]
        
        # Update response time tracking
        if session.avg_response_time == 0:
            session.avg_response_time = response_time
        else:
            session.avg_response_time = (session.avg_response_time + response_time) / 2
        
        # Check for detection events
        detection_info = response.get("detection_info", {})
        detection_occurred = any(detection_info.values())
        
        if detection_occurred:
            session.detection_events += 1
            self.logger.warning(f"Detection event in session {session_id}: {detection_info}")
        
        # Update specific counters
        if detection_info.get("cloudflare_detected"):
            session.cloudflare_encounters += 1
        
        if detection_info.get("recaptcha_detected"):
            session.recaptcha_encounters += 1
        
        # Adjust strategy based on detection
        if detection_occurred:
            await self._adjust_strategy_for_detection(session_id, detection_info)
    
    def _assess_detection_risk(self, session: SessionMetrics) -> DetectionRisk:
        """Assess current detection risk level for a session"""
        # Calculate failure rate
        if session.requests_made == 0:
            return DetectionRisk.LOW
        
        failure_rate = session.requests_failed / session.requests_made
        detection_rate = session.detection_events / session.requests_made
        
        # Assess risk based on multiple factors
        risk_score = 0
        
        # Failure rate contribution
        if failure_rate > 0.5:
            risk_score += 3
        elif failure_rate > 0.3:
            risk_score += 2
        elif failure_rate > 0.1:
            risk_score += 1
        
        # Detection rate contribution
        if detection_rate > 0.3:
            risk_score += 3
        elif detection_rate > 0.1:
            risk_score += 2
        elif detection_rate > 0.05:
            risk_score += 1
        
        # Specific detection types
        if session.cloudflare_encounters > 2:
            risk_score += 2
        if session.recaptcha_encounters > 0:
            risk_score += 3
        
        # Response time (unusually slow might indicate detection)
        if session.avg_response_time > 10.0:
            risk_score += 1
        
        # Map score to risk level
        if risk_score >= 6:
            return DetectionRisk.CRITICAL
        elif risk_score >= 4:
            return DetectionRisk.HIGH
        elif risk_score >= 2:
            return DetectionRisk.MEDIUM
        else:
            return DetectionRisk.LOW
    
    async def _adjust_strategy_for_detection(self, 
                                           session_id: str,
                                           detection_info: Dict[str, Any]):
        """Adjust stealth strategy based on detection events"""
        session = self.active_sessions[session_id]
        
        # Force user agent rotation
        if self.user_agent_manager:
            new_ua = self.user_agent_manager.get_user_agent()
            session.last_user_agent_rotation = time.time()
            self.logger.info(f"Forced UA rotation for {session_id} due to detection")
        
        # Force proxy rotation if available
        if self.proxy_rotator:
            await self.proxy_rotator.rotate_proxy(session_id)
            session.last_proxy_rotation = time.time()
            self.logger.info(f"Forced proxy rotation for {session_id} due to detection")
        
        # Increase delays
        base_delay = random.uniform(5.0, 15.0)
        self.logger.info(f"Applying detection recovery delay: {base_delay:.2f}s")
        await asyncio.sleep(base_delay)
    
    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Get metrics for a specific session"""
        return self.active_sessions.get(session_id)
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global stealth manager metrics"""
        if not self.active_sessions:
            return {"active_sessions": 0, "total_requests": 0}
        
        total_requests = sum(s.requests_made for s in self.active_sessions.values())
        total_successful = sum(s.requests_successful for s in self.active_sessions.values())
        total_detection_events = sum(s.detection_events for s in self.active_sessions.values())
        
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        risk_distribution = {}
        for risk_level in DetectionRisk:
            count = sum(1 for s in self.active_sessions.values() 
                       if s.current_risk_level == risk_level)
            risk_distribution[risk_level.value] = count
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_requests": total_requests,
            "success_rate_percentage": round(success_rate, 2),
            "total_detection_events": total_detection_events,
            "risk_distribution": risk_distribution,
            "stealth_level": self.config.stealth_level.value,
            "components_active": {
                "user_agent_manager": self.user_agent_manager is not None,
                "proxy_rotator": self.proxy_rotator is not None,
                "behavior_simulator": self.behavior_simulator is not None,
                "rate_limiter": self.rate_limiter is not None
            }
        }
    
    async def close_session(self, session_id: str):
        """Close a stealth session and clean up resources"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session_duration = time.time() - session.start_time
            
            self.logger.info(f"Closing session {session_id}: "
                           f"duration={session_duration:.2f}s, "
                           f"requests={session.requests_made}, "
                           f"success_rate={session.requests_successful/max(session.requests_made, 1)*100:.1f}%")
            
            del self.active_sessions[session_id]
            if session_id in self.session_configs:
                del self.session_configs[session_id]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close all active sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            asyncio.run(self.close_session(session_id))


# Factory function for easy creation
def create_stealth_manager(stealth_level: StealthLevel = StealthLevel.MODERATE,
                          use_proxies: bool = False,
                          simulate_behavior: bool = True) -> StealthManager:
    """
    Factory function to create a StealthManager with common configurations
    
    Args:
        stealth_level: Level of stealth protection
        use_proxies: Whether to use proxy rotation
        simulate_behavior: Whether to simulate human behavior
        
    Returns:
        Configured StealthManager instance
    """
    config = StealthConfig(
        stealth_level=stealth_level,
        use_proxies=use_proxies,
        simulate_human_behavior=simulate_behavior
    )
    
    return StealthManager(config)