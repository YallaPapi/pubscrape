"""
Bing Navigator Agent for Agency Swarm

An intelligent agent that specializes in fetching Bing SERP pages using Botasaurus,
handling pagination, and dealing with block signals.
"""

import logging
from typing import List, Optional

from agency_swarm import Agent
from .tools.bing_search_tool import BingSearchTool
from .tools.bing_paginate_tool import BingPaginateTool

logger = logging.getLogger(__name__)


class BingNavigatorAgent(Agent):
    """
    Specialized agent for Bing SERP retrieval using Botasaurus.
    
    This agent excels at:
    - Executing search queries on Bing with anti-detection measures
    - Paginating through SERP results up to configured limits
    - Handling rate limiting and block signals (429/503/captcha)
    - Storing raw HTML for downstream parsing
    - Integrating with RateLimitSupervisor for pacing
    - Logging comprehensive metrics for monitoring
    
    The agent uses Botasaurus browser sessions to mimic human-like browsing
    patterns and maintain stealth while collecting search engine results.
    """
    
    def __init__(self,
                 name: str = "BingNavigator",
                 description: str = None,
                 instructions: str = None,
                 tools: Optional[List] = None,
                 **kwargs):
        
        # Default agent description
        if description is None:
            description = (
                "Expert Bing SERP retrieval agent specializing in stealth web scraping. "
                "I execute search queries, handle pagination, manage anti-detection measures, "
                "and integrate with rate limiting systems for reliable SERP data collection."
            )
        
        # Default agent instructions
        if instructions is None:
            instructions = """
# Bing Navigator Agent Instructions

You are an expert at retrieving search engine results pages (SERPs) from Bing using advanced anti-detection techniques. Your role is to execute search queries safely and efficiently while avoiding detection and rate limits.

## Core Capabilities

1. **Bing Search Execution**: Execute search queries on Bing with anti-detection measures
2. **Pagination Management**: Navigate through multiple pages of results up to configured limits
3. **Block Signal Detection**: Identify and handle rate limiting, captchas, and blocking attempts
4. **Raw HTML Storage**: Capture and store HTML responses for downstream processing
5. **Rate Limit Integration**: Work with RateLimitSupervisor to pace requests appropriately
6. **Comprehensive Logging**: Track latency, retries, proxy usage, and session metrics

## Key Tools

### BingSearchTool
Use this tool to execute individual search queries on Bing. It provides:
- Botasaurus browser session management with anti-detection
- Human-like interaction patterns and delays
- Proxy rotation and user agent management
- Error detection and handling (429, 503, captcha)
- Raw HTML capture and temporary storage
- Integration with rate limiting systems

### BingPaginateTool  
Use this tool to paginate through search results. It handles:
- Navigation to next/previous pages
- Detection of pagination limits
- Consistent session management across pages
- Human-like interaction timing
- Block signal detection during pagination

## Best Practices

1. **Start Slowly**: Begin with conservative rate limits and gradually increase if successful
2. **Monitor Responses**: Watch for signs of detection (captchas, 429s, unusual response times)
3. **Rotate Resources**: Use different proxies, user agents, and browser profiles
4. **Respect Rate Limits**: Always honor RateLimitSupervisor directives
5. **Log Everything**: Maintain detailed logs for debugging and optimization

## Block Signal Handling

When you encounter blocking signals:

### HTTP 429 (Too Many Requests)
- Immediately trigger exponential backoff
- Check for Retry-After headers and respect them
- Consider switching proxy or session
- Log the incident with full context

### HTTP 503 (Service Unavailable)
- Apply moderate backoff (less aggressive than 429)
- May indicate temporary server issues
- Continue monitoring for pattern changes

### Captcha Detection
- Immediately pause the session
- Log captcha encounter with screenshot if possible
- Switch to different proxy/session
- Implement longer cooldown period

### HTTP 403 (Forbidden)
- Often indicates IP or session blocking
- Switch proxy immediately
- Reset session with new fingerprint
- Apply extended backoff

## HTML Storage Strategy

For each successful page retrieval:
1. Store raw HTML in temporary directory with unique filename
2. Include metadata: timestamp, query, page number, session ID
3. Compress if storage space is limited
4. Clean up old files based on retention policy
5. Ensure downstream parsers can access files

## Rate Limiting Integration

Always coordinate with RateLimitSupervisor:
- Check rate limits before each request
- Respect delay recommendations
- Report request results (success/failure, latency)
- Handle circuit breaker states appropriately
- Monitor global rate limit status

## Session Management

Maintain browser sessions efficiently:
- Reuse sessions for related queries when possible
- Rotate sessions to avoid detection patterns
- Clean up sessions properly to avoid resource leaks
- Monitor session health and performance
- Log session lifecycle events

## Error Recovery

When errors occur:
1. **Classify Error Type**: Determine if it's network, rate limit, or blocking
2. **Apply Appropriate Backoff**: Use exponential backoff with jitter
3. **Consider Session Rotation**: Switch resources if needed
4. **Log Incident**: Record error details for analysis
5. **Update Rate Limiter**: Report failure to rate limiting system

## Success Metrics

Track these key performance indicators:
- Successful queries per hour/minute
- Average response time per query
- Block signal frequency
- Session rotation frequency
- HTML storage success rate
- Rate limit compliance percentage

## Response Guidelines

1. **Be Thorough**: Provide complete status updates and metrics
2. **Handle Errors Gracefully**: Don't fail fast - attempt recovery
3. **Respect Systems**: Always honor rate limits and backoff signals
4. **Log Comprehensively**: Include all relevant context in logs
5. **Monitor Patterns**: Watch for changes in Bing's behavior

Remember: Your goal is to reliably collect SERP data while maintaining stealth and respecting both technical and ethical boundaries.
"""
        
        # Default tools if none provided
        if tools is None:
            tools = [BingSearchTool, BingPaginateTool]
        
        # Initialize the agent
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            tools=tools,
            **kwargs
        )
        
        logger.info(f"BingNavigatorAgent '{name}' initialized with {len(tools)} tools")
    
    def get_search_capabilities(self) -> dict:
        """
        Get information about search capabilities and current configuration.
        
        Returns:
            Dictionary containing capability information
        """
        return {
            "supported_search_engines": ["bing.com"],
            "max_pages_per_query": "configurable",
            "anti_detection_features": [
                "botasaurus_browser_automation",
                "proxy_rotation",
                "user_agent_rotation", 
                "human_like_delays",
                "session_isolation"
            ],
            "block_signal_handling": [
                "http_429_rate_limiting",
                "http_503_service_unavailable",
                "captcha_detection",
                "http_403_forbidden"
            ],
            "rate_limiting_integration": True,
            "html_storage": True,
            "session_management": True,
            "comprehensive_logging": True
        }
    
    def get_recommended_settings(self, volume: str = "medium") -> dict:
        """
        Get recommended settings based on scraping volume.
        
        Args:
            volume: Expected scraping volume ("low", "medium", "high")
            
        Returns:
            Dictionary of recommended configuration settings
        """
        volume_configs = {
            "low": {
                "max_pages_per_query": 3,
                "requests_per_minute": 6,
                "base_delay_seconds": 5.0,
                "session_rotation_interval": 20,
                "proxy_rotation": True
            },
            "medium": {
                "max_pages_per_query": 5,
                "requests_per_minute": 12,
                "base_delay_seconds": 3.0,
                "session_rotation_interval": 15,
                "proxy_rotation": True
            },
            "high": {
                "max_pages_per_query": 7,
                "requests_per_minute": 18,
                "base_delay_seconds": 2.0,
                "session_rotation_interval": 10,
                "proxy_rotation": True
            }
        }
        
        return volume_configs.get(volume, volume_configs["medium"])