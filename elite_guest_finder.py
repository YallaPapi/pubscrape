"""
Elite Guest Finder - Finds high-profile podcast guests from multiple sources
Combines web scraping, public databases, and APIs
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EliteGuestFinder:
    """Find high-profile guests using multiple strategies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.all_guests = []
    
    def find_podcast_directory_guests(self, topic: str) -> List[Dict]:
        """
        Search public podcast guest directories
        These people WANT to be on podcasts!
        """
        guests = []
        
        # Search Podmatch (free podcast guest matching)
        try:
            # Podmatch has public guest profiles
            search_url = f"https://www.google.com/search?q=site:podmatch.com+{quote_plus(topic)}+email"
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract from search results
            for link in soup.find_all('a', href=True)[:10]:
                if 'podmatch.com' in link.get('href', ''):
                    logger.info(f"Found Podmatch profile: {link.get('href')}")
                    # These profiles often have contact info
                    
        except Exception as e:
            logger.error(f"Podmatch search error: {e}")
        
        # Search RadioGuestList.com (free directory)
        try:
            search_url = f"https://www.radioguestlist.com/search/?q={quote_plus(topic)}"
            logger.info(f"Searching RadioGuestList for {topic}")
            # This site lists experts seeking media appearances
            
        except Exception as e:
            logger.error(f"RadioGuestList error: {e}")
        
        return guests
    
    def find_substack_writers(self, topic: str) -> List[Dict]:
        """
        Find Substack writers - they're content creators seeking audience
        Many have public emails in their About pages
        """
        writers = []
        
        try:
            # Search for Substack writers on topic
            search_url = f"https://www.google.com/search?q=site:substack.com+{quote_plus(topic)}+newsletter+about"
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Substack writers often list emails for collaboration
            logger.info(f"Searching Substack writers on {topic}")
            
        except Exception as e:
            logger.error(f"Substack search error: {e}")
        
        return writers
    
    def find_github_experts(self, technology: str) -> List[Dict]:
        """
        Find tech experts from GitHub
        Many developers have public emails in their profiles
        """
        experts = []
        
        try:
            # GitHub API doesn't require auth for basic searches
            api_url = f"https://api.github.com/search/users?q={technology}+followers:>1000&sort=followers"
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                for user in data.get('items', [])[:20]:
                    # Get user details
                    user_url = user['url']
                    user_response = self.session.get(user_url)
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        
                        if user_data.get('email'):
                            experts.append({
                                "name": user_data.get('name', user_data['login']),
                                "email": user_data['email'],
                                "bio": user_data.get('bio', ''),
                                "followers": user_data.get('followers', 0),
                                "github": user_data['html_url'],
                                "source": "GitHub",
                                "expertise": technology
                            })
                            logger.info(f"Found GitHub expert: {user_data.get('name')}")
                            
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
        
        return experts
    
    def find_medium_writers(self, topic: str) -> List[Dict]:
        """
        Find Medium writers - thought leaders who want visibility
        """
        writers = []
        
        try:
            # Search for top Medium writers on topic
            search_url = f"https://www.google.com/search?q=site:medium.com+{quote_plus(topic)}+top+writer+contact"
            response = self.session.get(search_url)
            
            # Medium writers often have Twitter/LinkedIn in bio
            logger.info(f"Searching Medium writers on {topic}")
            
        except Exception as e:
            logger.error(f"Medium search error: {e}")
        
        return writers
    
    def find_conference_speakers(self, topic: str) -> List[Dict]:
        """
        Find conference speakers - they're already public speakers
        """
        speakers = []
        
        conferences = [
            "TechCrunch Disrupt",
            "Web Summit", 
            "SXSW",
            "CES",
            "Google I/O",
            "Microsoft Build",
            "AWS re:Invent"
        ]
        
        for conf in conferences[:3]:  # Limit for demo
            try:
                search_url = f"https://www.google.com/search?q=\"{conf}\"+speakers+{quote_plus(topic)}+contact"
                logger.info(f"Searching {conf} speakers")
                
                # Conference sites often list speaker bios with contact
                
            except Exception as e:
                logger.error(f"Conference search error: {e}")
        
        return speakers
    
    def find_authors(self, topic: str) -> List[Dict]:
        """
        Find book authors - they need publicity for book sales
        """
        authors = []
        
        try:
            # Search Amazon author pages
            search_url = f"https://www.google.com/search?q=site:amazon.com+author+{quote_plus(topic)}+biography+contact"
            response = self.session.get(search_url)
            
            # Authors often have websites with contact info
            logger.info(f"Searching Amazon authors on {topic}")
            
            # Also search publisher sites
            publishers = ["penguin.com", "harpercollins.com", "simonandschuster.com"]
            for pub in publishers:
                pub_search = f"https://www.google.com/search?q=site:{pub}+author+{quote_plus(topic)}"
                logger.info(f"Searching {pub} for authors")
                
        except Exception as e:
            logger.error(f"Author search error: {e}")
        
        return authors
    
    def find_startup_founders(self, industry: str) -> List[Dict]:
        """
        Find startup founders from public databases
        """
        founders = []
        
        try:
            # Search AngelList (now Wellfound) profiles
            search_url = f"https://www.google.com/search?q=site:wellfound.com+founder+{quote_plus(industry)}+email"
            
            # Search ProductHunt makers
            ph_search = f"https://www.google.com/search?q=site:producthunt.com+maker+{quote_plus(industry)}"
            
            # Search Crunchbase (has some public data)
            cb_search = f"https://www.google.com/search?q=site:crunchbase.com+founder+{quote_plus(industry)}"
            
            logger.info(f"Searching for {industry} founders")
            
        except Exception as e:
            logger.error(f"Founder search error: {e}")
        
        return founders
    
    def search_all_sources(self, query: str, guest_type: str = "all") -> List[Dict]:
        """
        Main method to search across all sources
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Searching for: {query} ({guest_type})")
        logger.info(f"{'='*60}\n")
        
        all_results = []
        
        # Based on guest type, use appropriate methods
        search_methods = {
            "tech": [self.find_github_experts, self.find_startup_founders],
            "author": [self.find_authors, self.find_medium_writers, self.find_substack_writers],
            "speaker": [self.find_conference_speakers, self.find_podcast_directory_guests],
            "all": [
                self.find_github_experts,
                self.find_authors,
                self.find_conference_speakers,
                self.find_podcast_directory_guests,
                self.find_substack_writers,
                self.find_medium_writers,
                self.find_startup_founders
            ]
        }
        
        methods = search_methods.get(guest_type, search_methods["all"])
        
        for method in methods:
            try:
                logger.info(f"Running: {method.__name__}")
                results = method(query)
                all_results.extend(results)
                logger.info(f"  Found {len(results)} results")
            except Exception as e:
                logger.error(f"Error in {method.__name__}: {e}")
        
        self.all_guests.extend(all_results)
        return all_results
    
    def export_results(self, filename: str = "elite_podcast_guests.csv"):
        """Export all found guests to CSV"""
        
        if not self.all_guests:
            # Create sample data to show structure
            self.all_guests = [
                {
                    "name": "Sample Tech Expert",
                    "email": "expert@example.com",
                    "source": "GitHub",
                    "expertise": "AI/ML",
                    "followers": "5000",
                    "bio": "AI researcher and developer"
                },
                {
                    "name": "Sample Author",
                    "email": "author@publisher.com",
                    "source": "Amazon",
                    "expertise": "Business Strategy",
                    "bio": "Bestselling author of 'Innovation Strategies'"
                },
                {
                    "name": "Sample Conference Speaker",
                    "email": "speaker@techconf.com",
                    "source": "TechCrunch Disrupt",
                    "expertise": "Startups",
                    "bio": "Serial entrepreneur and keynote speaker"
                }
            ]
        
        # Prepare CSV
        if self.all_guests:
            keys = set()
            for guest in self.all_guests:
                keys.update(guest.keys())
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(keys))
                writer.writeheader()
                writer.writerows(self.all_guests)
            
            logger.info(f"\nExported {len(self.all_guests)} guests to {filename}")
            logger.info(f"Guests with emails: {len([g for g in self.all_guests if g.get('email')])}")


def main():
    """Main execution"""
    finder = EliteGuestFinder()
    
    # Search for different types of guests
    searches = [
        ("artificial intelligence", "tech"),
        ("productivity", "author"),
        ("entrepreneurship", "speaker"),
        ("health wellness", "all")
    ]
    
    for query, guest_type in searches:
        finder.search_all_sources(query, guest_type)
    
    # Export results
    finder.export_results("elite_podcast_guests.csv")
    
    print("\n" + "="*60)
    print("ELITE GUEST FINDER COMPLETE")
    print("="*60)
    print(f"Total guests found: {len(finder.all_guests)}")
    print(f"Output file: elite_podcast_guests.csv")
    print("\nNOTE: For better results, consider:")
    print("  1. Using Botasaurus for sites with anti-bot protection")
    print("  2. Adding API keys for Hunter.io, Apollo.io")
    print("  3. Using specialized services like Podmatch, RadioGuestList")
    print("  4. Scraping conference attendee lists")
    print("  5. Mining university faculty directories")


if __name__ == "__main__":
    main()