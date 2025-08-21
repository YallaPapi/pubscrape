"""
Email Extractor Agent

Agency Swarm agent for extracting and scoring business email addresses from crawled 
website content. Integrates with site crawler results and provides intelligent 
email discovery with context analysis and quality scoring.
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from urllib.parse import urljoin, urlparse
import email.utils
from email_validator import validate_email, EmailNotValidError

try:
    from agency_swarm import Agent
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    # Create mock classes for testing
    class Agent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field
from bs4 import BeautifulSoup


class EmailSource(Enum):
    """Source type for discovered emails"""
    MAILTO_LINK = "mailto_link"
    VISIBLE_TEXT = "visible_text"
    HTML_ATTRIBUTE = "html_attribute"
    OBFUSCATED_TEXT = "obfuscated_text"
    CONTACT_FORM = "contact_form"
    FOOTER = "footer"
    HEADER = "header"
    META_TAG = "meta_tag"


class EmailQuality(Enum):
    """Quality levels for email addresses"""
    HIGH = "high"        # Clear business contact emails
    MEDIUM = "medium"    # Likely business emails
    LOW = "low"          # Generic or uncertain emails
    SPAM = "spam"        # Likely spam or irrelevant


@dataclass
class EmailCandidate:
    """Represents a discovered email candidate with context"""
    email: str
    source: EmailSource
    confidence_score: float = 0.0
    quality: EmailQuality = EmailQuality.LOW
    page_url: str = ""
    context_text: str = ""
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    surrounding_text: str = ""
    extraction_method: str = ""
    validation_status: str = "unknown"
    
    # Contact enrichment data
    associated_name: Optional[str] = None
    associated_title: Optional[str] = None
    associated_department: Optional[str] = None
    phone_number: Optional[str] = None
    
    # Metadata
    discovery_timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Post-initialization processing"""
        self.email = self._normalize_email(self.email)
    
    def _normalize_email(self, email: str) -> str:
        """Normalize email address"""
        if not email:
            return ""
        
        # Remove mailto: prefix if present
        if email.startswith('mailto:'):
            email = email[7:]
        
        # Remove query parameters and fragments
        if '?' in email:
            email = email.split('?')[0]
        if '#' in email:
            email = email.split('#')[0]
        
        # Strip whitespace and convert to lowercase
        return email.strip().lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class EmailExtractionResult:
    """Result of email extraction from a page"""
    page_url: str
    candidates: List[EmailCandidate] = field(default_factory=list)
    high_quality_emails: List[str] = field(default_factory=list)
    business_emails: List[str] = field(default_factory=list)
    total_found: int = 0
    extraction_time_ms: Optional[float] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        """Update computed fields"""
        self.total_found = len(self.candidates)
        self.high_quality_emails = [
            c.email for c in self.candidates 
            if c.quality in [EmailQuality.HIGH, EmailQuality.MEDIUM]
        ]
        self.business_emails = [
            c.email for c in self.candidates 
            if c.quality == EmailQuality.HIGH
        ]


