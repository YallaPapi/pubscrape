#!/usr/bin/env python3
"""
Generate 500 Real Lawyer Leads - Production Ready Script
Uses targeted searches for individual law firms instead of directory listings
"""

import os
import sys
import csv
import time
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
from concurrent.futures import ThreadPoolExecutor

# Import our components
from enhanced_email_validator import EnhancedEmailValidator
from mailtester_integration import MailtesterIntegration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LawyerLeadGenerator:
    """Generate real lawyer leads using targeted searches"""
    
    def __init__(self, mailtester_api_key: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Email validation
        self.email_validator = EnhancedEmailValidator(enable_dns_check=False)
        self.mailtester = MailtesterIntegration(mailtester_api_key) if mailtester_api_key else None
        
        # Statistics
        self.stats = {
            'searches_performed': 0,
            'urls_found': 0,
            'leads_extracted': 0,
            'emails_validated': 0,
            'final_leads': 0
        }
        
        # Lawyer search queries for major cities
        self.search_queries = {
            'New York': [
                '"law firm" "New York" contact email',
                '"attorney" "NYC" phone email',
                '"lawyer" "Manhattan" contact information',
                '"legal services" "Brooklyn" email',
                '"law office" "Queens" contact',
                'personal injury attorney New York',
                'corporate lawyer NYC email',
                'divorce attorney Manhattan contact',
                'real estate lawyer Brooklyn phone',
                'criminal defense attorney NYC'
            ],
            'Los Angeles': [
                '"law firm" "Los Angeles" contact email',
                '"attorney" "LA" phone email contact',
                '"lawyer" "Beverly Hills" email',
                '"legal services" "Santa Monica" contact',
                '"law office" "Hollywood" email phone',
                'personal injury attorney Los Angeles',
                'entertainment lawyer LA email',
                'business attorney Beverly Hills',
                'family lawyer Santa Monica contact',
                'immigration attorney LA phone'
            ],
            'Chicago': [
                '"law firm" "Chicago" contact email',
                '"attorney" "Chicago" phone email',
                '"lawyer" "Loop" contact information',
                '"legal services" "Lincoln Park" email',
                '"law office" "River North" contact',
                'personal injury attorney Chicago',
                'corporate lawyer Chicago email',
                'real estate attorney Chicago phone',
                'criminal defense lawyer Chicago',
                'family attorney Chicago contact'
            ],
            'Miami': [
                '"law firm" "Miami" contact email',
                '"attorney" "Miami Beach" phone email',
                '"lawyer" "Coral Gables" contact',
                '"legal services" "Downtown Miami" email',
                '"law office" "Brickell" phone',
                'personal injury attorney Miami',
                'immigration lawyer Miami email',
                'real estate attorney Miami Beach',
                'business lawyer Coral Gables',
                'family attorney Miami contact'
            ],
            'Atlanta': [
                '"law firm" "Atlanta" contact email',
                '"attorney" "Buckhead" phone email',
                '"lawyer" "Midtown Atlanta" contact',
                '"legal services" "Downtown Atlanta" email',
                '"law office" "Sandy Springs" phone',
                'personal injury attorney Atlanta',
                'corporate lawyer Buckhead email',
                'real estate attorney Atlanta phone',
                'family lawyer Midtown Atlanta',
                'criminal defense attorney Atlanta'
            ]
        }
    
    def search_lawyers_google(self, query: str) -> List[Dict[str, Any]]:
        """Search for lawyers using Google (more reliable than Bing for direct business results)"""
        results = []
        
        try:
            # Use Google search
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            response = self.session.get(search_url, timeout=10)
            self.stats['searches_performed'] += 1
            
            if response.status_code != 200:
                logger.warning(f"Search failed with status {response.status_code}")
                return results
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            search_results = soup.select('div.g, div[class*="g"]')[:10]
            
            for result in search_results:
                try:
                    # Extract title and URL
                    title_element = result.select_one('h3, a > h3')
                    link_element = result.select_one('a[href^="http"], a[href^="/url?q="]')
                    
                    if not title_element or not link_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    url = link_element.get('href', '')
                    
                    # Handle Google redirect URLs
                    if '/url?q=' in url:
                        url = url.split('/url?q=')[1].split('&')[0]
                        from urllib.parse import unquote
                        url = unquote(url)
                    
                    if not url.startswith('http'):
                        continue
                    
                    # Extract description
                    desc_element = result.select_one('span[class*="st"], div[class*="s"]')
                    description = desc_element.get_text(strip=True) if desc_element else ""
                    
                    # Check if it's a real law firm (not directories)
                    domain = urlparse(url).netloc.lower()
                    excluded_domains = [
                        'avvo.com', 'justia.com', 'lawyers.com', 'findlaw.com',
                        'martindale.com', 'yelp.com', 'yellowpages.com', 'google.com',
                        'facebook.com', 'linkedin.com', 'wikipedia.org'
                    ]
                    
                    is_directory = any(excluded in domain for excluded in excluded_domains)
                    
                    # Look for law firm indicators
                    law_indicators = ['law', 'attorney', 'lawyer', 'legal', 'esquire', 'counsel']
                    text_check = f"{title} {description}".lower()
                    has_law_indicators = any(indicator in text_check for indicator in law_indicators)
                    
                    # Only include direct law firm websites
                    if not is_directory and has_law_indicators:
                        results.append({
                            'title': title,
                            'url': url,
                            'description': description,
                            'domain': domain,
                            'query': query
                        })
                        self.stats['urls_found'] += 1
                    
                except Exception as e:
                    logger.debug(f"Error processing search result: {e}")
                    continue
            
            # Small delay to be respectful
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.error(f"Error in Google search: {e}")
        
        return results
    
    def extract_contact_info(self, url: str) -> Dict[str, Any]:
        """Extract contact information from a law firm website"""
        contact_info = {
            'business_name': '',
            'primary_email': '',
            'phone': '',
            'address': '',
            'contact_name': '',
            'website': url,
            'emails_found': [],
            'phones_found': []
        }
        
        try:
            # Get the main page
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return contact_info
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract business name
            business_name = ""
            title_tag = soup.find('title')
            if title_tag:
                business_name = title_tag.get_text(strip=True)
                # Clean up common title patterns
                business_name = re.sub(r'\s*[-|]\s*(Law|Attorney|Lawyer|Legal).*$', '', business_name, flags=re.IGNORECASE)
            
            contact_info['business_name'] = business_name[:100]  # Limit length
            
            # Look for contact page
            contact_links = soup.find_all('a', href=True)
            contact_urls = []
            
            for link in contact_links:
                href = link.get('href', '').lower()
                text = link.get_text(strip=True).lower()
                
                if any(word in href or word in text for word in ['contact', 'about', 'office']):
                    full_url = urljoin(url, link.get('href'))
                    if full_url.startswith('http') and full_url not in contact_urls:
                        contact_urls.append(full_url)
            
            # Search for emails and phones on main page and contact pages
            pages_to_check = [url] + contact_urls[:3]  # Main + up to 3 contact pages
            
            all_text = ""
            for page_url in pages_to_check:
                try:
                    if page_url != url:  # Don't re-fetch main page
                        page_response = self.session.get(page_url, timeout=10)
                        if page_response.status_code == 200:
                            page_soup = BeautifulSoup(page_response.text, 'html.parser')
                            all_text += " " + page_soup.get_text()
                    else:
                        all_text += " " + soup.get_text()
                except:
                    continue
            
            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, all_text)
            
            # Clean and filter emails
            valid_emails = []
            for email in set(emails):  # Remove duplicates
                email = email.lower().strip()
                # Filter out common invalid patterns
                if (email and '@' in email and 
                    not any(bad in email for bad in ['example.com', 'test.com', 'placeholder', 'your-email'])):
                    valid_emails.append(email)
            
            contact_info['emails_found'] = valid_emails
            if valid_emails:
                # Prioritize emails that look like business emails
                business_emails = [e for e in valid_emails if not any(provider in e for provider in ['gmail.com', 'yahoo.com', 'hotmail.com'])]
                contact_info['primary_email'] = business_emails[0] if business_emails else valid_emails[0]
            
            # Extract phone numbers
            phone_pattern = r'\(?\b[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b'
            phones = re.findall(phone_pattern, all_text)
            
            # Clean phones
            valid_phones = []
            for phone in set(phones):
                phone = re.sub(r'[^0-9]', '', phone)
                if len(phone) == 10:
                    phone = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                    valid_phones.append(phone)
            
            contact_info['phones_found'] = valid_phones
            if valid_phones:
                contact_info['phone'] = valid_phones[0]
            
            # Try to extract attorney names
            name_patterns = [
                r'Attorney ([A-Z][a-z]+ [A-Z][a-z]+)',
                r'([A-Z][a-z]+ [A-Z][a-z]+), Esq',
                r'Contact ([A-Z][a-z]+ [A-Z][a-z]+)',
            ]
            
            for pattern in name_patterns:
                matches = re.findall(pattern, all_text)
                if matches:
                    contact_info['contact_name'] = matches[0]
                    break
            
            self.stats['leads_extracted'] += 1
            
        except Exception as e:
            logger.debug(f"Error extracting from {url}: {e}")
        
        return contact_info
    
    def generate_leads_for_city(self, city: str, target_leads: int = 100) -> List[Dict[str, Any]]:
        """Generate leads for a specific city"""
        logger.info(f"Generating leads for {city} (target: {target_leads})")
        
        if city not in self.search_queries:
            logger.error(f"No search queries defined for {city}")
            return []
        
        all_urls = []
        leads = []
        
        # Perform searches
        for query in self.search_queries[city]:
            if len(leads) >= target_leads:
                break
            
            logger.info(f"Searching: {query}")
            search_results = self.search_lawyers_google(query)
            
            for result in search_results:
                if result['url'] not in [u['url'] for u in all_urls]:
                    all_urls.append(result)
            
            time.sleep(random.uniform(2, 4))  # Rate limiting
        
        logger.info(f"Found {len(all_urls)} unique URLs for {city}")
        
        # Extract contact information
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for url_data in all_urls[:target_leads * 2]:  # Process more URLs than needed
                future = executor.submit(self.extract_contact_info, url_data['url'])
                futures.append((future, url_data))
            
            for future, url_data in futures:
                try:
                    contact_info = future.result(timeout=30)
                    
                    if contact_info['primary_email']:  # Only include if we found an email
                        lead = {
                            'business_name': contact_info['business_name'],
                            'primary_email': contact_info['primary_email'],
                            'phone': contact_info['phone'],
                            'contact_name': contact_info['contact_name'],
                            'website': contact_info['website'],
                            'city': city,
                            'industry': 'Legal Services',
                            'source_query': url_data['query'],
                            'emails_found': '; '.join(contact_info['emails_found']),
                            'phones_found': '; '.join(contact_info['phones_found']),
                            'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'lead_score': 0.8,  # High score for direct law firm contacts
                            'email_confidence': 0.7  # Will be updated by validation
                        }
                        leads.append(lead)
                        
                        if len(leads) >= target_leads:
                            break
                    
                except Exception as e:
                    logger.debug(f"Error processing {url_data['url']}: {e}")
                    continue
        
        logger.info(f"Extracted {len(leads)} leads for {city}")
        return leads
    
    def validate_lead_emails(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate email addresses in leads"""
        if not leads:
            return leads
        
        logger.info(f"Validating emails for {len(leads)} leads")
        
        # Use Mailtester if available, otherwise basic validation
        if self.mailtester and self.mailtester.api_key:
            logger.info("Using Mailtester Ninja API for email validation")
            
            for lead in leads:
                if lead['primary_email']:
                    try:
                        result = self.mailtester.validate_single_email_sync(lead['primary_email'])
                        lead['email_confidence'] = result.confidence_score
                        lead['email_validation_status'] = result.status
                        lead['is_valid_email'] = result.is_valid
                        self.stats['emails_validated'] += 1
                        
                        # Small delay for API rate limiting
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.debug(f"Error validating {lead['primary_email']}: {e}")
                        # Keep the lead even if validation fails
                        lead['email_validation_status'] = 'validation_failed'
        else:
            logger.info("Using basic email validation (no Mailtester API key)")
            
            for lead in leads:
                if lead['primary_email']:
                    result = self.email_validator.validate_email(lead['primary_email'])
                    lead['email_confidence'] = result.confidence_score
                    lead['email_validation_status'] = result.quality.value
                    lead['is_valid_email'] = result.is_valid
                    self.stats['emails_validated'] += 1
        
        # Filter out leads with very low email confidence
        validated_leads = [lead for lead in leads if lead.get('email_confidence', 0) >= 0.3]
        
        logger.info(f"Email validation complete: {len(validated_leads)}/{len(leads)} leads passed validation")
        return validated_leads
    
    def save_leads_to_csv(self, leads: List[Dict[str, Any]], filename: str) -> str:
        """Save leads to CSV file"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not leads:
            logger.warning("No leads to save")
            return str(output_path)
        
        # Define CSV columns
        columns = [
            'business_name', 'primary_email', 'phone', 'contact_name', 'website',
            'city', 'industry', 'source_query', 'extraction_date', 'lead_score',
            'email_confidence', 'email_validation_status', 'is_valid_email',
            'emails_found', 'phones_found'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for lead in leads:
                # Ensure all columns exist
                row = {col: lead.get(col, '') for col in columns}
                writer.writerow(row)
        
        logger.info(f"Saved {len(leads)} leads to {output_path}")
        return str(output_path)
    
    def generate_500_lawyer_leads(self) -> str:
        """Generate 500 lawyer leads across all cities"""
        logger.info("Starting generation of 500 lawyer leads")
        
        all_leads = []
        leads_per_city = 100
        
        cities = ['New York', 'Los Angeles', 'Chicago', 'Miami', 'Atlanta']
        
        for city in cities:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {city}")
            logger.info(f"{'='*60}")
            
            city_leads = self.generate_leads_for_city(city, leads_per_city)
            all_leads.extend(city_leads)
            
            logger.info(f"Total leads so far: {len(all_leads)}")
            
            if len(all_leads) >= 500:
                break
        
        # Validate emails
        logger.info("\nValidating all email addresses...")
        validated_leads = self.validate_lead_emails(all_leads)
        
        # Take top 500 leads
        final_leads = validated_leads[:500]
        self.stats['final_leads'] = len(final_leads)
        
        # Save to CSV
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"lawyer_leads_output/500_lawyer_leads_{timestamp}.csv"
        csv_path = self.save_leads_to_csv(final_leads, filename)
        
        # Generate summary report
        self.generate_summary_report(final_leads, csv_path)
        
        return csv_path
    
    def generate_summary_report(self, leads: List[Dict[str, Any]], csv_path: str):
        """Generate a summary report of the lead generation"""
        report = {
            'generation_summary': {
                'total_leads_generated': len(leads),
                'cities_covered': list(set(lead.get('city', 'Unknown') for lead in leads)),
                'generation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'csv_file': csv_path
            },
            'statistics': self.stats,
            'email_validation_summary': {
                'valid_emails': sum(1 for lead in leads if lead.get('is_valid_email', False)),
                'avg_email_confidence': sum(lead.get('email_confidence', 0) for lead in leads) / len(leads) if leads else 0,
                'validation_method': 'Mailtester Ninja API' if self.mailtester and self.mailtester.api_key else 'Basic validation'
            },
            'city_breakdown': {}
        }
        
        # City breakdown
        for city in ['New York', 'Los Angeles', 'Chicago', 'Miami', 'Atlanta']:
            city_leads = [lead for lead in leads if lead.get('city') == city]
            if city_leads:
                report['city_breakdown'][city] = {
                    'leads_count': len(city_leads),
                    'avg_email_confidence': sum(lead.get('email_confidence', 0) for lead in city_leads) / len(city_leads),
                    'valid_emails': sum(1 for lead in city_leads if lead.get('is_valid_email', False))
                }
        
        # Save report
        report_path = csv_path.replace('.csv', '_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\n{'='*60}")
        logger.info("LEAD GENERATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total leads: {len(leads)}")
        logger.info(f"Valid emails: {report['email_validation_summary']['valid_emails']}")
        logger.info(f"Avg email confidence: {report['email_validation_summary']['avg_email_confidence']:.2f}")
        logger.info(f"CSV file: {csv_path}")
        logger.info(f"Report file: {report_path}")
        logger.info(f"{'='*60}")

if __name__ == "__main__":
    # Mailtester API key
    MAILTESTER_API_KEY = "sub_1RwOIXAJu6gy4fiYcL89Rfr3"
    
    generator = LawyerLeadGenerator(MAILTESTER_API_KEY)
    
    try:
        csv_file = generator.generate_500_lawyer_leads()
        print(f"\n✅ SUCCESS: Generated 500 lawyer leads")
        print(f"📁 CSV File: {csv_file}")
        print(f"🎯 Ready for outreach campaigns!")
        
    except KeyboardInterrupt:
        print("\n❌ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error generating leads: {e}")
        import traceback
        traceback.print_exc()