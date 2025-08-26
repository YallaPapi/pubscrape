#!/usr/bin/env python3
"""
Real Lead Extraction Test
Tests the complete pipeline with actual website scraping and email extraction
to identify and fix garbage data issues.
"""

import os
import sys
import json
import time
import csv
import requests
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class RealLeadExtractionTest:
    """Test real lead extraction from actual websites"""
    
    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Test URLs for different business types
        self.test_urls = [
            # Medical practices
            "https://www.chicagomedicalassociates.com/contact",
            "https://www.nm.org/contact",
            "https://www.rush.edu/contact",
            
            # Professional services
            "https://www.latham.com/contact",
            "https://www.mckinsey.com/contact-us",
            "https://www.deloitte.com/us/en/footerlinks/contact-us.html",
            
            # Local businesses (smaller sites)
            "https://www.drjonesdentist.com/contact",
            "https://www.smithlawfirm.com/contact-us",
            "https://www.acmeconsulting.com/contact"
        ]
        
        # Backup test URLs that we know have contact info
        self.backup_test_sites = [
            "https://example-medical-practice.com",  # Will be replaced with real sites
            "https://sample-law-firm.org",
            "https://test-consulting-firm.net"
        ]
    
    def test_real_bing_scraping(self) -> Dict[str, Any]:
        """Test real Bing search results extraction"""
        print("Testing Real Bing Search Results...")
        
        # Test medical practice query
        query = "medical practice contact information Chicago"
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                results = []
                result_divs = soup.select('.b_algo')
                
                for div in result_divs[:5]:  # First 5 results
                    title_link = div.select_one('h2 a')
                    if title_link:
                        title = title_link.get_text(strip=True)
                        url = title_link.get('href', '')
                        
                        description_div = div.select_one('.b_caption p')
                        description = description_div.get_text(strip=True) if description_div else ""
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'description': description
                        })
                
                print(f"  Extracted {len(results)} search results")
                return {
                    'status': 'success',
                    'results_count': len(results),
                    'results': results
                }
            else:
                print(f"  Bing search failed: Status {response.status_code}")
                return {'status': 'failed', 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"  Bing scraping error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def extract_contact_info_from_url(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Extract real contact information from a website URL"""
        try:
            response = self.session.get(url, timeout=timeout)
            if response.status_code != 200:
                return {
                    'url': url,
                    'status': 'failed',
                    'error': f'HTTP {response.status_code}',
                    'emails': [],
                    'phones': [],
                    'names': [],
                    'addresses': []
                }
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract various contact information
            contact_info = {
                'url': url,
                'status': 'success',
                'business_name': self.extract_business_name(soup, url),
                'emails': self.extract_emails(soup, response.text),
                'phones': self.extract_phone_numbers(response.text),
                'names': self.extract_person_names(soup, response.text),
                'addresses': self.extract_addresses(response.text),
                'social_profiles': self.extract_social_profiles(soup),
                'page_title': soup.title.get_text(strip=True) if soup.title else "",
                'content_length': len(response.text),
                'extraction_timestamp': time.time()
            }
            
            return contact_info
            
        except Exception as e:
            return {
                'url': url,
                'status': 'error',
                'error': str(e),
                'emails': [],
                'phones': [],
                'names': [],
                'addresses': []
            }
    
    def extract_business_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract business name from webpage"""
        # Try various methods to find business name
        candidates = []
        
        # Method 1: Page title
        if soup.title:
            title = soup.title.get_text(strip=True)
            # Clean up title
            title = re.sub(r'\s*[|-].*$', '', title)
            if title and len(title) < 100:
                candidates.append(title)
        
        # Method 2: H1 tags
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags[:3]:
            text = h1.get_text(strip=True)
            if text and len(text) < 80:
                candidates.append(text)
        
        # Method 3: Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')
            # Extract potential business name from start of description
            first_sentence = desc.split('.')[0]
            if first_sentence and len(first_sentence) < 100:
                candidates.append(first_sentence)
        
        # Method 4: Extract from domain
        domain = urlparse(url).netloc.replace('www.', '')
        domain_name = domain.split('.')[0].replace('-', ' ').title()
        candidates.append(domain_name)
        
        # Choose best candidate
        if candidates:
            # Prefer candidates with business keywords
            business_keywords = ['practice', 'clinic', 'medical', 'law', 'firm', 'group', 'associates', 'partners']
            for candidate in candidates:
                if any(keyword in candidate.lower() for keyword in business_keywords):
                    return candidate
            
            # Return first non-empty candidate
            return candidates[0]
        
        return "Unknown Business"
    
    def extract_emails(self, soup: BeautifulSoup, text: str) -> List[Dict[str, Any]]:
        """Extract email addresses with context"""
        emails_found = []
        
        # Enhanced email regex
        email_pattern = re.compile(
            r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}\b',
            re.IGNORECASE
        )
        
        # Extract from text content
        text_emails = email_pattern.findall(text)
        for email in text_emails:
            # Get context around email
            context = self.get_email_context(text, email)
            
            emails_found.append({
                'email': email.lower(),
                'source': 'text_content',
                'context': context,
                'confidence': self.score_email_quality(email)
            })
        
        # Extract from mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0].strip()
                if '@' in email:
                    link_text = link.get_text(strip=True)
                    
                    emails_found.append({
                        'email': email.lower(),
                        'source': 'mailto_link',
                        'context': link_text,
                        'confidence': self.score_email_quality(email) + 0.1  # Bonus for mailto
                    })
        
        # Remove duplicates and filter quality
        unique_emails = {}
        for email_data in emails_found:
            email = email_data['email']
            if email not in unique_emails or email_data['confidence'] > unique_emails[email]['confidence']:
                unique_emails[email] = email_data
        
        # Filter out obviously bad emails
        filtered_emails = []
        for email_data in unique_emails.values():
            if self.is_valid_business_email(email_data['email']):
                filtered_emails.append(email_data)
        
        # Sort by confidence
        filtered_emails.sort(key=lambda x: x['confidence'], reverse=True)
        
        return filtered_emails[:5]  # Top 5 emails
    
    def extract_phone_numbers(self, text: str) -> List[Dict[str, Any]]:
        """Extract phone numbers with context"""
        phones_found = []
        
        # Phone number patterns
        phone_patterns = [
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            re.compile(r'\b\+?1[-.\s]?([0-9]{3})[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})\.([0-9]{3})\.([0-9]{4})\b')
        ]
        
        for pattern in phone_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                if len(match.groups()) == 3:
                    area_code, exchange, number = match.groups()
                    phone = f"({area_code}) {exchange}-{number}"
                    
                    # Get context
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end].strip()
                    
                    # Score phone number quality
                    confidence = 0.7
                    if any(keyword in context.lower() for keyword in ['phone', 'call', 'contact', 'office']):
                        confidence += 0.2
                    
                    phones_found.append({
                        'phone': phone,
                        'context': context,
                        'confidence': confidence
                    })
        
        # Remove duplicates and sort by confidence
        unique_phones = {}
        for phone_data in phones_found:
            phone = phone_data['phone']
            if phone not in unique_phones or phone_data['confidence'] > unique_phones[phone]['confidence']:
                unique_phones[phone] = phone_data
        
        return sorted(unique_phones.values(), key=lambda x: x['confidence'], reverse=True)[:3]
    
    def extract_person_names(self, soup: BeautifulSoup, text: str) -> List[Dict[str, Any]]:
        """Extract person names from content"""
        names_found = []
        
        # Name patterns
        name_pattern = re.compile(r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b')
        
        # Look for names in specific contexts
        staff_sections = soup.find_all(['div', 'section'], class_=re.compile(r'(staff|team|doctor|attorney|professional)', re.I))
        
        for section in staff_sections:
            section_text = section.get_text()
            matches = name_pattern.findall(section_text)
            
            for name in matches:
                # Skip common false positives
                if not any(skip_word in name.lower() for skip_word in [
                    'about us', 'contact us', 'our team', 'new york', 'los angeles'
                ]):
                    names_found.append({
                        'name': name,
                        'context': 'staff_section',
                        'confidence': 0.8
                    })
        
        # Look for names near contact information
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        email_matches = email_pattern.finditer(text)
        
        for email_match in email_matches:
            # Look for names within 100 characters of email
            start = max(0, email_match.start() - 100)
            end = min(len(text), email_match.end() + 100)
            context_text = text[start:end]
            
            name_matches = name_pattern.findall(context_text)
            for name in name_matches:
                if not any(skip_word in name.lower() for skip_word in [
                    'about us', 'contact us', 'our team'
                ]):
                    names_found.append({
                        'name': name,
                        'context': 'near_email',
                        'confidence': 0.9
                    })
        
        # Remove duplicates and sort by confidence
        unique_names = {}
        for name_data in names_found:
            name = name_data['name']
            if name not in unique_names or name_data['confidence'] > unique_names[name]['confidence']:
                unique_names[name] = name_data
        
        return sorted(unique_names.values(), key=lambda x: x['confidence'], reverse=True)[:5]
    
    def extract_addresses(self, text: str) -> List[Dict[str, Any]]:
        """Extract physical addresses"""
        addresses_found = []
        
        # Address patterns
        address_pattern = re.compile(
            r'\b\d+[\w\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Circle|Cir|Court|Ct|Plaza|Pl)\b[,\s]+[\w\s,]+(?:IL|Illinois|Chicago|CA|California|NY|New York|TX|Texas)\s+\d{5}(?:-\d{4})?\b',
            re.IGNORECASE
        )
        
        matches = address_pattern.findall(text)
        for address in matches:
            addresses_found.append({
                'address': address.strip(),
                'confidence': 0.8
            })
        
        return addresses_found[:3]
    
    def extract_social_profiles(self, soup: BeautifulSoup) -> List[str]:
        """Extract social media profile links"""
        social_profiles = []
        
        social_domains = ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com']
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            for domain in social_domains:
                if domain in href:
                    social_profiles.append(href)
                    break
        
        return list(set(social_profiles))[:5]  # Remove duplicates, limit to 5
    
    def get_email_context(self, text: str, email: str, window: int = 50) -> str:
        """Get context around an email in text"""
        email_pos = text.lower().find(email.lower())
        if email_pos >= 0:
            start = max(0, email_pos - window)
            end = min(len(text), email_pos + len(email) + window)
            return text[start:end].strip()
        return ""
    
    def score_email_quality(self, email: str) -> float:
        """Score email quality for business use"""
        score = 0.5  # Base score
        
        email_lower = email.lower()
        local_part, domain = email_lower.split('@', 1)
        
        # High-quality patterns
        if any(pattern in email_lower for pattern in [
            'ceo@', 'president@', 'director@', 'manager@', 'owner@',
            'contact@', 'info@', 'business@', 'sales@'
        ]):
            score += 0.3
        
        # firstname.lastname pattern
        if '.' in local_part and all(part.isalpha() for part in local_part.split('.')):
            score += 0.2
        
        # Domain quality
        if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            score -= 0.1  # Personal domains get slight penalty
        
        # Penalty for obviously bad patterns
        if any(bad_pattern in email_lower for bad_pattern in [
            'noreply', 'no-reply', 'test', 'example', 'webmaster'
        ]):
            score -= 0.4
        
        return max(0.0, min(1.0, score))
    
    def is_valid_business_email(self, email: str) -> bool:
        """Check if email is valid for business use"""
        if not email or '@' not in email:
            return False
        
        # Check for obvious spam/invalid patterns
        spam_patterns = [
            r'^noreply', r'^no-reply', r'^test', r'^example',
            r'@test\.', r'@example\.', r'@localhost'
        ]
        
        for pattern in spam_patterns:
            if re.match(pattern, email, re.IGNORECASE):
                return False
        
        return True
    
    def validate_extracted_lead(self, contact_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and score an extracted lead"""
        lead_score = 0.0
        validation_issues = []
        
        # Check email quality
        emails = contact_info.get('emails', [])
        if emails:
            best_email = max(emails, key=lambda x: x['confidence'])
            lead_score += best_email['confidence'] * 0.4
        else:
            validation_issues.append("No emails found")
            lead_score -= 0.3
        
        # Check phone numbers
        phones = contact_info.get('phones', [])
        if phones:
            lead_score += 0.2
        else:
            validation_issues.append("No phone numbers found")
        
        # Check business name
        business_name = contact_info.get('business_name', '')
        if business_name and business_name != 'Unknown Business':
            lead_score += 0.2
        else:
            validation_issues.append("No clear business name")
        
        # Check names
        names = contact_info.get('names', [])
        if names:
            lead_score += 0.1
        
        # Check addresses
        addresses = contact_info.get('addresses', [])
        if addresses:
            lead_score += 0.1
        
        lead_score = max(0.0, min(1.0, lead_score))
        
        return {
            'lead_score': lead_score,
            'validation_issues': validation_issues,
            'is_high_quality': lead_score >= 0.7,
            'is_actionable': lead_score >= 0.5 and len(emails) > 0
        }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive lead extraction test"""
        print("COMPREHENSIVE REAL LEAD EXTRACTION TEST")
        print("=" * 60)
        
        test_results = {
            'start_time': time.time(),
            'bing_search_test': None,
            'website_extraction_tests': [],
            'lead_quality_analysis': {},
            'issues_found': [],
            'recommendations': []
        }
        
        # Test 1: Bing search functionality
        print("\n1. Testing Bing Search Results Extraction...")
        bing_test = self.test_real_bing_scraping()
        test_results['bing_search_test'] = bing_test
        
        if bing_test['status'] != 'success':
            test_results['issues_found'].append("Bing search extraction failed")
        
        # Test 2: Website contact extraction
        print("\n2. Testing Website Contact Information Extraction...")
        
        # Use real test URLs or Bing results
        test_urls = []
        if bing_test['status'] == 'success' and bing_test.get('results'):
            # Use URLs from Bing results
            test_urls = [result['url'] for result in bing_test['results'][:3]]
        
        # Add fallback test URLs
        fallback_urls = [
            "https://httpbin.org/html",  # Safe test URL
            "https://example.com",       # Simple test
        ]
        test_urls.extend(fallback_urls)
        
        all_extracted_contacts = []
        
        for i, url in enumerate(test_urls[:5]):  # Test first 5 URLs
            print(f"  Testing URL {i+1}: {url[:60]}...")
            
            contact_info = self.extract_contact_info_from_url(url)
            validation = self.validate_extracted_lead(contact_info)
            
            contact_info['validation'] = validation
            test_results['website_extraction_tests'].append(contact_info)
            
            if contact_info['status'] == 'success':
                all_extracted_contacts.append(contact_info)
                
                print(f"    Status: {contact_info['status']}")
                print(f"    Emails: {len(contact_info['emails'])}")
                print(f"    Phones: {len(contact_info['phones'])}")
                print(f"    Names: {len(contact_info['names'])}")
                print(f"    Business: {contact_info['business_name']}")
                print(f"    Lead Score: {validation['lead_score']:.2f}")
            else:
                print(f"    Failed: {contact_info.get('error', 'Unknown error')}")
        
        # Test 3: Lead Quality Analysis
        print("\n3. Analyzing Lead Quality...")
        
        if all_extracted_contacts:
            quality_stats = {
                'total_contacts': len(all_extracted_contacts),
                'high_quality_leads': 0,
                'actionable_leads': 0,
                'average_emails_per_contact': 0,
                'average_phones_per_contact': 0,
                'contacts_with_names': 0,
                'contacts_with_addresses': 0
            }
            
            total_emails = 0
            total_phones = 0
            
            for contact in all_extracted_contacts:
                validation = contact['validation']
                
                if validation['is_high_quality']:
                    quality_stats['high_quality_leads'] += 1
                if validation['is_actionable']:
                    quality_stats['actionable_leads'] += 1
                
                total_emails += len(contact['emails'])
                total_phones += len(contact['phones'])
                
                if contact['names']:
                    quality_stats['contacts_with_names'] += 1
                if contact['addresses']:
                    quality_stats['contacts_with_addresses'] += 1
            
            quality_stats['average_emails_per_contact'] = total_emails / len(all_extracted_contacts)
            quality_stats['average_phones_per_contact'] = total_phones / len(all_extracted_contacts)
            
            test_results['lead_quality_analysis'] = quality_stats
            
            print(f"    Total Contacts Extracted: {quality_stats['total_contacts']}")
            print(f"    High Quality Leads: {quality_stats['high_quality_leads']}")
            print(f"    Actionable Leads: {quality_stats['actionable_leads']}")
            print(f"    Avg Emails/Contact: {quality_stats['average_emails_per_contact']:.1f}")
            print(f"    Avg Phones/Contact: {quality_stats['average_phones_per_contact']:.1f}")
            
            # Identify issues
            if quality_stats['high_quality_leads'] == 0:
                test_results['issues_found'].append("No high-quality leads extracted")
            
            if quality_stats['actionable_leads'] == 0:
                test_results['issues_found'].append("No actionable leads extracted")
            
            if quality_stats['average_emails_per_contact'] < 0.5:
                test_results['issues_found'].append("Low email extraction rate")
        
        else:
            test_results['issues_found'].append("No contacts extracted from any website")
        
        # Generate recommendations
        print("\n4. Generating Recommendations...")
        
        if test_results['issues_found']:
            print("    Issues Found:")
            for issue in test_results['issues_found']:
                print(f"      - {issue}")
        
        # Generate recommendations based on findings
        if "No emails" in str(test_results['issues_found']):
            test_results['recommendations'].append("Improve email extraction patterns")
            test_results['recommendations'].append("Add more email obfuscation detection")
        
        if "No high-quality leads" in str(test_results['issues_found']):
            test_results['recommendations'].append("Enhance lead scoring algorithm")
            test_results['recommendations'].append("Improve business name extraction")
        
        if "Bing search" in str(test_results['issues_found']):
            test_results['recommendations'].append("Fix Bing search result parsing")
            test_results['recommendations'].append("Add error handling for blocked requests")
        
        test_results['end_time'] = time.time()
        test_results['total_time'] = test_results['end_time'] - test_results['start_time']
        
        return test_results
    
    def save_test_results(self, results: Dict[str, Any]) -> Path:
        """Save test results to JSON file"""
        timestamp = int(time.time())
        filename = f"real_lead_extraction_test_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nTest results saved to: {filepath}")
        return filepath
    
    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable test report"""
        report = []
        report.append("REAL LEAD EXTRACTION TEST REPORT")
        report.append("=" * 50)
        report.append(f"Test Duration: {results['total_time']:.2f} seconds")
        report.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Bing Search Test
        bing_test = results.get('bing_search_test', {})
        report.append("1. BING SEARCH TEST")
        report.append(f"Status: {bing_test.get('status', 'unknown')}")
        if bing_test.get('status') == 'success':
            report.append(f"Results Found: {bing_test.get('results_count', 0)}")
        else:
            report.append(f"Error: {bing_test.get('error', 'Unknown error')}")
        report.append("")
        
        # Website Extraction Tests
        extraction_tests = results.get('website_extraction_tests', [])
        report.append("2. WEBSITE EXTRACTION TESTS")
        report.append(f"URLs Tested: {len(extraction_tests)}")
        
        successful_extractions = [t for t in extraction_tests if t.get('status') == 'success']
        report.append(f"Successful Extractions: {len(successful_extractions)}")
        
        if successful_extractions:
            report.append("\nExtracted Data Summary:")
            for i, test in enumerate(successful_extractions):
                report.append(f"  URL {i+1}: {test.get('url', 'Unknown')[:50]}...")
                report.append(f"    Business: {test.get('business_name', 'Unknown')}")
                report.append(f"    Emails: {len(test.get('emails', []))}")
                report.append(f"    Phones: {len(test.get('phones', []))}")
                report.append(f"    Names: {len(test.get('names', []))}")
                report.append(f"    Lead Score: {test.get('validation', {}).get('lead_score', 0):.2f}")
                report.append("")
        
        # Lead Quality Analysis
        quality_stats = results.get('lead_quality_analysis', {})
        if quality_stats:
            report.append("3. LEAD QUALITY ANALYSIS")
            report.append(f"Total Contacts: {quality_stats.get('total_contacts', 0)}")
            report.append(f"High Quality Leads: {quality_stats.get('high_quality_leads', 0)}")
            report.append(f"Actionable Leads: {quality_stats.get('actionable_leads', 0)}")
            report.append(f"Average Emails per Contact: {quality_stats.get('average_emails_per_contact', 0):.1f}")
            report.append(f"Average Phones per Contact: {quality_stats.get('average_phones_per_contact', 0):.1f}")
            report.append("")
        
        # Issues Found
        issues = results.get('issues_found', [])
        if issues:
            report.append("ISSUES FOUND")
            for issue in issues:
                report.append(f"  - {issue}")
            report.append("")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        if recommendations:
            report.append("RECOMMENDATIONS")
            for rec in recommendations:
                report.append(f"  - {rec}")
            report.append("")
        
        # Overall Assessment
        report.append("OVERALL ASSESSMENT")
        if not issues:
            report.append("All tests passed - extraction pipeline working correctly")
        elif len(issues) <= 2:
            report.append("Minor issues found - pipeline needs tuning")
        else:
            report.append("Major issues found - pipeline requires significant fixes")
        
        return "\n".join(report)


def run_real_lead_extraction_test():
    """Run the real lead extraction test"""
    print("STARTING REAL LEAD EXTRACTION TEST")
    print("This test will analyze the actual lead extraction pipeline")
    print("and identify issues with current data quality.")
    print()
    
    tester = RealLeadExtractionTest()
    
    try:
        # Run comprehensive test
        results = tester.run_comprehensive_test()
        
        # Save results
        results_file = tester.save_test_results(results)
        
        # Generate and display report
        report = tester.generate_test_report(results)
        print("\n" + report)
        
        # Save report to file
        report_file = tester.output_dir / f"test_report_{int(time.time())}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nFull report saved to: {report_file}")
        
        # Return success status
        issues_count = len(results.get('issues_found', []))
        return issues_count == 0, results
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False, {'error': str(e)}


if __name__ == "__main__":
    success, results = run_real_lead_extraction_test()
    
    if success:
        print("\nReal lead extraction test completed successfully!")
        print("Lead extraction pipeline is working correctly")
    else:
        print("\nReal lead extraction test found issues")
        print("Review the test report and fix identified problems")
        
        # Show key issues
        if 'issues_found' in results:
            print("\nKey Issues:")
            for issue in results['issues_found']:
                print(f"  - {issue}")
    
    sys.exit(0 if success else 1)