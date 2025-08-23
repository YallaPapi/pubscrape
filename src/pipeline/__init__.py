"""
Data Pipeline Package

Comprehensive data processing pipeline for scraped data with validation,
deduplication, enrichment, and multi-format export capabilities.
"""

from .data_processor import DataProcessor, ProcessingConfig, ProcessingResult
from .validators import DataValidator, ValidationResult, ValidationError
from .deduplicator import Deduplicator, DedupeResult
from .metrics_tracker import MetricsTracker, ProcessingMetrics

__all__ = [
    'DataProcessor',
    'ProcessingConfig', 
    'ProcessingResult',
    'DataValidator',
    'ValidationResult',
    'ValidationError',
    'Deduplicator',
    'DedupeResult',
    'MetricsTracker',
    'ProcessingMetrics'
]

__version__ = '1.0.0'