"""
Enhanced contact information extraction module.
Advanced email validation, phone extraction, and contact verification.
"""

import re
import logging
import requests
import dns.resolver
from typing import List, Dict, Any, Optional, Tuple
from email_validator import validate_email, EmailNotValidError

from .config import config

logger = logging.getLogger(__name__)


class ContactExtractor:
    """Enhanced contact information extraction with validation."""
    
    def __init__(self):
        """Initialize the contact extractor."""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
        
        # Enhanced email patterns
        self.email_patterns = [
            # Standard email pattern
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            # Mailto links
            re.compile(r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', re.IGNORECASE),
            # JavaScript obfuscated emails
            re.compile(r'([A-Za-z0-9._%+-]+)\s*\[\s*at\s*\]\s*([A-Za-z0-9.-]+)\s*\[\s*dot\s*\]\s*([A-Z|a-z]{2,})', re.IGNORECASE),
            # Obfuscated with 'AT' and 'DOT'
            re.compile(r'([A-Za-z0-9._%+-]+)\s+AT\s+([A-Za-z0-9.-]+)\s+DOT\s+([A-Za-z]{2,})', re.IGNORECASE),
        ]
        
        # Phone number patterns (US and international)
        self.phone_patterns = [
            # US phone numbers
            re.compile(r'\b(?:\+1[-.\s]?)?\(?([2-9][0-8][0-9])\)?[-.\s]?([2-9][0-9]{2})[-.\s]?([0-9]{4})\b'),
            # International format
            re.compile(r'\+([1-9]\d{0,3})[-.\s]?(\d{1,14})\b'),
            # Toll-free numbers
            re.compile(r'\b(?:1[-.\s]?)?(?:800|888|877|866|855|844|833|822)[-.\s]?(\d{3})[-.\s]?(\d{4})\b'),
        ]
        
        # Contact-related keywords for context analysis
        self.contact_keywords = [
            'contact', 'email', 'reach', 'write', 'booking', 'guest', 'interview',
            'collaboration', 'partnership', 'business', 'inquiries', 'questions',
            'booking@', 'host@', 'info@', 'hello@', 'contact@', 'business@'
        ]
        
        # Professional email domains (preferred for business contacts)
        self.professional_domains = [
            'gmail.com', 'outlook.com', 'yahoo.com', 'icloud.com', 'protonmail.com',
            'fastmail.com', 'hey.com'  # Plus domain-specific emails are usually more professional
        ]
        
        # Email addresses to skip (common false positives)
        self.skip_emails = [
            'example@example.com', 'test@test.com', 'admin@admin.com',
            'noreply@', 'no-reply@', 'donotreply@', 'support@wordpress',
            'support@google', 'privacy@', 'legal@', 'abuse@'
        ]
    
    def extract_emails(self, content: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Extract and validate email addresses with confidence scoring.
        
        Args:
            content: Text content to extract from
            context: Additional context (e.g., page URL, title)
            
        Returns:
            List of email dictionaries with metadata
        """
        found_emails = []
        seen_emails = set()
        
        # Extract using different patterns
        for pattern in self.email_patterns:
            matches = pattern.findall(content)
            
            for match in matches:
                if isinstance(match, tuple):
                    # Handle obfuscated patterns
                    if len(match) == 3:  # "user AT domain DOT com"
                        email = f"{match[0]}@{match[1]}.{match[2]}"
                    else:
                        email = match[0]  # mailto pattern
                else:
                    email = match
                
                email = email.lower().strip()
                
                # Skip if already processed or invalid
                if email in seen_emails or self._should_skip_email(email):
                    continue
                
                seen_emails.add(email)
                
                # Validate email
                is_valid, validation_info = self._validate_email(email)
                if is_valid:
                    confidence_score = self._calculate_email_confidence(email, content, context)
                    
                    email_info = {
                        'email': email,
                        'confidence': confidence_score,
                        'domain': email.split('@')[1],
                        'validation': validation_info,
                        'context': self._extract_email_context(email, content)
                    }
                    
                    found_emails.append(email_info)
        
        # Sort by confidence score (highest first)
        found_emails.sort(key=lambda x: x['confidence'], reverse=True)
        return found_emails
    
    def extract_phone_numbers(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract and format phone numbers.
        
        Args:
            content: Text content to extract from
            
        Returns:
            List of phone number dictionaries
        """
        found_phones = []
        seen_phones = set()
        
        for pattern in self.phone_patterns:
            matches = pattern.findall(content)
            
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 3:  # US format (area)(exchange)(number)
                        phone = f"({match[0]}) {match[1]}-{match[2]}"
                        formatted = f"+1{match[0]}{match[1]}{match[2]}"
                    elif len(match) == 2:
                        if match[0] == '1':  # US international
                            phone = f"+1 {match[1]}"
                            formatted = f"+1{match[1]}"
                        else:  # Other international
                            phone = f"+{match[0]} {match[1]}"
                            formatted = f"+{match[0]}{match[1]}"
                    else:
                        continue
                else:
                    phone = match
                    formatted = re.sub(r'\D', '', match)
                
                if formatted not in seen_phones:
                    seen_phones.add(formatted)
                    
                    phone_info = {
                        'phone': phone,
                        'formatted': formatted,
                        'type': self._classify_phone_type(formatted),
                        'confidence': 0.8  # Basic confidence for phone numbers
                    }
                    
                    found_phones.append(phone_info)
        
        return found_phones
    
    def extract_addresses(self, content: str) -> List[str]:
        """
        Extract physical addresses from content.
        
        Args:
            content: Text content to extract from
            
        Returns:
            List of potential addresses
        """
        addresses = []
        
        # US address pattern (basic)
        address_pattern = r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Ct|Court|Pl|Place)\.?(?:\s*,?\s*(?:[A-Z][a-z]+\s*){1,3})?(?:\s*,?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)?'
        
        matches = re.findall(address_pattern, content, re.IGNORECASE)
        for match in matches:
            address = match.strip()
            if len(address) > 20:  # Filter out very short matches
                addresses.append(address)
        
        return list(set(addresses))  # Remove duplicates
    
    def classify_contact_type(self, email: str, context: str = "") -> str:
        """
        Classify the type of contact based on email and context.
        
        Args:
            email: Email address
            context: Context where email was found
            
        Returns:
            Contact type classification
        """
        email_lower = email.lower()
        context_lower = context.lower()
        
        # Host/personal email indicators
        if any(indicator in email_lower for indicator in ['host@', 'info@', 'hello@', 'hi@']):
            return 'host'
        
        # Business/booking email indicators  
        if any(indicator in email_lower for indicator in ['booking@', 'business@', 'guest@', 'interview@']):
            return 'booking'
        
        # General contact
        if 'contact@' in email_lower:
            return 'general'
        
        # Check context for clues
        if any(keyword in context_lower for keyword in ['host', 'creator', 'founder']):
            return 'host'
        elif any(keyword in context_lower for keyword in ['booking', 'guest', 'interview']):
            return 'booking'
        
        return 'unknown'
    
    def _validate_email(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate email address and return detailed info."""
        try:
            # Basic format validation
            validated = validate_email(email)
            
            # DNS validation (optional, can be slow)
            domain = email.split('@')[1]
            mx_valid = self._check_mx_record(domain)
            
            validation_info = {
                'format_valid': True,
                'normalized': validated.email,
                'domain_valid': mx_valid,
                'disposable': self._is_disposable_email(domain)
            }
            
            return True, validation_info
            
        except EmailNotValidError as e:
            validation_info = {
                'format_valid': False,
                'error': str(e),
                'domain_valid': False,
                'disposable': False
            }
            return False, validation_info
    
    def _check_mx_record(self, domain: str) -> bool:
        """Check if domain has valid MX record."""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except:
            return False
    
    def _is_disposable_email(self, domain: str) -> bool:
        """Check if email domain is from a disposable email service."""
        disposable_domains = [
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'tempmail.org', 'throwaway.email', 'yopmail.com'
        ]
        return domain.lower() in disposable_domains
    
    def _should_skip_email(self, email: str) -> bool:
        """Check if email should be skipped."""
        email_lower = email.lower()
        
        # Check against skip list
        for skip_pattern in self.skip_emails:
            if skip_pattern in email_lower:
                return True
        
        # Skip obviously fake emails
        if any(fake in email_lower for fake in ['test', 'example', 'dummy', 'fake']):
            return True
        
        # Skip very short emails (likely false positives)
        if len(email) < 6:
            return True
        
        return False
    
    def _calculate_email_confidence(self, email: str, content: str, context: str) -> float:
        """Calculate confidence score for an email address."""
        score = 0.5  # Base score
        
        email_lower = email.lower()
        content_lower = content.lower()
        context_lower = context.lower()
        
        # Higher score for professional domains
        domain = email.split('@')[1]
        if domain in self.professional_domains:
            score += 0.1
        elif not domain.endswith(('.com', '.org', '.net', '.io')):
            score -= 0.1
        
        # Higher score if email appears in contact context
        email_context = content_lower[max(0, content_lower.find(email_lower)-50):content_lower.find(email_lower)+50]
        for keyword in self.contact_keywords:
            if keyword in email_context:
                score += 0.1
                break
        
        # Host/booking email bonus
        if any(indicator in email_lower for indicator in ['host@', 'booking@', 'guest@']):
            score += 0.2
        
        # Generic email penalty
        if any(generic in email_lower for generic in ['noreply', 'admin@', 'support@']):
            score -= 0.3
        
        # Context relevance
        if 'contact' in context_lower or 'about' in context_lower:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _extract_email_context(self, email: str, content: str, window: int = 100) -> str:
        """Extract surrounding context for an email."""
        content_lower = content.lower()
        email_pos = content_lower.find(email.lower())
        
        if email_pos == -1:
            return ""
        
        start = max(0, email_pos - window)
        end = min(len(content), email_pos + len(email) + window)
        
        context = content[start:end].strip()
        # Clean up whitespace
        context = ' '.join(context.split())
        
        return context
    
    def _classify_phone_type(self, formatted_phone: str) -> str:
        """Classify phone number type."""
        if formatted_phone.startswith('+1800') or formatted_phone.startswith('+1888') or \
           formatted_phone.startswith('+1877') or formatted_phone.startswith('+1866'):
            return 'toll_free'
        elif formatted_phone.startswith('+1'):
            return 'us_domestic'
        elif formatted_phone.startswith('+'):
            return 'international'
        else:
            return 'unknown'


class ContactValidator:
    """Validates and scores contact information quality."""
    
    def __init__(self):
        """Initialize contact validator."""
        self.logger = logging.getLogger(__name__)
    
    def validate_contact_info(self, contact_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and score contact information.
        
        Args:
            contact_info: Dictionary of contact information
            
        Returns:
            Validated contact info with scores
        """
        validation_result = {
            'overall_score': 0.0,
            'email_score': 0.0,
            'completeness_score': 0.0,
            'quality_indicators': [],
            'issues': [],
            'recommendations': []
        }
        
        # Score email quality
        if contact_info.get('emails'):
            # Handle both simple list and detailed list formats
            emails = contact_info['emails']
            if emails:
                if isinstance(emails[0], str):
                    # Simple string format - assign default confidence
                    validation_result['email_score'] = 0.7
                    validation_result['quality_indicators'].append('Email addresses found')
                else:
                    # Detailed format with confidence scores
                    best_email = emails[0]
                    validation_result['email_score'] = best_email.get('confidence', 0.0)
                    
                    if best_email['confidence'] > 0.8:
                        validation_result['quality_indicators'].append('High-confidence email found')
                    elif best_email['confidence'] < 0.5:
                        validation_result['issues'].append('Low-confidence email addresses')
        else:
            validation_result['issues'].append('No email addresses found')
            validation_result['recommendations'].append('Check for contact forms or social media')
        
        # Score completeness
        completeness_factors = 0
        total_factors = 5
        
        if contact_info.get('emails'):
            completeness_factors += 1
        if contact_info.get('social_links'):
            completeness_factors += 1  
        if contact_info.get('phone_numbers'):
            completeness_factors += 1
        if contact_info.get('contact_forms'):
            completeness_factors += 1
        if contact_info.get('addresses'):
            completeness_factors += 1
        
        validation_result['completeness_score'] = completeness_factors / total_factors
        
        # Calculate overall score
        validation_result['overall_score'] = (
            validation_result['email_score'] * 0.6 +
            validation_result['completeness_score'] * 0.4
        )
        
        # Add quality indicators
        if len(contact_info.get('emails', [])) > 1:
            validation_result['quality_indicators'].append('Multiple contact options')
        
        if contact_info.get('social_links'):
            validation_result['quality_indicators'].append(f"{len(contact_info['social_links'])} social media profiles")
        
        return validation_result