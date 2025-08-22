#!/usr/bin/env python3
"""
Enhanced Santa Monica Restaurant Scraper with Strict Validation
Filters out fake data, technical debt, and placeholder content
"""

from BingNavigator.tools.SerpFetchTool_requests import SerpFetchTool
from fixed_email_extractor import WorkingEmailExtractor
import csv
import json
import re
from datetime import datetime
import time

print('=== ENHANCED SANTA MONICA RESTAURANT SCRAPER (STRICT VALIDATION) ===')

class StrictRestaurantValidator:
    def __init__(self):
        self.valid_area_codes = ['310', '424', '323', '213', '818', '747']  # LA County area codes
        self.santa_monica_zip_codes = ['90401', '90402', '90403', '90404', '90405']
        
        # Expanded fake data detection
        self.fake_indicators = [
            'test', 'example', 'demo', 'fake', 'sample', 'placeholder',
            'user@domain.com', 'info@example.com', 'contact@test.com',
            '555-', '123-456-', 'xxx-xxx-xxxx'
        ]
        
        # Non-restaurant business name patterns
        self.non_restaurant_patterns = [
            'ready to get started', 'contact us', 'about us', 'home',
            'welcome', 'click here', 'learn more', 'get started',
            'digital agency', 'web design', 'marketing', 'seo'
        ]
        
        # Invalid area codes (non-existent)
        self.invalid_area_codes = ['170', '171', '172', '000', '999']
        
    def validate_email(self, email):
        if not email:
            return {'valid': True, 'score': 0.0, 'issues': ['No email provided']}
        
        issues = []
        score = 0.5
        
        # Check for placeholder patterns
        if any(fake in email.lower() for fake in self.fake_indicators):
            issues.append('Placeholder/fake email detected')
            return {'valid': False, 'score': 0.0, 'issues': issues}
        
        # Basic email format validation
        if '@' not in email or '.' not in email.split('@')[1]:
            issues.append('Invalid email format')
            return {'valid': False, 'score': 0.0, 'issues': issues}
        
        # Domain validation
        domain = email.split('@')[1].lower()
        if domain in ['domain.com', 'example.com', 'test.com', 'fake.com']:
            issues.append('Test domain detected')
            return {'valid': False, 'score': 0.0, 'issues': issues}
        
        # Business email scoring
        if any(pattern in email.lower() for pattern in ['info@', 'contact@', 'hello@', 'admin@']):
            score += 0.3
        
        return {'valid': True, 'score': score, 'issues': issues}
    
    def validate_phone(self, phone):
        if not phone:
            return {'valid': True, 'score': 0.0, 'issues': ['No phone provided']}
        
        issues = []
        score = 0.5
        
        # Extract digits
        phone_digits = re.sub(r'[^0-9]', '', phone)
        
        # Check for fake patterns
        if phone_digits.startswith('555') or phone_digits in ['1234567890', '0000000000']:
            issues.append('Fake phone pattern')
            return {'valid': False, 'score': 0.0, 'issues': issues}
        
        # Check for invalid area codes
        if len(phone_digits) >= 3:
            area_code = phone_digits[:3]
            if area_code in self.invalid_area_codes:
                issues.append(f'Invalid area code: {area_code}')
                return {'valid': False, 'score': 0.0, 'issues': issues}
            
            # Valid LA area codes
            if area_code in self.valid_area_codes:
                score += 0.3
            else:
                issues.append(f'Non-LA area code: {area_code}')
                score -= 0.1
        
        return {'valid': True, 'score': score, 'issues': issues}
    
    def validate_business_name(self, name):
        if not name:
            return {'valid': False, 'score': 0.0, 'issues': ['No business name']}
        
        issues = []
        score = 0.5
        
        name_lower = name.lower()
        
        # Check for non-restaurant patterns
        if any(pattern in name_lower for pattern in self.non_restaurant_patterns):
            issues.append('Non-restaurant business name detected')
            return {'valid': False, 'score': 0.0, 'issues': issues}
        
        # Check for fake indicators
        if any(fake in name_lower for fake in self.fake_indicators):
            issues.append('Fake business name pattern')
            return {'valid': False, 'score': 0.0, 'issues': issues}
        
        # Restaurant indicators
        restaurant_keywords = ['restaurant', 'cafe', 'bistro', 'grill', 'kitchen', 'dining', 'eatery', 'bar']
        if any(keyword in name_lower for keyword in restaurant_keywords):
            score += 0.3
        
        # Length validation (too short names are suspicious)
        if len(name.strip()) < 3:
            issues.append('Business name too short')
            score -= 0.2
        
        return {'valid': True, 'score': score, 'issues': issues}
    
    def validate_lead(self, lead_data):
        """Comprehensive lead validation with strict filtering"""
        
        # Validate each component
        email_validation = self.validate_email(lead_data.get('primary_email', ''))
        phone_validation = self.validate_phone(lead_data.get('primary_phone', ''))
        name_validation = self.validate_business_name(lead_data.get('business_name', ''))
        
        # Collect all issues
        all_issues = []
        all_issues.extend(email_validation['issues'])
        all_issues.extend(phone_validation['issues']) 
        all_issues.extend(name_validation['issues'])
        
        # Calculate composite score
        total_score = (name_validation['score'] * 0.5 + 
                      email_validation['score'] * 0.3 + 
                      phone_validation['score'] * 0.2)
        
        # Strict validation - reject if any critical issues
        has_critical_issues = (
            not email_validation['valid'] or 
            not phone_validation['valid'] or 
            not name_validation['valid']
        )
        
        # Must have at least one form of contact (email OR phone)
        has_contact = lead_data.get('primary_email') or lead_data.get('primary_phone')
        
        is_valid = not has_critical_issues and has_contact and total_score >= 0.6
        
        return {
            'is_valid': is_valid,
            'score': total_score,
            'issues': all_issues,
            'component_scores': {
                'email': email_validation['score'],
                'phone': phone_validation['score'], 
                'business_name': name_validation['score']
            }
        }

