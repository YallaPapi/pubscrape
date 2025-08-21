#!/usr/bin/env python3
"""
Professor scraper using more accessible university directories and Google Scholar.
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class AccessibleProfessorScraper:
    """Scraper using accessible methods to find professors."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def search_google_scholar(self, query, num_results=20):
        """Search Google Scholar for professors in a field."""
        professors = []
        
        # Google Scholar search URL
        base_url = "https://scholar.google.com/citations"
        params = {
            'view_op': 'search_authors',
            'mauthors': query,
            'hl': 'en'
        }
        
        try:
            response = self.session.get(base_url, params=params, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find author entries
            author_entries = soup.find_all('div', class_='gs_ai_t')
            
            for entry in author_entries[:num_results]:
                try:
                    # Extract name
                    name_elem = entry.find('h3', class_='gs_ai_name')
                    name = name_elem.get_text(strip=True) if name_elem else None
                    
                    # Extract affiliation
                    aff_elem = entry.find('div', class_='gs_ai_aff')
                    affiliation = aff_elem.get_text(strip=True) if aff_elem else ''
                    
                    # Extract email if verified
                    email_elem = entry.find('div', class_='gs_ai_eml')
                    email = None
                    if email_elem:
                        email_text = email_elem.get_text(strip=True)
                        # Extract domain from "Verified email at domain.edu"
                        match = re.search(r'at\s+([\w\.-]+\.edu)', email_text)
                        if match:
                            domain = match.group(1)
                            # Guess email from name and domain
                            if name:
                                first_last = name.lower().split()
                                if len(first_last) >= 2:
                                    email = f"{first_last[0]}.{first_last[-1]}@{domain}"
                    
                    # Extract research interests
                    interests_elem = entry.find('div', class_='gs_ai_int')
                    interests = interests_elem.get_text(strip=True) if interests_elem else ''
                    
                    if name and affiliation:
                        professors.append({
                            'name': name,
                            'email': email,
                            'affiliation': affiliation,
                            'research_interests': interests,
                            'source': 'Google Scholar'
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing entry: {e}")
                    
        except Exception as e:
            logger.error(f"Error searching Google Scholar: {e}")
            
        return professors
    
    def get_berkeley_faculty(self):
        """UC Berkeley EECS has an accessible directory."""
        professors = []
        url = "https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html"
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Berkeley uses a simple table structure
            rows = soup.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # First cell usually has name
                    name_cell = cells[0]
                    name_link = name_cell.find('a')
                    if name_link:
                        name = name_link.get_text(strip=True)
                        
                        # Try to find email
                        email = None
                        for cell in cells:
                            cell_text = cell.get_text()
                            email_match = re.search(r'([\w\.-]+)@([\w\.-]+\.edu)', cell_text)
                            if email_match:
                                email = email_match.group(0)
                                break
                        
                        # If no email found, construct from name
                        if not email and name:
                            # Berkeley pattern: firstname@berkeley.edu or lastname@berkeley.edu
                            name_parts = name.lower().split()
                            if name_parts:
                                email = f"{name_parts[-1]}@berkeley.edu"
                        
                        professors.append({
                            'name': name,
                            'email': email,
                            'affiliation': 'UC Berkeley EECS',
                            'research_interests': '',
                            'source': 'Berkeley Directory'
                        })
                        
        except Exception as e:
            logger.error(f"Error scraping Berkeley: {e}")
            
        return professors
    
    def get_university_ai_labs(self):
        """Get professors from various AI lab pages."""
        professors = []
        
        # List of AI lab pages that might be accessible
        ai_labs = [
            {
                'name': 'MIT AI Lab',
                'search_term': 'MIT artificial intelligence professor'
            },
            {
                'name': 'Stanford AI',  
                'search_term': 'Stanford machine learning professor'
            },
            {
                'name': 'CMU AI',
                'search_term': 'Carnegie Mellon AI robotics professor'
            },
            {
                'name': 'Berkeley AI',
                'search_term': 'Berkeley deep learning professor'
            },
            {
                'name': 'Harvard AI',
                'search_term': 'Harvard computer science AI professor'
            }
        ]
        
        for lab in ai_labs:
            logger.info(f"Searching for {lab['name']} professors...")
            results = self.search_google_scholar(lab['search_term'], num_results=10)
            professors.extend(results)
            time.sleep(2)  # Be respectful to Google Scholar
            
        return professors
    
    def create_email_from_name(self, name, university):
        """Create likely email addresses from name and university."""
        if not name or not university:
            return []
        
        # Common university email domains
        domain_map = {
            'MIT': 'mit.edu',
            'Stanford': 'stanford.edu',
            'Berkeley': 'berkeley.edu',
            'CMU': 'cmu.edu',
            'Carnegie Mellon': 'cmu.edu',
            'Harvard': 'harvard.edu',
            'Princeton': 'princeton.edu',
            'Yale': 'yale.edu',
            'Columbia': 'columbia.edu',
            'Cornell': 'cornell.edu'
        }
        
        # Find matching domain
        domain = None
        for uni, dom in domain_map.items():
            if uni.lower() in university.lower():
                domain = dom
                break
        
        if not domain:
            return []
        
        # Create email variations
        name_parts = name.lower().replace(',', '').replace('.', '').split()
        if len(name_parts) >= 2:
            first = name_parts[0]
            last = name_parts[-1]
            
            return [
                f"{first}.{last}@{domain}",
                f"{last}@{domain}",
                f"{first[0]}{last}@{domain}",
                f"{first}@{domain}"
            ]
        
        return []

def main():
    """Run the accessible professor scraper."""
    print("\n" + "="*80)
    print("ACCESSIBLE PROFESSOR SCRAPER")
    print("Using Google Scholar and public directories")
    print("="*80)
    
    scraper = AccessibleProfessorScraper()
    all_professors = []
    
    # Method 1: Try Berkeley's accessible directory
    print("\n[1/3] Scraping UC Berkeley EECS...")
    berkeley_profs = scraper.get_berkeley_faculty()
    all_professors.extend(berkeley_profs)
    print(f"Found {len(berkeley_profs)} Berkeley professors")
    
    # Method 2: Search Google Scholar for AI professors
    print("\n[2/3] Searching Google Scholar for AI professors...")
    ai_profs = scraper.get_university_ai_labs()
    all_professors.extend(ai_profs)
    print(f"Found {len(ai_profs)} AI professors via Google Scholar")
    
    # Method 3: Search for specific well-known professors
    print("\n[3/3] Searching for well-known AI researchers...")
    famous_researchers = [
        "Geoffrey Hinton deep learning",
        "Yann LeCun neural networks",
        "Andrew Ng machine learning",
        "Fei-Fei Li computer vision",
        "Yoshua Bengio deep learning",
        "Ian Goodfellow GAN",
        "Demis Hassabis DeepMind"
    ]
    
    for researcher in famous_researchers:
        results = scraper.search_google_scholar(researcher, num_results=1)
        all_professors.extend(results)
        time.sleep(1)
    
    # Remove duplicates
    seen = set()
    unique_professors = []
    for prof in all_professors:
        key = (prof['name'], prof['affiliation'])
        if key not in seen:
            seen.add(key)
            unique_professors.append(prof)
    
    # Add AI relevance scoring
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning',
                   'neural', 'nlp', 'computer vision', 'robotics', 'data science']
    
    for prof in unique_professors:
        score = 0
        interests = prof.get('research_interests', '').lower()
        for keyword in ai_keywords:
            if keyword in interests:
                score += 20
        prof['ai_relevance_score'] = min(score, 100)
    
    # Sort by AI relevance
    unique_professors.sort(key=lambda x: x.get('ai_relevance_score', 0), reverse=True)
    
    # Save results
    if unique_professors:
        output_dir = Path("university_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_dir / f"ai_professors_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'email', 'affiliation', 'research_interests', 
                         'ai_relevance_score', 'source']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_professors)
        
        print(f"\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"Total professors found: {len(unique_professors)}")
        print(f"With emails: {sum(1 for p in unique_professors if p.get('email'))}")
        print(f"CSV saved to: {csv_path}")
        
        print(f"\nTop AI professors found:")
        for i, prof in enumerate(unique_professors[:10], 1):
            print(f"\n{i}. {prof['name']}")
            print(f"   Affiliation: {prof['affiliation']}")
            print(f"   Email: {prof.get('email', 'Not found')}")
            print(f"   Research: {prof.get('research_interests', '')[:80]}...")
            print(f"   AI Score: {prof.get('ai_relevance_score', 0)}")
    else:
        print("\nNo professors found. Google Scholar might be blocking.")

if __name__ == "__main__":
    main()