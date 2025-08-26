#!/usr/bin/env python3
"""
Get REAL leads by actually visiting restaurant websites and extracting contact info
"""
import sys
import os
import requests
import re
import time
import csv
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import random

def get_real_bing_results(queries, max_results=50):
    """Get real search results from Bing"""
    print("🔍 SEARCHING BING FOR REAL RESTAURANT WEBSITES")
    print("=" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    all_urls = []
    
    for i, query in enumerate(queries[:10]):  # Limit to 10 queries to avoid blocking
        print(f"Query {i+1}: {query}")
        
        try:
            search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract URLs from search results
                result_links = soup.select('.b_algo h2 a')
                
                for link in result_links:
                    href = link.get('href')
                    title = link.get_text(strip=True)
                    
                    if href and href.startswith('http') and 'bing.com' not in href:
                        # Filter out obvious non-restaurant sites
                        url_lower = href.lower()
                        if not any(exclude in url_lower for exclude in [
                            'facebook.com', 'twitter.com', 'yelp.com', 'tripadvisor.com',
                            'opentable.com', 'grubhub.com', 'doordash.com', 'ubereats.com',
                            'google.com', 'linkedin.com', 'instagram.com'
                        ]):
                            all_urls.append({
                                'url': href,
                                'title': title,
                                'query': query
                            })
                            print(f"  ✓ Found: {title[:50]}...")
                
                print(f"  Found {len([u for u in all_urls if u['query'] == query])} URLs from this query")
                
            else:
                print(f"  ✗ Failed: Status {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
        
        # Be polite to Bing
        time.sleep(random.uniform(2, 4))
    
    # Remove duplicates
    seen_urls = set()
    unique_urls = []
    for url_data in all_urls:
        if url_data['url'] not in seen_urls:
            seen_urls.add(url_data['url'])
            unique_urls.append(url_data)
    
    print(f"\\n✓ Total unique URLs found: {len(unique_urls)}")
    return unique_urls[:max_results]

def extract_contact_info(url, timeout=10):
    """Extract real contact information from a website"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract emails
        email_pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
        text_content = soup.get_text()
        emails = re.findall(email_pattern, text_content, re.IGNORECASE)
        
        # Filter out common spam/generic emails
        filtered_emails = []
        for email in emails:
            email_lower = email.lower()
            if not any(spam in email_lower for spam in [
                'noreply', 'no-reply', 'donotreply', 'test', 'example', 
                'admin', 'webmaster', 'postmaster', 'abuse', 'spam'
            ]):
                filtered_emails.append(email)
        
        # Extract phone numbers
        phone_pattern = r'\\(?([0-9]{3})\\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})'
        phones = re.findall(phone_pattern, text_content)
        formatted_phones = [f"({p[0]}) {p[1]}-{p[2]}" for p in phones]
        
        # Get business name from title or h1
        business_name = ""
        if soup.title:
            business_name = soup.title.get_text(strip=True)
        elif soup.find('h1'):
            business_name = soup.find('h1').get_text(strip=True)
        else:
            # Extract from domain
            domain = urlparse(url).netloc.replace('www.', '')
            business_name = domain.split('.')[0].title()
        
        # Clean up business name
        business_name = re.sub(r'\\s*[|-].*$', '', business_name)  # Remove everything after | or -
        business_name = business_name[:50]  # Limit length
        
        return {
            'url': url,
            'business_name': business_name,
            'emails': filtered_emails[:3],  # Limit to 3 emails
            'phones': formatted_phones[:2],  # Limit to 2 phones
            'title': soup.title.get_text(strip=True) if soup.title else "",
            'success': True
        }
        
    except Exception as e:
        return {
            'url': url,
            'business_name': "",
            'emails': [],
            'phones': [],
            'title': "",
            'success': False,
            'error': str(e)
        }

def process_websites_for_contacts(urls, max_sites=30):
    """Process websites to extract real contact information"""
    print(f"\\n🌐 EXTRACTING CONTACT INFO FROM {len(urls)} WEBSITES")
    print("=" * 60)
    
    leads = []
    processed = 0
    successful = 0
    
    for i, url_data in enumerate(urls):
        if processed >= max_sites:
            break
            
        url = url_data['url']
        print(f"\\nProcessing {i+1}/{min(len(urls), max_sites)}: {url[:60]}...")
        
        contact_info = extract_contact_info(url)
        processed += 1
        
        if contact_info and contact_info['success']:
            if contact_info['emails']:  # Only include if we found emails
                successful += 1
                
                # Create leads for each email found
                for j, email in enumerate(contact_info['emails']):
                    lead = {
                        'business_name': contact_info['business_name'],
                        'website': url,
                        'email': email,
                        'phone': contact_info['phones'][0] if contact_info['phones'] else "",
                        'source_query': url_data['query'],
                        'page_title': contact_info['title'][:100],
                        'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'lead_type': 'Primary' if j == 0 else 'Secondary'
                    }
                    leads.append(lead)
                
                print(f"  ✓ SUCCESS: {contact_info['business_name']}")
                print(f"    Emails: {', '.join(contact_info['emails'])}")
                if contact_info['phones']:
                    print(f"    Phones: {', '.join(contact_info['phones'])}")
            else:
                print(f"  ⚠️ No emails found")
        else:
            error = contact_info.get('error', 'Unknown error') if contact_info else 'Failed to process'
            print(f"  ✗ FAILED: {error}")
        
        # Be polite - don't hammer websites
        time.sleep(random.uniform(1, 3))
    
    print(f"\\n✓ Processed: {processed} websites")
    print(f"✓ Successful: {successful} websites with emails")
    print(f"✓ Total leads: {len(leads)}")
    
    return leads

def save_real_leads(leads, filename='out/real_restaurant_leads.csv'):
    """Save real leads to CSV"""
    print(f"\\n💾 SAVING REAL LEADS TO {filename}")
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        if leads:
            fieldnames = leads[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for lead in leads:
                writer.writerow(lead)
    
    print(f"✅ Saved {len(leads)} REAL leads to {filename}")
    
    # Show sample leads
    print("\\n📋 Sample Real Leads:")
    for i, lead in enumerate(leads[:10]):
        print(f"  {i+1:2d}. {lead['business_name'][:30]:30s} | {lead['email']:35s}")
    
    if len(leads) > 10:
        print(f"       ... and {len(leads) - 10} more")
    
    return filename

def main():
    """Get real restaurant leads"""
    print("🎯 GETTING REAL RESTAURANT LEADS")
    print("This will search real websites and extract actual contact information")
    print()
    
    # Real restaurant search queries
    search_queries = [
        "restaurant New York contact email",
        "restaurant Los Angeles owner email", 
        "restaurant Chicago contact information",
        "restaurant Houston manager contact",
        "restaurant Phoenix owner email",
        "restaurant Philadelphia restaurant contact",
        "restaurant San Antonio email address",
        "restaurant San Diego contact info",
        "restaurant Dallas restaurant email",
        "restaurant Seattle restaurant contact"
    ]
    
    start_time = time.time()
    
    # Step 1: Get real URLs from Bing
    urls = get_real_bing_results(search_queries, max_results=50)
    
    if not urls:
        print("❌ No URLs found. Cannot proceed.")
        return None, None
    
    # Step 2: Extract real contact info from websites
    leads = process_websites_for_contacts(urls, max_sites=50)
    
    if not leads:
        print("❌ No contact information found. Try different search queries.")
        return None, None
    
    # Step 3: Save real leads
    filename = save_real_leads(leads)
    
    # Summary
    duration = time.time() - start_time
    print(f"\\n⏱️  Total time: {duration:.1f} seconds")
    print(f"📊 Success rate: {len(leads)/len(urls)*100:.1f}% (found contacts on {len(leads)} of {len(urls)} sites)")
    
    print(f"\\n🎉 SUCCESS: Generated {len(leads)} REAL restaurant leads!")
    print(f"📁 File: {filename}")
    print("✅ These are actual businesses you can contact for podcast opportunities!")
    
    return leads, filename

if __name__ == "__main__":
    leads, filename = main()
    if leads:
        print(f"\\n✅ DONE: {len(leads)} real leads ready for outreach!")
    else:
        print("\\n❌ FAILED: Could not generate real leads")
        sys.exit(1)