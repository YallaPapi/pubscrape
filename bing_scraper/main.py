#!/usr/bin/env python3
"""
Bing Search Scraper - Main Entry Point
Production-ready lead generation system using Botasaurus.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.settings import get_settings

def main():
    """Main entry point for Bing scraper."""
    print("Bing Search Scraper v1.0")
    print("=" * 50)
    
    # Load configuration
    try:
        settings = get_settings()
        print(f"[OK] Configuration loaded successfully")
        print(f"Output directory: {settings.output_directory}")
        print(f"Max requests/minute: {settings.max_requests_per_minute}")
        print(f"Headless mode: {settings.headless_mode}")
        print(f"User agent rotation: {settings.user_agent_rotation}")
        
    except Exception as e:
        print(f"[ERROR] Configuration error: {e}")
        return 1
    
    # Test Botasaurus import
    try:
        from botasaurus.browser import browser
        print(f"[OK] Botasaurus imported successfully")
        
    except ImportError as e:
        print(f"[ERROR] Botasaurus import failed: {e}")
        print("Try: pip install botasaurus")
        return 1
    
    # Create output directories
    try:
        output_dir = Path(settings.output_directory)
        logs_dir = Path(settings.logs_directory)
        output_dir.mkdir(exist_ok=True)
        logs_dir.mkdir(exist_ok=True)
        print(f"[OK] Output directories created")
        
    except Exception as e:
        print(f"[ERROR] Directory creation failed: {e}")
        return 1
    
    print("\nEnvironment setup complete!")
    print("Ready for Bing scraping operations")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)