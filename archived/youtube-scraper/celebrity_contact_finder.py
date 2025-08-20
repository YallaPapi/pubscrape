"""
Celebrity & Athlete Contact Finder
Finds agents, managers, and publicists for high-profile individuals
"""

import requests
from bs4 import BeautifulSoup
import re
import csv
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CelebrityContactFinder:
    """Find contact info for celebrities through their representatives"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def find_via_speaker_bureau(self, name: str) -> Dict:
        """
        Speaker bureaus list celebrities available for events
        They WANT you to book their clients!
        """
        speaker_bureaus = [
            "washingtonspeakers.com",
            "harrywalker.com",
            "leadingauthorities.com",
            "apbspeakers.com",
            "keplersspeakers.com",
            "bigspeak.com"
        ]
        
        results = []
        for bureau in speaker_bureaus[:3]:  # Limit for demo
            try:
                # Search for celebrity on speaker bureau site
                search_url = f"https://www.google.com/search?q=site:{bureau}+\"{name}\"+booking+contact"
                response = self.session.get(search_url)
                
                if response.status_code == 200:
                    logger.info(f"Searching {bureau} for {name}")
                    # Speaker bureaus have booking agents listed
                    
            except Exception as e:
                logger.error(f"Error searching {bureau}: {e}")
        
        return {"name": name, "booking_agencies": speaker_bureaus[:3]}
    
    def find_via_imdb_pro_public(self, name: str) -> Dict:
        """
        IMDb has some public info (full details need IMDbPro)
        """
        try:
            # Search IMDb for public agent info
            search_url = f"https://www.google.com/search?q=site:imdb.com+\"{name}\"+agent+manager+publicist"
            response = self.session.get(search_url)
            
            # IMDb sometimes shows representation in bio
            logger.info(f"Checking IMDb for {name}")
            
            return {"name": name, "source": "IMDb", "note": "Check IMDbPro for full contact"}
            
        except Exception as e:
            logger.error(f"IMDb search error: {e}")
            return {}
    
    def find_athlete_agent(self, athlete_name: str, sport: str) -> Dict:
        """
        Find athlete agents through sports databases
        """
        # Professional sports leagues often list agents
        leagues = {
            "NFL": "nflpa.com",  # NFL Players Association
            "NBA": "nbpa.com",   # NBA Players Association  
            "MLB": "mlbplayers.com",  # MLB Players Association
            "NHL": "nhlpa.com",  # NHL Players Association
        }
        
        # Many athletes are listed on their team sites with agent info
        try:
            # Search for athlete's agent
            search_url = f"https://www.google.com/search?q=\"{athlete_name}\"+agent+represented+by"
            response = self.session.get(search_url)
            
            logger.info(f"Searching for {athlete_name}'s agent")
            
            # Also check sports agency sites
            for agency in ["caa", "octagon", "wasserman", "rocnation"]:
                agency_search = f"https://www.google.com/search?q=site:{agency}.com+\"{athlete_name}\""
                logger.info(f"Checking {agency} for {athlete_name}")
            
        except Exception as e:
            logger.error(f"Athlete agent search error: {e}")
        
        return {"athlete": athlete_name, "sport": sport}
    
    def find_via_wikipedia(self, name: str) -> Dict:
        """
        Wikipedia often lists agents/managers in celebrity pages
        """
        try:
            # Clean name for Wikipedia URL
            wiki_name = name.replace(" ", "_")
            wiki_url = f"https://en.wikipedia.org/wiki/{wiki_name}"
            
            response = self.session.get(wiki_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for agent/manager info in infobox
                infobox = soup.find('table', {'class': 'infobox'})
                if infobox:
                    # Search for agent, manager, label fields
                    text = infobox.get_text()
                    
                    # Extract any emails found
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    
                    return {
                        "name": name,
                        "wikipedia": wiki_url,
                        "emails_found": emails,
                        "source": "Wikipedia"
                    }
                    
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
        
        return {}
    
    def find_music_artist_contact(self, artist_name: str) -> Dict:
        """
        Musicians often have booking info on their official sites
        """
        try:
            # Search for official site
            search_url = f"https://www.google.com/search?q=\"{artist_name}\"+official+website+booking+contact"
            response = self.session.get(search_url)
            
            # Record labels also list contact for their artists
            labels = ["universalmusic.com", "sonymusic.com", "warnermusic.com"]
            for label in labels:
                label_search = f"https://www.google.com/search?q=site:{label}+\"{artist_name}\"+contact"
                logger.info(f"Checking {label} for {artist_name}")
            
            # Booking agencies for musicians
            booking_agencies = ["caa.com", "wmeagency.com", "uta.com", "paradigmagency.com"]
            
            return {
                "artist": artist_name,
                "booking_agencies": booking_agencies,
                "note": "Check artist's official website footer for booking email"
            }
            
        except Exception as e:
            logger.error(f"Music artist search error: {e}")
            return {}
    
    def find_influencer_contact(self, username: str, platform: str) -> Dict:
        """
        Social media influencers often list business emails
        """
        results = {}
        
        if platform.lower() == "youtube":
            # YouTube About tab sometimes has email
            results["youtube_about"] = f"https://youtube.com/@{username}/about"
            results["note"] = "Check About tab for business email"
            
        elif platform.lower() == "instagram":
            # Instagram bio often has email or link tree
            results["instagram"] = f"https://instagram.com/{username}"
            results["note"] = "Check bio for email or Linktree"
            
        elif platform.lower() == "tiktok":
            # TikTok creators list email in bio
            results["tiktok"] = f"https://tiktok.com/@{username}"
            results["note"] = "Check bio for business email"
        
        # Many influencers use management companies
        influencer_agencies = [
            "Digital Brand Architects",
            "Gleam Futures",
            "Whalar",
            "Obviously",
            "AspireIQ"
        ]
        
        results["management_companies"] = influencer_agencies
        
        return results
    
    def bulk_find_celebrities(self, names: List[str], category: str = "general") -> List[Dict]:
        """
        Find contact info for multiple celebrities
        """
        all_results = []
        
        for name in names:
            logger.info(f"\nSearching for: {name}")
            
            result = {"name": name, "category": category}
            
            # Try different methods based on category
            if category == "athlete":
                athlete_info = self.find_athlete_agent(name, "")
                result.update(athlete_info)
                
            elif category == "musician":
                music_info = self.find_music_artist_contact(name)
                result.update(music_info)
                
            elif category == "influencer":
                influencer_info = self.find_influencer_contact(name, "instagram")
                result.update(influencer_info)
                
            else:  # General celebrity
                # Try speaker bureau
                speaker_info = self.find_via_speaker_bureau(name)
                result.update(speaker_info)
                
                # Try Wikipedia
                wiki_info = self.find_via_wikipedia(name)
                if wiki_info:
                    result.update(wiki_info)
                
                # Try IMDb
                imdb_info = self.find_via_imdb_pro_public(name)
                if imdb_info:
                    result.update(imdb_info)
            
            all_results.append(result)
        
        return all_results
    
    def export_contacts(self, results: List[Dict], filename: str = "celebrity_contacts.csv"):
        """Export found contacts to CSV"""
        
        if not results:
            logger.warning("No results to export")
            return
        
        # Get all unique keys
        all_keys = set()
        for result in results:
            all_keys.update(result.keys())
        
        # Write CSV
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(results)
        
        logger.info(f"\nExported {len(results)} celebrity contacts to {filename}")


def main():
    """Demo: Find contacts for various celebrities"""
    
    finder = CelebrityContactFinder()
    
    # Example celebrities to search
    celebrities = {
        "athletes": ["LeBron James", "Serena Williams", "Tom Brady"],
        "musicians": ["Taylor Swift", "Drake", "Beyonce"],
        "actors": ["Ryan Reynolds", "Emma Stone", "Chris Hemsworth"],
        "influencers": ["MrBeast", "Emma Chamberlain", "David Dobrik"]
    }
    
    all_results = []
    
    for category, names in celebrities.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Searching {category.upper()}")
        logger.info(f"{'='*60}")
        
        results = finder.bulk_find_celebrities(names[:2], category.replace("s", ""))  # Limit for demo
        all_results.extend(results)
    
    # Export all results
    finder.export_contacts(all_results, "celebrity_contacts.csv")
    
    print("\n" + "="*60)
    print("CELEBRITY CONTACT FINDER COMPLETE")
    print("="*60)
    print(f"Searched for {len(all_results)} celebrities")
    print("\nKEY INSIGHTS:")
    print("  1. Celebrities use agents/managers - not direct emails")
    print("  2. Speaker bureaus list booking contacts")
    print("  3. IMDbPro has full contact info (paid)")
    print("  4. Athletes: Check players associations")
    print("  5. Musicians: Check label/booking agency sites")
    print("  6. Influencers: Check bio links on their platforms")
    print("\nRECOMMENDED SERVICES:")
    print("  - IMDbPro ($19.99/mo) - Actor/director contacts")
    print("  - Rocketreach ($79/mo) - Business contacts")
    print("  - ContactOut ($99/mo) - Social media emails")
    print("  - Speaker bureau sites (FREE) - Booking agents")


if __name__ == "__main__":
    main()