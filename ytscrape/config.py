"""
Configuration module for YouTuber Contact Discovery Agent.
Loads all API keys and settings from environment variables only.
No hardcoded secrets allowed per Development Rule #3.
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Configuration class that loads all settings from environment variables."""
    
    def __init__(self):
        """Initialize configuration and validate required environment variables."""
        self.load_credentials()
        self.load_settings()
        self.validate_config()
    
    def load_credentials(self):
        """Load API credentials from environment variables."""
        # YouTube API
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
        
        # OpenAI API for AI scoring and email generation
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
        # Optional: Anthropic API as fallback
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        
        # Email finder API keys
        self.HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")  # Get free key at: https://hunter.io/users/sign_up
        self.APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")  # Get free key at: https://app.apollo.io
        
        # CSV output settings
        self.OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
        
    def load_settings(self):
        """Load application settings."""
        # YouTube API settings
        self.YOUTUBE_API_VERSION = "v3"
        self.YOUTUBE_API_SERVICE_NAME = "youtube"
        self.MAX_RESULTS_PER_SEARCH = int(os.getenv("MAX_RESULTS_PER_SEARCH", "50"))
        
        # AI model settings
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
        self.AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))
        
        # Error handling settings (20-cycle protocol)
        self.MAX_ERROR_CYCLES = int(os.getenv("MAX_ERROR_CYCLES", "20"))
        self.RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds
        
        # CSV Schema - enhanced with email field
        self.CSV_SCHEMA = [
            "ChannelName",
            "ChannelID", 
            "Email",  # Business email extracted
            "ChannelDescription",
            "Website",
            "SocialLinks",
            "SubscriberCount",
            "GuestScore",
            "ScoreReason",
            "DraftEmail"
        ]
        
        # Quota management
        self.YOUTUBE_DAILY_QUOTA = int(os.getenv("YOUTUBE_DAILY_QUOTA", "10000"))
        self.QUOTA_PER_SEARCH = 100  # search.list costs 100 units
        self.QUOTA_PER_CHANNEL = 1   # channels.list costs 1 unit
        
    def validate_config(self):
        """Validate that all required environment variables are set."""
        errors = []
        
        if not self.YOUTUBE_API_KEY:
            errors.append("YOUTUBE_API_KEY is not set")
        
        if not self.OPENAI_API_KEY and not self.ANTHROPIC_API_KEY:
            errors.append("Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be set")
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            print(f"\n[ERROR] {error_msg}\n")
            print("Please check your .env file and ensure all required API keys are set.")
            sys.exit(1)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        
        logger.info("Configuration loaded successfully")
        print("[OK] Configuration loaded successfully")
        
    def get_remaining_quota(self, used_quota: int) -> int:
        """Calculate remaining YouTube API quota."""
        return self.YOUTUBE_DAILY_QUOTA - used_quota
    
    def can_make_api_call(self, used_quota: int, required_units: int) -> bool:
        """Check if we have enough quota for an API call."""
        return (used_quota + required_units) <= self.YOUTUBE_DAILY_QUOTA


# Global config instance
config = Config()