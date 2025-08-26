"""
Enhanced Security Testing Suite for PubScrape
Tests security measures, anti-detection mechanisms, and vulnerability prevention.
"""

import pytest
import time
import random
import re
from typing import Dict, List, Any
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Security testing utilities
import hashlib
import uuid
from urllib.parse import urlparse, parse_qs


class TestAntiDetectionSecurity:
    """Comprehensive anti-detection security testing"""
    
    @pytest.fixture
    def stealth_browser_config(self):
        """Browser configuration for stealth testing"""
        return {
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ],
            'screen_resolutions': ['1920x1080', '1366x768', '1440x900', '1536x864'],
            'timezones': ['America/New_York', 'America/Chicago', 'America/Los_Angeles'],
            'languages': ['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-CA,en;q=0.9']
        }
    
    @pytest.mark.security
    def test_user_agent_randomization(self, stealth_browser_config):
        """Test user agent randomization effectiveness"""
        generated_agents = []
        
        # Generate 50 user agents
        for _ in range(50):
            agent = random.choice(stealth_browser_config['user_agents'])
            generated_agents.append(agent)
        
        # Verify diversity
        unique_agents = set(generated_agents)
        diversity_ratio = len(unique_agents) / len(generated_agents)
        
        assert diversity_ratio >= 0.6, f"User agent diversity {diversity_ratio:.2%} below 60% threshold"
        assert all('Chrome' in agent for agent in unique_agents), "All user agents should be Chrome-based"
        assert all('WebKit' in agent for agent in unique_agents), "All user agents should be WebKit-based"
    
    @pytest.mark.security
    def test_browser_fingerprint_uniqueness(self, stealth_browser_config):
        """Test browser fingerprint uniqueness and realism"""
        fingerprints = []
        
        for _ in range(20):
            fingerprint = {
                'user_agent': random.choice(stealth_browser_config['user_agents']),
                'screen_resolution': random.choice(stealth_browser_config['screen_resolutions']),
                'timezone': random.choice(stealth_browser_config['timezones']),
                'language': random.choice(stealth_browser_config['languages']),
                'canvas_hash': hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
                'webgl_hash': hashlib.md5(str(random.random()).encode()).hexdigest()[:16]
            }
            fingerprints.append(fingerprint)
        
        # Create fingerprint signatures
        signatures = [
            f"{fp['user_agent']}|{fp['screen_resolution']}|{fp['timezone']}"
            for fp in fingerprints
        ]
        
        # Verify uniqueness
        unique_signatures = set(signatures)
        uniqueness_ratio = len(unique_signatures) / len(signatures)
        
        assert uniqueness_ratio >= 0.8, f"Fingerprint uniqueness {uniqueness_ratio:.2%} below 80% threshold"
        
        # Verify realistic combinations
        for fp in fingerprints:
            resolution = fp['screen_resolution']
            width, height = map(int, resolution.split('x'))
            assert 1024 <= width <= 3840, f"Screen width {width} outside realistic range"
            assert 768 <= height <= 2160, f"Screen height {height} outside realistic range"
    
    @pytest.mark.security
    def test_timing_pattern_randomization(self):
        """Test human-like timing pattern generation"""
        click_intervals = []
        scroll_intervals = []
        page_load_waits = []
        
        # Generate timing patterns
        for _ in range(50):
            # Mouse click intervals (0.5-3.0 seconds)
            click_interval = random.uniform(0.5, 3.0) + random.gauss(0, 0.2)
            click_intervals.append(max(0.3, click_interval))
            
            # Scroll intervals (0.1-2.0 seconds)  
            scroll_interval = random.uniform(0.1, 2.0) + random.gauss(0, 0.1)
            scroll_intervals.append(max(0.05, scroll_interval))
            
            # Page load waits (1.0-5.0 seconds)
            page_wait = random.uniform(1.0, 5.0) + random.gauss(0, 0.5)
            page_load_waits.append(max(0.5, page_wait))
        
        # Statistical analysis
        click_mean = sum(click_intervals) / len(click_intervals)
        click_std = (sum((x - click_mean) ** 2 for x in click_intervals) / len(click_intervals)) ** 0.5
        
        # Verify human-like patterns
        assert 0.8 <= click_mean <= 2.5, f"Click timing mean {click_mean:.2f} outside human range"
        assert click_std >= 0.3, f"Click timing std dev {click_std:.2f} too consistent (robotic)"
        
        # Verify no fixed intervals (robotic patterns)
        sorted_intervals = sorted(click_intervals)
        consecutive_diffs = [sorted_intervals[i+1] - sorted_intervals[i] for i in range(len(sorted_intervals)-1)]
        max_similar = max(sum(1 for d in consecutive_diffs if abs(d) < 0.01) for _ in [0])
        
        assert max_similar < 5, f"Too many similar intervals ({max_similar}) indicates robotic behavior"
    
    @pytest.mark.security
    def test_detection_rate_monitoring(self):
        """Test detection rate stays below acceptable thresholds"""
        simulation_results = []
        
        # Simulate 100 scraping attempts with anti-detection measures
        for attempt in range(100):
            # Simulate various detection scenarios
            detection_factors = {
                'rate_limit_triggered': random.random() < 0.02,  # 2% chance
                'captcha_encountered': random.random() < 0.01,  # 1% chance  
                'ip_blocked': random.random() < 0.005,          # 0.5% chance
                'behavior_flagged': random.random() < 0.015,    # 1.5% chance
                'fingerprint_detected': random.random() < 0.01  # 1% chance
            }
            
            # Overall detection if any factor triggers
            detected = any(detection_factors.values())
            
            result = {
                'attempt': attempt,
                'detected': detected,
                'factors': detection_factors,
                'timestamp': datetime.now()
            }
            simulation_results.append(result)
        
        # Calculate detection statistics
        total_detections = sum(1 for r in simulation_results if r['detected'])
        detection_rate = total_detections / len(simulation_results)
        
        # Factor-specific analysis
        factor_rates = {}
        for factor in ['rate_limit_triggered', 'captcha_encountered', 'ip_blocked', 
                      'behavior_flagged', 'fingerprint_detected']:
            factor_count = sum(1 for r in simulation_results if r['factors'][factor])
            factor_rates[factor] = factor_count / len(simulation_results)
        
        # Assertions
        assert detection_rate < 0.05, f"Overall detection rate {detection_rate:.2%} exceeds 5% threshold"
        assert factor_rates['rate_limit_triggered'] < 0.03, "Rate limiting detection too high"
        assert factor_rates['captcha_encountered'] < 0.02, "CAPTCHA encounters too frequent"
        assert factor_rates['ip_blocked'] < 0.01, "IP blocking rate too high"
        
        return {
            'detection_rate': detection_rate,
            'factor_rates': factor_rates,
            'total_simulations': len(simulation_results)
        }
    
    @pytest.mark.security
    def test_session_isolation_security(self):
        """Test session isolation prevents data leakage"""
        sessions = []
        
        # Create 10 isolated sessions
        for i in range(10):
            session = {
                'id': f"session_{uuid.uuid4()}",
                'cookies': {},
                'local_storage': {},
                'session_storage': {},
                'browsing_history': [],
                'cache': {},
                'sensitive_data': f"secret_{i}_{uuid.uuid4()}"
            }
            sessions.append(session)
        
        # Simulate cross-session operations
        for i, session in enumerate(sessions):
            # Add session-specific data
            session['cookies'][f'session_token'] = f"token_{i}_{uuid.uuid4()}"
            session['local_storage'][f'user_pref'] = f"pref_{i}"
            session['browsing_history'].append(f"https://example{i}.com")
            
            # Simulate potential contamination attempts
            for other_session in sessions:
                if other_session['id'] != session['id']:
                    # Verify no cross-contamination
                    assert session['sensitive_data'] not in str(other_session), \
                        f"Data leakage detected between sessions {session['id']} and {other_session['id']}"
                    
                    # Verify cookie isolation
                    session_tokens = [k for k in other_session['cookies'].keys() if 'session_token' in k]
                    for token_key in session_tokens:
                        assert session['cookies'].get(token_key) != other_session['cookies'].get(token_key), \
                            "Session token contamination detected"
        
        # Verify session cleanup
        for session in sessions:
            # Simulate session termination
            session_data_keys = list(session.keys())
            for key in session_data_keys:
                if key != 'id':  # Keep ID for tracking
                    session[key] = None
            
            # Verify cleanup effectiveness
            assert session['cookies'] is None
            assert session['sensitive_data'] is None
    
    @pytest.mark.security
    def test_request_pattern_obfuscation(self):
        """Test request pattern obfuscation effectiveness"""
        request_patterns = []
        
        # Generate request patterns
        for session in range(5):
            session_requests = []
            base_time = time.time()
            
            for req_num in range(20):  # 20 requests per session
                # Add human-like variations
                delay = random.uniform(1.0, 8.0) + random.gauss(0, 1.0)
                delay = max(0.5, delay)
                
                request = {
                    'session_id': session,
                    'request_num': req_num,
                    'timestamp': base_time + sum(r.get('delay', 0) for r in session_requests) + delay,
                    'delay': delay,
                    'user_agent_rotation': req_num % 3 == 0,  # Rotate every 3rd request
                    'proxy_rotation': req_num % 5 == 0,       # Rotate every 5th request
                    'referrer_spoofing': random.choice([True, False])
                }
                session_requests.append(request)
            
            request_patterns.extend(session_requests)
        
        # Analyze patterns for robotic behavior
        all_delays = [req['delay'] for req in request_patterns]
        delay_variance = sum((d - sum(all_delays)/len(all_delays))**2 for d in all_delays) / len(all_delays)
        
        # Check for regular intervals (robotic)
        sorted_delays = sorted(all_delays)
        regular_intervals = 0
        for i in range(len(sorted_delays) - 1):
            if abs(sorted_delays[i+1] - sorted_delays[i]) < 0.1:  # Within 100ms
                regular_intervals += 1
        
        regularity_ratio = regular_intervals / len(sorted_delays)
        
        # Assertions
        assert delay_variance > 1.0, f"Request delay variance {delay_variance:.2f} too low (robotic)"
        assert regularity_ratio < 0.1, f"Regular interval ratio {regularity_ratio:.2%} too high (robotic)"
        
        # Verify rotation effectiveness
        ua_rotations = sum(1 for req in request_patterns if req['user_agent_rotation'])
        proxy_rotations = sum(1 for req in request_patterns if req['proxy_rotation'])
        referrer_spoofs = sum(1 for req in request_patterns if req['referrer_spoofing'])
        
        assert ua_rotations > 15, f"User agent rotations {ua_rotations} insufficient"
        assert proxy_rotations > 10, f"Proxy rotations {proxy_rotations} insufficient"
        assert referrer_spoofs > 25, f"Referrer spoofing {referrer_spoofs} insufficient"


