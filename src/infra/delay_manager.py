"""
Delay Manager for Human-like Behavior Simulation

Implements configurable human-like delays, including base delays with jitter
and micro-delays for individual actions to mimic real user behavior and avoid detection.
"""

import logging
import time
import random
import math
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Types of actions that can have delays"""
    PAGE_LOAD = "page_load"
    SEARCH_QUERY = "search_query"
    CLICK = "click"
    SCROLL = "scroll"
    TYPE = "type"
    HOVER = "hover"
    NAVIGATION = "navigation"
    FORM_SUBMIT = "form_submit"
    API_REQUEST = "api_request"


@dataclass
class DelayConfig:
    """Configuration for delay timing"""
    base_ms: int = 800  # Base delay in milliseconds
    jitter_ms: int = 400  # Maximum jitter to add/subtract
    min_ms: int = 200  # Minimum delay
    max_ms: int = 3000  # Maximum delay
    distribution: str = "normal"  # normal, uniform, exponential
    
    # Action-specific multipliers
    action_multipliers: Dict[ActionType, float] = None
    
    def __post_init__(self):
        if self.action_multipliers is None:
            self.action_multipliers = {
                ActionType.PAGE_LOAD: 2.0,      # Longer delays for page loads
                ActionType.SEARCH_QUERY: 1.5,   # Moderate delay for searches
                ActionType.CLICK: 1.0,          # Standard delay for clicks
                ActionType.SCROLL: 0.5,         # Shorter delays for scrolling
                ActionType.TYPE: 0.3,           # Quick delays for typing
                ActionType.HOVER: 0.8,          # Moderate delay for hover
                ActionType.NAVIGATION: 1.2,     # Slightly longer for navigation
                ActionType.FORM_SUBMIT: 1.8,    # Longer delay before submitting
                ActionType.API_REQUEST: 1.0     # Standard for API requests
            }


class DelayManager:
    """
    Manages human-like delays for anti-detection
    """
    
    def __init__(self, config: Optional[DelayConfig] = None):
        self.config = config or DelayConfig()
        self.logger = logging.getLogger(__name__)
        
        # Tracking for adaptive delays
        self.action_history: List[Dict[str, Any]] = []
        self.last_action_time = 0
        self.session_start_time = time.time()
        
        # Adaptive behavior settings
        self.adaptive_enabled = True
        self.speed_variation_factor = 1.0  # Can be adjusted based on session behavior
        
        self.logger.info(f"Initialized DelayManager with base delay {self.config.base_ms}ms")
    
    def delay(self, 
              action_type: ActionType, 
              context: Optional[Dict[str, Any]] = None) -> float:
        """
        Execute a delay for the specified action type
        
        Args:
            action_type: Type of action being performed
            context: Optional context for adaptive behavior
            
        Returns:
            Actual delay time in seconds
        """
        delay_ms = self.calculate_delay(action_type, context)
        delay_seconds = delay_ms / 1000.0
        
        # Record action for history
        self._record_action(action_type, delay_ms, context)
        
        # Execute the delay
        time.sleep(delay_seconds)
        
        self.logger.debug(f"Delayed {delay_ms}ms for {action_type.value}")
        
        return delay_seconds
    
    def calculate_delay(self, 
                       action_type: ActionType, 
                       context: Optional[Dict[str, Any]] = None) -> int:
        """
        Calculate delay time without executing it
        
        Args:
            action_type: Type of action being performed
            context: Optional context for adaptive behavior
            
        Returns:
            Delay time in milliseconds
        """
        # Base delay with action multiplier
        base_delay = self.config.base_ms * self.config.action_multipliers.get(action_type, 1.0)
        
        # Apply jitter based on distribution
        jittered_delay = self._apply_jitter(base_delay)
        
        # Apply adaptive adjustments
        if self.adaptive_enabled:
            jittered_delay = self._apply_adaptive_adjustments(jittered_delay, action_type, context)
        
        # Apply session-based variations
        jittered_delay = self._apply_session_variations(jittered_delay)
        
        # Ensure within bounds
        final_delay = max(self.config.min_ms, min(self.config.max_ms, jittered_delay))
        
        return int(final_delay)
    
    def _apply_jitter(self, base_delay: float) -> float:
        """Apply jitter to base delay based on distribution"""
        if self.config.distribution == "normal":
            # Normal distribution with base_delay as mean
            jitter = random.normalvariate(0, self.config.jitter_ms / 3)  # 3-sigma rule
            return base_delay + jitter
        
        elif self.config.distribution == "uniform":
            # Uniform distribution
            jitter = random.uniform(-self.config.jitter_ms, self.config.jitter_ms)
            return base_delay + jitter
        
        elif self.config.distribution == "exponential":
            # Exponential distribution (more realistic for human behavior)
            # Use exponential for additional delay beyond base
            extra_delay = random.expovariate(1.0 / (self.config.jitter_ms / 2))
            return base_delay + extra_delay
        
        else:
            # Default: normal distribution
            jitter = random.normalvariate(0, self.config.jitter_ms / 3)
            return base_delay + jitter
    
    def _apply_adaptive_adjustments(self, 
                                  delay: float, 
                                  action_type: ActionType, 
                                  context: Optional[Dict[str, Any]]) -> float:
        """Apply adaptive adjustments based on session behavior and context"""
        adjusted_delay = delay
        
        # Time of day adjustments (simulate user energy levels)
        hour = time.localtime().tm_hour
        if 9 <= hour <= 17:  # Work hours - faster
            adjusted_delay *= 0.9
        elif 22 <= hour or hour <= 6:  # Late night/early morning - slower
            adjusted_delay *= 1.3
        
        # Frequency-based adjustments
        recent_actions = self._get_recent_actions(action_type, 60)  # Last minute
        if len(recent_actions) > 5:  # High frequency - slightly faster
            adjusted_delay *= 0.85
        elif len(recent_actions) == 0:  # First action - slower (thinking)
            adjusted_delay *= 1.4
        
        # Context-based adjustments
        if context:
            # Page complexity
            if context.get("page_complexity") == "high":
                adjusted_delay *= 1.2
            elif context.get("page_complexity") == "low":
                adjusted_delay *= 0.9
            
            # Error state - slower reactions
            if context.get("previous_error"):
                adjusted_delay *= 1.5
            
            # Success state - confidence boost
            if context.get("previous_success"):
                adjusted_delay *= 0.95
            
            # Target found - excitement/urgency
            if context.get("target_found"):
                adjusted_delay *= 0.8
        
        return adjusted_delay
    
    def _apply_session_variations(self, delay: float) -> float:
        """Apply session-wide variations to simulate user behavior patterns"""
        # Session duration effects
        session_minutes = (time.time() - self.session_start_time) / 60
        
        if session_minutes > 30:  # Fatigue after 30 minutes
            delay *= 1.1 + (session_minutes - 30) * 0.01  # Gradual slowdown
        
        # Speed variation factor (can be set based on "user personality")
        delay *= self.speed_variation_factor
        
        # Random micro-variations to avoid patterns
        micro_variation = random.uniform(0.95, 1.05)
        delay *= micro_variation
        
        return delay
    
    def _record_action(self, 
                      action_type: ActionType, 
                      delay_ms: int, 
                      context: Optional[Dict[str, Any]]):
        """Record action in history for adaptive behavior"""
        current_time = time.time()
        
        action_record = {
            "action_type": action_type,
            "delay_ms": delay_ms,
            "timestamp": current_time,
            "context": context or {}
        }
        
        self.action_history.append(action_record)
        
        # Keep only recent history (last hour)
        cutoff_time = current_time - 3600
        self.action_history = [a for a in self.action_history if a["timestamp"] > cutoff_time]
        
        self.last_action_time = current_time
    
    def _get_recent_actions(self, action_type: ActionType, seconds: int) -> List[Dict[str, Any]]:
        """Get recent actions of a specific type"""
        cutoff_time = time.time() - seconds
        return [
            action for action in self.action_history
            if action["action_type"] == action_type and action["timestamp"] > cutoff_time
        ]
    
    def create_typing_delays(self, text: str) -> List[float]:
        """
        Create realistic typing delays for a string of text
        
        Args:
            text: Text to be typed
            
        Returns:
            List of delays between each character (in seconds)
        """
        delays = []
        
        for i, char in enumerate(text):
            # Base typing delay
            base_delay = 80  # Base 80ms between characters
            
            # Character-specific adjustments
            if char == ' ':
                base_delay *= 0.7  # Spaces are quick
            elif char in '.,!?;:':
                base_delay *= 1.5  # Punctuation requires thought
            elif char.isupper() and i > 0 and text[i-1].islower():
                base_delay *= 1.3  # Shift key for capitals
            elif char.isdigit():
                base_delay *= 1.2  # Numbers slightly slower
            
            # Position-based adjustments
            if i == 0:
                base_delay *= 2.0  # First character takes longer
            elif i == len(text) - 1:
                base_delay *= 1.5  # Last character (thinking before submit)
            
            # Add realistic jitter
            jitter = random.normalvariate(0, base_delay * 0.3)
            final_delay = max(20, base_delay + jitter)  # Minimum 20ms
            
            delays.append(final_delay / 1000.0)  # Convert to seconds
        
        return delays
    
    def type_text_with_delays(self, 
                             text: str, 
                             type_function: Callable[[str], None],
                             char_by_char: bool = True) -> float:
        """
        Type text with realistic delays
        
        Args:
            text: Text to type
            type_function: Function to call for typing each character/word
            char_by_char: Whether to type character by character or word by word
            
        Returns:
            Total time taken for typing
        """
        start_time = time.time()
        
        if char_by_char:
            delays = self.create_typing_delays(text)
            for i, char in enumerate(text):
                type_function(char)
                if i < len(delays):
                    time.sleep(delays[i])
        else:
            # Word-by-word typing
            words = text.split(' ')
            for i, word in enumerate(words):
                type_function(word)
                if i < len(words) - 1:  # Don't delay after last word
                    # Delay between words
                    word_delay = random.uniform(0.1, 0.3)
                    time.sleep(word_delay)
                    type_function(' ')  # Type the space
        
        total_time = time.time() - start_time
        return total_time
    
    def mouse_movement_delay(self, distance_pixels: float) -> float:
        """
        Calculate delay for mouse movement based on distance
        
        Args:
            distance_pixels: Distance the mouse needs to travel
            
        Returns:
            Delay in seconds
        """
        # Fitts' Law approximation: time = a + b * log2(distance/width + 1)
        # Where a and b are constants, width is target width
        
        a = 0.05  # Base movement time
        b = 0.02  # Distance factor
        target_width = 20  # Assume 20px target width
        
        if distance_pixels <= 0:
            return 0
        
        movement_time = a + b * math.log2(distance_pixels / target_width + 1)
        
        # Add some jitter
        jitter = random.uniform(-0.01, 0.02)
        final_time = max(0.01, movement_time + jitter)
        
        return final_time
    
    def set_speed_personality(self, personality: str):
        """
        Set the speed personality for the session
        
        Args:
            personality: "fast", "normal", "slow", "variable"
        """
        if personality == "fast":
            self.speed_variation_factor = 0.7
        elif personality == "slow":
            self.speed_variation_factor = 1.4
        elif personality == "variable":
            self.speed_variation_factor = random.uniform(0.8, 1.3)
        else:  # normal
            self.speed_variation_factor = 1.0
        
        self.logger.info(f"Set speed personality to {personality} (factor: {self.speed_variation_factor:.2f})")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get delay statistics for the session"""
        if not self.action_history:
            return {"total_actions": 0}
        
        delays = [action["delay_ms"] for action in self.action_history]
        action_types = [action["action_type"].value for action in self.action_history]
        
        # Calculate statistics
        stats = {
            "total_actions": len(self.action_history),
            "session_duration_minutes": (time.time() - self.session_start_time) / 60,
            "average_delay_ms": sum(delays) / len(delays),
            "min_delay_ms": min(delays),
            "max_delay_ms": max(delays),
            "total_delay_seconds": sum(delays) / 1000,
            "actions_by_type": {}
        }
        
        # Action type breakdown
        for action_type in ActionType:
            type_actions = [d for d, t in zip(delays, action_types) if t == action_type.value]
            if type_actions:
                stats["actions_by_type"][action_type.value] = {
                    "count": len(type_actions),
                    "average_delay_ms": sum(type_actions) / len(type_actions)
                }
        
        return stats


# Factory function for easy creation
def create_delay_manager(
    base_ms: int = 800,
    jitter_ms: int = 400,
    distribution: str = "normal",
    personality: str = "normal"
) -> DelayManager:
    """
    Factory function to create a DelayManager with common configurations
    
    Args:
        base_ms: Base delay in milliseconds
        jitter_ms: Maximum jitter to add/subtract
        distribution: Delay distribution ("normal", "uniform", "exponential")
        personality: Speed personality ("fast", "normal", "slow", "variable")
        
    Returns:
        Configured DelayManager instance
    """
    config = DelayConfig(
        base_ms=base_ms,
        jitter_ms=jitter_ms,
        distribution=distribution
    )
    
    delay_manager = DelayManager(config)
    delay_manager.set_speed_personality(personality)
    
    return delay_manager