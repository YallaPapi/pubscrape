from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json


class HtmlParserTool(BaseTool):
    """
    Parses HTML files from BingNavigator and extracts relevant URLs.
    
    This tool reads HTML content from files (to avoid 512KB OpenAI limit)
    and extracts business-relevant URLs from search engine results.
    """
    
    html_file: str = Field(
        ..., 
        description="Path to HTML file saved by BingNavigator. Should be in format: output/html_cache/bing_*.html"
    )
    max_urls: int = Field(
        50, 
        ge=10, 
        le=200, 
        description="Maximum number of URLs to extract. Higher numbers provide more leads but slower processing."
    )
    filter_domains: bool = Field(
        True, 
        description="Filter out low-quality domains like social media, directories, etc."
    )

    def run(self) -> dict:
        """
        Parse HTML file and extract business-relevant URLs from SERP results.
        Returns clean, filtered URLs ready for domain classification.
        """
        try:
            # Validate file exists
            if not os.path.exists(self.html_file):
                return {
                    "status": "error",
                    "error_type": "file_not_found",
                    "error_message": f"HTML file not found: {self.html_file}",
                    "urls_extracted": 0
                }
            
            # Read HTML content
            try:
                with open(self.html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
            except Exception as e:
                return {
                    "status": "error",
                    "error_type": "file_read_error", 
                    "error_message": f"Could not read HTML file: {str(e)}",
                    "urls_extracted": 0
                }
            
            if len(html_content) < 1000:
                return {
                    "status": "error",
                    "error_type": "insufficient_content",
                    "error_message": f"HTML file too small ({len(html_content)} chars), likely empty or corrupted",
                    "urls_extracted": 0
                }
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract URLs from search results
            urls = set()
            
            # Bing-specific selectors for search result links
            bing_result_selectors = [
                'h2 a[href]',                    # Main result titles
                'a[href*="://"]:not([href*="bing.com"])',  # General links not to Bing
                'cite',                          # URL citations in results
                '.b_algo h2 a',                 # Bing algorithm results  
                '.b_algo .b_attribution cite',  # Bing URL attributions
                'a.sh_ial_ls'                   # Bing local search results
            ]
            
            # Extract URLs using selectors
            for selector in bing_result_selectors:
                elements = soup.select(selector)
                for element in elements:
                    if element.name == 'cite':
                        # Extract URL from cite text
                        url_text = element.get_text().strip()
                        if url_text and not url_text.startswith('http'):
                            url_text = 'https://' + url_text
                        if self._is_valid_business_url(url_text):
                            urls.add(url_text)
                    elif element.get('href'):
                        # Extract from href attribute
                        url = element.get('href')
                        # Clean Bing redirect URLs
                        if 'bing.com' in url and ('&u=' in url or 'url=' in url):
                            url = self._extract_bing_redirect_url(url)
                        if self._is_valid_business_url(url):
                            urls.add(url)
            
            # Convert to list and apply filters
            url_list = list(urls)
            
            if self.filter_domains:
                url_list = self._filter_business_urls(url_list)
            
            # Limit results
            url_list = url_list[:self.max_urls]
            
            # Sort by business relevance (prioritize .com, then others)
            url_list.sort(key=self._url_priority_score, reverse=True)
            
            # Create output with URL metadata
            parsed_urls = []
            for url in url_list:
                parsed = urlparse(url)
                parsed_urls.append({
                    'url': url,
                    'domain': parsed.netloc,
                    'path': parsed.path,
                    'is_root': parsed.path in ['', '/'],
                    'tld': parsed.netloc.split('.')[-1] if '.' in parsed.netloc else '',
                    'subdomain': '.'.join(parsed.netloc.split('.')[:-2]) if len(parsed.netloc.split('.')) > 2 else ''
                })
            
            return {
                "status": "success",
                "urls_extracted": len(parsed_urls),
                "urls": parsed_urls,
                "meta": {
                    "html_file": self.html_file,
                    "html_size": len(html_content),
                    "total_urls_found": len(urls),
                    "urls_after_filtering": len(url_list),
                    "max_urls_requested": self.max_urls,
                    "filter_enabled": self.filter_domains
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_type": "parsing_error",
                "error_message": f"HTML parsing failed: {str(e)}",
                "urls_extracted": 0
            }
    
    def _extract_bing_redirect_url(self, bing_url: str) -> str:
        """Extract actual URL from Bing redirect URL"""
        import urllib.parse as urlparse_module
        
        # Handle Bing redirect patterns
        if '&u=' in bing_url:
            parts = bing_url.split('&u=')
            if len(parts) > 1:
                return urlparse_module.unquote(parts[1].split('&')[0])
        
        if 'url=' in bing_url:
            parts = bing_url.split('url=')
            if len(parts) > 1:
                return urlparse_module.unquote(parts[1].split('&')[0])
        
        return bing_url
    
    def _is_valid_business_url(self, url: str) -> bool:
        """Check if URL is valid and business-relevant"""
        if not url or len(url) < 10:
            return False
            
        # Must be HTTP/HTTPS
        if not url.startswith(('http://', 'https://')):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Must have valid domain
            if not domain or '.' not in domain:
                return False
            
            # Skip search engines and generic sites
            skip_domains = {
                'bing.com', 'google.com', 'yahoo.com', 'duckduckgo.com',
                'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
                'youtube.com', 'pinterest.com', 'tiktok.com',
                'wikipedia.org', 'wikimedia.org'
            }
            
            for skip in skip_domains:
                if skip in domain:
                    return False
            
            return True
            
        except:
            return False
    
    def _filter_business_urls(self, urls: list) -> list:
        """Filter URLs to focus on high-quality business websites"""
        filtered = []
        
        # Prioritize certain TLDs and patterns
        high_value_tlds = {'.com', '.org', '.net', '.edu', '.gov'}
        low_value_domains = {
            'yellowpages', 'yelp', 'mapquest', 'whitepages', 'superpages',
            'foursquare', 'citysearch', 'manta', '411.com', 'spoke.com'
        }
        
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Skip low-value directory sites
            skip_url = False
            for low_val in low_value_domains:
                if low_val in domain:
                    skip_url = True
                    break
            
            if skip_url:
                continue
            
            # Prefer high-value TLDs but don't exclude others entirely
            filtered.append(url)
        
        return filtered
    
    def _url_priority_score(self, url: str) -> int:
        """Calculate priority score for URL sorting (higher = better)"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            score = 0
            
            # TLD scoring
            if domain.endswith('.com'):
                score += 10
            elif domain.endswith('.org'):
                score += 8
            elif domain.endswith('.net'):
                score += 6
            elif domain.endswith('.edu'):
                score += 7
            
            # Prefer root domains over deep paths
            if parsed.path in ['', '/']:
                score += 5
            
            # Prefer shorter domains (likely more authoritative)
            if len(domain) < 20:
                score += 3
            
            # Prefer domains without subdomains
            if len(domain.split('.')) == 2:
                score += 2
            
            return score
            
        except:
            return 0