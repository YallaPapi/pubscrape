# Production Lead Generation System - Usage Guide

## Overview

This is a complete, production-ready lead generation system that:
- **Scrapes search engines** (Bing) to find businesses
- **Extracts contact information** from business websites  
- **Validates email addresses** using multiple methods
- **Generates CSV files** ready for outreach campaigns
- **Uses anti-detection** measures to avoid blocking

## Quick Start

### 1. Test the System
```bash
python lead_generator_main.py --test
```
This runs a small test campaign to verify everything works.

### 2. Generate Sample Configuration
```bash
python lead_generator_main.py --sample-config
```
Creates `sample_campaign.yaml` with all configuration options explained.

### 3. Run a Quick Campaign
```bash
python lead_generator_main.py --query "optometrist Atlanta" --leads 50 --location "Atlanta, GA"
```

### 4. Run a Full Campaign with Configuration
```bash
python lead_generator_main.py --config campaign.yaml
```

## System Requirements

### Dependencies
All required packages are in `requirements.txt`:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `botasaurus>=4.0.0` - Anti-detection web scraping
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `pandas` - Data processing
- `pyyaml` - Configuration files

### System Requirements
- **Python 3.8+**
- **Chrome/Chromium browser** (for Botasaurus)
- **4GB+ RAM** (for browser automation)
- **Stable internet connection**

## Configuration

### Command Line Options

```bash
python lead_generator_main.py [OPTIONS]

Options:
  --config FILE         Campaign configuration file (YAML/JSON)
  --query "QUERY"       Search query for quick campaign
  --leads N             Number of leads to generate (default: 25)
  --location "LOCATION" Geographic location
  --output DIR          Output directory (default: output)
  --test                Run test campaign
  --sample-config       Create sample configuration file
  --verbose, -v         Verbose logging
```

### Configuration File Format

Create a YAML file with your campaign settings:

```yaml
# Campaign basics
name: "optometrist_atlanta_campaign"
description: "Lead generation for optometrists in Atlanta area"

# Search configuration
search_queries:
  - "optometrist Atlanta"
  - "eye doctor Atlanta"
  - "vision care Atlanta"
  - "ophthalmologist Atlanta"

max_leads_per_query: 25
max_pages_per_query: 3
location: "Atlanta, GA"

# Business filtering
business_types:
  - "optometry"
  - "eye care"
  - "vision"
  - "ophthalmology"

exclude_keywords:
  - "yelp"
  - "reviews"
  - "directory"
  - "wikipedia"

# Quality thresholds
min_business_score: 0.5
min_email_confidence: 0.6

# Email validation
enable_email_validation: true
enable_dns_checking: false  # Set to true for thorough validation

# Output settings
output_directory: "campaign_output"
include_report: true

# Performance settings
max_concurrent_extractions: 3
request_delay_seconds: 2.5
timeout_seconds: 20

# Anti-detection
use_rotating_user_agents: true
headless_mode: true
```

## Output Files

The system generates several output files:

### 1. CSV File (Primary Output)
- **Filename**: `{campaign_name}_{timestamp}.csv`
- **Format**: Standard CSV compatible with CRMs
- **Columns**: 
  - `business_name` - Business/company name
  - `primary_email` - Main contact email
  - `primary_phone` - Main phone number
  - `contact_name` - Contact person name
  - `contact_title` - Job title/role
  - `website` - Business website URL
  - `address` - Physical address
  - `city`, `state` - Location information
  - `linkedin_url` - LinkedIn profile
  - `lead_score` - Quality score (0-1)
  - `email_confidence` - Email validation confidence
  - `is_actionable` - Ready for outreach (true/false)
  - `source_query` - Which search query found this lead
  - `extraction_date` - When the lead was extracted

### 2. Metadata File
- **Filename**: `{campaign_name}_{timestamp}_metadata.json`
- **Contains**: Campaign configuration, statistics, file paths

### 3. Campaign Report
- **Filename**: `campaign_report_{timestamp}.json`
- **Contains**: Detailed analysis, quality distribution, performance metrics

### 4. Log Files
- **Location**: `{output_directory}/logs/`
- **Contains**: Detailed execution logs for debugging

## Lead Quality Scoring

The system automatically scores leads based on:

### Email Quality (40% of score)
- **High**: CEO@, firstname.lastname@, contact@ patterns
- **Medium**: info@, support@, admin@ patterns  
- **Low**: Generic or personal email domains

### Data Completeness (60% of score)
- Business name and email (required)
- Phone number (+20%)
- Contact name (+15%)
- Address information (+10%)
- Social media profiles (+10%)

### Validation Status
- **Valid**: Email passes syntax and domain checks
- **Invalid**: Failed validation (excluded from final results)
- **Actionable**: Meets all quality thresholds

## Best Practices

### 1. Query Selection
- **Be specific**: "optometrist Atlanta" vs "eye doctor"
- **Include location**: Better targeting and relevance
- **Use variations**: Different terms for same business type
- **Test first**: Run small campaigns to optimize queries

