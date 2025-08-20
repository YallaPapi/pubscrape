"""
Hunter.io Email Finder Integration
Free tier: 25 searches per month
Finds business emails from names and domains
"""

import os
import logging
import requests
from typing import Optional, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HunterEmailFinder:
    """Find emails using Hunter.io API (free tier available)."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Hunter.io client.
        
        Get your free API key at: https://hunter.io/users/sign_up
        """
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")
        self.base_url = "https://api.hunter.io/v2"
        self.remaining_calls = 25  # Free tier limit
        
        if not self.api_key:
            logger.warning("Hunter.io API key not found. Get free key at: https://hunter.io/users/sign_up")
    
    def find_email(self, full_name: str, domain: Optional[str] = None, 
                   company: Optional[str] = None) -> Dict:
        """
        Find email for a person.
        
        Args:
            full_name: Person's full name
            domain: Company domain (e.g., "example.com")
            company: Company name if domain unknown
            
        Returns:
            Dict with email and confidence score
        """
        if not self.api_key:
            return {"email": None, "confidence": 0, "source": "No API key"}
        
        # Try email finder endpoint
        params = {
            "api_key": self.api_key,
            "full_name": full_name
        }
        
        if domain:
            params["domain"] = domain
        elif company:
            params["company"] = company
        
        try:
            response = requests.get(
                f"{self.base_url}/email-finder",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("email"):
                    return {
                        "email": data["data"]["email"],
                        "confidence": data["data"].get("score", 0),
                        "source": "Hunter.io",
                        "first_name": data["data"].get("first_name"),
                        "last_name": data["data"].get("last_name"),
                        "position": data["data"].get("position"),
                        "sources": data["data"].get("sources", [])
                    }
            
            elif response.status_code == 429:
                logger.warning("Hunter.io rate limit reached")
                return {"email": None, "confidence": 0, "source": "Rate limit"}
            
        except Exception as e:
            logger.error(f"Hunter.io error: {e}")
        
        return {"email": None, "confidence": 0, "source": "Not found"}
    
    def search_domain(self, domain: str, limit: int = 10) -> List[Dict]:
        """
        Search for all emails at a domain.
        
        Args:
            domain: Domain to search
            limit: Max results
            
        Returns:
            List of email records
        """
        if not self.api_key:
            return []
        
        params = {
            "api_key": self.api_key,
            "domain": domain,
            "limit": limit
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/domain-search",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                emails = []
                
                for email_data in data.get("data", {}).get("emails", []):
                    emails.append({
                        "email": email_data.get("value"),
                        "type": email_data.get("type"),
                        "confidence": email_data.get("confidence", 0),
                        "first_name": email_data.get("first_name"),
                        "last_name": email_data.get("last_name"),
                        "position": email_data.get("position"),
                        "department": email_data.get("department")
                    })
                
                return emails
                
        except Exception as e:
            logger.error(f"Hunter.io domain search error: {e}")
        
        return []
    
    def verify_email(self, email: str) -> Dict:
        """
        Verify if an email exists.
        
        Args:
            email: Email to verify
            
        Returns:
            Verification result
        """
        if not self.api_key:
            return {"valid": False, "status": "No API key"}
        
        params = {
            "api_key": self.api_key,
            "email": email
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/email-verifier",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": data["data"]["status"] == "valid",
                    "status": data["data"]["status"],
                    "score": data["data"].get("score", 0),
                    "regexp": data["data"].get("regexp"),
                    "gibberish": data["data"].get("gibberish"),
                    "disposable": data["data"].get("disposable"),
                    "webmail": data["data"].get("webmail"),
                    "mx_records": data["data"].get("mx_records"),
                    "smtp_server": data["data"].get("smtp_server"),
                    "smtp_check": data["data"].get("smtp_check"),
                    "accept_all": data["data"].get("accept_all"),
                    "sources": data["data"].get("sources", [])
                }
                
        except Exception as e:
            logger.error(f"Hunter.io verify error: {e}")
        
        return {"valid": False, "status": "Error"}
    
    def get_account_info(self) -> Dict:
        """Get account information and remaining searches."""
        if not self.api_key:
            return {"calls": {"available": 0, "used": 0}}
        
        params = {"api_key": self.api_key}
        
        try:
            response = requests.get(
                f"{self.base_url}/account",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()["data"]
                
        except Exception as e:
            logger.error(f"Hunter.io account error: {e}")
        
        return {"calls": {"available": 0, "used": 0}}


# Alternative: Apollo.io (more generous free tier)
class ApolloEmailFinder:
    """
    Apollo.io email finder (better free tier).
    Free: 120 email credits per month
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Apollo.io client.
        
        Get your free API key at: https://app.apollo.io/#/settings/integrations/api
        """
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        self.base_url = "https://api.apollo.io/v1"
        
        if not self.api_key:
            logger.warning("Apollo.io API key not found. Get free key at: https://app.apollo.io")
    
    def search_people(self, name: str, organization: Optional[str] = None) -> List[Dict]:
        """
        Search for people and their emails.
        
        Args:
            name: Person's name
            organization: Company/organization name
            
        Returns:
            List of people with emails
        """
        if not self.api_key:
            return []
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }
        
        data = {
            "api_key": self.api_key,
            "q_person_name": name,
            "page": 1,
            "per_page": 10
        }
        
        if organization:
            data["q_organization_name"] = organization
        
        try:
            response = requests.post(
                f"{self.base_url}/mixed_people/search",
                json=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                people = []
                
                for person in result.get("people", []):
                    if person.get("email"):
                        people.append({
                            "name": person.get("name"),
                            "email": person.get("email"),
                            "title": person.get("title"),
                            "company": person.get("organization", {}).get("name"),
                            "linkedin": person.get("linkedin_url"),
                            "verified": person.get("email_status") == "verified"
                        })
                
                return people
                
        except Exception as e:
            logger.error(f"Apollo.io search error: {e}")
        
        return []


# Fallback: Free email pattern guessing
class EmailGuesser:
    """
    Guess email patterns when APIs aren't available.
    Common patterns: firstname.lastname@, first@, contact@, etc.
    """
    
    def __init__(self):
        """Initialize email pattern guesser."""
        self.common_patterns = [
            "{first}.{last}@{domain}",
            "{first}{last}@{domain}",
            "{first}@{domain}",
            "{last}@{domain}",
            "{first}_{last}@{domain}",
            "{f}{last}@{domain}",
            "{first}{l}@{domain}",
            "contact@{domain}",
            "hello@{domain}",
            "info@{domain}",
            "business@{domain}",
            "inquiries@{domain}",
            "collab@{domain}",
            "pr@{domain}",
            "press@{domain}",
            "booking@{domain}",
            "management@{domain}",
            "team@{domain}"
        ]
    
    def guess_email(self, name: str, domain: str) -> List[str]:
        """
        Generate possible email addresses.
        
        Args:
            name: Full name
            domain: Domain name
            
        Returns:
            List of possible emails
        """
        if not domain:
            return []
        
        # Parse name
        parts = name.lower().split()
        if len(parts) >= 2:
            first = parts[0]
            last = parts[-1]
            f = first[0] if first else ""
            l = last[0] if last else ""
        else:
            first = parts[0] if parts else ""
            last = ""
            f = first[0] if first else ""
            l = ""
        
        # Generate emails
        emails = []
        for pattern in self.common_patterns:
            try:
                email = pattern.format(
                    first=first,
                    last=last,
                    f=f,
                    l=l,
                    domain=domain
                )
                if "@" in email and "." in email:
                    emails.append(email)
            except:
                continue
        
        return list(set(emails))  # Remove duplicates


# Main integration for your pipeline
class SmartEmailFinder:
    """
    Combines multiple methods to find emails.
    Priority: Hunter.io -> Apollo.io -> Website scraping -> Guessing
    """
    
    def __init__(self):
        """Initialize all email finders."""
        self.hunter = HunterEmailFinder()
        self.apollo = ApolloEmailFinder()
        self.guesser = EmailGuesser()
    
    def find_best_email(self, channel_data: Dict) -> Dict:
        """
        Find the best email for a channel using all available methods.
        
        Args:
            channel_data: Channel information
            
        Returns:
            Best email found with metadata
        """
        channel_name = channel_data.get("channel_name", "")
        website = channel_data.get("website", "")
        
        # Extract domain from website
        domain = None
        if website:
            try:
                parsed = urlparse(website)
                domain = parsed.netloc.replace("www.", "")
            except:
                pass
        
        # Try Hunter.io first (if we have API key)
        if self.hunter.api_key and domain:
            result = self.hunter.find_email(channel_name, domain)
            if result.get("email"):
                return {
                    "email": result["email"],
                    "confidence": result["confidence"],
                    "source": "Hunter.io",
                    "verified": True
                }
        
        # Try Apollo.io
        if self.apollo.api_key:
            people = self.apollo.search_people(channel_name)
            if people and people[0].get("email"):
                return {
                    "email": people[0]["email"],
                    "confidence": 85,
                    "source": "Apollo.io",
                    "verified": people[0].get("verified", False)
                }
        
        # Fallback to guessing
        if domain:
            guesses = self.guesser.guess_email(channel_name, domain)
            if guesses:
                return {
                    "email": guesses[0],
                    "confidence": 30,
                    "source": "Pattern guess",
                    "alternatives": guesses[1:5],
                    "verified": False
                }
        
        # No email found
        return {
            "email": None,
            "confidence": 0,
            "source": "Not found",
            "youtube_about": f"https://youtube.com/channel/{channel_data.get('channel_id')}/about"
        }