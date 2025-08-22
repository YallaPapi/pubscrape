#!/usr/bin/env python3
"""
Debug SerpParseTool to identify the exact issue
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_serp_tool_minimal():
    """Minimal test of SerpParseTool"""
    print("Testing SerpParseTool initialization...")
    
    try:
        from agents.tools.serp_parse_tool import SerpParseTool
        print("Import successful")
        
        # Simple HTML content
        html = """
        <html>
        <body>
            <div id="b_results">
                <div class="b_algo">
                    <h2><a href="https://example.com">Example</a></h2>
                    <div class="b_caption"><p>Test result</p></div>
                </div>
            </div>
        </body>
        </html>
        """
        
        print("Creating SerpParseTool instance...")
        tool = SerpParseTool(
            html_content=html,
            query="test query",
            page_number=1
        )
        print("Instance created successfully")
        
        print("Running tool...")
        result = tool.run()
        print(f"Tool completed: {result.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_serp_tool_minimal()