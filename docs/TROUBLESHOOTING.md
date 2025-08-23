# Troubleshooting Guide - PubScrape Infinite Scroll Scraper System

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Browser and Driver Issues](#browser-and-driver-issues)
4. [Rate Limiting and Blocking](#rate-limiting-and-blocking)
5. [Data Extraction Problems](#data-extraction-problems)
6. [Configuration Issues](#configuration-issues)
7. [Performance Problems](#performance-problems)
8. [Docker and Deployment Issues](#docker-and-deployment-issues)
9. [API and Authentication Issues](#api-and-authentication-issues)
10. [Debugging Tools and Techniques](#debugging-tools-and-techniques)

## Common Issues

### Issue: "No module named 'botasaurus'" Error

**Symptoms:**
```bash
ImportError: No module named 'botasaurus'
```

**Solutions:**
1. **Install Botasaurus:**
   ```bash
   pip install botasaurus
   ```

2. **Verify Installation:**
   ```bash
   python -c "import botasaurus; print('✅ Botasaurus installed successfully')"
   ```

3. **Check Virtual Environment:**
   ```bash
   # Ensure you're in the correct virtual environment
   which python
   pip list | grep botasaurus
   ```

4. **Reinstall if Corrupted:**
   ```bash
   pip uninstall botasaurus
   pip install botasaurus>=4.0.0
   ```

### Issue: Chrome Browser Not Found

**Symptoms:**
```bash
WebDriverException: 'chromedriver' executable needs to be in PATH
selenium.common.exceptions.WebDriverException: Message: unknown error: cannot find Chrome binary
```

**Solutions:**
1. **Install Chrome/Chromium:**
   ```bash
   # Ubuntu/Debian
   wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
   sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
   sudo apt-get update
   sudo apt-get install google-chrome-stable
   
   # CentOS/RHEL
   sudo yum install -y chromium
   
   # macOS
   brew install --cask google-chrome
   
   # Windows
   # Download and install from https://www.google.com/chrome/
   ```

2. **Set Chrome Path in Environment:**
   ```bash
   export CHROME_BIN=/usr/bin/google-chrome
   # Or for Chromium
   export CHROME_BIN=/usr/bin/chromium-browser
   ```

3. **Configure Chrome Path in Code:**
   ```python
   from src.infra.browser_manager import BrowserConfig, BrowserMode
   
   config = BrowserConfig(
       mode=BrowserMode.HEADLESS,
       chrome_binary_path="/usr/bin/google-chrome"
   )
   ```

### Issue: Permission Denied Errors

**Symptoms:**
```bash
PermissionError: [Errno 13] Permission denied: '/app/output'
```

**Solutions:**
1. **Fix Directory Permissions:**
   ```bash
   # Create directories with correct permissions
   mkdir -p output logs cache temp
   chmod 755 output logs cache temp
   
   # Fix ownership if needed
   sudo chown -R $USER:$USER output logs cache temp
   ```

2. **Docker Permission Fix:**
   ```bash
   # In Dockerfile, add:
   RUN mkdir -p output logs cache temp && \
       chmod 755 output logs cache temp
   
   # Or run container with user mapping
   docker run --user $(id -u):$(id -g) -v $(pwd)/output:/app/output pubscrape
   ```

## Installation Problems

### Issue: Pip Installation Failures

**Symptoms:**
```bash
ERROR: Could not build wheels for some-package
error: Microsoft Visual C++ 14.0 is required
```

**Solutions:**
1. **Install Build Tools (Windows):**
   ```bash
   # Install Visual C++ Build Tools
   # Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   ```

2. **Use Pre-compiled Wheels:**
   ```bash
   pip install --only-binary=all package-name
   ```

3. **Update pip and setuptools:**
   ```bash
   python -m pip install --upgrade pip setuptools wheel
   ```

4. **Alternative Installation Methods:**
   ```bash
   # Try conda instead of pip
   conda install package-name
   
   # Or use system package manager
   sudo apt-get install python3-package-name
   ```

### Issue: Python Version Compatibility

**Symptoms:**
```bash
SyntaxError: invalid syntax (python 3.7 features in python 3.6)
```

**Solutions:**
1. **Check Python Version:**
   ```bash
   python --version
   python3 --version
   ```

2. **Install Correct Python Version:**
   ```bash
   # Using pyenv
   pyenv install 3.11.0
   pyenv local 3.11.0
   
   # Using conda
   conda create -n pubscrape python=3.11
   conda activate pubscrape
   ```

3. **Use Compatible Dependencies:**
   ```bash
   # Install version-specific requirements
   pip install -r requirements-py38.txt  # For Python 3.8
   pip install -r requirements-py311.txt # For Python 3.11
   ```

## Browser and Driver Issues

### Issue: Browser Crashes or Timeouts

**Symptoms:**
```bash
selenium.common.exceptions.TimeoutException
Browser process crashed
```

**Solutions:**
1. **Increase Memory Allocation:**
   ```python
   from src.infra.browser_manager import BrowserConfig
   
   config = BrowserConfig(
       timeout=60,  # Increase timeout
       max_retries=5,  # More retries
       chrome_options=[
           '--no-sandbox',
           '--disable-dev-shm-usage',
           '--disable-gpu',
           '--memory-pressure-off',
           '--max_old_space_size=4096'
       ]
   )
   ```

2. **Monitor Memory Usage:**
   ```python
   import psutil
   
   def monitor_memory():
       process = psutil.Process()
       memory_mb = process.memory_info().rss / 1024 / 1024
       print(f"Memory usage: {memory_mb:.1f} MB")
       
       if memory_mb > 2048:  # 2GB limit
           print("⚠️  High memory usage detected")
           return False
       return True
   
   # Use in your scraping loop
   if not monitor_memory():
       # Cleanup and restart browser session
       browser_manager.close_all_sessions()
   ```

3. **Use Browser Session Rotation:**
   ```python
   class RotatingBrowserManager:
       def __init__(self, max_requests_per_session=50):
           self.max_requests = max_requests_per_session
           self.request_count = 0
           self.browser_manager = None
           self.session_id = None
       
       def get_session(self):
           if (self.request_count >= self.max_requests or 
               self.browser_manager is None):
               self.restart_session()
           
           self.request_count += 1
           return self.browser_manager.get_browser_session(self.session_id)
       
       def restart_session(self):
           if self.browser_manager:
               self.browser_manager.close_all_sessions()
           
           self.browser_manager = create_browser_manager()
           self.session_id = f"session_{int(time.time())}"
           self.request_count = 0
           print(f"🔄 Restarted browser session: {self.session_id}")
   ```

### Issue: Browser Detection and Blocking

**Symptoms:**
```bash
Access denied
Captcha challenge
Your request looks automated
```

**Solutions:**
1. **Enhanced Anti-Detection:**
   ```python
   from src.infra.anti_detection_supervisor import AntiDetectionSupervisor
   
   config = {
       "user_agents": {
           "rotation_enabled": True,
           "prefer_chrome": True,
           "desktop_only": True
       },
       "delays": {
           "base_delay": 3.0,
           "random_factor": 1.0,
           "human_like_patterns": True
       },
       "proxies": {
           "enabled": True,
           "rotation_interval": 10
       }
   }
   
   supervisor = AntiDetectionSupervisor(config)
   ```

2. **Implement Captcha Handling:**
   ```python
   def handle_captcha_detection(driver):
       try:
           # Check for common captcha indicators
           captcha_selectors = [
               'div[class*="captcha"]',
               'iframe[src*="recaptcha"]',
               'div[class*="challenge"]'
           ]
           
           for selector in captcha_selectors:
               if driver.find_elements(By.CSS_SELECTOR, selector):
                   print("🤖 Captcha detected, implementing countermeasures...")
                   
                   # Strategy 1: Wait and retry
                   time.sleep(30)
                   driver.refresh()
                   time.sleep(5)
                   
                   # Strategy 2: Switch session/proxy
                   return "CAPTCHA_DETECTED"
           
           return "NO_CAPTCHA"
           
       except Exception as e:
           print(f"Error checking for captcha: {e}")
           return "ERROR"
   ```

3. **Use Residential Proxies:**
   ```python
   # Configure rotating residential proxies
   proxy_list = [
       "residential1.proxy.com:8080",
       "residential2.proxy.com:8080",
       "residential3.proxy.com:8080"
   ]
   
   def get_rotating_proxy():
       return random.choice(proxy_list)
   
   # Use in browser configuration
   config = BrowserConfig(
       proxy=get_rotating_proxy(),
       user_agent=get_random_user_agent()
   )
   ```

## Rate Limiting and Blocking

### Issue: 429 Too Many Requests

**Symptoms:**
```bash
HTTP 429: Too Many Requests
Rate limit exceeded
```

**Solutions:**
1. **Implement Exponential Backoff:**
   ```python
   import time
   import random
   
   class ExponentialBackoff:
       def __init__(self, base_delay=1, max_delay=300, factor=2):
           self.base_delay = base_delay
           self.max_delay = max_delay
           self.factor = factor
           self.attempt = 0
       
       def wait(self):
           delay = min(
               self.base_delay * (self.factor ** self.attempt),
               self.max_delay
           )
           jitter = random.uniform(0.1, 0.3) * delay
           total_delay = delay + jitter
           
           print(f"⏳ Waiting {total_delay:.1f}s before retry (attempt {self.attempt + 1})")
           time.sleep(total_delay)
           self.attempt += 1
       
       def reset(self):
           self.attempt = 0
   
   # Usage
   backoff = ExponentialBackoff()
   
   for attempt in range(5):
       try:
           response = make_request()
           backoff.reset()
           break
       except RateLimitError:
           if attempt == 4:
               raise
           backoff.wait()
   ```

2. **Smart Rate Limiting:**
   ```python
   class SmartRateLimiter:
       def __init__(self, rpm=12):
           self.rpm = rpm
           self.requests = []
           self.blocked_until = None
       
       def can_make_request(self):
           now = time.time()
           
           # Check if we're in a blocked state
           if self.blocked_until and now < self.blocked_until:
               return False
           
           # Clean old requests
           minute_ago = now - 60
           self.requests = [t for t in self.requests if t > minute_ago]
           
           return len(self.requests) < self.rpm
       
       def record_request(self, success=True, retry_after=None):
           now = time.time()
           
           if success:
               self.requests.append(now)
               self.blocked_until = None
           else:
               # Handle rate limit response
               if retry_after:
                   self.blocked_until = now + retry_after
               else:
                   # Default backoff
                   self.blocked_until = now + 60
               
               print(f"⚠️  Rate limited until {time.ctime(self.blocked_until)}")
       
       def wait_if_needed(self):
           while not self.can_make_request():
               wait_time = max(1, (self.blocked_until or time.time()) - time.time() + 1)
               print(f"⏳ Rate limit active, waiting {wait_time:.1f}s...")
               time.sleep(min(wait_time, 10))
   ```

3. **Adaptive Rate Limiting:**
   ```python
   class AdaptiveRateLimiter:
       def __init__(self, initial_rpm=12):
           self.base_rpm = initial_rpm
           self.current_rpm = initial_rpm
           self.success_streak = 0
           self.failure_streak = 0
       
       def adjust_rate_limit(self, success):
           if success:
               self.success_streak += 1
               self.failure_streak = 0
               
               # Gradually increase rate if successful
               if self.success_streak >= 10:
                   self.current_rpm = min(self.current_rpm * 1.1, self.base_rpm * 2)
                   self.success_streak = 0
                   print(f"📈 Increased rate limit to {self.current_rpm:.1f} RPM")
           else:
               self.failure_streak += 1
               self.success_streak = 0
               
               # Decrease rate immediately on failure
               self.current_rpm = max(self.current_rpm * 0.5, self.base_rpm * 0.25)
               print(f"📉 Decreased rate limit to {self.current_rpm:.1f} RPM")
       
       def get_delay(self):
           return 60 / self.current_rpm if self.current_rpm > 0 else 5
   ```

## Data Extraction Problems

### Issue: No Data Extracted

**Symptoms:**
```bash
Empty results returned
extraction_successful: False
No emails/phones found
```

**Solutions:**
1. **Debug HTML Structure:**
   ```python
   def debug_page_content(driver, url):
       print(f"🔍 Debugging page: {url}")
       
       # Get page source and save for inspection
       html = driver.page_source
       with open(f'debug_page_{int(time.time())}.html', 'w', encoding='utf-8') as f:
           f.write(html)
       
       # Check if page loaded properly
       if len(html) < 1000:
           print("⚠️  Page content seems too short, possible redirect or error")
       
       # Look for common indicators
       indicators = {
           'contact': ['contact', 'about', 'staff', 'team'],
           'email': ['@', 'email', 'mail'],
           'phone': ['phone', 'tel:', 'call'],
           'errors': ['404', 'not found', 'error', 'blocked']
       }
       
       for category, keywords in indicators.items():
           count = sum(html.lower().count(keyword) for keyword in keywords)
           print(f"  {category.title()} indicators: {count}")
       
       # Check for JavaScript-heavy content
       script_tags = driver.find_elements(By.TAG_NAME, 'script')
       print(f"  JavaScript tags: {len(script_tags)}")
       
       if len(script_tags) > 10:
           print("  ⚠️  Page appears to be JavaScript-heavy, may need dynamic loading")
   ```

2. **Enhanced Data Extraction:**
   ```python
   def enhanced_contact_extraction(driver, url):
       try:
           driver.get(url)
           time.sleep(3)
           
           # Wait for dynamic content
           from selenium.webdriver.support.ui import WebDriverWait
           from selenium.webdriver.support import expected_conditions as EC
           
           try:
               WebDriverWait(driver, 10).until(
                   EC.presence_of_element_located((By.TAG_NAME, "body"))
               )
           except:
               print("⚠️  Page did not load properly")
           
           # Multiple extraction strategies
           strategies = [
               extract_from_text_content,
               extract_from_structured_data,
               extract_from_contact_page,
               extract_from_footer
           ]
           
           results = {}
           for strategy in strategies:
               try:
                   strategy_results = strategy(driver)
                   for key, value in strategy_results.items():
                       if value and key not in results:
                           results[key] = value
               except Exception as e:
                   print(f"Strategy failed: {strategy.__name__}: {e}")
           
           return results
           
       except Exception as e:
           print(f"❌ Extraction failed for {url}: {e}")
           return {}
   
   def extract_from_contact_page(driver):
       """Try to find and navigate to contact page"""
       contact_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Contact")
       if not contact_links:
           contact_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "About")
       
       if contact_links:
           original_url = driver.current_url
           try:
               contact_links[0].click()
               time.sleep(2)
               
               # Extract from contact page
               results = extract_from_text_content(driver)
               
               # Go back to original page
               driver.get(original_url)
               return results
           except:
               driver.get(original_url)
       
       return {}
   ```

3. **Pattern-Based Extraction:**
   ```python
   import re
   
   def extract_with_multiple_patterns(text):
       """Use multiple regex patterns for robust extraction"""
       
       # Email patterns
       email_patterns = [
           r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
           r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\s*\.\s*[a-zA-Z]{2,}',
           r'[a-zA-Z0-9._%+-]+\s*\[\s*at\s*\]\s*[a-zA-Z0-9.-]+\s*\[\s*dot\s*\]\s*[a-zA-Z]{2,}'
       ]
       
       # Phone patterns
       phone_patterns = [
           r'\(\d{3}\)\s*\d{3}[-.\s]*\d{4}',
           r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
           r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
           r'(?:phone|tel|call):?\s*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
       ]
       
       emails = set()
       phones = set()
       
       # Extract emails
       for pattern in email_patterns:
           matches = re.findall(pattern, text, re.IGNORECASE)
           emails.update(matches)
       
       # Extract phones
       for pattern in phone_patterns:
           matches = re.findall(pattern, text, re.IGNORECASE)
           if isinstance(matches[0], tuple) if matches else False:
               phones.update([''.join(match) for match in matches])
           else:
               phones.update(matches)
       
       # Clean and validate
       valid_emails = [email for email in emails if validate_email_format(email)]
       valid_phones = [phone for phone in phones if validate_phone_format(phone)]
       
       return {
           'emails': list(valid_emails),
           'phones': list(valid_phones)
       }
   
   def validate_email_format(email):
       """Basic email validation"""
       pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
       return bool(re.match(pattern, email)) and len(email) <= 254
   
   def validate_phone_format(phone):
       """Basic phone validation"""
       digits = re.sub(r'[^\d]', '', phone)
       return 10 <= len(digits) <= 15
   ```

### Issue: Incorrect or Low-Quality Data

**Symptoms:**
```bash
Invalid email addresses
Malformed phone numbers
Wrong business information
```

**Solutions:**
1. **Data Quality Validation:**
   ```python
   from email_validator import validate_email, EmailNotValidError
   import phonenumbers
   
   class DataQualityValidator:
       def __init__(self):
           self.email_domains_cache = {}
           self.disposable_domains = {
               '10minutemail.com', 'tempmail.org', 'guerrillamail.com'
           }
       
       def validate_email_quality(self, email):
           """Comprehensive email validation"""
           try:
               # Basic format validation
               validated = validate_email(email)
               normalized_email = validated.email
               domain = validated.domain
               
               # Check for disposable domains
               if domain in self.disposable_domains:
                   return {
                       'is_valid': False,
                       'reason': 'disposable_domain',
                       'email': email
                   }
               
               # Check domain validity (DNS lookup)
               if domain not in self.email_domains_cache:
                   try:
                       import dns.resolver
                       dns.resolver.resolve(domain, 'MX')
                       self.email_domains_cache[domain] = True
                   except:
                       self.email_domains_cache[domain] = False
               
               domain_valid = self.email_domains_cache[domain]
               
               return {
                   'is_valid': domain_valid,
                   'normalized': normalized_email,
                   'domain': domain,
                   'reason': 'valid' if domain_valid else 'invalid_domain'
               }
               
           except EmailNotValidError as e:
               return {
                   'is_valid': False,
                   'reason': str(e),
                   'email': email
               }
       
       def validate_phone_quality(self, phone, country='US'):
           """Comprehensive phone validation"""
           try:
               parsed = phonenumbers.parse(phone, country)
               
               return {
                   'is_valid': phonenumbers.is_valid_number(parsed),
                   'is_possible': phonenumbers.is_possible_number(parsed),
                   'formatted': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
                   'international': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                   'type': phonenumbers.number_type(parsed),
                   'carrier': phonenumbers.carrier.name_for_number(parsed, 'en')
               }
           except:
               return {'is_valid': False, 'reason': 'parsing_failed'}
       
       def score_lead_quality(self, lead):
           """Calculate overall quality score"""
           score = 0
           max_score = 100
           
           # Business name quality (20 points)
           if lead.get('business_name'):
               name = lead['business_name'].strip()
               if len(name) > 3 and not any(char.isdigit() for char in name):
                   score += 20
               elif len(name) > 1:
                   score += 10
           
           # Email quality (30 points)
           if lead.get('emails'):
               for email in lead['emails'][:2]:  # Check first 2 emails
                   email_result = self.validate_email_quality(email)
                   if email_result['is_valid']:
                       score += 15
           
           # Phone quality (25 points)
           if lead.get('phones'):
               for phone in lead['phones'][:2]:  # Check first 2 phones
                   phone_result = self.validate_phone_quality(phone)
                   if phone_result['is_valid']:
                       score += 12.5
           
           # Website quality (15 points)
           if lead.get('website'):
               url = lead['website']
               if url.startswith('http') and len(url) > 10:
                   score += 15
           
           # Address quality (10 points)
           if lead.get('address'):
               address = lead['address'].strip()
               if len(address) > 10 and any(char.isdigit() for char in address):
                   score += 10
           
           return {
               'score': score,
               'grade': self._score_to_grade(score),
               'is_high_quality': score >= 70
           }
       
       def _score_to_grade(self, score):
           if score >= 90: return 'A+'
           elif score >= 80: return 'A'
           elif score >= 70: return 'B'
           elif score >= 60: return 'C'
           elif score >= 50: return 'D'
           else: return 'F'
   ```

## Configuration Issues

### Issue: Configuration Not Loading

**Symptoms:**
```bash
Configuration file not found
Invalid YAML syntax
Environment variables not recognized
```

**Solutions:**
1. **Debug Configuration Loading:**
   ```python
   from src.core.config_manager import ConfigManager
   import os
   
   def debug_configuration():
       print("🔧 Configuration Debug Info:")
       
       # Check environment variables
       important_vars = [
           'OPENAI_API_KEY', 'MAX_PAGES_PER_QUERY', 'RATE_LIMIT_RPM',
           'DEBUG_MODE', 'LOG_LEVEL'
       ]
       
       for var in important_vars:
           value = os.getenv(var)
           if value:
               # Mask API keys
               if 'key' in var.lower() or 'token' in var.lower():
                   value = value[:8] + '...' if len(value) > 8 else '***'
               print(f"  ✅ {var}={value}")
           else:
               print(f"  ❌ {var} not set")
       
       # Check configuration files
       config_files = [
           'config.yaml', 'config.json', 'configs/config.yaml', 
           'configs/config.json', '.env'
       ]
       
       for config_file in config_files:
           if os.path.exists(config_file):
               print(f"  ✅ Found: {config_file}")
               try:
                   with open(config_file, 'r') as f:
                       content = f.read()
                   print(f"     Size: {len(content)} bytes")
               except Exception as e:
                   print(f"     ❌ Error reading: {e}")
           else:
               print(f"  ❌ Missing: {config_file}")
       
       # Test configuration loading
       try:
           config = ConfigManager()
           is_valid, errors = config.validate()
           
           if is_valid:
               print("  ✅ Configuration is valid")
           else:
               print("  ❌ Configuration errors:")
               for error in errors:
                   print(f"     - {error}")
       
       except Exception as e:
           print(f"  ❌ Configuration loading failed: {e}")
   
   # Run debug
   debug_configuration()
   ```

2. **Fix YAML Syntax Issues:**
   ```python
   import yaml
   
   def validate_yaml_file(filepath):
       """Validate YAML syntax and structure"""
       try:
           with open(filepath, 'r') as f:
               data = yaml.safe_load(f)
           
           print(f"✅ {filepath} is valid YAML")
           
           # Check required sections
           required_sections = ['api', 'search', 'processing', 'export']
           missing_sections = [section for section in required_sections 
                             if section not in data]
           
           if missing_sections:
               print(f"⚠️  Missing sections: {missing_sections}")
           else:
               print("✅ All required sections present")
           
           return True, data
           
       except yaml.YAMLError as e:
           print(f"❌ YAML syntax error in {filepath}:")
           print(f"   {e}")
           return False, None
       except FileNotFoundError:
           print(f"❌ File not found: {filepath}")
           return False, None
   
   # Validate configuration files
   for config_file in ['config.yaml', 'configs/config.yaml']:
       if os.path.exists(config_file):
           validate_yaml_file(config_file)
   ```

3. **Environment Variable Troubleshooting:**
   ```bash
   # Check if variables are set
   echo $OPENAI_API_KEY
   printenv | grep OPENAI
   
   # Load .env file manually
   set -a
   source .env
   set +a
   
   # Verify variables are available
   python -c "import os; print('API Key:', bool(os.getenv('OPENAI_API_KEY')))"
   ```

## Performance Problems

### Issue: Slow Extraction Speed

**Symptoms:**
```bash
Very slow processing
High CPU/memory usage
Timeouts during extraction
```

**Solutions:**
1. **Performance Profiling:**
   ```python
   import cProfile
   import pstats
   import time
   from functools import wraps
   
   def profile_function(func):
       @wraps(func)
       def wrapper(*args, **kwargs):
           pr = cProfile.Profile()
           pr.enable()
           
           start_time = time.time()
           result = func(*args, **kwargs)
           end_time = time.time()
           
           pr.disable()
           
           # Save profile stats
           stats = pstats.Stats(pr)
           stats.sort_stats('cumulative')
           stats.print_stats(20)  # Top 20 functions
           
           print(f"⏱️  {func.__name__} took {end_time - start_time:.2f}s")
           return result
       
       return wrapper
   
   # Use on slow functions
   @profile_function
   def extract_doctor_contact_info(url):
       # Your extraction code here
       pass
   ```

2. **Memory Optimization:**
   ```python
   import gc
   import psutil
   
   class MemoryOptimizer:
       def __init__(self, max_memory_mb=2048):
           self.max_memory_mb = max_memory_mb
           self.cleanup_threshold = max_memory_mb * 0.8
       
       def get_memory_usage(self):
           process = psutil.Process()
           return process.memory_info().rss / 1024 / 1024
       
       def cleanup_if_needed(self):
           current_memory = self.get_memory_usage()
           
           if current_memory > self.cleanup_threshold:
               print(f"🧹 Memory usage: {current_memory:.1f}MB, cleaning up...")
               
               # Force garbage collection
               gc.collect()
               
               # Check improvement
               new_memory = self.get_memory_usage()
               freed = current_memory - new_memory
               print(f"   Freed {freed:.1f}MB, new usage: {new_memory:.1f}MB")
               
               return freed > 50  # Return True if significant cleanup
           
           return False
       
       def monitor_continuously(self, callback=None):
           """Monitor memory usage continuously"""
           while True:
               usage = self.get_memory_usage()
               
               if usage > self.max_memory_mb:
                   print(f"⚠️  Memory limit exceeded: {usage:.1f}MB")
                   if callback:
                       callback()
                   break
               
               time.sleep(30)  # Check every 30 seconds
   ```

3. **Parallel Processing:**
   ```python
   from concurrent.futures import ThreadPoolExecutor, as_completed
   import queue
   
   class ParallelExtractor:
       def __init__(self, max_workers=4):
           self.max_workers = max_workers
           self.results_queue = queue.Queue()
       
       def extract_batch(self, urls):
           """Extract data from multiple URLs in parallel"""
           results = []
           
           with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
               # Submit all tasks
               future_to_url = {
                   executor.submit(self.safe_extract, url): url 
                   for url in urls
               }
               
               # Collect results as they complete
               for future in as_completed(future_to_url):
                   url = future_to_url[future]
                   try:
                       result = future.result(timeout=60)
                       if result['extraction_successful']:
                           results.append(result)
                           print(f"✅ Extracted: {url}")
                       else:
                           print(f"❌ Failed: {url}")
                   except Exception as e:
                       print(f"❌ Error extracting {url}: {e}")
           
           return results
       
       def safe_extract(self, url):
           """Thread-safe extraction with error handling"""
           try:
               # Create separate browser session for each thread
               browser_manager = create_browser_manager()
               driver = browser_manager.get_browser_session(
                   f"thread_{threading.current_thread().ident}",
                   domain=urlparse(url).netloc
               )
               
               result = extract_doctor_contact_info_with_driver(driver, url)
               
               # Cleanup
               browser_manager.close_all_sessions()
               
               return result
               
           except Exception as e:
               return {
                   'url': url,
                   'extraction_successful': False,
                   'error': str(e)
               }
   ```

## Docker and Deployment Issues

### Issue: Docker Build Failures

**Symptoms:**
```bash
Docker build failed
Package installation errors in container
Permission denied in Docker
```

**Solutions:**
1. **Fix Dockerfile Issues:**
   ```dockerfile
   FROM python:3.11-slim
   
   # Fix timezone issues
   ENV TZ=UTC
   RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
   
   # Install system dependencies with error handling
   RUN apt-get update && apt-get install -y \
       wget \
       gnupg \
       unzip \
       curl \
       xvfb \
       && rm -rf /var/lib/apt/lists/* \
       || (echo "Failed to install system packages" && exit 1)
   
   # Install Chrome with verification
   RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
       && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
       && apt-get update \
       && apt-get install -y google-chrome-stable \
       && google-chrome --version \
       || (echo "Failed to install Chrome" && exit 1)
   
   # Create non-root user
   RUN useradd -m -u 1000 appuser
   WORKDIR /app
   RUN chown appuser:appuser /app
   
   # Install Python dependencies as non-root
   USER appuser
   COPY --chown=appuser:appuser requirements.txt .
   RUN pip install --user --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY --chown=appuser:appuser . .
   
   # Create directories
   RUN mkdir -p output logs cache temp
   
   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
       CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1
   
   CMD ["python", "botasaurus_doctor_scraper.py"]
   ```

2. **Debug Container Issues:**
   ```bash
   # Build with verbose output
   docker build --no-cache --progress=plain -t pubscrape .
   
   # Run container with debugging
   docker run -it --rm pubscrape /bin/bash
   
   # Check Chrome installation in container
   docker run --rm pubscrape google-chrome --version
   
   # Check Python dependencies
   docker run --rm pubscrape pip list
   
   # Test basic functionality
   docker run --rm -e OPENAI_API_KEY=test pubscrape python -c "from botasaurus_doctor_scraper import search_bing_for_doctors; print('Import successful')"
   ```

3. **Fix Permission Issues:**
   ```bash
   # Fix host volume permissions
   sudo chown -R 1000:1000 output logs cache
   chmod -R 755 output logs cache
   
   # Or run with user mapping
   docker run --user $(id -u):$(id -g) \
     -v $(pwd)/output:/app/output \
     pubscrape
   ```

## API and Authentication Issues

### Issue: OpenAI API Errors

**Symptoms:**
```bash
Invalid API key
Rate limit exceeded
Authentication failed
```

**Solutions:**
1. **API Key Validation:**
   ```python
   import openai
   
   def validate_openai_api_key(api_key):
       """Validate OpenAI API key"""
       try:
           openai.api_key = api_key
           
           # Test with a simple request
           response = openai.models.list()
           
           print("✅ OpenAI API key is valid")
           print(f"   Available models: {len(response.data)}")
           return True
           
       except openai.AuthenticationError:
           print("❌ OpenAI API key is invalid")
           return False
       except openai.RateLimitError:
           print("⚠️  OpenAI API rate limit exceeded")
           return False
       except Exception as e:
           print(f"❌ OpenAI API error: {e}")
           return False
   
   # Test API key
   api_key = os.getenv('OPENAI_API_KEY')
   if api_key:
       validate_openai_api_key(api_key)
   else:
       print("❌ OPENAI_API_KEY environment variable not set")
   ```

2. **API Usage Monitoring:**
   ```python
   class APIUsageMonitor:
       def __init__(self):
           self.request_count = 0
           self.token_usage = 0
           self.start_time = time.time()
       
       def log_api_usage(self, response):
           """Log API usage from response"""
           self.request_count += 1
           
           if hasattr(response, 'usage'):
               self.token_usage += response.usage.total_tokens
           
           # Calculate rate
           elapsed = time.time() - self.start_time
           rpm = (self.request_count / elapsed) * 60 if elapsed > 0 else 0
           
           print(f"📊 API Usage: {self.request_count} requests, "
                 f"{self.token_usage} tokens, {rpm:.1f} RPM")
       
       def estimate_cost(self, model='gpt-4-turbo-preview'):
           """Estimate API costs"""
           pricing = {
               'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03},
               'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002}
           }
           
           if model in pricing:
               # Rough estimate (assuming 50/50 input/output)
               cost_per_1k = (pricing[model]['input'] + pricing[model]['output']) / 2
               estimated_cost = (self.token_usage / 1000) * cost_per_1k
               print(f"💰 Estimated cost: ${estimated_cost:.4f}")
               return estimated_cost
           
           return 0
   ```

## Debugging Tools and Techniques

### General Debugging Setup

```python
import logging
import sys
from pathlib import Path

def setup_debug_logging():
    """Set up comprehensive debug logging"""
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/debug.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.INFO)
    logging.getLogger('botasaurus').setLevel(logging.DEBUG)

def debug_environment():
    """Debug environment and dependencies"""
    print("🔍 Environment Debug Information:")
    
    # Python version
    print(f"Python: {sys.version}")
    
    # Key packages
    packages = ['botasaurus', 'selenium', 'requests', 'pydantic']
    for package in packages:
        try:
            import importlib
            mod = importlib.import_module(package)
            version = getattr(mod, '__version__', 'unknown')
            print(f"  ✅ {package}: {version}")
        except ImportError:
            print(f"  ❌ {package}: not installed")
    
    # System resources
    import psutil
    print(f"Memory: {psutil.virtual_memory().available // 1024 // 1024} MB available")
    print(f"CPU: {psutil.cpu_count()} cores")
    print(f"Disk: {psutil.disk_usage('.').free // 1024 // 1024} MB free")

# Run debugging
if __name__ == "__main__":
    setup_debug_logging()
    debug_environment()
```

### Browser Debugging

```python
def debug_browser_session():
    """Debug browser session issues"""
    from src.infra.browser_manager import create_browser_manager
    
    try:
        print("🌐 Testing browser session...")
        
        manager = create_browser_manager(mode="headful")  # Use headful for debugging
        driver = manager.get_browser_session("debug_session")
        
        # Test basic navigation
        driver.get("https://httpbin.org/html")
        print(f"✅ Page title: {driver.title}")
        
        # Test JavaScript execution
        result = driver.execute_script("return document.readyState;")
        print(f"✅ JS execution: {result}")
        
        # Test element finding
        elements = driver.find_elements(By.TAG_NAME, "h1")
        print(f"✅ Found {len(elements)} h1 elements")
        
        # Cleanup
        manager.close_all_sessions()
        print("✅ Browser session test completed")
        
    except Exception as e:
        print(f"❌ Browser session test failed: {e}")
        import traceback
        traceback.print_exc()
```

This troubleshooting guide covers the most common issues you'll encounter with the PubScrape system. For issues not covered here, check the logs, enable debug mode, and use the debugging tools provided.