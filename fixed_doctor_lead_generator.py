#!/usr/bin/env python3
"""
Fixed Doctor Lead Generator - Addresses business URL detection issues
"""

import re
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse, unquote
from lead_generator_main import ProductionLeadGenerator, CampaignConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_real_url_from_bing_redirect(bing_url: str) -> str:
    """Extract the real URL from Bing redirect URL"""
    try:
        # Bing redirect URLs contain the real URL encoded in the 'u' parameter
        if "bing.com/ck/a" in bing_url:
            # Look for u=a1 parameter which contains the base64-encoded URL
            match = re.search(r'u=([^&]+)', bing_url)
            if match:
                encoded_url = match.group(1)
                # Decode the URL (it's often base64-like encoded)
                try:
                    # Try to extract recognizable URL patterns
                    if encoded_url.startswith('a1aHR0c'):
                        # This looks like base64 for "http"
                        import base64
                        decoded = base64.b64decode(encoded_url[2:] + '==').decode('utf-8', errors='ignore')
                        return decoded
                    elif 'http' in unquote(encoded_url):
                        return unquote(encoded_url)
                except:
                    pass
        
        # If it's already a direct URL, return it
        if bing_url.startswith('http') and 'bing.com' not in bing_url:
            return bing_url
            
        return bing_url
    except:
        return bing_url

def improved_business_detection(title: str, description: str, url: str, query: str) -> bool:
    """Improved business detection specifically for medical/doctor searches"""
    
    # Extract real URL from Bing redirects
    real_url = extract_real_url_from_bing_redirect(url)
    
    text_to_check = f"{title} {description}".lower()
    real_url_lower = real_url.lower()
    
    # Medical-specific business indicators
    medical_indicators = [
        'doctor', 'physician', 'clinic', 'medical', 'health', 'hospital', 
        'practice', 'healthcare', 'md', 'dvm', 'dds', 'specialist',
        'dentist', 'orthodontist', 'dermatologist', 'cardiologist',
        'orthopedic', 'pediatric', 'family medicine', 'internal medicine',
        'contact', 'appointment', 'location', 'phone', 'email', 'office',
        'consultation', 'patient', 'treatment', 'therapy', 'surgery'
    ]
    
    # Business structure indicators
    business_indicators = [
        'about us', 'contact us', 'our team', 'staff', 'services',
        'location', 'hours', 'appointment', 'phone', 'email',
        'address', 'directions', 'office', 'clinic', 'center'
    ]
    
    # Exclude non-business sites but be more lenient for medical content
    exclude_patterns = [
        'wikipedia.org', 'facebook.com', 'twitter.com', 'instagram.com',
        'linkedin.com/in/', 'youtube.com', 'google.com', 'reddit.com',
        'pinterest.com', 'tiktok.com'
    ]
    
    # Strong exclusions for directory sites (but allow some medical directories)
    strong_exclude = [
        'yelp.com', 'yellowpages.com', 'whitepages.com', 'superpages.com',
        'foursquare.com', 'bbb.org'
    ]
    
    # Check strong exclusions first
    for pattern in strong_exclude:
        if pattern in real_url_lower:
            return False
    
    # Check general exclusions (but be more lenient)
    exclude_count = 0
    for pattern in exclude_patterns:
        if pattern in real_url_lower:
            exclude_count += 1
    
    # If multiple exclusion patterns, likely not a business site
    if exclude_count >= 2:
        return False
    
    # Count medical indicators
    medical_score = sum(1 for indicator in medical_indicators if indicator in text_to_check)
    
    # Count business indicators  
    business_score = sum(1 for indicator in business_indicators if indicator in text_to_check)
    
    # Check for specific medical domains
    medical_domains = ['.md', 'medical', 'health', 'clinic', 'hospital', 'doctor']
    domain_score = sum(1 for domain in medical_domains if domain in real_url_lower)
    
    # Calculate total relevance score
    total_score = medical_score + business_score + domain_score
    
    # More lenient scoring for medical searches
    if 'doctor' in query.lower() or 'medical' in query.lower():
        return total_score >= 1  # Very lenient for medical queries
    else:
        return total_score >= 2  # Normal threshold
        
