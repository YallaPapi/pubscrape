"""
Simple runner for YouTuber Contact Discovery Agent
Works on Windows console without Unicode issues
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

from ytscrape import Pipeline


def main():
    """Run a simple test of the pipeline."""
    
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "python programming tutorials"
    
    print("\n" + "="*60)
    print("YouTuber Contact Discovery Agent")
    print("="*60)
    print(f"Query: {query}")
    print("="*60 + "\n")
    
    # Create pipeline
    pipeline = Pipeline()
    
    # Run with basic settings
    try:
        result = pipeline.run(
            query=query,
            podcast_name="Tech Talk Podcast",
            podcast_topic="technology and programming",
            host_name="Host",
            max_channels=5,  # Small number for testing
            min_score=5,
            output_filename="youtube_contacts.csv"
        )
        
        if result:
            print(f"\n[SUCCESS] Output saved to: {result}")
        else:
            print("\n[ERROR] Pipeline failed")
            
    except Exception as e:
        print(f"\n[ERROR] Pipeline error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()