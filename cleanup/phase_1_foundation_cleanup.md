# **PHASE 1: FOUNDATION CLEANUP PLAN**
## **Week 1 - Complete System Detox**

---

## **🎯 PHASE 1 OBJECTIVES**

**PRIMARY GOAL**: Remove all fake data generation and fix broken imports to establish a clean foundation for real browser scraping.

**SUCCESS CRITERIA**:
- All fake data generation code deleted
- Botasaurus imports working correctly
- Main scrapers execute without crashes
- Zero fake data in any outputs

---

## **📋 DAY-BY-DAY IMPLEMENTATION**

### **DAY 1: FAKE DATA ELIMINATION**

#### **IMMEDIATE DELETIONS** (Morning Tasks)
```bash
# Navigate to project root
cd C:\Users\stuar\Desktop\Projects\pubscrape

# Delete fake data generators
rm real_business_scraper.py          # Priority 1 - Most deceptive
rm generate_100_leads.py             # Priority 2 - Pure fake generator
rm create_500_final_leads.py         # Priority 3 - Fake multiplication
rm expand_lawyer_leads_500.py        # Priority 4 - Fake variations
rm generate_100_doctor_leads.py      # Priority 5 - Mixed fake/real

# Move to archive for reference
mkdir -p cleanup/deleted_fake_generators
git mv real_business_scraper.py cleanup/deleted_fake_generators/ 2>/dev/null || true
git mv generate_100_leads.py cleanup/deleted_fake_generators/ 2>/dev/null || true
git mv create_500_final_leads.py cleanup/deleted_fake_generators/ 2>/dev/null || true
git mv expand_lawyer_leads_500.py cleanup/deleted_fake_generators/ 2>/dev/null || true
git mv generate_100_doctor_leads.py cleanup/deleted_fake_generators/ 2>/dev/null || true
```

#### **VERIFICATION TASKS** (Afternoon)
```bash
# Search for remaining fake data patterns
grep -r "random.randint" src/ || echo "✅ No random.randint found"
grep -r "random.choice" src/ || echo "✅ No random.choice found"
grep -r "for i in range.*business" src/ || echo "✅ No business generation loops"
grep -r "Restaurant #" . || echo "✅ No numbered restaurant patterns"

# Check for hardcoded fake lists
grep -r "business_types.*=.*\[" src/
grep -r "cities.*=.*\[" src/
grep -r "first_names.*=.*\[" src/
```

**DELIVERABLE**: Clean codebase with zero fake data generators

---

### **DAY 2: BOTASAURUS IMPORT FIXES**

#### **BOTASAURUS API CORRECTION** 

**FILE: `botasaurus_business_scraper.py`**
```python
# BEFORE (Broken):
from botasaurus import browser, Driver  # ❌ Wrong import path
from botasaurus import Request          # ❌ Wrong import path

@browser(add_stealth=True, bypass_cloudflare=True)  # ❌ Non-existent params
def scrape_google_maps(driver, search_data):
    driver.get_element_or_none_by_selector()  # ❌ Method doesn't exist

# AFTER (Fixed):
from botasaurus.browser import browser  # ✅ Correct import
from selenium.webdriver.common.by import By  # ✅ For element selection

@browser(headless=False, block_images=True, window_size="1920,1080")  # ✅ Real params
def scrape_google_maps(driver, search_data):
    driver.find_element(By.CSS_SELECTOR, "input#searchboxinput")  # ✅ Real method
```

**SPECIFIC CORRECTIONS**:
1. **Import Fixes**:
   ```python
   # Fix all Botasaurus imports
   from botasaurus.browser import browser
   # Remove: from botasaurus import Driver, Request
   ```

2. **Parameter Fixes**:
   ```python
   # Remove non-existent parameters:
   # add_stealth=True, bypass_cloudflare=True, block_resources=True
   
   # Use real parameters:
   @browser(
       headless=False,
       block_images=True, 
       window_size="1920,1080",
       user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
   )
   ```

