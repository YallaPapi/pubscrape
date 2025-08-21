"""
Base Agent Class for VRSEN Agency Swarm

Provides common functionality, error handling, and standardized interfaces
for all agents in the lead generation pipeline.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Type, Union
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from contextlib import contextmanager

from agency_swarm import Agent
from agency_swarm.tools import BaseTool

from ..infra.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from ..core.config_manager import ConfigManager


@dataclass
class AgentMetrics:
    """Tracks agent performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_execution_time: float = 0.0
    average_response_time: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=dict)
    last_error: Optional[str] = None
    last_success_time: Optional[float] = None


@dataclass
class AgentConfig:
    """Configuration for base agent"""
    name: str
    description: str
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_retries: int = 3
    retry_delay: float = 2.0
    enable_metrics: bool = True
    enable_caching: bool = True
    log_level: str = "INFO"
    instructions_path: Optional[str] = None
    tools: List[Type[BaseTool]] = field(default_factory=list)


class BaseAgent(Agent):
    """
    Enhanced base agent with common functionality for all VRSEN agents.
    
    Features:
    - Standardized error handling with recovery strategies
    - Performance metrics tracking
    - Configuration management
    - Request/response validation
    - Retry logic with exponential backoff
    - Structured logging
    - Resource cleanup
    """
    
    def __init__(self, config: AgentConfig, **kwargs):
        """
        Initialize base agent with enhanced configuration.
        
        Args:
            config: Agent configuration dataclass
            **kwargs: Additional arguments for parent Agent class
        """
        self.config = config
        self.metrics = AgentMetrics()
        self.error_handler = ErrorHandler(agent_name=config.name)
        self._setup_logging()
        
        # Load instructions if path provided
        instructions = self._load_instructions() if config.instructions_path else ""
        
        # Initialize parent Agent class
        super().__init__(
            name=config.name,
            description=config.description,
            instructions=instructions,
            tools=config.tools,
            model=config.model,
            temperature=config.temperature,
            **kwargs
        )
        
        self.logger.info(f"{config.name} agent initialized successfully")
    
    def _setup_logging(self):
        """Configure structured logging for the agent"""
        self.logger = logging.getLogger(f"vrsen.agents.{self.config.name}")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.config.name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_instructions(self) -> str:
        """Load instructions from file with error handling"""
        try:
            instructions_path = Path(self.config.instructions_path)
            if instructions_path.exists():
                return instructions_path.read_text(encoding='utf-8')
            else:
                self.logger.warning(f"Instructions file not found: {instructions_path}")
                return self._get_default_instructions()
        except Exception as e:
            self.logger.error(f"Failed to load instructions: {e}")
            return self._get_default_instructions()
    
    @abstractmethod
    def _get_default_instructions(self) -> str:
        """
        Get default instructions for the agent.
        Must be implemented by subclasses.
        """
        pass
    
    def response_validator(self, message: Any) -> Any:
        """
        Enhanced response validation with metrics tracking.
        
        Args:
            message: Response message to validate
            
        Returns:
            Validated message or error response
        """
        try:
            # Track request
            self.metrics.total_requests += 1
            start_time = time.time()
            
            # Perform validation
            validated = self._validate_response(message)
            
            # Update metrics on success
            execution_time = time.time() - start_time
            self.metrics.successful_requests += 1
            self.metrics.total_execution_time += execution_time
            self.metrics.average_response_time = (
                self.metrics.total_execution_time / self.metrics.successful_requests
            )
            self.metrics.last_success_time = time.time()
            
            self.logger.debug(f"Response validated in {execution_time:.2f}s")
            return validated
            
        except Exception as e:
            # Track failure
            self.metrics.failed_requests += 1
            self.metrics.last_error = str(e)
            
            # Log error with context
            self.error_handler.log_error(
                error=e,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                context={"message_type": type(message).__name__}
            )
            
            # Attempt recovery
            return self._handle_validation_error(e, message)
    
    def _validate_response(self, message: Any) -> Any:
        """
        Perform actual validation logic.
        Can be overridden by subclasses for custom validation.
        
        Args:
            message: Message to validate
            
        Returns:
            Validated message
        """
        if message is None:
            raise ValueError("Response message cannot be None")
        
        # Default validation - just return the message
        return message
    
    def _handle_validation_error(self, error: Exception, message: Any) -> Any:
        """
        Handle validation errors with recovery strategies.
        
        Args:
            error: The validation error
            message: The original message
            
        Returns:
            Recovered response or error message
        """
        error_type = type(error).__name__
        
        # Increment error count for this type
        self.metrics.error_counts[error_type] = (
            self.metrics.error_counts.get(error_type, 0) + 1
        )
        
        # Log detailed error
        self.logger.error(f"Validation error: {error}", exc_info=True)
        
        # Return safe error response
        return {
            "status": "error",
            "error_type": error_type,
            "error_message": str(error),
            "agent": self.config.name,
            "timestamp": time.time()
        }
    
    def execute_with_retry(self, 
                          func: callable, 
                          *args, 
                          max_retries: Optional[int] = None,
                          **kwargs) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            max_retries: Override default max retries
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        max_retries = max_retries or self.config.max_retries
        delay = self.config.retry_delay
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"All {max_retries} attempts failed: {e}")
                    raise
                
                self.logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
                delay *= 2  # Exponential backoff
    
    @contextmanager
    def performance_tracking(self, operation_name: str):
        """
        Context manager for tracking operation performance.
        
        Args:
            operation_name: Name of the operation being tracked
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Starting operation: {operation_name}")
            yield
            
        finally:
            duration = time.time() - start_time
            self.logger.debug(f"Operation '{operation_name}' completed in {duration:.2f}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current agent metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "agent_name": self.config.name,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": (
                self.metrics.successful_requests / self.metrics.total_requests
                if self.metrics.total_requests > 0 else 0
            ),
            "average_response_time": self.metrics.average_response_time,
            "error_counts": self.metrics.error_counts,
            "last_error": self.metrics.last_error,
            "last_success_time": self.metrics.last_success_time
        }
    
    def reset_metrics(self):
        """Reset agent metrics"""
        self.metrics = AgentMetrics()
        self.logger.info("Agent metrics reset")
    
    def cleanup(self):
        """
        Cleanup agent resources.
        Should be called when agent is no longer needed.
        """
        self.logger.info(f"Cleaning up {self.config.name} agent")
        
        # Log final metrics
        if self.config.enable_metrics:
            metrics = self.get_metrics()
            self.logger.info(f"Final metrics: {metrics}")
        
        # Subclasses can override to add specific cleanup
        self._cleanup_resources()
    
    def _cleanup_resources(self):
        """
        Cleanup agent-specific resources.
        Override in subclasses for custom cleanup.
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()


