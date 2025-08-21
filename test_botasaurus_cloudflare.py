#!/usr/bin/env python3
"""
Test Botasaurus Cloudflare bypass methods
Figure out what actually works
"""

from botasaurus.browser import browser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@browser(headless=False)
def test_cloudflare_methods(driver, data):
    """Test different Cloudflare bypass approaches."""
    
    # First, let's see what methods are available
    logger.info("Available driver methods:")
    methods = [m for m in dir(driver) if not m.startswith('_')]
    
    # Check for cloudflare-related methods
    cf_methods = [m for m in methods if 'cloudflare' in m.lower() or 'google' in m.lower() or 'bypass' in m.lower()]
    logger.info(f"Cloudflare-related methods: {cf_methods}")
    
    # Test 1: Try google_get if it exists
    if 'google_get' in methods:
        logger.info("\n✓ google_get method exists!")
        
        # Check the signature
        import inspect
        sig = inspect.signature(driver.google_get)
        logger.info(f"google_get signature: {sig}")
        
        # Try using it
        try:
            logger.info("Testing google_get with a protected site...")
            # Try TED speaker's external site
            driver.google_get("https://www.gsb.stanford.edu/faculty-research/faculty/jennifer-aaker")
            driver.sleep(3)
            
            # Check if we bypassed Cloudflare
            current_url = driver.current_url
            page_text = driver.page_html[:500]
            
            if "enable-javascript" in current_url:
                logger.info("❌ Still blocked by Cloudflare")
            else:
                logger.info(f"✓ Successfully loaded: {current_url}")
                
                # Try to find email
                import re
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', driver.page_html)
                if emails:
                    logger.info(f"✓ Found emails: {emails[:3]}")
                    
        except Exception as e:
            logger.error(f"google_get failed: {e}")
    else:
        logger.info("❌ google_get method not found")
    
    # Test 2: Check for detect_and_bypass_cloudflare
    if 'detect_and_bypass_cloudflare' in methods:
        logger.info("\n✓ detect_and_bypass_cloudflare exists!")
        
        # Try using it
        try:
            driver.get("https://www.gsb.stanford.edu/faculty-research/faculty/jennifer-aaker")
            result = driver.detect_and_bypass_cloudflare()
            logger.info(f"Bypass result: {result}")
        except Exception as e:
            logger.error(f"detect_and_bypass_cloudflare failed: {e}")
    
    # Test 3: Check is_bot_detected
    if 'is_bot_detected' in methods:
        logger.info(f"\nBot detected: {driver.is_bot_detected()}")
        
        if driver.is_bot_detected():
            logger.info("Trying to get bot detection reason...")
            if 'get_bot_detected_by' in methods:
                reason = driver.get_bot_detected_by()
                logger.info(f"Detection reason: {reason}")
    
    return {"methods_found": cf_methods}

if __name__ == "__main__":
    result = test_cloudflare_methods()
    print(f"\nResults: {result}")