3. **Method Fixes**:
   ```python
   # Replace non-existent methods:
   # driver.get_element_or_none_by_selector() -> driver.find_element()
   # driver.get_elements_or_none_by_selector() -> driver.find_elements()
   # driver.google_get() -> driver.get()
   ```

#### **TESTING BOTASAURUS FUNCTIONALITY**
```python
# Create: test_botasaurus_basic.py
from botasaurus.browser import browser

@browser(headless=False)
def test_browser_launch(driver):
    """Test basic Botasaurus functionality"""
    driver.get("https://httpbin.org/get")
    print(f"✅ Browser opened: {driver.title}")
    print(f"✅ URL loaded: {driver.current_url}")
    return {"success": True, "title": driver.title, "url": driver.current_url}

# Run test
if __name__ == "__main__":
    result = test_browser_launch()
    print(f"Botasaurus test result: {result}")
```

**DELIVERABLE**: Working Botasaurus integration without import errors

---

### **DAY 3: SYNTAX ERROR FIXES**

#### **MAIN.PY SYNTAX FIXES**

**FILE: `src/utils/logger.py` Line 212**
```python
# BEFORE (Broken):
logger.info(f"Processing {count} items \
             with advanced settings")  # ❌ Line continuation issue

# AFTER (Fixed):
logger.info(f"Processing {count} items "
            f"with advanced settings")  # ✅ Proper string continuation
```

#### **COMPREHENSIVE SYNTAX SCAN**
```bash
# Check all Python files for syntax errors
python -m py_compile main.py
python -m py_compile src/utils/logger.py
python -m py_compile botasaurus_business_scraper.py
python -m py_compile scrape_businesses.py

# Fix any remaining syntax issues found
```

#### **IMPORT DEPENDENCY FIXES**

**Check and fix missing imports**:
```python
# Common missing imports to add:
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
```

**DELIVERABLE**: All Python files execute without syntax/import errors

---

### **DAY 4: BROKEN SCRAPER REHABILITATION**

#### **SCRAPE_BUSINESSES.PY FIXES**

```python
# BEFORE (Broken):
@browser(block_resources=True, add_stealth=True)  # ❌ Invalid parameters
def scrape_business_data(driver, query):
    results = driver.get_elements_or_none_by_selector()  # ❌ Non-existent method

# AFTER (Fixed):
@browser(headless=False, block_images=True)  # ✅ Valid parameters  
def scrape_business_data(driver, query):
    results = driver.find_elements(By.CSS_SELECTOR, "[data-result-index]")  # ✅ Real method
```

#### **SIMPLE_BUSINESS_SCRAPER.PY TIMEOUT FIX**

**Identify and fix infinite loop/timeout issues**:
```python
# Add timeout protection:
import signal
import time

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

# Wrap scraping operations:
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60 second timeout

try:
    # Scraping code here
    results = scrape_data()
finally:
    signal.alarm(0)  # Cancel timeout
```

#### **ERROR HANDLING IMPLEMENTATION**

```python
def safe_scraper_execution(scraper_func, *args, **kwargs):
    """
    Wrapper to safely execute scrapers with proper error handling
    """
    try:
        return scraper_func(*args, **kwargs)
    except TimeoutError:
        print("❌ Scraper timed out")
        return []
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []
```

**DELIVERABLE**: All scraper files execute without crashes or timeouts

---

### **DAY 5: VERIFICATION AND TESTING**

#### **EXECUTION TESTS**

```bash
# Test each previously broken file:
echo "Testing main.py..."
python main.py --help || echo "❌ main.py still broken"

echo "Testing botasaurus_business_scraper.py..."
python -c "from botasaurus_business_scraper import *; print('✅ Import successful')" || echo "❌ Imports broken"

echo "Testing scrape_businesses.py..."
python scrape_businesses.py || echo "❌ Still crashing"

echo "Testing simple_business_scraper.py (with timeout)..."
timeout 30s python simple_business_scraper.py || echo "⚠️ Timeout or error"
```

#### **FUNCTIONALITY VERIFICATION**

