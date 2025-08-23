#!/usr/bin/env python3
"""
Email Scorer - Score Email Quality and Business Relevance
Advanced scoring system for email quality assessment
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class EmailScore:
    """Email scoring result"""
    email: str
    quality_score: float
    business_score: float
    personal_score: float
    confidence: float
    category: str
    factors: Dict[str, float]
    is_actionable: bool


class EmailScorer:
    """
    Advanced email scoring system that evaluates:
    1. Email quality (format, domain, etc.)
    2. Business relevance (role-based vs personal)
    3. Actionability for outreach
    """
    
    def __init__(self):
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Define scoring weights
        self.weights = {
            'format_quality': 0.2,
            'domain_quality': 0.25,
            'role_relevance': 0.3,
            'personal_indicators': 0.15,
            'context_relevance': 0.1
        }
        
        # Business role patterns (high value for outreach)
        self.business_roles = {
            # Executive roles (highest priority)
            'ceo': 1.0, 'president': 1.0, 'founder': 1.0, 'owner': 1.0,
            'director': 0.9, 'manager': 0.8, 'head': 0.8, 'chief': 0.9,
            
            # Decision makers
            'admin': 0.7, 'administrator': 0.7, 'coordinator': 0.6,
            'supervisor': 0.7, 'leader': 0.6, 'executive': 0.8,
            
            # Department contacts
            'sales': 0.9, 'marketing': 0.8, 'business': 0.8, 'operations': 0.7,
            'development': 0.6, 'hr': 0.5, 'human': 0.5, 'resources': 0.5,
            
            # General business contacts
            'contact': 0.8, 'info': 0.7, 'inquiry': 0.7, 'support': 0.6,
            'office': 0.6, 'reception': 0.5, 'desk': 0.4
        }
        
        # Personal email indicators (lower business value)
        self.personal_indicators = [
            'personal', 'private', 'home', 'gmail.com', 'yahoo.com', 
            'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com',
            'me.com', 'mac.com'
        ]
        
        # Generic/automated email patterns (low value)
        self.generic_patterns = [
            re.compile(r'^(no-?reply|noreply)', re.IGNORECASE),
            re.compile(r'^(do-?not-?reply|donotreply)', re.IGNORECASE),
            re.compile(r'^(auto-?reply|autoreply)', re.IGNORECASE),
            re.compile(r'^(bounce|bounces)', re.IGNORECASE),
            re.compile(r'^(postmaster|webmaster)', re.IGNORECASE),
            re.compile(r'^(mailer-daemon|daemon)', re.IGNORECASE),
            re.compile(r'^(abuse|spam)', re.IGNORECASE),
        ]
        
        # Professional domain indicators
        self.professional_domains = [
            # Corporate TLDs
            '.com', '.org', '.net', '.co', '.io', '.biz',
            # Geographic business domains
            '.com.au', '.co.uk', '.co.za', '.com.sg'
        ]
        
        # Free email providers (personal use)
        self.free_providers = {
            'gmail.com': 0.3, 'yahoo.com': 0.2, 'hotmail.com': 0.1,
            'outlook.com': 0.2, 'aol.com': 0.1, 'icloud.com': 0.2,
            'me.com': 0.1, 'mac.com': 0.1, 'live.com': 0.1,
            'msn.com': 0.1, 'ymail.com': 0.1, 'rocketmail.com': 0.1
        }
        
        # Business email patterns
        self.business_patterns = [
            # firstname.lastname pattern
            re.compile(r'^[a-z]+\.[a-z]+@', re.IGNORECASE),
            # first initial + lastname
            re.compile(r'^[a-z]\.[a-z]+@', re.IGNORECASE),
            # firstname + initial
            re.compile(r'^[a-z]+\.[a-z]@', re.IGNORECASE),
            # role-based
            re.compile(r'^(info|contact|sales|admin|support|office)@', re.IGNORECASE),
        ]
    
    def score_email_quality(self, email: str) -> float:
        """
        Score email quality based on format, domain, and structure
        
        Args:
            email: Email address to score
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        if not email or '@' not in email:
            return 0.0
        
        try:
            local_part, domain = email.lower().split('@', 1)
            score = 0.5  # Base score
            
            # Format quality checks
            if self._is_valid_email_format(email):
                score += 0.2
            
            # Local part quality
            local_score = self._score_local_part(local_part)
            score += local_score * 0.3
            
            # Domain quality
            domain_score = self._score_domain(domain)
            score += domain_score * 0.3
            
            # Penalty for generic/automated emails
            if self._is_generic_email(email):
                score *= 0.1
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"Error scoring email quality for {email}: {e}")
            return 0.0
    
    def score_business_relevance(self, email: str, context: str = "") -> float:
        """
        Score business relevance for outreach purposes
        
        Args:
            email: Email address to score
            context: Context where email was found
            
        Returns:
            Business relevance score (0.0 to 1.0)
        """
        if not email or '@' not in email:
            return 0.0
        
        try:
            local_part, domain = email.lower().split('@', 1)
            score = 0.5  # Base score
            
            # Role-based scoring
            role_score = self._score_business_role(local_part)
            score += role_score * 0.4
            
            # Domain business relevance
            domain_business_score = self._score_domain_business_relevance(domain)
            score += domain_business_score * 0.3
            
            # Context relevance
            if context:
                context_score = self._score_context_relevance(context)
                score += context_score * 0.2
            
            # Personal email penalty
            if self._is_personal_email(email):
                score *= 0.6
            
            # Professional pattern bonus
            if self._matches_business_pattern(email):
                score += 0.1
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"Error scoring business relevance for {email}: {e}")
            return 0.0
    
    def score_personal_likelihood(self, email: str) -> float:
        """
        Score likelihood that email is personal (vs business)
        
        Args:
            email: Email address to score
            
        Returns:
            Personal likelihood score (0.0 to 1.0)
        """
        if not email or '@' not in email:
            return 0.0
        
        try:
            local_part, domain = email.lower().split('@', 1)
            score = 0.0
            
            # Free provider check
            if domain in self.free_providers:
                score += 0.7
            
            # Personal indicators in local part
            personal_keywords = ['personal', 'private', 'home', 'me', 'my']
            if any(keyword in local_part for keyword in personal_keywords):
                score += 0.2
            
            # Numeric patterns (often personal)
            if re.search(r'\d+', local_part):
                score += 0.1
            
            # Long random-looking strings
            if len(local_part) > 12 and not '.' in local_part:
                score += 0.1
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error scoring personal likelihood for {email}: {e}")
            return 0.0
    
    def score_comprehensive(self, email: str, context: str = "") -> EmailScore:
        """
        Comprehensive email scoring with detailed breakdown
        
        Args:
            email: Email address to score
            context: Context where email was found
            
        Returns:
            EmailScore object with detailed scoring
        """
        quality_score = self.score_email_quality(email)
        business_score = self.score_business_relevance(email, context)
        personal_score = self.score_personal_likelihood(email)
        
        # Calculate confidence based on available data
        confidence = 0.7  # Base confidence
        if context:
            confidence += 0.2
        if self._has_clear_business_indicators(email):
            confidence += 0.1
        
        # Determine category
        category = self._categorize_email(email, business_score, personal_score)
        
        # Calculate factor breakdown
        factors = self._calculate_factor_breakdown(email, context)
        
        # Determine actionability
        is_actionable = self._is_actionable_email(quality_score, business_score, personal_score)
        
        return EmailScore(
            email=email,
            quality_score=quality_score,
            business_score=business_score,
            personal_score=personal_score,
            confidence=confidence,
            category=category,
            factors=factors,
            is_actionable=is_actionable
        )
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Check if email has valid format"""
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email))
    
    def _score_local_part(self, local_part: str) -> float:
        """Score the local part (before @) of email"""
        score = 0.5
        
        # Length scoring
        if 3 <= len(local_part) <= 20:
            score += 0.2
        elif len(local_part) > 20:
            score -= 0.1
        
        # Pattern scoring
        if '.' in local_part:
            # firstname.lastname pattern
            parts = local_part.split('.')
            if len(parts) == 2 and all(part.isalpha() and len(part) > 1 for part in parts):
                score += 0.3
        
        # Role-based local parts
        for role, role_score in self.business_roles.items():
            if role in local_part:
                score += role_score * 0.2
                break
        
        return min(1.0, score)
    
    def _score_domain(self, domain: str) -> float:
        """Score the domain part of email"""
        score = 0.5
        
        # Free provider penalty
        if domain in self.free_providers:
            score = self.free_providers[domain]
        else:
            # Professional domain bonus
            if any(domain.endswith(tld) for tld in self.professional_domains):
                score += 0.3
            
            # Custom domain bonus (not free provider)
            score += 0.2
        
        # Subdomain penalty (often automated)
        if domain.count('.') > 1:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_business_role(self, local_part: str) -> float:
        """Score based on business role indicators"""
        max_score = 0.0
        
        for role, role_score in self.business_roles.items():
            if role in local_part:
                max_score = max(max_score, role_score)
        
        return max_score
    
    def _score_domain_business_relevance(self, domain: str) -> float:
        """Score domain for business relevance"""
        score = 0.5
        
        # Free providers are less business relevant
        if domain in self.free_providers:
            score = 0.2
        else:
            # Business domain indicators
            business_keywords = ['corp', 'company', 'firm', 'group', 'inc', 'llc', 'ltd']
            if any(keyword in domain for keyword in business_keywords):
                score += 0.3
            
            # Professional TLD bonus
            if any(domain.endswith(tld) for tld in self.professional_domains):
                score += 0.2
        
        return min(1.0, score)
    
    def _score_context_relevance(self, context: str) -> float:
        """Score based on context where email was found"""
        score = 0.0
        context_lower = context.lower()
        
        # Business context indicators
        business_contexts = [
            'contact', 'about', 'team', 'staff', 'management', 'office',
            'business', 'company', 'organization', 'executive', 'director'
        ]
        
        for context_word in business_contexts:
            if context_word in context_lower:
                score += 0.2
        
        return min(1.0, score)
    
    def _is_generic_email(self, email: str) -> bool:
        """Check if email is generic/automated"""
        for pattern in self.generic_patterns:
            if pattern.search(email):
                return True
        return False
    
    def _is_personal_email(self, email: str) -> bool:
        """Check if email appears to be personal"""
        email_lower = email.lower()
        return any(indicator in email_lower for indicator in self.personal_indicators)
    
    def _matches_business_pattern(self, email: str) -> bool:
        """Check if email matches business patterns"""
        for pattern in self.business_patterns:
            if pattern.search(email):
                return True
        return False
    
    def _has_clear_business_indicators(self, email: str) -> bool:
        """Check if email has clear business indicators"""
        local_part = email.split('@')[0].lower()
        return any(role in local_part for role in self.business_roles.keys())
    
    def _categorize_email(self, email: str, business_score: float, personal_score: float) -> str:
        """Categorize email based on scores"""
        if business_score > 0.7:
            return "high_value_business"
        elif business_score > 0.5:
            return "business"
        elif personal_score > 0.6:
            return "personal"
        elif self._is_generic_email(email):
            return "generic"
        else:
            return "unknown"
    
    def _calculate_factor_breakdown(self, email: str, context: str) -> Dict[str, float]:
        """Calculate detailed factor breakdown"""
        if '@' not in email:
            return {}
        
        local_part, domain = email.lower().split('@', 1)
        
        return {
            'format_quality': 1.0 if self._is_valid_email_format(email) else 0.0,
            'domain_quality': self._score_domain(domain),
            'role_relevance': self._score_business_role(local_part),
            'personal_indicators': self.score_personal_likelihood(email),
            'context_relevance': self._score_context_relevance(context) if context else 0.0,
            'is_generic': 1.0 if self._is_generic_email(email) else 0.0,
            'is_free_provider': 1.0 if domain in self.free_providers else 0.0
        }
    
    def _is_actionable_email(self, quality_score: float, business_score: float, personal_score: float) -> bool:
        """Determine if email is actionable for outreach"""
        # Must have good quality
        if quality_score < 0.6:
            return False
        
        # Must have business relevance
        if business_score < 0.4:
            return False
        
        # Should not be overly personal
        if personal_score > 0.8:
            return False
        
        return True
    
    def score_email_list(self, emails: List[str], contexts: List[str] = None) -> List[EmailScore]:
        """
        Score a list of emails
        
        Args:
            emails: List of email addresses
            contexts: Optional list of contexts (same length as emails)
            
        Returns:
            List of EmailScore objects
        """
        if contexts is None:
            contexts = [""] * len(emails)
        
        scores = []
        for i, email in enumerate(emails):
            context = contexts[i] if i < len(contexts) else ""
            score = self.score_comprehensive(email, context)
            scores.append(score)
        
        # Sort by business score (highest first)
        return sorted(scores, key=lambda x: x.business_score, reverse=True)
    
    def filter_actionable_emails(self, email_scores: List[EmailScore], 
                                min_business_score: float = 0.5) -> List[EmailScore]:
        """
        Filter emails to only actionable ones
        
        Args:
            email_scores: List of EmailScore objects
            min_business_score: Minimum business score threshold
            
        Returns:
            Filtered list of actionable emails
        """
        return [
            score for score in email_scores 
            if score.is_actionable and score.business_score >= min_business_score
        ]


def test_email_scorer():
    """Test the email scorer with various email types"""
    print("Testing Email Scorer")
    print("=" * 40)
    
    scorer = EmailScorer()
    
    # Test emails with different characteristics
    test_emails = [
        # High-value business emails
        ("ceo@company.com", "Found on CEO bio page"),
        ("sales@business.org", "Contact page"),
        ("john.doe@startup.io", "Team page"),
        
        # Medium-value business emails
        ("info@restaurant.com", "Contact information"),
        ("contact@service.net", "Contact us page"),
        ("admin@office.co", "About us"),
        
        # Personal emails
        ("john.smith@gmail.com", "Personal contact"),
        ("mary123@yahoo.com", ""),
        ("personal.email@hotmail.com", ""),
        
        # Generic/automated emails
        ("noreply@system.com", ""),
        ("donotreply@automated.net", ""),
        ("support@helpdesk.org", "Support page"),
        
        # Invalid/low quality
        ("invalid@", ""),
        ("test@test", ""),
        ("", "")
    ]
    
    results = []
    
    print("\nScoring individual emails:")
    print("-" * 30)
    
    for email, context in test_emails:
        if not email:
            continue
            
        score = scorer.score_comprehensive(email, context)
        results.append(score)
        
        print(f"Email: {email}")
        print(f"  Quality: {score.quality_score:.2f}")
        print(f"  Business: {score.business_score:.2f}")
        print(f"  Personal: {score.personal_score:.2f}")
        print(f"  Category: {score.category}")
        print(f"  Actionable: {score.is_actionable}")
        print()
    
    # Test list scoring and filtering
    email_list = [email for email, _ in test_emails if email]
    context_list = [context for email, context in test_emails if email]
    
    list_scores = scorer.score_email_list(email_list, context_list)
    actionable = scorer.filter_actionable_emails(list_scores)
    
    print(f"Total emails tested: {len(list_scores)}")
    print(f"Actionable emails: {len(actionable)}")
    print(f"Actionable rate: {len(actionable)/len(list_scores)*100:.1f}%")
    
    print("\nTop actionable emails:")
    for score in actionable[:5]:
        print(f"  {score.email} (business: {score.business_score:.2f}, quality: {score.quality_score:.2f})")
    
    return len(actionable) > 0


if __name__ == "__main__":
    test_email_scorer()