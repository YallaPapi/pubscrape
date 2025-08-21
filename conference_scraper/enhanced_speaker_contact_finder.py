#!/usr/bin/env python3
"""
Enhanced Conference Speaker Contact Finder
This script takes the conference speaker data and enriches it by:
1. Visiting speaker profile pages (e.g., TED profiles)
2. Extracting personal websites and social media links
3. Scraping those personal websites for contact information
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
import json
from pathlib import Path
from datetime import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedSpeakerContactFinder:
    """Enriches conference speaker data with contact information from their websites."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.enriched_speakers = []
        
    def load_speaker_data(self, csv_path):
        """Load existing speaker data from CSV."""
        speakers = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    speakers.append(row)
            logger.info(f"Loaded {len(speakers)} speakers from {csv_path}")
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
        return speakers
    
    def extract_ted_profile_links(self, ted_url):
        """Extract actual website and social links from TED speaker profile."""
        links = {
            'personal_website': None,
            'twitter': None,
            'linkedin': None,
            'facebook': None,
            'instagram': None
        }
        
        try:
            response = self.session.get(ted_url, timeout=10)
            if response.status_code != 200:
                return links
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for social media links in TED profiles
            # TED often has a section with speaker's external links
            social_section = soup.find('div', class_='profile__social') or \
                           soup.find('div', class_='speaker-social') or \
                           soup.find('ul', class_='social-links')
            
            if social_section:
                all_links = social_section.find_all('a', href=True)
            else:
                # Fallback: look for all external links
                all_links = soup.find_all('a', href=re.compile(r'^https?://(?!.*ted\.com)'))
            
            for link in all_links:
                href = link.get('href', '')
                
                # Categorize links
                if 'twitter.com' in href or 'x.com' in href:
                    links['twitter'] = href
                elif 'linkedin.com' in href:
                    links['linkedin'] = href
                elif 'facebook.com' in href:
                    links['facebook'] = href
                elif 'instagram.com' in href:
                    links['instagram'] = href
                elif not any(social in href for social in ['twitter', 'linkedin', 'facebook', 'instagram', 'youtube', 'ted.com']):
                    # Likely a personal website
                    if not links['personal_website']:
                        links['personal_website'] = href
            
            # Also look for bio text that might contain a website
            bio = soup.find('div', class_='profile__bio') or soup.find('div', class_='speaker-description')
            if bio and not links['personal_website']:
                # Look for patterns like "Visit www.example.com"
                text = bio.get_text()
                url_pattern = re.search(r'(?:www\.|https?://)[^\s]+', text)
                if url_pattern:
                    links['personal_website'] = url_pattern.group()
                    if not links['personal_website'].startswith('http'):
                        links['personal_website'] = 'https://' + links['personal_website']
            
        except Exception as e:
            logger.debug(f"Error extracting from TED profile {ted_url}: {e}")
        
        return links
    
    def extract_contact_from_website(self, website_url):
        """Extract contact information from a personal website."""
        contact_info = {
            'email': None,
            'contact_form': False,
            'phone': None
        }
        
        if not website_url:
            return contact_info
            
        try:
            response = self.session.get(website_url, timeout=10)
            if response.status_code != 200:
                return contact_info
                
            soup = BeautifulSoup(response.text, 'html.parser')
            text = response.text
            
            # 1. Look for email addresses
            email_patterns = [
                r'[\w\.-]+@[\w\.-]+\.\w+',  # Standard email
                r'[\w\.-]+\s*\[\s*at\s*\]\s*[\w\.-]+\s*\[\s*dot\s*\]\s*\w+',  # Obfuscated
                r'[\w\.-]+\s*@\s*[\w\.-]+\s*\.\s*\w+'  # Spaced email
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Clean up obfuscated emails
                    email = match.replace('[at]', '@').replace('[dot]', '.').replace(' ', '')
                    # Filter out common false positives
                    if not any(fake in email for fake in ['example.', 'domain.', 'email.', 'test.', 'sample.']):
                        if '@' in email and '.' in email.split('@')[1]:
                            contact_info['email'] = email
                            break
                if contact_info['email']:
                    break
            
            # 2. Look for contact page link and follow it
            if not contact_info['email']:
                contact_links = soup.find_all('a', href=re.compile(r'contact|about|connect', re.I))
                for link in contact_links[:3]:  # Check first 3 contact-related links
                    contact_url = urljoin(website_url, link.get('href'))
                    try:
                        contact_response = self.session.get(contact_url, timeout=5)
                        contact_text = contact_response.text
                        
                        # Look for email in contact page
                        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_text)
                        if email_match:
                            email = email_match.group()
                            if not any(fake in email for fake in ['example.', 'domain.']):
                                contact_info['email'] = email
                                break
                    except:
                        continue
            
            # 3. Check for contact forms
            if soup.find('form', {'class': re.compile(r'contact', re.I)}) or \
               soup.find('form', {'id': re.compile(r'contact', re.I)}) or \
               soup.find('input', {'type': 'email'}):
                contact_info['contact_form'] = True
            
            # 4. Look for phone numbers (US format)
            phone_pattern = re.search(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            if phone_pattern:
                contact_info['phone'] = phone_pattern.group()
            
        except Exception as e:
            logger.debug(f"Error extracting from website {website_url}: {e}")
        
        return contact_info
    
    def extract_contact_from_linkedin(self, linkedin_url):
        """Extract contact hints from LinkedIn (limited without login)."""
        # LinkedIn heavily restricts non-logged-in access
        # We can only get basic info
        contact_info = {
            'linkedin_url': linkedin_url,
            'requires_linkedin_message': True
        }
        return contact_info
    
    def extract_contact_from_twitter(self, twitter_url):
        """Extract information from Twitter/X profile."""
        contact_info = {
            'twitter_handle': None,
            'twitter_bio_url': None
        }
        
        try:
            # Extract handle from URL
            handle_match = re.search(r'(?:twitter\.com|x\.com)/(@?\w+)', twitter_url)
            if handle_match:
                contact_info['twitter_handle'] = handle_match.group(1)
                if not contact_info['twitter_handle'].startswith('@'):
                    contact_info['twitter_handle'] = '@' + contact_info['twitter_handle']
        except:
            pass
        
        return contact_info
    
    def enrich_speaker(self, speaker):
        """Enrich a single speaker with contact information."""
        enriched = speaker.copy()
        
        # If the website is a TED profile, extract real links first
        if 'ted.com/speakers' in str(speaker.get('website', '')):
            logger.info(f"Extracting links for {speaker.get('name')}")
            profile_links = self.extract_ted_profile_links(speaker['website'])
            
            # Update speaker with real links
            enriched['personal_website'] = profile_links['personal_website']
            enriched['twitter_url'] = profile_links['twitter'] or speaker.get('twitter')
            enriched['linkedin_url'] = profile_links['linkedin'] or speaker.get('linkedin')
        else:
            enriched['personal_website'] = speaker.get('website')
            enriched['twitter_url'] = speaker.get('twitter')
            enriched['linkedin_url'] = speaker.get('linkedin')
        
        # Extract contact from personal website
        if enriched.get('personal_website'):
            logger.info(f"Checking website for {speaker.get('name')}: {enriched['personal_website']}")
            website_contact = self.extract_contact_from_website(enriched['personal_website'])
            enriched['email_from_website'] = website_contact['email']
            enriched['has_contact_form'] = website_contact['contact_form']
            enriched['phone'] = website_contact['phone']
        
        # Extract Twitter info
        if enriched.get('twitter_url'):
            twitter_info = self.extract_contact_from_twitter(enriched['twitter_url'])
            enriched['twitter_handle'] = twitter_info['twitter_handle']
        
        # Set final email (prefer website email over conference email)
        if enriched.get('email_from_website'):
            enriched['best_email'] = enriched['email_from_website']
        elif speaker.get('email') and '@' in str(speaker.get('email', '')):
            enriched['best_email'] = speaker['email']
        else:
            enriched['best_email'] = None
        
        # Calculate contact score
        score = 0
        if enriched.get('best_email'):
            score += 50
        if enriched.get('has_contact_form'):
            score += 20
        if enriched.get('twitter_handle'):
            score += 15
        if enriched.get('linkedin_url'):
            score += 15
        enriched['contact_score'] = score
        
        return enriched
    
    def enrich_all_speakers(self, speakers, max_workers=3):
        """Enrich all speakers with contact information."""
        enriched_speakers = []
        
        # Filter to only speakers with websites
        speakers_with_sites = [s for s in speakers if s.get('website')]
        
        print(f"\nEnriching {len(speakers_with_sites)} speakers with websites...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.enrich_speaker, speaker): speaker 
                      for speaker in speakers_with_sites[:50]}  # Limit to 50 for testing
            
            for future in as_completed(futures):
                try:
                    enriched = future.result()
                    enriched_speakers.append(enriched)
                    
                    # Progress update
                    if enriched.get('best_email'):
                        print(f"  ✓ Found email for {enriched['name']}: {enriched['best_email']}")
                    elif enriched.get('has_contact_form'):
                        print(f"  ◐ Found contact form for {enriched['name']}")
                    
                except Exception as e:
                    logger.error(f"Error enriching speaker: {e}")
                
                # Be polite to servers
                time.sleep(0.5)
        
        # Add speakers without websites
        for speaker in speakers:
            if not speaker.get('website'):
                enriched_speakers.append(speaker)
        
        return enriched_speakers
    
    def save_enriched_data(self, speakers, filename=None):
        """Save enriched speaker data to CSV."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"enriched_speakers_{timestamp}.csv"
        
        output_dir = Path("conference_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / filename
        
        fieldnames = ['name', 'best_email', 'conference', 'title', 'company',
                     'personal_website', 'email_from_website', 'has_contact_form',
                     'twitter_handle', 'linkedin_url', 'phone', 'contact_score',
                     'bio', 'ai_relevance_score']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            # Sort by contact score
            speakers.sort(key=lambda x: x.get('contact_score', 0), reverse=True)
            
            for speaker in speakers:
                writer.writerow(speaker)
        
        logger.info(f"Saved {len(speakers)} enriched speakers to {csv_path}")
        return str(csv_path)

def main():
    """Run the enhanced contact finder."""
    print("\n" + "="*80)
    print("ENHANCED CONFERENCE SPEAKER CONTACT FINDER")
    print("="*80)
    
    finder = EnhancedSpeakerContactFinder()
    
    # Load existing speaker data
    csv_path = "conference_scraper/output/conference_speakers_20250820_124322.csv"
    speakers = finder.load_speaker_data(csv_path)
    
    if not speakers:
        print("No speaker data found!")
        return
    
    # Enrich speakers with contact info
    print(f"\nProcessing {len(speakers)} speakers...")
    enriched = finder.enrich_all_speakers(speakers)
    
    # Save results
    output_file = finder.save_enriched_data(enriched)
    
    # Statistics
    with_email = sum(1 for s in enriched if s.get('best_email'))
    with_form = sum(1 for s in enriched if s.get('has_contact_form'))
    with_twitter = sum(1 for s in enriched if s.get('twitter_handle'))
    with_linkedin = sum(1 for s in enriched if s.get('linkedin_url'))
    with_website = sum(1 for s in enriched if s.get('personal_website'))
    
    print(f"\n" + "="*80)
    print("ENRICHMENT COMPLETE!")
    print("="*80)
    print(f"\nResults:")
    print(f"  • Total speakers: {len(enriched)}")
    print(f"  • With email: {with_email} ({with_email/max(len(enriched),1)*100:.1f}%)")
    print(f"  • With contact form: {with_form}")
    print(f"  • With Twitter: {with_twitter}")
    print(f"  • With LinkedIn: {with_linkedin}")
    print(f"  • With personal website: {with_website}")
    print(f"  • CSV saved to: {output_file}")
    
    # Show top contacts
    if enriched:
        print(f"\nTop speakers by contact score:")
        for speaker in enriched[:10]:
            if speaker.get('contact_score', 0) > 0:
                print(f"\n{speaker['name']} (Score: {speaker.get('contact_score', 0)})")
                if speaker.get('best_email'):
                    print(f"  Email: {speaker['best_email']}")
                if speaker.get('personal_website'):
                    print(f"  Website: {speaker['personal_website']}")
                if speaker.get('twitter_handle'):
                    print(f"  Twitter: {speaker['twitter_handle']}")

if __name__ == "__main__":
    main()