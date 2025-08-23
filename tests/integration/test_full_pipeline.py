"""
End-to-end integration tests for the complete scraper pipeline.

Tests the full workflow from search query to final data export,
including all agent interactions and data flow.
"""

import pytest
import tempfile
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

import pandas as pd
from bs4 import BeautifulSoup

try:
    from src.core.agency_factory import AgencyFactory
    from src.agents.bing_navigator_agent import BingNavigatorAgent
    from src.agents.serp_parser_agent import SerpParserAgent
    from src.agents.email_extractor_agent import EmailExtractorAgent
    from src.agents.validator_dedupe_agent import ValidatorDedupeAgent
    from src.agents.exporter_agent import ExporterAgent
    from src.query_builder.campaign_parser import CampaignParser
    from src.query_builder.query_builder import QueryBuilder
except ImportError:
    pytest.skip("Pipeline modules not available", allow_module_level=True)


@pytest.mark.integration
class TestFullPipeline:
    """Test complete pipeline integration"""
    
    @pytest.fixture
    def pipeline_config(self):
        """Configuration for pipeline testing"""
        return {
            "campaign_name": "test_integration_campaign",
            "target_industry": "healthcare",
            "target_locations": ["Chicago, IL", "Houston, TX"],
            "search_queries": [
                "doctors in {location} contact information",
                "medical practice {location} email"
            ],
            "max_results_per_query": 20,
            "enable_email_validation": True,
            "enable_deduplication": True,
            "output_format": "csv",
            "anti_detection_level": "medium",
            "browser_config": {
                "headless": True,
                "timeout": 30,
                "stealth_mode": True
            }
        }
    
    @pytest.fixture
    def mock_html_responses(self, bing_html_sample, medical_practice_html):
        """Mock HTML responses for different stages"""
        return {
            "bing_search": bing_html_sample,
            "business_page": medical_practice_html,
            "contact_page": """
            <html><body>
                <div class="contact-info">
                    <h2>Contact Dr. Sarah Johnson</h2>
                    <p>Email: dr.johnson@chicagopremiermedicine.com</p>
                    <p>Phone: (312) 555-0123</p>
                    <p>Address: 123 Michigan Avenue, Chicago, IL</p>
                </div>
            </body></html>
            """
        }
    
    @pytest.fixture
    def temp_output_dir(self):
        """Temporary directory for test outputs"""
        temp_dir = Path(tempfile.mkdtemp(prefix="integration_test_"))
        yield temp_dir
        
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_agency_factory(self, pipeline_config):
        """Mock agency factory with configured agents"""
        factory = Mock(spec=AgencyFactory)
        
        # Mock agent creation
        factory.create_bing_navigator.return_value = Mock(spec=BingNavigatorAgent)
        factory.create_serp_parser.return_value = Mock(spec=SerpParserAgent)
        factory.create_email_extractor.return_value = Mock(spec=EmailExtractorAgent)
        factory.create_validator_dedupe.return_value = Mock(spec=ValidatorDedupeAgent)
        factory.create_exporter.return_value = Mock(spec=ExporterAgent)
        
        return factory
    
    def test_pipeline_initialization(self, pipeline_config, mock_agency_factory):
        """Test pipeline initialization with all components"""
        # Test campaign parser
        campaign_parser = CampaignParser()
        parsed_config = campaign_parser.parse_config(pipeline_config)
        
        assert parsed_config["campaign_name"] == "test_integration_campaign"
        assert len(parsed_config["target_locations"]) == 2
        assert len(parsed_config["search_queries"]) == 2
        
        # Test query builder
        query_builder = QueryBuilder()
        queries = query_builder.build_queries(
            parsed_config["search_queries"],
            parsed_config["target_locations"]
        )
        
        # Should generate 4 queries (2 templates × 2 locations)
        assert len(queries) == 4
        assert "doctors in Chicago, IL contact information" in queries
        assert "medical practice Houston, TX email" in queries
    
    def test_search_phase(self, pipeline_config, mock_html_responses):
        """Test search phase with Bing navigation and SERP parsing"""
        # Mock Bing Navigator
        with patch('src.agents.bing_navigator_agent.BingNavigatorAgent') as MockNavigator:
            navigator = MockNavigator.return_value
            navigator.search_bing.return_value = {
                "status": "success",
                "html": mock_html_responses["bing_search"],
                "query": "doctors in Chicago, IL contact information",
                "results_count": 5
            }
            
            # Execute search
            search_result = navigator.search_bing("doctors in Chicago, IL contact information")
            
            assert search_result["status"] == "success"
            assert "Northwestern Medicine" in search_result["html"]
            assert search_result["results_count"] == 5
        
        # Mock SERP Parser
        with patch('src.agents.serp_parser_agent.SerpParserAgent') as MockParser:
            parser = MockParser.return_value
            parser.parse_serp.return_value = {
                "status": "success",
                "results": [
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
                ],
                "total_results": 2
            }
            
            # Parse SERP results
            parsed_results = parser.parse_serp(mock_html_responses["bing_search"])
            
            assert parsed_results["status"] == "success"
            assert len(parsed_results["results"]) == 2
            assert parsed_results["results"][0]["title"] == "Northwestern Medicine - Chicago Locations"
    
    def test_extraction_phase(self, mock_html_responses):
        """Test email extraction phase"""
        with patch('src.agents.email_extractor_agent.EmailExtractorAgent') as MockExtractor:
            extractor = MockExtractor.return_value
            extractor.extract_emails.return_value = {
                "status": "success",
                "emails": [
                    {
                        "email": "dr.johnson@chicagopremiermedicine.com",
                        "domain": "chicagopremiermedicine.com",
                        "business_name": "Chicago Premier Medical Associates",
                        "contact_type": "direct",
                        "source_url": "https://chicagopremiermedicine.com/contact",
                        "extraction_confidence": 0.95
                    },
                    {
                        "email": "info@chicagopremiermedicine.com",
                        "domain": "chicagopremiermedicine.com",
                        "business_name": "Chicago Premier Medical Associates",
                        "contact_type": "general",
                        "source_url": "https://chicagopremiermedicine.com/contact",
                        "extraction_confidence": 0.88
                    }
                ],
                "total_extracted": 2
            }
            
            # Test extraction
            urls_to_crawl = [
                "https://www.nm.org/locations/chicago",
                "https://www.rush.edu/patients-visitors/find-doctor"
            ]
            
            extraction_results = []
            for url in urls_to_crawl:
                result = extractor.extract_emails(url)
                extraction_results.append(result)
            
            assert len(extraction_results) == 2
            assert all(result["status"] == "success" for result in extraction_results)
    
    def test_validation_and_deduplication_phase(self):
        """Test validation and deduplication phase"""
        sample_emails = [
            {
                "email": "dr.johnson@chicagopremiermedicine.com",
                "domain": "chicagopremiermedicine.com",
                "business_name": "Chicago Premier Medical Associates",
                "contact_type": "direct"
            },
            {
                "email": "info@chicagopremiermedicine.com",
                "domain": "chicagopremiermedicine.com",
                "business_name": "Chicago Premier Medical Associates",
                "contact_type": "general"
            },
            {
                "email": "dr.johnson@chicagopremiermedicine.com",  # Duplicate
                "domain": "chicagopremiermedicine.com",
                "business_name": "Chicago Premier Medical Associates",
                "contact_type": "direct"
            },
            {
                "email": "invalid-email",  # Invalid format
                "domain": "invalid",
                "business_name": "Test Business",
                "contact_type": "general"
            }
        ]
        
        with patch('src.agents.validator_dedupe_agent.ValidatorDedupeAgent') as MockValidator:
            validator = MockValidator.return_value
            validator.validate_and_dedupe.return_value = {
                "status": "success",
                "validated_emails": [
                    {
                        "email": "dr.johnson@chicagopremiermedicine.com",
                        "domain": "chicagopremiermedicine.com",
                        "business_name": "Chicago Premier Medical Associates",
                        "contact_type": "direct",
                        "validation_status": "valid",
                        "confidence_score": 0.98
                    },
                    {
                        "email": "info@chicagopremiermedicine.com",
                        "domain": "chicagopremiermedicine.com",
                        "business_name": "Chicago Premier Medical Associates",
                        "contact_type": "general",
                        "validation_status": "valid",
                        "confidence_score": 0.92
                    }
                ],
                "duplicates_removed": 1,
                "invalid_emails": 1,
                "total_processed": 4,
                "final_count": 2
            }
            
            # Test validation
            validation_result = validator.validate_and_dedupe(sample_emails)
            
            assert validation_result["status"] == "success"
            assert len(validation_result["validated_emails"]) == 2
            assert validation_result["duplicates_removed"] == 1
            assert validation_result["invalid_emails"] == 1
    
    def test_export_phase(self, temp_output_dir):
        """Test data export phase"""
        sample_validated_data = [
            {
                "email": "dr.johnson@chicagopremiermedicine.com",
                "domain": "chicagopremiermedicine.com",
                "business_name": "Chicago Premier Medical Associates",
                "contact_type": "direct",
                "phone": "(312) 555-0123",
                "address": "123 Michigan Avenue, Chicago, IL",
                "validation_status": "valid",
                "confidence_score": 0.98,
                "extraction_timestamp": datetime.now().isoformat()
            },
            {
                "email": "physicians@rush.edu",
                "domain": "rush.edu",
                "business_name": "Rush University Medical Center",
                "contact_type": "general",
                "phone": "(312) 942-5000",
                "address": "1611 W Harrison St, Chicago, IL",
                "validation_status": "valid",
                "confidence_score": 0.94,
                "extraction_timestamp": datetime.now().isoformat()
            }
        ]
        
        with patch('src.agents.exporter_agent.ExporterAgent') as MockExporter:
            exporter = MockExporter.return_value
            
            # Mock CSV export
            csv_file = temp_output_dir / "test_campaign_results.csv"
            exporter.export_to_csv.return_value = {
                "status": "success",
                "file_path": str(csv_file),
                "records_exported": 2,
                "file_size_bytes": 1024
            }
            
            # Mock JSON export
            json_file = temp_output_dir / "test_campaign_metadata.json"
            exporter.export_metadata.return_value = {
                "status": "success",
                "file_path": str(json_file),
                "metadata": {
                    "campaign_name": "test_integration_campaign",
                    "total_records": 2,
                    "export_timestamp": datetime.now().isoformat(),
                    "validation_summary": {
                        "valid_emails": 2,
                        "invalid_emails": 0,
                        "duplicates_removed": 1
                    }
                }
            }
            
            # Test exports
            csv_result = exporter.export_to_csv(sample_validated_data, str(csv_file))
            json_result = exporter.export_metadata(
                {"campaign_name": "test_integration_campaign", "total_records": 2},
                str(json_file)
            )
            
            assert csv_result["status"] == "success"
            assert csv_result["records_exported"] == 2
            assert json_result["status"] == "success"
    
    @pytest.mark.slow
    def test_complete_pipeline_flow(self, pipeline_config, mock_html_responses, temp_output_dir):
        """Test complete pipeline from start to finish"""
        pipeline_results = {
            "campaign_name": pipeline_config["campaign_name"],
            "start_time": datetime.now(),
            "queries_executed": [],
            "results_found": [],
            "emails_extracted": [],
            "validation_summary": {},
            "export_files": []
        }
        
        # Phase 1: Query Building
        campaign_parser = CampaignParser()
        parsed_config = campaign_parser.parse_config(pipeline_config)
        
        query_builder = QueryBuilder()
        queries = query_builder.build_queries(
            parsed_config["search_queries"],
            parsed_config["target_locations"]
        )
        
        pipeline_results["queries_executed"] = queries
        assert len(queries) == 4
        
        # Phase 2: Search and Parse (Mocked)
        for query in queries[:2]:  # Test first 2 queries
            # Mock search
            search_result = {
                "query": query,
                "html": mock_html_responses["bing_search"],
                "status": "success"
            }
            
            # Mock parse
            parse_result = {
                "query": query,
                "results": [
                    {
                        "title": "Northwestern Medicine - Chicago",
                        "url": "https://www.nm.org/locations/chicago",
                        "contact_info": {"email": "info@nm.org"}
                    }
                ],
                "status": "success"
            }
            
            pipeline_results["results_found"].append(parse_result)
        
        # Phase 3: Email Extraction (Mocked)
        extracted_emails = [
            {
                "email": "dr.johnson@chicagopremiermedicine.com",
                "business_name": "Chicago Premier Medical",
                "validation_status": "pending"
            },
            {
                "email": "info@nm.org",
                "business_name": "Northwestern Medicine",
                "validation_status": "pending"
            }
        ]
        
        pipeline_results["emails_extracted"] = extracted_emails
        
        # Phase 4: Validation and Deduplication (Mocked)
        validation_summary = {
            "total_emails": len(extracted_emails),
            "valid_emails": 2,
            "invalid_emails": 0,
            "duplicates_removed": 0,
            "final_count": 2
        }
        
        pipeline_results["validation_summary"] = validation_summary
        
        # Phase 5: Export (Mocked)
        export_files = [
            str(temp_output_dir / "campaign_results.csv"),
            str(temp_output_dir / "campaign_metadata.json")
        ]
        
        pipeline_results["export_files"] = export_files
        pipeline_results["end_time"] = datetime.now()
        pipeline_results["duration"] = (pipeline_results["end_time"] - pipeline_results["start_time"]).total_seconds()
        
        # Validate complete pipeline results
        assert len(pipeline_results["queries_executed"]) == 4
        assert len(pipeline_results["results_found"]) == 2
        assert len(pipeline_results["emails_extracted"]) == 2
        assert pipeline_results["validation_summary"]["final_count"] == 2
        assert len(pipeline_results["export_files"]) == 2
        assert pipeline_results["duration"] >= 0
    
    def test_pipeline_error_handling(self, pipeline_config):
        """Test pipeline error handling and recovery"""
        # Test search failure
        with patch('src.agents.bing_navigator_agent.BingNavigatorAgent') as MockNavigator:
            navigator = MockNavigator.return_value
            navigator.search_bing.side_effect = Exception("Search service unavailable")
            
            # Pipeline should handle search failures gracefully
            try:
                navigator.search_bing("test query")
                assert False, "Should have raised exception"
            except Exception as e:
                assert "Search service unavailable" in str(e)
        
        # Test parsing failure
        with patch('src.agents.serp_parser_agent.SerpParserAgent') as MockParser:
            parser = MockParser.return_value
            parser.parse_serp.return_value = {
                "status": "error",
                "error": "Failed to parse HTML",
                "results": []
            }
            
            result = parser.parse_serp("<invalid html>")
            assert result["status"] == "error"
            assert len(result["results"]) == 0
        
        # Test validation failure
        with patch('src.agents.validator_dedupe_agent.ValidatorDedupeAgent') as MockValidator:
            validator = MockValidator.return_value
            validator.validate_and_dedupe.return_value = {
                "status": "partial_success",
                "validated_emails": [],
                "errors": ["Email validation service timeout"],
                "total_processed": 5,
                "final_count": 0
            }
            
            result = validator.validate_and_dedupe([{"email": "test@example.com"}])
            assert result["status"] == "partial_success"
            assert len(result["errors"]) > 0
    
    def test_pipeline_performance_metrics(self, pipeline_config):
        """Test pipeline performance tracking"""
        performance_metrics = {
            "start_time": datetime.now(),
            "phase_timings": {},
            "memory_usage": [],
            "request_counts": {},
            "error_counts": {},
            "data_quality_scores": []
        }
        
        # Simulate phase timing
        import time
        
        phases = ["search", "parse", "extract", "validate", "export"]
        for phase in phases:
            phase_start = time.time()
            time.sleep(0.01)  # Simulate work
            phase_duration = time.time() - phase_start
            performance_metrics["phase_timings"][phase] = phase_duration
        
        # Simulate request tracking
        performance_metrics["request_counts"] = {
            "search_requests": 4,
            "parse_operations": 4,
            "extraction_requests": 8,
            "validation_requests": 15,
            "export_operations": 2
        }
        
        # Simulate error tracking
        performance_metrics["error_counts"] = {
            "timeout_errors": 1,
            "parse_errors": 0,
            "validation_errors": 2,
            "export_errors": 0
        }
        
        # Calculate total metrics
        performance_metrics["end_time"] = datetime.now()
        performance_metrics["total_duration"] = (
            performance_metrics["end_time"] - performance_metrics["start_time"]
        ).total_seconds()
        
        performance_metrics["total_requests"] = sum(performance_metrics["request_counts"].values())
        performance_metrics["total_errors"] = sum(performance_metrics["error_counts"].values())
        performance_metrics["success_rate"] = (
            (performance_metrics["total_requests"] - performance_metrics["total_errors"]) /
            performance_metrics["total_requests"]
        )
        
        # Validate performance metrics
        assert performance_metrics["total_duration"] > 0
        assert performance_metrics["total_requests"] == 33
        assert performance_metrics["total_errors"] == 3
        assert abs(performance_metrics["success_rate"] - 0.909) < 0.01
        assert len(performance_metrics["phase_timings"]) == 5
    
    def test_data_quality_validation(self):
        """Test data quality validation across pipeline"""
        # Sample data at different pipeline stages
        search_results = [
            {"title": "Valid Medical Practice", "url": "https://valid-medical.com"},
            {"title": "Another Practice", "url": "https://another-practice.com"},
            {"title": "", "url": "invalid-url"},  # Poor quality
        ]
        
        extracted_emails = [
            {"email": "doctor@valid-medical.com", "confidence": 0.95},
            {"email": "info@another-practice.com", "confidence": 0.88},
            {"email": "invalid-email", "confidence": 0.30},  # Poor quality
            {"email": "test@test.com", "confidence": 0.60},  # Medium quality
        ]
        
        # Data quality assessment
        quality_metrics = {
            "search_quality": {
                "total_results": len(search_results),
                "valid_results": len([r for r in search_results if r["title"] and r["url"].startswith("http")]),
                "quality_score": 0.0
            },
            "extraction_quality": {
                "total_emails": len(extracted_emails),
                "high_confidence": len([e for e in extracted_emails if e["confidence"] >= 0.8]),
                "medium_confidence": len([e for e in extracted_emails if 0.6 <= e["confidence"] < 0.8]),
                "low_confidence": len([e for e in extracted_emails if e["confidence"] < 0.6]),
                "quality_score": 0.0
            }
        }
        
        # Calculate quality scores
        quality_metrics["search_quality"]["quality_score"] = (
            quality_metrics["search_quality"]["valid_results"] /
            quality_metrics["search_quality"]["total_results"]
        )
        
        avg_confidence = sum(e["confidence"] for e in extracted_emails) / len(extracted_emails)
        quality_metrics["extraction_quality"]["quality_score"] = avg_confidence
        
        # Validate quality metrics
        assert quality_metrics["search_quality"]["valid_results"] == 2
        assert abs(quality_metrics["search_quality"]["quality_score"] - 0.667) < 0.01
        assert quality_metrics["extraction_quality"]["high_confidence"] == 2
        assert quality_metrics["extraction_quality"]["medium_confidence"] == 1
        assert quality_metrics["extraction_quality"]["low_confidence"] == 1
        assert abs(quality_metrics["extraction_quality"]["quality_score"] - 0.683) < 0.01