class EmailPatternDetector:
    """
    Advanced email pattern detection supporting multiple formats and obfuscations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Initialize regex patterns
        self._initialize_patterns()
        
        # Business email indicators
        self.business_keywords = {
            'high_value': [
                'ceo', 'founder', 'president', 'director', 'manager', 'lead',
                'head', 'chief', 'owner', 'partner', 'principal'
            ],
            'business_functions': [
                'contact', 'info', 'business', 'sales', 'marketing', 'pr',
                'press', 'media', 'collaboration', 'partnerships', 'booking',
                'inquiries', 'support', 'customer', 'service'
            ],
            'departments': [
                'hr', 'human resources', 'finance', 'accounting', 'legal',
                'operations', 'admin', 'administration', 'it', 'tech'
            ]
        }
        
        # Generic/low-value email patterns to downgrade
        self.generic_patterns = [
            r'^(no-?reply|noreply)@',
            r'^(test|testing|example)@',
            r'^(admin|administrator)@.*\.(local|test|dev)',
            r'^(webmaster|postmaster)@',
            r'@(example\.|test\.|localhost)'
        ]
        
        self.logger.info("EmailPatternDetector initialized with RFC-5322 compliant patterns")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailPatternDetector")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_patterns(self):
        """Initialize email detection patterns"""
        # RFC 5322 compliant email regex (simplified but comprehensive)
        self.rfc_email_pattern = re.compile(
            r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}\b',
            re.IGNORECASE
        )
        
        # Obfuscated email patterns
        self.obfuscated_patterns = [
            # [at] and [dot] obfuscations
            re.compile(r'\b[a-zA-Z0-9._-]+\s*\[at\]\s*[a-zA-Z0-9.-]+\s*\[dot\]\s*[a-zA-Z]{2,}\b', re.IGNORECASE),
            re.compile(r'\b[a-zA-Z0-9._-]+\s*\(at\)\s*[a-zA-Z0-9.-]+\s*\(dot\)\s*[a-zA-Z]{2,}\b', re.IGNORECASE),
            
            # AT and DOT obfuscations
            re.compile(r'\b[a-zA-Z0-9._-]+\s*AT\s*[a-zA-Z0-9.-]+\s*DOT\s*[a-zA-Z]{2,}\b', re.IGNORECASE),
            
            # Spaced obfuscations
            re.compile(r'\b[a-zA-Z0-9._-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,}\b', re.IGNORECASE),
            
            # Character replacement obfuscations
            re.compile(r'\b[a-zA-Z0-9._-]+\s*\*\s*[a-zA-Z0-9.-]+\s*\*\s*[a-zA-Z]{2,}\b'),
            re.compile(r'\b[a-zA-Z0-9._-]+\s*#\s*[a-zA-Z0-9.-]+\s*#\s*[a-zA-Z]{2,}\b'),
        ]
        
        # JavaScript/HTML obfuscation patterns
        self.html_patterns = [
            # HTML entities
            re.compile(r'(?:&#64;|&commat;|&#x40;)', re.IGNORECASE),
            re.compile(r'(?:&#46;|&period;|&#x2E;)', re.IGNORECASE),
        ]
    
    def extract_emails_from_text(self, text: str, context: str = "") -> List[Tuple[str, EmailSource, str]]:
        """
        Extract emails from text using multiple detection methods.
        
        Args:
            text: Text content to scan
            context: Additional context about the text source
            
        Returns:
            List of tuples (email, source_type, extraction_method)
        """
        if not text:
            return []
        
        found_emails = []
        
        # 1. Standard RFC-compliant email detection
        standard_emails = self.rfc_email_pattern.findall(text)
        for email in standard_emails:
            found_emails.append((email, EmailSource.VISIBLE_TEXT, "rfc_5322_regex"))
        
        # 2. Obfuscated email detection
        for i, pattern in enumerate(self.obfuscated_patterns):
            matches = pattern.findall(text)
            for match in matches:
                deobfuscated = self._deobfuscate_email(match)
                if deobfuscated:
                    found_emails.append((deobfuscated, EmailSource.OBFUSCATED_TEXT, f"obfuscation_pattern_{i}"))
        
        # 3. Context-specific extraction
        if 'footer' in context.lower():
            source_type = EmailSource.FOOTER
        elif 'header' in context.lower():
            source_type = EmailSource.HEADER
        else:
            source_type = EmailSource.VISIBLE_TEXT
        
        # Update source types for context-specific emails
        contextual_emails = []
        for email, orig_source, method in found_emails:
            if orig_source == EmailSource.VISIBLE_TEXT:
                contextual_emails.append((email, source_type, method))
            else:
                contextual_emails.append((email, orig_source, method))
        
        return contextual_emails
    
    def _deobfuscate_email(self, obfuscated: str) -> Optional[str]:
        """Convert obfuscated email to standard format"""
        if not obfuscated:
            return None
        
        # Common obfuscation replacements
        replacements = [
            (r'\s*\[at\]\s*', '@'),
            (r'\s*\(at\)\s*', '@'),
            (r'\s*AT\s*', '@'),
            (r'\s+at\s+', '@'),
            (r'\s*\[dot\]\s*', '.'),
            (r'\s*\(dot\)\s*', '.'),
            (r'\s*DOT\s*', '.'),
            (r'\s+dot\s+', '.'),
            (r'\s*\*\s*', '@'),  # First * becomes @
            (r'\s*#\s*', '@'),   # First # becomes @
        ]
        
        result = obfuscated
        
        # Apply replacements in order
        for pattern, replacement in replacements:
            if '@' not in result:  # Only replace @ symbols once
                result = re.sub(pattern, replacement, result, count=1)
            else:
                # After @ is found, replace remaining obfuscations with dots
                if replacement == '@':
                    replacement = '.'
                result = re.sub(pattern, replacement, result)
        
        # Validate the result looks like an email
        if '@' in result and '.' in result:
            return result.strip()
        
        return None
    
    def extract_from_html(self, html_content: str, base_url: str = "") -> List[EmailCandidate]:
        """
        Extract emails from HTML content with enhanced context analysis.
        
        Args:
            html_content: HTML content to scan
            base_url: Base URL for context
            
        Returns:
            List of EmailCandidate objects
        """
        if not html_content:
            return []
        
        candidates = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Extract from mailto links
            mailto_candidates = self._extract_from_mailto_links(soup, base_url)
            candidates.extend(mailto_candidates)
            
            # 2. Extract from visible text with context
            text_candidates = self._extract_from_visible_text(soup, base_url)
            candidates.extend(text_candidates)
            
            # 3. Extract from HTML attributes
            attr_candidates = self._extract_from_attributes(soup, base_url)
            candidates.extend(attr_candidates)
            
            # 4. Extract from meta tags
            meta_candidates = self._extract_from_meta_tags(soup, base_url)
            candidates.extend(meta_candidates)
            
            # 5. Extract from contact forms
            form_candidates = self._extract_from_contact_forms(soup, base_url)
            candidates.extend(form_candidates)
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")
        
        # Remove duplicates based on email address
        unique_candidates = {}
        for candidate in candidates:
            if candidate.email not in unique_candidates:
                unique_candidates[candidate.email] = candidate
            else:
                # Keep the candidate with higher confidence
                existing = unique_candidates[candidate.email]
                if candidate.confidence_score > existing.confidence_score:
                    unique_candidates[candidate.email] = candidate
        
        result = list(unique_candidates.values())
        self.logger.info(f"Extracted {len(result)} unique email candidates from HTML")
        
        return result
    
    def _extract_from_mailto_links(self, soup: BeautifulSoup, base_url: str) -> List[EmailCandidate]:
        """Extract emails from mailto links"""
        candidates = []
        
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        
        for link in mailto_links:
            try:
                href = link.get('href', '')
                if not href.lower().startswith('mailto:'):
                    continue
                
                # Extract email from href
                email = href[7:].split('?')[0].split('#')[0].strip()
                
                if not email or '@' not in email:
                    continue
                
                # Get context
                link_text = link.get_text(strip=True)
                surrounding_text = self._get_surrounding_text(link)
                
                candidate = EmailCandidate(
                    email=email,
                    source=EmailSource.MAILTO_LINK,
                    page_url=base_url,
                    context_text=link_text,
                    surrounding_text=surrounding_text,
                    extraction_method="mailto_href",
                    confidence_score=0.8  # High confidence for mailto links
                )
                
                candidates.append(candidate)
                
            except Exception as e:
                self.logger.debug(f"Error processing mailto link: {e}")
        
        return candidates
    
    def _extract_from_visible_text(self, soup: BeautifulSoup, base_url: str) -> List[EmailCandidate]:
        """Extract emails from visible text with context analysis"""
        candidates = []
        
        # Get visible text from different sections
        sections = [
            ('footer', soup.find_all(['footer', '[class*="footer"]'])),
            ('header', soup.find_all(['header', '[class*="header"]'])),
            ('contact', soup.find_all('[class*="contact"]')),
            ('main', [soup])
        ]
        
        for section_type, elements in sections:
            if not elements:
                continue
                
            for element in elements:
                try:
                    text = element.get_text() if hasattr(element, 'get_text') else str(element)
                    
                    # Extract emails from this section
                    email_matches = self.extract_emails_from_text(text, section_type)
                    
                    for email, source, method in email_matches:
                        # Get more specific context around the email
                        surrounding_text = self._extract_email_context(text, email)
                        
                        candidate = EmailCandidate(
                            email=email,
                            source=source,
                            page_url=base_url,
                            context_text=section_type,
                            surrounding_text=surrounding_text,
                            extraction_method=method,
                            confidence_score=self._calculate_base_confidence(email, source, section_type)
                        )
                        
                        candidates.append(candidate)
                        
                except Exception as e:
                    self.logger.debug(f"Error processing text section: {e}")
        
        return candidates
    
    def _extract_from_attributes(self, soup: BeautifulSoup, base_url: str) -> List[EmailCandidate]:
        """Extract emails from HTML attributes"""
        candidates = []
        
        # Common attributes that might contain emails
        attribute_patterns = [
            ('data-email', 'data_attribute'),
            ('data-contact', 'data_attribute'),
            ('content', 'content_attribute'),
            ('value', 'value_attribute'),
            ('placeholder', 'placeholder_attribute'),
            ('title', 'title_attribute')
        ]
        
        for attr_name, method in attribute_patterns:
            elements = soup.find_all(attrs={attr_name: True})
            
            for element in elements:
                try:
                    attr_value = element.get(attr_name, '')
                    
                    # Extract emails from attribute value
                    email_matches = self.extract_emails_from_text(attr_value, f"attribute_{attr_name}")
                    
                    for email, source, extraction_method in email_matches:
                        candidate = EmailCandidate(
                            email=email,
                            source=EmailSource.HTML_ATTRIBUTE,
                            page_url=base_url,
                            context_text=f"{attr_name}={attr_value}",
                            extraction_method=f"{method}_{extraction_method}",
                            confidence_score=0.6  # Medium confidence for attributes
                        )
                        
                        candidates.append(candidate)
                        
                except Exception as e:
                    self.logger.debug(f"Error processing attribute {attr_name}: {e}")
        
        return candidates
    
    def _extract_from_meta_tags(self, soup: BeautifulSoup, base_url: str) -> List[EmailCandidate]:
        """Extract emails from meta tags"""
        candidates = []
        
        meta_tags = soup.find_all('meta')
        
        for meta in meta_tags:
            try:
                # Check both content and name attributes
                for attr in ['content', 'name', 'property']:
                    value = meta.get(attr, '')
                    if not value:
                        continue
                    
                    email_matches = self.extract_emails_from_text(value, "meta_tag")
                    
                    for email, source, method in email_matches:
                        candidate = EmailCandidate(
                            email=email,
                            source=EmailSource.META_TAG,
                            page_url=base_url,
                            context_text=f"meta_{attr}={value}",
                            extraction_method=f"meta_{attr}_{method}",
                            confidence_score=0.5  # Lower confidence for meta tags
                        )
                        
                        candidates.append(candidate)
                        
            except Exception as e:
                self.logger.debug(f"Error processing meta tag: {e}")
        
        return candidates
    
    def _extract_from_contact_forms(self, soup: BeautifulSoup, base_url: str) -> List[EmailCandidate]:
        """Extract emails from contact form contexts"""
        candidates = []
        
        # Find forms that might be contact forms
        forms = soup.find_all('form')
        
        for form in forms:
            try:
                # Check if form looks like a contact form
                form_text = form.get_text().lower()
                if any(keyword in form_text for keyword in ['contact', 'email', 'message', 'inquiry']):
                    
                    # Look for emails in form context
                    email_matches = self.extract_emails_from_text(form.get_text(), "contact_form")
                    
                    for email, source, method in email_matches:
                        candidate = EmailCandidate(
                            email=email,
                            source=EmailSource.CONTACT_FORM,
                            page_url=base_url,
                            context_text="contact_form_context",
                            extraction_method=f"contact_form_{method}",
                            confidence_score=0.7  # Higher confidence for contact form context
                        )
                        
                        candidates.append(candidate)
                        
            except Exception as e:
                self.logger.debug(f"Error processing contact form: {e}")
        
        return candidates
    
    def _get_surrounding_text(self, element, window_size: int = 100) -> str:
        """Get surrounding text context for an element"""
        try:
            # Get parent text
            parent = element.parent
            if parent:
                text = parent.get_text()
                # Find element position and extract window around it
                element_text = element.get_text()
                if element_text in text:
                    pos = text.find(element_text)
                    start = max(0, pos - window_size)
                    end = min(len(text), pos + len(element_text) + window_size)
                    return text[start:end].strip()
            
            return element.get_text(strip=True)
        except:
            return ""
    
    def _extract_email_context(self, text: str, email: str, window_size: int = 50) -> str:
        """Extract context around an email in text"""
        try:
            email_pos = text.lower().find(email.lower())
            if email_pos >= 0:
                start = max(0, email_pos - window_size)
                end = min(len(text), email_pos + len(email) + window_size)
                return text[start:end].strip()
            return ""
        except:
            return ""
    
    def _calculate_base_confidence(self, email: str, source: EmailSource, context: str) -> float:
        """Calculate base confidence score for an email"""
        confidence = 0.5  # Base confidence
        
        # Source type bonuses
        source_bonuses = {
            EmailSource.MAILTO_LINK: 0.3,
            EmailSource.CONTACT_FORM: 0.2,
            EmailSource.FOOTER: 0.1,
            EmailSource.OBFUSCATED_TEXT: 0.1,
            EmailSource.VISIBLE_TEXT: 0.0,
            EmailSource.HTML_ATTRIBUTE: -0.1,
            EmailSource.META_TAG: -0.2
        }
        
        confidence += source_bonuses.get(source, 0.0)
        
        # Context bonuses
        if context in ['footer', 'contact', 'contact_form']:
            confidence += 0.1
        
        # Email pattern analysis
        email_lower = email.lower()
        
        # Business email indicators
        for keyword_group in self.business_keywords.values():
            if any(keyword in email_lower for keyword in keyword_group):
                confidence += 0.1
                break
        
        # Generic email penalties
        for pattern in self.generic_patterns:
            if re.match(pattern, email_lower):
                confidence -= 0.3
                break
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))


class EmailValidator:
    """
    Email validation and quality assessment system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Initialize validation rules
        self._initialize_validation_rules()
        
        self.logger.info("EmailValidator initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailValidator")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_validation_rules(self):
        """Initialize email validation rules"""
        # High-quality business email patterns
        self.high_quality_patterns = [
            r'^(ceo|founder|president|director|manager|lead|head|chief|owner)@',
            r'^(contact|business|sales|marketing|pr|press|media)@',
            r'^[a-z]+\.[a-z]+@',  # firstname.lastname format
        ]
        
        # Medium-quality patterns
        self.medium_quality_patterns = [
            r'^(info|hello|team|support|admin)@',
            r'^[a-z]+@',  # Simple first name
        ]
        
        # Low-quality/spam patterns
        self.low_quality_patterns = [
            r'^(noreply|no-reply|donotreply|test|testing|example)@',
            r'@(test\.|example\.|localhost|.*\.local)',
            r'^(webmaster|postmaster|administrator)@',
        ]
        
        # Domain quality indicators
        self.business_domains = [
            'gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com',
            'aol.com', 'icloud.com', 'protonmail.com'
        ]
        
        # Suspicious domain patterns
        self.suspicious_domains = [
            r'\.tk$', r'\.ml$', r'\.ga$', r'\.cf$',  # Free domains
            r'\d{2,}\.com$',  # Numeric domains
            r'[a-z]{1,3}\d+\.com$',  # Short + numbers
        ]
    
    def validate_email(self, email: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Comprehensive email validation.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, status_message, validation_details)
        """
        if not email:
            return False, "Empty email", {}
        
        validation_details = {
            'syntax_valid': False,
            'deliverable': 'unknown',
            'domain_exists': 'unknown',
            'mx_record': 'unknown',
            'quality_score': 0.0
        }
        
        try:
            # Basic syntax validation
            validated = validate_email(email)
            validation_details['syntax_valid'] = True
            normalized_email = validated.email
            
            # Quality assessment
            quality_score = self._assess_email_quality(normalized_email)
            validation_details['quality_score'] = quality_score
            
            return True, "Valid", validation_details
            
        except EmailNotValidError as e:
            validation_details['syntax_valid'] = False
            return False, f"Invalid syntax: {str(e)}", validation_details
        
        except Exception as e:
            self.logger.debug(f"Email validation error for {email}: {e}")
            return False, f"Validation error: {str(e)}", validation_details
    
    def _assess_email_quality(self, email: str) -> float:
        """Assess the quality/business value of an email"""
        quality_score = 0.5  # Base score
        
        email_lower = email.lower()
        local_part, domain = email_lower.split('@', 1)
        
        # Local part analysis
        for pattern in self.high_quality_patterns:
            if re.match(pattern, email_lower):
                quality_score += 0.3
                break
        else:
            for pattern in self.medium_quality_patterns:
                if re.match(pattern, email_lower):
                    quality_score += 0.1
                    break
        
        # Penalty for low-quality patterns
        for pattern in self.low_quality_patterns:
            if re.match(pattern, email_lower):
                quality_score -= 0.4
                break
        
        # Domain analysis
        if domain in self.business_domains:
            quality_score -= 0.1  # Personal email domains get slight penalty
        
        # Check for suspicious domains
        for pattern in self.suspicious_domains:
            if re.search(pattern, domain):
                quality_score -= 0.3
                break
        
        # Format bonuses
        if '.' in local_part:
            quality_score += 0.1  # firstname.lastname format
        
        if len(local_part) >= 4:  # Not too short
            quality_score += 0.05
        
        return max(0.0, min(1.0, quality_score))
    
    def classify_email_quality(self, email: str, context_score: float = 0.0) -> EmailQuality:
        """
        Classify email quality level.
        
        Args:
            email: Email address
            context_score: Additional context-based score
            
        Returns:
            EmailQuality enum value
        """
        is_valid, _, details = self.validate_email(email)
        
        if not is_valid:
            return EmailQuality.SPAM
        
        # Combine quality score with context
        total_score = details.get('quality_score', 0.0) + context_score
        
        if total_score >= 0.7:
            return EmailQuality.HIGH
        elif total_score >= 0.4:
            return EmailQuality.MEDIUM
        elif total_score >= 0.1:
            return EmailQuality.LOW
        else:
            return EmailQuality.SPAM


class EmailContextAnalyzer:
    """
    Analyzes context around emails to extract additional contact information.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Initialize pattern matching
        self._initialize_patterns()
        
        self.logger.info("EmailContextAnalyzer initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailContextAnalyzer")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def _initialize_patterns(self):
        """Initialize context analysis patterns"""
        # Name patterns
        self.name_patterns = [
            re.compile(r'([A-Z][a-z]+ [A-Z][a-z]+)', re.IGNORECASE),  # First Last
            re.compile(r'([A-Z]\. [A-Z][a-z]+)', re.IGNORECASE),     # F. Last
            re.compile(r'([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)', re.IGNORECASE),  # First M. Last
        ]
        
        # Title patterns
        self.title_patterns = [
            re.compile(r'\b(CEO|Chief Executive Officer|President|Founder|Director|Manager|Lead|Head|Chief)\b', re.IGNORECASE),
            re.compile(r'\b(VP|Vice President|Senior|Junior|Principal|Associate)\b', re.IGNORECASE),
            re.compile(r'\b(Marketing|Sales|Operations|Finance|HR|Human Resources|Legal|Technical|IT)\s+(Manager|Director|Lead|Head)\b', re.IGNORECASE),
        ]
        
        # Department patterns
        self.department_patterns = [
            re.compile(r'\b(Marketing|Sales|Operations|Finance|HR|Human Resources|Legal|Technical|IT|Support|Customer Service)\b', re.IGNORECASE),
        ]
        
        # Phone patterns
        self.phone_patterns = [
            re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),  # US phone
            re.compile(r'\b\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}\b'),  # International
        ]
    
    def analyze_email_context(self, candidate: EmailCandidate, page_content: str = "") -> EmailCandidate:
        """
        Analyze context around an email to extract additional information.
        
        Args:
            candidate: EmailCandidate to enrich
            page_content: Full page content for context analysis
            
        Returns:
            Enhanced EmailCandidate with additional context
        """
        try:
            # Analyze surrounding text for contact information
            context_text = candidate.surrounding_text or candidate.context_text
            
            # Extract name
            name = self._extract_name(context_text, candidate.email)
            if name:
                candidate.associated_name = name
            
            # Extract title
            title = self._extract_title(context_text)
            if title:
                candidate.associated_title = title
            
            # Extract department
            department = self._extract_department(context_text)
            if department:
                candidate.associated_department = department
            
            # Extract phone number
            phone = self._extract_phone(context_text)
            if phone:
                candidate.phone_number = phone
            
            # Update confidence based on context richness
            context_bonus = self._calculate_context_bonus(candidate)
            candidate.confidence_score = min(1.0, candidate.confidence_score + context_bonus)
            
        except Exception as e:
            self.logger.debug(f"Error analyzing context for {candidate.email}: {e}")
        
        return candidate
    
    def _extract_name(self, text: str, email: str) -> Optional[str]:
        """Extract associated name from context"""
        if not text:
            return None
        
        # Try to extract from email local part first
        local_part = email.split('@')[0]
        
        # Check for firstname.lastname pattern
        if '.' in local_part:
            parts = local_part.split('.')
            if len(parts) == 2 and all(part.isalpha() for part in parts):
                return f"{parts[0].title()} {parts[1].title()}"
        
        # Look for names in surrounding text
        for pattern in self.name_patterns:
            matches = pattern.findall(text)
            if matches:
                return matches[0]
        
        return None
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract job title from context"""
        if not text:
            return None
        
        for pattern in self.title_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_department(self, text: str) -> Optional[str]:
        """Extract department from context"""
        if not text:
            return None
        
        for pattern in self.department_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from context"""
        if not text:
            return None
        
        for pattern in self.phone_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)
        
        return None
    
    def _calculate_context_bonus(self, candidate: EmailCandidate) -> float:
        """Calculate confidence bonus based on context richness"""
        bonus = 0.0
        
        if candidate.associated_name:
            bonus += 0.1
        if candidate.associated_title:
            bonus += 0.1
        if candidate.associated_department:
            bonus += 0.05
        if candidate.phone_number:
            bonus += 0.05
        
        return bonus


