#!/usr/bin/env python3
"""
VRSEN PubScrape - Main CLI Entry Point

Advanced multi-agent web scraping platform with Botasaurus integration,
Anti-detection capabilities, and comprehensive lead generation pipeline.

Usage:
    python main.py --help
    python main.py scrape --campaign campaigns/doctor_leads.yaml
    python main.py validate --input output/leads.csv
    python main.py export --input output/leads.csv --format csv
"""

import sys
import os
import argparse
import asyncio
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Core imports
# Config manager may not be available/valid in lightweight runs
try:
    from src.core.config_manager import config_manager  # type: ignore
except Exception:  # pragma: no cover
    class _DummyLogging:
        log_level = 'INFO'
        log_directory = 'logs'
        enable_console_logging = True
        enable_file_logging = False
    class _DummyExport:
        output_directory = 'output'
    class _DummyConfig:
        enable_metrics = False
        data_directory = 'output'
    class _DummyConfigManager:
        logging = _DummyLogging()
        export = _DummyExport()
        config = _DummyConfig()
        _config_file_path = '<defaults>'
        def load_from_file(self, *args, **kwargs):
            return True
        def validate(self):
            return True, []
        def set(self, *args, **kwargs):
            return None
    config_manager = _DummyConfigManager()
from src.utils.logger import setup_logging, get_logger
from src.utils.error_handler import ErrorHandler, RetryableError
from src.core.agency_factory import AgencyFactory
from src.pipeline.campaign_runner import CampaignRunner
from src.pipeline.validation_pipeline import ValidationPipeline
from src.pipeline.export_pipeline import ExportPipeline
from src.utils.performance_monitor import PerformanceMonitor
from src.utils.resume_manager import ResumeManager

# Version info
__version__ = "1.0.0"
__author__ = "VRSEN Agency"
__description__ = "Advanced Multi-Agent Web Scraping Platform"