# Known high-quality Santa Monica restaurants for testing
quality_restaurant_sites = [
    'https://www.formarestaurant.com',  # Confirmed working
    'https://www.thelobster.com',       # Needs filtering for fake email
    'https://www.noburestaurants.com',  # Needs area code validation
    'https://melissesantamonica.com',
    'https://www.valentinossantamonica.com',
    'https://www.chinoisonmain.com',
    'https://www.ivy.restaurant',
    'https://www.blueplatesantamonica.com',
    'https://www.library-ale-house.com',
    'https://www.rustyspelican.com'
]

# Initialize components
validator = StrictRestaurantValidator()
extractor = WorkingEmailExtractor()
validated_leads = []

print(f'Processing {len(quality_restaurant_sites)} high-quality restaurant websites...')

for site_num, url in enumerate(quality_restaurant_sites, 1):
    print(f'\n--- PROCESSING SITE {site_num}/{len(quality_restaurant_sites)} ---')
    print(f'URL: {url}')
    
    try:
        # Extract contact information
        contact_info = extractor.extract_contact_info(url)
        
        if contact_info:
            # Create lead record
            lead = {
                'business_name': contact_info.business_name or '',
                'primary_email': contact_info.emails[0]['email'] if contact_info.emails else '',
                'primary_phone': contact_info.phones[0]['phone'] if contact_info.phones else '',
                'contact_name': contact_info.names[0]['name'] if contact_info.names else '',
                'website': url,
                'address': contact_info.addresses[0] if contact_info.addresses else '',
                'city': 'Santa Monica',
                'state': 'CA',
                'extraction_score': contact_info.lead_score,
                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'business_type': 'restaurant'
            }
            
            print(f'Extracted: {lead["business_name"]}')
            print(f'Email: {lead["primary_email"]}')
            print(f'Phone: {lead["primary_phone"]}')
            
            # Strict validation
            validation_result = validator.validate_lead(lead)
            
            print(f'Validation Score: {validation_result["score"]:.3f}')
            print(f'Component Scores: {validation_result["component_scores"]}')
            
            if validation_result['is_valid']:
                lead['validation_score'] = validation_result['score']
                lead['validation_issues'] = validation_result['issues']
                lead['is_validated'] = True
                lead['lead_id'] = f'CLEAN_{len(validated_leads)+1:03d}'
                
                validated_leads.append(lead)
                print('✅ LEAD VALIDATED AND ACCEPTED')
            else:
                print(f'❌ LEAD REJECTED: {validation_result["issues"]}')
        else:
            print('❌ No contact information extracted')
            
    except Exception as e:
        print(f'❌ Extraction error: {str(e)[:100]}')
    
    # Rate limiting
    time.sleep(2)

# Export clean results
print(f'\n=== CLEAN EXPORT RESULTS ===')
print(f'Total validated leads: {len(validated_leads)}')

if validated_leads:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'clean_santa_monica_restaurants_{timestamp}.csv'
    
    headers = [
        'lead_id', 'business_name', 'primary_email', 'primary_phone', 
        'contact_name', 'website', 'address', 'city', 'state',
        'extraction_score', 'validation_score', 'extraction_date', 
        'business_type', 'is_validated'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(validated_leads)
    
    print(f'✅ Clean leads exported: {csv_filename}')
    
    # Summary report
    total_emails = sum(1 for lead in validated_leads if lead['primary_email'])
    total_phones = sum(1 for lead in validated_leads if lead['primary_phone'])
    avg_score = sum(lead['validation_score'] for lead in validated_leads) / len(validated_leads)
    
    report = {
        'timestamp': timestamp,
        'total_clean_leads': len(validated_leads),
        'leads_with_emails': total_emails,
        'leads_with_phones': total_phones,
        'average_validation_score': avg_score,
        'csv_file': csv_filename,
        'quality_assurance': 'STRICT_VALIDATION_APPLIED',
        'fake_data_filtered': 'YES'
    }
    
    with open(f'clean_restaurant_report_{timestamp}.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f'\n🎯 CLEAN DATA SUMMARY:')
    print(f'   Clean validated leads: {len(validated_leads)}')
    print(f'   Leads with emails: {total_emails}')
    print(f'   Leads with phones: {total_phones}')
    print(f'   Average validation score: {avg_score:.3f}')
    
    # Show clean samples
    print(f'\n📋 VERIFIED CLEAN LEADS:')
    for i, lead in enumerate(validated_leads[:3]):
        print(f'{i+1}. {lead["business_name"]}')
        print(f'   Email: {lead["primary_email"]}')
        print(f'   Phone: {lead["primary_phone"]}')
        print(f'   Validation: {lead["validation_score"]:.3f}')
        print(f'   Issues: {lead.get("validation_issues", [])}')
        print()
else:
    print('❌ No clean leads passed strict validation')

print('Enhanced restaurant scraping with strict validation completed!')