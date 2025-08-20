"""
Podcast Host Contact Scraper

100% free, open-source tool for discovering podcast host contact information.
Perfect for finding guests, building relationships, and growing your podcast network.
"""

__version__ = "1.0.0"
__author__ = "Podcast Host Scraper Contributors"
__license__ = "MIT"

from .base import BasePlatformScraper
from .main import PodcastHostScraper

__all__ = ["BasePlatformScraper", "PodcastHostScraper"]