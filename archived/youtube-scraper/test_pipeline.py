"""
Test script for YouTuber Contact Discovery Pipeline
"""

import sys
sys.path.insert(0, '.')

from ytscrape import Pipeline


def test_basic_pipeline():
    """Test basic pipeline functionality."""
    print("\n" + "="*60)
    print("🧪 Testing YouTuber Contact Discovery Pipeline")
    print("="*60)
    
    # Test configuration
    test_config = {
        "query": "python programming tutorials",  # Small test query
        "podcast_name": "Code Talk Podcast",
        "podcast_topic": "programming and software development",
        "host_name": "Test Host",
        "max_channels": 5,  # Small number for testing
        "min_score": 5,
        "output_filename": "test_output.csv"
    }
    
    print("\n📋 Test Configuration:")
    for key, value in test_config.items():
        print(f"  • {key}: {value}")
    
    try:
        # Initialize pipeline
        print("\n🚀 Starting pipeline test...")
        pipeline = Pipeline()
        
        # Run pipeline
        result = pipeline.run_with_config(test_config)
        
        if result:
            print(f"\n✅ Test successful! Output: {result}")
            
            # Get pipeline state
            state = pipeline.get_pipeline_state()
            print("\n📊 Pipeline Statistics:")
            print(f"  • Channels fetched: {state['raw_channels']}")
            print(f"  • Channels normalized: {state['normalized_channels']}")
            print(f"  • Channels scored: {state['scored_channels']}")
            print(f"  • Final output: {state['final_channels']} channels")
            
            return True
        else:
            print("\n❌ Test failed - no output generated")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quota_check():
    """Test quota management system."""
    print("\n🔍 Testing Quota Management...")
    
    from ytscrape.quota_manager import QuotaManager
    
    quota_mgr = QuotaManager()
    status = quota_mgr.get_quota_status()
    
    print(f"  • Current quota used: {status['used']}/{status['total']}")
    print(f"  • Remaining: {status['remaining']} units")
    print(f"  • Can search: {status['can_search']}")
    print(f"  • Can fetch channel: {status['can_fetch_channel']}")
    
    ops = quota_mgr.estimate_operations_available()
    print(f"\n  • Searches available: {ops['searches']}")
    print(f"  • Channel fetches available: {ops['channel_fetches']}")
    
    return True


def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing Configuration...")
    
    try:
        from ytscrape.config import config
        
        print("  ✅ Configuration loaded successfully")
        print(f"  • YouTube API Key: {'✓' if config.YOUTUBE_API_KEY else '✗'}")
        print(f"  • OpenAI API Key: {'✓' if config.OPENAI_API_KEY else '✗'}")
        print(f"  • Output directory: {config.OUTPUT_DIR}")
        
        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


if __name__ == "__main__":
    print("\n🧪 YouTuber Contact Discovery Agent - Test Suite")
    print("="*60)
    
    # Run tests
    tests_passed = 0
    tests_total = 3
    
    # Test 1: Configuration
    if test_configuration():
        tests_passed += 1
    
    # Test 2: Quota Check
    if test_quota_check():
        tests_passed += 1
    
    # Test 3: Basic Pipeline (only if config is valid)
    print("\n" + "="*60)
    response = input("⚠️  Run full pipeline test? This will use API quota (y/n): ")
    if response.lower() == 'y':
        if test_basic_pipeline():
            tests_passed += 1
    else:
        print("⏭️  Skipping pipeline test")
        tests_total -= 1
    
    # Print summary
    print("\n" + "="*60)
    print(f"📊 Test Results: {tests_passed}/{tests_total} passed")
    if tests_passed == tests_total:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {tests_total - tests_passed} test(s) failed")
    print("="*60)