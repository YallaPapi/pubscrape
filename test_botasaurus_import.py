#!/usr/bin/env python3
"""Test correct botasaurus import"""

# Try different import methods
try:
    from botasaurus import *
    print("Import * worked")
    print("Available:", dir())
except Exception as e:
    print(f"Import * failed: {e}")

try:
    from botasaurus.browser import browser
    print("From botasaurus.browser import browser worked")
except Exception as e:
    print(f"botasaurus.browser failed: {e}")
    
try:
    import botasaurus
    print("Import botasaurus worked")
    print("Available in botasaurus:", dir(botasaurus))
except Exception as e:
    print(f"Import botasaurus failed: {e}")