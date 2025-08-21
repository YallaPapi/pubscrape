"""
Comprehensive test suite for refactored VRSEN Agency Swarm

Tests the refactored components with improved error handling,
metrics tracking, and performance monitoring.
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.agency_factory import agency_factory, create_agency, AgencyConfig
from src.core.base_agent import BaseAgent, AgentConfig, SearchAgent, ProcessingAgent
from src.core.base_tool import BaseVRSENTool, SearchTool
from src.core.config_manager import config_manager
from src.infra.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity


class TestBaseAgent(unittest.TestCase):
    """Test the enhanced base agent functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = AgentConfig(
            name="TestAgent",
            description="Test agent for unit tests",
            model="gpt-4-turbo-preview"
        )
    
    def test_agent_creation(self):
        """Test agent creation with configuration"""
        # Create a test agent class
        class TestAgent(BaseAgent):
            def _get_default_instructions(self):
                return "Test instructions"
        
        agent = TestAgent(self.config)
        
        self.assertEqual(agent.config.name, "TestAgent")
        self.assertIsNotNone(agent.metrics)
        self.assertIsNotNone(agent.error_handler)
        self.assertIsNotNone(agent.logger)
    
    def test_agent_metrics_tracking(self):
        """Test metrics tracking functionality"""
        class TestAgent(BaseAgent):
            def _get_default_instructions(self):
                return "Test instructions"
        
        agent = TestAgent(self.config)
        
        # Simulate successful request
        agent.metrics.total_requests = 5
        agent.metrics.successful_requests = 4
        agent.metrics.failed_requests = 1
        
        metrics = agent.get_metrics()
        
        self.assertEqual(metrics["total_requests"], 5)
        self.assertEqual(metrics["successful_requests"], 4)
        self.assertEqual(metrics["failed_requests"], 1)
        self.assertEqual(metrics["success_rate"], 0.8)
    
    def test_response_validation(self):
        """Test response validation with error handling"""
        class TestAgent(BaseAgent):
            def _get_default_instructions(self):
                return "Test instructions"
            
            def _validate_response(self, message):
                if message == "error":
                    raise ValueError("Test error")
                return message
        
        agent = TestAgent(self.config)
        
        # Test successful validation
        result = agent.response_validator("success")
        self.assertEqual(result, "success")
        self.assertEqual(agent.metrics.successful_requests, 1)
        
        # Test error handling
        result = agent.response_validator("error")
        self.assertEqual(result["status"], "error")
        self.assertEqual(agent.metrics.failed_requests, 1)
    
    def test_retry_logic(self):
        """Test retry logic with exponential backoff"""
        class TestAgent(BaseAgent):
            def _get_default_instructions(self):
                return "Test instructions"
        
        agent = TestAgent(self.config)
        agent.config.max_retries = 3
        agent.config.retry_delay = 0.1  # Short delay for testing
        
        # Create a function that fails twice then succeeds
        call_count = 0
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Test error")
            return "success"
        
        result = agent.execute_with_retry(test_func)
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)


class TestBaseTool(unittest.TestCase):
    """Test the enhanced base tool functionality"""
    
    def test_tool_creation(self):
        """Test tool creation and initialization"""
        class TestTool(BaseVRSENTool):
            tool_name = "TestTool"
            
            def _execute(self):
                return {"result": "success"}
        
        tool = TestTool()
        
        self.assertEqual(tool.tool_name, "TestTool")
        self.assertIsNotNone(tool.metrics)
        self.assertIsNotNone(tool.error_handler)
        self.assertIsNotNone(tool.logger)
    
    def test_tool_execution_success(self):
        """Test successful tool execution"""
        class TestTool(BaseVRSENTool):
            tool_name = "TestTool"
            
            def _execute(self):
                return {"data": "test_result"}
        
        tool = TestTool()
        result = tool.run()
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["data"], "test_result")
        self.assertEqual(tool.metrics.successful_executions, 1)
    
    def test_tool_execution_with_retry(self):
        """Test tool execution with retry on failure"""
        class TestTool(BaseVRSENTool):
            tool_name = "TestTool"
            execution_count = 0
            
            def _execute(self):
                self.execution_count += 1
                if self.execution_count < 2:
                    raise Exception("Temporary failure")
                return {"data": "success"}
        
        tool = TestTool(max_retries=3, retry_delay=0.1)
        result = tool.run()
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(tool.execution_count, 2)
    
    def test_tool_metrics(self):
        """Test tool metrics tracking"""
        class TestTool(BaseVRSENTool):
            tool_name = "TestTool"
            
            def _execute(self):
                return {"data": "test"}
        
        tool = TestTool()
        
        # Execute multiple times
        for _ in range(3):
            tool.run()
        
        metrics = tool.get_metrics()
        
        self.assertEqual(metrics["total_executions"], 3)
        self.assertEqual(metrics["successful_executions"], 3)
        self.assertEqual(metrics["failed_executions"], 0)
        self.assertEqual(metrics["success_rate"], 1.0)


