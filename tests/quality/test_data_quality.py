"""
Data quality verification tests for the scraper system.

Tests data accuracy, completeness, consistency, validity,
and overall quality metrics across the extraction pipeline.
"""

import pytest
import re
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import pandas as pd
from email_validator import validate_email, EmailNotValidError


@dataclass
class QualityMetrics:
    """Data quality metrics container"""
    completeness_score: float
    accuracy_score: float
    validity_score: float
    consistency_score: float
    uniqueness_score: float
    overall_score: float
    issues: List[str]
    recommendations: List[str]


class DataQualityValidator:
    """Data quality validation utility"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_patterns = [
            re.compile(r'^\(\d{3}\) \d{3}-\d{4}$'),  # (123) 456-7890
            re.compile(r'^\d{3}-\d{3}-\d{4}$'),      # 123-456-7890
            re.compile(r'^\d{10}$'),                 # 1234567890
            re.compile(r'^\+1\d{10}$'),              # +11234567890
        ]
        self.url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
        
        # Common data quality issues
        self.spam_indicators = [
            'noreply', 'no-reply', 'donotreply', 'do-not-reply',
            'mailer-daemon', 'postmaster', 'webmaster',
            'test', 'example', 'sample', 'demo'
        ]
        
        self.disposable_domains = [
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'temp-mail.org', 'throwaway.email', 'example.com'
        ]
    
    def validate_email_quality(self, email: str) -> Dict[str, Any]:
        """Validate email quality and extract quality metrics"""
        result = {
            "email": email,
            "is_valid_format": False,
            "is_deliverable": False,
            "is_business_email": False,
            "is_disposable": False,
            "is_spam_trap": False,
            "quality_score": 0.0,
            "issues": [],
            "domain_info": {}
        }
        
        # Basic format validation
        if self.email_pattern.match(email):
            result["is_valid_format"] = True
            result["quality_score"] += 0.2
        else:
            result["issues"].append("Invalid email format")
            return result  # Can't validate further if format is wrong
        
        # Extract domain information
        local_part, domain = email.split('@', 1)
        result["domain_info"] = {
            "domain": domain,
            "local_part": local_part,
            "tld": domain.split('.')[-1] if '.' in domain else ""
        }
        
        # Check for disposable email domains
        if domain.lower() in self.disposable_domains:
            result["is_disposable"] = True
            result["issues"].append("Disposable email domain")
        else:
            result["quality_score"] += 0.2
        
        # Check for spam indicators
        email_lower = email.lower()
        spam_found = any(indicator in email_lower for indicator in self.spam_indicators)
        if spam_found:
            result["is_spam_trap"] = True
            result["issues"].append("Contains spam indicators")
        else:
            result["quality_score"] += 0.2
        
        # Business email detection (has proper domain, not free email)
        free_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']
        if domain.lower() not in free_domains and not result["is_disposable"]:
            result["is_business_email"] = True
            result["quality_score"] += 0.3
        else:
            result["issues"].append("Not a business email domain")
        
        # Deliverability check (simplified)
        if len(local_part) >= 1 and len(domain) >= 4 and '.' in domain:
            result["is_deliverable"] = True
            result["quality_score"] += 0.1
        
        return result
    
    def validate_phone_quality(self, phone: str) -> Dict[str, Any]:
        """Validate phone number quality"""
        result = {
            "phone": phone,
            "is_valid_format": False,
            "is_mobile": False,
            "is_toll_free": False,
            "country_code": None,
            "area_code": None,
            "quality_score": 0.0,
            "issues": []
        }
        
        # Clean phone number
        cleaned_phone = re.sub(r'[^\d+]', '', phone)
        
        # Check against known patterns
        for pattern in self.phone_patterns:
            if pattern.match(phone):
                result["is_valid_format"] = True
                result["quality_score"] += 0.4
                break
        
        if not result["is_valid_format"]:
            result["issues"].append("Invalid phone format")
            return result
        
        # Extract area code (US format)
        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) >= 10:
            if digits_only.startswith('1') and len(digits_only) == 11:
                result["country_code"] = "1"
                result["area_code"] = digits_only[1:4]
            elif len(digits_only) == 10:
                result["area_code"] = digits_only[:3]
            
            result["quality_score"] += 0.2
        
        # Check for toll-free numbers
        toll_free_codes = ['800', '833', '844', '855', '866', '877', '888']
        if result["area_code"] in toll_free_codes:
            result["is_toll_free"] = True
            result["quality_score"] += 0.2
        
        # Check for mobile indicators (simplified)
        # This is a simplified check - real implementation would use carrier lookup
        if len(digits_only) == 10 and result["area_code"] not in toll_free_codes:
            result["is_mobile"] = True
            result["quality_score"] += 0.2
        
        return result
    
    def validate_url_quality(self, url: str) -> Dict[str, Any]:
        """Validate URL quality"""
        result = {
            "url": url,
            "is_valid_format": False,
            "is_accessible": None,  # Would require actual HTTP request
            "has_ssl": False,
            "domain_age": None,  # Would require domain lookup
            "quality_score": 0.0,
            "issues": [],
            "parsed_url": {}
        }
        
        try:
            parsed = urlparse(url)
            result["parsed_url"] = {
                "scheme": parsed.scheme,
                "domain": parsed.netloc,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment
            }
            
            if parsed.scheme and parsed.netloc:
                result["is_valid_format"] = True
                result["quality_score"] += 0.3
            else:
                result["issues"].append("Invalid URL format")
                return result
            
            # Check for HTTPS
            if parsed.scheme == 'https':
                result["has_ssl"] = True
                result["quality_score"] += 0.3
            else:
                result["issues"].append("No SSL/HTTPS")
            
            # Check domain validity
            if '.' in parsed.netloc and len(parsed.netloc) >= 4:
                result["quality_score"] += 0.2
            else:
                result["issues"].append("Invalid domain")
            
            # Check for suspicious patterns
            suspicious_patterns = ['bit.ly', 'tinyurl', 'short.link', 'click.here']
            if any(pattern in url.lower() for pattern in suspicious_patterns):
                result["issues"].append("Suspicious URL shortener")
            else:
                result["quality_score"] += 0.2
                
        except Exception as e:
            result["issues"].append(f"URL parsing error: {str(e)}")
        
        return result
    
    def validate_business_data_completeness(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate completeness of business data"""
        required_fields = ['name', 'email', 'phone', 'address', 'website']
        optional_fields = ['description', 'hours', 'services', 'social_media']
        
        result = {
            "total_fields": len(required_fields) + len(optional_fields),
            "required_fields_present": 0,
            "optional_fields_present": 0,
            "completeness_score": 0.0,
            "missing_required": [],
            "missing_optional": [],
            "empty_fields": [],
            "quality_issues": []
        }
        
        # Check required fields
        for field in required_fields:
            if field in business_data and business_data[field]:
                result["required_fields_present"] += 1
            else:
                result["missing_required"].append(field)
        
        # Check optional fields
        for field in optional_fields:
            if field in business_data and business_data[field]:
                result["optional_fields_present"] += 1
            else:
                result["missing_optional"].append(field)
        
        # Check for empty or placeholder values
        for field, value in business_data.items():
            if value in ['', 'N/A', 'TBD', 'Unknown', None]:
                result["empty_fields"].append(field)
        
        # Calculate completeness score
        required_score = result["required_fields_present"] / len(required_fields)
        optional_score = result["optional_fields_present"] / len(optional_fields)
        result["completeness_score"] = (required_score * 0.8) + (optional_score * 0.2)
        
        # Generate quality issues
        if result["missing_required"]:
            result["quality_issues"].append(f"Missing required fields: {result['missing_required']}")
        
        if len(result["empty_fields"]) > 2:
            result["quality_issues"].append(f"Too many empty fields: {result['empty_fields']}")
        
        return result
    
    def detect_duplicate_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect duplicate records in dataset"""
        result = {
            "total_records": len(records),
            "unique_records": 0,
            "duplicate_groups": [],
            "duplication_rate": 0.0,
            "duplicate_fields": {},
            "recommendations": []
        }
        
        if not records:
            return result
        
        # Group records by various keys
        email_groups = {}
        phone_groups = {}
        name_groups = {}
        
        for i, record in enumerate(records):
            # Group by email
            email = record.get('email', '').lower().strip()
            if email:
                if email not in email_groups:
                    email_groups[email] = []
                email_groups[email].append(i)
            
            # Group by phone
            phone = re.sub(r'\D', '', record.get('phone', ''))
            if phone:
                if phone not in phone_groups:
                    phone_groups[phone] = []
                phone_groups[phone].append(i)
            
            # Group by business name (normalized)
            name = record.get('name', '').lower().strip()
            name = re.sub(r'[^a-z0-9\s]', '', name)  # Remove special chars
            if name:
                if name not in name_groups:
                    name_groups[name] = []
                name_groups[name].append(i)
        
        # Find duplicates
        email_duplicates = {k: v for k, v in email_groups.items() if len(v) > 1}
        phone_duplicates = {k: v for k, v in phone_groups.items() if len(v) > 1}
        name_duplicates = {k: v for k, v in name_groups.items() if len(v) > 1}
        
        result["duplicate_fields"] = {
            "email": len(email_duplicates),
            "phone": len(phone_duplicates),
            "name": len(name_duplicates)
        }
        
        # Create duplicate groups
        all_duplicate_indices = set()
        
        for field_name, duplicates in [("email", email_duplicates), 
                                      ("phone", phone_duplicates), 
                                      ("name", name_duplicates)]:
            for key, indices in duplicates.items():
                if len(indices) > 1:
                    result["duplicate_groups"].append({
                        "field": field_name,
                        "value": key,
                        "record_indices": indices,
                        "record_count": len(indices)
                    })
                    all_duplicate_indices.update(indices)
        
        result["unique_records"] = len(records) - len(all_duplicate_indices)
        result["duplication_rate"] = len(all_duplicate_indices) / len(records)
        
        # Generate recommendations
        if result["duplication_rate"] > 0.1:
            result["recommendations"].append("High duplication rate detected - implement deduplication")
        
        if result["duplicate_fields"]["email"] > 0:
            result["recommendations"].append("Email duplicates found - merge records with same email")
        
        return result
    
    def calculate_overall_quality(self, dataset: List[Dict[str, Any]]) -> QualityMetrics:
        """Calculate overall data quality metrics"""
        if not dataset:
            return QualityMetrics(0, 0, 0, 0, 0, 0, ["Empty dataset"], ["Add data to analyze"])
        
        # Initialize metrics
        total_completeness = 0
        total_accuracy = 0
        total_validity = 0
        valid_emails = 0
        valid_phones = 0
        valid_urls = 0
        
        issues = []
        recommendations = []
        
        # Analyze each record
        for record in dataset:
            # Completeness check
            completeness_result = self.validate_business_data_completeness(record)
            total_completeness += completeness_result["completeness_score"]
            
            # Email validation
            if 'email' in record and record['email']:
                email_result = self.validate_email_quality(record['email'])
                total_validity += email_result["quality_score"]
                if email_result["is_valid_format"]:
                    valid_emails += 1
            
            # Phone validation
            if 'phone' in record and record['phone']:
                phone_result = self.validate_phone_quality(record['phone'])
                total_validity += phone_result["quality_score"]
                if phone_result["is_valid_format"]:
                    valid_phones += 1
            
            # URL validation
            if 'website' in record and record['website']:
                url_result = self.validate_url_quality(record['website'])
                total_validity += url_result["quality_score"]
                if url_result["is_valid_format"]:
                    valid_urls += 1
        
        # Calculate averages
        completeness_score = total_completeness / len(dataset)
        validity_score = total_validity / (len(dataset) * 3)  # 3 fields checked
        
        # Accuracy score (simplified - would need reference data for real accuracy)
        accuracy_score = 0.8  # Assume 80% accuracy without reference
        
        # Uniqueness check
        duplicate_result = self.detect_duplicate_records(dataset)
        uniqueness_score = 1.0 - duplicate_result["duplication_rate"]
        
        # Consistency score (check for consistent formats)
        consistency_score = 0.9  # Simplified
        
        # Overall score (weighted average)
        overall_score = (
            completeness_score * 0.25 +
            accuracy_score * 0.25 +
            validity_score * 0.25 +
            uniqueness_score * 0.15 +
            consistency_score * 0.10
        )
        
        # Generate issues and recommendations
        if completeness_score < 0.7:
            issues.append("Low data completeness")
            recommendations.append("Improve data collection to capture more fields")
        
        if validity_score < 0.6:
            issues.append("Many invalid data formats")
            recommendations.append("Implement better data validation during collection")
        
        if uniqueness_score < 0.9:
            issues.append("High duplication rate")
            recommendations.append("Implement deduplication process")
        
        return QualityMetrics(
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            validity_score=validity_score,
            consistency_score=consistency_score,
            uniqueness_score=uniqueness_score,
            overall_score=overall_score,
            issues=issues,
            recommendations=recommendations
        )


@pytest.mark.quality
class TestDataQualityValidation:
    """Test data quality validation capabilities"""
    
    @pytest.fixture
    def quality_validator(self):
        """Create data quality validator instance"""
        return DataQualityValidator()
    
    @pytest.fixture
    def sample_business_data(self):
        """Sample business data for testing"""
        return {
            "complete_record": {
                "name": "Chicago Premier Medical Associates",
                "email": "info@chicagopremiermedicine.com",
                "phone": "(312) 555-0123",
                "address": "123 Michigan Avenue, Chicago, IL 60601",
                "website": "https://chicagopremiermedicine.com",
                "description": "Comprehensive healthcare services",
                "hours": "Mon-Fri 8AM-6PM",
                "services": ["Primary Care", "Preventive Medicine"]
            },
            "incomplete_record": {
                "name": "Incomplete Business",
                "email": "contact@incomplete.com",
                "phone": "",
                "address": "N/A",
                "website": None
            },
            "poor_quality_record": {
                "name": "Bad Data Business",
                "email": "invalid-email",
                "phone": "123",
                "address": "TBD",
                "website": "not-a-url"
            }
        }
    
    def test_email_quality_validation(self, quality_validator):
        """Test email quality validation"""
        # Test valid business email
        valid_result = quality_validator.validate_email_quality("contact@business.com")
        assert valid_result["is_valid_format"]
        assert valid_result["is_business_email"]
        assert not valid_result["is_disposable"]
        assert valid_result["quality_score"] >= 0.8
        
        # Test invalid email
        invalid_result = quality_validator.validate_email_quality("invalid-email")
        assert not invalid_result["is_valid_format"]
        assert invalid_result["quality_score"] == 0.0
        assert len(invalid_result["issues"]) > 0
        
        # Test disposable email
        disposable_result = quality_validator.validate_email_quality("test@10minutemail.com")
        assert disposable_result["is_valid_format"]
        assert disposable_result["is_disposable"]
        assert "Disposable email domain" in disposable_result["issues"]
        
        # Test spam email
        spam_result = quality_validator.validate_email_quality("noreply@example.com")
        assert spam_result["is_spam_trap"]
        assert "spam indicators" in str(spam_result["issues"]).lower()
    
    def test_phone_quality_validation(self, quality_validator):
        """Test phone number quality validation"""
        # Test valid formats
        valid_formats = [
            "(312) 555-0123",
            "312-555-0123",
            "3125550123",
            "+13125550123"
        ]
        
        for phone in valid_formats:
            result = quality_validator.validate_phone_quality(phone)
            assert result["is_valid_format"], f"Failed for {phone}"
            assert result["quality_score"] > 0.4
        
        # Test invalid format
        invalid_result = quality_validator.validate_phone_quality("123")
        assert not invalid_result["is_valid_format"]
        assert "Invalid phone format" in invalid_result["issues"]
        
        # Test toll-free number
        tollfree_result = quality_validator.validate_phone_quality("(800) 555-0123")
        assert tollfree_result["is_toll_free"]
        assert tollfree_result["area_code"] == "800"
    
    def test_url_quality_validation(self, quality_validator):
        """Test URL quality validation"""
        # Test valid HTTPS URL
        valid_result = quality_validator.validate_url_quality("https://business.com")
        assert valid_result["is_valid_format"]
        assert valid_result["has_ssl"]
        assert valid_result["quality_score"] >= 0.8
        
        # Test HTTP URL (lower quality)
        http_result = quality_validator.validate_url_quality("http://business.com")
        assert http_result["is_valid_format"]
        assert not http_result["has_ssl"]
        assert "No SSL/HTTPS" in http_result["issues"]
        
        # Test invalid URL
        invalid_result = quality_validator.validate_url_quality("not-a-url")
        assert not invalid_result["is_valid_format"]
        assert len(invalid_result["issues"]) > 0
        
        # Test suspicious URL
        suspicious_result = quality_validator.validate_url_quality("https://bit.ly/short")
        assert "Suspicious URL shortener" in suspicious_result["issues"]
    
    def test_business_data_completeness(self, quality_validator, sample_business_data):
        """Test business data completeness validation"""
        # Test complete record
        complete_result = quality_validator.validate_business_data_completeness(
            sample_business_data["complete_record"]
        )
        assert complete_result["completeness_score"] >= 0.9
        assert complete_result["required_fields_present"] == 5
        assert len(complete_result["missing_required"]) == 0
        
        # Test incomplete record
        incomplete_result = quality_validator.validate_business_data_completeness(
            sample_business_data["incomplete_record"]
        )
        assert incomplete_result["completeness_score"] < 0.7
        assert len(incomplete_result["missing_required"]) > 0
        assert len(incomplete_result["empty_fields"]) > 0
        
        # Test poor quality record
        poor_result = quality_validator.validate_business_data_completeness(
            sample_business_data["poor_quality_record"]
        )
        assert poor_result["completeness_score"] < 0.5
        assert len(poor_result["quality_issues"]) > 0
    
    def test_duplicate_detection(self, quality_validator):
        """Test duplicate record detection"""
        records_with_duplicates = [
            {"name": "Business A", "email": "contact@businessa.com", "phone": "(312) 555-0001"},
            {"name": "Business B", "email": "info@businessb.com", "phone": "(312) 555-0002"},
            {"name": "Business A", "email": "contact@businessa.com", "phone": "(312) 555-0001"},  # Duplicate
            {"name": "Business C", "email": "hello@businessc.com", "phone": "(312) 555-0002"},  # Phone duplicate
            {"name": "Different Name", "email": "contact@businessa.com", "phone": "(312) 555-0003"},  # Email duplicate
        ]
        
        result = quality_validator.detect_duplicate_records(records_with_duplicates)
        
        assert result["total_records"] == 5
        assert result["duplication_rate"] > 0.4  # High duplication
        assert result["duplicate_fields"]["email"] > 0
        assert result["duplicate_fields"]["phone"] > 0
        assert len(result["duplicate_groups"]) > 0
        assert len(result["recommendations"]) > 0
    
    def test_overall_quality_metrics(self, quality_validator, sample_business_data):
        """Test overall quality metrics calculation"""
        # Test with high-quality dataset
        high_quality_dataset = [sample_business_data["complete_record"]] * 3
        
        high_quality_metrics = quality_validator.calculate_overall_quality(high_quality_dataset)
        
        assert high_quality_metrics.overall_score >= 0.8
        assert high_quality_metrics.completeness_score >= 0.9
        assert high_quality_metrics.validity_score >= 0.7
        assert high_quality_metrics.uniqueness_score == 0.0  # All identical records
        
        # Test with mixed quality dataset
        mixed_dataset = [
            sample_business_data["complete_record"],
            sample_business_data["incomplete_record"],
            sample_business_data["poor_quality_record"]
        ]
        
        mixed_metrics = quality_validator.calculate_overall_quality(mixed_dataset)
        
        assert mixed_metrics.overall_score < high_quality_metrics.overall_score
        assert len(mixed_metrics.issues) > 0
        assert len(mixed_metrics.recommendations) > 0
    
    def test_empty_dataset_handling(self, quality_validator):
        """Test handling of empty datasets"""
        empty_metrics = quality_validator.calculate_overall_quality([])
        
        assert empty_metrics.overall_score == 0
        assert "Empty dataset" in empty_metrics.issues
        assert "Add data to analyze" in empty_metrics.recommendations


@pytest.mark.quality
class TestDataConsistency:
    """Test data consistency across different dimensions"""
    
    @pytest.fixture
    def consistency_validator(self):
        return DataQualityValidator()
    
    def test_field_format_consistency(self, consistency_validator):
        """Test consistency of field formats across records"""
        records = [
            {"phone": "(312) 555-0001", "email": "contact@business1.com"},
            {"phone": "(312) 555-0002", "email": "info@business2.com"},
            {"phone": "3125550003", "email": "hello@business3.com"},  # Different format
            {"phone": "(312) 555-0004", "email": "CONTACT@BUSINESS4.COM"},  # Different case
        ]
        
        # Analyze phone format consistency
        phone_formats = {}
        for record in records:
            phone = record.get("phone", "")
            # Categorize format
            if "(" in phone and ")" in phone and "-" in phone:
                format_type = "formatted"
            elif phone.isdigit():
                format_type = "digits_only"
            else:
                format_type = "other"
            
            phone_formats[format_type] = phone_formats.get(format_type, 0) + 1
        
        # Check consistency
        most_common_format = max(phone_formats, key=phone_formats.get)
        consistency_rate = phone_formats[most_common_format] / len(records)
        
        assert consistency_rate >= 0.5  # At least 50% should use same format
        
        # For this test data, "formatted" should be most common
        assert most_common_format == "formatted"
        assert consistency_rate == 0.75  # 3 out of 4 records
    
    def test_domain_consistency(self, consistency_validator):
        """Test email domain consistency for business verification"""
        business_data = {
            "name": "Example Business Corp",
            "website": "https://examplebusiness.com",
            "email": "contact@examplebusiness.com",
            "secondary_email": "support@examplebusiness.com"
        }
        
        # Extract domains
        website_domain = business_data["website"].replace("https://", "").replace("http://", "")
        email_domain = business_data["email"].split("@")[1]
        secondary_email_domain = business_data["secondary_email"].split("@")[1]
        
        # Check consistency
        assert website_domain == email_domain  # Should match
        assert email_domain == secondary_email_domain  # Should match
        
        # Test inconsistent case
        inconsistent_data = {
            "name": "Another Business",
            "website": "https://anotherbusiness.com",
            "email": "contact@differentdomain.com"  # Inconsistent domain
        }
        
        website_domain_2 = inconsistent_data["website"].replace("https://", "")
        email_domain_2 = inconsistent_data["email"].split("@")[1]
        
        assert website_domain_2 != email_domain_2  # Should be different
    
    def test_geographic_consistency(self):
        """Test geographic data consistency"""
        business_data = {
            "name": "Chicago Medical Center",
            "address": "123 Main St, Chicago, IL 60601",
            "phone": "(312) 555-0123",  # Chicago area code
            "service_area": "Chicago, IL"
        }
        
        # Extract geographic indicators
        address_city = "Chicago" in business_data["address"]
        phone_area_chicago = business_data["phone"].startswith("(312)")  # Chicago area code
        service_area_chicago = "Chicago" in business_data["service_area"]
        name_chicago = "Chicago" in business_data["name"]
        
        # Check consistency
        geographic_indicators = [address_city, phone_area_chicago, service_area_chicago, name_chicago]
        consistency_score = sum(geographic_indicators) / len(geographic_indicators)
        
        assert consistency_score >= 0.75  # At least 75% consistency
        assert address_city and phone_area_chicago  # Critical fields should match


@pytest.mark.quality
class TestDataAccuracy:
    """Test data accuracy validation"""
    
    def test_email_deliverability_indicators(self):
        """Test email deliverability indicators"""
        # Test emails with good deliverability indicators
        good_emails = [
            "info@established-business.com",
            "contact@company.org",
            "sales@business.net"
        ]
        
        # Test emails with poor deliverability indicators
        poor_emails = [
            "test@example.com",  # Example domain
            "noreply@business.com",  # No-reply address
            "a@b.co",  # Too short
            "user@newdomain.xyz"  # Uncommon TLD
        ]
        
        validator = DataQualityValidator()
        
        # Good emails should score higher
        for email in good_emails:
            result = validator.validate_email_quality(email)
            assert result["quality_score"] >= 0.6  # Should be reasonably good
        
        # Poor emails should score lower
        for email in poor_emails:
            result = validator.validate_email_quality(email)
            assert result["quality_score"] <= 0.8  # Should have some issues
    
    def test_business_hours_validation(self):
        """Test business hours data validation"""
        valid_hours_formats = [
            "Mon-Fri 9AM-5PM",
            "Monday-Friday 9:00AM-5:00PM",
            "M-F 9-17",
            "24/7",
            "Mon-Thu 8AM-6PM, Fri 8AM-4PM"
        ]
        
        invalid_hours_formats = [
            "Sometimes open",
            "Call for hours",
            "9-5",  # No days specified
            "Open late"
        ]
        
        # Simple hours validation regex
        hours_pattern = re.compile(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun|\d+AM|\d+PM|24/7)', re.IGNORECASE)
        
        # Valid formats should match pattern
        for hours in valid_hours_formats:
            assert hours_pattern.search(hours), f"Failed to validate: {hours}"
        
        # Invalid formats should not match or should be flagged
        invalid_count = 0
        for hours in invalid_hours_formats:
            if not hours_pattern.search(hours):
                invalid_count += 1
        
        assert invalid_count >= len(invalid_hours_formats) * 0.5  # At least half should be caught
    
    def test_address_validation(self):
        """Test address validation"""
        valid_addresses = [
            "123 Main Street, Chicago, IL 60601",
            "456 Oak Ave, Suite 200, Houston, TX 77002",
            "789 Broadway, New York, NY 10003"
        ]
        
        invalid_addresses = [
            "123",  # Too short
            "Somewhere in the city",  # Too vague
            "TBD",  # Placeholder
            "N/A"  # Placeholder
        ]
        
        # Simple address validation
        def validate_address(address):
            if len(address) < 10:
                return False
            if address.upper() in ['TBD', 'N/A', 'UNKNOWN']:
                return False
            # Should contain numbers (street number) and letters
            has_numbers = any(c.isdigit() for c in address)
            has_letters = any(c.isalpha() for c in address)
            return has_numbers and has_letters
        
        # Valid addresses should pass
        for address in valid_addresses:
            assert validate_address(address), f"Failed to validate: {address}"
        
        # Invalid addresses should fail
        for address in invalid_addresses:
            assert not validate_address(address), f"Should have failed: {address}"


@pytest.mark.quality
class TestDataQualityReporting:
    """Test data quality reporting and metrics"""
    
    @pytest.fixture
    def sample_campaign_data(self):
        """Sample campaign data for quality reporting"""
        return [
            {
                "name": "Premier Medical Group",
                "email": "info@premiermedical.com",
                "phone": "(312) 555-0101",
                "address": "100 N Michigan Ave, Chicago, IL 60601",
                "website": "https://premiermedical.com",
                "extraction_timestamp": "2024-01-15T10:30:00Z",
                "source_url": "https://bing.com/search?q=doctors+chicago",
                "confidence_score": 0.95
            },
            {
                "name": "Quick Care Clinic",
                "email": "contact@quickcare.org",
                "phone": "312-555-0102",  # Different format
                "address": "200 W Madison St, Chicago, IL 60606",
                "website": "http://quickcare.org",  # No SSL
                "extraction_timestamp": "2024-01-15T10:31:00Z",
                "source_url": "https://bing.com/search?q=doctors+chicago",
                "confidence_score": 0.88
            },
            {
                "name": "Downtown Health",
                "email": "noreply@downtown-health.com",  # No-reply email
                "phone": "",  # Missing phone
                "address": "TBD",  # Placeholder address
                "website": "https://downtown-health.com",
                "extraction_timestamp": "2024-01-15T10:32:00Z",
                "source_url": "https://bing.com/search?q=doctors+chicago",
                "confidence_score": 0.62
            }
        ]
    
    def test_quality_metrics_calculation(self, sample_campaign_data):
        """Test calculation of quality metrics for campaign data"""
        validator = DataQualityValidator()
        metrics = validator.calculate_overall_quality(sample_campaign_data)
        
        # Validate metric ranges
        assert 0 <= metrics.completeness_score <= 1
        assert 0 <= metrics.accuracy_score <= 1
        assert 0 <= metrics.validity_score <= 1
        assert 0 <= metrics.consistency_score <= 1
        assert 0 <= metrics.uniqueness_score <= 1
        assert 0 <= metrics.overall_score <= 1
        
        # Should identify quality issues
        assert len(metrics.issues) > 0  # Should find some issues
        assert len(metrics.recommendations) > 0  # Should provide recommendations
        
        # Overall score should reflect mixed quality
        assert 0.4 <= metrics.overall_score <= 0.8  # Mixed quality dataset
    
    def test_quality_trend_analysis(self):
        """Test quality trend analysis over time"""
        # Simulate quality metrics over time
        daily_metrics = [
            {"date": "2024-01-01", "overall_score": 0.85, "records": 100},
            {"date": "2024-01-02", "overall_score": 0.82, "records": 120},
            {"date": "2024-01-03", "overall_score": 0.78, "records": 150},  # Declining
            {"date": "2024-01-04", "overall_score": 0.75, "records": 180},
            {"date": "2024-01-05", "overall_score": 0.73, "records": 200}
        ]
        
        # Calculate trend
        scores = [metric["overall_score"] for metric in daily_metrics]
        
        # Check for declining quality
        is_declining = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
        assert is_declining  # Quality is consistently declining
        
        # Calculate quality change rate
        initial_score = scores[0]
        final_score = scores[-1]
        quality_change = (final_score - initial_score) / initial_score
        
        assert quality_change < -0.1  # Quality declined by more than 10%
        
        # This should trigger alerts
        quality_alert = quality_change < -0.05  # 5% decline threshold
        assert quality_alert
    
    def test_field_specific_quality_analysis(self, sample_campaign_data):
        """Test field-specific quality analysis"""
        validator = DataQualityValidator()
        
        field_quality = {
            "email": [],
            "phone": [],
            "website": [],
            "address": []
        }
        
        # Analyze each field across all records
        for record in sample_campaign_data:
            # Email quality
            if record.get("email"):
                email_result = validator.validate_email_quality(record["email"])
                field_quality["email"].append(email_result["quality_score"])
            
            # Phone quality
            if record.get("phone"):
                phone_result = validator.validate_phone_quality(record["phone"])
                field_quality["phone"].append(phone_result["quality_score"])
            
            # Website quality
            if record.get("website"):
                url_result = validator.validate_url_quality(record["website"])
                field_quality["website"].append(url_result["quality_score"])
        
        # Calculate average quality per field
        field_averages = {}
        for field, scores in field_quality.items():
            if scores:
                field_averages[field] = sum(scores) / len(scores)
            else:
                field_averages[field] = 0.0
        
        # Email should have lower quality (due to noreply email)
        assert field_averages["email"] < 0.9
        
        # Website should have medium quality (due to HTTP site)
        assert 0.6 <= field_averages["website"] <= 0.9
        
        # Identify worst performing field
        worst_field = min(field_averages, key=field_averages.get)
        worst_score = field_averages[worst_field]
        
        # Generate field-specific recommendations
        recommendations = []
        for field, score in field_averages.items():
            if score < 0.7:
                recommendations.append(f"Improve {field} data quality (current: {score:.2f})")
        
        assert len(recommendations) > 0  # Should have recommendations
        assert worst_score < 0.8  # Worst field should be clearly problematic
    
    def test_quality_benchmark_comparison(self):
        """Test quality metrics against industry benchmarks"""
        # Industry benchmarks (example values)
        benchmarks = {
            "healthcare": {
                "completeness": 0.85,
                "accuracy": 0.90,
                "validity": 0.80,
                "uniqueness": 0.95
            },
            "legal": {
                "completeness": 0.90,
                "accuracy": 0.95,
                "validity": 0.85,
                "uniqueness": 0.98
            },
            "general": {
                "completeness": 0.75,
                "accuracy": 0.80,
                "validity": 0.70,
                "uniqueness": 0.90
            }
        }
        
        # Current metrics (simulated)
        current_metrics = {
            "completeness": 0.78,
            "accuracy": 0.82,
            "validity": 0.71,
            "uniqueness": 0.88
        }
        
        industry = "healthcare"
        benchmark = benchmarks[industry]
        
        # Compare against benchmark
        comparison = {}
        for metric, value in current_metrics.items():
            benchmark_value = benchmark[metric]
            comparison[metric] = {
                "current": value,
                "benchmark": benchmark_value,
                "difference": value - benchmark_value,
                "meets_benchmark": value >= benchmark_value
            }
        
        # Check which metrics meet benchmarks
        meets_benchmark_count = sum(
            1 for comp in comparison.values() 
            if comp["meets_benchmark"]
        )
        
        # Should meet at least half the benchmarks
        assert meets_benchmark_count >= len(comparison) / 2
        
        # Generate benchmark report
        failing_metrics = [
            metric for metric, comp in comparison.items()
            if not comp["meets_benchmark"]
        ]
        
        if failing_metrics:
            # Should identify areas for improvement
            assert len(failing_metrics) > 0
            # Completeness is likely failing for healthcare
            assert "completeness" in failing_metrics or "validity" in failing_metrics
