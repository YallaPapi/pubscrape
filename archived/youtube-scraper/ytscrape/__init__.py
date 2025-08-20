"""
YouTuber Contact Discovery Agent
A fully automated pipeline for discovering and scoring potential podcast guests from YouTube.
"""

__version__ = "1.0.0"
__author__ = "YTScrape Team"

from .config import Config
from .channel_fetcher import ChannelFetcher
from .data_normalizer import DataNormalizer
from .guest_scorer import GuestScorer
from .email_drafter import EmailDrafter
from .csv_compiler import CSVCompiler
from .pipeline import Pipeline

__all__ = [
    "Config",
    "ChannelFetcher",
    "DataNormalizer",
    "GuestScorer",
    "EmailDrafter",
    "CSVCompiler",
    "Pipeline"
]