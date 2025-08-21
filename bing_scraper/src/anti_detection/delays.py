"""
Human-like Delays for Anti-Detection
Implements natural timing patterns to avoid bot detection.
"""

import time
import random
import logging
from typing import Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DelayConfig:
    """Configuration for delay timing."""
    min_delay: float = 1.0
    max_delay: float = 3.0
    base_multiplier: float = 1.0
    variance: float = 0.3

class HumanLikeDelays:
    """Generates human-like delay patterns for web scraping."""
    
    def __init__(self, settings):
        """Initialize with settings."""
        self.settings = settings
        self.base_delay = settings.base_delay_seconds
        self.request_count = 0
        self.session_start = time.time()
        
        # Delay configurations for different actions
        self.configs = {
            'page_load': DelayConfig(2.0, 5.0, 1.0, 0.4),
            'search': DelayConfig(1.5, 4.0, 1.2, 0.3),
            'navigation': DelayConfig(0.8, 2.5, 1.0, 0.2),
            'extraction': DelayConfig(0.5, 1.5, 0.8, 0.2),
            'typing': DelayConfig(0.1, 0.3, 0.5, 0.1),
        }
        
        logger.info("HumanLikeDelays initialized")
    
    def random_delay(self, action: str = 'navigation') -> float:
        """
        Generate random delay based on action type.
        
        Args:
            action: Type of action ('page_load', 'search', 'navigation', 'extraction', 'typing')
            
        Returns:
            Delay duration in seconds
        """
        config = self.configs.get(action, self.configs['navigation'])
        
        # Base delay with human variance
        base = random.uniform(config.min_delay, config.max_delay)
        
        # Apply base multiplier from settings
        base *= (self.base_delay / 3.0)  # Normalize to base_delay_seconds
        
        # Add random variance
        variance = random.uniform(-config.variance, config.variance)
        delay = base * (1 + variance)
        
        # Ensure minimum delay
        delay = max(delay, 0.1)
        
        # Apply fatigue factor (slower as session progresses)
        fatigue_factor = self._get_fatigue_factor()
        delay *= fatigue_factor
        
        logger.debug(f"Generated {action} delay: {delay:.2f}s")
        time.sleep(delay)
        
        self.request_count += 1
        return delay
    
    def _get_fatigue_factor(self) -> float:
        """Calculate fatigue factor based on session duration and request count."""
        # Increase delays as session progresses (simulates human fatigue)
        session_duration = time.time() - self.session_start
        
        # Base fatigue from session duration (max 50% increase)
        duration_fatigue = min(1.5, 1.0 + (session_duration / 3600) * 0.5)
        
        # Request count fatigue (max 30% increase)
        request_fatigue = min(1.3, 1.0 + (self.request_count / 100) * 0.3)
        
        return duration_fatigue * request_fatigue
    
    def typing_delay(self, text: str) -> float:
        """
        Generate realistic typing delays for text input.
        
        Args:
            text: Text being typed
            
        Returns:
            Total typing duration
        """
        if not text:
            return 0
        
        total_delay = 0
        
        for i, char in enumerate(text):
            # Base typing speed: 60-120 WPM (250-500ms per character)
            base_speed = random.uniform(0.08, 0.16)  # seconds per character
            
            # Adjust for character complexity
            if char.isupper():
                base_speed *= 1.2  # Slower for uppercase
            elif char in '!@#$%^&*()_+-={}[]|\\:";\'<>?,./':
                base_speed *= 1.4  # Slower for special characters
            elif char == ' ':
                base_speed *= 0.8  # Faster for spaces
            
            # Add human variance
            char_delay = base_speed * random.uniform(0.7, 1.5)
            
            # Occasional longer pauses (thinking)
            if random.random() < 0.1:  # 10% chance
                char_delay += random.uniform(0.5, 2.0)
            
            time.sleep(char_delay)
            total_delay += char_delay
        
        logger.debug(f"Typing delay for '{text[:20]}...': {total_delay:.2f}s")
        return total_delay
    
    def page_load_delay(self) -> float:
        """Delay after page load, simulating reading time."""
        return self.random_delay('page_load')
    
    def search_delay(self) -> float:
        """Delay before performing search."""
        return self.random_delay('search')
    
    def extraction_delay(self) -> float:
        """Delay during data extraction."""
        return self.random_delay('extraction')
    
    def retry_delay(self, attempt: int) -> float:
        """
        Exponential backoff delay for retries.
        
        Args:
            attempt: Current retry attempt (1-based)
            
        Returns:
            Delay duration in seconds
        """
        # Exponential backoff with jitter
        base_delay = min(60, 2 ** attempt)  # Cap at 60 seconds
        jitter = random.uniform(0.8, 1.2)
        delay = base_delay * jitter
        
        logger.info(f"Retry delay (attempt {attempt}): {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def rate_limit_delay(self) -> float:
        """Delay when rate limit is detected."""
        # Longer delay to respect rate limits
        delay = random.uniform(30, 90)  # 30-90 seconds
        logger.warning(f"Rate limit delay: {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def session_break_delay(self) -> float:
        """Longer delay simulating session break."""
        delay = random.uniform(300, 900)  # 5-15 minutes
        logger.info(f"Session break delay: {delay:.2f}s")
        time.sleep(delay)
        return delay
    
    def smart_delay(self, response_time: Optional[float] = None, 
                   status_code: Optional[int] = None) -> float:
        """
        Smart delay based on server response characteristics.
        
        Args:
            response_time: Server response time in seconds
            status_code: HTTP status code
            
        Returns:
            Calculated delay duration
        """
        base_delay = self.base_delay
        
        # Adjust based on response time
        if response_time:
            if response_time > 5.0:
                # Server is slow, be more gentle
                base_delay *= 1.5
            elif response_time < 0.5:
                # Server is fast, can be more aggressive
                base_delay *= 0.8
        
        # Adjust based on status code
        if status_code:
            if status_code == 429:  # Rate limited
                return self.rate_limit_delay()
            elif status_code >= 500:  # Server error
                base_delay *= 2.0
            elif status_code == 403:  # Forbidden
                base_delay *= 1.8
        
        # Apply variance
        delay = base_delay * random.uniform(0.7, 1.4)
        
        logger.debug(f"Smart delay: {delay:.2f}s (response: {response_time}, status: {status_code})")
        time.sleep(delay)
        return delay
    
    def get_burst_pattern(self, count: int) -> List[float]:
        """
        Generate burst pattern delays for multiple requests.
        
        Args:
            count: Number of requests in burst
            
        Returns:
            List of delay durations
        """
        delays = []
        
        for i in range(count):
            if i == 0:
                # First request: normal delay
                delay = self.random_delay('navigation')
            elif i < count // 2:
                # Ramp up: shorter delays
                delay = self.random_delay('extraction') * 0.7
            else:
                # Cool down: longer delays
                delay = self.random_delay('navigation') * 1.3
            
            delays.append(delay)
        
        return delays
    
    def get_session_stats(self) -> dict:
        """Get session delay statistics."""
        session_duration = time.time() - self.session_start
        avg_delay = session_duration / max(1, self.request_count)
        
        return {
            'session_duration': session_duration,
            'total_requests': self.request_count,
            'average_delay': avg_delay,
            'fatigue_factor': self._get_fatigue_factor(),
            'base_delay_setting': self.base_delay
        }