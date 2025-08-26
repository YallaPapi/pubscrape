# Podcast Scraper Status & Issues Report (Bulk Email Extraction)

Date: 2025-08-20

## Current Status
- Apple pipeline working end-to-end, including website discovery and email extraction.
  - Example: DISGRACELAND found website and 1 email; CSV exported to `podcast_host_scraper/output/podcast_contacts.csv`.
- Live progress support added: `--progress` prints heartbeats and writes `podcast_host_scraper/output/progress.json` during runs.
- Bulk scaffolding added:
  - iTunes API platform (`itunes_api`) to fetch many podcasts reliably.
  - LearnOutLoud platform scaffolded for direct site scraping (needs selector refinement).

## Key Fixes Implemented
- Apple Podcasts scraper stability:
  - Robust element-to-text handling to avoid `'Element'` attribute errors.
  - Page-source regex fallback to collect links.
- Contact discovery improvements:
  - RSS parsing: derive external site (links/entries) and extract emails from feed metadata/entries.
  - Avoid treating Apple/Spotify directories as the official website.
  - DuckDuckGo fallback (no API key) to find official sites when Google Custom Search not configured.
  - Contact page detection tolerates 3xx; improved patterns.
- Social enrichment:
  - Fallback to `document.documentElement.outerHTML` when `page_source` unavailable in Botasaurus driver.
- CLI & UX:
  - Added `--progress` flag for real-time observation (prints `[LIVE] ...` and writes progress JSON).
  - Log setup forced to ensure consistent output to `output/scraper.log`.

## Repro & Correct Invocation
- Ensure you run commands from `podcast_host_scraper/` (not repo root) to avoid path errors:
```bash
cd podcast_host_scraper
python scrape_podcasts.py --topic "technology" --platforms apple_podcasts --limit 10 --enrich-contacts --no-report --log-level INFO --progress
```
- The earlier "hangs" were often due to running from `ytscrape/` root, which caused:
  - `can't open file 'C:\...\ytscrape\scrape_podcasts.py'`: file is in `podcast_host_scraper/`.
  - Missing log paths like `output/scraper.log` when not inside the tool directory.

## Platforms
- Apple (`apple_podcasts`):
  - Works; currently yielding limited chart URLs via dynamic DOM. We added page-source fallback. For larger batches, the iTunes API is recommended.
- iTunes API (`itunes_api`):
  - New platform to fetch many podcasts quickly without brittle DOM scraping.
  - Use for bulk runs, then enrich for emails.
- LearnOutLoud (`learnoutloud`):
  - Initial scraper added (directory/page parser); currently returns 0 due to directory structure filtering. Needs selector & pagination tuning against real pages like `https://www.learnoutloud.com/Podcast-Directory`.
  - Site reference: https://www.learnoutloud.com

## How to Bulk Run (Recommended)
```bash
cd podcast_host_scraper
# Bulk discover via iTunes API (10+) with live progress and enrichment
python scrape_podcasts.py --topic "technology" --platforms itunes_api --limit 25 --enrich-contacts --no-report --log-level INFO --progress

# Bulk (Apple only) – may be smaller due to Apple charts page structure
python scrape_podcasts.py --topic "technology" --platforms apple_podcasts --limit 25 --enrich-contacts --no-report --log-level INFO --progress
```

## Output Locations
- Logs: `podcast_host_scraper/output/scraper.log`
- Live progress: `podcast_host_scraper/output/progress.json`
- CSV: `podcast_host_scraper/output/podcast_contacts.csv`
- Optional: `test_results.csv`, `test_report.md` from simple test script

## Optional API Keys (for higher yield)
- Spotify: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- Google CSE: `GOOGLE_CUSTOM_SEARCH_KEY`, `GOOGLE_SEARCH_ENGINE_ID`

## Next Steps
1. iTunes API bulk run + enrichment (primary path for large lists).
2. LearnOutLoud: implement pagination & robust selectors across category pages; extract external sites.
3. Add per-platform backoff/retry and rotate categories for Apple charts to increase diversity.
4. Add configurable domain allow/block lists for website discovery.
5. Extend email heuristics (info@, press@, booking@) prioritization and confidence scoring.

## Known Limitations
- Some sites hide email behind forms/JS; enrichment returns partial contact methods.
- Social platforms often block scraping; enrichment degrades gracefully.

---
Maintained in repo: this report documents current findings and actionable next steps for bulk email scraping readiness.
