#!/usr/bin/env python3
"""
Quick test of university professor scraping.
Starting with universities that have simple, accessible faculty directories.
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

def scrape_simple_faculty_page():
    """Test with a simple faculty page."""
    
    print("\n" + "="*80)
    print("UNIVERSITY PROFESSOR SCRAPER - QUICK TEST")
    print("="*80)
    
    # Test with a few known accessible faculty pages
    test_urls = [
        {
            'university': 'MIT CSAIL',
            'url': 'https://www.csail.mit.edu/people',
            'dept': 'Computer Science & AI Lab'
        },
        {
            'university': 'Stanford AI Lab',
            'url': 'https://ai.stanford.edu/people/',
            'dept': 'Artificial Intelligence'
        },
        {
            'university': 'CMU Machine Learning',
            'url': 'https://www.ml.cmu.edu/people/core-faculty.html',
            'dept': 'Machine Learning'
        }
    ]
    
    all_professors = []
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    for target in test_urls:
        print(f"\n[Scraping {target['university']}]")
        print(f"URL: {target['url']}")
        
        try:
            response = session.get(target['url'], timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Strategy 1: Find all email links
            email_links = soup.find_all('a', href=re.compile(r'mailto:'))
            print(f"Found {len(email_links)} email links")
            
            # Strategy 2: Find email patterns in text
            text = soup.get_text()
            email_pattern = re.findall(r'[\w\.-]+@[\w\.-]+\.edu', text)
            unique_emails = list(set(email_pattern))
            print(f"Found {len(unique_emails)} emails via pattern matching")
            
            # Extract professor info from email links
            for email_link in email_links[:10]:  # Limit for testing
                email = email_link.get('href').replace('mailto:', '').strip()
                
                # Try to find the professor's name
                # Usually the name is near the email link
                parent = email_link.parent
                name = None
                
                # Look for text that could be a name
                for elem in [email_link.previous_sibling, email_link.next_sibling, parent]:
                    if elem and hasattr(elem, 'get_text'):
                        text = elem.get_text(strip=True)
                    elif isinstance(elem, str):
                        text = elem.strip()
                    else:
                        continue
                        
                    # Check if it looks like a name
                    if text and len(text) > 3 and len(text) < 50 and not '@' in text:
                        # Basic name detection: starts with capital letter
                        if text[0].isupper():
                            name = text
                            break
                
                # If no name found, try to extract from email
                if not name and email:
                    email_prefix = email.split('@')[0]
                    # Convert email to name (e.g., john.smith -> John Smith)
                    name = ' '.join(email_prefix.split('.')).title()
                
                if email and '@' in email:
                    all_professors.append({
                        'name': name or 'Unknown',
                        'email': email,
                        'university': target['university'],
                        'department': target['dept']
                    })
            
            # Also try pattern matching approach
            for email in unique_emails[:10]:
                if email not in [p['email'] for p in all_professors]:
                    # Extract name from email
                    email_prefix = email.split('@')[0]
                    name = ' '.join(email_prefix.replace('_', '.').split('.')).title()
                    
                    all_professors.append({
                        'name': name,
                        'email': email,
                        'university': target['university'],
                        'department': target['dept']
                    })
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {target['university']}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {target['university']}: {e}")
    
    # Filter for likely professors (edu emails)
    professors = [p for p in all_professors if p['email'].endswith('.edu')]
    
    # Remove duplicates
    seen_emails = set()
    unique_professors = []
    for prof in professors:
        if prof['email'] not in seen_emails:
            seen_emails.add(prof['email'])
            unique_professors.append(prof)
    
    # Save to CSV
    if unique_professors:
        output_dir = Path("university_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_dir / f"professors_test_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'email', 'university', 'department']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_professors)
        
        print(f"\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"Total professors found: {len(unique_professors)}")
        print(f"CSV saved to: {csv_path}")
        
        print(f"\nSample professors found:")
        for prof in unique_professors[:5]:
            print(f"  • {prof['name']} - {prof['email']} ({prof['university']})")
    else:
        print("\nNo professors found. The websites might have changed their structure.")

if __name__ == "__main__":
    scrape_simple_faculty_page()