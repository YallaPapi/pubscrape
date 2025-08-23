"""
Data Pipeline Processor - Main orchestration for scraped data processing

Handles validation, enrichment, deduplication, and multi-format export
with resumable operations and metrics tracking.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from .validators import DataValidator, ValidationResult
from .deduplicator import Deduplicator, DedupeResult
from .metrics_tracker import MetricsTracker, ProcessingMetrics
from ..storage.csv_exporter import CSVExporter
from ..storage.json_exporter import JSONExporter
from ..storage.sqlite_manager import SQLiteManager


@dataclass
class ProcessingConfig:
    """Configuration for data processing pipeline"""
    batch_size: int = 100
    max_workers: int = 4
    enable_validation: bool = True
    enable_deduplication: bool = True
    enable_enrichment: bool = True
    output_formats: List[str] = None
    resume_from_checkpoint: bool = True
    checkpoint_interval: int = 50
    quality_threshold: float = 0.3
    
    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ['csv', 'json', 'sqlite']


@dataclass
class ProcessingResult:
    """Result of pipeline processing"""
    total_records: int
    processed_records: int
    valid_records: int
    duplicates_removed: int
    enriched_records: int
    export_results: Dict[str, bool]
    processing_time: float
    checkpoint_file: Optional[str] = None
    error_count: int = 0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class DataProcessor:
    """Main data processing pipeline orchestrator"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.validator = DataValidator()
        self.deduplicator = Deduplicator()
        self.metrics_tracker = MetricsTracker()
        
        # Initialize exporters
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
        self.sqlite_manager = SQLiteManager()
        
        # Processing state
        self.session_id = self._generate_session_id()
        self.checkpoint_data = {}
        self.processed_ids = set()
        
        self.logger.info(f"DataProcessor initialized with session_id: {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"pipeline_{timestamp}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
    
    async def process_data(self, 
                          input_data: List[Dict[str, Any]], 
                          output_path: str,
                          session_name: str = None) -> ProcessingResult:
        """Main processing pipeline entry point"""
        start_time = datetime.now()
        session_name = session_name or f"session_{self.session_id}"
        
        self.logger.info(f"Starting data processing for {len(input_data)} records")
        
        try:
            # Initialize metrics tracking
            await self.metrics_tracker.start_session(session_name)
            
            # Load checkpoint if resuming
            if self.config.resume_from_checkpoint:
                await self._load_checkpoint(output_path, session_name)
            
            # Process in batches
            processed_data = []
            validation_results = []
            dedupe_results = []
            
            total_records = len(input_data)
            processed_count = 0
            valid_count = 0
            duplicate_count = 0
            enriched_count = 0
            error_count = 0
            
            # Process data in batches for better memory management
            for batch_start in range(0, total_records, self.config.batch_size):
                batch_end = min(batch_start + self.config.batch_size, total_records)
                batch_data = input_data[batch_start:batch_end]
                
                self.logger.info(f"Processing batch {batch_start}-{batch_end}")
                
                # Process batch
                batch_result = await self._process_batch(
                    batch_data, batch_start, session_name
                )
                
                processed_data.extend(batch_result['processed'])
                validation_results.extend(batch_result['validation'])
                dedupe_results.extend(batch_result['dedupe'])
                
                # Update counters
                processed_count += len(batch_result['processed'])
                valid_count += len([r for r in batch_result['validation'] if r.is_valid])
                duplicate_count += len([r for r in batch_result['dedupe'] if r.is_duplicate])
                enriched_count += batch_result['enriched_count']
                error_count += batch_result['error_count']
                
                # Save checkpoint
                if (batch_start + self.config.batch_size) % (self.config.checkpoint_interval * self.config.batch_size) == 0:
                    await self._save_checkpoint(output_path, session_name, processed_data)
                
                # Update progress
                progress = (batch_end / total_records) * 100
                self.logger.info(f"Progress: {progress:.1f}% ({batch_end}/{total_records})")
            
            # Filter out duplicates and invalid records based on config
            final_data = self._filter_final_data(processed_data, validation_results, dedupe_results)
            
            # Export to requested formats
            export_results = await self._export_data(final_data, output_path, session_name)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Finalize metrics
            await self.metrics_tracker.end_session({
                'total_records': total_records,
                'processed_records': processed_count,
                'valid_records': valid_count,
                'duplicates_removed': duplicate_count,
                'enriched_records': enriched_count,
                'processing_time': processing_time,
                'error_count': error_count
            })
            
            # Create result
            result = ProcessingResult(
                total_records=total_records,
                processed_records=processed_count,
                valid_records=valid_count,
                duplicates_removed=duplicate_count,
                enriched_records=enriched_count,
                export_results=export_results,
                processing_time=processing_time,
                error_count=error_count,
                checkpoint_file=f"{output_path}/checkpoint_{session_name}.json"
            )
            
            self.logger.info(f"Processing completed: {valid_count}/{total_records} valid records")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline processing failed: {str(e)}")
            await self.metrics_tracker.record_error(str(e))
            raise
    
    async def _process_batch(self, batch_data: List[Dict], 
                           batch_start: int,
                           session_name: str) -> Dict[str, Any]:
        """Process a single batch of data"""
        processed = []
        validation_results = []
        dedupe_results = []
        enriched_count = 0
        error_count = 0
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Create tasks for parallel processing
            tasks = []
            
            for i, record in enumerate(batch_data):
                record_id = record.get('lead_id') or f"record_{batch_start + i}"
                
                # Skip if already processed (resume capability)
                if record_id in self.processed_ids:
                    continue
                
                # Submit processing task
                task = asyncio.get_event_loop().run_in_executor(
                    executor, self._process_record, record, record_id, session_name
                )
                tasks.append((record_id, task))
            
            # Gather results
            for record_id, task in tasks:
                try:
                    record_result = await task
                    
                    processed.append(record_result['data'])
                    validation_results.append(record_result['validation'])
                    dedupe_results.append(record_result['dedupe'])
                    
                    if record_result['enriched']:
                        enriched_count += 1
                    
                    self.processed_ids.add(record_id)
                    
                except Exception as e:
                    self.logger.error(f"Error processing record {record_id}: {str(e)}")
                    error_count += 1
        
        return {
            'processed': processed,
            'validation': validation_results,
            'dedupe': dedupe_results,
            'enriched_count': enriched_count,
            'error_count': error_count
        }
    
    def _process_record(self, record: Dict, record_id: str, session_name: str) -> Dict[str, Any]:
        """Process a single record (validation, deduplication, enrichment)"""
        try:
            # Validation
            validation_result = None
            if self.config.enable_validation:
                validation_result = self.validator.validate_record(record)
                self.metrics_tracker.record_validation_sync(validation_result)
            
            # Deduplication
            dedupe_result = None
            if self.config.enable_deduplication:
                dedupe_result = self.deduplicator.check_duplicate(record, session_name)
                self.metrics_tracker.record_deduplication_sync(dedupe_result)
            
            # Enrichment
            enriched_data = record.copy()
            enriched = False
            if self.config.enable_enrichment:
                enriched_data, enriched = self._enrich_record(record)
            
            return {
                'data': enriched_data,
                'validation': validation_result,
                'dedupe': dedupe_result,
                'enriched': enriched
            }
            
        except Exception as e:
            self.logger.error(f"Error in record processing: {str(e)}")
            raise
    
    def _enrich_record(self, record: Dict) -> Tuple[Dict, bool]:
        """Enrich record with additional data"""
        enriched_record = record.copy()
        enriched = False
        
        try:
            # Add processing metadata
            enriched_record['processing_timestamp'] = datetime.now().isoformat()
            enriched_record['processor_session'] = self.session_id
            
            # Normalize email format
            if 'primary_email' in enriched_record and enriched_record['primary_email']:
                email = enriched_record['primary_email'].strip().lower()
                if email != enriched_record['primary_email']:
                    enriched_record['primary_email'] = email
                    enriched = True
            
            # Normalize phone format
            if 'primary_phone' in enriched_record and enriched_record['primary_phone']:
                phone = self._normalize_phone(enriched_record['primary_phone'])
                if phone != enriched_record['primary_phone']:
                    enriched_record['primary_phone'] = phone
                    enriched = True
            
            # Add data quality score if missing
            if 'lead_score' not in enriched_record:
                enriched_record['lead_score'] = self._calculate_quality_score(enriched_record)
                enriched = True
            
            # Add actionability flag if missing
            if 'is_actionable' not in enriched_record:
                enriched_record['is_actionable'] = self._is_actionable(enriched_record)
                enriched = True
            
            return enriched_record, enriched
            
        except Exception as e:
            self.logger.warning(f"Enrichment failed for record: {str(e)}")
            return record, False
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format"""
        if not phone:
            return phone
        
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Basic US format normalization
        if cleaned.startswith('1') and len(cleaned) == 11:
            return f"+{cleaned}"
        elif len(cleaned) == 10:
            return f"+1{cleaned}"
        
        return cleaned or phone
    
    def _calculate_quality_score(self, record: Dict) -> float:
        """Calculate data quality score for record"""
        score = 0.0
        weights = {
            'primary_email': 0.4,
            'primary_phone': 0.3,
            'website': 0.2,
            'contact_name': 0.1
        }
        
        for field, weight in weights.items():
            if field in record and record[field] and record[field].strip():
                score += weight
        
        return round(score, 2)
    
    def _is_actionable(self, record: Dict) -> bool:
        """Determine if record is actionable (has contact info)"""
        has_email = record.get('primary_email', '').strip() != ''
        has_phone = record.get('primary_phone', '').strip() != ''
        quality_score = float(record.get('lead_score', 0))
        
        return (has_email or has_phone) and quality_score >= self.config.quality_threshold
    
    def _filter_final_data(self, processed_data: List[Dict],
                          validation_results: List[ValidationResult],
                          dedupe_results: List[DedupeResult]) -> List[Dict]:
        """Filter final dataset based on validation and deduplication results"""
        final_data = []
        
        for i, record in enumerate(processed_data):
            # Check validation if enabled
            if self.config.enable_validation:
                validation = validation_results[i]
                if not validation.is_valid:
                    continue
            
            # Check deduplication if enabled
            if self.config.enable_deduplication:
                dedupe = dedupe_results[i]
                if dedupe.is_duplicate:
                    continue
            
            final_data.append(record)
        
        return final_data
    
    async def _export_data(self, data: List[Dict], output_path: str, session_name: str) -> Dict[str, bool]:
        """Export data to requested formats"""
        export_results = {}
        
        for format_type in self.config.output_formats:
            try:
                if format_type == 'csv':
                    result = await self.csv_exporter.export(
                        data, f"{output_path}/{session_name}.csv"
                    )
                    export_results['csv'] = result.success
                
                elif format_type == 'json':
                    result = await self.json_exporter.export(
                        data, f"{output_path}/{session_name}.json", 
                        {
                            'session_name': session_name,
                            'processing_timestamp': datetime.now().isoformat(),
                            'total_records': len(data)
                        }
                    )
                    export_results['json'] = result.success
                
                elif format_type == 'sqlite':
                    result = await self.sqlite_manager.store_data(
                        data, f"{output_path}/{session_name}.db", session_name
                    )
                    export_results['sqlite'] = result
                
                else:
                    self.logger.warning(f"Unknown export format: {format_type}")
                    export_results[format_type] = False
                    
            except Exception as e:
                self.logger.error(f"Export failed for format {format_type}: {str(e)}")
                export_results[format_type] = False
        
        return export_results
    
    async def _save_checkpoint(self, output_path: str, session_name: str, data: List[Dict]):
        """Save processing checkpoint for resume capability"""
        checkpoint_file = Path(output_path) / f"checkpoint_{session_name}.json"
        
        checkpoint_data = {
            'session_id': self.session_id,
            'session_name': session_name,
            'timestamp': datetime.now().isoformat(),
            'processed_ids': list(self.processed_ids),
            'records_processed': len(data),
            'config': asdict(self.config)
        }
        
        try:
            checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            self.logger.info(f"Checkpoint saved: {checkpoint_file}")
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {str(e)}")
    
    async def _load_checkpoint(self, output_path: str, session_name: str):
        """Load processing checkpoint for resume capability"""
        checkpoint_file = Path(output_path) / f"checkpoint_{session_name}.json"
        
        if not checkpoint_file.exists():
            self.logger.info("No checkpoint file found, starting fresh")
            return
        
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            self.processed_ids = set(checkpoint_data.get('processed_ids', []))
            self.logger.info(f"Loaded checkpoint: {len(self.processed_ids)} records already processed")
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {str(e)}")
            self.processed_ids = set()
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get processing metrics summary"""
        return await self.metrics_tracker.get_summary()
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'sqlite_manager'):
            self.sqlite_manager.close()
        
        self.logger.info("DataProcessor cleanup completed")