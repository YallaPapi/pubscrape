"""
AntiDetection Integration Tool

Tool for integrating SiteCrawler with AntiDetectionSupervisor to manage
browser sessions, proxies, and anti-detection measures.
"""

import logging
import time
import random
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field

# Import infrastructure components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from infra.anti_detection_supervisor import AntiDetectionSupervisor, DomainOverride
    ANTI_DETECTION_AVAILABLE = True
except ImportError:
    AntiDetectionSupervisor = None
    DomainOverride = None
    ANTI_DETECTION_AVAILABLE = False


class SessionRotationTrigger(Enum):
    """Triggers for session rotation"""
    ERROR_COUNT = "error_count"
    TIME_THRESHOLD = "time_threshold"
    DOMAIN_CHANGE = "domain_change"
    MANUAL_ROTATION = "manual_rotation"
    CHALLENGE_DETECTED = "challenge_detected"


@dataclass
class CrawlSessionConfig:
    """Configuration for a crawl session"""
    domain: str
    session_id: str
    browser_mode: str = "headless"
    enable_resource_blocking: bool = True
    blocked_resources: List[str] = field(default_factory=lambda: [".png", ".jpg", ".jpeg", ".gif", ".css", ".js"])
    user_agent_override: Optional[str] = None
    proxy_override: Optional[str] = None
    crawl_delay: float = 1.0
    max_errors_before_rotation: int = 3
    max_session_duration: float = 1800.0  # 30 minutes
    created_at: float = field(default_factory=time.time)
    
    @property
    def is_expired(self) -> bool:
        """Check if session has exceeded duration limit"""
        return (time.time() - self.created_at) > self.max_session_duration


