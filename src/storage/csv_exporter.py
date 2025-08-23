"""
CSV Export with Proper Formatting

Handles CSV export with field validation, proper escaping, and
compatibility with existing CSV formats in the project.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class ExportResult:
    """Result of CSV export operation"""
    success: bool
    file_path: str
    records_exported: int
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class CSVExporter:
    """CSV exporter with proper formatting and validation"""
    
    # Standard field order matching existing project format
    STANDARD_FIELDS = [
        'lead_id',
        'business_name',
        'primary_email',
        'primary_phone',
        'contact_name',
        'website',
        'lead_score',
        'extraction_date',
        'source_query',
        'is_actionable'
    ]
    
    # Optional fields that may be present
    OPTIONAL_FIELDS = [
        'secondary_email',
        'secondary_phone',
        'address',
        'city',
        'state',
        'zip_code',
        'industry',
        'company_size',
        'description',
        'social_media',
        'processing_timestamp',
        'processor_session',
        'validation_score',
        'dedupe_status'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def export(self, 
                    data: List[Dict[str, Any]], 
                    output_path: str,
                    include_metadata: bool = True,
                    custom_fields: List[str] = None) -> ExportResult:
        """Export data to CSV with proper formatting"""
        
        if not data:
            return ExportResult(
                success=False,
                file_path=output_path,
                records_exported=0,
                error_message="No data to export"
            )
        
        try:
            # Prepare output path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine field order
            field_order = self._determine_field_order(data, custom_fields)
            
            # Validate and clean data
            cleaned_data, warnings = self._validate_and_clean_data(data, field_order)
            
            # Write CSV
            records_written = self._write_csv(cleaned_data, output_file, field_order)
            
            # Write metadata file if requested
            if include_metadata:
                await self._write_metadata(cleaned_data, output_file, warnings)
            
            self.logger.info(f"CSV export successful: {records_written} records to {output_file}")
            
            return ExportResult(
                success=True,
                file_path=str(output_file),
                records_exported=records_written,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"CSV export failed: {str(e)}")
            return ExportResult(
                success=False,
                file_path=output_path,
                records_exported=0,
                error_message=str(e)
            )
    
    def _determine_field_order(self, data: List[Dict], custom_fields: List[str] = None) -> List[str]:
        """Determine the field order for CSV columns"""
        
        # Get all unique fields from data
        all_fields = set()
        for record in data:
            all_fields.update(record.keys())
        
        # Start with standard fields (in order)
        field_order = []
        for field in self.STANDARD_FIELDS:
            if field in all_fields:
                field_order.append(field)
                all_fields.remove(field)
        
        # Add custom fields if specified
        if custom_fields:
            for field in custom_fields:
                if field in all_fields:
                    field_order.append(field)
                    all_fields.remove(field)
        
        # Add optional fields (in order)
        for field in self.OPTIONAL_FIELDS:
            if field in all_fields:
                field_order.append(field)
                all_fields.remove(field)
        
        # Add any remaining fields alphabetically
        remaining_fields = sorted(list(all_fields))
        field_order.extend(remaining_fields)
        
        self.logger.debug(f"Field order determined: {field_order}")
        return field_order
    
    def _validate_and_clean_data(self, data: List[Dict], field_order: List[str]) -> tuple:
        """Validate and clean data for CSV export"""
        cleaned_data = []
        warnings = []
        
        for i, record in enumerate(data):
            cleaned_record = {}
            
            for field in field_order:
                value = record.get(field, '')
                
                # Clean and format value
                cleaned_value = self._clean_field_value(value, field)
                cleaned_record[field] = cleaned_value
                
                # Check for potential issues
                if field in self.STANDARD_FIELDS and not cleaned_value:
                    if field == 'business_name':  # Critical field
                        warnings.append(f"Record {i}: Missing business name")
                    elif field in ['primary_email', 'primary_phone']:
                        warnings.append(f"Record {i}: Missing contact information ({field})")
            
            cleaned_data.append(cleaned_record)
        
        return cleaned_data, warnings
    
    def _clean_field_value(self, value: Any, field_name: str) -> str:
        """Clean and format field value for CSV"""
        if value is None:
            return ''\n        \n        # Convert to string\n        str_value = str(value).strip()\n        \n        # Handle boolean values\n        if isinstance(value, bool):\n            return 'True' if value else 'False'\n        \n        # Handle numeric values\n        if field_name in ['lead_score', 'validation_score']:\n            try:\n                float_val = float(str_value)\n                return f\"{float_val:.3f}\"\n            except (ValueError, TypeError):\n                return '0.000'\n        \n        # Handle dates\n        if 'date' in field_name.lower() or 'timestamp' in field_name.lower():\n            if str_value:\n                try:\n                    # Try to parse and reformat date\n                    if 'T' in str_value or '-' in str_value:\n                        # Already in ISO format or similar\n                        return str_value\n                    else:\n                        return str_value\n                except:\n                    return str_value\n        \n        # Handle email fields\n        if 'email' in field_name.lower():\n            if str_value:\n                return str_value.lower().strip()\n        \n        # Handle phone fields\n        if 'phone' in field_name.lower():\n            if str_value:\n                # Keep original formatting but clean whitespace\n                return str_value.strip()\n        \n        # Handle URLs\n        if field_name in ['website']:\n            if str_value and not str_value.startswith(('http://', 'https://')):\n                if str_value.startswith('www.'):\n                    return f\"https://{str_value}\"\n                elif '.' in str_value:\n                    return f\"https://{str_value}\"\n        \n        # Clean general text fields\n        # Remove problematic characters for CSV\n        cleaned = str_value.replace('\\n', ' ').replace('\\r', ' ')\n        cleaned = ' '.join(cleaned.split())  # Normalize whitespace\n        \n        # Handle quotes in CSV data\n        if '\"' in cleaned:\n            cleaned = cleaned.replace('\"', '\"\"')  # Escape quotes\n        \n        return cleaned\n    \n    def _write_csv(self, data: List[Dict], output_file: Path, field_order: List[str]) -> int:\n        \"\"\"Write data to CSV file\"\"\"\n        \n        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:\n            writer = csv.DictWriter(\n                csvfile, \n                fieldnames=field_order,\n                quoting=csv.QUOTE_MINIMAL,\n                escapechar='\\\\'\n            )\n            \n            # Write header\n            writer.writeheader()\n            \n            # Write data\n            records_written = 0\n            for record in data:\n                try:\n                    writer.writerow(record)\n                    records_written += 1\n                except Exception as e:\n                    self.logger.error(f\"Failed to write record: {str(e)}\")\n                    continue\n        \n        return records_written\n    \n    async def _write_metadata(self, data: List[Dict], output_file: Path, warnings: List[str]):\n        \"\"\"Write metadata file alongside CSV\"\"\"\n        metadata_file = output_file.with_suffix('.csv.meta.json')\n        \n        # Calculate statistics\n        total_records = len(data)\n        fields_with_data = {}\n        \n        for field in data[0].keys() if data else []:\n            filled_count = sum(1 for record in data if record.get(field))\n            fields_with_data[field] = {\n                'filled_count': filled_count,\n                'fill_percentage': (filled_count / total_records) * 100 if total_records > 0 else 0\n            }\n        \n        metadata = {\n            'export_timestamp': datetime.now().isoformat(),\n            'csv_file': output_file.name,\n            'total_records': total_records,\n            'field_statistics': fields_with_data,\n            'warnings': warnings,\n            'export_format': 'CSV',\n            'encoding': 'utf-8',\n            'field_order': list(data[0].keys()) if data else []\n        }\n        \n        import json\n        with open(metadata_file, 'w', encoding='utf-8') as f:\n            json.dump(metadata, f, indent=2, default=str)\n        \n        self.logger.debug(f\"Metadata written to {metadata_file}\")\n    \n    def validate_csv_format(self, file_path: str) -> Dict[str, Any]:\n        \"\"\"Validate existing CSV format compatibility\"\"\"\n        try:\n            # Try to read the CSV\n            df = pd.read_csv(file_path)\n            \n            # Check field compatibility\n            existing_fields = set(df.columns)\n            standard_fields = set(self.STANDARD_FIELDS)\n            \n            missing_standard = standard_fields - existing_fields\n            extra_fields = existing_fields - standard_fields - set(self.OPTIONAL_FIELDS)\n            \n            # Check data quality\n            issues = []\n            if df.empty:\n                issues.append(\"File is empty\")\n            \n            # Check for missing critical fields\n            if 'business_name' not in existing_fields:\n                issues.append(\"Missing critical field: business_name\")\n            \n            # Check for contact info\n            contact_fields = ['primary_email', 'primary_phone']\n            if not any(field in existing_fields for field in contact_fields):\n                issues.append(\"No contact information fields found\")\n            \n            return {\n                'valid': len(issues) == 0,\n                'record_count': len(df),\n                'field_count': len(df.columns),\n                'missing_standard_fields': list(missing_standard),\n                'extra_fields': list(extra_fields),\n                'issues': issues,\n                'sample_record': df.iloc[0].to_dict() if not df.empty else {}\n            }\n            \n        except Exception as e:\n            return {\n                'valid': False,\n                'error': str(e),\n                'record_count': 0,\n                'field_count': 0\n            }\n    \n    def convert_to_standard_format(self, input_file: str, output_file: str) -> ExportResult:\n        \"\"\"Convert existing CSV to standard format\"\"\"\n        try:\n            # Read existing CSV\n            df = pd.read_csv(input_file)\n            \n            # Convert to list of dictionaries\n            data = df.to_dict('records')\n            \n            # Export in standard format\n            import asyncio\n            result = asyncio.run(self.export(data, output_file))\n            \n            return result\n            \n        except Exception as e:\n            return ExportResult(\n                success=False,\n                file_path=output_file,\n                records_exported=0,\n                error_message=f\"Conversion failed: {str(e)}\"\n            )\n    \n    def merge_csv_files(self, input_files: List[str], output_file: str, \n                       remove_duplicates: bool = True) -> ExportResult:\n        \"\"\"Merge multiple CSV files into one\"\"\"\n        try:\n            all_data = []\n            seen_ids = set() if remove_duplicates else None\n            \n            for file_path in input_files:\n                df = pd.read_csv(file_path)\n                \n                for _, row in df.iterrows():\n                    record = row.to_dict()\n                    \n                    # Handle duplicates if requested\n                    if remove_duplicates:\n                        record_id = record.get('lead_id')\n                        if record_id in seen_ids:\n                            continue\n                        if record_id:\n                            seen_ids.add(record_id)\n                    \n                    all_data.append(record)\n            \n            # Export merged data\n            import asyncio\n            result = asyncio.run(self.export(all_data, output_file))\n            \n            return result\n            \n        except Exception as e:\n            return ExportResult(\n                success=False,\n                file_path=output_file,\n                records_exported=0,\n                error_message=f\"Merge failed: {str(e)}\"\n            )