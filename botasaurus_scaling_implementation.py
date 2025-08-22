#!/usr/bin/env python3
"""
Botasaurus Scaling Implementation for 1000 Emails/Day
Optimized lead generation with parallel processing and anti-detection
"""

from botasaurus import *
from botasaurus.request import request, Request
import time
import random
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

# Enhanced configuration for scaling
SCALING_CONFIG = {
    "max_workers": 10,  # Concurrent browser instances
    "request_delay": (2, 5),  # Random delay between requests
    "timeout": 30,
    "retries": 3,
    "email_success_target": 0.65,  # 65% email success rate target
    "daily_email_target": 1000,
    "anti_detection": True,
    "proxy_rotation": True
}

# Medical site targeting for higher success rates
MEDICAL_SITE_PATTERNS = [
    "doctor", "physician", "medical", "clinic", "hospital", 
    "healthcare", "practice", "specialist", "surgery", "care"
]

# Enhanced email extraction patterns for medical sites
MEDICAL_EMAIL_PATTERNS = [
    'a[href^="mailto:"]',
    '[data-email]', '[data-contact-email]',
    '.contact-email', '.email-address', '.email',
    '.doctor-email', '.physician-email',
    '.practice-contact', '.office-email',
    '.appointment-email', '.booking-email',
    '.admin-email', '.info-email',
    'input[name*="email"]', 'input[id*="email"]',
    # Medical-specific patterns
    '.provider-contact', '.staff-email',
    '.reception-email', '.schedule-email'
]

# Contact page discovery patterns
CONTACT_PAGE_URLS = [
    '/contact', '/contact-us', '/contact-info',
    '/appointments', '/schedule', '/booking',
    '/staff', '/providers', '/team', '/doctors',
    '/about', '/about-us', '/office-info',
    '/location', '/locations', '/office',
    '/patient-info', '/new-patients'
]

@request(
    parallel=True,
    max_workers=SCALING_CONFIG["max_workers"],
    run_async=True,
    proxy=SCALING_CONFIG["proxy_rotation"],
    block_detection=SCALING_CONFIG["anti_detection"],
    use_stealth=True,
    cache_browser=True,
    user_agent_rotation=True,
    wait_for_complete_page_load=True,
    timeout=SCALING_CONFIG["timeout"],
    retry=SCALING_CONFIG["retries"]
)
def extract_medical_contacts_parallel(request: Request, url: str) -> Dict[str, Any]:
    """
    Optimized parallel medical contact extraction using Botasaurus
    Designed for high-volume processing with anti-detection
    """
    
    try:
        # Add random delay for anti-detection
        delay = random.uniform(*SCALING_CONFIG["request_delay"])
        time.sleep(delay)
        
        # Navigate to the URL
        request.get(url)
        
        # Enhanced contact extraction
        contact_data = {
            "url": url,
            "business_name": "",
            "emails": [],
            "phones": [],
            "names": [],
            "addresses": [],
            "social_profiles": [],
            "extraction_timestamp": datetime.now().isoformat(),
            "processing_time": 0
        }
        
        start_time = time.time()
        
        # Extract business name from multiple sources
        business_name_selectors = [
            'title', 'h1', '.practice-name', '.clinic-name',
            '.business-name', '.company-name', '[itemprop="name"]',
            '.header-title', '.main-title', '.site-title'
        ]
        
        for selector in business_name_selectors:
            try:
                element = request.select(selector)
                if element:
                    contact_data["business_name"] = element.text.strip()
                    break
            except:
                continue
        
        # Enhanced email extraction
        emails_found = set()
        
        # Method 1: Direct email pattern matching
        for pattern in MEDICAL_EMAIL_PATTERNS:
            try:
                elements = request.select_all(pattern)
                for element in elements:
                    # Extract from href attribute
                    href = element.get_attribute('href')
                    if href and href.startswith('mailto:'):
                        email = href.replace('mailto:', '').split('?')[0]
                        emails_found.add(email.lower())
                    
                    # Extract from text content
                    text = element.text
                    if '@' in text and '.' in text:
                        # Basic email validation
                        import re
                        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                        if email_match:
                            emails_found.add(email_match.group().lower())
            except:
                continue
        
        # Method 2: Contact page discovery and extraction
        for contact_path in CONTACT_PAGE_URLS:
            try:
                contact_url = request.current_url.rstrip('/') + contact_path
                request.get(contact_url)
                
                # Extract emails from contact page
                page_text = request.page_source
                import re
                contact_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', page_text)
                for email in contact_emails:
                    emails_found.add(email.lower())
                
                # Limit contact page crawling for performance
                if len(emails_found) >= 3:
                    break
                    
            except:
                continue
        
        # Process found emails
        for email in emails_found:
            # Filter out common non-business emails
            if not any(exclude in email for exclude in ['noreply', 'no-reply', 'donotreply', 'newsletter']):
                contact_data["emails"].append({
                    "email": email,
                    "confidence": calculate_email_confidence(email),
                    "type": classify_email_type(email)
                })
        
        # Extract phone numbers
        phone_patterns = [
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # (123) 456-7890
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',  # 123-456-7890 or 123.456.7890
            r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # +1-123-456-7890
            r'\d{3}\s*\d{3}\s*\d{4}'  # 1234567890
        ]
        
        page_text = request.page_source
        import re
        for pattern in phone_patterns:
            phones = re.findall(pattern, page_text)
            for phone in phones:
                # Clean and validate phone number
                cleaned_phone = re.sub(r'[^\d+()-]', '', phone)
                if len(cleaned_phone.replace('+', '').replace('(', '').replace(')', '').replace('-', '')) >= 10:
                    contact_data["phones"].append({
                        "phone": phone,
                        "type": "business",
                        "confidence": 0.8
                    })
        
        # Calculate processing metrics
        contact_data["processing_time"] = time.time() - start_time
        contact_data["email_count"] = len(contact_data["emails"])
        contact_data["phone_count"] = len(contact_data["phones"])
        contact_data["success"] = len(contact_data["emails"]) > 0 or len(contact_data["phones"]) > 0
        
        return contact_data
        
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "success": False,
            "extraction_timestamp": datetime.now().isoformat()
        }

