"""
Blacklist Filter Tool

Agency Swarm tool for filtering email addresses using configurable blacklist patterns.
Supports regex patterns, exact matches, domain-based filtering, and bulk processing.
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from pydantic import Field
from dataclasses import dataclass

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


@dataclass
class BlacklistResult:
    """Result of blacklist filtering for an email"""
    email: str
    is_blacklisted: bool = False
    matched_pattern: Optional[str] = None
    pattern_type: str = "none"  # "regex", "exact", "domain"
    reason: str = ""
    confidence: float = 1.0  # Confidence in the blacklist decision
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'email': self.email,
            'is_blacklisted': self.is_blacklisted,
            'matched_pattern': self.matched_pattern,
            'pattern_type': self.pattern_type,
            'reason': self.reason,
            'confidence': self.confidence
        }


class BlacklistFilterTool(BaseTool):
    """
    Tool for filtering emails using configurable blacklist patterns.
    
    Supports multiple pattern types including regex, exact matches, and 
    domain-based filtering with detailed reporting.
    """
    
    emails: List[str] = Field(
        ...,
        description="List of email addresses to filter"
    )
    
    regex_patterns: Optional[List[str]] = Field(
        default=None,
        description="List of regex patterns for blacklist filtering"
    )
    
    exact_patterns: Optional[List[str]] = Field(
        default=None,
        description="List of exact email patterns to blacklist"
    )
    
    domain_blacklist: Optional[List[str]] = Field(
        default=None,
        description="List of domains to blacklist entirely"
    )
    
    use_default_patterns: bool = Field(
        default=True,
        description="Include default blacklist patterns for common unwanted emails"
    )
    
    case_sensitive: bool = Field(
        default=False,
        description="Enable case-sensitive pattern matching"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Filter emails using blacklist patterns.
        
        Returns:
            Dictionary with filtering results and statistics
        """
        start_time = time.time()
        
        # Initialize patterns
        all_patterns = self._initialize_patterns()
        
        # Process emails
        results = []
        stats = {
            'total_processed': 0,
            'blacklisted': 0,
            'allowed': 0,
            'pattern_matches': Counter()
        }
        
        for email in self.emails:
            if not email or not isinstance(email, str):
                continue
            
            result = self._check_email_against_blacklist(email, all_patterns)
            results.append(result)
            
            stats['total_processed'] += 1
            
            if result.is_blacklisted:
                stats['blacklisted'] += 1
                if result.matched_pattern:
                    stats['pattern_matches'][result.matched_pattern] += 1
            else:
                stats['allowed'] += 1
        
        # Generate analysis
        analysis = self._analyze_blacklist_results(results)
        
        processing_time = time.time() - start_time
        
        # Separate allowed and blacklisted emails
        allowed_emails = [r.email for r in results if not r.is_blacklisted]
        blacklisted_emails = [r.to_dict() for r in results if r.is_blacklisted]
        
        return {
            'summary': {
                'total_emails': len(self.emails),
                'processed': stats['total_processed'],
                'allowed': stats['allowed'],
                'blacklisted': stats['blacklisted'],
                'blacklist_rate': stats['blacklisted'] / max(1, stats['total_processed']),
                'processing_time_seconds': processing_time
            },
            'filtering_stats': dict(stats),
            'pattern_analysis': analysis,
            'allowed_emails': allowed_emails,
            'blacklisted_emails': blacklisted_emails,
            'all_results': [r.to_dict() for r in results],
            'configuration': {
                'regex_patterns': self.regex_patterns or [],
                'exact_patterns': self.exact_patterns or [],
                'domain_blacklist': self.domain_blacklist or [],
                'use_default_patterns': self.use_default_patterns,
                'case_sensitive': self.case_sensitive
            }
        }
    
    def _initialize_patterns(self) -> Dict[str, List[Tuple[str, str]]]:
        """Initialize all blacklist patterns by type"""
        patterns = {
            'regex': [],
            'exact': [],
            'domain': []
        }
        
        # Add default patterns if enabled
        if self.use_default_patterns:
            default_patterns = self._get_default_patterns()
            patterns['regex'].extend([(p, 'default') for p in default_patterns['regex']])
            patterns['exact'].extend([(p, 'default') for p in default_patterns['exact']])
            patterns['domain'].extend([(p, 'default') for p in default_patterns['domain']])
        
        # Add custom patterns
        if self.regex_patterns:
            patterns['regex'].extend([(p, 'custom') for p in self.regex_patterns])
        
        if self.exact_patterns:
            patterns['exact'].extend([(p, 'custom') for p in self.exact_patterns])
        
        if self.domain_blacklist:
            patterns['domain'].extend([(p, 'custom') for p in self.domain_blacklist])
        
        # Compile regex patterns
        compiled_regex = []
        for pattern, source in patterns['regex']:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(pattern, flags)
                compiled_regex.append((compiled_pattern, pattern, source))
            except re.error as e:
                logging.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        patterns['compiled_regex'] = compiled_regex
        
        return patterns
    
    def _get_default_patterns(self) -> Dict[str, List[str]]:
        """Get default blacklist patterns"""
        return {
            'regex': [
                # No-reply patterns
                r'^no-?reply@',
                r'^donotreply@',
                r'^bounce@',
                r'^unsubscribe@',
                
                # Placeholder/test patterns
                r'^(test|testing|example|placeholder)@',
                r'^(dummy|fake|temp|temporary)@',
                r'^(sample|demo)@',
                
                # System/admin patterns
                r'^(admin|administrator|root|system)@',
                r'^(webmaster|postmaster|hostmaster)@',
                r'^(daemon|mailer-daemon|mail-daemon)@',
                r'^(listserv|majordomo)@',
                
                # Generic/automated patterns
                r'^(newsletter|news|updates)@',
                r'^(marketing|promo|promotions)@',
                r'^(billing|invoice|accounting)@',
                r'^(legal|abuse|security)@',
                
                # Privacy patterns
                r'^(privacy|anonymous|anon)@',
                r'^(devnull|null|void)@',
                
                # Suspicious patterns
                r'^[a-z]{1,2}@',  # Very short local parts
                r'^[0-9]+@',  # Numeric only local parts
                r'^[a-z]{20,}@',  # Very long local parts
                
                # Domain patterns
                r'@.*\.(local|test|dev|localhost)$',
                r'@example\.',
                r'@.*\.invalid$',
                r'@.*\.test$',
                
                # Temporary email services
                r'@(10minutemail|guerrillamail|mailinator|tempmail)\.com$',
                r'@.*temp.*\.com$',
                r'@.*disposable.*\.',
            ],
            'exact': [
                # Common exact matches
                'info@example.com',
                'test@test.com',
                'admin@localhost',
                'root@localhost',
                'nobody@nowhere.com',
            ],
            'domain': [
                # Test domains
                'example.com',
                'example.org',
                'example.net',
                'test.com',
                'localhost',
                'invalid',
                
                # Temporary email domains
                '10minutemail.com',
                'guerrillamail.com',
                'mailinator.com',
                'tempmail.org',
                'yopmail.com',
                'sharklasers.com',
                'grr.la',
                'guerrillamailblock.com',
            ]
        }
    
    def _check_email_against_blacklist(self, email: str, patterns: Dict[str, List]) -> BlacklistResult:
        """Check a single email against all blacklist patterns"""
        
        # Normalize email for checking
        check_email = email if self.case_sensitive else email.lower()
        
        # Check regex patterns
        for compiled_pattern, original_pattern, source in patterns['compiled_regex']:
            if compiled_pattern.search(check_email):
                return BlacklistResult(
                    email=email,
                    is_blacklisted=True,
                    matched_pattern=original_pattern,
                    pattern_type='regex',
                    reason=f'Matched regex pattern: {original_pattern} ({source})',
                    confidence=0.9
                )
        
        # Check exact patterns
        for pattern, source in patterns['exact']:
            pattern_check = pattern if self.case_sensitive else pattern.lower()
            if check_email == pattern_check:
                return BlacklistResult(
                    email=email,
                    is_blacklisted=True,
                    matched_pattern=pattern,
                    pattern_type='exact',
                    reason=f'Exact match: {pattern} ({source})',
                    confidence=1.0
                )
        
        # Check domain patterns
        if '@' in email:
            domain = email.split('@')[1]
            domain_check = domain if self.case_sensitive else domain.lower()
            
            for pattern, source in patterns['domain']:
                pattern_check = pattern if self.case_sensitive else pattern.lower()
                if domain_check == pattern_check:
                    return BlacklistResult(
                        email=email,
                        is_blacklisted=True,
                        matched_pattern=pattern,
                        pattern_type='domain',
                        reason=f'Domain blacklisted: {pattern} ({source})',
                        confidence=1.0
                    )
        
        # Email is not blacklisted
        return BlacklistResult(
            email=email,
            is_blacklisted=False,
            reason='Passed all blacklist checks'
        )
    
    def _analyze_blacklist_results(self, results: List[BlacklistResult]) -> Dict[str, Any]:
        """Analyze blacklist filtering results for insights"""
        
        # Pattern effectiveness analysis
        pattern_stats = defaultdict(lambda: {
            'matches': 0,
            'emails': [],
            'pattern_type': 'unknown'
        })
        
        # Domain analysis
        domain_stats = defaultdict(lambda: {
            'total': 0,
            'blacklisted': 0,
            'allowed': 0
        })
        
        # Reason analysis
        reason_categories = Counter()
        
        for result in results:
            # Extract domain for analysis
            if '@' in result.email:
                domain = result.email.split('@')[1].lower()
                domain_stats[domain]['total'] += 1
                
                if result.is_blacklisted:
                    domain_stats[domain]['blacklisted'] += 1
                else:
                    domain_stats[domain]['allowed'] += 1
            
            # Pattern effectiveness
            if result.is_blacklisted and result.matched_pattern:
                pattern_stats[result.matched_pattern]['matches'] += 1
                pattern_stats[result.matched_pattern]['emails'].append(result.email)
                pattern_stats[result.matched_pattern]['pattern_type'] = result.pattern_type
            
            # Reason categorization
            if result.is_blacklisted:
                # Extract category from reason
                reason_lower = result.reason.lower()
                if 'no-reply' in reason_lower or 'noreply' in reason_lower:
                    reason_categories['noreply_emails'] += 1
                elif 'test' in reason_lower or 'placeholder' in reason_lower:
                    reason_categories['test_emails'] += 1
                elif 'admin' in reason_lower or 'system' in reason_lower:
                    reason_categories['system_emails'] += 1
                elif 'domain' in reason_lower:
                    reason_categories['domain_blacklist'] += 1
                else:
                    reason_categories['other_patterns'] += 1
        
        # Top blacklisted domains
        blacklisted_domains = [
            (domain, stats['blacklisted'])
            for domain, stats in domain_stats.items()
            if stats['blacklisted'] > 0
        ]
        blacklisted_domains.sort(key=lambda x: x[1], reverse=True)
        
        # Most effective patterns
        effective_patterns = [
            {
                'pattern': pattern,
                'matches': stats['matches'],
                'pattern_type': stats['pattern_type'],
                'sample_emails': stats['emails'][:5]  # Show first 5 matches
            }
            for pattern, stats in pattern_stats.items()
        ]
        effective_patterns.sort(key=lambda x: x['matches'], reverse=True)
        
        return {
            'pattern_effectiveness': {
                'most_effective_patterns': effective_patterns[:10],
                'total_patterns_matched': len(pattern_stats),
                'avg_matches_per_pattern': sum(s['matches'] for s in pattern_stats.values()) / max(1, len(pattern_stats))
            },
            'domain_analysis': {
                'domains_with_blacklisted_emails': len(blacklisted_domains),
                'top_blacklisted_domains': blacklisted_domains[:10],
                'total_unique_domains': len(domain_stats)
            },
            'reason_categories': dict(reason_categories.most_common()),
            'recommendations': self._generate_blacklist_recommendations(
                pattern_stats, domain_stats, reason_categories
            )
        }
    
    def _generate_blacklist_recommendations(self, pattern_stats, domain_stats, 
                                          reason_categories) -> List[str]:
        """Generate actionable recommendations based on blacklist analysis"""
        recommendations = []
        
        # Pattern effectiveness recommendations
        unused_patterns = [p for p, s in pattern_stats.items() if s['matches'] == 0]
        if len(unused_patterns) > len(pattern_stats) * 0.3:
            recommendations.append(
                f"Many patterns ({len(unused_patterns)}) had no matches. "
                "Consider reviewing and removing unused patterns to improve performance."
            )
        
        # Domain concentration recommendations
        total_blacklisted = sum(s['blacklisted'] for s in domain_stats.values())
        domains_with_blacklisted = len([d for d, s in domain_stats.items() if s['blacklisted'] > 0])
        
        if domains_with_blacklisted < len(domain_stats) * 0.1 and total_blacklisted > 10:
            recommendations.append(
                "Blacklisted emails are concentrated in a few domains. "
                "Consider adding domain-level blacklist rules for efficiency."
            )
        
        # Category-specific recommendations
        if reason_categories.get('noreply_emails', 0) > total_blacklisted * 0.3:
            recommendations.append(
                "High number of no-reply emails detected. "
                "Consider strengthening no-reply detection patterns."
            )
        
        if reason_categories.get('test_emails', 0) > total_blacklisted * 0.2:
            recommendations.append(
                "Many test/placeholder emails found. "
                "Consider improving data source quality to reduce test data."
            )
        
        # Performance recommendations
        regex_patterns = len([p for p, s in pattern_stats.items() if s['pattern_type'] == 'regex'])
        if regex_patterns > 20:
            recommendations.append(
                f"Large number of regex patterns ({regex_patterns}) may impact performance. "
                "Consider consolidating similar patterns or using exact/domain matching where possible."
            )
        
        return recommendations


