# Contributing to Podcast Host Scraper

Thank you for your interest in contributing! This project is 100% open source and welcomes contributions from the community.

## 🚀 Quick Start

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/podcast-host-scraper.git
   cd podcast-host-scraper
   ```
3. **Set up development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate  # Windows
   
   pip install -r requirements-dev.txt
   ```
4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## 🛠️ Development Workflow

### Code Style
We use **Black** for formatting and **Ruff** for linting:

```bash
# Format code
black .

# Check linting
ruff check .

# Type checking
mypy .
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=podcast_scraper --cov-report=html
```

### Pre-commit Hooks
The following checks run automatically before each commit:
- Black code formatting
- Ruff linting
- Type checking with mypy
- Basic Python syntax validation

## 📋 Contribution Types

### 🐛 Bug Fixes
1. Check existing [issues](https://github.com/yourusername/podcast-host-scraper/issues)
2. Create new issue if bug not reported
3. Create branch: `git checkout -b fix/issue-description`
4. Fix the bug with tests
5. Submit pull request

### ✨ New Features  
1. Check [discussions](https://github.com/yourusername/podcast-host-scraper/discussions) for feature requests
2. Create issue to discuss feature before implementation
3. Create branch: `git checkout -b feature/feature-name`
4. Implement feature with comprehensive tests
5. Update documentation
6. Submit pull request

### 🎯 New Podcast Platform Support
We welcome scrapers for additional podcast platforms!

**Popular platforms to add**:
- YouTube Podcasts
- Stitcher
- PodcastAddict
- Castbox
- Overcast
- Pocket Casts

**Implementation guideline**:
```python
from podcast_scraper.base import BasePlatformScraper

class NewPlatformScraper(BasePlatformScraper):
    def scrape_podcasts(self, topic: str) -> List[Dict]:
        # Your implementation
        pass
```

### 📚 Documentation
- Improve README
- Add usage examples  
- Create tutorials
- Fix typos and clarity

## 🔧 Code Organization

```
podcast_host_scraper/
├── podcast_scraper/           # Main package
│   ├── __init__.py
│   ├── base.py               # Base classes
│   ├── platforms/            # Platform-specific scrapers
│   │   ├── apple_podcasts.py
│   │   ├── spotify.py
│   │   └── google_podcasts.py
│   ├── contact/              # Contact extraction
│   │   ├── email_finder.py
│   │   └── website_scraper.py
│   ├── ai/                   # AI scoring
│   │   └── relevance_scorer.py
│   └── utils/                # Utilities
│       ├── validation.py
│       └── data_processing.py
├── tests/                    # Test suite
├── docs/                     # Documentation
└── examples/                 # Usage examples
```

## 📝 Pull Request Guidelines

### PR Title Format
- `feat: add YouTube podcast scraper`
- `fix: handle rate limiting in Apple Podcasts`
- `docs: improve installation instructions`
- `test: add contact extraction tests`

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tests pass locally
- [ ] Added new tests for changes
- [ ] Manual testing completed

## Screenshots/Examples
If applicable, add screenshots or example output
```

### Review Process
1. **Automated checks** must pass (linting, tests, type checking)
2. **Manual review** by maintainers
3. **Discussion** if changes needed
4. **Merge** once approved

## 🎯 Priority Areas

### High Priority
- **New podcast platforms**: YouTube, Stitcher, major platforms
- **Contact quality**: Improve email discovery accuracy
- **Performance**: Optimize scraping speed and reliability
- **Error handling**: Better resilience to site changes

### Medium Priority  
- **AI features**: Better relevance scoring, personalized pitches
- **Export formats**: CRM integrations, different file formats
- **Advanced filtering**: Geographic, language, audience size
- **Documentation**: More examples and tutorials

### Nice to Have
- **Web interface**: Simple web UI for non-technical users
- **API**: REST API for programmatic access
- **Monitoring**: Health checks and status dashboards
- **Analytics**: Success rate tracking and reporting

## 🤝 Community Guidelines

### Be Respectful
- Use inclusive language
- Provide constructive feedback
- Help newcomers get started
- Credit contributors properly

### Quality Standards
- **Code quality**: Follow existing patterns and style
- **Testing**: Add tests for new functionality
- **Documentation**: Update docs for user-facing changes
- **Performance**: Consider impact on scraping speed

### Legal Compliance
- **Public data only**: Only scrape publicly available information
- **Rate limiting**: Respect website rate limits and robots.txt  
- **Privacy**: No storage of personal data without consent
- **Terms of service**: Ensure compliance with platform ToS

## 🐛 Reporting Issues

### Bug Reports
Include:
- **Python version**
- **Operating system**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Error messages/logs**
- **Sample code if applicable**

### Feature Requests
Include:
- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Other solutions considered?
- **Examples**: Similar features in other tools?

## 📞 Getting Help

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and specific problems
- **Code Review**: Tag maintainers in PRs for review

## 🏆 Recognition

Contributors are recognized in:
- **README contributors section**
- **CHANGELOG for each release**  
- **GitHub contributors graph**
- **Special thanks** for significant contributions

---

**Thank you for helping make podcast discovery better for everyone!** 🎙️