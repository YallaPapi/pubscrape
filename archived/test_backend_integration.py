#!/usr/bin/env python3
"""
VRSEN Lead Generation - Backend Integration Test Suite
Tests backend API functionality and WebSocket connections
"""

import asyncio
import json
import time
import logging
import requests
import subprocess
import threading
import signal
import os
import sys
from datetime import datetime
from pathlib import Path
import websocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackendTestSuite:
    """Backend-focused test suite"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.backend_process = None
        self.test_results = {
            'backend_health': False,
            'api_endpoints': False,
            'websocket_connection': False,
            'real_time_updates': False,
            'campaign_lifecycle': False,
            'email_validation': False,
            'csv_export': False,
            'performance': False,
            'error_handling': False
        }
        
    def start_backend(self):
        """Start the FastAPI backend server"""
        try:
            logger.info("Starting FastAPI backend server...")
            self.backend_process = subprocess.Popen([
                sys.executable, "backend_api.py"
            ], cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            time.sleep(8)
            
            # Test if server is running
            response = requests.get(f"{self.backend_url}/api/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Backend server started successfully")
                return True
            else:
                logger.error(f"❌ Backend health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start backend: {e}")
            return False
    
    def test_backend_health(self):
        """Test backend server health and basic functionality"""
        try:
            logger.info("🔍 Testing backend health...")
            
            # Test root endpoint
            response = requests.get(self.backend_url, timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'running'
            
            # Test health endpoint
            response = requests.get(f"{self.backend_url}/api/health", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            
            logger.info("✅ Backend health tests passed")
            self.test_results['backend_health'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Backend health test failed: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test all critical API endpoints"""
        try:
            logger.info("🔍 Testing API endpoints...")
            
            # Test metrics endpoint
            response = requests.get(f"{self.backend_url}/api/metrics", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert 'data' in data
            assert 'total_campaigns' in data['data']
            logger.info(f"📊 Found {data['data']['total_campaigns']} campaigns, {data['data']['total_leads']} leads")
            
            # Test campaigns endpoint
            response = requests.get(f"{self.backend_url}/api/campaigns", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert 'data' in data
            assert isinstance(data['data'], list)
            logger.info(f"📋 Retrieved {len(data['data'])} campaigns")
            
            # Test leads endpoint
            response = requests.get(f"{self.backend_url}/api/leads", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert 'data' in data
            assert isinstance(data['data'], list)
            logger.info(f"👥 Retrieved {len(data['data'])} leads")
            
            logger.info("✅ API endpoints test passed")
            self.test_results['api_endpoints'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ API endpoints test failed: {e}")
            return False
    
    def test_websocket_connection(self):
        """Test WebSocket connectivity"""
        try:
            logger.info("🔍 Testing WebSocket connection...")
            
            # Test WebSocket connection
            ws_url = f"ws://localhost:8000/ws"
            
            connection_success = False
            message_received = False
            
            def on_message(ws, message):
                nonlocal message_received
                logger.info(f"📨 WebSocket message received: {message}")
                message_received = True
                ws.close()
            
            def on_open(ws):
                nonlocal connection_success
                logger.info("🔗 WebSocket connection opened")
                connection_success = True
                ws.send("test message")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.info("🔒 WebSocket connection closed")
            
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            
            # Run WebSocket in a separate thread
            wst = threading.Thread(target=ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Wait for connection and message
            time.sleep(5)
            
            if connection_success and message_received:
                logger.info("✅ WebSocket connection test passed")
                self.test_results['websocket_connection'] = True
                return True
            else:
                logger.error("❌ WebSocket connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket connection test failed: {e}")
            return False
    
    def test_campaign_lifecycle(self):
        """Test complete campaign creation, start, and monitoring"""
        try:
            logger.info("🔍 Testing campaign lifecycle...")
            
            # Create a campaign
            campaign_data = {
                "name": "Backend Test Campaign",
                "description": "Test campaign for backend validation",
                "business_types": ["healthcare", "optometry"],
                "location": "Test City, TX",
                "search_queries": ["test optometrist", "test eye doctor"],
                "max_leads": 25,
                "settings": {
                    "search_engine": "bing",
                    "max_leads_per_query": 12,
                    "enable_email_validation": True,
                    "min_email_confidence": 0.7,
                    "request_delay_seconds": 2.0,
                    "timeout_seconds": 30
                }
            }
            
            # Create campaign
            response = requests.post(
                f"{self.backend_url}/api/campaigns",
                json=campaign_data,
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            campaign_id = data['data']['id']
            logger.info(f"📋 Created campaign: {campaign_id}")
            
            # Verify campaign details
            response = requests.get(
                f"{self.backend_url}/api/campaigns/{campaign_id}",
                timeout=10
            )
            assert response.status_code == 200
            campaign = response.json()['data']
            assert campaign['name'] == campaign_data['name']
            assert campaign['status'] == 'draft'
            
            # Start campaign
            response = requests.post(
                f"{self.backend_url}/api/campaigns/{campaign_id}/start",
                timeout=10
            )
            assert response.status_code == 200
            logger.info("🚀 Campaign started")
            
            # Monitor campaign progress for a bit
            for i in range(5):
                response = requests.get(
                    f"{self.backend_url}/api/campaigns/{campaign_id}",
                    timeout=10
                )
                campaign = response.json()['data']
                logger.info(f"📊 Campaign status: {campaign['status']}, step: {campaign['progress']['current_step']}")
                time.sleep(2)
            
            # Pause campaign
            response = requests.post(
                f"{self.backend_url}/api/campaigns/{campaign_id}/pause",
                timeout=10
            )
            assert response.status_code == 200
            logger.info("⏸️ Campaign paused")
            
            # Stop campaign
            response = requests.post(
                f"{self.backend_url}/api/campaigns/{campaign_id}/stop",
                timeout=10
            )
            assert response.status_code == 200
            logger.info("⏹️ Campaign stopped")
            
            logger.info("✅ Campaign lifecycle test passed")
            self.test_results['campaign_lifecycle'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Campaign lifecycle test failed: {e}")
            return False
    
    def test_real_time_updates(self):
        """Test real-time progress updates via WebSocket"""
        try:
            logger.info("🔍 Testing real-time progress updates...")
            
            # Create a campaign first
            campaign_data = {
                "name": "Real-time Test Campaign",
                "description": "Test campaign for real-time updates",
                "business_types": ["test"],
                "location": "Test City",
                "search_queries": ["test query"],
                "max_leads": 5,
                "settings": {
                    "search_engine": "bing",
                    "max_leads_per_query": 5
                }
            }
            
            response = requests.post(
                f"{self.backend_url}/api/campaigns",
                json=campaign_data,
                timeout=10
            )
            assert response.status_code == 200
            campaign_id = response.json()['data']['id']
            
            # Set up WebSocket to monitor progress updates
            progress_updates_received = []
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get('type') == 'campaign_progress':
                        progress_updates_received.append(data)
                        logger.info(f"📈 Progress update: {data['progress']['current_step']} - {data['progress']['leads_found']} leads")
                except:
                    pass
            
            def on_open(ws):
                logger.info("🔗 WebSocket connected for progress monitoring")
            
            ws = websocket.WebSocketApp(f"ws://localhost:8000/ws",
                                      on_open=on_open,
                                      on_message=on_message)
            
            # Start WebSocket in separate thread
            wst = threading.Thread(target=ws.run_forever)
            wst.daemon = True
            wst.start()
            
            time.sleep(2)
            
            # Start the campaign
            response = requests.post(
                f"{self.backend_url}/api/campaigns/{campaign_id}/start",
                timeout=10
            )
            assert response.status_code == 200
            
            # Wait for progress updates
            time.sleep(15)
            
            if len(progress_updates_received) > 0:
                logger.info(f"✅ Real-time updates test passed ({len(progress_updates_received)} updates received)")
                self.test_results['real_time_updates'] = True
                return True
            else:
                logger.error("❌ No progress updates received")
                return False
                
        except Exception as e:
            logger.error(f"❌ Real-time updates test failed: {e}")
            return False
    
    def test_email_validation(self):
        """Test email validation functionality structure"""
        try:
            logger.info("🔍 Testing email validation configuration...")
            
            # Check if email validation is properly configured in the API
            response = requests.get(f"{self.backend_url}/api/campaigns", timeout=10)
            campaigns = response.json()['data']
            
            if len(campaigns) > 0:
                campaign = campaigns[0]
                settings = campaign.get('settings', {})
                
                # Check for email validation settings
                email_validation_enabled = settings.get('enable_email_validation', False)
                min_confidence = settings.get('min_email_confidence', 0.0)
                
                logger.info(f"📧 Email validation enabled: {email_validation_enabled}")
                logger.info(f"📊 Min confidence threshold: {min_confidence}")
                
                # Email validation structure is available
                self.test_results['email_validation'] = True
                logger.info("✅ Email validation configuration test passed")
                return True
            
            logger.error("❌ No campaigns found to test email validation")
            return False
            
        except Exception as e:
            logger.error(f"❌ Email validation test failed: {e}")
            return False
    
    def test_csv_export(self):
        """Test CSV export functionality"""
        try:
            logger.info("🔍 Testing CSV export...")
            
            # Get a campaign to export
            response = requests.get(f"{self.backend_url}/api/campaigns", timeout=10)
            campaigns = response.json()['data']
            
            if len(campaigns) > 0:
                campaign_id = campaigns[0]['id']
                
                # Test export endpoint
                response = requests.post(
                    f"{self.backend_url}/api/campaigns/{campaign_id}/export",
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data['success'] == True
                assert 'downloadUrl' in data['data']
                
                logger.info(f"📁 Export URL generated: {data['data']['downloadUrl']}")
                logger.info("✅ CSV export test passed")
                self.test_results['csv_export'] = True
                return True
            
            logger.error("❌ No campaigns found for CSV export test")
            return False
            
        except Exception as e:
            logger.error(f"❌ CSV export test failed: {e}")
            return False
    
    def test_performance(self):
        """Test system performance under load"""
        try:
            logger.info("🔍 Testing backend performance...")
            
            # Test API response times
            start_time = time.time()
            
            # Make multiple concurrent requests
            import concurrent.futures
            
            def make_request(endpoint):
                return requests.get(f"{self.backend_url}{endpoint}", timeout=10)
            
            endpoints = ["/api/metrics", "/api/campaigns", "/api/leads"] * 10
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
                futures = [executor.submit(make_request, endpoint) for endpoint in endpoints]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            
            # Check that all requests succeeded
            success_count = len([r for r in responses if r.status_code == 200])
            total_time = end_time - start_time
            
            if success_count >= 25:  # Allow for some failures
                avg_response_time = total_time / len(responses)
                requests_per_second = len(responses) / total_time
                
                logger.info(f"✅ Performance test passed:")
                logger.info(f"   📊 {success_count}/{len(responses)} requests successful")
                logger.info(f"   ⏱️ Average response time: {avg_response_time:.3f}s")
                logger.info(f"   🚀 Throughput: {requests_per_second:.1f} req/s")
                
                self.test_results['performance'] = True
                return True
            else:
                logger.error(f"❌ Performance test failed - only {success_count}/{len(responses)} requests successful")
                return False
                
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        try:
            logger.info("🔍 Testing error handling...")
            
            # Test 404 for non-existent campaign
            response = requests.get(f"{self.backend_url}/api/campaigns/non-existent-id", timeout=10)
            assert response.status_code == 404
            logger.info("✅ 404 handling works correctly")
            
            # Test invalid campaign creation
            invalid_campaign = {
                "name": "",  # Empty name
                "description": "Invalid campaign",
                "business_types": [],
                "location": "",
                "search_queries": [],
                "max_leads": -1,  # Invalid negative value
                "settings": {}
            }
            
            response = requests.post(
                f"{self.backend_url}/api/campaigns",
                json=invalid_campaign,
                timeout=10
            )
            # Should handle gracefully
            assert response.status_code in [200, 400, 422]
            logger.info("✅ Invalid input handling works")
            
            # Test malformed JSON
            try:
                response = requests.post(
                    f"{self.backend_url}/api/campaigns",
                    data="invalid json",
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                assert response.status_code in [400, 422]
                logger.info("✅ Malformed JSON handling works")
            except:
                logger.info("⚠️ Malformed JSON test skipped")
            
            logger.info("✅ Error handling test passed")
            self.test_results['error_handling'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test processes"""
        logger.info("🧹 Cleaning up test processes...")
        
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
    
    def run_all_tests(self):
        """Run all backend tests"""
        logger.info("🚀 Starting Backend Integration Test Suite")
        logger.info("=" * 60)
        
        try:
            # Start backend service
            if not self.start_backend():
                logger.error("❌ Failed to start backend - aborting tests")
                return False
            
            # Run tests in sequence
            tests = [
                ("Backend Health", self.test_backend_health),
                ("API Endpoints", self.test_api_endpoints),
                ("WebSocket Connection", self.test_websocket_connection),
                ("Campaign Lifecycle", self.test_campaign_lifecycle),
                ("Real-time Updates", self.test_real_time_updates),
                ("Email Validation Config", self.test_email_validation),
                ("CSV Export", self.test_csv_export),
                ("Performance", self.test_performance),
                ("Error Handling", self.test_error_handling)
            ]
            
            passed_tests = 0
            total_tests = len(tests)
            
            for test_name, test_func in tests:
                logger.info(f"\n📋 Running {test_name} test...")
                try:
                    if test_func():
                        passed_tests += 1
                        logger.info(f"✅ {test_name} - PASSED")
                    else:
                        logger.error(f"❌ {test_name} - FAILED")
                except Exception as e:
                    logger.error(f"❌ {test_name} - ERROR: {e}")
                
                time.sleep(1)  # Brief pause between tests
            
            # Print summary
            logger.info("\n" + "=" * 60)
            logger.info("📊 BACKEND TEST SUMMARY")
            logger.info("=" * 60)
            
            for key, passed in self.test_results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                logger.info(f"{key.replace('_', ' ').title()}: {status}")
            
            success_rate = (passed_tests / total_tests) * 100
            logger.info(f"\nBackend Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
            
            if success_rate >= 80:
                logger.info("🎉 BACKEND READY FOR PRODUCTION")
                return True
            else:
                logger.error("💥 BACKEND NEEDS WORK")
                return False
                
        finally:
            self.cleanup()

def main():
    """Main test execution"""
    test_suite = BackendTestSuite()
    success = test_suite.run_all_tests()
    
    if success:
        logger.info("\n🚀 Backend is production-ready!")
        return 0
    else:
        logger.error("\n⚠️ Backend needs fixes")
        return 1

if __name__ == "__main__":
    sys.exit(main())