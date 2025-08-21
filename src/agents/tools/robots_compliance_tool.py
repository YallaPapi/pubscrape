"""
Robots.txt Compliance Tool

Tool for parsing robots.txt files and implementing crawl policies
including polite delays and page limits.
"""

import logging
import time
import random
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from urllib.robotparser import RobotFileParser
import requests

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


@dataclass
class RobotsDirective:
    """Represents a robots.txt directive"""
    user_agent: str
    directive_type: str  # 'allow', 'disallow', 'crawl-delay', 'sitemap'
    path: Optional[str] = None
    value: Optional[str] = None
    line_number: int = 0


@dataclass
class CrawlPolicy:
    """Represents crawl policies for a domain"""
    domain: str
    max_pages: int = 10
    base_delay: float = 1.0
    robots_delay: Optional[float] = None
    jitter_factor: float = 0.3
    respect_robots: bool = True
    allowed_paths: Set[str] = field(default_factory=set)
    disallowed_paths: Set[str] = field(default_factory=set)
    sitemaps: List[str] = field(default_factory=list)
    user_agent: str = "*"
    last_request_time: Optional[float] = None
    request_count: int = 0
    
    @property
    def effective_delay(self) -> float:
        """Calculate the effective delay including robots.txt and jitter"""
        base = self.robots_delay if self.robots_delay is not None else self.base_delay
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * base
        return max(0.1, base + jitter)


