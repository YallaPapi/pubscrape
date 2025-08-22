#!/usr/bin/env python3
"""
Extract real leads from cached Bing HTML files
Validates that we're working with real data, not mocks
"""

import os
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import requests
import time

class RealLeadExtractor:
    """Extract and validate real leads from cached HTML"""
    
    def __init__(self):
        self.leads = []
        self.validation_log = []
        
    def validate_bing_html(self, html_content):
        """Validate that HTML is real Bing search results"""
        # Check for Bing-specific markers
        bing_markers = ['b_algo', 'b_title', 'bing.com', 'microsoft']
        found = sum(1 for marker in bing_markers if marker in html_content.lower())
        
        if found < 2:
            return False, f"Not real Bing HTML (only {found} markers)"
        
        return True, f"Valid Bing HTML ({found} markers found)"
    
    def extract_urls_from_bing(self, html_content):
        """Extract business URLs from Bing search results"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = []
        
        # Find all search result containers (b_algo class)
        results = soup.find_all('li', class_='b_algo')
        
        for result in results:
            # Get the link
            link_elem = result.find('h2')
            if link_elem:
                a_tag = link_elem.find('a')
                if a_tag and a_tag.get('href'):
                    url = a_tag['href']
                    
                    # Handle Bing redirect URLs
                    if 'bing.com/ck/a' in url:
                        # Try to extract the actual URL from the redirect
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query)
                        
                        # Look for the actual URL in various parameters
                        actual_url = None
                        if 'u' in params and params['u']:
                            # Decode the URL parameter
                            encoded = params['u'][0]
                            if encoded.startswith('a1'):
                                # It's base64 encoded with a prefix
                                import base64
                                try:
                                    decoded = base64.b64decode(encoded[2:] + '==').decode('utf-8')
                                    actual_url = decoded
                                except:
                                    pass
                        
                        # If we couldn't decode, skip this URL
                        if not actual_url:
                            # Try alternate extraction - look for actual URL in cite tag
                            cite_elem = result.find('cite')
                            if cite_elem:
                                cite_text = cite_elem.get_text(strip=True)
                                if 'http' in cite_text:
                                    actual_url = cite_text
                                elif cite_text and not cite_text.startswith('http'):
                                    actual_url = 'https://' + cite_text
                        
                        if actual_url:
                            url = actual_url
                        else:
                            continue  # Skip if we can't get the real URL
                    
                    title = a_tag.get_text(strip=True)
                    
                    # Get snippet
                    snippet = ""
                    snippet_elem = result.find('div', class_='b_caption')
                    if snippet_elem:
                        p_elem = snippet_elem.find('p')
                        if p_elem:
                            snippet = p_elem.get_text(strip=True)
                    
                    # Also try to get the display URL from cite element
                    cite_elem = result.find('cite')
                    display_url = cite_elem.get_text(strip=True) if cite_elem else ""
                    
                    # Use display URL if main URL is still a redirect
                    if 'bing.com' in url and display_url:
                        if display_url.startswith('http'):
                            url = display_url
                        else:
                            url = 'https://' + display_url
                    
                    # Final check - skip if still a Bing URL
                    if 'bing.com' not in url:
                        urls.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet
                        })
        
        return urls
    
    def filter_medical_urls(self, urls):
        """Filter URLs to keep only medical/doctor related ones"""
        medical_keywords = ['doctor', 'dr', 'md', 'physician', 'medical', 'clinic', 
                          'health', 'practice', 'hospital', 'care']
        
        filtered = []
        for url_data in urls:
            url = url_data['url'].lower()
            title = url_data['title'].lower()
            snippet = url_data['snippet'].lower()
            
            # Check if any medical keyword is present
            if any(keyword in url + title + snippet for keyword in medical_keywords):
                filtered.append(url_data)
        
        return filtered
    
    def extract_emails_from_website(self, url, max_retries=2):
        """Extract emails from a website with validation"""
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    # Find email addresses
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, content)
                    
                    # Filter out common non-contact emails
                    blacklist = ['noreply', 'no-reply', 'donotreply', 'mailer-daemon', 
                               'postmaster', 'abuse', 'spam', 'root', 'admin@']
                    
                    valid_emails = []
                    for email in emails:
                        if not any(black in email.lower() for black in blacklist):
                            # Check for medical indicators
                            medical_indicators = ['dr', 'md', 'clinic', 'medical', 'health', 'doctor']
                            score = sum(1 for ind in medical_indicators if ind in email.lower())
                            
                            valid_emails.append({
                                'email': email,
                                'score': score,
                                'source': url
                            })
                    
                    return valid_emails
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"    ❌ Failed to extract from {url[:50]}...: {str(e)}")
            
            time.sleep(1)  # Rate limiting
        
        return []
    
    def process_cached_files(self):
        """Process all cached HTML files"""
        html_dir = "output/html_cache"
        
        if not os.path.exists(html_dir):
            print("❌ No HTML cache directory found")
            return False
        
        html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
        
        print(f"📁 Found {len(html_files)} cached HTML files")
        
        all_urls = []
        
        # Process each HTML file
        for html_file in html_files[:10]:  # Process first 10 files
            file_path = os.path.join(html_dir, html_file)
            print(f"\n📄 Processing: {html_file}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Validate it's real Bing HTML
            is_valid, msg = self.validate_bing_html(html_content)
            
            if is_valid:
                print(f"  ✅ {msg}")
                
                # Extract URLs
                urls = self.extract_urls_from_bing(html_content)
                print(f"  📎 Found {len(urls)} URLs")
                
                # Filter for medical URLs
                medical_urls = self.filter_medical_urls(urls)
                print(f"  🏥 {len(medical_urls)} medical URLs")
                
                all_urls.extend(medical_urls)
                self.validation_log.append(f"✅ Processed {html_file}: {len(medical_urls)} medical URLs")
            else:
                print(f"  ❌ {msg}")
                self.validation_log.append(f"❌ Invalid HTML: {html_file} - {msg}")
        
        print(f"\n📊 Total medical URLs found: {len(all_urls)}")
        
        # Extract emails from medical websites
        print("\n📧 Extracting emails from medical websites...")
        
        for i, url_data in enumerate(all_urls[:20]):  # Process first 20 URLs
            url = url_data['url']
            print(f"\n[{i+1}/20] {url[:60]}...")
            
            emails = self.extract_emails_from_website(url)
            
            if emails:
                print(f"  ✅ Found {len(emails)} emails")
                
                for email_data in emails[:2]:  # Max 2 emails per site
                    lead = {
                        'business_name': url_data['title'][:100],
                        'website': url,
                        'email': email_data['email'],
                        'confidence_score': min(1.0, 0.5 + email_data['score'] * 0.1),
                        'source': 'real_bing_extraction',
                        'extraction_date': datetime.now().strftime('%Y-%m-%d'),
                        'snippet': url_data['snippet'][:200]
                    }
                    
                    # Validate it's not test data
                    if not any(test in lead['email'].lower() for test in ['test', 'example', 'fake', 'demo']):
                        self.leads.append(lead)
                        self.validation_log.append(f"✅ Valid lead: {lead['email']} from {url[:40]}...")
            else:
                print(f"  ⚠️  No emails found")
        
        return True
    
    def save_results(self):
        """Save extracted leads to CSV"""
        if not self.leads:
            print("\n❌ No leads to save")
            return None
        
        # Create output directory
        os.makedirs("output/real_leads", exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"output/real_leads/extracted_leads_{timestamp}.csv"
        log_file = f"output/real_leads/validation_log_{timestamp}.txt"
        
        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['business_name', 'website', 'email', 'confidence_score', 
                         'source', 'extraction_date', 'snippet']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for lead in self.leads:
                writer.writerow(lead)
        
        print(f"\n✅ Saved {len(self.leads)} leads to: {csv_file}")
        
        # Write validation log
        with open(log_file, 'w') as f:
            f.write("REAL LEAD EXTRACTION VALIDATION LOG\n")
            f.write("=" * 60 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Leads: {len(self.leads)}\n")
            f.write("=" * 60 + "\n\n")
            for entry in self.validation_log:
                f.write(entry + "\n")
        
        print(f"✅ Validation log saved to: {log_file}")
        
        return csv_file


def main():
    """Main extraction pipeline"""
    print("🏥 REAL LEAD EXTRACTION FROM CACHED BING RESULTS")
    print("=" * 60)
    
    extractor = RealLeadExtractor()
    
    # Process cached files
    if extractor.process_cached_files():
        # Save results
        csv_file = extractor.save_results()
        
        if csv_file:
            print("\n" + "=" * 60)
            print("📊 EXTRACTION SUMMARY")
            print("=" * 60)
            print(f"✅ Total Leads Extracted: {len(extractor.leads)}")
            print(f"✅ Validation Entries: {len(extractor.validation_log)}")
            print(f"✅ Output File: {csv_file}")
            
            # Show sample leads
            print("\n📋 Sample Leads:")
            for i, lead in enumerate(extractor.leads[:5]):
                print(f"  {i+1}. {lead['email']} ({lead['business_name'][:40]}...)")
            
            return True
    
    return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)