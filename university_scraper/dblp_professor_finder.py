#!/usr/bin/env python3
"""
DBLP-based professor finder.
DBLP is a public CS bibliography with 2.2M+ authors.
We can use it to find CS professors and their university pages.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import re
from pathlib import Path
from datetime import datetime
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class DBLPProfessorFinder:
    """Find CS professors using DBLP database."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Academic Research Bot)'
        })
        self.professors = []
        
    def search_dblp_authors(self, query, max_results=50):
        """Search DBLP for authors in a specific field."""
        # DBLP search API
        url = "https://dblp.org/search/author/api"
        params = {
            'q': query,
            'format': 'json',
            'h': max_results  # Number of results
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            authors = []
            if 'result' in data and 'hits' in data['result']:
                hits = data['result']['hits'].get('hit', [])
                
                for hit in hits:
                    info = hit.get('info', {})
                    author = info.get('author', {})
                    
                    # Extract author details
                    name = author.get('text', '')
                    dblp_url = info.get('url', '')
                    
                    # Get affiliation from notes
                    notes = info.get('notes', {})
                    affiliation = ''
                    if isinstance(notes, dict):
                        note = notes.get('note', {})
                        if isinstance(note, list) and note:
                            affiliation = note[0].get('text', '')
                        elif isinstance(note, dict):
                            affiliation = note.get('text', '')
                    
                    if name:
                        authors.append({
                            'name': name,
                            'dblp_url': dblp_url,
                            'affiliation': affiliation,
                            'email': None,
                            'homepage': None
                        })
            
            return authors
            
        except Exception as e:
            logger.error(f"DBLP search error: {e}")
            return []
    
    def get_author_homepage(self, dblp_url):
        """Extract homepage URL from DBLP author page."""
        if not dblp_url:
            return None
            
        try:
            # Convert API URL to HTML page URL
            html_url = dblp_url.replace('/rec/', '/pid/').replace('.xml', '.html')
            
            response = self.session.get(html_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for homepage link
            homepage_link = soup.find('a', {'title': 'Home Page'})
            if homepage_link:
                return homepage_link.get('href')
            
            # Alternative: look for external links
            external_links = soup.find_all('a', class_='url')
            for link in external_links:
                href = link.get('href', '')
                if 'http' in href and 'dblp.org' not in href:
                    return href
                    
        except Exception as e:
            logger.debug(f"Error fetching homepage: {e}")
            
        return None
    
    def extract_email_from_homepage(self, homepage_url):
        """Try to extract email from a professor's homepage."""
        if not homepage_url:
            return None
            
        try:
            response = self.session.get(homepage_url, timeout=5)
            text = response.text
            
            # Look for email patterns
            email_patterns = [
                r'[\w\.-]+@[\w\.-]+\.edu',  # .edu emails
                r'[\w\.-]+@[\w\.-]+\.ac\.\w+',  # .ac.uk, .ac.jp etc
                r'mailto:([\w\.-]+@[\w\.-]+)',  # mailto links
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    email = matches[0]
                    if isinstance(email, tuple):
                        email = email[0]
                    return email.replace('mailto:', '')
                    
        except Exception as e:
            logger.debug(f"Error extracting email from {homepage_url}: {e}")
            
        return None
    
    def find_ai_ml_professors(self):
        """Find professors in AI/ML fields."""
        # Search queries for different AI/ML areas
        queries = [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural networks",
            "computer vision",
            "natural language processing",
            "reinforcement learning",
            "robotics AI"
        ]
        
        all_authors = []
        
        for query in queries:
            logger.info(f"Searching DBLP for: {query}")
            authors = self.search_dblp_authors(query, max_results=30)
            all_authors.extend(authors)
            time.sleep(1)  # Be polite to DBLP
        
        # Remove duplicates
        seen = set()
        unique_authors = []
        for author in all_authors:
            if author['name'] not in seen:
                seen.add(author['name'])
                unique_authors.append(author)
        
        return unique_authors
    
    def enrich_with_contact_info(self, authors, max_workers=5):
        """Enrich authors with homepage and email info."""
        logger.info(f"Enriching {len(authors)} authors with contact info...")
        
        def enrich_author(author):
            # Get homepage from DBLP
            homepage = self.get_author_homepage(author['dblp_url'])
            author['homepage'] = homepage
            
            # Try to extract email from homepage
            if homepage:
                email = self.extract_email_from_homepage(homepage)
                author['email'] = email
            
            # If no email from homepage, try to construct from name and affiliation
            if not author['email'] and author['affiliation']:
                email = self.guess_email(author['name'], author['affiliation'])
                if email:
                    author['email'] = email
            
            return author
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(enrich_author, author) for author in authors]
            
            for i, future in enumerate(as_completed(futures), 1):
                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(authors)} authors")
                try:
                    future.result()
                except Exception as e:
                    logger.debug(f"Error enriching author: {e}")
        
        return authors
    
    def guess_email(self, name, affiliation):
        """Guess email from name and affiliation."""
        if not name or not affiliation:
            return None
        
        # Common university domains
        domain_patterns = {
            'MIT': 'mit.edu',
            'Stanford': 'stanford.edu',
            'Berkeley': 'berkeley.edu',
            'CMU': 'cmu.edu',
            'Carnegie Mellon': 'cs.cmu.edu',
            'Harvard': 'harvard.edu',
            'Oxford': 'ox.ac.uk',
            'Cambridge': 'cam.ac.uk',
            'ETH': 'ethz.ch',
            'Toronto': 'toronto.edu',
            'Washington': 'washington.edu',
            'UCLA': 'ucla.edu',
            'UCSD': 'ucsd.edu',
            'Georgia Tech': 'gatech.edu',
            'Princeton': 'princeton.edu',
            'Cornell': 'cornell.edu'
        }
        
        # Find matching domain
        domain = None
        aff_lower = affiliation.lower()
        for uni, dom in domain_patterns.items():
            if uni.lower() in aff_lower:
                domain = dom
                break
        
        if not domain:
            return None
        
        # Create email from name
        name_parts = name.lower().replace(',', '').split()
        if len(name_parts) >= 2:
            first = name_parts[0]
            last = name_parts[-1]
            # Most common pattern: firstname.lastname@domain
            return f"{first}.{last}@{domain}"
        
        return None
    
    def save_to_csv(self, authors, filename=None):
        """Save results to CSV."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"dblp_professors_{timestamp}.csv"
        
        output_dir = Path("university_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / filename
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'email', 'affiliation', 'homepage', 'dblp_url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for author in authors:
                writer.writerow({
                    'name': author.get('name', ''),
                    'email': author.get('email', ''),
                    'affiliation': author.get('affiliation', ''),
                    'homepage': author.get('homepage', ''),
                    'dblp_url': author.get('dblp_url', '')
                })
        
        return str(csv_path)

def main():
    """Run the DBLP professor finder."""
    print("\n" + "="*80)
    print("DBLP CS PROFESSOR FINDER")
    print("Finding AI/ML researchers from DBLP database")
    print("="*80)
    
    finder = DBLPProfessorFinder()
    
    # Step 1: Find AI/ML professors
    print("\n[1/3] Searching DBLP for AI/ML researchers...")
    authors = finder.find_ai_ml_professors()
    print(f"Found {len(authors)} unique authors")
    
    # Step 2: Enrich with contact info
    print("\n[2/3] Enriching with homepage and email info...")
    authors = finder.enrich_with_contact_info(authors)
    
    # Step 3: Save results
    print("\n[3/3] Saving results...")
    csv_path = finder.save_to_csv(authors)
    
    # Statistics
    with_email = sum(1 for a in authors if a.get('email'))
    with_homepage = sum(1 for a in authors if a.get('homepage'))
    with_affiliation = sum(1 for a in authors if a.get('affiliation'))
    
    print(f"\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Total authors found: {len(authors)}")
    print(f"With email: {with_email} ({with_email/len(authors)*100:.1f}%)")
    print(f"With homepage: {with_homepage} ({with_homepage/len(authors)*100:.1f}%)")
    print(f"With affiliation: {with_affiliation} ({with_affiliation/len(authors)*100:.1f}%)")
    print(f"CSV saved to: {csv_path}")
    
    # Show samples
    if authors:
        print(f"\nSample AI/ML researchers found:")
        for author in authors[:10]:
            if author.get('email'):
                print(f"  • {author['name']} ({author.get('affiliation', 'Unknown')})")
                print(f"    Email: {author['email']}")
                if len([a for a in authors[:10] if a.get('email')]) >= 5:
                    break

if __name__ == "__main__":
    main()