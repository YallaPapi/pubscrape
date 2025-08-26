#!/usr/bin/env python3
"""
Business Lead Scraper with Real-time Dashboard
Shows live progress, stats, and results as they come in
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import csv
from typing import List, Dict
import logging
import threading
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

# Install required packages if needed
try:
    from rich import print as rprint
except ImportError:
    os.system("pip install rich")
    from rich import print as rprint

try:
    from botasaurus import *
    from botasaurus.browser import browser, Driver
except ImportError:
    print("Installing botasaurus...")
    os.system("pip install botasaurus")
    from botasaurus import *
    from botasaurus.browser import browser, Driver

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup console
console = Console()

class DashboardScraper:
    """Business scraper with live dashboard"""
    
    def __init__(self):
        self.results = []
        self.emails_found = 0
        self.businesses_scraped = 0
        self.current_query = ""
        self.current_action = "Initializing..."
        self.errors = []
        self.start_time = time.time()
        self.last_business = {}
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Stats tracking
        self.stats = {
            'queries_processed': 0,
            'total_queries': 0,
            'websites_visited': 0,
            'emails_found': 0,
            'businesses_scraped': 0,
            'errors': 0,
            'success_rate': 0,
            'avg_time_per_business': 0
        }
        
    def create_dashboard(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()
        
        # Create header
        header = Panel(
            Text("🔍 US BUSINESS LEAD SCRAPER - LIVE DASHBOARD 🔍", style="bold cyan", justify="center"),
            style="bold blue"
        )
        
        # Stats panel
        stats_text = f"""[bold cyan]📊 Statistics[/bold cyan]
        
⏱️  Runtime: {self.get_runtime()}
🔍  Queries: {self.stats['queries_processed']}/{self.stats['total_queries']}
🏢  Businesses Found: {self.stats['businesses_scraped']}
✉️  Emails Extracted: {self.stats['emails_found']}
🌐  Websites Visited: {self.stats['websites_visited']}
✅  Success Rate: {self.stats['success_rate']:.1f}%
⚡  Avg Time/Business: {self.stats['avg_time_per_business']:.1f}s
❌  Errors: {self.stats['errors']}"""
        
        stats_panel = Panel(stats_text, title="Statistics", border_style="green")
        
        # Current action panel
        action_text = f"""[bold yellow]Current Action:[/bold yellow]
{self.current_action}

[bold yellow]Current Query:[/bold yellow]
{self.current_query}"""
        
        action_panel = Panel(action_text, title="Current Activity", border_style="yellow")
        
        # Last business found
        if self.last_business:
            business_text = f"""[bold green]✓ Latest Business Found:[/bold green]

