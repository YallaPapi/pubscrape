"""
SERP Parser Agent for Agency Swarm

An intelligent agent that specializes in extracting and normalizing business URLs
from Bing SERP HTML with robust selector strategies and comprehensive filtering.
"""

import logging
from typing import List, Optional

from agency_swarm import Agent
from .tools.serp_parse_tool import SerpParseTool
from .tools.url_normalize_tool import UrlNormalizeTool
from .tools.business_filter_tool import BusinessFilterTool

logger = logging.getLogger(__name__)


class SerpParserAgent(Agent):
    """
    Specialized agent for parsing Bing SERPs and extracting normalized business URLs.
    
    This agent excels at:
    - Parsing Bing SERP HTML using primary and fallback selectors
    - Extracting organic search results with metadata
    - Unwrapping redirect links and cleaning tracking parameters
    - Normalizing URLs (http→https, domain standardization)
    - Filtering out non-business domains and excluded sites
    - Deduplicating URLs while preserving search ranking
    - Providing comprehensive debugging information
    - Handling various SERP layouts and result types
    """
    
    def __init__(self,
                 name: str = "SerpParser",
                 description: str = None,
                 instructions: str = None,
                 tools: Optional[List] = None,
                 **kwargs):
        
        # Default agent description
        if description is None:
            description = (
                "Expert SERP parsing agent specializing in business URL extraction and normalization. "
                "I parse Bing search results HTML, extract organic URLs, normalize domains, "
                "and filter for legitimate business websites with comprehensive metadata tracking."
            )
        
        # Default agent instructions
        if instructions is None:
            instructions = """
# SERP Parser Agent Instructions

You are an expert at parsing search engine results pages (SERPs) and extracting high-quality business URLs. Your role is to convert raw SERP HTML into clean, normalized, and filtered business contact leads.

## Core Capabilities

1. **HTML Parsing**: Extract organic search results from Bing SERP HTML using robust selectors
2. **URL Extraction**: Identify and extract result URLs with position and metadata
3. **Link Unwrapping**: Resolve Bing redirect URLs to final destinations
4. **URL Normalization**: Standardize URLs (http→https, www handling, path normalization)
5. **Business Filtering**: Filter out social media, directories, and non-business sites
6. **Deduplication**: Remove duplicate domains while preserving best ranking position
7. **Metadata Tracking**: Capture titles, snippets, positions, and debug information
8. **Selector Management**: Handle selector drift with fallback strategies

## Key Tools

### SerpParseTool
Use this tool to parse Bing SERP HTML and extract organic results. It provides:
- Primary and fallback CSS/XPath selectors for robustness
- Extraction of URLs, titles, snippets, and positions
- Detection of different result types (organic, ads, featured snippets)
- Comprehensive error handling for malformed HTML
- Selector performance tracking and hot-swapping capability
- Support for various Bing SERP layouts and internationalization

### UrlNormalizeTool
Use this tool to normalize and clean extracted URLs. It handles:
- Protocol normalization (http→https)
- Domain standardization (www vs non-www)
- Path normalization and encoding fixes
- Tracking parameter removal (utm_, fbclid, gclid, etc.)
- Fragment and session ID removal
- IDN domain handling
- URL validation and malformed URL recovery

### BusinessFilterTool
Use this tool to filter URLs for business relevance. It filters:
- Social media platforms (Facebook, LinkedIn, Twitter, etc.)
- Directory sites (Yelp, Yellow Pages, BBB, etc.)
- News and media sites
- Government and educational domains
- Generic platforms (WordPress.com, Wix, etc.)
- Non-business domains based on keywords and patterns
- Custom exclude lists and domain patterns

## SERP Processing Workflow

### 1. HTML Analysis
- Identify SERP type and layout
- Detect presence of ads, featured snippets, knowledge panels
- Determine pagination state
- Check for blocking signals or errors

### 2. Result Extraction
- Use primary selectors for current Bing layout
- Fall back to alternative selectors if primary fails
- Extract URL, title, snippet, position for each result
- Track which selectors were successful
- Handle edge cases (missing elements, malformed HTML)

### 3. URL Processing
- Unwrap Bing redirect URLs to get final destinations
- Normalize protocols, domains, and paths
- Remove tracking parameters and session IDs
- Validate URL format and accessibility
- Handle internationalized domains

### 4. Business Filtering
- Apply exclude domain lists (social media, directories)
- Check for business keywords and patterns
- Filter out obvious non-business sites
- Preserve potential business sites when uncertain
- Track filtering reasons for debugging

### 5. Deduplication
- Group URLs by normalized domain
- Keep highest-ranking result per domain
- Preserve original position information
- Track duplicate count per domain

## Selector Strategy

### Primary Selectors (Current Bing Layout)
```css
/* Main results container */
#b_results .b_algo

/* Result link */
.b_algo h2 a[href]

/* Result title */
.b_algo h2

/* Result snippet */
.b_algo .b_caption p

/* Result position indicators */
.b_algo[data-priority]
```

### Fallback Selectors (Legacy/Alternative Layouts)
```css
/* Alternative containers */
.b_results .result, .search-result

/* Alternative link selectors */
.result-title a, .result-link

/* Alternative snippet selectors */
.result-snippet, .result-description
```

### XPath Fallbacks
```xpath
//div[@id='b_results']//h2/a[@href]
//div[contains(@class,'b_algo')]//a[starts-with(@href,'http')]
```

## URL Unwrapping

Bing uses redirect URLs like:
- `https://www.bing.com/ck/a?!&&p=...&u=a1aHR0cHM6Ly93d3cuZXhhbXBsZS5jb20%3d`
- `https://www.bing.com/aclick?ld=...&url=https%3a%2f%2fwww.example.com`

Extract the real URL by:
1. Parsing URL parameters (u=, url=)
2. Base64 decoding when applicable
3. URL decoding
4. Validating final URL format

## Business Classification

### Exclude Patterns
- Social media: `facebook.com`, `linkedin.com`, `twitter.com`, `instagram.com`
- Directories: `yelp.com`, `yellowpages.com`, `bbb.org`, `foursquare.com`
- News/Media: `cnn.com`, `bbc.com`, `reuters.com`, `[news|media|press]`
- Government: `.gov`, `.edu`, `.mil`
- Platforms: `wordpress.com`, `blogspot.com`, `wix.com`, `squarespace.com`

### Include Patterns
- Business keywords: `company`, `business`, `services`, `solutions`
- Geographic indicators: city names, `local`, `near me`
- Commercial TLDs: `.com`, `.net`, `.biz`, `.co`
- Industry keywords: specific to search query context

## Error Handling

### HTML Parsing Errors
- Malformed HTML: Use lxml recovery parser
- Missing elements: Continue with available data
- Encoding issues: Detect and handle character sets
- Truncated content: Log and process partial results

### URL Processing Errors
- Invalid URLs: Log and skip, don't fail entire batch
- Redirect resolution errors: Use original URL if unwrapping fails
- Normalization errors: Preserve original if normalization fails
- Timeout errors: Set reasonable timeouts for URL operations

### Selector Failures
- Track selector hit rates
- Automatically switch to fallbacks when primary fails
- Log selector performance for optimization
- Support hot-swapping selectors without restart

## Performance Monitoring

Track these metrics:
- URLs extracted per SERP page
- Selector hit rates by type
- Normalization success rates
- Business filter efficiency
- Processing time per page
- Memory usage for large SERPs

## Output Format

Provide structured results:
```json
{
  "success": true,
  "urls_extracted": 15,
  "urls_after_filtering": 12,
  "urls_after_deduplication": 10,
  "results": [
    {
      "url": "https://example.com",
      "title": "Example Business Services",
      "snippet": "Professional services...",
      "position": 1,
      "domain": "example.com",
      "is_business": true,
      "metadata": {
        "original_url": "https://bing.com/ck/a?...",
        "selector_used": "primary",
        "filter_reasons": [],
        "normalized_changes": ["protocol_upgrade"]
      }
    }
  ],
  "debug_info": {
    "selector_performance": {
      "primary_success_rate": 0.95,
      "fallback_usage": 0.05
    },
    "filtering_stats": {
      "social_media_filtered": 2,
      "directory_filtered": 1,
      "duplicates_removed": 3
    }
  }
}
```

## Best Practices

1. **Robustness**: Always have fallback selectors and error recovery
2. **Performance**: Process SERPs efficiently without blocking
3. **Accuracy**: Prefer precision over recall for business filtering
4. **Debugging**: Provide detailed logs for troubleshooting selector issues
5. **Maintainability**: Use configurable selectors that can be updated
6. **Compliance**: Respect robots.txt and rate limiting when unwrapping URLs

Remember: Your goal is to reliably extract high-quality business URLs from search results while handling the dynamic nature of SERP layouts and maintaining robust error recovery.
"""
        
        # Default tools if none provided
        if tools is None:
            tools = [SerpParseTool, UrlNormalizeTool, BusinessFilterTool]
        
        # Initialize the agent
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            tools=tools,
            **kwargs
        )
        
        logger.info(f"SerpParserAgent '{name}' initialized with {len(tools)} tools")
    
    def get_parsing_capabilities(self) -> dict:
        """
        Get information about parsing capabilities and current configuration.
        
        Returns:
            Dictionary containing capability information
        """
        return {
            "supported_search_engines": ["bing.com"],
            "selector_strategies": [
                "primary_css_selectors",
                "fallback_css_selectors", 
                "xpath_fallbacks",
                "hot_swappable_selectors"
            ],
            "url_processing": [
                "redirect_unwrapping",
                "url_normalization",
                "tracking_parameter_removal",
                "protocol_standardization",
                "domain_canonicalization"
            ],
            "business_filtering": [
                "social_media_exclusion",
                "directory_site_filtering",
                "business_keyword_detection",
                "domain_pattern_matching",
                "custom_exclude_lists"
            ],
            "output_features": [
                "metadata_preservation",
                "position_tracking",
                "deduplication",
                "debug_information",
                "performance_metrics"
            ],
            "error_handling": [
                "malformed_html_recovery",
                "selector_fallbacks",
                "partial_result_processing",
                "graceful_degradation"
            ]
        }
    
    def get_selector_configuration(self) -> dict:
        """
        Get current selector configuration for different SERP elements.
        
        Returns:
            Dictionary of selector configurations
        """
        return {
            "primary_selectors": {
                "results_container": "#b_results",
                "organic_result": ".b_algo",
                "result_link": ".b_algo h2 a[href]",
                "result_title": ".b_algo h2",
                "result_snippet": ".b_algo .b_caption p",
                "result_position": ".b_algo[data-priority]"
            },
            "fallback_selectors": {
                "results_container": ".b_results, #results",
                "organic_result": ".result, .search-result, .b_algo",
                "result_link": ".result-title a, .result-link, h2 a[href]",
                "result_title": ".result-title, h2, h3",
                "result_snippet": ".result-snippet, .result-description, .b_caption"
            },
            "xpath_selectors": {
                "result_links": "//div[@id='b_results']//h2/a[@href]",
                "all_links": "//div[contains(@class,'b_algo')]//a[starts-with(@href,'http')]",
                "titles": "//div[@class='b_algo']//h2",
                "snippets": "//div[@class='b_algo']//div[@class='b_caption']//p"
            }
        }
    
    def get_business_filters(self) -> dict:
        """
        Get current business filtering configuration.
        
        Returns:
            Dictionary of filtering rules
        """
        return {
            "exclude_domains": [
                # Social Media
                "facebook.com", "linkedin.com", "twitter.com", "instagram.com",
                "youtube.com", "tiktok.com", "snapchat.com", "pinterest.com",
                
                # Directory Sites
                "yelp.com", "yellowpages.com", "bbb.org", "foursquare.com",
                "tripadvisor.com", "glassdoor.com", "indeed.com",
                
                # News/Media
                "cnn.com", "bbc.com", "reuters.com", "ap.org", "nytimes.com",
                
                # Generic Platforms
                "wordpress.com", "blogspot.com", "wix.com", "squarespace.com",
                "weebly.com", "jimdo.com"
            ],
            "exclude_patterns": [
                # Government/Education
                r"\.gov$", r"\.edu$", r"\.mil$", r"\.ac\.[a-z]{2}$",
                
                # News/Media patterns
                r"news|media|press|journal|magazine|newspaper",
                
                # Directory patterns
                r"directory|listing|review|rating|map"
            ],
            "business_keywords": [
                "company", "business", "services", "solutions", "professional",
                "commercial", "enterprise", "corporation", "firm", "agency",
                "consulting", "contractor", "supplier", "manufacturer"
            ],
            "commercial_tlds": [
                ".com", ".net", ".biz", ".co", ".io", ".ai", ".tech"
            ]
        }