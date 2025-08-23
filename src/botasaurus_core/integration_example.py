"""
Website Navigator Integration Example
TASK-D001: Complete integration with business scraper system

Demonstrates how to use the website navigator with:
- Business lead generation
- Contact page discovery
- Email extraction
- Data validation and storage
- Export functionality
"""

import os
import sys
import time
import json
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from botasaurus_core.website_navigator import WebsiteNavigator, create_website_navigator, NavigationSession
from botasaurus_core.engine import SessionConfig
from botasaurus_core.models import BusinessLead, ContactInfo, Address, LeadDatabase, Campaign
from botasaurus_core.anti_detection import AntiDetectionManager


class BusinessContactDiscoverySystem:
    """
    Complete business contact discovery system using website navigator
    
    Features:
    - Automated contact page discovery
    - Business lead enhancement
    - Contact information validation
    - Bulk processing capabilities
    - Progress tracking and reporting
    """
    
    def __init__(self, db_path: str = "./business_contacts.db"):
        """Initialize the discovery system"""
        self.database = LeadDatabase(db_path)
        self.navigator = create_website_navigator()
        self.anti_detection = AntiDetectionManager()
        
        # Processing statistics
        self.stats = {
            'leads_processed': 0,
            'contacts_discovered': 0,
            'emails_found': 0,
            'phones_found': 0,
            'forms_discovered': 0,
            'processing_errors': 0,
            'start_time': None,
            'end_time': None
        }
        
    def discover_business_contacts(self, business_urls: List[str], 
                                 campaign_name: str = "Contact Discovery") -> Dict[str, Any]:
        """
        Main method to discover contacts for a list of business websites
        
        Args:
            business_urls: List of business website URLs
            campaign_name: Name for the discovery campaign
            
        Returns:
            Dictionary with discovery results and statistics
        """
        self.stats['start_time'] = datetime.now()
        
        print(f"Starting contact discovery campaign: {campaign_name}")
        print(f"Processing {len(business_urls)} business websites...")
        
        # Create campaign record
        campaign = Campaign(
            id=f"discovery_{int(time.time())}",
            name=campaign_name,
            description=f"Contact discovery for {len(business_urls)} businesses",
            max_results=len(business_urls) * 10,  # Expect multiple contacts per business
            enable_email_validation=True,
            status="running"
        )
        campaign.started_at = self.stats['start_time']
        
        # Process URLs concurrently (in batches to avoid overwhelming)
        batch_size = 5
        all_results = {}
        
        for i in range(0, len(business_urls), batch_size):
            batch = business_urls[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}: {len(batch)} URLs")
            
            # Navigate to websites in this batch
            batch_results = self.navigator.navigate_multiple_sites(batch, max_concurrent=3)
            all_results.update(batch_results)
            
            # Process navigation results
            self._process_navigation_results(batch_results, campaign)
            
            # Small delay between batches
            time.sleep(2)
        
        # Finalize campaign
        campaign.completed_at = datetime.now()
        campaign.status = "completed"
        self.stats['end_time'] = campaign.completed_at
        
        # Calculate final statistics
        final_stats = self._calculate_final_statistics(campaign, all_results)
        
        print(f"\\nCampaign completed: {campaign_name}")
        print(f"Total contacts discovered: {self.stats['contacts_discovered']}")
        print(f"Emails found: {self.stats['emails_found']}")
        print(f"Phones found: {self.stats['phones_found']}")
        print(f"Processing time: {(self.stats['end_time'] - self.stats['start_time']).total_seconds():.1f}s")
        
        return final_stats
    
    def _process_navigation_results(self, navigation_results: Dict[str, NavigationSession], 
                                  campaign: Campaign):
        """Process navigation results and create business leads"""
        
        for base_url, session in navigation_results.items():
            try:
                self.stats['leads_processed'] += 1
                
                if session.errors_encountered:
                    self.stats['processing_errors'] += 1
                    print(f"Warning: Errors encountered for {base_url}: {len(session.errors_encountered)}")
                    continue
                
                # Create or update business leads for each contact page found
                for contact_page in session.contact_pages:
                    if contact_page.has_contact_info():
                        lead = self._create_business_lead_from_contact_page(base_url, contact_page, session)
                        
                        if lead:
                            # Validate and save lead
                            if lead.validate():
                                success = self.database.save_lead(lead)
                                if success:
                                    self.stats['contacts_discovered'] += 1
                                    self.stats['emails_found'] += len(contact_page.email_addresses)
                                    self.stats['phones_found'] += len(contact_page.phone_numbers)
                                    self.stats['forms_discovered'] += len(contact_page.forms_found)
                                    
                                    print(f"✓ Contact discovered: {lead.name} ({len(contact_page.email_addresses)} emails, {len(contact_page.phone_numbers)} phones)")
                                else:
                                    print(f"✗ Failed to save lead for {base_url}")
                            else:
                                print(f"⚠ Lead validation failed for {base_url}: {lead.validation_errors}")
                
            except Exception as e:
                self.stats['processing_errors'] += 1
                print(f"✗ Error processing {base_url}: {str(e)}")
    
    def _create_business_lead_from_contact_page(self, base_url: str, 
                                              contact_page: Any, 
                                              session: NavigationSession) -> Optional[BusinessLead]:
        """Create a BusinessLead from contact page analysis"""
        
        try:
            # Extract business name from URL or page content
            from urllib.parse import urlparse
            domain = urlparse(base_url).netloc.replace('www.', '')
            business_name = domain.replace('.com', '').replace('.org', '').replace('.net', '').title()
            
            # Create contact information
            contact_info = ContactInfo(
                email=contact_page.email_addresses[0] if contact_page.email_addresses else None,
                phone=contact_page.phone_numbers[0] if contact_page.phone_numbers else None,
                website=base_url,
                social_media=contact_page.social_links
            )
            
            # Create address (minimal info from URL)
            address = Address(
                city="Unknown",  # Would need additional parsing
                state="Unknown",
                country="USA"
            )
            
            # Create business lead
            lead = BusinessLead(
                name=business_name,
                category="Business",  # Could be enhanced with categorization
                description=f"Contact discovered via website navigation on {datetime.now().strftime('%Y-%m-%d')}",
                contact=contact_info,
                address=address,
                source="website_navigator",
                source_id=session.session_id
            )
            
            # Calculate confidence score based on contact page analysis
            lead.calculate_confidence()
            
            # Adjust confidence based on contact page quality
            if contact_page.confidence_score > 0.8:
                lead.confidence_score = min(lead.confidence_score + 0.2, 1.0)
            elif contact_page.confidence_score < 0.3:
                lead.confidence_score = max(lead.confidence_score - 0.2, 0.0)
            
            return lead
            
        except Exception as e:
            print(f"Error creating business lead for {base_url}: {str(e)}")
            return None
    
    def _calculate_final_statistics(self, campaign: Campaign, 
                                  navigation_results: Dict[str, NavigationSession]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for the discovery campaign"""
        
        # Calculate campaign metrics
        campaign.calculate_metrics([])  # Would need to fetch leads from database
        
        # Aggregate navigation statistics
        total_pages_visited = sum(len(session.pages_visited) for session in navigation_results.values())
        total_contact_pages = sum(len(session.contact_pages) for session in navigation_results.values())
        total_about_pages = sum(len(session.about_pages) for session in navigation_results.values())
        total_team_pages = sum(len(session.team_pages) for session in navigation_results.values())
        
        # Calculate efficiency metrics
        processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        leads_per_hour = (self.stats['leads_processed'] / processing_time) * 3600 if processing_time > 0 else 0
        contacts_per_lead = self.stats['contacts_discovered'] / self.stats['leads_processed'] if self.stats['leads_processed'] > 0 else 0
        
        # Error rate
        error_rate = (self.stats['processing_errors'] / self.stats['leads_processed']) * 100 if self.stats['leads_processed'] > 0 else 0
        
        return {
            'campaign': {
                'name': campaign.name,
                'id': campaign.id,
                'start_time': campaign.started_at.isoformat(),
                'end_time': campaign.completed_at.isoformat(),
                'duration_seconds': processing_time,
                'status': campaign.status
            },
            'processing_statistics': {
                'leads_processed': self.stats['leads_processed'],
                'contacts_discovered': self.stats['contacts_discovered'],
                'emails_found': self.stats['emails_found'],
                'phones_found': self.stats['phones_found'],
                'forms_discovered': self.stats['forms_discovered'],
                'processing_errors': self.stats['processing_errors']
            },
            'navigation_statistics': {
                'total_pages_visited': total_pages_visited,
                'total_contact_pages': total_contact_pages,
                'total_about_pages': total_about_pages,
                'total_team_pages': total_team_pages,
                'unique_sessions': len(navigation_results)
            },
            'efficiency_metrics': {
                'leads_per_hour': leads_per_hour,
                'contacts_per_lead': contacts_per_lead,
                'error_rate_percent': error_rate,
                'pages_per_lead': total_pages_visited / self.stats['leads_processed'] if self.stats['leads_processed'] > 0 else 0
            },
            'database_statistics': self.database.get_statistics()
        }
    
    def enhance_existing_leads(self, limit: int = 50) -> Dict[str, Any]:
        """
        Enhance existing business leads by discovering contact information
        
        Args:
            limit: Maximum number of leads to enhance
            
        Returns:
            Enhancement results and statistics
        """
        print(f"Enhancing existing leads (limit: {limit})...")
        
        # Get leads that need contact enhancement (missing email/phone)
        from botasaurus_core.models import LeadStatus
        leads_to_enhance = []
        
        # Query leads with incomplete contact info
        all_leads = self.database.query_leads(status=LeadStatus.VALIDATED, limit=limit)
        
        for lead in all_leads:
            if not lead.contact.email or not lead.contact.phone:
                if lead.contact.website:  # Need a website to enhance
                    leads_to_enhance.append(lead)
        
        print(f"Found {len(leads_to_enhance)} leads that can be enhanced")
        
        if not leads_to_enhance:
            return {'message': 'No leads found that need enhancement'}
        
        # Extract websites to navigate
        websites = [lead.contact.website for lead in leads_to_enhance if lead.contact.website]
        
        # Discover contacts for these websites
        enhancement_stats = self.discover_business_contacts(
            websites, 
            campaign_name=f"Lead Enhancement {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        return enhancement_stats
    
    def export_discovered_contacts(self, output_format: str = 'csv', 
                                 filename: Optional[str] = None) -> str:
        """
        Export discovered contacts to file
        
        Args:
            output_format: Export format ('csv', 'json', 'xlsx')
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"discovered_contacts_{timestamp}.{output_format}"
        
        # Get all validated leads
        from botasaurus_core.models import LeadStatus
        discovered_leads = self.database.query_leads(
            status=LeadStatus.VALIDATED, 
            limit=10000  # Large limit to get all
        )
        
        if output_format.lower() == 'csv':
            return self._export_to_csv(discovered_leads, filename)
        elif output_format.lower() == 'json':
            return self._export_to_json(discovered_leads, filename)
        else:
            raise ValueError(f"Unsupported export format: {output_format}")
    
    def _export_to_csv(self, leads: List[BusinessLead], filename: str) -> str:
        """Export leads to CSV format"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'name', 'category', 'email', 'phone', 'website',
                'city', 'state', 'country', 'confidence_score',
                'scraped_at', 'source'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in leads:
                writer.writerow({
                    'name': lead.name,
                    'category': lead.category,
                    'email': lead.contact.email,
                    'phone': lead.contact.phone,
                    'website': lead.contact.website,
                    'city': lead.address.city,
                    'state': lead.address.state,
                    'country': lead.address.country,
                    'confidence_score': lead.confidence_score,
                    'scraped_at': lead.scraped_at.isoformat(),
                    'source': lead.source
                })
        
        print(f"Exported {len(leads)} contacts to {filename}")
        return filename
    
    def _export_to_json(self, leads: List[BusinessLead], filename: str) -> str:
        """Export leads to JSON format"""
        leads_data = [lead.to_dict() for lead in leads]
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(leads_data, jsonfile, indent=2, default=str)
        
        print(f"Exported {len(leads)} contacts to {filename}")
        return filename
    
    def get_discovery_report(self) -> Dict[str, Any]:
        """Generate a comprehensive discovery report"""
        db_stats = self.database.get_statistics()
        
        return {
            'system_statistics': self.stats,
            'database_statistics': db_stats,
            'discovery_efficiency': {
                'contacts_per_lead': db_stats['total_leads'] / max(self.stats['leads_processed'], 1),
                'email_discovery_rate': db_stats['email_rate'],
                'phone_discovery_rate': db_stats['phone_rate']
            },
            'recommendations': self._generate_recommendations(db_stats)
        }
    
    def _generate_recommendations(self, db_stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on discovery statistics"""
        recommendations = []
        
        if db_stats['email_rate'] < 0.5:
            recommendations.append("Consider improving email extraction patterns - current rate is low")
        
        if db_stats['phone_rate'] < 0.3:
            recommendations.append("Phone number extraction could be enhanced")
        
        if self.stats['processing_errors'] / max(self.stats['leads_processed'], 1) > 0.2:
            recommendations.append("High error rate detected - review anti-detection settings")
        
        if not recommendations:
            recommendations.append("System performing well - all metrics within expected ranges")
        
        return recommendations
    
    def cleanup(self):
        """Clean up resources"""
        if self.database:
            self.database.close()


def demo_contact_discovery():
    """Demonstration of the contact discovery system"""
    print("Business Contact Discovery System Demo")
    print("TASK-D001 Integration Example")
    print("="*50)
    
    # Create discovery system
    discovery_system = BusinessContactDiscoverySystem("./demo_contacts.db")
    
    # Example business websites (using reliable test sites)
    demo_websites = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://www.python.org"
    ]
    
    try:
        # Run contact discovery
        print("\\n1. Running contact discovery...")
        results = discovery_system.discover_business_contacts(
            demo_websites, 
            campaign_name="Demo Contact Discovery"
        )
        
        # Display results
        print(f"\\n2. Discovery Results:")
        print(f"   Contacts discovered: {results['processing_statistics']['contacts_discovered']}")
        print(f"   Emails found: {results['processing_statistics']['emails_found']}")
        print(f"   Phones found: {results['processing_statistics']['phones_found']}")
        print(f"   Processing time: {results['campaign']['duration_seconds']:.1f}s")
        
        # Export results
        print("\\n3. Exporting results...")
        csv_file = discovery_system.export_discovered_contacts('csv')
        print(f"   Results exported to: {csv_file}")
        
        # Generate report
        print("\\n4. System Report:")
        report = discovery_system.get_discovery_report()
        print(f"   Database statistics: {json.dumps(report['database_statistics'], indent=2)}")
        
        if report['recommendations']:
            print("\\n5. Recommendations:")
            for rec in report['recommendations']:
                print(f"   • {rec}")
        
        print("\\n✓ Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"\\n✗ Demo failed: {str(e)}")
        return False
    
    finally:
        discovery_system.cleanup()


if __name__ == "__main__":
    success = demo_contact_discovery()
    print(f"\\nDemo {'PASSED' if success else 'FAILED'}")