@dataclass
class SessionMetrics:
    """Metrics for a crawl session"""
    session_id: str
    domain: str
    requests_made: int = 0
    errors_encountered: int = 0
    challenges_detected: int = 0
    blocks_detected: int = 0
    total_response_time: float = 0.0
    rotation_count: int = 0
    start_time: float = field(default_factory=time.time)
    last_request_time: Optional[float] = None
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return self.total_response_time / self.requests_made if self.requests_made > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage"""
        return (self.errors_encountered / self.requests_made) * 100 if self.requests_made > 0 else 0.0
    
    @property
    def session_duration(self) -> float:
        """Get session duration in seconds"""
        return time.time() - self.start_time


class AntiDetectionManager:
    """
    Manager for coordinating anti-detection measures with crawling operations.
    
    This class integrates with the AntiDetectionSupervisor to provide
    session management, rotation policies, and domain-specific configurations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Anti-detection supervisor
        self.supervisor = None
        self._initialize_supervisor()
        
        # Session management
        self.active_sessions: Dict[str, CrawlSessionConfig] = {}
        self.session_metrics: Dict[str, SessionMetrics] = {}
        self.domain_overrides: Dict[str, DomainOverride] = {}
        
        # Configuration
        self.default_browser_mode = self.config.get("default_browser_mode", "headless")
        self.enable_session_rotation = self.config.get("enable_session_rotation", True)
        self.max_concurrent_sessions = self.config.get("max_concurrent_sessions", 5)
        self.session_cleanup_interval = self.config.get("session_cleanup_interval", 300)  # 5 minutes
        
        # Domain-specific settings
        self._load_domain_overrides()
        
        self.logger.info("AntiDetectionManager initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the manager"""
        logger = logging.getLogger(f"{__name__}.AntiDetectionManager")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_supervisor(self) -> bool:
        """Initialize the AntiDetectionSupervisor"""
        if not ANTI_DETECTION_AVAILABLE:
            self.logger.warning("AntiDetectionSupervisor not available - using mock implementation")
            return False
        
        try:
            supervisor_config = self.config.get("supervisor", {})
            self.supervisor = AntiDetectionSupervisor(supervisor_config)
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize AntiDetectionSupervisor: {e}")
            return False
    
    def _load_domain_overrides(self):
        """Load domain-specific override configurations"""
        overrides_config = self.config.get("domain_overrides", {})
        
        for domain, override_data in overrides_config.items():
            if ANTI_DETECTION_AVAILABLE and DomainOverride:
                try:
                    override = DomainOverride(domain=domain, **override_data)
                    self.domain_overrides[domain] = override
                    self.logger.debug(f"Loaded domain override for {domain}")
                except Exception as e:
                    self.logger.error(f"Failed to load domain override for {domain}: {e}")
    
    def create_crawl_session(self, domain: str, custom_config: Optional[Dict[str, Any]] = None) -> Optional[CrawlSessionConfig]:
        """
        Create a new crawl session with anti-detection measures.
        
        Args:
            domain: Domain to create session for
            custom_config: Optional custom configuration
            
        Returns:
            CrawlSessionConfig or None if creation failed
        """
        try:
            # Check session limits
            if len(self.active_sessions) >= self.max_concurrent_sessions:
                self.logger.warning(f"Max concurrent sessions reached ({self.max_concurrent_sessions})")
                self._cleanup_expired_sessions()
                
                if len(self.active_sessions) >= self.max_concurrent_sessions:
                    return None
            
            # Generate session ID
            session_id = f"crawl_{domain}_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Apply domain overrides
            session_config = self._create_session_config(domain, session_id, custom_config)
            
            # Create supervisor session if available
            if self.supervisor:
                try:
                    supervisor_session = self.supervisor.create_session(
                        session_id=session_id,
                        domain=domain,
                        context={
                            "crawl_type": "site_discovery",
                            "domain": domain,
                            "created_at": time.time()
                        }
                    )
                    self.logger.info(f"Created supervisor session: {session_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to create supervisor session: {e}")
            
            # Store session
            self.active_sessions[session_id] = session_config
            self.session_metrics[session_id] = SessionMetrics(
                session_id=session_id,
                domain=domain
            )
            
            self.logger.info(f"Created crawl session: {session_id} for {domain}")
            return session_config
            
        except Exception as e:
            self.logger.error(f"Error creating crawl session for {domain}: {e}")
            return None
    
    def _create_session_config(self, domain: str, session_id: str, 
                              custom_config: Optional[Dict[str, Any]] = None) -> CrawlSessionConfig:
        """Create session configuration with domain overrides"""
        custom_config = custom_config or {}
        
        # Base configuration
        config = CrawlSessionConfig(
            domain=domain,
            session_id=session_id,
            browser_mode=self.default_browser_mode,
            enable_resource_blocking=True,
            crawl_delay=1.0,
            max_errors_before_rotation=3,
            max_session_duration=1800.0
        )
        
        # Apply domain override if available
        if domain in self.domain_overrides:
            override = self.domain_overrides[domain]
            
            if override.browser_mode:
                config.browser_mode = override.browser_mode
            
            if override.resource_blocking:
                config.enable_resource_blocking = override.resource_blocking.get("enabled", True)
                if "blocked_extensions" in override.resource_blocking:
                    config.blocked_resources = override.resource_blocking["blocked_extensions"]
            
            if override.delay_config:
                config.crawl_delay = override.delay_config.get("base_delay", config.crawl_delay)
                config.max_errors_before_rotation = override.delay_config.get("max_errors", config.max_errors_before_rotation)
        
        # Apply custom configuration
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def get_session_for_request(self, domain: str, url: str) -> Optional[CrawlSessionConfig]:
        """
        Get or create an appropriate session for a request.
        
        Args:
            domain: Domain being requested
            url: Specific URL being requested
            
        Returns:
            CrawlSessionConfig or None if unavailable
        """
        # Look for existing session for this domain
        for session_id, session_config in self.active_sessions.items():
            if session_config.domain == domain and not session_config.is_expired:
                # Check if session needs rotation
                metrics = self.session_metrics.get(session_id)
                if metrics and self._should_rotate_session(session_config, metrics):
                    self.logger.info(f"Rotating session {session_id} due to trigger conditions")
                    self._rotate_session(session_id)
                    continue
                
                return session_config
        
        # Create new session if none available
        return self.create_crawl_session(domain)
    
    def _should_rotate_session(self, session_config: CrawlSessionConfig, 
                              metrics: SessionMetrics) -> bool:
        """Check if session should be rotated"""
        if not self.enable_session_rotation:
            return False
        
        # Check error count
        if metrics.errors_encountered >= session_config.max_errors_before_rotation:
            self.logger.debug(f"Session rotation triggered: error count ({metrics.errors_encountered})")
            return True
        
        # Check session duration
        if session_config.is_expired:
            self.logger.debug(f"Session rotation triggered: duration expired")
            return True
        
        # Check challenge/block rate
        if metrics.requests_made > 5:
            challenge_rate = (metrics.challenges_detected + metrics.blocks_detected) / metrics.requests_made
            if challenge_rate > 0.3:  # 30% challenge/block rate
                self.logger.debug(f"Session rotation triggered: high challenge rate ({challenge_rate:.2f})")
                return True
        
        return False
    
    def _rotate_session(self, session_id: str):
        """Rotate a session by closing it and removing from active sessions"""
        if session_id in self.active_sessions:
            session_config = self.active_sessions[session_id]
            
            # Close supervisor session
            if self.supervisor:
                try:
                    self.supervisor.close_session(session_id)
                except Exception as e:
                    self.logger.warning(f"Error closing supervisor session {session_id}: {e}")
            
            # Update metrics
            if session_id in self.session_metrics:
                self.session_metrics[session_id].rotation_count += 1
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            self.logger.info(f"Rotated session: {session_id} for domain {session_config.domain}")
    
    def record_request_result(self, session_id: str, url: str, success: bool,
                             response_time: Optional[float] = None,
                             status_code: Optional[int] = None,
                             error_type: Optional[str] = None):
        """
        Record the result of a request for session management.
        
        Args:
            session_id: Session ID that made the request
            url: URL that was requested
            success: Whether the request was successful
            response_time: Response time in seconds
            status_code: HTTP status code
            error_type: Type of error if request failed
        """
        if session_id not in self.session_metrics:
            return
        
        metrics = self.session_metrics[session_id]
        metrics.requests_made += 1
        metrics.last_request_time = time.time()
        
        if response_time:
            metrics.total_response_time += response_time
        
        if not success:
            metrics.errors_encountered += 1
            
            # Classify error types for metrics
            if error_type:
                if "challenge" in error_type.lower():
                    metrics.challenges_detected += 1
                elif "block" in error_type.lower():
                    metrics.blocks_detected += 1
        
        # Record with supervisor if available
        if self.supervisor:
            try:
                self.supervisor.record_request_result(
                    session_id=session_id,
                    url=url,
                    success=success,
                    response_time=response_time,
                    status_code=status_code,
                    error=error_type
                )
            except Exception as e:
                self.logger.warning(f"Error recording request result with supervisor: {e}")
        
        self.logger.debug(f"Recorded request result for session {session_id}: "
                         f"success={success}, status={status_code}")
    
    def enforce_crawl_delay(self, session_id: str) -> float:
        """
        Enforce crawl delay for a session.
        
        Args:
            session_id: Session ID to enforce delay for
            
        Returns:
            Actual delay time applied in seconds
        """
        if session_id not in self.active_sessions:
            return 0.0
        
        session_config = self.active_sessions[session_id]
        metrics = self.session_metrics.get(session_id)
        
        if not metrics or not metrics.last_request_time:
            return 0.0
        
        # Calculate required delay
        time_since_last = time.time() - metrics.last_request_time
        required_delay = session_config.crawl_delay
        
        # Add jitter
        jitter = random.uniform(-0.2, 0.2) * required_delay
        required_delay = max(0.1, required_delay + jitter)
        
        # Apply delay if needed
        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            self.logger.debug(f"Applying crawl delay: {sleep_time:.2f}s for session {session_id}")
            time.sleep(sleep_time)
            return sleep_time
        
        return 0.0
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = []
        
        for session_id, session_config in self.active_sessions.items():
            if session_config.is_expired:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.logger.info(f"Cleaning up expired session: {session_id}")
            self._rotate_session(session_id)
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        total_requests = sum(m.requests_made for m in self.session_metrics.values())
        total_errors = sum(m.errors_encountered for m in self.session_metrics.values())
        total_challenges = sum(m.challenges_detected for m in self.session_metrics.values())
        
        active_domains = set(s.domain for s in self.active_sessions.values())
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_sessions_created": len(self.session_metrics),
            "active_domains": len(active_domains),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "total_challenges": total_challenges,
            "error_rate_percent": (total_errors / total_requests) * 100 if total_requests > 0 else 0,
            "challenge_rate_percent": (total_challenges / total_requests) * 100 if total_requests > 0 else 0,
            "supervisor_available": self.supervisor is not None,
            "domain_overrides_loaded": len(self.domain_overrides),
            "session_details": [
                {
                    "session_id": session_id,
                    "domain": config.domain,
                    "browser_mode": config.browser_mode,
                    "age_seconds": time.time() - config.created_at,
                    "requests_made": self.session_metrics.get(session_id, SessionMetrics("", "")).requests_made,
                    "error_rate": self.session_metrics.get(session_id, SessionMetrics("", "")).error_rate
                }
                for session_id, config in self.active_sessions.items()
            ]
        }
    
    def close_all_sessions(self):
        """Close all active sessions"""
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            self._rotate_session(session_id)
        
        self.logger.info(f"Closed {len(session_ids)} active sessions")


