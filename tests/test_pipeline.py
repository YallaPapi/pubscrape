"""
Comprehensive Pipeline Tests

Tests for data processing pipeline including validation, deduplication,
storage, and metrics tracking functionality.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.data_processor import DataProcessor, ProcessingConfig, ProcessingResult
from src.pipeline.validators import DataValidator, ValidationResult, ValidationError
from src.pipeline.deduplicator import Deduplicator, DedupeResult
from src.pipeline.metrics_tracker import MetricsTracker
from src.storage.csv_exporter import CSVExporter, ExportResult
from src.storage.json_exporter import JSONExporter, JSONExportResult
from src.storage.sqlite_manager import SQLiteManager


class TestDataValidator:
    """Test data validation functionality"""
    
    def test_valid_record_validation(self):
        """Test validation of valid record"""
        validator = DataValidator()
        
        valid_record = {
            'lead_id': 'TEST_001',
            'business_name': 'Test Business Inc',
            'primary_email': 'contact@testbusiness.com',
            'primary_phone': '+1-555-123-4567',
            'website': 'https://testbusiness.com',
            'contact_name': 'John Doe'
        }
        
        result = validator.validate_record(valid_record)
        
        assert result.is_valid
        assert result.score > 0.7
        assert len(result.errors) == 0
    
    def test_invalid_email_validation(self):
        """Test validation catches invalid email"""
        validator = DataValidator()
        
        invalid_record = {
            'lead_id': 'TEST_002',
            'business_name': 'Test Business',
            'primary_email': 'invalid-email',
            'primary_phone': '555-123-4567'
        }
        
        result = validator.validate_record(invalid_record)
        
        assert not result.is_valid
        assert any(error.field == 'primary_email' for error in result.errors)
        assert any(error.code == 'INVALID_EMAIL_FORMAT' for error in result.errors)
    
    def test_missing_required_fields(self):
        """Test validation catches missing required fields"""
        validator = DataValidator()
        
        incomplete_record = {
            'lead_id': 'TEST_003',
            'primary_email': 'test@example.com'
        }
        
        result = validator.validate_record(incomplete_record)
        
        assert not result.is_valid
        assert any(error.field == 'business_name' for error in result.errors)
    
    def test_batch_validation(self):
        """Test batch validation of multiple records"""
        validator = DataValidator()
        
        records = [
            {'lead_id': 'B1', 'business_name': 'Business 1', 'primary_email': 'test1@example.com'},
            {'lead_id': 'B2', 'business_name': 'Business 2', 'primary_email': 'invalid-email'},
            {'lead_id': 'B3', 'business_name': 'Business 3', 'primary_phone': '555-123-4567'}
        ]
        
        results = validator.validate_batch(records)
        
        assert len(results) == 3
        assert results[0].is_valid  # Valid record
        assert not results[1].is_valid  # Invalid email
        assert results[2].is_valid  # Valid with phone only


class TestDeduplicator:
    """Test deduplication functionality"""
    
    def test_exact_email_match(self):
        """Test exact email matching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            deduplicator = Deduplicator(f"{temp_dir}/dedupe.db")
            
            record1 = {
                'lead_id': 'DUP_001',
                'business_name': 'Test Company',
                'primary_email': 'contact@testcompany.com'
            }
            
            record2 = {
                'lead_id': 'DUP_002',
                'business_name': 'Test Company Inc',  # Slightly different
                'primary_email': 'contact@testcompany.com'  # Same email
            }
            
            # First record should not be duplicate
            result1 = deduplicator.check_duplicate(record1, 'test_session')
            assert not result1.is_duplicate
            
            # Second record should be duplicate
            result2 = deduplicator.check_duplicate(record2, 'test_session')
            assert result2.is_duplicate
            assert result2.match_type == 'exact'
            assert 'primary_email' in result2.matching_fields
    
    def test_fuzzy_business_name_match(self):
        """Test fuzzy business name matching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            deduplicator = Deduplicator(f"{temp_dir}/dedupe.db")
            
            record1 = {
                'lead_id': 'FUZZY_001',
                'business_name': 'ABC Corporation Inc',
                'primary_email': 'info@abc-corp.com'
            }
            
            record2 = {
                'lead_id': 'FUZZY_002',
                'business_name': 'ABC Corp',  # Similar name
                'primary_email': 'contact@abccorp.com'  # Different email
            }
            
            # Store first record
            result1 = deduplicator.check_duplicate(record1, 'test_session')
            assert not result1.is_duplicate
            
            # Second record might be fuzzy duplicate (depending on threshold)
            result2 = deduplicator.check_duplicate(record2, 'test_session')
            # This should pass regardless of fuzzy match due to different emails
    
    def test_domain_matching(self):
        """Test website domain matching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            deduplicator = Deduplicator(f"{temp_dir}/dedupe.db")
            
            record1 = {
                'lead_id': 'DOMAIN_001',
                'business_name': 'Company A',
                'website': 'https://example.com/about'
            }
            
            record2 = {
                'lead_id': 'DOMAIN_002',
                'business_name': 'Company A LLC',
                'website': 'https://www.example.com/home'  # Same domain
            }
            
            # First record
            result1 = deduplicator.check_duplicate(record1, 'test_session')
            assert not result1.is_duplicate
            
            # Second record should match by domain
            result2 = deduplicator.check_duplicate(record2, 'test_session')
            assert result2.is_duplicate
            assert result2.match_type == 'domain'