class AdvancedBlacklistTool(BaseTool):
    """
    Advanced blacklist filtering tool with machine learning-based pattern detection.
    
    Uses statistical analysis to identify potential spam patterns and 
    automatically generate blacklist recommendations.
    """
    
    emails: List[str] = Field(
        ...,
        description="List of email addresses to analyze and filter"
    )
    
    confidence_threshold: float = Field(
        default=0.8,
        description="Confidence threshold for automatic blacklist suggestions"
    )
    
    min_pattern_frequency: int = Field(
        default=3,
        description="Minimum frequency for a pattern to be considered for blacklisting"
    )
    
    analyze_patterns: bool = Field(
        default=True,
        description="Enable automatic pattern analysis and suggestions"
    )
    
    learn_from_existing: bool = Field(
        default=True,
        description="Learn patterns from emails that match existing blacklist rules"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Perform advanced blacklist filtering with pattern learning.
        
        Returns:
            Dictionary with filtering results and learned patterns
        """
        start_time = time.time()
        
        # First pass: Apply existing blacklist
        blacklist_tool = BlacklistFilterTool(
            emails=self.emails,
            use_default_patterns=True
        )
        
        initial_results = blacklist_tool.run()
        
        # Analyze patterns if enabled
        suggested_patterns = []
        if self.analyze_patterns:
            suggested_patterns = self._analyze_email_patterns(
                initial_results['allowed_emails'],
                initial_results['blacklisted_emails']
            )
        
        # Learn from existing blacklist matches if enabled
        learned_patterns = []
        if self.learn_from_existing:
            learned_patterns = self._learn_from_blacklisted_emails(
                initial_results['blacklisted_emails']
            )
        
        # Apply suggested patterns to refine results
        refined_results = initial_results
        if suggested_patterns:
            refined_results = self._apply_suggested_patterns(
                initial_results['allowed_emails'],
                suggested_patterns
            )
        
        processing_time = time.time() - start_time
        
        return {
            'summary': {
                'total_emails': len(self.emails),
                'initial_blacklisted': initial_results['summary']['blacklisted'],
                'additional_blacklisted': len(refined_results.get('additional_blacklisted', [])),
                'final_allowed': len(refined_results.get('final_allowed', initial_results['allowed_emails'])),
                'suggested_patterns_found': len(suggested_patterns),
                'learned_patterns_found': len(learned_patterns),
                'processing_time_seconds': processing_time
            },
            'initial_filtering': initial_results,
            'pattern_analysis': {
                'suggested_patterns': suggested_patterns,
                'learned_patterns': learned_patterns,
                'pattern_confidence_scores': self._score_pattern_confidence(suggested_patterns)
            },
            'refined_results': refined_results,
            'final_emails': {
                'allowed': refined_results.get('final_allowed', initial_results['allowed_emails']),
                'blacklisted': initial_results['blacklisted_emails'] + refined_results.get('additional_blacklisted', [])
            },
            'recommendations': {
                'high_confidence_patterns': [
                    p for p in suggested_patterns 
                    if p.get('confidence', 0) >= self.confidence_threshold
                ],
                'review_patterns': [
                    p for p in suggested_patterns 
                    if p.get('confidence', 0) < self.confidence_threshold
                ]
            },
            'configuration': {
                'confidence_threshold': self.confidence_threshold,
                'min_pattern_frequency': self.min_pattern_frequency,
                'analyze_patterns': self.analyze_patterns,
                'learn_from_existing': self.learn_from_existing
            }
        }
    
    def _analyze_email_patterns(self, allowed_emails: List[str], 
                               blacklisted_emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze email patterns to suggest new blacklist rules"""
        
        # Extract patterns from allowed emails that might be suspicious
        suspicious_patterns = []
        
        # Analyze local parts
        local_parts = [email.split('@')[0].lower() for email in allowed_emails if '@' in email]
        local_part_freq = Counter(local_parts)
        
        # Look for suspicious local part patterns
        for local_part, freq in local_part_freq.items():
            if freq >= self.min_pattern_frequency:
                # Check if it looks suspicious
                confidence = self._calculate_suspicion_score(local_part)
                
                if confidence >= 0.5:  # Potential suspicious pattern
                    suspicious_patterns.append({
                        'pattern': f'^{re.escape(local_part)}@',
                        'type': 'regex',
                        'reason': f'Suspicious local part pattern: {local_part}',
                        'frequency': freq,
                        'confidence': confidence,
                        'sample_emails': [
                            email for email in allowed_emails 
                            if email.lower().startswith(local_part + '@')
                        ][:5]
                    })
        
        # Analyze domains
        domains = [email.split('@')[1].lower() for email in allowed_emails if '@' in email]
        domain_freq = Counter(domains)
        
        # Look for suspicious domain patterns
        for domain, freq in domain_freq.items():
            if freq >= self.min_pattern_frequency:
                confidence = self._calculate_domain_suspicion_score(domain)
                
                if confidence >= 0.6:  # Potential suspicious domain
                    suspicious_patterns.append({
                        'pattern': domain,
                        'type': 'domain',
                        'reason': f'Suspicious domain pattern: {domain}',
                        'frequency': freq,
                        'confidence': confidence,
                        'sample_emails': [
                            email for email in allowed_emails 
                            if email.lower().endswith('@' + domain)
                        ][:5]
                    })
        
        # Sort by confidence and frequency
        suspicious_patterns.sort(key=lambda x: (x['confidence'], x['frequency']), reverse=True)
        
        return suspicious_patterns[:20]  # Return top 20 suggestions
    
    def _calculate_suspicion_score(self, local_part: str) -> float:
        """Calculate suspicion score for a local part"""
        score = 0.0
        
        # Length-based scoring
        if len(local_part) <= 2:
            score += 0.3  # Very short
        elif len(local_part) >= 25:
            score += 0.2  # Very long
        
        # Pattern-based scoring
        if local_part.isdigit():
            score += 0.4  # All numeric
        
        if re.match(r'^[a-z]{1,3}\d+$', local_part):
            score += 0.3  # Short letters + numbers
        
        # Common suspicious keywords
        suspicious_keywords = [
            'spam', 'junk', 'trash', 'delete', 'remove',
            'auto', 'generated', 'random', 'temp'
        ]
        
        for keyword in suspicious_keywords:
            if keyword in local_part:
                score += 0.2
        
        # Repetitive patterns
        if len(set(local_part)) < len(local_part) * 0.5:
            score += 0.2  # Low character diversity
        
        return min(1.0, score)
    
    def _calculate_domain_suspicion_score(self, domain: str) -> float:
        """Calculate suspicion score for a domain"""
        score = 0.0
        
        # TLD-based scoring
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.click', '.download']
        for tld in suspicious_tlds:
            if domain.endswith(tld):
                score += 0.4
        
        # Domain structure scoring
        parts = domain.split('.')
        if len(parts) > 4:
            score += 0.2  # Too many subdomains
        
        # Numeric domains
        if any(part.isdigit() for part in parts[:-1]):
            score += 0.3
        
        # Random-looking domains
        main_part = parts[0] if parts else domain
        if len(main_part) > 15 and len(set(main_part)) < len(main_part) * 0.6:
            score += 0.2
        
        # Suspicious keywords in domain
        suspicious_keywords = [
            'temp', 'temporary', 'fake', 'test', 'spam',
            'disposable', 'throwaway', 'guerrilla'
        ]
        
        for keyword in suspicious_keywords:
            if keyword in domain.lower():
                score += 0.3
        
        return min(1.0, score)
    
    def _learn_from_blacklisted_emails(self, blacklisted_emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Learn new patterns from existing blacklisted emails"""
        
        learned_patterns = []
        
        # Analyze blacklisted email patterns
        blacklisted_emails_only = [item['email'] for item in blacklisted_emails]
        
        # Extract common prefixes and suffixes
        prefixes = []
        suffixes = []
        
        for email in blacklisted_emails_only:
            if '@' in email:
                local_part = email.split('@')[0].lower()
                
                # Look for common prefixes (first 3-5 characters)
                if len(local_part) >= 3:
                    prefixes.append(local_part[:3])
                    prefixes.append(local_part[:4])
                    if len(local_part) >= 5:
                        prefixes.append(local_part[:5])
                
                # Look for common suffixes (last 3-5 characters)
                if len(local_part) >= 3:
                    suffixes.append(local_part[-3:])
                    suffixes.append(local_part[-4:])
                    if len(local_part) >= 5:
                        suffixes.append(local_part[-5:])
        
        # Find frequent patterns
        prefix_freq = Counter(prefixes)
        suffix_freq = Counter(suffixes)
        
        # Generate learned patterns
        for prefix, freq in prefix_freq.items():
            if freq >= self.min_pattern_frequency:
                learned_patterns.append({
                    'pattern': f'^{re.escape(prefix)}.*@',
                    'type': 'regex',
                    'reason': f'Learned prefix pattern: {prefix}',
                    'frequency': freq,
                    'confidence': 0.7,
                    'source': 'learned_from_blacklist'
                })
        
        for suffix, freq in suffix_freq.items():
            if freq >= self.min_pattern_frequency:
                learned_patterns.append({
                    'pattern': f'^.*{re.escape(suffix)}@',
                    'type': 'regex',
                    'reason': f'Learned suffix pattern: {suffix}',
                    'frequency': freq,
                    'confidence': 0.7,
                    'source': 'learned_from_blacklist'
                })
        
        return learned_patterns[:10]  # Return top 10 learned patterns
    
    def _apply_suggested_patterns(self, allowed_emails: List[str], 
                                 suggested_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply suggested patterns to refine filtering results"""
        
        # Only apply high-confidence patterns
        high_confidence_patterns = [
            p for p in suggested_patterns 
            if p.get('confidence', 0) >= self.confidence_threshold
        ]
        
        if not high_confidence_patterns:
            return {'final_allowed': allowed_emails, 'additional_blacklisted': []}
        
        # Apply patterns
        final_allowed = []
        additional_blacklisted = []
        
        for email in allowed_emails:
            is_blacklisted = False
            matched_pattern = None
            
            for pattern_info in high_confidence_patterns:
                pattern = pattern_info['pattern']
                pattern_type = pattern_info['type']
                
                if pattern_type == 'regex':
                    try:
                        if re.search(pattern, email.lower()):
                            is_blacklisted = True
                            matched_pattern = pattern
                            break
                    except re.error:
                        continue
                elif pattern_type == 'domain' and '@' in email:
                    domain = email.split('@')[1].lower()
                    if domain == pattern.lower():
                        is_blacklisted = True
                        matched_pattern = pattern
                        break
            
            if is_blacklisted:
                additional_blacklisted.append({
                    'email': email,
                    'matched_pattern': matched_pattern,
                    'reason': f'Suggested pattern match: {matched_pattern}',
                    'confidence': pattern_info.get('confidence', 0.8)
                })
            else:
                final_allowed.append(email)
        
        return {
            'final_allowed': final_allowed,
            'additional_blacklisted': additional_blacklisted
        }
    
    def _score_pattern_confidence(self, patterns: List[Dict[str, Any]]) -> Dict[str, float]:
        """Score the confidence of suggested patterns"""
        
        scores = {}
        
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            frequency = pattern_info.get('frequency', 1)
            base_confidence = pattern_info.get('confidence', 0.5)
            
            # Adjust confidence based on frequency
            frequency_bonus = min(0.2, frequency * 0.02)
            final_confidence = min(1.0, base_confidence + frequency_bonus)
            
            scores[pattern] = final_confidence
        
        return scores