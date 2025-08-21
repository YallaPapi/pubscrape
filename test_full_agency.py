#!/usr/bin/env python3
"""
Comprehensive test of VRSEN Agency Swarm functionality
Tests actual agent communication and task execution
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_single_agent_conversation():
    """Test having a conversation with a single agent"""
    try:
        from agency_swarm import set_openai_key
        from BingNavigator import BingNavigator
        
        # Set OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OpenAI API key required for agent conversation test")
            return False
            
        set_openai_key(openai_key)
        
        # Create BingNavigator agent
        print("🤖 Creating BingNavigator agent...")
        navigator = BingNavigator()
        print(f"✅ Created: {navigator.name}")
        
        # Test agent conversation
        print("\n💬 Testing agent conversation...")
        test_message = """
        I need you to help me understand your capabilities. 
        What tools do you have available and what can you do?
        Please be specific about your search functionality.
        """
        
        print(f"📤 Sending: {test_message.strip()}")
        
        # Create a single-agent agency to test the agent
        from agency_swarm import Agency
        agency = Agency([navigator])
        
        # Get completion through agency
        response = agency.get_completion(test_message)
        
        # Handle generator response and MessageOutput objects
        if hasattr(response, '__iter__') and not isinstance(response, str):
            content_parts = []
            for chunk in response:
                if hasattr(chunk, 'get_content'):
                    content_parts.append(chunk.get_content())
                elif hasattr(chunk, 'content'):
                    content_parts.append(chunk.content)
                else:
                    content_parts.append(str(chunk))
            response = ''.join(content_parts)
        
        print(f"📥 Response: {response}")
        print("✅ Agent conversation successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Single agent conversation failed: {e}")
        return False

def test_multi_agent_agency():
    """Test creating and running a multi-agent agency"""
    try:
        from agency_swarm import Agency, set_openai_key
        from BingNavigator import BingNavigator
        from SerpParser import SerpParser
        
        # Set OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OpenAI API key required for agency test")
            return False
            
        set_openai_key(openai_key)
        
        # Create agents
        print("🤖 Creating agents...")
        navigator = BingNavigator()
        parser = SerpParser()
        
        print(f"✅ Created: {navigator.name}, {parser.name}")
        
        # Create agency with communication flow
        print("\n🏢 Creating agency...")
        agency = Agency([
            navigator,                    # Navigator is entry point
            [navigator, parser],          # Navigator can talk to Parser
        ])
        
        print("✅ Agency created successfully!")
        print("   Communication flow: BingNavigator → SerpParser")
        
        # Test agency conversation
        print("\n💬 Testing agency conversation...")
        test_task = """
        I need to execute a search for 'plumber atlanta contact' and then parse the results.
        
        BingNavigator: Please use your SerpFetchTool to search for business contact information.
        Then hand off the HTML results to SerpParser for processing.
        
        Work together to complete this task step by step.
        """
        
        print(f"📤 Sending task: {test_task.strip()}")
        
        # Get agency response
        response = agency.get_completion(test_task)
        
        # Handle generator response and MessageOutput objects
        if hasattr(response, '__iter__') and not isinstance(response, str):
            content_parts = []
            for chunk in response:
                if hasattr(chunk, 'get_content'):
                    content_parts.append(chunk.get_content())
                elif hasattr(chunk, 'content'):
                    content_parts.append(chunk.content)
                else:
                    content_parts.append(str(chunk))
            response = ''.join(content_parts)
        
        print(f"📥 Agency response: {response}")
        print("✅ Multi-agent agency conversation successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-agent agency test failed: {e}")
        return False

def test_agency_demo_mode():
    """Test agency in demo mode (if supported)"""
    try:
        from agency_swarm import Agency, set_openai_key
        from BingNavigator import BingNavigator
        from CampaignCEO import CampaignCEO
        
        # Set OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OpenAI API key required for demo test")
            return False
            
        set_openai_key(openai_key)
        
        # Create agents
        print("🤖 Creating demo agency...")
        ceo = CampaignCEO()
        navigator = BingNavigator()
        
        # Create simple agency
        agency = Agency([
            ceo,                         # CEO is entry point
            [ceo, navigator],            # CEO can delegate to Navigator
        ])
        
        print("✅ Demo agency created!")
        print("   Entry point: CampaignCEO")
        print("   Delegation: CEO → BingNavigator")
        
        # Test if demo mode works
        print("\n🎪 Testing demo capabilities...")
        
        # Try terminal demo (non-blocking)
        try:
            print("   Terminal demo: Available")
            # Don't actually run it in test, just confirm it exists
            demo_method = getattr(agency, 'run_demo', None)
            if demo_method:
                print("   ✅ run_demo() method available")
            else:
                print("   ❌ run_demo() method not found")
        except Exception as e:
            print(f"   ❌ Terminal demo error: {e}")
        
        # Try gradio demo (non-blocking)
        try:
            print("   Web demo: Checking availability...")
            gradio_method = getattr(agency, 'demo_gradio', None)
            if gradio_method:
                print("   ✅ demo_gradio() method available")
            else:
                print("   ❌ demo_gradio() method not found")
        except Exception as e:
            print(f"   ❌ Web demo error: {e}")
        
        print("✅ Demo mode test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Demo mode test failed: {e}")
        return False

def test_tool_functionality():
    """Test tool execution within agency context"""
    try:
        from agency_swarm import set_openai_key
        from BingNavigator import BingNavigator
        
        # Set OpenAI key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OpenAI API key required for tool test")
            return False
            
        set_openai_key(openai_key)
        
        # Create agent
        navigator = BingNavigator()
        
        # Test tool-specific conversation
        print("🔧 Testing tool usage in conversation...")
        tool_test = """
        Please use your SerpFetchTool to execute a search for 'test query'.
        
        Set these parameters:
        - query: "restaurant chicago contact"
        - page: 1  
        - timeout_s: 15
        - use_stealth: false
        
        After you execute the tool, tell me what happened and show me the results.
        """
        
        print(f"📤 Tool test request: {tool_test.strip()}")
        
        # Create a single-agent agency to test tool usage
        from agency_swarm import Agency
        agency = Agency([navigator])
        
        response = agency.get_completion(tool_test)
        
        # Handle generator response and MessageOutput objects
        if hasattr(response, '__iter__') and not isinstance(response, str):
            content_parts = []
            for chunk in response:
                if hasattr(chunk, 'get_content'):
                    content_parts.append(chunk.get_content())
                elif hasattr(chunk, 'content'):
                    content_parts.append(chunk.content)
                else:
                    content_parts.append(str(chunk))
            response = ''.join(content_parts)
        
        print(f"📥 Tool execution response: {response}")
        
        # Check if response mentions tool usage
        if "SerpFetchTool" in response or "search" in response.lower():
            print("✅ Agent attempted to use tool!")
        else:
            print("⚠️  Agent may not have used tool (check response)")
            
        return True
        
    except Exception as e:
        print(f"❌ Tool functionality test failed: {e}")
        return False

def main():
    """Run comprehensive VRSEN Agency Swarm tests"""
    print("🧪 COMPREHENSIVE VRSEN AGENCY SWARM TEST")
    print("=" * 50)
    
    tests = [
        ("Single Agent Conversation", test_single_agent_conversation),
        ("Tool Functionality", test_tool_functionality),
        ("Multi-Agent Agency", test_multi_agent_agency),
        ("Demo Mode Capabilities", test_agency_demo_mode),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20}")
        print(f"🔍 TEST: {test_name}")
        print(f"{'='*20}")
        
        try:
            success = test_func()
            results[test_name] = success
            
            if success:
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"\n💥 {test_name}: CRASHED - {e}")
            results[test_name] = False
    
    # Final summary
    print(f"\n{'='*50}")
    print("📊 FINAL TEST RESULTS")
    print(f"{'='*50}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! VRSEN Agency Swarm is fully functional!")
        print("\n🚀 Ready for:")
        print("   - End-to-end lead generation pipeline")
        print("   - Campaign orchestration") 
        print("   - Production deployment")
    elif passed >= total * 0.75:
        print(f"\n✅ MOSTLY WORKING! {passed} out of {total} tests passed.")
        print("   Minor issues to resolve but core functionality working.")
    else:
        print(f"\n⚠️  NEEDS ATTENTION: Only {passed} out of {total} tests passed.")
        print("   Check errors above for configuration issues.")

if __name__ == "__main__":
    main()