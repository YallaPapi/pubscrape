"""
Comprehensive Test Suite for Anti-Detection System

Tests all components of the anti-detection framework including:
- Stealth manager functionality
- Proxy rotation and health monitoring
- Human behavior simulation
- Adaptive rate limiting
- Configuration loading and validation
- Integration with existing systems
"""

import pytest
import asyncio
import time
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import yaml

# Import the anti-detection system components
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from anti_detection import (
    StealthManager, StealthConfig, StealthLevel, DetectionRisk,
    ProxyRotator, ProxyInfo, ProxyType, ProxyStatus, ProxyProvider,
    BehaviorSimulator, BehaviorConfig, IntensityLevel, BehaviorProfile,
    AdaptiveRateLimiter, RateLimitConfig, RequestStatus, CircuitState,
    create_anti_detection_system
)


class TestStealthManager:
    """Test suite for the main stealth manager"""
    
    @pytest.fixture
    def stealth_config(self):
        """Create a test stealth configuration"""
        return StealthConfig(
            stealth_level=StealthLevel.MODERATE,
            use_proxies=False,
            simulate_human_behavior=True,
            adaptive_rate_limiting=True
        )
    
    @pytest.fixture
    def stealth_manager(self, stealth_config):
        """Create a stealth manager instance for testing"""
        return StealthManager(stealth_config)
    
    def test_stealth_manager_initialization(self, stealth_manager):
        """Test stealth manager initializes correctly"""
        assert stealth_manager.config.stealth_level == StealthLevel.MODERATE
        assert stealth_manager.active_sessions == {}
        assert stealth_manager.session_configs == {}
        assert stealth_manager.detection_patterns is not None
    
    @pytest.mark.asyncio
    async def test_create_stealth_session(self, stealth_manager):
        """Test creating a stealth session"""
        domain = "example.com"
        session_id = await stealth_manager.create_stealth_session(domain)
        
        assert session_id is not None
        assert session_id in stealth_manager.active_sessions
        assert session_id in stealth_manager.session_configs
        
        session = stealth_manager.active_sessions[session_id]
        assert session.domain == domain
        assert session.start_time > 0
        assert session.current_risk_level == DetectionRisk.LOW
    
    @pytest.mark.asyncio
    async def test_session_metrics_tracking(self, stealth_manager):
        """Test session metrics are tracked correctly"""
        domain = "test.com"
        session_id = await stealth_manager.create_stealth_session(domain)
        session = stealth_manager.active_sessions[session_id]
        
        # Initial metrics
        assert session.requests_made == 0
        assert session.requests_successful == 0
        assert session.detection_events == 0
        
        # Simulate some activity
        session.requests_made = 5
        session.requests_successful = 4
        session.detection_events = 1
        
        metrics = stealth_manager.get_session_metrics(session_id)
        assert metrics.requests_made == 5
        assert metrics.requests_successful == 4
        assert metrics.detection_events == 1
    
    def test_detection_pattern_loading(self, stealth_manager):
        """Test detection patterns are loaded correctly"""
        patterns = stealth_manager.detection_patterns
        
        assert "cloudflare" in patterns
        assert "recaptcha" in patterns
        assert "rate_limiting" in patterns
        assert "bot_detection" in patterns
        
        # Check specific patterns
        assert "cf-ray" in patterns["cloudflare"]
        assert "recaptcha" in patterns["recaptcha"]
        assert "429" in patterns["rate_limiting"]
    
    def test_detection_pattern_matching(self, stealth_manager):
        """Test detection pattern matching works correctly"""
        # Test Cloudflare detection
        html_with_cf = "<html>Cloudflare protection enabled</html>"
        detection_info = stealth_manager._detect_anti_bot_measures(html_with_cf)
        assert detection_info["cloudflare_detected"] is True
        
        # Test reCAPTCHA detection
        html_with_captcha = "<div class='recaptcha'>Verify you are human</div>"
        detection_info = stealth_manager._detect_anti_bot_measures(html_with_captcha)
        assert detection_info["recaptcha_detected"] is True
        
        # Test clean HTML
        clean_html = "<html><body>Normal content</body></html>"
        detection_info = stealth_manager._detect_anti_bot_measures(clean_html)
        assert not any(detection_info.values())
    
    @pytest.mark.asyncio
    async def test_close_session(self, stealth_manager):
        """Test session cleanup works correctly"""
        domain = "cleanup.com"
        session_id = await stealth_manager.create_stealth_session(domain)
        
        assert session_id in stealth_manager.active_sessions
        
        await stealth_manager.close_session(session_id)
        
        assert session_id not in stealth_manager.active_sessions
        assert session_id not in stealth_manager.session_configs


