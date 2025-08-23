"""
Pytest configuration and fixtures for the scraper testing framework.

Provides common fixtures, test data, and configuration for all test modules.
Includes mock objects, sample data, and test utilities.
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Import project modules
try:
    from src.core.base_agent import BaseAgent, AgentConfig
    from src.infra.browser_manager import BrowserManager
    from src.infra.anti_detection_supervisor import AntiDetectionSupervisor
    from src.agents.bing_navigator_agent import BingNavigatorAgent
    from src.agents.serp_parser_agent import SerpParserAgent
    from src.agents.email_extractor_agent import EmailExtractorAgent
except ImportError:
    # Handle case where modules might not be available
    BaseAgent = None
    BrowserManager = None


# Test Configuration
@pytest.fixture(scope="session")
def test_config():
    """Global test configuration"""
    return {
        "test_data_dir": Path(__file__).parent / "fixtures",
        "output_dir": Path(tempfile.mkdtemp(prefix="scraper_test_")),
        "max_test_duration": 300,  # 5 minutes
        "browser_timeout": 30,
        "api_timeout": 10,
        "enable_real_requests": os.getenv("ENABLE_REAL_REQUESTS", "false").lower() == "true",
        "test_proxy": os.getenv("TEST_PROXY", None),
        "debug_mode": os.getenv("DEBUG_TESTS", "false").lower() == "true"
    }


# Fixture Data Loaders
@pytest.fixture
def bing_html_sample():
    """Load Bing Maps sample HTML"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "bing_maps_samples.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def google_html_sample():
    """Load Google Maps sample HTML"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "google_maps_samples.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def medical_practice_html():
    """Load medical practice website HTML"""
    fixtures_dir = Path(__file__).parent / "fixtures" / "business_websites"
    with open(fixtures_dir / "medical_practice.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def law_firm_html():
    """Load law firm website HTML"""
    fixtures_dir = Path(__file__).parent / "fixtures" / "business_websites"
    with open(fixtures_dir / "law_firm.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def restaurant_html():
    """Load restaurant website HTML"""
    fixtures_dir = Path(__file__).parent / "fixtures" / "business_websites"
    with open(fixtures_dir / "restaurant.html", "r", encoding="utf-8") as f:
        return f.read()


# Mock Objects and Test Doubles
@pytest.fixture
def mock_browser_manager():
    """Mock BrowserManager for testing"""
    mock_manager = Mock(spec=BrowserManager)
    
    # Configure mock driver
    mock_driver = Mock(spec=webdriver.Chrome)
    mock_driver.get.return_value = None
    mock_driver.page_source = "<html><body>Test Page</body></html>"
    mock_driver.current_url = "https://example.com"
    mock_driver.title = "Test Page"
    
    mock_manager.get_driver.return_value = mock_driver
    mock_manager.close_driver.return_value = None
    mock_manager.is_healthy.return_value = True
    
    return mock_manager


@pytest.fixture
def mock_anti_detection():
    """Mock AntiDetectionSupervisor"""
    mock_ad = Mock(spec=AntiDetectionSupervisor)
    
    mock_ad.apply_stealth_settings.return_value = None
    mock_ad.random_delay.return_value = None
    mock_ad.should_use_proxy.return_value = False
    mock_ad.get_random_user_agent.return_value = "Mozilla/5.0 (Test Agent)"
    mock_ad.is_blocked.return_value = False
    mock_ad.handle_captcha.return_value = True
    
    return mock_ad


@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return [
        {
            "title": "Northwestern Medicine - Chicago Locations",
            "url": "https://www.nm.org/locations/chicago",
            "snippet": "Find doctors and medical specialists in Chicago.",
            "contact_info": {
                "phone": "(312) 926-2000",
                "email": "info@nm.org"
            }
        },
        {
            "title": "Rush University Medical Center",
            "url": "https://www.rush.edu/patients-visitors/find-doctor",
            "snippet": "Search for doctors and medical professionals.",
            "contact_info": {
                "phone": "(312) 942-5000",
                "email": "physicians@rush.edu"
            }
        }
    ]


@pytest.fixture
def sample_extracted_emails():
    """Sample extracted email data"""
    return [
        {
            "email": "info@chicagopremiermedicine.com",
            "domain": "chicagopremiermedicine.com",
            "business_name": "Chicago Premier Medical Associates",
            "contact_type": "general",
            "validation_status": "valid",
            "source_url": "https://chicagopremiermedicine.com/contact",
            "extraction_confidence": 0.95
        },
        {
            "email": "dr.johnson@chicagopremiermedicine.com",
            "domain": "chicagopremiermedicine.com",
            "business_name": "Chicago Premier Medical Associates",
            "contact_type": "direct",
            "validation_status": "valid",
            "source_url": "https://chicagopremiermedicine.com/doctors",
            "extraction_confidence": 0.98
        }
    ]


@pytest.fixture
def sample_campaign_config():
    """Sample campaign configuration"""
    return {
        "name": "test_campaign",
        "target_industry": "healthcare",
        "target_locations": ["Chicago, IL", "Houston, TX"],
        "search_queries": [
            "doctors in {location} contact",
            "medical practice {location} email"
        ],
        "max_results_per_query": 50,
        "enable_email_validation": True,
        "output_format": "csv",
        "anti_detection_level": "medium"
    }


# Performance Testing Fixtures
@pytest.fixture
def performance_metrics():
    """Initialize performance metrics tracking"""
    return {
        "start_time": datetime.now(),
        "requests_made": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "total_results": 0,
        "memory_usage": [],
        "response_times": []
    }


@pytest.fixture
def benchmark_thresholds():
    """Performance benchmark thresholds"""
    return {
        "max_response_time": 5.0,  # seconds
        "min_success_rate": 0.95,  # 95%
        "max_memory_usage": 500,  # MB
        "max_cpu_usage": 80,  # percentage
        "max_results_per_second": 10,
        "min_data_quality_score": 0.90
    }


# Data Quality Fixtures
@pytest.fixture
def data_quality_rules():
    """Data quality validation rules"""
    return {
        "email_validation": {
            "required_format": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "min_confidence": 0.8,
            "blacklisted_domains": ["example.com", "test.com"],
            "required_mx_record": True
        },
        "business_data": {
            "required_fields": ["name", "contact_info"],
            "min_contact_methods": 1,
            "valid_phone_formats": [r"\(\d{3}\) \d{3}-\d{4}", r"\d{3}-\d{3}-\d{4}"],
            "min_address_length": 10
        },
        "url_validation": {
            "valid_schemes": ["http", "https"],
            "exclude_patterns": ["javascript:", "mailto:", "tel:"],
            "max_redirect_depth": 3
        }
    }


# Testing Utilities
@pytest.fixture
def test_logger():
    """Test-specific logger configuration"""
    import logging
    logger = logging.getLogger("test_scraper")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


@pytest.fixture
def temp_output_dir(test_config):
    """Temporary directory for test outputs"""
    output_dir = test_config["output_dir"]
    output_dir.mkdir(exist_ok=True)
    yield output_dir
    
    # Cleanup after test
    import shutil
    if output_dir.exists():
        shutil.rmtree(output_dir)


# Browser Testing Fixtures
@pytest.fixture
def headless_browser_options():
    """Chrome options for headless testing"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Test Browser)")
    return options


