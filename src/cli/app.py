"""
CLI Application

Main CLI application orchestrator that handles initialization, command routing,
and graceful shutdown. Provides centralized error handling and logging.
"""

import sys
import signal
import asyncio
from argparse import Namespace
from typing import Optional

from .parsers.argument_parser import create_parser, get_command_classes
from .commands.base import BaseCommand

# Core imports with fallback handling
try:
    from src.core.config_manager import config_manager
except Exception:
    # Fallback dummy config manager for lightweight runs
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
from src.utils.error_handler import ErrorHandler
from src.utils.performance_monitor import PerformanceMonitor
from src.utils.resume_manager import ResumeManager


class CLIApplication:
    """
    Main CLI application class that orchestrates all operations.
    
    Handles:
    - Application initialization and configuration
    - Command routing and execution
    - Error handling and logging
    - Graceful shutdown
    """
    
    def __init__(self):
        self.logger = None
        self.error_handler = None
        self.performance_monitor = None
        self.resume_manager = None
        self.shutdown_requested = False
        self.current_command = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\\n⚠️  Shutdown signal received. Cleaning up...")
        self.shutdown_requested = True
        
        # Request shutdown of current command
        if self.current_command:
            self.current_command.request_shutdown()
        
        # Stop monitoring services
        if self.performance_monitor:
            self.performance_monitor.stop()
        
        if self.resume_manager:
            self.resume_manager.save_state()
        
        print("✅ Cleanup completed. Exiting.")
        sys.exit(0)
    
    def initialize(self, args: Namespace) -> bool:
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
                return True
            
            # Load configuration
            if args.config:
                if not config_manager.load_from_file(args.config):
                    print(f"❌ Failed to load configuration from {args.config}")
                    return False
            
            # Apply CLI overrides
            self._apply_cli_overrides(args)
            
            # Validate configuration (non-fatal warnings)
            try:
                is_valid, errors = config_manager.validate()
                if not is_valid:
                    print(f"⚠️  Configuration issues detected:")
                    for error in errors:
                        print(f"   • {error}")
            except Exception as e:
                print(f"⚠️  Configuration validation failed: {e}")
            
            # Setup logging
            self.logger = setup_logging(
                level=config_manager.logging.log_level,
                log_dir=config_manager.logging.log_directory,
                enable_console=config_manager.logging.enable_console_logging,
                enable_file=config_manager.logging.enable_file_logging
            )
            
            # Initialize error handler
            try:
                self.error_handler = ErrorHandler(
                    max_retries=getattr(config_manager.search, 'retry_attempts', 3),
                    retry_delay=getattr(config_manager.search, 'retry_delay', 1.0),
                    logger=self.logger
                )
            except AttributeError:
                # Fallback if search config is not available
                self.error_handler = ErrorHandler(
                    max_retries=3,
                    retry_delay=1.0,
                    logger=self.logger
                )
            
            # Initialize performance monitor (optional)
            if getattr(config_manager.config, 'enable_metrics', False):
                try:
                    self.performance_monitor = PerformanceMonitor(
                        output_dir=config_manager.export.output_directory
                    )
                    self.performance_monitor.start()
                except Exception as e:
                    self.logger.warning(f"Failed to start performance monitor: {e}")
            
            # Initialize resume manager
            try:
                from pathlib import Path
                self.resume_manager = ResumeManager(
                    state_dir=Path(config_manager.config.data_directory) / "state"
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize resume manager: {e}")
            
            self.logger.info(f"🚀 VRSEN PubScrape initialized successfully")
            self.logger.info(f"📊 Configuration: {config_manager._config_file_path}")
            self.logger.info(f"📁 Output directory: {config_manager.export.output_directory}")
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            if self.logger:
                self.logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def _apply_cli_overrides(self, args: Namespace):
        """Apply command line argument overrides to configuration"""
        if hasattr(args, 'verbose') and args.verbose:
            config_manager.set('logging.log_level', 'DEBUG')
        
        if hasattr(args, 'quiet') and args.quiet:
            config_manager.set('logging.log_level', 'WARNING')
            config_manager.set('logging.enable_console_logging', False)
        
        if hasattr(args, 'output_dir') and args.output_dir:
            config_manager.set('export.output_directory', args.output_dir)
        
        if hasattr(args, 'debug') and args.debug:
            config_manager.set('debug_mode', True)
            config_manager.set('logging.log_level', 'DEBUG')
        
        if hasattr(args, 'dry_run') and args.dry_run:
            config_manager.set('dry_run', True)
    
    async def execute_command(self, args: Namespace) -> int:
        """
        Execute the requested command.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        command_name = args.command
        
        # Handle special status command (not yet implemented as class)
        if command_name == 'status':
            return await self._run_status_command(args)
        
        # Get command class
        command_classes = get_command_classes()
        command_class = command_classes.get(command_name)
        
        if not command_class:
            print(f"❌ Unknown command: {command_name}")
            return 1
        
        try:
            # Create and execute command
            self.current_command = command_class(
                config_manager=config_manager,
                logger=self.logger,
                error_handler=self.error_handler
            )
            
            return await self.current_command.execute(args)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Command execution failed: {e}", exc_info=True)
            print(f"❌ Command failed: {e}")
            return 1
        finally:
            self.current_command = None
    
    async def _run_status_command(self, args: Namespace) -> int:
        """Handle status command (placeholder implementation)"""
        try:
            print("📊 System Status:")
            print(f"   Version: 1.0.0")
            print(f"   Config: {config_manager._config_file_path}")
            print(f"   Output: {config_manager.export.output_directory}")
            
            if args.sessions and self.resume_manager:
                print("📄 Active Sessions:")
                # TODO: Implement session listing
                print("   No active sessions found")
            
            return 0
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Status command failed: {e}")
            print(f"❌ Status command failed: {e}")
            return 1
    
    def cleanup(self):
        """Perform application cleanup"""
        try:
            if self.performance_monitor:
                self.performance_monitor.stop()
            
            if self.resume_manager:
                self.resume_manager.save_state()
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Cleanup failed: {e}")


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
        return await app.execute_command(args)
        
    except KeyboardInterrupt:
        print("\\n⚠️  Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if app.logger:
            app.logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup
        app.cleanup()