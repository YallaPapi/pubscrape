#!/usr/bin/env python3
"""
Demo script for VRSEN Agency Swarm functionality
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_bing_navigator_functionality():
    """Test BingNavigator agent with a real search"""
    try:
        from agency_swarm import set_openai_key
        from BingNavigator import BingNavigator
        
        # Set OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OpenAI API key required for agent functionality test")
            return False
            
        set_openai_key(openai_key)
        
        # Create BingNavigator agent
        navigator = BingNavigator()
        print(f"✅ Created BingNavigator: {navigator.name}")
        
        # Test the tool directly first
        from BingNavigator.tools.SerpFetchTool import SerpFetchTool
        
        tool = SerpFetchTool(
            query="plumber atlanta contact",
            page=1,
            timeout_s=10,
            use_stealth=False  # Disable for testing
        )
        
        print("🔧 Testing SerpFetchTool directly...")
        result = tool.run()
        
        print(f"   Status: {result.get('status')}")
        print(f"   Error (if any): {result.get('error_message', 'None')}")
        
        if result.get('status') == 'success':
            print(f"   HTML Length: {len(result.get('html', ''))}")
            print("✅ SerpFetchTool working correctly")
        else:
            print("⚠️  SerpFetchTool returned error (expected if infrastructure not set up)")
            
        return True
        
    except Exception as e:
        print(f"❌ BingNavigator functionality test failed: {e}")
        return False

def test_simple_agency():
    """Test creating a simple agency with multiple agents"""
    try:
        from agency_swarm import Agency, set_openai_key
        from BingNavigator import BingNavigator
        from CampaignCEO import CampaignCEO
        
        # Set OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OpenAI API key required for agency test")
            return False
            
        set_openai_key(openai_key)
        
        # Create agents
        ceo = CampaignCEO()
        navigator = BingNavigator()
        
        print(f"✅ Created agents: {ceo.name}, {navigator.name}")
        
        # Create simple agency
        agency = Agency([
            ceo,                    # CEO is entry point
            [ceo, navigator],       # CEO can talk to Navigator
        ])
        
        print("✅ Agency created successfully")
        print(f"   Communication flows: CEO → BingNavigator")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple agency test failed: {e}")
        return False

def main():
    """Run demo tests"""
    print("🚀 VRSEN Agency Swarm Demo")
    print("=" * 40)
    
    tests = [
        ("BingNavigator Functionality", test_bing_navigator_functionality),
        ("Simple Agency Creation", test_simple_agency),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        try:
            success = test_func()
            if success:
                print(f"✅ {test_name} completed successfully")
            else:
                print(f"⚠️  {test_name} had issues")
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 Demo completed!")
    print("\nNext steps:")
    print("   1. Configure Botasaurus and search infrastructure")
    print("   2. Set up remaining agents with proper tools")
    print("   3. Create complete agency workflow")
    print("   4. Test end-to-end lead generation pipeline")

if __name__ == "__main__":
    main()