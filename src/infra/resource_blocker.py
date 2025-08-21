"""
Resource Blocker for Anti-Detection and Performance

Handles resource blocking to reduce detection fingerprints and improve
performance by blocking unnecessary resources like images, CSS, fonts, etc.
"""

import logging
import re
from typing import List, Dict, Any, Set, Optional, Pattern
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class BlockingRule:
    """Represents a resource blocking rule"""
    pattern: str
    rule_type: str  # 'extension', 'domain', 'regex', 'keyword'
    block: bool = True  # True to block, False to allow
    priority: int = 0  # Higher priority rules take precedence


class ResourceBlocker:
    """
    Manages resource blocking for anti-detection and performance optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Compile blocking rules
        self.blocking_rules = self._compile_blocking_rules()
        
        # Statistics tracking
        self.blocked_count = 0
        self.allowed_count = 0
        self.blocked_types: Dict[str, int] = {}
        
        self.logger.info(f"Initialized ResourceBlocker with {len(self.blocking_rules)} rules")
    
    def _compile_blocking_rules(self) -> List[BlockingRule]:
        """Compile blocking rules from configuration"""
        rules = []
        
        # Default blocking patterns
        default_rules = [
            # Image files
            {"pattern": r"\.(png|jpg|jpeg|gif|webp|svg|ico|bmp)(\?.*)?$", "rule_type": "regex", "block": True, "priority": 10},
            
            # Stylesheets
            {"pattern": r"\.(css|scss|less)(\?.*)?$", "rule_type": "regex", "block": True, "priority": 10},
            
            # Fonts
            {"pattern": r"\.(woff|woff2|ttf|otf|eot)(\?.*)?$", "rule_type": "regex", "block": True, "priority": 10},
            
            # Media files
            {"pattern": r"\.(mp4|mp3|avi|mov|wav|ogg|webm)(\?.*)?$", "rule_type": "regex", "block": True, "priority": 10},
            
            # Documents
            {"pattern": r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar)(\?.*)?$", "rule_type": "regex", "block": True, "priority": 5},
            
            # Analytics and tracking
            {"pattern": "google-analytics", "rule_type": "keyword", "block": True, "priority": 15},
            {"pattern": "googletagmanager", "rule_type": "keyword", "block": True, "priority": 15},
            {"pattern": "doubleclick", "rule_type": "keyword", "block": True, "priority": 15},
            {"pattern": "facebook.com/tr", "rule_type": "keyword", "block": True, "priority": 15},
            {"pattern": "analytics", "rule_type": "keyword", "block": True, "priority": 12},
            {"pattern": "tracking", "rule_type": "keyword", "block": True, "priority": 12},
            {"pattern": "ads", "rule_type": "keyword", "block": True, "priority": 12},
            
            # Ad networks
            {"pattern": "googlesyndication", "rule_type": "keyword", "block": True, "priority": 15},
            {"pattern": "adsystem", "rule_type": "keyword", "block": True, "priority": 15},
            {"pattern": "amazon-adsystem", "rule_type": "keyword", "block": True, "priority": 15},
            
            # Social media widgets
            {"pattern": "facebook.com/plugins", "rule_type": "keyword", "block": True, "priority": 12},
            {"pattern": "platform.twitter.com", "rule_type": "keyword", "block": True, "priority": 12},
            {"pattern": "linkedin.com/embed", "rule_type": "keyword", "block": True, "priority": 12},
        ]
        
        # Add custom rules from config
        custom_rules = self.config.get("custom_blocking_rules", [])
        all_rules_data = default_rules + custom_rules
        
        # Convert to BlockingRule objects
        for rule_data in all_rules_data:
            rule = BlockingRule(**rule_data)
            rules.append(rule)
        
        # Sort by priority (higher priority first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        return rules
    
    def should_block_resource(self, url: str, resource_type: Optional[str] = None) -> bool:
        """
        Determine if a resource should be blocked
        
        Args:
            url: Resource URL to check
            resource_type: Optional resource type hint (image, stylesheet, etc.)
            
        Returns:
            True if resource should be blocked, False otherwise
        """
        # Apply blocking rules in priority order
        for rule in self.blocking_rules:
            if self._matches_rule(url, rule):
                if rule.block:
                    self._record_block(url, resource_type, rule.pattern)
                    return True
                else:
                    self._record_allow(url, resource_type, rule.pattern)
                    return False
        
        # Default: allow if no rules match
        self._record_allow(url, resource_type, "default")
        return False
    
    def _matches_rule(self, url: str, rule: BlockingRule) -> bool:
        """Check if URL matches a blocking rule"""
        try:
            if rule.rule_type == "extension":
                return url.lower().endswith(rule.pattern.lower())
            
            elif rule.rule_type == "domain":
                parsed_url = urlparse(url)
                return rule.pattern.lower() in parsed_url.netloc.lower()
            
            elif rule.rule_type == "regex":
                return bool(re.search(rule.pattern, url, re.IGNORECASE))
            
            elif rule.rule_type == "keyword":
                return rule.pattern.lower() in url.lower()
            
            else:
                self.logger.warning(f"Unknown rule type: {rule.rule_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error matching rule {rule.pattern}: {e}")
            return False
    
    def _record_block(self, url: str, resource_type: Optional[str], rule_pattern: str):
        """Record a blocked resource for statistics"""
        self.blocked_count += 1
        
        # Determine resource type if not provided
        if not resource_type:
            resource_type = self._guess_resource_type(url)
        
        self.blocked_types[resource_type] = self.blocked_types.get(resource_type, 0) + 1
        
        self.logger.debug(f"Blocked {resource_type}: {url[:100]} (rule: {rule_pattern})")
    
    def _record_allow(self, url: str, resource_type: Optional[str], rule_pattern: str):
        """Record an allowed resource for statistics"""
        self.allowed_count += 1
        
        if not resource_type:
            resource_type = self._guess_resource_type(url)
        
        self.logger.debug(f"Allowed {resource_type}: {url[:100]} (rule: {rule_pattern})")
    
    def _guess_resource_type(self, url: str) -> str:
        """Guess resource type from URL"""
        url_lower = url.lower()
        
        # Images
        if any(ext in url_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico']):
            return "image"
        
        # Stylesheets
        if any(ext in url_lower for ext in ['.css', '.scss', '.less']):
            return "stylesheet"
        
        # JavaScript
        if '.js' in url_lower:
            return "script"
        
        # Fonts
        if any(ext in url_lower for ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']):
            return "font"
        
        # Media
        if any(ext in url_lower for ext in ['.mp4', '.mp3', '.avi', '.mov', '.wav']):
            return "media"
        
        # Documents
        if any(ext in url_lower for ext in ['.pdf', '.doc', '.zip']):
            return "document"
        
        # Analytics/tracking patterns
        if any(pattern in url_lower for pattern in ['analytics', 'tracking', 'ads']):
            return "tracking"
        
        return "other"
    
    def get_chrome_resource_blocking_config(self) -> Dict[str, Any]:
        """
        Get Chrome-specific resource blocking configuration
        
        Returns:
            Dictionary suitable for Chrome options
        """
        prefs = {}
        
        # Block images if configured
        if self._should_block_type("image"):
            prefs["profile.managed_default_content_settings.images"] = 2
        
        # Block notifications
        prefs["profile.default_content_setting_values.notifications"] = 2
        
        # Block popups
        prefs["profile.default_content_settings.popups"] = 0
        
        # Block media stream
        prefs["profile.managed_default_content_settings.media_stream"] = 2
        
        # Block plugins
        prefs["profile.default_content_setting_values.plugins"] = 2
        
        # Block automatic downloads
        prefs["profile.default_content_setting_values.automatic_downloads"] = 2
        
        return prefs
    
    def _should_block_type(self, resource_type: str) -> bool:
        """Check if a resource type should be blocked based on configuration"""
        block_config = self.config.get("block_types", {})
        
        type_mapping = {
            "image": block_config.get("images", True),
            "stylesheet": block_config.get("stylesheets", True),
            "font": block_config.get("fonts", True),
            "media": block_config.get("media", True),
            "tracking": block_config.get("tracking", True)
        }
        
        return type_mapping.get(resource_type, False)
    
    def get_request_interception_patterns(self) -> List[str]:
        """
        Get patterns for request interception in browsers
        
        Returns:
            List of URL patterns to intercept
        """
        patterns = []
        
        for rule in self.blocking_rules:
            if rule.block and rule.rule_type == "regex":
                patterns.append(rule.pattern)
        
        return patterns
    
    def create_domain_specific_blocker(self, domain: str) -> 'ResourceBlocker':
        """
        Create a domain-specific resource blocker with custom rules
        
        Args:
            domain: Domain to create specific rules for
            
        Returns:
            New ResourceBlocker instance with domain-specific configuration
        """
        domain_config = self.config.copy()
        
        # Apply domain-specific overrides
        domain_overrides = self._get_domain_overrides(domain)
        if domain_overrides:
            domain_config.update(domain_overrides)
        
        return ResourceBlocker(domain_config)
    
    def _get_domain_overrides(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get domain-specific blocking overrides"""
        domain_lower = domain.lower()
        
        # Bing.com - be more conservative
        if "bing.com" in domain_lower:
            return {
                "block_types": {
                    "images": False,  # May need for SERP thumbnails
                    "stylesheets": False,  # Need for proper layout
                    "fonts": True,
                    "media": True,
                    "tracking": True
                }
            }
        
        # Social media - keep some resources
        if any(social in domain_lower for social in ["facebook", "twitter", "linkedin", "instagram"]):
            return {
                "block_types": {
                    "images": False,
                    "stylesheets": False,
                    "fonts": False,
                    "media": True,
                    "tracking": True
                }
            }
        
        # News sites - may need images
        if any(news in domain_lower for news in ["cnn", "bbc", "reuters", "bloomberg"]):
            return {
                "block_types": {
                    "images": False,
                    "stylesheets": True,
                    "fonts": True,
                    "media": True,
                    "tracking": True
                }
            }
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get blocking statistics"""
        total_requests = self.blocked_count + self.allowed_count
        
        stats = {
            "total_requests": total_requests,
            "blocked_count": self.blocked_count,
            "allowed_count": self.allowed_count,
            "block_percentage": round((self.blocked_count / total_requests * 100), 2) if total_requests > 0 else 0,
            "blocked_by_type": self.blocked_types.copy(),
            "active_rules": len(self.blocking_rules)
        }
        
        return stats
    
    def reset_statistics(self):
        """Reset blocking statistics"""
        self.blocked_count = 0
        self.allowed_count = 0
        self.blocked_types.clear()
        self.logger.info("Reset resource blocking statistics")


# Factory function for easy creation
def create_resource_blocker(
    block_images: bool = True,
    block_stylesheets: bool = True,
    block_fonts: bool = True,
    block_media: bool = True,
    block_tracking: bool = True,
    custom_rules: Optional[List[Dict[str, Any]]] = None
) -> ResourceBlocker:
    """
    Factory function to create a ResourceBlocker with common configurations
    
    Args:
        block_images: Whether to block image resources
        block_stylesheets: Whether to block CSS resources
        block_fonts: Whether to block font resources
        block_media: Whether to block media files
        block_tracking: Whether to block tracking/analytics
        custom_rules: Additional custom blocking rules
        
    Returns:
        Configured ResourceBlocker instance
    """
    config = {
        "block_types": {
            "images": block_images,
            "stylesheets": block_stylesheets,
            "fonts": block_fonts,
            "media": block_media,
            "tracking": block_tracking
        },
        "custom_blocking_rules": custom_rules or []
    }
    
    return ResourceBlocker(config)