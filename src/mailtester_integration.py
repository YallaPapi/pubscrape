#!/usr/bin/env python3
"""
Mailtester Ninja API Integration for VRSEN Lead Generation System
Provides email validation using Mailtester Ninja API service
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests
import aiohttp
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

@dataclass
class MailtesterResult:
    """Mailtester validation result"""
    email: str
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    status: str  # valid, invalid, risky, unknown
    reason: str  # Detailed reason for the status
    
    # Technical details
    smtp_valid: Optional[bool] = None
    mx_records_exist: bool = False
    disposable: bool = False
    role_account: bool = False
    
    # Additional metadata
    domain: str = ""
    suggested_correction: Optional[str] = None
    validation_time_ms: float = 0.0
    api_response: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

class MailtesterNinjaClient:
    """Mailtester Ninja API client with async support"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.mailtester.ninja"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = None
        
        # Rate limiting
        self.requests_per_minute = 60  # Default limit
        self.last_request_times = []
        
        # Statistics
        self.total_validations = 0
        self.successful_validations = 0
        self.failed_validations = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.last_request_times = [
            t for t in self.last_request_times 
            if now - t < 60
        ]
        
        # Check if we're at the limit
        if len(self.last_request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.last_request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.last_request_times.append(now)
    
    async def validate_email(self, email: str) -> MailtesterResult:
        """Validate a single email address"""
        start_time = time.time()
        
        try:
            self._enforce_rate_limit()
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Prepare request
            url = f"{self.base_url}/v1/verify"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'email': email,
                'check_smtp': True,
                'check_disposable': True,
                'check_role_account': True
            }
            
            # Make API request
            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()
                validation_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = self._parse_response(email, response_data, validation_time)
                    self.successful_validations += 1
                    logger.debug(f"Validated {email}: {result.status} (confidence: {result.confidence_score:.2f})")
                    return result
                else:
                    error_msg = response_data.get('error', 'Unknown error')
                    logger.error(f"API error for {email}: {error_msg}")
                    self.failed_validations += 1
                    return self._create_error_result(email, error_msg, validation_time)
        
        except asyncio.TimeoutError:
            validation_time = (time.time() - start_time) * 1000
            logger.error(f"Timeout validating {email}")
            self.failed_validations += 1
            return self._create_error_result(email, "Timeout", validation_time)
        
        except Exception as e:
            validation_time = (time.time() - start_time) * 1000
            logger.error(f"Error validating {email}: {e}")
            self.failed_validations += 1
            return self._create_error_result(email, str(e), validation_time)
        
        finally:
            self.total_validations += 1
    
    def validate_email_sync(self, email: str) -> MailtesterResult:
        """Synchronous email validation"""
        start_time = time.time()
        
        try:
            self._enforce_rate_limit()
            
            # Prepare request
            url = f"{self.base_url}/v1/verify"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'email': email,
                'check_smtp': True,
                'check_disposable': True,
                'check_role_account': True
            }
            
            # Make API request
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            validation_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                response_data = response.json()
                result = self._parse_response(email, response_data, validation_time)
                self.successful_validations += 1
                logger.debug(f"Validated {email}: {result.status} (confidence: {result.confidence_score:.2f})")
                return result
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', 'Unknown error')
                except:
                    error_msg = f"HTTP {response.status_code}"
                
                logger.error(f"API error for {email}: {error_msg}")
                self.failed_validations += 1
                return self._create_error_result(email, error_msg, validation_time)
        
        except requests.exceptions.Timeout:
            validation_time = (time.time() - start_time) * 1000
            logger.error(f"Timeout validating {email}")
            self.failed_validations += 1
            return self._create_error_result(email, "Timeout", validation_time)
        
        except Exception as e:
            validation_time = (time.time() - start_time) * 1000
            logger.error(f"Error validating {email}: {e}")
            self.failed_validations += 1
            return self._create_error_result(email, str(e), validation_time)
        
        finally:
            self.total_validations += 1
    
    async def validate_emails_batch(self, emails: List[str], batch_size: int = 10) -> List[MailtesterResult]:
        """Validate multiple emails in batches"""
        results = []
        
        # Process in batches to respect rate limits
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} emails)")
            
            # Create tasks for concurrent validation
            tasks = [self.validate_email(email) for email in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Exception validating {batch[j]}: {result}")
                    error_result = self._create_error_result(batch[j], str(result), 0)
                    results.append(error_result)
                else:
                    results.append(result)
            
            # Delay between batches
            if i + batch_size < len(emails):
                await asyncio.sleep(1)
        
        return results
    
    def _parse_response(self, email: str, response_data: Dict, validation_time: float) -> MailtesterResult:
        """Parse API response into MailtesterResult"""
        
        # Extract main validation result
        is_valid = response_data.get('valid', False)
        status = response_data.get('status', 'unknown')
        reason = response_data.get('reason', 'No reason provided')
        
        # Calculate confidence score based on multiple factors
        confidence_score = self._calculate_confidence_score(response_data)
        
        # Extract technical details
        smtp_valid = response_data.get('smtp_check', {}).get('valid')
        mx_records_exist = response_data.get('mx_records_exist', False)
        disposable = response_data.get('disposable', False)
        role_account = response_data.get('role_account', False)
        
        # Extract domain
        domain = email.split('@')[1] if '@' in email else ""
        
        # Check for suggested correction
        suggested_correction = response_data.get('suggested_correction')
        
        return MailtesterResult(
            email=email,
            is_valid=is_valid,
            confidence_score=confidence_score,
            status=status,
            reason=reason,
            smtp_valid=smtp_valid,
            mx_records_exist=mx_records_exist,
            disposable=disposable,
            role_account=role_account,
            domain=domain,
            suggested_correction=suggested_correction,
            validation_time_ms=validation_time,
            api_response=response_data
        )
    
    def _calculate_confidence_score(self, response_data: Dict) -> float:
        """Calculate confidence score from API response"""
        score = 0.0
        
        # Base validity check
        if response_data.get('valid', False):
            score += 0.4
        
        # SMTP check
        smtp_result = response_data.get('smtp_check', {})
        if smtp_result.get('valid', False):
            score += 0.3
        elif smtp_result.get('valid') is False:
            score -= 0.2
        
        # MX records
        if response_data.get('mx_records_exist', False):
            score += 0.2
        
        # Disposable email check
        if not response_data.get('disposable', False):
            score += 0.1
        else:
            score -= 0.3
        
        # Role account check
        if not response_data.get('role_account', False):
            score += 0.1
        else:
            score -= 0.1
        
        # Syntax check
        if response_data.get('syntax_valid', False):
            score += 0.1
        
        # Domain reputation (if available)
        domain_reputation = response_data.get('domain_reputation', 0)
        if domain_reputation > 0.7:
            score += 0.1
        elif domain_reputation < 0.3:
            score -= 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def _create_error_result(self, email: str, error_message: str, validation_time: float) -> MailtesterResult:
        """Create error result for failed validations"""
        domain = email.split('@')[1] if '@' in email else ""
        
        return MailtesterResult(
            email=email,
            is_valid=False,
            confidence_score=0.0,
            status="error",
            reason=f"Validation failed: {error_message}",
            domain=domain,
            validation_time_ms=validation_time
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        success_rate = (self.successful_validations / self.total_validations * 100) if self.total_validations > 0 else 0
        
        return {
            "total_validations": self.total_validations,
            "successful_validations": self.successful_validations,
            "failed_validations": self.failed_validations,
            "success_rate": round(success_rate, 2),
            "requests_per_minute_limit": self.requests_per_minute
        }

class MailtesterIntegration:
    """High-level integration class for Mailtester Ninja API"""
    
    def __init__(self, api_key: Optional[str] = None, fallback_validation: bool = True):
        """
        Initialize Mailtester integration
        
        Args:
            api_key: Mailtester Ninja API key (can be None for fallback mode)
            fallback_validation: Whether to use fallback validation when API fails
        """
        self.api_key = api_key
        self.fallback_validation = fallback_validation
        self.client = None
        
        if self.api_key:
            self.client = MailtesterNinjaClient(self.api_key)
            logger.info("Mailtester Ninja integration initialized with API key")
        else:
            logger.warning("Mailtester Ninja API key not provided - using fallback validation only")
    
    async def validate_lead_emails(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate emails for a list of leads"""
        if not leads:
            return leads
        
        # Extract emails to validate
        emails_to_validate = []
        email_to_lead_map = {}
        
        for i, lead in enumerate(leads):
            primary_email = lead.get('primary_email') or lead.get('email', '')
            if primary_email and self._is_email_format_valid(primary_email):
                emails_to_validate.append(primary_email)
                email_to_lead_map[primary_email] = i
        
        if not emails_to_validate:
            logger.info("No valid emails to validate")
            return leads
        
        logger.info(f"Validating {len(emails_to_validate)} emails using Mailtester Ninja")
        
        # Validate emails
        if self.client and self.api_key:
            validation_results = await self._validate_with_api(emails_to_validate)
        else:
            validation_results = self._validate_with_fallback(emails_to_validate)
        
        # Apply validation results to leads
        updated_leads = leads.copy()
        for result in validation_results:
            if result.email in email_to_lead_map:
                lead_index = email_to_lead_map[result.email]
                lead = updated_leads[lead_index]
                
                # Update lead with validation results
                lead['email_confidence'] = result.confidence_score
                lead['email_validation_status'] = result.status
                lead['email_validation_reason'] = result.reason
                lead['is_valid_email'] = result.is_valid
                
                # Update validation metadata
                if 'validation_details' not in lead:
                    lead['validation_details'] = {}
                
                lead['validation_details'].update({
                    'mailtester_result': result.to_dict(),
                    'validated_at': time.time(),
                    'disposable': result.disposable,
                    'role_account': result.role_account
                })
                
                # Apply suggested correction if available
                if result.suggested_correction and result.suggested_correction != result.email:
                    lead['suggested_email'] = result.suggested_correction
        
        # Log validation summary
        valid_emails = sum(1 for r in validation_results if r.is_valid)
        logger.info(f"Email validation complete: {valid_emails}/{len(validation_results)} emails are valid")
        
        return updated_leads
    
    async def _validate_with_api(self, emails: List[str]) -> List[MailtesterResult]:
        """Validate emails using Mailtester Ninja API"""
        try:
            async with self.client:
                results = await self.client.validate_emails_batch(emails, batch_size=5)
            return results
        except Exception as e:
            logger.error(f"API validation failed: {e}")
            if self.fallback_validation:
                logger.info("Falling back to basic validation")
                return self._validate_with_fallback(emails)
            else:
                raise
    
    def _validate_with_fallback(self, emails: List[str]) -> List[MailtesterResult]:
        """Fallback validation using basic checks"""
        results = []
        
        for email in emails:
            is_valid = self._is_email_format_valid(email)
            confidence = 0.7 if is_valid else 0.1
            status = "valid" if is_valid else "invalid"
            reason = "Basic format validation" if is_valid else "Invalid format"
            
            result = MailtesterResult(
                email=email,
                is_valid=is_valid,
                confidence_score=confidence,
                status=status,
                reason=reason,
                domain=email.split('@')[1] if '@' in email else "",
                validation_time_ms=1.0
            )
            results.append(result)
        
        return results
    
    def _is_email_format_valid(self, email: str) -> bool:
        """Basic email format validation"""
        import re
        
        if not email or '@' not in email:
            return False
        
        # Basic email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_single_email_sync(self, email: str) -> MailtesterResult:
        """Synchronously validate a single email"""
        if not self._is_email_format_valid(email):
            return MailtesterResult(
                email=email,
                is_valid=False,
                confidence_score=0.0,
                status="invalid",
                reason="Invalid email format",
                domain=email.split('@')[1] if '@' in email else "",
                validation_time_ms=0.1
            )
        
        if self.client and self.api_key:
            try:
                return self.client.validate_email_sync(email)
            except Exception as e:
                logger.error(f"API validation failed for {email}: {e}")
                if self.fallback_validation:
                    return self._validate_with_fallback([email])[0]
                raise
        else:
            return self._validate_with_fallback([email])[0]

# Utility functions for easy integration
def create_mailtester_integration(api_key: Optional[str] = None) -> MailtesterIntegration:
    """Create Mailtester integration instance"""
    return MailtesterIntegration(api_key)

async def validate_emails_async(emails: List[str], api_key: Optional[str] = None) -> List[MailtesterResult]:
    """Async utility function to validate emails"""
    integration = create_mailtester_integration(api_key)
    
    if integration.client and api_key:
        async with integration.client:
            return await integration.client.validate_emails_batch(emails)
    else:
        return integration._validate_with_fallback(emails)

def validate_email_sync(email: str, api_key: Optional[str] = None) -> MailtesterResult:
    """Sync utility function to validate single email"""
    integration = create_mailtester_integration(api_key)
    return integration.validate_single_email_sync(email)

if __name__ == "__main__":
    # Example usage
    import os
    
    async def test_validation():
        """Test email validation"""
        api_key = os.getenv('MAILTESTER_API_KEY')
        
        test_emails = [
            "test@example.com",
            "invalid-email",
            "admin@gmail.com",
            "contact@vrsen.com"
        ]
        
        integration = MailtesterIntegration(api_key)
        
        print("Testing email validation...")
        for email in test_emails:
            result = integration.validate_single_email_sync(email)
            print(f"{email}: {result.status} (confidence: {result.confidence_score:.2f})")
    
    # Run test
    asyncio.run(test_validation())