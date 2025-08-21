"""
Base Tool Class for VRSEN Agency Swarm

Provides common functionality, error handling, and standardized interfaces
for all tools used by agents in the lead generation pipeline.
"""

import logging
import time
from typing import Any, Dict, Optional, Type, Union, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from contextlib import contextmanager
import traceback

from agency_swarm.tools import BaseTool as AgencySwarmBaseTool
from pydantic import Field, validator

from ..infra.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from ..core.config_manager import config_manager


@dataclass
class ToolMetrics:
    """Tracks tool execution metrics"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_execution_time: Optional[float] = None
    last_error: Optional[str] = None
    error_counts: Dict[str, int] = field(default_factory=dict)


class BaseVRSENTool(AgencySwarmBaseTool):
    """
    Enhanced base tool with common functionality for all VRSEN tools.
    
    Features:
    - Standardized error handling with recovery
    - Execution metrics tracking
    - Input validation and sanitization
    - Result validation and formatting
    - Retry logic with exponential backoff
    - Structured logging
    - Performance monitoring
    """
    
    # Tool metadata (to be overridden by subclasses)
    tool_name: str = "BaseVRSENTool"
    tool_category: str = "general"
    tool_version: str = "1.0.0"
    
    # Execution settings
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    retry_delay: float = Field(2.0, description="Initial retry delay in seconds")
    timeout: int = Field(30, description="Execution timeout in seconds")
    
    def __init__(self, **data):
        """Initialize base tool with enhanced features"""
        super().__init__(**data)
        
        # Initialize components
        self.metrics = ToolMetrics()
        self.error_handler = ErrorHandler(agent_name=f"tool_{self.tool_name}")
        self.logger = self._setup_logging()
        
        # Load configuration
        self.config = config_manager.config
        
        self.logger.debug(f"{self.tool_name} initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging for the tool"""
        logger = logging.getLogger(f"vrsen.tools.{self.tool_name}")
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.tool_name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the tool with comprehensive error handling and metrics.
        
        Returns:
            Standardized result dictionary
        """
        start_time = time.time()
        self.metrics.total_executions += 1
        
        try:
            # Log execution start
            self.logger.info(f"Executing {self.tool_name}")
            
            # Validate inputs
            validation_result = self._validate_inputs()
            if not validation_result["valid"]:
                return self._create_error_response(
                    "validation_error",
                    validation_result["message"]
                )
            
            # Execute with retry logic
            result = self._execute_with_retry()
            
            # Validate output
            validated_result = self._validate_output(result)
            
            # Update success metrics
            execution_time = time.time() - start_time
            self._update_success_metrics(execution_time)
            
            # Return standardized response
            return self._create_success_response(validated_result, execution_time)
            
        except Exception as e:
            # Update failure metrics
            execution_time = time.time() - start_time
            self._update_failure_metrics(e, execution_time)
            
            # Log error
            self.error_handler.log_error(
                error=e,
                category=self._categorize_error(e),
                severity=self._assess_severity(e),
                operation=self.tool_name,
                context=self._get_execution_context()
            )
            
            # Return error response
            return self._create_error_response(
                error_type=type(e).__name__,
                error_message=str(e),
                execution_time=execution_time
            )
    
    @abstractmethod
    def _execute(self) -> Any:
        """
        Actual tool execution logic.
        Must be implemented by subclasses.
        
        Returns:
            Tool-specific result
        """
        pass
    
    def _validate_inputs(self) -> Dict[str, Any]:
        """
        Validate tool inputs.
        Can be overridden by subclasses for custom validation.
        
        Returns:
            Validation result dictionary
        """
        try:
            # Pydantic automatically validates fields
            # Additional custom validation can be added here
            return {"valid": True, "message": "Inputs validated"}
        except Exception as e:
            return {"valid": False, "message": str(e)}
    
    def _validate_output(self, output: Any) -> Any:
        """
        Validate and format tool output.
        Can be overridden by subclasses.
        
        Args:
            output: Raw output from tool execution
            
        Returns:
            Validated and formatted output
        """
        return output
    
    def _execute_with_retry(self) -> Any:
        """
        Execute tool with retry logic and exponential backoff.
        
        Returns:
            Tool execution result
        """
        delay = self.retry_delay
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Execution attempt {attempt + 1}/{self.max_retries}")
                
                # Execute with timeout
                result = self._execute_with_timeout()
                
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed")
        
        # If all retries failed, raise the last error
        raise last_error
    
    def _execute_with_timeout(self) -> Any:
        """
        Execute tool with timeout.
        Note: Simplified timeout handling - in production would use threading/asyncio.
        
        Returns:
            Tool execution result
        """
        # For now, just execute directly
        # In production, would wrap in timeout handler
        return self._execute()
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize error for proper handling.
        Can be overridden by subclasses.
        
        Args:
            error: The exception to categorize
            
        Returns:
            Error category
        """
        error_msg = str(error).lower()
        
        if "timeout" in error_msg:
            return ErrorCategory.TIMEOUT
        elif "rate" in error_msg or "429" in error_msg:
            return ErrorCategory.RATE_LIMIT
        elif "network" in error_msg or "connection" in error_msg:
            return ErrorCategory.NETWORK
        elif "parse" in error_msg or "json" in error_msg:
            return ErrorCategory.PARSING
        elif "validation" in error_msg or "invalid" in error_msg:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """
        Assess error severity.
        Can be overridden by subclasses.
        
        Args:
            error: The exception to assess
            
        Returns:
            Error severity
        """
        error_msg = str(error).lower()
        
        if "critical" in error_msg or "fatal" in error_msg:
            return ErrorSeverity.CRITICAL
        elif "timeout" in error_msg or "rate" in error_msg:
            return ErrorSeverity.HIGH
        elif "network" in error_msg:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _get_execution_context(self) -> Dict[str, Any]:
        """
        Get current execution context for error logging.
        
        Returns:
            Context dictionary
        """
        return {
            "tool_name": self.tool_name,
            "tool_category": self.tool_category,
            "tool_version": self.tool_version,
            "execution_count": self.metrics.total_executions,
            "config": {
                "max_retries": self.max_retries,
                "timeout": self.timeout
            }
        }
    
    def _update_success_metrics(self, execution_time: float):
        """Update metrics for successful execution"""
        self.metrics.successful_executions += 1
        self.metrics.total_execution_time += execution_time
        self.metrics.last_execution_time = execution_time
        self.metrics.average_execution_time = (
            self.metrics.total_execution_time / self.metrics.successful_executions
        )
        
        self.logger.debug(f"Execution successful in {execution_time:.2f}s")
    
    def _update_failure_metrics(self, error: Exception, execution_time: float):
        """Update metrics for failed execution"""
        self.metrics.failed_executions += 1
        self.metrics.last_error = str(error)
        self.metrics.last_execution_time = execution_time
        
        # Track error types
        error_type = type(error).__name__
        self.metrics.error_counts[error_type] = (
            self.metrics.error_counts.get(error_type, 0) + 1
        )
        
        self.logger.debug(f"Execution failed after {execution_time:.2f}s: {error}")
    
    def _create_success_response(self, 
                                result: Any, 
                                execution_time: float) -> Dict[str, Any]:
        """
        Create standardized success response.
        
        Args:
            result: Tool execution result
            execution_time: Time taken to execute
            
        Returns:
            Standardized response dictionary
        """
        return {
            "status": "success",
            "tool": self.tool_name,
            "result": result,
            "metadata": {
                "execution_time": execution_time,
                "timestamp": time.time(),
                "version": self.tool_version
            }
        }
    
    def _create_error_response(self, 
                              error_type: str,
                              error_message: str,
                              execution_time: float = 0.0) -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            error_type: Type of error
            error_message: Error message
            execution_time: Time before failure
            
        Returns:
            Standardized error response dictionary
        """
        return {
            "status": "error",
            "tool": self.tool_name,
            "error": {
                "type": error_type,
                "message": error_message,
                "traceback": traceback.format_exc() if self.config.debug_mode else None
            },
            "metadata": {
                "execution_time": execution_time,
                "timestamp": time.time(),
                "version": self.tool_version,
                "retry_attempts": self.max_retries
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current tool metrics.
        
        Returns:
            Dictionary of metrics
        """
        success_rate = 0.0
        if self.metrics.total_executions > 0:
            success_rate = (
                self.metrics.successful_executions / self.metrics.total_executions
            )
        
        return {
            "tool_name": self.tool_name,
            "total_executions": self.metrics.total_executions,
            "successful_executions": self.metrics.successful_executions,
            "failed_executions": self.metrics.failed_executions,
            "success_rate": success_rate,
            "average_execution_time": self.metrics.average_execution_time,
            "last_execution_time": self.metrics.last_execution_time,
            "last_error": self.metrics.last_error,
            "error_counts": self.metrics.error_counts
        }
    
    def reset_metrics(self):
        """Reset tool metrics"""
        self.metrics = ToolMetrics()
        self.logger.info("Tool metrics reset")
    
    @contextmanager
    def performance_tracking(self):
        """Context manager for tracking tool performance"""
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.logger.debug(f"Operation completed in {duration:.2f}s")