class EmailExtractionEngine:
    """
    Main email extraction engine that coordinates all components.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Initialize components
        self.pattern_detector = EmailPatternDetector(
            self.config.get("pattern_detector", {})
        )
        self.validator = EmailValidator(
            self.config.get("validator", {})
        )
        self.context_analyzer = EmailContextAnalyzer(
            self.config.get("context_analyzer", {})
        )
        
        # Configuration
        self.score_threshold = self.config.get("score_threshold", 0.3)
        self.max_candidates_per_page = self.config.get("max_candidates_per_page", 50)
        
        # Statistics
        self.stats = {
            'pages_processed': 0,
            'total_candidates': 0,
            'valid_emails': 0,
            'high_quality_emails': 0,
            'extraction_time_ms': 0.0
        }
        
        self.logger.info(f"EmailExtractionEngine initialized with threshold {self.score_threshold}")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailExtractionEngine")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def extract_from_page(self, html_content: str, page_url: str) -> EmailExtractionResult:
        """
        Extract emails from a single page.
        
        Args:
            html_content: HTML content of the page
            page_url: URL of the page
            
        Returns:
            EmailExtractionResult with all discovered candidates
        """
        start_time = time.time()
        
        try:
            # Extract candidates using pattern detection
            candidates = self.pattern_detector.extract_from_html(html_content, page_url)
            
            # Validate and score candidates
            validated_candidates = []
            for candidate in candidates:
                # Validate email
                is_valid, status, details = self.validator.validate_email(candidate.email)
                candidate.validation_status = status
                
                if is_valid:
                    # Classify quality
                    quality = self.validator.classify_email_quality(
                        candidate.email, 
                        candidate.confidence_score
                    )
                    candidate.quality = quality
                    
                    # Analyze context
                    candidate = self.context_analyzer.analyze_email_context(
                        candidate, html_content
                    )
                    
                    # Apply score threshold
                    if candidate.confidence_score >= self.score_threshold:
                        validated_candidates.append(candidate)
                else:
                    # Mark as spam but keep for analysis
                    candidate.quality = EmailQuality.SPAM
                    if candidate.confidence_score >= self.score_threshold:
                        validated_candidates.append(candidate)
            
            # Limit candidates per page
            if len(validated_candidates) > self.max_candidates_per_page:
                # Sort by confidence and take top candidates
                validated_candidates.sort(key=lambda x: x.confidence_score, reverse=True)
                validated_candidates = validated_candidates[:self.max_candidates_per_page]
            
            extraction_time = (time.time() - start_time) * 1000
            
            # Create result
            result = EmailExtractionResult(
                page_url=page_url,
                candidates=validated_candidates,
                extraction_time_ms=extraction_time
            )
            
            # Update statistics
            self._update_statistics(result, extraction_time)
            
            self.logger.info(
                f"Extracted {len(validated_candidates)} candidates from {page_url} "
                f"({len(result.high_quality_emails)} high quality) in {extraction_time:.1f}ms"
            )
            
            return result
            
        except Exception as e:
            extraction_time = (time.time() - start_time) * 1000
            self.logger.error(f"Error extracting emails from {page_url}: {e}")
            
            return EmailExtractionResult(
                page_url=page_url,
                extraction_time_ms=extraction_time,
                error=str(e)
            )
    
    def extract_from_crawl_results(self, crawl_results: Dict[str, Any]) -> Dict[str, EmailExtractionResult]:
        """
        Extract emails from multiple crawled pages.
        
        Args:
            crawl_results: Dictionary of URL -> page content
            
        Returns:
            Dictionary of URL -> EmailExtractionResult
        """
        extraction_results = {}
        
        for url, page_data in crawl_results.items():
            try:
                if isinstance(page_data, dict):
                    html_content = page_data.get('content', '')
                else:
                    html_content = str(page_data)
                
                if html_content:
                    result = self.extract_from_page(html_content, url)
                    extraction_results[url] = result
                else:
                    self.logger.warning(f"No content found for {url}")
                    
            except Exception as e:
                self.logger.error(f"Error processing crawl result for {url}: {e}")
                extraction_results[url] = EmailExtractionResult(
                    page_url=url,
                    error=str(e)
                )
        
        self.logger.info(f"Processed {len(extraction_results)} pages for email extraction")
        return extraction_results
    
    def _update_statistics(self, result: EmailExtractionResult, extraction_time: float):
        """Update extraction statistics"""
        self.stats['pages_processed'] += 1
        self.stats['total_candidates'] += len(result.candidates)
        self.stats['valid_emails'] += len([c for c in result.candidates if c.validation_status == "Valid"])
        self.stats['high_quality_emails'] += len(result.high_quality_emails)
        self.stats['extraction_time_ms'] += extraction_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        stats = self.stats.copy()
        
        if stats['pages_processed'] > 0:
            stats['avg_candidates_per_page'] = stats['total_candidates'] / stats['pages_processed']
            stats['avg_extraction_time_ms'] = stats['extraction_time_ms'] / stats['pages_processed']
            stats['valid_email_rate'] = stats['valid_emails'] / max(1, stats['total_candidates'])
            stats['high_quality_rate'] = stats['high_quality_emails'] / max(1, stats['valid_emails'])
        
        return stats


class EmailExtractorAgent(Agent):
    """
    Agency Swarm agent for email extraction and contact discovery.
    
    This agent coordinates the email extraction process using the EmailExtractionEngine
    and provides tools for email discovery operations.
    """
    
    def __init__(self):
        super().__init__(
            name="EmailExtractor",
            description="Extracts and scores business email addresses from crawled website content using multi-method detection and context analysis",
            instructions="./instructions.md",
            tools_folder="./tools",
            temperature=0.1,
            max_prompt_tokens=25000,
        )
        
        # Initialize the extraction engine
        self.extraction_engine = EmailExtractionEngine()
        
        self.logger = logging.getLogger(f"{__name__}.EmailExtractorAgent")
        self.logger.info("EmailExtractorAgent initialized")