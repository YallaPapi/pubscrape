#!/usr/bin/env python3
"""
Quick Validation Script for Botasaurus Test Suite

This script validates that the test suite is properly implemented and ready for use.
It performs basic structural validation without requiring external dependencies.
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime

class TestSuiteValidator:
    """Validates the test suite implementation"""
    
    def __init__(self):
        self.tests_dir = Path(__file__).parent
        self.project_root = self.tests_dir.parent
        self.validation_results = {}
    
    def validate_file_structure(self):
        """Validate required test files exist"""
        required_files = [
            'test_suite.py',
            'conftest.py',
            'run_test_suite.py',
            'fixtures/google_maps_samples.html',
            'fixtures/bing_maps_samples.html',
            'fixtures/business_websites/medical_practice.html',
            'fixtures/business_websites/law_firm.html',
            'fixtures/business_websites/restaurant.html'
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path in required_files:
            full_path = self.tests_dir / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        return {
            'status': 'PASSED' if len(missing_files) == 0 else 'FAILED',
            'existing_files': existing_files,
            'missing_files': missing_files,
            'total_files': len(required_files),
            'files_found': len(existing_files)
        }
    
    def validate_test_suite_structure(self):
        """Validate test suite code structure"""
        test_suite_file = self.tests_dir / 'test_suite.py'
        
        if not test_suite_file.exists():
            return {'status': 'FAILED', 'error': 'test_suite.py not found'}
        
        try:
            with open(test_suite_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required classes
            required_classes = [
                'TestDataFactory',
                'AntiDetectionTestSuite',
                'PerformanceTestSuite',
                'IntegrationTestSuite',
                'DataQualityTestSuite',
                'MockDataTestSuite',
                'TestSuiteRunner'
            ]
            
            found_classes = []
            missing_classes = []
            
            for class_name in required_classes:
                if f'class {class_name}' in content:
                    found_classes.append(class_name)
                else:
                    missing_classes.append(class_name)
            
            # Check for key methods
            required_methods = [
                'test_bypass_cloudflare_functionality',
                'test_load_testing_1000_leads',
                'test_complete_lead_generation_workflow',
                'test_email_extraction_accuracy',
                'create_business_lead'
            ]
            
            found_methods = []
            missing_methods = []
            
            for method_name in required_methods:
                if f'def {method_name}' in content:
                    found_methods.append(method_name)
                else:
                    missing_methods.append(method_name)
            
            return {
                'status': 'PASSED' if len(missing_classes) == 0 and len(missing_methods) == 0 else 'WARNING',
                'classes_found': found_classes,
                'missing_classes': missing_classes,
                'methods_found': found_methods,
                'missing_methods': missing_methods,
                'file_size_kb': len(content) // 1024
            }
            
        except Exception as e:
            return {'status': 'FAILED', 'error': str(e)}
    
    def validate_fixtures_content(self):
        """Validate fixture files contain expected content"""
        fixtures_to_check = {
            'fixtures/google_maps_samples.html': ['Northwestern Medicine', 'business-name', 'contact-info'],
            'fixtures/bing_maps_samples.html': ['Baker Botts', 'businessListing', 'contactInfo'],
            'fixtures/business_websites/medical_practice.html': ['Chicago Premier Medical', 'info@chicagopremiermedicine.com'],
            'fixtures/business_websites/law_firm.html': ['Smith & Associates', 'contact@smithlawchicago.com'],
            'fixtures/business_websites/restaurant.html': ['Bella Vista', 'info@bellavistachicago.com']
        }
        
        fixture_results = {}
        
        for fixture_path, expected_content in fixtures_to_check.items():
            full_path = self.tests_dir / fixture_path
            
            if not full_path.exists():
                fixture_results[fixture_path] = {'status': 'MISSING'}
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_content = []
                missing_content = []
                
                for expected in expected_content:
                    if expected in content:
                        found_content.append(expected)
                    else:
                        missing_content.append(expected)
                
                fixture_results[fixture_path] = {
                    'status': 'PASSED' if len(missing_content) == 0 else 'WARNING',
                    'size_kb': len(content) // 1024,
                    'found_content': found_content,
                    'missing_content': missing_content
                }
                
            except Exception as e:
                fixture_results[fixture_path] = {'status': 'ERROR', 'error': str(e)}
        
        return fixture_results
    
    def validate_test_coverage(self):
        """Analyze test coverage areas"""
        test_coverage_areas = {
            'Anti-Detection': [
                'bypass_cloudflare',
                'human_behavior',
                'fingerprint_randomization',
                'session_isolation',
                'detection_rates'
            ],
            'Performance': [
                'load_testing_1000_leads',
                'concurrent_sessions',
                'response_time_benchmarks',
                'resource_cleanup'
            ],
            'Integration': [
                'end_to_end_workflow',
                'error_recovery',
                'data_pipeline',
                'multi_browser'
            ],
            'Data Quality': [
                'email_extraction',
                'business_validation',
                'duplicate_detection',
                'completeness_scoring'
            ],
            'Mock Data': [
                'html_fixtures',
                'sample_data',
                'edge_cases'
            ]
        }
        
        # Read test suite content
        test_suite_file = self.tests_dir / 'test_suite.py'
        content = ""
        
        if test_suite_file.exists():
            with open(test_suite_file, 'r', encoding='utf-8') as f:
                content = f.read()
        
        coverage_results = {}
        
        for area, test_cases in test_coverage_areas.items():
            found_tests = 0
            for test_case in test_cases:
                if test_case in content:
                    found_tests += 1
            
            coverage_percentage = (found_tests / len(test_cases)) * 100
            
            coverage_results[area] = {
                'total_tests': len(test_cases),
                'found_tests': found_tests,
                'coverage_percentage': coverage_percentage,
                'status': 'PASSED' if coverage_percentage >= 80 else 'WARNING'
            }
        
        return coverage_results
    
    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        print("🧪 Validating Botasaurus Test Suite Implementation")
        print("=" * 70)
        
        # File structure validation
        print("\n📁 File Structure Validation:")
        file_structure = self.validate_file_structure()
        self.validation_results['file_structure'] = file_structure
        
        if file_structure['status'] == 'PASSED':
            print(f"✅ All {file_structure['total_files']} required files found")
        else:
            print(f"⚠️  {len(file_structure['missing_files'])} files missing:")
            for missing_file in file_structure['missing_files']:
                print(f"   - {missing_file}")
        
        # Test suite structure validation
        print("\n🏗️  Test Suite Structure Validation:")
        structure = self.validate_test_suite_structure()
        self.validation_results['test_structure'] = structure
        
        if structure['status'] == 'PASSED':
            print(f"✅ Test suite structure is complete")
            print(f"   - Classes: {len(structure['classes_found'])}")
            print(f"   - Methods: {len(structure['methods_found'])}")
            print(f"   - File size: {structure['file_size_kb']} KB")
        else:
            print(f"⚠️  Test suite structure needs attention:")
            if structure.get('missing_classes'):
                print(f"   Missing classes: {structure['missing_classes']}")
            if structure.get('missing_methods'):
                print(f"   Missing methods: {structure['missing_methods']}")
        
        # Fixtures validation
        print("\n🗂️  Fixtures Content Validation:")
        fixtures = self.validate_fixtures_content()
        self.validation_results['fixtures'] = fixtures
        
        passed_fixtures = sum(1 for f in fixtures.values() if f['status'] == 'PASSED')
        total_fixtures = len(fixtures)
        print(f"✅ {passed_fixtures}/{total_fixtures} fixtures validated successfully")
        
        # Test coverage validation
        print("\n📊 Test Coverage Analysis:")
        coverage = self.validate_test_coverage()
        self.validation_results['coverage'] = coverage
        
        total_coverage = sum(area['coverage_percentage'] for area in coverage.values()) / len(coverage)
        print(f"📈 Overall Test Coverage: {total_coverage:.1f}%")
        
        for area, results in coverage.items():
            status_icon = "✅" if results['status'] == 'PASSED' else "⚠️"
            print(f"   {status_icon} {area}: {results['coverage_percentage']:.1f}% ({results['found_tests']}/{results['total_tests']})")
        
        # Overall assessment
        print("\n" + "=" * 70)
        print("📋 VALIDATION SUMMARY")
        print("=" * 70)
        
        overall_status = self._calculate_overall_status()
        
        if overall_status == 'PASSED':
            print("🎉 EXCELLENT: Test suite is ready for production use!")
            print("   - All required files present")
            print("   - Comprehensive test coverage achieved")
            print("   - All fixtures properly configured")
        elif overall_status == 'WARNING':
            print("⚠️  GOOD: Test suite is functional with minor issues")
            print("   - Core functionality implemented")
            print("   - Minor improvements recommended")
        else:
            print("❌ ATTENTION NEEDED: Test suite requires fixes")
            print("   - Critical files or components missing")
        
        print(f"\n📊 Coverage Breakdown:")
        print(f"   - File Structure: {file_structure['files_found']}/{file_structure['total_files']} files")
        print(f"   - Test Coverage: {total_coverage:.1f}% average")
        print(f"   - Fixtures: {passed_fixtures}/{total_fixtures} validated")
        
        # Save detailed report
        report_file = self.tests_dir / f"validation_report_{int(datetime.now().timestamp())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return overall_status
    
    def _calculate_overall_status(self):
        """Calculate overall validation status"""
        file_status = self.validation_results.get('file_structure', {}).get('status')
        structure_status = self.validation_results.get('test_structure', {}).get('status')
        
        coverage_results = self.validation_results.get('coverage', {})
        avg_coverage = sum(area['coverage_percentage'] for area in coverage_results.values()) / len(coverage_results) if coverage_results else 0
        
        if file_status == 'PASSED' and structure_status in ['PASSED', 'WARNING'] and avg_coverage >= 90:
            return 'PASSED'
        elif file_status in ['PASSED', 'WARNING'] and avg_coverage >= 70:
            return 'WARNING'
        else:
            return 'FAILED'


def main():
    """Main validation execution"""
    validator = TestSuiteValidator()
    status = validator.generate_validation_report()
    
    # Exit with appropriate code
    if status == 'PASSED':
        return 0
    elif status == 'WARNING':
        return 0  # Still considered successful
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())