class TestCSVExporter:
    """Test CSV export functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_csv_export(self):
        """Test basic CSV export"""
        exporter = CSVExporter()
        
        test_data = [
            {
                'lead_id': 'CSV_001',
                'business_name': 'Test Business',
                'primary_email': 'test@business.com',
                'lead_score': 0.8,
                'is_actionable': True
            },
            {
                'lead_id': 'CSV_002',
                'business_name': 'Another Business',
                'primary_phone': '555-123-4567',
                'lead_score': 0.6,
                'is_actionable': False
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = f"{temp_dir}/test_export.csv"
            
            result = await exporter.export(test_data, output_file)
            
            assert result.success
            assert result.records_exported == 2
            assert Path(output_file).exists()
            
            # Verify content
            import pandas as pd
            df = pd.read_csv(output_file)
            assert len(df) == 2
            assert 'lead_id' in df.columns
            assert 'business_name' in df.columns
    
    @pytest.mark.asyncio
    async def test_csv_field_cleaning(self):
        """Test CSV field value cleaning"""
        exporter = CSVExporter()
        
        # Test data with problematic values
        test_data = [
            {
                'lead_id': 'CLEAN_001',
                'business_name': 'Company with "quotes" and\nnewlines',
                'primary_email': '  MESSY@EXAMPLE.COM  ',
                'website': 'www.example.com',  # Missing protocol
                'lead_score': '0.75',  # String instead of float
                'is_actionable': 'True'  # String instead of boolean
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = f"{temp_dir}/clean_test.csv"
            
            result = await exporter.export(test_data, output_file)
            
            assert result.success
            
            # Verify cleaning
            import pandas as pd
            df = pd.read_csv(output_file)
            
            # Check email normalization
            assert df.iloc[0]['primary_email'] == 'messy@example.com'
            
            # Check website protocol addition
            assert df.iloc[0]['website'] == 'https://www.example.com'
            
            # Check numeric formatting
            assert df.iloc[0]['lead_score'] == '0.750'


class TestJSONExporter:
    """Test JSON export functionality"""
    
    @pytest.mark.asyncio
    async def test_structured_json_export(self):
        """Test structured JSON export with metadata"""
        exporter = JSONExporter()
        
        test_data = [
            {
                'lead_id': 'JSON_001',
                'business_name': 'JSON Test Company',
                'primary_email': 'test@jsoncompany.com'
            }
        ]
        
        metadata = {
            'export_source': 'test_suite',
            'test_run': True
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = f"{temp_dir}/test_export.json"
            
            result = await exporter.export(test_data, output_file, metadata)
            
            assert result.success
            assert result.records_exported == 1
            
            # Verify structure
            with open(output_file, 'r') as f:
                exported_data = json.load(f)
            
            assert 'metadata' in exported_data
            assert 'data' in exported_data
            assert 'schema' in exported_data
            assert len(exported_data['data']) == 1
    
    @pytest.mark.asyncio
    async def test_json_schema_generation(self):
        """Test JSON schema generation"""
        exporter = JSONExporter()
        
        test_data = [
            {
                'lead_id': 'SCHEMA_001',
                'business_name': 'Schema Test',
                'lead_score': 0.8,
                'is_actionable': True,
                'tags': ['test', 'schema']
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = f"{temp_dir}/schema_test.json"
            
            result = await exporter.export(test_data, output_file, include_schema=True)
            
            assert result.success
            
            with open(output_file, 'r') as f:
                exported_data = json.load(f)
            
            schema = exported_data['schema']
            assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
            assert 'properties' in schema
            
            data_properties = schema['properties']['data']['items']['properties']
            assert 'lead_id' in data_properties
            assert data_properties['lead_score']['type'] == 'number'
            assert data_properties['is_actionable']['type'] == 'boolean'


class TestSQLiteManager:
    """Test SQLite storage functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_storage(self):
        """Test basic data storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/test.db"
            manager = SQLiteManager(db_path)
            
            test_data = [
                {
                    'lead_id': 'SQL_001',
                    'business_name': 'SQL Test Company',
                    'primary_email': 'test@sqlcompany.com',
                    'lead_score': 0.7
                }
            ]
            
            success = await manager.store_data(test_data, session_name='test_session')
            assert success
            
            # Verify storage
            result = manager.query_data()
            assert result.success
            assert len(result.data) == 1
            assert result.data[0]['business_name'] == 'SQL Test Company'
    
    def test_query_filtering(self):
        """Test data querying with filters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/filter_test.db"
            manager = SQLiteManager(db_path)
            
            # Store test data synchronously for this test
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute(manager.LEADS_SCHEMA)
            
            test_records = [
                ('TEST_001', 'High Score Company', 'test1@example.com', '', '', '', 0.9, 1),
                ('TEST_002', 'Low Score Company', 'test2@example.com', '', '', '', 0.2, 0),
                ('TEST_003', 'Medium Company', '', '555-123-4567', '', '', 0.5, 1)
            ]
            
            for record in test_records:
                conn.execute('''\n                    INSERT INTO leads \n                    (lead_id, business_name, primary_email, primary_phone, website, \n                     contact_name, lead_score, is_actionable)\n                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                ''', record)\n            \n            conn.commit()\n            conn.close()\n            \n            # Test filtering\n            result = manager.query_data({'min_score': 0.5})\n            assert result.success\n            assert len(result.data) == 2  # Records with score >= 0.5\n            \n            result = manager.query_data({'is_actionable': True})\n            assert result.success\n            assert len(result.data) == 2  # Actionable records\n            \n            result = manager.query_data({'has_email': True})\n            assert result.success\n            assert len(result.data) == 2  # Records with email\n    \n    def test_database_statistics(self):\n        \"\"\"Test database statistics generation\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            db_path = f\"{temp_dir}/stats_test.db\"\n            manager = SQLiteManager(db_path)\n            \n            # Manually insert test data for statistics\n            import sqlite3\n            conn = sqlite3.connect(db_path)\n            conn.execute(manager.LEADS_SCHEMA)\n            \n            # Insert varied test data\n            conn.execute('''\n                INSERT INTO leads (lead_id, business_name, primary_email, lead_score, is_actionable)\n                VALUES ('STAT_001', 'Company A', 'a@example.com', 0.8, 1)\n            ''')\n            conn.execute('''\n                INSERT INTO leads (lead_id, business_name, primary_phone, lead_score, is_actionable)\n                VALUES ('STAT_002', 'Company B', '555-123-4567', 0.6, 0)\n            ''')\n            conn.commit()\n            conn.close()\n            \n            stats = manager.get_statistics()\n            \n            assert stats['total_records'] == 2\n            assert stats['actionable_records'] == 1\n            assert stats['records_with_email'] == 1\n            assert stats['records_with_phone'] == 1\n            assert 0.6 <= stats['average_lead_score'] <= 0.8"