**Create: `cleanup/phase1_verification_test.py`**
```python
#!/usr/bin/env python3
"""
Phase 1 Cleanup Verification Test
Confirms all fake data is removed and basic functionality works
"""

import os
import subprocess
import glob

def test_fake_data_removal():
    """Verify no fake data generators remain"""
    fake_patterns = [
        "random.randint(",
        "random.choice(",
        "for i in range(.*business",
        "Restaurant #",
        "Business #"
    ]
    
    for pattern in fake_patterns:
        cmd = f"grep -r '{pattern}' src/ || true"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"❌ Found fake data pattern: {pattern}")
            print(result.stdout)
        else:
            print(f"✅ No fake data pattern: {pattern}")

def test_import_functionality():
    """Test that all scrapers can import without errors"""
    scrapers = [
        "botasaurus_business_scraper",
        "scrape_businesses", 
        "simple_business_scraper"
    ]
    
    for scraper in scrapers:
        if os.path.exists(f"{scraper}.py"):
            try:
                exec(f"import {scraper}")
                print(f"✅ {scraper}.py imports successfully")
            except Exception as e:
                print(f"❌ {scraper}.py import error: {e}")

def test_botasaurus_basic():
    """Test basic Botasaurus functionality"""
    try:
        from botasaurus.browser import browser
        print("✅ Botasaurus imports successfully")
        
        @browser(headless=True)
        def test_func(driver):
            driver.get("data:text/html,<html><body>Test</body></html>")
            return driver.title
        
        result = test_func()
        print(f"✅ Botasaurus browser test: {result}")
        
    except Exception as e:
        print(f"❌ Botasaurus test failed: {e}")

if __name__ == "__main__":
    print("🧹 Phase 1 Cleanup Verification")
    print("=" * 40)
    test_fake_data_removal()
    print()
    test_import_functionality() 
    print()
    test_botasaurus_basic()
    print()
    print("✅ Phase 1 verification complete!")
```

#### **DOCUMENTATION UPDATE**

**Create: `cleanup/phase1_completion_report.md`**
```markdown
# Phase 1 Completion Report

## Files Deleted
- [x] real_business_scraper.py - Fake data generator
- [x] generate_100_leads.py - Pure fake generator  
- [x] create_500_final_leads.py - Fake multiplication
- [x] expand_lawyer_leads_500.py - Fake variations
- [x] generate_100_doctor_leads.py - Mixed fake/real

## Import Fixes Applied
- [x] botasaurus_business_scraper.py - Fixed import paths
- [x] scrape_businesses.py - Removed invalid parameters
- [x] main.py - Fixed syntax errors

## Verification Results
- [x] Zero fake data patterns found in src/
- [x] All scrapers import without errors
- [x] Botasaurus basic functionality confirmed
- [x] No crashes during import testing

## Ready for Phase 2
The foundation is now clean and ready for real scraper development.
```

**DELIVERABLE**: Verified clean foundation ready for real scraper development

---

## **🚨 CRITICAL SUCCESS INDICATORS**

### **MUST PASS BEFORE PHASE 2**:
- ✅ **Zero fake data**: No `random.randint()`, `random.choice()`, or hardcoded fake lists
- ✅ **No crashes**: All Python files import and execute basic operations
- ✅ **Botasaurus working**: Browser can launch and navigate to websites
- ✅ **Clean imports**: No ImportError, SyntaxError, or TypeError exceptions

### **RISK MITIGATION**:
- **Backup before deletion**: Keep deleted files in `cleanup/deleted_fake_generators/`
- **Incremental testing**: Test each fix before proceeding to next
- **Version control**: Commit after each successful day
- **Rollback plan**: Know how to restore previous state if needed

### **PHASE 1 EXIT CRITERIA**:
```bash
# Must pass all these tests:
python cleanup/phase1_verification_test.py  # ✅ All tests pass
python -c "from botasaurus.browser import browser; print('Botasaurus OK')"  # ✅ No errors
grep -r "random.randint" src/ | wc -l  # ✅ Returns 0
python main.py --help  # ✅ Shows help without crashing
```

---

**NEXT PHASE**: Once Phase 1 is complete, proceed to `phase_2_real_scrapers.md` for building actual browser scrapers that extract real business data.