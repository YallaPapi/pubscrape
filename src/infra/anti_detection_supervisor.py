"""
Anti-Detection Supervisor

Coordinates all anti-detection components with per-domain overrides
and comprehensive logging for observability and debugging.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
# Optional import for structlog
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None

# Optional imports for other infrastructure components
try:
    from .browser_manager import BrowserManager, BrowserConfig, BrowserMode
    BROWSER_MANAGER_AVAILABLE = True
except ImportError:
    BROWSER_MANAGER_AVAILABLE = False
    BrowserManager = None
    BrowserConfig = None
    BrowserMode = None

try:
    from .user_agent_manager import UserAgentManager, UserAgentProfile
    USER_AGENT_MANAGER_AVAILABLE = True
except ImportError:
    USER_AGENT_MANAGER_AVAILABLE = False
    UserAgentManager = None
    UserAgentProfile = None

try:
    from .proxy_manager import ProxyManager, ProxyInfo
    PROXY_MANAGER_AVAILABLE = True
except ImportError:
    PROXY_MANAGER_AVAILABLE = False
    ProxyManager = None
    ProxyInfo = None

try:
    from .delay_manager import DelayManager, ActionType, DelayConfig
    DELAY_MANAGER_AVAILABLE = True
except ImportError:
    DELAY_MANAGER_AVAILABLE = False
    DelayManager = None
    ActionType = None
    DelayConfig = None

try:
    from .resource_blocker import ResourceBlocker
    RESOURCE_BLOCKER_AVAILABLE = True
except ImportError:
    RESOURCE_BLOCKER_AVAILABLE = False
    ResourceBlocker = None


@dataclass
class DomainOverride:
    """Domain-specific configuration overrides"""
    domain: str
    browser_mode: Optional[str] = None  # headless, headful, auto
    user_agent_preferences: Optional[Dict[str, Any]] = None
    proxy_preferences: Optional[Dict[str, Any]] = None
    delay_config: Optional[Dict[str, Any]] = None
    resource_blocking: Optional[Dict[str, Any]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class AntiDetectionSupervisor:
    """
    Supervises and coordinates all anti-detection components with
    per-domain overrides and comprehensive observability
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Set up structured logging
        self.logger = self._setup_logging()
        
        # Initialize components
        self.browser_manager = None
        self.user_agent_manager = None
        self.proxy_manager = None
        self.delay_manager = None
        self.resource_blocker = None
        
        # Domain overrides
        self.domain_overrides: Dict[str, DomainOverride] = {}
        self._load_domain_overrides()
        
        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_logs: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize components
        self._initialize_components()
        
        components = self._get_component_status()
        self.logger.info(f"Anti-Detection Supervisor initialized: {components}")
    
    def _setup_logging(self):
        """Set up structured logging for observability"""
        if STRUCTLOG_AVAILABLE:
            # Configure structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            return structlog.get_logger("anti_detection")
        else:
            # Fallback to standard logging
            return logging.getLogger("anti_detection")
    
    def _load_domain_overrides(self):
        """Load domain-specific configuration overrides"""
        overrides_config = self.config.get("domain_overrides", {})
        
        for domain, override_data in overrides_config.items():
            try:
                override = DomainOverride(domain=domain, **override_data)
                self.domain_overrides[domain] = override
            except Exception as e:
                self.logger.error("Failed to load domain override", 
                                domain=domain, error=str(e))
    
    def _initialize_components(self):
        """Initialize all anti-detection components"""
        try:
            # Browser Manager
            if BROWSER_MANAGER_AVAILABLE:
                browser_config = BrowserConfig(**self.config.get("browser", {}))
                self.browser_manager = BrowserManager(browser_config)
            else:
                self.logger.warning("BrowserManager not available")
            
            # User Agent Manager
            if USER_AGENT_MANAGER_AVAILABLE:
                ua_config = self.config.get("user_agent", {})
                self.user_agent_manager = UserAgentManager(ua_config)
            else:
                self.logger.warning("UserAgentManager not available")
            
            # Proxy Manager
            if PROXY_MANAGER_AVAILABLE:
                proxy_config = self.config.get("proxy", {})
                self.proxy_manager = ProxyManager(proxy_config)
            else:
                self.logger.warning("ProxyManager not available")
            
            # Delay Manager
            if DELAY_MANAGER_AVAILABLE:
                delay_config_data = self.config.get("delays", {})
                delay_config = DelayConfig(**delay_config_data)
                self.delay_manager = DelayManager(delay_config)
            else:
                self.logger.warning("DelayManager not available")
            
            # Resource Blocker
            if RESOURCE_BLOCKER_AVAILABLE:
                resource_config = self.config.get("resource_blocking", {})
                self.resource_blocker = ResourceBlocker(resource_config)
            else:
                self.logger.warning("ResourceBlocker not available")
            
            self.logger.info("Anti-detection components initialized (some may be unavailable)")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize some components: {str(e)}")
            # Don't raise - allow partial initialization
    
    def create_session(self, 
                      session_id: str, 
                      domain: Optional[str] = None,
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new anti-detection session with all components configured
        
        Args:
            session_id: Unique session identifier
            domain: Optional target domain for domain-specific overrides
            context: Additional context for session creation
            
        Returns:
            Session configuration dictionary
        """
        start_time = time.time()
        
        try:
            # Apply domain overrides if available
            effective_config = self._apply_domain_overrides(domain)
            
            # Get user agent (or create mock)
            user_agent = None
            if self.user_agent_manager:
                user_agent = self.user_agent_manager.get_user_agent(
                    domain=domain,
                    **effective_config.get("user_agent_preferences", {})
                )
            else:
                # Mock user agent
                user_agent = type('MockUserAgent', (), {
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'browser': 'chrome',
                    'platform': 'windows'
                })()
            
            # Get proxy (or None)
            proxy = None
            if self.proxy_manager:
                proxy = self.proxy_manager.get_proxy(
                    session_id=session_id,
                    domain=domain,
                    **effective_config.get("proxy_preferences", {})
                )
            
            # Get browser profile path (or mock)
            profile_path = f"profile_{session_id}"
            if self.user_agent_manager:
                profile_path = self.user_agent_manager.get_profile_path(session_id, domain)
            
            # Get resource blocking config (or empty)
            resource_config = {}
            if self.resource_blocker:
                resource_config = self.resource_blocker.get_chrome_resource_blocking_config()
                if domain:
                    domain_blocker = self.resource_blocker.create_domain_specific_blocker(domain)
                    resource_config = domain_blocker.get_chrome_resource_blocking_config()
            
            # Create browser session (if browser manager available)
            browser = None
            if self.browser_manager:
                browser_config = BrowserConfig(
                    mode=BrowserMode(effective_config.get("browser_mode", "headless")),
                    user_agent=user_agent.user_agent,
                    profile_path=str(profile_path),
                    proxy=proxy.proxy_url if proxy else None,
                    block_resources=list(resource_config.keys()) if resource_config else None,
                    domain_overrides=self.browser_manager.config.domain_overrides
                )
                
                browser = self.browser_manager.get_browser_session(session_id, domain)
            
            # Session configuration
            session_config = {
                "session_id": session_id,
                "domain": domain,
                "user_agent": asdict(user_agent),
                "proxy": asdict(proxy) if proxy else None,
                "profile_path": str(profile_path),
                "resource_blocking": resource_config,
                "browser_mode": effective_config.get("browser_mode", "headless"),
                "created_at": time.time(),
                "context": context or {}
            }
            
            # Store session
            self.active_sessions[session_id] = session_config
            self.session_logs[session_id] = []
            
            # Log session creation
            self._log_session_event(session_id, "session_created", {
                "domain": domain,
                "user_agent": user_agent.user_agent,
                "proxy_host": proxy.host if proxy else None,
                "browser_mode": effective_config.get("browser_mode"),
                "creation_time_ms": (time.time() - start_time) * 1000
            })
            
            self.logger.info(f"Session created successfully: session_id={session_id}, "
                             f"domain={domain}, user_agent_browser={user_agent.browser}, "
                             f"proxy_provider={proxy.provider if proxy else None}")
            
            return session_config
            
        except Exception as e:
            self.logger.error(f"Failed to create session: session_id={session_id}, "
                              f"domain={domain}, error={str(e)}")
            raise
    
    def _apply_domain_overrides(self, domain: Optional[str]) -> Dict[str, Any]:
        """Apply domain-specific configuration overrides"""
        base_config = {
            "browser_mode": "headless",
            "user_agent_preferences": {},
            "proxy_preferences": {},
            "delay_config": {},
            "resource_blocking": {}
        }
        
        if not domain:
            return base_config
        
        # Check for exact domain match
        if domain in self.domain_overrides:
            override = self.domain_overrides[domain]
            return self._merge_override(base_config, override)
        
        # Check for subdomain matches
        for override_domain, override in self.domain_overrides.items():
            if domain.endswith(override_domain):
                return self._merge_override(base_config, override)
        
        return base_config
    
    def _merge_override(self, base_config: Dict[str, Any], override: DomainOverride) -> Dict[str, Any]:
        """Merge domain override with base configuration"""
        merged = base_config.copy()
        
        if override.browser_mode:
            merged["browser_mode"] = override.browser_mode
        
        if override.user_agent_preferences:
            merged["user_agent_preferences"].update(override.user_agent_preferences)
        
        if override.proxy_preferences:
            merged["proxy_preferences"].update(override.proxy_preferences)
        
        if override.delay_config:
            merged["delay_config"].update(override.delay_config)
        
        if override.resource_blocking:
            merged["resource_blocking"].update(override.resource_blocking)
        
        return merged
    
    def delay_for_action(self, 
                        session_id: str, 
                        action_type: ActionType,
                        context: Optional[Dict[str, Any]] = None) -> float:
        """Execute a delay for an action with logging"""
        delay_time = self.delay_manager.delay(action_type, context)
        
        # Log the delay
        self._log_session_event(session_id, "action_delay", {
            "action_type": action_type.value,
            "delay_ms": delay_time * 1000,
            "context": context or {}
        })
        
        return delay_time
    
    def record_request_result(self, 
                            session_id: str,
                            url: str,
                            success: bool,
                            response_time: Optional[float] = None,
                            status_code: Optional[int] = None,
                            error: Optional[str] = None):
        """Record the result of a request for monitoring"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        # Update proxy statistics if proxy was used
        if session.get("proxy"):
            proxy_info = ProxyInfo(**session["proxy"])
            self.proxy_manager.record_proxy_result(proxy_info, success, response_time)
        
        # Log the request
        self._log_session_event(session_id, "request_completed", {
            "url": url,
            "success": success,
            "response_time_ms": response_time * 1000 if response_time else None,
            "status_code": status_code,
            "error": error
        })
        
        # Update session metadata
        if session_id in self.browser_manager.session_metadata:
            self.browser_manager.update_session_stats(session_id, 1)
    
    def switch_user_agent(self, session_id: str, domain: Optional[str] = None):
        """Switch user agent for a session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        old_ua = session.get("user_agent", {}).get("user_agent", "unknown")
        
        # Get new user agent
        new_ua = self.user_agent_manager.get_user_agent(domain=domain)
        session["user_agent"] = asdict(new_ua)
        
        # Log the change
        self._log_session_event(session_id, "user_agent_changed", {
            "old_user_agent": old_ua,
            "new_user_agent": new_ua.user_agent,
            "browser": new_ua.browser,
            "platform": new_ua.platform
        })
        
        self.logger.info(f"User agent switched: session_id={session_id}, "
                         f"old_browser={old_ua.split()[0] if old_ua else 'unknown'}, "
                         f"new_browser={new_ua.browser}")
    
    def switch_proxy(self, session_id: str, domain: Optional[str] = None):
        """Switch proxy for a session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        old_proxy = session.get("proxy", {}).get("host", "none")
        
        # Get new proxy
        new_proxy = self.proxy_manager.get_proxy(session_id=session_id, domain=domain)
        session["proxy"] = asdict(new_proxy) if new_proxy else None
        
        # Log the change
        self._log_session_event(session_id, "proxy_changed", {
            "old_proxy": old_proxy,
            "new_proxy": new_proxy.host if new_proxy else None,
            "provider": new_proxy.provider if new_proxy else None
        })
        
        self.logger.info(f"Proxy switched: session_id={session_id}, "
                         f"old_proxy={old_proxy}, new_proxy={new_proxy.host if new_proxy else 'none'}")
    
    def _log_session_event(self, 
                          session_id: str, 
                          event_type: str, 
                          data: Dict[str, Any]):
        """Log a session event for observability"""
        event = {
            "timestamp": time.time(),
            "session_id": session_id,
            "event_type": event_type,
            "data": data
        }
        
        # Store in session logs
        if session_id not in self.session_logs:
            self.session_logs[session_id] = []
        
        self.session_logs[session_id].append(event)
        
        # Keep only last 1000 events per session
        if len(self.session_logs[session_id]) > 1000:
            self.session_logs[session_id] = self.session_logs[session_id][-1000:]
    
    def close_session(self, session_id: str):
        """Close a session and clean up resources"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session_duration = time.time() - session["created_at"]
        
        # Close browser session
        self.browser_manager.close_session(session_id)
        
        # Log session closure
        self._log_session_event(session_id, "session_closed", {
            "duration_seconds": session_duration,
            "total_events": len(self.session_logs.get(session_id, []))
        })
        
        # Clean up
        del self.active_sessions[session_id]
        
        self.logger.info(f"Session closed: session_id={session_id}, "
                         f"duration_minutes={session_duration/60:.2f}")
    
    def get_session_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """Get logs for a specific session"""
        return self.session_logs.get(session_id, [])
    
    def export_session_logs(self, 
                           session_id: str, 
                           output_path: Optional[Path] = None) -> Path:
        """Export session logs to JSON file"""
        if not output_path:
            output_path = Path(f"session_logs_{session_id}_{int(time.time())}.json")
        
        logs = self.get_session_logs(session_id)
        session_info = self.active_sessions.get(session_id, {})
        
        export_data = {
            "session_info": session_info,
            "events": logs,
            "exported_at": time.time()
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Session logs exported: session_id={session_id}, "
                         f"output_path={str(output_path)}, event_count={len(logs)}")
        
        return output_path
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components"""
        stats = {
            "active_sessions": len(self.active_sessions),
            "total_session_logs": sum(len(logs) for logs in self.session_logs.values()),
            "domain_overrides": len(self.domain_overrides),
            "component_stats": {}
        }
        
        # Component statistics
        if self.user_agent_manager:
            stats["component_stats"]["user_agents"] = self.user_agent_manager.get_usage_stats()
        
        if self.proxy_manager:
            stats["component_stats"]["proxies"] = self.proxy_manager.get_statistics()
        
        if self.delay_manager:
            stats["component_stats"]["delays"] = self.delay_manager.get_statistics()
        
        if self.resource_blocker:
            stats["component_stats"]["resource_blocking"] = self.resource_blocker.get_statistics()
        
        return stats
    
    def _get_component_status(self) -> Dict[str, bool]:
        """Get status of all components"""
        return {
            "browser_manager": self.browser_manager is not None,
            "user_agent_manager": self.user_agent_manager is not None,
            "proxy_manager": self.proxy_manager is not None,
            "delay_manager": self.delay_manager is not None,
            "resource_blocker": self.resource_blocker is not None
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close all active sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            self.close_session(session_id)


# Factory function for easy creation
def create_anti_detection_supervisor(config: Optional[Dict[str, Any]] = None) -> AntiDetectionSupervisor:
    """
    Factory function to create an AntiDetectionSupervisor
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured AntiDetectionSupervisor instance
    """
    return AntiDetectionSupervisor(config)