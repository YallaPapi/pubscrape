"""
Phone Extraction Tool

Agency Swarm tool for extracting phone numbers from HTML content with advanced 
pattern detection, validation, and context scoring. Integrates with the PhoneExtractor
from botasaurus_core.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from pydantic import Field, BaseModel

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool(BaseModel):
        pass

# Import the PhoneExtractor from botasaurus_core
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from botasaurus_core.phone_extractor import PhoneExtractor, PhoneExtractionResult


class PhoneExtractionInput(BaseModel):
    """Input model for phone extraction"""
    html_content: str = Field(
        description="HTML content to extract phone numbers from"
    )
    page_url: str = Field(
        description="URL of the page being processed"
    )
    extraction_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional configuration overrides for extraction"
    )


class PhoneExtractionTool(BaseTool):
    """
    Tool for extracting and scoring phone numbers from HTML content.
    
    Uses advanced pattern detection including US/International formats,
    obfuscated phone detection, and contextual scoring to identify
    high-quality business phone numbers.
    """
    
    name: str = "phone_extraction"
    description: str = "Extract and score phone numbers from HTML content with context analysis"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.phone_extractor = None
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.PhoneExtractionTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _get_phone_extractor(self, config: Optional[Dict[str, Any]] = None) -> PhoneExtractor:
        """Get or create phone extractor with configuration"""
        if self.phone_extractor is None or config:
            self.phone_extractor = PhoneExtractor(config)
        return self.phone_extractor
    
    def run(self, 
            html_content: str,
            page_url: str,
            extraction_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract phone numbers from HTML content.
        
        Args:
            html_content: HTML content to scan for phone numbers
            page_url: URL of the page being processed
            extraction_config: Optional configuration overrides
            
        Returns:
            Dictionary containing extraction results and metadata
        """
        try:
            self.logger.info(f"Starting phone extraction for {page_url}")
            
            # Get phone extractor with configuration
            extractor = self._get_phone_extractor(extraction_config)
            
            # Perform extraction
            result = extractor.extract_from_html(html_content, page_url)
            
            # Format results for return
            formatted_result = {
                'success': True,
                'page_url': result.source_url,
                'total_candidates': result.total_found,
                'high_confidence_count': result.high_confidence_count,
                'business_phone_count': result.business_phone_count,
                'toll_free_count': result.toll_free_count,
                'extraction_time_ms': result.extraction_time_ms,
                'primary_phone': result.primary_phone.to_dict() if result.primary_phone else None,
                'secondary_phones': [phone.to_dict() for phone in result.secondary_phones],
                'all_candidates': [candidate.to_dict() for candidate in result.candidates],
                'patterns_used': result.patterns_used,
                'statistics': extractor.get_statistics(),
                'errors': result.extraction_errors
            }
            
            self.logger.info(
                f"Phone extraction completed for {page_url}: "
                f"{result.total_found} candidates, "
                f"{result.high_confidence_count} high confidence"
            )
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"Phone extraction failed for {page_url}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'page_url': page_url,
                'error': error_msg,
                'total_candidates': 0,
                'high_confidence_count': 0,
                'business_phone_count': 0,
                'toll_free_count': 0,
                'primary_phone': None,
                'secondary_phones': [],
                'all_candidates': []
            }


