"""
Refactored Campaign CEO Agent

Orchestrates the entire lead generation campaign using enhanced base functionality.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ...core.base_agent import BaseAgent, AgentConfig
from ...core.config_manager import config_manager


@dataclass
class CampaignConfig:
    """Configuration for a lead generation campaign"""
    topic: str
    target_locations: List[str]
    max_leads: int = 100
    quality_threshold: float = 0.7
    enable_deduplication: bool = True
    export_format: str = "csv"


class CampaignCEO(BaseAgent):
    """
    Enhanced Campaign CEO Agent with improved orchestration capabilities.
    
    This agent serves as the central orchestrator for lead generation campaigns,
    coordinating all other agents and ensuring smooth pipeline execution.
    
    Improvements:
    - Centralized campaign configuration management
    - Progress tracking and reporting
    - Error recovery and fallback strategies
    - Performance optimization
    - Comprehensive metrics collection
    """
    
    def __init__(self):
        """Initialize Campaign CEO with enhanced configuration"""
        config = AgentConfig(
            name="CampaignCEO",
            description=(
                "Strategic orchestrator for lead generation campaigns. "
                "I coordinate the entire pipeline from search query generation "
                "to final lead export, ensuring quality and efficiency."
            ),
            model=config_manager.get("api.openai_model", "gpt-4-turbo-preview"),
            temperature=0.7,
            enable_metrics=True,
            instructions_path="instructions/campaign_ceo.md"
        )
        
        super().__init__(config)
        
        # Campaign-specific attributes
        self.active_campaigns: Dict[str, CampaignConfig] = {}
        self.campaign_metrics = {
            "total_campaigns": 0,
            "successful_campaigns": 0,
            "total_leads_generated": 0,
            "average_lead_quality": 0.0
        }
    
    def _get_default_instructions(self) -> str:
        """Provide default instructions for Campaign CEO"""
        return """
        You are the Campaign CEO, responsible for orchestrating lead generation campaigns.
        
        Your responsibilities:
        1. Parse and validate campaign requirements
        2. Generate effective search strategies
        3. Coordinate agent workflow:
           - Direct BingNavigator for search execution
           - Ensure SerpParser extracts URLs properly
           - Verify DomainClassifier filters results
           - Monitor SiteCrawler progress
           - Validate EmailExtractor results
           - Confirm ValidatorDedupe quality
           - Oversee Exporter output
        4. Track campaign progress and metrics
        5. Handle errors and implement recovery strategies
        6. Generate comprehensive campaign reports
        
        Communication style:
        - Clear and directive with other agents
        - Informative and professional with users
        - Focus on results and efficiency
        
        Quality standards:
        - Minimum 70% lead quality score
        - No duplicate leads in final output
        - All emails must be validated
        - Complete documentation of sources
        """
    
    def start_campaign(self, config: CampaignConfig) -> str:
        """
        Start a new lead generation campaign.
        
        Args:
            config: Campaign configuration
            
        Returns:
            Campaign ID
        """
        with self.performance_tracking("start_campaign"):
            campaign_id = f"campaign_{int(time.time())}"
            
            self.logger.info(f"Starting campaign {campaign_id}: {config.topic}")
            
            # Validate campaign configuration
            if not self._validate_campaign_config(config):
                raise ValueError("Invalid campaign configuration")
            
            # Store campaign
            self.active_campaigns[campaign_id] = config
            self.campaign_metrics["total_campaigns"] += 1
            
            # Initialize campaign workflow
            self._initialize_campaign_workflow(campaign_id, config)
            
            return campaign_id
    
    def _validate_campaign_config(self, config: CampaignConfig) -> bool:
        """Validate campaign configuration"""
        if not config.topic or len(config.topic.strip()) == 0:
            self.logger.error("Campaign topic cannot be empty")
            return False
        
        if not config.target_locations:
            self.logger.error("At least one target location required")
            return False
        
        if config.max_leads < 1:
            self.logger.error("max_leads must be at least 1")
            return False
        
        if config.quality_threshold < 0 or config.quality_threshold > 1:
            self.logger.error("quality_threshold must be between 0 and 1")
            return False
        
        return True
    
    def _initialize_campaign_workflow(self, campaign_id: str, config: CampaignConfig):
        """Initialize the campaign workflow"""
        # This would coordinate with other agents
        # For now, we'll create a workflow plan
        workflow = {
            "campaign_id": campaign_id,
            "steps": [
                {"agent": "BingNavigator", "action": "search", "status": "pending"},
                {"agent": "SerpParser", "action": "parse", "status": "pending"},
                {"agent": "DomainClassifier", "action": "classify", "status": "pending"},
                {"agent": "SiteCrawler", "action": "crawl", "status": "pending"},
                {"agent": "EmailExtractor", "action": "extract", "status": "pending"},
                {"agent": "ValidatorDedupe", "action": "validate", "status": "pending"},
                {"agent": "Exporter", "action": "export", "status": "pending"}
            ]
        }
        
        self.logger.debug(f"Workflow initialized for campaign {campaign_id}")
        return workflow
    
    def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get current status of a campaign.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Campaign status dictionary
        """
        if campaign_id not in self.active_campaigns:
            return {"error": "Campaign not found"}
        
        config = self.active_campaigns[campaign_id]
        
        return {
            "campaign_id": campaign_id,
            "topic": config.topic,
            "status": "active",  # Would track actual status
            "progress": {
                "leads_found": 0,  # Would track actual progress
                "leads_validated": 0,
                "leads_exported": 0
            },
            "metrics": self.get_metrics()
        }
    
    def stop_campaign(self, campaign_id: str) -> bool:
        """
        Stop an active campaign.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            True if stopped successfully
        """
        if campaign_id in self.active_campaigns:
            self.logger.info(f"Stopping campaign {campaign_id}")
            del self.active_campaigns[campaign_id]
            return True
        
        return False
    
    def _validate_response(self, message: Any) -> Any:
        """
        Enhanced response validation for campaign orchestration.
        
        Args:
            message: Response message to validate
            
        Returns:
            Validated message
        """
        # Perform base validation
        validated = super()._validate_response(message)
        
        # Add campaign-specific validation
        if isinstance(validated, dict):
            # Ensure required fields for campaign responses
            if "status" not in validated:
                validated["status"] = "unknown"
            
            if "campaign_id" in validated:
                # Validate campaign exists
                if validated["campaign_id"] not in self.active_campaigns:
                    self.logger.warning(f"Unknown campaign ID: {validated['campaign_id']}")
        
        return validated
    
    def _cleanup_resources(self):
        """Clean up campaign-specific resources"""
        # Stop all active campaigns
        for campaign_id in list(self.active_campaigns.keys()):
            self.stop_campaign(campaign_id)
        
        self.logger.info("All campaigns stopped and resources cleaned")


# For backward compatibility with existing code
class CampaignCEOAgent(CampaignCEO):
    """Alias for compatibility"""
    pass