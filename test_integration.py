#!/usr/bin/env python3
"""
Integration Test for VRSEN Lead Generation System
Tests the complete backend integration with the lead generation engine
"""

import asyncio
import json
import sys
import time
from pathlib import Path
import requests
import websockets
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class IntegrationTester:
    """Test the complete integration system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.ws_url = f"ws://localhost:8000/ws"
        self.test_campaign_id = None
        
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log test message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def assert_true(self, condition: bool, message: str):
        """Assert condition is true"""
        self.results["tests_run"] += 1
        
        if condition:
            self.results["tests_passed"] += 1
            self.log(f"✓ {message}", "PASS")
        else:
            self.results["tests_failed"] += 1
            self.results["errors"].append(message)
            self.log(f"✗ {message}", "FAIL")
    
    def test_health_check(self):
        """Test health check endpoint"""
        self.log("Testing health check endpoint")
        
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            self.assert_true(response.status_code == 200, "Health endpoint returns 200")
            
            data = response.json()
            self.assert_true(data.get("status") == "healthy", "Health status is healthy")
            self.assert_true("version" in data, "Health response includes version")
            
        except Exception as e:
            self.assert_true(False, f"Health check failed: {e}")
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        self.log("Testing metrics endpoint")
        
        try:
            response = requests.get(f"{self.api_url}/metrics", timeout=10)
            self.assert_true(response.status_code == 200, "Metrics endpoint returns 200")
            
            data = response.json()
            self.assert_true(data.get("success") is True, "Metrics response is successful")
            self.assert_true("data" in data, "Metrics includes data")
            
            metrics = data["data"]
            expected_fields = ["totalCampaigns", "activeCampaigns", "totalLeads"]
            for field in expected_fields:
                self.assert_true(field in metrics, f"Metrics includes {field}")
            
        except Exception as e:
            self.assert_true(False, f"Metrics test failed: {e}")
    
    def test_create_campaign(self):
        """Test campaign creation"""
        self.log("Testing campaign creation")
        
        campaign_data = {
            "name": "Integration Test Campaign",
            "description": "Test campaign for integration testing",
            "business_types": ["optometry", "eye care"],
            "location": "Atlanta, GA",
            "search_queries": ["optometrist Atlanta test"],
            "max_leads": 5,
            "settings": {
                "search_engine": "bing",
                "language": "en",
                "country_code": "US",
                "max_pages_per_query": 1,
                "max_leads_per_query": 5,
                "request_delay_seconds": 1.0,
                "timeout_seconds": 10,
                "headless_mode": True,
                "use_rotating_user_agents": True,
                "use_residential_proxies": False,
                "enable_email_validation": True,
                "enable_dns_checking": False,
                "min_email_confidence": 0.5,
                "min_business_score": 0.4,
                "max_concurrent_extractions": 2,
                "include_report": True,
                "exclude_keywords": ["yelp", "reviews"],
                "output_directory": "test_output",
                "csv_filename": ""
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/campaigns",
                json=campaign_data,
                timeout=10
            )
            
            self.assert_true(response.status_code == 200, "Campaign creation returns 200")
            
            data = response.json()
            self.assert_true(data.get("success") is True, "Campaign creation is successful")
            self.assert_true("data" in data, "Campaign response includes data")
            
            campaign = data["data"]
            self.test_campaign_id = campaign.get("id")
            
            self.assert_true(self.test_campaign_id is not None, "Campaign has ID")
            self.assert_true(campaign.get("name") == campaign_data["name"], "Campaign name matches")
            self.assert_true(campaign.get("status") == "draft", "Campaign status is draft")
            
            self.log(f"Created test campaign: {self.test_campaign_id}")
            
        except Exception as e:
            self.assert_true(False, f"Campaign creation failed: {e}")
    
    def test_get_campaigns(self):
        """Test getting campaigns list"""
        self.log("Testing campaigns list endpoint")
        
        try:
            response = requests.get(f"{self.api_url}/campaigns", timeout=10)
            self.assert_true(response.status_code == 200, "Campaigns list returns 200")
            
            data = response.json()
            self.assert_true("data" in data, "Campaigns response includes data")
            self.assert_true("total" in data, "Campaigns response includes total")
            
            campaigns = data["data"]
            self.assert_true(isinstance(campaigns, list), "Campaigns data is a list")
            
            if self.test_campaign_id:
                campaign_ids = [c["id"] for c in campaigns]
                self.assert_true(
                    self.test_campaign_id in campaign_ids,
                    "Test campaign appears in campaigns list"
                )
            
        except Exception as e:
            self.assert_true(False, f"Get campaigns failed: {e}")
    
    def test_get_single_campaign(self):
        """Test getting single campaign"""
        if not self.test_campaign_id:
            self.assert_true(False, "No test campaign ID available")
            return
        
        self.log("Testing single campaign endpoint")
        
        try:
            response = requests.get(
                f"{self.api_url}/campaigns/{self.test_campaign_id}",
                timeout=10
            )
            
            self.assert_true(response.status_code == 200, "Single campaign returns 200")
            
            data = response.json()
            self.assert_true(data.get("success") is True, "Single campaign response is successful")
            
            campaign = data["data"]
            self.assert_true(campaign.get("id") == self.test_campaign_id, "Campaign ID matches")
            
        except Exception as e:
            self.assert_true(False, f"Get single campaign failed: {e}")
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        self.log("Testing WebSocket connection")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self.assert_true(True, "WebSocket connection established")
                
                # Test subscription message
                if self.test_campaign_id:
                    subscribe_message = {
                        "type": "subscribe_campaign",
                        "campaign_id": self.test_campaign_id
                    }
                    
                    await websocket.send(json.dumps(subscribe_message))
                    
                    # Wait for confirmation
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        self.assert_true(
                            response_data.get("type") == "subscription_confirmed",
                            "WebSocket subscription confirmed"
                        )
                    except asyncio.TimeoutError:
                        self.assert_true(False, "WebSocket subscription timeout")
                
        except Exception as e:
            self.assert_true(False, f"WebSocket test failed: {e}")
    
    def test_start_campaign(self):
        """Test starting a campaign (without waiting for completion)"""
        if not self.test_campaign_id:
            self.assert_true(False, "No test campaign ID available")
            return
        
        self.log("Testing campaign start (this may take a moment)")
        
        try:
            response = requests.post(
                f"{self.api_url}/campaigns/{self.test_campaign_id}/start",
                timeout=15
            )
            
            self.assert_true(response.status_code == 200, "Campaign start returns 200")
            
            data = response.json()
            self.assert_true(data.get("success") is True, "Campaign start is successful")
            
            campaign = data["data"]
            self.assert_true(campaign.get("status") == "running", "Campaign status is running")
            
            # Wait a few seconds to let it start
            self.log("Waiting for campaign to begin processing...")
            time.sleep(3)
            
            # Check campaign status again
            status_response = requests.get(
                f"{self.api_url}/campaigns/{self.test_campaign_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                campaign_status = status_data.get("data", {}).get("status")
                self.log(f"Campaign status after start: {campaign_status}")
            
        except Exception as e:
            self.assert_true(False, f"Campaign start failed: {e}")
    
    def test_stop_campaign(self):
        """Test stopping a campaign"""
        if not self.test_campaign_id:
            self.assert_true(False, "No test campaign ID available")
            return
        
        self.log("Testing campaign stop")
        
        try:
            response = requests.post(
                f"{self.api_url}/campaigns/{self.test_campaign_id}/stop",
                timeout=10
            )
            
            self.assert_true(response.status_code == 200, "Campaign stop returns 200")
            
            data = response.json()
            self.assert_true(data.get("success") is True, "Campaign stop is successful")
            
            campaign = data["data"]
            self.assert_true(campaign.get("status") == "completed", "Campaign status is completed")
            
        except Exception as e:
            self.assert_true(False, f"Campaign stop failed: {e}")
    
    def test_leads_endpoint(self):
        """Test leads endpoint"""
        self.log("Testing leads endpoint")
        
        try:
            response = requests.get(f"{self.api_url}/leads", timeout=10)
            self.assert_true(response.status_code == 200, "Leads endpoint returns 200")
            
            data = response.json()
            self.assert_true("data" in data, "Leads response includes data")
            self.assert_true("total" in data, "Leads response includes total")
            
            leads = data["data"]
            self.assert_true(isinstance(leads, list), "Leads data is a list")
            
        except Exception as e:
            self.assert_true(False, f"Leads endpoint test failed: {e}")
    
    def test_cleanup(self):
        """Clean up test campaign"""
        if not self.test_campaign_id:
            return
        
        self.log("Cleaning up test campaign")
        
        try:
            # Make sure campaign is stopped first
            requests.post(f"{self.api_url}/campaigns/{self.test_campaign_id}/stop")
            
            # Delete the campaign
            response = requests.delete(
                f"{self.api_url}/campaigns/{self.test_campaign_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("Test campaign cleaned up successfully")
            else:
                self.log(f"Campaign cleanup returned status: {response.status_code}")
            
        except Exception as e:
            self.log(f"Campaign cleanup failed: {e}", "WARN")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        self.log("Starting VRSEN Integration Tests")
        self.log(f"Testing backend at: {self.base_url}")
        
        # Basic API tests
        self.test_health_check()
        self.test_metrics_endpoint()
        
        # Campaign management tests
        self.test_create_campaign()
        self.test_get_campaigns()
        self.test_get_single_campaign()
        
        # WebSocket test
        await self.test_websocket_connection()
        
        # Campaign execution test (brief)
        self.test_start_campaign()
        time.sleep(2)  # Let it run briefly
        self.test_stop_campaign()
        
        # Other endpoints
        self.test_leads_endpoint()
        
        # Cleanup
        self.test_cleanup()
        
        # Print results
        self.print_results()
    
    def print_results(self):
        """Print test results"""
        self.log("Integration Test Results:")
        self.log(f"Total Tests: {self.results['tests_run']}")
        self.log(f"Passed: {self.results['tests_passed']}")
        self.log(f"Failed: {self.results['tests_failed']}")
        
        if self.results["tests_failed"] == 0:
            self.log("🎉 ALL TESTS PASSED! Integration is working correctly.", "SUCCESS")
        else:
            self.log("❌ Some tests failed. Check the errors above.", "ERROR")
            for error in self.results["errors"]:
                self.log(f"  - {error}", "ERROR")

async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VRSEN Integration Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    args = parser.parse_args()
    
    # Check if backend is running
    try:
        response = requests.get(f"{args.url}/api/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Backend not responding at {args.url}")
            print("Please start the backend with: python start_integrated_backend.py")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to backend at {args.url}")
        print("Please start the backend with: python start_integrated_backend.py")
        return 1
    
    # Run tests
    tester = IntegrationTester(args.url)
    await tester.run_all_tests()
    
    return 0 if tester.results["tests_failed"] == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)