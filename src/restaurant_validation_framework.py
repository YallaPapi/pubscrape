"""
Restaurant Lead Generation Validation Framework
==============================================

A comprehensive validation system for restaurant business leads in Santa Monica, 
designed to catch fake data, technical shortcuts, and ensure data authenticity 
at every step of the scraping process.

Features:
- Real-time data authenticity validation
- Restaurant-specific business verification
- Santa Monica geographic validation
- Email domain authenticity checks
- Phone number format and area code validation
- Anti-fake data detection with multiple verification layers
- Technical debt monitoring and prevention
"""

import logging
import re
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from urllib.parse import urlparse
import requests
from datetime import datetime
import dns.resolver
from pathlib import Path


class ValidationLevel(Enum):
    """Validation strictness levels"""
    STRICT = "strict"      # Zero tolerance for any questionable data
    NORMAL = "normal"      # Standard validation rules
    PERMISSIVE = "permissive"  # Allow minor irregularities


class DataQuality(Enum):
    """Data quality assessment levels"""
    AUTHENTIC = "authentic"     # Verified real restaurant data
    SUSPICIOUS = "suspicious"   # Questionable but not conclusively fake
    FAKE = "fake"              # Clearly fake or generated data
    INCOMPLETE = "incomplete"   # Missing critical information


class ValidationStatus(Enum):
    """Validation result statuses"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    status: ValidationStatus
    quality: DataQuality
    score: float  # 0.0 to 1.0, higher is better
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RestaurantLead:
    """Restaurant lead data structure with validation tracking"""
    name: str
    address: str
    phone: str
    email: str
    website: str
    cuisine_type: str = ""
    price_range: str = ""
    rating: float = 0.0
    source_url: str = ""
    
    # Validation tracking
    validation_results: List[ValidationResult] = field(default_factory=list)
    overall_score: float = 0.0
    is_authentic: bool = False
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_validation_result(self, result: ValidationResult):
        """Add a validation result and update overall score"""
        self.validation_results.append(result)
        self._update_overall_score()
    
    def _update_overall_score(self):
        """Update overall authenticity score based on all validation results"""
        if not self.validation_results:
            self.overall_score = 0.0
            return
            
        # Calculate weighted average with penalty for failures
        total_score = 0.0
        total_weight = 0.0
        
        for result in self.validation_results:
            weight = 1.0
            score = result.score
            
            # Apply penalties for failed validations
            if result.status == ValidationStatus.FAIL:
                score *= 0.1  # Heavy penalty for failures
                weight = 2.0  # Give failures more weight
            elif result.status == ValidationStatus.WARNING:
                score *= 0.7  # Moderate penalty for warnings
                weight = 1.5
            elif result.quality == DataQuality.FAKE:
                score = 0.0  # Zero score for fake data
                weight = 3.0  # Maximum weight for fake data detection
            
            total_score += score * weight
            total_weight += weight
        
        self.overall_score = total_score / total_weight if total_weight > 0 else 0.0
        self.is_authentic = self.overall_score >= 0.7 and not any(
            r.quality == DataQuality.FAKE for r in self.validation_results
        )


class RestaurantBusinessValidator:
    """Validates that businesses are actual restaurants, not fake/generated data"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.RestaurantBusinessValidator")
        
        # Real restaurant indicators
        self.restaurant_keywords = {
            'cuisine_types': {
                'american', 'italian', 'chinese', 'mexican', 'thai', 'indian', 'japanese',
                'french', 'mediterranean', 'greek', 'korean', 'vietnamese', 'pizza',
                'seafood', 'steakhouse', 'barbecue', 'bakery', 'cafe', 'diner',
                'gastropub', 'bistro', 'brasserie', 'trattoria', 'cantina', 'sushi'
            },
            'business_types': {
                'restaurant', 'eatery', 'dining', 'kitchen', 'grill', 'house',
                'room', 'bar', 'pub', 'tavern', 'lounge', 'club', 'cafe',
                'bistro', 'diner', 'pizzeria', 'steakhouse', 'bakery'
            }
        }
        
        # Fake data patterns to detect
        self.fake_patterns = {
            'test_names': re.compile(r'\b(test|sample|example|demo|fake|mock|temp|placeholder|lorem|ipsum)\b', re.IGNORECASE),
            'generic_names': re.compile(r'^(restaurant|eatery|cafe|diner)\s*\d*$', re.IGNORECASE),
            'sequential_names': re.compile(r'(restaurant|cafe|diner)\s*[0-9]{1,3}$', re.IGNORECASE),
            'placeholder_domains': re.compile(r'\.(test|example|localhost|local)$', re.IGNORECASE),
            'fake_emails': re.compile(r'\b(test|fake|example|noreply|admin)@', re.IGNORECASE)
        }
    
    def validate_restaurant_authenticity(self, lead: RestaurantLead) -> ValidationResult:
        """Validate that this appears to be a real restaurant business"""
        
        evidence = []
        score = 0.8  # Start with high score, deduct for issues
        quality = DataQuality.AUTHENTIC
        status = ValidationStatus.PASS
        
        # Check for fake data patterns
        fake_indicators = []
        
        # Check restaurant name
        if self.fake_patterns['test_names'].search(lead.name):
            fake_indicators.append(f"Name contains test/placeholder keywords: {lead.name}")
            score -= 0.4
        
        if self.fake_patterns['generic_names'].match(lead.name):
            fake_indicators.append(f"Generic restaurant name pattern: {lead.name}")
            score -= 0.3
        
        if self.fake_patterns['sequential_names'].match(lead.name):
            fake_indicators.append(f"Sequential naming pattern: {lead.name}")
            score -= 0.3
        
        # Check email authenticity
        if lead.email:
            if self.fake_patterns['fake_emails'].search(lead.email):
                fake_indicators.append(f"Fake email pattern: {lead.email}")
                score -= 0.4
            
            if self.fake_patterns['placeholder_domains'].search(lead.email):
                fake_indicators.append(f"Placeholder email domain: {lead.email}")
                score -= 0.5
        
        # Check website authenticity
        if lead.website:
            if self.fake_patterns['placeholder_domains'].search(lead.website):
                fake_indicators.append(f"Placeholder website domain: {lead.website}")
                score -= 0.4
        
        # Positive indicators
        positive_indicators = []
        
        # Check for restaurant-specific keywords
        name_lower = lead.name.lower()
        has_cuisine_type = any(cuisine in name_lower for cuisine in self.restaurant_keywords['cuisine_types'])
        has_business_type = any(btype in name_lower for btype in self.restaurant_keywords['business_types'])
        
        if has_cuisine_type:
            positive_indicators.append(f"Contains cuisine type indicator in name")
            score += 0.1
        
        if has_business_type:
            positive_indicators.append(f"Contains restaurant business type indicator")
            score += 0.1
        
        # Check for realistic business patterns
        if lead.cuisine_type and lead.cuisine_type.lower() in self.restaurant_keywords['cuisine_types']:
            positive_indicators.append(f"Valid cuisine type: {lead.cuisine_type}")
            score += 0.1
        
        # Determine final assessment
        if fake_indicators:
            if len(fake_indicators) >= 2 or score <= 0.3:
                quality = DataQuality.FAKE
                status = ValidationStatus.FAIL
                message = f"Restaurant appears to be fake data (score: {score:.2f})"
            else:
                quality = DataQuality.SUSPICIOUS
                status = ValidationStatus.WARNING
                message = f"Restaurant data is suspicious (score: {score:.2f})"
        else:
            message = f"Restaurant appears authentic (score: {score:.2f})"
        
        evidence.extend(fake_indicators)
        evidence.extend(positive_indicators)
        
        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            status=status,
            quality=quality,
            score=score,
            message=message,
            details={
                'fake_indicators': fake_indicators,
                'positive_indicators': positive_indicators,
                'name_analysis': self._analyze_restaurant_name(lead.name)
            },
            evidence=evidence
        )
    
    def _analyze_restaurant_name(self, name: str) -> Dict[str, Any]:
        """Analyze restaurant name for authenticity indicators"""
        analysis = {
            'length': len(name),
            'word_count': len(name.split()),
            'has_numbers': bool(re.search(r'\d', name)),
            'has_special_chars': bool(re.search(r'[^\w\s]', name)),
            'appears_genuine': True
        }
        
        # Check for overly generic or sequential patterns
        if re.match(r'^(restaurant|cafe|diner|eatery)\s*\d*$', name, re.IGNORECASE):
            analysis['appears_genuine'] = False
            analysis['issue'] = 'Generic pattern'
        
        # Check for test/placeholder patterns
        if re.search(r'\b(test|sample|example|demo|fake)\b', name, re.IGNORECASE):
            analysis['appears_genuine'] = False
            analysis['issue'] = 'Test/placeholder pattern'
        
        return analysis