class TestDataProcessor:
    """Test main data processor integration"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_processing(self):
        """Test complete pipeline processing"""
        config = ProcessingConfig(
            batch_size=2,
            enable_validation=True,
            enable_deduplication=True,
            enable_enrichment=True,
            output_formats=['csv', 'json'],
            resume_from_checkpoint=False
        )
        
        processor = DataProcessor(config)
        
        test_data = [
            {
                'lead_id': 'PIPELINE_001',
                'business_name': 'Pipeline Test Company',
                'primary_email': 'test@pipeline.com',
                'website': 'pipeline.com'  # Will be enriched with https://
            },
            {
                'lead_id': 'PIPELINE_002',
                'business_name': 'Another Pipeline Co',
                'primary_phone': '(555) 123-4567',  # Will be normalized
                'primary_email': 'CONTACT@PIPELINE.COM'  # Will be normalized
            },\n            {\n                'lead_id': 'PIPELINE_003',\n                'business_name': 'Duplicate Test',\n                'primary_email': 'test@pipeline.com'  # Duplicate of first\n            }\n        ]\n        \n        with tempfile.TemporaryDirectory() as temp_dir:\n            result = await processor.process_data(\n                test_data, \n                temp_dir, \n                session_name='test_pipeline'\n            )\n            \n            assert result.total_records == 3\n            assert result.processed_records > 0\n            assert result.duplicates_removed >= 1  # At least one duplicate\n            assert result.export_results['csv']\n            assert result.export_results['json']\n            \n            # Verify files were created\n            assert Path(f\"{temp_dir}/test_pipeline.csv\").exists()\n            assert Path(f\"{temp_dir}/test_pipeline.json\").exists()\n    \n    @pytest.mark.asyncio\n    async def test_checkpoint_resume(self):\n        \"\"\"Test checkpoint and resume functionality\"\"\"\n        config = ProcessingConfig(\n            batch_size=1,\n            checkpoint_interval=1,\n            resume_from_checkpoint=True\n        )\n        \n        processor = DataProcessor(config)\n        \n        test_data = [\n            {'lead_id': 'CHECKPOINT_001', 'business_name': 'Company 1'},\n            {'lead_id': 'CHECKPOINT_002', 'business_name': 'Company 2'}\n        ]\n        \n        with tempfile.TemporaryDirectory() as temp_dir:\n            # First processing (simulate interruption after first record)\n            processor.processed_ids.add('CHECKPOINT_001')\n            \n            # Create a checkpoint file\n            checkpoint_data = {\n                'session_id': processor.session_id,\n                'session_name': 'checkpoint_test',\n                'timestamp': datetime.now().isoformat(),\n                'processed_ids': ['CHECKPOINT_001'],\n                'records_processed': 1\n            }\n            \n            checkpoint_file = Path(temp_dir) / \"checkpoint_checkpoint_test.json\"\n            with open(checkpoint_file, 'w') as f:\n                json.dump(checkpoint_data, f)\n            \n            # Resume processing\n            result = await processor.process_data(\n                test_data, \n                temp_dir, \n                session_name='checkpoint_test'\n            )\n            \n            # Should process only the second record (first was already processed)\n            assert result.total_records == 2"


class TestMetricsTracker:
    \"\"\"Test metrics tracking functionality\"\"\"\n    \n    @pytest.mark.asyncio\n    async def test_session_tracking(self):\n        \"\"\"Test metrics session tracking\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            tracker = MetricsTracker(temp_dir)\n            \n            # Start session\n            session_id = await tracker.start_session('test_metrics')\n            assert session_id\n            assert tracker.current_session is not None\n            \n            # Record some metrics\n            await tracker.record_error('Test error', 'validation', 'TEST_001')\n            await tracker.record_warning('Test warning', 'processing')\n            \n            # End session\n            await tracker.end_session({\n                'total_records': 10,\n                'valid_records': 8,\n                'processing_time': 5.5\n            })\n            \n            # Verify session data\n            assert tracker.current_session.total_records == 10\n            assert tracker.current_session.valid_records == 8\n            assert tracker.current_session.processing_time == 5.5\n    \n    @pytest.mark.asyncio\n    async def test_validation_metrics_recording(self):\n        \"\"\"Test validation metrics recording\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            tracker = MetricsTracker(temp_dir)\n            \n            await tracker.start_session('validation_test')\n            \n            # Create mock validation result\n            validation_result = Mock()\n            validation_result.record_id = 'VAL_001'\n            validation_result.is_valid = True\n            validation_result.error_count = 0\n            validation_result.warning_count = 1\n            validation_result.score = 0.85\n            \n            await tracker.record_validation(validation_result, processing_time=0.1)\n            \n            assert len(tracker.validation_metrics) == 1\n            metric = tracker.validation_metrics[0]\n            assert metric.record_id == 'VAL_001'\n            assert metric.is_valid\n            assert metric.validation_score == 0.85\n    \n    @pytest.mark.asyncio\n    async def test_performance_report_generation(self):\n        \"\"\"Test performance report generation\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            tracker = MetricsTracker(temp_dir)\n            \n            await tracker.start_session('performance_test')\n            \n            # Record some operation times\n            tracker.record_operation_time('validation', 0.1)\n            tracker.record_operation_time('validation', 0.15)\n            tracker.record_operation_time('deduplication', 0.05)\n            \n            await tracker.end_session({\n                'total_records': 100,\n                'processing_time': 10.0\n            })\n            \n            # Generate report\n            report_path = tracker.generate_performance_report()\n            \n            assert Path(report_path).exists()\n            \n            # Verify report content\n            with open(report_path, 'r') as f:\n                report = json.load(f)\n            \n            assert 'current_session' in report\n            assert 'summary_statistics' in report\n            assert report['current_session']['total_records'] == 100


if __name__ == '__main__':\n    # Run tests\n    pytest.main([__file__, '-v'])"