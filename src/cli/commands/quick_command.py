"""
Quick Command Implementation

Handles quick, lightweight scraping operations with minimal configuration.
Uses both browser-based and HTTP fallback strategies.
"""

import csv
import time
from pathlib import Path
from argparse import Namespace

from .base import BaseCommand


class QuickCommand(BaseCommand):
    """Command for quick, lightweight scraping operations"""
    
    def add_arguments(self, parser):
        """Add quick command arguments"""
        parser.add_argument(
            '--query', '-q', 
            help='Search query', 
            default='coffee shops in Seattle'
        )
        parser.add_argument(
            '--max', type=int, default=10, 
            help='Max leads to generate'
        )
        parser.add_argument(
            '--fallback-only', action='store_true', 
            help='Use HTTP fallback only (no browser)'
        )
    
    async def execute(self, args: Namespace) -> int:
        """
        Execute quick scrape operation.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"⚡ Quick scrape starting. query={args.query} max={args.max}")
            
            # Ensure output directory exists
            output_base = getattr(self.config_manager.export, 'output_directory', 'output')
            output_dir = self._ensure_output_directory(output_base or 'output')
            if not output_dir:
                return 1
            
            leads = []
            start_time = time.monotonic()
            
            # Try browser-based scraping first (unless fallback-only requested)
            if not args.fallback_only:
                leads = await self._try_browser_scraping(args.query, args.max)
            
            # Try HTTP fallback if no leads found
            if not leads and (time.monotonic() - start_time) < 20:
                leads = await self._try_http_fallback(args.query, args.max, start_time)
            
            # Export results
            csv_path = output_dir / 'quick_leads.csv'
            self._export_leads_csv(leads, csv_path)
            
            # Display summary
            self._display_results_summary(leads)
            
            self.logger.info(f"✅ Quick scrape completed: {len(leads)} leads -> {csv_path}")
            return 0
            
        except Exception as e:
            return self._handle_command_error(e, "Quick command failed")
    
    async def _try_browser_scraping(self, query: str, max_leads: int) -> list:
        """Try browser-based scraping with Google Maps"""
        leads = []
        
        try:
            from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
            from src.scrapers.email_extractor import extract_emails_from_website
            
            self.logger.info("🌐 Using Google Maps browser scraper")
            
            businesses = scrape_google_maps_businesses(
                query, 
                max_results=max(5, min(10, max_leads))
            )
            
            for business in businesses:
                if len(leads) >= max_leads:
                    break
                
                # Extract email from website if available
                if business.get('website'):
                    try:
                        email = extract_emails_from_website(business['website']) or ''
                        business['email'] = email
                    except Exception as e:
                        self.logger.debug(f"Email extraction failed for {business['website']}: {e}")
                        business['email'] = ''
                
                business['source'] = 'google_maps'
                leads.append(business)
                
        except Exception as e:
            self.logger.warning(f"Browser scrape failed: {e}")
        
        return leads
    
    async def _try_http_fallback(self, query: str, max_leads: int, start_time: float) -> list:
        """Try HTTP-based fallback scraping"""
        leads = []
        
        try:
            self.logger.info("🔎 Fallback to HTTP search path (Bing/Yellow Pages)")
            
            from simple_business_scraper import SimpleBusinessScraper
            scraper = SimpleBusinessScraper()
            
            businesses = scraper.search_bing(query, max_results=max(5, min(10, max_leads)))
            
            for business in businesses:
                if len(leads) >= max_leads:
                    break
                    
                # Check timeout
                if (time.monotonic() - start_time) > 30:
                    break
                
                # Extract email from website if available
                if business.get('website'):
                    try:
                        email = scraper.extract_email_from_website(business['website']) or ''
                        business['email'] = email
                    except Exception as e:
                        self.logger.debug(f"Email extraction failed for {business['website']}: {e}")
                        business['email'] = ''
                
                business['source'] = 'web_search'
                leads.append(business)
                
        except Exception as e:
            self.logger.error(f"Fallback path failed: {e}")
        
        return leads
    
    def _export_leads_csv(self, leads: list, csv_path: Path):
        """Export leads to CSV file"""
        try:
            fieldnames = ['name', 'email', 'phone', 'address', 'website', 'source']
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for lead in leads:
                    writer.writerow(lead)
                    
        except Exception as e:
            self.logger.error(f"Failed to export quick leads: {e}")
            raise
    
    def _display_results_summary(self, leads: list):
        """Display brief summary of results"""
        print(f"Quick leads generated: {len(leads)}")
        
        for i, lead in enumerate(leads[:5], 1):
            name = lead.get('name', 'N/A')
            email = lead.get('email', '')
            phone = lead.get('phone', '')
            website = lead.get('website', '')
            print(f"{i}. {name} | {email} | {phone} | {website}")