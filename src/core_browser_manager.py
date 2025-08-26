#!/usr/bin/env python3
"""
Core Browser Management with Anti-Detection
Central module for managing browser sessions with anti-bot protection
"""

from botasaurus.browser import browser, Driver
import random
import time
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserManager:
    """Core browser management with anti-detection features."""
    
    # User agents pool
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    
    # Common screen resolutions
    SCREEN_SIZES = [
        (1920, 1080), (1366, 768), (1440, 900), 
        (1536, 864), (1680, 1050), (2560, 1440)
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize browser manager with configuration."""
        self.config = config or {}
        self.sessions = {}
        self.rate_limiter = RateLimiter()
        
    def get_random_user_agent(self) -> str:
        """Get random user agent for anti-detection."""
        return random.choice(self.USER_AGENTS)
    
    def get_random_viewport(self) -> tuple:
        """Get random viewport size."""
        return random.choice(self.SCREEN_SIZES)
    
    def get_browser_config(self, **kwargs):
        """Get browser configuration with anti-detection features."""
        width, height = self.get_random_viewport()
        
        default_config = {
            'headless': kwargs.get('headless', True),
            'block_images': kwargs.get('block_images', True),
            'reuse_driver': kwargs.get('reuse_driver', True),
            'user_agent': kwargs.get('user_agent', self.get_random_user_agent()),
            'window_size': (width, height),
            'add_arguments': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                f'--window-size={width},{height}',
                '--start-maximized'
            ],
            'experimental_options': {
                'excludeSwitches': ['enable-automation'],
                'useAutomationExtension': False,
                'prefs': {
                    'credentials_enable_service': False,
                    'profile.password_manager_enabled': False
                }
            }
        }
        
        # Merge with provided kwargs
        for key, value in kwargs.items():
            if key not in default_config:
                default_config[key] = value
                
        return default_config
    
    def human_like_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """Add human-like random delay."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def smart_scroll(self, driver: Driver, scroll_pause_time: float = 1.0):
        """Perform human-like scrolling on page."""
        # Get page height
        last_height = driver.run_js("return document.body.scrollHeight")
        
        while True:
            # Scroll down with random distance
            scroll_distance = random.randint(300, 700)
            driver.run_js(f"window.scrollBy(0, {scroll_distance})")
            
            # Random pause
            self.human_like_delay(scroll_pause_time * 0.5, scroll_pause_time * 1.5)
            
            # Check if reached bottom
            new_height = driver.run_js("return document.body.scrollHeight")
            current_position = driver.run_js("return window.pageYOffset + window.innerHeight")
            
            if current_position >= new_height:
                break
                
            last_height = new_height
    
    def safe_click(self, driver: Driver, element):
        """Click element with human-like behavior."""
        # Scroll element into view
        driver.run_js("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        self.human_like_delay(0.3, 0.8)
        
        # Move mouse and click
        element.click()
        self.human_like_delay(0.2, 0.5)
    
    def bypass_cloudflare(self, driver: Driver, url: str) -> bool:
        """Enhanced Cloudflare bypass using botasaurus."""
        try:
            # Use botasaurus built-in bypass
            driver.google_get(url, bypass_cloudflare=True)
            self.human_like_delay(2, 4)
            
            # Check if still blocked
            current_url = driver.current_url.lower()
            page_source = driver.page_html.lower()
            
            blocked_indicators = [
                'enable-javascript', 'cloudflare', 'cf-browser-verification',
                'checking your browser', 'ddos-guard', 'please wait'
            ]
            
            is_blocked = any(indicator in current_url or indicator in page_source 
                           for indicator in blocked_indicators)
            
            if is_blocked:
                logger.warning(f"Cloudflare detected at {url}")
                # Try additional bypass techniques
                driver.run_js("location.reload();")
                self.human_like_delay(3, 5)
                
            return not is_blocked
            
        except Exception as e:
            logger.error(f"Cloudflare bypass error: {e}")
            return False
    
    def extract_emails(self, driver: Driver) -> List[str]:
        """Extract emails from current page using multiple methods."""
        emails = driver.run_js("""
            const emails = new Set();
            
            // Method 1: Regex on text content
            const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\\.[a-zA-Z0-9_-]+)/gi;
            const pageText = document.body.innerText || '';
            const textMatches = pageText.match(emailRegex) || [];
            textMatches.forEach(e => emails.add(e.toLowerCase()));
            
            // Method 2: Mailto links
            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                const email = a.href.replace('mailto:', '').split('?')[0];
                if (email) emails.add(email.toLowerCase());
            });
            
            // Method 3: Check common email containers
            const selectors = [
                '[class*="email"]', '[id*="email"]',
                '[class*="contact"]', '[id*="contact"]',
                '[class*="mail"]', '[id*="mail"]'
            ];
            
            selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(elem => {
                    const text = elem.textContent || '';
                    const matches = text.match(emailRegex) || [];
                    matches.forEach(e => emails.add(e.toLowerCase()));
                });
            });
            
            // Method 4: Check data attributes
            document.querySelectorAll('[data-email]').forEach(elem => {
                const email = elem.getAttribute('data-email');
                if (email && email.includes('@')) {
                    emails.add(email.toLowerCase());
                }
            });
            
            // Filter out invalid emails
            return Array.from(emails).filter(email => {
                if (!email.includes('@') || !email.includes('.')) return false;
                
                const invalidPatterns = [
                    'example', 'test', 'demo', 'sample',
                    'noreply', 'no-reply', 'donotreply',
                    '.png', '.jpg', '.gif', '.css', '.js',
                    'sentry', 'cloudflare', 'protected'
                ];
                
                return !invalidPatterns.some(pattern => email.includes(pattern));
            });
        """)
        
        return emails
    
    def extract_social_links(self, driver: Driver) -> Dict[str, str]:
        """Extract social media links from current page."""
        social_links = driver.run_js("""
            const links = {
                twitter: null,
                linkedin: null,
                facebook: null,
                instagram: null,
                youtube: null,
                github: null
            };
            
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href.toLowerCase();
                
                if ((href.includes('twitter.com') || href.includes('x.com')) && !links.twitter) {
                    links.twitter = a.href;
                } else if (href.includes('linkedin.com') && !links.linkedin) {
                    links.linkedin = a.href;
                } else if (href.includes('facebook.com') && !links.facebook) {
                    links.facebook = a.href;
                } else if (href.includes('instagram.com') && !links.instagram) {
                    links.instagram = a.href;
                } else if (href.includes('youtube.com') && !links.youtube) {
                    links.youtube = a.href;
                } else if (href.includes('github.com') && !links.github) {
                    links.github = a.href;
                }
            });
            
            // Remove null values
            Object.keys(links).forEach(key => {
                if (!links[key]) delete links[key];
            });
            
            return links;
        """)
        
        return social_links

class RateLimiter:
    """Rate limiting for requests."""
    
    def __init__(self):
        self.last_request_time = {}
        self.request_counts = {}
        
    def wait_if_needed(self, domain: str, min_delay: float = 1.0, max_delay: float = 3.0):
        """Wait if needed to respect rate limits."""
        current_time = time.time()
        
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < min_delay:
                wait_time = random.uniform(min_delay, max_delay)
                time.sleep(wait_time)
        
        self.last_request_time[domain] = time.time()
        self.request_counts[domain] = self.request_counts.get(domain, 0) + 1
        
    def get_request_count(self, domain: str) -> int:
        """Get number of requests made to domain."""
        return self.request_counts.get(domain, 0)

class SessionManager:
    """Manage browser sessions with persistence."""
    
    def __init__(self, session_dir: str = "browser_sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.active_sessions = {}
        
    def save_session(self, session_id: str, data: Dict):
        """Save session data to disk."""
        session_file = self.session_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load session data from disk."""
        session_file = self.session_dir / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return None
    
    def create_session(self, session_id: str, **kwargs) -> Dict:
        """Create new browser session."""
        session_data = {
            'id': session_id,
            'created_at': time.time(),
            'last_used': time.time(),
            'config': kwargs,
            'cookies': [],
            'history': []
        }
        
        self.active_sessions[session_id] = session_data
        self.save_session(session_id, session_data)
        return session_data
    
    def update_session(self, session_id: str, updates: Dict):
        """Update existing session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].update(updates)
            self.active_sessions[session_id]['last_used'] = time.time()
            self.save_session(session_id, self.active_sessions[session_id])

# Example usage functions
@browser(
    headless=False,
    block_images=True,
    reuse_driver=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
def example_scraper(driver, url):
    """Example scraper using anti-detection browser."""
    manager = BrowserManager()
    rate_limiter = RateLimiter()
    
    # Parse domain for rate limiting
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    rate_limiter.wait_if_needed(domain)
    
    # Navigate with Cloudflare bypass
    if manager.bypass_cloudflare(driver, url):
        logger.info(f"Successfully loaded {url}")
        
        # Human-like scrolling
        manager.smart_scroll(driver)
        
        # Extract data
        emails = manager.extract_emails(driver)
        social_links = manager.extract_social_links(driver)
        
        return {
            'url': url,
            'emails': emails,
            'social_links': social_links,
            'success': True
        }
    else:
        logger.error(f"Failed to bypass protection at {url}")
        return {'url': url, 'success': False}

def test_anti_detection():
    """Test anti-detection features."""
    test_urls = [
        "https://www.stanford.edu/",
        "https://www.mit.edu/",
        "https://www.harvard.edu/"
    ]
    
    results = []
    for url in test_urls:
        result = example_scraper(url)
        results.append(result)
        print(f"\nResults for {url}:")
        print(f"  Success: {result.get('success')}")
        print(f"  Emails found: {len(result.get('emails', []))}")
        print(f"  Social links: {list(result.get('social_links', {}).keys())}")
    
    return results

if __name__ == "__main__":
    print("Core Browser Manager with Anti-Detection")
    print("="*50)
    print("\nFeatures:")
    print("- Random user agents and viewports")
    print("- Human-like delays and scrolling")
    print("- Cloudflare bypass integration")
    print("- Email and social media extraction")
    print("- Rate limiting and session management")
    print("\nRunning test...")
    
    test_anti_detection()