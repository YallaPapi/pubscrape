#!/usr/bin/env python3
"""
Real Business Lead Scraper using Botasaurus Anti-Detection
Scrapes Google Maps for actual business listings with emails
"""

import time
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import random

from botasaurus.browser import browser
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

# Setup
console = Console()

class BotasaurusBusinessScraper:
    """Advanced business scraper using Botasaurus anti-detection"""
    
    def __init__(self):
        self.results = []
        self.stats = {
            'total_scraped': 0,
            'with_email': 0,
            'with_phone': 0,
            'with_website': 0,
            'queries_processed': 0,
            'websites_visited': 0
        }
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.current_action = "Initializing..."
        self.current_query = ""
        self.last_business = {}
    
    @browser(
        headless=False,
        block_images=True,
        window_size="1920,1080",
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    )
    def scrape_google_maps_businesses(self, driver, search_data):
        """Scrape businesses from Google Maps using anti-detection"""
        # --- shims for nonstandard helpers ---
        if not hasattr(driver, "short_random_sleep"):
            import time as _t, random as _r
            def _srs():
                _t.sleep(_r.uniform(0.5, 1.5))
            driver.short_random_sleep = _srs
        if not hasattr(driver, "get_element_or_none_by_selector"):
            from selenium.webdriver.common.by import By as _By
            def _get_one(sel):
                try:
                    return driver.find_element(_By.CSS_SELECTOR, sel)
                except Exception:
                    return None
            driver.get_element_or_none_by_selector = _get_one
        if not hasattr(driver, "get_elements_or_none_by_selector"):
            from selenium.webdriver.common.by import By as _By
            def _get_many(sel_or_list):
                sels = sel_or_list if isinstance(sel_or_list, list) else [sel_or_list]
                for s in sels:
                    els = driver.find_elements(_By.CSS_SELECTOR, s)
                    if els:
                        return els
                return []
            driver.get_elements_or_none_by_selector = _get_many
        if not hasattr(driver, "google_get"):
            def _gg(url):
                driver.get(url)
            driver.google_get = _gg
        # --- end shims ---
        query, location = search_data['query'], search_data['location']
        self.current_query = f"{query} in {location}"
        self.current_action = "🔍 Starting Google Maps search..."
        
        businesses = []
        
        try:
            # Use organic navigation - visit Google first
            self.current_action = "🌐 Visiting Google homepage organically..."
            driver.google_get("https://www.google.com/maps")
            driver.short_random_sleep()
            
            # Search for businesses
            self.current_action = f"📝 Searching for '{query}' in '{location}'..."
            search_box = driver.get_element_or_none_by_selector('input[data-value="Search"], input[id="searchboxinput"]')
            
            if search_box:
                # Human-like typing
                search_query = f"{query} {location}"
                search_box.clear()
                driver.type(search_box, search_query, typing_speed=100)  # Human typing speed
                driver.short_random_sleep()
                search_box.send_keys("\n")
            
            # Wait for results to load
            self.current_action = "⏳ Waiting for map results to load..."
            driver.sleep(3)
            
            # Check for results
            results_container = driver.get_element_or_none_by_selector('div[role="main"]')
            if not results_container:
                console.print(f"[red]No results container found for {query}[/red]")
                return []
            
            # Scroll through results to load more businesses
            self.current_action = "📜 Scrolling through results..."
            businesses = self._extract_businesses_with_scroll(driver, max_businesses=50)
            
            self.stats['queries_processed'] += 1
            console.print(f"[green]Found {len(businesses)} businesses for '{query}' in '{location}'[/green]")
            
        except Exception as e:
            console.print(f"[red]Error scraping Google Maps: {str(e)}[/red]")
            
        return businesses
    
    def _extract_businesses_with_scroll(self, driver, max_businesses=50):
        """Extract businesses with infinite scroll handling"""
        businesses = []
        last_count = 0
        scroll_attempts = 0
        max_scrolls = 10
        
        while len(businesses) < max_businesses and scroll_attempts < max_scrolls:
            self.current_action = f"📊 Extracting business cards... ({len(businesses)} found)"
            
            # Find business cards
            business_cards = driver.get_elements_or_none_by_selector([
                'div[data-result-index]',  # Google Maps result cards
                'div[role="article"]',      # Alternative selector
                'div.Nv2PK',               # Alternative selector
                'a[data-cid]'              # Business links
            ])
            
            if business_cards:
                for card in business_cards:
                    if len(businesses) >= max_businesses:
                        break
                    
                    try:
                        business = self._extract_business_from_card(driver, card)
                        if business and not self._is_duplicate(business, businesses):
                            businesses.append(business)
                            self.last_business = business
                            self.stats['total_scraped'] += 1
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to extract business: {str(e)[:50]}...[/yellow]")
            
            # Check if we got new results
            if len(businesses) == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = len(businesses)
            
            # Scroll down with human-like behavior
            driver.execute_script("window.scrollBy(0, Math.random() * 500 + 300)")
            driver.short_random_sleep()
            
            # Try to click "Show more results" if available
            more_button = driver.get_element_or_none_by_selector('button:contains("more"), button[aria-label*="more"]')
            if more_button:
                try:
                    more_button.click()
                    driver.sleep(2)
                except:
                    pass
        
        return businesses
    
    def _extract_business_from_card(self, driver, card):
        """Extract business information from a single card"""
        business = {}
        
        try:
            # Business name
            name_selectors = [
                'div[class*="fontHeadline"]',
                'h3', 'h2', 'h1',
                '[data-value="title"]',
                'div[role="img"]',
                'span[class*="title"]'
            ]
            
            for selector in name_selectors:
                name_elem = card.get_element_or_none_by_selector(selector)
                if name_elem and name_elem.text.strip():
                    business['name'] = name_elem.text.strip()
                    break
            
            if not business.get('name'):
                return None
            
            # Address
            address_selectors = [
                'span[class*="address"]',
                'div:contains("·")',
                '[data-value="address"]'
            ]
            
            for selector in address_selectors:
                addr_elem = card.get_element_or_none_by_selector(selector)
                if addr_elem and addr_elem.text.strip():
                    business['address'] = addr_elem.text.strip()
                    break
            
            # Phone
            phone_elem = card.get_element_or_none_by_selector('span[data-value="phone"], a[href^="tel:"]')
            if phone_elem:
                phone = phone_elem.get_attribute('href') or phone_elem.text
                business['phone'] = phone.replace('tel:', '').strip()
            
            # Website
            website_elem = card.get_element_or_none_by_selector('a[data-value="website"], a[href*="http"]:not([href*="google.com"])')
            if website_elem:
                business['website'] = website_elem.get_attribute('href')
            
            # Rating
            rating_elem = card.get_element_or_none_by_selector('[data-value="rating"], span:contains("★")')
            if rating_elem:
                business['rating'] = rating_elem.text.strip()
            
            # Business type/category
            category_elem = card.get_element_or_none_by_selector('[data-value="category"], span[class*="category"]')
            if category_elem:
                business['category'] = category_elem.text.strip()
            
        except Exception as e:
            console.print(f"[yellow]Warning extracting fields: {str(e)[:50]}...[/yellow]")
        
        return business if business.get('name') else None
    
    def _is_duplicate(self, business, existing_businesses):
        """Check if business is duplicate"""
        name = business.get('name', '').lower()
        for existing in existing_businesses:
            if existing.get('name', '').lower() == name:
                return True
        return False
    
    @browser(
        headless=True,
        block_images=True,
        window_size="1280,800",
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    def extract_email_from_website(self, driver, url_data):
        """Extract email from business website using anti-detection"""
        url = url_data['url']
        
        if not url or not url.startswith('http'):
            return None
        
        try:
            self.current_action = f"🌐 Visiting: {url[:50]}..."
            self.stats['websites_visited'] += 1
            
            # Use organic navigation
            driver.google_get(url, bypass_cloudflare=True)
            driver.short_random_sleep()
            
            emails = set()
            
            # Look for contact page
            contact_links = driver.get_elements_or_none_by_selector([
                'a:contains("Contact")', 'a:contains("contact")',
                'a:contains("About")', 'a:contains("about")',
                'a[href*="contact"]', 'a[href*="about"]'
            ])
            
            if contact_links:
                try:
                    contact_links[0].click()
                    driver.sleep(2)
                except:
                    pass
            
            # Extract emails
            page_text = driver.get_text()
            
            # Find mailto links
            mailto_links = driver.get_elements_or_none_by_selector('a[href^="mailto:"]')
            for link in mailto_links or []:
                email = link.get_attribute('href').replace('mailto:', '').split('?')[0]
                if '@' in email and '.' in email:
                    emails.add(email.lower())
            
            # Regex search in page text
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found_emails = re.findall(email_pattern, page_text)
            
            for email in found_emails:
                email = email.lower()
                if not any(bad in email for bad in ['example.', 'test.', 'demo.', 'noreply']):
                    emails.add(email)
            
            # Look for obfuscated emails
            obfuscated = re.findall(r'([a-zA-Z0-9._%+-]+)\s*\[\s*at\s*\]\s*([a-zA-Z0-9.-]+)', page_text, re.IGNORECASE)
            for match in obfuscated:
                email = f"{match[0]}@{match[1]}".lower()
                emails.add(email)
            
            # Prioritize business emails
            business_emails = [e for e in emails if any(prefix in e for prefix in ['info@', 'contact@', 'sales@', 'support@', 'hello@'])]
            
            if business_emails:
                self.stats['with_email'] += 1
                return business_emails[0]
            elif emails:
                self.stats['with_email'] += 1
                return list(emails)[0]
                
        except Exception as e:
            console.print(f"[yellow]Email extraction error for {url}: {str(e)[:50]}...[/yellow]")
        
        return None
    
    def scrape_businesses_with_dashboard(self, target_businesses=1000):
        """Main scraper with live dashboard"""
        console.clear()
        
        # Generate search queries
        cities = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
            "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
            "Dallas, TX", "Miami, FL", "Atlanta, GA", "Boston, MA"
        ]
        
        business_types = [
            "restaurant", "dental clinic", "law firm", "real estate agency",
            "auto repair", "plumbing service", "electrical contractor",
            "medical clinic", "accounting firm", "insurance agency"
        ]
        
        # Create search tasks
        search_tasks = []
        for city in cities[:6]:  # Limit cities for faster results
            for btype in business_types[:5]:  # Limit business types
                search_tasks.append({'query': btype, 'location': city})
        
        all_businesses = []
        
        console.print("\n[bold cyan]🚀 BOTASAURUS BUSINESS SCRAPER STARTING[/bold cyan]\n")
        console.print(f"Target: {target_businesses} businesses")
        console.print(f"Search tasks: {len(search_tasks)}")
        console.print(f"Anti-detection: [green]ENABLED[/green]")
        console.print(f"Human behavior: [green]ENABLED[/green]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            main_task = progress.add_task("Overall Progress", total=target_businesses)
            
            for search_task in search_tasks:
                if len(all_businesses) >= target_businesses:
                    break
                
                progress.update(main_task, description=f"Scraping {search_task['query']} in {search_task['location']}")
                
                # Scrape Google Maps
                businesses = self.scrape_google_maps_businesses(search_task)
                
                # Enrich with emails
                for business in businesses:
                    if len(all_businesses) >= target_businesses:
                        break
                    
                    # Track stats
                    if business.get('phone'):
                        self.stats['with_phone'] += 1
                    if business.get('website'):
                        self.stats['with_website'] += 1
                        # Extract email
                        email = self.extract_email_from_website({'url': business['website']})
                        if email:
                            business['email'] = email
                    
                    # Add metadata
                    business['scraped_at'] = datetime.now().isoformat()
                    business['search_query'] = search_task['query']
                    business['search_location'] = search_task['location']
                    
                    all_businesses.append(business)
                    progress.update(main_task, completed=len(all_businesses))
                
                # Save incrementally
                if len(all_businesses) % 25 == 0:
                    self.save_results(all_businesses)
        
        # Final save
        self.save_results(all_businesses)
        return all_businesses
    
    def save_results(self, businesses):
        """Save results to multiple formats"""
        
        # Save to CSV
        csv_path = self.output_dir / "botasaurus_business_leads.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if businesses:
                fieldnames = ['name', 'email', 'phone', 'address', 'website', 
                             'rating', 'category', 'search_query', 'search_location', 'scraped_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(businesses)
        
        # Save to JSON
        json_path = self.output_dir / "botasaurus_business_leads.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(businesses, f, indent=2, ensure_ascii=False)
        
        # Save statistics
        self.stats['success_rate'] = f"{(self.stats['with_email'] / max(len(businesses), 1) * 100):.1f}%"
        stats_path = self.output_dir / "botasaurus_scraping_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def display_results(self, businesses):
        """Display final results"""
        console.print("\n" + "="*80)
        console.print("[bold green]✅ SCRAPING COMPLETE![/bold green]", justify="center")
        console.print("="*80)
        
        # Create results table
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Businesses", str(len(businesses)))
        table.add_row("With Email", f"{self.stats['with_email']} ({self.stats['with_email']/max(len(businesses),1)*100:.1f}%)")
        table.add_row("With Phone", f"{self.stats['with_phone']} ({self.stats['with_phone']/max(len(businesses),1)*100:.1f}%)")
        table.add_row("With Website", f"{self.stats['with_website']} ({self.stats['with_website']/max(len(businesses),1)*100:.1f}%)")
        table.add_row("Queries Processed", str(self.stats['queries_processed']))
        table.add_row("Websites Visited", str(self.stats['websites_visited']))
        
        console.print(table)
        
        # Show sample results
        console.print("\n[bold cyan]📋 SAMPLE RESULTS:[/bold cyan]\n")
        for i, business in enumerate(businesses[:10], 1):
            console.print(f"[bold]{i}. {business.get('name', 'Unknown')}[/bold]")
            console.print(f"   📧 Email: [green]{business.get('email', 'N/A')}[/green]")
            console.print(f"   📞 Phone: {business.get('phone', 'N/A')}")
            console.print(f"   📍 Address: {business.get('address', 'N/A')}")
            console.print(f"   🌐 Website: {business.get('website', 'N/A')}")
            console.print(f"   ⭐ Rating: {business.get('rating', 'N/A')}")
            console.print()

def main():
    """Main execution"""
    scraper = BotasaurusBusinessScraper()
    
    try:
        # Run scraper with dashboard
        businesses = scraper.scrape_businesses_with_dashboard(target_businesses=1000)
        
        # Display results
        scraper.display_results(businesses)
        
        console.print(f"\n[bold green]✅ Results saved to: output/botasaurus_business_leads.csv[/bold green]")
        console.print("[bold yellow]🚀 Powered by Botasaurus Anti-Detection Technology![/bold yellow]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Scraping interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {str(e)}[/red]")

if __name__ == "__main__":
    main()