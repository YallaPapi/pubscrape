"""
Agency Factory for VRSEN Lead Generation System

Centralized factory for creating and managing agency swarms with
optimized configuration and dependency injection.
"""

import logging
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass
from pathlib import Path

from agency_swarm import Agency, set_openai_key

from ..core.config_manager import config_manager
from ..core.base_agent import BaseAgent
from ..infra.error_handler import ErrorHandler


@dataclass
class AgencyConfig:
    """Configuration for an agency swarm"""
    name: str
    description: str
    agents: List[str]
    communication_flow: List[List[str]]
    enable_metrics: bool = True
    enable_caching: bool = True
    enable_gradio: bool = False
    max_iterations: int = 10


class AgencyFactory:
    """
    Factory for creating and managing optimized agency swarms.
    
    Features:
    - Centralized agent registration and creation
    - Dependency injection for tools and infrastructure
    - Configuration-driven agency setup
    - Performance monitoring and metrics
    - Error recovery and fallback strategies
    """
    
    def __init__(self):
        """Initialize agency factory"""
        self.logger = self._setup_logging()
        self.error_handler = ErrorHandler(agent_name="agency_factory")
        
        # Agent registry
        self._agent_registry: Dict[str, Type[BaseAgent]] = {}
        self._agent_instances: Dict[str, BaseAgent] = {}
        
        # Agency registry
        self._agencies: Dict[str, Agency] = {}
        
        # Load configuration
        self.config = config_manager.config
        
        # Initialize OpenAI
        self._initialize_openai()
        
        # Register default agents
        self._register_default_agents()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for factory"""
        logger = logging.getLogger("vrsen.agency_factory")
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - AgencyFactory - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _initialize_openai(self):
        """Initialize OpenAI with API key"""
        api_key = self.config.api.openai_api_key
        
        if not api_key:
            self.logger.warning("OpenAI API key not configured")
            return
        
        try:
            set_openai_key(api_key)
            self.logger.info("OpenAI API key configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to set OpenAI API key: {e}")
    
    def _register_default_agents(self):
        """Register default VRSEN agents"""
        try:
            # Import refactored agents
            from ..agents.refactored.campaign_ceo import CampaignCEO
            from ..agents.refactored.bing_navigator import BingNavigator
            
            self.register_agent("CampaignCEO", CampaignCEO)
            self.register_agent("BingNavigator", BingNavigator)
            
            # Import other agents as they're refactored
            # For now, use original agents as fallback
            try:
                from SerpParser import SerpParser
                from DomainClassifier import DomainClassifier
                from SiteCrawler import SiteCrawler
                from EmailExtractor import EmailExtractor
                from ValidatorDedupe import ValidatorDedupe
                from Exporter import Exporter
                
                self.register_agent("SerpParser", SerpParser)
                self.register_agent("DomainClassifier", DomainClassifier)
                self.register_agent("SiteCrawler", SiteCrawler)
                self.register_agent("EmailExtractor", EmailExtractor)
                self.register_agent("ValidatorDedupe", ValidatorDedupe)
                self.register_agent("Exporter", Exporter)
                
            except ImportError as e:
                self.logger.warning(f"Could not import original agents: {e}")
            
            self.logger.info(f"Registered {len(self._agent_registry)} agents")
            
        except Exception as e:
            self.logger.error(f"Failed to register default agents: {e}")
    
    def register_agent(self, name: str, agent_class: Type[BaseAgent]):
        """
        Register an agent class with the factory.
        
        Args:
            name: Agent name
            agent_class: Agent class to register
        """
        self._agent_registry[name] = agent_class
        self.logger.debug(f"Registered agent: {name}")
    
    def create_agent(self, name: str, **kwargs) -> BaseAgent:
        """
        Create an agent instance.
        
        Args:
            name: Agent name
            **kwargs: Additional arguments for agent
            
        Returns:
            Agent instance
        """
        # Check if already created
        if name in self._agent_instances:
            self.logger.debug(f"Returning existing agent: {name}")
            return self._agent_instances[name]
        
        # Check if registered
        if name not in self._agent_registry:
            raise ValueError(f"Agent not registered: {name}")
        
        # Create instance
        try:
            agent_class = self._agent_registry[name]
            agent = agent_class(**kwargs)
            
            # Cache instance
            self._agent_instances[name] = agent
            
            self.logger.info(f"Created agent: {name}")
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to create agent {name}: {e}")
            raise
    
    def create_agency(self, config: AgencyConfig) -> Agency:
        """
        Create an agency swarm from configuration.
        
        Args:
            config: Agency configuration
            
        Returns:
            Configured Agency instance
        """
        try:
            self.logger.info(f"Creating agency: {config.name}")
            
            # Create agents
            agents = []
            for agent_name in config.agents:
                agent = self.create_agent(agent_name)
                agents.append(agent)
            
            # Build communication flow
            flow = []
            for connection in config.communication_flow:
                if len(connection) == 1:
                    # Entry point
                    agent = self._get_agent_by_name(connection[0], agents)
                    flow.append(agent)
                else:
                    # Communication pair
                    from_agent = self._get_agent_by_name(connection[0], agents)
                    to_agents = [self._get_agent_by_name(name, agents) 
                               for name in connection[1:]]
                    flow.append([from_agent] + to_agents)
            
            # Create agency
            agency = Agency(
                agency_chart=flow,
                max_prompt_tokens=4000,
                temperature=0.7
            )
            
            # Store agency
            self._agencies[config.name] = agency
            
            self.logger.info(f"Agency '{config.name}' created successfully")
            return agency
            
        except Exception as e:
            self.logger.error(f"Failed to create agency: {e}")
            raise
    
    def _get_agent_by_name(self, name: str, agents: List[BaseAgent]) -> BaseAgent:
        """Get agent from list by name"""
        for agent in agents:
            if agent.name == name or agent.config.name == name:
                return agent
        raise ValueError(f"Agent not found: {name}")
    
    def create_vrsen_agency(self) -> Agency:
        """
        Create the complete VRSEN lead generation agency.
        
        Returns:
            Configured VRSEN agency
        """
        config = AgencyConfig(
            name="VRSEN_Lead_Generation",
            description="Complete lead generation pipeline with 8 specialized agents",
            agents=[
                "CampaignCEO",
                "BingNavigator",
                "SerpParser",
                "DomainClassifier",
                "SiteCrawler",
                "EmailExtractor",
                "ValidatorDedupe",
                "Exporter"
            ],
            communication_flow=[
                ["CampaignCEO"],  # Entry point
                ["CampaignCEO", "BingNavigator"],
                ["BingNavigator", "SerpParser"],
                ["SerpParser", "DomainClassifier"],
                ["DomainClassifier", "SiteCrawler"],
                ["SiteCrawler", "EmailExtractor"],
                ["EmailExtractor", "ValidatorDedupe"],
                ["ValidatorDedupe", "Exporter"],
                ["Exporter", "CampaignCEO"]  # Report back
            ]
        )
        
        return self.create_agency(config)
    
    def create_minimal_agency(self) -> Agency:
        """
        Create a minimal agency for testing.
        
        Returns:
            Minimal agency with 2 agents
        """
        config = AgencyConfig(
            name="Minimal_Test",
            description="Minimal agency for testing",
            agents=["CampaignCEO", "BingNavigator"],
            communication_flow=[
                ["CampaignCEO"],
                ["CampaignCEO", "BingNavigator"]
            ]
        )
        
        return self.create_agency(config)
    
    def get_agency(self, name: str) -> Optional[Agency]:
        """
        Get an existing agency by name.
        
        Args:
            name: Agency name
            
        Returns:
            Agency instance or None
        """
        return self._agencies.get(name)
    
    def list_agencies(self) -> List[str]:
        """List all created agencies"""
        return list(self._agencies.keys())
    
    def list_agents(self) -> List[str]:
        """List all registered agents"""
        return list(self._agent_registry.keys())
    
    def get_agent_metrics(self, agent_name: str) -> Dict[str, Any]:
        """
        Get metrics for a specific agent.
        
        Args:
            agent_name: Agent name
            
        Returns:
            Agent metrics dictionary
        """
        if agent_name not in self._agent_instances:
            return {"error": "Agent not created"}
        
        agent = self._agent_instances[agent_name]
        
        if hasattr(agent, 'get_metrics'):
            return agent.get_metrics()
        else:
            return {"error": "Agent does not support metrics"}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all agents and agencies"""
        metrics = {
            "agencies": {},
            "agents": {}
        }
        
        # Agency metrics
        for name in self._agencies:
            metrics["agencies"][name] = {
                "status": "active",
                "agent_count": len(self._agencies[name].agents)
                if hasattr(self._agencies[name], 'agents') else 0
            }
        
        # Agent metrics
        for name, agent in self._agent_instances.items():
            if hasattr(agent, 'get_metrics'):
                metrics["agents"][name] = agent.get_metrics()
        
        return metrics
    
    def cleanup(self):
        """Clean up all resources"""
        self.logger.info("Cleaning up agency factory resources")
        
        # Clean up agents
        for agent in self._agent_instances.values():
            if hasattr(agent, 'cleanup'):
                agent.cleanup()
        
        # Clear registries
        self._agent_instances.clear()
        self._agencies.clear()
        
        self.logger.info("Cleanup complete")


# Singleton instance
agency_factory = AgencyFactory()


def create_agency(agency_type: str = "full") -> Agency:
    """
    Convenience function to create an agency.
    
    Args:
        agency_type: Type of agency ("full", "minimal", "test")
        
    Returns:
        Configured agency instance
    """
    if agency_type == "full":
        return agency_factory.create_vrsen_agency()
    elif agency_type == "minimal":
        return agency_factory.create_minimal_agency()
    else:
        raise ValueError(f"Unknown agency type: {agency_type}")