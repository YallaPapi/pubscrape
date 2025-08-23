#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.google_maps_scraper import scrape_google_maps_businesses
from src.scrapers.email_extractor import extract_emails_from_website


def main():
    queries = [
        "coffee shops in Seattle",
    ]
    total = 0
    leads = []

    for q in queries:
        businesses = scrape_google_maps_businesses(q, max_results=10)
        for b in businesses:
            if b.get("website"):
                email = extract_emails_from_website(b["website"]) or ""
                b["email"] = email
            leads.append(b)
            total += 1
            if total >= 10:
                break
        if total >= 10:
            break

    print(f"Generated {len(leads)} leads")
    for i, l in enumerate(leads[:5], 1):
        print(f"{i}. {l.get('name')} | {l.get('email','')} | {l.get('phone','')} | {l.get('website','')}")


if __name__ == "__main__":
    main()