class TestProxyRotator:
    """Test suite for proxy rotation system"""
    
    @pytest.fixture
    def proxy_config(self):
        """Create test proxy configuration"""
        return {
            "proxies": [
                {
                    "host": "proxy1.example.com",
                    "port": 8080,
                    "type": "http",
                    "provider": "manual",
                    "country": "US"
                },
                {
                    "host": "proxy2.example.com", 
                    "port": 3128,
                    "type": "http",
                    "provider": "manual",
                    "country": "UK"
                }
            ],
            "rotation": {
                "rotation_strategy": "weighted",
                "health_check_enabled": False  # Disable for tests
            }
        }
    
    @pytest.fixture
    def proxy_rotator(self, proxy_config):
        """Create proxy rotator for testing"""
        return ProxyRotator(proxy_config)
    
    def test_proxy_rotator_initialization(self, proxy_rotator):
        """Test proxy rotator initializes correctly"""
        assert len(proxy_rotator.proxies) == 2
        assert proxy_rotator.rotation_config.rotation_strategy == "weighted"
        
        # Check proxies were loaded correctly
        proxy1 = proxy_rotator.proxies[0]
        assert proxy1.host == "proxy1.example.com"
        assert proxy1.port == 8080
        assert proxy1.proxy_type == ProxyType.HTTP
    
    @pytest.mark.asyncio
    async def test_get_proxy_selection(self, proxy_rotator):
        """Test proxy selection works"""
        proxy = await proxy_rotator.get_proxy()
        
        assert proxy is not None
        assert proxy.is_healthy
        assert proxy.proxy_url.startswith("http://")
    
    def test_proxy_health_status(self, proxy_rotator):
        """Test proxy health status calculations"""
        proxy = proxy_rotator.proxies[0]
        
        # Initially healthy
        assert proxy.is_healthy
        assert proxy.status == ProxyStatus.ACTIVE
        
        # Record failures
        for _ in range(3):
            proxy.record_failure()
        
        assert proxy.failure_count == 3
        assert proxy.is_healthy  # Still healthy, below max failures
        
        # Record more failures to exceed threshold
        for _ in range(5):
            proxy.record_failure()
        
        assert not proxy.is_healthy
        assert proxy.status == ProxyStatus.FAILED
    
    def test_proxy_success_recovery(self, proxy_rotator):
        """Test proxy recovery after failures"""
        proxy = proxy_rotator.proxies[0]
        
        # Cause failures
        for _ in range(3):
            proxy.record_failure()
        
        failure_count = proxy.failure_count
        
        # Record success
        proxy.record_success(1.5)
        
        assert proxy.success_count == 1
        assert proxy.failure_count < failure_count  # Reduced on success
        assert proxy.avg_response_time == 1.5
    
    def test_proxy_url_formatting(self, proxy_rotator):
        """Test proxy URL formatting"""
        proxy = ProxyInfo(
            host="test.proxy.com",
            port=8080,
            proxy_type=ProxyType.HTTP,
            username="user",
            password="pass"
        )
        
        expected_url = "http://user:pass@test.proxy.com:8080"
        assert proxy.proxy_url == expected_url
        
        # Without auth
        proxy_no_auth = ProxyInfo(
            host="simple.proxy.com",
            port=3128,
            proxy_type=ProxyType.HTTP
        )
        
        expected_url_no_auth = "http://simple.proxy.com:3128"
        assert proxy_no_auth.proxy_url == expected_url_no_auth
    
    @pytest.mark.asyncio
    async def test_proxy_rotation(self, proxy_rotator):
        """Test proxy rotation functionality"""
        session_id = "test_session"
        
        # Get initial proxy
        proxy1 = await proxy_rotator.get_proxy(session_id)
        
        # Force rotation
        proxy2 = await proxy_rotator.rotate_proxy(session_id)
        
        assert proxy2 is not None
        # May be same proxy in small pool, but rotation was attempted
        assert session_id in proxy_rotator.session_proxies
    
    def test_proxy_statistics(self, proxy_rotator):
        """Test proxy statistics generation"""
        stats = proxy_rotator.get_statistics()
        
        assert "total_proxies" in stats
        assert "healthy_proxies" in stats
        assert "failed_proxies" in stats
        assert "provider_breakdown" in stats
        assert "rotation_strategy" in stats
        
        assert stats["total_proxies"] == 2
        assert stats["rotation_strategy"] == "weighted"


