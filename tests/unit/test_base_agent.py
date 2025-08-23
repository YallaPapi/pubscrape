"""
Unit tests for BaseAgent class and agent infrastructure.

Tests the core agent functionality including:
- Agent initialization and configuration
- Error handling and recovery
- Metrics tracking
- Request/response validation
- Retry logic with exponential backoff
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

try:
    from src.core.base_agent import BaseAgent, AgentConfig, AgentMetrics, SearchAgent, ProcessingAgent
    from src.infra.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
except ImportError:
    pytest.skip("Agent modules not available", allow_module_level=True)


class TestAgentConfig:
    """Test AgentConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = AgentConfig(name="test_agent", description="Test agent")
        
        assert config.name == "test_agent"
        assert config.description == "Test agent"
        assert config.model == "gpt-4-turbo-preview"
        assert config.temperature == 0.7
        assert config.max_retries == 3
        assert config.retry_delay == 2.0
        assert config.enable_metrics is True
        assert config.enable_caching is True
        assert config.log_level == "INFO"
        assert config.instructions_path is None
        assert config.tools == []
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = AgentConfig(
            name="custom_agent",
            description="Custom test agent",
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_retries=5,
            retry_delay=1.0,
            enable_metrics=False,
            log_level="DEBUG"
        )
        
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_retries == 5
        assert config.retry_delay == 1.0
        assert config.enable_metrics is False
        assert config.log_level == "DEBUG"


class TestAgentMetrics:
    """Test AgentMetrics dataclass"""
    
    def test_default_metrics(self):
        """Test default metrics initialization"""
        metrics = AgentMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_execution_time == 0.0
        assert metrics.average_response_time == 0.0
        assert metrics.error_counts == {}
        assert metrics.last_error is None
        assert metrics.last_success_time is None
    
    def test_metrics_updates(self):
        """Test metrics can be updated"""
        metrics = AgentMetrics()
        
        metrics.total_requests = 10
        metrics.successful_requests = 8
        metrics.failed_requests = 2
        metrics.error_counts["ValueError"] = 2
        
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 8
        assert metrics.failed_requests == 2
        assert metrics.error_counts["ValueError"] == 2


class MockBaseAgent(BaseAgent):
    """Mock BaseAgent implementation for testing"""
    
    def _get_default_instructions(self) -> str:
        return "Mock agent instructions"


