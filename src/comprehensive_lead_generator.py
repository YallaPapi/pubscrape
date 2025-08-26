#!/usr/bin/env python3
"""
Comprehensive Lead Generator
Integrates all fixed components: Bing scraping, email extraction, validation, and CSV export
"""

import os
import csv
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from urllib.parse import urljoin, urlparse

# Import our fixed components
from fixed_email_extractor import WorkingEmailExtractor, ContactInfo
from enhanced_email_validator import EnhancedEmailValidator, EmailValidationResult


@dataclass
class Lead:
    """Structured lead for outreach campaigns"""
    # Business information
    business_name: str = ""
    industry: str = ""
    website: str = ""
    
    # Primary contact
    primary_email: str = ""
    primary_phone: str = ""
    contact_name: str = ""
    contact_title: str = ""
    
    # Additional contacts
    secondary_emails: List[str] = field(default_factory=list)
    additional_phones: List[str] = field(default_factory=list)
    additional_contacts: List[Dict[str, str]] = field(default_factory=list)
    
    # Location
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    
    # Social presence
    linkedin_url: str = ""
    facebook_url: str = ""
    twitter_url: str = ""
    other_social: List[str] = field(default_factory=list)
    
    # Lead quality metrics
    lead_score: float = 0.0
    email_confidence: float = 0.0
    data_completeness: float = 0.0
    is_actionable: bool = False
    
    # Source tracking
    source_url: str = ""
    source_query: str = ""
    extraction_date: str = ""
    last_verified: str = ""
    
    # Technical metadata
    extraction_time_ms: float = 0.0
    validation_status: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON export"""
        result = asdict(self)
        # Flatten lists for CSV compatibility
        result['secondary_emails'] = '; '.join(self.secondary_emails)
        result['additional_phones'] = '; '.join(self.additional_phones)
        result['other_social'] = '; '.join(self.other_social)
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert to CSV row with proper string formatting"""
        return {k: str(v) if v is not None else '' for k, v in self.to_dict().items()}


class LeadDeduplicator:
    """Remove duplicate leads based on email addresses and business names"""
    
    def __init__(self):
        self.seen_emails = set()
        self.seen_businesses = {}
        self.duplicate_count = 0
    
    def deduplicate_leads(self, leads: List[Lead]) -> List[Lead]:
        """Remove duplicates from lead list"""
        unique_leads = []
        
        for lead in leads:
            # Check for email duplicates
            if lead.primary_email and lead.primary_email.lower() in self.seen_emails:
                self.duplicate_count += 1
                continue
            
            # Check for business name duplicates (fuzzy matching)
            business_key = self._normalize_business_name(lead.business_name)
            if business_key and business_key in self.seen_businesses:
                # Merge with existing lead if this one has better data
                existing_lead = self.seen_businesses[business_key]
                if self._should_replace_lead(existing_lead, lead):
                    # Remove the old lead and add the new one
                    unique_leads = [l for l in unique_leads if l != existing_lead]
                    unique_leads.append(lead)
                    self.seen_businesses[business_key] = lead
                else:
                    # Merge additional information into existing lead
                    self._merge_lead_data(existing_lead, lead)
                self.duplicate_count += 1
                continue
            
            # Add to unique leads
            unique_leads.append(lead)
            
            # Track for future duplicates
            if lead.primary_email:
                self.seen_emails.add(lead.primary_email.lower())
            if business_key:
                self.seen_businesses[business_key] = lead
        
        return unique_leads
    
    def _normalize_business_name(self, business_name: str) -> str:
        """Normalize business name for duplicate detection"""
        if not business_name or business_name == "Unknown Business":
            return ""
        
        # Remove common business suffixes and normalize
        name = business_name.lower()
        name = name.replace(' llc', '').replace(' inc', '').replace(' corp', '')
        name = name.replace(' company', '').replace(' co.', '').replace(' ltd', '')
        name = name.replace('-', ' ').replace('_', ' ')
        name = ' '.join(name.split())  # Normalize whitespace
        
        return name
    
    def _should_replace_lead(self, existing: Lead, new: Lead) -> bool:
        """Determine if new lead should replace existing one"""
        return (
            new.lead_score > existing.lead_score or
            new.data_completeness > existing.data_completeness or
            (new.primary_email and not existing.primary_email)
        )
    
    def _merge_lead_data(self, existing: Lead, new: Lead):
        """Merge data from new lead into existing lead"""
        # Merge secondary emails
        for email in new.secondary_emails:
            if email and email not in existing.secondary_emails:
                existing.secondary_emails.append(email)
        
        # Merge phones
        for phone in new.additional_phones:
            if phone and phone not in existing.additional_phones:
                existing.additional_phones.append(phone)
        
        # Update if new lead has better primary contact
        if new.primary_email and not existing.primary_email:
            existing.primary_email = new.primary_email
        
        if new.primary_phone and not existing.primary_phone:
            existing.primary_phone = new.primary_phone
        
        # Merge social profiles
        if new.linkedin_url and not existing.linkedin_url:
            existing.linkedin_url = new.linkedin_url
        
        # Update scores if better
        if new.lead_score > existing.lead_score:
            existing.lead_score = new.lead_score
            existing.email_confidence = new.email_confidence