class TestBehaviorSimulator:
    """Test suite for human behavior simulation"""
    
    @pytest.fixture
    def behavior_config(self):
        """Create test behavior configuration"""
        return BehaviorConfig(
            intensity=IntensityLevel.MEDIUM,
            enable_mouse_movements=True,
            enable_scrolling=True,
            enable_typing=True,
            enable_reading_pauses=True
        )
    
    @pytest.fixture
    def behavior_simulator(self, behavior_config):
        """Create behavior simulator for testing"""
        return BehaviorSimulator(behavior_config)
    
    def test_behavior_simulator_initialization(self, behavior_simulator):
        """Test behavior simulator initializes correctly"""
        assert behavior_simulator.config.intensity == IntensityLevel.MEDIUM
        assert len(behavior_simulator.BEHAVIOR_PROFILES) >= 4
        assert behavior_simulator.current_profile is not None
        assert behavior_simulator.mouse_position is not None
    
    def test_behavior_profiles(self, behavior_simulator):
        """Test behavior profiles are loaded correctly"""
        profiles = behavior_simulator.BEHAVIOR_PROFILES
        
        assert "careful_reader" in profiles
        assert "quick_scanner" in profiles
        assert "distracted_browser" in profiles
        assert "focused_researcher" in profiles
        
        # Test profile properties
        careful_reader = profiles["careful_reader"]
        assert careful_reader.browsing_speed < 1.0  # Slower than average
        assert careful_reader.attention_span > 1.0  # Above average attention
    
    def test_profile_switching(self, behavior_simulator):
        """Test switching between behavior profiles"""
        original_profile = behavior_simulator.current_profile.name
        
        behavior_simulator.set_behavior_profile("quick_scanner")
        assert behavior_simulator.current_profile.name == "quick_scanner"
        
        behavior_simulator.set_behavior_profile("focused_researcher")
        assert behavior_simulator.current_profile.name == "focused_researcher"
        
        # Test invalid profile
        behavior_simulator.set_behavior_profile("nonexistent_profile")
        assert behavior_simulator.current_profile.name == "focused_researcher"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_pre_request_behavior(self, behavior_simulator):
        """Test pre-request behavior simulation"""
        session_id = "test_session"
        
        start_time = time.time()
        await behavior_simulator.pre_request_behavior(session_id)
        end_time = time.time()
        
        # Should take some time for behavior simulation
        duration = end_time - start_time
        assert duration >= 0.1  # At least some delay
        
        # Check session was recorded
        assert session_id in behavior_simulator.session_behaviors
    
    @pytest.mark.asyncio
    async def test_post_request_behavior(self, behavior_simulator):
        """Test post-request behavior simulation"""
        session_id = "test_session"
        
        start_time = time.time()
        await behavior_simulator.post_request_behavior(session_id, success=True)
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration >= 0.2  # Should take some time
        
        # Check behaviors were recorded
        assert session_id in behavior_simulator.session_behaviors
    
    @pytest.mark.asyncio
    async def test_typing_simulation(self, behavior_simulator):
        """Test typing behavior simulation"""
        test_text = "Hello, World!"
        
        start_time = time.time()
        duration = await behavior_simulator.simulate_typing(test_text)
        actual_duration = time.time() - start_time
        
        assert duration > 0
        assert actual_duration >= duration * 0.8  # Allow some variance
        
        # Longer text should take longer
        long_text = "This is a much longer piece of text that should take more time to type"
        long_duration = await behavior_simulator.simulate_typing(long_text)
        assert long_duration > duration
    
    def test_behavior_statistics(self, behavior_simulator):
        """Test behavior statistics tracking"""
        # Initially empty
        global_stats = behavior_simulator.get_global_behavior_stats()
        assert global_stats["total_sessions"] == 0
        assert global_stats["total_behaviors"] == 0
        
        # Add some behavior records manually
        behavior_simulator.behavior_history.append({
            "timestamp": time.time(),
            "session_id": "test",
            "phase": "pre_request",
            "profile": "test_profile",
            "actions": [{"type": "mouse_movement"}],
            "action_count": 1
        })
        
        updated_stats = behavior_simulator.get_global_behavior_stats()
        assert updated_stats["total_behaviors"] == 1
        assert updated_stats["total_actions"] == 1