class CLIApplication:
    """
    Main CLI application class that orchestrates all operations.
    """
    
    def __init__(self):
        self.logger = None
        self.error_handler = None
        self.performance_monitor = None
        self.resume_manager = None
        self.agency_factory = None
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n⚠️  Shutdown signal received. Cleaning up...")
        self.shutdown_requested = True
        
        if self.performance_monitor:
            self.performance_monitor.stop()
        
        if self.resume_manager:
            self.resume_manager.save_state()
        
        print("✅ Cleanup completed. Exiting.")
        sys.exit(0)
    
    def initialize(self, args: argparse.Namespace) -> bool:
        """
        Initialize the application with command line arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Lightweight bootstrap for quick command
            if getattr(args, 'command', None) == 'quick':
                self.logger = setup_logging(
                    level='INFO',
                    log_dir='logs',
                    enable_console=True,
                    enable_file=False
                )
                # Skip heavy subsystems for quick mode
                return True
            # Load configuration
            if args.config:
                if not config_manager.load_from_file(args.config):
                    print(f"❌ Failed to load configuration from {args.config}")
                    return False
            
            # Override config with CLI arguments
            self._apply_cli_overrides(args)
            
            # Validate configuration (non-fatal in regular mode if issues)
            try:
                is_valid, errors = config_manager.validate()
            except Exception as e:
                is_valid, errors = (False, [str(e)])
            if not is_valid:
                print(f"⚠️  Configuration issues detected:")
                for error in errors:
                    print(f"   • {error}")
                # Continue with defaults rather than failing hard
            
            # Setup logging
            self.logger = setup_logging(
                level=config_manager.logging.log_level,
                log_dir=config_manager.logging.log_directory,
                enable_console=config_manager.logging.enable_console_logging,
                enable_file=config_manager.logging.enable_file_logging
            )
            
            # Initialize error handler
            self.error_handler = ErrorHandler(
                max_retries=config_manager.search.retry_attempts,
                retry_delay=config_manager.search.retry_delay,
                logger=self.logger
            )
            
            # Initialize performance monitor
            if config_manager.config.enable_metrics:
                self.performance_monitor = PerformanceMonitor(
                    output_dir=config_manager.export.output_directory
                )
                self.performance_monitor.start()
            
            # Initialize resume manager
            self.resume_manager = ResumeManager(
                state_dir=Path(config_manager.config.data_directory) / "state"
            )
            
            # Initialize agency factory
            self.agency_factory = AgencyFactory(config_manager.config)
            
            self.logger.info(f"🚀 VRSEN PubScrape v{__version__} initialized successfully")
            self.logger.info(f"📊 Configuration: {config_manager._config_file_path}")
            self.logger.info(f"📁 Output directory: {config_manager.export.output_directory}")
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            if self.logger:
                self.logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def _apply_cli_overrides(self, args: argparse.Namespace):
        """Apply command line argument overrides to configuration"""
        if hasattr(args, 'verbose') and args.verbose:
            config_manager.set('logging.log_level', 'DEBUG')
        
        if hasattr(args, 'quiet') and args.quiet:
            config_manager.set('logging.log_level', 'WARNING')
            config_manager.set('logging.enable_console_logging', False)
        
        if hasattr(args, 'output_dir') and args.output_dir:
            config_manager.set('export.output_directory', args.output_dir)
        
        if hasattr(args, 'max_pages') and args.max_pages:
            config_manager.set('search.max_pages_per_query', args.max_pages)
        
        if hasattr(args, 'rate_limit') and args.rate_limit:
            config_manager.set('search.rate_limit_rpm', args.rate_limit)
        
        if hasattr(args, 'debug') and args.debug:
            config_manager.set('debug_mode', True)
            config_manager.set('logging.log_level', 'DEBUG')
        
        if hasattr(args, 'dry_run') and args.dry_run:
            config_manager.set('dry_run', True)
    
    async def run_scrape_command(self, args: argparse.Namespace) -> int:
        """
        Execute scraping campaign.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"🎯 Starting scraping campaign: {args.campaign}")
            
            # Load campaign configuration
            campaign_config = self._load_campaign_config(args.campaign)
            if not campaign_config:
                return 1
            
            # Create campaign runner
            runner = CampaignRunner(
                config=config_manager.config,
                agency_factory=self.agency_factory,
                error_handler=self.error_handler,
                resume_manager=self.resume_manager,
                logger=self.logger
            )
            
            # Check for resume
            session_id = args.resume or f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if args.resume and self.resume_manager.can_resume(session_id):
                self.logger.info(f"📄 Resuming campaign from session: {session_id}")
                results = await runner.resume(session_id)
            else:
                self.logger.info(f"🆕 Starting new campaign session: {session_id}")
                results = await runner.run(
                    campaign_config=campaign_config,
                    session_id=session_id,
                    max_leads=args.max_leads
                )
            
            # Generate summary report
            self._generate_campaign_report(results, session_id)
            
            self.logger.info(f"✅ Campaign completed successfully")
            self.logger.info(f"📊 Total leads generated: {len(results.get('leads', []))}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Campaign execution failed: {e}", exc_info=True)
            return 1
    
    async def run_validate_command(self, args: argparse.Namespace) -> int:
        """
        Execute validation pipeline.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"🔍 Starting validation: {args.input}")
            
            # Create validation pipeline
            validator = ValidationPipeline(
                config=config_manager.config,
                error_handler=self.error_handler,
                logger=self.logger
            )
            
            # Run validation
            results = await validator.validate_file(
                input_file=args.input,
                validation_level=args.level or 'strict',
                output_dir=args.output_dir or config_manager.export.output_directory
            )
            
            # Generate validation report
            self._generate_validation_report(results, args.input)
            
            self.logger.info(f"✅ Validation completed successfully")
            self.logger.info(f"📊 Valid leads: {results.get('valid_count', 0)}")
            self.logger.info(f"❌ Invalid leads: {results.get('invalid_count', 0)}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}", exc_info=True)
            return 1
    
    async def run_export_command(self, args: argparse.Namespace) -> int:
        """
        Execute export pipeline.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"📤 Starting export: {args.input}")
            
            # Create export pipeline
            exporter = ExportPipeline(
                config=config_manager.config,
                logger=self.logger
            )
            
            # Run export
            output_files = await exporter.export(
                input_file=args.input,
                format=args.format or 'csv',
                output_dir=args.output_dir or config_manager.export.output_directory,
                include_metadata=not args.no_metadata
            )
            
            self.logger.info(f"✅ Export completed successfully")
            for file_path in output_files:
                self.logger.info(f"📁 Generated: {file_path}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}", exc_info=True)
            return 1
    
    async def run_quick_command(self, args: argparse.Namespace) -> int:
        """
        Execute a quick, small scrape using the new scrapers and export CSV.
        """
        try:
            self.logger.info(f"⚡ Quick scrape starting. query={getattr(args, 'query', None)} max={getattr(args, 'max', None)}")

            # Ensure output dir exists
            try:
                output_base = getattr(getattr(config_manager, 'export', None), 'output_directory', 'output')
            except Exception:
                output_base = 'output'
            output_dir = Path(output_base or 'output')
            output_dir.mkdir(parents=True, exist_ok=True)

            leads = []

            import time as _t
            start_time = _t.monotonic()
            query = getattr(args, 'query', None) or 'coffee shops in Seattle'
            max_leads = getattr(args, 'max', None) or 10
            fallback_only = getattr(args, 'fallback_only', False)

            if not fallback_only:
                try:
                    from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
                    from src.scrapers.email_extractor import extract_emails_from_website

                    self.logger.info("🌐 Using Google Maps browser scraper")
                    businesses = scrape_google_maps_businesses(query, max_results=max(5, min(10, max_leads)))
                    for b in businesses:
                        if len(leads) >= max_leads:
                            break
                        if b.get('website'):
                            email = extract_emails_from_website(b['website']) or ''
                            b['email'] = email
                        b['source'] = 'google_maps'
                        leads.append(b)
                except Exception as e:
                    self.logger.warning(f"Browser scrape failed or produced no results: {e}")

            if not leads and (_t.monotonic() - start_time) < 20:
                try:
                    self.logger.info("🔎 Fallback to HTTP search path (Bing/Yellow Pages)")
                    from simple_business_scraper import SimpleBusinessScraper
                    s = SimpleBusinessScraper()
                    businesses = s.search_bing(query, max_results=max(5, min(10, max_leads)))
                    for b in businesses:
                        if len(leads) >= max_leads:
                            break
                        if b.get('website'):
                            email = s.extract_email_from_website(b['website']) or ''
                            b['email'] = email
                        b['source'] = 'web_search'
                        leads.append(b)
                        if (_t.monotonic() - start_time) > 30:
                            break
                except Exception as e:
                    self.logger.error(f"Fallback path failed: {e}")

            # Export
            csv_path = output_dir / 'quick_leads.csv'
            try:
                import csv
                fieldnames = ['name', 'email', 'phone', 'address', 'website', 'source']
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    for row in leads:
                        writer.writerow(row)
                self.logger.info(f"✅ Quick scrape completed: {len(leads)} leads -> {csv_path}")
            except Exception as e:
                self.logger.error(f"Failed to export quick leads: {e}")

            # Also print a brief summary
            print(f"Quick leads generated: {len(leads)}")
            for i, l in enumerate(leads[:5], 1):
                print(f"{i}. {l.get('name')} | {l.get('email','')} | {l.get('phone','')} | {l.get('website','')}")

            return 0
        except Exception as e:
            self.logger.error(f"Quick command failed: {e}", exc_info=True)
            return 1
    
    def _load_campaign_config(self, campaign_path: str) -> Optional[Dict[str, Any]]:
        """Load campaign configuration from file"""
        try:
            path = Path(campaign_path)
            if not path.exists():
                self.logger.error(f"Campaign file not found: {campaign_path}")
                return None
            
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    self.logger.error(f"Unsupported campaign file format: {path.suffix}")
                    return None
            
        except Exception as e:
            self.logger.error(f"Failed to load campaign config: {e}")
            return None
    
    def _generate_campaign_report(self, results: Dict[str, Any], session_id: str):
        """Generate campaign execution report"""
        try:
            report_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'version': __version__,
                'results': results,
                'performance': self.performance_monitor.get_metrics() if self.performance_monitor else None
            }
            
            report_path = Path(config_manager.export.output_directory) / f"{session_id}_report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.logger.info(f"📊 Campaign report saved: {report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate campaign report: {e}")
    
    def _generate_validation_report(self, results: Dict[str, Any], input_file: str):
        """Generate validation report"""
        try:
            report_data = {
                'input_file': input_file,
                'timestamp': datetime.now().isoformat(),
                'version': __version__,
                'results': results
            }
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = Path(config_manager.export.output_directory) / f"validation_report_{timestamp}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.logger.info(f"📊 Validation report saved: {report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate validation report: {e}")


def create_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='vrsen-pubscrape',
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Run a scraping campaign
  python main.py scrape --campaign campaigns/doctor_leads.yaml --max-leads 100
  
  # Validate existing leads
  python main.py validate --input output/leads.csv --level strict
  
  # Export leads to different format
  python main.py export --input output/leads.csv --format xlsx
  
  # Resume interrupted campaign
  python main.py scrape --campaign campaigns/doctors.yaml --resume campaign_20240101_120000
  
  # Debug mode with verbose logging
  python main.py scrape --campaign campaigns/test.yaml --debug --verbose

Version: {__version__}
Author: {__author__}
        """
    )
    
    # Global options
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode (warnings only)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--output-dir', '-o', help='Output directory for results')
    parser.add_argument('--dry-run', action='store_true', help='Simulate operations without execution')
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser(
        'scrape',
        help='Run web scraping campaign',
        description='Execute a web scraping campaign using configured agents'
    )
    scrape_parser.add_argument(
        '--campaign', '-c', required=True,
        help='Campaign configuration file (YAML or JSON)'
    )
    scrape_parser.add_argument(
        '--max-leads', type=int,
        help='Maximum number of leads to generate'
    )
    scrape_parser.add_argument(
        '--max-pages', type=int,
        help='Maximum pages per search query'
    )
    scrape_parser.add_argument(
        '--rate-limit', type=int,
        help='Rate limit (requests per minute)'
    )
    scrape_parser.add_argument(
        '--resume', 
        help='Resume from previous session ID'
    )
    scrape_parser.add_argument(
        '--no-validation', action='store_true',
        help='Skip lead validation'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate existing leads',
        description='Validate email addresses and lead quality'
    )
    validate_parser.add_argument(
        '--input', '-i', required=True,
        help='Input CSV file to validate'
    )
    validate_parser.add_argument(
        '--level', choices=['strict', 'moderate', 'lenient'],
        default='strict', help='Validation strictness level'
    )
    validate_parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for validation results'
    )
    
    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export leads to different formats',
        description='Convert and export lead data'
    )
    export_parser.add_argument(
        '--input', '-i', required=True,
        help='Input CSV file to export'
    )
    export_parser.add_argument(
        '--format', '-f', choices=['csv', 'xlsx', 'json', 'xml'],
        default='csv', help='Output format'
    )
    export_parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for exported files'
    )
    export_parser.add_argument(
        '--no-metadata', action='store_true',
        help='Exclude metadata from export'
    )
    
    # Status command
    status_parser = subparsers.add_parser(
        'status',
        help='Show system and session status',
        description='Display current system status and running sessions'
    )
    status_parser.add_argument(
        '--sessions', action='store_true',
        help='Show all session information'
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        'config',
        help='Configuration management',
        description='View and modify configuration settings'
    )
    config_parser.add_argument(
        '--show', action='store_true',
        help='Show current configuration'
    )
    config_parser.add_argument(
        '--validate', action='store_true',
        help='Validate configuration'
    )
    config_parser.add_argument(
        '--set', nargs=2, metavar=('KEY', 'VALUE'),
        help='Set configuration value (key.path value)'
    )
    
    # Quick command
    quick_parser = subparsers.add_parser(
        'quick',
        help='Quick small scrape with new scrapers',
        description='Run a small quick scrape using Google Maps and website email extraction'
    )
    quick_parser.add_argument('--query', '-q', help='Search query', default='coffee shops in Seattle')
    quick_parser.add_argument('--max', type=int, default=10, help='Max leads to generate')
    quick_parser.add_argument('--fallback-only', action='store_true', help='Use HTTP fallback only (no browser)')
    
    return parser


async def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 1
    
    # Create and initialize application
    app = CLIApplication()
    if not app.initialize(args):
        return 1
    
    try:
        # Execute command
        if args.command == 'scrape':
            return await app.run_scrape_command(args)
        elif args.command == 'validate':
            return await app.run_validate_command(args)
        elif args.command == 'export':
            return await app.run_export_command(args)
        elif args.command == 'quick':
            return await app.run_quick_command(args)
        elif args.command == 'status':
            return await app.run_status_command(args)
        elif args.command == 'config':
            return await app.run_config_command(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if app.logger:
            app.logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup
        if app.performance_monitor:
            app.performance_monitor.stop()
        if app.resume_manager:
            app.resume_manager.save_state()


if __name__ == "__main__":
    # Run the application
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Application interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)