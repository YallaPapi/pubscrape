"""
Data Validation Rules and Quality Checks

Implements comprehensive validation logic for scraped data with
configurable rules and detailed reporting.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
import validators
import hashlib


@dataclass
class ValidationError:
    """Represents a validation error"""
    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    code: str
    value: Any = None


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    score: float  # Overall quality score 0-1
    record_id: str
    validation_timestamp: str
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    @property
    def has_critical_errors(self) -> bool:
        return any(error.severity == 'error' for error in self.errors)


class ValidationRules:
    """Defines validation rules for different field types"""
    
    # Email validation patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Phone number patterns
    PHONE_PATTERNS = [
        re.compile(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'),  # US/Canada
        re.compile(r'^\+?[1-9][0-9]{7,14}$'),  # International
        re.compile(r'^\([0-9]{3}\)\s?[0-9]{3}-[0-9]{4}$'),  # (555) 123-4567
    ]
    
    # Business name patterns to avoid
    INVALID_BUSINESS_PATTERNS = [
        re.compile(r'^\s*$'),  # Empty or whitespace
        re.compile(r'^(test|example|sample)', re.IGNORECASE),
        re.compile(r'^[0-9]+$'),  # Only numbers
        re.compile(r'^[^a-zA-Z0-9]+$'),  # Only special characters
    ]
    
    # Minimum field lengths
    MIN_LENGTHS = {
        'business_name': 2,
        'contact_name': 2,
        'primary_email': 5,
        'primary_phone': 10,
        'website': 8,
    }
    
    # Maximum field lengths
    MAX_LENGTHS = {
        'business_name': 200,
        'contact_name': 100,
        'primary_email': 320,  # RFC 5321 limit
        'primary_phone': 20,
        'website': 2048,
        'source_query': 200,
    }


class DataValidator:
    """Main data validation class"""
    
    def __init__(self, rules: ValidationRules = None):
        self.rules = rules or ValidationRules()
        self.logger = logging.getLogger(__name__)
    
    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """Validate a single record"""
        record_id = record.get('lead_id', f"record_{hash(str(record))}")
        errors = []
        warnings = []
        
        # Validate required fields
        self._validate_required_fields(record, errors, warnings)
        
        # Validate field formats
        self._validate_email(record.get('primary_email'), errors, warnings)
        self._validate_phone(record.get('primary_phone'), errors, warnings)
        self._validate_website(record.get('website'), errors, warnings)
        self._validate_business_name(record.get('business_name'), errors, warnings)
        self._validate_contact_name(record.get('contact_name'), errors, warnings)
        
        # Validate field lengths
        self._validate_field_lengths(record, errors, warnings)
        
        # Validate data quality
        self._validate_data_quality(record, errors, warnings)
        
        # Calculate overall score
        score = self._calculate_validation_score(record, errors, warnings)
        
        # Determine if valid (no critical errors)
        is_valid = not any(error.severity == 'error' for error in errors)
        
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            score=score,
            record_id=record_id,
            validation_timestamp=datetime.now().isoformat()
        )
        
        self.logger.debug(f"Validation result for {record_id}: valid={is_valid}, score={score:.2f}")
        return result
    
    def _validate_required_fields(self, record: Dict, errors: List, warnings: List):
        """Validate presence of required fields"""
        required_fields = ['business_name']  # Minimum requirement
        
        for field in required_fields:
            if field not in record or not record[field] or str(record[field]).strip() == '':
                errors.append(ValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing or empty",
                    severity='error',
                    code='REQUIRED_FIELD_MISSING',
                    value=record.get(field)
                ))
        
        # Warn if no contact information
        has_email = record.get('primary_email', '').strip()
        has_phone = record.get('primary_phone', '').strip()
        
        if not has_email and not has_phone:
            warnings.append(ValidationError(
                field='contact_info',
                message="No contact information (email or phone) available",
                severity='warning',
                code='NO_CONTACT_INFO',
                value=None
            ))
    
    def _validate_email(self, email: str, errors: List, warnings: List):
        """Validate email format and deliverability"""
        if not email or str(email).strip() == '':
            return  # Optional field
        
        email = str(email).strip()
        
        # Basic format check
        if not self.rules.EMAIL_PATTERN.match(email):
            errors.append(ValidationError(
                field='primary_email',
                message=f"Invalid email format: {email}",
                severity='error',
                code='INVALID_EMAIL_FORMAT',
                value=email
            ))
            return
        
        # Advanced validation using email-validator
        try:
            validated_email = validate_email(email)
            normalized_email = validated_email.email
            
            # Check if normalization changed the email
            if normalized_email != email:
                warnings.append(ValidationError(
                    field='primary_email',
                    message=f"Email could be normalized: {email} -> {normalized_email}",
                    severity='info',
                    code='EMAIL_NORMALIZATION',
                    value={'original': email, 'normalized': normalized_email}
                ))
        
        except EmailNotValidError as e:
            errors.append(ValidationError(
                field='primary_email',
                message=f"Email validation failed: {str(e)}",
                severity='error',
                code='EMAIL_NOT_DELIVERABLE',
                value=email
            ))
    
    def _validate_phone(self, phone: str, errors: List, warnings: List):
        """Validate phone number format"""
        if not phone or str(phone).strip() == '':
            return  # Optional field
        
        phone = str(phone).strip()
        
        # Check against known patterns
        valid_format = False
        for pattern in self.rules.PHONE_PATTERNS:
            if pattern.match(phone):
                valid_format = True
                break
        
        if not valid_format:
            errors.append(ValidationError(
                field='primary_phone',
                message=f"Invalid phone format: {phone}",
                severity='error',
                code='INVALID_PHONE_FORMAT',
                value=phone
            ))
        
        # Check for obviously invalid patterns
        if re.match(r'^[0\-\(\)\s]+$', phone):  # All zeros or formatting chars
            errors.append(ValidationError(
                field='primary_phone',
                message=f"Phone appears to be placeholder: {phone}",
                severity='error',
                code='PLACEHOLDER_PHONE',
                value=phone
            ))
        
        # Check length after removing non-digits
        digits_only = re.sub(r'[^\d]', '', phone)
        if len(digits_only) < 10:
            warnings.append(ValidationError(
                field='primary_phone',
                message=f"Phone number seems too short: {phone}",
                severity='warning',
                code='SHORT_PHONE',
                value=phone
            ))
    
    def _validate_website(self, website: str, errors: List, warnings: List):
        """Validate website URL format"""
        if not website or str(website).strip() == '':
            return  # Optional field
        
        website = str(website).strip()
        
        # Add protocol if missing
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        # Validate URL format
        if not validators.url(website):
            errors.append(ValidationError(
                field='website',
                message=f"Invalid website URL: {website}",
                severity='error',
                code='INVALID_URL',
                value=website
            ))
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'localhost',
            r'127\.0\.0\.1',
            r'\.local',
            r'example\.com',
            r'test\.com',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, website, re.IGNORECASE):
                warnings.append(ValidationError(
                    field='website',
                    message=f"Website appears to be test/local: {website}",
                    severity='warning',
                    code='SUSPICIOUS_URL',
                    value=website
                ))
    
    def _validate_business_name(self, business_name: str, errors: List, warnings: List):
        """Validate business name"""
        if not business_name or str(business_name).strip() == '':
            return  # Handled by required fields check
        
        business_name = str(business_name).strip()
        
        # Check against invalid patterns
        for pattern in self.rules.INVALID_BUSINESS_PATTERNS:
            if pattern.match(business_name):
                errors.append(ValidationError(
                    field='business_name',
                    message=f"Invalid business name pattern: {business_name}",
                    severity='error',
                    code='INVALID_BUSINESS_NAME',
                    value=business_name
                ))
                return
        
        # Check for suspicious patterns
        if business_name.lower() in ['unknown', 'n/a', 'na', 'none', 'null']:
            warnings.append(ValidationError(
                field='business_name',
                message=f"Business name appears to be placeholder: {business_name}",
                severity='warning',
                code='PLACEHOLDER_BUSINESS_NAME',
                value=business_name
            ))
    
    def _validate_contact_name(self, contact_name: str, errors: List, warnings: List):
        """Validate contact person name"""
        if not contact_name or str(contact_name).strip() == '':
            return  # Optional field
        
        contact_name = str(contact_name).strip()
        
        # Check for suspicious patterns
        suspicious_names = ['admin', 'administrator', 'info', 'contact', 'support', 'webmaster']
        
        if contact_name.lower() in suspicious_names:
            warnings.append(ValidationError(
                field='contact_name',
                message=f"Contact name appears to be generic: {contact_name}",
                severity='warning',
                code='GENERIC_CONTACT_NAME',
                value=contact_name
            ))
        
        # Check for valid name pattern
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', contact_name):
            warnings.append(ValidationError(
                field='contact_name',
                message=f"Contact name contains unusual characters: {contact_name}",
                severity='warning',
                code='UNUSUAL_CONTACT_NAME',
                value=contact_name
            ))
    
    def _validate_field_lengths(self, record: Dict, errors: List, warnings: List):
        """Validate field lengths"""
        for field, value in record.items():
            if value is None:
                continue
            
            value_str = str(value)
            
            # Check minimum length
            min_length = self.rules.MIN_LENGTHS.get(field)
            if min_length and len(value_str) < min_length:
                warnings.append(ValidationError(
                    field=field,
                    message=f"Field '{field}' is shorter than recommended minimum ({min_length})",
                    severity='warning',
                    code='FIELD_TOO_SHORT',
                    value=value
                ))
            
            # Check maximum length
            max_length = self.rules.MAX_LENGTHS.get(field)
            if max_length and len(value_str) > max_length:
                errors.append(ValidationError(
                    field=field,
                    message=f"Field '{field}' exceeds maximum length ({max_length})",
                    severity='error',
                    code='FIELD_TOO_LONG',
                    value=value
                ))
    
    def _validate_data_quality(self, record: Dict, errors: List, warnings: List):
        """Validate overall data quality"""
        # Check lead score if present
        lead_score = record.get('lead_score')
        if lead_score is not None:
            try:
                score_value = float(lead_score)
                if not 0.0 <= score_value <= 1.0:
                    warnings.append(ValidationError(
                        field='lead_score',
                        message=f"Lead score outside expected range (0-1): {score_value}",
                        severity='warning',
                        code='SCORE_OUT_OF_RANGE',
                        value=lead_score
                    ))
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field='lead_score',
                    message=f"Invalid lead score format: {lead_score}",
                    severity='error',
                    code='INVALID_SCORE_FORMAT',
                    value=lead_score
                ))
        
        # Check extraction date if present
        extraction_date = record.get('extraction_date')
        if extraction_date:
            try:
                # Try to parse the date
                if isinstance(extraction_date, str):
                    datetime.fromisoformat(extraction_date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                warnings.append(ValidationError(
                    field='extraction_date',
                    message=f"Invalid extraction date format: {extraction_date}",
                    severity='warning',
                    code='INVALID_DATE_FORMAT',
                    value=extraction_date
                ))
    
    def _calculate_validation_score(self, record: Dict, errors: List, warnings: List) -> float:
        """Calculate overall validation score (0-1)"""
        base_score = 1.0
        
        # Deduct points for errors (more severe penalty)
        for error in errors:
            if error.severity == 'error':
                base_score -= 0.3
            elif error.severity == 'warning':
                base_score -= 0.1
        
        # Bonus points for data completeness
        completeness_fields = ['primary_email', 'primary_phone', 'website', 'contact_name']
        filled_fields = sum(1 for field in completeness_fields 
                           if record.get(field) and str(record[field]).strip())
        completeness_bonus = (filled_fields / len(completeness_fields)) * 0.2
        
        final_score = max(0.0, min(1.0, base_score + completeness_bonus))
        return round(final_score, 3)
    
    def validate_batch(self, records: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate multiple records"""
        results = []
        for record in records:
            result = self.validate_record(record)
            results.append(result)
        
        self.logger.info(f"Batch validation completed: {len(results)} records processed")
        return results
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for validation results"""
        total_records = len(results)
        if total_records == 0:
            return {
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0,
                'validation_rate': 0.0,
                'average_score': 0.0,
                'total_errors': 0,
                'total_warnings': 0,
                'common_errors': []
            }
        
        valid_records = sum(1 for r in results if r.is_valid)
        invalid_records = total_records - valid_records
        
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        
        average_score = sum(r.score for r in results) / total_records
        
        # Find common error codes
        error_codes = {}
        for result in results:
            for error in result.errors:
                error_codes[error.code] = error_codes.get(error.code, 0) + 1
        
        common_errors = sorted(error_codes.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': invalid_records,
            'validation_rate': valid_records / total_records,
            'average_score': round(average_score, 3),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'common_errors': common_errors,
            'timestamp': datetime.now().isoformat()
        }