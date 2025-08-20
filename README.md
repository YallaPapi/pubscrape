# 🎙️ Podcast Host Contact Scraper

**100% Free, Open Source Podcast Host Contact Discovery Tool**

Find contact information for popular podcast hosts who are perfect guests for your show. No subscriptions, no API limits, just pure open-source scraping power.

## 🚀 Features

- **Multi-Platform Discovery**: Apple Podcasts, Spotify, Google Podcasts
- **Smart Contact Extraction**: Websites, emails, booking info, social media
- **AI-Powered Relevance**: Score hosts by topic relevance and interest
- **Bulk Processing**: Handle 1000+ podcasts per search
- **100% Free**: No API costs, subscriptions, or hidden fees
- **Anti-Detection**: Uses Botasaurus for bypass protection

## 📁 Project Structure

```
podcast_host_scraper/     # Main podcast scraper implementation
├── podcast_scraper/      # Core scraping modules
├── scrape_podcasts.py    # CLI interface
├── output/              # Generated CSV and reports
└── tests/               # Test suite

archived/                 # Archived components
└── youtube-scraper/      # Previous YouTube scraper implementation

docs/                     # Documentation
└── podcast_scraper_prd.md # Product requirements
```

## ⚡ Quick Start

```bash
# Navigate to podcast scraper
cd podcast_host_scraper

# Install dependencies
pip install -r requirements.txt

# Find AI-related podcast hosts
python scrape_podcasts.py --topic "artificial intelligence" --limit 100

# Output includes:
# - podcast_contacts.csv (main results)
# - podcast_report.md (summary stats)
```

## 🎯 Current Status

**✅ Working Features:**
- Apple Podcasts directory scraping
- Basic CSV output with podcast metadata
- CLI interface with comprehensive options
- Error logging and reporting

**⚠️ Known Issues:**
- Contact extraction incomplete (0% email discovery rate)
- Missing social media and website discovery
- AI relevance scoring not fully implemented
- Limited multi-platform integration

**📋 Next Development Priorities:**
1. Fix contact extraction from podcast websites
2. Implement social media profile discovery
3. Complete AI relevance scoring integration
4. Add Spotify and Google Podcasts support

## 📊 Example Output

Current CSV structure:
```csv
podcast_name,host_name,host_email,website,social_links,estimated_downloads,ai_relevance_score
DISGRACELAND,,,,,,,unknown
```

Target CSV structure (in development):
```csv
podcast_name,host_name,host_email,website,social_links,estimated_downloads,ai_relevance_score
"The AI Podcast",John Smith,john@aipodcast.com,https://aipodcast.com,@johnsmith_ai,50000,95
```

## 🛠️ Development

The scraper uses:
- **Botasaurus**: Anti-detection web scraping
- **Python 3.11+**: Core implementation
- **Apple Podcasts RSS**: Free podcast directory access
- **OpenAI API**: AI relevance scoring (optional)

## 📄 License

MIT License - Use freely for commercial and personal projects.

---

**Note**: This project evolved from a YouTube scraper to a podcast scraper. The YouTube scraper components have been archived in `archived/youtube-scraper/` and can be reactivated if needed.

⭐ **Star this repo if it helps you discover amazing podcast opportunities!**