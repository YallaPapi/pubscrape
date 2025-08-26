"""
Argument Parser Factory

Creates the main ArgumentParser with all command subparsers.
Delegates command-specific argument parsing to individual command classes.
"""

import argparse
from typing import Dict, Type

from ..commands import (
    ScrapeCommand, ValidateCommand, ExportCommand, 
    ConfigCommand, QuickCommand, BaseCommand
)


# Version info
__version__ = "1.0.0"
__author__ = "VRSEN Agency"
__description__ = "Advanced Multi-Agent Web Scraping Platform"


def create_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser with all command subparsers.
    
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
    
    # Command definitions with their corresponding classes
    command_definitions = {
        'scrape': {
            'class': ScrapeCommand,
            'help': 'Run web scraping campaign',
            'description': 'Execute a web scraping campaign using configured agents'
        },
        'validate': {
            'class': ValidateCommand,
            'help': 'Validate existing leads',
            'description': 'Validate email addresses and lead quality'
        },
        'export': {
            'class': ExportCommand,
            'help': 'Export leads to different formats',
            'description': 'Convert and export lead data'
        },
        'config': {
            'class': ConfigCommand,
            'help': 'Configuration management',
            'description': 'View and modify configuration settings'
        },
        'quick': {
            'class': QuickCommand,
            'help': 'Quick small scrape with new scrapers',
            'description': 'Run a small quick scrape using Google Maps and website email extraction'
        }
    }
    
    # Create subparsers for each command
    for command_name, command_info in command_definitions.items():
        command_parser = subparsers.add_parser(
            command_name,
            help=command_info['help'],
            description=command_info['description']
        )
        
        # Create a temporary instance to get argument definitions
        # Note: We don't need actual dependencies for argument parsing
        temp_command = command_info['class'](None)  # Pass None for config_manager
        temp_command.add_arguments(command_parser)
    
    # Add status command separately (not implemented as a command class yet)
    status_parser = subparsers.add_parser(
        'status',
        help='Show system and session status',
        description='Display current system status and running sessions'
    )
    status_parser.add_argument(
        '--sessions', action='store_true',
        help='Show all session information'
    )
    
    return parser


def get_command_classes() -> Dict[str, Type[BaseCommand]]:
    """
    Get mapping of command names to their implementation classes.
    
    Returns:
        Dictionary mapping command names to command classes
    """
    return {
        'scrape': ScrapeCommand,
        'validate': ValidateCommand,
        'export': ExportCommand,
        'config': ConfigCommand,
        'quick': QuickCommand
    }