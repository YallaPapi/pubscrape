"""
Anti-Detection Layer Implementation
TASK-F002: Advanced fingerprint randomization and human behavior simulation

Provides comprehensive anti-detection mechanisms including:
- Browser fingerprint randomization
- Human behavior simulation
- Proxy rotation and management
- Session isolation mechanisms
"""

import random
import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import threading
from collections import deque


@dataclass
class FingerprintProfile:
    """Browser fingerprint profile for anti-detection"""
    user_agent: str
    screen_resolution: Tuple[int, int]
    viewport_size: Tuple[int, int]
    timezone: str
    locale: str
    languages: List[str]
    platform: str
    hardware_concurrency: int
    device_memory: int
    webgl_vendor: str
    webgl_renderer: str
    canvas_noise: float
    audio_noise: float
    font_list: List[str]
    plugins: List[str]
    
    def to_hash(self) -> str:
        """Generate unique hash for this fingerprint"""
        data = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class FingerprintGenerator:
    """Generate realistic browser fingerprints"""
    
    # Realistic user agent strings
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    
    # Common screen resolutions
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (2560, 1440), (1366, 768), (1440, 900),
        (1536, 864), (1680, 1050), (1280, 720), (1600, 900)
    ]
    
    # Timezone options
    TIMEZONES = [
        "America/New_York", "America/Chicago", "America/Los_Angeles",
        "America/Denver", "America/Phoenix", "America/Detroit",
        "Europe/London", "Europe/Paris", "Asia/Tokyo"
    ]
    
    # WebGL vendors and renderers
    WEBGL_VENDORS = [
        "Intel Inc.", "NVIDIA Corporation", "AMD", "Apple Inc.",
        "Google Inc. (Intel)", "Google Inc. (NVIDIA)"
    ]
    
    WEBGL_RENDERERS = [
        "Intel Iris OpenGL Engine", "Intel HD Graphics 620",
        "NVIDIA GeForce GTX 1060", "AMD Radeon Pro 5500M",
        "ANGLE (Intel HD Graphics Direct3D11)"
    ]
    
    # Common fonts
    FONTS = [
        "Arial", "Verdana", "Times New Roman", "Georgia", "Courier New",
        "Comic Sans MS", "Impact", "Trebuchet MS", "Arial Black", "Palatino"
    ]
    
    @classmethod
    def generate(cls) -> FingerprintProfile:
        """Generate a realistic browser fingerprint"""
        screen_res = random.choice(cls.SCREEN_RESOLUTIONS)
        
        # Viewport is usually smaller than screen resolution
        viewport = (
            screen_res[0] - random.randint(0, 200),
            screen_res[1] - random.randint(100, 300)
        )
        
        # Select matching WebGL vendor/renderer pairs
        webgl_idx = random.randint(0, len(cls.WEBGL_VENDORS) - 1)
        
        return FingerprintProfile(
            user_agent=random.choice(cls.USER_AGENTS),
            screen_resolution=screen_res,
            viewport_size=viewport,
            timezone=random.choice(cls.TIMEZONES),
            locale=random.choice(["en-US", "en-GB", "en-CA"]),
            languages=["en-US", "en"],
            platform=random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16, 32]),
            webgl_vendor=cls.WEBGL_VENDORS[min(webgl_idx, len(cls.WEBGL_VENDORS)-1)],
            webgl_renderer=cls.WEBGL_RENDERERS[min(webgl_idx, len(cls.WEBGL_RENDERERS)-1)],
            canvas_noise=random.uniform(0.00001, 0.0001),
            audio_noise=random.uniform(0.000001, 0.00001),
            font_list=random.sample(cls.FONTS, random.randint(20, 35)),
            plugins=random.sample(["PDF Viewer", "Chrome PDF Viewer", "Native Client"], random.randint(1, 3))
        )


