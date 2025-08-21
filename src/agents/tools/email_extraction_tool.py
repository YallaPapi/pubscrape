"""
Email Extraction Tool

Agency Swarm tool for extracting emails from HTML content with advanced 
pattern detection, validation, and context scoring.
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

from agents.email_extractor_agent import EmailExtractionEngine, EmailExtractionResult


class EmailExtractionInput(BaseModel):
    """Input model for email extraction"""
    html_content: str = Field(
        description="HTML content to extract emails from"
    )
    page_url: str = Field(
        description="URL of the page being processed"
    )
    extraction_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional configuration overrides for extraction"
    )


class EmailExtractionTool(BaseTool):
    """
    Tool for extracting and scoring email addresses from HTML content.
    
    Uses advanced pattern detection including RFC-5322 compliant regex,
    obfuscated email detection, and contextual scoring to identify
    high-quality business email addresses.
    """
    
    name: str = "email_extraction"
    description: str = "Extract and score email addresses from HTML content with context analysis"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.extraction_engine = None
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailExtractionTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _get_extraction_engine(self, config: Optional[Dict[str, Any]] = None) -> EmailExtractionEngine:
        """Get or create extraction engine with configuration"""
        if self.extraction_engine is None or config:
            self.extraction_engine = EmailExtractionEngine(config)
        return self.extraction_engine
    
    def run(self, 
            html_content: str,
            page_url: str,
            extraction_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract emails from HTML content.
        
        Args:
            html_content: HTML content to scan for emails
            page_url: URL of the page being processed
            extraction_config: Optional configuration overrides
            
        Returns:
            Dictionary containing extraction results and metadata
        """
        try:
            self.logger.info(f"Starting email extraction for {page_url}")
            
            # Get extraction engine with configuration
            engine = self._get_extraction_engine(extraction_config)
            
            # Perform extraction
            result = engine.extract_from_page(html_content, page_url)
            
            # Format results for return
            formatted_result = {
                'success': True,
                'page_url': result.page_url,
                'total_candidates': result.total_found,
                'high_quality_count': len(result.high_quality_emails),
                'business_email_count': len(result.business_emails),
                'extraction_time_ms': result.extraction_time_ms,
                'candidates': [candidate.to_dict() for candidate in result.candidates],
                'high_quality_emails': result.high_quality_emails,
                'business_emails': result.business_emails,
                'statistics': engine.get_statistics(),
                'error': result.error
            }
            
            self.logger.info(
                f"Extraction completed for {page_url}: "
                f"{result.total_found} candidates, "
                f"{len(result.high_quality_emails)} high quality"
            )
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"Email extraction failed for {page_url}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'page_url': page_url,
                'error': error_msg,
                'candidates': [],
                'high_quality_emails': [],
                'business_emails': [],
                'total_candidates': 0,
                'high_quality_count': 0,
                'business_email_count': 0
            }