class AntiDetectionIntegrationTool(BaseTool):
    """
    Tool for managing anti-detection integration during crawling operations.
    
    This tool provides session management, rotation, and anti-detection
    coordination for site crawling activities.
    """
    
    operation: str = Field(
        ...,
        description="Operation to perform: 'create_session', 'get_session', 'record_result', 'enforce_delay', 'get_statistics'"
    )
    
    domain: Optional[str] = Field(
        None,
        description="Domain for session operations"
    )
    
    url: Optional[str] = Field(
        None,
        description="URL being processed (for context)"
    )
    
    session_id: Optional[str] = Field(
        None,
        description="Specific session ID to operate on"
    )
    
    browser_mode: str = Field(
        "headless",
        description="Browser mode: headless, headful, auto"
    )
    
    enable_resource_blocking: bool = Field(
        True,
        description="Whether to enable resource blocking"
    )
    
    blocked_resources: List[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".gif", ".css", ".js"],
        description="List of resource extensions to block"
    )
    
    crawl_delay: float = Field(
        1.0,
        description="Base crawl delay in seconds"
    )
    
    # For request result recording
    request_success: Optional[bool] = Field(
        None,
        description="Whether the request was successful"
    )
    
    response_time: Optional[float] = Field(
        None,
        description="Response time in seconds"
    )
    
    status_code: Optional[int] = Field(
        None,
        description="HTTP status code"
    )
    
    error_type: Optional[str] = Field(
        None,
        description="Type of error encountered"
    )
    
    # Configuration
    enable_session_rotation: bool = Field(
        True,
        description="Whether to enable automatic session rotation"
    )
    
    max_concurrent_sessions: int = Field(
        5,
        description="Maximum number of concurrent sessions"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.anti_detection_manager = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.AntiDetectionIntegrationTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_manager(self) -> bool:
        """Initialize the anti-detection manager"""
        if self.anti_detection_manager is None:
            try:
                config = {
                    "default_browser_mode": self.browser_mode,
                    "enable_session_rotation": self.enable_session_rotation,
                    "max_concurrent_sessions": self.max_concurrent_sessions,
                    "supervisor": {
                        "browser": {
                            "mode": self.browser_mode,
                            "resource_blocking": {
                                "enabled": self.enable_resource_blocking,
                                "blocked_extensions": self.blocked_resources
                            }
                        },
                        "delays": {
                            "base_delay": self.crawl_delay
                        }
                    }
                }
                self.anti_detection_manager = AntiDetectionManager(config)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize anti-detection manager: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the anti-detection integration operation.
        
        Returns:
            Dictionary containing operation results
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting anti-detection operation: {self.operation}")
            
            # Initialize manager
            if not self._initialize_manager():
                return {
                    "success": False,
                    "error": "Failed to initialize anti-detection manager",
                    "operation": self.operation
                }
            
            if self.operation == "create_session":
                return self._create_session_operation(start_time)
            
            elif self.operation == "get_session":
                return self._get_session_operation(start_time)
            
            elif self.operation == "record_result":
                return self._record_result_operation(start_time)
            
            elif self.operation == "enforce_delay":
                return self._enforce_delay_operation(start_time)
            
            elif self.operation == "get_statistics":
                return self._get_statistics_operation(start_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {self.operation}",
                    "operation": self.operation,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            self.logger.error(f"Error during anti-detection operation: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": self.operation,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _create_session_operation(self, start_time: float) -> Dict[str, Any]:
        """Create a new crawl session"""
        if not self.domain:
            return {
                "success": False,
                "error": "Domain required for session creation",
                "operation": "create_session",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            custom_config = {
                "browser_mode": self.browser_mode,
                "enable_resource_blocking": self.enable_resource_blocking,
                "blocked_resources": self.blocked_resources,
                "crawl_delay": self.crawl_delay
            }
            
            session_config = self.anti_detection_manager.create_crawl_session(
                self.domain, custom_config
            )
            
            if session_config:
                return {
                    "success": True,
                    "operation": "create_session",
                    "domain": self.domain,
                    "session_created": True,
                    "session_config": {
                        "session_id": session_config.session_id,
                        "domain": session_config.domain,
                        "browser_mode": session_config.browser_mode,
                        "enable_resource_blocking": session_config.enable_resource_blocking,
                        "blocked_resources": session_config.blocked_resources,
                        "crawl_delay": session_config.crawl_delay,
                        "max_errors_before_rotation": session_config.max_errors_before_rotation,
                        "max_session_duration": session_config.max_session_duration
                    },
                    "anti_detection_available": ANTI_DETECTION_AVAILABLE,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create session - may have reached limits",
                    "operation": "create_session",
                    "domain": self.domain,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "create_session",
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_session_operation(self, start_time: float) -> Dict[str, Any]:
        """Get session for a domain/URL"""
        if not self.domain:
            return {
                "success": False,
                "error": "Domain required for session retrieval",
                "operation": "get_session",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            session_config = self.anti_detection_manager.get_session_for_request(
                self.domain, self.url or ""
            )
            
            if session_config:
                return {
                    "success": True,
                    "operation": "get_session",
                    "domain": self.domain,
                    "url": self.url,
                    "session_available": True,
                    "session_config": {
                        "session_id": session_config.session_id,
                        "domain": session_config.domain,
                        "browser_mode": session_config.browser_mode,
                        "crawl_delay": session_config.crawl_delay,
                        "is_expired": session_config.is_expired
                    },
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            else:
                return {
                    "success": False,
                    "error": "No session available for domain",
                    "operation": "get_session",
                    "domain": self.domain,
                    "session_available": False,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "get_session",
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _record_result_operation(self, start_time: float) -> Dict[str, Any]:
        """Record request result"""
        if not self.session_id:
            return {
                "success": False,
                "error": "Session ID required for result recording",
                "operation": "record_result",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            self.anti_detection_manager.record_request_result(
                session_id=self.session_id,
                url=self.url or "",
                success=self.request_success or False,
                response_time=self.response_time,
                status_code=self.status_code,
                error_type=self.error_type
            )
            
            return {
                "success": True,
                "operation": "record_result",
                "session_id": self.session_id,
                "url": self.url,
                "result_recorded": True,
                "request_success": self.request_success,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "record_result",
                "session_id": self.session_id,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _enforce_delay_operation(self, start_time: float) -> Dict[str, Any]:
        """Enforce crawl delay"""
        if not self.session_id:
            return {
                "success": False,
                "error": "Session ID required for delay enforcement",
                "operation": "enforce_delay",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            delay_applied = self.anti_detection_manager.enforce_crawl_delay(self.session_id)
            
            return {
                "success": True,
                "operation": "enforce_delay",
                "session_id": self.session_id,
                "delay_applied_seconds": delay_applied,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "enforce_delay",
                "session_id": self.session_id,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_statistics_operation(self, start_time: float) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            statistics = self.anti_detection_manager.get_session_statistics()
            
            return {
                "success": True,
                "operation": "get_statistics",
                "session_statistics": statistics,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "get_statistics",
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the anti-detection integration tool
    print("Testing AntiDetectionIntegrationTool...")
    
    # Test session creation
    tool = AntiDetectionIntegrationTool(
        operation="create_session",
        domain="example.com",
        browser_mode="headless",
        enable_resource_blocking=True,
        crawl_delay=1.5
    )
    
    result = tool.run()
    print(f"Session creation result: {result.get('success', False)}")
    
    if result.get("success"):
        session_config = result.get("session_config", {})
        session_id = session_config.get("session_id")
        print(f"Session ID: {session_id}")
        
        # Test getting session
        tool = AntiDetectionIntegrationTool(
            operation="get_session",
            domain="example.com",
            url="https://example.com/contact"
        )
        
        result = tool.run()
        print(f"Get session result: {result.get('success', False)}")
        
        # Test statistics
        tool = AntiDetectionIntegrationTool(operation="get_statistics")
        result = tool.run()
        print(f"Statistics result: {result.get('success', False)}")
        
        if result.get("success"):
            stats = result.get("session_statistics", {})
            print(f"Active sessions: {stats.get('active_sessions', 0)}")
            print(f"Anti-detection available: {stats.get('supervisor_available', False)}")