class TestBaseAgent:
    """Test BaseAgent functionality"""
    
    @pytest.fixture
    def agent_config(self):
        """Create test agent configuration"""
        return AgentConfig(
            name="test_agent",
            description="Test agent for unit testing",
            max_retries=2,
            retry_delay=0.1  # Fast retries for testing
        )
    
    @pytest.fixture
    def mock_agent(self, agent_config):
        """Create mock agent instance"""
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            agent = MockBaseAgent(agent_config)
            return agent
    
    def test_agent_initialization(self, agent_config):
        """Test agent initialization"""
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            agent = MockBaseAgent(agent_config)
            
            assert agent.config == agent_config
            assert isinstance(agent.metrics, AgentMetrics)
            assert isinstance(agent.error_handler, ErrorHandler)
            assert agent.logger is not None
    
    def test_default_instructions(self, mock_agent):
        """Test default instructions loading"""
        instructions = mock_agent._get_default_instructions()
        assert instructions == "Mock agent instructions"
    
    def test_response_validation_success(self, mock_agent):
        """Test successful response validation"""
        test_message = {"status": "success", "data": "test_data"}
        
        result = mock_agent.response_validator(test_message)
        
        assert result == test_message
        assert mock_agent.metrics.total_requests == 1
        assert mock_agent.metrics.successful_requests == 1
        assert mock_agent.metrics.failed_requests == 0
        assert mock_agent.metrics.last_success_time is not None
    
    def test_response_validation_failure(self, mock_agent):
        """Test failed response validation"""
        # Test with None message (should fail validation)
        result = mock_agent.response_validator(None)
        
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert "error_type" in result
        assert "error_message" in result
        assert result["agent"] == "test_agent"
        
        assert mock_agent.metrics.total_requests == 1
        assert mock_agent.metrics.successful_requests == 0
        assert mock_agent.metrics.failed_requests == 1
        assert mock_agent.metrics.last_error is not None
        assert "ValueError" in mock_agent.metrics.error_counts
    
    def test_execute_with_retry_success(self, mock_agent):
        """Test retry mechanism with successful execution"""
        mock_func = Mock(return_value="success")
        
        result = mock_agent.execute_with_retry(mock_func, "arg1", keyword="arg2")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_with("arg1", keyword="arg2")
    
    def test_execute_with_retry_eventual_success(self, mock_agent):
        """Test retry mechanism with eventual success"""
        mock_func = Mock(side_effect=[Exception("Fail"), Exception("Fail"), "success"])
        
        # Should succeed on third attempt
        result = mock_agent.execute_with_retry(mock_func, max_retries=3)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_execute_with_retry_all_failures(self, mock_agent):
        """Test retry mechanism with all failures"""
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        with pytest.raises(Exception, match="Always fails"):
            mock_agent.execute_with_retry(mock_func, max_retries=2)
        
        assert mock_func.call_count == 2
    
    def test_performance_tracking(self, mock_agent):
        """Test performance tracking context manager"""
        start_time = time.time()
        
        with mock_agent.performance_tracking("test_operation"):
            time.sleep(0.01)  # Small delay
        
        # Should have taken at least 0.01 seconds
        assert time.time() - start_time >= 0.01
    
    def test_get_metrics(self, mock_agent):
        """Test metrics retrieval"""
        # Simulate some activity
        mock_agent.response_validator({"test": "data"})
        mock_agent.response_validator(None)  # This will fail
        
        metrics = mock_agent.get_metrics()
        
        assert metrics["agent_name"] == "test_agent"
        assert metrics["total_requests"] == 2
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == 0.5
        assert "error_counts" in metrics
        assert "last_error" in metrics
    
    def test_reset_metrics(self, mock_agent):
        """Test metrics reset"""
        # Generate some metrics
        mock_agent.response_validator({"test": "data"})
        
        # Reset metrics
        mock_agent.reset_metrics()
        
        metrics = mock_agent.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
    
    def test_context_manager(self, agent_config):
        """Test agent as context manager"""
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            with MockBaseAgent(agent_config) as agent:
                assert isinstance(agent, MockBaseAgent)
                # Agent should be usable within context
                assert agent.config.name == "test_agent"


class TestSearchAgent:
    """Test SearchAgent specialized functionality"""
    
    @pytest.fixture
    def search_agent_config(self):
        """Create search agent configuration"""
        return AgentConfig(
            name="search_agent",
            description="Search agent for testing"
        )
    
    @pytest.fixture
    def mock_search_agent(self, search_agent_config):
        """Create mock search agent"""
        class MockSearchAgent(SearchAgent):
            def _get_default_instructions(self) -> str:
                return "Search agent instructions"
        
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            agent = MockSearchAgent(search_agent_config)
            return agent
    
    def test_search_agent_initialization(self, mock_search_agent):
        """Test search agent initialization"""
        assert hasattr(mock_search_agent, 'search_metrics')
        assert mock_search_agent.search_metrics["total_searches"] == 0
        assert mock_search_agent.search_metrics["total_results_found"] == 0
        assert mock_search_agent.search_metrics["blocked_requests"] == 0
    
    def test_track_search_success(self, mock_search_agent):
        """Test successful search tracking"""
        mock_search_agent.track_search("test query", 10, blocked=False)
        
        metrics = mock_search_agent.search_metrics
        assert metrics["total_searches"] == 1
        assert metrics["total_results_found"] == 10
        assert metrics["blocked_requests"] == 0
        assert metrics["average_results_per_search"] == 10.0
    
    def test_track_search_blocked(self, mock_search_agent):
        """Test blocked search tracking"""
        mock_search_agent.track_search("blocked query", 0, blocked=True)
        
        metrics = mock_search_agent.search_metrics
        assert metrics["total_searches"] == 1
        assert metrics["total_results_found"] == 0
        assert metrics["blocked_requests"] == 1
        assert metrics["average_results_per_search"] == 0.0
    
    def test_get_search_metrics(self, mock_search_agent):
        """Test search metrics retrieval"""
        mock_search_agent.track_search("query1", 5)
        mock_search_agent.track_search("query2", 15)
        
        metrics = mock_search_agent.get_search_metrics()
        
        # Should include both base and search metrics
        assert "agent_name" in metrics
        assert "total_searches" in metrics
        assert "total_results_found" in metrics
        assert metrics["total_searches"] == 2
        assert metrics["total_results_found"] == 20
        assert metrics["average_results_per_search"] == 10.0


