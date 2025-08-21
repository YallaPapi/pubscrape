"""
CSV Export Tool

Agency Swarm tool for exporting validated contact data to CSV format
with comprehensive schema validation and Excel compatibility.
"""

import os
import json
from typing import Dict, Any, List, Optional
from pydantic import Field

try:
    from agency_swarm.tools import BaseTool
except ImportError:
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class CSVExportTool(BaseTool):
    """
    Tool for exporting contact data to CSV format with comprehensive validation.
    
    This tool exports validated podcast contact data to CSV format following
    the podcast outreach schema with proper quoting, character encoding,
    and Excel compatibility.
    """
    
    contact_data: List[Dict[str, Any]] = Field(
        description="List of contact data dictionaries to export to CSV"
    )
    
    output_path: str = Field(
        description="Output file path for the CSV export (should end with .csv)"
    )
    
    validate_schema: bool = Field(
        default=True,
        description="Whether to validate data against the podcast outreach schema"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Whether to include export metadata in a separate file"
    )
    
    def run(self) -> str:
        """
        Export contact data to CSV format.
        
        Returns:
            JSON string with export results including metrics and file paths
        """
        try:
            # Import the exporter here to avoid circular imports
            from agents.exporter_agent import CSVExporter
            
            # Initialize exporter
            exporter = CSVExporter()
            
            # Validate input
            if not self.contact_data:
                return json.dumps({
                    "success": False,
                    "error": "No contact data provided for export",
                    "metrics": None
                })
            
            if not self.output_path.endswith('.csv'):
                return json.dumps({
                    "success": False,
                    "error": "Output path must end with .csv extension",
                    "metrics": None
                })
            
            # Perform CSV export
            metrics = exporter.export_to_csv(
                data=self.contact_data,
                output_path=self.output_path,
                validate_schema=self.validate_schema
            )
            
            # Create metadata file if requested
            metadata_path = None
            if self.include_metadata and metrics.success:
                metadata_path = self.output_path.replace('.csv', '_metadata.json')
                
                metadata = {
                    "export_timestamp": metrics.export_timestamp,
                    "total_rows": metrics.total_rows,
                    "write_duration_ms": metrics.write_duration_ms,
                    "file_size_bytes": metrics.file_size_bytes,
                    "validation_errors": metrics.validation_errors,
                    "quality_distribution": metrics.quality_distribution,
                    "output_path": metrics.output_path,
                    "schema_validation_enabled": self.validate_schema
                }
                
                try:
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    # Don't fail the main export if metadata fails
                    metadata_path = f"Metadata export failed: {str(e)}"
            
            # Prepare result
            result = {
                "success": metrics.success,
                "error": metrics.error_message,
                "csv_path": self.output_path if metrics.success else None,
                "metadata_path": metadata_path,
                "metrics": {
                    "total_rows": metrics.total_rows,
                    "write_duration_ms": metrics.write_duration_ms,
                    "file_size_bytes": metrics.file_size_bytes,
                    "validation_errors": metrics.validation_errors,
                    "quality_distribution": metrics.quality_distribution
                }
            }
            
            if metrics.success:
                result["message"] = f"Successfully exported {metrics.total_rows} contacts to {self.output_path}"
                if metrics.validation_errors > 0:
                    result["warning"] = f"Export completed with {metrics.validation_errors} validation warnings"
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"CSV export tool failed: {str(e)}",
                "csv_path": None,
                "metadata_path": None,
                "metrics": None
            })