class BulkEmailExtractionTool(BaseTool):
    """
    Tool for extracting emails from multiple pages in bulk.
    
    Processes crawl results from the SiteCrawler agent and extracts
    emails from all discovered pages with consolidated reporting.
    """
    
    name: str = "bulk_email_extraction"
    description: str = "Extract emails from multiple crawled pages with consolidated reporting"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.extraction_engine = None
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.BulkEmailExtractionTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _get_extraction_engine(self, config: Optional[Dict[str, Any]] = None) -> EmailExtractionEngine:
        """Get or create extraction engine with configuration"""
        if self.extraction_engine is None or config:
            self.extraction_engine = EmailExtractionEngine(config)
        return self.extraction_engine
    
    def run(self,
            crawl_results: Dict[str, Any],
            extraction_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract emails from multiple crawled pages.
        
        Args:
            crawl_results: Dictionary of URL -> page content from crawler
            extraction_config: Optional configuration overrides
            
        Returns:
            Dictionary containing consolidated extraction results
        """
        try:
            self.logger.info(f"Starting bulk email extraction for {len(crawl_results)} pages")
            
            # Get extraction engine with configuration
            engine = self._get_extraction_engine(extraction_config)
            
            # Perform bulk extraction
            results = engine.extract_from_crawl_results(crawl_results)
            
            # Consolidate results
            all_candidates = []
            all_high_quality = set()
            all_business_emails = set()
            total_extraction_time = 0.0
            pages_with_emails = 0
            
            page_results = {}
            
            for url, result in results.items():
                page_data = {
                    'url': url,
                    'candidates': len(result.candidates),
                    'high_quality': len(result.high_quality_emails),
                    'business_emails': len(result.business_emails),
                    'extraction_time_ms': result.extraction_time_ms,
                    'error': result.error
                }
                page_results[url] = page_data
                
                # Consolidate candidates
                all_candidates.extend([c.to_dict() for c in result.candidates])
                all_high_quality.update(result.high_quality_emails)
                all_business_emails.update(result.business_emails)
                
                if result.extraction_time_ms:
                    total_extraction_time += result.extraction_time_ms
                
                if result.candidates:
                    pages_with_emails += 1
            
            # Format consolidated results
            consolidated_result = {
                'success': True,
                'pages_processed': len(crawl_results),
                'pages_with_emails': pages_with_emails,
                'total_candidates': len(all_candidates),
                'unique_high_quality': len(all_high_quality),
                'unique_business_emails': len(all_business_emails),
                'total_extraction_time_ms': total_extraction_time,
                'avg_extraction_time_ms': total_extraction_time / max(1, len(crawl_results)),
                'all_candidates': all_candidates,
                'high_quality_emails': list(all_high_quality),
                'business_emails': list(all_business_emails),
                'page_results': page_results,
                'engine_statistics': engine.get_statistics()
            }
            
            self.logger.info(
                f"Bulk extraction completed: {len(crawl_results)} pages processed, "
                f"{len(all_candidates)} total candidates, "
                f"{len(all_high_quality)} unique high-quality emails"
            )
            
            return consolidated_result
            
        except Exception as e:
            error_msg = f"Bulk email extraction failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'pages_processed': len(crawl_results) if crawl_results else 0,
                'total_candidates': 0,
                'high_quality_emails': [],
                'business_emails': [],
                'page_results': {}
            }


class EmailValidationTool(BaseTool):
    """
    Tool for validating and scoring individual email addresses.
    
    Provides detailed validation including syntax checking, domain validation,
    and business quality assessment.
    """
    
    name: str = "email_validation"
    description: str = "Validate and assess quality of individual email addresses"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
        self.extraction_engine = EmailExtractionEngine()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailValidationTool")
        
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
            email: str,
            context: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate and assess an email address.
        
        Args:
            email: Email address to validate
            context: Optional context text for quality assessment
            
        Returns:
            Dictionary containing validation results and quality metrics
        """
        try:
            self.logger.debug(f"Validating email: {email}")
            
            # Validate email
            is_valid, status, details = self.extraction_engine.validator.validate_email(email)
            
            # Assess quality
            quality = self.extraction_engine.validator.classify_email_quality(email, 0.0)
            
            # Context analysis if provided
            context_score = 0.0
            if context:
                # Simple context scoring based on business keywords
                context_lower = context.lower()
                business_indicators = [
                    'contact', 'business', 'ceo', 'founder', 'director', 
                    'manager', 'sales', 'marketing', 'pr', 'press'
                ]
                
                for indicator in business_indicators:
                    if indicator in context_lower:
                        context_score += 0.1
                
                context_score = min(0.5, context_score)  # Cap at 0.5
            
            result = {
                'email': email,
                'is_valid': is_valid,
                'validation_status': status,
                'validation_details': details,
                'quality_level': quality.value,
                'quality_score': details.get('quality_score', 0.0),
                'context_score': context_score,
                'total_score': details.get('quality_score', 0.0) + context_score,
                'recommended_use': self._get_use_recommendation(quality, details.get('quality_score', 0.0) + context_score)
            }
            
            self.logger.debug(f"Validation completed for {email}: {quality.value}")
            
            return result
            
        except Exception as e:
            error_msg = f"Email validation failed for {email}: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'email': email,
                'is_valid': False,
                'error': error_msg,
                'quality_level': 'unknown',
                'quality_score': 0.0,
                'total_score': 0.0,
                'recommended_use': 'do_not_use'
            }
    
    def _get_use_recommendation(self, quality, total_score: float) -> str:
        """Get recommendation for email usage"""
        if quality.value == 'spam' or total_score < 0.1:
            return 'do_not_use'
        elif quality.value == 'high' or total_score >= 0.7:
            return 'priority_contact'
        elif quality.value == 'medium' or total_score >= 0.4:
            return 'secondary_contact'
        else:
            return 'backup_contact'


