"""
Export Command Implementation

Handles lead export to various formats with metadata control and comprehensive logging.
"""

from typing import List
from argparse import Namespace

from .base import BaseCommand
from src.pipeline.export_pipeline import ExportPipeline


class ExportCommand(BaseCommand):
    """Command for exporting leads to different formats"""
    
    def add_arguments(self, parser):
        """Add export command arguments"""
        parser.add_argument(
            '--input', '-i', required=True,
            help='Input CSV file to export'
        )
        parser.add_argument(
            '--format', '-f', choices=['csv', 'xlsx', 'json', 'xml'],
            default='csv', help='Output format'
        )
        parser.add_argument(
            '--output-dir', '-o',
            help='Output directory for exported files'
        )
        parser.add_argument(
            '--no-metadata', action='store_true',
            help='Exclude metadata from export'
        )
    
    async def execute(self, args: Namespace) -> int:
        """
        Execute export pipeline.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"📤 Starting export: {args.input}")
            
            # Validate input file exists
            input_path = self._validate_file_path(args.input, must_exist=True)
            if not input_path:
                return 1
            
            # Determine output directory
            output_dir = args.output_dir or self.config_manager.export.output_directory
            output_path = self._ensure_output_directory(output_dir)
            if not output_path:
                return 1
            
            # Create export pipeline
            exporter = ExportPipeline(
                config=self.config_manager.config,
                logger=self.logger
            )
            
            # Run export
            output_files = await exporter.export(
                input_file=str(input_path),
                format=args.format,
                output_dir=str(output_path),
                include_metadata=not args.no_metadata
            )
            
            # Log results
            self.logger.info(f"✅ Export completed successfully")
            self.logger.info(f"📊 Format: {args.format.upper()}")
            
            for file_path in output_files:
                self.logger.info(f"📁 Generated: {file_path}")
            
            return 0
            
        except Exception as e:
            return self._handle_command_error(e, "Export failed")