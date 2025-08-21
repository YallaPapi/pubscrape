#!/usr/bin/env python3
"""
Demo of using SerpAPI for Google Scholar to find professors.
SerpAPI handles anti-blocking and returns structured data.

Note: SerpAPI is a paid service but offers a free tier (100 searches/month).
Sign up at https://serpapi.com to get an API key.
"""

import requests
import json
from pathlib import Path
import csv
from datetime import datetime

def test_serpapi_scholar():
    """Test SerpAPI Google Scholar endpoint."""
    
    # You would need to sign up for a free API key at https://serpapi.com
    # Free tier: 100 searches per month
    API_KEY = "YOUR_SERPAPI_KEY_HERE"  # Replace with your key
    
    if API_KEY == "YOUR_SERPAPI_KEY_HERE":
        print("\n" + "="*80)
        print("SERPAPI GOOGLE SCHOLAR DEMO")
        print("="*80)
        print("\nTo use SerpAPI, you need to:")
        print("1. Sign up for free at https://serpapi.com")
        print("2. Get your API key (100 free searches/month)")
        print("3. Replace 'YOUR_SERPAPI_KEY_HERE' with your actual key")
        print("\nSerpAPI advantages:")
        print("  - No blocking/CAPTCHAs")
        print("  - Structured JSON data")
        print("  - Author profiles with affiliations")
        print("  - Sometimes includes email domains")
        print("\nPricing:")
        print("  • Free: 100 searches/month")
        print("  • Hobby: $50/month for 5,000 searches")
        print("  • Pro: $130/month for 15,000 searches")
        
        # Show example of what the API returns
        print("\n" + "-"*80)
        print("Example API response for searching 'machine learning professor MIT':")
        print("-"*80)
        
        example_response = {
            "search_metadata": {
                "status": "Success",
                "total_results": 450
            },
            "profiles": [
                {
                    "name": "Regina Barzilay",
                    "link": "https://scholar.google.com/citations?user=abc123",
                    "author_id": "abc123",
                    "affiliations": "MIT CSAIL, Professor",
                    "email": "Verified email at mit.edu",
                    "cited_by": 25000,
                    "interests": ["Machine Learning", "Natural Language Processing", "AI for Healthcare"]
                },
                {
                    "name": "Tommi Jaakkola",
                    "link": "https://scholar.google.com/citations?user=def456",
                    "author_id": "def456", 
                    "affiliations": "MIT, Professor",
                    "email": "Verified email at mit.edu",
                    "cited_by": 35000,
                    "interests": ["Machine Learning", "Computational Biology", "Statistics"]
                }
            ]
        }
        
        print(json.dumps(example_response, indent=2))
        
        print("\n" + "-"*80)
        print("What you get from SerpAPI:")
        print("-"*80)
        print("- Professor names")
        print("- University affiliations")
        print("- Email domains (e.g., 'mit.edu')")
        print("- Research interests")
        print("- Citation counts")
        print("- Google Scholar profile links")
        
        print("\nFrom email domains, we can construct likely emails:")
        print("  Regina Barzilay + mit.edu -> regina@mit.edu or barzilay@mit.edu")
        print("  Tommi Jaakkola + mit.edu -> tommi@mit.edu or jaakkola@mit.edu")
        
        return None
    
    # If API key is provided, make actual request
    base_url = "https://serpapi.com/search"
    
    # Search for AI professors
    params = {
        "engine": "google_scholar_profiles",
        "mauthors": "machine learning professor",
        "api_key": API_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        profiles = data.get("profiles", [])
        
        print(f"\nFound {len(profiles)} profiles")
        
        professors = []
        for profile in profiles:
            prof = {
                "name": profile.get("name"),
                "affiliations": profile.get("affiliations"),
                "email_domain": extract_email_domain(profile.get("email", "")),
                "interests": ", ".join(profile.get("interests", [])),
                "cited_by": profile.get("cited_by"),
                "scholar_link": profile.get("link")
            }
            
            # Construct likely email
            if prof["email_domain"] and prof["name"]:
                prof["likely_email"] = guess_email(prof["name"], prof["email_domain"])
            
            professors.append(prof)
        
        return professors
        
    except requests.RequestException as e:
        print(f"API Error: {e}")
        return None

def extract_email_domain(email_text):
    """Extract domain from 'Verified email at domain.edu' text."""
    if "at " in email_text:
        parts = email_text.split("at ")
        if len(parts) > 1:
            return parts[1].strip()
    return None

def guess_email(name, domain):
    """Generate likely email from name and domain."""
    if not name or not domain:
        return None
    
    name_parts = name.lower().split()
    if len(name_parts) >= 2:
        first = name_parts[0]
        last = name_parts[-1]
        
        # Common academic email patterns
        patterns = [
            f"{first}.{last}@{domain}",  # john.smith@mit.edu
            f"{last}@{domain}",           # smith@mit.edu
            f"{first[0]}{last}@{domain}", # jsmith@mit.edu
        ]
        
        # Return most likely pattern
        return patterns[0]
    
    return None

def main():
    """Run SerpAPI demo."""
    
    result = test_serpapi_scholar()
    
    if result:
        # Save to CSV
        output_dir = Path("university_scraper/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_dir / f"serpapi_professors_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["name", "affiliations", "likely_email", "email_domain", 
                         "interests", "cited_by", "scholar_link"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result)
        
        print(f"\nResults saved to: {csv_path}")
        
        # Show sample results
        print("\nSample professors found:")
        for prof in result[:5]:
            print(f"\n{prof['name']}")
            print(f"  Affiliation: {prof['affiliations']}")
            print(f"  Likely email: {prof.get('likely_email', 'N/A')}")
            print(f"  Research: {prof['interests'][:80]}...")
            print(f"  Citations: {prof['cited_by']}")

if __name__ == "__main__":
    main()