class SantaMonicaGeographicValidator:
    """Validates that addresses are actually in Santa Monica area"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.SantaMonicaGeographicValidator")
        
        # Santa Monica geographic boundaries and indicators
        self.santa_monica_indicators = {
            'zip_codes': {'90401', '90402', '90403', '90404', '90405'},
            'street_patterns': [
                r'\b(santa monica|sm)\b',
                r'\bwilshire\s+blvd\b',
                r'\bmain\s+st\b',
                r'\bocean\s+ave\b',
                r'\bbroadway\b',
                r'\bpico\s+blvd\b',
                r'\blincoln\s+blvd\b',
                r'\b26th\s+st\b',
                r'\b4th\s+st\b',
                r'\bsanta\s+monica\s+blvd\b'
            ],
            'area_identifiers': [
                'santa monica', 'sm', 'west la', 'westside',
                'venice border', 'mar vista border'
            ]
        }
        
        # Fake address patterns
        self.fake_address_patterns = [
            re.compile(r'\b(test|sample|example|fake|mock)\s+(street|ave|blvd|rd)\b', re.IGNORECASE),
            re.compile(r'^(123|456|789)\s+(main|test|sample)\s+st', re.IGNORECASE),
            re.compile(r'placeholder|lorem\s+ipsum|dummy\s+address', re.IGNORECASE),
            re.compile(r'^\d{1,3}\s+\w+\s+st$', re.IGNORECASE)  # Overly simple pattern
        ]
    
    def validate_santa_monica_location(self, lead: RestaurantLead) -> ValidationResult:
        """Validate that the address is actually in Santa Monica"""
        
        if not lead.address:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                quality=DataQuality.INCOMPLETE,
                score=0.0,
                message="No address provided",
                details={'missing_field': 'address'}
            )
        
        evidence = []
        score = 0.5  # Start neutral
        quality = DataQuality.SUSPICIOUS
        status = ValidationStatus.WARNING
        
        address_lower = lead.address.lower()
        
        # Check for fake address patterns
        fake_issues = []
        for pattern in self.fake_address_patterns:
            if pattern.search(address_lower):
                fake_issues.append(f"Fake address pattern detected: {pattern.pattern}")
                score -= 0.3
        
        # Check for Santa Monica ZIP codes
        zip_found = None
        for zip_code in self.santa_monica_indicators['zip_codes']:
            if zip_code in lead.address:
                zip_found = zip_code
                score += 0.3
                evidence.append(f"Valid Santa Monica ZIP code: {zip_code}")
                break
        
        # Check for Santa Monica street patterns
        street_matches = []
        for pattern in self.santa_monica_indicators['street_patterns']:
            if re.search(pattern, address_lower, re.IGNORECASE):
                street_matches.append(pattern)
                score += 0.2
                evidence.append(f"Santa Monica street pattern found: {pattern}")
        
        # Check for area identifiers
        area_matches = []
        for area in self.santa_monica_indicators['area_identifiers']:
            if area.lower() in address_lower:
                area_matches.append(area)
                score += 0.1
                evidence.append(f"Santa Monica area identifier: {area}")
        
        # Determine final assessment
        if fake_issues:
            quality = DataQuality.FAKE
            status = ValidationStatus.FAIL
            message = "Address appears to be fake or placeholder data"
        elif zip_found or street_matches:
            if score >= 0.7:
                quality = DataQuality.AUTHENTIC
                status = ValidationStatus.PASS
                message = "Address verified as Santa Monica location"
            else:
                quality = DataQuality.SUSPICIOUS
                status = ValidationStatus.WARNING
                message = "Address may be in Santa Monica but needs verification"
        else:
            quality = DataQuality.SUSPICIOUS
            status = ValidationStatus.WARNING
            message = "Cannot verify Santa Monica location from address"
        
        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            status=status,
            quality=quality,
            score=score,
            message=message,
            details={
                'zip_code_found': zip_found,
                'street_matches': street_matches,
                'area_matches': area_matches,
                'fake_issues': fake_issues,
                'address_components': self._parse_address_components(lead.address)
            },
            evidence=evidence
        )
    
    def _parse_address_components(self, address: str) -> Dict[str, str]:
        """Parse address components for analysis"""
        components = {
            'full_address': address,
            'has_street_number': bool(re.match(r'^\d+', address.strip())),
            'has_street_name': bool(re.search(r'\b\w+\s+(st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|way|ct|court|pl|place)\b', address, re.IGNORECASE)),
            'has_zip': bool(re.search(r'\b\d{5}(-\d{4})?\b', address)),
            'appears_complete': len(address.strip()) >= 20  # Minimum length for complete address
        }
        return components


class PhoneNumberValidator:
    """Validates phone numbers for authenticity and proper formatting"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.PhoneNumberValidator")
        
        # Valid area codes for Los Angeles/Santa Monica area
        self.valid_area_codes = {
            '310', '424', '213', '323', '818', '747', '626', '661', '562'
        }
        
        # Fake phone patterns
        self.fake_phone_patterns = [
            re.compile(r'\b555-?\d{4}\b'),  # 555 numbers
            re.compile(r'\b(123|000|111|222|333|444|666|777|888|999)[- ]?\d{3}[- ]?\d{4}\b'),
            re.compile(r'\b\d{3}[- ]?1234\b'),  # Ending in 1234
            re.compile(r'\b\d{3}[- ]?0000\b'),  # Ending in 0000
            re.compile(r'\b(000|111|222|333|444|555|666|777|888|999)[- ]\d{3}[- ]\d{4}\b')
        ]
    
    def validate_phone_number(self, lead: RestaurantLead) -> ValidationResult:
        """Validate phone number authenticity and format"""
        
        if not lead.phone:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                quality=DataQuality.INCOMPLETE,
                score=0.0,
                message="No phone number provided",
                details={'missing_field': 'phone'}
            )
        
        evidence = []
        score = 0.7  # Start high, deduct for issues
        quality = DataQuality.AUTHENTIC
        status = ValidationStatus.PASS
        
        phone_clean = re.sub(r'[^\d]', '', lead.phone)
        
        # Check for fake phone patterns
        fake_issues = []
        for pattern in self.fake_phone_patterns:
            if pattern.search(lead.phone):
                fake_issues.append(f"Fake phone pattern detected: {pattern.pattern}")
                score -= 0.5
        
        # Validate phone format and length
        format_issues = []
        
        if len(phone_clean) != 10 and len(phone_clean) != 11:
            format_issues.append(f"Invalid phone length: {len(phone_clean)} digits")
            score -= 0.3
        elif len(phone_clean) == 11 and not phone_clean.startswith('1'):
            format_issues.append("11-digit phone should start with 1")
            score -= 0.2
        
        # Extract area code
        area_code = None
        if len(phone_clean) >= 10:
            area_code = phone_clean[-10:-7] if len(phone_clean) == 11 else phone_clean[:3]
            
            if area_code in self.valid_area_codes:
                evidence.append(f"Valid LA/Santa Monica area code: {area_code}")
                score += 0.2
            else:
                evidence.append(f"Area code not in LA/Santa Monica region: {area_code}")
                score -= 0.1
        
        # Check for realistic phone patterns
        if phone_clean and len(phone_clean) >= 10:
            last_four = phone_clean[-4:]
            if last_four in ['0000', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999', '1234']:
                fake_issues.append(f"Unrealistic phone ending: {last_four}")
                score -= 0.3
        
        # Determine final assessment
        if fake_issues or format_issues:
            if fake_issues and len(fake_issues) >= 1:
                quality = DataQuality.FAKE
                status = ValidationStatus.FAIL
                message = "Phone number appears to be fake or test data"
            else:
                quality = DataQuality.SUSPICIOUS
                status = ValidationStatus.WARNING
                message = "Phone number format is questionable"
        else:
            message = f"Phone number appears authentic (area code: {area_code})"
        
        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            status=status,
            quality=quality,
            score=score,
            message=message,
            details={
                'area_code': area_code,
                'cleaned_phone': phone_clean,
                'format_issues': format_issues,
                'fake_issues': fake_issues,
                'is_local_area': area_code in self.valid_area_codes if area_code else False
            },
            evidence=evidence
        )


