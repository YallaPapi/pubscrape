#!/usr/bin/env python3
"""
Production Lead Generator - Complete Working System
==================================================

Main entry point for the lead generation system that:
1. Uses Botasaurus for stealth scraping
2. Integrates Bing search for business discovery
3. Extracts and validates email addresses
4. Generates high-quality CSV leads ready for outreach

Usage:
    python lead_generator_main.py --query "optometrist Atlanta" --leads 50
    python lead_generator_main.py --config campaign.yaml
    python lead_generator_main.py --test

Requirements:
    - botasaurus>=4.0.0
    - All dependencies from requirements.txt
    - Working internet connection
"""

import os
import sys
import time
import json
import logging
import argparse
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

# Import YAML with fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not available. Configuration files will use JSON format.")

# Import our fixed components
from comprehensive_lead_generator import ComprehensiveLeadGenerator, Lead
from fixed_email_extractor import WorkingEmailExtractor, ContactInfo
from enhanced_email_validator import EnhancedEmailValidator, EmailValidationResult

# Import Botasaurus components  
try:
    from botasaurus.browser import browser, Driver
    from botasaurus import UserAgent, WindowSize
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    print("Warning: Botasaurus not available. Using fallback scraping method.")
    
    # Fallback mock decorator
    def browser(**kwargs):
        def decorator(func):
            return func
        return decorator
    
    class Driver:
        pass


@dataclass
class CampaignConfig:
    """Configuration for a lead generation campaign"""
    # Campaign basics
    name: str = "lead_campaign"
    description: str = ""
    
    # Search configuration
    search_queries: List[str] = field(default_factory=list)
    max_leads_per_query: int = 20
    max_pages_per_query: int = 3
    search_engine: str = "bing"  # bing, google, duckduckgo
    
    # Geographic targeting
    location: str = ""
    country_code: str = "US"
    language: str = "en"
    
    # Business filters
    business_types: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    min_business_score: float = 0.4
    
    # Email validation
    enable_email_validation: bool = True
    enable_dns_checking: bool = False  # Disabled for speed by default
    min_email_confidence: float = 0.5
    
    # Output configuration
    output_directory: str = "output"
    csv_filename: str = ""  # Auto-generated if empty
    include_report: bool = True
    
    # Performance settings
    max_concurrent_extractions: int = 3
    request_delay_seconds: float = 2.0
    timeout_seconds: int = 15
    max_retries: int = 2
    
    # Anti-detection
    use_rotating_user_agents: bool = True
    use_residential_proxies: bool = False
    headless_mode: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'search_queries': self.search_queries,
            'max_leads_per_query': self.max_leads_per_query,
            'max_pages_per_query': self.max_pages_per_query,
            'search_engine': self.search_engine,
            'location': self.location,
            'country_code': self.country_code,
            'language': self.language,
            'business_types': self.business_types,
            'exclude_keywords': self.exclude_keywords,
            'min_business_score': self.min_business_score,
            'enable_email_validation': self.enable_email_validation,
            'enable_dns_checking': self.enable_dns_checking,
            'min_email_confidence': self.min_email_confidence,
            'output_directory': self.output_directory,
            'csv_filename': self.csv_filename,
            'include_report': self.include_report,
            'max_concurrent_extractions': self.max_concurrent_extractions,
            'request_delay_seconds': self.request_delay_seconds,
            'timeout_seconds': self.timeout_seconds,
            'max_retries': self.max_retries,
            'use_rotating_user_agents': self.use_rotating_user_agents,
            'use_residential_proxies': self.use_residential_proxies,
            'headless_mode': self.headless_mode
        }