class TestConfigManager(unittest.TestCase):
    """Test configuration management system"""
    
    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton"""
        from src.core.config_manager import ConfigManager
        
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        self.assertIs(manager1, manager2)
    
    def test_config_get_set(self):
        """Test getting and setting configuration values"""
        # Set a value
        config_manager.set("search.max_pages_per_query", 10)
        
        # Get the value
        value = config_manager.get("search.max_pages_per_query")
        
        self.assertEqual(value, 10)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Set valid values
        config_manager.set("search.max_pages_per_query", 5)
        config_manager.set("search.rate_limit_rpm", 12)
        
        is_valid, errors = config_manager.validate()
        
        # Should be valid if OpenAI key is set
        if config_manager.get("api.openai_api_key"):
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
    
    def test_config_reset(self):
        """Test configuration reset"""
        # Change a value
        original = config_manager.get("search.max_pages_per_query")
        config_manager.set("search.max_pages_per_query", 999)
        
        # Reset
        config_manager.reset()
        
        # Value should be back to default
        reset_value = config_manager.get("search.max_pages_per_query")
        self.assertNotEqual(reset_value, 999)


class TestErrorHandler(unittest.TestCase):
    """Test error handling system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = ErrorHandler(agent_name="test_agent")
    
    def test_error_classification(self):
        """Test error classification"""
        # Test timeout error
        error = TimeoutError("Request timed out")
        category, severity = self.handler.classify_error(error)
        self.assertEqual(category, ErrorCategory.TIMEOUT)
        
        # Test rate limit error
        error = Exception("429 Too Many Requests")
        category, severity = self.handler.classify_error(error)
        self.assertEqual(category, ErrorCategory.RATE_LIMIT)
        
        # Test network error
        error = ConnectionError("Network unreachable")
        category, severity = self.handler.classify_error(error)
        self.assertEqual(category, ErrorCategory.NETWORK)
    
    def test_recovery_strategy_suggestion(self):
        """Test recovery strategy suggestions"""
        # Rate limit should suggest backoff
        strategy = self.handler.suggest_recovery_strategy(
            ErrorCategory.RATE_LIMIT,
            ErrorSeverity.HIGH
        )
        self.assertEqual(strategy.value, "retry_with_backoff")
        
        # Network error should suggest immediate retry
        strategy = self.handler.suggest_recovery_strategy(
            ErrorCategory.NETWORK,
            ErrorSeverity.MEDIUM
        )
        self.assertEqual(strategy.value, "retry_immediate")
        
        # Critical error should abort
        strategy = self.handler.suggest_recovery_strategy(
            ErrorCategory.UNKNOWN,
            ErrorSeverity.CRITICAL
        )
        self.assertEqual(strategy.value, "abort_operation")
    
    def test_error_logging(self):
        """Test error logging and tracking"""
        # Log an error
        error = ValueError("Test error")
        record = self.handler.log_error(
            error=error,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            operation="test_operation"
        )
        
        self.assertEqual(record.error_type, "ValueError")
        self.assertEqual(record.error_message, "Test error")
        self.assertEqual(record.category, ErrorCategory.VALIDATION)
        self.assertEqual(record.severity, ErrorSeverity.LOW)
        
        # Check statistics
        stats = self.handler.get_statistics()
        self.assertEqual(stats["total_errors"], 1)
        self.assertIn("validation", stats["errors_by_category"])