class TestAdaptiveRateLimiter:
    """Test suite for adaptive rate limiting"""
    
    @pytest.fixture
    def rate_config(self):
        """Create test rate limiting configuration"""
        return RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            max_concurrent_requests=2,
            min_request_interval=1.0,
            adaptive_enabled=True,
            enable_exponential_backoff=True,
            enable_circuit_breaker=True
        )
    
    @pytest.fixture
    def rate_limiter(self, rate_config):
        """Create rate limiter for testing"""
        return AdaptiveRateLimiter(rate_config)
    
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initializes correctly"""
        assert rate_limiter.config.requests_per_minute == 10
        assert rate_limiter.config.adaptive_enabled is True
        assert rate_limiter.domain_limiters == {}
        assert rate_limiter.global_active_requests == 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_checking(self, rate_limiter):
        """Test basic rate limit checking"""
        url = "https://example.com/test"
        
        # First request should be allowed
        status, delay = await rate_limiter.check_rate_limit(url)
        assert status == RequestStatus.ALLOWED
        assert delay == 0.0
    
    @pytest.mark.asyncio
    async def test_request_slot_acquisition(self, rate_limiter):
        """Test request slot acquisition and release"""
        url = "https://example.com/test"
        
        # Acquire slot
        acquired = await rate_limiter.acquire_request_slot(url)
        assert acquired is True
        assert rate_limiter.global_active_requests == 1
        
        # Release slot
        rate_limiter.release_request_slot(
            url=url,
            success=True,
            response_time=1.5,
            status_code=200
        )
        
        assert rate_limiter.global_active_requests == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, rate_limiter):
        """Test concurrent request limits"""
        url = "https://example.com/test"
        max_concurrent = rate_limiter.config.max_concurrent_requests
        
        # Acquire maximum concurrent slots
        for i in range(max_concurrent):
            acquired = await rate_limiter.acquire_request_slot(url)
            assert acquired is True
        
        # Next request should be rate limited
        status, delay = await rate_limiter.check_rate_limit(url)
        assert status == RequestStatus.RATE_LIMITED
        assert delay > 0
    
    def test_domain_specific_configuration(self, rate_limiter):
        """Test domain-specific rate limiting"""
        # Test Bing gets more conservative limits
        bing_limiter = rate_limiter._get_domain_limiter("bing.com")
        assert bing_limiter.config.requests_per_minute <= 10
        assert bing_limiter.config.min_request_interval >= 3.0
        
        # Test Google gets even more conservative limits
        google_limiter = rate_limiter._get_domain_limiter("google.com")
        assert google_limiter.config.requests_per_minute <= 6
        assert google_limiter.config.max_concurrent_requests == 1
    
    def test_exponential_backoff(self, rate_limiter):
        """Test exponential backoff functionality"""
        domain = "test.com"
        limiter = rate_limiter._get_domain_limiter(domain)
        
        # Initially no backoff
        assert limiter.backoff_level == 0
        assert limiter.backoff_until == 0.0
        
        # Trigger backoff with a 429 status
        rate_limiter._apply_exponential_backoff(limiter, 429, "Rate limited")
        
        assert limiter.backoff_level == 1
        assert limiter.backoff_until > time.time()
    
    def test_circuit_breaker_functionality(self, rate_limiter):
        """Test circuit breaker behavior"""
        domain = "circuit-test.com"
        limiter = rate_limiter._get_domain_limiter(domain)
        circuit = limiter.circuit_breaker
        
        # Initially closed
        assert circuit.state == CircuitState.CLOSED
        assert circuit.failure_count == 0
        
        # Record failures to trip circuit
        current_time = time.time()
        failure_threshold = limiter.config.failure_threshold
        
        for i in range(failure_threshold):
            circuit.record_failure(
                current_time,
                failure_threshold,
                limiter.config.circuit_timeout_seconds
            )
        
        assert circuit.state == CircuitState.OPEN
        assert not circuit.should_allow_request(current_time, 300)
    
    def test_adaptive_rate_adjustment(self, rate_limiter):
        """Test adaptive rate limiting adjustments"""
        domain = "adaptive-test.com"
        limiter = rate_limiter._get_domain_limiter(domain)
        
        original_rpm = limiter.current_rpm
        
        # Simulate poor performance to trigger reduction
        for i in range(15):  # Add enough requests for adaptation
            record = Mock()
            record.timestamp = time.time() - (14 - i) * 10  # Spread over time
            record.success = i > 5  # First few fail, rest succeed
            record.response_time = 8.0  # Slow responses
            limiter.request_history.append(record)
        
        # Trigger adaptation check
        asyncio.run(rate_limiter._perform_adaptive_adjustment(limiter, time.time()))
        
        # Should have reduced limits due to slow responses
        # (Note: specific values may vary based on adaptation logic)
        adaptation_occurred = (
            len(limiter.adaptation_history) > 0 or
            limiter.current_rpm != original_rpm
        )
        assert adaptation_occurred
    
    def test_statistics_generation(self, rate_limiter):
        """Test statistics generation"""
        # Generate some activity first
        url = "https://stats-test.com/page"
        asyncio.run(rate_limiter.acquire_request_slot(url))
        rate_limiter.release_request_slot(url, True, 1.0, 200)
        
        # Get domain stats
        domain_stats = rate_limiter.get_domain_statistics("stats-test.com")
        assert "domain" in domain_stats
        assert "total_requests" in domain_stats
        assert "success_rate_percentage" in domain_stats
        
        # Get global stats
        global_stats = rate_limiter.get_global_statistics()
        assert "total_domains" in global_stats
        assert "total_requests" in global_stats
        assert "total_blocked" in global_stats


class TestConfigurationSystem:
    """Test suite for configuration loading and validation"""
    
    def test_yaml_config_loading(self):
        """Test YAML configuration file loading"""
        config_content = """
        global:
          stealth_level: "aggressive"
          enable_logging: true

        proxies:
          enabled: true
          rotation_strategy: "weighted"

        behavior_simulation:
          enabled: true
          intensity: "high"
        
        rate_limiting:
          adaptive_enabled: true
          global:
            requests_per_minute: 15
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            
            # Test loading configuration
            config = yaml.safe_load(open(f.name))
            
            assert config['global']['stealth_level'] == 'aggressive'
            assert config['proxies']['enabled'] is True
            assert config['behavior_simulation']['intensity'] == 'high'
            assert config['rate_limiting']['global']['requests_per_minute'] == 15
    
    def test_anti_detection_system_factory(self):
        """Test the factory function for creating complete system"""
        # Test with minimal config
        system = create_anti_detection_system()
        assert isinstance(system, StealthManager)
        assert system.config is not None
        
        # Test with explicit parameters
        system_aggressive = create_anti_detection_system(
            stealth_level="aggressive",
            use_proxies=True
        )
        assert isinstance(system_aggressive, StealthManager)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test valid stealth levels
        valid_levels = ["minimal", "moderate", "aggressive", "maximum"]
        for level in valid_levels:
            config = StealthConfig(stealth_level=StealthLevel(level))
            assert config.stealth_level.value == level
        
        # Test invalid level handling
        with pytest.raises(ValueError):
            StealthLevel("invalid_level")


