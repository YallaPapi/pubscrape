"""
CLI Package for VRSEN PubScrape

Provides modular command-line interface components for the web scraping platform.
Includes command handlers, argument parsing, and application orchestration.
"""

from .app import CLIApplication

__all__ = ['CLIApplication']