class CSVValidationTool(BaseTool):
    """
    Tool for validating CSV export files and ensuring schema compliance.
    
    This tool validates exported CSV files to ensure they meet the podcast
    outreach schema requirements and can be opened correctly in Excel/Sheets.
    """
    
    csv_file_path: str = Field(
        description="Path to the CSV file to validate"
    )
    
    check_file_integrity: bool = Field(
        default=True,
        description="Whether to check file integrity and readability"
    )
    
    sample_validation: bool = Field(
        default=True,
        description="Whether to perform sample data validation"
    )
    
    def run(self) -> str:
        """
        Validate CSV export file.
        
        Returns:
            JSON string with validation results
        """
        try:
            import pandas as pd
            from datetime import datetime
            
            # Check if file exists
            if not os.path.exists(self.csv_file_path):
                return json.dumps({
                    "success": False,
                    "error": f"CSV file not found: {self.csv_file_path}",
                    "validation_results": None
                })
            
            validation_results = {
                "file_exists": True,
                "file_size_bytes": os.path.getsize(self.csv_file_path),
                "readable": False,
                "schema_compliant": False,
                "row_count": 0,
                "column_count": 0,
                "missing_columns": [],
                "extra_columns": [],
                "sample_validation": {},
                "encoding_valid": False,
                "excel_compatible": False,
                "validation_timestamp": datetime.now().isoformat()
            }
            
            # File integrity check
            if self.check_file_integrity:
                try:
                    # Try to read the file with pandas
                    df = pd.read_csv(self.csv_file_path, encoding='utf-8-sig')
                    validation_results["readable"] = True
                    validation_results["encoding_valid"] = True
                    validation_results["row_count"] = len(df)
                    validation_results["column_count"] = len(df.columns)
                    
                    # Check for Excel compatibility (BOM presence)
                    with open(self.csv_file_path, 'rb') as f:
                        first_bytes = f.read(3)
                        validation_results["excel_compatible"] = first_bytes == b'\xef\xbb\xbf'
                    
                except Exception as e:
                    validation_results["readable"] = False
                    validation_results["read_error"] = str(e)
                    
                    return json.dumps({
                        "success": False,
                        "error": f"CSV file is not readable: {str(e)}",
                        "validation_results": validation_results
                    })
            
            # Schema compliance check
            try:
                # Expected schema from exporter
                expected_columns = [
                    "podcast_name", "host_name", "podcast_description",
                    "host_email", "booking_email", "alternative_emails",
                    "podcast_website", "contact_page_url", "contact_forms_available",
                    "best_contact_method", "contact_strategy", "contact_confidence",
                    "social_links", "social_influence_score", "social_platforms_count",
                    "overall_intelligence_score", "relevance_score", "popularity_score",
                    "authority_score", "content_quality_score", "guest_potential_score",
                    "contact_quality_score", "response_likelihood", "validation_status",
                    "estimated_downloads", "audience_size_category", "episode_count",
                    "rating", "host_authority_level", "platform_source",
                    "apple_podcasts_url", "spotify_url", "youtube_url",
                    "google_podcasts_url", "rss_feed_url", "content_format_type",
                    "interview_style", "target_audience", "content_themes",
                    "recommendations", "risk_factors", "outreach_priority",
                    "best_pitch_angle", "ai_relevance_score", "discovery_source",
                    "validation_date", "last_updated", "data_quality_grade", "notes"
                ]
                
                actual_columns = list(df.columns)
                
                # Find missing and extra columns
                missing_columns = [col for col in expected_columns if col not in actual_columns]
                extra_columns = [col for col in actual_columns if col not in expected_columns]
                
                validation_results["missing_columns"] = missing_columns
                validation_results["extra_columns"] = extra_columns
                validation_results["schema_compliant"] = len(missing_columns) == 0
                
            except Exception as e:
                validation_results["schema_error"] = str(e)
            
            # Sample data validation
            if self.sample_validation and validation_results["readable"]:
                try:
                    sample_results = {}
                    
                    # Check for required fields
                    required_fields = ['podcast_name', 'host_name']
                    for field in required_fields:
                        if field in df.columns:
                            empty_count = df[field].isna().sum() + (df[field] == '').sum()
                            sample_results[f"{field}_completeness"] = {
                                "total_rows": len(df),
                                "empty_rows": int(empty_count),
                                "completion_rate": float((len(df) - empty_count) / len(df)) if len(df) > 0 else 0
                            }
                    
                    # Check email format in email fields
                    email_fields = ['host_email', 'booking_email']
                    for field in email_fields:
                        if field in df.columns:
                            # Count non-empty emails and validate format
                            non_empty = df[field].dropna()
                            non_empty = non_empty[non_empty != '']
                            
                            if len(non_empty) > 0:
                                valid_emails = non_empty[non_empty.str.contains('@', na=False)]
                                sample_results[f"{field}_validation"] = {
                                    "total_emails": int(len(non_empty)),
                                    "valid_format": int(len(valid_emails)),
                                    "format_validity_rate": float(len(valid_emails) / len(non_empty))
                                }
                    
                    # Check URL format in URL fields
                    url_fields = ['podcast_website', 'apple_podcasts_url', 'spotify_url']
                    for field in url_fields:
                        if field in df.columns:
                            non_empty = df[field].dropna()
                            non_empty = non_empty[non_empty != '']
                            
                            if len(non_empty) > 0:
                                valid_urls = non_empty[non_empty.str.startswith(('http://', 'https://'), na=False)]
                                sample_results[f"{field}_validation"] = {
                                    "total_urls": int(len(non_empty)),
                                    "valid_format": int(len(valid_urls)),
                                    "format_validity_rate": float(len(valid_urls) / len(non_empty))
                                }
                    
                    validation_results["sample_validation"] = sample_results
                    
                except Exception as e:
                    validation_results["sample_validation_error"] = str(e)
            
            # Overall success determination
            success = (
                validation_results["readable"] and
                validation_results["encoding_valid"] and
                validation_results["schema_compliant"] and
                validation_results["row_count"] > 0
            )
            
            return json.dumps({
                "success": success,
                "message": f"Validation completed for {validation_results['row_count']} rows",
                "validation_results": validation_results
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"CSV validation tool failed: {str(e)}",
                "validation_results": None
            })