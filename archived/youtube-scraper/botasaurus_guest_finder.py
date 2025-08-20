"""
Botasaurus Guest Finder - Scrapes high-profile guest contacts from protected sources
Uses anti-detection to bypass Cloudflare and other bot protection
"""

from botasaurus import *
from botasaurus.browser import browser, Driver
from botasaurus.request import request, Request
import csv
import json
from typing import List, Dict
import time

# Sources that block regular scrapers but Botasaurus can handle
PROTECTED_SOURCES = {
    "podcast_guests": "https://www.podcastguests.com/",
    "ted_speakers": "https://www.ted.com/speakers",
    "linkedin_experts": "https://www.linkedin.com/search/results/people/",
    "instagram_influencers": "https://www.instagram.com/",
    "speaker_bureaus": "https://www.thespeakersbureau.com/",
}


@browser(
    headless=True,
    block_images=True,  # Faster loading
)
def scrape_podcast_guests(driver: Driver, search_query: str):
    """
    Scrape PodcastGuests.com - a directory of people looking to be on podcasts
    They WANT to be contacted!
    """
    results = []
    
    # Go to podcast guests site
    driver.get("https://www.podcastguests.com/")
    
    # Search for experts in our niche
    search_box = driver.find_element("input[type='search']", wait=10)
    if search_box:
        driver.type(search_box, search_query)
        driver.press_enter()
        driver.sleep(3)  # Wait for results
        
        # Extract guest profiles
        guest_cards = driver.find_elements(".guest-card", wait=5)
        
        for card in guest_cards[:20]:  # Get top 20
            try:
                name = driver.get_text_or_default(card.find_element(".guest-name"), "")
                expertise = driver.get_text_or_default(card.find_element(".expertise"), "")
                bio = driver.get_text_or_default(card.find_element(".bio"), "")
                
                # Click to get contact info (many have public emails)
                card.click()
                driver.sleep(2)
                
                email = driver.get_text_or_default("a[href^='mailto:']", "")
                website = driver.get_text_or_default("a.website-link", "")
                
                results.append({
                    "name": name,
                    "expertise": expertise,
                    "bio": bio[:200],
                    "email": email.replace("mailto:", ""),
                    "website": website,
                    "source": "PodcastGuests.com",
                    "actively_seeking": True
                })
                
                driver.go_back()
                
            except Exception as e:
                print(f"Error extracting guest: {e}")
                continue
    
    return results


@browser(
    headless=True,
    block_images=True
)
def scrape_linkedin_experts(driver: Driver, search_query: str):
    """
    Scrape LinkedIn for experts (without login - public profiles only)
    """
    results = []
    
    # Search Google for LinkedIn profiles (avoids LinkedIn login)
    google_query = f"site:linkedin.com/in/ {search_query} contact email"
    driver.google_get(google_query)
    
    # Get search results
    search_results = driver.find_elements("h3", wait=5)
    
    for result in search_results[:15]:
        try:
            result.click()
            driver.sleep(2)
            
            # Extract from public LinkedIn profile
            name = driver.get_text_or_default("h1", "")
            headline = driver.get_text_or_default(".headline", "")
            
            # Look for contact info in About section
            about = driver.get_text_or_default("#about", "")
            
            # Extract email if visible
            import re
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', about)
            email = email_match.group(0) if email_match else ""
            
            results.append({
                "name": name,
                "title": headline,
                "bio": about[:200],
                "email": email,
                "linkedin": driver.current_url,
                "source": "LinkedIn",
                "verified_expert": True
            })
            
            driver.go_back()
            
        except Exception as e:
            print(f"Error with LinkedIn profile: {e}")
            continue
    
    return results