@pytest.fixture
def test_webdriver(headless_browser_options):
    """WebDriver instance for browser tests"""
    if os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true":
        pytest.skip("Browser tests disabled")
    
    try:
        driver = webdriver.Chrome(options=headless_browser_options)
        driver.implicitly_wait(10)
        yield driver
    except Exception as e:
        pytest.skip(f"WebDriver not available: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()


# API Mocking Fixtures
@pytest.fixture
def mock_requests_session():
    """Mock requests session for API testing"""
    with patch('requests.Session') as mock_session:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.text = "<html>Mock Response</html>"
        mock_response.headers = {"Content-Type": "text/html"}
        
        mock_session.return_value.get.return_value = mock_response
        mock_session.return_value.post.return_value = mock_response
        
        yield mock_session


# Data Validation Fixtures
@pytest.fixture
def email_validator():
    """Email validation utility"""
    import re
    
    def validate_email(email: str) -> Dict[str, Any]:
        """Validate email format and structure"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        
        result = {
            "email": email,
            "is_valid": bool(re.match(email_pattern, email)),
            "format_score": 0.0,
            "domain": "",
            "local_part": ""
        }
        
        if "@" in email:
            local, domain = email.split("@", 1)
            result["domain"] = domain
            result["local_part"] = local
            result["format_score"] = 1.0 if result["is_valid"] else 0.5
        
        return result
    
    return validate_email


# Test Markers and Parametrization
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )
    config.addinivalue_line(
        "markers", "browser: marks tests that require a browser"
    )
    config.addinivalue_line(
        "markers", "network: marks tests that require network access"
    )
    config.addinivalue_line(
        "markers", "antidetection: marks anti-detection validation tests"
    )


# Cleanup and Teardown
@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Automatically cleanup test artifacts after each test"""
    yield
    
    # Clean up any temporary files or data created during tests
    temp_files = Path.cwd().glob("test_*.tmp")
    for temp_file in temp_files:
        try:
            temp_file.unlink()
        except (OSError, PermissionError):
            pass


# Test Data Factories
class TestDataFactory:
    """Factory for creating test data objects"""
    
    @staticmethod
    def create_search_result(title: str = "Test Result", 
                           url: str = "https://test.com",
                           **kwargs) -> Dict[str, Any]:
        """Create a mock search result"""
        return {
            "title": title,
            "url": url,
            "snippet": kwargs.get("snippet", "Test snippet"),
            "contact_info": kwargs.get("contact_info", {}),
            "extraction_time": datetime.now().isoformat(),
            "source": kwargs.get("source", "test")
        }
    
    @staticmethod
    def create_email_data(email: str, **kwargs) -> Dict[str, Any]:
        """Create mock email extraction data"""
        return {
            "email": email,
            "domain": email.split("@")[1] if "@" in email else "",
            "business_name": kwargs.get("business_name", "Test Business"),
            "contact_type": kwargs.get("contact_type", "general"),
            "validation_status": kwargs.get("validation_status", "unknown"),
            "source_url": kwargs.get("source_url", "https://test.com"),
            "extraction_confidence": kwargs.get("extraction_confidence", 0.8)
        }


@pytest.fixture
def test_data_factory():
    """Provide test data factory"""
    return TestDataFactory


# Performance Monitoring
@pytest.fixture
def performance_monitor():
    """Monitor test performance metrics"""
    import psutil
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            self.metrics = []
        
        def record_metric(self, name: str, value: float):
            self.metrics.append({
                "name": name,
                "value": value,
                "timestamp": time.time() - self.start_time
            })
        
        def get_summary(self) -> Dict[str, Any]:
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            return {
                "duration": time.time() - self.start_time,
                "memory_usage": current_memory - self.start_memory,
                "metrics_count": len(self.metrics),
                "metrics": self.metrics
            }
    
    return PerformanceMonitor()