class SearchTool(BaseVRSENTool):
    """
    Specialized base class for search-related tools.
    """
    
    tool_category: str = "search"
    
    # Search-specific fields
    query: str = Field(..., description="Search query")
    max_results: int = Field(10, description="Maximum results to return")
    
    def _validate_inputs(self) -> Dict[str, Any]:
        """Validate search-specific inputs"""
        result = super()._validate_inputs()
        
        if not result["valid"]:
            return result
        
        # Validate query
        if not self.query or len(self.query.strip()) == 0:
            return {"valid": False, "message": "Search query cannot be empty"}
        
        if len(self.query) > 500:
            return {"valid": False, "message": "Search query too long (max 500 chars)"}
        
        # Validate max_results
        if self.max_results < 1 or self.max_results > 100:
            return {"valid": False, "message": "max_results must be between 1 and 100"}
        
        return {"valid": True, "message": "Search inputs validated"}


class ProcessingTool(BaseVRSENTool):
    """
    Specialized base class for data processing tools.
    """
    
    tool_category: str = "processing"
    
    # Processing-specific fields
    input_data: Any = Field(..., description="Data to process")
    output_format: str = Field("json", description="Output format")
    
    def _validate_inputs(self) -> Dict[str, Any]:
        """Validate processing-specific inputs"""
        result = super()._validate_inputs()
        
        if not result["valid"]:
            return result
        
        # Validate input data
        if self.input_data is None:
            return {"valid": False, "message": "Input data cannot be None"}
        
        # Validate output format
        valid_formats = ["json", "csv", "text", "html"]
        if self.output_format not in valid_formats:
            return {
                "valid": False, 
                "message": f"Invalid output format. Must be one of: {valid_formats}"
            }
        
        return {"valid": True, "message": "Processing inputs validated"}