class EmailDeduplicationTool(BaseTool):
    """
    Tool for deduplicating and merging email candidates.
    
    Identifies duplicate emails across multiple sources and merges
    their context information to create consolidated contact records.
    """
    
    name: str = "email_deduplication"
    description: str = "Deduplicate emails and merge context information across sources"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging"""
        logger = logging.getLogger(f"{__name__}.EmailDeduplicationTool")
        
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
            email_candidates: List[Dict[str, Any]],
            merge_strategy: str = "best_quality") -> Dict[str, Any]:
        """
        Deduplicate and merge email candidates.
        
        Args:
            email_candidates: List of email candidate dictionaries
            merge_strategy: Strategy for merging duplicates ("best_quality", "merge_context", "latest")
            
        Returns:
            Dictionary containing deduplicated results
        """
        try:
            self.logger.info(f"Deduplicating {len(email_candidates)} email candidates")
            
            # Group candidates by email address
            email_groups = {}
            for candidate in email_candidates:
                email = candidate.get('email', '').lower().strip()
                if email:
                    if email not in email_groups:
                        email_groups[email] = []
                    email_groups[email].append(candidate)
            
            # Merge duplicates based on strategy
            deduplicated_candidates = []
            
            for email, candidates in email_groups.items():
                if len(candidates) == 1:
                    # No duplicates
                    deduplicated_candidates.append(candidates[0])
                else:
                    # Merge duplicates
                    merged = self._merge_candidates(candidates, merge_strategy)
                    deduplicated_candidates.append(merged)
            
            # Sort by quality and confidence
            deduplicated_candidates.sort(
                key=lambda x: (x.get('confidence_score', 0.0), x.get('quality', '')),
                reverse=True
            )
            
            result = {
                'success': True,
                'original_count': len(email_candidates),
                'unique_count': len(deduplicated_candidates),
                'duplicates_merged': len(email_candidates) - len(deduplicated_candidates),
                'merge_strategy': merge_strategy,
                'deduplicated_candidates': deduplicated_candidates,
                'duplicate_groups': {
                    email: len(candidates) 
                    for email, candidates in email_groups.items() 
                    if len(candidates) > 1
                }
            }
            
            self.logger.info(
                f"Deduplication completed: {len(email_candidates)} -> {len(deduplicated_candidates)} "
                f"({len(email_candidates) - len(deduplicated_candidates)} duplicates merged)"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Email deduplication failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'original_count': len(email_candidates) if email_candidates else 0,
                'unique_count': 0,
                'deduplicated_candidates': []
            }
    
    def _merge_candidates(self, candidates: List[Dict[str, Any]], strategy: str) -> Dict[str, Any]:
        """Merge duplicate candidates based on strategy"""
        if not candidates:
            return {}
        
        if strategy == "best_quality":
            # Take the candidate with highest confidence score
            best = max(candidates, key=lambda x: x.get('confidence_score', 0.0))
            merged = best.copy()
            
        elif strategy == "latest":
            # Take the most recent candidate
            latest = max(candidates, key=lambda x: x.get('discovery_timestamp', 0.0))
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
            if candidate.get('source'):
                all_sources.add(candidate['source'])
            if candidate.get('context_text'):
                all_context.add(candidate['context_text'])
            if candidate.get('extraction_method'):
                all_methods.add(candidate['extraction_method'])
            if candidate.get('page_url'):
                all_pages.add(candidate['page_url'])
        
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