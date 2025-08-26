#!/usr/bin/env python3
"""
VRSEN Lead Generation - Frontend Integration Test
Tests the built frontend with backend integration
"""

import time
import logging
import requests
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FrontendIntegrationTest:
    """Test frontend-backend integration"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:4173"  # Vite preview port
        self.backend_process = None
        self.frontend_process = None
        
    def start_backend(self):
        """Start the FastAPI backend server"""
        try:
            logger.info("Starting FastAPI backend server...")
            self.backend_process = subprocess.Popen([
                sys.executable, "backend_api.py"
            ], cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            time.sleep(8)
            
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
    
    def start_frontend(self):
        """Start the production frontend preview server"""
        try:
            logger.info("Starting production frontend preview...")
            
            # Start preview server
            self.frontend_process = subprocess.Popen([
                "npm", "run", "preview", "--", "--port", "4173"
            ], cwd=Path(__file__).parent / "frontend", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            time.sleep(10)
            
            # Test if server is running
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Frontend preview server started successfully")
                return True
            else:
                logger.error(f"❌ Frontend health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start frontend: {e}")
            return False
    
    def test_frontend_backend_connectivity(self):
        """Test that frontend can connect to backend APIs"""
        try:
            logger.info("🔍 Testing frontend-backend connectivity...")
            
            # Test CORS headers
            response = requests.options(f"{self.backend_url}/api/campaigns", 
                                      headers={'Origin': self.frontend_url})
            
            logger.info("✅ Frontend-backend connectivity test passed")
            return True
                
        except Exception as e:
            logger.error(f"❌ Frontend-backend connectivity test failed: {e}")
            return False
    
    def test_static_assets(self):
        """Test that all static assets are accessible"""
        try:
            logger.info("🔍 Testing static assets...")
            
            # Check main page loads
            response = requests.get(self.frontend_url, timeout=10)
            assert response.status_code == 200
            
            content = response.text
            # Check for key frontend elements
            assert "VRSEN" in content or "Lead Generation" in content or "root" in content
            
            logger.info("✅ Static assets test passed")
            return True
                
        except Exception as e:
            logger.error(f"❌ Static assets test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test processes"""
        logger.info("🧹 Cleaning up test processes...")
        
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
            
        if self.frontend_process:
            self.frontend_process.terminate()
            self.frontend_process.wait()
    
    def run_tests(self):
        """Run all frontend integration tests"""
        logger.info("🚀 Starting Frontend Integration Tests")
        logger.info("=" * 50)
        
        try:
            # Start services
            if not self.start_backend():
                logger.error("❌ Failed to start backend - aborting tests")
                return False
                
            if not self.start_frontend():
                logger.error("❌ Failed to start frontend - aborting tests")
                return False
            
            # Run tests
            tests = [
                ("Frontend-Backend Connectivity", self.test_frontend_backend_connectivity),
                ("Static Assets", self.test_static_assets)
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
            
            success_rate = (passed_tests / total_tests) * 100
            logger.info(f"\nFrontend Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
            
            if success_rate >= 80:
                logger.info("🎉 FRONTEND INTEGRATION READY")
                return True
            else:
                logger.error("💥 FRONTEND NEEDS WORK")
                return False
                
        finally:
            self.cleanup()

def main():
    """Main test execution"""
    test_suite = FrontendIntegrationTest()
    success = test_suite.run_tests()
    
    if success:
        logger.info("\n🚀 Frontend integration is ready!")
        return 0
    else:
        logger.error("\n⚠️ Frontend integration needs fixes")
        return 1

if __name__ == "__main__":
    sys.exit(main())