@browser(
    headless=True,
    block_images=True
)
def scrape_ted_speakers(driver: Driver, topic: str):
    """
    Scrape TED speakers - they're public figures who want visibility
    """
    results = []
    
    # Search TED for speakers on topic
    driver.get(f"https://www.ted.com/search?q={topic}&content_type=speakers")
    driver.sleep(3)
    
    # Get speaker cards
    speakers = driver.find_elements(".search-result", wait=10)
    
    for speaker in speakers[:20]:
        try:
            name = driver.get_text_or_default(speaker.find_element(".name"), "")
            title = driver.get_text_or_default(speaker.find_element(".title"), "")
            
            # Click for more info
            speaker.click()
            driver.sleep(2)
            
            bio = driver.get_text_or_default(".speaker-bio", "")
            
            # TED speakers often have websites with contact
            website = driver.get_text_or_default("a.website", "")
            
            results.append({
                "name": name,
                "title": title,
                "bio": bio[:200],
                "website": website,
                "ted_profile": driver.current_url,
                "source": "TED",
                "speaker_caliber": "High - TED Speaker"
            })
            
            driver.go_back()
            
        except Exception as e:
            print(f"Error with TED speaker: {e}")
            continue
    
    return results


@browser(
    headless=True,
    block_images=True
)
def scrape_instagram_creators(driver: Driver, hashtag: str):
    """
    Scrape Instagram creators from hashtag pages (no login required)
    """
    results = []
    
    # Go to hashtag page
    driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
    driver.sleep(3)
    
    # Get top posts
    posts = driver.find_elements("article a", wait=10)
    
    for post in posts[:15]:
        try:
            post.click()
            driver.sleep(2)
            
            # Get creator username
            username = driver.get_text_or_default("a.username", "")
            
            # Go to their profile
            profile_link = driver.find_element(f"a[href='/{username}/']")
            if profile_link:
                profile_link.click()
                driver.sleep(2)
                
                # Extract bio
                bio = driver.get_text_or_default(".bio", "")
                
                # Look for email in bio
                import re
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', bio)
                email = email_match.group(0) if email_match else ""
                
                # Get follower count
                followers = driver.get_text_or_default(".follower-count", "0")
                
                # Look for Linktree or contact link
                contact_link = driver.get_text_or_default("a[href*='linktr.ee'], a[href*='beacons.ai']", "")
                
                results.append({
                    "name": username,
                    "bio": bio[:200],
                    "email": email,
                    "contact_link": contact_link,
                    "followers": followers,
                    "instagram": f"https://instagram.com/{username}",
                    "source": "Instagram"
                })
            
            driver.go_back()
            driver.go_back()
            
        except Exception as e:
            print(f"Error with Instagram creator: {e}")
            continue
    
    return results


@request(
    parallel=5,  # Scrape 5 pages at once
    cache=True  # Cache results to avoid re-scraping
)
def scrape_university_experts(request: Request, university: str, field: str):
    """
    Scrape university faculty pages - professors want media attention
    """
    # Search for faculty pages
    search_url = f"https://www.google.com/search?q=site:{university}+faculty+{field}+email"
    response = request.get(search_url)
    
    # Parse results
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    results = []
    links = soup.find_all('a', href=True)
    
    for link in links[:10]:
        if university in link['href']:
            # Visit faculty page
            faculty_response = request.get(link['href'])
            faculty_soup = BeautifulSoup(faculty_response.text, 'html.parser')
            
            # Extract emails
            import re
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', faculty_response.text)
            
            # Get text content
            text = faculty_soup.get_text()
            
            # Try to extract name (usually in h1, h2, or title)
            name = ""
            for tag in ['h1', 'h2', 'title']:
                name_elem = faculty_soup.find(tag)
                if name_elem:
                    name = name_elem.get_text().strip()
                    break
            
            if emails:
                results.append({
                    "name": name,
                    "email": emails[0],
                    "university": university,
                    "field": field,
                    "source": "University Faculty Page",
                    "credibility": "High - Academic"
                })
    
    return results