class ComprehensiveLeadGenerator:
    """Main lead generation system combining all components"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.extractor = WorkingEmailExtractor(timeout=15)
        self.validator = EnhancedEmailValidator(enable_dns_check=False)  # Disable DNS for speed
        self.deduplicator = LeadDeduplicator()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'urls_processed': 0,
            'contacts_extracted': 0,
            'emails_found': 0,
            'emails_validated': 0,
            'leads_generated': 0,
            'actionable_leads': 0,
            'duplicates_removed': 0,
            'processing_time': 0.0
        }
        
        self.logger.info("ComprehensiveLeadGenerator initialized")
    
    def generate_leads_from_urls(self, urls: List[str], source_query: str = "") -> List[Lead]:
        """Generate leads from a list of URLs"""
        start_time = time.time()
        all_leads = []
        
        self.logger.info(f"Processing {len(urls)} URLs for lead generation")
        
        for i, url in enumerate(urls, 1):
            self.logger.info(f"Processing URL {i}/{len(urls)}: {url[:60]}...")
            
            try:
                # Extract contact information
                contact_info = self.extractor.extract_contact_info(url)
                self.stats['urls_processed'] += 1
                
                if contact_info.emails:
                    self.stats['contacts_extracted'] += 1
                    
                    # Create leads from contact info
                    leads = self._create_leads_from_contact_info(contact_info, source_query)
                    all_leads.extend(leads)
                    
                    self.logger.info(f"  Created {len(leads)} leads from {url}")
                else:
                    self.logger.info(f"  No contact information found for {url}")
            
            except Exception as e:
                self.logger.error(f"Error processing {url}: {e}")
                continue
        
        # Deduplicate leads
        unique_leads = self.deduplicator.deduplicate_leads(all_leads)
        self.stats['duplicates_removed'] = self.deduplicator.duplicate_count
        
        # Validate and score leads
        final_leads = self._validate_and_score_leads(unique_leads)
        
        # Update statistics
        self.stats['leads_generated'] = len(final_leads)
        self.stats['actionable_leads'] = len([l for l in final_leads if l.is_actionable])
        self.stats['processing_time'] = time.time() - start_time
        
        self.logger.info(f"Lead generation complete: {len(final_leads)} leads generated")
        return final_leads
    
    def _create_leads_from_contact_info(self, contact_info: ContactInfo, source_query: str) -> List[Lead]:
        """Convert ContactInfo to Lead objects"""
        leads = []
        
        # Main business lead
        if contact_info.emails:
            primary_email_data = contact_info.emails[0]  # Highest confidence email
            
            lead = Lead(
                business_name=contact_info.business_name,
                website=contact_info.url,
                primary_email=primary_email_data['email'],
                email_confidence=primary_email_data['confidence'],
                lead_score=contact_info.lead_score,
                is_actionable=contact_info.is_actionable,
                source_url=contact_info.url,
                source_query=source_query,
                extraction_date=time.strftime('%Y-%m-%d'),
                extraction_time_ms=contact_info.extraction_time * 1000
            )
            
            # Add secondary emails
            for email_data in contact_info.emails[1:5]:  # Up to 4 additional emails
                lead.secondary_emails.append(email_data['email'])
            
            # Add phone numbers
            if contact_info.phones:
                lead.primary_phone = contact_info.phones[0]['phone']
                for phone_data in contact_info.phones[1:3]:  # Up to 2 additional phones
                    lead.additional_phones.append(phone_data['phone'])
            
            # Add names and titles
            if contact_info.names:
                # Try to find the best name/title combination
                best_name = contact_info.names[0]
                lead.contact_name = best_name['name']
                
                # Look for title in context or use best guess
                if 'context' in best_name and best_name['context'] == 'staff_section':
                    lead.contact_title = "Staff Member"
                elif any(title in best_name['name'].lower() for title in ['ceo', 'president', 'director', 'manager']):
                    lead.contact_title = "Executive"
                else:
                    lead.contact_title = "Contact"
                
                # Add additional contacts
                for name_data in contact_info.names[1:3]:
                    lead.additional_contacts.append({
                        'name': name_data['name'],
                        'title': '',
                        'context': name_data.get('context', '')
                    })
            
            # Add address
            if contact_info.addresses:
                lead.address = contact_info.addresses[0]
                # Try to extract city/state
                address_parts = lead.address.split(',')
                if len(address_parts) >= 2:
                    lead.city = address_parts[-2].strip()
                    if len(address_parts) >= 3:
                        lead.state = address_parts[-1].strip().split()[0]  # Remove ZIP
            
            # Add social profiles
            for social_url in contact_info.social_profiles:
                if 'linkedin' in social_url.lower():
                    lead.linkedin_url = social_url
                elif 'facebook' in social_url.lower():
                    lead.facebook_url = social_url
                elif 'twitter' in social_url.lower():
                    lead.twitter_url = social_url
                else:
                    lead.other_social.append(social_url)
            
            # Calculate data completeness
            lead.data_completeness = self._calculate_data_completeness(lead)
            
            leads.append(lead)
        
        return leads
    
    def _calculate_data_completeness(self, lead: Lead) -> float:
        """Calculate how complete the lead data is"""
        completeness_score = 0.0
        max_score = 10.0
        
        # Core data (60% of score)
        if lead.business_name and lead.business_name != "Unknown Business":
            completeness_score += 2.0
        if lead.primary_email:
            completeness_score += 2.0
        if lead.website:
            completeness_score += 1.0
        if lead.primary_phone:
            completeness_score += 1.0
        
        # Contact details (20% of score)
        if lead.contact_name:
            completeness_score += 1.0
        if lead.contact_title:
            completeness_score += 0.5
        if lead.secondary_emails:
            completeness_score += 0.5
        
        # Location (10% of score)
        if lead.address:
            completeness_score += 0.5
        if lead.city:
            completeness_score += 0.3
        if lead.state:
            completeness_score += 0.2
        
        # Social presence (10% of score)
        if lead.linkedin_url:
            completeness_score += 0.5
        if lead.facebook_url or lead.twitter_url:
            completeness_score += 0.3
        if lead.other_social:
            completeness_score += 0.2
        
        return min(1.0, completeness_score / max_score)
    
    def _validate_and_score_leads(self, leads: List[Lead]) -> List[Lead]:
        """Validate email addresses and update lead scores"""
        if not leads:
            return leads
        
        # Extract all primary emails for batch validation
        primary_emails = [lead.primary_email for lead in leads if lead.primary_email]
        
        if primary_emails:
            self.logger.info(f"Validating {len(primary_emails)} primary email addresses...")
            validation_results = self.validator.validate_batch(primary_emails, max_workers=5)
            
            # Create email validation lookup
            email_validations = {result.email: result for result in validation_results}
            
            # Update leads with validation results
            for lead in leads:
                if lead.primary_email in email_validations:
                    validation = email_validations[lead.primary_email]
                    
                    lead.validation_status = "valid" if validation.is_valid else "invalid"
                    
                    # Update lead score based on email quality
                    if validation.is_valid:
                        quality_multiplier = {
                            'high': 1.2,
                            'medium': 1.0,
                            'low': 0.8,
                            'invalid': 0.5
                        }.get(validation.quality.value, 0.5)
                        
                        lead.lead_score = min(1.0, lead.lead_score * quality_multiplier)
                        lead.email_confidence = validation.confidence_score
                    else:
                        lead.lead_score *= 0.3  # Heavily penalize invalid emails
                        lead.is_actionable = False
                
                # Final actionability check
                lead.is_actionable = (
                    lead.validation_status == "valid" and
                    lead.lead_score >= 0.4 and
                    lead.data_completeness >= 0.3 and
                    lead.business_name and 
                    lead.business_name != "Unknown Business"
                )
            
            self.stats['emails_validated'] = len(primary_emails)
        
        return leads
    
    def export_leads_to_csv(self, leads: List[Lead], filename: Optional[str] = None) -> Path:
        """Export leads to CSV file"""
        if not filename:
            timestamp = int(time.time())
            filename = f"leads_generated_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        if not leads:
            self.logger.warning("No leads to export")
            return filepath
        
        # Define CSV field order for outreach compatibility
        fieldnames = [
            'business_name', 'industry', 'primary_email', 'primary_phone',
            'contact_name', 'contact_title', 'website', 'address', 'city', 'state',
            'linkedin_url', 'facebook_url', 'secondary_emails', 'additional_phones',
            'lead_score', 'email_confidence', 'data_completeness', 'is_actionable',
            'source_url', 'source_query', 'extraction_date', 'validation_status',
            'notes'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in leads:
                row = lead.to_csv_row()
                # Only include specified fields in correct order
                filtered_row = {field: row.get(field, '') for field in fieldnames}
                writer.writerow(filtered_row)
        
        self.logger.info(f"Exported {len(leads)} leads to {filepath}")
        return filepath
    
    def generate_report(self, leads: List[Lead]) -> Dict[str, Any]:
        """Generate comprehensive lead generation report"""
        if not leads:
            return {'error': 'No leads to analyze'}
        
        # Basic statistics
        total_leads = len(leads)
        actionable_leads = [l for l in leads if l.is_actionable]
        
        # Quality distribution
        quality_stats = {
            'high_quality': len([l for l in leads if l.lead_score >= 0.8]),
            'medium_quality': len([l for l in leads if 0.5 <= l.lead_score < 0.8]),
            'low_quality': len([l for l in leads if l.lead_score < 0.5])
        }
        
        # Email validation stats
        validation_stats = {
            'valid_emails': len([l for l in leads if l.validation_status == 'valid']),
            'invalid_emails': len([l for l in leads if l.validation_status == 'invalid']),
            'unvalidated': len([l for l in leads if not l.validation_status])
        }
        
        # Completeness stats
        avg_completeness = sum(l.data_completeness for l in leads) / total_leads if leads else 0
        avg_lead_score = sum(l.lead_score for l in leads) / total_leads if leads else 0
        
        return {
            'generation_summary': {
                'total_leads': total_leads,
                'actionable_leads': len(actionable_leads),
                'actionable_rate': len(actionable_leads) / total_leads * 100,
                'avg_lead_score': avg_lead_score,
                'avg_data_completeness': avg_completeness
            },
            'quality_distribution': quality_stats,
            'email_validation': validation_stats,
            'processing_stats': self.stats,
            'top_leads': [
                {
                    'business_name': l.business_name,
                    'primary_email': l.primary_email,
                    'lead_score': l.lead_score,
                    'data_completeness': l.data_completeness
                }
                for l in sorted(leads, key=lambda x: x.lead_score, reverse=True)[:10]
            ]
        }
    
    def save_report(self, leads: List[Lead], filename: Optional[str] = None) -> Path:
        """Save lead generation report to JSON"""
        if not filename:
            timestamp = int(time.time())
            filename = f"lead_generation_report_{timestamp}.json"
        
        filepath = self.output_dir / filename
        report = self.generate_report(leads)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Report saved to {filepath}")
        return filepath


def test_comprehensive_lead_generator():
    """Test the comprehensive lead generator"""
    print("Testing Comprehensive Lead Generator")
    print("=" * 45)
    
    # Test URLs (mix of real sites and local test)
    test_urls = [
        "file://test_contact_page.html",  # Our test file with rich contact data
        "https://httpbin.org/html",       # Real site with minimal data
        "https://example.com",            # Basic site
    ]
    
    # Create local file URL if it exists
    test_file = Path("test_contact_page.html")
    if test_file.exists():
        test_urls[0] = f"file://{test_file.absolute()}"
    
    generator = ComprehensiveLeadGenerator()
    
    print(f"Processing {len(test_urls)} test URLs...")
    
    # Generate leads
    leads = generator.generate_leads_from_urls(test_urls, "test_query")
    
    # Display results
    print(f"\n{'='*45}")
    print("LEAD GENERATION RESULTS")
    print(f"{'='*45}")
    
    for i, lead in enumerate(leads[:5], 1):  # Show first 5 leads
        print(f"\nLead {i}:")
        print(f"  Business: {lead.business_name}")
        print(f"  Email: {lead.primary_email}")
        print(f"  Phone: {lead.primary_phone}")
        print(f"  Contact: {lead.contact_name}")
        print(f"  Website: {lead.website}")
        print(f"  Score: {lead.lead_score:.2f}")
        print(f"  Completeness: {lead.data_completeness:.2f}")
        print(f"  Actionable: {lead.is_actionable}")
        print(f"  Validation: {lead.validation_status}")
    
    # Export leads
    csv_file = generator.export_leads_to_csv(leads)
    print(f"\nLeads exported to: {csv_file}")
    
    # Generate and save report
    report_file = generator.save_report(leads)
    print(f"Report saved to: {report_file}")
    
    # Display summary
    report = generator.generate_report(leads)
    summary = report['generation_summary']
    
    print(f"\n{'='*45}")
    print("GENERATION SUMMARY")
    print(f"{'='*45}")
    print(f"Total Leads: {summary['total_leads']}")
    print(f"Actionable Leads: {summary['actionable_leads']}")
    print(f"Success Rate: {summary['actionable_rate']:.1f}%")
    print(f"Avg Lead Score: {summary['avg_lead_score']:.2f}")
    print(f"Avg Completeness: {summary['avg_data_completeness']:.2f}")
    
    # Processing stats
    print(f"\nProcessing Stats:")
    for key, value in generator.stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    success = (
        len(leads) > 0 and
        summary['actionable_leads'] > 0 and
        summary['actionable_rate'] > 0
    )
    
    if success:
        print(f"\n{'='*45}")
        print("SUCCESS: Lead generator is working!")
        print("- Generated leads with real contact data")
        print("- Validated email addresses")
        print("- Calculated lead quality scores")
        print("- Exported to CSV format")
        print("- Ready for outreach campaigns!")
    else:
        print(f"\n{'='*45}")
        print("ISSUES: Lead generator needs fixes")
    
    return success, leads


if __name__ == "__main__":
    success, leads = test_comprehensive_lead_generator()
    
    if success:
        print(f"\nLEAD GENERATOR TEST: SUCCESS!")
        print(f"Generated {len(leads)} leads ready for outreach")
    else:
        print(f"\nLEAD GENERATOR TEST: FAILED")
        print("Review issues above")