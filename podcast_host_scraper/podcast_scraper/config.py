"""
Configuration settings for the podcast scraper.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for podcast scraper."""
    
    # API Keys (optional)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID") 
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    GOOGLE_CUSTOM_SEARCH_KEY = os.getenv("GOOGLE_CUSTOM_SEARCH_KEY")
    GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    # Scraping Configuration
    MAX_PODCASTS_PER_SEARCH = int(os.getenv("MAX_PODCASTS_PER_SEARCH", "100"))
    SCRAPING_DELAY_SECONDS = int(os.getenv("SCRAPING_DELAY_SECONDS", "1"))
    USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    # Output Configuration
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    CSV_FILENAME = os.getenv("CSV_FILENAME", "podcast_contacts.csv")
    REPORT_FILENAME = os.getenv("REPORT_FILENAME", "podcast_report.md")
    
    # CSV Schema for output
    CSV_COLUMNS = [
        "podcast_name",
        "host_name", 
        "host_email",
        "booking_email",
        "podcast_website",
        "contact_page_url",
        "social_links",
        "estimated_downloads",
        "episode_count",
        "rating",
        "ai_relevance_score",
        "contact_confidence",
        "platform_source",
        "apple_podcasts_url",
        "rss_feed_url",
        "last_updated"
    ]
    
    # Enhanced CSV Schema with intelligence and enrichment data
    ENHANCED_CSV_COLUMNS = [
        # Basic Information
        "podcast_name",
        "host_name",
        "podcast_description",
        
        # Contact Information
        "host_email",
        "booking_email", 
        "alternative_emails",
        "podcast_website",
        "contact_page_url",
        "contact_forms_available",
        
        # Social Media
        "social_links",
        "social_influence_score",
        "social_platforms_count",
        
        # Intelligence Metrics
        "overall_intelligence_score",
        "relevance_score",
        "popularity_score",
        "authority_score",
        "content_quality_score",
        "guest_potential_score",
        
        # Contact Quality
        "contact_quality_score",
        "response_likelihood",
        "best_contact_method",
        "contact_strategy",
        "contact_confidence",
        
        # Podcast Metrics
        "estimated_downloads",
        "audience_size_category",
        "episode_count",
        "rating",
        "host_authority_level",
        
        # Platform Information
        "platform_source",
        "apple_podcasts_url",
        "spotify_url",
        "youtube_url",
        "rss_feed_url",
        
        # Metadata
        "ai_relevance_score",
        "content_format_type",
        "interview_style",
        "recommendations",
        "risk_factors",
        "last_updated"
    ]
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Platform-specific settings
    APPLE_PODCASTS_SETTINGS = {
        "base_url": "https://podcasts.apple.com",
        "chart_url_template": "https://podcasts.apple.com/us/genre/podcasts-{category}/id1310",
        "rate_limit_delay": 2,  # seconds between requests
        "max_retries": 3
    }
    
    SPOTIFY_SETTINGS = {
        "base_url": "https://api.spotify.com/v1",
        "auth_url": "https://accounts.spotify.com/api/token",
        "rate_limit_delay": 1,
        "max_retries": 3
    }
    
    # Contact extraction settings
    CONTACT_EXTRACTION_SETTINGS = {
        "email_patterns": [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
        ],
        "contact_page_paths": [
            "/contact", 
            "/about",
            "/booking",
            "/business",
            "/collaborate",
            "/sponsor",
            "/advertising",
            "/guest"
        ],
        "social_media_domains": [
            "twitter.com",
            "instagram.com", 
            "facebook.com",
            "linkedin.com",
            "youtube.com",
            "tiktok.com"
        ]
    }
    
    # AI scoring settings
    AI_SETTINGS = {
        "openai_model": "gpt-3.5-turbo",
        "max_tokens": 150,
        "temperature": 0.3,
        "ai_topics": [
            "artificial intelligence",
            "machine learning", 
            "AI tools",
            "automation",
            "technology",
            "productivity",
            "business tools",
            "software"
        ]
    }
    
    @classmethod
    def get_output_path(cls, filename: str = None) -> str:
        """
        Get full output file path.
        
        Args:
            filename: Optional filename override
            
        Returns:
            Full path to output file
        """
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        filename = filename or cls.CSV_FILENAME
        return os.path.join(cls.OUTPUT_DIR, filename)
    
    @classmethod
    def has_openai_key(cls) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(cls.OPENAI_API_KEY and len(cls.OPENAI_API_KEY) > 10)
    
    @classmethod
    def has_spotify_keys(cls) -> bool:
        """Check if Spotify API keys are configured."""
        return bool(
            cls.SPOTIFY_CLIENT_ID and 
            cls.SPOTIFY_CLIENT_SECRET and
            len(cls.SPOTIFY_CLIENT_ID) > 10
        )
    
    @classmethod
    def has_google_search_keys(cls) -> bool:
        """Check if Google Custom Search keys are configured.""" 
        return bool(
            cls.GOOGLE_CUSTOM_SEARCH_KEY and
            cls.GOOGLE_SEARCH_ENGINE_ID and
            len(cls.GOOGLE_CUSTOM_SEARCH_KEY) > 10
        )
    
    @classmethod
    def get_available_features(cls) -> Dict[str, bool]:
        """
        Get dict of available features based on API keys.
        
        Returns:
            Dict mapping feature names to availability
        """
        return {
            "apple_podcasts": True,  # Always available (no API key needed)
            "ai_scoring": cls.has_openai_key(),
            "spotify_discovery": cls.has_spotify_keys(),
            "google_search": cls.has_google_search_keys(),
            "contact_extraction": True,  # Always available
            "csv_export": True,  # Always available
        }


# Global config instance
config = Config()