class TestProcessingAgent:
    """Test ProcessingAgent specialized functionality"""
    
    @pytest.fixture
    def processing_agent_config(self):
        """Create processing agent configuration"""
        return AgentConfig(
            name="processing_agent",
            description="Processing agent for testing"
        )
    
    @pytest.fixture
    def mock_processing_agent(self, processing_agent_config):
        """Create mock processing agent"""
        class MockProcessingAgent(ProcessingAgent):
            def _get_default_instructions(self) -> str:
                return "Processing agent instructions"
        
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            agent = MockProcessingAgent(processing_agent_config)
            return agent
    
    def test_processing_agent_initialization(self, mock_processing_agent):
        """Test processing agent initialization"""
        assert hasattr(mock_processing_agent, 'processing_metrics')
        assert mock_processing_agent.processing_metrics["total_items_processed"] == 0
        assert mock_processing_agent.processing_metrics["successful_items"] == 0
        assert mock_processing_agent.processing_metrics["failed_items"] == 0
        assert mock_processing_agent.processing_metrics["data_quality_score"] == 1.0
    
    def test_track_processing_success(self, mock_processing_agent):
        """Test successful processing tracking"""
        mock_processing_agent.track_processing(
            items_count=10,
            success_count=9,
            processing_time=2.0
        )
        
        metrics = mock_processing_agent.processing_metrics
        assert metrics["total_items_processed"] == 10
        assert metrics["successful_items"] == 9
        assert metrics["failed_items"] == 1
        assert metrics["average_processing_time"] == 2.0
        assert metrics["data_quality_score"] == 0.9
    
    def test_track_processing_multiple_batches(self, mock_processing_agent):
        """Test processing tracking across multiple batches"""
        # First batch
        mock_processing_agent.track_processing(
            items_count=10,
            success_count=8,
            processing_time=1.0
        )
        
        # Second batch
        mock_processing_agent.track_processing(
            items_count=20,
            success_count=18,
            processing_time=3.0
        )
        
        metrics = mock_processing_agent.processing_metrics
        assert metrics["total_items_processed"] == 30
        assert metrics["successful_items"] == 26
        assert metrics["failed_items"] == 4
        assert abs(metrics["data_quality_score"] - (26/30)) < 0.001
        
        # Average processing time should be weighted
        expected_avg = (1.0 * 10 + 3.0 * 20) / 30
        assert abs(metrics["average_processing_time"] - expected_avg) < 0.001
    
    def test_get_processing_metrics(self, mock_processing_agent):
        """Test processing metrics retrieval"""
        mock_processing_agent.track_processing(5, 4, 1.5)
        
        metrics = mock_processing_agent.get_processing_metrics()
        
        # Should include both base and processing metrics
        assert "agent_name" in metrics
        assert "total_items_processed" in metrics
        assert "data_quality_score" in metrics
        assert metrics["total_items_processed"] == 5
        assert metrics["successful_items"] == 4
        assert metrics["data_quality_score"] == 0.8