class EmailDomainValidator:
    """Validates email domains for authenticity and business legitimacy"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.EmailDomainValidator")
        
        # Common business email domains vs personal
        self.personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
            'icloud.com', 'me.com', 'protonmail.com', 'mail.com'
        }
        
        # Fake/test domain patterns
        self.fake_domain_patterns = [
            re.compile(r'\.(test|example|localhost|local|dev)$', re.IGNORECASE),
            re.compile(r'^(test|fake|sample|example|demo)\w*\.', re.IGNORECASE),
            re.compile(r'placeholder|lorem|ipsum', re.IGNORECASE)
        ]
        
        # DNS cache for performance
        self._dns_cache = {}
    
    def validate_email_domain(self, lead: RestaurantLead) -> ValidationResult:
        """Validate email domain authenticity and business appropriateness"""
        
        if not lead.email:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                quality=DataQuality.INCOMPLETE,
                score=0.0,
                message="No email provided",
                details={'missing_field': 'email'}
            )
        
        evidence = []
        score = 0.6  # Start neutral
        quality = DataQuality.SUSPICIOUS
        status = ValidationStatus.WARNING
        
        # Extract domain
        try:
            domain = lead.email.split('@')[1].lower()
        except IndexError:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                quality=DataQuality.FAKE,
                score=0.0,
                message="Invalid email format - no @ symbol",
                details={'email_format_error': True}
            )
        
        # Check for fake domain patterns
        fake_issues = []
        for pattern in self.fake_domain_patterns:
            if pattern.search(domain):
                fake_issues.append(f"Fake domain pattern: {pattern.pattern}")
                score -= 0.4
        
        # Check domain type
        if domain in self.personal_domains:
            evidence.append(f"Personal email domain: {domain}")
            score += 0.1  # Personal emails can be legitimate for small restaurants
        else:
            evidence.append(f"Business/custom domain: {domain}")
            score += 0.3  # Business domains are preferred
        
        # Check domain existence (DNS)
        dns_result = self._check_domain_dns(domain)
        if dns_result['exists']:
            evidence.append("Domain has valid DNS records")
            score += 0.2
            if dns_result['has_mx']:
                evidence.append("Domain has MX records for email")
                score += 0.1
        else:
            evidence.append("Domain does not exist or has no DNS records")
            score -= 0.5
            fake_issues.append("Domain does not exist")
        
        # Check for restaurant-themed domain names
        restaurant_indicators = ['restaurant', 'cafe', 'diner', 'eatery', 'kitchen', 'grill', 'bistro']
        if any(indicator in domain for indicator in restaurant_indicators):
            evidence.append("Domain contains restaurant-related keywords")
            score += 0.1
        
        # Determine final assessment
        if fake_issues:
            quality = DataQuality.FAKE
            status = ValidationStatus.FAIL
            message = "Email domain appears to be fake or test data"
        elif score >= 0.8:
            quality = DataQuality.AUTHENTIC
            status = ValidationStatus.PASS
            message = "Email domain appears authentic and business-appropriate"
        elif score >= 0.5:
            quality = DataQuality.SUSPICIOUS
            status = ValidationStatus.WARNING
            message = "Email domain is questionable but may be legitimate"
        else:
            quality = DataQuality.FAKE
            status = ValidationStatus.FAIL
            message = "Email domain fails authenticity checks"
        
        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))
        
        return ValidationResult(
            status=status,
            quality=quality,
            score=score,
            message=message,
            details={
                'domain': domain,
                'is_personal': domain in self.personal_domains,
                'dns_exists': dns_result['exists'],
                'has_mx_records': dns_result['has_mx'],
                'fake_issues': fake_issues
            },
            evidence=evidence
        )
    
    def _check_domain_dns(self, domain: str) -> Dict[str, bool]:
        """Check if domain exists and has proper DNS records"""
        
        # Check cache first
        if domain in self._dns_cache:
            return self._dns_cache[domain]
        
        result = {'exists': False, 'has_mx': False}
        
        try:
            # Check A record (domain exists)
            dns.resolver.resolve(domain, 'A')
            result['exists'] = True
            
            # Check MX record (email capability)
            try:
                dns.resolver.resolve(domain, 'MX')
                result['has_mx'] = True
            except:
                pass
                
        except Exception as e:
            self.logger.debug(f"DNS check failed for {domain}: {e}")
        
        # Cache result
        self._dns_cache[domain] = result
        return result


class TechnicalDebtMonitor:
    """Monitors for technical shortcuts, mocked data, and implementation issues"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.TechnicalDebtMonitor")
        
        # Technical debt patterns to detect
        self.debt_patterns = {
            'mock_data': [
                re.compile(r'\b(mock|fake|test|sample|placeholder|lorem|ipsum)\b', re.IGNORECASE),
                re.compile(r'TODO|FIXME|HACK|XXX', re.IGNORECASE),
                re.compile(r'hardcode|hardcoded', re.IGNORECASE)
            ],
            'suspicious_uniformity': [
                # Patterns that suggest generated rather than scraped data
                re.compile(r'^(Restaurant|Cafe|Diner)\s+\d+$'),  # Sequential naming
                re.compile(r'@(test|example)\.com$'),  # Test email domains
                re.compile(r'^\d{3}-\d{3}-\d{4}$')  # Too perfect phone formatting
            ],
            'implementation_shortcuts': [
                # Patterns that suggest shortcuts were taken
                re.compile(r'^\s*$'),  # Empty fields
                re.compile(r'^(N/A|n/a|null|None|undefined)$'),  # Placeholder values
                re.compile(r'^default|generic|placeholder', re.IGNORECASE)
            ]
        }
    
    def monitor_lead_data(self, leads: List[RestaurantLead]) -> ValidationResult:
        """Monitor a batch of leads for technical debt indicators"""
        
        if not leads:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                quality=DataQuality.FAKE,
                score=0.0,
                message="No leads provided for monitoring",
                details={'empty_dataset': True}
            )
        
        evidence = []
        score = 1.0  # Start perfect, deduct for issues
        issues_found = []
        
        # Check for suspicious patterns across leads
        uniformity_issues = self._check_data_uniformity(leads)
        if uniformity_issues:
            score -= 0.3
            issues_found.extend(uniformity_issues)
            evidence.extend(uniformity_issues)
        
        # Check individual leads for technical debt
        debt_count = 0
        for i, lead in enumerate(leads):
            lead_issues = self._check_lead_technical_debt(lead, i)
            if lead_issues:
                debt_count += len(lead_issues)
                issues_found.extend([f"Lead {i}: {issue}" for issue in lead_issues])
        
        # Calculate debt penalty
        if debt_count > 0:
            debt_ratio = debt_count / (len(leads) * 5)  # 5 fields per lead
            score -= min(0.5, debt_ratio * 2)  # Maximum penalty of 0.5
        
        # Check for data generation patterns
        generation_issues = self._check_generation_patterns(leads)
        if generation_issues:
            score -= 0.4
            issues_found.extend(generation_issues)
            evidence.extend(generation_issues)
        
        # Determine final assessment
        if score <= 0.3:
            status = ValidationStatus.FAIL
            quality = DataQuality.FAKE
            message = "Significant technical debt and fake data indicators detected"
        elif score <= 0.6:
            status = ValidationStatus.WARNING
            quality = DataQuality.SUSPICIOUS
            message = "Some technical debt indicators found, data quality questionable"
        else:
            status = ValidationStatus.PASS
            quality = DataQuality.AUTHENTIC
            message = "Minimal technical debt detected, data appears authentic"
        
        return ValidationResult(
            status=status,
            quality=quality,
            score=score,
            message=message,
            details={
                'total_leads': len(leads),
                'debt_count': debt_count,
                'issues_found': issues_found,
                'uniformity_analysis': uniformity_issues,
                'generation_analysis': generation_issues
            },
            evidence=evidence
        )
    
    def _check_data_uniformity(self, leads: List[RestaurantLead]) -> List[str]:
        """Check for suspicious uniformity that suggests generated data"""
        issues = []
        
        if len(leads) < 2:
            return issues
        
        # Check email domain uniformity
        email_domains = [lead.email.split('@')[1].lower() if '@' in lead.email else '' for lead in leads if lead.email]
        if email_domains:
            domain_counts = {}
            for domain in email_domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            # Check if too many leads share the same domain
            max_domain_count = max(domain_counts.values())
            if max_domain_count / len(email_domains) > 0.7:  # More than 70% same domain
                most_common_domain = max(domain_counts, key=domain_counts.get)
                issues.append(f"Suspicious uniformity: {max_domain_count}/{len(email_domains)} emails share domain {most_common_domain}")
        
        # Check phone area code uniformity
        area_codes = []
        for lead in leads:
            if lead.phone:
                phone_clean = re.sub(r'[^\d]', '', lead.phone)
                if len(phone_clean) >= 10:
                    area_code = phone_clean[-10:-7] if len(phone_clean) == 11 else phone_clean[:3]
                    area_codes.append(area_code)
        
        if area_codes:
            unique_area_codes = set(area_codes)
            if len(unique_area_codes) == 1 and len(area_codes) > 10:
                issues.append(f"Suspicious uniformity: All {len(area_codes)} phone numbers share area code {list(unique_area_codes)[0]}")
        
        return issues
    
    def _check_lead_technical_debt(self, lead: RestaurantLead, index: int) -> List[str]:
        """Check a single lead for technical debt indicators"""
        issues = []
        
        # Check all text fields for debt patterns
        text_fields = {
            'name': lead.name,
            'address': lead.address,
            'email': lead.email,
            'website': lead.website,
            'cuisine_type': lead.cuisine_type
        }
        
        for field_name, field_value in text_fields.items():
            if not field_value:
                continue
                
            # Check for mock/test patterns
            for pattern in self.debt_patterns['mock_data']:
                if pattern.search(field_value):
                    issues.append(f"Mock data pattern in {field_name}: {pattern.pattern}")
            
            # Check for implementation shortcuts
            for pattern in self.debt_patterns['implementation_shortcuts']:
                if pattern.match(field_value):
                    issues.append(f"Implementation shortcut in {field_name}: {field_value}")
        
        return issues
    
    def _check_generation_patterns(self, leads: List[RestaurantLead]) -> List[str]:
        """Check for patterns that suggest data was generated rather than scraped"""
        issues = []
        
        # Check for sequential naming
        names = [lead.name for lead in leads if lead.name]
        sequential_count = 0
        for name in names:
            if re.search(r'(Restaurant|Cafe|Diner)\s*\d+$', name):
                sequential_count += 1
        
        if sequential_count > 3:  # More than 3 sequential names
            issues.append(f"Sequential naming pattern detected in {sequential_count} leads")
        
        # Check for too-perfect formatting
        perfect_phone_count = 0
        for lead in leads:
            if lead.phone and re.match(r'^\(\d{3}\)\s\d{3}-\d{4}$', lead.phone):
                perfect_phone_count += 1
        
        if perfect_phone_count > len(leads) * 0.8:  # More than 80% perfect formatting
            issues.append(f"Suspiciously uniform phone formatting in {perfect_phone_count}/{len(leads)} leads")
        
        return issues


