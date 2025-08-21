#!/usr/bin/env python3
"""
Conference Speaker Scraper
Scrapes speaker information from major tech/AI conferences.
Many conferences list speaker bios with contact info or social links.
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import json
from pathlib import Path
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConferenceSpeakerScraper:
    """Scraper for conference speaker information."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.speakers = []
        
    def get_major_conferences(self):
        """List of major tech/AI conferences with speaker pages."""
        conferences = [
            {
                'name': 'NeurIPS 2024',
                'url': 'https://neurips.cc/Conferences/2024/Speakers',
                'type': 'neurips',
                'topic': 'AI/ML'
            },
            {
                'name': 'ICML 2024',
                'url': 'https://icml.cc/Conferences/2024/Speakers',
                'type': 'icml',
                'topic': 'Machine Learning'
            },
            {
                'name': 'TED Talks',
                'url': 'https://www.ted.com/speakers',
                'type': 'ted',
                'topic': 'Various'
            },
            {
                'name': 'Google I/O 2024',
                'url': 'https://io.google/2024/speakers/',
                'type': 'google_io',
                'topic': 'Technology'
            },
            {
                'name': 'Microsoft Build',
                'url': 'https://mybuild.microsoft.com/speakers',
                'type': 'ms_build',
                'topic': 'Technology'
            },
            {
                'name': 'AWS re:Invent',
                'url': 'https://reinvent.awsevents.com/speakers/',
                'type': 'aws',
                'topic': 'Cloud/AI'
            },
            {
                'name': 'PyCon US',
                'url': 'https://us.pycon.org/2024/speakers/',
                'type': 'pycon',
                'topic': 'Python/Programming'
            },
            {
                'name': 'Web Summit',
                'url': 'https://websummit.com/speakers',
                'type': 'websummit',
                'topic': 'Technology/Startups'
            }
        ]
        return conferences
    
    def scrape_generic_speakers_page(self, url, conference_name):
        """Generic scraper for conference speaker pages."""
        speakers = []
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Could not access {conference_name}: Status {response.status_code}")
                return speakers
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Strategy 1: Look for speaker cards/divs
            speaker_elements = (
                soup.find_all('div', class_=re.compile(r'speaker|person|profile', re.I)) +
                soup.find_all('article', class_=re.compile(r'speaker|person', re.I)) +
                soup.find_all('li', class_=re.compile(r'speaker|person', re.I))
            )[:50]  # Limit to 50 to avoid huge pages
            
            for element in speaker_elements:
                speaker = self.extract_speaker_info(element)
                if speaker and speaker.get('name'):
                    speaker['conference'] = conference_name
                    speakers.append(speaker)
            
            # Strategy 2: Find all email addresses on the page
            if not speakers:
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', response.text)
                for email in list(set(emails))[:20]:
                    # Try to find name near email
                    name = self.extract_name_near_email(soup, email)
                    if not name:
                        name = email.split('@')[0].replace('.', ' ').title()
                    
                    speakers.append({
                        'name': name,
                        'email': email,
                        'conference': conference_name,
                        'title': None,
                        'company': None,
                        'bio': None,
                        'website': None,
                        'twitter': None,
                        'linkedin': None
                    })
            
            logger.info(f"Found {len(speakers)} speakers from {conference_name}")
            
        except Exception as e:
            logger.error(f"Error scraping {conference_name}: {e}")
            
        return speakers
    
    def extract_speaker_info(self, element):
        """Extract speaker information from HTML element."""
        speaker = {}
        
        try:
            # Extract name
            name_elem = element.find(['h2', 'h3', 'h4', 'h5'], class_=re.compile(r'name|title', re.I))
            if not name_elem:
                name_elem = element.find('a', class_=re.compile(r'name|speaker', re.I))
            if name_elem:
                speaker['name'] = name_elem.get_text(strip=True)
            
            # Extract title/position
            title_elem = element.find(['span', 'p', 'div'], class_=re.compile(r'title|position|role', re.I))
            if title_elem:
                speaker['title'] = title_elem.get_text(strip=True)
            
            # Extract company/organization
            company_elem = element.find(['span', 'p', 'div'], class_=re.compile(r'company|organization|affiliation', re.I))
            if company_elem:
                speaker['company'] = company_elem.get_text(strip=True)
            
            # Extract bio
            bio_elem = element.find(['p', 'div'], class_=re.compile(r'bio|description|about', re.I))
            if bio_elem:
                speaker['bio'] = bio_elem.get_text(strip=True)[:500]  # Limit bio length
            
            # Extract email
            email_link = element.find('a', href=re.compile(r'mailto:', re.I))
            if email_link:
                speaker['email'] = email_link.get('href').replace('mailto:', '')
            else:
                # Look for email in text
                text = element.get_text()
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                if email_match:
                    speaker['email'] = email_match.group()
            
            # Extract website
            website_link = element.find('a', href=re.compile(r'^https?://', re.I))
            if website_link and 'twitter' not in website_link.get('href') and 'linkedin' not in website_link.get('href'):
                speaker['website'] = website_link.get('href')
            
            # Extract social media
            twitter_link = element.find('a', href=re.compile(r'twitter\.com|x\.com', re.I))
            if twitter_link:
                speaker['twitter'] = twitter_link.get('href')
            
            linkedin_link = element.find('a', href=re.compile(r'linkedin\.com', re.I))
            if linkedin_link:
                speaker['linkedin'] = linkedin_link.get('href')
            
        except Exception as e:
            logger.debug(f"Error extracting speaker info: {e}")
            
        # Set defaults for missing fields
        for field in ['name', 'email', 'title', 'company', 'bio', 'website', 'twitter', 'linkedin']:
            if field not in speaker:
                speaker[field] = None
                
        return speaker
    
    def extract_name_near_email(self, soup, email):
        """Try to find a name near an email address."""
        # Look for email in links
        email_links = soup.find_all('a', href=f'mailto:{email}')
        if email_links:
            link = email_links[0]
            # Check surrounding text
            parent = link.parent
            if parent:
                text = parent.get_text(strip=True)
                # Look for name pattern (2-4 capitalized words)
                name_match = re.search(r'\b([A-Z][a-z]+ ){1,3}[A-Z][a-z]+\b', text)
                if name_match:
                    return name_match.group()
        return None
    
    def scrape_ted_speakers(self):
        """Special scraper for TED speakers (they have good data)."""
        speakers = []
        
        # TED has a JSON API for speakers
        try:
            # This is a simplified example - TED's actual API might need authentication
            response = self.session.get('https://www.ted.com/people/speakers', timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find speaker links
            speaker_links = soup.find_all('a', href=re.compile(r'/speakers/'))[:30]
            
            for link in speaker_links:
                name = link.get_text(strip=True)
                if name:
                    speakers.append({
                        'name': name,
                        'conference': 'TED',
                        'website': f"https://www.ted.com{link.get('href')}",
                        'email': None,
                        'title': 'TED Speaker',
                        'company': None,
                        'bio': None,
                        'twitter': None,
                        'linkedin': None
                    })
            
            logger.info(f"Found {len(speakers)} TED speakers")
            
        except Exception as e:
            logger.error(f"Error scraping TED: {e}")
            
        return speakers
    
    def scrape_all_conferences(self):
        """Scrape all conferences in parallel."""
        conferences = self.get_major_conferences()
        all_speakers = []
        
        print(f"\nScraping {len(conferences)} major conferences...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            for conf in conferences:
                if conf['type'] == 'ted':
                    future = executor.submit(self.scrape_ted_speakers)
                else:
                    future = executor.submit(self.scrape_generic_speakers_page, conf['url'], conf['name'])
                
                futures[future] = conf['name']
            
            for future in as_completed(futures):
                conf_name = futures[future]
                try:
                    speakers = future.result()
                    all_speakers.extend(speakers)
                except Exception as e:
                    logger.error(f"Error processing {conf_name}: {e}")
        
        return all_speakers
    
    def enrich_with_ai_relevance(self, speakers):
        """Add AI/tech relevance scoring."""
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural', 'nlp', 'computer vision', 'robotics', 'data science',
            'tech', 'software', 'startup', 'innovation', 'digital', 'cloud',
            'blockchain', 'crypto', 'web3', 'metaverse'
        ]
        
        for speaker in speakers:
            score = 0
            
            # Check bio
            bio = (speaker.get('bio') or '').lower()
            for keyword in ai_keywords:
                if keyword in bio:
                    score += 10
            
            # Check title
            title = (speaker.get('title') or '').lower()
            for keyword in ai_keywords:
                if keyword in title:
                    score += 15
            
            # Check company
            company = (speaker.get('company') or '').lower()
            tech_companies = ['google', 'microsoft', 'meta', 'apple', 'amazon', 'openai', 'anthropic']
            for tech_company in tech_companies:
                if tech_company in company:
                    score += 20
                    break
            
            # Bonus for certain conferences
            if 'NeurIPS' in speaker.get('conference', '') or 'ICML' in speaker.get('conference', ''):
                score += 30
            
            speaker['ai_relevance_score'] = min(score, 100)
        
        # Sort by AI relevance
        speakers.sort(key=lambda x: x.get('ai_relevance_score', 0), reverse=True)
        
        return speakers
    
    def save_to_csv(self, speakers, filename=None):
        """Save speakers to CSV."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"conference_speakers_{timestamp}.csv"
        
        output_dir = Path("conference_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / filename
        
        fieldnames = ['name', 'email', 'conference', 'title', 'company', 
                     'bio', 'website', 'twitter', 'linkedin', 'ai_relevance_score']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for speaker in speakers:
                writer.writerow({
                    'name': speaker.get('name', ''),
                    'email': speaker.get('email', ''),
                    'conference': speaker.get('conference', ''),
                    'title': speaker.get('title', ''),
                    'company': speaker.get('company', ''),
                    'bio': speaker.get('bio', ''),
                    'website': speaker.get('website', ''),
                    'twitter': speaker.get('twitter', ''),
                    'linkedin': speaker.get('linkedin', ''),
                    'ai_relevance_score': speaker.get('ai_relevance_score', 0)
                })
        
        logger.info(f"Saved {len(speakers)} speakers to {csv_path}")
        return str(csv_path)

def main():
    """Run the conference speaker scraper."""
    print("\n" + "="*80)
    print("CONFERENCE SPEAKER SCRAPER")
    print("Target: Major Tech/AI Conferences")
    print("="*80)
    
    scraper = ConferenceSpeakerScraper()
    
    # Step 1: Scrape all conferences
    print("\n[Step 1/3] Scraping conference websites...")
    speakers = scraper.scrape_all_conferences()
    
    # Remove duplicates
    seen = set()
    unique_speakers = []
    for speaker in speakers:
        key = (speaker.get('name'), speaker.get('email'))
        if key not in seen and speaker.get('name'):
            seen.add(key)
            unique_speakers.append(speaker)
    
    # Step 2: Add AI relevance scoring
    print(f"\n[Step 2/3] Scoring {len(unique_speakers)} speakers for AI/tech relevance...")
    unique_speakers = scraper.enrich_with_ai_relevance(unique_speakers)
    
    # Step 3: Save results
    print(f"\n[Step 3/3] Saving results...")
    csv_file = scraper.save_to_csv(unique_speakers)
    
    # Statistics
    with_email = sum(1 for s in unique_speakers if s.get('email'))
    with_twitter = sum(1 for s in unique_speakers if s.get('twitter'))
    with_linkedin = sum(1 for s in unique_speakers if s.get('linkedin'))
    with_website = sum(1 for s in unique_speakers if s.get('website'))
    high_ai_relevance = sum(1 for s in unique_speakers if s.get('ai_relevance_score', 0) >= 50)
    
    print(f"\n" + "="*80)
    print("SCRAPING COMPLETE!")
    print("="*80)
    print(f"\nResults:")
    print(f"  • Total speakers found: {len(unique_speakers)}")
    print(f"  • With email addresses: {with_email} ({with_email/max(len(unique_speakers),1)*100:.1f}%)")
    print(f"  • With Twitter: {with_twitter}")
    print(f"  • With LinkedIn: {with_linkedin}")
    print(f"  • With website: {with_website}")
    print(f"  • High AI/tech relevance: {high_ai_relevance}")
    print(f"  • CSV saved to: {csv_file}")
    
    if unique_speakers:
        print(f"\nTop 10 AI-relevant speakers:")
        for i, speaker in enumerate(unique_speakers[:10], 1):
            print(f"\n{i}. {speaker['name']} ({speaker.get('conference', 'Unknown')})")
            if speaker.get('title'):
                print(f"   Title: {speaker['title']}")
            if speaker.get('company'):
                print(f"   Company: {speaker['company']}")
            if speaker.get('email'):
                print(f"   Email: {speaker['email']}")
            print(f"   AI Score: {speaker.get('ai_relevance_score', 0)}")

if __name__ == "__main__":
    main()