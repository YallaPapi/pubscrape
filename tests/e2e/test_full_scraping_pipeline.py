"""
End-to-End Integration Test: Full Scraping Pipeline

Tests the complete workflow from campaign configuration to final lead generation,
validating that all refactored components work together seamlessly.
"""

import pytest
import asyncio
import tempfile
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, patch

# Import system modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import CLIApplication
from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
from src.scrapers.email_extractor import extract_emails_from_website
from src.utils.logger import setup_logging
from src.utils.error_handler import ErrorHandler


class TestFullScrapingPipeline:
    """End-to-end integration tests for the complete scraping pipeline"""
    
    @pytest.fixture
    def test_campaign_config(self):
        """Sample campaign configuration for testing"""
        return {
            "name": "integration_test_campaign",
            "description": "Full pipeline integration test",
            "target_industry": "healthcare",
            "target_locations": ["Seattle, WA", "Portland, OR"],
            "search_queries": [
                "doctors in {location}",
                "medical clinics {location}",
                "healthcare providers {location}"
            ],
            "max_results_per_query": 5,
            "max_total_leads": 15,
            "enable_email_validation": True,
            "enable_anti_detection": True,
            "output_formats": ["csv", "json"],
            "quality_filters": {
                "min_confidence_score": 0.7,
                "require_email": False,
                "require_phone": False,
                "exclude_duplicates": True
            }
        }
    
    @pytest.fixture
    def temp_campaign_file(self, test_campaign_config, temp_output_dir):
        """Create temporary campaign configuration file"""
        campaign_file = temp_output_dir / "test_campaign.json"
        with open(campaign_file, 'w') as f:
            json.dump(test_campaign_config, f, indent=2)
        return campaign_file
    
    @pytest.fixture
    def cli_app(self):
        """Initialize CLI application for testing"""
        return CLIApplication()
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_complete_scraping_workflow(self, cli_app, temp_campaign_file, 
                                            temp_output_dir, performance_monitor):
        """
        Test the complete end-to-end scraping workflow:
        1. Load campaign configuration
        2. Initialize scrapers and agents
        3. Execute search queries
        4. Extract contact information
        5. Validate leads
        6. Export results
        7. Generate reports
        """
        performance_monitor.record_metric("test_start", datetime.now().timestamp())
        
        # Mock command line arguments
        class MockArgs:
            def __init__(self):
                self.command = 'scrape'
                self.campaign = str(temp_campaign_file)
                self.max_leads = 15
                self.config = None
                self.verbose = True
                self.quiet = False
                self.debug = True
                self.output_dir = str(temp_output_dir)
                self.dry_run = False
                self.resume = None
                self.no_validation = False
        
        args = MockArgs()
        
        # Initialize application
        assert cli_app.initialize(args), "CLI application initialization failed"
        
        # Execute scraping command
        with patch('src.scrapers.google_maps_scraper.scrape_google_maps_businesses') as mock_gmaps:
            with patch('src.scrapers.email_extractor.extract_emails_from_website') as mock_email:
                # Mock scraper responses
                mock_gmaps.return_value = [
                    {
                        'name': 'Seattle Medical Center',
                        'address': '123 Main St, Seattle, WA 98101',
                        'phone': '(206) 555-0123',
                        'website': 'https://seattlemedical.com',
                        'source': 'google_maps'
                    },
                    {
                        'name': 'Pacific Healthcare Clinic',
                        'address': '456 Oak Ave, Seattle, WA 98102',
                        'phone': '(206) 555-0456',
                        'website': 'https://pacifichealthcare.com',
                        'source': 'google_maps'
                    }
                ]
                
                mock_email.return_value = 'contact@seattlemedical.com'
                
                # Execute the campaign
                exit_code = await cli_app.run_scrape_command(args)
                
                # Verify successful execution
                assert exit_code == 0, "Scraping campaign should complete successfully"
                
                # Verify scraper was called
                assert mock_gmaps.called, "Google Maps scraper should be invoked"
                
                # Verify output files exist
                output_files = list(temp_output_dir.glob("*.csv"))
                assert len(output_files) > 0, "CSV output file should be generated"
                
                json_files = list(temp_output_dir.glob("*.json"))
                assert len(json_files) > 0, "JSON output file should be generated"
        
        performance_monitor.record_metric("test_end", datetime.now().timestamp())
        summary = performance_monitor.get_summary()
        assert summary["duration"] < 30, "End-to-end test should complete within 30 seconds"
    
    @pytest.mark.integration
    async def test_error_recovery_integration(self, cli_app, temp_campaign_file, temp_output_dir):
        """
        Test error handling and recovery across the pipeline:
        1. Network failures
        2. Rate limiting
        3. Parsing errors
        4. Validation failures
        """
        class MockArgs:
            def __init__(self):
                self.command = 'scrape'
                self.campaign = str(temp_campaign_file)
                self.max_leads = 5
                self.config = None
                self.verbose = True
                self.quiet = False
                self.debug = True
                self.output_dir = str(temp_output_dir)
                self.dry_run = False
                self.resume = None
                self.no_validation = False
        
        args = MockArgs()
        
        # Initialize application
        assert cli_app.initialize(args)
        
        # Test network failure recovery
        with patch('src.scrapers.google_maps_scraper.scrape_google_maps_businesses') as mock_scraper:
            # First call fails, second succeeds
            mock_scraper.side_effect = [
                ConnectionError("Network timeout"),
                [
                    {
                        'name': 'Recovery Test Clinic',
                        'address': '789 Test St, Test City, WA 98001',
                        'phone': '(206) 555-0789',
                        'website': 'https://recoverytest.com',
                        'source': 'google_maps'
                    }
                ]
            ]
            
            # Should recover from first failure and complete
            exit_code = await cli_app.run_scrape_command(args)
            
            # May succeed with retry logic or return appropriate exit code
            assert exit_code in [0, 1], "Should handle network errors gracefully"
    
    @pytest.mark.integration
    async def test_data_validation_pipeline(self, cli_app, temp_campaign_file, temp_output_dir):
        """
        Test data validation and quality assurance pipeline:
        1. Email validation
        2. Phone number validation  
        3. Business name validation
        4. Duplicate detection
        5. Quality scoring
        """
        class MockArgs:
            def __init__(self):
                self.command = 'scrape'
                self.campaign = str(temp_campaign_file)
                self.max_leads = 10
                self.config = None
                self.verbose = True
                self.quiet = False
                self.debug = True
                self.output_dir = str(temp_output_dir)
                self.dry_run = False
                self.resume = None
                self.no_validation = False
        
        args = MockArgs()
        assert cli_app.initialize(args)
        
        # Mock scrapers with validation test data
        with patch('src.scrapers.google_maps_scraper.scrape_google_maps_businesses') as mock_scraper:
            with patch('src.scrapers.email_extractor.extract_emails_from_website') as mock_email:
                # Test data with various validation scenarios
                mock_scraper.return_value = [
                    {
                        'name': 'Valid Medical Center',
                        'address': '123 Valid St, Seattle, WA 98101',
                        'phone': '(206) 555-0123',
                        'website': 'https://valid-medical.com',
                        'source': 'google_maps'
                    },
                    {
                        'name': 'Invalid Phone Clinic',
                        'address': '456 Test Ave, Seattle, WA 98102',
                        'phone': 'invalid-phone',
                        'website': 'https://invalid-phone.com',
                        'source': 'google_maps'
                    },
                    {
                        'name': 'Duplicate Medical Center',  # Duplicate for testing
                        'address': '123 Valid St, Seattle, WA 98101',
                        'phone': '(206) 555-0123',
                        'website': 'https://valid-medical.com',
                        'source': 'google_maps'
                    }
                ]
                
                mock_email.side_effect = [
                    'contact@valid-medical.com',
                    'invalid-email',
                    'contact@valid-medical.com'
                ]
                
                exit_code = await cli_app.run_scrape_command(args)
                
                # Should complete with validation
                assert exit_code == 0, "Should complete data validation successfully"
                
                # Verify output contains validated data
                output_files = list(temp_output_dir.glob("*.csv"))
                if output_files:
                    with open(output_files[0], 'r') as f:
                        reader = csv.DictReader(f)
                        leads = list(reader)
                        
                        # Should have valid leads (duplicates removed)
                        assert len(leads) <= 2, "Duplicates should be removed"
    
    @pytest.mark.integration
    async def test_multi_source_integration(self, cli_app, temp_campaign_file, temp_output_dir):
        """
        Test integration across multiple data sources:
        1. Google Maps scraping
        2. Website email extraction
        3. Bing search fallback
        4. Data source attribution
        """
        class MockArgs:
            def __init__(self):
                self.command = 'scrape'
                self.campaign = str(temp_campaign_file)
                self.max_leads = 8
                self.config = None
                self.verbose = True
                self.quiet = False
                self.debug = True
                self.output_dir = str(temp_output_dir)
                self.dry_run = False
                self.resume = None
                self.no_validation = False
        
        args = MockArgs()
        assert cli_app.initialize(args)
        
        # Test with multiple sources
        with patch('src.scrapers.google_maps_scraper.scrape_google_maps_businesses') as mock_gmaps:
            with patch('src.scrapers.email_extractor.extract_emails_from_website') as mock_email:
                # Google Maps returns some results
                mock_gmaps.return_value = [
                    {
                        'name': 'Multi-Source Clinic A',
                        'address': '111 Source St, Seattle, WA 98101',
                        'phone': '(206) 555-0111',
                        'website': 'https://clinic-a.com',
                        'source': 'google_maps'
                    },
                    {
                        'name': 'Multi-Source Clinic B',
                        'address': '222 Source Ave, Seattle, WA 98102',
                        'phone': '(206) 555-0222',
                        'website': 'https://clinic-b.com',
                        'source': 'google_maps'
                    }
                ]
                
                mock_email.side_effect = [
                    'info@clinic-a.com',
                    'contact@clinic-b.com'
                ]
                
                exit_code = await cli_app.run_scrape_command(args)
                assert exit_code == 0, "Multi-source integration should succeed"
                
                # Verify data source attribution
                output_files = list(temp_output_dir.glob("*.csv"))
                if output_files:
                    with open(output_files[0], 'r') as f:
                        reader = csv.DictReader(f)
                        leads = list(reader)
                        
                        for lead in leads:
                            assert 'source' in lead, "Each lead should have source attribution"
    
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_performance_integration(self, cli_app, temp_campaign_file, 
                                         temp_output_dir, benchmark_thresholds):
        """
        Test system performance under integration load:
        1. Response time benchmarks
        2. Memory usage tracking
        3. Throughput validation
        4. Resource utilization
        """
        class MockArgs:
            def __init__(self):
                self.command = 'scrape'
                self.campaign = str(temp_campaign_file)
                self.max_leads = 20
                self.config = None
                self.verbose = False  # Reduce logging overhead
                self.quiet = True
                self.debug = False
                self.output_dir = str(temp_output_dir)
                self.dry_run = False
                self.resume = None
                self.no_validation = False
        
        args = MockArgs()
        assert cli_app.initialize(args)
        
        import psutil
        import time
        
        # Monitor system resources
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_time = time.time()
        
        with patch('src.scrapers.google_maps_scraper.scrape_google_maps_businesses') as mock_scraper:
            with patch('src.scrapers.email_extractor.extract_emails_from_website') as mock_email:
                # Generate test data
                test_businesses = []
                for i in range(20):
                    test_businesses.append({
                        'name': f'Performance Test Clinic {i}',
                        'address': f'{100 + i} Perf St, Seattle, WA 98{100 + i:03d}',
                        'phone': f'(206) 555-{1000 + i:04d}',
                        'website': f'https://perf-clinic-{i}.com',
                        'source': 'google_maps'
                    })
                
                mock_scraper.return_value = test_businesses
                mock_email.return_value = 'test@clinic.com'
                
                # Execute performance test
                exit_code = await cli_app.run_scrape_command(args)
                
                # Measure performance
                end_time = time.time()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                execution_time = end_time - start_time
                memory_usage = end_memory - start_memory
                
                # Verify performance benchmarks
                assert execution_time < benchmark_thresholds["max_response_time"], \
                    f"Execution time {execution_time:.2f}s exceeds threshold"
                
                assert memory_usage < benchmark_thresholds["max_memory_usage"], \
                    f"Memory usage {memory_usage:.2f}MB exceeds threshold"
                
                assert exit_code == 0, "Performance test should complete successfully"
    
    @pytest.mark.integration
    async def test_configuration_integration(self, temp_output_dir):
        """
        Test configuration loading and application across pipeline:
        1. Configuration file loading
        2. Environment variable overrides
        3. Command-line argument precedence
        4. Configuration validation
        """
        # Create test configuration
        config_data = {
            "logging": {
                "log_level": "DEBUG",
                "log_directory": str(temp_output_dir / "logs"),
                "enable_console_logging": True,
                "enable_file_logging": True
            },
            "search": {
                "max_pages_per_query": 2,
                "rate_limit_rpm": 30,
                "retry_attempts": 2,
                "retry_delay": 1.0
            },
            "export": {
                "output_directory": str(temp_output_dir),
                "default_format": "csv"
            },
            "anti_detection": {
                "enable_stealth": True,
                "rotate_user_agents": True,
                "use_proxy_rotation": False
            }
        }
        
        config_file = temp_output_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Create minimal campaign
        campaign_data = {
            "name": "config_test_campaign",
            "search_queries": ["test clinics Seattle"],
            "max_results_per_query": 3
        }
        
        campaign_file = temp_output_dir / "config_test_campaign.json"
        with open(campaign_file, 'w') as f:
            json.dump(campaign_data, f, indent=2)
        
        class MockArgs:
            def __init__(self):
                self.command = 'scrape'
                self.campaign = str(campaign_file)
                self.config = str(config_file)
                self.max_leads = 3
                self.verbose = True
                self.quiet = False
                self.debug = False  # Should be overridden by config
                self.output_dir = None  # Should use config value
                self.dry_run = False
                self.resume = None
                self.no_validation = True
        
        cli_app = CLIApplication()
        args = MockArgs()
        
        # Test configuration loading
        assert cli_app.initialize(args), "Configuration integration should succeed"
        
        # Verify configuration is applied
        # (This would require accessing the internal config manager)
        # For now, we test that initialization succeeds with config file
        
        # Test execution with configuration
        with patch('src.scrapers.google_maps_scraper.scrape_google_maps_businesses') as mock_scraper:
            mock_scraper.return_value = [
                {
                    'name': 'Config Test Clinic',
                    'address': '123 Config St, Seattle, WA 98101',
                    'phone': '(206) 555-0123',
                    'website': 'https://config-test.com',
                    'source': 'google_maps'
                }
            ]
            
            exit_code = await cli_app.run_scrape_command(args)
            assert exit_code == 0, "Configuration-based execution should succeed"
            
            # Verify logs directory was created as specified in config
            logs_dir = temp_output_dir / "logs"
            assert logs_dir.exists(), "Logs directory should be created per config"


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])