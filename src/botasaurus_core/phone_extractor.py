"""
Advanced Phone Number Extraction System for Botasaurus Business Scraper
TASK-D003: Comprehensive phone number extraction and validation

Provides robust phone number extraction with:
- Multi-format pattern recognition (US/International)
- Obfuscation pattern handling (text to numbers)
- Context-aware business/personal classification
- Confidence scoring and validation
- Integration with BusinessLead models
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json


class PhoneType(Enum):
    """Phone number types"""
    BUSINESS = "business"
    PERSONAL = "personal"
    TOLL_FREE = "toll_free"
    FAX = "fax"
    MOBILE = "mobile"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence levels for phone extraction"""
    HIGH = "high"           # 90-100%
    MEDIUM = "medium"       # 70-89%
    LOW = "low"            # 50-69%
    VERY_LOW = "very_low"  # <50%


@dataclass
class PhoneCandidate:
    """Individual phone number candidate with metadata"""
    raw_text: str                    # Original text found
    formatted_number: str = ""       # Standardized format
    country_code: str = "1"         # Default US
    area_code: str = ""
    exchange: str = ""
    number: str = ""
    extension: str = ""
    
    # Context information
    context_text: str = ""
    context_keywords: List[str] = field(default_factory=list)
    source_page: str = ""
    extraction_method: str = "regex"
    
    # Classification
    phone_type: PhoneType = PhoneType.UNKNOWN
    is_toll_free: bool = False
    is_international: bool = False
    
    # Quality metrics
    confidence_score: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW
    validation_status: str = "pending"
    
    # Metadata
    extraction_timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'raw_text': self.raw_text,
            'formatted_number': self.formatted_number,
            'country_code': self.country_code,
            'area_code': self.area_code,
            'exchange': self.exchange,
            'number': self.number,
            'extension': self.extension,
            'context_text': self.context_text,
            'context_keywords': self.context_keywords,
            'source_page': self.source_page,
            'extraction_method': self.extraction_method,
            'phone_type': self.phone_type.value,
            'is_toll_free': self.is_toll_free,
            'is_international': self.is_international,
            'confidence_score': self.confidence_score,
            'confidence_level': self.confidence_level.value,
            'validation_status': self.validation_status,
            'extraction_timestamp': self.extraction_timestamp
        }


@dataclass
class PhoneExtractionResult:
    """Result of phone number extraction from a page or content"""
    source_url: str
    candidates: List[PhoneCandidate] = field(default_factory=list)
    primary_phone: Optional[PhoneCandidate] = None
    secondary_phones: List[PhoneCandidate] = field(default_factory=list)
    
    # Statistics
    total_found: int = 0
    high_confidence_count: int = 0
    business_phone_count: int = 0
    toll_free_count: int = 0
    
    # Performance
    extraction_time_ms: float = 0.0
    patterns_used: List[str] = field(default_factory=list)
    
    # Errors
    extraction_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'source_url': self.source_url,
            'candidates': [c.to_dict() for c in self.candidates],
            'primary_phone': self.primary_phone.to_dict() if self.primary_phone else None,
            'secondary_phones': [c.to_dict() for c in self.secondary_phones],
            'total_found': self.total_found,
            'high_confidence_count': self.high_confidence_count,
            'business_phone_count': self.business_phone_count,
            'toll_free_count': self.toll_free_count,
            'extraction_time_ms': self.extraction_time_ms,
            'patterns_used': self.patterns_used,
            'extraction_errors': self.extraction_errors
        }