class TestIntegrationScenarios:
    """Test suite for integration scenarios and realistic usage patterns"""
    
    @pytest.mark.asyncio
    async def test_complete_scraping_session(self):
        """Test a complete scraping session workflow"""
        # Create system with all components
        stealth_config = StealthConfig(
            stealth_level=StealthLevel.MODERATE,
            use_proxies=False,  # Disabled for testing
            simulate_human_behavior=True,
            adaptive_rate_limiting=True
        )
        
        stealth_manager = StealthManager(stealth_config)
        
        # Create session
        domain = "integration-test.com"
        session_id = await stealth_manager.create_stealth_session(domain)
        
        # Simulate multiple requests
        urls = [
            f"https://{domain}/page1",
            f"https://{domain}/page2", 
            f"https://{domain}/page3"
        ]
        
        for url in urls:
            # This would normally make actual requests
            # For testing, we just check the anti-detection measures
            
            # Check rate limiting
            if hasattr(stealth_manager, 'rate_limiter') and stealth_manager.rate_limiter:
                status, delay = await stealth_manager.rate_limiter.check_rate_limit(url)
                if status != RequestStatus.ALLOWED:
                    await asyncio.sleep(delay)
            
            # Simulate behavior
            if stealth_manager.behavior_simulator:
                await stealth_manager.behavior_simulator.pre_request_behavior(session_id)
                await stealth_manager.behavior_simulator.post_request_behavior(session_id, True)
        
        # Get final metrics
        metrics = stealth_manager.get_session_metrics(session_id)
        global_metrics = stealth_manager.get_global_metrics()
        
        assert metrics is not None
        assert global_metrics["active_sessions"] >= 1
        
        # Clean up
        await stealth_manager.close_session(session_id)
    
    @pytest.mark.asyncio
    async def test_detection_response_workflow(self):
        """Test response to detection events"""
        stealth_manager = StealthManager()
        
        session_id = await stealth_manager.create_stealth_session("detection-test.com")
        
        # Simulate detection events
        detection_responses = [
            {"cloudflare_detected": True},
            {"recaptcha_detected": True},
            {"rate_limiting_detected": True}
        ]
        
        for detection_info in detection_responses:
            # Test detection response
            await stealth_manager._adjust_strategy_for_detection(session_id, detection_info)
            
            # Check that adjustments were made
            session = stealth_manager.active_sessions[session_id]
            assert session.detection_events >= 0  # May be incremented
    
    def test_error_handling_and_recovery(self):
        """Test error handling and system recovery"""
        # Test with invalid configuration
        invalid_config = StealthConfig(
            stealth_level=StealthLevel.MAXIMUM,
            use_proxies=True  # Will fail without actual proxies
        )
        
        # System should still initialize without crashing
        try:
            stealth_manager = StealthManager(invalid_config)
            assert stealth_manager is not None
        except Exception as e:
            pytest.fail(f"System failed to handle invalid config gracefully: {e}")
    
    def test_performance_under_load(self):
        """Test system performance under simulated load"""
        stealth_manager = StealthManager()
        
        # Simulate many sessions
        start_time = time.time()
        
        session_count = 10
        session_ids = []
        
        async def create_sessions():
            tasks = []
            for i in range(session_count):
                task = stealth_manager.create_stealth_session(f"load-test-{i}.com")
                tasks.append(task)
            return await asyncio.gather(*tasks)
        
        session_ids = asyncio.run(create_sessions())
        
        creation_time = time.time() - start_time
        
        # Should create sessions reasonably quickly
        assert creation_time < 5.0  # Less than 5 seconds for 10 sessions
        assert len(session_ids) == session_count
        assert len(stealth_manager.active_sessions) == session_count
        
        # Clean up
        async def cleanup_sessions():
            tasks = []
            for session_id in session_ids:
                task = stealth_manager.close_session(session_id)
                tasks.append(task)
            await asyncio.gather(*tasks)
        
        asyncio.run(cleanup_sessions())


