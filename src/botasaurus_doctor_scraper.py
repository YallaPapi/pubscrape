#!/usr/bin/env python3
"""
Botasaurus Doctor Scraper for Miami
Real Bing search scraping with URL extraction from search results
"""

from botasaurus import *
from botasaurus.request import request
import re
import csv
import json
from datetime import datetime

@request(
    use_stealth=True,
    block_detection=True,
    timeout=30,
    cache=False
)
def search_bing_for_doctors(request, query):
    """Search Bing for doctors and extract actual URLs from search results"""
    
    # Navigate to Bing search
    bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    request.get(bing_url)
    
    # Wait for page to fully load
    request.sleep(3)
    
    # Get page HTML
    html = request.page_source
    
    # Extract URLs from Bing search results using regex patterns
    # Look for actual website URLs in the search results
    url_patterns = [
        r'href="(https?://[^"]*(?:doctor|medical|clinic|health|physician)[^"]*)"',
        r'href="(https?://[^"]*\.(?:com|org|net)/[^"]*)"'
    ]
    
    found_urls = set()
    
    for pattern in url_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for url in matches:
            # Filter out Bing's own URLs and other non-business sites
            if not any(exclude in url.lower() for exclude in [
                'bing.com', 'microsoft.com', 'facebook.com', 'linkedin.com', 
                'yelp.com', 'google.com', 'youtube.com', 'wikipedia.org',
                'mapquest.com', 'yellowpages.com'
            ]):
                # Only include URLs that look like medical practices
                if any(medical in url.lower() for medical in [
                    'doctor', 'medical', 'clinic', 'health', 'physician', 
                    'surgery', 'practice', 'hospital', 'care'
                ]) or url.endswith('.com') or url.endswith('.org'):
                    found_urls.add(url)
    
    return {
        'query': query,
        'urls_found': list(found_urls),
        'total_urls': len(found_urls),
        'search_html_length': len(html),
        'bing_search_url': bing_url
    }

@request(
    use_stealth=True,
    block_detection=True,
    timeout=30,
    cache=False
)
def extract_doctor_contact_info(request, url):
    """Extract contact information from doctor/medical practice website"""
    
    try:
        # Navigate to the doctor's website
        request.get(url)
        request.sleep(2)
        
        # Get page content
        html = request.page_source
        page_text = request.get_text()
        
        # Extract business name from title or h1
        business_name = ""
        try:
            title = request.title
            if title:
                business_name = title.strip()
        except:
            pass
        
        if not business_name:
            try:
                h1_elements = request.select_all('h1')
                if h1_elements:
                    business_name = h1_elements[0].text.strip()
            except:
                pass
        
        # Extract emails using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html)
        emails = list(set(emails))  # Remove duplicates
        
        # Extract phone numbers using regex
        phone_patterns = [
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # (123) 456-7890
            r'\d{3}-\d{3}-\d{4}',        # 123-456-7890
            r'\d{3}\.\d{3}\.\d{4}',      # 123.456.7890
            r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})'  # Various formats
        ]
        
        phones = []
        for pattern in phone_patterns:
            found_phones = re.findall(pattern, page_text)
            phones.extend(found_phones)
        
        # Clean phone numbers
        cleaned_phones = []
        for phone in phones:
            if isinstance(phone, tuple):
                phone = ''.join(phone)
            # Remove non-digit characters and format
            digits = re.sub(r'[^\d]', '', str(phone))
            if len(digits) == 10:
                formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                cleaned_phones.append(formatted)
            elif len(digits) == 11 and digits.startswith('1'):
                formatted = f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                cleaned_phones.append(formatted)
        
        # Extract addresses (basic pattern)
        address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Circle|Cir|Court|Ct)[^,\n]*(?:,\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5})?'
        addresses = re.findall(address_pattern, page_text)
        
        # Extract doctor names (look for Dr. or Doctor patterns)
        doctor_patterns = [
            r'Dr\.?\s+([A-Za-z\s]+)',
            r'Doctor\s+([A-Za-z\s]+)',
            r'([A-Za-z]+\s+[A-Za-z]+),?\s*M\.?D\.?',
            r'([A-Za-z]+\s+[A-Za-z]+),?\s*D\.?O\.?'
        ]
        
        doctor_names = []
        for pattern in doctor_patterns:
            names = re.findall(pattern, page_text)
            doctor_names.extend(names)
        
        return {
            'url': url,
            'business_name': business_name,
            'emails': emails[:5],  # Limit to first 5 emails
            'phones': cleaned_phones[:3],  # Limit to first 3 phones
            'addresses': addresses[:2],  # Limit to first 2 addresses
            'doctor_names': doctor_names[:3],  # Limit to first 3 names
            'extraction_successful': bool(emails or cleaned_phones or business_name),
            'extraction_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'url': url,
            'error': str(e),
            'extraction_successful': False,
            'extraction_timestamp': datetime.now().isoformat()
        }

