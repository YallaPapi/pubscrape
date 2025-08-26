"""
Base Command Class

Provides common functionality for all CLI commands including error handling,
logging integration, and standardized return codes.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from argparse import Namespace
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.error_handler import ErrorHandler


class BaseCommand(ABC):
    """
    Abstract base class for all CLI commands.
    
    Provides common functionality including:
    - Error handling and logging integration
    - Configuration access
    - Standardized return codes
    - Signal handling support
    """
    
    def __init__(self, config_manager, logger=None, error_handler=None):
        """
        Initialize base command.
        
        Args:
            config_manager: Application configuration manager
            logger: Optional logger instance
            error_handler: Optional error handler instance
        """
        self.config_manager = config_manager
        self.logger = logger or get_logger(self.__class__.__name__)
        self.error_handler = error_handler
        self._shutdown_requested = False
    
    @abstractmethod
    async def execute(self, args: Namespace) -> int:
        """
        Execute the command with given arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass
    
    @abstractmethod  
    def add_arguments(self, parser):
        """
        Add command-specific arguments to the parser.
        
        Args:
            parser: ArgumentParser subparser for this command
        """
        pass
    
    def request_shutdown(self):
        """Request graceful shutdown of the command"""
        self._shutdown_requested = True
        self.logger.info("Shutdown requested for command")
    
    def _validate_file_path(self, file_path: str, must_exist: bool = True) -> Optional[Path]:
        """
        Validate and return Path object for file path.
        
        Args:
            file_path: File path to validate
            must_exist: Whether file must already exist
            
        Returns:
            Path object if valid, None if invalid
        """
        try:
            path = Path(file_path)
            
            if must_exist and not path.exists():
                self.logger.error(f"File not found: {file_path}")
                return None
                
            if must_exist and not path.is_file():
                self.logger.error(f"Path is not a file: {file_path}")
                return None
                
            return path
            
        except Exception as e:
            self.logger.error(f"Invalid file path '{file_path}': {e}")
            return None
    
    def _ensure_output_directory(self, output_dir: str) -> Optional[Path]:
        """
        Ensure output directory exists and is writable.
        
        Args:
            output_dir: Output directory path
            
        Returns:
            Path object if valid, None if invalid
        """
        try:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            
            if not path.is_dir():
                self.logger.error(f"Cannot create output directory: {output_dir}")
                return None
                
            return path
            
        except Exception as e:
            self.logger.error(f"Failed to create output directory '{output_dir}': {e}")
            return None
    
    def _handle_command_error(self, error: Exception, context: str = "") -> int:
        """
        Handle command execution errors with consistent logging and return codes.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
            
        Returns:
            Appropriate exit code
        """
        error_msg = f"{context}: {error}" if context else str(error)
        
        if self.error_handler:
            return self.error_handler.handle_error(error, context)
        else:
            self.logger.error(error_msg, exc_info=True)
            return 1