def calculate_email_confidence(email: str) -> float:
    """Calculate confidence score for extracted email"""
    confidence = 0.5  # Base confidence
    
    # Domain-based scoring
    if any(domain in email for domain in ['.org', '.edu', '.gov']):
        confidence += 0.2
    elif any(domain in email for domain in ['.com', '.net']):
        confidence += 0.1
    
    # Email pattern scoring
    if any(pattern in email for pattern in ['info@', 'contact@', 'admin@']):
        confidence += 0.1
    elif any(pattern in email for pattern in ['appointment@', 'schedule@', 'office@']):
        confidence += 0.2
    elif '@' in email and '.' in email.split('@')[1]:
        confidence += 0.1
    
    return min(confidence, 1.0)

def classify_email_type(email: str) -> str:
    """Classify email type for medical practices"""
    if any(pattern in email for pattern in ['appointment', 'schedule', 'booking']):
        return 'appointment'
    elif any(pattern in email for pattern in ['info', 'contact', 'admin']):
        return 'general'
    elif any(pattern in email for pattern in ['doctor', 'dr.', 'physician']):
        return 'provider'
    else:
        return 'business'

class ScalableLeadGenerator:
    """High-performance lead generator designed for 1000+ emails/day"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or SCALING_CONFIG
        self.performance_metrics = {
            "urls_processed": 0,
            "emails_extracted": 0,
            "total_processing_time": 0,
            "success_rate": 0.0,
            "start_time": None
        }
    
    def generate_medical_leads(self, urls: List[str], max_concurrent: int = None) -> List[Dict[str, Any]]:
        """
        Generate medical leads using parallel Botasaurus processing
        Optimized for high-volume extraction
        """
        
        max_concurrent = max_concurrent or self.config["max_workers"]
        self.performance_metrics["start_time"] = time.time()
        
        print(f"🚀 Starting parallel extraction with {max_concurrent} workers")
        print(f"📊 Processing {len(urls)} medical websites")
        
        # Execute parallel extraction
        results = extract_medical_contacts_parallel(urls)
        
        # Process and validate results
        validated_leads = []
        total_emails = 0
        
        for result in results:
            if result.get("success", False):
                self.performance_metrics["urls_processed"] += 1
                
                # Count emails found
                email_count = len(result.get("emails", []))
                total_emails += email_count
                
                # Only include leads with contact information
                if email_count > 0 or len(result.get("phones", [])) > 0:
                    validated_leads.append(result)
        
        # Update performance metrics
        self.performance_metrics["emails_extracted"] = total_emails
        self.performance_metrics["total_processing_time"] = time.time() - self.performance_metrics["start_time"]
        self.performance_metrics["success_rate"] = total_emails / len(urls) if urls else 0
        
        # Performance reporting
        self.report_performance()
        
        return validated_leads
    
    def report_performance(self):
        """Report performance metrics for optimization"""
        metrics = self.performance_metrics
        
        processing_time = metrics["total_processing_time"]
        urls_per_second = metrics["urls_processed"] / processing_time if processing_time > 0 else 0
        emails_per_hour = (metrics["emails_extracted"] / processing_time) * 3600 if processing_time > 0 else 0
        
        print(f"\n📈 PERFORMANCE REPORT:")
        print(f"   Processing Time: {processing_time:.1f} seconds")
        print(f"   URLs Processed: {metrics['urls_processed']}")
        print(f"   Emails Extracted: {metrics['emails_extracted']}")
        print(f"   Success Rate: {metrics['success_rate']:.1%}")
        print(f"   URLs/Second: {urls_per_second:.2f}")
        print(f"   Projected Emails/Hour: {emails_per_hour:.0f}")
        print(f"   Projected Emails/Day: {emails_per_hour * 16:.0f}")  # 16 hour operation
        
        # Scaling assessment
        target_emails_day = self.config["daily_email_target"]
        projected_daily = emails_per_hour * 16
        
        if projected_daily >= target_emails_day:
            print(f"   ✅ TARGET ACHIEVED: {projected_daily:.0f} ≥ {target_emails_day}")
        else:
            scale_factor = target_emails_day / projected_daily if projected_daily > 0 else float('inf')
            print(f"   ⚠️  SCALING NEEDED: {scale_factor:.1f}x improvement required")
    
    def optimize_for_medical_sites(self, search_query: str) -> List[str]:
        """
        Generate optimized URL list for medical site targeting
        Focus on high-conversion medical directories and practices
        """
        
        # Medical directory URLs with high email success rates
        medical_directories = [
            "https://www.healthgrades.com",
            "https://www.zocdoc.com", 
            "https://www.vitals.com",
            "https://www.webmd.com/find-a-doctor",
            "https://www.medicare.gov/care-compare/",
            "https://www.yelp.com/c/miami/doctors",
            "https://www.yellowpages.com/search?search_terms=doctors",
            "https://www.superpages.com/search/doctors"
        ]
        
        # Known high-conversion medical practice websites
        practice_websites = [
            "https://www.clevelandclinic.org",
            "https://www.mayoclinic.org", 
            "https://www.johnshopkins.org",
            "https://www.cedars-sinai.org",
            "https://www.mountsinai.org",
            "https://www.memorialsloan.org",
            "https://www.houstonmethodist.org",
            "https://www.scripps.org"
        ]
        
        # Combine and prioritize based on geographic relevance
        if "miami" in search_query.lower() or "florida" in search_query.lower():
            florida_practices = [
                "https://www.baptisthealth.net",
                "https://www.umiamihealth.org",
                "https://www.mhs.net",
                "https://www.browardhealth.org",
                "https://www.memorialhealthcare.org"
            ]
            return florida_practices + practice_websites + medical_directories
        
        return practice_websites + medical_directories

# Example usage for 1000 emails/day scaling
if __name__ == "__main__":
    print("🏥 Scalable Medical Lead Generator - Botasaurus Powered")
    print("Target: 1000+ emails/day with parallel processing")
    
    # Initialize generator
    generator = ScalableLeadGenerator()
    
    # Generate target URLs
    medical_urls = generator.optimize_for_medical_sites("doctor Miami Florida")
    
    # Run parallel extraction
    leads = generator.generate_medical_leads(medical_urls[:20])  # Test with 20 URLs
    
    print(f"\n✅ Extraction complete: {len(leads)} leads generated")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scalable_medical_leads_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2)
    
    print(f"📁 Results saved to: {output_file}")