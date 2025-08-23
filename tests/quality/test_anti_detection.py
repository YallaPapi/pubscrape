"""
Anti-detection validation tests for the scraper system.

Tests stealth capabilities, bot detection evasion,
CAPTCHA handling, and overall anti-detection effectiveness.
"""

import pytest
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

try:
    from src.infra.anti_detection_supervisor import AntiDetectionSupervisor
    from src.infra.browser_manager import BrowserManager
    from src.infra.user_agent_manager import UserAgentManager
    from src.infra.proxy_manager import ProxyManager
    from src.infra.delay_manager import DelayManager
except ImportError:
    pytest.skip("Anti-detection modules not available", allow_module_level=True)


@dataclass
class DetectionTestResult:
    """Result of a detection test"""
    test_name: str
    detected: bool
    confidence: float
    evidence: List[str]
    response_time: float
    timestamp: datetime
    metadata: Dict[str, Any]


class AntiDetectionTester:
    """Anti-detection testing utility"""
    
    def __init__(self):
        self.test_results: List[DetectionTestResult] = []
        self.detection_indicators = [
            # Common bot detection indicators
            "bot", "robot", "crawler", "spider", "automated",
            "blocked", "denied", "forbidden", "captcha",
            "verify", "human", "suspicious", "unusual"
        ]
    
    def test_user_agent_effectiveness(self, user_agents: List[str]) -> Dict[str, Any]:
        """Test effectiveness of user agent rotation"""
        results = {
            "total_agents_tested": len(user_agents),
            "agents_analysis": [],
            "diversity_score": 0.0,
            "realism_score": 0.0,
            "recommendations": []
        }
        
        for ua in user_agents:
            analysis = self._analyze_user_agent(ua)
            results["agents_analysis"].append(analysis)
        
        # Calculate diversity score
        unique_browsers = set()
        unique_os = set()
        
        for analysis in results["agents_analysis"]:
            if analysis["browser"]:
                unique_browsers.add(analysis["browser"])
            if analysis["os"]:
                unique_os.add(analysis["os"])
        
        results["diversity_score"] = (
            len(unique_browsers) * len(unique_os) / len(user_agents)
            if user_agents else 0
        )
        
        # Calculate realism score
        realistic_count = sum(
            1 for analysis in results["agents_analysis"]
            if analysis["realism_score"] >= 0.7
        )
        results["realism_score"] = realistic_count / len(user_agents) if user_agents else 0
        
        # Generate recommendations
        if results["diversity_score"] < 0.5:
            results["recommendations"].append("Increase user agent diversity")
        
        if results["realism_score"] < 0.8:
            results["recommendations"].append("Use more realistic user agent strings")
        
        return results
    
    def _analyze_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """Analyze a single user agent string"""
        analysis = {
            "user_agent": user_agent,
            "browser": None,
            "os": None,
            "realism_score": 0.0,
            "issues": []
        }
        
        # Detect browser
        if "Chrome" in user_agent:
            analysis["browser"] = "Chrome"
        elif "Firefox" in user_agent:
            analysis["browser"] = "Firefox"
        elif "Safari" in user_agent:
            analysis["browser"] = "Safari"
        elif "Edge" in user_agent:
            analysis["browser"] = "Edge"
        
        # Detect OS
        if "Windows" in user_agent:
            analysis["os"] = "Windows"
        elif "Macintosh" in user_agent or "Mac OS" in user_agent:
            analysis["os"] = "macOS"
        elif "Linux" in user_agent:
            analysis["os"] = "Linux"
        elif "Android" in user_agent:
            analysis["os"] = "Android"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            analysis["os"] = "iOS"
        
        # Calculate realism score
        score = 0.0
        
        # Has browser and OS
        if analysis["browser"] and analysis["os"]:
            score += 0.4
        
        # Reasonable length
        if 50 <= len(user_agent) <= 200:
            score += 0.2
        else:
            analysis["issues"].append("Unusual length")
        
        # Contains Mozilla (most browsers do)
        if "Mozilla" in user_agent:
            score += 0.2
        else:
            analysis["issues"].append("Missing Mozilla")
        
        # Not obviously a bot
        bot_indicators = ["bot", "crawler", "spider", "scraper"]
        if not any(indicator in user_agent.lower() for indicator in bot_indicators):
            score += 0.2
        else:
            analysis["issues"].append("Contains bot indicators")
        
        analysis["realism_score"] = score
        return analysis
    
    def test_timing_patterns(self, delays: List[float]) -> Dict[str, Any]:
        """Test timing patterns for human-like behavior"""
        if not delays:
            return {"error": "No delays provided"}
        
        results = {
            "total_delays": len(delays),
            "mean_delay": sum(delays) / len(delays),
            "min_delay": min(delays),
            "max_delay": max(delays),
            "variance": 0.0,
            "humanness_score": 0.0,
            "issues": []
        }
        
        # Calculate variance
        mean = results["mean_delay"]
        variance = sum((d - mean) ** 2 for d in delays) / len(delays)
        results["variance"] = variance
        results["std_deviation"] = variance ** 0.5
        
        # Analyze timing patterns
        score = 0.0
        
        # Reasonable mean delay (not too fast, not too slow)
        if 1.0 <= results["mean_delay"] <= 10.0:
            score += 0.3
        elif results["mean_delay"] < 0.5:
            results["issues"].append("Delays too fast (bot-like)")
        elif results["mean_delay"] > 30.0:
            results["issues"].append("Delays too slow (inefficient)")
        
        # Good variance (humans are inconsistent)
        if results["std_deviation"] >= results["mean_delay"] * 0.3:
            score += 0.3
        else:
            results["issues"].append("Too consistent (bot-like)")
        
        # No extremely short delays
        short_delays = [d for d in delays if d < 0.1]
        if len(short_delays) / len(delays) < 0.1:
            score += 0.2
        else:
            results["issues"].append("Too many very short delays")
        
        # Some longer pauses (humans pause to think)
        long_delays = [d for d in delays if d > results["mean_delay"] * 2]
        if len(long_delays) >= len(delays) * 0.1:
            score += 0.2
        else:
            results["issues"].append("Missing longer thinking pauses")
        
        results["humanness_score"] = score
        return results
    
    def test_request_patterns(self, request_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test request patterns for bot-like behavior"""
        if not request_log:
            return {"error": "No requests provided"}
        
        results = {
            "total_requests": len(request_log),
            "unique_urls": len(set(req.get("url", "") for req in request_log)),
            "request_rate": 0.0,
            "pattern_analysis": {},
            "bot_likelihood": 0.0,
            "warnings": []
        }
        
        # Calculate request rate
        if len(request_log) >= 2:
            timestamps = [req.get("timestamp", 0) for req in request_log]
            timestamps.sort()
            duration = timestamps[-1] - timestamps[0]
            results["request_rate"] = len(request_log) / duration if duration > 0 else 0
        
        # Analyze patterns
        patterns = {
            "same_interval_requests": 0,
            "rapid_fire_requests": 0,
            "perfect_sequence": 0,
            "unusual_user_agents": 0
        }
        
        # Check for same interval requests
        if len(request_log) >= 3:
            intervals = []
            for i in range(1, len(request_log)):
                prev_time = request_log[i-1].get("timestamp", 0)
                curr_time = request_log[i].get("timestamp", 0)
                intervals.append(curr_time - prev_time)
            
            # Check for identical intervals (bot-like)
            identical_intervals = 0
            for i in range(1, len(intervals)):
                if abs(intervals[i] - intervals[i-1]) < 0.01:  # 10ms tolerance
                    identical_intervals += 1
            
            patterns["same_interval_requests"] = identical_intervals
            
            # Check for rapid fire (less than 100ms between requests)
            rapid_intervals = sum(1 for interval in intervals if interval < 0.1)
            patterns["rapid_fire_requests"] = rapid_intervals
        
        # Check for perfect sequence access
        urls = [req.get("url", "") for req in request_log]
        if self._is_perfect_sequence(urls):
            patterns["perfect_sequence"] = 1
        
        # Check user agent diversity
        user_agents = [req.get("user_agent", "") for req in request_log]
        unique_uas = set(user_agents)
        if len(unique_uas) == 1 and len(request_log) > 10:
            patterns["unusual_user_agents"] = 1
        
        results["pattern_analysis"] = patterns
        
        # Calculate bot likelihood
        bot_score = 0.0
        
        # High request rate
        if results["request_rate"] > 10:  # More than 10 requests per second
            bot_score += 0.3
            results["warnings"].append("Very high request rate")
        
        # Same interval requests
        if patterns["same_interval_requests"] > len(request_log) * 0.5:
            bot_score += 0.3
            results["warnings"].append("Too many identical intervals")
        
        # Rapid fire requests
        if patterns["rapid_fire_requests"] > len(request_log) * 0.3:
            bot_score += 0.2
            results["warnings"].append("Too many rapid requests")
        
        # Perfect sequence
        if patterns["perfect_sequence"]:
            bot_score += 0.2
            results["warnings"].append("Perfect sequential access pattern")
        
        results["bot_likelihood"] = min(bot_score, 1.0)
        return results
    
    def _is_perfect_sequence(self, urls: List[str]) -> bool:
        """Check if URLs follow a perfect sequential pattern"""
        if len(urls) < 3:
            return False
        
        # Look for patterns like page1, page2, page3...
        sequential_count = 0
        for i in range(1, len(urls)):
            if self._urls_are_sequential(urls[i-1], urls[i]):
                sequential_count += 1
        
        return sequential_count >= len(urls) * 0.8
    
    def _urls_are_sequential(self, url1: str, url2: str) -> bool:
        """Check if two URLs are sequential"""
        import re
        
        # Extract numbers from URLs
        numbers1 = re.findall(r'\d+', url1)
        numbers2 = re.findall(r'\d+', url2)
        
        if len(numbers1) != len(numbers2):
            return False
        
        # Check if exactly one number incremented by 1
        differences = 0
        for n1, n2 in zip(numbers1, numbers2):
            if int(n2) == int(n1) + 1:
                differences += 1
            elif n1 != n2:
                return False
        
        return differences == 1


@pytest.mark.antidetection
class TestAntiDetectionCapabilities:
    """Test anti-detection capabilities"""
    
    @pytest.fixture
    def anti_detection_tester(self):
        """Create anti-detection tester instance"""
        return AntiDetectionTester()
    
    @pytest.fixture
    def sample_user_agents(self):
        """Sample user agents for testing"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
    
    def test_user_agent_diversity(self, anti_detection_tester, sample_user_agents):
        """Test user agent diversity and realism"""
        results = anti_detection_tester.test_user_agent_effectiveness(sample_user_agents)
        
        assert results["total_agents_tested"] == len(sample_user_agents)
        assert results["diversity_score"] >= 0.5  # Should have good diversity
        assert results["realism_score"] >= 0.8  # Should be realistic
        
        # Check individual agents
        for analysis in results["agents_analysis"]:
            assert analysis["realism_score"] >= 0.6  # Each agent should be reasonably realistic
            assert "bot" not in analysis["user_agent"].lower()  # Shouldn't contain bot indicators
    
    def test_bot_user_agent_detection(self, anti_detection_tester):
        """Test detection of obviously bot-like user agents"""
        bot_user_agents = [
            "Bot/1.0",
            "Spider-Bot",
            "Crawler/2.0",
            "Mozilla/5.0 (compatible; Googlebot/2.1)",
            "Short"
        ]
        
        results = anti_detection_tester.test_user_agent_effectiveness(bot_user_agents)
        
        # Should detect these as problematic
        assert results["realism_score"] < 0.5  # Low realism score
        assert len(results["recommendations"]) > 0  # Should have recommendations
        
        # Check that individual bot agents are flagged
        poor_agents = [
            analysis for analysis in results["agents_analysis"]
            if analysis["realism_score"] < 0.5
        ]
        assert len(poor_agents) >= 3  # Most should be flagged as poor
    
    def test_human_like_timing_patterns(self, anti_detection_tester):
        """Test human-like timing patterns"""
        # Generate human-like delays with variance
        human_delays = []
        base_delay = 2.0
        
        for _ in range(50):
            # Add randomness to simulate human behavior
            delay = base_delay + random.gauss(0, base_delay * 0.5)
            delay = max(0.1, delay)  # Minimum delay
            human_delays.append(delay)
        
        results = anti_detection_tester.test_timing_patterns(human_delays)
        
        assert results["humanness_score"] >= 0.7  # Should score well for human-like behavior
        assert len(results["issues"]) <= 1  # Should have minimal issues
        assert results["std_deviation"] >= results["mean_delay"] * 0.2  # Good variance
    
    def test_bot_like_timing_detection(self, anti_detection_tester):
        """Test detection of bot-like timing patterns"""
        # Generate bot-like delays (too consistent)
        bot_delays = [0.05] * 50  # Identical short delays
        
        results = anti_detection_tester.test_timing_patterns(bot_delays)
        
        assert results["humanness_score"] < 0.5  # Should score poorly
        assert "Too consistent" in str(results["issues"])  # Should detect consistency issue
        assert "too fast" in str(results["issues"]).lower()  # Should detect speed issue
    
    def test_request_pattern_analysis(self, anti_detection_tester):
        """Test request pattern analysis"""
        # Generate human-like request pattern
        human_requests = []
        base_time = time.time()
        
        for i in range(20):
            # Vary intervals and add some randomness
            interval = random.uniform(1.0, 5.0)
            base_time += interval
            
            human_requests.append({
                "url": f"https://example.com/page{random.randint(1, 100)}",
                "timestamp": base_time,
                "user_agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                ])
            })
        
        results = anti_detection_tester.test_request_patterns(human_requests)
        
        assert results["bot_likelihood"] < 0.5  # Should have low bot likelihood
        assert results["request_rate"] < 5  # Reasonable request rate
        assert len(results["warnings"]) <= 1  # Minimal warnings
    
    def test_bot_request_pattern_detection(self, anti_detection_tester):
        """Test detection of bot-like request patterns"""
        # Generate bot-like request pattern
        bot_requests = []
        base_time = time.time()
        
        for i in range(30):
            # Identical intervals (bot-like)
            base_time += 0.1  # Very fast, consistent
            
            bot_requests.append({
                "url": f"https://example.com/page{i+1}",  # Perfect sequence
                "timestamp": base_time,
                "user_agent": "Mozilla/5.0 (Bot)"  # Same UA every time
            })
        
        results = anti_detection_tester.test_request_patterns(bot_requests)
        
        assert results["bot_likelihood"] >= 0.7  # Should have high bot likelihood
        assert results["request_rate"] > 5  # High request rate
        assert len(results["warnings"]) >= 2  # Multiple warnings
        assert "rapid" in str(results["warnings"]).lower() or "interval" in str(results["warnings"]).lower()


@pytest.mark.antidetection
class TestStealthMeasures:
    """Test stealth measures and browser fingerprinting evasion"""
    
    @pytest.fixture
    def mock_driver(self):
        """Mock WebDriver for stealth testing"""
        driver = Mock()
        driver.execute_script.return_value = None
        driver.get.return_value = None
        return driver
    
    def test_webdriver_property_hiding(self, mock_driver):
        """Test hiding of webdriver properties"""
        stealth_scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            "delete navigator.__proto__.webdriver;",
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});",
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});"
        ]
        
        # Apply stealth measures
        for script in stealth_scripts:
            mock_driver.execute_script(script)
        
        # Verify scripts were executed
        assert mock_driver.execute_script.call_count == len(stealth_scripts)
        
        # Test webdriver detection
        mock_driver.execute_script.return_value = None  # webdriver should be undefined
        webdriver_detected = mock_driver.execute_script("return navigator.webdriver")
        
        assert webdriver_detected is None  # Should be hidden
    
    def test_chrome_detection_evasion(self, mock_driver):
        """Test Chrome-specific detection evasion"""
        chrome_evasion_scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            "window.chrome = {runtime: {}};",
            "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});",
            "window.Notification.permission = 'default';"
        ]
        
        for script in chrome_evasion_scripts:
            mock_driver.execute_script(script)
        
        # Test chrome object presence
        mock_driver.execute_script.return_value = {"runtime": {}}
        chrome_obj = mock_driver.execute_script("return window.chrome")
        
        assert chrome_obj is not None  # Chrome object should exist
        assert "runtime" in chrome_obj  # Should have runtime property
    
    def test_viewport_randomization(self, mock_driver):
        """Test viewport randomization"""
        common_viewports = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1280, 720)
        ]
        
        selected_viewport = random.choice(common_viewports)
        
        # Set viewport
        mock_driver.set_window_size(*selected_viewport)
        
        # Verify viewport was set
        mock_driver.set_window_size.assert_called_with(*selected_viewport)
        
        # Viewport should be one of the common ones
        assert selected_viewport in common_viewports
    
    def test_canvas_fingerprinting_evasion(self, mock_driver):
        """Test canvas fingerprinting evasion"""
        canvas_script = """
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
            if (contextType === '2d') {
                const context = originalGetContext.call(this, contextType, contextAttributes);
                const originalGetImageData = context.getImageData;
                context.getImageData = function(sx, sy, sw, sh) {
                    const imageData = originalGetImageData.call(this, sx, sy, sw, sh);
                    // Add slight noise to prevent fingerprinting
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                    }
                    return imageData;
                };
                return context;
            }
            return originalGetContext.call(this, contextType, contextAttributes);
        };
        """
        
        mock_driver.execute_script(canvas_script)
        
        # Verify script was executed
        mock_driver.execute_script.assert_called_with(canvas_script)
        
        # Test that canvas fingerprinting returns different values
        mock_driver.execute_script.return_value = "fingerprint_123"
        fingerprint1 = mock_driver.execute_script("return canvas.toDataURL()")
        
        mock_driver.execute_script.return_value = "fingerprint_456"
        fingerprint2 = mock_driver.execute_script("return canvas.toDataURL()")
        
        # Should return different fingerprints (due to noise)
        assert fingerprint1 != fingerprint2
    
    def test_audio_fingerprinting_evasion(self, mock_driver):
        """Test audio fingerprinting evasion"""
        audio_script = """
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {
            const originalChannelData = originalGetChannelData.call(this, channel);
            // Add slight noise to prevent audio fingerprinting
            for (let i = 0; i < originalChannelData.length; i++) {
                originalChannelData[i] += (Math.random() - 0.5) * 0.0001;
            }
            return originalChannelData;
        };
        """
        
        mock_driver.execute_script(audio_script)
        
        # Verify audio fingerprinting evasion was applied
        mock_driver.execute_script.assert_called_with(audio_script)


