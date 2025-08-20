"""
Advanced contact enrichment, validation, and confidence scoring module.
Provides sophisticated contact verification and alternative contact discovery.
"""

import re
import logging
import requests
import smtplib
from typing import List, Dict, Any, Optional, Tuple
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .base import PodcastData
from .config import config
from .contact_extraction import ContactExtractor, ContactValidator

logger = logging.getLogger(__name__)


class AdvancedContactEnricher:
    """Advanced contact enrichment with validation and scoring."""
    
    def __init__(self):
        """Initialize advanced contact enricher."""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
        
        # Initialize base extractors
        self.contact_extractor = ContactExtractor()
        self.contact_validator = ContactValidator()
        
        # Alternative contact patterns
        self.team_keywords = [
            'team', 'staff', 'crew', 'producer', 'manager', 'assistant',
            'booking', 'business', 'media', 'press', 'pr', 'publicity'
        ]
        
        # Email deliverability services (would need API keys for full implementation)
        self.email_verification_services = {
            'hunter_io': 'https://api.hunter.io/v2/email-verifier',
            'zerobounce': 'https://api.zerobounce.net/v2/validate',
            'kickbox': 'https://api.kickbox.com/v2/verify'
        }
        
        # Contact method preferences scoring
        self.contact_preferences = {
            'direct_email': 10,
            'booking_email': 9,
            'business_email': 8,
            'general_email': 7,
            'contact_form': 6,
            'social_dm': 5,
            'website_only': 3,
            'no_contact': 1
        }
    
    def enrich_contact_comprehensive(self, podcast: PodcastData) -> Dict[str, Any]:
        """
        Perform comprehensive contact enrichment with advanced validation.
        
        Args:
            podcast: PodcastData to enrich
            
        Returns:
            Dict with comprehensive contact analysis
        """
        enrichment_result = {
            'primary_contacts': [],
            'alternative_contacts': [],
            'team_contacts': [],
            'contact_validation': {},
            'response_likelihood': 0.0,
            'best_contact_method': 'unknown',
            'contact_strategy': '',
            'verification_status': {},
            'confidence_factors': []
        }
        
        try:
            self.logger.info(f"Starting comprehensive contact enrichment for: {podcast.podcast_name}")
            
            # Gather all existing contact information
            all_contacts = self._gather_existing_contacts(podcast)
            
            # Discover additional contacts
            additional_contacts = self._discover_additional_contacts(podcast)
            all_contacts.update(additional_contacts)
            
            # Categorize contacts by type and quality
            contact_categories = self._categorize_contacts(all_contacts)
            enrichment_result.update(contact_categories)
            
            # Validate email deliverability (basic checks)
            validation_results = self._validate_email_deliverability(contact_categories['primary_contacts'])
            enrichment_result['contact_validation'] = validation_results
            
            # Calculate response likelihood
            enrichment_result['response_likelihood'] = self._calculate_response_likelihood(podcast, contact_categories)
            
            # Determine best contact method
            enrichment_result['best_contact_method'] = self._determine_best_contact_method(contact_categories)
            
            # Generate contact strategy
            enrichment_result['contact_strategy'] = self._generate_contact_strategy(podcast, enrichment_result)
            
            # Identify confidence factors
            enrichment_result['confidence_factors'] = self._identify_confidence_factors(podcast, enrichment_result)
            
            self.logger.info(f"Contact enrichment completed. Response likelihood: {enrichment_result['response_likelihood']:.1f}%")
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive contact enrichment: {e}")
        
        return enrichment_result
    
    def _gather_existing_contacts(self, podcast: PodcastData) -> Dict[str, List[str]]:
        """Gather all existing contact information from podcast data."""
        contacts = {
            'emails': [],
            'websites': [],
            'social_profiles': [],
            'contact_forms': []
        }
        
        # Direct contact fields
        if podcast.host_email:
            contacts['emails'].append(podcast.host_email)
        if podcast.booking_email:
            contacts['emails'].append(podcast.booking_email)
        if podcast.podcast_website:
            contacts['websites'].append(podcast.podcast_website)
        if podcast.contact_page_url:
            contacts['contact_forms'].append(podcast.contact_page_url)
        
        # Social media profiles
        if podcast.social_links:
            for platform, url in podcast.social_links.items():
                contacts['social_profiles'].append(f"{platform}:{url}")
        
        # Extract from raw data if available
        if podcast.raw_data:
            # From social media enrichment
            social_profiles = podcast.raw_data.get('social_profiles', {})
            for platform, profile_data in social_profiles.items():
                contact_info = profile_data.get('contact_info', {})
                contacts['emails'].extend(contact_info.get('emails', []))
                contacts['websites'].extend(contact_info.get('websites', []))
        
        # Remove duplicates
        for key in contacts:
            contacts[key] = list(set(contacts[key]))
        
        return contacts
    
    def _discover_additional_contacts(self, podcast: PodcastData) -> Dict[str, List[str]]:
        """Discover additional contact methods not previously found."""
        additional_contacts = {
            'emails': [],
            'websites': [],
            'social_profiles': [],
            'contact_forms': []
        }
        
        # Search for team/alternative contacts
        if podcast.podcast_website:
            team_contacts = self._find_team_contacts(podcast.podcast_website)
            additional_contacts['emails'].extend(team_contacts.get('emails', []))
            additional_contacts['contact_forms'].extend(team_contacts.get('forms', []))
        
        # Search social media for additional contact methods
        if podcast.social_links:
            social_contacts = self._extract_social_contact_methods(podcast.social_links)
            additional_contacts.update(social_contacts)
        
        # Pattern-based email discovery
        if podcast.podcast_website:
            pattern_emails = self._discover_pattern_emails(podcast.podcast_website, podcast.podcast_name)
            additional_contacts['emails'].extend(pattern_emails)
        
        return additional_contacts
    
    def _find_team_contacts(self, website_url: str) -> Dict[str, List[str]]:
        """Find team/staff contact information on website."""
        team_contacts = {'emails': [], 'forms': []}
        
        try:
            # Check common team pages
            team_pages = ['/team', '/staff', '/about', '/contact', '/crew', '/people']
            
            for page_path in team_pages:
                try:
                    team_url = website_url.rstrip('/') + page_path
                    response = self.session.get(team_url, timeout=10)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Extract emails from team page
                        team_emails = self.contact_extractor.extract_emails(content, team_url)
                        team_contacts['emails'].extend([email['email'] for email in team_emails])
                        
                        # Look for team-specific contact forms
                        if self._has_contact_form(content):
                            team_contacts['forms'].append(team_url)
                
                except Exception as e:
                    self.logger.debug(f"Error checking team page {team_url}: {e}")
                    continue
        
        except Exception as e:
            self.logger.warning(f"Error finding team contacts for {website_url}: {e}")
        
        return team_contacts
    
    def _extract_social_contact_methods(self, social_links: Dict[str, str]) -> Dict[str, List[str]]:
        """Extract contact methods from social media profiles."""
        social_contacts = {
            'emails': [],
            'websites': [],
            'social_profiles': [],
            'contact_forms': []
        }
        
        # This would involve scraping social profiles for contact info
        # For now, we'll add the social profiles as contact methods
        for platform, url in social_links.items():
            social_contacts['social_profiles'].append(f"{platform}:{url}")
        
        return social_contacts
    
    def _discover_pattern_emails(self, website_url: str, podcast_name: str) -> List[str]:
        """Discover emails using common patterns."""
        pattern_emails = []
        
        try:
            from urllib.parse import urlparse
            domain = urlparse(website_url).netloc.replace('www.', '')
            
            # Common email patterns
            clean_name = re.sub(r'[^\w\s]', '', podcast_name.lower())
            name_variations = [
                clean_name.replace(' ', ''),
                clean_name.replace(' ', '.'),
                clean_name.replace(' ', '_'),
                ''.join(word[0] for word in clean_name.split())  # Initials
            ]
            
            email_prefixes = ['info', 'hello', 'contact', 'host', 'booking', 'business', 'team']
            
            # Generate potential emails
            potential_emails = []
            for prefix in email_prefixes:
                potential_emails.append(f"{prefix}@{domain}")
            
            for variation in name_variations[:2]:  # Limit to avoid spam
                potential_emails.append(f"{variation}@{domain}")
            
            # Quick validation (just format check for now)
            for email in potential_emails:
                if self._is_valid_email_format(email):
                    pattern_emails.append(email)
        
        except Exception as e:
            self.logger.debug(f"Error discovering pattern emails: {e}")
        
        return pattern_emails[:5]  # Limit to prevent abuse
    
    def _categorize_contacts(self, all_contacts: Dict[str, List[str]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize contacts by type and quality."""
        categories = {
            'primary_contacts': [],
            'alternative_contacts': [],
            'team_contacts': []
        }
        
        # Process emails
        for email in all_contacts.get('emails', []):
            contact_info = {
                'type': 'email',
                'value': email,
                'quality': self._assess_email_quality(email),
                'category': self._classify_email_category(email)
            }
            
            # Categorize based on quality and type
            if contact_info['quality'] >= 8 or 'host' in email or 'booking' in email:
                categories['primary_contacts'].append(contact_info)
            elif contact_info['quality'] >= 6:
                categories['alternative_contacts'].append(contact_info)
            else:
                categories['team_contacts'].append(contact_info)
        
        # Process websites
        for website in all_contacts.get('websites', []):
            contact_info = {
                'type': 'website',
                'value': website,
                'quality': 7,  # Medium quality
                'category': 'general'
            }
            categories['alternative_contacts'].append(contact_info)
        
        # Process social profiles
        for social in all_contacts.get('social_profiles', []):
            platform, url = social.split(':', 1) if ':' in social else ('unknown', social)
            quality = {'twitter': 8, 'linkedin': 9, 'instagram': 7, 'youtube': 6}.get(platform, 5)
            
            contact_info = {
                'type': 'social',
                'value': url,
                'platform': platform,
                'quality': quality,
                'category': 'social_media'
            }
            categories['alternative_contacts'].append(contact_info)
        
        # Sort each category by quality
        for category in categories:
            categories[category].sort(key=lambda x: x['quality'], reverse=True)
        
        return categories
    
    def _assess_email_quality(self, email: str) -> int:
        """Assess email quality score (1-10)."""
        score = 5  # Base score
        
        email_lower = email.lower()
        
        # High-quality indicators
        if any(indicator in email_lower for indicator in ['host', 'booking', 'business']):
            score += 3
        elif any(indicator in email_lower for indicator in ['info', 'hello', 'contact']):
            score += 2
        elif any(indicator in email_lower for indicator in ['team', 'crew', 'producer']):
            score += 1
        
        # Reduce score for generic emails
        if any(generic in email_lower for generic in ['noreply', 'no-reply', 'donotreply']):
            score -= 5
        
        # Professional domain bonus
        domain = email.split('@')[1] if '@' in email else ''
        if not domain.endswith(('.gmail.com', '.yahoo.com', '.hotmail.com')):
            score += 1  # Custom domain bonus
        
        return max(1, min(10, score))
    
    def _classify_email_category(self, email: str) -> str:
        """Classify email into category."""
        email_lower = email.lower()
        
        if 'host' in email_lower:
            return 'host'
        elif 'booking' in email_lower:
            return 'booking'
        elif 'business' in email_lower:
            return 'business'
        elif any(word in email_lower for word in ['info', 'contact', 'hello']):
            return 'general'
        elif any(word in email_lower for word in ['team', 'crew', 'producer']):
            return 'team'
        else:
            return 'unknown'
    
    def _validate_email_deliverability(self, primary_contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate email deliverability (basic checks only)."""
        validation_results = {
            'total_emails': 0,
            'valid_format': 0,
            'deliverable': 0,
            'risky': 0,
            'details': {}
        }
        
        emails = [contact['value'] for contact in primary_contacts if contact['type'] == 'email']
        validation_results['total_emails'] = len(emails)
        
        for email in emails:
            # Basic format validation only (advanced services would require API keys)
            is_valid, validation_info = self.contact_extractor._validate_email(email)
            
            validation_results['details'][email] = validation_info
            
            if is_valid:
                validation_results['valid_format'] += 1
                
                # Simple deliverability check (domain has MX record)
                if validation_info.get('domain_valid'):
                    validation_results['deliverable'] += 1
                
                # Flag risky emails
                if validation_info.get('disposable') or 'temp' in email.lower():
                    validation_results['risky'] += 1
        
        return validation_results
    
    def _calculate_response_likelihood(self, podcast: PodcastData, contact_categories: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate likelihood of getting a response (0-100%)."""
        likelihood = 0.0
        
        # Base likelihood from contact quality
        primary_contacts = contact_categories.get('primary_contacts', [])
        if primary_contacts:
            best_contact = primary_contacts[0]
            likelihood = best_contact['quality'] * 10  # Convert to percentage
        
        # Podcast authority bonus
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            intelligence = podcast.raw_data.get('intelligence', {})
            authority_score = intelligence.get('authority_score', 0)
            likelihood += authority_score * 2  # Up to 20% bonus
        
        # Social media presence bonus
        if podcast.social_links and len(podcast.social_links) >= 2:
            likelihood += 10
        
        # Website presence bonus
        if podcast.podcast_website:
            likelihood += 5
        
        # Multiple contact methods bonus
        total_contacts = sum(len(contacts) for contacts in contact_categories.values())
        if total_contacts >= 3:
            likelihood += 5
        
        # Professional setup bonus
        if podcast.podcast_website and podcast.host_email:
            likelihood += 10
        
        return min(100.0, max(0.0, likelihood))
    
    def _determine_best_contact_method(self, contact_categories: Dict[str, List[Dict[str, Any]]]) -> str:
        """Determine the best contact method."""
        # Check primary contacts first
        primary = contact_categories.get('primary_contacts', [])
        if primary:
            best_primary = primary[0]
            if best_primary['type'] == 'email':
                return f"Direct email ({best_primary['category']})"
        
        # Check alternative contacts
        alternative = contact_categories.get('alternative_contacts', [])
        if alternative:
            best_alt = alternative[0]
            if best_alt['type'] == 'social':
                return f"Social media ({best_alt.get('platform', 'unknown')})"
            elif best_alt['type'] == 'website':
                return "Website contact form"
        
        return "No clear contact method"
    
    def _generate_contact_strategy(self, podcast: PodcastData, enrichment_result: Dict[str, Any]) -> str:
        """Generate recommended contact strategy."""
        response_likelihood = enrichment_result['response_likelihood']
        best_method = enrichment_result['best_contact_method']
        primary_contacts = enrichment_result.get('primary_contacts', [])
        
        if response_likelihood >= 80:
            strategy = f"HIGH SUCCESS POTENTIAL: Use {best_method}. "
        elif response_likelihood >= 60:
            strategy = f"GOOD POTENTIAL: Try {best_method}, follow up if needed. "
        elif response_likelihood >= 40:
            strategy = f"MODERATE POTENTIAL: Use {best_method}, consider multiple touchpoints. "
        else:
            strategy = f"LOW POTENTIAL: Try {best_method}, set low expectations. "
        
        # Add specific tactics
        if primary_contacts and primary_contacts[0]['type'] == 'email':
            strategy += "Personalize email with specific podcast references. "
        
        if 'social' in best_method.lower():
            strategy += "Engage with content before reaching out. "
        
        if len(primary_contacts) > 1:
            strategy += "Multiple contact options available - try primary first, then alternatives. "
        
        return strategy
    
    def _identify_confidence_factors(self, podcast: PodcastData, enrichment_result: Dict[str, Any]) -> List[str]:
        """Identify factors that increase/decrease confidence."""
        factors = []
        
        # Positive factors
        if enrichment_result['response_likelihood'] >= 70:
            factors.append("✅ High response likelihood based on contact quality")
        
        if len(enrichment_result.get('primary_contacts', [])) >= 2:
            factors.append("✅ Multiple high-quality contact methods")
        
        if podcast.host_email and '@' in podcast.host_email and 'noreply' not in podcast.host_email:
            factors.append("✅ Direct host email available")
        
        if podcast.podcast_website and podcast.social_links:
            factors.append("✅ Professional online presence")
        
        # Intelligence factors
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            intelligence = podcast.raw_data.get('intelligence', {})
            if intelligence.get('authority_score', 0) >= 7:
                factors.append("✅ High host authority level")
            if intelligence.get('guest_potential_score', 0) >= 7:
                factors.append("✅ Strong guest appearance potential")
        
        # Risk factors
        if len(enrichment_result.get('primary_contacts', [])) == 0:
            factors.append("⚠️ No high-quality direct contact methods")
        
        if enrichment_result['response_likelihood'] < 40:
            factors.append("⚠️ Low predicted response rate")
        
        validation = enrichment_result.get('contact_validation', {})
        if validation.get('risky', 0) > 0:
            factors.append("⚠️ Some email addresses may be risky/temporary")
        
        return factors
    
    def _has_contact_form(self, page_content: str) -> bool:
        """Check if page has a contact form."""
        form_indicators = ['<form', 'contact-form', 'name="message"', 'name="email"', 'type="submit"']
        content_lower = page_content.lower()
        return any(indicator in content_lower for indicator in form_indicators)
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation."""
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return bool(re.match(pattern, email))


class ContactQualityScorer:
    """Scores contact quality and response likelihood."""
    
    def __init__(self):
        """Initialize contact quality scorer."""
        self.logger = logging.getLogger(__name__)
    
    def score_contact_portfolio(self, podcast: PodcastData) -> Dict[str, Any]:
        """Score the overall contact portfolio for a podcast."""
        portfolio_score = {
            'overall_score': 0.0,
            'contact_diversity_score': 0.0,
            'contact_quality_score': 0.0,
            'response_probability': 0.0,
            'contact_confidence': 'unknown',
            'scoring_factors': []
        }
        
        # Count available contact methods
        contact_methods = 0
        quality_points = 0
        
        # Email contacts
        if podcast.host_email:
            contact_methods += 1
            quality_points += 10
            portfolio_score['scoring_factors'].append("Direct host email (+10 points)")
        
        if podcast.booking_email:
            contact_methods += 1
            quality_points += 8
            portfolio_score['scoring_factors'].append("Booking email (+8 points)")
        
        # Website/contact pages
        if podcast.contact_page_url:
            contact_methods += 1
            quality_points += 6
            portfolio_score['scoring_factors'].append("Contact page available (+6 points)")
        elif podcast.podcast_website:
            contact_methods += 1
            quality_points += 4
            portfolio_score['scoring_factors'].append("Website available (+4 points)")
        
        # Social media
        social_count = len(podcast.social_links) if podcast.social_links else 0
        if social_count > 0:
            contact_methods += 1
            social_points = min(6, social_count * 2)
            quality_points += social_points
            portfolio_score['scoring_factors'].append(f"{social_count} social profiles (+{social_points} points)")
        
        # Calculate diversity score
        portfolio_score['contact_diversity_score'] = min(10.0, contact_methods * 2.5)
        
        # Calculate quality score
        portfolio_score['contact_quality_score'] = min(10.0, quality_points / 4)
        
        # Calculate overall score
        portfolio_score['overall_score'] = (
            portfolio_score['contact_diversity_score'] * 0.4 +
            portfolio_score['contact_quality_score'] * 0.6
        )
        
        # Calculate response probability
        portfolio_score['response_probability'] = self._calculate_response_probability(
            portfolio_score['overall_score'],
            podcast
        )
        
        # Determine confidence level
        portfolio_score['contact_confidence'] = self._determine_confidence_level(
            portfolio_score['overall_score']
        )
        
        return portfolio_score
    
    def _calculate_response_probability(self, overall_score: float, podcast: PodcastData) -> float:
        """Calculate probability of getting a response."""
        base_probability = overall_score * 10  # Convert to percentage
        
        # Adjust based on podcast characteristics
        if hasattr(podcast, 'raw_data') and podcast.raw_data:
            intelligence = podcast.raw_data.get('intelligence', {})
            
            # Authority adjustment
            authority = intelligence.get('authority_score', 0)
            if authority >= 8:
                base_probability += 10
            elif authority >= 6:
                base_probability += 5
            elif authority < 3:
                base_probability -= 10
            
            # Popularity adjustment
            popularity = intelligence.get('popularity_score', 0)
            if popularity >= 8:
                base_probability -= 5  # Very popular hosts get more requests
            elif popularity < 3:
                base_probability += 5  # Less popular hosts more likely to respond
        
        return min(100.0, max(0.0, base_probability))
    
    def _determine_confidence_level(self, overall_score: float) -> str:
        """Determine confidence level based on score."""
        if overall_score >= 8.5:
            return "very_high"
        elif overall_score >= 7.0:
            return "high"
        elif overall_score >= 5.5:
            return "medium"
        elif overall_score >= 3.5:
            return "low"
        else:
            return "very_low"