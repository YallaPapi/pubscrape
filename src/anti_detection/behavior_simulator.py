"""
Human Behavior Simulation Engine

Simulates realistic human browsing patterns including mouse movements,
scrolling behaviors, typing patterns, and reading pauses to evade
bot detection systems.
"""

import logging
import time
import random
import asyncio
import math
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class BehaviorType(Enum):
    """Types of human behaviors to simulate"""
    MOUSE_MOVEMENT = "mouse_movement"
    SCROLLING = "scrolling"
    CLICKING = "clicking"
    TYPING = "typing"
    READING = "reading"
    NAVIGATION = "navigation"
    IDLE = "idle"


class IntensityLevel(Enum):
    """Intensity levels for behavior simulation"""
    MINIMAL = "minimal"      # Basic delays only
    LOW = "low"             # Simple movements
    MEDIUM = "medium"       # Realistic patterns
    HIGH = "high"           # Complex human-like behavior
    MAXIMUM = "maximum"     # Full simulation with variance


@dataclass
class MousePosition:
    """Mouse cursor position"""
    x: int
    y: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class BehaviorConfig:
    """Configuration for behavior simulation"""
    # Overall settings
    intensity: IntensityLevel = IntensityLevel.MEDIUM
    variability_factor: float = 0.3  # 0.0 = no variance, 1.0 = high variance
    
    # Mouse behavior
    enable_mouse_movements: bool = True
    mouse_speed_range: Tuple[int, int] = (100, 300)  # pixels per second
    mouse_path_curvature: float = 0.2  # 0.0 = straight, 1.0 = very curved
    random_mouse_movements: bool = True
    mouse_idle_movements: bool = True
    
    # Scrolling behavior
    enable_scrolling: bool = True
    scroll_speed_range: Tuple[int, int] = (200, 800)  # pixels
    scroll_pause_range: Tuple[float, float] = (0.1, 0.5)  # seconds
    natural_scroll_patterns: bool = True
    read_scroll_behavior: bool = True
    
    # Clicking behavior
    enable_clicking: bool = True
    click_delay_range: Tuple[float, float] = (0.05, 0.2)
    double_click_probability: float = 0.1
    right_click_probability: float = 0.05
    
    # Typing behavior
    enable_typing: bool = True
    typing_speed_range: Tuple[int, int] = (40, 120)  # WPM
    typing_error_rate: float = 0.02
    backspace_correction_probability: float = 0.8
    typing_pause_probability: float = 0.1
    
    # Reading and pauses
    enable_reading_pauses: bool = True
    reading_speed_wpm: int = 200
    content_scan_time: float = 2.0
    focus_attention_span: Tuple[float, float] = (5.0, 30.0)  # seconds
    
    # Navigation behavior
    enable_navigation_delays: bool = True
    page_load_wait_range: Tuple[float, float] = (1.0, 3.0)
    back_button_probability: float = 0.1
    tab_switching_probability: float = 0.05
    
    # Idle behavior
    idle_movement_probability: float = 0.3
    idle_check_interval: float = 5.0
    max_idle_time: float = 120.0


@dataclass
class BehaviorProfile:
    """Profile defining human behavior characteristics"""
    name: str
    description: str
    
    # Behavioral traits
    browsing_speed: float = 1.0  # Multiplier for all timing
    attention_span: float = 1.0  # Attention duration multiplier
    distraction_level: float = 0.1  # Probability of random actions
    precision: float = 0.8  # Mouse/click accuracy (0.0-1.0)
    
    # Preferences
    scroll_preference: str = "smooth"  # smooth, jerky, step
    reading_pattern: str = "linear"    # linear, scanning, skipping
    interaction_style: str = "careful" # careful, quick, exploratory