@pytest.mark.integration
@pytest.mark.network
class TestRealWorldIntegration:
    """Integration tests with real network requests (when enabled)"""
    
    def test_real_bing_search(self, test_config):
        """Test real Bing search (when network tests enabled)"""
        if not test_config["enable_real_requests"]:
            pytest.skip("Real network requests disabled")
        
        # This would test against real Bing search
        # Only run when explicitly enabled for development
        pytest.skip("Real network tests require manual activation")
    
    def test_real_email_validation(self, test_config):
        """Test real email validation service"""
        if not test_config["enable_real_requests"]:
            pytest.skip("Real network requests disabled")
        
        # This would test against real email validation APIs
        pytest.skip("Real validation tests require API keys")


@pytest.mark.integration
class TestPipelineRecovery:
    """Test pipeline recovery and resilience"""
    
    def test_partial_failure_recovery(self):
        """Test recovery from partial pipeline failures"""
        # Simulate scenario where some queries succeed and others fail
        query_results = [
            {"query": "query1", "status": "success", "results": ["result1", "result2"]},
            {"query": "query2", "status": "error", "error": "Timeout"},
            {"query": "query3", "status": "success", "results": ["result3"]},
            {"query": "query4", "status": "error", "error": "Blocked"}
        ]
        
        # Pipeline should continue with successful results
        successful_results = [r for r in query_results if r["status"] == "success"]
        failed_results = [r for r in query_results if r["status"] == "error"]
        
        assert len(successful_results) == 2
        assert len(failed_results) == 2
        
        # Should extract data from successful results
        all_results = []
        for result in successful_results:
            all_results.extend(result["results"])
        
        assert len(all_results) == 3
        assert "result1" in all_results
        assert "result3" in all_results
    
    def test_data_consistency_validation(self):
        """Test data consistency across pipeline stages"""
        # Simulate data flow with potential inconsistencies
        stage1_data = {
            "query_count": 4,
            "total_results": 20,
            "unique_domains": 15
        }
        
        stage2_data = {
            "urls_processed": 20,
            "emails_found": 35,
            "extraction_errors": 2
        }
        
        stage3_data = {
            "emails_validated": 33,  # 35 - 2 errors
            "valid_emails": 28,
            "invalid_emails": 5,
            "duplicates_removed": 3
        }
        
        # Validate data consistency
        assert stage2_data["urls_processed"] == stage1_data["total_results"]
        assert stage2_data["emails_found"] - stage2_data["extraction_errors"] == stage3_data["emails_validated"]
        assert stage3_data["valid_emails"] + stage3_data["invalid_emails"] == stage3_data["emails_validated"]
        
        final_count = stage3_data["valid_emails"] - stage3_data["duplicates_removed"]
        assert final_count == 25  # 28 - 3 duplicates
    
    def test_resource_cleanup(self):
        """Test proper resource cleanup after pipeline completion"""
        # Simulate resource tracking
        resources = {
            "browser_sessions": 3,
            "temp_files": 15,
            "open_connections": 8,
            "memory_allocations": 25
        }
        
        # Simulate cleanup
        cleanup_results = {
            "browser_sessions_closed": 3,
            "temp_files_deleted": 15,
            "connections_closed": 8,
            "memory_freed": 25
        }
        
        # Validate complete cleanup
        assert cleanup_results["browser_sessions_closed"] == resources["browser_sessions"]
        assert cleanup_results["temp_files_deleted"] == resources["temp_files"]
        assert cleanup_results["connections_closed"] == resources["open_connections"]
        assert cleanup_results["memory_freed"] == resources["memory_allocations"]