class SearchAgent(BaseAgent):
    """
    Specialized base class for search-related agents.
    Adds search-specific functionality and metrics.
    """
    
    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(config, **kwargs)
        
        # Additional search-specific metrics
        self.search_metrics = {
            "total_searches": 0,
            "total_results_found": 0,
            "average_results_per_search": 0.0,
            "blocked_requests": 0,
            "rate_limited_requests": 0
        }
    
    def track_search(self, query: str, results_count: int, blocked: bool = False):
        """
        Track search operation metrics.
        
        Args:
            query: Search query executed
            results_count: Number of results found
            blocked: Whether request was blocked
        """
        self.search_metrics["total_searches"] += 1
        
        if blocked:
            self.search_metrics["blocked_requests"] += 1
        else:
            self.search_metrics["total_results_found"] += results_count
            self.search_metrics["average_results_per_search"] = (
                self.search_metrics["total_results_found"] / 
                (self.search_metrics["total_searches"] - self.search_metrics["blocked_requests"])
            )
        
        self.logger.debug(
            f"Search tracked - Query: '{query}', Results: {results_count}, Blocked: {blocked}"
        )
    
    def get_search_metrics(self) -> Dict[str, Any]:
        """Get search-specific metrics"""
        base_metrics = self.get_metrics()
        base_metrics.update(self.search_metrics)
        return base_metrics


class ProcessingAgent(BaseAgent):
    """
    Specialized base class for data processing agents.
    Adds processing-specific functionality and metrics.
    """
    
    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(config, **kwargs)
        
        # Processing-specific metrics
        self.processing_metrics = {
            "total_items_processed": 0,
            "successful_items": 0,
            "failed_items": 0,
            "average_processing_time": 0.0,
            "data_quality_score": 1.0
        }
    
    def track_processing(self, 
                        items_count: int, 
                        success_count: int,
                        processing_time: float):
        """
        Track data processing metrics.
        
        Args:
            items_count: Total items processed
            success_count: Successfully processed items
            processing_time: Time taken to process
        """
        self.processing_metrics["total_items_processed"] += items_count
        self.processing_metrics["successful_items"] += success_count
        self.processing_metrics["failed_items"] += (items_count - success_count)
        
        # Update average processing time
        total_time = (
            self.processing_metrics["average_processing_time"] * 
            (self.processing_metrics["total_items_processed"] - items_count) +
            processing_time
        )
        self.processing_metrics["average_processing_time"] = (
            total_time / self.processing_metrics["total_items_processed"]
            if self.processing_metrics["total_items_processed"] > 0 else 0
        )
        
        # Calculate data quality score
        if self.processing_metrics["total_items_processed"] > 0:
            self.processing_metrics["data_quality_score"] = (
                self.processing_metrics["successful_items"] /
                self.processing_metrics["total_items_processed"]
            )
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing-specific metrics"""
        base_metrics = self.get_metrics()
        base_metrics.update(self.processing_metrics)
        return base_metrics