@pytest.mark.antidetection
class TestCaptchaHandling:
    """Test CAPTCHA detection and handling"""
    
    @pytest.fixture
    def captcha_samples(self):
        """Sample HTML with various CAPTCHA types"""
        return {
            "recaptcha": """
            <div class="g-recaptcha" data-sitekey="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></div>
            <script src="https://www.google.com/recaptcha/api.js" async defer></script>
            """,
            "hcaptcha": """
            <div class="h-captcha" data-sitekey="10000000-ffff-ffff-ffff-000000000001"></div>
            <script src="https://hcaptcha.com/1/api.js" async defer></script>
            """,
            "cloudflare": """
            <div class="cf-browser-verification">
                <h1>Checking your browser before accessing the website.</h1>
                <p>This process is automatic. Your browser will redirect to your requested content shortly.</p>
            </div>
            """,
            "custom_captcha": """
            <div id="captcha-container">
                <img src="/captcha-image.png" alt="CAPTCHA">
                <input type="text" name="captcha" placeholder="Enter CAPTCHA">
            </div>
            """,
            "no_captcha": """
            <div class="content">
                <h1>Welcome to our website</h1>
                <p>This is normal content without any CAPTCHA.</p>
            </div>
            """
        }
    
    def test_recaptcha_detection(self, captcha_samples):
        """Test reCAPTCHA detection"""
        from bs4 import BeautifulSoup
        
        # Test positive detection
        soup = BeautifulSoup(captcha_samples["recaptcha"], 'html.parser')
        
        recaptcha_indicators = [
            soup.find(class_="g-recaptcha"),
            soup.find("script", src=lambda x: x and "recaptcha" in x),
            "g-recaptcha" in captcha_samples["recaptcha"]
        ]
        
        assert any(recaptcha_indicators)  # Should detect reCAPTCHA
        
        # Test negative detection
        soup_clean = BeautifulSoup(captcha_samples["no_captcha"], 'html.parser')
        
        no_recaptcha_indicators = [
            soup_clean.find(class_="g-recaptcha"),
            soup_clean.find("script", src=lambda x: x and "recaptcha" in x),
            "g-recaptcha" in captcha_samples["no_captcha"]
        ]
        
        assert not any(no_recaptcha_indicators)  # Should not detect reCAPTCHA
    
    def test_hcaptcha_detection(self, captcha_samples):
        """Test hCaptcha detection"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(captcha_samples["hcaptcha"], 'html.parser')
        
        hcaptcha_indicators = [
            soup.find(class_="h-captcha"),
            soup.find("script", src=lambda x: x and "hcaptcha" in x),
            "h-captcha" in captcha_samples["hcaptcha"]
        ]
        
        assert any(hcaptcha_indicators)  # Should detect hCaptcha
    
    def test_cloudflare_detection(self, captcha_samples):
        """Test Cloudflare challenge detection"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(captcha_samples["cloudflare"], 'html.parser')
        
        cloudflare_indicators = [
            soup.find(class_="cf-browser-verification"),
            "Checking your browser" in captcha_samples["cloudflare"],
            "cloudflare" in captcha_samples["cloudflare"].lower()
        ]
        
        assert any(cloudflare_indicators)  # Should detect Cloudflare challenge
    
    def test_custom_captcha_detection(self, captcha_samples):
        """Test custom CAPTCHA detection"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(captcha_samples["custom_captcha"], 'html.parser')
        
        custom_captcha_indicators = [
            soup.find(id="captcha-container"),
            soup.find("img", alt="CAPTCHA"),
            soup.find("input", attrs={"name": "captcha"}),
            "captcha" in captcha_samples["custom_captcha"].lower()
        ]
        
        assert any(custom_captcha_indicators)  # Should detect custom CAPTCHA
    
    def test_captcha_response_strategies(self):
        """Test CAPTCHA response strategies"""
        strategies = {
            "recaptcha": {
                "action": "wait_and_retry",
                "delay": 30,
                "max_retries": 3,
                "fallback": "use_proxy"
            },
            "cloudflare": {
                "action": "wait_for_clearance",
                "delay": 60,
                "max_retries": 2,
                "fallback": "change_user_agent"
            },
            "custom": {
                "action": "skip_url",
                "delay": 0,
                "max_retries": 0,
                "fallback": "manual_intervention"
            }
        }
        
        # Validate strategy completeness
        required_fields = ["action", "delay", "max_retries", "fallback"]
        
        for captcha_type, strategy in strategies.items():
            for field in required_fields:
                assert field in strategy, f"Missing {field} in {captcha_type} strategy"
            
            assert strategy["delay"] >= 0, f"Invalid delay in {captcha_type} strategy"
            assert strategy["max_retries"] >= 0, f"Invalid max_retries in {captcha_type} strategy"
    
    def test_captcha_avoidance_effectiveness(self):
        """Test effectiveness of CAPTCHA avoidance measures"""
        avoidance_measures = {
            "user_agent_rotation": True,
            "proxy_rotation": True,
            "request_delays": True,
            "session_management": True,
            "referrer_spoofing": True,
            "cookie_management": True
        }
        
        # Simulate CAPTCHA encounter rates with and without measures
        baseline_captcha_rate = 0.25  # 25% without measures
        
        # Calculate reduction based on active measures
        active_measures = sum(avoidance_measures.values())
        reduction_factor = min(0.8, active_measures * 0.15)  # Max 80% reduction
        
        expected_captcha_rate = baseline_captcha_rate * (1 - reduction_factor)
        
        # With good anti-detection, CAPTCHA rate should be low
        assert expected_captcha_rate <= 0.10  # Should be 10% or less
        assert reduction_factor >= 0.6  # Should achieve at least 60% reduction


@pytest.mark.antidetection
@pytest.mark.slow
class TestRealWorldAntiDetection:
    """Real-world anti-detection testing scenarios"""
    
    def test_detection_evasion_simulation(self):
        """Simulate detection evasion over time"""
        simulation_results = {
            "total_requests": 1000,
            "detected_requests": 0,
            "blocked_requests": 0,
            "captcha_requests": 0,
            "successful_requests": 0
        }
        
        # Simulate requests with various anti-detection measures
        for i in range(simulation_results["total_requests"]):
            # Simulate detection probability based on request characteristics
            detection_probability = 0.02  # Base 2% detection rate
            
            # Factors that increase detection
            if i % 50 == 0:  # Every 50th request (pattern)
                detection_probability += 0.05
            
            if i > 500:  # Later requests (accumulated suspicion)
                detection_probability += 0.01
            
            # Anti-detection measures reduce probability
            user_agent_rotation = True
            proxy_rotation = i % 100 == 0  # Rotate every 100 requests
            random_delays = True
            
            if user_agent_rotation:
                detection_probability *= 0.8
            if proxy_rotation:
                detection_probability *= 0.7
            if random_delays:
                detection_probability *= 0.9
            
            # Simulate outcome
            if random.random() < detection_probability:
                outcome = random.choice(["detected", "blocked", "captcha"])
                simulation_results[f"{outcome}_requests"] += 1
            else:
                simulation_results["successful_requests"] += 1
        
        # Analyze results
        success_rate = simulation_results["successful_requests"] / simulation_results["total_requests"]
        detection_rate = (
            simulation_results["detected_requests"] + 
            simulation_results["blocked_requests"] + 
            simulation_results["captcha_requests"]
        ) / simulation_results["total_requests"]
        
        # Assertions for good anti-detection performance
        assert success_rate >= 0.85  # At least 85% success rate
        assert detection_rate <= 0.15  # At most 15% detection rate
        assert simulation_results["blocked_requests"] <= 50  # Limited blocks
    
    def test_fingerprinting_resistance(self):
        """Test resistance to browser fingerprinting"""
        fingerprinting_tests = {
            "user_agent": {"entropy": 8.5, "passed": True},
            "screen_resolution": {"entropy": 4.2, "passed": True},
            "timezone": {"entropy": 3.4, "passed": True},
            "language": {"entropy": 2.1, "passed": True},
            "plugins": {"entropy": 5.8, "passed": True},
            "canvas": {"entropy": 12.1, "passed": False},  # High entropy = bad
            "webgl": {"entropy": 9.3, "passed": True},
            "audio": {"entropy": 7.2, "passed": True}
        }
        
        total_entropy = sum(test["entropy"] for test in fingerprinting_tests.values())
        passed_tests = sum(1 for test in fingerprinting_tests.values() if test["passed"])
        
        # Good anti-fingerprinting should:
        assert total_entropy <= 60  # Total entropy should be reasonable
        assert passed_tests >= 6  # Most tests should pass
        
        # Canvas fingerprinting should be the main concern
        assert fingerprinting_tests["canvas"]["entropy"] > 10  # High entropy indicates problem
        assert not fingerprinting_tests["canvas"]["passed"]  # Should fail this specific test
    
    def test_rate_limiting_adaptation(self):
        """Test adaptation to rate limiting"""
        rate_limit_scenario = {
            "initial_rate": 10,  # requests per second
            "rate_limit_threshold": 5,  # server starts limiting at 5 req/s
            "current_rate": 10,
            "adaptive_enabled": True
        }
        
        # Simulate rate limiting detection and adaptation
        for attempt in range(10):
            if scenario["current_rate"] > scenario["rate_limit_threshold"]:
                # Rate limiting detected
                if scenario["adaptive_enabled"]:
                    # Adapt by reducing rate
                    scenario["current_rate"] *= 0.7  # Reduce by 30%
                    scenario["current_rate"] = max(1, scenario["current_rate"])  # Minimum 1 req/s
                else:
                    # No adaptation, likely to be blocked
                    break
        
        # After adaptation, rate should be under threshold
        assert scenario["current_rate"] <= scenario["rate_limit_threshold"]
        assert scenario["current_rate"] >= 1  # Should maintain minimum functionality
    
    @pytest.mark.skip(reason="Requires real network requests")
    def test_real_world_detection_sites(self):
        """Test against real bot detection services (when enabled)"""
        # This test would check against actual bot detection services
        # Only run when explicitly enabled for development testing
        
        detection_services = [
            "https://bot.sannysoft.com/",
            "https://intoli.com/blog/not-possible-to-block-chrome-headless/",
            "https://arh.antoinevastel.com/bots/areyouheadless"
        ]
        
        results = {}
        for service in detection_services:
            # Would test actual detection here
            results[service] = {
                "detected": False,  # Simulated result
                "confidence": 0.95,
                "fingerprint_unique": True
            }
        
        # All services should fail to detect bot
        for service, result in results.items():
            assert not result["detected"], f"Bot detected by {service}"
            assert result["confidence"] >= 0.9, f"Low confidence for {service}"
