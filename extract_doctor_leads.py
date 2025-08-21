#!/usr/bin/env python3
"""
Extract Doctor Leads from Collected HTML Data
"""

import json
import re
import csv
import os
from datetime import datetime

def extract_leads_from_html():
    """Extract doctor contact information from the HTML data we collected"""
    
    print("🏥 EXTRACTING DOCTOR LEADS FROM COLLECTED HTML DATA")
    print("=" * 60)
    
    try:
        # Read the HTML data we collected
        html_file = "output/execute_bing_search.json"
        
        if not os.path.exists(html_file):
            print("❌ HTML data file not found")
            return False
            
        print(f"📂 Reading HTML data from: {html_file}")
        
        with open(html_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        html_content = data.get('html', '')
        print(f"📊 HTML content length: {len(html_content):,} characters")
        
        if not html_content:
            print("❌ No HTML content found")
            return False
        
        # Extract potential doctor/medical leads using regex patterns
        leads = []
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = set(re.findall(email_pattern, html_content))
        
        # Phone patterns
        phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
        phones = set(re.findall(phone_pattern, html_content))
        
        # Medical-related keywords for context
        medical_keywords = [
            'doctor', 'physician', 'md', 'dr.', 'medical', 'clinic', 'practice', 
            'hospital', 'healthcare', 'dentist', 'dds', 'cardiology', 'dermatology',
            'pediatric', 'surgery', 'orthopedic', 'neurology', 'psychiatry'
        ]
        
        print(f"📧 Found {len(emails)} email addresses")
        print(f"📞 Found {len(phones)} phone numbers")
        
        # Look for medical directory listings
        directory_patterns = [
            r'<h3[^>]*>(.*?(?:dr\.?|doctor|physician|md).*?)</h3>',
            r'<title[^>]*>(.*?(?:doctor|physician|medical).*?)</title>',
            r'<a[^>]*href[^>]*>(.*?(?:contact|email|phone).*?)</a>'
        ]
        
        potential_listings = []
        for pattern in directory_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            potential_listings.extend(matches)
        
        print(f"🔍 Found {len(potential_listings)} potential medical listings")
        
        # Create sample leads from the data we found
        lead_count = 0
        
        # Create leads from email addresses
        for email in list(emails)[:50]:  # Limit to first 50
            if any(keyword in email.lower() for keyword in ['admin', 'no-reply', 'noreply']):
                continue
                
            # Try to extract name/practice info from surrounding context
            email_context = ""
            email_pos = html_content.find(email)
            if email_pos > 0:
                start = max(0, email_pos - 200)
                end = min(len(html_content), email_pos + 200)
                email_context = html_content[start:end]
            
            # Basic lead entry
            lead = {
                'name': extract_name_from_context(email_context, email),
                'practice': extract_practice_from_context(email_context),
                'email': email,
                'phone': extract_phone_from_context(email_context),
                'location': extract_location_from_context(email_context),
                'specialty': extract_specialty_from_context(email_context, medical_keywords),
                'website': 'bing.com',
                'source': 'Bing Medical Directory Search',
                'confidence': calculate_confidence(email, email_context, medical_keywords)
            }
            
            leads.append(lead)
            lead_count += 1
        
        # Add some phone-based leads
        for phone in list(phones)[:25]:  # Add 25 phone-based leads
            phone_context = ""
            phone_pos = html_content.find(phone)
            if phone_pos > 0:
                start = max(0, phone_pos - 200)
                end = min(len(html_content), phone_pos + 200)
                phone_context = html_content[start:end]
            
            # Skip if no medical context
            if not any(keyword in phone_context.lower() for keyword in medical_keywords):
                continue
                
            lead = {
                'name': extract_name_from_context(phone_context, phone),
                'practice': extract_practice_from_context(phone_context),
                'email': extract_email_from_context(phone_context),
                'phone': phone,
                'location': extract_location_from_context(phone_context),
                'specialty': extract_specialty_from_context(phone_context, medical_keywords),
                'website': 'bing.com',
                'source': 'Bing Medical Directory Search',
                'confidence': calculate_confidence(phone, phone_context, medical_keywords)
            }
            
            leads.append(lead)
            lead_count += 1
            
            if lead_count >= 100:  # Limit to 100 leads for demo
                break
        
        if not leads:
            print("⚠️  No medical leads extracted from HTML data")
            return False
            
        # Save leads to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"doctor_leads_extracted_{timestamp}.csv"
        
        print(f"💾 Saving {len(leads)} leads to: {csv_filename}")
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'practice', 'email', 'phone', 'location', 'specialty', 'website', 'source', 'confidence']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for lead in leads:
                writer.writerow(lead)
        
        # Generate summary report
        print("\n📊 EXTRACTION SUMMARY:")
        print(f"✅ Leads extracted: {len(leads)}")
        print(f"✅ CSV file created: {csv_filename}")
        print(f"✅ Average confidence: {sum(l['confidence'] for l in leads) / len(leads):.1f}/10")
        
        # Show sample leads
        print("\n🎯 SAMPLE LEADS:")
        for i, lead in enumerate(leads[:5]):
            print(f"\nLead {i+1}:")
            print(f"  Name: {lead['name']}")
            print(f"  Practice: {lead['practice']}")
            print(f"  Email: {lead['email']}")
            print(f"  Phone: {lead['phone']}")
            print(f"  Location: {lead['location']}")
            print(f"  Specialty: {lead['specialty']}")
            print(f"  Confidence: {lead['confidence']}/10")
        
        print(f"\n🎉 SUCCESS! {len(leads)} doctor leads extracted and saved to {csv_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to extract leads: {e}")
        import traceback
        traceback.print_exc()
        return False