📍 Name: {self.last_business.get('name', 'N/A')}
📍 Address: {self.last_business.get('address', 'N/A')}
📞 Phone: {self.last_business.get('phone', 'N/A')}
✉️  Email: {self.last_business.get('email', '[searching...]')}
🌐 Website: {self.last_business.get('website', 'N/A')}
⭐ Rating: {self.last_business.get('rating', 'N/A')}"""
        else:
            business_text = "[dim]No businesses found yet...[/dim]"
        
        business_panel = Panel(business_text, title="Latest Find", border_style="green")
        
        # Progress bar
        progress_text = self.create_progress_bar()
        progress_panel = Panel(progress_text, title="Progress", border_style="cyan")
        
        # Recent errors (if any)
        if self.errors:
            errors_text = "\n".join(self.errors[-3:])  # Show last 3 errors
        else:
            errors_text = "[green]No errors encountered ✓[/green]"
        
        errors_panel = Panel(errors_text, title="Recent Logs", border_style="red")
        
        # Layout arrangement
        layout.split_column(
            Layout(header, size=3),
            Layout(name="main"),
            Layout(progress_panel, size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["main"]["left"].split_column(
            stats_panel,
            action_panel
        )
        
        layout["main"]["right"].split_column(
            business_panel,
            errors_panel
        )
        
        return layout
    
    def get_runtime(self):
        """Get formatted runtime"""
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def create_progress_bar(self):
        """Create progress bar visualization"""
        total = 1000  # Target
        current = self.stats['businesses_scraped']
        percentage = (current / total) * 100
        
        bar_width = 50
        filled = int(bar_width * (current / total))
        bar = "█" * filled + "░" * (bar_width - filled)
        
        return f"""[cyan]{bar}[/cyan]
{current}/{total} businesses ({percentage:.1f}%)
Emails: {self.stats['emails_found']} ({(self.stats['emails_found']/max(current, 1)*100):.1f}% success rate)"""
    
    def update_stats(self):
        """Update statistics"""
        if self.businesses_scraped > 0:
            self.stats['success_rate'] = (self.emails_found / self.businesses_scraped) * 100
            self.stats['avg_time_per_business'] = (time.time() - self.start_time) / self.businesses_scraped
    
    @browser(
        headless=True,  # Run headless for better performance
        block_resources=True,
        block_images=True,
        add_arguments=["--disable-blink-features=AutomationControlled"],
    )
    def scrape_bing_maps(self, driver: Driver, query: str):
        """Scrape business listings from Bing Maps"""
        try:
            self.current_query = query
            self.current_action = f"🔍 Searching Bing Maps for: {query}"
            
            # Navigate to Bing Maps
            driver.get("https://www.bing.com/maps")
            driver.sleep(2)
            
            # Search for businesses
            self.current_action = "📝 Entering search query..."
            search_box = driver.select('input[type="search"], input[name="q"], #maps_sb')
            if search_box:
                search_box.type(query)
                driver.sleep(1)
                search_box.press("Enter")
                driver.sleep(3)
            
            # Wait for results
            self.current_action = "⏳ Waiting for results to load..."
            driver.wait_for_element('.b_entityTP', timeout=10)
            
            # Scroll to load more results
            businesses = []
            last_count = 0
            scroll_attempts = 0
            max_scrolls = 5  # Reduced for faster results
            
            while scroll_attempts < max_scrolls:
                self.current_action = f"📜 Scrolling for more results... ({len(businesses)} found)"
                
                # Get current business cards
                cards = driver.select_all('.b_entityTP, .microcard, div[data-entityid]')
                
                for card in cards:
                    try:
                        business_data = self.extract_bing_business(driver, card)
                        if business_data and business_data not in businesses:
                            businesses.append(business_data)
                            self.last_business = business_data
                            self.businesses_scraped += 1
                            self.stats['businesses_scraped'] = self.businesses_scraped
                    except Exception as e:
                        pass
                
                # Check for new results
                if len(businesses) == last_count:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_count = len(businesses)
                
                # Scroll
                driver.execute_script("window.scrollBy(0, 500)")
                driver.sleep(1)
            
            self.stats['queries_processed'] += 1
            return businesses
            
        except Exception as e:
            self.errors.append(f"❌ Error: {str(e)[:50]}...")
            self.stats['errors'] += 1
            return []
    
    def extract_bing_business(self, driver: Driver, card):
        """Extract business data from Bing Maps card"""
        business = {}
        
        try:
            # Business name
            name_elem = card.select('h2, .b_entityTitle, [class*="title"]')
            if name_elem:
                business['name'] = name_elem.text.strip()
            
            # Address
            addr_elem = card.select('.b_factrow:contains("Address"), [class*="address"]')
            if addr_elem:
                business['address'] = addr_elem.text.replace('Address:', '').strip()
            
            # Phone
            phone_elem = card.select('.b_factrow:contains("Phone"), [class*="phone"], a[href^="tel:"]')
            if phone_elem:
                phone = phone_elem.get_attribute('href') or phone_elem.text
                business['phone'] = phone.replace('tel:', '').replace('Phone:', '').strip()
            
            # Website
            website_elem = card.select('a[href*="http"]:not([href*="bing"]):not([href*="microsoft"])')
            if website_elem:
                business['website'] = website_elem.get_attribute('href')
            
            # Rating
            rating_elem = card.select('[class*="rating"], .csrc_rating')
            if rating_elem:
                business['rating'] = rating_elem.text.strip()
            
            # Category
            cat_elem = card.select('.b_factrow:contains("Category"), [class*="category"]')
            if cat_elem:
                business['category'] = cat_elem.text.replace('Category:', '').strip()
                
        except Exception:
            pass
        
        return business if business.get('name') else None
    
    @browser(
        headless=True,
        block_resources=True,
        block_images=True,
        timeout=15
    )
    def extract_emails_from_website(self, driver: Driver, url: str):
        """Visit website and extract email addresses"""
        try:
            if not url or not url.startswith('http'):
                return None
            
            self.current_action = f"🌐 Visiting website: {url[:50]}..."
            self.stats['websites_visited'] += 1
            
            driver.get(url, timeout=10)
            driver.sleep(1.5)
            
            emails = set()
            
            # Check contact page
            self.current_action = "📧 Looking for contact information..."
            contact_link = driver.select('a:contains("Contact"), a[href*="contact"]')
            if contact_link:
                try:
                    contact_link.click()
                    driver.sleep(1)
                except:
                    pass
            
            # Extract emails
            page_text = driver.get_text()
            
            # Mailto links
            mailto_links = driver.select_all('a[href^="mailto:"]')
            for link in mailto_links:
                email = link.get_attribute('href').replace('mailto:', '').split('?')[0]
                if '@' in email:
                    emails.add(email.lower())
            
            # Regex search
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found_emails = re.findall(email_pattern, page_text)
            
            for email in found_emails:
                email = email.lower()
                if not any(x in email for x in ['example.', 'test.', 'demo.']):
                    emails.add(email)
            
            if emails:
                self.emails_found += 1
                self.stats['emails_found'] = self.emails_found
                self.current_action = f"✅ Found email: {list(emails)[0]}"
                return list(emails)[0]
            
            return None
            
        except Exception as e:
            self.errors.append(f"⚠️ Website error: {str(e)[:30]}...")
            return None
    
    async def scrape_with_dashboard(self, max_results: int = 1000):
        """Run scraper with live dashboard"""
        console.clear()
        
        # Generate queries
        queries = self.generate_queries()
        self.stats['total_queries'] = len(queries)
        
        with Live(self.create_dashboard(), refresh_per_second=2, console=console) as live:
            all_businesses = []
            
            for query in queries:
                if len(all_businesses) >= max_results:
                    break
                
                # Update dashboard
                live.update(self.create_dashboard())
                
                # Scrape from Bing Maps
                businesses = self.scrape_bing_maps(query)
                
                # Enrich with emails
                for business in businesses:
                    if len(all_businesses) >= max_results:
                        break
                    
                    if business.get('website'):
                        email = self.extract_emails_from_website(business['website'])
                        if email:
                            business['email'] = email
                    
                    business['source'] = 'Bing Maps'
                    business['query'] = query
                    business['scraped_at'] = datetime.now().isoformat()
                    
                    all_businesses.append(business)
                    self.update_stats()
                    
                    # Save incrementally
                    if len(all_businesses) % 10 == 0:
                        self.save_results(all_businesses)
                    
                    # Update dashboard
                    live.update(self.create_dashboard())
            
            # Final save
            self.save_results(all_businesses)
            self.current_action = "✅ Scraping complete! Results saved to output/"
            live.update(self.create_dashboard())
            
        return all_businesses
    
    def generate_queries(self):
        """Generate search queries"""
        cities = [
            "New York NY", "Los Angeles CA", "Chicago IL", "Houston TX",
            "Phoenix AZ", "Philadelphia PA", "San Antonio TX", "San Diego CA",
            "Dallas TX", "Miami FL"
        ]
        
        business_types = [
            "restaurant", "dental clinic", "law firm", "real estate agency",
            "auto repair", "plumbing service", "landscaping", "coffee shop"
        ]
        
        queries = []
        for city in cities:
            for business_type in business_types:
                queries.append(f"{business_type} near {city}")
        
        return queries
    
    def save_results(self, businesses: List[Dict]):
        """Save results to CSV and JSON"""
        
        # Save to CSV
        csv_path = self.output_dir / "us_business_owners.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if businesses:
                fieldnames = ['name', 'address', 'phone', 'email', 'website', 'rating', 'category', 'source', 'query', 'scraped_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(businesses)
        
        # Save to JSON
        json_path = self.output_dir / "us_business_owners.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(businesses, f, indent=2, ensure_ascii=False)

async def main():
    """Main execution with dashboard"""
    scraper = DashboardScraper()
    
    # Run scraper with dashboard
    results = await scraper.scrape_with_dashboard(max_results=1000)
    
    # Show final summary
    console.print("\n" + "="*60, style="bold cyan")
    console.print("SCRAPING COMPLETE!", style="bold green", justify="center")
    console.print("="*60, style="bold cyan")
    console.print(f"Total businesses found: {len(results)}", style="green")
    console.print(f"Emails extracted: {scraper.emails_found}", style="green")
    console.print(f"Success rate: {(scraper.emails_found/len(results)*100):.1f}%", style="green")
    console.print(f"\nResults saved to: output/us_business_owners.csv", style="yellow")
    console.print("="*60 + "\n", style="bold cyan")

if __name__ == "__main__":
    asyncio.run(main())