class TestAgencyFactory(unittest.TestCase):
    """Test agency factory functionality"""
    
    def test_agent_registration(self):
        """Test agent registration in factory"""
        # Create a test agent
        class CustomAgent(BaseAgent):
            def _get_default_instructions(self):
                return "Custom instructions"
        
        # Register agent
        agency_factory.register_agent("CustomAgent", CustomAgent)
        
        # Check registration
        agents = agency_factory.list_agents()
        self.assertIn("CustomAgent", agents)
    
    @patch('src.core.agency_factory.Agency')
    def test_agency_creation(self, mock_agency):
        """Test agency creation from configuration"""
        # Create test configuration
        config = AgencyConfig(
            name="TestAgency",
            description="Test agency",
            agents=["CampaignCEO", "BingNavigator"],
            communication_flow=[
                ["CampaignCEO"],
                ["CampaignCEO", "BingNavigator"]
            ]
        )
        
        # Mock the Agency class
        mock_agency_instance = MagicMock()
        mock_agency.return_value = mock_agency_instance
        
        # Create agency (this will use mocked Agency)
        agency = agency_factory.create_agency(config)
        
        # Verify agency was created
        self.assertIsNotNone(agency)
        mock_agency.assert_called_once()
    
    def test_metrics_collection(self):
        """Test metrics collection from agents"""
        # Create an agent
        from src.agents.refactored.campaign_ceo import CampaignCEO
        
        agent = agency_factory.create_agent("CampaignCEO")
        
        # Get metrics
        metrics = agency_factory.get_agent_metrics("CampaignCEO")
        
        self.assertIn("agent_name", metrics)
        self.assertEqual(metrics["agent_name"], "CampaignCEO")
        self.assertIn("total_requests", metrics)


class TestIntegration(unittest.TestCase):
    """Integration tests for refactored components"""
    
    def test_end_to_end_agent_tool_interaction(self):
        """Test agent using a tool"""
        # Create a test tool
        class TestSearchTool(SearchTool):
            tool_name = "TestSearchTool"
            
            def _execute(self):
                return {
                    "results": ["result1", "result2"],
                    "query": self.query
                }
        
        # Create a test agent
        class TestSearchAgent(SearchAgent):
            def _get_default_instructions(self):
                return "Test search agent"
            
            def execute_search_with_tool(self, query):
                tool = TestSearchTool(query=query, max_results=5)
                return tool.run()
        
        # Create agent
        config = AgentConfig(
            name="TestSearchAgent",
            description="Test agent",
            tools=[TestSearchTool]
        )
        agent = TestSearchAgent(config)
        
        # Execute search
        result = agent.execute_search_with_tool("test query")
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["query"], "test query")
        self.assertEqual(len(result["result"]["results"]), 2)
    
    def test_error_recovery_flow(self):
        """Test error recovery in tool execution"""
        class UnreliableTool(BaseVRSENTool):
            tool_name = "UnreliableTool"
            attempt_count = 0
            
            def _execute(self):
                self.attempt_count += 1
                if self.attempt_count == 1:
                    raise ConnectionError("Network error")
                elif self.attempt_count == 2:
                    raise TimeoutError("Timeout")
                else:
                    return {"data": "success"}
        
        tool = UnreliableTool(max_retries=3, retry_delay=0.1)
        result = tool.run()
        
        # Should succeed after retries
        self.assertEqual(result["status"], "success")
        self.assertEqual(tool.attempt_count, 3)
        
        # Check metrics
        metrics = tool.get_metrics()
        self.assertEqual(metrics["successful_executions"], 1)


def run_tests():
    """Run all tests with coverage reporting"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestBaseAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestBaseTool))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestAgencyFactory))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)