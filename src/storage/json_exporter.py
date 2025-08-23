"""
JSON Export with Metadata Tracking

Handles JSON export with structured metadata, schema validation,
and support for complex nested data structures.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib


@dataclass
class JSONExportResult:
    """Result of JSON export operation"""
    success: bool
    file_path: str
    records_exported: int
    metadata_file: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class ExportMetadata:
    """Metadata for JSON export"""
    export_timestamp: str
    total_records: int
    schema_version: str
    data_hash: str
    field_schema: Dict[str, Any]
    processing_info: Dict[str, Any]
    quality_metrics: Dict[str, Any]


class JSONExporter:
    """JSON exporter with metadata tracking"""
    
    SCHEMA_VERSION = "1.0.0"
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def export(self, 
                    data: List[Dict[str, Any]], 
                    output_path: str,
                    metadata: Dict[str, Any] = None,
                    include_schema: bool = True,
                    pretty_print: bool = True) -> JSONExportResult:
        """Export data to JSON with metadata"""
        
        if not data:
            return JSONExportResult(
                success=False,
                file_path=output_path,
                records_exported=0,
                error_message="No data to export"
            )
        
        try:
            # Prepare output path
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate and clean data
            cleaned_data, warnings = self._validate_and_clean_data(data)
            
            # Generate metadata
            export_metadata = self._generate_metadata(cleaned_data, metadata)
            
            # Create export structure
            export_structure = {
                'metadata': asdict(export_metadata),
                'data': cleaned_data
            }
            
            # Add schema if requested
            if include_schema:
                export_structure['schema'] = self._generate_schema(cleaned_data)
            
            # Write JSON file
            self._write_json_file(export_structure, output_file, pretty_print)
            
            # Write separate metadata file
            metadata_file = await self._write_metadata_file(export_metadata, output_file)
            
            self.logger.info(f"JSON export successful: {len(cleaned_data)} records to {output_file}")
            
            return JSONExportResult(
                success=True,
                file_path=str(output_file),
                records_exported=len(cleaned_data),
                metadata_file=metadata_file,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"JSON export failed: {str(e)}")
            return JSONExportResult(
                success=False,
                file_path=output_path,
                records_exported=0,
                error_message=str(e)
            )
    
    def _validate_and_clean_data(self, data: List[Dict]) -> tuple:
        """Validate and clean data for JSON export"""
        cleaned_data = []
        warnings = []
        
        for i, record in enumerate(data):
            try:
                cleaned_record = self._clean_record(record)
                cleaned_data.append(cleaned_record)
                
                # Validate record structure
                validation_warnings = self._validate_record_structure(cleaned_record, i)
                warnings.extend(validation_warnings)
                
            except Exception as e:
                warnings.append(f"Record {i}: Failed to clean - {str(e)}")
                continue
        
        return cleaned_data, warnings
    
    def _clean_record(self, record: Dict) -> Dict:
        """Clean individual record for JSON serialization"""
        cleaned = {}\n        \n        for key, value in record.items():\n            # Clean key name\n            clean_key = str(key).strip()\n            \n            # Clean value\n            if value is None:\n                cleaned[clean_key] = None\n            elif isinstance(value, (str, int, float, bool)):\n                cleaned[clean_key] = value\n            elif isinstance(value, (list, tuple)):\n                cleaned[clean_key] = self._clean_list(value)\n            elif isinstance(value, dict):\n                cleaned[clean_key] = self._clean_record(value)  # Recursive\n            else:\n                # Convert other types to string\n                cleaned[clean_key] = str(value)\n        \n        return cleaned\n    \n    def _clean_list(self, lst: Union[list, tuple]) -> List:\n        \"\"\"Clean list values for JSON serialization\"\"\"\n        cleaned_list = []\n        \n        for item in lst:\n            if isinstance(item, dict):\n                cleaned_list.append(self._clean_record(item))\n            elif isinstance(item, (list, tuple)):\n                cleaned_list.append(self._clean_list(item))\n            elif item is None:\n                cleaned_list.append(None)\n            elif isinstance(item, (str, int, float, bool)):\n                cleaned_list.append(item)\n            else:\n                cleaned_list.append(str(item))\n        \n        return cleaned_list\n    \n    def _validate_record_structure(self, record: Dict, record_index: int) -> List[str]:\n        \"\"\"Validate record structure and return warnings\"\"\"\n        warnings = []\n        \n        # Check for required fields\n        required_fields = ['lead_id', 'business_name']\n        for field in required_fields:\n            if field not in record or not record[field]:\n                warnings.append(f\"Record {record_index}: Missing required field '{field}'\")\n        \n        # Check for empty records\n        non_empty_fields = sum(1 for v in record.values() if v is not None and str(v).strip())\n        if non_empty_fields < 2:\n            warnings.append(f\"Record {record_index}: Very sparse data (only {non_empty_fields} filled fields)\")\n        \n        # Check for oversized fields\n        for key, value in record.items():\n            if isinstance(value, str) and len(value) > 10000:\n                warnings.append(f\"Record {record_index}: Field '{key}' is very large ({len(value)} chars)\")\n        \n        return warnings\n    \n    def _generate_metadata(self, data: List[Dict], custom_metadata: Dict = None) -> ExportMetadata:\n        \"\"\"Generate comprehensive metadata\"\"\"\n        \n        # Calculate data hash for integrity\n        data_str = json.dumps(data, sort_keys=True, default=str)\n        data_hash = hashlib.sha256(data_str.encode()).hexdigest()\n        \n        # Generate field schema\n        field_schema = self._analyze_field_schema(data)\n        \n        # Calculate quality metrics\n        quality_metrics = self._calculate_quality_metrics(data)\n        \n        # Processing info\n        processing_info = {\n            'export_timestamp': datetime.now().isoformat(),\n            'exporter_version': '1.0.0',\n            'custom_metadata': custom_metadata or {}\n        }\n        \n        return ExportMetadata(\n            export_timestamp=datetime.now().isoformat(),\n            total_records=len(data),\n            schema_version=self.SCHEMA_VERSION,\n            data_hash=data_hash,\n            field_schema=field_schema,\n            processing_info=processing_info,\n            quality_metrics=quality_metrics\n        )\n    \n    def _analyze_field_schema(self, data: List[Dict]) -> Dict[str, Any]:\n        \"\"\"Analyze data to generate field schema\"\"\"\n        if not data:\n            return {}\n        \n        schema = {}\n        total_records = len(data)\n        \n        # Get all unique fields\n        all_fields = set()\n        for record in data:\n            all_fields.update(record.keys())\n        \n        # Analyze each field\n        for field in all_fields:\n            field_info = {\n                'type': self._determine_field_type(data, field),\n                'nullable': self._is_field_nullable(data, field),\n                'fill_rate': self._calculate_fill_rate(data, field),\n                'unique_values': self._count_unique_values(data, field),\n                'sample_values': self._get_sample_values(data, field)\n            }\n            \n            schema[field] = field_info\n        \n        return schema\n    \n    def _determine_field_type(self, data: List[Dict], field: str) -> str:\n        \"\"\"Determine the primary type of a field\"\"\"\n        types = {}\n        \n        for record in data:\n            value = record.get(field)\n            if value is not None:\n                value_type = type(value).__name__\n                types[value_type] = types.get(value_type, 0) + 1\n        \n        if not types:\n            return 'null'\n        \n        # Return most common type\n        return max(types.items(), key=lambda x: x[1])[0]\n    \n    def _is_field_nullable(self, data: List[Dict], field: str) -> bool:\n        \"\"\"Check if field can be null\"\"\"\n        for record in data:\n            if record.get(field) is None:\n                return True\n        return False\n    \n    def _calculate_fill_rate(self, data: List[Dict], field: str) -> float:\n        \"\"\"Calculate the fill rate for a field\"\"\"\n        if not data:\n            return 0.0\n        \n        filled_count = sum(1 for record in data \n                          if record.get(field) is not None and str(record[field]).strip())\n        \n        return round(filled_count / len(data), 3)\n    \n    def _count_unique_values(self, data: List[Dict], field: str) -> int:\n        \"\"\"Count unique values in a field\"\"\"\n        unique_values = set()\n        \n        for record in data:\n            value = record.get(field)\n            if value is not None:\n                # Convert to string for uniqueness check\n                unique_values.add(str(value))\n        \n        return len(unique_values)\n    \n    def _get_sample_values(self, data: List[Dict], field: str, limit: int = 5) -> List[Any]:\n        \"\"\"Get sample values for a field\"\"\"\n        values = []\n        \n        for record in data:\n            value = record.get(field)\n            if value is not None and str(value).strip():\n                if value not in values:\n                    values.append(value)\n                    if len(values) >= limit:\n                        break\n        \n        return values\n    \n    def _calculate_quality_metrics(self, data: List[Dict]) -> Dict[str, Any]:\n        \"\"\"Calculate data quality metrics\"\"\"\n        if not data:\n            return {}\n        \n        total_records = len(data)\n        \n        # Contact information completeness\n        has_email = sum(1 for record in data if record.get('primary_email'))\n        has_phone = sum(1 for record in data if record.get('primary_phone'))\n        has_contact = sum(1 for record in data \n                         if record.get('primary_email') or record.get('primary_phone'))\n        \n        # Business information completeness\n        has_business_name = sum(1 for record in data if record.get('business_name'))\n        has_website = sum(1 for record in data if record.get('website'))\n        \n        # Calculate scores\n        contact_completeness = has_contact / total_records if total_records > 0 else 0\n        email_completeness = has_email / total_records if total_records > 0 else 0\n        phone_completeness = has_phone / total_records if total_records > 0 else 0\n        business_completeness = has_business_name / total_records if total_records > 0 else 0\n        website_completeness = has_website / total_records if total_records > 0 else 0\n        \n        # Overall quality score\n        quality_weights = {\n            'contact_info': 0.4,\n            'business_info': 0.3,\n            'website_info': 0.2,\n            'completeness': 0.1\n        }\n        \n        overall_score = (\n            contact_completeness * quality_weights['contact_info'] +\n            business_completeness * quality_weights['business_info'] +\n            website_completeness * quality_weights['website_info'] +\n            (sum([email_completeness, phone_completeness, website_completeness]) / 3) * quality_weights['completeness']\n        )\n        \n        return {\n            'total_records': total_records,\n            'contact_completeness': round(contact_completeness, 3),\n            'email_completeness': round(email_completeness, 3),\n            'phone_completeness': round(phone_completeness, 3),\n            'business_completeness': round(business_completeness, 3),\n            'website_completeness': round(website_completeness, 3),\n            'overall_quality_score': round(overall_score, 3),\n            'records_with_contact_info': has_contact,\n            'records_with_email': has_email,\n            'records_with_phone': has_phone,\n            'actionable_records': sum(1 for record in data if record.get('is_actionable'))\n        }\n    \n    def _generate_schema(self, data: List[Dict]) -> Dict[str, Any]:\n        \"\"\"Generate JSON schema for the data\"\"\"\n        if not data:\n            return {}\n        \n        # Basic JSON Schema structure\n        schema = {\n            \"$schema\": \"http://json-schema.org/draft-07/schema#\",\n            \"type\": \"object\",\n            \"properties\": {\n                \"metadata\": {\n                    \"type\": \"object\",\n                    \"description\": \"Export metadata\"\n                },\n                \"data\": {\n                    \"type\": \"array\",\n                    \"items\": {\n                        \"type\": \"object\",\n                        \"properties\": self._generate_record_schema(data)\n                    }\n                }\n            },\n            \"required\": [\"metadata\", \"data\"]\n        }\n        \n        return schema\n    \n    def _generate_record_schema(self, data: List[Dict]) -> Dict[str, Any]:\n        \"\"\"Generate schema for individual records\"\"\"\n        properties = {}\n        \n        # Get all fields\n        all_fields = set()\n        for record in data:\n            all_fields.update(record.keys())\n        \n        # Define schema for each field\n        for field in all_fields:\n            field_type = self._determine_field_type(data, field)\n            \n            # Map Python types to JSON Schema types\n            type_mapping = {\n                'str': 'string',\n                'int': 'integer',\n                'float': 'number',\n                'bool': 'boolean',\n                'list': 'array',\n                'dict': 'object',\n                'NoneType': 'null'\n            }\n            \n            json_type = type_mapping.get(field_type, 'string')\n            \n            field_schema = {\n                \"type\": json_type\n            }\n            \n            # Add nullable if field can be null\n            if self._is_field_nullable(data, field):\n                field_schema[\"type\"] = [json_type, \"null\"]\n            \n            # Add description for known fields\n            descriptions = {\n                'lead_id': 'Unique identifier for the lead',\n                'business_name': 'Name of the business',\n                'primary_email': 'Primary email contact',\n                'primary_phone': 'Primary phone contact',\n                'website': 'Business website URL',\n                'lead_score': 'Quality score of the lead (0-1)',\n                'is_actionable': 'Whether the lead has actionable contact info'\n            }\n            \n            if field in descriptions:\n                field_schema[\"description\"] = descriptions[field]\n            \n            properties[field] = field_schema\n        \n        return properties\n    \n    def _write_json_file(self, data: Dict, output_file: Path, pretty_print: bool):\n        \"\"\"Write JSON data to file\"\"\"\n        with open(output_file, 'w', encoding='utf-8') as f:\n            if pretty_print:\n                json.dump(data, f, indent=2, ensure_ascii=False, default=str)\n            else:\n                json.dump(data, f, ensure_ascii=False, default=str)\n    \n    async def _write_metadata_file(self, metadata: ExportMetadata, output_file: Path) -> str:\n        \"\"\"Write separate metadata file\"\"\"\n        metadata_file = output_file.with_suffix('.json.meta')\n        \n        with open(metadata_file, 'w', encoding='utf-8') as f:\n            json.dump(asdict(metadata), f, indent=2, default=str)\n        \n        self.logger.debug(f\"Metadata written to {metadata_file}\")\n        return str(metadata_file)\n    \n    def validate_json_format(self, file_path: str) -> Dict[str, Any]:\n        \"\"\"Validate existing JSON format\"\"\"\n        try:\n            with open(file_path, 'r', encoding='utf-8') as f:\n                data = json.load(f)\n            \n            # Check structure\n            is_valid_structure = isinstance(data, dict) and 'data' in data\n            \n            if is_valid_structure:\n                records = data['data']\n                metadata = data.get('metadata', {})\n                \n                return {\n                    'valid': True,\n                    'structure': 'structured',\n                    'has_metadata': 'metadata' in data,\n                    'record_count': len(records) if isinstance(records, list) else 0,\n                    'metadata_version': metadata.get('schema_version', 'unknown'),\n                    'sample_record': records[0] if records else {}\n                }\n            else:\n                # Check if it's a simple array\n                if isinstance(data, list):\n                    return {\n                        'valid': True,\n                        'structure': 'simple_array',\n                        'has_metadata': False,\n                        'record_count': len(data),\n                        'sample_record': data[0] if data else {}\n                    }\n                else:\n                    return {\n                        'valid': False,\n                        'error': 'Unknown JSON structure'\n                    }\n        \n        except Exception as e:\n            return {\n                'valid': False,\n                'error': str(e)\n            }\n    \n    def convert_to_structured_format(self, input_file: str, output_file: str) -> JSONExportResult:\n        \"\"\"Convert simple JSON array to structured format\"\"\"\n        try:\n            with open(input_file, 'r', encoding='utf-8') as f:\n                data = json.load(f)\n            \n            # Handle different input formats\n            if isinstance(data, list):\n                records = data\n            elif isinstance(data, dict) and 'data' in data:\n                records = data['data']\n            else:\n                raise ValueError(\"Unsupported JSON structure\")\n            \n            # Export in structured format\n            import asyncio\n            result = asyncio.run(self.export(records, output_file))\n            \n            return result\n            \n        except Exception as e:\n            return JSONExportResult(\n                success=False,\n                file_path=output_file,\n                records_exported=0,\n                error_message=f\"Conversion failed: {str(e)}\"\n            )"