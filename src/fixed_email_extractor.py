#!/usr/bin/env python3
"""
Fixed Email Extractor - Actually extracts real contact information from websites
Replaces the broken extraction system with working implementation.
"""

import re
import requests
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urljoin, urlparse
import logging
from dataclasses import dataclass, field


@dataclass
class ContactInfo:
    """Structured contact information extracted from a website"""
    url: str
    business_name: str = ""
    emails: List[Dict[str, Any]] = field(default_factory=list)
    phones: List[Dict[str, Any]] = field(default_factory=list)
    names: List[Dict[str, Any]] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    social_profiles: List[str] = field(default_factory=list)
    
    # Quality metrics
    lead_score: float = 0.0
    extraction_confidence: float = 0.0
    is_actionable: bool = False
    
    # Metadata
    page_title: str = ""
    content_length: int = 0
    extraction_time: float = 0.0
    extraction_timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'url': self.url,
            'business_name': self.business_name,
            'emails': self.emails,
            'phones': self.phones,
            'names': self.names,
            'addresses': self.addresses,
            'social_profiles': self.social_profiles,
            'lead_score': self.lead_score,
            'extraction_confidence': self.extraction_confidence,
            'is_actionable': self.is_actionable,
            'page_title': self.page_title,
            'content_length': self.content_length,
            'extraction_time': self.extraction_time,
            'extraction_timestamp': self.extraction_timestamp
        }


