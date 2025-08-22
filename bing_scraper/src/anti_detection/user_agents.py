"""
User Agent Rotation for Anti-Detection
Provides realistic user agent strings for browser fingerprinting protection.
"""

import random
import logging
from typing import List

logger = logging.getLogger(__name__)

class UserAgentRotator:
    """Manages rotation of realistic user agent strings."""
    
    def __init__(self):
        """Initialize with comprehensive user agent database."""
        self.user_agents = self._load_user_agents()
        self.current_index = 0
        logger.info(f"UserAgentRotator initialized with {len(self.user_agents)} user agents")
    
    def _load_user_agents(self) -> List[str]:
        """Load realistic user agent strings with latest versions and enterprise patterns."""
        return [
            # Latest Chrome on Windows 10/11 (most common)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Chrome with specific Windows versions (professional environments)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            
            # Chrome on macOS (M1/M2 and Intel)
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; arm64 Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            
            # Chrome on Linux (popular distributions)
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            
            # Latest Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.0; rv:122.0) Gecko/20100101 Firefox/122.0",
            
            # Firefox on Linux
            "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
            
            # Latest Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            
            # Latest Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            
            # Business/Professional user agents (higher trust, enterprise environments)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.6.3271.50",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/1.62.165",
            
            # Corporate Chrome with company extensions/modifications
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Corporate/22.2.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Enterprise/21.12.5",
            
            # Slightly older but still common browsers (for variety)
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            
            # Regional variations
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (compatible; en-US)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 (compatible; en-CA)",
            
            # Chrome on Android (mobile - less suspicious for some queries)
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            
            # Safari on iOS (latest)
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        user_agent = random.choice(self.user_agents)
        logger.debug(f"Selected user agent: {user_agent[:50]}...")
        return user_agent
    
    def get_next_user_agent(self) -> str:
        """Get next user agent in rotation sequence."""
        user_agent = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        logger.debug(f"Rotated to user agent: {user_agent[:50]}...")
        return user_agent
    
    def get_chrome_user_agents(self) -> List[str]:
        """Get only Chrome user agents."""
        return [ua for ua in self.user_agents if 'Chrome/' in ua and 'Edg/' not in ua]
    
    def get_firefox_user_agents(self) -> List[str]:
        """Get only Firefox user agents."""
        return [ua for ua in self.user_agents if 'Firefox/' in ua]
    
    def get_desktop_user_agents(self) -> List[str]:
        """Get only desktop user agents."""
        mobile_indicators = ['Mobile', 'Android', 'iPhone', 'iPad']
        return [ua for ua in self.user_agents 
                if not any(indicator in ua for indicator in mobile_indicators)]
    
    def get_mobile_user_agents(self) -> List[str]:
        """Get only mobile user agents."""
        mobile_indicators = ['Mobile', 'Android', 'iPhone', 'iPad']
        return [ua for ua in self.user_agents 
                if any(indicator in ua for indicator in mobile_indicators)]
    
    def get_windows_user_agents(self) -> List[str]:
        """Get user agents for Windows systems."""
        return [ua for ua in self.user_agents if 'Windows NT' in ua]
    
    def get_macos_user_agents(self) -> List[str]:
        """Get user agents for macOS systems."""
        return [ua for ua in self.user_agents if 'Macintosh' in ua or 'Mac OS X' in ua]
    
    def get_linux_user_agents(self) -> List[str]:
        """Get user agents for Linux systems."""
        return [ua for ua in self.user_agents if 'Linux' in ua and 'Android' not in ua]
    
    def get_user_agent_by_browser(self, browser: str) -> str:
        """
        Get random user agent for specific browser.
        
        Args:
            browser: Browser name ('chrome', 'firefox', 'safari', 'edge')
            
        Returns:
            Random user agent string for specified browser
        """
        browser = browser.lower()
        
        if browser == 'chrome':
            candidates = self.get_chrome_user_agents()
        elif browser == 'firefox':
            candidates = self.get_firefox_user_agents()
        elif browser == 'safari':
            candidates = [ua for ua in self.user_agents if 'Safari/' in ua and 'Chrome/' not in ua]
        elif browser == 'edge':
            candidates = [ua for ua in self.user_agents if 'Edg/' in ua]
        else:
            candidates = self.user_agents
        
        return random.choice(candidates) if candidates else self.get_random_user_agent()
    
    def add_custom_user_agent(self, user_agent: str) -> None:
        """Add custom user agent to rotation pool."""
        if user_agent not in self.user_agents:
            self.user_agents.append(user_agent)
            logger.info(f"Added custom user agent: {user_agent[:50]}...")
    
    def get_stats(self) -> dict:
        """Get user agent statistics."""
        total = len(self.user_agents)
        chrome_count = len(self.get_chrome_user_agents())
        firefox_count = len(self.get_firefox_user_agents())
        desktop_count = len(self.get_desktop_user_agents())
        mobile_count = len(self.get_mobile_user_agents())
        
        return {
            'total_user_agents': total,
            'chrome_agents': chrome_count,
            'firefox_agents': firefox_count,
            'desktop_agents': desktop_count,
            'mobile_agents': mobile_count,
            'current_index': self.current_index
        }