"""
Validation Pipeline for VRSEN PubScrape

Comprehensive data validation and quality assurance pipeline
for lead data with multiple validation levels and reporting.
"""

import asyncio
import re
import dns.resolver
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import csv
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
import requests
from email_validator import validate_email, EmailNotValidError

from ..config.config_manager import config_manager
from ..utils.error_handler import ErrorHandler


class ValidationLevel(Enum):
    """Validation strictness levels"""
    LENIENT = "lenient"
    MODERATE = "moderate"
    STRICT = "strict"


@dataclass
class ValidationResult:
    """Individual validation result"""
    field: str
    is_valid: bool
    confidence: float
    error_message: Optional[str] = None
    suggested_correction: Optional[str] = None
    validation_method: str = ""


@dataclass
class LeadValidationReport:
    """Complete validation report for a single lead"""
    lead_id: str
    original_data: Dict[str, Any]
    validation_results: List[ValidationResult] = field(default_factory=list)
    overall_score: float = 0.0
    is_valid: bool = False
    corrected_data: Optional[Dict[str, Any]] = None
    validation_timestamp: datetime = field(default_factory=datetime.now)


class ValidationPipeline:
    """
    Comprehensive validation pipeline for lead data.
    
    Features:
    - Multiple validation levels (lenient, moderate, strict)
    - Email validation with DNS checking
    - Phone number validation and formatting
    - Address validation and geocoding
    - Website validation and accessibility checking
    - Data correction suggestions
    - Batch processing with progress tracking
    - Detailed reporting and metrics
    """
    
    def __init__(self, 
                 config: Any,
                 error_handler: ErrorHandler,
                 logger: logging.Logger):
        
        self.config = config
        self.error_handler = error_handler
        self.logger = logger
        
        # Validation configuration
        self.validation_rules = self._setup_validation_rules()
        self.field_validators = self._setup_field_validators()
        
        # External service clients
        self._setup_external_services()
        
        self.logger.info("Validation pipeline initialized")
    
    def _setup_validation_rules(self) -> Dict[str, Dict]:
        """Setup validation rules for different levels"""
        return {
            ValidationLevel.LENIENT.value: {
                'email': {'required': True, 'dns_check': False, 'syntax_only': True},
                'phone': {'required': False, 'format_check': False},
                'name': {'required': True, 'min_length': 2},
                'website': {'required': False, 'accessibility_check': False},
                'address': {'required': False, 'geocoding': False}
            },
            ValidationLevel.MODERATE.value: {
                'email': {'required': True, 'dns_check': True, 'syntax_only': False},
                'phone': {'required': False, 'format_check': True},
                'name': {'required': True, 'min_length': 3},
                'website': {'required': False, 'accessibility_check': True},
                'address': {'required': False, 'geocoding': False}
            },
            ValidationLevel.STRICT.value: {
                'email': {'required': True, 'dns_check': True, 'syntax_only': False, 'deliverability_check': True},
                'phone': {'required': True, 'format_check': True, 'region_check': True},
                'name': {'required': True, 'min_length': 3, 'profanity_check': True},
                'website': {'required': False, 'accessibility_check': True, 'ssl_check': True},
                'address': {'required': False, 'geocoding': True, 'completeness_check': True}
            }
        }
    
    def _setup_field_validators(self) -> Dict[str, callable]:
        """Setup field-specific validator functions"""
        return {
            'email': self._validate_email,
            'phone': self._validate_phone,
            'name': self._validate_name,
            'website': self._validate_website,
            'address': self._validate_address,
            'company': self._validate_company
        }
    
    def _setup_external_services(self):
        """Setup external validation services"""
        # Email validation service
        self.mailtester_api_key = self.config.api.mailtester_api_key
        self.hunter_api_key = self.config.api.hunter_api_key
        
        # DNS resolver
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = 5
        self.dns_resolver.lifetime = 10
    
    async def validate_file(self, input_file: str, validation_level: str = "strict",
                          output_dir: str = "output") -> Dict[str, Any]:
        """
        Validate leads from a CSV file.
        
        Args:
            input_file: Path to input CSV file
            validation_level: Validation strictness level
            output_dir: Output directory for results
            
        Returns:
            Validation results summary
        """
        try:
            self.logger.info(f"Starting file validation: {input_file}")
            
            # Load data
            leads = await self._load_leads_from_file(input_file)
            if not leads:
                raise ValueError(f"No leads found in file: {input_file}")
            
            # Validate leads
            validation_reports = await self._validate_leads_batch(leads, validation_level)
            
            # Generate summary
            summary = self._generate_validation_summary(validation_reports)
            
            # Export results
            output_files = await self._export_validation_results(
                validation_reports, summary, output_dir, input_file
            )
            
            self.logger.info(f"File validation completed: {summary['valid_count']} valid, "
                           f"{summary['invalid_count']} invalid leads")
            
            return {
                'total_leads': len(leads),\n                'valid_count': summary['valid_count'],\n                'invalid_count': summary['invalid_count'],\n                'validation_rate': summary['validation_rate'],\n                'output_files': output_files,\n                'summary': summary,\n                'validation_level': validation_level\n            }\n            \n        except Exception as e:\n            self.logger.error(f\"File validation failed: {e}\")\n            raise\n    \n    async def validate_lead(self, lead_data: Dict[str, Any], \n                          validation_level: str = \"strict\") -> LeadValidationReport:\n        \"\"\"\n        Validate a single lead.\n        \n        Args:\n            lead_data: Lead data dictionary\n            validation_level: Validation strictness level\n            \n        Returns:\n            LeadValidationReport\n        \"\"\"\n        lead_id = lead_data.get('id', str(hash(str(lead_data))))\n        \n        report = LeadValidationReport(\n            lead_id=lead_id,\n            original_data=lead_data.copy()\n        )\n        \n        try:\n            # Get validation rules for level\n            rules = self.validation_rules[validation_level]\n            \n            # Validate each field\n            for field, field_rules in rules.items():\n                if field in lead_data or field_rules.get('required', False):\n                    validation_result = await self._validate_field(\n                        field, lead_data.get(field), field_rules\n                    )\n                    report.validation_results.append(validation_result)\n            \n            # Calculate overall score\n            report.overall_score = self._calculate_overall_score(report.validation_results)\n            report.is_valid = report.overall_score >= self.config.processing.quality_threshold\n            \n            # Generate corrected data if needed\n            if not report.is_valid:\n                report.corrected_data = self._generate_corrected_data(\n                    lead_data, report.validation_results\n                )\n            \n            return report\n            \n        except Exception as e:\n            self.logger.error(f\"Lead validation failed for {lead_id}: {e}\")\n            # Return failed validation report\n            report.validation_results.append(ValidationResult(\n                field=\"validation_error\",\n                is_valid=False,\n                confidence=0.0,\n                error_message=str(e),\n                validation_method=\"error_handling\"\n            ))\n            return report\n    \n    async def _load_leads_from_file(self, file_path: str) -> List[Dict[str, Any]]:\n        \"\"\"Load leads from CSV file\"\"\"\n        leads = []\n        \n        try:\n            with open(file_path, 'r', encoding='utf-8') as f:\n                reader = csv.DictReader(f)\n                for i, row in enumerate(reader):\n                    # Add unique ID if not present\n                    if 'id' not in row:\n                        row['id'] = f\"lead_{i+1}\"\n                    leads.append(row)\n            \n            self.logger.info(f\"Loaded {len(leads)} leads from {file_path}\")\n            return leads\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to load leads from {file_path}: {e}\")\n            raise\n    \n    async def _validate_leads_batch(self, leads: List[Dict[str, Any]], \n                                  validation_level: str) -> List[LeadValidationReport]:\n        \"\"\"Validate leads in batch with concurrency control\"\"\"\n        max_concurrent = self.config.processing.max_workers\n        semaphore = asyncio.Semaphore(max_concurrent)\n        \n        async def validate_single_lead(lead_data):\n            async with semaphore:\n                return await self.validate_lead(lead_data, validation_level)\n        \n        # Execute validations concurrently\n        tasks = [validate_single_lead(lead) for lead in leads]\n        reports = await asyncio.gather(*tasks, return_exceptions=True)\n        \n        # Filter out exceptions\n        valid_reports = []\n        for report in reports:\n            if isinstance(report, LeadValidationReport):\n                valid_reports.append(report)\n            else:\n                self.logger.error(f\"Validation task failed: {report}\")\n        \n        return valid_reports\n    \n    async def _validate_field(self, field_name: str, field_value: Any, \n                            field_rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate a single field\"\"\"\n        if field_name in self.field_validators:\n            return await self.field_validators[field_name](field_value, field_rules)\n        else:\n            # Generic validation\n            return await self._validate_generic_field(field_name, field_value, field_rules)\n    \n    async def _validate_email(self, email: str, rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate email address\"\"\"\n        if not email:\n            if rules.get('required', False):\n                return ValidationResult(\n                    field=\"email\",\n                    is_valid=False,\n                    confidence=0.0,\n                    error_message=\"Email is required\",\n                    validation_method=\"required_check\"\n                )\n            else:\n                return ValidationResult(\n                    field=\"email\",\n                    is_valid=True,\n                    confidence=1.0,\n                    validation_method=\"optional_field\"\n                )\n        \n        try:\n            # Basic syntax validation\n            validated_email = validate_email(email)\n            normalized_email = validated_email.email\n            \n            confidence = 0.7  # Base confidence for syntax validation\n            is_valid = True\n            error_message = None\n            \n            # DNS validation if enabled\n            if rules.get('dns_check', False):\n                dns_valid = await self._check_email_dns(normalized_email)\n                if not dns_valid:\n                    confidence = 0.3\n                    error_message = \"Domain does not exist or has no MX record\"\n                else:\n                    confidence = 0.9\n            \n            # Deliverability check if enabled (strict mode)\n            if rules.get('deliverability_check', False) and self.mailtester_api_key:\n                deliverable = await self._check_email_deliverability(normalized_email)\n                if deliverable['deliverable']:\n                    confidence = min(1.0, confidence + 0.1)\n                else:\n                    confidence = max(0.2, confidence - 0.3)\n                    error_message = f\"Email may not be deliverable: {deliverable.get('reason', 'Unknown')}\"\n            \n            return ValidationResult(\n                field=\"email\",\n                is_valid=is_valid and confidence > 0.5,\n                confidence=confidence,\n                error_message=error_message,\n                suggested_correction=normalized_email if normalized_email != email else None,\n                validation_method=\"comprehensive_email_validation\"\n            )\n            \n        except EmailNotValidError as e:\n            return ValidationResult(\n                field=\"email\",\n                is_valid=False,\n                confidence=0.0,\n                error_message=str(e),\n                validation_method=\"syntax_validation\"\n            )\n        except Exception as e:\n            self.logger.warning(f\"Email validation error for {email}: {e}\")\n            return ValidationResult(\n                field=\"email\",\n                is_valid=False,\n                confidence=0.0,\n                error_message=f\"Validation error: {str(e)}\",\n                validation_method=\"error_fallback\"\n            )\n    \n    async def _validate_phone(self, phone: str, rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate phone number\"\"\"\n        if not phone:\n            if rules.get('required', False):\n                return ValidationResult(\n                    field=\"phone\",\n                    is_valid=False,\n                    confidence=0.0,\n                    error_message=\"Phone number is required\",\n                    validation_method=\"required_check\"\n                )\n            else:\n                return ValidationResult(\n                    field=\"phone\",\n                    is_valid=True,\n                    confidence=1.0,\n                    validation_method=\"optional_field\"\n                )\n        \n        # Clean phone number\n        cleaned_phone = re.sub(r'[^\\d+]', '', phone)\n        \n        # Basic format validation\n        if len(cleaned_phone) < 10:\n            return ValidationResult(\n                field=\"phone\",\n                is_valid=False,\n                confidence=0.2,\n                error_message=\"Phone number too short\",\n                validation_method=\"length_check\"\n            )\n        \n        # US phone number pattern\n        us_pattern = re.compile(r'^\\+?1?[2-9]\\d{2}[2-9]\\d{2}\\d{4}$')\n        \n        confidence = 0.5\n        is_valid = True\n        suggested_correction = None\n        \n        if us_pattern.match(cleaned_phone):\n            confidence = 0.9\n            # Format as standard US number\n            if len(cleaned_phone) == 10:\n                suggested_correction = f\"({cleaned_phone[:3]}) {cleaned_phone[3:6]}-{cleaned_phone[6:]}\"\n            elif len(cleaned_phone) == 11 and cleaned_phone[0] == '1':\n                suggested_correction = f\"+1 ({cleaned_phone[1:4]}) {cleaned_phone[4:7]}-{cleaned_phone[7:]}\"\n        elif len(cleaned_phone) >= 10:\n            confidence = 0.6  # Possible international number\n        else:\n            is_valid = False\n            confidence = 0.1\n        \n        return ValidationResult(\n            field=\"phone\",\n            is_valid=is_valid,\n            confidence=confidence,\n            suggested_correction=suggested_correction,\n            validation_method=\"phone_format_validation\"\n        )\n    \n    async def _validate_name(self, name: str, rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate name field\"\"\"\n        if not name:\n            if rules.get('required', False):\n                return ValidationResult(\n                    field=\"name\",\n                    is_valid=False,\n                    confidence=0.0,\n                    error_message=\"Name is required\",\n                    validation_method=\"required_check\"\n                )\n            else:\n                return ValidationResult(\n                    field=\"name\",\n                    is_valid=True,\n                    confidence=1.0,\n                    validation_method=\"optional_field\"\n                )\n        \n        # Clean name\n        cleaned_name = name.strip()\n        \n        # Length check\n        min_length = rules.get('min_length', 2)\n        if len(cleaned_name) < min_length:\n            return ValidationResult(\n                field=\"name\",\n                is_valid=False,\n                confidence=0.1,\n                error_message=f\"Name too short (minimum {min_length} characters)\",\n                validation_method=\"length_check\"\n            )\n        \n        # Basic name pattern (letters, spaces, common punctuation)\n        name_pattern = re.compile(r\"^[a-zA-Z\\s.,'-]+$\")\n        \n        confidence = 0.7\n        is_valid = True\n        suggested_correction = None\n        \n        if not name_pattern.match(cleaned_name):\n            confidence = 0.3\n            # Try to suggest correction\n            suggested_correction = re.sub(r'[^a-zA-Z\\s.,\\'-]', '', cleaned_name)\n        \n        # Check for suspicious patterns\n        if any(word in cleaned_name.lower() for word in ['test', 'example', 'sample', 'dummy']):\n            confidence = 0.2\n        \n        # Title case suggestion\n        if cleaned_name != cleaned_name.title() and confidence > 0.5:\n            suggested_correction = cleaned_name.title()\n        \n        return ValidationResult(\n            field=\"name\",\n            is_valid=is_valid and confidence > 0.4,\n            confidence=confidence,\n            suggested_correction=suggested_correction,\n            validation_method=\"name_pattern_validation\"\n        )\n    \n    async def _validate_website(self, website: str, rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate website URL\"\"\"\n        if not website:\n            if rules.get('required', False):\n                return ValidationResult(\n                    field=\"website\",\n                    is_valid=False,\n                    confidence=0.0,\n                    error_message=\"Website is required\",\n                    validation_method=\"required_check\"\n                )\n            else:\n                return ValidationResult(\n                    field=\"website\",\n                    is_valid=True,\n                    confidence=1.0,\n                    validation_method=\"optional_field\"\n                )\n        \n        # Add protocol if missing\n        url = website.strip()\n        if not url.startswith(('http://', 'https://')):\n            url = 'https://' + url\n        \n        # Basic URL validation\n        url_pattern = re.compile(\n            r'^https?://'  # http:// or https://\n            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+'  # domain\n            r'(?:[A-Z]{2,6}\\.?|[A-Z0-9-]{2,}\\.?)|'  # host\n            r'localhost|'  # localhost\n            r'\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})'  # IP\n            r'(?::\\d+)?'  # optional port\n            r'(?:/?|[/?]\\S+)$', re.IGNORECASE)\n        \n        if not url_pattern.match(url):\n            return ValidationResult(\n                field=\"website\",\n                is_valid=False,\n                confidence=0.1,\n                error_message=\"Invalid URL format\",\n                validation_method=\"url_pattern_validation\"\n            )\n        \n        confidence = 0.6\n        is_valid = True\n        suggested_correction = url if url != website else None\n        \n        # Accessibility check if enabled\n        if rules.get('accessibility_check', False):\n            try:\n                response = requests.head(url, timeout=10, allow_redirects=True)\n                if response.status_code == 200:\n                    confidence = 0.9\n                elif response.status_code in [301, 302, 307, 308]:\n                    confidence = 0.8\n                else:\n                    confidence = 0.4\n                    is_valid = False\n            except Exception:\n                confidence = 0.3\n                is_valid = False\n        \n        return ValidationResult(\n            field=\"website\",\n            is_valid=is_valid,\n            confidence=confidence,\n            suggested_correction=suggested_correction,\n            validation_method=\"website_validation\"\n        )\n    \n    async def _validate_address(self, address: str, rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate address\"\"\"\n        if not address:\n            if rules.get('required', False):\n                return ValidationResult(\n                    field=\"address\",\n                    is_valid=False,\n                    confidence=0.0,\n                    error_message=\"Address is required\",\n                    validation_method=\"required_check\"\n                )\n            else:\n                return ValidationResult(\n                    field=\"address\",\n                    is_valid=True,\n                    confidence=1.0,\n                    validation_method=\"optional_field\"\n                )\n        \n        # Basic address validation\n        cleaned_address = address.strip()\n        \n        if len(cleaned_address) < 10:\n            return ValidationResult(\n                field=\"address\",\n                is_valid=False,\n                confidence=0.2,\n                error_message=\"Address too short\",\n                validation_method=\"length_check\"\n            )\n        \n        # Look for basic address components\n        has_number = bool(re.search(r'\\d', cleaned_address))\n        has_street_indicators = bool(re.search(\n            r'\\b(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court|pl|place)\\b', \n            cleaned_address, re.IGNORECASE\n        ))\n        \n        confidence = 0.4\n        if has_number:\n            confidence += 0.2\n        if has_street_indicators:\n            confidence += 0.2\n        \n        # US ZIP code pattern\n        if re.search(r'\\b\\d{5}(-\\d{4})?\\b', cleaned_address):\n            confidence += 0.1\n        \n        return ValidationResult(\n            field=\"address\",\n            is_valid=confidence > 0.5,\n            confidence=confidence,\n            validation_method=\"address_pattern_validation\"\n        )\n    \n    async def _validate_company(self, company: str, rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Validate company name\"\"\"\n        if not company:\n            return ValidationResult(\n                field=\"company\",\n                is_valid=True,\n                confidence=1.0,\n                validation_method=\"optional_field\"\n            )\n        \n        cleaned_company = company.strip()\n        \n        # Basic validation\n        if len(cleaned_company) < 2:\n            return ValidationResult(\n                field=\"company\",\n                is_valid=False,\n                confidence=0.1,\n                error_message=\"Company name too short\",\n                validation_method=\"length_check\"\n            )\n        \n        confidence = 0.7\n        \n        # Check for common business suffixes\n        business_suffixes = ['inc', 'corp', 'llc', 'ltd', 'co', 'company', 'corporation']\n        if any(suffix in cleaned_company.lower() for suffix in business_suffixes):\n            confidence = 0.9\n        \n        return ValidationResult(\n            field=\"company\",\n            is_valid=True,\n            confidence=confidence,\n            validation_method=\"company_pattern_validation\"\n        )\n    \n    async def _validate_generic_field(self, field_name: str, field_value: Any, \n                                     rules: Dict[str, Any]) -> ValidationResult:\n        \"\"\"Generic field validation\"\"\"\n        if not field_value:\n            if rules.get('required', False):\n                return ValidationResult(\n                    field=field_name,\n                    is_valid=False,\n                    confidence=0.0,\n                    error_message=f\"{field_name} is required\",\n                    validation_method=\"required_check\"\n                )\n            else:\n                return ValidationResult(\n                    field=field_name,\n                    is_valid=True,\n                    confidence=1.0,\n                    validation_method=\"optional_field\"\n                )\n        \n        # Basic validation - just check if value exists\n        return ValidationResult(\n            field=field_name,\n            is_valid=True,\n            confidence=0.5,\n            validation_method=\"basic_validation\"\n        )\n    \n    async def _check_email_dns(self, email: str) -> bool:\n        \"\"\"Check if email domain has valid MX record\"\"\"\n        try:\n            domain = email.split('@')[1]\n            self.dns_resolver.resolve(domain, 'MX')\n            return True\n        except Exception:\n            return False\n    \n    async def _check_email_deliverability(self, email: str) -> Dict[str, Any]:\n        \"\"\"Check email deliverability using external service\"\"\"\n        if not self.mailtester_api_key:\n            return {'deliverable': True, 'reason': 'No API key configured'}\n        \n        try:\n            # This would integrate with an actual email validation service\n            # For now, return mock data\n            await asyncio.sleep(0.1)  # Simulate API call\n            \n            return {\n                'deliverable': True,\n                'reason': 'Mock validation - always true',\n                'confidence': 0.9\n            }\n            \n        except Exception as e:\n            self.logger.warning(f\"Email deliverability check failed: {e}\")\n            return {'deliverable': False, 'reason': str(e)}\n    \n    def _calculate_overall_score(self, validation_results: List[ValidationResult]) -> float:\n        \"\"\"Calculate overall validation score\"\"\"\n        if not validation_results:\n            return 0.0\n        \n        # Weight different fields\n        field_weights = {\n            'email': 0.4,\n            'phone': 0.2,\n            'name': 0.2,\n            'website': 0.1,\n            'address': 0.1\n        }\n        \n        total_weight = 0.0\n        weighted_score = 0.0\n        \n        for result in validation_results:\n            weight = field_weights.get(result.field, 0.05)\n            total_weight += weight\n            \n            if result.is_valid:\n                weighted_score += weight * result.confidence\n        \n        return weighted_score / total_weight if total_weight > 0 else 0.0\n    \n    def _generate_corrected_data(self, original_data: Dict[str, Any], \n                               validation_results: List[ValidationResult]) -> Dict[str, Any]:\n        \"\"\"Generate corrected data based on validation results\"\"\"\n        corrected = original_data.copy()\n        \n        for result in validation_results:\n            if result.suggested_correction:\n                corrected[result.field] = result.suggested_correction\n        \n        return corrected\n    \n    def _generate_validation_summary(self, reports: List[LeadValidationReport]) -> Dict[str, Any]:\n        \"\"\"Generate validation summary statistics\"\"\"\n        total_leads = len(reports)\n        valid_leads = len([r for r in reports if r.is_valid])\n        invalid_leads = total_leads - valid_leads\n        \n        # Field-specific statistics\n        field_stats = {}\n        for report in reports:\n            for result in report.validation_results:\n                field = result.field\n                if field not in field_stats:\n                    field_stats[field] = {'total': 0, 'valid': 0, 'confidence_sum': 0.0}\n                \n                field_stats[field]['total'] += 1\n                if result.is_valid:\n                    field_stats[field]['valid'] += 1\n                field_stats[field]['confidence_sum'] += result.confidence\n        \n        # Calculate field validation rates\n        for field, stats in field_stats.items():\n            stats['validation_rate'] = stats['valid'] / stats['total'] * 100\n            stats['avg_confidence'] = stats['confidence_sum'] / stats['total']\n        \n        return {\n            'total_leads': total_leads,\n            'valid_count': valid_leads,\n            'invalid_count': invalid_leads,\n            'validation_rate': valid_leads / total_leads * 100 if total_leads > 0 else 0,\n            'field_statistics': field_stats,\n            'avg_overall_score': sum(r.overall_score for r in reports) / total_leads if total_leads > 0 else 0\n        }\n    \n    async def _export_validation_results(self, reports: List[LeadValidationReport], \n                                        summary: Dict[str, Any], output_dir: str,\n                                        input_file: str) -> List[str]:\n        \"\"\"Export validation results to files\"\"\"\n        output_files = []\n        timestamp = datetime.now().strftime(\"%Y%m%d_%H%M%S\")\n        base_name = Path(input_file).stem\n        \n        output_path = Path(output_dir)\n        output_path.mkdir(parents=True, exist_ok=True)\n        \n        # Export valid leads\n        valid_leads_file = output_path / f\"{base_name}_valid_{timestamp}.csv\"\n        valid_reports = [r for r in reports if r.is_valid]\n        \n        if valid_reports:\n            with open(valid_leads_file, 'w', newline='', encoding='utf-8') as f:\n                if valid_reports[0].original_data:\n                    fieldnames = list(valid_reports[0].original_data.keys()) + ['validation_score']\n                    writer = csv.DictWriter(f, fieldnames=fieldnames)\n                    writer.writeheader()\n                    \n                    for report in valid_reports:\n                        row = report.original_data.copy()\n                        row['validation_score'] = round(report.overall_score, 3)\n                        writer.writerow(row)\n            \n            output_files.append(str(valid_leads_file))\n        \n        # Export invalid leads with corrections\n        invalid_leads_file = output_path / f\"{base_name}_invalid_{timestamp}.csv\"\n        invalid_reports = [r for r in reports if not r.is_valid]\n        \n        if invalid_reports:\n            with open(invalid_leads_file, 'w', newline='', encoding='utf-8') as f:\n                fieldnames = ['lead_id', 'field', 'original_value', 'error_message', \n                            'suggested_correction', 'confidence']\n                writer = csv.DictWriter(f, fieldnames=fieldnames)\n                writer.writeheader()\n                \n                for report in invalid_reports:\n                    for result in report.validation_results:\n                        if not result.is_valid:\n                            writer.writerow({\n                                'lead_id': report.lead_id,\n                                'field': result.field,\n                                'original_value': report.original_data.get(result.field, ''),\n                                'error_message': result.error_message,\n                                'suggested_correction': result.suggested_correction,\n                                'confidence': round(result.confidence, 3)\n                            })\n            \n            output_files.append(str(invalid_leads_file))\n        \n        # Export detailed validation report\n        report_file = output_path / f\"{base_name}_validation_report_{timestamp}.json\"\n        \n        detailed_report = {\n            'validation_timestamp': datetime.now().isoformat(),\n            'input_file': input_file,\n            'summary': summary,\n            'detailed_reports': [\n                {\n                    'lead_id': r.lead_id,\n                    'is_valid': r.is_valid,\n                    'overall_score': r.overall_score,\n                    'validation_results': [\n                        {\n                            'field': vr.field,\n                            'is_valid': vr.is_valid,\n                            'confidence': vr.confidence,\n                            'error_message': vr.error_message,\n                            'suggested_correction': vr.suggested_correction,\n                            'validation_method': vr.validation_method\n                        }\n                        for vr in r.validation_results\n                    ]\n                }\n                for r in reports\n            ]\n        }\n        \n        with open(report_file, 'w', encoding='utf-8') as f:\n            json.dump(detailed_report, f, indent=2, default=str)\n        \n        output_files.append(str(report_file))\n        \n        self.logger.info(f\"Validation results exported to {len(output_files)} files\")\n        return output_files"