class RestaurantValidationFramework:
    """
    Comprehensive validation framework for restaurant lead generation
    
    Orchestrates all validation components to provide comprehensive
    authenticity checking with zero tolerance for fake data.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT, config: Dict[str, Any] = None):
        self.validation_level = validation_level
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.RestaurantValidationFramework")
        
        # Initialize all validators
        self.business_validator = RestaurantBusinessValidator(self.config.get('business', {}))
        self.location_validator = SantaMonicaGeographicValidator(self.config.get('location', {}))
        self.phone_validator = PhoneNumberValidator(self.config.get('phone', {}))
        self.email_validator = EmailDomainValidator(self.config.get('email', {}))
        self.debt_monitor = TechnicalDebtMonitor(self.config.get('debt_monitor', {}))
        
        # Validation history
        self.validation_history: List[Dict[str, Any]] = []
        
        # Thresholds based on validation level
        self.score_thresholds = {
            ValidationLevel.STRICT: {'pass': 0.8, 'warning': 0.6},
            ValidationLevel.NORMAL: {'pass': 0.7, 'warning': 0.5},
            ValidationLevel.PERMISSIVE: {'pass': 0.6, 'warning': 0.4}
        }
        
        self.logger.info(f"RestaurantValidationFramework initialized with {validation_level.value} validation level")
    
    def validate_lead(self, lead: RestaurantLead) -> RestaurantLead:
        """
        Perform comprehensive validation on a single restaurant lead
        
        Args:
            lead: RestaurantLead object to validate
            
        Returns:
            Updated RestaurantLead with validation results
        """
        start_time = time.time()
        
        self.logger.info(f"Starting validation for lead: {lead.name}")
        
        # Run all validations
        validations = {
            'business_authenticity': self.business_validator.validate_restaurant_authenticity(lead),
            'santa_monica_location': self.location_validator.validate_santa_monica_location(lead),
            'phone_validation': self.phone_validator.validate_phone_number(lead),
            'email_domain': self.email_validator.validate_email_domain(lead)
        }
        
        # Add validation results to lead
        for validation_type, result in validations.items():
            lead.add_validation_result(result)
            self.logger.debug(f"{validation_type}: {result.status.value} (score: {result.score:.2f})")
        
        # Apply validation level thresholds
        self._apply_validation_thresholds(lead)
        
        validation_time = time.time() - start_time
        
        # Record in history
        self.validation_history.append({
            'timestamp': datetime.now().isoformat(),
            'lead_name': lead.name,
            'overall_score': lead.overall_score,
            'is_authentic': lead.is_authentic,
            'validation_time': validation_time,
            'validations': {k: v.status.value for k, v in validations.items()}
        })
        
        self.logger.info(f"Validation completed for {lead.name}: score={lead.overall_score:.2f}, authentic={lead.is_authentic}, time={validation_time:.2f}s")
        
        return lead
    
    def validate_lead_batch(self, leads: List[RestaurantLead]) -> List[RestaurantLead]:
        """
        Validate a batch of restaurant leads with additional cross-lead analysis
        
        Args:
            leads: List of RestaurantLead objects to validate
            
        Returns:
            List of validated RestaurantLead objects
        """
        if not leads:
            self.logger.warning("Empty leads list provided for batch validation")
            return []
        
        self.logger.info(f"Starting batch validation for {len(leads)} leads")
        start_time = time.time()
        
        # Validate individual leads first
        validated_leads = []
        for lead in leads:
            validated_lead = self.validate_lead(lead)
            validated_leads.append(validated_lead)
        
        # Run technical debt monitoring on the batch
        debt_result = self.debt_monitor.monitor_lead_data(validated_leads)
        
        # Apply debt monitoring results to all leads
        for lead in validated_leads:
            lead.add_validation_result(debt_result)
        
        # Filter leads based on validation level
        final_leads = self._filter_leads_by_authenticity(validated_leads)
        
        batch_time = time.time() - start_time
        
        self.logger.info(f"Batch validation completed: {len(final_leads)}/{len(leads)} leads passed validation "
                        f"(time: {batch_time:.2f}s)")
        
        return final_leads
    
    def _apply_validation_thresholds(self, lead: RestaurantLead):
        """Apply validation level thresholds to determine final authenticity"""
        thresholds = self.score_thresholds[self.validation_level]
        
        # Check for any FAKE quality results (zero tolerance)
        has_fake_data = any(result.quality == DataQuality.FAKE for result in lead.validation_results)
        
        if has_fake_data:
            lead.is_authentic = False
            self.logger.warning(f"Lead {lead.name} marked as inauthentic due to fake data detection")
        elif lead.overall_score >= thresholds['pass']:
            lead.is_authentic = True
        elif lead.overall_score < thresholds['warning'] and self.validation_level == ValidationLevel.STRICT:
            lead.is_authentic = False
        # For NORMAL and PERMISSIVE levels, leads between warning and pass thresholds remain as-is
    
    def _filter_leads_by_authenticity(self, leads: List[RestaurantLead]) -> List[RestaurantLead]:
        """Filter leads based on authenticity requirements"""
        if self.validation_level == ValidationLevel.PERMISSIVE:
            # Return all leads, even suspicious ones
            return leads
        
        # For STRICT and NORMAL, only return authentic leads
        authentic_leads = [lead for lead in leads if lead.is_authentic]
        
        filtered_count = len(leads) - len(authentic_leads)
        if filtered_count > 0:
            self.logger.info(f"Filtered out {filtered_count} inauthentic leads")
        
        return authentic_leads
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        if not self.validation_history:
            return {'error': 'No validation history available'}
        
        total_validations = len(self.validation_history)
        authentic_count = sum(1 for v in self.validation_history if v['is_authentic'])
        
        # Calculate average scores
        avg_score = sum(v['overall_score'] for v in self.validation_history) / total_validations
        avg_time = sum(v['validation_time'] for v in self.validation_history) / total_validations
        
        # Quality distribution
        quality_counts = {'authentic': authentic_count, 'rejected': total_validations - authentic_count}
        
        # Common validation failures
        failure_patterns = {}
        for validation in self.validation_history:
            for validation_type, status in validation['validations'].items():
                if status != 'pass':
                    failure_patterns[validation_type] = failure_patterns.get(validation_type, 0) + 1
        
        return {
            'validation_summary': {
                'total_leads_validated': total_validations,
                'authentic_leads': authentic_count,
                'rejection_rate': (total_validations - authentic_count) / total_validations,
                'average_score': avg_score,
                'average_validation_time': avg_time
            },
            'validation_level': self.validation_level.value,
            'quality_distribution': quality_counts,
            'common_failures': failure_patterns,
            'score_thresholds': self.score_thresholds[self.validation_level],
            'recent_validations': self.validation_history[-10:] if len(self.validation_history) > 10 else self.validation_history
        }
    
    def save_validation_evidence(self, filepath: str):
        """Save detailed validation evidence to file"""
        evidence_data = {
            'framework_config': {
                'validation_level': self.validation_level.value,
                'thresholds': self.score_thresholds[self.validation_level],
                'timestamp': datetime.now().isoformat()
            },
            'validation_history': self.validation_history,
            'validation_report': self.get_validation_report()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(evidence_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Validation evidence saved to {filepath}")
    
    def export_validated_leads(self, leads: List[RestaurantLead], filepath: str):
        """Export validated leads with full validation details"""
        export_data = []
        
        for lead in leads:
            lead_data = {
                'name': lead.name,
                'address': lead.address,
                'phone': lead.phone,
                'email': lead.email,
                'website': lead.website,
                'cuisine_type': lead.cuisine_type,
                'price_range': lead.price_range,
                'rating': lead.rating,
                'source_url': lead.source_url,
                'validation_summary': {
                    'overall_score': lead.overall_score,
                    'is_authentic': lead.is_authentic,
                    'validation_timestamp': lead.validation_timestamp,
                    'validation_count': len(lead.validation_results)
                },
                'validation_details': [
                    {
                        'status': result.status.value,
                        'quality': result.quality.value,
                        'score': result.score,
                        'message': result.message,
                        'evidence': result.evidence,
                        'timestamp': result.timestamp
                    }
                    for result in lead.validation_results
                ]
            }
            export_data.append(lead_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Validated leads exported to {filepath}")


# Convenience functions for easy usage

def validate_santa_monica_restaurants(leads_data: List[Dict[str, str]], 
                                    validation_level: str = "strict") -> Tuple[List[RestaurantLead], Dict[str, Any]]:
    """
    Convenience function to validate restaurant leads for Santa Monica
    
    Args:
        leads_data: List of dictionaries containing restaurant data
        validation_level: "strict", "normal", or "permissive"
    
    Returns:
        Tuple of (validated_leads, validation_report)
    """
    # Convert dictionaries to RestaurantLead objects
    leads = []
    for data in leads_data:
        lead = RestaurantLead(
            name=data.get('name', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            website=data.get('website', ''),
            cuisine_type=data.get('cuisine_type', ''),
            price_range=data.get('price_range', ''),
            rating=float(data.get('rating', 0)),
            source_url=data.get('source_url', '')
        )
        leads.append(lead)
    
    # Initialize validation framework
    framework = RestaurantValidationFramework(ValidationLevel(validation_level))
    
    # Validate leads
    validated_leads = framework.validate_lead_batch(leads)
    
    # Get report
    report = framework.get_validation_report()
    
    return validated_leads, report


def create_validation_checkpoint(checkpoint_name: str, leads: List[RestaurantLead], 
                               framework: RestaurantValidationFramework):
    """
    Create a validation checkpoint for monitoring progress
    
    Args:
        checkpoint_name: Name for this validation checkpoint
        leads: Current leads being validated
        framework: ValidationFramework instance
    """
    checkpoint_data = {
        'checkpoint_name': checkpoint_name,
        'timestamp': datetime.now().isoformat(),
        'leads_count': len(leads),
        'authentic_count': sum(1 for lead in leads if lead.is_authentic),
        'validation_report': framework.get_validation_report(),
        'sample_leads': [
            {
                'name': lead.name,
                'overall_score': lead.overall_score,
                'is_authentic': lead.is_authentic,
                'validation_count': len(lead.validation_results)
            }
            for lead in leads[:5]  # Sample first 5 leads
        ]
    }
    
    checkpoint_file = f"validation_checkpoint_{checkpoint_name}_{int(time.time())}.json"
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, indent=2)
    
    logging.getLogger(__name__).info(f"Validation checkpoint '{checkpoint_name}' saved to {checkpoint_file}")
    
    return checkpoint_file


class FakeDataDetector:
    """Specialized detector for fake restaurant data patterns"""
    
    def __init__(self):
        self.fake_patterns = {
            'names': [
                r'^(test|sample|example|demo|fake|mock|temp)\s+restaurant',
                r'^restaurant\s*\d+$',
                r'^(cafe|diner|eatery)\s*\d+$',
                r'placeholder|lorem ipsum'
            ],
            'addresses': [
                r'^(123|456|789)\s+(main|test|sample)\s+(st|street)',
                r'test\s+(street|ave|blvd)',
                r'placeholder\s+address',
                r'example\s+(street|ave|blvd)'
            ],
            'phones': [
                r'555-?\d{4}',
                r'\d{3}-?1234',
                r'\d{3}-?0000',
                r'000-?\d{3}-?\d{4}'
            ],
            'emails': [
                r'(test|fake|example|noreply)@',
                r'@(test|example|localhost)\.com',
                r'placeholder@'
            ]
        }
        
        # Compile patterns
        for category in self.fake_patterns:
            self.fake_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in self.fake_patterns[category]
            ]
    
    def is_authentic_restaurant(self, lead: RestaurantLead) -> bool:
        """Check if restaurant data appears authentic"""
        fake_indicators = self.get_fake_indicators(lead)
        return len(fake_indicators) == 0
    
    def get_fake_indicators(self, lead: RestaurantLead) -> List[str]:
        """Get list of fake data indicators for a lead"""
        indicators = []
        
        # Check name
        if lead.name:
            for pattern in self.fake_patterns['names']:
                if pattern.search(lead.name):
                    indicators.append(f"Fake name pattern: {pattern.pattern}")
        
        # Check address
        if lead.address:
            for pattern in self.fake_patterns['addresses']:
                if pattern.search(lead.address):
                    indicators.append(f"Fake address pattern: {pattern.pattern}")
        
        # Check phone
        if lead.phone:
            for pattern in self.fake_patterns['phones']:
                if pattern.search(lead.phone):
                    indicators.append(f"Fake phone pattern: {pattern.pattern}")
        
        # Check email
        if lead.email:
            for pattern in self.fake_patterns['emails']:
                if pattern.search(lead.email):
                    indicators.append(f"Fake email pattern: {pattern.pattern}")
        
        return indicators


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Sample test data
    test_leads = [
        {
            'name': 'Boa Steakhouse',
            'address': '101 Santa Monica Blvd, Santa Monica, CA 90401',
            'phone': '(310) 899-4466',
            'email': 'info@boasteakhouse.com',
            'website': 'https://boasteakhouse.com',
            'cuisine_type': 'American'
        },
        {
            'name': 'Test Restaurant 123',  # Should be flagged as fake
            'address': '123 Test St, Santa Monica, CA 90401',
            'phone': '(555) 123-4567',  # Should be flagged as fake
            'email': 'test@example.com',  # Should be flagged as fake
            'website': 'http://test.example.com'
        }
    ]
    
    # Validate with strict mode
    validated_leads, report = validate_santa_monica_restaurants(test_leads, "strict")
    
    print(f"Validation complete: {len(validated_leads)}/{len(test_leads)} leads passed validation")
    print(f"Rejection rate: {report['validation_summary']['rejection_rate']:.1%}")