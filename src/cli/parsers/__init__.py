"""
CLI Parsers Package

Contains argument parsing logic for the VRSEN PubScrape CLI.
Provides modular argument parsing with command delegation.
"""

from .argument_parser import create_parser

__all__ = ['create_parser']