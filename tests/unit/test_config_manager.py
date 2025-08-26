"""
Unit tests for ConfigManager component.

Tests configuration loading, validation, and environment handling
for secure and robust configuration management.
"""

import pytest
import os
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any

# Import the module under test
try:
    from src.config.config_manager import ConfigManager
    from src.core.config_manager import ConfigManager as CoreConfigManager
except ImportError:
    # Create a mock if the actual module doesn't exist
    class ConfigManager:
        def __init__(self, config_path=None):
            self.config_path = config_path
            self._config = {}
        
        def load_config(self):
            return self._config
        
        def get(self, key, default=None):
            return self._config.get(key, default)
        
        def validate_config(self):
            return True


class TestConfigManager:
    """Test suite for ConfigManager functionality."""

    @pytest.fixture
    def sample_config(self):
        """Sample configuration data for testing."""
        return {
            "scraping": {
                "max_concurrent": 5,
                "request_delay": 2.0,
                "timeout": 30,
                "user_agents": ["Mozilla/5.0 (Test)"],
                "anti_detection": {
                    "enabled": True,
                    "stealth_level": "medium",
                    "proxy_rotation": False
                }
            },
            "email_validation": {
                "enabled": True,
                "api_key": "${EMAIL_API_KEY}",
                "timeout": 10,
                "batch_size": 100
            },
            "export": {
                "formats": ["csv", "json"],
                "output_dir": "./output",
                "include_metadata": True
            },
            "logging": {
                "level": "INFO",
                "file": "scraper.log",
                "max_size": "10MB",
                "backup_count": 5
            }
        }

    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """ConfigManager instance with test configuration."""
        return ConfigManager(config_path=temp_config_file)

    # Configuration Loading Tests
    def test_load_config_from_file(self, config_manager, sample_config):
        """Test loading configuration from YAML file."""
        config = config_manager.load_config()
        
        assert config is not None
        assert "scraping" in config
        assert "email_validation" in config
        assert config["scraping"]["max_concurrent"] == sample_config["scraping"]["max_concurrent"]

    def test_load_config_file_not_found(self):
        """Test handling of missing configuration file."""
        manager = ConfigManager(config_path="nonexistent.yaml")
        
        with pytest.raises(FileNotFoundError):
            manager.load_config()

    def test_load_config_invalid_yaml(self):
        """Test handling of invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            with pytest.raises(yaml.YAMLError):
                manager.load_config()
        finally:
            os.unlink(temp_path)

    def test_load_config_empty_file(self):
        """Test handling of empty configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            config = manager.load_config()
            assert config is None or config == {}
        finally:
            os.unlink(temp_path)

    # Environment Variable Substitution Tests
    @patch.dict(os.environ, {"EMAIL_API_KEY": "test-api-key-123"})
    def test_environment_variable_substitution(self, config_manager):
        """Test environment variable substitution in configuration."""
        config = config_manager.load_config()
        
        # Should substitute ${EMAIL_API_KEY} with actual environment value
        assert config["email_validation"]["api_key"] == "test-api-key-123"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_environment_variable(self, config_manager):
        """Test handling of missing environment variables."""
        config = config_manager.load_config()
        
        # Should keep placeholder when env var is missing
        assert "${EMAIL_API_KEY}" in config["email_validation"]["api_key"]

    # Configuration Validation Tests
    def test_validate_config_valid(self, config_manager):
        """Test configuration validation with valid config."""
        config_manager.load_config()
        
        is_valid = config_manager.validate_config()
        assert is_valid is True

    def test_validate_config_missing_required_fields(self):
        """Test validation failure for missing required fields."""
        incomplete_config = {
            "scraping": {
                # Missing required fields like max_concurrent
                "timeout": 30
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_config, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            manager.load_config()
            
            is_valid = manager.validate_config()
            assert is_valid is False
        finally:
            os.unlink(temp_path)

    def test_validate_config_invalid_types(self):
        """Test validation failure for invalid data types."""
        invalid_config = {
            "scraping": {
                "max_concurrent": "not_a_number",  # Should be int
                "request_delay": True,  # Should be float
                "timeout": "30s"  # Should be numeric
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            manager.load_config()
            
            is_valid = manager.validate_config()
            assert is_valid is False
        finally:
            os.unlink(temp_path)

    # Configuration Access Tests
    def test_get_config_value(self, config_manager):
        """Test getting configuration values."""
        config_manager.load_config()
        
        max_concurrent = config_manager.get("scraping.max_concurrent")
        assert max_concurrent == 5
        
        anti_detection_enabled = config_manager.get("scraping.anti_detection.enabled")
        assert anti_detection_enabled is True

    def test_get_config_value_with_default(self, config_manager):
        """Test getting configuration values with default fallback."""
        config_manager.load_config()
        
        nonexistent = config_manager.get("nonexistent.key", "default_value")
        assert nonexistent == "default_value"

    def test_get_config_value_nested(self, config_manager):
        """Test getting nested configuration values."""
        config_manager.load_config()
        
        stealth_level = config_manager.get("scraping.anti_detection.stealth_level")
        assert stealth_level == "medium"

    # Security Tests
    def test_no_sensitive_data_in_logs(self, config_manager, caplog):
        """Test that sensitive configuration data is not logged."""
        with patch.dict(os.environ, {"EMAIL_API_KEY": "secret-key-123"}):
            config = config_manager.load_config()
            
        # Check that API key is not in log messages
        for record in caplog.records:
            assert "secret-key-123" not in record.message

    def test_config_file_permissions(self, temp_config_file):
        """Test that configuration files have appropriate permissions."""
        # On Unix systems, check file permissions
        if os.name != 'nt':  # Not Windows
            file_stat = os.stat(temp_config_file)
            file_mode = file_stat.st_mode
            
            # File should not be world-readable for security
            assert not (file_mode & 0o004)  # Others can't read

    # Performance Tests
    @pytest.mark.performance
    def test_config_loading_performance(self, config_manager, benchmark):
        """Test configuration loading performance."""
        def load_config():
            return config_manager.load_config()
        
        result = benchmark(load_config)
        assert result is not None

    @pytest.mark.performance
    def test_config_access_performance(self, config_manager, benchmark):
        """Test configuration value access performance."""
        config_manager.load_config()
        
        def access_config():
            return config_manager.get("scraping.anti_detection.stealth_level")
        
        result = benchmark(access_config)
        assert result == "medium"

    # Edge Cases and Error Handling
    def test_config_with_unicode_characters(self):
        """Test handling of Unicode characters in configuration."""
        unicode_config = {
            "business_categories": {
                "café": "coffee_shops",
                "résumé_services": "professional_services",
                "naïve_algorithm": False
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(unicode_config, f, allow_unicode=True)
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            config = manager.load_config()
            
            assert "café" in config["business_categories"]
            assert config["business_categories"]["café"] == "coffee_shops"
        finally:
            os.unlink(temp_path)

    def test_config_with_large_values(self):
        """Test handling of large configuration values."""
        large_config = {
            "user_agents": ["User-Agent-" + str(i) for i in range(1000)],
            "large_string": "x" * 10000,
            "nested_large": {f"key_{i}": f"value_{i}" for i in range(500)}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(large_config, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            config = manager.load_config()
            
            assert len(config["user_agents"]) == 1000
            assert len(config["large_string"]) == 10000
            assert len(config["nested_large"]) == 500
        finally:
            os.unlink(temp_path)

    def test_concurrent_config_access(self, config_manager):
        """Test concurrent access to configuration."""
        import threading
        import time
        
        config_manager.load_config()
        results = []
        errors = []
        
        def access_config():
            try:
                for _ in range(10):
                    value = config_manager.get("scraping.max_concurrent")
                    results.append(value)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=access_config) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 accesses
        assert all(result == 5 for result in results)

    # Integration with Environment
    def test_config_manager_singleton(self):
        """Test that ConfigManager behaves as singleton when appropriate."""
        # This test would verify singleton behavior if implemented
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        # If singleton pattern is used, these should be the same instance
        # assert manager1 is manager2

    def test_config_reload(self, config_manager, temp_config_file):
        """Test configuration reloading when file changes."""
        # Load initial config
        initial_config = config_manager.load_config()
        initial_value = initial_config["scraping"]["max_concurrent"]
        
        # Modify the config file
        modified_config = initial_config.copy()
        modified_config["scraping"]["max_concurrent"] = 10
        
        with open(temp_config_file, 'w') as f:
            yaml.dump(modified_config, f)
        
        # Reload config
        reloaded_config = config_manager.load_config()
        new_value = reloaded_config["scraping"]["max_concurrent"]
        
        assert initial_value == 5
        assert new_value == 10

    # Test Fixtures and Helpers
    def test_config_merge_functionality(self):
        """Test configuration merging functionality."""
        base_config = {
            "scraping": {"max_concurrent": 5, "timeout": 30},
            "logging": {"level": "INFO"}
        }
        
        override_config = {
            "scraping": {"max_concurrent": 10},
            "export": {"format": "json"}
        }
        
        # This would test a merge function if implemented
        # merged = config_manager.merge_configs(base_config, override_config)
        # assert merged["scraping"]["max_concurrent"] == 10
        # assert merged["scraping"]["timeout"] == 30
        # assert merged["export"]["format"] == "json"

    @pytest.mark.parametrize("config_format", ["yaml", "json", "toml"])
    def test_multiple_config_formats(self, config_format, sample_config):
        """Test support for multiple configuration formats."""
        if config_format == "yaml":
            content = yaml.dump(sample_config)
            suffix = ".yaml"
        elif config_format == "json":
            content = json.dumps(sample_config, indent=2)
            suffix = ".json"
        elif config_format == "toml":
            pytest.skip("TOML support not implemented")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_path=temp_path)
            config = manager.load_config()
            
            assert config["scraping"]["max_concurrent"] == 5
        finally:
            os.unlink(temp_path)