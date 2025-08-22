#!/usr/bin/env python3
"""
Direct Lawyer Lead Generator - Extract leads from specific law firm websites
Uses a targeted list of law firm domains to ensure high-quality results
"""

import os
import csv
import time
import json
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any

# Import email validation
from mailtester_integration import MailtesterIntegration

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectLawyerLeadGenerator:
    """Generate lawyer leads by directly scraping known law firm websites"""
    
    def __init__(self, mailtester_api_key: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self.mailtester = MailtesterIntegration(mailtester_api_key) if mailtester_api_key else None
        
        # Statistics
        self.stats = {
            'websites_processed': 0,
            'successful_extractions': 0,
            'emails_found': 0,
            'phones_found': 0,
            'validation_attempts': 0,
            'valid_emails': 0
        }
        
        # Law firm websites by city (real, known firms)
        self.law_firm_websites = {
            'New York': [
                'https://www.sullcrom.com',
                'https://www.skadden.com', 
                'https://www.lw.com',
                'https://www.whitecase.com',
                'https://www.shearman.com',
                'https://www.cravath.com',
                'https://www.clearygottlieb.com',
                'https://www.dwt.com',
                'https://www.paulweiss.com',
                'https://www.wlrk.com',
                'https://www.cahill.com',
                'https://www.kramerlevin.com',
                'https://www.stroock.com',
                'https://www.proskauer.com',
                'https://www.goodwinlaw.com',
                'https://www.mofo.com',
                'https://www.orrick.com',
                'https://www.whitecase.com',
                'https://www.jw.com',
                'https://www.milbank.com',
                # Smaller NYC firms
                'https://www.tarter.com',
                'https://www.abramsonlaw.net',
                'https://www.lawrubenstein.com',
                'https://www.nolan-lawfirm.com',
                'https://www.kraemerlaw.com',
                'https://www.newyorkinjuryattorney.com',
                'https://www.levylaw.com',
                'https://www.cellino.com',
                'https://www.rosenberglaw.com',
                'https://www.garfinkellawfirm.com',
                'https://www.parnialaw.com',
                'https://www.jacobylaw.com',
                'https://www.fchgroup.com',
                'https://www.chaikinlaw.com',
                'https://www.rossfellercasey.com',
                'https://www.steinberglaw.com',
                'https://www.personalinjurynyc.com',
                'https://www.attorneymonohan.com',
                'https://www.newyorkpersonalinjurylawyer.com',
                'https://www.wingaterealtorlaw.com'
            ],
            'Los Angeles': [
                'https://www.lw.com',
                'https://www.goodwinlaw.com',
                'https://www.irell.com',
                'https://www.omm.com',
                'https://www.munger.com',
                'https://www.loeb.com',
                'https://www.mofo.com',
                'https://www.orrick.com',
                'https://www.sheppardmullin.com',
                'https://www.paulhastings.com',
                'https://www.girardgibbs.com',
                'https://www.greenbergtraurig.com',
                # LA area firms
                'https://www.bckrlaw.com',
                'https://www.westcoastpersonalinjury.com',
                'https://www.chasleylaw.com',
                'https://www.mesrianilawgroup.com',
                'https://www.weintraub.com',
                'https://www.ehlinelaw.com',
                'https://www.personalinjuryla.com',
                'https://www.legalattorneys.com',
                'https://www.lalawyers.com',
                'https://www.abramslaw.com',
                'https://www.rosenerlaw.com',
                'https://www.westcoasttriallawyers.com',
                'https://www.lalawfirm.com',
                'https://www.angeleslawfirm.com',
                'https://www.beverlyhillslaw.com',
                'https://www.california-lawyer.com',
                'https://www.legallionslaw.com',
                'https://www.personalinjuryattorneyla.com',
                'https://www.dellawfirm.com',
                'https://www.citylawyer.com'
            ],
            'Chicago': [
                'https://www.kirkland.com',
                'https://www.sidley.com',
                'https://www.mayer.com',
                'https://www.winston.com',
                'https://www.kcclaw.com',
                'https://www.joneswalkup.com',
                'https://www.lw.com',
                'https://www.goodwinlaw.com',
                # Chicago area firms
                'https://www.cliffordlaw.com',
                'https://www.rmblaw.com',
                'https://www.chicagoaccidentattorneys.com',
                'https://www.chicagolawfirm.net',
                'https://www.personalinjurychicago.com',
                'https://www.injurylawyerschicago.com',
                'https://www.chicagoinjurylaw.com',
                'https://www.illinoispersonalinjury.com',
                'https://www.chicagolegal.com',
                'https://www.robertkreisman.com',
                'https://www.torhoermanlaw.com',
                'https://www.chicagoaccidentcenter.com',
                'https://www.kadzialawfirm.com',
                'https://www.rosenfeldinjurylawyers.com',
                'https://www.dangerlegalteam.com',
                'https://www.chicagopersonalinjurylawfirm.com',
                'https://www.illinoisinjurylawyers.com',
                'https://www.legalteamchicago.com',
                'https://www.spertusalaw.com',
                'https://www.levinperconti.com'
            ],
            'Miami': [
                'https://www.greenbergtraurig.com',
                'https://www.hklaw.com',
                'https://www.whitecase.com',
                'https://www.lw.com',
                'https://www.akerman.com',
                # Miami area firms
                'https://www.miamilaw.com',
                'https://www.personalinjurymiami.com',
                'https://www.miamipersonalinjury.com',
                'https://www.lawtiger.com',
                'https://www.floridalaw.com',
                'https://www.miamilawfirm.com',
                'https://www.southflorida-law.com',
                'https://www.phalaw.com',
                'https://www.miamiduilawyer.com',
                'https://www.morrolaw.com',
                'https://www.corbellalaw.com',
                'https://www.themiamipersonalinjurylaw.com',
                'https://www.miamiinjurylawfirm.com',
                'https://www.personalinjuryflorida.com',
                'https://www.injurylawyersflorida.com',
                'https://www.jglawfirm.com',
                'https://www.floridalawfirm.com',
                'https://www.miamicrime.com',
                'https://www.southfloridalaw.com',
                'https://www.floridacaraccidentlaw.com'
            ],
            'Atlanta': [
                'https://www.kcclaw.com',
                'https://www.alston.com',
                'https://www.kilpatricktownsend.com',
                'https://www.troutman.com',
                'https://www.goodwinlaw.com',
                # Atlanta area firms
                'https://www.atllaw.com',
                'https://www.atlantapersonalinjury.com',
                'https://www.georgialawfirm.com',
                'https://www.atlantainjurylawyers.com',
                'https://www.atlantacaraccidentlawyers.com',
                'https://www.georgiainjurylaw.com',
                'https://www.injurylawyersatlanta.com',
                'https://www.kahnlaw.net',
                'https://www.georgialegal.com',
                'https://www.gglawatlanta.com',
                'https://www.atlantalawfirm.com',
                'https://www.personalinjuryga.com',
                'https://www.atlantaaccidentattorney.com',
                'https://www.mcdowelllaw.com',
                'https://www.solomonlaw.com',
                'https://www.mowery-law.com',
                'https://www.georgiatrialattorneys.com',
                'https://www.atlantatriallaw.com',
                'https://www.atlantaautoaccidentlawyer.com',
                'https://www.georgiaattorney.com'
            ]
        }
    
    def extract_contact_from_website(self, url: str, city: str) -> Dict[str, Any]:
        """Extract contact information from a law firm website"""
        contact_info = {
            'business_name': '',
            'primary_email': '',
            'phone': '',
            'address': '',
            'contact_name': '',
            'website': url,
            'city': city,
            'industry': 'Legal Services',
            'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'lead_score': 0.9,  # High score for direct law firm websites
            'email_confidence': 0.0,
            'source_type': 'Direct Website',
            'all_emails': [],
            'all_phones': []
        }
        
        try:
            self.stats['websites_processed'] += 1
            logger.info(f"Processing: {url}")
            
            # Get the main page
            response = self.session.get(url, timeout=20)
            if response.status_code != 200:
                logger.warning(f"Failed to access {url} - Status: {response.status_code}")
                return contact_info
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract business name from title or main heading
            business_name = self._extract_business_name(soup, url)
            contact_info['business_name'] = business_name
            
            # Look for contact pages
            contact_urls = self._find_contact_pages(soup, url)
            
            # Collect text from main page and contact pages
            all_text = soup.get_text()
            
            # Process up to 3 contact pages
            for contact_url in contact_urls[:3]:
                try:
                    contact_response = self.session.get(contact_url, timeout=15)
                    if contact_response.status_code == 200:
                        contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                        all_text += " " + contact_soup.get_text()
                except Exception as e:
                    logger.debug(f"Error accessing contact page {contact_url}: {e}")
                    continue
            
            # Extract emails
            emails = self._extract_emails(all_text)
            contact_info['all_emails'] = emails
            if emails:
                # Prioritize business emails over personal emails
                business_emails = [e for e in emails if not any(provider in e for provider in 
                                                              ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'])]
                contact_info['primary_email'] = business_emails[0] if business_emails else emails[0]
                self.stats['emails_found'] += 1
            
            # Extract phone numbers
            phones = self._extract_phones(all_text)
            contact_info['all_phones'] = phones
            if phones:
                contact_info['phone'] = phones[0]
                self.stats['phones_found'] += 1
            
            # Extract address
            address = self._extract_address(all_text, city)
            contact_info['address'] = address
            
            # Try to extract contact name (attorney name)
            contact_name = self._extract_attorney_name(all_text)
            contact_info['contact_name'] = contact_name
            
            if contact_info['primary_email']:
                self.stats['successful_extractions'] += 1
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
        
        return contact_info
    
    def _extract_business_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract business name from website"""
        # Try title tag first
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Clean up common title patterns
            business_name = re.sub(r'\s*[-|]\s*(Law|Attorney|Lawyer|Legal|LLP|PC|PA).*$', '', title_text, flags=re.IGNORECASE)
            if business_name and len(business_name) > 3:
                return business_name[:100]
        
        # Try main heading
        main_heading = soup.find(['h1', 'h2'])
        if main_heading:
            heading_text = main_heading.get_text(strip=True)
            if len(heading_text) > 3 and len(heading_text) < 100:
                return heading_text
        
        # Use domain as fallback
        domain = urlparse(url).netloc
        return domain.replace('www.', '').replace('.com', '').title()
    
    def _find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find contact page URLs"""
        contact_urls = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            
            if any(word in href or word in text for word in ['contact', 'about', 'office', 'location']):
                full_url = urljoin(base_url, link.get('href'))
                if full_url.startswith('http') and full_url not in contact_urls:
                    contact_urls.append(full_url)
        
        return contact_urls[:5]  # Limit to 5 contact pages
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract valid email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text, re.IGNORECASE)
        
        valid_emails = []
        for email in set(emails):  # Remove duplicates
            email = email.lower().strip()
            # Filter out invalid patterns
            if (email and '@' in email and 
                not any(bad in email for bad in ['example.com', 'test.com', 'placeholder', 'your-email', 'noreply', 'no-reply'])):
                valid_emails.append(email)
        
        return valid_emails[:10]  # Limit to 10 emails
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phone_patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
            r'\(\d{3}\)\s?\d{3}-\d{4}'
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Clean and format phones
        valid_phones = []
        for phone in set(phones):
            # Extract just digits
            digits = re.sub(r'[^0-9]', '', phone)
            if len(digits) == 10:
                formatted_phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                valid_phones.append(formatted_phone)
            elif len(digits) == 11 and digits[0] == '1':
                formatted_phone = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                valid_phones.append(formatted_phone)
        
        return valid_phones[:5]  # Limit to 5 phones
    
    def _extract_address(self, text: str, city: str) -> str:
        """Extract address information"""
        # Look for addresses containing the city name
        lines = text.split('\n')
        for line in lines:
            if city.lower() in line.lower() and any(word in line.lower() for word in ['street', 'avenue', 'road', 'drive', 'suite', 'floor']):
                return line.strip()[:200]
        
        return ""
    
    def _extract_attorney_name(self, text: str) -> str:
        """Extract attorney name from text"""
        name_patterns = [
            r'Attorney ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+), Esq\.?',
            r'Partner[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            r'Managing Partner[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            r'Contact ([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0] if isinstance(matches[0], str) else matches[0]
        
        return ""
    
    def validate_emails(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate email addresses using Mailtester API"""
        if not leads or not self.mailtester:
            return leads
        
        logger.info(f"Validating emails for {len(leads)} leads using Mailtester API")
        
        for i, lead in enumerate(leads):
            if lead['primary_email']:
                try:
                    self.stats['validation_attempts'] += 1
                    result = self.mailtester.validate_single_email_sync(lead['primary_email'])
                    
                    lead['email_confidence'] = result.confidence_score
                    lead['email_validation_status'] = result.status
                    lead['is_valid_email'] = result.is_valid
                    
                    if result.is_valid:
                        self.stats['valid_emails'] += 1
                    
                    logger.info(f"Validated {i+1}/{len(leads)}: {lead['primary_email']} - {result.status} ({result.confidence_score:.2f})")
                    
                    # Rate limiting
                    time.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"Error validating {lead['primary_email']}: {e}")
                    lead['email_validation_status'] = 'validation_failed'
                    lead['email_confidence'] = 0.5  # Default confidence
        
        return leads
    
    def generate_leads(self, target_leads: int = 500) -> str:
        """Generate lawyer leads from all cities"""
        logger.info(f"Starting generation of {target_leads} lawyer leads")
        
        all_leads = []
        leads_per_city = target_leads // len(self.law_firm_websites)
        
        for city, websites in self.law_firm_websites.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {city} ({leads_per_city} target leads)")
            logger.info(f"{'='*60}")
            
            city_leads = []
            
            # Process websites concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {
                    executor.submit(self.extract_contact_from_website, url, city): url 
                    for url in websites[:leads_per_city * 2]  # Process more websites than needed
                }
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        contact_info = future.result(timeout=60)
                        
                        # Only include leads with email addresses
                        if contact_info['primary_email']:
                            city_leads.append(contact_info)
                            
                        if len(city_leads) >= leads_per_city:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error processing {url}: {e}")
                        continue
            
            logger.info(f"Extracted {len(city_leads)} leads from {city}")
            all_leads.extend(city_leads)
            
            if len(all_leads) >= target_leads:
                break
        
        # Take top leads
        final_leads = all_leads[:target_leads]
        
        # Validate emails
        if self.mailtester:
            final_leads = self.validate_emails(final_leads)
        
        # Save to CSV
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"lawyer_leads_output/500_lawyer_leads_direct_{timestamp}.csv"
        csv_path = self.save_leads_to_csv(final_leads, filename)
        
        # Generate report
        self.generate_report(final_leads, csv_path)
        
        return csv_path
    
    def save_leads_to_csv(self, leads: List[Dict[str, Any]], filename: str) -> str:
        """Save leads to CSV file"""
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not leads:
            logger.warning("No leads to save")
            return str(output_path)
        
        # CSV columns
        columns = [
            'business_name', 'primary_email', 'phone', 'contact_name', 'website',
            'address', 'city', 'industry', 'extraction_date', 'lead_score',
            'email_confidence', 'email_validation_status', 'is_valid_email',
            'source_type', 'all_emails', 'all_phones'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for lead in leads:
                row = {}
                for col in columns:
                    value = lead.get(col, '')
                    if isinstance(value, list):
                        value = '; '.join(str(v) for v in value)
                    row[col] = str(value)
                writer.writerow(row)
        
        logger.info(f"Saved {len(leads)} leads to {output_path}")
        return str(output_path)
    
    def generate_report(self, leads: List[Dict[str, Any]], csv_path: str):
        """Generate summary report"""
        report = {
            'generation_summary': {
                'total_leads': len(leads),
                'generation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'csv_file': csv_path,
                'method': 'Direct Website Scraping'
            },
            'statistics': self.stats,
            'email_validation': {
                'validation_attempts': self.stats['validation_attempts'],
                'valid_emails': self.stats['valid_emails'],
                'success_rate': (self.stats['valid_emails'] / self.stats['validation_attempts'] * 100) if self.stats['validation_attempts'] > 0 else 0
            },
            'city_breakdown': {}
        }
        
        # City breakdown
        for city in self.law_firm_websites.keys():
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
        logger.info(f"Valid emails: {self.stats['valid_emails']}")
        logger.info(f"Success rate: {(self.stats['successful_extractions']/self.stats['websites_processed']*100):.1f}%")
        logger.info(f"CSV file: {csv_path}")
        logger.info(f"Report file: {report_path}")
        logger.info(f"{'='*60}")

if __name__ == "__main__":
    # Use Mailtester API key
    MAILTESTER_API_KEY = "sub_1RwOIXAJu6gy4fiYcL89Rfr3"
    
    generator = DirectLawyerLeadGenerator(MAILTESTER_API_KEY)
    
    try:
        csv_file = generator.generate_leads(500)
        print(f"\n✅ SUCCESS: Generated 500 lawyer leads")
        print(f"📁 CSV File: {csv_file}")
        print(f"🎯 Ready for outreach campaigns!")
        
    except KeyboardInterrupt:
        print("\n❌ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error generating leads: {e}")
        import traceback
        traceback.print_exc()