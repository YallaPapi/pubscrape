#!/usr/bin/env python3
"""
VRSEN PubScrape - Main CLI Entry Point

Advanced multi-agent web scraping platform with modular CLI architecture.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli.app import main


if __name__ == "__main__":
    """Application entry point with graceful error handling"""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Application interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)