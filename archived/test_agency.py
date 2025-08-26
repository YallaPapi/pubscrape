#!/usr/bin/env python3
"""
Test script for VRSEN Agency Swarm setup
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_agency_swarm_import():
    """Test that Agency Swarm imports correctly"""
    try:
        from agency_swarm import Agency, set_openai_key
        print("✅ Agency Swarm imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Agency Swarm import failed: {e}")
        return False

def test_openai_key():
    """Test OpenAI API key is available"""
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("✅ OpenAI API key found")
        return True
    else:
        print("❌ OpenAI API key not found in environment")
        return False

def test_agent_imports():
    """Test that all VRSEN agents import correctly"""
    agents_to_test = [
        "CampaignCEO",
        "BingNavigator", 
        "SerpParser",
        "DomainClassifier",
        "SiteCrawler",
        "EmailExtractor",
        "ValidatorDedupe",
        "Exporter"
    ]
    
    successful_imports = []
    failed_imports = []
    
    for agent_name in agents_to_test:
        try:
            agent_module = __import__(agent_name, fromlist=[agent_name])
            agent_class = getattr(agent_module, agent_name)
            print(f"✅ {agent_name} imports successfully")
            successful_imports.append(agent_name)
        except ImportError as e:
            print(f"❌ {agent_name} import failed: {e}")
            failed_imports.append(agent_name)
        except Exception as e:
            print(f"❌ {agent_name} error: {e}")
            failed_imports.append(agent_name)
    
    return successful_imports, failed_imports

def test_bing_navigator_tool():
    """Test the BingNavigator SerpFetchTool"""
    try:
        from BingNavigator.tools.SerpFetchTool import SerpFetchTool
        
        # Create tool instance
        tool = SerpFetchTool(
            query="test query",
            page=1,
            timeout_s=30,
            use_stealth=False  # Disable stealth for basic test
        )
        
        print("✅ SerpFetchTool creates successfully")
        print(f"   - Query: {tool.query}")
        print(f"   - Page: {tool.page}")
        print(f"   - Timeout: {tool.timeout_s}s")
        print(f"   - Stealth: {tool.use_stealth}")
        
        return True
    except ImportError as e:
        print(f"❌ SerpFetchTool import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ SerpFetchTool error: {e}")
        return False

def test_basic_agency_creation():
    """Test creating a basic agency with available agents"""
    try:
        from agency_swarm import Agency, set_openai_key
        
        # Set OpenAI key if available
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️  Skipping agency creation test - no OpenAI key")
            return True
            
        set_openai_key(openai_key)
        
        # Try to import and create one agent
        from BingNavigator import BingNavigator
        bing_navigator = BingNavigator()
        
        print("✅ BingNavigator agent created successfully")
        print(f"   - Name: {bing_navigator.name}")
        print(f"   - Description: {bing_navigator.description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agency creation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing VRSEN Agency Swarm Setup")
    print("=" * 50)
    
    tests = [
        ("Agency Swarm Import", test_agency_swarm_import),
        ("OpenAI API Key", test_openai_key),
        ("Agent Imports", test_agent_imports),
        ("BingNavigator Tool", test_bing_navigator_tool),
        ("Basic Agency Creation", test_basic_agency_creation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Agency Swarm setup is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()