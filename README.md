# DuckDuckGo Search Scraper (Botasaurus/Selenium)

This module provides a production-style, headless browser scraper for DuckDuckGo (DDG). It supports single-query scraping and batch runs with validation and exports.

## Quick Smoke Test (fast)

```
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install botasaurus selenium lxml beautifulsoup4 requests

cd pubscrape
python smoke_ddg.py "restaurants Seattle Washington"
```

You should see a small set of results printed and a JSON file under `pubscrape/output/`.

## Batch Run (comprehensive)

```
cd pubscrape
python -m src.scrapers.real_duckduckgo_scraper
```

This runs 30+ targeted queries, deduplicates, validates, and emits a JSON file with metrics.

## Notes and Next Steps

- Current organic scraping returns many aggregator pages; we will prioritize DDG Places results (business cards) and add filtering.
- We will add runtime caps and a `--smoke` mode to ensure quick validation (< 2 min).
- See `../ROADMAP.md` for the detailed plan and acceptance criteria.