class WorkingEmailExtractor:
    """Email extractor that actually works on real websites"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Email patterns - comprehensive collection
        self.email_patterns = [
            # Standard RFC-compliant emails
            re.compile(r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}\b', re.IGNORECASE),
            
            # Common obfuscations
            re.compile(r'\b[a-zA-Z0-9._-]+\s*\[at\]\s*[a-zA-Z0-9.-]+\s*\[dot\]\s*[a-zA-Z]{2,}\b', re.IGNORECASE),
            re.compile(r'\b[a-zA-Z0-9._-]+\s*\(at\)\s*[a-zA-Z0-9.-]+\s*\(dot\)\s*[a-zA-Z]{2,}\b', re.IGNORECASE),
            re.compile(r'\b[a-zA-Z0-9._-]+\s*AT\s*[a-zA-Z0-9.-]+\s*DOT\s*[a-zA-Z]{2,}\b', re.IGNORECASE),
            re.compile(r'\b[a-zA-Z0-9._-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,}\b', re.IGNORECASE),
        ]
        
        # Phone patterns
        self.phone_patterns = [
            # US phone formats
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})\.([0-9]{3})\.([0-9]{4})\b'),
            re.compile(r'\b([0-9]{3})-([0-9]{3})-([0-9]{4})\b'),
            # International formats
            re.compile(r'\b\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}\b'),
        ]
        
        # Name patterns
        self.name_patterns = [
            # Standard name formats
            re.compile(r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b'),
            re.compile(r'\b([A-Z]\. [A-Z][a-z]+)\b'),
            re.compile(r'\b([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)\b'),
        ]
        
        # Business indicators
        self.business_keywords = [
            'contact', 'about', 'team', 'staff', 'management', 'leadership',
            'executives', 'directors', 'partners', 'associates', 'professionals'
        ]
        
        # Spam/invalid email patterns
        self.spam_patterns = [
            re.compile(r'^(noreply|no-reply|donotreply)', re.IGNORECASE),
            re.compile(r'^(test|testing|example|placeholder)', re.IGNORECASE),
            re.compile(r'@(test\.|example\.|localhost)', re.IGNORECASE),
            re.compile(r'^(webmaster|postmaster|admin|administrator)', re.IGNORECASE),
        ]
    
    def extract_contact_info(self, url: str) -> ContactInfo:
        """Extract comprehensive contact information from a website"""
        start_time = time.time()
        contact_info = ContactInfo(url=url)
        
        try:
            # Handle file:// URLs
            if url.startswith('file://'):
                # Remove file:// prefix and handle path
                file_path = url[7:]  # Remove 'file://'
                if file_path.startswith('/') and ':' in file_path:
                    # Windows path like /C:/path
                    file_path = file_path[1:]
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                    soup = BeautifulSoup(text_content, 'html.parser')
                except Exception as e:
                    self.logger.error(f"Failed to read file {file_path}: {e}")
                    return contact_info
            else:
                # Fetch the webpage via HTTP
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                    return contact_info
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = response.text
            
            # Extract basic metadata
            contact_info.page_title = soup.title.get_text(strip=True) if soup.title else ""
            contact_info.content_length = len(text_content)
            
            # Extract business name
            contact_info.business_name = self.extract_business_name(soup, url)
            
            # Extract emails
            contact_info.emails = self.extract_emails(soup, text_content, url)
            
            # Extract phone numbers
            contact_info.phones = self.extract_phone_numbers(text_content)
            
            # Extract names
            contact_info.names = self.extract_names(soup, text_content)
            
            # Extract addresses
            contact_info.addresses = self.extract_addresses(text_content)
            
            # Extract social profiles
            contact_info.social_profiles = self.extract_social_profiles(soup)
            
            # Calculate quality scores
            contact_info.lead_score = self.calculate_lead_score(contact_info)
            contact_info.extraction_confidence = self.calculate_confidence(contact_info)
            contact_info.is_actionable = self.is_actionable_lead(contact_info)
            
            contact_info.extraction_time = time.time() - start_time
            
            self.logger.info(f"Extracted from {url}: {len(contact_info.emails)} emails, {len(contact_info.phones)} phones, {len(contact_info.names)} names")
            
        except Exception as e:
            self.logger.error(f"Error extracting from {url}: {e}")
            contact_info.extraction_time = time.time() - start_time
        
        return contact_info
    
    def extract_business_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract business name from webpage"""
        candidates = []
        
        # Method 1: Page title
        if soup.title:
            title = soup.title.get_text(strip=True)
            # Clean up common title patterns
            title = re.sub(r'\s*[|-].*$', '', title)
            title = re.sub(r'\s*-\s*(Home|Contact|About).*$', '', title, re.IGNORECASE)
            if title and len(title) < 100 and not re.match(r'^(Contact|About|Home)', title, re.IGNORECASE):
                candidates.append((title, 0.8))
        
        # Method 2: H1 tags
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags[:2]:
            text = h1.get_text(strip=True)
            if text and len(text) < 80 and not re.match(r'^(Contact|About|Welcome)', text, re.IGNORECASE):
                candidates.append((text, 0.7))
        
        # Method 3: Logo alt text
        logo_imgs = soup.find_all('img', alt=re.compile(r'logo', re.IGNORECASE))
        for img in logo_imgs[:2]:
            alt_text = img.get('alt', '').strip()
            if alt_text and len(alt_text) < 60 and 'logo' not in alt_text.lower():
                candidates.append((alt_text, 0.6))
        
        # Method 4: Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc = meta_desc.get('content', '')
            first_sentence = desc.split('.')[0].strip()
            if first_sentence and len(first_sentence) < 100:
                # Extract potential business name from start
                words = first_sentence.split()[:5]
                if len(words) >= 2:
                    potential_name = ' '.join(words)
                    candidates.append((potential_name, 0.5))
        
        # Method 5: Extract from domain
        domain = urlparse(url).netloc.replace('www.', '')
        domain_name = domain.split('.')[0].replace('-', ' ').title()
        candidates.append((domain_name, 0.3))
        
        # Choose best candidate
        if candidates:
            # Prefer candidates with business keywords
            business_keywords = ['practice', 'clinic', 'medical', 'law', 'firm', 'group', 'associates', 'partners', 'company', 'corp', 'llc']
            for name, score in candidates:
                if any(keyword in name.lower() for keyword in business_keywords):
                    return name
            
            # Return highest scoring candidate
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return "Unknown Business"
    
    def extract_emails(self, soup: BeautifulSoup, text_content: str, url: str) -> List[Dict[str, Any]]:
        """Extract email addresses with context and scoring"""
        found_emails = []
        
        # Extract from mailto links first (highest confidence)
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            if href.lower().startswith('mailto:'):
                email = href[7:].split('?')[0].split('#')[0].strip()
                if self.is_valid_email(email):
                    link_text = link.get_text(strip=True)
                    found_emails.append({
                        'email': email.lower(),
                        'source': 'mailto_link',
                        'context': link_text,
                        'confidence': self.score_email_quality(email) + 0.2  # Bonus for mailto
                    })
        
        # Extract from text content
        for pattern in self.email_patterns:
            matches = pattern.findall(text_content)
            for match in matches:
                email = match if isinstance(match, str) else match[0]
                
                # Clean and normalize
                email = self.clean_email(email)
                
                if self.is_valid_email(email):
                    context = self.get_email_context(text_content, email)
                    found_emails.append({
                        'email': email.lower(),
                        'source': 'text_content',
                        'context': context,
                        'confidence': self.score_email_quality(email)
                    })
        
        # Remove duplicates and filter quality
        unique_emails = {}
        for email_data in found_emails:
            email = email_data['email']
            if email not in unique_emails or email_data['confidence'] > unique_emails[email]['confidence']:
                if not self.is_spam_email(email):
                    unique_emails[email] = email_data
        
        # Sort by confidence and return top results
        result = sorted(unique_emails.values(), key=lambda x: x['confidence'], reverse=True)
        return result[:10]  # Top 10 emails
    
    def extract_phone_numbers(self, text_content: str) -> List[Dict[str, Any]]:
        """Extract phone numbers with context"""
        found_phones = []
        
        for pattern in self.phone_patterns:
            matches = pattern.finditer(text_content)
            for match in matches:
                if len(match.groups()) >= 3:
                    # Format as (XXX) XXX-XXXX
                    area_code, exchange, number = match.groups()[:3]
                    phone = f"({area_code}) {exchange}-{number}"
                    
                    # Get context
                    start = max(0, match.start() - 30)
                    end = min(len(text_content), match.end() + 30)
                    context = text_content[start:end].strip()
                    
                    # Score based on context
                    confidence = 0.7
                    context_lower = context.lower()
                    if any(keyword in context_lower for keyword in ['phone', 'call', 'contact', 'office', 'tel']):
                        confidence += 0.2
                    if any(keyword in context_lower for keyword in ['fax', 'toll-free', '800-', '888-', '877-']):
                        confidence += 0.1
                    
                    found_phones.append({
                        'phone': phone,
                        'context': context,
                        'confidence': confidence,
                        'type': self.classify_phone_type(context)
                    })
        
        # Remove duplicates and sort by confidence
        unique_phones = {}
        for phone_data in found_phones:
            phone = phone_data['phone']
            if phone not in unique_phones or phone_data['confidence'] > unique_phones[phone]['confidence']:
                unique_phones[phone] = phone_data
        
        return sorted(unique_phones.values(), key=lambda x: x['confidence'], reverse=True)[:5]
    
    def extract_names(self, soup: BeautifulSoup, text_content: str) -> List[Dict[str, Any]]:
        """Extract person names from content"""
        found_names = []
        
        # Look for names in specific sections
        name_sections = soup.find_all(['div', 'section'], class_=re.compile(r'(staff|team|about|bio|management|leadership)', re.I))
        
        for section in name_sections:
            section_text = section.get_text()
            for pattern in self.name_patterns:
                matches = pattern.findall(section_text)
                for name in matches:
                    if self.is_valid_name(name):
                        found_names.append({
                            'name': name,
                            'context': 'staff_section',
                            'confidence': 0.8
                        })
        
        # Look for names near contact information
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        email_matches = email_pattern.finditer(text_content)
        
        for email_match in email_matches:
            # Look for names within 100 characters of email
            start = max(0, email_match.start() - 100)
            end = min(len(text_content), email_match.end() + 100)
            context_text = text_content[start:end]
            
            for pattern in self.name_patterns:
                name_matches = pattern.findall(context_text)
                for name in name_matches:
                    if self.is_valid_name(name):
                        found_names.append({
                            'name': name,
                            'context': 'near_email',
                            'confidence': 0.9
                        })
        
        # Remove duplicates and filter
        unique_names = {}
        for name_data in found_names:
            name = name_data['name']
            if name not in unique_names or name_data['confidence'] > unique_names[name]['confidence']:
                unique_names[name] = name_data
        
        return sorted(unique_names.values(), key=lambda x: x['confidence'], reverse=True)[:8]
    
    def extract_addresses(self, text_content: str) -> List[str]:
        """Extract physical addresses"""
        # US address pattern
        address_pattern = re.compile(
            r'\b\d+[\w\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Circle|Cir|Court|Ct|Plaza|Pl)\b[,\s]+[\w\s,]+\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b\s+\d{5}(?:-\d{4})?\b',
            re.IGNORECASE
        )
        
        matches = address_pattern.findall(text_content)
        return list(set(matches))[:3]  # Return unique addresses, max 3
    
    def extract_social_profiles(self, soup: BeautifulSoup) -> List[str]:
        """Extract social media profile links"""
        social_profiles = []
        social_domains = [
            'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
            'youtube.com', 'tiktok.com', 'pinterest.com'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            for domain in social_domains:
                if domain in href and href.startswith('http'):
                    social_profiles.append(href)
                    break
        
        return list(set(social_profiles))[:5]  # Remove duplicates, max 5
    
    def clean_email(self, email: str) -> str:
        """Clean and normalize email address"""
        if not email:
            return ""
        
        # Handle obfuscated emails
        email = re.sub(r'\s*\[at\]\s*', '@', email, flags=re.IGNORECASE)
        email = re.sub(r'\s*\(at\)\s*', '@', email, flags=re.IGNORECASE)
        email = re.sub(r'\s*AT\s*', '@', email, flags=re.IGNORECASE)
        email = re.sub(r'\s+at\s+', '@', email, flags=re.IGNORECASE)
        email = re.sub(r'\s*\[dot\]\s*', '.', email, flags=re.IGNORECASE)
        email = re.sub(r'\s*\(dot\)\s*', '.', email, flags=re.IGNORECASE)
        email = re.sub(r'\s*DOT\s*', '.', email, flags=re.IGNORECASE)
        email = re.sub(r'\s+dot\s+', '.', email, flags=re.IGNORECASE)
        
        return email.strip().lower()
    
    def is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        if not email or '@' not in email:
            return False
        
        # Basic format check
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain:
            return False
        
        # Domain must have a dot
        if '.' not in domain:
            return False
        
        # Must end with valid TLD
        if not re.match(r'.*\.[a-zA-Z]{2,}$', domain):
            return False
        
        return True
    
    def is_spam_email(self, email: str) -> bool:
        """Check if email is spam/invalid"""
        for pattern in self.spam_patterns:
            if pattern.search(email):
                return True
        return False
    
    def is_valid_name(self, name: str) -> bool:
        """Validate if string is likely a real person name"""
        if not name or len(name) < 4:
            return False
        
        # Skip common false positives
        false_positives = [
            'about us', 'contact us', 'our team', 'new york', 'los angeles',
            'united states', 'terms of', 'privacy policy', 'lorem ipsum'
        ]
        
        name_lower = name.lower()
        if any(fp in name_lower for fp in false_positives):
            return False
        
        # Must have at least 2 words
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word should start with capital letter
        if not all(word[0].isupper() for word in words):
            return False
        
        return True
    
    def get_email_context(self, text: str, email: str, window: int = 50) -> str:
        """Get context around an email in text"""
        email_pos = text.lower().find(email.lower())
        if email_pos >= 0:
            start = max(0, email_pos - window)
            end = min(len(text), email_pos + len(email) + window)
            return text[start:end].strip()
        return ""
    
    def classify_phone_type(self, context: str) -> str:
        """Classify phone number type based on context"""
        context_lower = context.lower()
        if 'fax' in context_lower:
            return 'fax'
        elif any(keyword in context_lower for keyword in ['toll', '800', '888', '877', '866']):
            return 'toll_free'
        elif any(keyword in context_lower for keyword in ['mobile', 'cell', 'cellular']):
            return 'mobile'
        else:
            return 'office'
    
    def score_email_quality(self, email: str) -> float:
        """Score email quality for business use"""
        score = 0.5  # Base score
        
        email_lower = email.lower()
        local_part, domain = email_lower.split('@', 1)
        
        # High-quality patterns
        if any(pattern in email_lower for pattern in [
            'ceo@', 'president@', 'director@', 'manager@', 'owner@',
            'contact@', 'info@', 'business@', 'sales@', 'admin@'
        ]):
            score += 0.3
        
        # firstname.lastname pattern
        if '.' in local_part and len(local_part.split('.')) == 2:
            parts = local_part.split('.')
            if all(part.isalpha() and len(part) > 1 for part in parts):
                score += 0.2
        
        # Domain assessment
        if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            score -= 0.1  # Personal domains get slight penalty
        elif any(indicator in domain for indicator in ['corp', 'company', 'firm', 'group']):
            score += 0.1  # Business domains get bonus
        
        # Length bonus for reasonable emails
        if 6 <= len(local_part) <= 20:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def calculate_lead_score(self, contact_info: ContactInfo) -> float:
        """Calculate overall lead quality score"""
        score = 0.0
        
        # Email quality (40% of score)
        if contact_info.emails:
            best_email = max(contact_info.emails, key=lambda x: x['confidence'])
            score += best_email['confidence'] * 0.4
        
        # Contact completeness (60% of score)
        if contact_info.phones:
            score += 0.2
        if contact_info.names:
            score += 0.15
        if contact_info.addresses:
            score += 0.1
        if contact_info.business_name and contact_info.business_name != 'Unknown Business':
            score += 0.15
        
        return min(1.0, score)
    
    def calculate_confidence(self, contact_info: ContactInfo) -> float:
        """Calculate extraction confidence"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on data richness
        if contact_info.emails:
            confidence += 0.3
        if contact_info.phones:
            confidence += 0.1
        if contact_info.names:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def is_actionable_lead(self, contact_info: ContactInfo) -> bool:
        """Determine if lead is actionable for outreach"""
        # Must have at least one email
        if not contact_info.emails:
            return False
        
        # Must have reasonable lead score
        if contact_info.lead_score < 0.4:
            return False
        
        # Must have identifiable business
        if not contact_info.business_name or contact_info.business_name == 'Unknown Business':
            return False
        
        return True


def test_working_extractor():
    """Test the working email extractor"""
    print("Testing Working Email Extractor")
    print("=" * 40)
    
    extractor = WorkingEmailExtractor()
    
    # Test URLs with known contact info
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://www.python.org/community/",  # Should have some contact info
        "https://docs.python.org/",  # Might have some info
    ]
    
    results = []
    
    for i, url in enumerate(test_urls):
        print(f"\nTesting URL {i+1}: {url}")
        print("-" * 30)
        
        contact_info = extractor.extract_contact_info(url)
        results.append(contact_info)
        
        print(f"Business Name: {contact_info.business_name}")
        print(f"Emails Found: {len(contact_info.emails)}")
        for email in contact_info.emails[:3]:
            print(f"  - {email['email']} (confidence: {email['confidence']:.2f})")
        
        print(f"Phones Found: {len(contact_info.phones)}")
        for phone in contact_info.phones[:2]:
            print(f"  - {phone['phone']} (confidence: {phone['confidence']:.2f})")
        
        print(f"Names Found: {len(contact_info.names)}")
        for name in contact_info.names[:2]:
            print(f"  - {name['name']} (confidence: {name['confidence']:.2f})")
        
        print(f"Lead Score: {contact_info.lead_score:.2f}")
        print(f"Is Actionable: {contact_info.is_actionable}")
        print(f"Extraction Time: {contact_info.extraction_time:.2f}s")
    
    # Summary
    print(f"\n{'='*40}")
    print("EXTRACTION TEST SUMMARY")
    print(f"{'='*40}")
    
    total_emails = sum(len(r.emails) for r in results)
    total_phones = sum(len(r.phones) for r in results)
    total_names = sum(len(r.names) for r in results)
    actionable_leads = sum(1 for r in results if r.is_actionable)
    
    print(f"URLs Tested: {len(results)}")
    print(f"Total Emails: {total_emails}")
    print(f"Total Phones: {total_phones}")
    print(f"Total Names: {total_names}")
    print(f"Actionable Leads: {actionable_leads}")
    print(f"Success Rate: {actionable_leads/len(results)*100:.1f}%")
    
    if total_emails > 0:
        print("\nSUCCESS: Email extractor is working!")
    else:
        print("\nWARNING: No emails extracted - may need tuning")
    
    return results


if __name__ == "__main__":
    test_working_extractor()