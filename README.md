# Bing Search Engine Scraper with Botasaurus and Agency Swarm

A production-ready, AI-powered contact discovery system that uses Bing search to find business emails at scale while maintaining compliance and minimizing detection.

## 🎯 Overview

This system combines **Botasaurus** for anti-detection browser automation with **Agency Swarm** for multi-agent AI orchestration to create a robust, scalable email scraping solution.

### Key Features

- **🤖 13 Specialized AI Agents** - Campaign CEO, Query Builder, Bing Navigator, etc.
- **🛡️ Advanced Anti-Detection** - User-agent rotation, proxy management, human-like delays
- **⚡ Rate Limiting & Circuit Breakers** - Smart throttling and adaptive backoff
- **📧 Multi-Method Email Extraction** - Regex, obfuscation handling, context scoring
- **🔧 Configuration-Driven** - YAML configs per campaign
- **📊 Comprehensive Monitoring** - Real-time dashboards, metrics, and alerts
- **🐳 Docker Ready** - Full containerization with monitoring stack

### Target Performance

- **500-1000 leads/day** per campaign
- **60-70% SERP extraction** success rate
- **25-35% email discovery** rate on visited sites
- **<10% block rate** with proper configuration

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Git**
- **Docker & Docker Compose** (optional, for production)
- **Chrome/Chromium** browser

### 1. Clone and Setup

```bash
git clone <repository-url>
cd pubscrape

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
source venv/Scripts/activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file with your API keys:

```bash
# Core AI APIs
ANTHROPIC_API_KEY=your_anthropic_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional: Additional APIs
OPENROUTER_API_KEY=your_openrouter_key_here
YOUTUBE_API_KEY=your_youtube_key_here
```

### 3. Verify Installation

```bash
# Test Agency Swarm CLI
agency-swarm --help

# Test Botasaurus installation
python -c "import botasaurus; print('Botasaurus ready!')"

# Run tests
pytest tests/ -v
```

## 📁 Project Structure

```
pubscrape/
├── src/
│   ├── core/           # Core scraping components
│   ├── infra/          # Anti-detection & infrastructure  
│   ├── pipeline/       # Data processing pipeline
│   └── cli/            # Command-line interface
├── configs/            # Campaign configurations
├── out/               # Output files (CSV, JSON, logs)
├── tests/             # Test suites
├── .taskmaster/       # TaskMaster project management
├── venv/             # Virtual environment
├── Dockerfile        # Container configuration
├── docker-compose.yml # Multi-service orchestration
└── requirements.txt   # Python dependencies
```

## 🤖 Agency Swarm Agents

The system uses 13 specialized AI agents:

1. **CampaignCEO** - Orchestrates campaigns and delegates tasks
2. **QueryBuilder** - Expands search templates to concrete queries  
3. **BingNavigator** - Fetches SERPs via Botasaurus
4. **SerpParser** - Parses SERP HTML to extract URLs
5. **DomainClassifier** - Filters and prioritizes business domains
6. **SiteCrawler** - Visits site pages via Botasaurus
7. **EmailExtractor** - Finds and scores emails using multiple methods
8. **ValidatorDedupe** - Validates and deduplicates emails
9. **Exporter** - Writes CSV/JSON outputs
10. **RateLimitSupervisor** - Enforces rate limits and backoff
11. **AntiDetectionSupervisor** - Manages proxies and sessions
12. **MonitoringAnalyst** - Tracks metrics and raises alerts
13. **IncidentResponder** - Handles operational incidents

## 📚 TaskMaster Integration

This project uses TaskMaster for development workflow:

```bash
# View current tasks
task-master list

# Work on next task
task-master next

# Mark task complete  
task-master set-status --id=X --status=done
```

## 📄 License

MIT License - Use freely for commercial and personal projects.

---

**Note**: This project evolved from a podcast scraper to a comprehensive Bing scraper. Previous implementations have been archived in the `archived/` directory.

⭐ **Star this repo for production-ready contact discovery!**