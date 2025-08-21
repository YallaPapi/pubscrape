"""
User Agent Manager for Rotation and Anti-Detection

Handles user agent rotation, profile isolation, and resource blocking
to minimize detection during web scraping operations.
"""

import logging
import random
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import time


@dataclass
class UserAgentProfile:
    """Represents a user agent profile with associated settings"""
    user_agent: str
    platform: str
    browser: str
    version: str
    mobile: bool = False
    weight: int = 1  # Higher weight = more likely to be selected


class UserAgentManager:
    """
    Manages user agent rotation and profile isolation for anti-detection
    """
    
    # Modern user agents pool (updated frequently)
    DEFAULT_USER_AGENTS = [
        # Chrome Windows
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Windows",
            "browser": "Chrome",
            "version": "120.0.0.0",
            "weight": 10
        },
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "platform": "Windows",
            "browser": "Chrome", 
            "version": "119.0.0.0",
            "weight": 8
        },
        # Chrome macOS
        {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "macOS",
            "browser": "Chrome",
            "version": "120.0.0.0",
            "weight": 8
        },
        # Firefox Windows
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "platform": "Windows",
            "browser": "Firefox",
            "version": "121.0",
            "weight": 6
        },
        # Edge Windows
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "platform": "Windows",
            "browser": "Edge",
            "version": "120.0.0.0",
            "weight": 5
        },
        # Safari macOS
        {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "platform": "macOS",
            "browser": "Safari",
            "version": "17.2",
            "weight": 5
        },
        # Chrome Linux
        {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Linux",
            "browser": "Chrome",
            "version": "120.0.0.0",
            "weight": 4
        },
        # Mobile Chrome Android
        {
            "user_agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "platform": "Android",
            "browser": "Chrome",
            "version": "120.0.0.0",
            "mobile": True,
            "weight": 3
        },
        # Mobile Safari iOS
        {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "platform": "iOS",
            "browser": "Safari",
            "version": "17.2",
            "mobile": True,
            "weight": 3
        }
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Load user agents
        self.user_agents = self._load_user_agents()
        
        # Track usage for rotation
        self.usage_history: Dict[str, int] = {}
        self.last_used: Dict[str, float] = {}
        
        # Profile isolation settings
        self.profile_base_path = Path(self.config.get("profile_base_path", "browser_profiles"))
        self.profile_base_path.mkdir(exist_ok=True)
        
        self.logger.info(f"Initialized UserAgentManager with {len(self.user_agents)} user agents")
    
    def _load_user_agents(self) -> List[UserAgentProfile]:
        """Load user agents from config or use defaults"""
        custom_agents = self.config.get("custom_user_agents", [])
        
        if custom_agents:
            agents_data = custom_agents
        else:
            agents_data = self.DEFAULT_USER_AGENTS
        
        user_agents = []
        for agent_data in agents_data:
            profile = UserAgentProfile(**agent_data)
            user_agents.append(profile)
        
        return user_agents
    
    def get_user_agent(self, 
                      domain: Optional[str] = None,
                      mobile_preferred: bool = False,
                      platform_preferred: Optional[str] = None) -> UserAgentProfile:
        """
        Get a user agent with rotation logic
        
        Args:
            domain: Domain for domain-specific preferences
            mobile_preferred: Prefer mobile user agents
            platform_preferred: Preferred platform (Windows, macOS, Linux, etc.)
            
        Returns:
            Selected UserAgentProfile
        """
        # Filter candidates based on preferences
        candidates = self.user_agents
        
        if mobile_preferred:
            mobile_agents = [ua for ua in candidates if ua.mobile]
            if mobile_agents:
                candidates = mobile_agents
        
        if platform_preferred:
            platform_agents = [ua for ua in candidates if ua.platform.lower() == platform_preferred.lower()]
            if platform_agents:
                candidates = platform_agents
        
        # Apply domain-specific logic
        if domain:
            domain_agents = self._get_domain_preferred_agents(domain, candidates)
            if domain_agents:
                candidates = domain_agents
        
        # Weight-based random selection with anti-repeat logic
        selected_agent = self._select_with_rotation(candidates)
        
        # Track usage
        agent_key = selected_agent.user_agent
        self.usage_history[agent_key] = self.usage_history.get(agent_key, 0) + 1
        self.last_used[agent_key] = time.time()
        
        self.logger.debug(f"Selected user agent: {selected_agent.browser} {selected_agent.version} "
                         f"on {selected_agent.platform}")
        
        return selected_agent
    
    def _get_domain_preferred_agents(self, 
                                   domain: str, 
                                   candidates: List[UserAgentProfile]) -> List[UserAgentProfile]:
        """Apply domain-specific user agent preferences"""
        domain_lower = domain.lower()
        
        # Domain-specific logic
        if "mobile" in domain_lower or "m." in domain_lower:
            # Prefer mobile agents for mobile sites
            return [ua for ua in candidates if ua.mobile]
        
        if "microsoft" in domain_lower or "office" in domain_lower:
            # Prefer Edge for Microsoft sites
            return [ua for ua in candidates if ua.browser == "Edge"]
        
        if "apple" in domain_lower or "icloud" in domain_lower:
            # Prefer Safari for Apple sites
            return [ua for ua in candidates if ua.browser == "Safari"]
        
        if "google" in domain_lower:
            # Prefer Chrome for Google sites
            return [ua for ua in candidates if ua.browser == "Chrome"]
        
        # Default: no filtering
        return candidates
    
    def _select_with_rotation(self, candidates: List[UserAgentProfile]) -> UserAgentProfile:
        """Select user agent with weighted rotation and anti-repeat logic"""
        current_time = time.time()
        
        # Calculate scores for each candidate
        scored_candidates = []
        for ua in candidates:
            agent_key = ua.user_agent
            
            # Base weight
            score = ua.weight
            
            # Penalize recently used agents
            if agent_key in self.last_used:
                time_since_use = current_time - self.last_used[agent_key]
                if time_since_use < 300:  # 5 minutes penalty
                    score *= 0.1
                elif time_since_use < 1800:  # 30 minutes reduced weight
                    score *= 0.5
            
            # Penalize heavily used agents
            usage_count = self.usage_history.get(agent_key, 0)
            if usage_count > 10:
                score *= 0.7
            
            scored_candidates.append((ua, score))
        
        # Weighted random selection
        total_weight = sum(score for _, score in scored_candidates)
        if total_weight == 0:
            # Fallback: equal probability
            return random.choice(candidates)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for ua, score in scored_candidates:
            cumulative += score
            if r <= cumulative:
                return ua
        
        # Fallback
        return candidates[0]
    
    def get_profile_path(self, session_id: str, domain: Optional[str] = None) -> Path:
        """
        Get isolated profile path for a session
        
        Args:
            session_id: Unique session identifier
            domain: Optional domain for domain-specific profiles
            
        Returns:
            Path to profile directory
        """
        # Create deterministic but isolated profile paths
        if domain:
            # Use domain-specific profiles to maintain consistency
            profile_key = hashlib.md5(f"{domain}_{session_id}".encode()).hexdigest()[:16]
            profile_path = self.profile_base_path / f"domain_{profile_key}"
        else:
            # Session-specific profiles
            profile_key = hashlib.md5(session_id.encode()).hexdigest()[:16]
            profile_path = self.profile_base_path / f"session_{profile_key}"
        
        profile_path.mkdir(exist_ok=True, parents=True)
        return profile_path
    
    def get_resource_blocking_config(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get resource blocking configuration for anti-detection
        
        Args:
            domain: Optional domain for domain-specific blocking rules
            
        Returns:
            Resource blocking configuration
        """
        # Default blocking configuration
        default_config = {
            "block_images": True,
            "block_stylesheets": True,
            "block_fonts": True,
            "block_media": True,
            "block_extensions": [
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
                ".css", ".scss", ".less",
                ".woff", ".woff2", ".ttf", ".otf", ".eot",
                ".mp4", ".mp3", ".avi", ".mov", ".wav",
                ".zip", ".pdf", ".doc", ".docx"
            ],
            "allow_domains": [],  # Domains to never block
            "block_patterns": [
                "*analytics*", "*tracking*", "*ads*", "*facebook.com/tr*",
                "*google-analytics*", "*googletagmanager*", "*doubleclick*"
            ]
        }
        
        # Domain-specific overrides
        if domain:
            domain_config = self._get_domain_blocking_config(domain)
            if domain_config:
                default_config.update(domain_config)
        
        return default_config
    
    def _get_domain_blocking_config(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get domain-specific resource blocking configuration"""
        domain_lower = domain.lower()
        
        # Bing-specific configuration
        if "bing.com" in domain_lower:
            return {
                "block_images": False,  # May need some images for SERP parsing
                "block_stylesheets": False,  # CSS might be needed for layout
                "allow_domains": ["bing.com", "microsoft.com"]
            }
        
        # Social media sites - be more conservative
        if any(social in domain_lower for social in ["facebook", "twitter", "linkedin", "instagram"]):
            return {
                "block_images": False,
                "block_stylesheets": False
            }
        
        # News sites - may need images for content
        if any(news in domain_lower for news in ["cnn", "bbc", "reuters", "bloomberg", "techcrunch"]):
            return {
                "block_images": False
            }
        
        return None
    
    def reset_usage_history(self):
        """Reset usage tracking for fresh rotation"""
        self.usage_history.clear()
        self.last_used.clear()
        self.logger.info("Reset user agent usage history")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about user agent usage"""
        total_requests = sum(self.usage_history.values())
        
        stats = {
            "total_requests": total_requests,
            "unique_agents_used": len(self.usage_history),
            "available_agents": len(self.user_agents),
            "usage_distribution": {}
        }
        
        # Calculate usage percentages
        if total_requests > 0:
            for agent_key, count in self.usage_history.items():
                # Find the agent profile for readable name
                agent_profile = next((ua for ua in self.user_agents if ua.user_agent == agent_key), None)
                if agent_profile:
                    name = f"{agent_profile.browser} {agent_profile.version} ({agent_profile.platform})"
                else:
                    name = agent_key[:50] + "..."
                
                percentage = (count / total_requests) * 100
                stats["usage_distribution"][name] = {
                    "count": count,
                    "percentage": round(percentage, 2)
                }
        
        return stats


# Factory function for easy creation
def create_user_agent_manager(config: Optional[Dict[str, Any]] = None) -> UserAgentManager:
    """
    Factory function to create a UserAgentManager
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured UserAgentManager instance
    """
    return UserAgentManager(config)