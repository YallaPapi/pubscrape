"""
Mailtester Ninja Email Validation Tool

Agency Swarm tool for comprehensive email validation using the Mailtester Ninja API.
Provides real API-based validation with proper handling of all response types.
"""

import logging
import time
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

from .mailtester_ninja_client import (
    MailtesterNinjaClient, MailtesterResult, ValidationLevel, 
    EmailStatus, create_mailtester_client
)


class MailtesterEmailValidationTool(BaseTool):
    """
    Tool for validating email addresses using the Mailtester Ninja API.
    
    Provides comprehensive email validation with real-time API checks,
    deliverability verification, and quality scoring based on Mailtester Ninja results.
    """
    
    emails: List[str] = Field(
        ..., 
        description="List of email addresses to validate using Mailtester Ninja API"
    )
    
    validation_level: str = Field(
        default="basic",
        description="Validation level: 'basic' for syntax/domain checks, 'full' for SMTP verification"
    )
    
    enable_caching: bool = Field(
        default=True,
        description="Enable caching of validation results to reduce API calls"
    )
    
    rate_limit_delay: float = Field(
        default=0.1,
        description="Delay between API requests in seconds for rate limiting"
    )
    
    quality_threshold: float = Field(
        default=0.5,
        description="Minimum quality score threshold for accepting emails (0.0-1.0)"
    )
    
    batch_size: int = Field(
        default=50,
        description="Number of emails to validate per batch (for large lists)"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Validate email addresses using Mailtester Ninja API and return results.
        
        Returns:
            Dictionary containing validation results and statistics
        """
        start_time = time.time()
        
        if not self.emails:
            return {
                'error': 'No emails provided for validation',
                'summary': {
                    'total_emails': 0,
                    'valid_emails': 0,
                    'invalid_emails': 0,
                    'processing_time_seconds': 0
                }
            }
        
        try:
            # Parse validation level
            try:
                validation_level = ValidationLevel(self.validation_level.lower())
            except ValueError:
                validation_level = ValidationLevel.BASIC
            
            # Initialize Mailtester client
            with create_mailtester_client(
                enable_caching=self.enable_caching,
                rate_limit_delay=self.rate_limit_delay
            ) as client:
                
                # Validate emails
                if len(self.emails) > self.batch_size:
                    # Use batch validation for large lists
                    results = client.validate_batch(
                        self.emails, 
                        validation_level=validation_level,
                        batch_size=self.batch_size
                    )
                else:
                    # Validate individually for smaller lists
                    results = [
                        client.validate_email(email, validation_level)
                        for email in self.emails
                    ]
                
                # Process results
                processed_results = self._process_validation_results(results)
                
                # Get client statistics
                client_stats = client.get_stats()
                
                # Calculate summary metrics
                total_time = time.time() - start_time
                
                return {
                    'summary': {
                        'total_emails': len(self.emails),
                        'processed_emails': len(results),
                        'valid_emails': processed_results['counts']['valid'],
                        'invalid_emails': processed_results['counts']['invalid'],
                        'risky_emails': processed_results['counts']['risky'],
                        'catch_all_emails': processed_results['counts']['catch_all'],
                        'unknown_emails': processed_results['counts']['unknown'],
                        'acceptance_rate': processed_results['acceptance_rate'],
                        'processing_time_seconds': total_time,
                        'average_response_time_ms': client_stats.get('average_response_time_ms', 0),
                        'validation_level': validation_level.value,
                        'quality_threshold': self.quality_threshold
                    },
                    'api_stats': client_stats,
                    'quality_distribution': processed_results['quality_distribution'],
                    'status_distribution': processed_results['status_distribution'],
                    'valid_emails': processed_results['valid_emails'],
                    'invalid_emails': processed_results['invalid_emails'],
                    'risky_emails': processed_results['risky_emails'],
                    'accepted_emails': processed_results['accepted_emails'],
                    'rejected_emails': processed_results['rejected_emails'],
                    'all_results': [result.to_dict() for result in results]
                }
                
        except Exception as e:
            logging.error(f"Mailtester validation failed: {e}")
            return {
                'error': f"Validation failed: {str(e)}",
                'summary': {
                    'total_emails': len(self.emails),
                    'valid_emails': 0,
                    'invalid_emails': 0,
                    'processing_time_seconds': time.time() - start_time
                }
            }
    
    def _process_validation_results(self, results: List[MailtesterResult]) -> Dict[str, Any]:
        """Process validation results and generate statistics"""
        
        # Initialize counters
        counts = {
            'valid': 0,
            'invalid': 0,
            'risky': 0,
            'catch_all': 0,
            'unknown': 0
        }
        
        quality_counts = {
            'high': 0,     # score >= 0.8
            'medium': 0,   # score >= 0.5
            'low': 0,      # score >= 0.2
            'very_low': 0  # score < 0.2
        }
        
        # Categorized results
        valid_emails = []
        invalid_emails = []
        risky_emails = []
        accepted_emails = []
        rejected_emails = []
        
        for result in results:
            # Count by status
            status_key = result.status.value
            if status_key in counts:
                counts[status_key] += 1
            
            # Count by quality
            quality_score = result.get_quality_score()
            if quality_score >= 0.8:
                quality_counts['high'] += 1
            elif quality_score >= 0.5:
                quality_counts['medium'] += 1
            elif quality_score >= 0.2:
                quality_counts['low'] += 1
            else:
                quality_counts['very_low'] += 1
            
            # Categorize results
            result_dict = result.to_dict()
            
            if result.status == EmailStatus.VALID:
                valid_emails.append(result_dict)
            elif result.status == EmailStatus.INVALID:
                invalid_emails.append(result_dict)
            elif result.status == EmailStatus.RISKY:
                risky_emails.append(result_dict)
            
            # Apply quality threshold for acceptance
            if result.is_deliverable() and quality_score >= self.quality_threshold:
                accepted_emails.append(result_dict)
            else:
                rejected_emails.append(result_dict)
        
        # Calculate rates
        total = len(results)
        acceptance_rate = len(accepted_emails) / max(1, total)
        
        # Sort accepted emails by quality score
        accepted_emails.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return {
            'counts': counts,
            'quality_distribution': quality_counts,
            'status_distribution': {
                status: count / max(1, total) for status, count in counts.items()
            },
            'acceptance_rate': acceptance_rate,
            'valid_emails': valid_emails,
            'invalid_emails': invalid_emails,
            'risky_emails': risky_emails,
            'accepted_emails': accepted_emails,
            'rejected_emails': rejected_emails
        }


class MailtesterBulkValidationTool(BaseTool):
    """
    Tool for bulk email validation using Mailtester Ninja API with enhanced
    processing capabilities for large datasets.
    """
    
    email_data: List[Dict[str, Any]] = Field(
        ...,
        description="List of email data objects with 'email' field and optional contact info"
    )
    
    validation_level: str = Field(
        default="basic",
        description="Validation level: 'basic' for syntax/domain checks, 'full' for SMTP verification"
    )
    
    batch_size: int = Field(
        default=100,
        description="Number of emails to process in each batch"
    )
    
    quality_threshold: float = Field(
        default=0.6,
        description="Minimum quality score threshold for accepting emails (0.0-1.0)"
    )
    
    rate_limit_delay: float = Field(
        default=0.15,
        description="Delay between batches in seconds for rate limiting"
    )
    
    enable_progress_logging: bool = Field(
        default=True,
        description="Enable progress logging for large batch processing"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Process large email datasets in batches using Mailtester Ninja API.
        
        Returns:
            Dictionary with comprehensive batch processing results
        """
        start_time = time.time()
        
        if not self.email_data:
            return self._empty_result("No email data provided for validation")
        
        try:
            # Parse validation level
            try:
                validation_level = ValidationLevel(self.validation_level.lower())
            except ValueError:
                validation_level = ValidationLevel.BASIC
            
            # Extract emails from data
            emails = []
            email_to_data = {}
            
            for item in self.email_data:
                email = item.get('email', '').strip()
                if email:
                    emails.append(email)
                    email_to_data[email] = item
            
            if not emails:
                return self._empty_result("No valid email addresses found in provided data")
            
            # Process in batches
            with create_mailtester_client(
                enable_caching=True,
                rate_limit_delay=self.rate_limit_delay
            ) as client:
                
                all_results = []
                batch_summaries = []
                
                total_batches = (len(emails) + self.batch_size - 1) // self.batch_size
                
                for i in range(0, len(emails), self.batch_size):
                    batch_start_time = time.time()
                    batch_emails = emails[i:i + self.batch_size]
                    batch_num = (i // self.batch_size) + 1
                    
                    if self.enable_progress_logging:
                        logging.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_emails)} emails)")
                    
                    # Validate batch
                    batch_results = client.validate_batch(
                        batch_emails,
                        validation_level=validation_level,
                        batch_size=len(batch_emails)
                    )
                    
                    # Enrich results with contact data
                    enriched_results = []
                    for result in batch_results:
                        enriched_result = result.to_dict()
                        
                        # Add contact information if available
                        contact_data = email_to_data.get(result.email, {})
                        enriched_result.update({
                            'contact_name': contact_data.get('name', ''),
                            'contact_title': contact_data.get('title', ''),
                            'contact_company': contact_data.get('company', ''),
                            'source_url': contact_data.get('source_url', ''),
                            'discovery_method': contact_data.get('discovery_method', '')
                        })
                        
                        enriched_results.append(enriched_result)
                    
                    all_results.extend(enriched_results)
                    
                    # Calculate batch statistics
                    batch_accepted = sum(
                        1 for r in batch_results 
                        if r.is_deliverable() and r.get_quality_score() >= self.quality_threshold
                    )
                    
                    batch_time = time.time() - batch_start_time
                    
                    batch_summary = {
                        'batch_number': batch_num,
                        'total_batches': total_batches,
                        'emails_processed': len(batch_emails),
                        'accepted_emails': batch_accepted,
                        'acceptance_rate': batch_accepted / len(batch_emails),
                        'processing_time_seconds': batch_time,
                        'emails_per_second': len(batch_emails) / max(0.001, batch_time)
                    }
                    
                    batch_summaries.append(batch_summary)
                    
                    if self.enable_progress_logging:
                        logging.info(
                            f"Batch {batch_num} completed: {batch_accepted}/{len(batch_emails)} accepted "
                            f"({batch_summary['acceptance_rate']:.1%}), {batch_time:.1f}s"
                        )
                
                # Process final results
                final_results = self._process_bulk_results(all_results)
                client_stats = client.get_stats()
                
                total_time = time.time() - start_time
                
                return {
                    'summary': {
                        'total_email_records': len(self.email_data),
                        'valid_emails_found': len(emails),
                        'total_processed': len(all_results),
                        'total_accepted': len(final_results['accepted_contacts']),
                        'overall_acceptance_rate': final_results['acceptance_rate'],
                        'validation_level': validation_level.value,
                        'quality_threshold': self.quality_threshold,
                        'total_processing_time_seconds': total_time,
                        'average_emails_per_second': len(all_results) / max(0.001, total_time),
                        'total_batches': len(batch_summaries)
                    },
                    'api_stats': client_stats,
                    'batch_summaries': batch_summaries,
                    'quality_distribution': final_results['quality_distribution'],
                    'status_distribution': final_results['status_distribution'],
                    'accepted_contacts': final_results['accepted_contacts'],
                    'rejected_contacts': final_results['rejected_contacts'],
                    'high_quality_contacts': final_results['high_quality_contacts'],
                    'risky_contacts': final_results['risky_contacts'],
                    'all_results': all_results
                }
                
        except Exception as e:
            logging.error(f"Bulk validation failed: {e}")
            return self._empty_result(f"Bulk validation failed: {str(e)}")
    
    def _process_bulk_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process bulk validation results"""
        
        # Initialize counters
        status_counts = {'valid': 0, 'invalid': 0, 'risky': 0, 'catch_all': 0, 'unknown': 0}
        quality_counts = {'high': 0, 'medium': 0, 'low': 0, 'very_low': 0}
        
        # Categorized results
        accepted_contacts = []
        rejected_contacts = []
        high_quality_contacts = []
        risky_contacts = []
        
        for result in results:
            # Count by status
            status = result.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
            
            # Count by quality
            score = result.get('score', 0.0)
            if score >= 0.8:
                quality_counts['high'] += 1
            elif score >= 0.5:
                quality_counts['medium'] += 1
            elif score >= 0.2:
                quality_counts['low'] += 1
            else:
                quality_counts['very_low'] += 1
            
            # Categorize contacts
            is_deliverable = (
                result.get('is_valid_format', False) and
                result.get('domain_exists', False) and
                result.get('has_mx_records', False) and
                not result.get('is_disposable', True)
            )
            
            quality_score = score  # Use raw score for now
            
            if is_deliverable and quality_score >= self.quality_threshold:
                accepted_contacts.append(result)
                
                if quality_score >= 0.8:
                    high_quality_contacts.append(result)
            else:
                rejected_contacts.append(result)
            
            if status == 'risky':
                risky_contacts.append(result)
        
        # Sort contacts by quality score
        accepted_contacts.sort(key=lambda x: x.get('score', 0), reverse=True)
        high_quality_contacts.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        total = len(results)
        acceptance_rate = len(accepted_contacts) / max(1, total)
        
        return {
            'acceptance_rate': acceptance_rate,
            'status_distribution': {k: v / max(1, total) for k, v in status_counts.items()},
            'quality_distribution': {k: v / max(1, total) for k, v in quality_counts.items()},
            'accepted_contacts': accepted_contacts,
            'rejected_contacts': rejected_contacts,
            'high_quality_contacts': high_quality_contacts,
            'risky_contacts': risky_contacts
        }
    
    def _empty_result(self, error_message: str) -> Dict[str, Any]:
        """Return empty result structure with error message"""
        return {
            'error': error_message,
            'summary': {
                'total_email_records': len(self.email_data) if hasattr(self, 'email_data') else 0,
                'valid_emails_found': 0,
                'total_processed': 0,
                'total_accepted': 0,
                'overall_acceptance_rate': 0.0,
                'total_processing_time_seconds': 0.0
            },
            'accepted_contacts': [],
            'rejected_contacts': [],
            'all_results': []
        }


class MailtesterEmailQualityAnalyzer(BaseTool):
    """
    Tool for analyzing email quality patterns and generating insights from
    Mailtester Ninja validation results.
    """
    
    validation_results: List[Dict[str, Any]] = Field(
        ...,
        description="List of validation results from Mailtester Ninja validation"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Analyze email quality patterns and generate actionable insights.
        
        Returns:
            Dictionary with comprehensive quality analysis and recommendations
        """
        if not self.validation_results:
            return {'error': 'No validation results provided for analysis'}
        
        # Domain analysis
        domain_stats = {}
        provider_analysis = {}
        quality_patterns = {
            'high_quality_domains': set(),
            'low_quality_domains': set(),
            'disposable_providers': set(),
            'business_domains': set(),
            'personal_domains': set()
        }
        
        # Status and quality metrics
        status_counts = {}
        quality_levels = {'high': 0, 'medium': 0, 'low': 0, 'very_low': 0}
        
        # SMTP and deliverability insights
        smtp_insights = {
            'catch_all_domains': set(),
            'verified_mailboxes': 0,
            'unverified_mailboxes': 0,
            'smtp_failures': 0
        }
        
        # Process each result
        for result in self.validation_results:
            email = result.get('email', '')
            domain = email.split('@')[-1] if '@' in email else 'unknown'
            status = result.get('status', 'unknown')
            score = result.get('score', 0.0)
            is_disposable = result.get('is_disposable', False)
            is_role_account = result.get('is_role_account', False)
            smtp_check = result.get('smtp_check', {})
            
            # Domain statistics
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'total_emails': 0,
                    'valid_emails': 0,
                    'average_score': 0.0,
                    'scores': [],
                    'disposable_count': 0,
                    'role_account_count': 0,
                    'smtp_verified': 0
                }
            
            stats = domain_stats[domain]
            stats['total_emails'] += 1
            stats['scores'].append(score)
            
            if status == 'valid':
                stats['valid_emails'] += 1
            
            if is_disposable:
                stats['disposable_count'] += 1
                quality_patterns['disposable_providers'].add(domain)
            
            if is_role_account:
                stats['role_account_count'] += 1
                quality_patterns['business_domains'].add(domain)
            
            if smtp_check and smtp_check.get('mailbox_exists'):
                stats['smtp_verified'] += 1
                smtp_insights['verified_mailboxes'] += 1
            elif smtp_check and not smtp_check.get('can_connect'):
                smtp_insights['smtp_failures'] += 1
            else:
                smtp_insights['unverified_mailboxes'] += 1
            
            if smtp_check and smtp_check.get('is_catch_all'):
                smtp_insights['catch_all_domains'].add(domain)
            
            # Status counting
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Quality level counting
            if score >= 0.8:
                quality_levels['high'] += 1
                quality_patterns['high_quality_domains'].add(domain)
            elif score >= 0.5:
                quality_levels['medium'] += 1
            elif score >= 0.2:
                quality_levels['low'] += 1
            else:
                quality_levels['very_low'] += 1
                quality_patterns['low_quality_domains'].add(domain)
            
            # Classify domain types
            if self._is_personal_domain(domain):
                quality_patterns['personal_domains'].add(domain)
            elif self._is_business_domain(domain):
                quality_patterns['business_domains'].add(domain)
        
        # Calculate domain averages
        for domain, stats in domain_stats.items():
            if stats['scores']:
                stats['average_score'] = sum(stats['scores']) / len(stats['scores'])
                stats['acceptance_rate'] = stats['valid_emails'] / stats['total_emails']
            del stats['scores']  # Remove raw data
        
        # Sort domains by various metrics
        top_domains_by_volume = sorted(
            domain_stats.items(), 
            key=lambda x: x[1]['total_emails'], 
            reverse=True
        )[:15]
        
        top_domains_by_quality = sorted(
            [(d, s) for d, s in domain_stats.items() if s['total_emails'] >= 3],
            key=lambda x: x[1]['average_score'],
            reverse=True
        )[:15]
        
        # Overall metrics
        total = len(self.validation_results)
        valid_count = status_counts.get('valid', 0)
        
        return {
            'overview': {
                'total_emails_analyzed': total,
                'valid_emails': valid_count,
                'acceptance_rate': valid_count / max(1, total),
                'high_quality_emails': quality_levels['high'],
                'high_quality_rate': quality_levels['high'] / max(1, total),
                'unique_domains': len(domain_stats),
                'disposable_domains': len(quality_patterns['disposable_providers']),
                'catch_all_domains': len(smtp_insights['catch_all_domains'])
            },
            'status_distribution': {
                status: count / max(1, total) 
                for status, count in status_counts.items()
            },
            'quality_distribution': {
                level: count / max(1, total)
                for level, count in quality_levels.items()
            },
            'domain_analysis': {
                'top_domains_by_volume': [
                    {'domain': d, 'stats': s} for d, s in top_domains_by_volume
                ],
                'top_domains_by_quality': [
                    {'domain': d, 'stats': s} for d, s in top_domains_by_quality
                ],
                'high_quality_domains': list(quality_patterns['high_quality_domains'])[:20],
                'low_quality_domains': list(quality_patterns['low_quality_domains'])[:20],
                'disposable_providers': list(quality_patterns['disposable_providers'])[:20],
                'business_domains': list(quality_patterns['business_domains'])[:20],
                'personal_domains': list(quality_patterns['personal_domains'])[:20]
            },
            'smtp_insights': {
                'verified_mailboxes': smtp_insights['verified_mailboxes'],
                'unverified_mailboxes': smtp_insights['unverified_mailboxes'],
                'smtp_failures': smtp_insights['smtp_failures'],
                'catch_all_domains': list(smtp_insights['catch_all_domains'])[:20],
                'verification_rate': smtp_insights['verified_mailboxes'] / max(1, total)
            },
            'recommendations': self._generate_recommendations(
                domain_stats, quality_patterns, smtp_insights, total, valid_count
            )
        }
    
    def _is_personal_domain(self, domain: str) -> bool:
        """Check if domain is a personal email provider"""
        personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'me.com', 'protonmail.com',
            'tutanota.com', 'fastmail.com', 'zoho.com', 'yandex.com'
        }
        return domain.lower() in personal_domains
    
    def _is_business_domain(self, domain: str) -> bool:
        """Check if domain appears to be business-oriented"""
        business_indicators = [
            'corp', 'inc', 'ltd', 'llc', 'company', 'enterprises',
            'group', 'solutions', 'consulting', 'services'
        ]
        domain_lower = domain.lower()
        return any(indicator in domain_lower for indicator in business_indicators)
    
    def _generate_recommendations(self, domain_stats, quality_patterns, smtp_insights, total, valid_count) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        acceptance_rate = valid_count / max(1, total)
        
        if acceptance_rate < 0.4:
            recommendations.append(
                "Low acceptance rate detected. Consider improving email source quality "
                "or implementing pre-filtering before validation."
            )
        
        if len(quality_patterns['disposable_providers']) > total * 0.1:
            recommendations.append(
                "High number of disposable email providers detected. Consider filtering "
                "out known disposable domains to improve lead quality."
            )
        
        if smtp_insights['smtp_failures'] > total * 0.2:
            recommendations.append(
                "High SMTP failure rate detected. Consider using basic validation for "
                "initial filtering and full validation for final verification."
            )
        
        if len(quality_patterns['personal_domains']) > len(quality_patterns['business_domains']):
            recommendations.append(
                "More personal domains than business domains detected. For B2B targeting, "
                "consider filtering for business email domains."
            )
        
        catch_all_rate = len(smtp_insights['catch_all_domains']) / max(1, len(domain_stats))
        if catch_all_rate > 0.3:
            recommendations.append(
                "High catch-all domain rate detected. These emails may have lower "
                "deliverability. Consider applying additional scoring penalties."
            )
        
        return recommendations