class PhoneExtractor:
    """
    Advanced phone number extraction system with comprehensive pattern recognition
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize phone extractor with configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Compile regex patterns for performance
        self._compile_patterns()
        
        # Valid US area codes for validation
        self.valid_area_codes = self._load_valid_area_codes()
        
        # Text-to-number mappings for obfuscation
        self.text_to_number = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'oh': '0', 'nil': '0'
        }
        
        # Context keywords for classification
        self.business_keywords = {
            'office', 'business', 'company', 'corporate', 'headquarters', 'hq',
            'main', 'reception', 'customer', 'sales', 'support', 'service',
            'contact', 'phone', 'call', 'telephone', 'tel', 'direct', 'line'
        }
        
        self.personal_keywords = {
            'personal', 'private', 'home', 'cell', 'mobile', 'cellular'
        }
        
        self.fax_keywords = {
            'fax', 'facsimile', 'telefax'
        }
        
        # Statistics tracking
        self.stats = {
            'total_extractions': 0,
            'total_candidates': 0,
            'pattern_usage': {},
            'avg_extraction_time': 0.0,
            'validation_accuracy': 0.0
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the phone extractor"""
        logger = logging.getLogger(f"{__name__}.PhoneExtractor")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _compile_patterns(self):
        """Compile regex patterns for phone number extraction"""
        
        # Standard US phone number patterns
        # Note: Using relaxed patterns for testing with 555 numbers
        self.us_patterns = {
            'standard_parens': re.compile(
                r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})(?:\s?(?:ext?\.?|extension|x)\s?(\d{1,5}))?',
                re.IGNORECASE
            ),
            'dots_dashes': re.compile(
                r'(\d{3})[-.](\d{3})[-.](\d{4})(?:\s?(?:ext?\.?|extension|x)\s?(\d{1,5}))?',
                re.IGNORECASE
            ),
            'spaces_only': re.compile(
                r'(\d{3})\s+(\d{3})\s+(\d{4})(?:\s+(?:ext?\.?|extension|x)\s+(\d{1,5}))?',
                re.IGNORECASE
            ),
            'digits_only': re.compile(
                r'\b(?:1)?(\d{3})(\d{3})(\d{4})\b'
            ),
            'tel_links': re.compile(
                r'tel:(?:\+?1[-.\s]?)?(?:\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4}))',
                re.IGNORECASE
            )
        }
        
        # International patterns
        self.international_patterns = {
            'plus_format': re.compile(
                r'\+(\d{1,4})[-.\s]?(?:\(?(\d{1,4})\)?[-.\s]?)?(\d{1,4})[-.\s]?(\d{1,4})(?:[-.\s]?(\d{1,4}))?',
                re.IGNORECASE
            ),
            'country_code': re.compile(
                r'\b00(\d{1,4})[-.\s]?(?:\(?(\d{1,4})\)?[-.\s]?)?(\d{1,4})[-.\s]?(\d{1,4})(?:[-.\s]?(\d{1,4}))?\b',
                re.IGNORECASE
            )
        }
        
        # Obfuscated patterns (text-based)
        self.obfuscated_patterns = {
            'word_numbers': re.compile(
                r'\b(?:(?:one|two|three|four|five|six|seven|eight|nine|zero|oh)\s*){7,}(?:(?:one|two|three|four|five|six|seven|eight|nine|zero|oh))\b',
                re.IGNORECASE
            ),
            'mixed_format': re.compile(
                r'\b(?:\(?(?:(?:\d|one|two|three|four|five|six|seven|eight|nine|zero|oh)\s*){3}\)?[-.\s]?(?:(?:\d|one|two|three|four|five|six|seven|eight|nine|zero|oh)\s*){3}[-.\s]?(?:(?:\d|one|two|three|four|five|six|seven|eight|nine|zero|oh)\s*){4})\b',
                re.IGNORECASE
            ),
            'dot_space_separator': re.compile(
                r'\b([2-9]\d{2})(?:\s*[.]\s*)([2-9]\d{2})(?:\s*[.]\s*)(\d{4})\b'
            )
        }
        
        # JavaScript/encoded patterns
        self.encoded_patterns = {
            'javascript_encoded': re.compile(
                r'javascript[^"\']*["\'](?:[^"\']*)?(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})',
                re.IGNORECASE
            ),
            'html_entities': re.compile(
                r'&#(\d+);&#(\d+);&#(\d+);[^\d]*&#(\d+);&#(\d+);&#(\d+);[^\d]*&#(\d+);&#(\d+);&#(\d+);&#(\d+);'
            )
        }
    
    def _load_valid_area_codes(self) -> Set[str]:
        """Load valid US area codes for validation"""
        # Common valid US area codes
        valid_codes = {
            '201', '202', '203', '205', '206', '207', '208', '209', '210', '212',
            '213', '214', '215', '216', '217', '218', '219', '224', '225', '228',
            '229', '231', '234', '239', '240', '248', '251', '252', '253', '254',
            '256', '260', '262', '267', '269', '270', '276', '281', '283', '301',
            '302', '303', '304', '305', '307', '308', '309', '310', '312', '313',
            '314', '315', '316', '317', '318', '319', '320', '321', '323', '325',
            '330', '331', '334', '336', '337', '339', '340', '347', '351', '352',
            '360', '361', '364', '369', '380', '385', '386', '401', '402', '404',
            '405', '406', '407', '408', '409', '410', '412', '413', '414', '415',
            '417', '419', '423', '424', '425', '430', '432', '434', '435', '440',
            '442', '443', '445', '458', '469', '470', '475', '478', '479', '480',
            '484', '501', '502', '503', '504', '505', '507', '508', '509', '510',
            '512', '513', '515', '516', '517', '518', '520', '530', '540', '541',
            '551', '559', '561', '562', '563', '564', '567', '570', '571', '573',
            '574', '575', '580', '585', '586', '601', '602', '603', '605', '606',
            '607', '608', '609', '610', '612', '614', '615', '616', '617', '618',
            '619', '620', '623', '626', '628', '630', '631', '636', '641', '646',
            '650', '651', '657', '660', '661', '662', '667', '669', '678', '681',
            '682', '701', '702', '703', '704', '706', '707', '708', '712', '713',
            '714', '715', '716', '717', '718', '719', '720', '724', '727', '731',
            '732', '734', '737', '740', '747', '754', '757', '760', '762', '763',
            '765', '770', '772', '773', '774', '775', '781', '785', '786', '801',
            '802', '803', '804', '805', '806', '808', '810', '812', '813', '814',
            '815', '816', '817', '818', '828', '830', '831', '832', '843', '845',
            '847', '848', '850', '856', '857', '858', '859', '860', '862', '863',
            '864', '865', '870', '872', '878', '901', '903', '904', '906', '907',
            '908', '909', '910', '912', '913', '914', '915', '916', '917', '918',
            '919', '920', '925', '928', '929', '930', '931', '934', '936', '937',
            '940', '941', '947', '949', '951', '952', '954', '956', '959', '970',
            '971', '972', '973', '978', '979', '980', '984', '985', '989'
        }
        
        return valid_codes
    
    def extract_from_text(self, 
                         text: str, 
                         source_url: str = "",
                         context_size: int = 50) -> PhoneExtractionResult:
        """
        Extract phone numbers from plain text
        
        Args:
            text: Text content to extract from
            source_url: Source URL for tracking
            context_size: Characters of context to capture around matches
            
        Returns:
            PhoneExtractionResult with all found candidates
        """
        start_time = time.time()
        result = PhoneExtractionResult(source_url=source_url)
        
        try:
            self.logger.info(f"Starting phone extraction from text ({len(text)} chars)")
            
            # Extract using different pattern groups
            candidates = []
            
            # Standard US patterns
            candidates.extend(self._extract_with_patterns(
                text, self.us_patterns, "us_standard", context_size
            ))
            
            # International patterns
            candidates.extend(self._extract_with_patterns(
                text, self.international_patterns, "international", context_size
            ))
            
            # Obfuscated patterns
            candidates.extend(self._extract_obfuscated_numbers(
                text, context_size
            ))
            
            # JavaScript/encoded patterns
            candidates.extend(self._extract_with_patterns(
                text, self.encoded_patterns, "encoded", context_size
            ))
            
            # Process and validate candidates
            result.candidates = self._process_candidates(candidates, source_url)
            result.total_found = len(result.candidates)
            
            # Classify and score candidates
            self._classify_and_score_candidates(result.candidates)
            
            # Select primary and secondary phones
            self._select_primary_secondary(result)
            
            # Update statistics
            result.high_confidence_count = len([c for c in result.candidates 
                                              if c.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]])
            result.business_phone_count = len([c for c in result.candidates 
                                             if c.phone_type == PhoneType.BUSINESS])
            result.toll_free_count = len([c for c in result.candidates if c.is_toll_free])
            
            result.extraction_time_ms = (time.time() - start_time) * 1000
            
            # Update global stats
            self._update_stats(result)
            
            self.logger.info(f"Phone extraction completed: {result.total_found} candidates found")
            
        except Exception as e:
            error_msg = f"Phone extraction failed: {str(e)}"
            self.logger.error(error_msg)
            result.extraction_errors.append(error_msg)
            result.extraction_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def extract_from_html(self, 
                         html_content: str, 
                         source_url: str = "") -> PhoneExtractionResult:
        """
        Extract phone numbers from HTML content
        
        Args:
            html_content: HTML content to extract from
            source_url: Source URL for tracking
            
        Returns:
            PhoneExtractionResult with all found candidates
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract text content for text-based extraction
            text_content = soup.get_text(separator=' ', strip=True)
            
            # First, extract from text content
            result = self.extract_from_text(text_content, source_url)
            
            # Additional HTML-specific extraction
            html_candidates = []
            
            # Extract from tel: links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('tel:'):
                    phone_text = href[4:]  # Remove 'tel:'
                    candidate = self._parse_phone_candidate(
                        phone_text, phone_text, "tel_link", source_url
                    )
                    if candidate:
                        # Get context from link text
                        link_text = link.get_text(strip=True)
                        candidate.context_text = link_text
                        html_candidates.append(candidate)
            
            # Extract from data attributes
            for element in soup.find_all(attrs={"data-phone": True}):
                phone_text = element.get('data-phone', '')
                if phone_text:
                    candidate = self._parse_phone_candidate(
                        phone_text, phone_text, "data_attribute", source_url
                    )
                    if candidate:
                        candidate.context_text = element.get_text(strip=True)[:100]
                        html_candidates.append(candidate)
            
            # Process HTML-specific candidates
            if html_candidates:
                processed_html_candidates = self._process_candidates(html_candidates, source_url)
                self._classify_and_score_candidates(processed_html_candidates)
                
                # Merge with text-based results
                all_candidates = result.candidates + processed_html_candidates
                
                # Deduplicate
                result.candidates = self._deduplicate_candidates(all_candidates)
                result.total_found = len(result.candidates)
                
                # Re-select primary/secondary
                self._select_primary_secondary(result)
            
            return result
            
        except Exception as e:
            error_msg = f"HTML phone extraction failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Fall back to text extraction
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text(separator=' ', strip=True)
                result = self.extract_from_text(text_content, source_url)
                result.extraction_errors.append(f"HTML extraction failed, used text fallback: {error_msg}")
                return result
            except:
                return PhoneExtractionResult(source_url=source_url, extraction_errors=[error_msg])
    
    def _extract_with_patterns(self, 
                              text: str, 
                              patterns: Dict[str, re.Pattern], 
                              method: str,
                              context_size: int) -> List[PhoneCandidate]:
        """Extract phone numbers using regex patterns"""
        candidates = []
        
        for pattern_name, pattern in patterns.items():
            matches = pattern.finditer(text)
            
            for match in matches:
                # Get context around match
                start = max(0, match.start() - context_size)
                end = min(len(text), match.end() + context_size)
                context = text[start:end].strip()
                
                # Create candidate
                candidate = PhoneCandidate(
                    raw_text=match.group(0),
                    context_text=context,
                    extraction_method=f"{method}_{pattern_name}"
                )
                
                # Parse phone number components
                groups = match.groups()
                if len(groups) >= 3:
                    candidate.area_code = groups[0] or ""
                    candidate.exchange = groups[1] or ""
                    candidate.number = groups[2] or ""
                    if len(groups) > 3 and groups[3]:
                        candidate.extension = groups[3]
                
                candidates.append(candidate)
                
                # Track pattern usage
                if pattern_name not in self.stats['pattern_usage']:
                    self.stats['pattern_usage'][pattern_name] = 0
                self.stats['pattern_usage'][pattern_name] += 1
        
        return candidates
    
    def _extract_obfuscated_numbers(self, text: str, context_size: int) -> List[PhoneCandidate]:
        """Extract obfuscated phone numbers (text-based)"""
        candidates = []
        
        # Find word-based numbers
        word_pattern = self.obfuscated_patterns['word_numbers']
        matches = word_pattern.finditer(text)
        
        for match in matches:
            raw_text = match.group(0)
            
            # Convert words to numbers
            converted = self._convert_words_to_numbers(raw_text)
            
            if converted and len(converted) >= 10:
                # Get context
                start = max(0, match.start() - context_size)
                end = min(len(text), match.end() + context_size)
                context = text[start:end].strip()
                
                candidate = PhoneCandidate(
                    raw_text=raw_text,
                    context_text=context,
                    extraction_method="obfuscated_words"
                )
                
                # Parse converted number
                if len(converted) == 10:
                    candidate.area_code = converted[:3]
                    candidate.exchange = converted[3:6]
                    candidate.number = converted[6:10]
                elif len(converted) == 11 and converted[0] == '1':
                    candidate.country_code = "1"
                    candidate.area_code = converted[1:4]
                    candidate.exchange = converted[4:7]
                    candidate.number = converted[7:11]
                
                candidates.append(candidate)
        
        return candidates
    
    def _convert_words_to_numbers(self, text: str) -> str:
        """Convert word-based numbers to digits"""
        words = text.lower().split()
        converted = ""
        
        for word in words:
            word = word.strip('.,!?();:')
            if word in self.text_to_number:
                converted += self.text_to_number[word]
            elif word.isdigit():
                converted += word
        
        return converted
    
    def _parse_phone_candidate(self, 
                              raw_text: str, 
                              phone_text: str, 
                              method: str, 
                              source_url: str) -> Optional[PhoneCandidate]:
        """Parse a phone text into a candidate"""
        try:
            # Clean up the phone text
            digits = re.sub(r'[^\d]', '', phone_text)
            
            if len(digits) < 10:
                return None
            
            candidate = PhoneCandidate(
                raw_text=raw_text,
                extraction_method=method,
                source_page=source_url
            )
            
            # Parse digits into components
            if len(digits) == 10:
                candidate.area_code = digits[:3]
                candidate.exchange = digits[3:6]
                candidate.number = digits[6:10]
            elif len(digits) == 11 and digits[0] == '1':
                candidate.country_code = "1"
                candidate.area_code = digits[1:4]
                candidate.exchange = digits[4:7]
                candidate.number = digits[7:11]
            elif len(digits) > 11:
                # Might be international
                candidate.country_code = digits[:-10]
                candidate.area_code = digits[-10:-7]
                candidate.exchange = digits[-7:-4]
                candidate.number = digits[-4:]
                candidate.is_international = True
            
            return candidate
            
        except Exception as e:
            self.logger.debug(f"Failed to parse phone candidate '{phone_text}': {e}")
            return None
    
    def _process_candidates(self, 
                           candidates: List[PhoneCandidate], 
                           source_url: str) -> List[PhoneCandidate]:
        """Process and validate phone candidates"""
        processed = []
        
        for candidate in candidates:
            # Set source URL
            candidate.source_page = source_url
            
            # Format the phone number
            candidate.formatted_number = self._format_phone_number(candidate)
            
            # Validate the phone number
            if self._validate_phone_number(candidate):
                candidate.validation_status = "valid"
                processed.append(candidate)
            else:
                candidate.validation_status = "invalid"
                # Still include for completeness but with low confidence
                candidate.confidence_score = 0.1
                processed.append(candidate)
        
        return processed
    
    def _format_phone_number(self, candidate: PhoneCandidate) -> str:
        """Format phone number in standard format"""
        if candidate.area_code and candidate.exchange and candidate.number:
            base_format = f"({candidate.area_code}) {candidate.exchange}-{candidate.number}"
            
            if candidate.extension:
                base_format += f" ext. {candidate.extension}"
            
            if candidate.country_code and candidate.country_code != "1":
                base_format = f"+{candidate.country_code} {base_format}"
            
            return base_format
        
        # Fallback - clean up raw text
        digits = re.sub(r'[^\d]', '', candidate.raw_text)
        if len(digits) >= 10:
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"
            elif len(digits) == 11 and digits[0] == '1':
                return f"({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
        
        return candidate.raw_text
    
    def _validate_phone_number(self, candidate: PhoneCandidate) -> bool:
        """Validate phone number"""
        # Check area code validity for US numbers
        if candidate.country_code == "1" or not candidate.is_international:
            if candidate.area_code not in self.valid_area_codes:
                return False
            
            # Check for invalid patterns
            if candidate.area_code[0] in ['0', '1']:
                return False
            
            if candidate.exchange and candidate.exchange[0] in ['0', '1']:
                return False
        
        # Check for fake numbers
        digits = re.sub(r'[^\d]', '', candidate.formatted_number or candidate.raw_text)
        if self._is_fake_number(digits):
            return False
        
        return True
    
    def _is_fake_number(self, digits: str) -> bool:
        """Check if number is a common fake/test number"""
        fake_patterns = [
            '5555555555', '1234567890', '0123456789', '9999999999',
            '1111111111', '2222222222', '3333333333', '4444444444',
            '6666666666', '7777777777', '8888888888', '0000000000'
        ]
        
        # Check for repeated digits
        if digits and len(set(digits[-10:])) == 1:
            return True
        
        # Check against known fake patterns
        if digits[-10:] in fake_patterns:
            return True
        
        return False
    
    def _classify_and_score_candidates(self, candidates: List[PhoneCandidate]):
        """Classify phone type and calculate confidence scores"""
        for candidate in candidates:
            # Classify phone type based on context
            candidate.phone_type = self._classify_phone_type(candidate)
            
            # Check if toll-free
            if candidate.area_code in ['800', '888', '877', '866', '855', '844', '833', '822']:
                candidate.is_toll_free = True
                candidate.phone_type = PhoneType.TOLL_FREE
            
            # Calculate confidence score
            candidate.confidence_score = self._calculate_confidence_score(candidate)
            
            # Set confidence level
            if candidate.confidence_score >= 0.9:
                candidate.confidence_level = ConfidenceLevel.HIGH
            elif candidate.confidence_score >= 0.7:
                candidate.confidence_level = ConfidenceLevel.MEDIUM
            elif candidate.confidence_score >= 0.5:
                candidate.confidence_level = ConfidenceLevel.LOW
            else:
                candidate.confidence_level = ConfidenceLevel.VERY_LOW
    
    def _classify_phone_type(self, candidate: PhoneCandidate) -> PhoneType:
        """Classify phone number type based on context"""
        context_lower = candidate.context_text.lower()
        
        # Extract context keywords
        context_words = set(re.findall(r'\b\w+\b', context_lower))
        candidate.context_keywords = list(context_words & 
                                        (self.business_keywords | self.personal_keywords | self.fax_keywords))
        
        # Check for fax
        if any(keyword in context_lower for keyword in self.fax_keywords):
            return PhoneType.FAX
        
        # Check for personal indicators
        if any(keyword in context_lower for keyword in self.personal_keywords):
            return PhoneType.PERSONAL
        
        # Check for business indicators
        if any(keyword in context_lower for keyword in self.business_keywords):
            return PhoneType.BUSINESS
        
        # Default to unknown
        return PhoneType.UNKNOWN
    
    def _calculate_confidence_score(self, candidate: PhoneCandidate) -> float:
        """Calculate confidence score for phone candidate"""
        score = 0.0
        
        # Base score for valid format
        if candidate.validation_status == "valid":
            score += 0.4
        else:
            score += 0.1
        
        # Extraction method scoring
        method_scores = {
            'tel_link': 0.3,
            'us_standard': 0.25,
            'data_attribute': 0.2,
            'international': 0.15,
            'obfuscated': 0.1,
            'encoded': 0.05
        }
        
        for method, method_score in method_scores.items():
            if method in candidate.extraction_method:
                score += method_score
                break
        
        # Context scoring
        context_score = self._score_context(candidate)
        score += context_score * 0.3
        
        # Phone type scoring
        type_scores = {
            PhoneType.BUSINESS: 0.1,
            PhoneType.TOLL_FREE: 0.05,
            PhoneType.PERSONAL: 0.03,
            PhoneType.FAX: 0.02,
            PhoneType.UNKNOWN: 0.0
        }
        score += type_scores.get(candidate.phone_type, 0.0)
        
        return min(1.0, score)
    
    def _score_context(self, candidate: PhoneCandidate) -> float:
        """Score context quality for business relevance"""
        context_lower = candidate.context_text.lower()
        score = 0.0
        
        # Business context indicators
        business_indicators = [
            ('contact', 0.3), ('phone', 0.25), ('call', 0.2), ('office', 0.2),
            ('business', 0.15), ('customer', 0.15), ('service', 0.1), ('sales', 0.1),
            ('support', 0.1), ('main', 0.05), ('reception', 0.05)
        ]
        
        for indicator, weight in business_indicators:
            if indicator in context_lower:
                score += weight
        
        # Negative indicators
        negative_indicators = ['personal', 'private', 'home']
        for indicator in negative_indicators:
            if indicator in context_lower:
                score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _deduplicate_candidates(self, candidates: List[PhoneCandidate]) -> List[PhoneCandidate]:
        """Remove duplicate phone numbers, keeping best quality"""
        unique_phones = {}
        
        for candidate in candidates:
            # Use formatted number as key
            phone_key = re.sub(r'[^\d]', '', candidate.formatted_number)[-10:]  # Last 10 digits
            
            if phone_key not in unique_phones or candidate.confidence_score > unique_phones[phone_key].confidence_score:
                unique_phones[phone_key] = candidate
        
        # Sort by confidence score
        return sorted(unique_phones.values(), key=lambda x: x.confidence_score, reverse=True)
    
    def _select_primary_secondary(self, result: PhoneExtractionResult):
        """Select primary and secondary phone numbers"""
        if not result.candidates:
            return
        
        # Sort by confidence and business relevance
        business_phones = [c for c in result.candidates if c.phone_type == PhoneType.BUSINESS]
        toll_free_phones = [c for c in result.candidates if c.phone_type == PhoneType.TOLL_FREE]
        other_phones = [c for c in result.candidates if c.phone_type not in [PhoneType.BUSINESS, PhoneType.TOLL_FREE, PhoneType.FAX]]
        
        # Primary phone selection priority:
        # 1. Highest confidence business phone
        # 2. Toll-free phone
        # 3. Highest confidence other phone
        
        if business_phones:
            result.primary_phone = max(business_phones, key=lambda x: x.confidence_score)
        elif toll_free_phones:
            result.primary_phone = max(toll_free_phones, key=lambda x: x.confidence_score)
        elif other_phones:
            result.primary_phone = max(other_phones, key=lambda x: x.confidence_score)
        
        # Secondary phones are remaining high-quality numbers
        if result.primary_phone:
            remaining = [c for c in result.candidates if c != result.primary_phone]
            result.secondary_phones = [c for c in remaining if c.confidence_score >= 0.5][:3]  # Max 3 secondary
    
    def _update_stats(self, result: PhoneExtractionResult):
        """Update extraction statistics"""
        self.stats['total_extractions'] += 1
        self.stats['total_candidates'] += result.total_found
        
        # Update average extraction time
        if self.stats['total_extractions'] > 1:
            current_avg = self.stats['avg_extraction_time']
            new_time = result.extraction_time_ms
            self.stats['avg_extraction_time'] = ((current_avg * (self.stats['total_extractions'] - 1)) + new_time) / self.stats['total_extractions']
        else:
            self.stats['avg_extraction_time'] = result.extraction_time_ms
    
    def extract_batch(self, 
                     text_list: List[str], 
                     source_urls: Optional[List[str]] = None,
                     progress_callback: Optional[callable] = None) -> List[PhoneExtractionResult]:
        """
        Extract phone numbers from multiple texts in batch
        
        Args:
            text_list: List of text content to process
            source_urls: Optional list of source URLs
            progress_callback: Optional progress callback function
            
        Returns:
            List of PhoneExtractionResult objects
        """
        results = []
        
        if source_urls is None:
            source_urls = [""] * len(text_list)
        
        for i, (text, url) in enumerate(zip(text_list, source_urls)):
            if progress_callback:
                progress_callback(i, len(text_list), url)
            
            try:
                result = self.extract_from_text(text, url)
                results.append(result)
            except Exception as e:
                error_result = PhoneExtractionResult(
                    source_url=url,
                    extraction_errors=[f"Batch processing error: {str(e)}"]
                )
                results.append(error_result)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return self.stats.copy()
    
    def export_results_csv(self, results: List[PhoneExtractionResult], filename: str):
        """Export extraction results to CSV format"""
        try:
            import csv
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'source_url', 'formatted_number', 'raw_text', 'phone_type', 
                    'confidence_score', 'confidence_level', 'area_code', 'exchange', 
                    'number', 'extension', 'context_text', 'extraction_method',
                    'is_toll_free', 'validation_status'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    for candidate in result.candidates:
                        row = {
                            'source_url': result.source_url,
                            'formatted_number': candidate.formatted_number,
                            'raw_text': candidate.raw_text,
                            'phone_type': candidate.phone_type.value,
                            'confidence_score': candidate.confidence_score,
                            'confidence_level': candidate.confidence_level.value,
                            'area_code': candidate.area_code,
                            'exchange': candidate.exchange,
                            'number': candidate.number,
                            'extension': candidate.extension,
                            'context_text': candidate.context_text[:200],  # Truncate for CSV
                            'extraction_method': candidate.extraction_method,
                            'is_toll_free': candidate.is_toll_free,
                            'validation_status': candidate.validation_status
                        }
                        writer.writerow(row)
            
            self.logger.info(f"Results exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to export results to CSV: {e}")


def test_phone_extractor():
    """Test the phone extractor with sample content"""
    print("Testing Phone Number Extractor")
    print("=" * 50)
    
    # Initialize extractor
    extractor = PhoneExtractor()
    
    # Test text samples
    test_texts = [
        "Contact us at (555) 123-4567 for business inquiries. Fax: (555) 123-4568",
        "Call our office at 555.123.4567 or mobile 555 123 4568 ext. 123",
        "Phone: one two three four five six seven eight nine zero. Office line.",
        "tel:+1-555-123-4567 or visit our website. Customer service: 1-800-555-0123",
        "Invalid numbers: 555-555-5555, 123-456-7890, real: (312) 555-0199"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        print("-" * 40)
        
        result = extractor.extract_from_text(text, f"test_url_{i}")
        
        print(f"Total found: {result.total_found}")
        print(f"High confidence: {result.high_confidence_count}")
        print(f"Business phones: {result.business_phone_count}")
        print(f"Extraction time: {result.extraction_time_ms:.2f}ms")
        
        if result.primary_phone:
            print(f"Primary: {result.primary_phone.formatted_number} "
                  f"(confidence: {result.primary_phone.confidence_score:.2f}, "
                  f"type: {result.primary_phone.phone_type.value})")
        
        for phone in result.candidates[:3]:  # Show top 3
            print(f"  - {phone.formatted_number} "
                  f"[{phone.confidence_level.value}] "
                  f"({phone.extraction_method})")
    
    # Show statistics
    print(f"\nExtractor Statistics:")
    stats = extractor.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return True


if __name__ == "__main__":
    test_phone_extractor()