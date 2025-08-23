"""
Unit tests for BrowserManager and browser automation components.

Tests browser initialization, configuration, anti-detection measures,
and browser lifecycle management.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException

try:
    from src.infra.browser_manager import BrowserManager
    from src.infra.anti_detection_supervisor import AntiDetectionSupervisor
    from src.infra.proxy_manager import ProxyManager
    from src.infra.user_agent_manager import UserAgentManager
except ImportError:
    pytest.skip("Browser infrastructure modules not available", allow_module_level=True)


class TestBrowserManager:
    """Test BrowserManager functionality"""
    
    @pytest.fixture
    def mock_webdriver(self):
        """Mock WebDriver for testing"""
        with patch('src.infra.browser_manager.webdriver') as mock_wd:
            mock_driver = Mock()
            mock_driver.page_source = "<html><body>Test</body></html>"
            mock_driver.current_url = "https://example.com"
            mock_driver.title = "Test Page"
            mock_driver.get.return_value = None
            mock_driver.quit.return_value = None
            
            mock_wd.Chrome.return_value = mock_driver
            yield mock_wd, mock_driver
    
    @pytest.fixture
    def browser_config(self):
        """Basic browser configuration"""
        return {
            "headless": True,
            "window_size": "1920,1080",
            "user_agent": "Mozilla/5.0 (Test Browser)",
            "proxy": None,
            "timeout": 30,
            "page_load_strategy": "normal"
        }
    
    @pytest.fixture
    def browser_manager(self, browser_config, mock_webdriver):
        """Create BrowserManager instance with mocked WebDriver"""
        manager = BrowserManager(config=browser_config)
        return manager
    
    def test_browser_manager_initialization(self, browser_config):
        """Test BrowserManager initialization"""
        manager = BrowserManager(config=browser_config)
        
        assert manager.config == browser_config
        assert manager.driver is None
        assert not manager.is_active
    
    def test_chrome_options_configuration(self, browser_manager):
        """Test Chrome options are configured correctly"""
        options = browser_manager._create_chrome_options()
        
        assert isinstance(options, Options)
        # Verify common options are set
        option_args = options.arguments
        assert "--headless" in option_args
        assert any("--window-size=1920,1080" in arg for arg in option_args)
        assert "--no-sandbox" in option_args
        assert "--disable-dev-shm-usage" in option_args
    
    def test_driver_creation_success(self, browser_manager, mock_webdriver):
        """Test successful driver creation"""
        mock_wd, mock_driver = mock_webdriver
        
        driver = browser_manager.get_driver()
        
        assert driver == mock_driver
        assert browser_manager.driver == mock_driver
        assert browser_manager.is_active
        mock_wd.Chrome.assert_called_once()
    
    def test_driver_creation_failure(self, browser_manager):
        """Test driver creation failure handling"""
        with patch('src.infra.browser_manager.webdriver.Chrome') as mock_chrome:
            mock_chrome.side_effect = WebDriverException("Failed to start browser")
            
            with pytest.raises(WebDriverException):
                browser_manager.get_driver()
            
            assert browser_manager.driver is None
            assert not browser_manager.is_active
    
    def test_driver_reuse(self, browser_manager, mock_webdriver):
        """Test driver reuse when already created"""
        mock_wd, mock_driver = mock_webdriver
        
        # First call creates driver
        driver1 = browser_manager.get_driver()
        
        # Second call should return same driver
        driver2 = browser_manager.get_driver()
        
        assert driver1 == driver2
        assert driver1 == mock_driver
        # Chrome should only be called once
        mock_wd.Chrome.assert_called_once()
    
    def test_close_driver(self, browser_manager, mock_webdriver):
        """Test driver cleanup"""
        mock_wd, mock_driver = mock_webdriver
        
        # Create driver
        browser_manager.get_driver()
        assert browser_manager.is_active
        
        # Close driver
        browser_manager.close_driver()
        
        assert browser_manager.driver is None
        assert not browser_manager.is_active
        mock_driver.quit.assert_called_once()
    
    def test_close_driver_when_none(self, browser_manager):
        """Test closing driver when none exists"""
        # Should not raise exception
        browser_manager.close_driver()
        
        assert browser_manager.driver is None
        assert not browser_manager.is_active
    
    def test_context_manager(self, browser_manager, mock_webdriver):
        """Test BrowserManager as context manager"""
        mock_wd, mock_driver = mock_webdriver
        
        with browser_manager as driver:
            assert driver == mock_driver
            assert browser_manager.is_active
        
        # Should be closed after context
        assert browser_manager.driver is None
        assert not browser_manager.is_active
        mock_driver.quit.assert_called_once()
    
    def test_navigate_to_url(self, browser_manager, mock_webdriver):
        """Test URL navigation"""
        mock_wd, mock_driver = mock_webdriver
        
        url = "https://example.com/test"
        browser_manager.navigate_to(url)
        
        mock_driver.get.assert_called_once_with(url)
    
    def test_navigate_with_timeout(self, browser_manager, mock_webdriver):
        """Test URL navigation with timeout"""
        mock_wd, mock_driver = mock_webdriver
        mock_driver.get.side_effect = TimeoutException("Page load timeout")
        
        with pytest.raises(TimeoutException):
            browser_manager.navigate_to("https://slow-site.com", timeout=5)
    
    def test_get_page_source(self, browser_manager, mock_webdriver):
        """Test page source retrieval"""
        mock_wd, mock_driver = mock_webdriver
        expected_html = "<html><body>Test Content</body></html>"
        mock_driver.page_source = expected_html
        
        browser_manager.get_driver()  # Initialize driver
        html = browser_manager.get_page_source()
        
        assert html == expected_html
    
    def test_health_check_healthy(self, browser_manager, mock_webdriver):
        """Test health check for healthy browser"""
        mock_wd, mock_driver = mock_webdriver
        
        browser_manager.get_driver()
        assert browser_manager.is_healthy()
    
    def test_health_check_unhealthy(self, browser_manager, mock_webdriver):
        """Test health check for unhealthy browser"""
        mock_wd, mock_driver = mock_webdriver
        mock_driver.current_url = None  # Simulate crashed browser
        
        browser_manager.get_driver()
        assert not browser_manager.is_healthy()
    
    def test_restart_browser(self, browser_manager, mock_webdriver):
        """Test browser restart functionality"""
        mock_wd, mock_driver = mock_webdriver
        
        # Create initial browser
        browser_manager.get_driver()
        initial_driver = browser_manager.driver
        
        # Restart browser
        browser_manager.restart()
        
        # Should have new driver instance
        assert browser_manager.driver != initial_driver
        assert browser_manager.is_active
        
        # Old driver should be quit
        initial_driver.quit.assert_called_once()
    
    @pytest.mark.parametrize("proxy_config", [
        None,
        {"host": "proxy.example.com", "port": 8080},
        {"host": "proxy.example.com", "port": 8080, "username": "user", "password": "pass"}
    ])
    def test_proxy_configuration(self, proxy_config):
        """Test proxy configuration in browser options"""
        config = {
            "headless": True,
            "proxy": proxy_config
        }
        
        manager = BrowserManager(config=config)
        options = manager._create_chrome_options()
        
        if proxy_config:
            # Verify proxy arguments are present
            option_args = options.arguments
            proxy_arg = f"--proxy-server={proxy_config['host']}:{proxy_config['port']}"
            assert any(proxy_arg in arg for arg in option_args)
        else:
            # No proxy configuration should be present
            option_args = options.arguments
            assert not any("--proxy-server" in arg for arg in option_args)


class TestAntiDetectionSupervisor:
    """Test AntiDetectionSupervisor functionality"""
    
    @pytest.fixture
    def anti_detection_config(self):
        """Anti-detection configuration"""
        return {
            "user_agent_rotation": True,
            "viewport_randomization": True,
            "request_delays": True,
            "stealth_mode": True,
            "captcha_detection": True
        }
    
    @pytest.fixture
    def mock_driver(self):
        """Mock WebDriver for anti-detection testing"""
        driver = Mock()
        driver.execute_script.return_value = None
        driver.get.return_value = None
        driver.current_url = "https://example.com"
        driver.page_source = "<html><body>Normal page</body></html>"
        return driver
    
    @pytest.fixture
    def supervisor(self, anti_detection_config):
        """Create AntiDetectionSupervisor instance"""
        return AntiDetectionSupervisor(config=anti_detection_config)
    
    def test_supervisor_initialization(self, anti_detection_config):
        """Test supervisor initialization"""
        supervisor = AntiDetectionSupervisor(config=anti_detection_config)
        
        assert supervisor.config == anti_detection_config
        assert hasattr(supervisor, 'user_agent_manager')
        assert hasattr(supervisor, 'delay_manager')
    
    def test_apply_stealth_settings(self, supervisor, mock_driver):
        """Test stealth settings application"""
        supervisor.apply_stealth_settings(mock_driver)
        
        # Should call execute_script to apply stealth measures
        assert mock_driver.execute_script.called
        
        # Verify stealth scripts were executed
        script_calls = mock_driver.execute_script.call_args_list
        assert len(script_calls) > 0
    
    def test_random_delay(self, supervisor):
        """Test random delay generation"""
        start_time = time.time()
        
        # Test with minimum delay
        supervisor.random_delay(min_delay=0.01, max_delay=0.02)
        
        elapsed = time.time() - start_time
        assert elapsed >= 0.01
        assert elapsed <= 0.05  # Allow some tolerance
    
    def test_user_agent_rotation(self, supervisor):
        """Test user agent rotation"""
        ua1 = supervisor.get_random_user_agent()
        ua2 = supervisor.get_random_user_agent()
        
        # Should return user agent strings
        assert isinstance(ua1, str)
        assert isinstance(ua2, str)
        assert len(ua1) > 10
        assert len(ua2) > 10
        
        # May or may not be different (depends on pool size)
        # But should be valid user agent format
        assert "Mozilla" in ua1 or "Chrome" in ua1
    
    def test_captcha_detection(self, supervisor, mock_driver):
        """Test CAPTCHA detection"""
        # Normal page - no CAPTCHA
        mock_driver.page_source = "<html><body>Normal content</body></html>"
        assert not supervisor.detect_captcha(mock_driver)
        
        # Page with CAPTCHA indicators
        mock_driver.page_source = "<html><body><div id='captcha'>Please verify</div></body></html>"
        assert supervisor.detect_captcha(mock_driver)
        
        # Page with reCAPTCHA
        mock_driver.page_source = "<html><body><div class='g-recaptcha'></div></body></html>"
        assert supervisor.detect_captcha(mock_driver)
    
    def test_block_detection(self, supervisor, mock_driver):
        """Test blocking detection"""
        # Normal page
        mock_driver.page_source = "<html><body>Welcome to our site</body></html>"
        assert not supervisor.is_blocked(mock_driver)
        
        # Blocked page with common indicators
        blocked_pages = [
            "<html><body>Access Denied</body></html>",
            "<html><body>You have been blocked</body></html>",
            "<html><body>Error 403 Forbidden</body></html>",
            "<html><body>Bot detection activated</body></html>"
        ]
        
        for blocked_html in blocked_pages:
            mock_driver.page_source = blocked_html
            assert supervisor.is_blocked(mock_driver)
    
    def test_stealth_measures_integration(self, supervisor, mock_driver):
        """Test integrated stealth measures"""
        # Apply all stealth measures
        supervisor.apply_stealth_settings(mock_driver)
        supervisor.randomize_viewport(mock_driver)
        supervisor.disable_automation_indicators(mock_driver)
        
        # Verify multiple execute_script calls were made
        assert mock_driver.execute_script.call_count >= 3
        
        # Verify different types of scripts were executed
        script_calls = [call[0][0] for call in mock_driver.execute_script.call_args_list]
        assert any("navigator" in script for script in script_calls)
        assert any("window" in script for script in script_calls)
    
    def test_proxy_recommendation(self, supervisor):
        """Test proxy usage recommendation"""
        # Should recommend proxy for certain conditions
        assert isinstance(supervisor.should_use_proxy(), bool)
        
        # Test with blocked status
        recommendation = supervisor.should_use_proxy(blocked_count=5)
        assert isinstance(recommendation, bool)
        
        # High block count should recommend proxy
        if supervisor.config.get('adaptive_proxy', True):
            assert supervisor.should_use_proxy(blocked_count=10) == True


class TestUserAgentManager:
    """Test UserAgentManager functionality"""
    
    @pytest.fixture
    def ua_manager(self):
        """Create UserAgentManager instance"""
        return UserAgentManager()
    
    def test_ua_manager_initialization(self, ua_manager):
        """Test UserAgentManager initialization"""
        assert hasattr(ua_manager, 'user_agents')
        assert len(ua_manager.user_agents) > 0
    
    def test_get_random_user_agent(self, ua_manager):
        """Test random user agent selection"""
        ua = ua_manager.get_random_user_agent()
        
        assert isinstance(ua, str)
        assert len(ua) > 20  # Reasonable length for UA string
        assert "Mozilla" in ua or "Chrome" in ua
    
    def test_get_user_agent_by_browser(self, ua_manager):
        """Test user agent selection by browser type"""
        chrome_ua = ua_manager.get_user_agent_by_browser("chrome")
        firefox_ua = ua_manager.get_user_agent_by_browser("firefox")
        
        assert "Chrome" in chrome_ua
        assert "Firefox" in firefox_ua
    
    def test_user_agent_diversity(self, ua_manager):
        """Test user agent diversity"""
        uas = [ua_manager.get_random_user_agent() for _ in range(10)]
        
        # Should have some diversity (not all the same)
        unique_uas = set(uas)
        assert len(unique_uas) > 1  # At least some variation
    
    def test_mobile_user_agents(self, ua_manager):
        """Test mobile user agent selection"""
        mobile_ua = ua_manager.get_mobile_user_agent()
        
        assert isinstance(mobile_ua, str)
        assert any(keyword in mobile_ua.lower() for keyword in ['mobile', 'android', 'iphone'])


class TestProxyManager:
    """Test ProxyManager functionality"""
    
    @pytest.fixture
    def proxy_config(self):
        """Proxy configuration for testing"""
        return {
            "proxies": [
                {"host": "proxy1.example.com", "port": 8080},
                {"host": "proxy2.example.com", "port": 8080},
                {"host": "proxy3.example.com", "port": 3128, "username": "user", "password": "pass"}
            ],
            "rotation_strategy": "round_robin",
            "health_check": True
        }
    
    @pytest.fixture
    def proxy_manager(self, proxy_config):
        """Create ProxyManager instance"""
        return ProxyManager(config=proxy_config)
    
    def test_proxy_manager_initialization(self, proxy_manager, proxy_config):
        """Test ProxyManager initialization"""
        assert proxy_manager.config == proxy_config
        assert len(proxy_manager.proxies) == 3
    
    def test_get_next_proxy(self, proxy_manager):
        """Test proxy selection"""
        proxy1 = proxy_manager.get_next_proxy()
        proxy2 = proxy_manager.get_next_proxy()
        
        assert isinstance(proxy1, dict)
        assert isinstance(proxy2, dict)
        assert "host" in proxy1
        assert "port" in proxy1
        
        # With round-robin, should get different proxies
        assert proxy1 != proxy2
    
    def test_proxy_rotation(self, proxy_manager):
        """Test proxy rotation strategy"""
        # Get all proxies in sequence
        proxies = [proxy_manager.get_next_proxy() for _ in range(5)]
        
        # Should cycle through available proxies
        unique_proxies = {(p['host'], p['port']) for p in proxies}
        assert len(unique_proxies) <= 3  # Should not exceed available proxies
    
    def test_proxy_health_check(self, proxy_manager):
        """Test proxy health checking"""
        proxy = proxy_manager.get_next_proxy()
        
        # Mock health check
        with patch.object(proxy_manager, '_check_proxy_health') as mock_health:
            mock_health.return_value = True
            
            is_healthy = proxy_manager.check_proxy_health(proxy)
            assert is_healthy
            mock_health.assert_called_once_with(proxy)
    
    def test_proxy_formatting(self, proxy_manager):
        """Test proxy URL formatting"""
        proxy = {"host": "proxy.example.com", "port": 8080}
        url = proxy_manager.format_proxy_url(proxy)
        
        assert url == "http://proxy.example.com:8080"
        
        # Test with authentication
        auth_proxy = {
            "host": "proxy.example.com",
            "port": 8080,
            "username": "user",
            "password": "pass"
        }
        auth_url = proxy_manager.format_proxy_url(auth_proxy)
        assert auth_url == "http://user:pass@proxy.example.com:8080"


@pytest.mark.browser
class TestBrowserIntegration:
    """Integration tests for browser components"""
    
    @pytest.fixture
    def integrated_browser_manager(self):
        """Create browser manager with real anti-detection"""
        config = {
            "headless": True,
            "anti_detection": True,
            "stealth_mode": True
        }
        return BrowserManager(config=config)
    
    def test_browser_with_anti_detection(self, integrated_browser_manager):
        """Test browser with anti-detection measures"""
        if not integrated_browser_manager:
            pytest.skip("Browser manager not available")
        
        with integrated_browser_manager as driver:
            # Apply anti-detection measures
            integrated_browser_manager.apply_anti_detection(driver)
            
            # Verify browser is functional
            assert driver is not None
            assert hasattr(driver, 'get')
            assert hasattr(driver, 'page_source')
    
    def test_stealth_script_execution(self, integrated_browser_manager):
        """Test stealth script execution"""
        if not integrated_browser_manager:
            pytest.skip("Browser manager not available")
        
        with integrated_browser_manager as driver:
            # Execute stealth scripts
            result = driver.execute_script("return navigator.webdriver")
            
            # Should return None or undefined (not True)
            assert result is None or result == False
    
    @pytest.mark.slow
    def test_browser_performance_under_load(self, integrated_browser_manager):
        """Test browser performance under load"""
        if not integrated_browser_manager:
            pytest.skip("Browser manager not available")
        
        start_time = time.time()
        
        with integrated_browser_manager as driver:
            # Simulate multiple operations
            for i in range(10):
                driver.execute_script(f"return {i + 1}")
        
        duration = time.time() - start_time
        
        # Should complete operations efficiently
        assert duration < 5.0  # Less than 5 seconds