class BehaviorSimulator:
    """
    Simulates realistic human browsing behavior patterns
    """
    
    # Predefined behavior profiles
    BEHAVIOR_PROFILES = {
        "careful_reader": BehaviorProfile(
            name="Careful Reader",
            description="Methodical user who reads content thoroughly",
            browsing_speed=0.7,
            attention_span=1.5,
            distraction_level=0.05,
            precision=0.9,
            scroll_preference="smooth",
            reading_pattern="linear",
            interaction_style="careful"
        ),
        "quick_scanner": BehaviorProfile(
            name="Quick Scanner", 
            description="Fast user who scans content quickly",
            browsing_speed=1.4,
            attention_span=0.6,
            distraction_level=0.2,
            precision=0.7,
            scroll_preference="step",
            reading_pattern="scanning",
            interaction_style="quick"
        ),
        "distracted_browser": BehaviorProfile(
            name="Distracted Browser",
            description="User with short attention span and frequent distractions",
            browsing_speed=1.1,
            attention_span=0.4,
            distraction_level=0.4,
            precision=0.6,
            scroll_preference="jerky",
            reading_pattern="skipping",
            interaction_style="exploratory"
        ),
        "focused_researcher": BehaviorProfile(
            name="Focused Researcher",
            description="Deliberate user doing focused research",
            browsing_speed=0.8,
            attention_span=2.0,
            distraction_level=0.02,
            precision=0.95,
            scroll_preference="smooth",
            reading_pattern="linear",
            interaction_style="careful"
        )
    }
    
    def __init__(self, config: Optional[BehaviorConfig] = None):
        self.config = config or BehaviorConfig()
        self.logger = self._setup_logging()
        
        # Current behavior state
        self.current_profile = self.BEHAVIOR_PROFILES["careful_reader"]
        self.mouse_position = MousePosition(960, 540)  # Center of 1920x1080
        self.last_interaction = time.time()
        
        # Session tracking
        self.session_behaviors: Dict[str, List[Dict[str, Any]]] = {}
        self.behavior_history: List[Dict[str, Any]] = []
        
        # Timing patterns
        self.typing_rhythm: Dict[str, float] = self._generate_typing_rhythm()
        self.scroll_patterns: List[Dict[str, Any]] = self._generate_scroll_patterns()
        
        self.logger.info(f"BehaviorSimulator initialized with {self.config.intensity.value} intensity")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for behavior simulation"""
        logger = logging.getLogger("behavior_simulator")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _generate_typing_rhythm(self) -> Dict[str, float]:
        """Generate personal typing rhythm patterns"""
        base_intervals = {
            'a': 0.12, 'b': 0.15, 'c': 0.14, 'd': 0.11, 'e': 0.09,
            'f': 0.13, 'g': 0.14, 'h': 0.12, 'i': 0.10, 'j': 0.16,
            'k': 0.15, 'l': 0.11, 'm': 0.16, 'n': 0.12, 'o': 0.10,
            'p': 0.13, 'q': 0.18, 'r': 0.11, 's': 0.10, 't': 0.09,
            'u': 0.12, 'v': 0.16, 'w': 0.15, 'x': 0.17, 'y': 0.14,
            'z': 0.18, ' ': 0.08
        }
        
        # Add personal variance
        rhythm = {}
        for char, base_time in base_intervals.items():
            variance = random.uniform(-0.03, 0.03)
            rhythm[char] = max(0.05, base_time + variance)
        
        return rhythm
    
    def _generate_scroll_patterns(self) -> List[Dict[str, Any]]:
        """Generate natural scrolling patterns"""
        patterns = [
            {
                "name": "reading_scroll",
                "description": "Smooth scrolling while reading",
                "scroll_sizes": [150, 200, 250, 300],
                "pause_range": (0.8, 2.0),
                "acceleration": "smooth"
            },
            {
                "name": "scanning_scroll", 
                "description": "Quick scrolling to scan content",
                "scroll_sizes": [400, 500, 600, 800],
                "pause_range": (0.2, 0.5),
                "acceleration": "linear"
            },
            {
                "name": "searching_scroll",
                "description": "Variable scrolling when searching",
                "scroll_sizes": [100, 300, 150, 500, 200],
                "pause_range": (0.1, 1.0),
                "acceleration": "variable"
            }
        ]
        return patterns
    
    def set_behavior_profile(self, profile_name: str):
        """Set the current behavior profile"""
        if profile_name in self.BEHAVIOR_PROFILES:
            self.current_profile = self.BEHAVIOR_PROFILES[profile_name]
            self.logger.info(f"Switched to behavior profile: {profile_name}")
        else:
            self.logger.warning(f"Unknown behavior profile: {profile_name}")
    
    def create_custom_profile(self, profile: BehaviorProfile):
        """Add a custom behavior profile"""
        self.BEHAVIOR_PROFILES[profile.name] = profile
        self.logger.info(f"Added custom behavior profile: {profile.name}")
    
    async def pre_request_behavior(self, session_id: str, context: Optional[Dict[str, Any]] = None):
        """Execute behavior before making a request"""
        if self.config.intensity == IntensityLevel.MINIMAL:
            await asyncio.sleep(random.uniform(0.1, 0.3))
            return
        
        behaviors_executed = []
        
        # Pre-navigation pause (thinking time)
        if self.config.enable_reading_pauses:
            think_time = self._calculate_thinking_time(context)
            await asyncio.sleep(think_time)
            behaviors_executed.append({"type": "thinking_pause", "duration": think_time})
        
        # Random mouse movement
        if (self.config.enable_mouse_movements and 
            random.random() < self.current_profile.distraction_level):
            await self._simulate_mouse_movement("random")
            behaviors_executed.append({"type": "random_mouse_movement"})
        
        # Idle scrolling (if on a page)
        if (self.config.enable_scrolling and 
            random.random() < 0.2):
            await self._simulate_scroll("idle")
            behaviors_executed.append({"type": "idle_scroll"})
        
        # Record behaviors
        self._record_session_behavior(session_id, "pre_request", behaviors_executed)
        
        self.logger.debug(f"Pre-request behavior for {session_id}: {len(behaviors_executed)} actions")
    
    async def post_request_behavior(self, 
                                   session_id: str, 
                                   success: bool, 
                                   context: Optional[Dict[str, Any]] = None):
        """Execute behavior after receiving a response"""
        if self.config.intensity == IntensityLevel.MINIMAL:
            await asyncio.sleep(random.uniform(0.2, 0.5))
            return
        
        behaviors_executed = []
        
        # Page load waiting time
        if self.config.enable_navigation_delays:
            load_wait = self._calculate_page_load_wait(success, context)
            await asyncio.sleep(load_wait)
            behaviors_executed.append({"type": "page_load_wait", "duration": load_wait})
        
        # Content scanning behavior
        if success and self.config.enable_reading_pauses:
            await self._simulate_content_scanning(context)
            behaviors_executed.append({"type": "content_scanning"})
        
        # Reading and scrolling behavior
        if success and self.config.enable_scrolling:
            scroll_actions = await self._simulate_reading_scroll(context)
            behaviors_executed.extend(scroll_actions)
        
        # Random interactions based on profile
        if random.random() < self.current_profile.distraction_level:
            distraction_actions = await self._simulate_distraction_behavior()
            behaviors_executed.extend(distraction_actions)
        
        # Update interaction timestamp
        self.last_interaction = time.time()
        
        # Record behaviors
        self._record_session_behavior(session_id, "post_request", behaviors_executed)
        
        self.logger.debug(f"Post-request behavior for {session_id}: {len(behaviors_executed)} actions")
    
    def _calculate_thinking_time(self, context: Optional[Dict[str, Any]]) -> float:
        """Calculate realistic thinking/decision time"""
        base_time = random.uniform(0.5, 2.0)
        
        # Adjust for profile
        base_time *= (2.0 - self.current_profile.browsing_speed)
        
        # Adjust for content complexity
        if context and context.get("page_type") == "search_results":
            base_time *= 0.7  # Faster for search results
        elif context and context.get("content_length", 0) > 10000:
            base_time *= 1.3  # Longer for complex pages
        
        # Add variability
        variance = base_time * self.config.variability_factor
        thinking_time = max(0.1, base_time + random.uniform(-variance, variance))
        
        return thinking_time
    
    def _calculate_page_load_wait(self, success: bool, context: Optional[Dict[str, Any]]) -> float:
        """Calculate realistic page load waiting time"""
        if not success:
            # Shorter wait for failed requests
            return random.uniform(0.5, 1.5)
        
        base_wait = random.uniform(*self.config.page_load_wait_range)
        
        # Adjust for profile patience
        if self.current_profile.browsing_speed > 1.2:
            base_wait *= 0.8  # Impatient users wait less
        elif self.current_profile.browsing_speed < 0.8:
            base_wait *= 1.2  # Patient users wait longer
        
        return base_wait
    
    async def _simulate_mouse_movement(self, movement_type: str = "natural"):
        """Simulate realistic mouse movements"""
        if not self.config.enable_mouse_movements:
            return
        
        current_pos = self.mouse_position
        
        if movement_type == "random":
            # Random movement within screen bounds
            target_x = random.randint(100, 1820)
            target_y = random.randint(100, 980)
        elif movement_type == "reading":
            # Follow reading pattern
            target_x = current_pos.x + random.randint(-50, 200)
            target_y = current_pos.y + random.randint(20, 100)
        else:  # natural
            # Natural cursor drift
            target_x = current_pos.x + random.randint(-30, 30)
            target_y = current_pos.y + random.randint(-20, 20)
        
        # Ensure bounds
        target_x = max(10, min(1910, target_x))
        target_y = max(10, min(1070, target_y))
        
        await self._move_mouse_smoothly(current_pos.x, current_pos.y, target_x, target_y)
        
        self.mouse_position = MousePosition(target_x, target_y)
    
    async def _move_mouse_smoothly(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Move mouse with smooth, human-like motion"""
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
        if distance < 5:
            return
        
        # Calculate movement parameters
        speed = random.randint(*self.config.mouse_speed_range)  # pixels per second
        duration = distance / speed
        steps = max(3, int(duration * 60))  # 60 steps per second
        
        # Add curvature for natural movement
        curvature = self.config.mouse_path_curvature * distance * 0.1
        curve_offset = random.uniform(-curvature, curvature)
        
        for i in range(steps):
            progress = (i + 1) / steps
            
            # Bezier curve for smooth movement
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress
            
            # Add curve in the middle
            if 0.2 < progress < 0.8:
                curve_factor = 4 * progress * (1 - progress)  # Peak at 0.5
                y += curve_offset * curve_factor
            
            # Add small random jitter
            jitter_x = random.uniform(-1, 1)
            jitter_y = random.uniform(-1, 1)
            
            self.mouse_position = MousePosition(
                int(x + jitter_x), 
                int(y + jitter_y)
            )
            
            await asyncio.sleep(duration / steps)
    
    async def _simulate_scroll(self, scroll_type: str = "reading"):
        """Simulate realistic scrolling behavior"""
        if not self.config.enable_scrolling:
            return
        
        # Select scroll pattern based on type and profile
        if scroll_type == "reading":
            pattern = self.scroll_patterns[0]  # reading_scroll
        elif scroll_type == "scanning":
            pattern = self.scroll_patterns[1]  # scanning_scroll
        else:  # idle or searching
            pattern = random.choice(self.scroll_patterns)
        
        # Apply profile modifications
        scroll_size = random.choice(pattern["scroll_sizes"])
        scroll_size = int(scroll_size * self.current_profile.browsing_speed)
        
        pause_range = pattern["pause_range"]
        pause_time = random.uniform(*pause_range)
        pause_time *= (2.0 - self.current_profile.browsing_speed)  # Adjust for profile
        
        # Simulate the scroll action (this would interface with browser)
        self.logger.debug(f"Scrolling {scroll_size}px with {pause_time:.2f}s pause")
        
        await asyncio.sleep(pause_time)
    
    async def _simulate_content_scanning(self, context: Optional[Dict[str, Any]]):
        """Simulate scanning content on a page"""
        scan_time = self.config.content_scan_time
        
        # Adjust for content type and length
        if context:
            content_length = context.get("content_length", 1000)
            if content_length > 5000:
                scan_time *= 1.5
            elif content_length < 1000:
                scan_time *= 0.7
        
        # Apply profile adjustments
        scan_time *= (2.0 - self.current_profile.browsing_speed)
        scan_time += random.uniform(-scan_time * 0.3, scan_time * 0.3)
        
        await asyncio.sleep(max(0.5, scan_time))
    
    async def _simulate_reading_scroll(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate reading-based scrolling behavior"""
        actions = []
        
        # Determine reading behavior based on profile
        reading_pattern = self.current_profile.reading_pattern
        
        if reading_pattern == "linear":
            # Methodical scrolling
            scroll_count = random.randint(2, 5)
            for _ in range(scroll_count):
                await self._simulate_scroll("reading")
                actions.append({"type": "reading_scroll"})
        
        elif reading_pattern == "scanning":
            # Quick scanning scrolls
            scroll_count = random.randint(3, 7)
            for _ in range(scroll_count):
                await self._simulate_scroll("scanning")
                actions.append({"type": "scanning_scroll"})
        
        elif reading_pattern == "skipping":
            # Irregular scrolling with longer jumps
            scroll_count = random.randint(1, 4)
            for _ in range(scroll_count):
                if random.random() < 0.6:
                    await self._simulate_scroll("searching")
                else:
                    await self._simulate_scroll("reading")
                actions.append({"type": "skipping_scroll"})
        
        return actions
    
    async def _simulate_distraction_behavior(self) -> List[Dict[str, Any]]:
        """Simulate distracted/exploratory behavior"""
        actions = []
        
        distraction_types = []
        
        if self.config.enable_mouse_movements:
            distraction_types.append("random_mouse")
        
        if self.config.enable_scrolling:
            distraction_types.append("idle_scroll")
        
        if not distraction_types:
            return actions
        
        distraction = random.choice(distraction_types)
        
        if distraction == "random_mouse":
            await self._simulate_mouse_movement("random")
            actions.append({"type": "distraction_mouse_movement"})
        
        elif distraction == "idle_scroll":
            await self._simulate_scroll("idle")
            actions.append({"type": "distraction_scroll"})
        
        return actions
    
    async def simulate_typing(self, text: str, session_id: Optional[str] = None) -> float:
        """
        Simulate realistic typing behavior
        
        Args:
            text: Text to type
            session_id: Optional session identifier
            
        Returns:
            Total typing duration in seconds
        """
        if not self.config.enable_typing or not text:
            return 0.0
        
        total_duration = 0.0
        text_lower = text.lower()
        
        # Calculate base typing speed (characters per second)
        wpm = random.randint(*self.config.typing_speed_range)
        cps = (wpm * 5) / 60  # Assume 5 characters per word
        
        # Apply profile speed adjustment
        cps *= self.current_profile.browsing_speed
        
        for i, char in enumerate(text_lower):
            # Get character-specific timing
            char_time = self.typing_rhythm.get(char, 0.12)
            char_time *= (1.0 / cps)  # Adjust for overall speed
            
            # Add natural variation
            variation = char_time * self.config.variability_factor
            char_time += random.uniform(-variation, variation)
            
            # Simulate typing errors
            if (random.random() < self.config.typing_error_rate and 
                char.isalpha()):
                # Simulate error + correction
                error_time = char_time * 2  # Time to type wrong char
                correction_time = char_time * 1.5  # Time to backspace and correct
                char_time += error_time + correction_time
            
            # Simulate thinking pauses
            if (random.random() < self.config.typing_pause_probability and 
                char == ' '):
                pause_time = random.uniform(0.5, 2.0)
                char_time += pause_time
            
            await asyncio.sleep(max(0.01, char_time))
            total_duration += char_time
        
        self.logger.debug(f"Typed '{text[:50]}...' in {total_duration:.2f}s "
                         f"({len(text)/total_duration:.1f} chars/sec)")
        
        return total_duration
    
    def _record_session_behavior(self, 
                                session_id: str, 
                                phase: str, 
                                actions: List[Dict[str, Any]]):
        """Record behavior for session analysis"""
        if session_id not in self.session_behaviors:
            self.session_behaviors[session_id] = []
        
        behavior_record = {
            "timestamp": time.time(),
            "session_id": session_id,
            "phase": phase,
            "profile": self.current_profile.name,
            "actions": actions,
            "action_count": len(actions)
        }
        
        self.session_behaviors[session_id].append(behavior_record)
        self.behavior_history.append(behavior_record)
        
        # Keep history manageable
        if len(self.behavior_history) > 1000:
            self.behavior_history = self.behavior_history[-1000:]
    
    def get_session_behavior_stats(self, session_id: str) -> Dict[str, Any]:
        """Get behavior statistics for a session"""
        if session_id not in self.session_behaviors:
            return {"session_id": session_id, "total_behaviors": 0}
        
        behaviors = self.session_behaviors[session_id]
        total_actions = sum(b["action_count"] for b in behaviors)
        
        # Count action types
        action_counts = {}
        for behavior in behaviors:
            for action in behavior["actions"]:
                action_type = action["type"]
                action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        return {
            "session_id": session_id,
            "total_behaviors": len(behaviors),
            "total_actions": total_actions,
            "action_breakdown": action_counts,
            "profile_used": behaviors[0]["profile"] if behaviors else None,
            "duration": behaviors[-1]["timestamp"] - behaviors[0]["timestamp"] if behaviors else 0
        }
    
    def get_global_behavior_stats(self) -> Dict[str, Any]:
        """Get global behavior statistics"""
        if not self.behavior_history:
            return {"total_sessions": 0, "total_behaviors": 0}
        
        sessions = set(b["session_id"] for b in self.behavior_history)
        total_actions = sum(b["action_count"] for b in self.behavior_history)
        
        # Profile usage
        profile_usage = {}
        for behavior in self.behavior_history:
            profile = behavior["profile"]
            profile_usage[profile] = profile_usage.get(profile, 0) + 1
        
        # Action type distribution
        action_distribution = {}
        for behavior in self.behavior_history:
            for action in behavior["actions"]:
                action_type = action["type"]
                action_distribution[action_type] = action_distribution.get(action_type, 0) + 1
        
        return {
            "total_sessions": len(sessions),
            "total_behaviors": len(self.behavior_history),
            "total_actions": total_actions,
            "profile_usage": profile_usage,
            "action_distribution": action_distribution,
            "current_profile": self.current_profile.name,
            "intensity_level": self.config.intensity.value
        }
    
    def export_behavior_profile(self, profile_name: str, file_path: str):
        """Export a behavior profile to file"""
        if profile_name not in self.BEHAVIOR_PROFILES:
            raise ValueError(f"Profile '{profile_name}' not found")
        
        profile = self.BEHAVIOR_PROFILES[profile_name]
        profile_data = {
            "name": profile.name,
            "description": profile.description,
            "browsing_speed": profile.browsing_speed,
            "attention_span": profile.attention_span,
            "distraction_level": profile.distraction_level,
            "precision": profile.precision,
            "scroll_preference": profile.scroll_preference,
            "reading_pattern": profile.reading_pattern,
            "interaction_style": profile.interaction_style
        }
        
        with open(file_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        self.logger.info(f"Exported behavior profile '{profile_name}' to {file_path}")
    
    def import_behavior_profile(self, file_path: str) -> str:
        """Import a behavior profile from file"""
        with open(file_path, 'r') as f:
            profile_data = json.load(f)
        
        profile = BehaviorProfile(**profile_data)
        self.BEHAVIOR_PROFILES[profile.name] = profile
        
        self.logger.info(f"Imported behavior profile '{profile.name}' from {file_path}")
        return profile.name


# Factory function for easy creation
def create_behavior_simulator(intensity: IntensityLevel = IntensityLevel.MEDIUM,
                             profile_name: str = "careful_reader",
                             enable_all_behaviors: bool = True) -> BehaviorSimulator:
    """
    Factory function to create a BehaviorSimulator with common configurations
    
    Args:
        intensity: Simulation intensity level
        profile_name: Initial behavior profile to use
        enable_all_behaviors: Whether to enable all behavior types
        
    Returns:
        Configured BehaviorSimulator instance
    """
    config = BehaviorConfig(
        intensity=intensity,
        enable_mouse_movements=enable_all_behaviors,
        enable_scrolling=enable_all_behaviors,
        enable_typing=enable_all_behaviors,
        enable_reading_pauses=enable_all_behaviors
    )
    
    simulator = BehaviorSimulator(config)
    simulator.set_behavior_profile(profile_name)
    
    return simulator