def main():
    """Main function to run the doctor lead scraping"""
    
    print("🏥 BOTASAURUS DOCTOR SCRAPER - MIAMI")
    print("Searching Bing for real doctor websites...")
    
    # Step 1: Search Bing for doctors
    search_query = "doctors in miami"
    search_results = search_bing_for_doctors(search_query)
    
    print(f"✅ Bing search completed")
    print(f"   Query: {search_results['query']}")
    print(f"   URLs found: {search_results['total_urls']}")
    print(f"   Search HTML length: {search_results['search_html_length']} chars")
    
    if search_results['total_urls'] == 0:
        print("❌ No doctor URLs found in search results")
        return
    
    # Show first few URLs found
    print(f"\n📋 Sample URLs extracted from Bing:")
    for i, url in enumerate(search_results['urls_found'][:5]):
        print(f"   {i+1}. {url}")
    
    # Step 2: Extract contact info from doctor websites
    print(f"\n🔍 Extracting contact info from {min(10, len(search_results['urls_found']))} doctor websites...")
    
    doctor_leads = []
    urls_to_process = search_results['urls_found'][:10]  # Process first 10 URLs
    
    for i, url in enumerate(urls_to_process, 1):
        print(f"\nProcessing {i}/{len(urls_to_process)}: {url}")
        
        contact_info = extract_doctor_contact_info(url)
        
        if contact_info['extraction_successful']:
            lead = {
                'lead_id': f"DOC_MIAMI_{i:03d}",
                'business_name': contact_info['business_name'],
                'website': url,
                'primary_email': contact_info['emails'][0] if contact_info['emails'] else '',
                'all_emails': ', '.join(contact_info['emails']) if contact_info['emails'] else '',
                'primary_phone': contact_info['phones'][0] if contact_info['phones'] else '',
                'all_phones': ', '.join(contact_info['phones']) if contact_info['phones'] else '',
                'doctor_names': ', '.join(contact_info['doctor_names']) if contact_info['doctor_names'] else '',
                'address': contact_info['addresses'][0] if contact_info['addresses'] else '',
                'extraction_date': contact_info['extraction_timestamp'],
                'source_query': search_query
            }
            
            doctor_leads.append(lead)
            
            print(f"   ✅ SUCCESS: {lead['business_name']}")
            print(f"      Email: {lead['primary_email']}")
            print(f"      Phone: {lead['primary_phone']}")
            print(f"      Doctor: {lead['doctor_names']}")
        else:
            error_msg = contact_info.get('error', 'Unknown error')
            print(f"   ❌ FAILED: {error_msg[:100]}")
    
    # Step 3: Export results
    if doctor_leads:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'miami_doctors_botasaurus_{timestamp}.csv'
        
        # Write to CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'lead_id', 'business_name', 'website', 'primary_email', 'all_emails',
                'primary_phone', 'all_phones', 'doctor_names', 'address', 
                'extraction_date', 'source_query'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(doctor_leads)
        
        # Save detailed results
        results_data = {
            'campaign_info': {
                'timestamp': timestamp,
                'search_query': search_query,
                'total_urls_found': search_results['total_urls'],
                'urls_processed': len(urls_to_process),
                'successful_extractions': len(doctor_leads)
            },
            'search_results': search_results,
            'extracted_leads': doctor_leads
        }
        
        json_filename = f'miami_doctors_results_{timestamp}.json'
        with open(json_filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n🎯 SCRAPING RESULTS:")
        print(f"   Total doctor leads: {len(doctor_leads)}")
        print(f"   CSV file: {csv_filename}")
        print(f"   Results file: {json_filename}")
        
        # Show sample leads
        print(f"\n📋 SAMPLE DOCTOR LEADS:")
        for i, lead in enumerate(doctor_leads[:3]):
            print(f"   {i+1}. {lead['business_name']}")
            print(f"      Website: {lead['website']}")
            print(f"      Email: {lead['primary_email']}")
            print(f"      Phone: {lead['primary_phone']}")
            print()
    else:
        print("❌ No successful doctor lead extractions")

if __name__ == "__main__":
    main()