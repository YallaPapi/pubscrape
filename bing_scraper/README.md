# Bing Search Scraper

Production-ready lead generation system using Botasaurus for scraping Bing search results and extracting business contact information.

## 🚀 Quick Start

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Test environment
python test_environment.py

# Run scraper
python main.py
```

### Docker Deployment

```bash
# Build container
docker build -t bing-scraper .

# Run container
docker run -it --env-file .env bing-scraper
```

## 📁 Project Structure

```
bing_scraper/
├── src/
│   ├── config/           # Configuration management
│   ├── search/           # Bing search interface
│   ├── anti_detection/   # Anti-detection features
│   ├── extraction/       # Email extraction engine
│   └── data/            # Data processing and export
├── tests/               # Unit and integration tests
├── output/              # Generated CSV files
├── logs/                # Application logs
├── main.py              # Main entry point
└── requirements.txt     # Python dependencies
```

## ⚙️ Configuration

Key environment variables in `.env`:

- `MAX_REQUESTS_PER_MINUTE`: Rate limiting (default: 15)
- `MAX_CONCURRENT_SESSIONS`: Concurrent browser sessions (default: 2)
- `HEADLESS_MODE`: Run browsers in headless mode (default: true)
- `USER_AGENT_ROTATION`: Enable user agent rotation (default: true)
- `PROXY_ENABLED`: Enable proxy support (default: false)

## 🎯 Features

- **Anti-Detection**: User agent rotation, browser fingerprinting, resource blocking
- **Rate Limiting**: Configurable request limits and retry logic
- **Email Extraction**: Multi-strategy email discovery and validation
- **Search Verticals**: Real estate, local services, e-commerce, professional services
- **CSV Export**: Clean, deduplicated lead data with confidence scoring
- **Docker Support**: Containerized deployment for production scaling

## 🔧 Development

### Requirements

- Python 3.10+
- Botasaurus 4.0.24+
- Chrome/Chromium browser

### Testing

```bash
# Run environment test
python test_environment.py

# Run unit tests (when implemented)
pytest tests/unit/

# Run integration tests (when implemented)
pytest tests/integration/
```

## 📊 Output Format

CSV fields:
- email: Extracted email address
- source_website: Website where email was found
- search_query: Original Bing search query
- found_date: Timestamp when email was extracted
- confidence_score: Email quality/confidence rating
- website_type: Site categorization (shopify, wordpress, etc.)
- business_name: Extracted business name
- phone: Extracted phone number (if available)
- address: Extracted address (if available)

## 🛡️ Security

- Environment variable configuration for sensitive data
- Proxy support for IP rotation
- Rate limiting to avoid service blocks
- Audit logging for all scraping activities

## 📝 License

MIT License - See LICENSE file for details.