"""
Error Handler Module
Implements 20-cycle error recovery protocol as per mandate.
"""

import logging
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

from .config import config

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handles errors with 20-cycle recovery protocol."""
    
    def __init__(self):
        """Initialize error handler with cycle tracking."""
        self.error_cycles = {}
        self.blocked_errors = []
        self.error_log_file = os.path.join(config.OUTPUT_DIR, "error_log.json")
        self.load_error_history()
    
    def load_error_history(self):
        """Load previous error history if exists."""
        if os.path.exists(self.error_log_file):
            try:
                with open(self.error_log_file, 'r') as f:
                    data = json.load(f)
                    self.error_cycles = data.get("error_cycles", {})
                    self.blocked_errors = data.get("blocked_errors", [])
            except Exception as e:
                logger.warning(f"Could not load error history: {e}")
    
    def save_error_history(self):
        """Save error history to file."""
        try:
            with open(self.error_log_file, 'w') as f:
                json.dump({
                    "error_cycles": self.error_cycles,
                    "blocked_errors": self.blocked_errors,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save error history: {e}")
    
    def handle_api_error(self, error: Exception, operation: str) -> bool:
        """
        Handle API errors with 20-cycle protocol.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            
        Returns:
            True if error can be retried, False if blocked
        """
        error_key = f"{operation}:{type(error).__name__}"
        
        # Check if already blocked
        if error_key in self.blocked_errors:
            logger.error(f"Error {error_key} is blocked after 20 cycles")
            print(f"❌ BLOCKED: {operation} failed after 20 attempts")
            return False
        
        # Initialize or increment cycle count
        if error_key not in self.error_cycles:
            self.error_cycles[error_key] = {
                "count": 0,
                "first_seen": datetime.now().isoformat(),
                "last_seen": None,
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        
        self.error_cycles[error_key]["count"] += 1
        self.error_cycles[error_key]["last_seen"] = datetime.now().isoformat()
        
        cycle_count = self.error_cycles[error_key]["count"]
        
        logger.info(f"Error cycle {cycle_count}/20 for {error_key}")
        print(f"⚠️  Error cycle {cycle_count}/20 for {operation}")
        
        # Check if we've hit the 20-cycle limit
        if cycle_count >= config.MAX_ERROR_CYCLES:
            self.blocked_errors.append(error_key)
            self.save_error_history()
            logger.error(f"Error {error_key} blocked after {cycle_count} cycles")
            print(f"❌ ESCALATION: {operation} blocked after {cycle_count} failed attempts")
            return False
        
        # Apply retry delay with exponential backoff
        delay = min(config.RETRY_DELAY * (2 ** (cycle_count - 1)), 300)  # Max 5 minutes
        logger.info(f"Waiting {delay} seconds before retry...")
        time.sleep(delay)
        
        self.save_error_history()
        return True
    
    def reset_error_cycles(self, operation: Optional[str] = None):
        """
        Reset error cycles for a specific operation or all.
        
        Args:
            operation: Operation to reset, or None for all
        """
        if operation:
            keys_to_reset = [k for k in self.error_cycles.keys() if k.startswith(f"{operation}:")]
            for key in keys_to_reset:
                del self.error_cycles[key]
                if key in self.blocked_errors:
                    self.blocked_errors.remove(key)
            logger.info(f"Reset error cycles for operation: {operation}")
        else:
            self.error_cycles = {}
            self.blocked_errors = []
            logger.info("Reset all error cycles")
        
        self.save_error_history()
    
    def get_error_status(self) -> Dict[str, Any]:
        """Get current error handling status."""
        return {
            "active_errors": len(self.error_cycles),
            "blocked_errors": len(self.blocked_errors),
            "error_cycles": self.error_cycles,
            "blocked_list": self.blocked_errors
        }
    
    def handle_recoverable_error(self, error: Exception, context: str) -> bool:
        """
        Handle errors that can be recovered from.
        
        Args:
            error: The exception
            context: Context where error occurred
            
        Returns:
            True if recovery successful, False otherwise
        """
        error_msg = str(error)
        
        # Check for specific recoverable errors
        if "quota" in error_msg.lower():
            logger.warning(f"Quota error in {context}: {error_msg}")
            print(f"⚠️  Quota limit reached. Waiting for reset...")
            return False
        
        if "rate limit" in error_msg.lower():
            logger.warning(f"Rate limit in {context}: {error_msg}")
            print(f"⚠️  Rate limited. Waiting before retry...")
            time.sleep(60)  # Wait 1 minute for rate limits
            return True
        
        if "timeout" in error_msg.lower():
            logger.warning(f"Timeout in {context}: {error_msg}")
            print(f"⚠️  Request timeout. Retrying...")
            return True
        
        # For other errors, use the 20-cycle protocol
        return self.handle_api_error(error, context)