class RobotsTxtParser:
    """
    Parser for robots.txt files with comprehensive directive support.
    
    Handles standard robots.txt directives including user-agent specific rules,
    crawl delays, sitemaps, and path allow/disallow patterns.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Configuration
        self.default_user_agent = self.config.get("default_user_agent", "*")
        self.timeout = self.config.get("timeout", 10)
        self.max_file_size = self.config.get("max_file_size", 500000)  # 500KB
        
        self.logger.info("RobotsTxtParser initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the parser"""
        logger = logging.getLogger(f"{__name__}.RobotsTxtParser")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def fetch_robots_txt(self, domain: str) -> Optional[str]:
        """
        Fetch robots.txt content from a domain.
        
        Args:
            domain: Domain to fetch robots.txt from
            
        Returns:
            Robots.txt content or None if not found/accessible
        """
        # Try both HTTPS and HTTP
        for protocol in ['https', 'http']:
            robots_url = f"{protocol}://{domain}/robots.txt"
            
            try:
                self.logger.debug(f"Fetching robots.txt from {robots_url}")
                
                response = requests.get(
                    robots_url,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'SiteCrawler-Bot/1.0 (Respectful Crawler)',
                        'Accept': 'text/plain, text/html, */*'
                    }
                )
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check file size
                    if len(content) > self.max_file_size:
                        self.logger.warning(f"Robots.txt too large ({len(content)} bytes), truncating")
                        content = content[:self.max_file_size]
                    
                    self.logger.info(f"Successfully fetched robots.txt from {domain} ({len(content)} bytes)")
                    return content
                    
                elif response.status_code == 404:
                    self.logger.debug(f"No robots.txt found at {robots_url}")
                else:
                    self.logger.warning(f"Unexpected status {response.status_code} for {robots_url}")
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout fetching robots.txt from {robots_url}")
            except requests.exceptions.ConnectionError:
                self.logger.debug(f"Connection error fetching robots.txt from {robots_url}")
            except Exception as e:
                self.logger.error(f"Error fetching robots.txt from {robots_url}: {e}")
        
        self.logger.info(f"No accessible robots.txt found for {domain}")
        return None
    
    def parse_robots_txt(self, content: str, domain: str = "") -> List[RobotsDirective]:
        """
        Parse robots.txt content into structured directives.
        
        Args:
            content: Robots.txt content to parse
            domain: Domain for context (optional)
            
        Returns:
            List of parsed RobotsDirective objects
        """
        if not content:
            return []
        
        directives = []
        current_user_agent = None
        line_number = 0
        
        try:
            for line in content.split('\n'):
                line_number += 1
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Split on first colon
                if ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'user-agent':
                    current_user_agent = value
                    directives.append(RobotsDirective(
                        user_agent=value,
                        directive_type='user-agent',
                        value=value,
                        line_number=line_number
                    ))
                
                elif key in ['allow', 'disallow']:
                    if current_user_agent:
                        directives.append(RobotsDirective(
                            user_agent=current_user_agent,
                            directive_type=key,
                            path=value,
                            line_number=line_number
                        ))
                
                elif key == 'crawl-delay':
                    if current_user_agent:
                        try:
                            delay_value = float(value)
                            directives.append(RobotsDirective(
                                user_agent=current_user_agent,
                                directive_type='crawl-delay',
                                value=str(delay_value),
                                line_number=line_number
                            ))
                        except ValueError:
                            self.logger.warning(f"Invalid crawl-delay value: {value} (line {line_number})")
                
                elif key == 'sitemap':
                    directives.append(RobotsDirective(
                        user_agent='*',
                        directive_type='sitemap',
                        value=value,
                        line_number=line_number
                    ))
            
            self.logger.info(f"Parsed {len(directives)} directives from robots.txt")
            return directives
            
        except Exception as e:
            self.logger.error(f"Error parsing robots.txt content: {e}")
            return []
    
    def create_crawl_policy(self, directives: List[RobotsDirective], 
                           domain: str, user_agent: str = "*",
                           base_config: Optional[Dict[str, Any]] = None) -> CrawlPolicy:
        """
        Create a crawl policy from robots.txt directives.
        
        Args:
            directives: Parsed robots.txt directives
            domain: Domain for the policy
            user_agent: User agent to match against
            base_config: Base configuration to merge
            
        Returns:
            CrawlPolicy object with appropriate settings
        """
        base_config = base_config or {}
        
        policy = CrawlPolicy(
            domain=domain,
            max_pages=base_config.get("max_pages", 10),
            base_delay=base_config.get("base_delay", 1.0),
            jitter_factor=base_config.get("jitter_factor", 0.3),
            respect_robots=base_config.get("respect_robots", True),
            user_agent=user_agent
        )
        
        if not policy.respect_robots:
            self.logger.info(f"Robots.txt compliance disabled for {domain}")
            return policy
        
        # Find applicable directives for the user agent
        applicable_directives = self._find_applicable_directives(directives, user_agent)
        
        for directive in applicable_directives:
            if directive.directive_type == 'allow' and directive.path:
                policy.allowed_paths.add(directive.path)
            
            elif directive.directive_type == 'disallow' and directive.path:
                policy.disallowed_paths.add(directive.path)
            
            elif directive.directive_type == 'crawl-delay' and directive.value:
                try:
                    policy.robots_delay = float(directive.value)
                except ValueError:
                    pass
            
            elif directive.directive_type == 'sitemap' and directive.value:
                policy.sitemaps.append(directive.value)
        
        self.logger.info(f"Created crawl policy for {domain}: "
                        f"{len(policy.disallowed_paths)} disallowed paths, "
                        f"delay: {policy.robots_delay or policy.base_delay}s")
        
        return policy
    
    def _find_applicable_directives(self, directives: List[RobotsDirective], 
                                   user_agent: str) -> List[RobotsDirective]:
        """Find directives applicable to a specific user agent"""
        applicable = []
        
        # User agents to match (in order of precedence)
        user_agents_to_check = [user_agent, "*"]
        
        for ua in user_agents_to_check:
            ua_directives = [d for d in directives if d.user_agent == ua]
            if ua_directives:
                applicable.extend(ua_directives)
                break  # Use most specific match
        
        # Always include sitemaps (they apply globally)
        sitemaps = [d for d in directives if d.directive_type == 'sitemap']
        applicable.extend(sitemaps)
        
        return applicable
    
    def is_path_allowed(self, path: str, policy: CrawlPolicy) -> bool:
        """
        Check if a path is allowed according to robots.txt policy.
        
        Args:
            path: URL path to check
            policy: CrawlPolicy to check against
            
        Returns:
            True if path is allowed, False if disallowed
        """
        if not policy.respect_robots:
            return True
        
        # Clean the path
        path = path.strip()
        if not path.startswith('/'):
            path = '/' + path
        
        # Check explicit allows first (they override disallows)
        for allowed_pattern in policy.allowed_paths:
            if self._path_matches_pattern(path, allowed_pattern):
                return True
        
        # Check disallows
        for disallowed_pattern in policy.disallowed_paths:
            if self._path_matches_pattern(path, disallowed_pattern):
                return False
        
        # Default to allowed if no matches
        return True
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a robots.txt pattern"""
        if not pattern:
            return False
        
        # Handle wildcard patterns
        if '*' in pattern:
            # Convert robots.txt pattern to regex
            regex_pattern = pattern.replace('*', '.*')
            regex_pattern = '^' + regex_pattern
            try:
                return bool(re.match(regex_pattern, path))
            except re.error:
                # Fallback to simple prefix match
                return path.startswith(pattern.replace('*', ''))
        else:
            # Simple prefix match
            return path.startswith(pattern)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            "default_user_agent": self.default_user_agent,
            "timeout": self.timeout,
            "max_file_size": self.max_file_size
        }


class CrawlPolicyManager:
    """
    Manager for crawl policies and delay enforcement.
    
    Handles policy creation, enforcement of delays, and tracking
    of crawl statistics across domains.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Policy storage
        self.policies: Dict[str, CrawlPolicy] = {}
        
        # Initialize robots parser
        self.robots_parser = RobotsTxtParser(self.config.get("robots_parser", {}))
        
        # Global configuration
        self.global_max_pages = self.config.get("global_max_pages", 50)
        self.global_delay = self.config.get("global_delay", 1.0)
        self.respect_robots_globally = self.config.get("respect_robots", True)
        
        self.logger.info("CrawlPolicyManager initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the manager"""
        logger = logging.getLogger(f"{__name__}.CrawlPolicyManager")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def get_or_create_policy(self, domain: str, user_agent: str = "*",
                           max_pages: Optional[int] = None) -> CrawlPolicy:
        """
        Get existing policy or create new one by fetching robots.txt.
        
        Args:
            domain: Domain to get policy for
            user_agent: User agent for robots.txt matching
            max_pages: Optional override for max pages
            
        Returns:
            CrawlPolicy for the domain
        """
        policy_key = f"{domain}:{user_agent}"
        
        if policy_key in self.policies:
            return self.policies[policy_key]
        
        self.logger.info(f"Creating new crawl policy for {domain}")
        
        # Base configuration
        base_config = {
            "max_pages": max_pages or self.global_max_pages,
            "base_delay": self.global_delay,
            "respect_robots": self.respect_robots_globally
        }
        
        # Fetch and parse robots.txt
        robots_content = None
        directives = []
        
        if self.respect_robots_globally:
            robots_content = self.robots_parser.fetch_robots_txt(domain)
            if robots_content:
                directives = self.robots_parser.parse_robots_txt(robots_content, domain)
        
        # Create policy
        policy = self.robots_parser.create_crawl_policy(
            directives, domain, user_agent, base_config
        )
        
        # Store policy
        self.policies[policy_key] = policy
        
        return policy
    
    def is_crawl_allowed(self, url: str, policy: CrawlPolicy) -> Tuple[bool, str]:
        """
        Check if crawling a URL is allowed by the policy.
        
        Args:
            url: URL to check
            policy: CrawlPolicy to check against
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path or '/'
            
            # Check robots.txt compliance
            if not self.robots_parser.is_path_allowed(path, policy):
                return False, f"Disallowed by robots.txt: {path}"
            
            # Check page limit
            if policy.request_count >= policy.max_pages:
                return False, f"Max pages limit reached: {policy.max_pages}"
            
            return True, "Allowed"
            
        except Exception as e:
            self.logger.error(f"Error checking crawl permission for {url}: {e}")
            return False, f"Error checking permissions: {e}"
    
    def enforce_delay(self, policy: CrawlPolicy) -> float:
        """
        Enforce crawl delay for a policy.
        
        Args:
            policy: CrawlPolicy to enforce delay for
            
        Returns:
            Actual delay time applied
        """
        current_time = time.time()
        
        if policy.last_request_time is not None:
            time_since_last = current_time - policy.last_request_time
            required_delay = policy.effective_delay
            
            if time_since_last < required_delay:
                sleep_time = required_delay - time_since_last
                self.logger.debug(f"Enforcing delay: {sleep_time:.2f}s for {policy.domain}")
                time.sleep(sleep_time)
                policy.last_request_time = time.time()
                return sleep_time
        
        policy.last_request_time = current_time
        return 0.0
    
    def record_request(self, policy: CrawlPolicy, success: bool = True):
        """Record a request against the policy"""
        policy.request_count += 1
        if success:
            self.logger.debug(f"Request recorded for {policy.domain}: {policy.request_count}/{policy.max_pages}")
    
    def get_policy_status(self, domain: str, user_agent: str = "*") -> Dict[str, Any]:
        """Get status information for a domain policy"""
        policy_key = f"{domain}:{user_agent}"
        
        if policy_key not in self.policies:
            return {
                "domain": domain,
                "exists": False,
                "error": "Policy not found"
            }
        
        policy = self.policies[policy_key]
        
        return {
            "domain": domain,
            "exists": True,
            "max_pages": policy.max_pages,
            "requests_made": policy.request_count,
            "requests_remaining": max(0, policy.max_pages - policy.request_count),
            "base_delay": policy.base_delay,
            "robots_delay": policy.robots_delay,
            "effective_delay": policy.effective_delay,
            "respect_robots": policy.respect_robots,
            "disallowed_paths_count": len(policy.disallowed_paths),
            "allowed_paths_count": len(policy.allowed_paths),
            "sitemaps_count": len(policy.sitemaps),
            "last_request_time": policy.last_request_time
        }
    
    def get_all_policies_status(self) -> Dict[str, Any]:
        """Get status for all managed policies"""
        return {
            "total_policies": len(self.policies),
            "global_settings": {
                "global_max_pages": self.global_max_pages,
                "global_delay": self.global_delay,
                "respect_robots_globally": self.respect_robots_globally
            },
            "policies": {
                key: self.get_policy_status(policy.domain, policy.user_agent)
                for key, policy in self.policies.items()
            }
        }


class RobotsComplianceTool(BaseTool):
    """
    Tool for managing robots.txt compliance and crawl policies.
    
    This tool handles robots.txt parsing, policy creation, and crawl
    permission checking for responsible web crawling.
    """
    
    domain: str = Field(
        ...,
        description="Domain to create or check crawl policy for"
    )
    
    user_agent: str = Field(
        "*",
        description="User agent string for robots.txt matching"
    )
    
    max_pages: Optional[int] = Field(
        None,
        description="Maximum pages to crawl for this domain"
    )
    
    check_url: Optional[str] = Field(
        None,
        description="Specific URL to check for crawl permission"
    )
    
    respect_robots: bool = Field(
        True,
        description="Whether to respect robots.txt directives"
    )
    
    base_delay: Optional[float] = Field(
        None,
        description="Base delay between requests in seconds"
    )
    
    operation: str = Field(
        "create_policy",
        description="Operation to perform: 'create_policy', 'check_url', 'get_status'"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.policy_manager = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.RobotsComplianceTool")
        
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
        """Initialize the crawl policy manager"""
        if self.policy_manager is None:
            try:
                config = {
                    "respect_robots": self.respect_robots,
                    "global_delay": self.base_delay or 1.0,
                    "global_max_pages": self.max_pages or 10
                }
                self.policy_manager = CrawlPolicyManager(config)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize policy manager: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the robots compliance operation.
        
        Returns:
            Dictionary containing operation results
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting robots compliance operation: {self.operation} for {self.domain}")
            
            # Initialize manager
            if not self._initialize_manager():
                return {
                    "success": False,
                    "error": "Failed to initialize policy manager",
                    "domain": self.domain
                }
            
            if self.operation == "create_policy":
                return self._create_policy_operation(start_time)
            
            elif self.operation == "check_url":
                return self._check_url_operation(start_time)
            
            elif self.operation == "get_status":
                return self._get_status_operation(start_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {self.operation}",
                    "domain": self.domain,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            self.logger.error(f"Error during robots compliance operation: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _create_policy_operation(self, start_time: float) -> Dict[str, Any]:
        """Create crawl policy operation"""
        try:
            policy = self.policy_manager.get_or_create_policy(
                self.domain, self.user_agent, self.max_pages
            )
            
            policy_status = self.policy_manager.get_policy_status(self.domain, self.user_agent)
            
            return {
                "success": True,
                "operation": "create_policy",
                "domain": self.domain,
                "user_agent": self.user_agent,
                "policy_created": True,
                "policy_details": policy_status,
                "robots_txt_found": len(policy.disallowed_paths) > 0 or len(policy.allowed_paths) > 0,
                "crawl_delay": policy.robots_delay or policy.base_delay,
                "max_pages_allowed": policy.max_pages,
                "sitemaps_found": policy.sitemaps,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "create_policy",
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _check_url_operation(self, start_time: float) -> Dict[str, Any]:
        """Check URL permission operation"""
        if not self.check_url:
            return {
                "success": False,
                "error": "No URL provided for checking",
                "operation": "check_url",
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            policy = self.policy_manager.get_or_create_policy(
                self.domain, self.user_agent, self.max_pages
            )
            
            is_allowed, reason = self.policy_manager.is_crawl_allowed(self.check_url, policy)
            
            return {
                "success": True,
                "operation": "check_url",
                "domain": self.domain,
                "url_checked": self.check_url,
                "is_allowed": is_allowed,
                "reason": reason,
                "requests_made": policy.request_count,
                "requests_remaining": max(0, policy.max_pages - policy.request_count),
                "required_delay": policy.effective_delay,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "check_url",
                "domain": self.domain,
                "url_checked": self.check_url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_status_operation(self, start_time: float) -> Dict[str, Any]:
        """Get policy status operation"""
        try:
            policy_status = self.policy_manager.get_policy_status(self.domain, self.user_agent)
            all_policies = self.policy_manager.get_all_policies_status()
            
            return {
                "success": True,
                "operation": "get_status",
                "domain": self.domain,
                "policy_status": policy_status,
                "manager_status": all_policies,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "get_status",
                "domain": self.domain,
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the robots compliance tool
    print("Testing RobotsComplianceTool...")
    
    # Test policy creation
    tool = RobotsComplianceTool(
        domain="example.com",
        user_agent="SiteCrawler-Bot/1.0",
        max_pages=5,
        operation="create_policy"
    )
    
    result = tool.run()
    print(f"Policy creation result: {result.get('success', False)}")
    
    # Test URL checking
    tool = RobotsComplianceTool(
        domain="example.com",
        check_url="https://example.com/contact",
        operation="check_url"
    )
    
    result = tool.run()
    print(f"URL check result: {result.get('is_allowed', False)}")