def fixed_scrape_with_url_extraction(query: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Scrape Bing with improved URL extraction and business detection"""
    from lead_generator_main import scrape_bing_results
    
    logging.info(f"Scraping Bing for: {query} (with URL extraction)")
    
    # Get raw results
    results = scrape_bing_results(query, max_pages)
    
    # Process each result with improved logic
    processed_results = []
    
    for result in results:
        # Extract real URL
        original_url = result.get('url', '')
        real_url = extract_real_url_from_bing_redirect(original_url)
        
        # Update result with real URL
        result['original_bing_url'] = original_url
        result['url'] = real_url
        result['domain'] = urlparse(real_url).netloc.lower()
        
        # Apply improved business detection
        title = result.get('title', '')
        description = result.get('description', '')
        
        is_business = improved_business_detection(title, description, real_url, query)
        result['is_business'] = is_business
        
        # Add debug info
        result['business_detection_debug'] = {
            'original_classification': result.get('is_business_original', False),
            'improved_classification': is_business,
            'real_url_extracted': real_url != original_url
        }
        
        processed_results.append(result)
        
        logging.debug(f"Processed: {title[:50]}... -> Business: {is_business}")
    
    business_count = sum(1 for r in processed_results if r.get('is_business', False))
    logging.info(f"Found {len(processed_results)} results, {business_count} classified as businesses")
    
    return processed_results

class FixedDoctorLeadGenerator(ProductionLeadGenerator):
    """Fixed version with improved business detection for medical searches"""
    
    def discover_business_urls(self) -> List[str]:
        """Discover business URLs with fixed medical business detection"""
        self.logger.info("Starting business URL discovery (FIXED VERSION)")
        
        all_urls = []
        
        for i, query in enumerate(self.config.search_queries, 1):
            self.logger.info(f"Processing query {i}/{len(self.config.search_queries)}: {query}")
            
            try:
                # Add location to query if specified
                search_query = query
                if self.config.location:
                    search_query = f"{query} {self.config.location}"
                
                # Use fixed scraping with URL extraction
                search_results = fixed_scrape_with_url_extraction(
                    search_query, 
                    max_pages=self.config.max_pages_per_query
                )
                
                # Filter for business URLs
                business_urls = []
                for result in search_results:
                    if result.get('is_business', False):
                        url = result['url']
                        if self.is_valid_business_url(url):
                            business_urls.append(url)
                            self.logger.debug(f"  Added business URL: {url}")
                        else:
                            self.logger.debug(f"  Rejected URL (validation): {url}")
                    else:
                        self.logger.debug(f"  Not classified as business: {result.get('title', 'N/A')}")
                
                # Limit per query
                business_urls = business_urls[:self.config.max_leads_per_query]
                
                self.logger.info(f"  Found {len(business_urls)} business URLs for query '{query}'")
                for j, url in enumerate(business_urls, 1):
                    self.logger.info(f"    {j}. {url}")
                
                all_urls.extend(business_urls)
                self.stats['queries_processed'] += 1
                self.stats['urls_discovered'] += len(business_urls)
                
                # Delay between queries
                if i < len(self.config.search_queries):
                    time.sleep(self.config.request_delay_seconds)
                    
            except Exception as e:
                self.logger.error(f"Error processing query '{query}': {e}")
                self.stats['errors'] += 1
                continue
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in all_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        self.logger.info(f"Total unique business URLs: {len(unique_urls)}")
        return unique_urls

def test_fixed_doctor_generator():
    """Test the fixed doctor lead generator"""
    print("=" * 60)
    print("TESTING FIXED DOCTOR LEAD GENERATOR")
    print("=" * 60)
    
    # Create test configuration
    config = CampaignConfig(
        name="fixed_doctor_test",
        description="Test fixed doctor lead generation",
        search_queries=["doctors Miami Florida"],
        max_leads_per_query=5,
        max_pages_per_query=2,
        location="",  # Already included in query
        output_directory="validation_test",
        include_report=True,
        request_delay_seconds=1.0,
        timeout_seconds=15,
        min_business_score=0.3,  # Lower threshold for testing
        min_email_confidence=0.4  # Lower threshold for testing
    )
    
    # Create fixed generator
    generator = FixedDoctorLeadGenerator(config)
    
    try:
        # Run campaign
        print("Running fixed doctor lead generation...")
        results = generator.run_campaign()
        
        print(f"\nRESULTS:")
        print(f"  CSV File: {results['csv_file']}")
        print(f"  Total Leads: {results['total_leads']}")
        print(f"  URLs Discovered: {results['statistics']['urls_discovered']}")
        print(f"  URLs -> Leads Rate: {(results['total_leads']/max(1, results['statistics']['urls_discovered'])*100):.1f}%")
        
        if results['total_leads'] > 0:
            print(f"\n✅ SUCCESS: Fixed generator working!")
            print(f"   Generated {results['total_leads']} doctor leads")
            print(f"   System ready for 100-lead campaign")
            return True
        else:
            print(f"\n❌ Still having issues:")
            print(f"   URLs found: {results['statistics']['urls_discovered']}")
            print(f"   Leads generated: {results['total_leads']}")
            return False
            
    except Exception as e:
        print(f"\nERROR: Fixed generator failed: {e}")
        logging.error(f"Fixed generator error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_fixed_doctor_generator()