class ValidationTool(BaseVRSENTool):
    """
    Specialized base class for validation tools.
    """
    
    tool_category: str = "validation"
    
    # Validation-specific fields
    data_to_validate: Any = Field(..., description="Data to validate")
    validation_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validation rules to apply"
    )
    strict_mode: bool = Field(True, description="Use strict validation")
    
    def _validate_output(self, output: Any) -> Any:
        """Format validation results"""
        if isinstance(output, dict):
            # Ensure standard validation response format
            if "valid" not in output:
                output["valid"] = False
            if "errors" not in output:
                output["errors"] = []
            if "warnings" not in output:
                output["warnings"] = []
        
        return output


class ExportTool(BaseVRSENTool):
    """
    Specialized base class for data export tools.
    """
    
    tool_category: str = "export"
    
    # Export-specific fields
    data: Any = Field(..., description="Data to export")
    output_path: str = Field(..., description="Output file path")
    format: str = Field("csv", description="Export format")
    
    def _validate_inputs(self) -> Dict[str, Any]:
        """Validate export-specific inputs"""
        result = super()._validate_inputs()
        
        if not result["valid"]:
            return result
        
        # Validate data
        if self.data is None:
            return {"valid": False, "message": "Export data cannot be None"}
        
        # Validate output path
        if not self.output_path:
            return {"valid": False, "message": "Output path cannot be empty"}
        
        # Validate format
        valid_formats = ["csv", "json", "excel", "html", "xml"]
        if self.format not in valid_formats:
            return {
                "valid": False,
                "message": f"Invalid export format. Must be one of: {valid_formats}"
            }
        
        return {"valid": True, "message": "Export inputs validated"}