class BulkPhoneExtractionTool(BaseTool):
    """
    Tool for extracting phone numbers from multiple pages in bulk.
    
    Processes crawl results from the SiteCrawler agent and extracts
    phone numbers from all discovered pages with consolidated reporting.
    """
    
    name: str = "bulk_phone_extraction"
    description: str = "Extract phone numbers from multiple crawled pages with consolidated reporting"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.phone_extractor = None
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.BulkPhoneExtractionTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _get_phone_extractor(self, config: Optional[Dict[str, Any]] = None) -> PhoneExtractor:
        """Get or create phone extractor with configuration"""
        if self.phone_extractor is None or config:
            self.phone_extractor = PhoneExtractor(config)
        return self.phone_extractor
    
    def run(self,
            crawl_results: Dict[str, Any],
            extraction_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract phone numbers from multiple crawled pages.
        
        Args:
            crawl_results: Dictionary of URL -> page content from crawler
            extraction_config: Optional configuration overrides
            
        Returns:
            Dictionary containing consolidated extraction results
        """
        try:
            self.logger.info(f"Starting bulk phone extraction for {len(crawl_results)} pages")
            
            # Get phone extractor with configuration
            extractor = self._get_phone_extractor(extraction_config)
            
            # Perform bulk extraction
            all_results = []
            all_candidates = []
            all_primary_phones = []
            total_extraction_time = 0.0
            pages_with_phones = 0
            
            page_results = {}
            
            for url, page_content in crawl_results.items():
                try:
                    # Extract from this page
                    result = extractor.extract_from_html(page_content, url)
                    all_results.append(result)
                    
                    page_data = {
                        'url': url,
                        'candidates': len(result.candidates),
                        'high_confidence': result.high_confidence_count,
                        'business_phones': result.business_phone_count,
                        'toll_free_phones': result.toll_free_count,
                        'extraction_time_ms': result.extraction_time_ms,
                        'primary_phone': result.primary_phone.formatted_number if result.primary_phone else None,
                        'errors': result.extraction_errors
                    }
                    page_results[url] = page_data
                    
                    # Consolidate candidates
                    all_candidates.extend(result.candidates)
                    if result.primary_phone:
                        all_primary_phones.append(result.primary_phone)
                    
                    if result.extraction_time_ms:
                        total_extraction_time += result.extraction_time_ms
                    
                    if result.candidates:
                        pages_with_phones += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing page {url}: {e}")
                    page_results[url] = {
                        'url': url,
                        'error': str(e),
                        'candidates': 0
                    }
            
            # Deduplicate phone numbers across all pages
            unique_phones = {}
            for candidate in all_candidates:
                phone_key = candidate.formatted_number
                if phone_key not in unique_phones or candidate.confidence_score > unique_phones[phone_key].confidence_score:
                    unique_phones[phone_key] = candidate
            
            # Get best phones by category
            business_phones = [p for p in unique_phones.values() if p.phone_type.value == 'business']
            toll_free_phones = [p for p in unique_phones.values() if p.is_toll_free]
            high_confidence_phones = [p for p in unique_phones.values() if p.confidence_score >= 0.7]
            
            # Format consolidated results
            consolidated_result = {
                'success': True,
                'pages_processed': len(crawl_results),
                'pages_with_phones': pages_with_phones,
                'total_candidates': len(all_candidates),
                'unique_phones': len(unique_phones),
                'business_phone_count': len(business_phones),
                'toll_free_count': len(toll_free_phones),
                'high_confidence_count': len(high_confidence_phones),
                'total_extraction_time_ms': total_extraction_time,
                'avg_extraction_time_ms': total_extraction_time / max(1, len(crawl_results)),
                'best_phones': [phone.to_dict() for phone in sorted(unique_phones.values(), 
                                                                   key=lambda x: x.confidence_score, 
                                                                   reverse=True)[:10]],
                'business_phones': [phone.to_dict() for phone in business_phones[:5]],
                'toll_free_phones': [phone.to_dict() for phone in toll_free_phones[:3]],
                'page_results': page_results,
                'extractor_statistics': extractor.get_statistics()
            }
            
            self.logger.info(
                f"Bulk phone extraction completed: {len(crawl_results)} pages processed, "
                f"{len(all_candidates)} total candidates, "
                f"{len(unique_phones)} unique phone numbers"
            )
            
            return consolidated_result
            
        except Exception as e:
            error_msg = f"Bulk phone extraction failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'pages_processed': len(crawl_results) if crawl_results else 0,
                'total_candidates': 0,
                'unique_phones': 0,
                'best_phones': [],
                'page_results': {}
            }


class PhoneValidationTool(BaseTool):
    """
    Tool for validating and scoring individual phone numbers.
    
    Provides detailed validation including format checking, area code validation,
    and business quality assessment.
    """
    
    name: str = "phone_validation"
    description: str = "Validate and assess quality of individual phone numbers"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.phone_extractor = PhoneExtractor()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.PhoneValidationTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run(self, 
            phone_number: str,
            context: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and assess a phone number.
        
        Args:
            phone_number: Phone number to validate
            context: Optional context text for quality assessment
            
        Returns:
            Dictionary containing validation results and quality metrics
        """
        try:
            self.logger.debug(f"Validating phone number: {phone_number}")
            
            # Create a temporary phone candidate for validation
            candidate = self.phone_extractor._parse_phone_candidate(
                phone_number, phone_number, "direct_input", ""
            )
            
            if not candidate:
                return {
                    'phone_number': phone_number,
                    'is_valid': False,
                    'error': 'Could not parse phone number',
                    'confidence_score': 0.0,
                    'recommendation': 'invalid_format'
                }
            
            # Add context if provided
            if context:
                candidate.context_text = context
            
            # Process the candidate
            candidates = self.phone_extractor._process_candidates([candidate], "")
            if candidates:
                processed_candidate = candidates[0]
                self.phone_extractor._classify_and_score_candidates([processed_candidate])
                
                result = {
                    'phone_number': phone_number,
                    'formatted_number': processed_candidate.formatted_number,
                    'is_valid': processed_candidate.validation_status == 'valid',
                    'validation_status': processed_candidate.validation_status,
                    'phone_type': processed_candidate.phone_type.value,
                    'is_toll_free': processed_candidate.is_toll_free,
                    'is_international': processed_candidate.is_international,
                    'area_code': processed_candidate.area_code,
                    'confidence_score': processed_candidate.confidence_score,
                    'confidence_level': processed_candidate.confidence_level.value,
                    'context_keywords': processed_candidate.context_keywords,
                    'recommendation': self._get_use_recommendation(processed_candidate)
                }
                
                self.logger.debug(f"Validation completed for {phone_number}: {result['validation_status']}")
                
                return result
            else:
                return {
                    'phone_number': phone_number,
                    'is_valid': False,
                    'error': 'Phone number failed processing',
                    'confidence_score': 0.0,
                    'recommendation': 'invalid'
                }
            
        except Exception as e:
            error_msg = f"Phone validation failed for {phone_number}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'phone_number': phone_number,
                'is_valid': False,
                'error': error_msg,
                'confidence_score': 0.0,
                'recommendation': 'validation_error'
            }
    
    def _get_use_recommendation(self, candidate) -> str:
        """Get recommendation for phone usage"""
        if candidate.validation_status == 'invalid':
            return 'do_not_use'
        elif candidate.confidence_score >= 0.8:
            return 'primary_contact'
        elif candidate.confidence_score >= 0.6:
            return 'secondary_contact'
        elif candidate.confidence_score >= 0.4:
            return 'backup_contact'
        else:
            return 'low_confidence'