if BOTASAURUS_AVAILABLE:
    @browser(
        headless=True,
        user_agent_rotation=True,
        block_images=True,
        stealth=True,
        page_load_strategy='eager'
    )
    def scrape_bing_results(driver: Driver, query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Scrape Bing search results using Botasaurus for anti-detection"""
        return _scrape_bing_with_botasaurus(driver, query, max_pages)
else:
    def scrape_bing_results(query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Fallback scraping method using requests + BeautifulSoup"""
        return _scrape_bing_fallback(query, max_pages)


def _scrape_bing_with_botasaurus(driver: Driver, query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Scrape Bing search results using Botasaurus for anti-detection"""
    results = []
    
    try:
        import random
        # Construct search URL
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        
        for page in range(max_pages):
            try:
                # Navigate to search page
                if page == 0:
                    driver.get(search_url)
                else:
                    # Click next page or construct pagination URL
                    next_url = f"{search_url}&first={page * 10 + 1}"
                    driver.get(next_url)
                
                # Wait for results to load
                time.sleep(2)
                
                # Extract search results
                page_results = extract_search_results_botasaurus(driver, query, page + 1)
                results.extend(page_results)
                
                # Human-like delay between pages
                if page < max_pages - 1:
                    time.sleep(random.uniform(3, 6))
                    
            except Exception as e:
                logging.error(f"Error scraping page {page + 1}: {e}")
                break
                
    except Exception as e:
        logging.error(f"Error in Bing scraping: {e}")
    
    return results


def _scrape_bing_fallback(query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Fallback scraping method using requests + BeautifulSoup"""
    import requests
    from bs4 import BeautifulSoup
    import random
    
    results = []
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        for page in range(max_pages):
            try:
                # Construct search URL
                if page == 0:
                    search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
                else:
                    search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&first={page * 10 + 1}"
                
                # Make request
                response = session.get(search_url, timeout=10)
                if response.status_code != 200:
                    logging.warning(f"Bing returned status {response.status_code}")
                    break
                
                # Parse results
                soup = BeautifulSoup(response.text, 'html.parser')
                page_results = extract_search_results_fallback(soup, query, page + 1)
                results.extend(page_results)
                
                # Delay between pages
                if page < max_pages - 1:
                    time.sleep(random.uniform(2, 4))
                    
            except Exception as e:
                logging.error(f"Error scraping page {page + 1}: {e}")
                break
                
    except Exception as e:
        logging.error(f"Error in fallback Bing scraping: {e}")
    
    return results


def extract_search_results_botasaurus(driver: Driver, query: str, page_num: int) -> List[Dict[str, Any]]:
    """Extract search results from current page using Botasaurus driver"""
    results = []
    
    try:
        # Find all search result containers
        # Bing uses different selectors than Google
        result_selectors = [
            'li.b_algo',
            '.b_algo',
            'li[class*="algo"]',
            'div.b_title',
        ]
        
        search_results = None
        for selector in result_selectors:
            try:
                search_results = driver.find_elements_by_css_selector(selector)
                if search_results:
                    break
            except:
                continue
        
        if not search_results:
            logging.warning(f"No search results found on page {page_num}")
            return results
        
        for i, result in enumerate(search_results[:10]):  # Top 10 results per page
            try:
                # Extract title
                title_element = None
                title_selectors = ['h2 a', 'h3 a', '.b_title a', 'a']
                for selector in title_selectors:
                    try:
                        title_element = result.find_element_by_css_selector(selector)
                        break
                    except:
                        continue
                
                if not title_element:
                    continue
                
                title = title_element.text.strip()
                url = title_element.get_attribute('href')
                
                if not url or not url.startswith('http'):
                    continue
                
                # Extract description
                description = ""
                desc_selectors = ['.b_caption p', '.b_dsc', 'p', '.snippet']
                for selector in desc_selectors:
                    try:
                        desc_element = result.find_element_by_css_selector(selector)
                        description = desc_element.text.strip()
                        break
                    except:
                        continue
                
                # Extract domain for business categorization
                domain = urlparse(url).netloc.lower()
                
                # Basic business detection
                is_business = detect_business_relevance(title, description, url, query)
                
                result_data = {
                    'title': title,
                    'url': url,
                    'description': description,
                    'domain': domain,
                    'query': query,
                    'page': page_num,
                    'position': i + 1,
                    'is_business': is_business,
                    'extracted_at': time.time()
                }
                
                results.append(result_data)
                
            except Exception as e:
                logging.debug(f"Error extracting result {i}: {e}")
                continue
    
    except Exception as e:
        logging.error(f"Error extracting search results: {e}")
    
    return results


def extract_search_results_fallback(soup, query: str, page_num: int) -> List[Dict[str, Any]]:
    """Extract search results from current page using BeautifulSoup"""
    results = []
    
    try:
        # Find all search result containers
        result_selectors = [
            'li.b_algo',
            '.b_algo',
            'li[class*="algo"]',
        ]
        
        search_results = None
        for selector in result_selectors:
            search_results = soup.select(selector)
            if search_results:
                break
        
        if not search_results:
            logging.warning(f"No search results found on page {page_num}")
            return results
        
        for i, result in enumerate(search_results[:10]):  # Top 10 results per page
            try:
                # Extract title and URL
                title_element = result.select_one('h2 a, h3 a, .b_title a, a')
                if not title_element:
                    continue
                
                title = title_element.get_text(strip=True)
                url = title_element.get('href', '')
                
                if not url or not url.startswith('http'):
                    continue
                
                # Extract description
                description = ""
                desc_element = result.select_one('.b_caption p, .b_dsc, p')
                if desc_element:
                    description = desc_element.get_text(strip=True)
                
                # Extract domain for business categorization
                domain = urlparse(url).netloc.lower()
                
                # Basic business detection
                is_business = detect_business_relevance(title, description, url, query)
                
                result_data = {
                    'title': title,
                    'url': url,
                    'description': description,
                    'domain': domain,
                    'query': query,
                    'page': page_num,
                    'position': i + 1,
                    'is_business': is_business,
                    'extracted_at': time.time()
                }
                
                results.append(result_data)
                
            except Exception as e:
                logging.debug(f"Error extracting result {i}: {e}")
                continue
    
    except Exception as e:
        logging.error(f"Error extracting search results: {e}")
    
    return results


def detect_business_relevance(title: str, description: str, url: str, query: str) -> bool:
    """Detect if a search result is a relevant business"""
    # Business indicators
    business_indicators = [
        'contact', 'about', 'services', 'location', 'phone', 'email',
        'hours', 'appointment', 'consultation', 'clinic', 'office',
        'practice', 'company', 'business', 'professional', 'service'
    ]
    
    # Exclude patterns
    exclude_patterns = [
        'wikipedia', 'facebook.com', 'twitter.com', 'instagram.com',
        'linkedin.com', 'youtube.com', 'yelp.com', 'google.com',
        'directory', 'listing', 'review', 'forum', 'blog'
    ]
    
    text_to_check = f"{title} {description}".lower()
    url_lower = url.lower()
    
    # Check for exclusions first
    for pattern in exclude_patterns:
        if pattern in url_lower or pattern in text_to_check:
            return False
    
    # Check for business indicators
    indicator_count = sum(1 for indicator in business_indicators 
                         if indicator in text_to_check)
    
    # More indicators = more likely to be business
    return indicator_count >= 2


class ProductionLeadGenerator:
    """Production-ready lead generation system"""
    
    def __init__(self, config: CampaignConfig):
        self.config = config
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.lead_generator = ComprehensiveLeadGenerator(
            output_dir=config.output_directory
        )
        
        # Setup output directory
        self.output_dir = Path(config.output_directory)
        self.output_dir.mkdir(exist_ok=True)
        
        # Campaign statistics
        self.stats = {
            'campaign_start_time': time.time(),
            'queries_processed': 0,
            'urls_discovered': 0,
            'leads_extracted': 0,
            'leads_validated': 0,
            'final_leads': 0,
            'errors': 0
        }
        
        self.logger.info(f"Production Lead Generator initialized: {config.name}")
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = Path(self.config.output_directory) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"lead_generation_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def run_campaign(self) -> Dict[str, Any]:
        """Execute the complete lead generation campaign"""
        start_time = time.time()
        
        self.logger.info(f"Starting campaign: {self.config.name}")
        self.logger.info(f"Queries: {len(self.config.search_queries)}")
        self.logger.info(f"Target leads per query: {self.config.max_leads_per_query}")
        
        try:
            # Step 1: Discover business URLs from search
            all_urls = self.discover_business_urls()
            
            # Step 2: Extract leads from URLs
            leads = self.extract_leads_from_urls(all_urls)
            
            # Step 3: Filter and validate leads
            final_leads = self.filter_and_validate_leads(leads)
            
            # Step 4: Export results
            results = self.export_results(final_leads)
            
            # Step 5: Generate report
            if self.config.include_report:
                report = self.generate_campaign_report(final_leads)
                results['report'] = report
            
            campaign_time = time.time() - start_time
            self.stats['total_campaign_time'] = campaign_time
            
            self.logger.info(f"Campaign completed in {campaign_time:.2f} seconds")
            self.logger.info(f"Final leads generated: {len(final_leads)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Campaign failed: {e}")
            raise
    
    def discover_business_urls(self) -> List[str]:
        """Discover business URLs from search queries"""
        self.logger.info("Starting business URL discovery")
        
        all_urls = []
        
        for i, query in enumerate(self.config.search_queries, 1):
            self.logger.info(f"Processing query {i}/{len(self.config.search_queries)}: {query}")
            
            try:
                # Add location to query if specified
                search_query = query
                if self.config.location:
                    search_query = f"{query} {self.config.location}"
                
                # Scrape search results
                search_results = scrape_bing_results(
                    search_query, 
                    max_pages=self.config.max_pages_per_query
                )
                
                # Filter for business URLs
                business_urls = []
                for result in search_results:
                    if result.get('is_business', False):
                        url = result['url']
                        if self.is_valid_business_url(url):
                            business_urls.append(url)
                
                # Limit per query
                business_urls = business_urls[:self.config.max_leads_per_query]
                
                self.logger.info(f"  Found {len(business_urls)} business URLs")
                all_urls.extend(business_urls)
                self.stats['queries_processed'] += 1
                self.stats['urls_discovered'] += len(business_urls)
                
                # Delay between queries
                if i < len(self.config.search_queries):
                    time.sleep(self.config.request_delay_seconds)
                    
            except Exception as e:
                self.logger.error(f"Error processing query '{query}': {e}")
                self.stats['errors'] += 1
                continue
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in all_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        self.logger.info(f"Total unique business URLs: {len(unique_urls)}")
        return unique_urls
    
    def is_valid_business_url(self, url: str) -> bool:
        """Check if URL is valid for business lead extraction"""
        try:
            parsed = urlparse(url)
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Must have domain
            if not parsed.netloc:
                return False
            
            # Exclude social media and directories
            excluded_domains = [
                'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
                'youtube.com', 'yelp.com', 'yellowpages.com', 'google.com',
                'wikipedia.org', 'reddit.com', 'pinterest.com'
            ]
            
            domain = parsed.netloc.lower()
            for excluded in excluded_domains:
                if excluded in domain:
                    return False
            
            # Check exclude keywords
            url_lower = url.lower()
            for keyword in self.config.exclude_keywords:
                if keyword.lower() in url_lower:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def extract_leads_from_urls(self, urls: List[str]) -> List[Lead]:
        """Extract leads from business URLs"""
        self.logger.info(f"Extracting leads from {len(urls)} URLs")
        
        # Combine source queries for context
        source_query = "; ".join(self.config.search_queries)
        
        # Use the comprehensive lead generator
        leads = self.lead_generator.generate_leads_from_urls(urls, source_query)
        
        self.stats['leads_extracted'] = len(leads)
        self.logger.info(f"Extracted {len(leads)} initial leads")
        
        return leads
    
    def filter_and_validate_leads(self, leads: List[Lead]) -> List[Lead]:
        """Filter and validate leads based on campaign criteria"""
        self.logger.info(f"Filtering and validating {len(leads)} leads")
        
        filtered_leads = []
        
        for lead in leads:
            # Apply business score filter
            if lead.lead_score < self.config.min_business_score:
                continue
            
            # Apply email confidence filter
            if lead.email_confidence < self.config.min_email_confidence:
                continue
            
            # Check business type filters
            if self.config.business_types:
                business_name_lower = lead.business_name.lower()
                if not any(btype.lower() in business_name_lower 
                          for btype in self.config.business_types):
                    continue
            
            # Check exclude keywords
            if self.config.exclude_keywords:
                text_to_check = f"{lead.business_name} {lead.contact_name}".lower()
                if any(keyword.lower() in text_to_check 
                       for keyword in self.config.exclude_keywords):
                    continue
            
            filtered_leads.append(lead)
        
        self.stats['leads_validated'] = len(filtered_leads)
        self.logger.info(f"Filtered to {len(filtered_leads)} qualified leads")
        
        return filtered_leads
    
    def export_results(self, leads: List[Lead]) -> Dict[str, Any]:
        """Export leads to CSV and return file paths"""
        self.logger.info(f"Exporting {len(leads)} leads to CSV")
        
        # Generate filename if not specified
        if not self.config.csv_filename:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            safe_name = "".join(c for c in self.config.name if c.isalnum() or c in (' ', '-', '_'))
            safe_name = safe_name.replace(' ', '_')
            self.config.csv_filename = f"{safe_name}_{timestamp}.csv"
        
        # Export to CSV
        csv_path = self.lead_generator.export_leads_to_csv(leads, self.config.csv_filename)
        
        self.stats['final_leads'] = len(leads)
        
        results = {
            'csv_file': str(csv_path),
            'total_leads': len(leads),
            'campaign_config': self.config.to_dict(),
            'statistics': self.stats.copy()
        }
        
        # Save campaign metadata
        metadata_file = csv_path.parent / f"{csv_path.stem}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        results['metadata_file'] = str(metadata_file)
        
        self.logger.info(f"Results exported:")
        self.logger.info(f"  CSV: {csv_path}")
        self.logger.info(f"  Metadata: {metadata_file}")
        
        return results
    
    def generate_campaign_report(self, leads: List[Lead]) -> Dict[str, Any]:
        """Generate comprehensive campaign report"""
        report = self.lead_generator.generate_report(leads)
        
        # Add campaign-specific information
        report['campaign'] = {
            'name': self.config.name,
            'description': self.config.description,
            'queries': self.config.search_queries,
            'location': self.config.location,
            'execution_time': time.time() - self.stats['campaign_start_time']
        }
        
        report['performance'] = self.stats.copy()
        
        # Save report
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"campaign_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Campaign report saved: {report_file}")
        return report


def load_config_from_file(config_file: str) -> CampaignConfig:
    """Load campaign configuration from YAML or JSON file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            if (config_file.endswith('.yaml') or config_file.endswith('.yml')) and YAML_AVAILABLE:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return CampaignConfig(**data)
        
    except Exception as e:
        raise ValueError(f"Error loading config file '{config_file}': {e}")


def create_sample_config(output_file: str = None):
    """Create a sample campaign configuration file"""
    if output_file is None:
        if YAML_AVAILABLE:
            output_file = "sample_campaign.yaml"
        else:
            output_file = "sample_campaign.json"
    sample_config = CampaignConfig(
        name="optometrist_atlanta_campaign",
        description="Lead generation for optometrists in Atlanta area",
        search_queries=[
            "optometrist Atlanta",
            "eye doctor Atlanta", 
            "vision care Atlanta",
            "ophthalmologist Atlanta"
        ],
        max_leads_per_query=25,
        max_pages_per_query=3,
        location="Atlanta, GA",
        business_types=["optometry", "eye care", "vision", "ophthalmology"],
        exclude_keywords=["yelp", "reviews", "directory", "wikipedia"],
        min_business_score=0.5,
        min_email_confidence=0.6,
        enable_email_validation=True,
        enable_dns_checking=False,
        output_directory="campaign_output",
        include_report=True,
        max_concurrent_extractions=3,
        request_delay_seconds=2.5,
        timeout_seconds=20,
        use_rotating_user_agents=True,
        headless_mode=True
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        if output_file.endswith('.yaml') or output_file.endswith('.yml'):
            if YAML_AVAILABLE:
                yaml.dump(sample_config.to_dict(), f, default_flow_style=False, indent=2)
            else:
                json.dump(sample_config.to_dict(), f, indent=2)
        else:
            json.dump(sample_config.to_dict(), f, indent=2)
    
    print(f"Sample configuration saved to: {output_file}")
    return output_file


def run_test_campaign():
    """Run a small test campaign to verify the system works"""
    print("Running test campaign...")
    
    test_config = CampaignConfig(
        name="test_campaign",
        description="Test campaign to verify system functionality",
        search_queries=["optometrist Atlanta"],
        max_leads_per_query=5,
        max_pages_per_query=1,
        location="Atlanta",
        output_directory="test_output",
        include_report=True,
        request_delay_seconds=1.0,
        timeout_seconds=10
    )
    
    generator = ProductionLeadGenerator(test_config)
    
    try:
        results = generator.run_campaign()
        
        print(f"\nTest Campaign Results:")
        print(f"  CSV File: {results['csv_file']}")
        print(f"  Total Leads: {results['total_leads']}")
        print(f"  Success: {results['total_leads'] > 0}")
        
        if results['total_leads'] > 0:
            print(f"\nSUCCESS: Lead generation system is working!")
            print(f"   Generated {results['total_leads']} test leads")
            print(f"   Ready for production campaigns")
        else:
            print(f"\nWARNING: No leads generated in test")
            print(f"   Check configuration and network connectivity")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: Test campaign failed: {e}")
        logging.error(f"Test campaign error: {e}", exc_info=True)
        return False


def main():
    """Main entry point for the lead generation system"""
    parser = argparse.ArgumentParser(
        description="Production Lead Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lead_generator_main.py --test
  python lead_generator_main.py --query "optometrist Atlanta" --leads 50
  python lead_generator_main.py --config campaign.yaml
  python lead_generator_main.py --sample-config
        """
    )
    
    parser.add_argument('--config', type=str, help='Campaign configuration file (YAML/JSON)')
    parser.add_argument('--query', type=str, help='Search query for quick campaign')
    parser.add_argument('--leads', type=int, default=25, help='Number of leads to generate')
    parser.add_argument('--location', type=str, default='', help='Geographic location')
    parser.add_argument('--output', type=str, default='output', help='Output directory')
    parser.add_argument('--test', action='store_true', help='Run test campaign')
    parser.add_argument('--sample-config', action='store_true', help='Create sample config file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create sample config
        if args.sample_config:
            sample_file = create_sample_config()
            print(f"Sample configuration created: {sample_file}")
            print("Edit the file and run: python lead_generator_main.py --config {sample_file}")
            return 0
        
        # Run test campaign
        if args.test:
            success = run_test_campaign()
            return 0 if success else 1
        
        # Load configuration
        if args.config:
            config = load_config_from_file(args.config)
            print(f"Loaded configuration from: {args.config}")
        elif args.query:
            # Quick campaign from command line
            config = CampaignConfig(
                name=f"quick_campaign_{int(time.time())}",
                description=f"Quick campaign for: {args.query}",
                search_queries=[args.query],
                max_leads_per_query=args.leads,
                location=args.location,
                output_directory=args.output,
                include_report=True
            )
            print(f"Created quick campaign: {args.query}")
        else:
            parser.print_help()
            print(f"\nERROR: Must specify --config, --query, --test, or --sample-config")
            return 1
        
        # Run the campaign
        print(f"\n{'='*60}")
        print(f"PRODUCTION LEAD GENERATION SYSTEM")
        print(f"{'='*60}")
        print(f"Campaign: {config.name}")
        print(f"Queries: {len(config.search_queries)}")
        print(f"Target Leads: {config.max_leads_per_query} per query")
        print(f"Output: {config.output_directory}")
        print(f"{'='*60}")
        
        generator = ProductionLeadGenerator(config)
        results = generator.run_campaign()
        
        # Display results
        print(f"\n{'='*60}")
        print(f"CAMPAIGN COMPLETED SUCCESSFULLY")
        print(f"{'='*60}")
        print(f"CSV File: {results['csv_file']}")
        print(f"Total Leads: {results['total_leads']}")
        print(f"Metadata: {results.get('metadata_file', 'N/A')}")
        
        if 'report' in results:
            summary = results['report']['generation_summary']
            print(f"\nLead Quality Summary:")
            print(f"  Actionable Leads: {summary['actionable_leads']}")
            print(f"  Success Rate: {summary['actionable_rate']:.1f}%")
            print(f"  Avg Lead Score: {summary['avg_lead_score']:.2f}")
            print(f"  Avg Completeness: {summary['avg_data_completeness']:.2f}")
        
        print(f"\nSUCCESS: Campaign completed!")
        print(f"   Leads are ready for outreach campaigns")
        print(f"   Import the CSV file into your CRM or email tool")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\nCampaign interrupted by user")
        return 1
    except Exception as e:
        print(f"\nERROR: Campaign failed: {e}")
        logging.error(f"Campaign error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())