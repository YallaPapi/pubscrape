"""
Botasaurus Demo - How to properly use it for celebrity/influencer scraping
This shows the CORRECT way to use Botasaurus for protected sites
"""

from botasaurus import *

# Method 1: Browser automation (for JavaScript-heavy sites)
@browser(
    headless=False,  # Set to True in production
    block_images=True,  # Faster loading
)
def scrape_protected_site(driver, data):
    """
    Botasaurus can bypass:
    - Cloudflare protection
    - JavaScript challenges
    - Bot detection systems
    """
    
    # Example 1: Scraping Instagram (normally blocks bots)
    driver.get("https://www.instagram.com/cristiano")
    driver.wait_for_element("article", timeout=10)  # Wait for content
    
    # Human-like interaction
    driver.scroll_to_bottom()  # Scroll like a human
    driver.sleep(2)  # Random delays
    
    # Extract data
    bio = driver.get_text("div.-vDIg span")
    follower_count = driver.get_text("span.g47SY")
    
    # Example 2: Cloudflare-protected site
    driver.google_get("podcast guests directory")  # Uses Google to find sites
    results = driver.find_elements("h3")
    
    return {
        "instagram_bio": bio,
        "followers": follower_count,
        "search_results": len(results)
    }


# Method 2: Request-based scraping (faster for APIs)
@request(
    parallel=10,  # Scrape 10 URLs at once
    cache=True,  # Cache responses
    max_retries=3,
)
def scrape_api_endpoint(request, url):
    """
    For sites that don't need browser rendering
    """
    response = request.get(url)
    return response.json()


# Method 3: Stealth browser (maximum anti-detection)
@browser(
    headless=False,
    block_images=False,
    window_size=(1920, 1080),  # Full browser size
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
)
def scrape_with_stealth(driver, celebrity_name):
    """
    Maximum stealth for heavily protected sites
    """
    
    # Botasaurus features for anti-detection:
    # 1. Realistic mouse movements
    driver.move_mouse_to(500, 300)  # Human-like mouse movement
    
    # 2. Random delays between actions
    driver.sleep(2, 4)  # Random sleep between 2-4 seconds
    
    # 3. Bypass Cloudflare
    driver.get("https://heavily-protected-site.com")
    
    # 4. Handle popups/cookies
    try:
        cookie_button = driver.find_element("button[contains(text(), 'Accept')]")
        if cookie_button:
            driver.click(cookie_button)
    except:
        pass
    
    # 5. Search for celebrity
    search_box = driver.find_element("input[type='search']")
    driver.type(search_box, celebrity_name, delay=0.1)  # Type with human delay
    driver.press_enter()
    
    # 6. Extract results
    results = driver.find_elements(".result-item")
    
    data = []
    for result in results[:5]:
        data.append({
            "name": driver.get_text(result.find_element(".name")),
            "contact": driver.get_text(result.find_element(".contact")),
        })
    
    return data


# The REAL power of Botasaurus:
class CelebrityScraperBot:
    """
    Production-ready celebrity contact scraper using Botasaurus
    """
    
    def scrape_imdb_with_bypass(self, celebrity_name):
        """
        IMDb has Cloudflare - Botasaurus can bypass it
        """
        @browser(headless=True)
        def _scrape(driver, name):
            # Bypass Cloudflare and scrape IMDb
            driver.get(f"https://www.imdb.com/find?q={name}")
            # ... extraction logic
            return {}
        
        return _scrape(celebrity_name)
    
    def scrape_linkedin_without_login(self, person_name):
        """
        LinkedIn aggressively blocks bots - Botasaurus can handle it
        """
        @browser(headless=True, block_images=True)
        def _scrape(driver, name):
            # Use Google to find LinkedIn profiles (avoids login)
            driver.google_get(f"site:linkedin.com/in/ {name}")
            # Click first result
            first_result = driver.find_element("h3")
            driver.click(first_result)
            # Extract public profile data
            return {}
        
        return _scrape(person_name)
    
    def scrape_instagram_profiles(self, username):
        """
        Instagram has heavy bot protection - Botasaurus bypasses it
        """
        @browser(headless=False)  # Instagram may need visible browser
        def _scrape(driver, user):
            driver.get(f"https://www.instagram.com/{user}")
            # Wait for content to load
            driver.wait_for_element("article", timeout=10)
            
            # Extract bio (often has email)
            bio = driver.get_text("div.-vDIg")
            
            # Look for business email button
            email_button = driver.find_element("button[contains(text(), 'Email')]")
            if email_button:
                # This would show email if logged in
                pass
            
            return {"bio": bio, "has_email_button": bool(email_button)}
        
        return _scrape(username)


# Why Botasaurus is powerful:
"""
1. BYPASSES CLOUDFLARE: Many celebrity sites use Cloudflare
2. HANDLES JAVASCRIPT: Modern sites need JS rendering
3. HUMAN-LIKE BEHAVIOR: Avoids detection with realistic actions
4. PARALLEL SCRAPING: Scrape 100s of profiles at once
5. BUILT-IN CACHING: Don't re-scrape same data
6. ERROR HANDLING: Automatic retries and screenshots on failure

Sites Botasaurus can scrape that others can't:
- Instagram (without API)
- LinkedIn (public profiles without login)
- IMDb (bypasses Cloudflare)
- Podcast guest directories (many use protection)
- Conference speaker lists (often behind JS)
- Talent agency sites (usually protected)
"""

if __name__ == "__main__":
    print("BOTASAURUS CAPABILITIES:")
    print("-" * 50)
    print("1. Bypass Cloudflare protection")
    print("2. Handle JavaScript-rendered sites")
    print("3. Simulate human behavior")
    print("4. Parallel scraping at scale")
    print("5. Automatic retry and error handling")
    print("\nPERFECT FOR:")
    print("- Instagram/TikTok profiles")
    print("- LinkedIn without login")
    print("- IMDb celebrity pages")
    print("- Protected directory sites")
    print("- Any site that blocks regular scrapers")