class TestAgentErrorHandling:
    """Test agent error handling capabilities"""
    
    @pytest.fixture
    def error_prone_agent(self):
        """Create agent that simulates various errors"""
        class ErrorProneAgent(BaseAgent):
            def _get_default_instructions(self) -> str:
                return "Error-prone agent for testing"
            
            def _validate_response(self, message):
                if message == "timeout":
                    raise TimeoutError("Request timed out")
                elif message == "network":
                    raise ConnectionError("Network error")
                elif message == "value":
                    raise ValueError("Invalid value")
                return message
        
        config = AgentConfig(name="error_agent", description="Error testing")
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            return ErrorProneAgent(config)
    
    def test_timeout_error_handling(self, error_prone_agent):
        """Test timeout error handling"""
        result = error_prone_agent.response_validator("timeout")
        
        assert result["status"] == "error"
        assert result["error_type"] == "TimeoutError"
        assert "timed out" in result["error_message"]
        assert "TimeoutError" in error_prone_agent.metrics.error_counts
    
    def test_network_error_handling(self, error_prone_agent):
        """Test network error handling"""
        result = error_prone_agent.response_validator("network")
        
        assert result["status"] == "error"
        assert result["error_type"] == "ConnectionError"
        assert "ConnectionError" in error_prone_agent.metrics.error_counts
    
    def test_multiple_error_types(self, error_prone_agent):
        """Test tracking of multiple error types"""
        # Generate different types of errors
        error_prone_agent.response_validator("timeout")
        error_prone_agent.response_validator("network")
        error_prone_agent.response_validator("value")
        error_prone_agent.response_validator("timeout")  # Second timeout
        
        error_counts = error_prone_agent.metrics.error_counts
        assert error_counts["TimeoutError"] == 2
        assert error_counts["ConnectionError"] == 1
        assert error_counts["ValueError"] == 1
        
        metrics = error_prone_agent.get_metrics()
        assert metrics["failed_requests"] == 4
        assert metrics["success_rate"] == 0.0


@pytest.mark.slow
class TestAgentPerformance:
    """Test agent performance characteristics"""
    
    @pytest.fixture
    def performance_agent(self):
        """Create agent for performance testing"""
        config = AgentConfig(
            name="perf_agent",
            description="Performance testing agent",
            max_retries=1,
            retry_delay=0.01
        )
        
        with patch('src.core.base_agent.Agent.__init__', return_value=None):
            return MockBaseAgent(config)
    
    def test_response_time_tracking(self, performance_agent):
        """Test response time tracking accuracy"""
        # Simulate processing delay
        def slow_validation(message):
            time.sleep(0.05)  # 50ms delay
            return message
        
        with patch.object(performance_agent, '_validate_response', slow_validation):
            start_time = time.time()
            performance_agent.response_validator({"test": "data"})
            actual_duration = time.time() - start_time
        
        metrics = performance_agent.get_metrics()
        tracked_time = metrics["average_response_time"]
        
        # Tracked time should be close to actual duration
        assert abs(tracked_time - actual_duration) < 0.01
        assert tracked_time >= 0.05  # At least the sleep duration
    
    def test_high_volume_requests(self, performance_agent):
        """Test agent under high request volume"""
        num_requests = 100
        
        start_time = time.time()
        for i in range(num_requests):
            performance_agent.response_validator({"request": i})
        duration = time.time() - start_time
        
        metrics = performance_agent.get_metrics()
        assert metrics["total_requests"] == num_requests
        assert metrics["successful_requests"] == num_requests
        assert metrics["success_rate"] == 1.0
        
        # Should handle requests efficiently
        requests_per_second = num_requests / duration
        assert requests_per_second > 50  # Should handle at least 50 req/sec
    
    def test_memory_efficiency(self, performance_agent):
        """Test agent memory usage remains reasonable"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Generate many requests
        for i in range(1000):
            large_data = {"data": "x" * 1000, "id": i}
            performance_agent.response_validator(large_data)
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50