class HumanBehaviorSimulator:
    """Simulate realistic human browsing behavior"""
    
    def __init__(self):
        self.last_action_time = time.time()
        self.action_history = deque(maxlen=100)
        self.typing_speed = random.uniform(0.1, 0.3)  # Seconds between keystrokes
        self.reading_speed = random.uniform(2.0, 5.0)  # Seconds per paragraph
        
    def get_typing_delay(self) -> float:
        """Get realistic typing delay between keystrokes"""
        # Add variation to typing speed
        base_delay = self.typing_speed
        
        # Occasionally add longer pauses (thinking)
        if random.random() < 0.1:
            return base_delay + random.uniform(0.5, 2.0)
            
        # Normal variation
        return base_delay + random.uniform(-0.05, 0.1)
    
    def get_mouse_path(self, start: Tuple[int, int], end: Tuple[int, int], steps: int = 10) -> List[Tuple[int, int]]:
        """Generate human-like mouse movement path with bezier curves"""
        path = []
        
        # Add control points for bezier curve
        control1 = (
            start[0] + random.randint(-100, 100),
            start[1] + random.randint(-100, 100)
        )
        control2 = (
            end[0] + random.randint(-100, 100),
            end[1] + random.randint(-100, 100)
        )
        
        for i in range(steps):
            t = i / (steps - 1)
            # Cubic bezier curve
            x = (1-t)**3 * start[0] + 3*(1-t)**2*t * control1[0] + 3*(1-t)*t**2 * control2[0] + t**3 * end[0]
            y = (1-t)**3 * start[1] + 3*(1-t)**2*t * control1[1] + 3*(1-t)*t**2 * control2[1] + t**3 * end[1]
            
            # Add small random jitter
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)
            
            path.append((int(x), int(y)))
            
        return path
    
    def get_scroll_pattern(self) -> List[Dict[str, Any]]:
        """Generate human-like scrolling pattern"""
        patterns = []
        
        # Read top of page
        patterns.append({
            'action': 'wait',
            'duration': random.uniform(2.0, 4.0)
        })
        
        # Scroll down in chunks
        num_scrolls = random.randint(3, 7)
        for i in range(num_scrolls):
            patterns.append({
                'action': 'scroll',
                'distance': random.randint(200, 600),
                'duration': random.uniform(0.5, 1.5)
            })
            
            # Reading pause
            patterns.append({
                'action': 'wait',
                'duration': random.uniform(1.0, 3.0)
            })
            
            # Occasionally scroll back up a bit
            if random.random() < 0.3:
                patterns.append({
                    'action': 'scroll',
                    'distance': -random.randint(50, 200),
                    'duration': random.uniform(0.3, 0.7)
                })
                
        return patterns
    
    def simulate_reading_time(self, text_length: int) -> float:
        """Calculate realistic reading time based on text length"""
        # Average reading speed: 200-250 words per minute
        # Assuming average word length of 5 characters
        words = text_length / 5
        minutes = words / random.uniform(200, 250)
        
        # Add variation for skimming vs careful reading
        if random.random() < 0.3:  # 30% chance of skimming
            minutes *= 0.5
        elif random.random() < 0.1:  # 10% chance of careful reading
            minutes *= 1.5
            
        return minutes * 60  # Convert to seconds