def extract_name_from_context(context, identifier):
    """Extract potential doctor name from context"""
    # Look for Dr. patterns
    dr_pattern = r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    dr_match = re.search(dr_pattern, context)
    if dr_match:
        return dr_match.group(1)
    
    # Look for name patterns near email/phone
    name_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)'
    name_matches = re.findall(name_pattern, context)
    if name_matches:
        return name_matches[0]
    
    return "Unknown"

def extract_practice_from_context(context):
    """Extract practice name from context"""
    # Look for common practice patterns
    practice_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Medical|Clinic|Practice|Center|Associates))',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Cardiology|Dermatology|Pediatrics|Surgery))'
    ]
    
    for pattern in practice_patterns:
        match = re.search(pattern, context)
        if match:
            return match.group(1)
    
    return "Unknown Practice"

def extract_phone_from_context(context):
    """Extract phone from context"""
    phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
    match = re.search(phone_pattern, context)
    return match.group(1) if match else ""

def extract_email_from_context(context):
    """Extract email from context"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, context)
    return match.group(0) if match else ""

def extract_location_from_context(context):
    """Extract location from context"""
    # Look for city, state patterns
    location_pattern = r'([A-Z][a-z]+,\s*[A-Z]{2})'
    match = re.search(location_pattern, context)
    if match:
        return match.group(1)
    
    # Look for common city names
    cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'Dallas', 'San Diego', 'San Jose']
    for city in cities:
        if city.lower() in context.lower():
            return city
    
    return "Unknown Location"

def extract_specialty_from_context(context, medical_keywords):
    """Extract medical specialty from context"""
    specialties = {
        'cardiology': 'Cardiology', 'cardiologist': 'Cardiology',
        'dermatology': 'Dermatology', 'dermatologist': 'Dermatology',
        'pediatric': 'Pediatrics', 'pediatrician': 'Pediatrics',
        'surgery': 'Surgery', 'surgeon': 'Surgery',
        'orthopedic': 'Orthopedics', 'neurology': 'Neurology',
        'psychiatry': 'Psychiatry', 'dentist': 'Dentistry'
    }
    
    context_lower = context.lower()
    for keyword, specialty in specialties.items():
        if keyword in context_lower:
            return specialty
    
    return "General Practice"

def calculate_confidence(identifier, context, medical_keywords):
    """Calculate confidence score for the lead"""
    score = 5  # Base score
    
    # Check for medical keywords in context
    medical_count = sum(1 for keyword in medical_keywords if keyword in context.lower())
    score += min(medical_count, 3)  # Max 3 points
    
    # Check identifier quality
    if '@' in identifier and any(domain in identifier for domain in ['.com', '.org', '.edu']):
        score += 1
    
    if re.match(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', identifier):
        score += 1
    
    return min(score, 10)

if __name__ == "__main__":
    extract_leads_from_html()