class BotasaurusGuestFinder:
    """Main class to coordinate all scrapers"""
    
    def __init__(self):
        self.all_guests = []
    
    def find_podcast_ready_guests(self, topic: str, limit: int = 100):
        """
        Find guests who WANT to be on podcasts
        """
        print(f"\n🎯 Finding {topic} experts who want podcast appearances...\n")
        
        # 1. Scrape PodcastGuests.com - they literally want to be contacted
        print("📻 Searching PodcastGuests.com...")
        podcast_guests = scrape_podcast_guests(topic)
        self.all_guests.extend(podcast_guests)
        print(f"  Found {len(podcast_guests)} guests actively seeking podcasts")
        
        # 2. Scrape TED speakers
        print("\n🎤 Searching TED Speakers...")
        ted_speakers = scrape_ted_speakers(topic)
        self.all_guests.extend(ted_speakers)
        print(f"  Found {len(ted_speakers)} TED speakers")
        
        # 3. Scrape LinkedIn experts
        print("\n💼 Searching LinkedIn Experts...")
        linkedin_experts = scrape_linkedin_experts(f"{topic} expert speaker")
        self.all_guests.extend(linkedin_experts)
        print(f"  Found {len(linkedin_experts)} LinkedIn experts")
        
        # 4. Scrape Instagram creators
        print("\n📸 Searching Instagram Creators...")
        hashtag = topic.replace(" ", "")
        instagram_creators = scrape_instagram_creators(hashtag)
        self.all_guests.extend(instagram_creators)
        print(f"  Found {len(instagram_creators)} Instagram creators")
        
        # 5. Scrape university experts
        print("\n🎓 Searching University Experts...")
        universities = ["mit.edu", "stanford.edu", "harvard.edu"]
        for uni in universities[:2]:  # Demo: just 2 universities
            uni_experts = scrape_university_experts(uni, topic)
            self.all_guests.extend(uni_experts)
        print(f"  Found {len([g for g in self.all_guests if 'university' in g.get('source', '').lower()])} academics")
        
        return self.all_guests[:limit]
    
    def export_to_csv(self, filename: str = "high_profile_guests.csv"):
        """Export found guests to CSV"""
        if not self.all_guests:
            print("No guests found to export")
            return
        
        # Prepare CSV data
        csv_data = []
        for guest in self.all_guests:
            csv_data.append({
                "Name": guest.get("name", ""),
                "Email": guest.get("email", ""),
                "Title/Expertise": guest.get("title", guest.get("expertise", "")),
                "Bio": guest.get("bio", ""),
                "Source": guest.get("source", ""),
                "Website": guest.get("website", ""),
                "Social Media": guest.get("instagram", guest.get("linkedin", "")),
                "Actively Seeking Podcasts": guest.get("actively_seeking", False),
                "Credibility": guest.get("credibility", guest.get("speaker_caliber", ""))
            })
        
        # Write to CSV
        keys = csv_data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\n✅ Exported {len(csv_data)} high-profile guests to {filename}")
        print(f"📧 Guests with emails: {len([g for g in csv_data if g['Email']])}")
        print(f"🎯 Actively seeking podcasts: {len([g for g in csv_data if g['Actively Seeking Podcasts']])}")


if __name__ == "__main__":
    # Example usage
    finder = BotasaurusGuestFinder()
    
    # Find experts in specific fields
    topics = [
        "artificial intelligence",
        "entrepreneurship",
        "health wellness",
        "personal finance",
        "productivity"
    ]
    
    for topic in topics[:2]:  # Demo: just 2 topics
        print(f"\n{'='*60}")
        print(f"FINDING GUESTS FOR: {topic.upper()}")
        print(f"{'='*60}")
        
        guests = finder.find_podcast_ready_guests(topic, limit=50)
    
    # Export all results
    finder.export_to_csv("high_profile_podcast_guests.csv")
    
    print("\n🎉 Guest discovery complete!")
    print("📁 Check: high_profile_podcast_guests.csv")