### 2. Quality Filtering
- **Set appropriate thresholds**: Balance quantity vs quality
- **Use business type filters**: Focus on relevant businesses
- **Exclude irrelevant sites**: Directories, social media, etc.

### 3. Performance Optimization
- **Reasonable delays**: 2-3 seconds between requests
- **Limit concurrency**: 3-5 concurrent extractions max
- **Monitor logs**: Check for blocking or errors
- **Use headless mode**: Faster and more stable

### 4. Email Validation
- **Enable validation**: Always validate emails before outreach
- **DNS checking**: Enable for maximum accuracy (slower)
- **Confidence thresholds**: 0.5+ for general use, 0.7+ for premium campaigns

## Troubleshooting

### Common Issues

#### No Results Found
```
ISSUE: Search returns no business URLs
SOLUTIONS:
- Check internet connectivity
- Verify search queries are valid
- Try different search terms
- Check location spelling
```

#### Email Extraction Fails
```
ISSUE: No contact information extracted
SOLUTIONS:
- Increase timeout_seconds (try 30)
- Reduce max_concurrent_extractions (try 1)
- Check website accessibility manually
- Review error logs
```

#### Validation Errors
```
ISSUE: Email validation fails
SOLUTIONS:
- Disable DNS checking temporarily
- Check internet connectivity
- Reduce batch sizes
- Review validation logs
```

#### Performance Issues
```
ISSUE: System runs slowly or crashes
SOLUTIONS:
- Reduce max_concurrent_extractions
- Increase request_delay_seconds
- Enable headless_mode
- Close other applications
- Check system resources
```

### Log Analysis

Check log files for detailed error information:
```bash
# View latest log
tail -f campaign_output/logs/lead_generation_*.log

# Search for errors
grep ERROR campaign_output/logs/lead_generation_*.log

# Check extraction success rate
grep "extracted" campaign_output/logs/lead_generation_*.log
```

## Advanced Usage

### Custom Business Detection
Modify the `detect_business_relevance()` function in `lead_generator_main.py` to add:
- Industry-specific keywords
- Custom scoring algorithms
- Advanced filtering logic

### Email Validation Customization
Adjust validation parameters in `enhanced_email_validator.py`:
- Add domain whitelists/blacklists
- Modify quality scoring
- Custom validation rules

### Anti-Detection Tuning
Modify Botasaurus settings for different environments:
- Proxy configuration
- User agent rotation
- Request patterns
- Browser fingerprinting

## Integration with CRMs

### Importing to Popular CRMs

#### HubSpot
1. Export CSV from system
2. Go to Contacts > Import
3. Map fields: email → Email, business_name → Company
4. Review and import

#### Salesforce
1. Use Data Import Wizard
2. Map to Leads or Contacts
3. Use business_name for Account Name
4. Set lead source as "Web Scraping"

#### Pipedrive
1. Go to Contacts > Import
2. Map fields appropriately
3. Use lead_score for prioritization

### Email Marketing Tools

#### Mailchimp
1. Create new audience
2. Import CSV with email as primary field
3. Use custom fields for business_name, contact_name

#### Constant Contact
1. Add contacts from file
2. Map email and name fields
3. Create segments based on lead_score

## API Integration

The system can be integrated into larger workflows:

```python
from lead_generator_main import ProductionLeadGenerator, CampaignConfig

# Create configuration
config = CampaignConfig(
    name="api_campaign",
    search_queries=["dentist Miami"],
    max_leads_per_query=50
)

# Run campaign
generator = ProductionLeadGenerator(config)
results = generator.run_campaign()

# Access results
leads_csv = results['csv_file']
total_leads = results['total_leads']
```

## Support and Maintenance

### Regular Maintenance
- **Update dependencies**: `pip install -r requirements.txt --upgrade`
- **Clear old profiles**: Delete `profiles/` directory monthly
- **Archive old output**: Move completed campaigns to archive
- **Monitor logs**: Check for new blocking patterns

### Performance Monitoring
- Track success rates over time
- Monitor request delays and timeouts
- Check email validation accuracy
- Review lead quality scores

### Updating Configuration
- Test changes on small campaigns first
- Keep backup of working configurations
- Document custom modifications
- Version control configuration files

## Legal and Compliance

### Important Considerations
- **Respect robots.txt**: System honors website crawling policies
- **Rate limiting**: Built-in delays prevent server overload
- **Data privacy**: Follow GDPR, CCPA guidelines for contact data
- **Terms of service**: Comply with search engine ToS
- **Business use**: Only contact businesses for legitimate purposes

### Best Practices
- Always provide opt-out mechanisms
- Be transparent about data sources
- Respect do-not-contact preferences
- Follow CAN-SPAM Act requirements
- Maintain data security standards

---

## Quick Reference

### Start Test Campaign
```bash
python lead_generator_main.py --test
```

### Generate Sample Config
```bash
python lead_generator_main.py --sample-config
```

### Run Quick Campaign
```bash
python lead_generator_main.py --query "business type location" --leads 50
```

### Run Full Campaign
```bash
python lead_generator_main.py --config my_campaign.yaml --verbose
```

**Need help?** Check the log files in `{output_directory}/logs/` for detailed error information.