class PhoneDeduplicationTool(BaseTool):
    """
    Tool for deduplicating and merging phone number candidates.
    
    Identifies duplicate phone numbers across multiple sources and merges
    their context information to create consolidated contact records.
    """
    
    name: str = "phone_deduplication"
    description: str = "Deduplicate phone numbers and merge context information across sources"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.phone_extractor = PhoneExtractor()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.PhoneDeduplicationTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run(self, 
            phone_candidates: List[Dict[str, Any]],
            merge_strategy: str = "best_confidence") -> Dict[str, Any]:
        """
        Deduplicate and merge phone number candidates.
        
        Args:
            phone_candidates: List of phone candidate dictionaries
            merge_strategy: Strategy for merging duplicates ("best_confidence", "merge_context", "latest")
            
        Returns:
            Dictionary containing deduplicated results
        """
        try:
            self.logger.info(f"Deduplicating {len(phone_candidates)} phone candidates")
            
            # Group candidates by normalized phone number
            phone_groups = {}
            for candidate in phone_candidates:
                # Normalize phone number (last 10 digits)
                phone_raw = candidate.get('formatted_number', candidate.get('raw_text', ''))
                digits = ''.join(filter(str.isdigit, phone_raw))
                
                if len(digits) >= 10:
                    phone_key = digits[-10:]  # Last 10 digits as key
                    
                    if phone_key not in phone_groups:
                        phone_groups[phone_key] = []
                    phone_groups[phone_key].append(candidate)
            
            # Merge duplicates based on strategy
            deduplicated_candidates = []
            
            for phone_key, candidates in phone_groups.items():
                if len(candidates) == 1:
                    # No duplicates
                    deduplicated_candidates.append(candidates[0])
                else:
                    # Merge duplicates
                    merged = self._merge_phone_candidates(candidates, merge_strategy)
                    deduplicated_candidates.append(merged)
            
            # Sort by confidence score
            deduplicated_candidates.sort(
                key=lambda x: x.get('confidence_score', 0.0),
                reverse=True
            )
            
            result = {
                'success': True,
                'original_count': len(phone_candidates),
                'unique_count': len(deduplicated_candidates),
                'duplicates_merged': len(phone_candidates) - len(deduplicated_candidates),
                'merge_strategy': merge_strategy,
                'deduplicated_candidates': deduplicated_candidates,
                'duplicate_groups': {
                    phone_key: len(candidates) 
                    for phone_key, candidates in phone_groups.items() 
                    if len(candidates) > 1
                }
            }
            
            self.logger.info(
                f"Phone deduplication completed: {len(phone_candidates)} -> {len(deduplicated_candidates)} "
                f"({len(phone_candidates) - len(deduplicated_candidates)} duplicates merged)"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Phone deduplication failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'original_count': len(phone_candidates) if phone_candidates else 0,
                'unique_count': 0,
                'deduplicated_candidates': []
            }
    
    def _merge_phone_candidates(self, candidates: List[Dict[str, Any]], strategy: str) -> Dict[str, Any]:
        """Merge duplicate phone candidates based on strategy"""
        if not candidates:
            return {}
        
        if strategy == "best_confidence":
            # Take the candidate with highest confidence score
            best = max(candidates, key=lambda x: x.get('confidence_score', 0.0))
            merged = best.copy()
            
        elif strategy == "latest":
            # Take the most recent candidate
            latest = max(candidates, key=lambda x: x.get('extraction_timestamp', 0.0))
            merged = latest.copy()
            
        else:  # merge_context
            # Merge context from all candidates
            merged = candidates[0].copy()
        
        # Always merge unique context information
        all_sources = set()
        all_context = set()
        all_methods = set()
        all_pages = set()
        
        for candidate in candidates:
            if candidate.get('source_page'):
                all_sources.add(candidate['source_page'])
            if candidate.get('context_text'):
                all_context.add(candidate['context_text'])
            if candidate.get('extraction_method'):
                all_methods.add(candidate['extraction_method'])
            if candidate.get('source_page'):
                all_pages.add(candidate['source_page'])
        
        # Update merged candidate with consolidated information
        merged['sources'] = list(all_sources)
        merged['all_context'] = list(all_context)
        merged['extraction_methods'] = list(all_methods)
        merged['found_on_pages'] = list(all_pages)
        merged['duplicate_count'] = len(candidates)
        
        # Take best confidence score
        merged['confidence_score'] = max(
            c.get('confidence_score', 0.0) for c in candidates
        )
        
        return merged