class ProxyRotator:
    """Manage proxy rotation for IP diversity"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.proxy_health = {}  # Track proxy performance
        self.lock = threading.Lock()
        
        # Initialize proxy health scores
        for proxy in self.proxies:
            self.proxy_health[proxy] = {
                'success_count': 0,
                'failure_count': 0,
                'last_used': None,
                'response_times': deque(maxlen=10),
                'score': 1.0
            }
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next healthy proxy from rotation"""
        if not self.proxies:
            return None
            
        with self.lock:
            # Sort proxies by health score
            sorted_proxies = sorted(
                self.proxies,
                key=lambda p: self.proxy_health[p]['score'],
                reverse=True
            )
            
            # Select from top healthy proxies
            top_proxies = sorted_proxies[:max(3, len(sorted_proxies) // 3)]
            selected = random.choice(top_proxies)
            
            # Update last used time
            self.proxy_health[selected]['last_used'] = datetime.now()
            
            return selected
    
    def report_proxy_result(self, proxy: str, success: bool, response_time: float = 0):
        """Report proxy performance for health tracking"""
        if proxy not in self.proxy_health:
            return
            
        with self.lock:
            health = self.proxy_health[proxy]
            
            if success:
                health['success_count'] += 1
                health['response_times'].append(response_time)
            else:
                health['failure_count'] += 1
                
            # Calculate health score
            total = health['success_count'] + health['failure_count']
            if total > 0:
                success_rate = health['success_count'] / total
                
                # Factor in response time
                avg_response = sum(health['response_times']) / len(health['response_times']) if health['response_times'] else 10
                time_factor = min(1.0, 2.0 / avg_response)  # Prefer faster proxies
                
                health['score'] = success_rate * 0.7 + time_factor * 0.3
            
    def remove_unhealthy_proxies(self, threshold: float = 0.3):
        """Remove proxies with health score below threshold"""
        with self.lock:
            healthy_proxies = [
                proxy for proxy in self.proxies
                if self.proxy_health[proxy]['score'] >= threshold
            ]
            
            removed_count = len(self.proxies) - len(healthy_proxies)
            self.proxies = healthy_proxies
            
            return removed_count


class SessionIsolator:
    """Manage browser session isolation for anti-detection"""
    
    def __init__(self, base_profile_dir: str = "./browser_profiles"):
        self.base_dir = Path(base_profile_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.active_sessions = {}
        self.session_fingerprints = {}
        
    def create_isolated_session(self, session_id: str) -> Dict[str, Any]:
        """Create a new isolated browser session"""
        # Generate unique fingerprint
        fingerprint = FingerprintGenerator.generate()
        
        # Create session directory
        session_dir = self.base_dir / f"session_{session_id}"
        session_dir.mkdir(exist_ok=True)
        
        # Store session configuration
        session_config = {
            'id': session_id,
            'fingerprint': fingerprint,
            'profile_dir': str(session_dir),
            'created_at': datetime.now().isoformat(),
            'cookies': [],
            'local_storage': {},
            'session_storage': {}
        }
        
        # Save configuration
        config_file = session_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(session_config, f, indent=2, default=str)
            
        self.active_sessions[session_id] = session_config
        self.session_fingerprints[session_id] = fingerprint
        
        return session_config
    
    def get_session_fingerprint(self, session_id: str) -> Optional[FingerprintProfile]:
        """Get fingerprint for a session"""
        return self.session_fingerprints.get(session_id)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old session profiles"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for session_dir in self.base_dir.iterdir():
            if session_dir.is_dir() and session_dir.name.startswith("session_"):
                config_file = session_dir / "config.json"
                
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                            
                        created_at = datetime.fromisoformat(config['created_at'])
                        
                        if created_at < cutoff_time:
                            # Remove old session
                            import shutil
                            shutil.rmtree(session_dir)
                            cleaned_count += 1
                            
                            # Remove from active sessions
                            session_id = config['id']
                            self.active_sessions.pop(session_id, None)
                            self.session_fingerprints.pop(session_id, None)
                            
                    except Exception as e:
                        print(f"Error cleaning session {session_dir}: {e}")
                        
        return cleaned_count


class AntiDetectionManager:
    """Central manager for all anti-detection mechanisms"""
    
    def __init__(self):
        self.fingerprint_generator = FingerprintGenerator()
        self.behavior_simulator = HumanBehaviorSimulator()
        self.proxy_rotator = None
        self.session_isolator = SessionIsolator()
        self.detection_checks = []
        
    def initialize_proxies(self, proxy_list: List[str]):
        """Initialize proxy rotation"""
        self.proxy_rotator = ProxyRotator(proxy_list)
        
    def create_stealth_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a complete stealth browsing session"""
        if not session_id:
            session_id = f"stealth_{int(time.time())}_{random.randint(1000, 9999)}"
            
        # Create isolated session
        session = self.session_isolator.create_isolated_session(session_id)
        
        # Get proxy if available
        proxy = None
        if self.proxy_rotator:
            proxy = self.proxy_rotator.get_next_proxy()
            
        # Add stealth configuration
        session['stealth_config'] = {
            'proxy': proxy,
            'behavior_simulator': self.behavior_simulator,
            'fingerprint': session['fingerprint']
        }
        
        return session
    
    def check_detection_status(self, page_source: str, url: str) -> Dict[str, Any]:
        """Check if anti-bot measures are detected"""
        detection_status = {
            'detected': False,
            'confidence': 0.0,
            'indicators': [],
            'url': url
        }
        
        # Detection patterns with confidence scores
        patterns = {
            'captcha': 0.9,
            'recaptcha': 0.9,
            'hcaptcha': 0.9,
            'cloudflare': 0.8,
            'bot detection': 0.8,
            'access denied': 0.7,
            'unusual activity': 0.7,
            'security check': 0.6,
            'please verify': 0.6,
            'are you human': 0.9,
            'automated access': 0.7,
            'rate limit': 0.5
        }
        
        page_lower = page_source.lower()
        
        for pattern, confidence in patterns.items():
            if pattern in page_lower:
                detection_status['indicators'].append(pattern)
                detection_status['confidence'] = max(detection_status['confidence'], confidence)
                
        detection_status['detected'] = detection_status['confidence'] >= 0.5
        
        # Log detection for analysis
        self.detection_checks.append({
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'status': detection_status
        })
        
        return detection_status
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """Get statistics on detection attempts"""
        if not self.detection_checks:
            return {'total_checks': 0, 'detection_rate': 0.0}
            
        total = len(self.detection_checks)
        detected = sum(1 for check in self.detection_checks if check['status']['detected'])
        
        return {
            'total_checks': total,
            'detected_count': detected,
            'detection_rate': detected / total if total > 0 else 0.0,
            'common_indicators': self._get_common_indicators(),
            'recent_checks': self.detection_checks[-10:]
        }
    
    def _get_common_indicators(self) -> List[Tuple[str, int]]:
        """Get most common detection indicators"""
        indicator_counts = {}
        
        for check in self.detection_checks:
            for indicator in check['status']['indicators']:
                indicator_counts[indicator] = indicator_counts.get(indicator, 0) + 1
                
        # Sort by frequency
        sorted_indicators = sorted(
            indicator_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_indicators[:5]


if __name__ == "__main__":
    # Test anti-detection components
    print("Anti-Detection Layer Test")
    print("="*50)
    
    # Test fingerprint generation
    print("\n1. Fingerprint Generation:")
    fp1 = FingerprintGenerator.generate()
    fp2 = FingerprintGenerator.generate()
    print(f"Fingerprint 1 hash: {fp1.to_hash()}")
    print(f"Fingerprint 2 hash: {fp2.to_hash()}")
    print(f"Fingerprints unique: {fp1.to_hash() != fp2.to_hash()}")
    
    # Test human behavior simulation
    print("\n2. Human Behavior Simulation:")
    behavior = HumanBehaviorSimulator()
    print(f"Typing delay: {behavior.get_typing_delay():.3f}s")
    mouse_path = behavior.get_mouse_path((100, 100), (500, 400))
    print(f"Mouse path points: {len(mouse_path)}")
    scroll_pattern = behavior.get_scroll_pattern()
    print(f"Scroll actions: {len(scroll_pattern)}")
    
    # Test session isolation
    print("\n3. Session Isolation:")
    isolator = SessionIsolator()
    session = isolator.create_isolated_session("test_session")
    print(f"Session created: {session['id']}")
    print(f"Profile directory: {session['profile_dir']}")
    
    # Test anti-detection manager
    print("\n4. Anti-Detection Manager:")
    manager = AntiDetectionManager()
    stealth_session = manager.create_stealth_session()
    print(f"Stealth session ID: {stealth_session['id']}")
    print(f"Fingerprint hash: {stealth_session['fingerprint'].to_hash()}")
    
    print("\nAnti-detection layer initialized successfully!")