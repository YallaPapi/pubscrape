#!/usr/bin/env python3
import sys
from src.scrapers.real_duckduckgo_scraper import scrape_real_seattle_restaurants

def main():
    query = " ".join(sys.argv[1:]).strip() or "restaurants Seattle Washington"
    print(f"Running single-query smoke test: {query}")
    try:
        results = scrape_real_seattle_restaurants(query, max_results=8)
        print(f"\nExtracted: {len(results)} records")
        for r in results[:5]:
            print({k: r.get(k) for k in ['name','address','phone','website','source','rating']})
    except Exception as e:
        print("ERROR:", repr(e))

if __name__ == "__main__":
    main()
