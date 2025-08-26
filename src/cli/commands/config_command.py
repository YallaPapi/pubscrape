"""
Config Command Implementation

Handles configuration management including display, validation, and modification.
"""

import json
from argparse import Namespace

from .base import BaseCommand


class ConfigCommand(BaseCommand):
    """Command for configuration management"""
    
    def add_arguments(self, parser):
        """Add config command arguments"""
        parser.add_argument(
            '--show', action='store_true',
            help='Show current configuration'
        )
        parser.add_argument(
            '--validate', action='store_true',
            help='Validate configuration'
        )
        parser.add_argument(
            '--set', nargs=2, metavar=('KEY', 'VALUE'),
            help='Set configuration value (key.path value)'
        )
    
    async def execute(self, args: Namespace) -> int:
        """
        Execute configuration command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Handle show configuration
            if args.show:
                return self._show_configuration()
            
            # Handle validate configuration
            elif args.validate:
                return self._validate_configuration()
            
            # Handle set configuration value
            elif args.set:
                return self._set_configuration_value(args.set[0], args.set[1])
            
            # No action specified, show help
            else:
                self.logger.info("No action specified. Use --show, --validate, or --set")
                return 1
                
        except Exception as e:
            return self._handle_command_error(e, "Configuration command failed")
    
    def _show_configuration(self) -> int:
        """Show current configuration"""
        try:
            self.logger.info("📋 Current Configuration:")
            self.logger.info(f"   Config file: {self.config_manager._config_file_path}")
            
            # Get configuration as dict for display
            config_dict = {
                'logging': {
                    'log_level': self.config_manager.logging.log_level,
                    'log_directory': self.config_manager.logging.log_directory,
                    'enable_console_logging': self.config_manager.logging.enable_console_logging,
                    'enable_file_logging': self.config_manager.logging.enable_file_logging
                },
                'export': {
                    'output_directory': self.config_manager.export.output_directory
                },
                'config': {
                    'enable_metrics': self.config_manager.config.enable_metrics,
                    'data_directory': self.config_manager.config.data_directory
                }
            }
            
            # Display configuration in readable format
            config_json = json.dumps(config_dict, indent=2, default=str)
            for line in config_json.split('\n'):
                self.logger.info(f"   {line}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to show configuration: {e}")
            return 1
    
    def _validate_configuration(self) -> int:
        """Validate current configuration"""
        try:
            self.logger.info("🔍 Validating configuration...")
            
            is_valid, errors = self.config_manager.validate()
            
            if is_valid:
                self.logger.info("✅ Configuration is valid")
                return 0
            else:
                self.logger.error("❌ Configuration validation failed:")
                for error in errors:
                    self.logger.error(f"   • {error}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return 1
    
    def _set_configuration_value(self, key: str, value: str) -> int:
        """Set configuration value"""
        try:
            self.logger.info(f"🔧 Setting configuration: {key} = {value}")
            
            # Try to parse value as appropriate type
            parsed_value = self._parse_config_value(value)
            
            # Set the configuration value
            self.config_manager.set(key, parsed_value)
            
            self.logger.info("✅ Configuration updated successfully")
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration value: {e}")
            return 1
    
    def _parse_config_value(self, value: str):
        """Parse configuration value to appropriate type"""
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value