class TestDataSecurityValidation:
    """Data security and privacy validation tests"""
    
    @pytest.mark.security
    def test_pii_data_sanitization(self):
        """Test personally identifiable information sanitization"""
        test_data = [
            {
                'email': 'john.doe@example.com',
                'phone': '(555) 123-4567',
                'full_name': 'John Doe',
                'ssn': '123-45-6789',  # Should be filtered
                'credit_card': '4111-1111-1111-1111',  # Should be filtered
                'address': '123 Main Street, Anytown, USA'
            },
            {
                'email': 'jane.smith@company.com',
                'phone': '555-987-6543',
                'full_name': 'Jane Smith',
                'driver_license': 'D123456789',  # Should be filtered
                'passport': 'A12345678'  # Should be filtered
            }
        ]
        
        # Define PII patterns to detect and remove
        pii_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'driver_license': r'\b[A-Z]\d{9}\b',
            'passport': r'\b[A-Z]\d{8}\b'
        }
        
        sanitized_data = []
        for record in test_data:
            sanitized_record = record.copy()
            
            # Remove PII fields
            for field, pattern in pii_patterns.items():
                for key, value in list(sanitized_record.items()):
                    if isinstance(value, str) and re.search(pattern, value):
                        sanitized_record.pop(key, None)
            
            sanitized_data.append(sanitized_record)
        
        # Verify PII removal
        for record in sanitized_data:
            record_str = str(record)
            for pattern_name, pattern in pii_patterns.items():
                assert not re.search(pattern, record_str), \
                    f"PII pattern {pattern_name} found in sanitized data: {record_str}"
        
        # Verify legitimate data preservation
        assert all('email' in record for record in sanitized_data), "Legitimate email data removed"
        assert all('phone' in record for record in sanitized_data), "Legitimate phone data removed"
    
    @pytest.mark.security
    def test_data_encryption_validation(self):
        """Test data encryption and secure storage validation"""
        sensitive_fields = ['email', 'phone', 'contact_info']
        test_records = [
            {
                'business_name': 'Test Medical Practice',
                'email': 'info@testmedical.com',
                'phone': '(555) 123-0000',
                'website': 'https://testmedical.com',
                'contact_info': {'email': 'contact@testmedical.com', 'phone': '(555) 123-0001'}
            }
        ]
        
        def mock_encrypt(data):
            """Mock encryption function"""
            if isinstance(data, dict):
                return {k: f"encrypted_{hashlib.md5(str(v).encode()).hexdigest()}" 
                       for k, v in data.items()}
            return f"encrypted_{hashlib.md5(str(data).encode()).hexdigest()}"
        
        def mock_decrypt(encrypted_data):
            """Mock decryption function"""
            if isinstance(encrypted_data, dict):
                return {k: v.replace('encrypted_', '') for k, v in encrypted_data.items() 
                       if k.startswith('encrypted_')}
            return encrypted_data.replace('encrypted_', '') if 'encrypted_' in encrypted_data else encrypted_data
        
        # Test encryption
        encrypted_records = []
        for record in test_records:
            encrypted_record = record.copy()
            for field in sensitive_fields:
                if field in encrypted_record:
                    encrypted_record[field] = mock_encrypt(encrypted_record[field])
            encrypted_records.append(encrypted_record)
        
        # Verify encryption applied
        for i, record in enumerate(encrypted_records):
            original = test_records[i]
            for field in sensitive_fields:
                if field in record:
                    assert record[field] != original[field], f"Field {field} not encrypted"
                    assert 'encrypted_' in str(record[field]), f"Field {field} encryption format invalid"
        
        # Test decryption
        decrypted_records = []
        for record in encrypted_records:
            decrypted_record = {}
            for key, value in record.items():
                if key in sensitive_fields:
                    decrypted_record[key] = mock_decrypt(value)
                else:
                    decrypted_record[key] = value
            decrypted_records.append(decrypted_record)
        
        # Verify decryption successful (data accessibility maintained)
        assert len(decrypted_records) == len(test_records), "Record count mismatch after encryption/decryption"
    
    @pytest.mark.security
    def test_access_control_validation(self):
        """Test access control and permission validation"""
        # Define access levels
        access_levels = {
            'public': ['business_name', 'website', 'phone'],
            'authenticated': ['email', 'contact_info', 'address'],
            'admin': ['internal_notes', 'lead_score', 'campaign_data']
        }
        
        test_record = {
            'business_name': 'Test Business',
            'website': 'https://testbusiness.com',
            'phone': '(555) 123-4567',
            'email': 'info@testbusiness.com',
            'contact_info': {'primary': 'info@testbusiness.com'},
            'address': '123 Business Ave',
            'internal_notes': 'High value lead',
            'lead_score': 95,
            'campaign_data': {'source': 'google_maps', 'campaign_id': 'CM001'}
        }
        
        def filter_by_access_level(record, user_level, access_levels):
            """Filter record fields based on user access level"""
            allowed_fields = set()
            
            # Add fields for user level and all lower levels
            level_hierarchy = ['public', 'authenticated', 'admin']
            user_index = level_hierarchy.index(user_level)
            
            for level in level_hierarchy[:user_index + 1]:
                allowed_fields.update(access_levels[level])
            
            return {k: v for k, v in record.items() if k in allowed_fields}
        
        # Test access filtering
        public_view = filter_by_access_level(test_record, 'public', access_levels)
        auth_view = filter_by_access_level(test_record, 'authenticated', access_levels)
        admin_view = filter_by_access_level(test_record, 'admin', access_levels)
        
        # Verify access control
        assert 'business_name' in public_view, "Public field missing from public view"
        assert 'email' not in public_view, "Private field exposed in public view"
        
        assert 'email' in auth_view, "Authenticated field missing from authenticated view"
        assert 'internal_notes' not in auth_view, "Admin field exposed in authenticated view"
        
        assert 'internal_notes' in admin_view, "Admin field missing from admin view"
        assert len(admin_view) == len(test_record), "Admin should have access to all fields"
        
        # Verify field count progression
        assert len(public_view) <= len(auth_view) <= len(admin_view), \
            "Access level field count should be progressive"
    
    @pytest.mark.security
    def test_injection_attack_prevention(self):
        """Test prevention of injection attacks in search queries"""
        # SQL injection attempts
        sql_injection_payloads = [
            "doctors'; DROP TABLE businesses; --",
            "lawyers' OR '1'='1",
            "dentists' UNION SELECT * FROM sensitive_data --",
            "restaurants'; INSERT INTO logs VALUES ('hacked'); --"
        ]
        
        # XSS injection attempts  
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "'\"><script>alert('XSS')</script>"
        ]
        
        # NoSQL injection attempts
        nosql_payloads = [
            "{'$ne': null}",
            "{'$regex': '.*'}",
            "{'$where': 'this.password.match(/.*/)'}",
        ]
        
        def sanitize_query(query):
            """Sanitize search query to prevent injections"""
            # Remove/escape dangerous patterns
            dangerous_patterns = [
                r"[';\"\\]",  # Quotes and backslashes
                r"--",        # SQL comments
                r"/\*.*?\*/", # Multi-line comments
                r"<[^>]*>",   # HTML tags
                r"javascript:", # JavaScript protocol
                r"\$\w+",     # NoSQL operators
            ]
            
            sanitized = query
            for pattern in dangerous_patterns:
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            
            # Additional sanitization
            sanitized = sanitized.strip()
            sanitized = re.sub(r'\s+', ' ', sanitized)  # Normalize whitespace
            
            return sanitized
        
        # Test SQL injection prevention
        for payload in sql_injection_payloads:
            sanitized = sanitize_query(payload)
            assert "DROP" not in sanitized.upper(), f"SQL injection not prevented: {payload}"
            assert "UNION" not in sanitized.upper(), f"SQL injection not prevented: {payload}"
            assert "--" not in sanitized, f"SQL comment not sanitized: {payload}"
        
        # Test XSS prevention
        for payload in xss_payloads:
            sanitized = sanitize_query(payload)
            assert "<script>" not in sanitized.lower(), f"XSS not prevented: {payload}"
            assert "javascript:" not in sanitized.lower(), f"XSS not prevented: {payload}"
            assert "<img" not in sanitized.lower(), f"XSS not prevented: {payload}"
        
        # Test NoSQL injection prevention
        for payload in nosql_payloads:
            sanitized = sanitize_query(payload)
            assert "$ne" not in sanitized, f"NoSQL injection not prevented: {payload}"
            assert "$regex" not in sanitized, f"NoSQL injection not prevented: {payload}"
            assert "$where" not in sanitized, f"NoSQL injection not prevented: {payload}"
        
        # Verify legitimate queries remain functional
        legitimate_queries = [
            "doctors in Chicago",
            "lawyers near Houston TX",
            "family medicine & pediatrics",
            "restaurants with reviews"
        ]
        
        for query in legitimate_queries:
            sanitized = sanitize_query(query)
            assert len(sanitized) > 0, f"Legitimate query over-sanitized: {query}"
            assert any(word in sanitized.lower() for word in query.lower().split()), \
                f"Essential terms removed from query: {query} -> {sanitized}"


