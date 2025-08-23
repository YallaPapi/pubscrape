"""
Export Pipeline for VRSEN PubScrape

Comprehensive data export pipeline supporting multiple formats,
transformations, and delivery methods.
"""

import json
import csv
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
import pandas as pd
from dataclasses import dataclass, field
import zipfile
import gzip


@dataclass
class ExportConfig:
    """Export configuration"""
    format: str = "csv"
    include_metadata: bool = True
    compress: bool = False
    split_large_files: bool = False
    max_file_size_mb: int = 100
    custom_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    transformations: Optional[Dict[str, str]] = None


class ExportPipeline:
    """
    Comprehensive export pipeline for lead data.
    
    Features:
    - Multiple export formats (CSV, JSON, Excel, XML)
    - Data transformation and filtering
    - File compression and splitting
    - Metadata inclusion
    - Custom field mapping
    - Batch processing
    - Quality validation before export
    """
    
    def __init__(self, config: Any, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Supported formats and their handlers
        self.format_handlers = {
            'csv': self._export_csv,
            'json': self._export_json,
            'xlsx': self._export_excel,
            'xml': self._export_xml,
            'jsonl': self._export_jsonl,
            'tsv': self._export_tsv
        }
        
        self.logger.info("Export pipeline initialized")
    
    async def export(self, input_file: str, format: str = "csv",
                    output_dir: str = "output", 
                    include_metadata: bool = True,
                    custom_config: Optional[ExportConfig] = None) -> List[str]:
        """
        Export data to specified format.
        
        Args:
            input_file: Path to input file
            format: Export format
            output_dir: Output directory
            include_metadata: Include metadata in export
            custom_config: Custom export configuration
            
        Returns:
            List of generated output files
        """
        try:
            self.logger.info(f"Starting export: {input_file} -> {format}")
            
            # Load data
            data = await self._load_data(input_file)
            if not data:
                raise ValueError(f"No data found in file: {input_file}")
            
            # Setup export configuration
            export_config = custom_config or ExportConfig(
                format=format,
                include_metadata=include_metadata,
                compress=self.config.export.compress_output,
                split_large_files=self.config.export.split_large_files,
                max_file_size_mb=self.config.export.max_file_size_mb
            )
            
            # Validate format
            if format not in self.format_handlers:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Prepare output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate base filename
            base_name = Path(input_file).stem
            timestamp = datetime.now().strftime(self.config.export.timestamp_format)
            
            # Transform data if needed
            transformed_data = await self._transform_data(data, export_config)
            
            # Add metadata if requested
            if export_config.include_metadata:
                metadata = self._generate_metadata(input_file, len(data), export_config)
                transformed_data = self._merge_metadata(transformed_data, metadata)
            
            # Export data
            output_files = await self._export_data(
                transformed_data, 
                format, 
                output_path, 
                base_name, 
                timestamp, 
                export_config
            )
            
            self.logger.info(f"Export completed: {len(output_files)} files generated")
            return output_files
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            raise
    
    async def _load_data(self, input_file: str) -> List[Dict[str, Any]]:
        """Load data from input file"""
        try:
            file_path = Path(input_file)
            
            if file_path.suffix.lower() == '.csv':
                return await self._load_csv(file_path)
            elif file_path.suffix.lower() == '.json':
                return await self._load_json(file_path)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                return await self._load_excel(file_path)
            else:
                raise ValueError(f"Unsupported input format: {file_path.suffix}")
                
        except Exception as e:
            self.logger.error(f"Failed to load data from {input_file}: {e}")
            raise
    
    async def _load_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load data from CSV file"""
        data = []
        with open(file_path, 'r', encoding=self.config.export.csv_encoding) as f:
            reader = csv.DictReader(f, delimiter=self.config.export.csv_delimiter)
            for row in reader:
                data.append(row)
        return data
    
    async def _load_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load data from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, dict):
            if 'leads' in data:
                return data['leads']
            elif 'data' in data:
                return data['data']
            else:
                return [data]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Unsupported JSON structure")
    
    async def _load_excel(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load data from Excel file"""
        df = pd.read_excel(file_path)
        return df.to_dict('records')
    
    async def _transform_data(self, data: List[Dict[str, Any]], 
                            config: ExportConfig) -> List[Dict[str, Any]]:
        """Transform data based on configuration"""
        transformed_data = []
        
        for record in data:
            transformed_record = record.copy()
            
            # Apply custom field selection
            if config.custom_fields:
                transformed_record = {
                    field: transformed_record.get(field, '')
                    for field in config.custom_fields
                }
            
            # Exclude specified fields
            if config.exclude_fields:
                for field in config.exclude_fields:
                    transformed_record.pop(field, None)
            
            # Apply field transformations
            if config.transformations:
                for field, transformation in config.transformations.items():
                    if field in transformed_record:
                        transformed_record[field] = self._apply_transformation(
                            transformed_record[field], transformation
                        )
            
            transformed_data.append(transformed_record)
        
        return transformed_data
    
    def _apply_transformation(self, value: Any, transformation: str) -> Any:
        """Apply transformation to a field value"""
        try:
            if transformation == 'upper':
                return str(value).upper()
            elif transformation == 'lower':
                return str(value).lower()
            elif transformation == 'title':
                return str(value).title()
            elif transformation == 'strip':
                return str(value).strip()
            elif transformation == 'phone_format':
                return self._format_phone(str(value))
            elif transformation == 'email_lower':
                return str(value).lower().strip()
            else:
                return value
        except Exception:
            return value
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number"""
        import re
        # Remove all non-digits except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Format US phone numbers
        if len(cleaned) == 10 and cleaned.isdigit():
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        else:
            return phone
    
    def _generate_metadata(self, input_file: str, record_count: int, 
                          config: ExportConfig) -> Dict[str, Any]:
        """Generate export metadata"""
        return {
            'export_info': {
                'source_file': input_file,\n                'export_timestamp': datetime.now().isoformat(),\n                'export_format': config.format,\n                'record_count': record_count,\n                'compression_enabled': config.compress,\n                'metadata_included': config.include_metadata\n            },\n            'system_info': {\n                'version': '1.0.0',\n                'platform': 'VRSEN PubScrape',\n                'configuration': {\n                    'csv_delimiter': self.config.export.csv_delimiter,\n                    'csv_encoding': self.config.export.csv_encoding,\n                    'max_file_size_mb': config.max_file_size_mb\n                }\n            }\n        }\n    \n    def _merge_metadata(self, data: List[Dict[str, Any]], \n                       metadata: Dict[str, Any]) -> Dict[str, Any]:\n        \"\"\"Merge data with metadata\"\"\"\n        return {\n            'metadata': metadata,\n            'data': data\n        }\n    \n    async def _export_data(self, data: Any, format: str, output_path: Path,\n                          base_name: str, timestamp: str, \n                          config: ExportConfig) -> List[str]:\n        \"\"\"Export data using appropriate handler\"\"\"\n        handler = self.format_handlers[format]\n        output_files = await handler(data, output_path, base_name, timestamp, config)\n        \n        # Apply compression if requested\n        if config.compress:\n            compressed_files = []\n            for file_path in output_files:\n                compressed_file = await self._compress_file(file_path)\n                compressed_files.append(compressed_file)\n            output_files = compressed_files\n        \n        return output_files\n    \n    async def _export_csv(self, data: Any, output_path: Path, base_name: str,\n                         timestamp: str, config: ExportConfig) -> List[str]:\n        \"\"\"Export to CSV format\"\"\"\n        # Handle metadata structure\n        if isinstance(data, dict) and 'data' in data:\n            records = data['data']\n            metadata = data.get('metadata', {})\n        else:\n            records = data if isinstance(data, list) else [data]\n            metadata = {}\n        \n        if not records:\n            raise ValueError(\"No records to export\")\n        \n        output_files = []\n        \n        # Split large files if needed\n        if config.split_large_files and len(records) > 1000:  # Arbitrary split threshold\n            chunk_size = 1000\n            for i, chunk_start in enumerate(range(0, len(records), chunk_size)):\n                chunk = records[chunk_start:chunk_start + chunk_size]\n                filename = f\"{base_name}_part{i+1}_{timestamp}.csv\"\n                file_path = output_path / filename\n                \n                await self._write_csv_chunk(chunk, file_path, config)\n                output_files.append(str(file_path))\n        else:\n            filename = f\"{base_name}_{timestamp}.csv\"\n            file_path = output_path / filename\n            \n            await self._write_csv_chunk(records, file_path, config)\n            output_files.append(str(file_path))\n        \n        # Export metadata separately if present\n        if metadata and config.include_metadata:\n            metadata_file = output_path / f\"{base_name}_metadata_{timestamp}.json\"\n            with open(metadata_file, 'w', encoding='utf-8') as f:\n                json.dump(metadata, f, indent=2, default=str)\n            output_files.append(str(metadata_file))\n        \n        return output_files\n    \n    async def _write_csv_chunk(self, records: List[Dict[str, Any]], \n                              file_path: Path, config: ExportConfig):\n        \"\"\"Write CSV chunk to file\"\"\"\n        if not records:\n            return\n        \n        with open(file_path, 'w', newline='', encoding=self.config.export.csv_encoding) as f:\n            fieldnames = list(records[0].keys())\n            writer = csv.DictWriter(f, fieldnames=fieldnames, \n                                  delimiter=self.config.export.csv_delimiter)\n            writer.writeheader()\n            writer.writerows(records)\n    \n    async def _export_json(self, data: Any, output_path: Path, base_name: str,\n                          timestamp: str, config: ExportConfig) -> List[str]:\n        \"\"\"Export to JSON format\"\"\"\n        filename = f\"{base_name}_{timestamp}.json\"\n        file_path = output_path / filename\n        \n        with open(file_path, 'w', encoding='utf-8') as f:\n            json.dump(data, f, indent=2, default=str, ensure_ascii=False)\n        \n        return [str(file_path)]\n    \n    async def _export_excel(self, data: Any, output_path: Path, base_name: str,\n                           timestamp: str, config: ExportConfig) -> List[str]:\n        \"\"\"Export to Excel format\"\"\"\n        # Handle metadata structure\n        if isinstance(data, dict) and 'data' in data:\n            records = data['data']\n            metadata = data.get('metadata', {})\n        else:\n            records = data if isinstance(data, list) else [data]\n            metadata = {}\n        \n        filename = f\"{base_name}_{timestamp}.xlsx\"\n        file_path = output_path / filename\n        \n        # Create Excel file with multiple sheets\n        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:\n            # Main data sheet\n            if records:\n                df = pd.DataFrame(records)\n                df.to_excel(writer, sheet_name='Leads', index=False)\n            \n            # Metadata sheet if available\n            if metadata and config.include_metadata:\n                metadata_df = pd.DataFrame([\n                    {'Key': k, 'Value': str(v)} \n                    for k, v in self._flatten_dict(metadata).items()\n                ])\n                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)\n        \n        return [str(file_path)]\n    \n    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:\n        \"\"\"Flatten nested dictionary\"\"\"\n        items = []\n        for k, v in d.items():\n            new_key = f\"{parent_key}{sep}{k}\" if parent_key else k\n            if isinstance(v, dict):\n                items.extend(self._flatten_dict(v, new_key, sep=sep).items())\n            else:\n                items.append((new_key, v))\n        return dict(items)\n    \n    async def _export_xml(self, data: Any, output_path: Path, base_name: str,\n                         timestamp: str, config: ExportConfig) -> List[str]:\n        \"\"\"Export to XML format\"\"\"\n        # Handle metadata structure\n        if isinstance(data, dict) and 'data' in data:\n            records = data['data']\n            metadata = data.get('metadata', {})\n        else:\n            records = data if isinstance(data, list) else [data]\n            metadata = {}\n        \n        filename = f\"{base_name}_{timestamp}.xml\"\n        file_path = output_path / filename\n        \n        # Create XML structure\n        root = ET.Element('export')\n        \n        # Add metadata if available\n        if metadata and config.include_metadata:\n            metadata_elem = ET.SubElement(root, 'metadata')\n            self._dict_to_xml(metadata, metadata_elem)\n        \n        # Add leads data\n        leads_elem = ET.SubElement(root, 'leads')\n        leads_elem.set('count', str(len(records)))\n        \n        for record in records:\n            lead_elem = ET.SubElement(leads_elem, 'lead')\n            self._dict_to_xml(record, lead_elem)\n        \n        # Write XML file\n        tree = ET.ElementTree(root)\n        ET.indent(tree, space=\"  \", level=0)\n        tree.write(file_path, encoding='utf-8', xml_declaration=True)\n        \n        return [str(file_path)]\n    \n    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element):\n        \"\"\"Convert dictionary to XML elements\"\"\"\n        for key, value in data.items():\n            # Clean key name for XML\n            clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))\n            \n            if isinstance(value, dict):\n                elem = ET.SubElement(parent, clean_key)\n                self._dict_to_xml(value, elem)\n            elif isinstance(value, list):\n                for item in value:\n                    elem = ET.SubElement(parent, clean_key)\n                    if isinstance(item, dict):\n                        self._dict_to_xml(item, elem)\n                    else:\n                        elem.text = str(item)\n            else:\n                elem = ET.SubElement(parent, clean_key)\n                elem.text = str(value) if value is not None else ''\n    \n    async def _export_jsonl(self, data: Any, output_path: Path, base_name: str,\n                           timestamp: str, config: ExportConfig) -> List[str]:\n        \"\"\"Export to JSON Lines format\"\"\"\n        # Handle metadata structure\n        if isinstance(data, dict) and 'data' in data:\n            records = data['data']\n        else:\n            records = data if isinstance(data, list) else [data]\n        \n        filename = f\"{base_name}_{timestamp}.jsonl\"\n        file_path = output_path / filename\n        \n        with open(file_path, 'w', encoding='utf-8') as f:\n            for record in records:\n                json.dump(record, f, default=str, ensure_ascii=False)\n                f.write('\\n')\n        \n        return [str(file_path)]\n    \n    async def _export_tsv(self, data: Any, output_path: Path, base_name: str,\n                         timestamp: str, config: ExportConfig) -> List[str]:\n        \"\"\"Export to TSV format\"\"\"\n        # Handle metadata structure\n        if isinstance(data, dict) and 'data' in data:\n            records = data['data']\n        else:\n            records = data if isinstance(data, list) else [data]\n        \n        if not records:\n            raise ValueError(\"No records to export\")\n        \n        filename = f\"{base_name}_{timestamp}.tsv\"\n        file_path = output_path / filename\n        \n        with open(file_path, 'w', newline='', encoding='utf-8') as f:\n            fieldnames = list(records[0].keys())\n            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\\t')\n            writer.writeheader()\n            writer.writerows(records)\n        \n        return [str(file_path)]\n    \n    async def _compress_file(self, file_path: str) -> str:\n        \"\"\"Compress file using gzip\"\"\"\n        input_path = Path(file_path)\n        output_path = input_path.with_suffix(input_path.suffix + '.gz')\n        \n        with open(input_path, 'rb') as f_in:\n            with gzip.open(output_path, 'wb') as f_out:\n                f_out.writelines(f_in)\n        \n        # Remove original file\n        input_path.unlink()\n        \n        return str(output_path)\n    \n    def get_supported_formats(self) -> List[str]:\n        \"\"\"Get list of supported export formats\"\"\"\n        return list(self.format_handlers.keys())\n    \n    def validate_export_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:\n        \"\"\"Validate data before export\"\"\"\n        if not data:\n            return {'valid': False, 'error': 'No data to export'}\n        \n        if not isinstance(data, list):\n            return {'valid': False, 'error': 'Data must be a list of records'}\n        \n        # Check for consistent field structure\n        if len(data) > 1:\n            first_keys = set(data[0].keys())\n            for i, record in enumerate(data[1:], 1):\n                record_keys = set(record.keys())\n                if record_keys != first_keys:\n                    return {\n                        'valid': False, \n                        'error': f'Inconsistent fields in record {i}',\n                        'missing_fields': first_keys - record_keys,\n                        'extra_fields': record_keys - first_keys\n                    }\n        \n        return {\n            'valid': True,\n            'record_count': len(data),\n            'fields': list(data[0].keys()) if data else [],\n            'estimated_size_mb': len(str(data)) / 1024 / 1024\n        }"