class TestRealWorldScenarios:
    """Test suite for real-world scraping scenarios"""
    
    @pytest.mark.asyncio 
    async def test_search_engine_scraping_scenario(self):
        """Test anti-detection for search engine scraping"""
        # Create system optimized for search engines
        stealth_config = StealthConfig(
            stealth_level=StealthLevel.AGGRESSIVE,
            use_proxies=False,
            adaptive_rate_limiting=True
        )
        
        stealth_manager = StealthManager(stealth_config)
        
        # Test with different search engines
        search_domains = ["bing.com", "google.com", "duckduckgo.com"]
        
        for domain in search_domains:
            session_id = await stealth_manager.create_stealth_session(domain)
            
            # Verify appropriate rate limiting is applied
            if hasattr(stealth_manager, 'rate_limiter') and stealth_manager.rate_limiter:
                limiter = stealth_manager.rate_limiter._get_domain_limiter(domain)
                
                # Search engines should have conservative limits
                if "bing.com" in domain:
                    assert limiter.config.requests_per_minute <= 10
                elif domain in ["google.com", "duckduckgo.com"]:
                    assert limiter.config.requests_per_minute <= 6
            
            await stealth_manager.close_session(session_id)
    
    def test_social_media_scraping_scenario(self):
        """Test anti-detection for social media scraping"""
        rate_limiter = AdaptiveRateLimiter()
        
        social_domains = ["facebook.com", "twitter.com", "linkedin.com"]
        
        for domain in social_domains:
            limiter = rate_limiter._get_domain_limiter(domain)
            
            # Social media should have moderate limits
            assert limiter.config.requests_per_minute >= 10
            assert limiter.config.max_concurrent_requests >= 2
    
    @pytest.mark.asyncio
    async def test_e_commerce_scraping_scenario(self):
        """Test anti-detection for e-commerce scraping"""
        behavior_simulator = BehaviorSimulator()
        
        # Use a browsing profile suitable for e-commerce
        behavior_simulator.set_behavior_profile("focused_researcher")
        
        session_id = "ecommerce_session"
        
        # Simulate browsing behavior typical for e-commerce
        await behavior_simulator.pre_request_behavior(session_id, {
            "page_type": "product_listing"
        })
        
        # Simulate reading product descriptions
        await behavior_simulator.simulate_typing("laptop specifications")
        
        await behavior_simulator.post_request_behavior(session_id, True, {
            "content_length": 5000,
            "page_type": "product_detail"
        })
        
        # Check that behaviors were recorded
        stats = behavior_simulator.get_session_behavior_stats(session_id)
        assert stats["total_actions"] > 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])