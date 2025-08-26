"""
Validate Command Implementation

Handles lead validation with configurable strictness levels and comprehensive reporting.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from argparse import Namespace

from .base import BaseCommand
from src.pipeline.validation_pipeline import ValidationPipeline


class ValidateCommand(BaseCommand):
    """Command for validating existing leads"""
    
    def add_arguments(self, parser):
        """Add validate command arguments"""
        parser.add_argument(
            '--input', '-i', required=True,
            help='Input CSV file to validate'
        )
        parser.add_argument(
            '--level', choices=['strict', 'moderate', 'lenient'],
            default='strict', help='Validation strictness level'
        )
        parser.add_argument(
            '--output-dir', '-o',
            help='Output directory for validation results'
        )
    
    async def execute(self, args: Namespace) -> int:
        """
        Execute validation pipeline.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"🔍 Starting validation: {args.input}")
            
            # Validate input file exists
            input_path = self._validate_file_path(args.input, must_exist=True)
            if not input_path:
                return 1
            
            # Determine output directory
            output_dir = args.output_dir or self.config_manager.export.output_directory
            output_path = self._ensure_output_directory(output_dir)
            if not output_path:
                return 1
            
            # Create validation pipeline
            validator = ValidationPipeline(
                config=self.config_manager.config,
                error_handler=self.error_handler,
                logger=self.logger
            )
            
            # Run validation
            results = await validator.validate_file(
                input_file=str(input_path),
                validation_level=args.level,
                output_dir=str(output_path)
            )
            
            # Generate validation report
            self._generate_validation_report(results, args.input)
            
            # Log summary
            valid_count = results.get('valid_count', 0)
            invalid_count = results.get('invalid_count', 0)
            total_count = valid_count + invalid_count
            
            self.logger.info(f"✅ Validation completed successfully")
            self.logger.info(f"📊 Valid leads: {valid_count}/{total_count} ({valid_count/total_count*100:.1f}%)")
            self.logger.info(f"❌ Invalid leads: {invalid_count}/{total_count} ({invalid_count/total_count*100:.1f}%)")
            
            return 0
            
        except Exception as e:
            return self._handle_command_error(e, "Validation failed")
    
    def _generate_validation_report(self, results: Dict[str, Any], input_file: str):
        """Generate validation report"""
        try:
            report_data = {
                'input_file': input_file,
                'timestamp': datetime.now().isoformat(),
                'version': "1.0.0",  # TODO: Get from central version location
                'results': results
            }
            
            output_dir = self._ensure_output_directory(self.config_manager.export.output_directory)
            if not output_dir:
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = output_dir / f"validation_report_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.logger.info(f"📊 Validation report saved: {report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate validation report: {e}")