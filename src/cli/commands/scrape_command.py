"""
Scrape Command Implementation

Handles web scraping campaign execution with support for resume, validation,
and comprehensive reporting.
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from argparse import Namespace

from .base import BaseCommand
from src.pipeline.campaign_runner import CampaignRunner
from src.utils.resume_manager import ResumeManager


class ScrapeCommand(BaseCommand):
    """Command for executing web scraping campaigns"""
    
    def __init__(self, config_manager, logger=None, error_handler=None):
        super().__init__(config_manager, logger, error_handler)
        self.resume_manager = None
        self.agency_factory = None
    
    def add_arguments(self, parser):
        """Add scrape command arguments"""
        parser.add_argument(
            '--campaign', '-c', required=True,
            help='Campaign configuration file (YAML or JSON)'
        )
        parser.add_argument(
            '--max-leads', type=int,
            help='Maximum number of leads to generate'
        )
        parser.add_argument(
            '--max-pages', type=int,
            help='Maximum pages per search query'
        )
        parser.add_argument(
            '--rate-limit', type=int,
            help='Rate limit (requests per minute)'
        )
        parser.add_argument(
            '--resume', 
            help='Resume from previous session ID'
        )
        parser.add_argument(
            '--no-validation', action='store_true',
            help='Skip lead validation'
        )
    
    async def execute(self, args: Namespace) -> int:
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
            
            # Initialize dependencies if not already done
            if not self._initialize_dependencies():
                return 1
            
            # Create campaign runner
            runner = CampaignRunner(
                config=self.config_manager.config,
                agency_factory=self.agency_factory,
                error_handler=self.error_handler,
                resume_manager=self.resume_manager,
                logger=self.logger
            )
            
            # Handle session management
            session_id = args.resume or f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Execute campaign
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
            return self._handle_command_error(e, "Campaign execution failed")
    
    def _initialize_dependencies(self) -> bool:
        """Initialize dependencies for scrape command"""
        try:
            # Import here to avoid circular dependencies
            from src.core.agency_factory import AgencyFactory
            
            # Initialize resume manager
            self.resume_manager = ResumeManager(
                state_dir=Path(self.config_manager.config.data_directory) / "state"
            )
            
            # Initialize agency factory
            self.agency_factory = AgencyFactory(self.config_manager.config)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize dependencies: {e}")
            return False
    
    def _load_campaign_config(self, campaign_path: str) -> Optional[Dict[str, Any]]:
        """Load campaign configuration from file"""
        try:
            path = self._validate_file_path(campaign_path, must_exist=True)
            if not path:
                return None
            
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    self.logger.error(f"Unsupported campaign file format: {path.suffix}")
                    return None
            
            self.logger.info(f"📋 Loaded campaign configuration: {campaign_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load campaign config: {e}")
            return None
    
    def _generate_campaign_report(self, results: Dict[str, Any], session_id: str):
        """Generate campaign execution report"""
        try:
            report_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'version': "1.0.0",  # TODO: Get from central version location
                'results': results
            }
            
            output_dir = self._ensure_output_directory(self.config_manager.export.output_directory)
            if not output_dir:
                return
            
            report_path = output_dir / f"{session_id}_report.json"
            
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.logger.info(f"📊 Campaign report saved: {report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate campaign report: {e}")