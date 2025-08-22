"""
Validation Framework Testing Suite
=================================

Comprehensive testing suite for the Restaurant Validation Framework
to verify it properly detects fake data, technical shortcuts, and
ensures data authenticity at every level.

This test suite includes:
1. Fake data detection tests
2. Real data acceptance tests  
3. Technical debt detection tests
4. Edge case handling tests
5. Performance validation tests
"""

import logging
import json
import time
from typing import List, Dict, Any
from datetime import datetime

from restaurant_validation_framework import (
    RestaurantValidationFramework,
    RestaurantLead,
    ValidationLevel,
    DataQuality,
    ValidationStatus,
    RestaurantBusinessValidator,
    SantaMonicaGeographicValidator,
    PhoneNumberValidator,
    EmailDomainValidator,
    TechnicalDebtMonitor,
    FakeDataDetector
)


class ValidationFrameworkTester:
    """Comprehensive tester for the validation framework"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.test_results = []
        
        # Initialize all validators for individual testing
        self.business_validator = RestaurantBusinessValidator()
        self.location_validator = SantaMonicaGeographicValidator()
        self.phone_validator = PhoneNumberValidator()
        self.email_validator = EmailDomainValidator()
        self.debt_monitor = TechnicalDebtMonitor()
        self.fake_detector = FakeDataDetector()
        
        # Initialize validation framework
        self.framework = RestaurantValidationFramework(ValidationLevel.STRICT)
        
        self.logger.info("ValidationFrameworkTester initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for testing"""
        logger = logging.getLogger(f"{__name__}.ValidationFrameworkTester")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        self.logger.info("Starting comprehensive validation framework tests")
        start_time = time.time()
        
        test_suites = [
            ("fake_data_detection", self.test_fake_data_detection),
            ("real_data_acceptance", self.test_real_data_acceptance),
            ("technical_debt_detection", self.test_technical_debt_detection),
            ("edge_case_handling", self.test_edge_case_handling),
            ("business_validation", self.test_business_validation),
            ("location_validation", self.test_location_validation),
            ("phone_validation", self.test_phone_validation),
            ("email_validation", self.test_email_validation),
            ("framework_integration", self.test_framework_integration),
            ("performance_validation", self.test_performance_validation)
        ]
        
        for test_name, test_func in test_suites:
            self.logger.info(f"Running {test_name} tests...")
            try:
                test_result = test_func()
                test_result['test_name'] = test_name
                test_result['status'] = 'PASS' if test_result['success'] else 'FAIL'
                self.test_results.append(test_result)
                
                self.logger.info(f"{test_name}: {test_result['status']} - {test_result['summary']}")
                
            except Exception as e:
                error_result = {
                    'test_name': test_name,
                    'status': 'ERROR',
                    'success': False,
                    'summary': f"Test failed with error: {str(e)}",
                    'error': str(e)
                }
                self.test_results.append(error_result)
                self.logger.error(f"{test_name}: ERROR - {str(e)}")
        
        total_time = time.time() - start_time
        
        # Generate final report
        report = self._generate_test_report(total_time)
        
        self.logger.info(f"All validation tests completed in {total_time:.2f}s")
        
        return report
    
    def test_fake_data_detection(self) -> Dict[str, Any]:
        """Test the framework's ability to detect fake/mock data"""
        
        fake_leads = [
            # Obvious fake data
            RestaurantLead(
                name="Test Restaurant 123",
                address="123 Test Street, Santa Monica, CA 90401",
                phone="(555) 123-4567",
                email="test@example.com",
                website="http://test.example.com"
            ),
            # Sequential naming pattern (generated data)
            RestaurantLead(
                name="Restaurant 001",
                address="456 Main St, Santa Monica, CA 90402",
                phone="(310) 555-0000",
                email="info@restaurant001.com",
                website="http://restaurant001.com"
            ),
            # Placeholder data
            RestaurantLead(
                name="Sample Eatery",
                address="Sample Address, Santa Monica, CA",
                phone="(555) 000-0000",
                email="placeholder@example.org",
                website="http://placeholder.local"
            ),
            # Mock data patterns
            RestaurantLead(
                name="Mock Cafe",
                address="Lorem ipsum street, Santa Monica, CA 90403",
                phone="(555) 555-5555",
                email="fake@test.com",
                website="http://mock.test"
            )
        ]
        
        detection_results = []
        total_fake_detected = 0
        
        for i, lead in enumerate(fake_leads):
            # Test individual fake data detector
            is_authentic = self.fake_detector.is_authentic_restaurant(lead)
            fake_indicators = self.fake_detector.get_fake_indicators(lead)
            
            # Test full framework validation
            validated_lead = self.framework.validate_lead(lead)
            
            result = {
                'lead_index': i,
                'lead_name': lead.name,
                'fake_detector_caught': not is_authentic,
                'fake_indicators': fake_indicators,
                'framework_score': validated_lead.overall_score,
                'framework_authentic': validated_lead.is_authentic,
                'fake_quality_detected': any(vr.quality == DataQuality.FAKE for vr in validated_lead.validation_results)
            }
            
            detection_results.append(result)
            
            # Count successful detections
            if not is_authentic or not validated_lead.is_authentic or result['fake_quality_detected']:
                total_fake_detected += 1
        
        success = total_fake_detected == len(fake_leads)  # All fake data should be detected
        
        return {
            'success': success,
            'summary': f"Detected {total_fake_detected}/{len(fake_leads)} fake leads",
            'details': detection_results,
            'detection_rate': total_fake_detected / len(fake_leads) if fake_leads else 0
        }
    
    def test_real_data_acceptance(self) -> Dict[str, Any]:
        """Test that the framework accepts legitimate restaurant data"""
        
        real_leads = [
            # Legitimate Santa Monica restaurant
            RestaurantLead(
                name="Boa Steakhouse",
                address="101 Santa Monica Blvd, Santa Monica, CA 90401",
                phone="(310) 899-4466",
                email="info@boasteakhouse.com",
                website="https://boasteakhouse.com",
                cuisine_type="American"
            ),
            # Another legitimate restaurant
            RestaurantLead(
                name="The Lobster Restaurant",
                address="1602 Ocean Ave, Santa Monica, CA 90401",
                phone="(310) 458-9294",
                email="reservations@thelobster.com",
                website="https://thelobster.com",
                cuisine_type="Seafood"
            ),
            # Casual dining restaurant
            RestaurantLead(
                name="Rustic Canyon Wine Bar",
                address="1119 Wilshire Blvd, Santa Monica, CA 90401",
                phone="(310) 393-7050",
                email="info@rusticcanyonwinebar.com",
                website="https://rusticcanyonwinebar.com",
                cuisine_type="Mediterranean"
            ),
            # Small local restaurant (may have personal email)
            RestaurantLead(
                name="Pho Saigon Pearl",
                address="2058 Sawtelle Blvd, Los Angeles, CA 90025",
                phone="(310) 477-1882",
                email="owner@gmail.com",  # Personal email but legitimate
                website="",
                cuisine_type="Vietnamese"
            )
        ]
        
        acceptance_results = []
        total_accepted = 0
        
        for i, lead in enumerate(real_leads):
            # Test framework validation
            validated_lead = self.framework.validate_lead(lead)
            
            result = {
                'lead_index': i,
                'lead_name': lead.name,
                'framework_score': validated_lead.overall_score,
                'framework_authentic': validated_lead.is_authentic,
                'validation_results': [
                    {
                        'status': vr.status.value,
                        'quality': vr.quality.value,
                        'score': vr.score,
                        'message': vr.message
                    }
                    for vr in validated_lead.validation_results
                ],
                'has_fake_quality': any(vr.quality == DataQuality.FAKE for vr in validated_lead.validation_results)
            }
            
            acceptance_results.append(result)
            
            # Count accepted leads (should be high score and authentic)
            if validated_lead.overall_score >= 0.6 and not result['has_fake_quality']:
                total_accepted += 1
        
        success = total_accepted >= len(real_leads) * 0.75  # At least 75% should be accepted
        
        return {
            'success': success,
            'summary': f"Accepted {total_accepted}/{len(real_leads)} legitimate leads",
            'details': acceptance_results,
            'acceptance_rate': total_accepted / len(real_leads) if real_leads else 0
        }
    
    def test_technical_debt_detection(self) -> Dict[str, Any]:
        """Test detection of technical debt and implementation shortcuts"""
        
        # Create leads with technical debt indicators
        debt_leads = [
            # Empty fields (implementation shortcut)
            RestaurantLead(name="Restaurant A", address="", phone="", email="", website=""),
            
            # Placeholder values
            RestaurantLead(
                name="Restaurant B",
                address="N/A",
                phone="None",
                email="null",
                website="undefined"
            ),
            
            # Hardcoded test values
            RestaurantLead(
                name="TODO Restaurant",
                address="FIXME Address",
                phone="XXX-XXX-XXXX",
                email="HACK@email.com",
                website="hardcoded.com"
            ),
            
            # Suspiciously uniform data (suggests generation)
            RestaurantLead(
                name="Restaurant 001",
                address="1234 Main St, Santa Monica, CA 90401",
                phone="(310) 123-4567",
                email="info@restaurant001.com",
                website="http://restaurant001.com"
            ),
            RestaurantLead(
                name="Restaurant 002",
                address="1235 Main St, Santa Monica, CA 90401",
                phone="(310) 123-4568",
                email="info@restaurant002.com",
                website="http://restaurant002.com"
            ),
            RestaurantLead(
                name="Restaurant 003",
                address="1236 Main St, Santa Monica, CA 90401",
                phone="(310) 123-4569",
                email="info@restaurant003.com",
                website="http://restaurant003.com"
            )
        ]
        
        # Test technical debt monitoring
        debt_result = self.debt_monitor.monitor_lead_data(debt_leads)
        
        # Individual lead checks
        individual_results = []
        for i, lead in enumerate(debt_leads[:3]):  # Test first 3 individual leads
            lead_issues = self.debt_monitor._check_lead_technical_debt(lead, i)
            individual_results.append({
                'lead_index': i,
                'lead_name': lead.name,
                'debt_issues': lead_issues,
                'has_debt': len(lead_issues) > 0
            })
        
        # Check uniformity detection
        uniformity_issues = self.debt_monitor._check_data_uniformity(debt_leads)
        generation_issues = self.debt_monitor._check_generation_patterns(debt_leads)
        
        success = (
            debt_result.status in [ValidationStatus.FAIL, ValidationStatus.WARNING] and
            len(uniformity_issues) > 0 and
            len(generation_issues) > 0 and
            any(result['has_debt'] for result in individual_results)
        )
        
        return {
            'success': success,
            'summary': f"Technical debt detection: {debt_result.status.value} (score: {debt_result.score:.2f})",
            'details': {
                'batch_result': {
                    'status': debt_result.status.value,
                    'quality': debt_result.quality.value,
                    'score': debt_result.score,
                    'message': debt_result.message
                },
                'individual_results': individual_results,
                'uniformity_issues': uniformity_issues,
                'generation_issues': generation_issues
            }
        }
    
    def test_edge_case_handling(self) -> Dict[str, Any]:
        """Test handling of edge cases and malformed data"""
        
        edge_cases = [
            # Empty lead
            RestaurantLead(name="", address="", phone="", email="", website=""),
            
            # Malformed data
            RestaurantLead(
                name="Restaurant with\nNewlines\tTabs",
                address="123 Main St\n\nSanta Monica",
                phone="not-a-phone",
                email="invalid-email",
                website="not-a-url"
            ),
            
            # Very long data
            RestaurantLead(
                name="A" * 500,  # Very long name
                address="B" * 1000,  # Very long address
                phone="1" * 50,  # Very long phone
                email="c" * 100 + "@" + "d" * 100 + ".com",  # Very long email
                website="http://" + "e" * 200 + ".com"  # Very long URL
            ),
            
            # Unicode and special characters
            RestaurantLead(
                name="Café José's Taquería & Grill",
                address="123 Résumé Blvd, Santa Mónica, CA 90401",
                phone="(310) 555-¿Qué?",
                email="josé@café.com",
                website="https://café.com"
            ),
            
            # Boundary values
            RestaurantLead(
                name=None,  # None values
                address=None,
                phone=None,
                email=None,
                website=None
            )
        ]
        
        edge_results = []
        errors_handled = 0
        
        for i, lead in enumerate(edge_cases):
            try:
                # Framework should handle edge cases gracefully
                validated_lead = self.framework.validate_lead(lead)
                
                result = {
                    'lead_index': i,
                    'handled_gracefully': True,
                    'overall_score': validated_lead.overall_score,
                    'validation_count': len(validated_lead.validation_results),
                    'error': None
                }
                
                errors_handled += 1
                
            except Exception as e:
                result = {
                    'lead_index': i,
                    'handled_gracefully': False,
                    'error': str(e)
                }
            
            edge_results.append(result)
        
        success = errors_handled == len(edge_cases)  # All cases should be handled
        
        return {
            'success': success,
            'summary': f"Handled {errors_handled}/{len(edge_cases)} edge cases gracefully",
            'details': edge_results,
            'error_handling_rate': errors_handled / len(edge_cases) if edge_cases else 0
        }
    
    def test_business_validation(self) -> Dict[str, Any]:
        """Test business authenticity validation"""
        
        test_cases = [
            # Authentic restaurants
            {"lead": RestaurantLead(name="Joe's Italian Kitchen", cuisine_type="Italian"), "expect_authentic": True},
            {"lead": RestaurantLead(name="Ocean View Seafood", cuisine_type="Seafood"), "expect_authentic": True},
            {"lead": RestaurantLead(name="The Blue Door Bistro", cuisine_type="French"), "expect_authentic": True},
            
            # Fake/test restaurants
            {"lead": RestaurantLead(name="Test Restaurant 123"), "expect_authentic": False},
            {"lead": RestaurantLead(name="Sample Diner"), "expect_authentic": False},
            {"lead": RestaurantLead(name="Restaurant 001"), "expect_authentic": False},
            {"lead": RestaurantLead(name="Fake Eatery Demo"), "expect_authentic": False}
        ]
        
        validation_results = []
        correct_assessments = 0
        
        for i, case in enumerate(test_cases):
            result = self.business_validator.validate_restaurant_authenticity(case["lead"])
            
            is_correct = (
                (case["expect_authentic"] and result.quality != DataQuality.FAKE) or
                (not case["expect_authentic"] and result.quality == DataQuality.FAKE)
            )
            
            if is_correct:
                correct_assessments += 1
            
            validation_results.append({
                'case_index': i,
                'restaurant_name': case["lead"].name,
                'expected_authentic': case["expect_authentic"],
                'result_quality': result.quality.value,
                'result_score': result.score,
                'assessment_correct': is_correct
            })
        
        success = correct_assessments >= len(test_cases) * 0.8  # At least 80% correct
        
        return {
            'success': success,
            'summary': f"Business validation: {correct_assessments}/{len(test_cases)} correct assessments",
            'details': validation_results,
            'accuracy': correct_assessments / len(test_cases) if test_cases else 0
        }
    
    def test_location_validation(self) -> Dict[str, Any]:
        """Test Santa Monica location validation"""
        
        test_cases = [
            # Valid Santa Monica addresses
            {"lead": RestaurantLead(address="101 Santa Monica Blvd, Santa Monica, CA 90401"), "expect_valid": True},
            {"lead": RestaurantLead(address="1234 Wilshire Blvd, Santa Monica, CA 90402"), "expect_valid": True},
            {"lead": RestaurantLead(address="567 Ocean Ave, Santa Monica, CA 90403"), "expect_valid": True},
            
            # Invalid/fake addresses
            {"lead": RestaurantLead(address="123 Test Street, Santa Monica, CA 90401"), "expect_valid": False},
            {"lead": RestaurantLead(address="Sample Address, Santa Monica"), "expect_valid": False},
            {"lead": RestaurantLead(address="Fake Street, Los Angeles, CA 90210"), "expect_valid": False},  # Wrong city
            
            # Edge cases
            {"lead": RestaurantLead(address=""), "expect_valid": False},  # Empty address
            {"lead": RestaurantLead(address="Santa Monica, CA"), "expect_valid": True}  # Partial but valid
        ]
        
        validation_results = []
        correct_assessments = 0
        
        for i, case in enumerate(test_cases):
            result = self.location_validator.validate_santa_monica_location(case["lead"])
            
            is_correct = (
                (case["expect_valid"] and result.status in [ValidationStatus.PASS, ValidationStatus.WARNING]) or
                (not case["expect_valid"] and result.status == ValidationStatus.FAIL)
            )
            
            if is_correct:
                correct_assessments += 1
            
            validation_results.append({
                'case_index': i,
                'address': case["lead"].address,
                'expected_valid': case["expect_valid"],
                'result_status': result.status.value,
                'result_score': result.score,
                'assessment_correct': is_correct
            })
        
        success = correct_assessments >= len(test_cases) * 0.8
        
        return {
            'success': success,
            'summary': f"Location validation: {correct_assessments}/{len(test_cases)} correct assessments",
            'details': validation_results,
            'accuracy': correct_assessments / len(test_cases) if test_cases else 0
        }
    
    def test_phone_validation(self) -> Dict[str, Any]:
        """Test phone number validation"""
        
        test_cases = [
            # Valid LA/Santa Monica area phones
            {"lead": RestaurantLead(phone="(310) 123-4567"), "expect_valid": True},
            {"lead": RestaurantLead(phone="424-555-1234"), "expect_valid": True},
            {"lead": RestaurantLead(phone="310.987.6543"), "expect_valid": True},
            
            # Fake phone patterns
            {"lead": RestaurantLead(phone="(555) 123-4567"), "expect_valid": False},
            {"lead": RestaurantLead(phone="(310) 555-1234"), "expect_valid": False},
            {"lead": RestaurantLead(phone="(000) 000-0000"), "expect_valid": False},
            {"lead": RestaurantLead(phone="123-1234"), "expect_valid": False},  # Too short
            
            # Edge cases
            {"lead": RestaurantLead(phone=""), "expect_valid": False},  # Empty
            {"lead": RestaurantLead(phone="not-a-phone"), "expect_valid": False}  # Invalid format
        ]
        
        validation_results = []
        correct_assessments = 0
        
        for i, case in enumerate(test_cases):
            result = self.phone_validator.validate_phone_number(case["lead"])
            
            is_correct = (
                (case["expect_valid"] and result.status in [ValidationStatus.PASS, ValidationStatus.WARNING]) or
                (not case["expect_valid"] and result.status == ValidationStatus.FAIL)
            )
            
            if is_correct:
                correct_assessments += 1
            
            validation_results.append({
                'case_index': i,
                'phone': case["lead"].phone,
                'expected_valid': case["expect_valid"],
                'result_status': result.status.value,
                'result_score': result.score,
                'assessment_correct': is_correct
            })
        
        success = correct_assessments >= len(test_cases) * 0.8
        
        return {
            'success': success,
            'summary': f"Phone validation: {correct_assessments}/{len(test_cases)} correct assessments",
            'details': validation_results,
            'accuracy': correct_assessments / len(test_cases) if test_cases else 0
        }
    
    def test_email_validation(self) -> Dict[str, Any]:
        """Test email domain validation"""
        
        test_cases = [
            # Valid business emails
            {"lead": RestaurantLead(email="info@restaurant.com"), "expect_valid": True},
            {"lead": RestaurantLead(email="contact@boasteakhouse.com"), "expect_valid": True},
            {"lead": RestaurantLead(email="reservations@thelobster.com"), "expect_valid": True},
            
            # Personal emails (may be valid for small restaurants)
            {"lead": RestaurantLead(email="owner@gmail.com"), "expect_valid": True},
            {"lead": RestaurantLead(email="chef@yahoo.com"), "expect_valid": True},
            
            # Fake/test emails
            {"lead": RestaurantLead(email="test@example.com"), "expect_valid": False},
            {"lead": RestaurantLead(email="fake@test.com"), "expect_valid": False},
            {"lead": RestaurantLead(email="noreply@localhost"), "expect_valid": False},
            
            # Invalid formats
            {"lead": RestaurantLead(email=""), "expect_valid": False},  # Empty
            {"lead": RestaurantLead(email="invalid-email"), "expect_valid": False}  # No @
        ]
        
        validation_results = []
        correct_assessments = 0
        
        for i, case in enumerate(test_cases):
            result = self.email_validator.validate_email_domain(case["lead"])
            
            is_correct = (
                (case["expect_valid"] and result.status in [ValidationStatus.PASS, ValidationStatus.WARNING]) or
                (not case["expect_valid"] and result.status == ValidationStatus.FAIL)
            )
            
            if is_correct:
                correct_assessments += 1
            
            validation_results.append({
                'case_index': i,
                'email': case["lead"].email,
                'expected_valid': case["expect_valid"],
                'result_status': result.status.value,
                'result_score': result.score,
                'assessment_correct': is_correct
            })
        
        success = correct_assessments >= len(test_cases) * 0.8
        
        return {
            'success': success,
            'summary': f"Email validation: {correct_assessments}/{len(test_cases)} correct assessments",
            'details': validation_results,
            'accuracy': correct_assessments / len(test_cases) if test_cases else 0
        }
    
    def test_framework_integration(self) -> Dict[str, Any]:
        """Test full framework integration and consistency"""
        
        # Mixed quality leads for comprehensive testing
        test_leads = [
            # High quality authentic lead
            RestaurantLead(
                name="Boa Steakhouse",
                address="101 Santa Monica Blvd, Santa Monica, CA 90401",
                phone="(310) 899-4466",
                email="info@boasteakhouse.com",
                website="https://boasteakhouse.com",
                cuisine_type="American"
            ),
            
            # Medium quality lead (personal email but otherwise good)
            RestaurantLead(
                name="Local Pizza Place",
                address="1234 Main St, Santa Monica, CA 90402",
                phone="(310) 555-9876",
                email="owner@gmail.com",
                website="https://localpizza.com",
                cuisine_type="Italian"
            ),
            
            # Low quality but not fake
            RestaurantLead(
                name="Restaurant",  # Generic name
                address="Santa Monica, CA",  # Incomplete address
                phone="",  # Missing phone
                email="info@restaurant.biz",
                website="http://restaurant.biz"
            ),
            
            # Fake data (should be rejected)
            RestaurantLead(
                name="Test Restaurant 123",
                address="123 Test Street, Santa Monica, CA 90401",
                phone="(555) 123-4567",
                email="test@example.com",
                website="http://test.example.com"
            )
        ]
        
        # Test batch validation
        validated_leads = self.framework.validate_lead_batch(test_leads)
        
        # Analyze results
        high_quality_count = sum(1 for lead in validated_leads if lead.overall_score >= 0.8)
        authentic_count = sum(1 for lead in validated_leads if lead.is_authentic)
        fake_detected = len(test_leads) - len(validated_leads)  # Assuming strict mode filters fake data
        
        # Get framework report
        report = self.framework.get_validation_report()
        
        integration_results = []
        for i, lead in enumerate(validated_leads):
            integration_results.append({
                'original_index': i,
                'name': lead.name,
                'overall_score': lead.overall_score,
                'is_authentic': lead.is_authentic,
                'validation_count': len(lead.validation_results),
                'has_fake_quality': any(vr.quality == DataQuality.FAKE for vr in lead.validation_results)
            })
        
        # Success criteria
        success = (
            len(validated_leads) >= 2 and  # Should keep at least 2 good leads
            fake_detected >= 1 and  # Should detect at least 1 fake lead
            authentic_count >= 1 and  # At least 1 should be marked authentic
            report['validation_summary']['total_leads_validated'] == len(test_leads)
        )
        
        return {
            'success': success,
            'summary': f"Framework integration: {len(validated_leads)}/{len(test_leads)} leads passed, {authentic_count} authentic",
            'details': {
                'input_leads': len(test_leads),
                'output_leads': len(validated_leads),
                'authentic_count': authentic_count,
                'high_quality_count': high_quality_count,
                'fake_detected': fake_detected,
                'framework_report': report,
                'lead_results': integration_results
            }
        }
    
    def test_performance_validation(self) -> Dict[str, Any]:
        """Test validation framework performance"""
        
        # Create a larger dataset for performance testing
        performance_leads = []
        
        # Generate 50 test leads (mix of real and fake)
        for i in range(50):
            if i % 3 == 0:  # Every 3rd is fake
                lead = RestaurantLead(
                    name=f"Test Restaurant {i:03d}",
                    address=f"123 Test St {i}, Santa Monica, CA 90401",
                    phone=f"(555) {i:03d}-{(i*7)%10000:04d}",
                    email=f"test{i}@example.com",
                    website=f"http://test{i}.example.com"
                )
            else:  # Real-looking data
                lead = RestaurantLead(
                    name=f"Restaurant {i}",
                    address=f"{100+i} Main St, Santa Monica, CA 90{401+(i%5)}",
                    phone=f"(310) {200+(i%8):03d}-{1000+(i*13)%9000:04d}",
                    email=f"info@restaurant{i}.com",
                    website=f"https://restaurant{i}.com",
                    cuisine_type="American" if i % 2 == 0 else "Italian"
                )
            
            performance_leads.append(lead)
        
        # Time the validation process
        start_time = time.time()
        validated_leads = self.framework.validate_lead_batch(performance_leads)
        validation_time = time.time() - start_time
        
        # Performance metrics
        leads_per_second = len(performance_leads) / validation_time if validation_time > 0 else 0
        avg_time_per_lead = validation_time / len(performance_leads) if performance_leads else 0
        
        # Quality metrics
        fake_detection_count = sum(1 for lead in validated_leads 
                                 if any(vr.quality == DataQuality.FAKE for vr in lead.validation_results))
        
        # Success criteria: reasonable performance and good detection
        success = (
            validation_time < 60 and  # Should complete within 60 seconds
            leads_per_second > 0.5 and  # At least 0.5 leads per second
            fake_detection_count >= 5  # Should detect at least some fake leads
        )
        
        return {
            'success': success,
            'summary': f"Performance: {validation_time:.2f}s for {len(performance_leads)} leads ({leads_per_second:.2f} leads/sec)",
            'details': {
                'total_leads': len(performance_leads),
                'validation_time': validation_time,
                'leads_per_second': leads_per_second,
                'avg_time_per_lead': avg_time_per_lead,
                'output_leads': len(validated_leads),
                'fake_detected': fake_detection_count,
                'memory_efficient': True  # Assume memory efficient for now
            }
        }
    
    def _generate_test_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'pass_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'total_time_seconds': total_time,
                'timestamp': datetime.now().isoformat()
            },
            'test_results': self.test_results,
            'validation_framework_status': 'PASS' if passed_tests == total_tests else 'FAIL',
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [result for result in self.test_results if not result['success']]
        
        if not failed_tests:
            recommendations.append("All tests passed! The validation framework is ready for production use.")
        else:
            for failed_test in failed_tests:
                test_name = failed_test['test_name']
                
                if 'fake_data_detection' in test_name:
                    recommendations.append("Improve fake data detection patterns and scoring algorithms")
                elif 'real_data_acceptance' in test_name:
                    recommendations.append("Adjust validation thresholds to reduce false positives")
                elif 'technical_debt_detection' in test_name:
                    recommendations.append("Enhance technical debt monitoring patterns")
                elif 'performance' in test_name:
                    recommendations.append("Optimize validation algorithms for better performance")
                else:
                    recommendations.append(f"Review and fix issues in {test_name}")
        
        return recommendations
    
    def save_test_report(self, filename: str = None) -> str:
        """Save test report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_framework_test_report_{timestamp}.json"
        
        # Run tests if not already run
        if not self.test_results:
            self.run_all_tests()
        
        report = self._generate_test_report(0)  # Total time not available if called separately
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Test report saved to {filename}")
        return filename


def main():
    """Main function for running validation tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validation Framework Testing Suite')
    parser.add_argument('--output', '-o', help='Output file for test report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    tester = ValidationFrameworkTester()
    
    try:
        print("Starting comprehensive validation framework tests...")
        report = tester.run_all_tests()
        
        # Print summary
        summary = report['test_summary']
        print(f"\nTest Results Summary:")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Pass Rate: {summary['pass_rate']:.1%}")
        print(f"Total Time: {summary['total_time_seconds']:.2f}s")
        print(f"Overall Status: {report['validation_framework_status']}")
        
        # Print failed tests
        failed_tests = [r for r in report['test_results'] if not r['success']]
        if failed_tests:
            print(f"\nFailed Tests:")
            for test in failed_tests:
                print(f"- {test['test_name']}: {test['summary']}")
        
        # Print recommendations
        if report['recommendations']:
            print(f"\nRecommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Save report
        if args.output:
            tester.save_test_report(args.output)
            print(f"\nDetailed report saved to: {args.output}")
        
        # Exit code based on results
        return 0 if report['validation_framework_status'] == 'PASS' else 1
        
    except Exception as e:
        print(f"Test suite failed with error: {e}")
        return 2


if __name__ == "__main__":
    exit(main())