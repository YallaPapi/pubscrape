"""
Email Validation Tool

Agency Swarm tool for comprehensive email validation using Mailtester Ninja API
as the primary validation method, with fallback to local validation methods.
"""

import logging
import time
import os
from typing import Dict, Any, List, Optional
from pydantic import Field

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

# Import both Mailtester Ninja and local validation
try:
    from .mailtester_ninja_client import (
        MailtesterNinjaClient, ValidationLevel, EmailStatus, create_mailtester_client
    )
    MAILTESTER_AVAILABLE = True
except ImportError:
    MAILTESTER_AVAILABLE = False

from agents.validator_dedupe_agent import (
    EmailSyntaxValidator, DNSValidator, BlacklistFilter, 
    ValidationResult, ValidationStatus, EmailQuality
)


class EmailValidationTool(BaseTool):
    """
    Tool for validating email addresses with comprehensive checks using Mailtester Ninja API.
    
    Primary validation uses Mailtester Ninja API for real-time email verification.
    Falls back to local validation methods if API is unavailable.
    """
    
    emails: List[str] = Field(
        ..., 
        description="List of email addresses to validate using Mailtester Ninja API"
    )
    
    use_mailtester_api: bool = Field(
        default=True,
        description="Use Mailtester Ninja API for validation (recommended)"
    )
    
    validation_level: str = Field(
        default="basic",
        description="API validation level: 'basic' for syntax/domain checks, 'full' for SMTP verification"
    )
    
    enable_dns_check: bool = Field(
        default=False,
        description="Enable DNS MX record validation for fallback method"
    )
    
    enable_deliverability_check: bool = Field(
        default=False,
        description="Enable email deliverability checking for fallback method"
    )
    
    tld_whitelist: Optional[List[str]] = Field(
        default=None,
        description="Custom TLD whitelist (uses defaults if not provided)"
    )
    
    blacklist_patterns: Optional[List[str]] = Field(
        default=None,
        description="Custom blacklist patterns to filter out unwanted emails"
    )
    
    max_workers: int = Field(
        default=10,
        description="Maximum number of parallel validation workers"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Validate email addresses using Mailtester Ninja API or fallback methods.
        
        Returns:
            Dictionary containing validation results and statistics
        """
        start_time = time.time()
        
        # Always prioritize Mailtester Ninja API when available and configured
        use_api = (
            self.use_mailtester_api and 
            MAILTESTER_AVAILABLE and 
            os.getenv('MAILTESTER_NINJA_API_KEY') and 
            os.getenv('MAILTESTER_NINJA_API_KEY') not in ['YOUR_MAILTESTER_NINJA_API_KEY_HERE', '', None]
        )
        
        if use_api:
            logging.info(f"Using Mailtester Ninja API for email validation ({self.validation_level})")
            return self._validate_with_mailtester_api()
        else:
            if not MAILTESTER_AVAILABLE:
                logging.warning("Mailtester Ninja client not available - check installation")
            elif not os.getenv('MAILTESTER_NINJA_API_KEY'):
                logging.warning("MAILTESTER_NINJA_API_KEY environment variable not set")
            else:
                logging.warning("Mailtester Ninja API disabled by configuration")
                
            logging.info("Using fallback validation method (basic validation without API)")
            return self._validate_with_fallback_methods()
    
    def _validate_with_mailtester_api(self) -> Dict[str, Any]:
        """Validate emails using Mailtester Ninja API"""
        start_time = time.time()
        
        try:
            # Parse validation level
            try:
                validation_level = ValidationLevel(self.validation_level.lower())
            except ValueError:
                validation_level = ValidationLevel.BASIC
            
            # Create Mailtester client
            with create_mailtester_client(enable_caching=True) as client:
                
                # Validate emails
                if len(self.emails) > 50:
                    # Use batch validation for large lists
                    mailtester_results = client.validate_batch(
                        self.emails, 
                        validation_level=validation_level,
                        batch_size=100
                    )
                else:
                    # Validate individually for smaller lists
                    mailtester_results = [
                        client.validate_email(email, validation_level)
                        for email in self.emails
                    ]
                
                # Convert Mailtester results to our format
                results = []
                stats = self._initialize_stats()
                
                for mt_result in mailtester_results:
                    # Convert to ValidationResult format
                    result_dict = self._convert_mailtester_result(mt_result)
                    results.append(result_dict)
                    
                    # Update statistics
                    self._update_stats(stats, result_dict)
                
                # Get API statistics
                api_stats = client.get_stats()
                
                total_time = time.time() - start_time
                acceptance_rate = stats['valid'] / max(1, stats['total_processed'])
                
                # Sort results by quality
                valid_emails = [r for r in results if r['is_valid']]
                invalid_emails = [r for r in results if not r['is_valid']]
                
                valid_emails.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
                
                return {
                    'summary': {
                        'total_emails': len(self.emails),
                        'processed': stats['total_processed'],
                        'valid_emails': stats['valid'],
                        'invalid_emails': stats['total_processed'] - stats['valid'],
                        'acceptance_rate': acceptance_rate,
                        'processing_time_seconds': total_time,
                        'emails_per_second': stats['total_processed'] / max(0.001, total_time),
                        'validation_method': f'Mailtester Ninja API ({validation_level.value})',
                        'api_requests': api_stats.get('total_requests', 0),
                        'cache_hits': api_stats.get('cache_hits', 0)
                    },
                    'validation_stats': stats,
                    'quality_distribution': {
                        'high': stats['high_quality'],
                        'medium': stats['medium_quality'], 
                        'low': stats['low_quality'],
                        'spam': stats['spam']
                    },
                    'mailtester_stats': {
                        'valid_count': len([r for r in mailtester_results if r.status == EmailStatus.VALID]),
                        'risky_count': len([r for r in mailtester_results if r.status == EmailStatus.RISKY]),
                        'catch_all_count': len([r for r in mailtester_results if r.status == EmailStatus.CATCH_ALL]),
                        'disposable_count': len([r for r in mailtester_results if r.is_disposable]),
                        'role_account_count': len([r for r in mailtester_results if r.is_role_account])
                    },
                    'valid_emails': valid_emails,
                    'invalid_emails': invalid_emails,
                    'all_results': results
                }
                
        except Exception as e:
            logging.error(f"Mailtester API validation failed: {e}")
            logging.info("Falling back to local validation methods")
            return self._validate_with_fallback_methods()
    
    def _validate_with_fallback_methods(self) -> Dict[str, Any]:
        """Validate emails using local validation methods as fallback"""
        start_time = time.time()
        
        # Configure local validators
        syntax_config = {
            "check_deliverability": self.enable_deliverability_check,
            "tld_whitelist": self.tld_whitelist or []
        }
        
        dns_config = {
            "enable_mx_check": self.enable_dns_check,
            "dns_timeout": 5.0,
            "enable_caching": True
        }
        
        blacklist_config = {
            "blacklist_patterns": self.blacklist_patterns or []
        }
        
        # Initialize validators
        syntax_validator = EmailSyntaxValidator(syntax_config)
        dns_validator = DNSValidator(dns_config)
        blacklist_filter = BlacklistFilter(blacklist_config)
        
        # Validate emails
        results = []
        stats = self._initialize_stats()
        
        for email in self.emails:
            if not email or not isinstance(email, str):
                continue
            
            try:
                # Step 1: Syntax validation
                result = syntax_validator.validate_syntax(email)
                
                if result.is_valid:
                    # Step 2: DNS validation (if enabled)
                    if self.enable_dns_check:
                        result = dns_validator.validate_domain(result.domain, result)
                    
                    if result.is_valid:
                        # Step 3: Blacklist filtering
                        result = blacklist_filter.check_blacklist(email, result)
                
                result_dict = result.to_dict()
                results.append(result_dict)
                self._update_stats(stats, result_dict)
                
            except Exception as e:
                logging.error(f"Error validating email {email}: {e}")
                
                # Create error result
                error_result = ValidationResult(
                    email=email,
                    status=ValidationStatus.UNKNOWN_ERROR,
                    reason=f"Validation error: {str(e)}"
                )
                result_dict = error_result.to_dict()
                results.append(result_dict)
                stats['total_processed'] += 1
        
        # Calculate summary metrics
        total_time = time.time() - start_time
        acceptance_rate = stats['valid'] / max(1, stats['total_processed'])
        
        # Separate valid and invalid emails
        valid_emails = [r for r in results if r['is_valid']]
        invalid_emails = [r for r in results if not r['is_valid']]
        
        # Sort by quality and confidence
        valid_emails.sort(key=lambda x: (
            {'high': 3, 'medium': 2, 'low': 1, 'spam': 0}.get(x.get('quality', 'spam'), 0),
            x.get('confidence_score', 0)
        ), reverse=True)
        
        return {
            'summary': {
                'total_emails': len(self.emails),
                'processed': stats['total_processed'],
                'valid_emails': stats['valid'],
                'invalid_emails': stats['total_processed'] - stats['valid'],
                'acceptance_rate': acceptance_rate,
                'processing_time_seconds': total_time,
                'emails_per_second': stats['total_processed'] / max(0.001, total_time),
                'validation_method': 'Local validation (fallback)'
            },
            'validation_stats': stats,
            'quality_distribution': {
                'high': stats['high_quality'],
                'medium': stats['medium_quality'], 
                'low': stats['low_quality'],
                'spam': stats['spam']
            },
            'valid_emails': valid_emails,
            'invalid_emails': invalid_emails,
            'all_results': results
        }
    
    def _initialize_stats(self) -> Dict[str, int]:
        """Initialize statistics dictionary"""
        return {
            'total_processed': 0,
            'valid': 0,
            'invalid_syntax': 0,
            'invalid_domain': 0,
            'blacklisted': 0,
            'no_mx_record': 0,
            'dns_errors': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'spam': 0
        }
    
    def _update_stats(self, stats: Dict[str, int], result_dict: Dict[str, Any]):
        """Update statistics with result"""
        stats['total_processed'] += 1
        
        if result_dict.get('is_valid', False):
            stats['valid'] += 1
        else:
            # Count rejection reasons
            status = result_dict.get('status', 'unknown_error')
            if status == 'invalid_syntax':
                stats['invalid_syntax'] += 1
            elif status == 'invalid_domain':
                stats['invalid_domain'] += 1
            elif status == 'blacklisted':
                stats['blacklisted'] += 1
            elif status == 'no_mx_record':
                stats['no_mx_record'] += 1
            elif status == 'dns_error':
                stats['dns_errors'] += 1
        
        # Count quality levels
        quality = result_dict.get('quality', 'spam')
        if quality == 'high':
            stats['high_quality'] += 1
        elif quality == 'medium':
            stats['medium_quality'] += 1
        elif quality == 'low':
            stats['low_quality'] += 1
        else:
            stats['spam'] += 1
    
    def _convert_mailtester_result(self, mt_result) -> Dict[str, Any]:
        """Convert MailtesterResult to our ValidationResult format"""
        
        # Map Mailtester status to our status with improved logic
        if mt_result.status == EmailStatus.VALID:
            our_status = ValidationStatus.VALID
            is_valid = True
        elif mt_result.status == EmailStatus.RISKY:
            # Accept risky emails but lower the confidence
            our_status = ValidationStatus.VALID
            is_valid = True
        elif mt_result.status == EmailStatus.CATCH_ALL:
            # Accept catch-all but note the limitation
            our_status = ValidationStatus.VALID
            is_valid = True
        else:
            our_status = ValidationStatus.INVALID_DOMAIN
            is_valid = False
        
        # Enhanced quality scoring using Mailtester's comprehensive data
        quality_score = mt_result.get_quality_score()
        
        # Apply additional business-context scoring adjustments
        if mt_result.is_role_account and not mt_result.is_disposable:
            # Role accounts from legitimate domains are valuable for B2B
            quality_score = min(1.0, quality_score + 0.1)
        
        if mt_result.smtp_check and mt_result.smtp_check.get('mailbox_exists'):
            # SMTP verification is highly valuable
            quality_score = min(1.0, quality_score + 0.15)
        
        if mt_result.is_disposable:
            # Heavily penalize disposable emails
            quality_score = max(0.0, quality_score - 0.4)
        
        # Map to quality levels with adjusted thresholds
        if quality_score >= 0.75:
            quality = EmailQuality.HIGH
        elif quality_score >= 0.45:
            quality = EmailQuality.MEDIUM
        elif quality_score >= 0.15:
            quality = EmailQuality.LOW
        else:
            quality = EmailQuality.SPAM
        
        # Build comprehensive validation reason
        reasons = []
        if not mt_result.is_valid_format:
            reasons.append("Invalid format")
        if not mt_result.domain_exists:
            reasons.append("Domain doesn't exist")
        if not mt_result.has_mx_records:
            reasons.append("No MX records")
        if mt_result.is_disposable:
            reasons.append("Disposable email provider")
        if mt_result.status == EmailStatus.RISKY:
            reasons.append("Risky email (deliverability concerns)")
        if mt_result.status == EmailStatus.CATCH_ALL:
            reasons.append("Catch-all domain (accepts all emails)")
        if mt_result.smtp_check and not mt_result.smtp_check.get('mailbox_exists'):
            reasons.append("Mailbox existence unverified")
        
        reason = "; ".join(reasons) if reasons else "Valid email with API verification"
        
        # Enhanced domain classification
        is_business_domain = (
            mt_result.is_role_account and 
            not mt_result.is_disposable and 
            not self._is_personal_email_provider(mt_result.email.split('@')[1] if '@' in mt_result.email else '')
        )
        
        is_personal_domain = (
            not is_business_domain and 
            self._is_personal_email_provider(mt_result.email.split('@')[1] if '@' in mt_result.email else '')
        )
        
        return {
            'email': mt_result.email,
            'status': our_status.value,
            'is_valid': is_valid,
            'quality': quality.value,
            'confidence_score': quality_score,
            'reason': reason,
            'normalized_email': mt_result.email.lower(),
            'domain': mt_result.email.split('@')[1] if '@' in mt_result.email else '',
            'validation_time_ms': mt_result.api_response_time_ms,
            'tld': mt_result.email.split('@')[1].split('.')[-1] if '@' in mt_result.email else '',
            'is_business_domain': is_business_domain,
            'is_personal_domain': is_personal_domain,
            
            # Enhanced Mailtester-specific fields
            'mailtester_score': mt_result.score,
            'mailtester_status': mt_result.status.value,
            'mailtester_confidence_level': mt_result.confidence_level,
            'is_disposable': mt_result.is_disposable,
            'is_role_account': mt_result.is_role_account,
            'smtp_verified': mt_result.smtp_check.get('mailbox_exists', False) if mt_result.smtp_check else False,
            'is_catch_all': mt_result.smtp_check.get('is_catch_all', False) if mt_result.smtp_check else False,
            'has_mx_records': mt_result.has_mx_records,
            'domain_exists': mt_result.domain_exists,
            
            # Additional SMTP insights if available
            'smtp_can_connect': mt_result.smtp_check.get('can_connect', False) if mt_result.smtp_check else False,
            'smtp_accepts_mail': mt_result.smtp_check.get('accepts_mail', False) if mt_result.smtp_check else False,
            
            # API validation metadata
            'validation_method': 'Mailtester Ninja API',
            'api_validation_level': mt_result.validation_level.value,
            'deliverability_verified': mt_result.is_deliverable()
        }
    
    def _is_personal_email_provider(self, domain: str) -> bool:
        """Check if domain is a known personal email provider"""
        personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'me.com', 'protonmail.com',
            'tutanota.com', 'fastmail.com', 'zoho.com', 'yandex.com',
            'mail.com', 'gmx.com', 'web.de', 'live.com', 'msn.com'
        }
        return domain.lower() in personal_domains


class BulkEmailValidationTool(BaseTool):
    """
    Tool for bulk email validation with rate limiting and progress tracking.
    
    Designed for processing large datasets with configurable batch sizes
    and validation settings.
    """
    
    email_data: List[Dict[str, Any]] = Field(
        ...,
        description="List of email data objects with 'email' field and optional contact info"
    )
    
    batch_size: int = Field(
        default=100,
        description="Number of emails to process in each batch"
    )
    
    enable_dns_check: bool = Field(
        default=False,
        description="Enable DNS MX record validation"
    )
    
    rate_limit_delay: float = Field(
        default=0.1,
        description="Delay between batches in seconds for rate limiting"
    )
    
    quality_threshold: float = Field(
        default=0.3,
        description="Minimum confidence score for accepting emails"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Process emails in batches with rate limiting.
        
        Returns:
            Dictionary with batch processing results and final summary
        """
        start_time = time.time()
        
        total_emails = len(self.email_data)
        all_results = []
        batch_summaries = []
        
        # Process in batches
        for i in range(0, total_emails, self.batch_size):
            batch_start = time.time()
            batch_emails = self.email_data[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_emails + self.batch_size - 1) // self.batch_size
            
            # Extract emails from batch data
            emails = [item.get('email', '') for item in batch_emails if item.get('email')]
            
            if not emails:
                continue
            
            # Validate batch using EmailValidationTool
            validation_tool = EmailValidationTool(
                emails=emails,
                enable_dns_check=self.enable_dns_check,
                max_workers=min(10, len(emails))
            )
            
            batch_result = validation_tool.run()
            
            # Apply quality threshold filtering
            accepted_emails = [
                r for r in batch_result['valid_emails'] 
                if r['confidence_score'] >= self.quality_threshold
            ]
            
            batch_time = time.time() - batch_start
            
            batch_summary = {
                'batch_number': batch_num,
                'total_batches': total_batches,
                'emails_processed': len(emails),
                'valid_emails': len(batch_result['valid_emails']),
                'accepted_emails': len(accepted_emails),
                'acceptance_rate': len(accepted_emails) / max(1, len(emails)),
                'processing_time_seconds': batch_time,
                'emails_per_second': len(emails) / max(0.001, batch_time)
            }
            
            batch_summaries.append(batch_summary)
            all_results.extend(batch_result['all_results'])
            
            # Log progress
            logging.info(
                f"Batch {batch_num}/{total_batches}: {len(emails)} emails, "
                f"{len(accepted_emails)} accepted ({batch_summary['acceptance_rate']:.1%}), "
                f"{batch_time:.1f}s"
            )
            
            # Rate limiting delay
            if i + self.batch_size < total_emails and self.rate_limit_delay > 0:
                time.sleep(self.rate_limit_delay)
        
        # Calculate final statistics
        total_time = time.time() - start_time
        total_valid = sum(1 for r in all_results if r['is_valid'])
        total_accepted = sum(
            1 for r in all_results 
            if r['is_valid'] and r['confidence_score'] >= self.quality_threshold
        )
        
        # Quality distribution
        quality_counts = {'high': 0, 'medium': 0, 'low': 0, 'spam': 0}
        for result in all_results:
            quality = result.get('quality', 'spam')
            quality_counts[quality] += 1
        
        # Final accepted emails (sorted by quality and confidence)
        final_emails = [
            r for r in all_results 
            if r['is_valid'] and r['confidence_score'] >= self.quality_threshold
        ]
        
        final_emails.sort(key=lambda x: (
            {'high': 3, 'medium': 2, 'low': 1, 'spam': 0}.get(x['quality'], 0),
            x['confidence_score']
        ), reverse=True)
        
        return {
            'summary': {
                'total_emails': total_emails,
                'total_processed': len(all_results),
                'total_valid': total_valid,
                'total_accepted': total_accepted,
                'overall_acceptance_rate': total_accepted / max(1, total_emails),
                'quality_threshold': self.quality_threshold,
                'total_processing_time_seconds': total_time,
                'average_emails_per_second': len(all_results) / max(0.001, total_time),
                'total_batches': len(batch_summaries)
            },
            'quality_distribution': quality_counts,
            'batch_summaries': batch_summaries,
            'accepted_emails': final_emails,
            'rejected_emails': [r for r in all_results if not r['is_valid']],
            'low_quality_emails': [
                r for r in all_results 
                if r['is_valid'] and r['confidence_score'] < self.quality_threshold
            ]
        }


class EmailQualityAnalysisTool(BaseTool):
    """
    Tool for analyzing email quality and generating insights about contact datasets.
    
    Provides detailed analysis of email patterns, domain distribution,
    and quality metrics for business intelligence.
    """
    
    validation_results: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation results from email validation"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Analyze email quality patterns and generate insights.
        
        Returns:
            Dictionary with comprehensive quality analysis
        """
        if not self.validation_results:
            return {'error': 'No validation results provided'}
        
        # Domain analysis
        domain_stats = {}
        quality_by_domain = {}
        
        # Quality patterns
        quality_patterns = {
            'high_quality_patterns': [],
            'low_quality_patterns': [],
            'business_domains': set(),
            'personal_domains': set()
        }
        
        # Process results
        for result in self.validation_results:
            if not isinstance(result, dict):
                continue
            
            email = result.get('email', '')
            domain = result.get('domain', '')
            quality = result.get('quality', 'spam')
            confidence = result.get('confidence_score', 0.0)
            is_valid = result.get('is_valid', False)
            
            if not domain:
                continue
            
            # Domain statistics
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'total_emails': 0,
                    'valid_emails': 0,
                    'high_quality': 0,
                    'medium_quality': 0,
                    'low_quality': 0,
                    'spam': 0,
                    'avg_confidence': 0.0,
                    'confidence_scores': []
                }
            
            stats = domain_stats[domain]
            stats['total_emails'] += 1
            stats['confidence_scores'].append(confidence)
            
            if is_valid:
                stats['valid_emails'] += 1
                stats[f'{quality}_quality'] += 1
            
            # Classify domain types
            if result.get('is_business_domain'):
                quality_patterns['business_domains'].add(domain)
            if result.get('is_personal_domain'):
                quality_patterns['personal_domains'].add(domain)
            
            # Analyze email patterns
            if quality == 'high' and confidence > 0.7:
                local_part = email.split('@')[0] if '@' in email else ''
                if local_part:
                    quality_patterns['high_quality_patterns'].append(local_part)
            elif quality in ['spam', 'low'] and confidence < 0.3:
                local_part = email.split('@')[0] if '@' in email else ''
                if local_part:
                    quality_patterns['low_quality_patterns'].append(local_part)
        
        # Calculate averages
        for domain, stats in domain_stats.items():
            if stats['confidence_scores']:
                stats['avg_confidence'] = sum(stats['confidence_scores']) / len(stats['confidence_scores'])
                stats['acceptance_rate'] = stats['valid_emails'] / stats['total_emails']
            del stats['confidence_scores']  # Remove raw data
        
        # Sort domains by various metrics
        domains_by_volume = sorted(
            domain_stats.items(), 
            key=lambda x: x[1]['total_emails'], 
            reverse=True
        )[:20]
        
        domains_by_quality = sorted(
            [(d, s) for d, s in domain_stats.items() if s['total_emails'] >= 3],
            key=lambda x: (x[1]['avg_confidence'], x[1]['acceptance_rate']),
            reverse=True
        )[:20]
        
        # Pattern analysis
        from collections import Counter
        
        high_patterns = Counter(quality_patterns['high_quality_patterns']).most_common(10)
        low_patterns = Counter(quality_patterns['low_quality_patterns']).most_common(10)
        
        # Overall metrics
        total_emails = len(self.validation_results)
        valid_emails = sum(1 for r in self.validation_results if r.get('is_valid'))
        high_quality = sum(1 for r in self.validation_results if r.get('quality') == 'high')
        
        return {
            'overview': {
                'total_emails_analyzed': total_emails,
                'valid_emails': valid_emails,
                'high_quality_emails': high_quality,
                'overall_acceptance_rate': valid_emails / max(1, total_emails),
                'high_quality_rate': high_quality / max(1, valid_emails),
                'unique_domains': len(domain_stats),
                'business_domains': len(quality_patterns['business_domains']),
                'personal_domains': len(quality_patterns['personal_domains'])
            },
            'domain_analysis': {
                'top_domains_by_volume': [
                    {'domain': d, 'stats': s} for d, s in domains_by_volume
                ],
                'top_domains_by_quality': [
                    {'domain': d, 'stats': s} for d, s in domains_by_quality
                ],
                'business_domains': list(quality_patterns['business_domains'])[:20],
                'personal_domains': list(quality_patterns['personal_domains'])[:20]
            },
            'pattern_analysis': {
                'high_quality_patterns': [
                    {'pattern': pattern, 'count': count} 
                    for pattern, count in high_patterns
                ],
                'low_quality_patterns': [
                    {'pattern': pattern, 'count': count} 
                    for pattern, count in low_patterns
                ]
            },
            'recommendations': self._generate_recommendations(
                domain_stats, quality_patterns, total_emails, valid_emails
            )
        }
    
    def _generate_recommendations(self, domain_stats, quality_patterns, 
                                total_emails, valid_emails) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Acceptance rate recommendations
        acceptance_rate = valid_emails / max(1, total_emails)
        if acceptance_rate < 0.5:
            recommendations.append(
                "Low acceptance rate detected. Consider reviewing email sources "
                "and improving data quality at collection time."
            )
        
        # Domain diversity recommendations
        if len(domain_stats) < total_emails * 0.1:
            recommendations.append(
                "Low domain diversity detected. Consider expanding data sources "
                "to capture more varied business contacts."
            )
        
        # Personal vs business domain recommendations
        personal_ratio = len(quality_patterns['personal_domains']) / max(1, len(domain_stats))
        if personal_ratio > 0.3:
            recommendations.append(
                "High proportion of personal email domains detected. Consider "
                "filtering for business domains to improve lead quality."
            )
        
        # Quality pattern recommendations
        if len(quality_patterns['high_quality_patterns']) < 5:
            recommendations.append(
                "Limited high-quality email patterns detected. Consider targeting "
                "specific professional email formats (e.g., firstname.lastname@company.com)."
            )
        
        return recommendations