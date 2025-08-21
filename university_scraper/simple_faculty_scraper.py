#!/usr/bin/env python3
"""
Simple faculty scraper using known public directories.
Many universities have simple HTML pages with faculty emails.
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_public_faculty_lists():
    """Scrape faculty from universities with public, simple directories."""
    
    all_faculty = []
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Academic Research)'
    })
    
    # List of universities with accessible faculty pages
    # These are real, working URLs with faculty info
    faculty_sources = [
        {
            'name': 'MIT CSAIL People',
            'url': 'https://www.csail.mit.edu/about/people/type/11',
            'method': 'csail'
        },
        {
            'name': 'Princeton CS',
            'url': 'https://www.cs.princeton.edu/people/faculty',
            'method': 'princeton'
        },
        {
            'name': 'Yale CS',
            'url': 'https://cpsc.yale.edu/people/faculty',
            'method': 'yale'
        },
        {
            'name': 'Cornell CS',
            'url': 'https://www.cs.cornell.edu/people/faculty',
            'method': 'cornell'
        },
        {
            'name': 'NYU CS',
            'url': 'https://cs.nyu.edu/dynamic/people/faculty/',
            'method': 'nyu'
        }
    ]
    
    # Also try some direct faculty lists that are just HTML tables
    simple_lists = [
        'https://www.cs.utexas.edu/people/faculty',
        'https://www.cs.purdue.edu/people/faculty/',
        'https://www.cs.wisc.edu/people/faculty/',
        'https://cs.illinois.edu/about/people/all-faculty'
    ]
    
    print("\n" + "="*80)
    print("SIMPLE FACULTY SCRAPER")
    print("="*80)
    
    # Method 1: Scrape specific university pages
    for source in faculty_sources:
        print(f"\n[Trying {source['name']}]")
        try:
            response = session.get(source['url'], timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all email addresses on the page
            emails_found = re.findall(r'[\w\.-]+@[\w\.-]+\.edu', response.text)
            unique_emails = list(set(emails_found))
            
            print(f"  Found {len(unique_emails)} unique .edu emails")
            
            for email in unique_emails[:20]:  # Limit to 20 per university
                # Try to find name associated with email
                name = extract_name_near_email(soup, email)
                if not name:
                    # Generate name from email
                    name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                
                all_faculty.append({
                    'name': name,
                    'email': email,
                    'university': source['name'],
                    'department': 'Computer Science'
                })
                
        except Exception as e:
            logger.error(f"  Error: {e}")
    
    # Method 2: Try simple email extraction from other pages
    for url in simple_lists:
        uni_name = extract_uni_name(url)
        print(f"\n[Trying {uni_name}]")
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.edu', response.text)
                unique = list(set(emails))
                print(f"  Found {len(unique)} emails")
                
                for email in unique[:10]:
                    name = email.split('@')[0].replace('.', ' ').title()
                    all_faculty.append({
                        'name': name,
                        'email': email,
                        'university': uni_name,
                        'department': 'Computer Science'
                    })
        except:
            print(f"  Could not access")
    
    # Method 3: Try some known AI lab pages
    ai_labs = [
        ('MIT AI Lab', 'https://www.ai.mit.edu/people.html'),
        ('Stanford Vision Lab', 'https://vision.stanford.edu/people.html'),
        ('Berkeley AI Research', 'https://bair.berkeley.edu/students.html')
    ]
    
    for lab_name, url in ai_labs:
        print(f"\n[Trying {lab_name}]")
        try:
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.edu', response.text)
                print(f"  Found {len(set(emails))} emails")
                for email in list(set(emails))[:5]:
                    all_faculty.append({
                        'name': email.split('@')[0].replace('.', ' ').title(),
                        'email': email,
                        'university': lab_name,
                        'department': 'AI Research'
                    })
        except:
            print(f"  Could not access")
    
    # Remove duplicates
    seen = set()
    unique_faculty = []
    for person in all_faculty:
        if person['email'] not in seen:
            seen.add(person['email'])
            unique_faculty.append(person)
    
    return unique_faculty

def extract_name_near_email(soup, email):
    """Try to find a name near an email address in HTML."""
    # Look for the email in links
    email_links = soup.find_all('a', href=f'mailto:{email}')
    if email_links:
        link = email_links[0]
        # Check link text
        if link.get_text(strip=True):
            return link.get_text(strip=True)
        # Check parent
        parent = link.parent
        if parent and parent.get_text(strip=True):
            text = parent.get_text(strip=True)
            if len(text) < 50:  # Reasonable name length
                return text
    return None

def extract_uni_name(url):
    """Extract university name from URL."""
    if 'utexas' in url:
        return 'UT Austin CS'
    elif 'purdue' in url:
        return 'Purdue CS'
    elif 'wisc' in url:
        return 'Wisconsin CS'
    elif 'illinois' in url:
        return 'UIUC CS'
    else:
        return 'University CS'

def main():
    """Run the simple faculty scraper."""
    
    # Scrape faculty
    faculty = scrape_public_faculty_lists()
    
    if faculty:
        # Add AI relevance scoring
        ai_keywords = ['ai', 'machine', 'learning', 'neural', 'vision', 'nlp', 'robotics']
        for person in faculty:
            score = 0
            email_lower = person['email'].lower()
            for keyword in ai_keywords:
                if keyword in email_lower:
                    score += 20
            # Bonus for AI labs
            if 'AI' in person.get('department', ''):
                score += 30
            person['ai_relevance'] = min(score, 100)
        
        # Sort by AI relevance
        faculty.sort(key=lambda x: x.get('ai_relevance', 0), reverse=True)
        
        # Save to CSV
        output_dir = Path("university_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_dir / f"faculty_emails_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'email', 'university', 'department', 'ai_relevance']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(faculty)
        
        print(f"\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"Total faculty found: {len(faculty)}")
        print(f"CSV saved to: {csv_path}")
        
        print(f"\nSample faculty with emails:")
        for person in faculty[:10]:
            print(f"  • {person['name']} - {person['email']}")
            print(f"    {person['university']}, AI relevance: {person.get('ai_relevance', 0)}")
    else:
        print("\nNo faculty found. Universities may be blocking scrapers.")

if __name__ == "__main__":
    main()