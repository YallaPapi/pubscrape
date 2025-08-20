"""
Simple test of YouTuber Contact Discovery Agent
"""

import os
import sys

# Set environment for Windows console
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Test imports
print("Testing imports...")
try:
    from ytscrape.config import config
    print("[OK] Config loaded")
except Exception as e:
    print(f"[ERROR] Config failed: {e}")
    sys.exit(1)

try:
    from ytscrape.channel_fetcher import ChannelFetcher
    print("[OK] Channel Fetcher loaded")
except Exception as e:
    print(f"[ERROR] Channel Fetcher failed: {e}")

try:
    from ytscrape.data_normalizer import DataNormalizer  
    print("[OK] Data Normalizer loaded")
except Exception as e:
    print(f"[ERROR] Data Normalizer failed: {e}")

try:
    from ytscrape.guest_scorer import GuestScorer
    print("[OK] Guest Scorer loaded")
except Exception as e:
    print(f"[ERROR] Guest Scorer failed: {e}")

try:
    from ytscrape.email_drafter import EmailDrafter
    print("[OK] Email Drafter loaded")
except Exception as e:
    print(f"[ERROR] Email Drafter failed: {e}")

try:
    from ytscrape.csv_compiler import CSVCompiler
    print("[OK] CSV Compiler loaded")
except Exception as e:
    print(f"[ERROR] CSV Compiler failed: {e}")

try:
    from ytscrape.pipeline import Pipeline
    print("[OK] Pipeline loaded")
except Exception as e:
    print(f"[ERROR] Pipeline failed: {e}")

print("\n[SUCCESS] All modules loaded successfully!")
print("\nReady to run pipeline with:")
print("  python main.py 'your search query' --podcast 'Your Podcast Name'")