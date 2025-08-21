#!/usr/bin/env python3
"""
University Professor Scraper - Find AI/CS professors as potential podcast guests.
Targets top universities' Computer Science and AI departments.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import re
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniversityProfessorScraper:
    """Scraper for university faculty directories."""
    
    def __init__(self):
        self.professors = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_top_cs_universities(self):
        """List of top CS universities with their faculty page URLs."""
        # Top universities for CS/AI with direct faculty page URLs
        universities = [
            {
                'name': 'MIT',
                'url': 'https://www.eecs.mit.edu/people',
                'type': 'mit'
            },
            {
                'name': 'Stanford',
                'url': 'https://cs.stanford.edu/directory/faculty',
                'type': 'stanford'
            },
            {
                'name': 'Carnegie Mellon',
                'url': 'https://www.cs.cmu.edu/directory/all',
                'type': 'cmu'
            },
            {
                'name': 'UC Berkeley',
                'url': 'https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html',
                'type': 'berkeley'
            },
            {
                'name': 'Harvard',
                'url': 'https://seas.harvard.edu/computer-science/faculty-research',
                'type': 'harvard'
            },
            {
                'name': 'University of Washington',
                'url': 'https://www.cs.washington.edu/people/faculty',
                'type': 'uw'
            },
            {
                'name': 'Georgia Tech',
                'url': 'https://www.cc.gatech.edu/people/faculty',
                'type': 'gatech'
            },
            {
                'name': 'University of Toronto',
                'url': 'https://web.cs.toronto.edu/faculty',
                'type': 'toronto'
            },
            {
                'name': 'Oxford',
                'url': 'https://www.cs.ox.ac.uk/people/faculty.html',
                'type': 'oxford'
            },
            {
                'name': 'Cambridge',
                'url': 'https://www.cst.cam.ac.uk/people/academic-staff',
                'type': 'cambridge'
            }
        ]
        return universities
    
    def scrape_mit_faculty(self, url):
        """Scrape MIT EECS faculty."""
        logger.info("Scraping MIT faculty...")
        professors = []
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # MIT specific selectors (you'd need to inspect actual page)
            faculty_cards = soup.find_all('div', class_='people-card') or \
                          soup.find_all('div', class_='faculty-member') or \
                          soup.find_all('article', class_='person')
            
            for card in faculty_cards[:20]:  # Limit for testing
                prof = self.extract_basic_info(card)
                if prof:
                    prof['university'] = 'MIT'
                    professors.append(prof)
                    
        except Exception as e:
            logger.error(f"Error scraping MIT: {e}")
            
        return professors
    
    def scrape_stanford_faculty(self, url):
        """Scrape Stanford CS faculty."""
        logger.info("Scraping Stanford faculty...")
        professors = []
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Stanford specific parsing
            faculty_list = soup.find_all('div', class_='faculty-item') or \
                          soup.find_all('tr', class_='person') or \
                          soup.find_all('div', class_='person-info')
            
            for item in faculty_list[:20]:
                prof = self.extract_basic_info(item)
                if prof:
                    prof['university'] = 'Stanford'
                    professors.append(prof)
                    
        except Exception as e:
            logger.error(f"Error scraping Stanford: {e}")
            
        return professors
    
    def extract_basic_info(self, element):
        """Extract basic professor info from HTML element."""
        try:
            # Try multiple common patterns
            name = None
            email = None
            title = None
            research = None
            website = None
            
            # Extract name
            name_elem = element.find(['h3', 'h4', 'h5', 'a', 'span'], class_=re.compile('name|title'))
            if name_elem:
                name = name_elem.get_text(strip=True)
            
            # Extract email
            email_link = element.find('a', href=re.compile(r'mailto:'))
            if email_link:
                email = email_link.get('href').replace('mailto:', '')
            else:
                # Look for email pattern in text
                text = element.get_text()
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                if email_match:
                    email = email_match.group()
            
            # Extract title/position
            title_elem = element.find(['span', 'p', 'div'], class_=re.compile('title|position|role'))
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Extract research areas
            research_elem = element.find(['p', 'div', 'span'], class_=re.compile('research|interests|areas'))
            if research_elem:
                research = research_elem.get_text(strip=True)[:200]  # Limit length
            
            # Extract personal website
            website_link = element.find('a', href=re.compile(r'^https?://'))
            if website_link and 'mailto:' not in website_link.get('href'):
                website = website_link.get('href')
            
            if name:
                return {
                    'name': name,
                    'email': email,
                    'title': title or 'Professor',
                    'research_areas': research,
                    'website': website
                }
                
        except Exception as e:
            logger.debug(f"Error extracting info: {e}")
            
        return None
    
    def scrape_generic_faculty_page(self, url, university_name):
        """Generic scraper for faculty pages."""
        logger.info(f"Scraping {university_name} faculty...")
        professors = []
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all email links on the page
            email_links = soup.find_all('a', href=re.compile(r'mailto:'))
            
            for email_link in email_links[:30]:  # Limit for testing
                email = email_link.get('href').replace('mailto:', '').strip()
                
                # Try to find the name near the email
                parent = email_link.parent
                name = None
                
                # Look for name in parent or siblings
                for elem in [email_link, parent] + list(parent.find_all(['h3', 'h4', 'strong', 'b'])):
                    text = elem.get_text(strip=True)
                    # Simple heuristic: if it looks like a name (2-4 words, title case)
                    if text and 2 <= len(text.split()) <= 4 and not '@' in text:
                        if text[0].isupper():
                            name = text
                            break
                
                if not name:
                    # Try to extract from email
                    name_part = email.split('@')[0]
                    name = name_part.replace('.', ' ').replace('_', ' ').title()
                
                professors.append({
                    'name': name,
                    'email': email,
                    'university': university_name,
                    'title': 'Professor',
                    'research_areas': None,
                    'website': None
                })
                
        except Exception as e:
            logger.error(f"Error scraping {university_name}: {e}")
            
        return professors
    
    def scrape_all_universities(self):
        """Scrape all universities in parallel."""
        universities = self.get_top_cs_universities()
        all_professors = []
        
        print(f"\nScraping {len(universities)} top CS departments...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            for uni in universities:
                if uni['type'] == 'mit':
                    future = executor.submit(self.scrape_mit_faculty, uni['url'])
                elif uni['type'] == 'stanford':
                    future = executor.submit(self.scrape_stanford_faculty, uni['url'])
                else:
                    future = executor.submit(self.scrape_generic_faculty_page, uni['url'], uni['name'])
                
                futures[future] = uni['name']
            
            for future in as_completed(futures):
                uni_name = futures[future]
                try:
                    professors = future.result()
                    all_professors.extend(professors)
                    logger.info(f"Found {len(professors)} professors at {uni_name}")
                except Exception as e:
                    logger.error(f"Error processing {uni_name}: {e}")
        
        return all_professors
    
    def enrich_with_ai_keywords(self, professors):
        """Add AI/ML relevance scoring based on research areas."""
        ai_keywords = [
            'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'nlp', 'natural language', 'computer vision',
            'robotics', 'reinforcement learning', 'data science', 'AI',
            'ML', 'GPT', 'transformer', 'generative', 'LLM', 'large language'
        ]
        
        for prof in professors:
            score = 0
            research = (prof.get('research_areas') or '').lower()
            title = (prof.get('title') or '').lower()
            
            for keyword in ai_keywords:
                if keyword.lower() in research or keyword.lower() in title:
                    score += 10
            
            prof['ai_relevance_score'] = min(score, 100)
        
        # Sort by AI relevance
        professors.sort(key=lambda x: x.get('ai_relevance_score', 0), reverse=True)
        
        return professors
    
    def save_to_csv(self, professors, filename=None):
        """Save professors to CSV."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"university_professors_{timestamp}.csv"
        
        output_dir = Path("university_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / filename
        
        fieldnames = ['name', 'email', 'university', 'title', 
                     'research_areas', 'website', 'ai_relevance_score']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for prof in professors:
                writer.writerow({
                    'name': prof.get('name', ''),
                    'email': prof.get('email', ''),
                    'university': prof.get('university', ''),
                    'title': prof.get('title', ''),
                    'research_areas': prof.get('research_areas', ''),
                    'website': prof.get('website', ''),
                    'ai_relevance_score': prof.get('ai_relevance_score', 0)
                })
        
        logger.info(f"Saved {len(professors)} professors to {csv_path}")
        return str(csv_path)

def main():
    """Run the professor scraper."""
    print("\n" + "="*80)
    print("UNIVERSITY PROFESSOR SCRAPER")
    print("Target: Top CS/AI Departments")
    print("="*80)
    
    scraper = UniversityProfessorScraper()
    
    # Scrape all universities
    print("\n[Step 1/3] Scraping faculty directories...")
    professors = scraper.scrape_all_universities()
    
    # Add AI relevance scoring
    print(f"\n[Step 2/3] Scoring AI/ML relevance...")
    professors = scraper.enrich_with_ai_keywords(professors)
    
    # Save results
    print(f"\n[Step 3/3] Saving results...")
    csv_file = scraper.save_to_csv(professors)
    
    # Statistics
    with_email = sum(1 for p in professors if p.get('email'))
    with_ai_relevance = sum(1 for p in professors if p.get('ai_relevance_score', 0) > 0)
    
    print(f"\n" + "="*80)
    print("SCRAPING COMPLETE!")
    print("="*80)
    print(f"\nResults:")
    print(f"  • Total professors found: {len(professors)}")
    print(f"  • With email addresses: {with_email}")
    print(f"  • With AI/ML relevance: {with_ai_relevance}")
    print(f"  • CSV saved to: {csv_file}")
    
    if professors:
        print(f"\nTop 5 AI-relevant professors:")
        for i, prof in enumerate(professors[:5], 1):
            print(f"  {i}. {prof['name']} ({prof['university']})")
            print(f"     Email: {prof.get('email', 'N/A')}")
            print(f"     AI Score: {prof.get('ai_relevance_score', 0)}")

if __name__ == "__main__":
    main()