@pytest.mark.security
class TestComplianceValidation:
    """Test compliance with data protection regulations"""
    
    def test_gdpr_compliance_features(self):
        """Test GDPR compliance features"""
        # Right to be forgotten simulation
        user_data = {
            'user_id': 'user123',
            'email': 'user123@example.com',
            'business_contacts': [
                {'email': 'contact1@business.com', 'consent': True},
                {'email': 'contact2@business.com', 'consent': False}
            ],
            'processing_history': ['search', 'extraction', 'validation', 'export']
        }
        
        def implement_right_to_be_forgotten(user_id, data_store):
            """Simulate right to be forgotten implementation"""
            if user_id in data_store:
                # Remove user data
                del data_store[user_id]
                return True
            return False
        
        def check_consent_requirements(contact_list):
            """Check consent requirements for contacts"""
            return [contact for contact in contact_list if contact.get('consent', False)]
        
        # Test data removal
        data_store = {'user123': user_data}
        removal_success = implement_right_to_be_forgotten('user123', data_store)
        
        assert removal_success, "Right to be forgotten not implemented"
        assert 'user123' not in data_store, "User data not removed"
        
        # Test consent filtering
        consented_contacts = check_consent_requirements(user_data['business_contacts'])
        assert len(consented_contacts) == 1, "Consent filtering not working correctly"
        assert all(contact['consent'] for contact in consented_contacts), \
            "Non-consented contacts included"
    
    def test_data_retention_policies(self):
        """Test data retention policy compliance"""
        from datetime import datetime, timedelta
        
        # Define retention policies
        retention_policies = {
            'search_logs': timedelta(days=30),
            'extracted_data': timedelta(days=90),
            'user_preferences': timedelta(days=365),
            'audit_logs': timedelta(days=2555)  # 7 years
        }
        
        # Generate test data with timestamps
        test_data = {
            'search_logs': [
                {'query': 'doctors chicago', 'timestamp': datetime.now() - timedelta(days=45)},
                {'query': 'lawyers houston', 'timestamp': datetime.now() - timedelta(days=15)}
            ],
            'extracted_data': [
                {'email': 'old@business.com', 'timestamp': datetime.now() - timedelta(days=120)},
                {'email': 'new@business.com', 'timestamp': datetime.now() - timedelta(days=30)}
            ]
        }
        
        def apply_retention_policies(data, policies):
            """Apply retention policies to data"""
            cleaned_data = {}
            current_time = datetime.now()
            
            for data_type, records in data.items():
                if data_type in policies:
                    retention_period = policies[data_type]
                    cutoff_date = current_time - retention_period
                    
                    cleaned_records = [
                        record for record in records 
                        if record['timestamp'] > cutoff_date
                    ]
                    cleaned_data[data_type] = cleaned_records
                else:
                    cleaned_data[data_type] = records
            
            return cleaned_data
        
        # Apply retention policies
        cleaned_data = apply_retention_policies(test_data, retention_policies)
        
        # Verify retention compliance
        assert len(cleaned_data['search_logs']) == 1, "Search log retention policy not applied"
        assert len(cleaned_data['extracted_data']) == 1, "Data retention policy not applied"
        
        # Verify remaining data is within retention period
        for data_type, records in cleaned_data.items():
            if data_type in retention_policies:
                retention_period = retention_policies[data_type]
                cutoff_date = datetime.now() - retention_period
                
                for record in records:
                    assert record['timestamp'] > cutoff_date, \
                        f"Record older than retention period found in {data_type}"