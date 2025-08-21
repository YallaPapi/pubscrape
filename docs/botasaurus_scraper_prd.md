# Product Requirements Document: Botasaurus-Powered Contact Discovery System

## Executive Summary
Build a robust, scalable contact discovery system using Botasaurus to bypass anti-bot measures and extract high-quality contact information from protected sources that regular scrapers cannot access.

## Problem Statement
Current scrapers are achieving only 10-58% success rates due to:
- JavaScript challenges (Cloudflare, reCAPTCHA)
- IP-based blocking and rate limiting
- Missing browser fingerprints
- Dynamic content that requires JS execution
- Protected contact information behind interactive elements

## Solution Overview
Implement Botasaurus-powered scrapers that use real browser automation to:
1. Bypass JavaScript challenges and anti-bot systems
2. Extract dynamic content from SPAs (Single Page Applications)
3. Handle multi-step interactions (clicking "Show Email" buttons)
4. Rotate proxies and user agents automatically
5. Mimic human behavior with realistic delays and mouse movements

## Technical Requirements

### Phase 1: Botasaurus Setup & Configuration
- Install Botasaurus on Windows with proper Python environment
- Configure Chrome/Chromium driver for Windows
- Set up proxy rotation system (optional: residential proxies)
- Implement anti-detection measures (user agents, fingerprints)
- Create reusable browser session management
- Build error handling and retry logic
- Set up headless/headed mode switching for debugging

### Phase 2: LinkedIn Profile Scraper
**Target: LinkedIn public profiles of podcast guests, speakers, professors**
- Navigate LinkedIn without login (public view)
- Extract name, title, company, location
- Find contact info in bio sections
- Extract personal website links
- Follow website links to find emails
- Handle LinkedIn's rate limiting gracefully
- Expected success rate: 70%+ for profiles with websites

### Phase 3: Conference Speaker Deep Scraper
**Target: TED, NeurIPS, ICML, Google I/O speaker pages**
- Bypass Cloudflare protection on TED.com
- Execute JavaScript to load dynamic content
- Extract speaker profile URLs
- Navigate to each speaker's page
- Extract all external links (personal sites, social media)
- Follow personal websites and scrape contact pages
- Handle multi-step forms and "reveal email" buttons
- Expected success rate: 60%+ email discovery

### Phase 4: YouTube Channel Contact Extractor
**Target: YouTube channel About sections and linked websites**
- Navigate YouTube without triggering bot detection
- Access channel About pages
- Click "View email address" button (requires JS)
- Extract business inquiry emails
- Follow channel website links
- Scrape linked social media for additional contacts
- Expected success rate: 40%+ (many hide emails)

### Phase 5: University Faculty Advanced Scraper
**Target: University directories with JS-rendered content**
- Handle university SSO login pages (skip if required)
- Navigate JavaScript-heavy directory sites
- Click through pagination and filters
- Expand collapsed sections with contact info
- Extract emails from dynamically loaded content
- Follow faculty personal pages
- Expected success rate: 50%+ improvement over current 10%

### Phase 6: Twitter/X Profile Scraper
**Target: Twitter profiles of identified experts**
- Navigate Twitter without login
- Extract bio information
- Find website links in profiles
- Follow links to find contact information
- Handle Twitter's aggressive anti-bot measures
- Expected success rate: 30%+ email discovery

## Implementation Priorities

### Highest Value First:
1. **LinkedIn Scraper** - Most professionals have LinkedIn, often with websites listed
2. **Conference Speaker Scraper** - High-value contacts already identified, just need better extraction
3. **YouTube Channel Scraper** - Direct access to content creators' business emails
4. **University Faculty Scraper** - Academic experts in AI/tech fields
5. **Twitter Scraper** - Additional enrichment for existing contacts

## Technical Architecture

### Core Components:
```python
BotasaurusScraper/
├── core/
│   ├── browser_manager.py      # Browser session management
│   ├── anti_detection.py       # Fingerprint and behavior randomization
│   ├── proxy_rotator.py        # Proxy management
│   └── error_handler.py        # Retry logic and error recovery
├── scrapers/
│   ├── linkedin_scraper.py     # LinkedIn profile extraction
│   ├── conference_scraper.py   # Conference speaker extraction
│   ├── youtube_scraper.py      # YouTube channel extraction
│   ├── university_scraper.py   # University faculty extraction
│   └── twitter_scraper.py      # Twitter profile extraction
├── extractors/
│   ├── email_extractor.py      # Advanced email pattern matching
│   ├── website_follower.py     # Follow and scrape external sites
│   └── contact_page_finder.py  # Locate and extract from contact pages
├── utils/
│   ├── data_validator.py       # Validate extracted data
│   ├── rate_limiter.py         # Intelligent rate limiting
│   └── human_simulator.py      # Mouse movements, scrolling, delays
└── export/
    └── csv_exporter.py          # Export to CSV format
```

## Success Metrics
- **Email Discovery Rate**: Achieve 60%+ average across all sources (up from current 35%)
- **Data Quality**: 90%+ valid email addresses (verified format)
- **Scraping Success**: 95%+ pages successfully loaded (vs current 70%)
- **Anti-Detection**: <5% blocking rate after implementation
- **Performance**: Process 100 profiles/hour per worker

## Risk Mitigation
- **Legal Compliance**: Only scrape publicly available information
- **Rate Limiting**: Implement adaptive delays based on response times
- **Proxy Costs**: Start with free proxies, upgrade if needed
- **Maintenance**: Build modular system for easy updates when sites change
- **Detection**: Rotate user agents, use residential proxies for high-value targets

## Development Phases

### Week 1: Foundation
- Fix Botasaurus installation issues
- Build core browser management system
- Implement anti-detection measures
- Create test suite with sample URLs

### Week 2: LinkedIn & Conference Scrapers
- Implement LinkedIn public profile scraper
- Build enhanced conference speaker scraper
- Test with 100 profiles each
- Optimize for success rate

### Week 3: YouTube & University Scrapers  
- Implement YouTube channel scraper
- Build university faculty scraper
- Handle edge cases and errors
- Performance optimization

### Week 4: Polish & Scale
- Add Twitter scraper
- Implement proxy rotation
- Build comprehensive export system
- Create monitoring dashboard

## Dependencies
- Python 3.8+
- Botasaurus library
- Chrome/Chromium browser
- Optional: Residential proxy service
- Optional: CAPTCHA solving service

## Testing Strategy
- Unit tests for each extractor module
- Integration tests for full scraping flows
- Performance benchmarks for each source
- Anti-detection validation testing
- Data quality verification

## Rollout Plan
1. Start with LinkedIn scraper (highest value, clearest ROI)
2. Test with 100 profiles, measure success rate
3. If >60% success, scale to 1000 profiles
4. Add conference scraper as second source
5. Progressively add other sources based on success

## Expected Outcomes
- **3x improvement** in email discovery rate
- **5x more sources** successfully scraped
- **High-quality leads** from previously inaccessible sources
- **Scalable system** that can handle 10,000+ profiles/day
- **Maintainable codebase** that adapts to site changes

## Next Steps
1. Fix Botasaurus installation on Windows
2. Build minimal LinkedIn scraper as proof of concept
3. Test anti-detection measures
4. Scale based on initial results